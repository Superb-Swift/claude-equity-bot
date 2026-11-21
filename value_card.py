#!/usr/bin/env python3
"""
value_card.py -- the valuation layer, organised around decisions and changes.

WHY (2026-10-14, claude/ValuePass_WhatItMeasures_2026-10-14.md)
    implied_return prints about 27 KB a day, and across the 29 dated exhibits
    from 2026-08-24 to 10-14, 14 of 15 headline classes never changed. Three
    findings explain why, and each section below answers one of them:

    1. THE CLASS IS A TRAILING-FISCAL-YEAR P/E. Book value cancels out of
       `implied/trailing @9%`:
           ratio = (P/EPS) * (r-g)/(1+g) + g/((1+g) ROE)  =  0.0583 * P/E + 0.0291/ROE
       Schwab's eps is the last fiscal year and does not move on a quarterly
       report, so the class moves only with price or a 10-K. Section 6 checks
       this identity every run and FLAGS it if the exhibit stops satisfying it.
    2. THE DAILY REPRINT HIDES THE DAYS THAT MATTER. Section 1 prints only
       what changed since the previous dated exhibit, and splits every ratio
       move into a PRICE part and a FILING part.
    3. THE CLASSES ARE FRAGILE. Neither ROE route is trailing-twelve-month.
       Section 3 re-derives every class under both routes and r = 7/9/11%,
       and calls a class ROBUST only if all six agree.

    Section 2 is the decision card the 2026-08-24 DP-V2 memo specified as
    stage 1 and the 2026-10-09 review ranked V1. Section 4 is DP-V2's
    counterfactual flip ledger: COUNTS ONLY, never an outcome.

DP-V4 (2026-10-24, claude/DP-V4_ValueCard_TTM_2026-10-24.md): THE CLASS
    READS 12-MONTH ROE. Finding 1 above was the defect: Schwab's last-FY eps
    is 1 to 4 quarters old (NVDA's 4.90 against 7.91 over the last 12 months),
    so the class could not hear a quarterly report. It is now
        implied ROE at 9% / (12-month net income / period-end equity)
    from sec_facts, POINT IN TIME: a class dated d reads only filings SEC had
    published by d (on or before d for the card; strictly before d for the
    DP-V2 ledger, whose BUY was decided that morning). The 2.00 / 1.50 lines,
    r = 9% and g = 3% are unchanged. Robustness is the r = 7/9/11% grid on that
    basis plus the distance to the nearest line; the last-FY class is printed
    beside it for reference. The DP-V2 ledger is REBUILT on the 12-month basis
    from 2026-08-24; the last-FY ledger is CLOSED and printed, never pooled.
    A name with no 12-month figure is NO READ, never a last-FY fallback.
    The card also opens the hood, one question per panel:
      2b  earnings direction, earnings quality, balance sheet (SEC facts)
      2c  expectations: the next report, Finnhub's ADJUSTED consensus and the
          last four surprises (earnings_calendar), and the class if the
          consensus is met (approximate; its own basis, never the class)

2b, 2026-10-29 (claude/UnderTheHood_GapAnalysis_2026-10-29.md, step 1): the
    cells the 10-28 sheet left blank for a reason it did not print. OCF/rev
    (operating cash flow / revenue) is defined through a loss, where OCF/NI is
    not; L/A (liabilities / assets) is defined when equity is negative, where
    L/E is not; the balance sheet opens on the latest assets date when there
    is no equity line (PAA's cash). The text card and the sheet share one note
    list (hood_notes) and one +/-300% cap. Display only: the class, its
    robustness and the DP-V2 ledger are unchanged.

DP-V7 step 2, 2026-11-18 (claude/DP-V7_Step2_CostOfEquity_2026-11-18.md): A
    COST OF EQUITY PER NAME, BESIDE THE 9% CLASS. The 9% is the SML rate of a
    beta-1.0 stock only when rRF + RPM = 9% (Ch 6 slide 59: 4% + 5%).
    cost_of_equity.py (value.bat step 7c) writes each name's CAPM r = rRF +
    adjusted beta x 5.0% (Rob, 2026-11-18). The card prints, CONTEXT ONLY:
      decision card  '@own r': the class at that r (* where it differs from 9%)
      2d             beta, r CAPM and its 95% CI; the course's second estimate,
                     dividend growth r = D1/P0 + g with g = (1 - payout) x ROE
                     (Ch 9 slides 21-28) on the class's own 12-month ROE, defined
                     only where g < the CAPM r (Ch 7 slide 62); and the class at
                     9%, at the beta-1.0 r (the rate LEVEL alone) and at own r
                     (level plus BETA), so the two effects read separately
      3              the class across own r -2 / own r / own r +2
    Own r is the CAPM r alone (the bar is in cost_of_equity.py's header). The
    headline class, its 7/9/11% robustness, the DP-V2 gate and its ledger are
    unchanged: moving the class off 9% is class-affecting and needs a ruling.
    A missing cost_of_equity_<date>.json prints 'not available', never a guess.

DP-V8, 2026-11-18 (Rob, 13:56 CT; claude/DP-V8_HeadlineRate_2026-11-18.md): THE
    HEADLINE CLASS READS r = rRF + RPM. rRF is the latest 10-year Treasury yield
    (FRED DGS10) dated BEFORE the card's session, from the series
    cost_of_equity.py caches in valuation_cache\\dgs10.json; RPM is 5.0% (DP-V7).
    The same rule serves every date, so the card and the rebuilt ledger read one
    rate. The 2.00 / 1.50 lines and g = 3% are unchanged; at r = 10.12% they are
    P/E lines of about 29 and 22 (34 and 26 at 9%). Robustness is the r -/+ 2
    grid around the headline r (7/9/11 when r was 9). The class at 9% is
    carried for reference (decision card '@9%', section 3, the sheet). Section
    1 splits a ratio move into PRICE, FILING and RATE. The DP-V2 ledger is
    REBUILT on this basis from 2026-08-24, point in time (each session's own
    yield, filings public before it, its own exhibit); the 12-month ledger at
    9% is CLOSED and printed, never pooled; DP-V2's bar and 12-31 stop are
    unchanged. No yield before the date -> every class NO READ, never a 9%
    fallback. Section 6 still checks implied_return's own 9% arithmetic.
    AMENDS DP-V7 step 2 above: '@beta-1' is now the headline itself, so panel
    2d prints @9%, the headline class and @own r.

DP-V7 step 3, 2026-11-18 (claude/DP-V7_Step3_CapitalCredit_2026-11-18.md):
    PANEL 2e, CAPITAL AND CREDIT -- two questions the card did not ask. CONTEXT
    ONLY: nothing in 2e enters the class, a gate or the prompt (DP-V1).
      credit  can operating profit carry the debt? EBIT / interest and EBITDA /
              interest (Ch 3 s.40-42); Altman Z and its zone (Web 24A, eq.
              24A-1); the ratings-median band, the WORSE of a return-on-capital
              band and a debt-to-capital band against S&P's medians (Ch 5 s.45),
              with its 5-year default rate (s.42)
      value   does it earn its cost of capital? WACC = w_d r_d (1 - T) + w_s r_s
              (Ch 9 s.40): r_d = rRF + the band's live spread (ICE BofA OAS),
              r_s = own CAPM r (2d), debt at book and equity at market (s.60),
              T = 25.5% marginal (DP-V6's statutory rate; 0 for a pass-through).
              ROIC - WACC and EVA = (ROIC - WACC) x capital (Ch 2 s.29-30); the
              growth hurdle WACC / (1 + WACC) (Ch 7 s.51)
      shares  the share-count part of EPS growth: (1 + NI y/y) / (1 + EPS y/y)
              - 1 (Brav 2005: buybacks raise EPS)
    Bars fixed in capital_read()'s docstring before the first live run.

DP-V10, 2026-11-18 (Rob, 15:20 CT; FINC 5133 step 5; claude/DP-V10_Step5_ImpliedMove_
    2026-11-18.md): PANEL 2f, the market-implied move. implied_vol.py (value.bat step 7d)
    reads one option chain per name; the card prints its ATM IV at the earliest expiry
    on or after the +5 session, the 5-day 1-sigma move, the band in sigma and the
    market's P(|move| > 3%), and flags a report between the session and that expiry.
    F-10 (same day): section 5 refuses a P/E below 1 (price and EPS on different share
    classes). Both are context: no class, gate, prompt or ledger reads them.

WHAT IT DOES NOT DO
    It reads no return, breach, hit or +Nd cell. It modifies no gate, admits
    and rejects nothing, touches no workbook, no prompt, no endpoint, no
    edgar_client extract. DP-V1 stands: nothing here reaches the model. The
    DP-V2 gate column is COUNTERFACTUAL and is never applied.

INPUTS
    implied_return_<date>.md   today's, plus every earlier dated exhibit found
                               in the root or exhibits\\archive (sections 1, 4)
    logs\\signals_<date>.log   signal, confidence, held/scout, per-account
    quote_dump.json            divYield and eps for the book-free reads (5)
    the MASTER                 BUY rows since 2026-08-24 for the ledger (4).
                               tracker_with_registry.xlsx is REFUSED.

USAGE
    python value_card.py --date 2026-10-14 --tracker logs\\claude_equity_bot_tracker.xlsx
           --log logs\\signals_2026-10-14.log --quotes quote_dump.json
           --md value_card_2026-10-14.md [--json value_card_2026-10-14.json]
    python value_card.py --selftest

EXIT  0 = exhibit written.  1 = written, with FINDINGS (identity check failed,
      or a parse anomaly).  2 = could not run (no exhibit for the date, report
      copy given as input, unreadable master or log). Nothing is written on 2.

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

R_GRID = (7.0, 9.0, 11.0)      # implied_return 4's own grid (its exhibit); the card's is r -/+ R_STEP (DP-V8)
R_BASE = 9.0                   # the class rate until DP-V8 (DP-V2 memo 3.1); now the reference
                               # rate: the '@9%' columns, the closed ledger and implied_return's own
                               # exhibit (section 6)
RPM_PCT = 5.0                  # DP-V7 (Rob, 2026-11-18); DP-V8: headline r = rRF + RPM
R_STEP = 2.0                   # DP-V8: the robustness grid is r -/+ 2 points (7/9/11 at r = 9)
RRF_SERIES = os.path.join("valuation_cache", "dgs10.json")   # written by cost_of_equity.py
RRF_STALE_DAYS = 7             # an rRF older than this before the date is a FINDING
# DP-V7 step 3 (2026-11-18): live spreads by rating band for r_d = rRF + spread.
# ICE BofA option-adjusted spreads on FRED; cost_of_equity.py caches them.
SPREADS = os.path.join("valuation_cache", "spreads.json")
SPREAD_SERIES = (("AAA", "BAMLC0A1CAAA"), ("AA", "BAMLC0A2CAA"), ("A", "BAMLC0A3CA"),
                 ("BBB", "BAMLC0A4CBBB"), ("BB", "BAMLH0A1HYBB"), ("B", "BAMLH0A2HYB"),
                 ("CCC", "BAMLH0A3HYC"))
G_BASE = 3.0                   # implied_return's g
DEMANDING_AT = 2.00            # DP-V2 memo 3.1, frozen at first run, never re-cut
NEUTRAL_AT = 1.50
DPV2_GATE = {"DEMANDING": 75, "NEUTRAL": 70, "UNDEMANDING": 65, "NO READ": 70}
DPV2_BASE_GATE = 70
DPV2_SINCE = dt.date(2026, 8, 24)      # first day the layer printed section 4
DPV2_STOP = dt.date(2026, 12, 31)      # DP-V2 memo 6: withdrawn, not extended
DPV2_MIN_ROWS, DPV2_MIN_TICKERS = 12, 3
INSTALLED = dt.date(2026, 10, 14)      # rows on or before this are BACKFILLED
DPV4_ON = dt.date(2026, 10, 24)        # DP-V4: the class reads 12-month ROE; earlier rows REBUILT
DPV8_ON = dt.date(2026, 11, 18)        # DP-V8: the class reads r = rRF + RPM; earlier rows REBUILT
EDGE_BORDERLINE = 0.05                 # a ratio this close to a line can cross on a 2-3% price move
OWN_R_STEP = 2.0                       # DP-V7 step 2: own r +/- 2 points, as 7/9/11 is 9 +/- 2
CLASS_LETTER = {"DEMANDING": "D", "NEUTRAL": "N", "UNDEMANDING": "U", "NO READ": "-"}
# The identity is checked against the ROUNDING of the printed inputs (px, BVPS,
# ROE% and the ratio are all printed to 2dp), so SND's 0.51% ROE gets the wide
# bound it needs and a 2.7x name gets a tight one. Verified on all 29 exhibits
# 2026-08-24..10-14: no name exceeds its bound.
REFUSED = "tracker_with_registry.xlsx"
SECTION_RULE = re.compile(r"^-{20,}")

ACCT_RE = re.compile(r"\] \[([^\]]+)\] \[(HELD|SCOUT)\] ([A-Z][A-Z0-9.]*) \| Signal: (\w+) \| "
                     r"Confidence: (\d+)% \| Risk: (\w+)")
PER_RE = re.compile(r"PER-ACCOUNT: ([^.|]+)")


# --------------------------------------------------------------------------- #
# Parsing the implied_return exhibit (format stable since 2026-08-24)
# --------------------------------------------------------------------------- #

def _num(s):
    s = str(s).strip().rstrip("%x").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _section(lines, title_re):
    """The body lines of the section whose title matches title_re."""
    out, on = [], False
    for i, line in enumerate(lines):
        if SECTION_RULE.match(line) and i + 1 < len(lines) and re.match(title_re, lines[i + 1]):
            on = True
            continue
        if on and SECTION_RULE.match(line) and out and not re.match(title_re, lines[i - 1]):
            break
        if on:
            out.append(line)
    return out


S1_RE = re.compile(
    r"^\s+([A-Z][A-Z0-9.]*)\s+(\d{4}-\d{2}-\d{2})\s+(-?[\d.]+)\s+(-?[\d.]+)\s+([+-][\d.]+%)\s+"
    r"(n/a|-?[\d.]+%)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(?:([\d.]+)Q\s+([\d.]+)Q\s+)?(.*)$")
S1A_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*)\s+(Q\d|FY)\s+(n/a|-?[\d.]+%)\s+(n/a|-?[\d.]+%)\s+")
S4_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*)\s+(-?[\d.]+)\s+(-?[\d.]+%|n/a)\s+(-?[\d.]+)%\s+"
                   r"(-?[\d.]+)%\s+(-?[\d.]+)%\s+(n/a|-?[\d.]+x)")
S4B_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(n/a|-?[\d.]+%)\s+"
                    r"(NO CONVERGENT g|-?[\d.]+%)\s+(.*)$")
BLOCK_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*) NOT COMPUTED -- (.*)$")
DATE_RE = re.compile(r"implied_return_(\d{4}-\d{2}-\d{2})\.md$")


def parse_exhibit(path):
    """{ticker: fields} and {ticker: blocked reason} from one implied_return exhibit."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().replace("\r", "").split("\n")
    rec, blocked = {}, {}
    for line in _section(lines, r"^1\. INPUTS"):
        m = S1_RE.match(line)
        if m:
            rec[m.group(1)] = dict(
                anchor=m.group(2), bvps=_num(m.group(3)), px=_num(m.group(4)),
                roe=None if m.group(6) == "n/a" else _num(m.group(6)),
                mb=_num(m.group(7)), divy=_num(m.group(8)),
                anc_age=_num(m.group(9)) if m.group(9) else None,
                num_age=_num(m.group(10)) if m.group(10) else None,
                basis=m.group(11).strip())
    for line in _section(lines, r"^1a\."):
        m = S1A_RE.match(line)
        if m and m.group(1) in rec:
            rec[m.group(1)]["roe_edgar"] = None if m.group(4) == "n/a" else _num(m.group(4))
    for line in _section(lines, r"^4\. \(II\)"):
        m = S4_RE.match(line)
        if m and m.group(1) in rec:
            rec[m.group(1)].update(
                i7=_num(m.group(4)), i9=_num(m.group(5)), i11=_num(m.group(6)),
                ratio=None if m.group(7) == "n/a" else _num(m.group(7)))
    for line in _section(lines, r"^4b\."):
        m = S4B_RE.match(line)
        if m and m.group(1) in rec:
            rec[m.group(1)]["g_impl"] = None if "NO" in m.group(5) else _num(m.group(5))
    for line in lines:
        m = BLOCK_RE.match(line)
        if m:
            blocked[m.group(1)] = m.group(2).strip()
    return rec, blocked


def find_exhibits(root):
    """{date: path} for every dated implied_return exhibit in root and exhibits/archive."""
    out = {}
    for p in glob.glob(os.path.join(root, "implied_return_*.md")) + \
            glob.glob(os.path.join(root, "exhibits", "archive", "implied_return_*.md")):
        m = DATE_RE.search(os.path.basename(p))
        if m:
            d = dt.date.fromisoformat(m.group(1))
            if d not in out or os.path.dirname(p) == root:   # root copy wins
                out[d] = p
    return out


# --------------------------------------------------------------------------- #
# Valuation arithmetic -- the exhibit's own identity, nothing new
# --------------------------------------------------------------------------- #

def klass(ratio):
    if ratio is None:
        return "NO READ"
    if ratio >= DEMANDING_AT:
        return "DEMANDING"
    return "NEUTRAL" if ratio >= NEUTRAL_AT else "UNDEMANDING"


def implied_roe(mb, r=R_BASE, g=G_BASE):
    """implied_return (II), percent in and out: [r + (M/B - 1)(r - g)] / (1 + g),
    i.e. [M/B (r - g) + g] / (1 + g). Same expression as implied_return.py L179."""
    return (mb * (r - g) + g) / (1.0 + g / 100.0)


def ratio_from(px, bvps, roe, r=R_BASE):
    """implied/trailing at rate r. None where trailing ROE is not positive."""
    if not roe or roe <= 0 or not bvps or bvps <= 0 or not px:
        return None
    return implied_roe(px / bvps, r) / roe


def pe_lastfy(f):
    """Price over the EPS the class actually uses (ROE x BVPS)."""
    if not f.get("roe") or f["roe"] <= 0 or not f.get("bvps"):
        return None
    return f["px"] / (f["roe"] / 100.0 * f["bvps"])


def robustness(f):
    """DP-V4 (2026-10-24): the class under a cost-of-equity grid on the 12-month
    basis, and the distance from today's ratio to the nearest line. ROBUST
    only if the three agree. The old six-way test mixed in two ROE routes that
    were both known to be the wrong period (the last-FY year and one quarter
    x4); the basis is now settled by DP-V4, so what is left to doubt is the
    cost of equity and the closeness of a line. The last-FY class (the basis
    before DP-V4) is carried for reference only.
    AMENDED 2026-11-18 (DP-V8): the grid is the headline r -/+ 2 points
    (f["r_head"]; 9% when absent, which is the 7/9/11 grid exactly: ratio_at
    inverts the exhibit's own i9). r_grid carries the three rates."""
    r0 = f.get("r_head", R_BASE)
    grid = (r0 - R_STEP, r0, r0 + R_STEP) if r0 is not None else (None, None, None)
    combos = {}
    for r in grid:
        ratio = ratio_at(f, r) if r is not None else None
        combos[r] = (ratio, klass(ratio))
    base = klass(f.get("ratio"))
    ratios = [v[0] for v in combos.values() if v[0] is not None]
    classes = {v[1] for v in combos.values()}
    x = f.get("ratio")
    edge = min((abs(x - line), line) for line in (NEUTRAL_AT, DEMANDING_AT)) if x is not None else None
    lastfy = klass(f.get("ratio_lastfy")) if "ratio_lastfy" in f else None
    return dict(
        base=base,
        tag=("ROBUST" if len(classes) == 1 and base != "NO READ" else
             ("—" if base == "NO READ" else "FRAGILE")),
        lo=min(ratios) if ratios else None, hi=max(ratios) if ratios else None,
        r_flip=(base != "NO READ" and len(classes) > 1),
        r_classes=[combos[r][1] for r in grid], r_grid=list(grid),
        edge=edge[0] if edge else None, edge_line=edge[1] if edge else None,
        borderline=bool(edge) and edge[0] < EDGE_BORDERLINE,
        lastfy=lastfy, lastfy_ratio=f.get("ratio_lastfy"),
        basis_flip=(lastfy is not None and lastfy != base))


def decompose(prev, cur):
    """Split a ratio move into PRICE (new price, old fundamentals, old rate),
    FILING (new fundamentals at the new price, old rate) and RATE (the new
    headline r on everything new; DP-V8). The three sum to the total. A record
    without r_head reads 9%, so before DP-V8 RATE is 0. Returns None where any
    leg has no ratio."""
    ra, rb = prev.get("r_head", R_BASE), cur.get("r_head", R_BASE)
    if ra is None or rb is None:
        return None
    r0 = ratio_from(prev["px"], prev["bvps"], prev["roe"], ra)
    rp = ratio_from(cur["px"], prev["bvps"], prev["roe"], ra)
    rf = ratio_from(cur["px"], cur["bvps"], cur["roe"], ra)
    r1 = ratio_from(cur["px"], cur["bvps"], cur["roe"], rb)
    if None in (r0, rp, rf, r1):
        return None
    return dict(r0=r0, r1=r1, price=rp - r0, filing=rf - rp, rate=r1 - rf)


def g_implied_pct(roe_pct, mb, r=R_BASE):
    """implied_return (III) on the class's ROE, percent: the growth the price
    implies, g = (M/B r - ROE) / (M/B + ROE - 1). None when no convergent g
    exists (g >= r) or M/B is not positive -- implied_return.g_implied."""
    if roe_pct is None or mb is None or mb <= 0:
        return None
    roe, rs = roe_pct / 100.0, r / 100.0
    den = mb + roe - 1.0
    if den == 0:
        return None
    g = (mb * rs - roe) / den
    return None if g >= rs else g * 100.0


# --------------------------------------------------------------------------- #
# DP-V8 (2026-11-18): the headline r = rRF + RPM, rRF the 10-year yield dated
# before the session. One rule for the card, section 1's previous exhibit and
# every DP-V2 ledger date.
# --------------------------------------------------------------------------- #

def load_rrf_series(root):
    """[(date, percent), ...] oldest first from valuation_cache\\dgs10.json (FRED
    DGS10, written by cost_of_equity.py), and the file's 'fetched' stamp. None
    when the file is absent or unreadable."""
    path = os.path.join(root, RRF_SERIES)
    try:
        with open(path, encoding="utf-8") as fh:
            js = json.load(fh)
        obs = sorted((dt.date.fromisoformat(d), float(v)) for d, v in js.get("obs") or [])
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return dict(obs=obs, fetched=js.get("fetched"), source=js.get("source") or "FRED DGS10") if obs else None


def rrf_before(series, d):
    """(observation date, percent): the latest observation dated strictly
    before d -- the yield known when d's session opened. None if there is none."""
    best = None
    for od, v in (series or {}).get("obs") or []:
        if od < d:
            best = (od, v)
        else:
            break
    return best


def load_spreads(root):
    """valuation_cache\\spreads.json (DP-V7 step 3), or None."""
    try:
        with open(os.path.join(root, SPREADS), encoding="utf-8") as fh:
            js = json.load(fh)
        return js if isinstance(js.get("series"), dict) else None
    except (OSError, ValueError, AttributeError):
        return None


def spread_before(spreads, band, d):
    """(date, percent): the band's latest spread dated BEFORE d, the rRF rule."""
    rows = (((spreads or {}).get("series") or {}).get(band) or {}).get("obs") or []
    best = None
    for od, v in rows:
        try:
            od = dt.date.fromisoformat(od)
        except (TypeError, ValueError):
            continue
        if od < d and (best is None or od > best[0]):
            best = (od, float(v))
    return best


def headline_r(series, d):
    """dict(r, rrf, rrf_date, age_days, stale, why) for the card dated d."""
    got = rrf_before(series, d) if series else None
    if got is None:
        return dict(r=None, rrf=None, rrf_date=None, age_days=None, stale=False,
                    why=("no %s: run cost_of_equity.py online once (DP-V8)" % RRF_SERIES if not series
                         else "no 10-year yield dated before %s in %s" % (d, RRF_SERIES)))
    age = (d - got[0]).days
    return dict(r=got[1] + RPM_PCT, rrf=got[1], rrf_date=got[0], age_days=age,
                stale=age > RRF_STALE_DAYS, why=None)


# --------------------------------------------------------------------------- #
# DP-V7 step 2 (2026-11-18): the class at the name's own cost of equity.
# Context only: nothing below feeds klass(f["ratio"]), robustness(), the DP-V2
# gate or its ledger.
# --------------------------------------------------------------------------- #

