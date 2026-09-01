#!/usr/bin/env python3
"""
apply_h1_window_ruling.py — verify the H1 window diagnosis LIVE, then apply it.

THE RULING (operator, 2026-08-26): apply the H1 window fix and stamp a new era.
This script is the whole ruling in one command, with the verification wired in
front of the write so the two cannot be separated.

WHY THE VERIFICATION IS PART OF THE SCRIPT
------------------------------------------
The SYMPTOM is airtight: `trail_basis_audit.py` found the same one-session
forward shift on all ten August logs, with two independent signatures (236/240
oldest-element matches, 255/255 newest elements within 0.5% of that session's
own Px@signal).

The CAUSE was INFERRED from price evidence, not observed. Nobody has watched
`schwab_client.get_price_history()` run and looked at what it returns. The
inference is that local-time `datetime.fromtimestamp()` dates every candle one
day early. If that is wrong, the patch below is aimed at the wrong thing.

This script closes that gap before writing anything.

THE TEST, AND WHY IT IS DECISIVE
--------------------------------
Under the diagnosis every returned candle is labelled one CALENDAR day early.
Any five consecutive NYSE sessions span at least one weekend, so at least one
of them is a Monday -- and a Monday labelled one day early is a SUNDAY.

    correct :  every returned date is an NYSE session
    defect  :  at least one returned date is a weekend or holiday

So: fetch one ticker's history and ask whether every date it returns is a real
session. That is a yes/no question with no judgement in it, and it needs one
API call. A second, corroborating check compares the newest returned close
against the live quote -- under the defect they are the same intraday print.

If the dates all land on real sessions, the diagnosis is REFUTED and this
script refuses to write. That is the outcome worth protecting against: a patch
applied to a correctly-behaving function, on the strength of a story that
happened to fit.

WHAT IT WRITES, IF AND ONLY IF THE DIAGNOSIS HOLDS
--------------------------------------------------
  1. `schwab_client.py`  -- date candles in UTC, compare against Eastern today,
     and warn loudly if an in-progress candle ever reaches the window again.
     (The same two edits as `propose_h1_window_fix.py`, imported from it so
     there is one definition, not two.)

  2. `main.py` -- the era stamp: `A-S1D1-B1-E1` -> `A-S1D2-B1-E1`.
     D IS THE RIGHT GENERATION TO BUMP. The damping engine is what consumes
     the trailing move: `risk_engine.compute_trail_pct()` reads this list and
     feeds THETA. S1, B1 and E1 are untouched by the change, and saying so in
     the stamp is more informative than incrementing a global version.

MEASURED IMPACT, on the 2026-08-26 cohort (3 of 24 operative confidences):
    DOW  36 -> 42     (run trail -8.75%  vs contract -5.01%   damp 6 -> 0)
    PWR  49 -> 45     (run trail -8.28%  vs contract -10.87%  damp 5 -> 9)
    WMT  42 -> 38     (run trail +0.78%  vs contract -7.80%   damp 0 -> 4)
CBRS's damp moves 14 -> 15 and binds DampingConfig.CAP. No row crossed the 70%
gate that day; that is one session, not a bound.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import os
import shutil
import sys

OLD_ERA, NEW_ERA = "A-S1D1-B1", "A-S1D2-B1"

ERA_EDIT = (
    "main.py",
    "era stamp: D1 -> D2 (the damping engine consumes the trailing move)",
    'PROMPT_VARIANT = "A-S1D1-B1-E1" if EDGAR_ENABLED else "A-S1D1-B1"\n',
    "# ERA BUMP 2026-08-26, ruled by the operator. The H1 trailing window was\n"
    "# shifted one session forward and ended on a live intraday print; see\n"
    "# H1_Window_OffByOne_Defect_2026-08-26.md. risk_engine.compute_trail_pct()\n"
    "# reads that series and feeds THETA damping, so the D generation is what\n"
    "# changes. S1, B1 and E1 are untouched and keep their numbers deliberately:\n"
    "# the stamp should say WHICH channel moved, not merely that something did.\n"
    "#\n"
    "# DO NOT POOL ACROSS THIS LINE. H1 trailing moves before and after are\n"
    "# different measurements, so any lag, damping or episode series spanning it\n"
    "# is measuring two things. Same discipline as DP-3C-o.\n"
    'PROMPT_VARIANT = "A-S1D2-B1-E1" if EDGAR_ENABLED else "A-S1D2-B1"\n',
)


# -----------------------------------------------------------------------------
# signal_scan.py -- the era registry. WITHOUT THESE THREE EDITS THE FIRST RUN
# UNDER THE NEW ERA IS A LOUD, MISLEADING FINDING.
#
#   1. KNOWN_ERAS: an unregistered stamp FAILS by design ("era stamp ... is
#      UNKNOWN"). That check is right and must keep working -- so register the
#      new era rather than weaken it.
#   2. ERA_RANK: rank is TREATMENT, and this ruling changes none. D2 keeps D1's
#      rank so the direction rule reads "same arm", not "regression".
#   3. A THIRD BRANCH. With equal ranks the existing code falls through to the
#      RESTORED message -- "treatment is back and THIS run is correct, the
#      finding belongs to yesterday" -- which is wrong advice for a deliberate,
#      ruled bump. That file's own note says a FAIL whose advice is wrong
#      teaches the reader to skim it. Same trap, one branch further along.
# -----------------------------------------------------------------------------
SCAN_EDITS = [
    (
        "signal_scan.py",
        "KNOWN_ERAS: register the D2 generation",
        'KNOWN_ERAS = {\n'
        '    "A-S1D1-B1":    "pre-EDGAR (3-B)",\n'
        '    "A-S1D1-B1-E1": "EDGAR live (3-C)",\n'
        '}\n',

        'KNOWN_ERAS = {\n'
        '    "A-S1D1-B1":    "pre-EDGAR (3-B)",\n'
        '    "A-S1D1-B1-E1": "EDGAR live (3-C)",\n'
        '    # ADDED 2026-08-26 with the H1 window ruling. D2 = trailing move over\n'
        '    # five COMPLETED sessions; D1 = the shifted window ending on a live\n'
        '    # intraday print. Same treatment, different measurement.\n'
        '    "A-S1D2-B1":    "pre-EDGAR (3-B), H1 window corrected",\n'
        '    "A-S1D2-B1-E1": "EDGAR live (3-C), H1 window corrected",\n'
        '}\n',
    ),
    (
        "signal_scan.py",
        "ERA_RANK: D2 carries D1's treatment rank",
        'ERA_RANK = {\n'
        '    "A-S1D1-B1":    0,\n'
        '    "A-S1D1-B1-E1": 1,\n'
        '}\n',

        'ERA_RANK = {\n'
        '    "A-S1D1-B1":    0,\n'
        '    "A-S1D1-B1-E1": 1,\n'
        '    # RANK IS TREATMENT, and the H1 window ruling changes none of it: the\n'
        '    # EDGAR arm is untouched. Equal rank across the D1->D2 line is the\n'
        '    # correct statement and is what routes it to the third branch below.\n'
        '    "A-S1D2-B1":    0,\n'
        '    "A-S1D2-B1-E1": 1,\n'
        '}\n',
    ),
    (
        "signal_scan.py",
        "era-change alarm: a same-treatment bump is neither a loss nor a recovery",
        '                else:\n'
        '                    out.append(("WARN",\n'
        '                                "era stamp RESTORED since {}: {} -> {}  ** treatment is back and "\n',

        '                elif now == was:\n'
        '                    # ADDED 2026-08-26. A deliberate generation bump at the SAME\n'
        '                    # treatment rank is neither a loss nor a recovery, and the\n'
        '                    # RESTORED advice below would be actively wrong for it.\n'
        '                    out.append(("WARN",\n'
        '                                "era stamp CHANGED since {}: {} -> {}  ** SAME treatment "\n'
        '                                "rank, so nothing was lost or restored. This is a ruled "\n'
        '                                "generation bump. Cohorts either side are DIFFERENT "\n'
        '                                "MEASUREMENTS on the changed channel - do not pool across "\n'
        '                                "the line. Confirm the ruling is recorded."\n'
        '                                .format(p_date, p_era, this_era)))\n'
        '                else:\n'
        '                    out.append(("WARN",\n'
        '                                "era stamp RESTORED since {}: {} -> {}  ** treatment is back and "\n',
    ),
]

def _lf(s: str) -> str:
    return s.replace("\r\n", "\n")


def _dominant_ending(s: str) -> str:
    crlf = s.count("\r\n")
    return "\r\n" if crlf and crlf >= (s.count("\n") - crlf) else "\n"


def _restore(s: str, ending: str) -> str:
    return s.replace("\n", ending) if ending == "\r\n" else s


# -----------------------------------------------------------------------------
# Step 1 - verify the diagnosis against the live feed
# -----------------------------------------------------------------------------
def verify(ticker: str):
    """Returns (verdict, detail). verdict in {'CONFIRMED','REFUTED','UNAVAILABLE'}."""
    try:
        from trading_calendar import is_trading_day
    except ImportError:
        return "UNAVAILABLE", "trading_calendar.py not importable from this directory."
    try:
        from schwab_client import get_price_history, get_quote
    except Exception as e:
        return "UNAVAILABLE", "could not import schwab_client: %s" % e

    try:
        hist = get_price_history(ticker, days=5)
    except Exception as e:
        return "UNAVAILABLE", "get_price_history(%s) raised: %s" % (ticker, e)
    if not hist:
        return "UNAVAILABLE", "get_price_history(%s) returned nothing (token expired? offline?)" % ticker

    lines, bad = [], []
    for c in hist:
        d = dt.date.fromisoformat(c["date"])
        ok = is_trading_day(d)
        if not ok:
            bad.append(c["date"])
        lines.append("      %s  %-9s  close %-12s  %s"
                     % (c["date"], d.strftime("%a"), c["close"],
                        "session" if ok else "<<< NOT AN NYSE SESSION"))

    today = dt.date.today()
    newest = dt.date.fromisoformat(hist[-1]["date"])
    detail = ["    returned by get_price_history(%r, days=5):" % ticker] + lines

    # Corroboration: under the defect the newest 'close' is today's live print.
    try:
        q = get_quote(ticker) or {}
        last = q.get("lastPrice")
        if last:
            gap = abs(hist[-1]["close"] - last) / last * 100.0
            detail.append("    newest returned close %s vs live quote %s -> %.3f%%%s"
                          % (hist[-1]["close"], last, gap,
                             "   <<< same intraday print" if gap <= 0.5 else ""))
    except Exception:
        pass

    if bad:
        detail.append("    %d returned date(s) are NOT NYSE sessions: %s"
                      % (len(bad), ", ".join(bad)))
        detail.append("    A weekend or holiday cannot be a completed session. The")
        detail.append("    candle dates are shifted. DIAGNOSIS CONFIRMED.")
        return "CONFIRMED", "\n".join(detail)

    if newest >= today:
        detail.append("    newest returned date %s is not BEFORE today %s -- the"
                      % (newest, today))
        detail.append("    in-progress session is in the window. DIAGNOSIS CONFIRMED")
        detail.append("    (by the second signature; the date shift did not show).")
        return "CONFIRMED", "\n".join(detail)

    detail.append("    Every returned date is a real NYSE session and the newest is")
    detail.append("    before today. The candle dates are NOT shifted.")
    detail.append("    DIAGNOSIS REFUTED -- do not apply this patch. The window")
    detail.append("    discrepancy is real (trail_basis_audit measures it) but its")
    detail.append("    cause is something else. Re-diagnose.")
    return "REFUTED", "\n".join(detail)


# -----------------------------------------------------------------------------
# Step 2 - the edits
# -----------------------------------------------------------------------------
def stage_edits():
    """(path, name, old, new) for every file this ruling touches."""
    try:
        from propose_h1_window_fix import EDITS as SC_EDITS, TARGET as SC_TARGET
    except ImportError:
        print("ERROR: propose_h1_window_fix.py not importable - it holds the "
              "schwab_client edits and this script will not duplicate them.",
              file=sys.stderr)
        raise SystemExit(2)
    out = [(SC_TARGET, name, old, new) for name, _why, old, new in SC_EDITS]
    out.append(ERA_EDIT)
    out.extend(SCAN_EDITS)
    return out


def apply_to_file(path, edits, do_write):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    ending = _dominant_ending(raw)
    original = _lf(raw)
    text = original
    for name, old, new in edits:
        old, new = _lf(old), _lf(new)
        n = text.count(old)
        if n != 1:
            return None, "anchor %r matched %d times (expected 1)" % (name, n)
    for name, old, new in edits:
        text = text.replace(_lf(old), _lf(new), 1)
    if do_write:
        bak = "%s.bak-%s" % (path, dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(path, bak)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(_restore(text, ending))
        return bak, None
    return (original, text), None


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify and apply the H1 window ruling.")
    ap.add_argument("--ticker", default="AAPL",
                    help="ticker used for the live verification fetch")
    ap.add_argument("--apply", action="store_true",
                    help="write the change (only if verification CONFIRMS)")
    ap.add_argument("--force-diagnosis", action="store_true",
                    help="proceed even if verification is UNAVAILABLE. Never use "
                         "this to get past a REFUTED result -- REFUTED means the "
                         "patch is aimed at the wrong thing.")
    a = ap.parse_args()

    print("=" * 78)
    print("H1 WINDOW RULING - %s" % ("APPLY" if a.apply else "DRY RUN"))
    print("=" * 78)
    print("  STEP 1 - verify the diagnosis against the live feed")
    print("-" * 78)
    verdict, detail = verify(a.ticker)
    print(detail)
    print("-" * 78)
    print("  VERDICT: %s" % verdict)
    print("-" * 78)

    if verdict == "REFUTED":
        print("  REFUSING TO WRITE. The window discrepancy is real, but this")
        print("  patch fixes a cause that is not present. Re-open the diagnosis:")
        print("    H1_Window_OffByOne_Defect_2026-08-26.md")
        print("=" * 78)
        return 1
    if verdict == "UNAVAILABLE" and not a.force_diagnosis:
        print("  REFUSING TO WRITE. Verification could not run, so the cause is")
        print("  still unconfirmed. Fix the feed access and re-run, or pass")
        print("  --force-diagnosis if you have confirmed it another way.")
        print("=" * 78)
        return 2

    print("  STEP 2 - the edits")
    print("-" * 78)
    staged = stage_edits()
    byfile = {}
    for path, name, old, new in staged:
        byfile.setdefault(path, []).append((name, old, new))
    for path, edits in byfile.items():
        if not os.path.exists(path):
            print("ERROR: not found: %s" % path, file=sys.stderr)
            return 2
        for name, _o, _n in edits:
            print("    %-20s %s" % (path, name))

    results = {}
    for path, edits in byfile.items():
        res, err = apply_to_file(path, edits, do_write=False)
        if err:
            print("-" * 78)
            print("REFUSING: %s: %s" % (path, err), file=sys.stderr)
            print("The file has drifted. Nothing was changed.", file=sys.stderr)
            return 2
        results[path] = res

    print("-" * 78)
    for path, (before, after) in results.items():
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(),
                                         fromfile=path + " (current)",
                                         tofile=path + " (ruled)", lineterm="", n=2):
            print(line)
    print("-" * 78)

    if not a.apply:
        print("  DRY RUN - nothing written. Re-run with --apply.")
        print("=" * 78)
        return 0

    for path, edits in byfile.items():
        bak, err = apply_to_file(path, edits, do_write=True)
        if err:                                                # pragma: no cover
            print("ERROR mid-write on %s: %s" % (path, err), file=sys.stderr)
            return 2
        print("  wrote %-20s backup %s" % (path, bak))

    print("-" * 78)
    print("  STEP 3 - confirm the window now spans what its label claims")
    print("-" * 78)
    print("  The audit reads LOGS, and no log has yet been written under the new")
    print("  code, so it will still report the OLD behaviour until the next run.")
    print("  That is expected. After the next bot run:")
    print("      python trail_basis_audit.py")
    print("  should report COMPLETED_ONLY and exit 0.")
    print("-" * 78)
    print("  STILL OWED - the code is changed, the record is not:")
    print("    1. The next log will stamp era %s-E1. Cohorts before and" % NEW_ERA)
    print("       after are DIFFERENT MEASUREMENTS on any H1, damping or episode")
    print("       series. Do not pool. (DP-3C-o precedent: nothing poolable.)")
    print("    2. G1's episode history was collected under the old window. The")
    print("       2 of 4 post-deploy episodes do not carry across the line.")
    print("       Decide whether G1's n restarts. It probably does.")
    print("    3. E4 is NOT contaminated: the defect was constant across all rows")
    print("       and both arms, so a within-cohort contrast is unbiased. Write")
    print("       that down, or someone will void nine cohorts over it later.")
    print("    4. Record the ruling in the next closing review's Standing block.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
