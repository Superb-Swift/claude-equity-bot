# Closing Review — 2026-08-18

*Claude Equity Bot · Phase 3-C · E4 cohort 4 · era `A-S1D1-B1-E1` · advisory-only · no orders · not financial advice.*

**Cross-check 25/25 CLEAN** `[V]` — `signals_2026-08-18.log` ↔ `logs\claude_equity_bot_tracker.xlsx`, reproduced independently from the log JSON at full precision (signal, confidence, DQ, Price at Signal); zero rows in the log and absent from the master, zero the other way. Era `A-S1D1-B1-E1` in every Signal JSON and in no phase bracket; `regime_score` uniform at −0.306 across all 25; confidence channels present on all rows; totals **1,536 rows, 64 cohorts**. Resolutions complete at all three horizons. Every figure in this entry is computed from the Price columns and is formula-cache independent.

---

## 1 · What resolved, and it resolved exactly as pre-committed

### 1.1 ★★ KEEP-70 IS SUPPORTED AT 19/40 = 47.50%, AND THE 8/14 BOUNDARY RULING DID NOT HAVE TO CARRY IT

Both 2026-08-11 near-miss rows resolved at +5d and **both paid NO** `[V]`:

| row | conf | DQ | Price at Signal | Price +5d | +5d return | scored |
|---|---|---|---|---|---|---|
| NVDA 8/11 | 68 | HIGH | 219.75 | 219.74 | **−0.004551%** | NO |
| GLD 8/11 | 68 | HIGH | 403.265 | 398.55 | −1.169206% | NO |

The 8/14 branch tree closed 8/17 at **19/38 = 50.00% — SUPPORTED by exactly zero margin**, entirely on the boundary ruled that day (SUPPORTED ⟺ rate ≤ 50.0%). Two NOs take it to **19/40 = 47.50%**, supported with margin and not dependent on the boundary. Registry unchanged at **43**; three rows still pending (NVDA 8/12, GLD 8/12, GLD 8/13). Monitor strip agrees: `47.5% (19/40) · supported`.

**★ NVDA MISSED BY ONE CENT.** 219.75 → 219.74 is a −$0.01 move on a $219.75 price, and the sign test has no dead band. That single cent is the whole difference between 19/40 and 20/40. Recorded because the record already carries the mirror case — NVDA +0.005% scored YES on 2026-08-04 — and the pair establishes that near-miss dispositions are being decided at the tick.

### 1.2 ★★ THE BRANCH TREE'S ARITHMETIC WAS RIGHT AND ITS SCHEDULE WAS WRONG, AND THE RULING'S OWN "EXACTLY ONE READING" CLAIM IS FALSIFIED BY IT

§3 of the pre-commitment enumerated the worst case as `8/11 NVDA (~8/18) → 20/39 = 51.28% → NOT SUPPORTED` and `8/11 GLD (~8/19) → 21/40 = 52.50%`. **Both rows belong to the 8/11 cohort and therefore resolve on the same session.** The 39-row node never existed. Under the schedule the trading-day index actually produces, today's three possible outcomes were 19/40 = 47.50%, **20/40 = exactly 50.00%**, and 21/40 = 52.50%.

So a 1-of-2 outcome today would have landed on the boundary a **second** time, and the ruling would have been decisive again — against its own stated limit that it *"changes the disposition on exactly one reading and defers nothing beyond it."* **The claim is falsified as written.** The ruling itself is unaffected — it is a boundary definition and it is correct — but its self-description was computed from a resolution schedule that does not exist, and that is worth more than the arithmetic error, because the whole point of the branch tree is that it is enumerated in advance.

**Direction, stated per house practice: this runs against the ruling and against the operator's convenience.** The outcome went the gate's way regardless, so nothing is being defended after the fact.

### 1.3 ★★ H4's FIRST PASSING READING WAS REVERSED AT THE VERY NEXT READING — THE TWO-CONSECUTIVE RULE IS WHAT STOPPED A PROMOTION

