# Phase 3 Design Concepts — Reference Frameworks \& "Triple Blend" Vision

**Status:** Active design notes — DO NOT IMPLEMENT during Phase 2
**Created:** 2026-05-29 (Phase 2, Day 9 of 19)
**Read again:** Post-Phase-2-review (after Fri 2026-06-12)

\---

## Purpose of This Document

Phase 2 of the Claude Equity Bot project is the read-only calibration
dry-run. While running Phase 2, we encountered two external reference
frameworks worth studying:

1. **The Claude Portfolio** (@theaiportfolios on X) — deep per-position
thesis with stateful tracking and forward catalysts
2. **The Grok Portfolio** (same operator, Dr. Lopez-Lira / AI Finance
Labs) — portfolio-level architecture with sector ETFs, cross-asset
allocation, and explicit risk discipline

We are deliberately NOT modifying the bot during Phase 2 to avoid
contaminating the calibration dataset. But the design thinking
deserves capture so it isn't lost — and so Phase 2's remaining \~10
trading days can include additional observation of how these two
frameworks perform in changing market conditions.

This document is the dedicated home for that design thinking. It
should be read AFTER Phase 2 closes on 2026-06-12, with the locked
worksheet verdicts in hand.

\---

## The Three Reference Frameworks

### Framework A: Our Bot (Current — Phase 2)

**What it is:** Stateless daily per-ticker analysis. Reads news +
quotes for 19 held tickers + 5 scouts, produces BUY/SELL/HOLD signals
with confidence scores, bull/bear cases, risk flags, and data quality
ratings. Risk Engine then applies hard thresholds (BUY ≥70%, SELL ≥65%).

**Strengths:**

* Disciplined daily cadence
* Per-position depth (cost basis, account type, P\&L all in prompt)
* Confidence calibration measurable and currently TRENDING TOWARD VALIDATED
* Already includes sector ETF holdings (XLU, SCHD, AIQ) and broad-market
scouts (SPY, QQQ, VTI)
* Internal diagnostics richer than what either reference framework
publishes publicly

**Limitations:**

* No memory across days (stateless)
* No price targets — bull/bear cases are qualitative narratives
* No forward catalyst commitment
* No position sizing logic — sizes are historical artifacts
* No stop-loss / kill condition
* No portfolio-level constraints (correlation, sector weight, drawdown)
* No cross-asset exposure (equity-only)

### Framework B: The Claude Portfolio

**What it is:** Public AI-managed portfolio on Autopilot copy-trading
platform. $50K seed, launched April 2026, fully autonomous (no human
override). Style is concentrated single-name with deep written
commentary.

**Source:** @theaiportfolios on X · marketplace.joinautopilot.com/landing/5/950048

**Reference post (ServiceNow / NOW):**

* Position opened 2026-04-10 near $88
* Up \~39% when commentary published
* Thesis: "AI capability shipping vs AI deployment governance are
different timelines on different layers. ServiceNow is the layer
governance happens on."
* Mark-to-thesis: "Reached my base case this week"
* Forward catalyst: "Late-July report, where the AI revenue either
confirms the move or it doesn't"

**Borrowable design patterns:**

1. **Stateful thesis tracking** — entry date, entry price, original
thesis stored and referenced on subsequent days
2. **Probability-weighted price targets** — base/bear/bull cases with
specific price levels, not just qualitative narratives
3. **Forward catalyst as commitment device** — pre-committed
re-evaluation date/event
4. **First-person voice** — "How I read my own position, your call
is your own"
5. **Self-aware tone** — acknowledges contradictions and complexity
instead of hedging into mush

**Performance reality:**

|Metric|Value|
|-|-|
|First 2 months return|+2.6%|
|SPY same window|+8.3%|
|Verdict|UNDERPERFORMING benchmark|

> ANALYST NOTE: The NOW call is a winning trade inside an
> overall losing portfolio relative to SPY. Borrow the \\\*structure\\\*
> of the reasoning, not the assumption that the structure is
> producing alpha.

### Framework C: The Grok Portfolio

**What it is:** Same operator as Claude Portfolio. Different architecture.
Concentrated but diversified — 15 positions across sector ETFs,
cross-asset (bonds), mega-cap quality, and defensive single names.

**Source:** marketplace.joinautopilot.com/landing/5/568906

**Current holdings (15 positions):**

|Category|Tickers|Weight|
|-|-|-|
|Sector ETFs|XLV, XLK, XLP, ITA|\~27% of book|
|Cross-asset (bonds)|TLT|\~7%|
|Mega-cap tech/AI|NVDA, AVGO, MSFT, ORCL, MA|Significant|
|Defensive single names|LLY, COST, WM, CBOE, LMT|Sized for stability|

**Borrowable design patterns:**

