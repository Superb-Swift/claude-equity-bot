#!/usr/bin/env python3
"""
earnings_calendar.py - the next scheduled earnings date per watchlist name
(value layer V5; gap #9 as a REPORTING covariate).

WHY THIS EXISTS (DailySequence 2026-10-09, V5; OutcomesReview gap #9)
    No forward earnings input exists anywhere in the stack [V, 2026-10-09]:
    E4 looks only backward (filings already made), and WMT fell 9.2% on its
    own 8-K session. Knowing that a report lands inside the next five
    sessions is event risk the decision card should carry beside the value
    class. Finnhub, already in the stack for headlines, publishes the
    calendar.

DISCIPLINE (DP-V1; DP-3C-ai)
    Reporting only. Nothing here reaches the prompt, the risk engine, an
    endpoint, a gate or the paste. Putting the calendar INTO the prompt is a
    Phase 4b change with its own pre-registration (DP-3C-bc).

OUTPUT
    earnings_calendar_<date>.md / .json: per name, the next report date in the
    next --days calendar days, the NYSE sessions until it (trading_calendar),
    and INSIDE 5 SESSIONS when it is close. Funds read "n/a (fund)"; a name
    with no date in the window reads "none scheduled in window", never a guess.

USAGE
    python earnings_calendar.py [--date 2026-10-22] [--days 60]
    python earnings_calendar.py --tickers UNH,O  (names outside the run, written to
        earnings_calendar_<date>_adhoc.*; the value card's input is untouched;
        added 2026-10-23)
    python earnings_calendar.py --selftest      (offline, a fake client)

Exit 0 written; 2 could not run.
Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
import time

FLAG_SESSIONS = 5
_TK = re.compile(r'Signal JSON: \{"ticker": "([A-Z][A-Z.\-]*)"')
_LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")


def universe(log_dir="logs"):
    logs = sorted((m.group(1), p) for p in glob.glob(os.path.join(log_dir, "signals_*.log"))
                  for m in [_LOGDATE.search(os.path.basename(p))] if m)
    if not logs:
        return None, []
    d, p = logs[-1]
    with open(p, encoding="utf-8", errors="replace") as fh:
        return d, sorted({m.group(1) for ln in fh for m in [_TK.search(ln)] if m})


def next_report(client, tk, start, end):
    """(date, hour) of the first scheduled report in [start, end], or (None, why)."""
    try:
        r = client.earnings_calendar(_from=start.isoformat(), to=end.isoformat(),
                                     symbol=tk, international=False)
    except Exception as e:                              # noqa: BLE001
        return None, "fetch failed: %s" % type(e).__name__
    rows = [x for x in (r or {}).get("earningsCalendar", []) if x.get("date")]
    rows = [x for x in rows if start.isoformat() <= x["date"] <= end.isoformat()]
    if not rows:
        return None, "none scheduled in window"
    x = min(rows, key=lambda z: z["date"])
    return dt.date.fromisoformat(x["date"]), (x.get("hour") or "").strip() or "?"


def build(client, tickers, today, days, funds, cal):
    end = today + dt.timedelta(days=days)
    out = []
    for tk in tickers:
        if tk in funds:
            out.append(dict(ticker=tk, date=None, note="n/a (fund)"))
            continue
        d, hour = next_report(client, tk, today, end)
        if d is None:
            out.append(dict(ticker=tk, date=None, note=hour))
            continue
        n = len(cal.sessions_between(today, d)) - 1 if cal.is_trading_day(d) else None
        flag = n is not None and n <= FLAG_SESSIONS
        out.append(dict(ticker=tk, date=d.isoformat(), hour=hour, sessions=n,
                        note=("INSIDE %d SESSIONS" % FLAG_SESSIONS) if flag else ""))
    return out


def render(day, rows):
    L = ["# Earnings calendar (value layer V5) - %s" % day, "",
         "*Finnhub calendar. Reporting only: nothing here reaches the prompt or any gate "
         "(DP-V1). `hour` is Finnhub's bmo (before open) / amc (after close) / dmh.*", "",
         "| Ticker | Next report | Hour | NYSE sessions away | Flag |", "|---|---|---|---:|---|"]
    for r in sorted(rows, key=lambda r: (r["date"] or "9999", r["ticker"])):
        L.append("| %s | %s | %s | %s | %s |" % (
            r["ticker"], r["date"] or "—", r.get("hour", "") or "",
            "" if r.get("sessions") is None else r["sessions"],
            r["note"] if r["date"] else r["note"]))
    L += ["", "*Advisory-only · no orders · not financial advice.*"]
    return "\n".join(L)


def selftest():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import trading_calendar as cal

    class Fake:
        def earnings_calendar(self, _from, to, symbol, international=False):
            data = {"AAA": [{"date": "2026-10-27", "hour": "amc", "symbol": "AAA"}],
                    "BBB": [{"date": "2026-12-01", "hour": "bmo", "symbol": "BBB"}],
                    "CCC": []}
            if symbol == "ERR":
                raise RuntimeError("boom")
            return {"earningsCalendar": data.get(symbol, [])}
    rows = {r["ticker"]: r for r in build(Fake(), ["AAA", "BBB", "CCC", "ERR", "SPY"],
                                          dt.date(2026, 10, 22), 60, {"SPY"}, cal)}
    fails = []
    checks = [("a report 3 sessions out is flagged", rows["AAA"]["note"].startswith("INSIDE")
               and rows["AAA"]["sessions"] == 3),
              ("a report weeks out is listed, not flagged", rows["BBB"]["note"] == ""),
              ("no date in the window says so", rows["CCC"]["note"] == "none scheduled in window"),
              ("a failed fetch is reported, not guessed", rows["ERR"]["note"].startswith("fetch failed")),
              ("a fund reads n/a", rows["SPY"]["note"] == "n/a (fund)")]
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        ok or fails.append(name)
    print("  earnings_calendar selftest: %s" % ("ALL PASS" if not fails else "FAIL"))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Next earnings date per name (V5).")
    ap.add_argument("--date", default=None)
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--quotes", default="quote_dump.json", help="for the fund flag")
    ap.add_argument("--tickers", default=None,
                    help="comma list to read INSTEAD of the latest log's names; written to "
                         "earnings_calendar_<date>_adhoc.* so the value card's input is untouched")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import trading_calendar as cal
    d, tks = universe()
    if a.tickers:
        tks = sorted({t.strip().upper() for t in a.tickers.split(",") if t.strip()})
    if not tks:
        print("EARNINGS CALENDAR COULD NOT RUN: no session log with signal rows.")
        return 2
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    funds = set()
    if os.path.exists(a.quotes):
        with open(a.quotes, encoding="utf-8") as fh:
            funds = {t for t, q in json.load(fh).get("quotes", {}).items() if q.get("is_etf")}
    try:
        import news_client
        client = news_client.get_client()
    except Exception as e:                              # noqa: BLE001
        print("EARNINGS CALENDAR COULD NOT RUN: %s" % e)
        return 2

    class Polite:                                       # Finnhub free tier: 60 calls/min
        def earnings_calendar(self, **kw):
            time.sleep(1.1)
            return client.earnings_calendar(**kw)
    rows = build(Polite(), tks, day, a.days, funds, cal)
    md = render(day, rows)
    stem = ("earnings_calendar_%s_adhoc" if a.tickers else "earnings_calendar_%s") % day
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print(md)
    print("\nWrote: %s.md (%d names; %d inside %d sessions)"
          % (stem, len(rows), sum(1 for r in rows if r["note"].startswith("INSIDE")), FLAG_SESSIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
