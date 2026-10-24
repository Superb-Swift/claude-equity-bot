#!/usr/bin/env python3
"""
sec_data_audit.py - an SEC data-gap audit for every name the value layer
reads, and any name you are considering, with a period-basis reconciliation of
what the model is shown and of any outside source you compare against.

WHY THIS EXISTS (Rob, 2026-10-24)
    DOW's TTM read NO READ, and Morningstar's figures looked "wildly different"
    from the prompt's. Two different things were mixed in that comparison:
      * PERIOD BASIS. The prompt's statement block shows the LATEST QUARTER
        (a 10-K: the year), balance-sheet lines on the period end, and cash
        flow year-to-date, labelled [9M YTD]. Morningstar shows trailing twelve
        months. AAPL's net income of $29.8B (the June quarter) and
        Morningstar's $128.93B (TTM) are both right.
      * REAL GAPS. DOW's Q2 2026 10-Q facts are not in DOW Inc.'s companyfacts
        feed at all: SEC filed them under the co-registrant, The Dow Chemical
        Company (edgar_client.py analyst note, 2026-08-26).
    This tool separates the two, per name and per metric, so a gap is never
    read as a basis difference or the reverse.

UNIVERSE (grows with the watchlist; no ticker list lives in this file)
    default             the tickers the latest session log wrote
    --add A,B           plus names you are considering (the post-exit list, say)
    --tickers A,B       only these
    --tickers-file F    one ticker per line; '#' starts a comment

WHAT IT REPORTS, PER NAME
    1  identity: CIK, filer type (us-gaap, IFRS, fund, no CIK), and every
       10-Q/10-K in the submissions list that has NO facts in the feed
       (FILING-GAP), with any co-registrant recovery (RECOVERED)
    2  coverage of each metric over the last 8 quarters:
         R reported   q fiscal Q4 (FY minus 3 quarters, routine)
         D derived    (a hole inside a year, filled from year-to-date facts)
         C recovered  (a co-registrant's facts, same accession)   - missing
    3  TTM for each flow metric, with its basis and any fallback tag; the
       latest instant for each balance-sheet metric
    4  the prompt's statement block (logs\\inputs_<date>.jsonl) against SEC for
       the SAME period - MATCH or MISMATCH - with the TTM beside it
    5  the value card's ROE bases (Schwab last-FY, the class; EDGAR quarter x4)
       against TTM ROE (implied_return exhibit)
    6  --reference CSV (ticker,metric,value[,basis][,as_of][,source]): each
       outside figure checked on its stated basis, and, if it disagrees, the
       basis that explains it (quarter, year-to-date, TTM at another date ...)

DISCIPLINE (DP-V1, DP-V3, DP-3C-ai)
    Reporting only. Nothing here reaches the prompt, the risk engine, a gate or
    the paste. It reads the prompt's block from the captured inputs; it never
    changes how edgar_client builds it (a Phase 4b question, pre-registered).
    The reading rules are sec_facts.py's, shared with ttm_eps.py.

USAGE
    python sec_data_audit.py
    python sec_data_audit.py --add UNH,O,VHT --reference "Claude outputs\\ref.csv"
    python sec_data_audit.py --offline        (cached files only, any version; no SEC calls)
    python sec_data_audit.py --selftest
Writes sec_data_audit_<date>.md and .json (git-ignored).
Exit 0 no unresolved gap or mismatch; 1 findings; 2 could not run.
Advisory-only - no orders - not financial advice.
"""

import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sec_facts as SF                                   # noqa: E402

WINDOW_QUARTERS = 8
TTM_QUARTERS = 4
STALE_DAYS = 135                     # as ttm_eps: one missed 10-Q
EQUITY_MAX_AGE_DAYS = 400            # as ttm_eps
ROE_GAP_PTS = 5.0                    # report a class-basis ROE this far from TTM ...
ROE_GAP_REL = 0.25                   # ... and this far in relative terms
REF_TOL = 0.01                       # an outside figure "agrees" within 1% (or its rounding)
_TK = re.compile(r'Signal JSON: \{"ticker": "([A-Z][A-Z.\-]*)"')
_LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")
_HDR = re.compile(r"Financial statements \(XBRL, (?P<form>10-[QK])(?: (?P<fp>Q\d))?"
                  r"(?: FY(?P<fy>\d{4}))?, period ended (?P<end>\d{4}-\d{2}-\d{2})\)")
_LINE = re.compile(r"^  (?P<label>[A-Z][A-Za-z ]+?)\s{2,}(?P<val>\$?-?\$?[\d,]*\.?\d+[BMK]?)"
                   r"(?P<rest>.*)$")
_NOTE = re.compile(r"\[(?P<note>[^\]]+)\]\s*$")
_NOTE_BUCKET = {"quarter": "Q", "6M YTD": "H", "9M YTD": "9M", "full year": "FY"}


# --------------------------------------------------------------------------- #
# Universe
# --------------------------------------------------------------------------- #
def latest_log(log_dir="logs"):
    logs = sorted((m.group(1), p) for p in glob.glob(os.path.join(log_dir, "signals_*.log"))
                  for m in [_LOGDATE.search(os.path.basename(p))] if m)
    return logs[-1] if logs else (None, None)


