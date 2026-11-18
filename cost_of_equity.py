#!/usr/bin/env python3
"""
cost_of_equity.py - DP-V7 step 2, REPORTING ONLY. Each watchlist name's cost of
equity by CAPM, from its own beta:  r = rRF + adjusted beta x RPM.

WHY (DP-V7, ruled by Rob 2026-11-18; claude/FINC5133_CourseReview_2026-11-18.md 4.1)
    The value card prices every name at one cost of equity, 9%. On the SML
    (Ch 6 slides 50-59) 9% is the required return of a beta-1.0 stock only when
    rRF + RPM = 9%, e.g. the course's rRF 4% + RPM 5%. This tool measures the two
    things the card has been assuming: each name's beta, and today's rRF. The
    card (value_card.py, panel 2d and section 3) prints the class at the name's
    own r BESIDE the headline class. AMENDED 2026-11-18 (DP-V8, Rob): the
    headline class itself now reads rRF + RPM, the beta-1.0 r, from the series
    this tool caches; own r stays context.

    Beta comes from beta_probe.name_betas (step 1, committed 0dd90ef), so the
    card and the probe can never disagree about how a beta is estimated.

WHAT IT READS
    today's signals log (the watchlist, via value_card.parse_log), Schwab daily
    candles (one call per name, through beta_probe.fetch_all) unless a fresh
    beta cache covers them, and FRED's public DGS10 series (the cached copy when
    FRED does not answer). No account data, no model call.

WHAT IT WRITES
    cost_of_equity_<date>.md and .json, valuation_cache\\beta_cache.json
    (today's runs only) and valuation_cache\\dgs10.json (the 10-year series,
    whenever FRED answers). No workbook, no prompt, no gate, no endpoint.
    AMENDED 2026-11-18 (DP-V8): dgs10.json is the HEADLINE class's rRF (value_card
    reads it for the card and every DP-V2 ledger date), so this step is no longer
    context only for the class: with no series at all the card is NO READ.

BARS - fixed here on 2026-11-18, before the first run (DP-V7)
    Ruled by Rob (2026-11-18)
      beta       2 years of DAILY simple returns vs SPY, Blume-adjusted
                 0.67 x raw + 0.33 (not printed in the course files); 3 years
                 of WEEKLY returns as the cross-check. Exactly beta_probe's.
      RPM        5.0%
    Set by Claude under DP-V7 (2026-11-18); Rob may change any before Part B
      rRF        FRED DGS10 (a 10-year Treasury, Ch 9 slide 23). STALE when the
                 observation used is more than 7 calendar days old.
                 RE-CUT 2026-11-18 (DP-V8, after the first live run): the latest
                 observation dated BEFORE the card's date (value_card.rrf_before),
                 not on or before it -- the yield known when the session opened,
                 one rule for the card and the rebuilt ledger. The first live
                 run read 11-16's 5.12% on 11-18, which the new rule also reads
                 while 11-17's is unpublished. The series is cached in
                 valuation_cache\\dgs10.json; a failed fetch reads the cache
                 (a FINDING). The $TNX fallback is REMOVED: a live quote is not
                 a yield dated before the session.
      CAPM r     rRF + adjusted beta x RPM, in percent.
      95% CI     the raw beta's +/- 1.96 SE carried through Blume (x 0.67) and
                 RPM: half-width = 5.0 x 0.67 x 1.96 x SE points of r.
      flags      SHORT    fewer than 250 daily returns (beta_probe's bar)
                 DISAGREE daily and weekly betas more than 2 SE apart (beta_probe's)
                 WIDE     the r 95% CI half-width exceeds 2.0 points: the
                          estimate is less certain than the card's own r +/- 2 grid
      cache      valuation_cache\\beta_cache.json is REUSED when its estimation
                 date is on or before the card's date (never a look-ahead), at
                 most 7 calendar days earlier, on the same bars, and covers every
                 name (a name that failed counts as covered until the cache
                 refreshes). Otherwise every name is re-fetched. A past date
                 never reads a later cache and never writes one. --refresh
                 forces a fetch.
      own r      the card's "own r" is the CAPM r ALONE. The course averages its
                 three estimates (Ch 9 slide 31), but here dividend growth is
                 defined for few names (value_card computes it, with the class's
                 own 12-month ROE) and the own-bond-yield method has no feed
                 (step 3 brings the cost of debt). An average would use a
                 different method for different names.

USAGE (cmd, repo root, venv active)
    python cost_of_equity.py --date 2026-11-18 --log logs\\signals_2026-11-18.log
    python cost_of_equity.py ... --refresh        re-fetch every beta
    python cost_of_equity.py --selftest           offline, fixtures; touches no repo file
    EXIT 0 = written.  1 = written, with FINDINGS (rRF fallback, stale or
         missing; a fetch error; feed sanity not PASS).  2 = could not run
         (no log, no SPY history); nothing is written on 2.
    value.bat step 7c runs it as CONTEXT: its exit code never changes the pass.

Advisory-only - no orders - not financial advice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import beta_probe as BP
import corpfin as CF

COE_VERSION = 1
CACHE_VERSION = 1
RPM_PCT = 5.0                       # DP-V7 (Rob, 2026-11-18)
RRF_STALE_DAYS = 7
BETA_MAX_AGE_DAYS = 7
WIDE_HALF_PP = 2.0                  # the card's own grid: own r +/- 2 points
CI_Z = 1.96
SERIES_FROM = dt.date(2024, 1, 1)   # dgs10.json keeps observations from here on
CACHE_DIR = "valuation_cache"
CACHE_NAME = "beta_cache.json"
FRED_URL = BP.FRED_URL
REFUSED = "tracker_with_registry.xlsx"


def bars():
    """The beta bars a cache must match to be reused."""
    return {"market": BP.MARKET, "daily_years": BP.DAILY_YEARS, "weekly_years": BP.WEEKLY_YEARS,
            "min_obs_daily": BP.MIN_OBS_DAILY, "min_obs_weekly": BP.MIN_OBS_WEEKLY,
            "disagree_z": BP.DISAGREE_Z, "blume": CF.BLUME_LABEL}


# ============================================================================ rRF
def parse_fred_series(text, since=SERIES_FROM):
    """[(date, percent), ...] oldest first, every numeric DGS10 row from `since`.
    FRED's header has been 'DATE,DGS10' and 'observation_date,DGS10'; a missing
    day is '.' or empty and is skipped."""
    import csv
    import io
    out = {}
    for row in csv.reader(io.StringIO(text or "")):
        if len(row) < 2 or not row[0][:4].isdigit():
            continue
        try:
            d = dt.date.fromisoformat(row[0][:10])
            v = float(row[1])
        except ValueError:
            continue
        if d >= since:
            out[d] = v
    return sorted(out.items())


def fetch_fred_text(timeout=20):
    try:
        import requests
    except ImportError:             # pragma: no cover - beta_probe.fetch_fred's fallback
        import urllib.request
        with urllib.request.urlopen(FRED_URL, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    resp = requests.get(FRED_URL, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def series_path(root):
    import value_card as VC
    return os.path.join(root, VC.RRF_SERIES)


def save_rrf_series(root, obs):
    os.makedirs(os.path.dirname(series_path(root)), exist_ok=True)
    tmp = series_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"source": "FRED DGS10", "url": FRED_URL,
                   "fetched": dt.datetime.now().isoformat(timespec="seconds"),
                   "obs": [[str(d), v] for d, v in obs]}, fh, indent=0)
    os.replace(tmp, series_path(root))


def get_rrf(date, root, fred_text_fn=fetch_fred_text):
    """The headline's own rule (DP-V8): the latest DGS10 observation dated
    before `date`, from a fresh FRED fetch (which rewrites the cached series)
    or, if FRED does not answer, the cached series. Returns {'pct', 'date',
    'source', 'stale', 'age_days', 'why', 'cached', 'series_written'}."""
    import value_card as VC
    why, written = None, False
    try:
        obs = parse_fred_series(fred_text_fn())
        if obs:
            save_rrf_series(root, obs)
            written = True
        else:
            why = "FRED answered with no numeric DGS10 row"
    except Exception as e:          # noqa: BLE001
        why = "FRED: %s: %s" % (type(e).__name__, e)
    series = VC.load_rrf_series(root)
    got = VC.rrf_before(series, date) if series else None
    if got is None:
        return {"pct": None, "date": None, "source": None, "stale": False, "age_days": None,
                "cached": not written, "series_written": written,
                "why": "; ".join(x for x in (why, "no 10-year yield dated before %s in %s" % (
                    date, VC.RRF_SERIES)) if x)}
    age = (date - got[0]).days
    return {"pct": got[1], "date": str(got[0]), "source": "FRED DGS10" + ("" if written else
            " (cached series, fetched %s)" % series.get("fetched")), "stale": age > RRF_STALE_DAYS,
            "age_days": age, "cached": not written, "series_written": written, "why": why}


# ============================================================================ cache
def cache_path(root):
    return os.path.join(root, CACHE_DIR, CACHE_NAME)


def load_cache(root):
    try:
        with open(cache_path(root), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def cache_usable(cache, date, tickers):
    """(usable, reason). The rule in the header, one test per clause."""
    if not cache:
        return False, "no beta cache"
    if cache.get("cache_version") != CACHE_VERSION:
        return False, "cache version %s, expected %s" % (cache.get("cache_version"), CACHE_VERSION)
    if cache.get("bars") != bars():
        return False, "cache was estimated on different bars"
    try:
        as_of = dt.date.fromisoformat(cache["as_of"])
    except (KeyError, TypeError, ValueError):
        return False, "cache has no estimation date"
    if as_of > date:
        return False, "cache estimated %s, after %s: a look-ahead" % (as_of, date)
    if (date - as_of).days > BETA_MAX_AGE_DAYS:
        return False, "cache estimated %s, more than %d days before %s" % (as_of, BETA_MAX_AGE_DAYS, date)
    have = set(cache.get("betas") or {}) | set(cache.get("errors") or {})
    missing = sorted(set(tickers) - have)
    if missing:
        return False, "cache lacks %s" % ", ".join(missing)
    return True, "cache estimated %s (%d day(s) before %s)" % (as_of, (date - as_of).days, date)


def save_cache(root, as_of, betas, errors):
    os.makedirs(os.path.join(root, CACHE_DIR), exist_ok=True)
    tmp = cache_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"cache_version": CACHE_VERSION, "as_of": str(as_of), "bars": bars(),
                   "written": dt.datetime.now().isoformat(timespec="seconds"),
                   "betas": betas, "errors": errors}, fh, indent=1, default=BP._jsonable)
    os.replace(tmp, cache_path(root))


# ============================================================================ per name
def name_record(b, rrf_pct, rpm_pct=RPM_PCT):
    """The card's inputs for one name, from beta_probe.name_betas output."""
    d = (b or {}).get("daily") or {}
    w = (b or {}).get("weekly") or {}
    if d.get("beta") is None:
        return {"r_capm_pct": None, "flags": [], "why": d.get("why") or "no daily beta"}
    half_b = CF.BLUME_WEIGHT_RAW * CI_Z * d["se"]
    rec = {"beta_raw": d["beta"], "beta_adj": d["adj"], "se": d["se"], "r2": d["r2"], "n": d["n"],
           "first": d.get("first"), "last": d.get("last"), "short": bool(d.get("short")),
           "weekly_raw": w.get("beta"), "weekly_adj": w.get("adj"), "weekly_n": w.get("n"),
           "z": b.get("z"), "cross": b.get("cross"),
           "beta_adj_ci": [d["adj"] - half_b, d["adj"] + half_b]}
    flags = []
    if rec["short"]:
        flags.append("SHORT")
    if rec["cross"] == "DISAGREE":
        flags.append("DISAGREE")
    if rrf_pct is None:
        rec.update(r_capm_pct=None, r_ci_pct=None, r_half_pp=None, why="no rRF")
    else:
        r = CF.capm(rrf_pct, rpm_pct, d["adj"])
        half_r = rpm_pct * half_b
        rec.update(r_capm_pct=r, r_ci_pct=[r - half_r, r + half_r], r_half_pp=half_r, why=None)
        if half_r > WIDE_HALF_PP:
            flags.append("WIDE")
    rec["flags"] = flags
    return rec


