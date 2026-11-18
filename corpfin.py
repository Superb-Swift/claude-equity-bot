#!/usr/bin/env python3
"""
corpfin.py - the course formulas, in ONE place, each checked against a worked
answer printed in Rob's FINC-5133 materials (Brigham & Ehrhardt, Financial
Management 16e: slides, Build-a-Model solutions, web extensions).

WHY (DP-V7, 2026-11-18)
    claude/FINC5133_CourseReview_2026-11-18.md proposed a cost-of-capital and
    distress layer for the value card. Every tool in that layer (beta_probe.py
    first) imports its arithmetic from here, so a formula is written once and
    tested once. The record's lesson: self-tests miss what live runs catch, and
    the recurring defect class is a tool reporting a value it did not compute.
    A worked answer printed in the textbook is an oracle this project did not
    compute, so a slip (like the 0.03/ROE vs 0.0291/ROE correction of
    2026-10-14) fails HERE before it reaches a card.

    Pure standard library. Reads nothing, writes nothing, makes no network call.
    Nothing here reaches the prompt, a gate, an endpoint or the paste (DP-V1).

USAGE
    python corpfin.py --selftest      the course's golden values; exit 0 = all pass

ANALYST NOTE (syntax)
    Returns are SIMPLE returns throughout, the course's convention. Use the same
    kind for both series in any beta. sigma*sqrt(t) scales by sessions/252.
    The Blume adjustment (0.67 x raw + 0.33) is NOT printed in the course files:
    Ch 25 slide 44 cites "Eq. 25-17" without coefficients. Rob chose the Blume
    form on 2026-11-18 (DP-V7); it is labelled wherever it is printed.

Advisory-only - no orders - not financial advice.
"""
import math
import sys

TRADING_DAYS = 252
BLUME_WEIGHT_RAW = 0.67        # DP-V7 (Rob, 2026-11-18): adjusted = 0.67*raw + 0.33
BLUME_WEIGHT_ONE = 0.33
BLUME_LABEL = "Blume 0.67 x raw + 0.33 (not printed in the course files)"


# ---------------------------------------------------------------- risk and return
def mean(xs):
    return sum(xs) / len(xs)


def sample_sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def correl(xs, ys):
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


def beta(stock, market):
    """Slope of the characteristic line: b = rho * sd_i / sd_M (Ch 6 slide 54)."""
    return correl(stock, market) * sample_sd(stock) / sample_sd(market)


def ols(y, x):
    """Regress y (stock returns) on x (market returns). Returns a dict with the
    slope (beta), intercept (alpha per period), the slope's standard error,
    R^2, rho, n and the t-stat; None when the regression is undefined (fewer
    than 3 points, or no variance in either series)."""
    n = len(y)
    if n != len(x) or n < 3:
        return None
    mx, my = mean(x), mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    slope = sxy / sxx
    intercept = my - slope * mx
    sse = sum((b - intercept - slope * a) ** 2 for a, b in zip(x, y))
    se = math.sqrt(max(sse, 0.0) / (n - 2) / sxx)
    r2 = (sxy * sxy) / (sxx * syy)
    rho = sxy / math.sqrt(sxx * syy)
    return {"beta": slope, "alpha": intercept, "se": se, "r2": r2, "rho": rho,
            "n": n, "t": (slope / se if se > 0 else float("inf"))}


def blume(raw_beta):
    """DP-V7 adjusted beta: 0.67 x raw + 0.33 (see the module's analyst note)."""
    return BLUME_WEIGHT_RAW * raw_beta + BLUME_WEIGHT_ONE


def capm(r_rf, rp_m, b):
    """SML: r_i = r_RF + RP_M * b_i (Ch 6 slides 50-55)."""
    return r_rf + rp_m * b


def jensen_alpha(actual, r_rf, rp_m, b):
    """Return above the SML-required return (Ch 6 slide 73; Ch 25 slide 43)."""
    return actual - capm(r_rf, rp_m, b)


def hamada_unlever(b_levered, tax, debt_to_equity):
    """b_U = b_L / [1 + (1 - T)(D/S)] (Ch 15 solutions, problem 15-13)."""
    return b_levered / (1 + (1 - tax) * debt_to_equity)


def hamada_relever(b_unlevered, tax, debt_to_equity):
    """b_L = b_U [1 + (1 - T)(D/S)]."""
    return b_unlevered * (1 + (1 - tax) * debt_to_equity)


