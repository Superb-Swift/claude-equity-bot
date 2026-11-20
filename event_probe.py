#!/usr/bin/env python3
"""
event_probe.py - READ-ONLY. Counts the last 12 months of SEC filings for the
watchlist's operating filers, sorted into the event types step 6 proposes
(FINC-5133 course review, item E1), so step 6's pre-registration can set its
bars from known event rates instead of hopes.

WHY (step 6 of claude/FINC5133_CourseReview_2026-11-18.md; Rob, 2026-11-19)
    Step 6 types corporate actions (equity issue, debt issue, convertible,
    dividend change, buyback, insider purchase or sale) and runs a descriptive
    trace by type. E4-3 read 8-Ks as one undifferentiated class and is CLOSED
    (DP-3C-bb), so the trace is prospective: it can only count events filed
    after its own ruling. Before any bar is written, the question is how often
    each type happens on these 19 names. This probe answers that and nothing
    else. Same pattern as ROIC_Feasibility_2026-10-29 before DP-V6.

WHAT IT READS
    SEC only: company_tickers.json (CIK map), each name's submissions index
    (plus older index pages when the recent block does not reach back 12
    months), and two XBRL company concepts per name. The Form 4 transaction
    codes come from Form 4 XML ALREADY in edgar_cache (no new Form 4 fetch).
    The master is read only for the latest cohort's ticker list (refuses the
    report copy). It reads NO price, NO confidence, NO signal, NO outcome:
    BLIND by construction, like e4_counter.py.

WHAT IT WRITES
    event_probe_<date>.md and event_probe_<date>.json, nothing else. No cache,
    no workbook, no prompt, no gate, no endpoint (DP-V1).

DEFINITIONS - fixed here on 2026-11-19, before the first run
    Window        the 365 calendar days ending on the run date, by acceptance
                  time read in US Eastern.
    Filer         a name with a 10-K, 10-Q, 20-F or 40-F in the window. Others
                  (ETFs, trusts) are NON-FILERS and listed, not counted.
    One event     one accession. An 8-K with two typed items is one filing that
                  counts once under each type it carries.
    8-K types     3.02 EQUITY ISSUE; 2.03 DEBT ISSUE; 2.03 and 3.02 on the same
                  8-K: CONVERTIBLE (candidate) [?]. Context types: 2.02
                  RESULTS, 2.01 M&A, 1.01/1.02 AGREEMENT, 2.04 TRIGGERING
                  EVENT, 2.05 RESTRUCTURING, 2.06 IMPAIRMENT, 3.01 LISTING,
                  3.03 RIGHTS, 4.01 AUDITOR, 4.02 NON-RELIANCE, 5.02
                  MANAGEMENT, 5.03 CHARTER, 5.07 VOTE, 7.01 REG FD, 8.01 OTHER
                  EVENTS (the usual carrier of dividend and buyback news: it is
                  untyped from the index). 9.01 alone: EXHIBITS ONLY. 8-K/A:
                  AMENDMENT, never an event.
    Shelf         424B2/B3/B5/B7: SHELF TAKEDOWN (security type unknown from
                  the index). 424B1/B4: FINAL PROSPECTUS. A name with more than
                  PROGRAM_424B2 (50) 424B2s in the window runs a note program
                  (bank structured notes): its 424B2s are PROGRAM, not
                  takedowns. FWP: OFFERING MATERIAL. S-1/S-3/S-3ASR/F-3:
                  REGISTRATION. S-8: PLAN REGISTRATION (mechanical).
    Dividend      XBRL us-gaap CommonStockDividendsPerShareDeclared (fallback
                  ...CashPaid), quarterly periods only (80-100 days). A CHANGE
                  is a quarter whose value differs from the previous quarter's
                  by more than 0.0005, dated by the FIRST filing that reports
                  it (a lag: the announcement came earlier) [?]. RAISE or CUT.
    Buyback       XBRL us-gaap StockRepurchaseProgramAuthorizedAmount1. An
                  AUTHORIZATION is a reported amount different from the last
                  one, dated by its first filing [?].
    Insider       Form 4 and 4/A filings counted from the index. Codes P
                  (open-market purchase) and S (open-market sale) read from the
                  cached XML only; the cached share is the bot's own 30-day
                  windows since 08-03, so it is a sample, not a census [?].
    Bot session   the first NYSE session whose 10:30 ET signal (09:30 CT) comes
                  after the acceptance. Timing: PRE-OPEN (< 09:30 ET), MARKET
                  HOURS, AFTER CLOSE (>= 16:00 ET), NON-SESSION DAY.
    Time zone     EDGAR's acceptanceDateTime carries a "Z". The probe reads it
                  both ways and keeps the reading under which fewer item-2.02
                  earnings 8-Ks fall in market hours (earnings are released
                  outside them). UNRESOLVED (fewer than 5 earnings 8-Ks, a
                  tie, or both readings above 30%) falls back to Eastern and
                  says so.
    Projection    the trailing-12-month rate per session, carried forward from
                  the next session to the backstop 2027-06-30 (PR-6's).
                  READABLE >= 40 projected; THIN 20-39; NOT BY THE BACKSTOP
                  < 20. CONCENTRATED when one name supplies more than 50%.
                  These are probe labels, NOT the pre-registration's bars.

USAGE (cmd, repo root, venv active, outside the 09:30 window)
    python event_probe.py                     the master's latest cohort
    python event_probe.py --tickers JPM,AAPL  these names only
    python event_probe.py --selftest          offline, fixtures; touches no file
    Exit: 0 ran; 2 could not run (no SEC_USER_AGENT, no CIK map, no names).

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
from collections import Counter, defaultdict

import trading_calendar as TC

PROBE_VERSION = 1
WINDOW_DAYS = 365
BACKSTOP = dt.date(2027, 6, 30)
READABLE_N = 40
THIN_N = 20
CONCENTRATED_SHARE = 0.50
PROGRAM_424B2 = 50
DIV_TOL = 0.0005
QUARTER_DAYS = (80, 100)
BOT_SIGNAL_ET = dt.time(10, 30)          # 09:30 CT
OPEN_ET, CLOSE_ET = dt.time(9, 30), dt.time(16, 0)
TZ_MIN_EARNINGS = 5
TZ_MAX_MARKET_SHARE = 0.30
MASTER_DEFAULT = os.path.join("logs", "claude_equity_bot_tracker.xlsx")
REFUSED = "tracker_with_registry.xlsx"
FIRST_DATA_ROW = 5
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"
CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik10}/us-gaap/{tag}.json"
DIV_TAGS = ("CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid")
BUYBACK_TAG = "StockRepurchaseProgramAuthorizedAmount1"
PERIODIC = {"10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A", "20-F/A", "40-F/A"}
INDEX_KEYS = ("form", "filingDate", "accessionNumber", "primaryDocument", "items",
              "acceptanceDateTime")

# The step-6 candidate types (course E1) and the context types, in print order.
COURSE_TYPES = ("EQUITY ISSUE", "DEBT ISSUE", "CONVERTIBLE (candidate)", "SHELF TAKEDOWN",
                "DIVIDEND CHANGE", "BUYBACK AUTHORIZATION", "INSIDER PURCHASE (cached)",
                "INSIDER SALE (cached)")
ITEM_TYPES = {
    "3.02": "EQUITY ISSUE", "2.03": "DEBT ISSUE", "2.02": "RESULTS", "2.01": "M&A",
    "1.01": "AGREEMENT", "1.02": "AGREEMENT", "2.04": "TRIGGERING EVENT",
    "2.05": "RESTRUCTURING", "2.06": "IMPAIRMENT", "3.01": "LISTING", "3.03": "RIGHTS",
    "4.01": "AUDITOR", "4.02": "NON-RELIANCE", "5.02": "MANAGEMENT", "5.03": "CHARTER",
    "5.07": "VOTE", "7.01": "REG FD", "8.01": "OTHER EVENTS",
}
FORM_TYPES = {
    "424B2": "SHELF TAKEDOWN", "424B3": "SHELF TAKEDOWN", "424B5": "SHELF TAKEDOWN",
    "424B7": "SHELF TAKEDOWN", "424B1": "FINAL PROSPECTUS", "424B4": "FINAL PROSPECTUS",
    "FWP": "OFFERING MATERIAL", "S-1": "REGISTRATION", "S-3": "REGISTRATION",
    "S-3ASR": "REGISTRATION", "F-3": "REGISTRATION", "S-8": "PLAN REGISTRATION",
    "4": "FORM 4", "4/A": "FORM 4",
}
_TXN_CODE_RE = re.compile(r"<transactionCode>\s*([A-Z])\s*</transactionCode>")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                       # pragma: no cover
    ET = dt.timezone(dt.timedelta(hours=-5))


# ============================================================================ index
def zip_block(block):
    """EDGAR's parallel arrays -> one dict per filing."""
    block = block or {}
    forms = block.get("form") or []
    cols = {k: block.get(k) or [""] * len(forms) for k in INDEX_KEYS}
    return [{k: (cols[k][i] if i < len(cols[k]) else "") for k in INDEX_KEYS}
            for i in range(len(forms))]


