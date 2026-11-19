#!/usr/bin/env python3
"""
implied_vol.py - FINC 5133 step 5 (DP-V10), REPORTING ONLY. The options
market's own 5-day move for each watchlist name, and its probability of a move
beyond the fixed +/-3% HOLD band.

WHY (claude/FINC5133_CourseReview_2026-11-18.md 4.4; DP-V10, Rob 2026-11-18)
    The HOLD band is a fixed +/-3% for every name. The band identity is on the
    record (the band-breach rate is market dispersion). Black-Scholes (Ch 8)
    gives each name the market's own sigma, so the card can show how wide the
    band is in that name's sigma and the market's own P(|5-day move| > 3%):
    about 1 sigma for a quiet name, a third of 1 sigma for a volatile one.
    D4's checkable HOLD forecast will need this as its free baseline, but ONLY
    at D4's own pre-registration (L2). Here it is context (DP-V1).

WHAT IT READS
    today's signals log (the watchlist, via value_card.parse_log) and one Schwab
    option chain per name (schwab-py get_option_chain, the call beta_probe.py
    confirmed on 2026-11-18: SPY, AAPL and NVDA read). No account data, no
    model call, no price history.

WHAT IT WRITES
    implied_vol_<date>.md and .json only. No workbook, prompt, gate, endpoint
    or paste. value_card.py prints panel 2f from the JSON.

BARS - fixed here on 2026-11-18, before the first run (DP-V10)
    Ruled by Rob (2026-11-18 15:20 CT: "Build step 5 now, but don't apply it
    before tonight's review", building on the three defaults put to him):
      expiry     the HORIZON expiry is the earliest expiry on or after the +5
                 session (trading_calendar.shift_sessions(D, 5)), the session
                 whose close resolves the band. The expiry nearest 30 calendar
                 days (beta_probe's rule) is printed beside it as a reference.
      names      every name in the day's signals log, plus SPY.
      where      the value card only (panel 2f). The near-miss registry and
                 D4 wait for D4's own pre-registration.
    Set by Claude under DP-V10 (2026-11-18); Rob may change any before Part B
      ATM        the strike nearest the underlying that has a usable
                 volatility; IV = the mean of the usable call and put
                 'volatility' values at that strike (beta_probe's rule).
                 Usable = a number, > 0, <= 500 (percent), not NaN.
      sigma, P   sigma_5 = IV x sqrt(5/252); P(|r5| > 3%) = 2 (1 - N(3% /
                 sigma_5)): a zero-mean normal (corpfin.implied_move and
                 p_breach, the course-fixture functions). The horizon IV is
                 applied over 5 sessions even when its expiry is later
                 (assumes flat vol to expiry); the term ratio shows how far
                 the two IVs differ.
      window     chains from D to D + 45 calendar days, 8 strikes around
                 the money.
      sanity     SPY must read, with a horizon IV in [5%, 80%]. Otherwise a
                 FINDING (exit 1): a feed or parse fault, not a market fact.
      live only  a chain is today's market; a past date is refused (exit 2).
                 No chain is ever reconstructed or carried forward.
      missing    a name with no chain, or no usable volatility, is printed
                 with its reason and never filled.

    CAVEAT, printed on the card: risk-neutral valuation grows the asset at
    the risk-free rate, not its expected rate (Web 26B), so P is the market's
    PRICE of the move, not a real-world forecast. A normal understates fat
    tails.

USAGE (cmd, repo root, venv active, during or after the session)
    python implied_vol.py --log logs\\signals_2026-11-19.log
    python implied_vol.py --tickers SPY,AAPL
    python implied_vol.py --selftest           offline, synthetic chains; touches no file
    Exit: 0 ran clean; 1 findings; 2 could not run.

Advisory-only - no orders - not financial advice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import time

import corpfin as CF
import trading_calendar as TC

IV_VERSION = 1
MARKET = "SPY"
HORIZON_SESSIONS = 5
BAND = 0.03
REF_DTE = 30
WINDOW_DAYS = 45
STRIKE_COUNT = 8
MAX_VOL_PCT = 500.0
SPY_IV_RANGE = (0.05, 0.80)
CALL_PAUSE_S = 0.35                 # Schwab allows 120 calls/minute; stay well under
REFUSED = "tracker_with_registry.xlsx"

try:
    from zoneinfo import ZoneInfo
    _MARKET_TZ = ZoneInfo("America/New_York")
except Exception:                   # pragma: no cover
    _MARKET_TZ = dt.timezone.utc


def market_today():
    return dt.datetime.now(_MARKET_TZ).date()


def bars():
    return {"horizon_sessions": HORIZON_SESSIONS, "band": BAND, "ref_dte": REF_DTE,
            "window_days": WINDOW_DAYS, "strike_count": STRIKE_COUNT, "max_vol_pct": MAX_VOL_PCT,
            "spy_iv_range": list(SPY_IV_RANGE),
            "expiry_rule": "earliest expiry on or after shift_sessions(D, 5)",
            "atm_rule": "strike nearest the underlying with a usable vol; mean of call and put"}


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x


def usable_vol(v):
    return _num(v) and 0 < v <= MAX_VOL_PCT


def chain_expiries(js):
    """{expiry_date: {"dte": int, "strikes": {strike: [(side, vol_pct), ...]}}} and the
    underlying price, from a Schwab chain. Unusable vols are dropped here."""
    js = js or {}
    und = js.get("underlyingPrice")
    if not _num(und) or und <= 0:
        und = (js.get("underlying") or {}).get("last")
    out = {}
    for side, key in (("call", "callExpDateMap"), ("put", "putExpDateMap")):
        for exp_key, strikes in (js.get(key) or {}).items():
            try:
                ds, dte_s = exp_key.split(":")
                exp = dt.date.fromisoformat(ds)
                dte = int(dte_s)
            except (ValueError, AttributeError):
                continue
            e = out.setdefault(exp, {"dte": dte, "strikes": {}})
            for k, contracts in (strikes or {}).items():
                try:
                    kf = float(k)
                except (TypeError, ValueError):
                    continue
                for c in contracts or []:
                    v = (c or {}).get("volatility")
                    if usable_vol(v):
                        e["strikes"].setdefault(kf, []).append((side, float(v)))
    return (und if _num(und) and und > 0 else None), out


def atm_iv(expiry_rec, und):
    """(iv fraction, strike, sides) at the strike nearest `und` with a usable vol, or None."""
    st = expiry_rec["strikes"]
    if not st or und is None:
        return None
    k = min(st, key=lambda s: (abs(s - und), s))
    vols = [v for _side, v in st[k]]
    return sum(vols) / len(vols) / 100.0, k, sorted({s for s, _v in st[k]})


def read_chain(js, date):
    """One name's read. Never raises; a reason in `why` when there is no read."""
    st = (js or {}).get("status")
    if st not in (None, "SUCCESS"):
        return {"ok": False, "why": "chain status %s" % st}
    und, exps = chain_expiries(js)
    if und is None:
        return {"ok": False, "why": "no underlying price in the chain"}
    per = []
    for exp in sorted(exps):
        a = atm_iv(exps[exp], und)
        if a is None:
            continue
        per.append({"expiry": exp, "dte": exps[exp]["dte"],
                    "sessions": len(TC.sessions_between(date + dt.timedelta(days=1), exp)),
                    "iv": a[0], "strike": a[1], "sides": a[2]})
    if not per:
        return {"ok": False, "why": "no usable volatility in the chain", "underlying": und}
    target = TC.shift_sessions(date, HORIZON_SESSIONS)
    hz = [p for p in per if p["expiry"] >= target]
    if not hz:
        return {"ok": False, "why": "no expiry on or after the +5 session (%s) in the chain" % target,
                "underlying": und, "expiries": per}
    h = hz[0]
    ref = min(per, key=lambda p: (abs(p["dte"] - REF_DTE), p["dte"]))
    s5 = CF.implied_move(h["iv"], HORIZON_SESSIONS)
    return {"ok": True, "why": None, "underlying": und, "target_session": target,
            "horizon": h, "ref30": ref, "sigma_5d": s5, "band_in_sigma": BAND / s5,
            "p_breach": CF.p_breach(h["iv"], HORIZON_SESSIONS, BAND),
            "term_ratio": h["iv"] / ref["iv"] if ref["iv"] else None, "expiries": per}


