# =============================================================================
# main.py
# =============================================================================
# PURPOSE:
#   Entry point for the Claude Equity Bot.
#
#   MULTI-ACCOUNT MONITORING + SCOUTING + NEWS WORKFLOW:
#     1. Pull every active account from Schwab
#     2. For each account:
#        a. Print portfolio overview with account label
#        b. Build watchlist: held tickers + scout tickers
#        c. For each ticker: fetch quote + recent headlines
#        d. Generate position-aware Claude signal with news context
#        e. Run signal through risk engine
#        f. Log everything tagged by account
#     3. Print aggregate summary across all accounts
#
# ANALYST NOTE:
#   News headlines are fetched once per ticker and cached across accounts
#   to minimize Finnhub API calls. The Finnhub free tier allows 60/min
#   so this is rarely a constraint but it is good practice.
#
# USAGE:
#   python main.py
# =============================================================================

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

from schwab_client import (
    get_quote,
    get_all_portfolios,
    get_position_detail,
    ACCOUNT_LABELS,
)
from claude_signal import get_signal, print_signal
from risk_engine  import evaluate_signal, print_risk_report, calculate_position_size
from news_client  import get_recent_headlines

load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

# --- Phase Control ---
#   PHASE = 2  →  Read-only dry run. No orders. Logs signals to file.
#   PHASE = 3  →  Paper simulation. Logs simulated orders. No real trades.
#   PHASE = 4  →  Live trading. Real orders. Human approval required.
PHASE = 2

# --- Scouting Watchlist ---
WATCHLIST_SCOUT = [
    "SPY",    # S&P 500 — broad market benchmark
    "QQQ",    # Nasdaq 100 — tech-heavy benchmark
    "VTI",    # Total stock market — diversified core
    "NVDA",   # AI semiconductor bellwether
    "GLD",    # Gold ETF — defensive hedge
]

# --- Monitoring Toggle ---
MONITOR_HOLDINGS = True

# --- News Settings ---
# ANALYST NOTE: Tune these based on signal quality vs API cost tradeoffs.
# More days back = more historical context but possibly stale.
# More headlines = richer analysis but more Claude tokens consumed.
NEWS_DAYS_BACK = 7    # Look back 1 week for headlines
NEWS_LIMIT     = 5    # Top 5 most recent headlines per ticker

# --- Logging Setup ---
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
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)


# =============================================================================
# PORTFOLIO DISPLAY
# =============================================================================

def print_portfolio_overview(portfolio: dict) -> None:
    """
    Print a clean overview of a single account's portfolio.
    """
    label     = portfolio.get("account_label", "Account")
    positions = portfolio.get("positions", [])

    print("\n" + "="*72)
    print(f"  PORTFOLIO OVERVIEW — {label}")
    print("="*72)
    print(f"  Total Value     : ${portfolio.get('portfolio_value', 0):>12,.2f}")
    print(f"  Cash Available  : ${portfolio.get('cash_available', 0):>12,.2f}")
    print(f"  Position Count  : {len(positions):>13}")

    if not positions:
        print("-"*72)
        print("  No equity positions in this account.")
        print("="*72 + "\n")
        return

    print("-"*72)
    print(f"  {'Ticker':<8} {'Shares':>10} {'Avg Price':>12} "
          f"{'Mkt Value':>12} {'Day P&L':>14}")
    print("-"*72)

    for position in positions:
        instrument = position.get("instrument", {})
        symbol     = instrument.get("symbol", "?")
        shares     = position.get("longQuantity", 0)
        avg_price  = position.get("averagePrice", 0)
        mkt_value  = position.get("marketValue", 0)
        day_pnl    = position.get("currentDayProfitLoss", 0)

        if day_pnl > 0:
            pnl_str = f"\033[92m+${day_pnl:>10,.2f}\033[0m"
        elif day_pnl < 0:
            pnl_str = f"\033[91m-${abs(day_pnl):>10,.2f}\033[0m"
        else:
            pnl_str = f" ${day_pnl:>10,.2f}"

        print(f"  {symbol:<8} {shares:>10.0f} ${avg_price:>11,.2f} "
              f"${mkt_value:>11,.2f}  {pnl_str}")

    print("="*72 + "\n")


def print_aggregate_summary(portfolios: list) -> None:
    """
    Print a roll-up summary across all analyzed accounts.
    """
    total_value     = sum(p.get("portfolio_value", 0) for p in portfolios)
    total_cash      = sum(p.get("cash_available", 0)  for p in portfolios)
    total_positions = sum(len(p.get("positions", [])) for p in portfolios)

    print("\n" + "="*72)
    print(f"  AGGREGATE SUMMARY — {len(portfolios)} Account(s)")
    print("="*72)
    for p in portfolios:
        label  = p.get("account_label", "Account")
        value  = p.get("portfolio_value", 0)
        cash   = p.get("cash_available", 0)
        pcount = len(p.get("positions", []))
        print(f"  {label:<20} ${value:>12,.2f} value | "
              f"${cash:>10,.2f} cash | {pcount} positions")
    print("-"*72)
    print(f"  {'TOTAL':<20} ${total_value:>12,.2f} value | "
          f"${total_cash:>10,.2f} cash | {total_positions} positions")
    print("="*72 + "\n")


