#!/usr/bin/env python3
# =============================================================================
# monitor_strip.py  —  the OPEN QUESTIONS dashboard (daily glance)
# =============================================================================
# WHY THIS EXISTS
#   guardrail_trace.py answers "does 50-59 lead 60-69?" — a question CLOSED by
#   the Q1-R diagnostic (guardrail retired, T2 retired). This strip tracks the
#   questions that are still OPEN, in fixed width regardless of how much
#   history accumulates:
#
#     WS1 / G2   blend vs base        gate-flip net + confirm/discount arms
#     WS2 / G1   H1 acceptance clock  episodes detected + response verdict
#     H4         DQ-conditional gate  HIGH-DQ near-miss n & hit% vs the bars
#     KEEP-70    the 70% BUY gate     near-miss BUY EPISODES (DP-3C-y basis)
#     DP-3C-w    prospective arm      episode count, blind until n = 10
#     context    registry size, live band split
#
# EPISODE DETECTION (WS2) — the one encoded judgement, and it is NOT a new
#   number: "material adverse move" reuses D1's pre-registered
#   DampingConfig.THETA (5.0%), imported from risk_engine so there is exactly
#   ONE definition of "material" in the system. An episode = a tracer session
#   whose trailing 5-day move is <= -THETA. It is SERVED if the operative
#   confidence falls within RESPONSE_SESSIONS (2) sessions of that move; the
#   acceptance criterion (WS2_H1_Feature_Spec / G1) is the table read, and this
#   counter makes "how many test cases have we actually had" reproducible
#   rather than a recollection.
#
# DATA SOURCES
#   tracker Signals tab  — bands, near-miss/H4, KEEP-70, tracer confidences
#   logs/signals_*.log   — confidence_blend (the blend channel lives only in
#                          the logs; there is no tracker column by design)
#   Returns are computed from the Price columns, so an unrecalculated formula
#   cache cannot affect this tool.
#
# EMBED MODE (--embed-into)
#   Mirrors guardrail_trace.py: reads the MASTER tracker for the data, then
#   writes a refreshed "Monitor Strip" sheet — as-of line + auditable table +
#   the strip image — into a GENERATED COPY (tracker_with_registry.xlsx). The
#   master is never modified. Idempotent: the sheet is replaced, never stacked,
#   and it is re-parked immediately after "Guardrail Trace" on every run.
#
#   NO-SQUISH RULE: the image is resampled to the exact embed width with PIL
#   (LANCZOS) and then anchored with a plain cell string, which openpyxl writes
#   as a oneCellAnchor at the image's own pixel size. Excel therefore performs
#   ZERO scaling. Do NOT hand openpyxl an oversized PNG and shrink it via
#   img.width/img.height — that is what crushed guardrail_trace's chart to
#   46.6% (1632px native displayed at a fixed 760px cap) and it gets worse
#   every cohort. Render big, resample once, embed at native size.
#
# USAGE
#   python monitor_strip.py --tracker "logs\\claude_equity_bot_tracker.xlsx"
#   python monitor_strip.py --tracker ... --logs "logs\\signals_*.log" --no-png
#   python monitor_strip.py --tracker "%TRACKER%" --embed-into tracker_with_registry.xlsx
# =============================================================================

from __future__ import annotations
import argparse
import datetime as dt
import glob
import json
import os
import re
from collections import defaultdict

import openpyxl

SIGNALS_SHEET = "Signals"
FIRST_DATA_ROW = 5
COL = dict(date=1, ticker=2, account=3, signal=4, conf=5, dq=6, p0=7, p5=8)

LIVE_START = dt.date(2026, 6, 15)     # Phase 3-A go-live (population boundary)
WS2_DEPLOY = dt.date(2026, 7, 7)      # S1+D1 go-live (era A-S1D1) — G1 clock start
WS1_DEPLOY = dt.date(2026, 7, 13)     # blend go-live (era A-S1D1-B1)
TRACERS = ("WMT", "GM")               # WS2 primary / secondary
RESPONSE_SESSIONS = 2                 # G1: confidence must respond within 2
# DP-3C-aa (2026-09-03), applied here 2026-09-16. The H1 window fix changed the
# trailing move THETA damps on. Only responses measured on the corrected
# channel (episodes from D2_START) are evidence for G1, plus the one pre-fix
# response that survives recomputation. WMT 2026-08-20's response was produced
# by THETA firing on the defective window and is VACATED. The bar is unchanged.
D2_START = dt.date(2026, 9, 1)
G1_VACATED = {("WMT", dt.date(2026, 8, 20))}
G1_SURVIVES = {("WMT", dt.date(2026, 7, 23))}
HOLD_BAND = 0.03                      # +/-3% -> a HOLD was "right"
BUY_GATE = 70                         # KEEP-70
SELL_GATE = 65                        # CHECK 5 SELL gate (risk_engine); DP-3C-as
# DP-3C-an (RULED 2026-09-25). G1 is read ONCE at a pooled n of evidence
# episodes across the WS2 tracer universe (WMT + GM) -- n = 4 is the
# pre-registered read point [R: 2026-08-20 review, "the pre-registered n = 4"].
# The tool counts toward it and says when it is reached; the read itself is
# taken in a dated review, never emitted here.
G1_READ_N = 4
# H4 reopen bar. Raised 10 -> 12 on 2026-07-28 after the 7/27 REOPEN lasted
# exactly one session: n crossed 10 while the rate FELL to 60.0000%, and the
# 11th resolution flipped it straight back. The ruling attached a second
# condition this tool CANNOT evaluate — the pass must hold on TWO CONSECUTIVE
# readings — because a single run has no history. The bar text therefore states
# the full rule and the state field reports only the single-reading result,
# rather than asserting a two-reading verdict the tool did not compute.
H4_MIN_N = 12                         # H4 reopen: resolved HIGH-DQ near-misses
H4_MIN_HIT = 60.0                     # H4 reopen: hit rate bar
H4_CONSECUTIVE = 2                    # readings required; NOT evaluated here

# ---- embed mode ----
SHEET_NAME = "Monitor Strip"          # the sheet written into the report copy
DEFAULT_THEME = "dark"                # the strip is a dashboard tile, not a table
EMBED_WIDTH_PX = 1100                 # on-screen width; PNG is resampled to it
PX_PER_ROW = 20                       # default Excel row height (15pt) in px

# Park the strip after the first of these that exists (keeps "How to Use" last).
EMBED_AFTER = ("Cohort Analysis", "Near-Miss BUYs", "Signals")

# RETIRED 2026-07-27 — Q1-R closed the guardrail question; guardrail_trace.py
# is out of the runner. Both sheets below were written by it, and neither has
# a tool refreshing it any more. They are dropped from the GENERATED COPY on
# every run so a stale-but-authoritative-looking tab cannot survive in the
# workbook. This never touches the master (see the guard in main()). If the
# master still carries these tabs, delete them there once — otherwise
# --emit-master-copy will keep resurrecting them into the copy.
RETIRED_SHEETS = ("Guardrail Trace", "Live Cohort Scoreboard")

# Name matching is not enough — see _retired_sheets_in(). These are matched
# against the first three cells of column A, lowercased.
RETIRED_SIGNATURES = (
    "guardrail compression trace",
    "guardrail_trace.py",
    "live cohort scoreboard",
    "must lead 60-69",
    "out-of-sample guardrail",
)

try:                                   # one definition of "material adverse"
    from risk_engine import DampingConfig
    THETA = float(DampingConfig.THETA)
    THETA_SRC = "risk_engine.DampingConfig.THETA"
    THETA_OK = True                    # provenance-clean: one definition
