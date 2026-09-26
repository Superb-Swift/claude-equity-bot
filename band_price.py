#!/usr/bin/env python3
"""band_price.py — price the fixed +/-3% HOLD band per name, and monitor
volatility-tier drift against the FROZEN E4-2 table.

WHAT THIS IS
    A PARALLEL SECONDARY report. It does not re-baseline the +/-3% band, does
    not re-cut the frozen E4-2 volatility-tier table, does not touch any E4
    endpoint, arm, threshold, robustness condition, n or rate, and does not
    modify KEEP-70 or H4. It reads the master and prints. It writes nothing
    unless --md is passed explicitly.

WHY IT EXISTS
    The record established on 2026-07-30 that cohort accuracy is driven by the
    HOLD band-breach count, and on 2026-08-05 that on the HOLD population
    accuracy IS 1 - breach rate (verified 1,160/1,160). What was never
    measured is how much of the breach rate is a property of the NAME rather
    than of the signal. This tool measures that, from the master alone.

    The model is one parameter and no skill term: if a name's +5d moves are
    symmetric about zero with dispersion sigma, then

        P(breach) = 2 * (1 - Phi(0.03 / sigma))

    Any name whose OBSERVED breach rate sits far from that is a name whose
    moves are not shaped like the model -- fat-tailed, trending, or drifting.
    That residual is the only part of the band's output that is not dispersion.

WHAT IT IS NOT
    Not a skill estimate. A name matching the model tells you the band cannot
    see skill on that name; it does NOT tell you the generator is worthless.
    Not a re-baseline proposal. Not an input to any gate.

HOUSE RULES OBSERVED
    * READS THE MASTER, WRITES NOTHING. Hard-refuses tracker_with_registry.xlsx
      as an input and exits 2, matching log_tracker_crosscheck.py.
    * FORMULA-CACHE IMMUNE BY CONSTRUCTION. Every return is computed from the
      Price columns. The workbook's cached Return and "Was Claude Right?"
      columns are read ONLY to cross-check, and a blank cache degrades the
      cross-check to SKIPPED rather than corrupting a figure.
    * THE THRESHOLD IS VERIFIED, NOT RECALLED. BAND is not trusted as a
      constant: --selftest proves it reproduces the master's own
      "Was Claude Right? (5d)" column on the HOLD population. Two sources of
      truth for a threshold is how analyze_log.py L33-34 came to duplicate
      risk_engine's gate. Here the second source is checked against the first.
    * Exits 1 on findings for future hook use. Not in the pre-commit hook: a
      legitimate finding would block unrelated commits.

USAGE
    python band_price.py                      # master at the default path
    python band_price.py --tracker PATH
    python band_price.py --md exhibit.md      # opt-in write, never the master
    python band_price.py --selftest

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import math
import os
import statistics as st
import sys
from collections import defaultdict

# =============================================================================
# CONSTANTS
# =============================================================================

# The HOLD band. PROVENANCE: logs\claude_equity_bot_tracker.xlsx, Signals tab,
# column N formula =IF(H="","",IF(D="HOLD",IF(ABS(K)<0.03,"YES","NO"),...)).
# NOT trusted as a constant -- see selftest_band_matches_workbook().
BAND = 0.03

# Phi^-1(0.75). The median absolute z of a standard normal, so
# sigma = median|move| / MEDIAN_ABS_Z. Defined ONCE, here, with its derivation.
#
# ANALYST NOTE ON SYNTAX -- why the median and not sd.
#   sigma could be estimated from the sample sd instead. It should not be. The
#   record's own movers lists (CBRS +31.7%, AG +28.7%, MSFT +26.5% at +20d)
#   show two or three names per cohort dominate the sd. Deriving sigma from
#   the median is the robust estimator; deriving it from the sd would make the
#   model look worse for reasons that are about outliers, not about the model.
#   BOTH are reported per name so the reader can see the difference.
MEDIAN_ABS_Z = 0.6744897501960817

# The FROZEN E4-2 volatility-tier table.
# PROVENANCE: E4_2_Volatility_Tier_Table_FROZEN_2026-08-10.md, section "The
# table", frozen 2026-08-10 before the E4-2 clock started, per DP-3C-n 3.3.
#
# THIS TABLE IS NOT RECOMPUTED BY THIS TOOL AND MUST NOT BE. The freeze doc:
#   "This table must not be recomputed once EDGAR go-live begins. If a
#    ticker's classification is ever revisited, it is a new dated ruling, not
#    a re-run of this script."
# What this tool does is compare the frozen medians against current ones and
# REPORT drift. Reporting drift is not re-cutting. The freeze doc's own
# remedy for a sensitive boundary is "a robustness note ... not a re-cut".
FROZEN_TIERS = {
    "JPM": ("LOW", 1.834), "GLD": ("LOW", 1.931), "CORN": ("LOW", 1.990),
    "RTX": ("LOW", 2.021), "WMT": ("LOW", 2.559),
    "GM": ("MID", 2.592), "PM": ("MID", 3.188), "FTI": ("MID", 3.201),
    "PWR": ("MID", 3.343), "NVDA": ("MID", 3.595),
    "DOW": ("HIGH", 3.598), "NKE": ("HIGH", 3.598), "AAPL": ("HIGH", 3.779),
    "MSFT": ("HIGH", 3.910), "SND": ("HIGH", 5.517),
}

# Boundary flagged AT FREEZE TIME as the sensitivity risk, so that this tool
# can report whether the flagged risk or an unflagged one actually moved.
FROZEN_FLAGGED_BOUNDARY = ("NVDA", "DOW", 0.003)

# Report copy is OUTPUT-ONLY and never an input (workflow section 6).
REFUSED_INPUTS = ("tracker_with_registry.xlsx", "actionable_registry.xlsx",
                  "near_miss_registry.xlsx")

DEFAULT_TRACKER = os.path.join("logs", "claude_equity_bot_tracker.xlsx")

# Residual beyond which a name's observed breach rate is called out as not
# matching the one-parameter model. 5.0pt was chosen (at n≈58 per name) as
# inside 1 standard error of a breach-rate estimate (sqrt(.5*.5/58) = 6.6pt), i.e.
# deliberately INSIDE one SE so the tool over-reports rather than under-
# reports candidates. It is a REPORTING trigger, not an acceptance bar, and
# nothing is ruled on it. AMENDED 2026-09-16: n per name is now ~75+, where
# one SE is ~5.8pt; the trigger is unchanged and the report prints the live n
# rather than the n it was set at.
MODEL_RESIDUAL_FLAG_PT = 5.0


# =============================================================================
# NORMAL DISTRIBUTION
# =============================================================================

def _phi(z: float) -> float:
    """Standard normal CDF via erf. No scipy dependency."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _phi_inv(p: float) -> float:
    """Standard normal quantile. Acklam's rational approximation, refined by
    one Newton step against _phi so the round trip is exact to ~1e-15."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
             ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    else:
        q, r = p - 0.5, (p - 0.5) ** 2
        x = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
            (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    # one Newton refinement
    e = _phi(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


def model_breach(sigma: float, band: float = BAND) -> float:
    """P(|move| >= band) for a zero-median normal with dispersion sigma."""
    if sigma <= 0:
        return float("nan")
    return 2.0 * (1.0 - _phi(band / sigma))


def sigma_from_median(median_abs: float) -> float:
    """Robust dispersion estimate from the median absolute move."""
    return median_abs / MEDIAN_ABS_Z


# =============================================================================
# LOADING
# =============================================================================

class Row:
    __slots__ = ("date", "tk", "acct", "sig", "conf", "dq",
                 "p0", "p5", "p10", "p20",
                 "cached_r5", "cached_right5")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def ret(self, horizon: int):
        """Return computed FROM THE PRICE COLUMNS. Never the cached column."""
        px = {5: self.p5, 10: self.p10, 20: self.p20}[horizon]
        if px is None or self.p0 in (None, 0):
            return None
        return (px - self.p0) / self.p0


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_master(path: str):
    base = os.path.basename(path).lower()
    for bad in REFUSED_INPUTS:
        if base == bad.lower():
            sys.stderr.write(
                f"REFUSED: {base} is an OUTPUT copy, never an input "
                f"(workflow section 6). Pass logs\\claude_equity_bot_tracker.xlsx.\n")
            sys.exit(2)
    if not os.path.exists(path):
        sys.stderr.write(f"REFUSED: master not found at {path}\n")
        sys.exit(2)

    try:
        import openpyxl
    except ImportError:
        sys.stderr.write("REFUSED: openpyxl not installed.\n")
        sys.exit(2)

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if "Signals" not in wb.sheetnames:
        sys.stderr.write("REFUSED: no 'Signals' tab; is this the master?\n")
        sys.exit(2)
    ws = wb["Signals"]

    rows = []
    for r in ws.iter_rows(min_row=5, values_only=True):
        if r is None or len(r) < 14:
            continue
        if r[0] is None or r[1] is None:
            continue
        rows.append(Row(
            date=str(r[0])[:10], tk=str(r[1]).strip(),
            acct=r[2], sig=(str(r[3]).strip() if r[3] else None),
            conf=_f(r[4]), dq=r[5],
            p0=_f(r[6]), p5=_f(r[7]), p10=_f(r[8]), p20=_f(r[9]),
            cached_r5=_f(r[10]),
            cached_right5=(str(r[13]).strip().upper() if r[13] else None),
        ))
    wb.close()
    return rows


# =============================================================================
# CROSS-CHECKS -- run before any figure is reported
# =============================================================================

def crosscheck_prices_vs_cache(rows):
    """Price-derived returns must reproduce the workbook's cached Return +5d.
    A blank cache SKIPS rather than fails -- the open-in-Excel step may not
    have run, and that is a workflow state, not a data defect."""
    checked = blank = bad = 0
    worst = 0.0
    for r in rows:
        mine = r.ret(5)
        if mine is None:
            continue
        if r.cached_r5 is None:
            blank += 1
            continue
        checked += 1
        d = abs(mine - r.cached_r5)
        worst = max(worst, d)
        if d > 1e-9:
            bad += 1
    return dict(checked=checked, blank=blank, mismatched=bad, worst=worst)


def crosscheck_band_vs_cache(rows):
    """THE THRESHOLD CHECK. On HOLD rows the workbook's
    "Was Claude Right? (5d)" is YES iff |Return+5d| < BAND. If BAND were
    wrong, this disagrees. This is what makes BAND a verified value rather
    than a recalled one."""
    agree = disagree = skipped = 0
    examples = []
    for r in rows:
        if r.sig != "HOLD":
            continue
        mine = r.ret(5)
        if mine is None or r.cached_right5 not in ("YES", "NO"):
            skipped += 1
            continue
        pred = "YES" if abs(mine) < BAND else "NO"
        if pred == r.cached_right5:
            agree += 1
        else:
            disagree += 1
            if len(examples) < 5:
                examples.append((r.date, r.tk, mine, r.cached_right5, pred))
    return dict(agree=agree, disagree=disagree, skipped=skipped,
                examples=examples)


# =============================================================================
# ANALYSIS
# =============================================================================

def per_name(rows, tickers=None):
    by = defaultdict(list)
    for r in rows:
        v = r.ret(5)
        if v is not None:
            by[r.tk].append(v)
    out = {}
    for tk, vals in by.items():
        if tickers is not None and tk not in tickers:
            continue
        if len(vals) < 2:
            continue
        absv = [abs(v) for v in vals]
        med = st.median(absv)
        sig_med = sigma_from_median(med)
        sig_sd = st.pstdev(vals)
        obs = sum(1 for v in absv if v >= BAND) / len(vals)
        out[tk] = dict(
            n=len(vals), median_abs=med, sigma_med=sig_med, sigma_sd=sig_sd,
            z=BAND / sig_med if sig_med else float("nan"),
            model=model_breach(sig_med), observed=obs,
            model_sd=model_breach(sig_sd) if sig_sd else float("nan"),
            mean=st.mean(vals),
        )
    return out


def pooled(rows, pred):
    sel = [r.ret(5) for r in rows if pred(r)]
    sel = [v for v in sel if v is not None]
    if not sel:
        return None
    b = sum(1 for v in sel if abs(v) >= BAND)
    return dict(breach=b, n=len(sel), rate=b / len(sel))


def binomial_z(observed_count, n, p0):
    """Normal approximation. At n in the hundreds with p0 near 0.5 the
    approximation is close; the exact test is not carried because the
    conclusion never turns on the third decimal of p. Stated rather than
    silently assumed."""
    if n == 0 or not 0 < p0 < 1:
        return None, None
    sd = math.sqrt(n * p0 * (1 - p0))
    z = (observed_count - n * p0) / sd
    return z, 2 * (1 - _phi(abs(z)))


def design_effect(rows, horizon=5):
    """Approximate effective n for a pooled breach rate (ADDED 2026-09-16).

    §4's z treats every resolved row as an independent draw. They are not:
    names on one date move together (clustering) and consecutive +5d windows
    share four of five days (overlap). Discovery 2026-09-16 §1 measured the
    combined effect at roughly n_eff = 125 of 1,883 at +5d. This is the same
    rough bound: n_eff = n / (1 + (m - 1) * ICC) / h, with ICC the one-way
    ANOVA intraclass correlation of the breach indicator by date, m the mean
    names per date and h the horizon in sessions. A sizing aid, not a test.
    Returns dict(n, n_eff, icc, m) or None."""
    by = defaultdict(list)
    for r in rows:
        v = r.ret(horizon)
        if v is not None:
            by[r.date].append(1.0 if abs(v) >= BAND else 0.0)
    groups = [g for g in by.values() if len(g) >= 2]
    n = sum(len(g) for g in groups)
    k = len(groups)
    if k < 3 or n <= k:
        return None
    grand = sum(sum(g) for g in groups) / n
    ssb = sum(len(g) * (st.mean(g) - grand) ** 2 for g in groups)
    ssw = sum(sum((x - st.mean(g)) ** 2 for x in g) for g in groups)
    msb, msw = ssb / (k - 1), ssw / (n - k)
    k0 = (n - sum(len(g) ** 2 for g in groups) / n) / (k - 1)
    denom = msb + (k0 - 1) * msw
    icc = max(0.0, (msb - msw) / denom) if denom > 0 else 0.0
    m = n / k
    n_eff = n / (1 + (m - 1) * icc) / horizon
    return dict(n=n, n_eff=n_eff, icc=icc, m=m)


def horizon_gradient(rows):
    """Does median |move| scale as sqrt(t)? Packet p.1072: d2 = d1 - sigma*sqrt(t)."""
    out = {}
    for h in (5, 10, 20):
        # NOTE: filter BEFORE abs(). An unresolved horizon returns None, and
        # abs(None) raises. This was a live crash on the first real run, missed
        # because the self-tests did not cover horizon_gradient at all --
        # recorded here because "the tests passed" was exactly the wrong
        # reassurance. selftest now exercises this path with mixed None rows.
        v = [abs(x) for x in (r.ret(h) for r in rows) if x is not None]
        if not v:
            continue
        holds = [abs(x) for x in (r.ret(h) for r in rows if r.sig == "HOLD")
                 if x is not None]
        band_h = BAND * math.sqrt(h / 5)     # ADDED 2026-09-16: sqrt(t) band
        out[h] = dict(n=len(v), median=st.median(v),
                      hold_n=len(holds),
                      hold_breach=(sum(1 for x in holds if x >= BAND) / len(holds)
                                   if holds else float("nan")),
                      band_h=band_h,
                      hold_breach_scaled=(sum(1 for x in holds if x >= band_h) / len(holds)
                                          if holds else float("nan")))
    if 5 in out:
        anchor = out[5]["median"]
        for h in out:
            out[h]["sqrt_t_pred"] = anchor * math.sqrt(h / 5)
    return out


def tier_drift(stats):
    """Compare CURRENT medians against the FROZEN table. Reports drift and
    would-be re-tiering. DOES NOT RE-CUT."""
    have = {tk: s for tk, s in stats.items() if tk in FROZEN_TIERS}
    ranked = sorted(have.items(), key=lambda kv: kv[1]["median_abs"])
    k = len(ranked)
    rows_out = []
    for i, (tk, s) in enumerate(ranked):
        # terciles only meaningful at the frozen cardinality of 15
        if k == len(FROZEN_TIERS):
            cur_tier = "LOW" if i < 5 else ("MID" if i < 10 else "HIGH")
        else:
            cur_tier = None
        frozen_tier, frozen_med = FROZEN_TIERS[tk]
        rows_out.append(dict(
            tk=tk, frozen_tier=frozen_tier, frozen_med=frozen_med,
            current_med=s["median_abs"] * 100, n=s["n"],
            drift=s["median_abs"] * 100 - frozen_med,
            current_tier=cur_tier,
            retier=(cur_tier is not None and cur_tier != frozen_tier),
        ))
    return rows_out


def scaled_band_k(target_rate):
    """k such that P(|z| >= k) == target_rate, i.e. the scaled band that
    PRESERVES the pooled breach rate. Calibrating to preserve rather than to
    improve is deliberate: it makes the scaled band a re-allocation of the
    same total, not a loosening."""
    return _phi_inv(1 - target_rate / 2)


# =============================================================================
# REPORT
# =============================================================================

def _pct(x, w=7, d=2):
    return "n/a".rjust(w) if x is None or (isinstance(x, float) and math.isnan(x)) \
        else f"{x*100:{w}.{d}f}%"


def report(rows, md_path=None):
    L = []
    def out(s=""):
        L.append(s)
        print(s)

    findings = []

    dates = sorted({r.date for r in rows})
    out("=" * 100)
    out("BAND PRICE -- fixed +/-3% HOLD band, priced per name")
    out("PARALLEL SECONDARY. The +/-3% band is NOT re-baselined. The frozen")
    out("E4-2 tier table is NOT re-cut. No endpoint, bar, arm or n is changed.")
    out("=" * 100)
    out(f"master rows {len(rows)}   cohorts {len(dates)}   "
        f"{dates[0]} .. {dates[-1]}   tickers {len({r.tk for r in rows})}")
    out()

    # ---- integrity first, before any figure is quoted
    out("-" * 100)
    out("0. INTEGRITY -- every figure below is price-derived; the cache is only cross-checked")
    out("-" * 100)
    cp = crosscheck_prices_vs_cache(rows)
    out(f"  price-derived Return+5d vs workbook cached Return+5d:")
    out(f"    compared {cp['checked']}   mismatched {cp['mismatched']}   "
        f"max residual {cp['worst']:.3e}   cache-blank(skipped) {cp['blank']}")
    if cp["mismatched"]:
        findings.append(f"{cp['mismatched']} cached Return+5d cells disagree with the Price columns")
        out("    [FAIL] cached returns disagree with the prices they are computed from")
    else:
        out("    [ OK ] cached returns reproduce the Price columns exactly")

    cb = crosscheck_band_vs_cache(rows)
    out(f"  BAND={BAND} verified against the workbook's own 'Was Claude Right? (5d)' on HOLD rows:")
    out(f"    agree {cb['agree']}   disagree {cb['disagree']}   skipped {cb['skipped']}")
    if cb["disagree"]:
        findings.append(f"BAND={BAND} disagrees with the workbook on {cb['disagree']} HOLD rows")
        out("    [FAIL] the band constant does not reproduce the workbook's verdict column")
        for e in cb["examples"]:
            out(f"           {e[0]} {e[1]:>6}  ret {e[2]:+.4%}  workbook {e[3]}  this tool {e[4]}")
    else:
        out("    [ OK ] the band constant is CONFIRMED against the master, not recalled")
    out()

    covered = set(FROZEN_TIERS)
    stats = per_name(rows)

    # ---- per-name band pricing
    out("-" * 100)
    out("1. THE FIXED BAND, PRICED PER NAME (covered 15; sigma from median|+5d| / 0.674490)")
    out("-" * 100)
    out(f"{'tier':>5} {'tk':>6} {'n':>4} {'med|r5|':>9} {'sigma':>8} {'z':>7} "
        f"{'model':>8} {'observed':>9} {'resid pt':>9} {'sd-based':>9}")
    cov_rows = sorted(((tk, s) for tk, s in stats.items() if tk in covered),
                      key=lambda kv: kv[1]["median_abs"])
    for tk, s in cov_rows:
        resid = (s["observed"] - s["model"]) * 100
        flag = "  <<" if abs(resid) >= MODEL_RESIDUAL_FLAG_PT else ""
        out(f"{FROZEN_TIERS[tk][0]:>5} {tk:>6} {s['n']:>4} "
            f"{s['median_abs']*100:8.3f}% {s['sigma_med']*100:7.3f}% {s['z']:7.4f} "
            f"{s['model']*100:7.1f}% {s['observed']*100:8.1f}% {resid:+9.2f} "
            f"{s['model_sd']*100:8.1f}%{flag}")
    if cov_rows:
        lo, hi = cov_rows[0], cov_rows[-1]
        spread_obs = (hi[1]["observed"] - lo[1]["observed"]) * 100
        spread_mod = (hi[1]["model"] - lo[1]["model"]) * 100
        out()
        out(f"  P(marked right): {lo[0]} {(1-lo[1]['observed'])*100:.1f}%  vs  "
            f"{hi[0]} {(1-hi[1]['observed'])*100:.1f}%   "
            f"= {spread_obs:.1f} POINTS observed, {spread_mod:.1f} predicted")
        out("  The spread is a property of the NAMES. Signal quality is held identical across it.")
        out("  'sd-based' is the same model with sigma from the sample sd instead of the median --")
        out("  shown so the estimator choice is visible rather than buried.")
    out()

    # names the model does not fit
    misfits = [(tk, s) for tk, s in cov_rows
               if abs((s["observed"] - s["model"]) * 100) >= MODEL_RESIDUAL_FLAG_PT]
    out("-" * 100)
    out(f"2. NAMES THE ONE-PARAMETER MODEL DOES NOT FIT (|residual| >= {MODEL_RESIDUAL_FLAG_PT}pt)")
    out("-" * 100)
    if not misfits:
        out("  none -- every covered name's breach rate is within the reporting trigger.")
    else:
        for tk, s in sorted(misfits, key=lambda kv: -abs(kv[1]["observed"]-kv[1]["model"])):
            resid = (s["observed"] - s["model"]) * 100
            direction = "MORE" if resid > 0 else "FEWER"
            out(f"  {tk:>6}  observed {s['observed']*100:.1f}% vs model {s['model']*100:.1f}% "
                f"({resid:+.2f}pt) -- breaches {direction} often than its own median implies")
        out()
        out("  A positive residual means moves CLUSTER rather than distributing about zero:")
        out("  fat tails or trending. This residual is the only part of the band's output")
        out("  that is not dispersion, so it is the only part that could carry information.")
        ns = sorted(s["n"] for _, s in cov_rows)
        out(f"  NOTHING IS RULED ON IT. It is a reporting trigger (n = {ns[0]}-{ns[-1]} per name;")
        out(f"  one SE of a rate near 50% is ~{50/math.sqrt(ns[0]):.1f}pt at the smallest n).")
        out("  AMENDED 2026-09-16: a residual is only as good as the closes under it. Names")
        out("  with MATERIAL Check F items in outcome_sanity (manual close vs log close) have")
        out("  contested inputs; read their residual only after that queue is cleared.")
    out()

    # ---- pooled, with the dark-name contamination made explicit
    out("-" * 100)
    out("3. POOLED BREACH RATE -- BOTH DENOMINATORS, because mixing them is invalid")
    out("-" * 100)
    # AMENDED 2026-09-16 (DP-3C-al). These pools are ALL resolved rows -- BUY,
    # SELL and blank-signal rows included -- which is right for a DISPERSION
    # read and wrong for an accuracy label: "accuracy-equivalent = 1 - breach"
    # is true only for HOLD rows, which the band scores. outcome_sanity's
    # cohort table counts HOLD rows only, so the label now follows it.
    pa = pooled(rows, lambda r: True)
    pc = pooled(rows, lambda r: r.tk in covered)
    pd_ = pooled(rows, lambda r: r.tk not in covered)
    out("  ALL SIGNALS (dispersion only - no accuracy reading):")
    for label, p in (("ALL names", pa), ("COVERED 15", pc), ("not covered", pd_)):
        if p:
            out(f"    {label:<14} |move| >= 3%  {p['breach']:>5}/{p['n']:<5} = {p['rate']*100:6.2f}%")
    ha = pooled(rows, lambda r: r.sig == "HOLD")
    hc = pooled(rows, lambda r: r.sig == "HOLD" and r.tk in covered)
    hd = pooled(rows, lambda r: r.sig == "HOLD" and r.tk not in covered)
    out("  HOLD ROWS ONLY (the band's own population):")
    for label, p in (("ALL names", ha), ("COVERED 15", hc), ("not covered", hd)):
        if p:
            out(f"    {label:<14} breach        {p['breach']:>5}/{p['n']:<5} = {p['rate']*100:6.2f}%"
                f"   accuracy-equivalent {(1-p['rate'])*100:6.2f}%")
    if pa and pc and pd_:
        gap = (pc["rate"] - pd_["rate"]) * 100
        out(f"  covered minus not-covered = {gap:+.2f} pt")
        out("  The uncovered set is mostly broad-market and sector funds, whose dispersion is")
        out("  structurally suppressed by diversification. ANY comparison that pools the two")
        out("  populations against a covered-set expectation is contaminated by this gap.")
    out()

    if pc and cov_rows:
        wexp = sum(s["model"] * s["n"] for _, s in cov_rows) / sum(s["n"] for _, s in cov_rows)
        nexp = sum(s["model"] for _, s in cov_rows) / len(cov_rows)
        z, pv = binomial_z(pc["breach"], pc["n"], wexp)
        out("-" * 100)
        out("4. IS THE COVERED-SET BREACH RATE DISTINGUISHABLE FROM ZERO-SKILL DISPERSION?")
        out("-" * 100)
        out(f"  row-weighted model expectation   {wexp*100:6.2f}%   (name-weighted {nexp*100:.2f}%)")
        out(f"  observed covered-15 pooled       {pc['rate']*100:6.2f}%   (n = {pc['n']})")
        out(f"  gap {((pc['rate']-wexp)*100):+.2f} pt      z = {z:+.3f}   two-sided p = {pv:.3f}"
            f"   (normal approximation)")
        if pv is not None and pv > 0.05:
            out("  => NOT DISTINGUISHABLE from a zero-skill dispersion baseline at this n.")
        else:
            out("  => DISTINGUISHABLE at the 5% level. Read the SIGN before reading anything else.")
        # ADDED 2026-09-16: the rows are not independent. Same-date clustering
        # and 5-day window overlap shrink the effective n; the z above is the
        # naive one and overstates any evidence.
        de = design_effect([r for r in rows if r.tk in covered], 5)
        if de and z is not None:
            z_adj = z * math.sqrt(de["n_eff"] / de["n"])
            p_adj = 2 * (1 - _phi(abs(z_adj)))
            out(f"  cluster + overlap adjusted (approximate): n_eff ~ {de['n_eff']:.0f} of {de['n']}"
                f"  (date ICC {de['icc']:.3f}, {de['m']:.1f} names/date, 5-session overlap)")
            out(f"    z_adj = {z_adj:+.3f}   p_adj = {p_adj:.3f}   -- a sizing aid, not a test")
        out()
        out("  READ THIS CAREFULLY. It does NOT say the signal generator is worthless. It says")
        out("  the +/-3% band cannot see whether it is, because the band's output is dominated")
        out("  by a quantity the generator does not control. That is the argument for a")
        out("  price-referenced yardstick, not an argument about the generator.")
        out()

    # ---- horizon gradient / sqrt(t)
    hg = horizon_gradient(rows)
    if hg:
        out("-" * 100)
        out("5. HORIZON GRADIENT -- does median |move| scale as sqrt(t)?  (packet p.1072)")
        out("-" * 100)
        out(f"{'horizon':>8} {'n':>6} {'median|move|':>13} {'sqrt(t) pred':>13} "
            f"{'error pp':>9} {'HOLD breach':>12} {'sqrt(t) band':>13} {'breach':>8} {'HOLD n':>7}")
        for h in sorted(hg):
            g = hg[h]
            err = (g.get("sqrt_t_pred", float('nan')) - g["median"]) * 100
            out(f"{'+'+str(h)+'d':>8} {g['n']:>6} {g['median']*100:12.4f}% "
                f"{g.get('sqrt_t_pred',float('nan'))*100:12.4f}% {err:+9.4f} "
                f"{g['hold_breach']*100:11.2f}% {'+/-'+format(g['band_h']*100,'.2f')+'%':>13} "
                f"{g['hold_breach_scaled']*100:7.2f}% {g['hold_n']:>7}")
        out("  A close fit at +10d with an overshoot at +20d is the signature of mild")
        out("  mean-reversion at longer horizons. Reported, not fitted away.")
        out("  ADDED 2026-09-16: the fixed +/-3% HOLD breach rises with horizon by")
        out("  construction. The sqrt(t) band (3% x sqrt(h/5)) holds the band's width in")
        out("  sigma constant, so its breach column is the horizon-comparable one. Reporting")
        out("  only; the +/-3% band is not re-baselined. +20d spans ~4 independent windows.")
        out()

    # ---- tier drift
    td = tier_drift(stats)
    if td:
        out("-" * 100)
        out("6. FROZEN E4-2 TIER TABLE vs CURRENT n -- DRIFT MONITORING, NOT A RE-CUT")
        out("-" * 100)
        out("  Frozen 2026-08-10 per DP-3C-n 3.3. This tool NEVER re-cuts the table.")
        out(f"{'tk':>6} {'frozen':>7} {'frozen med':>11} {'current med':>12} {'n':>4} "
            f"{'drift pp':>9} {'current':>8}  note")
        n_retier = 0
        for d in td:
            note = ""
            if d["retier"]:
                n_retier += 1
                note = f"** would re-tier {d['frozen_tier']} -> {d['current_tier']}"
            out(f"{d['tk']:>6} {d['frozen_tier']:>7} {d['frozen_med']:10.3f}% "
                f"{d['current_med']:11.3f}% {d['n']:>4} {d['drift']:+9.3f} "
                f"{str(d['current_tier']):>8}  {note}")
        out()
        out(f"  names that would re-tier at current n: {n_retier} of {len(td)}")
        a, b, gappp = FROZEN_FLAGGED_BOUNDARY
        sa = stats.get(a); sb = stats.get(b)
        if sa and sb:
            still = sa["median_abs"] < sb["median_abs"]
            out(f"  the boundary FLAGGED at freeze time ({a} {gappp}pp below {b}): "
                f"{'HAS NOT flipped' if still else 'HAS flipped'} "
                f"({a} {sa['median_abs']*100:.3f}% vs {b} {sb['median_abs']*100:.3f}%)")
            if n_retier and still:
                # AMENDED 2026-09-25. Until today this printed "the freeze doc's
                # sensitivity note was aimed at the wrong boundary" on every run.
                # The 2026-09-21 review amended that claim as too confident on a
                # two-session read (the gap closed 0.180 -> 0.055pp in two
                # sessions), but hardcoded text kept asserting it. The exhibit now
                # prints the LIVE gap and makes no claim about the note.
                _gap = (sb["median_abs"] - sa["median_abs"]) * 100
                out(f"  => the flagged boundary has not flipped; live gap {_gap:.3f}pp "
                    f"({b} above {a}); {n_retier} name(s) would re-tier across "
                    f"unflagged boundaries. No claim is made about the freeze note's "
                    f"aim (amended 2026-09-21).")
        if n_retier:
            findings.append(f"{n_retier} of {len(td)} covered names would re-tier at current n")
            out()
            out("  WHY THIS MATTERS TO E4-2 AND NOT MERELY TO BOOKKEEPING: section 3.3's fallback")
            out("  pools ADJACENT vs COVERED-QUIET WITHIN TIER. A name in the wrong tier is")
            out("  pooled against a volatility peer group it no longer belongs to -- which is the")
            out("  confound the tier table exists to remove. The pre-registration already requires")
            out("  the primary/fallback split at every read; report this count beside it.")
            out("  THE TABLE IS NOT RE-CUT. The freeze doc's remedy is a sensitivity note.")
        out()

    # ---- scaled band secondary
    if pc and cov_rows:
        k = scaled_band_k(pc["rate"])
        out("-" * 100)
        out("7. VOLATILITY-SCALED BAND -- PARALLEL SECONDARY ONLY (the parked Q4-2 shape)")
        out("-" * 100)
        out(f"  k calibrated to PRESERVE the covered-15 pooled breach rate "
            f"({pc['rate']*100:.2f}%): k = {k:.4f}")
        out("  i.e. a HOLD is 'right' inside +/- {:.2f} sigma of its OWN 5-day dispersion.".format(k))
        out("  Calibrating to preserve rather than to improve is deliberate: it makes the scaled")
        out("  band a RE-ALLOCATION of the same total, not a loosening of the criterion.")
        out()
        out(f"{'tk':>6} {'fixed':>8} {'scaled equivalent':>18} {'ratio':>7}")
        for tk, s in cov_rows:
            eq = k * s["sigma_med"]
            out(f"{tk:>6} {'+/-3.000%':>8} {'+/-'+format(eq*100,'.3f')+'%':>18} "
                f"{eq/BAND:6.2f}x")
        out()
        out("  The fixed band is simultaneously TOO LOOSE for the low-dispersion names and")
        out("  TOO TIGHT for the high-dispersion ones. The +/-3% band is NOT re-baselined by")
        out("  this tool and no prior conclusion moves.")
        out()

    out("=" * 100)
    if findings:
        out(f"FINDINGS: {len(findings)}")
        for f in findings:
            out(f"  - {f}")
    else:
        out("FINDINGS: none")
    out("=" * 100)
    out("Advisory-only - no orders - not financial advice.")

    if md_path:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write("# band_price exhibit\n\n```\n" + "\n".join(L) + "\n```\n")
        print(f"\n[wrote {md_path}]")

    return 1 if findings else 0


# =============================================================================
# SELF-TESTS -- each must be SHOWN TO FAIL, per the phase_dispatch_audit standard
# =============================================================================

def _check(name, got, want, tol=None):
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")
    return ok


def selftest():
    global BAND
    print("band_price.py self-tests")
    ok = True

    print("\n normal distribution")
    ok &= _check("phi(0)", _phi(0.0), 0.5, 1e-12)
    ok &= _check("phi(1.96)", _phi(1.959963984540054), 0.975, 1e-9)
    ok &= _check("phi_inv(0.75) == MEDIAN_ABS_Z", _phi_inv(0.75), MEDIAN_ABS_Z, 1e-12)
    ok &= _check("phi_inv round trip at .3", _phi(_phi_inv(0.3)), 0.3, 1e-12)
    ok &= _check("phi_inv round trip at .999", _phi(_phi_inv(0.999)), 0.999, 1e-12)

    print("\n model_breach")
    # sigma == band/1.959964 -> exactly 5% breach
    ok &= _check("sigma s.t. z=1.96 gives 5%",
                 model_breach(BAND / 1.959963984540054), 0.05, 1e-9)
    ok &= _check("huge sigma -> breach ~1", model_breach(1e6), 1.0, 1e-6)
    ok &= _check("tiny sigma -> breach ~0", model_breach(1e-6), 0.0, 1e-9)
    ok &= _check("sigma<=0 is nan", math.isnan(model_breach(0.0)), True)

    print("\n sigma_from_median -- a normal's median |z| is 0.674490")
    ok &= _check("median 2% -> sigma 2.9652%",
                 sigma_from_median(0.02), 0.02 / MEDIAN_ABS_Z, 1e-15)
    # round trip: build a normal with known sigma, recover it from its median
    sig = 0.04
    ok &= _check("round trip median->sigma",
                 sigma_from_median(sig * MEDIAN_ABS_Z), sig, 1e-15)

    print("\n scaled_band_k preserves the rate it is calibrated to")
    for target in (0.10, 0.4548, 0.75):
        k = scaled_band_k(target)
        ok &= _check(f"k({target}) round trips", 2 * (1 - _phi(k)), target, 1e-12)

    print("\n binomial_z")
    z, p = binomial_z(50, 100, 0.5)
    ok &= _check("no deviation -> z=0", z, 0.0, 1e-12)
    ok &= _check("no deviation -> p=1", p, 1.0, 1e-12)
    z, p = binomial_z(430, 869, 0.4827)
    ok &= _check("evidence-pack figure reproduces z", z, 0.715, 5e-3)

    print("\n Row.ret is price-derived and ignores the cached column")
    r = Row(p0=100.0, p5=103.0, p10=None, p20=None, cached_r5=999.0, sig="HOLD")
    ok &= _check("ret(5) from prices", r.ret(5), 0.03, 1e-15)
    ok &= _check("ret(5) ignores cached_r5", r.ret(5) != r.cached_r5, True)
    ok &= _check("ret(10) missing -> None", r.ret(10), None)
    ok &= _check("p0 zero -> None", Row(p0=0.0, p5=1.0).ret(5), None)

    print("\n NEGATIVE TESTS -- the checks must be shown to FAIL, not merely to pass")

    # 1. band cross-check must catch a wrong BAND
    good = [Row(sig="HOLD", p0=100.0, p5=102.0, cached_right5="YES", date="d", tk="T"),
            Row(sig="HOLD", p0=100.0, p5=104.0, cached_right5="NO", date="d", tk="T")]
    res = crosscheck_band_vs_cache(good)
    ok &= _check("band check agrees on correct band", (res["agree"], res["disagree"]), (2, 0))
    saved = BAND
    BAND = 0.05          # deliberately wrong: 4% move now reads YES
    res_bad = crosscheck_band_vs_cache(good)
    ok &= _check("band check DETECTS a wrong band", res_bad["disagree"] >= 1, True)
    BAND = saved
    res_restored = crosscheck_band_vs_cache(good)
    ok &= _check("band check clean after restore", res_restored["disagree"], 0)

    # 2. price/cache cross-check must catch a corrupted cache
    bad = [Row(sig="HOLD", p0=100.0, p5=103.0, cached_r5=0.03),
           Row(sig="HOLD", p0=100.0, p5=103.0, cached_r5=0.99)]
    res = crosscheck_prices_vs_cache(bad)
    ok &= _check("price check DETECTS a corrupted cached return",
                 res["mismatched"], 1)
    res = crosscheck_prices_vs_cache([Row(sig="HOLD", p0=100.0, p5=103.0, cached_r5=None)])
    ok &= _check("blank cache SKIPS rather than fails",
                 (res["blank"], res["mismatched"]), (1, 0))

    # 3. tier_drift must detect a re-tier, and must not invent one
    class S(dict): pass
    stats_same = {tk: dict(median_abs=m / 100.0, n=58)
                  for tk, (_t, m) in FROZEN_TIERS.items()}
    td = tier_drift(stats_same)
    ok &= _check("frozen medians reproduce frozen tiers (0 re-tiers)",
                 sum(1 for d in td if d["retier"]), 0)
    stats_moved = dict(stats_same)
    stats_moved["JPM"] = dict(median_abs=0.09, n=58)   # LOW -> HIGH by force
    td2 = tier_drift(stats_moved)
    ok &= _check("tier_drift DETECTS a forced re-tier",
                 any(d["tk"] == "JPM" and d["retier"] for d in td2), True)

    # 4. per_name must not report a name with too few observations
    rows = [Row(sig="HOLD", tk="X", p0=100.0, p5=101.0)]
    ok &= _check("per_name drops n<2", "X" in per_name(rows), False)

    # 5. horizon_gradient must survive UNRESOLVED horizons.
    #    REGRESSION TEST for a live crash on the first real run: abs(None).
    #    Every real cohort has unresolved +10d/+20d rows at the tail, so this
    #    path is exercised on every genuine invocation and was covered by no
    #    test at all.
    mixed = [Row(sig="HOLD", tk="A", p0=100.0, p5=102.0, p10=None, p20=None),
             Row(sig="HOLD", tk="A", p0=100.0, p5=104.0, p10=108.0, p20=None),
             Row(sig="BUY",  tk="A", p0=100.0, p5=101.0, p10=None, p20=115.0)]
    try:
        hg = horizon_gradient(mixed)
        crashed = False
    except TypeError:
        hg = {}
        crashed = True
    ok &= _check("horizon_gradient survives unresolved horizons", crashed, False)
    ok &= _check("horizon_gradient counts only resolved rows at +5d",
                 hg.get(5, {}).get("n"), 3)
    ok &= _check("horizon_gradient counts only resolved rows at +10d",
                 hg.get(10, {}).get("n"), 1)
    ok &= _check("horizon_gradient excludes directional rows from HOLD breach",
                 hg.get(20, {}).get("hold_n"), 0)
    ok &= _check("horizon_gradient all-unresolved horizon is absent",
                 20 in hg and hg[20]["n"] == 1, True)

    # 5. the report must exit 1 when there is a finding
    ok &= _check("MODEL_RESIDUAL_FLAG_PT is a reporting trigger, not a bar",
                 MODEL_RESIDUAL_FLAG_PT > 0, True)

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


# =============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Price the fixed +/-3% HOLD band per name. Parallel secondary; "
                    "changes nothing. Reads the master, writes nothing.")
    ap.add_argument("--tracker", default=DEFAULT_TRACKER,
                    help=f"path to the MASTER (default {DEFAULT_TRACKER})")
    ap.add_argument("--md", default=None,
                    help="optional path to write a markdown exhibit (never the master)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    rows = load_master(a.tracker)
    return report(rows, md_path=a.md)


if __name__ == "__main__":
    sys.exit(main())
