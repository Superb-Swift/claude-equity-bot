# =============================================================================
# schwab_client.py
# =============================================================================
# PURPOSE:
#   Handles all communication with the Charles Schwab Trader API.
#   Responsibilities:
#     - Authentication via OAuth 2.0
#     - Fetching real-time quotes
#     - Fetching account positions and balances
#     - Fetching price history for a ticker
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
#   from schwab_client import get_client, get_quote, get_positions
# =============================================================================

import os
import schwab
from dotenv import load_dotenv

# Load environment variables from .env file
# ANALYST NOTE: load_dotenv() reads your .env file and makes each line
# available via os.getenv(). This keeps secrets out of your source code.
load_dotenv()

# Pull credentials from .env
APP_KEY     = os.getenv("SCHWAB_APP_KEY")
APP_SECRET  = os.getenv("SCHWAB_APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "https://127.0.0.1")
TOKEN_PATH  = os.getenv("TOKEN_PATH", "token.json")


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_client():
    """
    Authenticate with Schwab and return an authenticated client object.

    ANALYST NOTE:
        easy_client() handles the full OAuth 2.0 flow automatically:
        - First run: opens browser, you log in, paste the redirect URL
        - Subsequent runs: silently refreshes token from token.json
        - token.json stores your access + refresh tokens locally
        - Access tokens expire every 30 minutes — schwab-py auto-refreshes them

    Returns:
        schwab.client.Client: authenticated Schwab API client

    Raises:
        ValueError: if APP_KEY or APP_SECRET are missing from .env
    """
    if not APP_KEY or not APP_SECRET:
        raise ValueError(
            "SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in your .env file. "
            "Get these from developer.schwab.com after your app is approved."
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
        Returns key fields like lastPrice, bidPrice, askPrice, netChange,
        netPercentChangeInDouble, totalVolume. These feed directly into
        Claude's signal generation prompt.

    Args:
        ticker (str): Stock symbol e.g. "AAPL", "MSFT", "TSLA"

    Returns:
        dict: Quote data for the ticker, or empty dict on failure
    """
    try:
        client = get_client()
        response = client.get_quote(ticker)
        data = response.json()

        # ANALYST NOTE: Schwab wraps quote data in the ticker key
        # e.g. {"AAPL": {"lastPrice": 189.5, "bidPrice": ...}}
        return data.get(ticker, {})

    except Exception as e:
        print(f"[schwab_client] Error fetching quote for {ticker}: {e}")
        return {}


def get_price_history(ticker: str, period_type: str = "month",
                      period: int = 1, frequency_type: str = "daily",
                      frequency: int = 1) -> dict:
    """
    Fetch historical price data for a ticker.

    ANALYST NOTE:
        Useful for trend analysis. Default returns 1 month of daily candles.
        Can be adjusted for intraday data by changing frequency_type to
        "minute" and frequency to 5, 15, 30, etc.

    Args:
        ticker      (str): Stock symbol
        period_type (str): "day", "month", "year", "ytd"
        period      (int): Number of periods
        frequency_type (str): "minute", "daily", "weekly", "monthly"
        frequency   (int): Frequency interval

    Returns:
        dict: OHLCV candle data
    """
    try:
        client = get_client()
        response = client.get_price_history(
            ticker,
            period_type=client.PriceHistory.PeriodType[period_type.upper()],
            period=client.PriceHistory.Period(period),
            frequency_type=client.PriceHistory.FrequencyType[frequency_type.upper()],
            frequency=client.PriceHistory.Frequency(frequency)
        )
        return response.json()

    except Exception as e:
        print(f"[schwab_client] Error fetching price history for {ticker}: {e}")
        return {}


# =============================================================================
# ACCOUNT DATA
# =============================================================================

def get_account_numbers() -> list:
    """
    Retrieve all account numbers linked to the authenticated user.

    ANALYST NOTE:
        Schwab returns an encrypted account hash (hashValue) rather than
        the raw account number for security. Use hashValue for all
        subsequent account-specific API calls.

    Returns:
        list: List of dicts with 'accountNumber' and 'hashValue'
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
    Fetch current positions and balances for a given account.

    ANALYST NOTE:
        Returns full position detail including symbol, quantity, market value,
        average price, and unrealized P&L. This data feeds the risk engine
        to check position limits before Claude's signals trigger any action.

    Args:
        account_hash (str): Encrypted account hash from get_account_numbers()

    Returns:
        dict: Account positions and balance information
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
# CONVENIENCE SUMMARY
# =============================================================================

def get_portfolio_summary() -> dict:
    """
    High-level summary: account hash, cash balance, and current positions.

    ANALYST NOTE:
        This is the primary function called by main.py at the start of each
        run. It gives the risk engine everything it needs to evaluate whether
        a new signal should proceed to execution.

    Returns:
        dict: {
            "account_hash": str,
            "cash_available": float,
            "portfolio_value": float,
            "positions": list
        }
    """
    accounts = get_account_numbers()

    if not accounts:
        print("[schwab_client] No accounts found.")
        return {}

    # ANALYST NOTE: Use the first linked account by default.
    # If you have multiple Schwab accounts, you may want to add logic
    # to select a specific one by account number.
    account_hash = accounts[0]["hashValue"]
    account_data = get_positions(account_hash)

    try:
        balances   = account_data["securitiesAccount"]["currentBalances"]
        positions  = account_data["securitiesAccount"].get("positions", [])

        return {
            "account_hash"    : account_hash,
            "cash_available"  : balances.get("cashAvailableForTrading", 0),
            "portfolio_value" : balances.get("liquidationValue", 0),
            "positions"       : positions
        }

    except KeyError as e:
        print(f"[schwab_client] Unexpected account data structure: {e}")
        return {}
