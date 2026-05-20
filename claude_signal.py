# =============================================================================
# claude_signal.py
# =============================================================================
# PURPOSE:
#   Uses the Anthropic Claude API to analyze market data and generate
#   structured trading signals for individual equity tickers.
#
#   Position-aware, asset-type-aware, AND multi-account-aware:
#   when a ticker is held across multiple accounts, Claude sees the
#   consolidated view AND a per-account breakdown.
#
# DEPENDENCIES:
#   pip install anthropic python-dotenv
# =============================================================================

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """
You are a disciplined equity research analyst. Your job is to analyze 
market data and news for a given stock ticker and produce a concise, 
structured trading signal.

You will receive:
- Ticker symbol and company name
- Asset type (equity or ETF)
- Current price, intraday change, OHLC, bid/ask, volume
- 52-week range
- For equities: P/E, EPS, dividend yield
- For ETFs: dividend yield only (P/E and EPS are intentionally omitted
  because they are unreliable for fund products)
- Recent news headlines (if available)
- Position context (if the user holds this ticker)
  IMPORTANT: when the user holds the same ticker in multiple accounts,
  you will see a CONSOLIDATED position summary AND a per-account
  breakdown. Account taxonomy matters — Roth IRA gains are tax-free,
  Individual account gains are taxable. Factor this into SELL signals
  if relevant.

For ETFs: do NOT request, infer, or speculate about underlying P/E.
Do not flag missing P/E as a risk for ETFs — it is intentionally omitted.

You must respond with ONLY a valid JSON object — no preamble, no markdown,
no code fences. Just raw JSON.

Schema:
{
  "ticker": "string",
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": integer between 0 and 100,
  "time_horizon": "SHORT" | "MEDIUM" | "LONG",
  "reasoning": "2-3 sentences max explaining the signal",
  "bull_case": "1 sentence on what could drive upside",
  "bear_case": "1 sentence on the key risk",
  "risk_flags": ["list", "of", "concerns"],
  "data_quality": "HIGH" | "MEDIUM" | "LOW",
  "position_note": "1 sentence on holding context, or empty if scouting"
}

Signal definitions:
- BUY: Meaningful positive catalyst, asymmetric upside, favorable risk/reward
- SELL: Deteriorating fundamentals, negative catalyst, justified profit-taking
- HOLD: No clear edge in either direction

Confidence:
- 80-100: Strong conviction, multiple confirming signals
- 60-79:  Moderate conviction
- 40-59:  Low conviction, mixed data
- 0-39:   Very low conviction

IMPORTANT: Research for human review only. Be honest about uncertainty.
"""


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def _build_market_data_section(quote: dict) -> list:
    """Build the market data lines that apply to both equities and ETFs."""
    return [
        f"Ticker: {quote.get('ticker', '?')} ({quote.get('companyName', 'Unknown')})",
        f"Asset Type: {'ETF / Fund' if quote.get('is_etf') else 'Equity'}",
        f"Exchange: {quote.get('exchange', 'N/A')}",
        f"Current Price: ${quote.get('lastPrice', 'N/A')}",
        f"Day Change: ${quote.get('netChange', 0):.2f} ({quote.get('netPercentChange', 0):.2f}%)",
        f"Open: ${quote.get('openPrice', 'N/A')} | High: ${quote.get('highPrice', 'N/A')} | Low: ${quote.get('lowPrice', 'N/A')} | Prev Close: ${quote.get('closePrice', 'N/A')}",
        f"Bid / Ask: ${quote.get('bidPrice', 'N/A')} / ${quote.get('askPrice', 'N/A')}",
        f"Volume: {quote.get('totalVolume', 0):,} (10-day avg: {int(quote.get('avg10DayVolume', 0)):,})",
        f"52-Week Range: ${quote.get('fiftyTwoWeekLow', 'N/A')} - ${quote.get('fiftyTwoWeekHigh', 'N/A')}",
    ]


def _build_fundamentals_section(quote: dict) -> list:
    """Build the fundamentals section — different for ETFs vs equities."""
    if quote.get("is_etf"):
        return [
            f"Dividend Yield: {quote.get('divYield', 0):.2f}%",
            "(P/E and EPS are not displayed for ETFs.)",
        ]
    else:
        pe  = quote.get("peRatio")
        eps = quote.get("eps")
        div = quote.get("divYield", 0)
        return [
            f"P/E Ratio: {pe if pe is not None else 'N/A'} | "
            f"EPS: ${eps if eps is not None else 'N/A'} | "
            f"Div Yield: {div:.2f}%",
        ]