def fetch_chains(tickers, today, log):
    """{ticker: chain json or None}, {ticker: error}. One call per name."""
    import schwab_client as SC
    client = SC.get_client()
    out, errors = {}, {}
    for t in tickers:
        try:
            sym = SC.schwab_symbol(t)
            try:
                resp = client.get_option_chain(sym, strike_count=STRIKE_COUNT, include_underlying_quote=True,
                                               from_date=today, to_date=today + dt.timedelta(days=WINDOW_DAYS))
            except TypeError:
                resp = client.get_option_chain(sym, strike_count=STRIKE_COUNT, include_underlying_quote=True)
            status = getattr(resp, "status_code", None)
            js = resp.json() if status in (None, 200) else None
            if js is None:
                errors[t] = "HTTP %s" % status
            out[t] = js
        except Exception as e:      # noqa: BLE001
            errors[t] = "%s: %s" % (type(e).__name__, e)
            out[t] = None
        log("  %-6s %s" % (t, ("ERROR " + errors[t]) if t in errors else "chain read"))
        time.sleep(CALL_PAUSE_S)
    return out, errors


def build(date, tickers, fetch_fn=None, log=print, now=None):
    want = sorted(set(tickers) | {MARKET})
    chains, errors = (fetch_fn or fetch_chains)(want, date, log)
    names = {}
    for t in want:
        if errors.get(t):
            names[t] = {"ok": False, "why": "no chain: %s" % errors[t]}
        else:
            names[t] = read_chain(chains.get(t), date)
    findings = []
    spy = names.get(MARKET) or {}
    if not spy.get("ok"):
        findings.append("feed sanity: %s did not read (%s)" % (MARKET, spy.get("why")))
    elif not SPY_IV_RANGE[0] <= spy["horizon"]["iv"] <= SPY_IV_RANGE[1]:
        findings.append("feed sanity: %s horizon IV %.1f%% outside [%.0f%%, %.0f%%]" % (
            MARKET, 100 * spy["horizon"]["iv"], 100 * SPY_IV_RANGE[0], 100 * SPY_IV_RANGE[1]))
    res = {"iv_version": IV_VERSION, "date": date, "fetched_at": (now or dt.datetime.now()).isoformat(
        timespec="seconds"), "bars": bars(), "names": names, "findings": findings}
    return res, findings


