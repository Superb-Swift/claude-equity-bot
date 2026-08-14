# Phase 3-B — Closeout Memo

*Claude Equity Bot · v1.1 · written 2026-07-31, revised same day after the worksheet was signed and the 07-31 cross-check ran · the G6 instrument, companion to `Phase3B_Closeout_Decision_Worksheet_v1_2.docx`. Evidence is the master `logs\claude_equity_bot_tracker.xlsx` (1,243 rows, 52 cohorts, 2026-05-18 → 2026-07-31), `docs\analyst_notes.md` spliced through 2026-07-31, and the deploy notes and diagnostic memos cross-referenced at §9. Advisory-only · no orders · not financial advice.*

---

## 0 · Verdict, conclusions first

**Phase 3-B ran 19 advisory sessions (2026-07-07 → 2026-07-31), deployed three code workstreams, closed two parked questions, and produced one durable measurement finding. It does not close cleanly, and the reason is worth more than a clean close would have been.**

Two of the six exit gates cannot be settled on evidence — not because the workstreams failed, but because **the pre-registered criteria required event counts that the system's own output rate cannot supply on a phase timescale.** G1 needs four material adverse moves on two named tickers; the market supplied one in nineteen sessions. G2's gate-flip condition needs a favourable disagreement between base and blend; the system emitted 32 BUY signals in 1,243 rows and produced one gate-flip in the entire post-deploy window.

That is the phase's central lesson, and it generalises: **an acceptance criterion is only as good as the event rate that feeds it.** Phase 3-C's E4 pre-registration should be written against observed rates, not round numbers.

The second durable output is a measurement finding, not a workstream result: **the project's headline accuracy metric is substantially a measurement of market dispersion.** That is now arithmetic rather than interpretation (§4.1), and it changes how every prior accuracy figure in the record should be read — without invalidating any of them.

| Gate | Disposition | One-line basis |
|---|---|---|
| **G5** — trigger service | **CLOSED — VERDICT: SERVED** (2026-07-29) | T2 fired, the Tier-2E diff ran, Q1-R is diagnosed |
| **G1** — WS2 (H1 feature) | **INSUFFICIENT TEST CONDITIONS** (2026-07-31) | 1 episode of 4; arrival rate puts four 5–11 weeks out |
| **G2** — WS1 (triple-blend) | **DESCOPE** (signed 2026-07-31) | (A) robust positive, (B) net −1, breadth 90% single-name; never adequately tested |
| **G3** — WS3 (commodity code) | **PARK, with trigger** (2026-07-31) | Never built; E1 prerequisite amended |
| **G4** — operational integrity | **CLOSED — VERDICT** (2026-07-31) | Cross-check streak clean through the exit review, 24/24 on 07-31 |
| **G6** — instruments | **CLOSED — VERDICT** (2026-07-31) | Worksheet v1.2 signed; notes spliced; this memo |

`Phase3B_Closeout_Decision_Worksheet_v1_2.docx` was signed RW / 2026-07-31 across all eleven lines. Two defects in the signed instrument are recorded at §3.7 and require a v1.3 correction; neither changes a disposition.

---

## 1 · What Phase 3-B was

Phase 3-A closed 2026-07-06 with the H1 update-lag finding locked (lag 5, stable, prompt remedy retired) and instructions to implement it at feature level. Phase 3-B opened with three workstreams and a standing mandate of advisory-only operation:

| WS | Deliverable | Deployed | Era |
|---|---|---|---|
| **WS1** | Triple-blend architecture — sector backbone + cross-asset regime overlays, shadow-parallel | 2026-07-13 | `A-S1D1-B1` |
| **WS2** | H1 feature-level implementation — S1 prior-signal state (model-side) + D1 mechanical damping (post-model) | 2026-07-07 | `A-S1D1` |
| **WS3** | Commodity context modules for CORN / GLD / AG | never built | — |

Nineteen sessions, 456 signals: **444 HOLD, 12 BUY, 0 SELL.** Data quality 334 HIGH / 121 MEDIUM / 1 LOW. Resolved +5d cohort accuracy ranged 29.2% to 70.8%, mean 59.2%.

Almost all of the phase's work was measurement discipline rather than model development: pre-registering criteria, then judging evidence against the commitments rather than against what would have been convenient. Several sections below exist because that discipline caught something.

---

## 2 · Governance vocabulary