def universe(args, log_dir="logs"):
    d, p = latest_log(log_dir)
    base = []
    if p:
        with open(p, encoding="utf-8", errors="replace") as fh:
            base = sorted({m.group(1) for ln in fh for m in [_TK.search(ln)] if m})
    split = lambda s: [t.strip().upper() for t in (s or "").split(",") if t.strip()]  # noqa: E731
    if args.tickers:
        names = split(args.tickers)
    else:
        names = base + split(args.add)
    if args.tickers_file:
        with open(args.tickers_file, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.split("#", 1)[0].strip().upper()
                if ln:
                    names.append(ln)
    out = []
    for t in names:
        if t not in out:
            out.append(t)
    return d, out, set(base)


# --------------------------------------------------------------------------- #
# Number parsing (the prompt's block, an outside source's figures)
# --------------------------------------------------------------------------- #
def parse_amount(s):
    """'$109.4B' -> (109.4e9, 0.05e9); '$-1.3b' -> (-1.3e9, 0.05e9); '2.02' ->
    (2.02, 0.005). The second value is half the last printed digit."""
    t = s.strip().replace(",", "").replace("$", "")
    mult = {"B": 1e9, "M": 1e6, "K": 1e3}.get(t[-1:].upper(), 1.0)
    if mult != 1.0:
        t = t[:-1]
    try:
        v = float(t)
    except ValueError:
        return None, None
    dec = len(t.split(".", 1)[1]) if "." in t else 0
    return v * mult, 0.5 * 10 ** (-dec) * mult


def _agrees(ours, theirs, half_digit):
    if ours is None or theirs is None:
        return False
    tol = max(abs(theirs) * REF_TOL, (half_digit or 0) * 1.0001)
    return abs(ours - theirs) <= tol


# --------------------------------------------------------------------------- #
# The prompt's statement block, from the captured inputs (R6)
# --------------------------------------------------------------------------- #
def latest_inputs(log_dir="logs"):
    files = sorted(glob.glob(os.path.join(log_dir, "inputs_*.jsonl")))
    return files[-1] if files else None


def prompt_blocks(path):
    """{ticker: dict(form, fp, fy, end, lines=[dict(label, text, value, half, note)])}."""
    out = {}
    if not path:
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            x = r.get("extra_context") or ""
            m = _HDR.search(x)
            if not m:
                continue
            blk = dict(form=m.group("form"), fp=m.group("fp"), fy=m.group("fy"),
                       end=dt.date.fromisoformat(m.group("end")), lines=[])
            for line in x[m.end():].split("\n")[1:]:
                lm = _LINE.match(line)
                if not lm:
                    if line.strip() and not line.startswith("  "):
                        break
                    continue
                v, half = parse_amount(lm.group("val"))
                nm = _NOTE.search(lm.group("rest"))
                blk["lines"].append(dict(label=lm.group("label").strip(), text=lm.group("val"),
                                         value=v, half=half,
                                         note=nm.group("note") if nm else None))
            out[r.get("ticker")] = blk
    return out


# --------------------------------------------------------------------------- #
# Per-name audit
# --------------------------------------------------------------------------- #
def _slots(cf, latest_end):
    """The last WINDOW_QUARTERS quarter slots, newest first, from the filer's
    own quarter calendar (the union of every flow metric's quarters)."""
    union = {}
    for m in SF.METRICS:
        if m[2] != "flow":
            continue
        _t, rows = SF.rows_for(cf, m)
        for k in SF.quarters(rows):
            union[k] = 1
    slots, cur = [], latest_end
    for _ in range(WINDOW_QUARTERS):
        hit = [k for k in union if abs((k[1] - cur).days) <= 10]
        if hit:
            k = max(hit, key=lambda k: k[1])
            slots.append(k)
            cur = k[0] - dt.timedelta(days=1)
        else:
            slots.append((cur - dt.timedelta(days=90), cur))
            cur = cur - dt.timedelta(days=91)
    return slots


_CODE = {"reported": "R", "fiscal-q4": "q", "derived": "D", "recovered": "C"}
# Cash flow is reported year-to-date by convention (edgar_client: RTX tags
# operating cash flow only for H/9M/FY), so a quarter derived from YTD facts is
# routine there: coded 'd' and not flagged. A recovered quarter is always flagged.
ROUTINE_YTD = ("ocf",)


def audit_name(tk, cf, src, today, prompt=None, vrec=None):
    a = dict(ticker=tk, source=src, flags=[], metrics={}, prompt=[], roe=None)
    if cf is None:
        a["type"] = "FUND/NO-FACTS" if "no CIK" in (src or "") else "NO-FACTS"
        a["flags"].append(a["type"] + ": " + (src or ""))
        return a
    gaap = cf.get("facts", {}).get("us-gaap", {})
    a.update(cik=cf.get("cik"), entity=cf.get("entityName"),
             taxonomies=cf.get("taxonomies"), fetched=cf.get("fetched"))
    if not gaap:
        a["type"] = "IFRS" if "ifrs-full" in (cf.get("taxonomies") or []) else "NO-US-GAAP"
        a["flags"].append("%s: no us-gaap facts (only us-gaap is read; DP-3C-f)" % a["type"])
        return a
    a["type"] = "FILER"
    # filing-level gaps and recoveries
    a["recovered"] = cf.get("recovered") or []
    a["filing_gaps"] = SF.filing_gaps(cf, today)
    if cf.get("periodic") is None:
        a["flags"].append("SUBMISSIONS-UNKNOWN: no filing list cached; filing gaps not checked")
    for r in a["recovered"]:
        a["flags"].append("RECOVERED: %s %s from CIK %s (%d facts, same accession)"
                          % (r["report"], r["accn"], r["from_cik"], r["facts_added"]))
    for g in a["filing_gaps"]:
        a["flags"].append("FILING-GAP: %s for %s (%s) has no facts in this feed"
                          % (g["form"], g["report"], g["accn"]))
    # latest quarter end across the flow metrics
    ends = []
    for m in SF.METRICS:
        if m[2] == "flow":
            _t, rows = SF.rows_for(cf, m)
            ends += [k[1] for k in SF.quarters(rows)]
    if not ends:
        a["flags"].append("NO-QUARTERS: no quarterly flow facts")
        return a
    latest = max(ends)
    a["latest_quarter_end"] = str(latest)
    if (today - latest).days > STALE_DAYS:
        a["flags"].append("STALE: the latest quarter in the feed ends %s (%d days)"
                          % (latest, (today - latest).days))
    slots = _slots(cf, latest)
    a["slots"] = [str(s[1]) for s in slots]
    for m in SF.METRICS:
        key, label, kind, unit, tags = m
        tag, rows = SF.rows_for(cf, m)
        ages = SF.tag_ages(cf, tags, unit)
        rec = dict(label=label, kind=kind, tag=tag)
        if not rows and (cf.get("slim_version") or 0) < 3:
            # a cache written before 2026-10-24 kept EPS, net income and equity only
            rec.update(status="NOT-CACHED", coverage="?" * len(slots))
            a["metrics"][key] = rec
            continue
        if not rows:
            rec.update(status="NOT-TAGGED", coverage="." * len(slots))
            a["metrics"][key] = rec
            continue
        pref = next((t for t, last in ages if last), None)
        pref_last = dict(ages).get(pref)
        chosen_last = dict(ages).get(tag)
        if pref and pref != tag and pref_last and chosen_last and \
                (SF._d(chosen_last) - SF._d(pref_last)).days > 100:
            rec["tag_switch"] = "%s ends %s; %s runs to %s" % (pref, pref_last, tag, chosen_last)
            a["flags"].append("TAG-SWITCH %s: %s" % (label, rec["tag_switch"]))
        if kind == "flow":
            q = SF.quarters(rows)
            cov = []
            for s, e in slots:
                hit = [k for k in q if abs((k[1] - e).days) <= 10]
                code = (_CODE[SF.source_kind(q[max(hit, key=lambda k: k[1])]["source"])]
                        if hit else "-")
                cov.append("d" if (code == "D" and key in ROUTINE_YTD) else code)
            rec["coverage"] = "".join(reversed(cov))           # oldest -> newest
            t = SF.best_ttm(cf, m)
            rec.update(ttm=t["value"], ttm_end=str(t["end"]) if t["end"] else None,
                       ttm_detail=t["detail"], ttm_tag=t.get("tag"), ttm_note=t.get("note"),
                       unusual=t.get("unusual", 0))
            missing_ttm = [c for c in cov[:TTM_QUARTERS] if c == "-"]
            if t["value"] is not None and t["end"] and (latest - t["end"]).days > 10:
                # The freshest tag stopped years ago (RTX's GrossProfit after FY2020,
                # JPM's Revenues after 2014). A TTM that old is history, not a figure:
                # it is withheld here, as edgar_client drops such a line from the prompt.
                rec.update(status="STALE-TAG", ttm=None, stale_ttm_end=str(t["end"]))
                a["flags"].append("STALE-TAG %s: %s ends %s; no current figure (the prompt "
                                  "drops this line too)" % (label, t.get("tag"), t["end"]))
            elif t["value"] is None:
                rec["status"] = "NO-TTM"
                first_q = min((k[1] for k in q), default=None)
                has_10k = any(r.get("form") == "10-K" for r in rows)
                if first_q and ((latest - first_q).days < 3 * 91 + 20 or not has_10k):
                    # A recent listing, not a hole: no 10-K in the feed yet, so the
                    # prior-year quarters its 10-Qs carry as comparatives cannot
                    # be completed (CBRS and SPCX, public in 2026).
                    rec["status"] = "SHORT-HISTORY"
                    a["flags"].append("SHORT-HISTORY %s: no 10-K in the feed yet (quarters from %s); "
                                      "a TTM needs the first annual report" % (label, first_q))
                elif missing_ttm or "gap" in (t["why"] or ""):
                    a["flags"].append("QUARTER-GAP %s: %s" % (label, t["why"]))
            else:
                rec["status"] = "TTM"
                rec_q = [(e, s2) for _s, e, s2 in t["quarters"] if SF.source_kind(s2) == "recovered"]
                der_q = [(e, s2) for _s, e, s2 in t["quarters"] if SF.source_kind(s2) == "derived"]
                if rec_q:
                    a["flags"].append("RECOVERED-QUARTER %s: %s" % (label, "; ".join(
                        "Q ending %s %s" % (e, SF.short_source(s2)) for e, s2 in rec_q)))
                if der_q and key not in ROUTINE_YTD:
                    a["flags"].append("DERIVED %s: %s" % (label, "; ".join(
                        "Q ending %s %s" % (e, SF.short_source(s2)) for e, s2 in der_q)))
                if t.get("note"):
                    a["flags"].append("FALLBACK-TAG %s: %s" % (label, t["note"]))
        else:
            cov = ["R" if SF.instant_at(rows, e) is not None else "-" for _s, e in slots]
            rec["coverage"] = "".join(reversed(cov))
            v, end = SF.latest_instant(rows)
            rec.update(latest=v, latest_end=end, status="INSTANT")
            if end and (latest - SF._d(end)).days > 10:
                rec["status"] = "BEHIND"
                a["flags"].append("BEHIND %s: latest %s, the feed's latest quarter %s"
                                  % (label, end, latest))
        a["metrics"][key] = rec
    if prompt:
        a["prompt"] = reconcile_prompt(cf, prompt)
        for p in a["prompt"]:
            if p["verdict"] == "MISMATCH":
                a["flags"].append("PROMPT-MISMATCH %s: shown %s for %s, SEC %s"
                                  % (p["label"], p["shown"], p["period"], p["sec_fmt"]))
        a["prompt_period"] = "%s %s FY%s, period ended %s" % (
            prompt["form"], prompt["fp"] or "", prompt["fy"] or "?", prompt["end"])
    a["roe"] = roe_bases(cf, vrec, today)
    if a["roe"] and a["roe"].get("flag"):
        a["flags"].append(a["roe"]["flag"])
    r = a["roe"] or {}
    if r.get("class_on_ttm") and r["class_on_ttm"] != r.get("class_now"):
        a["flags"].append("CLASS-ON-TTM: %s today; %s on TTM ROE (ratio %.2f) - counterfactual, "
                          "not applied (DP-V3)" % (r["class_now"], r["class_on_ttm"], r["ratio_on_ttm"]))
    return a


def _fmt(v, unit):
    if v is None:
        return "—"
    if unit == "USD/shares":
        return "%.2f" % v
    a = abs(v)
    if a >= 1e9:
        return "$%.2fB" % (v / 1e9)
    if a >= 1e6:
        return "$%.1fM" % (v / 1e6)
    return "$%.0f" % v


def reconcile_prompt(cf, blk):
    """Each line of the prompt's block against SEC for the same period."""
    out = []
    for ln in blk["lines"]:
        m = SF.metric_by_label(ln["label"])
        if not m or ln["value"] is None:
            continue
        key, label, kind, unit, tags = m
        b = _NOTE_BUCKET.get(ln["note"]) if ln["note"] else ("FY" if blk["form"] == "10-K" else "Q")
        gaap = cf.get("facts", {}).get("us-gaap", {})
        best = None
        for t in tags:                                     # the prompt may use any of them
            rows = gaap.get(t, {}).get("units", {}).get(unit) or []
            if not rows:
                continue
            if kind == "flow":
                v, src = SF.period_value(rows, blk["end"], b)
            else:
                v, src = SF.instant_at(rows, blk["end"]), "reported"
            if v is None:
                continue
            ok = _agrees(v, ln["value"], ln["half"])
            if best is None or (ok and not best[2]):
                best = (t, v, ok, src)
            if ok:
                break
        period = ("%s ending %s" % ({"Q": "quarter", "H": "6M YTD", "9M": "9M YTD",
                                     "FY": "full year"}[b], blk["end"])) if kind == "flow" \
            else "at %s" % blk["end"]
        rec = dict(label=label, shown=ln["text"], period=period, key=key)
        if best is None:
            rec.update(verdict="NOT-FOUND", sec=None, sec_fmt="—", tag=None)
        else:
            rec.update(verdict="MATCH" if best[2] else "MISMATCH", sec=best[1],
                       sec_fmt=_fmt(best[1], unit), tag=best[0], source=best[3])
        if kind == "flow":
            t = SF.best_ttm(cf, m, as_of=blk["end"])
            rec["ttm_same_end"] = t["value"]
            rec["ttm_fmt"] = _fmt(t["value"], unit)
        out.append(rec)
    return out


def roe_bases(cf, vrec, today):
    """The value card's two ROE routes against TTM ROE (all in %)."""
    t = SF.best_ttm(cf, SF.metric("net_income"))
    _tag, eq_rows = SF.rows_for(cf, SF.metric("equity"))
    eq, eq_end = SF.latest_instant(eq_rows) if eq_rows else (None, None)
    ttm_roe = None
    if t["value"] is not None and eq is not None and eq > 0 and eq_end and \
            (today - SF._d(eq_end)).days <= EQUITY_MAX_AGE_DAYS:
        ttm_roe = 100.0 * t["value"] / eq
    out = dict(ttm_roe=ttm_roe, equity_end=eq_end)
    if vrec:
        out.update(class_roe=vrec.get("roe"), class_basis=vrec.get("basis"),
                   q4_roe=vrec.get("roe_edgar"), num_age=vrec.get("num_age"),
                   anchor=vrec.get("anchor"))
        c = vrec.get("roe")
        ratio = vrec.get("ratio")
        if c is not None and ttm_roe is not None and ratio is not None and c > 0 and ttm_roe > 0:
            # the class ratio is roe_implied(9%) / trailing ROE (implied_return
            # section 4), so on a TTM basis it scales by class_roe / ttm_roe
            r_ttm = ratio * c / ttm_roe
            try:
                import value_card as VC
                out.update(class_now=VC.klass(ratio), class_on_ttm=VC.klass(r_ttm),
                           ratio_on_ttm=r_ttm)
            except Exception:                           # noqa: BLE001
                pass
        if c is not None and ttm_roe is not None:
            gap = c - ttm_roe
            out["gap_pts"] = gap
            if abs(gap) >= ROE_GAP_PTS and abs(gap) >= ROE_GAP_REL * max(abs(ttm_roe), 1.0):
                out["flag"] = ("ROE-BASIS: the class reads %.1f%% (%s, numerator %.1fQ old); "
                               "TTM %.1f%% (%+.1f pts)" % (c, vrec.get("basis"),
                                                         vrec.get("num_age") or 0, ttm_roe, gap))
    return out


# --------------------------------------------------------------------------- #
# Outside reference (Morningstar or any other), basis-aware
# --------------------------------------------------------------------------- #
_REF_METRIC = {m[1].lower(): m[0] for m in SF.METRICS}
_REF_METRIC.update({m[0]: m[0] for m in SF.METRICS})
_REF_METRIC.update({"eps": "eps_diluted", "diluted eps": "eps_diluted",
                    "cash": "cash", "cash and equivalents": "cash",
                    "operating cash flow": "ocf", "total assets": "assets",
                    "total liabilities": "liabilities", "net income": "net_income",
                    "operating income": "operating_income", "gross profit": "gross_profit",
                    "revenue": "revenue", "sales": "revenue", "equity": "equity"})


def read_reference(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            key = _REF_METRIC.get(r.get("metric", "").lower())
            v, half = parse_amount(r.get("value", ""))
            if not key or v is None:
                rows.append(dict(r, error="unreadable metric or value"))
                continue
            rows.append(dict(ticker=r.get("ticker", "").upper(), key=key, value=v, half=half,
                             text=r.get("value"), basis=(r.get("basis") or "").upper() or None,
                             as_of=dt.date.fromisoformat(r["as_of"]) if r.get("as_of") else None,
                             source=r.get("source") or "reference"))
    return rows


def reconcile_reference(ref, cf, prompt):
    """One outside figure: our value on its stated basis, and, if it disagrees,
    which basis does explain it."""
    m = SF.metric(ref["key"])
    key, label, kind, unit, tags = m
    basis = ref["basis"] or ("TTM" if kind == "flow" else "INSTANT")
    out = dict(ticker=ref["ticker"], label=label, reference=ref["text"], basis=basis,
               as_of=str(ref["as_of"]) if ref["as_of"] else None, source=ref["source"])
    shown = None
    if prompt:
        for ln in prompt["lines"]:
            if SF.metric_by_label(ln["label"]) and SF.metric_by_label(ln["label"])[0] == key:
                if ln["note"]:
                    what = ln["note"]
                elif kind == "flow":
                    what = "quarter" if prompt["form"] == "10-Q" else "full year"
                else:
                    what = "at"
                shown = "%s (%s %s)" % (ln["text"], what, prompt["end"])
    out["prompt_shows"] = shown
    if cf is None or not cf.get("facts", {}).get("us-gaap"):
        out.update(verdict="NO-SEC-DATA", ours=None)
        return out
    _tag, rows = SF.rows_for(cf, m)
    if not rows:
        out.update(verdict="NOT-CACHED (run online)" if (cf.get("slim_version") or 0) < 3
                   else "NOT-TAGGED", ours=None)
        return out
    cand = []
    asof = ref["as_of"]
    if kind == "flow":
        cand.append(("TTM as of %s" % (asof or "latest"), SF.best_ttm(cf, m, as_of=asof)["value"]))
        t_last = SF.best_ttm(cf, m)
        cand.append(("TTM to %s" % t_last["end"], t_last["value"]))
        for e in sorted({k[1] for k in SF.quarters(rows)}, reverse=True)[:3]:
            for b in ("Q", "H", "9M", "FY"):
                v, _s = SF.period_value(rows, e, b)
                if v is not None:
                    cand.append(("%s ending %s" % ({"Q": "quarter", "H": "6M YTD", "9M": "9M YTD",
                                                     "FY": "full year"}[b], e), v))
    else:
        if asof:
            cand.append(("at %s" % asof, SF.instant_at(rows, asof)))
        v, end = SF.latest_instant(rows)
        cand.append(("at %s" % end, v))
    stated = cand[0]
    out["ours"] = _fmt(stated[1], unit)
    out["ours_basis"] = stated[0]
    if kind == "flow":
        bt = SF.best_ttm(cf, m, as_of=asof)
        if bt.get("note"):
            out["ours_basis"] += " [%s; %s]" % (bt["tag"], "includes noncontrolling interest"
                                                if bt["tag"] == "ProfitLoss" else "fallback tag")
    if _agrees(stated[1], ref["value"], ref["half"]):
        out["verdict"] = "AGREES"
    else:
        alt = [c for c in cand[1:] if _agrees(c[1], ref["value"], ref["half"])]
        out["verdict"] = ("EXPLAINED: %s" % alt[0][0]) if alt else "DISAGREES"
    return out


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(day, audits, refs, inputs_path, exhibit):
    L = ["# SEC data audit - %s" % day, "",
         "*sec_data_audit.py. Reporting only: nothing here reaches the prompt or any gate "
         "(DP-V1, DP-V3). Reading rules: sec_facts.py, shared with ttm_eps.py. Prompt "
         "block from `%s`; value-card ROE from `%s`.*" % (inputs_path or "-", exhibit or "-"), "",
         "## Summary", "",
         "| Ticker | Type | Latest quarter | Filing gaps | TTM EPS | TTM net income | Prompt block "
         "| Class ROE vs TTM | Flags |",
         "|---|---|---|---|---:|---:|---|---|---:|"]
    for a in audits:
        ms = a.get("metrics", {})
        eps, ni = ms.get("eps_diluted", {}), ms.get("net_income", {})
        pr = a.get("prompt") or []
        chk = [p for p in pr if p["verdict"] in ("MATCH", "MISMATCH")]
        pv = ("%d/%d match" % (sum(1 for p in chk if p["verdict"] == "MATCH"), len(chk))
              + (" (+%d not in cache)" % (len(pr) - len(chk)) if len(pr) > len(chk) else "")) if pr else "—"
        roe = a.get("roe") or {}
        rs = ("%.1f%% vs %.1f%%" % (roe["class_roe"], roe["ttm_roe"])
              if roe.get("class_roe") is not None and roe.get("ttm_roe") is not None else "—")
        if roe.get("class_on_ttm") and roe["class_on_ttm"] != roe.get("class_now"):
            rs += " · **%s → %s on TTM**" % (roe["class_now"], roe["class_on_ttm"])
        fg = a.get("filing_gaps")
        fgs = ("—" if fg is None else ("%d open" % len(fg) if fg else "none")) + \
              (" · %d recovered" % len(a.get("recovered") or []) if a.get("recovered") else "")
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %d |" % (
            a["ticker"], a.get("type", "?"), a.get("latest_quarter_end", "—"), fgs,
            _fmt(eps.get("ttm"), "USD/shares") if eps.get("ttm") is not None else eps.get("status", "—"),
            _fmt(ni.get("ttm"), "USD") if ni.get("ttm") is not None else ni.get("status", "—"),
            pv, rs, len(a["flags"])))
    L += ["", "**Coverage codes** (oldest → newest, 8 quarters): R reported · q fiscal Q4 "
          "(FY minus 3 quarters, routine) · D derived from year-to-date · d the same for cash "
          "flow, where year-to-date reporting is the convention (routine) · C recovered from a "
          "co-registrant · - missing · . not tagged by this filer · ? not in this cache "
          "(a pre-2026-10-24 cache kept EPS, net income and equity only). A STALE-TAG metric's "
          "freshest tag stopped before the latest quarter; its old TTM is withheld.", ""]
    for a in audits:
        L += ["## %s — %s" % (a["ticker"], a.get("entity") or a.get("type")), ""]
        if a.get("type") != "FILER":
            L += ["- " + f for f in a["flags"]] + [""]
            continue
        L.append("CIK %s · feed fetched %s · latest quarter %s · slots %s → %s" % (
            a.get("cik"), a.get("fetched") or "?", a.get("latest_quarter_end"),
            (a.get("slots") or ["?"])[-1], (a.get("slots") or ["?"])[0]))
        L += ["", "| Metric | Tag | Coverage | TTM / latest | Basis |", "|---|---|---|---:|---|"]
        for key, r in a["metrics"].items():
            unit = SF.metric(key)[3]
            if r["kind"] == "flow":
                val = _fmt(r.get("ttm"), unit) if r.get("ttm") is not None else r["status"]
                basis = ("tag ends %s" % r["stale_ttm_end"]) if r.get("stale_ttm_end") \
                    else (r.get("ttm_detail") or "")
                if r.get("ttm_note"):
                    basis += " — " + r["ttm_note"]
            else:
                val = _fmt(r.get("latest"), unit) if r.get("latest") is not None else r["status"]
                basis = "at %s" % r.get("latest_end") if r.get("latest_end") else r["status"]
            L.append("| %s | %s | `%s` | %s | %s |" % (r["label"], r.get("ttm_tag") or r.get("tag") or "—",
                                                      r.get("coverage", ""), val, basis))
        if a.get("prompt"):
            L += ["", "**The prompt's block** (%s):" % a.get("prompt_period"), "",
                  "| Line | Shown | Period | SEC, same period | Verdict | TTM to the same end |",
                  "|---|---:|---|---:|---|---:|"]
            for p in a["prompt"]:
                L.append("| %s | %s | %s | %s | %s | %s |" % (
                    p["label"], p["shown"], p["period"], p["sec_fmt"], p["verdict"],
                    p.get("ttm_fmt", "—")))
        roe = a.get("roe") or {}
        if roe.get("class_roe") is not None:
            L += ["", "**Value-card ROE:** class %.1f%% (%s, numerator %.1fQ old) · EDGAR quarter "
                  "x4 %s · TTM %s" % (roe["class_roe"], roe.get("class_basis"), roe.get("num_age") or 0,
                                      "%.1f%%" % roe["q4_roe"] if roe.get("q4_roe") is not None else "—",
                                      "%.1f%%" % roe["ttm_roe"] if roe.get("ttm_roe") is not None else "—")]
            if roe.get("class_on_ttm"):
                L[-1] += (" · class %s (ratio %.2f); on TTM ROE it would read **%s** (%.2f) - "
                          "counterfactual, not applied (DP-V3)" % (
                              roe["class_now"], roe["ratio_on_ttm"] * roe["ttm_roe"] / roe["class_roe"],
                              roe["class_on_ttm"], roe["ratio_on_ttm"]))
        if a["flags"]:
            L += ["", "Flags:"] + ["- " + f for f in a["flags"]]
        L.append("")
    if refs:
        L += ["## Outside reference, basis-aware", "",
              "| Ticker | Metric | Reference (basis, as of) | Prompt shows | SEC on that basis | Verdict |",
              "|---|---|---|---|---|---|"]
        for r in refs:
            L.append("| %s | %s | %s (%s, %s) | %s | %s (%s) | %s |" % (
                r["ticker"], r["label"], r["reference"], r["basis"], r.get("as_of") or "—",
                r.get("prompt_shows") or "—", r.get("ours") or "—", r.get("ours_basis") or "—",
                r["verdict"]))
        L.append("")
    L += ["*Advisory-only · no orders · not financial advice.*"]
    return "\n".join(L)


