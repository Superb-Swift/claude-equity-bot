#!/usr/bin/env python3
"""
damper_rebase_table.py - DP-3C-aw's before/after table, for the Phase 3-C exit review.

WHAT DP-3C-aw PRE-REGISTERED (claude/Phase3C_Rulings_2026-09-25.md)
    Candidate change: the D1 damper's trailing move becomes the SIGNAL-TIME move,
        quote(D) / close(D-5) - 1,
    the run-time equivalent of G1's ruled basis (DP-3C-an), so the damper and
    the gate that judges it read one series. Today (D2, since 2026-08-31) the
    damper reads close(D-1) / close(D-5) - 1: the H1 trace's five completed
    closes, newest over oldest.
    Evidence required at the exit review: a before/after table of damping
    decisions over EVERY D2 row, with the WMT 2026-07-23..08-26 window shown
    separately; disagreement counts in both directions, and the rows at FLOOR.
    Adoption only by a dated ruling at the exit. Nothing changes before it.
    DP-3C-bo (2026-11-06): the table is built for the exit review.

WHAT THIS TOOL DOES, AND DOES NOT
    It re-applies risk_engine.damp_confidence_value (the one definition of the
    damper, THETA/K/CAP/FLOOR unchanged) to each logged raw confidence under
    both trailing moves, and counts where the decisions differ. It uses no
    outcome of the rows it compares (no return or hit of any row). The only
    master values it reads are earlier closes, as the D-5 reference price for
    D1 rows and as a cross-check of the H1 trace on D2 rows. It changes nothing
    the bot does. "Damped" means damp > 0 (a sub-floor raw can carry damp > 0
    and be left unchanged by the floor rule; such rows are listed at FLOOR).
    COMPLETENESS (2026-11-06 review): every Signal JSON line on a D2 log is
    counted; a line that cannot be parsed is listed, never dropped silently.
    Before: the logged D[raw; op; trail; damp] (checked against the rule).
    After:  the same rule on quote(D) / close(D-5) - 1, with quote(D) = the
            row's lastPrice and close(D-5) = the H1 trace's oldest close on a
            D2 log (cross-checked against the master), or the master's
            recorded close for D-5 on a D1 log (the WMT window).
    Rows run through rulings.EXIT_CUT["review_date"].

USAGE
    python damper_rebase_table.py [--tracker logs\\claude_equity_bot_tracker.xlsx]
                                  [--logs "logs\\signals_*.log"] [--md FILE]
    python damper_rebase_table.py --selftest

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import trading_calendar as cal   # noqa: E402

H1_RE = re.compile(r"H1\[trail(\d+)d=([-+0-9.]+)%;\s*closes=([0-9.>]+)\]")
D_RE = re.compile(r"D\[raw=(\d+);\s*op=(\d+);\s*trail=([-+0-9.]+)%;\s*damp=(\d+)\]")
LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")
WMT_WINDOW = (dt.date(2026, 7, 23), dt.date(2026, 8, 26))
GATE = {"BUY": 70, "SELL": 65}
MATCH_TOL = 0.0051          # the log's 2dp print, as Check F


def load_rows(pattern, dropped=None):
    """One dict per Signal JSON line with a D tag (and, on a D2 log, an H1
    tag). Lines that cannot be parsed go to `dropped` as (date, reason, text)."""
    import signal_logs
    paths, _ = signal_logs.discover(pattern)
    dec = json.JSONDecoder()
    out = []
    dropped = dropped if dropped is not None else []
    for p in paths:
        m = LOGDATE.search(os.path.basename(p))
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                i = line.find("Signal JSON: ")
                if i < 0:
                    continue
                tail = line[i + 13:]
                try:
                    j, end = dec.raw_decode(tail)
                except ValueError:
                    dropped.append((d, "signal JSON did not decode", line[:120].strip()))
                    continue
                rest = tail[end:]
                pv = j.get("prompt_variant") or ""
                h, dd = H1_RE.search(rest), D_RE.search(rest)
                if not dd:
                    dropped.append((d, f"{j.get('ticker')}: no D tag", ""))
                    continue
                if not h and "S1D2" in pv:
                    dropped.append((d, f"{j.get('ticker')}: D2 row with no H1 tag", ""))
                    continue
                out.append(dict(d=d, tk=j.get("ticker"), sig=str(j.get("signal") or "").upper(),
                                pv=pv, quote=j.get("lastPrice"),
                                closes=[float(x) for x in h.group(3).split(">")] if h else None,
                                raw=int(dd.group(1)), op=int(dd.group(2)),
                                trail=float(dd.group(3)), damp=int(dd.group(4))))
    return out


def keep_dropped(dropped, d2d, through):
    """The unparsed lines this table must list: every one on a D2 log, and on a
    WMT-window date every WMT line AND every line whose JSON did not decode (its
    ticker cannot be known, so it may be WMT's)."""
    def wmt_day(d):
        return WMT_WINDOW[0] <= d <= WMT_WINDOW[1]
    return [x for x in dropped if x[0] <= through and
            (x[0] in d2d or (wmt_day(x[0]) and (x[1].startswith("WMT") or x[1] == "signal JSON did not decode")))]


def d2_logs(pattern, through):
    """{date: number of Signal JSON lines} for every log that carries a D2 row:
    the denominator, counted by line so an unparseable line still counts."""
    import signal_logs
    paths, _ = signal_logs.discover(pattern)
    out = {}
    for p in paths:
        m = LOGDATE.search(os.path.basename(p))
        if not m or dt.date.fromisoformat(m.group(1)) > through:
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = [ln for ln in fh if "Signal JSON: " in ln]
        if any("S1D2" in ln for ln in lines):
            out[dt.date.fromisoformat(m.group(1))] = len(lines)
    return out


def count_d2_lines(pattern, through):
    return sum(d2_logs(pattern, through).values())


def master_closes(path):
    """{(ticker, session): close} from the master's own outcome columns:
    Price +5d / +10d / +20d of cohort c are the closes of c+5 / c+10 / c+20."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    ws = wb["Signals"]
    out = {}
    for r in ws.iter_rows(min_row=5, max_col=10, values_only=True):
        if not r or not isinstance(r[0], dt.datetime) or not r[1]:
            continue
        c, tk = r[0].date(), str(r[1]).strip()
        for col, n in ((7, 5), (8, 10), (9, 20)):
            v = r[col]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.setdefault((tk, cal.shift_sessions(c, n)), float(v))
    wb.close()
    return out


def is_d2(r):
    return "S1D2" in r["pv"]


def candidate(r, closes_ref):
    """(trail % on quote(D)/close(D-5) - 1, source note) or (None, why)."""
    q = r["quote"]
    if not isinstance(q, (int, float)) or q <= 0:
        return None, "no quote"
    d5 = cal.shift_sessions(r["d"], -5)
    ref = closes_ref.get((r["tk"], d5))
    if is_d2(r):
        if not r["closes"]:
            return None, "D2 row with no H1 closes"
        c0 = r["closes"][0]
        if ref is not None and abs(c0 - ref) > MATCH_TOL:
            note = f"H1 oldest {c0} vs master {ref}"
        else:
            note = "H1 oldest close"
        return (q / c0 - 1.0) * 100.0, note
    if ref is None:
        return None, f"no master close for {d5}"
    return (q / ref - 1.0) * 100.0, "master close"


def classify(rows, closes_ref):
    import risk_engine as re_
    out = []
    for r in rows:
        chk_op, chk_damp = re_.damp_confidence_value(r["raw"], r["sig"], r["trail"])
        cand, note = candidate(r, closes_ref)
        if cand is None:
            out.append(dict(r, cand=None, note=note, op2=None, damp2=None, rule_ok=(chk_op, chk_damp) == (r["op"], r["damp"])))
            continue
        op2, damp2 = re_.damp_confidence_value(r["raw"], r["sig"], cand)
        out.append(dict(r, cand=cand, note=note, op2=op2, damp2=damp2,
                        rule_ok=(chk_op, chk_damp) == (r["op"], r["damp"])))
    return out


def summary(xs):
    import risk_engine as re_
    fl = re_.DampingConfig.FLOOR
    ok = [x for x in xs if x["cand"] is not None]
    c = Counter()
    for x in ok:
        b, a = x["damp"] > 0, x["damp2"] > 0
        c["both"] += b and a
        c["before only"] += b and not a
        c["after only"] += a and not b
        c["neither"] += not a and not b
        if b and a:
            c["more after"] += x["damp2"] > x["damp"]
            c["less after"] += x["damp2"] < x["damp"]
            c["same"] += x["damp2"] == x["damp"]
        c["FLOOR before"] += b and x["op"] == fl and x["raw"] > fl
        c["FLOOR after"] += a and x["op2"] == fl and x["raw"] > fl
        g = GATE.get(x["sig"])
        if g:
            c["admitted before only"] += x["op"] >= g and x["op2"] < g
            c["admitted after only"] += x["op2"] >= g and x["op"] < g
    return len(xs), len(ok), c


def render(d2, wmt, through, d2_lines=None, dropped=(), since=None):
    import risk_engine as re_
    cfg = re_.DampingConfig
    title = (f"# DP-3C-aw - damper re-basing: before/after table (rows through {through})" if since is None
             else f"# DP-3C-aw SHADOW (DP-3C-bs) - re-based damper, rows {since} through {through}")
    L = [title, "",
         f"*THETA {cfg.THETA}%, K {cfg.K}, CAP {cfg.CAP}, FLOOR {cfg.FLOOR} (risk_engine.DampingConfig, "
         "unchanged). Before = the logged D tag, close(D-1)/close(D-5) - 1. After = the same rule on "
         "quote(D)/close(D-5) - 1. Reads no outcome. Descriptive; adoption is a dated ruling at the exit "
         "(DP-3C-aw). Uses no outcome of the rows it compares. Advisory-only - no orders - not financial advice.*", ""]
    if since is not None:
        L += ["*SHADOW: DP-3C-bs (2026-11-07) adopted the re-based rule effective at the first Phase 4b "
              "go-live. Until then it reaches no gate, paste or daily view; the operative damp is the logged "
              "D tag ('before').*", ""]
    if d2_lines is not None:
        L += [f"**Completeness: {len(d2)} D2 rows parsed of {d2_lines} D2 Signal JSON lines in the logs"
              + (" - COMPLETE.**" if len(d2) == d2_lines else f" - **INCOMPLETE: {d2_lines - len(d2)} missing.**"), ""]
    if dropped:
        L += [f"Lines not parsed ({len(dropped)}):", ""] + [f"- {d} {why} {txt}" for d, why, txt in dropped] + [""]
    for title, xs in (("Every D2 row", d2), ("WMT 2026-07-23..08-26 (D1 window), shown separately", wmt)):
        n, nok, c = summary(xs)
        L += [f"## {title}", "",
              f"Rows {n}; candidate computable on {nok}. Logged D tag matches the rule on "
              f"{sum(x['rule_ok'] for x in xs)} of {n}.", "",
              "| Decision | Rows |", "|---|---|"]
        for k in ("neither", "both", "before only", "after only", "more after", "less after", "same",
                  "FLOOR before", "FLOOR after", "admitted before only", "admitted after only"):
            L.append(f"| {k} | {c[k]} |")
        diff = [x for x in xs if x["cand"] is not None and (x["damp"] != x["damp2"])]
        L += ["", f"Rows where the damp differs ({len(diff)}):", "",
              "| Date | Ticker | Signal | raw | trail before | trail after | damp before | damp after | op before | op after | note |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in sorted(diff, key=lambda x: (x["d"], x["tk"])):
            L.append(f"| {x['d']} | {x['tk']} | {x['sig']} | {x['raw']} | {x['trail']:+.2f}% | {x['cand']:+.2f}% | "
                     f"{x['damp']} | {x['damp2']} | {x['op']} | {x['op2']} | {x['note']} |")
        mism = [x for x in xs if "vs master" in x["note"]]
        L.append("")
        L.append(f"H1 oldest close vs the master's close for D-5: {len(mism)} disagreement(s) of "
                 f"{sum(1 for x in xs if is_d2(x))} D2 rows.")
        floor = [x for x in xs if x["cand"] is not None and x["raw"] > re_.DampingConfig.FLOOR
                 and (x["op"] == re_.DampingConfig.FLOOR or x["op2"] == re_.DampingConfig.FLOOR)
                 and (x["damp"] > 0 or x["damp2"] > 0)]
        if floor:
            L += ["", f"Rows at FLOOR before or after ({len(floor)}):", "",
                  "| Date | Ticker | raw | op before | op after |", "|---|---|---|---|---|"]
            L += [f"| {x['d']} | {x['tk']} | {x['raw']} | {x['op']} | {x['op2']} |"
                  for x in sorted(floor, key=lambda x: (x["d"], x["tk"]))]
        miss = [x for x in xs if x["cand"] is None]
        if miss:
            L.append("")
            L.append("Not computable: " + "; ".join(f"{x['tk']} {x['d']} ({x['note']})" for x in miss))
        L.append("")
    L.append("*Advisory-only - no orders - not financial advice.*")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="DP-3C-aw before/after damper table.")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"))
    ap.add_argument("--md", default=None)
    ap.add_argument("--through", default=None,
                    help="last signal date (YYYY-MM-DD). Default: the exit-review date "
                         "(rulings.EXIT_CUT). ADDED 2026-11-07: DP-3C-bs keeps the re-based damper "
                         "as an offline SHADOW until the 4b go-live; re-run with a later date to "
                         "extend the table. Reads no outcome")
    ap.add_argument("--since", default=None,
                    help="first signal date to tabulate (default: every D2 row). Use the first "
                         "Phase 4a session (2026-11-09) for the shadow's live rows")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if os.path.basename(a.tracker).lower() == "tracker_with_registry.xlsx":
        print("refused: read THE MASTER, not the generated report copy")
        return 2
    import rulings
    through = (dt.date.fromisoformat(a.through) if a.through else rulings.EXIT_CUT["review_date"])
    since = dt.date.fromisoformat(a.since) if a.since else None
    dropped = []
    rows = [r for r in load_rows(a.logs, dropped) if r["d"] <= through and (since is None or r["d"] >= since)]
    d2d = {d: n for d, n in d2_logs(a.logs, through).items() if since is None or d >= since}
    # Only the lines this table needs: every line on a D2 log, and WMT in its window.
    # (Logs from before the D tag existed are not part of DP-3C-aw.)
    dropped = keep_dropped(dropped, d2d, through)
    ref = master_closes(a.tracker)
    xs = classify(rows, ref)
    d2 = [x for x in xs if is_d2(x)]
    wmt = [x for x in xs if x["tk"] == "WMT" and WMT_WINDOW[0] <= x["d"] <= WMT_WINDOW[1]]
    n_d2 = sum(d2d.values())
    text = render(d2, wmt, through, d2_lines=n_d2, dropped=dropped, since=since)
    md = a.md or (f"damper_rebase_table_{through}.md" if since is None
                  else f"damper_shadow_{since}_{through}.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)
    print(f"\nWrote {md}")
    return 0


def selftest():
    import risk_engine as re_
    fails = []

    def check(name, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")
        if not ok:
            fails.append(name)

    D = dt.date
    d = D(2026, 11, 6)
    base = dict(d=d, tk="PWR", sig="BUY", pv="A-S1D2-B1-E1", quote=520.0,
                closes=[620.73, 621.18, 657.00, 580.44, 509.06], raw=68, op=53, trail=-17.99, damp=15)
    xs = classify([base], {})
    check("the logged D tag reproduces under the rule", xs[0]["rule_ok"], True)
    check("after = quote(D)/close(D-5) - 1 on the H1 oldest close", round(xs[0]["cand"], 4),
          round((520.0 / 620.73 - 1) * 100, 4))
    check("after re-applies the same rule", (xs[0]["op2"], xs[0]["damp2"]),
          re_.damp_confidence_value(68, "BUY", (520.0 / 620.73 - 1) * 100))
    # a row that damps before but not after (quote recovered above THETA)
    rec = dict(base, quote=600.0)
    n, nok, c = summary(classify([rec], {}))
    check("before-only damping is counted", (c["before only"], c["after only"]), (1, 0))
    # a row that does not damp before but does after
    up = dict(base, closes=[620.0, 615.0, 612.0, 611.0, 600.0], trail=-3.23, op=68, damp=0, quote=570.0)
    n, nok, c = summary(classify([up], {}))
    check("after-only damping is counted", (c["before only"], c["after only"]), (0, 1))
    check("a BUY already under its gate cannot lose admission", c["admitted before only"], 0)
    gate = dict(base, raw=78, op=78, damp=0, trail=-3.0, closes=[100.0, 99, 98, 97, 97.0], quote=85.0)
    n, nok, c = summary(classify([gate], {}))
    check("a BUY pushed under 70 by the new trail is admitted-before-only", c["admitted before only"], 1)
    # D1 row: needs the master close for D-5; absent -> not computable, never guessed
    d1 = dict(base, pv="A-S1D1-B1", d=D(2026, 8, 3))
    xs = classify([d1], {})
    check("a D1 row with no master close is not computable", xs[0]["cand"], None)
    ref = {("PWR", cal.shift_sessions(D(2026, 8, 3), -5)): 600.0}
    xs = classify([d1], ref)
    check("a D1 row uses the master close for D-5", round(xs[0]["cand"], 4), round((520.0 / 600.0 - 1) * 100, 4))
    # FLOOR rows: raw 45, heavy adverse move -> op clamps to 35
    fl = dict(base, raw=45, op=35, damp=15, trail=-20.0, quote=480.0)
    n, nok, c = summary(classify([fl], {}))
    check("a row at FLOOR before and after is counted both ways", (c["FLOOR before"], c["FLOOR after"]), (1, 1))
    # a wrongly logged D tag is reported, not trusted
    bad = dict(base, op=60)
    check("a D tag that does not match the rule is flagged", classify([bad], {})[0]["rule_ok"], False)
    txt = render(classify([base, rec], {}), [], D(2026, 11, 7), d2_lines=3, dropped=[(d, "x: no D tag", "")])
    check("the table states it uses no outcome", "Uses no outcome" in txt, True)
    check("an incomplete parse is stated, not hidden", "INCOMPLETE: 1 missing" in txt, True)
    check("a dropped line is listed", "x: no D tag" in txt, True)
    # real-format lines (copied from the 2026-11-06 log's layout), parsed end to end
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp(prefix="drt_")
    try:
        lp = os.path.join(tmp, "signals_2026-11-06.log")
        with open(lp, "w", encoding="utf-8") as fh:
            fh.write('2026-11-06 09:46:20,382 | INFO | Signal JSON: {"ticker": "PWR", "signal": "BUY", "confidence": 53, '
                     '"confidence_raw": 68, "lastPrice": 520.0, "prompt_variant": "A-S1D2-B1-E1"} | [PHASE 3-C DRY RUN] '
                     '[Roth IRA] [HELD] PWR | Signal: BUY | Confidence: 53% | H1[trail5d=-17.99%; '
                     'closes=620.73>621.18>657.00>580.44>509.06] | S1[prior=68,68,72,62,58; dconf=-10] | '
                     'D[raw=68; op=53; trail=-17.99%; damp=15] | B[sec=-0.401] | E[8k=1@2026-10-29]\n')
            fh.write('2026-11-06 09:47:00,000 | INFO | Signal JSON: {"ticker": "WMT", "signal": "HOLD", "confidence": 60, '
                     '"lastPrice": 125.0, "prompt_variant": "A-S1D2-B1-E1"} | WMT | S1[prior=52] | B[sec=0.9]\n')
            fh.write('2026-11-06 09:48:00,000 | INFO | Signal JSON: {"ticker": "GM", "signal": "HOLD" BROKEN\n')
        lp1 = os.path.join(tmp, "signals_2026-08-03.log")
        with open(lp1, "w", encoding="utf-8") as fh:
            fh.write('2026-08-03 09:46:20,382 | INFO | Signal JSON: {"ticker": "WMT", "signal": "HOLD", "confidence": 60, '
                     '"confidence_raw": 60, "lastPrice": 98.0, "prompt_variant": "A-S1D1-B1"} | WMT | '
                     'D[raw=60; op=60; trail=+1.00%; damp=0]\n')
        dr = []
        got = load_rows(os.path.join(tmp, "signals_*.log"), dr)
        check("a real-format D2 line parses (raw, op, damp, closes)",
              [(r["tk"], r["raw"], r["op"], r["damp"], r["closes"][0] if r["closes"] else None) for r in got
               if r["tk"] == "PWR"], [("PWR", 68, 53, 15, 620.73)])
        check("a D1 row parses without an H1 tag", [r["tk"] for r in got if r["d"] == D(2026, 8, 3)], ["WMT"])
        check("every unparsed line is reported, none dropped silently", len(dr), 2)
        kd = keep_dropped([(D(2026, 8, 3), "signal JSON did not decode", "x"), (D(2026, 8, 3), "GM: no D tag", ""),
                           (D(2026, 8, 3), "WMT: no D tag", ""), (D(2026, 9, 3), "signal JSON did not decode", "y")],
                          {}, D(2026, 11, 7))
        check("a WMT-window decode failure is listed; other tickers' and out-of-window lines are not",
              [x[1] for x in kd], ["signal JSON did not decode", "WMT: no D tag"])
        check("a shadow run is titled and labelled as the DP-3C-bs shadow",
              "SHADOW (DP-3C-bs)" in render([], [], D(2026, 11, 13), since=D(2026, 11, 9)), True)
        check("the report copy is refused in any letter case",
              main(["--tracker", os.path.join(tmp, "Tracker_With_Registry.XLSX")]), 2)
        check("the D2 denominator counts every D2 Signal JSON line",
              count_d2_lines(os.path.join(tmp, "signals_*.log"), D(2026, 11, 7)), 3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("damper_rebase_table selftest (synthetic data only): " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