def annualize_sd(sd_per_period, periods_per_year):
    return sd_per_period * math.sqrt(periods_per_year)


# ---------------------------------------------------------------- cost of capital
def cost_of_equity_dcf(d0, p0, g):
    """r_s = D1/P0 + g (Ch 9 slide 21)."""
    return d0 * (1 + g) / p0 + g


def retention_growth(roe, payout):
    """g = (1 - payout) * ROE (Ch 9 slides 27-28)."""
    return (1 - payout) * roe


def bond_ytm(n_periods, pmt, price, par, lo=-0.99, hi=1.0):
    """Periodic yield that prices the bond (bisection; Ch 5, Ch 9 P18)."""
    def pv(r):
        if abs(r) < 1e-12:
            return pmt * n_periods + par
        return pmt * (1 - (1 + r) ** -n_periods) / r + par * (1 + r) ** -n_periods
    for _ in range(200):
        mid = (lo + hi) / 2
        if pv(mid) > price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def wacc(w_d, r_d, tax, w_ps, r_ps, w_s, r_s):
    """WACC = w_d r_d (1 - T) + w_ps r_ps + w_s r_s (Ch 9 slide 40)."""
    return w_d * r_d * (1 - tax) + w_ps * r_ps + w_s * r_s


def eva(nopat, wacc_rate, op_capital):
    """EVA = NOPAT - WACC x operating capital (Ch 2 slide 30)."""
    return nopat - wacc_rate * op_capital


def growth_hurdle(wacc_rate):
    """Ch 7 slide 51: growth adds value only if ROIC > WACC / (1 + WACC)."""
    return wacc_rate / (1 + wacc_rate)


def growth_adds_value(roic, wacc_rate):
    return roic > growth_hurdle(wacc_rate)


# ---------------------------------------------------------------- valuation
def value_ops_constant_growth(fcf0, wacc_rate, g):
    """Vop = FCF0 (1 + g) / (WACC - g), g < WACC (Ch 7 slides 23-26)."""
    if g >= wacc_rate:
        raise ValueError("g must be below WACC")
    return fcf0 * (1 + g) / (wacc_rate - g)


def class_pe_line(ratio_line, r, g, roe=None):
    """P/E at which implied/trailing ROE crosses ratio_line, inverting
    ratio = (P/E)(r - g)/(1 + g) + (g/(1 + g))/ROE (ValuePass 2026-10-14,
    corrected). With roe=None the small ROE term is dropped."""
    small = 0.0 if roe is None else (g / (1 + g)) / roe
    return (ratio_line - small) * (1 + g) / (r - g)


# ---------------------------------------------------------------- distress
def altman_z(nwc, retained_earnings, ebit, mv_equity, book_debt, sales, total_assets):
    """Web Extension 24A, eq. 24A-1. X1..X4 in percent, X5 a ratio. Higher is
    safer; zone of ignorance 1.81-2.99; 50-50 point 2.675. X4's debt is the
    balance-sheet value of total debt incl. all short-term liabilities (note 5)."""
    x1 = 100 * nwc / total_assets
    x2 = 100 * retained_earnings / total_assets
    x3 = 100 * ebit / total_assets
    x4 = 100 * mv_equity / book_debt
    x5 = sales / total_assets
    return 0.012 * x1 + 0.014 * x2 + 0.033 * x3 + 0.006 * x4 + 0.999 * x5


def altman_zone(z):
    if z < 1.81:
        return "DISTRESS"
    if z <= 2.99:
        return "ZONE OF IGNORANCE"
    return "SAFE"


