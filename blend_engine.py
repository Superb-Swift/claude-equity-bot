# =============================================================================
# blend_engine.py  —  WS1 triple-blend combination rule
# =============================================================================
# Turns the model's RAW confidence into a BLENDED confidence using the blend
# providers' scores. Direction integrity: the base owns BUY/HOLD/SELL; the
# overlays only MODULATE conviction, bounded. Design note §2; DP-W2 weights.
#
#   agree(dir, s) = +1 if the overlay confirms the base direction,
#                   -1 if it opposes, 0 if flat / HOLD
#   adj           = sum over providers of  weight * agree * |score|
#   conf_blend    = clip( conf_raw * (1 + adj), FLOOR, 100 )
#
# T3: references direction-agreement x overlay-magnitude and a CONTINUOUS
# confidence — never confidence bands or their ordering. Compliant.
#
# WEIGHTS is the pre-registered, FIXED weight map (ruled: sector/regime =
# 0.15/0.15). Not fitted — a weight tuned to 24 tickers would repeat the Q1
# overfit. Change only via a dated worksheet entry. Providers without a weight
# here contribute 0 (safe default for any future blend provider).
# =============================================================================

WEIGHTS = {"sector": 0.15, "regime": 0.15}   # DP-W2 (fixed, pre-registered)
FLOOR   = 35                                  # matches D1; clear of the 0-conf error code


def _agree(direction: int, score: float) -> int:
    if abs(score) < 1e-9:
        return 0
    return 1 if (score > 0) == (direction > 0) else -1


def blend_confidence(signal: dict, scores: dict):
    """conf_raw -> conf_blend. Direction unchanged. Returns (conf_blend, meta)."""
    raw = signal.get("confidence_raw", signal.get("confidence"))
    if not isinstance(raw, (int, float)) or raw <= 0:      # parse-error -> untouched
        return raw, {"active": False, "reason": "no valid confidence", "blend": raw}
    raw = int(raw)

    direction = {"BUY": 1, "SELL": -1}.get(str(signal.get("signal", "")).upper(), 0)
    if direction == 0:                                     # HOLD unchanged (DP-W3)
        return raw, {"active": False, "dir": 0, "adj": 0.0,
                     "scores": {k: round(v, 3) for k, v in scores.items()}, "blend": raw}

    adj = sum(WEIGHTS.get(name, 0.0) * _agree(direction, s) * abs(s)
              for name, s in scores.items())
    blend = max(FLOOR, min(100, int(round(raw * (1 + adj)))))
    return blend, {"active": adj != 0, "dir": direction, "adj": round(adj, 4),
                   "scores": {k: round(v, 3) for k, v in scores.items()},
                   "raw": raw, "blend": blend}