def findings(audits, refs):
    n = 0
    for a in audits:
        for f in a["flags"]:
            if f.startswith(("FILING-GAP", "QUARTER-GAP", "PROMPT-MISMATCH")):
                n += 1
    n += sum(1 for r in refs if r["verdict"] == "DISAGREES")
    return n


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _cache_only(tk, cik_map, any_version=True):
    cik = (cik_map or {}).get(tk)
    if not cik:
        return None, "no CIK (fund, or not an SEC registrant)"
    p = SF.cache_path(cik)
    if not os.path.exists(p):
        return None, "not cached (run without --offline)"
    with open(p, encoding="utf-8") as fh:
        cf = json.load(fh)
    return cf, "cache v%s (offline)" % cf.get("slim_version", "?")


def _offline_cik_map():
    """CIK by ticker from the cached files' entity names is not possible, so
    offline mode reads the map the last online run saved."""
    p = os.path.join(SF.CACHE_DIR, "cik_map.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def run(args, today=None, ec=None, quiet=False):
    today = today or dt.date.today()
    d, names, _base = universe(args)
    if not names:
        print("SEC DATA AUDIT COULD NOT RUN: no session log with signal rows, and no --tickers.")
        return 2, None
    funds = set()
    if os.path.exists(args.quotes):
        try:
            with open(args.quotes, encoding="utf-8") as fh:
                funds = {t for t, q in json.load(fh).get("quotes", {}).items() if q.get("is_etf")}
        except (OSError, ValueError):
            pass
    if args.offline:
        cik_map = _offline_cik_map()
    else:
        if ec is None:
            try:
                import edgar_client as ec
            except Exception as e:                      # noqa: BLE001
                print("SEC DATA AUDIT COULD NOT RUN: %s" % e)
                return 2, None
        SF.standalone_budget(ec)              # this process only (sec_facts docstring)
        cik_map = ec.load_cik_map({}) or {}
        if cik_map:
            os.makedirs(SF.CACHE_DIR, exist_ok=True)
            with open(os.path.join(SF.CACHE_DIR, "cik_map.json"), "w", encoding="utf-8") as fh:
                json.dump({t: cik_map[t] for t in names if t in cik_map}, fh)
    inputs_path = args.inputs or latest_inputs()
    blocks = prompt_blocks(inputs_path)
    vrecs, exhibit = {}, None
    try:
        import value_card as VC
        ex = VC.find_exhibits(".")
        if ex:
            exhibit = ex[max(ex)]
            vrecs, _blocked = VC.parse_exhibit(exhibit)
    except Exception:                                   # noqa: BLE001
        pass
    audits, cfs = [], {}
    for tk in names:
        if tk in funds:
            audits.append(dict(ticker=tk, type="FUND", flags=["FUND: no EPS or statements to audit"]))
            continue
        if args.offline:
            cf, src = _cache_only(tk, cik_map)
        else:
            cf, src = SF.fetch(tk, cik_map, args.max_age_days, ec=ec, today=today)
        cfs[tk] = cf
        audits.append(audit_name(tk, cf, src, today, blocks.get(tk), vrecs.get(tk)))
    refs = []
    if args.reference:
        for r in read_reference(args.reference):
            if r.get("error"):
                refs.append(dict(ticker=r.get("ticker", "?"), label=r.get("metric", "?"),
                                 reference=r.get("value", "?"), basis="?", verdict="UNREADABLE"))
                continue
            cf = cfs.get(r["ticker"])
            if cf is None and r["ticker"] not in cfs:
                cf, _s = (_cache_only(r["ticker"], cik_map) if args.offline else
                          SF.fetch(r["ticker"], cik_map, args.max_age_days, ec=ec, today=today))
            refs.append(reconcile_reference(r, cf, blocks.get(r["ticker"])))
    day = args.date or today.isoformat()
    md = render(day, audits, refs, inputs_path, exhibit)
    stem = args.out or "sec_data_audit_%s" % day
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(dict(date=day, audits=audits, reference=refs), fh, indent=1, default=str)
    n = findings(audits, refs)
    if not quiet:
        print(md)
        print("\nWrote: %s.md (%d names; %d finding(s))" % (stem, len(audits), n))
    return (1 if n else 0), dict(audits=audits, reference=refs)


def main(argv=None):
    ap = argparse.ArgumentParser(description="SEC data-gap audit for the value layer.")
    ap.add_argument("--add", default=None, help="comma list added to the latest log's names")
    ap.add_argument("--tickers", default=None, help="comma list INSTEAD of the latest log's")
    ap.add_argument("--tickers-file", default=None)
    ap.add_argument("--reference", default=None, help="CSV: ticker,metric,value[,basis][,as_of][,source]")
    ap.add_argument("--inputs", default=None, help="captured inputs (default: the latest logs\\inputs_*.jsonl)")
    ap.add_argument("--quotes", default="quote_dump.json")
    ap.add_argument("--max-age-days", type=float, default=7.0)
    ap.add_argument("--offline", action="store_true", help="cached files only; no SEC calls")
    ap.add_argument("--date", default=None)
    ap.add_argument("--out", default=None, help="output stem (default sec_data_audit_<date>)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    rc, _ = run(a)
    return rc


# --------------------------------------------------------------------------- #
# Selftest (offline: a fake edgar_client, fixture facts, a temp directory)
# --------------------------------------------------------------------------- #
def selftest():
    import shutil
    import tempfile
    fails = []

    def check(name, ok):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        ok or fails.append(name)

    def f(s, e, v, accn="a", form="10-Q", filed="2026-08-01"):
        return {"start": s, "end": e, "val": v, "accn": accn, "form": form, "filed": filed}

    def inst(e, v, accn="a", form="10-Q"):
        return {"end": e, "val": v, "accn": accn, "form": form, "filed": "2026-08-01"}

    aaa = {"cik": 1, "entityName": "AAA CORP", "facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            f("2025-07-01", "2025-09-30", 100e9), f("2025-01-01", "2025-12-31", 420e9, form="10-K"),
            f("2025-01-01", "2025-03-31", 100e9), f("2025-04-01", "2025-06-30", 105e9),
            f("2026-01-01", "2026-03-31", 110e9), f("2026-04-01", "2026-06-30", 109.4e9)]}},
        "NetIncomeLoss": {"units": {"USD": [
            f("2025-07-01", "2025-09-30", 30e9), f("2025-01-01", "2025-12-31", 120e9, form="10-K"),
            f("2025-01-01", "2025-03-31", 28e9), f("2025-04-01", "2025-06-30", 29e9),
            f("2026-01-01", "2026-03-31", 31e9), f("2026-04-01", "2026-06-30", 29.8e9)]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            f("2026-01-01", "2026-03-31", 40e9), f("2026-01-01", "2026-06-30", 80e9)]}},
        "GrossProfit": {"units": {"USD": [
            f("2020-01-01", "2020-03-31", 1e9), f("2020-04-01", "2020-06-30", 1e9),
            f("2020-07-01", "2020-09-30", 1e9), f("2020-10-01", "2020-12-31", 1e9)]}},
        "Assets": {"units": {"USD": [inst("2026-06-30", 383.3e9)]}},
        "StockholdersEquity": {"units": {"USD": [inst("2026-06-30", 107.5e9)]}}}},
        "periodic": [dict(form="10-Q", report="2026-06-30", accn="a", filed="2026-07-31")]}
    # BBB: the DOW shape - the Q2 10-Q's facts sit under a co-registrant
    bbb_full = {"cik": 2, "entityName": "BBB INC", "facts": {"us-gaap": {
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            f("2025-01-01", "2025-03-31", -0.43, "k1"), f("2025-04-01", "2025-06-30", -1.18, "k2"),
            f("2025-07-01", "2025-09-30", 0.08, "k3"), f("2025-01-01", "2025-12-31", -3.70, "k4", "10-K"),
            f("2026-01-01", "2026-03-31", -0.74, "q1"), f("2026-01-01", "2026-09-30", 0.88, "q3"),
            f("2026-07-01", "2026-09-30", 0.62, "q3")]}}}}}
    ifrs = {"cik": 3, "entityName": "CCC LTD", "facts": {"ifrs-full": {}}}

    class FakeEC:
        XBRL_FACTS_URL = "facts:{cik10}"
        _last_fetch = {"reason": "test"}

        @staticmethod
        def load_cik_map(_c):
            return {"AAA": "0000000001", "BBB": "0000000002", "CCC": "0000000003"}

        @staticmethod
        def _http_get(url, as_json=False):
            return {"facts:0000000001": aaa, "facts:0000000002": bbb_full,
                    "facts:0000000003": ifrs}.get(url)

        @staticmethod
        def fetch_submissions(cik10):
            return {"cik": cik10}

        @staticmethod
        def _recent_rows(subs):
            if subs["cik"] == "0000000002":
                return [dict(form="10-Q", reportDate="2026-09-30", accessionNumber="q3", filingDate="2026-10-23"),
                        dict(form="10-Q", reportDate="2026-06-30", accessionNumber="q2", filingDate="2026-07-24"),
                        dict(form="10-Q", reportDate="2026-03-31", accessionNumber="q1", filingDate="2026-04-24")]
            if subs["cik"] == "0000000001":
                return [dict(form="10-Q", reportDate="2026-06-30", accessionNumber="a", filingDate="2026-07-31")]
            return []

        @staticmethod
        def _facts_from_co_registrant(cik10, accn, report):
            if accn == "q2":
                return ({"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": [
                    f("2026-04-01", "2026-06-30", 1.01, "q2"), f("2026-01-01", "2026-06-30", 0.27, "q2")]}}}}},
                        "0000000029")
            return None, None

    tmp = tempfile.mkdtemp(prefix="secaudit_")
    cwd = os.getcwd()
    try:
        os.chdir(tmp)
        os.makedirs("logs")
        with open(os.path.join("logs", "signals_2026-10-23.log"), "w", encoding="utf-8") as fh:
            for t in ("AAA", "BBB", "CCC", "SPY"):
                fh.write('x | INFO | Signal JSON: {"ticker": "%s", "signal": "HOLD"}\n' % t)
        block = ("Financial statements (XBRL, 10-Q Q3 FY2026, period ended 2026-06-30):\n"
                 "  Revenue                    $109.4B  YoY +16.4%\n"
                 "  Net income                  $31.0B  YoY +27.1%\n"
                 "  Operating cash flow         $80.0B  YoY +43.1%  [6M YTD]\n"
                 "  Total assets               $383.3B  YoY +15.6%\n")
        with open(os.path.join("logs", "inputs_2026-10-23.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"ticker": "AAA", "extra_context": "--- SEC ---\n" + block}) + "\n")
        with open("quote_dump.json", "w", encoding="utf-8") as fh:
            json.dump({"quotes": {"SPY": {"is_etf": True}}}, fh)
        with open("ref.csv", "w", encoding="utf-8") as fh:
            fh.write("ticker,metric,value,basis,as_of,source\n"
                     "AAA,Net income,123.8b,TTM,2026-06-30,ms\n"      # 30 + 33 + 31 + 29.8
                     "AAA,Revenue,109.4b,TTM,2026-06-30,ms\n"         # really the quarter
                     "AAA,Total assets,383.27b,,2026-06-30,ms\n"
                     "BBB,Diluted EPS,-1.82,TTM,2026-06-30,ms\n"
                     "AAA,Net income,999b,TTM,2026-06-30,ms\n")
        ns = argparse.Namespace(add="ZZZ", tickers=None, tickers_file=None, reference="ref.csv",
                                inputs=None, quotes="quote_dump.json", max_age_days=7.0,
                                offline=False, date="2026-10-24", out=None)
        rc, res = run(ns, today=dt.date(2026, 10, 24), ec=FakeEC, quiet=True)
        A = {a["ticker"]: a for a in res["audits"]}
        check("the universe is the latest log's names plus --add (ZZZ), funds named",
              list(A) == ["AAA", "BBB", "CCC", "SPY", "ZZZ"] and A["SPY"]["type"] == "FUND")
        check("an IFRS filer says so", A["CCC"]["type"] == "IFRS")
        gp = A["AAA"]["metrics"]["gross_profit"]
        check("a tag that stopped in 2020 is STALE-TAG, its old TTM withheld (RTX, JPM case)",
              gp["status"] == "STALE-TAG" and gp["ttm"] is None)
        ocf = A["AAA"]["metrics"]["ocf"]
        check("a cash-flow quarter derived from year-to-date is routine: coded d, not flagged",
              ocf["coverage"].endswith("d") and
              not any(x.startswith("DERIVED Operating cash flow") for x in A["AAA"]["flags"]))
        check("a name with no CIK is reported, not dropped", A["ZZZ"]["type"].endswith("NO-FACTS"))
        b = A["BBB"]
        check("a co-registrant 10-Q is RECOVERED on its accession; no filing gap remains",
              b["recovered"] and b["recovered"][0]["from_cik"] == "0000000029" and not b["filing_gaps"])
        cov = b["metrics"]["eps_diluted"]["coverage"]
        check("BBB EPS coverage reads q (fiscal Q4) and C (recovered) where they belong",
              cov.endswith("RqRCR") or cov.endswith("qRCR"))
        check("BBB TTM EPS uses the recovered Q2 (1.01), not a derivation",
              abs(b["metrics"]["eps_diluted"]["ttm"] - (-2.17 - 0.74 + 1.01 + 0.62)) < 1e-6)
        check("a recovered quarter is flagged RECOVERED-QUARTER, never DERIVED",
              any(x.startswith("RECOVERED-QUARTER Diluted EPS") for x in b["flags"])
              and not any(x.startswith("DERIVED Diluted EPS") for x in b["flags"]))
        p = {x["label"]: x for x in A["AAA"]["prompt"]}
        check("the prompt's quarter revenue MATCHES SEC for the same quarter",
              p["Revenue"]["verdict"] == "MATCH")
        check("a prompt figure that differs from SEC for the same period is a MISMATCH",
              p["Net income"]["verdict"] == "MISMATCH")
        check("a [6M YTD] line is compared with the six-month figure",
              p["Operating cash flow"]["verdict"] == "MATCH" and "6M YTD" in p["Operating cash flow"]["period"])
        check("an instant line matches at the period end", p["Total assets"]["verdict"] == "MATCH")
        R = res["reference"]
        check("a TTM reference that equals SEC's TTM AGREES", R[0]["verdict"] == "AGREES")
        check("a 'TTM' reference that is really the quarter is EXPLAINED by basis",
              R[1]["verdict"].startswith("EXPLAINED: quarter ending 2026-06-30"))
        check("a balance-sheet reference agrees within its rounding", R[2]["verdict"] == "AGREES")
        check("BBB's TTM EPS as of 06-30 agrees with -1.82 (recovered Q2)",
              R[3]["verdict"] in ("AGREES",) or R[3]["verdict"].startswith("EXPLAINED"))
        check("a figure no basis explains DISAGREES", R[4]["verdict"] == "DISAGREES")
        check("findings set the exit code (one mismatch, one disagreement)", rc == 1)
        check("the report and its json are written", os.path.exists("sec_data_audit_2026-10-24.md")
              and os.path.exists("sec_data_audit_2026-10-24.json"))
        ns2 = argparse.Namespace(**dict(vars(ns), add=None, reference=None, offline=True,
                                        out="offline"))
        rc2, res2 = run(ns2, today=dt.date(2026, 10, 24), quiet=True)
        check("--offline reads the cache only (no SEC calls) and still audits",
              res2 and {a["ticker"] for a in res2["audits"]} == {"AAA", "BBB", "CCC", "SPY"})
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)
    print("  sec_data_audit selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
