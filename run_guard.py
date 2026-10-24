#!/usr/bin/env python3
"""
run_guard.py - the checks run_daily.bat makes BEFORE main.py runs (R2).

WHY THIS EXISTS (proposed 2026-10-09 as R2; adopted 2026-10-22, DP-3C-ba)
    run_daily.bat had no guards at all, and each missing one has a cost on the
    record:

      A  NON-SESSION / PRE-REGISTERED NO-RUN DAY. scan.bat already tells these
         apart; the run did not. A run on a BOT_ABSENT day creates a cohort the
         pre-registration says does not exist.
      B  SECOND RUN ON THE SAME DATE. main.py opens logs\\signals_<today>.log
         with a FileHandler, which APPENDS: a second run duplicates every row,
         advances signal_state.json twice and overwrites paste_today.tsv.
         Workflow section 17 said "Refused"; nothing refused it.
      C  THE EDGAR FLAG. EQUITY_EDGAR is set by hand each console session, by
         design, so that a control cohort is a deliberate choice. Two control
         cohorts were lost because it was not set (2026-08-04, 08-19). If the
         flag is not "1" the operator must type CONTROL to go on; "0" or unset
         both mean a control cohort that is absent from E4.
      D  LATE START (report only). Price at Signal is a morning quote; a late
         start moves it. 10-19 started 10:42 and 10-20 10:01. On 2026-09-30 a
         25-minute-late start decided a G1 episode on the tracker basis.

    None of these touches what the model sees (DP-3C-ai): they decide whether
    the run happens, never what it is shown.

USAGE (called by run_daily.bat; runnable alone)
    python run_guard.py                 # checks today
    python run_guard.py --date 2026-10-23 --now 09:50   # what it would say
    python run_guard.py --selftest

Exit 0 = run. 1 = refused (the reason is printed). 2 = usage.
Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import os
import re
import sys

LATE_AFTER = (9, 45)          # CT; the canonical start is 09:30 CT
SIGNAL_LINE = re.compile(r"Signal JSON: \{")


def local_now():
    """The operator's clock, in US Central. Falls back to the machine clock
    (the device runs in CT) if no zone database is installed."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Chicago")).replace(tzinfo=None)
    except Exception:                                   # noqa: BLE001
        return dt.datetime.now()


def check(day, now_hm, edgar, log_dir, cal, ask=input):
    """Returns (ok, lines). `ask` is called only for guard C."""
    lines = []
    # ---- A: an NYSE session, and not a pre-registered no-run session ------
    if not cal.is_trading_day(day):
        return False, ["REFUSED (A): %s is not an NYSE session (weekend or holiday)." % day]
    if day in cal.BOT_ABSENT:
        why, doc = cal.BOT_ABSENT[day]
        return False, ["REFUSED (A): %s is a PRE-REGISTERED NO-RUN SESSION: %s (%s)." % (day, why, doc),
                       "  Running would create a cohort the pre-registration says does not",
                       "  exist. If the plan changed, remove the BOT_ABSENT entry first and",
                       "  record it as an amendment."]
    lines.append("  [A] %s is an NYSE session; not a pre-registered no-run day." % day)

    # ---- B: one canonical run per date ---------------------------------
    log = os.path.join(log_dir, "signals_%s.log" % day.isoformat())
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as fh:
            n_sig = sum(1 for ln in fh if SIGNAL_LINE.search(ln))
        if n_sig:
            return False, lines + [
                "REFUSED (B): %s already holds %d signal row(s). A second run appends" % (log, n_sig),
                "  duplicate rows, advances signal_state.json twice and overwrites",
                "  paste_today.tsv. The AM run is canonical; a PM run is diagnostic and",
                "  must not be pasted. To investigate a failed run, rename the log",
                "  (e.g. signals_%s_run1_failed.log) and re-run." % day.isoformat()]
        lines.append("  [B] WARN: %s exists with no signal rows (a run that failed at" % log)
        lines.append("      start-up). Continuing; the new rows will be the only ones.")
    else:
        lines.append("  [B] no log yet for %s - this is the first run." % day)

    # ---- C: the EDGAR flag stays a deliberate per-session choice --------
    if edgar == "1":
        lines.append("  [C] EQUITY_EDGAR=1 - an EDGAR-live (E4 treatment) cohort.")
    else:
        lines.append("  [C] EQUITY_EDGAR is %s. This run would be a CONTROL cohort, absent"
                     % ("unset" if edgar is None else "'%s'" % edgar))
        lines.append("      from E4. Two control cohorts were lost this way (08-04, 08-19).")
        lines.append("      To run with EDGAR: stop, `set EQUITY_EDGAR=1`, run again.")
        for ln in lines:
            print(ln)
        lines = []
        try:
            ans = ask("      Type CONTROL to run a control cohort anyway, anything else to stop: ")
        except EOFError:
            ans = ""
        if ans.strip().upper() != "CONTROL":
            return False, ["REFUSED (C): no CONTROL confirmation. Nothing was run."]
        lines.append("  [C] CONTROL confirmed by the operator - record it in the next review.")

    # ---- D: canonical start time (report only) --------------------------
    if now_hm > LATE_AFTER:
        lines.append("  [D] WARN: started %02d:%02d CT; canonical is 09:30 CT. Price at Signal"
                     % now_hm)
        lines.append("      is a morning quote and moves with the start time. Note why in the")
        lines.append("      next review.")
    else:
        lines.append("  [D] start %02d:%02d CT - on time." % now_hm)
    return True, lines


