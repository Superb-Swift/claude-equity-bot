#!/usr/bin/env python3
"""
sec_facts.py - the value layer's one reader of SEC companyfacts: the metric
map, the slim cache, quarter series with every derivation labelled, TTM as of
any date, balance-sheet instants, and the recovery of a quarter SEC filed
under a co-registrant's CIK.

WHY ONE MODULE (2026-10-24)
    ttm_eps.py (V2) and sec_data_audit.py read the same feed. Two readers
    would disagree exactly where it matters - a missing quarter, a tag switch
    - so the rules live here once and both tools call them.

WHAT IT IS NOT
    Not what the model sees. The prompt's statement block is built by
    edgar_client.extract_financials and is frozen under DP-3C-ai. This module
    MIRRORS that block's concept map (METRICS; the selftest fails if the two
    drift) so an audit checks the same concepts, but nothing here reaches the
    prompt, an endpoint, a gate or the paste (DP-V1).

THE GAP CLASSES IT HANDLES, each from a live case
    * TAG SWITCH: the freshest candidate tag wins, ties to the preference
      order (SNOW's equity, 2026-10-23).
    * MISSING FISCAL Q4: derived as FY minus Q1..Q3 (the usual 10-K case).
    * MISSING QUARTER INSIDE A YEAR: derived from year-to-date facts, e.g.
      Q2 = 9M - Q1 - Q3, or Q3 = 9M - H1 (DOW Q2 2026, found 2026-10-24).
    * COMBINED FILING: a 10-Q co-registered with a subsidiary, whose facts
      SEC files under the OTHER CIK (DOW's Q2 2026 under The Dow Chemical
      Company, CIK 29915; edgar_client.py, analyst note of 2026-08-26).
      Recovered on the SAME ACCESSION only, never merged across registrants,
      by edgar_client's own _facts_from_co_registrant.
    A recovered quarter beats a derived one; every derived one is labelled.

    A derived per-share figure (EPS) is approximate: share counts move between
    quarters, so FY - (Q1+Q2+Q3) can differ from the filed Q4 by a cent or two.

USAGE
    import sec_facts as SF
    cf, src = SF.fetch("DOW", cik_map, max_age_days=7)
    tag, rows = SF.rows_for(cf, SF.metric("net_income"))
    t = SF.ttm(rows)                 # dict(value, detail, end, quarters, ...)
    pit = SF.point_in_time(cf, date) # only what SEC had published by `date` (DP-V4)
    SF.ttm_roe(pit, date)            # the value card's class basis (DP-V4)
    SF.fundamentals(pit, date)       # growth, earnings quality, balance sheet
    python sec_facts.py --selftest   (offline, fixtures)

DP-V4 (2026-10-24) moved the value card's class onto 12-month ROE. The class,
its robustness and the DP-V2 ledger all read ttm_roe() on point_in_time()
facts, so a class dated d uses only filings SEC had published by d.

Advisory-only - no orders - not financial advice.
"""

import datetime as dt
import json
import os
import sys

CACHE_DIR = "valuation_cache"
# 2 (2026-10-23): the slim cache records the filer's taxonomies.
# 3 (2026-10-24): every audited metric's tags, the filer's periodic-filing
#   list, and any co-registrant recovery. An older cache is re-fetched once.
SLIM_VERSION = 3
PERIODIC_FORMS = ("10-Q", "10-K", "10-Q/A", "10-K/A")
RECOVERY_LOOKBACK_DAYS = 800          # two years of quarters, plus the YoY base

# The metric map. Mirrors edgar_client.FINANCIAL_CONCEPTS (what the PROMPT can
# show), same labels and same tag order. Tags the value layer reads beyond the
# prompt's (Basic EPS as a last resort) are appended at the END of a list, never
# ahead of the prompt's order. (key, label, kind, unit, tags)
METRICS = (
    ("revenue", "Revenue", "flow", "USD",
     ("RevenueFromContractWithCustomerExcludingAssessedTax",
      "RevenueFromContractWithCustomerIncludingAssessedTax",
      "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet")),
    ("gross_profit", "Gross profit", "flow", "USD", ("GrossProfit",)),
    ("operating_income", "Operating income", "flow", "USD", ("OperatingIncomeLoss",)),
    ("net_income", "Net income", "flow", "USD", ("NetIncomeLoss", "ProfitLoss")),
    ("eps_diluted", "Diluted EPS", "flow", "USD/shares",
     ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
      "EarningsPerShareBasic")),
    ("ocf", "Operating cash flow", "flow", "USD",
     ("NetCashProvidedByUsedInOperatingActivities",
      "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")),
    ("assets", "Total assets", "instant", "USD", ("Assets",)),
    ("liabilities", "Total liabilities", "instant", "USD", ("Liabilities",)),
    ("equity", "Shareholders equity", "instant", "USD",
     ("StockholdersEquity",
      "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")),
    ("cash", "Cash and equivalents", "instant", "USD",
     ("CashAndCashEquivalentsAtCarryingValue",)),
    ("lt_debt", "Long-term debt", "instant", "USD",
     ("LongTermDebtNoncurrent", "LongTermDebt")),
)
VALUE_LAYER_EXTRA = ("EarningsPerShareBasic",)   # beyond the prompt's lists


def metric(key):
    for m in METRICS:
        if m[0] == key:
            return m
    raise KeyError(key)


def metric_by_label(label):
    for m in METRICS:
        if m[1] == label:
            return m
    return None


def slim_tags():
    out = []
    for m in METRICS:
        for t in m[4]:
            if t not in out:
                out.append(t)
    return tuple(out)


def _d(s):
    return dt.date.fromisoformat(s)


# --------------------------------------------------------------------------- #
# Tags
# --------------------------------------------------------------------------- #
def tag_ages(cf, tags, unit):
    """[(tag, last end date or None)] in preference order."""
    gaap = (cf or {}).get("facts", {}).get("us-gaap", {})
    out = []
    for t in tags:
        rows = gaap.get(t, {}).get("units", {}).get(unit) or []
        last = max((r.get("end", "") for r in rows), default="") or None
        out.append((t, last))
    return out