except Exception:                      # standalone fallback, kept in sync
    THETA = 5.0
    THETA_SRC = "local default (risk_engine unavailable)"
    THETA_OK = False                   # NB: test THETA_OK, not THETA_SRC —
                                       # the fallback string CONTAINS the word
                                       # "risk_engine", so a substring check
                                       # silently passes. It did, once.


# ----------------------------------------------------------------- loading --
def _date(v):
    return v.date() if isinstance(v, dt.datetime) else (v if isinstance(v, dt.date) else None)


def _num(v):
    return v if isinstance(v, (int, float)) else None


def load_rows(tracker):
    wb = openpyxl.load_workbook(tracker, data_only=True)
    ws = wb[SIGNALS_SHEET]
    rows, blank = [], 0
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        d = _date(ws.cell(r, COL["date"]).value)
        tk = ws.cell(r, COL["ticker"]).value
        if d is None and not tk:
            blank += 1
            if blank >= 30:
                break
            continue
        blank = 0
        if d is None or not tk:
            continue
        conf = ws.cell(r, COL["conf"]).value
        if isinstance(conf, (int, float)) and conf <= 1:
            conf *= 100
        p0, p5 = _num(ws.cell(r, COL["p0"]).value), _num(ws.cell(r, COL["p5"]).value)
        rows.append(dict(
            date=d, ticker=str(tk).strip().upper(),
            signal=str(ws.cell(r, COL["signal"]).value or "").strip().upper(),
            conf=conf, dq=str(ws.cell(r, COL["dq"]).value or "").strip().upper(),
            p0=p0, ret5=((p5 - p0) / p0 if (p0 and p5) else None),
        ))
    wb.close()
    rows.sort(key=lambda x: (x["date"], x["ticker"]))
    return rows


def load_blend(pattern):
    """{(date,ticker): {base, blend}} from the logs (blend lives only there).

    ANALYST NOTE (2026-09-08): this used to call glob.glob(pattern) directly,
    which is NON-RECURSIVE. When the logs were tidied into month subfolders
    ("05 May signals", "06 June signals", "07 July Signals", "08 August
    Signals"), the loose set in logs/ fell to five files — 2026-09-01 onward —
    and this function silently stopped seeing four months of history. The WS1
    gate-flip ledger went from "4 resolved gate-flips, net +2" (2026-08-27
    review) to "1 flip, net -1" with nothing reporting the change. A resolved
    flip cannot un-resolve; the ledger had simply been narrowed to the current
    month and was still being printed as though it were the whole record.

    The blend channel exists ONLY in the logs — there is no tracker column, by
    design — so for WS1 the log set IS the ledger. signal_logs.discover walks
    the archive subfolders; the caller reports the span it actually read.

    Note the comment on the skipped branch below also read "archived/renamed
    logs", i.e. the archive case was anticipated here and handled by SKIPPING
    it. That is now the one thing this function must not do.
    """
    out = {}
    try:
        import signal_logs
        paths, _info = signal_logs.discover(pattern)
    except Exception:
        paths = sorted(glob.glob(pattern))
    for fp in paths:
        m = re.search(r"signals_(\d{4}-\d{2}-\d{2})", os.path.basename(fp))
        if not m:
            continue                                  # undated / renamed logs
        d = dt.date.fromisoformat(m.group(1))
        for line in open(fp, encoding="utf-8", errors="replace"):
            if "Signal JSON" not in line:
                continue
            j = line.split("Signal JSON:", 1)[1]
            j = j[:j.rfind("} |") + 1] if "} |" in j else j
            try:
                p = json.loads(j)
            except Exception:
                continue
            if "confidence_blend" not in p:
                continue
            key = (d, str(p.get("ticker", "")).upper())
            out.setdefault(key, dict(base=p.get("confidence"),
                                     blend=p.get("confidence_blend"),
                                     signal=str(p.get("signal", "")).upper()))
    return out


def load_raw(pattern):
    """{(date, ticker): confidence_raw} from the Signal JSON log lines.

    ADDED 2026-09-25 for DP-3C-an: G1 is scored on the RAW (model-side,
    pre-damping) channel. The tracker stores only the OPERATIVE value, so the
    raw channel exists only in the logs -- the same reason load_blend exists.
    A row with no confidence_raw (logs before S1, or a missing log) falls back
    to the tracker's operative value, which equals raw wherever damping was
    inactive; the caller reports how many rows were overridden."""
    out = {}
    try:
        import signal_logs
        paths, _info = signal_logs.discover(pattern)
    except Exception:
        paths = sorted(glob.glob(pattern))
    rx = re.compile(r'"ticker":\s*"(?P<tk>[A-Z.\-]+)".*?"confidence_raw":\s*(?P<raw>\d+)')
    for fp in paths:
        m = re.search(r"signals_(\d{4}-\d{2}-\d{2})", os.path.basename(fp))
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        for line in open(fp, encoding="utf-8", errors="replace"):
            if "Signal JSON" not in line:
                continue
            mm = rx.search(line)
            if mm:
                out.setdefault((d, mm.group("tk")), int(mm.group("raw")))
    return out


def run_basis_crossread(pattern):
    """DP-3C-an's mandatory cross-read (ADDED 2026-09-25). G1 is scored on the
    TRACKER basis; the run's own series -- `D[trail=…]`, closes over prior
    sessions, the series THETA damps on -- is read beside it on every run so
    the ruled basis can never be the only one visible. D2 logs only (from
    D2_START): D1 logs are history under DP-3C-aj. Response on the RAW
    channel, same baseline rule (raw five run-sessions earlier). Reported,
    never scored."""
    rx = re.compile(r'Signal JSON: \{"ticker": "(?P<tk>[A-Z.\-]+)".*?'
                    r'D\[raw=(?P<raw>\d+); op=\d+; trail=(?P<tr>[+-]?[\d.]+)%')
    ser = {tk: {} for tk in TRACERS}
    try:
        import signal_logs
        paths, _info = signal_logs.discover(pattern)
    except Exception:
        paths = sorted(glob.glob(pattern))
    for fp in paths:
        m = re.search(r"signals_(\d{4}-\d{2}-\d{2})\.log$", os.path.basename(fp))
        if not m:
            continue                       # only canonical per-date logs
        d = dt.date.fromisoformat(m.group(1))
        for line in open(fp, encoding="utf-8", errors="replace"):
            mm = rx.search(line)
            if mm and mm.group("tk") in ser:
                ser[mm.group("tk")].setdefault(d, (int(mm.group("raw")), float(mm.group("tr"))))
    out = {}
    for tk, sd in ser.items():
        ds = sorted(sd)
        eps, in_run = [], False
        for i, d in enumerate(ds):
            raw, tr = sd[d]
            if tr > -THETA:
                in_run = False
                continue
            if in_run:
                continue
            in_run = True
            if d < D2_START or i < 5:
                continue
            pre = sd[ds[i - 5]][0]
            lag = next((k for k in range(RESPONSE_SESSIONS + 1)
                        if i + k < len(ds) and sd[ds[i + k]][0] < pre), None)
            pending = lag is None and i + RESPONSE_SESSIONS >= len(ds)
            eps.append((d, tr, lag, pending))
        out[tk] = eps
    return out


# ----------------------------------------------------------------- metrics --
def right5(sig, ret):
    if ret is None:
        return None
    return abs(ret) < HOLD_BAND if sig == "HOLD" else (ret > 0 if sig == "BUY" else ret < 0)


def _acc(sub):
    sub = [x for x in sub if x["ret5"] is not None]
    h = sum(1 for x in sub if right5(x["signal"], x["ret5"]))
    return len(sub), (100.0 * h / len(sub) if sub else 0.0)


