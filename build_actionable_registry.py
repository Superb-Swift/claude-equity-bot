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

2026-09-16 ADDITIONS (DP-3C-u, DP-3C-af, DP-3C-w / DP-3C-ah)
    * EXECUTABILITY (DP-3C-u): EXECUTABLE / PARTIAL / BLOCKED, read from each
      row's log line -- the PER-ACCOUNT field where the log carries one, the
      top-level Risk verdict before that field existed. A REPORTED ATTRIBUTE,
      NEVER A FILTER: no figure in this tool is computed on a subset selected
      by it. The ruling's revisit condition (PARTIAL > 25% of post-era rows)
      is checked and printed.
    * CHANNELMARGIN (DP-3C-af): the ledger admits on D.op, the confidence
      CHECK 5 actually gated on. Where the descoped blend channel disagrees,
      the row is marked; ERASED means blend_op < gate <= D.op (MSFT 2026-08-27
      and 2026-09-08). Nothing is read from the blend.
    * DP-3C-w PROSPECTIVE ARM: counted here with episodes.dp3cw_arm(), blind
      until 10 episodes resolve; the first qualifying reading is recorded to
      logs/instrument_readings.json and printed thereafter as recorded.
    The registry reads logs with signal_logs.discover() (recursive). A row
    whose log is not on disk shows "no log".

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
    executability: str = field(default="")      # DP-3C-u
    channel_margin: str = field(default="")     # DP-3C-af
    per_account: dict = field(default_factory=dict)   # DP-3C-av, verbatim from the log
    bridged: list = field(default_factory=list)       # DP-3C-ar, on the OPEN row only

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
# Log fields: Executability (DP-3C-u) and ChannelMargin (DP-3C-af)
# --------------------------------------------------------------------------- #
import re as _re

_LINE_RE = _re.compile(r'Signal JSON: \{"ticker": "(?P<tk>[A-Z.\-]+)"')
_RISK_RE = _re.compile(r"\|\s*Risk:\s*(?P<risk>APPROVED|REJECTED)\b")
_PER_RE = _re.compile(r"PER-ACCOUNT:\s*(?P<per>[^.|]*)\.")
_OP_RE = _re.compile(r"D\[raw=\d+;\s*op=(?P<op>\d+);")
_BOP_RE = _re.compile(r"blend_op=(?P<bop>\d+)\]")


def load_log_fields(pattern):
    """{(date, ticker): dict(exec, src, op, blend_op)} from every signals log."""
    out = {}
    try:
        import signal_logs
        paths, _info = signal_logs.discover(pattern)
    except Exception:                                   # noqa: BLE001
        import glob
        paths = sorted(glob.glob(pattern))
    for fp in paths:
        m = _re.search(r"signals_(\d{4}-\d{2}-\d{2})\.log$", os.path.basename(fp))
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        with open(fp, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                lm = _LINE_RE.search(line)
                if not lm:
                    continue
                tail = line[lm.end():]
                risk = _RISK_RE.search(tail)
                per = _PER_RE.search(tail)
                ex, src = "", ""
                if per:
                    verdicts = [v.split("=", 1)[1].strip().upper()
                                for v in per.group("per").split(";") if "=" in v]
                    if verdicts:
                        n_ok = sum(1 for v in verdicts if v == "APPROVED")
                        ex = ("EXECUTABLE" if n_ok == len(verdicts) else
                              "BLOCKED" if n_ok == 0 else "PARTIAL")
                        src = "per-account"
                if not ex and risk:
                    ex = "EXECUTABLE" if risk.group("risk") == "APPROVED" else "BLOCKED"
                    src = "top-level (pre per-account logging)"
                op = _OP_RE.search(tail)
                bop = _BOP_RE.search(tail)
                out.setdefault((d, lm.group("tk")), dict(
                    exec=ex, src=src,
                    per=(per.group("per").strip() if per else ""),
                    op=int(op.group("op")) if op else None,
                    blend_op=int(bop.group("bop")) if bop else None))
    return out


def attach_log_fields(rows, fields):
    for x in rows:
        f = fields.get((x.date, x.ticker))
        if not f:
            x.executability, x.channel_margin = "no log", "no log"
            continue
        x.executability = f["exec"] or "unparsed"
        x.per_account = {k.strip(): v.strip().upper()
                         for k, v in (seg.split("=", 1) for seg in (f.get("per") or "").split(";")
                                      if "=" in seg)}
        if x.executability == "PARTIAL" and f.get("per"):
            # DP-3C-u's revisit condition was met on 2026-09-16 (PARTIAL above
            # 25% of post-era rows). The per-account verdicts are therefore
            # carried verbatim, so any future per-account pre-registration has
            # its inputs on the row. Still an attribute, never a filter.
            x.executability += " (" + f["per"] + ")"
        op, bop = f["op"], f["blend_op"]
        if op is None or bop is None:
            x.channel_margin = "n/a (no D/B tag)"
        elif op == bop:
            x.channel_margin = ""
        else:
            # DP-3C-as (RULED 2026-09-25): ERASED is SIGNAL-AWARE. The guard
            # `if x.signal == "BUY" else False` stood here from 2026-09-16 and
            # made the SELL branch unreachable, contradicting this module's own
            # definition ("blend_op < gate <= D.op") and signal_scan's
            # _would_lose_gate(), which mirrors both gates. It was latent until
            # the first post-era SELLs (USO 2026-09-23, TWST 2026-09-24/25) and
            # hid three rows signal_scan FAILed. x.gate already carries 65 for
            # a SELL, so the comparison needs no other change.
            erased = bop < x.gate <= op
            x.channel_margin = ("ERASED: " if erased else "") + \
                f"D.op {op} / blend_op {bop} ({bop - op:+d})"


def load_master_rows(tracker_path):
    """Every master row as a light dict for the DP-3C-w arm (price-derived
    +5d return, so the formula cache cannot affect it)."""
    wb = openpyxl.load_workbook(tracker_path, data_only=True, read_only=True)
    ws = wb[SIGNALS_SHEET]
    out, blank = [], 0
    for vals in ws.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW_CAP,
                             min_col=1, max_col=COL["p5"], values_only=True):
        d = as_date(vals[0])
        if d is None:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        conf = vals[COL["conf"] - 1]
        p0, p5 = vals[COL["p0"] - 1], vals[COL["p5"] - 1]
        ok = isinstance(p0, (int, float)) and isinstance(p5, (int, float)) and p0
        out.append(dict(
            date=d, ticker=str(vals[1] or "").strip().upper(),
            signal=str(vals[COL["signal"] - 1] or "").strip().upper(),
            conf=(conf * 100 if isinstance(conf, (int, float)) and conf <= 1 else conf),
            ret5=((p5 - p0) / p0) if ok else None))
    wb.close()
    return out


