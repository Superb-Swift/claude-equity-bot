# Closing Review — 2026-08-20

*Claude Equity Bot · Phase 3-C · **E4 cohort 5** · era `A-S1D1-B1-E1` · advisory-only · no orders · not financial advice.*

**Cross-check 26/26 CLEAN** `[V]` — `signals_2026-08-20.log` ↔ `logs\claude_equity_bot_tracker.xlsx`, reproduced independently from the log JSON at full precision (signal, confidence, DQ, Price at Signal); zero rows in one and absent from the other in either direction. Era `A-S1D1-B1-E1` in every Signal JSON and in no phase bracket; `regime_score` uniform at **−0.71**; confidence channels present on all rows; totals **1,588 rows, 66 cohorts**; resolutions complete at all three horizons with **zero overdue** and no premature values on today's rows. Every figure below is computed from the Price columns and is formula-cache independent.

**The flag was set, the treatment ran, and E4 gained cohort 5.** Three instruments shipped in the last two sessions had their first live run today. Two worked. One found a defect in itself.

**This review carries a same-session self-correction.** §4.1 diagnosed CORN's degradation as a self-perpetuating cache failure and recommended one command. The operator ran it, the output falsified the mechanism, and **§4.1a retracts it** — the true mechanism is more general and more expensive, and **§4.1b** is a finding the probe surfaced that nothing in the stack was looking for. §4.1 is left standing as written rather than edited, per the rule that a wrong reading is corrected in place and visibly.

---

## 1 · The three new instruments, on first contact

### 1.1 ★★ THE ERA ALARM FIRED ON ITS FIRST LIVE RUN — ON THE RECOVERY, AND ITS ADVICE WAS WRONG

`[V]` verbatim from `signal_scan_2026-08-20.md`:

```
[FAIL] era stamp CHANGED since 2026-08-19: A-S1D1-B1 -> A-S1D1-B1-E1  ** THE RUN
       EXECUTED ON A DIFFERENT ARM. Check EQUITY_EDGAR. During E4 this is a
       cohort-level finding, not a formatting one
```

**The detection is correct and the remediation text is exactly backwards.** The arm did change; the change was the *fix*. Today's flag is right and yesterday's was wrong, and "Check EQUITY_EDGAR" points the operator at a setting that is now correct.

**The alarm is directionally blind.** It compares today against the prior session and reports any difference as a regression, because it was written on the session the flag was *lost* and the only case in view was a loss. A recovery produces an identically-worded FAIL. Two consequences, of different size:

1. **Cosmetic but corrosive:** a FAIL whose advice is wrong is a FAIL that teaches the reader to skim it — the precise failure mode this alarm was built to prevent (§1.3 of the 8/19 entry). It is the noise-FAIL problem reintroduced by the fix for the noise-FAIL problem.
2. **Substantive:** an alarm that cannot tell a loss from a recovery cannot be used to gate anything, and it should not be, until it can.

**Remedy, and it is small.** The alarm knows both era strings; it needs one rule about which direction is a regression:

| transition | today's output | correct output |
|---|---|---|
| `A-S1D1-B1-E1` → `A-S1D1-B1` | FAIL, "check EQUITY_EDGAR" | **FAIL — treatment LOST. Check EQUITY_EDGAR.** |
| `A-S1D1-B1` → `A-S1D1-B1-E1` | FAIL, "check EQUITY_EDGAR" | **WARN — treatment RESTORED after a control session. Confirm the control cohort is recorded as ABSENT from E4.** |
| any → unknown | FAIL | FAIL |

**Recorded as my own defect, found on first live use, which is the record's own maxim working exactly as written:** *"The first live run of anything is where the defects are. Not the test suite."* Eleven assertions passed, five cases, three negatives — and none of them was a recovery, because on 2026-08-19 a recovery had not happened yet.

### 1.2 ★★ THE VALUE-PASS FIXES WORKED END TO END, AND THE EXHIBIT SET IS COMPLETE FOR THE FIRST TIME SINCE 8/18

