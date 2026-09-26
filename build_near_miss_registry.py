#!/usr/bin/env python3
"""
build_near_miss_registry.py  —  Claude Equity Bot, Phase 3-A engineering item

Auto-generates the Near-Miss BUY registry FROM THE SIGNALS TAB, replacing the
hand-maintained "Near-Miss BUYs" sheet that drifted twice in Week 4 (mis-dated
6/2-vs-6/3 pair + missing rows). The Signals tab is the single source of truth;
this script never transcribes prices or returns by hand and never edits the
master workbook in place.

WHAT A "NEAR-MISS BUY" IS
    A row in the Signals tab whose Signal == "BUY" and whose confidence sits in
    the near-miss band [60%, 70%) — i.e. a BUY the Risk Engine rejected only
    because it fell short of the 70% threshold. These are the highest-information
    signals for the Q2 threshold-calibration question.

LOCKED vs EXTENDED
    LOCKED   = the frozen Q2 verdict cohort: near-miss BUYs dated on/before the
               lock cutoff (default 2026-06-01, the 6/1 addendum). This set is
               final and immutable; its hit rate (4/7 = 57.1%) and avg +5d
               return (-0.90%) are the basis for KEEP-70%.
    EXTENDED = running post-lock tracking (dates after the cutoff). Outcomes
               fill in over time; reported as a live corroboration set, NOT
               re-litigating the locked verdict.

HOUSE RULE (matches parse_log_to_tracker.py)
    Scripts do not mutate the master tracker. By default this tool only READS
    the master (read-only) and writes fresh, standalone artifacts. Writing the
    regenerated sheet into a *copy* of the workbook is available behind the
    explicit, off-by-default --emit-master-copy flag (the original file is never
    touched even then).

CONVENTIONS (Phase 2 locked; see Phase2_Closeout_Memo Appendix)
    +Nd  = N TRADING days, computed from a holiday-aware calendar (never
           transcribed). Outcomes use closing prices. Confidence stored as a
           fraction (0.62 == 62%). Returns stored as fractions (-0.0362).

OUTPUTS
    near_miss_registry.xlsx   regenerated sheet (15 master columns + Segment),
                              LOCKED/EXTENDED split summary (live formulas),
                              fresh KEEP-70% verdict box, provenance footer.
    near_miss_registry.md     same content as a paste-ready markdown summary.
    console digest            counts + per-segment scorecards + self-validation.

USAGE
    python build_near_miss_registry.py
    python build_near_miss_registry.py --tracker /path/to/claude_equity_bot_tracker.xlsx \
        --out-dir ./out --lock-cutoff 2026-06-01
    python build_near_miss_registry.py --emit-master-copy   # writes a *copy* of the workbook
"""

from __future__ import annotations
import argparse
import datetime as dt
import os
import shutil
import sys
from dataclasses import dataclass

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# --------------------------------------------------------------------------- #
# Configuration / conventions
# --------------------------------------------------------------------------- #

SIGNALS_SHEET = "Signals"
HEADER_ROW = 4                 # Signals tab: data begins at row 5
FIRST_DATA_ROW = 5
LAST_DATA_ROW_CAP = 100_000    # generous upper bound; we stop at first all-empty run

# Signals tab column map (1-indexed) — verified against the workbook.
COL = dict(date=1, ticker=2, account=3, signal=4, conf=5, dq=6,
           p0=7, p5=8, p10=9, p20=10, r5=11, r10=12, r20=13, right5=14, notes=15)

BAND_LOW, BAND_HIGH = 60.0, 70.0   # near-miss confidence band [60%, 70%)
BUY_LABEL = "BUY"
DEFAULT_LOCK_CUTOFF = dt.date(2026, 6, 1)   # <= cutoff -> LOCKED ; > cutoff -> EXTENDED
EXPECT_LOCKED = 7                            # frozen invariant; the locked cohort is immutable

# Frozen locked-segment baselines (immutable; used as a sanity reconciliation).
#
# ANALYST NOTE (2026-09-08): comp10 read 6 and had been WARNing against a live
#   1/7. The LOCKED POPULATION is immutable at 7 rows; its RESOLUTION was not,
#   and this baseline was captured while the seventh row was still open at
#   +10d. It has since resolved, as a miss — hit10 stayed 1 while comp10 moved
#   6 -> 7. So the invariant was asserting a denominator that was always going
#   to move, and the WARN it produced was the check catching up with reality
#   rather than catching anything.
#
#   That is not a harmless mislabel. It fires the run-level banner "one or more
#   checks WARNed — inspect before trusting the run" on an otherwise all-PASS
#   instrument, EVERY run, on a condition known to be benign. A warning channel
#   that cries wolf is worth less than no warning channel, because the operator
#   learns to skip it — and this one sits on the registry carrying the BUY
#   gate's evidence.
#
#   comp10 is now 7 and the locked cohort is FULLY RESOLVED at both horizons,
#   so every field here is finally immutable in fact and not merely in label.
#   The check itself is also rewritten below to distinguish "still resolving"
#   from "wrong", so this cannot recur if the population is ever re-cut.
LOCKED_BASELINE = dict(hit5=4, comp5=7, rate5=4 / 7, avg5=-0.0090,
                       hit10=1, comp10=7, avg10=-0.0300)
BASELINE_TOL = 0.0015

