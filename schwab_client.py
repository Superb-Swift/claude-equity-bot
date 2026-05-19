# =============================================================================
# schwab_client.py
# =============================================================================
# PURPOSE:
#   Handles all communication with the Charles Schwab Trader API.
#   Supports multiple accounts with friendly labels.
#
# ANALYST NOTE:
#   This file is the "data layer" of the bot. It knows nothing about Claude
#   or trading decisions — it only knows how to talk to Schwab and return
#   clean data.
#
# DEPENDENCIES:
#   pip install schwab-py python-dotenv
# =============================================================================

import os
import schwab
from dotenv import load_dotenv

load_dotenv()

APP_KEY      = os.getenv("SCHWAB_APP_KEY")
APP_SECRET   = os.getenv("SCHWAB_APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "https://127.0.0.1:8182")
TOKEN_PATH   = os.getenv("TOKEN_PATH", "token.json")


# =============================================================================
# ACCOUNT LABELS
# =============================================================================

ACCOUNT_LABELS = {
    "XXXXXXXX": "Roth IRA",
    "XXXXXXXX": "Individual",
}

ACTIVE_ACCOUNTS = [
    "XXXXXXXX",   # Roth IRA
    "XXXXXXXX",   # Individual
]


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_client():
    """Authenticate with Schwab and return an authenticated client object."""
    if not APP_KEY or not APP_SECRET:
        raise ValueError(
            "SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in your .env file."
        )

    return schwab.auth.easy_client(
        api_key=APP_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=TOKEN_PATH
    )


# =============================================================================
# MARKET DATA
# =============================================================================

# ANALYST NOTE: Schwab's assetMainType values that we treat as equities vs ETFs.
# This determines which fundamental fields are trustworthy.
#
# EQUITY              → individual stocks. peRatio, eps, divYield all reliable.
# COLLECTIVE_INVESTMENT → ETFs/mutual funds. peRatio is unreliable per testing
#                        (returns expense ratio or some weighted number, not
#                        the actual underlying-holdings P/E). Suppress these.
#EQUITY_ASSET_TYPES = {"EQUITY"}
#ETF_ASSET_TYPES    = {"COLLECTIVE_INVESTMENT", "ETF", "MUTUAL_FUND"}
# ANALYST NOTE: Schwab classifies ETFs as assetMainType="EQUITY" because they
# trade on exchanges like stocks. The actual fund-vs-stock distinction lives
# in assetSubType. Diagnostic on SPY confirmed:
#   AAPL → assetMainType: EQUITY, assetSubType: COE  (Common Equity)
#   SPY  → assetMainType: EQUITY, assetSubType: ETF
# We use assetSubType to detect ETFs/funds and suppress unreliable P/E values.
ETF_SUB_TYPES = {"ETF", "ETN", "CEF", "MUTUAL_FUND"}

def get_quote(ticker: str) -> dict:
    """
    Fetch a real-time quote for a single ticker symbol.

    ANALYST NOTE:
        Returns a flattened dict with an "is_etf" flag derived from
        Schwab's assetMainType. Downstream code uses this to decide
        which fundamental fields to display to Claude.

        For ETFs we suppress P/E and EPS (Schwab values are unreliable)
        but keep dividend yield since that field IS accurate for ETFs.

    Args:
        ticker (str): Stock symbol e.g. "AAPL"

    Returns:
        dict: Flattened quote data, or empty dict on failure
    """
    try:
        client = get_client()
        response = client.get_quote(ticker)
        data = response.json()

        ticker_block = data.get(ticker, {})
        quote        = ticker_block.get("quote", {})
        fundamental  = ticker_block.get("fundamental", {})
        reference    = ticker_block.get("reference", {})

        # ANALYST NOTE: assetMainType lives at the top of the ticker block,
        # not inside any sub-block. Examples: "EQUITY" (AAPL),
        # "COLLECTIVE_INVESTMENT" (SPY), "MUTUAL_FUND" (some funds).
        #asset_main_type = ticker_block.get("assetMainType", "")
        #is_etf = asset_main_type in ETF_ASSET_TYPES

        asset_main_type = ticker_block.get("assetMainType", "")
        asset_sub_type  = ticker_block.get("assetSubType", "")
        is_etf = asset_sub_type in ETF_SUB_TYPES

        # For ETFs, suppress unreliable fundamental fields.
        # We pass None instead of the raw value so downstream code can
        # decide what to display.
        pe_ratio = None if is_etf else fundamental.get("peRatio", 0)
        eps      = None if is_etf else fundamental.get("eps", 0)

        return {
            "ticker"            : ticker,
            "asset_type"        : asset_main_type,
            "asset_sub_type"    : asset_sub_type,
            "is_etf"            : is_etf,
            "companyName"       : reference.get("description", ""),
            "lastPrice"         : quote.get("lastPrice", 0),
            "bidPrice"          : quote.get("bidPrice", 0),
            "askPrice"          : quote.get("askPrice", 0),
            "openPrice"         : quote.get("openPrice", 0),
            "closePrice"        : quote.get("closePrice", 0),
            "highPrice"         : quote.get("highPrice", 0),
            "lowPrice"          : quote.get("lowPrice", 0),
            "netChange"         : quote.get("netChange", 0),
            "netPercentChange"  : quote.get("netPercentChange", 0),
            "fiftyTwoWeekHigh"  : quote.get("52WeekHigh", 0),
            "fiftyTwoWeekLow"   : quote.get("52WeekLow", 0),
            "totalVolume"       : quote.get("totalVolume", 0),
            "avg10DayVolume"    : fundamental.get("avg10DaysVolume", 0),
            "peRatio"           : pe_ratio,    # None for ETFs
            "eps"               : eps,         # None for ETFs
            "divYield"          : fundamental.get("divYield", 0),
            "exchange"          : reference.get("exchangeName", ""),
        }

    except Exception as e:
        print(f"[schwab_client] Error fetching quote for {ticker}: {e}")
        return {}


# =============================================================================
# ACCOUNT DATA
# =============================================================================

def get_account_numbers() -> list:
    """Retrieve all account numbers linked to the authenticated user."""
    try:
        client = get_client()
        response = client.get_account_numbers()
        return response.json()
    except Exception as e:
        print(f"[schwab_client] Error fetching account numbers: {e}")
        return []


def get_positions(account_hash: str) -> dict:
    """Fetch current positions and balances for a given account hash."""
    try:
        client = get_client()
        response = client.get_account(
            account_hash,
            fields=client.Account.Fields.POSITIONS
        )
        return response.json()
    except Exception as e:
        print(f"[schwab_client] Error fetching positions: {e}")
        return {}


# =============================================================================
# PORTFOLIO HELPERS
# =============================================================================

def extract_held_tickers(positions: list) -> list:
    """
    Extract a clean list of ticker symbols from a Schwab positions list.

    ANALYST NOTE:
        Filters out cash equivalents and money market funds since those
        don't behave like equities and shouldn't be analyzed by Claude.
    """
    CASH_EQUIVALENTS = {
        "SWVXX", "SNAXX", "SNSXX", "SWGXX", "MMDA1",
    }

    tickers = []
    for position in positions:
        instrument = position.get("instrument", {})
        symbol     = instrument.get("symbol", "")
        asset_type = instrument.get("assetType", "")

        if not symbol:
            continue
        if symbol in CASH_EQUIVALENTS:
            continue
        # ANALYST NOTE: At this layer we accept both equities AND ETFs/funds.
        # The is_etf flag is set later in get_quote() and used to suppress
        # P/E in the Claude prompt — not to filter what gets analyzed.
        if asset_type not in ("EQUITY", "COLLECTIVE_INVESTMENT", "ETF"):
            continue

        tickers.append(symbol)

    return tickers


def get_position_detail(positions: list, ticker: str) -> dict:
    """Return the position detail for a specific ticker if held."""
    for position in positions:
        instrument = position.get("instrument", {})
        if instrument.get("symbol") == ticker:
            return {
                "is_held"            : True,
                "quantity"           : position.get("longQuantity", 0),
                "average_price"      : position.get("averagePrice", 0),
                "market_value"       : position.get("marketValue", 0),
                "current_day_pnl"    : position.get("currentDayProfitLoss", 0),
                "current_day_pnl_pct": position.get("currentDayProfitLossPercentage", 0),
                "long_open_pnl"      : position.get("longOpenProfitLoss", 0),
            }

    return {"is_held": False}


def get_account_portfolio(account_number: str, account_hash: str) -> dict:
    """Get a single account's portfolio summary including label."""
    account_data = get_positions(account_hash)
    label = ACCOUNT_LABELS.get(account_number, f"Account {account_number}")

    try:
        balances  = account_data["securitiesAccount"]["currentBalances"]
        positions = account_data["securitiesAccount"].get("positions", [])

        return {
            "account_number"  : account_number,
            "account_label"   : label,
            "account_hash"    : account_hash,
            "cash_available"  : balances.get("cashAvailableForTrading",
                                     balances.get("cashBalance", 0)),
            "portfolio_value" : balances.get("liquidationValue", 0),
            "positions"       : positions,
            "held_tickers"    : extract_held_tickers(positions),
        }

    except KeyError as e:
        print(f"[schwab_client] Unexpected account data structure for "
              f"{label}: {e}")
        return {}


def get_all_portfolios() -> list:
    """Fetch portfolio summaries for all active accounts."""
    accounts = get_account_numbers()
    if not accounts:
        print("[schwab_client] No accounts found.")
        return []

    portfolios = []
    for account in accounts:
        account_number = account.get("accountNumber", "")
        account_hash   = account.get("hashValue", "")

        if ACTIVE_ACCOUNTS and account_number not in ACTIVE_ACCOUNTS:
            continue

        portfolio = get_account_portfolio(account_number, account_hash)
        if portfolio:
            portfolios.append(portfolio)

    return portfolios
