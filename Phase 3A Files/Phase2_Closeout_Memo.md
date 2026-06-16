# Phase 2 Closeout Memo — Claude Equity Bot

**Status:** FINAL — Phase 2 closed at the 6/12 review; Phase 3-A approved (advisory-only)
**Phase:** 2 (read-only calibration dry run)
**Review date:** Fri 2026-06-12 (Day 19) — locked
**Dataset:** 9 daily cohorts (2026-05-18 → 2026-05-29), 24 unique tickers/day
(19 held + 5 scouts), ~$32K across Roth IRA + Individual (margin)
**Author:** Rob · **Drafted:** 2026-06-05
**Last updated:** 2026-06-12 — **REVIEW COMPLETE.** §4 5/29 row filled; final scorecards locked (magnitude 8/9, decay 6/9 / ex-shock 3/6); §0, §3 Finding #3, §5, §7 finalized. Phase 2 validated; Phase 3-A approved, advisory-only, H1 first. Carry-forward: worksheet v6 +10d caveat edit.

> HOW TO USE THIS FILE: This memo is FINAL as of the 6/12 review. All sections
> carry their locked numbers; daily fill slots were resolved 6/8–6/12 and the
> synthesis sections (§0, §5, §7) were written at the review. The change history
> lives in the Last-updated line above and in analyst_notes.md. Do not re-derive
> locked verdicts — they're settled.

---

## 0. Executive Summary  **[FINAL — written at the 6/12 review]**

Phase 2 ran 9 cohorts (216 banded signals) over 4 trading weeks and validated
the bot's confidence calibration at +5d: the 50-59% band leads at 61.3%, above
40-49% (43.1%) and 60-69% (50.0%), with 6 of 9 cohorts individually confirming.
The strongest finding is the update lag (H1): WMT, traced across all nine
cohorts, showed confidence following price with a ~3–5 day self-correcting lag
— the only result that replicated every cohort, has a clear mechanism, and
demonstrated its own resolution. The near-miss decision is KEEP the 70% BUY
threshold: the locked 7-of-7 cohort hit 57.1% with a −0.90% average +5d return,
failing both loosening gates, and the extended post-lock set went 0-for-5 (avg
−6.2%) — every horizon and every extension lands on the same side. At +10d,
magnitude-growth proved robust (8 of 9 cohorts) while accuracy-decay stayed a
coin flip ex-shock (3 of 6) and is retired; the 6/10 Middle East shock landed
inside the three final windows, demonstrating the single-regime caveat
in-sample and exposing HOLD ±3% as regime- and path-dependent. We recommend
Phase 3 GO as a staged, advisory-only program: Phase 3-A implements the
prompt-level fixes (H1 prior-5-day price input first, then H3 stable-thesis
language, then the H2 asymmetry A/B) plus the locked engineering items (CBRS
exclusion, commodity-context modules — WASDE-validated 6/11, 429 backoff); the
triple-blend architecture is deferred to a Phase 3-B scoping pass gated on 3-A
producing its own calibration data.

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

### Q2 — Are near-miss BUYs (60-69%) profitable?  **[FINAL — 6/8 addendum recorded]**

**VERDICT: KEEP 70% threshold.** Complete 7-of-7 cohort 4/7 = 57.1% hit, **−0.90% avg
+5d return.** Both loosening gates fail (need ≥75% AND ≥3%). The 6/1 addendum moved
both metrics further from the bar (was 4/6 = 66.7%, −0.07% avg before it landed).

| Date | Ticker | Conf | DQ | +5d Return | Right |
|---|---|---|---|---|---|
| 5/19 | NVDA | 62% | MED | −3.62% | NO |
| 5/21 | SCHD | 68% | HIGH | +1.22% | YES |
| 5/22 | NVDA | 62% | MED | +3.50% | YES |
| 5/26 | VTI | 68% | HIGH | +1.14% | YES |
| 5/27 | NVDA | 63% | MED | +2.34% | YES |
| 5/29 | NVDA | 68% | MED | −5.02% | NO |
| **6/1** | **NVDA** | **68%** | **MED** | **−5.84%** | **NO** |

> ⚠️ ADDENDUM RESOLVED [6/8]: NVDA 6/1 (entry $221.59) closed +5d at $208.64 →
> −5.84% → NO (function-computed). Final 7-of-7: hit rate 4/7 = 57.1%, avg +5d
> return −0.90%. Both gates fail (need ≥75% AND ≥3%); the addendum lowered both
> figures, moving the cohort further from the loosening bar — exactly as the
> one-outcome math predicted. KEEP 70% confirmed.

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
3. **+10d behavior — FINAL (9/9, reconciled 6/12).** Absolute moves reliably
   grow at +10d (**8 of 9 cohorts**; 5/22 the lone exception). HOLD accuracy
   decay is **NOT robust**: 6 of 9 decayed, but the sharpest sit in
   shock-contaminated windows (5/27–5/29) or the quiet-week inflation-unwind
   pair (5/26–5/27); ex-shock the tally is 3 of 6 — a coin flip. The durable
   claims are magnitude-growth and the conditional observation that
   inflation-built +5d hit rates mean-revert hard at +10d.
