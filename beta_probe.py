#!/usr/bin/env python3
"""
beta_probe.py - READ-ONLY. Estimates each watchlist name's beta against SPY
from Schwab's own daily price history, tests the master's prices against the
same feed (D9), and checks two inputs the next DP-V7 steps need: a 10-year
Treasury yield and option-implied volatility.

WHY (DP-V7, ruled by Rob 2026-11-18; claude/FINC5133_CourseReview_2026-11-18.md)
    The value card prices every name at one cost of equity, r = 9%. In the
    course's own CAPM example (rRF 4%, RPM 5%) 9% is the return on a beta-1.0
    stock (Ch 6 slide 59), so the card assumes beta = 1 for every name. Step 2
    replaces that with r = rRF + beta x 5.0%. This probe is step 1: it measures
    the betas, and how much to trust them, before anything uses them.

    D9 (the price-provenance [?] open since 08-17) gets its independent check
    here. The 08-17 evidence pack computed betas from the master and found
    AAPL's correlation with SPY at 0.08 against ~0.70 typical. This probe sets
    the master's prices beside Schwab's candles for the same dates, and
    rebuilds that correlation four ways on the same cohort dates (master
    Price@Signal, Schwab open, Schwab close, and the 2-year daily series), so a
    low reading is located: in the master's numbers, in the sampling, or in
    the timing of an open-auction quote.

WHAT IT READS
    Schwab daily candles (one call per name), the MASTER read-only (refuses the
    report copy), a Schwab quote for the 10-year yield index, FRED's public
    DGS10 series, and 3 option chains. No account data. No model call.

WHAT IT WRITES
    beta_probe_<date>.md and beta_probe_<date>.json, nothing else. No cache,
    no workbook, no prompt, no gate, no endpoint, no paste (DP-V1).

BARS - fixed here on 2026-11-18, before the first run (DP-V7)
    Beta (Rob, 2026-11-18)
      primary      2 years of DAILY simple returns vs SPY (Ch 25 slide 44)
      cross-check  3 years of WEEKLY returns (last close of each week)
      adjusted     Blume 0.67 x raw + 0.33 (not printed in the course files)
      SHORT        fewer than 250 daily / 104 weekly returns: printed, flagged
      DISAGREE     |daily - weekly| / sqrt(SE_d^2 + SE_w^2) > 2.0
    Feed sanity
      SPY on itself must read beta 1 exactly (code integrity)
      VTI daily beta in [0.95, 1.05] with R^2 >= 0.95, else FEED SUSPECT
    D9 provenance
      a master close (H/I/J) vs Schwab's close on its resolution session
      (trading_calendar.shift_sessions(cohort, 5/10/20)):
        MATCH     within max($0.01, 0.05%)
        NEAR      within 0.5%
        MISMATCH  beyond 0.5%
      Price@Signal (G) is an intraday quote: INSIDE when within that
      session's [low - $0.01, high + $0.01], else OUTSIDE.
      A close whose session is AFTER today is FUTURE (a filled-but-not-due cell);
      one whose session IS today is counted TODAY and not compared (no completed
      candle yet).
      D9 CLEAN = 0 MISMATCH, 0 FUTURE and 0 OUTSIDE. Anything else lists every row.
    Cost-of-equity preview
      r = 10-yr Treasury (FRED DGS10, latest) + adjusted beta x 5.0% (RPM,
      Rob 2026-11-18). PREVIEW ONLY: step 2 computes it on the card.
    Options
      ATM implied vol: the expiry nearest 30 calendar days, the strike nearest
      the underlying, mean of call and put volatility. 3 names: SPY, AAPL, NVDA.

USAGE (cmd, repo root, venv active, outside the 09:30 window)
    python beta_probe.py                      latest cohort's names + D9 on every master ticker
    python beta_probe.py --tickers AAPL,SPY   betas for these only (SPY is always added)
    python beta_probe.py --no-d9 --no-options --no-rates
    python beta_probe.py --selftest           offline, fixtures; touches no file
    Exit: 0 ran (findings are the normal state); 2 could not run.

Advisory-only - no orders - not financial advice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import math
import os
import sys
import time

import corpfin as CF
import trading_calendar as TC

PROBE_VERSION = 1
MARKET = "SPY"
DAILY_YEARS = 2
WEEKLY_YEARS = 3
FETCH_YEARS = 3
FETCH_PAD_DAYS = 21
MIN_OBS_DAILY = 250
MIN_OBS_WEEKLY = 104
DISAGREE_Z = 2.0
VTI_BAND = (0.95, 1.05)
VTI_MIN_R2 = 0.95
MATCH_ABS = 0.01
MATCH_REL = 0.0005
NEAR_REL = 0.005
RANGE_TOL = 0.01
RPM = 0.05                          # DP-V7 (Rob, 2026-11-18)
OPTION_TICKERS = ("SPY", "AAPL", "NVDA")
TARGET_DTE = 30
TNX_SYMBOLS = ("$TNX", "$TNX.X")
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
MASTER_DEFAULT = os.path.join("logs", "claude_equity_bot_tracker.xlsx")
REFUSED = "tracker_with_registry.xlsx"
FIRST_DATA_ROW = 5
HORIZONS = (("H", 7, 5), ("I", 8, 10), ("J", 9, 20))   # column, 0-based index, sessions
CALL_PAUSE_S = 0.35                 # Schwab allows 120 calls/minute; stay well under

try:
    from zoneinfo import ZoneInfo
    _MARKET_TZ = ZoneInfo("America/New_York")
except Exception:                   # pragma: no cover
    _MARKET_TZ = dt.timezone.utc


def market_today():
    return dt.datetime.now(_MARKET_TZ).date()


def years_before(d, years):
    try:
        return d.replace(year=d.year - years)
    except ValueError:              # 29 February
        return d.replace(year=d.year - years, day=28)


# ============================================================================ candles
def candles_from_json(js, today):
    """Schwab price-history JSON -> [{date, open, high, low, close}], completed
    sessions only, oldest first. Candle 'datetime' is epoch ms in a market-side
    zone: date it in UTC and compare with the market's 'today' (schwab_client's
    H1 rule, 2026-08-26)."""
    out = {}
    for c in (js or {}).get("candles", []) or []:
        ts, close = c.get("datetime"), c.get("close")
        if ts is None or close is None:
            continue
        d = dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc).date()
        if d >= today:
            continue
        out[d] = {"date": d, "open": c.get("open"), "high": c.get("high"),
                  "low": c.get("low"), "close": float(close)}
    return [out[d] for d in sorted(out)]


def window(candles, years, today):
    start = years_before(today, years)
    return [c for c in candles if c["date"] > start]


def weekly_closes(candles, today):
    """Last close of each ISO week, oldest first. The current week is dropped:
    candles stop before today, so it is never complete."""
    weeks = {}
    for c in candles:
        weeks[c["date"].isocalendar()[:2]] = c
    cur = today.isocalendar()[:2]
    return [{"date": weeks[k]["date"], "close": weeks[k]["close"], "key": k}
            for k in sorted(weeks) if k != cur]


def aligned_returns(stock, market, key="date"):
    """Simple returns over consecutive COMMON points. A day one series lacks is
    skipped by both, so both returns always span the same interval."""
    s = {c[key]: c["close"] for c in stock}
    m = {c[key]: c["close"] for c in market}
    common = sorted(set(s) & set(m))
    ys, xs, ends = [], [], []
    for a, b in zip(common, common[1:]):
        if s[a] and m[a]:
            ys.append(s[b] / s[a] - 1)
            xs.append(m[b] / m[a] - 1)
            ends.append(b)
    return ys, xs, ends


def beta_block(stock, market, periods_per_year, min_obs, key="date"):
    ys, xs, ends = aligned_returns(stock, market, key)
    reg = CF.ols(ys, xs)
    if reg is None:
        return {"n": len(ys), "beta": None, "why": "fewer than 3 common returns, or no variance"}
    sd_i = CF.sample_sd(ys) if len(ys) > 1 else None
    sd_m = CF.sample_sd(xs) if len(xs) > 1 else None
    out = dict(reg)
    out.update({
        "adj": CF.blume(reg["beta"]),
        "ci95": (reg["beta"] - 1.96 * reg["se"], reg["beta"] + 1.96 * reg["se"]),
        "sigma_ann": CF.annualize_sd(sd_i, periods_per_year) if sd_i else None,
        "sigma_mkt_ann": CF.annualize_sd(sd_m, periods_per_year) if sd_m else None,
        "first": str(ends[0]) if ends else None, "last": str(ends[-1]) if ends else None,
        "short": len(ys) < min_obs,
    })
    return out


def cross_check(d, w):
    if not d or not w or d.get("beta") is None or w.get("beta") is None:
        return None, "n/a"
    den = math.sqrt(d["se"] ** 2 + w["se"] ** 2)
    if den == 0:
        return None, "n/a"
    z = (d["beta"] - w["beta"]) / den
    return z, ("DISAGREE" if abs(z) > DISAGREE_Z else "AGREE")


def name_betas(candles, mkt_candles, today):
    daily = beta_block(window(candles, DAILY_YEARS, today),
                       window(mkt_candles, DAILY_YEARS, today), 252, MIN_OBS_DAILY)
    weekly = beta_block(weekly_closes(window(candles, WEEKLY_YEARS, today), today),
                        weekly_closes(window(mkt_candles, WEEKLY_YEARS, today), today),
                        52, MIN_OBS_WEEKLY, key="key")
    z, verdict = cross_check(daily, weekly)
    return {"daily": daily, "weekly": weekly, "z": z, "cross": verdict,
            "history_from": str(candles[0]["date"]) if candles else None}


def feed_sanity(betas):
    spy = betas.get(MARKET, {}).get("daily") or {}
    spy_ok = spy.get("beta") is not None and abs(spy["beta"] - 1) < 1e-9 and abs(spy["r2"] - 1) < 1e-9
    vti = betas.get("VTI", {}).get("daily") or {}
    if vti.get("beta") is None:
        vti_v = "n/a (VTI not read)"
    elif VTI_BAND[0] <= vti["beta"] <= VTI_BAND[1] and vti["r2"] >= VTI_MIN_R2:
        vti_v = "PASS"
    else:
        vti_v = "FEED SUSPECT"
    return {"spy_self": "PASS" if spy_ok else "FAIL", "vti": vti_v,
            "vti_beta": vti.get("beta"), "vti_r2": vti.get("r2")}


# ============================================================================ D9
def classify_close(master, schwab):
    diff = abs(master - schwab)
    if diff <= max(MATCH_ABS, MATCH_REL * abs(schwab)):
        return "MATCH"
    if diff <= NEAR_REL * abs(schwab):
        return "NEAR"
    return "MISMATCH"


def inside_range(price, low, high):
    return (low - RANGE_TOL) <= price <= (high + RANGE_TOL)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def load_master(path):
    """[{date, ticker, G, H, I, J}] from Signals rows 5+. Read-only; refuses
    the generated report copy (house rule)."""
    if os.path.basename(path).lower() == REFUSED.lower():
        raise SystemExit("REFUSED: %s is the GENERATED REPORT COPY, never an input. "
                         "Use logs\\claude_equity_bot_tracker.xlsx (THE MASTER)." % REFUSED)
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Signals"]
        rows = []
        for r in ws.iter_rows(min_row=FIRST_DATA_ROW, max_col=10, values_only=True):
            if not r or r[0] is None or r[1] is None or not hasattr(r[0], "year"):
                continue
            d = r[0].date() if hasattr(r[0], "date") else r[0]
            rows.append({"date": d, "ticker": str(r[1]).strip().upper(),
                         "G": r[6] if _num(r[6]) else None,
                         "H": r[7] if _num(r[7]) else None,
                         "I": r[8] if _num(r[8]) else None,
                         "J": r[9] if _num(r[9]) else None})
        return rows
    finally:
        wb.close()


def latest_cohort(rows):
    if not rows:
        return []
    last = max(r["date"] for r in rows)
    return sorted({r["ticker"] for r in rows if r["date"] == last})


def d9_checks(rows, candles_by_ticker, today):
    """Every master price set beside Schwab's candle for the same session."""
    closes = {"MATCH": 0, "NEAR": 0, "MISMATCH": 0, "NO CANDLE": 0, "TODAY": 0, "FUTURE": 0}
    signal = {"INSIDE": 0, "OUTSIDE": 0, "NO CANDLE": 0}
    flagged, per_ticker, signed = [], {}, []
    for r in rows:
        bydate = candles_by_ticker.get(r["ticker"])
        if bydate is None:
            continue
        t = per_ticker.setdefault(r["ticker"], {"closes": 0, "bad": 0, "outside": 0})
        for col, _, n in HORIZONS:
            v = r[col]
            if v is None:
                continue
            target = TC.shift_sessions(r["date"], n)
            if target == today:         # tonight's close: no completed candle yet
                closes["TODAY"] += 1
                continue
            if target > today:          # a close for a session that has not happened
                closes["FUTURE"] += 1
                flagged.append({"kind": "close", "verdict": "FUTURE", "date": str(r["date"]),
                                "ticker": r["ticker"], "col": col, "session": str(target),
                                "master": v, "schwab": None})
                continue
            c = bydate.get(target)
            if c is None:
                closes["NO CANDLE"] += 1
                continue
            verdict = classify_close(v, c["close"])
            closes[verdict] += 1
            t["closes"] += 1
            signed.append(((c["close"] - v) / v, (today - target).days))
            if verdict != "MATCH":
                t["bad"] += 1 if verdict == "MISMATCH" else 0
                flagged.append({"kind": "close", "verdict": verdict, "date": str(r["date"]),
                                "ticker": r["ticker"], "col": col, "session": str(target),
                                "master": v, "schwab": c["close"]})
        g = r["G"]
        if g is not None:
            c = bydate.get(r["date"])
            if c is None or c.get("low") is None or c.get("high") is None:
                signal["NO CANDLE"] += 1
            elif inside_range(g, c["low"], c["high"]):
                signal["INSIDE"] += 1
            else:
                signal["OUTSIDE"] += 1
                t["outside"] += 1
                flagged.append({"kind": "signal", "verdict": "OUTSIDE", "date": str(r["date"]),
                                "ticker": r["ticker"], "col": "G", "session": str(r["date"]),
                                "master": g, "schwab": [c["low"], c["high"]]})
    buckets = {}
    for rel, age in signed:
        b = "<30d" if age < 30 else ("30-90d" if age <= 90 else ">90d")
        buckets.setdefault(b, []).append(rel)
    adj = {b: {"n": len(v), "median_signed": sorted(v)[len(v) // 2]} for b, v in buckets.items()}
    verdict = ("CLEAN" if closes["MISMATCH"] == 0 and closes["FUTURE"] == 0 and signal["OUTSIDE"] == 0
               else "FINDINGS")
    return {"verdict": verdict, "closes": closes, "signal": signal, "flagged": flagged,
            "per_ticker": per_ticker, "age_buckets": adj}


def matched_date_rho(rows, candles_by_ticker, ticker):
    """The 08-17 anomaly rebuilt on the SAME cohort dates, four ways."""
    g_t = {r["date"]: r["G"] for r in rows if r["ticker"] == ticker and r["G"]}
    g_m = {r["date"]: r["G"] for r in rows if r["ticker"] == MARKET and r["G"]}
    ct, cm = candles_by_ticker.get(ticker, {}), candles_by_ticker.get(MARKET, {})
    dates = sorted(d for d in set(g_t) & set(g_m) if d in ct and d in cm)
    out = {"n_dates": len(dates)}
    for label, f_t, f_m in (
            ("master_G", lambda d: g_t[d], lambda d: g_m[d]),
            ("schwab_open", lambda d: ct[d]["open"], lambda d: cm[d]["open"]),
            ("schwab_close", lambda d: ct[d]["close"], lambda d: cm[d]["close"])):
        ys, xs = [], []
        for a, b in zip(dates, dates[1:]):
            try:
                ys.append(f_t(b) / f_t(a) - 1)
                xs.append(f_m(b) / f_m(a) - 1)
            except (TypeError, ZeroDivisionError):
                pass
        reg = CF.ols(ys, xs)
        out[label] = {"rho": reg["rho"] if reg else None, "beta": reg["beta"] if reg else None,
                      "n": len(ys)}
    return out


# ============================================================================ rates, options
def parse_fred_csv(text):
    """Latest non-missing (date, percent) from FRED's fredgraph.csv. FRED's
    header has been both 'DATE,DGS10' and 'observation_date,DGS10'; a missing
    day is '.' or empty."""
    import csv
    latest = None
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2 or not row[0][:4].isdigit():
            continue
        try:
            latest = (row[0], float(row[1]))
        except ValueError:
            continue
    return latest


def fetch_fred(timeout=20):
    try:
        try:
            import requests
            resp = requests.get(FRED_URL, timeout=timeout)
            resp.raise_for_status()
            text = resp.text
        except ImportError:         # pragma: no cover
            import urllib.request
            with urllib.request.urlopen(FRED_URL, timeout=timeout) as r:
                text = r.read().decode("utf-8", "replace")
        got = parse_fred_csv(text)
        if not got:
            return {"ok": False, "why": "no numeric row in FRED's CSV"}
        return {"ok": True, "date": got[0], "pct": got[1]}
    except Exception as e:          # noqa: BLE001 - a probe reports, it does not crash
        return {"ok": False, "why": "%s: %s" % (type(e).__name__, e)}


def tnx_from_quote_json(js, symbol):
    q = (js or {}).get(symbol, {})
    q = q.get("quote", q)
    for k in ("lastPrice", "closePrice", "mark"):
        if _num(q.get(k)):
            return float(q[k])
    return None


def parse_option_chain(js, target_dte=TARGET_DTE):
    """ATM implied vol from a Schwab option chain: the expiry nearest
    target_dte, the strike nearest the underlying, mean of call and put
    'volatility' (percent). Unusable values (<= 0, -999, NaN) are dropped."""
    js = js or {}
    und = js.get("underlyingPrice")
    if not _num(und):
        und = ((js.get("underlying") or {}).get("last"))
    if not _num(und):
        return {"ok": False, "why": "no underlying price in the chain"}
    best = None
    for side in ("callExpDateMap", "putExpDateMap"):
        for exp_key, strikes in (js.get(side) or {}).items():
            try:
                dte = int(exp_key.split(":")[1])
            except (IndexError, ValueError):
                continue
            for k, contracts in strikes.items():
                for c in contracts or []:
                    v = c.get("volatility")
                    if not _num(v) or v <= 0 or v != v or v > 500:
                        continue
                    cand = (abs(dte - target_dte), abs(float(k) - und), exp_key, float(k))
                    if best is None or cand[:2] < best[0][:2]:
                        best = (cand, [])
                    if cand[:2] == best[0][:2]:
                        best[1].append((side, v))
    if best is None:
        return {"ok": False, "why": "no usable volatility field"}
    vols = [v for _, v in best[1]]
    iv = sum(vols) / len(vols) / 100.0
    return {"ok": True, "iv": iv, "expiry": best[0][2], "strike": best[0][3], "underlying": und,
            "sides": sorted({s for s, _ in best[1]}),
            "move_5d": CF.implied_move(iv, 5), "p_breach_5d_3pct": CF.p_breach(iv, 5, 0.03)}


# ============================================================================ live run
def fetch_all(tickers, today, log):
    import schwab_client as SC
    client = SC.get_client()
    start = dt.datetime.combine(years_before(today, FETCH_YEARS) - dt.timedelta(days=FETCH_PAD_DAYS),
                                dt.time())
    end = dt.datetime.now()
    out, errors = {}, {}
    for t in tickers:
        try:
            resp = client.get_price_history_every_day(SC.schwab_symbol(t), start_datetime=start,
                                                      end_datetime=end)
            js = resp.json()
            cs = candles_from_json(js, today)
            if not cs:
                errors[t] = "no candles returned (HTTP %s)" % getattr(resp, "status_code", "?")
            out[t] = cs
        except Exception as e:      # noqa: BLE001
            errors[t] = "%s: %s" % (type(e).__name__, e)
            out[t] = []
        log("  %-6s %4d candles%s" % (t, len(out[t]), ("  ERROR " + errors[t]) if t in errors else ""))
        time.sleep(CALL_PAUSE_S)
    return client, out, errors


def fetch_rates(client):
    fred = fetch_fred()
    tnx = {}
    for sym in TNX_SYMBOLS:
        try:
            resp = client.get_quotes([sym])
            tnx[sym] = {"value": tnx_from_quote_json(resp.json(), sym),
                        "http": getattr(resp, "status_code", None)}
        except Exception as e:      # noqa: BLE001
            tnx[sym] = {"value": None, "why": "%s: %s" % (type(e).__name__, e)}
        time.sleep(CALL_PAUSE_S)
    scale = None
    if fred.get("ok"):
        for sym, v in tnx.items():
            if v.get("value"):
                ratio = v["value"] / fred["pct"]
                v["ratio_to_fred"] = ratio
                if scale is None:
                    scale = ("x10 (index = yield x 10)" if 8 <= ratio <= 12 else
                             "x1 (index = yield)" if 0.8 <= ratio <= 1.2 else
                             "UNCLEAR (ratio %.2f)" % ratio)
    return {"fred": fred, "schwab": tnx, "schwab_scale": scale}


def fetch_options(client, today):
    out = {}
    for t in OPTION_TICKERS:
        try:
            try:
                resp = client.get_option_chain(t, strike_count=8, include_underlying_quote=True,
                                               from_date=today + dt.timedelta(days=1),
                                               to_date=today + dt.timedelta(days=60))
            except TypeError:
                resp = client.get_option_chain(t, strike_count=8, include_underlying_quote=True)
            got = parse_option_chain(resp.json())
            got["http"] = getattr(resp, "status_code", None)
        except Exception as e:      # noqa: BLE001
            got = {"ok": False, "why": "%s: %s" % (type(e).__name__, e)}
        out[t] = got
        time.sleep(CALL_PAUSE_S)
    return out


# ============================================================================ report
def _f(x, fmt="%.3f", none="—"):
    return none if x is None else fmt % x


def _pct(x, d=2):
    return "—" if x is None else ("%." + str(d) + "f%%") % (100 * x)


def render_md(res):
    L = []
    w = L.append
    d9 = res.get("d9")
    fs = res["feed_sanity"]
    rates = res.get("rates") or {}
    fred = rates.get("fred") or {}
    names = [t for t in res["tickers"] if t in res["betas"]]
    read = [t for t in names if res["betas"][t]["daily"].get("beta") is not None]
    short = [t for t in read if res["betas"][t]["daily"].get("short")]
    dis = [t for t in read if res["betas"][t]["cross"] == "DISAGREE"]
    w("# beta_probe - %s" % res["date"])
    w("")
    w("*READ-ONLY (DP-V7). Schwab daily candles, the master read-only, FRED DGS10, 3 option "
      "chains. Writes this file and its JSON only. Nothing reaches the card, the prompt, a gate, "
      "an endpoint or the paste (DP-V1). Advisory-only - no orders - not financial advice.*")
    w("")
    w("## 0 - Verdicts (bars fixed in the code header before the first run)")
    w("")
    w("| Check | Result |")
    w("|---|---|")
    w("| Feed sanity: SPY on itself | %s |" % fs["spy_self"])
    w("| Feed sanity: VTI daily beta in [0.95, 1.05], R^2 >= 0.95 | %s (beta %s, R^2 %s) |"
      % (fs["vti"], _f(fs["vti_beta"]), _f(fs["vti_r2"])))
    w("| Betas read (2y daily) | %d of %d; SHORT %s; daily vs weekly DISAGREE %s |"
      % (len(read), len(names), ", ".join(short) or "none", ", ".join(dis) or "none"))
    if d9:
        w("| **D9 provenance** | **%s**: closes %s; Price@Signal %s |" % (
            d9["verdict"], ", ".join("%s %d" % kv for kv in d9["closes"].items() if kv[1]),
            ", ".join("%s %d" % kv for kv in d9["signal"].items() if kv[1])))
    else:
        w("| D9 provenance | not run (--no-d9) |")
    if rates:
        w("| 10-yr Treasury, FRED DGS10 | %s |" % (
            ("%.2f%% on %s" % (fred["pct"], fred["date"])) if fred.get("ok") else
            ("UNAVAILABLE: " + fred.get("why", "?")[:160])))
        w("| 10-yr yield index, Schwab | %s; scale %s |" % (
            "; ".join("%s %s" % (s, _f(v.get("value"), "%.3f", v.get("why", "no value")))
                      for s, v in rates["schwab"].items()), rates.get("schwab_scale") or "n/a"))
    else:
        w("| Rates | not run (--no-rates) |")
    if res.get("options"):
        ok = [t for t, v in res["options"].items() if v.get("ok")]
        w("| Option-implied vol | %s |" % ("AVAILABLE on %s" % ", ".join(ok) if ok else "UNAVAILABLE"))
    w("")
    w("## 1 - Betas against SPY")
    w("")
    w("Primary: 2 years of daily simple returns. Cross-check: 3 years of weekly. Adjusted = "
      "%s. CI = beta +/- 1.96 SE. Preview r = rRF + adjusted beta x %.1f%% (step 2 computes it "
      "on the card; this is not a class)." % (CF.BLUME_LABEL, 100 * RPM))
    w("")
    w("| Name | beta (2y d) | SE | 95% CI | R^2 | n | adjusted | beta (3y w) | n | z | cross | "
      "sigma ann | preview r |")
    w("|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|")
    rrf = (fred.get("pct") / 100.0) if fred.get("ok") else None
    for t in names:
        b = res["betas"][t]
        dd, ww = b["daily"], b["weekly"]
        if dd.get("beta") is None:
            w("| %s | no read: %s | | | | %d | | | | | | | |" % (t, dd.get("why", "?"), dd.get("n", 0)))
            continue
        prev = CF.capm(rrf, RPM, dd["adj"]) if rrf is not None else None
        w("| %s%s | %s | %s | %s to %s | %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
            t, " (SHORT)" if dd.get("short") else "", _f(dd["beta"]), _f(dd["se"]),
            _f(dd["ci95"][0], "%.2f"), _f(dd["ci95"][1], "%.2f"), _f(dd["r2"], "%.2f"), dd["n"],
            _f(dd["adj"]), _f(ww.get("beta")), ww.get("n", 0), _f(b["z"], "%+.1f"), b["cross"],
            _pct(dd.get("sigma_ann"), 0), _pct(prev, 1)))
    w("")
    if d9:
        w("## 2 - D9: the master's prices against Schwab's candles")
        w("")
        w("| Prices compared | Count |")
        w("|---|---:|")
        for k, v in d9["closes"].items():
            w("| close (H/I/J) %s | %d |" % (k, v))
        for k, v in d9["signal"].items():
            w("| Price@Signal (G) %s | %d |" % (k, v))
        w("")
        w("**Adjustment check** (median of (Schwab - master) / master on compared closes, by age): " +
          "; ".join("%s %s (n %d)" % (b, _pct(v["median_signed"], 3), v["n"])
                    for b, v in sorted(d9["age_buckets"].items())) +
          ". A median that grows with age would mean the feed is dividend-adjusted.")
        w("")
        bad = [f for f in d9["flagged"] if f["verdict"] in ("MISMATCH", "OUTSIDE", "NEAR", "FUTURE")]
        if bad:
            w("| Kind | Verdict | Cohort | Ticker | Col | Session | Master | Schwab |")
            w("|---|---|---|---|---|---|---:|---|")
            for f in bad[:200]:
                w("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    f["kind"], f["verdict"], f["date"], f["ticker"], f["col"], f["session"],
                    f["master"], f["schwab"]))
            if len(bad) > 200:
                w("")
                w("*%d more in the JSON.*" % (len(bad) - 200))
        else:
            w("Every compared price matched.")
        w("")
        w("### The 08-17 anomaly, rebuilt on the same cohort dates")
        w("")
        w("Correlation with SPY of returns between consecutive cohort dates, four ways. If the "
          "master's figure is low and Schwab's close is not, the master's numbers are the cause. If "
          "Schwab's open is low too, the cause is open-auction timing, not the data.")
        w("")
        w("| Name | dates | rho master G | rho Schwab open | rho Schwab close | rho 2y daily |")
        w("|---|---:|---:|---:|---:|---:|")
        for t, m in sorted(res.get("matched", {}).items()):
            w("| %s | %d | %s | %s | %s | %s |" % (
                t, m["n_dates"], _f(m["master_G"]["rho"], "%.2f"), _f(m["schwab_open"]["rho"], "%.2f"),
                _f(m["schwab_close"]["rho"], "%.2f"),
                _f((res["betas"].get(t, {}).get("daily") or {}).get("rho"), "%.2f")))
        w("")
    if res.get("options"):
        w("## 3 - Option-implied volatility (feasibility for step 5)")
        w("")
        w("| Name | Result | IV (ATM) | Expiry | Strike | 1-sigma 5d | P(\\|move\\| > 3%) 5d |")
        w("|---|---|---:|---|---:|---:|---:|")
        for t, v in res["options"].items():
            if v.get("ok"):
                w("| %s | OK | %s | %s | %s | %s | %s |" % (
                    t, _pct(v["iv"], 1), v["expiry"], _f(v["strike"], "%.2f"), _pct(v["move_5d"]),
                    _pct(v["p_breach_5d_3pct"], 1)))
            else:
                w("| %s | UNAVAILABLE: %s | | | | | |" % (t, v.get("why", "?")))
        w("")
    if res.get("fetch_errors"):
        w("## Fetch errors")
        w("")
        for t, e in sorted(res["fetch_errors"].items()):
            w("- %s: %s" % (t, e))
        w("")
    w("*Advisory-only - no orders - not financial advice.*")
    return "\n".join(L) + "\n"


def _jsonable(o):
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def run(args, log=print):
    today = market_today()
    rows = []
    if not args.no_d9 or not args.tickers:
        try:
            rows = load_master(args.tracker)
        except SystemExit:
            raise
        except Exception as e:      # noqa: BLE001
            if not args.tickers:
                log("COULD NOT RUN: master unreadable (%s) and no --tickers given" % e)
                return 2
            log("NOTE: master unreadable (%s); D9 skipped" % e)
            args.no_d9 = True
    tickers = ([t.strip().upper() for t in args.tickers.split(",") if t.strip()]
               if args.tickers else latest_cohort(rows))
    if MARKET not in tickers:
        tickers.append(MARKET)
    fetch = list(tickers)
    if not args.no_d9:
        fetch += sorted({r["ticker"] for r in rows} - set(tickers))
    log("beta_probe %s: %d beta names, %d fetched in all" % (today, len(tickers), len(fetch)))
    try:
        client, candles, errors = fetch_all(fetch, today, log)
    except Exception as e:          # noqa: BLE001
        log("COULD NOT RUN: Schwab client unavailable (%s: %s)" % (type(e).__name__, e))
        return 2
    if not candles.get(MARKET):
        log("COULD NOT RUN: no SPY candles")
        return 2
    betas = {t: name_betas(candles[t], candles[MARKET], today) for t in tickers if candles.get(t)}
    res = {"probe_version": PROBE_VERSION, "date": str(today), "tickers": tickers, "betas": betas,
           "feed_sanity": feed_sanity(betas), "fetch_errors": errors,
           "bars": {"daily_years": DAILY_YEARS, "weekly_years": WEEKLY_YEARS, "min_obs_daily": MIN_OBS_DAILY,
                    "min_obs_weekly": MIN_OBS_WEEKLY, "disagree_z": DISAGREE_Z, "blume": CF.BLUME_LABEL,
                    "match_abs": MATCH_ABS, "match_rel": MATCH_REL, "near_rel": NEAR_REL,
                    "range_tol": RANGE_TOL, "rpm": RPM, "target_dte": TARGET_DTE}}
    if not args.no_d9:
        bydate = {t: {c["date"]: c for c in cs} for t, cs in candles.items()}
        res["d9"] = d9_checks(rows, bydate, today)
        res["matched"] = {t: matched_date_rho(rows, bydate, t) for t in tickers if t != MARKET}
    if not args.no_rates:
        res["rates"] = fetch_rates(client)
    if not args.no_options:
        res["options"] = fetch_options(client, today)
    stem = args.out or ("beta_probe_%s" % today)
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(render_md(res))
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=_jsonable)
    log("wrote %s.md and %s.json" % (stem, stem))
    log("feed sanity: SPY self %s, VTI %s | D9 %s" % (
        res["feed_sanity"]["spy_self"], res["feed_sanity"]["vti"], (res.get("d9") or {}).get("verdict", "not run")))
    return 0


