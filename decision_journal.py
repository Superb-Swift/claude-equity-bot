#!/usr/bin/env python3
"""
decision_journal.py - the operator's decision journal (#6a) and thesis
registry (#3a), kept LOCAL, plus the check that nothing goes unjournaled.

WHY THIS EXISTS (gap analysis 2026-10-09, #6a and #3a; DP-3C-bi, 2026-10-22)
    Phase 4 is decision-support quality (DP-T1), and nothing records the
    decisions. The first acted-on approvals exist only as position changes
    inferred from the logs, and one PARTIAL lapsed unacted. Each week without a
    record turns a reason into a reconstruction. A thesis written after the
    fact is hindsight, so the registry must be started while the names are
    held, by the operator, in the operator's words.

WHAT IT WRITES (both in logs\\, which git ignores - personal trading data)
    logs\\decision_journal.tsv   one row per EVENT the logs show:
        ADVICE-APPROVED   a BUY/SELL the risk engine marked APPROVED (headline),
                          with its PER-ACCOUNT split
        HELD-CHANGE       the accounts a name is held in changed between two
                          consecutive session logs (opened, added, reduced, closed, moved)
      Facts are filled from the logs. The columns `action`, `action_date`,
      `account` and `why` are the operator's and are left blank: this tool
      never writes a reason.
        --note (added 2026-10-23) appends an operator decision the logs cannot
      show, such as a watchlist edit, one row per ticker, with the reason AS
      THE OPERATOR GAVE IT (--why). It refuses before --init has run, so a note
      can never block the journal's creation.
    logs\\thesis_registry.tsv    one row per name held in the latest log:
      held_since and accounts from the logs; `why_held`, `invalidation_1..3`
      and `review_date` are the operator's.

    The code holds no tickers, accounts or positions; everything is read from
    the logs at run time (the repo is public - Repo_Review 2026-09-14 s3).

USAGE
    python decision_journal.py --init [--since 2026-10-01]   # create (never overwrites)
    python decision_journal.py --check [--since 2026-10-01]  # list unjournaled events
    python decision_journal.py --note --tickers A,B --event WATCHLIST-OUT \
        --detail "..." --why "<the operator's words>" [--date YYYY-MM-DD]
    python decision_journal.py --thesis-init                 # create the registry
    python decision_journal.py --thesis-check                # held names with no thesis
    python decision_journal.py --selftest

Exit 0 always for --check / --thesis-check (they report); 1 on a refused
write (the file exists); 2 on usage.
Advisory-only - no orders - not financial advice.
"""

import argparse
import csv
import datetime as dt
import glob
import os
import re
import sys

JOURNAL = os.path.join("logs", "decision_journal.tsv")
THESIS = os.path.join("logs", "thesis_registry.tsv")
J_COLS = ["event_date", "ticker", "event", "detail", "action", "action_date",
          "account", "why", "recorded_by"]
T_COLS = ["ticker", "accounts", "held_since", "why_held", "invalidation_1",
          "invalidation_2", "invalidation_3", "review_date", "recorded_by"]
_LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")


def _logs(pattern):
    try:
        import signal_logs
        paths, _ = signal_logs.discover(pattern)
    except Exception:                                   # noqa: BLE001
        base = os.path.dirname(pattern) or "."
        paths = sorted(set(glob.glob(pattern)) | set(
            glob.glob(os.path.join(base, "**", os.path.basename(pattern)), recursive=True)))
    out = []
    for p in paths:
        m = _LOGDATE.search(os.path.basename(p))
        if m:
            out.append((dt.date.fromisoformat(m.group(1)), p))
    return sorted(out)


def _accounts(field):
    f = (field or "").strip()
    if f in ("", "—", "-"):
        return frozenset()
    return frozenset(a.strip() for a in f.split(",") if a.strip())


