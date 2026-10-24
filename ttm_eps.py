#!/usr/bin/env python3
"""
ttm_eps.py - trailing-twelve-month EPS, net income and ROE for the watchlist,
from SEC companyfacts, in a SEPARATE valuation cache (value layer V2).

WHY THIS EXISTS (DailySequence 2026-10-09 section 3.2, V2; the 2026-10-21
review: "it hears 10-Q book-value anchors; what it still cannot hear is TTM
EPS")
    Neither ROE basis in implied_return / value_card is TTM: the numerator is
    1.1 to 4.1 quarters old, and GM's was overstated about 1.5x [R]. The TTM
    rebuild was deferred because changing EXTRACT_SCHEMA would change what the
    model sees. A separate fetch into a separate cache does not: nothing here
    reaches the prompt, an endpoint, KEEP-70, H4 or the band (DP-V1).

WHAT IT DOES
    * universe = the tickers the latest session log wrote (no list here);
    * for each, the SEC companyfacts JSON, cached in valuation_cache\\ (never
      edgar_cache\\) and re-fetched when older than --max-age-days;
    * TTM diluted EPS = the latest four consecutive 3-month quarters, with a
      missing fiscal Q4 derived as FY minus Q1..Q3 (the usual 10-K case);
      the same for net income; equity = the latest StockholdersEquity;
    * TTM ROE = TTM net income / latest equity; TTM P/E from quote_dump.json;
    * funds and names with no companyfacts are listed as NO READ, never zero.

    AMENDED 2026-10-23, after the first live run (2026-10-22):
    * Each figure reads the FRESHEST candidate tag, not the first one with any
      data. SNOW stopped reporting StockholdersEquity after 2026-01-31 and
      reports only the line including noncontrolling interest since, so the
      first-tag rule set a January equity against a July TTM.
    * A TTM whose last quarter ended more than STALE_DAYS before the run date
      is flagged STALE (DOW's companyfacts end at 2026-03-31 on 2026-10-22).
    * Equity at or below zero gives no ROE ("negative equity: ROE not
      meaningful"), never a negative percentage (BBWI, PM).
    * An equity date that predates the TTM end is flagged; one older than
      EQUITY_MAX_AGE_DAYS is not read (PAA's StockholdersEquity ends 2017).
    * The slim cache records the filer's taxonomies, so an IFRS filer reads
      "IFRS filer" rather than "no EPS tag" (NTR; DP-3C-f). A cache written
      before this version is re-fetched once.
    * --tickers reads names the bot does not run, into ttm_eps_<date>_adhoc.*,
      so the value card's same-date input is never overwritten.

    REPORTING ONLY. The value card's class still reads its own ROE basis; this
    exhibit sits beside it. Wiring TTM into the class is a separate change and
    would need its own ruling (it moves DP-V2's counterfactual ledger).

    Summed quarterly diluted EPS approximates annual diluted EPS; share counts
    move between quarters, so the two can differ by a cent or two.

USAGE
    python ttm_eps.py [--date 2026-10-22] [--quotes quote_dump.json]
    python ttm_eps.py --tickers UNH,O      (names outside the run; adds nothing to it)
    python ttm_eps.py --selftest          (offline, fixture data)

Exit 0 written; 1 written with NO READ names; 2 could not run.
Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

CACHE_DIR = "valuation_cache"
EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
            "EarningsPerShareBasic")
NI_TAGS = ("NetIncomeLoss", "ProfitLoss")
EQ_TAGS = ("StockholdersEquity",
           "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")
_TK = re.compile(r'Signal JSON: \{"ticker": "([A-Z][A-Z.\-]*)"')
_LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")
# A 10-Q is due 40-45 days after its quarter ends, so a TTM whose last quarter
# ended more than 90 + 45 days ago has missed at least one filing.
STALE_DAYS = 135
# 2: the slim cache records the filer's taxonomies (2026-10-23). A cache file
# without this version is re-fetched once.
SLIM_VERSION = 2
# An equity figure older than this is not read at all (PAA's tag ends 2017).
EQUITY_MAX_AGE_DAYS = 400


def _d(s):
    return dt.date.fromisoformat(s)


def _facts(cf, tags, unit_hint):
    """(tag, [facts]) for the candidate tag whose LATEST fact is the most
    recent; a tie goes to the earlier tag in `tags` (the preference order).

    AMENDED 2026-10-23: this took the FIRST tag that carried any data. A filer
    that switches tags (SNOW's equity, after 2026-01-31) then reads stale."""
    gaap = (cf or {}).get("facts", {}).get("us-gaap", {})
    best = None
    for i, t in enumerate(tags):
        units = gaap.get(t, {}).get("units", {})
        for u, rows in units.items():
            if unit_hint in u and rows:
                key = (max((r.get("end", "") for r in rows), default=""), -i)
                if best is None or key > best[0]:
                    best = (key, t, rows)
    return (best[1], best[2]) if best else (None, [])


def _durations(rows):
    """{(start, end): (val, filed)} keeping the latest-filed value."""
    out = {}
    for r in rows:
        if "start" not in r or "end" not in r or r.get("val") is None:
            continue
        k = (_d(r["start"]), _d(r["end"]))
        filed = r.get("filed", "")
        if k not in out or filed > out[k][1]:
            out[k] = (float(r["val"]), filed)
    return out


def ttm(rows):
    """TTM sum from duration facts. Returns (value, detail, last_quarter_end);
    (None, why, None) when four consecutive quarters are not there."""
    dur = _durations(rows)
    q = {k: v[0] for k, v in dur.items() if 80 <= (k[1] - k[0]).days <= 100}
    fy = {k: v[0] for k, v in dur.items() if 350 <= (k[1] - k[0]).days <= 380}
    # derive a missing fiscal Q4 = FY - (the three quarters inside it)
    for (s, e), v in fy.items():
        inside = sorted((k for k in q if k[0] >= s and k[1] <= e), key=lambda k: k[1])
        if len(inside) == 3 and not any(abs((k[1] - e).days) <= 7 for k in inside):
            q[(inside[-1][1] + dt.timedelta(days=1), e)] = v - sum(q[k] for k in inside)
    if not q:
        return None, "no quarterly facts", None
    ends = sorted(q, key=lambda k: k[1])
    last = ends[-1]
    chain = [last]
    for _ in range(3):
        prev_end = chain[-1][0] - dt.timedelta(days=1)
        cand = [k for k in ends if abs((k[1] - prev_end).days) <= 10]
        if not cand:
            return None, "gap before the quarter ending %s" % chain[-1][1], None
        chain.append(max(cand, key=lambda k: k[1]))
    return sum(q[k] for k in chain), "quarters ending %s" % ", ".join(
        str(k[1]) for k in reversed(chain)), last[1]


def latest_instant(rows):
    best = None
    for r in rows:
        if "end" in r and "start" not in r and r.get("val") is not None:
            k = (r["end"], r.get("filed", ""))
            if best is None or k > best[0]:
                best = (k, float(r["val"]))
    return (best[1], best[0][0]) if best else (None, None)


def _why_no_eps(cf):
    if "ifrs-full" in ((cf or {}).get("taxonomies") or []):
        return "IFRS filer (ifrs-full facts; only us-gaap is read - DP-3C-f)"
    return "no EPS tag"


def read_name(cf, today=None):
    """TTM figures for one filer. `today` (a date) enables the STALE flag."""
    eps_tag, eps_rows = _facts(cf, EPS_TAGS, "USD/shares")
    ni_tag, ni_rows = _facts(cf, NI_TAGS, "USD")
    eq_tag, eq_rows = _facts(cf, EQ_TAGS, "USD")
    eps, eps_why, eps_end = ttm(eps_rows) if eps_rows else (None, _why_no_eps(cf), None)
    ni, ni_why, _ = ttm(ni_rows) if ni_rows else (None, "no net-income tag", None)
    eq, eq_end = latest_instant(eq_rows) if eq_rows else (None, None)
    flags = []
    if eq is not None and eq_end and today and (today - _d(eq_end)).days > EQUITY_MAX_AGE_DAYS:
        # PAA: StockholdersEquity was last reported 2017-09-30 (an MLP reports
        # partners' capital); a figure that old is not an equity, it is history.
        flags.append("equity tag last reported %s: not read" % eq_end)
        eq = None
    if eps_end and today and (today - eps_end).days > STALE_DAYS:
        flags.append("STALE: last quarter ends %s, %d days before %s"
                     % (eps_end, (today - eps_end).days, today))
    if eq is not None and eq_end and eps_end and _d(eq_end) < eps_end - dt.timedelta(days=10):
        flags.append("equity as of %s predates the TTM end %s" % (eq_end, eps_end))
    roe = None
    if ni is not None and eq is not None:
        if eq > 0:
            roe = ni / eq
        else:
            flags.append("negative equity: ROE not meaningful")
    return dict(eps_ttm=eps, eps_basis=eps_why, eps_tag=eps_tag,
                eps_end=str(eps_end) if eps_end else None, ni_ttm=ni, ni_basis=ni_why,
                equity=eq, equity_end=eq_end, equity_tag=eq_tag, roe_ttm=roe, flags=flags,
                stale=any(f.startswith("STALE") for f in flags))


def universe(log_dir="logs"):
    logs = sorted((m.group(1), p) for p in glob.glob(os.path.join(log_dir, "signals_*.log"))
                  for m in [_LOGDATE.search(os.path.basename(p))] if m)
    if not logs:
        return None, []
    d, p = logs[-1]
    with open(p, encoding="utf-8", errors="replace") as fh:
        return d, sorted({m.group(1) for ln in fh for m in [_TK.search(ln)] if m})


def fetch(tk, cik_map, max_age_days):
    import edgar_client as ec
    cik = cik_map.get(tk)
    if not cik:
        return None, "no CIK (fund, or not an SEC registrant)"
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "companyfacts_%s.json" % cik)
    if os.path.exists(path):
        age = (dt.datetime.now().timestamp() - os.path.getmtime(path)) / 86400.0
        if age <= max_age_days:
            with open(path, encoding="utf-8") as fh:
                cached = json.load(fh)
            if cached.get("slim_version") == SLIM_VERSION:
                return cached, "cache (%.1f d old)" % age
    cf = ec._http_get(ec.XBRL_FACTS_URL.format(cik10=cik), as_json=True)
    if not cf:
        return None, "companyfacts fetch failed (%s)" % (ec._last_fetch.get("reason") or "?")
    # Keep only the tags this exhibit reads: a full companyfacts file runs to
    # megabytes, the slice to kilobytes.
    gaap = cf.get("facts", {}).get("us-gaap", {})
    slim = {"cik": cf.get("cik"), "entityName": cf.get("entityName"),
            "slim_version": SLIM_VERSION, "taxonomies": sorted(cf.get("facts", {}).keys()),
            "facts": {"us-gaap": {t: gaap[t] for t in EPS_TAGS + NI_TAGS + EQ_TAGS if t in gaap}}}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(slim, fh)
    return slim, "fetched"