# NYSE full-closure holidays. 2026 is complete; extend when the project runs
# into 2027. Unlisted holidays would be mis-counted as trading days, so keep
# this current. Weekends are handled separately.
NYSE_HOLIDAYS: set[dt.date] = {
    dt.date(2026, 1, 1),    # New Year's Day
    dt.date(2026, 1, 19),   # MLK Jr. Day
    dt.date(2026, 2, 16),   # Washington's Birthday
    dt.date(2026, 4, 3),    # Good Friday
    dt.date(2026, 5, 25),   # Memorial Day
    dt.date(2026, 6, 19),   # Juneteenth
    dt.date(2026, 7, 3),    # Independence Day (observed; Jul 4 is a Saturday)
    dt.date(2026, 9, 7),    # Labor Day
    dt.date(2026, 11, 26),  # Thanksgiving
    dt.date(2026, 12, 25),  # Christmas Day
}

# Loosening gates for the Q2 verdict (unchanged from the worksheet).
GATE_HIT_RATE = 0.75
GATE_AVG_RETURN = 0.03


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return None


def conf_pct(v):
    """Confidence as a percentage number, accepting fraction (0.62) or pct (62)."""
    if v is None:
        return None
    return v * 100.0 if v <= 1.0 else float(v)


def in_band(v):
    p = conf_pct(v)
    return p is not None and BAND_LOW <= p < BAND_HIGH


def is_buy(v):
    return str(v).strip().upper() == BUY_LABEL


def add_trading_days(start: dt.date, n: int, holidays: set[dt.date]) -> dt.date:
    """Advance N trading days from `start` (skips weekends + listed holidays)."""
    d, added = start, 0
    while added < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            added += 1
    return d


@dataclass
class NearMiss:
    date: dt.date
    ticker: str
    account: str
    conf: float          # stored as fraction
    dq: str
    p0: float
    p5: float | None
    p10: float | None
    r5: float | None
    r10: float | None
    right5_src: str | None
    notes: str
    d5: dt.date
    d10: dt.date
    segment: str         # "LOCKED" | "EXTENDED"
    era: str = "D2"      # DP-3C-v: "D1" before 2026-09-01, "D2" from it
    flag: str = ""       # DP-3C-v: "D1-WINDOW" on the one row the fix would move


# DP-3C-v (2026-09-03), applied 2026-09-16. The H1 window fix changed what the
# model was shown from the 2026-09-01 cohort (era D2). Registries record what
# was EMITTED; rows are never added or removed on a counterfactual. The era is
# carried so "does KEEP-70 read differently either side of the fix?" can be
# asked later. It is NOT answerable now and no split reading is taken.
D2_START = dt.date(2026, 9, 1)
# The only BUY among the 60 rows the D1 defect moved: 62% as emitted, 59% on
# the corrected window (below the band floor). It STAYS, flagged.
D1_WINDOW_FLAGS = {(dt.date(2026, 8, 27), "PWR"): "D1-WINDOW"}


# --------------------------------------------------------------------------- #
# Read + filter (READ-ONLY on the source workbook)
# --------------------------------------------------------------------------- #

LIVE_KEEP70 = {}     # filled by main(); read by the writers


def live_keep70(tracker_path):
    """episodes.keep70() over the whole master (price-derived +5d)."""
    import episodes
    wb = openpyxl.load_workbook(tracker_path, data_only=True, read_only=True)
    ws = wb[SIGNALS_SHEET]
    rows, dates, blank = [], set(), 0
    for v in ws.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW_CAP,
                          min_col=1, max_col=COL["p5"], values_only=True):
        d = as_date(v[0])
        if d is None:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        dates.add(d)
        conf, p0, p5 = v[COL["conf"] - 1], v[COL["p0"] - 1], v[COL["p5"] - 1]
        ok = isinstance(p0, (int, float)) and isinstance(p5, (int, float)) and p0
        rows.append(dict(
            date=d, ticker=str(v[COL["ticker"] - 1] or "").strip().upper(),
            signal=str(v[COL["signal"] - 1] or "").strip().upper(),
            conf=(conf * 100 if isinstance(conf, (int, float)) and conf <= 1 else conf),
            ret5=((p5 - p0) / p0) if ok else None))
    wb.close()
    # DP-3C-ar (RULED 2026-09-25): run-fault dropouts bridge, never split --
    # the same set the actionable registry and the strip use.
    try:
        import signal_logs
        paths, _info = signal_logs.discover(os.path.join("logs", "signals_*.log"))
        drops = episodes.dropouts_from_logs(
            paths, present={(r["ticker"], r["date"]) for r in rows})
    except Exception:                                   # noqa: BLE001
        drops = None
    return episodes.keep70(rows, sorted(dates), dropouts=drops)