def mb_from_i9(f):
    """M/B backed out of the exhibit's implied ROE at 9% (inverting implied_roe),
    so ratio_at(f, 9) IS the headline ratio i9 / ROE. The printed i9 carries more
    digits than the printed M/B (SND: 7.64% against 0.81x), so this is also the
    more precise M/B. Falls back to the printed M/B when i9 is absent."""
    i9 = f.get("i9")
    if i9 is None:
        return f.get("mb")
    return (i9 * (1.0 + G_BASE / 100.0) - G_BASE) / (R_BASE - G_BASE)


def ratio_at(f, r):
    """The class ratio at rate r (percent) on the card's own inputs: implied
    ROE at r from the exhibit's M/B (mb_from_i9), over the 12-month ROE. At r = 9
    this equals the headline ratio. None where r is not above g (the
    constant-growth value is not finite) or an input is missing."""
    if f is None or r is None or r <= G_BASE:
        return None
    mb, roe = mb_from_i9(f), f.get("roe")
    if mb is None or mb <= 0 or roe is None or roe <= 0:
        return None
    return implied_roe(mb, r) / roe


def own_r_read(f, cn, mkt_r=None):
    """The class at the name's own CAPM r (cost_of_equity.py's record `cn`), the
    own r -/+ 2 grid around it, and the class at the beta-1.0 r (`mkt_r`, rRF +
    RPM) so the move from 9% splits into the rate LEVEL and the name's BETA.
    None when there is no CAPM r for the name. Since DP-V8 the beta-1.0 r is
    the headline r, so cls_mkt is the headline class re-derived."""
    if not cn or cn.get("r_capm_pct") is None:
        return None
    r = cn["r_capm_pct"]
    grid = [ratio_at(f, r + d) for d in (-OWN_R_STEP, 0.0, OWN_R_STEP)]
    classes = [klass(x) for x in grid]
    base = classes[1]
    mkt = ratio_at(f, mkt_r)
    return dict(r=r, ratio=grid[1], cls=base, grid=grid, classes=classes,
                tag=("ROBUST" if len(set(classes)) == 1 and base != "NO READ"
                     else ("—" if base == "NO READ" else "FRAGILE")),
                ratio_mkt=mkt, cls_mkt=klass(mkt), flags=list(cn.get("flags") or []),
                ci=cn.get("r_ci_pct"))


def dividend_growth_r(q, eps12, roe_pct, r_capm):
    """The course's second estimate (Ch 9 slides 21, 25-28): r = D1/P0 + g, with
    the earnings retention model g = (1 - payout) x ROE. Payout is Schwab's
    dividend per share (divYield x lastPrice) over the SEC 12-month EPS; ROE is
    the class's own 12-month ROE. The constant-growth model needs g < rs (Ch 7
    slide 62), tested against the independent CAPM rs (testing it against the
    DCF r itself would be circular: D1/P0 + g always exceeds g). Dividends only:
    buybacks count as retention here, so g reads high for heavy repurchasers
    [?]. Returns dict(r, g, payout, y, why), percent; r is None with a why."""
    q = q or {}
    y, px = q.get("divYield"), q.get("lastPrice")
    out = dict(r=None, g=None, payout=None, y=y, why=None)
    if q.get("is_etf"):
        out["why"] = "fund: no company earnings"
    elif not y or y <= 0:
        out["why"] = "pays no dividend"
    elif not px or px <= 0:
        out["why"] = "no Schwab price for the dividend"
    elif eps12 is None or eps12 <= 0:
        out["why"] = "no positive 12-month EPS"
    elif roe_pct is None or roe_pct <= 0:
        out["why"] = "no positive 12-month ROE"
    if out["why"]:
        return out
    import corpfin as CF
    dps = y / 100.0 * px
    payout = dps / eps12
    out["payout"] = payout
    if payout >= 1.0:
        out["why"] = "payout %.0f%% of 12-month EPS: retention is negative" % (100 * payout)
        return out
    g = CF.retention_growth(roe_pct / 100.0, payout) * 100.0
    out["g"] = g
    if r_capm is None:
        out["why"] = "no CAPM r to test g < rs against"
    elif g >= r_capm:
        out["why"] = ("retention g %.1f%% is not below the CAPM r %.1f%%: not a constant "
                      "growth rate (gL < rs, Ch 7 s.62)" % (g, r_capm))
    else:
        out["r"] = CF.cost_of_equity_dcf(dps, px, g / 100.0) * 100.0
    return out


# --------------------------------------------------------------------------- #
# DP-V4: the 12-month basis, point in time, from the slim SEC cache
# --------------------------------------------------------------------------- #

class TTMBasis:
    """12-month ROE and the fundamentals panels per ticker and date, from
    valuation_cache\\ (written by ttm_eps / sec_data_audit; read only here).
    Each filer is loaded once; every read is point in time (sec_facts)."""

    def __init__(self, root):
        import sec_facts as SF
        self.SF, self.root = SF, root
        self.cik = SF.load_saved_cik_map(root)
        self._cf = {}

    def cf(self, t):
        if t not in self._cf:
            self._cf[t] = self.SF.load_slim(t, self.cik, self.root)
        return self._cf[t]

    def why_none(self, t):
        if not self.cik:
            return "no 12-month figure: valuation_cache\\cik_map.json missing (run ttm_eps)"
        if t not in self.cik:
            return "no 12-month figure: not an SEC filer in the cache map"
        return "no 12-month figure: no slim cache for this filer (run ttm_eps)"

    def roe(self, t, d, strict):
        """(roe percent or None, ttm_roe dict or None, why or None)."""
        cf = self.cf(t)
        if cf is None:
            return None, None, self.why_none(t)
        r = self.SF.ttm_roe(self.SF.point_in_time(cf, d, strict=strict), d)
        pct = r["roe"] * 100.0 if r["roe"] is not None else None
        return pct, r, r["why"]

    def fundamentals(self, t, d):
        cf = self.cf(t)
        if cf is None:
            return None
        return self.SF.fundamentals(self.SF.point_in_time(cf, d, strict=False), d)


def rebase(rec, basis, d, strict, r=R_BASE):
    """The exhibit's records re-based on 12-month ROE as of d (DP-V4).
    `roe` and `ratio` become the 12-month figures; the exhibit's own are kept
    as roe_lastfy / ratio_lastfy for reference and for the identity check.
    The implied ROE at each r (i7/i9/i11) depends only on price and book, so
    it carries over unchanged: ratio = i9 / 12-month ROE.
    AMENDED 2026-11-18 (DP-V8): the ratio is read at `r` (the headline r for
    d; 9% by default, which is i9 / ROE exactly). ratio_9 keeps the 9% ratio
    for reference. r None (no yield before d) leaves every ratio None."""
    out = {}
    for t, f in rec.items():
        g = dict(f, roe_lastfy=f.get("roe"), ratio_lastfy=f.get("ratio"),
                 g_impl_lastfy=f.get("g_impl"))
        pct, rr, why = basis.roe(t, d, strict) if basis is not None else (None, None, "no basis")
        g["roe"] = pct
        g["ttm_why"] = why
        g["ttm_notes"] = (rr or {}).get("notes") or []
        g["ttm_end"] = (rr or {}).get("ni_end")
        i9 = f.get("i9")
        g["ratio_9"] = (i9 / pct) if (i9 is not None and pct is not None and pct > 0) else None
        g["r_head"] = r
        g["ratio"] = ratio_at(g, r) if r is not None else None
        g["class_why"] = None if r is not None else "no headline r: no 10-year yield before %s (DP-V8)" % d
        g["g_impl"] = g_implied_pct(pct, f.get("mb"), r) if (pct is not None and r is not None) else None
        out[t] = g
    return out


def no_read_reason(f, blocked_reason=None):
    if blocked_reason:
        return blocked_reason
    if f is None:
        return "not in the valuation set"
    return f.get("ttm_why") or f.get("class_why") or "negative 12-month ROE"


def sector_caveat(t):
    """A one-line warning where a panel's ratio does not mean what it means
    elsewhere. Read from sector_map; nothing is computed from it."""
    try:
        import sector_map
        s = sector_map.STOCK_SECTOR.get(t)
    except Exception:                                   # noqa: BLE001
        s = None
    if s == "XLF":
        return "bank: operating cash flow and liabilities/equity are not comparable"
    if s == "XLRE":
        return "REIT: GAAP earnings carry depreciation; funds from operations are not read"
    return ""


def pct_s(x, cap=3.0):
    """'+12%'; beyond +/-300% the base is too small to read as a rate."""
    if x is None:
        return "—"
    if abs(x) > cap:
        return ">+300%" if x > 0 else "<-300%"
    return "%+.0f%%" % (100.0 * x)


def pct0(x):
    """'9%' for a ratio 0.09; '—' when undefined."""
    return "—" if x is None else "%.0f%%" % (100.0 * x)


def _p100(x):
    return None if x is None else 100.0 * x


def growth_cell(x, cap=3.0):
    """A sheet cell for a y/y change in percent; beyond +/-300% the same text
    the card prints (2026-10-29: the sheet printed SND 1200 and DOW 675)."""
    if x is None:
        return None
    if abs(x) > cap:
        return ">+300%" if x > 0 else "<-300%"
    return 100.0 * x


def hood_notes(u):
    """The 2b notes for one name, ONE list for the text card and the sheet
    (2026-10-29: the sheet had dropped 'negative book equity'). `u` is the
    fundamentals dict plus its sector caveat."""
    b, q = u.get("balance") or {}, u.get("quality") or {}
    out = [u["caveat"]] if u.get("caveat") else []
    if b.get("negative_equity"):
        eq = b.get("equity")
        out.append("negative book equity%s: L/E not defined, see L/A"
                   % ("" if eq is None else " (deficit $%.2fB)" % (abs(eq) / 1e9)))
    if q.get("net_loss"):
        out.append("12-month net loss: OCF/NI not defined, see OCF/rev")
    rn = roic_note_for(u)
    return out + list(u.get("notes") or []) + ([rn] if rn else [])


def roic_note_for(u):
    """DP-V6: the ROIC note for one name ('' for a standard read; a bank's ROIC
    is not shown, and its caveat already says why)."""
    if (u.get("caveat") or "").startswith("bank"):
        return ""
    try:
        import sec_facts as SF
        return SF.roic_note(u.get("roic"))
    except Exception:                                   # noqa: BLE001
        return ""


def roic_value(u):
    """DP-V6: the ROIC fraction to show, or None (no read, or a bank)."""
    if (u.get("caveat") or "").startswith("bank"):
        return None
    return (u.get("roic") or {}).get("roic")


def hood_sheet_row(t, u):
    """The 2b sheet row, in HOOD_SHEET_COLUMNS order."""
    g, q, b = u["growth"], u["quality"], u["balance"]
    bank = (u.get("caveat") or "").startswith("bank")
    return [t, g["eps"]["ttm"], growth_cell(g["eps"]["chg"]), growth_cell(g["revenue"]["chg"]),
            growth_cell(g["q_eps"]["chg"]), None if bank else q.get("ocf_to_ni"),
            None if bank else _p100(q.get("ocf_margin")),
            _p100(q.get("gross_margin")), _p100(q.get("gross_margin_year_ago")),
            _p100(q.get("op_margin")), _p100(q.get("op_margin_year_ago")),
            _p100(roic_value(u)),
            None if bank else b.get("liab_to_equity"),
            None if bank else _p100(b.get("liab_to_assets")),
            None if b.get("cash") is None else b["cash"] / 1e9,
            "; ".join(hood_notes(u))]


HOOD_SHEET_COLUMNS = (
    "Ticker", "EPS 12m", "EPS y/y %", "Revenue y/y %", "Last quarter EPS y/y %", "OCF / NI",
    "OCF / revenue %", "Gross margin %", "Gross margin a year ago %", "Operating margin %",
    "Operating margin a year ago %", "ROIC %", "Liabilities / equity", "Liabilities / assets %",
    "Cash ($B)", "Notes")


def dividend_implied_g(yield_pct, r=R_BASE):
    """Gordon, solved for g: P = D0(1+g)/(r-g)  ->  g = (r - y)/(1 + y)."""
    if yield_pct is None or yield_pct <= 0:
        return None
    y, rr = yield_pct / 100.0, r / 100.0
    return (rr - y) / (1.0 + y) * 100.0


# F-10 (Rob, 2026-11-18 14:58 CT: yes): step 3's own share-class bar, applied to
# section 5. A P/E below 1 is not a cheap stock: it is a price on one share class
# over EPS on another. BRK.B: Schwab eps 46,563.02 (Class A) on a 573.78 B price
# gives peRatio 0.01092, which section 5 used to label UNDEMANDING-equiv.
MIN_PE_ONE_CLASS = 1.0


def book_free_pe(px, eps12, schwab_pe):
    """Section 5's P/E: price over 12-month SEC EPS, else Schwab's own
    12-month P/E. Returns (pe, source, why). ADDED 2026-11-18 (F-10): a P/E
    below MIN_PE_ONE_CLASS from either route is refused, and `why` says so."""
    pe, src = None, ""
    if eps12 and eps12 > 0 and px:
        pe, src = px / eps12, "SEC 12m"
    elif schwab_pe and schwab_pe > 0:
        pe, src = schwab_pe, "Schwab 12m"
    if pe is not None and pe < MIN_PE_ONE_CLASS:
        return None, src, ("%s P/E %.4f < 1: price and EPS on different share classes (F-10)"
                           % (src, pe))
    return pe, src, None


# DP-V10 (FINC 5133 step 5, 2026-11-18): panel 2f. The numbers are implied_vol.py's;
# the card adds only the report-in-window flag, from the earnings calendar it
# already reads. One sigma 5d is the band in sigma's denominator: P(|move| > 3%)
# exceeds 31.7% exactly when the band is narrower than 1 sigma.
ONE_SIGMA_TWO_TAIL = 0.3173


def implied_rows(ivd, earn, on_card, date):
    """Panel 2f's rows from an implied_vol_<date>.json dict, sorted by P
    (highest first; no-reads last). None when the file is absent or is for
    another date. Each row: ticker, card, ok, why, expiry, sessions, iv,
    exp30, iv30, term, sigma, band_sigma, p, report, report_note."""
    if not isinstance(ivd, dict) or str(ivd.get("date")) != str(date):
        return None
    rows = []
    for t, x in sorted((ivd.get("names") or {}).items()):
        r = dict(ticker=t, card=t in on_card, ok=bool(x.get("ok")), why=x.get("why"), expiry=None,
                 sessions=None, iv=None, exp30=None, iv30=None, term=None, sigma=None,
                 band_sigma=None, p=None, report=None, report_note="")
        if r["ok"]:
            h, ref = x["horizon"], x["ref30"]
            r.update(expiry=str(h["expiry"]), sessions=h["sessions"], iv=h["iv"],
                     exp30=str(ref["expiry"]), iv30=ref["iv"], term=x.get("term_ratio"),
                     sigma=x["sigma_5d"], band_sigma=x["band_in_sigma"], p=x["p_breach"])
            e = (earn or {}).get(t) or {}
            try:
                rep_d = dt.date.fromisoformat(str(e.get("date")))
            except ValueError:
                rep_d = None
            exp_d = dt.date.fromisoformat(r["expiry"][:10])
            if rep_d is not None and date <= rep_d <= exp_d:
                import trading_calendar as _tc
                inside = rep_d <= _tc.shift_sessions(date, 5)
                r["report"] = str(rep_d)
                r["report_note"] = "report %s%s %s: the IV carries it" % (
                    rep_d.strftime("%m-%d"), (" " + e["hour"]) if e.get("hour") else "",
                    "inside the 5 sessions" if inside else "after the 5 sessions, before expiry")
        rows.append(r)
    rows.sort(key=lambda r: (not r["ok"], -(r["p"] or 0.0), r["ticker"]))
    return rows


# --------------------------------------------------------------------------- #
# DP-V7 step 3 (2026-11-18): capital and credit. Context only.
# --------------------------------------------------------------------------- #

MIN_ABS_EPS = 0.05             # a 12-month EPS closer to zero gives no share count
WACC_TAX = 0.255               # marginal rate: DP-V6's ruled statutory rate (Rob, 2026-10-30)


def capital_read(fu, px, cn, rrf_pct, spreads, d, mb=None, bank=False):
    """Panel 2e for one name, from the under-the-hood facts `fu` (sec_facts.
    fundamentals: growth, balance, roic, credit), the price, the name's
    cost-of-equity record `cn`, the headline rRF and the spread cache.

    BARS (fixed 2026-11-18, before the first live run):
      coverage   12-month EBIT (DP-V6's route) / 12-month GROSS interest expense;
                 EBITDA coverage adds 12-month D&A. A filer tagging only NET
                 interest: coverage on the net expense when it is a net cost
                 (labelled 'net'); none when it is net interest income.
      market cap price x diluted shares, shares = 12-month net income / 12-month
                 diluted EPS (same filer, same window); used only when |EPS| >=
                 0.05, both have one sign and |price / EPS| >= 1 (else the price
                 and the EPS are on different share classes: BRK.B). Fallback:
                 the exhibit's M/B x book equity.
      Altman Z   X1 (current assets - current liabilities) / total assets, X2
                 retained earnings / TA, X3 EBIT / TA, X4 market cap / TOTAL
                 liabilities (Web 24A note 5), X5 revenue / TA. Zones as Web 24A.
      band       return on capital = 12-month EBIT / (debt + equity incl. NCI),
                 pretax; debt to capital = debt / (debt + equity), both at book
                 at the ROIC close (corpfin.rating_band: the worse side). Debt +
                 equity not positive -> no band. NEGATIVE book equity (buybacks:
                 PM, BBWI) -> book D/C is an artifact, so the band reads the ROC
                 side alone, flagged.
      r_d        rRF + the band's ICE BofA OAS dated before the session. No
                 spread -> no WACC (never the course's 2016 table).
      WACC       w_d = debt / (debt + market cap); r_s = own CAPM r; T = 25.5%,
                 0 for a pass-through (DP-V6's tax basis). A name with no debt
                 has WACC = r_s.
      EVA        spread = ROIC - WACC; EVA = spread x DP-V6's average invested
                 capital; hurdle = WACC / (1 + WACC).
      shares     (1 + NI y/y) / (1 + EPS y/y) - 1, both defined and above -100%.
    A bank (sector caveat) reads none of it: interest is its cost of goods."""
    import corpfin as CF
    out = dict(cov=None, ebitda_cov=None, z=None, zone=None, z_x5=None, roc=None, dc=None, band=None,
               roc_band=None, dc_band=None, default_5y=None, spread=None, spread_date=None, r_d=None,
               e_mkt=None, e_route=None, debt=None, w_d=None, r_s=None, tax=None, wacc=None, roic=None,
               eva_spread=None, eva=None, hurdle=None, creates=None, growth_ok=None, ni_chg=None,
               eps_chg=None, shares_chg=None, notes=[], why=None)
    if bank:
        out["why"] = "bank: interest is its cost of goods; coverage, Altman, band and WACC are not comparable"
        return out
    fu = fu or {}
    ro, cr, bal, gr = (fu.get("roic") or {}), (fu.get("credit") or {}), (fu.get("balance") or {}), \
        (fu.get("growth") or {})
    ni = gr.get("net_income") or {}
    ep = gr.get("eps") or {}
    out.update(ni_chg=ni.get("chg"), eps_chg=ep.get("chg"))
    if ni.get("chg") is not None and ep.get("chg") is not None and ni["chg"] > -1 and ep["chg"] > -1:
        out["shares_chg"] = (1 + ni["chg"]) / (1 + ep["chg"]) - 1
    ebit = ro.get("ebit")
    if ebit is None:
        out["why"] = ro.get("why") or cr.get("why") or "no 12-month EBIT"
        return out
    out["notes"] += [n for n in (cr.get("notes") or []) if not n.startswith("interest: only net")]
    interest = cr.get("interest")
    if interest is None and cr.get("interest_net") is not None and cr["interest_net"] < 0:
        interest = -cr["interest_net"]                  # a net interest COST (credit balance < 0)
        out["notes"].append("coverage on NET interest expense (%s)" % cr.get("interest_tag"))
    elif interest is None and cr.get("interest_net") is not None:
        out["notes"].append("net interest INCOME: no interest cost to cover")
    out["cov"] = CF.interest_coverage(ebit, interest)
    if out["cov"] is not None and cr.get("da") is not None:
        out["ebitda_cov"] = (ebit + cr["da"]) / interest
    # market cap
    ni12, eps12 = ni.get("ttm"), ep.get("ttm")
    if px and ni12 and eps12 and abs(eps12) >= MIN_ABS_EPS and (ni12 > 0) == (eps12 > 0) \
            and abs(px / eps12) >= 1.0:
        out.update(e_mkt=px * ni12 / eps12, e_route="price x (12-month NI / diluted EPS)")
    elif mb and bal.get("equity") and bal["equity"] > 0:
        out.update(e_mkt=mb * bal["equity"], e_route="M/B x book equity")
    elif px and eps12 and abs(px / eps12) < 1.0:
        out["notes"].append("market cap: price and EPS are on different share classes (|P/E| < 1)")
    else:
        out["notes"].append("market cap: no usable share count (no 12-month EPS, EPS near zero, or NI "
                            "and EPS of different signs) and no M/B")
    # Altman Z
    ta, tl, sales = bal.get("assets"), bal.get("liabilities"), (gr.get("revenue") or {}).get("ttm")
    ca, cl, re_ = cr.get("current_assets"), cr.get("current_liabilities"), cr.get("retained_earnings")
    if None not in (ta, tl, sales, ca, cl, re_, out["e_mkt"]) and ta > 0 and tl > 0:
        out["z"] = CF.altman_z(ca - cl, re_, ebit, out["e_mkt"], tl, sales, ta)
        out["zone"] = CF.altman_zone(out["z"])
        out["z_x5"] = sales / ta
    # ratings band
    debt, eq = ro.get("debt"), ro.get("equity")
    out["debt"] = debt
    if debt is not None and eq is not None:
        cap = debt + eq
        if cap > 0:
            out.update(roc=100.0 * ebit / cap, dc=100.0 * debt / cap)
            if eq < 0:
                out["notes"].append("band: book equity is negative, so D/C %.0f%% is not used; ROC side alone"
                                    % out["dc"])
            rb = CF.rating_band(out["roc"], out["dc"] if eq >= 0 else None)
            out.update(band=rb["band"], roc_band=rb["roc_band"], dc_band=rb["dc_band"],
                       default_5y=rb["default_5y"])
            out["notes"] += rb["beyond"]
        else:
            out["notes"].append("band: debt + equity %.1fB is not positive" % (cap / 1e9))
    # r_d, WACC, EVA
    if out["band"]:
        sb = spread_before(spreads, out["band"], d)
        if sb:
            out.update(spread=sb[1], spread_date=str(sb[0]))
            if rrf_pct is not None:
                out["r_d"] = rrf_pct + sb[1]
        else:
            out["notes"].append("no %s spread dated before %s" % (out["band"], d))
    out["r_s"] = (cn or {}).get("r_capm_pct")
    out["tax"] = 0.0 if str(ro.get("tax_basis") or "").startswith("pass-through") else WACC_TAX
    if out["e_mkt"] and out["e_mkt"] > 0 and debt is not None and out["r_s"] is not None \
            and (out["r_d"] is not None or debt == 0):
        w_d = debt / (debt + out["e_mkt"])
        out["w_d"] = w_d
        out["wacc"] = CF.wacc(w_d, out["r_d"] or 0.0, out["tax"], 0.0, 0.0, 1.0 - w_d, out["r_s"])
    if ro.get("roic") is not None:
        out["roic"] = 100.0 * ro["roic"]
    if out["wacc"] is not None and out["roic"] is not None:
        out["eva_spread"] = out["roic"] - out["wacc"]
        out["hurdle"] = 100.0 * CF.growth_hurdle(out["wacc"] / 100.0)
        out["creates"] = out["roic"] > out["wacc"]
        out["growth_ok"] = out["roic"] > out["hurdle"]
        if ro.get("ic"):
            out["eva"] = out["eva_spread"] / 100.0 * ro["ic"]
    return out


# --------------------------------------------------------------------------- #
# Inputs other than the exhibit
# --------------------------------------------------------------------------- #