def render(day, rows, quotes):
    L = ["# TTM EPS and ROE (value layer V2) - %s" % day, "",
         "*SEC companyfacts in a separate `valuation_cache\\`; nothing here reaches the "
         "prompt, an endpoint or a gate (DP-V1). Reporting only: the value card's class "
         "keeps its own ROE basis.*", "",
         "| Ticker | TTM EPS | TTM P/E | TTM net income | Equity (as of) | TTM ROE | Basis | Source |",
         "|---|---:|---:|---:|---|---:|---|---|"]
    for tk, r in rows:
        if r.get("no_read"):
            L.append("| %s | NO READ | | | | | %s | |" % (tk, r["no_read"]))
            continue
        px = (quotes.get(tk) or {}).get("lastPrice")
        pe = (px / r["eps_ttm"]) if (px and r["eps_ttm"] and r["eps_ttm"] > 0) else None
        nci = " incl. NCI" if (r.get("equity_tag") or "").endswith("NoncontrollingInterest") else ""
        neg = any(f.startswith("negative equity") for f in r.get("flags") or [])
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            tk, "%.2f" % r["eps_ttm"] if r["eps_ttm"] is not None else "—",
            "%.1f" % pe if pe else "—",
            "%.0f M" % (r["ni_ttm"] / 1e6) if r["ni_ttm"] is not None else "—",
            ("%.0f M (%s)%s" % (r["equity"] / 1e6, r["equity_end"], nci))
            if r["equity"] is not None else "—",
            "n/m" if neg else ("%.1f%%" % (r["roe_ttm"] * 100) if r["roe_ttm"] is not None else "—"),
            "; ".join([r["eps_basis"]] + list(r.get("flags") or [])), r.get("source", "")))
    L += ["", "*Advisory-only · no orders · not financial advice.*"]
    return "\n".join(L)