def load_near_misses(tracker_path: str, lock_cutoff: dt.date) -> list[NearMiss]:
    wb = openpyxl.load_workbook(tracker_path, data_only=True, read_only=True)
    if SIGNALS_SHEET not in wb.sheetnames:
        wb.close()
        sys.exit(f"ERROR: '{SIGNALS_SHEET}' tab not found in {tracker_path}")
    ws = wb[SIGNALS_SHEET]

    rows: list[NearMiss] = []
    blank_streak = 0
    # 2026-08-13: SINGLE PASS via iter_rows. On a read_only worksheet every
    # ws.cell() call can re-walk the sheet, so the old per-cell scan was O(rows^2)
    # and took minutes at 1,460 rows. Behaviour is identical -- same columns, same
    # blank-streak break, same order -- only the access pattern changed.
    for vals in ws.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW_CAP,
                             min_col=1, max_col=COL["notes"], values_only=True):
        def g(name):
            i = COL[name] - 1
            return vals[i] if i < len(vals) else None

        d = as_date(g("date"))
        tk = g("ticker")
        if d is None and not tk:
            blank_streak += 1
            if blank_streak >= 25:          # well past the data; stop scanning
                break
            continue
        blank_streak = 0
        if d is None:
            continue
        sig = g("signal")
        conf = g("conf")
        if not (is_buy(sig) and in_band(conf)):
            continue
        rows.append(NearMiss(
            date=d,
            ticker=str(tk).strip(),
            account=str(g("account") or "").strip(),
            conf=conf if conf <= 1.0 else conf / 100.0,
            dq=str(g("dq") or "").strip(),
            p0=g("p0"), p5=g("p5"), p10=g("p10"),
            r5=g("r5"), r10=g("r10"),
            right5_src=g("right5"),
            notes=str(g("notes") or "").strip(),
            d5=add_trading_days(d, 5, NYSE_HOLIDAYS),
            d10=add_trading_days(d, 10, NYSE_HOLIDAYS),
            segment="LOCKED" if d <= lock_cutoff else "EXTENDED",
            era="D1" if d < D2_START else "D2",
            flag=D1_WINDOW_FLAGS.get((d, str(tk).strip().upper()), ""),
        ))
    wb.close()
    rows.sort(key=lambda x: (x.date, x.ticker))
    return rows


# --------------------------------------------------------------------------- #
# Summaries (computed in Python for md/console; Excel re-derives via formulas)
# --------------------------------------------------------------------------- #

def summarize(rows: list[NearMiss], segment: str) -> dict:
    seg = [x for x in rows if x.segment == segment]
    comp5 = [x for x in seg if x.r5 is not None]
    comp10 = [x for x in seg if x.r10 is not None]
    hit5 = [x for x in comp5 if x.r5 > 0]
    hit10 = [x for x in comp10 if x.r10 > 0]
    return dict(
        n=len(seg),
        comp5=len(comp5), hit5=len(hit5),
        rate5=(len(hit5) / len(comp5)) if comp5 else None,
        avg5=(sum(x.r5 for x in comp5) / len(comp5)) if comp5 else None,
        comp10=len(comp10), hit10=len(hit10),
        rate10=(len(hit10) / len(comp10)) if comp10 else None,
        avg10=(sum(x.r10 for x in comp10) / len(comp10)) if comp10 else None,
    )


def verdict_text(locked: dict) -> tuple[str, str]:
    """Returns (headline, rationale) for the Q2 threshold decision."""
    rate_ok = (locked["rate5"] or 0) >= GATE_HIT_RATE
    avg_ok = (locked["avg5"] or -1) >= GATE_AVG_RETURN
    if rate_ok and avg_ok:
        head = "LOWER BUY threshold to 65% (both loosening gates met)"
    else:
        head = "KEEP 70% threshold"
    fails = []
    if not rate_ok:
        fails.append(f"hit rate {pct(locked['rate5'])} < {pct(GATE_HIT_RATE)} required")
    if not avg_ok:
        fails.append(f"avg +5d {pct(locked['avg5'])} < {pct(GATE_AVG_RETURN)} required")
    rationale = ("Locked 7-of-7 cohort: " + " AND ".join(fails) +
                 ". Both gates fail; extended post-lock set corroborates "
                 "(running). KEEP 70% confirmed at the 6/12 review.")
    return head, rationale


# --------------------------------------------------------------------------- #
# Formatting helpers for the console / markdown
# --------------------------------------------------------------------------- #

def pct(x, plus=False):
    if x is None:
        return "—"
    s = f"{x*100:.1f}%"
    return f"+{s}" if (plus and x >= 0) else s


def usd(x):
    return "—" if x is None else f"${x:,.2f}"


def mdrow(cells):
    return "| " + " | ".join(cells) + " |"


# --------------------------------------------------------------------------- #
# Excel writer
# --------------------------------------------------------------------------- #

HEADERS = ["Signal Date", "Ticker", "Account", "Conf %", "Data Quality",
           "Price at Signal", "+5d Date", "+10d Date", "Price +5d", "Price +10d",
           "Return +5d", "Return +10d", "Was Claude Right? (5d)",
           "Was Claude Right? (10d)", "Notes", "Segment", "H1 Era", "Flag"]
# column letters
A = {name: get_column_letter(i + 1) for i, name in enumerate(
    ["sigdate", "ticker", "acct", "conf", "dq", "p0", "d5", "d10",
     "p5", "p10", "r5", "r10", "right5", "right10", "notes", "seg", "era", "flag"])}

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
LOCK_FILL = PatternFill("solid", fgColor="DDEBF7")    # light blue
EXT_FILL = PatternFill("solid", fgColor="FFF2CC")     # light amber
LABEL_FILL = PatternFill("solid", fgColor="F2F2F2")


