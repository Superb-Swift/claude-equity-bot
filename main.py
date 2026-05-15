# =============================================================================
# main.py
# =============================================================================
# PURPOSE:
#   Entry point for the Claude Equity Bot. Orchestrates the full pipeline:
#     1. Pull portfolio summary from Schwab
#     2. Fetch real-time quote for target ticker(s)
#     3. Ask Claude to generate a trading signal
#     4. Run signal through the risk engine
#     5. Log the result — NO orders placed in Phase 2
#
# ANALYST NOTE:
#   This file is deliberately kept thin. Its only job is to connect the
#   other modules together in the right order. Business logic lives in
#   the module files — main.py just orchestrates the sequence.
#
#   PHASE CONTROLS (set below):
#     PHASE 2 — Read-only: pulls data, generates signals, logs everything
#     PHASE 3 — Paper sim: same as Phase 2, simulates order log
#     PHASE 4 — Live (tiny): real orders, human approval required
#
# USAGE:
#   python main.py
#
# REQUIREMENTS:
#   - .env file with valid API keys
#   - Schwab app approved with Accounts and Trading Production access
#   - venv activated: venv\Scripts\activate
# =============================================================================

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
# ANALYST NOTE: Each module handles one concern. If something breaks,
# you know exactly which file to look in.
from schwab_client import get_quote, get_portfolio_summary
from claude_signal  import get_signal, print_signal
from risk_engine    import evaluate_signal, print_risk_report, calculate_position_size

# Load environment variables
load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

# --- Phase Control ---
# ANALYST NOTE: Change this value to control what the bot does with signals.
# Start at PHASE 2 and only advance after thorough testing of each phase.
#
#   PHASE = 2  →  Read-only dry run. No orders. Logs signals to file.
#   PHASE = 3  →  Paper simulation. Logs simulated orders. No real trades.
#   PHASE = 4  →  Live trading. Real orders. Human approval required.
PHASE = 2

# --- Watchlist ---
# ANALYST NOTE: Tickers the bot will analyze on each run.
# Start with 1-3 well-known, liquid large-caps while testing.
# Avoid penny stocks, OTC markets, or thinly traded names.
WATCHLIST = [
    "AAPL",   # Apple — large-cap, highly liquid, well-covered
    "MSFT",   # Microsoft — stable, strong fundamentals
    "SPY",    # S&P 500 ETF — useful as market benchmark
]

# --- Logging Setup ---
# ANALYST NOTE: Logs are written to a daily file so you can review
# every signal generated and every risk decision made.
# The .gitignore already excludes *.log files from GitHub.
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(
    LOG_DIR,
    f"signals_{datetime.now().strftime('%Y-%m-%d')}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()          # Also print to terminal
    ]
)

log = logging.getLogger(__name__)


# =============================================================================
# PHASE HANDLERS
# =============================================================================

def handle_phase2(ticker: str, signal: dict, portfolio: dict) -> None:
    """
    Phase 2: Dry run — log signal and risk decision, no execution.

    ANALYST NOTE:
        This is the safest starting point. Run this for at least 2 weeks
        before advancing to Phase 3. Review the log file daily and ask:
        - Are Claude's signals reasonable?
        - Are confidence scores calibrated correctly?
        - Are risk rules triggering appropriately?
        - Would these signals have made money in hindsight?
    """
    approved, reason = evaluate_signal(signal, portfolio)

    log.info(
        f"[PHASE 2 DRY RUN] {ticker} | "
        f"Signal: {signal.get('signal')} | "
        f"Confidence: {signal.get('confidence')}% | "
        f"Risk: {'APPROVED' if approved else 'REJECTED'} | "
        f"Reason: {reason}"
    )

    print_signal(signal)
    print_risk_report(signal, portfolio)
    print(f"  >>> PHASE 2: No order placed. Signal logged to {log_filename}\n")


def handle_phase3(ticker: str, signal: dict, portfolio: dict) -> None:
    """
    Phase 3: Paper simulation — log as if order was placed, no real execution.

    ANALYST NOTE:
        Run this for at least 4 weeks and track simulated P&L manually.
        Build a spreadsheet: date, ticker, signal, price, simulated shares,
        outcome 5/10/20 days later. Only advance to Phase 4 if you see
        a consistent edge in the simulation data.
    """
    approved, reason = evaluate_signal(signal, portfolio)

    if approved and signal.get("signal") in ["BUY", "SELL"]:
        price  = signal.get("lastPrice", 0) or portfolio.get("last_price", 0)
        pvalue = portfolio.get("portfolio_value", 0)
        shares = calculate_position_size(pvalue, price) if price else 0

        log.info(
            f"[PHASE 3 PAPER] SIMULATED ORDER | {ticker} | "
            f"Action: {signal.get('signal')} | "
            f"Shares: {shares} | "
            f"Price: ${price} | "
            f"Confidence: {signal.get('confidence')}%"
        )
    else:
        log.info(
            f"[PHASE 3 PAPER] NO ORDER | {ticker} | "
            f"Signal: {signal.get('signal')} | "
            f"Risk: REJECTED | Reason: {reason}"
        )

    print_signal(signal)
    print_risk_report(signal, portfolio)
    print(f"  >>> PHASE 3: Simulated order logged. No real trade placed.\n")


