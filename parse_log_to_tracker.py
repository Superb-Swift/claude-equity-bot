# =============================================================================
# parse_log_to_tracker.py
# =============================================================================
# PURPOSE:
#   Read one or more bot signal log files and emit ready-to-paste TSV rows
#   for the Signals tab of claude_equity_bot_tracker.xlsx.
#
#   Solves the recurring problem: bot runs daily, tracker rows lag behind,
#   and manual transcription is tedious + error-prone.
#
# USAGE:
#   # Single day:
#   python parse_log_to_tracker.py logs\signals_2026-05-26.log
#
#   # Multiple days (catches up the backlog):
#   python parse_log_to_tracker.py logs\signals_2026-05-21.log logs\signals_2026-05-22.log logs\signals_2026-05-26.log
#
#   # Glob shortcut (all logs from a date range):
#   python parse_log_to_tracker.py logs\signals_2026-05-2*.log
#
#   # Write to file instead of stdout:
#   python parse_log_to_tracker.py logs\signals_2026-05-26.log -o paste_me.tsv
#
# WORKFLOW (paste into tracker):
#   1. Run this script for the days you need to backfill
#   2. Open the output (stdout or file)
#   3. Open claude_equity_bot_tracker.xlsx → Signals tab
#   4. Find the first blank row below the last filled row
#   5. Paste the TSV content into column A
#   6. Excel auto-populates columns A through G
#   7. Select cells K-N from the row directly ABOVE the pasted block,
#      then drag the fill handle down across all new rows to extend
#      the Return and "Was Claude Right?" formulas
#   8. Save
#
# ANALYST NOTE:
#   This script is intentionally read-only — it never touches the
#   tracker xlsx directly. Direct-write mode would risk corrupting
#   existing data if a parse error occurs mid-run. Outputting TSV
#   keeps a human-in-the-loop checkpoint between log parsing and
#   spreadsheet mutation. The 30 seconds of paste-and-drag is worth
#   the safety.
#
# DEPENDENCIES:
#   Standard library only (re, json, sys, argparse, glob, pathlib).
#   No pandas, no openpyxl. Runs fast and has no install footprint.
# =============================================================================

import argparse
import glob
import json
import re
import sys
from pathlib import Path

# ANALYST NOTE:
#   Two regex patterns handle the two pieces of info we need per signal:
#
#   1. JSON_RE — finds the embedded "Signal JSON: { ... }" object.
#      The non-greedy match plus brace-counting approach (in extract_json)
#      handles nested braces inside reasoning/risk_flags fields safely.
#
#   2. ACCOUNT_RE — captures the "[PHASE 2 DRY RUN]" OR "[PHASE 3-A DRY RUN]"
#      tag block that appears later on the same log line as the JSON.
#      Accounts can be "Roth IRA", "Individual", "Roth IRA,Individual",
#      or "—" (em-dash for scout signals).
JSON_RE    = re.compile(r'Signal JSON:\s*(\{)')
# ANALYST NOTE (2026-07-06, WS2 deploy): phase-agnostic tag match — mirrors
#   the 2026-06-15 analyze_log.py fix. The original alternation hardcoded
#   "2 DRY RUN|3-A...", so the Phase 3-B cutover would have silently imported
#   every row with Account="Unknown" (the same failure class analyze_log hit
#   at the 3-A cutover). [\w.-]+ matches any phase label (2, 3-A, 3-B, ...).
ACCOUNT_RE = re.compile(r'\[PHASE [\w.-]+[^\]]*\]\s+\[([^\]]+)\]\s+\[(HELD|SCOUT)\]')