`[V]` All four artifacts written this run: `quote_dump.json` (26/26 ok, captured 15:18:27), `band_price_2026-08-20.md`, **`value_anchor_2026-08-20.md`** and `implied_return_2026-08-20.md` (22,409 bytes against 8/19's empty 11,574).

The join reads **16 verified, 0 unverified** — against 0 verified / 16 unverified on 8/19. The chain that failed on 8/19 is now closed at every link: the flag was set → `E[…]` tags exist on 17 of 26 rows → route 2 of the two-route join resolves → 16 tickers verify → 14 compute.

**GM is back in the valuation layer**, and that resolves an 8/18 finding by a route nobody chose. The three carried-forward `implied_return` strings that referenced a name absent from their own tables — §1a's "GM reads 4.88% in this table", §5's expected-DOWN evidence, and FINDINGS 2 — are **current again**, because GM is in the table at 4.88% exactly as the sentence says. **The re-tensing item is therefore not closed, only dormant:** the strings are correct today by luck of GM's return, and they will read as current the next time GM drops out. Fix the tense anyway.

The layer's only external verification is reproducible again: Schwab eps 3.27 = GM's FY2025 10-K diluted EPS 3.27, against Morningstar's 3.28%. **It still rests on one ticker.**

### 1.3 ★ THE ARTIFACT GUARD DID NOT FIRE, WHICH IS THE RESULT IT SHOULD PRODUCE ON A GOOD DAY

`VALUE PASS FINDINGS` with all three exhibits stamped WRITTEN this run. The guard is only visible when it catches something; a silent guard on a clean pass is the design working. Recorded because the alternative reading — "the guard did nothing" — is how a guard gets removed.

---

## 2 · WS2 / G1 — the second post-deploy episode, and the two channels disagree for the first time

### 2.1 ★★ WMT PRODUCED G1's SECOND POST-DEPLOY EPISODE, 19 SESSIONS AFTER THE FIRST

`[V]` computed from the master's Price column, coalesced, THETA = 5.0%:

| episode | date | trailing 5-session move | response |
|---|---|---|---|
| 1 | 2026-07-23 | −5.19% | lag 0, 47 → 38 (−9.0pt), **D1 damp 0** |
| 2 | **2026-08-20** | **−10.09%** | lag 0, 46 → 35 (−11.0pt), **D1 damp 7** |

WMT closed 114.30 → 103.80, a **−9.18% single session**, with an **8-K filed 2026-08-20** in its own E tag (`E[8k=1@2026-08-20; …]`). GM produced nothing (trail −2.89%, damp 0) and its clock reads 0 post-deploy in 32 sessions.

The monitor strip agrees: `2 post-deploy episode(s) in 33 session(s) (2 responded ≤2 sessions)`. **G1's stated bar — ≥1 episode with response ≤2 sessions — is met on both episodes.** The pre-registered n = 4 is not, so **G1 stays INSUFFICIENT TEST CONDITIONS**; nothing is re-read here at n = 2.

### 2.2 ★★ THE TWO-CHANNEL ACCEPTANCE SLICE RETURNS DIFFERENT LAG VERDICTS, AND UNTIL TODAY IT COULD NOT HAVE

`[V]` The two files the daily review has been producing since deploy:

| slice | estimated lag | corr(conf, trailing move) | today's WMT confidence |
|---|---|---|---|
| `h1_lag_trace_WMT_3B.md` (operative) | **0 sessions** | +0.794 | 35% |
| `h1_lag_trace_WMT_raw_3B.md` (raw) | **1 session** | +0.662 | 42% |

**Before today these two files were byte-identical.** On 2026-08-19 both were 2,866 bytes; the diff is empty on every prior session. The reason is on the record, stated on 2026-07-30: *"all four damped names are outside the WS2 tracer universe, and WMT and GM both read damp 0, so operative ≡ raw on both tracers and E2 remains trivially satisfied and substantively untested."*

**2026-08-20 is the first post-deploy session on which a WS2 tracer was damped.** `D[raw=42; op=35; trail=-9.95%; damp=7]` — and note that **op 35 is exactly the D1 FLOOR**, so the damping was clamped and the arithmetic still reconciles (`D.op == floor-aware(raw, damp)` 26/26).

Why it matters, stated precisely and without re-reading the gate:

- G1's FAIL condition is *"model-side remedy class exhausted at 3-B."* The measurement that answers it is the **model-side** channel — S1's raw confidence — because D1 is not the remedy under test.
- Episode 1 was unambiguous: lag 0 with D1 contributing nothing, so the response was entirely model-side.
- Episode 2 reads **lag 0 on the operative channel and lag 1 on the raw channel**. Both clear the ≤2-session bar, **so the disposition does not turn on it today.** It will the moment a channel reads 3 or more.
- **The monitor strip reports one number and does not say which channel produced it.** `(2 responded ≤2 sessions)` is true on both channels today and therefore harmless today. It is the tool-reports-a-value-it-did-not-decompose class attached to a gate carrying a formal disposition — the same place the record has twice said it least belongs.

**E2 is no longer trivially satisfied.** For the first time since deploy, operative ≠ raw on a tracer. That is a fact about the measurement apparatus, not about the gate, and it should be recorded before the n = 4 read rather than discovered at it.

### 2.3 ★ E4-3's CHANNEL CHOICE HAS ITS FIRST CONSEQUENCE TODAY

E4-3 is pre-registered as a trace table around material 8-K dates, **RAW channel only**. WMT filed an 8-K today and is a covered name, so this is an E4-3 event — **and it is the first event in the record on which the raw and operative channels differ on a tracer.** The pre-registration's channel choice was made before any such event existed and is vindicated by the first one. Recorded because a choice that costs nothing until it matters is invisible until it matters.

---

## 3 · The gates

### 3.1 ★★ THE FIRST POST-DP-3C-o GATE-CLEARED ROW RESOLVED, AND IT PAID NO

`[V]` **NVDA 2026-08-13, BUY, conf 70 — clearing the gate by exactly 0 points — 224.88 → 216.85 = −3.57%. Scored NO.**

| era | rows | resolved +5d | hit |
|---|---|---|---|
| PRE-DP-3C-o | 6 | 6 | **5 = 83.3%** |
| POST-DP-3C-o | 4 | **1** | **0 = 0.0%** |

The 8/19 entry named this as *"the next reading that can change anything on this endpoint."* It arrived and it went against the pre-era figure. **Nothing is read from n = 1**, and the tab's own instruction holds: *"DO NOT POOL ACROSS THE ERA LINE."* The pooled ROW basis now reads 5/7 = 71.4% and **must not be quoted** — it mixes six pre-era rows with one post-era row. Episode basis 1/3 = 33.3%. Ledger unchanged at 10 rows / 3 episodes; three post-era rows still pending (NVDA 8/14, 8/17, 8/18).

**Direction, stated per house practice: this runs AGAINST the phase looking good**, and it is the first evidence that the 83.3% was an era artifact rather than a result — which is precisely what the mandatory era split was built to expose. The split earned its keep today.

### 3.2 ★ KEEP-70 — SUPPORTED AT 21/43 = 48.84%, AND THE MARGIN NARROWED

GLD 2026-08-13, conf 65 HIGH, 400.02 → 414.75 = **+3.68% YES**. Registry **45 → 47**; four pending (NVDA and GLD on both 8/19 and 8/20).

| basis | reading | under the ruled `≤ 50.0%` rule |
|---|---|---|
| ROW | **21/43 = 48.84%** | SUPPORTED |
| EPISODE (DP-3C-m coalesced, opening row) | **10/18 = 55.6%** | NOT SUPPORTED |

Row basis moved 47.62% → 48.84% — **still supported, but the margin fell for the first time in four readings** (50.00% → 47.50% → 47.62% → 48.84%). One more YES without a matching NO puts it back on the boundary. **The basis remains UNRULED and the two continue to straddle.** Monitor strip agrees at 48.8%.

### 3.3 ★ H4 — THIRD CONSECUTIVE FAILING READING, AND THE RATE TICKED UP

HIGH-DQ near-miss +5d: 8/17 **61.1% PASS** → 8/18 55.0% FAIL → 8/19 54.5% FAIL → **8/20 13/23 = 56.5% FAIL**. MEDIUM unchanged at 8/20 = 40.0%; registry HIGH total 27. Overall HIGH 514/843 = 61.0% ≥ MEDIUM 276/593 = 46.5%; LOW 9/22 = 40.9%.

**H4 STAYS DEMOTED.** The rate rose 2.0pt and is still 3.5pt short of the bar. Eighth reading in the reversal series. The single 61.1% pass at n = 18 now sits alone against three failures at n = 20, 22 and 23 — **the two-consecutive rule has not merely delayed a promotion, it has outlived the reading that would have started one.**

### 3.4 ★ COHORT RESOLUTIONS, ALL THREE HORIZONS `[V]`

| horizon | cohort | n | accuracy | mean | sd(pop) | HOLD breaches |
|---|---|---|---|---|---|---|
| +5d | 2026-08-13 | 25 | 15/25 = **60.0%** | −0.39% | 4.97% | 9/23 (4 UP / 5 DOWN) |
| +10d | 2026-08-06 | 24 | 10/24 = 41.7% | +2.10% | 6.71% | 13/22 (7 UP / 6 DOWN) |
| +20d | 2026-07-23 | 24 | 10/24 = 41.7% | +4.63% | **8.24%** | 14/23 (11 UP / 3 DOWN) |

+5d movers: AG +13.47%, NTR +8.40%, DOW +7.46% against **WMT −10.05%**, CBRS −6.76%, SPCX −5.17%.
+20d movers: AG +30.24%, MSFT +27.43%, GLD +11.72% against XLU −5.49%, WMT −4.07%, AAPL −3.17%.

The +20d reading fell 58.3% → 41.7% on a breach count of 14 against 10, at the **highest dispersion in a month** (sd 8.24%). Same annotation as always, now stated in both directions per the 8/19 entry: **the +20d series has printed 29.2%, 37.5%, 58.3% and 41.7% within five weeks and is measuring dispersion at a twenty-day horizon, not skill.**

---

## 4 · EDGAR and the valuation layer

### 4.1 ★★ CORN DEGRADED FOR THE SECOND CONSECUTIVE EDGAR SESSION — SAME NAME, AND IT IS NOT RANDOM

`[V]` The run-budget warning fired at 09:36:31. Per-ticker tags: **exactly one name degraded, CORN, tagged `fin=degraded`** — identical to 2026-08-18. Sixteen names rendered full sections, nine are structurally dark (AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU).

**CORN is the last ticker processed in both runs.** The processing order ends `… SPCX, GM, CORN`, so by the time CORN is reached the wall-clock budget is long gone and only a warm cache can save a name.

The v7.0 §4.2 guidance held: the run-level warning claimed run-wide degradation, the tags said one name, and the tags were right.

### 4.1a ★★ SELF-CORRECTION, SAME SESSION — THE MECHANISM I GAVE IN §4.1 IS WRONG, AND THE CORRECT ONE IS WORSE

**Written in §4.1 above and now retracted:** *"CORN's cache cannot be warm, because it degrades before it can be written — the same self-perpetuating cache failure … it will recur every session until the cache is warmed out of band."*

`[V]` The operator ran the recommended command. It returned a complete section **in seconds**, cached cleanly, and tagged `E[8k=0; form4=0f; periodic=10-Q@2026-08-14; fin=1@2026-06-30]`. **The cache warms without difficulty. There is nothing self-perpetuating about it.**

**The actual mechanism, and it generalises past CORN.** CORN filed a **new 10-Q on 2026-08-14**. The derived cache is keyed on accession plus schema version, so a new accession is a cold entry that must be fetched and extracted on first encounter. CORN is processed **last**, the wall-clock budget is spent long before the run reaches it, and the cold extraction is abandoned every session — so the new accession has never been written. Both degraded sessions carry `periodic=10-Q@2026-08-14`, which is the fingerprint.

**Why the correct mechanism is worse than the one I retracted.** A self-perpetuating CORN-specific failure is one name and one command. What is actually happening is: **any covered name whose new periodic lands while it sits late in the processing order will degrade, silently, until someone fetches it by hand.** The processing order is not stable — it follows the held/scouting split — and periodic filings arrive on every filer's own calendar. This is a **recurring, order-dependent treatment gap with no alarm attached**, and it has now produced two degraded E4 rows without anyone noticing until the tags were read by hand.

The 2026-08-03 F-1 finding described exactly this shape — *"the in-run recompute started, was abandoned at budget, and NEVER WROTE TO CACHE"* — and DP-3C-j's remedy (move the timer inside `edgar_client`) is still unimplemented. **F-1 is not a historical finding. It is live, and it is now costing E4 rows on a quarterly cadence.**

**Revised remedy.** The one-off command was right and is done. The standing fix is either (i) implement DP-3C-j so the budget bounds EDGAR time rather than wall clock, or (ii) prefetch cold accessions before the signal loop, or — cheapest and available today — (iii) have the run FAIL rather than WARN when a covered name tags `fin=degraded`, so it is never again discovered by hand-reading tags.

### 4.1b ★★ AND THE PROBE FOUND SOMETHING LARGER: TWO OF THE COVERED-15 ARE STRUCTURALLY NEAR-EMPTY

`fin=1` is one statements line. That is not a degradation artifact — it is what CORN has. Measured across the frozen covered-15 from today's tags `[V]`:

| statements lines | names |
|---|---|
| 9–11 | AAPL, MSFT, SND, NVDA, FTI, PM, PWR, NKE, RTX, WMT, GM |
| 6–7 | DOW, JPM |
| **3** | **GLD** |
| **1** | **CORN** |

And on the event axis, today's tags show **exactly two of the fifteen produced no 8-K and no Form 4: CORN and GLD.** Both are commodity trusts. CORN's MD&A extract is the Teucrium Commodity Trust formation description — *"a Delaware statutory trust organized on September 11, 2009 … On June 8, 2010, four Creation Baskets for CORN were issued"* — with no discussion of the current period at all. That is not a bad slice; **a trust's 10-Q Overview is always its own formation description**, so the §12 "MD&A is variable" caveat is, for this filer class, a permanent condition.

**This vindicates a scepticism the record wrote down in advance and has never revisited.** The 2026-08-02 coverage audit corrected Kickoff §2 on exactly these two names — §2 had called CORN's 39 and GLD's 33 MEDIUM rows untreatable; the audit found both file, and recorded the correction as **running toward the treatment, flagged as "exactly the direction that warrants the most scepticism."** Today's measurement settles it: **§2 was right on substance and the correction was right only on the letter.** Both names are reachable in the sense that a document exists, and untreatable in the sense that what is in it is one and three statements lines and no event flow.

**Three consequences for E4, none of which re-cuts anything:**

1. **E4-2's primary read (§3.2, within-ticker, requires a name in BOTH arms) gets nothing from CORN or GLD** — not "almost always quiet" as the pre-registration warned, but **always** quiet. The effective primary population is 13, not 15.
2. **E4-2's fallback (§3.3, pooled within tier) is worst-hit in LOW**, because the frozen LOW tier is {JPM, GLD, CORN, RTX, WMT} — **two of its five names can never be ADJACENT.** Within LOW the ADJACENT arm draws only on JPM, RTX and WMT while the QUIET arm is diluted by two names carrying near-zero treatment. That is the confound the tier table exists to remove, arriving through a door the tier table does not watch.
3. **A third denominator is now required.** The record reports the pre-registered 15/24 and the practical 14–15/24. Today shows **ADJACENT-ELIGIBLE coverage = 13/24 = 54.2%**, and that is the denominator E4-2's primary read actually runs on.

**An uncomfortable corollary, stated because it runs against the freeze.** The two names admitted since the table was frozen — **SPCX (fin=10, two 8-Ks) and USO (fin=6, one 8-K)** — carry **more** treatment than two names inside the frozen population. **The table is NOT re-cut and must not be**: freezing it before the first E4 cohort resolved was a go-live prerequisite precisely so a control could not be fitted to its data, and that reasoning is unaffected. The remedy is to **report the third denominator and the LOW-tier imbalance at every E4-2 read**, not to change the population.

`value_anchor` has been saying the same thing from the other side all along and nobody connected it: **GLD and USO read "NOT COMPUTED — missing Diluted EPS" on every run**, for the same structural reason a trust has no earnings. Two instruments, one fact, agreeing.

### 4.2 ★★ THE RE-TIER COUNT WENT 4 → 6 OF 15 IN ONE SESSION, AND THE MEMBERSHIP TURNED OVER AGAIN

`[V]` Three consecutive sessions of the frozen E4-2 tier table at n = 59 → 61:

| session | count | membership |
|---|---|---|
| 2026-08-18 | 4 of 15 | GM, WMT, **AAPL**, FTI |
| 2026-08-19 | 4 of 15 | GM, WMT, **NKE**, FTI |
| **2026-08-20** | **6 of 15** | GM, WMT, NKE, **AAPL**, **NVDA**, FTI |

AAPL left and returned across two sessions; NVDA crossed MID → HIGH today. **This is the v7.0 §14 instruction being paid for on the session after it was written:** the count is not the reportable quantity, because §3.3's fallback pools ADJACENT against COVERED-QUIET *within tier*, and it is which names are mis-tiered that fixes the comparison group.

The boundary the freeze document flagged (NVDA 0.003pp below DOW) **still has not flipped** — NVDA 3.475% vs DOW 3.835% — while NVDA crossed the MID/HIGH cut anyway. The sensitivity note was aimed at the wrong boundary, and that is now demonstrated twice. **The table is NOT re-cut.**

### 4.3 ★ THE `peRatio` `[?]` HAS A LIVE TEST CASE FOR THE FIRST TIME

`implied_return` §5 puts **WMT in the 'expected DOWN' set** (px/eps 38.08 vs peRatio 40.24, ratio 1.057) on the same session WMT filed an 8-K and fell 9.2%. The open question is whether `eps` is trailing and `peRatio` forward; **a live earnings event inside the window is the cleanest test the record has ever had for it**, and `quote_dump.json` has been accumulating both fields daily since 8/17. Run `fundamental_probe.py` now, while the event is fresh — a `peRatio` that moves on a day `eps` does not is the discriminator.

### 4.4 ★ COVERAGE, AND THE HEADLINE VALUATION READ

`[EDGAR] prefetch: 21/26 resolved to submissions` against **17/26 sections actually rendered** — the known and still-undocumented `--coverage` gap, now wrong against a fourth true value. `value_anchor` computed 14 of 16 verified (GLD and USO NOT COMPUTED — missing Diluted EPS, structural); PM's M/B stays suppressed on non-positive book equity of −8.58B with a balance-sheet residual of 2.82% of assets, flagged for inspection as on every prior run.

`implied_return` §4: **eight of thirteen names require MORE THAN A DOUBLING of trailing ROE** at a 9% cost of equity — AAPL 2.50x, NVDA 2.64x, PWR 6.06x, SND 15.15x. **No valuation is asserted and no price target is implied**, and nothing here touches the prompt or any endpoint (DP-V1).

---

## 5 · Instrument and integrity items

### 5.1 ★ `confidence_blend` SEMANTICS CONFIRMED ON A FOURTH OBSERVATION

`signal_scan` reports: rows where blend ≠ blend_op, n = 1 — tracks `B.blend` 0/1, tracks `B.blend_op` **1/1**. **The field named for the blend channel carries the POST-damping value.** The 2026-07-30 reading was n = 3 and explicitly provisional; today's damped tracer row is the fourth observation and it agrees. The `[?]` is closeable.

### 5.2 ★ THE TWO KNOWN-NOISE FAILS BOTH FIRED AGAIN, EXACTLY AS v7.0 §6.1 SAYS THEY WILL

`[FAIL] signal count 26 (expected 24)` — the hardcoded constant, now wrong against a **fifth** successive true value. `[FAIL] D.op == B.blend_op 24/26` — NVDA op 68 vs blend_op 65, GLD op 65 vs blend_op 58, on a DESCOPED channel. Both were documented as noise the day before they fired. **CORRECTED 2026-08-20, after this section was written:** the membership check is **NOT blocked**. `signal_scan.py` entered `edgar_parser_audit.py` on **2026-08-10** — the audit runs it as parser [7] and asserts all three `fin=` states — and `log_tracker_crosscheck` followed on 8/12. **The blocker cited on 8/18, 8/19 and again above has not existed for ten sessions.** The check was described as built and tested on 8/18; it is not in the deployed `signal_scan.py`, so landing it is the operator's call and nothing gates it. See `DP-3C-j_Implementation_2026-08-20.md` §4.

### 5.3 ★ `Sheet1` IS STILL IN THE MASTER — FIFTEEN SESSIONS

Tabs read `Dashboard / Signals / Cohort Analysis / Sheet1 / How to Use`. Unchanged since 2026-07-30.

### 5.4 Operational

- **Run started 09:34:03 CST**, first signal 09:34:36, last 09:40:10 — canonical, second on-time run in a row.
- **26 tickers, 18 held + 8 scouting.** `Prior-signal state loaded: 26` against `ANALYZING 26` — the 8/18 mismatch stays closed.
- **DQ 20 HIGH / 6 MEDIUM / 0 LOW** — SPCX recovered from LOW to HIGH. Cohort profile mean 56.7, median 59.0, sd(pop) 11.41, min 32 (CBRS), max 74 (FTI); reproduces `signal_scan` exactly `[V]`.
- **Two BUYs, both rejected on confidence** — NVDA 68, GLD 65, both per account, confidence-first. No gate-clearing directional; the ledger did not grow.
- **`band_price` integrity block:** price-derived Return+5d reproduces the cached column on **1,460 of 1,460** rows, zero mismatches; BAND=0.03 confirmed against the workbook's own column on 1,408 HOLD rows, zero disagreements.
- The two 2026-06-01 ghost rows are unchanged and remain the only incompleteness in 1,588 rows.

---

## 6 · Findings, ranked

| # | finding | class | action |
|---|---|---|---|
| 1 | **The era alarm cannot distinguish a lost arm from a restored one**; it FAILed on today's recovery with remediation text that was wrong | my defect, first live run | Add the direction rule (§1.1). Until then, read the arrow, not the word FAIL |
| 2 | **G1's two-channel slice returns different lag verdicts** (operative 0, raw 1) — the first session a tracer was damped, and the first on which the two files differ at all | measurement apparatus | Record before the n = 4 read. Make the monitor strip state which channel it scored |
| 3 | **First POST-DP-3C-o gate-cleared row resolved NO** (0/1) against a pre-era 5/6 | endpoint, runs against the phase | None. Do not pool. DP-3C-l amendment still owed |
| 4 | **F-1 IS LIVE, NOT HISTORICAL.** A new accession on a late-processed name is abandoned at the wall-clock budget and never cached — it will recur on any covered name whose periodic lands while it sits late in the order | recurring order-dependent treatment gap, no alarm | Implement DP-3C-j, or prefetch cold accessions, or — today — make `fin=degraded` on a covered name a FAIL |
| 4b | **CORN and GLD are structurally near-empty** (1 and 3 statements lines, zero 8-K/Form 4) — the two names the 8/02 correction rescued from Kickoff §2's untreatable list | E4 measurement, vindicates a pre-registered scepticism | Report **ADJACENT-eligible 13/24 = 54.2%** as a third denominator, and the LOW-tier imbalance, at every E4-2 read. Do NOT re-cut |
| 5 | **Re-tier count 4 → 6 of 15**, membership turned over twice in three sessions | measurement | Report membership at every E4-2 read, per v7.0 §14 |
| 6 | **KEEP-70 margin narrowed** to 48.84%; episode basis still opposite | gate, basis UNRULED | Rule the basis |
| 7 | **H4 third consecutive failing reading** (56.5%) | endpoint | None. The rule is working |
| 8 | **`implied_return`'s GM strings read as current only because GM returned** | dormant staleness | Re-tense to 8/17 historical anyway |
| 9 | **`peRatio` `[?]` has a live earnings event to test against** | open question | Run `fundamental_probe.py` now |
| 10 | **Membership check still blocked**; hardcoded 24 wrong against a fifth value | change-order ordering | `signal_scan.py` → `edgar_parser_audit.py` first |
| 11 | **`confidence_blend` semantics confirmed at n = 4** | `[?]` closeable | Close it |
| 12 | **`Sheet1` still in the master**, 15 sessions | integrity, G4 | Delete once |

---

## 7 · Standing

T1 (advisory-only, pre-execution, mandatory) · T3. **2026-08-20 is E4 cohort 5**, era `A-S1D1-B1-E1`, treatment delivered on 17 of 26 rows with one degraded name (CORN). **E4 clock: cohort 5 of ~10.** Practical coverage 15/24; **ADJACENT-eligible coverage 13/24 = 54.2%** — CORN and GLD produce no 8-K and no Form 4 and cannot enter the ADJACENT arm. **KEEP 70% — SUPPORTED at 21/43 = 48.84% on the row basis, NOT SUPPORTED at 10/18 = 55.6% on the episode basis; the basis is UNRULED.** H4 **STAYS DEMOTED** (56.5%, third consecutive failing reading). Gate-cleared ledger 10 rows / 3 episodes, **no disposition read at any n**; post-era arm opens 0/1. ±3% HOLD band unchanged and **NOT re-baselined**. Frozen E4-2 tier table **NOT re-cut**; 6 of 15 would re-tier. Blend (WS1) **DESCOPED**. Q4-2 **parked**. Peer-relative M/B–ROE form DESCOPED, P/E form PARKED. Nothing in the valuation layer touches the prompt (DP-V1). **G1 INSUFFICIENT TEST CONDITIONS — 2 of 4 post-deploy episodes, both responding ≤2 sessions, the bar NOT lowered and the n NOT met.** E2 is no longer trivially satisfied.

*Advisory-only · no orders · not financial advice.*
