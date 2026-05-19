# =============================================================================
# ticker_suggester.py
# =============================================================================
# PURPOSE:
#   Asks Claude to suggest new tickers worth analyzing based on:
#     A. Sector gaps in your current portfolio
#     B. Market themes/catalysts in current news flow
#     C. Peer companies to your existing holdings
#
# ANALYST NOTE:
#   This is a "generative" addition to the bot — instead of just analyzing
#   what you tell it to, it proposes ideas you might not have considered.
#   Output is LOGGED for manual review, not auto-fed into the watchlist.
#   You promote ideas manually by editing WATCHLIST_SCOUT in main.py.
#
#   Runs once per day, costs ~$0.02-0.03 in Claude tokens. Generates 5-10
#   ticker ideas per run with reasoning.
#
# USAGE:
#   from ticker_suggester import suggest_tickers
#   ideas = suggest_tickers(held_tickers, current_scout_list, market_headlines)
# =============================================================================

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """
You are a portfolio analyst tasked with suggesting new ticker ideas
for further research. You generate three categories of suggestions:

1. SECTOR GAP — Tickers that would fill underrepresented sectors in
   the user's current portfolio. Identify what they're missing.

2. THEME — Tickers riding strong market catalysts evident in news flow.
   Focus on sustainable themes, not single-day moves.

3. PEER — Tickers similar to existing holdings that offer comparable
   exposure with different risk/return characteristics.

You must respond with ONLY a valid JSON object. No preamble, no markdown,
no code fences. Schema:

{
  "portfolio_observations": "1-2 sentences on what you see in the portfolio",
  "suggestions": [
    {
      "ticker": "string",
      "company": "string",
      "category": "SECTOR_GAP" | "THEME" | "PEER",
      "reasoning": "1-2 sentence rationale",
      "related_to": "ticker or sector this connects to (if applicable)",
      "priority": "HIGH" | "MEDIUM" | "LOW"
    }
  ]
}

Rules:
- Suggest 6-9 total tickers across the three categories
- DO NOT suggest tickers already held or already on the scout list
- Stick to liquid US-listed equities and ETFs ($1B+ market cap preferred)
- For SECTOR_GAP suggestions, name the specific gap being filled
- For THEME suggestions, cite the catalyst from the headlines provided
- For PEER suggestions, name the existing holding the suggestion relates to
- HIGH priority = strong conviction + clear catalyst
- MEDIUM priority = solid idea but no urgent catalyst
- LOW priority = worth monitoring but not adding now

Be honest. If nothing in the news flow supports a THEME suggestion, return
fewer THEME ideas. Don't pad the list to hit a count.
"""


# =============================================================================
# SUGGESTION GENERATOR
# =============================================================================

def suggest_tickers(held_tickers: list, scout_list: list,
                    market_headlines: list = None) -> dict:
    """
    Ask Claude for new ticker ideas based on portfolio and market context.

    ANALYST NOTE:
        We send Claude three pieces of context:
        1. The user's current holdings (so it can identify gaps and peers)
        2. The current scout list (so it doesn't duplicate)
        3. Recent market headlines (for theme detection)

        The headlines should be broad-market news — not ticker-specific.
        Aggregating a handful of SPY/QQQ headlines gives Claude a sense
        of "what the market is talking about" without ticker bias.

    Args:
        held_tickers     (list): All tickers currently held across accounts
        scout_list       (list): Current WATCHLIST_SCOUT from main.py
        market_headlines (list): Recent broad-market news (optional)

    Returns:
        dict: Structured suggestion output matching the schema above
    """

    prompt_parts = [
        "=== USER'S CURRENT PORTFOLIO ===",
        f"Currently Held Tickers ({len(held_tickers)}): {', '.join(sorted(set(held_tickers)))}",
        "",
        "=== CURRENT SCOUT WATCHLIST ===",
        f"Already Watching: {', '.join(scout_list)}",
        "",
        "=== MARKET CONTEXT ===",
    ]

    if market_headlines:
        prompt_parts.append("Recent broad-market headlines:")
        for i, headline in enumerate(market_headlines[:10], 1):
            prompt_parts.append(f"  {i}. {headline}")
    else:
        prompt_parts.append("No market headlines provided.")

    prompt_parts.extend([
        "",
        "=== TASK ===",
        "Generate your structured JSON suggestion list following the schema. "
        "Focus on quality over quantity — 6-9 strong ideas across the three "
        "categories. Skip categories where the data doesn't support solid "
        "suggestions.",
    ])

    user_prompt = "\n".join(prompt_parts)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = response.content[0].text.strip()
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)

        result["input_tokens"]  = response.usage.input_tokens
        result["output_tokens"] = response.usage.output_tokens

        return result

    except json.JSONDecodeError as e:
        print(f"[ticker_suggester] Failed to parse Claude's response: {e}")
        return {"error": "parse_error", "suggestions": []}

    except Exception as e:
        print(f"[ticker_suggester] Unexpected error: {e}")
        return {"error": str(e), "suggestions": []}


