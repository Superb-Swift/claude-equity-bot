#!/usr/bin/env python3
# =============================================================================
# retired_criteria_audit.py  —  does anything still print a CLOSED question
#                               as if it were a LIVE criterion?
# =============================================================================
# WHY THIS EXISTS
#   Retiring a research question is not one edit. The Q1 guardrail (50-59 vs
#   60-69) was closed by Q1-R on 2026-07-13, and retiring it touched, in order:
#     - h1_lag_trace.py      printed the guardrail criterion as a pass/fail
#     - the T2 tripwire       fired on a suspended decision input
#     - guardrail_trace.py    two sheets + regime_stratification.md
#     - run_weekly_review.bat a closing banner pointing at retired artifacts
#   Each was found by accident, one at a time, weeks apart. This tool finds
#   the rest on purpose.
#
#   THE FAILURE MODE IS NOT MENTIONING A RETIRED THING. Provenance, closeout
#   notes and history SHOULD name it. The failure is presenting it in the
#   grammar of a live decision input — a bar, a verdict, a PASS/FAIL, a
#   tripwire, an instruction to act. So the scan is two-factor: a retired
#   TOPIC token AND live-CRITERION grammar on the same line. A line carrying
#   an explicit retirement marker is cleared.
#
# EXIT CODE
#   0 = clean (or LOW only), 1 = at least one HIGH/MEDIUM finding. Safe to
#   chain into a pre-commit hook once the current findings are cleared.
#
# USAGE
#   python retired_criteria_audit.py                 (scans . recursively)
#   python retired_criteria_audit.py --root src --ext .py .bat
#   python retired_criteria_audit.py --quiet         (findings only)
# =============================================================================

from __future__ import annotations
import argparse
import os
import re
import sys

# ---- what is retired -------------------------------------------------------
# Add a row here the day a question closes; that is the whole maintenance job.
#
# NB on the Q1 pattern: "60-69" is deliberately NOT a token on its own. That
# band is shared by two DIFFERENT questions — the RETIRED Q1 guardrail (the
# 50-59 vs 60-69 comparison) and the LIVE KEEP-70 near-miss band (BUY signals
# at 60-69 that the 70% gate rejects, which H4 and KEEP-70 both still turn on).
# Tokenising bare "60-69" flagged h4_dq_threshold.py's near-miss lever, which
# is a live question and correct as written. "50-59" and "guardrail" only ever
# mean the retired comparison, so those are the tokens.
RETIRED = {
    "Q1 guardrail (50-59 vs 60-69)": r"50\s*[-–]\s*59|guardrail",
    "T2 tripwire":                   r"\bT2\b|tripwire",
    "Live Cohort Scoreboard":        r"live cohort scoreboard|scoreboard",
    "regime stratification":         r"regime[_ ]strat|stratify-regime",

    # ---- disposed at the 3-B closeout, 2026-07-31 --------------------------
    # ANALYST NOTE (2026-08-03): the original table only held retired
    #   TRIPWIRES, so the audit could not see a criterion that was LIVE when
    #   written and DISPOSED since — which is what G1 and G2 became on 7/31.
    #   That blind spot is why run_daily_review.bat's closing banner has been
    #   printing live-criterion grammar for two dispositioned gates for three
    #   days while the audit reported 23 HIGH findings about something else.
    #   A disposition is a retirement; add the row the day it is signed.
    "G2 blend gate — DESCOPED 2026-07-31":   r"\bG2\b|gate[- ]flip",
    "G1 WS2 gate — INSUFFICIENT TEST COND.": r"\bG1\b",

    # H4 itself is LIVE (demoted, still measured). Only its BAR moved: n >= 10
    # was superseded 2026-07-28 by n >= 12 on two consecutive readings, after
    # the n=10 bar produced a one-session false REOPEN. Token the stale bar,
    # never "H4" — tokenising the question would flag every correct use.
    "H4 n>=10 bar — superseded 2026-07-28":  r"n\s*(?:at or past|>=|≥)\s*10\b",
}

# ---- the grammar of a LIVE criterion ---------------------------------------
CRITERION = re.compile(
    r"\b(pass|fail|verdict|criterion|criteria|threshold|tripwire|bar is|"
    r"must (?:lead|be|exceed|hold)|should (?:lead|be)|reopen|re-open|fires?\b|"
    r"decision input|acceptance|gate)\b", re.I)

# ---- an explicit retirement marker clears the line -------------------------
CLEARED = re.compile(
    r"\b(retired?|retirement|closed|suspended|context[- ]only|superseded|"
    r"no longer|deprecat|historical|Q1-R|do not use|was\b)\b", re.I)

# printing/emitting rather than merely computing
EMITS = re.compile(r"\b(print|echo|write|append|L\.append|f\")", re.I)

# An explicit opt-out for a line that is genuinely fine and cannot be reworded.
PRAGMA = re.compile(r"#\s*audit:\s*retired-ok", re.I)

# A retirement marker rarely sits on the SAME physical line as the tokens —
# multi-line f-strings, wrapped comments and echo blocks split them. Look this
# many lines either side before calling a line a finding.
CLEAR_WINDOW = 3

SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules", ".idea", ".vscode"}