def events(pattern, since):
    """[(date, ticker, event, detail)] from the logs, oldest first."""
    import analyze_log
    try:
        from risk_engine import per_account_verdicts
    except Exception:                                   # noqa: BLE001
        per_account_verdicts = lambda _r: {}            # noqa: E731
    out, prev, prev_d = [], None, None
    for d, p in _logs(pattern):
        rows = analyze_log.parse_log(p)
        held = {}
        for r in rows:
            held[r["ticker"]] = _accounts(r["account"]) if r["held"] == "HELD" else frozenset()
            if d >= since and r["signal"] in ("BUY", "SELL") and r["risk"] == "APPROVED":
                per = per_account_verdicts(r["reason"])
                split = "; ".join("%s=%s" % kv for kv in sorted(per.items())) or "headline only"
                out.append((d, r["ticker"], "ADVICE-APPROVED",
                            "%s %d%% at %s; %s" % (r["signal"], r["confidence"],
                                                  r["price"], split)))
        if prev is not None and d >= since:
            for tk in sorted(set(prev) & set(held)):
                a, b = prev[tk], held[tk]
                if a != b:
                    gained, lost = sorted(b - a), sorted(a - b)
                    out.append((d, tk, "HELD-CHANGE",
                                "between the %s and %s runs: %s%s" % (
                                    prev_d, d,
                                    ("now held in " + ", ".join(gained)) if gained else "",
                                    ((" ; " if gained else "") + "no longer held in "
                                     + ", ".join(lost)) if lost else "")))
        prev, prev_d = held, d
    return out, prev or {}


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _write(path, cols, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def held_since(pattern, held_now):
    """{ticker: first date of the current continuous held run}."""
    import analyze_log
    since = {}
    for d, p in _logs(pattern):
        cur = {r["ticker"] for r in analyze_log.parse_log(p) if r["held"] == "HELD"}
        for tk in list(since):
            if tk not in cur:
                del since[tk]
        for tk in cur:
            since.setdefault(tk, d)
    return {tk: since.get(tk) for tk in held_now}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Local decision journal and thesis registry.")
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"))
    ap.add_argument("--since", type=dt.date.fromisoformat, default=dt.date(2026, 10, 1))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--init", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--thesis-init", action="store_true")
    g.add_argument("--thesis-check", action="store_true")
    g.add_argument("--note", action="store_true",
                   help="append an operator decision the logs cannot show (one row per ticker)")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--journal", default=JOURNAL)
    ap.add_argument("--thesis", default=THESIS)
    ap.add_argument("--tickers", default="", help="--note: comma list")
    ap.add_argument("--event", default="", help="--note: e.g. WATCHLIST-OUT, WATCHLIST-IN")
    ap.add_argument("--detail", default="", help="--note: the facts of the decision")
    ap.add_argument("--action", default="", help="--note: what was done, if anything")
    ap.add_argument("--why", default="", help="--note: the reason, in the operator's words")
    ap.add_argument("--date", default=None, help="--note: the decision date (default today)")
    ap.add_argument("--by", default="operator", help="--note: who gave the reason")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if a.selftest:
        return selftest()

    if a.note:
        tks = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
        if not tks or not re.fullmatch(r"[A-Z][A-Z0-9-]*", a.event or "") or not a.why.strip():
            print("USAGE: --note needs --tickers, an --event in CAPS (e.g. WATCHLIST-OUT) "
                  "and --why in your own words.")
            return 2
        if not os.path.exists(a.journal):
            print("REFUSED: %s does not exist yet. Run --init first; a note written before "
                  "it would block --init." % a.journal)
            return 1
        day = a.date or dt.date.today().isoformat()
        with open(a.journal, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=J_COLS, delimiter="\t", lineterminator="\n")
            for tk in tks:
                w.writerow(dict(event_date=day, ticker=tk, event=a.event, detail=a.detail,
                                action=a.action, why=a.why.strip(),
                                recorded_by="decision_journal.py --note (%s)" % a.by))
        print("Appended %d %s row(s) to %s." % (len(tks), a.event, a.journal))
        return 0

    if a.init or a.check:
        evs, _held = events(a.logs, a.since)
        if a.init:
            if os.path.exists(a.journal):
                print("REFUSED: %s exists. The journal is append-by-hand; --init never "
                      "overwrites it. Use --check to see what is missing." % a.journal)
                return 1
            _write(a.journal, J_COLS, [dict(event_date=d, ticker=tk, event=e, detail=x,
                                            recorded_by="decision_journal.py --init (facts only)")
                                       for d, tk, e, x in evs])
            print("Wrote %s: %d event(s) since %s. Fill action / action_date / account / "
                  "why in your own words; leave a row's why as 'no action' if none was "
                  "taken." % (a.journal, len(evs), a.since))
            return 0
        have = {(r["event_date"], r["ticker"], r["event"]): r for r in _read(a.journal)}
        missing = [e for e in evs if (str(e[0]), e[1], e[2]) not in have]
        blank = [e for e in evs if (str(e[0]), e[1], e[2]) in have
                 and not (have[(str(e[0]), e[1], e[2])].get("why") or "").strip()]
        print("DECISION JOURNAL CHECK since %s: %d event(s); %d not in the journal; %d "
              "with no 'why'." % (a.since, len(evs), len(missing), len(blank)))
        for d, tk, e, x in missing:
            print("  UNJOURNALED  %s %-5s %-15s %s" % (d, tk, e, x))
        for d, tk, e, x in blank:
            print("  NO WHY       %s %-5s %-15s %s" % (d, tk, e, x))
        if missing and os.path.exists(a.journal):
            with open(a.journal, "a", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=J_COLS, delimiter="\t", lineterminator="\n")
                for d, tk, e, x in missing:
                    w.writerow(dict(event_date=d, ticker=tk, event=e, detail=x,
                                    recorded_by="decision_journal.py --check (facts only)"))
            print("  (appended %d fact row(s); the reasons are yours to add)" % len(missing))
        return 0

    _evs, held = events(a.logs, a.since)
    held_now = sorted(tk for tk, acc in held.items() if acc)
    if a.thesis_init:
        if os.path.exists(a.thesis):
            print("REFUSED: %s exists; --thesis-init never overwrites it." % a.thesis)
            return 1
        hs = held_since(a.logs, held_now)
        _write(a.thesis, T_COLS, [dict(ticker=tk, accounts=", ".join(sorted(held[tk])),
                                       held_since=hs.get(tk) or "",
                                       recorded_by="decision_journal.py --thesis-init (facts only)")
                                  for tk in held_now])
        print("Wrote %s: %d held name(s). Write why each is held, two or three conditions "
              "that would end the thesis, and a review date - before the next outcome "
              "lands, so it is a thesis and not hindsight." % (a.thesis, len(held_now)))
        return 0
    have = {r["ticker"]: r for r in _read(a.thesis)}
    no_row = [tk for tk in held_now if tk not in have]
    no_why = [tk for tk in held_now if tk in have and not (have[tk].get("why_held") or "").strip()]
    gone = sorted(tk for tk in have if tk not in held_now)
    print("THESIS REGISTRY CHECK: %d held; %d with no row; %d with no 'why_held'; %d row(s) "
          "for names no longer held." % (len(held_now), len(no_row), len(no_why), len(gone)))
    for tk in no_row:
        print("  NO ROW       %s" % tk)
    for tk in no_why:
        print("  NO THESIS    %s" % tk)
    for tk in gone:
        print("  NOT HELD     %s (keep the row; record the exit in the journal)" % tk)
    return 0


