# Phase 3-A Closeout Memo

*Claude Equity Bot · Phase 3-A (live advisory) · CLOSED 2026-07-06 by sign-off — Worksheet v3 signed "Rob · July 6, 2026" (H1 verdict lock ✓, Close Phase 3-A: YES ✓) and same-day written directive (terminate A/B testing; move to Phase 3-B triple-blend; implement H1 findings; cut dead-weight hypotheses). Advisory-only throughout — Phase 3-A executed no orders. Not financial advice.*

---

## 1. Run Summary

| Item | Value |
|---|---|
| Duration | 2026-06-15 → 2026-07-06 (14 trading sessions; 6/19 and 7/3 NYSE holidays) |
| Live cohorts +5d-complete at close | **9** (6/15–6/26); 5 more in flight (6/29–7/6), resolving under 3-B monitoring |
| Project signals at close | **787** total · BUY 20 · SELL 1 |
| Live band samples (+5d resolved) | 50-59%: **n=97 @ 52.6%** · 60-69%: **n=67 @ 65.7%** |
| Integrity | Every session cross-validated log↔tracker (24/24 daily); recalc 0 errors throughout; single prompt arm (variant "A") all 14 sessions |

## 2. Gate Dispositions — the governance record

The closeout distinguishes three ways a gate closed. **Verdicts** are evidence-complete conclusions per pre-committed criteria. **Descopes** are deliberate terminations before test — decisions, not findings. **Parks** are open questions shelved with documented re-open triggers.

| Gate | Disposition | Basis |
|---|---|---|
| **H1 — confidence update lag** | **VERDICT (b) LOCKED** 7/6 | Criterion met (8 cohorts at lock; 9th consistent). Lag **5 sessions, stable in every read** 6/15→7/6; two complete hold→catch-up arcs (Phase 2 May; live June: held 52–55% through −3.51/−5.22/−8.99/−4.61% misses, then stepped 52→45% on 7/1). corr(conf,+5d) −0.583. The +0.198 contemporaneous-corr headline decomposes to the 7/1–7/2 catch-up itself (−0.153 without it) — the flip *is* the lag signature. **Prompt-level remedy ineffective → retired.** Provenance note: the variant-"A"-includes-H1-input box was left open at signature; recorded as a documented assumption — moot for action, since implementation moves to feature level (§4). |
| **H3 — thesis stability** | **DESCOPED** (retired untested) | Terminated by sign-off before A/B. Baseline on record: 26/737 day-over-day flips = **3.5%**, concentrated (NVDA 38.7%, VTI 20.0%, GLD 12.9%; 19 of 24 tickers zero flips; 54% of flips on <1% moves). Portfolio-wide, the premise is weaker than the 5/29 intraday snapshot suggested — churn is a 3-ticker trait, not a system trait. Not a verdict: the stable-thesis prompt was never tested. Any future churn work would be ticker-scoped (NVDA) inside 3-B design, not a standing hypothesis. |
| **H2 — direction asymmetry** | **DESCOPED** (retired untested-and-unsupported) | Terminated by sign-off before A/B. Baseline on record is **hypothesis-adverse**: portfolio ratio **0.85** (sens_down 1.51 / sens_up 1.78 — up-reactive on average), heterogeneous per ticker (RTX 2.89 ↔ CBRS 0.33). The original WMT/GM pair replicates directionally (1.68 vs 1.10) but does not generalize. |
| **Q1-R — live reversal of the certified edge** | **PARKED** with re-open triggers (§5) | Findings certified (§3.2); root cause open. Diagnosis test identified (prompt diff + distribution diff) but inputs not assembled; no execution exposure exists to force it now. |
| **Gate S — live sample depth** | **WAIVED at closeout** | Closed at 9 of ~10–12 cohorts, 60-69 n=67 vs the ~88 target. Rationale: advisory-only — no execution decision rests on this sample; monitoring continues in 3-B; the depth target transfers into re-open trigger T2 (§5). |
| **A/B program** | **TERMINATED** | `run_ab_test.bat` and the two-arm plan archived; variant "A" continues as the sole live generator. |

## 3. Certified Findings of the Live Run

