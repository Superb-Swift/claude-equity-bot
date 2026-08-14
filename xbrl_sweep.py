#!/usr/bin/env python3
# =============================================================================
# xbrl_sweep.py  --  CROSS-TICKER AUDIT OF THE XBRL FINANCIAL EXTRACT
# =============================================================================
# WHAT THIS IS:
#   A coherence and corroboration sweep over the EDGAR-covered watchlist. It
#   renders each covered ticker's financial extract and asks, per ticker,
#   whether the block is internally coherent and whether it AGREES WITH THE
#   FILER'S OWN 8-K where one is available.
#
# WHY IT EXISTS (2026-08-10/11, the N-1 closeout):
#   RTX rendered six-month revenue ($46.8B) under a "Q2 FY2026" header with no
#   label for an unknown number of sessions. Every number in the block was
#   REAL and the block looked entirely plausible; nothing about it read as
#   wrong unless you checked it against RTX's own earnings release. Two green
#   harnesses (edgar_client --selftest, edgar_parser_audit) both passed
#   throughout, because both tested the code's internals rather than the
#   rendered output against external truth.
#
#   That is the failure this sweep exists to catch, and the reason it checks
#   ACROSS tickers rather than one at a time: the defect was never visible in
#   isolation, only in the disagreement between the extract and the 8-K.
#
# WHAT IT CANNOT DO:
#   It cannot establish that a figure is TRUE. It can establish that a block
#   is internally incoherent (which proves something is wrong), or that it
#   disagrees with the filer's own press release (which proves the same), or
#   that it sits in the specific defect class that produced the RTX error.
#   A clean sweep is evidence of coherence, NOT a certificate of accuracy.
#   The eyeball queue at the end is not optional garnish -- it is the part of
#   the check that machines cannot do.
#
# USAGE (project root, venv active):
#     python xbrl_sweep.py                     # the 15 covered names
#     python xbrl_sweep.py --tickers RTX,GM,PM
#     python xbrl_sweep.py --from-log          # watchlist from latest log
#     python xbrl_sweep.py --md sweep.md       # write a markdown exhibit
#     python xbrl_sweep.py --selftest          # offline; no network
#
# EXIT CODES:  0 = no HARD finding (FLAGs may still be present and listed)
#              1 = at least one HARD finding -- an extract is incoherent
#              2 = could not run (no CIK map / no SEC_USER_AGENT / import)
#
# CONSOLE ENCODING: ASCII-only output on purpose. cmd/PowerShell under cp1252
#   raises UnicodeEncodeError on em-dashes and arrows, which looks like a crash.
#
# Advisory-only . no orders . not financial advice.
# =============================================================================

import argparse
import re
import sys
from datetime import datetime

try:
    import edgar_client as ec
except ImportError as e:                                  # pragma: no cover
    print("HARNESS ERROR: cannot import edgar_client ({}).".format(e))
    print("Run from the project root with the venv active.")
    sys.exit(2)

# T-A + T-B from Phase3C_E4_Endpoint_PreRegistration_v1.md section 1. CBRS is
# excluded by DP-3; the T-C dark names have no financials to audit.
COVERED_DEFAULT = ["AAPL", "CORN", "DOW", "FTI", "GLD", "GM", "JPM", "MSFT",
                   "NKE", "NVDA", "PM", "PWR", "RTX", "SND", "WMT"]

# Balance-sheet identity tolerance. Assets = Liabilities + Equity is
# definitional, but the extract prefers StockholdersEquity (which EXCLUDES
# noncontrolling interests) over the including-NCI concept, so a filer with
# material NCI shows a real, benign gap -- RTX runs about 1.0% on ~$1.7B of
# NCI against $174B of assets. 5% is set well above that and well below the
# ~25%+ a mixed-period or wrong-concept error would produce.
BALANCE_TOL = 0.05

# Implied share count = net income / diluted EPS. Backing the prior year out
# of the two YoY figures gives a second, independent share count; the two
# should differ only by real buybacks or issuance. Sustained buybacks run
# under ~10%/yr, so a 25% drift is not a capital action -- it is the two
# lines describing different periods.
SHARE_DRIFT_TOL = 0.25

# 8-K press-release cross-check tolerance. Filers round to one decimal
# ("$24.7 billion"), so the extract can differ from the stated figure by up
# to half a rounding step; 2% covers that with margin at any scale.
EIGHTK_TOL = 0.02

_REV_RE = re.compile(
    r"(?P<label>total revenues|total revenue|net sales|revenues|revenue|sales)"
    r"(?P<gap>[^.$]{0,70}?)"
    r"\$\s*(?P<num>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>billion|million|trillion|bn\b|mm\b)?",
    re.I)

_SCALE = {"trillion": 1e12, "billion": 1e9, "bn": 1e9,
          "million": 1e6, "mm": 1e6}

