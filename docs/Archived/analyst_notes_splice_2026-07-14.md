# analyst_notes.md — monitoring splice (2026-07-14)

*Paste target: `docs/analyst_notes.md`. Two edits: (1) insert the dated bullet below immediately AFTER the CONSOLIDATED 7/13 entry; (2) replace the Upcoming block. **PASTE AS PLAIN TEXT.** All figures verified against `signals_2026-07-14.log` and the tracker (uploaded as `claude-equity-bot-tracker.xlsx` — same 7-tab schema; returns computed from the Price columns). +Nd = trading days.*

---

## (1) New dated bullet — insert after the 7/13 entry

* **7/14 (Phase 3-B Day 6) — the 7/7 cohort (first full S1+D1) resolves 24/24 at 62.5%; Q4-R's volatility artifact shows up live; NVDA repeat near-miss.** **Cross-check 24/24** — log↔tracker operative reconcile clean; era `A-S1D1-B1`, blend fields on all 24; **no effective damping** (third calm session); DQ **17 HIGH / 7 MED / 0 LOW**; **23 HOLD + 1 BUY (NVDA 65, rejected <70)**; totals **931 rows**. **NVDA 65% (HIGH) new near-miss — third in five sessions (7/10 @63 MED, 7/13 @65 HIGH, 7/14 @65 HIGH) → registry 22 → 23**; all three +5d pending (7/17, 7/20, 7/21). **RESOLUTION — 7/7 cohort (the first full S1+D1 cohort) resolved 24/24, accuracy 15/24 = 62.5%**; its 60-69 band n=8 came in 4/8 = 50%. **The four D1-damped names resolved:** PWR HOLD op47 → +2.20% **RIGHT**; AIQ HOLD op47 → +0.29% **RIGHT**; SND HOLD op40 → +7.66% **WRONG**; CBRS HOLD op35 → **+15.97% WRONG**. **Both "wrong" ones are precisely the Q4-R volatility artifact** — CBRS median |+5d move| **10.42%**, SND 5.09%, so a fixed ±3% HOLD band is near-impossible for them to satisfy; yesterday's scoping predicted this pattern and it appeared unprompted the next session. (D1's direction was defensible on both — it cut conviction on signals that proved wrong — but at n=4 that is an observation, **not** evidence; the acceptance instrument remains the WMT/GM tracer.) **Q1-R robustness check:** live **60-69 = 64.8% (n=108)** vs 50-59 **55.3% (n=159)** — the diagnosis holds. The 7/7 cohort's 50% is **within normal cohort variance** (60-69 by cohort has ranged 27.3%–87.5% across the live era), not a trend — logged as a watch item only. **Blend, day 2 — a same-signal / different-verdict pair:** NVDA repeated BUY 65 but blended **65 → 66 today vs 65 → 70 yesterday** — the sector score deteriorated sharply (−0.079 → **−0.44**, XLK selling off) while regime softened (+0.609 → +0.514), so the overlays nearly cancelled → **no gate-flip today**. Context-sensitivity working as designed, and a fair caution that 7/13's gate-flip was marginal; the two resolve 7/20 and 7/21 → a natural paired comparison for `blend_eval`. **H4:** HIGH-DQ near-miss **4/5 resolved = 80%**, total 7 (2 pending); HIGH 59.1% ≥ MEDIUM 42.7% ✓; **n-blocker (≥10) unchanged** → stays demoted. **DQ live:** HIGH 59.1% vs MEDIUM 42.7% — stable, and per Q4-R **no action** (volatility composition, not miscalibration). **WS2 acceptance clock:** WMT 45→45→47→46→47→47→47, GM 52→52→52→54→55→55→55 — **6 post-deploy cohorts (7/7–7/14), all null for the tracers**; still awaiting a material episode. **Flag:** tracker arrived named `claude-equity-bot-tracker.xlsx` (hyphens) rather than `tracker_with_registry.xlsx` — identical schema, but if it has been renamed on disk, `t2.bat` / `seed_signal_state.py` / the weekly harnesses all reference the old name and would not find it.

---

## (2) Replacement — the Upcoming block

**Upcoming (Phase 3-B era; every date is a trading day unless noted):**

* **Resolutions:** **Wed 7/15** 7/8 +5d; **Thu 7/16** 7/9 +5d + GLD 65% +10d; **Fri 7/17** 7/10 +5d + **NVDA 7/10 near-miss +5d**; **Mon 7/20** **7/13 +5d (first WS1 blend cohort)** + **NVDA 7/13 near-miss +5d (the gate-flip verdict)**; **Tue 7/21** 7/14 +5d + **NVDA 7/14 near-miss +5d** (the no-flip half of the pair).
* **WS1 G2 clock:** 2 cohorts logged (7/13, 7/14); footprint sparse (1/24 adjusted each day — only BUY/SELL adjust). First `blend_eval` read ~7/20+. The **NVDA 7/13 (flip, blend 70) vs 7/14 (no flip, blend 66) pair** is the first natural test of overlay predictive value. Verdict G2: overlay predictive value (confirm > discount) + gate-flip net ≥ 0, cross-validated, ≥ 5 cohorts.
* **WS2 acceptance clock:** 6 null cohorts (7/7–7/14) — needs a **material trailing move on WMT (primary) / GM (secondary)** with confidence response ≤ 2 sessions, read on the RAW channel (`h1_lag_trace … --raw-from-logs "logs\signals_*.log" --suffix _raw_3B`). Ignore the full-series corr-scan until an episode lands.
* **H4** — HIGH-DQ near-miss 4/5 = 80%, total 7; reopen blocker n ≥ 10. **Registry 23** (three NVDA entries pending).
* **Watch item (no action):** 60-69 cohort accuracy — 7/7 came in at 50% (n=8); live band still 64.8% (n=108). Only a sustained run of sub-50% cohorts would warrant revisiting the Q1-R diagnosis.
* **Q1-R: CLOSED** (go-live calibration improvement; guardrail retired; **T2 retired**). **Q4-R: CLOSED** (no DQ lever — volatility artifact). **Optional successor thread:** volatility-scaled accuracy metric as a **parallel secondary report** (not a re-baseline) — its own scoping if pursued.
* **Phase 3-C (EDGAR)** — scoped, on the WS1 provider registry; gated on 3-B exit sign-off. **3-B exit review** earliest late-Jul / early-Aug (`Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1`, G1–G6).
* **Hygiene** — open+save the tracker in Excel before each weekly (formula cache for `h1_lag_trace`); paste splices as plain text; confirm the tracker filename matches what the tools expect.
* **Standing:** **T1** (pre-execution, mandatory) · **T3** (no band-ordering reliance — reinforced by Q1-R/Q4-R). **Guardrail SUSPENDED/retired.** **KEEP 70%.** Advisory-only · no orders.

---

*Advisory-only · no orders · not financial advice.*
