# =============================================================================
# blend_providers.py  —  WS1 blend components C2 (sector) + C3 (regime)
# =============================================================================
# Numeric blend providers (mode="blend"): each returns a score in [-1,+1] that
# the blend engine uses to confirm/discount the base signal's conviction.
# Registered on import — main.py does `import blend_providers` to activate them.
#
#   C2 sector-backbone : trailing trend of the ticker's sector ETF (sector_map)
#   C3 cross-asset-regime : SPY vs GLD trend — market-wide risk-on/off (one
#                           value/run, shared by all tickers)
#
# Trend scopes are disjoint from D1 (which reads the TICKER's own trailing
# return): C2 = sector, C3 = market, D1 = name -> no double-counting.
# Windows/scales are the pre-registered defaults (DP-W-a/-b); change here.
# =============================================================================

from context_providers import Provider, register
from sector_map import sector_reference, is_mapped

N_SECTOR      = 20      # trading-day sector-trend window
SECTOR_SCALE  = 0.10    # a 10% ETF move over the window = full +/-1.0
N_REGIME      = 20      # trading-day regime window
REGIME_SCALE  = 0.10    # a 10% SPY-minus-GLD gap = full +/-1.0


def _ret(closes):
    """Trailing return over a list of closes (oldest-first). None if unusable."""
    if not closes or len(closes) < 2 or not closes[0]:
        return None
    return closes[-1] / closes[0] - 1.0


def _clip(x):
    return max(-1.0, min(1.0, x))


def sector_score(ticker, caches):
    """C2 — [-1,+1] from the ticker's sector-ETF trailing trend."""
    ref = sector_reference(ticker)
    meta = {"ref": ref}
    if ref is None:                                  # broad / commodity / unknown
        if not is_mapped(ticker):
            meta["unmapped"] = True                  # caller may WARN to map it
        return 0.0, meta
    ret = _ret((caches.get("sector") or {}).get(ref))
    if ret is None:
        meta["note"] = "no data"
        return 0.0, meta
    meta["ret"] = round(ret, 4)
    return _clip(ret / SECTOR_SCALE), meta


def regime_score(ticker, caches):
    """C3 — [-1,+1] risk-on/off = SPY trend minus GLD trend (same for all tickers)."""
    reg = caches.get("regime") or {}
    spy, gld = _ret(reg.get("SPY")), _ret(reg.get("GLD"))
    if spy is None or gld is None:
        return 0.0, {"note": "no data"}
    return _clip((spy - gld) / REGIME_SCALE), {"spy": round(spy, 4), "gld": round(gld, 4)}


register(Provider("sector", "blend", sector_score))
register(Provider("regime", "blend", regime_score))
