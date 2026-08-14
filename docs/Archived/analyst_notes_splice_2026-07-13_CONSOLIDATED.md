# analyst_notes.md — CONSOLIDATED 7/13 splice (supersedes the morning 7/13 splice)

*Paste target: `docs/analyst_notes.md`. This is the FULL 7/13 entry — use this instead of `analyst_notes_splice_2026-07-13.md` (that one predated the diagnostic work). Insert after the 7/10 entry; replace the Upcoming block. PASTE AS PLAIN TEXT. All figures verified against `signals_2026-07-13.log` + `tracker_with_registry.xlsx`; T2 confirmed by `t2_check.py` (exit 10). +Nd = trading days.*

---

## (1) New dated bullet — insert after the 7/10 entry

* **7/13 (Phase 3-B Day 5) — a milestone day: WS1 GO-LIVE, T2 FIRED, Q1-R DIAGNOSED & CLOSED, Q4-R scoped & closed.** **WS1 deployed (era `A-S1D1-B1`):** first blend cohort, cross-check 24/24 operative (base path byte-identical — shadow-parallel intact); **blend adjusted exactly 1 signal** (rest HOLD, unchanged by design). NVDA BUY base 65 → blend_op 70 (sector −0.079 opposes, regime +0.609 risk-on confirms → +0.079) — **first live GATE-FLIP** (base rejected <70, blend would approve); +5d resolves 7/20. G2 clock: 1 cohort; `blend_eval` reads from ~7/20+. **Cross-check:** 24/24; no effective damping; DQ 19H/5M/0L; 23 HOLD + 1 BUY; 7/6 cohort +5d resolved 24/24; totals 907. **NVDA 65% (HIGH) new near-miss → registry 22**; H4 HIGH-DQ near-miss → 6 (pending 7/20). **T2 TRIPWIRE FIRED** (`t2_check.py` exit 10): DEPTH n=100/88 MET; **LEAD (non-compressed) swung −12.7 → −15.4pt** (7/6 cohort resolved favoring 60-69), 0.4pt past, marginal but pre-registered → **Tier-2E diff run.** **Q1-R DIAGNOSED (Tier-2E, `Q1R_Diagnostic_Memo.md`):** the guardrail did NOT break — the model got **better-calibrated at go-live**. Decomposition: 50-59 −4.8pt (58.8→53.9) but **60-69 +15.4pt (50.6→66.0)** — the inversion is the high-confidence band improving, not the safe band failing. Two coincident drivers, both at go-live (6/15): **DQ mix flip** (Phase 2 69% MEDIUM → Phase 3 69% HIGH; HIGH−MED gap +7.5→+16.1pt) and the **H1/H3 prompt** improving 60-69 calibration. **CONTROL:** within HIGH-DQ alone the guardrail still inverts (+2.7 → −10.7pt) → not pure composition, a real calibration gain. **Confound ruled out:** not a blanket market shift (50-59 stayed flat; only 60-69 rose — selective to the high-confidence band). **Disposition: Q1-R CLOSED** — go-live calibration improvement, guardrail stays RETIRED (no useful band ordering either direction), **T2 retired** (served its purpose). T1 unchanged (diagnostic only). **Q4-R (DQ-weighting, `Q4R_Scoping.md`) — SCOPED & CLOSED same day:** the Q1-R spinoff (HIGH 58.6% vs MED 43.1% on HOLDs) is **a volatility artifact, not miscalibration.** MEDIUM-DQ HOLDs move ~2x more (median 4.22% vs 2.38%; breach 57% vs 41%); MEDIUM concentrates in inherently volatile names (CBRS 11.6%, AG 6.9%, commodities). **Q4-1** (control for vol): within-tier gap −4.0 to +5.9pt, **within-ticker mean +0.5pt** → no residual DQ signal. **Q4-2** (vol-scaled band): DQ gap +15.5 → +2.8pt (fixed band was unfair to volatile names), but the 60-69 inversion **survives scaling** (−12.1 → −12.9pt) → **Q1-R robust to the metric.** **Disposition: Q4-R CLOSED — no DQ lever** (would penalize correct holds on volatile names); DQ → monitoring / EDGAR-targeting only. **Spinoff/metric finding:** volatility dominates the fixed ±3% HOLD metric (low-vol 90% vs high-vol 20% right) — it substantially measures instrument volatility, not skill; prior findings survive scaling (stand), but a **volatility-scaled metric is worth a parallel secondary report** (not a re-baseline). The day's through-line: **fixed-threshold rules on confidence bands / DQ mislead — instrument volatility is the hidden variable.**

---

## (2) Replacement — the Upcoming block

**Upcoming (Phase 3-B era; every date is a trading day unless noted):**

* **Q1-R: CLOSED** (diagnosed — go-live calibration improvement; guardrail retired; **T2 retired**). **Q4-R: CLOSED** (no DQ lever — volatility artifact). Update the decision worksheet.
* **Open successor thread (optional):** volatility-scaled accuracy metric as a **parallel secondary report** (the ±3% band is volatility-confounded; key findings survive scaling so no re-baseline). Its own scoping if pursued (DP-Q4-c).
* **Resolutions:** **Tue 7/14** 7/7 +5d; **Wed 7/15** 7/8 +5d; **Thu 7/16** 7/9 +5d + GLD +10d; **Fri 7/17** 7/10 +5d + NVDA 7/10 near-miss +5d; **Mon 7/20** **7/13 +5d (first WS1 cohort)** + **NVDA 7/13 near-miss +5d** (the gate-flip verdict).
* **WS1 G2 clock:** 1 cohort (7/13); sparse footprint (1/24 adjusted — only BUY/SELL). First `blend_eval` read ~7/20+. Verdict: overlay predictive value + gate-flip net ≥ 0, cross-validated, ≥ 5 cohorts.
* **H4** near-miss n=6 (pending NVDA 7/20); reopen blocker n ≥ 10. **Registry 22**.
* **Phase 3-C (EDGAR)** — scoped, on the WS1 registry; the DQ input-improvement path (Option C) for the single-stock MEDIUM cases; gated on 3-B exit. (Schwab API has no news endpoint — EDGAR is the primary-source path.)
* **Hygiene** — open+save tracker before each weekly; paste splices as plain text.
* **Standing:** **T1** (pre-execution, mandatory) · **T3** (no band-ordering reliance — reinforced today). **Guardrail SUSPENDED/retired.** **KEEP 70%.** Advisory-only.

---

*Advisory-only · no orders · not financial advice.*
