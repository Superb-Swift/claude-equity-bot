#!/usr/bin/env python3
"""
build_actionable_registry.py  —  Claude Equity Bot, Phase 3-C engineering item

Auto-generates the ACTIONABLE-DIRECTIONAL registry FROM THE SIGNALS TAB. This is
the mirror of build_near_miss_registry.py: that tool captures directional signals
that FAILED CHECK 5; this one captures those that CLEARED it.

WHAT THIS IS, AND WHAT IT IS NOT
    THIS IS A TOOLING CHANGE, NOT A NEW ENDPOINT. The population is already
    defined by DP-3C-l/m and was already being tracked BY HAND in analyst_notes.
    Generating it from the Signals tab replaces a hand-maintained ledger with a
    derived one -- exactly the failure mode build_near_miss_registry.py was
    written to fix ("replacing the hand-maintained sheet that drifted twice in
    Week 4"). The 2026-08-13 review found the hand ledger's admission rule
    unwritten and its two resolved episodes carrying DIFFERENT gates.

    NO HYPOTHESIS IS OPENED HERE. DP-3C-l's reading standard is NONE and this
    tool does not change it. There is deliberately NO VERDICT BOX (see below).

ADMISSION RULE (RULED 2026-08-13)
    A row is ADMITTED if it is directional AND its operative confidence cleared
    ITS OWN CHECK 5 gate in risk_engine.py:
        BUY  -> conf >= MIN_CONFIDENCE_BUY  (70)
        SELL -> conf >= MIN_CONFIDENCE_SELL (65)
    There is no single "70% gate". CBRS SELL @ 68 on 2026-06-26 CLEARED its gate
    (68 >= 65) and is correctly admitted; it was rejected later, at CHECK 6.

    Admission is on CHECK 5 ONLY -- never on risk-engine APPROVAL. CHECKS 6/6b/7/8
    are portfolio-state rules that say nothing about whether the model was right,
    and admitting on approval would make the population a function of how many
    positions happened to be open. The risk disposition is CARRIED as a column
    instead (see ERA SPLIT).

MANDATORY DESIGN CONSTRAINTS (2026-08-13 review; do not remove without a ruling)
    1. GATE + MARGIN are stored per row. Two rows in the current record clear by
       EXACTLY ZERO (NVDA 8/10 and 8/13). A registry that hides margin makes a
       0-margin clearance indistinguishable from NVDA 8/05's +4.
    2. ERA SPLIT ON 2026-08-11, not on a lock cutoff. risk_engine.py L201-207
       REQUIRES that any reading of approval counts date-split on the DP-3C-o
       ruling rather than pool across it, and records that the change "makes the
       record look better, which is the direction warranting the most
       scepticism." Under the Phase-2 cap the engine approved ZERO directional
       signals in 57 cohorts. Pooling pre- and post-o rows into one hit rate
       would bake in exactly that contamination.
    3. ROW and EPISODE bases are BOTH reported, always. Consecutive same-name
       clearances coalesce into one episode under DP-3C-m. The near-miss
       registry's basis ambiguity is unresolved precisely because it only ever
       reported rows; repeating that in a new instrument is a choice, not an
       oversight.
    4. NO VERDICT BOX. build_near_miss_registry.py emits a "VERDICT -- RESOLVED"
       headline with a decision. Reproducing that here, at single-digit n, builds
       a machine for over-reading. This tool emits INSUFFICIENT TEST CONDITIONS
       and the DP-3C-l standard instead, and cannot be made to emit anything else
       without editing the source.
    5. NO FROZEN Q2 INVARIANTS. EXPECT_LOCKED / LOCKED_BASELINE / GATE_HIT_RATE /
       GATE_AVG_RETURN are near-miss artifacts. There is no locked cohort here,
       and a self-validation that WARNs on every run is a check that gets ignored.

HOUSE RULE (matches parse_log_to_tracker.py / build_near_miss_registry.py)
    Never mutates the master. Reads it read-only; writes standalone artifacts.
    --emit-into-copy embeds the sheet into tracker_with_registry.xlsx, which is
    an OUTPUT file rebuilt by the near-miss registry on every review run.

    ORDERING CONSTRAINT: build_near_miss_registry.py --emit-master-copy REBUILDS
    tracker_with_registry.xlsx from the master and DESTROYS any sheet embedded
    before it. This tool must therefore run AFTER it and BEFORE monitor_strip.py.

CONVENTIONS (Phase 2 locked)
    +Nd = N TRADING days from a holiday-aware calendar, never transcribed.
    Confidence stored as a fraction (0.72 == 72%). Returns as fractions.
    Directional rightness is the SIGN TEST: BUY right if r > 0, SELL if r < 0.
    The +/-3% HOLD band does not apply -- no HOLD row is ever admitted here.

USAGE
    python build_actionable_registry.py --tracker logs\\claude_equity_bot_tracker.xlsx
    python build_actionable_registry.py --tracker logs\\claude_equity_bot_tracker.xlsx --emit-into-copy
"""

