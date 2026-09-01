# Closing Review — 2026-08-19

*Claude Equity Bot · Phase 3-C · **NOT an E4 cohort** · era `A-S1D1-B1` (pre-EDGAR) · advisory-only · no orders · not financial advice.*

**Cross-check 26/26 CLEAN** `[V]` — `signals_2026-08-19.log` ↔ `logs\claude_equity_bot_tracker.xlsx`, reproduced independently from the log JSON at full precision (signal, confidence, DQ, Price at Signal); zero rows in the log and absent from the master, zero the other way. Confidence channels present on all rows; `regime_score` uniform at **−0.65**; totals **1,562 rows, 65 cohorts**; resolutions complete at all three horizons with **zero overdue** and no premature values on today's rows. Every figure below is computed from the Price columns and is formula-cache independent.

**AND THE ERA STAMP READS `A-S1D1-B1`, NOT `A-S1D1-B1-E1`.** That single field is the review.

---

## 1 · The EDGAR flag was not set. Today is a control cohort, and the E4 clock did not advance.

### 1.1 ★★ THE 2026-08-04 PRECEDENT REPEATED, ON THE SESSION AFTER THE RECORD SAID IT HAD NOT

`[V]` from the log, three independent confirmations of one cause:

| check | 2026-08-18 | 2026-08-19 |
|---|---|---|
| `"prompt_variant"` in every Signal JSON | `A-S1D1-B1-E1` × 25 | **`A-S1D1-B1` × 26** |
| `E[…]` tags | 25 | **0** |
| `[EDGAR]` log lines | 3 (prefetch, doc budget, run budget) | **0** |

`main.py` L104–106 derives both the flag and the era from one environment variable —
`EDGAR_ENABLED = os.environ.get("EQUITY_EDGAR","0") == "1"`, and `PROMPT_VARIANT` from it — so
**the run is correctly labelled for what it actually was.** The flag-and-era atomicity ruled on
2026-08-02 did exactly its job: a forgotten flag produced a correctly-stamped control cohort
rather than a mislabelled treatment one. **The safety property held. The measurement did not.**

The go-live runbook named this mechanism in advance, §2, verbatim: *"`set` is per-console. **The
2026-08-04 precedent is the one to avoid** — a new console after a token reauth lost the flag and
produced a control cohort."* The 8/18 entry closed its operational block by observing that a
second late start had occurred *"but unlike 8/04 **the EDGAR flag WAS set**, the era stamp is
correct and this is a treatment cohort."* **One session later it was not set.** 8/18 reauthorised
Schwab in a browser at 10:06:21–10:06:46; today's run started cleanly at 09:30:16 on a refreshed
token — so the flag was lost to a fresh console, not to a reauth, which is the same failure with
the trigger the runbook did not enumerate.

### 1.2 ★★ WHAT THIS COSTS, STATED PRECISELY, AND WHAT IT DOES NOT

**The cohort is not defective and is not a SHAKEDOWN.** DP-3C-t's test is *"is the artifact
wrong, or is the reader wrong?"* — and the artifact is right. Every field describes what ran.
This is a **correctly-labelled control cohort**, the same class as 2026-08-04 and 2026-08-05, and
it is exactly what §6 of the runbook says unsetting the flag produces: *"a byte-identical
3-B-behaviour run under the 3-C token."*

Consequences, each scoped:

1. **E4-1/2/3 gain nothing today. The E4 clock stays at cohort 4 of ~10.** Not excluded as
   defective — **absent**, because there is no treatment to measure. That distinction matters for
   the exit narrative: 8/03 was excluded because it was wrong; 8/19 is absent because it did not
   happen.
2. **E4-1's pre-era baseline gains a row, and this is the one real benefit.** E4-1 reads DQ-mix
   shift pre-era versus post-era, and control cohorts *are* its baseline — the same argument
   recorded on 8/04. Today's DQ mix is **16 HIGH / 9 MEDIUM / 1 LOW** against 8/18's treatment mix
   of 17 HIGH / 8 MEDIUM / 0 LOW, and against 8/04's control mix of 19 HIGH / 5 MEDIUM. **The
   no-treatment noise floor measured on 8/04 was ±2 names; today's control-vs-treatment delta is
   also ~2 names.** E4-1 still has no shift larger than its own noise floor, which is the finding
   that endpoint has been carrying since 8/04 and which is now measured on a third cohort.
