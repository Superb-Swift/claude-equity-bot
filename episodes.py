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

2026-09-25 (DP-3C-ar, DP-3C-au)
    coalesce() takes an optional `dropouts` set: a run-fault gap (the run was
    asked about a ticker and wrote no row) is removed from THAT ticker's
    calendar, so it bridges rather than splits. dropouts_from_logs() is the one
    definition of a dropout. keep70() now returns its margin to the bar and a
    KNIFE-EDGE flag. build_actionable_registry.assign_episodes() now calls
    coalesce() instead of keeping a private copy of the rule (verified
    identical on the live master with dropouts=None: 16 episodes, same ids).

2026-11-18 (DP-V9; Rob, 14:58 CT: "I'm comfortable ruling your recommendations")
    Adds PR-6 (F1-a, claude/F1_CAPMAlpha_PreRegistration_2026-11-18.md):
    gate-cleared BUY episodes scored on abnormal return AR = r - beta * r_SPY,
    beta point in time from cost_of_equity_<D>.json. pr6_arm() is counted
    blind; build_actionable_registry prints it nightly and records its one
    read. The bars are in the PR-6 header below, fixed before its first row.
    Nothing here changes coalesce(), dp3cw_arm() or keep70().

WHAT THIS MODULE IS NOT
    It filters nothing. The caller chooses the population (the band, the
    signal type, the era); this module only groups what it is handed. The
    population is chosen BEFORE coalescing: an episode is a run of consecutive
    cohorts on which the ticker had a QUALIFYING row.
