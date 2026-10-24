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

AMENDED 2026-10-22 (DP-3C-ba, DP-3C-bd; proposed 2026-10-20 as G-c and R9)
    * --catch-up enters EVERY settled session that still has blank due cells,
      oldest first, each session with its own guards, in ONE write (one
      backup). The default (no --date) still means the last settled session
      only; that default is how 2026-10-19 was missed (54 cells), so the
      evening chain now uses --catch-up.
    * PASTE FIRST. A session the bot ran whose cohort is not yet in the master
      is REFUSED: without that cohort's Px@signal the evening entry has no
      content guard at all (the next session's log does not exist yet).
    * UNGUARDED. A ticker for which NEITHER content guard ran (no Px@signal on
      the session, no later log close) used to print "ok". It now prints
      UNGUARDED and is skipped unless --allow-unguarded is given (a departed
      name, or a bot-absent session entered in the evening). Allowed cells
      carry "UNGUARDED" in the ledger's source field.
    * --settle-precision (DP-3C-bd, R10) settles every FILLED cell whose value
      differs from the close the logs carry by more than the log's print
      precision but by less than 0.05% (Check F's PRECISION tier), to the log
      close. It skips a candidate when the logs carrying that session disagree
      with each other, or when settling would flip a verdict (those go to D9,
      an external close, first). Ledger source: "settle_precision R10
      (DP-3C-bd)".

USAGE
    python enter_closes.py                         # last settled session, dry run
    python enter_closes.py --catch-up              # every settled session with blanks
    python enter_closes.py --catch-up --apply
    python enter_closes.py --date 2026-09-16       # dry run
    python enter_closes.py --date 2026-09-16 --apply
    python enter_closes.py --date 2026-09-16 --closes-csv closes.tsv --apply
    python enter_closes.py --settle-precision      # dry run; --apply to write
    python settle_precision.py [--apply]           # the same, under its own name

    --catch-up ALSO settles PRECISION-tier cells (same rules) in the same
    write, unless --no-settle: the evening command is one command.

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


def due_sessions(rows, through, want=None):
    """Settled sessions (<= through) with at least one BLANK due cell on a row
    with a usable Px@signal, oldest first. One rule with outcome_sanity's
    Check H, so the gate that fires and the command that clears it agree."""
    out = set()
    for r in rows:
        tk = str(r["tkr"] or "").strip().upper()
        if want and tk not in want:
            continue
        if not roc.num(r["g"]) or not r["g"]:
            continue
        for _label, pcol, _rcol, n in roc.HORIZONS:
            if roc.num(r[pcol]):
                continue
            d = cal.shift_sessions(r["date"], n)
            if d <= through:
                out.add(d)
    return sorted(out)


def plan_session(target, rows, args, want, closes_for, logs_glob):
    """Guards and edits for one resolution session. Returns a dict with
    edits/audit/audit_tk/skipped/conflicts/refused/lines (printed by caller)."""
    cohorts = sorted({r["date"] for r in rows})
    res = dict(edits=[], audit=[], audit_tk=[], skipped=[], conflicts=[],
               unguarded=[], refused=None, lines=[], n_blank=0, n_filled=0)
    out = res["lines"].append
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
        out("  Nothing resolves on %s in this master (cohorts %s -> %s)."
            % (target, cohorts[0], cohorts[-1]))
        return res
    res["n_blank"] = sum(len(v) for v in blank.values())
    res["n_filled"] = sum(len(v) for v in filled.values())
    out("  cells resolving on %s: %d blank, %d already filled, %d ticker(s)"
        % (target, res["n_blank"], res["n_filled"], len(set(blank) | set(filled))))

    # ---- PASTE FIRST (DP-3C-ba) ---------------------------------------------
    bot_ran = target not in getattr(cal, "BOT_ABSENT", {})
    pxsig = {str(r["tkr"]).upper(): r["g"] for r in rows if r["date"] == target}
    from_logs = log_closes(logs_glob, target)
    if bot_ran and not pxsig and not from_logs and not args.allow_unguarded:
        res["refused"] = ("the %s cohort is not in the master yet. Paste and save "
                          "today's rows FIRST, then re-run: without that cohort's "
                          "Px@signal no content guard can run tonight." % target)
        return res

    tickers = sorted(set(blank) | set(filled))
    closes = closes_for(target, tickers)
    out("  %-6s %10s %10s %10s  %s" % ("ticker", "close", "Px@signal", "log", "result"))
    for tk in tickers:
        c = closes.get(tk)
        if c is None:
            res["skipped"].append((tk, "no close from the source"))
            out("  %-6s %10s %10s %10s  SKIP no close" % (tk, "-", "-", "-"))
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
                res["conflicts"].append((tk, "%s%d" % (pcol, r["row"]), label, r[pcol], c))
        guarded = (roc.num(ref) and ref) or lg is not None
        result = "ok"
        if problems and not args.force:
            res["skipped"].append((tk, "; ".join(problems)))
            result = "SKIP " + "; ".join(problems)
        elif problems:
            result = "FORCED over " + "; ".join(problems)
        elif not guarded:
            # R9 (DP-3C-ba): never print "ok" for a check that did not run.
            if args.allow_unguarded:
                result = "UNGUARDED (allowed)"
                res["unguarded"].append(tk)
            else:
                res["skipped"].append((tk, "UNGUARDED: no Px@signal on %s and no later log "
                                           "close; re-run with --allow-unguarded after "
                                           "checking it yourself" % target))
                result = "UNGUARDED - skipped"
        out("  %-6s %10.4f %10s %10s  %s"
            % (tk, c, ("%.4f" % ref) if roc.num(ref) else "-",
               ("%.2f" % lg) if lg is not None else "-", result))
        if result.startswith("SKIP") or result == "UNGUARDED - skipped":
            continue
        for r, label, pcol, rcol in blank.get(tk, []):
            g = r["g"]
            new_ret = (c - g) / g if roc.num(g) and g else None
            if new_ret is None:
                res["skipped"].append((tk, "row %d has no Px@signal" % r["row"]))
                continue
            res["edits"].append((r, pcol, rcol, c, new_ret))
            res["audit"].append(dict(cell="%s%d" % (pcol, r["row"]), label=label, old=None,
                                     new=c, old_ret=float("nan"), new_ret=new_ret * 100.0,
                                     flip="UNGUARDED" if result.startswith("UNGUARDED") else ""))
            res["audit_tk"].append((tk, target))
    return res


SETTLE_SRC = "settle_precision R10 (DP-3C-bd)"


def precision_candidates(tracker, logs_glob):
    """DP-3C-bd (R10). ([(r, pcol, rcol, price, ret)], [audit], [(tkr, sess)],
    [(item, why) skipped]) for every FILLED cell in Check F's PRECISION tier
    whose carrying logs all agree and whose settling flips no verdict."""
    import outcome_sanity as osn
    rows = osn.load(tracker)
    resolve = cal.shift_sessions
    cons = osn.log_close_consensus(rows, logs_glob, resolve)
    by_num = {r["row"]: r for r in rows}
    cand, skipped = [], []
    for r in rows:
        for label, col, n in osn.HORIZONS:
            key = {8: "h", 9: "i", 10: "j"}[col]
            v = r[key]
            if not osn.num(v):
                continue
            sess = resolve(r["date"], n)
            c = cons.get((r["tkr"], sess))
            if not c:
                continue
            price, nruns, byprice = c
            gap = abs(price - v) / v * 100.0 if v else 0.0
            if abs(price - v) <= osn.CHECK_F_TOL_ABS or gap >= osn.CHECK_F_TOL_PCT:
                continue
            why = None
            if len(byprice) > 1:
                why = "logs disagree (%s)" % ", ".join("%.4f x%d" % (p, len(d))
                                                      for p, d in sorted(byprice.items()))
            sens = osn._verdict_sensitivity(by_num, [(r["row"], label)], price)
            if sens and not why:
                why = sens.strip()
            item = (r, label, {"h": "H", "i": "I", "j": "J"}[key],
                    {"h": "K", "i": "L", "j": "M"}[key], v, price, sess, nruns)
            (skipped if why else cand).append((item, why))
    edits, audit, tks = [], [], []
    rrows = None
    for (r, label, pcol, rcol, v, price, sess, nruns), _ in cand:
        g = r["g"]
        if not osn.num(g) or not g:
            continue
        if rrows is None:
            rrows = {x["row"]: x for x in roc.load_rows(tracker)}
        old_ret, new_ret = (v - g) / g * 100.0, (price - g) / g * 100.0
        edits.append((rrows[r["row"]], pcol, rcol, price, new_ret / 100.0))
        audit.append(dict(cell="%s%d" % (pcol, r["row"]), label=label, old=v, new=price,
                          old_ret=old_ret, new_ret=new_ret, flip="", nruns=nruns))
        tks.append((r["tkr"], sess))
    return edits, audit, tks, skipped


def settle_precision(args):
    """DP-3C-bd (R10): settle PRECISION-tier cells to the close the logs carry.
    Standalone form; --catch-up runs the same candidates in its own write."""
    edits, audit, tks, skipped = precision_candidates(args.tracker, args.logs)
    print("=" * 78)
    print("SETTLE PRECISION-TIER CELLS TO THE LOG CLOSE (DP-3C-bd)   [%s]"
          % ("APPLY" if args.apply else "DRY RUN"))
    print("=" * 78)
    print("  master : %s" % args.tracker)
    _print_settle(edits, audit, tks, skipped)
    if not edits:
        print("  Nothing to settle.")
        print("=" * 78)
        return 0
    if not args.apply:
        print("  DRY RUN - nothing written. Re-run with --apply (Excel closed).")
        print("=" * 78)
        return 0
    try:
        backup, ledger, part = roc.write_edits(
            args.tracker, edits, audit, lambda i: tks[i][0], SETTLE_SRC, lambda i: tks[i][1])
    except AssertionError as e:
        print("  ERROR: %s - nothing written." % e, file=sys.stderr)
        return 1
    print("  backup : %s" % backup)
    print("  WROTE  : %d cell(s) (%s); fullCalcOnLoad set" % (len(edits), part))
    print("  NEXT   : python outcome_sanity.py   <- the PRECISION list should be empty")
    print("=" * 78)
    return 0


def _print_settle(edits, audit, tks, skipped):
    print("  PRECISION-tier cells to settle to the log close (DP-3C-bd): %d; "
          "left for D9: %d" % (len(edits), len(skipped)))
    for (r, pcol, _rc, price, _ret), a, (tk, sess) in zip(edits, audit, tks):
        print("    %s%-5d %-5s %s %-5s  %.4f -> %.4f  (%d log(s))  ret %+.3f%% -> %+.3f%%"
              % (pcol, r["row"], tk, sess, a["label"], a["old"], price, a.get("nruns", 0),
                 a["old_ret"], a["new_ret"]))
    for (r, label, pcol, rcol, v, price, sess, nruns), why in skipped:
        print("    D9   %s%-5d %-5s %s %-5s  %.4f vs log %.4f  - %s"
              % (pcol, r["row"], r["tkr"], sess, label, v, price, why))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Enter settled outcome closes.")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"))
    ap.add_argument("--date", default=None, help="resolution session YYYY-MM-DD "
                    "(default: the last settled session)")
    ap.add_argument("--catch-up", action="store_true",
                    help="every settled session that still has blank due cells, oldest first")
    ap.add_argument("--tickers", default=None, help="comma list (default: every "
                    "ticker with a blank cell resolving on the date)")
    ap.add_argument("--closes-csv", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="override the plausibility and log-agreement guards "
                         "(never the settlement guard)")
    ap.add_argument("--allow-unguarded", action="store_true",
                    help="write cells for which neither content guard could run "
                         "(departed names, bot-absent sessions); labelled UNGUARDED")
    ap.add_argument("--settle-precision", action="store_true",
                    help="DP-3C-bd: settle PRECISION-tier cells to the log close")
    ap.add_argument("--no-settle", action="store_true",
                    help="with --catch-up: do not settle PRECISION-tier cells this run")
    args = ap.parse_args(argv)

    if not os.path.exists(args.tracker):
        print("ERROR: not found: %s" % args.tracker, file=sys.stderr)
        return 2
    if os.path.basename(args.tracker).lower() == roc.REFUSED.lower():
        print("REFUSED: %s is the generated report copy." % roc.REFUSED)
        return 2
    if args.settle_precision:
        return settle_precision(args)
    if args.catch_up and args.date:
        print("ERROR: --catch-up and --date are exclusive", file=sys.stderr)
        return 2
    try:
        last = last_settled_session()
        target = datetime.date.fromisoformat(args.date) if args.date else last
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 2

    rows = roc.load_rows(args.tracker)
    want = ({t.strip().upper() for t in args.tickers.split(",") if t.strip()}
            if args.tickers else None)
    if args.catch_up:
        targets = due_sessions(rows, last, want)
        label = "CATCH-UP through %s: %s" % (
            last, ", ".join(str(d) for d in targets) if targets else "nothing due")
    else:
        targets = [target]
        label = "resolution session %s" % target

    print("=" * 78)
    print("ENTER OUTCOME CLOSES - %s   [%s]" % (label, "APPLY" if args.apply else "DRY RUN"))
    print("=" * 78)
    print("  master : %s" % args.tracker)
    if not targets:
        print("  Every settled session's cells are filled. Nothing to enter.")
        print("=" * 78)
        return 0

    # ---- guard 1: settled NYSE sessions ---------------------------------
    for t in targets:
        if not cal.is_trading_day(t):
            print("  REFUSED: %s is not an NYSE session." % t)
            return 2
        settled, why = roc.market_settled(t)
        if not settled:
            print("  settlement (%s): %s" % (t, why))
            print("  REFUSED: a close cannot be entered for a session that has not")
            print("  settled. This is the guard whose absence let 80 cells for")
            print("  2026-09-17/18 into the master on 2026-09-16. --force does not")
            print("  override it.")
            print("=" * 78)
            return 1
    print("  settlement: %s" % ("; ".join("%s %s" % (t, roc.market_settled(t)[1])
                                          for t in targets[-3:])))

    # ---- source ------------------------------------------------------------
    if args.closes_csv:
        src = "enter_closes csv:%s" % os.path.basename(args.closes_csv)
        csv_closes = read_csv(args.closes_csv)
        if len(targets) > 1:
            print("  REFUSED: --closes-csv carries one session; use --date with it.")
            return 2

        def closes_for(t, tickers):
            return {tk: csv_closes[tk] for tk in tickers if tk in csv_closes}
    else:
        src = "enter_closes schwab"
        cache = {}

        def closes_for(t, tickers):
            out = {}
            for tk in tickers:
                if tk not in cache:
                    cache[tk] = roc.fetch_daily_closes(tk, quiet=True)
                if t in cache[tk]:
                    out[tk] = cache[tk][t]
            return out
    if args.force:
        src += " FORCED"

    edits, audit, audit_tk = [], [], []
    skipped, conflicts, unguarded = [], [], []
    for t in targets:
        print("-" * 78)
        print("  SESSION %s" % t)
        plan = plan_session(t, rows, args, want, closes_for, args.logs)
        for line in plan["lines"]:
            print(line)
        if plan["refused"]:
            print("  REFUSED: %s" % plan["refused"])
            print("=" * 78)
            return 1
        edits += plan["edits"]
        audit += plan["audit"]
        audit_tk += plan["audit_tk"]
        skipped += [(t, tk, why) for tk, why in plan["skipped"]]
        conflicts += [(t,) + c for c in plan["conflicts"]]
        unguarded += [(t, tk) for tk in plan["unguarded"]]

    # ---- DP-3C-bd: --catch-up also settles PRECISION-tier cells -------------
    settle = ([], [], [], [])
    if args.catch_up and not args.no_settle:
        try:
            settle = precision_candidates(args.tracker, args.logs)
        except Exception as e:                          # noqa: BLE001
            print("  [WARN] precision settle skipped (%s); blank-cell entry unaffected." % e)
        print("-" * 78)
        _print_settle(*settle)

    print("-" * 78)
    print("  %d blank cell(s) to fill" % len(edits))
    for (r, pcol, _, c, ret), (tk, t) in zip(edits, audit_tk):
        print("    %s%-5d %-5s cohort %s -> %s  %.4f  -> %+.2f%%"
              % (pcol, r["row"], tk, r["date"], t, c, ret * 100.0))
    if conflicts:
        print("  %d FILLED cell(s) disagree with the sourced close - NOT changed:"
              % len(conflicts))
        for t, tk, cell, label, old, new in conflicts:
            print("    %-5s %-6s %-5s master %.4f vs source %.4f  -> "
                  "repair_outcome_close.py --ticker %s --date %s --price %s"
                  % (tk, cell, label, old, new, tk, t, new))
    if unguarded:
        print("  %d ticker-session(s) entered UNGUARDED (allowed): %s"
              % (len(unguarded), ", ".join("%s %s" % (tk, t) for t, tk in unguarded)))
    if skipped:
        print("  %d ticker(s) skipped:" % len(skipped))
        for t, tk, why in skipped:
            print("    %s %-6s %s" % (t, tk, why))

    s_edits, s_audit, s_tks, _s_skipped = settle
    if not edits and not s_edits:
        print("=" * 78)
        return 1 if (skipped or conflicts) else 0
    if not args.apply:
        print("-" * 78)
        print("  DRY RUN - nothing written. Re-run with --apply to commit.")
        print("=" * 78)
        return 1 if (skipped or conflicts) else 0

    srcs = [src + (" UNGUARDED" if a["flip"] == "UNGUARDED" else "") for a in audit]
    edits, audit, audit_tk = edits + s_edits, audit + s_audit, audit_tk + s_tks
    srcs += [SETTLE_SRC] * len(s_edits)
    for a in audit:
        if a["flip"] == "UNGUARDED":
            a["flip"] = ""
    try:
        if len(set(srcs)) == 1:
            backup, ledger, part = roc.write_edits(
                args.tracker, edits, audit, lambda i: audit_tk[i][0], srcs[0],
                lambda i: audit_tk[i][1])
        else:
            # two ledger sources: write the guarded and unguarded cells in two
            # passes (two backups), so each ledger line says what was checked
            for want_src in sorted(set(srcs)):
                idx = [i for i, x in enumerate(srcs) if x == want_src]
                backup, ledger, part = roc.write_edits(
                    args.tracker, [edits[i] for i in idx], [audit[i] for i in idx],
                    lambda k, idx=idx: audit_tk[idx[k]][0], want_src,
                    lambda k, idx=idx: audit_tk[idx[k]][1])
    except AssertionError as e:
        print("  ERROR: %s - nothing written." % e, file=sys.stderr)
        return 1
    print("-" * 78)
    print("  backup : %s" % backup)
    print("  WROTE  : %d cell(s) in %s (%s); fullCalcOnLoad set%s"
          % (len(edits), args.tracker, part,
             (" - incl. %d settled to the log close (DP-3C-bd)" % len(s_edits)) if s_edits else ""))
    if ledger:
        print("  audit  : %s" % ledger)
    print("  NEXT   : python outcome_sanity.py   <- must come back clean")
    print("=" * 78)
    return 1 if (skipped or conflicts) else 0