3. **KEEP-70, H4, the near-miss registry, the gate-cleared ledger, the monitor strip, `band_price`
   and the master all take today's rows normally.** Per the DP-3C-k precedent, an exclusion scoped
   to one endpoint must not silently move another criterion's denominator. Nothing here is scoped
   out.
4. **`value_anchor` produced no exhibit and `implied_return` produced an empty one.** That is a
   *downstream consequence* of the missing `E[…]` tags, and it is covered in §4 — including the
   defect that let the value pass report itself as normal while computing nothing.

### 1.3 ★★ NOTHING IN THE STACK RAISES AN ALARM ON A LOST FLAG, AND ONE INSTRUMENT ALMOST DOES

`signal_scan` printed, in the RUN INTEGRITY block:

```
[OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)
```

**Factually correct, and marked `[OK]`.** The check verifies the stamp is internally consistent
with the run, which it is; it does not and cannot know which arm was intended. An operator
scanning the integrity block for red lines sees two FAILs, both of them known noise (§5.1, §5.2),
and an OK on the one line that mattered. `grep -i edgar` returns nothing from `run_daily.bat`,
`scan.bat` or `run_daily_review.bat`; `value.bat` mentions EDGAR only in a comment.

**So the project's only current alarm for a lost EDGAR flag is the absence of a
`value_anchor_<date>.md` file — and §4 shows that absence is currently reported as a routine
findings run.** That is the highest-value item on this page.

**Cheapest fix, and it reuses work already built:** the prior-session comparison written for the
membership check (8/18, five tests passing, not yet landed) applied to a second field — compare
today's era stamp against the prior session's log and FAIL on a change. A watchlist edit during
E4 is a finding; an *arm* change during E4 is a larger one.

---

## 2 · The gates, all recomputed independently from the Price columns

### 2.1 ★★ KEEP-70 — SUPPORTED AT 20/42 = 47.62%, AND IT NO LONGER SITS NEAR THE BOUNDARY

`[V]` Both 2026-08-12 near-miss rows resolved at +5d and they **split**:

| row | conf | DQ | Price at Signal | Price +5d | +5d return | scored |
|---|---|---|---|---|---|---|
| NVDA 8/12 | 68 | HIGH | 224.18 | 217.56 | **−2.9530%** | NO |
| GLD 8/12 | 68 | HIGH | 405.56 | 413.84 | **+2.0416%** | YES |