### 3.1 H1 — the lag is real (the run's cleanest positive result)
~5-session confidence-update lag on WMT-type names: certified in Phase 2, **fully replicated live** (stable in all 9 cohorts' reads; two complete hold→catch-up cycles; step size ~7–14pts, ~5 sessions late). This is the finding Phase 3-B implements (§4).

### 3.2 Q1 guardrail — inverted out-of-sample (the run's headline negative result)
The certified "50-59 leads 60-69 on +5d" edge (**+61.3%** snapshot, +8.2pt all-Phase-2) **did not reproduce**: final live cumulative **−0.6pt** (crossover reached 7/2, held); pairwise held **2 of 9** cohorts; **7 of 8 non-compressed cohorts favored 60-69**; regime-stratified non-compressed lead **−18.0pt** (55.2% vs 73.2%) vs Phase 2's **+5.8pt** — a ~24pt within-regime swing. Established along the way: **regime-artifact hypothesis RULED OUT** (Phase 2 lead held in clean cohorts, +9.1pt); **band populations are not stable across phases** (60-69 BUY share 21%→3%; PM 29%→75% within-band; NVDA exited 60-69; SPY/QQQ/XLU entered 50-59) — root cause narrowed toward generator-drift/population-shift, not diagnosed. The reversal is **+5d-sharp**: the four +10d horizon reads split 2–2 (6/15, 6/18 → 60-69; 6/16, 6/17 → 50-59). **Operational status: the Q1 guardrail is SUSPENDED as a decision input** — nothing in 3-B may rely on confidence-band ordering (trigger T3).

### 3.3 Q2 — KEEP 70% (reinforced)
Near-miss BUYs (60-69%) failed both horizons live: LOCKED 4/7 (+5d) and 1/7 (+10d); EXTENDED 5/12 and **1/12 (8.3%, avg −3.7%)**. The 70% threshold stands. 20 near-misses on the registry; GLD 65% (HIGH) resolves +5d on 7/9.

### 3.4 Magnitude growth — robust, with an annotated event cluster
**Net growth (|+20d| > |+5d|) 13-for-13** — every measured cohort. Strict monotonicity 9-for-13; the four exceptions (5/22, 6/1, 6/2, 6/3) all dip at +10d and recover — the 6/10-shock cohort family (shock at peak |+5d|, mean-reversion by +10d, late-June re-expansion). Event-driven, not a law failure; 6/4 returned to monotonic (4.14 → 4.61 → 6.22%).

### 3.5 First SELL — single datapoint, adverse
CBRS SELL 68% (6/26) resolved **+14.61% → NO** — the project's first and only SELL, a hard miss. n=1, no generalization drawn; consistent with and supportive of the standing **Q3 Path A decision** (CBRS excluded to Q4 2026).

### 3.6 H4 watchdog — 2 of 3 reopen conditions met
HIGH-DQ near-miss hit 75% (3/4) ✓; HIGH ≥ MEDIUM overall (57.5% vs 48.9%) ✓; blocker **n = 4 of ≥10**. Watchdog continues in 3-B; GLD 7/9 adds HIGH-DQ n.

## 4. H1 Implementation Order (into 3-B)
Per the locked disposition and the 7/6 directive: retire prompt-phrasing as a lag remedy; **implement at feature level** — a mechanical trailing 5-day return input in the signal context (optionally a confidence-damping rule). Acceptance test pre-registered in the 3-B kickoff: h1_lag_trace estimated lag **≤ 2 sessions sustained over ≥ 4 live cohorts** post-deploy (WMT primary tracer, GM secondary).

## 5. Q1-R Park Record — re-open triggers
Parked 2026-07-06, rationale: scope discipline; the decisive diagnosis (Phase-2-vs-live **prompt diff + distribution diff**: per-ticker confidence histograms, band-membership flows, DQ mix) requires inputs not yet assembled; advisory-only status means no capital is exposed to the undiagnosed reversal. **Re-open on any of:**
- **T1 (mandatory):** before any execution-gate consideration — no real orders, ever, while Q1-R is undiagnosed.
- **T2 (data):** when live 60-69 n ≥ 88 (the original Gate-S depth target), if the non-compressed stratum lead is still ≤ −15pt → run the diff regardless of other work.
- **T3 (reliance):** before any 3-B design choice that would depend on confidence-band ordering.

## 6. Standing Constraints into Phase 3-B
Advisory-only, human-approval-gated, **no order execution** — unchanged. Execution remains a separate future gate requiring, at minimum: Q1-R diagnosed (T1), positive live paper-EV over a pre-set cohort count, and validated risk controls (position caps, kill-switch). The Q1 guardrail is suspended as a decision input. KEEP 70% stands. Q3 code paths stand (CORN/GLD/AG → Path B modules; CBRS → Path A exclusion). Not financial advice.

## 7. Deliverables Index (closeout set)
`Phase3A_Closeout_Memo.md` (this document) · `Phase3A_Closeout_Decision_Worksheet_v3.docx` (signed instrument) · `Phase3B_Kickoff_Prompt.md` · `analyst_notes.md` (dated entries 6/15–7/6, Days 1–14) · `regime_stratification.md` (final, 9 cohorts) · `near_miss_registry.md` · tracker with Guardrail Trace + Live Cohort Scoreboard sheets (Rob's weekly-review copies, authoritative).

---

*Phase 3-A opened 2026-06-15 on the Phase 2 certification; closed 2026-07-06 on signed worksheet v3. The phase did its job: it caught a certified edge failing out-of-sample before any capital could rely on it, certified the lag finding for implementation, and cleared the hypothesis backlog for 3-B.*