# ============================================================================ run
def tickers_from_log(path):
    import value_card as VC
    return sorted(VC.parse_log(path))


def build(date, today, tickers, root, refresh=False, fetch_fn=None, fred_text_fn=fetch_fred_text,
          log=print):
    """Returns (result dict, findings, cache_written) or raises SystemExit((msg, 2))."""
    fetch_fn = fetch_fn or BP.fetch_all
    want = sorted(set(tickers) | {BP.MARKET})
    cache = None if refresh else load_cache(root)
    usable, reason = cache_usable(cache, date, want)
    findings, wrote = [], False
    if usable:
        betas = {t: cache["betas"][t] for t in want if t in cache["betas"]}
        errors = {t: cache["errors"][t] for t in want if t in (cache.get("errors") or {})}
        src = {"from_cache": True, "as_of": cache["as_of"], "reason": reason, "fetched": 0}
    else:
        log("  beta cache not used (%s); fetching %d names" % ("--refresh" if refresh else reason, len(want)))
        try:
            _client, candles, errors = fetch_fn(want, date, log)
        except Exception as e:      # noqa: BLE001
            raise SystemExit(("Schwab client unavailable (%s: %s) and no usable beta cache (%s)"
                              % (type(e).__name__, e, reason), 2))
        if not candles.get(BP.MARKET):
            raise SystemExit(("no %s history: no beta can be estimated" % BP.MARKET, 2))
        betas = {t: BP.name_betas(candles[t], candles[BP.MARKET], date)
                 for t in want if candles.get(t)}
        betas = json.loads(json.dumps(betas, default=BP._jsonable))     # the cache's own shape
        src = {"from_cache": False, "as_of": str(date), "reason": "--refresh" if refresh else reason,
               "fetched": len(want)}
        if date == today:
            save_cache(root, date, betas, errors)
            wrote = True
        else:
            src["note"] = "past date: estimated on candles before %s; the cache was not written" % date
    if BP.MARKET not in betas:
        raise SystemExit(("no %s beta in the cache or the fetch" % BP.MARKET, 2))
    rrf = get_rrf(date, root, fred_text_fn)
    if rrf["pct"] is None:
        findings.append("no rRF (%s): no CAPM r, and the value card's headline class is NO READ (DP-V8)"
                        % rrf["why"])
    else:
        if rrf["cached"]:
            findings.append("FRED did not answer (%s): rRF read from the cached series" % rrf["why"])
        if rrf["stale"]:
            findings.append("rRF STALE: the latest DGS10 dated before %s is %s (%d days)"
                            % (date, rrf["date"], rrf["age_days"]))
    for t, why in sorted(errors.items()):
        findings.append("fetch error %s: %s" % (t, why))
    fs = BP.feed_sanity(betas)
    if fs["spy_self"] != "PASS":
        findings.append("feed sanity: SPY on itself is not beta 1 - the regression code is wrong")
    if fs["vti"] == "FEED SUSPECT":
        findings.append("feed sanity: VTI beta %.3f (R^2 %.2f) outside [%.2f, %.2f] / %.2f - FEED SUSPECT"
                        % (fs["vti_beta"], fs["vti_r2"], BP.VTI_BAND[0], BP.VTI_BAND[1], BP.VTI_MIN_R2))
    names = {}
    for t in sorted(set(tickers) | {BP.MARKET}):
        if t in betas:
            names[t] = name_record(betas[t], rrf["pct"])
        else:
            names[t] = {"r_capm_pct": None, "flags": [], "why": "no beta: %s" % errors.get(t, "no candles")}
    mkt = CF.capm(rrf["pct"], RPM_PCT, 1.0) if rrf["pct"] is not None else None
    res = {"coe_version": COE_VERSION, "date": str(date), "rpm_pct": RPM_PCT, "rrf": rrf, "mkt_r_pct": mkt,
           "rrf_for_9pct": 9.0 - RPM_PCT, "beta_source": src, "bars": dict(bars(), rpm_pct=RPM_PCT,
           rrf_stale_days=RRF_STALE_DAYS, beta_max_age_days=BETA_MAX_AGE_DAYS, wide_half_pp=WIDE_HALF_PP),
           "feed_sanity": fs, "fetch_errors": errors, "names": names, "findings": findings}
    return res, findings, wrote


