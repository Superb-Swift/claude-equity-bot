#!/usr/bin/env python3
"""
episodes.py — one coalescing rule, shared by every instrument that counts episodes.

WHY THIS EXISTS (2026-09-16, DP-3C-y / DP-3C-ab implementation)
    DP-3C-m says consecutive qualifying signals on one ticker are ONE episode.
    DP-3C-ab says "consecutive" means consecutive COHORTS (sessions on which the
    bot ran), not consecutive trading sessions, so the bot-absent sessions
    2026-08-28 and 2026-08-31 do not split an episode.
    DP-3C-y rules that KEEP-70 is read on the EPISODE basis, scored on the
    OPENING row of each episode.

    Before this module the rule lived only inside build_actionable_registry.py.
    monitor_strip and the near-miss registry counted rows, so the ruled basis
    could not be printed by the instrument that prints the verdict. Putting the
    rule in one place is how the three tools are kept from disagreeing about
    what an episode is.

VALIDATION
    On the master cut at 2026-09-02 (near-miss BUY, 60 <= conf < 70, +5d
    resolved on or before the cut) this module reproduces DP-3C-y's ruled
    figures exactly: row basis 28/52, episode basis 11/20, 22 episodes.
    `python episodes.py --selftest` checks the rule on synthetic data,
    including the bot-absent gap.

WHAT THIS MODULE IS NOT
    It filters nothing. The caller chooses the population (the band, the
    signal type, the era); this module only groups what it is handed. The
    population is chosen BEFORE coalescing: an episode is a run of consecutive
    cohorts on which the ticker had a QUALIFYING row.
"""

import datetime as dt
import sys


def cohort_index(cohort_dates):
    """Map each cohort date to its position in the sorted cohort calendar."""
    return {d: i for i, d in enumerate(sorted(set(cohort_dates)))}


def coalesce(rows, cohort_dates, *, ticker=lambda r: r["ticker"],
             date=lambda r: r["date"]):
    """Group qualifying rows into DP-3C-m/ab episodes.

    rows          iterable of row objects (dicts by default)
    cohort_dates  every date on which the bot ran (the master's own calendar)

    Returns a list of episodes, oldest first. Each episode is a dict:
        id       "<TICKER>-<YYYYMMDD of opening row>"
        ticker   ticker
        opened   date of the opening row
        closed   date of the last row
        rows     the rows, oldest first
        open_row the opening row (the one DP-3C-y scores)
    Two rows on the same ticker and date (e.g. one per account) belong to the
    same episode; the first one seen is the opening row.
    """
    idx = cohort_index(cohort_dates)
    by_tk = {}
    for r in rows:
        by_tk.setdefault(ticker(r), []).append(r)
    out = []
    for tk, rs in by_tk.items():
        rs = sorted(rs, key=date)
        cur = None
        prev_i = None
        for r in rs:
            i = idx.get(date(r))
            if i is None:
                # A row on a date that is not a cohort date cannot be placed on
                # the calendar; it opens its own episode rather than joining one.
                i = -10 ** 9
            same_day = cur is not None and date(r) == cur["closed"]
            if cur is not None and (same_day or (prev_i is not None and i == prev_i + 1)):
                cur["rows"].append(r)
                cur["closed"] = date(r)
            else:
                cur = dict(id=f"{tk}-{date(r):%Y%m%d}", ticker=tk,
                           opened=date(r), closed=date(r), rows=[r], open_row=r)
                out.append(cur)
            prev_i = i
    out.sort(key=lambda e: (e["opened"], e["ticker"]))
    return out


def opening_rows(episodes):
    return [e["open_row"] for e in episodes]


def rate_line(hit, n):
    return f"{hit}/{n} = {100.0 * hit / n:.2f}%" if n else f"{hit}/0 = n/a"


# --------------------------------------------------------------------------- #
# DP-3C-w prospective arm — ONE definition, used by the actionable registry
# (which records the reading) and the monitor strip (which only displays it).
# --------------------------------------------------------------------------- #
DP3CW_ERA_START = dt.date(2026, 8, 11)     # DP-3C-o: the post-era begins
DP3CW_OPENED = dt.date(2026, 9, 3)         # only episodes opening on/after this
DP3CW_MIN_N = 10
DP3CW_MIN_TICKERS = 4
DP3CW_POS_RHO = -0.40


