# =============================================================================
# risk_engine.py
# =============================================================================
# PURPOSE:
#   Evaluates Claude's trading signals against hardcoded risk rules before
#   any order is placed. Acts as the last line of defense between signal
#   generation and execution.
#
# ANALYST NOTE:
#   This is the most important file in the entire bot. Claude is a language
#   model — it can hallucinate, misread data, or generate overconfident
#   signals. The risk engine is deterministic and rule-based, which means
#   it is predictable and auditable in a way that Claude is not.
#
#   RULE: Claude suggests. The risk engine decides. Humans approve.
#
#   Never allow Claude to modify or override these rules. The risk parameters
#   below should only be changed deliberately and with full understanding
#   of the implications.
#
# DEPENDENCIES:
#   None — this file is intentionally dependency-free for reliability.
#
# USAGE:
#   from risk_engine import evaluate_signal, RiskConfig
# =============================================================================


# =============================================================================
# RISK CONFIGURATION
# =============================================================================

class RiskConfig:
    """
    Central risk parameter store.

    ANALYST NOTE:
        All risk rules live here in one place so they are easy to audit,
        review, and adjust. Change these values deliberately — each one
        has real financial consequences.

        Start conservative. You can always loosen rules after live testing
        proves the system is behaving as expected. You cannot undo a loss.
    """

    # --- Signal Quality Thresholds ---
    # ANALYST NOTE: Minimum confidence score Claude must report before
    # the risk engine will approve a BUY or SELL signal.
    # HOLD signals are always approved regardless of confidence.
    MIN_CONFIDENCE_BUY  : int   = 70   # Require 70%+ confidence to buy
    MIN_CONFIDENCE_SELL : int   = 65   # Slightly lower bar to exit a position

    # --- Position Sizing ---
    # ANALYST NOTE: Maximum percentage of total portfolio value in any
    # single position. At $10,000 portfolio, 5% = $500 max per position.
    # This prevents catastrophic loss if one position goes to zero.
    MAX_POSITION_PCT    : float = 0.05  # 5% of portfolio per position

    # --- Portfolio Concentration ---
    # ANALYST NOTE: Maximum number of open positions at any time.
    # Fewer positions = more concentration risk but easier to monitor.
    # More positions = more diversification but harder to track.
    MAX_OPEN_POSITIONS  : int   = 8

    # --- Loss Limits ---
    # ANALYST NOTE: Daily loss limit as a percentage of portfolio value.
    # If the portfolio drops by this amount in a single day, the bot
    # stops generating new BUY signals for the rest of the day.
    DAILY_LOSS_LIMIT_PCT: float = 0.02  # Stop buying at -2% day

    # --- Duplicate Position Guard ---
    # ANALYST NOTE: Prevents the bot from adding to an existing position.
    # In Phase 2-4, we only take new positions, not add to existing ones.
    ALLOW_POSITION_ADD  : bool  = False

    # --- Human Approval Gate ---
    # ANALYST NOTE: When True, the bot logs the signal and recommended
    # action but does NOT execute the order. A human must review and
    # manually approve. Set to False only after extensive paper testing.
    REQUIRE_HUMAN_APPROVAL: bool = True

    # --- Banned Tickers ---
    # ANALYST NOTE: Tickers the bot will never trade regardless of signal.
    # Add highly volatile, illiquid, or personally conflicted tickers here.
    BANNED_TICKERS      : list  = [
        # Examples — customize as needed:
        # "GME",   # High short interest / meme stock
        # "BBBY",  # Bankruptcy risk
    ]

    # --- Minimum Data Quality ---
    # ANALYST NOTE: Claude rates the quality of available data in each signal.
    # Reject signals where data quality is too low to act on responsibly.
    MIN_DATA_QUALITY    : str   = "MEDIUM"  # Reject "LOW" quality signals


# =============================================================================
# RISK EVALUATION
# =============================================================================