def load_dropouts(pattern, master_rows):
    """DP-3C-ar (2026-09-25): run-fault dropouts from the logs, vetoed by any
    master row for the same (ticker, date)."""
    import episodes
    try:
        import signal_logs
        paths, _info = signal_logs.discover(pattern)
    except Exception:                                   # noqa: BLE001
        import glob
        paths = sorted(glob.glob(pattern))
    return episodes.dropouts_from_logs(
        paths, present={(r["ticker"], r["date"]) for r in master_rows})


def _r1(arm, as_of):
    """DP-3C-bb (R1): (recordable, last resolving session). A one-time read is
    recorded only once every resolving close predates the newest cohort, i.e.
    a later session's log has carried it and Check F has compared it."""
    import trading_calendar as _tc
    import rulings as _ru
    sess = [_tc.shift_sessions(d, 5) for d in arm.get("resolved_open_dates", [])]
    return _ru.read_protection(sess, as_of)


def mask_resolved_through(master_rows, through):
    """DP-3C-bl (2026-11-06): a copy of master_rows in which a +5d result counts
    only when its +5d session is on or before `through` (rulings.EXIT_CUT). The
    rows themselves are all kept, so episodes coalesce exactly as they do
    nightly; only what has RESOLVED is pinned to the cut."""
    import trading_calendar as _tc
    out = []
    for r in master_rows:
        if r.get("ret5") is not None and _tc.shift_sessions(r["date"], 5) > through:
            r = dict(r, ret5=None)
        out.append(r)
    return out


def dp3cw_block(master_rows, cohort_dates, as_of, record=True, dropouts=None,
                exit_read=False, resolved_through=None, exit_run=False):
    """Print the DP-3C-w arm. Records the FIRST read and prints it thereafter.
    dropouts: DP-3C-ar run-fault set (2026-09-25), bridged not split.

    AMENDED 2026-10-22 (DP-3C-bb, R1): a read is recorded only once its
    resolving closes have been log-verified; before that the block prints
    counts only and withholds rho. exit_read: the once-more read DP-3C-ah
    reserves for the Phase 3-C exit review, recorded as 'DP-3C-w@exit' under
    the same protection. It is taken only when asked for (--exit-read).

    AMENDED 2026-11-06 (DP-3C-bl): resolved_through pins the exit read to the
    ruled cut, so it reads the same episodes whenever it is run."""
    import episodes
    if resolved_through is not None:
        master_rows = mask_resolved_through(master_rows, resolved_through)
    arm = episodes.dp3cw_arm(master_rows, cohort_dates, dropouts=dropouts)
    lines = ["DP-3C-w PROSPECTIVE ARM (episodes opening on/after 2026-09-03)",
             f"  episodes opened {arm['n_open']}   resolved +5d {arm['n_resolved']} of "
             f"{episodes.DP3CW_MIN_N} needed   tickers {len(arm['tickers'])} "
             f"({', '.join(arm['tickers']) or 'none'}) of {episodes.DP3CW_MIN_TICKERS} needed"]
    if resolved_through is not None:
        lines.append(f"  pinned: +5d results counted through {resolved_through} "
                     "(rulings.EXIT_CUT, DP-3C-bl)")
    if arm.get("bridged"):
        lines.append("  DP-3C-ar bridged (run-fault dropout, not a split): "
                     + ", ".join(f"{t} {d:%Y-%m-%d}" for t, d in arm["bridged"]))
    try:
        import rulings
        prior = rulings.readings("DP-3C-w")
    except Exception:                                   # noqa: BLE001
        rulings, prior = None, []
    def _take(instrument, label):
        ok, last = _r1(arm, as_of)
        if not ok:
            lines.append(f"  {label} REACHED - NOT READ (DP-3C-bb): the {last} close has not "
                         f"been log-verified (newest cohort {as_of}). Counts only; the next "
                         f"session's chain (scan, then review) reads and records it.")
            return
        rho = arm["rho"]
        lines.append(f"  {label}: rho = {rho:+.3f}  -> {arm['verdict']}"
                     if rho is not None else f"  {label} -> {arm['verdict']}")
        if record and rulings is not None:
            rulings.record_reading(
                instrument, as_of, arm["verdict"].startswith("POSITIVE"),
                detail=dict(verdict=arm["verdict"], rho=rho, n=arm["n_resolved"],
                            tickers=arm["tickers_resolved"], episodes=arm["episodes"],
                            verified_through=str(_r1(arm, as_of)[1])))
            lines.append(f"  reading recorded to the readings log as {instrument}; "
                         "later runs print it as recorded.")

    if prior:
        e = prior[0]
        lines.append(f"  READ on {e['date']} (recorded, not recomputed): "
                     f"{e['detail'].get('verdict')}  rho {e['detail'].get('rho')}  "
                     f"n {e['detail'].get('n')}")
        ex = _exit_record("DP-3C-w@exit")
        if ex:
            x = ex[0]
            lines.append(f"  EXIT READ on {x['date']} (recorded): {x['detail'].get('verdict')}  "
                         f"rho {x['detail'].get('rho')}  n {x['detail'].get('n')}")
        elif exit_read and arm["read_ready"]:
            _take("DP-3C-w@exit", "EXIT READ")
        elif exit_run:
            lines.append("  exit read: taken below under PHASE 3-C EXIT READS (gated, pinned to the cut)")
        else:
            lines.append("  exit read: not taken (run with --exit-read at the Phase 3-C exit "
                         "review; protected by DP-3C-bb)")
    elif exit_run:
        lines.append("  no first reading on the record; an exit run takes no first read "
                     "(the exit read below stops on this)")
    elif arm["read_ready"]:
        _take("DP-3C-w", "READ DATE")
    else:
        lines.append(f"  {arm['verdict']}")
    return lines