# ---------------------------------------------------------------- options
def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def black_scholes(p, x, t, r_rf, sigma):
    """European call and put (Ch 8 slides 43-58). Returns (call, put, N(d1), N(d2))."""
    d1 = (math.log(p / x) + (r_rf + sigma ** 2 / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    call = p * norm_cdf(d1) - x * math.exp(-r_rf * t) * norm_cdf(d2)
    put = call - p + x * math.exp(-r_rf * t)  # put-call parity
    return call, put, norm_cdf(d1), norm_cdf(d2)


def implied_move(sigma_annual, sessions):
    """One-sigma move over `sessions` trading days: sigma * sqrt(t), t = sessions/252."""
    return sigma_annual * math.sqrt(sessions / float(TRADING_DAYS))


def p_breach(sigma_annual, sessions, band):
    """P(|move| > band) under a zero-mean normal with sd sigma*sqrt(t)."""
    h = implied_move(sigma_annual, sessions)
    return 2 * (1 - norm_cdf(band / h))


# ---------------------------------------------------------------- selftest
def _close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def selftest():
    checks = []

    def ok(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # Ch 6 slides 26-55: Blandy vs the market, 10 annual returns
    market = [.30, .07, .18, -.22, -.14, .10, .26, -.10, -.03, .38]
    blandy = [.26, .15, -.14, -.15, .02, -.18, .42, .30, -.32, .28]
    ok("Ch6 market sd 20.12%", _close(sample_sd(market), 0.2012, 5e-5), "%.4f" % sample_sd(market))
    ok("Ch6 Blandy sd 25.19%", _close(sample_sd(blandy), 0.2519, 5e-5), "%.4f" % sample_sd(blandy))
    ok("Ch6 rho(B,M) 0.4812", _close(correl(blandy, market), 0.4812328, 5e-6))
    ok("Ch6 beta 0.60269", _close(beta(blandy, market), 0.602691, 5e-6), "%.6f" % beta(blandy, market))
    reg = ols(blandy, market)
    ok("ols slope = Ch6 beta", _close(reg["beta"], 0.602691, 5e-6), "%.6f" % reg["beta"])
    ok("ols R^2 = rho^2", _close(reg["r2"], 0.4812328 ** 2, 1e-6))
    se_alt = math.sqrt((1 - reg["r2"]) / (reg["n"] - 2)) * sample_sd(blandy) / sample_sd(market)
    ok("ols SE two routes agree", _close(reg["se"], se_alt, 1e-12), "%.6f" % reg["se"])
    ok("ols refuses n<3 and flat x", ols([1, 2], [1, 2]) is None and ols([1, 2, 3], [1, 1, 1]) is None)
    ok("market on itself: beta 1, R^2 1", _close(ols(market, market)["beta"], 1.0, 1e-12)
       and _close(ols(market, market)["r2"], 1.0, 1e-12))
    ok("Blume(1.5) = 1.335", _close(blume(1.5), 1.335, 1e-12))
    ok("Blume fixed point 1.0", _close(blume(1.0), 1.0, 1e-12))

    # Ch 6 slides 55 & 59: SML at rRF 4%, RPM 5%
    ok("Ch6 r Blandy 7.015%", _close(capm(.04, .05, 0.603), 0.07015, 1e-9))
    ok("Ch6 r average stock 9.00%", _close(capm(.04, .05, 1.0), 0.09, 1e-12))
    ok("Ch6 r Gourmange 10.50%", _close(capm(.04, .05, 1.3), 0.105, 1e-12))
    # Ch 6 slide 73: portfolio managers vs the SML
    ok("Ch6 JJ alpha +1.0%", _close(jensen_alpha(.085, .04, .05, 0.7), 0.010, 1e-12))
    ok("Ch6 CC alpha -1.5%", _close(jensen_alpha(.095, .04, .05, 1.4), -0.015, 1e-12))
    # Ch 6 slide 71: portfolio beta 0.70(0.603) + 0.30(1.300)
    ok("Ch6 portfolio beta 0.8121", _close(0.7 * 0.603 + 0.3 * 1.3, 0.8121, 1e-12))

    # Ch 15 solutions 15-13: BEA unlevered 0.8421, relevered at 40% debt 1.2632
    bu = hamada_unlever(1.0, 0.25, 20 / 80)
    ok("Ch15 BEA b_U 0.8421", _close(bu, 0.8421, 5e-5), "%.4f" % bu)
    ok("Ch15 BEA b_L@40% 1.2632", _close(hamada_relever(bu, 0.25, 40 / 60), 1.2632, 5e-5))

    # Ch 9
    ok("Ch9 retention g 5.7%", _close(retention_growth(.15, .62), 0.057, 1e-12))
    y = bond_ytm(40, 60, 1171.59, 1000)
    ok("Ch9 P18 semiannual YTM 5.0%", _close(y, 0.0500000443, 1e-8), "%.10f" % y)
    ok("Ch9 P18 r_s DCF 13.6982%", _close(cost_of_equity_dcf(3.13, 50, .07), 0.136982, 1e-9))
    ok("Ch9 P18 r_s CAPM 13.70%", _close(capm(.065, .06, 1.2), 0.137, 1e-12))
    ok("Ch9 WACC 10.83%", _close(wacc(.30, .10, .25, .10, .09, .60, .128), 0.1083, 1e-12))
    ok("Ch9 3-method avg 12.8%", _close(mean([.128, .124, .132]), 0.128, 1e-12))

    # Ch 7 slides 25-29 and 49-51; Ch 2 slide 29
    vop = value_ops_constant_growth(24, .11, .05)
    ok("Ch7 Vop $420", _close(vop, 420.0, 1e-9))
    ok("Ch7 price/share $27.00", _close((vop + 100 - 200 - 50) / 10, 27.0, 1e-9))
    ok("Ch7 growth hurdle 8.26%", _close(growth_hurdle(.09), 0.0826, 5e-5))
    ok("Ch7 ROIC 8.0% fails the hurdle", growth_adds_value(.08, .09) is False)
    ok("Ch2 EVA sign negative", eva(8.11, .10, 100) < 0)
    try:
        value_ops_constant_growth(10, .05, .05)
        ok("negative: g >= WACC refused", False)
    except ValueError:
        ok("negative: g >= WACC refused", True)

    # Web Extension 24A: MicroDrive 2018 Altman Z. The text prints 4.46, but its
    # own rounded inputs (23.82, 48.20, 11.08, 292.54, 1.385) sum to 4.4651, so
    # 4.46 is truncated. First run (2026-11-18) failed at 0.005 against 4.46
    # (got 4.4652); the check uses the text's arithmetic. Recorded, not loosened.
    z = altman_z(1610 - 750, 1740, 400, 60 * 31 + 100, 150 + 520, 5000, 3610)
    ok("Web24A MicroDrive Z 4.465 (text prints 4.46)", _close(z, 4.4651, 0.001), "%.4f" % z)
    ok("Web24A zone SAFE", altman_zone(z) == "SAFE")
    ok("Web24A zone edges", altman_zone(1.80) == "DISTRESS" and altman_zone(2.5) == "ZONE OF IGNORANCE")

    # Ch 8 Build-a-Model P08: P 65, X 70, t 0.5, rRF 5%, sigma 0.5
    c, p, nd1, nd2 = black_scholes(65, 70, 0.5, .05, .5)
    ok("Ch8 P08 N(d1) 0.51511", _close(nd1, 0.5151076725, 1e-9))
    ok("Ch8 P08 N(d2) 0.37612", _close(nd2, 0.3761245961, 1e-9))
    ok("Ch8 P08 call $7.8033", _close(c, 7.803335437, 1e-8), "%.9f" % c)
    ok("Ch8 P08 put $11.0750", _close(p, 11.07502928, 1e-7), "%.8f" % p)
    c2 = black_scholes(27, 25, 0.5, .06, .49)[0]
    ok("Ch8 slide 48 call $5.06", _close(c2, 5.06, 0.01), "%.4f" % c2)

    # The class as P/E (ValuePass 10-14): ~34 and ~26 at 9%
    ok("class DEMANDING line 34.3x @9%", _close(class_pe_line(2.00, .09, .03), 34.33, 0.01))
    ok("class UNDEMANDING line 25.8x @9%", _close(class_pe_line(1.50, .09, .03), 25.75, 0.01))

    # sigma*sqrt(t) and the band
    ok("sigma*sqrt(t) 5d @30% = 4.23%", _close(implied_move(.30, 5), 0.0422577, 1e-6))
    ok("P(|move|>3%) 5d @30% = 47.8%", _close(p_breach(.30, 5, .03), 0.4777, 5e-4),
       "%.4f" % p_breach(.30, 5, .03))
    ok("annualize daily sd", _close(annualize_sd(0.01, 252), 0.158745, 1e-6))

    width = max(len(n) for n, _, _ in checks)
    for n, passed, d in checks:
        print("  %s  %s  %s" % ("PASS" if passed else "FAIL", n.ljust(width), d))
    failed = [n for n, passed, _ in checks if not passed]
    print("%d checks, %d PASS, %d FAIL" % (len(checks), len(checks) - len(failed), len(failed)))
    if not failed:
        print("ALL PASS")
    return 0 if not failed else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