def all_rows(subs, since, get_page):
    """The recent block plus every older page whose span reaches `since`.
    Dedupes by accession. Returns (rows, coverage)."""
    filings = (subs or {}).get("filings") or {}
    rows = zip_block(filings.get("recent"))
    pages = []
    for f in filings.get("files") or []:
        try:
            to = dt.date.fromisoformat(str(f.get("filingTo")))
        except ValueError:
            continue
        if to >= since:
            pages.append(f.get("name"))
    fetched, failed = 0, 0
    for name in pages:
        js = get_page(SUBMISSIONS_PAGE_URL.format(name=name))
        if js is None:
            failed += 1
            continue
        fetched += 1
        rows += zip_block(js)
    seen, out = set(), []
    for r in rows:
        a = r.get("accessionNumber")
        if a and a not in seen:
            seen.add(a)
            out.append(r)
    dates = [r["filingDate"] for r in out if r.get("filingDate")]
    earliest = min(dates) if dates else None
    complete = failed == 0 and earliest is not None and (
        dt.date.fromisoformat(earliest) <= since or not filings.get("files"))
    return out, {"pages_needed": len(pages), "pages_fetched": fetched, "pages_failed": failed,
                 "earliest_filing": earliest, "complete": bool(complete)}


def parse_accept(s, mode):
    """acceptanceDateTime -> aware Eastern datetime. mode 'ET': the digits are
    Eastern despite the 'Z'; mode 'UTC': they are UTC."""
    if not s:
        return None
    try:
        naive = dt.datetime.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    if mode == "UTC":
        return naive.replace(tzinfo=dt.timezone.utc).astimezone(ET)
    return naive.replace(tzinfo=ET)


def timing(t):
    if t is None:
        return "UNKNOWN"
    if not TC.is_trading_day(t.date()):
        return "NON-SESSION DAY"
    if t.time() < OPEN_ET:
        return "PRE-OPEN"
    if t.time() < CLOSE_ET:
        return "MARKET HOURS"
    return "AFTER CLOSE"