def rows_for(cf, m_or_tags, unit=None):
    """(tag, rows) for the candidate whose LATEST fact is the most recent; a
    tie goes to the earlier tag (preference order). Accepts a METRICS entry or
    (tags, unit). The unit is matched EXACTLY, so 'USD' never picks up a
    'USD/shares' series."""
    if unit is None:
        tags, unit = m_or_tags[4], m_or_tags[3]
    else:
        tags = m_or_tags
    gaap = (cf or {}).get("facts", {}).get("us-gaap", {})
    best = None
    for i, t in enumerate(tags):
        rows = gaap.get(t, {}).get("units", {}).get(unit) or []
        if not rows:
            continue
        key = (max((r.get("end", "") for r in rows), default=""), -i)
        if best is None or key > best[0]:
            best = (key, t, rows)
    return (best[1], best[2]) if best else (None, [])


# --------------------------------------------------------------------------- #
# Durations and quarters
# --------------------------------------------------------------------------- #
def bucket(days):
    if 80 <= days <= 100:
        return "Q"
    if 170 <= days <= 195:
        return "H"
    if 260 <= days <= 285:
        return "9M"
    if 350 <= days <= 380:
        return "FY"
    return None


_N_QUARTERS = {"Q": 1, "H": 2, "9M": 3, "FY": 4}


def durations(rows):
    """{(start, end): dict(val, filed, accn, form, src)} keeping the latest-filed value."""
    out = {}
    for r in rows:
        if "start" not in r or "end" not in r or r.get("val") is None:
            continue
        k = (_d(r["start"]), _d(r["end"]))
        filed = r.get("filed", "")
        if k not in out or filed > out[k]["filed"]:
            out[k] = dict(val=float(r["val"]), filed=filed, accn=r.get("accn"),
                          form=r.get("form"),
                          src=("recovered from CIK %s" % r["recovered_from"])
                          if r.get("recovered_from") else "reported")
    return out


def _inside(q, s, e):
    return sorted((k for k in q if k[0] >= s - dt.timedelta(days=5)
                   and k[1] <= e + dt.timedelta(days=5)), key=lambda k: k[0])


def _one_slot(inside, s, e):
    """The single quarter-length hole inside [s, e] not covered by `inside`,
    or None when there is not exactly one."""
    holes, cur = [], s
    for k in inside:
        if (k[0] - cur).days > 10:
            holes.append((cur, k[0] - dt.timedelta(days=1)))
        cur = max(cur, k[1] + dt.timedelta(days=1))
    if (e - cur).days >= 10:
        holes.append((cur, e))
    if len(holes) != 1:
        return None
    h = holes[0]
    return h if bucket((h[1] - h[0]).days) == "Q" else None


def quarters(rows):
    """{(start, end): dict(val, source)} for every three-month quarter the
    rows give or imply. `source` is 'reported', 'recovered from CIK n', or
    'derived: <how>'. Derivations, repeated until nothing new appears:
      A  a cumulative period (H, 9M, FY) minus the quarters inside it, when
         exactly one quarter-length hole remains;
      B  a cumulative period minus a shorter one with the same start, when
         they end one quarter apart (Q3 = 9M - H1)."""
    dur = durations(rows)
    q = {k: dict(val=v["val"], source=v["src"]) for k, v in dur.items()
         if bucket((k[1] - k[0]).days) == "Q"}
    cum = {k: v["val"] for k, v in dur.items()
           if bucket((k[1] - k[0]).days) in ("H", "9M", "FY")}
    for _ in range(4):
        new = 0
        for (s, e), v in sorted(cum.items(), key=lambda kv: kv[0][1]):
            b = bucket((e - s).days)
            inside = _inside(q, s, e)
            if len(inside) == _N_QUARTERS[b] - 1:
                slot = _one_slot(inside, s, e)
                if slot and not any(abs((k[1] - slot[1]).days) <= 7 for k in q):
                    q[slot] = dict(val=v - sum(q[k]["val"] for k in inside),
                                   source="derived: %s %s..%s minus %d quarter(s)"
                                   % (b, s, e, len(inside)))
                    new += 1
        # B: cumulative minus a shorter cumulative (or Q1) with the same start
        starts = dict(cum)
        starts.update({k: v["val"] for k, v in q.items()})
        for (s2, e2), v2 in starts.items():
            for (s1, e1), v1 in starts.items():
                if abs((s1 - s2).days) > 5 or e1 >= e2:
                    continue
                if bucket((e2 - e1).days) != "Q":
                    continue
                slot = (e1 + dt.timedelta(days=1), e2)
                if any(abs((k[1] - e2).days) <= 7 and bucket((k[1] - k[0]).days) == "Q"
                       for k in q):
                    continue
                q[slot] = dict(val=v2 - v1, source="derived: %s %s..%s minus %s %s..%s"
                               % (bucket((e2 - s2).days), s2, e2,
                                  bucket((e1 - s1).days), s1, e1))
                new += 1
        if not new:
            break
    return q


def source_kind(src):
    """'reported', 'fiscal-q4' (FY minus three quarters: routine for every 10-K
    filer), 'derived' (a hole inside a year, filled from year-to-date facts) or
    'recovered' (a co-registrant's facts on the same accession)."""
    if src == "reported":
        return "reported"
    if src.startswith("recovered"):
        return "recovered"
    if src.startswith("derived: FY ") and (src.endswith("minus 3 quarter(s)")
                                           or " minus 9M " in src):
        return "fiscal-q4"
    return "derived"


def short_source(src):
    """A compact label for a card or table: 'derived (9M minus 2 quarters)',
    'derived (9M minus H)', 'recovered (CIK 0000029915)', 'reported'."""
    k = source_kind(src)
    if k == "recovered":
        return "recovered (CIK %s)" % src.rsplit(" ", 1)[-1]
    if k in ("derived", "fiscal-q4"):
        parts = src[len("derived: "):].split(" ")
        if parts and parts[0] in ("H", "9M", "FY") and "minus" in src:
            n = src.split("minus ", 1)[1].split(" ")[0]
            if n in ("Q", "H", "9M", "FY"):
                return "derived (%s minus %s)" % (parts[0], n)
            return "derived (%s minus %s quarter%s)" % (parts[0], n, "" if n == "1" else "s")
        return "derived (cumulative difference)"
    return k