def _f(x, spec="%.2f", none="-"):
    return none if x is None else spec % x


def render_md(res):
    L = []
    rrf, src, fs = res["rrf"], res["beta_source"], res["feed_sanity"]
    L.append("=" * 100)
    L.append("COST OF EQUITY -- DP-V7 step 2: each name's CAPM rate from its own beta. REPORTING ONLY.")
    L.append("Nothing here reaches the prompt, a gate or the headline class (DP-V1).")
    L.append("=" * 100)
    L.append("as of %s   rRF %s (%s%s)   RPM %.2f%% (Rob, 2026-11-18)   beta-1.0 r %s" % (
        res["date"], _f(rrf["pct"], "%.2f%%"), rrf.get("source") or rrf.get("why"),
        (", observed %s" % rrf["date"]) if rrf.get("date") else "", res["rpm_pct"],
        _f(res["mkt_r_pct"], "%.2f%%")))
    L.append("rRF + RPM = %s is the value card's headline r since DP-V8 (it was 9%%, which is rRF + RPM "
             "only at rRF %.2f%%)" % (_f(res["mkt_r_pct"], "%.2f%%"), res["rrf_for_9pct"]))
    if src["from_cache"]:
        age = (dt.date.fromisoformat(res["date"]) - dt.date.fromisoformat(src["as_of"])).days
        L.append("betas: REUSED from valuation_cache\\beta_cache.json, estimated %s on completed sessions "
                 "before it (%d day(s) old; refreshed after %d)" % (src["as_of"], age, BETA_MAX_AGE_DAYS))
    else:
        L.append("betas: FETCHED this run (%d names), estimated %s on completed sessions before it (%s)" % (
            src["fetched"], src["as_of"], src["reason"]))
    if src.get("note"):
        L.append("       " + src["note"])
    L.append("method: %s; 2y daily primary, 3y weekly cross-check (beta_probe.name_betas)" % CF.BLUME_LABEL)
    L.append("feed sanity: SPY on itself %s; VTI %s (beta %s, R^2 %s)" % (
        fs["spy_self"], fs["vti"], _f(fs.get("vti_beta"), "%.3f"), _f(fs.get("vti_r2"), "%.2f")))
    L.append("")
    L.append("  %-6s %7s %6s %6s %5s %4s %-22s %11s %6s %-8s %8s %-11s %s" % (
        "tk", "beta", "adj", "SE", "R^2", "n", "window", "weekly (n)", "z", "check", "r CAPM",
        "95% CI", "flags"))
    for t, x in sorted(res["names"].items()):
        if x.get("beta_raw") is None:
            L.append("  %-6s %s" % (t, x.get("why")))
            continue
        ci = x.get("r_ci_pct")
        L.append("  %-6s %7.3f %6.3f %6.3f %5.2f %4d %-22s %11s %6s %-8s %8s %-11s %s" % (
            t, x["beta_raw"], x["beta_adj"], x["se"], x["r2"], x["n"],
            "%s..%s" % (x.get("first") or "?", x.get("last") or "?"),
            "%s (%s)" % (_f(x.get("weekly_raw"), "%.2f"), x.get("weekly_n") or "-"),
            _f(x.get("z"), "%+.2f"), x.get("cross") or "-", _f(x.get("r_capm_pct"), "%.2f%%"),
            ("%.1f-%.1f%%" % tuple(ci)) if ci else "-", " ".join(x.get("flags") or []) or ""))
    L.append("")
    L.append("  beta: OLS slope of daily simple returns on SPY's; adj = 0.67 x beta + 0.33. r CAPM =")
    L.append("  rRF + adj x RPM. 95% CI: raw beta +/- 1.96 SE, through Blume and RPM. SHORT: under 250")
    L.append("  daily returns. DISAGREE: daily and weekly more than 2 SE apart. WIDE: the CI's half-width")
    L.append("  exceeds the card's +/- 2-point grid. R^2 near 0.3 is typical for one stock (Ch 25 s.40-41);")
    L.append("  one stock's beta is a noisy estimate of its future risk (Ch 25 s.47).")
    L.append("")
    L.append("=" * 100)
    L.append("FINDINGS: %d" % len(res["findings"]))
    for f in res["findings"]:
        L.append("  - " + f)
    L.append("=" * 100)
    L.append("No valuation asserted, no price target implied. Advisory-only - no orders - not financial advice.")
    return "# cost_of_equity exhibit\n\n```\n" + "\n".join(L) + "\n```\n"


