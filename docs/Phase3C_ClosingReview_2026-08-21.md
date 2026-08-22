# Closing Review — 2026-08-21

*Claude Equity Bot · Phase 3-C · **E4 cohort 6** · era `A-S1D1-B1-E1` · advisory-only · no orders · not financial advice.*

**Cross-check 26/26 CLEAN** `[V]` — `signals_2026-08-21.log` ↔ `logs\claude_equity_bot_tracker.xlsx`, reproduced independently from the log JSON at full precision (signal, confidence, DQ, Price at Signal); zero rows in one and absent from the other in either direction. Era `A-S1D1-B1-E1` in every Signal JSON and in no phase bracket; `regime_score` uniform at **−0.918**; confidence channels present on all rows; totals **1,614 rows, 67 cohorts**; resolutions complete at all three horizons with **zero overdue** and no premature values on today's rows. Every figure below is computed from the Price columns and is formula-cache independent.

**Three things happened that had not happened before.** The gate-cleared ledger took its first non-NVDA episode since June and its first ever on a name that receives no EDGAR treatment at all. The `peRatio` open question was settled by a natural experiment the record asked for yesterday and got for free today. And a G1 acceptance exhibit was found to have been printing a confidence that exists in no channel anywhere in the stack.

**Four instrument fixes were landed this session and verified against the real logs**, including the membership check that has been quoted as blocked since 8/18 on a prerequisite satisfied on 8/10. Run integrity findings fell **2 → 1**. Full memo: `H1LagTrace_Truncation_Defect_2026-08-21.md`.

---

## 1 · The ledger

### 1.1 ★★ THE FIRST GATE-CLEARING DIRECTIONAL OF THE E4 ERA, AND IT LANDED ON A NAME WITH NO EDGAR TREATMENT

`[V]` **NTR BUY 72, HIGH DQ, $74.50, clearing the 70% gate by +2.** The ledger goes **10 → 11 rows and 3 → 4 episodes**; episode `NTR-20260821` opens. It is the first gate-clearing directional that is not NVDA since **CBRS on 2026-06-26**, and the first ever inside the E4 era.

**And it is an uncovered name.** NTR's tag reads `E[no filings]` — it is one of the nine structurally dark names (AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU), a 40-F/6-K foreign private issuer outside the 3-C filing set. Three consequences, stated separately because they are different:

1. **The newest ledger episode carries zero treatment.** It cannot be an ADJACENT row, it contributes nothing to E4-2 in either arm, and it is invisible to the whole EDGAR layer. The ledger and the E4 population are not the same set and today is the first session where that costs something.
2. **`implied_return` §6(c) already names NTR** as one of two operating companies excluded by the filing set, under **DP-3C-f, which is still unruled.** The instrument that would say anything about NTR's valuation is switched off for NTR, on the session NTR became the record's only actionable directional. Recorded because it sharpens a cost-benefit the record has been deferring, not because it argues for extending the filing set.
3. Risk **REJECTED in every account**, and *not* on confidence: `Already holding NTR and ALLOW_POSITION_ADD is False`. Admission to the ledger is CHECK 5 clearance at the signal's own gate, never risk-engine approval, so the row is admitted correctly. This is the first admitted row rejected for a reason other than confidence.

### 1.2 ★★ IT IS ALSO A TEXTBOOK LATE ENTRY, AND H1's OWN LOCKED VERDICT SAYS SO

`[V]` NTR's five-session run and confidence ramp, from the log's own tags:

| | t−4 | t−3 | t−2 | t−1 | **today** |
|---|---|---|---|---|---|
| close | 68.29 | 69.40 | 70.50 | 73.12 | **74.50** |
| S1 prior confidence | 50 | 55 | 60 | 63 | 67 → **72** |

`H1[trail5d=+9.09%]`, `S1[dconf=+17]` — **the largest positive confidence change in the cohort by a factor of nearly two.** The price rose monotonically for five sessions and confidence rose monotonically with it; the BUY is issued on session five, at the top.

**This is the H1 lag signature, arriving on the favourable side.** H1's locked verdict (b) — lag real and stable, prompt remedy retired, implement feature-level in 3-B — was established on adverse moves. The record has never had a gate-clearing directional on which to observe the same lag in the other direction, and it has one now. **Nothing is read from it**: n = 1, the row is unresolved, and G1's disposition is untouched. It is written down because if `NTR-20260821` resolves NO it will be the third consecutive post-era NO and the question "was the entry late" will be asked then, when the answer is harder to reconstruct.

### 1.3 ★★ THE SECOND POST-DP-3C-o ROW RESOLVED, AND IT ALSO PAID NO

`[V]` **NVDA 2026-08-14, BUY, conf 72 — $225.40 → −4.7%. Scored NO.**

| era | rows | resolved +5d | hit |
|---|---|---|---|
| PRE-DP-3C-o | 6 | 6 | **5 = 83.3%** |
| POST-DP-3C-o | 5 | **2** | **0 = 0.0%** |

