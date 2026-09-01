#!/usr/bin/env python3
"""
fetch_closes.py — pull settled closes for ONE date across many tickers, to TSV.

WHY THIS EXISTS
---------------
`repair_outcome_close.py` sources one ticker at a time and writes to the master.
Adjudicating a Check F candidate needs the opposite: many tickers, one date,
writing NOTHING — a third column to set beside the master's cell and the log's
H1 channel, so a disagreement can be settled instead of argued.

The 2026-08-20 case is the worked example. Master and log agree to the penny on
25 of 26 names that day and disagree on exactly one (GM, 85.75 vs 86.15). That
pattern already argues against a corporate-action adjustment — an adjustment is
a property of the FEED, and this feed agrees with the master everywhere else on
the same date — but "argues against" is not "settled". This closes it.

DISCIPLINE
----------
  * WRITES NOTHING except the TSV you name. Never touches a workbook.
  * Refuses to source an UNSETTLED session, reusing `repair_outcome_close`'s own
    `market_settled()` so there is one rule, not two. `--force` overrides.
  * Prints to stdout by default so it can be piped or pasted.

Usage:
    python fetch_closes.py --date 2026-08-20
    python fetch_closes.py --date 2026-08-20 --out closes_2026-08-20.tsv
    python fetch_closes.py --date 2026-08-20 --tickers GM,PWR,NKE

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

DEFAULT_TICKERS = ["AAPL", "AG", "AIQ", "CBRS", "CORN", "DOW", "FTI", "GLD", "GM",
                   "JPM", "MSFT", "NKE", "NTR", "NVDA", "PM", "PWR", "QQQ", "RTX",
                   "SCHD", "SND", "SPCX", "SPY", "USO", "VTI", "WMT", "XLU"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Settled closes for one date, many tickers.")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    ap.add_argument("--out", default=None, help="write TSV here as well as stdout")
    ap.add_argument("--force", action="store_true",
                    help="source even if the session is not settled (do not)")
    a = ap.parse_args()

    try:
        target = dt.date.fromisoformat(a.date)
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 2

    try:
        from trading_calendar import is_trading_day
        if not is_trading_day(target):
            print("ERROR: %s is not an NYSE session." % target, file=sys.stderr)
            return 2
    except ImportError:
        print("[warn] trading_calendar.py not importable - session check skipped.",
              file=sys.stderr)

    # One settlement rule for the project, not two.
    try:
        from repair_outcome_close import market_settled
        ok, why = market_settled(target)      # returns (settled_bool, explanation)
        if ok is False and not a.force:
            print("ERROR: %s is not settled yet (%s). Sourcing a close from a "
                  "running session returns the last print, not the close."
                  % (target, why), file=sys.stderr)
            print("       Wait for 16:15 ET, or pass --force if you know what you "
                  "are doing.", file=sys.stderr)
            return 2
        if ok is None:
            print("[warn] settlement could not be determined (%s) - check the date "
                  "yourself." % why, file=sys.stderr)
    except Exception as e:
        print("[warn] settlement guard unavailable (%s) - check the date yourself." % e,
              file=sys.stderr)

    try:
        from schwab_client import get_price_history
    except Exception as e:
        print("ERROR: could not import schwab_client: %s" % e, file=sys.stderr)
        return 2

    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    lines = ["date\tticker\tclose\tsource"]
    misses = []
    for tk in tickers:
        try:
            # Ask for a generous window and pick the exact date out of it, rather
            # than trusting the tail slice: the window itself is the thing the H1
            # ruling is about, and this tool must not inherit that assumption.
            hist = get_price_history(tk, days=40) or []
        except Exception as e:
            misses.append((tk, "fetch failed: %s" % e))
            continue
        hit = next((c for c in hist if c.get("date") == target.isoformat()), None)
        if hit is None:
            misses.append((tk, "no candle dated %s in the returned window" % target))
            continue
        lines.append("%s\t%s\t%s\tschwab" % (target, tk, hit["close"]))

    out = "\n".join(lines)
    print(out)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        print("\n[wrote] %s" % a.out, file=sys.stderr)

    if misses:
        print("\n%d ticker(s) returned nothing for %s:" % (len(misses), target),
              file=sys.stderr)
        for tk, why in misses:
            print("    %-6s %s" % (tk, why), file=sys.stderr)
        print("  NOTE: while the H1 window defect is unfixed, candle dates are one\n"
              "  day early, so an exact-date match can miss. If every ticker misses,\n"
              "  that is the defect, not a bad date -- see\n"
              "  H1_Window_OffByOne_Defect_2026-08-26.md.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