19/40 = 47.50% → **20/42 = 47.62%**, against the ruled `SUPPORTED ⟺ rate ≤ 50.0%`. Registry
**43 → 45**; three rows pending (**GLD 8/13, and today's NVDA 8/19 and GLD 8/19**). Monitor strip
agrees: `47.6% (20/42) · supported`.

**The gate has now been supported for three consecutive readings without depending on the 8/14
boundary ruling** (50.00% on 8/17 → 47.50% on 8/18 → 47.62% today). Worth stating because the
8/14 ruling was decisive once and the 8/18 entry showed it would have been decisive a second
time under a schedule that never existed; two sessions of margin is the first evidence that the
disposition is not resting on it.

### 2.2 ★★ H4 — A SECOND CONSECUTIVE FAILING READING. THE PROMOTION IS NOT MERELY DEFERRED, IT IS REFUSED TWICE.

`[V]` HIGH-DQ near-miss +5d, computed from the Price columns and reproducing `h4_dq_threshold` exactly:

| session | reading | vs ≥60.0% bar |
|---|---|---|
| 8/17 | 11/18 = **61.1%** | PASS — first passing reading at n ≥ 12 |
| 8/18 | 11/20 = 55.0% | FAIL |
| **8/19** | **12/22 = 54.5%** | **FAIL** |

Both of today's HIGH-DQ resolutions were HIGH (NVDA NO, GLD YES), so the numerator moved +1 and n
moved +2. MEDIUM is **unchanged at 8/20 = 40.0%** — no MEDIUM near-miss resolved today. Registry
HIGH total 25, MEDIUM 20. **H4 STAYS DEMOTED.**

This is the **seventh** reading in the reversal series (60.0000% → 54.5% → 50.0% → 46.2% → 61.1%
→ 55.0% → 54.5%). The 8/18 entry recorded the two-consecutive rule *"paying for itself"* on one
reversal; today is the first session on which the *second* of the two required consecutive
readings has itself been followed by a third, and the reading is still falling. **A single
passing reading at n = 18 is now visibly an artifact of n, not a signal**, which is the exact
claim the 7/28 rule was written to make testable.

The overall condition also still holds: HIGH 499/823 = 60.6% ≥ MEDIUM 276/588 = 46.9%; LOW reads
9/22 = 40.9% at an average +5d of −4.35%.

### 2.3 ★ THE GATE-CLEARED LEDGER DID NOT MOVE, AND ITS FIRST POST-ERA RESOLUTION IS DUE TOMORROW

`[V]` Ledger unchanged at **10 rows / 3 episodes** — independently reproduced row-for-row against
`actionable_registry.md`. **Today added nothing**: both directional signals were sub-gate
(§2.4). The NVDA episode opened 8/13 therefore **closes at 8/18, four sessions**, since 8/19 did
not clear; the registry still labels it *(open)* because it was generated before that was
knowable.

**The era split is still 6 resolved PRE-DP-3C-o (5 hit) against 4 resolved POST-DP-3C-o (0
resolved), and the first post-era row — NVDA 8/13, conf 70, clearing by exactly 0 points —
resolves at +5d on 2026-08-20.** That is the next reading that can change anything on this
endpoint, and per the tab's own *"DO NOT POOL ACROSS THE ERA LINE"* instruction the 83.3% figure
stays quarantined until it does. **No disposition is read at any n**; DP-3C-l is still awaiting
the amendment recorded on 8/18.

### 2.4 ★★ TWO BUYs, BOTH REJECTED AT THE CONFIDENCE GATE — AND ONE OF THEM IS THE FIRST GLD BUY SINCE 8/13

```
[SCOUT] NVDA | BUY | 68% | Risk: REJECTED | BUY confidence too low: 68% < required 70%
[SCOUT] GLD  | BUY | 66% | Risk: REJECTED | BUY confidence too low: 66% < required 70%
```

Rejected **per account, in both accounts, on confidence first** — which independently re-confirms
the 8/04 finding that the rejection-reason ordering is confidence-first and that CHECK 6 has never
pre-empted the confidence gate for a sub-70 BUY. Both rows enter the KEEP-70 near-miss registry
(§2.1) and neither enters the gate-cleared ledger. **The 70% gate is doing the thing KEEP-70
measures, twice, on the same session.**

NVDA fell 72 → 68 while its own S1 chain still reads `68,70,72,74,72`; GLD rose to a BUY at 66 on
a `dconf` of **−10**, the steepest confidence decline of any name today, on a +3.17% trailing move
and a +3.28% session. **A rising signal on a falling confidence trend is unusual enough to note**;
it is not a defect and nothing is ruled on it.

### 2.5 ★ COHORT RESOLUTIONS, ALL THREE HORIZONS `[V]`

| horizon | cohort | n | accuracy | mean | sd(pop) | HOLD breaches |
|---|---|---|---|---|---|---|
| +5d | 2026-08-12 | 24 | 16/24 = **66.7%** | +0.19% | **4.15%** | 7/22 = 31.8% (5 UP / 2 DOWN) |
| +10d | 2026-08-05 | 24 | 15/24 = 62.5% | +2.79% | 5.08% | 8/22 = 36.4% (8 UP / 0 DOWN) |
| +20d | 2026-07-22 | 24 | 14/24 = 58.3% | +4.09% | 6.45% | 10/22 = 45.5% |

Movers at +5d: AG +7.17%, NTR +5.99%, CORN +5.04% against CBRS **−14.38%**, SND −3.34%, NVDA
−2.95%.

**Three observations, in order of how much they matter.**

**(a) The +5d cohort is the strongest in weeks and for the reason the identity predicts.** 66.7%
against 54.2% last session, on a breach count of 7 against 9, on sd 4.15%. The 8/11 cohort was
called *"the quietest tape in weeks"* at sd 3.31%; 8/12 is the second-quietest and reads 12 points
higher. **The band-breach identity continues to hold: accuracy is the breach count plus a rounding
term, and the breach count is a property of the tape.** Nothing about the generator moved.

**(b) ★★ THE +20d READING IS 58.3% — AND THAT IS A 21-POINT JUMP FROM 37.5% ONE SESSION AGO.**
The standing annotation on the +20d series says a low reading is the fixed band meeting a
twenty-day horizon on a rising tape, not generator degradation. **Today is the same annotation
running the other way and it should be recorded with equal prominence**, because a reader who
sees 37.5% → 58.3% and reads it as improvement has made exactly the error the annotation exists
to prevent. The 7/22 cohort had 10 breaches against the 7/21 cohort's 15. **The +20d series has
now printed 29.2%, 37.5% and 58.3% within a month; it is measuring dispersion at a twenty-day
horizon and it is not measuring skill.**

**(c) The +10d cohort breached 8 UP and 0 DOWN.** Every single band breach at +10d on the 8/05
cohort was upward, on a mean of +2.79%. A one-sided breach distribution is the cleanest possible
illustration that the fixed band scores a HOLD wrong for being *right about direction and wrong
about magnitude* — and it is the argument for the parked Q4-2 volatility-scaled secondary, which
**remains parked and is explicitly not reopened here.**

---

## 3 · GM is back, the predictions made on 8/18 were exact, and the check that would have caught it still has not landed

### 3.1 ★★ THE S1 PRIOR-CHAIN PREDICTION REPRODUCED TO THE DIGIT

The 8/18 entry predicted, before the run: *"On GM's next session the S1 tag will therefore render
`S1[prior=62,62,61,60,57; dconf=−5]`, five priors spanning 2026-08-11 to 2026-08-17, six elapsed
sessions, with no date anywhere in the tag."*

Today's log, verbatim: **`S1[prior=62,62,61,60,57; dconf=-5]`.** `[V]`

**The prediction is confirmed exactly, which makes the finding a demonstrated defect rather than
an argued one.** GM's momentum feature is measured across a six-session window and rendered as a
five-session trend, and no field in the tag says so. The remedy stands unchanged: carry dates or
a span in the S1 tag — the DP-3C-i remedy applied to a second tag. **Recorded as the strongest
form of evidence this record produces: a defect predicted in advance, in writing, and then
observed.**

### 3.2 ★ MEMBERSHIP RESTORED; THE PREDICTED-CORRECT FAIL DID NOT FIRE BECAUSE THE CHECK IS NOT IN

Session-over-session set difference, computed by hand again because **no tool does it yet** `[V]`:

| session | n | added | dropped |
|---|---|---|---|
| 8/17 | 26 | USO | — |
| 8/18 | 25 | — | GM |
| **8/19** | **26** | **GM** | — |

The 8/18 entry stated: *"GM's re-add will itself fire the check on the next run (25 → 26, ADDED:
GM), and it should."* **It did not, because the check is still not landed** — `signal_scan` printed
`[FAIL] signal count 26 (expected 24)` instead, the hardcoded constant now wrong against a
**fourth** successive true value (24, 25, 26, 25, 26). The membership fix is built and tested (5
cases, 2 negatives) and blocked behind the 8/03 change order's ordering requirement
(`signal_scan.py` into `edgar_parser_audit.py` first). **The one session on which the check would
have produced a correct, informative FAIL is the session on which it produced the noise FAIL
instead.**