def handle_phase4(ticker: str, signal: dict, portfolio: dict) -> None:
    """
    Phase 4: Live trading with human approval gate.

    ANALYST NOTE:
        DO NOT advance here until:
        1. Phase 3 paper trading showed consistent edge over 4+ weeks
        2. You understand every line of code in this repo
        3. Risk rules have been reviewed and deliberately set
        4. You are prepared to lose the capital allocated

        REQUIRE_HUMAN_APPROVAL in risk_engine.py MUST remain True
        until you have extensive confidence in the system.
    """
    approved, reason = evaluate_signal(signal, portfolio)

    if not approved:
        log.warning(f"[PHASE 4] REJECTED | {ticker} | {reason}")
        print_signal(signal)
        print_risk_report(signal, portfolio)
        return

    if signal.get("signal") == "HOLD":
        log.info(f"[PHASE 4] HOLD | {ticker} | No action taken.")
        return

    # Human approval gate
    # ANALYST NOTE: This is intentionally interactive — a human must
    # type "yes" to proceed. Never automate past this gate in Phase 4.
    print_signal(signal)
    print_risk_report(signal, portfolio)

    print(f"\n  ⚠️  LIVE TRADE PENDING APPROVAL")
    print(f"  Action    : {signal.get('signal')} {ticker}")
    print(f"  Confidence: {signal.get('confidence')}%")
    print(f"  Reasoning : {signal.get('reasoning')}")
    print(f"  Risk Flags: {signal.get('risk_flags', [])}")

    approval = input("\n  Type 'yes' to approve this trade, anything else to cancel: ")

    if approval.strip().lower() == "yes":
        log.info(f"[PHASE 4] HUMAN APPROVED | {ticker} | {signal.get('signal')}")
        print("\n  >>> Order execution coming in Phase 4 full implementation.")
        print("  >>> Schwab order placement code will be added here.")
        # TODO: Add schwab_client.place_order() call here in Phase 4
    else:
        log.info(f"[PHASE 4] HUMAN CANCELLED | {ticker}")
        print("\n  >>> Trade cancelled by user.")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_bot():
    """
    Main execution pipeline — runs once per call.

    ANALYST NOTE:
        In production, you'd schedule this to run at market open, midday,
        and market close using Windows Task Scheduler or a cloud scheduler.
        For now, run it manually during market hours to test.

        Market hours: Monday-Friday, 9:30 AM - 4:00 PM Eastern Time.
        Pre/after-market data is available but signals are less reliable
        due to lower liquidity.
    """
    log.info("="*60)
    log.info(f"Claude Equity Bot — Phase {PHASE} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Watchlist: {', '.join(WATCHLIST)}")
    log.info("="*60)

    # ------------------------------------------------------------------
    # STEP 1: Pull portfolio summary
    # ANALYST NOTE: We pull this once and reuse it for all tickers
    # to avoid redundant API calls. The portfolio summary gives the
    # risk engine the context it needs for position sizing and limits.
    # ------------------------------------------------------------------
    log.info("Fetching portfolio summary from Schwab...")

    try:
        portfolio = get_portfolio_summary()
        if not portfolio:
            log.error("Could not fetch portfolio data. Check Schwab API credentials.")
            return

        log.info(
            f"Portfolio loaded | "
            f"Value: ${portfolio.get('portfolio_value', 0):,.2f} | "
            f"Cash: ${portfolio.get('cash_available', 0):,.2f} | "
            f"Positions: {len(portfolio.get('positions', []))}"
        )

    except Exception as e:
        log.error(f"Portfolio fetch failed: {e}")
        return

    # ------------------------------------------------------------------
    # STEP 2: Process each ticker in the watchlist
    # ------------------------------------------------------------------
    for ticker in WATCHLIST:
        log.info(f"\nProcessing: {ticker}")

        try:
            # STEP 2a: Fetch real-time quote
            # ANALYST NOTE: In a full implementation, you'd also pull
            # recent news headlines from a news API (Benzinga, Polygon.io)
            # and pass them to get_signal() for richer analysis.
            quote = get_quote(ticker)

            if not quote:
                log.warning(f"No quote data returned for {ticker} — skipping.")
                continue

            log.info(
                f"{ticker} | "
                f"Price: ${quote.get('lastPrice', 'N/A')} | "
                f"Change: {quote.get('netPercentChangeInDouble', 'N/A')}%"
            )

            # STEP 2b: Generate Claude signal
            # ANALYST NOTE: headlines=None for now — in Phase 3/4 wire in
            # a news API here to significantly improve signal quality.
            log.info(f"Requesting Claude signal for {ticker}...")
            signal = get_signal(
                ticker=ticker,
                quote=quote,
                headlines=None,   # TODO: Wire in news API in Phase 3
                metrics=None      # TODO: Wire in financial metrics in Phase 3
            )

            # Store last price in signal for position sizing reference
            signal["lastPrice"] = quote.get("lastPrice", 0)

            # Log the raw signal as JSON for audit trail
            log.info(f"Signal received: {json.dumps(signal, indent=2)}")

            # STEP 2c: Route to appropriate phase handler
            if PHASE == 2:
                handle_phase2(ticker, signal, portfolio)
            elif PHASE == 3:
                handle_phase3(ticker, signal, portfolio)
            elif PHASE == 4:
                handle_phase4(ticker, signal, portfolio)
            else:
                log.error(f"Unknown PHASE value: {PHASE}. Set to 2, 3, or 4.")

        except Exception as e:
            log.error(f"Error processing {ticker}: {e}")
            continue

    log.info("\nBot run complete.")
    log.info(f"Full log saved to: {log_filename}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # ANALYST NOTE: The if __name__ == "__main__" guard ensures this code
    # only runs when you execute main.py directly (python main.py).
    # It won't run if another file imports from main.py.
    run_bot()