def ws2_episodes(rows, raw=None):
    """WS2/G1 — count post-deploy tracer episodes and whether each was SERVED.

    episode  : trailing 5-session move <= -THETA on a tracer (TRACKER basis:
               five tracker rows off Price at Signal -- DP-3C-an keeps it)
    served   : confidence FALLS within RESPONSE_SESSIONS sessions

    DP-3C-an (RULED 2026-09-25): when `raw` is passed, the response is scored
    on the RAW channel (log `confidence_raw`, the model's own number) and the
    OPERATIVE lag is kept beside it in e["op_lag"] so a channel-sensitive
    episode is visible. Without `raw` the old operative scoring is unchanged.
    """
    out = {}
    for tk in TRACERS:
        ser = [dict(x) for x in rows if x["ticker"] == tk and x["p0"]]
        ser.sort(key=lambda x: x["date"])
        n_raw = 0
        for x in ser:
            x["op"] = x["conf"]
            if raw is not None and (x["date"], tk) in raw:
                x["conf"] = float(raw[(x["date"], tk)])
                n_raw += 1
        post = [i for i, x in enumerate(ser) if x["date"] >= WS1_DEPLOY or True]  # full series indexable
        pre_eps = post_eps = post_served = 0
        last_ep = None
        ep_detail = []
        op_lag = {}
        in_run, run_len = False, 0               # episode coalescing state
        for i, x in enumerate(ser):
            if i < 5 or x["date"] < LIVE_START:
                continue
            trail = (x["p0"] - ser[i - 5]["p0"]) / ser[i - 5]["p0"] * 100.0
            if trail > -THETA:
                in_run = False                   # slide over; next dip is new
                continue
            # COALESCING (added 2026-07-27, third detector correction). A slide
            # keeps the trailing window below -THETA for as long as it lasts, so
            # counting every qualifying SESSION emitted one "episode" per day of
            # a single decline: WMT 7/23 (-5.19%) and 7/24 (-5.62%) reported as
            # two episodes with IDENTICAL conf-pre/response (47->38, -9pt)
            # because they overlap. An EPISODE is now the FIRST session of a
            # qualifying run; the run continues until the trail recovers above
            # -THETA. This is the number G1 turns on — independent test cases.
            if in_run:
                run_len += 1
                continue
            in_run, run_len = True, 1
            # LAST-EPISODE DATE (corrected 2026-08-04, fifth instance of a
            # corrected value surviving in a second code path). last_ep used to
            # be assigned on EVERY qualifying session, above the coalescing
            # check, so it reported the last qualifying SESSION (WMT 7/24) while
            # the count and the ledger both correctly reported the coalesced
            # EPISODE (7/23) — a date the 7/27 correction explicitly struck,
            # printed on the gate blocking the exit. It is now assigned only
            # where an episode actually begins, so all three surfaces agree.
            last_ep = x["date"]
            if x["date"] < WS2_DEPLOY:          # baseline era — not the G1 test
                pre_eps += 1
                continue
            post_eps += 1                        # THIS is the acceptance clock
            # RESPONSE LAG (corrected 2026-07-23): the criterion is "confidence
            # responds within <= RESPONSE_SESSIONS of a material trailing move".
            # The baseline is the confidence BEFORE the slide (window start,
            # i-5), NOT the confidence at the episode session — otherwise a
            # same-session (lag-0) response, which is the STRONGEST possible
            # outcome, scores as "not served" because it demands a FURTHER fall.
            pre = ser[i - 5]["conf"]
            lag = None
            if pre is not None:
                for k in range(0, RESPONSE_SESSIONS + 1):
                    if i + k >= len(ser):
                        break
                    c = ser[i + k]["conf"]
                    if c is not None and c < pre:
                        lag = k
                        break
            # operative-channel lag, same baseline rule, kept for disclosure
            olag = None
            opre = ser[i - 5]["op"]
            if opre is not None:
                for k in range(0, RESPONSE_SESSIONS + 1):
                    if i + k >= len(ser):
                        break
                    c = ser[i + k]["op"]
                    if c is not None and c < opre:
                        olag = k
                        break
            op_lag[x["date"]] = olag
            if lag is not None:
                post_served += 1
                drop = pre - ser[i + lag]["conf"]
                ep_detail.append((x["date"], lag, pre, ser[i + lag]["conf"], drop))
            else:
                pending = (i + RESPONSE_SESSIONS) >= len(ser)   # window not elapsed
                ep_detail.append((x["date"], None, pre, x["conf"], None if pending else 0))
        post_sessions = sum(1 for x in ser if x["date"] >= WS2_DEPLOY)
        sessions_since = (sum(1 for x in ser if x["date"] > last_ep)
                          if last_ep is not None else None)
        out[tk] = dict(episodes=post_eps, served=post_served, pre=pre_eps,
                       last=last_ep, since=sessions_since, detail=ep_detail,
                       post_sessions=post_sessions, n=len(ser),
                       channel=("RAW" if raw is not None else "OPERATIVE"),
                       n_raw=n_raw, op_lag=op_lag)
    return out


def ws1_blend(rows, blend):
    """WS1/G2 — gate-flip net and confirm/discount arms (post-deploy only)."""
    idx = {(x["date"], x["ticker"]): x for x in rows}
    confirm, discount, flips, net = [], [], [], 0
    flips_sell, net_sell = [], 0
    adjusted = 0
    for (d, tk), b in blend.items():
        if d < WS1_DEPLOY:
            continue
        base, bl = b.get("base"), b.get("blend")
        if not isinstance(base, (int, float)) or not isinstance(bl, (int, float)):
            continue
        if bl != base:
            adjusted += 1
        row = idx.get((d, tk))
        if row is None or row["ret5"] is None:
            continue
        if b["signal"] in ("BUY", "SELL"):
            if bl > base:
                confirm.append(row)
            elif bl < base:
                discount.append(row)
        if b["signal"] == "BUY" and ((base >= BUY_GATE) != (bl >= BUY_GATE)):
            good = (row["ret5"] > 0) == (bl >= BUY_GATE)
            net += 1 if good else -1
            flips.append((d, tk, base, bl, row["ret5"], good))
        # DP-3C-as (RULED 2026-09-25): a SELL crossing ITS OWN gate on the
        # other channel is a gate-flip too. Kept as a SEPARATE ledger so the
        # BUY ledger above -- the record since 2026-07-13 -- is not silently
        # re-based; a SELL flip is "good" when the blend's side of the gate
        # matched the outcome (price fell <=> blend cleared 65).
        if b["signal"] == "SELL" and ((base >= SELL_GATE) != (bl >= SELL_GATE)):
            good = (row["ret5"] < 0) == (bl >= SELL_GATE)
            net_sell += 1 if good else -1
            flips_sell.append((d, tk, base, bl, row["ret5"], good))
    nc, ac = _acc(confirm)
    nd, ad = _acc(discount)
    return dict(adjusted=adjusted, n_confirm=nc, acc_confirm=ac,
                n_discount=nd, acc_discount=ad, flips=flips, net=net,
                flips_sell=flips_sell, net_sell=net_sell)


def near_miss(rows):
    nm = [x for x in rows if x["signal"] == "BUY"
          and isinstance(x["conf"], (int, float)) and 60 <= x["conf"] < BUY_GATE]
    res = [x for x in nm if x["ret5"] is not None]
    hits = sum(1 for x in res if right5(x["signal"], x["ret5"]))
    hi = [x for x in nm if x["dq"] == "HIGH"]
    hres = [x for x in hi if x["ret5"] is not None]
    hhits = sum(1 for x in hres if right5(x["signal"], x["ret5"]))
    return dict(total=len(nm), resolved=len(res), hits=hits,
                rate=(100.0 * hits / len(res) if res else 0.0),
                hi_total=len(hi), hi_resolved=len(hres), hi_hits=hhits,
                hi_rate=(100.0 * hhits / len(hres) if hres else 0.0))


