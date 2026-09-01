# Closing Review — 2026-08-27, and the return from the gap

*Claude Equity Bot · Phase 3-C · **E4 cohort 10** · era `A-S1D1-B1-E1` (D2 applied 2026-08-31, first D2 cohort will be 2026-09-01) · advisory-only · no orders · not financial advice.*

**The vacation gap held exactly as pre-registered** `[V]`. 1,718 rows, 71 cohorts, 2026-05-18 → 2026-08-27. `trading_calendar` reconciles against the master with **zero unexplained missing sessions and zero cohort rows on non-sessions**. The 08-28 and 08-31 backfill is **151 of 151 cells complete**, and against a frontier of 2026-08-31 there are **zero overdue and zero premature**. Cached returns reproduce price-derived across **4,418 comparisons to 1.110e-16**; the ±3% band reproduces on **1,576 of 1,576** HOLD rows. The outcome gate reads **CLEAN**.

**`scan.bat` and `value.bat` were not run for 2026-08-27** — no `signal_scan_2026-08-27.md`, no dated value-layer exhibits. **I ran the log↔master cross-check myself: 26/26 CLEAN** on signal, confidence, DQ and Price at Signal, with the era stamp `A-S1D1-B1-E1` and model `claude-sonnet-4-6` uniform across all 26 rows. So cohort 10 is verified — but by me, after the fact, rather than by the gate at the time.

**Two things moved in opposite directions, and the combination is the session.** The rejected near-miss BUYs are now winning more often than not, while every approved directional since the DP-3C-o line has lost. §2 is the sharpest form of that and it is the most important item in this review.

---

## 1 · The ledger

### 1.1 ★★ TWO GATE-CLEARING DIRECTIONALS IN ONE SESSION — A FIRST — AND ONE OF THEM WAS REJECTED ON A RULE THE LEDGER DOES NOT MODEL

`[V]` 2026-08-27 produced **three BUYs**, two clearing the 70% gate:

| ticker | conf | DQ | risk decision | reason |
|---|---|---|---|---|
| **NVDA** | **75** | HIGH | **APPROVED** | `PENDING HUMAN APPROVAL — passed all automated checks` |
| **MSFT** | **72** | HIGH | **REJECTED** | `Already holding MSFT and ALLOW_POSITION_ADD is False` |
| PWR | 62 | HIGH | REJECTED | confidence below 70 — a near-miss, joins KEEP-70 |

**NVDA at 75 is the highest-confidence directional in the record** (prior max 74) and only the third row ever to reach `PENDING HUMAN APPROVAL`. The ledger goes **13 → 15 rows** and **5 → 7 episodes**.

**★ MSFT is a definitional problem and it has a deadline.** The Actionable ledger is built on the confidence gate — `build_actionable_registry` records `CHECK 5 Gate 0.70, Margin 2 pts` — so MSFT is in it. But the risk engine **rejected** it, on a position rule that has nothing to do with signal quality. It was never executable.

That distinction has never mattered before, because every prior ledger row was either approved or rejected *on confidence*. **MSFT resolves at +5d on 2026-09-03**, and when it does it will be scored into an arm whose meaning depends on which question the arm asks:

- *"what happens after confidence clears 70?"* → MSFT belongs in.
- *"what happens after the risk engine approves?"* → MSFT must be excluded, and so must any future row rejected on a position rule.

**Rule this before 2026-09-03.** Deciding after the outcome is visible is the thing this project's whole discipline exists to prevent. My reading is that the ledger measures the **confidence gate** — that is what the tab's own `CHECK 5 Gate` column says — and that MSFT therefore counts, with a marker recording that it was not executable. But it is a ruling, not a reading.

`[V]` The blend would have knocked MSFT to 69, below the gate; NVDA to 71, still clearing. WS1 remains **DESCOPED**.

### 1.2 ★★ THE POST-ERA ARM IS 0/6, AND ALL THREE PENDING ROWS RESOLVED AGAINST IT

`[V]` NTR 2026-08-21 **−1.33% NO** and GLD 2026-08-24 **−4.82% NO** resolved during the gap. GLD 2026-08-25 resolves today.

| era | rows | resolved +5d | hit | mean +5d |
|---|---|---|---|---|
| PRE-DP-3C-o | 6 | 6 | **5 = 83.3%** | **+4.37%** |
| POST-DP-3C-o | 9 | **6** | **0 = 0.0%** | **−4.24%** |

