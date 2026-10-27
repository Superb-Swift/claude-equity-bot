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

EXPECTATIONS (added 2026-10-24, DP-V4; the value card's panel 3)
    The calendar row Finnhub already returns carries the consensus for that
    report (epsEstimate, revenueEstimate, fiscal quarter and year); until today
    only the date was kept. Finnhub's earnings-surprise endpoint adds the last
    four reported quarters (actual against estimate). ALL OF IT IS ADJUSTED
    (non-GAAP) and an opinion, so it is kept on its own basis and never mixed
    into the SEC figures:
      beats         reported quarters, of the last four, above the estimate
      adj_ttm       the four adjusted actuals summed
      adj_ttm_if_met  adj_ttm - the same fiscal quarter a year earlier + the
                    consensus: what the adjusted 12-month EPS becomes if the
                    next report meets it
    Context only (DP-V1): nothing here reaches the class, the DP-V2 ledger,
    the prompt or a gate.

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


def _next_row(client, tk, start, end):
    """(Finnhub's calendar row for the first report in [start, end], None) or (None, why)."""
    try:
        r = client.earnings_calendar(_from=start.isoformat(), to=end.isoformat(),
                                     symbol=tk, international=False)
    except Exception as e:                              # noqa: BLE001
        return None, "fetch failed: %s" % type(e).__name__
    rows = [x for x in (r or {}).get("earningsCalendar", []) if x.get("date")]
    rows = [x for x in rows if start.isoformat() <= x["date"] <= end.isoformat()]
    if not rows:
        return None, "none scheduled in window"
    return min(rows, key=lambda z: z["date"]), None


def next_report(client, tk, start, end):
    """(date, hour) of the first scheduled report in [start, end], or (None, why)."""
    x, why = _next_row(client, tk, start, end)
    if x is None:
        return None, why
    return dt.date.fromisoformat(x["date"]), (x.get("hour") or "").strip() or "?"


def estimate_of(row):
    """The consensus on a calendar row (added 2026-10-24: the row always carried
    it; only the date was kept). {} when there is no row."""
    if not row:
        return {}
    return dict(eps_estimate=row.get("epsEstimate"), revenue_estimate=row.get("revenueEstimate"),
                fiscal_quarter=row.get("quarter"), fiscal_year=row.get("year"))


def surprises(client, tk, n=4):
    """([dict(period, fiscal_year, fiscal_quarter, actual, estimate, surprise_pct)],
    None) for the last n reported quarters, newest first, or (None, why).
    Finnhub's earnings-surprise figures are ADJUSTED (non-GAAP)."""
    try:
        r = client.company_earnings(tk, limit=n)
    except Exception as e:                              # noqa: BLE001
        return None, "surprise history fetch failed: %s" % type(e).__name__
    rows = [dict(period=x.get("period"), fiscal_year=x.get("year"), fiscal_quarter=x.get("quarter"),
                 actual=x.get("actual"), estimate=x.get("estimate"),
                 surprise_pct=x.get("surprisePercent"))
            for x in (r or []) if isinstance(x, dict) and x.get("period")]
    rows.sort(key=lambda h: h["period"], reverse=True)
    return rows[:n], None


def expectations(est, hist):
    """Consensus beside the last four quarters, all on Finnhub's adjusted basis.
    dict(eps_estimate, beats, reported, adj_ttm, adj_ttm_if_met, chg_if_met, why)."""
    out = dict(eps_estimate=(est or {}).get("eps_estimate"), beats=None, reported=0,
               adj_ttm=None, adj_ttm_if_met=None, chg_if_met=None, why=None)
    acts = [h for h in (hist or []) if h.get("actual") is not None]
    out["reported"] = len(acts)
    if acts:
        out["beats"] = sum(1 for h in acts if h.get("estimate") is not None
                           and h["actual"] > h["estimate"])
    if len(acts) >= 4:
        out["adj_ttm"] = sum(h["actual"] for h in acts[:4])
    e, fq, fy = out["eps_estimate"], (est or {}).get("fiscal_quarter"), (est or {}).get("fiscal_year")
    if e is None:
        out["why"] = "no consensus for the next report"
        return out
    yago = [h for h in acts[:4] if fq is not None and fy is not None
            and h.get("fiscal_quarter") == fq and h.get("fiscal_year") == fy - 1]
    if out["adj_ttm"] is None or not yago:
        out["why"] = ("fewer than four reported quarters" if out["adj_ttm"] is None
                      else "the same quarter a year earlier is not among the last four")
        return out
    out["adj_ttm_if_met"] = out["adj_ttm"] - yago[0]["actual"] + e
    if out["adj_ttm"] > 0:
        out["chg_if_met"] = out["adj_ttm_if_met"] / out["adj_ttm"] - 1.0
    return out


def build(client, tickers, today, days, funds, cal):
    end = today + dt.timedelta(days=days)
    out = []
    for tk in tickers:
        if tk in funds:
            out.append(dict(ticker=tk, date=None, note="n/a (fund)"))
            continue
        row, why = _next_row(client, tk, today, end)
        d = dt.date.fromisoformat(row["date"]) if row else None
        hour = ((row.get("hour") or "").strip() or "?") if row else why
        hist, hwhy = surprises(client, tk)
        est = estimate_of(row)
        exp = dict(expectations(est, hist), history=hist, history_why=hwhy,
                   revenue_estimate=est.get("revenue_estimate"),
                   fiscal_quarter=est.get("fiscal_quarter"), fiscal_year=est.get("fiscal_year"),
                   basis="Finnhub, adjusted (non-GAAP)")
        if d is None:
            out.append(dict(ticker=tk, date=None, note=hour, expectations=exp))
            continue
        n = len(cal.sessions_between(today, d)) - 1 if cal.is_trading_day(d) else None
        flag = n is not None and n <= FLAG_SESSIONS
        out.append(dict(ticker=tk, date=d.isoformat(), hour=hour, sessions=n,
                        note=("INSIDE %d SESSIONS" % FLAG_SESSIONS) if flag else "",
                        expectations=exp))
    return out


def render(day, rows):
    L = ["# Earnings calendar (value layer V5) - %s" % day, "",
         "*Finnhub calendar. Reporting only: nothing here reaches the prompt or any gate "
         "(DP-V1). `hour` is Finnhub's bmo (before open) / amc (after close) / dmh.*", "",
         "| Ticker | Next report | Hour | NYSE sessions away | Flag | Consensus EPS (adj.) "
         "| Beat estimate, last 4 | Adj. 12-month EPS | If consensus is met |",
         "|---|---|---|---:|---|---:|---:|---:|---|"]

    def num(v):
        return "—" if v is None else "%.2f" % v
    for r in sorted(rows, key=lambda r: (r["date"] or "9999", r["ticker"])):
        e = r.get("expectations") or {}
        met = ("%s (%+.1f%%)" % (num(e.get("adj_ttm_if_met")), 100 * e["chg_if_met"])
               if e.get("chg_if_met") is not None else
               (num(e.get("adj_ttm_if_met")) if e.get("adj_ttm_if_met") is not None
                else (e.get("why") or e.get("history_why") or "—")))
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["ticker"], r["date"] or "—", r.get("hour", "") or "",
            "" if r.get("sessions") is None else r["sessions"],
            r["note"] if r["date"] else r["note"], num(e.get("eps_estimate")),
            ("%d of %d" % (e["beats"], e["reported"])) if e.get("beats") is not None else "—",
            num(e.get("adj_ttm")), met))
    L += ["", "*Consensus, actuals and surprises are Finnhub's ADJUSTED (non-GAAP) figures, on "
          "their own basis: they are never mixed into the SEC (GAAP) 12-month figures, the "
          "class or the DP-V2 ledger. 'If consensus is met' = adjusted 12-month EPS minus the "
          "same fiscal quarter a year earlier plus the estimate.*",
          "", "*Advisory-only · no orders · not financial advice.*"]
    return "\n".join(L)