The 8/20 entry recorded the first post-era row resolving NO and said nothing could be read at n = 1. The second has arrived and gone the same way. **Nothing is read at n = 2 either** — the tab's own instruction holds: *"DO NOT POOL ACROSS THE ERA LINE."* The pooled ROW basis now reads 5/8 = 62.5% and **must not be quoted.** Episode basis 1/3 = 33.3%, unchanged, because both rows belong to the already-scored `NVDA-20260813` episode.

**Direction, per house practice: this continues to run AGAINST the phase looking good.** Two independent post-era resolutions, both negative, against a pre-era 83.3%. The mandatory era split was built to expose exactly this and it is now doing so on consecutive sessions. Three post-era rows remain pending — NVDA 8/17, NVDA 8/18, NTR 8/21.

---

## 2 · The valuation layer

### 2.1 ★★ THE `peRatio` `[?]` IS SETTLED, BY THE NATURAL EXPERIMENT THE RECORD ASKED FOR — AND THE PROBE WAS NEVER NEEDED

The 8/20 entry's item #9 read: *"Run `fundamental_probe.py` while the WMT event is fresh — a `peRatio` that moves on a day `eps` does not is the discriminator."* **The discriminator fired on its own, and `quote_dump.json` had already recorded it.**

`[V]` WMT, straight from the dated quote dumps:

| field | 8/18 | 8/20 | **8/21** | move 8/20→8/21 |
|---|---|---|---|---|
| `eps` | 2.73 | 2.73 | **2.73** | **0.00%** |
| `lastPrice` | 115.21 | 103.97 | **103.59** | −0.37% |
| `peRatio` | 40.45 | 40.237 | **36.555** | **−9.16%** |
| implied denominator (px/peRatio) | 2.848 | 2.5839 | **2.8338** | **+9.67%** |

**A trailing P/E cannot do this.** If `peRatio` were price/`eps` it would have moved −0.37%, exactly with the price. It moved −9.16% on a session when `eps` did not move at all, which means the *denominator* was revised — upward by 9.67% — the session after **WMT's own 8-K of 2026-08-20**.

**And the cohort rules out a re-fetch artifact** `[V]`. Backing the denominator out for every name with a positive implied earnings figure, 8/20 → 8/21: WMT **+9.67%**, NKE +3.35%, RTX +2.79%, JPM +1.43%, AAPL +1.15%, MSFT +0.97%, PWR −0.92%, SND −0.69%, NVDA −0.49%, GM +0.39%, FTI −0.98%, NTR −1.37%, AG −2.12%, PM −2.44%. **WMT is nearly three times the next mover and is the only name with an earnings event in the window.**

**The reading in §5 is confirmed on a live event: `eps` is a static last-fiscal-year figure and `peRatio` carries a forward, analyst-maintained denominator.** The `[?]` is **left standing and is the operator's to close**, because the marker's own stated resolution was Schwab's field reference for the `fundamental` block and that document still has not been read. Confirming a reading by experiment is not the same as reading the documentation, and the record should not quietly upgrade one to the other.

### 2.2 ★★ AND THE CONFIRMATION COMES WITH A WARNING ABOUT HOW §5 HAS BEEN READ

`[V]` WMT's own classification flipped on the revision:

| session | px/eps | peRatio | ratio | §5 verdict |
|---|---|---|---|---|
| 2026-08-20 | 38.08 | 40.24 | 1.057 | **forward dearer: earnings expected DOWN** |
| 2026-08-21 | 37.94 | 36.55 | **0.963** | **forward cheaper: earnings expected UP** |

The 'expected DOWN' set went `['DOW', 'GM', 'WMT']` → `['DOW', 'GM']`, on a **−0.4% price move**, purely because the forward denominator was revised.

**So a §5 row is not a statement about a company. It is a statement about how stale the two fields are relative to each other on the day they were captured**, and it can invert on any filer's own calendar. WMT sat in the 'expected DOWN' set for exactly one session — the session of its own 8-K, on which it fell 9.2% — and left it the next. Read as a property of WMT that is a category error; read as denominator freshness it is exactly right. The exhibit printed it as a flat per-name verdict, and now says so.

### 2.3 ★ SECTION 1's PRICE-SOURCE CLAIM WAS FALSE FOR SECTION 5, AND HAD BEEN SINCE SECTION 5 WAS BUILT

`[V]` §1 stated: *"px(quote) is shown as DRIFT ONLY. Every derived figure uses px(master), the record's Price at Signal, so there is exactly one price source."* §5 computes `trail = r["qpx"] / r["eps"]` — the **quote** price. Checkable on today's face: WMT px(master) 102.36 / eps 2.73 = 37.49, and §5 prints **37.94** = 103.5892 / 2.73. GM px(master) 86.69 / 3.27 = 26.51, §5 prints **26.82** = 87.70 / 3.27.

