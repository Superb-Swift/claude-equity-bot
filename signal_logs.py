#!/usr/bin/env python3
"""
signal_logs.py — find every signals log, including the archived ones.

WHY THIS EXISTS (2026-09-08)
    The 2026-08-27 closing review recorded the WS1 gate-flip ledger as
    "4 resolved gate-flips, net +2, and 3 of 4 favoured the blend". On
    2026-09-08 `monitor_strip` printed "gate-flip net -1 (1 flip(s));
    confirm 0% (n=0) vs discount 100% (n=3)" and listed a single flip.

    A RESOLVED GATE-FLIP CANNOT UN-RESOLVE. The ledger had lost three quarters
    of its rows, and nothing in the run said so.

    THE CAUSE, verified by listing the directory: `logs/` holds only five
    `signals_*.log` files (2026-09-01 .. 2026-09-08). Every earlier log is
    still on disk, filed into month subfolders — `05 May signals`,
    `06 June signals`, `07 July Signals`, `08 August Signals`. Nothing was
    deleted. The default pattern `logs/signals_*.log` is NON-RECURSIVE, so the
    moment the logs were tidied, every tool reading them silently narrowed to
    the current month and reported the result as if it were the whole record.

    The blend channel lives ONLY in the logs — there is no tracker column for
    it, by design — so for WS1 the log set IS the ledger. Narrowing it does not
    degrade the reading; it silently replaces it with a different one.

    This is the DP-3C-i lesson in a second place: state that survives nowhere
    durable will eventually be reorganised by someone with good intentions.

WHAT THIS FIXES, AND WHAT IT DOES NOT
    It restores the FULL log set to any tool that asks. It does not reconstruct
    the ledger, take a reading, or touch WS1's DESCOPED status — readings on
    that channel remain context only. It also cannot recover a log that was
    genuinely deleted; `report()` states the span found so a caller can see
    what it is actually reading before quoting a figure from it.

    `Retired/` is EXCLUDED by default. A log filed there was withdrawn
    deliberately, and silently folding it back in would be the mirror image of
    the defect above. The exclusion is counted and reported, never silent.
"""

import datetime as dt
import glob
import os
import re

DEFAULT_PATTERN = os.path.join("logs", "signals_*.log")
EXCLUDE_DIRS = {"retired"}
_DATE_RE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})")


def log_date(path):
    """The cohort date a log filename encodes, or None."""
    m = _DATE_RE.search(os.path.basename(path))
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def discover(pattern=DEFAULT_PATTERN, include_retired=False):
    """Every signals log reachable from `pattern`'s directory, archived ones
    included. Returns (paths_sorted_by_date, info_dict).

    Deduplicated by BASENAME: a log present both loose and archived is one
    cohort, not two, and counting it twice would inflate every denominator
    built on top of it. The shallowest copy wins, arbitrarily but stably.
    """
    root = os.path.dirname(pattern) or "."
    base = os.path.basename(pattern)

    found, excluded = {}, 0
    for p in glob.glob(os.path.join(root, "**", base), recursive=True):
        parts = [seg.lower() for seg in os.path.normpath(p).split(os.sep)[:-1]]
        if not include_retired and any(seg in EXCLUDE_DIRS for seg in parts):
            excluded += 1
            continue
        name = os.path.basename(p)
        prev = found.get(name)
        if prev is None or p.count(os.sep) < prev.count(os.sep):
            found[name] = p

    paths = sorted(found.values(), key=lambda p: (log_date(p) or dt.date.min, p))
    dated = [d for d in (log_date(p) for p in paths) if d]
    loose = sum(1 for p in paths if os.path.dirname(p).rstrip(os.sep) == root.rstrip(os.sep))
    info = dict(n=len(paths), n_archived=len(paths) - loose, n_loose=loose,
                n_excluded_retired=excluded,
                first=min(dated) if dated else None,
                last=max(dated) if dated else None)
    return paths, info


def report(info, indent="  "):
    """One quotable line stating what the caller is actually reading."""
    if not info["n"]:
        return f"{indent}[logs] NONE FOUND — any log-derived figure below is empty, not zero"
    span = (f"{info['first']} .. {info['last']}"
            if info["first"] else "undated")
    bits = [f"{info['n']} log(s)", span]
    if info["n_archived"]:
        bits.append(f"{info['n_archived']} from archive subfolder(s)")
    if info["n_excluded_retired"]:
        bits.append(f"{info['n_excluded_retired']} excluded (Retired/)")
    return f"{indent}[logs] " + " · ".join(bits)


def short_span_warning(info, min_days=45, indent="  "):
    """Warn when the visible history is too short to carry a cumulative ledger.

    Returns "" when the span is adequate. The threshold is a REPORTING trigger,
    not a bar: it exists so that a truncated log set announces itself instead of
    being read as a complete record, which is exactly what happened on
    2026-09-08."""
    if not info["n"] or not info["first"] or not info["last"]:
        return f"{indent}[logs] WARNING: no dated logs — cumulative ledgers below are empty"
    span = (info["last"] - info["first"]).days
    if span >= min_days:
        return ""
    return (f"{indent}[logs] WARNING: only {span} day(s) of logs visible "
            f"({info['first']} .. {info['last']}). Any CUMULATIVE figure below "
            f"— gate-flip ledgers above all — covers this window ONLY and must "
            f"not be quoted as the full record.")


if __name__ == "__main__":
    import sys
    pat = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATTERN
    paths, info = discover(pat)
    print(report(info, indent=""))
    w = short_span_warning(info, indent="")
    if w:
        print(w)
    for p in paths:
        print(f"  {log_date(p)}  {p}")