# Concept pairs where the SMALLER concept is the DELIBERATE and correct
# choice, so the preference order stepping past the larger one is by design.
#
# ANALYST NOTE (2026-08-11): the first live run of the scope check produced 15
# findings, of which 14 were these four pairs and exactly ONE (GM's Revenues)
# was real. A check that is wrong 14 times out of 15 does not get read, and an
# unread check is worse than no check because it looks like coverage. The
# pairs are enumerated rather than suppressed by threshold: the DIFFERENCE is
# still reported, because the noncontrolling-interest amount cross-validates
# the balance-sheet residual and the current-portion amount is real
# information. What changes is the severity, not the visibility.
_BY_DESIGN = {
    ("LongTermDebtNoncurrent", "LongTermDebt"):
        "difference is the CURRENT portion of long-term debt, reported "
        "separately as a current liability; 'Long-term debt' conventionally "
        "means the noncurrent portion",
    ("NetIncomeLoss", "ProfitLoss"):
        "difference is income attributable to NONCONTROLLING INTERESTS; the "
        "parent figure is what an equity holder owns and is the numerator "
        "EPS is computed from, which the SHARES check confirms independently",
    ("StockholdersEquity",
     "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"):
        "difference is NONCONTROLLING INTERESTS; parent equity is the "
        "standard 'shareholders equity' and the basis for book value",
    ("RevenueFromContractWithCustomerExcludingAssessedTax",
     "RevenueFromContractWithCustomerIncludingAssessedTax"):
        "difference is SALES TAXES COLLECTED, which are not revenue; the "
        "excluding-tax figure is the correct one",
}


# =============================================================================
# PURE CHECKS -- no network, unit-testable offline via --selftest
# =============================================================================

def _by_label(fin):
    return {l["label"]: l for l in (fin.get("lines") or [])}


def check_labelling(fin):
    """Every flow line whose duration differs from the anchor MUST be
    labelled. This is the N-1 invariant stated directly: an unlabelled
    cumulative figure is exactly what RTX rendered."""
    out = []
    anchor_period = fin.get("period")
    for l in fin.get("lines") or []:
        if l.get("end") and anchor_period and l["end"] != anchor_period:
            out.append(("HARD", "MIXED-PERIOD",
                        "{} ends {} but the block is anchored at {}".format(
                            l["label"], l["end"], anchor_period)))
    return out


def check_balance(fin, nci=None):
    """Assets = Liabilities + Equity, within an NCI-tolerant band.

    When the filer tags BOTH equity concepts, the noncontrolling interest is
    a known quantity rather than an allowance, and the identity stops being
    approximate: assets - (liabilities + parent equity) should equal NCI
    EXACTLY. Verifying that is far stronger than tolerating a 5% band, and it
    turns two separately-plausible numbers into one checked relationship.
    """
    b = _by_label(fin)
    a, li, eq = b.get("Total assets"), b.get("Total liabilities"), b.get("Shareholders equity")
    if not (a and li and eq):
        return []
    av, lv, ev = a["value"], li["value"], eq["value"]
    if not av:
        return []
    gap = av - (lv + ev)
    rel = abs(gap) / abs(av)

    if nci is not None:
        residual = gap - nci
        rres = abs(residual) / abs(av)
        if rres <= 0.005:
            return [("INFO", "BALANCE",
                     "assets = liabilities + equity + NCI EXACTLY: residual "
                     "{:,.0f} on {:,.0f} of assets ({:.3%}) after accounting "
                     "for {:,.0f} of noncontrolling interest".format(
                         residual, av, rres, nci))]
        if rres > BALANCE_TOL:
            return [("HARD", "BALANCE",
                     "assets {:,.0f} vs liabilities+equity+NCI {:,.0f} -- "
                     "residual {:,.0f} ({:.1%} of assets) is NOT explained by "
                     "the {:,.0f} of noncontrolling interest the filer "
                     "tags".format(av, lv + ev + nci, residual, rres, nci))]
        return [("INFO", "BALANCE",
                 "balance closes to {:.2%} after NCI of {:,.0f}".format(
                     rres, nci))]

    if rel > BALANCE_TOL:
        return [("HARD", "BALANCE",
                 "assets {:,.0f} vs liabilities+equity {:,.0f} -- gap {:,.0f} "
                 "({:.1%} of assets, tolerance {:.0%})".format(
                     av, lv + ev, gap, rel, BALANCE_TOL))]
    return [("INFO", "BALANCE",
             "balance sheet closes to {:.2%} (NCI not separately tagged; "
             "tolerated, not verified)".format(rel))]


def check_share_coherence(fin):
    """Net income / diluted EPS must imply the same share count this year and
    last. Catches a net income and an EPS that describe different periods --
    a second, independent route to the RTX defect that the labelling check
    would miss if BOTH lines were mislabelled the same way."""
    b = _by_label(fin)
    ni, eps = b.get("Net income"), b.get("Diluted EPS")
    if not (ni and eps) or not eps.get("value"):
        return []
    cur = ni["value"] / eps["value"]
    out = []
    if not (1e6 <= abs(cur) <= 5e10):
        out.append(("FLAG", "SHARES",
                    "implied share count {:,.0f} is outside any plausible "
                    "range -- net income and EPS may not describe the same "
                    "period".format(cur)))
        return out
    if ni.get("yoy") is not None and eps.get("yoy") is not None:
        try:
            pni = ni["value"] / (1 + ni["yoy"] / 100.0)
            peps = eps["value"] / (1 + eps["yoy"] / 100.0)
            prior = pni / peps
            drift = abs(cur - prior) / abs(prior) if prior else 0.0
        except ZeroDivisionError:
            return out
        if drift > SHARE_DRIFT_TOL:
            out.append(("FLAG", "SHARES",
                        "implied shares moved {:.1%} YoY ({:,.0f} -> {:,.0f}) "
                        "-- too large for buybacks; check net income and EPS "
                        "are the same period".format(drift, prior, cur)))
        else:
            out.append(("INFO", "SHARES",
                        "implied shares {:,.0f}, {:+.1%} YoY -- coherent".format(
                            cur, (cur - prior) / prior if prior else 0.0)))
    return out


