#!/usr/bin/env python3
"""
chain_check.py - did the evening chain run in order before this review?

WHY THIS EXISTS (proposed 2026-10-16 and 2026-10-20; adopted 2026-10-22,
DP-3C-ba)
    Two evenings broke in a row and nothing said so at the time:
      * 2026-10-19: closes were never entered (the 54-cell gap);
      * 2026-10-20: the chain stopped after the review - no value.bat and no
        step-7 Excel refresh, so the report copy carried cached returns on 0
        of 2,490 rows the next morning.
    review_artifacts.py checks only what THIS review wrote. This checks what
    should already have happened, and it runs FIRST in run_daily_review.bat,
    before the report copy is rebuilt (the rebuild erases the evidence for
    check 4).

CHECKS (each a WARN line; exit 1 when any fires - run_daily_review.bat
    folds that into its exit code but never stops the review on it)
    1  today's scan ran: signal_scan_<today>.md exists and was written today;
    2  every settled resolution session is filled (outcome_sanity Check H's
       rule) - i.e. enter_closes ran tonight, and on every evening before;
    3  the previous cohort session's value.bat ran: value_card_<prev>.md;
    4  the previous review's step-7 refresh happened: the current report copy
       carries cached K (Return +5d) values. A copy that was never opened in
       Excel holds none, because openpyxl saves blank every formula cache.

USAGE
    python chain_check.py [--tracker logs\\claude_equity_bot_tracker.xlsx]
                          [--report tracker_with_registry.xlsx] [--today D]

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import os
import sys


def cached_k(report):
    """(numeric cached K cells, data rows) on the report copy's Signals tab."""
    import openpyxl
    wb = openpyxl.load_workbook(report, data_only=True, read_only=True)
    ws = wb["Signals"]
    n_k = n_rows = 0
    for row in ws.iter_rows(min_row=5, max_col=11, values_only=True):
        if row and isinstance(row[0], dt.datetime):
            n_rows += 1
            if isinstance(row[10], (int, float)) and not isinstance(row[10], bool):
                n_k += 1
    wb.close()
    return n_k, n_rows


def run(tracker, report, today, root="."):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import outcome_sanity as osn
    import trading_calendar as cal
    warns, notes = [], []

    # 1 - today's scan
    scan_md = os.path.join(root, "signal_scan_%s.md" % today.isoformat())
    if not os.path.exists(scan_md):
        warns.append("[1] no %s - run scan.bat (after the paste and enter_closes) "
                     "BEFORE this review." % os.path.basename(scan_md))
    else:
        m = dt.date.fromtimestamp(os.path.getmtime(scan_md))
        if m != today:
            warns.append("[1] %s was written %s, not today." % (os.path.basename(scan_md), m))
        else:
            notes.append("[1] today's scan ran (%s)." % os.path.basename(scan_md))

    # 2 - closes entered for every settled session
    rows = osn.load(tracker)
    try:
        from repair_outcome_close import market_settled
        settled = today if (cal.is_trading_day(today) and market_settled(today)[0]) \
            else cal.prior_session(today)
    except Exception:                                   # noqa: BLE001
        settled = cal.prior_session(today)
    due, _nopx = osn.due_but_blank(rows, cal.shift_sessions, settled)
    if due:
        warns.append("[2] blank closes on settled session(s) %s (%d cells) - run "
                     "python enter_closes.py --catch-up, then scan.bat, then this review."
                     % (", ".join(str(d) for d in sorted(due)), sum(len(v) for v in due.values())))
    else:
        notes.append("[2] every settled session through %s is filled." % settled)

    # 3 - the previous cohort session's value.bat
    cohorts = sorted({r["date"] for r in rows if r["date"] < today})
    prev = cohorts[-1] if cohorts else None
    if prev is not None:
        card = os.path.join(root, "value_card_%s.md" % prev.isoformat())
        if os.path.exists(card):
            notes.append("[3] value.bat ran for %s (%s)." % (prev, os.path.basename(card)))
        else:
            warns.append("[3] no %s - value.bat did not run for %s. It cannot be run "
                         "for a past session once a newer cohort is pasted (its paste "
                         "guard refuses), so record the gap in this review."
                         % (os.path.basename(card), prev))

    # 4 - the previous review's step-7 Excel refresh
    if os.path.exists(report):
        try:
            n_k, n_rows = cached_k(report)
            when = dt.datetime.fromtimestamp(os.path.getmtime(report)).strftime("%Y-%m-%d %H:%M")
            if n_rows and n_k == 0:
                warns.append("[4] the report copy (saved %s) holds cached returns on 0 of %d "
                             "rows: the step-7 refresh (open in Excel, let it recalculate, "
                             "save, close) did not happen after the last review." % (when, n_rows))
            else:
                notes.append("[4] report copy (saved %s) carries cached returns on %d of %d rows."
                             % (when, n_k, n_rows))
        except Exception as e:                          # noqa: BLE001
            warns.append("[4] could not read %s (%s) - is it open in Excel?" % (report, e))
    else:
        notes.append("[4] no report copy yet; this review creates it.")
    return warns, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evening-chain order check (DP-3C-ba).")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--report", default="tracker_with_registry.xlsx")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=None)
    a = ap.parse_args(argv)
    if os.path.basename(a.tracker).lower() == "tracker_with_registry.xlsx":
        print("REFUSED: pass THE MASTER as --tracker; the report copy is --report.")
        return 2
    today = a.today or dt.date.today()
    try:
        warns, notes = run(a.tracker, a.report, today)
    except Exception as e:                              # noqa: BLE001
        print("CHAIN CHECK COULD NOT RUN: %s" % e)
        return 2
    print("CHAIN CHECK - %s (DP-3C-ba)" % today)
    for n in notes:
        print("  " + n)
    for w in warns:
        print("  WARN " + w)
    print("  -> %s" % ("CHAIN IN ORDER" if not warns else
                       "%d WARNING(S) - fix the chain, or record why, before reading "
                       "this review" % len(warns)))
    return 1 if warns else 0


if __name__ == "__main__":
    sys.exit(main())