def selftest():
    """Offline: the R9 and paste-first rules and the catch-up session finder,
    on synthetic rows. Negative cases included."""
    import types
    global log_closes
    real_log_closes = log_closes
    fails = []

    def row(n, d, tk, g, h=None, i=None, j=None, sig="HOLD"):
        return {"row": n, "date": d, "tkr": tk, "sig": sig, "g": g, "H": h, "I": i, "J": j}

    d0 = datetime.date(2026, 10, 12)
    t5 = cal.shift_sessions(d0, 5)                      # 2026-10-19
    args = types.SimpleNamespace(force=False, allow_unguarded=False)
    try:
        # 1. catch-up finds the missed session and only it
        rows = [row(5, d0, "AAA", 10.0), row(6, d0, "BBB", 20.0, h=21.0),
                row(7, t5, "AAA", 10.4), row(8, t5, "BBB", 20.5)]
        got = due_sessions(rows, t5)
        ok = got == [t5]
        print("  [%s] catch-up finds %s" % ("PASS" if ok else "FAIL", got)); ok or fails.append("catchup")
        ok = due_sessions(rows, cal.prior_session(t5)) == []
        print("  [%s] catch-up ignores an unsettled session" % ("PASS" if ok else "FAIL")); ok or fails.append("catchup-neg")
        # 2. guarded by Px@signal -> ok
        log_closes = lambda g, t: {}
        plan = plan_session(t5, rows, args, None, lambda t, tks: {"AAA": 10.5, "BBB": 21.0}, "x")
        ok = len(plan["edits"]) == 1 and not plan["skipped"] and not plan["refused"] \
            and not plan["conflicts"]
        print("  [%s] Px@signal-guarded cell written" % ("PASS" if ok else "FAIL")); ok or fails.append("guarded")
        # 3. paste-first: the session's cohort is absent and no log -> REFUSED
        rows_np = [r for r in rows if r["date"] != t5]
        plan = plan_session(t5, rows_np, args, None, lambda t, tks: {"AAA": 10.5}, "x")
        ok = bool(plan["refused"]) and not plan["edits"]
        print("  [%s] cohort not pasted -> REFUSED" % ("PASS" if ok else "FAIL")); ok or fails.append("paste-first")
        # 4. departed name: cohort present, this ticker absent, no log -> UNGUARDED skip
        rows_dep = rows + [row(9, d0, "CCC", 5.0)]
        plan = plan_session(t5, rows_dep, args, None, lambda t, tks: {"AAA": 10.5, "CCC": 5.1}, "x")
        ok = any(tk == "CCC" and "UNGUARDED" in w for tk, w in plan["skipped"]) and \
            all(e[0]["tkr"] != "CCC" for e in plan["edits"])
        print("  [%s] neither guard -> UNGUARDED, skipped" % ("PASS" if ok else "FAIL")); ok or fails.append("unguarded")
        # 5. ...and written, labelled, with --allow-unguarded
        args2 = types.SimpleNamespace(force=False, allow_unguarded=True)
        plan = plan_session(t5, rows_dep, args2, None, lambda t, tks: {"AAA": 10.5, "CCC": 5.1}, "x")
        ok = any(a["flip"] == "UNGUARDED" for a in plan["audit"]) and "CCC" in plan["unguarded"]
        print("  [%s] --allow-unguarded writes and labels it" % ("PASS" if ok else "FAIL")); ok or fails.append("allow")
        # 6. a later log guards a departed name
        log_closes = lambda g, t: {"CCC": 5.1}
        plan = plan_session(t5, rows_dep, args, None, lambda t, tks: {"AAA": 10.5, "CCC": 5.1}, "x")
        ok = not plan["unguarded"] and not any(tk == "CCC" for tk, _ in plan["skipped"])
        print("  [%s] a later log is a guard" % ("PASS" if ok else "FAIL")); ok or fails.append("logguard")
        # 7. log disagreement -> SKIP
        log_closes = lambda g, t: {"AAA": 10.9}
        plan = plan_session(t5, rows, args, None, lambda t, tks: {"AAA": 10.5}, "x")
        ok = any(tk == "AAA" and "log says" in w for tk, w in plan["skipped"])
        print("  [%s] log disagreement -> SKIP" % ("PASS" if ok else "FAIL")); ok or fails.append("logskip")
    finally:
        log_closes = real_log_closes
    print("  enter_closes selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