def run(args, log=print, fetch_fn=None, fred_text_fn=fetch_fred_text, today=None):
    today = today or BP.market_today()
    date = dt.date.fromisoformat(args.date) if args.date else today
    if date > today:
        log("COULD NOT RUN: %s is after today (%s)" % (date, today))
        return 2
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        logp = args.log or os.path.join(args.root, "logs", "signals_%s.log" % date)
        if os.path.basename(logp).lower() == REFUSED:
            log("REFUSED: %s is the GENERATED REPORT COPY, never an input." % REFUSED)
            return 2
        if not os.path.exists(logp):
            log("COULD NOT RUN: no signals log at %s" % logp)
            return 2
        tickers = tickers_from_log(logp)
        if not tickers:
            log("COULD NOT RUN: %s names no ticker" % logp)
            return 2
    try:
        res, findings, wrote = build(date, today, tickers, args.root, args.refresh, fetch_fn,
                                     fred_text_fn, log)
    except SystemExit as e:
        msg = e.code[0] if isinstance(e.code, tuple) else str(e.code)
        log("COULD NOT RUN: %s" % msg)
        return 2
    stem = args.out or os.path.join(args.root, "cost_of_equity_%s" % date)
    with open(stem + ".md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_md(res))
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=BP._jsonable)
    n_r = sum(1 for x in res["names"].values() if x.get("r_capm_pct") is not None)
    log("cost_of_equity %s: rRF %s (%s), %d of %d names with a CAPM r; betas %s%s; findings %d" % (
        date, _f(res["rrf"]["pct"], "%.2f%%"), res["rrf"].get("source") or "none", n_r, len(res["names"]),
        "reused" if res["beta_source"]["from_cache"] else "fetched",
        ", cache written" if wrote else "", len(findings)))
    log("wrote %s.md and %s.json" % (stem, stem))
    return 1 if findings else 0


