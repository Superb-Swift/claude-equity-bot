# =============================================================================
# main.py
# =============================================================================
# PURPOSE:
#   Entry point for the Claude Equity Bot.
#
#   MULTI-ACCOUNT MONITORING + SCOUTING + NEWS + SUGGESTIONS WORKFLOW:
#     1. Pull all active accounts from Schwab
#     2. Print portfolio overview per account + aggregate summary
#     3. Build deduplicated watchlist with consolidated position context
#     4. For each unique ticker: fetch quote + news, generate signal
#     5. Generate ticker suggestions based on portfolio + market context
#     6. Log everything for review
#
# ANALYST NOTE:
#   Held-ticker signals now use CONSOLIDATED position context across all
#   accounts — one Claude call per ticker instead of one per account.
#   This eliminates duplicate token spend when you hold the same ticker
#   in multiple accounts. The signal mentions both account positions
#   in its analysis.
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
    get_price_history,
    get_all_portfolios,
    get_position_detail,
    ACCOUNT_LABELS,
)
from claude_signal    import get_signal, print_signal
from risk_engine      import (evaluate_signal, print_risk_report,
                              calculate_position_size, apply_conf_damping,
                              damp_confidence_value)
from news_client      import get_recent_headlines
from ticker_suggester import suggest_tickers, print_suggestions, log_suggestions
from signal_state     import load_signal_state, save_signal_state, update_signal_state
from context_providers import run_blend_scores
from blend_engine      import blend_confidence
import blend_providers  # noqa: F401 — registers the sector + regime blend providers

load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

PHASE = "3-B"   # advisory-only development (WS2 live); set to 2 to replay the Phase 2 handler

# A/B testing (H2 — direction asymmetry). When AB_TEST is True, every ticker is
# scored under each prompt variant on identical inputs and logged separately, so
# h2_direction_asymmetry.py can compare the arms. PROMPT_VARIANT is the single
# arm used when AB_TEST is off. Prefer toggling via run_ab_test.bat (which sets
# EQUITY_AB_TEST=1) over editing source, so the daily run never accidentally A/Bs.
AB_TEST = os.environ.get("EQUITY_AB_TEST", "0") == "1"
AB_VARIANTS = ("A", "B")
# ANALYST NOTE (2026-07-06, WS2): "A-S1D1" is a generator-ERA stamp, not an
#   A/B arm — the single live arm continues. S1 = prior-signal state input;
#   D1 = the confidence-damping rule (risk_engine.apply_conf_damping). Never
#   set this to bare "B": build_system_prompt() and the tracker parser both
#   treat exact "B" as the retired H2 experimental arm.
# ANALYST NOTE (2026-07-10, WS1): "-B1" adds the shadow-parallel triple
#   blend (C2 sector + C3 regime). Still ONE live arm, not an A/B. The
#   base signal remains the official advisory output; the blend is logged
#   (confidence_blend) and measured for G2 but does not drive the gate.
PROMPT_VARIANT = "A-S1D1-B1"

WATCHLIST_SCOUT = [
    "SPY",
    "QQQ",
    "VTI",
    "NVDA",
    "GLD",
]

MONITOR_HOLDINGS = True
ENABLE_SUGGESTIONS = True   # Set False to skip the daily suggester call

NEWS_DAYS_BACK = 7
NEWS_LIMIT     = 5

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
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)


# =============================================================================
# PORTFOLIO DISPLAY
# =============================================================================

def print_portfolio_overview(portfolio: dict) -> None:
    """Print a clean overview of a single account's portfolio."""
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
    """Print a roll-up summary across all analyzed accounts."""
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
# CONSOLIDATED POSITION CONTEXT (NEW)
# =============================================================================

