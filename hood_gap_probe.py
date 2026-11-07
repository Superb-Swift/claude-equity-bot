#!/usr/bin/env python3
"""
hood_gap_probe.py - READ-ONLY. Tests, on live SEC data, whether the blank
cells of the value card's panel 2b ("under the hood") can be filled from SEC
filings, and how well each way of filling them reproduces a figure the
company DOES report.

WHY (2026-10-29)
    The 10-28 sheet left 2b blank wherever a company files the parts of a
    figure but not the figure itself: no GrossProfit tag (WMT and FTI never;
    GM, RTX, DOW and PAA stopped years ago), no OperatingIncomeLoss tag (NKE,
    DOW). sec_facts' slim cache keeps only the prompt's tags (METRICS), so the
    parts were never read. This probe fetches each filer's FULL companyfacts
    in memory, looks for the parts, derives the figure, and checks every
    derivation against the reported figure on each filer that reports both.

    Nothing is cached, nothing is written to valuation_cache\\ or edgar_cache\\,
    and nothing reaches the card, the prompt, a gate or the paste (DP-V1).

WHAT IT CANNOT SEE
    companyfacts carries the STANDARD taxonomies only (us-gaap, dei, srt...).
    A line a company files under its own extension tag (a company-specific
    "cost of sales") is not in it. Where the probe finds no standard part, the
    cell needs the filing's own XBRL instance, which is a different build.

PASS BARS (fixed here, before the probe has run)
    gross profit      derived = revenue - cost of revenue; PASS when the
                      12-month figure is within 0.5% of the reported one
    operating income  each route below; PASS within 2.0%, because companies
                      draw "operating" around different items
        A  revenue - total costs and expenses
        B  gross profit - operating expenses
        C  gross profit - SG&A - R&D (- amortization, - restructuring when filed)
        D  pre-tax income + interest expense (an EBIT proxy, never "operating")
    A route is only offered for a blank cell if it passed on the filers that
    report both, and the cell would carry the route's name.

OUTPUTS (public SEC data only; no account data)
    hood_gap_probe_<date>.md    the blank cells, the parts found, the checks
    hood_gap_probe_<date>.json  every candidate tag's rows and a tag inventory

USAGE
    python hood_gap_probe.py                    every name in the saved CIK map (funds skipped)
    python hood_gap_probe.py --tickers WMT,NKE
    python hood_gap_probe.py --selftest         offline, fixtures
    Exit: 0 ran; 2 could not run.

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

import sec_facts as SF

GP_TOL = 0.005
OI_TOL = 0.02

# (key, label, kind, unit, tags) - the shape of sec_facts.METRICS, so SF.best_ttm
# and SF.rows_for read them unchanged. Preference order inside each tuple.
FLOWS = (
    ("cost_of_revenue", "Cost of revenue", "flow", "USD",
     ("CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold",
      "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
      "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization", "CostOfServices")),
    ("costs_and_expenses", "Total costs and expenses", "flow", "USD",
     ("CostsAndExpenses", "OperatingCostsAndExpenses")),
    ("operating_expenses", "Operating expenses", "flow", "USD", ("OperatingExpenses",)),
    ("sga", "SG&A", "flow", "USD", ("SellingGeneralAndAdministrativeExpense",)),
    ("rnd", "R&D", "flow", "USD",
     ("ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost")),
    ("amortization", "Amortization of intangibles", "flow", "USD", ("AmortizationOfIntangibleAssets",)),
    ("restructuring", "Restructuring", "flow", "USD",
     ("RestructuringCharges", "RestructuringSettlementAndImpairmentProvisions")),
    ("pretax", "Pre-tax income", "flow", "USD",
     ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments")),
    ("interest_expense", "Interest expense", "flow", "USD",
     ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt")),
    ("lp_eps", "Net income per LP unit", "flow", "USD/shares",
     ("NetIncomeLossPerOutstandingLimitedPartnershipUnitDilutedNetOfTax",
      "NetIncomeLossPerOutstandingLimitedPartnershipUnitBasicAndDilutedNetOfTax",
      "NetIncomeLossPerOutstandingLimitedPartnershipUnitBasicNetOfTax",
      "IncomeLossFromContinuingOperationsPerOutstandingLimitedPartnershipUnitDilutedNetOfTax",
      "IncomeLossFromContinuingOperationsPerOutstandingLimitedPartnershipUnitBasicNetOfTax")),
    ("bank_revenue", "Total net revenue (bank)", "flow", "USD", ("RevenuesNetOfInterestExpense",)),
    ("net_interest_income", "Net interest income", "flow", "USD", ("InterestIncomeExpenseNet",)),
    ("noninterest_income", "Noninterest revenue", "flow", "USD", ("NoninterestIncome",)),
    ("noninterest_expense", "Noninterest expense", "flow", "USD", ("NoninterestExpense",)),
    ("provision", "Provision for credit losses", "flow", "USD",
     ("ProvisionForLoanLeaseAndOtherLosses", "ProvisionForCreditLossesExcludingUnfundedCommitments")),
)
INSTANTS = (
    ("lp_equity", "Partners' capital", "instant", "USD",
     ("PartnersCapital", "PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest")),
    ("cash_alt", "Cash (other tags)", "instant", "USD",
     ("CashAndDueFromBanks", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash")),
    ("deposits_in_banks", "Interest-bearing deposits in banks", "instant", "USD",
     ("InterestBearingDepositsInBanks",)),
    ("goodwill", "Goodwill", "instant", "USD", ("Goodwill",)),
    ("intangibles", "Intangibles ex goodwill", "instant", "USD", ("IntangibleAssetsNetExcludingGoodwill",)),
    ("deposits", "Deposits", "instant", "USD", ("Deposits",)),
)
# Tags kept with their rows for the analysis, beyond the lists above.
DISCOVER = re.compile(r"CostOf|GrossProfit|OperatingIncome|OperatingExpenses|CostsAndExpenses|"
                      r"SellingGeneral|ResearchAndDevelopment|PartnersCapital|LimitedPartnership|"
                      r"Revenue|Noninterest|InterestIncomeExpense|InterestExpense|CashAndDueFromBanks|"
                      r"InterestBearingDeposits|ProvisionFor|BeforeIncomeTaxes|Restructuring|"
                      r"AmortizationOfIntangible")
ROW_FIELDS = ("start", "end", "val", "fy", "fp", "form", "filed", "accn", "frame")
ROWS_SINCE_DAYS = 1200

# The sheet's 2b cells, in its column order.
CELLS = (("eps", "EPS 12m"), ("eps_chg", "EPS y/y"), ("rev_chg", "Revenue y/y"),
         ("q_eps_chg", "Last quarter EPS y/y"), ("ocf_ni", "OCF / NI"),
         ("gm", "Gross margin"), ("gm_ya", "Gross margin a year ago"),
         ("om", "Operating margin"), ("om_ya", "Operating margin a year ago"),
         ("le", "Liabilities / equity"), ("cash", "Cash"))


def _d(s):
    return dt.date.fromisoformat(str(s))


def _rel(a, b):
    if a is None or b is None or b == 0:
        return None
    return abs(a - b) / abs(b)


def _pct(x, nd=1):
    return "—" if x is None else ("%." + str(nd) + "f%%") % (100.0 * x)


def _bn(x):
    return "—" if x is None else "%.2fB" % (x / 1e9)


def is_bank(tk):
    try:
        import sector_map
        return sector_map.STOCK_SECTOR.get(tk) == "XLF"
    except Exception:                                   # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# One filer
# --------------------------------------------------------------------------- #
def flow(cf, m, end):
    """12-month figure for m on the window ending at `end` (+-7 days), and the
    window a year earlier on the SAME tag. dict(tag, value, end, aligned,
    year_ago, last) - value is None unless the window lines up."""
    t = SF.best_ttm(cf, m, as_of=end + dt.timedelta(days=7)) if end else SF.best_ttm(cf, m)
    tag = t.get("tag")
    last = None
    if tag:
        rows = (cf.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get(m[3]) or [])
        last = max((r.get("end", "") for r in rows), default="") or None
    out = dict(tag=tag, value=None, end=str(t["end"]) if t.get("end") else None,
               aligned=False, year_ago=None, last=last, why=t.get("why"))
    if t.get("value") is None or end is None or t.get("end") is None:
        return out
    if abs((t["end"] - end).days) > 7:
        out["why"] = "window ends %s, not %s" % (t["end"], end)
        return out
    out.update(value=t["value"], aligned=True)
    rows = cf["facts"]["us-gaap"][tag]["units"][m[3]]
    y = SF.ttm(rows, t["end"] - dt.timedelta(days=SF.YEAR_BACK_DAYS))
    if y["value"] is not None and 350 <= (t["end"] - y["end"]).days <= 380:
        out["year_ago"] = y["value"]
    return out


def flow_by_tag(cf, key, tag, unit, end):
    return flow(cf, (key, tag, "flow", unit, (tag,)), end)


def instant(cf, m, at):
    tag, rows = SF.rows_for(cf, m)
    if not tag or at is None:
        return dict(tag=tag, value=None)
    return dict(tag=tag, value=SF.instant_at(rows, at),
                last=max((r.get("end", "") for r in rows), default="") or None)


def _sub(a, *bs):
    if a is None or any(b is None for b in bs):
        return None
    return a - sum(bs)


def _add(a, b):
    return None if a is None or b is None else a + b


def probe_one(tk, cf_full, today, bank=False):
    """Everything the probe knows about one filer, as a dict."""
    gaap = (cf_full or {}).get("facts", {}).get("us-gaap", {})
    res = dict(ticker=tk, entity=(cf_full or {}).get("entityName"),
               taxonomies=sorted((cf_full or {}).get("facts", {}).keys()), bank=bank)
    if not gaap:
        res["scope"] = ("IFRS filer: no us-gaap facts" if "ifrs-full" in res["taxonomies"]
                        else "no us-gaap facts")
        return res
    cf = SF.point_in_time({"facts": {"us-gaap": gaap}}, today, strict=False)
    fu = SF.fundamentals(cf, today)
    res["card_notes"] = list(fu.get("notes") or [])
    if fu.get("end") is None:
        res["scope"] = "no 12-month figures"
        return res
    end = _d(fu["end"])
    res["end"] = fu["end"]
    g, q, b = fu["growth"], fu["quality"], fu["balance"]
    now = dict(eps=g["eps"]["ttm"], eps_chg=g["eps"]["chg"], rev_chg=g["revenue"]["chg"],
               q_eps_chg=g["q_eps"]["chg"], ocf_ni=q.get("ocf_to_ni"),
               gm=q.get("gross_margin"), gm_ya=q.get("gross_margin_year_ago"),
               om=q.get("op_margin"), om_ya=q.get("op_margin_year_ago"),
               le=b.get("liab_to_equity"), cash=b.get("cash"))
    res["card_now"] = now
    res["blank"] = [k for k, _lab in CELLS if now.get(k) is None]

    rev = flow(cf, SF.metric("revenue"), end)
    ni = flow(cf, SF.metric("net_income"), end)
    ocf = flow(cf, SF.metric("ocf"), end)
    gp_rep = flow(cf, SF.metric("gross_profit"), end)
    oi_rep = flow(cf, SF.metric("operating_income"), end)
    parts = {m[0]: flow(cf, m, end) for m in FLOWS}
    res["parts"] = {k: {kk: v[kk] for kk in ("tag", "aligned", "end", "last", "value", "year_ago")}
                    for k, v in parts.items() if v["tag"]}
    res["reported"] = dict(revenue=rev, gross_profit=gp_rep, operating_income=oi_rep,
                           net_income=ni, ocf=ocf)

    # Gross profit: revenue - cost of revenue, every cost tag the filer has
    gp_routes = []
    for tag in FLOWS[0][4]:
        if tag not in gaap:
            continue
        c = flow_by_tag(cf, "cost", tag, "USD", end)
        gp = _sub(rev["value"], c["value"]) if c["aligned"] and rev["aligned"] else None
        gp_ya = _sub(rev["year_ago"], c["year_ago"]) if gp is not None else None
        gp_routes.append(dict(route="revenue - %s" % tag, tag=tag, aligned=c["aligned"],
                              last=c["last"], why=c["why"], value=gp, year_ago=gp_ya,
                              margin=SF._div(gp, rev["value"]),
                              margin_ya=SF._div(gp_ya, rev["year_ago"]),
                              vs_reported=_rel(gp, gp_rep["value"]) if gp_rep["aligned"] else None))
    res["gp_routes"] = gp_routes
    gp_best = gp_rep["value"] if gp_rep["aligned"] else next(
        (r["value"] for r in gp_routes if r["value"] is not None), None)
    gp_best_ya = gp_rep["year_ago"] if gp_rep["aligned"] else next(
        (r["year_ago"] for r in gp_routes if r["value"] is not None), None)

    # Operating income: four routes
    P = {k: (v["value"] if v["aligned"] else None) for k, v in parts.items()}
    Py = {k: (v["year_ago"] if v["aligned"] else None) for k, v in parts.items()}
    oi_routes = []

    def route(name, v, vya, used):
        oi_routes.append(dict(route=name, value=v, year_ago=vya, used=used,
                              margin=SF._div(v, rev["value"]), margin_ya=SF._div(vya, rev["year_ago"]),
                              vs_reported=_rel(v, oi_rep["value"]) if oi_rep["aligned"] else None))
    if P["costs_and_expenses"] is not None and rev["aligned"]:
        route("A revenue - total costs and expenses", _sub(rev["value"], P["costs_and_expenses"]),
              _sub(rev["year_ago"], Py["costs_and_expenses"]), [parts["costs_and_expenses"]["tag"]])
    if P["operating_expenses"] is not None and gp_best is not None:
        route("B gross profit - operating expenses", _sub(gp_best, P["operating_expenses"]),
              _sub(gp_best_ya, Py["operating_expenses"]), [parts["operating_expenses"]["tag"]])
    if P["sga"] is not None and gp_best is not None:
        extra = [k for k in ("rnd", "amortization", "restructuring") if P[k] is not None]
        v = _sub(gp_best, P["sga"], *[P[k] for k in extra])
        vya = _sub(gp_best_ya, Py["sga"], *[Py[k] for k in extra])
        route("C gross profit - SG&A" + "".join(" - " + k for k in extra), v, vya,
              [parts[k]["tag"] for k in ["sga"] + extra])
    if P["pretax"] is not None and P["interest_expense"] is not None:
        route("D pre-tax income + interest expense (EBIT proxy)",
              _add(P["pretax"], P["interest_expense"]), _add(Py["pretax"], Py["interest_expense"]),
              [parts["pretax"]["tag"], parts["interest_expense"]["tag"]])
    res["oi_routes"] = oi_routes

    # Partnership units: per-unit earnings and partners' capital
    lp = None
    for tag in FLOWS[9][4]:
        units = (gaap.get(tag) or {}).get("units") or {}
        for u in units:
            if u.startswith("USD/"):
                f = flow_by_tag(cf, "lp_eps", tag, u, end)
                if f["aligned"]:
                    qq = SF.quarters(units[u])
                    qn = [v["val"] for kk, v in qq.items() if abs((kk[1] - end).days) <= 7]
                    qp = [v["val"] for kk, v in qq.items()
                          if abs((kk[1] - (end - dt.timedelta(days=364))).days) <= 10]
                    lp = dict(tag=tag, unit=u, value=f["value"], year_ago=f["year_ago"],
                              q_chg=SF._chg(qn[0] if qn else None, qp[0] if qp else None))
                    break
        if lp:
            break
    res["lp_eps"] = lp

    # Balance sheet at the latest assets date (the card reads it only when equity exists)
    a_tag, a_rows = SF.rows_for(cf, SF.metric("assets"))
    assets, a_end = SF.latest_instant(a_rows) if a_rows else (None, None)
    at = _d(a_end) if a_end else None
    bal = dict(assets_end=a_end, assets=assets)
    _lt, l_rows = SF.rows_for(cf, SF.metric("liabilities"))
    bal["liabilities"] = SF.instant_at(l_rows, at) if (l_rows and at) else None
    _et, e_rows = SF.rows_for(cf, SF.metric("equity"))
    bal["equity"] = SF.instant_at(e_rows, at) if (e_rows and at) else None
    _ct, c_rows = SF.rows_for(cf, SF.metric("cash"))
    bal["cash"] = SF.instant_at(c_rows, at) if (c_rows and at) else None
    for m in INSTANTS:
        bal[m[0]] = instant(cf, m, at)
    eq_any = bal["equity"] if bal["equity"] is not None else bal["lp_equity"]["value"]
    liab = bal["liabilities"]
    if liab is None and assets is not None and eq_any is not None:
        liab = assets - eq_any
    bal["liab_any"] = liab
    bal["liab_to_assets"] = SF._div(liab, assets)
    bal["liab_to_equity_any"] = SF._div(liab, eq_any) if (eq_any is not None and eq_any > 0) else None
    bal["negative_equity"] = eq_any is not None and eq_any <= 0
    res["balance"] = bal
    res["ocf_margin"] = SF._div(ocf["value"], rev["value"]) if (ocf["aligned"] and rev["aligned"]) else None
    res["net_loss"] = ni["aligned"] and ni["value"] is not None and ni["value"] <= 0
    if bank:
        bk = {k: (parts[k]["value"] if parts.get(k, {}).get("aligned") else None)
              for k in ("bank_revenue", "net_interest_income", "noninterest_income",
                        "noninterest_expense", "provision")}
        bk["efficiency_ratio"] = SF._div(bk["noninterest_expense"], bk["bank_revenue"])
        bk["bank_revenue_chg"] = SF._chg(bk["bank_revenue"], parts.get("bank_revenue", {}).get("year_ago")) \
            if bk["bank_revenue"] is not None else None
        res["bank_view"] = bk
    return res


def verdicts(res, gp_pass, oi_pass):
    """For each blank cell: (cell, verdict, how). gp_pass / oi_pass map a route
    name to (passes, checked) across the filers that report both."""
    out = []
    blank = set(res.get("blank") or [])
    bal = res.get("balance") or {}
    for k, lab in CELLS:
        if k not in blank:
            continue
        if res.get("bank") and k in ("ocf_ni", "le", "gm", "gm_ya", "om", "om_ya"):
            out.append((lab, "BANK", "not comparable for a bank; see the bank view"))
            continue
        if k in ("gm", "gm_ya"):
            r = next((r for r in res.get("gp_routes") or []
                      if (r["margin"] if k == "gm" else r["margin_ya"]) is not None), None)
            if r:
                p, n = gp_pass.get(r["tag"], (0, 0))
                ok = n and p == n
                out.append((lab, "FILLABLE" if ok else "FILLABLE, UNPROVEN",
                            "%s = %s (route passed on %d of %d filers that report both)"
                            % (r["route"], _pct(r["margin"] if k == "gm" else r["margin_ya"]), p, n)))
            else:
                why = "; ".join("%s: %s" % (r["tag"], r["why"]) for r in res.get("gp_routes") or [])
                out.append((lab, "NOT IN STANDARD TAGS",
                            why or "no standard cost-of-revenue tag (a company extension, or no such line)"))
            continue
        if k in ("om", "om_ya"):
            best = None
            for r in res.get("oi_routes") or []:
                mv = r["margin"] if k == "om" else r["margin_ya"]
                if mv is None:
                    continue
                p, n = oi_pass.get(r["route"][0], (0, 0))
                score = (1 if (n and p == n) else 0, p, -ord(r["route"][0]))
                if best is None or score > best[0]:
                    best = (score, r, mv, p, n)
            if best:
                _s, r, mv, p, n = best
                ok = n and p == n and not r["route"].startswith("D")
                out.append((lab, "FILLABLE" if ok else "FILLABLE, UNPROVEN",
                            "%s = %s (route passed on %d of %d filers that report both)"
                            % (r["route"], _pct(mv), p, n)))
            else:
                out.append((lab, "NOT IN STANDARD TAGS", "no route has all its parts on the window"))
            continue
        if k == "le":
            if bal.get("negative_equity"):
                out.append((lab, "UNDEFINED", "equity is negative (a deficit): liabilities / assets = %s"
                            % _pct(bal.get("liab_to_assets"), 0)))
            elif bal.get("liab_to_equity_any") is not None:
                out.append((lab, "FILLABLE", "equity from %s: %.2f"
                            % ((bal.get("lp_equity") or {}).get("tag") or "the equity tag",
                               bal["liab_to_equity_any"])))
            else:
                out.append((lab, "NOT IN STANDARD TAGS", "no equity tag on the balance date"))
            continue
        if k == "ocf_ni":
            if res.get("net_loss"):
                out.append((lab, "UNDEFINED", "net loss over 12 months: OCF / revenue = %s"
                            % _pct(res.get("ocf_margin"))))
            else:
                out.append((lab, "NOT IN STANDARD TAGS", "operating cash flow or net income missing"))
            continue
        if k == "cash":
            alt = bal.get("cash")
            alt_i = bal.get("cash_alt") or {}
            if alt is not None:
                out.append((lab, "FILLABLE", "the card skips its balance sheet without equity; "
                            "cash on %s = %s" % (bal.get("assets_end"), _bn(alt))))
            elif alt_i.get("value") is not None:
                out.append((lab, "FILLABLE", "%s = %s" % (alt_i["tag"], _bn(alt_i["value"]))))
            else:
                out.append((lab, "NOT IN STANDARD TAGS", "no cash tag on the balance date"))
            continue
        if k in ("eps", "eps_chg", "q_eps_chg"):
            lp = res.get("lp_eps")
            if lp:
                v = (lp["value"] if k == "eps" else SF._chg(lp["value"], lp["year_ago"])
                     if k == "eps_chg" else lp.get("q_chg"))
                out.append((lab, "FILLABLE", "%s = %s" % (lp["tag"], ("%.2f" % v) if k == "eps" and v is not None
                                                          else _pct(v))))
            else:
                out.append((lab, "NOT IN STANDARD TAGS", "no per-share or per-unit earnings tag"))
            continue
        if k == "rev_chg":
            bv = res.get("bank_view") or {}
            if bv.get("bank_revenue_chg") is not None:
                out.append((lab, "FILLABLE", "RevenuesNetOfInterestExpense (a bank's total net "
                            "revenue) = %s" % _pct(bv["bank_revenue_chg"])))
            else:
                out.append((lab, "NOT IN STANDARD TAGS", "no revenue tag on the window"))
            continue
        out.append((lab, "OPEN", "not probed"))
    return out


def pass_tables(results):
    """Route pass counts across filers that report the figure."""
    gp, oi = {}, {}
    for r in results:
        for g in r.get("gp_routes") or []:
            if g.get("vs_reported") is not None:
                p, n = gp.get(g["tag"], (0, 0))
                gp[g["tag"]] = (p + (1 if g["vs_reported"] <= GP_TOL else 0), n + 1)
        for o in r.get("oi_routes") or []:
            if o.get("vs_reported") is not None:
                p, n = oi.get(o["route"][0], (0, 0))
                oi[o["route"][0]] = (p + (1 if o["vs_reported"] <= OI_TOL else 0), n + 1)
    return gp, oi


# --------------------------------------------------------------------------- #
# Saving the rows
# --------------------------------------------------------------------------- #
def keep_rows(gaap, today):
    """The candidate tags' rows (periodic forms, about three years) and an
    inventory of every us-gaap tag: {tag: [last end, number of facts]}."""
    since = (today - dt.timedelta(days=ROWS_SINCE_DAYS)).isoformat()
    wanted = set(SF.slim_tags())
    for m in FLOWS + INSTANTS:
        wanted.update(m[4])
    rows, inv = {}, {}
    for tag, node in gaap.items():
        units = node.get("units") or {}
        allr = [r for u in units.values() for r in u]
        inv[tag] = [max((r.get("end", "") for r in allr), default=""), len(allr)]
        if tag in wanted or DISCOVER.search(tag):
            keep = {}
            for u, rr in units.items():
                k = [{f: r[f] for f in ROW_FIELDS if f in r} for r in rr
                     if r.get("form") in SF.PERIODIC_FORMS and r.get("end", "") >= since]
                if k:
                    keep[u] = k
            if keep:
                rows[tag] = {"units": keep}
    return rows, inv


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def report(results, gp_pass, oi_pass, today):
    L = ["# Under-the-hood gap probe, %s" % today.isoformat(), "",
         "READ-ONLY. Full SEC companyfacts, read in memory; nothing cached, nothing reaches",
         "the card, the prompt or a gate (DP-V1). Pass bars fixed before the run: gross",
         "profit within %.1f%%, operating income within %.1f%% of the reported figure."
         % (100 * GP_TOL, 100 * OI_TOL), "",
         "## 1. The blank cells and what the filings hold", "",
         "| Ticker | Cell | Verdict | How |", "|---|---|---|---|"]
    for r in results:
        if r.get("scope"):
            L.append("| %s | all | OUT OF SCOPE | %s |" % (r["ticker"], r["scope"]))
            continue
        vs = verdicts(r, gp_pass, oi_pass)
        if not vs:
            L.append("| %s | — | NO BLANKS | |" % r["ticker"])
        for cell, v, how in vs:
            L.append("| %s | %s | %s | %s |" % (r["ticker"], cell, v, how.replace("|", "/")))
    L += ["", "## 2. The checks: derived against reported, where a filer reports both", "",
          "| Ticker | Figure | Route | Derived | Reported | Off by | Pass |", "|---|---|---|---|---|---|---|"]
    for r in results:
        rep = r.get("reported") or {}
        for g in r.get("gp_routes") or []:
            if g.get("vs_reported") is not None:
                L.append("| %s | gross profit | %s | %s | %s | %s | %s |" % (
                    r["ticker"], g["route"], _bn(g["value"]), _bn(rep["gross_profit"]["value"]),
                    _pct(g["vs_reported"], 2), "PASS" if g["vs_reported"] <= GP_TOL else "FAIL"))
        for o in r.get("oi_routes") or []:
            if o.get("vs_reported") is not None:
                L.append("| %s | operating income | %s | %s | %s | %s | %s |" % (
                    r["ticker"], o["route"], _bn(o["value"]), _bn(rep["operating_income"]["value"]),
                    _pct(o["vs_reported"], 2), "PASS" if o["vs_reported"] <= OI_TOL else "FAIL"))
    L += ["", "Route totals: gross profit " + (", ".join("%s %d/%d" % (t, p, n) for t, (p, n)
                                                       in sorted(gp_pass.items())) or "none checked")
          + "; operating income " + (", ".join("%s %d/%d" % (t, p, n) for t, (p, n)
                                               in sorted(oi_pass.items())) or "none checked") + ".", ""]
    banks = [r for r in results if r.get("bank_view")]
    if banks:
        L += ["## 3. Bank view (what a bank reports instead)", "",
              "| Ticker | Total net revenue | y/y | Net interest income | Noninterest revenue | "
              "Noninterest expense | Efficiency ratio | Provision |", "|---|---|---|---|---|---|---|---|"]
        for r in banks:
            b = r["bank_view"]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r["ticker"], _bn(b["bank_revenue"]), _pct(b["bank_revenue_chg"]),
                _bn(b["net_interest_income"]), _bn(b["noninterest_income"]),
                _bn(b["noninterest_expense"]), _pct(b["efficiency_ratio"]), _bn(b["provision"])))
        L.append("")
    L += ["## 4. Parts found per filer (tag, last period end, on the window?)", ""]
    for r in results:
        if r.get("scope"):
            continue
        ps = ", ".join("%s %s (%s%s)" % (k, v["tag"], v["last"], "" if v["aligned"] else ", OFF WINDOW")
                       for k, v in sorted((r.get("parts") or {}).items()))
        L.append("- **%s** (window ends %s): %s" % (r["ticker"], r.get("end"), ps or "none"))
    L += ["", "Advisory-only - no orders - not financial advice.", ""]
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
def run(a, ec=None):
    today = _d(a.date) if a.date else dt.date.today()
    cik_map = SF.load_saved_cik_map(".")
    names = [t.strip().upper() for t in a.tickers.split(",")] if a.tickers else sorted(cik_map)
    funds = set()
    if os.path.exists(a.quotes):
        try:
            with open(a.quotes, encoding="utf-8") as fh:
                funds = {t for t, q in json.load(fh).get("quotes", {}).items() if q.get("is_etf")}
        except (OSError, ValueError):
            pass
    if ec is None:
        import edgar_client as ec
    SF.standalone_budget(ec)
    results, saved = [], {}
    for tk in names:
        if tk in funds:
            results.append(dict(ticker=tk, scope="fund: no company statements"))
            continue
        cik = cik_map.get(tk)
        if not cik:
            results.append(dict(ticker=tk, scope="no CIK in the saved map"))
            continue
        cf = ec._http_get(ec.XBRL_FACTS_URL.format(cik10=cik), as_json=True)
        if not cf:
            results.append(dict(ticker=tk, scope="companyfacts fetch failed (%s)"
                                % ((getattr(ec, "_last_fetch", {}) or {}).get("reason") or "?")))
            continue
        r = probe_one(tk, cf, today, bank=is_bank(tk))
        results.append(r)
        rows, inv = keep_rows(cf.get("facts", {}).get("us-gaap", {}), today)
        saved[tk] = dict(cik=cik, entity=cf.get("entityName"), taxonomies=r.get("taxonomies"),
                         inventory=inv, facts={"us-gaap": rows})
        print("  %-5s %s" % (tk, r.get("scope") or ("blank: " + (", ".join(r.get("blank") or []) or "none"))))
    gp_pass, oi_pass = pass_tables(results)
    stem = a.out or "hood_gap_probe_%s" % today.isoformat()
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(report(results, gp_pass, oi_pass, today))
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(dict(date=today.isoformat(), gp_tol=GP_TOL, oi_tol=OI_TOL, results=results,
                       filers=saved), fh, default=str)
    print("  wrote %s.md and %s.json" % (stem, stem))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only probe of the value card's 2b gaps.")
    ap.add_argument("--tickers", default=None)
    ap.add_argument("--quotes", default="quote_dump.json")
    ap.add_argument("--date", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    SF.console_safe()
    if a.selftest:
        return selftest()
    try:
        return run(a)
    except Exception as e:                              # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("HOOD GAP PROBE COULD NOT RUN: %s: %s" % (type(e).__name__, e))
        return 2


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

    ends = ["2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30",
            "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]

    def qs(vals, unit="USD", shift=0):
        out, start = [], "2024-07-01"
        for e, v in zip(ends[:len(ends) - shift], vals):
            filed = (_d(e) + dt.timedelta(days=30)).isoformat()
            out.append({"start": start, "end": e, "val": v, "filed": filed,
                        "accn": "x" + e, "form": "10-Q"})
            start = (_d(e) + dt.timedelta(days=1)).isoformat()
        return {"units": {unit: out}}

    def bal(v, e="2026-06-30"):
        return {"units": {"USD": [{"end": e, "val": v, "filed": "2026-07-30", "accn": "b", "form": "10-Q"}]}}

    rev = qs([100.0] * 4 + [110.0] * 4)
    eps = qs([1.0] * 4 + [1.2] * 4, "USD/shares")
    ni = qs([10.0] * 4 + [12.0] * 4)
    base = {"Revenues": rev, "NetIncomeLoss": ni, "NetCashProvidedByUsedInOperatingActivities": qs([12.0] * 8),
            "EarningsPerShareDiluted": eps, "Assets": bal(500.0), "StockholdersEquity": bal(200.0),
            "CashAndCashEquivalentsAtCarryingValue": bal(30.0)}
    # A reports gross profit AND its cost: the route is checked
    fa = dict(base, CostOfRevenue=qs([60.0] * 4 + [55.0] * 4), GrossProfit=qs([40.0] * 4 + [55.0] * 4),
              OperatingIncomeLoss=qs([20.0] * 4 + [30.0] * 4), OperatingExpenses=qs([20.0] * 4 + [25.0] * 4),
              SellingGeneralAndAdministrativeExpense=qs([15.0] * 4 + [20.0] * 4),
              ResearchAndDevelopmentExpense=qs([5.0] * 4 + [5.0] * 4))
    # W files the cost but not the gross profit (WMT's shape); no operating-income tag (NKE's)
    fw = dict(base, CostOfRevenue=qs([75.0] * 4 + [82.5] * 4),
              SellingGeneralAndAdministrativeExpense=qs([15.0] * 4 + [17.0] * 4))
    # S: the cost tag's window ends a quarter early - never mixed into the margin
    fs = dict(base, CostOfGoodsAndServicesSold=qs([60.0] * 7, shift=1))
    # P: a partnership - per-unit earnings, partners' capital, no StockholdersEquity
    fp = {k: v for k, v in base.items() if k not in ("EarningsPerShareDiluted", "StockholdersEquity")}
    fp.update(NetIncomeLossPerOutstandingLimitedPartnershipUnitDilutedNetOfTax=qs([0.5] * 4 + [0.6] * 4,
                                                                                   "USD/shares"),
              PartnersCapital=bal(250.0), Liabilities=bal(250.0))
    # N: negative equity; L: a net loss
    fn = dict(base, StockholdersEquity=bal(-50.0), Liabilities=bal(550.0))
    fl = dict(base, NetIncomeLoss=qs([-5.0] * 8))
    fixtures = {"A": fa, "W": fw, "S": fs, "P": fp, "N": fn, "L": fl}
    cik = {t: "%010d" % (i + 1) for i, t in enumerate(fixtures)}
    by_cik = {cik[t]: {"entityName": t, "facts": {"us-gaap": f, "dei": {}}} for t, f in fixtures.items()}

    class FakeEC:
        XBRL_FACTS_URL = "https://x/CIK{cik10}.json"
        _last_fetch = {"reason": None}
        EDGAR_MAX_SECONDS = 120

        @staticmethod
        def _http_get(url, as_json=False):
            return by_cik.get(url.split("CIK")[1].split(".")[0])

    tmp = tempfile.mkdtemp()
    cwd = os.getcwd()
    try:
        os.chdir(tmp)
        os.makedirs(SF.CACHE_DIR)
        with open(SF.cik_map_path("."), "w") as fh:
            json.dump(cik, fh)
        a = argparse.Namespace(tickers=None, quotes="none.json", date="2026-08-15", out="probe")
        rc = run(a, ec=FakeEC)
        with open("probe.json", encoding="utf-8") as fh:
            out = json.load(fh)
        with open("probe.md", encoding="utf-8") as fh:
            md = fh.read()
        R = {r["ticker"]: r for r in out["results"]}
        check("ran and wrote both files", rc == 0 and "## 2. The checks" in md)
        g = R["A"]["gp_routes"][0]
        check("A: revenue - cost reproduces the reported gross profit exactly (the route's check)",
              g["vs_reported"] is not None and g["vs_reported"] < 1e-9)
        w = next(r for r in R["W"]["gp_routes"] if r["tag"] == "CostOfRevenue")
        check("W: gross margin 25% now and a year ago, derived from the cost tag",
              abs(w["margin"] - 0.25) < 1e-9 and abs(w["margin_ya"] - 0.25) < 1e-9)
        vw = dict((c, (v, h)) for c, v, h in verdicts(R["W"], *pass_tables(list(R.values()))))
        check("W: the verdict names the route and how often it passed",
              vw["Gross margin"][0] == "FILLABLE" and "1 of 1" in vw["Gross margin"][1])
        check("W: operating margin by route C (gross profit - SG&A) = 9.5%, the route checked on A",
              vw["Operating margin"][0] == "FILLABLE" and "C gross profit - SG&A" in vw["Operating margin"][1]
              and "9.5%" in vw["Operating margin"][1])
        s = R["S"]["gp_routes"][0]
        check("S: a cost window a quarter early is not used (no margin, says why)",
              s["margin"] is None and not s["aligned"] and "window ends" in (s["why"] or ""))
        vp = dict((c, (v, h)) for c, v, h in verdicts(R["P"], {}, {}))
        check("P: partnership per-unit earnings and partners' capital fill EPS and L/E",
              vp["EPS 12m"][0] == "FILLABLE" and "2.40" in vp["EPS 12m"][1]
              and vp["Liabilities / equity"][0] == "FILLABLE" and "1.00" in vp["Liabilities / equity"][1]
              and vp["Last quarter EPS y/y"] == ("FILLABLE",
                  "NetIncomeLossPerOutstandingLimitedPartnershipUnitDilutedNetOfTax = 20.0%"))
        check("P: cash is read without shareholders' equity", vp["Cash"][0] == "FILLABLE")
        vn = dict((c, (v, h)) for c, v, h in verdicts(R["N"], {}, {}))
        check("N: negative equity is UNDEFINED and shows liabilities / assets instead",
              vn["Liabilities / equity"][0] == "UNDEFINED" and "110%" in vn["Liabilities / equity"][1])
        vl = dict((c, (v, h)) for c, v, h in verdicts(R["L"], {}, {}))
        check("L: a net loss makes OCF/NI UNDEFINED and shows OCF / revenue",
              vl["OCF / NI"][0] == "UNDEFINED" and "10.9%" in vl["OCF / NI"][1])
        fb = {k: v for k, v in base.items() if k not in ("Revenues", "CashAndCashEquivalentsAtCarryingValue")}
        fb.update(RevenuesNetOfInterestExpense=qs([100.0] * 4 + [110.0] * 4),
                  NoninterestExpense=qs([55.0] * 8), CashAndDueFromBanks=bal(20.0))
        rb = probe_one("B", {"facts": {"us-gaap": fb}}, dt.date(2026, 8, 15), bank=True)
        vb = dict((c, (v, h)) for c, v, h in verdicts(rb, {}, {}))
        check("B: a bank's revenue y/y from total net revenue (+10%), efficiency ratio 50%, "
              "cash and due from banks; margins marked BANK",
              vb["Revenue y/y"][0] == "FILLABLE" and "10.0%" in vb["Revenue y/y"][1]
              and abs(rb["bank_view"]["efficiency_ratio"] - 0.5) < 1e-9
              and vb["Cash"][0] == "FILLABLE" and vb["Gross margin"][0] == "BANK")
        check("the saved rows keep the candidate tags, and the inventory every tag",
              "CostOfRevenue" in out["filers"]["W"]["facts"]["us-gaap"]
              and "Revenues" in out["filers"]["W"]["inventory"])
        check("nothing was written to the slim cache",
              sorted(os.listdir(SF.CACHE_DIR)) == ["cik_map.json"])
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)
    print("  hood_gap_probe selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