# --------------------------------------------------------------------------- #
# DP-3C-m episode coalescing
# --------------------------------------------------------------------------- #

def assign_episodes(rows: list[Actionable], cohort_dates: list[dt.date],
                    dropouts=None) -> None:
    """DP-3C-m: consecutive gate-clearing COHORT SESSIONS on one ticker are ONE
    episode. Adjacency is measured against the cohort calendar derived from the
    master itself -- never a holiday table and never a second source of truth,
    so a skipped session (holiday, 429, no run) cannot silently split an episode.

    AMENDED 2026-09-25 (DP-3C-ar): this function now CALLS episodes.coalesce()
    instead of carrying its own copy of the rule. Until today the registry kept
    a private implementation while KEEP-70 and DP-3C-w used the shared one --
    the exact two-definitions hazard episodes.py was written to remove. With
    dropouts=None the output is verified identical to the old code on the live
    master (16 episodes, same ids, same opening rows). With the DP-3C-ar
    dropout set, a run-fault gap for one ticker is bridged, not split.
    """
    import episodes
    for e in episodes.coalesce(rows, cohort_dates, ticker=lambda x: x.ticker,
                               date=lambda x: x.date, dropouts=dropouts):
        for x in e["rows"]:
            x.episode_id = e["id"]
            x.episode_open = x is e["open_row"]
        e["open_row"].bridged = list(e.get("bridged", []))


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
            hit5=head.hit5(), r5=head.r5, bridged=list(head.bridged),
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
    "until DP-3C-l is amended by a dated ruling. The EPISODE basis (DP-3C-m, "
    "opening row) is primary, as DP-3C-y ruled for KEEP-70; the ROW basis is "
    "shown beside it as descriptive. Executability and ChannelMargin are "
    "reported attributes and are never used to select a subset (DP-3C-u, "
    "DP-3C-af)."
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
           "Hit (5d)", "Hit (10d)", "Episode", "Opens Episode", "Risk Era",
           "Executability", "ChannelMargin", "Notes"]