GM's 2026-08-12 +5d resolution **filled on schedule** `[V]`: 87.1674 → 84.96 = −2.53%, scored
YES. GM now carries 64 rows with 4 unresolved at +5d, 9 at +10d, 19 at +20d — **none overdue**.
The 8/18 finding #1 (data loss, imminent) is **CLOSED**; the permanent one-session hole at
2026-08-18 remains, and remains recorded only in the notes.

The monitor strip's GM clock reads `0 post-deploy episode(s) in 31 session(s)`. GM's actual
post-deploy exposure is **30 observed sessions in 31 elapsed** and the strip counts elapsed. The
over-count is unchanged at one session, the effect on G1's disposition is nil, and it is carried
because it is the tool-reports-a-value-it-did-not-compute class attached to a gate holding a
formal disposition.

Secondary, and now consistent: the log reads `Prior-signal state loaded: 26 ticker(s)` against
`ANALYZING 26 UNIQUE TICKERS`. **The 26-vs-25 disagreement flagged on 8/18 has closed itself** —
by the watchlist moving to meet `signal_state.json`, not by anything comparing the two.

---

## 4 · The value pass reported itself as normal while computing nothing

### 4.1 ★★ `value_anchor` WROTE NO EXHIBIT, AND `value.bat` READ THAT AS "FINDINGS"

