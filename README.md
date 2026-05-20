# Claude Equity Bot

> An AI-powered equity research and signal generation system that combines real-time brokerage data, large language model analysis, and disciplined risk management to produce structured trading signals for human review.

![Phase](https://img.shields.io/badge/Phase-2%20Dry%20Run-yellow)
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
              │      + ticker suggester       │
              └──────────────────────────────┘
```

---

## Features

- **Multi-account portfolio integration** — Aggregates positions across Roth IRA and Individual taxable accounts, with weighted-average cost basis calculations
- **Position-aware signals** — Claude sees your cost basis, P&L, and which account holds the position before generating recommendations
- **News context** — Recent headlines are fetched per ticker via Finnhub and included in the analysis prompt
- **Asset-type awareness** — ETFs receive different fundamental analysis than equities (P/E is suppressed for ETFs since broker-reported values are unreliable for fund products)
- **Risk engine** — Confidence thresholds, position-size caps, data-quality minimums, and human-approval gates prevent overconfident or low-quality signals from triggering action
- **Daily ticker suggester** — Claude analyzes portfolio gaps, market themes, and peer companies to suggest new research candidates each day
- **Audit-ready logging** — Every signal is logged with reasoning, risk flags, and token usage; a daily analyzer produces a one-page digest
- **Phased rollout** — Currently operating in Phase 2 (read-only dry runs), with Phase 3 (paper simulation) and Phase 4 (live trading with approval gates) planned

---

## Tech Stack

| Component | Purpose |
|---|---|
| **Python 3.14** | Core language |
| **schwab-py** | Charles Schwab Trader API client |
| **anthropic** | Claude API SDK |
| **finnhub-python** | News and fundamentals data |
| **python-dotenv** | Environment variable management |
| **OAuth 2.0** | Authentication with Schwab |
| **Git / GitHub** | Version control |

---

## Module Breakdown

| File | Responsibility |
|---|---|
| `main.py` | Orchestrator — pulls portfolios, dedupes the watchlist, coordinates signal generation across modules |
| `schwab_client.py` | Data layer — authenticates with Schwab, fetches quotes and positions, handles account labeling |
| `news_client.py` | News layer — fetches recent headlines per ticker from Finnhub |
| `claude_signal.py` | Signal layer — builds structured prompts and parses Claude's JSON responses |
| `risk_engine.py` | Decision layer — applies hardcoded rules to approve or reject signals |
| `ticker_suggester.py` | Generative layer — proposes new tickers based on portfolio gaps, market themes, and peer analysis |
| `analyze_log.py` | Analytics layer — produces a daily digest of signals, confidence distributions, and data quality breakdowns |

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
| **Phase 2** | 🟡 Current | Read-only dry runs — full signal pipeline, no orders placed |
| **Phase 3** | ⏸️ Planned | Paper simulation — simulated order placement, no real money |
| **Phase 4** | ⏸️ Planned | Live trading — real orders with mandatory human approval |

---

## Risk Engine Configuration

The risk engine acts as a backstop against overconfident or poorly-calibrated signals. Current settings:

```python
MIN_CONFIDENCE_BUY   = 70%      # BUY signals need ≥70% confidence
MIN_CONFIDENCE_SELL  = 65%      # SELL signals need ≥65% confidence
MAX_POSITION_PCT     = 5.0%     # No single position above 5% of portfolio
MAX_OPEN_POSITIONS   = 30       # Cap on total concurrent holdings
DAILY_LOSS_LIMIT     = 2.0%     # Halt new BUYs if daily portfolio loss exceeds 2%
ALLOW_POSITION_ADD   = False    # Disallow adding to existing positions
REQUIRE_HUMAN_APPROVAL = True   # Always require human approval (Phase 4+)
MIN_DATA_QUALITY     = "MEDIUM" # Reject LOW-quality signals automatically
```

These thresholds will be refined empirically after 2-3 weeks of Phase 2 data collection.

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

# Install dependencies
pip install schwab-py anthropic finnhub-python python-dotenv flask cryptography
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
python main.py            # Generate signals
python analyze_log.py     # Produce the daily digest
```

---

## Design Principles

### Why Phase Discipline?

Algorithmic trading systems most often fail not because the strategy is wrong, but because the operator skipped validation. Phase 2 forces a minimum of 2-3 weeks of observed signals before any simulated trading begins. Phase 3 forces a similar period of paper trading before any real capital is at risk.

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
| SEC EDGAR fundamentals (Form 4, 8-K, earnings) | ⏸️ Phase 2.5 |
| 10-Q management discussion summaries | ⏸️ Phase 3 |
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
