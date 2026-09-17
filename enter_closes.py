#!/usr/bin/env python3
"""
enter_closes.py — fill the master's outcome closes for ONE settled session, by machine.

WHY THIS EXISTS (DP-3C-ag, 2026-09-16; triage Action 8, open since 2026-08-26)
    Every +5d/+10d/+20d close in the master was typed by hand. On 2026-09-16
    one entry mistake put closes into the wrong cohorts (26 Check B findings)
    and wrote 80 cells for 2026-09-17 and 2026-09-18, sessions that had not
    happened yet. The 2026-09-15 MSFT +20d cell held a post-close quote
    (497.12) instead of the close (496.914) and passed every check.

    The remedy recorded on 2026-08-26 was to put `market_settled()` in the
    ENTRY path, not only the repair path. This is that entry path:

      * it locates cells by RESOLUTION DATE on the NYSE calendar, so a
        bot-absent session (2026-08-28, 2026-08-31) cannot shift anything;
      * it refuses any session that has not settled (16:15 ET rule), so a
        future or in-progress close cannot be written;
      * it fills BLANK cells only. A filled cell that disagrees with the
        sourced close is reported and left for repair_outcome_close.py,
        because overwriting is a repair and repairs are decided one at a time;
      * it writes through repair_outcome_close.write_edits(): backup first,
        cell-scoped XML surgery (cached values survive), fullCalcOnLoad, and
        one ledger line per cell in logs/outcome_close_repairs.log.

    Manual typing remains possible. It is no longer the only way, and
    outcome_sanity.py now blocks on the failure it produced (Check G).

SOURCES
    default          Schwab daily candles (one fetch per ticker)
    --closes-csv F   a file with columns ticker,close (e.g. fetch_closes.py
                     output, or a statement); used for offline entry and tests

GUARDS (a ticker that fails any is skipped and named; --force overrides 2-3)
    1. the session is an NYSE session and has settled
    2. the close is within 12% of that ticker's Px@signal on the session
       (a morning quote; a wide guard, it catches digit errors, not noise)
    3. where a session log already carries this close (the NEXT session's
       H1 trace, 2dp), the two agree within 0.0051

USAGE
    python enter_closes.py                         # last settled session, dry run
    python enter_closes.py --date 2026-09-16       # dry run
    python enter_closes.py --date 2026-09-16 --apply
    python enter_closes.py --date 2026-09-16 --closes-csv closes.tsv --apply

Exit 0 = nothing wrong (dry run or written). 1 = refused or a ticker skipped.
2 = usage / wrong input.

Advisory-only - no orders - not financial advice.
"""

import argparse
import csv
import datetime
import glob
import os
import sys

import repair_outcome_close as roc

try:
    import trading_calendar as cal
except ImportError:                                           # pragma: no cover
    print("ERROR: trading_calendar.py is required (it locates the cells).",
          file=sys.stderr)
    sys.exit(2)

PLAUS_PCT = 12.0
LOG_TOL = 0.0051        # a 2dp log print against a full-precision close


def last_settled_session(now_date=None):
    d = now_date or datetime.date.today()
    if not cal.is_trading_day(d):
        return cal.prior_session(d)
    ok, _ = roc.market_settled(d)
    return d if ok else cal.prior_session(d)