1. **Sector ETF backbone** — diversified factor exposure as core,
not just thematic dabbling
2. **Cross-asset allocation** — TLT for duration/defensive ballast
3. **Explicit position sizing** by conviction (per Pareto Investor
commentary — sizes are not equal)
4. **Stop-loss / kill conditions** stated upfront
5. **Portfolio correlation awareness** — avoid concentration risk
from correlated single names
6. **Adaptive theme rotation** — exit losers, double down on winners,
pivot to new themes

**Performance reality:**

|Metric|Value|Source|
|-|-|-|
|First 9 months return|+59%|Yahoo Finance reporting|
|S\&P 500 same window|+36%|Benchmark|
|YTD return (alt window)|+17.16%|Composer.trade|
|Max drawdown|9.07%|Composer.trade|
|Verdict|OUTPERFORMING benchmark||

> ANALYST NOTE: The 59% number is being marketed publicly and
> can't be independently audited (no access to execution prices,
> slippage, fees, selection methodology). One operator running
> multiple AI-driven portfolios with different headline returns
> is a SETUP that's worth understanding before treating any
> single number as definitive evidence of methodology superiority.

\---

## The "Triple Blend" Vision

User envisioning Phase 3 as a synthesis, not a wholesale adoption of
any one framework. Here is how the borrowable patterns map across
the three reference frameworks:

### Architecture Layer (Borrow From: Grok)

|Element|Detail|Why It's a Grok Strength|
|-|-|-|
|Sector ETF backbone|XLU, XLV, XLK, ITA, XLP, etc. as core holdings|Diversified factor exposure reduces idiosyncratic risk|
|Cross-asset overlay|TLT or similar for duration/defensive ballast|Smooths portfolio variance across regimes|
|Position sizing by conviction|High-conviction names get larger positions|Reflects information advantage where it exists|
|Target portfolio weights|Each sector + each conviction tier has a target band|Prevents drift; forces rebalancing discipline|

### Reasoning Layer (Borrow From: Claude Portfolio)

|Element|Detail|Why It's a Claude Portfolio Strength|
|-|-|-|
|Stateful thesis|Per-ticker thesis stored across runs|Continuity of reasoning; mark-to-thesis possible|
|Base/bear/bull price targets|Specific prices at specific time horizons|Quantifies "right" vs "wrong"|
|Forward catalyst|Pre-committed re-evaluation date|Discipline against narrative drift|
|First-person conviction voice|Bot writes as if it owns the capital|Reduces hedged institutional non-answers|
|Public-style commentary|Daily output reads like a portfolio letter|Forces clarity of thinking|

### Risk Layer (Borrow From: Grok + Discipline)

|Element|Detail|Why It Matters|
|-|-|-|
|Explicit kill condition|Price OR event that invalidates the thesis|Exit without needing a SELL signal|
|Drawdown limit|Portfolio-level max drawdown trigger|Forces deleveraging before catastrophe|
|Correlation awareness|Track sector/factor exposure across positions|Prevents accidental concentration|
|Theme rotation log|Track active themes and their performance|Adaptive — exit failed themes|

### What Stays From Our Current Bot (Framework A)

|Element|Why Keep|
|-|-|
|Daily cadence|Already disciplined; calibrated through Phase 2|
|Per-position depth with cost basis + account type + P\&L|Tax-efficient reasoning is unique to our setup|
|Risk Engine thresholds (post-Phase-2-tuning)|Hard guards independent of model output|
|Internal analyst\_notes diagnostics|Far richer than either reference publishes publicly|
|Cohort analysis methodology|Calibration framework is our genuine strength|

\---

## Phase 3 Hypotheses (Updated Through Today's Thinking)

The Decision Worksheet v3 documents 4 hypotheses based on Phase 2
evidence. Reference-framework analysis adds 2 more:

|#|Hypothesis|Source|Test Design (Sketch)|
|-|-|-|-|
|1|3-5 day confidence update lag|Phase 2 (WMT/GM)|Add prior-5-day price input|
|2|Direction asymmetry (loss > gain reactivity)|Phase 2 (WMT vs GM)|A/B symmetric framing prompts|
|3|Intraday news sensitivity|Phase 2 (AM/PM 5/29)|"Stable thesis" prompt language|
|4|DQ-conditional confidence threshold|Phase 2 (HIGH-DQ near-misses)|DQ-stratified threshold rules|
|5|Stateful thesis tracking|Claude Portfolio|Persistent positions\_state.json|
|6|Portfolio-level architecture (sector + cross-asset + sizing)|Grok Portfolio|Add allocation layer above signal layer|

> ANALYST NOTE: Hypotheses 1-4 are well-grounded in our own
> Phase 2 data. Hypotheses 5-6 are framework-borrowed and not yet
> validated against our portfolio. Phase 3 prioritization should
> probably begin with 1-4 (validated by our data) and treat 5-6
> as larger structural experiments to scope after the prompt-level
> hypotheses are tested.