4. **Data quality ≠ thesis quality.** HIGH-DQ HOLDs were among the biggest
   misses (MSFT, PM). DQ measures input completeness, not directional
   correctness.
5. **Near-miss band is negative-EV.** 60-69% BUYs returned −0.90% avg (final
   7-of-7) with a 57.1% hit rate — the basis for keeping the 70% threshold.
   Extended post-lock tracking corroborates: 0-for-5 through 6/12, avg −6.2%.
6. **Operational: rate-limit skips.** Schwab 429s skipped different tickers on
   6/1/6/2/6/3 (burst-position artifact, not ticker-specific). Phase 3 fix:
   exponential backoff/retry in `schwab_client`.

---

## 4. +10d Completion Tracker — Week 4 Data  **[FINAL — all 9 cohorts complete 6/12]**

*Four +10d cohorts are in (5/18–5/21). Five complete this week. Each tests
whether the magnitude-grows / accuracy-coin-flip pattern holds.*

| Cohort | +10d due | +5d hit | +10d hit | Δ | Abs-move grew? | Decayed? |
|---|---|---|---|---|---|---|
| 5/18 | done | 50.0% | 41.7% | −8.3pt | Yes | Yes |
| 5/19 | done | 37.5% | 37.5% | 0.0pt | Yes | No |
| 5/20 | done | 37.5% | 33.3% | −4.2pt | Yes | Yes |
| 5/21 | done | 41.7% | 45.8% | +4.2pt | Yes | No |
| 5/22 | done | 45.8% | 50.0% | +4.2pt | No | No |
| 5/26 | done | 66.7% | 29.2% | −37.5pt | Yes | Yes |
| 5/27 | done | 79.2% | 29.2% | −50.0pt | Yes | Yes |
| 5/28 | done | 66.7% | 41.7% | −25.0pt | Yes | Yes |
| 5/29 | done | 54.2% | 37.5% | −16.7pt | Yes | Yes |

> ⚠️ FINAL SCORECARD (9 of 9, locked 6/12): **magnitude grew 8 of 9** (5/22 the
> lone exception) — robust across quiet weeks, the shock, and the bounce.
> **Accuracy decayed 6 of 9; ex-shock 3 of 6** — a coin flip; the decay claim is
> RETIRED, with the regime flag on 5/27–5/29 and the conditional
> inflation-unwind observation (5/26, 5/27: the two quietest +5d cohorts were
> the two biggest decayers, shock or no shock; 5/27 vs 5/28 showed 25pt of pure
> path dependence around the gap). WMT +10d full arc: −15.19 → −12.87 → −12.24
> → −2.54 → −0.00 → +0.01 → +1.99 → +1.71 → **+4.31%** — the lag self-corrected
> from −15% to flat, then the final cohort breached the band on the FAVORABLE
> side (a HOLD "miss" that made money), closing the H1 case with the lag
> visible in both directions. Finding #3 in §3 is reconciled to the 9-cohort
> picture.

> ⚠️ DATA CORRECTION (6/8): the 5/22 +5d hit was previously logged as 54.2%; the
> tracker's own Was-Claude-Right column and the Cohort-Analysis bands both give
> 45.8% (11/24). 54.2% was the 5/29 cohort's figure mis-copied one row up.
> Corrected in the table above; the other 8 cohorts were re-verified clean. No
> locked verdict is affected — Q1 rests on the n=216 band aggregate, and 5/22 was
> a NO either way (a 50/50 band tie).

> ✓ FILL RULE RESOLVED (6/12): all nine +10d rows computed from function
> output; final scorecards tallied above; Finding #3 updated; WMT tracked
> through every cohort. Remaining carry-forward: soften the Decision
> Worksheet's "+10d grows (4/4)" caveat to the final 8/9 (v6 edit,
> post-review).

---

## 5. Phase 3 Recommendation  **[FINAL — 6/12 review]**

### 5a. Go / No-Go on the "Triple Blend"

*Reference: phase3_design_concepts.md (read alongside this memo on 6/12).
Decide whether Phase 3 pursues the triple-blend synthesis or prioritizes the
validated H1–H4 prompt-level hypotheses first.*

**DECISION (6/12): CONFIRM the 5/29 guidance — staged approach.** Phase 3-A
pursues the prompt-level hypotheses validated by our own data (H1 → H3 → H2)
plus the locked engineering items; the triple-blend architecture (sector
backbone, cross-asset, sizing — phase3_design_concepts.md) is **deferred to a
Phase 3-B scoping pass** gated on 3-A producing its own calibration data.
Rationale: every validated Phase 2 finding is prompt-level; the reference
frameworks' returns cannot be attributed (design-doc caveats 2–3); and the 6/10
shock showed the evaluation methodology itself (HOLD bands) needs work before
architectural conclusions can be trusted.