def evaluate_signal(signal: dict, portfolio: dict) -> tuple[bool, str]:
    """
    Evaluate a Claude signal against all risk rules.

    ANALYST NOTE:
        This function runs every signal through a checklist of rules in order
        of severity. It returns on the FIRST failed rule — if a signal fails
        any check, it is rejected and the reason is logged.

        The function returns a tuple so callers always get both a decision
        AND a reason — never a silent rejection.

    Args:
        signal    (dict): Signal dict from claude_signal.get_signal()
        portfolio (dict): Portfolio summary from schwab_client.get_portfolio_summary()

    Returns:
        tuple[bool, str]: (approved, reason)
            - (True,  "Passed all risk checks") if approved
            - (False, "Reason for rejection")   if rejected
    """
    cfg    = RiskConfig()
    ticker = signal.get("ticker", "UNKNOWN")
    sig    = signal.get("signal", "HOLD")
    conf   = signal.get("confidence", 0)
    dq     = signal.get("data_quality", "LOW")

    # ------------------------------------------------------------------
    # CHECK 1: Error signals are always rejected
    # ANALYST NOTE: If Claude returned an error or parse failure, the
    # signal dict will contain an 'error' key. Never act on error signals.
    # ------------------------------------------------------------------
    if "error" in signal:
        return False, f"Signal contains error: {signal['error']}"

    # ------------------------------------------------------------------
    # CHECK 2: HOLD signals are always approved (no action required)
    # ANALYST NOTE: A HOLD signal means "do nothing" — it can never
    # cause harm, so we pass it through immediately.
    # ------------------------------------------------------------------
    if sig == "HOLD":
        return True, "HOLD signal — no action required."

    # ------------------------------------------------------------------
    # CHECK 3: Banned ticker check
    # ------------------------------------------------------------------
    if ticker in cfg.BANNED_TICKERS:
        return False, f"{ticker} is on the banned tickers list."

    # ------------------------------------------------------------------
    # CHECK 4: Data quality check
    # ANALYST NOTE: We map quality strings to numeric scores so we can
    # compare them programmatically.
    # ------------------------------------------------------------------
    quality_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    signal_quality  = quality_map.get(dq, 0)
    required_quality = quality_map.get(cfg.MIN_DATA_QUALITY, 2)

    if signal_quality < required_quality:
        return False, (
            f"Data quality too low: signal is '{dq}', "
            f"minimum required is '{cfg.MIN_DATA_QUALITY}'."
        )

    # ------------------------------------------------------------------
    # CHECK 5: Confidence threshold
    # ------------------------------------------------------------------
    if sig == "BUY" and conf < cfg.MIN_CONFIDENCE_BUY:
        return False, (
            f"BUY confidence too low: {conf}% < "
            f"required {cfg.MIN_CONFIDENCE_BUY}%."
        )

    if sig == "SELL" and conf < cfg.MIN_CONFIDENCE_SELL:
        return False, (
            f"SELL confidence too low: {conf}% < "
            f"required {cfg.MIN_CONFIDENCE_SELL}%."
        )

    # ------------------------------------------------------------------
    # CHECK 6: Portfolio concentration — too many open positions
    # ------------------------------------------------------------------
    open_positions = portfolio.get("positions", [])
    if len(open_positions) >= cfg.MAX_OPEN_POSITIONS:
        return False, (
            f"Too many open positions: {len(open_positions)} >= "
            f"max {cfg.MAX_OPEN_POSITIONS}."
        )

    # ------------------------------------------------------------------
    # CHECK 7: Duplicate position guard
    # ANALYST NOTE: Check if we already hold this ticker.
    # ------------------------------------------------------------------
    if sig == "BUY" and not cfg.ALLOW_POSITION_ADD:
        held_tickers = [
            p.get("instrument", {}).get("symbol", "")
            for p in open_positions
        ]
        if ticker in held_tickers:
            return False, (
                f"Already holding {ticker} and ALLOW_POSITION_ADD is False."
            )

    # ------------------------------------------------------------------
    # CHECK 8: Daily loss limit
    # ANALYST NOTE: If the portfolio has lost more than DAILY_LOSS_LIMIT_PCT
    # today, block new BUY signals. SELL signals still allowed (to cut losses).
    # ------------------------------------------------------------------
    if sig == "BUY":
        portfolio_value = portfolio.get("portfolio_value", 0)
        # ANALYST NOTE: In a full implementation, compare portfolio_value
        # to start-of-day value stored in a log file. For now we skip
        # this check if we can't calculate the daily change.
        # TODO: Implement daily P&L tracking in Phase 4.
        pass

    # ------------------------------------------------------------------
    # CHECK 9: Human approval gate
    # ANALYST NOTE: If REQUIRE_HUMAN_APPROVAL is True, the signal passes
    # all automated checks but is still flagged for human review.
    # main.py handles the actual gating logic.
    # ------------------------------------------------------------------
    if cfg.REQUIRE_HUMAN_APPROVAL:
        return True, (
            f"PENDING HUMAN APPROVAL — Signal passed all automated checks. "
            f"Action: {sig} {ticker} at {conf}% confidence. "
            f"Review and approve manually before executing."
        )

    # All checks passed
    return True, "Passed all risk checks. Ready for execution."


