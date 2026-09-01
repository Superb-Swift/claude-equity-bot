#!/usr/bin/env python3
"""
propose_h1_window_fix.py — the remedy for the H1 window off-by-one.

*** THIS IS A PROPOSAL. IT IS NOT APPLIED, AND APPLYING IT MOVES ENDPOINTS. ***

WHAT IT FIXES
-------------
`schwab_client.get_price_history()` dates each Schwab candle with local-time
`datetime.fromtimestamp()`. Schwab stamps the candle in a zone east of this
machine, so every candle is dated ONE DAY EARLY. Two things follow:

  * today's IN-PROGRESS candle passes the `cdate < today` filter and its last
    intraday print is returned as a completed close; and
  * the oldest real session falls out of the `closes[-days:]` tail.

The window is therefore shifted one session forward and its right edge is a live
print rather than a settled close. See `trail_basis_audit.py` (measures it, every
session, from evidence) and `H1_Window_OffByOne_Defect_2026-08-26.md`.

WHY IT IS NOT APPLIED
---------------------
`risk_engine.compute_trail_pct()` reads this list, so the number feeds THETA
damping -> operative confidence -> the signal -> every endpoint, arm and n in
the record. Measured on the 2026-08-26 cohort, the correction moves **3 of 24**
rows' operative confidence:

    DOW  36 -> 42     (run trail -8.75%  vs contract -5.01%  -> damp 6 -> 0)
    PWR  49 -> 45     (run trail -8.28%  vs contract -10.87% -> damp 5 -> 9)
    WMT  42 -> 38     (run trail +0.78%  vs contract -7.80%  -> damp 0 -> 4)

No row crossed the 70% gate on that day, so no disposition changed -- but that
is one session, not a bound. WMT is the WS2 tracer, and under the correction its
adverse-move episode stays OPEN where the run closes it, which is precisely the
G1 ambiguity recorded in the 2026-08-26 closing review §4.5. CBRS's damp would
also move 14 -> 15 and bind against `DampingConfig.CAP`.

That is an amendment, not a bug fix, and it belongs to the operator.
DP-3C-o is the precedent for how an era break of this kind gets fenced.

USAGE
-----
    python propose_h1_window_fix.py                 # dry run, prints the diff
    python propose_h1_window_fix.py --apply         # writes, after a .bak
    python propose_h1_window_fix.py --apply --era   # also prints the era-bump
                                                    # checklist it does NOT do

Refuses and changes nothing if any anchor has drifted.

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import sys

TARGET = "schwab_client.py"


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
        "imports: market-timezone awareness",
        "The bug is a timezone assumption, so the fix needs an explicit zone. "
        "zoneinfo is stdlib on 3.9+; the fallback keeps the module importable "
        "on a stripped runtime rather than failing closed on a data layer.",
        "import os\r\n"
        "import schwab\r\n"
        "from datetime import datetime\r\n"
        "from dotenv import load_dotenv\r\n",

        "import os\r\n"
        "import schwab\r\n"
        "from datetime import datetime, timezone\r\n"
        "from dotenv import load_dotenv\r\n"
        "\r\n"
        "# H1 WINDOW FIX (proposed 2026-08-26): Schwab stamps daily candles in a\r\n"
        "# zone east of this machine. Converting with local-time fromtimestamp()\r\n"
        "# dated every candle one day early, which let today's in-progress candle\r\n"
        "# through the completed-sessions filter. Both sides of the comparison are\r\n"
        "# now explicit: candle dates come from UTC, 'today' comes from Eastern.\r\n"
        "try:\r\n"
        "    from zoneinfo import ZoneInfo\r\n"
        "    _MARKET_TZ = ZoneInfo(\"America/New_York\")\r\n"
        "except Exception:                      # pragma: no cover\r\n"
        "    _MARKET_TZ = timezone.utc\r\n",
    ),
    (
        "get_price_history: date candles in UTC, compare against Eastern today",
        "`datetime.fromtimestamp(ts/1000)` uses the LOCAL zone. On a UTC-5 "
        "machine a candle stamped at 00:00 UTC (or 00:00 ET) lands on the "
        "PREVIOUS calendar day, so `cdate < today` admitted the running "
        "session. Dating in UTC and comparing against the market's own today "
        "removes both halves of that assumption. The added guard states what "
        "was previously only promised in the docstring.",

        "        today = datetime.now().date()\r\n"
        "        closes = []\r\n"
        "        for c in candles:\r\n"
        "            ts = c.get(\"datetime\")\r\n"
        "            close = c.get(\"close\")\r\n"
        "            if ts is None or close is None:\r\n"
        "                continue\r\n"
        "            # Schwab candle 'datetime' is epoch milliseconds.\r\n"
        "            cdate = datetime.fromtimestamp(ts / 1000).date()\r\n"
        "            if cdate < today:                 # completed sessions only\r\n"
        "                closes.append({\"date\": cdate.isoformat(), \"close\": close})\r\n"
        "\r\n"
        "        return closes[-days:]\r\n",

        "        today = datetime.now(_MARKET_TZ).date()\r\n"
        "        closes = []\r\n"
        "        for c in candles:\r\n"
        "            ts = c.get(\"datetime\")\r\n"
        "            close = c.get(\"close\")\r\n"
        "            if ts is None or close is None:\r\n"
        "                continue\r\n"
        "            # Schwab candle 'datetime' is epoch milliseconds, stamped in a\r\n"
        "            # market-side zone. Date it in UTC and compare against the\r\n"
        "            # market's own 'today' -- never the machine's local date.\r\n"
        "            cdate = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()\r\n"
        "            if cdate < today:                 # completed sessions only\r\n"
        "                closes.append({\"date\": cdate.isoformat(), \"close\": close})\r\n"
        "\r\n"
        "        # The docstring promises the in-progress candle is excluded. Say so\r\n"
        "        # out loud rather than trusting it: this is the exact condition that\r\n"
        "        # silently held from at least 2026-08-13 to 2026-08-26.\r\n"
        "        if closes and closes[-1][\"date\"] >= today.isoformat():\r\n"
        "            print(f\"[schwab_client] WARNING: newest candle for {ticker} is \"\r\n"
        "                  f\"{closes[-1]['date']} against market today {today} -- \"\r\n"
        "                  f\"an in-progress session reached the H1 window.\")\r\n"
        "\r\n"
        "        return closes[-days:]\r\n",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Proposed H1 window fix (NOT applied by default).")
    ap.add_argument("--file", default=TARGET)
    ap.add_argument("--apply", action="store_true",
                    help="write the change (endpoint-moving; see the module docstring)")
    ap.add_argument("--era", action="store_true",
                    help="print the era-bump checklist this script deliberately does NOT perform")
    a = ap.parse_args()

    if not os.path.exists(a.file):
        print("ERROR: not found: %s" % a.file, file=sys.stderr)
        return 2

    with open(a.file, "r", encoding="utf-8", newline="") as fh:
        raw = fh.read()
    ending = _dominant_ending(raw)
    original = _lf(raw)

    text = original
    for name, why, old, new in EDITS:
        old, new = _lf(old), _lf(new)
        n = text.count(old)
        if n != 1:
            print("REFUSING: anchor %r matched %d times (expected exactly 1)." % (name, n),
                  file=sys.stderr)
            print("The file has drifted from what this patch was written against.", file=sys.stderr)
            print("Nothing was changed. Re-derive the anchors before applying.", file=sys.stderr)
            return 2
        text = text.replace(old, new, 1)

    print("=" * 78)
    print("PROPOSED H1 WINDOW FIX - %s" % a.file)
    print("=" * 78)
    for i, (name, why, _, _) in enumerate(EDITS, 1):
        print("  %d. %s" % (i, name))
        for line in why.split(". "):
            if line.strip():
                print("     %s" % (line.strip().rstrip(".") + "."))
    print("-" * 78)
    diff = difflib.unified_diff(original.splitlines(), text.splitlines(),
                                fromfile=a.file + " (current)",
                                tofile=a.file + " (proposed)", lineterm="", n=3)
    for line in diff:
        print(line)
    print("-" * 78)

    if a.era:
        print("  ERA-BUMP CHECKLIST - this script does NOT do any of it:")
        print("    1. Decide the new era string and where the split is recorded.")
        print("    2. Pre-register the split BEFORE the first run under it.")
        print("    3. State which arms/endpoints are poolable across the line")
        print("       and which are not (DP-3C-o's answer was: none).")
        print("    4. Record that H1 trailing moves before and after are")
        print("       DIFFERENT MEASUREMENTS, so any lag series that spans the")
        print("       line is measuring two things.")
        print("    5. Note it in the next closing review's Standing section.")
        print("-" * 78)

    if not a.apply:
        print("  DRY RUN - nothing written.")
        print()
        print("  This change moves operative confidence, and therefore signals and")
        print("  every endpoint downstream. On the 2026-08-26 cohort it moved 3 of")
        print("  24 rows (DOW 36->42, PWR 49->45, WMT 42->38) and flipped the WS2")
        print("  tracer's episode state. Do not apply it to get a tidy audit.")
        print("  Rule on it first: H1_Window_OffByOne_Defect_2026-08-26.md")
        print("=" * 78)
        return 0

    bak = a.file + ".bak"
    shutil.copy2(a.file, bak)
    with open(a.file, "w", encoding="utf-8", newline="") as fh:
        fh.write(_restore(text, ending))
    print("  APPLIED. Backup written to %s" % bak)
    print("  Now: re-run trail_basis_audit.py (it should report COMPLETED_ONLY),")
    print("  and record the era decision. The audit going clean is NOT the same")
    print("  as the amendment being governed.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
