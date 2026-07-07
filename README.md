# Claude Equity Bot

> An AI-powered equity research and signal generation system that combines real-time brokerage data, large language model analysis, and disciplined risk management to produce structured trading signals for human review.

![Phase](https://img.shields.io/badge/Phase-3--B%20Advisory%20Development-orange)
![Language](https://img.shields.io/badge/Python-3.14-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active%20Development-success)

---

## Overview

Claude Equity Bot is a personal research tool that ingests live portfolio data from **Charles Schwab's Trader API**, enriches it with recent news from **Finnhub**, and asks **Anthropic's Claude** to generate structured BUY/SELL/HOLD signals. Every signal flows through a hardcoded risk engine before being eligible for human approval — automated trading is **never** initiated without explicit consent.

The system is designed around three principles:

1. **Discipline over speed** — A multi-phase rollout (dry run → paper simulation → live trading) ensures the system is proven before it touches real orders.
2. **Position awareness** — Signals factor in cost basis, unrealized P&L, and tax-account context (Roth vs Individual).
3. **Transparency** — Every signal includes reasoning, risk flags, and a confidence score the human can audit.

---

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Schwab API     │     │   Finnhub API    │     │  Anthropic API   │
│  (quotes,        │     │  (news headlines)│     │  (Claude signal  │
│   positions)     │     │                  │     │   generation)    │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         ▼                        ▼                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │                       main.py                            │
    │              (multi-account orchestrator)                │
    └────────────────────────┬────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │       risk_engine.py          │
              │  (confidence + position size  │
              │   + data quality gates)       │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Signal log + daily analyzer  │
              │  + ticker suggester + tracker │
              │           export              │
              └──────────────────────────────┘
```

Phase 3-B adds a per-ticker **prior-signal state loop**: `main.py` loads `signal_state.json` at run start, feeds each ticker's own last-5 outputs (raw confidences) into the prompt alongside the price trajectory, and writes the updated state back — so the model can see its own staleness against the move it is already shown.

---

## Features

- **Multi-account portfolio integration** — Aggregates positions across Roth IRA and Individual taxable accounts, with weighted-average cost basis calculations
- **Position-aware signals** — Claude sees your cost basis, P&L, and which account holds the position before generating recommendations
- **News context** — Recent headlines are fetched per ticker via Finnhub and included in the analysis prompt
- **Asset-type awareness** — ETFs receive different fundamental analysis than equities (P/E is suppressed for ETFs since broker-reported values are unreliable for fund products)
- **Risk engine** — Confidence thresholds, position-size caps, data-quality minimums, and human-approval gates prevent overconfident or low-quality signals from triggering action
- **Daily ticker suggester** — Claude analyzes portfolio gaps, market themes, and peer companies to suggest new research candidates each day
- **Audit-ready logging** — Every signal is logged with reasoning, risk flags, and token usage; a daily analyzer produces a one-page digest
- **Hypothesis-driven validation** — Read-only harnesses probed signal behavior against the accumulated logs: the H1 confidence-update-lag finding was certified in Phase 2 and fully replicated live in Phase 3-A, H2/H3 were descoped at the 3-A closeout, and the H4 data-quality watchdog keeps running as a monitor
- **Prior-signal state input (S1)** — the model receives its own last-5 signals and confidences per ticker, closing the statelessness gap behind the certified lag finding
- **Confidence damping (D1)** — a deterministic post-model rule damps stale conviction into a material adverse trailing move; every line logs both the raw (model) and operative (damped) confidence, so the model-side channel stays auditable
- **Phased rollout** — Phases 2 (read-only calibration) and 3-A (live advisory) are complete; the system is currently in **Phase 3-B** (advisory-only development: triple-blend architecture plus the H1 feature-level implementation), with Phase 3-C (EDGAR filing context), paper simulation, and Phase 4 (live trading with approval gates) planned

---

## Tech Stack

| Component | Purpose |
|---|---|
| **Python 3.14** | Core language |
| **schwab-py** | Charles Schwab Trader API client |
| **anthropic** | Claude API SDK |
| **finnhub-python** | News and fundamentals data |
| **python-dotenv** | Environment variable management |
| **openpyxl** | Reads/writes the tracking spreadsheet for the validation harnesses |
| **OAuth 2.0** | Authentication with Schwab |
| **Git / GitHub** | Version control |

---

## Module Breakdown

### Core signal pipeline

| File | Responsibility |
|---|---|
| `main.py` | Orchestrator — pulls portfolios, dedupes the watchlist, coordinates signal generation across modules; carries the active phase flag and the generator-era label (`prompt_variant`); maintains the S1 state each run |
| `schwab_client.py` | Data layer — authenticates with Schwab, fetches quotes and positions, handles account labeling |
| `news_client.py` | News layer — fetches recent headlines per ticker from Finnhub |
| `claude_signal.py` | Signal layer — builds structured prompts (the prior-5-day price trajectory **and** the S1 prior-signal state) and parses Claude's JSON responses |
| `risk_engine.py` | Decision layer — applies hardcoded rules to approve or reject signals; hosts the WS2 confidence-damping rule (raw vs operative confidence) |
| `signal_state.py` | State layer — persistence for the S1 prior-signal input (raw confidences, last 5 per ticker; re-seedable from the tracker) |
| `seed_signal_state.py` | State layer — one-shot seed/restore of `signal_state.json` from the tracker Signals tab |
| `ticker_suggester.py` | Generative layer — proposes new tickers based on portfolio gaps, market themes, and peer analysis |
| `analyze_log.py` | Analytics layer — produces a daily digest of signals, confidence distributions, and data quality breakdowns |
| `parse_log_to_tracker.py` | Export layer — converts a run's signal log into paste-ready tracker rows (phase-agnostic tag parsing; imports the operative confidence) |

### Research & validation tooling

| File | Responsibility |
|---|---|
| `h1_lag_trace.py` | Hypothesis 1 — confidence-update-lag tracer; two-channel in 3-B (`--raw-from-logs` recovers the raw model confidence from the logs, AM-canonical; `--suffix` keeps channel MDs separate) |
| `h2_direction_asymmetry.py` | Hypothesis 2 — directional-asymmetry harness (descoped at the 3-A closeout; retained for archival reproducibility) |
| `h3_thesis_stability.py` | Hypothesis 3 — thesis-stability harness (descoped at the 3-A closeout; retained for archival reproducibility) |
| `h4_dq_threshold.py` | Hypothesis 4 — data-quality-conditional threshold watchdog (running monitor) |
| `guardrail_trace.py` | Scoreboard + guardrail trace; `--stratify-regime` writes `regime_stratification.md` — the Q1-R / T2 tripwire sensors |
| `build_near_miss_registry.py` | Regenerates the near-miss BUY registry from the signal logs |
| `run_daily.bat` | Windows runner — venv activate → signals → analyzer → tracker rows |
| `run_weekly_review.bat` | Windows runner — WMT + GM lag tracers (full-series and post-deploy two-channel acceptance slices), H4 watchdog, near-miss registry rebuild, guardrail trace with regime stratification |

All four harnesses accept `--since` / `--until` for phase-scoped analysis (e.g. `--since 2026-06-15` isolates Phase 3-A from the certified Phase 2 window).

---

## Sample Signal Output

```
============================================================
  SIGNAL: HOLD  |  Ticker: NTR  |  Confidence: 62%
============================================================
  Reasoning   : Nutrien trades at a reasonable 14.5x P/E with a solid 
                3.07% dividend yield, and Oppenheimer's raised price 
                target of $82 suggests ~15% upside from current levels.
  Bull Case   : Oppenheimer's Outperform rating with an $82 price target...
  Bear Case   : Fertilizer demand is cyclical and sensitive to global...
  Time Frame  : MEDIUM
  Data Quality: HIGH
  Position    : Holding 16 shares with a $70.22 cost basis and only
                $13.49 in unrealized gains...
  Risk Flags  : Volume significantly below 10-day average, Geopolitical 
                risk on fertilizer supply, Cyclical earnings sensitivity
============================================================
```

*(When damping engages, the header shows both channels: `Confidence: 48% (raw 55%)`.)*

---

## Sample Daily Digest

```
========================================================================
  DAILY SIGNAL SUMMARY — 2026-05-19
========================================================================
  Total signals analyzed: 24

  SIGNAL DISTRIBUTION
  BUY    :   1  (  4.2%)
  SELL   :   0  (  0.0%)
  HOLD   :  23  ( 95.8%)

  CONFIDENCE STATS
  Average confidence : 53.2%
  Highest            : 68%

  DATA QUALITY DISTRIBUTION
  HIGH    (  7)  29.2%  ███████
  MEDIUM  ( 17)  70.8%  █████████████████
  LOW     (  0)   0.0%

  CLAUDE API USAGE
  Input tokens   :   23,500
  Output tokens  :    9,500
  Estimated cost : $0.21
========================================================================
```

---

## Phased Rollout

| Phase | State | Description |
|---|---|---|
| **Phase 1** | ✅ Complete | Foundation — auth, quote retrieval, single-account positions |
| **Phase 2** | ✅ Complete | Read-only calibration dry run (19 trading days, concluded 2026-06-12) — full signal pipeline, thresholds calibrated, no orders placed |
| **Phase 3-A** | ✅ Complete | Live advisory run (14 sessions, concluded 2026-07-06) — no orders placed. H1 lag verdict locked; the certified Phase 2 guardrail failed to reproduce out-of-sample and was **suspended** before anything relied on it; H2/H3 descoped; the A/B program terminated |
| **Phase 3-B** | 🟡 Current | Advisory-only development — triple-blend architecture (WS1), the H1 feature-level implementation (S1 prior-signal state + D1 confidence damping; generator era A-S1D1), Q3 commodity-context code (WS3) — still no orders placed |
| **Phase 3-C** | ⏸️ Planned | EDGAR SEC-filing context (Form 4, 8-K, 10-Q/10-K MD&A) — entry criteria pre-registered in the 3-B exit / 3-C entry decision instrument |
| **Phase 3** | ⏸️ Planned | Paper simulation — simulated order placement, no real money |
| **Phase 4** | ⏸️ Planned | Live trading — real orders with mandatory human approval |

---

## Risk Engine Configuration

The risk engine acts as a backstop against overconfident or poorly-calibrated signals. Current settings:

```python
MIN_CONFIDENCE_BUY   = 70%      # BUY signals need ≥70% confidence
MIN_CONFIDENCE_SELL  = 65%      # SELL signals need ≥65% confidence
MAX_POSITION_PCT     = 5.0%     # No single position above 5% of portfolio
MAX_OPEN_POSITIONS   = 8        # Cap on total concurrent holdings
DAILY_LOSS_LIMIT     = 2.0%     # Halt new BUYs if daily portfolio loss exceeds 2%
ALLOW_POSITION_ADD   = False    # Disallow adding to existing positions
REQUIRE_HUMAN_APPROVAL = True   # Always require human approval (Phase 4+)
MIN_DATA_QUALITY     = "MEDIUM" # Reject LOW-quality signals automatically
```

Phase 3-B adds a deterministic **confidence-damping** layer ahead of these gates (`risk_engine.apply_conf_damping`):

```python
DAMP_THETA = 5.0%   # trailing 5-day move before damping engages
DAMP_K     = 1.5    # confidence points removed per % beyond theta
DAMP_CAP   = 15     # maximum points removed in one session
DAMP_FLOOR = 35     # damping never pushes below this floor
```

Damping only ever lowers confidence; both the raw and the operative value are logged on every line.

The base thresholds were calibrated empirically over Phase 2's 19-trading-day dry run (concluded 2026-06-12). Two live updates from Phase 3-A: the **50–59% confidence-band guardrail** certified in Phase 2 **failed to reproduce out-of-sample** and is **suspended as a decision input** (it runs monitor-only, with re-open triggers parked under the Q1-R record) — exactly the failure mode the phase discipline exists to catch — while the **70% near-miss BUY threshold was reinforced** (near-misses failed both forward horizons live).

---

## Setup

### Prerequisites

- Python 3.14+
- A Charles Schwab Developer Portal account with API access
- An Anthropic API key
- A Finnhub API key (free tier sufficient)

### Installation

```bash
# Clone the repository
git clone https://github.com/Superb-Swift/claude-equity-bot.git
cd claude-equity-bot

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS / Linux

# Install runtime dependencies (the bot)
pip install schwab-py anthropic finnhub-python python-dotenv flask cryptography

# Install the analysis layer (openpyxl, used by the validation harnesses)
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root (never committed):

```env
SCHWAB_APP_KEY=your_schwab_app_key
SCHWAB_APP_SECRET=your_schwab_app_secret
CALLBACK_URL=https://127.0.0.1:8182
TOKEN_PATH=token.json
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=your_finnhub_key
```

Update `ACTIVE_ACCOUNTS` and `ACCOUNT_LABELS` in `schwab_client.py` with your own Schwab account numbers.

### Run

```bash
python main.py            # Generate signals (single prompt arm)
python analyze_log.py     # Produce the daily digest

# Windows convenience runners
run_daily.bat             # venv + signals + analyzer + tracker rows
run_weekly_review.bat     # lag tracers (two-channel) + H4 + registry + T2 sensors

# S1 state seed / restore (warm start; recovery after a PM diagnostic run)
python seed_signal_state.py --tracker tracker_with_registry.xlsx

# Phase-scoped hypothesis analysis (any harness)
python h1_lag_trace.py --since 2026-06-15

# WS2 acceptance reads (post-deploy, both channels)
python h1_lag_trace.py --since 2026-07-07 --ticker WMT --suffix _3B
python h1_lag_trace.py --since 2026-07-07 --ticker WMT --raw-from-logs "logs\signals_*.log" --suffix _raw_3B
```

---

## Design Principles

### Why Phase Discipline?

Algorithmic trading systems most often fail not because the strategy is wrong, but because the operator skipped validation. Phase 2 forced a minimum of 2-3 weeks of observed signals before any simulated trading began, and Phase 3 forces a similar period of paper trading before any real capital is at risk. Phase 3-A proved the point in practice: a Phase-2-certified edge inverted out-of-sample and was caught — and suspended — by the advisory run before any capital could have relied on it.

### Why Human Approval?

Even at Phase 4, every signal that passes the risk engine requires a human "yes" before an order is placed. This is not a temporary safeguard — it is permanent architecture. The bot is a research assistant, not an autopilot.

### Why Position-Aware?

A 5% gain in a Roth IRA is structurally different from a 5% gain in a taxable account. The bot's signals account for this — selling appreciated stock in the Roth has no tax consequence, while doing so in the Individual account triggers capital gains. Claude is given per-account breakdowns so its recommendations can be tax-aware.

---

## Roadmap

| Feature | Status |
|---|---|
| Multi-account portfolio integration | ✅ Done |
| News context (Finnhub) | ✅ Done |
| Multi-account consolidated position context | ✅ Done |
| ETF asset-type detection | ✅ Done |
| Daily ticker suggester | ✅ Done |
| Daily log analyzer | ✅ Done |
| Phase 2 calibration (confidence-band + near-miss thresholds) | ✅ Done |
| Hypothesis harness suite (H1–H4) | ✅ Done |
| Near-miss registry automation | ✅ Done |
| Prompt A/B testing harness | ✅ Done (program terminated at the 3-A closeout; harness archived) |
| Phase 3-A live advisory run (H1 verdict locked; guardrail suspended) | ✅ Done (2026-07-06) |
| H1 feature-level implementation — S1 prior-signal state + D1 damping | ✅ Done (2026-07-06) |
| Triple-blend architecture (WS1) | 🟡 Phase 3-B |
| Q3 commodity-context modules (WS3) | ⏸️ Phase 3-B |
| SEC/EDGAR filing context (Form 4, 8-K, 10-Q/10-K MD&A, fundamentals) | ⏸️ Phase 3-C (entry criteria pre-registered) |
| Paper trading simulation | ⏸️ Phase 3 |
| Email daily digest | ⏸️ Backlog |
| Scheduled execution (Task Scheduler) | ⏸️ Backlog |
| Live trading with approval gate | ⏸️ Phase 4 |

---

## Disclaimer

This project is for personal research and educational purposes only. It does not constitute investment advice. Past performance of signals is not predictive of future results. The author is not a registered investment advisor. Use at your own risk.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built iteratively with assistance from Claude (Anthropic's AI assistant) over multiple development sessions. The collaborative process — from initial scaffolding through bug fixes around margin accounts, ETF fundamentals, and multi-account consolidation — is documented in the project's [commit history](https://github.com/Superb-Swift/claude-equity-bot/commits/main).