def check_identities(fin):
    """Revenue >= gross profit >= operating income, among RENDERED lines.
    _consistency_filter should already have dropped violations; if one
    survives to here, the filter did not fire and that is itself a finding."""
    b = _by_label(fin)
    out = []
    for dep, prim in (("Gross profit", "Revenue"),
                      ("Operating income", "Gross profit")):
        d, p = b.get(dep), b.get(prim)
        if d and p and d["unit"] != "USD/shares" and p["unit"] != "USD/shares":
            if d["value"] > p["value"]:
                out.append(("HARD", "IDENTITY",
                            "{} {:,.0f} exceeds {} {:,.0f} -- the consistency "
                            "filter did not fire".format(
                                dep, d["value"], prim, p["value"])))
    return out


def check_anchor_class(fin, headline_bucket, modal_bucket):
    """The specific defect class the 2026-08-10 fix addressed. A ticker whose
    headline vote and universe-wide poll DISAGREE is one where the pre-fix
    code would have rendered the wrong period. Not a defect now -- a
    standing risk marker, and the set worth re-checking after any change to
    anchor selection."""
    out = []
    if headline_bucket and modal_bucket and headline_bucket != modal_bucket:
        out.append(("FLAG", "SPLIT-VOTE",
                    "headline concepts vote '{}' but a universe-wide poll "
                    "votes '{}' -- this ticker WOULD have rendered the wrong "
                    "period before the 2026-08-10 fix".format(
                        headline_bucket, modal_bucket)))
    src = (fin.get("source") or "")
    if src == "10-Q" and headline_bucket and headline_bucket != "Q":
        out.append(("FLAG", "CUMULATIVE-ANCHOR",
                    "10-Q whose headline lines are '{}', not a standalone "
                    "quarter -- legitimate for some filers, but every figure "
                    "in the block is cumulative and must be read that "
                    "way".format(headline_bucket)))
    return out


def concept_candidates(gaap, anchor_end):
    """Every concept in each line's preference list that reports at the anchor
    date. More than one means the label is SCOPE-AMBIGUOUS and the preference
    ORDER -- not the data -- is silently choosing which one the model sees."""
    out = []
    for label, kind, concepts in ec.FINANCIAL_CONCEPTS:
        present = []
        for c in concepts:
            if c not in gaap:
                continue
            units = gaap[c].get("units") or {}
            unit_key = (next((u for u in ("USD", "USD/shares") if u in units), None)
                        or next(iter(units), None))
            if not unit_key:
                continue
            here = [e for e in units[unit_key]
                    if e.get("end") == anchor_end
                    and e.get("form") in ec.XBRL_FORMS
                    and e.get("val") is not None
                    and (e.get("start") or kind != "flow")]
            if not here:
                continue
            pick = (min(here, key=lambda e: ec._duration_days(e)
                        if ec._duration_days(e) is not None else 10**9)
                    if kind == "flow" else here[-1])
            present.append((c, pick.get("val")))
        if len(present) > 1:
            out.append((label, present))
    return out


def check_concept_scope(gaap, fin):
    """A line whose chosen concept is materially SMALLER than another concept
    the filer tags for the same line at the same period.

    ANALYST NOTE (2026-08-11, found on GM by the 8-K cross-check): GM tags
    RevenueFromContractWithCustomerExcludingAssessedTax at $43.762B for the
    quarter while its own 8-K states $48.0B. The period was CORRECT -- this
    is a different defect class entirely. ASC 606 contract revenue excludes
    GM Financial's interest and leasing income, so for any filer with a
    captive finance arm the first entry in the preference list is a
    COMPONENT of revenue being rendered under the label "Revenue". A model
    reading GM's top line would understate it by ~9% and compute every
    margin off the wrong denominator.

    NOT AUTOMATICALLY A DEFECT. RevenueFromContractWithCustomerIncluding-
    AssessedTax is legitimately larger than the Excluding variant by the
    sales taxes collected, and Excluding is the figure we want. The concept
    NAMES are reported so the difference can be judged rather than assumed.
    """
    if not gaap or not fin.get("period"):
        return []
    out = []
    chosen = {l["label"]: l for l in (fin.get("lines") or [])}
    for label, present in concept_candidates(gaap, fin["period"]):
        cur = chosen.get(label)
        if not cur or not cur.get("value"):
            continue
        biggest = max(present, key=lambda p: abs(p[1] or 0))
        cv = abs(cur["value"])
        bv = abs(biggest[1] or 0)
        if bv <= cv * 1.02:
            continue
        reason = _BY_DESIGN.get((cur.get("concept"), biggest[0]))
        if reason:
            out.append(("INFO", "SCOPE-BY-DESIGN",
                        "{}: {} is {:,.0f} below {} -- {}".format(
                            label, cur.get("concept"), bv - cv,
                            biggest[0], reason)))
            continue
        out.append(("FLAG", "SCOPE",
                    "{} renders {} = {:,.0f}, but the filer also tags {} = "
                    "{:,.0f} at the same period ({:.1%} larger). This pair is "
                    "NOT a known by-design exclusion -- if the larger concept "
                    "is the TOTAL and the chosen one a component, the block "
                    "understates this line.".format(
                        label, cur.get("concept") or "?", cur["value"],
                        biggest[0], biggest[1], (bv - cv) / cv)))
    return out


