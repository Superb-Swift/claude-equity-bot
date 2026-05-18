# =============================================================================
# analyze_log.py
# =============================================================================
# PURPOSE:
#   Reads the most recent bot signal log and produces a clean summary
#   of what happened on that run — signal distribution, confidence stats,
#   notable BUY/SELL alerts, risk engine outcomes, and token usage.
#
# ANALYST NOTE:
#   Run this after main.py to get a one-page digest of the day's signals
#   without scrolling through hundreds of log lines. The output is also
#   appended to a running summary file so you can review trends across
#   days/weeks without opening every log file.
#
# USAGE:
#   python analyze_log.py              # analyze today's log
#   python analyze_log.py 2026-05-17   # analyze a specific date
# =============================================================================

import os
import re
import sys
import json
from datetime import datetime
from collections import defaultdict, Counter

LOG_DIR = "logs"
SUMMARY_FILE = os.path.join(LOG_DIR, "summary_history.txt")


# =============================================================================
# LOG PARSING
# =============================================================================

def find_log_file(date_str: str = None) -> str:
    """
    Locate the log file for the given date, or today's if not specified.

    ANALYST NOTE:
        Logs are named like signals_2026-05-18.log — we just inject
        the date into that filename pattern.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    path = os.path.join(LOG_DIR, f"signals_{date_str}.log")

    if not os.path.exists(path):
        print(f"❌ No log file found for {date_str} at: {path}")
        sys.exit(1)

    return path


def parse_log(log_path: str) -> list:
    """
    Read the log file and extract every signal as a structured dict.

    ANALYST NOTE:
        Signal lines look like:
        2026-05-18 14:57:50 | INFO | [PHASE 2 DRY RUN] [Roth IRA] [HELD] WMT |
        Signal: HOLD | Confidence: 62% | Risk: APPROVED | Reason: ...

        We use a regex to extract account, ticker, signal, confidence, etc.
        This is more reliable than trying to parse the raw JSON dumped
        elsewhere in the log because the one-liner format is stable.
    """
    # ANALYST NOTE: Regex breakdown for the curious:
    #   \[(?P<account>[^\]]+)\] — account label in brackets
    #   \[(?P<held>HELD|SCOUT)\] — held/scout marker
    #   (?P<ticker>\w+) — ticker symbol
    #   Signal: (?P<signal>\w+) — BUY/SELL/HOLD
    #   Confidence: (?P<confidence>\d+)% — numeric confidence
    #   Risk: (?P<risk>APPROVED|REJECTED) — risk decision
    pattern = re.compile(
        r"PHASE \d DRY RUN\] \[(?P<account>[^\]]+)\] "
        r"\[(?P<held>HELD|SCOUT)\] (?P<ticker>\S+) \| "
        r"Signal: (?P<signal>\w+) \| "
        r"Confidence: (?P<confidence>\d+)% \| "
        r"Risk: (?P<risk>\w+) \| "
        r"Reason: (?P<reason>.+)"
    )

    signals = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                d = match.groupdict()
                d["confidence"] = int(d["confidence"])
                signals.append(d)

    return signals


def parse_token_usage(log_path: str) -> dict:
    """
    Sum the input and output tokens used by Claude across the run.

    ANALYST NOTE:
        Token counts come from the raw signal JSON dumped by main.py.
        We grep for the input_tokens / output_tokens fields and sum them.
    """
    in_tokens = 0
    out_tokens = 0

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m_in  = re.search(r'"input_tokens":\s*(\d+)', line)
            m_out = re.search(r'"output_tokens":\s*(\d+)', line)
            if m_in:
                in_tokens += int(m_in.group(1))
            if m_out:
                out_tokens += int(m_out.group(1))

    # ANALYST NOTE: Sonnet 4.6 pricing as of 2026 (verify if Anthropic updates):
    #   Input:  $3 per million tokens  → $0.000003 per token
    #   Output: $15 per million tokens → $0.000015 per token
    cost = (in_tokens * 0.000003) + (out_tokens * 0.000015)

    return {
        "input_tokens" : in_tokens,
        "output_tokens": out_tokens,
        "est_cost_usd" : cost,
    }


# =============================================================================
# SUMMARY GENERATION
# =============================================================================

def build_summary(signals: list, tokens: dict, log_path: str) -> str:
    """
    Build a clean, scannable summary string from the parsed signals.

    ANALYST NOTE:
        The summary is designed to answer the questions you'll actually
        ask each day: How many BUY/SELL/HOLD? Any high-confidence calls?
        Did anything get rejected? What did this cost me?
    """
    lines = []

    # --- Header ---
    date_str = os.path.basename(log_path).replace("signals_", "").replace(".log", "")
    lines.append("="*72)
    lines.append(f"  DAILY SIGNAL SUMMARY — {date_str}")
    lines.append("="*72)
    lines.append(f"  Total signals analyzed: {len(signals)}")
    lines.append("")

    if not signals:
        lines.append("  No signals found in this log file.")
        lines.append("="*72)
        return "\n".join(lines)

    # --- Signal Distribution ---
    signal_counts = Counter(s["signal"] for s in signals)
    lines.append("  SIGNAL DISTRIBUTION")
    lines.append("  " + "-"*40)
    total = len(signals)
    for signal in ["BUY", "SELL", "HOLD"]:
        count = signal_counts.get(signal, 0)
        pct = (count / total) * 100 if total > 0 else 0
        lines.append(f"  {signal:<6} : {count:>3}  ({pct:>5.1f}%)")
    lines.append("")

    # --- Confidence Stats ---
    confidences = [s["confidence"] for s in signals]
    avg_conf = sum(confidences) / len(confidences)
    high_conf = sum(1 for c in confidences if c >= 70)
    low_conf  = sum(1 for c in confidences if c < 40)

    lines.append("  CONFIDENCE STATS")
    lines.append("  " + "-"*40)
    lines.append(f"  Average confidence : {avg_conf:.1f}%")
    lines.append(f"  Highest            : {max(confidences)}%")
    lines.append(f"  Lowest             : {min(confidences)}%")
    lines.append(f"  >= 70% (actionable): {high_conf}")
    lines.append(f"  <  40% (very weak) : {low_conf}")
    lines.append("")

    # --- Confidence Distribution by Band ---
    bands = defaultdict(int)
    for c in confidences:
        if c < 40:
            bands["0-39"] += 1
        elif c < 60:
            bands["40-59"] += 1
        elif c < 70:
            bands["60-69"] += 1
        elif c < 80:
            bands["70-79"] += 1
        else:
            bands["80-100"] += 1

    lines.append("  CONFIDENCE BANDS")
    lines.append("  " + "-"*40)
    for band in ["0-39", "40-59", "60-69", "70-79", "80-100"]:
        count = bands.get(band, 0)
        bar = "█" * count
        lines.append(f"  {band:<7} ({count:>2}) {bar}")
    lines.append("")

    # --- Account Breakdown ---
    by_account = defaultdict(list)
    for s in signals:
        by_account[s["account"]].append(s)

    lines.append("  BY ACCOUNT")
    lines.append("  " + "-"*40)
    for account, sigs in by_account.items():
        held = sum(1 for s in sigs if s["held"] == "HELD")
        scout = sum(1 for s in sigs if s["held"] == "SCOUT")
        lines.append(f"  {account:<20} {len(sigs):>3} signals "
                     f"({held} held, {scout} scouting)")
    lines.append("")

    # --- Notable Signals ---
    # Highest confidence non-HOLD signals are worth flagging.
    actionable = [s for s in signals
                  if s["signal"] in ("BUY", "SELL") and s["confidence"] >= 70]
    if actionable:
        lines.append("  ⚠️  ACTIONABLE SIGNALS (Non-HOLD, Confidence >= 70%)")
        lines.append("  " + "-"*40)
        for s in sorted(actionable, key=lambda x: -x["confidence"]):
            lines.append(f"  {s['signal']:<5} {s['ticker']:<6} "
                         f"({s['confidence']}%) in {s['account']} [{s['held']}]")
            lines.append(f"        Risk: {s['risk']} — {s['reason'][:60]}")
        lines.append("")

    # --- Top Confidence Signals (top 5 regardless of action) ---
    top5 = sorted(signals, key=lambda x: -x["confidence"])[:5]
    lines.append("  TOP 5 HIGHEST CONFIDENCE SIGNALS")
    lines.append("  " + "-"*40)
    for s in top5:
        lines.append(f"  {s['confidence']:>3}%  {s['signal']:<5} "
                     f"{s['ticker']:<6}  [{s['account']}] [{s['held']}]")
    lines.append("")

    # --- Risk Engine Outcomes ---
    risk_counts = Counter(s["risk"] for s in signals)
    lines.append("  RISK ENGINE OUTCOMES")
    lines.append("  " + "-"*40)
    for risk, count in risk_counts.most_common():
        lines.append(f"  {risk:<15} : {count}")
    lines.append("")

    # --- Token Usage & Cost ---
    lines.append("  CLAUDE API USAGE")
    lines.append("  " + "-"*40)
    lines.append(f"  Input tokens   : {tokens['input_tokens']:>8,}")
    lines.append(f"  Output tokens  : {tokens['output_tokens']:>8,}")
    lines.append(f"  Estimated cost : ${tokens['est_cost_usd']:.4f}")
    lines.append("")

    lines.append("="*72)
    return "\n".join(lines)


def append_to_history(summary: str) -> None:
    """
    Append the daily summary to the running history file.

    ANALYST NOTE:
        Over time this file accumulates a chronological record of every
        bot run. Open it with Notepad++ to scroll back through trends —
        great for spotting whether confidence is rising over time or
        whether the BUY/SELL ratio is shifting.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n[Run analyzed at: {timestamp}]\n")
        f.write(summary)
        f.write("\n")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    # Accept optional date arg
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    log_path = find_log_file(date_arg)

    print(f"Analyzing log: {log_path}\n")

    signals = parse_log(log_path)
    tokens  = parse_token_usage(log_path)
    summary = build_summary(signals, tokens, log_path)

    # Print to terminal
    print(summary)

    # Append to history file
    append_to_history(summary)

    print(f"\n📁 Summary appended to: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