def build_consolidated_position(ticker: str, portfolios: list) -> dict:
    """
    Build a unified position context for a ticker across all accounts.

    ANALYST NOTE:
        When you hold the same ticker in multiple accounts (e.g. NTR in
        both Roth IRA and Individual), this function combines them into
        one position context. Claude gets the full picture:
        - Total shares held across accounts
        - Weighted-average cost basis
        - Combined market value and P&L
        - Per-account breakdown for granular awareness

        This replaces the previous behavior of generating one Claude
        signal per account per ticker — cutting token spend roughly in
        half for duplicated tickers.

    Args:
        ticker     (str):  Ticker symbol
        portfolios (list): All account portfolios

    Returns:
        dict: Consolidated position dict, or {"is_held": False} if not held anywhere
    """
    holdings = []
    for portfolio in portfolios:
        position = get_position_detail(portfolio.get("positions", []), ticker)
        if position.get("is_held"):
            holdings.append({
                "account_label": portfolio.get("account_label", "?"),
                **position,
            })

    if not holdings:
        return {"is_held": False}

    # Aggregate across accounts
    total_shares      = sum(h.get("quantity", 0)        for h in holdings)
    total_market_val  = sum(h.get("market_value", 0)    for h in holdings)
    total_day_pnl     = sum(h.get("current_day_pnl", 0) for h in holdings)
    total_open_pnl    = sum(h.get("long_open_pnl", 0)   for h in holdings)

    # ANALYST NOTE: Weighted-average cost basis is shares-weighted, not
    # dollar-weighted. This matches how brokers calculate consolidated cost.
    weighted_cost = 0
    if total_shares > 0:
        weighted_cost = sum(
            h.get("average_price", 0) * h.get("quantity", 0)
            for h in holdings
        ) / total_shares

    return {
        "is_held"            : True,
        "quantity"           : total_shares,
        "average_price"      : weighted_cost,
        "market_value"       : total_market_val,
        "current_day_pnl"    : total_day_pnl,
        "current_day_pnl_pct": 0,   # Not meaningful when consolidated
        "long_open_pnl"      : total_open_pnl,
        "account_breakdown"  : holdings,   # Per-account detail for Claude
        "held_in_accounts"   : [h["account_label"] for h in holdings],
    }


# =============================================================================
# PHASE HANDLER (now account-agnostic)
# =============================================================================

def handle_phase2(ticker: str, signal: dict, position_detail: dict,
                  portfolios: list) -> None:
    """
    Phase 2: Dry run — log signal and risk decision, no execution.

    ANALYST NOTE:
        Uses the FIRST portfolio for risk engine evaluation since position
        limits are account-level. In Phase 3+ we may need to evaluate
        per-account separately if we add cross-account rules.
    """
    # Use the first portfolio for risk eval — simplest for Phase 2
    portfolio = portfolios[0] if portfolios else {}
    approved, reason = evaluate_signal(signal, portfolio)

    held_marker = "[HELD]" if position_detail.get("is_held") else "[SCOUT]"
    accounts = ",".join(position_detail.get("held_in_accounts", []))
    account_tag = f"[{accounts}]" if accounts else "[—]"

    log.info(
        f"Signal JSON: {json.dumps(signal)} | "
        f"[PHASE 2 DRY RUN] {account_tag} {held_marker} {ticker} | "
        f"Signal: {signal.get('signal')} | "
        f"Confidence: {signal.get('confidence')}% | "
        f"Risk: {'APPROVED' if approved else 'REJECTED'} | "
        f"Reason: {reason}"
    )

    print_signal(signal)
    print_risk_report(signal, portfolio)
    print(f"  >>> PHASE 2: No order placed. Signal logged to {log_filename}\n")


