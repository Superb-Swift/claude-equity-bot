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

def evaluate_signal(signal: dict, portfolio: dict,
                    held_value: float = None) -> tuple[bool, str]:
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
    # CHECK 6: Portfolio concentration — MONITORING-BURDEN FLAG, NOT A GATE
    #
    # RULED 2026-08-11 — DP-3C-o (i) + (iii). RW.
    #   (i)  D-3: the cap applies to BUY only. A SELL REDUCES the position
    #        count, so rejecting one for "too many open positions" is the
    #        rule firing in the opposite direction to its own purpose. This
    #        is what rejected CBRS's SELL at conf 68 on 2026-06-26, which
    #        stands in the DP-3C-l ledger as "REJECTED — position count".
    #   (iii) The check no longer REJECTS. It records a flag and the signal
    #        proceeds to the human-approval gate.
    #
    # RATIONALE OF RECORD: MAX_OPEN_POSITIONS is a monitoring-burden cap,
    # not a risk cap, and RiskConfig's own note (L59-63) says so in as many
    # words — "Fewer positions = more concentration risk but easier to
    # monitor. More positions = more diversification but harder to track."
    # By its own comment the cap BUYS monitoring convenience by ACCEPTING
    # concentration risk. A rule that increases the risk it is filed under
    # should not hold a veto over the signal.
    #
    # PRESERVED FINDING, REQUIRED BY THE RULING AND NOT TO BE ERASED:
    #   Under the Phase-2 cap the risk engine approved ZERO directional
    #   signals across 57 cohorts. That is the pre-change record. This
    #   amendment makes the approval rate look better BY CONSTRUCTION, so
    #   any future reading of approval counts MUST date-split on 2026-08-11
    #   rather than pool across it. Recorded as making the record look
    #   better, which is the direction warranting the most scepticism.
    #
    # NOT ADOPTED: DP-3C-o (ii) — enforcing MAX_POSITION_PCT inside
    # evaluate_signal — is NOT ruled and is NOT implemented. The rule that
    # actually sizes a position therefore still does not run inside this
    # function. Recorded as an OPEN ITEM, because demoting CHECK 6 without
    # (ii) leaves no position-concentration rule enforced at evaluation
    # time; calculate_position_size still bounds the RECOMMENDED share
    # count downstream, but nothing bounds concentration at the gate.
    #
    # PRE-CONDITION SATISFIED: D-7's approval-path audit passes as of
    # 2026-08-11 — the parsers have now seen an APPROVED directional row
    # carrying the multi-sentence PENDING HUMAN APPROVAL reason. Touching
    # CHECK 6 before that audit existed would have shipped a never-parsed
    # line shape into a canonical cohort.
    # ------------------------------------------------------------------
    open_positions = portfolio.get("positions", [])
    if sig == "BUY" and len(open_positions) >= cfg.MAX_OPEN_POSITIONS:
        signal.setdefault("risk_flags", []).append(
            f"RISK-ENGINE: {len(open_positions)} open positions at or above "
            f"the monitoring cap of {cfg.MAX_OPEN_POSITIONS} "
            f"(CHECK 6, non-blocking per DP-3C-o)"
        )

    # ------------------------------------------------------------------
    # CHECK 6b: POSITION CONCENTRATION — MAX_POSITION_PCT, ENFORCED
    #
    # RULED 2026-08-11 — DP-3C-o (ii). RW.
    #   MAX_POSITION_PCT was printed as an Active Rule on every signal and
    #   consulted by NOTHING inside evaluate_signal (D-6: calculate_position_
    #   size is imported at main.py L41 and never called, so the cap was
    #   advertised everywhere and enforced nowhere — the thirteenth instance
    #   of the tool-reports-a-value-it-did-not-compute class and the first
    #   found in the risk engine). This is the rule that actually measures
    #   concentration risk, so this is the rule that now runs.
    #
    # WHY THIS ENFORCES WHILE CHECK 6 ONLY FLAGS: MAX_POSITION_PCT is a REAL
    # risk cap — its own note says it "prevents catastrophic loss if one
    # position goes to zero". MAX_OPEN_POSITIONS is a monitoring-burden cap
    # by its own note. The real cap gates; the burden cap reports.
    #
    # DENOMINATOR: `portfolio` is ONE ACCOUNT, per D-1/D-2 (RW 2026-08-11).
    # `held_value` is this ticker's market value IN THAT SAME ACCOUNT. Both
    # sides of the comparison are therefore account-scoped, which is the
    # whole point of the D-1 ruling: 5% of the account that actually holds
    # the position, never 5% of a blended total.
    #
    # held_value=None means the caller did not supply per-account holdings,
    # and the check is SKIPPED rather than guessed. A concentration rule
    # evaluated against an unknown denominator would be worse than none.
    # ------------------------------------------------------------------
    if sig == "BUY" and held_value is not None:
        pvalue = portfolio.get("portfolio_value", 0) or 0
        if pvalue > 0:
            cap_dollars = cfg.MAX_POSITION_PCT * pvalue
            if held_value >= cap_dollars:
                return False, (
                    f"Position concentration: {ticker} is already "
                    f"${held_value:,.0f} in this account, at or above the "
                    f"{cfg.MAX_POSITION_PCT:.0%} cap of ${cap_dollars:,.0f}."
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
# D-1 / D-2 -- PER-ACCOUNT EVALUATION
# =============================================================================
# RULED 2026-08-11 -- D-1 / D-2. RW: PER-ACCOUNT, not consolidated.
#
# THE DEFECT: main.py L339 passed `portfolios[0] if portfolios else {}` into
# evaluate_signal -- whichever account Schwab happened to return first. Every
# risk decision in 57 cohorts was therefore computed against ONE arbitrary
# account while the bot trades across Roth IRA, Individual and Scout.
# `print_aggregate_summary` and `build_consolidated_position` both walk every
# portfolio correctly; the risk engine alone did not. The rejection that
# killed NVDA and CBRS -- "Too many open positions: 16 >= max 8" -- cited a
# count describing a fraction of the portfolio.
#
# RULING RATIONALE OF RECORD (RW): per-account is tighter and more accurate.
# Consolidation invites misleading aggregates and blurs the case where 5% of
# the combined value exceeds 5% of the account actually holding the position.
#
# TARGETING:
#   SELL -> only accounts that HOLD the ticker. You cannot sell what is not
#           there, so a SELL is never evaluated against an account with no
#           position in the name.
#   BUY  -> EVERY account (RW 2026-08-11). A new position could land in any
#           of them, so no account is privileged by assumption.
#
# COLLAPSE (RW 2026-08-11): the single Risk: token reads APPROVED when the
# signal is actionable in AT LEAST ONE account. The per-account split is
# preserved verbatim in the reason rather than discarded, because "actionable
# in the Roth but not the Individual" is the actual answer and collapsing it
# to one bit destroys the fact the D-1 ruling exists to expose.
#
# THE REASON CONTAINS NO " | ". main.py joins the log line's fields with
# " | ", so a pipe inside the reason would truncate every downstream parser's
# capture at the wrong point. Separator is "; " deliberately. D-7 established
# that the parsers tolerate a long multi-sentence reason; it did NOT establish
# that they tolerate one containing the field delimiter, and this code must
# not be the thing that finds out.
# =============================================================================

def evaluate_signal_per_account(signal: dict, portfolios: list,
                                account_breakdown: list = None) -> tuple[bool, str]:
    """Evaluate one signal against each relevant account separately.

    Returns the same (approved, reason) contract as evaluate_signal, so the
    log line shape is unchanged -- only the reason TEXT grows.
    """
    cfg = RiskConfig()
    sig = signal.get("signal", "HOLD")

    held = {}
    for h in (account_breakdown or []):
        lbl = h.get("account_label")
        if lbl is not None:
            held[lbl] = h.get("market_value", 0.0) or 0.0

    # No portfolios at all: degrade to the documented empty-portfolio path
    # rather than inventing an approval.
    if not portfolios:
        return evaluate_signal(signal, {})

    results = []
    for p in portfolios:
        label = p.get("account_label", "?")
        if sig == "SELL" and label not in held:
            continue
        probe = dict(signal)
        probe["risk_flags"] = []
        ok, why = evaluate_signal(probe, p, held_value=held.get(label))
        results.append((label, ok, why, probe.get("risk_flags") or []))

    if not results:
        # A SELL on a ticker held nowhere. Real, and not an approval.
        return False, (
            f"{signal.get('ticker', 'UNKNOWN')}: SELL signal but the ticker "
            f"is not held in any account."
        )

    # Engine-generated flags carry the account they came from, otherwise a
    # flag reading "16 open positions" is the same ambiguity D-1 just fixed.
    merged = signal.setdefault("risk_flags", [])
    for label, _ok, _why, flags in results:
        for f in flags:
            merged.append(f"[{label}] {f}")

    approved = any(ok for _l, ok, _w, _f in results)
    split = "; ".join(
        f"{label}={'APPROVED' if ok else 'REJECTED'}"
        for label, ok, _w, _f in results)

    if approved:
        base = next(why for _l, ok, why, _f in results if ok)
        blocked = [f"{label}: {why.rstrip('.')}"
                   for label, ok, why, _f in results if not ok]
        detail = (" NOT actionable in " + "; ".join(blocked) + ".") if blocked else ""
        return True, f"{base} PER-ACCOUNT: {split}.{detail}"

    worst = "; ".join(f"{label}: {why.rstrip('.')}"
                      for label, _ok, why, _f in results)
    return False, f"Rejected in every account. PER-ACCOUNT: {split}. {worst}."


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

def print_risk_report(signal: dict, portfolio: dict,
                      approved: bool = None, reason: str = None,
                      portfolios: list = None) -> None:
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
    # D-1 (RW 2026-08-11) -- DO NOT RE-EVALUATE HERE.
    #
    # This function used to call evaluate_signal() itself, independently of
    # the caller. That was survivable while both calls saw the same input.
    # It stopped being survivable the moment the LOG began deciding
    # per-account: main.py would log the per-account verdict and this
    # function would print a SECOND verdict computed against portfolios[0]
    # alone. A signal approved in Individual but rejected in the Roth would
    # have LOGGED APPROVED and PRINTED REJECTED, on the same row, in the
    # same run -- two computations of one value that can disagree, which is
    # the defect class this file has now produced three times (D-5, D-6,
    # and the CHECK 6 label).
    #
    # It also double-appended: CHECK 6 mutates signal["risk_flags"], so a
    # second evaluation of the same dict added the flag twice. The logged
    # JSON escaped that only because main.py logs BEFORE printing.
    #
    # The caller now passes the decision it actually made and logged. The
    # fallback re-evaluates only when a caller supplies neither -- which is
    # the dead handle_phase2 path and any external caller of this helper.
    if approved is None or reason is None:
        approved, reason = evaluate_signal(signal, portfolio)

    status_color = "\033[92m" if approved else "\033[91m"
    reset        = "\033[0m"

    print("\n" + "-"*60)
    print("  RISK ENGINE REPORT")
    print("-"*60)
    print(f"  Decision : {status_color}{'APPROVED' if approved else 'REJECTED'}{reset}")
    print(f"  Reason   : {reason}")

    cfg = RiskConfig()

    # D-1 (RW 2026-08-11): size PER ACCOUNT. MAX_POSITION_PCT is a
    # percentage OF AN ACCOUNT, so a single recommendation computed from
    # portfolios[0] is a share count for an account the approval may not
    # even apply to. Each account is sized against its OWN value; the
    # per-account approval split is in the Reason line above.
    if approved and signal.get("signal") == "BUY":
        price = signal.get("lastPrice", 0)
        accounts = portfolios if portfolios else ([portfolio] if portfolio else [])
        printed = False
        for p in accounts:
            pvalue = p.get("portfolio_value", 0)
            if not (price and pvalue):
                continue
            label = p.get("account_label", "Account")
            shares = calculate_position_size(pvalue, price)
            print(f"  Shares   : {shares} shares in {label} "
                  f"({cfg.MAX_POSITION_PCT:.0%} of ${pvalue:,.0f})")
            printed = True
        if not printed:
            print("  Shares   : not sized -- no account value available")

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