def weekly_bands(rows):
    """Band +5d hit rate aggregated to ISO WEEKS, not cohorts.

    THE SQUISH IS STRUCTURAL, NOT COSMETIC. One x-tick per cohort on an
    unbounded time series grows at ~+5 ticks/week and always loses eventually
    — no resolution, figure width or embed scale saves it. Weekly buckets
    change the GROWTH RATE to +1/week: 47 cohorts become 10 weeks, and the
    axis stays legible through the 3-B exit review and beyond. It also buries
    less signal in noise — per-cohort bands swing wildly on n=5-11, weekly
    they read on n roughly 18-57.

    SCOPE NOTE: 50-59 vs 60-69 is the RETIRED Q1 guardrail question (Q1-R
    closed, guardrail and T2 retired). It is carried here as CONTEXT only —
    population monitoring — never as one of the four open questions.
    """
    buckets = defaultdict(lambda: {"b59": [], "b69": []})
    for x in rows:
        if x["ret5"] is None or not isinstance(x["conf"], (int, float)):
            continue
        y, w, _ = x["date"].isocalendar()
        if 50 <= x["conf"] < 60:
            buckets[(y, w)]["b59"].append(x)
        elif 60 <= x["conf"] < 70:
            buckets[(y, w)]["b69"].append(x)
    out = []
    for key in sorted(buckets):
        n59, a59 = _acc(buckets[key]["b59"])
        n69, a69 = _acc(buckets[key]["b69"])
        out.append(dict(week=key, label=f"wk{key[1]}",
                        n59=n59, a59=a59, n69=n69, a69=a69))
    return out


def collect(tracker, logs):
    rows = load_rows(tracker)
    blend = load_blend(logs) if logs else {}
    raw = load_raw(logs) if logs else None          # DP-3C-an: G1 scores RAW
    try:
        runx = run_basis_crossread(logs) if logs else {}
    except Exception as e:                           # noqa: BLE001
        runx = {"error": str(e)}
    _paths = []
    # What log set did we ACTUALLY read? The WS1 ledger is built entirely from
    # it, so a reader cannot judge that row without this. See signal_logs.
    try:
        import signal_logs
        _paths, log_info = signal_logs.discover(logs) if logs else ([], dict(
            n=0, n_archived=0, n_loose=0, n_excluded_retired=0,
            first=None, last=None))
        log_report = signal_logs.report(log_info, indent="")
        log_warn = signal_logs.short_span_warning(log_info, indent="")
    except Exception as e:
        log_info, log_report, log_warn = {}, f"[logs] unavailable: {e}", ""
    live = [x for x in rows if x["date"] >= LIVE_START]
    n59, a59 = _acc([x for x in live if isinstance(x["conf"], (int, float)) and 50 <= x["conf"] < 60])
    n69, a69 = _acc([x for x in live if isinstance(x["conf"], (int, float)) and 60 <= x["conf"] < 70])
    nH, aH = _acc([x for x in live if x["dq"] == "HIGH"])
    nM, aM = _acc([x for x in live if x["dq"] == "MEDIUM"])
    cohort_dates = sorted({x["date"] for x in rows})
    try:
        import episodes
        # DP-3C-ar (2026-09-25): run-fault dropouts bridge, never split.
        drops = episodes.dropouts_from_logs(
            _paths, present={(x["ticker"], x["date"]) for x in rows}) if logs else set()
        k70 = episodes.keep70(rows, cohort_dates, dropouts=drops)     # DP-3C-y ruled basis
        arm = episodes.dp3cw_arm(rows, cohort_dates, dropouts=drops)  # DP-3C-w, blind
    except Exception as e:                                  # noqa: BLE001
        k70, arm = None, dict(error=str(e))
    return dict(
        k70=k70, dp3cw=arm,
        tracker=tracker, logs=logs,
        log_info=log_info, log_report=log_report, log_warn=log_warn,
        as_of=max(x["date"] for x in rows), n_rows=len(rows),
        n_cohorts=len({x["date"] for x in rows}),
        ws1=ws1_blend(rows, blend), ws2=ws2_episodes(rows, raw), nm=near_miss(rows),
        runx=runx,
        bands=dict(n59=n59, a59=a59, n69=n69, a69=a69),
        dq=dict(nH=nH, aH=aH, nM=nM, aM=aM),
        weekly=weekly_bands(rows),
    )


# ------------------------------------------------------------------ output --
# ONE SOURCE, THREE RENDERINGS. question_rows()/context_line()/provenance() are
# consumed by to_markdown AND by embed_into_workbook, so monitor_strip.md and
# the embedded "Monitor Strip" sheet cannot drift apart. The sheet is a
# RENDERING of the metrics dict, never a transcription of the markdown.
def _plain(s):
    """Strip the markdown emphasis markers for the Excel rendering."""
    return s.replace("**", "")


def provenance(m):
    return (f"Auto-generated by monitor_strip.py · source: {m.get('tracker','?')} "
            f"(Signals tab) + {m.get('logs','?')} · as of {m['as_of']} · "
            f"{m['n_rows']} signal rows. Returns computed from the Price columns "
            f"(cache-independent). Episode threshold THETA={THETA:.1f}% from {THETA_SRC}.")


def context_line(m):
    nm, b, dq = m["nm"], m["bands"], m["dq"]
    return ("**Context** (monitoring only — the Q1 guardrail is retired; the "
            "band split below is population context, not a decision input) — "
            f"registry {nm['total']} near-miss BUYs · "
            f"live bands 50-59 {b['a59']:.1f}% (n={b['n59']}) vs 60-69 {b['a69']:.1f}% (n={b['n69']}) · "
            f"DQ HIGH {dq['aH']:.1f}% (n={dq['nH']}) vs MEDIUM {dq['aM']:.1f}% (n={dq['nM']}).")


def _h4_state(n_ok, r_ok):
    """H4's state, read from the ruling registry rather than recomputed.

    ANALYST NOTE (2026-09-08): this cell used to end "— 2 consecutive required,
    NOT TRACKED HERE", and the H4 watchdog carried the same disclaimer. DP-3C-x
    had already ruled H4 PROMOTED on 2026-09-03, effective 2026-09-01, on three
    consecutive passing readings. Two instruments were disclaiming a condition
    that a third document had already satisfied. Both now read rulings.py, and
    the streak is counted from a durable log instead of recalled.
    """
    try:
        import rulings
        if not rulings.is_open("H4"):
            r = rulings.RULINGS["H4"]
            return (f"RULED {r['dp']}: {r['status']} (ruled {r['ruled_on']}, "
                    f"effective {r['effective']}) — monitoring only, no verdict")
        run = rulings.consecutive_passes("H4")
        streak = f" — {run} consecutive passing reading(s) of {H4_CONSECUTIVE} required"
    except Exception:
        streak = f" — {H4_CONSECUTIVE} consecutive required (streak unavailable)"
    return (f"{'passes this reading' if (n_ok and r_ok) else 'demoted'} "
            f"({'n ok' if n_ok else 'n short'}, "
            f"{'rate ok' if r_ok else 'rate FAILING'})"
            + (streak if (n_ok and r_ok) else ""))