`[V]` Reproduced independently and confirmed against the `Actionable BUYs` tab, which prints the identical split — the cross-check that was unavailable on 2026-08-26 because the registry workbook was not supplied.

**Six consecutive negative resolutions, now across three different names** (NVDA ×4, NTR, GLD). The 8/26 review noted the arm was "four NVDA rows from two coalesced episodes"; that is no longer the caveat it was. **Do not pool** — 5/12 is not a figure. Episode basis **0/3**.

---

## 2 · ★★★ THE CONFIDENCE ORDERING IS INVERTED IN THE POST-ERA WINDOW

This is the finding. It is what you noticed, stated as sharply as the data supports — and then bounded.

`[V]` Every BUY row since the DP-3C-o line, split by confidence band, never pooled across the line:

| era | band | n | resolved | up | rate | mean +5d |
|---|---|---|---|---|---|---|
| PRE | 60-69 | 38 | 38 | 19 | 50.0% | −1.35% |
| PRE | **≥70** | 5 | 5 | 5 | **100.0%** | **+2.32%** |
| POST | 60-69 | 15 | 12 | 7 | **58.3%** | **+0.88%** |
| POST | **≥70** | 9 | 6 | 0 | **0.0%** | **−4.24%** |

**Pre-era the ordering was correct: higher confidence, better outcomes. Post-era it is reversed.**

`[V]` Sorted by confidence, every resolved post-era BUY:

```
conf 74  NVDA  -8.21%      conf 68  NVDA  -3.92%
conf 72  NVDA  -4.74%      conf 68  NVDA  +4.49%
conf 72  NVDA  -2.78%      conf 67  GLD   -2.91%
conf 72  NTR   -1.33%      conf 66  GLD   +2.36%
conf 72  GLD   -4.82%      conf 66  NVDA  +1.27%
conf 70  NVDA  -3.57%      conf 65  GLD   +3.68%
conf 68  NVDA  -0.00%      conf 65  GLD   +2.50%
conf 68  GLD   -1.17%      conf 64  NVDA  +5.13%
conf 68  NVDA  -2.95%
conf 68  GLD   +2.04%
```

**The six highest-confidence rows are all negative. The five lowest are all positive.** Spearman ρ(confidence, +5d) = **−0.775** across all 18 rows — and it is not a composition artifact of mixing two names, because it reproduces *within* each: **NVDA ρ = −0.784 (n = 10), GLD ρ = −0.873 (n = 7)**.

### And now the bound, which is severe

**Eighteen rows are not eighteen observations.**

1. `[V]` **Two names supply 17 of the 18** — NVDA 10, GLD 7, NTR 1.
2. `[V]` **They coalesce to FOUR episodes** under DP-3C-m: NVDA opening 08-11 (len 10), GLD opening 08-11 (len 3), GLD opening 08-19 (len 4), NTR 08-21 (len 1).
3. Consecutive-session rows share **four of five days** in their outcome window. These are overlapping samples of two price paths, not independent draws.

**So the honest statement is: a strong, within-name-replicated inversion at row level that reduces to two names and four episodes.** That is enough to take seriously and nowhere near enough to rule on. The within-name replication is what stops it being dismissible — an inversion that appears independently in NVDA and in GLD is not a mix effect — but two names is two names.

**Nothing is ruled here.** The 70% gate is not moved, KEEP-70's bar is not moved, and no arm is re-read. What is owed is a decision about **what would settle it**, taken now while the answer is not yet visible: how many independent episodes, over what window, before this is read as a property of the generator rather than of NVDA and GLD in late August.

---

## 3 · ★★ KEEP-70 BREACHES ITS BAR FOR THE FIRST TIME — AND BOTH BASES AGREE

`[V]` Registry **53 rows** (PWR 08-27 added), **50 resolved at +5d**.

| basis | 8/25 | 8/26 | **8/31** | ruled bar | verdict |
|---|---|---|---|---|---|
| **ROW** | 21/43 = 48.84% | 22/45 = 48.89% | **26/50 = 52.00%** | ≤ 50.0% supports | **NOT SUPPORTED** |
| **EPISODE** | 10/18 = 55.6% | 11/20 = 55.0% | **11/20 = 55.00%** | | **NOT SUPPORTED** |

**For every prior session the two bases straddled the bar and the unruled basis question decided the verdict. It no longer does — both now say NOT SUPPORTED.** `monitor_strip` reads it as `review`.

`[V]` Five of the last six +5d resolutions went to the rejected side: 08-20 NVDA **+4.49%**, 08-20 GLD **+2.50%**, 08-21 NVDA **+1.27%**, 08-24 NVDA **+5.13%** right, against 08-21 GLD −2.91% wrong.