def spearman(xs, ys):
    """Spearman rho with average ranks for ties. None if undefined."""
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / (sxx * syy) ** 0.5


def dp3cw_arm(rows, cohort_dates):
    """The DP-3C-w prospective arm, counted blind.

    rows: dicts with date, ticker, signal ("BUY"...), conf (PERCENT), ret5
          (fraction, or None while unresolved). Every master row may be passed;
          the population is selected here so there is one definition.

    Population (DP-3C-w, 2026-09-03): post-DP-3C-o BUY rows with conf >= 60
    (gate-clearing and near-miss pooled), coalesced under DP-3C-m/ab over the
    WHOLE post-era, scored on the opening row. Only episodes OPENING on or
    after 2026-09-03 enter; an episode already open that day is discovery.

    BLINDNESS (DP-3C-ah): rho is computed ONLY once n >= 10 qualifying
    episodes have resolved. Below that the result carries counts only, so no
    one can look at the sign early.
    """
    pop = [r for r in rows
           if r["date"] >= DP3CW_ERA_START and r.get("signal") == "BUY"
           and isinstance(r.get("conf"), (int, float)) and r["conf"] >= 60]
    eps = [e for e in coalesce(pop, cohort_dates) if e["opened"] >= DP3CW_OPENED]
    opened = [e["open_row"] for e in eps]
    resolved = [r for r in opened if r.get("ret5") is not None]
    tickers_all = sorted({r["ticker"] for r in opened})
    tickers_res = sorted({r["ticker"] for r in resolved})
    out = dict(n_open=len(opened), n_resolved=len(resolved),
               tickers=tickers_all, tickers_resolved=tickers_res,
               episodes=[e["id"] for e in eps],
               read_ready=len(resolved) >= DP3CW_MIN_N,
               rho=None, verdict="COLLECTING — counts only, no rho before n = %d"
               % DP3CW_MIN_N)
    if out["read_ready"]:
        rho = spearman([r["conf"] for r in resolved], [r["ret5"] for r in resolved])
        out["rho"] = rho
        if rho is None:
            out["verdict"] = "READ — rho undefined (no variation)"
        elif rho <= DP3CW_POS_RHO and len(tickers_res) >= DP3CW_MIN_TICKERS:
            out["verdict"] = "POSITIVE — the inversion is a property of the generator"
        elif rho >= 0:
            out["verdict"] = "NEGATIVE"
        elif rho <= DP3CW_POS_RHO:
            out["verdict"] = ("INSUFFICIENT — rho meets the bar but only %d ticker(s) "
                              "of %d; continue to the exit review" %
                              (len(tickers_res), DP3CW_MIN_TICKERS))
        else:
            out["verdict"] = ("NOT DECIDED at this n — between the bars; read once "
                              "more at the Phase 3-C exit review")
    return out


# --------------------------------------------------------------------------- #
# KEEP-70 on the ruled basis (DP-3C-y) — ONE definition, used by the near-miss
# registry and the monitor strip.
# --------------------------------------------------------------------------- #
KEEP70_BAR = 50.0     # "<= 50.0% supports keeping 70" (DP-3C-y wording)


def keep70(rows, cohort_dates, resolved_through=None):
    """KEEP-70 on both bases.

    rows: dicts with date, ticker, signal, conf (PERCENT), ret5 (fraction or
          None). Population: BUY rows with 60 <= conf < 70 (the near-miss band),
          coalesced under DP-3C-m/ab and scored on the OPENING row (DP-3C-y).
    A "hit" is a rejected BUY that would have paid: ret5 > 0.
    resolved_through: count a +5d result only if the row's +5d session is on or
          before this date (used to reproduce a dated reading). Requires
          trading_calendar when given.
    """
    pop = [r for r in rows if r.get("signal") == "BUY"
           and isinstance(r.get("conf"), (int, float)) and 60 <= r["conf"] < 70]

    def res(r):
        if r.get("ret5") is None:
            return None
        if resolved_through is not None:
            import trading_calendar as _tc
            if _tc.shift_sessions(r["date"], 5) > resolved_through:
                return None
        return r["ret5"]

    row_res = [res(r) for r in pop]
    row_n = sum(1 for v in row_res if v is not None)
    row_hit = sum(1 for v in row_res if v is not None and v > 0)
    eps = coalesce(pop, cohort_dates)
    ep_res = [res(e["open_row"]) for e in eps]
    ep_n = sum(1 for v in ep_res if v is not None)
    ep_hit = sum(1 for v in ep_res if v is not None and v > 0)
    rate = (100.0 * ep_hit / ep_n) if ep_n else None
    return dict(
        rows=len(pop), row_n=row_n, row_hit=row_hit,
        row_rate=(100.0 * row_hit / row_n) if row_n else None,
        episodes=len(eps), ep_n=ep_n, ep_hit=ep_hit, ep_rate=rate,
        verdict=("NO RESOLVED EPISODES" if rate is None else
                 "SUPPORTED" if rate <= KEEP70_BAR else "NOT SUPPORTED"),
    )


