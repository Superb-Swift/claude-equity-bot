"""
discovery_scan.py -- structural and HOLD-population discovery reads on THE MASTER.

Claude Equity Bot · written 2026-09-16 · READ-ONLY on the master; --progress
may append a first arm reading to logs/instrument_readings.json.

WHAT THIS IS
    A single instrument for two jobs:
      * DISCOVERY  (--until 2026-09-16): the exploratory read that produced
        claude/Discovery_Analysis_2026-09-16.md. Rows resolved on or before the
        cutoff are DISCOVERY. Nothing is ever ruled on them.
      * PROSPECTIVE (--since YYYY-MM-DD): the same computations restricted to
        signal dates on/after a start date, for pre-registered confirmatory reads.
        The start date must be AFTER the discovery cutoff or the read is refused.

QUARANTINE (built in, not optional)
    * Outcome reads (sections 4-6) use HOLD rows ONLY. BUY and SELL rows are never
      grouped with their own forward returns here -- KEEP-70, H4, the actionable
      registry and DP-3C-w own those populations, and DP-3C-w's discovery sample
      is never re-read.
    * Non-HOLD rows contribute PRICES only (the assembled close series and each
      name's ex-ante dispersion), never an outcome grouped by signal.
    * Section 3 (generator behaviour) reads signals against TRAILING moves only.

ANALYST NOTES ON SYNTAX
    * Returns: r_h = Price+h / Price at Signal - 1 (the band's basis). The
      close-basis return rc_h = Price+h / close(signal date) - 1 uses the
      assembled close series, so the forward return does NOT share Price at
      Signal with any trailing feature (no shared-price artefact can arise).
    * trail1      = Px[t] / Px[t-1 row] - 1
    * trail5      = Px[t] / Px[t-5 rows] - 1       (h1_lag_trace's row basis)
      trail_skip  = Px[t-1] / Px[t-6 rows] - 1     (ends one row early)
    * conf_dev    = conf - mean(conf over that name's PRIOR rows), min 5 rows.
    * Rank IC     = Spearman rho inside one signal date; one IC per date.
    * t_NW        = mean IC / Newey-West SE with lag h-1 (overlapping windows).
      With ~60-80 dates this is an approximation. At +20d there are only ~4
      non-overlapping windows in the discovery set; no +20d t is trustworthy.
    * n_eff       = n / (1 + (m-1) * ICC1) / h  -- date clustering (ICC1 of
      returns within signal date, m = names per date) and window overlap (h).
      A deliberately crude bound, reported to size the evidence, not to test.

PROSPECTIVE ARMS (DP-3C-ah, ruled 2026-09-16 before any prospective row existed)
    All arms: HOLD rows, signal dates after the discovery cutoff (from
    2026-09-17), close basis (outcome starts at the signal date's close).
      PR-1  IC(dconf, +5d)          read at 144 resolved dates; NW lag 4
            POSITIVE mean IC <= -0.05 AND t <= -2;  NEGATIVE mean IC >= 0
      PR-2  IC(trail_skip, +20d)    read at 125 resolved dates; t from
            non-overlapping 20-date block means (NW at lag 19 is unreliable)
            POSITIVE mean IC <= -0.05 AND block t <= -2;  NEGATIVE mean IC >= 0
      PR-3  IC(damped) - IC(conf), +5d, paired per date (shadow_damper.py,
            lambda 0.5 fixed); read at 144 dates; NW lag 4
            POSITIVE diff >= +0.03 AND t >= 2;  NEGATIVE diff <= 0
      PR-4  rho(conf_dev, trail_skip) on all rows -- REPORT ONLY, no outcome
    Anything between the POSITIVE and NEGATIVE bars at the read date is
    INCONCLUSIVE; the arm is not extended.
    BLINDNESS: before an arm's read date `--progress` prints counts ONLY, and
    `--since` withholds sections 4-6 (the outcome reads). The first reading at
    the read date is recorded to logs/instrument_readings.json and printed as
    recorded afterwards, so an arm cannot be re-read into a better answer.
    D7 (within-name confidence z) is printed by --progress for the latest
    cohort; it is descriptive and reads no outcome.

USAGE
    python discovery_scan.py --progress              # daily: arm counts only
    python discovery_scan.py                         # discovery, cutoff 2026-09-16
    python discovery_scan.py --until 2026-09-16
    python discovery_scan.py --since 2026-09-17      # prospective read
    python discovery_scan.py --master logs\\claude_equity_bot_tracker.xlsx --selftest

Advisory-only - no orders - not financial advice.
"""
import argparse
import datetime as dt
import math
import os
import sys
from collections import defaultdict