**Two cautions that are not softening, but are load-bearing:**

- `[V]` **The bar's wording differs between sources.** The closing reviews use **≤ 50.0%**; `monitor_strip` prints **< 50%**. At 52.00% both give the same verdict, so nothing turns on it today — but the two texts differ at exactly 50.0%, and on 2026-08-26 the row basis was one resolution from landing there. **Reconcile the wording while it costs nothing.**
- **This is the same population as §2 and inherits the same bound.** The near-miss registry is also dominated by NVDA and GLD. KEEP-70 crossing its bar and the §2 inversion are not two pieces of evidence; they are one, read two ways.

`[V]` +10d reads **16/43 = 37.21%**.

---

## 4 · ★★ H4 PASSES A READING — ONE — AT EXACTLY THE BAR

`[V]` HIGH-DQ near-miss +5d, recomputed reading by reading from the master:

| as of | reading | verdict |
|---|---|---|
| 2026-08-17 | 11/18 = 61.1% | **PASS** |
| 2026-08-18 | 11/20 = 55.0% | FAIL |
| 2026-08-19 | 12/22 = 54.5% | FAIL |
| 2026-08-20 | 13/23 = 56.5% | FAIL |
| 2026-08-26 | 14/25 = 56.0% | FAIL |
| 2026-08-27 | 16/27 = 59.3% | FAIL |
| 2026-08-28 | 17/29 = 58.6% | FAIL |
| **2026-08-31** | **18/30 = 60.0%** | **PASS** |

The bar is `n ≥ 12 resolved AND hit ≥ 60%, on TWO CONSECUTIVE readings`. n = 30 satisfies; 60.0% clears the rate **by exactly zero margin**. `monitor_strip` states it as `passes this reading`.

**H4 STAYS DEMOTED.** This is one passing reading and the previous one failed at 58.6%. `[V]` The next reading decides: **one further YES gives 19/31 = 61.3% and H4 promotes; one NO gives 18/31 = 58.1% and the count restarts.** That is the tightest H4 has ever been, and it is worth writing the branch down in advance — this record has done that before (2026-08-13) and the discipline paid.

`[V]` MEDIUM unchanged at **8/20 = 40.0%**. LOW 0/0.

---

## 5 · The rest of the endpoints

### 5.1 ★ COHORT ACCURACY RECOVERED SHARPLY, INCLUDING +20d

`[V]` The nine cohorts that resolved on 08-27, 08-28 and 08-31:

| horizon | 08-27 | 08-28 | 08-31 |
|---|---|---|---|
| +5d | 17/26 = **65.4%** | 14/26 = 53.8% | 17/26 = **65.4%** |
| +10d | 16/25 = **64.0%** | 12/25 = 48.0% | 14/26 = 53.8% |
| +20d | 6/24 = 25.0% | 5/24 = 20.8% | 8/24 = **33.3%** |

`[V]` Series positions: **+5d 65.4%, rank 49 of 68** (mean 54.5%); **+10d 53.8%, rank 52 of 63** (mean 43.5%); **+20d 33.3%, rank 22 of 53** (mean 33.6%, median 33.3% — dead centre).

**+20d has climbed out of the record lows.** It printed 12.5% and 16.7% on consecutive cohorts around 08-25/08-26 — the two lowest of the series — and now reads exactly at its own median. **That is the strongest argument yet that those readings were the band mis-scaling and the drift regime, not a signal collapse**, and it retires the alarm those two entries raised. The +5d ±3% band is **NOT re-baselined**; the +10d/+20d rescale remains a reporting-convention item.

`[V]` +20d cohorts still breach overwhelmingly upward (13U/5D, 14U/5D, 10U/6D) on means of +5.83%, +4.91%, +3.70% — the dispersion argument, unchanged.

### 5.2 ★★ TIER DRIFT BREAKS OUT: 8 → 10 OF 15

`[V]` Recomputed from the Price columns at n = 67–68 per name:

| | |
|---|---|
| would re-tier | **10 of 15** — GM, PM, WMT, CORN, AAPL, NKE, MSFT, NVDA, PWR, FTI |
| new since 08-26 | **PM** (MID → LOW, drift −0.572pp) and **CORN** (LOW → MID, +0.743pp) |
| held | JPM, RTX, GLD, DOW, SND |