def write_xlsx(rows, locked, extended, out_path, tracker_path, lock_cutoff):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Near-Miss BUYs"

    def cell(r, c, val, *, bold=False, fill=None, fmt=None, align="left",
             color=None, size=10, border=True):
        cc = ws.cell(row=r, column=c, value=val)
        cc.font = Font(name="Arial", size=size, bold=bold,
                       color=color or ("FFFFFF" if fill is HEAD_FILL else "000000"))
        cc.alignment = Alignment(horizontal=align, vertical="center", wrap_text=False)
        if fill:
            cc.fill = fill
        if fmt:
            cc.number_format = fmt
        if border:
            cc.border = BORDER
        return cc

    # Title / description
    cell(1, 1, "Near-Miss BUY Signals — Threshold Calibration Cohort (auto-generated)",
         bold=True, size=12, border=False)
    cell(2, 1, "AUTO-GENERATED from the Signals tab — do not hand-edit. BUY signals "
               "rejected by the 70% threshold (60–69% confidence). Prices/returns are "
               "sourced from Signals; +Nd dates are trading-day offsets.",
         size=9, border=False)

    n_cols = len(HEADERS)
    for c in range(1, n_cols + 1):
        cell(HEADER_ROW, c, HEADERS[c - 1], bold=True, fill=HEAD_FILL,
             align="center", size=9)

    data_start = FIRST_DATA_ROW
    r = data_start
    for x in rows:
        fill = LOCK_FILL if x.segment == "LOCKED" else EXT_FILL
        cell(r, 1, x.date, fill=fill, fmt="yyyy-mm-dd", align="center")
        cell(r, 2, x.ticker, fill=fill, bold=True, align="center")
        cell(r, 3, x.account, fill=fill)
        cell(r, 4, x.conf, fill=fill, fmt="0%", align="center")
        cell(r, 5, x.dq, fill=fill, align="center")
        cell(r, 6, x.p0, fill=fill, fmt="$#,##0.00", align="right")
        cell(r, 7, x.d5, fill=fill, fmt="yyyy-mm-dd", align="center")
        cell(r, 8, x.d10, fill=fill, fmt="yyyy-mm-dd", align="center")
        cell(r, 9, x.p5, fill=fill, fmt="$#,##0.00", align="right")
        cell(r, 10, x.p10, fill=fill, fmt="$#,##0.00", align="right")
        # Returns & rightness as LIVE formulas over the pulled prices.
        cell(r, 11, f'=IF({A["p5"]}{r}<>"",{A["p5"]}{r}/{A["p0"]}{r}-1,"")',
             fill=fill, fmt="0.0%;[Red]-0.0%", align="right")
        cell(r, 12, f'=IF({A["p10"]}{r}<>"",{A["p10"]}{r}/{A["p0"]}{r}-1,"")',
             fill=fill, fmt="0.0%;[Red]-0.0%", align="right")
        cell(r, 13, f'=IF({A["r5"]}{r}<>"",IF({A["r5"]}{r}>0,"YES","NO"),"")',
             fill=fill, align="center")
        cell(r, 14, f'=IF({A["r10"]}{r}<>"",IF({A["r10"]}{r}>0,"YES","NO"),"")',
             fill=fill, align="center")
        cell(r, 15, x.notes, fill=fill)
        cell(r, 16, x.segment, fill=fill, align="center", size=9)
        cell(r, 17, x.era, fill=fill, align="center", size=9)
        cell(r, 18, x.flag, fill=fill, align="center", size=9, bold=bool(x.flag))
        r += 1
    data_end = r - 1

    # ----- Summary blocks (live formulas keyed off the Segment column) ----- #
    segP = f'{A["seg"]}{data_start}:{A["seg"]}{data_end}'
    p5R = f'{A["p5"]}{data_start}:{A["p5"]}{data_end}'
    p10R = f'{A["p10"]}{data_start}:{A["p10"]}{data_end}'
    r5R = f'{A["r5"]}{data_start}:{A["r5"]}{data_end}'
    r10R = f'{A["r10"]}{data_start}:{A["r10"]}{data_end}'
    m5R = f'{A["right5"]}{data_start}:{A["right5"]}{data_end}'
    m10R = f'{A["right10"]}{data_start}:{A["right10"]}{data_end}'

    def summary_block(start_row, label, seg, sub):
        cell(start_row, 1, label, bold=True, fill=LABEL_FILL, size=10)
        cell(start_row, 2, sub, size=9, color="808080", border=False)
        defs = [
            ("Near-miss BUYs (n)", f'=COUNTIF({segP},"{seg}")', "0"),
            ("Completed +5d", f'=COUNTIFS({segP},"{seg}",{p5R},"<>")', "0"),
            ("Hit count (+5d > 0)", f'=COUNTIFS({segP},"{seg}",{m5R},"YES")', "0"),
            ("Hit rate +5d",
             f'=IFERROR(COUNTIFS({segP},"{seg}",{m5R},"YES")'
             f'/COUNTIFS({segP},"{seg}",{p5R},"<>"),"—")', "0.0%"),
            ("Avg +5d return",
             f'=IFERROR(AVERAGEIFS({r5R},{segP},"{seg}",{p5R},"<>"),"—")',
             "0.0%;[Red]-0.0%"),
            ("Completed +10d", f'=COUNTIFS({segP},"{seg}",{p10R},"<>")', "0"),
            ("Hit count (+10d > 0)", f'=COUNTIFS({segP},"{seg}",{m10R},"YES")', "0"),
            ("Hit rate +10d",
             f'=IFERROR(COUNTIFS({segP},"{seg}",{m10R},"YES")'
             f'/COUNTIFS({segP},"{seg}",{p10R},"<>"),"—")', "0.0%"),
            ("Avg +10d return",
             f'=IFERROR(AVERAGEIFS({r10R},{segP},"{seg}",{p10R},"<>"),"—")',
             "0.0%;[Red]-0.0%"),
        ]
        rr = start_row + 1
        for name, formula, fmt in defs:
            cell(rr, 1, name, size=9)
            cell(rr, 2, formula, fmt=fmt, align="right", size=9)
            rr += 1
        return rr

    rr = data_end + 2
    rr = summary_block(rr, "LOCKED — final 7-of-7 verdict cohort",
                       "LOCKED", f"signals on/before {lock_cutoff:%Y-%m-%d} · immutable")
    rr += 1
    rr = summary_block(rr, "EXTENDED — running post-lock tracking",
                       "EXTENDED", f"signals after {lock_cutoff:%Y-%m-%d} · fills over time")
    rr += 1
    cell(rr, 1, "TOTAL near-miss BUYs", bold=True, size=9)
    cell(rr, 2, f'=COUNTA({A["sigdate"]}{data_start}:{A["sigdate"]}{data_end})',
         fmt="0", align="right", bold=True, size=9)
    rr += 2

    # ----- LIVE KEEP-70 on the ruled basis (DP-3C-y), added 2026-09-16 ----- #
    k70 = LIVE_KEEP70.get("k")
    if k70:
        cell(rr, 1, "LIVE KEEP-70 — DP-3C-y ruled basis (EPISODE, opening row)",
             bold=True, fill=LABEL_FILL, size=10)
        rr += 1
        for name, val in [
            ("EPISODE basis — rejected BUYs that paid",
             f"{k70['ep_hit']}/{k70['ep_n']} = {k70['ep_rate']:.2f}%" if k70["ep_n"] else "—"),
            ("Bar", "≤ 50.0% supports keeping 70"),
            ("State", k70["verdict"] + (f" — margin {k70['margin_pt']:+.2f}pt"
                                        if k70.get("margin_pt") is not None else "")
             + (" — KNIFE-EDGE" if k70.get("knife_edge") else "")
             + " (neither state moves or certifies the gate — DP-3C-y, DP-3C-au)"),
            ("ROW basis (descriptive, never the verdict)",
             f"{k70['row_hit']}/{k70['row_n']} = {k70['row_rate']:.2f}%" if k70["row_n"] else "—"),
        ]:
            cell(rr, 1, name, size=9)
            cell(rr, 2, val, size=9, bold=name == "State")
            rr += 1
        rr += 1

    # ----- Verdict box (resolved) ----- #
    head, rationale = verdict_text(locked)
    cell(rr, 1, "VERDICT — RESOLVED 2026-06-12 (Phase 2 close)", bold=True,
         fill=LABEL_FILL, size=10)
    rr += 1
    cell(rr, 1, f"Decision: {head}", bold=True, color="1F4E78", size=10, border=False)
    rr += 1
    cell(rr, 1, rationale, size=9, border=False)
    rr += 1
    cell(rr, 1, f"Loosening gates: hit rate ≥ {pct(GATE_HIT_RATE)} AND avg +5d "
                f"≥ {pct(GATE_AVG_RETURN)} → lower to 65%. Locked cohort "
                f"{pct(locked['rate5'])} / {pct(locked['avg5'], plus=True)} fails both.",
         size=9, color="808080", border=False)
    rr += 2

    # ----- Provenance footer ----- #
    cell(rr, 1, f"Source: {os.path.basename(tracker_path)} · Signals tab · "
                f"generated {dt.datetime.now():%Y-%m-%d %H:%M} · "
                f"near-miss band [{int(BAND_LOW)}%, {int(BAND_HIGH)}%) · "
                f"+Nd = trading days (weekends + NYSE holidays excluded).",
         size=8, color="808080", border=False)

    # column widths
    widths = [12, 8, 11, 7, 9, 13, 12, 12, 11, 11, 11, 11, 14, 14, 30, 10, 8, 12]
    for i, w in enumerate(widths):
        ws.column_dimensions[get_column_letter(i + 1)].width = w
    ws.freeze_panes = "A5"

    wb.save(out_path)
    return data_start, data_end