import openpyxl

DISCOVERY_CUTOFF = dt.date(2026, 9, 16)
HORIZONS = (5, 10, 20)
PHI_075 = 0.674490          # Phi^-1(0.75): sigma = median|r| / PHI_075 (robust to fat tails)
BAND = 0.03
ETF_LIKE = {"QQQ", "SPY", "VTI", "SCHD", "XLU", "GLD", "USO", "CORN", "AIQ"}


# ----------------------------------------------------------------------------- calendar
def _easter(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31; day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(y, month, day)


def _nth_weekday(y, month, weekday, n):
    d = dt.date(y, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(y, month, weekday):
    d = dt.date(y + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_holidays(y):
    hs = {
        _nth_weekday(y, 1, 0, 3),                 # MLK
        _nth_weekday(y, 2, 0, 3),                 # Presidents
        _easter(y) - dt.timedelta(days=2),        # Good Friday
        _last_weekday(y, 5, 0),                   # Memorial
        _nth_weekday(y, 9, 0, 1),                 # Labor
        _nth_weekday(y, 11, 3, 4),                # Thanksgiving
        _observed(dt.date(y, 7, 4)),
        _observed(dt.date(y, 12, 25)),
    }
    if y >= 2022:
        hs.add(_observed(dt.date(y, 6, 19)))      # Juneteenth
    ny = dt.date(y, 1, 1)
    if ny.weekday() != 5:                         # NYSE does not observe a Saturday New Year on Dec 31
        hs.add(_observed(ny))
    return hs


def sessions(start, end):
    hol = set()
    for y in range(start.year, end.year + 1):
        hol |= nyse_holidays(y)
    out, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in hol:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


# ----------------------------------------------------------------------------- stats
def mean(x):
    return sum(x) / len(x) if x else float("nan")


def sd(x):
    if len(x) < 2:
        return float("nan")
    m = mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def median(x):
    s = sorted(x); n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x); i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(x, y):
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x); syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def nw_mean(x, lag):
    x = [v for v in x if not math.isnan(v)]
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), n
    m = mean(x); e = [v - m for v in x]
    var = sum(v * v for v in e) / n
    for L in range(1, min(lag, n - 1) + 1):
        w = 1 - L / (lag + 1)
        var += 2 * w * sum(e[i] * e[i - L] for i in range(L, n)) / n
    se = math.sqrt(var / n)
    return m, (m / se if se > 0 else float("nan")), n


# ----------------------------------------------------------------------------- load
def load(master):
    wb = openpyxl.load_workbook(master, read_only=True)
    ws = wb["Signals"]
    rows = []
    for i, r in enumerate(ws.iter_rows(min_row=5, max_col=10, values_only=True), start=5):
        if not isinstance(r[0], dt.datetime):
            continue
        rows.append(dict(row=i, d=r[0].date(), tk=r[1], sig=r[3], conf=r[4], dq=r[5],
                         px=r[6], p={5: r[7], 10: r[8], 20: r[9]}))
    wb.close()
    return rows