def bot_session(t):
    """The first session whose 10:30 ET signal comes after acceptance `t`."""
    if t is None:
        return None
    d = t.date()
    if TC.is_trading_day(d) and t.time() < BOT_SIGNAL_ET:
        return d
    return TC.next_session(d)


def item_codes(row):
    return [c.strip() for c in str(row.get("items") or "").split(",") if c.strip()]


def tz_check(rows):
    """Pick the acceptanceDateTime reading under which fewer earnings 8-Ks
    (item 2.02) fall in market hours."""
    earn = [r for r in rows if r.get("form") == "8-K" and "2.02" in item_codes(r)]
    share = {}
    for mode in ("ET", "UTC"):
        ts = [parse_accept(r.get("acceptanceDateTime"), mode) for r in earn]
        ts = [t for t in ts if t is not None]
        share[mode] = (sum(1 for t in ts if timing(t) == "MARKET HOURS") / len(ts)) if ts else None
    n = len(earn)
    if n < TZ_MIN_EARNINGS or share["ET"] is None:
        return {"mode": "ET", "status": "UNRESOLVED (fewer than %d earnings 8-Ks)" % TZ_MIN_EARNINGS,
                "n": n, "market_share": share}
    if share["ET"] == share["UTC"]:
        return {"mode": "ET", "status": "UNRESOLVED (both readings agree; the times do not discriminate)",
                "n": n, "market_share": share}
    mode = "ET" if share["ET"] < share["UTC"] else "UTC"
    if share[mode] > TZ_MAX_MARKET_SHARE:
        return {"mode": "ET", "status": "UNRESOLVED (both readings above %.0f%%)" % (100 * TZ_MAX_MARKET_SHARE),
                "n": n, "market_share": share}
    return {"mode": mode, "status": "RESOLVED", "n": n, "market_share": share}


def classify(row, program=False):
    """Types carried by one filing. An empty list = not an event of interest."""
    form = str(row.get("form") or "").strip().upper()
    if form == "8-K":
        codes = item_codes(row)
        types = [ITEM_TYPES[c] for c in codes if c in ITEM_TYPES]
        if "2.03" in codes and "3.02" in codes:
            types.append("CONVERTIBLE (candidate)")
        if not types:
            types = ["EXHIBITS ONLY"] if codes == ["9.01"] or not codes else ["OTHER ITEM"]
        return sorted(set(types))
    if form == "8-K/A":
        return ["AMENDMENT"]
    if form == "424B2" and program:
        return ["PROGRAM (424B2)"]
    if form in FORM_TYPES:
        return [FORM_TYPES[form]]
    if form in PERIODIC:
        return ["PERIODIC"]
    return []


