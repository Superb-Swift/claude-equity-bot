# Phase 4 — Execution Readiness Register

*Claude Equity Bot · v1.0 · opened 2026-08-12 (RW) · companion to the "Terminal Intent" subsection in the Reference block of `docs\analyst_notes.md`. **Nothing in this document is ruled.** It exists so that the promotion to execution is designed under the same pre-registration discipline as every other phase transition, rather than assembled under schedule pressure at the moment it is wanted. Advisory-only · no orders · not financial advice.*

---

## 0 · Why this document exists

**The goal of this project is a bot that executes trades on a research-backed design.** The advisory-only period is the method for earning that promotion, not the destination. The sequence was deliberate: build the equity-research instrument, subject it to human review long enough to establish what it actually measures and where it fails, then promote it.

**T1 already says this and the wording should be read literally** — "advisory-only, **pre-execution**, mandatory." It is a phase gate, not a permanent ceiling. Nothing here relaxes it, softens it, or gives it a date.

The measurement discipline and the execution goal are the same project. Pre-registration, refusing to lower bars, and recording counterfactuals so their cost stays visible are not worth their cost for advice a human re-judges anyway. They are worth it precisely because something will eventually act on the output with real capital.

---

## 1 · Items whose "harmless under T1" classification has an expiry date

The record has repeatedly and correctly classed defects as harmless because nothing executes. That classification expires on one date. Each is carried here with its severity under execution.

| ID | Item | Under T1 | Under execution | Gate |
|---|---|---|---|---|
| **D-5** | CHECK 8's body is `if sig == "BUY": pass`; `DAILY_LOSS_LIMIT_PCT` controls nothing | Latent | **Highest severity.** A documented risk control that does not exist — the difference between a bad day and an uncapped one | X6 |
| **—** | `print_risk_report` sizes `Shares : N shares recommended` off `portfolios[0]` while the decision is per-account (D-1/D-2, ruled 2026-08-11) | Cosmetic | **Order-sizing error** against possibly the wrong account | X3 |
| **D-7** | Parsers have never seen the approval path in production (fixture-covered only) | Fixture-covered | That path is the one that places orders | X2 |
| **D-3** | CHECK 6 blocked SELL — fixed by DP-3C-o (i), 2026-08-11 | No effect | Refusing to exit at max positions is backwards when capital is at risk | closed |
| **DP-3C-o (iii)** | `MAX_OPEN_POSITIONS` demoted from veto to reported flag | Reporting only | Removes the only structural limit on position **count** | X4 |
| **DP-3C-s** | Held/scout directional asymmetry (below) | Design curiosity | **Execution blocker** | X4 |

---

## 2 · The ratchet — DP-3C-s under execution

Measured 2026-08-12 from the master (1,411 rows, 59 cohorts) `[V]`:

- BUY on an **unheld** name fires at **15.07%** (44 of 292 scout rows)
- SELL on a **held** name fires at **0.089%** (1 of 1,119 held rows)
- Roughly **170x** asymmetry in the acquire-versus-dispose direction

The only two held-name directional signals in the entire record are SCHD BUY (2026-05-21) and CBRS SELL (2026-06-26), both inside the first six weeks.

**Under advisory this is an interesting design property. Under execution it is a ratchet — a system that opens positions and structurally almost never closes them.**

Stack it with `MAX_OPEN_POSITIONS` demoted to a flag and `DAILY_LOSS_LIMIT_PCT` unimplemented, and the only remaining structural limit is `MAX_POSITION_PCT`, which bounds **concentration but not accumulation**.

Two rulings that were each individually sound interact into a property neither was assessed against. DP-3C-o (iii) is right that a monitoring-burden cap should not hold a veto. DP-3C-s option (A) — that held/unheld asymmetry is defensible on tax and transaction-cost grounds — may well also be right. **The interaction is the finding.**

Consequence: **DP-3C-s must be RULED before Phase 4, not merely documented, and its options are no longer symmetric.** Option (A) is sufficient for an advisory instrument and is **not** sufficient for an executing one absent a compensating exit mechanism.

---

## 3 · The measurement problem

Every acceptance criterion this project has run is a **research** criterion. Most do not transfer.

**What does not transfer.** The ±3% HOLD band and the "Was Claude Right" column. On the HOLD population, accuracy is definitionally `1 − breach rate` (verified 1,160/1,160 on 2026-08-05), and the breach count is driven by market **dispersion** and cohort **drift** — both market-side. A dispersion measurement cannot underwrite an execution decision. It never claimed it could.

**What partially transfers.** KEEP-70, because it asks whether the gate's *rejections* were right, which is an execution-shaped question. Its limits travel with it: it measures the rejected side only, and its evidence base is effectively five scout tickers.

**What has never been instrumented and must be, before Phase 4:**

- Realised P&L
- Slippage against the signal-time quote — note `Px@signal` is already a mid-session quote whose timing has drifted across the record (offsets of +2.5 to +98 minutes)
- Maximum drawdown
- Turnover
- Tax drag across the Roth IRA / Individual split — which the model reasons about in prose every session and which nothing measures

Each must carry an **expected event rate and time-to-read**, computed before go-live, per the Kickoff §5 binding rule. That rule was written for endpoints; it applies to the phase transition itself.

---

## 4 · Proposed entry gates — X1 through X7

Stated in the grammar of Phase 3-C's E1–E6. The letter **X** is proposed because E, G, T, H, Q and DP are all taken.

| Gate | Requirement |
|---|---|
| **X1** | Every rule printed in the Active Rules banner is enforced by `evaluate_signal` and has a test that has been **shown to fail**. No `pass` bodies; no advertised-but-unenforced rules |
| **X2** | The approval path exercised in production, not fixtures — the full `PENDING HUMAN APPROVAL` reason string and the Shares line, read by all three parsers |
| **X3** | Order sizing computed against the account that will receive the order |
| **X4** | DP-3C-s ruled, and a demonstrated SELL-generation path on held positions |
| **X5** | Execution metrics pre-registered with expected event rates and time-to-read (§3) |
| **X6** | A daily loss limit and a kill switch that exist, are enforced, and have been negative-tested |
| **X7** | A paper-execution phase producing real order objects against live signals, no capital at risk, before any live order |

**A gate that has never been shown to fail is not a gate** — the standing lesson from `phase_dispatch_audit.py`, which was negative-tested by reverting the D-8 defect and confirming exit 1. Every X-gate inherits that requirement.

---

## 5 · What this document does not do

It does not relax T1, give it a date, move any Phase 3-C gate, or change any E4 endpoint, arm, threshold, robustness condition, n or rate. It adds intent and a re-weighting to the record and moves no bar in either direction.

EDGAR go-live is unaffected — and the case for it strengthens rather than weakens, since primary-source filing context matters *more* to a system that will eventually act than to one that only advises.

---

*Advisory-only · no orders · not financial advice.*
