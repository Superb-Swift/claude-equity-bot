# =============================================================================
# claude_signal.py
# =============================================================================
# PURPOSE:
#   Uses the Anthropic Claude API to analyze market data and generate
#   structured trading signals for individual equity tickers.
#
# ANALYST NOTE:
#   This file is the "brain" of the bot. It takes raw market data (quotes,
#   headlines, price history) and asks Claude to reason about it like a
#   junior equity analyst would. Claude outputs a structured JSON signal
#   that the risk engine and main.py can act on.
#
#   Claude's edge here is qualitative reasoning — synthesizing news sentiment,
#   earnings language, and market context faster than manual analysis.
#   It is NOT a quantitative model and should not be treated as one.
#
# DEPENDENCIES:
#   pip install anthropic python-dotenv
#
# USAGE:
#   from claude_signal import get_signal
# =============================================================================

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Anthropic client
# ANALYST NOTE: The Anthropic client automatically reads ANTHROPIC_API_KEY
# from the environment. No need to pass it explicitly.
client = Anthropic()

# Model selection
# ANALYST NOTE: claude-sonnet-4-6 is the recommended balance of speed,
# cost, and reasoning quality for this use case. Claude Opus would give
# deeper reasoning at higher cost — consider it for weekly deep-dive analysis.
MODEL = "claude-sonnet-4-6"

# System prompt — defines Claude's role and output format
# ANALYST NOTE: The system prompt is the most important part of the signal
# generation architecture. It tells Claude:
#   1. What role to play (equity research analyst)
#   2. What data it will receive
#   3. Exactly what format to return
#   4. What NOT to do (no preamble, no markdown, no speculation)
# Keeping the system prompt strict and specific dramatically improves
# consistency and parsability of Claude's responses.
SYSTEM_PROMPT = """
You are a disciplined equity research analyst. Your job is to analyze 
market data and news for a given stock ticker and produce a concise, 
structured trading signal.

You will receive:
- Ticker symbol
- Current price and intraday change
- Recent news headlines
- Key financial metrics (if available)

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
  "data_quality": "HIGH" | "MEDIUM" | "LOW"
}

Signal definitions:
- BUY: Meaningful positive catalyst, asymmetric upside, favorable risk/reward
- SELL: Deteriorating fundamentals, negative catalyst, unfavorable risk/reward  
- HOLD: No clear edge in either direction, wait for better entry or more data

Confidence definitions:
- 80-100: Strong conviction, multiple confirming signals
- 60-79:  Moderate conviction, some uncertainty remains
- 40-59:  Low conviction, data is mixed or limited
- 0-39:   Very low conviction, do not act on this signal

data_quality reflects how much reliable data was available:
- HIGH: Recent news, clean price data, clear narrative
- MEDIUM: Some data gaps or conflicting signals
- LOW: Limited data, stale news, or highly uncertain environment

IMPORTANT: You are generating research for human review only.
You are not executing trades. Be honest about uncertainty.
Flag any risk factors prominently.
"""


# =============================================================================
# SIGNAL GENERATION
# =============================================================================