# ============================================================================ selftest
def _mk(dates, closes, spread=0.0):
    return [{"date": d, "open": c, "high": c + spread, "low": c - spread, "close": c}
            for d, c in zip(dates, closes)]


def selftest():
    import random
    checks = []

    def ok(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    today = dt.date(2026, 11, 18)
    sessions = TC.sessions_between(dt.date(2023, 10, 1), dt.date(2026, 11, 17))
    rng = random.Random(20261118)
    m_ret = [rng.gauss(0.0004, 0.01) for _ in sessions]
    s_ret = [1.5 * r + rng.gauss(0, 0.01) for r in m_ret]

    def path(rets, p0=100.0):
        out, p = [], p0
        for r in rets:
            p *= (1 + r)
            out.append(p)
        return out

    mkt = _mk(sessions, path(m_ret), 0.5)
    stk = _mk(sessions, path(s_ret, 50.0), 0.5)

    # 1-4 regression on synthetic data with a known beta of 1.5
    nb = name_betas(stk, mkt, today)
    dd = nb["daily"]
    ok("synthetic daily beta ~1.5 within 3 SE", abs(dd["beta"] - 1.5) < 3 * dd["se"], "%.3f +/- %.3f" % (dd["beta"], dd["se"]))
    ok("2y daily window ~502 returns, not SHORT", 495 <= dd["n"] <= 505 and not dd["short"], str(dd["n"]))
    ok("3y weekly window ~155 returns", 150 <= nb["weekly"]["n"] <= 158, str(nb["weekly"]["n"]))
    ok("adjusted = Blume of raw", abs(dd["adj"] - (0.67 * dd["beta"] + 0.33)) < 1e-12)
    ok("daily and weekly AGREE on a clean series", nb["cross"] == "AGREE", "z %.2f" % nb["z"])

    # 6 SPY on itself
    spyb = name_betas(mkt, mkt, today)
    ok("SPY on itself: beta 1, R^2 1", abs(spyb["daily"]["beta"] - 1) < 1e-12 and abs(spyb["daily"]["r2"] - 1) < 1e-12)
    fs = feed_sanity({"SPY": spyb, "VTI": nb})
    ok("feed sanity flags a VTI at beta 1.5", fs["spy_self"] == "PASS" and fs["vti"] == "FEED SUSPECT")
    fs2 = feed_sanity({"SPY": spyb, "VTI": spyb})
    ok("feed sanity passes a VTI at beta 1", fs2["vti"] == "PASS")

    # 9 alignment: a missing session is skipped by BOTH series
    gap = [c for c in stk if c["date"] != sessions[-10]]
    ys, xs, ends = aligned_returns(gap[-20:], mkt[-20:])
    ok("missing day: both returns span the same 2 sessions", sessions[-10] not in ends and len(ys) == len(xs) == 18)
    i = [k for k, e in enumerate(ends) if e == sessions[-9]][0]
    want_y = stk[-9]["close"] / stk[-11]["close"] - 1
    want_x = mkt[-9]["close"] / mkt[-11]["close"] - 1
    ok("missing day: return is the 2-session return", abs(ys[i] - want_y) < 1e-12 and abs(xs[i] - want_x) < 1e-12)

    # 11 SHORT history
    sb = name_betas(stk[-120:], mkt, today)
    ok("SHORT flag under 250 daily returns", sb["daily"]["short"] and sb["daily"]["n"] == 119, str(sb["daily"]["n"]))

    # 12 weekly: current ISO week dropped; a Friday holiday week closes on Thursday
    wk = weekly_closes(_mk(TC.sessions_between(dt.date(2026, 3, 30), dt.date(2026, 4, 9)),
                           [1, 2, 3, 4, 5, 6, 7, 8, 9]), dt.date(2026, 4, 9))
    ok("weekly: Good Friday week closes Thursday 04-02", wk[0]["date"] == dt.date(2026, 4, 2), str(wk[0]["date"]))
    ok("weekly: the current week is dropped", len(wk) == 1)

    # 14 candles: in-progress candle dropped; UTC dating
    ms = lambda d: int(dt.datetime(d.year, d.month, d.day, 5, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
    js = {"candles": [{"datetime": ms(dt.date(2026, 11, 16)), "open": 1, "high": 2, "low": 0.5, "close": 1.5},
                      {"datetime": ms(dt.date(2026, 11, 17)), "open": 1, "high": 2, "low": 0.5, "close": 1.6},
                      {"datetime": ms(today), "open": 1, "high": 2, "low": 0.5, "close": 9.9}]}
    cs = candles_from_json(js, today)
    ok("candles: today's in-progress candle dropped", len(cs) == 2 and cs[-1]["close"] == 1.6)

    # 15 cross-check disagreement
    z, v = cross_check({"beta": 1.0, "se": 0.05}, {"beta": 1.4, "se": 0.10})
    ok("cross-check: z %.2f -> DISAGREE" % z, v == "DISAGREE" and abs(z - (-0.4 / math.sqrt(0.0125))) < 1e-12)
    ok("cross-check: z 1.8 -> AGREE", cross_check({"beta": 1.0, "se": 0.1}, {"beta": 1.18, "se": 0.0})[1] == "AGREE")

    # 17 D9 classification bars
    ok("D9: 1 cent is MATCH", classify_close(100.00, 100.01) == "MATCH")
    ok("D9: 0.05% on a $400 name is MATCH", classify_close(400.0, 400.19) == "MATCH")
    ok("D9: 0.3% is NEAR", classify_close(100.0, 100.30) == "NEAR")
    ok("D9: 0.6% is MISMATCH (WMT 11.85 vs 111.85 class)", classify_close(11.85, 111.85) == "MISMATCH"
       and classify_close(100.0, 100.6) == "MISMATCH")
    ok("D9: signal inside range with 1-cent tolerance", inside_range(10.0, 10.01, 11) and not inside_range(9.98, 10.0, 11))

    # 22 D9 end to end on a fixture master
    cohort = dt.date(2026, 11, 2)
    t5, t10 = TC.shift_sessions(cohort, 5), TC.shift_sessions(cohort, 10)
    ok("calendar: 2026-11-02 +5 sessions = 11-09", t5 == dt.date(2026, 11, 9), str(t5))
    bydate = {"AAA": {cohort: {"date": cohort, "open": 10, "high": 10.5, "low": 9.5, "close": 10.2},
                      t5: {"date": t5, "open": 11, "high": 11, "low": 11, "close": 11.00},
                      t10: {"date": t10, "open": 12, "high": 12, "low": 12, "close": 12.00}}}
    rows = [{"date": cohort, "ticker": "AAA", "G": 10.1, "H": 11.00, "I": 12.50, "J": None},
            {"date": cohort, "ticker": "ZZZ", "G": 5.0, "H": 5.0, "I": None, "J": None}]
    d9 = d9_checks(rows, bydate, today)
    ok("D9: one MATCH, one MISMATCH, one INSIDE", d9["closes"]["MATCH"] == 1 and d9["closes"]["MISMATCH"] == 1
       and d9["signal"]["INSIDE"] == 1 and d9["verdict"] == "FINDINGS")
    ok("D9: a ticker with no candles is not counted", "ZZZ" not in d9["per_ticker"])
    rows_ok = [dict(rows[0], I=12.0)]
    ok("D9: all matching -> CLEAN", d9_checks(rows_ok, bydate, today)["verdict"] == "CLEAN")
    future = [{"date": dt.date(2026, 11, 16), "ticker": "AAA", "G": None, "H": 1.0, "I": None, "J": None},
              {"date": dt.date(2026, 11, 11), "ticker": "AAA", "G": None, "H": 1.0, "I": None, "J": None}]
    fd = d9_checks(future, bydate, today)
    ok("D9: a close dated after today is FUTURE and breaks CLEAN",
       fd["closes"]["FUTURE"] == 1 and fd["verdict"] == "FINDINGS")
    ok("D9: tonight's close (+5d = today) is counted TODAY, not flagged",
       fd["closes"]["TODAY"] == 1 and len(fd["flagged"]) == 1)

    # 27 matched-date rho: master G equal to Schwab close reproduces Schwab's rho
    dates = sessions[-40:]
    bd = {"AAA": {c["date"]: c for c in stk if c["date"] in dates},
          "SPY": {c["date"]: c for c in mkt if c["date"] in dates}}
    mrows = [{"date": d, "ticker": t, "G": bd[t][d]["close"], "H": None, "I": None, "J": None}
             for d in dates for t in ("AAA", "SPY")]
    md = matched_date_rho(mrows, bd, "AAA")
    ok("matched rho: master G == Schwab close -> identical rho",
       md["n_dates"] == 40 and abs(md["master_G"]["rho"] - md["schwab_close"]["rho"]) < 1e-12)

    # 28 FRED CSV, both header forms, missing days
    ok("FRED: new header, '.' skipped", parse_fred_csv("observation_date,DGS10\n2026-11-13,4.12\n2026-11-14,.\n") == ("2026-11-13", 4.12))
    ok("FRED: old header, empty skipped", parse_fred_csv("DATE,DGS10\n2026-11-12,4.10\n2026-11-13,\n") == ("2026-11-12", 4.10))
    ok("FRED: no numeric row -> None", parse_fred_csv("DATE,DGS10\n") is None)

    # 31 Schwab quote JSON
    ok("TNX: quote.lastPrice read", tnx_from_quote_json({"$TNX": {"quote": {"lastPrice": 41.2}}}, "$TNX") == 41.2)
    ok("TNX: absent symbol -> None", tnx_from_quote_json({}, "$TNX") is None)

    # 33 option chain: nearest-30-day expiry, nearest strike, call/put mean, junk dropped
    chain = {"underlyingPrice": 101.0,
             "callExpDateMap": {"2026-12-04:16": {"100.0": [{"volatility": 50.0}]},
                                "2026-12-18:30": {"100.0": [{"volatility": 24.0}], "105.0": [{"volatility": 30.0}]}},
             "putExpDateMap": {"2026-12-18:30": {"100.0": [{"volatility": 26.0}], "95.0": [{"volatility": -999.0}]}}}
    pc = parse_option_chain(chain)
    ok("options: ATM 30-day IV = mean(24, 26) = 25%", pc["ok"] and abs(pc["iv"] - 0.25) < 1e-12 and pc["strike"] == 100.0,
       "%.4f" % pc.get("iv", 0))
    ok("options: P(|move|>3%%) at 25%% = %.3f" % pc["p_breach_5d_3pct"], abs(pc["p_breach_5d_3pct"] - CF.p_breach(.25, 5, .03)) < 1e-12)
    ok("options: no usable vol -> not ok", parse_option_chain({"underlyingPrice": 1, "callExpDateMap": {"x:30": {"1": [{"volatility": -999}]}}})["ok"] is False)

    # 36 refuses the report copy
    try:
        load_master(REFUSED)
        ok("refuses the report copy", False)
    except SystemExit:
        ok("refuses the report copy", True)

    # 37 render works end to end without touching disk
    res = {"date": str(today), "tickers": ["AAA", "SPY"], "betas": {"AAA": nb, "SPY": spyb},
           "feed_sanity": fs2, "d9": d9, "matched": {"AAA": md},
           "rates": {"fred": {"ok": True, "date": "2026-11-17", "pct": 4.1},
                     "schwab": {"$TNX": {"value": 41.0, "ratio_to_fred": 10.0}}, "schwab_scale": "x10 (index = yield x 10)"},
           "options": {"SPY": pc}, "fetch_errors": {}}
    md_text = render_md(res)
    ok("render: verdict table and preview r present", "## 0 - Verdicts" in md_text and "D9 provenance" in md_text
       and "%.1f%%" % (100 * CF.capm(0.041, RPM, nb["daily"]["adj"])) in md_text)
    json.dumps(res, default=_jsonable)
    ok("render: result is JSON-serialisable", True)

    width = max(len(n) for n, _, _ in checks)
    for n, passed, d in checks:
        print("  %s  %s  %s" % ("PASS" if passed else "FAIL", n.ljust(width), d))
    failed = [n for n, p, _ in checks if not p]
    print("%d checks, %d PASS, %d FAIL" % (len(checks), len(checks) - len(failed), len(failed)))
    if not failed:
        print("ALL PASS")
    return 0 if not failed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="READ-ONLY beta / D9 / rates / options probe (DP-V7).")
    ap.add_argument("--tickers", help="comma-separated; default = the master's latest cohort")
    ap.add_argument("--tracker", default=MASTER_DEFAULT, help="THE MASTER (read-only)")
    ap.add_argument("--out", help="output stem (default beta_probe_<date>)")
    ap.add_argument("--no-d9", action="store_true")
    ap.add_argument("--no-rates", action="store_true")
    ap.add_argument("--no-options", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