from __future__ import annotations
import argparse
import datetime as dt
import os
import sys
from dataclasses import dataclass, field

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

SIGNALS_SHEET = "Signals"
SHEET_NAME = "Actionable BUYs"
HEADER_ROW = 4
FIRST_DATA_ROW = 5
LAST_DATA_ROW_CAP = 100_000

COL = dict(date=1, ticker=2, account=3, signal=4, conf=5, dq=6,
           p0=7, p5=8, p10=9, p20=10, r5=11, r10=12, r20=13, right5=14, notes=15)

# CHECK 5 thresholds, mirrored from risk_engine.RiskConfig. Kept as a dict rather
# than two constants so an unrecognised direction raises instead of defaulting.
CHECK5_GATE = {"BUY": 70.0, "SELL": 65.0}

# DP-3C-o (iii) landed on this date: CHECK 6 stopped REJECTING and became a flag.
# Every row before it faced a different risk engine. risk_engine.py L201-207
# requires the split; it is not a presentation choice.
ERA_SPLIT = dt.date(2026, 8, 11)
ERA_PRE, ERA_POST = "PRE-DP-3C-o", "POST-DP-3C-o"

NYSE_HOLIDAYS: set[dt.date] = {
    dt.date(2026, 1, 1), dt.date(2026, 1, 19), dt.date(2026, 2, 16),
    dt.date(2026, 4, 3), dt.date(2026, 5, 25), dt.date(2026, 6, 19),
    dt.date(2026, 7, 3), dt.date(2026, 9, 7), dt.date(2026, 11, 26),
    dt.date(2026, 12, 25),
}


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
    """Confidence as a percentage. Accepts fraction (0.72) or percent (72)."""
    if v is None or not isinstance(v, (int, float)):
        return None
    return float(v) * 100.0 if v <= 1.0 else float(v)


def direction(v):
    s = str(v).strip().upper()
    return s if s in CHECK5_GATE else None


def clears_check5(sig: str, conf) -> bool:
    """CHECK 5, mirrored. Rounds to 6dp first: 0.7*100 is 70.00000000000001 in
    IEEE754 and a naive >= comparison on the other side of a subtraction can
    flip a 0-margin clearance. Both sides of the comparison are integers in
    practice, so 6dp is generous."""
    p = conf_pct(conf)
    if p is None or sig not in CHECK5_GATE:
        return False
    return round(p, 6) >= CHECK5_GATE[sig]


def add_trading_days(start: dt.date, n: int, holidays: set[dt.date]) -> dt.date:
    d, added = start, 0
    while added < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            added += 1
    return d


def pct(x, plus=False):
    if x is None:
        return "—"
    s = f"{x*100:.1f}%"
    return f"+{s}" if (plus and x >= 0) else s


def usd(x):
    return "—" if x is None else f"${x:,.2f}"


def mdrow(cells):
    return "| " + " | ".join(cells) + " |"


@dataclass
class Actionable:
    date: dt.date
    ticker: str
    account: str
    signal: str
    conf: float           # fraction
    gate: float           # percent (70 or 65)
    margin: float         # percent points above the gate; 0.0 is meaningful
    dq: str
    p0: float
    p5: float | None
    p10: float | None
    r5: float | None
    r10: float | None
    notes: str
    d5: dt.date
    d10: dt.date
    era: str
    episode_id: str = field(default="")
    episode_open: bool = field(default=False)   # True on the episode's first row

    def hit5(self):
        if self.r5 is None:
            return None
        return (self.r5 > 0) if self.signal == "BUY" else (self.r5 < 0)

    def hit10(self):
        if self.r10 is None:
            return None
        return (self.r10 > 0) if self.signal == "BUY" else (self.r10 < 0)


# --------------------------------------------------------------------------- #
# Read + filter (READ-ONLY on the source workbook)
# --------------------------------------------------------------------------- #