def build(rows):
    first = min(x["d"] for x in rows)
    S = sessions(first, first + dt.timedelta(days=500))
    IDX = {d: i for i, d in enumerate(S)}
    for x in rows:
        if x["d"] not in IDX:
            raise SystemExit(f"row {x['row']}: {x['d']} is not an NYSE session")
        x["si"] = IDX[x["d"]]
        x["res"] = {h: S[x["si"] + h] for h in HORIZONS}
        x["r"] = {h: (x["p"][h] / x["px"] - 1) if x["p"][h] not in (None, "") else None for h in HORIZONS}

    # assembled close series: every outcome cell is a close for (ticker, resolution date)
    vals = defaultdict(set)
    for x in rows:
        for h in HORIZONS:
            if x["r"][h] is not None:
                vals[(x["tk"], x["res"][h])].add(round(float(x["p"][h]), 4))
    close = {k: next(iter(v)) for k, v in vals.items() if len(v) == 1}
    conflicts = sum(1 for v in vals.values() if len(v) > 1)

    by_tk = defaultdict(list)
    for x in rows:
        by_tk[x["tk"]].append(x)
    for tk, xs in by_tk.items():
        xs.sort(key=lambda z: z["d"])
        confs = []
        for j, x in enumerate(xs):
            x["conf_prev"] = xs[j - 1]["conf"] if j >= 1 else None
            x["dconf"] = (x["conf"] - x["conf_prev"]) if (x["conf"] is not None and x["conf_prev"] is not None) else None
            x["trail1"] = xs[j]["px"] / xs[j - 1]["px"] - 1 if j >= 1 else None
            x["trail5"] = xs[j]["px"] / xs[j - 5]["px"] - 1 if j >= 5 else None
            x["trail_skip"] = xs[j - 1]["px"] / xs[j - 6]["px"] - 1 if j >= 6 else None
            prior = [c for c in confs if c is not None]
            x["conf_dev"] = (x["conf"] - mean(prior)) if (x["conf"] is not None and len(prior) >= 5) else None
            confs.append(x["conf"])
            past = [abs(z["r"][5]) for z in xs if z["r"][5] is not None and IDX[z["res"][5]] <= x["si"] - 1]
            x["sig_ante"] = median(past) / PHI_075 if len(past) >= 10 else None
            c0 = close.get((tk, x["d"]))
            x["rc"] = {h: (x["p"][h] / c0 - 1) if (c0 and x["r"][h] is not None) else None for h in HORIZONS}
    return rows, close, conflicts, IDX


# ----------------------------------------------------------------------------- sections
def by_date(xs):
    g = defaultdict(list)
    for x in xs:
        g[x["d"]].append(x)
    return dict(sorted(g.items()))


def ic_series(xs, fx, fy, minn=8):
    out = []
    for d, grp in by_date(xs).items():
        pts = [(fx(x), fy(x)) for x in grp]
        pts = [(a, b) for a, b in pts if a is not None and b is not None]
        if len(pts) >= minn and len({a for a, _ in pts}) > 2:
            out.append((d, spearman([a for a, _ in pts], [b for _, b in pts])))
    return out


def section1(rows, IDX, P):
    P("1. SAMPLE STRUCTURE AND EFFECTIVE n  (how much independent evidence the rows hold)")
    P(f"   rows {len(rows)}   signal dates {len({x['d'] for x in rows})}   tickers {len({x['tk'] for x in rows})}")
    P("   horizon  resolved  dates  sessions-spanned  non-overlap-windows  date-ICC1   m    n_eff")
    for h in HORIZONS:
        xs = [x for x in rows if x["r"][h] is not None]
        if not xs:
            continue
        span = max(IDX[x["res"][h]] for x in xs) - min(x["si"] for x in xs)
        g = by_date(xs); k = len(g); n = len(xs); m = n / k
        gm = mean([x["r"][h] for x in xs])
        ssb = sum(len(v) * (mean([z["r"][h] for z in v]) - gm) ** 2 for v in g.values())
        sst = sum((x["r"][h] - gm) ** 2 for x in xs)
        msb = ssb / (k - 1); msw = (sst - ssb) / (n - k)
        icc = (msb - msw) / (msb + (m - 1) * msw)
        neff = n / (1 + (m - 1) * icc) / h
        P(f"   +{h:<2}d    {n:7}  {k:5}  {span:16}  {span / h:19.1f}  {icc:9.3f}  {m:4.1f}  {neff:6.0f}")
    P("   n_eff is a crude bound (date clustering x window overlap). Read it as the SIZE of the evidence.")


