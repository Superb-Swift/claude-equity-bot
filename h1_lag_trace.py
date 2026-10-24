#!/usr/bin/env python3
"""
h1_lag_trace.py  —  Claude Equity Bot, Phase 3-A · H1 success metric

Re-runs the WMT-style confidence-update-lag trace from the Signals tab. This is
the success metric for H1 (prior-5-day price input): Phase 2 showed confidence
trailed price by ~3-5 sessions (the WMT arc held 62% through three ~-11% losses,
then caught up only as the losses shrank). H1 should compress that lag toward
0-1 sessions WITHOUT degrading the +5d band calibration.

The same script runs against the Phase 2 tracker (the baseline below) and, later,
the Phase 3-A tracker — so you can quantify the change.

WHAT IT PRODUCES
    1. Per-cohort trace for the ticker (default WMT): conf, trailing-5d move,
       forward +5d / +10d returns, +5d hit.
    2. A lag estimate: corr(confidence[t], trailing move[t-L]) scanned over
       L = 0..maxlag; the argmax L is the estimated update lag in sessions.
    3. The forward +10d arc (reproduces WMT -15.19 -> +4.31).
    4. A calibration guardrail (RETIRED 2026-07-13, printed as history only):
       the cohort-window 3-band +5d hit rates
       (50-59% must keep leading).
    5. A SUCCESS-METRIC block: what 3-A must show vs this baseline.

USAGE
    python h1_lag_trace.py
    python h1_lag_trace.py --tracker claude_equity_bot_tracker.xlsx --ticker WMT
    python h1_lag_trace.py --ticker NVDA --window 5 --maxlag 5
"""

from __future__ import annotations
import argparse
import datetime as dt
import glob
import math
import os
import re
import sys

import openpyxl

# ---- DAMPING PARAMETERS ARE READ, NEVER RESTATED (added 2026-09-17) ---------
# THETA and FLOOR come from the damping engine itself. The 2026-08-04 desync
# (analyze_log's gate thresholds drifting from risk_engine) is the precedent:
# one field, one source. If risk_engine cannot be imported the reconciliation
# block below is SKIPPED and says so on the face of the exhibit, rather than
# falling back to a remembered 5.0 / 35 -- compute rather than recall.
try:
    from risk_engine import DampingConfig as _DAMP
    THETA_PCT = float(_DAMP.THETA)
    FLOOR_PTS = int(_DAMP.FLOOR)
    DAMP_SRC = "risk_engine.DampingConfig"
except Exception:                                   # pragma: no cover
    THETA_PCT, FLOOR_PTS, DAMP_SRC = None, None, None

SIGNALS_SHEET = "Signals"
FIRST_DATA_ROW = 5
LAST_ROW_CAP = 100_000
COL = dict(date=1, ticker=2, account=3, signal=4, conf=5, dq=6,
           p0=7, p5=8, p10=9, p20=10, r5=11, r10=12, r20=13, right5=14, notes=15)

COHORT_START = dt.date(2026, 5, 18)
COHORT_END = dt.date(2026, 5, 29)
# ---- optional date-window slice (--since / --until) --------------------------
# When either bound is set, the analysis AND the calibration guardrail are
# computed over [SINCE, UNTIL]. With no bounds: analysis uses all rows and the
# guardrail uses the certified Phase 2 cohort window (COHORT_START..COHORT_END).
SINCE = None
UNTIL = None


def _in_window(d):
    if not isinstance(d, dt.date):
        return False
    if SINCE is not None and d < SINCE:
        return False
    if UNTIL is not None and d > UNTIL:
        return False
    return True


def _guardrail_window():
    if SINCE is not None or UNTIL is not None:
        return (SINCE or dt.date.min, UNTIL or dt.date.max)
    return (COHORT_START, COHORT_END)


def _window_label():
    if SINCE is not None or UNTIL is not None:
        return (str(SINCE) if SINCE else 'earliest') + ' .. ' + (str(UNTIL) if UNTIL else 'latest')
    return 'ALL ROWS (guardrail = Phase 2 cohort window)'



# --------------------------------------------------------------------------- #
def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    return v if isinstance(v, dt.date) else None


def conf_pct(v):
    """Tracker Conf% cells are stored as fractions (0.57), so they must be scaled.

    DEFECT FIXED 2026-08-21 (found in the 8/21 closing review, on a live exhibit).
    This returned a bare `v * 100.0`, and IEEE-754 makes 0.57 * 100 ==
    56.99999999999999. The two display paths below then printed `int(conf)`,
    which TRUNCATES -- so every confidence of 0.29, 0.57 or 0.58 (the only three
    two-decimal fractions with this property) rendered ONE POINT LOW. It reached
    the record: h1_lag_trace_GM_3B.md printed 56% for 2026-08-17 and 2026-08-20
    against a tracker, a log `confidence`, a `confidence_raw` and a
    `confidence_blend` that ALL read 57, and printed 57% for 2026-07-21 against
    a tracker 58 -- a value present in no channel anywhere in the stack.
    The `--raw-from-logs` variant escaped on the post-deploy rows only because
    the override replaces the float with an exact int parsed from the log, which
    is why the operative and raw exhibits disagreed on two GM sessions that
    carry damp 0 and therefore CANNOT differ by construction.
    SCOPE: display only. `confs` below is the unrounded float, so the lag scan
    and both correlations were never affected -- the 8/21 review states that
    separation rather than leaving it to be assumed.
    """
    if v is None:
        return None
    # round() at the source is deliberate: it removes the dust once, so every
    # consumer -- display, correlation, banding -- sees one number rather than
    # each having to defend itself.
    return round(v * 100.0, 6) if v <= 1.0 else float(v)