def parse_log(path):
    """{ticker: dict(acct, held, signal, conf, risk, per)} from a signals log."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = ACCT_RE.search(line)
            if not m:
                continue
            per = PER_RE.search(line)
            per_map = {}
            if per:
                for part in per.group(1).split(";"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        per_map[k.strip()] = v.strip()
            px = None
            if "Signal JSON:" in line:
                try:
                    j, _ = json.JSONDecoder().raw_decode(line.split("Signal JSON:", 1)[1].strip())
                    px = j.get("lastPrice")
                except ValueError:
                    px = None
            out[m.group(3)] = dict(acct=m.group(1).strip(), held=m.group(2) == "HELD",
                                   signal=m.group(4).upper(), conf=int(m.group(5)),
                                   risk=m.group(6).upper(), per=per_map, px=px)
    return out


def executability(s):
    if s["signal"] == "HOLD":
        return "—"
    if not s["per"]:
        return "BLOCKED" if s["risk"] != "APPROVED" else "APPROVED"
    ok = [k for k, v in s["per"].items() if v == "APPROVED"]
    if len(ok) == len(s["per"]):
        return "EXECUTABLE"
    if ok:
        return "PARTIAL (" + ", ".join(ok) + " only)"
    return "REJECTED in every account"


def load_quotes(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        q = json.load(fh)
    return q.get("quotes", {}) if isinstance(q, dict) else {}


def load_buy_rows(tracker, since):
    """(date, ticker, conf) for BUY rows on/after `since`. Reads date, ticker,
    signal and confidence ONLY -- no price, return or outcome column is read."""
    import openpyxl
    from build_actionable_registry import (SIGNALS_SHEET, FIRST_DATA_ROW,
                                           LAST_DATA_ROW_CAP, COL, as_date, conf_pct)
    wb = openpyxl.load_workbook(tracker, data_only=True, read_only=True)
    ws = wb[SIGNALS_SHEET]
    out, blank = [], 0
    last = max(COL["date"], COL["ticker"], COL["signal"], COL["conf"])
    for vals in ws.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW_CAP,
                             min_col=1, max_col=last, values_only=True):
        d = as_date(vals[COL["date"] - 1])
        if d is None:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        if d < since or str(vals[COL["signal"] - 1] or "").strip().upper() != "BUY":
            continue
        c = conf_pct(vals[COL["conf"] - 1])
        if c is not None:
            out.append((d, str(vals[COL["ticker"] - 1] or "").strip().upper(), c))
    wb.close()
    return out


# --------------------------------------------------------------------------- #
# DP-V2 counterfactual flip ledger -- counts only
# --------------------------------------------------------------------------- #

def dpv2_flip(cls, conf):
    """'ADMIT->REJECT', 'REJECT->ADMIT' or None, for a BUY at `conf` under DP-V2."""
    gate = DPV2_GATE.get(cls, DPV2_BASE_GATE)
    now, then = conf >= DPV2_BASE_GATE, conf >= gate
    if now and not then:
        return "ADMIT->REJECT"
    if then and not now:
        return "REJECT->ADMIT"
    return None


def _label_lastfy(d):
    return "backfilled" if d <= INSTALLED else "live"


def _label_ttm(d):
    """DP-V4: rows before the ruling are REBUILT point in time (only filings
    public before that session, the exhibit written that day); they count."""
    return "rebuilt" if d < DPV4_ON else "live"


def _label_v8(d):
    """DP-V8: rows before the ruling are REBUILT at their own session's r (the
    10-year yield dated before it, + RPM); they count."""
    return "rebuilt" if d < DPV8_ON else "live"


def dpv2_ledger(buy_rows, classes_by_date, label=_label_lastfy):
    """classes_by_date: {date: {ticker: class}}. Returns flips, unscored rows.
    A row on a session with no exhibit is NEVER counted. It is reported as
    UNSCORED, with the class from the nearest EARLIER exhibit as a hint only,
    and only when that hint would have flipped it."""
    flips, unscored = [], []
    dates = sorted(classes_by_date)
    for d, tk, c in sorted(buy_rows):
        if d not in classes_by_date:
            prior = [x for x in dates if x < d]
            hint = classes_by_date[prior[-1]].get(tk, "NO READ") if prior else None
            if hint and dpv2_flip(hint, c):
                unscored.append((d, tk, c, hint, prior[-1]))
            continue
        cls = classes_by_date[d].get(tk, "NO READ")
        f = dpv2_flip(cls, c)
        if f:
            flips.append((d, tk, c, cls, f, label(d)))
    return flips, unscored


# --------------------------------------------------------------------------- #
# The exhibit
# --------------------------------------------------------------------------- #

def fmt(v, spec="{:.2f}", none="—"):
    return none if v is None else spec.format(v)


def portfolio_rows(prd, date):
    """DP-V13 (FINC 5133 step 8, 2026-11-19): panel 2g's rows from a
    portfolio_risk_<date>.json dict; None when the file is absent or for
    another date. The numbers are portfolio_risk.py's; nothing here recomputes
    them, and nothing reads them back into a class, gate or the prompt."""
    if not isinstance(prd, dict) or str(prd.get("date")) != str(date):
        return None
    keys = ("label", "positions", "beta_card", "beta_card_cash", "coverage_beta", "sigma_p", "r2",
            "beta_hist", "n_eff", "top_name", "top_w", "top3_w", "cash_share", "dr", "n_obs", "short",
            "pairs_n", "pairs", "risk_share",
            # AMENDED 2026-11-19 (v1.1, before Part B): the other-asset share reaches the card
            "other_share", "other_types", "too_new", "max_pair", "limiting")
    accts = list(prd.get("accounts") or []) + ([prd["combined"]] if prd.get("combined") else [])
    return [{k: a.get(k) for k in keys} for a in accts]


def load_context(root, date):
    """DP-V3 (2026-10-22): the TTM exhibit (ttm_eps.py, V2) and the earnings
    calendar (earnings_calendar.py, V5) for the SAME date, if value.bat wrote
    them before this step. Missing files mean '—', never a guess.
    AMENDED 2026-10-24 (DP-V4): the CLASS now reads 12-month ROE itself, from
    valuation_cache\\ (TTMBasis); these two files remain context: the notes,
    the report date, and the calendar's adjusted consensus (section 2c).
    AMENDED 2026-11-18 (DP-V7 step 2): also cost_of_equity_<date>.json
    (cost_of_equity.py, value.bat step 7c), the per-name CAPM r. Context only.
    AMENDED 2026-11-18 (DP-V10, step 5): also implied_vol_<date>.json
    (implied_vol.py, value.bat step 7d), the market-implied move. Context only.
    AMENDED 2026-11-19 (DP-V13, step 8): also portfolio_risk_<date>.json
    (portfolio_risk.py, value.bat step 7e), risk per account. Context only."""
    out = {}
    for key, name in (("ttm", "ttm_eps_%s.json"), ("earn", "earnings_calendar_%s.json"),
                      ("coe", "cost_of_equity_%s.json"), ("iv", "implied_vol_%s.json"),
                      ("pr", "portfolio_risk_%s.json")):
        path = os.path.join(root, name % date)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = None
        if key == "earn" and isinstance(data, list):
            data = {r.get("ticker"): r for r in data}
        out[key] = data
    return out


THESIS_LABEL = ("THESIS BROKEN (Rob, 2026-10-22): off the scout list at the exit; "
                "until then, measurement only (DP-3C-bk)")


def conf_caveat():
    """ADDED 2026-11-07 (Phase 4a, DP-3C-br): the DP-3C-w exit finding, printed
    beside the confidence column so the card never presents a BUY's confidence
    as a conviction ranking. One sentence, sourced from rulings.py; reporting
    only -- no class, gate, flip or recorded figure reads it."""
    try:
        import rulings
        return getattr(rulings, "BUY_CONFIDENCE_CAVEAT", "") or ""
    except Exception:                                              # noqa: BLE001
        return ""


def thesis_label(t):
    """DP-3C-bk (2026-10-23): a name Rob removed from his watchlist because its
    thesis is broken, kept in the run until the exit for the measurement. The
    label tells the reader a BUY or SELL on it is not a candidate. Read from
    rulings.py, so it disappears when the ruling closes. Reporting only."""
    try:
        import rulings
        r = rulings.RULINGS.get("DP-3C-bk") or {}
    except Exception:                                   # noqa: BLE001
        return ""
    return THESIS_LABEL if (r.get("open") and t in (r.get("measurement_only") or ())) else ""


def _ctx_cells(ctx, t):
    """(ttm_eps, ttm_roe_pct, next_report, sessions_away, note) for ticker t.

    AMENDED 2026-10-23: the note joins every reason instead of showing only the
    first: the calendar flag, the TTM flags (STALE, negative equity, an equity
    date before the TTM end), a NO READ reason (without the doubled "TTM: no
    TTM:" of 10-22) and the DP-3C-bk thesis label."""
    tt = ((ctx.get("ttm") or {}).get(t)) or {}
    ee = ((ctx.get("earn") or {}).get(t)) or {}
    roe = tt.get("roe_ttm")
    bits = [ee["note"]] if ee.get("note") else []
    nr = tt.get("no_read")
    if nr and not ("fund" in nr and "fund" in (ee.get("note") or "")):
        bits.append(nr if nr.startswith("no TTM") else "TTM: " + nr)
    bits += ["TTM " + f for f in (tt.get("flags") or [])]
    if thesis_label(t):
        bits.append(thesis_label(t))
    return (tt.get("eps_ttm"), (roe * 100.0) if isinstance(roe, (int, float)) else None,
            ee.get("date"), ee.get("sessions"), "; ".join(bits))


def build(date, root, log_path, quotes_path, tracker):
    exhibits = find_exhibits(root)
    if date not in exhibits:
        raise SystemExit(("no implied_return_%s.md in %s or exhibits/archive -- run "
                          "implied_return first; nothing to build on." % (date, root), 2))
    rec_raw, blocked = parse_exhibit(exhibits[date])
    if not rec_raw:
        raise SystemExit(("implied_return_%s.md parsed to zero names -- format changed?" % date, 2))
    basis = TTMBasis(root)
    series = load_rrf_series(root)                          # DP-V8: the 10-year series
    hr = headline_r(series, date)
    r_head = hr["r"]
    rec = rebase(rec_raw, basis, date, strict=False, r=r_head)   # the card: everything filed by today
    earlier = sorted(d for d in exhibits if d < date)
    prev_date = earlier[-1] if earlier else None
    prev_raw, prev_blocked = parse_exhibit(exhibits[prev_date]) if prev_date else ({}, {})
    hr_prev = headline_r(series, prev_date) if prev_date else None
    prev_rec = rebase(prev_raw, basis, prev_date, strict=False, r=hr_prev["r"]) if prev_date else {}
    sig = parse_log(log_path)
    quotes = load_quotes(quotes_path)
    ctx = load_context(root, date)
    findings = []

    rob = {t: robustness(f) for t, f in rec.items()}
    # DP-V7 step 2: own r, context only (never read by rob, klass(ratio) or the ledger)
    coe = ctx.get("coe") if isinstance(ctx.get("coe"), dict) else None
    coe_names = (coe or {}).get("names") or {}
    mkt_r = r_head                                          # DP-V8: the headline is the beta-1.0 r
    own = {t: own_r_read(rec.get(t), coe_names.get(t), mkt_r) for t in set(rec) | set(sig)}
    held = sorted(t for t, s in sig.items() if s["held"])
    directional = sorted((t for t, s in sig.items() if s["signal"] in ("BUY", "SELL")),
                         key=lambda t: -sig[t]["conf"])
    if not basis.cik:
        findings.append("no valuation_cache\\cik_map.json: every class is NO READ until ttm_eps "
                        "or sec_data_audit has run online once (DP-V4)")
    if r_head is None:
        findings.append("no headline r (%s): every class is NO READ, never a 9%% fallback (DP-V8)" % hr["why"])
    elif hr["stale"]:
        findings.append("headline rRF STALE: the latest 10-year yield before %s is dated %s (%d days); "
                        "run cost_of_equity.py online (DP-V8)" % (date, hr["rrf_date"], hr["age_days"]))
    r_s = fmt(r_head, "{:.2f}%")

    L = []
    L.append("=" * 100)
    L.append("VALUE CARD -- the valuation layer organised around decisions and changes")
    L.append("Counterfactual only. Modifies no gate, admits and rejects nothing, reads no outcome.")
    L.append("=" * 100)
    L.append("as of %s   exhibit %s   previous exhibit %s   log %s" % (
        date, os.path.basename(exhibits[date]), prev_date or "none", os.path.basename(log_path)))
    L.append("class = implied ROE at r / 12-MONTH ROE (DP-V4: SEC filings, point in time); "
             "lines %.2fx / %.2fx (DP-V2 memo 3.1, frozen)" % (DEMANDING_AT, NEUTRAL_AT))
    L.append("r     = rRF + RPM = %s (DP-V8): 10-year Treasury %s dated %s (FRED DGS10, the latest "
             "before %s) + %.2f%%" % (r_s, fmt(hr["rrf"], "{:.2f}%"), hr["rrf_date"] or "-", date, RPM_PCT)
             if r_head is not None else "r     = NO HEADLINE r (DP-V8): %s" % hr["why"])
    caveat = conf_caveat()
    if caveat:
        L.append("conf  = " + caveat)
    L.append("")

    # ---- 0. coverage -------------------------------------------------------
    read = [t for t in rec if rob[t]["base"] != "NO READ"]
    held_read = [t for t in held if t in rec and rob[t]["base"] != "NO READ"]
    held_rob = [t for t in held_read if rob[t]["tag"] == "ROBUST"]
    dir_read = [t for t in directional if t in rec and rob[t]["base"] != "NO READ"]
    L.append("-" * 100)
    L.append("0. COVERAGE -- stated first, because it bounds everything below")
    L.append("-" * 100)
    L.append("  watchlist %d   classed %d   ROBUST %d" % (
        len(sig), len(read), sum(1 for t in read if rob[t]["tag"] == "ROBUST")))
    L.append("  held names %d   classed %d   ROBUST %d   %s" % (
        len(held), len(held_read), len(held_rob),
        ("(" + ", ".join(held_rob) + ")") if held_rob else ""))
    L.append("  today's directionals %d   classed %d   %s" % (
        len(directional), len(dir_read), ", ".join(dir_read) or ""))
    coverage = dict(watchlist=len(sig), classed=len(read),
                    robust=sum(1 for t in read if rob[t]["tag"] == "ROBUST"),
                    held=len(held), held_classed=len(held_read), held_robust=held_rob,
                    directional=len(directional), directional_classed=dir_read)
    L.append("")

    # ---- 1. what changed ---------------------------------------------------
    L.append("-" * 100)
    L.append("1. WHAT CHANGED since %s -- filings, class crossings, robustness, coverage"
             % (prev_date or "(no earlier exhibit)"))
    L.append("-" * 100)
    basis_diff = [t for t in read if rob[t]["basis_flip"]] + \
           [t for t in rec if rob[t]["base"] == "NO READ" and rob[t]["lastfy"] not in (None, "NO READ")]
    basis_line = ("BASIS: 12-month ROE since %s (DP-V4). Today %d class(es) differ from the last-FY "
                  "basis: %s" % (DPV4_ON, len(basis_diff), ", ".join(
                      "%s %s->%s" % (t, rob[t]["lastfy"], rob[t]["base"]) for t in sorted(basis_diff))
                      or "none"))
    diff_9 = sorted(t for t in rec if klass(rec[t].get("ratio_9")) != rob[t]["base"])
    rate_line = ("RATE: r = rRF + RPM since %s (DP-V8), %s today. %d class(es) differ from the 9%% "
                 "class: %s" % (DPV8_ON, r_s, len(diff_9), ", ".join(
                     "%s %s->%s" % (t, klass(rec[t].get("ratio_9")), rob[t]["base"]) for t in diff_9)
                     or "none"))
    L.append("  " + rate_line)
    L.append("  " + basis_line)
    if prev_date and hr_prev and hr_prev["r"] is not None and r_head is not None:
        L.append("  r %s on %s (10-yr dated %s) -> %s today (%+.2f points)" % (
            fmt(hr_prev["r"], "{:.2f}%"), prev_date, hr_prev["rrf_date"], r_s, r_head - hr_prev["r"]))
    changes = []
    if prev_date:
        for t in sorted(set(rec) | set(prev_rec)):
            a, b = prev_rec.get(t), rec.get(t)
            if a is None and b is not None:
                changes.append("  %-5s ENTERED the computed set" % t)
                continue
            if b is None and a is not None:
                changes.append("  %-5s LEFT the computed set -- %s" % (t, blocked.get(t, "not in today's exhibit")))
                continue
            filing = a["anchor"] != b["anchor"] or a.get("roe") != b.get("roe")
            ca, cb = klass(a.get("ratio")), klass(b.get("ratio"))
            dec = decompose(a, b)
            if filing:
                part = (" | ratio %.2f -> %.2f: price %+.2f, filing %+.2f, rate %+.2f" % (
                    dec["r0"], dec["r1"], dec["price"], dec["filing"], dec["rate"])) if dec else ""
                changes.append("  %-5s NEW FILING  anchor %s -> %s   BVPS %s -> %s   12-month ROE %s -> %s%s" % (
                    t, a["anchor"], b["anchor"], fmt(a["bvps"]), fmt(b["bvps"]),
                    fmt(a.get("roe"), "{:.2f}%"), fmt(b.get("roe"), "{:.2f}%"), part))
            if ca != cb:
                why = (" (price %+.2f, filing %+.2f, rate %+.2f)" % (
                    dec["price"], dec["filing"], dec["rate"])) if dec else ""
                changes.append("  %-5s CLASS %s -> %s   ratio %s -> %s%s" % (
                    t, ca, cb, fmt(a.get("ratio")), fmt(b.get("ratio")), why))
            ra = robustness(a)
            if ra["tag"] != rob[t]["tag"]:
                lo, hi = rob[t]["lo"], rob[t]["hi"]
                changes.append("  %-5s ROBUSTNESS %s -> %s   r -/+2 range %s%s" % (
                    t, ra["tag"], rob[t]["tag"],
                    ("%.2f-%.2f" % (lo, hi)) if lo is not None else "—",
                    ("   (%.2f from the %.2fx line: borderline, expect flicker)" % (
                        rob[t]["edge"], rob[t]["edge_line"])) if rob[t]["borderline"] else ""))
        for t in sorted(set(blocked) - set(prev_blocked)):
            changes.append("  %-5s newly BLOCKED -- %s" % (t, blocked[t]))
    quiet = None
    if changes:
        L.extend(changes)
    else:
        moves = []
        for t, b in rec.items():
            a = prev_rec.get(t)
            if a and a.get("ratio") is not None and b.get("ratio") is not None:
                moves.append((abs(b["ratio"] - a["ratio"]), t, a["ratio"], b["ratio"]))
        if moves:
            mv = max(moves)
            quiet = ("No filing changed. Price and rate moves only; no class crossed a line. "
                     "Largest ratio move: %s %.2f -> %.2f" % (mv[1], mv[2], mv[3]))
            L.append("  NO FILING CHANGED. Price and rate moves only; no class crossed a line.")
            L.append("  largest ratio move: %s %.2f -> %.2f" % (mv[1], mv[2], mv[3]))
        else:
            L.append("  nothing to compare.")
    L.append("")

    # ---- 2. decision card --------------------------------------------------
    L.append("-" * 100)
    L.append("2. DECISION CARD -- today's directionals, then held names")
    L.append("-" * 100)
    L.append("  %-5s %-20s %-8s %-24s %-19s %5s %-12s %6s %-11s %-18s %-9s %7s %s" % (
        "tk", "held in", "today", "executability", "class (ratio)", "edge", "@9%",
        "P/E", "r -/+2", "robust", "@own r", "g impl", "DP-V2 gate"))
    order = directional + [t for t in sorted(held, key=lambda t: -(rec.get(t, {}).get("ratio") or -1))
                           if t not in directional]
    card = []
    hood = {t: basis.fundamentals(t, date) for t in order if t in basis.cik}
    for t in order:
        s = sig[t]
        f = rec.get(t)
        rb = rob.get(t)
        cls = rb["base"] if rb else "NO READ"
        why = no_read_reason(f, blocked.get(t)) if cls == "NO READ" else ""
        if s["signal"] == "BUY":
            gate = DPV2_GATE[cls]
            flip = dpv2_flip(cls, s["conf"])
            gate_s = "%d%s" % (gate, ("  FLIP " + flip) if flip else "")
        else:
            gate_s = "n/a" if s["signal"] == "SELL" else ""
        cls_s = ("%s (%.2f)" % (cls, f["ratio"])) if f and f.get("ratio") is not None else "NO READ"
        rng = ("%.2f-%.2f" % (rb["lo"], rb["hi"])) if rb and rb["lo"] is not None else "—"
        rtag = rb["tag"] if rb else "—"
        if rb and rtag == "FRAGILE":
            rtag = "FRAGILE r " + "/".join(CLASS_LETTER.get(c, "-") for c in rb["r_classes"])
        if rb and rb["borderline"] and rb["base"] != "NO READ":
            rtag = (rtag + " EDGE") if rtag != "—" else "EDGE"
        fu = hood.get(t) or {}
        eps12 = ((fu.get("growth") or {}).get("eps") or {}).get("ttm")
        px = f.get("px") if f else (s.get("px") or (quotes.get(t) or {}).get("lastPrice"))
        pe12 = (px / eps12) if (px and eps12 and eps12 > 0) else None
        c9 = klass(f.get("ratio_9")) if f else "NO READ"
        last_s = "—" if c9 == "NO READ" else c9 + ("*" if c9 != cls else "")   # DP-V8: the 9% class
        o = own.get(t)
        own_s = "—" if o is None else "%.1f%% %s%s" % (
            o["r"], CLASS_LETTER.get(o["cls"], "-"), "*" if o["cls"] not in (cls, "NO READ") else "")
        L.append("  %-5s %-20s %-8s %-24s %-19s %5s %-12s %6s %-11s %-18s %-9s %7s %s" % (
            t, (s["acct"] if s["held"] else "scout")[:20], "%s %d" % (s["signal"], s["conf"]),
            executability(s)[:24], cls_s, fmt(rb["edge"] if rb else None), last_s[:12],
            fmt(pe12, "{:.1f}"), rng, rtag[:18], own_s,
            fmt(f.get("g_impl"), "{:.2f}%") if f else "—", gate_s))
        if cls == "NO READ" and why:
            L.append("  %-5s   NO READ: %s" % ("", why))
        card.append(dict(ticker=t, held=s["held"], account=s["acct"], signal=s["signal"],
                         conf=s["conf"], executability=executability(s), cls=cls,
                         ratio=f.get("ratio") if f else None,
                         edge=rb["edge"] if rb else None, borderline=rb["borderline"] if rb else False,
                         cls_lastfy=rb["lastfy"] if rb else None,
                         ratio_lastfy=f.get("ratio_lastfy") if f else None,
                         cls_9=c9, ratio_9=f.get("ratio_9") if f else None, r_head=r_head,
                         pe_ttm=pe12, lo=rb["lo"] if rb else None, hi=rb["hi"] if rb else None,
                         robust=rb["tag"] if rb else "—", robust_detail=rtag,
                         g_impl=f.get("g_impl") if f else None,
                         dpv2_gate=DPV2_GATE[cls] if s["signal"] == "BUY" else None,
                         dpv2_flip=dpv2_flip(cls, s["conf"]) if s["signal"] == "BUY" else None,
                         num_age_q=f.get("num_age") if f else None, no_read_reason=why or None,
                         ttm_roe_pct=f.get("roe") if f else None, ttm_end=f.get("ttm_end") if f else None,
                         own_r=o["r"] if o else None, cls_own_r=o["cls"] if o else None,
                         ratio_own_r=o["ratio"] if o else None, own_r_classes=o["classes"] if o else None,
                         own_r_tag=o["tag"] if o else None, own_r_flags=o["flags"] if o else None,
                         cls_mkt_r=o["cls_mkt"] if o else None))
    L.append("")
    L.append("  class: implied ROE at r = rRF + RPM (%s, DP-V8) over 12-month ROE. edge: distance to" % r_s)
    L.append("  the nearest line (under %.2f marks EDGE: a 2-3%% price move can cross it). @9%%: the" % EDGE_BORDERLINE)
    L.append("  class at the 9% used before DP-V8, for reference (* where it differs). P/E: price over")
    L.append("  12-month diluted EPS (SEC). r -/+2: the ratio across r - 2 / r / r + 2; ROBUST only")
    L.append("  if all three give one class (FRAGILE r U/N/D lists them, D/N/U = DEMANDING/NEUTRAL/")
    L.append("  UNDEMANDING). @own r (DP-V7 step 2): the class at the name's own CAPM r, panel 2d;")
    L.append("  * where it differs from the class. Context only. Last-FY (pre-DP-V4): section 3.")
    L.append("  DP-V2 gate: the PROPOSED modifier (75/70/65) on the class; NOT APPLIED.")
    L.append("")

    # ---- 2b. under the hood (DP-V4) ------------------------------------------
    L.append("  2b. UNDER THE HOOD -- SEC filings, last 12 months against the 12 months before.")
    L.append("      Direction (are earnings growing?), quality (are they cash?), balance sheet.")
    L.append("  %-5s %8s %8s %8s %9s %6s %7s %-18s %-15s %5s %6s %5s %8s  %s" % (
        "tk", "EPS 12m", "EPS y/y", "rev y/y", "lastQ y/y", "OCF/NI", "OCF/rev", "gross mgn (yr ago)",
        "op mgn (yr ago)", "ROIC", "L/E", "L/A", "cash", "note"))

    def mgn(a, b):
        if a is None:
            return "—"
        return "%.0f%% (%s)" % (100 * a, "—" if b is None else "%.0f%%" % (100 * b))
    for c in card:
        t = c["ticker"]
        fu = hood.get(t)
        cav = sector_caveat(t)
        if not fu or fu.get("end") is None:
            reason = ("fund: no company statements"
                      if (quotes.get(t) or {}).get("is_etf") else basis.why_none(t)
                      if not fu else "; ".join(fu.get("notes") or []) or "no 12-month figures")
            L.append("  %-5s %s" % (t, reason))
            c.update(under_hood=None)
            continue
        g, q, b = fu["growth"], fu["quality"], fu["balance"]
        bank = cav.startswith("bank")
        ocfni = None if bank else q.get("ocf_to_ni")
        ocfm = None if bank else q.get("ocf_margin")
        le = None if bank else b.get("liab_to_equity")
        la = None if bank else b.get("liab_to_assets")
        notes = hood_notes(dict(fu, caveat=cav or None))
        L.append("  %-5s %8s %8s %8s %9s %6s %7s %-18s %-15s %5s %6s %5s %8s  %s" % (
            t, fmt(g["eps"]["ttm"]), pct_s(g["eps"]["chg"]), pct_s(g["revenue"]["chg"]),
            pct_s(g["q_eps"]["chg"]), fmt(ocfni), pct0(ocfm),
            mgn(q["gross_margin"], q["gross_margin_year_ago"]),
            mgn(q["op_margin"], q["op_margin_year_ago"]),
            pct0(roic_value(dict(fu, caveat=cav or None))), fmt(le), pct0(la),
            ("%.1fB" % (b["cash"] / 1e9)) if b.get("cash") is not None else "—",
            "; ".join(notes)[:120]))
        c.update(under_hood=dict(fu, caveat=cav or None))
    L.append("      y/y: change against the same window a year earlier, signed by direction;")
    L.append("      beyond +/-300% the base is too small to read as a rate. OCF/NI: operating cash")
    L.append("      flow over net income (below 1: profits not yet cash). OCF/rev: operating cash")
    L.append("      flow over revenue, defined through a loss. L/E: liabilities / equity. L/A:")
    L.append("      liabilities / assets, defined when equity is negative (above 100%: a deficit).")
    L.append("      ROIC (DP-V6): 12-month operating profit after tax / average invested capital")
    L.append("      (debt + equity incl. minority interests - cash). Tax: the filer's own rate, else")
    L.append("      its 3-year rate, else 25.5%; an operating loss gets no shield. Defined when equity")
    L.append("      is negative; a bank's is not shown. The note says when a read is not standard.")
    L.append("")

    # ---- 2c. expectations (DP-V4) ---------------------------------------------
    L.append("  2c. EXPECTATIONS -- the next report and Finnhub's ADJUSTED (non-GAAP) consensus,")
    L.append("      on their own basis. 'class if met' scales the 12-month ROE by the change the")
    L.append("      consensus implies, book unchanged: APPROXIMATE, context only, never the class.")
    has_earn = bool(ctx.get("earn"))
    if not has_earn and not ctx.get("ttm"):
        L.append("      not available for %s (value.bat did not write the calendar)." % date)
    L.append("  %-5s %-11s %8s %10s %9s %9s %-16s %-14s %s" % (
        "tk", "next report", "sessions", "consensus", "beat (4)", "adj 12m", "if met",
        "class if met", "note"))
    for c in card:
        t = c["ticker"]
        _e, _roe, nd, ns, note = _ctx_cells(ctx, t)
        ee = (((ctx.get("earn") or {}).get(t)) or {}).get("expectations") or {}
        chg = ee.get("chg_if_met")
        cim = None
        if chg is not None and c.get("ratio") is not None and (1.0 + chg) > 0:
            cim = c["ratio"] / (1.0 + chg)
        full_note = note
        met_s = ("%s (%s)" % (fmt(ee.get("adj_ttm_if_met")), pct_s(chg))
                 if ee.get("adj_ttm_if_met") is not None else (ee.get("why") or "—"))
        L.append("  %-5s %-11s %8s %10s %9s %9s %-16s %-14s %s" % (
            t, nd or "—", "" if ns is None else ns, fmt(ee.get("eps_estimate")),
            ("%d of %d" % (ee["beats"], ee["reported"])) if ee.get("beats") is not None else "—",
            fmt(ee.get("adj_ttm")), met_s[:16],
            ("%s (%.2f)" % (klass(cim), cim)) if cim is not None else "—", full_note[:140]))
        c.update(next_report=nd, sessions_to_report=ns, context_note=full_note,
                 ttm_eps=((c.get("under_hood") or {}).get("growth") or {}).get("eps", {}).get("ttm"),
                 expectations=dict(ee, cls_if_met=klass(cim) if cim is not None else None,
                                   ratio_if_met=cim) if ee else None)
    L.append("")

    # ---- 2d. cost of equity (DP-V7 step 2) ------------------------------------
    L.append("  2d. COST OF EQUITY (DP-V7 step 2) -- each name's own rate beside the headline r. CONTEXT")
    L.append("      ONLY: the class reads rRF + RPM (DP-V8), the beta-1.0 rate; own r never enters it.")
    coe_info = None
    if not coe:
        L.append("      not available for %s (value.bat step 7c did not write cost_of_equity_%s.json)."
                 % (date, date))
        for c in card:
            c.update(cost_of_equity=None)
    else:
        rr = coe.get("rrf") or {}
        src = coe.get("beta_source") or {}
        L.append("      own r = rRF %s (%s%s) + adjusted beta x RPM %s. Betas estimated %s; SE, window and" % (
            fmt(rr.get("pct"), "{:.2f}%"), rr.get("source") or rr.get("why") or "none",
            (", observed %s" % rr["date"]) if rr.get("date") else "", fmt(coe.get("rpm_pct"), "{:.2f}%"),
            src.get("as_of") or "?"))
        L.append("      the weekly check are in cost_of_equity_%s.md." % date)
        if rr.get("pct") is not None and hr["rrf"] is not None and abs(rr["pct"] - hr["rrf"]) > 1e-9:
            L.append("      NOTE: cost_of_equity_%s read rRF %s, the headline %s dated %s: re-run step 7c."
                     % (date, fmt(rr["pct"], "{:.2f}%"), fmt(hr["rrf"], "{:.2f}%"), hr["rrf_date"]))
        L.append("  %-5s %-20s %7s %-11s %7s %6s %6s %7s | %-7s %-7s %-7s %-13s %s" % (
            "tk", "beta adj (raw R2 n)", "r CAPM", "95% CI", "r DCF", "g", "payout", "DCF-CAPM",
            "@9%", "class", "@own r", "own -2/0/+2", "flags; note"))

        def cell(cl, x):
            return "-" if cl in (None, "NO READ") else "%s %.2f" % (CLASS_LETTER[cl], x)
        n_dcf = 0
        for c in card:
            t = c["ticker"]
            cn = coe_names.get(t) or {}
            o = own.get(t)
            f = rec.get(t)
            if cn.get("beta_adj") is None:
                L.append("  %-5s %s" % (t, cn.get("why") or "not in cost_of_equity_%s.json" % date))
                c.update(cost_of_equity=None)
                continue
            dg = dividend_growth_r(quotes.get(t), c.get("ttm_eps"), f.get("roe") if f else None,
                                   cn.get("r_capm_pct"))
            n_dcf += dg["r"] is not None
            spread = (dg["r"] - cn["r_capm_pct"]) if dg["r"] is not None else None
            ci = cn.get("r_ci_pct")
            note = " ".join(cn.get("flags") or [])
            if dg["why"]:
                note = (note + "; " if note else "") + "DCF: " + dg["why"]
            grid_s = "-" if not o or o["cls"] == "NO READ" else "%s %s" % (
                "/".join(CLASS_LETTER.get(k, "-") for k in o["classes"]), o["tag"])
            L.append("  %-5s %-20s %7s %-11s %7s %6s %6s %7s | %-7s %-7s %-7s %-13s %s" % (
                t, ("%.2f (%.2f %.2f %d)" % (cn["beta_adj"], cn["beta_raw"], cn["r2"], cn["n"]))[:20],
                fmt(cn.get("r_capm_pct"), "{:.2f}%"), ("%.1f-%.1f%%" % tuple(ci)) if ci else "—",
                fmt(dg["r"], "{:.2f}%"), fmt(dg["g"], "{:.1f}%"),
                fmt(None if dg["payout"] is None else 100 * dg["payout"], "{:.0f}%"),
                fmt(spread, "{:+.2f}"), cell(c.get("cls_9"), c.get("ratio_9")), cell(c["cls"], c.get("ratio")),
                cell(o["cls"] if o else None, o["ratio"] if o else None), grid_s[:13], note[:150]))
            c.update(cost_of_equity=dict(
                beta_adj=cn["beta_adj"], beta_raw=cn["beta_raw"], se=cn.get("se"), r2=cn["r2"], n=cn["n"],
                r_capm=cn.get("r_capm_pct"), r_ci=ci, flags=cn.get("flags") or [],
                dcf=dg, dcf_minus_capm=spread, cls_9=c.get("cls_9"), ratio_9=c.get("ratio_9"),
                cls_head=c["cls"], ratio_head=c.get("ratio"),
                cls_own=o["cls"] if o else None, ratio_own=o["ratio"] if o else None,
                own_classes=o["classes"] if o else None, own_tag=o["tag"] if o else None))
        withr = [c for c in card if (c.get("cost_of_equity") or {}).get("r_capm") is not None]
        dif = [c for c in withr if c["cls"] != "NO READ" and c["cost_of_equity"]["cls_own"] not in (c["cls"], None)]
        dif_l = [c for c in withr if c["cls"] != "NO READ" and c["cost_of_equity"]["cls_9"] not in (c["cls"], None, "NO READ")]
        L.append("      r CAPM = rRF + adjusted beta x RPM; 95% CI: the raw beta +/- 1.96 SE through Blume and")
        L.append("      RPM. r DCF = D1/P0 + g, g = (1 - payout) x 12-month ROE (Ch 9 s.21-28), defined only")
        L.append("      where g < r CAPM (Ch 7 s.62); dividends only, so buybacks count as retention [?].")
        L.append("      @9%: the class before DP-V8. class: the headline at rRF + RPM, the rate LEVEL (one r for")
        L.append("      every name). @own r: level plus the name's BETA. own -2/0/+2: own r -/+ 2 points;")
        L.append("      ROBUST only if all three agree. Own r is the CAPM r alone: the course averages its")
        L.append("      three estimates (Ch 9 s.31), but dividend growth reads for %d of %d names here and the"
                 % (n_dcf, len(withr)))
        L.append("      own-bond-yield method has no feed yet (step 3 brings the cost of debt).")
        L.append("      own r differs from the class: %d (%s). The class differs from 9%%: %d (%s)." % (
            len(dif), ", ".join("%s %s->%s" % (c["ticker"], CLASS_LETTER[c["cls"]],
                                              CLASS_LETTER[c["cost_of_equity"]["cls_own"]]) for c in dif) or "none",
            len(dif_l), ", ".join("%s %s->%s" % (c["ticker"], CLASS_LETTER[c["cost_of_equity"]["cls_9"]],
                                                CLASS_LETTER[c["cls"]]) for c in dif_l)
            or "none"))
        coe_info = dict(file="cost_of_equity_%s.json" % date, rrf=rr, rpm_pct=coe.get("rpm_pct"),
                        mkt_r_pct=mkt_r, beta_as_of=src.get("as_of"), dcf_read=n_dcf, with_r=len(withr),
                        differ_own=[c["ticker"] for c in dif], differ_level=[c["ticker"] for c in dif_l])
    L.append("")

    # ---- 2e. capital and credit (DP-V7 step 3) --------------------------------
    spreads = load_spreads(root)
    L.append("  2e. CAPITAL AND CREDIT (DP-V7 step 3) -- can it carry its debt, and does it earn its cost")
    L.append("      of capital? CONTEXT ONLY: nothing here enters the class, a gate or the prompt.")
    if not spreads:
        L.append("      no %s yet: r_d and WACC need cost_of_equity.py (step 7c) online once." % SPREADS)
    L.append("  %-5s %7s %7s %-22s %6s %6s %-14s %6s | %7s %6s %5s %-13s %6s %6s %6s %7s %7s %6s %-7s %s" % (
        "tk", "EBIT/i", "EBITDA", "Altman Z (zone)", "ROC", "D/C", "band (ROC/DC)", "5y def", "mkt $B",
        "debt", "w_d", "r_d (spread)", "r_s", "WACC", "ROIC", "spread", "EVA $B", "hurdle", "growth",
        "shares y/y; note"))
    zl = {"SAFE": "SAFE", "ZONE OF IGNORANCE": "GREY", "DISTRESS": "DISTRESS"}
    cap_rows = []
    for c in card:
        t = c["ticker"]
        u = c.get("under_hood")
        if not u:
            c.update(capital=None)
            continue
        f = rec.get(t)
        px = f.get("px") if f else (sig[t].get("px") or (quotes.get(t) or {}).get("lastPrice"))
        k = capital_read(u, px, coe_names.get(t), hr["rrf"], spreads, date,
                         mb=mb_from_i9(f) if f else None,
                         bank=str(u.get("caveat") or "").startswith("bank"))
        c.update(capital=k)
        cap_rows.append((t, k))
        if k["why"]:
            L.append("  %-5s %s" % (t, k["why"][:150]))
            continue
        sh = ("%+.1f%% (NI %s, EPS %s)" % (100 * k["shares_chg"], pct_s(k["ni_chg"]), pct_s(k["eps_chg"]))
              if k["shares_chg"] is not None else "-")
        note = "; ".join([sh] + k["notes"])
        L.append("  %-5s %7s %7s %-22s %6s %6s %-14s %6s | %7s %6s %5s %-13s %6s %6s %6s %7s %7s %6s %-7s %s" % (
            t, fmt(k["cov"], "{:.1f}x"), fmt(k["ebitda_cov"], "{:.1f}x"),
            ("%.2f %s" % (k["z"], zl.get(k["zone"], ""))) if k["z"] is not None else "-",
            fmt(k["roc"], "{:.1f}%"), fmt(k["dc"], "{:.0f}%"),
            ("%s (%s/%s)" % (k["band"], k["roc_band"], k["dc_band"])) if k["band"] else "-",
            fmt(k["default_5y"], "{:.2f}%"),
            fmt(None if k["e_mkt"] is None else k["e_mkt"] / 1e9, "{:.1f}"),
            fmt(None if k["debt"] is None else k["debt"] / 1e9, "{:.1f}"), fmt(k["w_d"], "{:.2f}"),
            ("%.2f%% (%.2f)" % (k["r_d"], k["spread"])) if k["r_d"] is not None else "-",
            fmt(k["r_s"], "{:.1f}%"), fmt(k["wacc"], "{:.1f}%"), fmt(k["roic"], "{:.1f}%"),
            fmt(k["eva_spread"], "{:+.1f}"), fmt(None if k["eva"] is None else k["eva"] / 1e9, "{:+.2f}"),
            fmt(k["hurdle"], "{:.1f}%"),
            "-" if k["growth_ok"] is None else ("adds" if k["growth_ok"] else "DESTROYS"), note[:170]))
    read_v = [(t, k) for t, k in cap_rows if k["wacc"] is not None and k["roic"] is not None]
    L.append("      EBIT/i, EBITDA: 12-month EBIT (DP-V6) and EBIT + D&A over gross interest (Ch 3 s.40-42).")
    L.append("      Altman Z: Web 24A eq. 24A-1; DISTRESS < 1.81, GREY 1.81-2.99, SAFE above; X5 (sales /")
    L.append("      assets) carries the largest weight, so high-turnover retailers read safe by construction.")
    L.append("      ROC: pretax EBIT / (debt + equity); D/C: debt / (debt + equity), book; band: the worse")
    L.append("      of the two against S&P's medians (Ch 5 s.45), 5y def its default rate (s.42). Book")
    L.append("      leverage misreads a negative-equity name (buybacks): its D/C runs past 100%.")
    L.append("      r_d = rRF + the band's ICE BofA OAS (FRED, dated before the session). WACC = w_d r_d (1 -")
    L.append("      25.5%) + w_s r_s at market weights, r_s = own r (2d). spread = ROIC - WACC; EVA = spread x")
    L.append("      average capital; growth adds value only if ROIC > hurdle = WACC/(1+WACC) (Ch 7 s.51).")
    L.append("      shares y/y = (1 + NI y/y)/(1 + EPS y/y) - 1: negative when buybacks lifted EPS.")
    L.append("      ROIC above WACC: %d of %d read (%s). Growth below the hurdle: %s." % (
        sum(1 for _t, k in read_v if k["creates"]), len(read_v),
        ", ".join(t for t, k in read_v if k["creates"]) or "none",
        ", ".join(t for t, k in read_v if not k["growth_ok"]) or "none"))
    L.append("")

    # ---- 2f. market-implied move (FINC 5133 step 5, DP-V10) -----------------
    ivd = ctx.get("iv") if isinstance(ctx.get("iv"), dict) else None
    iv_rows = implied_rows(ivd, ctx.get("earn"), {c["ticker"] for c in card}, date)
    L.append("  2f. MARKET-IMPLIED MOVE (FINC 5133 step 5, DP-V10) -- the options market's own 5-day move")
    L.append("      and its chance of leaving the fixed +/-3% HOLD band. CONTEXT ONLY: nothing here enters")
    L.append("      the class, a gate, the prompt or D4 (D4's baseline waits for its own pre-registration).")
    if iv_rows is None:
        L.append("      not available for %s (value.bat step 7d did not write implied_vol_%s.json%s)." % (
            date, date, "" if not ivd else "; the file is for %s" % ivd.get("date")))
    else:
        L.append("      chains fetched %s. * = on the decision card above." % ivd.get("fetched_at"))
        L.append("  %-5s %1s %-18s %6s %-11s %6s %5s %7s %7s %7s  %s" % (
            "tk", "", "horizon (sess)", "IV", "~30d", "IV", "term", "1sd 5d", "band/sd", "P>3%", "note"))
        for r in iv_rows:
            if not r["ok"]:
                L.append("  %-5s %1s %s" % (r["ticker"], "*" if r["card"] else "", r["why"]))
                continue
            L.append("  %-5s %1s %-18s %6s %-11s %6s %5s %7s %7s %7s  %s" % (
                r["ticker"], "*" if r["card"] else "", "%s (%d)" % (r["expiry"][:10], r["sessions"]),
                fmt(100 * r["iv"], "{:.1f}%"), r["exp30"][:10], fmt(100 * r["iv30"], "{:.1f}%"),
                fmt(r["term"], "{:.2f}"), fmt(100 * r["sigma"], "{:.2f}%"), fmt(r["band_sigma"], "{:.2f}"),
                fmt(100 * r["p"], "{:.1f}%"), r["report_note"]))
        okr = [r for r in iv_rows if r["ok"]]
        ps = sorted(r["p"] for r in okr)
        med = (ps[len(ps) // 2] if len(ps) % 2 else (ps[len(ps) // 2 - 1] + ps[len(ps) // 2]) / 2.0) if ps else None
        L.append("      horizon: the earliest expiry on or after the +5 session (sessions to it in brackets);")
        L.append("      ~30d: the expiry nearest 30 days, for reference; term = horizon IV / 30-day IV (above 1:")
        L.append("      the market prices an event before the later expiry). IV: ATM, mean of call and put.")
        L.append("      1sd 5d = IV x sqrt(5/252); band/sd = 3% / 1sd; P>3% = 2(1 - N(band/sd)), a zero-mean")
        L.append("      normal (Ch 8). RISK-NEUTRAL: the market's PRICE of the move, not a real-world forecast")
        L.append("      (Web 26B); a normal understates fat tails. The horizon IV is applied over 5 sessions.")
        L.append("      read %d of %d; median P>3%% %s; the band is under 1 sd (P > 31.7%%) for %d (%s);"
                 % (len(okr), len(iv_rows), fmt(None if med is None else 100 * med, "{:.1f}%"),
                    sum(1 for r in okr if r["p"] > ONE_SIGMA_TWO_TAIL),
                    ", ".join(r["ticker"] for r in okr if r["p"] > ONE_SIGMA_TWO_TAIL) or "none"))
        L.append("      a report inside the window: %s." % (
            ", ".join("%s %s" % (r["ticker"], r["report"][5:]) for r in okr if r["report"]) or "none"))
    L.append("")

    # ---- 2g. portfolio risk per account (FINC 5133 step 8, DP-V13) -------------
    prd = ctx.get("pr") if isinstance(ctx.get("pr"), dict) else None
    pr_rows = portfolio_rows(prd, date)
    L.append("  2g. PORTFOLIO RISK PER ACCOUNT (FINC 5133 step 8, DP-V13) -- each account's beta, sigma and")
    L.append("      concentration from today's holdings. CONTEXT ONLY: nothing here enters the class, a gate,")
    L.append("      the prompt or risk_engine (DP-V1). Labels and weights only; no dollar amounts.")
    if pr_rows is None:
        L.append("      not available for %s (value.bat step 7e did not write portfolio_risk_%s.json%s)." % (
            date, date, "" if not prd else "; the file is for %s" % prd.get("date")))
    else:
        L.append("  %-22s %5s %7s %8s %7s %7s %6s %6s %-12s %6s %5s %6s %6s" % (
            "account", "names", "beta", "whole", "sigma", "mkt R2", "own b", "N_eff", "top-1", "top-3",
            "cash", "other", "div"))
        for a in pr_rows:
            L.append("  %-22s %5s %7s %8s %7s %7s %6s %6s %-12s %6s %5s %6s %6s%s" % (
                a["label"][:22], a["positions"], fmt(a["beta_card"]), fmt(a["beta_card_cash"]),
                fmt(None if a["sigma_p"] is None else 100 * a["sigma_p"], "{:.1f}%"),
                fmt(None if a["r2"] is None else 100 * a["r2"], "{:.0f}%"), fmt(a["beta_hist"]),
                fmt(a["n_eff"], "{:.1f}"),
                "%s %s" % (a["top_name"] or "", fmt(None if a["top_w"] is None else 100 * a["top_w"], "{:.0f}%")),
                fmt(None if a["top3_w"] is None else 100 * a["top3_w"], "{:.0f}%"),
                fmt(None if a["cash_share"] is None else 100 * a["cash_share"], "{:.0f}%"),
                fmt(None if a.get("other_share") is None else 100 * a["other_share"], "{:.0f}%"), fmt(a["dr"]),
                "  SHORT (%s returns, limited by %s)" % (a["n_obs"], a.get("limiting")) if a["short"] else ""))
        for a in pr_rows:
            bits = []
            if a["pairs"]:
                bits.append("rho >= 0.70: %d pair(s), %s" % (a["pairs_n"], ", ".join(
                    "%s-%s %.2f" % (p["a"], p["b"], p["rho"]) for p in a["pairs"])))
            elif a.get("max_pair"):
                bits.append("no pair at rho >= 0.70 (highest %s-%s %.2f)" % (
                    a["max_pair"]["a"], a["max_pair"]["b"], a["max_pair"]["rho"]))
            if a.get("too_new"):
                bits.append("left out of sigma (under 250 returns of its own): %s" % ", ".join(
                    "%s %.1f%%" % (y["ticker"], 100 * y["w"]) for y in a["too_new"]))
            if a["risk_share"]:
                bits.append("largest variance shares %s" % ", ".join(
                    "%s %.0f%%" % (t, 100 * x) for t, x in a["risk_share"] if x is not None))
            if bits:
                L.append("      %s: %s" % (a["label"], "; ".join(bits)))
        if prd.get("in_both"):
            L.append("      held in more than one account: %s." % ", ".join(prd["in_both"]))
        L.append("      beta = sum w x the card's adjusted beta (panel 2d; Ch 6 slides 70-72), over the EQUITY and ETF")
        L.append("      positions only. whole = beta x their share of the account, with cash and every other asset")
        L.append("      (other: %s) at beta 0 -- right for T-bills and CDs, not for long or corporate bonds." % (
            ", ".join(sorted({t for a in pr_rows for t in (a.get("other_types") or [])})) or "none"))
        L.append("      sigma: today's weights on 2 years of daily returns, AS IF HELD")
        L.append("      THROUGHOUT (backward-looking). mkt R2 = the market's share of the account's variance; own b =")
        L.append("      its slope on SPY. N_eff = 1 / sum w^2; div = sum w sigma_i / sigma_p (1 = no diversification).")
        if prd.get("findings"):
            L.append("      findings (portfolio_risk_%s.md): %s." % (date, "; ".join(prd["findings"])))
    L.append("")

    # ---- 3. robustness, every classed name ---------------------------------
    L.append("-" * 100)
    L.append("3. ROBUSTNESS -- every classed name: the cost-of-equity grid on the 12-month basis")
    L.append("-" * 100)
    if r_head is not None:
        L.append("  grid: r - 2 / r / r + 2 = %.2f / %.2f / %.2f%% (DP-V8; r = rRF + RPM)" % (
            r_head - R_STEP, r_head, r_head + R_STEP))
    L.append("  %-5s %-12s %7s %-18s %-20s | %-12s %-12s %-12s | %6s %-13s | %-6s %-6s %-8s" % (
        "tk", "class", "ratio", "@9% (ratio)", "last-FY (ratio)", "r-2", "r", "r+2", "edge", "tag",
        "own r", "-2/0/+2", "own tag"))
    for t in sorted(read, key=lambda t: -(rec[t].get("ratio") or 0)):
        rb = rob[t]
        o = own.get(t)
        L.append("  %-5s %-12s %7s %-18s %-20s | %-12s %-12s %-12s | %6s %-13s | %-6s %-6s %-8s" % (
            t, rb["base"], fmt(rec[t].get("ratio")),
            ("%s (%s)" % (klass(rec[t].get("ratio_9")), fmt(rec[t].get("ratio_9"))))[:18],
            ("%s (%s)" % (rb["lastfy"], fmt(rb["lastfy_ratio"])))[:20],
            *rb["r_classes"], fmt(rb["edge"]), rb["tag"] + (" EDGE" if rb["borderline"] else ""),
            ("%.1f%%" % o["r"]) if o else "—",
            "/".join(CLASS_LETTER.get(k, "-") for k in o["classes"]) if o else "—",
            o["tag"] if o else "—"))
    n_rob = sum(1 for t in read if rob[t]["tag"] == "ROBUST")
    n_edge = sum(1 for t in read if rob[t]["borderline"])
    n_basis = sum(1 for t in read if rob[t]["basis_flip"])
    L.append("  ROBUST %d of %d.  EDGE (within %.2f of a line) %d.  Class differs from 9%%: %d.  From last-FY: %d."
             % (n_rob, len(read), EDGE_BORDERLINE, n_edge, len(diff_9), n_basis))
    own_read = [t for t in read if own.get(t) and own[t]["cls"] != "NO READ"]
    own_dif = [t for t in own_read if own[t]["cls"] != rob[t]["base"]]
    if coe:
        L.append("  own r (DP-V7 step 2, context only; -2/0/+2 = own r -/+ 2 points): read %d of %d, ROBUST %d;"
                 % (len(own_read), len(read), sum(1 for t in own_read if own[t]["tag"] == "ROBUST")))
        L.append("  class at own r differs from the class: %d (%s)." % (len(own_dif), ", ".join(
            "%s %s->%s" % (t, CLASS_LETTER[rob[t]["base"]], CLASS_LETTER[own[t]["cls"]]) for t in sorted(own_dif))
            or "none"))
    else:
        L.append("  own r: not available (no cost_of_equity_%s.json)." % date)
    L.append("")

    # ---- 4. DP-V2 counterfactual flip ledger -------------------------------
    L.append("-" * 100)
    L.append("4. DP-V2 COUNTERFACTUAL FLIP LEDGER -- COUNTS ONLY. No outcome is read here.")
    L.append("-" * 100)
    cls_ttm, cls_9, cls_old, rate_of = {}, {}, {}, {}
    for d, p in exhibits.items():
        if DPV2_SINCE <= d <= date:
            r_, _ = parse_exhibit(p)
            # the BUY on d was decided that morning: only filings public BEFORE d, and
            # (DP-V8) the 10-year yield dated before d
            hd = headline_r(series, d)
            rate_of[d] = hd["r"]
            rb_ = rebase(r_, basis, d, strict=True, r=hd["r"])
            cls_ttm[d] = {t: klass(f.get("ratio")) for t, f in rb_.items()}
            if d < DPV8_ON:
                cls_9[d] = {t: klass(f.get("ratio_9")) for t, f in rb_.items()}
            if d < DPV4_ON:
                cls_old[d] = {t: klass(f.get("ratio")) for t, f in r_.items()}
    flips, unscored, closed, closed_un, closed9, closed9_un = [], [], [], [], [], []
    if tracker:
        rows = [r for r in load_buy_rows(tracker, DPV2_SINCE) if r[0] <= date]
        flips, unscored = dpv2_ledger(rows, cls_ttm, label=_label_v8)
        closed9, closed9_un = dpv2_ledger([r for r in rows if r[0] < DPV8_ON], cls_9, label=_label_ttm)
        closed, closed_un = dpv2_ledger([r for r in rows if r[0] < DPV4_ON], cls_old)
    L.append("  ON THE 12-MONTH BASIS AT r = rRF + RPM (DP-V4, DP-V8; the count). Rows before %s are" % DPV8_ON)
    L.append("  REBUILT point in time: only filings public before that session, the exhibit written that")
    L.append("  day, and the 10-year yield dated before it.")
    for d, tk, c, cls, f, src in flips:
        L.append("  %s  %-5s BUY %3.0f  %-11s %-14s %-8s r %s" % (d, tk, c, cls, f, src,
                                                             fmt(rate_of.get(d), "{:.2f}%")))
    if not flips:
        L.append("  no flip rows.")
    for d, tk, c, hint, pd_ in unscored:
        L.append("  %s  %-5s BUY %3.0f  UNSCORED -- no exhibit that session; %s on %s would flip it. "
                 "Not counted [?]" % (d, tk, c, hint, pd_))
    try:
        import trading_calendar as cal
        left = len(cal.sessions_between(date + dt.timedelta(days=1), DPV2_STOP))
    except Exception:                                              # noqa: BLE001
        left = None
    tks = sorted({f[1] for f in flips})
    L.append("  flip rows %d of %d needed   tickers %d of %d (%s)   stop %s%s" % (
        len(flips), DPV2_MIN_ROWS, len(tks), DPV2_MIN_TICKERS, ", ".join(tks) or "none",
        DPV2_STOP, ("   sessions left %d" % left) if left is not None else ""))
    L.append("  If the n condition is unmet on %s, DP-V2 is WITHDRAWN, NOT EXTENDED (memo 6)." % DPV2_STOP)
    closed_tks = sorted({f[1] for f in closed})
    closed9_tks = sorted({f[1] for f in closed9})
    L.append("")
    L.append("  CLOSED -- the 12-month ledger at r = 9%% as it ran %s .. %s (DP-V8). On the record;" % (
        DPV2_SINCE, DPV8_ON - dt.timedelta(days=1)))
    L.append("  never pooled with the count above:")
    for d, tk, c, cls, f, src in closed9:
        L.append("  %s  %-5s BUY %3.0f  %-11s %-14s %s" % (d, tk, c, cls, f, src))
    for d, tk, c, hint, pd_ in closed9_un:
        L.append("  %s  %-5s BUY %3.0f  UNSCORED (prior %s on %s)" % (d, tk, c, hint, pd_))
    L.append("  closed: %d row(s), %d ticker(s) (%s)" % (len(closed9), len(closed9_tks),
                                                       ", ".join(closed9_tks) or "none"))
    L.append("")
    L.append("  CLOSED -- the last-FY ledger as it ran %s .. %s (DP-V4). On the record; never" % (
        DPV2_SINCE, DPV4_ON - dt.timedelta(days=1)))
    L.append("  pooled with the count above:")
    for d, tk, c, cls, f, src in closed:
        L.append("  %s  %-5s BUY %3.0f  %-11s %-14s %s" % (d, tk, c, cls, f, src))
    for d, tk, c, hint, pd_ in closed_un:
        L.append("  %s  %-5s BUY %3.0f  UNSCORED (prior %s on %s)" % (d, tk, c, hint, pd_))
    L.append("  closed: %d row(s), %d ticker(s) (%s)" % (len(closed), len(closed_tks),
                                                       ", ".join(closed_tks) or "none"))
    L.append("")

    # ---- 5. book-free reads ------------------------------------------------
    L.append("-" * 100)
    L.append("5. BOOK-FREE READS -- context only, for names the class cannot read")
    L.append("-" * 100)
    r_bf = r_head if r_head is not None and r_head > G_BASE else None     # DP-V8: the headline r
    pe_hi = DEMANDING_AT / ((r_bf - G_BASE) / (100 + G_BASE)) if r_bf else None
    pe_lo = NEUTRAL_AT / ((r_bf - G_BASE) / (100 + G_BASE)) if r_bf else None
    L.append("  P/E band: the class's own lines restated as P/E at r = %s (about %s and %s, section 6)," % (
        r_s, fmt(pe_hi, "{:.0f}"), fmt(pe_lo, "{:.0f}")))
    L.append("  on 12-month EPS (SEC, else Schwab's own 12-month P/E). Dividend-implied g: Gordon at")
    L.append("  r = %s, g = (r - y)/(1 + y). It ignores buybacks, so it UNDERSTATES for buyback-heavy names." % r_s)
    bf = []
    for t in sorted(set(held) | set(directional)):
        if t in rec and rob[t]["base"] != "NO READ":
            continue
        q = quotes.get(t, {})
        px, y = sig[t].get("px") or q.get("lastPrice"), q.get("divYield")
        fu = hood.get(t) if t in hood else basis.fundamentals(t, date) if t in basis.cik else None
        eps12 = (((fu or {}).get("growth") or {}).get("eps") or {}).get("ttm")
        pe, src, pe_why = book_free_pe(px, eps12, q.get("peRatio"))     # F-10 guard
        band = None if (pe is None or pe_hi is None) else (
            "DEMANDING-equiv" if pe >= pe_hi else ("NEUTRAL-equiv" if pe >= pe_lo else "UNDEMANDING-equiv"))
        gdiv = dividend_implied_g(y, r=r_bf) if r_bf else None
        etf = q.get("is_etf") or q.get("asset_type") not in (None, "EQUITY")
        note = "fund: distributions, not earnings" if etf else (pe_why or src)
        bf.append((t, pe, band, y, gdiv, note))
        L.append("  %-5s P/E %7s  %-18s divY %6s  dividend-implied g %7s  %s" % (
            t, fmt(pe, "{:.1f}"), band or ("no P/E" if pe_why else "no positive eps"), fmt(y, "{:.2f}%"),
            fmt(gdiv, "{:.2f}%"), note))
    L.append("")

    # ---- 6. identity check -------------------------------------------------
    L.append("-" * 100)
    L.append("6. IDENTITY CHECK -- implied_return's own ratio (its last-FY basis) as a P/E:")
    L.append("   (P/EPS)(r-g)/(1+g) + g/((1+g)ROE). It checks implied_return's arithmetic, not the class.")
    L.append("-" * 100)
    worst, breach, checked = 0.0, [], 0
    for t, f in rec_raw.items():
        if not f.get("roe") or f["roe"] <= 0 or f.get("ratio") is None:
            continue
        recon = ratio_from(f["px"], f["bvps"], f["roe"])
        if recon is None:
            continue
        checked += 1
        diff = abs(recon - f["ratio"])
        bound = f["ratio"] * (0.005 / f["px"] + 0.005 / f["bvps"] + 0.005 / f["roe"]) + 0.005
        worst = max(worst, diff)
        if diff > bound:
            breach.append("%s %.3f vs %.2f (bound %.3f)" % (t, recon, f["ratio"], bound))
    k = (R_BASE - G_BASE) / (100.0 + G_BASE)
    L.append("  %d names reconstructed; max |reconstructed - printed| = %.3f; outside the rounding "
             "bound: %s" % (checked, worst, ", ".join(breach) or "none"))
    L.append("  so a class is %.4f x P/E + %.4f/ROE: DEMANDING ~ P/E >= %.1f, UNDEMANDING ~ < %.1f" % (
        k, G_BASE / (100.0 + G_BASE), DEMANDING_AT / k, NEUTRAL_AT / k))
    L.append("  on whichever EPS the ROE carries: since DP-V4, the 12-month EPS.")
    if r_bf:
        kh = (r_bf - G_BASE) / (100.0 + G_BASE)
        L.append("  at the headline r = %s (DP-V8) the same lines are DEMANDING ~ P/E >= %.1f, "
                 "UNDEMANDING ~ < %.1f." % (r_s, DEMANDING_AT / kh, NEUTRAL_AT / kh))
    if breach:
        findings.append("identity check FAILED for %s: implied_return's class no longer reconstructs "
                        "as a P/E within rounding -- its formula or inputs changed; re-read section 1"
                        % ", ".join(b.split()[0] for b in breach))
    unparsed = [t for t in sig if t not in rec and t not in blocked]
    L.append("")
    L.append("=" * 100)
    L.append("FINDINGS: %d" % len(findings))
    for x in findings:
        L.append("  - " + x)
    L.append("  not in the valuation set (dark, fund, scope or negative ROE): %s" % (", ".join(sorted(unparsed)) or "none"))
    L.append("=" * 100)
    L.append("Counterfactual only. No gate modified. No valuation asserted, no price target implied.")
    L.append("Advisory-only - no orders - not financial advice.")

    # ASCII only on the way out: the runners redirect stdout through the Windows
    # ANSI code page, and a stray non-ASCII dash should never cost an exhibit.
    L = [line.replace("—", "-") for line in L]
    snapshot = dict(date=str(date), exhibit=os.path.basename(exhibits[date]), conf_caveat=conf_caveat(),
                    log=os.path.basename(log_path), coverage=coverage, quiet=quiet,
                    basis=dict(name="12-month ROE (DP-V4) at r = rRF + RPM (DP-V8)", since=str(DPV4_ON),
                               line=basis_line, rate_line=rate_line,
                               differ=[dict(ticker=t, lastfy=rob[t]["lastfy"], now=rob[t]["base"])
                                       for t in sorted(basis_diff)],
                               differ_9=[dict(ticker=t, at9=klass(rec[t].get("ratio_9")), now=rob[t]["base"])
                                         for t in diff_9]),
                    headline=dict(r=r_head, rrf=hr["rrf"], rrf_date=str(hr["rrf_date"]) if hr["rrf_date"] else None,
                                  rpm=RPM_PCT, age_days=hr["age_days"], stale=hr["stale"], why=hr["why"],
                                  since=str(DPV8_ON), series=(series or {}).get("fetched"),
                                  previous=dict(date=str(prev_date), r=hr_prev["r"]) if hr_prev else None),
                    identity_outside_bound=breach,
                    identity=dict(checked=checked, max_diff=worst, k=k,
                                  pe_demanding=DEMANDING_AT / k, pe_undemanding=NEUTRAL_AT / k),
                    previous=str(prev_date) if prev_date else None, card=card,
                    robustness={t: dict(cls=rob[t]["base"], ratio=rec[t].get("ratio"),
                                        lastfy=rob[t]["lastfy"], lastfy_ratio=rob[t]["lastfy_ratio"],
                                        tag=rob[t]["tag"], edge=rob[t]["edge"],
                                        borderline=rob[t]["borderline"],
                                        lo=rob[t]["lo"], hi=rob[t]["hi"],
                                        r_classes=rob[t]["r_classes"], r_grid=rob[t]["r_grid"],
                                        cls_9=klass(rec[t].get("ratio_9")), ratio_9=rec[t].get("ratio_9"),
                                        ttm_roe_pct=rec[t].get("roe"),
                                        ttm_why=rec[t].get("ttm_why"),
                                        own_r=own[t]["r"] if own.get(t) else None,
                                        cls_own_r=own[t]["cls"] if own.get(t) else None,
                                        ratio_own_r=own[t]["ratio"] if own.get(t) else None,
                                        own_r_classes=own[t]["classes"] if own.get(t) else None,
                                        own_r_tag=own[t]["tag"] if own.get(t) else None) for t in rec},
                    capital=dict(spreads=(spreads or {}).get("fetched"), read=len(read_v),
                                 creates=[t for t, k in read_v if k["creates"]],
                                 growth_below_hurdle=[t for t, k in read_v if not k["growth_ok"]]),
                    cost_of_equity=dict(coe_info or {}, available=bool(coe),
                                        differ_own_all=sorted(own_dif)),
                    implied=dict(available=iv_rows is not None, file="implied_vol_%s.json" % date,
                                 fetched_at=(ivd or {}).get("fetched_at"), rows=iv_rows or []),
                    portfolio=dict(available=pr_rows is not None, file="portfolio_risk_%s.json" % date,
                                   rows=pr_rows or [], in_both=(prd or {}).get("in_both") or [],
                                   findings=(prd or {}).get("findings") or []),
                    changes=[c.strip() for c in changes],
                    dpv2=dict(basis="12-month at rRF + RPM (DP-V8)", flip_rows=len(flips), tickers=tks,
                              needed_rows=DPV2_MIN_ROWS, needed_tickers=DPV2_MIN_TICKERS,
                              stop=str(DPV2_STOP), sessions_left=left,
                              unscored=[dict(date=str(u[0]), ticker=u[1], conf=u[2], hint=u[3])
                                        for u in unscored],
                              rows=[dict(date=str(d), ticker=tk, conf=c, cls=cl, flip=f, source=s,
                                         r=rate_of.get(d)) for d, tk, c, cl, f, s in flips],
                              closed_9=dict(basis="12-month at 9% (closed by DP-V8)", rows=[
                                  dict(date=str(d), ticker=tk, conf=c, cls=cl, flip=f, source=s)
                                  for d, tk, c, cl, f, s in closed9], tickers=closed9_tks,
                                  unscored=[dict(date=str(u[0]), ticker=u[1], conf=u[2], hint=u[3])
                                            for u in closed9_un]),
                              closed=dict(basis="last-FY (closed by DP-V4)", rows=[
                                  dict(date=str(d), ticker=tk, conf=c, cls=cl, flip=f, source=s)
                                  for d, tk, c, cl, f, s in closed], tickers=closed_tks)),
                    book_free=[dict(ticker=t, pe=pe, band=b, div_yield=y, g_div=g, note=n)
                               for t, pe, b, y, g, n in bf],
                    identity_max_diff=worst, findings=findings)
    return "\n".join(L), snapshot, findings


# --------------------------------------------------------------------------- #
# Embed into the GENERATED report copy (value.bat step 5b, added 2026-10-14)
# --------------------------------------------------------------------------- #
#
# The report copy (tracker_with_registry.xlsx) is the file read as the final
# word, so the card belongs in it. Four rules, each with the failure it stops:
#
#   1. NEVER WHILE EXCEL HAS IT OPEN. Excel holds the file with a deny-write
#      share lock and keeps an owner file "~$<name>" beside it. Writing under
#      it either fails half-way or is silently overwritten when Excel next
#      saves. Both are checked; a stale owner file (Excel closed) is refused
#      too, with the instruction to delete it -- the 2026-08-04 one sat in the
#      root for ten weeks.
#   2. NEVER INTO THE MASTER. The master is manual entry only.
#   3. ONLY INTO TODAY'S COPY. build_near_miss_registry --emit-master-copy
#      rebuilds the copy from the master on every review run (and drops every
#      embedded sheet). If the copy's latest cohort is not the card's date, the
#      review has not run today: embedding would put today's card into
#      yesterday's report.
#   4. ATOMIC. Saved to a temporary file beside the copy, then swapped in with
#      os.replace, so a failure never leaves a half-written report copy.
#
# openpyxl does not keep Excel's cached formula results when it saves. The
# workbook is therefore flagged fullCalcOnLoad, and the Excel refresh (daily
# workflow step 6) belongs AFTER value.bat, not before it.

VC_SHEET = "Value Card"
VC_AFTER = ("Monitor Strip", "Actionable BUYs", "Near-Miss BUYs", "Signals")
MASTER_NAME = "claude_equity_bot_tracker.xlsx"


def _probe_write(path):
    """Open for writing and close at once. Excel's open denies other writers on
    Windows, so this raises PermissionError while the workbook is open."""
    fh = open(path, "r+b")
    fh.close()


def excel_holds(path):
    """(reason, detail) if Excel has, or appears to have, the workbook open;
    (None, None) when it is safe to write."""
    folder, base = os.path.split(os.path.abspath(path))
    owner = os.path.join(folder, "~$" + base)
    try:
        _probe_write(path)
    except PermissionError:
        return "IN USE", "Excel (or another program) has %s open. Close it, then re-run value.bat" % base
    if os.path.exists(owner):
        return "OWNER FILE", ("%s exists. If Excel is closed it is stale: delete it, then re-run"
                              % os.path.basename(owner))
    return None, None


def latest_cohort(wb):
    """Newest date in the Signals sheet's date column."""
    from build_actionable_registry import SIGNALS_SHEET, FIRST_DATA_ROW, COL, as_date
    ws = wb[SIGNALS_SHEET]
    best, blank = None, 0
    for (v,) in ws.iter_rows(min_row=FIRST_DATA_ROW, min_col=COL["date"], max_col=COL["date"],
                             values_only=True):
        d = as_date(v)
        if d is None:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        best = d if best is None or d > best else best
    return best


def _write_sheet(ws, snap):
    from openpyxl.styles import Alignment, Font, PatternFill
    f_title = Font(bold=True, size=13)
    f_sec = Font(bold=True, size=11)
    f_hdr = Font(bold=True, size=10)
    f_note = Font(italic=True, size=9, color="FF6B6B6B")
    fill_hdr = PatternFill("solid", fgColor="FFE7E6E1")
    fill_rob = PatternFill("solid", fgColor="FFDDEFD9")
    fill_frag = PatternFill("solid", fgColor="FFF6E7C8")
    top = Alignment(vertical="top", wrap_text=False)
    r = [1]

    def put(values, font=None, fill=None):
        for c, v in enumerate(values, start=1):
            cell = ws.cell(r[0], c, v)
            cell.alignment = top
            if font is not None:
                cell.font = font
            if fill is not None:
                cell.fill = fill
        r[0] += 1

    def gap():
        r[0] += 1

    d = snap["date"]
    put(["Value Card -- %s" % d], f_title)
    put(["as of %s | built by value_card.py from %s, %s, quote_dump.json and the master | "
         "COUNTERFACTUAL ONLY: modifies no gate, reads no outcome | advisory-only, no orders"
         % (d, snap["exhibit"], snap.get("log", "the signals log"))], f_note)
    gap()
    cv = snap["coverage"]
    put(["Coverage"], f_sec)
    put(["watchlist %d, classed %d, ROBUST %d | held %d, classed %d, ROBUST %d (%s) | "
         "today's directionals %d, classed %d (%s)" % (
             cv["watchlist"], cv["classed"], cv["robust"], cv["held"], cv["held_classed"],
             len(cv["held_robust"]), ", ".join(cv["held_robust"]) or "none",
             cv["directional"], len(cv["directional_classed"]),
             ", ".join(cv["directional_classed"]) or "none")])
    gap()
    if snap.get("basis"):
        put([snap["basis"]["line"]], f_sec)
        gap()
    put(["What changed since %s" % (snap.get("previous") or "(no earlier exhibit)")], f_sec)
    for line in (snap["changes"] or [snap.get("quiet") or "Nothing to compare."]):
        put([line])
    gap()
    hd = snap.get("headline") or {}
    put(["Decision card -- today's directionals, then held names (class on 12-month ROE, DP-V4, at "
         "r = rRF + RPM = %s%%, DP-V8: 10-year %s%% dated %s + %s%%)" % (
             fmt(hd.get("r")), fmt(hd.get("rrf")), hd.get("rrf_date") or "-", fmt(hd.get("rpm")))], f_sec)
    if snap.get("conf_caveat"):
        put([snap["conf_caveat"]], f_note)
    hdr = ["Ticker", "Held in", "Today", "Conf", "Executability", "Class (12-month, rRF + RPM)", "Ratio",
           "Edge to line", "Last-FY class", "Last-FY ratio", "P/E (12-month)", "Range low (r -/+2)",
           "Range high", "Robust", "Why fragile", "Implied g %", "DP-V2 gate (not applied)",
           "Would flip", "NO READ reason", "12-month ROE %", "Next report", "Sessions to report",
           "Context note", "Own r % (CAPM)", "Class at own r", "Ratio at own r", "Own r -2/0/+2",
           "Own r tag", "Class @9%", "Ratio @9%"]
    put(hdr, f_hdr, fill_hdr)
    for c in snap["card"]:
        detail = (c.get("robust_detail") or "").replace("FRAGILE", "").strip()
        tag = c["robust"] if c["robust"] != "—" else ""
        put([c["ticker"], c["account"] if c["held"] else "scout", c["signal"], c["conf"],
             c["executability"].replace("—", ""), c["cls"], c["ratio"], c.get("edge"),
             c.get("cls_lastfy") or "", c.get("ratio_lastfy"), c.get("pe_ttm"),
             c["lo"], c["hi"], tag, detail, c["g_impl"], c.get("dpv2_gate"),
             c.get("dpv2_flip") or "", c.get("no_read_reason") or "",
             c.get("ttm_roe_pct"), c.get("next_report") or "",
             c.get("sessions_to_report"), c.get("context_note") or "",
             c.get("own_r"), c.get("cls_own_r") or "", c.get("ratio_own_r"),
             "/".join(CLASS_LETTER.get(k, "-") for k in (c.get("own_r_classes") or [])),
             c.get("own_r_tag") or "", c.get("cls_9") or "", c.get("ratio_9")],
            fill=fill_rob if tag == "ROBUST" else (fill_frag if tag == "FRAGILE" else None))
    put(["Class: implied ROE at r = rRF + RPM (DP-V8) over 12-month ROE (SEC, point in time). Edge: "
         "distance to the nearest line (under %.2f, a 2-3%% price move can cross it). Range: r -/+ 2; ROBUST "
         "only if all three give one class. Last-FY: the basis before DP-V4, for reference."
         % EDGE_BORDERLINE], f_note)
    gap()
    put(["Under the hood -- SEC filings, last 12 months against the 12 months before"], f_sec)
    put(list(HOOD_SHEET_COLUMNS), f_hdr, fill_hdr)
    for c in snap["card"]:
        u = c.get("under_hood")
        if not u:
            continue
        put(hood_sheet_row(c["ticker"], u))
    gap()
    put(["Expectations -- Finnhub's ADJUSTED (non-GAAP) consensus, on its own basis; "
         "'class if met' is approximate and never the class"], f_sec)
    put(["Ticker", "Next report", "Sessions", "Consensus EPS (adj.)", "Beat estimate (of last 4)",
         "Adj. 12-month EPS", "Adj. 12-month EPS if met", "Change if met %", "Class if met (approx.)",
         "Ratio if met", "Note"], f_hdr, fill_hdr)
    for c in snap["card"]:
        e = c.get("expectations") or {}
        put([c["ticker"], c.get("next_report") or "", c.get("sessions_to_report"),
             e.get("eps_estimate"),
             ("%d of %d" % (e["beats"], e["reported"])) if e.get("beats") is not None else "",
             e.get("adj_ttm"), e.get("adj_ttm_if_met"), _p100(e.get("chg_if_met")),
             e.get("cls_if_met") or "", e.get("ratio_if_met"),
             e.get("why") or e.get("history_why") or ""])
    gap()
    ce = snap.get("cost_of_equity") or {}
    put(["Cost of equity (DP-V7 step 2) -- each name's own CAPM r beside the 9% class; CONTEXT ONLY, "
         "the headline class stays at 9% until a ruling moves it"], f_sec)
    if not ce.get("available"):
        put(["not available: value.bat step 7c did not write cost_of_equity_%s.json" % d], f_note)
    else:
        rr = ce.get("rrf") or {}
        put(["own r = rRF %s%% (%s, observed %s) + adjusted beta x RPM %s%%; the class reads rRF + RPM = %s%% "
             "(DP-V8). Betas estimated %s. Own r differs from the class: %s. The class differs from 9%%: %s."
             % (fmt(rr.get("pct")), rr.get("source") or rr.get("why"), rr.get("date") or "-",
                fmt(ce.get("rpm_pct")), fmt(ce.get("mkt_r_pct")), ce.get("beta_as_of") or "?",
                ", ".join(ce.get("differ_own") or []) or "none",
                ", ".join(ce.get("differ_level") or []) or "none")], f_note)
        put(["Ticker", "Beta (adj.)", "Beta (raw)", "R^2", "Returns (n)", "r CAPM %", "CI low %",
             "CI high %", "r DCF %", "Retention g %", "Payout %", "DCF - CAPM (points)", "Class @9%",
             "Class (rRF + RPM)", "Ratio (rRF + RPM)", "Class @own r", "Ratio @own r", "Own r -2/0/+2",
             "Own r tag", "Flags", "Note"], f_hdr, fill_hdr)
        for c in snap["card"]:
            x = c.get("cost_of_equity")
            if not x:
                continue
            dg = x.get("dcf") or {}
            ci = x.get("r_ci") or [None, None]
            put([c["ticker"], x["beta_adj"], x["beta_raw"], x["r2"], x["n"], x["r_capm"], ci[0], ci[1],
                 dg.get("r"), dg.get("g"), _p100(dg.get("payout")), x.get("dcf_minus_capm"),
                 x.get("cls_9") or "", x.get("cls_head") or "", x.get("ratio_head"), x.get("cls_own") or "",
                 x.get("ratio_own"), "/".join(CLASS_LETTER.get(k, "-") for k in (x.get("own_classes") or [])),
                 x.get("own_tag") or "", " ".join(x.get("flags") or []),
                 ("DCF: " + dg["why"]) if dg.get("why") else ""])
    gap()
    put(["Capital and credit (DP-V7 step 3) -- can it carry its debt, and does it earn its cost of "
         "capital? CONTEXT ONLY"], f_sec)
    put(["Ticker", "EBIT / interest", "EBITDA / interest", "Altman Z", "Zone", "Return on capital %",
         "Debt / capital %", "Band", "ROC band", "D/C band", "5-yr default %", "Market cap $B", "Debt $B",
         "w_d", "Spread %", "r_d %", "r_s %", "WACC %", "ROIC %", "ROIC - WACC", "EVA $B", "Hurdle %",
         "Growth adds value", "Shares y/y %", "Note"], f_hdr, fill_hdr)
    for c in snap["card"]:
        k = c.get("capital")
        if not k:
            continue
        if k.get("why"):
            put([c["ticker"]] + [""] * 23 + [k["why"]])
            continue
        put([c["ticker"], k["cov"], k["ebitda_cov"], k["z"], k["zone"] or "", k["roc"], k["dc"],
             k["band"] or "", k["roc_band"] or "", k["dc_band"] or "", k["default_5y"],
             None if k["e_mkt"] is None else k["e_mkt"] / 1e9, None if k["debt"] is None else k["debt"] / 1e9,
             k["w_d"], k["spread"], k["r_d"], k["r_s"], k["wacc"], k["roic"], k["eva_spread"],
             None if k["eva"] is None else k["eva"] / 1e9, k["hurdle"],
             "" if k["growth_ok"] is None else ("yes" if k["growth_ok"] else "NO"),
             _p100(k["shares_chg"]), "; ".join(k.get("notes") or [])])
    gap()
    imp = snap.get("implied") or {}
    put(["Market-implied move (FINC 5133 step 5, DP-V10) -- the options market's 5-day move and its "
         "P(|move| > 3%). CONTEXT ONLY; risk-neutral, not a forecast"], f_sec)
    if not imp.get("available"):
        put(["not available: value.bat step 7d did not write %s" % imp.get("file", "implied_vol_<date>.json")],
            f_note)
    else:
        put(["Ticker", "On card", "Horizon expiry", "Sessions", "IV %", "~30d expiry", "IV 30d %", "Term",
             "1 sd 5d %", "Band / sd", "P(|move| > 3%) %", "Note"], f_hdr, fill_hdr)
        for ir in imp.get("rows") or []:        # not `r`: put() keeps its row counter in r
            if not ir.get("ok"):
                put([ir["ticker"], "yes" if ir.get("card") else "", "", "", "", "", "", "", "", "", "",
                     ir.get("why") or ""])
                continue
            put([ir["ticker"], "yes" if ir.get("card") else "", ir["expiry"][:10], ir["sessions"],
                 100 * ir["iv"], ir["exp30"][:10], 100 * ir["iv30"], ir["term"], 100 * ir["sigma"],
                 ir["band_sigma"], 100 * ir["p"], ir.get("report_note") or ""])
    gap()
    prs = snap.get("portfolio") or {}
    put(["Portfolio risk per account (FINC 5133 step 8, DP-V13) -- today's holdings on 2 years of daily "
         "returns. CONTEXT ONLY; labels and weights, no dollar amounts"], f_sec)
    if not prs.get("available"):
        put(["not available: value.bat step 7e did not write %s" % prs.get("file", "portfolio_risk_<date>.json")],
            f_note)
    else:
        put(["Account", "Names", "Beta (card)", "Beta, whole account", "Sigma %", "Market R2 %", "Own beta",
             "N_eff", "Top-1", "Top-1 %", "Top-3 %", "Cash %", "Other %", "Div. ratio", "Returns",
             "Pairs rho >= 0.70"], f_hdr, fill_hdr)
        for pa in prs.get("rows") or []:        # not `r`: put() keeps its row counter in r
            put([pa["label"], pa["positions"], pa["beta_card"], pa["beta_card_cash"], _p100(pa["sigma_p"]),
                 _p100(pa["r2"]), pa["beta_hist"], pa["n_eff"], pa["top_name"] or "", _p100(pa["top_w"]),
                 _p100(pa["top3_w"]), _p100(pa["cash_share"]), _p100(pa.get("other_share")), pa["dr"], pa["n_obs"],
                 "; ".join("%s-%s %.2f" % (p["a"], p["b"], p["rho"]) for p in (pa["pairs"] or []))])
    gap()
    put(["Robustness -- every classed name: the cost-of-equity grid on the 12-month basis"], f_sec)
    put(["Ticker", "Class (rRF + RPM)", "Ratio", "Last-FY class", "Last-FY ratio", "r - 2", "r",
         "r + 2", "Edge", "Tag", "Own r %", "Own r -2", "Own r", "Own r +2", "Own r tag", "Class @9%",
         "Ratio @9%"], f_hdr, fill_hdr)
    rb = snap["robustness"]
    for t in sorted((t for t in rb if rb[t]["cls"] != "NO READ"),
                    key=lambda t: -(rb[t]["ratio"] or 0)):
        x = rb[t]
        put([t, x["cls"], x["ratio"], x.get("lastfy") or "", x.get("lastfy_ratio"),
             *x.get("r_classes", ["", "", ""]), x.get("edge"),
             x["tag"] + (" EDGE" if x.get("borderline") else ""),
             x.get("own_r"), *(x.get("own_r_classes") or ["", "", ""]), x.get("own_r_tag") or "",
             x.get("cls_9") or "", x.get("ratio_9")],
            fill=fill_rob if x["tag"] == "ROBUST" else fill_frag)
    gap()
    dp = snap["dpv2"]
    put(["DP-V2 counterfactual flip ledger -- COUNTS ONLY, no outcome read (%s)"
         % dp.get("basis", "last-FY")], f_sec)
    put(["flip rows %d of %d needed | tickers %d of %d (%s) | stop %s | sessions left %s | "
         "withdrawn, not extended, if unmet on the stop date" % (
             dp["flip_rows"], dp["needed_rows"], len(dp["tickers"]), dp["needed_tickers"],
             ", ".join(dp["tickers"]) or "none", dp["stop"], dp.get("sessions_left"))])
    put(["Date", "Ticker", "BUY conf", "Class that day", "Flip", "Source", "r that day %"], f_hdr, fill_hdr)
    for x in dp["rows"]:
        put([x["date"], x["ticker"], x["conf"], x["cls"], x["flip"], x["source"], x.get("r")])
    for x in dp.get("unscored", []):
        put([x["date"], x["ticker"], x["conf"], "UNSCORED (prior: %s)" % x["hint"],
             "not counted", "no exhibit that session"])
    c9 = dp.get("closed_9")
    if c9:
        put(["CLOSED by DP-V8 -- the 12-month ledger at r = 9%% (%d rows; %s). On the record, never pooled "
             "with the count above." % (len(c9["rows"]), ", ".join(c9["tickers"]) or "none")], f_note)
        for x in c9["rows"]:
            put([x["date"], x["ticker"], x["conf"], x["cls"], x["flip"], x["source"] + " (closed)"])
        for x in c9.get("unscored", []):
            put([x["date"], x["ticker"], x["conf"], "UNSCORED (prior: %s)" % x["hint"],
                 "not counted (closed)", "no exhibit that session"])
    cl = dp.get("closed")
    if cl:
        put(["CLOSED by DP-V4 -- the last-FY ledger (%d rows; %s). On the record, never pooled "
             "with the count above." % (len(cl["rows"]), ", ".join(cl["tickers"]) or "none")], f_note)
        for x in cl["rows"]:
            put([x["date"], x["ticker"], x["conf"], x["cls"], x["flip"], x["source"] + " (closed)"])
    gap()
    put(["Book-free reads -- context only"], f_sec)
    put(["Ticker", "P/E (12-month EPS)", "P/E band", "Div yield %",
         "Dividend-implied g %", "Note"], f_hdr, fill_hdr)
    for x in snap["book_free"]:
        put([x["ticker"], x["pe"], x["band"] or ("no P/E" if "different share classes" in (x.get("note") or "")
                                                  else "no positive eps"), x["div_yield"], x["g_div"],
             x["note"]])
    gap()
    idn = snap.get("identity", {})
    put(["Identity check"], f_sec)
    put(["implied_return's ratio = %.4f x P/E + %.4f/ROE (DEMANDING ~ P/E >= %.1f, UNDEMANDING ~ < %.1f) | "
         "%d names reconstructed, max diff %.3f | outside rounding bound: %s" % (
             idn.get("k", 0), G_BASE / (100.0 + G_BASE), idn.get("pe_demanding", 0),
             idn.get("pe_undemanding", 0), idn.get("checked", 0), idn.get("max_diff", 0),
             ", ".join(snap.get("identity_outside_bound") or []) or "none")])
    if snap.get("findings"):
        put(["FINDINGS: " + " | ".join(snap["findings"])], f_sec)
    # number formats and widths
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, float):
                cell.number_format = "0.00"
    widths = [8, 22, 9, 8, 26, 14, 8, 10, 13, 10, 10, 10, 10, 9, 14, 11, 12, 15, 40, 10, 12, 10, 40,
              10, 13, 10, 12, 10]
    from openpyxl.utils import get_column_letter
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A3"


def embed(snap, copy_path, master_path=None):
    """Write/refresh the Value Card sheet in the report copy. Returns
    (ok, message). Never raises for an expected refusal."""
    import openpyxl
    base = os.path.basename(copy_path).lower()
    if base == MASTER_NAME or (master_path and os.path.abspath(copy_path) == os.path.abspath(master_path)):
        return False, "REFUSED: %s is the MASTER. The card is embedded into the report copy only." % copy_path
    if not os.path.exists(copy_path):
        return False, "REFUSED: %s not found. Run run_daily_review.bat first." % copy_path
    why, detail = excel_holds(copy_path)
    if why:
        return False, "REFUSED (%s): %s." % (why, detail)
    wb = openpyxl.load_workbook(copy_path)            # data_only=False: keep formulas
    newest = latest_cohort(wb)
    if str(newest) != snap["date"]:
        wb.close()
        return False, ("REFUSED: the report copy's latest cohort is %s, the card's is %s -- "
                       "run_daily_review.bat has not rebuilt it for today." % (newest, snap["date"]))
    if VC_SHEET in wb.sheetnames:
        del wb[VC_SHEET]                              # replace, never stack
    ws = wb.create_sheet(VC_SHEET)
    _write_sheet(ws, snap)
    for after in VC_AFTER:
        if after in wb.sheetnames and after != VC_SHEET:
            target = wb.sheetnames.index(after) + 1
            wb.move_sheet(VC_SHEET, offset=target - wb.sheetnames.index(VC_SHEET))
            break
    try:
        wb.calculation.fullCalcOnLoad = True          # cached results are gone; recalc on open
    except AttributeError:
        pass
    tmp = copy_path + ".vc-tmp"
    try:
        wb.save(tmp)
        why, detail = excel_holds(copy_path)          # re-check: Excel may have opened it meanwhile
        if why:
            return False, "REFUSED (%s) at save time: %s. Nothing was changed." % (why, detail.rstrip("."))
        os.replace(tmp, copy_path)
    except PermissionError as e:
        return False, "REFUSED: could not replace %s (%s). Nothing was changed." % (copy_path, e)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return True, "EMBEDDED: sheet '%s' (%d card rows) written into %s for %s." % (
        VC_SHEET, len(snap["card"]), os.path.basename(copy_path), snap["date"])


# --------------------------------------------------------------------------- #
# Self-test (positive and negative cases)
# --------------------------------------------------------------------------- #

def _selftest():
    import tempfile
    fails = []

    def check(name, ok):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        if not ok:
            fails.append(name)

    # thresholds and flips
    check("2.00x is DEMANDING", klass(2.00) == "DEMANDING")
    check("1.9999x is NEUTRAL", klass(1.9999) == "NEUTRAL")
    check("1.50x is NEUTRAL", klass(1.50) == "NEUTRAL")
    check("1.4999x is UNDEMANDING", klass(1.4999) == "UNDEMANDING")
    check("no ratio is NO READ", klass(None) == "NO READ")
    check("DEMANDING BUY 74 flips ADMIT->REJECT", dpv2_flip("DEMANDING", 74) == "ADMIT->REJECT")
    check("DEMANDING BUY 75 does not flip", dpv2_flip("DEMANDING", 75) is None)
    check("UNDEMANDING BUY 65 flips REJECT->ADMIT", dpv2_flip("UNDEMANDING", 65) == "REJECT->ADMIT")
    check("UNDEMANDING BUY 64 does not flip", dpv2_flip("UNDEMANDING", 64) is None)
    check("NEUTRAL BUY 72 does not flip", dpv2_flip("NEUTRAL", 72) is None)
    check("NO READ BUY 70 does not flip", dpv2_flip("NO READ", 70) is None)

    # identity: NVDA 2026-10-14 as printed by implied_return
    nv = dict(px=223.70, bvps=9.44, roe=51.92)
    check("identity reproduces NVDA 2.72x", abs(ratio_from(**nv) - 2.72) < 0.02)
    eps = nv["roe"] / 100 * nv["bvps"]
    k = (R_BASE - G_BASE) / (100 + G_BASE)
    check("ratio == k*P/E + g/((1+g)ROE) exactly",
          abs(ratio_from(**nv) - (k * nv["px"] / eps + (0.03 / 1.03) / 0.5192)) < 1e-9)
    check("BVPS cancels: doubling BVPS and halving ROE leaves the P/E term unchanged",
          abs(k * nv["px"] / eps - k * nv["px"] / ((nv["roe"] / 2 / 100) * (nv["bvps"] * 2))) < 1e-9)
    check("NEGATIVE: non-positive ROE gives no ratio", ratio_from(100, 10, -5) is None)

    # decomposition sums to the total
    a = dict(px=210.57, bvps=8.01, roe=61.17)
    b = dict(px=218.16, bvps=9.44, roe=51.92)
    dec = decompose(a, b)
    check("price + filing == total move (rate 0 with no r_head: both at 9%)",
          abs(dec["price"] + dec["filing"] + dec["rate"] - (dec["r1"] - dec["r0"])) < 1e-12 and dec["rate"] == 0)
    dr = decompose(dict(a, r_head=9.0), dict(b, r_head=10.12))
    check("DP-V8: price + filing + rate == total; rate = the new r on the new inputs",
          abs(dr["price"] + dr["filing"] + dr["rate"] - (dr["r1"] - dr["r0"])) < 1e-12
          and abs(dr["rate"] - (ratio_from(b["px"], b["bvps"], b["roe"], 10.12)
                                - ratio_from(b["px"], b["bvps"], b["roe"], 9.0))) < 1e-12
          and abs(dr["price"] - dec["price"]) < 1e-12 and dr["rate"] > 0)

    # robustness on a synthetic record (DP-V4: the r grid on 12-month ROE)
    f = dict(ratio=140.99 / 84.2, roe=84.2, i7=94.97, i9=140.99, i11=187.02, ratio_lastfy=2.72)
    rb = robustness(f)
    check("DP-V4: an NVDA-like record on 12-month ROE is NEUTRAL, FRAGILE across r, and "
          "differs from its last-FY class", rb["base"] == "NEUTRAL" and rb["tag"] == "FRAGILE"
          and rb["r_flip"] and rb["basis_flip"] and rb["lastfy"] == "DEMANDING")
    f2 = dict(ratio=6.03, roe=10.76, i7=44.21, i9=64.87, i11=85.52)
    check("PWR-like record is ROBUST", robustness(f2)["tag"] == "ROBUST")
    f3 = dict(ratio=52.97 / 35.9, roe=35.9, i7=36.28, i9=52.97, i11=69.65)
    r3 = robustness(f3)
    check("a ratio within 0.05 of a line is EDGE (FTI 1.48 against 1.50)",
          r3["borderline"] and r3["edge_line"] == NEUTRAL_AT and r3["base"] == "UNDEMANDING")
    check("(III) on 12-month ROE reproduces implied_return's g for NVDA (6.95%)",
          abs(g_implied_pct(51.92, 23.70) - 6.95) < 0.01 and g_implied_pct(10.0, -1.0) is None)

    # Gordon solved for g
    g = dividend_implied_g(3.0)
    check("dividend-implied g at y=3% is (9-3)/1.03", abs(g - 6.0 / 1.03) < 1e-9)
    check("NEGATIVE: no yield gives no g", dividend_implied_g(0) is None)

    # F-10 (2026-11-18): section 5's share-class guard, on BRK.B's own numbers
    pe_b, src_b, why_b = book_free_pe(573.78, None, 0.01092)
    check("F-10 NEGATIVE: BRK.B's Schwab P/E 0.0109 (Class A eps, B price) -> no P/E, and it says why",
          pe_b is None and src_b == "Schwab 12m" and "different share classes" in why_b)
    check("F-10 NEGATIVE: the SEC route is guarded too (573.78 over 46,563.02)",
          book_free_pe(573.78, 46563.02, None)[0] is None)
    check("F-10: an ordinary P/E passes untouched (40.3, Schwab; 25.0, SEC)",
          book_free_pe(20.0, None, 40.3) == (40.3, "Schwab 12m", None)
          and book_free_pe(50.0, 2.0, 40.3) == (25.0, "SEC 12m", None))
    check("F-10: no EPS and no P/E -> none, with no reason", book_free_pe(10.0, None, None) == (None, "", None))

    # DP-V10 (step 5): panel 2f's rows
    d5 = dt.date(2026, 11, 18)

    def _ivn(exp, iv, p, sess=6):
        return {"ok": True, "why": None, "horizon": {"expiry": exp, "sessions": sess, "iv": iv},
                "ref30": {"expiry": "2026-12-18", "iv": 0.30}, "term_ratio": iv / 0.30,
                "sigma_5d": iv * (5 / 252.0) ** 0.5, "band_in_sigma": 0.03 / (iv * (5 / 252.0) ** 0.5),
                "p_breach": p}
    ivd5 = {"date": "2026-11-18", "fetched_at": "2026-11-18T14:30:00", "names": {
        "WMT": _ivn("2026-11-27", 0.40, 0.45), "SPY": _ivn("2026-11-27", 0.18, 0.25),
        "NKE": _ivn("2026-12-18", 0.35, 0.40, 20), "XYZ": {"ok": False, "why": "chain status FAILED"}}}
    earn5 = {"WMT": {"date": "2026-11-19", "hour": "bmo"}, "NKE": {"date": "2026-12-16", "hour": "amc"},
             "SPY": {"date": None}}
    rows5 = implied_rows(ivd5, earn5, {"WMT"}, d5)
    check("step 5: rows sort by P (highest first), no-reads last; '*' marks the card",
          [r["ticker"] for r in rows5] == ["WMT", "NKE", "SPY", "XYZ"] and rows5[0]["card"] and not rows5[2]["card"])
    check("step 5: a report inside the 5 sessions is flagged (WMT 11-19 bmo)",
          rows5[0]["report"] == "2026-11-19" and "11-19 bmo inside the 5 sessions" in rows5[0]["report_note"])
    check("step 5: a report after the 5 sessions but before the expiry is flagged as such (NKE 12-16)",
          rows5[1]["report"] == "2026-12-16" and "after the 5 sessions, before expiry" in rows5[1]["report_note"])
    check("NEGATIVE step 5: no file -> None; a file for another date -> None (never a stale read)",
          implied_rows(None, earn5, set(), d5) is None
          and implied_rows(dict(ivd5, date="2026-11-17"), earn5, set(), d5) is None)
    check("NEGATIVE step 5: a no-read keeps its reason and no number",
          rows5[3]["why"] == "chain status FAILED" and rows5[3]["p"] is None and rows5[3]["iv"] is None)

    # parsing real-format lines, then the end-to-end refusal paths
    tmp = tempfile.mkdtemp(prefix="value_card_selftest_")
    ex = "\n".join([
        "-" * 100, "1. INPUTS -- ROE is trailing eps over book value per share", "-" * 100,
        "    tk      anchor      BVPS  px(master)   drift      ROE     M/B  divY%  anc.age num.age  ROE basis",
        "  NVDA  2026-07-26      9.44      223.70  -1.01%   51.92%   23.70   0.44     0.9Q    2.9Q  Schwab last-FY",
        "   FTI  2026-06-30      8.12       69.76  -1.32%   28.33%    8.59   0.29     1.3Q    3.3Q  Schwab last-FY",
        "", "-" * 100, "1a. THE TWO ROE ROUTES", "-" * 100,
        "  NVDA   Q2      51.92%     104.27%   +52.34  EDGAR quarterly x4",
        "", "-" * 100, "4. (II) WHAT ROE MUST THE MARKET BELIEVE?   <-- the headline read", "-" * 100,
        "  NVDA   23.70     51.92%     94.97%    140.99%    187.02%                   2.72x",
        "   FTI    8.59     28.33%     36.28%     52.97%     69.65%                   1.87x",
        "", "-" * 100, "4b. (III) WHAT GROWTH MUST THE MARKET BELIEVE?", "-" * 100,
        "  NVDA   23.70   0.9797        5.13%          6.95%  g (III)",
        "", "-" * 100, "5. WHY", "-" * 100,
        "         PM NOT COMPUTED -- book equity is non-positive (-8.58B); M/B undefined", ""])
    p = os.path.join(tmp, "implied_return_2026-10-14.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(ex)
    rec, bl = parse_exhibit(p)
    check("parses section 1 with the vintage columns", rec.get("NVDA", {}).get("num_age") == 2.9)
    check("parses the EDGAR route", rec["NVDA"].get("roe_edgar") == 104.27)
    check("parses the class ratio and g", rec["NVDA"].get("ratio") == 2.72 and rec["NVDA"].get("g_impl") == 6.95)
    check("parses a blocked name", "PM" in bl)
    log = os.path.join(tmp, "signals_2026-10-14.log")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("x | [PHASE 3-C DRY RUN] [Roth IRA,Individual] [HELD] NVDA | Signal: BUY | "
                 "Confidence: 74% | Risk: APPROVED | Reason: x PER-ACCOUNT: Roth IRA=APPROVED; "
                 "Individual=REJECTED. | H1[]\n")
        fh.write("x | [PHASE 3-C DRY RUN] [Acct A,Acct B] [HELD] FTI | Signal: BUY | "
                 "Confidence: 68% | Risk: REJECTED | Reason: x PER-ACCOUNT: Acct A=REJECTED; "
                 "Acct B=REJECTED. | H1[]\n")
    s = parse_log(log)
    check("parses held, accounts and per-account", s["NVDA"]["held"] and
          executability(s["NVDA"]) == "PARTIAL (Roth IRA only)")
    # ---- DP-V4: a two-filer slim cache, point in time ----------------------
    bare = tempfile.mkdtemp(prefix="value_card_bare_")       # no cache at all
    with open(os.path.join(bare, "implied_return_2026-10-14.md"), "w", encoding="utf-8") as fh:
        fh.write(ex)

    def _qs(ends, vals, lag=30):
        out, prev = [], None
        for e, v in zip(ends, vals):
            s0 = (dt.date.fromisoformat(prev) + dt.timedelta(days=1)).isoformat() if prev else \
                (dt.date.fromisoformat(e) - dt.timedelta(days=90)).isoformat()
            out.append({"start": s0, "end": e, "val": v, "form": "10-Q", "accn": "a" + e,
                        "filed": (dt.date.fromisoformat(e) + dt.timedelta(days=lag)).isoformat()})
            prev = e
        return out
    nv_ends = ["2024-10-27", "2025-01-26", "2025-04-27", "2025-07-27",
               "2025-10-26", "2026-01-25", "2026-04-26", "2026-07-26"]
    ft_ends = ["2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30",
               "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]
    nvda = {"slim_version": 3, "facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": _qs(nv_ends, [19e9, 22e9, 19e9, 26e9,
                                                         31.91e9, 42.96e9, 58.32e9, 59.69e9])}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": _qs(nv_ends, [0.78, 0.89, 0.76, 1.08,
                                                                          1.30, 1.76, 2.39, 2.46])}},
        "Revenues": {"units": {"USD": _qs(nv_ends, [35e9, 39e9, 44e9, 47e9,
                                                    57e9, 68e9, 81e9, 90e9])}},
        "StockholdersEquity": {"units": {"USD": [{"end": "2026-07-26", "val": 229.0e9,
                                                  "filed": "2026-08-25"}]}}}}}
    fti = {"slim_version": 3, "facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": _qs(ft_ends, [0.2e9, 0.2e9, 0.2e9, 0.25e9,
                                                         0.28e9, 0.27e9, 0.30e9, 0.33e9], lag=24)}},
        "StockholdersEquity": {"units": {"USD": [
            {"end": "2026-03-31", "val": 3.20e9, "filed": "2026-04-24"},
            {"end": "2026-06-30", "val": 1.18e9 / 0.359, "filed": "2026-07-24"}]}}}}}
    os.makedirs(os.path.join(tmp, "valuation_cache"))
    # DP-V8: the headline r reads the 10-year yield dated before the session. 4.00% + 5.00%
    # = 9.00%, so every pre-DP-V8 expectation below holds unchanged at r = 9%.
    rrf_file = os.path.join(tmp, RRF_SERIES)

    def _series(pct):
        with open(rrf_file, "w", encoding="utf-8") as fh:
            json.dump({"source": "FRED DGS10", "fetched": "selftest",
                       "obs": [["2026-10-09", pct - 0.05], ["2026-10-13", pct], ["2026-10-14", pct + 0.4]]}, fh)
    _series(4.00)
    with open(os.path.join(tmp, "valuation_cache", "cik_map.json"), "w") as fh:
        json.dump({"NVDA": "0001045810", "FTI": "0001681459"}, fh)
    for cik, body in (("0001045810", nvda), ("0001681459", fti)):
        with open(os.path.join(tmp, "valuation_cache", "companyfacts_%s.json" % cik), "w") as fh:
            json.dump(body, fh)
    with open(os.path.join(tmp, "earnings_calendar_2026-10-14.json"), "w") as fh:
        json.dump([{"ticker": "NVDA", "date": "2026-11-17", "hour": "amc", "sessions": 24, "note": "",
                    "expectations": {"eps_estimate": 2.10, "beats": 4, "reported": 4, "adj_ttm": 7.0,
                                     "adj_ttm_if_met": 7.7, "chg_if_met": 0.10, "why": None}}], fh)
    txt, snap, _ = build(dt.date(2026, 10, 14), tmp, log, None, None)
    cn = {c["ticker"]: c for c in snap["card"]}
    check("end to end (DP-V4): NVDA is NEUTRAL on 12-month ROE, DEMANDING on last-FY, and BUY 74 "
          "does not flip", cn["NVDA"]["cls"] == "NEUTRAL" and cn["NVDA"]["cls_lastfy"] == "DEMANDING"
          and cn["NVDA"]["dpv2_flip"] is None and snap["card"][0]["ticker"] == "NVDA")
    check("end to end: FTI is UNDEMANDING on 12-month ROE and BUY 68 flips REJECT->ADMIT",
          cn["FTI"]["cls"] == "UNDEMANDING" and "FLIP REJECT->ADMIT" in txt)
    check("the basis line names the classes that moved off last-FY",
          "NVDA DEMANDING->NEUTRAL" in txt and "FTI NEUTRAL->UNDEMANDING" in txt)
    check("2b opens the hood: NVDA's 12-month EPS and its growth against a year earlier",
          "UNDER THE HOOD" in txt and abs(cn["NVDA"]["under_hood"]["growth"]["eps"]["ttm"] - 7.91) < 1e-9
          and cn["NVDA"]["under_hood"]["growth"]["eps"]["chg"] > 1.0)
    # ---- 2026-10-29: the cells the 10-28 sheet left blank ----
    def _u(eps_chg=0.1, ocf_ni=1.2, ocfm=0.15, loss=False, eq=100e9, le=1.5, la=0.6, cav=None,
           notes=()):
        return dict(caveat=cav, notes=list(notes),
                    growth=dict(eps=dict(ttm=2.0, chg=eps_chg), revenue=dict(chg=0.05),
                                q_eps=dict(chg=0.02)),
                    quality=dict(ocf_to_ni=ocf_ni, ocf_margin=ocfm, net_loss=loss, gross_margin=0.4,
                                 gross_margin_year_ago=0.38, op_margin=0.2, op_margin_year_ago=0.18),
                    balance=dict(equity=eq, negative_equity=eq is not None and eq <= 0,
                                 liab_to_equity=le, liab_to_assets=la, cash=1e9))
    rb = hood_sheet_row("BBWI", _u(eq=-1.056e9, le=None, la=1.2048,
                                   notes=["liabilities: derived as assets minus equity"]))
    check("sheet (BBWI): L/E blank, liabilities / assets 120%, and the note the sheet used to drop",
          rb[HOOD_SHEET_COLUMNS.index("Liabilities / equity")] is None
          and abs(rb[HOOD_SHEET_COLUMNS.index("Liabilities / assets %")] - 120.48) < 1e-9
          and rb[-1].startswith("negative book equity (deficit $1.06B): L/E not defined, see L/A")
          and rb[-1].endswith("liabilities: derived as assets minus equity"))
    rd = hood_sheet_row("DOW", _u(ocf_ni=None, ocfm=0.107, loss=True))
    check("sheet (DOW): a net loss leaves OCF/NI blank, shows OCF / revenue 10.7%, and says why",
          rd[HOOD_SHEET_COLUMNS.index("OCF / NI")] is None
          and abs(rd[HOOD_SHEET_COLUMNS.index("OCF / revenue %")] - 10.7) < 1e-9
          and "12-month net loss: OCF/NI not defined" in rd[-1])
    rs = hood_sheet_row("SND", _u(eps_chg=12.0))
    check("sheet (SND): a change beyond +/-300% prints as the card does, not as 1200",
          rs[HOOD_SHEET_COLUMNS.index("EPS y/y %")] == ">+300%" and growth_cell(-4.0) == "<-300%"
          and abs(growth_cell(0.2026) - 20.26) < 1e-9 and growth_cell(None) is None)
    rj = hood_sheet_row("JPM", _u(cav="bank: operating cash flow and liabilities/equity are not comparable"))
    check("sheet (JPM): a bank's OCF ratios and leverage stay blank, the caveat leads the note",
          all(rj[HOOD_SHEET_COLUMNS.index(k)] is None for k in
              ("OCF / NI", "OCF / revenue %", "Liabilities / equity", "Liabilities / assets %"))
          and rj[-1].startswith("bank:"))
    check("the sheet row and its header have the same width", len(rb) == len(HOOD_SHEET_COLUMNS))
    # ---- DP-V6 (2026-10-30): ROIC on 2b ----
    ri = HOOD_SHEET_COLUMNS.index("ROIC %")
    upm = dict(_u(eq=-7.94e9, le=None, la=1.2), roic=dict(
        roic=0.366, ebit=16.66e9, ebit_route="operating income", tax_basis="own 12-month effective rate",
        ic_basis="average of opening and closing", notes=[]))
    rpm = hood_sheet_row("PM", upm)
    check("ROIC (PM): 36.6% reads where ROE cannot (negative equity), with no note for a standard read",
          abs(rpm[ri] - 36.6) < 1e-9 and "ROIC:" not in rpm[-1])
    udw = dict(_u(), roic=dict(roic=0.010, ebit=0.43e9, ebit_route="pretax income + interest expense "
                               "(InterestExpenseDebt)", tax_basis="statutory fallback 25.5%",
                               ic_basis="average of opening and closing", notes=[]))
    check("ROIC (DOW): the note names the EBIT route and the 25.5% fallback",
          "ROIC: EBIT = pretax income + interest expense; tax statutory fallback 25.5%"
          in hood_sheet_row("DOW", udw)[-1])
    ujp = dict(_u(cav="bank: operating cash flow and liabilities/equity are not comparable"),
               roic=dict(roic=None, why="no 12-month operating income, and no pretax income with "
                         "interest to rebuild it"))
    check("ROIC (JPM): a bank's ROIC stays blank and adds no note beside the bank caveat",
          hood_sheet_row("JPM", ujp)[ri] is None and "ROIC:" not in hood_sheet_row("JPM", ujp)[-1])
    ugm = dict(_u(), roic=dict(roic=None, why="no current debt tag at 2026-09-30 (absence is not zero)"))
    check("ROIC (GM): no read is blank, and the note says why",
          hood_sheet_row("GM", ugm)[ri] is None and "ROIC: no current debt tag" in hood_sheet_row("GM", ugm)[-1])
    check("2b text carries the ROIC column and its legend",
          " ROIC " in txt and "ROIC (DP-V6)" in txt and "25.5%" in txt)
    check("2b text carries the OCF/rev and L/A columns and their legend",
          "OCF/rev" in txt and " L/A " in txt and "defined when equity is negative" in txt)
    check("2c: the consensus and the class if it is met (ratio / 1.10), labelled approximate",
          cn["NVDA"]["expectations"]["cls_if_met"] == "NEUTRAL"
          and abs(cn["NVDA"]["expectations"]["ratio_if_met"] - cn["NVDA"]["ratio"] / 1.10) < 1e-9
          and "APPROXIMATE" in txt)
    check("the identity check still reads implied_return's own (last-FY) ratio",
          snap["identity"]["checked"] == 2 and not snap["identity_outside_bound"])
    bs = TTMBasis(tmp)
    raw, _ = parse_exhibit(p)
    on = rebase(raw, bs, dt.date(2026, 7, 24), strict=False)["FTI"]
    before = rebase(raw, bs, dt.date(2026, 7, 24), strict=True)["FTI"]
    check("point in time: on the day FTI's 10-Q is filed the card reads it; the ledger (strictly "
          "before the session) does not", on["ttm_end"] == "2026-06-30" and before["ttm_end"] == "2026-03-31")
    fl, _ = dpv2_ledger([(dt.date(2026, 10, 15), "FTI", 68), (dt.date(2026, 10, 26), "FTI", 68)],
                        {dt.date(2026, 10, 15): {"FTI": "UNDEMANDING"},
                         dt.date(2026, 10, 26): {"FTI": "UNDEMANDING"}}, label=_label_ttm)
    check("ledger rows before DP-V4 are REBUILT, from it LIVE",
          [x[5] for x in fl] == ["rebuilt", "live"])
    tb, sb, fb = build(dt.date(2026, 10, 14), bare, log, None, None)
    cb = {c["ticker"]: c for c in sb["card"]}
    check("NEGATIVE: with no slim cache a name is NO READ and says why, never a last-FY fallback",
          cb["NVDA"]["cls"] == "NO READ" and (cb["NVDA"]["no_read_reason"] or "").startswith("no 12-month")
          and any("cik_map" in x for x in fb))
    try:
        build(dt.date(2026, 10, 15), tmp, log, None, None)
        check("NEGATIVE: a date with no exhibit refuses", False)
    except SystemExit as e:
        check("NEGATIVE: a date with no exhibit refuses", isinstance(e.code, tuple) and e.code[1] == 2)
    check("NEGATIVE: the report copy is refused as --tracker",
          main(["--date", "2026-10-14", "--root", tmp, "--log", log, "--tracker",
                os.path.join(tmp, REFUSED), "--md", os.path.join(tmp, "x.md")]) == 2)
    # ---- the embed: guards first, then the write ----
    import openpyxl
    copy = os.path.join(tmp, "tracker_with_registry.xlsx")
    wb = openpyxl.Workbook()
    wb.active.title = "Signals"
    wb["Signals"].cell(5, 1, dt.datetime(2026, 10, 14))
    wb["Signals"].cell(5, 2, "NVDA")
    wb["Signals"]["K5"] = "=1+1"                       # a formula must survive the embed
    wb.create_sheet("Monitor Strip")
    wb.create_sheet("How to Use")
    wb.save(copy)
    snap_j = json.loads(json.dumps(snap, default=str))
    ok, msg = embed(snap_j, copy)
    names = openpyxl.load_workbook(copy).sheetnames
    check("embed writes the sheet right after Monitor Strip",
          ok and names.index(VC_SHEET) == names.index("Monitor Strip") + 1)
    ok2, _ = embed(snap_j, copy)
    _vs = openpyxl.load_workbook(copy)[VC_SHEET]
    _hdr = [row for row in _vs.iter_rows(values_only=True) if row and row[0] == "Ticker"
            and "Liabilities / assets %" in row]
    check("the embedded sheet's 2b header carries the two new columns",
          len(_hdr) == 1 and "OCF / revenue %" in _hdr[0] and "ROIC %" in _hdr[0]
          and _hdr[0][len(HOOD_SHEET_COLUMNS) - 1] == "Notes")
    check("re-embedding replaces, never stacks",
          ok2 and openpyxl.load_workbook(copy).sheetnames.count(VC_SHEET) == 1)
    check("formulas in the copy survive the embed",
          openpyxl.load_workbook(copy)["Signals"]["K5"].value == "=1+1")
    check("no temporary file is left behind", not os.path.exists(copy + ".vc-tmp"))
    owner = os.path.join(tmp, "~$tracker_with_registry.xlsx")
    open(owner, "w").close()
    ok3, msg3 = embed(snap_j, copy)
    check("NEGATIVE: an Excel owner file refuses the write", not ok3 and "OWNER FILE" in msg3)
    os.remove(owner)
    global _probe_write
    real = _probe_write

    def _held(path):
        raise PermissionError(13, "in use")
    _probe_write = _held
    try:
        before = os.path.getmtime(copy)
        ok4, msg4 = embed(snap_j, copy)
        check("NEGATIVE: a workbook open in Excel refuses the write, file untouched",
              not ok4 and "IN USE" in msg4 and os.path.getmtime(copy) == before)
    finally:
        _probe_write = real
    stale = dict(snap_j, date="2026-10-15")
    ok5, msg5 = embed(stale, copy)
    check("NEGATIVE: a copy the review has not rebuilt today is refused", not ok5 and "latest cohort" in msg5)
    ok6, msg6 = embed(snap_j, os.path.join(tmp, "claude_equity_bot_tracker.xlsx"))
    check("NEGATIVE: the master is never written", not ok6 and "MASTER" in msg6)
    # ---- 2026-10-23: the context note --------------------------------------
    cx = {"ttm": {"PAA": {"no_read": "no TTM: no EPS tag"},
                  "DOW": {"eps_ttm": -4.0, "flags": ["STALE: last quarter ends 2026-03-31"]},
                  "SPY": {"no_read": "fund (no EPS)"}},
          "earn": {"DOW": {"date": "2026-10-22", "sessions": 0, "note": "INSIDE 5 SESSIONS"},
                   "SPY": {"note": "n/a (fund)"}}}
    check("a NO READ reason is not doubled ('TTM: no TTM:')",
          _ctx_cells(cx, "PAA")[4] == "no TTM: no EPS tag")
    check("the calendar flag and a TTM flag both print",
          _ctx_cells(cx, "DOW")[4] == "INSIDE 5 SESSIONS; TTM STALE: last quarter ends 2026-03-31")
    check("a fund says so once", _ctx_cells(cx, "SPY")[4] == "n/a (fund)")
    import rulings
    bk = rulings.RULINGS["DP-3C-bk"]
    mo = (bk.get("measurement_only") or ("ZZZZ",))[0]
    check("a DP-3C-bk name carries the thesis label while the ruling is open",
          not bk.get("open")
          or (thesis_label(mo) == THESIS_LABEL and THESIS_LABEL in _ctx_cells({}, mo)[4]))
    check("a name outside DP-3C-bk carries no label", thesis_label("AAPL") == "")
    check("the card prints the DP-3C-w confidence caveat (Phase 4a)",
          not conf_caveat() or ("conf  = " + conf_caveat()) in txt)
    check("the caveat changes no class or flip: NVDA still NEUTRAL, FTI still flips",
          cn["NVDA"]["cls"] == "NEUTRAL" and "FLIP REJECT->ADMIT" in txt)

    # ---- DP-V7 step 2 (2026-11-18): own r beside the 9% class -----------------
    check("DP-V7: with no cost_of_equity file, 2d and section 3 say 'not available', no own r",
          "not available for 2026-10-14 (value.bat step 7c" in txt and "own r: not available" in txt
          and cn["NVDA"]["own_r"] is None and snap["cost_of_equity"]["available"] is False
          and "not available for 2026-10-14 (value.bat step 7c" in tb)
    with open(os.path.join(tmp, "cost_of_equity_2026-10-14.json"), "w", encoding="utf-8") as fh:
        json.dump({"date": "2026-10-14", "rpm_pct": 5.0, "mkt_r_pct": 10.12, "rrf_for_9pct": 4.0,
                   "rrf": {"pct": 4.00, "date": "2026-10-13", "source": "FRED DGS10"},
                   "beta_source": {"as_of": "2026-10-14"},
                   "names": {"NVDA": {"beta_adj": 1.553, "beta_raw": 1.825, "se": 0.085, "r2": 0.48, "n": 499,
                                      "r_capm_pct": 12.885, "r_ci_pct": [12.32, 13.45], "flags": []},
                             "FTI": {"beta_adj": 1.017, "beta_raw": 1.026, "se": 0.087, "r2": 0.22, "n": 499,
                                     "r_capm_pct": 10.205, "r_ci_pct": [9.64, 10.77], "flags": ["DISAGREE"]}}}, fh)
    txt2, snap2, fnd2 = build(dt.date(2026, 10, 14), tmp, log, None, None)
    c2 = {c["ticker"]: c for c in snap2["card"]}
    same = all(c2[t][k] == cn[t][k] for t in ("NVDA", "FTI")
               for k in ("cls", "ratio", "robust", "lo", "hi", "dpv2_gate", "dpv2_flip", "edge"))
    check("DP-V7: the headline class, its 7/9/11 robustness, the DP-V2 gate and flip are unchanged by own r",
          same and snap2["robustness"]["NVDA"]["r_classes"] == snap["robustness"]["NVDA"]["r_classes"]
          and snap2["dpv2"]["rows"] == snap["dpv2"]["rows"] and "FLIP REJECT->ADMIT" in txt2
          and snap2["identity"] == snap["identity"])
    rec2 = rebase(parse_exhibit(p)[0], TTMBasis(tmp), dt.date(2026, 10, 14), strict=False)
    check("DP-V7: ratio_at(9%) IS i9 / 12-month ROE (M/B backed out of the exhibit's i9)",
          all(abs(ratio_at(rec2[t], R_BASE) - rec2[t]["ratio_9"]) < 1e-12 for t in ("NVDA", "FTI"))
          and all(abs(rec2[t]["ratio_9"] - rec2[t]["i9"] / rec2[t]["roe"]) < 1e-12 for t in ("NVDA", "FTI")))
    mbn = (140.99 * 1.03 - 3.0) / 6.0
    hand = ((mbn * (12.885 - 3.0) + 3.0) / 1.03) / rec2["NVDA"]["roe"]
    check("DP-V7: NVDA at own r 12.885%% by hand ((M/B (r-g) + g)/(1+g) / ROE = %.3f): DEMANDING, '12.9%% D*'" % hand,
          abs(c2["NVDA"]["ratio_own_r"] - hand) < 1e-9 and c2["NVDA"]["cls_own_r"] == "DEMANDING"
          and "12.9% D*" in txt2)
    check("DP-V7: NVDA's grid is own r -/+ 2 (10.885 / 12.885 / 14.885)",
          c2["NVDA"]["own_r_classes"] == [klass(ratio_at(rec2["NVDA"], x)) for x in (10.885, 12.885, 14.885)]
          and c2["NVDA"]["own_r_tag"] == ("ROBUST" if len(set(c2["NVDA"]["own_r_classes"])) == 1 else "FRAGILE"))
    check("DP-V7: FTI at own r 10.2% is NEUTRAL against UNDEMANDING at 9%, and its BUY still flips at 9%",
          c2["FTI"]["cls_own_r"] == "NEUTRAL" and c2["FTI"]["cls"] == "UNDEMANDING"
          and c2["FTI"]["dpv2_flip"] == "REJECT->ADMIT" and "10.2% N*" in txt2
          and c2["FTI"]["own_r_flags"] == ["DISAGREE"])
    ce2 = c2["NVDA"]["cost_of_equity"]
    check("DP-V8: the 2d record carries @9%, the class (rRF + RPM) and @own r",
          ce2["cls_9"] == "NEUTRAL" and ce2["cls_head"] == c2["NVDA"]["cls"] and ce2["cls_own"] == "DEMANDING"
          and abs(ce2["ratio_head"] - c2["NVDA"]["ratio"]) < 1e-12)
    check("DP-V7: 2d prints own r's rRF; section 3 counts the differences; no rRF mismatch note",
          "2d. COST OF EQUITY" in txt2 and "own r = rRF 4.00% (FRED DGS10, observed 2026-10-13) + adjusted beta"
          in txt2 and "re-run step 7c" not in txt2
          and "class at own r differs from the class: 2 (FTI U->N, NVDA N->D)." in txt2
          and snap2["cost_of_equity"]["available"] and snap2["cost_of_equity"]["differ_own_all"] == ["FTI", "NVDA"])
    check("DP-V7: the snapshot's robustness carries own r for every classed name",
          snap2["robustness"]["NVDA"]["own_r"] == 12.885 and snap2["robustness"]["FTI"]["cls_own_r"] == "NEUTRAL")
    check("DP-V7: no quotes -> the DCF estimate says why, never a number",
          ce2["dcf"]["r"] is None and ce2["dcf"]["why"] == "pays no dividend")
    # the course's retention example (Ch 9 slides 27-28): ROE 15%, payout 62% -> g 5.7%
    dg = dividend_growth_r({"divYield": 6.2, "lastPrice": 50.0}, 5.0, 15.0, 12.8)
    check("DCF: the course's ROE 15%%, payout 62%% gives g 5.7%% and r = 6.2%% x 1.057 + 5.7%% = %.2f%%"
          % (dg["r"] or 0), abs(dg["payout"] - 0.62) < 1e-12 and abs(dg["g"] - 5.7) < 1e-9
          and abs(dg["r"] - (6.2 * 1.057 + 5.7)) < 1e-9)
    check("NEGATIVE DCF: retention g at or above the CAPM r is not a constant growth rate (AAPL-like)",
          (dividend_growth_r({"divYield": 0.3, "lastPrice": 350.0}, 8.9, 118.0, 10.24)["why"] or "").startswith(
              "retention g 104.1% is not below the CAPM r 10.2%"))
    check("NEGATIVE DCF: a payout over 100% of EPS has negative retention (O-like)",
          (dividend_growth_r({"divYield": 5.59, "lastPrice": 58.08}, 1.44, 3.6, 7.24)["why"] or "").startswith("payout 225%"))
    check("NEGATIVE DCF: a fund, no dividend, no positive EPS, no CAPM r each say why",
          (dividend_growth_r({"is_etf": True, "divYield": 1.0, "lastPrice": 700}, None, None, 10.0)["why"] or "").startswith("fund")
          and dividend_growth_r({"divYield": 0.0, "lastPrice": 586}, 30.0, 10.0, 8.0)["why"] == "pays no dividend"
          and dividend_growth_r({"divYield": 4.2, "lastPrice": 31.4}, -5.6, 5.0, 9.4)["why"] == "no positive 12-month EPS"
          and (dividend_growth_r({"divYield": 6.2, "lastPrice": 50.0}, 5.0, 15.0, None)["why"] or "").startswith("no CAPM r"))
    check("NEGATIVE: ratio_at refuses r at or below g = 3% and a missing ROE; own_r_read needs a CAPM r",
          ratio_at(rec2["NVDA"], 3.0) is None and ratio_at(dict(rec2["NVDA"], roe=None), 9.0) is None
          and own_r_read(rec2["NVDA"], {"r_capm_pct": None}) is None and own_r_read(rec2["NVDA"], None) is None)
    snap2_j = json.loads(json.dumps(snap2, default=str))
    ok7, _ = embed(snap2_j, copy)
    _vs7 = openpyxl.load_workbook(copy)[VC_SHEET]
    _rows7 = [row for row in _vs7.iter_rows(values_only=True) if row and row[0]]
    _dc = [r_ for r_ in _rows7 if r_[0] == "Ticker" and "Executability" in r_]
    _ce = [r_ for r_ in _rows7 if r_[0] == "Ticker" and "r CAPM %" in r_]
    _nv = [r_ for r_ in _rows7 if r_[0] == "NVDA" and len(r_) > 6 and r_[5] == 12.885]
    check("DP-V7 sheet: the decision card ends with the own-r columns; a cost-of-equity block with NVDA",
          ok7 and len(_dc) == 1 and [x for x in _dc[0] if x][-7:-2] == ["Own r % (CAPM)", "Class at own r",
                                                                       "Ratio at own r", "Own r -2/0/+2", "Own r tag"]
          and len(_ce) == 1 and len(_nv) == 1 and _nv[0][15] == "DEMANDING")
    check("DP-V7: own r adds no finding", fnd2 == [])

    # ---- DP-V8 (2026-11-18): the headline r = rRF + RPM -------------------------
    sr = {"obs": [(dt.date(2026, 11, 13), 5.10), (dt.date(2026, 11, 16), 5.12), (dt.date(2026, 11, 17), 5.15)]}
    h18, h17 = headline_r(sr, dt.date(2026, 11, 18)), headline_r(sr, dt.date(2026, 11, 17))
    check("DP-V8: r is the yield dated BEFORE the session + 5.00 (11-18 reads 11-17's 5.15; 11-17 reads 11-16's)",
          abs(h18["r"] - 10.15) < 1e-12 and h18["rrf_date"] == dt.date(2026, 11, 17)
          and abs(h17["r"] - 10.12) < 1e-12 and not h18["stale"])
    check("DP-V8: an observation 8 days before the session is STALE; none before it is no r",
          headline_r(sr, dt.date(2026, 11, 25))["stale"] and headline_r(sr, dt.date(2026, 11, 13))["r"] is None
          and "no valuation_cache" in headline_r(None, dt.date(2026, 11, 18))["why"])
    _series(5.12)
    global load_buy_rows
    _real_lbr = load_buy_rows

    def _rows(tracker, since):                 # the master's BUY rows, without a workbook
        return [(dt.date(2026, 10, 14), "FTI", 68.0), (dt.date(2026, 10, 14), "NVDA", 74.0)]
    load_buy_rows = _rows
    import implied_vol as _iv                  # DP-V10: the file as implied_vol.py itself writes it
    _cd = dt.date(2026, 10, 14)
    _ch = _iv._chain(180.0, [(dt.date(2026, 10, 16), 2, {180.0: (70.0, 72.0)}),
                             (dt.date(2026, 10, 23), 9, {180.0: (48.0, 50.0)}),
                             (dt.date(2026, 11, 13), 30, {180.0: (44.0, 46.0)})])
    _spy = _iv._chain(600.0, [(dt.date(2026, 10, 23), 9, {600.0: (15.0, 16.0)})])
    _res, _f = _iv.build(_cd, ["NVDA", "FTI"], lambda w, d, lg: (
        {"NVDA": _ch, "SPY": _spy, "FTI": {"status": "FAILED"}}, {}), log=lambda *_: None)
    with open(os.path.join(tmp, "implied_vol_2026-10-14.json"), "w", encoding="utf-8") as fh:
        json.dump(_res, fh, default=_iv._jsonable)
    import portfolio_risk as _pr               # DP-V13: the file as portfolio_risk.py itself writes it
    _m = [0.004 * ((i * 7) % 5 - 2) for i in range(520)]
    _pc = {"SPY": _pr._candles(dt.date(2024, 9, 2), _pr._path(_m)),
           "NVDA": _pr._candles(dt.date(2024, 9, 2), _pr._path([1.5 * x for x in _m])),
           "FTI": _pr._candles(dt.date(2024, 9, 2), _pr._path([0.5 * x + 0.001 * ((i * 3) % 4 - 1.5)
                                                              for i, x in enumerate(_m)]))}
    _pf = [{"account_number": "11112222", "account_label": "Roth IRA", "cash_available": 1000.0,
            "portfolio_value": 11000.0, "positions": [_pr._pos("NVDA", 6000.0), _pr._pos("FTI", 4000.0)]}]
    _prr, _ = _pr.build(_cd, _pf, _pc, {"date": "2026-10-14", "names": {"NVDA": {"beta_adj": 1.40},
                                                                         "FTI": {"beta_adj": 0.80}}},
                        ("Roth IRA",))
    with open(os.path.join(tmp, "portfolio_risk_2026-10-14.json"), "w", encoding="utf-8") as fh:
        json.dump(_prr, fh, default=_pr._jsonable)
    try:
        txt3, snap3, fnd3 = build(dt.date(2026, 10, 14), tmp, log, None, "selftest-master")
    finally:
        load_buy_rows = _real_lbr
    c3 = {c["ticker"]: c for c in snap3["card"]}
    hand3 = ((mbn * (10.12 - 3.0) + 3.0) / 1.03) / rec2["NVDA"]["roe"]
    check("DP-V8: at rRF 5.12%% the headline r is 10.12%%; NVDA's ratio by hand %.4f, NEUTRAL" % hand3,
          abs(snap3["headline"]["r"] - 10.12) < 1e-12 and abs(c3["NVDA"]["ratio"] - hand3) < 1e-9 and c3["NVDA"]["cls"] == "NEUTRAL"
          and "r     = rRF + RPM = 10.12% (DP-V8): 10-year Treasury 5.12% dated 2026-10-13" in txt3)
    check("DP-V8: FTI moves UNDEMANDING -> NEUTRAL at 10.12%; its BUY 68 no longer flips; '@9%' keeps U",
          c3["FTI"]["cls"] == "NEUTRAL" and c3["FTI"]["cls_9"] == "UNDEMANDING" and c3["FTI"]["dpv2_flip"] is None
          and "UNDEMANDING*" in txt3 and "1 class(es) differ from the 9% class: FTI UNDEMANDING->NEUTRAL" in txt3)
    check("DP-V8: robustness is r -/+ 2 around 10.12 (8.12 / 10.12 / 12.12)",
          all(abs(x - y) < 1e-12 for x, y in zip(snap3["robustness"]["NVDA"]["r_grid"], (8.12, 10.12, 12.12)))
          and "8.12 / 10.12 / 12.12%" in txt3
          and snap3["robustness"]["NVDA"]["r_classes"] == [klass(ratio_at(rec2["NVDA"], x)) for x in (8.12, 10.12, 12.12)])
    check("DP-V8: g implied and the book-free P/E band read the headline r; section 6 adds its P/E lines",
          abs(c3["NVDA"]["g_impl"] - g_implied_pct(rec2["NVDA"]["roe"], rec2["NVDA"]["mb"], 10.12)) < 1e-12
          and "at the headline r = 10.12%% (DP-V8) the same lines are DEMANDING ~ P/E >= %.1f" % (
              DEMANDING_AT / (7.12 / 103.0)) in txt3)
    dp3 = snap3["dpv2"]
    check("DP-V8 ledger: rebuilt at 10.12% the FTI row does not flip; the 9% ledger is CLOSED and keeps it",
          dp3["basis"].startswith("12-month at rRF + RPM") and dp3["rows"] == []
          and [(x["ticker"], x["flip"], x["source"]) for x in dp3["closed_9"]["rows"]] == [("FTI", "REJECT->ADMIT", "rebuilt")]
          and [(x["ticker"], x["flip"]) for x in dp3["closed"]["rows"]] == [("NVDA", "ADMIT->REJECT")]
          and "CLOSED -- the 12-month ledger at r = 9% as it ran 2026-08-24 .. 2026-11-17 (DP-V8)" in txt3)
    check("DP-V8: an exhibit's own 9% identity check is unchanged by the headline r",
          snap3["identity"] == snap["identity"])
    os.remove(rrf_file)
    txt4, snap4, fnd4 = build(dt.date(2026, 10, 14), tmp, log, None, None)
    c4 = {c["ticker"]: c for c in snap4["card"]}
    check("NEGATIVE DP-V8: no 10-year series -> every class NO READ with the reason, and a FINDING; never 9%",
          all(c4[t]["cls"] == "NO READ" and (c4[t]["no_read_reason"] or "").startswith("no headline r")
              for t in ("NVDA", "FTI")) and any("never a 9% fallback" in x for x in fnd4)
          and "NO HEADLINE r" in txt4)
    _series(5.12)
    snap3_j = json.loads(json.dumps(snap3, default=str))
    ok8, _ = embed(snap3_j, copy)
    _rows8 = [row for row in openpyxl.load_workbook(copy)[VC_SHEET].iter_rows(values_only=True) if row and row[0]]
    _dc8 = [r_ for r_ in _rows8 if r_[0] == "Ticker" and "Executability" in r_]
    check("DP-V8 sheet: the class column says rRF + RPM, the card ends with @9%, the closed 9% ledger prints",
          ok8 and len(_dc8) == 1 and "Class (12-month, rRF + RPM)" in _dc8[0]
          and [x for x in _dc8[0] if x][-2:] == ["Class @9%", "Ratio @9%"]
          and any(str(r_[0]).startswith("CLOSED by DP-V8") for r_ in _rows8))
    # ---- DP-V7 step 3 (2026-11-18): capital and credit ----------------------------
    import corpfin as CF
    md_fu = dict(growth=dict(net_income=dict(ttm=1960.0 / 31.0 * 10.0, chg=0.10), eps=dict(ttm=10.0, chg=0.15),
                             revenue=dict(ttm=5000.0)),
                 balance=dict(assets=3610.0, liabilities=670.0, equity=1500.0),
                 roic=dict(ebit=400.0, debt=1000.0, equity=1500.0, roic=0.12, ic=2300.0,
                           tax_basis="own 12-month effective rate", end="2026-06-30"),
                 credit=dict(interest=50.0, da=100.0, current_assets=1610.0, current_liabilities=750.0,
                             retained_earnings=1740.0, notes=[]))
    sp_fx = {"series": {"BBB": {"obs": [["2026-10-13", 1.10], ["2026-10-14", 9.99]]}}}
    k1 = capital_read(md_fu, 31.0, {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    check("step 3: coverage 400/50 = 8.0x, EBITDA (400+100)/50 = 10.0x",
          k1["cov"] == 8.0 and k1["ebitda_cov"] == 10.0 and k1["why"] is None)
    check("step 3: Altman Z reproduces the course's MicroDrive (Web 24A: 4.465, SAFE) through the card's wiring",
          abs(k1["z"] - CF.altman_z(860.0, 1740.0, 400.0, 1960.0, 670.0, 5000.0, 3610.0)) < 1e-9
          and abs(k1["z"] - 4.465) < 0.001 and k1["zone"] == "SAFE"
          and abs(k1["e_mkt"] - 1960.0) < 1e-6 and k1["e_route"].startswith("price x"))
    check("step 3: ROC 400/2500 = 16% -> BBB, D/C 1000/2500 = 40% -> BBB; band BBB, 5y default 1.72%",
          abs(k1["roc"] - 16.0) < 1e-12 and abs(k1["dc"] - 40.0) < 1e-12 and k1["band"] == "BBB"
          and k1["default_5y"] == 1.72)
    w_hand = (1000.0 / 2960.0) * 5.10 * (1 - 0.255) + (1960.0 / 2960.0) * 10.0
    check("step 3: r_d = 4.00 + BBB 1.10 (dated BEFORE 10-14, not 10-14's 9.99); WACC by hand %.3f%%" % w_hand,
          abs(k1["r_d"] - 5.10) < 1e-12 and k1["spread_date"] == "2026-10-13" and abs(k1["wacc"] - w_hand) < 1e-9)
    check("step 3: ROIC 12% - WACC = spread; EVA = spread x capital; hurdle WACC/(1+WACC); both verdicts",
          abs(k1["eva_spread"] - (12.0 - w_hand)) < 1e-9 and abs(k1["eva"] - (12.0 - w_hand) / 100 * 2300.0) < 1e-9
          and abs(k1["hurdle"] - 100 * w_hand / 100 / (1 + w_hand / 100)) < 1e-9 and k1["creates"]
          and k1["growth_ok"])
    check("step 3: shares y/y = 1.10 / 1.15 - 1 = -4.35% (EPS grew faster than NI: buybacks)",
          abs(k1["shares_chg"] - (1.10 / 1.15 - 1)) < 1e-12)
    kb = capital_read(md_fu, 31.0, {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14), bank=True)
    check("NEGATIVE step 3: a bank reads none of it, and says why", kb["why"].startswith("bank") and kb["cov"] is None)
    brk = dict(md_fu, growth=dict(md_fu["growth"], eps=dict(ttm=40000.0, chg=0.1), net_income=dict(ttm=9.0e10, chg=0.1)))
    kk = capital_read(brk, 586.0, {"r_capm_pct": 8.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    check("NEGATIVE step 3: price and EPS on different share classes (BRK.B) -> no market cap, no Z, no WACC",
          kk["e_mkt"] is None and kk["z"] is None and kk["wacc"] is None
          and any("different share classes" in n for n in kk["notes"]))
    kn = capital_read(md_fu, 31.0, {"r_capm_pct": 10.0}, 4.00, {"series": {}}, dt.date(2026, 10, 14))
    check("NEGATIVE step 3: no spread for the band -> no r_d and no WACC (never the 2016 table)",
          kn["r_d"] is None and kn["wacc"] is None and any("no BBB spread" in n for n in kn["notes"]))
    k0 = capital_read(dict(md_fu, roic=dict(md_fu["roic"], debt=0.0)), 31.0, {"r_capm_pct": 10.0}, 4.00,
                      {"series": {}}, dt.date(2026, 10, 14))
    check("step 3: no debt -> WACC = r_s even without a spread", k0["w_d"] == 0.0 and k0["wacc"] == 10.0)
    kp = capital_read(dict(md_fu, roic=dict(md_fu["roic"], tax_basis="pass-through: no entity-level tax assumed")),
                      31.0, {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    check("step 3: a pass-through gets no tax shield in WACC (PAA)", kp["tax"] == 0.0
          and abs(kp["wacc"] - ((1000.0 / 2960.0) * 5.10 + (1960.0 / 2960.0) * 10.0)) < 1e-9)
    kneg = capital_read(dict(md_fu, roic=dict(md_fu["roic"], debt=100.0, equity=-300.0)), 31.0,
                        {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    knet = capital_read(dict(md_fu, credit=dict(md_fu["credit"], interest=None, interest_net=-50.0,
                                                 interest_tag="InterestIncomeExpenseNonoperatingNet")),
                        31.0, {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    knin = capital_read(dict(md_fu, credit=dict(md_fu["credit"], interest=None, interest_net=20.0)),
                        31.0, {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    check("step 3: only net interest -> coverage on a net COST (8.0x, labelled); none on net INCOME (NKE)",
          knet["cov"] == 8.0 and any("NET interest expense" in n for n in knet["notes"])
          and knin["cov"] is None and any("net interest INCOME" in n for n in knin["notes"]))
    kpm = capital_read(dict(md_fu, roic=dict(md_fu["roic"], debt=1000.0, equity=-200.0)), 31.0,
                       {"r_capm_pct": 10.0}, 4.00, sp_fx, dt.date(2026, 10, 14))
    check("step 3: negative book equity (PM) -> D/C 125% not used; the band reads ROC 50% alone (AAA)",
          kpm["band"] == "AAA" and kpm["dc_band"] is None and abs(kpm["dc"] - 125.0) < 1e-9
          and any("book equity is negative" in n for n in kpm["notes"]))
    check("NEGATIVE step 3: debt + equity not positive -> no band, said so",
          kneg["band"] is None and any("not positive" in n for n in kneg["notes"]))
    im3 = {r["ticker"]: r for r in snap3["implied"]["rows"]}
    check("step 5 e2e: with no implied_vol file, 2f says 'not available' and never guesses",
          "2f. MARKET-IMPLIED MOVE" in txt and "step 7d did not write implied_vol_2026-10-14.json" in txt
          and snap["implied"]["available"] is False)
    check("step 5 e2e: implied_vol.py's own file prints in 2f (NVDA 49%% at 10-23, P %.1f%%; FTI's reason)"
          % (100 * CF.p_breach(0.49, 5, 0.03)),
          snap3["implied"]["available"] and im3["NVDA"]["expiry"] == "2026-10-23"
          and abs(im3["NVDA"]["iv"] - 0.49) < 1e-12 and abs(im3["NVDA"]["p"] - CF.p_breach(0.49, 5, 0.03)) < 1e-12
          and im3["NVDA"]["card"] and im3["FTI"]["why"] == "chain status FAILED"
          and "NVDA  * 2026-10-23 (7)" in txt3 and "FTI   * chain status FAILED" in txt3)
    check("step 5 e2e: 2f changes no class, ratio or ledger (the DP-V8 checks above ran with it present)",
          c3["NVDA"]["cls"] == "NEUTRAL" and dp3["rows"] == [] and not any("2f" in f for f in fnd3))
    pr3 = {a["label"]: a for a in snap3["portfolio"]["rows"]}
    check("step 8 e2e: with no portfolio_risk file, 2g says 'not available' and never guesses",
          "2g. PORTFOLIO RISK PER ACCOUNT" in txt and "step 7e did not write portfolio_risk_2026-10-14.json" in txt
          and snap["portfolio"]["available"] is False)
    check("step 8 e2e: portfolio_risk.py's own file prints in 2g (Roth IRA beta 0.6 x 1.40 + 0.4 x 0.80 = 1.16)",
          snap3["portfolio"]["available"] and abs(pr3["Roth IRA"]["beta_card"] - 1.16) < 1e-12
          and abs(pr3["Roth IRA"]["beta_card_cash"] - 1.16 * 10 / 11) < 1e-12
          and "Roth IRA                   2    1.16" in txt3 and "11112222" not in txt3)
    check("step 8 v1.1: 'whole' replaces 'w/ cash' and the other-asset column prints",
          " whole " in txt3 and " other " in txt3 and "w/ cash" not in txt3 and pr3["Roth IRA"]["other_share"] == 0.0)
    check("step 8 e2e: 2g changes no class, ratio or ledger",
          c3["NVDA"]["cls"] == "NEUTRAL" and dp3["rows"] == [] and not any("2g" in f for f in fnd3))
    check("step 8: a file for another date is not read",
          portfolio_rows(dict(_prr, date="2026-10-13"), dt.date(2026, 10, 14)) is None
          and portfolio_rows(None, dt.date(2026, 10, 14)) is None)
    check("step 3 e2e: 2e prints, and a v3 slim cache says why instead of guessing",
          "2e. CAPITAL AND CREDIT (DP-V7 step 3)" in txt3 and "no valuation_cache" in txt3
          and c3["NVDA"]["capital"]["why"] and "slim v3" in c3["NVDA"]["capital"]["why"])
    print("SELFTEST %s (%d failed)" % ("PASSED" if not fails else "FAILED", len(fails)))
    return 1 if fails else 0


# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--tracker", help="the MASTER (logs\\claude_equity_bot_tracker.xlsx)")
    ap.add_argument("--log", help="logs\\signals_<date>.log")
    ap.add_argument("--quotes", default="quote_dump.json")
    ap.add_argument("--md", help="output exhibit (default value_card_<date>.md)")
    ap.add_argument("--json", help="also write a machine-readable snapshot here")
    ap.add_argument("--embed-from", help="a value_card_<date>.json snapshot to embed")
    ap.add_argument("--embed-into", help="the GENERATED report copy (tracker_with_registry.xlsx)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.embed_from or a.embed_into:
        if not (a.embed_from and a.embed_into):
            print("COULD NOT RUN: --embed-from and --embed-into go together.")
            return 2
        if not os.path.exists(a.embed_from):
            print("COULD NOT RUN: snapshot %s not found -- step 5 did not write it." % a.embed_from)
            return 2
        with open(a.embed_from, encoding="utf-8") as fh:
            snap = json.load(fh)
        ok, msg = embed(snap, a.embed_into, a.tracker)
        print("  " + msg)
        return 0 if ok else 2
    date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    if a.tracker and os.path.basename(a.tracker).lower() == REFUSED:
        print("REFUSED: %s is the GENERATED REPORT COPY, never an input. Pass the MASTER." % REFUSED)
        return 2
    log = a.log or os.path.join(a.root, "logs", "signals_%s.log" % date)
    if not os.path.exists(log):
        print("COULD NOT RUN: no signals log at %s" % log)
        return 2
    if a.tracker and not os.path.exists(a.tracker):
        print("COULD NOT RUN: master not found at %s" % a.tracker)
        return 2
    try:
        text, snap, findings = build(date, a.root, log, a.quotes, a.tracker)
    except SystemExit as e:
        msg, code = e.code if isinstance(e.code, tuple) else (str(e.code), 2)
        print("COULD NOT RUN: %s" % msg)
        return code
    md = a.md or os.path.join(a.root, "value_card_%s.md" % date)
    with open(md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# value_card exhibit\n\n```\n" + text + "\n```\n")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=1, default=str)
    print(text)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
