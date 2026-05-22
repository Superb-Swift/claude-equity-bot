# =============================================================================
# analyze_log.py
# =============================================================================
# PURPOSE:
#   Reads the most recent bot signal log and produces a clean summary
#   of what happened on that run — signal distribution, confidence stats,
#   data quality breakdown, tiered signal sections (actionable / near-miss /
#   weak directional), low-confidence HOLD callouts, and token usage.
#
# USAGE:
#   python analyze_log.py              # analyze today's log
#   python analyze_log.py 2026-05-17   # analyze a specific date
# =============================================================================

import os
import re
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter

LOG_DIR = "logs"
SUMMARY_FILE = os.path.join(LOG_DIR, "summary_history.txt")

# =============================================================================
# CONFIGURATION
# =============================================================================
# ANALYST NOTE: Thresholds should mirror what's in risk_engine.py. If you
# change them in the engine, change them here too — otherwise the digest
# will misclassify signals.

MIN_CONFIDENCE_BUY  = 70   # Risk engine BUY threshold
MIN_CONFIDENCE_SELL = 65   # Risk engine SELL threshold

# How close to threshold = "near-miss"
# A 62% BUY (8 pts below 70) lands in near-miss; a 55% BUY does not
NEAR_MISS_BAND = 10

# HOLD < this confidence = flagged as "worth manual review"
LOW_CONFIDENCE_HOLD_THRESHOLD = 50


# ANALYST NOTE: US market holidays for 2026 (closed). Used to compute
# +5d / +10d / +20d tracker dates in trading-day arithmetic. Update
# annually. Source: NYSE 2026 holiday calendar.
US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}


# =============================================================================
# TRADING-DAY HELPERS
# =============================================================================

