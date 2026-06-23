# Claude Equity Bot — Analyst Notes

**Project:** claude-equity-bot
**Phase:** 2 (read-only dry run)
**Window:** 2026-05-18 to \~2026-06-10
**Maintainer:** Robert

This file documents structural findings, calibration evidence, and
decisions during Phase 2. Entries are organized into two sections:
**Reference** (glossary, definitions — stable) and **Findings**
(dated entries — chronological).

\---

# Reference

## Glossary — Metric Definitions

Locked in 2026-05-28 to prevent terminology drift over the remaining
\~7 days of Phase 2.

### "Hit" — Was Claude Right?

A "hit" means Claude's signal was correct on a given row. The formula
in the tracker's column N evaluates each signal type differently:

|Signal|"Right" Means|Tracker Formula|
|-|-|-|
|HOLD|Stock stayed within ±3% over 5 days|`IF(ABS(K\_) < 0.03, "YES", "NO")`|
|BUY|Stock went up (positive return)|`IF(K\_ > 0, "YES", "NO")`|
|SELL|Stock went down (negative return)|`IF(K\_ < 0, "YES", "NO")`|

A hit count of 9 means Claude's call was correct on 9 signals.
A hit rate of 37.5% means 9 out of 24 evaluated signals were correct.

### Why "Hit" Instead of "Accuracy"

"Accuracy" implies a single binary outcome, but Claude's "rightness"
means different things across signal types. A HOLD is right when
*nothing happens*. A BUY is right when *the predicted direction
happens*. The hit framework collapses those into one comparable
yes/no per row, enabling cross-signal-type aggregation.

### The ±3% HOLD Threshold

A HOLD is correct if the stock moves less than 3% in either direction
over 5 days. This threshold is a design choice, not a universal truth:

* Tighter (2%) → HOLD hit rates drop
* Looser (5%) → HOLD hit rates rise

Example boundary cases from the May 19 cohort:

* JPM moved +0.02% → YES (well within threshold)
* MSFT moved -2.53% → YES (within threshold)
* NTR moved -3.16% → NO (just outside, by 16 bps)
* CBRS moved -15.5% → NO (decisively outside)

**Phase 2 decision:** Do not adjust this threshold mid-test. Moving
the goalposts would invalidate the data. Revisit in Phase 3 as a
calibration question if needed.

### Hit Rate — Denominator Rules

```
Hit Rate = (Count of YES) / (Count of YES + Count of NO)
```

* The denominator counts only signals where +5d price has been entered
* Blank +5d rows do NOT appear in the denominator
* This is why Cohort Analysis tab shows 0% for cohorts before their
+5d completion date

### Cohort

A "cohort" = all signals from one signal date (e.g., the May 19
cohort = the 24 signals produced by the bot on 2026-05-19). Each
cohort completes its +5d evaluation exactly 5 trading days later.

### Near-Miss

A "near-miss" = a BUY signal at 60-69% confidence, rejected by the
70% risk-engine threshold. These are tracked as their own cohort in
the Near-Miss BUYs tab because they directly test threshold
calibration.

### Pattern Holds? (Cohort Analysis tab)

The Pattern Holds? cell in the Cohort Analysis tab evaluates ONE
specific question: Is the 50-59% confidence band the highest hit
rate band for this cohort? Formula:

```
=IF(AND(50-59% > 40-49%, 50-59% > 60-69%), "✓ YES", "NO")
```

It does NOT check whether the 40-49% band is the lowest. That's a
separate, secondary claim that may or may not hold independently.

### Quick Reference Table

|Term|Definition|
|-|-|
|Hit|One signal where Claude was right|
|Miss|One signal where Claude was wrong|
|Hit count|Number of YES rows|
|Hit rate|Hit count / (Hit count + Miss count)|
|Cohort|All signals from one signal date|
|Near-miss|BUY signal 60-69% conf, rejected by 70% threshold|
|Pattern Holds?|"Is 50-59% the highest hit-rate band for this cohort?"|
|+5d / +10d / +20d|5, 10, 20 trading-day evaluation windows|
|Was Claude Right?|The YES/NO column in the tracker|

\---

## Structural Gap Taxonomy

Locked in 2026-05-26. The four chronic-LOW tickers represent three
distinct gap types, each requiring a different Phase 3 response.