def _build_position_section(position: dict) -> list:
    """
    Build the position context section.

    ANALYST NOTE:
        Handles three cases:
        1. Not held (scouting) — minimal section
        2. Held in one account — standard display
        3. Held across multiple accounts — consolidated view + per-account breakdown
    """
    if not position or not position.get("is_held"):
        return ["\n--- POSITION CONTEXT (Scouting — not currently held) ---"]

    accounts = position.get("held_in_accounts", [])
    multi_account = len(accounts) > 1

    if multi_account:
        lines = [
            "\n--- POSITION CONTEXT (Held across multiple accounts) ---",
            f"Total Shares Held    : {position.get('quantity', 0):.0f}",
            f"Weighted Avg Cost    : ${position.get('average_price', 0):,.2f}",
            f"Combined Market Value: ${position.get('market_value', 0):,.2f}",
            f"Combined Day P&L     : ${position.get('current_day_pnl', 0):,.2f}",
            f"Total Open P&L       : ${position.get('long_open_pnl', 0):,.2f}",
            f"Held in Accounts     : {', '.join(accounts)}",
            "",
            "Per-Account Breakdown:",
        ]
        # ANALYST NOTE: Per-account detail lets Claude reason about
        # tax-aware decisions — selling from Roth has no tax impact,
        # selling from Individual triggers capital gains.
        for account in position.get("account_breakdown", []):
            lines.append(
                f"  • {account.get('account_label', '?'):<15} "
                f"{account.get('quantity', 0):.0f} shares @ "
                f"${account.get('average_price', 0):,.2f} avg = "
                f"${account.get('market_value', 0):,.2f} market value "
                f"(P&L: ${account.get('long_open_pnl', 0):,.2f})"
            )
        return lines
    else:
        # Single-account holding — standard display
        return [
            "\n--- POSITION CONTEXT (You currently hold this) ---",
            f"Account        : {accounts[0] if accounts else '?'}",
            f"Shares Held    : {position.get('quantity', 0):.0f}",
            f"Avg Cost Basis : ${position.get('average_price', 0):,.2f}",
            f"Market Value   : ${position.get('market_value', 0):,.2f}",
            f"Day P&L        : ${position.get('current_day_pnl', 0):,.2f}",
            f"Total Open P&L : ${position.get('long_open_pnl', 0):,.2f}",
        ]


# =============================================================================
# SIGNAL GENERATION
# =============================================================================

def get_signal(ticker: str, quote: dict, position: dict = None,
               headlines: list = None, metrics: dict = None) -> dict:
    """
    Generate a structured trading signal for a ticker using Claude.

    Args:
        ticker     (str):  Stock symbol
        quote      (dict): Quote data from schwab_client.get_quote()
        position   (dict): Optional consolidated position context
        headlines  (list): Optional list of recent headlines
        metrics    (dict): Optional financial metrics

    Returns:
        dict: Structured signal, or error dict
    """
    prompt_parts = []
    prompt_parts.extend(_build_market_data_section(quote))
    prompt_parts.extend(_build_fundamentals_section(quote))
    prompt_parts.extend(_build_position_section(position))

    if headlines:
        prompt_parts.append("\nRecent News Headlines:")
        for i, headline in enumerate(headlines[:5], 1):
            prompt_parts.append(f"  {i}. {headline}")
    else:
        prompt_parts.append("\nRecent News Headlines: None provided")

    if metrics:
        prompt_parts.append("\nKey Financial Metrics:")
        for key, value in metrics.items():
            prompt_parts.append(f"  {key}: {value}")

    prompt_parts.append("\nBased on this data, generate your structured JSON signal.")

    user_prompt = "\n".join(prompt_parts)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = response.content[0].text.strip()
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        signal = json.loads(clean_text)

        signal["model"]         = MODEL
        signal["input_tokens"]  = response.usage.input_tokens
        signal["output_tokens"] = response.usage.output_tokens

        return signal

    except json.JSONDecodeError as e:
        print(f"[claude_signal] Failed to parse Claude's response as JSON: {e}")
        return {
            "ticker"     : ticker,
            "signal"     : "HOLD",
            "confidence" : 0,
            "reasoning"  : "Signal generation failed — JSON parse error.",
            "risk_flags" : ["parse_error"],
            "error"      : str(e)
        }

    except Exception as e:
        print(f"[claude_signal] Unexpected error: {e}")
        return {
            "ticker"     : ticker,
            "signal"     : "HOLD",
            "confidence" : 0,
            "reasoning"  : "Signal generation failed — unexpected error.",
            "risk_flags" : ["unknown_error"],
            "error"      : str(e)
        }


# =============================================================================
# SIGNAL DISPLAY
# =============================================================================

def print_signal(signal: dict) -> None:
    """Pretty-print a signal dict to the terminal for human review."""
    COLORS = {
        "BUY"  : "\033[92m",
        "SELL" : "\033[91m",
        "HOLD" : "\033[93m",
        "RESET": "\033[0m"
    }

    sig   = signal.get("signal", "HOLD")
    conf  = signal.get("confidence", 0)
    color = COLORS.get(sig, COLORS["RESET"])

    print("\n" + "="*60)
    print(f"  SIGNAL: {color}{sig}{COLORS['RESET']}  |  "
          f"Ticker: {signal.get('ticker')}  |  "
          f"Confidence: {conf}%")
    print("="*60)
    print(f"  Reasoning   : {signal.get('reasoning')}")
    print(f"  Bull Case   : {signal.get('bull_case')}")
    print(f"  Bear Case   : {signal.get('bear_case')}")
    print(f"  Time Frame  : {signal.get('time_horizon')}")
    print(f"  Data Quality: {signal.get('data_quality')}")

    position_note = signal.get("position_note", "")
    if position_note:
        print(f"  Position    : {position_note}")

    flags = signal.get("risk_flags", [])
    if flags:
        print(f"  Risk Flags  : {', '.join(flags)}")

    print(f"  Tokens Used : {signal.get('input_tokens', '?')} in / "
          f"{signal.get('output_tokens', '?')} out")
    print("="*60 + "\n")
