# Phase 2 Closeout Memo — Claude Equity Bot

**Status:** SCAFFOLD — populate during Week 4 (6/8–6/12); finalize at the 6/12 review
**Phase:** 2 (read-only calibration dry run)
**Review date:** Fri 2026-06-12 (Day 19) — locked
**Dataset:** 9 daily cohorts (2026-05-18 → 2026-05-29), 24 unique tickers/day
(19 held + 5 scouts), ~$32K across Roth IRA + Individual (margin)
**Author:** Rob · **Drafted:** 2026-06-05

> HOW TO USE THIS FILE: Sections marked **[FINAL]** are locked and carry their
> numbers already. Sections marked **[PENDING 6/X]** have a clean slot to fill
> when that day's +10d data lands. Sections marked **[FINALIZE AT REVIEW]** are
> the synthesis written on 6/12 once all data is in. Fill the slots, don't
> re-derive the locked verdicts — they're settled.

---

## 0. Executive Summary  **[FINALIZE AT REVIEW]**

*One paragraph, written last. Should state: whether Phase 2 validated the bot's
calibration, the single most important finding, the Q2 threshold decision, and
the Phase 3 go/no-go recommendation. Draft slot below.*

> _[TO WRITE 6/12 — 5–7 sentences. Template:_ "Phase 2 ran N cohorts over 4
> trading weeks and found the bot's confidence is calibrated at +5d, with the
> 50-59% band leading at __%. The strongest finding was ____. The near-miss
> threshold decision is ____. We recommend Phase 3 ____ , prioritizing ____."_]_

---

## 1. What Phase 2 Set Out to Test  **[FINAL]**

Phase 2 was the read-only calibration dry-run: the bot produced daily
BUY/SELL/HOLD signals against live accounts but placed **no orders**, so we
could measure whether its confidence scores predict outcomes before risking
execution. Four decision questions framed it (see §2). The deliberate
constraint — no code changes during Phase 2 — kept the calibration dataset
clean.

| Design element | Value |
|---|---|
| Cadence | Daily AM run (9:30 CST canonical; PM diagnostic-only) |
| Signal engine | Claude Sonnet per-ticker, with confidence + bull/bear + risk flags + DQ |
| Risk Engine | BUY ≥70%, SELL ≥65%, max 5%/position, max 8 positions, human approval |
| Outcome windows | +5d, +10d, +20d (N trading days; closing prices) |
| HOLD-correct test | \|return\| < ±3% over the window (locked threshold) |

---

## 2. The Four Decision Questions — Verdicts

### Q1 — Is the bot's confidence calibrated?  **[FINAL]**

**VERDICT: ✓ CALIBRATED.** 6 of 9 cohorts confirm; combined band-sample n=216
has the 50-59% band leading at **61.3%**, above 40-49% (43.1%) and 60-69%
(50.0%).

| Band | Hit rate (n=216) |
|---|---|
| 40-49% | 43.1% (31/72) |
| **50-59%** | **61.3% (65/106)** |
| 60-69% | 50.0% (19/38) |

The 3 non-confirming cohorts (5/21, 5/22, 5/26) are explained by tiny 60-69%
samples (n=3–4) and low-volatility names inflating the 40-49% band; none
reverse the aggregate.

### Q2 — Are near-miss BUYs (60-69%) profitable?  **[LOCKED — 6/8 addendum pending]**

**VERDICT: KEEP 70% threshold.** Complete cohort 4/6 = 66.7% hit, **−0.07% avg
+5d return.** Both loosening gates fail (need ≥75% AND ≥3%).

| Date | Ticker | Conf | DQ | +5d Return | Right |
|---|---|---|---|---|---|
| 5/19 | NVDA | 62% | MED | −3.62% | NO |
| 5/21 | SCHD | 68% | HIGH | +1.22% | YES |
| 5/22 | NVDA | 62% | MED | +3.50% | YES |
| 5/26 | VTI | 68% | HIGH | +1.14% | YES |
| 5/27 | NVDA | 63% | MED | +2.34% | YES |
| 5/29 | NVDA | 68% | MED | −5.02% | NO |
| **6/1** | **NVDA** | **68%** | **MED** | **[PENDING 6/8]** | **[__]** |

> ⚠️ ADDENDUM SLOT [6/8]: NVDA 6/1 (entry $221.59) +5d completes 6/8. Record
> outcome here. Verdict is KEEP 70% regardless — confirm the addendum does not
> move hit rate to ≥75% AND avg return to ≥3% (it cannot, mathematically, on
> one outcome). State the final 7-of-7 numbers.

### Q3 — Structural gap decisions  **[FINAL]**

**LOCKED 2026-05-29.** CBRS = **Path A (exclude)** — worst miss in 4 of 4
cohorts. CORN/GLD/AG = **Path B (Phase 3 code work)** — `commodity_context.py`
and `commodity_backed_equity_context.py` modules.

### Q4 — Phase 3 hypotheses  **[FINAL — prioritization is a Phase 3 task]**

| # | Hypothesis | Phase 2 status |
|---|---|---|
| H1 | Update lag (add prior-5-day price input) | **TOP — strongest evidence** |
| H2 | Direction asymmetry (loss > gain reactivity) | Supported (NVDA, WMT) |
| H3 | Intraday news sensitivity | Documented (5/29 AM/PM) |
| H4 | DQ-conditional threshold | **DEMOTED — n too small** |

---

## 3. Findings Ledger — The Durable Empirical Results  **[FINAL except where noted]**

*The verified results Phase 2 produced, independent of the Q-framework.*

1. **Calibration shape.** The 50-59% confidence band leads hit rates; the
   relationship is non-monotonic (middle band beats both tails). Robust at
   n=216.
2. **Update lag (H1) — strongest finding.** WMT traced across all 9 cohorts:
   the bot held at 62% confidence through three identical ~−11% losses
   (5/18–5/20), then *caught up* — confidence fell to 48–55% as losses shrank
   (−5%, −4%, −1%) and by 5/29 WMT was +2.45%. Self-corrected over ~3–5 days.
   The only finding that replicated every cohort, has a clear mechanism, AND a
   demonstrated resolution.
3. **+10d behavior.** Absolute moves reliably grow at +10d (**4/4 cohorts**).
   HOLD accuracy decay is **NOT robust** — a coin flip (2 decayed, 2 did not).
   The durable claim is magnitude-growth, not accuracy-decay.
   **[EXTEND with 5/22–5/29 +10d this week — see §4]**
4. **Data quality ≠ thesis quality.** HIGH-DQ HOLDs were among the biggest
   misses (MSFT, PM). DQ measures input completeness, not directional
   correctness.
5. **Near-miss band is negative-EV.** 60-69% BUYs returned −0.07% avg with a
   coin-flip hit rate — the basis for keeping the 70% threshold.
6. **Operational: rate-limit skips.** Schwab 429s skipped different tickers on
   6/1/6/2/6/3 (burst-position artifact, not ticker-specific). Phase 3 fix:
   exponential backoff/retry in `schwab_client`.

---

## 4. +10d Completion Tracker — Week 4 Data  **[PENDING — fill daily]**

*Four +10d cohorts are in (5/18–5/21). Five complete this week. Each tests
whether the magnitude-grows / accuracy-coin-flip pattern holds.*

| Cohort | +10d due | +5d hit | +10d hit | Δ | Abs-move grew? | Decayed? |
|---|---|---|---|---|---|---|
| 5/18 | done | 50.0% | 41.7% | −8.3pt | Yes | Yes |
| 5/19 | done | 37.5% | 37.5% | 0.0pt | Yes | No |
| 5/20 | done | 37.5% | 33.3% | −4.2pt | Yes | Yes |
| 5/21 | done | 41.7% | 45.8% | +4.2pt | Yes | No |
| 5/22 | **6/8** | 54.2% | [__] | [__] | [__] | [__] |
| 5/26 | **6/9** | 66.7% | [__] | [__] | [__] | [__] |
| 5/27 | **6/10** | 79.2% | [__] | [__] | [__] | [__] |
| 5/28 | **6/11** | 66.7% | [__] | [__] | [__] | [__] |
| 5/29 | **6/12** | 54.2% | [__] | [__] | [__] | [__] |

> ⚠️ FILL RULE: compute +10d from the original signal date (function output,
> never transcribe). After 6/12, tally the final decay scorecard (X of 9
> decayed) and abs-move scorecard (X of 9 grew). Update Finding #3 in §3 and the
> worksheet +10d caveat if the 9-cohort picture differs from the 4-cohort read.
> Also track WMT's +10d in each remaining cohort to extend the H1 trajectory.

---

## 5. Phase 3 Recommendation  **[FINALIZE AT REVIEW]**

### 5a. Go / No-Go on the "Triple Blend"

*Reference: phase3_design_concepts.md (read alongside this memo on 6/12).
Decide whether Phase 3 pursues the triple-blend synthesis or prioritizes the
validated H1–H4 prompt-level hypotheses first.*

> _[DECISION 6/12. The 5/29 analyst guidance was: start with H1–H4 (validated by
> our data) and treat the architectural triple-blend (sector backbone,
> cross-asset, sizing) as larger structural experiments to scope after the
> prompt-level fixes. Confirm or revise.]_

### 5b. Hypothesis Prioritization

| Priority | Item | Rationale | Effort |
|---|---|---|---|
| 1 | **H1 — prior-5-day price input** | Strongest, replicated, clear mechanism + resolution | [__] |
| 2 | [__] | | |
| 3 | [__] | | |

### 5c. Open Design Questions (from phase3_design_concepts Q1–Q5)  **[FINALIZE AT REVIEW]**

| Q | Question | Lean |
|---|---|---|
| Q1 | Book concentration (10-15 / ~25 / 30-50)? | [__] |
| Q2 | Cross-asset (bonds/TLT) yes/no? | [__] |
| Q3 | Stateful thesis tracking vs rebuild-daily? | [__] |
| Q4 | Auto-execute vs remain advisory? | [__ — default advisory] |
| Q5 | Risk Engine evolution (drawdown, sector, correlation limits)? | [__] |

### 5d. What Stays / What Changes

*What carries forward from the current bot vs what the findings say to change.*

> _[Fill: daily cadence + per-position cost-basis depth + Risk Engine hard
> guards STAY; H1 price-input + CBRS exclusion + 429 backoff CHANGE; etc.]_

---

## 6. Risks, Caveats & Limitations  **[FINAL — extend if review surfaces more]**

- **Not financial advice.** System-design analysis on real personal capital.
- **Small per-cohort n.** Per-cohort Pattern-Holds flags (n=3–4 in deciding
  bands) are noisy; the aggregate (n=216) is the evidence.
- **Single market regime.** 4 weeks, one macro backdrop. Calibration may not
  hold across regimes.
- **HOLD ±3% test quirk.** Large favorable moves on HOLDs score as "misses"
  (e.g. SND +19.5%) — accuracy figures undercount gains-left-on-table.
- **+5d ≠ +10d.** Verdicts established at +5d; the +10d picture (magnitude
  grows, accuracy coin-flip) is a horizon caveat, not a contradiction.

---

## 7. Decision & Sign-Off  **[FINALIZE AT REVIEW]**

| Item | Decision |
|---|---|
| Phase 2 calibration validated? | [__] |
| Q2 threshold | KEEP 70% (confirm post-6/8 addendum) |
| Phase 3 approved? | [__] |
| Phase 3 first workstream | [__] |
| Auto-execution? | [__ — default advisory until Phase 3 has its own calibration] |

---

## Appendix — Provenance & Conventions  **[FINAL]**

- **+Nd** = N trading days; computed from function output, never transcribed.
- **AM (9:30 CST)** signals canonical; PM runs diagnostic-only.
- **±3% HOLD threshold** locked for Phase 2.
- **Outcomes** use closing prices, not AM run-capture prices.
- **NVDA 5/29 entry = $215.95** (Signals/worksheet authoritative; Near-Miss tab
  reconciled 6/5).
- **5/18 cohort** deduped to 24 rows (original 30 predated dual-account
  consolidation).
- **Source artifacts:** analyst_notes.md, Phase2_to_Phase3_Decision_Worksheet_v5.docx,
  claude_equity_bot_tracker.xlsx, phase3_design_concepts.md, Daily_Workflow_v2_1.docx.

---

*End of scaffold. Populate §4 daily 6/8–6/12; finalize §0, §5, §7 at the 6/12 review.*