def handle_phase3a(ticker: str, signal: dict, position_detail: dict,
                   portfolios: list, price_history: list = None,
                   variant: str = None, prior_signals: list = None,
                   blend_caches: dict = None) -> None:
    """
    Phase 3-A: Advisory-only dry run WITH the H1 prior-5-day price input.

    ANALYST NOTE:
        Behaviorally identical to Phase 2 (no orders placed, human stays in
        the loop, same Risk Engine), with two additions that make the run
        measurable for H1:
          1. Logs are tagged [PHASE 3-A DRY RUN] so 3-A signals are cleanly
             separable from the Phase 2 backlog in the same log/tracker.
          2. The H1 price trajectory the model actually saw (trailing N-day
             move + the prior closes) is recorded on the log line, so
             h1_lag_trace.py can measure the confidence-update lag against
             the Phase 2 baseline.

        The bracket-tag block keeps the EXACT
            [PHASE 3-A DRY RUN] [<accounts>] [HELD|SCOUT]
        shape that parse_log_to_tracker.py expects; the H1[...] marker is
        appended after the existing fields and is ignored by the parser.
    """
    portfolio = portfolios[0] if portfolios else {}

    # WS2 Lever A (H1 feature-level): mechanical confidence damping runs
    # BEFORE the risk engine, so risk, print, log, and tracker all see the
    # OPERATIVE confidence. apply_conf_damping only ever lowers confidence
    # and always stamps signal["confidence_raw"] — the raw (model-side)
    # channel stays auditable on every line.
    signal, damp_meta = apply_conf_damping(signal, price_history)

    # WS1 SHADOW-PARALLEL blend (C2 sector + C3 regime). Computed on the model's
    # RAW confidence and damped through the SAME D1 (via damp_confidence_value)
    # for an apples-to-apples compare with the base operative. Logged + measured
    # for G2 but NOT driving the risk gate — the base path above is untouched.
    trail = damp_meta.get("trail")
    blend_scores, _blend_metas = run_blend_scores(ticker, blend_caches or {})
    conf_blend, blend_meta = blend_confidence(signal, blend_scores)
    conf_blend_op, _ = damp_confidence_value(conf_blend, signal.get("signal"), trail)
    signal["confidence_blend"] = conf_blend_op
    signal["sector_score"] = round(blend_scores.get("sector", 0.0), 3)
    signal["regime_score"] = round(blend_scores.get("regime", 0.0), 3)

    approved, reason = evaluate_signal(signal, portfolio)

    held_marker = "[HELD]" if position_detail.get("is_held") else "[SCOUT]"
    accounts = ",".join(position_detail.get("held_in_accounts", []))
    account_tag = f"[{accounts}]" if accounts else "[\u2014]"

    # H1 trajectory marker — what the model saw (for the lag harness).
    h1_tag = "H1[trajectory unavailable]"
    if price_history:
        closes = [p.get("close") for p in price_history if p.get("close") is not None]
        if len(closes) >= 2 and closes[0]:
            trail = (closes[-1] / closes[0] - 1) * 100
            path = ">".join(f"{c:.2f}" for c in closes)
            h1_tag = f"H1[trail{len(closes)}d={trail:+.2f}%; closes={path}]"

    # S1 tag — the prior-signal state the model saw (two-channel harness).
    if prior_signals:
        s1_tag = ("S1[prior=" +
                  ",".join(str(int(p.get("conf", 0))) for p in prior_signals) +
                  f"; dconf={int(prior_signals[-1].get('conf', 0)) - int(prior_signals[0].get('conf', 0)):+d}]")
    else:
        s1_tag = "S1[no prior state]"

    # D tag — Lever A audit trail (raw vs operative confidence).
    if damp_meta.get("trail") is None:
        d_tag = "D[trail n/a]"
    else:
        d_tag = (f"D[raw={damp_meta['raw']}; op={damp_meta['op']}; "
                 f"trail={damp_meta['trail']:+.2f}%; damp={damp_meta['damp']}]")

    # phase tag carries the A/B variant when running an A/B (H2).
    # ANALYST NOTE (2026-07-06): the tag must keep the literal "DRY RUN" —
    #   analyze_log.py's summary_pattern anchors on it. The phase token itself
    #   is regex-agnostic on both parsers as of this deploy.
    # B tag — WS1 blend audit (base raw -> pure blend -> blend operative).
    b_tag = (f"B[sec={signal.get('sector_score')}; reg={signal.get('regime_score')}; "
             f"w=0.15/0.15; base={damp_meta.get('raw')}; "
             f"blend={blend_meta.get('blend')}; blend_op={signal.get('confidence_blend')}]")

    phase_tag = f"[PHASE {PHASE} DRY RUN{(' ' + variant) if variant else ''}]"
    log.info(
        f"Signal JSON: {json.dumps(signal)} | "
        f"{phase_tag} {account_tag} {held_marker} {ticker} | "
        f"Signal: {signal.get('signal')} | "
        f"Confidence: {signal.get('confidence')}% | "
        f"Risk: {'APPROVED' if approved else 'REJECTED'} | "
        f"Reason: {reason} | "
        f"{h1_tag} | {s1_tag} | {d_tag} | {b_tag}"
    )

    print_signal(signal)
    print_risk_report(signal, portfolio)
    print(f"  >>> PHASE {PHASE} (advisory-only): No order placed. "
          f"Signal logged to {log_filename}\n")


# =============================================================================
# CORE PROCESSING
# =============================================================================

