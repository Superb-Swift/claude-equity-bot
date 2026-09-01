#!/usr/bin/env python3
"""
apply_h1_trace_fixes.py — three corrections to `h1_lag_trace.py`.

None of these moves an endpoint, a bar, an arm or an n. They correct a printed
arithmetic error, a wrong provenance line, and an incomplete disclosure note.
Raised in the 2026-08-26 closing review, §3.2, §3.3 and §3.1.

  1. GUARDRAIL DENOMINATOR (arithmetic defect).
     `band_calibration()` increments the band denominator for EVERY row in the
     band and the numerator only on `right5 == "YES"`. Rows whose +5d has not
     resolved therefore count as misses. Measured against the master on the
     2026-08-26 slice:

         band     printed        correct        error
         40-49    112/245 45.7%  112/220 50.9%  -5.2 pt
         50-59    100/190 52.6%  100/161 62.1%  -9.5 pt
         60-69    155/302 51.3%  155/255 60.8%  -9.5 pt

     The deflation is NOT uniform -- it depends on the unresolved tail's band
     mix -- so it distorts comparisons between bands as well as levels, and it
     grows every session that adds unresolved rows. The block is RETIRED and is
     explicitly not a pass/fail signal, so nothing is re-read; a retired figure
     that silently drifts is still worth not printing.

  2. PROVENANCE (wrong source attribution).
     Under `--raw-from-logs` the `Conf` column carries the RAW pre-damping
     channel, which lives in the session logs. The header credits only
     `claude_equity_bot_tracker.xlsx`, which stores the OPERATIVE value. On
     2026-08-26 the WMT exhibit printed 42/38/38 for 08-20..08-24 where the
     master holds 0.35 on all three -- the D1 floor. A reader cross-checking a
     lag figure against the workbook finds a mismatch and concludes the exhibit
     is wrong. GM shows no discrepancy because GM was never damped, so raw and
     operative coincide: THE DEFECT IS INVISIBLE ON EVERY NAME EXCEPT A DAMPED
     ONE, which is the population this exhibit exists to study.

  3. TRAIL BASIS NOTE (incomplete disclosure).
     The note names two differences -- tracker rows vs market sessions, and
     Price at Signal vs closes. There is a third, and on 2026-08-26 it was the
     dominant one: the run's window is SHIFTED ONE SESSION FORWARD and its
     right edge is a live intraday print (see `trail_basis_audit.py` and
     `H1_Window_OffByOne_Defect_2026-08-26.md`). WMT read +0.78% on the run
     against -10.20% here -- opposite signs, 10.98 points, on the WS2 tracer --
     and under the documented contract THIS EXHIBIT'S figure is the closer one.

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

TARGET = "h1_lag_trace.py"


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
        "band_calibration(): denominator counts RESOLVED rows only",
        "        agg[b][1] += 1\r\n"
        "        if str(ws.cell(row=r, column=COL[\"right5\"]).value or \"\").strip().upper() == \"YES\":\r\n"
        "            agg[b][0] += 1\r\n",

        "        # FIXED 2026-08-26. This previously incremented the denominator\r\n"
        "        # for EVERY row in the band and the numerator only on YES, so an\r\n"
        "        # unresolved +5d counted as a miss. On the 2026-08-26 slice that\r\n"
        "        # deflated the three printed rates by 5.2, 9.5 and 9.5 points --\r\n"
        "        # non-uniformly, because it depends on the unresolved tail's band\r\n"
        "        # mix, and worst on the newest data. A row belongs in the\r\n"
        "        # denominator only once it has an outcome.\r\n"
        "        verdict = str(ws.cell(row=r, column=COL[\"right5\"]).value or \"\").strip().upper()\r\n"
        "        if verdict not in (\"YES\", \"NO\"):\r\n"
        "            continue\r\n"
        "        agg[b][1] += 1\r\n"
        "        if verdict == \"YES\":\r\n"
        "            agg[b][0] += 1\r\n",
    ),
    (
        "trace(): carry the raw-override count out to the exhibit",
        "    return dict(best_L=best_L, r_now=r_now, r_fwd=r_fwd, ok_cal=ok_cal,\r\n"
        "                cache_blank=cache_blank,\r\n"
        "                rows=rows, trail=trail, arc=arc, agg=agg)\r\n",

        "    return dict(best_L=best_L, r_now=r_now, r_fwd=r_fwd, ok_cal=ok_cal,\r\n"
        "                cache_blank=cache_blank,\r\n"
        "                raw_rows=n_raw, raw_used=(raw_map is not None),\r\n"
        "                rows=rows, trail=trail, arc=arc, agg=agg)\r\n",
    ),
    (
        "write_md(): name BOTH sources when the raw channel is in use",
        "    lines = [f\"# H1 Lag Trace — {ticker}\",\r\n"
        "             f\"*Source: `{os.path.basename(tracker)}` · window {window}d · \"\r\n"
        "             f\"generated {dt.datetime.now():%Y-%m-%d %H:%M}.*\", \"\",\r\n",

        "    # PROVENANCE, corrected 2026-08-26. Under --raw-from-logs the Conf\r\n"
        "    # column is the RAW pre-damping channel, which is NOT in the tracker --\r\n"
        "    # the tracker stores the OPERATIVE value. Crediting only the workbook\r\n"
        "    # made the WMT exhibit look wrong against its own stated source on\r\n"
        "    # every damped row (08-20..08-24 printed 42/38/38 against a stored\r\n"
        "    # 0.35, the D1 floor). Say where each column came from.\r\n"
        "    if res.get(\"raw_used\"):\r\n"
        "        src = (f\"*Prices and outcomes: `{os.path.basename(tracker)}`. \"\r\n"
        "               f\"**`Conf` is the RAW pre-damping channel, parsed from the \"\r\n"
        "               f\"session logs** ({res.get('raw_rows', 0)} row(s) overridden; \"\r\n"
        "               f\"the rest fall back to the tracker's operative value, which \"\r\n"
        "               f\"equals raw wherever damping was inactive). The tracker \"\r\n"
        "               f\"itself stores OPERATIVE confidence and will differ from \"\r\n"
        "               f\"this column on any damped row.* · window {window}d · \"\r\n"
        "               f\"generated {dt.datetime.now():%Y-%m-%d %H:%M}.\")\r\n"
        "    else:\r\n"
        "        src = (f\"*Source: `{os.path.basename(tracker)}` (`Conf` is the \"\r\n"
        "               f\"OPERATIVE, post-damping channel) · window {window}d · \"\r\n"
        "               f\"generated {dt.datetime.now():%Y-%m-%d %H:%M}.*\")\r\n"
        "    lines = [f\"# H1 Lag Trace — {ticker}\", src, \"\",\r\n",
    ),
    (
        "write_md(): TRAIL BASIS note gains its third and largest term",
        "        \"> **TRAIL BASIS.** `Trail\" + str(window) + \"d` walks back \" + str(window)\r\n"
        "        + \" **tracker rows** (a session this ticker missed is skipped, not counted) \"\r\n"
        "          \"and prices off **Price at Signal**, a ~09:3x quote. The run's own \"\r\n"
        "          \"`H1[trail5d=…]` / `D[trail=…]` tags walk back \" + str(window)\r\n"
        "        + \" **market sessions** and price off **closes**. The two can differ in \"\r\n"
        "          \"magnitude and, where a row is missing, in SIGN. Recorded 2026-08-21 \"\r\n"
        "          \"after GM read −0.31% here against +2.75% in the run.\", \"\"]\r\n",

        "        \"> **TRAIL BASIS — THREE differences, not two.** `Trail\" + str(window)\r\n"
        "        + \"d` walks back \" + str(window)\r\n"
        "        + \" **tracker rows** (a session this ticker missed is skipped, not counted) \"\r\n"
        "          \"and prices off **Price at Signal**, a ~09:3x quote, ending at the \"\r\n"
        "          \"most recent row. The run's own `H1[trail5d=…]` / `D[trail=…]` tags \"\r\n"
        "          \"price off **closes** — but their window is **shifted one session \"\r\n"
        "          \"forward and its right edge is a live intraday print**, because \"\r\n"
        "          \"`schwab_client.get_price_history()` dates candles in local time and \"\r\n"
        "          \"admits the in-progress session (measured every run by \"\r\n"
        "          \"`trail_basis_audit.py`; diagnosis in \"\r\n"
        "          \"`H1_Window_OffByOne_Defect_2026-08-26.md`). **That third term is \"\r\n"
        "          \"the largest.** Recorded 2026-08-21 after GM read −0.31% here \"\r\n"
        "          \"against +2.75% in the run; amended 2026-08-26 after WMT read \"\r\n"
        "          \"**−10.20% here against +0.78% in the run** — opposite signs, 10.98 \"\r\n"
        "          \"points, on the WS2 tracer. Under the documented contract for that \"\r\n"
        "          \"function, **this column is the closer of the two**; the run's \"\r\n"
        "          \"figure is the one that is wrong, and THETA damping uses it.\", \"\"]\r\n",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Three non-endpoint fixes to h1_lag_trace.py.")
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
            print("REFUSING: anchor %r matched %d times (expected exactly 1)." % (name, n),
                  file=sys.stderr)
            print("Nothing was changed.", file=sys.stderr)
            return 2
        text = text.replace(old, new, 1)

    print("=" * 78)
    print("H1_LAG_TRACE FIXES - %s" % a.file)
    print("=" * 78)
    for i, (name, _, _) in enumerate(EDITS, 1):
        print("  %d. %s" % (i, name))
    print("-" * 78)
    for line in difflib.unified_diff(original.splitlines(), text.splitlines(),
                                     fromfile=a.file + " (current)",
                                     tofile=a.file + " (fixed)", lineterm="", n=2):
        print(line)
    print("-" * 78)
    print("  No endpoint, bar, arm or n moves. The retired guardrail block stays")
    print("  retired; only its arithmetic changes.")
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