# =============================================================================
# POSITION SIZING
# =============================================================================

def calculate_position_size(portfolio_value: float,
                             price_per_share: float) -> int:
    """
    Calculate how many shares to buy based on risk rules.

    ANALYST NOTE:
        Uses MAX_POSITION_PCT to determine the dollar amount, then divides
        by the current share price to get share count. Always rounds DOWN
        to avoid accidentally exceeding the position limit.

        Example:
            portfolio_value = $10,000
            MAX_POSITION_PCT = 5%  →  $500 max position
            price_per_share = $150
            shares = floor($500 / $150) = 3 shares

    Args:
        portfolio_value (float): Total portfolio liquidation value
        price_per_share (float): Current ask price of the ticker

    Returns:
        int: Number of shares to buy (0 if calculation fails)
    """
    import math

    cfg = RiskConfig()

    if portfolio_value <= 0 or price_per_share <= 0:
        print("[risk_engine] Invalid portfolio value or price — returning 0 shares.")
        return 0

    max_position_dollars = portfolio_value * cfg.MAX_POSITION_PCT
    shares = math.floor(max_position_dollars / price_per_share)

    print(f"[risk_engine] Position sizing: "
          f"${portfolio_value:,.2f} portfolio × {cfg.MAX_POSITION_PCT*100}% "
          f"= ${max_position_dollars:,.2f} max → {shares} shares @ ${price_per_share:.2f}")

    return shares


# =============================================================================
# RISK REPORT
# =============================================================================

def print_risk_report(signal: dict, portfolio: dict) -> None:
    """
    Print a human-readable risk evaluation report to the terminal.

    ANALYST NOTE:
        Used in Phase 2-4 dry runs so the analyst can see exactly why
        a signal was approved or rejected, and what position size would
        have been taken.

    Args:
        signal    (dict): Signal from claude_signal.get_signal()
        portfolio (dict): Portfolio summary from schwab_client.get_portfolio_summary()
    """
    approved, reason = evaluate_signal(signal, portfolio)

    status_color = "\033[92m" if approved else "\033[91m"
    reset        = "\033[0m"

    print("\n" + "-"*60)
    print("  RISK ENGINE REPORT")
    print("-"*60)
    print(f"  Decision : {status_color}{'APPROVED' if approved else 'REJECTED'}{reset}")
    print(f"  Reason   : {reason}")

    if approved and signal.get("signal") == "BUY":
        price  = signal.get("lastPrice", 0)
        pvalue = portfolio.get("portfolio_value", 0)
        if price and pvalue:
            shares = calculate_position_size(pvalue, price)
            print(f"  Shares   : {shares} shares recommended")

    cfg = RiskConfig()
    print(f"\n  Active Rules:")
    print(f"    Min BUY confidence  : {cfg.MIN_CONFIDENCE_BUY}%")
    print(f"    Min SELL confidence : {cfg.MIN_CONFIDENCE_SELL}%")
    print(f"    Max position size   : {cfg.MAX_POSITION_PCT*100}% of portfolio")
    print(f"    Max open positions  : {cfg.MAX_OPEN_POSITIONS}")
    print(f"    Human approval      : {cfg.REQUIRE_HUMAN_APPROVAL}")
    print(f"    Min data quality    : {cfg.MIN_DATA_QUALITY}")
    print("-"*60 + "\n")