def process_ticker(ticker: str, portfolios: list,
                   quote_cache: dict, news_cache: dict,
                   history_cache: dict, signal_state: dict,
                   blend_caches: dict = None) -> None:
    """
    Process a single ticker ONCE across all accounts.

    ANALYST NOTE:
        Major change from previous version — we no longer loop per account.
        Each ticker gets exactly one Claude call. The consolidated position
        context tells Claude what's held in each account so it can still
        give account-aware advice in a single signal.

        Cache usage:
          - quote_cache: avoids duplicate Schwab quote calls
          - news_cache:  avoids duplicate Finnhub news calls
          - No scout cache needed — each ticker is processed once total
    """
    log.info(f"\nProcessing: {ticker}")

    try:
        # Quote (cached)
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

        # Prior-5-day price trajectory (H1) — cached
        if ticker in history_cache:
            price_history = history_cache[ticker]
        else:
            price_history = get_price_history(ticker, days=5)
            history_cache[ticker] = price_history

        if price_history:
            log.info(f"{ticker} | Prior {len(price_history)} closes loaded for H1 trajectory")

        # News (cached)
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

        # Consolidated position across all accounts
        position_detail = build_consolidated_position(ticker, portfolios)
        position_context = position_detail if position_detail.get("is_held") else None

        if position_detail.get("is_held"):
            accounts = ", ".join(position_detail.get("held_in_accounts", []))
            log.info(
                f"[HELD] {ticker} | "
                f"Total Shares: {position_detail.get('quantity'):.0f} | "
                f"Weighted Cost: ${position_detail.get('average_price', 0):,.2f} | "
                f"Day P&L: ${position_detail.get('current_day_pnl', 0):,.2f} | "
                f"In: {accounts}"
            )
        else:
            log.info(f"[SCOUT] {ticker} | Not currently held")

        # Generate the signal(s) for this ticker — one per A/B variant when
        # AB_TEST is on (H2), a single variant otherwise. Both arms see
        # identical inputs (same quote, news, position, price history).
        log.info(f"Requesting Claude signal for {ticker}...")
        variants = AB_VARIANTS if AB_TEST else (PROMPT_VARIANT,)

        # WS2 Lever B (S1): the model's own prior outputs for this ticker —
        # RAW confidences (state is updated with confidence_raw below), so
        # the model-side channel is never contaminated by Lever A's damping.
        prior_signals = signal_state.get(ticker, [])
        for variant in variants:
            signal = get_signal(
                ticker=ticker,
                quote=quote,
                position=position_context,
                headlines=headlines,
                metrics=None,
                price_history=price_history,
                prior_signals=prior_signals,
                prompt_variant=variant
            )

            signal["lastPrice"] = quote.get("lastPrice", 0)
            tag_variant = variant if AB_TEST else None

            if PHASE == 2:
                handle_phase2(ticker, signal, position_detail, portfolios)
            elif PHASE in ("3-A", "3A", 3, "3-B", "3B"):
                handle_phase3a(ticker, signal, position_detail, portfolios,
                               price_history, variant=tag_variant,
                               prior_signals=prior_signals,
                               blend_caches=blend_caches)
            else:
                log.error(f"Phase {PHASE} handler not implemented in this build.")

            # WS2 S1 state update — RAW confidence only (Lever A stamps
            # confidence_raw before any damping mutates "confidence").
            # Guards: parse-error signals (error key / conf 0) never enter
            # the chain; only the first (control) arm writes, so a
            # re-enabled A/B could never double-write the same date.
            if variant == variants[0] and not signal.get("error"):
                raw_conf = signal.get("confidence_raw", signal.get("confidence"))
                if isinstance(raw_conf, (int, float)) and raw_conf > 0:
                    update_signal_state(
                        signal_state, ticker,
                        datetime.now().strftime("%Y-%m-%d"),
                        signal.get("signal", ""), int(raw_conf),
                    )
                    save_signal_state(signal_state)

    except Exception as e:
        log.error(f"Error processing {ticker}: {e}")


# =============================================================================
# SUGGESTION RUNNER
# =============================================================================