### 5b. Hypothesis Prioritization

| Priority | Item | Rationale | Effort |
|---|---|---|---|
| 1 | **H1 — prior-5-day price input** | Strongest, replicated 9/9, clear mechanism + demonstrated resolution; final WMT arc shows the lag in both directions | Small — prompt + existing quote plumbing |
| 2 | **H3 — stable-thesis prompt language** | Documented intraday sensitivity (5/29 AM/PM); 6/10 shock-day confidence compression is consistent | Small — prompt-only |
| 3 | **H2 — direction-asymmetry A/B** | Supported (NVDA, WMT) but the WMT 5/29 favorable-side breach (+4.31%) complicates pure asymmetry — A/B needed to disentangle | Medium — A/B harness |

H4 (DQ-conditional threshold) stays demoted to the observation backlog (n too
small). Parallel engineering workstream, not hypothesis-gated: CBRS exclusion
(Path A), `commodity_context.py` + `commodity_backed_equity_context.py` (Path B
— WASDE-validated 6/11), 429 exponential backoff, near-miss registry
auto-generation from the Signals tab, and market-relative / vol-scaled HOLD
bands added to the Phase 3 evaluation design alongside ±3% for comparability.

### 5c. Open Design Questions (from phase3_design_concepts Q1–Q5)  **[FINAL — 6/12 review]**

| Q | Question | Lean (6/12) |
|---|---|---|
| Q1 | Book concentration (10-15 / ~25 / 30-50)? | **(b) maintain ~25** — no Phase 2 evidence touches book structure; revisit at 3-B with triple-blend scoping |
| Q2 | Cross-asset (bonds/TLT) yes/no? | **Defer to 3-B** — new reasoning domain (rates/duration); design doc itself suggested a sub-phase |
| Q3 | Stateful thesis tracking vs rebuild-daily? | **3-A: rebuild-daily + H1's prior-5-day price input** (data-level memory); full stateful thesis prototyped shadow-only at 3-B (anchoring/drift experiment) |
| Q4 | Auto-execute vs remain advisory? | **REMAIN ADVISORY** — locked default; nothing in Phase 2 argues for loosening; shock week reinforces |
| Q5 | Risk Engine evolution (drawdown, sector, correlation limits)? | **Unchanged for 3-A** (70/65 confirmed, 5%/position, 8 positions, human approval); drawdown/sector/correlation limits scoped with triple-blend at 3-B; DQ-conditional idea to backlog |

### 5d. What Stays / What Changes

**STAYS:** daily AM cadence (9:30 CST canonical); per-position depth (cost
basis + account type + P&L in prompt); Risk Engine hard guards with confirmed
70/65 thresholds; cohort-analysis calibration methodology; analyst-notes
discipline and the locked conventions (function-computed dates, closing
prices, ±3% HOLD test for cross-phase comparability).

**CHANGES:** add prior-5-day price input (H1); exclude CBRS from runs (Path A
— worst miss in 4 of 4 cohorts); build `commodity_context.py` +
`commodity_backed_equity_context.py` (Path B — WASDE-validated 6/11);
exponential backoff/retry in `schwab_client` (429 burst-position artifact);
stable-thesis prompt language (H3); auto-generate the near-miss registry from
the Signals tab (the hand-maintained registry drifted twice in Week 4:
mis-dated pair + missing rows); add market-relative / vol-scaled HOLD bands to
Phase 3 evaluation alongside ±3%.

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
- **Regime event inside Phase 2 (added 6/10; scope corrected 6/11).** The 6/10
  Middle East shock sits inside the **5/27–5/29** +10d windows (the 5/26 window
  ended 6/9, pre-shock). Those late-cohort +10d hit rates are regime-contaminated,
  and HOLD ±3% correctness is mechanically regime-dependent (a market-wide gap
  fails all HOLDs irrespective of skill) and path-dependent around a gap (5/28's
  +10d was measured on the 6/11 bounce). Candidate Phase 3 design note:
  market-relative or vol-scaled HOLD bands.

---

## 7. Decision & Sign-Off  **[FINAL — 6/12 review]**

| Item | Decision |
|---|---|
| Phase 2 calibration validated? | **YES — Q1 CALIBRATED** (50-59% leads at 61.3%, n=216, 6 of 9 cohorts) |
| Q2 threshold | **KEEP 70%** — confirmed post-addendum (7-of-7: 57.1%, −0.90% avg); extended set 0-for-5 corroborates |
| Phase 3 approved? | **YES — Phase 3-A (prompt-level), advisory-only**; 3-B scoping gated on 3-A calibration |
| Phase 3 first workstream | **H1 — prior-5-day price input** (parallel: CBRS exclusion, commodity modules, 429 backoff) |
| Auto-execution? | **NO — remain advisory** until Phase 3 has its own calibration |

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