# =============================================================================
# CONFIDENCE DAMPING — WS2 Lever A (H1 feature-level; deployed with S1)
# =============================================================================
# ANALYST NOTE:
#   Implements the locked H1 verdict at feature level. The model's confidence
#   update lags multi-session price moves by ~5 sessions (certified Phase 2,
#   fully replicated live in 3-A; prompt-level remedies retired at closeout).
#   This rule stops waiting for the model: when the trailing 5-day move is
#   materially ADVERSE to the stance and conviction hasn't adjusted,
#   confidence is damped mechanically before the risk engine sees it.
#
#   Governance fit: this section ADDS a deterministic, auditable rule and can
#   only ever LOWER confidence — strictly more conservative. It does not
#   modify or override any RiskConfig rule; evaluate_signal() runs unchanged
#   on the operative value. Both channels are always preserved:
#       signal["confidence"]      -> OPERATIVE (damped) — downstream truth
#       signal["confidence_raw"]  -> the model's own output — audit channel
#
#   Parameters sized on the locked WMT arc (held 52-55% through a -9.99%
#   trailing move; the model's own eventual catch-up step was 55 -> 45).
#   With the defaults below, trail=-9.99% gives damp ~= 7 -> 55 becomes 48:
#   the "correct" update in one session instead of five. Change deliberately.

class DampingConfig:
    """Central damping parameter store — audit and adjust in one place."""

    THETA : float = 5.0   # % trailing move before damping engages
    K     : float = 1.5   # confidence pts removed per % beyond THETA
    CAP   : int   = 15    # max pts removed in one session
    FLOOR : int   = 35    # damping never pushes below this (0 = parse-error code)


def compute_trail_pct(price_history: list):
    """
    Trailing % change over the prior completed closes — the SAME number the
    prompt shows the model (closes[-1] vs closes[0]; see the basis footnote
    in WS2_H1_Feature_Spec.md). Returns None when unavailable.
    """
    if not price_history:
        return None
    closes = [p.get("close") for p in price_history if p.get("close") is not None]
    if len(closes) < 2 or not closes[0]:
        return None
    return (closes[-1] / closes[0] - 1.0) * 100.0


def damp_confidence_value(conf, direction, trail):
    """Core D1 damping, reusable on ANY confidence channel (base or WS1 blend).

    Given a confidence, a signal DIRECTION (BUY/HOLD/SELL) and a trailing %,
    return (damped_confidence, damp_points). Only ever LOWERS; floor-safe;
    never raises a value that arrived below the floor. Non-positive/missing
    confidence or missing trail -> returned unchanged with damp 0.
    """
    if not isinstance(conf, (int, float)) or conf <= 0:
        return conf, 0
    conf = int(conf)
    if trail is None:
        return conf, 0
    d = str(direction or "").upper()
    adverse = ((d in ("BUY", "HOLD") and trail <= -DampingConfig.THETA) or
               (d == "SELL" and trail >= DampingConfig.THETA))
    if not adverse:
        return conf, 0
    damp = int(round(min(DampingConfig.CAP,
                         DampingConfig.K * (abs(trail) - DampingConfig.THETA))))
    op = conf - damp
    if op < DampingConfig.FLOOR:
        op = min(conf, DampingConfig.FLOOR)   # clamp, never RAISE a sub-floor value
    return op, damp


def apply_conf_damping(signal: dict, price_history: list):
    """
    Base-path D1 (behavior unchanged). Mutates signal in place:
      - always stamps signal["confidence_raw"] when a valid confidence exists
      - lowers signal["confidence"] to the operative value on an adverse move

    meta = {"active", "trail", "raw", "op", "damp"} — feeds the D[...] log tag.
    """
    raw = signal.get("confidence")
    trail = compute_trail_pct(price_history)
    meta = {"active": False, "trail": trail, "raw": raw, "op": raw, "damp": 0}
    if not isinstance(raw, (int, float)) or raw <= 0:      # parse-error: never touch
        return signal, meta
    raw = int(raw)
    signal["confidence_raw"] = raw
    op, damp = damp_confidence_value(raw, signal.get("signal"), trail)
    signal["confidence"] = op
    meta.update(raw=raw, op=op, damp=damp, active=(damp != 0))
    return signal, meta