def selftest():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="dj_")
    fails = []

    def line(tk, held, acct, sig, conf, risk, reason):
        return ('2026-10-0X 09:30:00,000 | INFO | Signal JSON: {"ticker": "%s"} '
                '[PHASE 3-C DRY RUN] [%s] [%s] %s | Signal: %s | Confidence: %d%% | '
                'Risk: %s | Reason: %s\n' % (tk, acct, held, tk, sig, conf, risk, reason))
    try:
        with open(os.path.join(tmp, "signals_2026-10-07.log"), "w", encoding="utf-8") as fh:
            fh.write(line("AAA", "HELD", "Acct1", "BUY", 78, "APPROVED",
                          "PENDING HUMAN APPROVAL. PER-ACCOUNT: Acct2=APPROVED; Acct1=REJECTED. x"))
            fh.write(line("BBB", "SCOUT", "—", "BUY", 70, "APPROVED", "PENDING HUMAN APPROVAL"))
            fh.write(line("CCC", "HELD", "Acct1", "HOLD", 50, "APPROVED", "HOLD signal"))
        with open(os.path.join(tmp, "signals_2026-10-08.log"), "w", encoding="utf-8") as fh:
            fh.write(line("AAA", "HELD", "Acct2,Acct1", "BUY", 76, "REJECTED", "Rejected"))
            fh.write(line("BBB", "HELD", "Acct1", "HOLD", 62, "APPROVED", "HOLD signal"))
            fh.write(line("CCC", "HELD", "Acct1", "HOLD", 50, "APPROVED", "HOLD signal"))
        pat = os.path.join(tmp, "signals_*.log")
        evs, held = events(pat, dt.date(2026, 10, 1))
        kinds = sorted((e[1], e[2]) for e in evs)
        want = [("AAA", "ADVICE-APPROVED"), ("AAA", "HELD-CHANGE"),
                ("BBB", "ADVICE-APPROVED"), ("BBB", "HELD-CHANGE")]
        ok = kinds == want
        print("  [%s] approvals and held-changes found, HOLDs and unchanged names ignored"
              % ("PASS" if ok else "FAIL")); ok or fails.append("events")
        ok = any("Acct2=APPROVED" in e[3] for e in evs if e[2] == "ADVICE-APPROVED")
        print("  [%s] the PER-ACCOUNT split is kept" % ("PASS" if ok else "FAIL")); ok or fails.append("split")
        j = os.path.join(tmp, "j.tsv")
        main(["--logs", pat, "--init", "--journal", j])
        ok = main(["--logs", pat, "--init", "--journal", j]) == 1
        print("  [%s] --init never overwrites" % ("PASS" if ok else "FAIL")); ok or fails.append("overwrite")
        rows = _read(j)
        ok = len(rows) == 4 and all(not r["why"] for r in rows)
        print("  [%s] facts written, reasons left blank" % ("PASS" if ok else "FAIL")); ok or fails.append("blank")
        t = os.path.join(tmp, "t.tsv")
        main(["--logs", pat, "--thesis-init", "--thesis", t])
        trows = {r["ticker"]: r for r in _read(t)}
        ok = sorted(trows) == ["AAA", "BBB", "CCC"] and trows["BBB"]["held_since"] == "2026-10-08"
        print("  [%s] thesis rows for every held name, held_since from the logs"
              % ("PASS" if ok else "FAIL")); ok or fails.append("thesis")
        nj = os.path.join(tmp, "n.tsv")
        ok = main(["--note", "--tickers", "XXX", "--event", "WATCHLIST-OUT",
                   "--why", "w", "--journal", nj]) == 1 and not os.path.exists(nj)
        print("  [%s] --note refuses before --init (it would block the journal)"
              % ("PASS" if ok else "FAIL")); ok or fails.append("note-refuse")
        main(["--note", "--tickers", "xxx,yyy", "--event", "WATCHLIST-OUT", "--date",
              "2026-10-22", "--why", "the thesis is broken", "--by", "Op", "--journal", j])
        nrows = [r for r in _read(j) if r["event"] == "WATCHLIST-OUT"]
        ok = ([r["ticker"] for r in nrows] == ["XXX", "YYY"]
              and all(r["why"] == "the thesis is broken" and r["event_date"] == "2026-10-22"
                      for r in nrows) and len(_read(j)) == 6)
        print("  [%s] --note appends one row per ticker with the operator's words, "
              "facts untouched" % ("PASS" if ok else "FAIL")); ok or fails.append("note")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            main(["--logs", pat, "--check", "--journal", j])
        ok = "0 not in the journal" in buf.getvalue()
        print("  [%s] a note does not disturb --check" % ("PASS" if ok else "FAIL"))
        ok or fails.append("note-check")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("  decision_journal selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