|Type|Definition|Tickers|Phase 3 Fix|
|-|-|-|-|
|**Type 1: Asset-class mismatch**|Pipeline built for equities; ticker is a commodity ETF. News flows around the underlying, not to the ticker.|CORN, GLD|`commodity\_context.py` module|
|**Type 2: Driver context gap**|Right data source, but dominant price driver is an exogenous commodity not in news feed.|AG (silver)|`commodity\_backed\_equity\_context.py`|
|**Type 3: News density gap**|Right source, insufficient ticker coverage (e.g., recent IPO).|CBRS|Time only — or exclude from auto-analysis|

**Key insight:** Three of four chronic-LOW tickers share the same root
cause — pipeline treats every ticker as an equity, but commodity ETFs
and commodity-backed equities have different dominant price drivers.

### Phase 3 Priority Order

1. `commodity\_context.py` — fixes CORN + GLD + future commodity ETFs
2. `commodity\_backed\_equity\_context.py` — fixes AG + future miners
3. CBRS exclusion config change (5 minutes)

\---

# Findings (Chronological)

## 2026-05-26 — Structural Data Gap: CORN (Commodity ETF Class)

**Phase:** 2 (read-only dry run), Day 5 of \~15
**Severity:** Medium — does not block Phase 2; deferred decision for Phase 3
**Status:** Documented, no action taken in Phase 2 to preserve test integrity

### Finding

Claude has consistently flagged CORN with LOW data quality across days
1, 3, and 5+, with reasoning that repeatedly cites:

> "Available news is tangentially related to commodities broadly rather
> than corn fundamentals specifically."

This is **not a bot defect** — it is correct epistemic behavior. The
bot is accurately reporting a real gap in input data.

### Root Cause

Finnhub's `company\_news` endpoint returns articles tagged with the
ticker symbol. For equity tickers (e.g., NVDA, AAPL) this is rich and
relevant. For commodity ETFs like CORN, the actual price drivers —
USDA WASDE reports, Corn Belt weather, ethanol demand, ag exports,
futures roll dynamics — generate news that is tagged under
"agriculture," "commodities," "USDA," or "corn futures," rarely under
the ticker CORN itself.

**Classification:** Asset-class data-routing mismatch. The pipeline
is built for equity tickers; CORN is a commodity ETF.

### Evidence (Days 1-5)

|Day|Date|Data Quality|Reasoning Pattern|
|-|-|-|-|
|1|2026-05-18|LOW|Thin news, low volume, no catalysts|
|2|2026-05-19|n/a|Consolidated out|
|3|2026-05-20|LOW|Tangential commodity news, no corn-specific drivers|
|4|2026-05-21|LOW|Same pattern|
|5|2026-05-22|LOW|Same pattern|

### Why Not Fix in Phase 2

1. Mid-test pipeline changes would contaminate the evaluation dataset
2. The bot's current behavior is working as designed — LOW data quality
correctly triggers auto-rejection of any non-HOLD signal via
`MIN\_DATA\_QUALITY = "MEDIUM"`. The risk engine is doing its job.
3. The persistent low-confidence HOLD output is the *correct* output
for a ticker the bot cannot confidently analyze.

### Deferred Decision (June 10 Review)

Three paths to evaluate against \~15 days of CORN data:

* **Path A — Exclude CORN from auto-analysis.** Move to manual monthly
review around WASDE release dates. Lowest effort.
* **Path B — Build `commodity\_context.py` module in Phase 3.** Free
data sources (USDA WASDE schedule + NASS QuickStats API + yfinance
ZC=F + NOAA Corn Belt outlook during growing season). Adds
\~$0.06/month in Claude tokens. \~3 hours build. Module would also
serve GLD and any future commodity ETFs.
* **Path C — Keep current behavior.** Accept that LOW data quality
is honest signal and the auto-rejection is the correct outcome.

### Rejected Approaches (and Why)

|Approach|Reason Rejected|
|-|-|
|Barchart CORN news page|Public page requires scraping (ToS risk); their `getNews` API is paid (Barchart OnDemand).|
|WeatherWealth subscription|Paid (\~$25-50/mo). Violates the "no added subscription cost" constraint.|
|Increase Finnhub `NEWS\_LIMIT` for CORN|Doesn't address relevance — more tangential headlines ≠ better signal.|
|Add commodity risk-mgmt rules (stop-loss, calendar spreads)|Belongs in Phase 4 execution, not Phase 2 analysis. Stop-loss already in risk engine; calendar spreads not applicable to ETF holdings.|