A = {n: get_column_letter(i + 1) for i, n in enumerate(
    ["sigdate", "ticker", "acct", "sig", "conf", "gate", "margin", "dq", "p0",
     "d5", "d10", "p5", "p10", "r5", "r10", "hit5", "hit10", "epi", "epiopen",
     "era", "exec", "chan", "notes"])}

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
        cell(r, 21, x.executability, fill=fill, align="center", size=9)
        cell(r, 22, x.channel_margin,
             fill=(WARN_FILL if x.channel_margin.startswith("ERASED") else fill), size=9,
             bold=x.channel_margin.startswith("ERASED"))
        cell(r, 23, x.notes, fill=fill, size=9)
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
    cell(rr, 1, "BOTH BASES — EPISODE primary, ROW descriptive", bold=True,
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

def per_account_block(rows, eps):
    """DP-3C-av (pre-registered 2026-09-25). The per-account arm DP-3C-u's
    revisit condition required once PARTIAL passed 25% of post-era rows.

    POPULATION  post-era (>= 2026-08-11) admitted rows, EPISODE basis, scored on
                the opening row; one sub-population per account = episodes whose
                OPENING row was APPROVED in that account (verbatim PER-ACCOUNT
                field at signal time, never revised).
    READ        ONCE, at the Phase 3-C exit review, and only for an account with
                >= 10 resolved episodes. Below that: 'not readable'.
    STANDARD    DESCRIPTIVE. DP-3C-l's reading standard is NONE; this arm adds
                no bar and moves no gate. It is never pooled across accounts.
    BLIND       Until the exit read this block prints COUNTS ONLY -- no hit rate
                on any account subset, so no subset is chosen with outcomes in
                view (DP-3C-u's reason for forbidding executability filters).
    """
    post_eps = [e for e in eps if e["era"] == ERA_POST]
    heads = {x.episode_id: x for x in rows if x.episode_open}
    accts = sorted({a for x in rows if x.era == ERA_POST for a in x.per_account})
    out = ["| Account | post-era rows APPROVED | episodes opened APPROVED | of which resolved +5d | readable at exit (>= 10) |",
           "|---|---|---|---|---|"]
    for a in accts:
        nrow = sum(1 for x in rows if x.era == ERA_POST and x.per_account.get(a) == "APPROVED")
        opened = [e for e in post_eps if heads[e["episode_id"]].per_account.get(a) == "APPROVED"]
        res = [e for e in opened if e["hit5"] is not None]
        out.append(f"| {a} | {nrow} | {len(opened)} | {len(res)} | "
                   f"{'yes' if len(res) >= 10 else 'no'} |")
    nofield = sum(1 for e in post_eps if not heads[e["episode_id"]].per_account)
    out.append("")
    out.append(f"Post-era episodes whose opening row carries NO per-account field "
               f"(top-level verdict only, e.g. a SELL on an unheld name): {nofield} of "
               f"{len(post_eps)}. No hit rate is printed on any account subset before "
               f"the exit read (blind).")
    return out


DP3CAV_MIN = 10   # DP-3C-av: readable only with >= 10 resolved episodes per account
DP3CAV_INSTR = "DP-3C-av@exit"
DP3CW_INSTR = "DP-3C-w@exit"
EXIT_REQUIRED = ("build_actionable_registry.py", "episodes.py", "rulings.py", "trading_calendar.py",
                 "exit_read_guard.py", "outcome_sanity.py", "signal_logs.py", "trail_basis_audit.py",
                 "log_tracker_crosscheck.py", "e4_counter.py")


def _exit_record(instrument):
    """The first exit reading of `instrument`, from the authoritative exit file,
    else the shared log's mirror; [] if neither has it. Display only."""
    try:
        import rulings
    except ImportError:
        return []
    for p in (getattr(rulings, "EXIT_READINGS_PATH", None), rulings.READINGS_PATH):
        if p:
            got = rulings.readings(instrument, p)
            if got:
                return got
    return []


def log_coverage(logs_glob, cohort_dates):
    """(ok, detail): every master cohort since the DP-3C-t clock has its own
    dated signals log, so no episode or DP-3C-av row is silently missing."""
    import signal_logs
    import e4_counter as ec
    paths, _ = signal_logs.discover(logs_glob)
    have = set()
    for p in paths:
        m = _re.search(r"signals_(\d{4}-\d{2}-\d{2})\.log$", os.path.basename(p))
        if m:
            have.add(dt.date.fromisoformat(m.group(1)))
    missing = sorted(d for d in set(cohort_dates) if d >= ec.CLOCK_START and d not in have)
    if missing:
        return False, "no log for master cohort(s) " + ", ".join(map(str, missing[:8]))
    return True, "logs cover every master cohort since the clock"


def _hit_from_prices(x):
    """DP-3C-l's sign test from the PRICE columns (never column K's cache):
    BUY paid if Price +5d > Price at Signal, SELL if below. None until filled."""
    if not isinstance(x.p0, (int, float)) or not x.p0 or not isinstance(x.p5, (int, float)):
        return None
    r = (x.p5 - x.p0) / x.p0
    return (r > 0) if x.signal == "BUY" else (r < 0)


def _resolved_by_prices(x):
    return isinstance(x.p0, (int, float)) and bool(x.p0) and isinstance(x.p5, (int, float))


def av_exit_compute(rows, eps, through, counts_only=False):
    """DP-3C-av (pre-registered 2026-09-25), computed for the ONE exit read.
    Per account: post-era episodes whose OPENING row was APPROVED there,
    resolved when the opening row's +5d session (trading_calendar) is on or
    before `through` and its +5d price is filled. >= 10 resolved -> hit rate;
    else 'not readable'. Never pooled. Returns (detail, sessions); prints nothing.
    counts_only=True computes no hit at all (the blind count for gate 5)."""
    import trading_calendar as _tc
    heads = {x.episode_id: x for x in rows if x.episode_open}
    post = [e for e in eps if e["era"] == ERA_POST]
    accts = sorted({a for x in rows if x.era == ERA_POST for a in x.per_account})
    detail, sessions = {}, []
    for a in accts:
        opened = [e for e in post if heads[e["episode_id"]].per_account.get(a) == "APPROVED"]
        res = []
        for e in opened:
            h = heads[e["episode_id"]]
            d5 = _tc.shift_sessions(h.date, 5)
            if d5 <= through and _resolved_by_prices(h):
                res.append((e["episode_id"], None if counts_only else _hit_from_prices(h)))
                sessions.append(d5)
        if counts_only:
            detail[a] = dict(n=len(res), opened=len(opened))
        elif len(res) >= DP3CAV_MIN:
            hits = sum(1 for _, h in res if h)
            detail[a] = dict(readable=True, hits=hits, n=len(res), opened=len(opened),
                             episodes=[eid for eid, _ in res])
        else:
            detail[a] = dict(readable=False, n=len(res), opened=len(opened))
    nofield = sum(1 for e in post if not heads[e["episode_id"]].per_account)
    return dict(per_account=detail, no_field=nofield, post_episodes=len(post)), sessions


def w_exit_compute(master_rows, cohort_dates, through, dropouts):
    """DP-3C-w's once-more read at the exit, pinned: only +5d results whose
    session is on or before `through` count. Prints nothing."""
    import episodes
    import trading_calendar as _tc
    arm = episodes.dp3cw_arm(mask_resolved_through(master_rows, through), cohort_dates, dropouts=dropouts)
    sessions = [_tc.shift_sessions(d, 5) for d in arm.get("resolved_open_dates", [])]
    readable = arm["read_ready"]
    return dict(readable=readable, verdict=arm["verdict"], rho=arm["rho"] if readable else None,
                n=arm["n_resolved"], tickers=arm["tickers_resolved"], episodes=arm["episodes"]), sessions


def w_exit_counts(master_rows, cohort_dates, through, dropouts):
    """dp3cw_arm's population and coalescing, COUNTED: resolved opening rows at
    the cut and their +5d sessions. Never computes rho (gate 5 and gate 1)."""
    import episodes
    import trading_calendar as _tc
    rows = mask_resolved_through(master_rows, through)
    pop = [r for r in rows if r["date"] >= episodes.DP3CW_ERA_START and r.get("signal") == "BUY"
           and isinstance(r.get("conf"), (int, float)) and r["conf"] >= 60]
    eps_ = [e for e in episodes.coalesce(pop, cohort_dates, dropouts=dropouts)
            if e["opened"] >= episodes.DP3CW_OPENED]
    res = [e["open_row"] for e in eps_ if e["open_row"].get("ret5") is not None]
    return dict(n=len(res)), [_tc.shift_sessions(r["date"], 5) for r in res]


def exit_counts(w, av):
    """The counts gate 5 compares with rulings.EXIT_CUT['expected'] (counts only)."""
    out = dict(dp3cw_resolved=w["n"])
    for a, v in av["per_account"].items():
        out[f"dp3cav_{a}"] = v["n"]
    return out


def exit_lines(w, av, through, recorded_on=None):
    head = (f"  READ on {recorded_on} (recorded, not recomputed)" if recorded_on
            else "  READ (recorded and verified just now)")
    L = ["PHASE 3-C EXIT READS - DP-3C-w@exit and DP-3C-av@exit (pinned to rulings.EXIT_CUT)", head,
         f"  pinned: +5d results on opening rows whose +5d session is on or before {through}",
         "  DP-3C-w@exit: " + (f"rho = {w['rho']:+.3f} -> {w['verdict']}" if w.get("rho") is not None
                               else f"{w['verdict']}")
         + f"  (n {w['n']} resolved episodes; tickers {', '.join(w.get('tickers') or [])})"]
    for a, v in sorted(av["per_account"].items()):
        L.append(f"  DP-3C-av {a}: " + (f"{v['hits']}/{v['n']} = {v['hits'] / v['n']:.1%} of resolved episodes "
                                        f"paid at +5d (opened APPROVED {v['opened']})" if v["readable"]
                                        else f"not readable ({v['n']} resolved, fewer than {DP3CAV_MIN})"))
    L.append(f"  post-era episodes with no per-account field: {av['no_field']} of {av['post_episodes']}")
    L.append("  DP-3C-av is DESCRIPTIVE (DP-3C-l standard NONE); never pooled across accounts.")
    return L


def registry_exit_reads(tracker_copy, logs_glob, master_rows, cohort_dates, dropouts, rows, eps, snap=None,
                        readings_path=None, gates_fn=None, exit_path=None):
    """The two registry exit reads, taken together: compute both, gate, record
    both in ONE verified write, then return the lines to print. Returns
    (rc, lines). rc 0 = read and recorded (or already on record), 1 = a gate
    stopped it, 2 = could not record or an anomaly."""
    import exit_read_guard as guard
    import rulings
    cut = rulings.EXIT_CUT
    through = cut["episodes_resolved_through"]
    rp = readings_path or rulings.READINGS_PATH
    ep = exit_path or (rulings.EXIT_READINGS_PATH if readings_path is None
                       else os.path.join(os.path.dirname(rp), "exit_readings.json"))
    try:
        data = guard.load_readings_strict(rp)
        have = guard.load_exit_records([DP3CW_INSTR, DP3CAV_INSTR], [ep, rp])
    except (OSError, ValueError) as exc:
        return 2, [f"  [STOP] a readings file is unreadable ({exc}); nothing read"]
    hw, hav = bool(have.get(DP3CW_INSTR)), bool(have.get(DP3CAV_INSTR))
    if hw and hav:
        w, av = have[DP3CW_INSTR][0], have[DP3CAV_INSTR][0]
        return 0, exit_lines(w["detail"], av["detail"], through, recorded_on=w["date"])
    if hw != hav:
        return 2, [f"  [STOP] ANOMALY: only one of {DP3CW_INSTR} / {DP3CAV_INSTR} is recorded; nothing recomputed"]
    if not data.get("DP-3C-w"):
        return 1, ["  [STOP] DP-3C-w has no first reading on the record; the exit read is the ONCE-MORE read "
                   "(DP-3C-ah) and cannot be its first"]
    wc, ws = w_exit_counts(master_rows, cohort_dates, through, dropouts)
    avc, avs = av_exit_compute(rows, eps, through, counts_only=True)
    counts = exit_counts(wc, avc)
    as_of = cohort_dates[-1] if cohort_dates else None
    if gates_fn is None:
        import signal_logs
        paths, _ = signal_logs.discover(logs_glob)
        dated = [p for p in paths if _re.search(r"signals_\d{4}-\d{2}-\d{2}\.log$", os.path.basename(p))]
        newest_log = max(dated, key=os.path.basename) if dated else ""
        ok3, det3, blobs = guard.gate_git_strict(list(EXIT_REQUIRED))
        gates = [("0 run from the repo folder", *guard.gate_cwd()),
                 ("1 read protection (DP-3C-bb)", *guard.gate_read_protection(ws + avs, as_of)),
                 ("2 integrity (DP-3C-bm)", *guard.gate_integrity(tracker_copy, logs_glob, newest_log)),
                 ("3 committed code", ok3, det3),
                 ("4 not already read", *guard.gate_not_recorded([DP3CW_INSTR, DP3CAV_INSTR], [ep, rp])),
                 ("5 inputs as ruled", *guard.gate_inputs(dict(cut["expected_registry"]), counts,
                                                         *log_coverage(logs_glob, cohort_dates)))]
    else:
        gates, blobs = gates_fn(ws + avs, as_of, counts)
    lines = ["PHASE 3-C EXIT READS: gates"] + guard.gate_lines(gates)
    if not guard.all_ok(gates):
        return 1, lines + ["  EXIT READS NOT TAKEN: a gate stopped them. Counts only; nothing recorded."]
    w, ws2 = w_exit_compute(master_rows, cohort_dates, through, dropouts)
    av, avs2 = av_exit_compute(rows, eps, through)
    if (w["n"], sorted(ws2), sorted(avs2)) != (wc["n"], sorted(ws), sorted(avs)):
        return 2, lines + ["  [STOP] the read's population differs from the gated count; nothing recorded"]
    if snap is not None:
        okl, detl = guard.logs_unchanged(snap)
        if not okl:
            return 1, lines + [f"  EXIT READS NOT TAKEN: {detl}"]
    prov = dict(master_sha=snap["master_sha"] if snap else None, blobs=blobs, git_head=guard.git_head(),
                resolved_through=str(through))
    ok, msg = guard.record_exit({
        DP3CW_INSTR: (cut["review_date"], bool(w["readable"] and str(w["verdict"]).startswith("POSITIVE")),
                      dict(prov, **w, verified_through=str(max(ws)) if ws else None)),
        DP3CAV_INSTR: (cut["review_date"], False, dict(prov, **av, verified_through=str(max(avs)) if avs else None)),
    }, ep, rp)
    if not ok:
        return 2, lines + [f"  *** RECORDING FAILED: {msg}. Nothing shown, nothing recorded. ***"]
    return 0, lines + [""] + exit_lines(w, av, through) + [f"  {msg}"]


def selftest():
    """Synthetic data only: the cut mask, both exit computations, and the
    gate -> compute -> record -> show order of the exit reads."""
    import tempfile
    import shutil
    import exit_read_guard as guard
    fails = []

    def check(name, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")
        if not ok:
            fails.append(name)

    D = dt.date
    mr = [dict(date=D(2026, 10, 29), ticker="X", signal="BUY", conf=72, ret5=0.01),
          dict(date=D(2026, 10, 30), ticker="X", signal="BUY", conf=72, ret5=0.02)]
    m = mask_resolved_through(mr, D(2026, 11, 5))
    check("a +5d session on the cut counts (10-29 -> 11-05)", m[0]["ret5"], 0.01)
    check("a +5d session after the cut is masked (10-30 -> 11-06)", m[1]["ret5"], None)
    check("the mask never edits the caller's rows", mr[1]["ret5"], 0.02)

    class R:
        def __init__(s, eid, acct, p5, day, sig="BUY"):
            s.episode_id, s.episode_open, s.era, s.per_account = eid, True, ERA_POST, acct
            s.p0, s.p5, s.date, s.signal = 100.0, p5, day, sig

    rows, eps = [], []
    day = D(2026, 9, 14)
    for i in range(12):
        x = R(f"E{i}", {"Roth IRA": "APPROVED", "Individual": "APPROVED" if i < 9 else "REJECTED"},
              101.0 if i % 3 else 99.0, day)
        rows.append(x)
        eps.append(dict(episode_id=x.episode_id, era=ERA_POST))
        import trading_calendar as _tc
        day = _tc.next_session(day)
    late = R("LATE", {"Roth IRA": "APPROVED"}, 105.0, D(2026, 10, 30))
    rows.append(late)
    eps.append(dict(episode_id="LATE", era=ERA_POST))
    sell = R("S", {"Roth IRA": "APPROVED"}, 95.0, D(2026, 9, 15), sig="SELL")
    check("a SELL is paid when the price falls (sign test from prices)", _hit_from_prices(sell), True)
    av, avs = av_exit_compute(rows, eps, D(2026, 11, 5))
    check("Roth IRA readable at 12 resolved; the 10-30 episode is past the cut",
          (av["per_account"]["Roth IRA"]["readable"], av["per_account"]["Roth IRA"]["n"],
           av["per_account"]["Roth IRA"]["hits"]), (True, 12, 8))
    check("Individual not readable at 9", (av["per_account"]["Individual"]["readable"],
                                           av["per_account"]["Individual"]["n"]), (False, 9))

    tmp = tempfile.mkdtemp(prefix="bar_")
    try:
        rp = os.path.join(tmp, "r.json")
        w = dict(readable=True, verdict="NOT DECIDED", rho=-0.2, n=12, tickers=["A"], episodes=["E"])

        def run(gates_ok=True, prior_first=True):
            import rulings
            if prior_first and not guard.load_readings_strict(rp).get("DP-3C-w"):
                rulings.record_reading("DP-3C-w", D(2026, 10, 13), False, {"verdict": "first"}, path=rp)
            orig_w, orig_wc = globals()["w_exit_compute"], globals()["w_exit_counts"]
            orig_av = globals()["av_exit_compute"]
            globals()["w_exit_compute"] = lambda *a, **k: (w, [D(2026, 11, 5)])
            globals()["w_exit_counts"] = lambda *a, **k: (dict(n=w["n"]), [D(2026, 11, 5)])
            try:
                g = lambda s, a, c: ([("x", gates_ok, "")], {})
                return registry_exit_reads("m", os.path.join(tmp, "signals_*.log"), [], [D(2026, 11, 6)], set(),
                                           rows, eps, readings_path=rp, gates_fn=g)
            finally:
                globals()["w_exit_compute"], globals()["w_exit_counts"] = orig_w, orig_wc
                globals()["av_exit_compute"] = orig_av

        rc, lines = run(prior_first=False)
        check("no DP-3C-w first reading -> refused", (rc, any("no first reading" in ln for ln in lines)), (1, True))
        rc, lines = run(gates_ok=False)
        check("a stopped gate records nothing and shows no rate",
              (rc, "DP-3C-w@exit" in guard.load_readings_strict(rp), any("%" in ln for ln in lines)), (1, False, False))
        rc, lines = run()
        rec = guard.load_readings_strict(rp)
        ep = os.path.join(tmp, "exit_readings.json")
        xrec = guard.load_readings_strict(ep)
        check("gates pass -> BOTH exit reads recorded in one write, in the exit file and mirrored",
              (rc, DP3CW_INSTR in xrec, DP3CAV_INSTR in xrec, DP3CW_INSTR in rec, DP3CAV_INSTR in rec),
              (0, True, True, True, True))
        check("the result is shown only after the verified record", any("recorded and verified" in ln for ln in lines), True)
        rows[0].p5 = 50.0
        rc, lines = run()
        check("a second run prints the record and never recomputes",
              (rc, any("recorded, not recomputed" in ln for ln in lines),
               guard.load_readings_strict(rp)[DP3CAV_INSTR][0]["detail"]["per_account"]["Roth IRA"]["hits"]),
              (0, True, 8))
        import json
        import rulings
        rulings.record_reading("DP-3C-w", D(2026, 11, 9), False, {"verdict": "nightly"}, path=rp)
        check("a nightly write to the shared log keeps the exit mirror",
              DP3CW_INSTR in guard.load_readings_strict(rp), True)
        del rec[DP3CAV_INSTR], rec[DP3CW_INSTR]
        with open(rp, "w") as fh:
            json.dump(rec, fh)                              # the shared log loses both
        rc, lines = run()
        check("the exit file alone still answers: printed as recorded, never recomputed",
              (rc, any("recorded, not recomputed" in ln for ln in lines)), (0, True))
        x1 = guard.load_readings_strict(ep)
        del x1[DP3CAV_INSTR]
        with open(ep, "w") as fh:
            json.dump(x1, fh)
        rc, lines = run()
        check("only one of the pair on record -> ANOMALY, nothing recomputed", rc, 2)
        with open(ep, "w") as fh:
            fh.write("corrupt")
        rc, lines = run()
        check("a corrupt exit file stops the read", rc, 2)
        os.remove(ep)
        with open(rp, "w") as fh:
            fh.write("corrupt")
        rc, lines = run(prior_first=False)
        check("a corrupt readings log stops the read", rc, 2)
        # log coverage (gate 5) on dated log names only
        lg = os.path.join(tmp, "lg")
        os.makedirs(lg)
        for d in ("2026-11-04", "2026-11-05"):
            open(os.path.join(lg, f"signals_{d}.log"), "w").close()
        open(os.path.join(lg, "signals_2026-11-06_run1_coldstart.log"), "w").close()
        okc, detc = log_coverage(os.path.join(lg, "signals_*.log"),
                                 [D(2026, 8, 12), D(2026, 11, 4), D(2026, 11, 5), D(2026, 11, 6)])
        check("a cohort with only an undated log fails coverage; pre-clock dates are ignored",
              (okc, "2026-11-06" in detc, "2026-08-12" in detc), (False, True, False))
        okc2, _ = log_coverage(os.path.join(lg, "signals_*.log"), [D(2026, 11, 4), D(2026, 11, 5)])
        check("full coverage passes", okc2, True)
        # an exit run's nightly block neither records nor points at --exit-read
        bl = dp3cw_block([], [D(2026, 11, 6)], D(2026, 11, 6), record=False, exit_run=True)
        check("an exit run's nightly block does not say 'run with --exit-read'",
              any("run with --exit-read" in ln for ln in bl), False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("build_actionable_registry selftest (synthetic data only): "
          + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
    return 0 if not fails else 1


def write_markdown(rows, eps, md_path, tracker_path):
    rsum, es = summarize_rows(rows), summarize_episodes(eps)

    def hit_str(v):
        return "—" if v is None else ("YES" if v else "NO")

    tbl = [mdrow(["Date", "Tkr", "Sig", "Conf", "Gate", "Margin", "DQ", "Price",
                  "+5d Ret", "Hit 5d", "Episode", "Era", "Exec", "ChannelMargin"]),
           mdrow(["---"] * 14)]
    for x in rows:
        tbl.append(mdrow([
            f"{x.date:%Y-%m-%d}", x.ticker, x.signal, pct(x.conf),
            f"{x.gate:.0f}%", f"{x.margin:+.0f}" if x.margin else "**0**",
            x.dq, usd(x.p0),
            pct(x.r5, plus=True) if x.r5 is not None else "pending",
            hit_str(x.hit5()), x.episode_id + (" *(open)*" if x.episode_open else ""),
            x.era, x.executability,
            (f"**{x.channel_margin}**" if x.channel_margin.startswith("ERASED")
             else x.channel_margin or "—"),
        ]))

    etbl = [mdrow(["Episode", "Sig", "Opened", "Last", "Sessions", "Open conf",
                   "Open margin", "Hit 5d", "Era", "Bridged (DP-3C-ar)"]), mdrow(["---"] * 10)]
    for e in eps:
        etbl.append(mdrow([
            e["episode_id"], e["signal"], f"{e['opened']:%Y-%m-%d}",
            f"{e['last']:%Y-%m-%d}", str(e["sessions"]), pct(e["open_conf"]),
            f"{e['open_margin']:+.0f}" if e["open_margin"] else "**0**",
            hit_str(e["hit5"]), e["era"],
            ", ".join(f"{d:%Y-%m-%d}" for d in e.get("bridged", [])) or "—",
        ]))
    pa_lines = per_account_block(rows, eps)

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

## Per-account executability — DP-3C-av (pre-registered 2026-09-25; COUNTS ONLY until the exit read)

{chr(10).join(pa_lines)}
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
    post = [x for x in rows if x.era == ERA_POST]
    from collections import Counter as _C
    ec = _C(x.executability.split(" (")[0] for x in post)
    print(f"Executability, post-era rows (DP-3C-u; attribute, never a filter): "
          + ", ".join(f"{k} {v}" for k, v in sorted(ec.items())))
    if post:
        share = ec.get("PARTIAL", 0) / len(post)
        _avx = _exit_record(DP3CAV_INSTR)
        flag = (("  ** REVISIT CONDITION MET -- per-account scoring PRE-REGISTERED "
                 "2026-09-25 (DP-3C-av): " + (f"exit read recorded {_avx[0]['date']}" if _avx
                                               else "counts only until the exit read"))
                if share > 0.25 else "")
        print(f"  PARTIAL share {share*100:.1f}% of {len(post)} (revisit above 25%){flag}")
    for line in per_account_block(rows, eps):
        if line.startswith("| ") and not line.startswith("| Account"):
            c = [x.strip() for x in line.strip("|").split("|")]
            print(f"  DP-3C-av {c[0]:<12} rows APPROVED {c[1]:>3}   episodes opened "
                  f"APPROVED {c[2]:>3}   resolved {c[3]:>3}   readable at exit: {c[4]}")
    # ADDED 2026-11-07: after the exit, the recorded per-account read is printed as
    # recorded (never recomputed); the live counts above keep running beside it.
    _avx = _exit_record(DP3CAV_INSTR)
    if _avx:
        pa = (_avx[0].get("detail") or {}).get("per_account") or {}
        bits = []
        for acct in sorted(pa):
            v = pa[acct]
            bits.append(f"{acct} {v.get('hits')}/{v.get('n')} = {100 * v['hits'] / v['n']:.1f}%"
                        if v.get("readable") and v.get("n") else f"{acct} not readable ({v.get('n')})")
        print(f"  DP-3C-av EXIT READ {_avx[0]['date']} (recorded, not recomputed): " + "; ".join(bits))
    erased = [x for x in rows if x.channel_margin.startswith("ERASED")]
    if erased:
        print(f"ChannelMargin ERASED (DP-3C-af; admitted on D.op, blend would not clear): "
              + ", ".join(f"{x.ticker} {x.date:%m-%d}" for x in erased))
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
    check("every row carries an Executability value (from its log)",
          all(x.executability for x in rows))
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
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"),
                    help="signals logs, searched recursively (Executability, ChannelMargin)")
    ap.add_argument("--no-record", action="store_true",
                    help="do not write the DP-3C-w reading to the readings log")
    ap.add_argument("--exit-read", action="store_true",
                    help="take the Phase 3-C exit reads: DP-3C-w@exit and DP-3C-av@exit, "
                         "pinned to rulings.EXIT_CUT and gated (DP-3C-bb, -bl, -bn)")
    ap.add_argument("--selftest", action="store_true", help="synthetic tests of the exit-read code")
    args = ap.parse_args(argv)
    if args.selftest:
        sys.exit(selftest())
    if args.exit_read and args.no_record:
        print("ERROR: --exit-read cannot be combined with --no-record. A one-time read that is "
              "printed but not recorded is a look, not a read (DP-3C-bn i).")
        sys.exit(2)

    if not os.path.exists(args.tracker):
        sys.exit(f"ERROR: tracker not found: {args.tracker}")
    if os.path.basename(args.tracker).lower() == "tracker_with_registry.xlsx":
        sys.exit("ERROR: refusing to read the generated report copy as the "
                 "master. Pass logs\\claude_equity_bot_tracker.xlsx. (exit 2)")
    os.makedirs(args.out_dir, exist_ok=True)

    # AMENDED 2026-11-06 (DP-3C-bn): with --exit-read, every input is read from ONE
    # snapshot of the master, and the logs are hashed, so the recorded read is of
    # the bytes that were gated. Without --exit-read nothing changes.
    source, snap, work = args.tracker, None, None
    if args.exit_read:
        import tempfile
        import exit_read_guard as guard
        import signal_logs
        log_paths, _ = signal_logs.discover(os.path.abspath(args.logs))
        work = tempfile.mkdtemp(prefix="exit_read_registry_")
        try:
            snap = guard.snapshot(args.tracker, log_paths, work)
        except Exception:
            import shutil
            shutil.rmtree(work, ignore_errors=True)
            raise
        source = snap["master"]
    try:
        rc = _build(args, source, snap)
    finally:
        if work:                                   # the master copy never outlives the run
            import shutil
            shutil.rmtree(work, ignore_errors=True)
    sys.exit(rc)


def _build(args, source, snap):
    rows, cohort_dates = load_actionable(source)
    if not rows:
        print("No actionable directional signals found. Writing an EMPTY registry "
              "rather than exiting — an empty population is a real and reportable "
              "state for this instrument, unlike the near-miss registry.")
    master_rows = load_master_rows(source)
    dropouts = load_dropouts(args.logs, master_rows)
    assign_episodes(rows, cohort_dates, dropouts=dropouts)
    attach_log_fields(rows, load_log_fields(args.logs))
    eps = episode_view(rows)

    xlsx_path = os.path.join(args.out_dir, "actionable_registry.xlsx")
    md_path = os.path.join(args.out_dir, "actionable_registry.md")
    write_xlsx(rows, eps, xlsx_path, args.tracker)
    write_markdown(rows, eps, md_path, args.tracker)
    ok = console_digest(rows, eps, cohort_dates)
    print()
    if dropouts:
        print("DP-3C-ar run-fault dropouts (bridged, never split): "
              + ", ".join(f"{t} {d:%Y-%m-%d}" for t, d in sorted(dropouts, key=lambda z: (z[1], z[0]))))
    as_of = cohort_dates[-1] if cohort_dates else dt.date.today()
    # In an exit run the nightly block records nothing: the run writes only what
    # the gated exit reads write (exit-tool review, 2026-11-07).
    for line in dp3cw_block(master_rows, cohort_dates, as_of,
                            record=not args.no_record and not args.exit_read, dropouts=dropouts,
                            exit_run=args.exit_read):
        print(line)
    exit_rc = 0
    if args.exit_read:
        print()
        exit_rc, lines = registry_exit_reads(source, os.path.abspath(args.logs), master_rows, cohort_dates,
                                             dropouts, rows, eps, snap=snap)
        for line in lines:
            print(line)
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

    return max(exit_rc, 0 if ok else 2)


if __name__ == "__main__":
    main()