def _chain(q, last_end, n=4):
    """n consecutive quarters ending at the quarter whose end is last_end."""
    ends = sorted(q, key=lambda k: k[1])
    first = [k for k in ends if k[1] == last_end]
    if not first:
        return None, "no quarter ends %s" % last_end
    chain = [first[-1]]
    for _ in range(n - 1):
        prev_end = chain[-1][0] - dt.timedelta(days=1)
        cand = [k for k in ends if abs((k[1] - prev_end).days) <= 10]
        if not cand:
            return None, "gap before the quarter ending %s" % chain[-1][1]
        chain.append(max(cand, key=lambda k: k[1]))
    return list(reversed(chain)), None


def ttm(rows, as_of=None):
    """Trailing four quarters ending at the latest quarter end <= as_of.
    dict(value, detail, end, quarters=[(start, end, source)], derived=n, why)."""
    q = quarters(rows)
    if as_of is not None:
        q = {k: v for k, v in q.items() if k[1] <= as_of}
    if not q:
        return dict(value=None, detail="no quarterly facts", end=None, quarters=[],
                    derived=0, unusual=0, why="no quarterly facts")
    last_end = max(k[1] for k in q)
    chain, why = _chain(q, last_end)
    if not chain:
        return dict(value=None, detail=why, end=None, quarters=[], derived=0, unusual=0,
                    why=why)
    srcs = [(k[0], k[1], q[k]["source"]) for k in chain]
    derived = [x for x in srcs if x[2] != "reported"]
    unusual = [x for x in srcs if source_kind(x[2]) in ("derived", "recovered")]
    detail = "quarters ending %s" % ", ".join(str(k[1]) for k in chain)
    if derived:
        detail += "; " + "; ".join("Q ending %s %s" % (e, src) for _s, e, src in derived)
    return dict(value=sum(q[k]["val"] for k in chain), detail=detail, end=last_end,
                quarters=srcs, derived=len(derived), unusual=len(unusual), why=None)


def best_ttm(cf, m, as_of=None):
    """TTM for metric m, trying its candidate tags freshest first and taking the
    first that builds a full four-quarter chain. dict as ttm() plus `tag` and
    `note` (set when the tag is not the freshest one, so a fallback is never
    silent). DOW's NetIncomeLoss has no FY2025 fact, so its Q4 2025 cannot be
    derived; ProfitLoss (which includes noncontrolling interest) can."""
    tags, unit = m[4], m[3]
    ages = sorted(((last or "", -i, t) for i, (t, last) in enumerate(tag_ages(cf, tags, unit))
                   if last), reverse=True)
    first, why = None, "no tag carries data"
    gaap = (cf or {}).get("facts", {}).get("us-gaap", {})
    for n, (_last, _i, t) in enumerate(ages):
        t_res = ttm(gaap[t]["units"][unit], as_of)
        if first is None:
            first, why = t, t_res["why"]
        if t_res["value"] is not None:
            t_res["tag"] = t
            t_res["note"] = (None if n == 0 else "%s cannot build a TTM (%s); %s used"
                             % (first, why, t))
            return t_res
    return dict(value=None, detail=why, end=None, quarters=[], derived=0, unusual=0,
                why=why, tag=first, note=None)


def period_value(rows, end, b):
    """The value for the period of bucket b ('Q', 'H', '9M', 'FY') ending on
    `end` (+-7 days): (value, source) or (None, why). Quarters may be derived."""
    if b == "Q":
        q = quarters(rows)
        hit = [k for k in q if abs((k[1] - end).days) <= 7]
        if hit:
            k = max(hit, key=lambda k: k[1])
            return q[k]["val"], q[k]["source"]
        return None, "no quarter ends %s" % end
    for k, v in durations(rows).items():
        if abs((k[1] - end).days) <= 7 and bucket((k[1] - k[0]).days) == b:
            return v["val"], v["src"]
    return None, "no %s period ends %s" % (b, end)


def latest_instant(rows, as_of=None):
    """(value, end date string) of the latest instant <= as_of, latest filed."""
    best = None
    for r in rows:
        if "end" in r and "start" not in r and r.get("val") is not None:
            if as_of is not None and _d(r["end"]) > as_of:
                continue
            k = (r["end"], r.get("filed", ""))
            if best is None or k > best[0]:
                best = (k, float(r["val"]))
    return (best[1], best[0][0]) if best else (None, None)


def instant_at(rows, end):
    """Value of the instant on `end` (+-7 days), latest filed, or None."""
    best = None
    for r in rows:
        if "end" in r and "start" not in r and r.get("val") is not None:
            if abs((_d(r["end"]) - end).days) <= 7:
                k = r.get("filed", "")
                if best is None or k > best[0]:
                    best = (k, float(r["val"]))
    return best[1] if best else None


# --------------------------------------------------------------------------- #
# Point in time, 12-month ROE and the value card's fundamentals (DP-V4, 2026-10-24)
# --------------------------------------------------------------------------- #
EQUITY_MAX_AGE_DAYS = 400       # as ttm_eps: an equity older than this is history, not a book
STALE_TAG_DAYS = 10             # a metric whose TTM ends further behind is not current (as the audit)
YEAR_BACK_DAYS = 358            # "a year earlier": the window ending ~52 weeks before