`[V]` HIGH-DQ near-miss +5d, computed from the Price columns:

| session | reading | vs ≥60.0% bar |
|---|---|---|
| 8/17 | 11/18 = **61.1%** | **PASS** — first passing reading at n ≥ 12 |
| 8/18 | **11/20 = 55.0%** | **FAIL** |

Both of today's HIGH-DQ resolutions were NO, so n rose by 2 and the numerator did not move. **H4 STAYS DEMOTED.** MEDIUM reads 8/20 = 40.0%; registry HIGH total 23.

The pre-commitment said in advance that *"H4 promotes on neither branch. The bar is two consecutive passing readings; a YES gives the first, and a second is required after it."* The second reading arrived on the next session and failed. This is the **sixth** reversal of H4 on small n (60.0000% → 54.5% → 50.0% → 46.2% → 61.1% → 55.0%), and it is the first time the two-consecutive rule has actually prevented a disposition rather than merely delayed one. **Record it as the rule paying for itself**; it was written on 7/28 precisely against this failure mode and it has now caught it.

### 1.4 ★★ THE ROW-VS-EPISODE BASIS NOW GIVES OPPOSITE DISPOSITIONS ON KEEP-70

| basis | reading | under the ruled `> 50%` rule |
|---|---|---|
| ROW | 19/40 = **47.50%** | **SUPPORTED** |
| EPISODE (consecutive-session runs per ticker, scored on the opening row per DP-3C-m) | 10/18 = **55.6%** | **NOT SUPPORTED** |

**The coalescing rule is verified, not assumed** `[V]`: the same code reproduces the record's 8/17 episode figure of 10/17 = 58.8% exactly. Today's 18th episode is NVDA 8/11–8/12, whose opening row resolved NO. The 7-row GLD run 8/05–8/13 counts once, as YES.

The pre-commitment named the basis question as *"the open item and… urgent."* It is now **decision-relevant rather than theoretical**: the two bases straddle the boundary and disagree on the disposition of a live gate. Nothing is ruled here. The figures are reported on both bases, per the 8/14 rule that a figure is quoted with its population attached.

### 1.5 Cohort resolutions, all three horizons `[V]`

| horizon | cohort | accuracy | mean | sd(pop) | HOLD breaches |
|---|---|---|---|---|---|
| +5d | 2026-08-11 | 13/24 = **54.2%** | +0.40% | **3.31%** | 9 (5 UP / 4 DOWN) |
| +10d | 2026-08-04 | 12/24 = 50.0% | +2.70% | 4.57% | 12 |
| +20d | 2026-07-21 | 9/24 = **37.5%** | +5.04% | 6.10% | 15 |

The 8/11 cohort is the **quietest tape in weeks** — sd 3.31% against a recent run of 6–9% — and the breach count fell with it. Movers: SND +8.63%, CORN +4.99%, FTI +4.59%, PWR +4.37% against GM −6.36%, MSFT −4.44%, CBRS −4.15%. The +20d reading of 37.5% is the fixed band meeting a twenty-day horizon on a rising tape (mean +5.04%) and carries the standing annotation; it is not generator degradation.

---

## 2 · GM left the watchlist, and nothing in the monitoring stack noticed

### 2.1 ★★ THE DETECTION GAP RULED ON 8/14 FIRED ON THE FIRST SESSION AFTER THE RULING, ON THE WORST AVAILABLE NAME

Session-over-session set difference, computed because no tool does it `[V]`:

| session | n | added | dropped |
|---|---|---|---|
| 8/11 | 24 | — | — |
| 8/12 | 24 | — | — |
| 8/13 | 25 | SPCX | — |
| 8/14 | 25 | — | — |
| 8/17 | 26 | USO | — |
| **8/18** | **25** | — | **GM** |

The 8/14 ruling's consequence (ii) stated the gap in exactly these terms: *"No existing tool compares cohort membership session-over-session… A one-line set-difference against the prior cohort would have caught this and should be added."* It was not added. GM's last row is **2026-08-17**; GM has 63 rows in the master.