`value_anchor_2026-08-19.md` **does not exist**. `band_price_2026-08-19.md` (16:41:22) and
`implied_return_2026-08-19.md` (16:41:23) do. The pass closed on `VALUE PASS FINDINGS` — the
banner whose own text reads *"Findings are the NORMAL state here, not a failure."*

**Reproduced end-to-end in an isolated environment against the operator's real master, real
`edgar_cache` and both real logs** `[V]`:

```
today's log (no E[…] tags):   VERIFIED 0, UNVERIFIED 16   EXIT 1   md written: NO FILE
8/18 log   (E[…] tags present): VERIFIED 15               EXIT 1   md written: 6,494 bytes
```

**Both exit 1.** One computed fifteen names; the other computed nothing and wrote no file. The
16 unverified names reproduce `implied_return`'s reported `join: 0 verified, 16 unverified`
exactly.

Two defects, separately remediable:

**(a) `value_anchor.py` L493 returns 1 on a could-not-run state, contradicting its own rule three
lines above.** L432 returns **2** for an absent cache with the comment *"No cache means nothing was
computed, which is a could-not-run state."* L493 returns **1** for nothing verified — the same
state under the file's own definition. The `return 1` also short-circuits **before** the `md_path`
write at L630, which is why no exhibit exists. **The comment arguing against L493 is sitting in
the same function as L493.**

**(b) `value.bat` cannot distinguish an exit code from an artifact.** Step 3 reads `errorlevel 1`
as FINDINGS, leaves `FAIL2=0`, and step 4 runs. Nothing verifies the `.md` was written, and the
closing banner lists all three exhibit names unconditionally, including the one that does not
exist. **An unhandled Python traceback also exits 1**, so any crash in any of the three tools is
currently reported as a clean findings run.

Fix is two edits, both scoped to the value pass, neither touching the prompt, the master,
`edgar_client.py`, any E4 endpoint, KEEP-70, H4 or the ±3% band. Written up with diffs in
`value_pass_exit_code_fix_2026-08-19.md`.

### 4.2 ★★ THE TWO TOOLS IN ONE PASS DISAGREE ABOUT WHAT "NOTHING VERIFIED" MEANS

`value_anchor` suppresses its exhibit entirely. `implied_return` has no equivalent early return —
it runs to completion and **publishes an exhibit whose tables are all empty while its narrative
prose still names GM, DOW, JPM and AAPL as though they were rows**:

- §1 header row printed, then `computed 0; blocked 0`.
- §1a's verified-against-Morningstar paragraph on GM reads in full, under an empty table.
- §5's *"the 'expected DOWN' set is `[]` — and GM's own XBRL block shows operating income −31.4%
  YoY while DOW is loss-making"* — an empty set, then evidence about two names not present.