\---

## Open Design Questions

These are unresolved and should be revisited at Phase 3 kickoff:

### Q1 — How concentrated should the book be?

|Option|Holdings|Style|
|-|-|-|
|(a) Concentrate further|10-15 positions, larger sizes|Claude Portfolio style|
|(b) Maintain current|\~25 positions current|Status quo|
|(c) Diversify wider|30-50 positions with sector ETF core|Grok Portfolio style|

User's portfolio is already at (b). Moving to (c) is the closer move
if Grok's outperformance attribution is real.

### Q2 — Cross-asset exposure: yes or no?

Adding bonds (TLT or similar) changes the bot's design surface
substantially. The bot would need to reason about rates, duration,
and inflation — domains we haven't tested. May warrant a Phase
3-A sub-phase.

### Q3 — Stateful or rebuild-from-scratch each day?

Stateful thesis tracking means daily prompts include yesterday's
thesis. Two failure modes:

1. **Anchoring** — Claude refuses to update theses when wrong
2. **Drift** — Claude updates theses too readily, losing the
commitment-device value

Both are testable in Phase 3 but require designing the experiment.

### Q4 — Auto-execute or remain advisory?

Phase 2 is read-only by design. Even with a "triple blend" Phase 3,
should the bot auto-execute approved BUYs/SELLs, or remain advisory?

This is fundamentally a risk-tolerance question independent of
methodology. Phase 3 design should default to advisory (consistent
with Phase 2's conservatism) and only loosen execution rules after
Phase 3 has its own calibration data.

### Q5 — How does the Risk Engine evolve?

Current Risk Engine has hard thresholds:

* BUY confidence ≥ 70%
* SELL confidence ≥ 65%
* Max position size 5% of portfolio
* Max 8 open positions
* Human approval required

Phase 3 hypothesis #4 (DQ-conditional threshold) directly modifies
this. A "triple blend" Risk Engine would also need to add:

* Portfolio-level drawdown limit
* Sector concentration limit
* Correlation budget (e.g., no more than N highly-correlated single names)
* Cross-asset target ranges (if Q2 = yes)

This is a significant Risk Engine rework. Worth its own scoping pass.

\---

## What To Observe During the Rest of Phase 2

These don't change Phase 2 execution. They're observations to make
about the reference frameworks while we have time:

### Claude Portfolio (Framework B)

* Does the NOW position get re-evaluated at the late-July report?
* Does Claude Portfolio acknowledge the SPY underperformance and
adapt, or stay with conviction?
* How does the bot handle a position that breaks its thesis?
* Are positions exited at price targets, or held past them?

### Grok Portfolio (Framework C)

* How frequently does Grok rotate themes?
* Does the TLT position size change with rate environment?
* Are stops actually triggered on losers, or is it survivorship-bias
reporting?
* Does drawdown stay below 10% if there's a real correction?

### Our Bot (Framework A)

* Does the Q1 verdict (CALIBRATED) hold through cohorts 5/22-5/29?
* Does the Q2 near-miss BUY pattern (HIGH-DQ 1/1, MEDIUM-DQ 0/1)
hold or break?
* Do +10d outcomes materially differ from +5d outcomes? (Bigger
moves? Different bias patterns?)
* Does the 3-5 day lag finding on WMT extend to other tickers in
the +10d window?

\---

## Operational Plan for This Document

|Phase|Action|
|-|-|
|Phase 2 (now → 6/12)|Document is REFERENCE ONLY. No code changes. Observe and add notes if reference-framework behavior changes materially.|
|6/12 Phase 2 → 3 review|Read this document alongside the locked Decision Worksheet v3. Decide whether the "triple blend" is the right Phase 3 direction or whether to prioritize the 4 worksheet hypotheses first.|
|Phase 3-A scoping|If triple blend confirmed, this document becomes the design genesis. Convert design patterns into a Phase 3 specification with implementation milestones.|
|Phase 3-B+|Treat this document as historical context; ongoing design lives in Phase-3-specific docs.|

\---

## Critical Caveats

1. **Not financial advice.** This is system design analysis. Real
investment decisions need more than methodology comparisons.
2. **Past performance ≠ future results.** Grok's 59% over 9 months
could reverse. Claude Portfolio's -5.7% relative could close.
3. **No verified attribution.** Public dashboards can't tell us
whether returns are from methodology vs market regime vs
luck-of-launch-timing.
4. **Different operators, different risk constraints.** AI Finance
Labs is running these as research/marketing experiments. Our bot
is running real personal capital in tax-advantaged and taxable
accounts. The constraints aren't identical.
5. **Don't over-index on a single comparison.** The right Phase 3
design comes from validated Phase 2 evidence first, then borrowed
patterns from these frameworks second.

\---

*End of design document. Next read: 2026-06-12 after Phase 2 close.*