**GM is the single worst name to lose**, for four independent reasons:

1. **GM is a pre-registered WS2/G1 tracer.** The episode universe is WMT/GM by pre-registration, and DP-9 explicitly ruled the universe is *not widened past WMT/GM*. G1 already carries the disposition INSUFFICIENT TEST CONDITIONS on an arrival-rate argument. **Half the universe has now stopped producing data**, and the monitor strip does not know it: the GM card still prints `0 post-deploy episode(s) in 30 session(s)… NO TEST CASES YET`, a live clock that will keep incrementing against a ticker that cannot generate an episode. **This is the fifth-plus instance of the tool-reports-a-value-it-did-not-compute class, and it is attached to a gate carrying a formal disposition.**
2. **E4 practical coverage falls to 14/24 = 58.3%** against the pre-registered 15/24 = 62.5% `[V]`. **This is precisely the number the 8/14 ruling forecast — and it arrives via the wrong name.** The ruling worried about CORN; CORN moved HELD → SCOUT on 8/17 and **is still generating today**, answering that open configuration question in the favourable direction. GM, which the ruling did not consider, is the name that went dark. Both denominators must now be reported at every E4 read, per that ruling, and today is the first session on which they actually differ.
3. **32 GM rows are unresolved and future-due** `[V]`: 4 at +5d (8/12, 8/13, 8/14, 8/17), 9 at +10d, 19 at +20d. None is overdue yet — the first, GM 8/12 at +5d, is due **2026-08-19**. If the resolution fill is driven by the run's ticker list, those 32 fills never arrive, and GM's rows become the largest incompleteness in the record by an order of magnitude (the standing ghost-row item is 2 rows). **This is the one item on this page that is actionable before tomorrow's run.**
4. **`band_price`'s "COVERED 15" is now a historical population, not a live one.** GM's n=59 freezes. The frozen E4-2 tier table still carries GM (MID, would re-tier to LOW), and §3.3's fallback pools ADJACENT against COVERED-QUIET *within tier* — a tier slot that can no longer be filled. The tier table is **NOT re-cut**; this is drift monitoring and a supply note.

Secondary observation `[V]`: the log reads `Prior-signal state loaded: 26 ticker(s)` against `ANALYZING 25 UNIQUE TICKERS`. `signal_state.json` still carries GM. Harmless today — S1 reads priors per ticker — but the 26-vs-25 disagreement is printed in the log and nothing compares the two.

### 2.2 ★ THE VALUATION LAYER HANDLED GM'S DEPARTURE CORRECTLY, AND THE EXHIBITS DID NOT

`value_anchor` derives the watchlist from the master rather than from a hardcoded list, and GM dropped out of the join cleanly and silently — 15 verified tickers, no stale entry, no error. **Recorded because it is the design working**, and because the 8/17 `verified_join` defect was in exactly this function.

The **narrative** did not keep up. Three carried-forward strings in `implied_return` now reference a name absent from their own tables:

- §1a: *"So GM reads 4.88% in this table against a true TTM near 3.33%."* GM is not in this table. The verification is correctly dated 2026-08-17 but the tense is wrong, and the sentence reads as a current row.
- §5: *"the 'expected DOWN' set is `['DOW']` — and GM's own XBRL block shows operating income −31.4% YoY while DOW is loss-making."* The evidence offered for a DOW reading is a GM figure, from a name no longer in the cohort. Note also that the 8/17 expected-dearer set was DOW, GM, MSFT, NKE; MSFT and NKE now read *flat*, so the sentence is stale in two directions.
- FINDINGS 2 rests entirely on GM.

**The substance of that finding is unaffected** — that neither ROE basis is trailing-twelve-month is an argument about period selection, not about GM. But **the only external verification the valuation layer has ever had (Schwab eps 3.27 = GM's FY2025 10-K EPS 3.27, against Morningstar's 3.28%) is no longer reproducible from this session's cohort.** No other name in the covered set has been checked against an outside source. That should be stated in the exhibit rather than left implicit, and it raises the priority of finding a second externally-verifiable name.