**The behaviour is right and the claim was wrong.** §5's whole point is comparing px/eps against Schwab's `peRatio`, and that field is struck on Schwab's own price — matching the basis is what makes the ratio mean anything. Using px(master) there would have introduced a spurious drift term into the very ratio the section exists to read. **Corrected in place**: §1 now scopes its claim to sections 1–4b and names §5 as a documented exception with its reason. Recorded as a finding rather than a silent edit because a blanket provenance claim that is false in one place is worse than no claim at all — it is exactly the sentence a reader uses to *stop* checking.

### 2.4 ★★ THE CORN GAP DID NOT CLOSE — IT MOVED TO A LAYER THE NEW ALARM CANNOT SEE

`[V]` `value_anchor` FINDINGS went **2 → 3**, and the new one is:

```
covered in the log but NOT joined to a cache file: ['CORN']
   Most likely cause: the periodic is filed under a trust or parent whose
   document name carries a different series ticker. Reported, never guessed.
```

**Its hypothesis is correct and can be named.** CORN is not degraded any more — its tag reads `E[8k=0; form4=0f; periodic=10-Q@2026-08-14; fin=1@2026-06-30]`, so DP-3C-j's budget fix and the 8/20 out-of-band warm both held. But the accession→ticker filename route resolves off the raw document name, and CORN is a series of **Teucrium Commodity Trust**: the cached document for accession `000143774926027963` is `tags20260630_10q.htm`, and the derived cache `fin_000143774926027963.json` is **346 bytes**. `tags` is not `corn`, so route 2 cannot resolve it and the two-route join correctly refuses to guess.

**Why this matters more than one missing row.** The 8/20 remedy — `fin=degraded` on a covered name is now a FAIL — fired correctly today and correctly said nothing, because **CORN's tag is present and healthy.** The gap has relocated from the EDGAR layer, where there is now an alarm, to the join layer, where there is not. Same name, same net effect on the valuation layer, different mechanism, and the new guard is blind to it by construction.

**It is also a filer-class problem, not a CORN problem.** GLD joins because SPDR Gold Trust files under its own name; CORN does not because Teucrium files a multi-series trust document. Any covered name whose filer names documents after the parent rather than the series will do the same. The remedy is a join route that reads the ticker from inside the document rather than from its filename, or an explicit series→ticker alias table — **not** a widened prefix match, which the tool's own docstring already warns produces `sndk` for SND.

### 2.5 ★ THE HEADLINE READ, AND WHAT IT STILL RESTS ON

`[V]` Join **16 verified, 0 unverified**; computed 14 of 16; GLD and USO NOT COMPUTED (missing diluted EPS, structural); PM's M/B suppressed on non-positive book equity of −8.58B with a balance-sheet residual of **2.82% of assets**, flagged for inspection as on every prior run.

`implied_return` §4: **eight of thirteen names require MORE THAN A DOUBLING of trailing ROE** at a 9% cost of equity — SND 14.98x, PWR 5.87x, RTX 2.77x, NVDA 2.60x, AAPL 2.43x, WMT 2.31x, GM 2.14x, FTI 2.07x. `[EDGAR] prefetch: 21/26 resolved to submissions` against **17/26 sections rendered** — the known and still-undocumented `--coverage` gap, now wrong against a fifth true value. The layer's only external verification remains Schwab eps 3.27 = GM's FY2025 10-K diluted EPS 3.27 against Morningstar's 3.28%, and **it still rests on one ticker.**

**No valuation is asserted and no price target is implied**, and nothing here touches the prompt or any endpoint (DP-V1).

---

## 3 · The instrument defect

### 3.1 ★★ A G1 ACCEPTANCE EXHIBIT HAS BEEN PRINTING A CONFIDENCE THAT EXISTS IN NO CHANNEL

`[V]` `h1_lag_trace_GM_3B.md` as shipped:

| date | exhibit (operative) | exhibit (raw) | tracker `Conf %` | log `confidence` | log `confidence_raw` | log `confidence_blend` |
|---|---|---|---|---|---|---|
| 2026-07-21 | **57%** | **57%** | 58 | — | — | — |
| 2026-08-17 | **56%** | 57% | 57 | 57 | 57 | 57 |
| 2026-08-20 | **56%** | 57% | 57 | 57 | 57 | 57 |

**GM carries `damp 0` on both August sessions** — `D[raw=57; op=57; trail=−2.89%; damp=0]` on 8/20 — so operative and raw *cannot* differ by construction. They differed anyway.

**Mechanism, and it is arithmetic** `[V]`. `conf_pct()` returned a bare `v * 100.0` on a tracker cell stored as a fraction, and both display paths printed `int(conf)`. IEEE-754 makes `0.57 * 100 == 56.99999999999999`, and `int()` truncates. Exactly three two-decimal fractions have this property — **0.29, 0.57 and 0.58** — and every confidence at those values rendered one point low. The `--raw-from-logs` variant escaped on post-deploy rows only because the override replaces the float with an exact integer parsed from the log; rows outside the log glob (2026-07-21) fell back and truncated in both files.

**Scope, stated precisely, because the two halves are different sizes:**