def read_csv(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        sample = fh.read(2048)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
        for row in csv.DictReader(fh, dialect=dialect):
            low = {k.strip().lower(): v for k, v in row.items() if k}
            tk = (low.get("ticker") or "").strip().upper()
            try:
                out[tk] = float(low.get("close"))
            except (TypeError, ValueError):
                continue
    return out


def log_closes(logs_glob, target):
    """{ticker: close} for `target` as printed in any session log's H1 trace.

    Under the D2 window the newest element of a log's closes= list is the
    PRIOR session's close, so the log dated next_session(target) carries it.
    Only D2 logs (>= 2026-09-01) are read; the D1 alignment differs."""
    try:
        import trail_basis_audit as tba
    except ImportError:
        return {}
    out = {}
    base = os.path.dirname(logs_glob) or "."
    paths = set(glob.glob(logs_glob)) | set(
        glob.glob(os.path.join(base, "**", os.path.basename(logs_glob)), recursive=True))
    for lp in sorted(paths):
        m = tba.LOG_DATE_RE.search(os.path.basename(lp))
        if not m:
            continue
        run = datetime.date.fromisoformat(m.group(1))
        if run < datetime.date(2026, 9, 1) or run <= target:
            continue
        per = tba.parse_log(lp)
        for tk, (_lbl, _tr, closes) in (per or {}).items():
            # closes are oldest-first; the newest is prior_session(run)
            k = len(closes)
            for pos, px in enumerate(closes):
                sess = cal.shift_sessions(run, -(k - pos))
                if sess == target:
                    out.setdefault(str(tk).upper(), px)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Enter settled outcome closes for one session.")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"))
    ap.add_argument("--date", default=None, help="resolution session YYYY-MM-DD "
                    "(default: the last settled session)")
    ap.add_argument("--tickers", default=None, help="comma list (default: every "
                    "ticker with a blank cell resolving on the date)")
    ap.add_argument("--closes-csv", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="override the plausibility and log-agreement guards "
                         "(never the settlement guard)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.tracker):
        print("ERROR: not found: %s" % args.tracker, file=sys.stderr)
        return 2
    try:
        target = (datetime.date.fromisoformat(args.date) if args.date
                  else last_settled_session())
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 2

    print("=" * 78)
    print("ENTER OUTCOME CLOSES - resolution session %s   [%s]"
          % (target, "APPLY" if args.apply else "DRY RUN"))
    print("=" * 78)
    print("  master : %s" % args.tracker)

    # ---- guard 1: a settled NYSE session ---------------------------------
    if not cal.is_trading_day(target):
        print("  REFUSED: %s is not an NYSE session." % target)
        return 2
    settled, why = roc.market_settled(target)
    print("  settlement: %s" % why)
    if not settled:
        print("  REFUSED: a close cannot be entered for a session that has not")
        print("  settled. This is the guard whose absence let 80 cells for")
        print("  2026-09-17/18 into the master on 2026-09-16. --force does not")
        print("  override it.")
        print("=" * 78)
        return 1

    rows = roc.load_rows(args.tracker)
    cohorts = sorted({r["date"] for r in rows})
    want = ({t.strip().upper() for t in args.tickers.split(",") if t.strip()}
            if args.tickers else None)

    blank, filled = {}, {}
    for r in rows:
        tk = str(r["tkr"] or "").strip().upper()
        if want and tk not in want:
            continue
        for label, pcol, rcol, n in roc.HORIZONS:
            if cal.shift_sessions(r["date"], n) != target:
                continue
            (filled if roc.num(r[pcol]) else blank).setdefault(tk, []).append(
                (r, label, pcol, rcol))
    if not blank and not filled:
        print("  Nothing resolves on %s in this master (cohorts %s -> %s)."
              % (target, cohorts[0], cohorts[-1]))
        return 0
    n_blank = sum(len(v) for v in blank.values())
    n_filled = sum(len(v) for v in filled.values())
    print("  cells resolving on %s: %d blank, %d already filled, %d ticker(s)"
          % (target, n_blank, n_filled, len(set(blank) | set(filled))))

    # ---- source ------------------------------------------------------------
    tickers = sorted(set(blank) | set(filled))
    if args.closes_csv:
        src = "enter_closes csv:%s" % os.path.basename(args.closes_csv)
        closes = read_csv(args.closes_csv)
    else:
        src = "enter_closes schwab"
        closes = {}
        for tk in tickers:
            seen = roc.fetch_daily_closes(tk, quiet=True)
            if target in seen:
                closes[tk] = seen[target]
    if args.force:
        src += " FORCED"
    from_logs = log_closes(args.logs, target)
    pxsig = {str(r["tkr"]).upper(): r["g"] for r in rows if r["date"] == target}

    edits, audit, audit_tk = [], [], []
    skipped, conflicts = [], []
    print("-" * 78)
    print("  %-6s %10s %10s %10s  %s" % ("ticker", "close", "Px@signal", "log", "result"))
    for tk in tickers:
        c = closes.get(tk)
        if c is None:
            skipped.append((tk, "no close from the source"))
            print("  %-6s %10s %10s %10s  SKIP no close" % (tk, "-", "-", "-"))
            continue
        ref = pxsig.get(tk)
        lg = from_logs.get(tk)
        problems = []
        if roc.num(ref) and ref and abs(c - ref) / ref * 100.0 > PLAUS_PCT:
            problems.append("%.1f%% from Px@signal" % ((c - ref) / ref * 100.0))
        if lg is not None and abs(c - lg) > LOG_TOL:
            problems.append("log says %.2f" % lg)
        for r, label, pcol, _ in filled.get(tk, []):
            if abs(float(r[pcol]) - c) > 1e-9:
                conflicts.append((tk, "%s%d" % (pcol, r["row"]), label, r[pcol], c))
        result = "ok"
        if problems and not args.force:
            skipped.append((tk, "; ".join(problems)))
            result = "SKIP " + "; ".join(problems)
        elif problems:
            result = "FORCED over " + "; ".join(problems)
        print("  %-6s %10.4f %10s %10s  %s"
              % (tk, c, ("%.4f" % ref) if roc.num(ref) else "-",
                 ("%.2f" % lg) if lg is not None else "-", result))
        if result.startswith("SKIP"):
            continue
        for r, label, pcol, rcol in blank.get(tk, []):
            g = r["g"]
            new_ret = (c - g) / g if roc.num(g) and g else None
            if new_ret is None:
                skipped.append((tk, "row %d has no Px@signal" % r["row"]))
                continue
            edits.append((r, pcol, rcol, c, new_ret))
            audit.append(dict(cell="%s%d" % (pcol, r["row"]), label=label, old=None,
                              new=c, old_ret=float("nan"), new_ret=new_ret * 100.0,
                              flip=""))
            audit_tk.append(tk)

    print("-" * 78)
    print("  %d blank cell(s) to fill" % len(edits))
    for (r, pcol, _, c, ret), tk in zip(edits, audit_tk):
        print("    %s%-5d %-5s cohort %s  %.4f  -> %+.2f%%"
              % (pcol, r["row"], tk, r["date"], c, ret * 100.0))
    if conflicts:
        print("  %d FILLED cell(s) disagree with the sourced close - NOT changed:"
              % len(conflicts))
        for tk, cell, label, old, new in conflicts:
            print("    %-5s %-6s %-5s master %.4f vs source %.4f  -> "
                  "repair_outcome_close.py --ticker %s --date %s --price %s"
                  % (tk, cell, label, old, new, tk, target, new))
    if skipped:
        print("  %d ticker(s) skipped:" % len(skipped))
        for tk, why in skipped:
            print("    %-6s %s" % (tk, why))

    if not edits:
        print("=" * 78)
        return 1 if (skipped or conflicts) else 0
    if not args.apply:
        print("-" * 78)
        print("  DRY RUN - nothing written. Re-run with --apply to commit.")
        print("=" * 78)
        return 1 if (skipped or conflicts) else 0

    try:
        backup, ledger, part = roc.write_edits(
            args.tracker, edits, audit, lambda i: audit_tk[i], src, lambda i: target)
    except AssertionError as e:
        print("  ERROR: %s - nothing written." % e, file=sys.stderr)
        return 1
    print("-" * 78)
    print("  backup : %s" % backup)
    print("  WROTE  : %d cell(s) in %s (%s); fullCalcOnLoad set" % (len(edits), args.tracker, part))
    if ledger:
        print("  audit  : %s" % ledger)
    print("  NEXT   : python outcome_sanity.py   <- must come back clean")
    print("=" * 78)
    return 1 if (skipped or conflicts) else 0


if __name__ == "__main__":
    sys.exit(main())