---

## 3 · EDGAR — the budget warning reports a consequence that did not happen

### 3.1 ★★ DP-3C-j IS NOT IMPLEMENTED, AND THE LOG CARRIES THE EVIDENCE BOTH WAYS `[V]`

```
10:07:08.418 | INFO    | [EDGAR] prefetch: 20/25 ticker(s) resolved to submissions
10:09:19.418 | WARNING | [EDGAR] run budget of 120s exhausted — remaining tickers
                         degrade to no-EDGAR for this run.
```

The warning fired while processing **NTR, the 11th ticker**. Fifteen tickers remained. **Fourteen of them rendered full `E[…]` sections with a live `fin=N@date`** — PM, PWR, RTX, SND, USO, WMT, NVDA, GLD, SPCX all carry complete statements blocks from warm cache; SCHD, SPY, QQQ, VTI, XLU are structurally dark. **Exactly one ticker degraded: CORN, tagged `fin=degraded`.**

Two distinct defects:

**(a) The run-level warning asserts a run-wide consequence contradicted by the per-ticker tags in the same file.** DP-3C-j ruled that degradation becomes visible *per ticker* rather than once at run level, *"because a tag that omits `fin=` for two different reasons is a tool reporting a value it did not compute."* The per-ticker half was implemented and works — `fin=degraded` is distinct from `fin=none` and fired correctly on the one affected name. **The run-level warning text was never retired to match**, and a reader taking it at face value would conclude fourteen names lost treatment on an E4 cohort. That is a worse error than the one DP-3C-j fixed, because it points the wrong way about a measurement cohort.

**(b) The budget is still bounding wall clock.** 10:07:08 → 10:09:19 is **131.0s**, and that window contains ten Claude signal calls (~10–16s each), ten news fetches and ten quote/price-history round trips. EDGAR fetch/extract against a warm cache is a small fraction of it — the 8/03 measurement put it near 6%. DP-3C-j ruled that *"the EDGAR budget bounds time spent INSIDE `edgar_client` fetch/extract, not run wall clock."* **The observed behaviour is the pre-ruling behaviour.** Raising `EDGAR_MAX_SECONDS` would buy more Claude API time, which is the same diagnosis reached on 2026-08-03.

**Consequence for E4:** today's cohort lost the statements block on **one** name (CORN), not fifteen. CORN is in the frozen E4 population. That is a one-row treatment gap, not a cohort-level one — but it is only knowable by reading the tags, because the warning says otherwise.

### 3.2 ★★ `form4=Nf` IS AMBIGUOUS BETWEEN A DATA STATE AND A RESOURCE LIMIT — DP-3C-j's DEFECT ON A FIELD DP-3C-j DID NOT COVER `[V]`

```
10:09:01.629 | INFO | [EDGAR] 11 Form 4s in window exceeds the 10-document budget
                      — reporting count only.
```

NKE tags `form4=11f@2026-08-17` — count only, no net direction, because the document budget was hit. But FTI tags `form4=4f@2026-08-04` and SND tags `form4=3f@2026-08-17`, **both well under the budget and both with no budget message**, so `Nf` there means something else entirely — no open-market transaction from which a direction is computable (codes A/M/F only). Meanwhile AAPL, JPM, MSFT, RTX and WMT all render the directional form `+X/−Y@date`.

**One grammar, two causes, and the tag cannot distinguish them.** DP-3C-j's rationale applies verbatim and was simply scoped to `fin=`. The fix is the same shape: a distinct token for the budget case (`form4=11f+@date` or `form4=budget@date`), so that "no direction exists" and "direction not computed" are not the same string.

**This matters to E4-2, not merely to bookkeeping.** DP-3C-i put filing dates in the tag precisely so ADJACENT-vs-COVERED-QUIET membership is reconstructible from the durable record, and it forced the disambiguation that `form4=` must carry the most recent Form 4 of *any* transaction code. Both grammars do carry a date, so **ADJACENT membership is safe today**. The exposure is to any future read that uses net direction, which would silently treat "budget-truncated" as "no directional activity."