# ---- places where a retired criterion is CORRECT to find -------------------
# ANALYST NOTE (2026-08-03): after the 3-C housekeeping move the audit reported
#   HIGH 23 · MEDIUM 34 — and not one of them was actionable. Every finding sat
#   in Retired\, in an archived spec, or in the institutional record. Meanwhile
#   the FOUR that matter (run_daily_review.bat's G2/G1/H4 banner lines and
#   run_daily.bat's era comment) were buried under 57 you have to scroll past.
#
#   An audit nobody reads is worse than no audit, because exit 1 stops meaning
#   anything. Two principles fix it:
#     * A tool inside a folder named Retired\ is ALREADY marked retired. The
#       folder name is the retirement marker; requiring the words as well is
#       asking the operator to edit code that is out of the cadence by design.
#     * THE HISTORICAL RECORD IS NOT A LIVE CRITERION. analyst_notes.md
#       entries dated 6/15-6/24 describe the guardrail while it WAS live.
#       Rewording them to satisfy a linter would falsify dated provenance —
#       the exact discipline this project runs on. Never edit the record to
#       quiet a tool.
#
#   Everything excluded here is still SCANNED on demand: --include-archived.
EXCLUDE_PATHS = (
    "Retired",                 # retired by folder; the location IS the marker
    "docs/Archived",           # applied splices, superseded by analyst_notes.md
    "docs/Phase 3-A docs",     # closed-phase specs — history, not cadence
    "docs/Phase 3-B docs",
    "docs/analyst_notes.md",   # the institutional record. Do not reword it.
)


def _excluded(path, root):
    """True if `path` lies under a directory or file the audit should not
    police. Compared on a normalised relative path so Windows separators and
    './' prefixes behave the same."""
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        rel = path
    rel = rel.replace("\\", "/").lstrip("./")
    return any(rel == ex or rel.startswith(ex.rstrip("/") + "/")
               for ex in (e.replace("\\", "/") for e in EXCLUDE_PATHS))

# This file is skipped by default: its RETIRED/CRITERION tables are by
# construction full of the very tokens it scans for, so it always matches
# itself. --include-self to scan it anyway.
SELF = os.path.basename(__file__)


def classify(line, neighbourhood=""):
    """-> (severity, topic) or None. Two-factor: retired topic + live grammar.

    `neighbourhood` is the line plus CLEAR_WINDOW lines either side; a
    retirement marker anywhere in it clears the finding, because the marker
    and the tokens routinely land on different physical lines.
    """
    hits = [name for name, pat in RETIRED.items() if re.search(pat, line, re.I)]
    if not hits:
        return None
    if PRAGMA.search(line):
        return None                                   # explicit opt-out
    if CLEARED.search(neighbourhood or line):
        return None                                   # marked retired nearby
    topic = hits[0]
    if CRITERION.search(line):
        return ("HIGH", topic)                        # framed as a live bar
    if EMITS.search(line):
        return ("MEDIUM", topic)                      # surfaced to the operator
    return ("LOW", topic)                             # mentioned in passing


def scan(root, exts, include_self=False, include_archived=False):
    out = []
    skipped = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if not include_archived:
            dirnames[:] = [d for d in dirnames
                           if not _excluded(os.path.join(dirpath, d), root)]
        for fn in sorted(filenames):
            if exts and os.path.splitext(fn)[1].lower() not in exts:
                continue
            if fn == SELF and not include_self:
                continue
            path = os.path.join(dirpath, fn)
            if not include_archived and _excluded(path, root):
                skipped += 1
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                lo = max(0, i - 1 - CLEAR_WINDOW)
                hi = min(len(lines), i + CLEAR_WINDOW)
                c = classify(line, "".join(lines[lo:hi]))
                if c:
                    out.append((c[0], c[1], path, i, line.rstrip()[:110]))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    out.sort(key=lambda r: (order[r[0]], r[2], r[3]))
    return out, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit for retired criteria still framed as live.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--ext", nargs="*", default=[".py", ".bat", ".md", ".cmd", ".ps1"])
    ap.add_argument("--quiet", action="store_true", help="suppress LOW findings")
    ap.add_argument("--include-self", action="store_true",
                    help="also scan this audit script (it matches its own tables)")
    ap.add_argument("--include-archived", action="store_true",
                    help="also scan Retired\\, archived docs and analyst_notes.md "
                         "(excluded by default — see EXCLUDE_PATHS)")
    args = ap.parse_args(argv)

    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in args.ext}
    findings, n_excluded = scan(args.root, exts, args.include_self,
                                args.include_archived)
    if args.quiet:
        findings = [f for f in findings if f[0] != "LOW"]

    print("=" * 74)
    print("RETIRED-CRITERIA AUDIT — root: %s" % os.path.abspath(args.root))
    if not args.include_archived:
        print("scope: LIVE CADENCE only — %d file(s) skipped under %s"
              % (n_excluded, ", ".join(EXCLUDE_PATHS)))
        print("       (--include-archived to scan them)")
    print("=" * 74)
    if not findings:
        print("\nCLEAN — nothing framing a retired question as a live criterion.\n")
        return 0

    cur = None
    for sev, topic, path, ln, text in findings:
        if sev != cur:
            cur = sev
            print("\n---- %s ----" % sev)
            print({"HIGH":   "  a retired question stated as a live bar/verdict — FIX",
                   "MEDIUM": "  a retired question surfaced to the operator — review wording",
                   "LOW":    "  mentioned only; usually fine (provenance/history)"}[sev])
            print()
        print("  %s:%d" % (path, ln))
        print("      [%s] %s" % (topic, text))

    hi = sum(1 for f in findings if f[0] == "HIGH")
    md = sum(1 for f in findings if f[0] == "MEDIUM")
    lo = sum(1 for f in findings if f[0] == "LOW")
    print("\n" + "=" * 74)
    print("HIGH %d · MEDIUM %d · LOW %d" % (hi, md, lo))
    print("Clear a line by rewording it, or by marking it retired in place")
    print("(the words 'retired', 'closed', 'suspended', 'context only' clear it).")
    print("=" * 74)
    return 1 if (hi or md) else 0


if __name__ == "__main__":
    raise SystemExit(main())