def point_in_time(cf, cutoff, strict=True):
    """A copy of cf holding only the facts FILED before `cutoff` (strict) or on
    or before it. A fact with no filing date is dropped, never assumed public.
    DP-V4: a class dated d reads only what SEC had published by d, so a ledger
    rebuilt after the fact sees exactly what a live run would have seen."""
    if cf is None:
        return None
    lim = cutoff.isoformat()
    gaap = {}
    for tag, node in ((cf.get("facts") or {}).get("us-gaap") or {}).items():
        units = {}
        for u, rows in (node.get("units") or {}).items():
            keep = [r for r in rows if r.get("filed")
                    and (r["filed"] < lim if strict else r["filed"] <= lim)]
            if keep:
                units[u] = keep
        if units:
            gaap[tag] = dict(node, units=units)
    out = {k: v for k, v in cf.items() if k != "facts"}
    out["facts"] = dict(cf.get("facts") or {}, **{"us-gaap": gaap})
    return out


def _unusual(t):
    return ["Q ending %s %s" % (e, short_source(src)) for _s, e, src in (t.get("quarters") or [])
            if source_kind(src) in ("derived", "recovered")]


def ttm_roe(cf, today):
    """12-month ROE, the DP-V4 class basis: TTM net income over shareholders'
    equity at the latest period end (the rule ttm_eps.read_name uses, so the
    card and the TTM exhibit agree). dict(roe (fraction; None when there is no
    figure), ni, ni_end, ni_tag, notes, equity, equity_end, equity_tag, why);
    `why` names the reason a class cannot be read, including a negative ROE."""
    t = best_ttm(cf, metric("net_income"))
    eq_tag, eq_rows = rows_for(cf, metric("equity"))
    eq, eq_end = latest_instant(eq_rows) if eq_rows else (None, None)
    notes = ["net income: " + x for x in _unusual(t)] if t["value"] is not None else []
    if t.get("note"):
        notes.append("net income: " + t["note"])
    out = dict(roe=None, ni=t["value"], ni_end=str(t["end"]) if t["end"] else None,
               ni_tag=t.get("tag"), notes=notes, equity=eq, equity_end=eq_end,
               equity_tag=eq_tag, why=None)
    if t["value"] is None:
        out["why"] = "no 12-month net income (%s)" % t["why"]
    elif eq is None:
        out["why"] = "no equity line"
    elif today is not None and (today - _d(eq_end)).days > EQUITY_MAX_AGE_DAYS:
        out["why"] = "equity last reported %s" % eq_end
    elif eq <= 0:
        out["why"] = "non-positive book equity"
    else:
        out["roe"] = t["value"] / eq
        if out["roe"] <= 0:
            out["why"] = "negative 12-month ROE"
        if t["end"] and _d(eq_end) < t["end"] - dt.timedelta(days=10):
            notes.append("equity as of %s predates the 12-month end %s" % (eq_end, t["end"]))
    return out


def _chg(now, then):
    """Relative change, signed by direction: (now - then) / |then|."""
    if now is None or then is None or then == 0:
        return None
    return (now - then) / abs(then)


def _div(a, b):
    return None if a is None or b is None or b == 0 else a / b


def fundamentals(cf, today):
    """The value card's under-the-hood panels for one filer, from SEC facts only.

    One 12-month window ending at the name's latest quarter. A metric whose
    window ends more than STALE_TAG_DAYS behind is not used (the audit's
    STALE-TAG rule), and every fallback or derivation is listed in `notes`.
      growth   12-month EPS, revenue and net income against the window a year
               earlier; the latest quarter against the same quarter a year earlier
      quality  operating cash flow / net income; operating cash flow / revenue
               (defined through a loss, where OCF/NI is not); gross and operating
               margin, now and a year earlier
      balance  at the latest period end: equity, liabilities (or assets minus
               equity, labelled), liabilities / equity, liabilities / assets
               (defined at any sign of equity), cash, long-term debt

    2026-10-29: the balance date is the equity's; with no usable equity line it
    is the latest total-assets date, so cash and liabilities / assets still read
    (PAA files partners' capital, not an equity tag, yet its cash is filed). The
    12-month class (ttm_roe) reads its own equity and is not affected."""
    out = dict(end=None, notes=[],
               growth={k: dict(ttm=None, year_ago=None, chg=None)
                       for k in ("eps", "revenue", "net_income")},
               quality=dict(ocf_to_ni=None, gross_margin=None, gross_margin_year_ago=None,
                            op_margin=None, op_margin_year_ago=None),
               balance=dict(end=None, equity=None, negative_equity=False))
    out["growth"].update({k: dict(quarter=None, year_ago=None, chg=None)
                          for k in ("q_eps", "q_revenue")})
    gaap = (cf or {}).get("facts", {}).get("us-gaap", {})
    tt = {k: best_ttm(cf, metric(k)) for k in
          ("revenue", "gross_profit", "operating_income", "net_income", "eps_diluted", "ocf")}
    ends = [t["end"] for k, t in tt.items()
            if t["value"] is not None and k in ("net_income", "eps_diluted", "revenue")]
    if not ends:
        out["notes"].append("no 12-month figures")
        return out
    end = max(ends)
    out["end"] = str(end)
    cur = {}
    for k, t in tt.items():
        if t["value"] is None:
            continue
        lab = metric(k)[1]
        if (end - t["end"]).days > STALE_TAG_DAYS:
            out["notes"].append("%s: %s ends %s, not used" % (lab, t["tag"], t["end"]))
            continue
        cur[k] = t
        if t.get("note"):
            out["notes"].append("%s: %s" % (lab, t["note"]))

    def rows(k):
        t = cur.get(k)
        return gaap.get(t["tag"], {}).get("units", {}).get(metric(k)[3], []) if t else []

    def yago(k):
        t = cur.get(k)
        if not t:
            return None
        y = ttm(rows(k), t["end"] - dt.timedelta(days=YEAR_BACK_DAYS))
        if y["value"] is None or not (350 <= (t["end"] - y["end"]).days <= 380):
            return None
        return y["value"]

    def q_yoy(k):
        t = cur.get(k)
        if not t:
            return None, None
        q = quarters(rows(k))
        now = [v["val"] for kk, v in q.items() if abs((kk[1] - t["end"]).days) <= 7]
        then = [v["val"] for kk, v in q.items()
                if abs((kk[1] - (t["end"] - dt.timedelta(days=364))).days) <= 10]
        return (now[0] if now else None), (then[0] if then else None)

    val = {k: (cur[k]["value"] if k in cur else None) for k in tt}
    ya = {k: yago(k) for k in tt}
    for k, name in (("eps_diluted", "eps"), ("revenue", "revenue"), ("net_income", "net_income")):
        out["growth"][name] = dict(ttm=val[k], year_ago=ya[k], chg=_chg(val[k], ya[k]))
    for k, name in (("eps_diluted", "q_eps"), ("revenue", "q_revenue")):
        n, p = q_yoy(k)
        out["growth"][name] = dict(quarter=n, year_ago=p, chg=_chg(n, p))
    ni, ocf = val["net_income"], val["ocf"]
    out["quality"] = dict(
        ocf_to_ni=_div(ocf, ni) if (ni is not None and ni > 0) else None,
        ocf_margin=_div(ocf, val["revenue"]),
        net_loss=(ni is not None and ni <= 0),
        gross_margin=_div(val["gross_profit"], val["revenue"]),
        gross_margin_year_ago=_div(ya["gross_profit"], ya["revenue"]),
        op_margin=_div(val["operating_income"], val["revenue"]),
        op_margin_year_ago=_div(ya["operating_income"], ya["revenue"]))
    eq_tag, eq_rows = rows_for(cf, metric("equity"))
    eq, eq_end = latest_instant(eq_rows) if eq_rows else (None, None)
    if eq is not None and today is not None and (today - _d(eq_end)).days > EQUITY_MAX_AGE_DAYS:
        out["notes"].append("equity: %s last reported %s, not used" % (eq_tag, eq_end))
        eq, eq_end = None, None
    bal_end = eq_end
    if bal_end is None:
        _a_tag, a_rows = rows_for(cf, metric("assets"))
        _a_val, a_end = latest_instant(a_rows) if a_rows else (None, None)
        if a_end and (today is None or (today - _d(a_end)).days <= EQUITY_MAX_AGE_DAYS):
            bal_end = a_end
    bal = dict(end=bal_end, equity=eq, negative_equity=(eq is not None and eq <= 0))
    if bal_end:
        at = _d(bal_end)

        def inst(k):
            _t, r = rows_for(cf, metric(k))
            return instant_at(r, at) if r else None
        assets, liab = inst("assets"), inst("liabilities")
        src = "reported"
        if liab is None and assets is not None and eq is not None:
            liab, src = assets - eq, "assets minus equity (includes any noncontrolling interest)"
            out["notes"].append("liabilities: derived as " + src)
        bal.update(assets=assets, liabilities=liab, liabilities_source=src if liab is not None else None,
                   liab_to_equity=_div(liab, eq) if eq and eq > 0 else None,
                   liab_to_assets=_div(liab, assets) if liab is not None else None,
                   cash=inst("cash"), lt_debt=inst("lt_debt"))
    out["balance"] = bal
    return out