**Two thirds of the covered set would now re-tier.** `[V]` The flagged boundary held again — NVDA 3.537% vs DOW 3.861%, gap **+0.324pp**, widened from 0.331pp on 08-26 and never flipped. The freeze doc's sensitivity note remains aimed at the wrong boundary.

**The table is NOT re-cut.** §3.3's fallback pools ADJACENT against COVERED-QUIET **within tier**, so ten mis-tiered names is the confound the table exists to remove, now applying to a two-thirds majority.

`[V]` Pooled covered-15 breach **506/1018 = 49.71%** against a row-weighted model expectation of **48.39%** — gap **+1.32pt, z = +0.842, p = 0.400**. Still **not distinguishable** from a zero-skill dispersion baseline, and more firmly so once the ~1.66× overlap inflation is applied.

### 5.3 ★ `regime_score` RETURNED TO ITS CLAMP

`[V]` The 08-27 log reads **`reg = -1.0`, uniform**, after −0.984 (08-25) and −0.913 (08-26). The 08-26 review recorded the channel as "live from today"; it moved twice and went back to the bound.

**Both statements are true and the second does not retract the first.** A channel that sits at −1.0 is not thereby proved inert — it has been demonstrated to move. `signal_scan`'s uniformity check passed at every one of the three values and **would not have flagged any of the transitions.** The proposed value-check assertion is now carrying its third unflagged move. **Implement it.**

### 5.4 ★ CHECK F — UNCHANGED, AND NOTHING WAS REPAIRED

`[V]` All six candidates I named before the gap still hold their original master values: GM 08-20 **85.75**, PWR 08-14 **684.78**, GLD 07-02 **379.13**, GLD 06-25 **368.46**, NKE 08-04 **42.53**, VTI 07-07 **363.61**. **The runbook's "do not fix these" was followed.** They remain a triage queue, with the GLD 07-02 reversal still the first one to look at.

---

## 6 · Process — including one item that is mine

### 6.1 ★★ AN EMPTY `signals_2026-08-31.log` NOW SITS IN THE RECORD, AND I PUT IT THERE

`[V]` `logs\signals_2026-08-31.log` exists at **0 bytes**, written ~77 seconds after `main.py` was patched.

**That is the runbook's step 6d.** I wrote `python -c "import main; print(main.PROMPT_VARIANT)"` as a "sanity check that costs nothing." Importing `main` executes module-level logging setup, which creates a log file named for today's date. It cost something.

**Why it matters more than its size.** 2026-08-31 is a **pre-registered BOT_ABSENT session**. There is now a log file for a session the record says had no run. Concretely:

- `scan.bat 2026-08-31` will find the file, skip the "pre-registered no-run session" branch I added for exactly this case, and try to scan an empty log;
- a later reader has a zero-byte artefact suggesting a run that did not happen.

**Nothing downstream is corrupted** `[V]` — `trail_basis_audit` and Check F both skip a log that parses to zero records, and the audit's 11-log table shows 08-13 through 08-27 with no 08-31 row. **Remedy: delete the file** (or move it to `logs\Retired\`), and replace step 6d with a check that does not import the module:

```
findstr /C:"PROMPT_VARIANT = " main.py
```

**The general lesson, which is the part worth keeping:** a "read-only" check that imports application code is not read-only. `phase_dispatch_audit.py` exists in this repo because of the same class of mistake.

### 6.2 ★ THE RULING WAS APPLIED — ON 08-31, AFTER `run_daily_review`, NOT ON 08-27 BEFORE IT

`[V]` Backups `main.py.bak-20260831_172015`, `schwab_client.py.bak-20260831_172015` and `signal_scan.py.bak-20260831_172015` — all three files, one timestamp. **All five edits landed.**

The runbook put the ruling *after* `run_daily_review` and *on 08-27*. It ran on 08-31, after the review pass. **No harm, and the reason is worth stating rather than assuming:** `run_daily_review.bat` reads the master and the logs and never calls `schwab_client` for signal generation, so the exhibits it produced are identical either way. And the goal that mattered — **cohort 10 recorded under D1** — held, because the 08-27 bot run preceded the patch by four days. `[V]` The 08-27 log carries `A-S1D1-B1-E1` on all 26 rows.

**The D1→D2 boundary still lands exactly on the gap.** Last D1 cohort 2026-08-27; first D2 cohort 2026-09-01.

`[V]` `trail_basis_audit` correctly still reports the defect across all eleven logs, 08-27 included — those were written under D1. It should flip to `COMPLETED_ONLY` after today's run. **That is the first real test that the fix works**, and it has not happened yet.

