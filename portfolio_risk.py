#!/usr/bin/env python3
"""
portfolio_risk.py - FINC 5133 step 8 (DP-V13), REPORTING ONLY. Each account's
portfolio beta, volatility, market share of its variance, concentration and its
most correlated holdings.

WHY (claude/FINC5133_CourseReview_2026-11-18.md 4.9, item F3; Rob 2026-11-19)
    The card judges names one at a time. risk_engine's MAX_POSITION_PCT bounds
    how big one position may get, not how much of the same risk accumulates
    across positions (WS4 3.2). The course gives the account-level measures:
    portfolio beta = sum of w x beta (Ch 6 slides 70-72; the 0.8121 example),
    portfolio sigma from the covariance of the holdings (Ch 6 slides 29-42),
    and the split of variance into market and specific risk (Ch 25). Several
    held names sit in both accounts, so each account is read on its own and
    the two together.

WHAT IT READS
    Schwab: every active account's positions and balances (schwab_client.
    get_all_portfolios, the read main.py makes each run) and one daily price
    history per held name plus SPY (beta_probe.fetch_all, the call DP-V7
    uses). today's cost_of_equity_<date>.json for the card's adjusted betas.
    No order path, no model call, no master, no log.

WHAT IT WRITES
    portfolio_risk_<date>.md and .json only: account LABELS and WEIGHTS. No
    dollar amount, quantity or account number is ever written. No workbook,
    prompt, gate, endpoint or paste (DP-V1). value_card.py prints panel 2g.

BARS - fixed here on 2026-11-19, before the first run (DP-V13)
    Put to Rob 2026-11-19 18:1x CT ("lets move to the next step"); he may
    change any before Part B:
      holdings   positions of asset type EQUITY, COLLECTIVE_INVESTMENT or ETF,
                 cash equivalents excluded: schwab_client.extract_held_tickers'
                 own rule. Weight = market value / the account's invested
                 total. Any other asset type is printed as OTHER with its
                 share and kept out. A short position is printed and kept out.
      cash       cash share = cash available / liquidation value. Cash has
                 beta 0: beta incl. cash = beta x invested / liquidation value.
      beta       sum of w x the card's ADJUSTED beta (cost_of_equity_<date>.json,
                 Blume, 2 years daily vs SPY): the course's portfolio beta.
                 Over the names that have one, re-weighted; the covered share
                 is printed. Below 95% covered: a FINDING.
      sigma      today's weights applied to the last 2 years of daily simple
                 returns (completed sessions on the dates EVERY held name and
                 SPY traded): r_p = sum w_i r_i; sigma_p = sd(r_p) x sqrt(252),
                 identical to sqrt(w' S w). Fewer than 250 returns: SHORT,
                 and the name that shortens the window is named.
      market     r_p regressed on SPY over the same returns: the portfolio's
                 own raw beta and R^2, the market's share of its variance.
      spread     N_eff = 1 / sum w^2; top-1 and top-3 weight; diversification
                 ratio = sum w_i sigma_i / sigma_p (1 = no diversification).
      risk share each name's share of the portfolio variance,
                 w_i cov(r_i, r_p) / var(r_p) (they sum to 1); top 3 printed.
      pairs      held-name pairs with rho >= 0.70 on the same returns, highest
                 first; 5 printed per account, all counted.
      accounts   each active account, then ALL ACCOUNTS combined (the same
                 name in two accounts is summed).
      live only  positions are today's; a past date is refused (exit 2).

    AMENDED 2026-11-19 ~20:30 CT (v1.1, after the first live read and BEFORE
    Part B; Rob's to accept by applying it):
      young      a held name with fewer than 250 returns of its OWN inside the
                 window is left out of sigma, R^2, own beta, variance shares
                 and pairs, and named with its weight. It stays in the weights,
                 N_eff, top-1/top-3 and the card beta. Sigma below 95% of the
                 weight covered (young or no history) is a FINDING. Only when
                 every held name is young does the common-date rule apply and
                 print SHORT. WHY: on 11-19 CBRS (1.4% of the Individual
                 account, listed 2026-05-15) cut that account and the combined
                 book from 499 returns to 130, so the two accounts were read on
                 different windows. Any recent listing would do the same; the
                 rule failed by construction, not by its numbers.
      whole acct the card's "w/ cash" becomes "whole account": beta x the
                 equity share, with cash AND every other asset (on 11-19, all
                 FIXED_INCOME) at beta 0. Right for T-bills and CDs, not for
                 long or corporate bonds [?]. The other-asset share is now on
                 the card, not only in the .md.
      context    the highest pair is printed even when none reaches 0.70;
                 "limited by" is printed only for a SHORT window.

    CAVEAT, printed on the card: today's holdings applied to 2 years of
    returns, as if held throughout. Backward-looking; betas move toward 1
    over time and individual betas are noisy (Ch 25 slides 40-47).

USAGE (cmd, repo root, venv active, after the session)
    python portfolio_risk.py
    python portfolio_risk.py --selftest      offline fixtures; touches no file
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

import corpfin as CF

PR_VERSION = 2          # v1.1, 2026-11-19 evening, before Part B (see AMENDED below)
MARKET = "SPY"
DAILY_YEARS = 2
MIN_OBS = 250
CLUSTER_RHO = 0.70
TOP_PAIRS = 5
TOP_RISK = 3
COVERAGE_MIN = 0.95
ANNUAL = 252
ACCEPTED_TYPES = ("EQUITY", "COLLECTIVE_INVESTMENT", "ETF")       # schwab_client's own
CASH_EQUIVALENTS = {"SWVXX", "SNAXX", "SNSXX", "SWGXX", "MMDA1"}  # schwab_client's own
REFUSED = "tracker_with_registry.xlsx"

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


# ============================================================================ holdings
def safe_label(portfolio, known_labels=()):
    """The account's label, never its number. An unlabelled account reads as
    'unlabelled account (...123)'."""
    lab = str(portfolio.get("account_label") or "").strip()
    num = str(portfolio.get("account_number") or "")
    if lab and (lab in known_labels or (num and num not in lab)):
        return lab
    return "unlabelled account (...%s)" % (num[-3:] if num else "?")


def holdings(portfolio, known_labels=()):
    """{label, mv: {ticker: market value}, other: {asset type: mv}, shorts: [..],
    cash, total}. Dollar values stay in memory; only shares are written."""
    mv, other, shorts = {}, {}, []
    for p in portfolio.get("positions") or []:
        ins = p.get("instrument") or {}
        sym = str(ins.get("symbol") or "").strip()
        typ = str(ins.get("assetType") or "").strip()
        val = p.get("marketValue") or 0.0
        if not sym:
            continue
        if (p.get("shortQuantity") or 0) > 0 or val < 0:
            shorts.append(sym)
            continue
        if sym in CASH_EQUIVALENTS:
            other["CASH EQUIVALENT"] = other.get("CASH EQUIVALENT", 0.0) + val
            continue
        if typ not in ACCEPTED_TYPES:
            other[typ or "UNKNOWN"] = other.get(typ or "UNKNOWN", 0.0) + val
            continue
        mv[sym] = mv.get(sym, 0.0) + float(val)
    return {"label": safe_label(portfolio, known_labels), "mv": mv, "other": other,
            "shorts": sorted(set(shorts)), "cash": float(portfolio.get("cash_available") or 0.0),
            "total": float(portfolio.get("portfolio_value") or 0.0)}


def combine(hs, label="ALL ACCOUNTS"):
    mv, other, shorts = {}, {}, set()
    for h in hs:
        for k, v in h["mv"].items():
            mv[k] = mv.get(k, 0.0) + v
        for k, v in h["other"].items():
            other[k] = other.get(k, 0.0) + v
        shorts |= set(h["shorts"])
    return {"label": label, "mv": mv, "other": other, "shorts": sorted(shorts),
            "cash": sum(h["cash"] for h in hs), "total": sum(h["total"] for h in hs)}


def weights(mv):
    tot = sum(v for v in mv.values() if v > 0)
    return {k: v / tot for k, v in mv.items() if v > 0} if tot > 0 else {}


def weighted_beta(w, betas):
    """(sum w b over covered names / covered weight, covered weight, missing)."""
    cov = sum(x for t, x in w.items() if betas.get(t) is not None)
    miss = sorted(t for t in w if betas.get(t) is None)
    if cov <= 0:
        return None, 0.0, miss
    return sum(x * betas[t] for t, x in w.items() if betas.get(t) is not None) / cov, cov, miss


# ============================================================================ returns
def aligned(candles, tickers, today):
    """Daily simple returns on the dates EVERY ticker traded inside the 2-year
    window. Returns (rets {t: [..]}, ends [..], limiting ticker or None)."""
    start = years_before(today, DAILY_YEARS)
    closes, firsts = {}, {}
    for t in tickers:
        cs = [c for c in (candles.get(t) or []) if start < c["date"] < today and c.get("close")]
        if not cs:
            return None, [], t
        closes[t] = {c["date"]: float(c["close"]) for c in cs}
        firsts[t] = cs[0]["date"]
    common = sorted(set.intersection(*(set(v) for v in closes.values())))
    rets = {t: [] for t in tickers}
    ends = []
    for a, b in zip(common, common[1:]):
        for t in tickers:
            rets[t].append(closes[t][b] / closes[t][a] - 1)
        ends.append(b)
    limiting = max(firsts, key=lambda t: firsts[t]) if firsts else None
    return rets, ends, limiting


def _cov(xs, ys):
    mx, my = CF.mean(xs), CF.mean(ys)
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (len(xs) - 1)


def account_risk(h, betas, candles, today):
    """Every DP-V13 measure for one account (or the combined book)."""
    w_all = weights(h["mv"])
    out = {"label": h["label"], "positions": len(w_all), "findings": [],
           "weights": {t: round(x, 4) for t, x in sorted(w_all.items(), key=lambda kv: -kv[1])}}
    inv = sum(h["mv"].values())
    tot = h["total"] if h["total"] > 0 else None
    out["invested_share"] = (inv / tot) if tot else None
    out["cash_share"] = (h["cash"] / tot) if tot else None
    oth = sum(h["other"].values())
    out["other_share"] = (oth / tot) if tot and oth else 0.0
    out["other_types"] = sorted(h["other"])
    out["shorts"] = h["shorts"]
    if not w_all:
        out["findings"].append("%s: no equity or ETF position" % h["label"])
        return out
    sq = sum(x * x for x in w_all.values())
    ranked = sorted(w_all.items(), key=lambda kv: -kv[1])
    out.update(n_eff=1.0 / sq, top_name=ranked[0][0], top_w=ranked[0][1],
               top3_w=sum(x for _, x in ranked[:3]))
    b, cov_b, miss_b = weighted_beta(w_all, betas)
    out.update(beta_card=b, coverage_beta=cov_b, missing_beta=miss_b,
               beta_card_cash=(b * out["invested_share"]) if (b is not None and out["invested_share"]) else None)
    if b is None or cov_b < COVERAGE_MIN:
        out["findings"].append("%s: card beta covers %.0f%% of the weight (missing %s)" % (
            h["label"], 100 * cov_b, ", ".join(miss_b) or "all"))
    have = [t for t in w_all if candles.get(t)]
    out["missing_candles"] = sorted(t for t in w_all if not candles.get(t))
    if out["missing_candles"]:
        out["findings"].append("%s: no price history for %s; sigma is over the rest" % (
            h["label"], ", ".join(out["missing_candles"])))
    if not have:
        return out
    start = years_before(today, DAILY_YEARS)
    own_n = {t: max(0, sum(1 for c in candles[t] if start < c["date"] < today and c.get("close")) - 1)
             for t in have}
    young = sorted((t for t in have if own_n[t] < MIN_OBS), key=lambda t: -w_all[t])
    if young and len(young) < len(have):
        have = [t for t in have if t not in young]
    else:
        young = []                         # every name is young: common dates, SHORT below
    out["too_new"] = [{"ticker": t, "w": w_all[t], "returns": own_n[t]} for t in young]
    cov_s = sum(w_all[t] for t in have)
    if cov_s < COVERAGE_MIN:
        out["findings"].append("%s: sigma covers %.0f%% of the weight (left out: %s)" % (
            h["label"], 100 * cov_s, ", ".join(out["missing_candles"] + young)))
    w = {t: w_all[t] / cov_s for t in have}
    use_mkt = bool(candles.get(MARKET))
    names = sorted(have) + ([MARKET] if use_mkt and MARKET not in have else [])
    rets, ends, limiting = aligned(candles, names, today)
    if rets is None or len(ends) < 3:
        out["findings"].append("%s: too few common returns for sigma" % h["label"])
        return out
    rp = [sum(w[t] * rets[t][i] for t in have) for i in range(len(ends))]
    var_p = CF.sample_sd(rp) ** 2
    sig = {t: CF.sample_sd(rets[t]) for t in have}
    out.update(coverage_sigma=cov_s, n_obs=len(ends), first=str(ends[0]), last=str(ends[-1]),
               limiting=limiting if len(ends) < MIN_OBS else None, short=len(ends) < MIN_OBS,
               sigma_p=math.sqrt(var_p) * math.sqrt(ANNUAL),
               dr=(sum(w[t] * sig[t] for t in have) / math.sqrt(var_p)) if var_p > 0 else None)
    if out["short"]:
        out["findings"].append("%s: SHORT window, %d returns (limited by %s)" % (h["label"], len(ends), limiting))
    share = {t: (w[t] * _cov(rets[t], rp) / var_p) if var_p > 0 else None for t in have}
    out["risk_share"] = [(t, s) for t, s in sorted(share.items(), key=lambda kv: -(kv[1] or 0))][:TOP_RISK]
    if use_mkt:
        reg = CF.ols(rp, rets[MARKET])
        out.update(beta_hist=reg["beta"] if reg else None, r2=reg["r2"] if reg else None,
                   sigma_m=CF.sample_sd(rets[MARKET]) * math.sqrt(ANNUAL))
    else:
        out.update(beta_hist=None, r2=None, sigma_m=None)
        out["findings"].append("%s: no SPY history; no market share" % h["label"])
    pairs, best = [], None
    srt = sorted(have)
    for i, a in enumerate(srt):
        for b2 in srt[i + 1:]:
            rho = CF.correl(rets[a], rets[b2]) if sig[a] > 0 and sig[b2] > 0 else None
            if rho is None:
                continue
            if best is None or rho > best[2]:
                best = (a, b2, rho)
            if rho >= CLUSTER_RHO:
                pairs.append((a, b2, rho))
    pairs.sort(key=lambda p: -p[2])
    out["pairs_n"] = len(pairs)
    out["pairs"] = [{"a": a, "b": b2, "rho": r} for a, b2, r in pairs[:TOP_PAIRS]]
    out["max_pair"] = {"a": best[0], "b": best[1], "rho": best[2]} if best else None
    return out


def build(date, portfolios, candles, coe, known_labels=()):
    """The whole read, fetching injected. Returns (result, findings)."""
    findings = []
    betas = {}
    if not coe or str(coe.get("date")) != str(date):
        findings.append("no cost_of_equity_%s.json for %s: card beta NO READ" % (date, date))
    else:
        betas = {t: (x or {}).get("beta_adj") for t, x in (coe.get("names") or {}).items()}
    hs = [holdings(p, known_labels) for p in portfolios]
    accounts = [account_risk(h, betas, candles, date) for h in hs]
    both = sorted(set.intersection(*(set(h["mv"]) for h in hs))) if len(hs) > 1 else []
    combined = account_risk(combine(hs), betas, candles, date) if len(hs) > 1 else None
    for a in accounts + ([combined] if combined else []):
        findings += a["findings"]
    if candles is not None and not candles.get(MARKET):
        findings.append("no SPY price history")
    res = {"pr_version": PR_VERSION, "date": str(date), "accounts": accounts, "combined": combined,
           "in_both": both, "beta_source": "cost_of_equity_%s.json (beta_adj)" % date,
           "bars": {"daily_years": DAILY_YEARS, "min_obs": MIN_OBS, "cluster_rho": CLUSTER_RHO,
                    "top_pairs": TOP_PAIRS, "coverage_min": COVERAGE_MIN},
           "findings": sorted(set(findings))}
    return res, res["findings"]


# ============================================================================ render
def _p(x, d=1):
    return "-" if x is None else ("%." + str(d) + "f%%") % (100 * x)


def _n(x, spec="%.2f"):
    return "-" if x is None else spec % x


def render_md(res):
    L = ["# Portfolio risk per account (FINC 5133 step 8, DP-V13) - %s" % res["date"], "",
         "*REPORTING ONLY (DP-V1). Account labels and weights only; no dollar amount, quantity or "
         "account number. Advisory-only · no orders · not financial advice.*", "",
         "| Account | Names | Beta (card) | Beta, whole account | Sigma (ann.) | Market share (R^2) | "
         "Own beta | N_eff | Top-1 | Top-3 | Cash | Other | Div. ratio | Returns |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|"]
    rows = res["accounts"] + ([res["combined"]] if res.get("combined") else [])
    for a in rows:
        L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s %s | %s | %s | %s | %s | %s%s |" % (
            a["label"], a["positions"], _n(a.get("beta_card")), _n(a.get("beta_card_cash")),
            _p(a.get("sigma_p")), _p(a.get("r2"), 0), _n(a.get("beta_hist")), _n(a.get("n_eff"), "%.1f"),
            a.get("top_name") or "-", _p(a.get("top_w"), 0), _p(a.get("top3_w"), 0), _p(a.get("cash_share"), 0),
            _p(a.get("other_share"), 0), _n(a.get("dr")), a.get("n_obs", "-"), " SHORT" if a.get("short") else ""))
    L.append("")
    for a in rows:
        L.append("**%s**" % a["label"])
        L.append("- weights: " + ", ".join("%s %.1f%%" % (t, 100 * x) for t, x in a["weights"].items()))
        if a.get("risk_share"):
            L.append("- largest shares of variance: " + ", ".join("%s %.0f%%" % (t, 100 * s)
                                                                 for t, s in a["risk_share"] if s is not None))
        if a.get("pairs_n") is not None:
            mp = a.get("max_pair")
            L.append("- pairs with rho >= %.2f: %d%s" % (CLUSTER_RHO, a["pairs_n"], (": " + ", ".join(
                "%s-%s %.2f" % (p["a"], p["b"], p["rho"]) for p in a["pairs"])) if a["pairs"] else (
                "; the highest is %s-%s %.2f" % (mp["a"], mp["b"], mp["rho"]) if mp else "")))
        if a.get("too_new"):
            L.append("- left out of sigma, R^2, own beta and pairs (under %d returns of their own): %s" % (
                MIN_OBS, ", ".join("%s %.1f%% (%d returns)" % (y["ticker"], 100 * y["w"], y["returns"])
                                   for y in a["too_new"])))
        if a.get("coverage_beta") is not None and a["coverage_beta"] < 1:
            L.append("- card beta covers %.0f%% of the weight (no beta: %s)" % (
                100 * a["coverage_beta"], ", ".join(a["missing_beta"]) or "-"))
        if a.get("other_share"):
            L.append("- other assets %.1f%% of the account (%s), kept out" % (100 * a["other_share"],
                                                                          ", ".join(a["other_types"])))
        if a.get("shorts"):
            L.append("- short positions kept out: " + ", ".join(a["shorts"]))
        if a.get("first"):
            L.append("- returns %s .. %s (%d, on the dates every included name and SPY traded%s)" % (
                a["first"], a["last"], a["n_obs"], "; SHORT, limited by %s" % a["limiting"] if a.get("short") else ""))
        L.append("")
    if res.get("in_both"):
        L.append("Held in more than one account: " + ", ".join(res["in_both"]) + ".")
        L.append("")
    L.append("Findings: " + ("; ".join(res["findings"]) if res["findings"] else "none") + ".")
    L.append("")
    L.append("Beta, whole account = beta (card) x the equity share, with cash and every other asset at beta 0 "
             "(right for T-bills and CDs, not for long or corporate bonds).")
    L.append("")
    L.append("Beta (card) = sum w x the card's adjusted beta (Ch 6 slides 70-72). Sigma: today's weights on 2 "
             "years of daily returns, as if held throughout (backward-looking). Market share = R^2 of the "
             "account's return on SPY; own beta = that regression's slope. N_eff = 1 / sum w^2. Div. ratio = "
             "sum w sigma_i / sigma_p.")
    L.append("")
    L.append("*Advisory-only · no orders · not financial advice.*")
    return "\n".join(L) + "\n"


def _jsonable(o):
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


# ============================================================================ run
def run(args, log=print, portfolios_fn=None, fetch_fn=None, today=None):
    today = today or market_today()
    date = dt.date.fromisoformat(args.date) if args.date else today
    if date != today:
        log("COULD NOT RUN: positions are today's (%s); %s cannot be read now and is never "
            "reconstructed" % (today, date))
        return 2
    coe = None
    try:
        with open(os.path.join(args.root, "cost_of_equity_%s.json" % date), encoding="utf-8") as fh:
            coe = json.load(fh)
    except (OSError, ValueError):
        coe = None
    try:
        if portfolios_fn is None:
            import schwab_client as SC
            portfolios = SC.get_all_portfolios()
            known = tuple(getattr(SC, "ACCOUNT_LABELS", {}).values())
        else:
            portfolios, known = portfolios_fn(), ()
    except Exception as e:          # noqa: BLE001 - no client, no token: context only
        log("COULD NOT RUN: account read failed (%s: %s)" % (type(e).__name__, e))
        return 2
    if not portfolios:
        log("COULD NOT RUN: no active account returned positions")
        return 2
    held = sorted({h for p in portfolios for h in holdings(p, known)["mv"]})
    try:
        if fetch_fn is None:
            import beta_probe as BP
            _client, candles, errors = BP.fetch_all(held + [MARKET], today, log)
        else:
            candles, errors = fetch_fn(held + [MARKET])
    except Exception as e:          # noqa: BLE001
        log("COULD NOT RUN: price history unavailable (%s: %s)" % (type(e).__name__, e))
        return 2
    res, findings = build(date, portfolios, candles, coe, known)
    res["fetch_errors"] = errors
    stem = args.out or os.path.join(args.root, "portfolio_risk_%s" % date)
    with open(stem + ".md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_md(res))
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=_jsonable)
    for a in res["accounts"] + ([res["combined"]] if res["combined"] else []):
        log("  %-22s names %2d  beta %s  sigma %s  R2 %s  N_eff %s" % (
            a["label"], a["positions"], _n(a.get("beta_card")), _p(a.get("sigma_p")),
            _p(a.get("r2"), 0), _n(a.get("n_eff"), "%.1f")))
    log("portfolio_risk %s: %d account(s); findings %d" % (date, len(res["accounts"]), len(findings)))
    log("wrote %s.md and %s.json" % (stem, stem))
    return 1 if findings else 0


# ============================================================================ selftest
def _candles(start, closes):
    """Synthetic completed-session candles on consecutive weekdays from start."""
    out, d = [], start
    for c in closes:
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        out.append({"date": d, "close": c})
        d += dt.timedelta(days=1)
    return out


def _path(rets, p0=100.0):
    out = [p0]
    for r in rets:
        out.append(out[-1] * (1 + r))
    return out


def _pos(sym, mv, typ="EQUITY", short=0):
    return {"instrument": {"symbol": sym, "assetType": typ}, "marketValue": mv,
            "longQuantity": 0 if short else 1, "shortQuantity": short}


def selftest():
    import random
    import tempfile
    fails, done = [], []

    def ok(name, cond, detail=""):
        print("%s  %s%s" % ("PASS" if cond else "FAIL", name, ("  " + str(detail)) if detail and not cond else ""))
        done.append(name)
        if not cond:
            fails.append(name)

    # 1-2 the course: portfolio beta 0.70 x 0.603 + 0.30 x 1.300 = 0.8121 (Ch 6 slide 71)
    b, cov, miss = weighted_beta({"B": 0.7, "G": 0.3}, {"B": 0.603, "G": 1.3})
    ok("Ch6 portfolio beta 0.8121", abs(b - 0.8121) < 1e-12 and cov == 1.0 and miss == [])
    b2, cov2, miss2 = weighted_beta({"B": 0.7, "G": 0.2, "X": 0.1}, {"B": 0.603, "G": 1.3})
    ok("a name with no beta: re-weighted, covered share and the name printed",
       abs(b2 - (0.7 * 0.603 + 0.2 * 1.3) / 0.9) < 1e-12 and abs(cov2 - 0.9) < 1e-12 and miss2 == ["X"])

    # 3 the course: a 70/30 Blandy-market portfolio's own beta = 0.7 x 0.60269 + 0.3 (linearity)
    market = [.30, .07, .18, -.22, -.14, .10, .26, -.10, -.03, .38]
    blandy = [.26, .15, -.14, -.15, .02, -.18, .42, .30, -.32, .28]
    rp = [0.7 * x + 0.3 * y for x, y in zip(blandy, market)]
    ok("Ch6 data: a 70/30 portfolio's own beta = 0.7 x 0.602691 + 0.3",
       abs(CF.ols(rp, market)["beta"] - (0.7 * 0.602691 + 0.3)) < 5e-6)

    # 4-6 holdings: types, cash equivalents, shorts, labels, no account number
    pf = {"account_number": "12345678", "account_label": "Roth IRA", "cash_available": 500.0,
          "portfolio_value": 10500.0,
          "positions": [_pos("AAA", 6000.0), _pos("BBB", 3000.0, "ETF"), _pos("SWVXX", 400.0, "COLLECTIVE_INVESTMENT"),
                        _pos("XOPT", 600.0, "OPTION"), _pos("SHRT", -100.0, short=5)]}
    h = holdings(pf, ("Roth IRA",))
    ok("holdings: equity and ETF in; cash equivalent, option and short out",
       h["mv"] == {"AAA": 6000.0, "BBB": 3000.0} and set(h["other"]) == {"CASH EQUIVALENT", "OPTION"}
       and h["shorts"] == ["SHRT"])
    ok("weights sum to 1", abs(sum(weights(h["mv"]).values()) - 1) < 1e-12 and abs(weights(h["mv"])["AAA"] - 2 / 3) < 1e-12)
    ok("an unlabelled account never shows its number",
       safe_label({"account_number": "12345678", "account_label": "Account 12345678"}) == "unlabelled account (...678)"
       and safe_label(pf, ("Roth IRA",)) == "Roth IRA")

    # 7-14 returns, sigma identity, R^2, pairs, N_eff, risk shares on synthetic paths
    random.seed(5)
    start = dt.date(2024, 11, 25)
    today = dt.date(2026, 11, 19)
    n = 500
    m = [random.gauss(0.0004, 0.010) for _ in range(n)]
    a = [1.2 * x + random.gauss(0, 0.008) for x in m]
    c = [0.98 * y + random.gauss(0, 0.002) for y in a]            # a near-twin of A
    e = [0.3 * x + random.gauss(0, 0.012) for x in m]
    cand = {"SPY": _candles(start, _path(m)), "AAA": _candles(start, _path(a)),
            "CCC": _candles(start, _path(c)), "EEE": _candles(start, _path(e))}
    mv = {"AAA": 5000.0, "CCC": 3000.0, "EEE": 2000.0}
    hh = {"label": "Individual", "mv": mv, "other": {}, "shorts": [], "cash": 0.0, "total": 10000.0}
    betas = {"AAA": 1.13, "CCC": 1.11, "EEE": 0.53}
    r = account_risk(hh, betas, cand, today)
    w = weights(mv)
    rets, ends, lim = aligned(cand, ["AAA", "CCC", "EEE", "SPY"], today)
    S = {(i, j): _cov(rets[i], rets[j]) for i in w for j in w}
    quad = math.sqrt(sum(w[i] * w[j] * S[(i, j)] for i in w for j in w)) * math.sqrt(ANNUAL)
    ok("sigma_p from the weighted return = sqrt(w' S w)", abs(r["sigma_p"] - quad) < 1e-12, (r["sigma_p"], quad))
    ok("card beta = sum w x beta", abs(r["beta_card"] - (0.5 * 1.13 + 0.3 * 1.11 + 0.2 * 0.53)) < 1e-12)
    ok("own beta = sum w x each name's own OLS beta (same returns)",
       abs(r["beta_hist"] - sum(w[t] * CF.ols(rets[t], rets["SPY"])["beta"] for t in w)) < 1e-9)
    ok("market share = R^2 of the account on SPY, in (0, 1)", 0 < r["r2"] < 1
       and abs(r["r2"] - CF.ols([sum(w[t] * rets[t][i] for t in w) for i in range(len(ends))], rets["SPY"])["r2"]) < 1e-12)
    ok("the near-twin pair is found, the unrelated name is not",
       r["pairs_n"] == 1 and (r["pairs"][0]["a"], r["pairs"][0]["b"]) == ("AAA", "CCC") and r["pairs"][0]["rho"] > 0.95)
    ok("N_eff = 1 / sum w^2; top-1 and top-3", abs(r["n_eff"] - 1 / (0.25 + 0.09 + 0.04)) < 1e-12
       and r["top_name"] == "AAA" and abs(r["top3_w"] - 1.0) < 1e-12)
    ok("risk shares sum to 1 over every name", abs(sum(w[t] * _cov(rets[t], [sum(w[u] * rets[u][i] for u in w)
                                                    for i in range(len(ends))]) for t in w)
                                                  / (CF.sample_sd([sum(w[u] * rets[u][i] for u in w) for i in range(len(ends))]) ** 2) - 1) < 1e-9
       and r["risk_share"][0][0] == "AAA")
    ok("diversification ratio >= 1", r["dr"] >= 1.0)
    ok("2-year window, not short", r["n_obs"] >= MIN_OBS and not r["short"] and r["last"] < str(today))

    # 15-17 the shortening name, missing history, missing beta are each said
    cand2 = dict(cand, NEW=_candles(dt.date(2026, 8, 3), _path([0.001] * 70)))
    r2 = account_risk(dict(hh, mv=dict(mv, NEW=200.0)), dict(betas, NEW=2.0), cand2, today)
    ok("v1.1: a small recent listing is left out of sigma and named; the window stays 2 years",
       not r2["short"] and r2["n_obs"] == r["n_obs"] and [y["ticker"] for y in r2["too_new"]] == ["NEW"]
       and r2["too_new"][0]["returns"] == 70 and r2["findings"] == []
       and abs(r2["beta_card"] - (5000 * 1.13 + 3000 * 1.11 + 2000 * 0.53 + 200 * 2.0) / 10200) < 1e-12
       and "NEW" in r2["weights"])
    r2b = account_risk(dict(hh, mv=dict(mv, NEW=1000.0)), dict(betas, NEW=2.0), cand2, today)
    ok("v1.1: a young name above 5% of the weight is a finding (sigma covers under 95%)",
       any("sigma covers" in f and "NEW" in f for f in r2b["findings"]) and not r2b["short"])
    r2c = account_risk({"label": "Young", "mv": {"NEW": 1.0}, "other": {}, "shorts": [], "cash": 0.0,
                        "total": 1.0}, {"NEW": 2.0}, cand2, today)
    ok("v1.1: when every name is young, the common dates apply: SHORT, limited by, a finding",
       r2c["short"] and r2c["limiting"] == "NEW" and r2c["too_new"] == []
       and any("SHORT" in f for f in r2c["findings"]))
    ok("v1.1: 'limited by' only for a SHORT window; the highest pair is kept below 0.70",
       r["limiting"] is None and r["max_pair"]["rho"] == r["pairs"][0]["rho"]
       and r2["max_pair"] is not None)
    r3 = account_risk(dict(hh, mv=dict(mv, GONE=1000.0)), dict(betas, GONE=0.9), cand, today)
    ok("no price history: sigma over the rest, said", r3["missing_candles"] == ["GONE"]
       and abs(r3["coverage_sigma"] - 10 / 11) < 1e-12 and any("no price history" in f for f in r3["findings"]))
    r4 = account_risk(dict(hh, mv=dict(mv, NOB=3000.0)), betas, dict(cand, NOB=cand["EEE"]), today)
    ok("card beta below 95% covered: a finding", r4["coverage_beta"] < COVERAGE_MIN
       and any("covers" in f for f in r4["findings"]))

    # 18-20 cash, combined book, the build and its findings
    pfs = [pf, {"account_number": "87654321", "account_label": "Individual", "cash_available": 0.0,
                "portfolio_value": 4000.0, "positions": [_pos("AAA", 4000.0)]}]
    cand3 = {"SPY": cand["SPY"], "AAA": cand["AAA"], "BBB": cand["EEE"]}
    coe = {"date": "2026-11-19", "names": {"AAA": {"beta_adj": 1.13}, "BBB": {"beta_adj": 0.53}}}
    res, fnd = build(today, pfs, cand3, coe, ("Roth IRA", "Individual"))
    roth = res["accounts"][0]
    ok("beta incl. cash = beta x invested / liquidation value",
       abs(roth["beta_card_cash"] - roth["beta_card"] * 9000.0 / 10500.0) < 1e-12
       and abs(roth["cash_share"] - 500.0 / 10500.0) < 1e-12)
    ok("combined book sums the same name across accounts",
       res["combined"]["weights"]["AAA"] == round(10000.0 / 13000.0, 4) and res["in_both"] == ["AAA"])
    ok("a clean build has no findings; the other-asset share is printed",
       fnd == [] and abs(roth["other_share"] - 1000.0 / 10500.0) < 1e-12)
    res_x, fnd_x = build(today, pfs, cand3, None, ())
    ok("no cost_of_equity file: card beta NO READ, a finding", res_x["accounts"][0]["beta_card"] is None
       and any("NO READ" in f for f in fnd_x))

    # 22-24 render, privacy, run's refusals
    md = render_md(res)
    ok("render: labels and weights, never a dollar amount or account number",
       "Roth IRA" in md and "12345678" not in md and "87654321" not in md and "$" not in md
       and "10500" not in md and "6000" not in md)
    js = json.dumps(res, default=_jsonable)
    ok("json: no dollar amount or account number either",
       "12345678" not in js and "10500" not in js and "6000.0" not in js)

    class A:
        date = "2026-11-18"
        root = "."
        out = None
    ok("a past date is refused (exit 2)", run(A(), log=lambda *_: None, today=today) == 2)
    with tempfile.TemporaryDirectory() as td:
        class B:
            date = None
            root = td
            out = None
        with open(os.path.join(td, "cost_of_equity_2026-11-19.json"), "w", encoding="utf-8") as fh:
            json.dump(coe, fh)
        rc = run(B(), log=lambda *_: None, portfolios_fn=lambda: pfs,
                 fetch_fn=lambda t: (cand3, {}), today=today)
        wrote = os.path.exists(os.path.join(td, "portfolio_risk_2026-11-19.json"))
        rc0 = run(B(), log=lambda *_: None, portfolios_fn=lambda: [], fetch_fn=lambda t: ({}, {}), today=today)
    ok("run: writes md and json, exit 0 when clean", rc == 0 and wrote)
    ok("run: no account -> exit 2", rc0 == 2)
    print("%d checks, %d failed" % (len(done), len(fails)))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="FINC 5133 step 8: portfolio risk per account (reporting only).")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today; any other date is refused)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--log", help="accepted for value.bat symmetry; not read")
    ap.add_argument("--out", help="output stem (default portfolio_risk_<date>)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
