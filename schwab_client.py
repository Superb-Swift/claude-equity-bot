# =============================================================================
# schwab_client.py
# =============================================================================
# PURPOSE:
#   Handles all communication with the Charles Schwab Trader API.
#   Now supports multiple accounts with friendly labels.
#
# ANALYST NOTE:
#   This file is the "data layer" of the bot. It knows nothing about Claude
#   or trading decisions — it only knows how to talk to Schwab and return
#   clean data. Keeping concerns separated like this makes the code easier
#   to debug and maintain.
#
# DEPENDENCIES:
#   pip install schwab-py python-dotenv
#
# USAGE:
#   from schwab_client import get_quote, get_all_portfolios
# =============================================================================

import os
import schwab
from dotenv import load_dotenv

load_dotenv()

# Pull credentials from .env
APP_KEY      = os.getenv("SCHWAB_APP_KEY")
APP_SECRET   = os.getenv("SCHWAB_APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "https://127.0.0.1:8182")
TOKEN_PATH   = os.getenv("TOKEN_PATH", "token.json")


# =============================================================================
# ACCOUNT LABELS
# =============================================================================
# ANALYST NOTE: Map your raw account numbers to friendly labels here.
# The bot uses these labels in logs and portfolio overviews so you always
# know which account is being analyzed at a glance.
#
# To add or rename an account: just edit this dict. Match by accountNumber
# exactly as Schwab returns it (no dashes, no spaces).

ACCOUNT_LABELS = {
    "52357894": "Roth IRA",
    "87343846": "Individual",
}

# ANALYST NOTE: Set which accounts to actively analyze. Comment out any
# account number you want to skip. The bot will silently ignore accounts
# not listed here. Leave empty list [] to analyze ALL linked accounts.
ACTIVE_ACCOUNTS = [
    "52357894",   # Roth IRA
    "87343846",   # Individual
]


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_client():
    """
    Authenticate with Schwab and return an authenticated client object.
    """
    if not APP_KEY or not APP_SECRET:
        raise ValueError(
            "SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in your .env file."
        )

    client = schwab.auth.easy_client(
        api_key=APP_KEY,
        app_secret=APP_SECRET,
        callback_url=CALLBACK_URL,
        token_path=TOKEN_PATH
    )

    return client


# =============================================================================
# MARKET DATA
# =============================================================================

def get_quote(ticker: str) -> dict:
    """
    Fetch a real-time quote for a single ticker symbol.

    ANALYST NOTE:
        Schwab returns a deeply nested structure with separate blocks for
        quote, fundamental, and reference data. We flatten the most useful
        fields into a single dict for easier downstream use.

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

        return {
            "ticker"            : ticker,
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
            "peRatio"           : fundamental.get("peRatio", 0),
            "eps"               : fundamental.get("eps", 0),
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
    """
    Retrieve all account numbers linked to the authenticated user.
    """
    try:
        client = get_client()
        response = client.get_account_numbers()
        return response.json()
    except Exception as e:
        print(f"[schwab_client] Error fetching account numbers: {e}")
        return []


def get_positions(account_hash: str) -> dict:
    """
    Fetch current positions and balances for a given account hash.
    """
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
        "SWVXX",   # Schwab Value Advantage Money Fund
        "SNAXX",   # Schwab Government Money Fund
        "SNSXX",   # Schwab US Treasury Money Fund
        "SWGXX",   # Schwab Government Money Fund Investor
        "MMDA1",   # Schwab Bank Deposit
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
        if asset_type not in ("EQUITY", "COLLECTIVE_INVESTMENT", "ETF"):
            continue

        tickers.append(symbol)

    return tickers


def get_position_detail(positions: list, ticker: str) -> dict:
    """
    Return the position detail for a specific ticker if held.

    Args:
        positions (list): Raw positions array from Schwab
        ticker    (str):  Ticker symbol to look up

    Returns:
        dict: Position detail or {"is_held": False}
    """
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
    """
    Get a single account's portfolio summary including label.

    Args:
        account_number (str): Raw account number from Schwab
        account_hash   (str): Encrypted hash for API calls

    Returns:
        dict: {
            "account_number"  : str,
            "account_label"   : str,
            "account_hash"    : str,
            "cash_available"  : float,
            "portfolio_value" : float,
            "positions"       : list,
            "held_tickers"    : list,
        }
    """
    account_data = get_positions(account_hash)
    label = ACCOUNT_LABELS.get(account_number, f"Account {account_number}")

    try:
        balances  = account_data["securitiesAccount"]["currentBalances"]
        positions = account_data["securitiesAccount"].get("positions", [])

        return {
            "account_number"  : account_number,
            "account_label"   : label,
            "account_hash"    : account_hash,
            "cash_available"  : balances.get("cashAvailableForTrading", 0),
            "portfolio_value" : balances.get("liquidationValue", 0),
            "positions"       : positions,
            "held_tickers"    : extract_held_tickers(positions),
        }

    except KeyError as e:
        print(f"[schwab_client] Unexpected account data structure for "
              f"{label}: {e}")
        return {}


def get_all_portfolios() -> list:
    """
    Fetch portfolio summaries for all active accounts.

    ANALYST NOTE:
        Iterates through every account returned by Schwab, filters to only
        those in ACTIVE_ACCOUNTS (or all if ACTIVE_ACCOUNTS is empty), and
        returns a list of portfolio dicts — one per account.

    Returns:
        list: List of account portfolio dicts, each with friendly label.
    """
    accounts = get_account_numbers()
    if not accounts:
        print("[schwab_client] No accounts found.")
        return []

    portfolios = []
    for account in accounts:
        account_number = account.get("accountNumber", "")
        account_hash   = account.get("hashValue", "")

        # Skip accounts not in active list (if list is populated)
        if ACTIVE_ACCOUNTS and account_number not in ACTIVE_ACCOUNTS:
            continue

        portfolio = get_account_portfolio(account_number, account_hash)
        if portfolio:
            portfolios.append(portfolio)

    return portfolios