def selftest():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import trading_calendar as cal

    class Fake:
        def earnings_calendar(self, _from, to, symbol, international=False):
            data = {"AAA": [{"date": "2026-10-27", "hour": "amc", "symbol": "AAA",
                             "epsEstimate": 1.30, "revenueEstimate": 9.0e9,
                             "quarter": 3, "year": 2026}],
                    "BBB": [{"date": "2026-12-01", "hour": "bmo", "symbol": "BBB",
                             "epsEstimate": 0.50, "quarter": 4, "year": 2026}],
                    "CCC": []}
            if symbol == "ERR":
                raise RuntimeError("boom")
            return {"earningsCalendar": data.get(symbol, [])}

        def company_earnings(self, symbol, limit=4):
            if symbol == "BBB":
                raise RuntimeError("premium")
            return {"AAA": [
                {"period": "2026-06-30", "year": 2026, "quarter": 2, "actual": 1.25, "estimate": 1.20},
                {"period": "2026-03-31", "year": 2026, "quarter": 1, "actual": 1.20, "estimate": 1.22},
                {"period": "2025-12-31", "year": 2025, "quarter": 4, "actual": 1.10, "estimate": 1.00},
                {"period": "2025-09-30", "year": 2025, "quarter": 3, "actual": 1.00, "estimate": 0.95}],
                    }.get(symbol, [])
    rows = {r["ticker"]: r for r in build(Fake(), ["AAA", "BBB", "CCC", "ERR", "SPY"],
                                          dt.date(2026, 10, 22), 60, {"SPY"}, cal)}
    fails = []
    checks = [("a report 3 sessions out is flagged", rows["AAA"]["note"].startswith("INSIDE")
               and rows["AAA"]["sessions"] == 3),
              ("a report weeks out is listed, not flagged", rows["BBB"]["note"] == ""),
              ("no date in the window says so", rows["CCC"]["note"] == "none scheduled in window"),
              ("a failed fetch is reported, not guessed", rows["ERR"]["note"].startswith("fetch failed")),
              ("a fund reads n/a", rows["SPY"]["note"] == "n/a (fund)")]
    ea = rows["AAA"]["expectations"]
    checks += [("the consensus on the calendar row is kept (it was fetched and dropped before)",
                ea["eps_estimate"] == 1.30 and ea["fiscal_quarter"] == 3),
               ("beats: 3 of the last 4 above the estimate", ea["beats"] == 3 and ea["reported"] == 4),
               ("if met: 4.55 - Q3 a year earlier (1.00) + 1.30 = 4.85, +6.6%",
                abs(ea["adj_ttm"] - 4.55) < 1e-9 and abs(ea["adj_ttm_if_met"] - 4.85) < 1e-9
                and abs(ea["chg_if_met"] - (4.85 / 4.55 - 1)) < 1e-12),
               ("NEGATIVE: a failed surprise fetch keeps the date and says why, no projection",
                rows["BBB"]["date"] == "2026-12-01"
                and rows["BBB"]["expectations"]["adj_ttm_if_met"] is None
                and "fetch failed" in (rows["BBB"]["expectations"]["history_why"] or "")),
               ("the basis is labelled adjusted (non-GAAP)", "non-GAAP" in ea["basis"])]
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        ok or fails.append(name)
    print("  earnings_calendar selftest: %s" % ("ALL PASS" if not fails else "FAIL"))
    return 1 if fails else 0


def _main(argv=None):
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

        def company_earnings(self, symbol, limit=4):    # added 2026-10-24 (DP-V4 panel 3)
            time.sleep(1.1)
            return client.company_earnings(symbol, limit=limit)
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


def main(argv=None):
    """_main with two guards (2026-10-27): a redirected console loses a
    character instead of the run, and an unexpected error exits 2 ('could not
    run') with its reason, never a bare traceback whose exit 1 value.bat could
    misread (the sec_data_audit defect of 2026-10-27)."""
    try:
        sys.stdout.reconfigure(errors="replace")     # cp1252 when redirected
    except Exception:                                   # noqa: BLE001
        pass
    try:
        return _main(argv)
    except Exception as e:                              # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("EARNINGS CALENDAR COULD NOT RUN: %s: %s" % (type(e).__name__, e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