### 3.3 Coverage and prefetch

`[EDGAR] prefetch: 20/25 ticker(s) resolved to submissions` against **16/25 sections actually rendered** (9 dark: AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU). The submissions-resolved-versus-sections-rendered gap is the known `--coverage` discrepancy and is still undocumented in Workflow §4, which states 15/24 and has now been wrong against three successive true values (19/24, 19/25, 20/25).

---

## 4 · The risk engine approved a directional signal for the first time in the project's history

### 4.1 ★★ NVDA BUY 72% — `Risk: APPROVED`, `PENDING HUMAN APPROVAL`, AND IT IS RULED AND DATED

```
[PHASE 3-C DRY RUN] [—] [SCOUT] NVDA | Signal: BUY | Confidence: 72% | Risk: APPROVED
Reason: PENDING HUMAN APPROVAL — Signal passed all automated checks.
PER-ACCOUNT: Roth IRA=APPROVED; Individual=APPROVED.
```

The record's last statement on this, dated 2026-08-04, was that **the risk engine had never approved a directional signal — 35 directional signals across 54 cohorts, zero approvals.** It has now approved one. **There is no provenance gap**: the `Actionable BUYs` tab records `DP-3C-o (iii)` demoting CHECK 6 to a non-blocking flag effective **2026-08-11**, cites `risk_engine.py` L201–207, and enforces a mandatory pre/post era split with an explicit *do not pool* warning. That is the DP-8/DP-9 provenance failure not being repeated.

Two of the 8/04 defects are visibly fixed: **D-1** (single-account scope) — the engine now evaluates and reports per account, both accounts; and **D-3**'s premise is moot for BUYs now that CHECK 6 no longer blocks. **T1 holds**: the signal is advisory, pending human approval, and no order exists.

**DP-3C-l's foresight is vindicated exactly as written.** It made ledger membership independent of the `Decision` field *"so that a future change to `MAX_OPEN_POSITIONS`… cannot silently redefine the population."* CHECK 6 changed on 8/11 and the population did not move by a single row.

### 4.2 ★★ DP-3C-l's SUPPLY ARITHMETIC IS FALSIFIED, AND THE ENDPOINT'S CONSTRAINT HAS CHANGED CHARACTER RATHER THAN GONE AWAY

DP-3C-l pre-committed **INSUFFICIENT TEST CONDITIONS** on measured supply of *2 events in 54 cohorts = 0.037/session*, giving ~540 sessions (~2 years) for n = 20, and stress-tested at triple the rate to ~180 sessions.

Observed since `[V]`:

| window | gate-cleared rows | sessions | rate |
|---|---|---|---|
| through 2026-08-04 | 2 | 54 | 0.037/session |
| 2026-08-04 → 2026-08-18 | 9 | 11 | **0.82/session** |

At the observed rate, n = 20 arrives in roughly **14 further sessions**, not 540. **The pre-committed disposition rests on a stated reason that is now wrong by a factor of ~22.**

**And it is not therefore readable.** The ledger stands at 10 rows: 1 CBRS SELL and **9 NVDA BUYs**. Coalesced per DP-3C-m it is **3 episodes**: CBRS 6/26 (NO), NVDA 8/04–8/10 (YES), NVDA 8/13–8/18 (pending).

| basis | resolved | hit | rate |
|---|---|---|---|
| ROW | 6 | 5 | 83.3% |
| EPISODE | 2 | 1 | 50.0% |

**Every one of the five resolved YES rows is PRE-DP-3C-o. Zero post-era rows have resolved.** The tab's own instruction — *"DO NOT POOL ACROSS THE ERA LINE"* — means the 83.3% is a pre-era figure and cannot be quoted as current.

