#!/usr/bin/env python3
"""
apply_repair_calendar_fix.py — put `repair_outcome_close.py` on the real calendar.

WHY THIS ONE MATTERS MORE THAN THE GATE'S
-----------------------------------------
`outcome_sanity.py` derives its trading-day index from the master's own cohort
dates and READS. `repair_outcome_close.py` does the same thing and WRITES. It
locates the cells to repair by resolution date -- deliberately, because "row
numbers shift" -- and that location is computed as

    dates = sorted({r["date"] for r in rows})
    idx   = {d: i for i, d in enumerate(dates)}
    ... if dates[i + n] == target

With 2026-08-28 and 2026-08-31 missing from the cohort list (pre-registered
no-run sessions), that index treats 08-27 and 09-01 as adjacent. A repair run
after the gap would resolve `target` to a cell TWO SESSIONS away from the one it
names on screen, print a confident "located by date, not by row number" banner,
and write a correct price into the wrong cell -- creating exactly the class of
defect this module exists to fix, by machine, with a backup taken of the
already-correct file.

It also refuses outright any target that is not itself a cohort date. After the
gap, 2026-08-28 and 2026-08-31 ARE resolution dates for cohorts 2026-08-21 and
2026-08-24 -- the sessions whose outcomes must be entered on return -- and the
module would decline to repair them at all.

Both problems are the same problem: a session list is not a calendar.

WHAT CHANGES
------------
  * `trading_calendar.shift_sessions()` replaces the derived index everywhere
    it decides which cell resolves when.
  * The target may be any NYSE session, cohort row or not, so the vacation-gap
    resolution dates are repairable.
  * The plausibility guard's "adjacent closes" become adjacent SESSIONS rather
    than adjacent cohort rows -- a distinction that only bites across a gap,
    which is precisely when a repair is most likely to be needed.

No endpoint, bar, arm or n moves. Behaviour on a gap-free record is identical.

Dry run by default. `--apply` writes, after a timestamped .bak.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import os
import shutil
import sys

TARGET = "repair_outcome_close.py"


def _lf(s: str) -> str:
    return s.replace("\r\n", "\n")


def _dominant_ending(s: str) -> str:
    crlf = s.count("\r\n")
    return "\r\n" if crlf and crlf >= (s.count("\n") - crlf) else "\n"


def _restore(s: str, ending: str) -> str:
    return s.replace("\n", ending) if ending == "\r\n" else s


EDITS = [
    (
        "import the calendar",
        'def recorded_close(rows, idx, dates, tkr, on_date):\n',

        '# AMENDED 2026-08-26. Cell location used to run off an index derived from\n'
        '# the master\'s own cohort dates. That is a list of days somebody ran the bot,\n'
        '# not a calendar, and this module WRITES: across a missed session it would\n'
        '# have located a cell two sessions from the one it names. See\n'
        '# Phase3C_VacationGap_PreRegistration_2026-08-26.md.\n'
        'try:\n'
        '    from trading_calendar import shift_sessions as _shift, is_trading_day as _is_sess\n'
        'except ImportError:                                    # pragma: no cover\n'
        '    _shift = _is_sess = None\n'
        '\n'
        '\n'
        'def recorded_close(rows, idx, dates, tkr, on_date):\n',
    ),
    (
        "recorded_close(): resolve on sessions",
        '        i = idx[r["date"]]\n'
        '        for label, pcol, _, n in HORIZONS:\n'
        '            v = r[pcol]\n'
        '            if not num(v) or i + n >= len(dates):\n'
        '                continue\n'
        '            if dates[i + n] == on_date:\n'
        '                vals.add(round(float(v), 6))\n',

        '        for label, pcol, _, n in HORIZONS:\n'
        '            v = r[pcol]\n'
        '            if not num(v):\n'
        '                continue\n'
        '            if _resolve(r["date"], n, idx, dates) == on_date:\n'
        '                vals.add(round(float(v), 6))\n',
    ),
    (
        "main(): accept any NYSE session as the target, not only a cohort date",
        '    rows = load_rows(args.tracker)\n'
        '    dates = sorted({r["date"] for r in rows})\n'
        '    idx = {d: i for i, d in enumerate(dates)}\n'
        '    if target not in idx:\n'
        '        print("  ERROR: %s is not a cohort date in the master. The trading-day index "\n'
        '              "is derived from the master\'s own dates; a date it has never seen "\n'
        '              "cannot be located." % target)\n'
        '        return 2\n',

        '    rows = load_rows(args.tracker)\n'
        '    dates = sorted({r["date"] for r in rows})\n'
        '    idx = {d: i for i, d in enumerate(dates)}          # legacy fallback only\n'
        '    if _is_sess is not None:\n'
        '        if not _is_sess(target):\n'
        '            print("  ERROR: %s is not an NYSE session." % target)\n'
        '            return 2\n'
        '        if target not in idx:\n'
        '            # A session with no cohort row is still a resolution date. This is\n'
        '            # the pre-registered vacation-gap case (2026-08-28, 2026-08-31):\n'
        '            # the market traded, outcomes exist, the bot did not run.\n'
        '            print("  NOTE: %s is an NYSE session with no cohort row in the master."\n'
        '                  % target)\n'
        '            print("        Repairing its resolution cells anyway - the outcome is")\n'
        '            print("        real whether or not the bot ran that morning.")\n'
        '    elif target not in idx:                            # pragma: no cover\n'
        '        print("  ERROR: %s is not a cohort date and trading_calendar.py is not "\n'
        '              "importable, so no session calendar is available." % target)\n'
        '        return 2\n',
    ),
    (
        "main(): locate cells on sessions",
        '        i = idx[r["date"]]\n'
        '        for label, pcol, rcol, n in HORIZONS:\n'
        '            if i + n >= len(dates) or dates[i + n] != target:\n'
        '                continue\n'
        '            targets.append((r, label, pcol, rcol))\n',

        '        for label, pcol, rcol, n in HORIZONS:\n'
        '            if _resolve(r["date"], n, idx, dates) != target:\n'
        '                continue\n'
        '            targets.append((r, label, pcol, rcol))\n',
    ),
    (
        "plausibility guard: adjacent SESSIONS, not adjacent cohort rows",
        '    i_t = idx[target]\n'
        '    prev_d = dates[i_t - 1] if i_t > 0 else None\n'
        '    next_d = dates[i_t + 1] if i_t + 1 < len(dates) else None\n',

        '    if _shift is not None:\n'
        '        prev_d = _shift(target, -1)\n'
        '        next_d = _shift(target, 1)\n'
        '        if next_d > dates[-1]:\n'
        '            next_d = None\n'
        '    else:                                              # pragma: no cover\n'
        '        i_t = idx[target]\n'
        '        prev_d = dates[i_t - 1] if i_t > 0 else None\n'
        '        next_d = dates[i_t + 1] if i_t + 1 < len(dates) else None\n',
    ),
]

HELPER = (
    '\n'
    'def _resolve(cohort_date, n, idx, dates):\n'
    '    """The +n-trading-day resolution date for `cohort_date`.\n'
    '\n'
    '    Uses the NYSE calendar when available, so it is correct whether or not the\n'
    '    bot ran on any session in between. Falls back to the old cohort-derived\n'
    '    index only if trading_calendar.py is missing -- in which case it is wrong\n'
    '    across a gap, exactly as before, and the caller has been warned.\n'
    '    """\n'
    '    if _shift is not None:\n'
    '        return _shift(cohort_date, n)\n'
    '    i = idx.get(cohort_date)                               # pragma: no cover\n'
    '    if i is None or i + n >= len(dates):\n'
    '        return None\n'
    '    return dates[i + n]\n'
    '\n'
    '\n'
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Calendar fix for repair_outcome_close.py.")
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
    for name, old, new in EDITS:
        old, new = _lf(old), _lf(new)
        n = text.count(old)
        if n != 1:
            print("REFUSING: anchor %r matched %d times (expected 1)." % (name, n), file=sys.stderr)
            print("Nothing was changed.", file=sys.stderr)
            return 2
        text = text.replace(old, new, 1)

    anchor = _lf('def recorded_close(rows, idx, dates, tkr, on_date):\n')
    if text.count(anchor) != 1:
        print("REFUSING: helper insertion anchor not unique.", file=sys.stderr)
        return 2
    text = text.replace(anchor, _lf(HELPER) + anchor, 1)

    print("=" * 78)
    print("REPAIR_OUTCOME_CLOSE CALENDAR FIX - %s" % a.file)
    print("=" * 78)
    for i, (name, _, _) in enumerate(EDITS, 1):
        print("  %d. %s" % (i, name))
    print("-" * 78)
    for line in difflib.unified_diff(original.splitlines(), text.splitlines(),
                                     fromfile=a.file + " (current)",
                                     tofile=a.file + " (fixed)", lineterm="", n=2):
        print(line)
    print("-" * 78)
    print("  Behaviour on a gap-free record is identical. No endpoint moves.")
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