"""

import datetime as dt
import os
import re
import sys


def cohort_index(cohort_dates):
    """Map each cohort date to its position in the sorted cohort calendar."""
    return {d: i for i, d in enumerate(sorted(set(cohort_dates)))}


# --------------------------------------------------------------------------- #
# DP-3C-ar (RULED 2026-09-25) — a ticker the run was ASKED about but never wrote.
#
#   DP-3C-ab bridges sessions on which the bot did not run. It said nothing
#   about a session on which the bot ran, was asked about a ticker, and failed
#   to write that ticker's row (a transport fault, logged as
#   "No quote data for X — skipping."). Until this ruling such a gap SPLIT the
#   episode, so a Schwab timeout could manufacture an episode: MSFT 2026-09-23
#   split MSFT-20260903 and opened MSFT-20260924, which became DP-3C-w's 10th
#   opened episode two sessions before its read.
#
#   RULE: that cohort is ABSENT FOR THAT TICKER ONLY. It neither splits nor
#   extends an episode; the episode bridges it exactly as DP-3C-ab bridges a
#   bot-absent day, and the bridged date is recorded on the episode.
#   EVIDENCE GATE (mechanical, never judged): the skip line must be in the
#   session's own log, the same log must carry no Signal JSON row for the
#   ticker, and the master must carry no row for (ticker, date). Anything else
#   is not a dropout and keeps its old behaviour.
#   COST, DISCLOSED: the bridged session's value is unknown; the row might not
#   have qualified. DP-3C-ab accepted the same assumption for bot-absent days.
# --------------------------------------------------------------------------- #
# Two run-fault lines exist in main.py.process_ticker(): the quote skip, and the
# catch-all "Error processing X: ..." (never yet seen in the archive, same
# class). Either one, WITH NO ROW WRITTEN for X in that log, is a dropout.
DROPOUT_RE = re.compile(r"(?:WARNING \| No quote data for (?P<tk>[A-Z][A-Z.\-]*) \u2014 skipping\."
                        r"|ERROR \| Error processing (?P<tk2>[A-Z][A-Z.\-]*):)")
_SIGNAL_TK_RE = re.compile(r'Signal JSON: \{"ticker": "(?P<tk>[A-Z][A-Z.\-]*)"')
_LOG_DATE_RE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})")


def dropouts_from_logs(paths, present=None):
    """{(ticker, date)} run-fault dropouts under DP-3C-ar.

    paths    signals logs (use signal_logs.discover() so the archive is read)
    present  optional iterable of (ticker, date) pairs that DO have a master
             row; any such pair is never a dropout, whatever a log says.
    """
    present = set(present or ())
    skipped, written = {}, {}
    for p in paths:
        m = _LOG_DATE_RE.search(os.path.basename(p))
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        skipped.setdefault(d, set()).update(x.group("tk") or x.group("tk2")
                                            for x in DROPOUT_RE.finditer(text))
        written.setdefault(d, set()).update(x.group("tk") for x in _SIGNAL_TK_RE.finditer(text))
    out = set()
    for d, tks in skipped.items():
        for tk in tks - written.get(d, set()):
            if (tk, d) not in present:
                out.add((tk, d))
    return out


def coalesce(rows, cohort_dates, *, ticker=lambda r: r["ticker"],
             date=lambda r: r["date"], dropouts=None):
    """Group qualifying rows into DP-3C-m/ab/ar episodes.

    rows          iterable of row objects (dicts by default)
    cohort_dates  every date on which the bot ran (the master's own calendar)
    dropouts      optional {(ticker, date)} from dropouts_from_logs(): those
                  cohorts are removed from THAT ticker's calendar only
                  (DP-3C-ar), so they neither split nor extend an episode.

    Returns a list of episodes, oldest first. Each episode is a dict:
        id       "<TICKER>-<YYYYMMDD of opening row>"
        ticker   ticker
        opened   date of the opening row
        closed   date of the last row
        rows     the rows, oldest first
        open_row the opening row (the one DP-3C-y scores)
        bridged  dropout dates inside the episode (DP-3C-ar), oldest first
    Two rows on the same ticker and date (e.g. one per account) belong to the
    same episode; the first one seen is the opening row.
    """
    all_dates = sorted(set(cohort_dates))
    drop_by_tk = {}
    for tk, d in (dropouts or ()):
        drop_by_tk.setdefault(tk, set()).add(d)
    by_tk = {}
    for r in rows:
        by_tk.setdefault(ticker(r), []).append(r)
    out = []
    for tk, rs in by_tk.items():
        gone = drop_by_tk.get(tk, set())
        idx = {d: i for i, d in enumerate(d for d in all_dates if d not in gone)}
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
                           opened=date(r), closed=date(r), rows=[r], open_row=r,
                           bridged=[])
                out.append(cur)
            prev_i = i
        for e in out:
            if e["ticker"] == tk and gone:
                e["bridged"] = sorted(d for d in gone if e["opened"] < d < e["closed"])
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


def dp3cw_arm(rows, cohort_dates, dropouts=None):
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
    eps = [e for e in coalesce(pop, cohort_dates, dropouts=dropouts)
           if e["opened"] >= DP3CW_OPENED]
    opened = [e["open_row"] for e in eps]
    resolved = [r for r in opened if r.get("ret5") is not None]
    tickers_all = sorted({r["ticker"] for r in opened})
    tickers_res = sorted({r["ticker"] for r in resolved})
    out = dict(n_open=len(opened), n_resolved=len(resolved),
               tickers=tickers_all, tickers_resolved=tickers_res,
               episodes=[e["id"] for e in eps],
               bridged=[(e["ticker"], d) for e in eps for d in e.get("bridged", [])],
               # ADDED 2026-10-22 (DP-3C-bb): the opening-row dates the read
               # rests on, so the caller can apply rulings.read_protection().
               resolved_open_dates=[r["date"] for r in resolved],
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


def keep70(rows, cohort_dates, resolved_through=None, dropouts=None):
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
    eps = coalesce(pop, cohort_dates, dropouts=dropouts)
    ep_res = [res(e["open_row"]) for e in eps]
    ep_n = sum(1 for v in ep_res if v is not None)
    ep_hit = sum(1 for v in ep_res if v is not None and v > 0)
    rate = (100.0 * ep_hit / ep_n) if ep_n else None
    # DP-3C-au (RULED 2026-09-25): a state is never printed without its margin,
    # and a reading that ONE further resolution could flip is KNIFE-EDGE. The
    # DP-3C-y rule that a NOT SUPPORTED reading does not move the gate applies
    # symmetrically: a SUPPORTED reading does not certify it either.
    def _state(h, n):
        return "SUPPORTED" if 100.0 * h / n <= KEEP70_BAR else "NOT SUPPORTED"
    margin = (rate - KEEP70_BAR) if rate is not None else None
    if ep_n:
        after_hit, after_miss = _state(ep_hit + 1, ep_n + 1), _state(ep_hit, ep_n + 1)
        knife = after_hit != after_miss or after_hit != _state(ep_hit, ep_n)
    else:
        after_hit = after_miss = None
        knife = False
    return dict(
        rows=len(pop), row_n=row_n, row_hit=row_hit,
        row_rate=(100.0 * row_hit / row_n) if row_n else None,
        episodes=len(eps), ep_n=ep_n, ep_hit=ep_hit, ep_rate=rate,
        verdict=("NO RESOLVED EPISODES" if rate is None else
                 "SUPPORTED" if rate <= KEEP70_BAR else "NOT SUPPORTED"),
        margin_pt=margin, after_hit=after_hit, after_miss=after_miss,
        knife_edge=knife,
        bridged=[(e["ticker"], d) for e in eps for d in e.get("bridged", [])],
    )


# --------------------------------------------------------------------------- #
# PR-6 (F1-a): gate-cleared BUY episodes scored NET OF THE MARKET.
#
# RULED 2026-11-18 (DP-V9). Rob, 14:58 CT: "I'm comfortable ruling your
# recommendations." Source: claude/F1_CAPMAlpha_PreRegistration_2026-11-18.md.
# Every bar below was fixed BEFORE the first qualifying row existed: the arm
# opens on the first cohort after the ruling. None is revised after it.
#
#   POPULATION    BUY rows with conf >= 70, coalesced under DP-3C-m/ab/ar over
#                 the WHOLE post-era (from DP3CW_ERA_START) and scored on the
#                 OPENING row. Only episodes OPENING inside the segment enter;
#                 one already open at the segment start is discovery.
#   RETURN        r_h = p(D+h)/p(D) - 1 from the master's price columns
#                 (close basis), h = 5, 10, 20.
#   MARKET        SPY's own master row on D, the same columns.
#   AR            r - beta * r_SPY, with r_f = 0 (corpfin.jensen_alpha at
#                 r_rf = 0, the course's own function).
#   BETA          point in time: beta_adj (Blume, DP-V7) from
#                 cost_of_equity_<D>.json, else the newest such file dated
#                 before D and at most 7 days old. A name's entry is used only
#                 if its window's last close is BEFORE D. No beta -> the
#                 episode is excluded and counted. SPY is excluded too (its
#                 AR is 0 by construction).
#   HIT           AR5 > 0. AR5 == 0 counts as neither (a tie), and is counted.
#   READ SET      eligible episodes in opening order. The read set is the
#                 shortest RESOLVED PREFIX with n >= 40 (ties dropped) that
#                 spans >= 6 tickers. An unresolved episode stops the prefix,
#                 so no later episode is read around it. Read ONCE, recorded
#                 under DP-3C-bb.
#   POSITIVE      hits >= k, the smallest k with one-sided sign-test
#                 p <= 0.05 at that n (k = 26 at n = 40), AND a hit share
#                 >= 60% after removing every episode of the ticker with the
#                 most episodes. On a tie for most, the ticker whose removal
#                 lowers the share most is removed.
#   NEGATIVE      hit share <= 50%.
#   INCONCLUSIVE  anything else. Not extended.
#   BACKSTOP      S1: 2027-06-30. If the read set's last +5d session is not
#                 on or before it -> WITHDRAWN, NOT EXTENDED.
#   SEGMENTS      a Phase 4b go-live adds a segment here, dated the go-live
#                 session. The earlier segment ends the session before; each
#                 segment has its own n and a backstop 182 days on. Segments
#                 are never pooled. A segment closed by a go-live whose every
#                 eligible episode has resolved without a read set is WITHDRAWN.
#   BLIND         before the read the arm returns counts only. No hit, share,
#                 mean, sign or AR is in its output (DP-3C-ah).
#   F1-b          AR twins of PR-1, PR-3 and PR-5: defined in rulings DP-V9,
#                 built before PR-1's read, no disposition. Not here.
# --------------------------------------------------------------------------- #
PR6_GATE = 70.0
PR6_NEAR = (60.0, 70.0)            # near-miss stratum, printed at the read, no bar
PR6_MARKET = "SPY"
PR6_MIN_N = 40
PR6_MIN_TICKERS = 6
PR6_ALPHA = 0.05
PR6_LOTO_SHARE = 60.0
PR6_NEG_SHARE = 50.0
PR6_BETA_MAX_AGE_DAYS = 7
PR6_HORIZONS = (5, 10, 20)
# (label, first cohort, backstop or None = start + PR6_LATER_BACKSTOP_DAYS)
PR6_SEGMENTS = [("S1", dt.date(2026, 11, 19), dt.date(2027, 6, 30))]
PR6_LATER_BACKSTOP_DAYS = 182


def sign_p(n, k):
    """One-sided sign test: P(X >= k) for X ~ Binomial(n, 0.5)."""
    from math import comb
    return sum(comb(n, i) for i in range(k, n + 1)) / 2.0 ** n if n else 1.0


def sign_k(n, alpha=PR6_ALPHA):
    """The smallest k with sign_p(n, k) <= alpha."""
    for k in range(0, n + 2):
        if sign_p(n, k) <= alpha:
            return k
    return n + 1


def pit_betas(folder, max_age_days=PR6_BETA_MAX_AGE_DAYS):
    """betas_for(d, ticker) -> dict(beta, raw, file, short) or None.

    It reads cost_of_equity_<YYYY-MM-DD>.json in `folder`: the file for d
    first, then older ones no more than max_age_days old. A name's entry
    counts only if beta_adj is a number and its window's `last` close is
    strictly BEFORE d, so a beta never sees the session it scores."""
    import json
    pat = re.compile(r"^cost_of_equity_(\d{4}-\d{2}-\d{2})\.json$")
    files = {}
    try:
        names = os.listdir(folder)
    except OSError:
        names = []
    for n in names:
        m = pat.match(n)
        if m:
            try:
                files[dt.date.fromisoformat(m.group(1))] = os.path.join(folder, n)
            except ValueError:
                pass
    cache = {}

    def _names(fd):
        if fd not in cache:
            try:
                with open(files[fd], encoding="utf-8") as fh:
                    cache[fd] = json.load(fh).get("names") or {}
            except (OSError, ValueError, AttributeError):
                cache[fd] = {}
        return cache[fd]

    def betas_for(d, ticker):
        cands = sorted((f for f in files if f <= d and (d - f).days <= max_age_days), reverse=True)
        for fd in cands:
            e = _names(fd).get(ticker)
            if not isinstance(e, dict):
                continue
            b = e.get("beta_adj")
            try:
                last = dt.date.fromisoformat(str(e.get("last")))
            except ValueError:
                continue
            if isinstance(b, (int, float)) and last < d:
                return dict(beta=float(b), raw=e.get("beta_raw"), file=fd,
                            short=bool(e.get("short")))
        return None

    betas_for.files = sorted(files)
    return betas_for


def pr6_segments():
    """[(label, start, end_exclusive or None, backstop)], oldest first."""
    segs = sorted(PR6_SEGMENTS, key=lambda s: s[1])
    out = []
    for i, (lab, start, backstop) in enumerate(segs):
        end = segs[i + 1][1] if i + 1 < len(segs) else None
        out.append((lab, start, end,
                    backstop or start + dt.timedelta(days=PR6_LATER_BACKSTOP_DAYS)))
    return out


def market_returns(rows, market=PR6_MARKET):
    """{h: {date: r_market}} from the market's own master rows (first seen wins)."""
    out = {h: {} for h in PR6_HORIZONS}
    for r in rows:
        if r.get("ticker") == market:
            for h in PR6_HORIZONS:
                v = r.get("ret%d" % h)
                if v is not None:
                    out[h].setdefault(r["date"], v)
    return out


def _shift5(d):
    import trading_calendar as _tc
    return _tc.shift_sessions(d, 5)


def pr6_arm(rows, cohort_dates, betas_for, as_of, dropouts=None, segment="S1",
            shift5=None):
    """The PR-6 arm for one segment, counted blind.

    rows: dicts with date, ticker, signal, conf (PERCENT), ret5/ret10/ret20
          (fractions, or None while unresolved). Every master row may be
          passed; the population is selected here so there is one definition.
    betas_for: pit_betas(folder) or a stand-in with the same signature.
    as_of: the newest cohort date (for the backstop and segment closure).
    shift5: d -> its +5d session (trading_calendar by default).

    Returns counts only until a read set exists; then `read` carries the
    verdict and its secondaries. The CALLER decides whether to print or record
    it (DP-3C-bb: only once every resolving close predates the newest cohort)."""
    import corpfin as CF
    shift5 = shift5 or _shift5
    seg = {s[0]: s for s in pr6_segments()}[segment]
    _, start, end, backstop = seg
    mkt = market_returns(rows)

    def in_seg(d):
        return d >= start and (end is None or d < end)

    def episodes_in(lo, hi):
        pop = [r for r in rows
               if r["date"] >= DP3CW_ERA_START and r.get("signal") == "BUY"
               and isinstance(r.get("conf"), (int, float)) and lo <= r["conf"] < hi]
        return [e for e in coalesce(pop, cohort_dates, dropouts=dropouts) if in_seg(e["opened"])]

    def score(e):
        r, t = e["open_row"], e["ticker"]
        if t == PR6_MARKET:
            return dict(ep=e, status="market")
        b = betas_for(r["date"], t)
        if b is None:
            return dict(ep=e, status="no_beta")
        s = dict(ep=e, status="eligible", beta=b["beta"], raw=b.get("raw"),
                 short=b.get("short", False), beta_file=b.get("file"))
        for h in PR6_HORIZONS:
            ri, rm = r.get("ret%d" % h), mkt[h].get(r["date"])
            s["r%d" % h], s["rm%d" % h] = ri, rm
            s["ar%d" % h] = (CF.jensen_alpha(ri, 0.0, rm, b["beta"])
                             if ri is not None and rm is not None else None)
        return s

    sc = [score(e) for e in episodes_in(PR6_GATE, float("inf"))]
    elig = [s for s in sc if s["status"] == "eligible"]
    prefix = []
    for s in elig:                         # coalesce() returns opening order
        if s["ar5"] is None:
            break
        prefix.append(s)
    nontie = [s for s in prefix if s["ar5"] != 0]
    read_set, seen = None, set()
    for i, s in enumerate(nontie, 1):
        seen.add(s["ep"]["ticker"])
        if i >= PR6_MIN_N and len(seen) >= PR6_MIN_TICKERS:
            read_set = nontie[:i]
            break
    out = dict(segment=segment, start=start, end=end, backstop=backstop,
               n_open=len(sc), n_market=sum(1 for s in sc if s["status"] == "market"),
               n_no_beta=sum(1 for s in sc if s["status"] == "no_beta"),
               n_eligible=len(elig), n_prefix=len(prefix),
               n_resolved_any=sum(1 for s in elig if s["ar5"] is not None),
               tickers_prefix=sorted({s["ep"]["ticker"] for s in prefix}),
               episodes=[s["ep"]["id"] for s in elig],
               resolved_open_dates=[], read=None, state="COLLECTING",
               verdict="COLLECTING - counts only; nothing is read before n = %d on %d tickers"
                       % (PR6_MIN_N, PR6_MIN_TICKERS))
    closed = end is not None and as_of is not None and as_of >= end
    if read_set is not None and shift5(read_set[-1]["ep"]["opened"]) > backstop:
        read_set = None                        # it resolved too late to count
    if read_set is None:
        if (as_of is not None and as_of > backstop) or \
                (closed and len(prefix) == len(elig)):
            out["state"] = "WITHDRAWN"
            out["verdict"] = ("WITHDRAWN, NOT EXTENDED - no read set of n >= %d on >= %d tickers %s"
                              % (PR6_MIN_N, PR6_MIN_TICKERS,
                                 "by the backstop %s" % backstop if not closed
                                 else "before the segment closed on %s" % end))
        return out
    out["state"] = "READY"
    out["resolved_open_dates"] = [s["ep"]["opened"] for s in read_set]
    out["read"] = pr6_read(read_set, sc, elig, rows, betas_for, mkt, start,
                           episodes_in, score)
    out["verdict"] = out["read"]["verdict"]
    return out


def _share(xs):
    return 100.0 * sum(1 for x in xs if x > 0) / len(xs) if xs else None


def _verdict(hits, n, loto):
    k = sign_k(n)
    if hits >= k and loto is not None and loto >= PR6_LOTO_SHARE:
        return "POSITIVE - gate-cleared BUYs beat their beta-implied return at +5d"
    if 100.0 * hits / n <= PR6_NEG_SHARE:
        return "NEGATIVE - no better than a coin net of the market"
    if hits >= k:
        return ("INCONCLUSIVE - the sign test clears but not without its most frequent "
                "ticker (%.1f%% < %.0f%%); not extended" % (loto or 0.0, PR6_LOTO_SHARE))
    return "INCONCLUSIVE - between the bars; not extended"


def _loto(read_set):
    from collections import Counter
    cnt = Counter(s["ep"]["ticker"] for s in read_set)
    top = max(cnt.values())
    best = None
    for t in sorted(x for x, c in cnt.items() if c == top):
        rest = [s["ar5"] for s in read_set if s["ep"]["ticker"] != t]
        sh = _share(rest) if rest else 0.0
        if best is None or sh < best[1]:
            best = (t, sh, top)
    return best


def _f1c(pairs):
    """1 - var(AR)/var(r) and R^2 of r on beta*r_M, over (r, beta*r_M) pairs."""
    n = len(pairs)
    if n < 3:
        return None
    rs = [p[0] for p in pairs]
    ms = [p[1] for p in pairs]
    ar = [a - b for a, b in pairs]

    def var(v):
        m = sum(v) / len(v)
        return sum((x - m) ** 2 for x in v) / (len(v) - 1)

    vr, vm = var(rs), var(ms)
    if vr == 0:
        return None
    mr, mm = sum(rs) / n, sum(ms) / n
    cov = sum((a - mr) * (b - mm) for a, b in zip(rs, ms)) / (n - 1)
    return dict(n=n, removed=1.0 - var(ar) / vr,
                r2=(cov * cov / (vr * vm)) if vm else None)


def pr6_read(read_set, sc, elig, rows, betas_for, mkt, start, episodes_in, score):
    """The one-time read: the verdict, then secondaries that carry no bar."""
    n = len(read_set)
    ar5 = [s["ar5"] for s in read_set]
    hits = sum(1 for x in ar5 if x > 0)
    lt = _loto(read_set)
    verdict = _verdict(hits, n, lt[1])
    # knife-edge: would one episode's sign, either way, change the state?
    state = verdict.split(" ")[0]
    flips = {_verdict(hits + 1, n, lt[1]).split(" ")[0],
             _verdict(max(hits - 1, 0), n, lt[1]).split(" ")[0]}
    srt = sorted(ar5)
    med = (srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0)
    last_open = read_set[-1]["ep"]["opened"]
    sec = {}
    for h in (10, 20):
        v = [s["ar%d" % h] for s in read_set if s["ar%d" % h] is not None]
        sec["ar%d_share" % h], sec["ar%d_n" % h] = _share(v), len(v)
    near = [score(e) for e in episodes_in(*PR6_NEAR) if e["opened"] <= last_open]
    near_v = [s["ar5"] for s in near if s["status"] == "eligible"
              and s["ar5"] is not None and s["ar5"] != 0]
    f1c = {}
    for h in PR6_HORIZONS:
        allrows = []
        for r in rows:
            if not (start <= r["date"] <= last_open) or r.get("ticker") == PR6_MARKET:
                continue
            rm, ri = mkt[h].get(r["date"]), r.get("ret%d" % h)
            if rm is None or ri is None:
                continue
            b = betas_for(r["date"], r["ticker"])
            if b is not None:
                allrows.append((ri, b["beta"] * rm))
        f1c["h%d" % h] = dict(
            episodes=_f1c([(s["r%d" % h], s["r%d" % h] - s["ar%d" % h]) for s in read_set
                           if s["ar%d" % h] is not None]),
            all_rows=_f1c(allrows))
    return dict(
        verdict=verdict, n=n, hits=hits, k=sign_k(n), p=sign_p(n, hits),
        share=100.0 * hits / n, loto_ticker=lt[0], loto_count=lt[2], loto_share=lt[1],
        knife_edge=any(f != state for f in flips),
        mean_ar5=sum(ar5) / n, median_ar5=med,
        raw_share=_share([s["r5"] for s in read_set]),
        tickers=sorted({s["ep"]["ticker"] for s in read_set}),
        episodes=[s["ep"]["id"] for s in read_set],
        ties=sum(1 for s in elig if s["ar5"] == 0 and s["ep"]["opened"] <= last_open),
        short_betas=sum(1 for s in read_set if s.get("short")),
        excluded_no_beta=sum(1 for s in sc if s["status"] == "no_beta"
                             and s["ep"]["opened"] <= last_open),
        excluded_market=sum(1 for s in sc if s["status"] == "market"
                            and s["ep"]["opened"] <= last_open),
        near_n=len(near_v), near_share=_share(near_v),
        f1c=f1c,
        **sec)


def _pr6_selftest(chk):
    """PR-6 checks (DP-V9). Synthetic rows only; no master, no file but a temp dir."""
    import corpfin as CF
    import json
    import tempfile
    global PR6_SEGMENTS
    D = dt.date
    cal, d = [], D(2026, 11, 19)
    while len(cal) < 260:
        if d.weekday() < 5:
            cal.append(d)
        d += dt.timedelta(days=1)
    pos = {x: i for i, x in enumerate(cal)}

    def sh5(x):
        return cal[pos[x] + 5]

    def bet(x, t):
        return None if t == "NOBETA" else dict(beta=1.2, raw=1.3, file=x, short=(t == "T7"))

    def mk(n, hits, tk=lambda j: "T%d" % (j % 8), gap=None, tie=None, extra=()):
        rows = [dict(date=x, ticker="SPY", signal="HOLD", conf=50.0,
                     ret5=0.01, ret10=0.01, ret20=0.01) for x in cal]
        for j in range(n):
            if j == tie:
                r5 = 0.0 + 0.01 * 1.2                    # AR exactly 0
            else:
                r5 = 0.01 * 1.2 + (0.005 if j in hits else -0.005)
            rows.append(dict(date=cal[2 * j], ticker=tk(j), signal="BUY", conf=72.0,
                             ret5=None if j == gap else r5, ret10=r5, ret20=None))
        rows.extend(extra)
        return rows

    def arm(rows, as_of=None, seg="S1"):
        return pr6_arm(rows, cal, bet, as_of or cal[120], segment=seg, shift5=sh5)

    chk("PR-6 sign test: k = 26 at n = 40 (p 0.040), 20 at 30, 32 at 50",
        sign_k(40) == 26 and sign_k(30) == 20 and sign_k(50) == 32
        and abs(sign_p(40, 26) - 0.0403) < 5e-4 and sign_p(40, 25) > 0.05)
    chk("PR-6 AR is the course's Jensen alpha at r_f = 0 (CC -1.5% at r_f 4% too)",
        abs(CF.jensen_alpha(0.02, 0.0, 0.01, 1.2) - 0.008) < 1e-12
        and abs(CF.jensen_alpha(.095, .04, .05, 1.4) + 0.015) < 1e-12)
    a = arm(mk(39, set(range(39))))
    chk("PR-6 BLIND at 39: COLLECTING, no read, and no hit, share or AR anywhere in the output",
        a["state"] == "COLLECTING" and a["read"] is None and a["n_prefix"] == 39
        and not any(k in json.dumps(a, default=str) for k in ("hits", "share", "ar5", "mean")))
    a = arm(mk(40, set(range(26))))
    chk("PR-6 26/40 spread over 8 tickers -> POSITIVE (k 26; 62.9% without the top ticker)",
        a["read"] is not None and a["verdict"].startswith("POSITIVE") and a["read"]["k"] == 26
        and abs(a["read"]["loto_share"] - 100.0 * 22 / 35) < 1e-9)
    chk("PR-6 26/40 is KNIFE-EDGE (one miss more is INCONCLUSIVE)", a["read"]["knife_edge"])
    chk("PR-6 the read carries mean/median AR5, the raw share and both F1-c reads",
        abs(a["read"]["mean_ar5"] - (26 * 0.005 - 14 * 0.005) / 40) < 1e-12
        and a["read"]["raw_share"] == 100.0 and a["read"]["f1c"]["h5"]["episodes"] is not None
        and a["read"]["short_betas"] == 5)
    a = arm(mk(40, set(range(30))))
    chk("PR-6 30/40 POSITIVE and not knife-edge",
        a["verdict"].startswith("POSITIVE") and not a["read"]["knife_edge"])
    chk("PR-6 25/40 -> INCONCLUSIVE, not extended",
        arm(mk(40, set(range(25))))["verdict"].startswith("INCONCLUSIVE - between"))
    chk("PR-6 20/40 = 50% -> NEGATIVE", arm(mk(40, set(range(20))))["verdict"].startswith("NEGATIVE"))
    conc = lambda j: "T0" if j % 8 < 3 else "T%d" % (1 + j % 8)
    hits = {j for j in range(40) if j % 8 < 3} | {j for j in range(40) if j % 8 >= 3 and j < 20}
    a = arm(mk(40, hits, tk=conc))
    chk("PR-6 NEGATIVE probe: a sign-test pass carried by one ticker stays INCONCLUSIVE",
        a["read"]["hits"] >= 26 and a["read"]["loto_ticker"] == "T0"
        and a["read"]["loto_share"] < 60 and a["verdict"].startswith("INCONCLUSIVE - the sign test"))
    few = lambda j: "T%d" % (j % 5) if j < 42 else "T9"
    a = arm(mk(45, set(range(45)), tk=few))
    chk("PR-6 5 tickers at n = 40 waits for the 6th: read at n = 43 with k for n = 43",
        a["read"]["n"] == 43 and a["read"]["k"] == sign_k(43) and len(a["read"]["tickers"]) == 6)
    a = arm(mk(45, set(range(45)), gap=9))
    chk("PR-6 an unresolved episode stops the prefix (nothing read around it)",
        a["read"] is None and a["n_prefix"] == 9 and a["n_resolved_any"] == 44)
    a = arm(mk(41, set(range(41)), tie=3))
    chk("PR-6 a tie (AR5 exactly 0) is neither: 41 resolved with one tie reads n = 40",
        a["read"]["n"] == 40 and a["read"]["ties"] == 1)
    ext = [dict(date=cal[1], ticker="T1", signal="BUY", conf=69.0, ret5=0.5),
           dict(date=cal[3], ticker="T2", signal="SELL", conf=80.0, ret5=0.5),
           dict(date=cal[5], ticker="SPY", signal="BUY", conf=75.0, ret5=0.01),
           dict(date=cal[7], ticker="NOBETA", signal="BUY", conf=75.0, ret5=0.5),
           dict(date=D(2026, 11, 18), ticker="OLD", signal="BUY", conf=75.0, ret5=0.5),
           dict(date=cal[0], ticker="OLD", signal="BUY", conf=75.0, ret5=0.5)]
    a = pr6_arm(mk(3, set(), extra=ext), [D(2026, 11, 18)] + cal, bet, cal[120], shift5=sh5)
    chk("PR-6 population: conf 69 and SELL are out; an episode open at the start is discovery",
        a["n_open"] == 5 and "OLD-20261118" not in a["episodes"])
    chk("PR-6 SPY and a name with no PIT beta are excluded and COUNTED",
        a["n_market"] == 1 and a["n_no_beta"] == 1 and a["n_eligible"] == 3)
    chk("PR-6 backstop: unread after 2027-06-30 -> WITHDRAWN, NOT EXTENDED",
        arm(mk(10, set()), as_of=D(2027, 7, 1))["state"] == "WITHDRAWN")
    keep = PR6_SEGMENTS
    try:
        PR6_SEGMENTS = [("S1", cal[0], D(2027, 6, 30)), ("S2", cal[30], None)]
        s1 = arm(mk(30, set()), as_of=cal[40], seg="S1")
        s2 = arm(mk(30, set()), as_of=cal[40], seg="S2")
        chk("PR-6 a go-live closes S1 (15 episodes, all resolved) -> WITHDRAWN; S2 starts its own n",
            s1["state"] == "WITHDRAWN" and s1["n_open"] == 15 and s2["n_open"] == 15
            and s2["state"] == "COLLECTING" and s2["backstop"] == cal[30] + dt.timedelta(days=182))
        PR6_SEGMENTS = [("S1", cal[0], cal[70])]
        late = arm(mk(40, set(range(40))), as_of=cal[100])
        chk("PR-6 a read set resolving after the backstop does not count -> WITHDRAWN",
            late["read"] is None and late["state"] == "WITHDRAWN")
    finally:
        PR6_SEGMENTS = keep
    with tempfile.TemporaryDirectory() as td:
        def put(day, names):
            with open(os.path.join(td, "cost_of_equity_%s.json" % day), "w", encoding="utf-8") as fh:
                json.dump({"names": names}, fh)
        put("2026-11-20", {"A": {"beta_adj": 1.5, "last": "2026-11-20"},
                           "C": {"beta_adj": "x", "last": "2026-11-19"}})
        put("2026-11-19", {"A": {"beta_adj": 1.1, "beta_raw": 1.15, "last": "2026-11-18"},
                           "B": {"beta_adj": 0.9, "last": "2026-11-18"}})
        put("2026-11-12", {"Z": {"beta_adj": 0.7, "last": "2026-11-11"}})
        bf = pit_betas(td)
        a20 = bf(D(2026, 11, 20), "A")
        chk("PR-6 PIT beta: a window ending ON the session is refused; the older file is used",
            a20 is not None and a20["beta"] == 1.1 and a20["file"] == D(2026, 11, 19))
        chk("PR-6 PIT beta: a non-number beta is skipped; an unknown name is None",
            bf(D(2026, 11, 20), "C") is None and bf(D(2026, 11, 20), "Q") is None)
        chk("PR-6 PIT beta: 7 days old is used, 8 days old is not",
            bf(D(2026, 11, 19), "Z") is not None and bf(D(2026, 11, 20), "Z") is None)
        chk("PR-6 PIT beta: a file dated after the session is never read",
            bf(D(2026, 11, 18), "A") is None)


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
    # DP-3C-ar (2026-09-25): a run-fault dropout bridges for THAT ticker only.
    cal3 = [D(2026, 9, 21), D(2026, 9, 22), D(2026, 9, 23), D(2026, 9, 24)]
    r3 = [dict(ticker="MSFT", date=D(2026, 9, 21)), dict(ticker="MSFT", date=D(2026, 9, 22)),
          dict(ticker="MSFT", date=D(2026, 9, 24)),
          dict(ticker="NVDA", date=D(2026, 9, 22)), dict(ticker="NVDA", date=D(2026, 9, 24))]
    e_old = coalesce(r3, cal3)
    e_new = coalesce(r3, cal3, dropouts={("MSFT", D(2026, 9, 23))})
    ms_new = [e for e in e_new if e["ticker"] == "MSFT"]
    chk("without DP-3C-ar the dropout splits MSFT (status quo preserved when not passed)",
        len([e for e in e_old if e["ticker"] == "MSFT"]) == 2)
    chk("with DP-3C-ar MSFT is ONE episode 09-21 -> 09-24",
        len(ms_new) == 1 and ms_new[0]["closed"] == D(2026, 9, 24))
    chk("the bridged date is recorded on the episode",
        ms_new[0]["bridged"] == [D(2026, 9, 23)])
    chk("a dropout on one ticker never bridges another (NVDA still splits)",
        len([e for e in e_new if e["ticker"] == "NVDA"]) == 2)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "signals_2026-09-23.log")
        with open(lp, "w", encoding="utf-8") as fh:
            fh.write("2026-09-23 09:34:54,659 | WARNING | No quote data for MSFT \u2014 skipping.\n"
                     "2026-09-23 09:35:00,000 | WARNING | No quote data for AAPL \u2014 skipping.\n"
                     '2026-09-23 09:36:00,000 | INFO | Signal JSON: {"ticker": "AAPL", "signal": "HOLD"}\n')
        got = dropouts_from_logs([lp])
        chk("log parser: MSFT skipped and unwritten -> dropout", ("MSFT", D(2026, 9, 23)) in got)
        chk("log parser: a skip followed by a written row is NOT a dropout",
            ("AAPL", D(2026, 9, 23)) not in got)
        chk("master presence vetoes a dropout",
            dropouts_from_logs([lp], present={("MSFT", D(2026, 9, 23))}) == set())
    # DP-3C-au (2026-09-25): margin and knife-edge.
    k = keep70([dict(ticker="A%d" % i, date=D(2026, 9, 1) + dt.timedelta(days=2 * i),
                     signal="BUY", conf=65, ret5=(0.01 if i < 2 else -0.01)) for i in range(4)],
               [D(2026, 9, 1) + dt.timedelta(days=i) for i in range(10)])
    chk("KEEP-70 2/4 = 50.00% sits ON the bar: SUPPORTED, margin 0, knife-edge",
        k["verdict"] == "SUPPORTED" and abs(k["margin_pt"]) < 1e-9 and k["knife_edge"])
    k = keep70([dict(ticker="B%d" % i, date=D(2026, 9, 1) + dt.timedelta(days=2 * i),
                     signal="BUY", conf=65, ret5=(0.01 if i < 1 else -0.01)) for i in range(5)],
               [D(2026, 9, 1) + dt.timedelta(days=i) for i in range(12)])
    chk("NEGATIVE: 1/5 = 20% is SUPPORTED with room -> NOT knife-edge",
        k["verdict"] == "SUPPORTED" and not k["knife_edge"] and k["margin_pt"] < -29)
    # PR-6 (DP-V9, 2026-11-18): the CAPM-alpha arm. Synthetic rows only.
    _pr6_selftest(chk)
    print("  RESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