def _dp3cw_row(m):
    """DP-3C-w's prospective arm — ADDED 2026-09-08, COUNTED 2026-09-16.

    On 2026-09-08 this row reported the clock only, because episode
    qualification belonged to "the registry that owns that rule" and a
    second definition would have been a second source of truth. That owner
    now exists as episodes.dp3cw_arm(), and this row calls it -- one
    definition, two readers. The actionable registry RECORDS the reading;
    this row only DISPLAYS it.

    BLIND BY CONSTRUCTION (DP-3C-ah): below 10 resolved qualifying episodes
    the function returns counts only; rho does not exist to be printed.
    """
    try:
        import rulings
        r = rulings.RULINGS["DP-3C-w"]
        opened, bar, status = r["effective"], r["bar"], r["status"]
        recorded = rulings.readings("DP-3C-w")
    except Exception:
        opened, bar, status, recorded = dt.date(2026, 9, 3), "see DP-3C-w", "OPEN", []
    arm = m.get("dp3cw") or {}
    if "error" in arm or "n_open" not in arm:
        reading = (f"arm opened **{opened}**; counter unavailable "
                   f"({arm.get('error', 'no data')})")
        state = f"{status} — counter unavailable"
    else:
        reading = (f"arm opened **{opened}**: **{arm['n_open']} episode(s) opened, "
                   f"{arm['n_resolved']} resolved** of 10 needed; "
                   f"{len(arm['tickers'])} ticker(s) of 4 "
                   f"({', '.join(arm['tickers']) or 'none'}). Discovery sample "
                   f"(21 rows, 3 names, 4 episodes, ρ = −0.834) is FROZEN and never re-read."
                   + (" DP-3C-ar bridged (run-fault dropout, not a split): "
                      + ", ".join(f"{t} {d}" for t, d in arm["bridged"]) + "."
                      if arm.get("bridged") else ""))
        if recorded:
            e = recorded[0]
            state = (f"READ {e['date']} (recorded): {e['detail'].get('verdict')}")
        elif arm.get("read_ready"):
            state = f"READ DATE REACHED — {arm['verdict']} (recorded by the actionable registry)"
        else:
            state = "COLLECTING — counts only; ρ is not computed before n = 10"
    return ("**DP-3C-w** confidence inversion (prospective)", reading, bar, state)


def _runx_text(m, tk):
    """DP-3C-an cross-read line: the OTHER basis, reported beside, never scored."""
    rx = m.get("runx") or {}
    if "error" in rx:
        return f"Run-basis cross-read unavailable ({rx['error']})."
    eps = rx.get(tk, [])
    if not eps:
        return ("Run-basis cross-read (DP-3C-an; D2 logs, the damper's series; "
                "reported, not scored): no episode.")
    parts = [f"{d} trail {tr:+.2f}% → "
             + (f"lag {lg}" if lg is not None else
                ("pending" if pend else f"NO RESPONSE ≤{RESPONSE_SESSIONS}"))
             for d, tr, lg, pend in eps]
    return ("**Run-basis cross-read** (DP-3C-an; D2 logs, the damper's series; "
            "reported, not scored): " + "; ".join(parts) + ".")


def question_rows(m):
    """The open questions as (question, reading, bar, state) tuples."""
    ws1, ws2, nm = m["ws1"], m["ws2"], m["nm"]
    h4_n_ok = nm["hi_resolved"] >= H4_MIN_N
    h4_r_ok = nm["hi_rate"] >= H4_MIN_HIT
    out = []
    out.append((
        "**WS1 / G2** blend vs base",
        f"gate-flip net **{ws1['net']:+d}** ({len(ws1['flips'])} flip(s)); "
        f"confirm {ws1['acc_confirm']:.0f}% (n={ws1['n_confirm']}) "
        f"vs discount {ws1['acc_discount']:.0f}% (n={ws1['n_discount']}). "
        f"SELL-gate flips (DP-3C-as, separate ledger from 2026-09-25): "
        f"{len(ws1.get('flips_sell', []))} resolved, net {ws1.get('net_sell', 0):+d}. "
        # ADDED 2026-09-08. This ledger is built ENTIRELY from the logs — the
        # blend has no tracker column by design — so the log span is not
        # provenance trivia, it is the ledger's denominator. Without it, the
        # 2026-09-08 truncation from 4 resolved flips to 1 was invisible.
        f"**Built from {m['log_info'].get('n', 0)} log(s)"
        + (f", {m['log_info']['first']} .. {m['log_info']['last']}"
           if m["log_info"].get("first") else "")
        + ".** A cumulative ledger cannot be read past the logs it was built "
          "from; if that span is short, this row is a window, not a record.",
        # FIXED 2026-08-13. This row printed a LIVE acceptance bar and a state of
        # "on track"/"negative" for a gate DESCOPED on 2026-07-31 - first flagged
        # 2026-08-05 and carried through four-plus regenerations. The numbers
        # above are still computed and still worth seeing; what was wrong was
        # scoring them against a criterion that no longer exists.
        "DESCOPED 2026-07-31 — no live bar; reopens on T-G2-a/b/c",
        "DESCOPED (readings are context only; see gate X8)",
    ))
    def _evidence(tk):
        return [(d, lg) for d, lg, _p, _n, _dr in ws2[tk].get("detail", [])
                if (tk, d) not in G1_VACATED
                and ((tk, d) in G1_SURVIVES or d >= D2_START)]
    pooled_ev = sum(len(_evidence(t)) for t in TRACERS)
    for tk in TRACERS:
        e = ws2[tk]
        last = e["last"].isoformat() if e["last"] else "none"

        def _g1_tag(d):
            if (tk, d) in G1_VACATED:
                return " [VACATED, DP-3C-aa]"
            if (tk, d) in G1_SURVIVES:
                return " [stands, DP-3C-aa]"
            if d < D2_START:
                return " [pre-fix: recorded, not evidence]"
            return " [corrected channel]"
        def _chan(d, lg):
            # DP-3C-an: an episode whose response differs by channel is marked.
            ol = e.get("op_lag", {}).get(d, lg)
            if e.get("channel") != "RAW" or ol == lg:
                return ""
            return (f" [CHANNEL-SENSITIVE: operative "
                    f"{'lag ' + str(ol) if ol is not None else 'no response'}]")
        lags = ", ".join(
            (f"{d} lag {lg} ({pre:g}→{now:g}, −{dr:g}pt)" if lg is not None
             else f"{d} NO RESPONSE YET" if dr is None else f"{d} no response")
            + _g1_tag(d) + _chan(d, lg)
            for d, lg, pre, now, dr in e.get("detail", []))
        evidence = _evidence(tk)
        ev_served = sum(1 for _d, lg in evidence if lg is not None)
        # CHANNEL AND BASIS DISCLOSURE, added 2026-08-21 per the 8/20 review's
        # finding #2. This strip reported ONE response number and never said
        # which confidence channel produced it. It is the OPERATIVE channel:
        # ws2_episodes() reads x["conf"], which is the tracker's Conf% column =
        # json.confidence = D.op, i.e. POST-damping. G1's FAIL condition is
        # "model-side remedy class exhausted at 3-B", and D1 is not the remedy
        # under test, so the channel that ANSWERS G1 is the RAW one. The two
        # agreed on every session until 2026-08-20, the first post-deploy session
        # on which a tracer was damped; on that episode they returned lag 0
        # operative against lag 1 raw. Both cleared the <=2 bar so the disposition
        # did not turn on it -- it will the moment either channel reads 3+.
        # The trailing move is likewise THIS tool's basis: `window` TRACKER ROWS
        # off Price at Signal, NOT market sessions off closes, while THETA is
        # imported from risk_engine, which damps on the other basis.
        # AMENDED 2026-09-25 (DP-3C-an, RULED): the paragraph above is history.
        # G1 is now scored on the RAW channel (load_raw -> ws2_episodes(raw)),
        # the operative lag is printed only where it differs, and the TRACKER
        # basis is RULED as G1's episode basis (not left as a disclosure).
        out.append((
            f"**WS2 / G1** {tk} clock",
            (f"**{e['episodes']} post-deploy episode(s)** in {e['post_sessions']} session(s)"
             f" ({e['served']} responded ≤{RESPONSE_SESSIONS} sessions); "
             f"{e['pre']} pre-deploy; last episode {last}"
             + (f", {e['since']} session(s) ago" if e["since"] is not None else "")
             + (f". Episodes: {lags}" if lags else "")
             + (f". **Scored on the RAW channel** (DP-3C-an, ruled 2026-09-25: "
                f"`confidence_raw` from the logs, {e.get('n_raw', 0)} row(s); the "
                f"operative lag is shown only where it differs). "
                if e.get("channel") == "RAW" else
                ". **Scored on the OPERATIVE channel** (logs unavailable — "
                "DP-3C-an requires RAW; this reading is a fallback). ")
             + "Episode basis (DP-3C-an): five tracker ROWS off `Price at "
               "Signal`, ending at the signal row — the move as it stood when "
               "the model answered; the run's `D[trail]` (closes, prior "
               "sessions) is the damper's basis, not G1's. "
             + _runx_text(m, tk)),
            f"read ONCE at n = {G1_READ_N} evidence episodes pooled across WMT + GM "
            f"(DP-3C-an); at the read, ≥1 episode with response ≤{RESPONSE_SESSIONS} "
            f"sessions [R]. Evidence per DP-3C-aa: corrected channel from {D2_START}, "
            f"plus WMT 2026-07-23",
            (f"{len(evidence)} evidence episode(s) here, {ev_served} responded; pooled "
             f"{pooled_ev} of {G1_READ_N} — "
             + ("INSUFFICIENT TEST CONDITIONS; bar not lowered" if pooled_ev < G1_READ_N
                else "READ POINT REACHED — the read is taken in a dated review, not here")
             if e["episodes"] else "NO TEST CASES YET"),
        ))
    out.append((
        "**H4** DQ-conditional gate",
        f"HIGH-DQ near-miss **{nm['hi_rate']:.0f}%** "
        f"({nm['hi_hits']}/{nm['hi_resolved']} resolved, {nm['hi_total']} total)",
        f"n ≥ {H4_MIN_N} resolved AND hit ≥ {H4_MIN_HIT:.0f}% "
        f"on {H4_CONSECUTIVE} consecutive readings",
        _h4_state(h4_n_ok, h4_r_ok),
    ))
    k70 = m.get("k70")
    if k70 and k70["ep_n"]:
        # RULED 2026-09-03 (DP-3C-y), applied 2026-09-16. The EPISODE basis,
        # scored on the opening row, is the verdict; the row basis is printed
        # beside it as descriptive. The bar is "<= 50.0%" (was "< 50%" here).
        # Computed by episodes.keep70(), shared with the near-miss registry.
        # A second instrument is also called KEEP-70 --
        # build_near_miss_registry's FROZEN 2026-06-12 verdict on the 7-row
        # locked cohort. Different question; both may be right.
        out.append((
            "**KEEP-70** the BUY gate",
            f"rejected BUY **episodes** that would have paid: "
            f"**{k70['ep_rate']:.1f}%** ({k70['ep_hit']}/{k70['ep_n']}, "
            f"{k70['episodes']} episodes); row basis {k70['row_rate']:.1f}% "
            f"({k70['row_hit']}/{k70['row_n']}) — descriptive only",
            "≤ 50.0% supports keeping 70 (DP-3C-y: episode basis, opening row)",
            # DP-3C-au (RULED 2026-09-25): never a state without its margin; a
            # reading one resolution from flipping is KNIFE-EDGE; and neither
            # state moves or certifies the gate.
            (("SUPPORTED" if k70["verdict"] == "SUPPORTED" else "NOT SUPPORTED")
             + (f" — margin {k70['margin_pt']:+.2f}pt" if k70.get("margin_pt") is not None else "")
             + (f"; next hit → {k70['after_hit']}, next miss → {k70['after_miss']}"
                if k70.get("after_hit") else "")
             + (" — KNIFE-EDGE" if k70.get("knife_edge") else "")
             + ". Recorded; neither state moves or certifies the gate (DP-3C-y, DP-3C-au)"),
        ))
    else:
        out.append((
            "**KEEP-70** the BUY gate",
            f"row basis {nm['rate']:.1f}% ({nm['hits']}/{nm['resolved']}); "
            f"episode basis unavailable",
            "≤ 50.0% supports keeping 70 (DP-3C-y: episode basis)",
            "UNREADABLE — the ruled basis could not be computed",
        ))
    out.append(_dp3cw_row(m))
    return out