def run_suggester(portfolios: list, news_cache: dict) -> None:
    """
    Generate ticker suggestions based on portfolio and market context.

    ANALYST NOTE:
        Uses SPY headlines as the broad-market signal since SPY is in
        the default scout list. If you remove SPY from scout, this falls
        back to a generic prompt without market context.
    """
    log.info("\n" + "#"*60)
    log.info("# GENERATING TICKER SUGGESTIONS")
    log.info("#"*60)

    # Collect all unique held tickers across accounts
    all_held = set()
    for p in portfolios:
        all_held.update(p.get("held_tickers", []))

    # Use SPY headlines as proxy for broad-market context (cached from earlier)
    market_headlines = news_cache.get("SPY", [])

    result = suggest_tickers(
        held_tickers=sorted(all_held),
        scout_list=WATCHLIST_SCOUT,
        market_headlines=market_headlines
    )

    print_suggestions(result)
    history_path = log_suggestions(result, LOG_DIR)

    log.info(f"Suggestions saved to: {history_path}")
    log.info(f"Suggestion tokens: {result.get('input_tokens', '?')} in / "
             f"{result.get('output_tokens', '?')} out")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def prefetch_blend_context(watchlist, days_sector=20, days_regime=20):
    """Fetch, ONCE per run, the unique sector-backbone ETFs and the regime
    series (SPY/GLD) the WS1 blend needs. Returns
    {"sector": {etf: closes}, "regime": {"SPY": closes, "GLD": closes}}.
    Failures degrade to absent keys (the blend scores those neutral)."""
    from sector_map import sector_reference
    sector_cache = {}
    refs = {sector_reference(t) for t in watchlist}
    refs.discard(None)
    for etf in sorted(refs):
        try:
            ph = get_price_history(etf, days=days_sector)
            sector_cache[etf] = [p.get("close") for p in ph if p.get("close") is not None]
        except Exception as e:
            log.warning(f"[WS1] sector prefetch failed for {etf}: {e}")
    regime_cache = {}
    for a in ("SPY", "GLD"):
        try:
            ph = get_price_history(a, days=days_regime)
            regime_cache[a] = [p.get("close") for p in ph if p.get("close") is not None]
        except Exception as e:
            log.warning(f"[WS1] regime prefetch failed for {a}: {e}")
    log.info(f"[WS1] blend context: {len(sector_cache)} sector ETF(s), "
             f"regime {sorted(regime_cache)} loaded")
    return {"sector": sector_cache, "regime": regime_cache}


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
            log.error("No active portfolios found.")
            return

        log.info(f"Loaded {len(portfolios)} active account(s): "
                 f"{', '.join(p['account_label'] for p in portfolios)}")

    except Exception as e:
        log.error(f"Portfolio fetch failed: {e}")
        return

    # STEP 2: Print overviews
    for portfolio in portfolios:
        print_portfolio_overview(portfolio)
    print_aggregate_summary(portfolios)

    # STEP 3: Build deduplicated watchlist
    # ANALYST NOTE: We combine all held tickers across accounts into one
    # unique set, then add scout tickers. Each ticker is processed exactly
    # once regardless of how many accounts hold it.
    all_held = set()
    for p in portfolios:
        all_held.update(p.get("held_tickers", []) if MONITOR_HOLDINGS else [])

    seen = set()
    watchlist = []
    for ticker in sorted(all_held) + WATCHLIST_SCOUT:
        if ticker not in seen:
            watchlist.append(ticker)
            seen.add(ticker)

    held_count  = sum(1 for t in watchlist if t in all_held)
    scout_count = len(watchlist) - held_count

    log.info("\n" + "#"*60)
    log.info(f"# ANALYZING {len(watchlist)} UNIQUE TICKERS")
    log.info(f"# {held_count} held + {scout_count} scouting")
    log.info(f"# (Held tickers analyzed once with consolidated cost basis)")
    log.info("#"*60)

    # STEP 4: Process each ticker with shared caches
    quote_cache   = {}
    news_cache    = {}
    history_cache = {}

    # WS2 S1: per-ticker prior-signal state (raw confidences, last 5
    # sessions). Missing/corrupt file degrades to {} — the prompt section
    # renders its "no prior state" form and the chain rebuilds from today.
    # Re-seedable any time from the tracker via seed_signal_state.py.
    signal_state = load_signal_state()
    log.info(f"Prior-signal state loaded: {len(signal_state)} ticker(s)")

    # WS1 blend context — prefetched once for the whole run.
    blend_caches = prefetch_blend_context(watchlist)

    for ticker in watchlist:
        process_ticker(ticker, portfolios, quote_cache, news_cache,
                       history_cache, signal_state, blend_caches)

    # STEP 5: Generate ticker suggestions
    if ENABLE_SUGGESTIONS:
        try:
            run_suggester(portfolios, news_cache)
        except Exception as e:
            log.error(f"Suggester failed: {e}")

    log.info("\nBot run complete.")
    log.info(f"Full log saved to: {log_filename}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_bot()