# =============================================================================
# DISPLAY
# =============================================================================

def print_suggestions(result: dict) -> None:
    """
    Pretty-print the suggestion list to the terminal.

    ANALYST NOTE:
        Color-codes priority levels and groups by category so you can
        scan it quickly. The full structured output also goes to the
        log file via main.py.
    """
    COLORS = {
        "HIGH"   : "\033[92m",   # Green
        "MEDIUM" : "\033[93m",   # Yellow
        "LOW"    : "\033[90m",   # Gray
        "RESET"  : "\033[0m",
    }

    print("\n" + "="*72)
    print("  🎯 TICKER SUGGESTIONS — Claude's Daily Ideas")
    print("="*72)

    obs = result.get("portfolio_observations", "")
    if obs:
        print(f"  Portfolio Observation: {obs}")
        print()

    suggestions = result.get("suggestions", [])
    if not suggestions:
        print("  No suggestions generated.")
        print("="*72 + "\n")
        return

    # Group by category for cleaner display
    categories = {"SECTOR_GAP": [], "THEME": [], "PEER": []}
    for s in suggestions:
        cat = s.get("category", "OTHER")
        if cat in categories:
            categories[cat].append(s)

    category_labels = {
        "SECTOR_GAP": "🧩 SECTOR GAPS — Fill missing portfolio exposure",
        "THEME"     : "📰 THEMES — Riding current market catalysts",
        "PEER"      : "🔗 PEERS — Similar to your holdings",
    }

    for cat, items in categories.items():
        if not items:
            continue
        print(f"  {category_labels[cat]}")
        print("  " + "-"*68)
        for s in items:
            prio = s.get("priority", "MEDIUM")
            color = COLORS.get(prio, COLORS["RESET"])
            print(f"  {color}[{prio:<6}]{COLORS['RESET']} "
                  f"{s.get('ticker', '?'):<6} {s.get('company', '')[:35]}")
            print(f"           Why: {s.get('reasoning', '')}")
            related = s.get("related_to", "")
            if related:
                print(f"           Related to: {related}")
            print()

    print(f"  Tokens used: {result.get('input_tokens', '?')} in / "
          f"{result.get('output_tokens', '?')} out")
    print("="*72)
    print("  💡 To promote any of these, add to WATCHLIST_SCOUT in main.py")
    print("="*72 + "\n")


# =============================================================================
# LOG TO FILE
# =============================================================================

def log_suggestions(result: dict, log_dir: str = "logs") -> str:
    """
    Append today's suggestions to a running ideas history file.

    ANALYST NOTE:
        Suggestions go to logs/suggestions_history.txt so you can review
        them across days. Watch for tickers that suggest repeatedly —
        those are the strongest candidates for promotion to the watchlist.
    """
    from datetime import datetime
    os.makedirs(log_dir, exist_ok=True)

    history_file = os.path.join(log_dir, "suggestions_history.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"\n\n[Suggestions generated: {timestamp}]\n")
        f.write("="*72 + "\n")

        obs = result.get("portfolio_observations", "")
        if obs:
            f.write(f"Observation: {obs}\n\n")

        for s in result.get("suggestions", []):
            f.write(f"  [{s.get('priority', '?'):<6}] "
                    f"{s.get('ticker', '?'):<6} ({s.get('category', '?')})  "
                    f"{s.get('company', '')}\n")
            f.write(f"           {s.get('reasoning', '')}\n")
            related = s.get("related_to", "")
            if related:
                f.write(f"           Related: {related}\n")
            f.write("\n")

    return history_file