def is_trading_day(d: datetime) -> bool:
    """Return True if d is a weekday and not a US market holiday."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d.strftime("%Y-%m-%d") not in US_MARKET_HOLIDAYS_2026


def add_trading_days(start: datetime, n: int) -> datetime:
    """
    Add n TRADING days (skipping weekends and US market holidays) to start.

    ANALYST NOTE:
        Trading-day math is critical — "5 days later" in calendar terms
        means something different than in trading-floor terms. A Friday
        signal's +5d lands on the following Friday, not on Wednesday.
        Memorial Day weekend shifts everything by an extra day.
    """
    current = start
    days_added = 0
    while days_added < n:
        current += timedelta(days=1)
        if is_trading_day(current):
            days_added += 1
    return current


def format_tracker_dates(signal_date: datetime) -> str:
    """Return a short string of +5d / +10d / +20d trading-day targets."""
    d5  = add_trading_days(signal_date, 5)
    d10 = add_trading_days(signal_date, 10)
    d20 = add_trading_days(signal_date, 20)
    return (f"+5d: {d5.strftime('%Y-%m-%d')}  "
            f"+10d: {d10.strftime('%Y-%m-%d')}  "
            f"+20d: {d20.strftime('%Y-%m-%d')}")


# =============================================================================
# LOG PARSING
# =============================================================================

def find_log_file(date_str: str = None) -> str:
    """Locate the log file for the given date, or today's if not specified."""
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
        Each line contains both the Signal JSON dump (with data_quality,
        token counts, full reasoning, lastPrice) AND the summary line
        ([PHASE 2 DRY RUN] ... | Signal: ... | Confidence: ... | Risk: ...).

        We parse both pieces from the same line so we can correlate
        confidence/signal type with data quality, price, and Claude's
        actual reasoning text for richer reporting.
    """
    summary_pattern = re.compile(
        r"PHASE \d DRY RUN\] \[(?P<account>[^\]]+)\] "
        r"\[(?P<held>HELD|SCOUT)\] (?P<ticker>\S+) \| "
        r"Signal: (?P<signal>\w+) \| "
        r"Confidence: (?P<confidence>\d+)% \| "
        r"Risk: (?P<risk>\w+) \| "
        r"Reason: (?P<reason>.+)"
    )

    quality_pattern   = re.compile(r'"data_quality":\s*"(HIGH|MEDIUM|LOW)"')
    reasoning_pattern = re.compile(r'"reasoning":\s*"([^"]+)"')
    price_pattern     = re.compile(r'"lastPrice":\s*([\d.]+)')

    signals = []

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s_match = summary_pattern.search(line)
            if not s_match:
                continue

            d = s_match.groupdict()
            d["confidence"] = int(d["confidence"])

            q_match = quality_pattern.search(line)
            d["data_quality"] = q_match.group(1) if q_match else "MEDIUM"

            # Reasoning snippet for the digest — first sentence, capped
            r_match = reasoning_pattern.search(line)
            if r_match:
                full_reasoning = r_match.group(1)
                first_sentence = full_reasoning.split('. ')[0]
                d["reasoning_snippet"] = (
                    first_sentence[:90] + "..."
                    if len(first_sentence) > 90
                    else first_sentence
                )
            else:
                d["reasoning_snippet"] = ""

            # Price at signal — used for near-miss tracking row
            p_match = price_pattern.search(line)
            d["price"] = float(p_match.group(1)) if p_match else None

            signals.append(d)

    return signals


def parse_token_usage(log_path: str) -> dict:
    """Sum the input and output tokens used by Claude across the run."""
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

    # ANALYST NOTE: Sonnet 4.6 pricing — verify if Anthropic updates
    cost = (in_tokens * 0.000003) + (out_tokens * 0.000015)

    return {
        "input_tokens" : in_tokens,
        "output_tokens": out_tokens,
        "est_cost_usd" : cost,
    }


# =============================================================================
# SIGNAL CLASSIFICATION
# =============================================================================

def classify_directional_signal(s: dict) -> str:
    """
    Bucket a BUY/SELL signal into one of three tiers based on confidence
    relative to the risk-engine threshold.

    Returns 'actionable', 'near_miss', 'weak', or None (for HOLDs).

    ANALYST NOTE:
        The near-miss band is the most important data during Phase 2.
        These are signals Claude was CLOSE to recommending — they're
        your calibration evidence. Was rejecting them correct? The
        outcome data over +5/+10/+20 days tells the story.
    """
    signal = s["signal"]
    conf   = s["confidence"]

    if signal == "BUY":
        threshold = MIN_CONFIDENCE_BUY
    elif signal == "SELL":
        threshold = MIN_CONFIDENCE_SELL
    else:
        return None  # HOLD doesn't go through this classification

    if conf >= threshold:
        return "actionable"
    if conf >= (threshold - NEAR_MISS_BAND):
        return "near_miss"
    return "weak"


# =============================================================================
# SUMMARY GENERATION
# =============================================================================

def build_summary(signals: list, tokens: dict, log_path: str) -> str:
    """Build a clean, scannable summary from the parsed signals."""
    lines = []

    # --- Header ---
    date_str = os.path.basename(log_path).replace("signals_", "").replace(".log", "")
    try:
        signal_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        signal_date = datetime.now()

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

    # --- Data Quality Distribution ---
    quality_counts = Counter(s["data_quality"] for s in signals)
    lines.append("  DATA QUALITY DISTRIBUTION")
    lines.append("  " + "-"*40)
    for quality in ["HIGH", "MEDIUM", "LOW"]:
        count = quality_counts.get(quality, 0)
        pct = (count / total) * 100 if total > 0 else 0
        bar = "█" * count
        lines.append(f"  {quality:<7} ({count:>3}) {pct:>5.1f}%  {bar}")
    lines.append("")

    # --- LOW Quality Investigations ---
    low_signals = [s for s in signals if s["data_quality"] == "LOW"]
    if low_signals:
        low_tickers = defaultdict(list)
        for s in low_signals:
            low_tickers[s["ticker"]].append(s["account"])

        lines.append("  LOW QUALITY SIGNALS (Worth Investigating)")
        lines.append("  " + "-"*40)
        for ticker, accounts in sorted(low_tickers.items()):
            unique_accounts = sorted(set(accounts))
            lines.append(f"  {ticker:<6} flagged in: {', '.join(unique_accounts)}")
        lines.append("")
        lines.append("  → Common LOW causes: thin news coverage, anomalous data,")
        lines.append("    earnings event risk, ETF data quirks. Worth tracking")
        lines.append("    whether these tickers persistently show LOW over time.")
        lines.append("")

    # =========================================================================
    # TIERED SIGNAL SECTIONS
    # =========================================================================
    # ANALYST NOTE:
    #   Classify every BUY/SELL into actionable / near-miss / weak tiers.
    #   These three sections REPLACE the old "Top 5 Highest Confidence"
    #   block — they're more meaningful because they tell you what to DO
    #   with each signal rather than just ranking by confidence.

    actionable = []
    near_miss  = []
    weak_dir   = []
    for s in signals:
        tier = classify_directional_signal(s)
        if tier == "actionable":
            actionable.append(s)
        elif tier == "near_miss":
            near_miss.append(s)
        elif tier == "weak":
            weak_dir.append(s)

    # --- TIER 1: ACTIONABLE SIGNALS ---
    lines.append("  ✅ ACTIONABLE SIGNALS (Risk Engine Approved)")
    lines.append("  " + "-"*40)
    if actionable:
        for s in sorted(actionable, key=lambda x: -x["confidence"]):
            lines.append(f"  {s['confidence']:>3}%  {s['signal']:<5} "
                         f"{s['ticker']:<6}  [{s['account']}] [{s['held']}] "
                         f"({s['data_quality']})")
            if s.get("reasoning_snippet"):
                lines.append(f"        → {s['reasoning_snippet']}")
    else:
        lines.append(f"  None today.")
        lines.append(f"  (No BUY ≥{MIN_CONFIDENCE_BUY}% or "
                     f"SELL ≥{MIN_CONFIDENCE_SELL}% generated.)")
    lines.append("")

    # --- TIER 2: NEAR-MISS SIGNALS ---
    # These are your most important Phase 2 calibration data
    lines.append("  🎯 NEAR-MISS SIGNALS (Rejected by Confidence Threshold)")
    lines.append("  " + "-"*40)
    if near_miss:
        for s in sorted(near_miss, key=lambda x: -x["confidence"]):
            threshold = (MIN_CONFIDENCE_BUY if s["signal"] == "BUY"
                         else MIN_CONFIDENCE_SELL)
            gap = threshold - s["confidence"]

            price_str = f"${s['price']:.2f}" if s["price"] is not None else "n/a"

            lines.append(f"  {s['confidence']:>3}%  {s['signal']:<5} "
                         f"{s['ticker']:<6}  [{s['account']}] [{s['held']}] "
                         f"({s['data_quality']})")
            lines.append(f"        Needs {threshold}%, missed by {gap} pt(s) "
                         f"| Price at signal: {price_str}")
            lines.append(f"        Track: {format_tracker_dates(signal_date)}")
            if s.get("reasoning_snippet"):
                lines.append(f"        → {s['reasoning_snippet']}")
            lines.append("")

        lines.append("  → These are Claude's near-conviction calls. Most important")
        lines.append(f"    Phase 2 data. Track outcomes carefully in spreadsheet.")
    else:
        lines.append(f"  None today.")
        lines.append(f"  (No BUY in {MIN_CONFIDENCE_BUY - NEAR_MISS_BAND}–"
                     f"{MIN_CONFIDENCE_BUY - 1}% or SELL in "
                     f"{MIN_CONFIDENCE_SELL - NEAR_MISS_BAND}–"
                     f"{MIN_CONFIDENCE_SELL - 1}%.)")
    lines.append("")

    # --- TIER 3: WEAK DIRECTIONAL SIGNALS ---
    # Below the near-miss band — Claude leans but doesn't lean hard
    lines.append("  📊 WEAK DIRECTIONAL SIGNALS (Far From Threshold)")
    lines.append("  " + "-"*40)
    if weak_dir:
        for s in sorted(weak_dir, key=lambda x: -x["confidence"]):
            lines.append(f"  {s['confidence']:>3}%  {s['signal']:<5} "
                         f"{s['ticker']:<6}  [{s['account']}] [{s['held']}] "
                         f"({s['data_quality']})")
    else:
        lines.append("  None today.")
    lines.append("")

    # --- LOW-CONFIDENCE HOLD SIGNALS ---
    # ANALYST NOTE: This section surfaces HOLDs where Claude has real
    # reservations. A HOLD at 42% confidence means "I'm telling you not
    # to act because nothing else clearly wins — but I'm not comfortable."
    # These are the signals where YOUR judgment matters most.
    low_conf_holds = [
        s for s in signals
        if s["signal"] == "HOLD" and s["confidence"] < LOW_CONFIDENCE_HOLD_THRESHOLD
    ]
    if low_conf_holds:
        low_conf_holds.sort(key=lambda x: x["confidence"])

        lines.append(f"  ⚠️  LOW-CONFIDENCE HOLDS (<{LOW_CONFIDENCE_HOLD_THRESHOLD}%) — Worth Manual Review")
        lines.append("  " + "-"*40)
        for s in low_conf_holds:
            lines.append(f"  {s['confidence']:>3}%  {s['ticker']:<6}  "
                         f"[{s['account']}] [{s['held']}] ({s['data_quality']})")
            if s.get("reasoning_snippet"):
                lines.append(f"        → {s['reasoning_snippet']}")
        lines.append("")
        lines.append("  → These HOLDs reflect Claude's uncertainty, NOT confidence in")
        lines.append("    the position. Claude couldn't recommend BUY or SELL with")
        lines.append("    conviction, so defaulted to HOLD. Apply your own judgment.")
        lines.append("")

    # --- Account Breakdown ---
    by_account = defaultdict(list)
    for s in signals:
        by_account[s["account"]].append(s)

    lines.append("  BY ACCOUNT")
    lines.append("  " + "-"*40)
    for account, sigs in by_account.items():
        held  = sum(1 for s in sigs if s["held"] == "HELD")
        scout = sum(1 for s in sigs if s["held"] == "SCOUT")
        lines.append(f"  {account:<20} {len(sigs):>3} signals "
                     f"({held} held, {scout} scouting)")
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
    """Append the daily summary to the running history file."""
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
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    log_path = find_log_file(date_arg)

    print(f"Analyzing log: {log_path}\n")

    signals = parse_log(log_path)
    tokens  = parse_token_usage(log_path)
    summary = build_summary(signals, tokens, log_path)

    print(summary)
    append_to_history(summary)

    print(f"\n📁 Summary appended to: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