def section2(rows, P):
    P("\n2. CONFIDENCE STRUCTURE  (what the confidence number is made of)")
    xs = [x for x in rows if x["conf"] is not None]
    for lab, pop in (("ALL ", xs), ("HOLD", [x for x in xs if x["sig"] == "HOLD"])):
        gm = mean([x["conf"] for x in pop]); sst = sum((x["conf"] - gm) ** 2 for x in pop)
        tk = defaultdict(list); dd = defaultdict(list)
        for x in pop:
            tk[x["tk"]].append(x["conf"]); dd[x["d"]].append(x["conf"])
        sb_t = sum(len(v) * (mean(v) - gm) ** 2 for v in tk.values())
        sb_d = sum(len(v) * (mean(v) - gm) ** 2 for v in dd.values())
        within = [x["conf"] - mean(tk[x["tk"]]) for x in pop]
        P(f"   {lab} n={len(pop):5}  sd {100 * sd([x['conf'] for x in pop]):4.1f}pt   ticker share {sb_t / sst:6.1%}"
          f"   date share {sb_d / sst:5.1%}   within-ticker sd {100 * sd(within):4.1f}pt")
    d = [x for x in xs if x["dconf"] is not None]
    tkm = defaultdict(list)
    for x in xs:
        tkm[x["tk"]].append(x["conf"])
    a = [x["conf"] - mean(tkm[x["tk"]]) for x in d]; b = [x["conf_prev"] - mean(tkm[x["tk"]]) for x in d]
    P(f"   row-to-row: unchanged {mean([abs(x['dconf']) < 1e-9 for x in d]):.1%}   |change| <= 2pt "
      f"{mean([abs(x['dconf']) <= 0.02 + 1e-9 for x in d]):.1%}   lag-1 autocorr (within-ticker) {pearson(a, b):+.3f}")
    t = [x for x in xs if x["trail5"] is not None]
    a = [x["conf"] - mean(tkm[x["tk"]]) for x in t]
    P(f"   within-ticker Spearman(conf, trail5) = {spearman(a, [x['trail5'] for x in t]):+.3f}  (n={len(t)})"
      "  <- confidence follows the trailing move")


