#!/usr/bin/env python3
"""implied_return.py — run the value-driver identity BACKWARDS.

THE EQUATION, AND WHY BACKWARDS
    The packet's horizon-value form (p.1072), written on the equity side:

        M/B = 1 + ((1+g)*ROE - r_s) / (r_s - g)

    Forwards, you assume ROE, r_s and g and out comes a price. That price is
    ~77% terminal value and moves ~13% on 100bp of g -- the most confidently
    stated and least defensible number this project could emit.

    Backwards, the price is an OBSERVATION and the equation answers a question
    with no free parameters but one:

        r_s_implied  = [ (1+g)*ROE + (M/B - 1)*g ] / (M/B)          ... (I)
        ROE_implied  = [ r_s + (M/B - 1)*(r_s - g) ] / (1+g)        ... (II)

    (I) asks: at the ROE this company actually earns, what discount rate is
        the market applying?
    (II) asks: at a normal cost of equity, what ROE must the market believe
        this company will earn?

    Both are the SAME equation. (II) is the more useful one here, and the
    reason is measured, not asserted -- see the SENSITIVITY section.

NO VALUATION IS PRODUCED. No price target, no fair value, no buy or sell.
    Not a gate, not a signal, not an input to any E4 endpoint. Does not touch
    the prompt, edgar_client.py, KEEP-70, H4 or the +/-3% band. Reads and
    prints; writes nothing unless --md is given.

SENSITIVITY -- WHY (II) BEATS (I), AND FOR WHICH NAMES
    Differentiating (I):

        d r_s / d g = (ROE + M/B - 1) / (M/B) = 1 + (ROE - 1)/(M/B)

    As M/B grows this tends to 1, so r_s_implied just hands g back. At
    M/B = 41.7 the equation is nearly content-free; at M/B = 1.3 it is
    informative. THE TOOL REPORTS THIS DERIVATIVE PER NAME and says which
    names the identity can actually speak about. That is the same lesson as
    the horizon-value sensitivity, reached from the other end of Chapter 7.

INPUT PROVENANCE -- TWO ROUTES TO ROE, AND WHY ONE IS PREFERRED
    PRIMARY:  ROE = eps(LAST FISCAL YEAR) / BVPS, eps from schwab_client's
              `fundamental` block via quote_dump.json, BVPS from the XBRL cache.
              NOT trailing-twelve-month -- see the retraction below.
    FALLBACK: ROE = net income / shareholders equity, both from the SAME
              EDGAR accession. The eps and the implied share count CANCEL out
              of this form, so it depends on neither.

    Schwab is primary because a full fiscal year beats one quarter multiplied by
    four -- x4 assumes four identical quarters and overstates NVDA by 58 points
    and FTI by 16. But "primary" now means least-bad, not right: a last-fiscal-
    year figure is STALE by up to four quarters. THE BASIS IS CARRIED ON EVERY
    ROW and the two are never pooled in a ranked column unlabelled.

    ★ RETRACTED 2026-08-17, SAME DAY, ON OPERATOR-SUPPLIED EVIDENCE. This
    docstring previously claimed the two routes "agree to the penny on MSFT and
    NKE" and called that "the strongest validation available here." IT IS NOT
    VALIDATION. value_anchor derives shares = NI/EPS_edgar, so substituting:

        ROE_schwab = eps_S / BVPS = NI*eps_S / (BE*eps_E)
        ROE_edgar  = NI / BE
        ratio      = eps_S / eps_E

    THE TWO ROUTES ARE ALGEBRAICALLY IDENTICAL whenever eps_S == eps_E -- one
    identity reached by two paths, not two independent measurements. And for a
    10-K filer, Schwab's eps IS that 10-K's EPS, so agreement was GUARANTEED
    for exactly the FY filers and no others. That is precisely the pattern
    that was read as evidence. Arithmetic dressed as corroboration.

    WORSE: `eps` IS NOT TRAILING-TWELVE-MONTH. Verified against GM's own XBRL
    -- Schwab reports eps 3.27, and GM's FY2025 10-K diluted EPS is 3.27,
    exactly. GM's TRUE TTM, rebuilt from the same XBRL as
    FY2025 - H1 2025 + H1 2026 = 3.27 - 5.29 + 4.25, is 2.23, giving ROE 3.33%
    against Morningstar's independently published 3.28%. So Schwab's field is
    the LAST FISCAL YEAR and the label "Schwab TTM" used here until now was
    wrong. It is renamed "Schwab last-FY".

    CONSEQUENCE, STATED PLAINLY: neither route is TTM. The EDGAR route is a
    quarter x4; the Schwab route is a stale fiscal year. For a Q filer whose
    results have moved, BOTH are wrong and they are wrong in different
    directions -- GM reads 4.88% here against a true TTM near 3.33%, a 1.5x
    overstatement. Every figure downstream of ROE inherits it. Rebuilding true
    TTM needs four quarters of filings and the cache holds one accession per
    filer, so it is NOT fixable here; it is labelled instead.

    A SCHWAB `eps` OF EXACTLY 0.0 IS TREATED AS A PLACEHOLDER, NOT A ZERO, when
    `peRatio` contradicts it. CBRS returns eps 0.0 with peRatio 479.19; SPCX
    returns eps 0.0 with peRatio -58.60. A true zero implies an undefined P/E,
    not a finite one. RECORDED AS A CORRECTION: this was first attributed to
    schwab_client's `.get(field, 0)` defaults. Removing those defaults on
    2026-08-17 proved otherwise -- the values came back 0.0 rather than None,
    so Schwab itself supplies the placeholder. The default removal was still
    correct and it changed the prompt for zero names, but it was not the cause.

    `peRatio` is NOT used, and that is a finding rather than an omission.
    A second route to the same ROE would be (M/B) / (P/E), which is
    algebraically identical to eps/BVPS. Tested 2026-08-17 across 15 names:
    peRatio / (lastPrice/eps) ranges 0.112 to 1.911 and is not constant, so
    the two fields are NOT the same measure. The pattern is coherent -- every
    name where forward looks cheaper is a grower, and the only names where it
    looks dearer are MSFT, NKE, PM, GM and DOW, with GM's own XBRL showing
    operating income -31.4% YoY and DOW loss-making. THE READING IS THEREFORE
    THAT `eps` IS TRAILING AND `peRatio` IS FORWARD, and it is marked [?]
    because schwab_client documents neither. Using peRatio as a trailing input
    would have silently mixed a forecast into a forecast-free instrument.
    SETTLED 2026-10-24 (sec_data_audit; claude/DP-V4_ValueCard_TTM_2026-10-24.md):
    peRatio is Schwab's TRAILING 12-MONTH P/E, not a forward one. Price over
    peRatio equals the SEC 12-month diluted EPS within about 1% on AAPL, JPM,
    MSFT, NVDA, PM, PWR, SND and WMT, and lags it only where a 10-Q landed that
    week (GM, DOW). `eps` is the last fiscal year. The pattern above was real,
    but it measured earnings that HAD moved since the last 10-K, not an
    expectation. peRatio is still not an input here; the value card's class
    reads 12-month ROE from SEC filings (DP-V4).

    PRICE COMES FROM THE MASTER, not from quote_dump.json, even though the
    dump carries a fresher lastPrice. One price source, deliberately: the
    master's Price at Signal is the record, value_anchor.py already uses it,
    and a second price source is how two correct numbers get quoted as each
    other. The dump's price is reported alongside as drift only.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

try:
    import value_anchor as VA
except ImportError:
    sys.stderr.write("REFUSED: value_anchor.py must sit beside this file; the\n"
                     "accession-to-ticker join is imported from it rather than\n"
                     "duplicated (one source of truth for the join).\n")
    sys.exit(2)

DEFAULT_QUOTES = "quote_dump.json"

# Long-run growth grid. NOT a forecast -- a grid, reported in full, so no
# single value is privileged. Upper bound is deliberately below long-run
# nominal GDP growth; g >= r_s does not converge and is rejected outright.
G_GRID = (0.00, 0.02, 0.03, 0.04)

# Cost-of-equity grid for the reverse read (II). Spans the range a CAPM
# estimate would plausibly produce for a large-cap US equity.
#
# THESE ARE NOT DERIVED FROM THIS PROJECT'S DATA, and the reason is now settled
# rather than open. The betas computable from the master do not reproduce known
# market relationships (SCHD/SPY rho = 0.098 against a real-world ~0.85). Three
# explanations were tested on 2026-08-17 and two were REJECTED:
#   - bad price data: REJECTED. State Street reports XLU NAV 44.30 and Schwab
#     Asset Management reports SCHD NAV 34.50, both as of 2026-08-14, against
#     master closes of 44.19 and 34.29. The prices are real.
#   - date misalignment: REJECTED. Lagged correlations peak cleanly at lag 0
#     for VTI (0.939) and QQQ (0.920); a shifted series would displace those too.
# What remains is sample length: 57 daily observations over one three-month
# window cannot estimate a beta, and the master will not hold enough history for
# roughly two years. So a CAPM r_s is unavailable here for a mundane reason, the
# grid is exogenous, and closing the gap needs an EXTERNAL beta, not more work
# on this data.
RS_GRID = (0.07, 0.09, 0.11)

# Above this, (I) is returning g rather than information.
DRDG_UNINFORMATIVE = 0.90
DRDG_INFORMATIVE = 0.50


def r_s_implied(roe, mb, g):
    """(I). None when M/B <= 0 or the result is not economically meaningful."""
    if mb is None or mb <= 0:
        return None
    return ((1.0 + g) * roe + (mb - 1.0) * g) / mb


def roe_implied(rs, mb, g):
    """(II). Defined for any M/B > 0 regardless of trailing ROE -- which is
    why it still works on a name whose trailing ROE is negative."""
    if mb is None or mb <= 0:
        return None
    if g >= rs:
        return None                      # non-convergent; refuse rather than emit
    return (rs + (mb - 1.0) * (rs - g)) / (1.0 + g)


def g_implied(roe, mb, rs):
    """(III) — the THIRD rearrangement of the same equation. Solve for growth.

    Expanding the packet's form gives  M/B = [(1+g)ROE - g] / (r_s - g),  so

        g_implied = (M/B*r_s - ROE) / (M/B + ROE - 1)

    WHY THIS EXISTS. The denominator is exactly  M/B * (dr_s/dg).  So (III) is
    well-determined precisely where (I) degenerates: a high M/B makes r_s
    uninformative and g informative, and a low M/B does the reverse. The two
    reads are complements, not alternatives, and which one to trust is decided
    by the same derivative already reported in section 2.

    Returns None when no convergent g exists (g >= r_s), which is itself the
    finding: the price cannot be explained by this model at that discount rate.
    """
    if mb is None or mb <= 0:
        return None
    den = mb + roe - 1.0
    if den == 0:
        return None
    g = (mb * rs - roe) / den
    if g >= rs:
        return None                      # non-convergent; refuse rather than emit
    return g


def drs_dg(roe, mb):
    """Analytic d r_s / d g. Verified against a numerical difference in --selftest."""
    if mb is None or mb <= 0:
        return None
    return (roe + mb - 1.0) / mb


def r_s_dividend(div_yield_pct, g):
    """Packet p.1072, expected rate of return: r_s = D1/P0 + g, with
    D1/P0 = (D0/P0)(1+g). div_yield_pct is a PERCENT as schwab_client returns
    it (claude_signal.py formats it '{div:.2f}%')."""
    if div_yield_pct is None:
        return None
    return (div_yield_pct / 100.0) * (1.0 + g) + g


def roe_from_edgar(fin):
    """ROE straight from the filing: net income / shareholders equity.

    THE EPS AND THE SHARE COUNT CANCEL. The Schwab route is
        ROE = eps / BVPS,  BVPS = equity/shares,  shares = NI/EPS_edgar
    which substitutes to NI/equity. So going to EDGAR directly removes BOTH
    the reported-EPS dependency and the implied-share-count dependency, and
    numerator and denominator come from the SAME accession, so they cannot
    be period-mismatched against each other.

    THE PERIOD IS THE CATCH, and it is not a small one. A 10-Q's net income
    is ONE QUARTER; Schwab's eps is TTM. Annualising by x4 assumes four
    identical quarters, which is false for any seasonal or lumpy business --
    measured 2026-08-17, x4 overstates NVDA by 58 points and FTI by 16.
    Returns the basis so it can never be pooled with a TTM figure unlabelled.
    """
    lm = VA.line_map(fin)
    ni = lm.get(VA.L_NI, {}).get("value")
    note = lm.get(VA.L_NI, {}).get("period_note")
    be, _src, _n = VA.book_equity(fin)
    if ni is None or be is None or be <= 0:
        return None, None, None
    fp = fin.get("fp")
    period_roe = ni / be
    if fp == "FY":
        return period_roe, "EDGAR annual (10-K)", 1.0
    return period_roe * 4.0, f"EDGAR quarterly x4{' [' + note + ']' if note else ''}", 4.0


def _q(v):
    return "--" if v is None else f"{v:.1f}Q"


def roe_vintage(r, run_date):
    """DP-3C-aq (RULED 2026-09-25): (anchor_age_q, numerator_age_q) in quarters.

    Reporting only -- zero new concepts, no schema bump, no figure changes.
    The fiscal-period offset is read from the fin cache's own `fp` field; an
    unknown fp returns None for the numerator rather than a guessed age."""
    try:
        anc = dt.date.fromisoformat(str(r.get("anchor"))[:10])
        rd = run_date if isinstance(run_date, dt.date) else dt.date.fromisoformat(str(run_date)[:10])
    except (TypeError, ValueError):
        return None, None
    a_age = (rd - anc).days / 91.3125
    if r.get("basis") == "Schwab last-FY":
        off = {"FY": 0, "Q4": 0, "Q1": 1, "Q2": 2, "Q3": 3}.get(str(r.get("fp") or "").upper())
        return a_age, (None if off is None else a_age + off)
    return a_age, a_age


def eps_is_reliable(q, price):
    """Schwab's `eps` can be a PLACEHOLDER ZERO that its own `peRatio`
    contradicts.

    Measured 2026-08-17, after the `.get(field, 0)` defaults were removed:
    CBRS returns eps 0.0 with peRatio 479.19 at a price of 253.00, and SPCX
    returns eps 0.0 with peRatio -58.60 at 145.89. If eps were truly zero the
    P/E would be undefined, not 479. So the zero is Schwab's own placeholder
    for 'no data', NOT an artifact of the default that was removed -- the
    removal was still correct, but it was not the cause and this is recorded
    so the earlier reading is not repeated.

    Returns (ok, reason).
    """
    eps = q.get("eps")
    pe = q.get("peRatio")
    if eps is None:
        return False, "eps absent from the quote payload"
    if eps == 0:
        if pe not in (None, 0):
            implied = price / pe if price and pe else None
            return False, (f"eps is 0.0 but peRatio is {pe:,.2f}, which implies "
                           f"eps ~ {implied:,.4f} at this price -- Schwab's own "
                           f"two fields contradict each other, so eps is a "
                           f"placeholder, not a measurement")
        return False, "eps is 0.0 with no peRatio to corroborate it"
    return True, None


def load_quotes(path):
    if not os.path.exists(path):
        return None, f"quote dump not found at {path} -- run quote_dump.py"
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        return None, f"unreadable quote dump: {e}"
    if not isinstance(d, dict) or "quotes" not in d:
        return None, "quote dump has no 'quotes' key"
    if not d.get("succeeded"):
        return None, ("quote dump records succeeded=0 -- every Schwab call "
                      "failed, most likely an expired OAuth token")
    return d, None


def report(tracker, cache_dir, log_path, quotes_path, md_path=None):
    L = []
    def out(s=""):
        L.append(s); print(s)
    findings = []

    qd, qerr = load_quotes(quotes_path)
    rows = VA.load_master(tracker)
    cohort_date, cohort = VA.latest_cohort(rows)
    watchlist = sorted(cohort)

    out("=" * 100)
    out("IMPLIED RETURN -- the value-driver identity, run backwards")
    out("No price target. No fair value. No signal. Changes nothing.")
    out("=" * 100)
    out(f"master cohort {cohort_date}   watchlist {len(watchlist)}")
    if qd:
        out(f"quotes {os.path.basename(quotes_path)} captured {qd.get('captured_local')}"
            f"   {qd.get('succeeded')}/{qd.get('requested')} ok")
    out()
    if qerr:
        out(f"NOT COMPUTED for every name: {qerr}")
        # EXIT 2, NOT 1. Nothing was computed, so this is a could-not-run state,
        # not a findings state. value.bat branches on the difference: a 1 lets
        # the pass report FINDINGS (a normal outcome) while a 2 reports
        # INCOMPLETE and suppresses the downstream step. Returning 1 here made a
        # total input failure read as a routine result.
        return 2

    fins, ferr = VA.load_fins(cache_dir)
    findings.extend(ferr)
    fn_map, fn_ambig = VA.filename_join(cache_dir, watchlist)
    tags = VA.parse_log_tags(log_path)
    verified, unverified = VA.verified_join(fins, fn_map, tags)
    out(f"join: {len(verified)} verified, {len(unverified)} unverified "
        f"(join logic imported from value_anchor.py, not duplicated)")
    out()

    Q = qd["quotes"]

    # ---- assemble the inputs
    recs, blocked = [], []
    for tk in sorted(verified):
        _acc, fin = verified[tk]
        be, be_src, be_note = VA.book_equity(fin)
        sh, sh_why = VA.implied_shares(fin)
        px = cohort.get(tk, {}).get("px")
        q = Q.get(tk, {})
        eps = q.get("eps")
        why = None
        if be is None:
            why = be_note
        elif sh is None:
            why = sh_why
        elif px is None:
            why = "no price in the master's latest cohort"
        elif be <= 0:
            why = f"book equity is non-positive ({VA.money(be)}); M/B undefined"
        elif q.get("is_etf"):
            why = "ETF -- schwab_client suppresses eps/peRatio by design; ROE undefined"
        if why:
            blocked.append((tk, why))
            continue

        bvps = be / sh
        mb = px / bvps

        # ROE SOURCE SELECTION, with the basis carried on every row.
        # Schwab TTM is PREFERRED because its period is the right one. EDGAR is
        # the FALLBACK, used only when Schwab's eps fails the reliability check,
        # and it is annualised from a single quarter for 10-Q filers -- which is
        # why the basis travels with the number and the two are never pooled in
        # a ranked column without it. The 2026-08-14 rule: quote each with its
        # population attached, or not at all.
        ok_eps, eps_why = eps_is_reliable(q, px)
        roe_e, basis_e, _mult = roe_from_edgar(fin)
        if ok_eps:
            roe, basis, fallback_reason = eps / bvps, "Schwab last-FY", None
        elif roe_e is not None:
            roe, basis, fallback_reason = roe_e, basis_e, eps_why
        else:
            blocked.append((tk, f"{eps_why}; and EDGAR cannot substitute "
                                f"(no net income or non-positive equity)"))
            continue
        lm = VA.line_map(fin)
        assets = lm.get(VA.L_ASSETS, {}).get("value")
        # Earnings are derived BACK OUT OF the selected ROE rather than from eps,
        # so the DuPont decomposition stays on the same basis as the ROE above it.
        # Computing it from eps directly would silently mix a Schwab-TTM
        # numerator into an EDGAR-based row.
        ni_basis = roe * be
        roa = (ni_basis / assets) if assets else None
        lev = (assets / be) if assets else None
        ni_ttm = ni_basis
        recs.append(dict(tk=tk, be=be, sh=sh, bvps=bvps, px=px, mb=mb,
                         eps=eps, roe=roe, dy=q.get("divYield"),
                         basis=basis, fallback_reason=fallback_reason,
                         roe_edgar=roe_e, basis_edgar=basis_e,
                         roe_schwab=(eps / bvps) if ok_eps else None,
                         qpx=q.get("lastPrice"), pe=q.get("peRatio"),
                         anchor=fin.get("period"), be_src=be_src, fp=fin.get("fp"),
                         assets=assets, roa=roa, lev=lev, ni_ttm=ni_ttm,
                         ebit=lm.get("Operating income", {}).get("value"),
                         ltd=lm.get("Long-term debt", {}).get("value"),
                         cash=lm.get("Cash and equivalents", {}).get("value")))

    # ---- 1. the inputs, stated before anything is derived from them
    out("-" * 100)
    out("1. INPUTS -- ROE is trailing eps over book value per share")
    out("-" * 100)
    out(f"{'tk':>6} {'anchor':>11} {'BVPS':>9} {'px(master)':>11} {'drift':>7} "
        f"{'ROE':>8} {'M/B':>7} {'divY%':>6}  {'anc.age':>7} {'num.age':>7}  ROE basis")
    for r in recs:
        drift = (r["qpx"] / r["px"] - 1) * 100 if r["qpx"] and r["px"] else float("nan")
        a_age, n_age = roe_vintage(r, cohort_date)
        out(f"{r['tk']:>6} {str(r['anchor']):>11} {r['bvps']:9,.2f} {r['px']:11,.2f} "
            f"{drift:+6.2f}% {r['roe']*100:7.2f}% {r['mb']:7.2f} "
            f"{(r['dy'] if r['dy'] is not None else float('nan')):6.2f}  "
            f"{_q(a_age):>7} {_q(n_age):>7}  {r['basis']}")
    out()
    out("  BASIS VINTAGE (DP-3C-aq, RULED 2026-09-25) -- ages in QUARTERS at the run date.")
    out("  anc.age: the balance-sheet anchor (BVPS). num.age: the END of the period the")
    out("  ROE NUMERATOR covers -- the last fiscal year for 'Schwab last-FY' (fp Q1/Q2/Q3")
    out("  puts that FY end 1/2/3 quarters before the anchor), the anchor quarter itself for")
    out("  'EDGAR quarterly x4'. A true TTM numerator would read num.age == anc.age; the gap")
    out("  is the staleness the deferred TTM rebuild removes. No figure above changes.")
    fb = [r for r in recs if r["basis"] != "Schwab last-FY"]
    if fb:
        out()
        out("  ROE FELL BACK TO EDGAR for:")
        for r in fb:
            out(f"     {r['tk']:>6} {r['basis']}")
            out(f"            because {r['fallback_reason']}")
    out()
    out(f"  computed {len(recs)}; blocked {len(blocked)}")
    for tk, why in blocked:
        out(f"     {tk:>6} NOT COMPUTED -- {why}")
    out()
    out("  px(quote) is shown as DRIFT ONLY. Every derived figure in sections 1-4b")
    out("  uses px(master), the record's Price at Signal.")
    out("  ONE DOCUMENTED EXCEPTION, stated here rather than left to be discovered:")
    out("  section 5's px/eps column uses px(QUOTE), deliberately, because it is")
    out("  compared against Schwab's own peRatio and that field is struck on")
    out("  Schwab's own price. Matching the price basis is what makes the ratio")
    out("  mean anything. CORRECTED 2026-08-21: this note previously read 'every")
    out("  derived figure uses px(master), so there is exactly one price source',")
    out("  which was false for section 5 and had been since the section was built.")
    zero_eps = [tk for tk, w in blocked if "exactly 0.0" in w]
    if zero_eps:
        findings.append(f"schwab_client defaults a missing `eps` to 0, so absent and "
                        f"zero are indistinguishable ({', '.join(zero_eps)})")
    out()

    # ---- 1a. the two ROE routes, cross-checked
    out("-" * 100)
    out("1a. THE TWO ROE ROUTES -- AND WHY THEIR AGREEMENT IS NOT EVIDENCE")
    out("-" * 100)
    out("  Schwab route: eps(last fiscal year) / BVPS.   EDGAR route: NI / equity.")
    out("  ★ THESE ARE NOT INDEPENDENT. value_anchor derives shares = NI/EPS_edgar, so")
    out("    ROE_schwab = eps_S x (NI/eps_E) / BE  and  ROE_edgar = NI/BE, whose ratio is")
    out("    exactly eps_S/eps_E. THE TWO ROUTES ARE ONE IDENTITY REACHED BY TWO PATHS and")
    out("    agree whenever the two eps figures coincide -- which for a 10-K filer they do")
    out("    BY CONSTRUCTION. A previous version of this tool read that agreement as")
    out("    validation. It was arithmetic. Retracted 2026-08-17.")
    out()
    out(f"{'tk':>6} {'fp':>4} {'Schwab lastFY':>13} {'EDGAR':>11} {'gap pt':>8}  basis of the EDGAR figure")
    exact = []
    for r in sorted(recs, key=lambda x: x["tk"]):
        s, e = r["roe_schwab"], r["roe_edgar"]
        gap = (e - s) * 100 if (s is not None and e is not None) else None
        if gap is not None and abs(gap) < 0.005:
            exact.append(r["tk"])
        out(f"{r['tk']:>6} {str(r.get('fp') or ''):>4} "
            f"{(f'{s*100:.2f}%' if s is not None else 'n/a'):>11} "
            f"{(f'{e*100:.2f}%' if e is not None else 'n/a'):>11} "
            f"{(f'{gap:+.2f}' if gap is not None else 'n/a'):>8}  {r['basis_edgar'] or ''}")
    if exact:
        out()
        out(f"  {exact} agree exactly -- and that is EXPECTED, not informative. They are the")
        out("  10-K (FY) filers, for whom Schwab's last-fiscal-year eps IS the eps in the")
        out("  accession the share count was derived from, so the identity above collapses")
        out("  to 1. Agreement here carries no evidential weight whatsoever.")
    out()
    out("  Elsewhere the gap is the two DIFFERENT WRONG PERIODS disagreeing: the EDGAR side")
    out("  is one quarter x4, the Schwab side is a fiscal year up to four quarters stale.")
    out("  NEITHER IS TRAILING-TWELVE-MONTH.")
    out()
    out("  ★ VERIFIED AGAINST AN EXTERNAL SOURCE 2026-08-17. Schwab reports GM eps 3.27;")
    out("  GM's FY2025 10-K diluted EPS is 3.27 exactly. True TTM rebuilt from GM's own")
    out("  XBRL (FY2025 - H1 2025 + H1 2026 = 3.27 - 5.29 + 4.25) is 2.23, giving ROE")
    out("  3.33% against Morningstar's independently published 3.28%. So GM reads 4.88%")
    out("  in this table against a true TTM near 3.33% -- a 1.5x OVERSTATEMENT, and every")
    out("  figure downstream of ROE inherits it.")
    out("  AMENDED 2026-09-16: the old blocker ('the cache holds one accession per filer')")
    out("  does not hold -- financials come from companyfacts, which carries the full period")
    out("  history (review 2026-09-08 §10.1). The TTM rebuild is DEFERRED, not blocked: it")
    out("  changes every cached extract (EXTRACT_SCHEMA bump) and lands on its own, with a")
    out("  GM before/after. Until then this overstatement stands and is labelled.")
    out()

    # ---- 1b. DuPont: how much of ROE is operating return and how much is leverage
    out("-" * 100)
    out("1b. DUPONT -- ROE = ROA x (Assets/Equity)   [packet p.1069]")
    out("-" * 100)
    out("  ROE IS A LEVERED MEASURE. Two firms with identical operations and different")
    out("  balance sheets report different ROE, so every implied figure in sections 3, 4")
    out("  and 4b is an implied LEVERED return. This decomposition says how much of each")
    out("  name's ROE is operating performance and how much is simply borrowing.")
    out()
    # RELABELLED 2026-09-16 (DP-3C-al). The column was headed "leverage share of
    # ROE", but 1 - 1/(A/E) = 1 - E/A is simply liabilities (incl. NCI) over
    # assets -- the debt ratio -- and "share of ROE" means nothing for a name
    # with negative ROE. Same number, honest name.
    out(f"{'tk':>6} {'ROE':>9} {'=':>2} {'ROA':>9} {'x':>2} {'A/E':>7}   {'liabilities/assets':>22}")
    dup = [r for r in recs if r["roa"] is not None]
    for r in sorted(dup, key=lambda x: -x["lev"]):
        share = (1.0 - 1.0 / r["lev"]) * 100      # 1 - E/A: the debt ratio
        out(f"{r['tk']:>6} {r['roe']*100:8.2f}% {'=':>2} {r['roa']*100:8.2f}% {'x':>2} "
            f"{r['lev']:7.2f}   {share:21.1f}%")
    if dup:
        hi = max(dup, key=lambda x: x["lev"]); lo = min(dup, key=lambda x: x["lev"])
        out()
        out(f"  Leverage multiplier spans {lo['lev']:.2f}x ({lo['tk']}) to "
            f"{hi['lev']:.2f}x ({hi['tk']}) -- a {hi['lev']/lo['lev']:.1f}x range.")
        out("  The identity ROE/ROA == A/E is exact, so this is a decomposition, not a model.")
        out("  'liabilities/assets' is 1 - E/A (the debt ratio). It is NOT a share of ROE.")
        out("  READ SECTIONS 3-4b THROUGH IT: an implied ROE of 18% at 13x leverage and one")
        out("  at 1.3x are not the same claim about a business.")
    out()

    # ---- 1c. why ROIC is NOT reported, stated as an inventory rather than a shrug
    out("-" * 100)
    out("1c. WHY ROIC IS NOT REPORTED -- what it would actually cost")
    out("-" * 100)
    out("  ROIC = NOPAT / invested capital is the right measure for an operating company,")
    out("  exactly because it strips out the leverage 1b just exposed. It is NOT computed")
    out("  here, and the reason is an input inventory rather than a design preference.")
    out()
    out("  NOPAT = EBIT(1-T) needs a tax rate. It CANNOT be derived from what is extracted:")
    out("  setting (1-T) = NetIncome/EBIT makes NOPAT identically equal to net income, which")
    out("  is circular. A genuine rate needs `IncomeTaxExpenseBenefit` and pretax income --")
    out("  both FLOW concepts, so both vote in edgar_client's anchor-period election and")
    out("  can change which period every other line reports.")
    out()
    out("  Invested capital is the binding constraint, and it is worse than the tax rate:")
    out(f"{'tk':>6} {'EBIT':>12} {'LT debt':>12} {'Cash':>12}  invested capital")
    n_ic = 0
    for r in sorted(recs, key=lambda x: x["tk"]):
        have = all(v is not None for v in (r["ebit"], r["ltd"], r["cash"]))
        n_ic += 1 if have else 0
        miss = [n for n, v in (("EBIT", r["ebit"]), ("LT debt", r["ltd"]),
                               ("Cash", r["cash"])) if v is None]
        out(f"{r['tk']:>6} {VA.money(r['ebit']):>12} {VA.money(r['ltd']):>12} "
            f"{VA.money(r['cash']):>12}  "
            f"{'computable (short-term debt still absent)' if have else 'BLOCKED: no ' + ', '.join(miss)}")
    out()
    out(f"  Even a crude capital base is assemblable for only {n_ic} of {len(recs)} names.")
    out("  `Long-term debt` is absent for most -- not a bug: DOW's was fossilised at")
    out("  2024-12-31 and the staleness rule correctly dropped it, and a filer that tags")
    out("  no `LongTermDebtNoncurrent` at the anchor period contributes nothing.")
    out("  JPM has no `Operating income` at all, which is correct -- a bank has no")
    out("  operating-income line in that sense, and ROIC is not defined for one either.")
    out()
    out("  SO: after-tax ROIC needs 3 new concepts (short-term debt, tax expense, pretax")
    out("  income), two of them on the hazardous flow side, AND it would still read for")
    out(f"  roughly {n_ic} names. DuPont above answers most of the same question at zero cost.")
    out()

    # ---- 2. sensitivity FIRST, so no one reads (I) without it
    out("-" * 100)
    out("2. IS THE EQUATION INFORMATIVE FOR THIS NAME?  d r_s / d g = 1 + (ROE-1)/(M/B)")
    out("-" * 100)
    out("  Read this BEFORE section 3. Where the derivative approaches 1, equation (I)")
    out("  returns the g you assumed and tells you nothing about the market.")
    out(f"{'tk':>6} {'M/B':>7} {'ROE':>8} {'dr_s/dg':>9}  verdict")
    inform = []
    for r in sorted(recs, key=lambda x: drs_dg(x["roe"], x["mb"])):
        d = drs_dg(r["roe"], r["mb"])
        if d < DRDG_INFORMATIVE:
            v = "INFORMATIVE -- price constrains r_s"; inform.append(r["tk"])
        elif d > DRDG_UNINFORMATIVE:
            v = "UNINFORMATIVE -- (I) mostly returns g"
        else:
            v = "weak"
        out(f"{r['tk']:>6} {r['mb']:7.2f} {r['roe']*100:7.2f}% {d:9.4f}  {v}")
    out()
    out(f"  informative under (I): {len(inform)} of {len(recs)}  {inform}")
    out("  This is why section 4's reverse read (II) is the headline: it is defined")
    out("  and interpretable at every M/B, and it does not degenerate.")
    out()

    # ---- 3. forward read (I)
    out("-" * 100)
    out("3. (I) IMPLIED COST OF EQUITY at the ROE actually earned")
    out("-" * 100)
    hdr = "".join(f"{'g='+format(g,'.0%'):>9}" for g in G_GRID)
    out(f"{'tk':>6}{hdr}   {'dividend route, g=3%':>21}  {'gap':>7}")
    for r in recs:
        # (I) IS SUPPRESSED WHERE TRAILING ROE <= 0. The formula still returns a
        # number -- DOW produced -11.26% on the first run -- and a negative cost
        # of equity in a table reads as a computed result. It is not one. Same
        # treatment as M/B on non-positive book equity in value_anchor.py.
        neg_roe = r["roe"] <= 0
        cells = ""
        for g in G_GRID:
            v = None if neg_roe else r_s_implied(r["roe"], r["mb"], g)
            cells += f"{v*100:8.2f}%" if v is not None else f"{'n/a':>9}"
        dv = None if r["dy"] in (0, None) else r_s_dividend(r["dy"], 0.03)
        base = None if neg_roe else r_s_implied(r["roe"], r["mb"], 0.03)
        gap = (base - dv) * 100 if (dv is not None and base is not None) else None
        out(f"{r['tk']:>6}{cells}   "
            f"{(f'{dv*100:.2f}%' if dv is not None else 'n/a'):>20}"
            f"  {(f'{gap:+.2f}' if gap is not None else 'n/a'):>7}")
    out()
    supp = [r["tk"] for r in recs if r["roe"] <= 0]
    if supp:
        out(f"  (I) SUPPRESSED for {supp} -- trailing ROE is negative, so the equation")
        out("  returns a negative cost of equity. That is not a computed result and is not")
        out("  printed as one. Read (II) and (III) for those names instead.")
        out()
    out("  DIVIDEND ROUTE is the packet's p.1072 expected return, r_s = D0(1+g)/P0 + g.")
    out("  IT IS EXPECTED TO UNDERSTATE, AND SYSTEMATICALLY: it assumes dividends are")
    out("  the only distribution. A firm returning capital mainly through buybacks")
    # FIXED 2026-09-16: the yield was hardcoded (0.35%) and had gone stale
    # against the table above it (0.32%). It is read from the same record now.
    _aapl = next((r for r in recs if r["tk"] == "AAPL" and r.get("dy")), None)
    # divYield is a PERCENT as schwab_client returns it (see r_s_dividend).
    _aapl_txt = (f"AAPL at a {_aapl['dy']:.2f}% yield" if _aapl
                 else "a low-yield buyback name")
    out(f"  reads low by construction -- {_aapl_txt} is the clear case. The")
    out("  gap column is therefore a buyback-intensity signal as much as a")
    out("  disagreement, and it is NOT evidence that either route is wrong.")
    amb_div = [r["tk"] for r in recs if r["dy"] in (0, None)]
    if amb_div:
        out(f"  divYield is 0 or absent for {amb_div} -- schwab_client defaults a missing")
        out("  divYield to 0 as well, so 'pays nothing' and 'field absent' are the same")
        out("  value here. The dividend route is NOT read for those names.")
    out()

    # ---- 4. the headline: reverse read (II)
    out("-" * 100)
    out("4. (II) WHAT ROE MUST THE MARKET BELIEVE?   <-- the headline read")
    out("-" * 100)
    out("  Defined at every M/B > 0, including where trailing ROE is negative.")
    out(f"{'tk':>6} {'M/B':>7} {'ROE trail':>10}" +
        "".join(f"{'r_s='+format(rs,'.0%'):>11}" for rs in RS_GRID) +
        f"   {'implied/trailing @9%':>21}")
    for r in sorted(recs, key=lambda x: -x["mb"]):
        cells = ""
        for rs in RS_GRID:
            v = roe_implied(rs, r["mb"], 0.03)
            cells += f"{v*100:10.2f}%" if v is not None else "       n/a "
        ref = roe_implied(0.09, r["mb"], 0.03)
        mult = (ref / r["roe"]) if (ref is not None and r["roe"] > 0) else None
        ms = f"{mult:20.2f}x" if mult else f"{'n/a':>21}"
        out(f"{r['tk']:>6} {r['mb']:7.2f} {r['roe']*100:9.2f}%{cells}   {ms}")
    out()
    out("  All at g = 3%. The last column is the implied ROE at a 9% cost of equity")
    out("  divided by the ROE actually earned -- how large a change in profitability")
    out("  the current price requires. A figure near 1.0x means the price is roughly")
    out("  consistent with what the company already earns.")
    out()
    stretch = [r for r in sorted(recs, key=lambda x: -x["mb"])
               if r["roe"] > 0 and (roe_implied(0.09, r["mb"], 0.03) or 0) / r["roe"] > 2.0]
    if stretch:
        out(f"  Price requires MORE THAN A DOUBLING of trailing ROE: "
            f"{[r['tk'] for r in stretch]}")
    cheap = [r for r in recs if r["roe"] > 0
             and (roe_implied(0.09, r["mb"], 0.03) or 0) / r["roe"] < 0.75]
    if cheap:
        out(f"  Price requires LESS than trailing ROE (market discounts current "
            f"profitability): {[r['tk'] for r in cheap]}")
    neg = [r["tk"] for r in recs if r["roe"] <= 0]
    if neg:
        out(f"  Trailing ROE is negative for {neg} -- (I) is undefined, (II) still reads,")
        out("  and the implied figure is the swing in profitability the price embeds.")
    out()

    # ---- 4b. the third rearrangement, and which read to trust
    out("-" * 100)
    out("4b. (III) WHAT GROWTH MUST THE MARKET BELIEVE?  g = (M/B*r_s - ROE)/(M/B + ROE - 1)")
    out("-" * 100)
    out("  The denominator is M/B * (dr_s/dg), so (III) is well determined EXACTLY where")
    out("  (I) degenerates. High M/B: trust g. Low M/B: trust r_s. Same equation, and")
    out("  which read is trustworthy is decided by section 2's derivative, not by taste.")
    out(f"{'tk':>6} {'M/B':>7} {'dr_s/dg':>8} {'r_s(I) g=3%':>12} "
        f"{'g(III) r_s=9%':>14}  TRUST")
    for r in sorted(recs, key=lambda x: -x["mb"]):
        d = drs_dg(r["roe"], r["mb"])
        rs_i = None if r["roe"] <= 0 else r_s_implied(r["roe"], r["mb"], 0.03)
        g_i = g_implied(r["roe"], r["mb"], 0.09)
        trust = "g (III)" if d > DRDG_UNINFORMATIVE else (
            "r_s (I)" if d < DRDG_INFORMATIVE else "neither cleanly")
        out(f"{r['tk']:>6} {r['mb']:7.2f} {d:8.4f} "
            f"{(f'{rs_i*100:.2f}%' if rs_i is not None else 'n/a'):>12} "
            f"{(f'{g_i*100:.2f}%' if g_i is not None else 'NO CONVERGENT g'):>14}  {trust}")
    out()
    nc = [r["tk"] for r in recs if g_implied(r["roe"], r["mb"], 0.09) is None]
    if nc:
        out(f"  NO CONVERGENT g at r_s = 9% for {nc}.")
        out("  This is a RESULT, not a gap. It means the constant-growth model cannot")
        out("  reconcile that name's price, its trailing ROE and a 9% cost of equity at")
        out("  ANY growth rate below 9% -- the price requires either a lower discount")
        out("  rate or a recovery in ROE that the trailing figure does not contain.")
        out("  For a name earning less than its cost of capital yet trading above book,")
        out("  that is the expected and correct answer.")
    out()

    # ---- 5. the peRatio finding
    out("-" * 100)
    out("5. `peRatio` IS SCHWAB'S 12-MONTH P/E -- settled 2026-10-24 (was [?]); still not an input")
    out("-" * 100)
    out("  (M/B)/(P/E) is algebraically identical to eps/BVPS, so it should give the")
    out("  same ROE. It does not, and the discrepancy is not a constant factor:")
    out(f"{'tk':>6} {'px/eps':>9} {'peRatio':>9} {'ratio':>7}  {'reading'}")
    for r in sorted(recs, key=lambda x: (x['pe'] or 0) / ((x['qpx'] or 1) / x['eps'])
                    if x['pe'] and x['eps'] else 0):
        if not r["pe"] or not r["eps"] or not r["qpx"]:
            continue
        trail = r["qpx"] / r["eps"]
        ratio = r["pe"] / trail
        # relabelled 2026-10-24: peRatio is TRAILING 12-month (see the SETTLED note)
        rd = ("12-month EPS above last-FY: earnings have RISEN" if ratio < 0.97
              else "12-month EPS below last-FY: earnings have FALLEN" if ratio > 1.03 else "flat")
        out(f"{r['tk']:>6} {trail:9.2f} {r['pe']:9.2f} {ratio:7.3f}  {rd}")
    # Derived from the table above rather than written into the prose. The first
    # draft hardcoded the name list from an earlier analysis and included PM,
    # which is blocked here for non-positive equity and so never appears in the
    # table -- prose citing a row the reader cannot see is the same class of
    # defect as a stale threshold quoted from memory.
    dearer = [r["tk"] for r in recs
              if r["pe"] and r["eps"] and r["qpx"]
              and r["pe"] / (r["qpx"] / r["eps"]) > 1.03]
    out()
    out("  SETTLED 2026-10-24: price / peRatio equals the SEC 12-month diluted EPS within")
    out("  about 1% on AAPL, JPM, MSFT, NVDA, PM, PWR, SND and WMT, and lags it only where a")
    out("  10-Q landed that week (GM, DOW). peRatio is TRAILING TWELVE MONTHS; `eps` is the")
    out("  last fiscal year. A row above says how far the last 12 months have moved from the")
    out("  last fiscal year: earnings that HAVE changed, not an expectation. The value card's")
    out("  class reads 12-month ROE from SEC filings since DP-V4 (2026-10-24).")
    out("  THE RECORD BELOW (2026-08-17 .. 08-21) IS KEPT AS WRITTEN. Its 'peRatio is")
    out("  FORWARD' reading is SUPERSEDED; 'expected UP/DOWN' there means risen/fallen.")
    out()
    out("  Every name reading 'expected UP' is a grower; the 'expected DOWN' set is")
    out(f"  {dearer} -- and GM's own XBRL block shows operating income -31.4% YoY")
    out("  while DOW is loss-making. The coherent reading is that `eps` is TRAILING")
    out("  and `peRatio` is FORWARD.")
    out("  MARKED [?]: schwab_client documents neither field. What would settle it is")
    out("  Schwab's API reference for the `fundamental` block. Until then peRatio is")
    out("  NOT used as a trailing input, because doing so would mix an analyst")
    out("  forecast into an instrument whose whole claim is that it makes none.")
    out()
    out("  EMPIRICAL CONFIRMATION 2026-08-21 -- a natural experiment, not a new claim.")
    out("  WMT filed an 8-K on 2026-08-20. Across quote_dump 8/20 -> 8/21 the `eps`")
    out("  field did NOT move (2.73 on 8/18, 8/20 and 8/21) and the price moved")
    out("  -0.37% (103.97 -> 103.59), while `peRatio` moved -9.16% (40.237 ->")
    out("  36.555). Backing the denominator out as px/peRatio gives an implied")
    out("  earnings figure of 2.5839 -> 2.8338, +9.67%. Across the whole cohort the")
    out("  next largest move in a POSITIVE implied denominator that session was NKE")
    out("  at +3.35%, and most names sat inside +/-1.5%. A denominator that revises")
    out("  ~10% the session after a filer's own earnings event, while `eps` holds")
    out("  still, is not the same measure as `eps` and is not price/eps.")
    out("  SO: the 'eps TRAILING, peRatio FORWARD' reading above is confirmed on a")
    out("  live event. THE [?] IS THE OPERATOR'S TO CLOSE -- it is left standing")
    out("  because the marker's own stated resolution was Schwab's field reference")
    out("  and that document has still not been read.")
    out("  AND A CONSEQUENCE FOR HOW THIS TABLE IS READ: the classification is a")
    out("  property of DENOMINATOR FRESHNESS, not of a company. WMT sat in the")
    out("  'expected DOWN' set on 2026-08-20 at ratio 1.057 and in the 'expected UP'")
    out("  set on 2026-08-21 at 0.963, on a -0.4% price move, purely because the")
    out("  forward denominator was revised. Reading a row here as a statement about")
    out("  a business is a category error; it is a statement about how stale the")
    out("  two fields are RELATIVE TO EACH OTHER on the day they were captured.")
    findings.append("peRatio is Schwab's trailing 12-month P/E and eps its last fiscal year "
                    "(settled 2026-10-24); peRatio stays outside this exhibit's ROE")
    findings.append("NEITHER ROE basis is trailing-twelve-month: Schwab's eps is the last "
                    "fiscal year (verified = GM's FY2025 10-K EPS 3.27) and the EDGAR "
                    "route is one quarter x4. GM reads 4.88% against a true TTM ~3.33% "
                    "(Morningstar 3.28%) -- a 1.5x overstatement inherited by everything "
                    "downstream of ROE. RESOLVED for the value card's class by DP-V4 "
                    "(2026-10-24): it reads 12-month ROE from SEC filings; this exhibit's "
                    "own ROE stays last-FY")
    out()

    # ---- 6. exclusions, classified by REASON -- they are not one category
    out("-" * 100)
    out("6. WHO IS EXCLUDED, AND WHY -- three different reasons, three different remedies")
    out("-" * 100)
    struct, defect, scope = [], [], []
    for tk, why in blocked:
        if "ETF" in why or "missing Diluted EPS" in why:
            struct.append((tk, why))
        elif "exactly 0.0" in why:
            defect.append((tk, why))
        else:
            scope.append((tk, why))
    out("  (a) STRUCTURAL -- the model does not apply. PERMANENT, and not a data gap.")
    for tk, _w in struct:
        out(f"        {tk}")
    out("      A passive fund or trust has no earnings in the corporate sense and its")
    out("      market-to-book is ~1.0 BY CONSTRUCTION, because the trust IS its net asset")
    out("      value. ROE is undefined conceptually, not merely missing. Adding concepts")
    out("      would not help. EXCLUDE FROM THE VALUATION LAYER ONLY -- these names stay")
    out("      in the signal pipeline, the accuracy series, KEEP-70, H4 and E4 exactly as")
    out("      they are. That distinction is the DP-3C-k precedent: an exclusion scoped to")
    out("      one endpoint must not silently move another criterion's denominator.")
    out()
    out("  (b) DATA DEFECT -- fixable, and NOT a reason to exclude the name.")
    if not defect:
        out("        none this session -- every name with an unreliable eps fell back")
        out("        to the EDGAR route rather than being excluded, which is the point")
        out("        of having a fallback.")
    for tk, _w in defect:
        out(f"        {tk}")
    if defect:
        out("      schwab_client.py L131 reads fundamental.get('eps', 0), so a MISSING")
        out("      fundamental becomes 0.0 and is indistinguishable from a real zero.")
        out("      The one-line fix is .get('eps') with no default, so absent becomes None.")
        out("      BUT claude_signal.py L162 renders eps into the prompt, so today a name")
        out("      with an absent EPS is being TOLD 'EPS: $0'. Changing that changes what")
        out("      the model receives, mid-E4. THE TIMING IS A RULING, NOT A BUILD CHOICE.")
        out("      Flagged rather than fixed here for exactly that reason.")
    out()
    out("  (c) SCOPE -- genuine operating companies excluded by the filing set.")
    out("      RULED 2026-09-16 (DP-3C-ai): no change to the filing set through the")
    out("      Phase 3-C exit; changing it mid-E4 would change what the treatment arm sees.")
    covered_now = set(verified) | {t for t, _ in blocked}
    foreign = [t for t in ("AG", "NTR") if t in watchlist and t not in covered_now]
    for tk in foreign:
        out(f"        {tk}  40-F/6-K foreign private issuer, outside the 3-C filing set")
    if foreign:
        out("      DP-3C-f is ruled 'no change' through the exit (DP-3C-ai). Its cost-benefit")
        out(f"      moves now that a valuation layer exists: these are {len(foreign)} operating")
        out(f"      companies against a valuation base of {len(recs)}, so extending the filing")
        out(f"      set would widen it by roughly {100*len(foreign)/max(len(recs),1):.0f}%. Recorded, not argued for.")
    out()
    out("  NONE of (a), (b) or (c) is a reason to drop a name from the watchlist, the")
    out("  signal pipeline or any existing criterion. They bound THIS instrument only.")
    out()

    out("=" * 100)
    if findings:
        out(f"FINDINGS: {len(findings)}")
        for f in findings:
            out(f"  - {f}")
    else:
        out("FINDINGS: none")
    out("=" * 100)
    out("No valuation asserted. No price target implied. One assumption (g), reported")
    out("as a grid rather than a choice. Advisory-only - no orders - not financial advice.")

    if md_path:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write("# implied_return exhibit\n\n```\n" + "\n".join(L) + "\n```\n")
        print(f"\n[wrote {md_path}]")
    return 1 if findings else 0


# =============================================================================
# SELF-TESTS
# =============================================================================

def _check(name, got, want, tol=None):
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")
    return ok


def selftest():
    print("implied_return.py self-tests")
    ok = True

    print("\n (I) and (II) are INVERSES of one another -- round trip")
    for roe, mb, g in ((0.15, 2.15, 0.05), (0.0488, 1.2837, 0.03),
                       (1.023, 41.73, 0.02), (0.08, 1.0, 0.00)):
        rs = r_s_implied(roe, mb, g)
        back = roe_implied(rs, mb, g)
        ok &= _check(f"roe->r_s->roe at M/B={mb}", back, roe, 1e-12)

    print("\n the packet's own worked relation: M/B from ROIC/WACC/g")
    # ROIC 15%, WACC 10%, g 5% -> MVA/OpCap 1.15 -> M/B 2.15 (verified symbolically
    # in the scoping memo). The equity-side form must reproduce r_s = WACC here.
    ok &= _check("r_s recovered from M/B=2.15", r_s_implied(0.15, 2.15, 0.05), 0.10, 1e-12)

    print("\n M/B == 1 means the market pays exactly book")
    # At M/B = 1 the identity collapses to r_s = (1+g)*ROE
    for roe, g in ((0.10, 0.03), (0.08, 0.00), (0.20, 0.04)):
        ok &= _check(f"M/B=1 -> r_s=(1+g)ROE  (ROE={roe},g={g})",
                     r_s_implied(roe, 1.0, g), (1 + g) * roe, 1e-15)

    print("\n analytic derivative matches a numerical difference")
    for roe, mb in ((0.0488, 1.2837), (1.023, 41.73), (0.15, 2.15)):
        h = 1e-7
        num = (r_s_implied(roe, mb, 0.03 + h) - r_s_implied(roe, mb, 0.03 - h)) / (2 * h)
        ok &= _check(f"drs_dg analytic == numeric at M/B={mb}",
                     drs_dg(roe, mb), num, 1e-6)
    print("  and the degeneration is real, not rhetorical:")
    ok &= _check("dr_s/dg -> ~1 at high M/B", round(drs_dg(1.023, 41.73), 3), 1.001)
    ok &= _check("dr_s/dg is small at low M/B", drs_dg(0.0488, 1.2837) < 0.3, True)
    ok &= _check("dr_s/dg == 1 exactly when ROE == 100%", drs_dg(1.0, 7.5), 1.0, 1e-15)

    print("\n NEGATIVE TESTS -- guards shown to fire")
    ok &= _check("(I) undefined at M/B <= 0", r_s_implied(0.1, -1.3, 0.03), None)
    ok &= _check("(I) undefined at M/B == 0", r_s_implied(0.1, 0.0, 0.03), None)
    ok &= _check("(II) undefined at M/B <= 0", roe_implied(0.09, -1.3, 0.03), None)
    ok &= _check("(II) REFUSES non-convergent g >= r_s", roe_implied(0.03, 1.5, 0.03), None)
    ok &= _check("(II) refuses g > r_s", roe_implied(0.03, 1.5, 0.05), None)
    ok &= _check("drs_dg undefined at M/B <= 0", drs_dg(0.1, 0.0), None)
    ok &= _check("dividend route needs a yield", r_s_dividend(None, 0.03), None)

    print("\n (II) works where (I) cannot -- the negative-trailing-ROE case (DOW)")
    ok &= _check("(I) is defined but meaningless on negative ROE",
                 r_s_implied(-0.175, 1.4728, 0.03) < 0, True)
    v = roe_implied(0.09, 1.4728, 0.03)
    ok &= _check("(II) still returns a positive implied ROE", v > 0, True)
    ok &= _check("(II) DOW implied ROE at r_s=9%, g=3%", round(v * 100, 2), 11.49)
    print("  DOW trails at -17.5% ROE and its price implies +11.49%. That swing IS")
    print("  the output; it is not a defect and not a valuation.")

    print("\n (III) implied growth -- the third rearrangement, and it round trips")
    for roe, mb, rs in ((1.0232, 41.73, 0.09), (0.3023, 8.13, 0.09),
                        (0.1468, 2.67, 0.09)):
        g = g_implied(roe, mb, rs)
        ok &= _check(f"g->r_s->g at M/B={mb}", r_s_implied(roe, mb, g), rs, 1e-12)
    ok &= _check("AAPL implied g at r_s=9%",
                 round(g_implied(1.0232, 41.73, 0.09) * 100, 2), 6.54)
    print("  and the packet's own expansion must agree: M/B == [(1+g)ROE - g]/(r_s - g)")
    for roe, mb, g in ((0.15, 2.15, 0.05), (0.3023, 8.13, 0.03)):
        rs = r_s_implied(roe, mb, g)
        ok &= _check(f"M/B reproduced at M/B={mb}",
                     ((1 + g) * roe - g) / (rs - g), mb, 1e-9)
    print("\n (III) refuses to emit a non-convergent growth rate")
    # GM: ROE 4.88% well below r_s 9% yet M/B 1.28 -> requires g > r_s
    ok &= _check("GM has NO convergent g at r_s=9%",
                 g_implied(0.0488, 1.2836, 0.09), None)
    ok &= _check("...and that is a result, reachable at a lower r_s",
                 g_implied(0.0488, 1.2836, 0.045) is not None, True)
    ok &= _check("(III) undefined at M/B <= 0", g_implied(0.1, -1.0, 0.09), None)
    print("  (III)'s denominator is M/B * dr_s/dg -- the complementarity, asserted:")
    for roe, mb in ((1.0232, 41.73), (0.0488, 1.2836)):
        ok &= _check(f"denominator == M/B*drs_dg at M/B={mb}",
                     mb + roe - 1.0, mb * drs_dg(roe, mb), 1e-9)

    print("\n dividend route, packet p.1072  r_s = D0(1+g)/P0 + g")
    ok &= _check("PM 3.11% yield at g=3%", round(r_s_dividend(3.11, 0.03) * 100, 4),
                 round((0.0311 * 1.03 + 0.03) * 100, 4))
    ok &= _check("zero yield -> r_s == g", r_s_dividend(0.0, 0.04), 0.04, 1e-15)
    print("  A zero-yield name returns exactly g, which is why a 0/absent divYield")
    print("  must be excluded rather than read as 6.20%-style output.")

    print("\n GM end-to-end, from the record's own figures")
    be, sh, px, eps = 62e9, 925.5e6, 85.99, 3.27
    bvps = be / sh
    mb = px / bvps
    roe = eps / bvps
    ok &= _check("GM BVPS", round(bvps, 2), 66.99)
    # 85.99 / (62e9/925.5e6) = 85.99 / 66.99081... = 1.283605...
    # The scoping work quoted 1.2837; the fourth decimal there was a rounding
    # slip in the note, not in the arithmetic. Recorded rather than quietly
    # corrected, because "compute rather than recall" applies to my own figures.
    ok &= _check("GM M/B", round(mb, 4), 1.2836)
    ok &= _check("GM trailing ROE", round(roe * 100, 2), 4.88)
    ok &= _check("GM r_s implied at g=3%", round(r_s_implied(roe, mb, 0.03) * 100, 2), 4.58)
    ok &= _check("GM ROE the market must believe at r_s=9%",
                 round(roe_implied(0.09, mb, 0.03) * 100, 2), 10.39)
    print("  GM earns 4.88% and its price at a 9% cost of equity implies 10.39% --")
    print("  the market prices roughly a doubling. That is the deliverable.")

    print("\n DuPont is an IDENTITY, not a model: ROE/ROA must equal A/E exactly")
    for ni, be, assets in ((1e9, 5e9, 20e9), (21.155e9, 374.598e9, 5.015e12),
                           (-533e6, 15.249e9, 59.78e9)):
        roe, roa, lev = ni / be, ni / assets, assets / be
        ok &= _check(f"ROE/ROA == A/E at A={assets:.3g}", roe / roa, lev, 1e-9)
        ok &= _check(f"ROA*lev == ROE at A={assets:.3g}", roa * lev, roe, 1e-12)
    print("  holds on negative net income too -- the identity does not care about sign.")

    print("\n the tax rate CANNOT be backed out of what is extracted")
    ebit, ni = 1459e6, 1305e6
    implied_keep = ni / ebit
    ok &= _check("NOPAT via (1-T)=NI/EBIT collapses to net income",
                 ebit * implied_keep, ni, 1e-6)
    print("  That is circular, which is the whole reason ROIC needs the tax concepts")
    print("  rather than an arithmetic trick. Asserted so the shortcut is not retried.")

    print("\n quote-dump loading")
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"quotes": {}, "succeeded": 0, "requested": 26}, fh)
        p = fh.name
    d, e = load_quotes(p)
    ok &= _check("succeeded=0 is REFUSED, not read as empty", d, None)
    ok &= _check("...with the token cause named", "OAuth" in (e or ""), True)
    os.unlink(p)
    d, e = load_quotes("/nonexistent.json")
    ok &= _check("missing dump refused", d, None)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write("{not json")
        p = fh.name
    d, e = load_quotes(p)
    ok &= _check("malformed dump refused without raising", d, None)
    os.unlink(p)

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="Run the value-driver identity backwards: implied cost of "
                    "equity, and the ROE the market must believe. No price target.")
    ap.add_argument("--tracker", default=VA.DEFAULT_TRACKER)
    ap.add_argument("--cache", default=VA.DEFAULT_CACHE)
    ap.add_argument("--log", default=None)
    ap.add_argument("--quotes", default=DEFAULT_QUOTES)
    ap.add_argument("--md", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    log_path = a.log
    if log_path is None:
        import glob as _g
        c = sorted(_g.glob(os.path.join("logs", "signals_*.log")))
        log_path = c[-1] if c else None
    return report(a.tracker, a.cache, log_path, a.quotes, md_path=a.md)


if __name__ == "__main__":
    sys.exit(main())