### Next Touch Points

* June 10, 2026 — Phase 2 evaluation; decide Path A/B/C
* Next WASDE release: June 11, 2026 (one day after eval — useful as
natural catalyst test for whichever path is chosen)

\---

## 2026-05-26 — Structural Gap Taxonomy: Chronic-LOW Ticker Class

Extending the CORN analysis above, applied same diagnostic lens to
AG, GLD, CBRS. Full taxonomy now lives in the Reference section above.

Quick summary:

|Ticker|Gap Type|Phase 3 Action|
|-|-|-|
|CORN|Asset-class mismatch|`commodity\_context.py`|
|GLD|Asset-class mismatch|Same module as CORN|
|AG|Driver context gap (silver spot missing)|`commodity\_backed\_equity\_context.py`|
|CBRS|News density gap (recent IPO)|Exclude until Q4 2026|

See CORN entry above for full evidence and rejected approaches.

\---

## 2026-05-26 — May 18 Cohort Day-5 Outcomes: First Calibration Signal

**Phase:** 2 (read-only dry run), Day 6 of \~15
**Status:** First completed +5d cohort, 30 data points
**Significance:** First evidence that confidence calibration may be working

### Headline Result

Hit rate by confidence band on the May 18 HOLD cohort:

|Confidence Band|Sample|Hit Rate|Avg Abs Return|
|-|-|-|-|
|60-69%|5|40%|6.42%|
|**50-59%**|**17**|**59%**|**3.48%**|
|40-49%|8|25%|7.17%|

The 40-49% band (low conviction) correctly fails more often AND
correlates with larger actual moves — exactly what an honestly
calibrated "I don't know" signal should look like.

The 50-59% band (moderate conviction) has both the highest hit rate
AND the lowest average move magnitude — strong evidence that when
Claude says "this isn't moving," moderate confidence is meaningful.

### Why This Matters

This is the **first quantitative evidence in Phase 2** that confidence
numbers carry signal, not noise. If it holds across the next 2-3
cohorts (5/19, 5/20, 5/21 completing 5/27-5/29), we have a foundation
for advancing to Phase 3.

### Caveats — Don't Overweight This Result

1. **All 30 signals were HOLD.** This measures HOLD calibration only;
says nothing yet about BUY or SELL signal accuracy.
2. **60-69% band is n=5.** WMT (held twice in tracker due to pre-dedup)
and PM dragged that bucket down. Could easily revert when sample grows.
3. **One trading week, one cohort.** Statistical significance requires
at least 3-4 completed cohorts.

### LOW Data Quality Outperformed MEDIUM (Confounded Finding)

LOW: 75% hit rate (n=4). MEDIUM: 42% (n=26).

This is **not** evidence that LOW signals are more trustworthy. The
LOW bucket is biased toward sleepy tickers (CORN, SND) that stay
range-bound by structural inactivity rather than by Claude correctly
predicting flatness. Don't trust LOW signals more on the basis of
this finding.

### Notable Misses

|Ticker|Conf|Return|Notes|
|-|-|-|-|
|CBRS|42%|-18.6%|Confirms chronic-LOW structural-gap diagnosis|
|WMT (x2)|62%|-11.1%|Highest-conf miss in dataset|
|GM (x2)|42-45%|+9.1%|Low conf HOLD that arguably should have been BUY|
|DOW (x2)|48-52%|-8.6%|Confirms chronic-low ticker pattern|
|AIQ|55%|+7.4%|Low-vol breakout — missed catalyst|

### Notable Hits

|Ticker|Conf|Return|Notes|
|-|-|-|-|
|GLD|48%|-1.1%|Scout signal|
|SPY|48%|+1.6%|Scout signal|
|MSFT (x2)|52%|-1.7%|Mega-cap noise band|
|RTX|52%|+1.9%|Mega-cap noise band|

Pattern: best hits are large, liquid index/mega-cap names where
±2% over 5 days is normal noise. Claude correctly identifies the
"no-signal regime" for liquid tickers.

### Decision Implications for June 10 Review

1. If 50-59% calibration holds across 5/19-5/21 cohorts → advance Phase 3
2. If 60-69% band continues underperforming with more data → consider
the BUY threshold of 70% may be correctly calibrated to filter
"tempting but not quite there" signals
3. The chronic-LOW ticker decisions (CORN/GLD/AG/CBRS) are now
reinforced by data — CBRS being the worst miss is consistent
with the gap diagnosis