def load_actionable(tracker_path: str) -> tuple[list[Actionable], list[dt.date]]:
    wb = openpyxl.load_workbook(tracker_path, data_only=True, read_only=True)
    if SIGNALS_SHEET not in wb.sheetnames:
        wb.close()
        sys.exit(f"ERROR: '{SIGNALS_SHEET}' tab not found in {tracker_path}")
    ws = wb[SIGNALS_SHEET]

    rows: list[Actionable] = []
    all_dates: set[dt.date] = set()
    blank_streak = 0
    # SINGLE PASS with iter_rows rather than per-cell ws.cell() lookups. On a
    # read-only worksheet each ws.cell() call can re-walk the sheet, which turns
    # a 1,500-row scan into minutes. iter_rows streams it once.
    for vals in ws.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW_CAP,
                             min_col=1, max_col=COL["notes"], values_only=True):
        def g(name):
            i = COL[name] - 1
            return vals[i] if i < len(vals) else None

        d = as_date(g("date"))
        tk = g("ticker")
        if d is None and not tk:
            blank_streak += 1
            if blank_streak >= 25:
                break
            continue
        blank_streak = 0
        if d is None:
            continue
        all_dates.add(d)
        sig = direction(g("signal"))
        conf = g("conf")
        if sig is None or not clears_check5(sig, conf):
            continue
        p = conf_pct(conf)
        rows.append(Actionable(
            date=d,
            ticker=str(tk).strip(),
            account=str(g("account") or "").strip(),
            signal=sig,
            conf=(conf if conf <= 1.0 else conf / 100.0),
            gate=CHECK5_GATE[sig],
            margin=round(p - CHECK5_GATE[sig], 6),
            dq=str(g("dq") or "").strip(),
            p0=g("p0"), p5=g("p5"), p10=g("p10"),
            r5=g("r5"), r10=g("r10"),
            notes=str(g("notes") or "").strip(),
            d5=add_trading_days(d, 5, NYSE_HOLIDAYS),
            d10=add_trading_days(d, 10, NYSE_HOLIDAYS),
            era=(ERA_PRE if d < ERA_SPLIT else ERA_POST),
        ))
    wb.close()
    rows.sort(key=lambda x: (x.date, x.ticker))
    return rows, sorted(all_dates)


# --------------------------------------------------------------------------- #
# DP-3C-m episode coalescing
# --------------------------------------------------------------------------- #

def assign_episodes(rows: list[Actionable], cohort_dates: list[dt.date]) -> None:
    """DP-3C-m: consecutive gate-clearing COHORT SESSIONS on one ticker are ONE
    episode. Adjacency is measured against the cohort calendar derived from the
    master itself -- never a holiday table and never a second source of truth,
    so a skipped session (holiday, 429, no run) cannot silently split an episode.
    """
    idx = {d: i for i, d in enumerate(cohort_dates)}
    by_ticker: dict[str, list[Actionable]] = {}
    for x in rows:
        by_ticker.setdefault(x.ticker, []).append(x)
    for tk, xs in by_ticker.items():
        xs.sort(key=lambda x: x.date)
        prev = None
        eid = None
        for x in xs:
            contiguous = (prev is not None
                          and idx.get(x.date, -99) == idx.get(prev.date, -100) + 1)
            if not contiguous:
                eid = f"{tk}-{x.date:%Y%m%d}"
                x.episode_open = True
            x.episode_id = eid
            prev = x


def episode_view(rows: list[Actionable]) -> list[dict]:
    """One record per episode, scored on its OPENING row (the DP-3C-l precedent:
    NVDA's 8/04 episode resolved on the 8/04 row's +5d, not on a later member)."""
    out = []
    seen = {}
    for x in rows:
        seen.setdefault(x.episode_id, []).append(x)
    for eid, xs in seen.items():
        xs.sort(key=lambda x: x.date)
        head = xs[0]
        out.append(dict(
            episode_id=eid, ticker=head.ticker, signal=head.signal,
            opened=head.date, last=xs[-1].date, sessions=len(xs),
            open_conf=head.conf, open_margin=head.margin, era=head.era,
            hit5=head.hit5(), r5=head.r5,
        ))
    out.sort(key=lambda e: e["opened"])
    return out


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #

def summarize_rows(rows: list[Actionable]) -> dict:
    comp5 = [x for x in rows if x.r5 is not None]
    comp10 = [x for x in rows if x.r10 is not None]
    h5 = [x for x in comp5 if x.hit5()]
    h10 = [x for x in comp10 if x.hit10()]
    return dict(
        n=len(rows), comp5=len(comp5), hit5=len(h5),
        rate5=(len(h5) / len(comp5)) if comp5 else None,
        avg5=(sum(x.r5 for x in comp5) / len(comp5)) if comp5 else None,
        comp10=len(comp10), hit10=len(h10),
        rate10=(len(h10) / len(comp10)) if comp10 else None,
        avg10=(sum(x.r10 for x in comp10) / len(comp10)) if comp10 else None,
        zero_margin=len([x for x in rows if x.margin == 0.0]),
    )


def summarize_episodes(eps: list[dict]) -> dict:
    comp = [e for e in eps if e["hit5"] is not None]
    hit = [e for e in comp if e["hit5"]]
    return dict(n=len(eps), comp5=len(comp), hit5=len(hit),
                rate5=(len(hit) / len(comp)) if comp else None)


STANDARD_TEXT = (
    "INSUFFICIENT TEST CONDITIONS. DP-3C-l's reading standard is NONE and this "
    "tool does not change it. No disposition is read from this registry at any n "
    "until DP-3C-l is amended by a dated ruling. The ROW and EPISODE bases are "
    "both shown because the correct basis is UNRULED (2026-08-13); a figure "
    "quoted from one basis alone is incomplete."
)

ERA_TEXT = (
    "ERA SPLIT IS MANDATORY, NOT COSMETIC. Before 2026-08-11 the risk engine "
    "approved ZERO directional signals across 57 cohorts -- CHECK 6 rejected them "
    "on open-position count. DP-3C-o (iii) demoted CHECK 6 to a non-blocking flag "
    "on that date. risk_engine.py L201-207 requires that approval counts date-"
    "split here rather than pool, and records the change as one that makes the "
    "record look better. Do not quote a pooled hit rate across this line."
)


# --------------------------------------------------------------------------- #
# Excel writer
# --------------------------------------------------------------------------- #

HEADERS = ["Signal Date", "Ticker", "Account", "Signal", "Conf %", "CHECK 5 Gate",
           "Margin (pts)", "Data Quality", "Price at Signal", "+5d Date",
           "+10d Date", "Price +5d", "Price +10d", "Return +5d", "Return +10d",
           "Hit (5d)", "Hit (10d)", "Episode", "Opens Episode", "Risk Era", "Notes"]

A = {n: get_column_letter(i + 1) for i, n in enumerate(
    ["sigdate", "ticker", "acct", "sig", "conf", "gate", "margin", "dq", "p0",
     "d5", "d10", "p5", "p10", "r5", "r10", "hit5", "hit10", "epi", "epiopen",
     "era", "notes"])}

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
PRE_FILL = PatternFill("solid", fgColor="F2F2F2")     # pre-DP-3C-o: grey, inert
POST_FILL = PatternFill("solid", fgColor="E2EFDA")    # post: green, live engine
LABEL_FILL = PatternFill("solid", fgColor="F2F2F2")
WARN_FILL = PatternFill("solid", fgColor="FCE4D6")
ZERO_FILL = PatternFill("solid", fgColor="FFF2CC")    # margin == 0 highlight


