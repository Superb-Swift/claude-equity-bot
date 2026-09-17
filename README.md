# Claude Equity Bot

> An AI-powered equity research and signal generation system that combines real-time brokerage data, SEC filing context, large language model analysis, and disciplined risk management to produce structured trading signals for human review.

![Phase](https://img.shields.io/badge/Phase-3--C%20EDGAR%20Advisory-blue)
![Language](https://img.shields.io/badge/Python-3.14-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active%20Development-success)
![Orders](https://img.shields.io/badge/Orders%20Placed-0-lightgrey)

---

## Overview

Claude Equity Bot ingests live portfolio data from **Charles Schwab's Trader API**, enriches it with recent news from **Finnhub** and **SEC EDGAR filing context** (Form 4, 8-K, and the latest 10-Q/10-K with a bounded MD&A extract), and asks **Anthropic's Claude** to generate structured BUY/SELL/HOLD signals. Every signal flows through a hardcoded risk engine and ends as advice for a human to act on or ignore. **The bot never places orders, and it never will:** advisory-only is permanent (`DP-T1`, ruled 2026-09-16), and `advisory_guard.py` fails the daily scan if an order path ever appears.

**No order has ever been placed.** Every phase has been advisory-only, by design.

The system is built around three principles:

1. **Discipline over speed** — a multi-phase rollout (dry run → live advisory → decision-support quality) with every bar pre-registered before it is read.
2. **Position awareness** — signals factor in cost basis, unrealized P&L, and tax-account context (Roth vs Individual).
3. **Transparency** — every signal carries reasoning, risk flags, a confidence score, and a full provenance tag chain the human can audit line by line.

---

## What this project actually is

The signal generator is the small half. The larger half is a **measurement apparatus built to find out whether the signal generator works** — and, more often, to catch the moments when it only appears to.

That apparatus has a specific shape:

- **Hypotheses are pre-registered before the data exists.** Endpoints, acceptance bars, sample sizes and robustness conditions are written down and dated *before* the cohort that will read them is generated. Amending an endpoint with data in view is treated as a defect in itself, and every amendment states explicitly whether it moved a bar.
- **Decision points are numbered, dated and ruled.** `DP-3C-j`, `DP-3C-o`, `DP-3C-t` and their siblings live in the source as comments beside the code they govern, so a rule and its rationale cannot drift apart.
- **Findings that make the project look good get the most scrutiny.** When a change improves an apparent result, the record says so in those words and forces a date-split rather than a pooled figure.
- **Wrong readings are corrected in place and visibly.** A retracted conclusion stays on the page next to its retraction, because the wrong sentence is usually the more instructive artifact.
- **Every reported figure carries a provenance mark.** `[V]` means independently recomputed from primary artifacts; `[?]` means asserted but not yet verified at source.

The result is a research record where negative results survive. A Phase-2-certified confidence-band guardrail **inverted out-of-sample and was retired**. The H4 data-quality gate **crossed its reopening bar and was demoted again one session later**. The triple-blend architecture (WS1) was **descoped** rather than reported as promising. These are the outcomes the phase discipline exists to produce, and they are all in `docs/`.

---

## Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Schwab API  │  │ Finnhub API  │  │  SEC EDGAR   │  │ Anthropic API│
│  quotes,     │  │  news        │  │  Form 4 /8-K │  │  Claude      │
│  positions   │  │  headlines   │  │  10-Q / 10-K │  │  signal gen  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                          main.py                             │
  │   multi-account orchestrator · phase flag · era stamp        │
  │   S1 prior-signal state · context_providers registry         │
  └───────────────────────────┬──────────────────────────────────┘
                              ▼
              ┌───────────────────────────────┐
              │        risk_engine.py         │
              │  D confidence damping, then   │
              │  CHECK 1-7 gates + human      │
              │  approval (permanent)         │
              └───────────────┬───────────────┘
                              ▼
       ┌──────────────────────────────────────────────┐
       │  signals_<date>.log  ·  master tracker.xlsx  │
       └───────────────────────┬──────────────────────┘
                               ▼
   ┌───────────────────────────────────────────────────────────┐
   │  REVIEW LAYER (read-only, writes nothing to the master)   │
   │  signal_scan · log_tracker_crosscheck · outcome_sanity    │
   │  h1_lag_trace · h4_dq_threshold · monitor_strip           │
   │  band_price · value_anchor · implied_return               │
   │  registries · parser + retired-criteria audits            │
   └───────────────────────────────────────────────────────────┘
```

**Every line of every signal carries its own provenance chain**, which is what makes the review layer possible:

```
H1[trail5d=+9.09%; closes=68.29>69.40>70.50>73.12>74.50]   ← price trajectory shown to the model
S1[prior=50,55,60,63,67; dconf=+17]                        ← the model's own last-5 confidences
D[raw=72; op=72; trail=+9.09%; damp=0]                     ← model-side vs operative confidence
B[sec=0.427; reg=-0.918; base=72; blend=67; blend_op=67]   ← shadow blend channel (descoped)
E[no filings]                                              ← EDGAR treatment actually delivered
```

Both the **raw (model-side)** and **operative (post-damping)** confidence are logged on every row, so the model's own behaviour stays measurable independently of the deterministic rules applied after it.

---

## Features

- **Multi-account portfolio integration** — aggregates positions across Roth IRA and Individual taxable accounts with weighted-average cost basis
- **Position-aware signals** — Claude sees cost basis, P&L, and which account holds the position before recommending anything
- **News context** — recent headlines per ticker via Finnhub
- **SEC EDGAR filing context (Phase 3-C)** — Form 4 insider transactions, 8-K material events with item codes, and the latest 10-Q/10-K with a bounded MD&A extract and an XBRL financial-statements block, delivered as a prompt section that touches no gate and no confidence channel
- **Asset-type awareness** — ETFs receive different fundamental analysis than equities
- **Risk engine** — confidence thresholds, position-concentration enforcement, data-quality minimums, and a permanent human-approval gate
- **Prior-signal state input (S1)** — the model receives its own last-5 signals and confidences per ticker, closing the statelessness gap behind the certified lag finding
- **Confidence damping (D)** — a deterministic post-model rule damps stale conviction into a material adverse trailing move; raw and operative confidence are both logged. The rule is unchanged since D1; the generation is **D2** since the 2026-08-31 H1 trailing-window correction (first D2 cohort 2026-09-01)
- **Forecast-free valuation layer** — market-vs-book anchoring and the value-driver identity run *backwards* (what ROE or growth must the market already believe?). Deliberately **off-prompt**: it produces no price target, feeds no signal, and touches no endpoint
- **Daily ticker suggester** — proposes new research candidates from portfolio gaps, market themes, and peer analysis
- **Audit-ready everything** — a daily cross-check reconciles the log against the master row by row at full precision; a parser audit proves every consumer tolerates the current tag format; a retired-criteria audit scans the source for rules that were retired but are still being cited

---

## Tech Stack

| Component | Purpose |
|---|---|
| **Python 3.14** | Core language |
| **schwab-py** | Charles Schwab Trader API client |
| **anthropic** | Claude API SDK |
| **finnhub-python** | News data |
| **python-dotenv** | Environment variable management |
| **openpyxl** | Reads/writes the tracking spreadsheet for every harness |
| **Pillow** | Monitor-strip PNG rendering and Excel embedding |
| **urllib / SEC EDGAR REST** | Filing retrieval (submissions, XBRL companyfacts, raw documents) |
| **OAuth 2.0** | Authentication with Schwab |
| **Git / GitHub** | Version control |

---

## Module Breakdown

### Core signal pipeline

| File | Responsibility |
|---|---|
| `main.py` | Orchestrator — pulls portfolios, dedupes the watchlist, coordinates signal generation; carries the phase flag and derives the generator-era stamp from the EDGAR flag so the two can never disagree; maintains S1 state each run |
| `schwab_client.py` | Data layer — Schwab auth, quotes, positions, account labeling |
| `news_client.py` | News layer — recent headlines per ticker from Finnhub |
| `claude_signal.py` | Signal layer — builds structured prompts (price trajectory, S1 prior-signal state, registered context sections) and parses Claude's JSON responses |
| `risk_engine.py` | Decision layer — the `CHECK 1`–`CHECK 9` gate sequence; hosts the damping rule (D2 era) and the `DampingConfig` / `RiskConfig` parameter stores |
| `context_providers.py` | Provider registry — the extension point prompt sections register against |
| `blend_engine.py`, `blend_providers.py`, `sector_map.py` | WS1 shadow blend (sector + regime channels) — logged and measured, **never drives the gate** |
| `signal_state.py`, `seed_signal_state.py` | S1 state persistence and one-shot re-seed from the tracker |
| `ticker_suggester.py` | Generative layer — proposes new research candidates |
| `analyze_log.py` | Analytics layer — daily digest of signals, confidence distributions, DQ breakdowns |
| `parse_log_to_tracker.py` | Export layer — converts a run's log into paste-ready tracker rows (phase-agnostic tag parsing) |

### EDGAR and the valuation layer (Phase 3-C)

| File | Responsibility |
|---|---|
| `edgar_client.py` | SEC filing provider — Form 4 / 8-K / 10-Q / 10-K retrieval, MD&A extraction, XBRL financial-statements block, on-disk accession cache, `--coverage` audit, and an EDGAR-time budget accumulator (`EDGAR_MAX_SECONDS`, default 120s) that bounds time spent *inside* the client rather than wall clock |
| `xbrl_sweep.py` | Full-watchlist XBRL extraction sweep with informational flags (split-vote, thin, XBRL-lag) |
| `edgar_parser_audit.py` | Pre-deploy audit — proves all four log consumers tolerate the live phase token, era label and `E[…]` tag before anything ships |
| `quote_dump.py` | Captures the raw Schwab `fundamental` block daily, so field semantics can be tested against live events |
| `fundamental_probe.py` | Targeted probe of Schwab fundamental-field behaviour |
| `value_anchor.py` | Forecast-free market-vs-book: MVA, M/B, BVPS, plus a balance-sheet identity check. Joins accession→ticker by **two independent routes that must agree**, and reports rather than guesses when they don't |
| `implied_return.py` | The value-driver identity run backwards — implied cost of equity, implied ROE, implied growth, with a per-name derivative saying which read the equation can actually speak to. DuPont decomposition; explicit accounting of why ROIC is not reported |
| `band_price.py` | Prices the fixed ±3% HOLD band per name, tests it against a one-parameter dispersion model, and monitors drift against the frozen volatility-tier table without ever re-cutting it |

### Research, validation and audit tooling

| File | Responsibility |
|---|---|
| `h1_lag_trace.py` | H1 confidence-update-lag tracer; two-channel (`--raw-from-logs` recovers the model-side confidence, `--suffix` keeps channel exhibits separate) |
| `h4_dq_threshold.py` | H4 data-quality-conditional threshold watchdog (promoted under DP-3C-x; monitoring only, status read from `rulings.py`) |
| `signal_scan.py` | One-day integrity read — run-integrity assertions, per-ticker channel table, channel reconciliation, cohort profile. Includes the era-change alarm (direction-aware) and the cohort-membership set-difference |
| `log_tracker_crosscheck.py` | Reconciles a run's log against the master at full precision, both directions |
| `outcome_sanity.py` | Guards the outcome closes: quote-vs-close, cross-horizon agreement, magnitude, dispersion, **Check G** (a close for a session that has not settled blocks the scan), and **Check F** (every cell against the machine-sourced log close) |
| `enter_closes.py` | Enters settled closes for one session into blank outcome cells by cell-scoped XML surgery; refuses unsettled sessions, never overwrites, backs up and writes a ledger line |
| `repair_outcome_close.py` | Repairs one close everywhere it resolves, with a backup and a one-line audit record per cell in `logs/outcome_close_repairs.log` |
| `fetch_closes.py` | Settled Schwab closes for one date to TSV — writes nothing to the master |
| `trading_calendar.py` | The NYSE session calendar, computed from rules and reconciled against the master's cohort dates; records pre-registered bot-absent sessions |
| `trail_basis_audit.py` | Regression gate for the H1 trailing window — every log since the 2026-08-31 fix must span completed sessions only |
| `rulings.py` | Settled decision-point registry (each entry cites its ruling document) plus an append-only readings log, so "N consecutive readings" is mechanical rather than recalled |
| `signal_logs.py` | Recursive signals-log discovery across archived month folders, `Retired/` excluded and counted |
| `episodes.py` | The one episode-coalescing rule (consecutive cohorts), the KEEP-70 episode basis and the blind DP-3C-w prospective-arm counter |
| `discovery_scan.py` | Structural and HOLD-population discovery reads; `--progress` prints the pre-registered prospective arms as counts only until their read dates |
| `shadow_damper.py` | Offline, never-shown-to-the-model confidence-change damper (λ fixed at 0.5) for prospective arm PR-3 |
| `advisory_guard.py` | Fails the scan if any order-placing code appears or human approval is switched off (DP-T1) |
| `monitor_strip.py` | Open-questions dashboard — one fixed-width strip of every live gate, its bar and its state; embeds into a generated report copy, never the master |
| `build_near_miss_registry.py` | Rebuilds the near-miss BUY registry (the KEEP-70 evidence base) from the master |
| `build_actionable_registry.py` | Rebuilds the gate-clearing directional ledger, with the mandatory era split |
| `retired_criteria_audit.py` | Scans the source for criteria that were retired but are still cited in live-rule grammar |
| `phase_dispatch_audit.py` | Verifies the phase handler dispatches correctly across phase labels |
| `blend_eval.py` | WS1 gate-flip evaluation (blend vs base) — descoped, retained for reproducibility |
| `docs/rebuild_notes.py` | Rebuilds the running analyst-notes record from its dated splice entries |

### Runners

| Script | What it does |
|---|---|
| `run_daily.bat` | S1 state seed → `main.py` → `analyze_log.py` → tracker rows |
| `scan.bat` | `trading_calendar` → `signal_scan` → `log_tracker_crosscheck` → `outcome_sanity` → `trail_basis_audit` → `advisory_guard` — the integrity pass |
| `selftest.bat` | Every `--selftest`, each with a negative case, as one pass/fail |
| `run_daily_review.bat` | Both lag tracers × both channels → H4 watchdog → near-miss registry → actionable registry → monitor strip embed |
| `value.bat` | `quote_dump` → `band_price` → `value_anchor` → `implied_return` — the valuation pass, with an artifact guard that fails loudly if an exhibit was not written |
| `monitor.bat` | Standalone monitor-strip refresh |

Retired harnesses (`h2_direction_asymmetry.py`, `h3_thesis_stability.py`, `guardrail_trace.py`, `t2_check.py`, `run_ab_test.bat`, `run_weekly_review.bat`) live under `Retired/` for archival reproducibility. All harnesses accept `--since` / `--until` for phase-scoped analysis.

---

## Sample Signal Output

```
============================================================
  SIGNAL: BUY  |  Ticker: NTR  |  Confidence: 72%
============================================================
  Reasoning   : NTR has surged ~9% over the last five sessions,
                breaking above the cost basis, with upward momentum
                confirming the gradual confidence build across prior
                sessions. Raised guidance despite nitrogen volume
                headwinds signals pricing power...
  Bull Case   : Continued fertilizer price recovery, guidance upgrades...
  Bear Case   : Sliding nitrogen volumes could accelerate if global...
  Time Frame  : MEDIUM
  Data Quality: HIGH
  Position    : Roth IRA shares (6 @ $70.16) should be held or added
                tax-free on dips, while Individual account gains
                ($42.80) would be taxable on sale...
  Risk Flags  : Nitrogen volume decline despite guidance raise,
                Volume well below 10-day average (~380K vs ~2.9M),
                Stock has run 9% in 5 days — short-term overbought risk,
                RISK-ENGINE: 15 open positions at or above the monitoring
                cap of 8 (CHECK 6, non-blocking per DP-3C-o)
============================================================
  Risk: REJECTED — Already holding NTR and ALLOW_POSITION_ADD is False
============================================================
```

*(When damping engages, the header shows both channels: `Confidence: 35% (raw 38%)`.)*

---

## Sample Run-Integrity Block

Emitted by `signal_scan.py` on every session. This is the artifact the daily review is scored against:

```
==============================================================================
SIGNAL SCAN - 2026-09-16  (era A-S1D2-B1-E1, 29 rows)
==============================================================================

RUN INTEGRITY
  [OK  ] cohort membership UNCHANGED since 2026-09-15 (29 names; count 29 vs 29)
  [OK  ] era stamp A-S1D2-B1-E1 - EDGAR live (3-C), H1 window corrected
  [OK  ] era unchanged since 2026-09-15 (A-S1D2-B1-E1, 29 rows)
  [OK  ] EDGAR sections on 20/29 row(s); 9 dark: AG, AIQ, CBRS, NTR, QQQ,
         SCHD, SPY, VTI, XLU
  [OK  ] no covered name degraded (fin=degraded absent)
  [OK  ] confidence_raw present on all rows
  [OK  ] regime_score uniform at -0.021
  [OK  ] regime_score within [-1, +1]
  [OK  ] regime_score step -0.180 (0.159 -> -0.021) vs prior session 2026-09-15
  [OK  ] THETA source: risk_engine.DampingConfig.THETA

CHANNEL RECONCILIATION
  [OK  ] json.confidence == D.op                              29/29
  [OK  ] json.confidence_raw == D.raw                         29/29
  [OK  ] D.raw == B.base                                      29/29
  [INFO] D.op == B.blend_op  [INFO: WS1 descoped, no disposition] 27/29
```

Three states are kept deliberately distinct throughout: **OK** (checked, passed), **FAIL** (checked, failed), and **NOCHK** (*could not be checked*). A tool that reports a pass when it could not run the check is treated as a defect class in its own right.

---

## Phased Rollout

| Phase | State | Description |
|---|---|---|
| **Phase 1** | ✅ Complete | Foundation — auth, quote retrieval, single-account positions |
| **Phase 2** | ✅ Complete | Read-only calibration dry run (19 trading days, concluded 2026-06-12) — thresholds calibrated, no orders placed |
| **Phase 3-A** | ✅ Complete | Live advisory run (14 sessions, concluded 2026-07-06). H1 lag verdict locked; the Phase-2-certified confidence-band guardrail failed to reproduce out-of-sample and was retired before anything relied on it; H2/H3 descoped; the A/B program terminated |
| **Phase 3-B** | ✅ Complete | Advisory-only development — WS1 triple-blend (built, measured, **descoped**), the H1 feature-level implementation (S1 prior-signal state + D1 damping, era `A-S1D1-B1`) |
| **Phase 3-C** | 🟢 **Current** | EDGAR filing context live 2026-08-03; first admitted measurement cohort 2026-08-13; era `A-S1D1-B1-E1`, then `A-S1D2-B1-E1` from 2026-09-01 after the H1 trailing-window correction (cohorts either side are not pooled on model-side channels). E4 endpoints pre-registered before go-live; a forecast-free valuation layer built off-prompt. Still **no orders placed** |
| **Phase 4** | ⏸️ Planned | **Decision-support quality** (re-scoped 2026-09-16 under `DP-T1`). Advice-quality gates carried over from the old execution register: every declared rule enforced or labelled, with tests shown to fail; the approval hand-off read by every parser; per-account and headline verdicts that never disagree silently; a demonstrated SELL path on held names (`DP-3C-s`); and a pre-registered skill yardstick. Execution-only gates (loss limit, kill switch, paper execution) are **retired** |

**On the terminal intent, stated plainly because the record now does:** `T1` — advisory-only, the human decides — is the **permanent ceiling** (`DP-T1`, ruled by the operator 2026-09-16). It was previously a phase gate on the way to execution. The record argued against that path: no price-based skill has been shown, the effective sample is small, confidence *changes* point the wrong way, and directional output is one-sided. The project's goal is now advice good enough to be worth reading. Reopening execution would need a new ruling and every retired gate reinstated in full.

---

## Risk Engine Configuration

The risk engine is a backstop against overconfident or poorly-calibrated signals. Every signal passes a numbered `CHECK 1`–`CHECK 9` sequence in `evaluate_signal`. Current settings, **annotated with what is actually enforced** rather than what is configured:

```python
MIN_CONFIDENCE_BUY     = 70%      # ENFORCED  — BUY signals need ≥70% confidence
MIN_CONFIDENCE_SELL    = 65%      # ENFORCED  — SELL signals need ≥65% confidence
MIN_DATA_QUALITY       = "MEDIUM" # ENFORCED  — LOW-quality signals rejected
MAX_POSITION_PCT       = 5.0%     # ENFORCED  — since 2026-08-11 (CHECK 6b)
ALLOW_POSITION_ADD     = False    # ENFORCED  — no adding to existing positions
REQUIRE_HUMAN_APPROVAL = True     # ENFORCED  — permanent, not a phase gate
MAX_OPEN_POSITIONS     = 8        # FLAGS ONLY — non-blocking since 2026-08-11
DAILY_LOSS_LIMIT_PCT   = 2.0%     # NOT ENFORCED — inert by design under DP-T1 (see below)
```

**CHECK 6 was demoted and CHECK 6b was enforced on 2026-08-11 (`DP-3C-o`).** `MAX_OPEN_POSITIONS` is a *monitoring-burden* cap, not a risk cap — by its own configuration comment it buys monitoring convenience by accepting concentration risk, and a rule that increases the risk it is filed under should not hold a veto. It now records a non-blocking flag. In its place `MAX_POSITION_PCT` — which had been printed as an "Active Rule" on every signal while being enforced nowhere at evaluation time — is now genuinely enforced at the gate.

That ruling carries a preserved finding, quoted in the source so it cannot be erased: *under the previous cap the risk engine approved **zero** directional signals across 57 cohorts.* Because the amendment makes the approval rate look better **by construction**, every reading of approval counts must date-split on 2026-08-11 rather than pool across it.

> ### `DAILY_LOSS_LIMIT_PCT` is declared and not enforced — by design since `DP-T1`
>
> `CHECK 8`'s body is `if sig == "BUY": pass`. It was tracked as **D-5**, *latent* under advisory-only and **highest severity under execution**. Under the permanent advisory ruling there is no execution for a loss limit to stop, so D-5 and gate X6 are retired. The Active Rules banner now labels the line *declared, not enforced*, so the rule no longer advertises something it does not do — the failure class the old `X1` was written to close.

### Confidence damping (D; generation D2 since 2026-08-31)

A deterministic layer applied **before** the gates (`risk_engine.apply_conf_damping`):

```python
THETA = 5.0   # % trailing 5-day move before damping engages
K     = 1.5   # confidence points removed per % beyond THETA
CAP   = 15    # maximum points removed in one session
FLOOR = 35    # damping never pushes below this floor
```

Damping only ever lowers confidence, and **both channels are logged on every line** — so the model-side signal remains measurable even where a deterministic rule has changed the operative value.

---

## Measurement Discipline

Everything below is live and documented in `docs/`. **Dispositions are stated here; current readings are not**, because they move as cohorts resolve.

### Pre-registration

E4 — the endpoint set measuring whether EDGAR context changes anything — was pre-registered **before** the first EDGAR-live cohort was generated, and has been amended three times to v1.3. Each amendment states explicitly that it moved no threshold, arm, population, sample size or robustness condition, because amending an endpoint is exactly where a bar slips quietly.

Its supporting instruments were frozen the same way: the **volatility-tier table** that supplies E4-2's comparison groups was cut and frozen before the E4 clock started, precisely so a control group could never be fitted to its own data. It has drifted since. **It is reported, not re-cut.**

### Admissibility

`DP-3C-t` defines, in advance, what disqualifies a cohort — with a one-line test: *is the artifact wrong, or is the reader wrong?*

- **COHORT-LEVEL** — the artifact is wrong (a malformed tag in the log, a mixed-period figure, a master row that doesn't reconcile). The cohort is tagged SHAKEDOWN and excluded.
- **NAME-LEVEL** — a covered name did not receive the treatment. Its rows are marked DEGRADED; the cohort survives.
- **READ-BLOCKING** — a *tool* cannot read correct inputs. The cohort is **not** excluded; the read is **deferred** until the tool is fixed and re-run clean against that cohort's own bytes. The deferral is binding and is not a pass.

### Live gates and their dispositions

| Gate | What it asks | Disposition |
|---|---|---|
| **KEEP-70** | Would the BUY gate have paid at a lower threshold? | **Supported** on the row basis; not supported on the episode basis. The correct basis is **unruled**, so both are always reported |
| **H4** | Should the confidence threshold be conditional on data quality? | **Demoted.** Crossed its reopening bar once, then failed on the next reading — the two-consecutive-readings rule has since outlived the pass that would have started a promotion |
| **G1 (WS2)** | Does confidence respond to a material adverse move within 2 sessions? | **Insufficient test conditions.** The stated bar is met on every episode observed; the pre-registered sample size is not. The bar is not lowered |
| **G2 (WS1)** | Does the blended confidence beat the base? | **Descoped.** Measured, found unscoreable in general form, and closed rather than reported as promising |
| **Q1 guardrail** | Does the 50–59% confidence band lead 60–69%? | **Retired.** Certified in Phase 2, inverted out-of-sample in Phase 3-A, and retired before any decision relied on it |
| **E4** | Does EDGAR context change accuracy, data quality, or confidence response? | **Open**, mid-collection, no disposition read at any sample size |

### Structural safeguards

- **Era stamping** — the EDGAR flag and the generator-era label are derived from one variable, so a treated cohort can never be filed as a control. A direction-aware alarm distinguishes *losing* the treatment from *restoring* it, because those need opposite advice.
- **Three coverage denominators** — pre-registered, practical, and ADJACENT-eligible — reported side by side, because two names in the covered set are commodity trusts that file documents containing no events and almost no financial statements.
- **No pooling across a rule change.** The gate-clearing ledger date-splits on `DP-3C-o` and prints the instruction in its own header.
- **Nothing in the valuation layer touches the prompt** (`DP-V1`). It reads and reports; it cannot influence a signal.

---

## Setup

### Prerequisites

- Python 3.14+
- A Charles Schwab Developer Portal account with API access
- An Anthropic API key
- A Finnhub API key (free tier sufficient)
- A contact string for the SEC EDGAR User-Agent header (required by SEC fair-access policy)

### Installation

```bash
git clone https://github.com/Superb-Swift/claude-equity-bot.git
cd claude-equity-bot

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Everything: the bot runtime, the analysis tooling and the monitor-strip renderer
pip install -r requirements.txt

# Check the install: every self-test, each with a failing case (Windows)
selftest.bat
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
SEC_USER_AGENT=Your Name your@email.com    # mandatory for any EDGAR fetch
ROTH_ACCOUNT_NUMBER=your_roth_account_number
INDIVIDUAL_ACCOUNT_NUMBER=your_individual_account_number
```

Account numbers go in `.env` only. `schwab_client.py` reads `ROTH_ACCOUNT_NUMBER` and `INDIVIDUAL_ACCOUNT_NUMBER` through `os.getenv` and builds `ACCOUNT_LABELS` / `ACTIVE_ACCOUNTS` from them. **Never put an account number in a source file** — source files are tracked and this repository is public.

**EDGAR is off by default and is turned on per-session, deliberately:**

```bash
set EQUITY_EDGAR=1          # Windows — enables the filing provider AND the -E1 era stamp
```

The flag and the era stamp move together by construction. Optional: `EDGAR_MAX_SECONDS` (default 120) bounds time spent inside the EDGAR client; `EDGAR_CACHE_DIR` (default `edgar_cache`) relocates the accession cache.

### Run

```bash
python main.py                # Generate signals
python analyze_log.py         # Daily digest

# Windows convenience runners
run_daily.bat                 # state seed + signals + analyzer + tracker rows
scan.bat                      # integrity pass (scan + cross-check + resolution sanity)
run_daily_review.bat          # lag tracers + H4 + registries + monitor strip
value.bat                     # valuation pass (quotes + band + anchor + implied return)

# Pre-deploy audits
python edgar_parser_audit.py  # every log consumer tolerates the live tag format
python signal_scan.py --selftest
python edgar_client.py --selftest
python retired_criteria_audit.py

# EDGAR coverage — computed against the live CIK map, never asserted
python edgar_client.py --coverage

# Phase-scoped analysis (any harness)
python h1_lag_trace.py --since 2026-06-15

# WS2 acceptance reads (post-deploy, both channels)
python h1_lag_trace.py --since 2026-07-07 --ticker WMT --suffix _3B
python h1_lag_trace.py --since 2026-07-07 --ticker WMT \
       --raw-from-logs "logs\signals_*.log" --suffix _raw_3B
```

---

## Design Principles

### Why phase discipline?

Algorithmic trading systems most often fail not because the strategy is wrong, but because the operator skipped validation. Phase 3-A proved the point in practice: a Phase-2-certified edge inverted out-of-sample and was caught — and retired — by the advisory run, before any capital could have relied on it.

### Why pre-registration?

Because a threshold chosen with the data in view is not a threshold, it is a description. Every acceptance bar in this project is dated, and every amendment states whether it moved one. When a bar has not been set, the record says so rather than inventing one at read time — a review that scored an endpoint against a bar that had never been set is itself a documented finding.

### Why does the record correct itself in public?

A retracted conclusion stays next to its retraction. The reasoning is that the *wrong* reading usually explains more about the system than the right one, and deleting it removes the only evidence of how a plausible mistake was made. Several of the most useful findings in `docs/` are corrections of earlier findings in the same file.

### Why human approval?

The bot never places an order. Every trade is the operator's decision, taken outside the system (`DP-T1`). This is permanent architecture, enforced by `advisory_guard.py` in the daily scan. The bot is a research assistant, not an autopilot.

### Why position-aware?

A 5% gain in a Roth IRA is structurally different from a 5% gain in a taxable account. Selling appreciated stock in the Roth has no tax consequence; doing so in the Individual account triggers capital gains. Claude receives per-account breakdowns so its reasoning can be tax-aware.

---

## Roadmap

| Feature | Status |
|---|---|
| Multi-account portfolio integration | ✅ Done |
| News context (Finnhub) | ✅ Done |
| ETF asset-type detection | ✅ Done |
| Daily ticker suggester + log analyzer | ✅ Done |
| Phase 2 calibration (confidence-band + near-miss thresholds) | ✅ Done |
| Hypothesis harness suite (H1–H4) | ✅ Done |
| Near-miss + actionable registry automation | ✅ Done |
| Prompt A/B testing harness | ✅ Done (program terminated at the 3-A closeout; archived) |
| Phase 3-A live advisory run (H1 verdict locked; guardrail retired) | ✅ Done (2026-07-06) |
| H1 feature-level implementation — S1 prior-signal state + D1 damping | ✅ Done (2026-07-06) |
| Triple-blend architecture (WS1) | ✅ Built and measured — **descoped 2026-07-31** |
| SEC/EDGAR filing context (Form 4, 8-K, 10-Q/10-K MD&A, XBRL) | ✅ Live 2026-08-03 |
| E4 endpoint pre-registration + frozen volatility-tier table | ✅ Done (before go-live) |
| Daily integrity pass (scan + cross-check + resolution sanity) | ✅ Done |
| Forecast-free valuation layer (off-prompt) | ✅ Done (2026-08-17) |
| EDGAR-time budget accumulator (`DP-3C-j`) | ✅ Done (2026-08-20) |
| Cohort-membership check (retires the hardcoded cohort size) | ✅ Done (2026-08-21) |
| E4 read-out and Phase 3-C exit review | 🟢 In progress |
| Q3 commodity-context modules (WS3) | ⏸️ Deferred |
| Machine entry of outcome closes with a settlement gate (`enter_closes.py`, Check G) | ✅ Done (2026-09-16) |
| Prospective arms PR-1…PR-4 and an offline confidence-change damper (`DP-3C-ah`) | 🟢 Collecting (from 2026-09-17) |
| SELL path on held names (`DP-3C-s`) · checkable HOLD ranges | ⏸️ Phase 4 (decision-support quality) |
| Email daily digest | ⏸️ Backlog |
| ~~Paper execution (X7) · loss limit and kill switch (X6) · live trading~~ | ❌ Retired by `DP-T1` (2026-09-16) — advisory permanently |

---

## Disclaimer

This project is for personal research and educational purposes only. **It does not constitute investment advice.** No figure produced by this system is a valuation, a price target, or a recommendation. Past performance of signals is not predictive of future results. The author is not a registered investment advisor. Use at your own risk.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built iteratively with assistance from Claude (Anthropic's AI assistant) over multiple development sessions. The collaborative process — from initial scaffolding through the EDGAR integration, the pre-registered endpoint apparatus, and a long run of defects found in the review layer rather than the test suite — is documented in `docs/` and in the project's [commit history](https://github.com/Superb-Swift/claude-equity-bot/commits/main).

> *"The first live run of anything is where the defects are. Not the test suite."*
> — from the project's own analyst record, after an alarm's first live run found a defect in the alarm