def to_markdown(m):
    ws1 = m["ws1"]
    L = []
    L.append("# Monitor strip — open questions")
    L.append(f"\n*{provenance(m)}*\n")
    L.append("| Question | Reading | Bar | State |")
    L.append("|---|---|---|---|")
    for q, reading, bar, state in question_rows(m):
        L.append(f"| {q} | {reading} | {bar} | {state} |")
    L.append("")
    L.append(context_line(m))
    if ws1["flips"]:
        L.append("\n**Gate-flips (WS1):**\n")
        L.append("| Date | Ticker | Base | Blend | +5d | Blend better? |")
        L.append("|---|---|---:|---:|---:|---|")
        for d, tk, base, bl, ret, good in ws1["flips"]:
            L.append(f"| {d} | {tk} | {base} | {bl} | {ret*100:+.2f}% | "
                     f"{'yes' if good else 'no'} |")
    if ws1.get("flips_sell"):
        L.append("\n**SELL-gate flips (WS1, DP-3C-as — separate ledger, gate 65):**\n")
        L.append("| Date | Ticker | Base | Blend | +5d | Blend better? |")
        L.append("|---|---|---:|---:|---:|---|")
        for d, tk, base, bl, ret, good in ws1["flips_sell"]:
            L.append(f"| {d} | {tk} | {base} | {bl} | {ret*100:+.2f}% | "
                     f"{'yes' if good else 'no'} |")
    L.append("\n*Advisory-only · no orders · not financial advice.*")
    return "\n".join(L)


THEMES = {
    # Excel embed sits on a white sheet -> light is the default. dark matches
    # the design mock as rendered in a dark-mode viewer.
    "light": dict(bg="#FFFFFF", text="#1A1A1A", sub="#6B6B66", grid="#E6E6E3",
                  axis="#B8B8B3", pos="#1A73E8", neg="#D93025", mute="#9AA0A6"),
    "dark":  dict(bg="#1F1F1E", text="#EDEDEB", sub="#9A9A94", grid="#3A3A38",
                  axis="#55554F", pos="#4C9AFF", neg="#F0674A", mute="#8A8A84"),
}
BAND_59 = "#2E7DD7"      # 50-59 band
BAND_69 = "#E8663C"      # 60-69 band


def _cards(m):
    """The four open questions as (label, value, sub, kind) — kind drives colour.
    The KEEP-70 card reads the EPISODE basis (DP-3C-y) since 2026-09-16."""
    ws1, ws2, nm = m["ws1"], m["ws2"], m["nm"]
    eps = sum(ws2[t]["episodes"] for t in TRACERS)
    # DP-3C-aa (applied 2026-09-16): the card counts EVIDENCE episodes, not
    # every detected episode, so it cannot show the vacated WMT 08-20 response.
    ev = [(t, d, lg) for t in TRACERS
          for d, lg, _p, _n, _dr in ws2[t].get("detail", [])
          if (t, d) not in G1_VACATED and ((t, d) in G1_SURVIVES or d >= D2_START)]
    ev_served = sum(1 for _t, _d, lg in ev if lg is not None)
    h4_ok = (nm["hi_resolved"] >= H4_MIN_N) and (nm["hi_rate"] >= H4_MIN_HIT)
    if eps:
        # DP-3C-an (2026-09-25): the card states the pooled read point, and is
        # shorter than before -- the old sub-label ran into the H4 card.
        ws2_val, ws2_sub, ws2_kind = (f"{len(ev)}",
                                      f"of {G1_READ_N} to read · {ev_served} served "
                                      f"\u2264{RESPONSE_SESSIONS} (raw)",
                                      "pos" if ev_served else "neg")
    else:
        nulls = max(ws2[t]["post_sessions"] for t in TRACERS)
        ws2_val, ws2_sub, ws2_kind = f"{nulls}", "null cohorts · no episode", "neg"
    return [
        ("WS1 blend (G2)", f"{ws1['net']:+d}",
         f"gate-flip net · n={len(ws1['flips'])}", "pos" if ws1["net"] >= 0 else "neg"),
        ("WS2 clock (G1)", ws2_val, ws2_sub, ws2_kind),
        ("H4 near-miss", f"{nm['hi_rate']:.0f}%",
         f"{nm['hi_hits']}/{nm['hi_resolved']} · bar is {H4_MIN_HIT:.0f}% "
         f"at n≥{H4_MIN_N}, ×{H4_CONSECUTIVE}",
         "pos" if h4_ok else "mute"),
        _keep70_card(m, nm),
    ]