# =============================================================================
# PHASE HANDLERS
# =============================================================================

def handle_phase2(ticker: str, signal: dict, portfolio: dict,
                  position_detail: dict, account_label: str) -> None:
    """Phase 2: Dry run — log signal and risk decision, no execution."""
    approved, reason = evaluate_signal(signal, portfolio)
    held_marker = "[HELD]" if position_detail.get("is_held") else "[SCOUT]"

    log.info(
        f"[PHASE 2 DRY RUN] [{account_label}] {held_marker} {ticker} | "
        f"Signal: {signal.get('signal')} | "
        f"Confidence: {signal.get('confidence')}% | "
        f"Risk: {'APPROVED' if approved else 'REJECTED'} | "
        f"Reason: {reason}"
    )

    print_signal(signal)
    print_risk_report(signal, portfolio)
    print(f"  >>> PHASE 2: No order placed. Signal logged to {log_filename}\n")


def handle_phase3(ticker: str, signal: dict, portfolio: dict,
                  position_detail: dict, account_label: str) -> None:
    """Phase 3: Paper simulation — log as if order was placed."""
    approved, reason = evaluate_signal(signal, portfolio)
    held_marker = "[HELD]" if position_detail.get("is_held") else "[SCOUT]"

    if approved and signal.get("signal") in ["BUY", "SELL"]:
        price  = signal.get("lastPrice", 0)
        pvalue = portfolio.get("portfolio_value", 0)
        shares = calculate_position_size(pvalue, price) if price else 0

        log.info(
            f"[PHASE 3 PAPER] [{account_label}] {held_marker} "
            f"SIMULATED ORDER | {ticker} | "
            f"Action: {signal.get('signal')} | "
            f"Shares: {shares} | Price: ${price}"
        )
    else:
        log.info(
            f"[PHASE 3 PAPER] [{account_label}] {held_marker} NO ORDER | "
            f"{ticker} | Signal: {signal.get('signal')} | Reason: {reason}"
        )

    print_signal(signal)
    print_risk_report(signal, portfolio)


def handle_phase4(ticker: str, signal: dict, portfolio: dict,
                  position_detail: dict, account_label: str) -> None:
    """Phase 4: Live trading with human approval gate."""
    approved, reason = evaluate_signal(signal, portfolio)
    held_marker = "[HELD]" if position_detail.get("is_held") else "[SCOUT]"

    if not approved:
        log.warning(f"[PHASE 4] [{account_label}] {held_marker} REJECTED | "
                    f"{ticker} | {reason}")
        print_signal(signal)
        print_risk_report(signal, portfolio)
        return

    if signal.get("signal") == "HOLD":
        log.info(f"[PHASE 4] [{account_label}] {held_marker} HOLD | {ticker}")
        return

    print_signal(signal)
    print_risk_report(signal, portfolio)

    print(f"\n  ⚠️  LIVE TRADE PENDING APPROVAL — {account_label}")
    print(f"  Action    : {signal.get('signal')} {ticker} {held_marker}")
    print(f"  Confidence: {signal.get('confidence')}%")
    print(f"  Reasoning : {signal.get('reasoning')}")

    approval = input(
        "\n  Type 'yes' to approve this trade, anything else to cancel: "
    )

    if approval.strip().lower() == "yes":
        log.info(f"[PHASE 4] [{account_label}] HUMAN APPROVED | {ticker} | "
                 f"{signal.get('signal')}")
        print("\n  >>> Order execution coming in Phase 4 full implementation.")
    else:
        log.info(f"[PHASE 4] [{account_label}] HUMAN CANCELLED | {ticker}")
        print("\n  >>> Trade cancelled by user.")


# =============================================================================
# CORE PROCESSING
# =============================================================================