def extract_json(line, start_idx):
    """
    Walk forward from the opening brace, counting nested braces and
    respecting string boundaries, until we find the matching close brace.

    ANALYST NOTE:
        We can't just use a non-greedy regex like brace-dot-star-brace
        because the signal JSON contains nested objects (risk_flags arrays
        sometimes include strings with braces, and reasoning text can have
        any character). A small hand-rolled brace counter is more reliable
        than regex gymnastics here, and runs in microseconds.
    """
    depth = 0
    in_string = False
    escape = False
    for i in range(start_idx, len(line)):
        ch = line[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return line[start_idx:i + 1]
    return None  # unterminated — should never happen on well-formed logs


def normalize_account(raw):
    """
    Normalize account label to match what the user has been entering
    in the tracker manually:
        "Roth IRA"            → "Roth IRA"
        "Individual"          → "Individual"
        "Roth IRA,Individual" → "Roth IRA,Individual"  (consolidated row)
        "—" or "-"            → "Scout"  (em-dash for scout/not-held)

    ANALYST NOTE:
        The em-dash (—, U+2014) comes from the bot output formatting.
        The existing tracker uses the friendlier label "Scout" for
        non-held tickers. We map it here to keep tracker rows consistent
        with the manual-entry convention.
    """
    raw = raw.strip()
    if raw in ("—", "-", "\u2014"):
        return "Scout"
    return raw


def parse_log_file(filepath):
    """
    Parse a single log file and yield one dict per signal found.

    Expected per-signal fields in the JSON payload:
        ticker, signal, confidence, data_quality, lastPrice

    Account / status are pulled from the log line's bracket tags,
    not the JSON itself (the JSON doesn't include account context).
    """
    path = Path(filepath)
    # Derive date from filename: "signals_2026-05-26.log" → "2026-05-26"
    date_str = path.stem.replace('signals_', '')

    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, start=1):
            m = JSON_RE.search(line)
            if not m:
                continue
            raw = extract_json(line, m.end() - 1)
            if not raw:
                print(f"  [warn] {path.name}:{line_num} — unterminated JSON, skipping",
                      file=sys.stderr)
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"  [warn] {path.name}:{line_num} — JSON decode error: {e}",
                      file=sys.stderr)
                continue

            # H2 A/B: import the CONTROL arm only — skip variant-B (symmetric)
            # rows so the tracker stays one row per ticker/day. Normal (non-A/B)
            # runs are variant "A" and import as usual.
            if str(payload.get("prompt_variant", "A")).upper() == "B":
                continue

            # Pull account/held status from the surrounding log text
            acct_match = ACCOUNT_RE.search(line)
            if acct_match:
                account = normalize_account(acct_match.group(1))
            else:
                # ANALYST NOTE: Older log formats may lack the [PHASE 2 DRY RUN]
                # prefix entirely. Default to "Unknown" so the row still imports;
                # user can correct it manually if it ever happens.
                account = "Unknown"

            rows.append({
                "Date":            date_str,
                "Ticker":          payload.get("ticker", ""),
                "Account":         account,
                "Signal":          payload.get("signal", ""),
                "Conf %":          payload.get("confidence", "") / 100.0
                                       if isinstance(payload.get("confidence"), (int, float))
                                       else "",
                "Data Quality":    payload.get("data_quality", ""),
                "Price at Signal": payload.get("lastPrice", ""),
            })

    return rows


def emit_tsv(rows, out_stream):
    """
    Write TSV (tab-separated) to the output stream.

    ANALYST NOTE:
        TSV pastes cleanly into Excel — each tab becomes a cell boundary,
        each newline becomes a new row. No quoting headaches, no CSV
        delimiter ambiguity when tickers contain commas (e.g., "Roth
        IRA,Individual" would break a CSV but works fine in a TSV cell).
    """
    if not rows:
        print("  [info] No signals parsed — nothing to write.", file=sys.stderr)
        return

    cols = ["Date", "Ticker", "Account", "Signal", "Conf %",
            "Data Quality", "Price at Signal"]

    # Header row (helpful for visual confirmation, NOT pasted into tracker)
    print("# Header (do NOT paste this line):", file=sys.stderr)
    print("\t".join(cols), file=sys.stderr)
    print("# Data rows below (paste these into tracker column A):",
          file=sys.stderr)

    for row in rows:
        out_stream.write(
            "\t".join(str(row[c]) for c in cols) + "\n"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Parse bot signal logs into ready-to-paste tracker rows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "logs",
        nargs="+",
        help="One or more log file paths (globs OK, e.g. logs\\signals_2026-05-*.log)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Write TSV to this file instead of stdout"
    )
    args = parser.parse_args()

    # Expand globs (Windows cmd.exe doesn't expand them, so we do it here)
    files = []
    for pattern in args.logs:
        matched = sorted(glob.glob(pattern))
        if matched:
            files.extend(matched)
        else:
            # Maybe the user typed an exact path
            if Path(pattern).exists():
                files.append(pattern)
            else:
                print(f"  [warn] No match for: {pattern}", file=sys.stderr)

    if not files:
        print("ERROR: No log files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing {len(files)} log file(s)...", file=sys.stderr)

    all_rows = []
    for fp in files:
        rows = parse_log_file(fp)
        print(f"  {Path(fp).name}: {len(rows)} signal(s) parsed", file=sys.stderr)
        all_rows.extend(rows)

    print(f"Total: {len(all_rows)} rows ready to paste\n", file=sys.stderr)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            emit_tsv(all_rows, f)
        print(f"  ✅ Wrote {len(all_rows)} rows to: {args.output}",
              file=sys.stderr)
    else:
        emit_tsv(all_rows, sys.stdout)


if __name__ == "__main__":
    main()