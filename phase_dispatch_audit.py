#!/usr/bin/env python3
# =============================================================================
# phase_dispatch_audit.py  --  THE D-8 GATE
# =============================================================================
# WHAT THIS IS:
#   The check that closes D-8. main.py's PHASE constant and its phase-dispatch
#   tuple are INDEPENDENT: nothing in the codebase requires the value of one to
#   appear in the other. Moving PHASE without extending the tuple sends every
#   ticker to the else-branch log.error, and the resulting run:
#
#     * emits ZERO "Signal JSON:" lines  -- the handler that writes them never
#       runs, so the log is empty of signals and every parser reports a clean
#       zero-row day rather than an error;
#     * has ALREADY SPENT all 24 API calls -- get_signal() is called BEFORE the
#       dispatch, so the cost is incurred whether or not a handler exists;
#     * STILL ADVANCES signal_state.json -- the S1 prior-state write sits
#       OUTSIDE the dispatch, so the WS2 chain moves forward on a run that
#       produced nothing.
#
#   That combination is silent in exactly the way the 2026-06-15 and 2026-07-07
#   cutovers were silent, and it destroys a canonical cohort.
#
# WHY IT IS NOT COVERED BY edgar_parser_audit.py:
#   That harness SYNTHESISES log lines and runs the real parsers against them.
#   It never executes main.py, so a dispatch that declines to run is invisible
#   to it. Both harnesses would stay green through the entire failure. This is
#   the gap the analyst notes named: "the parser audit cannot see it because it
#   never executes main.py".
#
# WHY THIS READS THE SOURCE INSTEAD OF IMPORTING IT:
#   Importing main.py executes module-level code and pulls in the Schwab and
#   Anthropic clients, which needs credentials this check has no business
#   touching and no business requiring. The pairing under test is STATIC -- a
#   constant and a literal tuple -- so it is verified statically, by parsing
#   the source. No network, no credentials, no API spend, no state mutation.
#
# USAGE (project root):
#     python phase_dispatch_audit.py
#     python phase_dispatch_audit.py --file main.py
#
# EXIT CODES:  0 = PHASE is routable; the dispatch will reach a handler
#              1 = FAILED -- PHASE would fall through to the error branch
#              2 = harness could not run (file unreadable / shape not found)
#
# Advisory-only . no orders . not financial advice.
# =============================================================================

import argparse
import ast
import sys


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None


def find_phase_constant(tree):
    """Module-level PHASE = <literal>."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "PHASE":
                    return _literal(node.value)
    return None


def find_dispatch_tuples(tree):
    """Every `PHASE in (<literals>)` test anywhere in the module.

    Returns a list of (lineno, tuple_of_values). More than one is not an
    error -- main.py may grow further phase tests -- but EVERY one of them is
    reported, because a PHASE that satisfies one test and not another is the
    same silent-divergence hazard in a new place.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "PHASE"):
            continue
        for op, comp in zip(node.ops, node.comparators):
            if isinstance(op, ast.In):
                vals = _literal(comp)
                if isinstance(vals, (tuple, list, set)):
                    found.append((node.lineno, tuple(vals)))
    return found


def find_phase_equalities(tree):
    """Every `PHASE == <literal>` test -- e.g. the Phase-2 branch."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "PHASE"):
            continue
        for op, comp in zip(node.ops, node.comparators):
            if isinstance(op, ast.Eq):
                out.append((node.lineno, _literal(comp)))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="D-8 gate: PHASE must be routable by main.py's dispatch. "
                    "Advisory-only; no orders; not financial advice.")
    ap.add_argument("--file", default="main.py")
    args = ap.parse_args()

    print("=" * 72)
    print("  PHASE DISPATCH AUDIT (D-8)")
    print("=" * 72)

    try:
        src = open(args.file, encoding="utf-8").read()
        tree = ast.parse(src)
    except (OSError, SyntaxError) as e:
        print(f"\nHARNESS ERROR: cannot read/parse {args.file} ({e}).")
        return 2

    phase = find_phase_constant(tree)
    if phase is None:
        print(f"\nHARNESS ERROR: no module-level PHASE assignment in {args.file}.")
        return 2

    tuples = find_dispatch_tuples(tree)
    equalities = find_phase_equalities(tree)
    if not tuples and not equalities:
        print(f"\nHARNESS ERROR: no `PHASE in (...)` or `PHASE == ...` test "
              f"found in {args.file}. The dispatch shape changed; this "
              f"harness must be updated before it can gate anything.")
        return 2

    print(f"\n  PHASE constant      : {phase!r}   ({args.file})")
    for ln, vals in tuples:
        print(f"  dispatch tuple L{ln:<5}: {vals}")
    for ln, val in equalities:
        print(f"  equality test L{ln:<5} : PHASE == {val!r}")

    fails = []
    routable = any(phase in vals for _ln, vals in tuples) or \
        any(phase == val for _ln, val in equalities)

    print()
    if routable:
        print(f"  [PASS] PHASE {phase!r} is matched by a dispatch branch")
    else:
        print(f"  [FAIL] PHASE {phase!r} matches NO dispatch branch -- every "
              f"ticker would fall to the error branch")
        print(f"         24 API calls would be spent, ZERO 'Signal JSON:' "
              f"lines emitted, and signal_state.json would still advance.")
        fails.append("PHASE not routable")

    # Every tuple must agree about PHASE. A value routable by one test and not
    # another is D-8 wearing a different hat.
    disagreeing = [ln for ln, vals in tuples if phase not in vals]
    if tuples and disagreeing and routable:
        print(f"  [FAIL] PHASE {phase!r} is absent from the tuple(s) at line(s) "
              f"{disagreeing} while present in another -- the dispatch tests "
              f"disagree with each other")
        fails.append("dispatch tuples disagree")
    elif len(tuples) > 1:
        print(f"  [PASS] all {len(tuples)} dispatch tuples agree on PHASE")

    # The bracket the parsers key on is built from PHASE, so a divergence
    # between the constant and the logged token is impossible by construction.
    # Assert that construction rather than assume it.
    uses_phase_in_tag = "f\"[PHASE {PHASE} DRY RUN" in src
    if uses_phase_in_tag:
        print("  [PASS] the logged phase bracket is built from PHASE itself")
    else:
        print("  [FAIL] the logged phase bracket is NOT built from PHASE -- "
              "the constant and the log token can now diverge")
        fails.append("phase tag not derived from PHASE")

    print("\n" + "=" * 72)
    if fails:
        print(f"  PHASE DISPATCH AUDIT: FAILED -- {len(fails)} check(s)")
        for f in fails:
            print(f"    - {f}")
        print("  DO NOT RUN. Extend the dispatch tuple in the SAME edit that")
        print("  moves PHASE.")
        print("=" * 72)
        return 1

    print("  PHASE DISPATCH AUDIT: PASSED")
    print(f"  PHASE {phase!r} reaches a handler. D-8 is disarmed for this value.")
    print("  STILL REQUIRED: one live run showing 24 'Signal JSON:' lines.")
    print("  This audit proves the dispatch ROUTES; it does not prove the")
    print("  handler, the Schwab path or the API path work.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