# --------------------------------------------------------------------------- #
# Filing-level gaps and the co-registrant recovery
# --------------------------------------------------------------------------- #
def _has_fact_at(slim, report_date):
    for node in slim.get("facts", {}).get("us-gaap", {}).values():
        for rows in (node.get("units") or {}).values():
            for r in rows:
                if r.get("end") == report_date and r.get("form") in ("10-Q", "10-K"):
                    return True
    return False


def filing_gaps(cf, today=None):
    """Periodic filings (from the cached submissions list) whose report date
    has no fact in this feed, after any recovery: [dict(form, report, accn, filed)]."""
    today = today or dt.date.today()
    out = []
    for p in cf.get("periodic") or []:
        if p.get("form") not in ("10-Q", "10-K") or not p.get("report"):
            continue
        if (today - _d(p["report"])).days > RECOVERY_LOOKBACK_DAYS:
            continue
        if not _has_fact_at(cf, p["report"]):
            out.append(p)
    return out


def _slim_gaap(gaap):
    return {t: gaap[t] for t in slim_tags() if t in gaap}


def _merge_recovered(slim, subset, from_cik):
    gaap = slim.setdefault("facts", {}).setdefault("us-gaap", {})
    added = 0
    for t, node in _slim_gaap((subset.get("facts") or {}).get("us-gaap") or {}).items():
        dst = gaap.setdefault(t, {"units": {}}).setdefault("units", {})
        for u, rows in (node.get("units") or {}).items():
            have = {(r.get("start"), r.get("end"), r.get("accn")) for r in dst.get(u, [])}
            for r in rows:
                if (r.get("start"), r.get("end"), r.get("accn")) in have:
                    continue
                dst.setdefault(u, []).append(dict(r, recovered_from=from_cik))
                added += 1
    return added


def recover(slim, cik10, ec, today=None):
    """Fill filing-level gaps from a co-registrant on the SAME accession.
    Mutates slim; returns [dict(accn, report, from_cik, facts_added)]."""
    done = []
    for p in filing_gaps(slim, today):
        try:
            subset, cand = ec._facts_from_co_registrant(cik10, p["accn"], p["report"])
        except Exception:                               # noqa: BLE001
            subset, cand = None, None
        if subset:
            n = _merge_recovered(slim, subset, cand)
            done.append(dict(accn=p["accn"], report=p["report"], from_cik=cand,
                             facts_added=n))
    slim["recovered"] = (slim.get("recovered") or []) + done
    return done


def _periodic_list(ec, cik10):
    try:
        subs = ec.fetch_submissions(cik10)
        rows = ec._recent_rows(subs) if subs else None
    except Exception:                                   # noqa: BLE001
        rows = None
    if rows is None:
        return None
    return [dict(form=r.get("form"), report=r.get("reportDate"), accn=r.get("accessionNumber"),
                 filed=r.get("filingDate"))
            for r in rows if r.get("form") in PERIODIC_FORMS and r.get("reportDate")]


STANDALONE_EDGAR_SECONDS = 600.0