def selftest():
    import tempfile
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import trading_calendar as cal
    fails = []
    tmp = tempfile.mkdtemp(prefix="run_guard_")
    sess = dt.date(2026, 10, 22)            # Thursday, an NYSE session
    absent = sorted(cal.BOT_ABSENT)[0]      # a pre-registered no-run session

    def case(name, expect_ok, **kw):
        a = dict(day=sess, now_hm=(9, 30), edgar="1", log_dir=tmp, cal=cal,
                 ask=lambda _p: "")
        a.update(kw)
        ok, _lines = check(**a)
        good = ok == expect_ok
        print("  [%s] %-34s -> %s" % ("PASS" if good else "FAIL", name,
                                     "run" if ok else "refused"))
        if not good:
            fails.append(name)

    case("session, flag set, no log", True)
    case("weekend (A)", False, day=dt.date(2026, 10, 24))
    case("holiday (A)", False, day=dt.date(2026, 11, 26))
    case("pre-registered no-run (A)", False, day=absent)
    log = os.path.join(tmp, "signals_%s.log" % sess.isoformat())
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("2026-10-22 09:31 INFO start\n")
    case("log without signal rows (B warn)", True)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write('2026-10-22 09:32 INFO Signal JSON: {"ticker": "AAPL"}\n')
    case("second run (B)", False)
    os.remove(log)
    case("flag unset, no confirmation (C)", False, edgar=None)
    case("flag 0, typed control (C)", True, edgar="0", ask=lambda _p: "control")
    case("late start is a warning only (D)", True, now_hm=(10, 42))
    print("  run_guard selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pre-run guards for run_daily.bat (R2).")
    ap.add_argument("--date", type=dt.date.fromisoformat, default=None)
    ap.add_argument("--now", default=None, help="HH:MM CT (default: the clock)")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import trading_calendar as cal
    except ImportError:
        print("REFUSED: trading_calendar.py is required for the session check.")
        return 1
    now = local_now()
    day = a.date or now.date()
    if a.now:
        h, m = (int(x) for x in a.now.split(":"))
        now_hm = (h, m)
    else:
        now_hm = (now.hour, now.minute)
    print("RUN GUARD - %s %02d:%02d CT (R2, DP-3C-ba)" % ((day,) + now_hm))
    # Resolve the flag EXACTLY as main.py will: main.py calls load_dotenv()
    # (which never overrides a variable already set in the console) and then
    # reads EQUITY_EDGAR. Reading os.environ alone would disagree with main.py
    # whenever the value comes from .env. Only this one variable is used.
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:                                   # noqa: BLE001
        pass
    ok, lines = check(day, now_hm, os.environ.get("EQUITY_EDGAR"), a.logs, cal)
    for ln in lines:
        print(ln)
    print("  -> %s" % ("RUN" if ok else "NOT RUN"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