def _jsonable(o):
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def _p(x, d=1, none="-"):
    return none if x is None else ("%." + str(d) + "f%%") % (100 * x)


def render_md(res):
    L = ["# Market-implied move, %s (FINC 5133 step 5, DP-V10)" % res["date"], "",
         "*READ-ONLY. One Schwab option chain per watchlist name. Context only: nothing here "
         "reaches the class, a gate, the prompt, the paste or D4 (DP-V1). Advisory-only - no "
         "orders - not financial advice.*", "",
         "Fetched %s. Horizon expiry: the earliest on or after the +5 session. sigma 5d = IV x "
         "sqrt(5/252); P = 2(1 - N(3%% / sigma 5d)). Risk-neutral: the market's price of the move, "
         "not a real-world forecast (Web 26B)." % res["fetched_at"], "",
         "| Name | Horizon expiry (sessions) | IV | ~30d expiry | IV | Term | 1 sigma 5d | +/-3% in sigma "
         "| P(\\|move\\| > 3%) | Note |",
         "|---|---|---:|---|---:|---:|---:|---:|---:|---|"]
    for t in sorted(res["names"]):
        x = res["names"][t]
        if not x.get("ok"):
            L.append("| %s | - | - | - | - | - | - | - | - | %s |" % (t, x.get("why")))
            continue
        h, r = x["horizon"], x["ref30"]
        L.append("| %s | %s (%d) | %s | %s | %s | %.2f | %s | %.2f | %s | strike %.2f |" % (
            t, h["expiry"], h["sessions"], _p(h["iv"]), r["expiry"], _p(r["iv"]), x["term_ratio"] or 0,
            _p(x["sigma_5d"], 2), x["band_in_sigma"], _p(x["p_breach"]), h["strike"]))
    L += ["", "**Findings:** %s" % ("; ".join(res["findings"]) or "none"), "",
          "*Advisory-only - no orders - not financial advice.*", ""]
    return "\n".join(L)


def tickers_from_log(path):
    import value_card as VC
    return sorted(VC.parse_log(path))


def run(args, log=print, fetch_fn=None, today=None):
    today = today or market_today()
    date = dt.date.fromisoformat(args.date) if args.date else today
    if date != today:
        log("COULD NOT RUN: an option chain is today's market (%s); %s cannot be read now and is "
            "never reconstructed" % (today, date))
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
        res, findings = build(date, tickers, fetch_fn, log)
    except Exception as e:          # noqa: BLE001 - no client, no token: context only
        log("COULD NOT RUN: %s: %s" % (type(e).__name__, e))
        return 2
    stem = args.out or os.path.join(args.root, "implied_vol_%s" % date)
    with open(stem + ".md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_md(res))
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=_jsonable)
    n_ok = sum(1 for x in res["names"].values() if x.get("ok"))
    log("implied_vol %s: %d of %d names read; findings %d" % (date, n_ok, len(res["names"]), len(findings)))
    log("wrote %s.md and %s.json" % (stem, stem))
    return 1 if findings else 0


