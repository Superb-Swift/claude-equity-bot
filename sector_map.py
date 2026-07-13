# =============================================================================
# sector_map.py  —  WS1 sector-backbone reference (component C2)
# =============================================================================
# Maps each watchlist ticker to the SPDR sector ETF whose trailing trend is
# its "sector backbone." The blend's C2 component fetches that ETF's trend
# and uses it to confirm/discount the base signal's conviction.
#
# CATEGORY POLICY (see WS1_Implementation_Spec.md §C2):
#   single stock   -> its SPDR sector ETF
#   sector ETF     -> itself (its own trend IS the backbone)
#   broad index    -> None (neutral for C2; C3 handles market-wide regime)
#   commodity ETF  -> None (neutral for C2; WS3 commodity context is the analog)
#   thematic ETF   -> dominant sector if unambiguous, else None
#
# UNKNOWN tickers (held set is dynamic from Schwab) -> None + a WARN, so the
# blend degrades to base-conviction for that name until it's mapped here.
#
# Ticker resolutions verified 2026-07-10:
#   CBRS = Cerebras Systems (AI chips) -> XLK
#   SND  = Smart Sand (frac sand / oilfield services) -> XLE
#   AG   = First Majestic Silver (silver miner) -> XLB
#   AIQ  = Global X Artificial Intelligence & Technology ETF -> XLK (reviewable)
# =============================================================================

SPDR_SECTORS = {"XLK", "XLF", "XLE", "XLI", "XLB", "XLP",
                "XLY", "XLV", "XLU", "XLRE", "XLC"}

# --- single stocks -> sector ETF ---
STOCK_SECTOR = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "CBRS": "XLK",  # Technology / semis
    "JPM":  "XLF",                                               # Financials
    "GM":   "XLY", "NKE":  "XLY",                                # Consumer Discretionary
    "WMT":  "XLP", "PM":   "XLP",                                # Consumer Staples
    "RTX":  "XLI", "PWR":  "XLI",                                # Industrials
    "DOW":  "XLB", "NTR":  "XLB", "AG": "XLB",                   # Materials
    "FTI":  "XLE", "SND":  "XLE",                                # Energy (oilfield svcs)
}

# --- sector ETFs -> self (extend as more sector ETFs enter the watchlist) ---
SECTOR_ETF_SELF = {"XLU"}

# --- thematic ETFs -> dominant sector (reviewable; DP-W1 note) ---
THEMATIC_SECTOR = {"AIQ": "XLK"}   # Global X AI & Technology -> tech-dominant

# --- broad indices + commodities -> neutral for C2 ---
NEUTRAL_C2 = {
    "SPY", "QQQ", "VTI", "SCHD",   # broad / dividend baskets -> C3's market regime covers these
    "GLD", "CORN",                 # commodities -> WS3 commodity context is the sector analog
}


def sector_reference(ticker: str):
    """ETF ticker to fetch for C2, or None if the ticker is C2-neutral."""
    t = (ticker or "").upper()
    if t in STOCK_SECTOR:     return STOCK_SECTOR[t]
    if t in SECTOR_ETF_SELF:  return t
    if t in THEMATIC_SECTOR:  return THEMATIC_SECTOR[t]
    return None                # neutral (broad/commodity) OR unknown (caller WARNs)


def is_mapped(ticker: str) -> bool:
    """True if the ticker has an explicit policy (any category). False = unknown."""
    t = (ticker or "").upper()
    return (t in STOCK_SECTOR or t in SECTOR_ETF_SELF
            or t in THEMATIC_SECTOR or t in NEUTRAL_C2)