def get_signal(ticker: str, quote: dict, headlines: list = None,
               metrics: dict = None) -> dict:
    """
    Generate a structured trading signal for a ticker using Claude.

    ANALYST NOTE:
        This function constructs a detailed prompt from available market data
        and asks Claude to reason about it. The more context you provide
        (headlines, metrics), the higher quality Claude's signal will be.
        At minimum, a quote dict with lastPrice is required.

    Args:
        ticker     (str):  Stock symbol e.g. "AAPL"
        quote      (dict): Quote data from schwab_client.get_quote()
        headlines  (list): Optional list of recent news headline strings
        metrics    (dict): Optional dict of financial metrics (P/E, EPS, etc.)

    Returns:
        dict: Structured signal matching the schema above, or error dict
    """

    # Build the user prompt from available data
    # ANALYST NOTE: We construct the prompt dynamically so Claude always
    # gets the freshest data. Format it clearly so Claude can parse each
    # section without ambiguity.
    prompt_parts = [
        f"Ticker: {ticker}",
        f"Current Price: ${quote.get('lastPrice', 'N/A')}",
        f"Bid / Ask: ${quote.get('bidPrice', 'N/A')} / ${quote.get('askPrice', 'N/A')}",
        f"Day Change: {quote.get('netPercentChangeInDouble', 'N/A')}%",
        f"Volume: {quote.get('totalVolume', 'N/A')}",
        f"52-Week High: ${quote.get('52WkHigh', 'N/A')}",
        f"52-Week Low: ${quote.get('52WkLow', 'N/A')}",
    ]

    # Append headlines if provided
    if headlines:
        prompt_parts.append("\nRecent News Headlines:")
        for i, headline in enumerate(headlines[:5], 1):  # Cap at 5 headlines
            prompt_parts.append(f"  {i}. {headline}")
    else:
        prompt_parts.append("\nRecent News Headlines: None provided")

    # Append financial metrics if provided
    if metrics:
        prompt_parts.append("\nKey Financial Metrics:")
        for key, value in metrics.items():
            prompt_parts.append(f"  {key}: {value}")

    prompt_parts.append(
        "\nBased on this data, generate your structured JSON signal."
    )

    user_prompt = "\n".join(prompt_parts)

    # Call the Claude API
    # ANALYST NOTE: max_tokens=800 is sufficient for the JSON schema above.
    # Temperature defaults to 1.0 in the API — for financial signals we want
    # consistency over creativity, so we set it lower at 0.2.
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract the text content from Claude's response
        raw_text = response.content[0].text.strip()

        # Parse the JSON response
        # ANALYST NOTE: We strip any accidental markdown fences Claude
        # might add despite our instructions. Defensive parsing like this
        # prevents crashes when Claude occasionally breaks format.
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        signal = json.loads(clean_text)

        # Add metadata for logging purposes
        signal["model"]         = MODEL
        signal["input_tokens"]  = response.usage.input_tokens
        signal["output_tokens"] = response.usage.output_tokens

        return signal

    except json.JSONDecodeError as e:
        print(f"[claude_signal] Failed to parse Claude's response as JSON: {e}")
        print(f"[claude_signal] Raw response: {raw_text}")
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

    ANALYST NOTE:
        This is for Phase 2/3 dry runs where we review signals manually
        before any execution logic is wired in. Color coding helps quickly
        identify BUY/SELL/HOLD at a glance.

    Args:
        signal (dict): Signal dict from get_signal()
    """
    # Simple terminal color codes
    COLORS = {
        "BUY"  : "\033[92m",  # Green
        "SELL" : "\033[91m",  # Red
        "HOLD" : "\033[93m",  # Yellow
        "RESET": "\033[0m"
    }

    sig  = signal.get("signal", "HOLD")
    conf = signal.get("confidence", 0)
    color = COLORS.get(sig, COLORS["RESET"])

    print("\n" + "="*60)
    print(f"  SIGNAL: {color}{sig}{COLORS['RESET']}  |  "
          f"Ticker: {signal.get('ticker')}  |  "
          f"Confidence: {conf}%")
    print("="*60)
    print(f"  Reasoning  : {signal.get('reasoning')}")
    print(f"  Bull Case  : {signal.get('bull_case')}")
    print(f"  Bear Case  : {signal.get('bear_case')}")
    print(f"  Time Frame : {signal.get('time_horizon')}")
    print(f"  Data Quality: {signal.get('data_quality')}")

    flags = signal.get("risk_flags", [])
    if flags:
        print(f"  Risk Flags : {', '.join(flags)}")

    print(f"  Tokens Used: {signal.get('input_tokens', '?')} in / "
          f"{signal.get('output_tokens', '?')} out")
    print("="*60 + "\n")
