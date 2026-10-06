#!/usr/bin/env python3
"""
trading_calendar.py — the NYSE session calendar, computed and self-validating.

WHY THIS EXISTS
---------------
Every horizon in this project is defined in TRADING DAYS: a cohort's +5d
resolution date is the fifth NYSE session after it. Until now the tools derived
that calendar from the master's own cohort dates:

    dates = sorted({r["date"] for r in rows})
    idx   = {d: i for i, d in enumerate(dates)}      # "trading-day index"
    rdate = dates[idx[cohort] + n]                   # "+n trading days"

That is exact ONLY while the bot runs every session. It is not a calendar; it is
a list of the days somebody happened to run the bot, and it silently relabels
itself when a session is missed. `outcome_sanity.py`'s own header states the
assumption as a virtue -- "No holiday table, no network, no second source of
truth to drift" -- and the cost of that choice is invisible right up until a
session is skipped, at which point every mapping past the gap is wrong by the
size of the gap, in silence, with no finding raised.

THE TRIGGER: 2026-08-28 and 2026-08-31 are NYSE sessions on which the bot will
NOT run (operator away; pre-registered in
`Phase3C_VacationGap_PreRegistration_2026-08-26.md`). Under the derived-index
scheme the cohort list would jump 2026-08-27 -> 2026-09-01 and treat them as
adjacent, so:

    cohort 2026-08-26, +5d  ->  would resolve to 2026-09-08 (WRONG)
                                truth is 2026-09-02

...and the same two-session shift applies to every +5d cohort from 2026-08-24
onward, every +10d cohort from 2026-08-17, and every +20d cohort from 2026-07-30.
Roughly 26 tickers x 3 horizons x ~30 cohorts of mis-mapped resolution dates,
none of which would raise a finding, because the corrupted index is the same
index the checks use to decide what to compare.

GM's ONE missing row (2026-08-18) already cost four sessions of confusion in the
closing reviews. Two missing sessions across the whole cohort is that, times
twenty-six.

DISCIPLINE
----------
  * Pure computation. No network, no data files, no third-party calendar
    package, no state.
  * Holidays are RULES, not a hardcoded year list, so this does not expire.
  * `selftest()` validates the computed calendar against the master's own
    cohort dates. If the two ever disagree on a session the master covers,
    that is a finding and the selftest fails. The "second source of truth to
    drift" objection is answered by reconciling the two rather than by
    refusing to have a second source.
  * BOT_ABSENT records sessions the market was OPEN and the bot did not run.
    A date in here is a planned, dated absence -- never a way to hide a missed
    run after the fact. Adding an entry retroactively is an amendment.

SECOND GAP (added 2026-09-30, BEFORE it): 2026-10-01 (Thu) and 2026-10-05 (Mon)
are NYSE sessions on which the operator is travelling and the bot will not run.
Pre-registered in `Phase3C_AbsenceGap_PreRegistration_2026-09-30.md`. Unlike
August's, this gap is two SEPARATE single sessions with a run (2026-10-02) in
between, so the cohort list steps 09-30 -> 10-02 -> 10-06. No horizon moves:
every resolution date is computed here, not from the cohort list.

AMENDMENT (2026-10-06, AFTER the fact): 2026-10-02 was planned as a run and
was NOT run. It is added below, declared as an amendment, because without it
the master's cohort list (09-30 -> 10-06) fails reconciliation with a [CAL]
finding on 10-02 every day from now on. Recorded in
`Phase3C_GapAmendment_ReturnRunbook_2026-10-06.md`. The realised gap is three
sessions (10-01, 10-02, 10-05); the cohort list steps 09-30 -> 10-06.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import datetime as _dt

__all__ = [
    "is_trading_day", "sessions_between", "next_session", "prior_session",
    "shift_sessions", "session_index", "BOT_ABSENT", "AD_HOC_CLOSURES",
    "reconcile_against_cohorts", "selftest",
]


# =============================================================================
# BOT-ABSENT SESSIONS -- market open, no run. Dated, pre-registered, never
# added after the fact to paper over a miss.
# =============================================================================
#   date          -> (reason, pre-registration document)
BOT_ABSENT = {
    _dt.date(2026, 8, 28): ("operator away -- no run",
                            "Phase3C_VacationGap_PreRegistration_2026-08-26.md"),
    _dt.date(2026, 8, 31): ("operator away -- no run",
                            "Phase3C_VacationGap_PreRegistration_2026-08-26.md"),
    # Added 2026-09-30, BEFORE the sessions (operator travelling; the bot runs
    # on 2026-10-02 in between). Not an amendment: nothing here was missed.
    _dt.date(2026, 10, 1): ("operator travelling -- no run",
                            "Phase3C_AbsenceGap_PreRegistration_2026-09-30.md"),
    _dt.date(2026, 10, 5): ("operator travelling -- no run",
                            "Phase3C_AbsenceGap_PreRegistration_2026-09-30.md"),
    # AMENDMENT, added 2026-10-06 AFTER the session: 10-02 was planned as a run
    # (pre-registration §1) and was missed. Declared, not hidden.
    _dt.date(2026, 10, 2): ("AMENDMENT 2026-10-06 -- planned run missed (operator travelling); "
                            "recorded after the fact",
                            "Phase3C_GapAmendment_ReturnRunbook_2026-10-06.md"),
}


# =============================================================================
# AD-HOC CLOSURES -- NYSE closures that no rule produces (national days of
# mourning, weather). Empty is the correct state; add with a dated comment.
# =============================================================================
AD_HOC_CLOSURES: set[_dt.date] = set()


# -----------------------------------------------------------------------------
# Holiday rules
# -----------------------------------------------------------------------------
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> _dt.date:
    """n-th `weekday` (Mon=0) of month; n<0 counts back from the end."""
    if n > 0:
        d = _dt.date(year, month, 1)
        d += _dt.timedelta(days=(weekday - d.weekday()) % 7)
        return d + _dt.timedelta(weeks=n - 1)
    d = _dt.date(year, month, 28)
    while (d + _dt.timedelta(days=1)).month == month:
        d += _dt.timedelta(days=1)
    d -= _dt.timedelta(days=(d.weekday() - weekday) % 7)
    return d + _dt.timedelta(weeks=n + 1)


def _observed(d: _dt.date) -> _dt.date:
    """NYSE observance: Saturday -> preceding Friday, Sunday -> following Monday."""
    if d.weekday() == 5:
        return d - _dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + _dt.timedelta(days=1)
    return d


def _easter(year: int) -> _dt.date:
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return _dt.date(year, month, day + 1)


def market_holidays(year: int) -> set[_dt.date]:
    """The nine (ten since 2022) full-day NYSE closures for `year`."""
    return {
        _observed(_dt.date(year, 1, 1)),                 # New Year's Day
        _nth_weekday(year, 1, 0, 3),                     # MLK Day
        _nth_weekday(year, 2, 0, 3),                     # Washington's Birthday
        _easter(year) - _dt.timedelta(days=2),           # Good Friday
        _nth_weekday(year, 5, 0, -1),                    # Memorial Day
        _observed(_dt.date(year, 6, 19)),                # Juneteenth (from 2022)
        _observed(_dt.date(year, 7, 4)),                 # Independence Day
        _nth_weekday(year, 9, 0, 1),                     # Labor Day
        _nth_weekday(year, 11, 3, 4),                    # Thanksgiving
        _observed(_dt.date(year, 12, 25)),               # Christmas
    }


# -----------------------------------------------------------------------------
# Session predicates and arithmetic
# -----------------------------------------------------------------------------
def is_trading_day(d: _dt.date) -> bool:
    """True if the NYSE holds a session on `d`. Independent of whether the bot ran."""
    if d.weekday() >= 5:
        return False
    if d in AD_HOC_CLOSURES:
        return False
    return d not in market_holidays(d.year)


def next_session(d: _dt.date) -> _dt.date:
    d += _dt.timedelta(days=1)
    while not is_trading_day(d):
        d += _dt.timedelta(days=1)
    return d


def prior_session(d: _dt.date) -> _dt.date:
    d -= _dt.timedelta(days=1)
    while not is_trading_day(d):
        d -= _dt.timedelta(days=1)
    return d


def shift_sessions(d: _dt.date, n: int) -> _dt.date:
    """The session `n` trading days after (n>0) or before (n<0) `d`.

    THE HORIZON PRIMITIVE. `shift_sessions(cohort, 5)` is the +5d resolution
    date and is correct whether or not the bot ran on any day in between.
    """
    step = next_session if n > 0 else prior_session
    for _ in range(abs(n)):
        d = step(d)
    return d


def sessions_between(start: _dt.date, end: _dt.date) -> list[_dt.date]:
    """All NYSE sessions in [start, end], inclusive, ascending."""
    out, d = [], start
    while d <= end:
        if is_trading_day(d):
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def session_index(start: _dt.date, end: _dt.date) -> dict:
    """{session date -> 0-based ordinal} over [start, end]. The honest
    replacement for `{d: i for i, d in enumerate(sorted(cohort_dates))}`."""
    return {d: i for i, d in enumerate(sessions_between(start, end))}


# -----------------------------------------------------------------------------
# Reconciliation against the record
# -----------------------------------------------------------------------------
def reconcile_against_cohorts(cohort_dates) -> dict:
    """Compare the computed calendar against the master's own cohort dates.

    Returns {"missing": [...], "extra": [...], "absent_expected": [...]}:
      missing          -- sessions the calendar says exist with no cohort row,
                          and NOT recorded in BOT_ABSENT. These are the finding.
      extra            -- cohort rows on days the calendar says are not sessions.
                          Always a finding: either the calendar is wrong or the
                          master holds a row it should not.
      absent_expected  -- sessions with no cohort row that ARE in BOT_ABSENT.
                          Expected; reported so the gap stays visible.
    """
    cd = sorted({d.date() if isinstance(d, _dt.datetime) else d for d in cohort_dates})
    if not cd:
        return {"missing": [], "extra": [], "absent_expected": []}
    span = sessions_between(cd[0], cd[-1])
    have = set(cd)
    missing, absent_expected = [], []
    for d in span:
        if d in have:
            continue
        (absent_expected if d in BOT_ABSENT else missing).append(d)
    extra = [d for d in cd if not is_trading_day(d)]
    return {"missing": missing, "extra": extra, "absent_expected": absent_expected}


# -----------------------------------------------------------------------------
# Selftest
# -----------------------------------------------------------------------------
def _check(name, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {got!r}" + ("" if ok else f"  expected {want!r}"))
    return ok


def selftest(tracker: str | None = None) -> int:
    """Validate the rules, then reconcile against the master if one is given."""
    D = _dt.date
    ok = True
    print("trading_calendar selftest")
    print("-" * 66)

    # Holiday rules, 2026 -- the year the record covers.
    h26 = market_holidays(2026)
    ok &= _check("2026 New Year's Day (Thu)", D(2026, 1, 1) in h26, True)
    ok &= _check("2026 MLK Day = Jan 19", _nth_weekday(2026, 1, 0, 3), D(2026, 1, 19))
    ok &= _check("2026 Good Friday = Apr 3", _easter(2026) - _dt.timedelta(days=2), D(2026, 4, 3))
    ok &= _check("2026 Memorial Day = May 25", _nth_weekday(2026, 5, 0, -1), D(2026, 5, 25))
    ok &= _check("2026 Juneteenth = Jun 19 (Fri)", _observed(D(2026, 6, 19)), D(2026, 6, 19))
    ok &= _check("2026 July 4 falls Sat -> observed Fri Jul 3", _observed(D(2026, 7, 4)), D(2026, 7, 3))
    ok &= _check("2026 Labor Day = Sep 7", _nth_weekday(2026, 9, 0, 1), D(2026, 9, 7))
    ok &= _check("2026 Thanksgiving = Nov 26", _nth_weekday(2026, 11, 3, 4), D(2026, 11, 26))

    # Observance edges across years.
    ok &= _check("2027 Jan 1 falls Fri -> itself", _observed(D(2027, 1, 1)), D(2027, 1, 1))
    ok &= _check("2021 Jul 4 Sun -> observed Mon Jul 5", _observed(D(2021, 7, 4)), D(2021, 7, 5))

    # Session arithmetic ACROSS the vacation gap -- the case this exists for.
    ok &= _check("2026-08-28 IS a session (bot absent, market open)", is_trading_day(D(2026, 8, 28)), True)
    ok &= _check("2026-08-31 IS a session", is_trading_day(D(2026, 8, 31)), True)
    ok &= _check("+5d from 2026-08-26", shift_sessions(D(2026, 8, 26), 5), D(2026, 9, 2))
    ok &= _check("+5d from 2026-08-21 (lands IN the gap)", shift_sessions(D(2026, 8, 21), 5), D(2026, 8, 28))
    ok &= _check("+5d from 2026-08-24 (lands IN the gap)", shift_sessions(D(2026, 8, 24), 5), D(2026, 8, 31))
    ok &= _check("+20d from 2026-08-26 (crosses Labor Day)", shift_sessions(D(2026, 8, 26), 20), D(2026, 9, 24))
    ok &= _check("round trip +10/-10", shift_sessions(shift_sessions(D(2026, 8, 26), 10), -10), D(2026, 8, 26))
    ok &= _check("Labor Day 2026-09-07 is NOT a session", is_trading_day(D(2026, 9, 7)), False)

    # The SECOND pre-registered gap (2026-09-30): two single sessions with a
    # run between them. Resolution dates land IN the gap and must not move.
    ok &= _check("2026-10-01 IS a session (bot absent, market open)", is_trading_day(D(2026, 10, 1)), True)
    ok &= _check("2026-10-05 IS a session (bot absent, market open)", is_trading_day(D(2026, 10, 5)), True)
    ok &= _check("+5d from 2026-09-24 (TWST SELL open row) lands IN the gap",
                 shift_sessions(D(2026, 9, 24), 5), D(2026, 10, 1))
    ok &= _check("+5d from 2026-09-28 lands IN the gap", shift_sessions(D(2026, 9, 28), 5), D(2026, 10, 5))
    ok &= _check("+5d from 2026-10-02 crosses 10-05 = 2026-10-09", shift_sessions(D(2026, 10, 2), 5), D(2026, 10, 9))
    ok &= _check("+20d from 2026-09-14 = 2026-10-12 (signal_state prune date)",
                 shift_sessions(D(2026, 9, 14), 20), D(2026, 10, 12))
    # Reconciliation across the gap, with its FAILING case: the same cohort
    # list minus a pre-registration must surface the sessions as missing.
    _cds = [D(2026, 9, 29), D(2026, 9, 30), D(2026, 10, 2), D(2026, 10, 6)]
    _rec = reconcile_against_cohorts(_cds)
    ok &= _check("gap cohorts 09-30 -> 10-02 -> 10-06: nothing unexplained", _rec["missing"], [])
    ok &= _check("...and both sessions named as pre-registered",
                 _rec["absent_expected"], [D(2026, 10, 1), D(2026, 10, 5)])
    _saved = {d: BOT_ABSENT.pop(d) for d in (D(2026, 10, 1), D(2026, 10, 5))}
    try:
        _neg = reconcile_against_cohorts(_cds)
    finally:
        BOT_ABSENT.update(_saved)
    ok &= _check("NEGATIVE: without the entries both are MISSED RUNS",
                 _neg["missing"], [D(2026, 10, 1), D(2026, 10, 5)])

    # AMENDMENT 2026-10-06: the realised gap. 10-02 was not run, so the cohort
    # list steps 09-30 -> 10-06 across three sessions. With its FAILING case.
    _real = [D(2026, 9, 29), D(2026, 9, 30), D(2026, 10, 6)]
    _rec2 = reconcile_against_cohorts(_real)
    ok &= _check("realised gap 09-30 -> 10-06: nothing unexplained", _rec2["missing"], [])
    ok &= _check("...all three sessions named",
                 _rec2["absent_expected"], [D(2026, 10, 1), D(2026, 10, 2), D(2026, 10, 5)])
    ok &= _check("...and 10-02 is marked as an AMENDMENT",
                 BOT_ABSENT[D(2026, 10, 2)][0].startswith("AMENDMENT"), True)
    _amend = BOT_ABSENT.pop(D(2026, 10, 2))
    try:
        _neg2 = reconcile_against_cohorts(_real)
    finally:
        BOT_ABSENT[D(2026, 10, 2)] = _amend
    ok &= _check("NEGATIVE: without the amendment 10-02 is a MISSED RUN",
                 _neg2["missing"], [D(2026, 10, 2)])

    # The historical horizon mappings the record already relies on.
    ok &= _check("+5d from 2026-08-19 = 2026-08-26", shift_sessions(D(2026, 8, 19), 5), D(2026, 8, 26))
    ok &= _check("+10d from 2026-08-12 = 2026-08-26", shift_sessions(D(2026, 8, 12), 10), D(2026, 8, 26))
    ok &= _check("+20d from 2026-07-29 = 2026-08-26", shift_sessions(D(2026, 7, 29), 20), D(2026, 8, 26))

    if tracker:
        print("-" * 66)
        try:
            import openpyxl
            wsheet = openpyxl.load_workbook(tracker, data_only=True)["Signals"]
            cds = []
            r = 5
            while wsheet.cell(r, 1).value is not None:
                cds.append(wsheet.cell(r, 1).value)
                r += 1
            rec = reconcile_against_cohorts(cds)
            ok &= _check("no unexplained missing sessions vs master", rec["missing"], [])
            ok &= _check("no cohort rows on non-sessions", rec["extra"], [])
            if rec["absent_expected"]:
                print(f"  [note] pre-registered bot-absent sessions in range: "
                      f"{[str(d) for d in rec['absent_expected']]}")
        except Exception as e:                                  # pragma: no cover
            print(f"  [SKIP] master reconciliation unavailable: {e}")

    print("-" * 66)
    print("ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    import os
    ap = argparse.ArgumentParser(description="NYSE session calendar.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--shift", nargs=2, metavar=("YYYY-MM-DD", "N"),
                    help="print the session N trading days from a date")
    a = ap.parse_args()
    if a.shift:
        d0 = _dt.date.fromisoformat(a.shift[0])
        print(shift_sessions(d0, int(a.shift[1])))
        raise SystemExit(0)
    raise SystemExit(selftest(a.tracker if os.path.exists(a.tracker) else None))