- **The displayed table was wrong.** Four values across two exhibits.
- **The lag scan and both correlations were never affected.** They are computed from the unrounded float, not the printed integer. Verified by regeneration: after the fix, all four exhibits return **byte-identical lag verdicts and correlations** — WMT operative lag 0 / +0.841, WMT raw lag 1 / +0.721, GM lag 0 / +0.694 in both channels. **No G1 reading moves.**

**Why it survived.** WMT never held a confidence of 0.29, 0.57 or 0.58 in the post-deploy window, so the primary tracer's exhibit is untouched and nobody had reason to look at the secondary's. And the tool's own degraded-cache block asserted, in the file, that *"the `Conf` and `Trail` columns — the ones the G1 table read is scored on — are unaffected, being a raw cell value and a Price-column computation respectively."* **`Conf` is not a raw cell value; it is a scaled one, and the scaling was the defect.** A tool that certifies its own column as exact is a tool nobody re-derives. The sentence is amended in place rather than deleted.

**One correction to the 8/20 entry follows, and it is in the record's favour.** §2.2 of that review recorded 8/20 as *"the first post-deploy session on which operative ≠ raw on a tracer."* That is **correct for WMT** — `D[raw=42; op=35; damp=7]` is real damping clamped at the floor. But the GM exhibits also differed that day, and had anyone read them the record would have logged a second, phantom instance. After the fix **GM's two exhibits are byte-identical again**, which is what damp 0 requires. The 8/20 finding stands; the near-miss beside it is recorded so it cannot be rediscovered as evidence.

### 3.2 ★★ AND THE SAME EXHIBIT'S TRAILING MOVE DISAGREES WITH THE RUN'S — ON GM, IN SIGN

`[V]` For 2026-08-21:

| name | `h1_lag_trace` Trail5d | the run's `H1[trail5d=]` / `D[trail=]` |
|---|---|---|
| WMT | **−11.21%** | −10.47% |
| GM | **−0.31%** | **+2.75%** |

**Two different measurements, neither labelled.** The exhibit walks back five **tracker rows** and prices off **Price at Signal** (a ~09:3x quote). The run walks back five **market sessions** and prices off **closes**. For GM the two disagree in sign, because GM's missing **2026-08-18** row moves the exhibit's t−5 anchor from 8/14 to 8/13.

**This reaches a gate.** `monitor_strip`'s G1 episode detector uses the *exhibit's* basis — `ws2_episodes()` walks `ser[i-5]["p0"]` over tracker rows — while importing **THETA from `risk_engine`**, which damps on the *other* basis. The threshold and the series it is applied to come from different definitions of "trailing five-session move". Today nothing turns on it: WMT is far past −5% on both, GM far short on both. It turns on it the first time a tracer sits near −5% and the two bases straddle it. **Both exhibits now state their basis on their face**, and the strip states both its basis and its channel.

### 3.3 ★ WHICH ALSO CORRECTS THE 8/18 ENTRY: GM's ONE-SESSION HOLE IS NOT INVISIBLE

The 8/18 entry recorded GM's single-session departure and concluded: *"the only durable evidence that 8/18 happened is GM's row count against the cohort count for that date, which no harness compares. It is written down here because that is the only place it will exist."*

**That is now falsified in two places** `[V]`:

