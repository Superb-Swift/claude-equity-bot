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
- Prior 5 trading-day closes (recent price trajectory) and the 5-day % change
- Your own prior signals and confidences for this ticker from recent
  sessions (when available)
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

PRICE TRAJECTORY (H1): You are also given the prior 5 trading-day closes
and the trailing 5-day % change. Let confidence reflect the RECENT
trajectory promptly — do not anchor to a stale read of the trend. If price
has already moved materially over the last five sessions, your signal and
confidence should account for that move NOW, not several sessions later.

THESIS STABILITY (H3): Separate your STABLE THESIS confidence — your durable
read on fundamentals, valuation, and the structural setup, which should change
only on a material catalyst — from NEWS-FLOW conviction, the noisier reaction
to individual headlines. The confidence you report must reflect the stable
thesis. A single day's headline, or a small price move (a few percent or less),
is a modifier to confidence, not a reason to flip BUY/SELL/HOLD; record such
reactions in your reasoning rather than letting them swing the reported
confidence. Reserve large confidence changes and signal reversals for genuine
catalysts — earnings, guidance, a real break in the multi-session price trend
shown above, or a regime event. Absent that, keep the signal and confidence
stable from one read to the next. This complements the trajectory guidance:
track the genuine multi-day trend promptly, but do not whipsaw on intraday
noise.

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


# H2 (variant B) — symmetric-framing addendum, appended to the base prompt ONLY
# for the "B" arm of the direction-asymmetry A/B. Variant "A" is the current
# build (H1 + H3) unchanged.
SYMMETRIC_FRAMING = """
DIRECTIONAL SYMMETRY (H2 — variant B): Update confidence symmetrically with
respect to direction. Weight comparable upside and downside evidence equally,
and re-rate into an improving trend as promptly and by as much as you de-rate
into a deteriorating one. Do not let losses move confidence faster or further
than equivalent gains — avoid loss-aversion in your updating. A recovery of a
given magnitude should raise confidence about as much as an equal-magnitude
decline would lower it.
"""


def build_system_prompt(variant: str = "A") -> str:
    """Return the system prompt for an A/B arm.

    "A" = the current build (H1 + H3) unchanged.
    "B" = the current build PLUS the H2 symmetric-framing addendum.
    """
    if str(variant).upper() == "B":
        return SYSTEM_PROMPT + SYMMETRIC_FRAMING
    return SYSTEM_PROMPT


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


def _build_price_history_section(price_history: list) -> list:
    """
    Build the prior-N-day price trajectory section (H1).

    ANALYST NOTE (H1):
        Targets the 3-5 day confidence update lag. Shows the recent closing
        path plus the trailing N-day % change so the model reacts to the
        move contemporaneously rather than several sessions behind it.
    """
    if not price_history:
        return ["\n--- PRICE TRAJECTORY (Prior closes unavailable) ---"]

    closes = [p.get("close") for p in price_history if p.get("close") is not None]
    lines = [f"\n--- PRICE TRAJECTORY (Prior {len(price_history)} trading-day closes) ---"]
    lines.append(
        "  ".join(f"{p.get('date', '?')}: ${p.get('close', 0):,.2f}" for p in price_history)
    )
    if len(closes) >= 2 and closes[0]:
        chg = (closes[-1] - closes[0]) / closes[0] * 100
        lines.append(
            f"{len(closes)}-day change: {chg:+.2f}%  "
            f"(${closes[0]:,.2f} -> ${closes[-1]:,.2f})"
        )
    return lines


def _build_prior_signal_section(prior_signals: list) -> list:
    """
    Build the prior-signal state section (S1 — the H1 feature-level input).

    ANALYST NOTE (S1):
        Feature-level implementation of the locked H1 verdict. Each call is
        otherwise stateless — the model cannot see that its own confidence
        has not moved while price did. This section feeds back the bot's own
        last-N outputs for the ticker (RAW confidence — never the damped
        value, so the model-side channel stays uncontaminated by Lever A)
        plus the net confidence change over the span, placed directly under
        the PRICE TRAJECTORY section for juxtaposition. Mechanical, numeric,
        computed. No behavioral phrasing is added — prompt-level phrasing was
        retired as a remedy class at the 3-A closeout.
    """
    if not prior_signals:
        return ["\n--- YOUR PRIOR SIGNALS (no prior-signal state available) ---"]
    lines = [f"\n--- YOUR PRIOR SIGNALS (this ticker, last {len(prior_signals)} sessions) ---"]
    lines.append(" | ".join(
        f"{p.get('date', '?')}: {p.get('signal', '?')} {int(p.get('conf', 0))}%"
        for p in prior_signals
    ))
    confs = [p.get("conf") for p in prior_signals if p.get("conf") is not None]
    if len(confs) >= 2:
        lines.append(
            f"Net confidence change over span: {int(confs[-1]) - int(confs[0]):+d} pts"
        )
    return lines


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
               headlines: list = None, metrics: dict = None,
               price_history: list = None, prior_signals: list = None,
               prompt_variant: str = "A") -> dict:
    """
    Generate a structured trading signal for a ticker using Claude.

    Args:
        ticker     (str):  Stock symbol
        quote      (dict): Quote data from schwab_client.get_quote()
        position   (dict): Optional consolidated position context
        headlines  (list): Optional list of recent headlines
        metrics    (dict): Optional financial metrics
        price_history (list): Optional prior-N-day closes (H1 trajectory input)
        prior_signals (list): Optional last-N own outputs for this ticker
                              (S1 prior-signal state input)
        prompt_variant (str): "A" (base build) or "B" (H2 symmetric framing)

    Returns:
        dict: Structured signal, or error dict
    """
    prompt_parts = []
    prompt_parts.extend(_build_market_data_section(quote))
    prompt_parts.extend(_build_fundamentals_section(quote))
    prompt_parts.extend(_build_price_history_section(price_history))  # H1
    prompt_parts.extend(_build_prior_signal_section(prior_signals))   # S1 (H1 feature-level)
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
            system=build_system_prompt(prompt_variant),
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = response.content[0].text.strip()
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        signal = json.loads(clean_text)

        signal["model"]         = MODEL
        signal["input_tokens"]  = response.usage.input_tokens
        signal["output_tokens"] = response.usage.output_tokens
        signal["prompt_variant"] = prompt_variant

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
    raw   = signal.get("confidence_raw")
    conf_str = f"{conf}%" if raw in (None, conf) else f"{conf}% (raw {raw}%)"
    color = COLORS.get(sig, COLORS["RESET"])

    print("\n" + "="*60)
    print(f"  SIGNAL: {color}{sig}{COLORS['RESET']}  |  "
          f"Ticker: {signal.get('ticker')}  |  "
          f"Confidence: {conf_str}")
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