def standalone_budget(ec, seconds=STANDALONE_EDGAR_SECONDS):
    """Raise edgar_client's EDGAR time ceiling for THIS process only.

    The 120 s ceiling (DP-3C-j) bounds the morning run, where EDGAR time is
    taken from the signal window. ttm_eps and sec_data_audit run separately in
    the evening and make two calls per filer (companyfacts and submissions),
    plus any co-registrant recovery; under 120 s a full refresh of ~30 names
    could trip it and leave the rest NO READ. The bot's own run is a different
    process and keeps its ceiling; the SEC rate throttle in _http_get applies
    unchanged."""
    try:
        ec.EDGAR_MAX_SECONDS = max(float(getattr(ec, "EDGAR_MAX_SECONDS", 0) or 0), seconds)
    except Exception:                                   # noqa: BLE001
        pass


def cache_path(cik10):
    return os.path.join(CACHE_DIR, "companyfacts_%s.json" % cik10)


def console_safe(stream=None):
    """Let a redirected console lose a character instead of the run.

    value.bat runs step 7b with stdout redirected ('> nul'). A redirected
    stdout on Windows encodes with the ANSI code page (cp1252), which has no
    arrow (U+2192). On 2026-10-27 the audit wrote both exhibits, then died
    printing one, and value.bat read the traceback's exit 1 as 'has findings'.
    The exhibits are UTF-8 on disk; only the console copy may show a '?'."""
    s = stream or sys.stdout
    try:
        s.reconfigure(errors="replace")
    except Exception:                                   # noqa: BLE001
        pass


def cik_map_path(root="."):
    return os.path.join(root, CACHE_DIR, "cik_map.json")


def load_saved_cik_map(root="."):
    """The ticker -> CIK map the last online run saved beside the slim cache
    ({} if none), so an offline reader (value_card, the audit's --offline)
    can find each filer's file without a SEC call."""
    try:
        with open(cik_map_path(root), encoding="utf-8") as fh:
            m = json.load(fh)
        return m if isinstance(m, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cik_map(cik_map, names, root="."):
    """MERGE the CIKs of `names` into the saved map; it never shrinks, so an
    ad-hoc run on a few names cannot cost the value card its other filers."""
    if not cik_map:
        return
    cur = load_saved_cik_map(root)
    cur.update({t: cik_map[t] for t in names if t in cik_map})
    os.makedirs(os.path.join(root, CACHE_DIR), exist_ok=True)
    tmp = cik_map_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(cur.items())), fh)
    os.replace(tmp, cik_map_path(root))