def _keep70_card(m, nm):
    """KEEP-70 card on the RULED basis (DP-3C-y, applied 2026-09-16)."""
    k = m.get("k70")
    if k and k["ep_n"]:
        return ("KEEP-70 (episodes)", f"{k['ep_rate']:.1f}%",
                f"{k['ep_hit']}/{k['ep_n']} episodes · bar ≤50.0% · rows {k['row_rate']:.0f}%",
                "pos" if k["ep_rate"] <= 50.0 else "neg")
    return ("KEEP-70 (rows only)", f"{nm['rate']:.1f}%",
            f"{nm['hits']}/{nm['resolved']} rows · ruled basis unavailable", "mute")


def make_png(m, out_path, theme=DEFAULT_THEME, width_px=EMBED_WIDTH_PX):
    """Fixed-width dashboard: four open-question cards over the weekly band
    aggregate. Card count is constant by construction and the chart grows at
    +1 x-tick per WEEK, so this figure never squishes as history accumulates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    T = THEMES.get(theme, THEMES["light"])
    wk = m.get("weekly") or []
    fig_w = 12.0
    fig = plt.figure(figsize=(fig_w, 5.4), facecolor=T["bg"])
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 3.3], hspace=0.30,
                          left=0.055, right=0.975, top=0.96, bottom=0.085)

    # ---------------------------------------------------------------- cards --
    ax = fig.add_subplot(gs[0]); ax.axis("off"); ax.set_facecolor(T["bg"])
    cards = _cards(m)
    for i, (label, value, sub, kind) in enumerate(cards):
        x = i / len(cards)
        ax.text(x, 0.92, label, transform=ax.transAxes, ha="left", va="top",
                fontsize=10.5, fontweight="bold", color=T["text"])
        ax.text(x, 0.52, value, transform=ax.transAxes, ha="left", va="center",
                fontsize=27, fontweight="bold", color=T[kind])
        ax.text(x, 0.06, sub, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=8.5, color=T["sub"])

    # ---------------------------------------------------------------- chart --
    ax = fig.add_subplot(gs[1]); ax.set_facecolor(T["bg"])
    if wk:
        idx = np.arange(len(wk)); w = 0.38
        ax.bar(idx - w / 2, [d["a59"] for d in wk], w, color=BAND_59, zorder=3)
        ax.bar(idx + w / 2, [d["a69"] for d in wk], w, color=BAND_69, zorder=3)
        ax.set_xticks(idx)
        ax.set_xticklabels([d["label"] for d in wk], fontsize=9, color=T["sub"])
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 10))
    ax.set_yticklabels([f"{v}%" for v in range(0, 101, 10)],
                       fontsize=8.5, color=T["sub"])
    ax.yaxis.grid(True, color=T["grid"], lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(T["axis"]); ax.spines[s].set_linewidth(0.8)
    ax.tick_params(length=0)

    handles = [plt.Rectangle((0, 0), 1, 1, color=BAND_59),
               plt.Rectangle((0, 0), 1, 1, color=BAND_69)]
    leg = ax.legend(handles, ["50\u201359 band", "60\u201369 band"],
                    loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2,
                    frameon=False, handlelength=0.9, handleheight=0.9,
                    fontsize=9.5, columnspacing=1.4, handletextpad=0.5)
    for t in leg.get_texts():
        t.set_color(T["text"]); t.set_fontweight("bold")
    ns = [d[k] for d in wk for k in ("n59", "n69")] or [0]
    ax.text(0.26, 1.015, f"weekly aggregate · {len(wk)} points, not {m.get('n_cohorts', 0)}"
                         f"   ·   n={min(ns)}\u2013{max(ns)} per band-week   ·   "
                         f"context only (Q1 guardrail retired)",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, color=T["sub"])

    fig.savefig(out_path, dpi=max(100, round(width_px * 1.6 / fig_w)),
                facecolor=T["bg"], bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------- embed --
def _fit_image(png_path, target_w):
    """Resample the PNG to EXACTLY the embed width (LANCZOS) and return the
    path + pixel size. The image is then anchored at its own native size, so
    Excel never rescales it — this is the whole no-squish mechanism.
    Returns (path, w, h). Falls back to the original file if PIL is missing."""
    try:
        from PIL import Image
    except Exception:
        return png_path, None, None
    im = Image.open(png_path)
    if im.width == target_w:
        return png_path, im.width, im.height
    h = max(1, round(im.height * target_w / im.width))
    out = os.path.splitext(png_path)[0] + "_embed.png"
    im.convert("RGB").resize((target_w, h), Image.LANCZOS).save(out, "PNG", optimize=True)
    return out, target_w, h


def _retired_sheets_in(wb):
    """Retired sheets BY CONTENT, not by name.

    Name matching failed on its first live run (2026-07-27): the retired
    guardrail tab had been renamed "Sheet1" in the master, so it walked
    straight through RETIRED_SHEETS and was re-emitted into the report copy
    complete with the line "The 50-59% band must lead 60-69%". A retired
    artifact is identified by what it SAYS, not by what it is called.
    """
    out = []
    for ws in wb.worksheets:
        if ws.title in RETIRED_SHEETS:
            out.append(ws.title)
            continue
        head = " ".join(str(ws.cell(r, 1).value or "") for r in (1, 2, 3)).lower()
        if any(sig in head for sig in RETIRED_SIGNATURES):
            out.append(ws.title)
    return out


def embed_into_workbook(m, png_path, embed_path, width_px=EMBED_WIDTH_PX,
                        theme=DEFAULT_THEME):
    """Write/refresh the 'Monitor Strip' sheet into embed_path (the GENERATED
    report copy). Idempotent: the sheet is deleted and rebuilt, retired sheets
    are dropped, and the strip is re-parked in canonical order every run.
    Never call this on the master tracker."""
    from openpyxl.styles import Alignment, Font, PatternFill

    dark = (theme == "dark")
    # The strip is a dashboard tile. On dark the whole SHEET is styled to match
    # so the image reads as designed rather than as a black rectangle pasted
    # onto white; gridlines are hidden for the same reason.
    c_bg   = "FF1F1F1E" if dark else "FFFFFFFF"
    c_hdr  = "FF2E2E2C" if dark else "FFF2F2F2"
    c_text = "FFEDEDEB" if dark else "FF1A1A1A"
    c_sub  = "FF9A9A94" if dark else "FF7F7F7F"

    wb = openpyxl.load_workbook(embed_path)          # data_only=False: keep formulas
    dropped = [s for s in _retired_sheets_in(wb) if s != SHEET_NAME]
    for s in dropped:
        del wb[s]
    if SHEET_NAME in wb.sheetnames:
        del wb[SHEET_NAME]                            # replace, never stack
    ws = wb.create_sheet(SHEET_NAME)
    ws.sheet_view.showGridLines = not dark

    f_title = Font(bold=True, size=13, color=c_text)
    f_grey  = Font(italic=True, size=9, color=c_sub)
    f_hdr   = Font(bold=True, size=10, color=c_text)
    f_body  = Font(size=10, color=c_text)
    fill    = PatternFill("solid", fgColor=c_hdr)
    wrap    = Alignment(vertical="top", wrap_text=True)

    hdr_cells = []                                    # re-filled after the bg tile

    def _band(row, col, text):
        cell = ws.cell(row, col, text)
        cell.font = f_hdr
        cell.fill = fill
        hdr_cells.append((row, col))

    ws.cell(1, 1, "Monitor Strip — open questions").font = f_title
    ws.cell(2, 1, provenance(m)).font = f_grey

    # --- the strip image, at the top: this sheet IS the daily glance ---------
    r = 4
    if png_path and os.path.exists(png_path):
        from openpyxl.drawing.image import Image as XLImage
        fit, w, h = _fit_image(png_path, width_px)
        img = XLImage(fit)                            # native size == embed size
        ws.add_image(img, "A4")                       # str anchor -> oneCellAnchor
        r = 4 + (h // PX_PER_ROW if h else 22) + 2

    # --- the auditable table ------------------------------------------------
    head = r
    for c, t in enumerate(("Question", "Reading", "Bar", "State"), start=1):
        _band(head, c, t)
    r += 1
    for q, reading, bar, state in question_rows(m):
        for c, t in enumerate((q, reading, bar, state), start=1):
            cell = ws.cell(r, c, _plain(t))
            cell.alignment = wrap
            cell.font = f_body
        r += 1

    r += 1
    ws.cell(r, 1, _plain(context_line(m))).font = Font(size=9, color=c_text)
    r += 2

    # --- WS1 gate-flips -----------------------------------------------------
    if m["ws1"]["flips"]:
        ws.cell(r, 1, "Gate-flips (WS1)").font = f_hdr
        r += 1
        for c, t in enumerate(("Date", "Ticker", "Base", "Blend", "+5d",
                               "Blend better?"), start=1):
            _band(r, c, t)
        r += 1
        for d, tk, base, bl, ret, good in m["ws1"]["flips"]:
            for c, v in enumerate((d.isoformat(), tk, base, bl,
                                   round(ret * 100, 2), "yes" if good else "no"), start=1):
                ws.cell(r, c, v).font = f_body
            ws.cell(r, 5).number_format = "+0.00;-0.00"
            r += 1
        r += 1

    # --- WS2 episode ledger (the G1 acceptance clock, row by row) ------------
    ws.cell(r, 1, f"WS2 / G1 episode ledger (THETA = {THETA:.1f}%) — "
                  f"OPERATIVE channel (post-damping); trailing move over tracker "
                  f"rows off Price at Signal").font = f_hdr
    r += 1
    for c, t in enumerate(("Ticker", "Episode", "Lag", "Conf pre",
                           "Conf at response", "Drop (pt)", "Served"), start=1):
        _band(r, c, t)
    r += 1
    any_ep = False
    for tk in TRACERS:
        for d, lag, pre, now, drop in m["ws2"][tk].get("detail", []):
            any_ep = True
            for c, v in enumerate((tk, d.isoformat(), "—" if lag is None else lag,
                                   pre, now, "—" if drop is None else drop,
                                   "yes" if lag is not None
                                   else ("pending" if drop is None else "no")), start=1):
                ws.cell(r, c, v).font = f_body
            r += 1
    if not any_ep:
        ws.cell(r, 1, "no post-deploy episodes detected yet").font = f_body
        r += 1

    if dropped:
        r += 1
        ws.cell(r, 1, "Retired " + dt.date.today().isoformat() + ": "
                + ", ".join(dropped) + " — Q1-R closed the guardrail question; "
                "guardrail_trace.py is out of the runner.").font = f_grey

    for col, w in (("A", 24), ("B", 92), ("C", 40), ("D", 22),
                   ("E", 18), ("F", 14), ("G", 12)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = ws.cell(head + 1, 1)

    if dark:                                          # tile the sheet background
        bg = PatternFill("solid", fgColor=c_bg)
        for row in range(1, r + 4):
            for col in range(1, 15):
                ws.cell(row, col).fill = bg
        for row, col in hdr_cells:                    # re-apply the header bands
            ws.cell(row, col).fill = fill

    # canonical tab order: park it after the first EMBED_AFTER that exists
    for after in EMBED_AFTER:
        if after in wb.sheetnames:
            target = wb.sheetnames.index(after) + 1
            wb.move_sheet(SHEET_NAME, offset=target - wb.sheetnames.index(SHEET_NAME))
            break

    wb.save(embed_path)
    return dropped


def main(argv=None):
    ap = argparse.ArgumentParser(description="Open-questions monitor strip.")
    ap.add_argument("--tracker",
                    default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"),
                    help="the MASTER tracker (the one you paste into). "
                         "tracker_with_registry.xlsx is a GENERATED report copy.")
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"))
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--theme", choices=("light", "dark"), default=DEFAULT_THEME,
                    help=f"strip + sheet styling (default {DEFAULT_THEME}). "
                         f"dark styles the whole Monitor Strip sheet to match "
                         f"the image and hides gridlines; light keeps a "
                         f"conventional white sheet")
    ap.add_argument("--embed-into", default=None,
                    help="write/refresh a 'Monitor Strip' sheet (as-of line + "
                         "table + strip image) into this .xlsx — pass the "
                         "GENERATED COPY (tracker_with_registry.xlsx), never "
                         "the master")
    ap.add_argument("--embed-width", type=int, default=EMBED_WIDTH_PX,
                    help=f"on-screen px width of the embedded image "
                         f"(default {EMBED_WIDTH_PX}); the PNG is resampled to "
                         f"this exactly so Excel never rescales it")
    args = ap.parse_args(argv)

    m = collect(args.tracker, args.logs)
    md = to_markdown(m)
    print(md)
    md_path = os.path.join(args.out_dir, "monitor_strip.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(f"\nWrote: {md_path}")

    png = None
    if not args.no_png:
        try:
            png = os.path.join(args.out_dir, "monitor_strip.png")
            make_png(m, png, args.theme, args.embed_width)
            print(f"Wrote: {png}")
        except Exception as e:
            png = None
            print(f"(png skipped: {e})")

    if args.embed_into:
        if not os.path.exists(args.embed_into):
            raise SystemExit(f"ERROR: --embed-into target not found: {args.embed_into}")
        if os.path.abspath(args.embed_into) == os.path.abspath(args.tracker):
            raise SystemExit(
                "ERROR: --embed-into must be the GENERATED COPY "
                "(tracker_with_registry.xlsx), not the tracker being read. "
                "Read the master, write the copy.")
        if png is None:
            print("WARNING: no image available (--no-png or render failed) — "
                  "embedding the TABLE ONLY. The sheet's as-of line is still "
                  "current; the strip image is simply absent this run.")
        if not THETA_OK:
            print("WARNING: THETA came from the LOCAL FALLBACK "
                  f"({THETA:.1f}%, {THETA_SRC}), not from "
                  "risk_engine.DampingConfig. The WS2 episode ledger you are "
                  "about to embed is NOT provenance-clean — it may not match "
                  "what D1 actually damps on. Run from the project root with "
                  "the venv active so risk_engine imports, then re-run.")
        dropped = embed_into_workbook(m, png, args.embed_into,
                                      args.embed_width, args.theme)
        if dropped:
            print("Dropped retired sheet(s) from the copy: " + ", ".join(dropped))
            print("  (this line printing on EVERY run means the master still "
                  "carries those tabs - delete them there once)")
        print(f"Embedded '{SHEET_NAME}' sheet into: {args.embed_into}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
