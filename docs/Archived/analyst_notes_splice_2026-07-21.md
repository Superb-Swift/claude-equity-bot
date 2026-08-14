# analyst_notes.md — monitoring splice (2026-07-21)

*Paste target: `docs/analyst_notes.md`. Two edits: (1) insert the dated bullet below immediately AFTER the 7/20 entry; (2) replace the Upcoming block. **PASTE AS PLAIN TEXT.** All figures price-computed from the tracker (Return/Right columns remain formulas with an empty cache — see the 7/20 entry). +Nd = trading days.*

---

## (1) New dated bullet — insert after the 7/20 entry

* **7/21 (Phase 3-B Day 11) — H4's hit rate falls BELOW its reopen bar (now failing on merit, not sample); NVDA 7/14 resolves wrong with blend and base AGREEING; tracers move but not materially.** **Cross-check 24/24** — log↔tracker operative reconcile clean; era `A-S1D1-B1`; **no effective damping**; DQ **18 HIGH / 6 MED / 0 LOW**; **23 HOLD + 1 BUY (NVDA 61, rejected <70)**; totals **1,051 rows**. **NVDA 61% (HIGH) — eighth consecutive near-miss → registry 27 → 28**; five pending (7/15, 7/16, 7/17, 7/20, 7/21). **RESOLUTION — 7/14 cohort resolved 24/24, accuracy 16/24 = 66.7%** (12/24 up — flat tape). **RESOLUTION — NVDA 7/14 near-miss (65%, HIGH) +5d = −0.43% → WRONG; the gate was right again.** Notable for WS1: the blend did **not** flip this one (blend 66, below the 70 gate), so **blend and base AGREED and both were correctly cautious** — the first case where the overlays' judgment aligned with the correct outcome. **★ H4 — the reopen question is now FAILING ON MERIT, not just sample size.** HIGH-DQ near-miss **hit rate 4/7 = 57%**, which is **below the ≥60% reopen bar**; trajectory **80% → 67% → 57%** as the NVDA cases resolve wrong. Criteria status: n ≥ 10 resolved → **7 (short)**; hit ≥ 60% → **57% (now FAILING)**; HIGH ≥ MEDIUM overall → 61.9% vs 43.9% ✓. A week ago H4 looked one signal from reopening; it is now failing the quality bar itself. If this holds, **H4 stays demoted because the evidence says so** — a cleaner outcome than tripping on a technicality. **KEEP-70% strengthening again:** all resolved near-miss BUYs **10/23 = 43.5%** (from 45.5%) — under half of rejected BUYs would have paid. **Q1-R holds:** live **60-69 = 64.3% (n=143)** vs 50-59 **57.1% (n=203)**. **DQ live:** HIGH 61.9% vs MEDIUM 43.9% — stable; no action per Q4-R. **BLEND:** NVDA 61 → 62 (sector −0.232, regime softened to +0.288 — the weakest risk-on reading of the series); no flip. **WS2 acceptance clock — tracers MOVED but it is NOT an episode:** **GM 54 → 58** (+4, the largest post-deploy single-session move) and **WMT 47 → 45**, ending WMT's ten-session pin. **But GM's trail was +0.63% — confidence rose on a SMALL POSITIVE move**, whereas the acceptance test requires a **material ADVERSE** trailing move with a ≤ 2-session confidence response. This does not qualify. **11 post-deploy cohorts (7/7–7/21), still all null for the acceptance instrument.**

---

## (2) Replacement — the Upcoming block

**Upcoming (Phase 3-B era; every date is a trading day unless noted):**

* **Resolutions:** **Wed 7/22** 7/15 +5d + NVDA 7/15 near-miss; **Thu 7/23** 7/16 +5d + NVDA 7/16; **Fri 7/24** 7/17 +5d + **NVDA 7/17 (first DISCOUNT case)**; **Mon 7/27** 7/20 +5d + NVDA 7/20 (second discount); **Tue 7/28** 7/21 +5d + NVDA 7/21.
* **WS1 G2 clock:** first read negative (gate-flip net −1; confirm arm 0/1). 7/14 added an **agreement** case (blend no-flip, base correct). **Re-run `blend_eval --since 2026-07-13` after 7/24** (discount arm finally populated) and again as the series completes. **HARD CAVEAT: the entire blend footprint is one ticker (NVDA)** — any G2 read is a single-name result, not portfolio-level; state it explicitly at the verdict.
* **H4 — FAILING ON MERIT.** Hit rate **57% (4/7)**, below the ≥60% bar; n still short at 7 resolved. Four more resolve 7/22–7/28. **Likely disposition: stays demoted on evidence** — record it that way rather than as a sample-size technicality.
* **KEEP-70% — holding out-of-sample:** all resolved near-misses **10/23 = 43.5%**; GLD +10d reversal; NVDA series now 5/17 ≈ 29%.
* **WS2 acceptance clock:** **11 null cohorts.** 7/21's tracer moves (GM +4, WMT −2) do **not** qualify — the test needs a **material ADVERSE** move with a ≤2-session response. *Standing risk: if no episode before the 3-B exit review, **G1 is unreadable** — flag as "insufficient test conditions"; do NOT lower the bar.*
* **TRACKER HYGIENE (verified):** **open in Excel → F9 → save before every weekly run.** Return/Right columns are formulas with an **empty** cache; `h1_lag_trace.py` reads r5/r10/right5 directly and will run on blanks without the recalc. `t2_check`, `blend_eval` and the daily analyses compute from Price columns and are unaffected. *Durable fix available (~5 lines) — see the 7/20 entry.*
* **VISUALIZATION (new):** the guardrail-trace PNG is being squished as cohorts accumulate (38+ and growing daily). Redesign options under discussion — see the 7/21 session notes.
* **Registry 28.** **Watch items** (60-69 variance, DQ mix) **CLOSED**.
* **Watchlist:** **no mid-window population change** (JEPI queued for the 3-B exit / 3-C entry boundary).
* **Q1-R: CLOSED.** **Q4-R: CLOSED** (no DQ lever). **Optional successor:** volatility-scaled accuracy metric as a parallel secondary report.
* **Phase 3-C (EDGAR)** — scoped, gated on 3-B exit. **3-B exit review** earliest late-Jul / early-Aug. *Note for the review: WS1/G2 trending negative on a single-name footprint; WS2/G1 likely unreadable; H4 likely demoted on merit.*
* **Standing:** **T1** (pre-execution, mandatory) · **T3** (no band-ordering reliance). **Guardrail SUSPENDED/retired.** **KEEP 70%.** Advisory-only · no orders.

---

*Advisory-only · no orders · not financial advice.*