def selftest():
    def f(s, e, v, filed="2026-08-01"):
        return {"start": s, "end": e, "val": v, "filed": filed}
    cf = {"facts": {"us-gaap": {
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            f("2025-01-01", "2025-03-31", 1.0), f("2025-04-01", "2025-06-30", 1.1),
            f("2025-07-01", "2025-09-30", 1.2), f("2025-01-01", "2025-12-31", 4.6),
            f("2026-01-01", "2026-03-31", 1.4), f("2026-04-01", "2026-06-30", 1.5)]}},
        "NetIncomeLoss": {"units": {"USD": [
            f("2025-07-01", "2025-09-30", 120.0), f("2025-01-01", "2025-12-31", 460.0),
            f("2025-01-01", "2025-03-31", 100.0), f("2025-04-01", "2025-06-30", 110.0),
            f("2026-01-01", "2026-03-31", 140.0), f("2026-04-01", "2026-06-30", 150.0)]}},
        "StockholdersEquity": {"units": {"USD": [
            {"end": "2025-12-31", "val": 900.0, "filed": "2026-02-01"},
            {"end": "2026-06-30", "val": 1000.0, "filed": "2026-08-01"}]}}}}}
    fails = []
    r = read_name(cf)
    # Q4 2025 derived = 4.6 - 3.3 = 1.3; TTM = 1.2 + 1.3 + 1.4 + 1.5 = 5.4
    ok = r["eps_ttm"] is not None and abs(r["eps_ttm"] - 5.4) < 1e-9
    print("  [%s] TTM EPS with a derived fiscal Q4 = 5.40 (got %s)" % ("PASS" if ok else "FAIL", r["eps_ttm"]))
    ok or fails.append("eps")
    ok = r["roe_ttm"] is not None and abs(r["roe_ttm"] - 0.54) < 1e-9
    print("  [%s] TTM ROE = 540 / 1000 (got %s)" % ("PASS" if ok else "FAIL", r["roe_ttm"]))
    ok or fails.append("roe")
    gap = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": [
        f("2025-01-01", "2025-03-31", 1.0), f("2026-01-01", "2026-03-31", 1.4)]}}}}}
    g = read_name(gap)
    ok = g["eps_ttm"] is None and "gap" in g["eps_basis"]
    print("  [%s] a gap in the quarters -> no TTM, says why" % ("PASS" if ok else "FAIL"))
    ok or fails.append("gap")
    ok = read_name({})["eps_ttm"] is None
    print("  [%s] no companyfacts -> no figure, never zero" % ("PASS" if ok else "FAIL"))
    ok or fails.append("empty")
    # 2026-10-23 cases, each from the first live run
    sw = json.loads(json.dumps(cf))
    sw["facts"]["us-gaap"]["StockholdersEquity"]["units"]["USD"] = [
        {"end": "2025-12-31", "val": 900.0, "filed": "2026-02-01"}]
    sw["facts"]["us-gaap"]["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"] = {
        "units": {"USD": [{"end": "2026-06-30", "val": 1200.0, "filed": "2026-08-01"}]}}
    s = read_name(sw)
    ok = s["equity_end"] == "2026-06-30" and abs(s["roe_ttm"] - 0.45) < 1e-9 and not s["flags"]
    print("  [%s] a filer that switched equity tags reads the FRESH tag (SNOW case)"
          % ("PASS" if ok else "FAIL")); ok or fails.append("fresh-tag")
    ok = (not read_name(cf, dt.date(2026, 10, 22))["stale"]
          and read_name(cf, dt.date(2026, 11, 13))["stale"])
    print("  [%s] STALE after %d days, not before (DOW case)" % ("PASS" if ok else "FAIL", STALE_DAYS))
    ok or fails.append("stale")
    ng = json.loads(json.dumps(cf))
    ng["facts"]["us-gaap"]["StockholdersEquity"]["units"]["USD"].append(
        {"end": "2026-06-30", "val": -50.0, "filed": "2026-08-02"})
    n = read_name(ng)
    ok = n["roe_ttm"] is None and any(x.startswith("negative equity") for x in n["flags"])
    print("  [%s] negative equity -> no ROE, flagged (BBWI, PM case)" % ("PASS" if ok else "FAIL"))
    ok or fails.append("neg-equity")
    od = json.loads(json.dumps(cf))
    od["facts"]["us-gaap"]["StockholdersEquity"]["units"]["USD"] = [
        {"end": "2025-12-31", "val": 900.0, "filed": "2026-02-01"}]
    ok = any("predates" in x for x in read_name(od)["flags"])
    print("  [%s] an equity date before the TTM end is flagged" % ("PASS" if ok else "FAIL"))
    ok or fails.append("eq-date")
    ok = (read_name(od, dt.date(2027, 3, 1))["equity"] is None
          and read_name(od, dt.date(2026, 10, 22))["equity"] == 900.0)
    print("  [%s] an equity older than %d days is not read (PAA case)"
          % ("PASS" if ok else "FAIL", EQUITY_MAX_AGE_DAYS)); ok or fails.append("eq-age")
    ok = read_name({"taxonomies": ["dei", "ifrs-full"],
                    "facts": {"us-gaap": {}}})["eps_basis"].startswith("IFRS filer")
    print("  [%s] an IFRS filer says so (NTR case)" % ("PASS" if ok else "FAIL"))
    ok or fails.append("ifrs")
    print("  ttm_eps selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="TTM EPS / ROE from SEC companyfacts (V2).")
    ap.add_argument("--date", default=None)
    ap.add_argument("--quotes", default="quote_dump.json")
    ap.add_argument("--max-age-days", type=float, default=7.0)
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--tickers", default=None,
                    help="comma list of names to read INSTEAD of the latest log's; written "
                         "to ttm_eps_<date>_adhoc.* so the value card's input is untouched")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    d, tks = universe()
    if a.tickers:
        tks = sorted({t.strip().upper() for t in a.tickers.split(",") if t.strip()})
        d = d or dt.date.today().isoformat()
    if not tks:
        print("TTM EPS COULD NOT RUN: no session log with signal rows.")
        return 2
    day = a.date or (dt.date.today().isoformat() if a.tickers else d)
    stem = "ttm_eps_%s_adhoc" % day if a.tickers else "ttm_eps_%s" % day
    try:
        import edgar_client as ec
        cik_map = ec.load_cik_map({}) or {}
    except Exception as e:                              # noqa: BLE001
        print("TTM EPS COULD NOT RUN: %s" % e)
        return 2
    quotes = {}
    if os.path.exists(a.quotes):
        with open(a.quotes, encoding="utf-8") as fh:
            quotes = json.load(fh).get("quotes", {})
    rows, no_read = [], 0
    for tk in tks:
        if (quotes.get(tk) or {}).get("is_etf"):
            rows.append((tk, dict(no_read="fund (no EPS)")))
            no_read += 1
            continue
        cf, src = fetch(tk, cik_map, a.max_age_days)
        if not cf:
            rows.append((tk, dict(no_read=src)))
            no_read += 1
            continue
        r = read_name(cf, dt.date.fromisoformat(day))
        r["source"] = src
        if r["eps_ttm"] is None:
            r = dict(no_read="no TTM: " + r["eps_basis"])
            no_read += 1
        rows.append((tk, r))
    md = render(day, rows, quotes)
    md_path = a.md or stem + ".md"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    with open(a.json or stem + ".json", "w", encoding="utf-8") as fh:
        json.dump({tk: r for tk, r in rows}, fh, indent=1, default=str)
    print(md)
    print("\nWrote: %s  (%d name(s), %d NO READ)" % (md_path, len(rows), no_read))
    return 1 if no_read else 0


if __name__ == "__main__":
    sys.exit(main())