- §2 reads `informative under (I): 0 of 0  []`; §1c reads *"a crude capital base is assemblable
  for only 0 of 0 names."*
- FINDINGS 2 is emitted in full, both findings resting on names with no rows.

**One instrument's silence and another's confident empty prose, from the same cause, in the same
minute.** The 8/18 entry already flagged the GM strings as needing re-tensing to 8/17 historical;
today shows the cost is larger than staleness — **on a session with no data at all, the narrative
is the only thing the exhibit contains, and it reads as a result.** The re-tensing item is
upgraded from housekeeping to a correctness item, and `implied_return` should take the same
early-return-with-suppressed-exhibit shape `value_anchor` already has.

### 4.3 ★ WHAT THE VALUE PASS GOT RIGHT, RECORDED SO IT IS NOT DISCARDED WITH THE REST

- **`band_price` ran correctly and its output is live** `[V]` — diffed against 8/18: master rows
  1536 → 1562, cohorts 64 → 65, every per-name median and every pooled figure moved. It is
  independent of EDGAR by design, as its header claims, and **today demonstrates that claim rather
  than asserting it**: the one step that survived a lost flag is the one documented to survive a
  lost SEC.
- **Step 0's paste guard worked** — the master carried 2026-08-19 before the pass ran.
- **`quote_dump` captured 26/26 at 16:41:21** and step 1 correctly reused it.
- **`implied_return`'s join count is honest** — `0 verified, 16 unverified` is precisely what the
  imported join produces on a tagless log.

### 4.4 ★★ THE RE-TIER COUNT HELD AT 4 OF 15 WHILE ITS MEMBERSHIP CHURNED, AND THE COUNT IS THE WRONG THING TO REPORT

`[V]` from the `band_price` diff, 8/18 → 8/19:

| | 8/18 | 8/19 |
|---|---|---|
| would re-tier | **4 of 15** | **4 of 15** |
| which names | GM, WMT, **AAPL**, FTI | GM, WMT, **NKE**, FTI |

**AAPL crossed back over the HIGH/MID boundary and NKE crossed it in the opposite direction, in
one session, and the headline count did not move.** AAPL's median |+5d| went 3.323% → 3.445% on
n = 59 → 60; NKE's went 3.533% → 3.414%. A single new observation moved each name across a tier
boundary.

The 8/17 instruction was to *"report the re-tier count at every E4-2 read, beside the
primary/fallback split."* **Today shows the count is insufficient**: §3.3's fallback pools ADJACENT
against COVERED-QUIET *within tier*, so it is **which** names are mis-tiered that determines the
comparison group, not how many. Two names swapped mis-tiered status with no change to the
reported figure. **Report the membership, not the count** — and record that at n ≈ 60 the tier
assignment is unstable enough to flip on one observation, which is itself an argument about how
much weight §3.3's within-tier pooling can carry.

The tier table is **NOT re-cut**. The boundary flagged at freeze time (NVDA 0.003pp below DOW) has
still not flipped (NVDA 3.411% vs DOW 3.717%).

---

## 5 · Instrument and integrity items

### 5.1 ★ `D.op == B.blend_op` NOW FAILS ON TWO ROWS WITH FOUR- AND SIX-POINT GAPS, AND `regime_score` MORE THAN DOUBLED

`signal_scan` reports `[FAIL] D.op == B.blend_op 24/26 — NVDA op 68 vs blend_op 64; GLD op 66 vs
blend_op 60`. On 8/18 the same check fired on one row at a one-point gap.

The cause is visible in the B tag: **`regime_score` moved from a uniform −0.306 to a uniform
−0.65**, so the same 0.15 weight now produces a much larger discount. GLD additionally reads
`sec=0.0` — no sector score at all, which for a commodity trust is correct and not a defect.

**Nothing turns on it.** WS1 is **DESCOPED**, the base signal is the official output, and both
rows were rejected on the base channel anyway. But the gap is no longer cosmetic: a −6 point
blend discount on GLD would matter to any future read that touched the blend channel, and the
8/03 instruction to rephrase this assertion as informational is now **open for twelve sessions**
and producing a red line on a descoped channel on every directional row.