# ============================================================================ selftest
def selftest():
    import random
    import shutil
    import tempfile
    import trading_calendar as TC
    checks = []

    def ok(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1-9 rRF (DP-V8): the latest DGS10 dated BEFORE the date, from a cached series
    csv_a = "observation_date,DGS10\n2023-12-29,3.88\n2026-11-13,5.10\n2026-11-16,5.12\n2026-11-17,.\n2026-11-18,5.20\n"
    sa = parse_fred_series(csv_a)
    ok("FRED series: '.' skipped, rows before 2024 dropped, oldest first",
       sa == [(dt.date(2026, 11, 13), 5.10), (dt.date(2026, 11, 16), 5.12), (dt.date(2026, 11, 18), 5.20)])
    ok("FRED series: the older 'DATE' header parses too",
       parse_fred_series("DATE,DGS10\n2026-11-16,5.12\n") == [(dt.date(2026, 11, 16), 5.12)])
    today = dt.date(2026, 11, 18)
    rr_root = tempfile.mkdtemp(prefix="coe_rrf_")
    try:
        g = get_rrf(today, rr_root, lambda: csv_a)
        ok("rRF on 11-18 is 11-16's 5.12% (dated BEFORE the session; 11-18's own 5.20 is not used)",
           g["pct"] == 5.12 and g["date"] == "2026-11-16" and g["series_written"] and not g["cached"]
           and not g["stale"], str(g["pct"]))
        g = get_rrf(dt.date(2026, 11, 19), rr_root, lambda: csv_a)
        ok("rRF on 11-19 is 11-18's 5.20%", g["pct"] == 5.20 and g["date"] == "2026-11-18")
        g = get_rrf(dt.date(2026, 12, 2), rr_root, lambda: csv_a)
        ok("rRF: an observation 14 days old is STALE", g["stale"] and g["age_days"] == 14 and g["pct"] == 5.20)

        def down():
            raise OSError("blocked")
        g = get_rrf(today, rr_root, down)
        ok("FRED down: the cached series answers, marked cached, the same 5.12%",
           g["pct"] == 5.12 and g["cached"] and not g["series_written"] and "FRED: OSError" in g["why"]
           and "cached series" in g["source"])
        g = get_rrf(dt.date(2026, 11, 13), rr_root, down)
        ok("NEGATIVE: no observation dated before 11-13 in the series -> no rRF", g["pct"] is None
           and "no 10-year yield dated before 2026-11-13" in g["why"])
        empty = tempfile.mkdtemp(prefix="coe_rrf0_")
        g = get_rrf(today, empty, down)
        ok("NEGATIVE: FRED down and no cached series -> no rRF, never a quote", g["pct"] is None)
        shutil.rmtree(empty, ignore_errors=True)
        import value_card as VC
        ok("one rule: the card's headline reads the same rRF from the same file",
           VC.headline_r(VC.load_rrf_series(rr_root), today)["rrf"] == 5.12
           and abs(VC.headline_r(VC.load_rrf_series(rr_root), today)["r"] - 10.12) < 1e-12)
        ok("RPM is one number in three places (cost_of_equity, value_card, beta_probe)",
           RPM_PCT == VC.RPM_PCT == 100 * BP.RPM)
    finally:
        shutil.rmtree(rr_root, ignore_errors=True)

    # 10-16 the per-name record against the probe's own 11-18 numbers
    aapl = {"daily": {"beta": 1.0369704336236014, "adj": CF.blume(1.0369704336236014), "se": 0.06113877344510087,
                      "r2": 0.36661524566691145, "n": 499, "short": False, "first": "2024-11-20",
                      "last": "2026-11-17"}, "weekly": {"beta": 1.0211, "adj": CF.blume(1.0211), "n": 155},
            "z": 0.11, "cross": "AGREE"}
    ra = name_record(aapl, 5.12)
    ok("AAPL: r = 5.12 + 1.0248 x 5 = 10.24% (the probe previewed 10.2%)",
       abs(ra["r_capm_pct"] - (5.12 + 5 * CF.blume(1.0369704336236014))) < 1e-12 and abs(ra["r_capm_pct"] - 10.24) < 0.005,
       "%.4f" % ra["r_capm_pct"])
    half = 5.0 * 0.67 * 1.96 * 0.06113877344510087
    ok("AAPL: CI half-width = 5 x 0.67 x 1.96 x SE (%.3f points), not WIDE" % half,
       abs(ra["r_half_pp"] - half) < 1e-12 and abs((ra["r_ci_pct"][1] - ra["r_ci_pct"][0]) / 2 - half) < 1e-12
       and ra["flags"] == [])
    cbrs = {"daily": {"beta": 2.7729407130345467, "adj": CF.blume(2.7729407130345467), "se": 0.6554155323775525,
                      "r2": 0.12, "n": 129, "short": True}, "weekly": {"beta": 5.97, "n": 26},
            "z": -2.41, "cross": "DISAGREE"}
    rc = name_record(cbrs, 5.12)
    ok("CBRS: SHORT, DISAGREE and WIDE (half-width %.1f points)" % rc["r_half_pp"],
       rc["flags"] == ["SHORT", "DISAGREE", "WIDE"] and rc["r_half_pp"] > WIDE_HALF_PP)
    spy = {"daily": {"beta": 1.0, "adj": 1.0, "se": 0.0, "r2": 1.0, "n": 499, "short": False},
           "weekly": {"beta": 1.0, "n": 155}, "z": None, "cross": "n/a"}
    ok("SPY: r = rRF + RPM exactly, CI of zero width", abs(name_record(spy, 5.12)["r_capm_pct"] - 10.12) < 1e-12
       and name_record(spy, 5.12)["r_half_pp"] == 0.0)
    ok("Ch 6 slide 59 at rRF 4%: beta 1.3 (adjusted) needs 10.5%", abs(CF.capm(4.0, 5.0, 1.3) - 10.5) < 1e-12)
    rn = name_record(aapl, None)
    ok("NEGATIVE: no rRF keeps the beta and gives no r", rn["r_capm_pct"] is None and rn["beta_adj"] is not None
       and rn["why"] == "no rRF")
    ok("NEGATIVE: no daily beta gives no record", name_record({"daily": {"beta": None, "why": "x"}}, 5.12)
       ["r_capm_pct"] is None)

    # 17-22 cache rules
    good = {"cache_version": CACHE_VERSION, "as_of": "2026-11-16", "bars": bars(),
            "betas": {"SPY": spy, "AAPL": aapl}, "errors": {"ZZZ": "no candles"}}
    ok("cache: 2 days old, same bars, covers the names -> reused",
       cache_usable(good, today, ["SPY", "AAPL", "ZZZ"])[0])
    ok("NEGATIVE: a cache estimated after the date is a look-ahead",
       not cache_usable(good, dt.date(2026, 11, 13), ["SPY"])[0]
       and "look-ahead" in cache_usable(good, dt.date(2026, 11, 13), ["SPY"])[1])
    ok("NEGATIVE: a cache 8 days old is refused", not cache_usable(good, dt.date(2026, 11, 24), ["SPY"])[0])
    ok("cache: 7 days old is still reused (the bar is 'more than 7')",
       cache_usable(good, dt.date(2026, 11, 23), ["SPY"])[0])
    ok("NEGATIVE: different bars or a new name refuse the cache",
       not cache_usable(dict(good, bars=dict(bars(), daily_years=1)), today, ["SPY"])[0]
       and "lacks NVDA" in cache_usable(good, today, ["SPY", "NVDA"])[1])
    ok("NEGATIVE: no cache, or the wrong version", not cache_usable(None, today, ["SPY"])[0]
       and not cache_usable(dict(good, cache_version=0), today, ["SPY"])[0])

    # 23-33 end to end, offline: synthetic candles, an injected fetch, a temp root
    sessions = TC.sessions_between(dt.date(2023, 10, 1), dt.date(2026, 11, 17))
    rng = random.Random(20261118)
    m_ret = [rng.gauss(0.0004, 0.01) for _ in sessions]

    def path(rets, p0):
        out, p = [], p0
        for r in rets:
            p *= (1 + r)
            out.append(p)
        return out
    series = {"SPY": path(m_ret, 500.0), "VTI": path([r + rng.gauss(0, 0.0005) for r in m_ret], 250.0),
              "AAA": path([1.5 * r + rng.gauss(0, 0.01) for r in m_ret], 50.0),
              "BBB": path([0.5 * r + rng.gauss(0, 0.01) for r in m_ret], 80.0)}
    calls = []

    def fake_fetch(tickers, asof, log):
        calls.append((tuple(tickers), asof))
        out = {t: [c for c in BP._mk(sessions, series[t]) if c["date"] < asof] for t in tickers if t in series}
        errs = {t: "no candles returned (HTTP 400)" for t in tickers if t not in series}
        for t in errs:
            out[t] = []
        return None, out, errs
    root = tempfile.mkdtemp(prefix="coe_selftest_")
    try:
        os.makedirs(os.path.join(root, "logs"))
        logp = os.path.join(root, "logs", "signals_2026-11-18.log")
        with open(logp, "w", encoding="utf-8") as fh:
            for t in ("AAA", "BBB", "VTI", "QQQX"):
                fh.write("x | [PHASE 3-C DRY RUN] [Acct A] [SCOUT] %s | Signal: HOLD | Confidence: 60%% | "
                         "Risk: APPROVED | Reason: x | H1[]\n" % t)
        ns = argparse.Namespace(date="2026-11-18", log=logp, tickers=None, root=root, refresh=False, out=None)
        quiet = []
        rc1 = run(ns, quiet.append, fake_fetch, lambda: csv_a, today=today)
        with open(os.path.join(root, "cost_of_equity_2026-11-18.json"), encoding="utf-8") as fh:
            j = json.load(fh)
        aaa = j["names"]["AAA"]
        ok("e2e: the log's names plus SPY are fetched once, candles before the date",
           len(calls) == 1 and set(calls[0][0]) == {"AAA", "BBB", "VTI", "QQQX", "SPY"} and calls[0][1] == today)
        ok("e2e: AAA (true beta 1.5) reads within 3 SE, r = 5.12 + adj x 5 (the yield dated before 11-18)",
           abs(aaa["beta_raw"] - 1.5) < 3 * aaa["se"] and abs(aaa["r_capm_pct"] - (5.12 + 5 * aaa["beta_adj"])) < 1e-12,
           "%.3f" % aaa["beta_raw"])
        ok("e2e: a name with no candles is listed with its reason and is a finding",
           j["names"]["QQQX"]["r_capm_pct"] is None and "HTTP 400" in j["names"]["QQQX"]["why"]
           and any("QQQX" in f for f in j["findings"]) and rc1 == 1)
        ok("e2e: feed sanity PASS (SPY on itself, VTI ~1)", j["feed_sanity"]["spy_self"] == "PASS"
           and j["feed_sanity"]["vti"] == "PASS")
        ok("e2e: the keys value_card reads are present",
           all(k in j for k in ("rrf", "mkt_r_pct", "rpm_pct", "names")) and abs(j["mkt_r_pct"] - 10.12) < 1e-12
           and all(k in aaa for k in ("r_capm_pct", "r_ci_pct", "flags", "beta_adj", "beta_raw", "se", "r2", "n")))
        ok("e2e: today's run writes the cache", os.path.exists(cache_path(root)))
        with open(os.path.join(root, "cost_of_equity_2026-11-18.md"), encoding="utf-8") as fh:
            md = fh.read()
        ok("e2e: the exhibit states the rRF, the 9% identity and the method",
           "rRF 5.12% (FRED DGS10, observed 2026-11-16)" in md and "rRF 4.00%" in md and "Blume 0.67" in md
           and os.path.exists(series_path(root)))
        rc2 = run(ns, quiet.append, fake_fetch, lambda: csv_a, today=today)
        with open(os.path.join(root, "cost_of_equity_2026-11-18.json"), encoding="utf-8") as fh:
            j2 = json.load(fh)
        ok("e2e: a second run the same day reuses the cache (no fetch), same r",
           len(calls) == 1 and j2["beta_source"]["from_cache"] and rc2 == 1
           and abs(j2["names"]["AAA"]["r_capm_pct"] - aaa["r_capm_pct"]) < 1e-12)
        mtime = os.path.getmtime(cache_path(root))
        ns_past = argparse.Namespace(date="2026-11-10", log=logp, tickers=None, root=root, refresh=False, out=None)
        rc3 = run(ns_past, quiet.append, fake_fetch, lambda: csv_a, today=today)
        with open(os.path.join(root, "cost_of_equity_2026-11-10.json"), encoding="utf-8") as fh:
            j3 = json.load(fh)
        ok("e2e: a PAST date refuses the later cache, fetches candles before it, writes no cache",
           len(calls) == 2 and calls[1][1] == dt.date(2026, 11, 10) and os.path.getmtime(cache_path(root)) == mtime
           and not j3["beta_source"]["from_cache"] and j3["names"]["AAA"]["last"] < "2026-11-10" and rc3 == 1)
        ok("e2e: the past date finds no yield dated before 11-10 in the series (it starts 11-13): none",
           j3["rrf"]["pct"] is None and "dated before 2026-11-10" in j3["rrf"]["why"])
        ns_ref = argparse.Namespace(date="2026-11-18", log=logp, tickers=None, root=root, refresh=True, out=None)
        run(ns_ref, quiet.append, fake_fetch, lambda: csv_a, today=today)
        ok("e2e: --refresh fetches even with a fresh cache", len(calls) == 3)

        def no_spy(tickers, asof, log):
            return None, {t: [] for t in tickers}, {t: "x" for t in tickers}
        nos = argparse.Namespace(date="2026-11-18", log=logp, tickers=None, root=root, refresh=True,
                                 out=os.path.join(root, "nospy"))
        ok("NEGATIVE: no SPY history -> exit 2, nothing written",
           run(nos, quiet.append, no_spy, lambda: csv_a, today=today) == 2
           and not os.path.exists(os.path.join(root, "nospy.md")))
        nolog = argparse.Namespace(date="2026-11-18", log=os.path.join(root, "none.log"), tickers=None,
                                   root=root, refresh=False, out=None)
        ok("NEGATIVE: no signals log -> exit 2", run(nolog, quiet.append, fake_fetch, lambda: csv_a,
                                                    today=today) == 2)
        fut = argparse.Namespace(date="2026-11-19", log=logp, tickers=None, root=root, refresh=False, out=None)
        ok("NEGATIVE: a date after today -> exit 2", run(fut, quiet.append, fake_fetch, lambda: csv_a,
                                                        today=today) == 2)
        shutil.copy(logp, os.path.join(root, REFUSED))     # exists and parses: only the name refuses it
        rep = argparse.Namespace(date="2026-11-18", log=os.path.join(root, REFUSED), tickers=None, root=root,
                                 refresh=False, out=None)
        said = []
        ok("NEGATIVE: the report copy is refused as an input, by name",
           run(rep, said.append, fake_fetch, lambda: csv_a, today=today) == 2
           and said and said[0].startswith("REFUSED"))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    width = max(len(n) for n, _, _ in checks)
    for n, passed, d in checks:
        print("  %s  %s  %s" % ("PASS" if passed else "FAIL", n.ljust(width), d))
    failed = [n for n, p, _ in checks if not p]
    print("%d checks, %d PASS, %d FAIL" % (len(checks), len(checks) - len(failed), len(failed)))
    if not failed:
        print("ALL PASS")
    return 0 if not failed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="DP-V7 step 2: per-name CAPM cost of equity (reporting only).")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--log", help="logs\\signals_<date>.log (the watchlist)")
    ap.add_argument("--tickers", help="comma-separated, instead of the log")
    ap.add_argument("--out", help="output stem (default cost_of_equity_<date>)")
    ap.add_argument("--refresh", action="store_true", help="re-fetch every beta")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