Carried unchanged from the Phase 3-A closeout:

- **VERDICT** — an evidence-complete conclusion against pre-committed criteria.
- **DESCOPE** — deliberate termination before test. A decision, not a finding.
- **PARK** — an open question shelved with documented re-open triggers.

Phase 3-B adds one, out of necessity:

- **INSUFFICIENT TEST CONDITIONS** — the criterion was correctly specified and correctly measured, and the world did not supply enough events to evaluate it. Not a pass, not a fail, and explicitly *not* an invitation to lower the bar.

The addition is itself a finding. G1's pre-registration admitted PASS and FAIL and assumed one or the other would arrive. It did not anticipate that the operative constraint would be event scarcity. Future gates should carry a stated event-rate assumption alongside their acceptance count.

---

## 3 · Gate-by-gate

### 3.1 · G1 — WS2 (H1 feature): INSUFFICIENT TEST CONDITIONS

**What was built.** Two levers, deployed together under ruling R1 (2026-07-06) as a two-channel readout. **S1** feeds the model its own prior five sessions of signals and confidences — the last untried input-side channel, addressing the hypothesis that the model cannot see its own staleness. **D1** is a deterministic post-model damping rule (THETA 5.0%, K 1.5 pts/%, CAP 15, FLOOR 35) that lowers confidence when the trailing move is materially adverse to the stance. `confidence_raw` carries the clean model-side test; `confidence` carries the engineered output.

**What the one test case showed.** WMT, 2026-07-23: trailing move −5.24% breached THETA; confidence moved **47 → 38 at lag 0**, with **D1 contributing zero damping**. The entire response was model-side. That is precisely what S1 was built to produce, and it is the strongest single observation in the workstream.

**Why it cannot close.** DP-6 (ruled 2026-07-28) established that G1 counts **episodes**, not cohorts — a cohort with no material move carries no information about response-to-material-move. That ruling made G1 stricter and was correct. It also moved G1 from "15 cohorts logged, count met" to **1 independent episode of 4**.

Episode arrival, computed from the master (THETA 5.0%, coalesced):

| Tracer | Pre-deploy | Post-deploy |
|---|---|---|
| WMT | 2 in 28 sessions | 1 in 19 |
| GM | 3 in 28 sessions | **0 in 19** |

Blended full-record rate **0.115 episodes/session**; observed post-deploy rate **0.053**. Three more episodes require roughly **26 further sessions (~5 weeks)** at the full-record rate and **~57 sessions (~11 weeks)** at the observed rate.

*Recorded divergence: this count reads 2 WMT pre-deploy episodes where `monitor_strip.py` reports 1; the coalescing rule or price series differs. Noted, not resolved — post-deploy is 1 on both counts.*

**Neither pre-registered disposition fits.** FAIL means "the raw channel didn't move" and is unavailable, because it demonstrably did. PASS is unavailable at n=1 of 4. Hence the new disposition.

**Self-correction of record.** The exit-criteria document projected "earliest realistic exit review: late July – early August 2026." That projection was computed on cohorts. DP-6 moved the basis to episodes and the timeline was never re-derived. It is re-derived here.

**E2 (quality-no-worse) is untested, not passed.** D1 contributed zero damping on every post-deploy session until 2026-07-30, when it engaged on FTI, AG, SND and NVDA — none of them tracers. On WMT and GM it has never engaged, so operative ≡ raw on both tracers and E2 is trivially satisfied and substantively unexamined.

**The bar was not lowered.** DP-8 (bidirectional episodes) and DP-9 (wider universe) were raised, held deliberately unruled while G1 was blocking, and ruled 2026-07-29 to keep the detector as pre-registered. On 2026-07-30 — the first session where it mattered — relaxing either would have moved G1 from 1 to 6 episodes on a single day's data. Holding the line cost the exit and was the right call.

### 3.2 · G2 — WS1 (triple-blend): open, ruling pending