def noncontrolling_interest(gaap, anchor_end):
    """NCI as the filer tags it: total equity less parent equity, when both
    concepts report at the anchor. Returns None when it cannot be computed."""
    if not gaap or not anchor_end:
        return None
    vals = {}
    for c in ("StockholdersEquity",
              "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"):
        if c not in gaap:
            return None
        units = (gaap[c].get("units") or {}).get("USD") or []
        here = [e for e in units
                if e.get("end") == anchor_end and e.get("form") in ec.XBRL_FORMS
                and e.get("val") is not None]
        if not here:
            return None
        vals[c] = here[-1]["val"]
    return (vals["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
            - vals["StockholdersEquity"])


def check_yoy(fin):
    out = []
    for l in fin.get("lines") or []:
        if l.get("yoy") is not None and abs(l["yoy"]) > 150:
            out.append(("FLAG", "YOY",
                        "{} YoY {:+.1f}% -- verify against the filing before "
                        "citing".format(l["label"], l["yoy"])))
    return out


def check_lag(fin, periodic):
    if (periodic and periodic.get("report") and fin.get("period")
            and fin["period"] < periodic["report"]):
        return [("FLAG", "XBRL-LAG",
                 "extract covers {} but the latest {} covers {} -- SEC has "
                 "not published XBRL for the newer filing".format(
                     fin["period"], periodic.get("form"), periodic["report"]))]
    return []


def eightk_revenue_candidates(bodies, limit=8):
    """Revenue-shaped figures stated in the filer's own 8-K text."""
    found = []
    for body in bodies:
        for m in _REV_RE.finditer(body or ""):
            unit = (m.group("unit") or "").lower()
            try:
                num = float(m.group("num").replace(",", ""))
            except ValueError:
                continue
            scale = _SCALE.get(unit)
            if scale is None:
                continue                    # bare number: scale unknowable
            found.append((m.group("label").lower(), num * scale,
                          m.group(0)[:70].replace("\n", " ")))
            if len(found) >= limit:
                return found
    return found


def check_against_8k(fin, candidates, lagged=False):
    """Corroborate the extracted revenue against the filer's own words.

    This is the only check here that reaches OUTSIDE the XBRL feed, and it is
    the one that would have caught RTX on day one: the 8-K said $24.7 billion
    while the block said $46.8 billion, in the same rendered section, and
    nothing compared them.

    TWO COMPARISONS ARE NOT LIKE-FOR-LIKE AND MUST NOT BE REPORTED AS
    DISAGREEMENT (both found on the first live sweep, 2026-08-11, and both
    were defects in THIS FILE rather than in the extract):

      * A 10-K block is ANNUAL. The earnings 8-K in the same 30-day window
        states the QUARTER. MSFT's FY2026 revenue of $331.8B against a
        press-released $90.0B quarter is a 72.9% "disagreement" that is
        simply an annual figure next to a quarterly one. The informative
        test for an annual block is the RATIO -- roughly 3-5x a quarter --
        and an annual revenue that is NOT materially above the quarterly
        figure is the genuine finding.

      * When XBRL LAGS the latest periodic, the block and the 8-K describe
        DIFFERENT QUARTERS by construction. DOW's Q1 $9.794B against a Q2
        press-released $12.1B is a real 23.5% gap between two figures that
        were never supposed to match. The lag is already its own flag; this
        check must not double-count it as a corroboration failure.
    """
    b = _by_label(fin)
    rev = b.get("Revenue")
    if not rev or not candidates:
        return []
    rv = rev["value"]
    best = min(candidates, key=lambda c: abs(c[1] - rv) / rv if rv else 9e9)
    rel = abs(best[1] - rv) / abs(rv) if rv else 9e9

    if lagged:
        return [("INFO", "8K-NOT-COMPARABLE",
                 "revenue {:,.0f} vs 8-K \"{}\" -- NOT COMPARED: XBRL lags "
                 "the latest periodic, so these are different quarters. "
                 "Corroboration is unavailable for this ticker until SEC "
                 "publishes the newer XBRL.".format(rv, best[2].strip()))]

    if (fin.get("source") or "") == "10-K":
        ratio = rv / best[1] if best[1] else 0.0
        if ratio < 1.5:
            return [("FLAG", "8K-DISAGREE",
                     "ANNUAL revenue {:,.0f} is only {:.2f}x the 8-K's "
                     "quarterly \"{}\" -- an annual figure should be "
                     "materially larger; the block may be a quarter "
                     "mislabelled as the year".format(
                         rv, ratio, best[2].strip()))]
        return [("INFO", "8K-ANNUAL",
                 "annual revenue {:,.0f} is {:.2f}x the 8-K's quarterly "
                 "\"{}\" -- consistent with an annual block; NOT a "
                 "like-for-like corroboration".format(
                     rv, ratio, best[2].strip()))]

    if rel <= EIGHTK_TOL:
        return [("INFO", "8K-AGREE",
                 "revenue {:,.0f} matches the 8-K's \"{}\" ({:.2%})".format(
                     rv, best[2].strip(), rel))]
    return [("FLAG", "8K-DISAGREE",
             "revenue {:,.0f} vs nearest 8-K figure {:,.0f} from \"{}\" "
             "-- {:.1%} apart; same period, so either the block picked the "
             "wrong concept scope or it picked the wrong period".format(
                 rv, best[1], best[2].strip(), rel))]


def audit_one(fin, periodic, headline_bucket, modal_bucket, candidates,
              gaap=None):
    """All pure checks for one ticker. Returns list of (severity, code, msg)."""
    findings = []
    findings += check_labelling(fin)
    findings += check_identities(fin)
    findings += check_balance(fin, noncontrolling_interest(gaap, fin.get("period")))
    findings += check_share_coherence(fin)
    findings += check_anchor_class(fin, headline_bucket, modal_bucket)
    findings += check_concept_scope(gaap, fin)
    findings += check_yoy(fin)
    lag = check_lag(fin, periodic)
    findings += lag
    findings += check_against_8k(fin, candidates, lagged=bool(lag))
    if len(fin.get("lines") or []) < 4:
        findings.append(("FLAG", "THIN",
                         "only {} line(s) extracted".format(
                             len(fin.get("lines") or []))))
    if fin.get("degraded"):
        findings.append(("FLAG", "DEGRADED",
                         "run budget cut this ticker's fetch short -- "
                         "absence of financials here is NOT evidence"))
    return findings


# =============================================================================
# LIVE SWEEP
# =============================================================================

def sweep_ticker(tkr, caches):
    """Fetch + extract one ticker. Returns (fin, periodic, hb, mb, cands, note)."""
    cik = ec.load_cik_map(caches).get(tkr)
    if not cik:
        return None, None, None, None, [], None, "no CIK"
    subs = ec.fetch_submissions(cik, caches)
    if not subs:
        return None, None, None, None, [], None, "submissions unavailable"

    rows = ec._recent_rows(subs)
    periodic = ec.extract_periodic(rows, cik)
    fin = ec.extract_financials(cik, periodic.get("accession"),
                                report_date=periodic.get("report"))

    facts = ec._http_get(ec.XBRL_FACTS_URL.format(cik10=cik), as_json=True)
    gaap = (facts.get("facts") or {}).get("us-gaap") or {} if facts else {}
    rd = periodic.get("report")
    hb = ec._headline_flow_bucket(gaap, rd) if (gaap and rd) else None
    mb = ec._modal_flow_bucket(gaap, rd) if (gaap and rd) else None

    eightk = ec.extract_8k(rows, ec._window_start(), cik10=cik)
    cands = eightk_revenue_candidates([e.get("body", "")
                                       for e in eightk.get("events", [])])
    return fin, periodic, hb, mb, cands, gaap, None


def render(results):
    L = []
    add = L.append
    add("=" * 78)
    add("XBRL FINANCIAL EXTRACT SWEEP -- {}".format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    add("=" * 78)

    hard = flags = 0
    for tkr, fin, findings, note in results:
        if note:
            add("")
            add("{:<6} SKIPPED -- {}".format(tkr, note))
            continue
        h = [f for f in findings if f[0] == "HARD"]
        fl = [f for f in findings if f[0] == "FLAG"]
        info = [f for f in findings if f[0] == "INFO"]
        hard += len(h)
        flags += len(fl)
        verdict = "HARD" if h else ("FLAG" if fl else "ok")
        add("")
        # An annual filing carries fp="FY", so the naive "{fp}FY{fy}" renders
        # "FYFY2026". format_financials() in edgar_client already handles
        # this; the sweep's own header did not. Same rule, stated once.
        fp, fy = fin.get("fp"), fin.get("fy")
        if fy:
            per = ("FY{}".format(fy) if fp in (None, "", "FY")
                   else "{} FY{}".format(fp, fy))
        else:
            per = fp or "?"
        add("{:<6} [{:<4}] {} line(s), {} {} period ended {}".format(
            tkr, verdict, len(fin.get("lines") or []),
            fin.get("source") or "?", per, fin.get("period")))
        for sev, code, msg in h + fl:
            add("         {:<4} {:<18} {}".format(sev, code, msg))
        for sev, code, msg in info:
            add("         {:<4} {:<18} {}".format("--", code, msg))

    add("")
    add("-" * 78)
    add("SUMMARY: {} ticker(s), {} HARD finding(s), {} FLAG(s)".format(
        len([r for r in results if not r[3]]), hard, flags))
    add("")
    add("A HARD finding means the block is internally incoherent -- something")
    add("in it is provably wrong. A FLAG means it needs a human read; the")
    add("SPLIT-VOTE and 8K-DISAGREE flags are the two that carry the RTX")
    add("defect class, and 8K-DISAGREE is the only check here that compares")
    add("the extract to anything outside the XBRL feed itself.")
    add("")
    add("A clean sweep is evidence of COHERENCE, not a certificate of")
    add("accuracy. Read the eyeball queue.")
    add("")
    add("Advisory-only . no orders . not financial advice.")
    return "\n".join(L)


# =============================================================================
# SELFTEST -- offline, exercises every check with synthetic extracts
# =============================================================================

def _selftest():
    fails = []

    def check(name, got, want):
        ok = got == want
        print("  [{}] {}".format("PASS" if ok else "FAIL", name))
        if not ok:
            print("        got:  {!r}".format(got))
            print("        want: {!r}".format(want))
            fails.append(name)

    def codes(findings, sev=None):
        return sorted({c for s, c, _ in findings if sev is None or s == sev})

    def line(label, value, yoy=None, end="2026-06-30", unit="USD"):
        return {"label": label, "value": value, "yoy": yoy, "end": end,
                "unit": unit, "period_note": None}

    # --- a clean RTX-shaped block ------------------------------------------
    print("clean block (RTX post-fix shape)")
    good = {"source": "10-Q", "fy": 2026, "fp": "Q2", "period": "2026-06-30",
            "degraded": False, "lines": [
                line("Revenue", 24_708_000_000, 14.5),
                line("Operating income", 2_811_000_000, 31.0),
                line("Net income", 2_139_000_000, 29.1),
                line("Diluted EPS", 1.57, 28.7, unit="USD/shares"),
                line("Total assets", 173_972_000_000, 4.1),
                line("Total liabilities", 105_828_000_000, 2.9),
                line("Shareholders equity", 66_377_000_000, 6.4)]}
    f = audit_one(good, {"report": "2026-06-30", "form": "10-Q"}, "Q", "H", [])
    check("no HARD findings on a clean block", codes(f, "HARD"), [])
    check("split vote is flagged even when the block is correct",
          "SPLIT-VOTE" in codes(f, "FLAG"), True)
    check("balance sheet closes despite NCI",
          [c for s, c, _ in f if c == "BALANCE" and s == "HARD"], [])
    check("implied shares reported as coherent",
          any(s == "INFO" and c == "SHARES" for s, c, _ in f), True)

    # --- the ACTUAL pre-fix RTX block, verbatim ----------------------------
    # RECORDED HONESTLY: the whole block was internally CONSISTENT. Every
    # line was the half-year, so the balance sheet closed, the identities
    # held, and net income / EPS implied a perfectly sensible ~1.36e9 shares.
    # NO internal-coherence check can catch this, and pretending otherwise
    # would be the same mistake as trusting a green harness. What catches it
    # is the anchor class and the filer's own press release -- nothing else.
    print("the ACTUAL pre-fix RTX block -- what does and does NOT catch it")
    prefix = dict(good)
    prefix["lines"] = [line("Revenue", 46_784_000_000, 11.7),
                       line("Operating income", 5_366_000_000, 28.3),
                       line("Net income", 4_198_000_000, 31.5),
                       line("Diluted EPS", 3.08, 30.5, unit="USD/shares"),
                       line("Total assets", 173_972_000_000, 4.1),
                       line("Total liabilities", 105_828_000_000, 2.9),
                       line("Shareholders equity", 66_377_000_000, 6.4)]
    f = audit_one(prefix, {"report": "2026-06-30", "form": "10-Q"}, "H", "H", [])
    check("pre-fix block is internally COHERENT -- no HARD finding",
          codes(f, "HARD"), [])
    check("share drift does NOT catch it (both lines were the half-year)",
          "SHARES" in codes(f, "FLAG"), False)
    check("CUMULATIVE-ANCHOR is one of the two things that DOES catch it",
          "CUMULATIVE-ANCHOR" in codes(f, "FLAG"), True)

    # --- the mix share-drift IS for: two lines, two different buckets ------
    print("share drift catches net income and EPS drawn from different buckets")
    drift = dict(good)
    drift["lines"] = [line("Net income", 4_198_000_000, 31.5),
                      line("Diluted EPS", 1.57, 0.0, unit="USD/shares")]
    check("implied share count moving >25% YoY is flagged",
          "SHARES" in codes(audit_one(drift, None, "Q", "Q", []), "FLAG"), True)

    # --- broken balance sheet ----------------------------------------------
    print("balance-sheet identity")
    bad = dict(good)
    bad["lines"] = [line("Total assets", 100_000_000_000),
                    line("Total liabilities", 40_000_000_000),
                    line("Shareholders equity", 20_000_000_000)]
    check("a 40% hole is HARD",
          "BALANCE" in codes(audit_one(bad, None, "Q", "Q", []), "HARD"), True)
    ok_bs = dict(good)
    ok_bs["lines"] = [line("Total assets", 100_000_000_000),
                      line("Total liabilities", 60_000_000_000),
                      line("Shareholders equity", 39_000_000_000)]
    check("a 1% NCI gap is not",
          "BALANCE" in codes(audit_one(ok_bs, None, "Q", "Q", []), "HARD"), False)

    # --- mixed period ------------------------------------------------------
    print("mixed reporting periods")
    mp = dict(good)
    mp["lines"] = [line("Revenue", 24_708_000_000, end="2026-06-30"),
                   line("Net income", 2_139_000_000, end="2026-03-31")]
    check("a line off the anchor date is HARD",
          "MIXED-PERIOD" in codes(audit_one(mp, None, "Q", "Q", []), "HARD"), True)

    # --- accounting identity surviving the filter --------------------------
    print("identity violation that survived _consistency_filter")
    iv = dict(good)
    iv["lines"] = [line("Revenue", 10_000_000_000),
                   line("Gross profit", 2_000_000_000),
                   line("Operating income", 3_000_000_000)]
    check("operating income above gross profit is HARD",
          "IDENTITY" in codes(audit_one(iv, None, "Q", "Q", []), "HARD"), True)

    # --- 8-K cross-check ---------------------------------------------------
    print("8-K corroboration")
    body = ("RTX Reports Q2 2026 Results. Second quarter 2026 Sales of "
            "$24.7 billion, up 14 percent versus prior year.")
    cands = eightk_revenue_candidates([body])
    check("revenue figure parsed from the press release",
          bool(cands) and abs(cands[0][1] - 24.7e9) < 1e6, True)
    f = audit_one(good, None, "Q", "Q", cands)
    check("matching revenue reads as agreement",
          "8K-AGREE" in codes(f, "INFO"), True)
    f = audit_one(prefix, None, "H", "H", cands)
    check("the pre-fix $46.8B block DISAGREES with the same 8-K",
          "8K-DISAGREE" in codes(f, "FLAG"), True)

    # --- the two false positives the first live sweep produced -------------
    # Both were defects in THIS FILE, not in the extract. Fixtured so they
    # cannot come back.
    print("annual block vs quarterly press release (the MSFT false positive)")
    annual = {"source": "10-K", "fy": 2026, "fp": "FY", "period": "2026-06-30",
              "degraded": False,
              "lines": [line("Revenue", 331_839_000_000, 15.0)]}
    q_body = "Microsoft Cloud Strength Drives Fourth Quarter Results. Revenue was $90.0 billion."
    qc = eightk_revenue_candidates([q_body])
    f = audit_one(annual, None, "FY", "FY", qc)
    check("annual-vs-quarterly is NOT reported as disagreement",
          "8K-DISAGREE" in codes(f, "FLAG"), False)
    check("it is reported as an annual, non-comparable read",
          "8K-ANNUAL" in codes(f, "INFO"), True)
    thin_year = dict(annual)
    thin_year["lines"] = [line("Revenue", 95_000_000_000, 15.0)]
    check("an 'annual' revenue barely above one quarter IS flagged",
          "8K-DISAGREE" in codes(audit_one(thin_year, None, "FY", "FY", qc),
                                 "FLAG"), True)

    print("lagged XBRL vs a newer 8-K (the DOW false positive)")
    lagged = {"source": "10-Q", "fy": 2026, "fp": "Q1", "period": "2026-03-31",
              "degraded": False,
              "lines": [line("Revenue", 9_794_000_000, 2.0, end="2026-03-31")]}
    dow_body = "Dow reports second quarter results. Net sales were $12.1 billion."
    dc = eightk_revenue_candidates([dow_body])
    f = audit_one(lagged, {"report": "2026-06-30", "form": "10-Q"},
                  "Q", "Q", dc)
    check("lag is flagged", "XBRL-LAG" in codes(f, "FLAG"), True)
    check("a lagged block is NOT also reported as 8-K disagreement",
          "8K-DISAGREE" in codes(f, "FLAG"), False)
    check("corroboration is reported as unavailable, not as agreement",
          "8K-NOT-COMPARABLE" in codes(f, "INFO"), True)

    # --- degraded / thin ---------------------------------------------------
    print("concept scope (the GM finding)")
    # GM tags contract revenue AND, if present, a total-revenue concept at the
    # same period. The chosen concept being materially SMALLER than another
    # the filer tags for the same line is the signature.
    gm_gaap = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 43_762_000_000,
             "form": "10-Q", "fy": 2026, "fp": "Q2"}]}},
        "Revenues": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 48_000_000_000,
             "form": "10-Q", "fy": 2026, "fp": "Q2"}]}},
    }
    gm_fin = {"source": "10-Q", "fy": 2026, "fp": "Q2", "period": "2026-06-30",
              "degraded": False, "lines": [
                  {"label": "Revenue", "value": 43_762_000_000, "yoy": None,
                   "end": "2026-06-30", "unit": "USD", "period_note": None,
                   "concept": "RevenueFromContractWithCustomerExcludingAssessedTax"}]}
    amb = concept_candidates(gm_gaap, "2026-06-30")
    check("both revenue concepts detected at the anchor",
          [lab for lab, _ in amb], ["Revenue"])
    check("a component chosen over a larger total is flagged",
          "SCOPE" in codes(check_concept_scope(gm_gaap, gm_fin), "FLAG"), True)

    # The 14 false positives from the first live run: known by-design pairs.
    by_design = {
        "NetIncomeLoss": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 2_139_000_000,
             "form": "10-Q"}]}},
        "ProfitLoss": {"units": {"USD": [
            {"start": "2026-04-01", "end": "2026-06-30", "val": 2_249_000_000,
             "form": "10-Q"}]}},
    }
    ni_fin = {"source": "10-Q", "fy": 2026, "fp": "Q2", "period": "2026-06-30",
              "degraded": False, "lines": [
                  {"label": "Net income", "value": 2_139_000_000, "yoy": None,
                   "end": "2026-06-30", "unit": "USD", "period_note": None,
                   "concept": "NetIncomeLoss"}]}
    r = check_concept_scope(by_design, ni_fin)
    check("NetIncomeLoss vs ProfitLoss is NOT flagged",
          "SCOPE" in codes(r, "FLAG"), False)
    check("it is still reported, as by-design",
          "SCOPE-BY-DESIGN" in codes(r, "INFO"), True)

    print("balance sheet verified against tagged NCI, not merely tolerated")
    eq_gaap = {
        "StockholdersEquity": {"units": {"USD": [
            {"end": "2026-06-30", "val": 66_377_000_000, "form": "10-Q"}]}},
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest":
            {"units": {"USD": [
                {"end": "2026-06-30", "val": 68_116_000_000, "form": "10-Q"}]}},
    }
    check("NCI derived from the two equity concepts",
          noncontrolling_interest(eq_gaap, "2026-06-30"), 1_739_000_000)
    bs = {"source": "10-Q", "period": "2026-06-30", "degraded": False,
          "lines": [line("Total assets", 173_972_000_000),
                    line("Total liabilities", 105_828_000_000),
                    line("Shareholders equity", 66_377_000_000)]}
    msg = check_balance(bs, 1_739_000_000)
    check("residual explained by NCI reads as EXACT",
          "EXACTLY" in msg[0][2], True)
    # A tiny NCI against RTX's real 1.77bn residual still leaves only ~1.0%
    # unexplained, which is inside tolerance and correctly NOT hard -- the
    # first draft of this test asserted HARD and was simply wrong about its
    # own arithmetic. The genuine case is a residual that survives NCI and
    # still exceeds the band.
    check("a small NCI leaves a residual inside tolerance, not HARD",
          check_balance(bs, 100)[0][0], "INFO")
    hole = {"source": "10-Q", "period": "2026-06-30", "degraded": False,
            "lines": [line("Total assets", 100_000_000_000),
                      line("Total liabilities", 40_000_000_000),
                      line("Shareholders equity", 20_000_000_000)]}
    check("a 40% hole that NCI cannot explain is HARD",
          check_balance(hole, 1_000_000_000)[0][0], "HARD")
    solo = {"RevenueFromContractWithCustomerExcludingAssessedTax":
            gm_gaap["RevenueFromContractWithCustomerExcludingAssessedTax"]}
    check("a single tagged concept is never a scope finding",
          check_concept_scope(solo, gm_fin), [])

    print("degraded and thin extracts")
    dg = {"source": "10-Q", "fy": 2026, "fp": "Q2", "period": "2026-06-30",
          "degraded": True, "lines": []}
    c = codes(audit_one(dg, None, None, None, []), "FLAG")
    check("degraded is flagged, not read as 'no financials'", "DEGRADED" in c, True)
    check("thin extract flagged", "THIN" in c, True)

    print("")
    if fails:
        print("SELFTEST FAILED: {} check(s)".format(len(fails)))
        for f_ in fails:
            print("  - {}".format(f_))
        return 1
    print("ALL PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Cross-ticker coherence and corroboration audit of the "
                    "XBRL financial extract. Advisory-only.")
    ap.add_argument("--tickers", help="comma-separated; default = covered set")
    ap.add_argument("--from-log", action="store_true",
                    help="use the watchlist from the most recent signals log")
    ap.add_argument("--md", help="write a markdown exhibit to this path")
    ap.add_argument("--budget", type=float,
                    help="override EDGAR_MAX_SECONDS for this sweep "
                         "(a 15-ticker sweep fetches 15 companyfacts "
                         "documents and will trip the 120s default)")
    ap.add_argument("--selftest", action="store_true",
                    help="offline check of every audit rule; no network")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    elif args.from_log:
        got = ec.watchlist_from_latest_log()
        if not got:
            print("no readable log; falling back to the covered set")
            tickers = COVERED_DEFAULT
        else:
            tickers, src = got
            print("watchlist from {}".format(src))
    else:
        tickers = COVERED_DEFAULT

    if args.budget:
        ec.EDGAR_MAX_SECONDS = args.budget
    else:
        # A sweep is not a signal run; the per-run budget exists to protect
        # the daily cohort's wall clock and is the wrong limit here. Raise it
        # rather than let tickers silently degrade to fin=none, which would
        # read as "no financials" and be exactly the kind of quiet wrong
        # answer this tool exists to catch.
        ec.EDGAR_MAX_SECONDS = max(ec.EDGAR_MAX_SECONDS, 60.0 * len(tickers))
    ec.reset_budget()

    if not ec.load_cik_map({}):
        print("CIK map unavailable. Check SEC_USER_AGENT in .env and egress "
              "to www.sec.gov.")
        return 2

    caches = {}
    results = []
    for i, t in enumerate(tickers, 1):
        print("  [{}/{}] {} ...".format(i, len(tickers), t))
        try:
            fin, periodic, hb, mb, cands, gaap, note = sweep_ticker(t, caches)
        except Exception as e:                            # never die mid-sweep
            results.append((t, None, [], "error: {}".format(e)))
            continue
        if note:
            results.append((t, None, [], note))
            continue
        results.append((t, fin,
                        audit_one(fin, periodic, hb, mb, cands, gaap), None))

    report = render(results)
    print("")
    print(report)

    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write("# XBRL extract sweep\n\n*Generated {}. Advisory-only.*\n\n"
                    "```\n{}\n```\n".format(
                        datetime.now().strftime("%Y-%m-%d %H:%M"), report))
        print("Wrote: {}".format(args.md))

    return 1 if any(s == "HARD" for _, _, fs, n in results if not n
                    for s, _, _ in fs) else 0


if __name__ == "__main__":
    sys.exit(main())