def write_xlsx(rows, eps, out_path, tracker_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET_NAME

    def cell(r, c, val, *, bold=False, fill=None, fmt=None, align="left",
             color=None, size=10, border=True):
        cc = ws.cell(row=r, column=c, value=val)
        cc.font = Font(name="Arial", size=size, bold=bold,
                       color=color or ("FFFFFF" if fill is HEAD_FILL else "000000"))
        cc.alignment = Alignment(horizontal=align, vertical="center")
        if fill:
            cc.fill = fill
        if fmt:
            cc.number_format = fmt
        if border:
            cc.border = BORDER
        return cc

    cell(1, 1, "Actionable Directional Signals — CHECK 5 clearances (auto-generated)",
         bold=True, size=12, border=False)
    cell(2, 1, "AUTO-GENERATED from the Signals tab — do not hand-edit. Admitted on "
               "CHECK 5 clearance at the signal's OWN gate (BUY ≥70%, SELL ≥65%), "
               "never on risk-engine approval. Mirror of the Near-Miss BUY registry.",
         size=9, border=False)

    for c in range(1, len(HEADERS) + 1):
        cell(HEADER_ROW, c, HEADERS[c - 1], bold=True, fill=HEAD_FILL,
             align="center", size=9)

    r = FIRST_DATA_ROW
    for x in rows:
        fill = PRE_FILL if x.era == ERA_PRE else POST_FILL
        cell(r, 1, x.date, fill=fill, fmt="yyyy-mm-dd", align="center")
        cell(r, 2, x.ticker, fill=fill, bold=True, align="center")
        cell(r, 3, x.account, fill=fill)
        cell(r, 4, x.signal, fill=fill, bold=True, align="center")
        cell(r, 5, x.conf, fill=fill, fmt="0%", align="center")
        cell(r, 6, x.gate / 100.0, fill=fill, fmt="0%", align="center")
        # Margin: 0.0 is a REAL value and must not render as blank or as "—".
        cell(r, 7, x.margin, fill=(ZERO_FILL if x.margin == 0.0 else fill),
             fmt="+0.0;-0.0;0.0", align="center",
             bold=(x.margin == 0.0))
        cell(r, 8, x.dq, fill=fill, align="center")
        cell(r, 9, x.p0, fill=fill, fmt="$#,##0.00", align="right")
        cell(r, 10, x.d5, fill=fill, fmt="yyyy-mm-dd", align="center")
        cell(r, 11, x.d10, fill=fill, fmt="yyyy-mm-dd", align="center")
        cell(r, 12, x.p5, fill=fill, fmt="$#,##0.00", align="right")
        cell(r, 13, x.p10, fill=fill, fmt="$#,##0.00", align="right")
        cell(r, 14, f'=IF({A["p5"]}{r}<>"",{A["p5"]}{r}/{A["p0"]}{r}-1,"")',
             fill=fill, fmt="0.0%;[Red]-0.0%", align="right")
        cell(r, 15, f'=IF({A["p10"]}{r}<>"",{A["p10"]}{r}/{A["p0"]}{r}-1,"")',
             fill=fill, fmt="0.0%;[Red]-0.0%", align="right")
        # SIGN TEST, direction-aware. The near-miss sheet can hardcode ">0"
        # because it is BUY-only; this sheet cannot -- a SELL is right when the
        # return is NEGATIVE, and a copied ">0" formula would score CBRS backwards.
        cell(r, 16, f'=IF({A["r5"]}{r}="","",IF({A["sig"]}{r}="BUY",'
                    f'IF({A["r5"]}{r}>0,"YES","NO"),IF({A["r5"]}{r}<0,"YES","NO")))',
             fill=fill, align="center")
        cell(r, 17, f'=IF({A["r10"]}{r}="","",IF({A["sig"]}{r}="BUY",'
                    f'IF({A["r10"]}{r}>0,"YES","NO"),IF({A["r10"]}{r}<0,"YES","NO")))',
             fill=fill, align="center")
        cell(r, 18, x.episode_id, fill=fill, align="center", size=9)
        cell(r, 19, "OPEN" if x.episode_open else "", fill=fill, align="center", size=9)
        cell(r, 20, x.era, fill=fill, align="center", size=9)
        cell(r, 21, x.notes, fill=fill, size=9)
        r += 1
    data_start, data_end = FIRST_DATA_ROW, r - 1

    eraP = f'{A["era"]}{data_start}:{A["era"]}{data_end}'
    p5R = f'{A["p5"]}{data_start}:{A["p5"]}{data_end}'
    r5R = f'{A["r5"]}{data_start}:{A["r5"]}{data_end}'
    m5R = f'{A["hit5"]}{data_start}:{A["hit5"]}{data_end}'
    mgR = f'{A["margin"]}{data_start}:{A["margin"]}{data_end}'

    def era_block(start_row, label, era, sub):
        cell(start_row, 1, label, bold=True, fill=LABEL_FILL, size=10)
        cell(start_row, 2, sub, size=9, color="808080", border=False)
        defs = [
            ("Rows (n)", f'=COUNTIF({eraP},"{era}")', "0"),
            ("Completed +5d", f'=COUNTIFS({eraP},"{era}",{p5R},"<>")', "0"),
            ("Hit count (+5d)", f'=COUNTIFS({eraP},"{era}",{m5R},"YES")', "0"),
            ("Hit rate +5d",
             f'=IFERROR(COUNTIFS({eraP},"{era}",{m5R},"YES")'
             f'/COUNTIFS({eraP},"{era}",{p5R},"<>"),"—")', "0.0%"),
            ("Avg +5d return",
             f'=IFERROR(AVERAGEIFS({r5R},{eraP},"{era}",{p5R},"<>"),"—")',
             "0.0%;[Red]-0.0%"),
            ("Rows clearing by 0 pts", f'=COUNTIFS({eraP},"{era}",{mgR},0)', "0"),
        ]
        rr = start_row + 1
        for name, formula, fmt in defs:
            cell(rr, 1, name, size=9)
            cell(rr, 2, formula, fmt=fmt, align="right", size=9)
            rr += 1
        return rr

    rr = data_end + 2
    rr = era_block(rr, "PRE-DP-3C-o — risk engine REJECTED every directional row",
                   ERA_PRE, f"signals before {ERA_SPLIT:%Y-%m-%d}")
    rr += 1
    rr = era_block(rr, "POST-DP-3C-o — CHECK 6 demoted to a flag",
                   ERA_POST, f"signals on/after {ERA_SPLIT:%Y-%m-%d}")
    rr += 1

    cell(rr, 1, "DO NOT POOL ACROSS THE ERA LINE", bold=True, fill=WARN_FILL, size=10)
    rr += 1
    cell(rr, 1, ERA_TEXT, size=9, border=False)
    rr += 2

    # ---- Episode basis ----
    es = summarize_episodes(eps)
    rsum = summarize_rows(rows)
    cell(rr, 1, "BOTH BASES — the correct one is UNRULED", bold=True,
         fill=LABEL_FILL, size=10)
    rr += 1
    for name, val, fmt in [
        ("ROW basis — n", rsum["n"], "0"),
        ("ROW basis — resolved +5d", rsum["comp5"], "0"),
        ("ROW basis — hit rate +5d", rsum["rate5"], "0.0%"),
        ("EPISODE basis — n (DP-3C-m coalesced)", es["n"], "0"),
        ("EPISODE basis — resolved +5d", es["comp5"], "0"),
        ("EPISODE basis — hit rate +5d", es["rate5"], "0.0%"),
        ("Rows clearing by exactly 0 pts", rsum["zero_margin"], "0"),
    ]:
        cell(rr, 1, name, size=9)
        cell(rr, 2, val if val is not None else "—", fmt=fmt, align="right", size=9)
        rr += 1
    rr += 1

    # ---- Standard box: deliberately NOT a verdict ----
    cell(rr, 1, "READING STANDARD — NOT A VERDICT", bold=True, fill=WARN_FILL, size=10)
    rr += 1
    cell(rr, 1, STANDARD_TEXT, size=9, border=False)
    rr += 2

    cell(rr, 1, f"Source: {os.path.basename(tracker_path)} · Signals tab · "
                f"generated {dt.datetime.now():%Y-%m-%d %H:%M} · admission = CHECK 5 "
                f"clearance (BUY ≥{CHECK5_GATE['BUY']:.0f}%, SELL ≥{CHECK5_GATE['SELL']:.0f}%) · "
                f"era split {ERA_SPLIT:%Y-%m-%d} · +Nd = trading days.",
         size=8, color="808080", border=False)

    widths = [12, 8, 11, 8, 8, 12, 12, 9, 14, 12, 12, 11, 11, 11, 11, 9, 9, 16, 13, 15, 26]
    for i, w in enumerate(widths):
        ws.column_dimensions[get_column_letter(i + 1)].width = w
    ws.freeze_panes = "A5"
    wb.save(out_path)


# --------------------------------------------------------------------------- #
# Markdown writer
# --------------------------------------------------------------------------- #

def write_markdown(rows, eps, md_path, tracker_path):
    rsum, es = summarize_rows(rows), summarize_episodes(eps)

    def hit_str(v):
        return "—" if v is None else ("YES" if v else "NO")

    tbl = [mdrow(["Date", "Tkr", "Sig", "Conf", "Gate", "Margin", "DQ", "Price",
                  "+5d Ret", "Hit 5d", "Episode", "Era"]), mdrow(["---"] * 12)]
    for x in rows:
        tbl.append(mdrow([
            f"{x.date:%Y-%m-%d}", x.ticker, x.signal, pct(x.conf),
            f"{x.gate:.0f}%", f"{x.margin:+.0f}" if x.margin else "**0**",
            x.dq, usd(x.p0),
            pct(x.r5, plus=True) if x.r5 is not None else "pending",
            hit_str(x.hit5()), x.episode_id + (" *(open)*" if x.episode_open else ""),
            x.era,
        ]))

    etbl = [mdrow(["Episode", "Sig", "Opened", "Last", "Sessions", "Open conf",
                   "Open margin", "Hit 5d", "Era"]), mdrow(["---"] * 9)]
    for e in eps:
        etbl.append(mdrow([
            e["episode_id"], e["signal"], f"{e['opened']:%Y-%m-%d}",
            f"{e['last']:%Y-%m-%d}", str(e["sessions"]), pct(e["open_conf"]),
            f"{e['open_margin']:+.0f}" if e["open_margin"] else "**0**",
            hit_str(e["hit5"]), e["era"],
        ]))

    md = f"""# Actionable Directional Registry — auto-generated

*Source: `{os.path.basename(tracker_path)}` · Signals tab · generated \
{dt.datetime.now():%Y-%m-%d %H:%M}. Admission = CHECK 5 clearance at the signal's \
own gate (BUY ≥ {CHECK5_GATE['BUY']:.0f}%, SELL ≥ {CHECK5_GATE['SELL']:.0f}%), \
never risk-engine approval. +Nd = trading days. Advisory-only · no orders.*

**Rows: {rsum['n']} · Episodes: {es['n']} · rows clearing by exactly 0 pts: {rsum['zero_margin']}**

## ⚠ READING STANDARD — NOT A VERDICT

{STANDARD_TEXT}

## ⚠ ERA SPLIT

{ERA_TEXT}

| Era | Rows | Resolved +5d | Hit +5d |
|---|---|---|---|
| {ERA_PRE} | {sum(1 for x in rows if x.era==ERA_PRE)} | \
{sum(1 for x in rows if x.era==ERA_PRE and x.r5 is not None)} | \
{sum(1 for x in rows if x.era==ERA_PRE and x.hit5())} |
| {ERA_POST} | {sum(1 for x in rows if x.era==ERA_POST)} | \
{sum(1 for x in rows if x.era==ERA_POST and x.r5 is not None)} | \
{sum(1 for x in rows if x.era==ERA_POST and x.hit5())} |

## Both bases

- **ROW basis** — n = {rsum['n']} · resolved +5d = {rsum['comp5']} · hit = \
**{rsum['hit5']}/{rsum['comp5']}** ({pct(rsum['rate5'])}) · avg +5d = \
{pct(rsum['avg5'], plus=True)}
- **EPISODE basis** (DP-3C-m coalesced, scored on the opening row) — n = \
{es['n']} · resolved +5d = {es['comp5']} · hit = **{es['hit5']}/{es['comp5']}** \
({pct(es['rate5'])})

## Rows

{chr(10).join(tbl)}

## Episodes

{chr(10).join(etbl)}
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)


# --------------------------------------------------------------------------- #
# Console digest + self-validation
# --------------------------------------------------------------------------- #

def console_digest(rows, eps, cohort_dates):
    ok = True
    rsum, es = summarize_rows(rows), summarize_episodes(eps)
    print("\n" + "=" * 66)
    print("ACTIONABLE DIRECTIONAL REGISTRY — DIGEST")
    print("=" * 66)
    print(f"Rows: {rsum['n']}   Episodes: {es['n']}   "
          f"Cohorts scanned: {len(cohort_dates)}")
    print(f"ROW     basis  +5d  {rsum['hit5']}/{rsum['comp5']} = {pct(rsum['rate5'])}"
          f"   avg {pct(rsum['avg5'], plus=True)}")
    print(f"EPISODE basis  +5d  {es['hit5']}/{es['comp5']} = {pct(es['rate5'])}")
    print(f"Rows clearing by exactly 0 pts: {rsum['zero_margin']}")
    for era in (ERA_PRE, ERA_POST):
        sub = [x for x in rows if x.era == era]
        s = summarize_rows(sub)
        print(f"  {era:14s} rows {s['n']:3d}  resolved {s['comp5']:3d}  "
              f"hit {s['hit5']}/{s['comp5']} = {pct(s['rate5'])}")
    print("\nNO VERDICT IS EMITTED. " + STANDARD_TEXT.split(".")[0] + ".")

    print("\n" + "-" * 66)
    print("SELF-VALIDATION")
    print("-" * 66)

    def check(name, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  [{'PASS' if cond else 'WARN'}] {name}")

    # Every check below can actually FAIL on real data. None assert a constant.
    check("no HOLD row admitted",
          all(x.signal in CHECK5_GATE for x in rows))
    check("every admitted row clears its OWN gate",
          all(round(x.conf * 100, 6) >= x.gate for x in rows))
    check("margin == conf - gate on every row",
          all(abs(round(x.conf * 100 - x.gate, 6) - x.margin) < 1e-9 for x in rows))
    check("every row carries a +5d and +10d trading date",
          all(x.d5 and x.d10 for x in rows))
    check("every row has an episode id",
          all(x.episode_id for x in rows))
    check("exactly one OPEN row per episode",
          len([x for x in rows if x.episode_open]) == len(eps))
    check("every signal date is a known cohort date",
          all(x.date in set(cohort_dates) for x in rows))
    check("era assignment matches the split date",
          all((x.era == ERA_PRE) == (x.date < ERA_SPLIT) for x in rows))
    check("no row is in BOTH this registry and the near-miss band [60,70)",
          not any(x.signal == "BUY" and 60.0 <= x.conf * 100 < 70.0 for x in rows))
    if not ok:
        print("\n  !! One or more checks WARNed — inspect before trusting the run.")
    else:
        print("\n  All checks passed.")
    return ok


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Regenerate the actionable-directional registry from the "
                    "Signals tab (read-only on source).")
    ap.add_argument("--tracker", default="claude_equity_bot_tracker.xlsx")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--emit-into-copy", action="store_true",
                    help="ALSO embed the sheet into tracker_with_registry.xlsx. "
                         "MUST run AFTER build_near_miss_registry.py "
                         "--emit-master-copy, which rebuilds that file.")
    ap.add_argument("--copy", default="tracker_with_registry.xlsx",
                    help="report copy to embed into (default: %(default)s)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.tracker):
        sys.exit(f"ERROR: tracker not found: {args.tracker}")
    if os.path.basename(args.tracker).lower() == "tracker_with_registry.xlsx":
        sys.exit("ERROR: refusing to read the generated report copy as the "
                 "master. Pass logs\\claude_equity_bot_tracker.xlsx. (exit 2)")
    os.makedirs(args.out_dir, exist_ok=True)

    rows, cohort_dates = load_actionable(args.tracker)
    if not rows:
        print("No actionable directional signals found. Writing an EMPTY registry "
              "rather than exiting — an empty population is a real and reportable "
              "state for this instrument, unlike the near-miss registry.")
    assign_episodes(rows, cohort_dates)
    eps = episode_view(rows)

    xlsx_path = os.path.join(args.out_dir, "actionable_registry.xlsx")
    md_path = os.path.join(args.out_dir, "actionable_registry.md")
    write_xlsx(rows, eps, xlsx_path, args.tracker)
    write_markdown(rows, eps, md_path, args.tracker)
    ok = console_digest(rows, eps, cohort_dates)
    print(f"\nWrote: {xlsx_path}\nWrote: {md_path}")

    if args.emit_into_copy:
        if not os.path.exists(args.copy):
            sys.exit(f"ERROR: report copy not found: {args.copy}. Run "
                     f"build_near_miss_registry.py --emit-master-copy FIRST — it "
                     f"rebuilds that file and would destroy this sheet. (exit 3)")
        from copy import copy as _copy
        wb = openpyxl.load_workbook(args.copy)
        if SHEET_NAME in wb.sheetnames:
            del wb[SHEET_NAME]
        src = openpyxl.load_workbook(xlsx_path)[SHEET_NAME]
        dst = wb.create_sheet(SHEET_NAME)
        for row in src.iter_rows():
            for c in row:
                nc = dst.cell(row=c.row, column=c.column, value=c.value)
                if c.has_style:
                    # Copy style ATTRIBUTES, not the _style index — StyleArray
                    # indices point into the SOURCE workbook's tables and scramble
                    # when reused (symptom: price cells render as 1900 dates).
                    nc.number_format = c.number_format
                    nc.font = _copy(c.font)
                    nc.fill = _copy(c.fill)
                    nc.border = _copy(c.border)
                    nc.alignment = _copy(c.alignment)
        for dim, d in src.column_dimensions.items():
            if d.width:
                dst.column_dimensions[dim].width = d.width
        dst.freeze_panes = src.freeze_panes
        # park it immediately after 'Near-Miss BUYs' so the two registries sit together
        try:
            anchor = wb.sheetnames.index("Near-Miss BUYs") + 1
            wb.move_sheet(SHEET_NAME, offset=anchor - wb.sheetnames.index(SHEET_NAME))
        except ValueError:
            pass
        wb.save(args.copy)
        print(f"Wrote: {args.copy}  (COPY — master untouched; open in Excel to "
              f"refresh the formula cache)")

    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