\---

## 2026-05-27 — Day 7 Run: Two Structural-Gap Confirmations

**Phase:** 2 (read-only dry run), Day 7 of \~15
**Status:** Two diagnoses validated by data within 24 hours

### Finding 1: CBRS Reverted to LOW Data Quality

Day 6 produced the first zero-LOW day in Phase 2 (HIGH at 37.5%).
Day 7 reverted to 1 LOW signal — and it was CBRS, exactly the ticker
we diagnosed as a Type 3 structural gap (news density / recent IPO).

**Why this matters:** Day 6's apparent improvement was a news-cycle
artifact (Iran-deal headlines providing macro anchors), not a
structural shift. CBRS will continue cycling between LOW and MEDIUM
regardless of news flow because the underlying issue is ticker-level
coverage thinness, not transient news drought.

**Implication for June 10:** CBRS Path A (exclude from auto-analysis
until Q4 2026) remains the right call. Path B is not available
because no data pipeline change fixes a coverage problem.

### Finding 2: NVDA Triple Near-Miss BUY Pattern

Day 7 produced the THIRD NVDA near-miss BUY in 9 days. Verified
against the tracker:

|Date|Ticker|Conf|Price|Tracking +5d|
|-|-|-|-|-|
|2026-05-19|NVDA|62%|$220.58|2026-05-27|
|2026-05-22|NVDA|62%|$216.77|2026-06-02|
|2026-05-27|NVDA|63%|$209.84|2026-06-03|

**Why this matters:** Three near-misses on the same ticker, at
descending prices, with consistent 62-63% conviction across 8 trading
days. This is a sustained directional view, not three independent
coin flips. Two competing interpretations:

* **Bullish read:** bot is right; entry keeps improving (averaging-down
logic). Each rejection at 70% is "protective" because the next day
offers a better price.
* **Bearish read:** bot is wrong; conviction without learning from
adverse price action is a calibration failure.

The three +5d outcomes will discriminate cleanly between these. This
is the single most informative natural experiment in Phase 2.

**Notable detail:** Today's NVDA reasoning explicitly flagged
"below-average volume on a down day could signal fading momentum
rather than healthy consolidation" — meaning the bot is aware of the
bearish interpretation and still produced a BUY. This is a cleaner
conviction signal than a BUY with no acknowledged risk.

Also new in the cohort:

* 2026-05-21: SCHD 68% BUY at $32.11 (Roth IRA scout signal). +5d due 5/29
* 2026-05-26: VTI 68% BUY at $370.15. +5d due 6/2

Cohort total: 5 near-miss BUYs, +5d outcomes complete by 6/3.

### Day 7 Headline Stats

|Metric|Day 6|Day 7|Δ|
|-|-|-|-|
|Avg confidence|52.7%|52.8%|Flat|
|HIGH data quality|9|8|-1|
|LOW data quality|0|1 (CBRS)|+1|
|Near-miss BUY|VTI 68%|NVDA 63%|New data point|
|Cost|$0.2245|$0.2274|+1.3%|

### Decision Implications

1. CBRS structural-gap diagnosis is now data-confirmed → lock Path A
2. NVDA paired near-miss is the strongest BUY-threshold evidence so
far → ensure all three +5d outcomes are tracked in their own block
3. Phase 2 trajectory remains on schedule for 6/10 evaluation

\---

## 2026-05-27 — May 19 Cohort Day-5 Outcomes: Mixed Calibration Signal

**Phase:** 2 (read-only dry run), Day 8 of \~15
**Status:** Second completed +5d cohort, 24 data points
**Significance:** Primary calibration pattern replicated; secondary did NOT

### Headline Result

Hit rate by confidence band on the May 19 HOLD cohort:

|Confidence Band|Sample|Hit Rate|Avg Abs Return|
|-|-|-|-|
|60-69%|7|14% (1/7)|5.25%|
|**50-59%**|**10**|**50% (5/10)**|**4.90%**|
|40-49%|7|43% (3/7)|5.74%|

**Pattern Holds (50-59% is the highest band): ✓ YES**

This confirms the central calibration claim — when Claude is moderately
confident, it is most accurate. 50% is still the highest hit rate of
the three bands, even though the margin shrank from 59% on May 18.

### What Did NOT Replicate

The *secondary* finding from May 18 — "40-49% band is the least
accurate" — did NOT hold. May 19's 40-49% band beat the 60-69% band
43% to 14%. Two interpretations:

1. **Sample noise (n=7 each).** The 60-69% bucket got hit hard by
AAPL (+4.7%), FTI (-7.5%), WMT (-11.6%), NTR (-3.2%), and NVDA
(-3.6%). Five HOLDs that all moved 3%+, plus the NVDA BUY that
lost ground. Brutal lineup.
2. **Real signal.** 60-69% confidence may be overconfident; 50-59%
may be where genuine equilibrium lives. The 40-49% band may
benefit from being applied to sleepy tickers.

Either way, the simple v1 framing — "low conviction = worst,
moderate = best, high = better" — is **less clean than after one
cohort.** Wait for Cohort 3 (May 20, due 5/28) before drawing real
conclusions about the secondary pattern.

### Cumulative Calibration Status

|Cohort|Sample|40-49%|50-59%|60-69%|Pattern Holds?|
|-|-|-|-|-|-|
|2026-05-18|30|25% (2/8)|59% (10/17)|40% (2/5)|✓ YES|
|2026-05-19|24|43% (3/7)|50% (5/10)|14% (1/7)|✓ YES|
|**Combined**|**54**|**33% (5/15)**|**56% (15/27)**|**25% (3/12)**|**✓ YES**|

**2 of 2 cohorts confirm the primary pattern.** Across 54 evaluated
signals, the 50-59% band still leads decisively. Q1 of the
Phase 2 → Phase 3 worksheet is trending toward CALIBRATED but
requires one more cohort to lock in.

### Notable Misses on May 19

|Ticker|Conf|Move|Notes|
|-|-|-|-|
|**GM +18.2%**|52% HOLD|Biggest miss of cohort|Second cohort in a row with GM running away upward|
|CBRS -15.5%|42% HOLD|Already on chronic-LOW list|Reinforces Type 3 structural gap|
|WMT -11.6%|62% HOLD with HIGH DQ|High-conf miss again|WMT is now chronic high-confidence miss across both cohorts|
|AIQ +8.9%|52% HOLD|Tech rally caught HOLD signal|AI thematic momentum signal missed|

### Diagnostic Watchlist — WMT and GM

**WMT and GM are emerging as the two most diagnostic tickers in the
portfolio.** WMT keeps producing high-confidence HOLD calls and then
dropping double-digit. GM keeps producing low-confidence HOLD calls
and then rallying double-digit. These are inverse patterns:

* WMT: bot is **overconfident** on a stock it shouldn't be confident on
* GM: bot is **missing a real catalyst** it should have a view on

Worth adding both to a Phase 3 diagnostic list alongside the
chronic-LOW work.

### First Near-Miss BUY Result — NVDA 5/19

|Field|Value|
|-|-|
|Signal|BUY at 62% conf|
|Price at signal|$220.58|
|Price +5d|$212.60|
|Return +5d|-3.62%|
|Was Claude Right?|NO|

**First piece of Q2 outcome data.** Early evidence favors "70%
threshold is correctly tight" — but n=1, and the remaining 4
near-miss BUYs (SCHD due 5/29, NVDA #2 + VTI due 6/2, NVDA #3 due
6/3) will fill out the picture. Specifically, the NVDA triple
pattern becomes testable across the next 6 trading days.

### Reading Lesson From Cohort 2

When evaluating a cohort, the right reading sequence is:

1. **Glance at the Pattern Holds? cell** — that's the formula's
binary verdict on the central claim
2. **Look at the three hit-rate cells** to see the magnitude of the
pattern
3. **Note the absolute return** in the 60-69% band — if it's still
highest, you have a separate "extreme confidence = volatile
outcomes" finding worth tracking

Avoid: starting with the cell values and building a narrative. Trust
the formula's verdict first, then explain.

\---

# Active Touch Points

* **May 28, 2026** — Day 8 run; fill +5d for May 20 cohort (Cohort 3)
* **May 29, 2026** — Fill +5d for May 21 cohort + SCHD 5/21 near-miss
* **June 1-2, 2026** — Fill +5d for May 22 cohort + VTI/NVDA near-misses;
first +10d data on May 18 cohort
* **June 3, 2026** — Fill +5d for May 26 + NVDA 5/27 near-miss
* **June 10, 2026** — Phase 2 → Phase 3 review using decision worksheet
* **June 11, 2026** — Next WASDE release (CORN natural catalyst test)