def selftest():
    D = dt.date
    cal = [D(2026, 8, 26), D(2026, 8, 27), D(2026, 9, 1), D(2026, 9, 2),
           D(2026, 9, 3), D(2026, 9, 8)]           # 08-28 and 08-31 bot-absent
    rows = [
        dict(ticker="NVDA", date=D(2026, 8, 27), k=1),
        dict(ticker="NVDA", date=D(2026, 9, 1), k=2),   # spans the absent days
        dict(ticker="NVDA", date=D(2026, 9, 2), k=3),
        dict(ticker="NVDA", date=D(2026, 9, 8), k=4),   # 09-03 missing -> new ep
        dict(ticker="MSFT", date=D(2026, 8, 26), k=5),
        dict(ticker="MSFT", date=D(2026, 8, 26), k=6),  # same day, 2nd account
        dict(ticker="MSFT", date=D(2026, 9, 2), k=7),
    ]
    eps = coalesce(rows, cal)
    ok = True

    def chk(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    chk("4 episodes", len(eps) == 4)
    nv = [e for e in eps if e["ticker"] == "NVDA"]
    chk("NVDA 08-27 -> 09-02 is one episode across bot-absent days (DP-3C-ab)",
        len(nv[0]["rows"]) == 3 and nv[0]["closed"] == D(2026, 9, 2))
    chk("a missing cohort splits the episode", nv[1]["opened"] == D(2026, 9, 8))
    ms = [e for e in eps if e["ticker"] == "MSFT"]
    chk("same-day second row joins its episode", len(ms[0]["rows"]) == 2)
    chk("opening row is the first row seen (DP-3C-y)", ms[0]["open_row"]["k"] == 5)
    chk("non-adjacent cohort opens a new episode", len(ms) == 2)
    # DP-3C-w arm: blind below n, correct population, verdict branches.
    cal2 = [D(2026, 8, 31 - k) for k in range(0)] + [
        D(2026, 9, 1) + dt.timedelta(days=k) for k in range(0, 40)]
    arm_rows = [dict(ticker="OLD", date=D(2026, 9, 2), signal="BUY", conf=75, ret5=0.01),
                dict(ticker="OLD", date=D(2026, 9, 3), signal="BUY", conf=75, ret5=0.01),
                dict(ticker="LOW", date=D(2026, 9, 4), signal="BUY", conf=55, ret5=0.01),
                dict(ticker="HLD", date=D(2026, 9, 4), signal="HOLD", conf=75, ret5=0.01)]
    a = dp3cw_arm(arm_rows, cal2)
    chk("episode open before 09-03 never enters; conf < 60 and HOLD excluded",
        a["n_open"] == 0)
    many = []
    for i in range(10):
        many.append(dict(ticker="T%d" % (i % 5), date=D(2026, 9, 4) + dt.timedelta(days=3 * i),
                         signal="BUY", conf=60 + i, ret5=(None if i == 9 else 0.05 - 0.01 * i)))
    a = dp3cw_arm(many, cal2)
    chk("9 resolved -> blind (no rho)", a["n_resolved"] == 9 and a["rho"] is None)
    many[9]["ret5"] = -0.05
    a = dp3cw_arm(many, cal2)
    chk("10 resolved, 5 tickers, rho = -1 -> POSITIVE",
        a["rho"] is not None and a["verdict"].startswith("POSITIVE"))
    chk("spearman ties", abs(spearman([1, 2, 2, 3], [1, 2, 2, 3]) - 1.0) < 1e-12)
    print("  RESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