# ============================================================================ selftest
def _chain(und, exps, side_vols=None):
    """A synthetic Schwab chain: exps = [(expiry date, dte, {strike: (call vol, put vol)})]."""
    js = {"underlyingPrice": und, "callExpDateMap": {}, "putExpDateMap": {}}
    for exp, dte, strikes in exps:
        key = "%s:%d" % (exp.isoformat(), dte)
        for k, (cv, pv) in strikes.items():
            if cv is not None:
                js["callExpDateMap"].setdefault(key, {})["%.1f" % k] = [{"volatility": cv}]
            if pv is not None:
                js["putExpDateMap"].setdefault(key, {})["%.1f" % k] = [{"volatility": pv}]
    return js


def selftest():
    import shutil
    import tempfile
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    D = dt.date
    d0 = D(2026, 11, 18)                                    # +5 session = 11-25 (Wed)
    tgt = TC.shift_sessions(d0, 5)
    ok("calendar: the +5 session from 2026-11-18 is 2026-11-25", tgt == D(2026, 11, 25))
    js = _chain(100.0, [(D(2026, 11, 20), 2, {100.0: (80.0, 82.0)}),
                        (D(2026, 11, 27), 9, {95.0: (44.0, 46.0), 100.0: (40.0, 42.0), 105.0: (38.0, -999.0)}),
                        (D(2026, 12, 18), 30, {100.0: (30.0, 32.0)})])
    r = read_chain(js, d0)
    ok("horizon expiry: 11-20 is before the +5 session, so 11-27 is chosen",
       r["ok"] and r["horizon"]["expiry"] == D(2026, 11, 27))
    ok("ATM: strike 100 (nearest 100.0), IV = mean(40, 42) = 41%",
       r["horizon"]["strike"] == 100.0 and abs(r["horizon"]["iv"] - 0.41) < 1e-12)
    ok("reference: the expiry nearest 30 days is 12-18 at 31%",
       r["ref30"]["expiry"] == D(2026, 12, 18) and abs(r["ref30"]["iv"] - 0.31) < 1e-12)
    s5 = 0.41 * math.sqrt(5 / 252.0)
    ok("sigma 5d = IV x sqrt(5/252); P = 2(1 - N(3%/sigma)) (corpfin, the course functions)",
       abs(r["sigma_5d"] - s5) < 1e-12 and abs(r["p_breach"] - 2 * (1 - CF.norm_cdf(0.03 / s5))) < 1e-12
       and abs(r["band_in_sigma"] - 0.03 / s5) < 1e-12)
    ok("term ratio = horizon IV / 30-day IV", abs(r["term_ratio"] - 0.41 / 0.31) < 1e-12)
    ok("sessions to the horizon expiry: 11-19 .. 11-27 is 6 (Thanksgiving closed)",
       r["horizon"]["sessions"] == 6)
    ok("NEGATIVE: a chain whose status is FAILED (no listed options) -> no read, with the status",
       read_chain({"status": "FAILED", "underlyingPrice": 10.0}, d0)["why"] == "chain status FAILED")
    ok("probe check: NVDA's 11-18 probe read, IV 51.1% -> 1 sigma 5d 7.20%, P 67.7%",
       abs(CF.implied_move(0.511, 5) - 0.0720) < 5e-5 and abs(CF.p_breach(0.511, 5, 0.03) - 0.677) < 5e-4)
    js2 = _chain(100.0, [(D(2026, 11, 27), 9, {100.0: (None, -999.0), 101.0: (39.0, None)})])
    r2 = read_chain(js2, d0)
    ok("an unusable vol (-999) is dropped; the nearest USABLE strike (101) is read",
       r2["ok"] and r2["horizon"]["strike"] == 101.0 and abs(r2["horizon"]["iv"] - 0.39) < 1e-12)
    ok("NEGATIVE: no underlying price -> no read, with a reason",
       read_chain({"callExpDateMap": {}}, d0)["why"] == "no underlying price in the chain")
    ok("NEGATIVE: every vol unusable -> no read",
       read_chain(_chain(50.0, [(D(2026, 11, 27), 9, {50.0: (0.0, 600.0)})]), d0)["why"]
       == "no usable volatility in the chain")
    r3 = read_chain(_chain(50.0, [(D(2026, 11, 20), 2, {50.0: (30.0, 30.0)})]), d0)
    ok("NEGATIVE: only expiries before the +5 session -> no read, never the short one",
       not r3["ok"] and "on or after the +5 session" in r3["why"])
    ok("underlying from 'underlying.last' when underlyingPrice is missing",
       read_chain({"underlying": {"last": 100.0}, "callExpDateMap":
                   {"2026-11-27:9": {"100.0": [{"volatility": 20.0}]}}}, d0)["ok"])

    def fake(chains, errors=None):
        def f(want, date, log):
            return {t: chains.get(t) for t in want}, dict(errors or {})
        return f
    good_spy = _chain(600.0, [(D(2026, 11, 27), 9, {600.0: (15.0, 16.0)}),
                              (D(2026, 12, 18), 30, {600.0: (17.0, 18.0)})])
    res, fnd = build(d0, ["AAPL", "XYZ"], fake({"SPY": good_spy, "AAPL": js}, {"XYZ": "HTTP 404"}),
                     log=lambda *_: None)
    ok("build: SPY is always added; a fetch error is 'no chain', never filled",
       set(res["names"]) == {"SPY", "AAPL", "XYZ"} and not res["names"]["XYZ"]["ok"]
       and res["names"]["XYZ"]["why"] == "no chain: HTTP 404" and res["names"]["AAPL"]["ok"])
    ok("build: a sane SPY gives no finding", fnd == [])
    _r, fnd2 = build(d0, ["AAPL"], fake({"AAPL": js}), log=lambda *_: None)
    ok("NEGATIVE: SPY missing -> FINDING (feed or parse fault)", len(fnd2) == 1 and "SPY did not read" in fnd2[0])
    bad_spy = _chain(600.0, [(D(2026, 11, 27), 9, {600.0: (2.0, 2.0)})])
    _r, fnd3 = build(d0, [], fake({"SPY": bad_spy}), log=lambda *_: None)
    ok("NEGATIVE: SPY IV 2% (outside 5-80%) -> FINDING", len(fnd3) == 1 and "outside" in fnd3[0])

    class A:
        date = None
        tickers = "AAPL"
        log = None
        root = "."
        out = None
    tmp = tempfile.mkdtemp(prefix="implied_vol_selftest_")
    try:
        a = A()
        a.root = tmp
        a.date = "2026-11-17"
        ok("NEGATIVE: a past date is refused (a chain is today's market)",
           run(a, log=lambda *_: None, fetch_fn=fake({"SPY": good_spy}), today=d0) == 2
           and not os.listdir(tmp))
        a.date = None
        rc = run(a, log=lambda *_: None, fetch_fn=fake({"SPY": good_spy, "AAPL": js}), today=d0)
        with open(os.path.join(tmp, "implied_vol_2026-11-18.json"), encoding="utf-8") as fh:
            j = json.load(fh)
        ok("e2e: writes implied_vol_<date>.json and .md; exit 0 with a sane SPY",
           rc == 0 and j["names"]["AAPL"]["horizon"]["expiry"] == "2026-11-27"
           and os.path.exists(os.path.join(tmp, "implied_vol_2026-11-18.md")) and j["iv_version"] == IV_VERSION)

        def boom(want, date, log):
            raise RuntimeError("no token")
        ok("NEGATIVE: no client (no token) -> COULD NOT RUN, exit 2", run(a, log=lambda *_: None,
                                                                          fetch_fn=boom, today=d0) == 2)
        a.tickers, a.log = None, os.path.join(tmp, "tracker_with_registry.xlsx")
        ok("NEGATIVE: the report copy is refused as an input", run(a, log=lambda *_: None, today=d0) == 2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for name, good in checks:
        print("  [%s] %s" % ("PASS" if good else "FAIL", name))
    n_fail = sum(1 for _n, g in checks if not g)
    print("%d checks, %d PASS, %d FAIL" % (len(checks), len(checks) - n_fail, n_fail))
    return 1 if n_fail else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="FINC 5133 step 5: market-implied 5-day move (reporting only).")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today; any other date is refused)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--log", help="logs\\signals_<date>.log (the watchlist)")
    ap.add_argument("--tickers", help="comma-separated, instead of the log")
    ap.add_argument("--out", help="output stem (default implied_vol_<date>)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