1. **It is already in the master.** GM carries **66 rows** where every other covered name except CORN carries **67**. (CORN's 66 is its own 2026-06-02 gap, as are QQQ, SPY, VTI and XLU.)
2. **It has been silently corrupting the G1 exhibit for three sessions** — §3.2 above — and will keep doing so until 8/18 leaves the five-row window after **2026-08-25**.
3. **And it becomes permanent on the face of `band_price` on 2026-08-25.** Today GM reads n = 62 resolved +5d, the same as its peers, only because its missing row is not yet due. When the 8/18 cohort resolves, the full names go to 63 and **GM stays at 62, in §1 and §6, on every run thereafter.**

The 8/18 entry was right that no harness *compared* it. It was wrong that no artifact would *carry* it. Both are worth having straight, because the first is the argument for the membership check landed today and the second means the evidence was never actually going to be lost.

---

## 4 · The gates

### 4.1 ★ COHORT RESOLUTIONS, ALL THREE HORIZONS `[V]`

| horizon | cohort | n | accuracy | mean | sd(pop) | HOLD breaches |
|---|---|---|---|---|---|---|
| +5d | 2026-08-14 | 25 | 11/25 = **44.0%** | −0.90% | 4.85% | 13/24 (5 UP / 8 DOWN) |
| +10d | 2026-08-07 | 24 | 9/24 = 37.5% | +1.58% | 6.64% | 13/21 (7 UP / 6 DOWN) |
| +20d | 2026-07-24 | 24 | 7/24 = **29.2%** | +3.85% | **8.37%** | **17/23** (12 UP / 5 DOWN) |

+5d movers: **NTR +9.98%**, AG +7.66%, GLD +5.24% against CBRS −10.85%, WMT −10.05%, PWR −6.30%.
+10d movers: **NTR +16.03%**, AG +15.66%, FTI +12.86% against WMT −7.42%, CBRS −7.24%, RTX −5.04%.
+20d movers: AG +26.06%, MSFT +25.43%, GLD +13.22% against XLU −7.77%, AAPL −6.77%, WMT −4.96%.

**The +20d series has now printed 29.2%, 37.5%, 58.3%, 41.7% and 29.2% inside six weeks** — a 29-point range on the same instrument — at its **highest HOLD-breach count yet** (17 of 23, 12 of them upward) and the highest dispersion in the series. Same annotation as always, in both directions per the 8/19 rule: **the +20d read is measuring dispersion at a twenty-day horizon, not skill.** +5d fell 60.0% → 44.0% on the same mechanism at the other end.

**And NTR led both resolving cohorts** — the strongest +5d name and the strongest +10d name — on the session the model finally issued a BUY on it. §1.2.

### 4.2 ★ KEEP-70 — SUPPORTED AT 21/43 = 48.84%, AND THE READING IS UNCHANGED BECAUSE NOTHING RESOLVED

`[V]` Registry **47 → 49** (NVDA 66 and GLD 67 added today, both HIGH, both pending). **No near-miss BUY resolved at +5d this session** — the 2026-08-14 cohort contained none — so the row basis is **numerically identical to 8/20**.

| basis | reading | under the ruled `≤ 50.0%` rule |
|---|---|---|
| ROW | **21/43 = 48.84%** | SUPPORTED |
| EPISODE (DP-3C-m coalesced, opening row) | **10/18 = 55.6%** | NOT SUPPORTED |

The 8/20 entry noted the margin had narrowed for the first time in four readings and that *"one more YES without a matching NO puts it back on the boundary."* **That has not happened, and it has not been tested either** — today adds a reading with no information in it. **The basis remains UNRULED and the two continue to straddle.** Monitor strip agrees at 48.8%. At +10d the registry completed two: GLD 2026-08-07 **+6.2% YES**, QQQ 2026-08-07 −0.9% NO.

### 4.3 ★ H4 — FOURTH CONSECUTIVE FAILING READING, AND THE FIRST ONE THAT IS NOT A NEW MEASUREMENT

`[V]` HIGH-DQ near-miss +5d: 8/17 **61.1% PASS** → 8/18 55.0% FAIL → 8/19 54.5% FAIL → 8/20 56.5% FAIL → **8/21 13/23 = 56.5% FAIL**.

**Identical numerator and denominator to 8/20.** Registry HIGH total moved 27 → **29** on today's two additions, but resolved is unchanged at 23, so the rate could not move. MEDIUM unchanged at 8/20 = 40.0%. Overall HIGH **522/859 = 60.8%** ≥ MEDIUM **279/602 = 46.3%**; LOW 9/22 = 40.9%.

**H4 STAYS DEMOTED.** Recorded with the qualifier because a reading series that counts an unchanged reading as a fresh failure overstates its own evidence — the ninth entry in the reversal series carries **zero new resolutions**. The single 61.1% pass at n = 18 still stands alone against four failures, but only three of them are independent.

### 4.4 ★ G1 — TODAY IS NOT A THIRD EPISODE, AND THAT IS THE COALESCING RULE WORKING

`[V]` WMT reads `trail5d −10.47%`, `raw 38 → op 35, damp 8` — a material adverse move, and `signal_scan` says so. **It is the tail of the 2026-08-20 slide, not a new episode**: the trailing window has not recovered above −THETA since, and DP-3C-m's coalescing counts an episode from the first qualifying session of a run. The monitor strip agrees — **2 post-deploy episodes in 34 sessions (2 responded ≤2 sessions), last episode 2026-08-20** — and GM reads **0 post-deploy in 33 sessions**.

**G1's stated bar is met on both episodes; the pre-registered n = 4 is not. G1 STAYS INSUFFICIENT TEST CONDITIONS** and nothing is re-read at n = 2. Note also that WMT's operative confidence sits at **35, exactly the D1 FLOOR**, for the second consecutive session — the damping is clamped, and a clamped channel cannot fall further, which is worth stating before anyone reads a lag off it.

### 4.5 ★ E4-2 TIER DRIFT — 6 OF 15, AND THE MEMBERSHIP HELD FOR THE FIRST TIME IN FOUR SESSIONS

`[V]` Four consecutive readings of the frozen table:

| session | count | membership |
|---|---|---|
| 2026-08-18 | 4 of 15 | GM, WMT, AAPL, FTI |
| 2026-08-19 | 4 of 15 | GM, WMT, NKE, FTI |
| 2026-08-20 | 6 of 15 | GM, WMT, NKE, AAPL, NVDA, FTI |
| **2026-08-21** | **6 of 15** | **GM, WMT, NKE, AAPL, NVDA, FTI — unchanged** |

**The first session with no turnover**, which is the reason v7.0 §14 asks for membership rather than the count: an unchanged count on 8/18→8/19 concealed a full swap, and an unchanged count today conceals nothing. Reporting the same quantity in both cases is what makes the difference visible. The boundary flagged at freeze time (NVDA 0.003pp below DOW) **still has not flipped** — NVDA 3.489% vs DOW 3.861%. **The table is NOT re-cut.**

### 4.6 ★ E4 COVERAGE — THE STRUCTURAL FINDING REPLICATES ON A SECOND SESSION

`[V]` From today's per-ticker tags, statements depth across the frozen covered-15:

| statements lines | names |
|---|---|
| 11 | AAPL, MSFT, NVDA, SND |
| 10 | FTI, PM, PWR, *(SPCX)* |
| 9 | GM, NKE, RTX, WMT |
| 7 | DOW |
| 6 | JPM, *(USO)* |
| **3** | **GLD** |
| **1** | **CORN** |

And on the event axis, **exactly two of the fifteen produced no 8-K and no Form 4 today: CORN and GLD** — the same two as 8/20, on a second independent session. **ADJACENT-eligible coverage = 13/24 = 54.2%** confirmed, beside the pre-registered 15/24 and the practical 15/24 (all fifteen generated today). The uncomfortable corollary also replicates: **USO carries `8k=1@2026-07-29` and `fin=6`, and SPCX `8k=2@2026-08-14` and `fin=10`** — both admitted after the freeze, both carrying more treatment than two names inside the frozen population. **The table is NOT re-cut**, and the third denominator plus the LOW-tier imbalance are reported instead, as ruled.

---

## 5 · DP-3C-j's first live reading, and the rest

### 5.1 ★★ THE NEW EDGAR BUDGET RETURNED A NUMBER, AND IT IS 2.5× THE ONE STATED IN ADVANCE

`[V]` verbatim: `[EDGAR] budget: 17.5s of EDGAR fetch/extract used of 120s (15% of ceiling)`.

The DP-3C-j memo pre-registered the expectation in exactly these terms: *"against ~7s of real EDGAR work a 120s EDGAR-time ceiling should never trip — and if it does, that is now a real signal."*

**The disposition is right and the magnitude is wrong.** The ceiling did not trip, is nowhere near tripping, and 15% of budget on a full 17-name run is a comfortable margin. But the estimate was **7s and the measurement is 17.5s**. Recorded for two reasons: the memo stated the figure in advance *so that it could be checked*, and checking it is the whole value of stating it; and a 2.5× error in an in-advance estimate of a quantity now bounded by a ceiling is worth knowing before anyone sets the next ceiling from the same intuition. **No change is recommended** — one observation, and 120s stands.

### 5.2 ★ THE DEGRADED-NAME FAIL AND THE ERA ALARM BOTH DID THE RIGHT THING BY SAYING NOTHING

`[V]` `[OK] no covered name degraded (fin=degraded absent)` — the alarm landed 8/20 is armed and silent, and CORN, the name that provoked it, is healthy at `fin=1@2026-06-30` with `periodic=10-Q@2026-08-14`. `[OK] era unchanged since 2026-08-20 (A-S1D1-B1-E1, 26 rows in signals_2026-08-20.log)` — the direction rule's second live run, no false FAIL on a correct session. Recorded because a silent guard reads as a guard doing nothing, and that is how a guard gets removed. Note in passing that CORN being un-degraded is exactly why §2.4's join failure was *reachable* today: a degraded name never gets as far as the join.

### 5.3 ★ `confidence_blend` SEMANTICS — n GOES 4 → 7, ALL AGREEING

`[V]` `signal_scan` reports rows where blend ≠ blend_op, **n = 3** (NTR, NVDA, GLD): tracks `B.blend` 0/3, tracks `B.blend_op` **3/3**. Cumulative across all observations: **7/7 post-damping.** **The `[?]` is closeable** and has been carried as such since 8/20.

### 5.4 ★ AND NTR IS A GATE-FLIP — THE THIRD IN THE RECORD, THE FIRST NOT ON NVDA

`[V]` `B[base=72; blend=67; blend_op=67]`. **The blend would have rejected the only gate-clearing directional of the session** (67 < 70). The gate-flip ledger has carried two rows since 2026-08-10 (NVDA 8/03 68→70 YES, NVDA 8/10 70→68 NO, net +0); this is the third, the first in eleven sessions, and the first on a name other than NVDA. It resolves +5d on **2026-08-28**.

**WS1 / G2 is DESCOPED and nothing is read from this.** It is recorded because the descope was taken on the grounds that a general-form blend could not be evaluated on the evidence available, and the evidence base has just acquired its first non-NVDA observation. That is a fact about the descope's reopening conditions (T-G2-a/b/c), not an argument to reopen it.

### 5.5 ★ `Sheet1` IS STILL IN THE MASTER — SIXTEEN SESSIONS

Tabs read `Dashboard / Signals / Cohort Analysis / Sheet1 / How to Use`. Unchanged since 2026-07-30.

### 5.6 Operational

- **Run started 09:31:03 CST**, first signal 09:31:36, last 09:37:20 — canonical, and the **third on-time run in a row**.
- **26 tickers, 18 held + 8 scouting.** `Prior-signal state loaded: 26` against `ANALYZING 26`.
- **DQ 19 HIGH / 7 MEDIUM / 0 LOW.** Cohort profile mean 55.8, median 57.0, sd(pop) 11.95, min 30 (CBRS), max 72 (FTI, NTR); reproduces `signal_scan` exactly `[V]`.
- **3 BUYs**: NTR 72 (gate-clearing, §1.1), NVDA 66 and GLD 67 (both rejected on confidence, both near-misses).
- **Largest adverse move in the cohort is not a tracer**: CBRS −20.92%, `raw 30 → op 30, damp 15` — the damping is inert because raw already sits below the D1 floor of 35. PWR −9.56% (damp 7) and SPCX −8.99% (damp 6) likewise sit outside the pre-registered WS2 universe. **Context only; widening the episode universe is an amendment, not a reading.**
- **`band_price` integrity block:** price-derived Return+5d reproduces the cached column on **1,485 of 1,485** rows, max residual 1.388e-17, zero mismatches; BAND=0.03 confirmed against the workbook's own column on **1,432** HOLD rows, zero disagreements.
- **`band_price` §4:** covered-15 pooled breach 49.30% against a row-weighted model expectation of 48.25% — gap +1.05pt, z = +0.641, two-sided p = 0.521. **NOT distinguishable from a zero-skill dispersion baseline** at n = 929. Unchanged in substance from 8/20.
- **Two names the one-parameter band model does not fit:** NVDA +8.32pt and SND +5.90pt, both breaching more often than their own medians imply. Reporting trigger only; nothing is ruled on it.
- The two 2026-06-01 ghost rows (AG, FTI — price-only backfills) are unchanged and remain **the only incompleteness in 1,614 rows.**

---

## 6 · What was landed this session

Four fixes, all verified against the real logs before this review was written. Full memo: **`H1LagTrace_Truncation_Defect_2026-08-21.md`**.

| # | file | change | verification |
|---|---|---|---|
| 1 | `h1_lag_trace.py` | `conf_pct()` rounds at the source; both display paths use `round()` not `int()`; the degraded-block and `[raw-from-logs]` claims narrowed to what they support; **TRAIL BASIS** disclosure added to the exhibit | Regenerated all four exhibits: **4 corrected values, all on GM (7/21 57→58, 8/17 56→57, 8/20 56→57 operative; 7/21 57→58 raw)**, WMT unchanged, **all four lag verdicts and all correlations byte-identical** |
| 2 | `signal_scan.py` | `EXPECTED_N = 24` **retired**; replaced by a cohort-membership set-difference against the prior session's log (OK / FAIL / NOCHK), count printed and never asserted | `--selftest` **30/30** (13 new, 3 negatives incl. an equal-size swap); `edgar_parser_audit` **PASSED at exit 0**; retro-run against the real logs emits `REMOVED: GM` on 8/18 and `ADDED: GM` on 8/19 |
| 3 | `monitor_strip.py` | WS2/G1 rows and the episode ledger now state **which channel scored the lag** (operative, post-damping) and **which trailing-move basis** they use | Regenerated; every published figure reproduces (2 episodes / 34 sessions, H4 57%, KEEP-70 48.8%, registry 49, band splits) |
| 4 | `implied_return.py` | §1's price-source claim scoped and §5 named as a documented exception; §5 carries the 2026-08-21 natural experiment and the denominator-freshness warning | Compiles; new lines are literal-only `out()` emissions with no interpolation. **Text-only change, not yet exercised on a live cache run** — the operator's next `value.bat` is its first |

**Findings on the 8/21 run fall 2 → 1.** The only remaining one is `[FAIL] D.op == B.blend_op 23/26` (NTR 72/67, NVDA 66/62, GLD 67/58), which is documented noise on a DESCOPED channel and is still owed a rephrase as informational.

**`retired_criteria_audit` moves 58 → 60 flagged lines**, both additions being comments in `monitor_strip.py` and `h1_lag_trace.py` that name G1 accurately as a live gate. G1 is not retired, so a flagged mention is the correct behaviour, and no wording clears it without misstating its status.

---

## 7 · Findings, ranked

| # | finding | class | action |
|---|---|---|---|
| 1 | **First gate-clearing directional of the E4 era — NTR BUY 72 — and it is an UNCOVERED name** (`E[no filings]`). Ledger 10→11 rows, 3→4 episodes | endpoint + E4 scope | None. Report that the newest episode carries zero treatment at every E4 read. DP-3C-f's cost-benefit has moved again |
| 2 | **Second post-DP-3C-o row resolved NO** (NVDA 8/14, −4.7%). Post-era 0/2 against pre-era 5/6 | endpoint, runs against the phase | None. **Do not pool** — 5/8 is not a figure. DP-3C-l amendment still owed |
| 3 | **`h1_lag_trace` printed a confidence present in no channel** — `int()` truncation of 0.29/0.57/0.58, four wrong values on GM's exhibits | my defect class / instrument | **FIXED and verified.** No G1 reading moves. 8/20 §2.2 stands; the phantom GM instance is recorded so it cannot be rediscovered as evidence |
| 4 | **The `peRatio` `[?]` is empirically settled** — WMT's denominator revised +9.67% on a −0.4% price move while `eps` held, the session after its own 8-K | open question | Evidence landed in the exhibit. **The `[?]` is the operator's to close**; its stated resolution was Schwab's field reference, still unread |
| 4b | **§5's classification is denominator freshness, not a company property** — WMT flipped 'expected DOWN' → 'expected UP' in one session | how the exhibit is read | Landed in the exhibit. Never quote a §5 row as a view on a business |
| 5 | **The CORN gap moved from the EDGAR layer to the join layer**, where the new `fin=degraded` FAIL is blind to it. `tags20260630_10q.htm` cannot resolve to CORN by filename | recurring, filer-class, no alarm | Read the ticker from inside the document, or add an explicit series→ticker alias. **Do not widen prefix matching** — it yields `sndk` for SND |
| 6 | **The G1 exhibit's trailing move and the run's disagree in SIGN on GM** (−0.31% vs +2.75%); the episode detector uses one basis and imports THETA from the engine that uses the other | measurement apparatus, attached to a gate | Basis now stated on both exhibits and the strip. Decide which basis G1 scores on **before** n = 4 |
| 6b | **GM's 8/18 hole is not invisible** — it is in the master's row count today and lands permanently in `band_price` on **2026-08-25** | corrects the 8/18 entry | None. Expect GM at n = 62 against peers at 63 from 8/25 and do not read it as a defect |
| 7 | **+20d printed 29.2%** — fifth reading, 29-point range in six weeks, highest breach count and dispersion in the series | endpoint | None. Annotate in both directions. It measures dispersion, not skill |
| 8 | **The membership check landed**, retiring `EXPECTED_N = 24` after six wrong values; retro-detects GM's 8/18 departure and 8/19 re-add | change-order item, ten sessions late | Done. Removes one standing noise FAIL |
| 9 | **DP-3C-j's budget measured 17.5s against an in-advance estimate of ~7s** | pre-registered expectation, 2.5× low | None. 120s stands. Note the estimate class before setting the next ceiling |
| 10 | **H4's fourth failing reading contains no new resolutions** (13/23, identical to 8/20) | endpoint, reading hygiene | None. Count independent readings, not sessions |
| 11 | **NTR is a gate-flip**, the third in the record and the first not on NVDA; blend 67 would have rejected it | WS1 DESCOPED, context only | None. Resolves 8/28. Relevant to T-G2-a/b/c, not an argument to reopen |
| 12 | **`confidence_blend` confirmed at n = 7** post-damping | `[?]` closeable | Close it |
| 13 | **`implied_return` §1's price-source claim was false for §5** | provenance claim | **FIXED in place.** A false blanket claim is worse than none |
| 14 | **`Sheet1` still in the master**, 16 sessions | integrity, G4 | Delete once |
| 15 | **`--coverage` gap wrong against a fifth true value** (21/26 vs 17/26) | known, undocumented | Document or fix |

---

## 8 · Standing

T1 (advisory-only, pre-execution, mandatory) · T3. **2026-08-21 is E4 cohort 6**, era `A-S1D1-B1-E1`, treatment delivered on 17 of 26 rows with **no degraded name**. **E4 clock: cohort 6 of ~10.** Practical coverage **15/24**; **ADJACENT-eligible coverage 13/24 = 54.2%** — CORN and GLD produce no 8-K and no Form 4 and cannot enter the ADJACENT arm, confirmed on a second session. **CORN is treated at the EDGAR layer and unjoinable at the valuation layer.** **KEEP 70% — SUPPORTED at 21/43 = 48.84% on the row basis, NOT SUPPORTED at 10/18 = 55.6% on the episode basis; the basis is UNRULED**, and today's reading carries no new resolutions. H4 **STAYS DEMOTED** (56.5%, fourth consecutive failing reading, third independent one). **Gate-cleared ledger 11 rows / 4 episodes, no disposition read at any n; post-era arm 0/2**, three rows pending. ±3% HOLD band unchanged and **NOT re-baselined**. Frozen E4-2 tier table **NOT re-cut**; 6 of 15 would re-tier, membership unchanged. Blend (WS1) **DESCOPED** — one new gate-flip pending. Q4-2 **parked**. Peer-relative M/B–ROE form DESCOPED, P/E form PARKED. DP-3C-f **unruled**, and its cost-benefit moved again today. Nothing in the valuation layer touches the prompt (DP-V1). **G1 INSUFFICIENT TEST CONDITIONS — 2 of 4 post-deploy episodes, both responding ≤2 sessions, the bar NOT lowered and the n NOT met; today is the coalesced tail of episode 2, not a third.** E2 is no longer trivially satisfied, and the channel it is scored on is now stated on the instrument.

*Advisory-only · no orders · not financial advice.*