def load_slim(tk, cik_map, root="."):
    """The cached slim companyfacts for a ticker, or None. Reads only."""
    cik = (cik_map or {}).get(tk)
    if not cik:
        return None
    try:
        with open(os.path.join(root, cache_path(cik)), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def fetch(tk, cik_map, max_age_days, ec=None, recover_gaps=True, today=None):
    """(slim companyfacts, source) or (None, why). Cached in valuation_cache\\
    (never edgar_cache\\), re-fetched when older than max_age_days or written
    by an older SLIM_VERSION."""
    cik = (cik_map or {}).get(tk)
    if not cik:
        return None, "no CIK (fund, or not an SEC registrant)"
    path = cache_path(cik)
    if os.path.exists(path):
        age = (dt.datetime.now().timestamp() - os.path.getmtime(path)) / 86400.0
        if age <= max_age_days:
            try:
                with open(path, encoding="utf-8") as fh:
                    cached = json.load(fh)
            except (OSError, ValueError):
                cached = {}
            if cached.get("slim_version") == SLIM_VERSION:
                return cached, "cache (%.1f d old)" % age
    if ec is None:
        import edgar_client as ec
    cf = ec._http_get(ec.XBRL_FACTS_URL.format(cik10=cik), as_json=True)
    if not cf:
        return None, "companyfacts fetch failed (%s)" % (ec._last_fetch.get("reason") or "?")
    gaap = cf.get("facts", {}).get("us-gaap", {})
    slim = {"cik": cf.get("cik"), "entityName": cf.get("entityName"),
            "slim_version": SLIM_VERSION, "taxonomies": sorted(cf.get("facts", {}).keys()),
            "fetched": dt.date.today().isoformat(), "facts": {"us-gaap": _slim_gaap(gaap)}}
    slim["periodic"] = _periodic_list(ec, cik)
    if recover_gaps and slim["periodic"]:
        recover(slim, cik, ec, today)
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(slim, fh)
    os.replace(tmp, path)
    return slim, "fetched"


# --------------------------------------------------------------------------- #
# Selftest
# --------------------------------------------------------------------------- #
def _f(s, e, v, filed="2026-08-01", accn="a1", form="10-Q"):
    return {"start": s, "end": e, "val": v, "filed": filed, "accn": accn, "form": form}


def selftest():
    fails = []

    def check(name, ok):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        ok or fails.append(name)

    # 1. a fiscal Q4 derived from the full year
    fy = [_f("2025-01-01", "2025-03-31", 1.0), _f("2025-04-01", "2025-06-30", 1.1),
          _f("2025-07-01", "2025-09-30", 1.2), _f("2025-01-01", "2025-12-31", 4.6, form="10-K"),
          _f("2026-01-01", "2026-03-31", 1.4), _f("2026-04-01", "2026-06-30", 1.5)]
    t = ttm(fy)
    check("TTM with a derived fiscal Q4 = 1.2 + 1.3 + 1.4 + 1.5",
          t["value"] is not None and abs(t["value"] - 5.4) < 1e-9 and t["derived"] == 1)
    # 2. DOW's shape: Q2 2026 absent, Q1, 9M and Q3 present
    dow = [_f("2025-07-01", "2025-09-30", 0.08), _f("2025-01-01", "2025-09-30", -1.53),
           _f("2025-01-01", "2025-12-31", -3.70, form="10-K"),
           _f("2025-01-01", "2025-03-31", -0.43), _f("2025-04-01", "2025-06-30", -1.18),
           _f("2026-01-01", "2026-03-31", -0.74), _f("2026-01-01", "2026-09-30", 0.88),
           _f("2026-07-01", "2026-09-30", 0.62)]
    q = quarters(dow)
    q2 = [v for k, v in q.items() if k == (dt.date(2026, 4, 1), dt.date(2026, 6, 30))]
    check("a quarter missing inside a year is derived from 9M - Q1 - Q3 (DOW Q2 2026 = +1.00)",
          q2 and abs(q2[0]["val"] - 1.00) < 1e-9 and q2[0]["source"].startswith("derived"))
    t = ttm(dow)
    check("DOW's TTM through 09-30 builds (Q4'25 routine, Q2'26 derived: 1 unusual)",
          t["value"] is not None and t["derived"] == 2 and t["unusual"] == 1
          and str(t["end"]) == "2026-09-30")
    t6 = ttm(dow, as_of=dt.date(2026, 6, 30))
    check("TTM as of 06-30: 0.08 - 2.17 - 0.74 + 1.00 = -1.83 (Morningstar -1.82)",
          t6["value"] is not None and abs(t6["value"] - (-1.83)) < 1e-6)
    # 3. Q3 from 9M minus H1 when no quarter is tagged at all (rule B)
    cum = [_f("2026-01-01", "2026-06-30", 10.0), _f("2026-01-01", "2026-09-30", 16.0)]
    v, src = period_value(cum, dt.date(2026, 9, 30), "Q")
    check("Q3 = 9M - H1 when the filer tags only cumulative periods (rule B)",
          v is not None and abs(v - 6.0) < 1e-9 and "minus" in src)
    # 4. a real gap stays a gap
    gap = [_f("2025-01-01", "2025-03-31", 1.0), _f("2026-01-01", "2026-03-31", 1.4)]
    t = ttm(gap)
    check("a gap no fact can fill is reported, never guessed", t["value"] is None and "gap" in t["why"])
    two = {"facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": gap + [_f("2026-04-01", "2026-06-30", 1.5, filed="2026-08-02")]}},
        "ProfitLoss": {"units": {"USD": fy}}}}}
    b = best_ttm(two, metric("net_income"))
    check("a fallback tag builds the TTM when the freshest cannot, and says so (DOW NI)",
          b["value"] is not None and b["tag"] == "ProfitLoss" and "NetIncomeLoss cannot" in b["note"])
    # 5. freshest tag, exact unit
    cf = {"facts": {"us-gaap": {
        "StockholdersEquity": {"units": {"USD": [{"end": "2026-01-31", "val": 1.0}]}},
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest":
            {"units": {"USD": [{"end": "2026-07-31", "val": 2.0}]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [{"end": "2026-07-31", "val": 3.0}]}}}}}
    tag, _ = rows_for(cf, metric("equity"))
    check("the freshest equity tag wins (SNOW case)", tag.endswith("NoncontrollingInterest"))
    tag2, rows2 = rows_for(cf, ("EarningsPerShareDiluted",), "USD")
    check("a 'USD' metric never picks up a 'USD/shares' series", tag2 is None and rows2 == [])
    # 6. co-registrant recovery on the same accession only
    slim = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
                _f("2026-01-01", "2026-03-31", 5.0, accn="q1")]}}}},
            "periodic": [dict(form="10-Q", report="2026-03-31", accn="q1", filed="2026-04-24"),
                         dict(form="10-Q", report="2026-06-30", accn="q2", filed="2026-07-24")]}

    class FakeEC:
        @staticmethod
        def _facts_from_co_registrant(cik10, accn, report):
            if accn != "q2":
                return None, None
            return ({"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
                _f("2026-04-01", "2026-06-30", 7.0, accn="q2"),
                _f("2026-01-01", "2026-06-30", 12.0, accn="q2")]}}}}}, "0000029915")
    gaps = filing_gaps(slim, dt.date(2026, 10, 24))
    check("a periodic filing with no facts at its report date is a filing gap",
          [g["accn"] for g in gaps] == ["q2"])
    done = recover(slim, "0001751788", FakeEC, dt.date(2026, 10, 24))
    _tag, nrows = rows_for(slim, metric("net_income"))
    v, src = period_value(nrows, dt.date(2026, 6, 30), "Q")
    check("the missing quarter is recovered from the co-registrant, labelled, on its accession",
          done and done[0]["from_cik"] == "0000029915" and v == 7.0 and "recovered" in src
          and not filing_gaps(slim, dt.date(2026, 10, 24)))
    # 7. instants
    inst = [{"end": "2026-06-30", "val": 9.0, "filed": "2026-07-30"},
            {"end": "2026-09-30", "val": 10.0, "filed": "2026-10-30"}]
    check("latest instant and instant as of a date",
          latest_instant(inst) == (10.0, "2026-09-30")
          and latest_instant(inst, dt.date(2026, 7, 1)) == (9.0, "2026-06-30")
          and instant_at(inst, dt.date(2026, 6, 28)) == 9.0)
    # 9. DP-V4: point in time, 12-month ROE, the fundamentals panels
    ends = ["2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30",
            "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]

    def qs(vals):
        out, start = [], "2024-07-01"
        for e, v in zip(ends, vals):
            filed = (_d(e) + dt.timedelta(days=30)).isoformat()
            out.append(_f(start, e, v, filed=filed, accn="x" + e))
            start = (_d(e) + dt.timedelta(days=1)).isoformat()
        return out
    old, new = [1.0] * 4, [1.2] * 4
    fx = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": qs([100.0] * 4 + [110.0] * 4)}},
        "GrossProfit": {"units": {"USD": qs([40.0] * 4 + [55.0] * 4)}},
        "OperatingIncomeLoss": {"units": {"USD": [
            _f(s, e, 9.0, filed="2016-02-01") for s, e in (("2015-01-01", "2015-03-31"),
                ("2015-04-01", "2015-06-30"), ("2015-07-01", "2015-09-30"), ("2015-10-01", "2015-12-31"))]}},
        "NetIncomeLoss": {"units": {"USD": qs([10.0] * 4 + [12.0] * 4)}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": qs(old + new)}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": qs([9.0] * 4 + [15.0] * 4)}},
        "StockholdersEquity": {"units": {"USD": [
            {"end": "2026-03-31", "val": 190.0, "filed": "2026-04-30"},
            {"end": "2026-06-30", "val": 200.0, "filed": "2026-07-30"}]}},
        "Assets": {"units": {"USD": [{"end": "2026-06-30", "val": 500.0, "filed": "2026-07-30"}]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [
            {"end": "2026-06-30", "val": 30.0, "filed": "2026-07-30"}]}}}}}
    today = dt.date(2026, 10, 24)
    r = ttm_roe(fx, today)
    check("12-month ROE = TTM net income / period-end equity (48 / 200)",
          r["roe"] is not None and abs(r["roe"] - 0.24) < 1e-12 and r["why"] is None
          and r["equity_end"] == "2026-06-30")
    pit = point_in_time(fx, dt.date(2026, 7, 30))
    r2 = ttm_roe(pit, dt.date(2026, 7, 30))
    check("point in time: a 10-Q filed ON the cutoff is not yet public (strict); the TTM ends a quarter earlier",
          r2["ni_end"] == "2026-03-31" and abs(r2["roe"] - 46.0 / 190.0) < 1e-12)
    r3 = ttm_roe(point_in_time(fx, dt.date(2026, 7, 30), strict=False), dt.date(2026, 7, 30))
    check("point in time, same day allowed: the 10-Q filed that day counts", r3["ni_end"] == "2026-06-30")
    nodate = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        {"start": "2026-01-01", "end": "2026-03-31", "val": 1.0}]}}}}}
    check("NEGATIVE: a fact with no filing date is never assumed public",
          not point_in_time(nodate, today)["facts"]["us-gaap"])
    neg = json.loads(json.dumps(fx))
    neg["facts"]["us-gaap"]["StockholdersEquity"]["units"]["USD"][-1]["val"] = -5.0
    check("NEGATIVE: non-positive equity gives no ROE and says why",
          ttm_roe(neg, today)["roe"] is None and "non-positive" in ttm_roe(neg, today)["why"])
    check("NEGATIVE: an equity older than 400 days is not a book",
          ttm_roe(fx, dt.date(2027, 9, 1))["why"].startswith("equity last reported"))
    fu = fundamentals(fx, today)
    g, qy, b = fu["growth"], fu["quality"], fu["balance"]
    check("growth: 12-month EPS +20%, revenue +10% against the window a year earlier",
          abs(g["eps"]["chg"] - 0.20) < 1e-9 and abs(g["revenue"]["chg"] - 0.10) < 1e-9
          and abs(g["q_eps"]["chg"] - 0.20) < 1e-9)
    check("quality: cash conversion 60/48, gross margin 50% now against 40% a year earlier",
          abs(qy["ocf_to_ni"] - 1.25) < 1e-9 and abs(qy["gross_margin"] - 0.50) < 1e-9
          and abs(qy["gross_margin_year_ago"] - 0.40) < 1e-9)
    check("a tag that stopped years ago is not used, and the note says so (operating income 2015)",
          qy["op_margin"] is None and any("Operating income" in n and "not used" in n for n in fu["notes"]))
    check("balance: liabilities derived as assets minus equity, labelled; liabilities/equity 1.5",
          b["liabilities"] == 300.0 and "assets minus equity" in b["liabilities_source"]
          and abs(b["liab_to_equity"] - 1.5) < 1e-9 and b["cash"] == 30.0)
    # 2026-10-29: the three cases the 10-28 sheet left blank
    check("quality: OCF / revenue 60/440, liabilities / assets 300/500",
          abs(qy["ocf_margin"] - 60.0 / 440.0) < 1e-9 and qy["net_loss"] is False
          and abs(b["liab_to_assets"] - 0.6) < 1e-9)
    nq = json.loads(json.dumps(fx))
    nq["facts"]["us-gaap"]["StockholdersEquity"]["units"]["USD"][-1]["val"] = -50.0
    nb = fundamentals(nq, today)["balance"]
    check("negative equity (BBWI, PM): L/E not defined, liabilities / assets is (550/500)",
          nb["negative_equity"] and nb["liab_to_equity"] is None and abs(nb["liab_to_assets"] - 1.1) < 1e-9)
    lq = json.loads(json.dumps(fx))
    for row in lq["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]:
        row["val"] = -3.0
    lqq = fundamentals(lq, today)["quality"]
    check("a 12-month net loss (DOW): OCF/NI not defined, OCF / revenue still is, flagged",
          lqq["ocf_to_ni"] is None and lqq["net_loss"] is True and abs(lqq["ocf_margin"] - 60.0 / 440.0) < 1e-9)
    pq = json.loads(json.dumps(fx))
    del pq["facts"]["us-gaap"]["StockholdersEquity"]
    pb = fundamentals(pq, today)["balance"]
    check("no equity line (PAA): cash still read at the latest assets date; nothing derived from equity",
          pb["end"] == "2026-06-30" and pb["cash"] == 30.0 and pb["equity"] is None
          and pb["liabilities"] is None and pb["liab_to_assets"] is None and pb["liab_to_equity"] is None)
    check("NEGATIVE: an assets date older than 400 days opens no balance sheet",
          fundamentals(pq, dt.date(2027, 9, 1))["balance"].get("cash") is None)
    # 8. the map mirrors the prompt's (drift alarm)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import edgar_client as ec
        theirs = [(lab, kind, tuple(c)) for lab, kind, c in ec.FINANCIAL_CONCEPTS]
        ours = [(m[1], m[2], tuple(t for t in m[4] if t not in VALUE_LAYER_EXTRA))
                for m in METRICS]
        check("METRICS mirrors edgar_client.FINANCIAL_CONCEPTS (labels, kinds, tag order)",
              ours == theirs)
    except ImportError as e:
        print("  [SKIP] edgar_client not importable here (%s)" % e)
    print("  sec_facts selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    print(__doc__)
