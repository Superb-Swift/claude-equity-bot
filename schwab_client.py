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
from datetime import datetime, timezone
from dotenv import load_dotenv

# H1 WINDOW FIX (proposed 2026-08-26): Schwab stamps daily candles in a
# zone east of this machine. Converting with local-time fromtimestamp()
# dated every candle one day early, which let today's in-progress candle
# through the completed-sessions filter. Both sides of the comparison are
# now explicit: candle dates come from UTC, 'today' comes from Eastern.
try:
    from zoneinfo import ZoneInfo
    _MARKET_TZ = ZoneInfo("America/New_York")
except Exception:                      # pragma: no cover
    _MARKET_TZ = timezone.utc

load_dotenv()

APP_KEY      = os.getenv("SCHWAB_APP_KEY")
APP_SECRET   = os.getenv("SCHWAB_APP_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "https://1XX.0.0.1:XXXX")
TOKEN_PATH   = os.getenv("TOKEN_PATH", "token.json")


# =============================================================================
# ACCOUNT LABELS
# =============================================================================

# ANALYST NOTE: Account numbers are loaded from .env so they never
# leak into source control. The .env file is gitignored.
ROTH_ACCOUNT       = os.getenv("ROTH_ACCOUNT_NUMBER", "")
INDIVIDUAL_ACCOUNT = os.getenv("INDIVIDUAL_ACCOUNT_NUMBER", "")

ACCOUNT_LABELS = {
    ROTH_ACCOUNT       : "Roth IRA",
    INDIVIDUAL_ACCOUNT : "Individual",
}

ACTIVE_ACCOUNTS = [
    ROTH_ACCOUNT,
    INDIVIDUAL_ACCOUNT,
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
        #
        # ANALYST NOTE (2026-08-17): the `, 0` defaults were REMOVED. They made
        #   a MISSING fundamental indistinguishable from a genuine zero, so a
        #   name Schwab reports nothing for was rendered into the prompt as
        #   "EPS: $0" and the model reasoned from it -- CBRS's own signal text
        #   reads "P/E near 480 on near-zero EPS". That is the same
        #   missing-versus-wrong distinction `fin=degraded` exists for on the
        #   EDGAR side (DP-3C-t(b)), arriving in a different file.
        #   Absent now yields None; a genuine 0.0 still yields 0.0.
        #   claude_signal.py L157-163 already renders None as "N/A" for BOTH
        #   fields, so no downstream change is required and none was made.
        #   peRatio is fixed alongside eps because it is the same defect on the
        #   adjacent line and is equally None-safe downstream; leaving it would
        #   half-fix a single fault.
        #   NOT CHANGED: `divYield` carries the same `, 0` default on L154 below
        #   and on L153/L159 of claude_signal.py, but it is formatted with
        #   "{:.2f}%" which raises TypeError on None. Fixing it needs a
        #   formatter change too, so it is recorded rather than half-done.
        #   THIS EDIT CHANGES WHAT THE MODEL RECEIVES and lands mid-E4, so it
        #   needs a dated decision-point entry. quote_dump.py must be re-run to
        #   learn which names actually move: the existing dump was captured
        #   THROUGH the defaulting code and has already lost that information.
        pe_ratio = None if is_etf else fundamental.get("peRatio")
        eps      = None if is_etf else fundamental.get("eps")

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
# PRICE HISTORY  (H1 — prior-5-day price input)
# =============================================================================

def get_price_history(ticker: str, days: int = 5) -> list:
    """
    Fetch the prior `days` COMPLETED daily closes for a ticker.

    ANALYST NOTE (H1):
        Phase 2's strongest finding was a 3-5 day confidence update lag —
        the model's confidence trailed price moves by several sessions
        (the WMT trace: held 62% through three ~-11% losses, then caught
        up only as the losses shrank). H1 feeds the recent closing path
        into the prompt so the model can react to the move now, not later.

        Returns the most recent `days` sessions that have ALREADY closed
        (today's in-progress candle is excluded), oldest-first:
            [{"date": "2026-06-05", "close": 211.97}, ...]
        Returns [] on failure; the prompt builder degrades gracefully.
    """
    try:
        client = get_client()
        # schwab-py daily-candle convenience method (returns ~1y of candles).
        response = client.get_price_history_every_day(ticker)
        candles = response.json().get("candles", [])

        today = datetime.now(_MARKET_TZ).date()
        closes = []
        for c in candles:
            ts = c.get("datetime")
            close = c.get("close")
            if ts is None or close is None:
                continue
            # Schwab candle 'datetime' is epoch milliseconds, stamped in a
            # market-side zone. Date it in UTC and compare against the
            # market's own 'today' -- never the machine's local date.
            cdate = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
            if cdate < today:                 # completed sessions only
                closes.append({"date": cdate.isoformat(), "close": close})

        # The docstring promises the in-progress candle is excluded. Say so
        # out loud rather than trusting it: this is the exact condition that
        # silently held from at least 2026-08-13 to 2026-08-26.
        if closes and closes[-1]["date"] >= today.isoformat():
            print(f"[schwab_client] WARNING: newest candle for {ticker} is "
                  f"{closes[-1]['date']} against market today {today} -- "
                  f"an in-progress session reached the H1 window.")

        return closes[-days:]

    except Exception as e:
        print(f"[schwab_client] Error fetching price history for {ticker}: {e}")
        return []


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