**The endpoint has moved from supply-starved to concentration-starved**, which is DP-10's problem (a cap was ruled to apply and no number was ever set) and needs a different remedy from the one DP-3C-l pre-committed. **The disposition may still be right; its stated reason is not. That needs a dated amendment rather than a silent re-reading**, and the amendment must carry the coalescing rule at the point of pre-registration, which is what DP-3C-l itself demanded and which the tab has already implemented.

**Direction, stated because it runs toward the phase looking better:** a falsified starvation argument on a ledger reading 5/6 is exactly the kind of finding to distrust. The tab is already refusing to read a disposition at any n — *"No disposition is read from this registry at any n until DP-3C-l is amended by a dated ruling"* — which is the correct posture and is being followed here.

### 4.3 ★ NVDA `op 72` vs `blend_op 71` — the reconciliation FAIL is benign today and the check's wording is still unrepaired

`signal_scan` reports `[FAIL] D.op == B.blend_op  24/25 — NVDA op 72 vs blend_op 71`. NVDA is the only blend-adjusted row today (`base=72; blend=71; blend_op=71`); all 24 HOLDs satisfy `blend == base`. **Both channels clear the 70% gate, so nothing turns on it.** On 2026-08-03 the same check fired the other way (op 68 vs blend_op 70) and was load-bearing on the gate. WS1 is **DESCOPED**; the blend is a shadow channel and the base signal is the official output. The 8/03 instruction to rephrase this assertion as informational rather than a FAIL is still open, and it is now producing a red line on a descoped channel every time a directional signal appears.

---

## 5 · Instrument and integrity items

### 5.1 ★ `signal_scan`'s count check is hardcoded and has now failed against three different true values

`[FAIL] signal count 25 (expected 24)`. The watchlist has read 24, 25, 26 and 25 across the last six sessions. **The check cannot pass while the watchlist moves, so it is noise on every run — which is how a real finding gets ignored.** One change fixes both this and §2.1: assert against **the prior session's membership** rather than a constant, and print the set difference. That is the one-line set-difference the 8/14 ruling asked for, and it would have made GM's departure the headline of the run's own integrity block rather than a line I had to compute by hand.

### 5.2 ★ Verified fixed, recorded because the record carried it as open for five sessions

The monitor strip's WMT clock now reads `last episode 2026-07-23, 18 session(s) ago`, consistent with the coalesced ledger. **The "last episode 2026-07-24" defect — raised 7/30, still open on 8/04 — is CLOSED** `[V]`. The H4 card also now prints the correct `n ≥ 12 … on 2 consecutive readings` bar rather than the superseded `n ≥ 10`.

### 5.3 ★ `Sheet1` is still in the master, thirteen sessions after the delete instruction

`logs\claude_equity_bot_tracker.xlsx` still carries `Sheet1`, row 1 *"Guardrail Compression Trace — cumulative +5d hit rate by confidence band"*, row 2 *"as of 2026-07-20. The 50-59% band must lead 60-69%"*, 43 cohort rows frozen at 2026-07-20 `[V]`. The purge drops it from the generated copy every run and the notice now stamps **"Retired 2026-08-18"** — the standing evidence, per Workflow §7, that the tab is still at source. A retired criterion stated in live-criterion grammar sits in the workbook every harness reads. **Delete it once in the master; the notice going quiet is the confirmation.**

### 5.4 Operational