def pearson(xs, ys):
    """Pearson r over paired, non-None numeric samples. None if < 3 pairs."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    sxx = sum((p[0] - mx) ** 2 for p in pairs)
    syy = sum((p[1] - my) ** 2 for p in pairs)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def pct(x, plus=False, dash="—"):
    if x is None:
        return dash
    s = f"{x*100:.2f}%"
    return f"+{s}" if (plus and x >= 0) else s


# --------------------------------------------------------------------------- #
def load_series(tracker, ticker):
    wb = openpyxl.load_workbook(tracker, data_only=True)
    ws = wb[SIGNALS_SHEET]
    rows = []
    blank = 0
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        d = as_date(ws.cell(row=r, column=COL["date"]).value)
        tk = ws.cell(row=r, column=COL["ticker"]).value
        if d is None and not tk:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        if not _in_window(d) or str(tk).strip().upper() != ticker.upper():
            continue
        rows.append(dict(
            date=d,
            signal=str(ws.cell(row=r, column=COL["signal"]).value or "").strip(),
            conf=conf_pct(ws.cell(row=r, column=COL["conf"]).value),
            p0=ws.cell(row=r, column=COL["p0"]).value,
            r5=ws.cell(row=r, column=COL["r5"]).value,
            r10=ws.cell(row=r, column=COL["r10"]).value,
            right5=str(ws.cell(row=r, column=COL["right5"]).value or "").strip(),
        ))
    wb.close()
    rows.sort(key=lambda x: x["date"])
    return rows


def band_calibration(tracker):
    """Cohort-window 3-band +5d hit rates (the calibration guardrail)."""
    wb = openpyxl.load_workbook(tracker, data_only=True)
    ws = wb[SIGNALS_SHEET]
    agg = {"40-49": [0, 0], "50-59": [0, 0], "60-69": [0, 0]}
    glo, ghi = _guardrail_window()
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        d = as_date(ws.cell(row=r, column=COL["date"]).value)
        if d is None:
            continue
        if not (glo <= d <= ghi):
            continue
        p = conf_pct(ws.cell(row=r, column=COL["conf"]).value)
        if p is None:
            continue
        b = ("40-49" if 40 <= p < 50 else "50-59" if 50 <= p < 60
             else "60-69" if 60 <= p < 70 else None)
        if b is None:
            continue
        # FIXED 2026-08-26. This previously incremented the denominator
        # for EVERY row in the band and the numerator only on YES, so an
        # unresolved +5d counted as a miss. On the 2026-08-26 slice that
        # deflated the three printed rates by 5.2, 9.5 and 9.5 points --
        # non-uniformly, because it depends on the unresolved tail's band
        # mix, and worst on the newest data. A row belongs in the
        # denominator only once it has an outcome.
        verdict = str(ws.cell(row=r, column=COL["right5"]).value or "").strip().upper()
        if verdict not in ("YES", "NO"):
            continue
        agg[b][1] += 1
        if verdict == "YES":
            agg[b][0] += 1
    wb.close()
    return agg


# --------------------------------------------------------------------------- #
def load_raw_conf_map(patterns):
    """Parse Signal JSON log lines into {(date, TICKER): raw_conf_pct}.

    ANALYST NOTE (WS2 two-channel readout):
        Lever A logs both confidences on every line — "confidence" is the
        OPERATIVE (damped) value that flows to the tracker, and
        "confidence_raw" is the model's own output. The tracker therefore
        carries the operative channel; this loader recovers the RAW channel
        straight from the logs so the pre-registered lag test can be run on
        the model-side series (the honest Lever-B read). Date comes from the
        filename (signals_YYYY-MM-DD.log). PM diagnostic runs APPEND to the
        same signals_DATE.log as the AM run, so the FIRST occurrence per
        (date, ticker) wins — the AM-canonical read — and later PM lines
        can never shadow it.
    """
    tick_re = re.compile(r'"ticker":\s*"([A-Za-z.\-]+)"')
    raw_re = re.compile(r'"confidence_raw":\s*(\d+)')
    # ANALYST NOTE (2026-09-08): glob.glob is NON-RECURSIVE, and the logs have
    #   since been tidied into month subfolders ("05 May signals",
    #   "06 June signals", "07 July Signals", "08 August Signals"). The loose
    #   set in logs/ is now five files — 2026-09-01 onward — so this loader
    #   reported "parsed 5 file(s)" and every raw-channel exhibit narrowed to
    #   the current month WITHOUT SAYING SO. Nothing was deleted; the pattern
    #   simply stopped reaching four months of history.
    #
    #   The damage here is milder than in monitor_strip — whose WS1 ledger is
    #   CUMULATIVE and lost three quarters of its rows — because this loader
    #   only OVERRIDES tracker values where it finds a raw entry and leaves the
    #   rest alone, so the exhibits still rendered full series. But "5 of 43
    #   rows use log RAW confidence" invites the reading "only 5 post-deploy
    #   rows exist", when the true reason was that the other logs were out of
    #   view. signal_logs.discover walks the archive; the span is printed below
    #   so the exhibit states what it was actually built from.
    files, spans = [], []
    try:
        import signal_logs
        for p in patterns:
            found, info = signal_logs.discover(p)
            files.extend(found)
            if info.get("n"):
                spans.append(info)
    except Exception:
        pass
    if not files:
        for p in patterns:
            hits = sorted(glob.glob(p))
            files.extend(hits if hits else ([p] if os.path.exists(p) else []))
    files = sorted(dict.fromkeys(files))
    m = {}
    for fp in files:
        stem = os.path.splitext(os.path.basename(fp))[0]
        try:
            d = dt.date.fromisoformat(stem.replace("signals_", ""))
        except ValueError:
            print(f"   [raw-from-logs] skip (no date in filename): {fp}")
            continue
        with open(fp, encoding="utf-8", errors="replace") as f:
            for line in f:
                if "Signal JSON" not in line:
                    continue
                tm, rm = tick_re.search(line), raw_re.search(line)
                if tm and rm:
                    key = (d, tm.group(1).upper())
                    if key not in m:  # FIRST occurrence wins - AM canonical
                        m[key] = float(rm.group(1))
    dates = sorted({d for d, _t in m})
    span = f", {dates[0]} .. {dates[-1]}" if dates else ""
    arch = sum(s.get("n_archived", 0) for s in spans)
    print(f"   [raw-from-logs] parsed {len(files)} file(s){span}, "
          f"{len(m)} raw-confidence entrie(s)"
          + (f" ({arch} log(s) from archive subfolder(s))" if arch else ""))
    return m


# --------------------------------------------------------------------------- #
def lag_scan_of(confs, trail, maxlag):
    """[(L, r), ...] for L = 0..maxlag. One definition, used by the headline
    scan and by every sensitivity re-run, so a sensitivity can never be
    computed by a second, slightly different estimator."""
    out = []
    for L in range(0, maxlag + 1):
        r = pearson(confs, trail) if L == 0 else pearson(confs[L:], trail[:-L])
        out.append((L, r))
    return out


def best_of(scan):
    """argmax over POSITIVE r, plus the runner-up margin. The margin is the
    point of this function: an argmax reported without the gap to second place
    is a point estimate presented as though the surface had a peak."""
    pos = [(L, r) for L, r in scan if r is not None]
    if not pos:
        return None, None, None
    ranked = sorted(pos, key=lambda t: t[1], reverse=True)
    best_L, best_r = ranked[0]
    margin = (best_r - ranked[1][1]) if len(ranked) > 1 else None
    return best_L, best_r, margin


def trace(tracker, ticker, window, maxlag, raw_map=None):
    rows = load_series(tracker, ticker)
    if not rows:
        sys.exit(f"ERROR: no rows for {ticker} in {tracker}")

    # ---- FORMULA-CACHE GUARD (added 2026-07-27) --------------------------
    # Return+5d / Return+10d / Was-Right-5d are FORMULAS. openpyxl reads their
    # CACHED values, and any openpyxl save blanks that cache — which the daily
    # runner now does every session when it embeds the Monitor Strip sheet.
    #
    # DELIBERATELY A WARNING, NOT A REFUSAL — and the distinction is the point.
    # h4_dq_threshold.py hard-refuses because its ENTIRE verdict rests on those
    # cached columns; run blind it printed "STAYS DEMOTED" on zero evidence.
    # This tool is different: the G1 criterion is the TABLE READ over
    # Date | Sig | Conf | Trail. Confidence is a raw cell value and the
    # trailing move is computed from the Price columns, so NEITHER touches the
    # cache. The acceptance read stays valid; only the context columns degrade.
    # Refusing here would block a sound read — so warn precisely and continue.
    cache_blank = bool(rows) and not any((x.get("right5") or "").strip() for x in rows)
    if cache_blank:
        print("\n" + "!" * 78)
        print("WARNING — FORMULA CACHE IS BLANK for this tracker.")
        print(f"  0 of {len(rows)} {ticker} rows carry a cached Was-Right-5d value.")
        print("  DEGRADED (display only): the +5d, +10d and R5 columns will read")
        print("  '—' throughout, and the RETIRED band-calibration block will show")
        print("  zero counts. Do not read anything into either.")
        print("  UNAFFECTED BY THE BLANK CACHE: Date | Sig | Conf | Trail — the")
        print("  columns the G1 table read is scored on. THE ACCEPTANCE READ IS VALID.")
        print("  AMENDED 2026-08-21: this block previously said Conf was 'a raw value'.")
        print("  It is a SCALED cell value (fraction x 100), and the scaling carried a")
        print("  truncation defect until 2026-08-21 — see conf_pct(). 'Unaffected by")
        print("  the blank cache' is not the same claim as 'exact', and stating the")
        print("  stronger one is how the defect survived unread.")
        print("  CAUSE: openpyxl saves clear cached formula values; the daily")
        print("  runner writes this workbook every session.")
        print("  FIX: point --tracker at the MASTER (logs\\claude_equity_bot_tracker")
        print("  .xlsx), which Excel keeps calculated, or open the report copy in")
        print("  Excel once to refresh, then re-run.")
        print("!" * 78)

    # The OPERATIVE value is kept on every row BEFORE any raw override, so the
    # two channels can be differenced later. Without this the tool overwrote the
    # only copy of the post-damping number and the censoring was invisible.
    for x in rows:
        x["conf_op"] = x["conf"]

    n_raw = 0
    if raw_map is not None:  # {} still prints the 0-override audit line
        for x in rows:
            v = raw_map.get((x["date"], ticker.upper()))
            if v is not None:
                x["conf"] = v
                n_raw += 1
        print(f"   [raw-from-logs] {n_raw} of {len(rows)} rows use log RAW "
              f"confidence; remainder keep tracker values (raw == operative by "
              f"construction on pre-deploy rows)")
        # AMENDED 2026-08-21: the word previously used here was "exact". It was
        # not: the tracker path scaled a fraction and the display truncated it,
        # so the fallback rows could read one point low while the overridden
        # rows read exactly -- which is precisely the asymmetry that made the
        # operative and raw exhibits disagree on GM 8/17 and 8/20. Fixed in
        # conf_pct(); the claim is now narrowed to what it can support.
    confs = [x["conf"] for x in rows]
    prices = [x["p0"] for x in rows]
    # trailing window-day move from the signal-capture price series.
    # AMENDED 2026-10-22 (DP-3C-ax, ruled by Rob 2026-09-30): the window is
    # `window` NYSE SESSIONS, not `window` tracker rows. The base is Price at
    # Signal on shift_sessions(d, -window); if the ticker has no row on that
    # session (bot-absent day or dropout) the row is NOT EVALUABLE and its
    # trail stays None (printed as a dash). Before this, a row after a missed
    # session got a 6- or 7-session window, which reaches THETA more easily.
    trail = [None] * len(rows)
    not_evaluable = []
    try:
        import trading_calendar as _tc
    except ImportError:                                 # pragma: no cover
        _tc = None
    by_date = {x["date"]: k for k, x in enumerate(rows)}
    for i in range(len(rows)):
        if prices[i] is None:
            continue
        if _tc is not None:
            base = _tc.shift_sessions(rows[i]["date"], -window)
            j = by_date.get(base)
            if j is None:
                if rows[i]["date"] >= rows[0]["date"] and i >= window:
                    not_evaluable.append(rows[i]["date"])
                continue
        else:                                           # pragma: no cover
            j = i - window if i >= window else None
            if j is None:
                continue
        if prices[j]:
            trail[i] = prices[i] / prices[j] - 1.0
    if not_evaluable:
        print(f"   [DP-3C-ax] {len(not_evaluable)} row(s) NOT EVALUABLE (no row on the base "
              f"session): " + ", ".join(d.isoformat() for d in not_evaluable[-8:])
              + (" ..." if len(not_evaluable) > 8 else ""))

    # ---- per-cohort trace table ----
    print("\n" + "=" * 78)
    print(f"H1 LAG TRACE — {ticker}  (window={window}d, source: {os.path.basename(tracker)})")
    print("=" * 78)
    hdr = f"{'Date':<12}{'Sig':<6}{'Conf':>6}{'Trail'+str(window)+'d':>9}{'+5d':>9}{'+10d':>9}{'R5':>5}"
    print(hdr)
    print("-" * 78)
    for i, x in enumerate(rows):
        print(f"{x['date'].isoformat():<12}{x['signal']:<6}"
              f"{(str(round(x['conf']))+'%') if x['conf'] is not None else '—':>6}"
              f"{pct(trail[i]):>9}{pct(x['r5'], plus=True):>9}{pct(x['r10'], plus=True):>9}"
              f"{(x['right5'] or '—'):>5}")

    # ---- lag estimate: corr(conf[t], trail[t-L]) over L = 0..maxlag ----
    print("\nLAG SCAN — corr(confidence[t], trailing-move[t-L])  "
          "(positive = confidence tracks the move from L sessions ago):")
    scan = []
    for L in range(0, maxlag + 1):
        r = pearson(confs, trail) if L == 0 else pearson(confs[L:], trail[:-L])
        scan.append((L, r))
        print(f"   L={L} session(s): r = {r:+.3f}" if r is not None
              else f"   L={L} session(s): r = n/a (insufficient overlap)")
    # The lag is the L with the most POSITIVE correlation — i.e. how many
    # sessions late confidence catches up to the move. (argmax |r| would be
    # wrong: a NEGATIVE r at L=0 is the lag symptom, not contemporaneity.)
    best_L, best_r, margin = best_of(scan)
    if best_L is not None:
        print(f"\n   >> Estimated update lag = {best_L} session(s)  "
              f"(peak positive r = {best_r:+.3f})")
        print("   0-1 = confidence tracks the move promptly; "
              "3-5 = the Phase 2 lag (catches up late).")
        if scan[0][1] is not None and scan[0][1] < 0:
            print(f"   (r at L=0 is {scan[0][1]:+.3f} — negative-at-0 flipping "
                  f"positive at L={best_L} is the lag signature: confidence sat "
                  "high through the recent adverse move.)")

    # ---- HOW MUCH OF A PEAK IS THIS? (added 2026-09-17) -------------------
    # A bare argmax hides two failure modes that this series has BOTH of:
    #   (a) a knife-edge peak, where the reported lag turns on a margin smaller
    #       than the noise in r; and
    #   (b) a FLAT surface, where every L scores within a hair of every other
    #       and the argmax is arbitrary. GM's operative scan runs +0.420..+0.453
    #       across L = 0..5; reporting "lag = 1" off that spread is false
    #       precision, not a measurement.
    # Reported, not ruled. G1's bar is the episode-response table and does not
    # move on any of this.
    rs = [r for _, r in scan if r is not None]
    spread = (max(rs) - min(rs)) if len(rs) > 1 else None
    if margin is not None:
        _sp = "n/a" if spread is None else f"{spread:.3f}"
        print(f"   peak margin over the runner-up: {margin:+.3f}   "
              f"surface spread (max-min over L): {_sp}")
        if spread is not None and spread < 0.10:
            print("   ** FLAT SURFACE (spread < 0.10) — the argmax is arbitrary "
                  "at this spread; read the scan, not the point estimate.")
        elif margin < 0.05:
            print("   ** KNIFE-EDGE (margin < 0.05) — the reported lag would "
                  "flip on a change smaller than the estimator's own noise.")

    # ---- FLOOR CENSORING AND THE SENSITIVITY IT DRIVES --------------------
    # Rows where the operative channel was clamped by the damper carry LESS
    # information than the model produced, and they are concentrated on exactly
    # the rows H1 is about (the response to an adverse move). Difference the two
    # channels, then re-run the SAME estimator without those rows.
    cens_ix = [i for i, x in enumerate(rows)
               if x.get("conf_op") is not None and x["conf"] is not None
               and round(x["conf_op"]) != round(x["conf"])]
    censored = [rows[i] for i in cens_ix]
    sens = None
    if censored:
        keep = [i for i in range(len(rows)) if i not in set(cens_ix)]
        s_conf = [rows[i]["conf"] for i in keep]
        s_trail = [trail[i] for i in keep]
        s_scan = lag_scan_of(s_conf, s_trail, maxlag)
        s_L, s_r, _ = best_of(s_scan)
        o_scan = lag_scan_of([x["conf_op"] for x in rows], trail, maxlag)
        o_L, o_r, _ = best_of(o_scan)
        sens = dict(n=len(censored), drop_L=s_L, drop_r=s_r,
                    op_L=o_L, op_r=o_r, op_scan=o_scan,
                    dates=[x["date"].isoformat() for x in censored],
                    deltas=[round(x["conf_op"]) - round(x["conf"]) for x in censored])
        print(f"\n   FLOOR CENSORING: {len(censored)} row(s) where operative != raw "
              f"({', '.join(sens['dates'])})")
        print(f"     lag on this channel        = {best_L}")
        print(f"     lag on the OTHER channel   = {o_L}"
              + ("   ** THE TWO CHANNELS DISAGREE" if o_L != best_L else ""))
        print(f"     lag with those rows DROPPED = {s_L}"
              + ("   ** the censored rows decide the estimate" if s_L != best_L else ""))

    # ---- DAMPER-BASIS RECONCILIATION --------------------------------------
    # The exhibit's Trail column and the trail THETA damps on are different
    # measurements (see the basis footnote). This block makes the CONSEQUENCE
    # visible instead of leaving it as prose: for every row this basis calls a
    # material adverse move, did damping actually fire? A row at the floor is
    # INDETERMINATE and is never counted as agreement.
    # BOTH DIRECTIONS, not one (extended 2026-09-21). The first version asked
    # only "this basis calls it material -- did the damper fire?". GM 2026-09-21
    # is the OTHER error: the damper fired (raw 38 -> op 37) on a run-basis
    # -5.69%, while this basis reads -3.14% and sees no qualifying move at all.
    # A one-directional check would have printed an empty table on the session
    # that produced the project's first GM test case. The 2x2 is the finding.
    recon = None
    if THETA_PCT is not None and raw_map is not None:
        items, extra, fired, missed, indet = [], [], 0, 0, 0
        for i, x in enumerate(rows):
            raw_v = None if x["conf"] is None else round(x["conf"])
            op_v = None if x.get("conf_op") is None else round(x["conf_op"])
            damped = (raw_v is not None and op_v is not None and raw_v != op_v)
            qualifies = (trail[i] is not None and trail[i] * 100.0 <= -THETA_PCT)
            if qualifies:
                if raw_v is None or op_v is None:
                    state = "UNREADABLE"
                elif damped:
                    state, fired = "DAMPED", fired + 1
                elif FLOOR_PTS is not None and raw_v <= FLOOR_PTS:
                    state, indet = f"INDETERMINATE (at FLOOR={FLOOR_PTS})", indet + 1
                else:
                    state, missed = "NOT DAMPED", missed + 1
                items.append((x["date"].isoformat(), trail[i] * 100.0, raw_v, op_v, state))
            elif damped:
                extra.append((x["date"].isoformat(),
                              None if trail[i] is None else trail[i] * 100.0,
                              raw_v, op_v, "DAMPED, NOT MATERIAL ON THIS BASIS"))
        if items or extra:
            recon = dict(items=items, extra=extra, fired=fired, missed=missed,
                         indet=indet, theta=THETA_PCT, floor=FLOOR_PTS, src=DAMP_SRC)
            print(f"\n   DAMPER-BASIS RECONCILIATION (THETA={THETA_PCT}% from {DAMP_SRC})")
            for d, tv, rv, ov, stt in items:
                print(f"     {d}  trail {tv:+7.2f}%  raw {rv}  op {ov}   {stt}")
            print(f"     -> {len(items)} qualifying row(s) on THIS basis: "
                  f"damped {fired}, NOT damped {missed}, indeterminate {indet}")
            if missed:
                print("     ** A row this basis calls material and the damper did not "
                      "touch is the off-by-one window showing up as a DECISION, not "
                      "just a label. Reported; no threshold moves.")
            for d, tv, rv, ov, stt in extra:
                tvs = "   n/a  " if tv is None else f"{tv:+7.2f}%"
                print(f"     {d}  trail {tvs}  raw {rv}  op {ov}   {stt}")
            if extra:
                print(f"     ** {len(extra)} row(s) DAMPED that this basis does not call "
                      "material -- the mirror error, and the one a qualifying-rows-only "
                      "table cannot see. Reported; no threshold moves.")

    # ---- contemporaneous vs predictive correlations ----
    r_now = pearson(confs, trail)
    r_fwd = pearson(confs, [x["r5"] for x in rows])
    print(f"\n   corr(conf, trailing move)  = {r_now:+.3f}" if r_now is not None
          else "   corr(conf, trailing move)  = n/a")
    print(f"   corr(conf, forward +5d)    = {r_fwd:+.3f}" if r_fwd is not None
          else "   corr(conf, forward +5d)    = n/a")

    # ---- forward +10d arc ----
    arc = [x["r10"] for x in rows if x["r10"] is not None]
    if arc:
        arc_str = " -> ".join(f"{v*100:.2f}" for v in arc)
        print(f"\n+10d ARC ({ticker}): {arc_str}")
        print(f"   first {arc[0]*100:+.2f}%  ->  last {arc[-1]*100:+.2f}%  "
              f"({'self-corrected upward' if arc[-1] > arc[0] else 'no net recovery'})")

    # ---- calibration guardrail (RETIRED — historical context only) ----
    # Q1-R was DIAGNOSED and CLOSED 2026-07-13: the 50-59 vs 60-69 inversion was
    # a go-live calibration IMPROVEMENT (the 60-69 band gained +15.4pt), not a
    # guardrail failure. The guardrail is RETIRED and T2 is retired with it.
    # T3 forbids any decision or design relying on confidence-band ordering, so
    # this block is printed as HISTORY ONLY and carries no PASS/FAIL meaning.
    print("\nCALIBRATION GUARDRAIL — RETIRED (Q1-R closed 2026-07-13) — "
          "historical context only; T3: no band-ordering reliance")
    agg = band_calibration(tracker)
    lead = max(agg, key=lambda b: (agg[b][0] / agg[b][1]) if agg[b][1] else -1)
    for b in ("40-49", "50-59", "60-69"):
        h, n = agg[b]
        rate = f"{h/n*100:.1f}%" if n else "—"
        mark = "  <-- leads" if b == lead else ""
        print(f"   {b}: {h}/{n} = {rate}{mark}")
    ok_cal = lead == "50-59"
    print(f"   (band ordering shown for the record: {lead} leads this window. "
          f"NOT a pass/fail signal — the guardrail is retired.)")
    print("   NOTE: this window is the run's --since/--until slice, so these "
          "rates will differ from the live 6/15+ figures in the notes.")

    # ---- success metric ----
    print("\n" + "-" * 78)
    print("SUCCESS METRIC (Phase 3-A vs this Phase 2 baseline)")
    print("-" * 78)
    print(f"   • Update lag shrinks from the Phase 2 ~3-5 sessions toward 0-1")
    print(f"     (this run's estimate: {best_L if best_L is not None else 'n/a'} session(s)).")
    print(f"   • corr(conf, trailing move) rises (confidence reacts to the recent")
    print(f"     move; this run: {r_now:+.3f})." if r_now is not None
          else "     move).")
    # DP-3C-aj (2026-09-16; review 2026-09-08 §6; Discovery D2). Tracking the
    # trailing move is NOT success on its own: in a universe that mean-reverts
    # at 10-20 sessions, a confidence that follows the trailing move more
    # closely is MORE anti-predictive. This block used to print the trailing
    # correlation as a pass criterion two lines below a negative forward
    # correlation and say nothing about it. The forward sign now travels with
    # it, and a non-positive forward correlation is named. No bar moves: G1 is
    # the episode-response table, not this block.
    if r_fwd is None:
        print("   • corr(conf, forward +5d) = n/a - the trailing figure above cannot")
        print("     be read as success without its forward sign.")
    else:
        print(f"   • corr(conf, forward +5d) must NOT be negative for the above to")
        print(f"     count as success. This run: {r_fwd:+.3f}"
              + ("  <-- NEGATIVE: tracking the trailing move is not helping the"
                 if r_fwd < 0 else "  (non-negative)"))
        if r_fwd < 0:
            print("     forward read here. Directional diagnostic only (small n,")
            print("     overlapping windows); see DP-3C-w and Discovery 2026-09-16 §7.")
    print(f"   • (Retired criterion, shown for continuity only: the 50-59 band "
          f"{'leads' if ok_cal else 'does not lead'} in this window.)")
    print(f"   • {ticker}-type names no longer hold high confidence through a")
    print(f"     multi-session adverse move.")
    # FIXED 2026-09-16: said "~19 cohorts", a Phase 2 figure, on a series that
    # now runs to 80+ rows. The count is the rows this run actually traced.
    print(f"\n   NOTE: per-ticker n is small ({len(rows)} rows, overlapping 5-session")
    print("   windows) — read the trace table as")
    print("   the primary evidence and the correlations as directional diagnostics.")

    return dict(best_L=best_L, r_now=r_now, r_fwd=r_fwd, ok_cal=ok_cal,
                cache_blank=cache_blank,
                raw_rows=n_raw, raw_used=(raw_map is not None),
                rows=rows, trail=trail, arc=arc, agg=agg,
                scan=scan, margin=margin, spread=spread,
                sens=sens, recon=recon)


def write_md(res, ticker, window, tracker, out_dir, suffix=""):
    rows, trail = res["rows"], res["trail"]

    # corr(conf, +5d) is None whenever the Return+5d formula cache is blank.
    # PRE-EXISTING BUG, found 2026-07-27: this used a bare {:+.3f} format, so a
    # blank cache raised TypeError HERE — after the full console trace had
    # already printed and looked correct. The exhibit was then never written and
    # the PREVIOUS run's .md was left on disk looking current. Since that file
    # is what the notes cite as G1 evidence, a crashed run could be mistaken for
    # a completed one. Format defensively and always write the exhibit.
    def _r(v):
        return "—" if v is None else f"{v:+.3f}"

    # PROVENANCE, corrected 2026-08-26. Under --raw-from-logs the Conf
    # column is the RAW pre-damping channel, which is NOT in the tracker --
    # the tracker stores the OPERATIVE value. Crediting only the workbook
    # made the WMT exhibit look wrong against its own stated source on
    # every damped row (08-20..08-24 printed 42/38/38 against a stored
    # 0.35, the D1 floor). Say where each column came from.
    if res.get("raw_used"):
        src = (f"*Prices and outcomes: `{os.path.basename(tracker)}`. "
               f"**`Conf` is the RAW pre-damping channel, parsed from the "
               f"session logs** ({res.get('raw_rows', 0)} row(s) overridden; "
               f"the rest fall back to the tracker's operative value, which "
               f"equals raw wherever damping was inactive). The tracker "
               f"itself stores OPERATIVE confidence and will differ from "
               f"this column on any damped row.* · window {window}d · "
               f"generated {dt.datetime.now():%Y-%m-%d %H:%M}.")
    else:
        src = (f"*Source: `{os.path.basename(tracker)}` (`Conf` is the "
               f"OPERATIVE, post-damping channel) · window {window}d · "
               f"generated {dt.datetime.now():%Y-%m-%d %H:%M}.*")
    lines = [f"# H1 Lag Trace — {ticker}", src, "",
             f"**Estimated update lag: {res['best_L']} session(s)** · "
             f"corr(conf, trailing move) = {_r(res['r_now'])} · "
             f"corr(conf, +5d) = {_r(res['r_fwd'])}", "",
             f"| Date | Sig | Conf | Trail{window}d | +5d | +10d | R5 |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    if res.get("cache_blank"):
        lines[4:4] = [
            "> **FORMULA CACHE WAS BLANK when this exhibit was generated.** The "
            "`+5d`, `+10d` and `R5` columns below are EMPTY FOR THAT REASON — not "
            "because the cohorts are unresolved. The retired band-calibration "
            "block likewise shows zero counts. **The `Conf` and `Trail` columns — "
            "the ones the G1 table read is scored on — are unaffected**, being a "
            "scaled cell value and a Price-column computation respectively. "
            "Regenerate against the master tracker for a complete exhibit.", ""]
    # BASIS DISCLOSURE, added 2026-08-21. The Trail column and the run's own
    # H1[trail5d=...] / D[trail=...] tags are TWO DIFFERENT MEASUREMENTS and the
    # exhibit never said so. They differ on two axes: this column walks back
    # `window` TRACKER ROWS (so a session a ticker missed is skipped, not
    # counted) and prices off `Price at Signal` (a ~09:3x quote), while the run
    # computes over consecutive MARKET sessions off CLOSES. On 2026-08-21 the two
    # gave GM OPPOSITE SIGNS -- this exhibit -0.31%, the run +2.75% -- because
    # GM's missing 2026-08-18 row moved this column's t-5 anchor from 8/14 to
    # 8/13. Both are correct under their own definition; neither was labelled.
    # It matters because monitor_strip's G1 episode detector uses THIS basis
    # while importing THETA from the damping engine, which uses the other.
    lines[4:4] = [
        "> **TRAIL BASIS — THREE differences, not two.** `Trail" + str(window)
        + "d` walks back " + str(window)
        + " **tracker rows** (a session this ticker missed is skipped, not counted) "
          "and prices off **Price at Signal**, a ~09:3x quote, ending at the "
          "most recent row. The run's own `H1[trail5d=…]` / `D[trail=…]` tags "
          "price off **closes** — but their window is **shifted one session "
          "forward and its right edge is a live intraday print**, because "
          "`schwab_client.get_price_history()` dates candles in local time and "
          "admits the in-progress session (measured every run by "
          "`trail_basis_audit.py`; diagnosis in "
          "`H1_Window_OffByOne_Defect_2026-08-26.md`). **That third term is "
          "the largest.** Recorded 2026-08-21 after GM read −0.31% here "
          "against +2.75% in the run; amended 2026-08-26 after WMT read "
          "**−10.20% here against +0.78% in the run** — opposite signs, 10.98 "
          "points, on the WS2 tracer. Under the documented contract for that "
          "function, **this column is the closer of the two**; the run's "
          "figure is the one that is wrong, and THETA damping uses it.",
        "> **AMENDED 2026-09-25 (DP-3C-an).** The paragraph above is true of "
        "**D1 rows only (before 2026-09-01)**. From D2 (H1-WINDOW, ruled and "
        "applied 2026-08-31; audited every run by `trail_basis_audit.py`) the "
        "run's window is the contract window, closes c(D−5)→c(D−1), and the "
        "third term is gone. On D2 rows the two bases differ by (a) tracker rows "
        "vs market sessions and (b) this column's right edge is the signal-time "
        "quote, so it includes the session's opening move, which the run's "
        "trail ends before. **Neither is wrong on D2.** DP-3C-an rules THIS "
        "column G1's episode basis (the move as it stood when the model "
        "answered) and requires the run's basis to be reported beside it; "
        "THETA still damps on the run's.",
        "> **AMENDED 2026-10-22 (DP-3C-ax, ruled 2026-09-30).** The Trail column "
        "is now measured over **five NYSE sessions** off Price at Signal, not "
        "five tracker rows. A row whose base session has no row (a bot-absent "
        "day or a dropout) is **NOT EVALUABLE** and shows a dash.", ""]
    for i, x in enumerate(rows):
        lines.append(
            f"| {x['date'].isoformat()} | {x['signal']} | "
            f"{(str(round(x['conf']))+'%') if x['conf'] is not None else '—'} | "
            f"{pct(trail[i])} | {pct(x['r5'], plus=True)} | "
            f"{pct(x['r10'], plus=True)} | {x['right5'] or '—'} |")
    if res["arc"]:
        lines += ["", f"**+10d arc:** {' → '.join(f'{v*100:.2f}' for v in res['arc'])} "
                      f"(first {res['arc'][0]*100:+.2f}% → last {res['arc'][-1]*100:+.2f}%)"]

    # ---- LAG SURFACE (added 2026-09-17) -----------------------------------
    # The exhibit used to carry the argmax alone. The scan was printed to the
    # console and thrown away, so the ONE number that survived into the durable
    # record was the one that cannot be audited. Everything below is reporting:
    # no bar, no gate and no G1 disposition moves on any of it.
    if res.get("scan"):
        lines += ["", "## Lag surface — the scan behind the point estimate", "",
                  "*`r` = corr(confidence[t], trailing move[t−L]). The headline lag is "
                  "the argmax over L. **An argmax is only a measurement when the "
                  "surface has a peak**, so the margin to the runner-up and the "
                  "spread across the whole scan are reported beside it.*", "",
                  "| L (sessions) | r |", "| --- | --- |"]
        for L, r in res["scan"]:
            star = "  ← argmax" if L == res.get("best_L") else ""
            lines.append(f"| {L} | {_r(r)}{star} |")
        _m = res.get("margin")
        _s = res.get("spread")
        lines += ["",
                  f"**Peak margin over the runner-up:** {_r(_m)} · "
                  f"**surface spread (max − min over L):** "
                  f"{'—' if _s is None else f'{_s:.3f}'}"]
        if _s is not None and _s < 0.10:
            lines += ["", "> **FLAT SURFACE — the argmax is arbitrary at this spread.** "
                          "Every lag in the scan scores within "
                          f"{_s:.3f} of every other. The headline figure above should "
                          "be read as *no lag structure is resolvable on this sample*, "
                          "not as a measured lag of "
                          f"{res.get('best_L')} session(s). Reported, not ruled."]
        elif _m is not None and _m < 0.05:
            lines += ["", "> **KNIFE-EDGE — the reported lag turns on a margin of "
                          f"{_m:.3f}.** A perturbation smaller than this estimator's own "
                          "noise flips the headline. Read the surface, not the point."]

    # ---- CHANNEL / CENSORING SENSITIVITY ----------------------------------
    sens = res.get("sens")
    if sens:
        lines += ["", "## Floor censoring — and what the estimate does without it", "",
                  f"**{sens['n']} row(s) carry a clamped operative value** "
                  f"({', '.join(sens['dates'])}), i.e. the damper removed "
                  f"{', '.join(str(d) for d in sens['deltas'])} point(s) from the "
                  "model's own number. Those rows are not incidental: they are the "
                  "rows where a multi-session adverse move was in progress, which is "
                  "precisely the event H1 is about. The same estimator, re-run three "
                  "ways:", "",
                  "| Channel / sample | estimated lag |", "| --- | --- |",
                  f"| this exhibit's channel | {res.get('best_L')} |",
                  f"| the other channel, same rows | {sens['op_L']} |",
                  f"| this channel, censored rows dropped | {sens['drop_L']} |"]
        if sens["op_L"] != res.get("best_L") or sens["drop_L"] != res.get("best_L"):
            lines += ["", "> **THE HEADLINE LAG IS NOT INVARIANT TO THE CHANNEL.** "
                          f"{sens['n']} clamped row(s) out of {len(res['rows'])} decide "
                          "it. The clamp is a risk-engine artefact, not a belief the "
                          "model expressed, so a lag estimate read off the clamped "
                          "channel is partly a measurement of `DampingConfig.FLOOR`. "
                          "**`monitor_strip` scores G1 on the operative channel while "
                          "naming this raw exhibit as the model-side channel** — that "
                          "choice is now known to change the answer and is owed a "
                          "ruling. Nothing here lowers G1's bar."]

    # ---- DAMPER-BASIS RECONCILIATION --------------------------------------
    recon = res.get("recon")
    if recon:
        lines += ["", "## Damper-basis reconciliation", "",
                  f"*Rows this exhibit's basis calls a material adverse move "
                  f"(trail ≤ −{recon['theta']}%, THETA read from `{recon['src']}`), "
                  f"against whether damping actually fired. A row already at "
                  f"FLOOR={recon['floor']} is **indeterminate** and is never scored as "
                  f"agreement.*", "",
                  "| Date | Trail | raw | op | damper |",
                  "| --- | --- | --- | --- | --- |"]
        for d, tv, rv, ov, stt in recon["items"]:
            lines.append(f"| {d} | {tv:+.2f}% | {rv} | {ov} | {stt} |")
        lines += ["",
                  f"**{len(recon['items'])} qualifying row(s): damped {recon['fired']}, "
                  f"NOT damped {recon['missed']}, indeterminate {recon['indet']}.**"]
        if recon.get("extra"):
            lines += ["", "**The mirror case — damped where this basis sees no "
                          "qualifying move:**", "",
                      "| Date | Trail | raw | op |", "| --- | --- | --- | --- |"]
            for d, tv, rv, ov, _stt in recon["extra"]:
                lines.append(f"| {d} | {'—' if tv is None else f'{tv:+.2f}%'} "
                             f"| {rv} | {ov} |")
            lines += ["", "> **The damper acted on a move this column does not see.** "
                          "A table built only from qualifying rows would be empty on "
                          "exactly these sessions, which is why both directions are "
                          "counted. Reported; no threshold, gate or n moves."]
        if recon["missed"]:
            lines += ["", "> **The two bases disagreed on a DECISION, not a label.** "
                          "Sessions this basis calls material on which the damper did "
                          "nothing. On D1 rows (before 2026-09-01) this is the "
                          "off-by-one window; on D2 rows it is the signal-time vs "
                          "prior-close difference (amended 2026-09-25, DP-3C-an). "
                          "Reported. No threshold, gate or n moves here."]
    lines += ["", "## Calibration guardrail — RETIRED (historical context only)",
              "*Q1-R closed 2026-07-13: the band inversion was a go-live calibration "
              "improvement, not a guardrail failure. The guardrail and T2 are retired; "
              "T3 forbids band-ordering reliance. Rates below are for the run's date "
              "slice and are NOT a pass/fail signal.*", ""]
    for b in ("40-49", "50-59", "60-69"):
        h, n = res["agg"][b]
        lines.append(f"- {b}: {h}/{n} = {h/n*100:.1f}%" if n else f"- {b}: —")
    path = os.path.join(out_dir, f"h1_lag_trace_{ticker}{suffix}.md")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return path


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="H1 confidence-lag trace / success metric.")
    ap.add_argument("--tracker", default="claude_equity_bot_tracker.xlsx")
    ap.add_argument("--ticker", default="WMT")
    ap.add_argument("--window", type=int, default=5, help="trailing-move window (sessions)")
    ap.add_argument("--maxlag", type=int, default=5, help="max lag to scan (sessions)")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--since", default=None,
                    help="only analyze rows on/after YYYY-MM-DD (e.g. 2026-06-15 = Phase 3-A only)")
    ap.add_argument("--until", default=None,
                    help="only analyze rows on/before YYYY-MM-DD")
    ap.add_argument("--raw-from-logs", nargs="*", default=None, metavar="LOG",
                    help="log files/globs; override tracker confidence with "
                         "the RAW (pre-damping) confidence parsed from Signal "
                         "JSON lines — the Lever-B model-side channel")
    ap.add_argument("--suffix", default="",
                    help="append to the output MD filename (e.g. _raw) so "
                         "raw-channel runs don't overwrite the operative MD")
    args = ap.parse_args(argv)
    global SINCE, UNTIL
    if args.since:
        SINCE = dt.date.fromisoformat(args.since)
    if args.until:
        UNTIL = dt.date.fromisoformat(args.until)
    if SINCE is not None or UNTIL is not None:
        print("")
        print("[DATE SLICE] analyzing " + _window_label())
        print("   (the retired band-calibration block uses this same window)")
    if not os.path.exists(args.tracker):
        sys.exit(f"ERROR: tracker not found: {args.tracker}")
    os.makedirs(args.out_dir, exist_ok=True)
    raw_map = (load_raw_conf_map(args.raw_from_logs)
               if args.raw_from_logs else None)
    res = trace(args.tracker, args.ticker, args.window, args.maxlag,
                raw_map=raw_map)
    md = write_md(res, args.ticker, args.window, args.tracker, args.out_dir,
                  suffix=args.suffix)
    print(f"\nWrote: {md}")


if __name__ == "__main__":
    main()
