# =============================================================================
# claude_signal.py
# =============================================================================
# PURPOSE:
#   Uses the Anthropic Claude API to analyze market data and generate
#   structured trading signals for individual equity tickers.
#
#   Position-aware: when analyzing a ticker you already hold, Claude receives
#   your cost basis and unrealized P&L as additional context. This lets it
#   evaluate SELL signals informed by your actual exposure, not just price.
#
# DEPENDENCIES:
#   pip install anthropic python-dotenv
#
# USAGE:
#   from claude_signal import get_signal, print_signal
# =============================================================================

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize the Anthropic client
client = Anthropic()

# Model selection
MODEL = "claude-sonnet-4-6"

# System prompt — defines Claude's role and output format
SYSTEM_PROMPT = """
You are a disciplined equity research analyst. Your job is to analyze 
market data and news for a given stock ticker and produce a concise, 
structured trading signal.

You will receive:
- Ticker symbol and company name
- Current price, intraday change, OHLC, bid/ask, volume
- 52-week range, P/E, EPS, dividend yield
- Recent news headlines (if available)
- Position context (if the user already holds this ticker):
  shares, average cost basis, current market value, day P&L, total P&L

When position context is provided, evaluate the signal in light of the
user's existing exposure. A SELL signal on a held position should account
for unrealized gains and the user's overall risk profile, not just price action.

You must respond with ONLY a valid JSON object — no preamble, no explanation,
no markdown formatting, no code fences. Just raw JSON.

Your response must follow this exact schema:
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
- SELL: Deteriorating fundamentals, negative catalyst, unfavorable risk/reward,
        or for held positions: justified profit-taking or loss-cutting
- HOLD: No clear edge in either direction, wait for better entry or more data

Confidence definitions:
- 80-100: Strong conviction, multiple confirming signals
- 60-79:  Moderate conviction, some uncertainty remains
- 40-59:  Low conviction, data is mixed or limited
- 0-39:   Very low conviction, do not act on this signal

IMPORTANT: You are generating research for human review only.
You are not executing trades. Be honest about uncertainty.
Flag any risk factors prominently.
"""


# =============================================================================
# SIGNAL GENERATION
# =============================================================================

def get_signal(ticker: str, quote: dict, position: dict = None,
               headlines: list = None, metrics: dict = None) -> dict:
    """
    Generate a structured trading signal for a ticker using Claude.

    ANALYST NOTE:
        When `position` is provided, Claude receives the user's holding
        context (shares, cost basis, P&L) and can evaluate SELL signals
        with awareness of unrealized gains and total exposure.

    Args:
        ticker     (str):  Stock symbol e.g. "AAPL"
        quote      (dict): Quote data from schwab_client.get_quote()
        position   (dict): Optional position detail if user holds this ticker
        headlines  (list): Optional list of recent news headline strings
        metrics    (dict): Optional dict of financial metrics

    Returns:
        dict: Structured signal, or error dict
    """

    prompt_parts = [
        f"Ticker: {ticker} ({quote.get('companyName', 'Unknown')})",
        f"Exchange: {quote.get('exchange', 'N/A')}",
        f"Current Price: ${quote.get('lastPrice', 'N/A')}",
        f"Day Change: ${quote.get('netChange', 0):.2f} ({quote.get('netPercentChange', 0):.2f}%)",
        f"Open: ${quote.get('openPrice', 'N/A')} | High: ${quote.get('highPrice', 'N/A')} | Low: ${quote.get('lowPrice', 'N/A')} | Prev Close: ${quote.get('closePrice', 'N/A')}",
        f"Bid / Ask: ${quote.get('bidPrice', 'N/A')} / ${quote.get('askPrice', 'N/A')}",
        f"Volume: {quote.get('totalVolume', 0):,} (10-day avg: {int(quote.get('avg10DayVolume', 0)):,})",
        f"52-Week Range: ${quote.get('fiftyTwoWeekLow', 'N/A')} - ${quote.get('fiftyTwoWeekHigh', 'N/A')}",
        f"P/E Ratio: {quote.get('peRatio', 'N/A')} | EPS: ${quote.get('eps', 'N/A')} | Div Yield: {quote.get('divYield', 0):.2f}%",
    ]

    # Add position context if provided
    if position and position.get("is_held"):
        prompt_parts.append("\n--- POSITION CONTEXT (You currently hold this) ---")
        prompt_parts.append(f"Shares Held    : {position.get('quantity', 0):.0f}")
        prompt_parts.append(f"Avg Cost Basis : ${position.get('average_price', 0):,.2f}")
        prompt_parts.append(f"Market Value   : ${position.get('market_value', 0):,.2f}")
        prompt_parts.append(f"Day P&L        : ${position.get('current_day_pnl', 0):,.2f} ({position.get('current_day_pnl_pct', 0):.2f}%)")
        prompt_parts.append(f"Total Open P&L : ${position.get('long_open_pnl', 0):,.2f}")
    else:
        prompt_parts.append("\n--- POSITION CONTEXT (Scouting — not currently held) ---")

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
            messages=[
                {"role": "user", "content": user_prompt}
            ]
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
    """
    Pretty-print a signal dict to the terminal for human review.
    """
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