# ============================================================================ XBRL
def _quarterly(entries):
    out = {}
    for e in entries or []:
        try:
            s, e_ = dt.date.fromisoformat(e["start"]), dt.date.fromisoformat(e["end"])
            filed = dt.date.fromisoformat(e["filed"])
            val = float(e["val"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (QUARTER_DAYS[0] <= (e_ - s).days <= QUARTER_DAYS[1]):
            continue
        k = (s, e_)
        if k not in out or filed < out[k]["filed"]:
            out[k] = {"start": s, "end": e_, "val": val, "filed": filed, "form": e.get("form")}
    return [out[k] for k in sorted(out, key=lambda k: k[1])]


def dividend_changes(concept_js, since, until):
    """[{end, filed, prev, val, dir}] for quarters whose value changed."""
    units = (concept_js or {}).get("units") or {}
    entries = units.get("USD/shares") or next(iter(units.values()), [])
    q = _quarterly(entries)
    out = []
    for prev, cur in zip(q, q[1:]):
        if abs(cur["val"] - prev["val"]) > DIV_TOL and since <= cur["filed"] <= until:
            out.append({"end": cur["end"], "filed": cur["filed"], "prev": prev["val"],
                        "val": cur["val"], "dir": "RAISE" if cur["val"] > prev["val"] else "CUT"})
    return out


def buyback_auths(concept_js, since, until):
    """[{end, filed, prev, val}] where the authorized amount changed."""
    units = (concept_js or {}).get("units") or {}
    entries = []
    for e in units.get("USD") or []:
        try:
            entries.append({"end": dt.date.fromisoformat(e["end"]),
                            "filed": dt.date.fromisoformat(e["filed"]), "val": float(e["val"])})
        except (KeyError, TypeError, ValueError):
            continue
    first = {}
    for e in entries:                    # earliest filing of each (end, val)
        k = (e["end"], e["val"])
        if k not in first or e["filed"] < first[k]["filed"]:
            first[k] = e
    series = sorted(first.values(), key=lambda e: (e["filed"], e["end"]))
    out, last = [], None
    for e in series:
        if last is not None and abs(e["val"] - last) > 0.5 and since <= e["filed"] <= until:
            out.append({"end": e["end"], "filed": e["filed"], "prev": last, "val": e["val"]})
        last = e["val"]
    return out


# ============================================================================ Form 4 (cache only)
def cached_form4_codes(accession, cache_dir):
    """Transaction codes from Form 4 XML already in edgar_cache, or None."""
    stem = os.path.join(cache_dir, accession.replace("-", "") + "_")
    codes, found = set(), False
    for path in glob.glob(stem + "*.xml"):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if "<ownershipDocument" not in text and "<transactionCode>" not in text:
            continue
        found = True
        codes |= set(_TXN_CODE_RE.findall(text))
    return sorted(codes) if found else None


# ============================================================================ tally
def projection(n, window_sessions, live_sessions):
    rate = n / window_sessions if window_sessions else 0.0
    proj = rate * live_sessions
    to20 = (THIN_N / rate) if rate else None
    to40 = (READABLE_N / rate) if rate else None
    label = "READABLE" if proj >= READABLE_N else ("THIN" if proj >= THIN_N else "NOT BY THE BACKSTOP")
    return {"rate_per_month": rate * 21.0, "projected": proj, "sessions_to_20": to20,
            "sessions_to_40": to40, "label": label}


def tally(events, window_sessions, live_sessions, types):
    out = {}
    for t in types:
        evs = [e for e in events if e["type"] == t]
        by = Counter(e["ticker"] for e in evs)
        top = by.most_common(1)[0] if by else (None, 0)
        share = (top[1] / len(evs)) if evs else None
        row = {"n": len(evs), "names": len(by), "by_name": dict(by.most_common()),
               "top": top[0], "top_share": share,
               "concentrated": bool(share is not None and share > CONCENTRATED_SHARE)}
        row.update(projection(len(evs), window_sessions, live_sessions))
        if t in ("DIVIDEND CHANGE",):
            row["raises"] = sum(1 for e in evs if e.get("dir") == "RAISE")
            row["cuts"] = sum(1 for e in evs if e.get("dir") == "CUT")
        timings = Counter(e.get("timing") for e in evs)
        row["timing"] = dict(timings)
        out[t] = row
    return out


# ============================================================================ run
def latest_cohort(path):
    if os.path.basename(path).lower() == REFUSED.lower():
        raise SystemExit("REFUSED: %s is the GENERATED REPORT COPY, never an input. "
                         "Use logs\\claude_equity_bot_tracker.xlsx (THE MASTER)." % REFUSED)
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        by = defaultdict(set)
        for r in wb["Signals"].iter_rows(min_row=FIRST_DATA_ROW, max_col=2, values_only=True):
            if r and r[0] is not None and r[1] is not None and hasattr(r[0], "year"):
                d = r[0].date() if hasattr(r[0], "date") else r[0]
                by[d].add(str(r[1]).strip().upper())
        return sorted(by[max(by)]) if by else []
    finally:
        wb.close()


def market_today():
    return dt.datetime.now(ET).date()


def probe(tickers, today, cik_map, get_json, cache_dir):
    """The whole count, with fetching injected (get_json(url) -> dict or None)."""
    since = today - dt.timedelta(days=WINDOW_DAYS)
    window_sessions = len(TC.sessions_between(since, today))
    live_sessions = len(TC.sessions_between(TC.next_session(today), BACKSTOP))
    names, raw = {}, {}
    for t in tickers:
        cik = cik_map.get(t)
        if not cik:
            names[t] = {"status": "NO CIK"}
            continue
        subs = get_json("https://data.sec.gov/submissions/CIK%s.json" % cik)
        if subs is None:
            names[t] = {"status": "FETCH FAILED", "cik": cik}
            continue
        rows, cov = all_rows(subs, since, get_json)
        raw[t] = (cik, rows, cov)
    tzc = tz_check([r for _, rows, _ in raw.values() for r in rows])
    events, context = [], Counter()
    form4 = {"filings": 0, "cached": 0, "with_P": 0, "with_S": 0}
    for t, (cik, rows, cov) in raw.items():
        inwin = []
        for r in rows:
            at = parse_accept(r.get("acceptanceDateTime"), tzc["mode"])
            day = at.date() if at else None
            if day is None:
                try:
                    day = dt.date.fromisoformat(r.get("filingDate"))
                except (TypeError, ValueError):
                    continue
            if since <= day <= today:
                inwin.append((r, at))
        forms = Counter(str(r.get("form")).upper() for r, _ in inwin)
        if not any(f in PERIODIC for f in forms):
            names[t] = {"status": "NON-FILER", "cik": cik, "forms": dict(forms.most_common(6)),
                        "coverage": cov}
            continue
        program = forms.get("424B2", 0) > PROGRAM_424B2
        per = Counter()
        for r, at in inwin:
            for typ in classify(r, program):
                ev = {"ticker": t, "type": typ, "accession": r.get("accessionNumber"),
                      "form": r.get("form"), "items": r.get("items"),
                      "accepted_et": at.isoformat() if at else None, "timing": timing(at),
                      "bot_session": str(bot_session(at)) if at else None}
                per[typ] += 1
                if typ in COURSE_TYPES:
                    events.append(ev)
                else:
                    context[typ] += 1
                if typ == "FORM 4":
                    form4["filings"] += 1
                    codes = cached_form4_codes(r.get("accessionNumber") or "", cache_dir)
                    if codes is not None:
                        form4["cached"] += 1
                        for code, label in (("P", "INSIDER PURCHASE (cached)"), ("S", "INSIDER SALE (cached)")):
                            if code in codes:
                                form4["with_" + code] += 1
                                e2 = dict(ev, type=label)
                                events.append(e2)
                                per[label] += 1
        div_tag, divs = None, []
        for tag in DIV_TAGS:
            js = get_json(CONCEPT_URL.format(cik10=cik, tag=tag))
            if js:
                div_tag, divs = tag, dividend_changes(js, since, today)
                break
        for d in divs:
            events.append({"ticker": t, "type": "DIVIDEND CHANGE", "dir": d["dir"], "form": "XBRL",
                           "period_end": str(d["end"]), "filed": str(d["filed"]), "prev": d["prev"],
                           "val": d["val"], "timing": "FILED (lagged)"})
            per["DIVIDEND CHANGE"] += 1
        bjs = get_json(CONCEPT_URL.format(cik10=cik, tag=BUYBACK_TAG))
        bbs = buyback_auths(bjs, since, today) if bjs else []
        for b in bbs:
            events.append({"ticker": t, "type": "BUYBACK AUTHORIZATION", "form": "XBRL",
                           "period_end": str(b["end"]), "filed": str(b["filed"]), "prev": b["prev"],
                           "val": b["val"], "timing": "FILED (lagged)"})
            per["BUYBACK AUTHORIZATION"] += 1
        names[t] = {"status": "FILER", "cik": cik, "coverage": cov, "program_424B2": program,
                    "counts": dict(per), "dividend_tag": div_tag, "buyback_tag": bool(bjs)}
    filers = sorted(t for t, v in names.items() if v.get("status") == "FILER")
    return {"probe_version": PROBE_VERSION, "date": str(today), "since": str(since),
            "window_sessions": window_sessions, "live_sessions": live_sessions,
            "backstop": str(BACKSTOP), "tz": tzc, "filers": filers,
            "non_filers": sorted(t for t, v in names.items() if v.get("status") == "NON-FILER"),
            "problems": {t: v["status"] for t, v in names.items()
                         if v.get("status") not in ("FILER", "NON-FILER")},
            "incomplete": sorted(t for t, v in names.items()
                                 if v.get("status") == "FILER" and not v["coverage"]["complete"]),
            "names": names, "course": tally(events, window_sessions, live_sessions, COURSE_TYPES),
            "context": dict(context.most_common()), "form4": form4, "events": events}


# ============================================================================ render
def _f(x, fmt="%.1f"):
    return "—" if x is None else fmt % x


def render_md(res):
    L = []
    w = L.append
    w("# Event probe (step 6 feasibility) — %s" % res["date"])
    w("")
    w("*READ-ONLY. SEC filing index and XBRL only; no price, confidence, signal or outcome read (blind). "
      "Window %s .. %s (%d sessions). Projection to the backstop %s (%d sessions). Advisory-only · no "
      "orders · not financial advice.*" % (res["since"], res["date"], res["window_sessions"],
                                          res["backstop"], res["live_sessions"]))
    w("")
    tz = res["tz"]
    ms = tz["market_share"]
    w("**Time zone:** acceptance read as **%s** (%s; earnings 8-Ks in market hours: ET reading %s, "
      "UTC reading %s, n = %d)." % (tz["mode"], tz["status"],
                                     _f(None if ms["ET"] is None else 100 * ms["ET"], "%.0f%%"),
                                     _f(None if ms["UTC"] is None else 100 * ms["UTC"], "%.0f%%"), tz["n"]))
    w("")
    w("**Filers:** %d (%s). **Non-filers:** %s." % (len(res["filers"]), ", ".join(res["filers"]),
                                                     ", ".join(res["non_filers"]) or "none"))
    if res["problems"]:
        w("**Not read:** " + ", ".join("%s (%s)" % kv for kv in sorted(res["problems"].items())) + ".")
    if res["incomplete"]:
        w("**Index incomplete for the window:** " + ", ".join(res["incomplete"]) + " (counts are lower bounds).")
    w("")
    w("## 1 · The step-6 candidate types")
    w("")
    w("| Type | Events (12 mo) | Names | Top name (share) | Per month | Projected by %s | Sessions to 20 / 40 | Label |"
      % res["backstop"])
    w("|---|---:|---:|---|---:|---:|---|---|")
    for t, r in res["course"].items():
        top = "—" if not r["top"] else "%s (%.0f%%)%s" % (r["top"], 100 * r["top_share"],
                                                          " CONCENTRATED" if r["concentrated"] else "")
        extra = ""
        if "raises" in r:
            extra = " (raises %d, cuts %d)" % (r["raises"], r["cuts"])
        w("| %s%s | %d | %d | %s | %.1f | %.0f | %s / %s | %s |" % (
            t, extra, r["n"], r["names"], top, r["rate_per_month"], r["projected"],
            _f(r["sessions_to_20"], "%.0f"), _f(r["sessions_to_40"], "%.0f"), r["label"]))
    w("")
    f4 = res["form4"]
    w("Form 4: %d filings in the window; %d have XML in edgar_cache (%s); of those, %d carry a P code "
      "and %d an S code. The insider rows count cached filings only [?]." % (
          f4["filings"], f4["cached"], _f(100.0 * f4["cached"] / f4["filings"], "%.0f%%") if f4["filings"] else "—",
          f4["with_P"], f4["with_S"]))
    w("")
    w("## 2 · When the index-typed events land (bot session = first 09:30 CT signal after acceptance)")
    w("")
    w("| Type | Pre-open | Market hours | After close | Non-session day |")
    w("|---|---:|---:|---:|---:|")
    for t, r in res["course"].items():
        tm = r["timing"]
        if not r["n"] or "FILED (lagged)" in tm:
            continue
        w("| %s | %d | %d | %d | %d |" % (t, tm.get("PRE-OPEN", 0), tm.get("MARKET HOURS", 0),
                                          tm.get("AFTER CLOSE", 0), tm.get("NON-SESSION DAY", 0)))
    w("")
    w("## 3 · Context types (8-K items and forms, not step-6 candidates)")
    w("")
    w("| Type | Filings |")
    w("|---|---:|")
    for t, n in res["context"].items():
        w("| %s | %d |" % (t, n))
    w("")
    w("## 4 · Per name")
    w("")
    w("| Name | Index pages | Earliest in index | 424B2 program | Dividend tag | Buyback tag | Typed counts |")
    w("|---|---|---|---|---|---|---|")
    for t in res["filers"]:
        v = res["names"][t]
        c = v["counts"]
        typed = ", ".join("%s %d" % (k, c[k]) for k in COURSE_TYPES if c.get(k))
        cov = v["coverage"]
        w("| %s | %d/%d%s | %s | %s | %s | %s | %s |" % (
            t, cov["pages_fetched"], cov["pages_needed"], "" if cov["complete"] else " INCOMPLETE",
            cov["earliest_filing"], "yes" if v["program_424B2"] else "no",
            v["dividend_tag"] or "none", "yes" if v["buyback_tag"] else "none", typed or "—"))
    w("")
    w("## 5 · Caveats")
    w("")
    w("- Dividend changes and buyback authorizations are dated by the first 10-Q/10-K that reports them, "
      "weeks after the announcement. The trace itself will need the announcement date (8-K 8.01 or the "
      "earnings release) [?].")
    w("- A trailing-year rate carried forward assumes next year looks like last year.")
    w("- CONVERTIBLE (candidate) is 2.03 and 3.02 on one 8-K; it is a heuristic, not a reading of the terms.")
    w("- SHELF TAKEDOWN does not say equity or debt; typing it needs the prospectus cover page.")
    w("- Probe labels are not bars. The pre-registration sets its own.")
    w("")
    w("*Advisory-only · no orders · not financial advice.*")
    return "\n".join(L) + "\n"


def _jsonable(o):
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    raise TypeError(type(o))


def run(args, log=print):
    # JPM's index runs to many pages a year (structured-note 424B2s). The run's
    # 120 s EDGAR budget is sized for the 09:30 signal, not for a 12-month
    # index pull, so this process alone gets 600 s unless .env or the shell
    # already sets one. A page cut short by the budget still prints INCOMPLETE.
    os.environ.setdefault("EDGAR_MAX_SECONDS", "600")
    import edgar_client as EC
    if not EC._user_agent():
        log("COULD NOT RUN: SEC_USER_AGENT is not set in .env")
        return 2
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        try:
            tickers = latest_cohort(args.tracker)
        except SystemExit:
            raise
        except Exception as e:      # noqa: BLE001
            log("COULD NOT RUN: master unreadable (%s) and no --tickers given" % e)
            return 2
    if not tickers:
        log("COULD NOT RUN: no names")
        return 2
    EC.reset_budget()
    cik_map = EC.load_cik_map({})
    if not cik_map:
        log("COULD NOT RUN: CIK map unavailable")
        return 2
    calls = [0]

    def get_json(url):
        calls[0] += 1
        return EC._http_get(url, as_json=True)

    today = market_today()
    log("event_probe %s: %d names" % (today, len(tickers)))
    res = probe(tickers, today, cik_map, get_json, EC.EDGAR_CACHE_DIR)
    res["sec_calls"] = calls[0] + 1
    res["edgar_seconds"] = round(EC.budget_spent(), 1)
    stem = args.out or ("event_probe_%s" % today)
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(render_md(res))
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=_jsonable)
    log("wrote %s.md and %s.json (%d SEC calls, %.1fs of a %.0fs EDGAR budget)" % (
        stem, stem, res["sec_calls"], res["edgar_seconds"], EC.EDGAR_MAX_SECONDS))
    log("filers %d, non-filers %d, not read %d, incomplete %d | time zone %s (%s)" % (
        len(res["filers"]), len(res["non_filers"]), len(res["problems"]), len(res["incomplete"]),
        res["tz"]["mode"], res["tz"]["status"]))
    for t, r in res["course"].items():
        log("  %-26s %4d events  %-20s projected %.0f" % (t, r["n"], r["label"], r["projected"]))
    return 0


# ============================================================================ selftest
def selftest():
    import tempfile
    fails, done = [], []

    def ok(name, cond, detail=""):
        print("%s  %s%s" % ("PASS" if cond else "FAIL", name, ("  " + detail) if detail and not cond else ""))
        done.append(name)
        if not cond:
            fails.append(name)

    def block(rows):
        return {k: [r.get(k, "") for r in rows] for k in INDEX_KEYS}

    # 1-2 zipping
    b = block([{"form": "8-K", "accessionNumber": "a1", "items": "3.02,9.01"},
               {"form": "4", "accessionNumber": "a2"}])
    z = zip_block(b)
    ok("zip: two filings", len(z) == 2 and z[0]["items"] == "3.02,9.01" and z[1]["form"] == "4")
    ok("zip: empty block", zip_block(None) == [])
    # 3-9 classification
    ok("3.02 -> EQUITY ISSUE", classify({"form": "8-K", "items": "3.02,9.01"}) == ["EQUITY ISSUE"])
    ok("2.03 -> DEBT ISSUE only", classify({"form": "8-K", "items": "2.03"}) == ["DEBT ISSUE"])
    ok("2.03 + 3.02 -> convertible candidate and both",
       classify({"form": "8-K", "items": "1.01,2.03,3.02"}) ==
       ["AGREEMENT", "CONVERTIBLE (candidate)", "DEBT ISSUE", "EQUITY ISSUE"])
    ok("9.01 alone -> EXHIBITS ONLY", classify({"form": "8-K", "items": "9.01"}) == ["EXHIBITS ONLY"])
    ok("2.02 + 9.01 -> RESULTS", classify({"form": "8-K", "items": "2.02,9.01"}) == ["RESULTS"])
    ok("8-K/A -> AMENDMENT", classify({"form": "8-K/A", "items": "3.02"}) == ["AMENDMENT"])
    ok("424B2: program vs takedown",
       classify({"form": "424B2"}, program=True) == ["PROGRAM (424B2)"]
       and classify({"form": "424B2"}) == ["SHELF TAKEDOWN"] and classify({"form": "424B5"}) == ["SHELF TAKEDOWN"])
    ok("unknown form -> nothing", classify({"form": "N-CSR"}) == [])
    # 10-12 index pages
    since = dt.date(2025, 11, 19)
    recent = block([{"form": "8-K", "filingDate": "2026-06-01", "accessionNumber": "x1"}])
    subs = {"filings": {"recent": recent, "files": [
        {"name": "p1.json", "filingFrom": "2025-01-01", "filingTo": "2026-01-15"},
        {"name": "p0.json", "filingFrom": "2023-01-01", "filingTo": "2024-12-31"}]}}
    asked = []

    def gp(url):
        asked.append(url)
        return block([{"form": "8-K", "filingDate": "2025-06-01", "accessionNumber": "x0"},
                      {"form": "8-K", "filingDate": "2026-06-01", "accessionNumber": "x1"}])
    rows, cov = all_rows(subs, since, gp)
    ok("older page fetched only when it reaches the window", asked == [SUBMISSIONS_PAGE_URL.format(name="p1.json")])
    ok("accession dedupe across pages", sorted(r["accessionNumber"] for r in rows) == ["x0", "x1"])
    ok("coverage complete", cov["complete"] and cov["earliest_filing"] == "2025-06-01")
    rows2, cov2 = all_rows(subs, since, lambda u: None)
    ok("failed page -> incomplete", not cov2["complete"] and cov2["pages_failed"] == 1)
    # 13-15 time zone and timing
    t_et = parse_accept("2026-11-17T16:05:12.000Z", "ET")
    t_utc = parse_accept("2026-11-17T21:05:12.000Z", "UTC")
    ok("ET reading", t_et.hour == 16 and timing(t_et) == "AFTER CLOSE")
    ok("UTC reading converts to Eastern", t_utc.hour == 16 and timing(t_utc) == "AFTER CLOSE")
    earn = [{"form": "8-K", "items": "2.02", "acceptanceDateTime": "2026-%02d-1%dT16:05:00.000Z" % (m, d)}
            for m, d in ((2, 2), (4, 3), (5, 4), (7, 5), (8, 6), (10, 7))]
    ok("tz check: Eastern digits resolve ET", tz_check(earn)["mode"] == "ET" and tz_check(earn)["status"] == "RESOLVED")
    earn_utc = [dict(r, acceptanceDateTime=r["acceptanceDateTime"].replace("T16:05", "T12:00")) for r in earn]
    ok("tz check: UTC digits (07:00 ET releases) resolve UTC", tz_check(earn_utc)["mode"] == "UTC"
       and tz_check(earn_utc)["status"] == "RESOLVED")
    earn_tie = [dict(r, acceptanceDateTime=r["acceptanceDateTime"].replace("T16:05", "T22:00")) for r in earn]
    ok("tz check: non-discriminating times -> UNRESOLVED", tz_check(earn_tie)["status"].startswith("UNRESOLVED"))
    ok("tz check: too few -> UNRESOLVED, ET", tz_check(earn[:2])["status"].startswith("UNRESOLVED")
       and tz_check(earn[:2])["mode"] == "ET")
    # 16-19 bot session
    ok("08:00 ET on a session -> same day", bot_session(parse_accept("2026-11-19T08:00:00", "ET")) == dt.date(2026, 11, 19))
    ok("11:00 ET -> next session", bot_session(parse_accept("2026-11-19T11:00:00", "ET")) == dt.date(2026, 11, 20))
    ok("Saturday -> Monday", bot_session(parse_accept("2026-11-21T09:00:00", "ET")) == dt.date(2026, 11, 23))
    ok("Thanksgiving -> 11-27", bot_session(parse_accept("2026-11-25T17:00:00", "ET")) == dt.date(2026, 11, 27)
       and timing(parse_accept("2026-11-26T12:00:00", "ET")) == "NON-SESSION DAY")
    # 20-22 XBRL dividends
    def q(s, e, v, f, form="10-Q"):
        return {"start": s, "end": e, "val": v, "filed": f, "form": form}
    divjs = {"units": {"USD/shares": [
        q("2025-01-01", "2025-03-31", 0.25, "2025-05-01"), q("2025-04-01", "2025-06-30", 0.25, "2025-08-01"),
        q("2025-07-01", "2025-09-30", 0.26, "2025-11-01"), q("2025-07-01", "2025-09-30", 0.26, "2026-11-01"),
        q("2025-01-01", "2025-09-30", 0.76, "2025-11-01"),
        q("2025-10-01", "2025-12-31", 0.26, "2026-02-01"), q("2026-01-01", "2026-03-31", 0.20, "2026-05-01")]}}
    ch = dividend_changes(divjs, dt.date(2025, 6, 1), dt.date(2026, 11, 19))
    ok("dividend: one raise, one cut, YTD and restatements ignored",
       [(c["dir"], str(c["filed"])) for c in ch] == [("RAISE", "2025-11-01"), ("CUT", "2026-05-01")])
    ok("dividend: window bound by filed date",
       len(dividend_changes(divjs, dt.date(2026, 1, 1), dt.date(2026, 11, 19))) == 1)
    ok("dividend: empty concept", dividend_changes(None, since, dt.date(2026, 11, 19)) == [])
    # 23 buybacks
    bjs = {"units": {"USD": [{"end": "2025-03-31", "filed": "2025-05-01", "val": 9e10},
                             {"end": "2025-06-30", "filed": "2025-08-01", "val": 9e10},
                             {"end": "2026-03-31", "filed": "2026-05-01", "val": 1.1e11},
                             {"end": "2025-06-30", "filed": "2026-08-01", "val": 9e10}]}}
    bb = buyback_auths(bjs, dt.date(2025, 11, 19), dt.date(2026, 11, 19))
    ok("buyback: one new authorization, repeats ignored", [str(b["filed"]) for b in bb] == ["2026-05-01"])
    # 24 Form 4 cache
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "000123_form4.xml"), "w") as fh:
            fh.write("<ownershipDocument><transactionCode>P</transactionCode>"
                     "<transactionCode>S</transactionCode></ownershipDocument>")
        with open(os.path.join(td, "000999_wf-form4.htm"), "w") as fh:
            fh.write("<html>rendered</html>")
        ok("Form 4 codes from cached XML", cached_form4_codes("0001-23", td) == ["P", "S"]
           and cached_form4_codes("0009-99", td) is None and cached_form4_codes("0005-55", td) is None)
    # 25-27 projection, labels, concentration
    p = projection(12, 250, 150)
    ok("projection: rate and sessions", abs(p["projected"] - 7.2) < 1e-9 and abs(p["sessions_to_20"] - 250 * 20 / 12) < 1e-9
       and p["label"] == "NOT BY THE BACKSTOP")
    ok("labels at 20 and 40", projection(40, 150, 150)["label"] == "READABLE"
       and projection(20, 150, 150)["label"] == "THIN" and projection(0, 150, 150)["sessions_to_20"] is None)
    tl = tally([{"ticker": "O", "type": "DIVIDEND CHANGE", "dir": "RAISE"}] * 3 +
               [{"ticker": "PM", "type": "DIVIDEND CHANGE", "dir": "CUT"}], 250, 150, ("DIVIDEND CHANGE",))
    r = tl["DIVIDEND CHANGE"]
    ok("tally: concentration and direction", r["concentrated"] and r["top"] == "O" and r["raises"] == 3 and r["cuts"] == 1)
    # 28-31 the whole probe on fixtures, offline
    today = dt.date(2026, 11, 19)
    co = block([
        {"form": "10-Q", "filingDate": "2026-08-01", "accessionNumber": "c1", "acceptanceDateTime": "2026-08-01T16:30:00.000Z"},
        {"form": "8-K", "filingDate": "2026-07-30", "accessionNumber": "c2", "items": "2.02,9.01", "acceptanceDateTime": "2026-07-30T16:05:00.000Z"},
        {"form": "8-K", "filingDate": "2026-09-10", "accessionNumber": "c3", "items": "2.03,9.01", "acceptanceDateTime": "2026-09-10T07:00:00.000Z"},
        {"form": "8-K", "filingDate": "2025-06-10", "accessionNumber": "c4", "items": "3.02", "acceptanceDateTime": "2025-06-10T07:00:00.000Z"},
        {"form": "4", "filingDate": "2026-10-01", "accessionNumber": "c5", "acceptanceDateTime": "2026-10-01T18:00:00.000Z"}])
    etf = block([{"form": "N-CSR", "filingDate": "2026-08-01", "accessionNumber": "e1"}])
    store = {"https://data.sec.gov/submissions/CIK0000000001.json": {"filings": {"recent": co}},
             "https://data.sec.gov/submissions/CIK0000000002.json": {"filings": {"recent": etf}},
             CONCEPT_URL.format(cik10="0000000001", tag=DIV_TAGS[0]): divjs}
    res = probe(["AAA", "ETF", "ZZZ"], today, {"AAA": "0000000001", "ETF": "0000000002"},
                lambda u: store.get(u), "/nonexistent")
    ok("probe: filer, non-filer, no CIK", res["filers"] == ["AAA"] and res["non_filers"] == ["ETF"]
       and res["problems"] == {"ZZZ": "NO CIK"})
    ok("probe: window drops the 2025-06 equity issue", res["course"]["EQUITY ISSUE"]["n"] == 0
       and res["course"]["DEBT ISSUE"]["n"] == 1)
    ok("probe: debt issue lands pre-open, seen the same session",
       [e for e in res["events"] if e["type"] == "DEBT ISSUE"][0]["bot_session"] == "2026-09-10")
    ok("probe: dividend cut in window, results counted as context, Form 4 uncached",
       res["course"]["DIVIDEND CHANGE"]["cuts"] == 1 and res["context"].get("RESULTS") == 1
       and res["form4"] == {"filings": 1, "cached": 0, "with_P": 0, "with_S": 0})
    md = render_md(res)
    body = "\n".join(md.split("\n")[3:])          # past the title and the READ-ONLY line
    ok("render: blind (no outcome words) and serializable",
       not re.search(r"(?i)confidence|outcome|\breturn|hit rate", body)
       and bool(json.dumps(res, default=_jsonable)))
    # 32 report copy refused
    try:
        latest_cohort(os.path.join("x", REFUSED))
        refused = False
    except SystemExit:
        refused = True
    ok("report copy refused", refused)
    print("%d checks, %d failed" % (len(done), len(fails)))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="READ-ONLY step-6 event-rate probe (SEC index and XBRL only).")
    ap.add_argument("--tickers", help="comma-separated; default = the master's latest cohort")
    ap.add_argument("--tracker", default=MASTER_DEFAULT, help="THE MASTER (read-only; tickers only)")
    ap.add_argument("--out", help="output stem (default event_probe_<date>)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