### 6.3 ★ `Sheet1` IS BACK IN THE MASTER

`[V]` Both workbooks carry `Sheet1` — 25 rows of ticker/price pairs, the outcome-entry paste buffer. The item was closed on 2026-08-24 (*"`Sheet1` stays gone"*) and has regressed.

Benign in content, and it is genuinely useful as a scratchpad. But it is in **the master**, which is the file every gate reads and which `outcome_sanity` and `log_tracker_crosscheck` both hard-refuse a copy of. **Move the paste buffer to a separate workbook.** A scratch sheet inside the file that is the source of truth is how a scratch value becomes a recorded one.

### 6.4 ★ WHAT WAS NOT RUN

`[V]` No `signal_scan_2026-08-27.md`, no `value_anchor_2026-08-27.md`, no `implied_return_2026-08-27.md`, no `band_price_2026-08-27.md`. **`scan.bat` and `value.bat` were skipped for cohort 10.**

`run_daily_review.bat` **was** run (all its outputs are dated today), which is why the registries, the H1 tracers and the monitor strip are current.

**Consequences, in order of size:**

1. **The integrity gate did not run at the time.** I have since reproduced it — **26/26 CLEAN** — so cohort 10 is verified, but by reconstruction rather than by the gate. Under E4's tier (c) that is a *read-blocking* condition resolved by re-running the tool clean against that cohort's own log and master, which is exactly what has now happened. **Cohort 10 stands.**
2. **There is no dated valuation-layer exhibit for 08-27.** CORN's join failure and DOW's `+coreg` state are unobserved for that session. Neither is decision-relevant.
3. **Check F and the H1 audit did not run against 08-27 at the time** — both have now, clean and as expected respectively.

**Run `scan.bat 2026-08-27` and `value.bat 2026-08-27` retrospectively** if you want the dated artefacts on disk. Both are read-only and both accept an explicit date.

### 6.5 One correction to my own analysis

My first completeness pass reported **151 premature cells**. That was my error, not the master's: I tested "due" against the last *cohort* date (2026-08-27) when the correct frontier is the last *resolution session with data* (2026-08-31). The 151 were exactly the gap backfill, correctly entered. Re-tested against the right frontier: **zero overdue, zero premature.** Recorded because it is the same confusion the calendar work exists to prevent — the last day somebody ran the bot is not the last day the market traded — and I made it in the tool I wrote to avoid it.

---

## 7 · Findings, ranked

| # | finding | class | action |
|---|---|---|---|
| 1 | **Confidence ordering is INVERTED post-era.** ρ = −0.775 over 18 rows; six highest-confidence BUYs all negative, five lowest all positive; replicates within NVDA (−0.784) and GLD (−0.873) separately | **endpoint-relevant, strongest signal in the record** | **Rule what would settle it — episode count and window — NOW, before the answer is visible.** 18 rows = 2 names = **4 episodes**. Nothing ruled today |
| 2 | **KEEP-70 breaches its bar for the first time: ROW 26/50 = 52.00%, EPISODE 11/20 = 55.00%** — and both bases agree for the first time | ruled criterion, state change | **NOT SUPPORTED on both bases.** Same population as #1 — one piece of evidence, not two |
| 3 | **Post-era arm 0/6**, now spanning three names; PRE 5/6 = 83.3% at +4.37% vs POST 0/6 at −4.24% | endpoint | **Do not pool.** Episode basis 0/3 |
| 4 | **MSFT 08-27 clears the confidence gate but was REJECTED on `ALLOW_POSITION_ADD`** — the ledger does not model that distinction | **definitional, with a deadline** | **Rule before 2026-09-03**, when it resolves. My reading: the ledger measures the confidence gate, so it counts, flagged as non-executable |
| 5 | **H4 passes one reading at exactly 60.0% (18/30)** after four independent failures | endpoint, one reading from promotion | STAYS DEMOTED. **Pre-compute the branch:** next YES → 19/31 = 61.3% promotes; next NO → 18/31 = 58.1% restarts |
| 6 | **Two gate-clearing directionals in one session — a first — and NVDA 75 is the highest confidence in the record** | endpoint | Ledger 15 rows / 7 episodes. NVDA is `PENDING HUMAN APPROVAL` |
| 7 | **The gap held exactly**: 151/151 backfilled, zero overdue, zero premature, calendar reconciles clean | control working | None. The calendar hardening did its job |
| 8 | **+20d recovered to its own median** (33.3%, rank 22 of 53) after two record lows | retires an alarm | Confirms those lows were band mis-scaling and drift, not signal collapse |
| 9 | **Tier drift 8 → 10 of 15**; PM and CORN added; flagged boundary held again at +0.324pp | control degrading | Table **NOT re-cut**. Report the fallback consequence at every read |
| 10 | **An empty `signals_2026-08-31.log` exists because of my runbook step 6d** — importing `main` creates a log | **process, mine** | Delete it. Replace the check with `findstr`. A read-only check that imports application code is not read-only |
| 11 | **`scan.bat` and `value.bat` were skipped for cohort 10** | process, resolved | Cross-check reproduced **26/26 CLEAN** — cohort 10 stands under E4 tier (c). Re-run both for the dated artefacts |
| 12 | **The ruling landed on 08-31 after `run_daily_review`, not on 08-27 before it** | process, no harm | The review pass reads master and logs only. **Cohort 10 is D1 as intended**; the D1→D2 boundary still sits on the gap |
| 13 | **`regime_score` returned to −1.0** after two moves; the uniformity check passed at all three values | instrument | Third unflagged move. **Implement the value check** |
| 14 | **`Sheet1` regressed into the master** — the outcome paste buffer | integrity, previously closed | Move the buffer to a separate workbook |
| 15 | **KEEP-70's bar is written `≤ 50.0%` in the reviews and `< 50%` on the Monitor Strip** | ruled-criterion ambiguity | Same verdict today. **Reconcile the wording while it is free** |
| 16 | **Check F unchanged; nothing repaired** — all six candidates hold their original values | queue, as instructed | GLD 2026-07-02 remains the first to adjudicate |
| 17 | **My completeness check misreported 151 premature cells** — wrong frontier (last cohort vs last resolution session) | mine, corrected | Zero overdue, zero premature on the correct test |
| 18 | **`trail_basis_audit` still reports the defect on all 11 logs including 08-27** | expected | Those are D1 logs. **The first real test of the fix is today's run** |

