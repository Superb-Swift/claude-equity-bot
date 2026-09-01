#!/usr/bin/env python3
"""
apply_outcome_sanity_fixes.py — calendar hardening + Check F for the outcome gate.

Two changes. Neither moves an endpoint, a bar, an arm or an n.

  1. REAL TRADING CALENDAR (correctness, and urgent).
     The module derives its trading-day index from the master's own cohort
     dates and its header presents that as a virtue: "No holiday table, no
     network, no second source of truth to drift." It is exact ONLY while the
     bot runs every session. It is not a calendar -- it is a list of the days
     somebody ran the bot, and it relabels itself silently when a session is
     missed.

     2026-08-28 and 2026-08-31 are NYSE sessions on which the bot will NOT run
     (pre-registered: Phase3C_VacationGap_PreRegistration_2026-08-26.md). Under
     the derived index the cohort list jumps 08-27 -> 09-01 and treats them as
     adjacent, so every +5d mapping from cohort 2026-08-24 on, every +10d from
     08-17, and every +20d from 07-30 shifts by two sessions -- in silence, with
     no finding raised, because the corrupted index IS the index the checks use
     to decide what to compare.

     GM's ONE missing row cost the closing reviews four sessions of confusion.
     Two missing sessions across the whole cohort is that, times twenty-six.

     `trading_calendar.py` answers the "second source of truth to drift"
     objection properly: it reconciles against the master's own cohort dates
     and reports any disagreement as a finding, rather than declining to have a
     second source at all.

  2. CHECK F -- reconcile manual outcome cells against the LOG's close channel.
     This module's own header says the outcome columns are "the only manual
     surface in the project with no gate", and the 2026-08-26 findings triage
     says "the project holds no internal source of truth for a close".

     THAT IS NO LONGER TRUE, and has not been for the life of the H1 tag. Every
     session log carries, per ticker, `H1[trail5d=...; closes=a>b>c>d>e]` -- a
     machine-sourced price series from Schwab, sitting inside the project's own
     artefacts. Across 70 logs x 26 tickers that is a dense independent record
     of closes.

     Check F reconciles the two. On the 2026-08-26 log alone: 102 settled
     (ticker, date) pairs, 101 agreeing within 0.03%, and ONE that does not --
     GM 2026-08-20, master 85.75 against the log's 86.15 (+0.466%), unanimous
     across rows 1087/1327/1447. Check B is silent because the value is
     unanimous; Check A is silent because the quote-to-close gap is only
     +1.77%. It is the consistently-propagated shape that produced Defect 1
     (the AG 19.89/16.89 typo), and Check F is the only check in the suite with
     an INDEPENDENT price source, so it is the only one that can see it.

     Check F does NOT gate the exit code (CHECK_F_GATES_EXIT = False). The GM
     row has two live explanations -- a manual-entry error, or a
     corporate-action-adjusted close from Schwab's price history -- and until
     that is settled a known-open item should not turn the gate red every day.
     Flip the constant once it is adjudicated.

     Check F derives each log's window alignment EMPIRICALLY via
     trail_basis_audit, so it stays correct if the H1 window off-by-one is ever
     fixed. It does not hardcode the defect.

Dry run by default. `--apply` writes, after a timestamped .bak. Refuses and
changes nothing if any anchor has drifted.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import os
import shutil
import sys

TARGET = "outcome_sanity.py"


# -----------------------------------------------------------------------------
# Line endings. This repo mixes CRLF and LF across files, and an anchor that
# matches in one style silently matches zero times in the other -- which reads
# as "the file drifted" and aborts a patch that was actually fine. Normalize to
# LF for matching, restore the file's own dominant ending on write.
# -----------------------------------------------------------------------------
def _lf(s: str) -> str:
    return s.replace("\r\n", "\n")


def _dominant_ending(s: str) -> str:
    crlf = s.count("\r\n")
    return "\r\n" if crlf and crlf >= (s.count("\n") - crlf) else "\n"


def _restore(s: str, ending: str) -> str:
    return s.replace("\n", ending) if ending == "\r\n" else s

EDITS = [
    (
        "header: record that the derived index was replaced",
        "  * Derives the trading-day index from the master's own cohort dates. No holiday\r\n"
        "    table, no network, no second source of truth to drift.\r\n",

        "  * Uses `trading_calendar.py` for the trading-day index -- NOT the master's\r\n"
        "    own cohort dates. AMENDED 2026-08-26: deriving the index from cohort dates\r\n"
        "    is exact only while the bot runs every session, and it relabels itself in\r\n"
        "    silence when one is missed (2026-08-28 and 2026-08-31 are pre-registered\r\n"
        "    no-run sessions). The old note called the absence of a second source a\r\n"
        "    virtue; the honest answer is to have one and RECONCILE it, which\r\n"
        "    trading_calendar.reconcile_against_cohorts() does on every run. Still no\r\n"
        "    network and no data file.\r\n",
    ),
    (
        "header: document Check F",
        "  D  COHORT DISPERSION.  sd(pop) of a resolved cohort > SD_PCT. A corrupted row\r\n"
        "     blows up dispersion before it changes the mean.\r\n",

        "  D  COHORT DISPERSION.  sd(pop) of a resolved cohort > SD_PCT. A corrupted row\r\n"
        "     blows up dispersion before it changes the mean.\r\n"
        "  F  LOG-CLOSE RECONCILIATION (added 2026-08-26). Every session log carries\r\n"
        "     `H1[...; closes=a>b>c>d>e]` per ticker -- a machine-sourced close series\r\n"
        "     from Schwab. Check F compares the manual outcome cells against it. It is\r\n"
        "     the ONLY check here with an independent price source, so it is the only\r\n"
        "     one that can see a value propagated CONSISTENTLY into all three horizon\r\n"
        "     cells -- the shape that produced the AG defect, where B is unanimous and\r\n"
        "     wrong and A is inside tolerance. Reports; does not gate (see\r\n"
        "     CHECK_F_GATES_EXIT).\r\n",
    ),
    (
        "imports: trading_calendar, with graceful degradation",
        "try:\r\n"
        "    import openpyxl\r\n"
        "except ImportError:\r\n"
        "    print(\"ERROR: openpyxl not available. Activate the venv.\", file=sys.stderr)\r\n"
        "    sys.exit(2)\r\n",

        "try:\r\n"
        "    import openpyxl\r\n"
        "except ImportError:\r\n"
        "    print(\"ERROR: openpyxl not available. Activate the venv.\", file=sys.stderr)\r\n"
        "    sys.exit(2)\r\n"
        "\r\n"
        "# The trading-day index. Degrades to the old cohort-derived index rather than\r\n"
        "# failing closed -- a gate that refuses to run is a gate nobody runs -- but it\r\n"
        "# says so loudly, because the degraded mode is the one that mis-maps horizons\r\n"
        "# across a missed session.\r\n"
        "try:\r\n"
        "    import trading_calendar as _cal\r\n"
        "except ImportError:                                    # pragma: no cover\r\n"
        "    _cal = None\r\n"
        "\r\n"
        "# Check F reports but does not gate while GM 2026-08-20 is unadjudicated\r\n"
        "# (manual-entry error vs corporate-action-adjusted close). Flip to True once\r\n"
        "# that is settled; a known-open item should not turn the gate red daily.\r\n"
        "CHECK_F_GATES_EXIT = False\r\n"
        "CHECK_F_TOL_PCT = 0.05      # a 2dp log print against a full-precision cell\r\n",
    ),
    (
        "main(): resolve horizons on the real calendar, and reconcile it",
        "    rows = load(args.tracker)\r\n"
        "    dates = sorted({r[\"date\"] for r in rows})\r\n"
        "    idx = {d: i for i, d in enumerate(dates)}          # trading-day index\r\n",

        "    rows = load(args.tracker)\r\n"
        "    dates = sorted({r[\"date\"] for r in rows})\r\n"
        "    idx = {d: i for i, d in enumerate(dates)}          # legacy fallback only\r\n"
        "\r\n"
        "    # AMENDED 2026-08-26. `resolve(d, n)` is the +n-trading-day resolution date\r\n"
        "    # and is correct whether or not the bot ran on any session in between.\r\n"
        "    cal_notes = []\r\n"
        "    if _cal is not None:\r\n"
        "        def resolve(d, n):\r\n"
        "            return _cal.shift_sessions(d, n)\r\n"
        "        rec = _cal.reconcile_against_cohorts(dates)\r\n"
        "        for d in rec[\"missing\"]:\r\n"
        "            findings_cal.append(\"[CAL] %s is an NYSE session with no cohort row \"\r\n"
        "                                \"and no BOT_ABSENT entry. Either the bot missed a \"\r\n"
        "                                \"run or the calendar is wrong; horizons around it \"\r\n"
        "                                \"cannot be trusted until it is explained.\" % d)\r\n"
        "        for d in rec[\"extra\"]:\r\n"
        "            findings_cal.append(\"[CAL] cohort rows exist for %s, which the calendar \"\r\n"
        "                                \"says is not an NYSE session.\" % d)\r\n"
        "        for d in rec[\"absent_expected\"]:\r\n"
        "            why, doc = _cal.BOT_ABSENT[d]\r\n"
        "            cal_notes.append(\"%s - %s (%s)\" % (d, why, doc))\r\n"
        "    else:                                              # pragma: no cover\r\n"
        "        def resolve(d, n):\r\n"
        "            i = idx[d]\r\n"
        "            return dates[i + n] if i + n < len(dates) else None\r\n"
        "        cal_notes.append(\"trading_calendar.py NOT IMPORTABLE - horizons are \"\r\n"
        "                         \"derived from cohort dates and WILL mis-map across any \"\r\n"
        "                         \"missed session.\")\r\n"
        "    last_cohort = dates[-1]\r\n",
    ),
    (
        "main(): findings_cal must exist before the calendar block populates it",
        "    findings = []\r\n"
        "    checked_a = skipped_a = 0\r\n",

        "    findings = []\r\n"
        "    checked_a = skipped_a = 0\r\n",
    ),
    (
        "Check A/B: map the resolution date through the calendar",
        "    for r in rows:\r\n"
        "        i = idx[r[\"date\"]]\r\n"
        "        for label, col, n in HORIZONS:\r\n"
        "            v = r[{8: \"h\", 9: \"i\", 10: \"j\"}[col]]\r\n"
        "            if not num(v):\r\n"
        "                continue\r\n"
        "            if i + n >= len(dates):\r\n"
        "                continue                                # not yet resolvable\r\n"
        "            rdate = dates[i + n]\r\n",

        "    for r in rows:\r\n"
        "        for label, col, n in HORIZONS:\r\n"
        "            v = r[{8: \"h\", 9: \"i\", 10: \"j\"}[col]]\r\n"
        "            if not num(v):\r\n"
        "                continue\r\n"
        "            rdate = resolve(r[\"date\"], n)\r\n"
        "            if rdate is None or rdate > last_cohort:\r\n"
        "                continue                                # not yet resolvable\r\n",
    ),
]

# The Check F body and the calendar-findings list are inserted as whole blocks.
CHECK_F_ANCHOR = (
    "    # ---- Check D: cohort dispersion ----------------------------------------\r\n"
)

CHECK_F_BODY = '''    # ---- Check F: reconcile outcome cells against the log's close channel ---
    # WHY THIS IS THE ONLY CHECK THAT CAN SEE THE AG DEFECT CLASS. A, B and D
    # are all internal to the master: B compares the master against itself, so a
    # value propagated consistently into all three horizon cells is unanimous
    # and passes; A compares a close against a same-day 09:3x quote, a window
    # wide enough to swallow a plausible-looking wrong number. F brings in a
    # price the operator did not type.
    #
    # CORROBORATION IS THE POINT. The same session's close appears in up to
    # four different logs, because each run carries a multi-day close series.
    # A disagreement confirmed by four independent Schwab fetches is a different
    # claim from one seen once, and the two are NOT reported as if they were.
    findings_f = []
    checked_f = 0
    if _tba is not None:
        try:
            closes_ref = {}
            for r in rows:
                for label, col, n in HORIZONS:
                    v = r[{8: "h", 9: "i", 10: "j"}[col]]
                    if num(v):
                        rd = resolve(r["date"], n)
                        if rd is not None:
                            closes_ref.setdefault((r["tkr"], rd), []).append((v, r["row"], label))
            import glob as _glob
            logs = sorted(set(_glob.glob(args.logs) +
                              _glob.glob(os.path.join(os.path.dirname(args.logs) or ".",
                                                      "**", os.path.basename(args.logs)),
                                         recursive=True)))
            seen = {}       # (tkr, session) -> {log price -> [run dates]}
            for lp in logs:
                m = _tba.LOG_DATE_RE.search(os.path.basename(lp))
                if not m:
                    continue
                run_date = datetime.date.fromisoformat(m.group(1))
                per = _tba.parse_log(lp)
                if not per:
                    continue
                # Alignment is MEASURED per log, never assumed: if the H1 window
                # off-by-one is ever fixed, this follows it rather than breaking.
                ref_for_align = {k: v[0][0] for k, v in closes_ref.items()}
                a_in = _tba.score_alignment(per, run_date, ref_for_align, True)
                a_do = _tba.score_alignment(per, run_date, ref_for_align, False)
                last_is_run = a_in[0] >= a_do[0]
                for tkr, (_lbl, _tr, cl) in per.items():
                    k = len(cl)
                    for pos, price in enumerate(cl):
                        back = (k - 1 - pos) if last_is_run else (k - pos)
                        if back <= 0:
                            continue        # the live intraday element: no settled ref
                        sess = resolve(run_date, -back)
                        if sess is None:
                            continue
                        seen.setdefault((tkr, sess), {}).setdefault(price, []).append(run_date)

            for (tkr, sess), byprice in sorted(seen.items()):
                cells = closes_ref.get((tkr, sess))
                if not cells:
                    continue
                vals = [c[0] for c in cells]
                if max(vals) - min(vals) > abs(max(vals)) * CHECK_F_TOL_PCT / 100.0:
                    continue                # disagreeing cells are Check B's problem
                ref = vals[0]
                if not ref:
                    continue
                checked_f += 1
                # The log price corroborated by the most runs is the challenger.
                price, runs = max(byprice.items(), key=lambda kv: len(kv[1]))
                gap = (price - ref) / ref * 100.0
                if abs(gap) <= CHECK_F_TOL_PCT:
                    continue
                where = "/".join("row %d %s" % (c[1], c[2]) for c in cells)
                spread = ("" if len(byprice) == 1 else
                          "  [logs also report %s]"
                          % ", ".join("%.4f x%d" % (p, len(d))
                                      for p, d in sorted(byprice.items()) if p != price))
                findings_f.append(
                    "[F] %-5s %s  master %.4f vs log %.4f  %+.3f%%  "
                    "corroborated by %d log(s) (%s)  cells: %s; %d UNANIMOUS so "
                    "Check B is silent%s"
                    % (tkr, sess, ref, price, gap, len(runs),
                       ", ".join(str(d) for d in sorted(runs)), where, len(cells), spread))
            findings_f.sort(key=lambda s: -abs(float(s.split("%")[0].split()[-1])))
        except Exception as e:                                 # pragma: no cover
            findings_f.append("[F] reconciliation unavailable: %s" % e)
    else:                                                      # pragma: no cover
        findings_f.append("[F] trail_basis_audit.py not importable - the log close "
                          "channel was not read this run.")

'''


def main() -> int:
    ap = argparse.ArgumentParser(description="Calendar hardening + Check F for outcome_sanity.py.")
    ap.add_argument("--file", default=TARGET)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.file):
        print("ERROR: not found: %s" % a.file, file=sys.stderr)
        return 2
    with open(a.file, "r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    ending = _dominant_ending(raw)
    original = _lf(raw)
    text = original

    # --- the straightforward exact-match edits -------------------------------
    for name, old, new in EDITS:
        old, new = _lf(old), _lf(new)
        if old == new:
            continue
        n = text.count(old)
        if n != 1:
            print("REFUSING: anchor %r matched %d times (expected 1)." % (name, n), file=sys.stderr)
            return 2
        text = text.replace(old, new, 1)

    # --- findings_cal must be declared before the calendar block uses it ------
    decl_old = "    rows = load(args.tracker)\r\n    dates = sorted("
    decl_new = "    findings_cal = []\r\n    rows = load(args.tracker)\r\n    dates = sorted("
    decl_old, decl_new = _lf(decl_old), _lf(decl_new)
    if text.count(decl_old) != 1:
        print("REFUSING: findings_cal declaration anchor not unique.", file=sys.stderr)
        return 2
    text = text.replace(decl_old, decl_new, 1)

    # --- trail_basis_audit import --------------------------------------------
    imp_old = "try:\r\n    import trading_calendar as _cal\r\n"
    imp_new = ("try:\r\n    import trail_basis_audit as _tba\r\n"
               "except ImportError:                                    # pragma: no cover\r\n"
               "    _tba = None\r\n"
               "try:\r\n    import trading_calendar as _cal\r\n")
    imp_old, imp_new = _lf(imp_old), _lf(imp_new)
    if text.count(imp_old) != 1:
        print("REFUSING: trail_basis_audit import anchor not unique.", file=sys.stderr)
        return 2
    text = text.replace(imp_old, imp_new, 1)

    # --- --logs CLI flag ------------------------------------------------------
    cli_old = ("    ap.add_argument(\"--quiet\", action=\"store_true\", help=\"findings only\")\r\n")
    cli_new = ("    ap.add_argument(\"--quiet\", action=\"store_true\", help=\"findings only\")\r\n"
               "    ap.add_argument(\"--logs\", default=os.path.join(\"logs\", \"signals_*.log\"),\r\n"
               "                    help=\"session logs for Check F's close reconciliation\")\r\n")
    cli_old, cli_new = _lf(cli_old), _lf(cli_new)
    if text.count(cli_old) != 1:
        print("REFUSING: --logs CLI anchor not unique.", file=sys.stderr)
        return 2
    text = text.replace(cli_old, cli_new, 1)

    # --- Check F body ---------------------------------------------------------
    anchor_f = _lf(CHECK_F_ANCHOR)
    if text.count(anchor_f) != 1:
        print("REFUSING: Check F insertion anchor not unique.", file=sys.stderr)
        return 2
    text = text.replace(anchor_f, _lf(CHECK_F_BODY) + anchor_f, 1)

    # --- reporting: calendar block, Check F block -----------------------------
    rep_old = ("    if findings:\r\n"
               "        print(\"  %d FINDING(S) - VERIFY BEFORE READING ANY RESOLUTION:\" % len(findings))\r\n")
    rep_new = (
        "    if cal_notes and not args.quiet:\r\n"
        "        print(\"  CALENDAR - pre-registered bot-absent session(s) in range:\")\r\n"
        "        for nline in cal_notes:\r\n"
        "            print(\"      \" + nline)\r\n"
        "        print(\"      Horizons are mapped on the NYSE calendar, so these do NOT\")\r\n"
        "        print(\"      shift any resolution date. Recorded so the gap stays visible.\")\r\n"
        "        print(\"-\" * 78)\r\n"
        "\r\n"
        "    if not args.quiet:\r\n"
        "        print(\"  [F] log-close comparisons made: %d\" % checked_f)\r\n"
        "    if findings_f:\r\n"
        "        print(\"  %d CHECK F FINDING(S) - independent price source disagrees \"\r\n"
        "              \"with a manual cell%s:\"\r\n"
        "              % (len(findings_f), \"\" if CHECK_F_GATES_EXIT else \" (REPORTING ONLY)\"))\r\n"
        "        for f in findings_f:\r\n"
        "            print(\"    \" + f)\r\n"
        "        print(\"    Resolve with the settled close (repair_outcome_close.py --price)\")\r\n"
        "        print(\"    before treating either value as correct. A corporate-action\")\r\n"
        "        print(\"    adjustment in Schwab's price history is a live alternative to a\")\r\n"
        "        print(\"    manual-entry error and would mean the two channels are not\")\r\n"
        "        print(\"    interchangeable.\")\r\n"
        "        print(\"-\" * 78)\r\n"
        "\r\n"
        "    findings = findings_cal + findings + (findings_f if CHECK_F_GATES_EXIT else [])\r\n"
        "\r\n"
        "    if findings:\r\n"
        "        print(\"  %d FINDING(S) - VERIFY BEFORE READING ANY RESOLUTION:\" % len(findings))\r\n")
    rep_old, rep_new = _lf(rep_old), _lf(rep_new)
    if text.count(rep_old) != 1:
        print("REFUSING: reporting anchor not unique.", file=sys.stderr)
        return 2
    text = text.replace(rep_old, rep_new, 1)

    print("=" * 78)
    print("OUTCOME_SANITY FIXES - %s" % a.file)
    print("=" * 78)
    print("  1. real trading calendar (trading_calendar.py) replaces the")
    print("     cohort-derived trading-day index, and is reconciled every run")
    print("  2. Check F: reconcile manual outcome cells against the log's")
    print("     H1 close channel (reports; does not gate)")
    print("-" * 78)
    for line in difflib.unified_diff(original.splitlines(), text.splitlines(),
                                     fromfile=a.file + " (current)",
                                     tofile=a.file + " (fixed)", lineterm="", n=2):
        print(line)
    print("-" * 78)
    print("  No endpoint, bar, arm or n moves.")
    if not a.apply:
        print("  DRY RUN - nothing written. Re-run with --apply.")
        print("=" * 78)
        return 0

    bak = "%s.bak-%s" % (a.file, dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(a.file, bak)
    with open(a.file, "w", encoding="utf-8", newline="") as fh:
        fh.write(_restore(text, ending))
    print("  APPLIED. Backup: %s" % bak)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