# --------------------------------------------------------------------------- #
# Markdown writer
# --------------------------------------------------------------------------- #

def write_markdown(rows, locked, extended, md_path, tracker_path, lock_cutoff):
    def seg_table(seg):
        out = [mdrow(["Signal Date", "Ticker", "Acct", "Conf", "DQ",
                      "Price", "+5d Date", "+5d Ret", "Right 5d",
                      "+10d Date", "+10d Ret", "Right 10d"]),
               mdrow(["---"] * 12)]
        for x in [r for r in rows if r.segment == seg]:
            out.append(mdrow([
                f"{x.date:%Y-%m-%d}", x.ticker, x.account, pct(x.conf), x.dq,
                usd(x.p0), f"{x.d5:%Y-%m-%d}",
                pct(x.r5, plus=True) if x.r5 is not None else "pending",
                ("YES" if (x.r5 or 0) > 0 else "NO") if x.r5 is not None else "—",
                f"{x.d10:%Y-%m-%d}",
                pct(x.r10, plus=True) if x.r10 is not None else "pending",
                ("YES" if (x.r10 or 0) > 0 else "NO") if x.r10 is not None else "—",
            ]))
        return "\n".join(out)

    def scorecard(s):
        return (f"- n = **{s['n']}** · completed +5d = {s['comp5']} · "
                f"hit +5d = **{s['hit5']}/{s['comp5']}** "
                f"({pct(s['rate5'])}) · avg +5d = **{pct(s['avg5'], plus=True)}**\n"
                f"- completed +10d = {s['comp10']} · hit +10d = "
                f"**{s['hit10']}/{s['comp10']}** ({pct(s['rate10'])}) · "
                f"avg +10d = **{pct(s['avg10'], plus=True)}**")

    head, rationale = verdict_text(locked)
    total = len(rows)
    k70 = LIVE_KEEP70.get("k")
    live_md = ""
    if k70 and k70["ep_n"]:
        live_md = (
            "## LIVE KEEP-70 — DP-3C-y ruled basis\n\n"
            f"- **EPISODE basis (opening row): {k70['ep_hit']}/{k70['ep_n']} = "
            f"{k70['ep_rate']:.2f}% → {k70['verdict']}** against `≤ 50.0% supports keeping 70`"
            + (f" — margin **{k70['margin_pt']:+.2f}pt**" if k70.get("margin_pt") is not None else "")
            + (f"; next paying episode → {k70['after_hit']}, next miss → {k70['after_miss']}"
               if k70.get("after_hit") else "")
            + (" — **KNIFE-EDGE**" if k70.get("knife_edge") else "") + "\n"
            f"- ROW basis (descriptive, never the verdict): {k70['row_hit']}/{k70['row_n']} = "
            f"{k70['row_rate']:.2f}%\n"
            f"- {k70['episodes']} episodes from {k70['rows']} rows (DP-3C-m over consecutive cohorts, DP-3C-ab)\n"
            "- A NOT SUPPORTED reading does not move the gate, and a SUPPORTED reading does "
            "not certify it (DP-3C-y; symmetry ruled DP-3C-au, 2026-09-25).\n\n")
    flagged = [x for x in rows if x.flag]
    era_md = ("*H1 era (DP-3C-v): D1 rows before 2026-09-01, D2 from it. Flagged: "
              + (", ".join(f"{x.ticker} {x.date} `{x.flag}`" for x in flagged) or "none")
              + ". Registries record what was emitted; no split reading is taken.*\n\n")
    md = f"""# Near-Miss BUY Registry — auto-generated

*Source: `{os.path.basename(tracker_path)}` · Signals tab · generated \
{dt.datetime.now():%Y-%m-%d %H:%M}. Near-miss band [{int(BAND_LOW)}%, \
{int(BAND_HIGH)}%); +Nd = trading days (weekends + NYSE holidays excluded). \
Prices/returns sourced from Signals, never transcribed.*

**Total near-miss BUYs: {total}**  (LOCKED {locked['n']} + EXTENDED {extended['n']})

{live_md}{era_md}## LOCKED — final 7-of-7 verdict cohort
*Signals on/before {lock_cutoff:%Y-%m-%d}. Immutable; basis for the Q2 verdict.*

{scorecard(locked)}

{seg_table("LOCKED")}

## EXTENDED — running post-lock tracking
*Signals after {lock_cutoff:%Y-%m-%d}. Outcomes fill over time; corroboration only.*

{scorecard(extended)}

{seg_table("EXTENDED")}

## Verdict — RESOLVED 2026-06-12 (FROZEN — not a live reading)

**Decision: {head}**

> **Population:** the immutable {locked['n']}-row LOCKED cohort only, tested against
> **loosening** gates. A separate, LIVE instrument is also called KEEP-70 —
> the episode-basis reading above (DP-3C-y), also shown on the monitor strip. The two ask different questions of different populations and may point
> opposite ways without either being wrong. Quote each with its population
> attached, or neither.

{rationale}

> Loosening gates: hit rate ≥ {pct(GATE_HIT_RATE)} AND avg +5d ≥ \
{pct(GATE_AVG_RETURN)} → lower to 65%. Locked cohort \
{pct(locked['rate5'])} / {pct(locked['avg5'], plus=True)} fails both.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)


# --------------------------------------------------------------------------- #
# Console digest + self-validation
# --------------------------------------------------------------------------- #

def console_digest(rows, locked, extended, expect_locked):
    ok = True

    def line(label, val):
        print(f"  {label:<26} {val}")

    print("\n" + "=" * 64)
    print("NEAR-MISS REGISTRY — DIGEST")
    print("=" * 64)
    print(f"Total near-miss BUYs: {len(rows)}  "
          f"(LOCKED {locked['n']} + EXTENDED {extended['n']})\n")

    print("LOCKED (final 7-of-7):")
    line("hit +5d", f"{locked['hit5']}/{locked['comp5']} = {pct(locked['rate5'])}")
    line("avg +5d", pct(locked["avg5"], plus=True))
    line("hit +10d", f"{locked['hit10']}/{locked['comp10']} = {pct(locked['rate10'])}")
    line("avg +10d", pct(locked["avg10"], plus=True))

    print("\nEXTENDED (running):")
    line("hit +5d", f"{extended['hit5']}/{extended['comp5']} = {pct(extended['rate5'])}")
    line("avg +5d", pct(extended["avg5"], plus=True))
    line("completed +10d", extended["comp10"])

    # ANALYST NOTE (2026-09-08): this line used to print bare, as
    #   "VERDICT: KEEP 70% threshold", and it is the ONLY emission of the three
    #   that dropped the date. The .xlsx cell reads "VERDICT — RESOLVED
    #   2026-06-12 (Phase 2 close)" and the .md heading reads "Verdict —
    #   RESOLVED 2026-06-12"; the console said neither.
    #
    #   That matters because a SECOND, LIVE instrument is also called KEEP-70:
    #   monitor_strip's "rejected BUYs that would have paid", read against a
    #   "< 50% supports keeping 70" bar. The two ask different questions of
    #   different populations and can legitimately point opposite ways — this
    #   one tests the FROZEN 7-row locked cohort against LOOSENING gates
    #   (hit >= 75% AND avg +5d >= 3%), which is a high bar deliberately hard
    #   to clear. Printed side by side in one scan with one of them undated,
    #   they read as a contradiction that is not there. Date it, name its
    #   population, and point at the live channel.
    head, _ = verdict_text(locked)
    print(f"\nVERDICT (FROZEN, resolved 2026-06-12 at the Phase 2 close): {head}")
    print(f"  basis: the immutable {locked['n']}-row LOCKED cohort only, against "
          f"LOOSENING gates (hit >= {pct(GATE_HIT_RATE)} AND avg +5d >= "
          f"{pct(GATE_AVG_RETURN)}); reads {pct(locked['rate5'])} / "
          f"{pct(locked['avg5'], plus=True)} and fails both.")
    print("  this is NOT a live reading of the 70% gate.")
    k70 = LIVE_KEEP70.get("k")
    if k70:
        # ADDED 2026-09-16: the live channel on the RULED basis (DP-3C-y),
        # computed with episodes.keep70() -- the same function the monitor
        # strip uses, so the two cannot disagree about what an episode is.
        print("\nLIVE KEEP-70 (DP-3C-y: EPISODE basis, opening row; bar <= 50.0%):")
        line("episode basis +5d", f"{k70['ep_hit']}/{k70['ep_n']} = "
             + (f"{k70['ep_rate']:.2f}%" if k70["ep_n"] else "n/a")
             + f"  -> {k70['verdict']}"
             + (f"  margin {k70['margin_pt']:+.2f}pt" if k70.get("margin_pt") is not None else "")
             + ("  KNIFE-EDGE" if k70.get("knife_edge") else ""))
        line("row basis (descriptive)", f"{k70['row_hit']}/{k70['row_n']} = "
             + (f"{k70['row_rate']:.2f}%" if k70["row_n"] else "n/a"))
        line("episodes / rows", f"{k70['episodes']} / {k70['rows']}")
        print("  A NOT SUPPORTED reading is a fact about the gate's rejections; it is")
        print("  not a reason to move the gate (DP-3C-y), and a SUPPORTED reading is not")
        print("  a reason to keep it (DP-3C-au, 2026-09-25).")
    d1 = sum(1 for x in rows if x.era == "D1")
    print(f"\nH1 era (DP-3C-v): D1 {d1} rows, D2 {len(rows) - d1} rows; flagged: "
          + (", ".join(f"{x.ticker} {x.date} {x.flag}" for x in rows if x.flag) or "none")
          + ". No split reading is taken.")

    # ---- self-validation ----
    print("\n" + "-" * 64)
    print("SELF-VALIDATION")
    print("-" * 64)

    def check(name, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'PASS' if cond else 'WARN'}] {name}")

    check(f"LOCKED count == {expect_locked} (frozen invariant)",
          locked["n"] == expect_locked)
    check("every row has a valid +5d / +10d trading date",
          all(r.d5 and r.d10 for r in rows))
    # 2026-08-13: the former first conjunct read `all(is_buy(BUY_LABEL) for _ in
    # [0])` -- i.e. is_buy("BUY"), a literal compared against itself. It was
    # unconditionally True and tested nothing. Removed; only the band half ever
    # did work, and a reconciliation that CAN fail is added below.
    check("no signal misclassified (all in [60%,70%))",
          all(BAND_LOW <= r.conf * 100 < BAND_HIGH for r in rows))
    # 2026-08-13: right5_src is pulled from the master's own "Was Claude Right?
    # (5d)" column and was previously never read -- the sheet writes its own
    # =IF(r5>0,...) formula instead, so the master was silently NOT cross-checked.
    # This makes the comparison real. A disagreement means the master's rightness
    # column and the registry's sign test have diverged, which is a finding.
    def _mismatch(r):
        if r.r5 is None or r.right5_src is None:
            return False
        return str(r.right5_src).strip().upper() != ("YES" if r.r5 > 0 else "NO")
    bad = [f"{r.date} {r.ticker}" for r in rows if _mismatch(r)]
    check("registry sign test reconciles with the master's Right?(5d) column"
          + (f" -- MISMATCHES: {', '.join(bad)}" if bad else ""),
          not bad)
    # reconcile the immutable locked baseline
    b = LOCKED_BASELINE
    check(f"locked hit +5d == {b['hit5']}/{b['comp5']}",
          locked["hit5"] == b["hit5"] and locked["comp5"] == b["comp5"])
    check(f"locked avg +5d ≈ {pct(b['avg5'], plus=True)} (±{BASELINE_TOL})",
          locked["avg5"] is not None and abs(locked["avg5"] - b["avg5"]) <= BASELINE_TOL)
    # ANALYST NOTE (2026-09-08): the +10d reconciliation is split into the part
    #   that is TRULY frozen and the part that merely finished moving.
    #
    #   HIT COUNT is the invariant. The locked population cannot gain rows, so a
    #   resolved winner cannot become a loser: hit10 may only ever equal its
    #   baseline. If it moves, something rewrote history and that is a real WARN.
    #
    #   COMPLETION is a progress counter, not an assertion. While rows are still
    #   open at +10d, comp10 < baseline is the EXPECTED state and must not fire
    #   the run-level warning banner — that is precisely what produced a
    #   standing false WARN against the old comp10=6. It is reported, not
    #   checked. Only OVER-completion (more resolved rows than the frozen
    #   population can contain) is an error.
    check(f"locked hit +10d count == {b['hit10']} (frozen; a resolved row "
          f"cannot change outcome)", locked["hit10"] == b["hit10"])
    check(f"locked +10d completion never exceeds the frozen population "
          f"({b['comp10']})", locked["comp10"] <= b["comp10"])
    if locked["comp10"] < b["comp10"]:
        print(f"  [note] locked +10d still resolving: {locked['comp10']} of "
              f"{b['comp10']} complete — not a finding, and deliberately not a WARN")

    if not ok:
        print("\n  ⚠️  One or more checks WARNed — inspect before trusting the run.")
    else:
        print("\n  ✓ All checks passed.")
    return ok


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description="Regenerate the near-miss BUY registry "
                                             "from the Signals tab (read-only on source).")
    ap.add_argument("--tracker", default="claude_equity_bot_tracker.xlsx",
                    help="path to the tracker workbook (read-only). "
                         "Default: ./claude_equity_bot_tracker.xlsx")
    ap.add_argument("--out-dir", default=".", help="directory for outputs (default: .)")
    ap.add_argument("--lock-cutoff", default=DEFAULT_LOCK_CUTOFF.isoformat(),
                    help="YYYY-MM-DD; signals on/before -> LOCKED, after -> EXTENDED "
                         f"(default {DEFAULT_LOCK_CUTOFF.isoformat()})")
    ap.add_argument("--expect-locked", type=int, default=EXPECT_LOCKED,
                    help=f"expected LOCKED count for the invariant check "
                         f"(default {EXPECT_LOCKED}; 0 disables)")
    ap.add_argument("--emit-master-copy", action="store_true",
                    help="ALSO write a COPY of the workbook with this sheet replaced "
                         "(original is never modified). Off by default.")
    args = ap.parse_args(argv)

    if not os.path.exists(args.tracker):
        sys.exit(f"ERROR: tracker not found: {args.tracker}")
    try:
        lock_cutoff = dt.date.fromisoformat(args.lock_cutoff)
    except ValueError:
        sys.exit(f"ERROR: --lock-cutoff must be YYYY-MM-DD, got {args.lock_cutoff!r}")
    os.makedirs(args.out_dir, exist_ok=True)

    rows = load_near_misses(args.tracker, lock_cutoff)
    if not rows:
        sys.exit("ERROR: no near-miss BUYs found — check the band/label config.")
    locked = summarize(rows, "LOCKED")
    extended = summarize(rows, "EXTENDED")
    try:
        LIVE_KEEP70["k"] = live_keep70(args.tracker)
    except Exception as e:                              # noqa: BLE001
        print(f"[warn] live KEEP-70 unavailable: {e}")

    xlsx_path = os.path.join(args.out_dir, "near_miss_registry.xlsx")
    md_path = os.path.join(args.out_dir, "near_miss_registry.md")
    write_xlsx(rows, locked, extended, xlsx_path, args.tracker, lock_cutoff)
    write_markdown(rows, locked, extended, md_path, args.tracker, lock_cutoff)
    ok = console_digest(rows, locked, extended, args.expect_locked)

    print(f"\nWrote: {xlsx_path}")
    print(f"Wrote: {md_path}")

    if args.emit_master_copy:
        # Honor the house rule: never touch the original. Write to a copy.
        copy_path = os.path.join(args.out_dir, "tracker_with_registry.xlsx")
        shutil.copy2(args.tracker, copy_path)
        wb = openpyxl.load_workbook(copy_path)        # values+formulas preserved
        if "Near-Miss BUYs" in wb.sheetnames:
            del wb["Near-Miss BUYs"]
        # rebuild the sheet inside the copy by re-running the writer on a temp,
        # then importing — simplest robust path: load our fresh file and copy cells.
        src = openpyxl.load_workbook(xlsx_path)["Near-Miss BUYs"]
        dst = wb.create_sheet("Near-Miss BUYs")
        from copy import copy as _copy
        for row in src.iter_rows():
            for c in row:
                nc = dst.cell(row=c.row, column=c.column, value=c.value)
                if c.has_style:
                    # Copy style ATTRIBUTES, not the _style index. StyleArray indices
                    # point into the SOURCE workbook's number-format/font tables and
                    # scramble when reused in a different workbook; strings/objects are
                    # portable. (Symptom of the bug: price cells render as 1900 dates.)
                    nc.number_format = c.number_format
                    nc.font = _copy(c.font)
                    nc.fill = _copy(c.fill)
                    nc.border = _copy(c.border)
                    nc.alignment = _copy(c.alignment)
        for dim, d in src.column_dimensions.items():
            if d.width:
                dst.column_dimensions[dim].width = d.width
        for mc in list(src.merged_cells.ranges):
            dst.merge_cells(str(mc))
        dst.freeze_panes = src.freeze_panes
        # keep the canonical tab order (Near-Miss BUYs back to position 3)
        idx = wb.sheetnames.index("Near-Miss BUYs")
        wb.move_sheet("Near-Miss BUYs", offset=2 - idx)
        wb.save(copy_path)
        print(f"Wrote: {copy_path}  (COPY — original untouched; recalc in Excel/"
              "LibreOffice to refresh formula cache)")

    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
