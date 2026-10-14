#!/usr/bin/env python3
"""
review_artifacts.py - did THIS run of run_daily_review.bat write its outputs?

WHY (proposed 2026-10-09): value.bat has checked its exhibits against the run's
start time since 2026-08-19 ("an exit code is a claim; the artifact is the
evidence"). run_daily_review.bat has no such check and no exit code, and its
output - tracker_with_registry.xlsx - is the file read as the final word. A
step that fails leaves last session's sheet in place, looking current.

Read-only. Touches no workbook. Exit 0 = every artifact written this run,
1 = something is STALE or ABSENT, 2 = usage.

    python review_artifacts.py --t0 <epoch seconds at the start of the run>
"""
import argparse
import os
import sys
import time

EXHIBITS = [
    "h1_lag_trace_WMT.md", "h1_lag_trace_GM.md",
    "h1_lag_trace_WMT_3B.md", "h1_lag_trace_GM_3B.md",
    "h1_lag_trace_WMT_raw_3B.md", "h1_lag_trace_GM_raw_3B.md",
    "h4_dq_threshold_baseline.md",
    "near_miss_registry.md", "actionable_registry.md", "monitor_strip.md",
    "e4_counter.md",
]
REPORT = "tracker_with_registry.xlsx"
SHEETS = ["Near-Miss BUYs", "Actionable BUYs", "Monitor Strip"]


def state(path, t0):
    if not os.path.exists(path):
        return "ABSENT"
    return "WRITTEN this run" if os.path.getmtime(path) >= t0 else "STALE - from an earlier run"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, required=True)
    ap.add_argument("--dir", default=".")
    a = ap.parse_args(argv)
    bad = 0
    print("Review artifacts (state read from disk, not assumed):")
    for name in EXHIBITS + [REPORT]:
        s = state(os.path.join(a.dir, name), a.t0)
        bad += not s.startswith("WRITTEN")
        print(f"   {name:<32} {s}")
    rp = os.path.join(a.dir, REPORT)
    if os.path.exists(rp):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(rp, read_only=True)
            have = set(wb.sheetnames)
            wb.close()
            for sh in SHEETS:
                ok = sh in have
                bad += not ok
                print(f"   sheet '{sh}'{'':<{max(0, 22 - len(sh))}} {'present' if ok else 'MISSING'}")
        except Exception as e:  # noqa: BLE001
            bad += 1
            print(f"   could not open {REPORT}: {e}")
    if bad:
        print(f"REVIEW INCOMPLETE - {bad} artifact(s) not written this run. "
              "Do not read the report copy as current.")
        return 1
    print("REVIEW COMPLETE - every exhibit and sheet was written this run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