- **Run started 10:06:19 CST**, first signal 10:07:24, last 10:12:37 — roughly 37 minutes past the canonical 9:30, following a proactive Schwab token re-authorisation at 10:06:21–10:06:46. Px@signal for all 25 rows is therefore a mid-morning quote. **Immaterial to +Nd returns (closing prices) and to any within-cohort comparison; recorded.** Second occurrence after 2026-08-04 — but unlike 8/04, **the EDGAR flag was set**, the era stamp is correct and the cohort is a treatment cohort.
- **CORN answered the open configuration question in the favourable direction.** The 8/14 ruling flagged *"whether CORN moves HELD → SCOUT and keeps generating"* as needing an answer before Monday's run. It moved to Scout on 8/17 and generated today. CORN stays in the E4 denominator and contributes rows. It is also the one name that degraded (§3.1).
- **Phase token corrected.** The log reads `[PHASE 3-C DRY RUN]`; change-order item (5) has landed.
- **`value_anchor` / `implied_return` / `band_price` figures independently verified** `[V]`: 1,411 resolved +5d rows; pooled breach ALL 45.50%, COVERED-15 49.43%, not-covered 38.90%; HOLD-only 619/1,363 = 45.41%; `Was Claude Right? (5d)` reproduces the price-derived sign/band test on **1,409 of 1,409** non-blank rows with 0 mismatches (the 2 blanks are the standing 2026-06-01 ghost rows). Today's cohort profile — mean 56.8, median 60.0, sd(pop) 10.19, min 35, max 72, DQ 17 HIGH / 8 MEDIUM — reproduces `signal_scan` exactly.

---

## 6 · Findings, ranked

| # | finding | class | action |
|---|---|---|---|
| 1 | **GM left the watchlist; 32 unresolved GM rows are future-due, the first on 8/19** | data loss, imminent | **Before tomorrow's run:** decide whether GM prices are still fetched for resolution fill, or annotate the rows as terminated |
| 2 | **GM's departure is unseen by every monitor**; G1's secondary tracer is dead and its clock still ticks | detection gap ruled 8/14, unfixed | Add the session-over-session set difference; fold it into `signal_scan` (§5.1) |
| 3 | **E4 practical coverage 15/24 → 14/24 = 58.3%** | measurement | Report both denominators at every E4 read, per the 8/14 ruling — first session on which they differ |
| 4 | **DP-3C-j unimplemented**: budget still wall-clock; run-level warning contradicts per-ticker tags | tool-reports-a-value-it-did-not-compute | Retire the run-level warning text; move the timer inside `edgar_client` |
| 5 | **`form4=Nf` conflates budget truncation with no-direction-computable** | same class, uncovered field | Distinct token for the budget case |
| 6 | **DP-3C-l's supply arithmetic falsified** (0.037 → 0.82/session); constraint is now concentration, not supply | pre-registration | Dated amendment; DP-10 needs a number |
| 7 | **Branch-tree schedule error** put two rows of one cohort on two days; the 8/14 ruling's "exactly one reading" claim is false | pre-registration | Record; no re-ruling needed |
| 8 | **Row-vs-episode basis gives opposite KEEP-70 dispositions** (47.50% vs 55.6%) | open item, now decision-relevant | Rule the basis |
| 9 | **`signal_scan` count check hardcoded at 24**, failing on every session | noise that hides signal | Fold into #2 |
| 10 | **`implied_return` narrative cites GM in three places**; the layer's only external verification is no longer reproducible | exhibit staleness | Re-tense as 8/17 historical; find a second verifiable name |
| 11 | **`Sheet1` still in the master**, 13 sessions on | integrity, G4 | Delete once |
| 12 | **NVDA `op` ≠ `blend_op` FAIL on a descoped channel** | wording, open since 8/03 | Rephrase as informational |

---

## 7 · Standing

T1 (advisory-only, pre-execution, mandatory) · T3. **KEEP 70% — SUPPORTED at 47.50% on the row basis, NOT SUPPORTED at 55.6% on the episode basis; the basis is UNRULED.** H4 **STAYS DEMOTED** (55.0%, first passing reading reversed at the second). ±3% HOLD band unchanged and **NOT re-baselined**. Frozen E4-2 tier table **NOT re-cut**. Blend (WS1) **DESCOPED**. Q4-2 parked. Peer-relative M/B–ROE form DESCOPED; P/E form PARKED. Nothing in the valuation layer touches the prompt. G1 **INSUFFICIENT TEST CONDITIONS**, and its secondary tracer has now stopped producing data. E4 clock: cohort 4 of ~10.

*Advisory-only · no orders · not financial advice.*
