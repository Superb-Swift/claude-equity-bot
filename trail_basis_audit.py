#!/usr/bin/env python3
"""
trail_basis_audit.py — what window does H1's trailing move actually span?

WHY THIS EXISTS
---------------
The record has carried, since 2026-08-21, an explanation for why
`h1_lag_trace`'s `Trail5d` and the run's own `H1[trail5d=]` disagree: one
prices off `Price at Signal` (a ~09:3x quote) and the other off closes, and a
session a ticker missed is skipped rather than counted.

Both are true. On 2026-08-26 neither explained WMT, which read **+0.78% on the
run and -10.20% on the exhibit** -- opposite signs, 10.98 points apart, on the
WS2 tracer. This tool exists to answer the question that gap raised, on
evidence, every session, without anybody re-deriving it.

WHAT IT FOUND (2026-08-26)
--------------------------
`schwab_client.get_price_history()` promises "the most recent `days` sessions
that have ALREADY closed (today's in-progress candle is excluded)". It dates
each Schwab candle with

    cdate = datetime.fromtimestamp(ts / 1000).date()      # LOCAL time

...on an epoch stamped in a zone east of the machine's. Every candle is
therefore dated ONE DAY EARLY, and two things follow at once:

  1. today's IN-PROGRESS candle passes the `cdate < today` filter, so its last
     intraday print is treated as a completed close; and
  2. the oldest of the five completed sessions falls out of the `[-days:]` tail.

STATED PRECISELY, because the obvious framing is wrong. The interval COUNT is
not what changes -- both windows span four intervals. Both EDGES move:

    contract :  c(D-5) ---------------------------------> c(D-1)
    actual   :          c(D-4) ------------------> p(D, live intraday print)

  * the RIGHT edge becomes a live intraday print instead of a settled close, so
    the trailing move now contains part of today's tape -- the very thing an
    H1 trajectory feature exists to look BEHIND; and
  * the LEFT edge moves one session later, so a gap that opened overnight into
    session D-4 drops out of the window entirely.

WMT on 2026-08-26 is the clean demonstration: its ~11% gap opened overnight
into 2026-08-20. The contracted window c(08-19) -> c(08-25) contains that gap
and reads about -10%. The actual window c(08-20) -> p(08-26) does not, and reads
**+0.78%**. The exhibit's -10.20% is the figure CLOSER to the documented
contract; the run's is the one that is wrong.

This matters beyond reporting: `risk_engine.compute_trail_pct()` reads the same
list, so **THETA damping runs on the four-interval-plus-stub number**, which
sets operative confidence, which sets the signal.

DISCIPLINE
----------
  * Reads logs and the master. WRITES NOTHING. Changes no endpoint.
  * It does NOT assume the defect. Each log's alignment is determined
    EMPIRICALLY, by testing both candidate alignments against settled closes
    recovered from the master's own outcome columns and taking the one that
    matches. If the defect is fixed, this tool reports the new alignment and
    keeps working -- it is a detector, not a hardcoded expectation.
  * Exit 0 = alignment is COMPLETED_ONLY on every log examined (the documented
    contract). Exit 1 = at least one log spans a different window than its
    label claims.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

try:
    import openpyxl
except ImportError:                                            # pragma: no cover
    print("ERROR: openpyxl not available. Activate the venv.", file=sys.stderr)
    sys.exit(2)

try:
    from trading_calendar import shift_sessions
except ImportError:                                            # pragma: no cover
    print("ERROR: trading_calendar.py not importable from this directory.", file=sys.stderr)
    sys.exit(2)

H1_RE = re.compile(r"H1\[trail(\d+)d=([-+0-9.]+)%;\s*closes=([0-9.>]+)\]")
LOG_DATE_RE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")

# A close printed to 2dp against a manual entry carried at full precision.
MATCH_TOL_PCT = 0.03


# -----------------------------------------------------------------------------
# Inputs
# -----------------------------------------------------------------------------
def load_master_closes(tracker: str):
    """{(ticker, session date) -> close} recovered from the outcome columns.

    A `Price +Nd` cell on a cohort row IS the settled close for the session N
    trading days later. That is the project's only record of a close, and it is
    manual -- which is exactly why reconciling it against the log's independent
    machine-sourced channel is worth doing (see outcome_sanity Check F).
    """
    ws = openpyxl.load_workbook(tracker, data_only=True)["Signals"]
    out, pxsig, r = {}, {}, 5
    while ws.cell(r, 1).value is not None:
        d = ws.cell(r, 1).value
        d = d.date() if isinstance(d, dt.datetime) else d
        tkr = ws.cell(r, 2).value
        g = ws.cell(r, 7).value
        if isinstance(g, (int, float)):
            pxsig[(tkr, d)] = float(g)
        for col, n in ((8, 5), (9, 10), (10, 20)):
            v = ws.cell(r, col).value
            if isinstance(v, (int, float)):
                out.setdefault((tkr, shift_sessions(d, n)), []).append(float(v))
        r += 1
    # Keep only cells whose horizons agree; a disagreement is Check B's problem,
    # not this tool's, and an ambiguous reference is no reference at all.
    closes = {}
    for k, vals in out.items():
        if max(vals) - min(vals) <= abs(max(vals)) * MATCH_TOL_PCT / 100.0:
            closes[k] = vals[0]
    return closes, pxsig


def parse_log(path: str):
    """{ticker -> (labelled_n, trail_pct, [closes])} for one session log."""
    dec = json.JSONDecoder()
    rows = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            i = line.find("Signal JSON: ")
            if i < 0:
                continue
            tail = line[i + len("Signal JSON: "):]
            try:
                j, end = dec.raw_decode(tail)
            except ValueError:
                continue
            m = H1_RE.search(tail[end:])
            if m:
                rows[j["ticker"]] = (int(m.group(1)), float(m.group(2)),
                                     [float(x) for x in m.group(3).split(">")])
    return rows


# -----------------------------------------------------------------------------
# The test
# -----------------------------------------------------------------------------
def score_alignment(rows, run_date, closes_ref, last_is_run_date: bool):
    """How many tickers' `closes` line up under one candidate alignment?

    last_is_run_date=True  -> [D-(k-1) ... D]      : in-progress candle included
    last_is_run_date=False -> [D-k ... D-1]        : completed sessions only
    Only the OLDEST element is scored: the newest is an intraday print under the
    first alignment and has no settled reference, so scoring it would bias the
    test toward the answer we are trying to test for.
    """
    hits = misses = 0
    for tkr, (_, _, cl) in rows.items():
        k = len(cl)
        back = (k - 1) if last_is_run_date else k
        ref = closes_ref.get((tkr, shift_sessions(run_date, -back)))
        if ref is None or ref == 0:
            continue
        if abs(cl[0] - ref) / ref * 100.0 <= MATCH_TOL_PCT:
            hits += 1
        else:
            misses += 1
    return hits, misses


def audit_log(path: str, closes_ref, pxsig):
    m = LOG_DATE_RE.search(os.path.basename(path))
    if not m:
        return None
    run_date = dt.date.fromisoformat(m.group(1))
    rows = parse_log(path)
    if not rows:
        return None

    inprog = score_alignment(rows, run_date, closes_ref, True)
    done = score_alignment(rows, run_date, closes_ref, False)

    if inprog[0] > done[0]:
        alignment, score = "INCLUDES_IN_PROGRESS", inprog
    elif done[0] > inprog[0]:
        alignment, score = "COMPLETED_ONLY", done
    else:
        alignment, score = "UNDETERMINED", (0, 0)

    k = max(len(cl) for _, _, cl in rows.values())
    labelled = max(n for n, _, _ in rows.values())
    intervals = k - 1

    # Corroboration, reported but never used to decide: under
    # INCLUDES_IN_PROGRESS the newest element should sit near that session's
    # own Px@signal, because both are intraday prints from the same morning.
    near_quote = 0
    for tkr, (_, _, cl) in rows.items():
        q = pxsig.get((tkr, run_date))
        if q and abs(cl[-1] - q) / q * 100.0 <= 0.5:
            near_quote += 1

    return {
        "date": run_date, "n_tickers": len(rows), "points": k,
        "intervals": intervals, "labelled": labelled,
        "alignment": alignment, "hits": score[0], "misses": score[1],
        "inprog": inprog, "done": done, "near_quote": near_quote,
    }


def main():
    ap = argparse.ArgumentParser(description="Audit the window H1's trailing move spans.")
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"),
                    help="glob for session logs")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.tracker):
        print("ERROR: not found: %s" % a.tracker, file=sys.stderr)
        return 2
    paths = sorted(glob.glob(a.logs)) + sorted(glob.glob(os.path.join(
        os.path.dirname(a.logs) or ".", "**", os.path.basename(a.logs)), recursive=True))
    paths = sorted(set(paths))
    if not paths:
        print("ERROR: no logs matched %s" % a.logs, file=sys.stderr)
        return 2

    closes_ref, pxsig = load_master_closes(a.tracker)
    results = [r for r in (audit_log(p, closes_ref, pxsig) for p in paths) if r]
    if not results:
        print("ERROR: no usable H1 tags found.", file=sys.stderr)
        return 2

    print("=" * 84)
    print("H1 TRAILING-WINDOW AUDIT - %s" % dt.date.today())
    print("=" * 84)
    print("  Determined empirically per log, by matching the OLDEST `closes=`")
    print("  element against settled closes recovered from the master. Nothing")
    print("  here is assumed; the alignment is measured.")
    print("-" * 84)
    print("  %-12s %5s %7s %10s %9s  %-21s %8s %10s"
          % ("log", "tkrs", "points", "intervals", "label", "alignment", "matched", "last~quote"))
    for r in results:
        print("  %-12s %5d %7d %10d %9s  %-21s %5d/%-4d %6d/%d"
              % (r["date"], r["n_tickers"], r["points"], r["intervals"],
                 "trail%dd" % r["labelled"], r["alignment"],
                 r["hits"], r["hits"] + r["misses"], r["near_quote"], r["n_tickers"]))

    findings = []
    for r in results:
        if r["alignment"] == "INCLUDES_IN_PROGRESS":
            k = r["points"]
            findings.append(
                "[H1] %s: window is SHIFTED ONE SESSION FORWARD. Contract is the "
                "close %d sessions back -> the close 1 session back (%d completed "
                "closes). Actual is the close %d sessions back -> an IN-PROGRESS "
                "candle for the run date itself (%d/%d newest elements sit within "
                "0.5%% of that session's own Px@signal). Interval count is "
                "unchanged at %d; both EDGES move."
                % (r["date"], k, k, k - 1, r["near_quote"], r["n_tickers"],
                   r["intervals"]))
        elif r["alignment"] == "UNDETERMINED":
            findings.append("[H1] %s: alignment undetermined - too few settled "
                            "references in the master to decide." % r["date"])
        elif r["intervals"] != r["labelled"]:
            findings.append("[H1] %s: label says trail%dd, window spans %d "
                            "completed intervals." % (r["date"], r["labelled"], r["intervals"]))

    print("-" * 84)
    if findings:
        print("  %d FINDING(S):" % len(findings))
        for f in findings:
            print("    " + f)
        print("-" * 84)
        print("  CONSEQUENCE, stated plainly: risk_engine.compute_trail_pct()")
        print("  reads this same list, so THETA damping runs on it and sets the")
        print("  operative confidence. This is NOT confined to reporting.")
        print("  Diagnosis and the UNAPPLIED remedy:")
        print("    H1_Window_OffByOne_Defect_2026-08-26.md")
        print("    propose_h1_window_fix.py   (dry-run by default; --apply is a")
        print("                                deliberate, endpoint-moving act)")
        print("=" * 84)
        return 1

    print("  RESULT: CLEAN - every log spans the window its label claims,")
    print("  over completed sessions only.")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    sys.exit(main())