---

## 8 · Standing

T1 (advisory-only, pre-execution, mandatory) · T3. **2026-08-27 is E4 cohort 10**, era `A-S1D1-B1-E1`, verified 26/26 by reconstruction after the gate was skipped — **read-blocking under E4 tier (c), now resolved; the cohort stands.** **The H1 window ruling is APPLIED** (2026-08-31): `schwab_client` dates candles in UTC against an Eastern today, era stamped **`A-S1D2-B1-E1`**, and `signal_scan`'s era registry updated. **The first D2 cohort is 2026-09-01 and has not yet run — `trail_basis_audit` reporting `COMPLETED_ONLY` after it is the first evidence the fix works.** **DO NOT POOL ACROSS THE D1/D2 LINE.** G1's 2-of-4 post-deploy episodes were detected on the old window and **G1's n most likely restarts — decide after one D2 session, not before.** **E4 is NOT contaminated by the window defect**: it was constant across all rows and both arms, so the within-cohort ADJACENT vs COVERED-QUIET contrast is unbiased; this is **not** a tier-(a) SHAKEDOWN condition.

**KEEP 70% — NOT SUPPORTED on BOTH bases for the first time**: ROW 26/50 = 52.00%, EPISODE 11/20 = 55.00%. The basis question no longer decides the verdict. H4 **STAYS DEMOTED** at 18/30 = 60.0% — **a passing reading, the first since 2026-08-17, one further pass from promotion.** **Gate-cleared ledger 15 rows / 7 episodes; post-era arm 0/6** with GLD 08-25 resolving today and MSFT/NVDA 08-27 on 09-03. **The post-era confidence ordering is inverted at ρ = −0.775, replicated within both contributing names, on 4 episodes — recorded, not ruled.** ±3% band at +5d **NOT re-baselined**; +20d back at its series median. Frozen E4-2 tier table **NOT re-cut**; **10 of 15 would re-tier**, the flagged boundary still held. Blend (WS1) **DESCOPED** — 4 resolved gate-flips, net +2, and 3 of 4 favoured the blend; **that is context on a descoped channel and is not an argument to reopen it** (T-G2-a/b/c are the conditions). Q4-2 **parked**. Peer-relative M/B–ROE DESCOPED, P/E PARKED. DP-3C-f **unruled**. CORN unjoinable at the valuation layer, unobserved for 08-27. **Nothing in the valuation layer touches the prompt (DP-V1).** `regime_score` is a live variable currently sitting at its clamp.

*Advisory-only · no orders · not financial advice.*