def section3(rows, P):
    P("\n3. GENERATOR BEHAVIOUR vs TRAILING MOVE  (signals only; NO outcome is read)")
    t = sorted([x for x in rows if x["trail5"] is not None and x["conf"] is not None], key=lambda z: z["trail5"])
    n = len(t)
    P("   quintile of trail5        n   BUY-rate  SELLs  mean-conf  median-trail5")
    for q in range(5):
        grp = t[q * n // 5:(q + 1) * n // 5]
        P(f"   Q{q + 1} {'(most down)' if q == 0 else '(most up)  ' if q == 4 else '           '}      "
          f"{len(grp):5}   {mean([x['sig'] == 'BUY' for x in grp]):7.1%}  {sum(x['sig'] == 'SELL' for x in grp):5}"
          f"   {100 * mean([x['conf'] for x in grp]):7.1f}   {100 * median([x['trail5'] for x in grp]):+11.2f}%")
    buys = defaultdict(int)
    for x in rows:
        if x["sig"] == "BUY":
            buys[x["tk"]] += 1
    tot = sum(buys.values()); top = sorted(buys.items(), key=lambda kv: -kv[1])
    if tot:
        P(f"   BUY supply {tot} rows; top name {top[0][0]} {top[0][1] / tot:.0%}; top 3 {sum(v for _, v in top[:3]) / tot:.0%}"
          f"; SELL rows {sum(x['sig'] == 'SELL' for x in rows)}")


def section4(hold, P):
    P("\n4. HOLD ROWS -- CROSS-SECTIONAL RANK IC vs FORWARD RETURN  (one IC per signal date)")
    P("   feature                              basis   h    dates   mean IC    t_NW   %IC>0")
    feats = [("conf (level)", lambda x: x["conf"]),
             ("conf vs own prior mean", lambda x: x["conf_dev"]),
             ("dconf (change vs prior row)", lambda x: x["dconf"]),
             ("trail1 (latest row move)", lambda x: x["trail1"]),
             ("trail5 (5-row move)", lambda x: x["trail5"]),
             ("trail_skip (5-row move, 1-row gap)", lambda x: x["trail_skip"])]
    for h in HORIZONS:
        for lab, f in feats:
            for basis, fy in (("px", lambda x, h=h: x["r"][h]), ("close", lambda x, h=h: x["rc"][h])):
                if basis == "px" and "trail" not in lab:
                    continue
                ic = ic_series(hold, f, fy)
                m, t, n = nw_mean([v for _, v in ic], h - 1)
                pos = mean([v > 0 for _, v in ic]) if ic else float("nan")
                P(f"   {lab:36} {basis:6} +{h:<2}  {n:6}   {m:+7.3f}  {t:+6.2f}   {pos:5.0%}")
    P("   Spearman inside a date is unchanged by subtracting a date constant, so IC is already a")
    P("   cross-sectional (excess-return) read. 'px' rows share Price at Signal between the feature")
    P("   and the outcome; 'close' rows start the outcome at the close and share no price. Read 'close'.")
    P("   trail5 minus trail_skip is the latest row's move: compare with the trail1 row.")
    # split-half stability for the three reads the record names
    P("   split-half stability (first vs second half of signal dates):")
    ds = sorted({x["d"] for x in hold}); mid = ds[len(ds) // 2]
    for lab, f, h, basis in (("dconf", lambda x: x["dconf"], 5, "close"),
                             ("trail_skip", lambda x: x["trail_skip"], 10, "close"),
                             ("trail_skip", lambda x: x["trail_skip"], 20, "close"),
                             ("conf", lambda x: x["conf"], 20, "px")):
        fy = (lambda x, h=h: x["rc"][h]) if basis == "close" else (lambda x, h=h: x["r"][h])
        ic = ic_series(hold, f, fy)
        a = nw_mean([v for d, v in ic if d < mid], h - 1); b = nw_mean([v for d, v in ic if d >= mid], h - 1)
        P(f"     {lab:11} +{h:<2}d {basis:5}  H1 {a[0]:+.3f} (t {a[1]:+.2f}, n {a[2]})   H2 {b[0]:+.3f} (t {b[1]:+.2f}, n {b[2]})")
    # size of the dconf effect
    P("   dconf bucket -> mean cross-sectional excess +5d (close basis; benchmark = HOLD mean of the date)")
    bench = {}
    for d, grp in by_date(hold).items():
        v = [x["rc"][5] for x in grp if x["rc"][5] is not None]
        if v:
            bench[d] = mean(v)
    for lab, cond in (("down", lambda c: c < -1e-9), ("unchanged", lambda c: abs(c) < 1e-9), ("up", lambda c: c > 1e-9)):
        v = [x["rc"][5] - bench[x["d"]] for x in hold if x["dconf"] is not None and x["rc"][5] is not None and cond(x["dconf"])]
        P(f"     {lab:10} n={len(v):5}  mean {100 * mean(v):+.2f}%  median {100 * median(v):+.2f}%")


def section5(hold, P):
    P("\n5. HOLD CONFIDENCE AS A 'NO BIG MOVE' FORECAST  (within name, |move| scaled by ex-ante sigma)")
    for h in HORIZONS:
        z = [x for x in hold if x["conf_dev"] is not None and x["sig_ante"] and x["rc"][h] is not None]
        if len(z) < 30:
            continue
        absz = [abs(x["rc"][h]) / (x["sig_ante"] * math.sqrt(h / 5)) for x in z]
        for x, a in zip(z, absz):
            x["_absz"] = a
        ic = ic_series(z, lambda x: x["conf_dev"], lambda x: x["_absz"])
        m, t, n = nw_mean([v for _, v in ic], h - 1)
        P(f"   +{h:<2}d  pooled rho {spearman([x['conf_dev'] for x in z], absz):+.3f} (n={len(z)})   per-date IC {m:+.3f}  t_NW {t:+.2f}")
    z = [x for x in hold if x["sig_ante"] and x["rc"][5] is not None]
    if z:
        P(f"   free baseline: rho(ex-ante sigma, |rc5|) = {spearman([x['sig_ante'] for x in z], [abs(x['rc'][5]) for x in z]):+.3f}  (n={len(z)})")


def section6(hold, P):
    P("\n6. DATA QUALITY -- POOLED vs WITHIN-NAME  (HOLD, +5d, band basis |r5| > 3%)")
    z = [x for x in hold if x["r"][5] is not None and x["dq"] in ("HIGH", "MEDIUM")]
    br = lambda xs: mean([abs(x["r"][5]) > BAND for x in xs])
    hi = [x for x in z if x["dq"] == "HIGH"]; me = [x for x in z if x["dq"] == "MEDIUM"]
    P(f"   pooled breach  HIGH {br(hi):.1%} (n={len(hi)})   MEDIUM {br(me):.1%} (n={len(me)})   gap {100 * (br(hi) - br(me)):+.1f}pt")
    num = den = 0.0; k = 0
    for tk in sorted({x["tk"] for x in z}):
        a = [x for x in hi if x["tk"] == tk]; b = [x for x in me if x["tk"] == tk]
        if a and b:
            w = len(a) * len(b) / (len(a) + len(b)); num += w * (br(a) - br(b)); den += w; k += 1
    if den:
        P(f"   within-name (Mantel-Haenszel) gap HIGH-MEDIUM {100 * num / den:+.1f}pt   across {k} names carrying both")
        P("   The difference between the two gaps is NAME COMPOSITION, not data quality.")


def section7(rows, close, IDX, P):
    P("\n7. PRICE-SERIES STRUCTURE  (daily close-to-close correlation with SPY; provenance check)")
    by = defaultdict(dict)
    for (tk, d), v in close.items():
        by[tk][d] = v
    spy = by.get("SPY", {})
    def daily(series):
        out = {}
        for d, v in series.items():
            i = IDX[d]
            prev = [p for p in series if IDX[p] == i - 1]
            if prev:
                out[d] = v / series[prev[0]] - 1
        return out
    rs = daily(spy)
    res = []
    for tk in sorted(by):
        if tk == "SPY":
            continue
        r = daily(by[tk]); common = [d for d in r if d in rs]
        if len(common) >= 30:
            res.append((pearson([r[d] for d in common], [rs[d] for d in common]), tk, len(common)))
    for c, tk, n in sorted(res):
        P(f"   {tk:5} {c:+.2f}  (n={n}){'   fund/ETF' if tk in ETF_LIKE else ''}")
    P("   Broad-index funds should sit near +0.9; single large caps typically +0.4..+0.8.")
    P("   Low values on single names were first flagged [?] on 2026-08-17 (Valuation Evidence Pack C-3).")


# ----------------------------------------------------------------------------- prospective arms
PROSPECTIVE_START = DISCOVERY_CUTOFF + dt.timedelta(days=1)
ARMS = {
    "PR-1": dict(h=5, need=144, label="dconf -> +5d (close)"),
    "PR-2": dict(h=20, need=125, label="trail_skip -> +20d (close)"),
    "PR-3": dict(h=5, need=144, label="shadow damper: IC(damped) - IC(conf), +5d"),
}


def _block_t(values, block=20):
    """t-statistic from non-overlapping block means (PR-2)."""
    blocks = [mean(values[i:i + block]) for i in range(0, len(values) - block + 1, block)]
    if len(blocks) < 3:
        return float("nan"), len(blocks)
    s = sd(blocks)
    return (mean(blocks) / (s / math.sqrt(len(blocks))) if s > 0 else float("nan")), len(blocks)


def arm_series(rows, arm):
    """Per-date values for one arm over PROSPECTIVE HOLD rows (resolved only)."""
    hold = [x for x in rows if x["sig"] == "HOLD" and x["d"] >= PROSPECTIVE_START]
    h = ARMS[arm]["h"]
    if arm == "PR-1":
        return ic_series(hold, lambda x: x["dconf"], lambda x: x["rc"][h])
    if arm == "PR-2":
        return ic_series(hold, lambda x: x["trail_skip"], lambda x: x["rc"][h])
    if arm == "PR-3":
        a = dict(ic_series(hold, lambda x: x.get("damped"), lambda x: x["rc"][h]))
        b = dict(ic_series(hold, lambda x: x["conf"], lambda x: x["rc"][h]))
        return [(d, a[d] - b[d]) for d in sorted(set(a) & set(b))]
    raise KeyError(arm)


def arm_verdict(arm, series):
    vals = [v for _, v in series if not math.isnan(v)]
    if arm == "PR-2":
        m = mean(vals)
        t, k = _block_t(vals)
        tdesc = f"block t {t:+.2f} ({k} blocks)"
    else:
        m, t, _n = nw_mean(vals, ARMS[arm]["h"] - 1)
        tdesc = f"t_NW {t:+.2f}"
    if arm in ("PR-1", "PR-2"):
        v = ("POSITIVE" if (m <= -0.05 and t <= -2) else
             "NEGATIVE" if m >= 0 else "INCONCLUSIVE")
    else:
        v = ("POSITIVE" if (m >= 0.03 and t >= 2) else
             "NEGATIVE" if m <= 0 else "INCONCLUSIVE")
    return v, m, t, tdesc


def progress_lines(rows, only=None, record=True):
    """Counts for each arm; a verdict only at (and recorded from) its read date."""
    try:
        import shadow_damper
        if any("damped" not in x for x in rows):
            shadow_damper.attach(rows)
    except Exception:                                    # noqa: BLE001
        pass
    try:
        import rulings
    except Exception:                                    # noqa: BLE001
        rulings = None
    out = [f"PROSPECTIVE ARMS (DP-3C-ah) - signal dates from {PROSPECTIVE_START}; "
           f"counts only before each read date"]
    pros = [x for x in rows if x["d"] >= PROSPECTIVE_START]
    hold = [x for x in pros if x["sig"] == "HOLD"]
    out.append(f"  prospective sessions {len({x['d'] for x in pros})}   HOLD rows {len(hold)}")
    for arm, cfg in ARMS.items():
        if only and arm not in only:
            continue
        series = arm_series(rows, arm)
        n = len(series)
        prior = rulings.readings(arm) if rulings else []
        if prior:
            e = prior[0]
            out.append(f"  {arm} {cfg['label']:<44} READ {e['date']} (recorded): "
                       f"{e['detail'].get('verdict')}  mean {e['detail'].get('mean')}  "
                       f"{e['detail'].get('t')}")
        elif n >= cfg["need"]:
            v, m, t, tdesc = arm_verdict(arm, series)
            out.append(f"  {arm} {cfg['label']:<44} READ DATE REACHED ({n} dates): "
                       f"{v}  mean {m:+.3f}  {tdesc}")
            if record and rulings:
                last = series[-1][0]
                rulings.record_reading(arm, last, v == "POSITIVE",
                                       detail=dict(verdict=v, mean=round(m, 4),
                                                   t=tdesc, dates=n))
        else:
            out.append(f"  {arm} {cfg['label']:<44} {n:>4} / {cfg['need']} resolved dates   [BLIND]")
    if not only or "PR-4" in only:
        pts = [(x["conf_dev"], x["trail_skip"]) for x in pros
               if x["conf_dev"] is not None and x["trail_skip"] is not None]
        if len(pts) >= 10:
            r = spearman([a for a, _ in pts], [b for _, b in pts])
            out.append(f"  PR-4 rho(conf_dev, trail_skip), report only: {r:+.3f} (n {len(pts)}; "
                       f"discovery +0.32 before 2026-07-07, +0.49 after)")
        else:
            out.append(f"  PR-4 rho(conf_dev, trail_skip), report only: n {len(pts)} (< 10)")
    if not only:
        # D7: within-name confidence z on the latest cohort (descriptive, no outcome)
        last = max(x["d"] for x in rows)
        by = defaultdict(list)
        for x in rows:
            if x["conf"] is not None and x["d"] < last:
                by[x["tk"]].append(x["conf"])
        zs = []
        for x in rows:
            if x["d"] == last and x["conf"] is not None and len(by[x["tk"]]) >= 10:
                s_ = sd(by[x["tk"]])
                if s_ > 0:
                    zs.append((x["tk"], (x["conf"] - mean(by[x["tk"]])) / s_))
        far = sorted([z for z in zs if abs(z[1]) >= 2], key=lambda z: z[1])
        out.append(f"  D7 {last}: {len(zs)} names scored against their own history; |z| >= 2: "
                   + (", ".join(f"{t} {z:+.1f}" for t, z in far) or "none"))
    return out


# ----------------------------------------------------------------------------- selftest
def selftest():
    checks = [
        (_easter(2026) - dt.timedelta(days=2), dt.date(2026, 4, 3)),
        (_nth_weekday(2026, 1, 0, 3), dt.date(2026, 1, 19)),
        (_last_weekday(2026, 5, 0), dt.date(2026, 5, 25)),
        (_observed(dt.date(2026, 7, 4)), dt.date(2026, 7, 3)),
        (_nth_weekday(2026, 9, 0, 1), dt.date(2026, 9, 7)),
        (_nth_weekday(2026, 11, 3, 4), dt.date(2026, 11, 26)),
    ]
    S = sessions(dt.date(2026, 5, 1), dt.date(2026, 12, 31)); I = {d: i for i, d in enumerate(S)}
    checks += [
        (S[I[dt.date(2026, 8, 26)] + 5], dt.date(2026, 9, 2)),
        (S[I[dt.date(2026, 8, 26)] + 20], dt.date(2026, 9, 24)),
        (S[I[dt.date(2026, 7, 29)] + 20], dt.date(2026, 8, 26)),
        (dt.date(2026, 8, 28) in I, True),
        (dt.date(2026, 9, 7) in I, False),
        (round(spearman([1, 2, 3, 4], [1, 3, 2, 4]), 6), 0.8),
        (round(spearman([1, 1, 2, 3], [1, 2, 3, 4]), 6), round(0.9486832980505138, 6)),
    ]
    # DP-3C-ah arm mechanics: verdict branches and the block t
    checks += [
        (arm_verdict("PR-1", [(i, -0.10 + (0.02 if i % 2 else -0.02)) for i in range(144)])[0], "POSITIVE"),
        (arm_verdict("PR-1", [(i, 0.01) for i in range(144)])[0], "NEGATIVE"),
        (arm_verdict("PR-3", [(i, 0.05 + (0.01 if i % 2 else -0.01)) for i in range(144)])[0], "POSITIVE"),
        (arm_verdict("PR-3", [(i, -0.01) for i in range(144)])[0], "NEGATIVE"),
        (_block_t([0.0] * 40)[1], 2),
        (PROSPECTIVE_START, dt.date(2026, 9, 17)),
    ]
    bad = [(i, a, b) for i, (a, b) in enumerate(checks) if a != b]
    for i, a, b in bad:
        print(f"  [FAIL] check {i}: got {a!r} expected {b!r}")
    print(f"selftest: {len(checks) - len(bad)}/{len(checks)} pass")
    return not bad


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", "--tracker", dest="master",
                    default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--progress", action="store_true",
                    help="prospective arm counts only (daily runner); verdicts only at read dates")
    ap.add_argument("--no-record", action="store_true")
    ap.add_argument("--until", type=dt.date.fromisoformat, help="discovery: keep outcomes resolved on/before this date")
    ap.add_argument("--since", type=dt.date.fromisoformat, help="prospective: keep signal dates on/after this date")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest and not selftest():
        sys.exit(1)
    if "with_registry" in os.path.basename(a.master):
        sys.exit("refused: this reads THE MASTER, not the generated report copy")
    if a.since and a.since <= DISCOVERY_CUTOFF:
        sys.exit(f"refused: --since {a.since} overlaps the discovery set (cutoff {DISCOVERY_CUTOFF}). "
                 "A prospective read must start after the cutoff.")
    until = a.until or (None if a.since else DISCOVERY_CUTOFF)

    rows = load(a.master)
    rows, close, conflicts, IDX = build(rows)
    if a.progress:
        for line in progress_lines(rows, record=not a.no_record):
            print(line)
        return
    # the mode filter applies AFTER features are built, so trailing features see full history
    keep = rows
    if a.since:
        keep = [x for x in rows if x["d"] >= a.since]
    for x in keep:
        for h in HORIZONS:
            if until and x["r"][h] is not None and x["res"][h] > until:
                x["r"][h] = None; x["rc"][h] = None
    if not keep:
        print(f"No rows on or after {a.since} yet - nothing to read. "
              f"Use --progress for the arm counts.")
        return
    mode = f"PROSPECTIVE since {a.since}" if a.since else f"DISCOVERY until {until}"
    hold = [x for x in keep if x["sig"] == "HOLD"]

    P = print
    P("=" * 100)
    P(f"DISCOVERY SCAN -- {mode}")
    P(f"master {a.master}   rows {len(keep)} (HOLD {len(hold)})   close keys {len(close)}  (skipped as conflicting: {conflicts})")
    P("READ-ONLY. Outcome reads use HOLD rows only. Nothing here is a ruling.")
    P("=" * 100)
    section1(keep, IDX, P); section2(keep, P); section3(keep, P)
    if a.since:
        # BLIND (DP-3C-ah): the outcome reads wait for the PR-1 read date.
        n1 = len(arm_series(rows, "PR-1"))
        if n1 < ARMS["PR-1"]["need"]:
            P(f"\n4-6. OUTCOME READS WITHHELD - {n1} of {ARMS['PR-1']['need']} resolved "
              f"prospective dates. Use --progress for counts.")
        else:
            section4(hold, P); section5(hold, P); section6(hold, P)
    else:
        section4(hold, P); section5(hold, P); section6(hold, P)
    section7(keep, close, IDX, P)
    P("\nAdvisory-only - no orders - not financial advice.")


if __name__ == "__main__":
    main()