**What was built.** Two overlays on a common signed scale: **C2** sector backbone (the ticker's sector ETF trailing 20-day trend) and **C3** cross-asset regime (SPY − GLD, one value per day). Fixed pre-registered weights of 0.15 each, deliberately unfitted — the direct lesson of the Q1 guardrail, which certified on Phase-2 data and inverted out of sample. The blend runs **shadow-parallel**: it is logged and resolved but never drives the risk gate. Direction integrity is absolute — overlays modulate conviction only, never flip BUY/HOLD/SELL. Trend scopes are disjoint (C2 sector, C3 market, D1 ticker), so no signal is counted twice.

**Where the evidence stands** (`blend_eval.py --since 2026-07-13`, 15 cohorts, 360 signals, 240 +5d-resolved, 10 blend-adjusted):

- **(A) Overlay predictive value — robust and positive.** Confirmed 40.0% (n=5) vs discounted 20.0% (n=5), gap **+20.0pt**. Leave-one-cohort-out folds `[+30, +30, +5, +5, +40, +15, +30, +7, +15, +20 ×6]` — all fifteen the same sign, min +5pt.
- **(B) Gate-flip @ 70% — net −1.** One disagreement in 11 resolved BUYs: 2026-07-13 NVDA, base 65 / blend 70, blend approves, +5d −2.1%, blend worse.

G2 requires **both**. It cannot pass.

**Two cautions belong in the record, because the summary line hides them.**

First, **the fold array is thinner than it appears.** Six of the fifteen folds equal the full-sample gap exactly, which means six cohorts contain no adjusted signal at all — removing them changes nothing. Only nine folds are informative, across ten adjusted signals. "All folds the same sign" is close to guaranteed when 40% of folds are the null fold. Leave-one-cohort-out is the wrong unit when adjustments are sparse and clustered; **leave-one-adjusted-signal-out (n=10) is the honest test** and has not been run.

Second, **(B) may be structurally unreachable.** One flip in eleven resolved BUYs is a 9.1% rate. Net ≥ 0 requires a *favourable* flip to offset 7/13 — expected ~22 more resolved BUYs, roughly **30 more cohorts (~6 weeks)** at 0.73 BUYs/cohort, for about even odds. Every BUY in the window is NVDA (10) or GLD (1).

**Breadth.** DP-7 (ruled 2026-07-28) added a condition of ≥2 distinct tickers with resolved adjusted signals; GLD's 7/22 signal met it on 2026-07-29. **DP-10** was raised immediately because the letter was satisfied while the spirit was not: the footprint is **9 NVDA : 1 GLD = 90% single-name**. **DP-10 was ruled NO CAP — status quo.** DP-7 therefore stands MET on its original terms. The concentration concern is not resolved by this ruling; it is **accepted as a known limitation of the WS1 evidence base** and should be read as such wherever DP-7 is cited. Any future re-opening of the blend inherits it (see the T-G2-a trigger below).

**Disposition: DESCOPE, signed 2026-07-31.** Of the three live options — DESCOPE, acceptance window INCOMPLETE, or a negative VERDICT — the operator ruled DESCOPE. That is available and defensible: DESCOPE is a decision rather than a finding, and "never adequately tested" is the accurate description of an evidence base of ten adjusted signals at 90% single-name concentration. A negative VERDICT would not have been supportable (scored 3 of 5 against the standard ruled 2026-07-31, with (A) pointing the other way), so the record states that the blend was shelved undecided rather than judged and rejected.

**Effect:** the blend is shelved; the base signal is retained as the official advisory output. Re-open triggers — **(T-G2-a)** at least 15 resolved adjusted signals with a materially broader footprint than 9:1; **(T-G2-b)** gate-flip net ≥ 0 across at least 5 resolved BUYs; **(T-G2-c)** any future workstream that would make the overlays load-bearing.

**A correction of record.** On 2026-07-30 the primary read was assessed as "not robust" on a fold array containing a −10pt entry, and DESCOPE was recommended partly on that basis. The 2026-07-31 re-run resolved that fold to +7 and every fold is now positive. **That premise was withdrawn.** It is recorded here rather than quietly dropped, because a memo that shows only the surviving reasoning misrepresents how the conclusion was reached.

**The design note.** `WS1_TripleBlend_Design_Note.md` remains **DRAFT v1.0, unsigned**, though its own signature condition — DP-W1 and DP-W2 ruled, blend producing cohorts — has been met since 2026-07-13. Its T3 compliance holds on inspection: the combination rule uses direction-agreement × overlay magnitude on continuous confidence and never references band membership. G2's design-note condition failed for want of a signature, not for want of evidence.

### 3.3 · G3 — WS3 (commodity context): PARK, with trigger

The workstream was never built. `commodity_context.py` and `commodity_backed_equity_context.py` appear zero times across `docs\analyst_notes.md`, and `WS1_Deploy_Notes.md` §7 still carries WS3 as an open item.

**Re-open trigger:** a downstream workstream requires commodity context in the prompt, **or** the provider registry proves an insufficient integration template at the 3-C build.

**Amendment to E1, recorded as an amendment.** E1 states that EDGAR is "wired as a per-ticker context module following the WS3 pattern — G3 is therefore a technical prerequisite (WS3 is the integration template)." The template exists, delivered by WS1 rather than WS3: `context_providers.py` ships with `run_prompt_context` wired and the prompt-provider slots deliberately empty, and `Phase3C_EDGAR_Scope_Spec.md` §3 shows `edgar_client` registering in a single line. E1's **rationale** is satisfied by other means while E1's **letter** is not. Adopting the rationale over the letter unblocks work the operator wants to do, which is exactly why it is entered as a dated amendment rather than absorbed as an interpretation.

### 3.4 · G4 — operational integrity: open

The daily log↔master cross-check held at 24/24 on every session directly verified. Resolutions are complete at all three horizons with zero missing — the first point in the 3-B record at which that was true.

**The exit-review cross-check ran clean.** `signals_2026-07-31.log` ↔ the master reconciled **24/24** on signal, confidence, data quality and price at signal, zero findings, closing the streak through the exit review as the criterion requires. Clerical items closing alongside it: two ghost rows annotated rather than deleted (Excel rows 222 and 226, 2026-06-01, AG and FTI — null signal/confidence/DQ but a complete price series at all four columns, so deletion would discard resolved outcomes to repair a metadata gap); the retired `Sheet1` guardrail tab deleted at source in the master; and the missing 2026-07-24 daily entry reconstructed. **Disposition: VERDICT — integrity maintained.**

### 3.5 · G5 — trigger service: CLOSED, VERDICT: SERVED

T2 fired 2026-07-13 on the pooled counter (depth n=100/88, non-compressed lead −15.4pt) exactly as ruling R2 anticipated. The Phase-2-vs-live prompt and distribution diff ran, Q1-R was diagnosed (§5.1), and T2 was retired as a tripwire having served its purpose. No FIRED-and-unserviced trigger remains.

### 3.6 · G6 — instruments: open

Worksheet drafted → v1.1 → v1.2 with dispositions entered and signed 2026-07-31. `analyst_notes.md` spliced through 2026-07-31. This memo is written. **Disposition: VERDICT — instruments complete**, subject to the v1.3 corrections at §3.7 and to archive and push housekeeping.

### 3.7 · Two defects in the signed instrument

Recorded because the instrument is the artifact, and both require a v1.3 correction. Neither changes a disposition.

**DP-10 is stated two ways.** The §3 table body reads **"No Cap"** — which is the ruling — while the signature line reads *"DP-10 cap value set at 70%,"* signed the same day. The operative ruling is **NO CAP, status quo**; the signature line is the error and should be corrected to match, dated.

**§6.2's G2 scoring is superseded.** It records *"(ii) MET — one fold at −10pt and the criterion requires all folds the same sign."* The 2026-07-31 `blend_eval.py` re-run returned all fifteen folds positive, min +5pt, so (ii) FAILS. The DESCOPE **decision** stands — it does not rest on that condition — but the recorded reasoning is stale and needs a dated correction rather than a silent edit.

A third, cosmetic: DP-9's correction note was attached to the corrected wording rather than to the superseded *"to GM,"* so it now reads as though the current ruling is the broken one.

---

## 4 · Findings that outlive the phase

### 4.1 · The headline accuracy metric is substantially a dispersion measurement

**This is the most important finding in Phase 3-B and it is arithmetic, not interpretation.**

Across all 47 resolved +5d cohorts, the correlation between HOLD band-breach count and cohort accuracy is **−0.9650**, and the relation `accuracy = (n − breaches − directional misses) / n` holds **exactly in 47 of 47 cohorts**, with directional misses averaging 0.45 per cohort. Because the watchlist output runs ~96% HOLD, **measured accuracy is the band-breach count plus a rounding term.**

The non-trivial content is what breach count depends on: market dispersion, not the generator. And the horizon data shows the metric degrading structurally as the window lengthens:

| Horizon | Accuracy | HOLD rows breaching ±3% | Median \|move\| |
|---|---|---|---|
| +5d | 54.7% (n=1,123) | 488/1,088 = **44.9%** | 2.61% |
| +10d | 43.3% (n=1,003) | 543/974 = **55.7%** | 3.54% |
| +20d | 32.6% (n=763) | 497/740 = **67.2%** | 5.35% |

**The median HOLD crosses the ±3% band between +5d and +10d.** At +10d and beyond, being scored wrong is the modal outcome for a HOLD regardless of signal quality.

**How to read the record in light of this.** The 2026-07-20 → 07-22 sequence (70.8% → 41.7% → 29.2%) looks like generator degradation and is not: dispersion rose from sd 6.02% to 7.54% and 13 then 15 HOLD names breached the band, splitting near-evenly up and down. When 7/23 and 7/24 resolved at 58.3% each, breaches had fallen to 9 — accuracy recovered because fewer names crossed the band, not because signals improved.

**What does not change.** The ±3% band is **not re-baselined**. Q4-2 established that the key inversions survive volatility scaling, so every prior finding stands. The recommendation is a **parallel secondary** volatility-scaled report, reported alongside and never in place of the fixed-band metric — switching would orphan the Phase-2 baseline and every conclusion built on it.

### 4.2 · Directional-signal scarcity is a structural constraint, not bad luck

Across the entire record, **32 BUY signals in 1,243 rows — 2.6% of output — and 25 of the 32 are NVDA.** No SELL signals at all.

This single fact is the common cause of several apparently unrelated problems:

- **G2's (B) gate-flip condition** is underpowered because gate-flips require BUYs.
- **DP-7 and DP-10** collide with concentration because the adjusted-signal population inherits the BUY population's 78% single-name skew.
- **The near-miss registry** accumulates slowly, and H4's DQ-conditional gate has spent the phase at n=10–13.
- **Any confidence-pipeline lever** — D1, the blend, a hypothetical DQ damper — has a "tiny actionable footprint," because HOLD confidence drives no action under advisory-only.

Q4-R identified this for the DQ lever specifically. It generalises: **in a HOLD-dominated advisory system, any mechanism gated on directional output will be starved.** Phase 3-C should assume it.

### 4.3 · Small-n readings reverse, and pre-committing to the reading is the only defence

Demonstrated three times in nine days. H4's reopening bar: 6/10 = 60.0000% (7/27) → 6/11 = 54.5% (7/28) → 6/12 = 50.0% (7/29) → 6/13 = 46.2% (7/31) — a pass on the weakest evidence the rule admits, reversed within 24 hours. G2's primary read: −10.0 → +15.0 → +20.0pt across three consecutive sessions, sign flipped on two observations. G2's fold robustness: not robust on 7/29, robust on 7/31.

The response adopted mid-phase — **no DQ-conditional design work until two consecutive readings pass at n ≥ 12** — is the pattern worth carrying: a confirmation requirement attached to the criterion *before* the number is seen.

### 4.4 · A tool defect that was not one

Raised on 2026-07-30 and again on 07-31: the `D[...]` log tag reported damping that did not match the change in operative confidence — AG damp 6 against a raw−op delta of 0, SND damp 6 against a delta of 3. It was classed as the same family as the four tooling faults cleared during the phase: a tool printing a number it did not act on.

**It is not a defect.** D1's **FLOOR = 35** clamps the reduction and never raises confidence, so where the floor binds the applied reduction is smaller than the computed damp — and where raw already sits below the floor, no reduction is applied at all. The rule `op = raw if raw < FLOOR else max(FLOOR, raw − damp)` predicts **7 of 7** damped rows across 2026-07-30 and 07-31 exactly. The D tag reports the *computed* damp rather than the *applied* reduction: a naming imprecision, not an arithmetic error.

The error was in the checking tool. `signal_scan.py` asserted the naive identity `damp == raw − op` and emitted a false FAIL on every floor-bound row. The assertion has been replaced with the floor-aware one; both sessions now pass clean.

**The lesson is the mirror of the phase's other tooling lessons.** Four defects were found because tools reported conclusions they had no evidence for. This one was manufactured because a tool asserted an identity stricter than the system's actual rule. An assertion that does not model the mechanism produces false positives at exactly the rate it produces confidence — and a false defect costs the same review time as a real one.

---

## 5 · Questions closed during the phase

### 5.1 · Q1-R — DIAGNOSED and CLOSED (2026-07-13)

The Phase-2 guardrail ("50-59 leads 60-69") inverted live. The Tier-2E diff established that **the guardrail did not break — the model became better calibrated.** The 60-69 band improved +15.4pt (50.6% → 66.0%) while 50-59 barely moved (−4.8pt). Two coincident drivers at the 2026-06-15 go-live: the data-quality mix flipped (69% MEDIUM → 69% HIGH) and the band shed its weak MEDIUM signals; and, holding DQ fixed at HIGH, 60-69's calibration genuinely improved +11.5pt — the control that rules out pure composition.

**Disposition: the suspended guardrail stays RETIRED.** There is no useful band ordering to reinstate in either direction. T3 (no band-ordering reliance) is not merely vindicated but strengthened — bands are no longer the informative axis. T2 retired as a tripwire.

### 5.2 · Q4-R — CLOSED, no DQ lever (2026-07-13)

The diff's spinoff was that data quality separated accuracy more than any confidence band (HIGH 58.6% vs MEDIUM 43.1%). The tempting move was to down-weight MEDIUM. **On inspection that would have been wrong.** Within volatility tiers the +15.5pt raw gap collapses to between −4.0 and +5.9pt and *reverses* in mid and high vol; within-ticker, holding volatility exactly constant, the mean HIGH−MEDIUM difference is **+0.5pt across 9 tickers**. The gap is instrument volatility, not miscalibration: MEDIUM-DQ names (CBRS, AG, SND, NVDA) simply move about twice as much, so they breach a fixed band more often.

**Disposition: no DQ lever.** DQ remains a monitoring and EDGAR-targeting signal. A mechanical down-weight would have penalised correct holds on volatile instruments.

### 5.3 · KEEP 70% — supported, seven consecutive improvements

Near-miss BUYs rejected by the 70% gate that would have paid: **13 of 32 = 40.6%**, improving from 50.0% on 7/24 through 48.1%, 46.4%, 43.3%, 41.9% to 40.6%. Comfortably under the 50% line that supports the gate. The 2026-07-23 watch item is closed in substance. **KEEP 70% carries into 3-C unchanged.**

### 5.4 · H4 — stays demoted

HIGH-DQ near-miss accuracy **6/13 = 46.2%** against a ≥60% bar; four consecutive declining reads. The n ≥ 12 confirmation rule, adopted 7/28 and applied as intended, confirms the 7/27 pass was an artifact of n crossing its bar. No DQ-conditional design work.

---

## 6 · Standing constraints into Phase 3-C

| Constraint | Status |
|---|---|
| **T1 — advisory only** | In force. No execution, ever. Execution remains its own future gate. |
| **T3 — no band-ordering reliance** | In force, now tool-enforced by `retired_criteria_audit.py`. |
| **Q1 guardrail** | RETIRED. Not suspended — retired, per Q1-R. |
| **T2** | RETIRED. No standing tripwire on band ordering remains. |
| **KEEP 70%** | Unchanged. |
| **±3% HOLD band** | Unchanged and NOT re-baselined. Vol-scaled reporting is parallel-secondary only. |
| **CBRS Path A** | Excluded to Q4 2026. |
| **Watchlist** | 24 tickers; frozen through 3-B, reviewable at the 3-B/3-C boundary. |
| **DP-5** | RULED 2026-07-31 — overlap permitted for 3-C scope work only; no go-live, no gate closes or relaxes. |

---

## 7 · What Phase 3-C inherits

**Ready.** The provider registry (`context_providers.py`) with `run_prompt_context` wired and prompt-provider slots empty — EDGAR is a one-line registration. `Phase3C_EDGAR_Scope_Spec.md` covers E1 scope content, E3 data/ops preconditions (SEC endpoints, mandatory User-Agent, ≥120 ms rate delay, graceful degradation) and E4 measurement pre-registration. E5 constraint compliance is stated. The pre-deploy parser audit checklist exists, carrying the ACCOUNT_RE lesson.

**Needs doing.** E1's named instrument (`Phase3C_Kickoff_Prompt.md`) with a worksheet-entered scope. DP-2 ruled (default: single-arm era stamp `A-S1D1-B1-E1`). DP-3 (CBRS skip), DP-4 (no `data_quality` coupling in v1), DP-3C-a/b/c.

**The measurement lesson to apply at E4.** Both of 3-B's unclosable gates failed on event scarcity, and the scarcity was predictable from the record. E4's endpoints — DQ-mix shift, filing-adjacent accuracy, event-window behaviour — should each carry an explicit **expected event rate and the resulting time-to-read**, computed before go-live. If an endpoint needs more filing-adjacent cohorts than the watchlist can produce in a phase, that must be visible at pre-registration, not discovered at the exit review.

**Carried open items.** `monitor_strip.py`'s "last episode" date computed pre-coalescing — it reports the last qualifying session, not the last coalesced episode; T2's tooling still printing live instructions on a retired tripwire; three audit exclusions before the pre-commit hook (`Retired\`, `docs\analyst_notes.md`, and `T2` where it is a test-case ID); `build_near_miss_registry.py` and `blend_eval.py` unaudited for formula-cache exposure; `h4_dq_threshold.py`'s stale console string. **Closed during the exit review:** the two ghost rows (annotated), the retired `Sheet1` tab, the missing 7/24 entry, and the D1 damp question (§4.4). The v1.3 worksheet corrections at §3.7 also carry.

---

## 8 · Operational lessons

Recorded because each was learned by being caught, several by accident.

- **The formula cache.** `Return+5d` / `Return+10d` / `Was-Right-5d` are formulas; openpyxl reads cached values and any openpyxl save clears them, which the daily runner does every session. The file must be opened in Excel after each run. Two harnesses had silent exposure to this and neither was suspected in advance. **Compute from the Price columns wherever possible — those are cache-independent.**
- **A renamed tab is still the tab it was.** A retired guardrail sheet re-entered the report copy as "Sheet1" and slipped a name-based purge. Matching is now by content. It is still in the master.
- **A clean console is not a completed run.** `h1_lag_trace.py` printed a full, correct-looking trace and then crashed writing its `.md`, leaving the previous exhibit on disk looking current. Check the `Wrote:` line.
- **Retired criteria drift back.** Four instances found by accident before `retired_criteria_audit.py` was built; more after. The recurring shape is a *corrected value surviving in a second code path* — `h1_lag_trace.py`, `h4_dq_threshold.py`, `t2_check.py`, the renamed sheet, and `monitor_strip.py`'s episode date.
- **The historical record is never rewritten to match present belief.** Entries describe what was believed when written. This is why `docs\analyst_notes.md` is excluded from the audit, and why the 2026-07-29 entry recording DP-8/DP-9 as unruled was left standing when the rulings were spliced in on 07-31.
- **Tools should assert, not just report — but an assertion must model the mechanism.** The harnesses added 2026-07-30 caught a confidence-channel naming collision nobody was looking for, and also manufactured a false defect by asserting a damping identity stricter than D1's actual floor rule (§4.4).
- **Cross-validate on the unit that carries the evidence.** G2's leave-one-*cohort*-out folds read robust while six of fifteen folds were the null fold, because most cohorts contained no adjusted signal at all. With sparse, clustered events the honest unit is the event, not the period.

---

## 9 · Cross-references

- `Phase3B_Closeout_Decision_Worksheet_v1_2.docx` — the signing instrument; dispositions and their evidence.
- `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1.docx` — the pre-registered gates this memo reports against.
- `WS2_H1_Feature_Spec.md` / `WS2_Deploy_Notes.md` — the S1/D1 build, rulings R1/R2, the §4b acceptance-scan caveat.
- `WS1_TripleBlend_Design_Note.md` / `WS1_Implementation_Spec.md` / `WS1_Deploy_Notes.md` — the blend design, the provider registry, the shadow-parallel discipline.
- `Q1R_Diagnostic_Memo.md` — the guardrail inversion diagnosed.
- `Q4R_Scoping.md` — the DQ question closed; the volatility-confound lesson.
- `Phase3C_EDGAR_Scope_Spec.md` — E1/E3/E4 content for the next phase.
- `Daily_Workflow_v5_3_Phase3B.docx` — the operating procedure these gates are read against.
- `docs\analyst_notes.md` — the institutional record, spliced through 2026-07-31.

---

**Status: v1.1** — all six gates carry a disposition. `Phase3B_Closeout_Decision_Worksheet_v1_2.docx` signed RW / 2026-07-31. Outstanding: the v1.3 worksheet corrections (§3.7), this memo's signature, and archive/push housekeeping. Phase 3-C scope work is unblocked under the DP-5 overlap ruling.

*Advisory-only · no orders · not financial advice.*