### 5.2 ★ `signal_scan`'s HARDCODED COUNT IS WRONG AGAINST A FOURTH TRUE VALUE

`[FAIL] signal count 26 (expected 24)`. See §3.2. Both of today's integrity FAILs are known noise;
neither is a finding. **A run whose integrity block contains only noise FAILs is a run whose
integrity block will be skimmed**, which is how §1.3's `[OK]` on the era stamp went past.

### 5.3 ★ SPCX IS THE FIRST LOW-DQ ROW SINCE 2026-07-30

`SPCX | LOW | conf 42 | S1[prior=52,50,48,47]` — a four-entry chain, correctly rendering as a cold
start. LOW-DQ rows historically read 9/22 = 40.9% at +5d with an average return of **−4.35%**, the
worst of the three strata by a wide margin. One row changes nothing and no criterion moves;
recorded because H4's overall condition requires HIGH ≥ MEDIUM and the LOW stratum is the one
with the largest effect and the smallest n.

### 5.4 ★ `Sheet1` IS STILL IN THE MASTER — FOURTEEN SESSIONS

`[V]` `logs\claude_equity_bot_tracker.xlsx` tabs read `Dashboard / Signals / Cohort Analysis /
Sheet1 / How to Use`. Unchanged from 8/18, and from 8/04, and from 7/30. **Delete it once in the
master; the drop notice going quiet is the confirmation.**

### 5.5 ★ THE NOTES MASTER CARRIES THREE `Upcoming` BLOCKS, WHICH IS THE DEFECT THE 8/04 SPLICE RECORDED AS FIXED

`[V]` `docs\analyst_notes_2026-08-17.md` contains `Upcoming` blocks at lines 2846 (Phase 3-B era),
3353 (Phase 3-C era, "every date is a trading day unless noted") and 3567 (additions from
2026-08-17). The 8/04 entry recorded: *"`docs\analyst_notes.md` carried TWO Upcoming blocks — the
7/29 multi-line version was never removed when the 7/30 single-line version was appended.
Superseded in this splice by a single current block."*

**It recurred.** Line 2846 is a legitimate era-boundary artifact; **3353 and 3567 are both
Phase 3-C blocks and 3353 is stale by roughly five sessions.** A reader arriving at the file
cannot tell which block is current without checking dates. **Nothing has been deleted** — the
house rule that historical entries are never rewritten cuts against a silent purge, and the call
is the operator's. Recommended: mark 3353 `SUPERSEDED 2026-08-18` inline rather than remove it,
which preserves the record and removes the ambiguity in one line.

### 5.6 Operational

- **Run started 09:30:16 CST**, first signal 09:30:40, last 09:35:31 — **the canonical 9:30, and
  the first on-time run in three sessions** after 10:06 on 8/18 and 11:08 on 8/04. Px@signal for
  all 26 rows is a canonical open-session quote. Recorded because the last two entries both
  carried a late-start annotation and this one does not.
- **26 unique tickers, 18 held + 8 scouting.** Suggestions ran normally (776 in / 1,040 out).
- **Zero WARNING or ERROR lines in the entire log** `[V]` — a consequence of EDGAR being absent,
  since both of 8/18's warnings came from `edgar_client`. **An empty warning channel is not
  evidence of a clean run today; it is evidence that the subsystem that emits warnings did not
  run.**
- **The two 2026-06-01 ghost rows are unchanged** — AG and FTI, null Signal/Confidence/DQ,
  complete price series at all three horizons. Still the only incompleteness in 1,562 rows.
- **Cohort profile:** mean 56.8, median 59.0, sd(pop) 10.19, min 33 (CBRS), max 72 (FTI), DQ 16
  HIGH / 9 MEDIUM / 1 LOW — reproduces `signal_scan` exactly `[V]`. Confidence mean and sd are
  *identical* to 8/18's on a different n and a different arm, which is coincidence and is stated
  as such.