def process_ticker(ticker: str, portfolio: dict, quote_cache: dict,
                   news_cache: dict, scout_signal_cache: dict) -> None:
    """
    Process a single ticker for a single account with news context.

    ANALYST NOTE:
        Three caches for efficiency:
          - quote_cache: same quote reused across accounts
          - news_cache: same headlines reused across accounts
          - scout_signal_cache: scout signals identical across accounts
        Held tickers always get fresh Claude signals because position
        context differs between accounts.
    """
    label = portfolio.get("account_label", "Account")
    log.info(f"\nProcessing: {ticker}  [account: {label}]")

    try:
        # Quote cache — reuse across accounts
        if ticker in quote_cache:
            quote = quote_cache[ticker]
        else:
            quote = get_quote(ticker)
            quote_cache[ticker] = quote

        if not quote:
            log.warning(f"No quote data for {ticker} — skipping.")
            return

        log.info(
            f"{ticker} | Price: ${quote.get('lastPrice', 'N/A')} | "
            f"Change: {quote.get('netPercentChange', 0):.2f}%"
        )

        # News cache — reuse across accounts
        if ticker in news_cache:
            headlines = news_cache[ticker]
        else:
            log.info(f"Fetching news for {ticker}...")
            headlines = get_recent_headlines(
                ticker,
                days_back=NEWS_DAYS_BACK,
                limit=NEWS_LIMIT
            )
            news_cache[ticker] = headlines

        if headlines:
            log.info(f"Found {len(headlines)} headline(s) for {ticker}")
        else:
            log.info(f"No recent news for {ticker}")

        # Look up position context
        position_detail = get_position_detail(
            portfolio.get("positions", []), ticker
        )

        is_held = position_detail.get("is_held", False)
        position_context = position_detail if is_held else None

        if is_held:
            log.info(
                f"[HELD in {label}] {ticker} | "
                f"Shares: {position_detail.get('quantity'):.0f} | "
                f"Avg Cost: ${position_detail.get('average_price', 0):,.2f} | "
                f"Day P&L: ${position_detail.get('current_day_pnl', 0):,.2f}"
            )
        else:
            log.info(f"[SCOUT in {label}] {ticker} | Not currently held")

        # Scout signal cache — same across accounts
        if not is_held and ticker in scout_signal_cache:
            log.info(f"Using cached scout signal for {ticker}")
            signal = scout_signal_cache[ticker]
        else:
            log.info(f"Requesting Claude signal for {ticker}...")
            signal = get_signal(
                ticker=ticker,
                quote=quote,
                position=position_context,
                headlines=headlines,
                metrics=None
            )
            if not is_held:
                scout_signal_cache[ticker] = signal

        signal["lastPrice"] = quote.get("lastPrice", 0)

        if PHASE == 2:
            handle_phase2(ticker, signal, portfolio, position_detail, label)
        elif PHASE == 3:
            handle_phase3(ticker, signal, portfolio, position_detail, label)
        elif PHASE == 4:
            handle_phase4(ticker, signal, portfolio, position_detail, label)
        else:
            log.error(f"Unknown PHASE: {PHASE}. Set to 2, 3, or 4.")

    except Exception as e:
        log.error(f"Error processing {ticker} in {label}: {e}")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_bot():
    """Main execution pipeline — runs once per call."""
    log.info("="*60)
    log.info(f"Claude Equity Bot — Phase {PHASE} — "
             f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("="*60)

    # STEP 1: Pull all active portfolios
    log.info("Fetching all account portfolios from Schwab...")

    try:
        portfolios = get_all_portfolios()
        if not portfolios:
            log.error("No active portfolios found. Check ACTIVE_ACCOUNTS "
                      "in schwab_client.py.")
            return

        log.info(f"Loaded {len(portfolios)} active account(s): "
                 f"{', '.join(p['account_label'] for p in portfolios)}")

    except Exception as e:
        log.error(f"Portfolio fetch failed: {e}")
        return

    # STEP 2: Print overview for each account
    for portfolio in portfolios:
        print_portfolio_overview(portfolio)

    # STEP 3: Print aggregate summary
    print_aggregate_summary(portfolios)

    # STEP 4: Process each account with shared caches
    quote_cache         = {}   # ticker → quote
    news_cache          = {}   # ticker → headlines
    scout_signal_cache  = {}   # ticker → signal (scout only)

    for portfolio in portfolios:
        label = portfolio.get("account_label", "Account")
        held_tickers = portfolio.get("held_tickers", []) if MONITOR_HOLDINGS else []

        seen = set()
        watchlist = []
        for ticker in held_tickers + WATCHLIST_SCOUT:
            if ticker not in seen:
                watchlist.append(ticker)
                seen.add(ticker)

        held_count  = sum(1 for t in watchlist if t in held_tickers)
        scout_count = len(watchlist) - held_count

        log.info("\n" + "#"*60)
        log.info(f"# ANALYZING ACCOUNT: {label}")
        log.info(f"# {len(watchlist)} tickers: "
                 f"{held_count} held + {scout_count} scouting")
        log.info("#"*60)

        for ticker in watchlist:
            process_ticker(ticker, portfolio, quote_cache,
                           news_cache, scout_signal_cache)

    log.info("\nBot run complete.")
    log.info(f"Full log saved to: {log_filename}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_bot()