---

## 6 · Findings, ranked

| # | finding | class | action |
|---|---|---|---|
| 1 | **`EQUITY_EDGAR` was not set; 2026-08-19 is a control cohort and the E4 clock did not advance.** Third occurrence of the mechanism the runbook named; second time it has produced a control cohort | measurement, recurring | **Before tomorrow's run:** `set EQUITY_EDGAR=1` and confirm `A-S1D1-B1-E1` in line 3 of the log. Then add an era-change alarm |
| 2 | **Nothing in the stack alarms on a lost flag.** `signal_scan` prints the era and marks it `[OK]`; the only signal is a missing `value_anchor` exhibit, which reads as a routine findings run | detection gap | Extend the built-but-unlanded prior-session comparison to the era field |
| 3 | **`value_anchor` returns 1 (findings) on a could-not-run state and writes no exhibit; `value.bat` cannot tell that from a clean run.** A Python traceback would behave identically | tool-reports-a-state-it-did-not-act-on | `return 2` at L493; add an artifact guard to each step of `value.bat`. Diffs supplied |
| 4 | **`implied_return` publishes an exhibit with empty tables and full narrative prose naming absent tickers** | correctness, upgraded from staleness | Give it `value_anchor`'s early-return shape; re-tense the GM strings to 8/17 historical |
| 5 | **H4's second consecutive failing reading (54.5%)** — the single 61.1% pass at n = 18 is now visibly an n artifact | endpoint, resolved favourably | None. The rule is working; record the seventh reading |
| 6 | **The re-tier count held at 4/15 while its membership swapped AAPL ↔ NKE** | measurement | Report tier *membership* beside the E4-2 split, not the count |
| 7 | **The 8/18 S1 prior-chain prediction reproduced exactly** (`prior=62,62,61,60,57; dconf=−5`) | confirmed defect | Carry dates or a span in the S1 tag |
| 8 | **Membership check still not landed**; hardcoded 24 now wrong against a fourth true value, and it fired noise on the session the real check would have been informative | blocked behind change-order ordering | Land it — `signal_scan.py` into `edgar_parser_audit.py` first |
| 9 | **+20d printed 58.3% after 37.5%**, a 21-point swing on the breach count | narrative risk | Annotate upward swings as explicitly as downward ones |
| 10 | **`D.op == B.blend_op` FAIL on 2 rows at 4 and 6 points**, `regime_score` −0.306 → −0.65 | wording, open 12 sessions | Rephrase as informational |
| 11 | **Notes master carries three `Upcoming` blocks** — the 8/04 defect recurred | record integrity | Mark the stale Phase 3-C block SUPERSEDED; do not delete |
| 12 | **`Sheet1` still in the master**, 14 sessions on | integrity, G4 | Delete once |

---

## 7 · Standing

T1 (advisory-only, pre-execution, mandatory) · T3. **2026-08-19 IS A CONTROL COHORT, era
`A-S1D1-B1`; it is NOT E4 cohort 5 and it is NOT a SHAKEDOWN — the artifact is correct and the
treatment simply did not run.** E4 clock: **still cohort 4 of ~10.** **KEEP 70% — SUPPORTED at
20/42 = 47.62% on the row basis; the row-vs-episode basis remains UNRULED.** H4 **STAYS DEMOTED**
(54.5%, second consecutive failing reading). Gate-cleared ledger unchanged at 10 rows / 3
episodes, **no disposition read at any n**, first post-era resolution due 2026-08-20. ±3% HOLD
band unchanged and **NOT re-baselined**. Frozen E4-2 tier table **NOT re-cut**. Blend (WS1)
**DESCOPED**. Q4-2 **parked**, and today's one-sided +10d breach distribution is not grounds to
reopen it. Peer-relative M/B–ROE form DESCOPED, P/E form PARKED. Nothing in the valuation layer
touches the prompt. G1 **INSUFFICIENT TEST CONDITIONS**; both tracers generating.

*Advisory-only · no orders · not financial advice.*
