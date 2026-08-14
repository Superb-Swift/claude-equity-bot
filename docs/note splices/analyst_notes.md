# Claude Equity Bot — Analyst Notes

**Project:** claude-equity-bot
**Phase:** 2 (read-only dry run)
**Window:** 2026-05-18 to 2026-06-12 (closed)
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

**Phase:** 2 (read-only dry run), Day 6 of \~15 (pattern first observed Day 5, 2026-05-22)
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
3. Phase 2 trajectory remains on schedule for 6/12 evaluation

\---

## 2026-05-27 — May 19 Cohort Day-5 Outcomes: Mixed Calibration Signal

**Phase:** 2 (read-only dry run), Day 7 of \~15
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



## 2026-05-28 — Day 8 Run: First Pure-HOLD Day, NVDA Conviction Reverts

**Phase:** 2 (read-only dry run), Day 8 of \~15
**Status:** First day with zero BUY signals and zero near-misses

### Headline

|Metric|Day 7|Day 8|Note|
|-|-|-|-|
|Signals|24|24|Stable|
|Avg confidence|52.8%|51.3%|Lowest of Phase 2 so far|
|Signal distribution|23H/1B|24H/0B|First pure-HOLD day|
|HIGH data quality|8|7|Stable|
|LOW data quality|1 (CBRS)|0|CBRS climbed back to MEDIUM|
|Cost|$0.2274|$0.2258|Stable|

### NVDA Conviction Drop — Diagnostic

After three straight days of NVDA near-miss BUYs (5/19, 5/22, 5/27),
today NVDA reverted to a 45% HOLD at $212.09. Price moved up slightly
from yesterday's $209.84; conviction dropped 18 percentage points.

**Interpretation:** The bot's bullish thesis on NVDA was at least
partially "buy the dip." Higher price → less attractive entry →
weaker BUY conviction. This is internally consistent disciplined
behavior, NOT mechanical bullishness.

**Implication for Q2:** Mild support for the bullish read on the NVDA
triple near-miss — the bot is NOT producing reflexive BUY signals
on this ticker. The three +5d outcomes (one in, two pending) will
still discriminate the broader question.

### Bug Fixed

run\_daily.bat threw ". was unexpected at this time" after parser
completed. Cause: unquoted `if exist paste\_today.tsv echo ...` line
in summary block. Fixed by parenthesizing the conditional echo.

\---

## 2026-05-28 — May 20 Cohort: Calibration Verdict Reached

**Phase:** 2 (read-only dry run), Day 8 of \~15
**Status:** Third completed +5d cohort. Q1 calibration threshold MET.

### Headline Result

The May 20 cohort produced the THIRD consecutive Pattern Holds = ✓ YES
result. The worksheet's 3+ cohort threshold for Q1 (calibration
working) is now met.

|Cohort|40-49%|50-59%|60-69%|Pattern Holds?|
|-|-|-|-|-|
|2026-05-18|25% (2/8)|59% (10/17)|40% (2/5)|✓ YES|
|2026-05-19|43% (3/7)|50% (5/10)|14% (1/7)|✓ YES|
|2026-05-20|36% (5/14)|43% (3/7)|33% (1/3)|✓ YES|
|**Combined**|**34% (10/29)**|**53% (18/34)**|**27% (4/15)**|**✓ YES**|

### Three-Cohort Synthesis

**Locked in:**

* Primary calibration claim (50-59% is most accurate band) is confirmed
* Across 78 evaluated signals, 50-59% leads at 53% hit rate
* 60-69% band underperforms (27% hit rate, n=15) — small sample but
consistent across all three cohorts. Worth flagging but not yet conclusive.

**Q1 Verdict:** CALIBRATED.

### May 20 Headline Numbers

|Metric|May 18|May 19|May 20|
|-|-|-|-|
|Hit rate|47%|37.5%|37.5%|
|Mean abs return|4.95%|5.25%|5.54%|
|Biggest miss|CBRS -18.6%|CBRS -15.5%|CBRS -24.8%|
|Biggest win|GM +9.1%|GM +18.2%|GM +13.3%|

**CBRS / GM pattern stability:** 3 of 3 cohorts have CBRS as the
biggest miss and GM as the biggest win. This is no longer noise.

### Data Quality Signal — First Clean Result

|Quality|Sample|Hit Rate|Abs Return|
|-|-|-|-|
|HIGH|3|100%|1.98%|
|MEDIUM|19|26%|5.30%|
|LOW|2|50%|13.16%|

Three HIGH-quality May 20 signals (SCHD, XLU, NVDA scout) all hit.
Sample tiny (n=3), but directionally encouraging.

\---

## 2026-05-28 — Diagnostic Deep Dive: WMT and GM Patterns

**Severity:** High — these are now confirmed as the two most diagnostic
tickers in the portfolio
**Status:** Phase 3 prompt-revision candidates

### The Pattern

WMT and GM have been the #1 miss in every completed cohort, in
opposite directions:

|Ticker|All 3 cohorts|Direction|Avg Move|Confidence|
|-|-|-|-|-|
|**WMT**|-11.1%, -11.6%, -11.4%|DOWN|-11.3%|62% HOLD|
|**GM**|+9.1%, +18.2%, +13.3%|UP|+13.5%|42-52% HOLD|

### Finding 1: Claude IS Adapting, Just Slowly

Confidence trajectories show the bot DID update — but with 3-5 day lag:

**WMT confidence:** 62% → 62% → 62% → 48% → 45% → 52% → 55% → 55%
(Dropped 17pt AFTER the -11% move had already happened on 5/21)

**GM confidence:** 42% → 52% → 45% → 52% → 52% → 52% → 62% → 58%
(Rose 20pt over the run, but always trailing the rally)

**Implication:** The bot has a price-update lag. Updates eventually
arrive but after the move has already played out.

### Finding 2: Two Distinct Biases

|Bias|WMT Example|GM Example|
|-|-|-|
|Mean-reversion (near 52w high → HOLD)|"Near $135 high, P/E 42x → HOLD"|n/a|
|Anchoring (slow to update)|Repeated valuation framing as price fell|Repeated "cyclical P/E elevated" as price rose|
|Valuation-heavy framing|-11% move was tariff-driven, not valuation|+13% rally was NASA contract, not earnings|

### Finding 3: HIGH Data Quality Did NOT Save the Bot

WMT was flagged HIGH data quality on 3 of 4 completed cohorts.
Bot still missed by -11% each time.

**Implication:** HIGH data quality reflects input quality, not thesis
quality. The prompt may not be distinguishing these clearly enough.

### Phase 3 Hypotheses to Test

|#|Hypothesis|Test|
|-|-|-|
|1|Anchoring on cost-basis P/E for cyclicals|Add momentum/trend-strength field for GM-class signals|
|2|Defensive staples need tariff/news weighting|News-category tagging; penalize HOLD when tariff is dominant|
|3|5-day conviction-update lag|Inject prior-day price change explicitly into prompt|
|4|Symmetric stuckness near 52w highs and lows|Force directional bias when 5-day trend exceeds 5%|

These are experiments, not fixes. Phase 3 must verify they improve
WMT/GM accuracy WITHOUT breaking the confirmed 50-59% calibration.



\---

## 2026-05-29 — Day 9 Run: Fix Verified, Log Recovery, AM/PM Diagnostic

**Phase:** 2 (read-only dry run), Day 9 of \~15
**Status:** run\_daily.bat fix verified; bot ran cleanly; log file
incident discovered and recovered

### Headline

|Metric|Value|
|-|-|
|Signals|24 (23 HOLD / 1 BUY)|
|Avg confidence|52.8%|
|HIGH data quality|10 (41.7%) — highest of Phase 2|
|LOW data quality|2 (CBRS + SND)|
|Near-miss BUY|NVDA 68% at $215.95 (5th in cohort)|
|Cost|$0.2251|

### Bug Fix Verification

The `. was unexpected at this time` error in run\_daily.bat is gone.
Root cause was an unquoted `if not exist` block where the variable
expansion `%TODAY%.log` confused cmd.exe's parser. Single fix:
quoted the path in line `if not exist "logs\\signals\_%TODAY%.log"`.
Verified by clean run today. Lesson learned: yesterday's fix
targeted the wrong block; should have asked to see the file
contents before claiming a fix.

### Log File Truncation Incident

After today's morning run, `signals\_2026-05-29.log` was found
truncated to 3 bytes. Most likely cause: a second run of
run\_daily.bat (to verify the fix worked) opened the log in write
mode, truncating it, then got interrupted before writing signals.

**Recovery:** Reconstructed the log file from the saved PowerShell
output. All 24 Signal JSON entries preserved (66 KB log file).
Signal data was already in the tracker from the morning paste, so
no actual analytical loss.

**Phase 3 fix candidate:** Modify the bot's logging to open in
append mode OR back up existing log to `.bak` before truncating.
This is the cheapest "data loss prevention" change in the codebase.

### AM/PM Diagnostic Comparison

As a side effect of testing the fix, the bot ran twice today
(9:31 AM CST and 3:36 PM CST). The PM run is NOT used for the
Phase 2 cohort (AM remains canonical for methodological
consistency), but the comparison surfaced a Phase 3 finding:

**9 of 24 signals changed between AM and PM. 6 of 24 changed data
quality.** Most striking:

* VTI: HOLD 52% → BUY 68% on a +0.10% price move
* GM:  HOLD 62% → HOLD 55% on a -0.62% move
* GLD: HOLD 42% → HOLD 52% on a +0.18% move

**Implication:** Bot signals are highly news-sensitive within a
single trading day. The "3-5 day update lag" we documented in
WMT/GM is the same phenomenon at a longer timescale. Confidence
updates appear to track news flow more than price action.

**Phase 3 hypothesis to add:** Test whether explicit prompt
language about "stable thesis confidence" vs "news-flow conviction"
reduces intraday volatility while preserving cohort-level
calibration. The PM run is archived as
`logs/diagnostic\_2026-05-29\_PM.txt`.

\---

## 2026-05-29 — May 21 Cohort: First Pattern-Holds = NO, SCHD Near-Miss Wins

**Phase:** 2 (read-only dry run), Day 9 of \~15
**Status:** Fourth completed +5d cohort. Q1 calibration robust to
one non-confirming cohort. First near-miss BUY win.

### Headline Result

Hit rate by confidence band on the May 21 cohort:

|Confidence Band|Sample|Hit Rate|Avg Abs Return|
|-|-|-|-|
|40-49%|9|33%|6.31%|
|50-59%|12|42%|4.70%|
|**60-69%**|**3**|**67%**|**2.70%**|

**Pattern Holds: ✗ NO** — first non-confirming cohort.

The 60-69% band led at 67% hit rate. However, n=3 is very small,
and the bucket consisted of PM, PWR, and SCHD — two
defensive/dividend HOLDs (PM, PWR) that don't move much by design,
plus the SCHD BUY signal. PM and PWR hit; SCHD also hit (covered
below).

### Why This Doesn't Reverse the Q1 Verdict

|Cohort|Pattern Holds?|
|-|-|
|2026-05-18 (n=30)|✓ YES|
|2026-05-19 (n=24)|✓ YES|
|2026-05-20 (n=24)|✓ YES|
|2026-05-21 (n=24)|✗ NO|
|**Combined (n=102)**|**50-59% still leads (50%) vs 40-49% (34%) and 60-69% (33%)**|

3 of 4 cohorts confirm. The combined sample at n=102 still strongly
supports the calibration claim. The Q1 worksheet threshold required
"3+ cohorts," which is met. Yesterday's CALIBRATED verdict holds.

**Lesson on noise vs signal:** This is exactly why the worksheet
required multiple cohorts. A single non-confirming sample with
n=3 in the deciding bucket is the kind of noise the framework
should absorb without reversing. Phase 2 was designed with this
robustness in mind.

### SCHD Near-Miss BUY: First Win

|Field|Value|
|-|-|
|Signal date|2026-05-21 (Roth IRA scout signal)|
|Conviction|68% BUY, HIGH data quality|
|Price at signal|$32.11|
|Price +5d (2026-05-29)|$32.50|
|Return +5d|**+1.22%**|
|Was Claude Right?|**YES**|

**Near-miss BUY cohort running tally (2 of 5 complete):**

|Date|Ticker|Conf|DQ|Return|Right?|
|-|-|-|-|-|-|
|2026-05-19|NVDA|62%|MEDIUM|-3.62%|NO|
|2026-05-21|SCHD|68%|HIGH|+1.22%|YES|
|2026-05-22|NVDA|62%|MEDIUM|due 6/2|—|
|2026-05-26|VTI|68%|HIGH|due 6/2|—|
|2026-05-27|NVDA|63%|MEDIUM|due 6/3|—|
|2026-05-29|NVDA|68%|MEDIUM|due 6/5|—|

(Note: 5/29 NVDA brings the cohort to 6 total, not 5 as previously
counted. The 6/5 outcome is the last Q2 (near-miss BUY) data point;
+10d outcomes continue arriving through 6/12, the review day.)

**Pattern observation:** The two HIGH-data-quality near-miss BUYs
are 1 for 1 (SCHD won; VTI pending). The MEDIUM-DQ near-misses are
0 for 1 (NVDA 5/19 lost). If this pattern holds across the
remaining outcomes, the Phase 3 conclusion would NOT be "lower
the threshold to 65%" — it would be "make the threshold
conditional on data quality."

### Notable Misses (May 21 Cohort)

|Ticker|Conf|DQ|Return|Note|
|-|-|-|-|-|
|**CBRS**|42%|MEDIUM|-17.40%|4th consecutive cohort as worst miss|
|SND|42%|MEDIUM|-11.82%|Frac sand small-cap weakness|
|**GM**|52%|MEDIUM|+9.24%|4th consecutive cohort as biggest win|
|AIQ|55%|HIGH|+9.02%|AI thematic rally caught HOLD|
|MSFT|55%|HIGH|+8.04%|High-conf miss on tech rally|
|AG|52%|MEDIUM|+7.72%|Silver miner participated in rally|
|DOW|45%|MEDIUM|-6.82%|Continued chemical sector pressure|
|PM|62%|HIGH|-6.49%|High-conf miss (PM only hits 60-69% bucket *because* it's defensive — and even defensive names break sometimes)|

### CBRS — Path A Now Unambiguous

|Cohort|CBRS Return|
|-|-|
|2026-05-18|-18.6%|
|2026-05-19|-15.5%|
|2026-05-20|-24.8%|
|2026-05-21|-17.4%|

**Four consecutive cohorts as the worst miss.** The Q3 worksheet
flag on the CBRS Path C decision should be resolved to Path A
(exclude until Q4 2026). The structural-gap diagnosis is
data-confirmed.

\---

## 2026-05-29 — Diagnostic Deep Dive Update: WMT and GM (Cohort 4)

**Phase:** 2 (read-only dry run), Day 9 of \~15
**Status:** New evidence on the 3-5 day update lag finding

### WMT — The Lag Played Out

The Day 8 WMT/GM diagnostic predicted that confidence updates lag
price moves by 3-5 days. The May 21 WMT data tests this:

|Date|Conf|DQ|Return +5d|Right?|
|-|-|-|-|-|
|2026-05-18|62%|MEDIUM|-11.06%|NO|
|2026-05-19|62%|HIGH|-11.64%|NO|
|2026-05-20|62%|MEDIUM|-11.37%|NO|
|**2026-05-21**|**48%**|**HIGH**|**-5.10%**|**NO**|

**Confidence dropped 14 points** AFTER three consecutive
double-digit misses. The bot updated. The miss is still in the
wrong direction, but its magnitude shrank 56% (from -11% to -5%).
This is the lag finding playing out in real time — exactly as
predicted, with measurable closure.

### GM — Lag Still in Effect

|Date|Conf|DQ|Return +5d|Right?|
|-|-|-|-|-|
|2026-05-18|42%|MEDIUM|+9.14%|NO|
|2026-05-19|52%|MEDIUM|+18.23%|NO|
|2026-05-20|45%|MEDIUM|+13.25%|NO|
|**2026-05-21**|**52%**|**MEDIUM**|**+9.24%**|**NO**|

Confidence drifted from 42 → 52 — modest update. Move magnitude
shrank from +18% to +9%. The bot is recognizing GM's strength,
but with much less responsiveness than WMT. Possible explanations:

1. **Direction asymmetry:** Bot may be more reactive to losses
than gains (loss-aversion-like behavior in the prompt).
2. **News density:** WMT generated more news during the run than
GM, providing more update triggers.
3. **Valuation anchoring:** "P/E too high" is a sticky bear
narrative for cyclicals; it may take a fundamental catalyst
beyond price action to dislodge.

### Phase 3 Hypotheses — Updated

|#|Hypothesis|Evidence|Test|
|-|-|-|-|
|1|3-5 day update lag|Confirmed on WMT (5/21 update after 3 prior misses); partially on GM|Add prior-5-day price change to prompt input; measure lag reduction|
|2|Direction asymmetry (loss > gain reactivity)|WMT updated faster than GM|A/B test prompts with symmetric framing|
|3|Intraday news sensitivity|9 signal changes between AM and PM today|Test "stable thesis" prompt language|
|4|Data quality matters for threshold|HIGH-DQ near-misses 1/1, MEDIUM 0/1 (small n)|Continue tracking; if pattern holds, recommend DQ-conditional threshold|

These are now four distinct Phase 3 experiments. Each is testable
without breaking the confirmed 50-59% calibration. Each has
documented baseline behavior from the Phase 2 data.

### Phase 2 Review Date Moved to Fri 6/12

Originally targeted for Wed 6/10 (Day 17), the Phase 2 → Phase 3
review has been moved to **Fri 6/12 (Day 19)**. Rationale:

* 6/10 would force review with +10d data on only 8 of 9 cohorts
(5/28 +10d lands 6/11; 5/29 +10d lands 6/12).
* 6/12 gives complete +5d and +10d data for all 9 cohorts.
* Dataset is now a clean **4 complete trading weeks**
(2026-05-18 through 2026-06-12) with one documented holiday
closure (Memorial Day 5/25).
* Methodology statement: "Phase 2 was a 4-trading-week dry run
with 9 cohorts of 24 signals each, evaluated at +5d and +10d
windows. One trading day lost to Memorial Day. No other
interruptions."

Worksheet rebuilt as v3 with 6/12 review date locked.

## 2026-05-29 — Phase 3 Reference Design: Documented Separately

**Phase:** 2 (read-only dry run), Day 9 of 19
**Status:** Phase 3 design thinking moved to dedicated file
**Decision type:** Document hygiene — keep analyst\_notes focused on Phase 2 execution

### Summary

Two external reference frameworks studied today:

* **The Claude Portfolio** (@theaiportfolios on X) — concentrated single-name
bot with deep per-position thesis and stateful tracking. Currently
UNDERPERFORMING SPY (+2.6% vs +8.3% first 2 months).
* **The Grok Portfolio** (same operator, Dr. Lopez-Lira / AI Finance Labs) —
portfolio-level architecture with sector ETF backbone, cross-asset (bonds
via TLT), and explicit risk discipline. Currently OUTPERFORMING SPY
(+59% vs +36% over 9 months).

User is considering a "triple blend" Phase 3 design: Grok's portfolio-level
architecture + Claude Portfolio's per-position depth + our bot's calibrated
daily analysis and tax-aware reasoning.

### Decision Logged

|Decision|Rationale|Revisit|
|-|-|-|
|No bot changes during Phase 2|Calibration dataset integrity|Post-6/12|
|No new hypothesis added to worksheet|Worksheet stays locked for review|Phase 3-A scoping|
|Phase 3 design thinking moved to dedicated file|Keep analyst\_notes focused on Phase 2 execution and findings|n/a|

### Where to Find the Design Thinking

**Document:** `phase3\_design\_concepts.md` (in project root)

**When to read it:** AFTER Phase 2 close on 2026-06-12, alongside the
locked Decision Worksheet v3 verdicts.

**What it contains:** Full framework comparison (A/B/C), borrowable
design patterns by layer (architecture/reasoning/risk), 6 Phase 3
hypotheses (4 from Phase 2 evidence + 2 framework-borrowed), 5 open
design questions, observation plan for remaining Phase 2 days, and
operational plan for the document itself.

### Lesson Worth Naming

"Don't change anything" is the hardest call in any project — there's
always a more sophisticated framework available to implement. The
discipline is recognizing when you don't yet have the data to know
whether more sophistication helps. Phase 2 is exactly that moment.
Logging this here so future-us doesn't second-guess the hold pattern
when something shiny appears.
---

## 2026-06-02 — May 18 Cohort: First +10d Outcomes — HOLD Theses Have a Shelf Life

**Phase:** 2 (read-only dry run), Day 11 of 19
**Status:** First cohort to reach +10d. New structural finding — the marquee measurement of Week 3.

> ⚠️ FORWARD-POINTER (added 2026-06-05): This entry's "accuracy decays at +10d"
> claim was the FIRST LOOK and did not fully replicate. Across 4 +10d cohorts
> the final tally is: absolute-move growth replicated 4/4, but accuracy-decay
> is a coin flip (2 decayed, 2 did not). The durable claim is magnitude-growth,
> NOT accuracy-decay. Do not quote this entry's decay figure in isolation —
> see 2026-06-03 and 2026-06-05 entries for the resolved picture.

### Headline Result

The May 18 cohort is the first to complete its +10d window. Comparing
the two horizons on the same 24 signals:

|Window|Hit Rate|Avg Return|Avg Abs Move|
|-|-|-|-|
|+5d|12/24 = 50.0%|-0.32%|4.51%|
|+10d|10/24 = 41.7%|-0.58%|5.69%|

**Finding:** +10d outcomes systematically differ from +5d, and in a
specific direction — HOLD accuracy DECAYS over the longer window
(-8.3 pt), while the average absolute move GROWS (4.51% -> 5.69%).
The mechanism is clean: the bot's output is \~95% HOLD, and a HOLD is
"right" only if the stock stays within +/-3%. Give prices twice the time
and more of them breach the band. **The bot's HOLD-heavy output has a
shelf life, and +10d is past it for a meaningful fraction of positions.**

### 10 of 24 Positions Flipped Between Windows

|Ticker|+5d|+10d|Mechanism|
|-|-|-|-|
|MSFT|Y (-1.65%)|N (+4.32%)|Recovered up — HOLD missed upside|
|NVDA|N (-3.35%)|Y (+0.23%)|Round-tripped to flat|
|XLU|N (+3.21%)|Y (-0.05%)|Round-tripped to flat|
|NKE|N (+5.72%)|Y (+2.87%)|Faded back into band|
|SND|N (+3.10%)|Y (+1.45%)|Faded back into band|
|AG|Y (+2.68%)|N (+6.28%)|Continued up, breached|
|FTI|Y (-2.79%)|N (-5.46%)|Continued down, breached|
|CORN|Y (-2.99%)|N (-5.50%)|Continued down, breached|
|NTR|Y (-2.56%)|N (-4.57%)|Continued down, breached|
|VTI|Y (+1.98%)|N (+3.33%)|Drifted past band|

**Two distinct mechanisms, diagnostically different:**

* **Trend continuations (5):** AG, FTI, CORN, NTR, VTI kept moving the
same direction until they breached +/-3%. This is the lag hypothesis —
a move "contained" at +5d simply had not finished. **Predictable from
the +5d trajectory.**
* **Mean-reversions (5):** MSFT, NVDA, XLU, NKE, SND moved then came
back. Noise that resolved. **Not predictable.**

18 of 24 positions held the same direction across both windows — the
underlying drift is mostly persistent. The flips concentrate in names
sitting near the +/-3% boundary.

### WMT Lag Hypothesis — Extends Cleanly Into +10d

This was an explicit open question for the week: does the WMT 3-5 day
lag finding replicate in the +10d window?

**Yes, decisively, and WMT is the textbook case.** WMT was HOLD 62%
(high confidence) on 5/18 at $133.31. It went -11.06% at +5d and
**-15.19% at +10d** — sustained, accelerating decline rated as a
confident hold. FTI, CORN, NTR show the same milder signature. The
"prior-5-day price input" Phase 3 hypothesis (H1) is now supported by
BOTH the +5d and +10d data — no longer a single-ticker anecdote. The
Decision Worksheet v4 Q4/H1 row has been updated with this corroboration.

### Band Behavior Degrades at +10d

|Band|+5d|+10d|
|-|-|-|
|40-49%|33%|50%|
|50-59%|57%|43%|
|60-69%|50%|25%|

At +5d the 50-59% band leads (57%) — Q1 CALIBRATED holds. At +10d the
ordering inverts. Note the low-vol confound: the 40-49% band's +10d
"wins" are sleepy names sitting still. The real signal is the
**60-69% band collapsing to 25%** — PM (62%, -9.36%) and WMT (62%,
-15.19%) are high-confidence HOLDs that got progressively MORE wrong.
In this cohort, confidence is anti-correlated with +10d accuracy for
the names the bot felt strongest about.

### Calibration Verdict Caveat (recorded in worksheet v4)

> The bot is calibrated at +5d (50-59% band leads). At +10d, HOLD
> accuracy decays (\~8pt) and the high-confidence band underperforms,
> driven by sustained adverse moves in high-conviction HOLDs (WMT, PM).
> The +5d window is where the signal lives; +10d is where HOLD theses
> expire.

This is ONE cohort (n=24) — a strong, mechanism-backed first reading,
not a verdict. The 5/19 +10d (due 6/3) is the replication test.

\---

## 2026-06-02 — May 22 \& May 26 Cohorts: Two More Non-Confirming, Aggregate Holds

**Phase:** 2 (read-only dry run), Day 11 of 19
**Status:** Cohorts 5 and 6 +5d complete. Both Pattern Holds = NO; aggregate unaffected.

### Cohort Results (closing prices)

|Cohort|40-49%|50-59%|60-69%|Pattern Holds?|Hit Rate|
|-|-|-|-|-|-|
|2026-05-22|38% (3/8)|50% (6/12)|50% (2/4)|✗ NO (tie)|45.8%|
|2026-05-26|83% (5/6)|64% (9/14)|50% (2/4)|✗ NO (low band led)|66.7%|

> ANALYST NOTE (corrected 2026-06-08): the 5/22 +5d hit above was previously logged as 54.2% — that is the 5/29 cohort's figure. The tracker's Was-Claude-Right column and band cells (3+6+2 = 11/24) both give 45.8%. See the 2026-06-08 entry.

**5/22 fails on a tie:** 50-59% and 60-69% both at 50% — the strict-greater
test requires the middle band to exceed BOTH tails. A tie is a NO.

**5/26 fails differently — the low-vol confound:** the 40-49% band led at
83% (5/6), but those "wins" are SND (-0.41%), CORN (-2.75%), NKE (-2.30%)
— low-volatility names that pass the HOLD +/-3% test by sitting still, not
by skill. Meanwhile the cohort's real action was in names the bot rated
mid-band and missed: AIQ +7.82%, MSFT +5.73%, AG +5.79% (all HOLD, all NO).

### Aggregate Still Holds (n=144 band sample / 150 filled +5d)

|Band|Was (n=102)|Now (n=144)|
|-|-|-|
|40-49%|34%|42%|
|50-59%|50%|**52%**|
|60-69%|33%|40%|

The 50-59% band still leads cleanly. **Q1 CALIBRATED is now 4 of 6
confirming cohorts, outweighing 2 noisy per-cohort NOs.** The per-cohort
flags are decided by n=3-4 samples in the 60-69% band and are noisy by
construction; the aggregate is the real evidence.

### Signal-Type Calibration — BUY Outperforms HOLD

|Signal|Hit Rate|
|-|-|
|BUY|3/4 = 75%|
|HOLD|66/146 = 45%|

The directional BUY calls (the near-misses) are beating the HOLD base
rate. Small n, but it is what you want from a conviction signal.

\---

## 2026-06-02 — Q2 Near-Miss: VTI Clean Test Wins; DQ Split Weakens

**Phase:** 2 (read-only dry run), Day 11 of 19
**Status:** Near-miss cohort 4 of 6 complete. Verdict trending KEEP 70%.

### Outcomes (4 of 6 complete)

|Date|Ticker|Conf|DQ|Return +5d|Right|
|-|-|-|-|-|-|
|5/19|NVDA|62%|MED|-3.62%|NO|
|5/21|SCHD|68%|HIGH|+1.22%|YES|
|5/22|NVDA|62%|MED|+3.50%|YES|
|5/26|VTI|68%|HIGH|+1.14%|YES|
|5/27|NVDA|63%|MED|due 6/3|—|
|5/29|NVDA|68%|MED|due 6/5|—|

**Tally: 3/4 = 75% positive | avg +5d return +0.56%.**

### VTI Is the Most Informative Near-Miss Yet

VTI was flagged in advance as a cleaner threshold test than any NVDA
entry: it is the broad market, not a single-name catalyst chase. It hit
(+1.14%). The near-miss band now has a positive outcome on a
non-speculative, HIGH-DQ, low-idiosyncratic thesis — evidence the 68%
reads carry signal beyond NVDA momentum.

### The DQ Split Weakened (H4 downgrade)

Heading in: HIGH-DQ near-misses 1/1, MEDIUM 0/1 — pointed toward a
DQ-conditional threshold (H4). NVDA 5/22 (+3.50%, MEDIUM) broke the clean
split: MEDIUM is now 1/2, same-ticker NVDA is 1 loss / 1 win. **H4 is a
weaker recommendation than it looked on 5/29.** Do not lock before 6/5.

### Verdict Math — KEEP 70% (the return criterion is binding)

Per the Near-Miss sheet's pre-committed rule, lowering to 65% requires
hit rate >=75% AND avg return >=3%. Hit rate is at 75%, but avg return is
+0.56% — nowhere near 3%. Even if all three pending landed positive, the
average would need \~+5.6% each to clear the bar. **Realistic Phase 2
conclusion: the 70% threshold is correctly tight. That is the experiment
working — a read-only dry run talking us out of a premature change.**

\---

## 2026-06-02 — Rate-Limit Skips Confirmed as Recurring (Phase 3 Fix)

**Phase:** 2 (read-only dry run), Day 11 of 19
**Severity:** Medium — data-completeness risk, not a calibration risk
**Status:** Promoted from "watch" to named Phase 3 fix

### The Pattern

|Date|429 Skips|
|-|-|
|5/26|none (clean)|
|6/1|AG, FTI|
|6/2|CORN, XLU, SPY|

The skipped tickers DIFFER each day — they are tied to position in the
burst sequence hitting Schwab's rate ceiling, not to specific symbols.
This rules out "bad ticker" and confirms missing rate-limit handling in
`schwab\_client`. Two consecutive skip-days after a clean week is enough
to name the fix: **add exponential backoff / retry on HTTP 429 to the
quote client.**

**SPY skip (6/2) has outsized cost:** SPY is the benchmark scout. Missing
its mark leaves a one-day gap in the benchmark series. Backfill SPY's 6/2
close specifically even if CORN/XLU are left.

### Phase 2 Integrity

Skips are acceptable in read-only Phase 2 (no trades missed). Affected
cohorts log 21-22 of 24 rows; backfill manually if full cohort rows are
wanted. In Phase 3 with execution enabled, a silent skip on a held
position would be a real gap — hence the priority bump.

\---

## 2026-06-03 — +10d Decay Finding Splits on Replication; H1 Hardens; Strongest Cohort Yet

**Phase:** 2 (read-only dry run), Day 12 of 19
**Status:** 5/27 cohort +5d complete; 5/19 +10d complete (replication test); Cohort Analysis tab extended through 6/12.

### Headline: The +10d "Decay" Finding Replicates Halfway

Yesterday (5/18 cohort) produced the week's marquee finding: HOLD
accuracy decayed \~8pt from +5d to +10d while absolute moves grew. The
5/19 cohort was the replication test. Result — **PARTIAL replication.
The mechanism replicates; the consequence does not.**

|Cohort|Window|Hit Rate|Avg Return|Avg Abs Move|
|-|-|-|-|-|
|5/18|+5d|50.0%|-0.32%|4.51%|
|5/18|+10d|41.7%|-0.58%|5.69%|
|5/19|+5d|37.5%|+0.06%|5.25%|
|5/19|+10d|37.5%|-0.66%|6.09%|

* **CONFIRMED — absolute moves grow at +10d.** Both cohorts show the
avg absolute move expanding (5/18: 4.51 -> 5.69; 5/19: 5.25 -> 6.09)
and avg return drifting more negative. Prices keep moving past +/-3%
as the window lengthens. This mechanism is now replicated.
* **NOT CONFIRMED — HOLD accuracy decay.** 5/18 dropped 8.3pt at +10d;
5/19 was FLAT (37.5% both windows). The accuracy consequence depends
on whether the growing moves break toward or away from positions
near the +/-3% line — cohort-specific noise at n=24.

**Why the divergence:** 5/19 had only 4 flips (vs 5/18's 10), and they
offset (2 gained, 2 lost), leaving the hit rate unchanged. 5/19's band
table is identical +5d vs +10d (43/50/14) — no band member flipped
enough to move a rate. 5/18's flips were lopsided toward losses.

> ANALYST NOTE: The defensible claim going into the 6/12 review is
> "absolute moves grow at +10d" (replicated), NOT "HOLD accuracy
> systematically decays at +10d" (one cohort, not replicated by the
> second). The Decision Worksheet +10d caveat should be softened to
> match. The 5/20 +10d (next) is the tiebreaker on the accuracy question.

### H1 (Update Lag) — Now the Most Robust Phase 2 Finding

WMT replicates emphatically across both +10d cohorts:

|Cohort|WMT Signal|+5d|+10d|
|-|-|-|-|
|5/18|HOLD 62%|-11.06%|-15.19%|
|5/19|HOLD 62%|-11.64%|-12.87%|

Same name, same high confidence, same sustained accelerating decline
over BOTH horizons. Where the broader decay claim split, the WMT lag
signature held in every window measured. **H1 (add prior-5-day price
input) is now the best-supported Phase 3 hypothesis** — it replicates
where the more ambitious +10d-decay claim did not.

### 5/27 Cohort — Strongest Calibration Confirmation to Date

|Band|Hit Rate|
|-|-|
|40-49%|67% (4/6)|
|50-59%|**85% (11/13)**|
|60-69%|80% (4/5)|

Overall 19/24 = 79.2% — highest hit rate of any cohort. Pattern Holds
= ✓ YES, cleanly (50-59% leads). DQ behaved as theory predicts: HIGH
7/8 (88%), MEDIUM 12/15 (80%), LOW 0/1. Worst: CBRS -16.8% (the chronic
excluded name). After two non-confirming cohorts (5/22 tie, 5/26
low-vol confound), 5/27 restores a confirming majority: **Q1 now 5 of 7
cohorts confirm.**

### NVDA 5/27 Near-Miss WON — Q2 Binding Constraint Now Crisp

NVDA 5/27 was the series-low entry ($209.84), flagged as the cleanest
test of whether near-conviction reads carry directional signal:

**BUY 63% MEDIUM | $209.84 -> $214.75 | +2.34% | YES**

Near-miss cohort is now 4/5 = 80% positive, which CLEARS the >=75%
hit-rate gate for lowering the threshold. But avg +5d return remains
far below the +3% bar.

> ANALYST NOTE: With the hit-rate gate cleared, the +3% average-return
> criterion is now the SOLE binding constraint on the threshold
> decision. Lowering 70% -> 65% requires BOTH gates; the return gate
> is the one that fails. Verdict stays KEEP 70% — and the reason is now
> a single, clearly-identified number, not a vague "needs more data."
> Final through 2026-06-05.

### Cohort Analysis Tab — Extended Through Phase 2 Close (6/12)

The Cohort Analysis tab now carries all Phase 2 cohorts (5/18 -> 6/12),
fully formula-driven:

* Added 12 cohort rows (5/28 -> 6/12) with the existing COUNTIFS pattern
keyed per row. Completed cohorts compute live; not-yet-complete
cohorts read "insufficient data" (gating fixed so empty cohorts no
longer falsely display "NO").
* Section-1 summary corrected to count only cohorts with +5d data in
the "X of Y hold" denominator.
* Sections 2 (Data Quality) and 3 (Signal Type) repaired after the
row-insert — both live again: HIGH 56.5%, MEDIUM 48.7%, LOW 55.6%
(n=168); HOLD 50.3%, BUY 80%.
* Verified by full recalculation; Signals/Dashboard/Near-Miss tabs
untouched.

> ANALYST NOTE: Reading caution — the 6/2 (n=21) and 6/3 (n=22) rows
> show samples below 24 due to 429 skips (not data-entry errors), and
> cohorts from 6/5 onward cannot reach +5d before the 6/12 review
> (their +5d dates fall on/after review day), so those rows stay
> "insufficient data" at review by design.

\---

## 2026-06-04 — Day 13 Run + 5/28 Cohort + 5/20 +10d Tiebreaker

**Phase:** 2 (read-only dry run), Day 13 of 19
**Status:** Clean 24/24 run (2nd consecutive). 5/28 cohort +5d complete; 5/20 +10d resolved the decay tiebreaker.

### Run Health

First clean 24/24 run since 5/26 — zero rate-limit skips, after 6/2 (3 skips)
and 6/3 (2 skips). No log evidence of retry/backoff firing, so the likeliest
cause is lighter Thursday API contention rather than a confirmed fix. The
Phase 3 429-backoff fix still stands; one clean day does not retire the pattern.

### 5/28 Cohort +5d

|Band|Hit Rate|
|-|-|
|40-49%|56% (5/9)|
|50-59%|**77% (10/13)**|
|60-69%|50% (1/2)|

Overall 16/24 = 66.7%. Pattern Holds = ✓ YES (50-59% leads). DQ: HIGH 5/7,
MEDIUM 11/17. Worst: CBRS −17.3% (chronic excluded name, again). Best: SND
+19.5%.

> ANALYST NOTE: SND +19.5% is a HOLD that COUNTS AS A MISS (breached +3%) even
> though the position gained \~20%. The HOLD ±3% test scores large favorable
> moves as "wrong" because the bot didn't say BUY. Correct by the locked
> definition, but when reading cohort accuracy, remember some "misses" are
> gains left on the table, not losses the bot failed to avoid.

### 5/20 +10d — The Decay Tiebreaker

The decay question was 1-1 (5/18 decayed −8pt; 5/19 flat). 5/20 broke it:

|Cohort|+5d Hit|+10d Hit|Δ|Decayed?|
|-|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|Yes|
|5/19|37.5%|37.5%|0.0pt|No|
|5/20|37.5%|33.3%|−4.2pt|Yes|

So decay sided with 5/18 (2 decayed, 1 flat). The magnitude-growth mechanism
is now 3/3 (every cohort: absolute moves grow at +10d). NOTE: this was the
"leans real" read at the time — superseded same week by the 5/21 +10d (see
6/05 entry), which flipped it back to a coin flip.

### WMT Lag — Replicates a THIRD Time

WMT 5/20: HOLD 62%, −11.37% (+5d), −12.24% (+10d). Three consecutive cohorts
(5/18, 5/19, 5/20) of the same high-confidence HOLD with double-digit
sustained losses in both windows. H1 anchor evidence.

### NVDA Near-Miss Confidence Decay Continues

NVDA 8th near-miss; confidence stair-stepped down 68→68→68→66→65 as price
unwound from the $228 peak back toward $213. Quick to de-rate on the drop,
never re-rated on the climb — the H2 (loss>gain reactivity) asymmetry in a
scout name. GLD reverted to HOLD after its one-day BUY (5/26-style single
event, not a cluster).

\---

## 2026-06-05 — Day 14: Q2 VERDICT LOCKED; 5/29 Cohort; 5/21 +10d; Decay = Coin Flip

**Phase:** 2 (read-only dry run), Day 14 of 19
**Status:** All 9 cohorts +5d-complete. Q2 near-miss threshold verdict LOCKED.
Clean 24/24 run (3rd consecutive). The week's terminal data event.

### Q2 VERDICT — LOCKED: KEEP 70% Threshold

The complete near-miss cohort (6 of 7 outcomes; NVDA 6/1 due 6/8 as addendum):

|Date|Ticker|Conf|DQ|+5d Return|Right|
|-|-|-|-|-|-|
|5/19|NVDA|62%|MED|−3.62%|NO|
|5/21|SCHD|68%|HIGH|+1.22%|YES|
|5/22|NVDA|62%|MED|+3.50%|YES|
|5/26|VTI|68%|HIGH|+1.14%|YES|
|5/27|NVDA|63%|MED|+2.34%|YES|
|5/29|NVDA|68%|MED|−5.02%|NO|

**Hit rate: 4/6 = 66.7%   |   Avg +5d return: −0.07%.**

Both loosening gates FAIL: hit rate 66.7% < 75% required, AND avg return
−0.07% is far below the +3% required. NVDA 5/29 closed −5.02% (NVDA fell to
$205), pulling the hit rate back below the gate after the 5/22/5/27 wins had
briefly lifted it.

> ANALYST NOTE: The 70% threshold is correctly calibrated. It screens out a
> band (60-69% BUYs) whose realized performance is barely better than a coin
> flip with NEGATIVE expected return (−0.07% avg). This is the experiment
> doing exactly its job: a read-only dry run that prevented a premature
> threshold loosening. Had we lowered to 65% on the early 3/4 reading, we'd
> have admitted a negative-EV signal class. KEEP 70% is the verdict.

> ANALYST NOTE (DATA-INTEGRITY): The tracker's Near-Miss summary "Average +5d
> return" formula was averaging K5:K9 (5 rows), EXCLUDING the NVDA 5/29
> −5.02% loss in row 10 — it displayed +0.92% instead of the correct −0.07%.
> Off-by-one range bug. Fixed to K5:K13 and summary ranges extended to capture
> pending near-misses. The verdict math above uses the corrected figure.

### H4 (DQ-Conditional Threshold) — DEMOTED

HIGH-DQ near-misses finished 2/2 (SCHD, VTI); MEDIUM-DQ finished 2/4 (wins
5/22, 5/27; losses 5/19, 5/29). The HIGH-DQ 2/2 is real but n=2 — far too
small to justify a DQ-conditional threshold. The same-ticker NVDA series
finished 2 wins / 2 losses across 4 entries — a coin flip. H4 should be
re-scoped in Phase 3 only if a larger near-miss sample reopens it.

### 5/29 Cohort +5d

|Band|Hit Rate|
|-|-|
|40-49%|14% (1/7)|
|50-59%|**73% (8/11)**|
|60-69%|67% (4/6)|

Overall 13/24 = 54.2%. Pattern Holds = ✓ YES (50-59% leads decisively). This
is the 9th and final cohort to reach +5d.

### Q1 CALIBRATED — FINALIZED

All 9 cohorts +5d-complete. Final aggregate (n=216 band-sample):

|Band|Hit Rate|
|-|-|
|40-49%|43.1% (31/72)|
|50-59%|**61.3% (65/106)**|
|60-69%|50.0% (19/38)|

**Q1 FINAL: ✓ CALIBRATED — 6 of 9 cohorts confirm; 50-59% leads at 61.3%
in the combined data.** The 3 non-confirming cohorts (5/21, 5/22, 5/26) are
explained by tiny 60-69% samples and low-volatility names inflating the
40-49% band; none reverse the aggregate.

### 5/21 +10d — Decay Reverts to a COIN FLIP

|Cohort|+5d Hit|+10d Hit|Δ|
|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|
|5/19|37.5%|37.5%|0.0pt|
|5/20|37.5%|33.3%|−4.2pt|
|5/21|41.7%|45.8%|**+4.2pt**|

5/21 IMPROVED at +10d, putting the final +10d decay tally at **2 decayed
(5/18, 5/20), 2 not (5/19 flat, 5/21 improved)** — a coin flip. Meanwhile the
magnitude-growth mechanism stayed 4/4 (absolute moves grew in every cohort).

> ANALYST NOTE: This RETIRES the "HOLD accuracy decays at +10d" finding as
> non-robust. The durable, replicated claim is "absolute moves grow at +10d"
> (4/4). The accuracy consequence depends on whether the growing moves break
> toward or away from the ±3% line — cohort-specific noise at n=24. The
> Decision Worksheet +10d caveat has been re-firmed to this language in v5.

### WMT Lag — The Full Trajectory, With Resolution

WMT 5/21 broke the double-digit streak (−5.10% +5d, −2.54% +10d). Tracing all
9 cohorts reveals the lag's full life cycle and its RESOLUTION:

|Cohort|Conf|+5d|+10d|
|-|-|-|-|
|5/18|62%|−11.06%|−15.19%|
|5/19|62%|−11.64%|−12.87%|
|5/20|62%|−11.37%|−12.24%|
|5/21|48%|−5.10%|−2.54%|
|5/22|45%|−4.37%|—|
|5/26|52%|−4.89%|—|
|5/27|55%|−1.14%|—|
|5/28|55%|−0.62%|—|
|5/29|52%|+2.45%|—|

> ANALYST NOTE: This is the single cleanest illustration of H1 in the dataset,
> and it now has a RESOLUTION, not just a failure. At 62% confidence the bot
> held WMT through three identical \~−11% losses (5/18-5/20). Then it CAUGHT UP:
> confidence dropped to 48-55% as the losses simultaneously shrank (−5%, −4%,
> −1%), and by 5/29 WMT was +2.45%. The lag self-corrected over \~3-5 days —
> exactly H1's hypothesized window. H1 (add prior-5-day price input) is the
> top Phase 3 hypothesis: it is the only finding that replicated across every
> cohort AND has a clear mechanism AND a demonstrated resolution.

\---

## 2026-06-08 — Day 15: Q2 Addendum Recorded (KEEP 70% Confirmed); 5/22 +10d; Magnitude-Growth Takes Its First Hit

**Phase:** 2 (read-only dry run), Day 15 of 19
**Status:** NVDA 6/1 near-miss +5d completed (Q2 7th/final addendum). 5/22 cohort
+10d complete (5 of 9 +10d-complete). Clean 24/24 run. One data-integrity
correction logged (5/22 +5d).

### NVDA 6/1 Near-Miss +5d — Q2 Addendum (7th outcome)

NVDA 6/1 (entry $221.59, the Computex-rally near-miss) completed +5d at the 6/8 close:

|Field|Value|
|-|-|
|Signal|BUY 68% MEDIUM (scout)|
|Price at signal (6/1)|$221.59|
|Price +5d (6/8 close)|$208.64|
|Return +5d|−5.84%|
|Was Claude Right?|NO|

Complete near-miss cohort — 7 of 7 outcomes:

|Date|Ticker|Conf|DQ|+5d Return|Right|
|-|-|-|-|-|-|
|5/19|NVDA|62%|MED|−3.62%|NO|
|5/21|SCHD|68%|HIGH|+1.22%|YES|
|5/22|NVDA|62%|MED|+3.50%|YES|
|5/26|VTI|68%|HIGH|+1.14%|YES|
|5/27|NVDA|63%|MED|+2.34%|YES|
|5/29|NVDA|68%|MED|−5.02%|NO|
|6/1|NVDA|68%|MED|−5.84%|NO|

**Hit rate: 4/7 = 57.1% | Avg +5d return: −0.90%.**

> ANALYST NOTE: Q2 verdict KEEP 70% is now FINAL through the addendum. The 6/1
> outcome did not merely fail to change the verdict — it moved both metrics
> further from the loosening bar (hit 66.7% → 57.1%; avg −0.07% → −0.90%). A single
> 7th outcome could only ever lower, never lift, the hit rate toward the ≥75% gate,
> and a −5.84% print pulled the average further below the +3% gate. The 70% screen
> held out four consecutive 68%-confidence scout BUYs ($221.59 and unwinding)
> across exactly the window NVDA fell from \~$228 to \~$205.

### 5/22 Cohort +10d — Magnitude-Growth's First Exception

The 5/22 cohort reached +10d at the 6/8 close (10 trading days; Memorial Day excluded):

|Window|Hit Rate|Avg Abs Move|
|-|-|-|
|+5d|11/24 = 45.8%|4.52%|
|+10d|12/24 = 50.0%|4.09%|

* **Accuracy did NOT decay** — it improved +4.2pt (45.8% → 50.0%).
* **Absolute move SHRANK** (4.52% → 4.09%) — the FIRST cohort where the +10d
magnitude-growth mechanism failed. Driver: two big +5d movers mean-reverted by
+10d (AIQ +10.29% → +2.35%, MSFT +10.38% → −1.32%), outweighing SND's blow-out
(−4.51% → +16.51%).

Band behavior (+5d → +10d): 40-49% 38% → 25%; 50-59% 50% → 75%; 60-69% 50% → 25%.

**Running +10d tally (5 of 9 complete):**

|Cohort|+5d|+10d|Δ|Decayed?|Abs move|Grew?|
|-|-|-|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|Yes|4.51→5.69|Yes|
|5/19|37.5%|37.5%|0.0pt|No|5.25→6.09|Yes|
|5/20|37.5%|33.3%|−4.2pt|Yes|5.54→6.28|Yes|
|5/21|41.7%|45.8%|+4.2pt|No|5.05→5.18|Yes|
|**5/22**|**45.8%**|**50.0%**|**+4.2pt**|**No**|**4.52→4.09**|**No**|

* **Magnitude grew: 4 of 5** (5/22 the exception)
* **Accuracy decayed: 2 of 5** (5/18, 5/20) — still a coin flip, now leaning "no decay"

> ANALYST NOTE: Magnitude-growth was the durable, replicated +10d claim (4/4),
> slated as the headline +10d takeaway for the 6/12 review; 5/22 is its first
> counterexample, dropping it to 4/5. This does NOT reopen Q1 (a +5d verdict) — but
> the Decision Worksheet / §3 Finding #3 "+10d magnitude grows (4/4)" line should be
> softened to 4/5, and 5/26–5/29 (+10d due 6/9–6/12) will decide whether 5/22 is
> n=24 noise or the start of a breakdown. The accuracy-decay claim stays retired.

### WMT Lag (H1) — +10d Trajectory Fully Self-Corrected

WMT 5/22: HOLD 45%, +5d −4.37%, +10d **−0.00%** (flat → a HOLD hit at +10d). The
+10d trajectory across the five completed cohorts:

|Cohort|Conf|+10d|
|-|-|-|
|5/18|62%|−15.19%|
|5/19|62%|−12.87%|
|5/20|62%|−12.24%|
|5/21|48%|−2.54%|
|5/22|45%|−0.00%|

> ANALYST NOTE: The +10d window now shows H1's full arc and resolution: as the bot
> de-rated WMT from 62% to 45–48%, the +10d loss collapsed from −15% to \~0%. H1
> (add prior-5-day price input) remains the top Phase 3 hypothesis — the only
> finding replicated across every cohort AND both horizons AND with a demonstrated
> self-correction.

### Q1 Re-Certified — Unchanged

Re-ran the band aggregate after entering the 5/22 +10d prices and the NVDA 6/1
addendum (neither touches the 9-cohort +5d hit column):

|Band|Hit Rate (n=216)|
|-|-|
|40-49%|43.1% (31/72)|
|50-59%|**61.3% (65/106)**|
|60-69%|50.0% (19/38)|

**Q1 CALIBRATED holds: 50-59% leads at 61.3%, 6 of 9 cohorts confirm.** Nothing in
today's data reopens a locked verdict.

### Data-Integrity Correction — 5/22 +5d Hit Rate (54.2% → 45.8%)

The 6/2 entry's Cohort Results table and the 6/1 Touch Points line both logged the
5/22 +5d hit rate as 54.2%. The tracker's own Was-Claude-Right column gives
11/24 = 45.8%, and the Cohort-Analysis band cells (3/8 + 6/12 + 2/4 = 11)
independently agree. The 54.2% was the 5/29 cohort's figure mis-copied. Both
instances corrected. All 9 cohort +5d hit rates were re-verified against the
tracker — the other 8 match to the decimal. No locked verdict is affected (Q1 rests
on the band aggregate; 5/22 was a NO either way, a 50/50 band tie). The Decision
Worksheet was checked and does NOT carry the error (it describes 5/22 as a tie).

### 6/8 Run Health + Bonus

Clean 24/24 AM run (avg confidence 52.9%, HIGH DQ 8/24, zero 429 skips — 4th clean
run across 6/4–6/8). Today produced a new NVDA BUY 68% near-miss at $208.41 (10th
near-miss overall; +5d due 6/15) — bookkeeping, outside the locked Q2 cohort. The
full 6/1 cohort +5d was also opportunistically filled (22 of 24; AG/FTI were
429-skipped on 6/1, so 22 is the max), but it sits outside the 9-cohort Phase 2
review set.

\---

## 2026-06-09 — Day 16: 5/26 +10d — Sharpest Decay Yet, and It Validates the Low-Vol Confound Call

**Phase:** 2 (read-only dry run), Day 16 of 19
**Status:** 5/26 cohort +10d complete (6 of 9). Near-Miss tab extended with +10d
tracking columns; 4 completed +10d near-miss outcomes verified. Clean 24/24 run.

### 5/26 Cohort +10d — −37.5pt, With a Known Mechanism

|Window|Hit Rate|Avg Abs Move|
|-|-|-|
|+5d|16/24 = 66.7%|2.92%|
|+10d|7/24 = 29.2%|4.47%|

The sharpest +10d decay of Phase 2 by a wide margin (prior worst: 5/18 at
−8.3pt). But this is NOT a surprise result — it is the 6/2 entry's low-vol
confound unwinding on schedule:

* The 6/2 entry flagged 5/26's 66.7% as inflated: the 40-49% band led at 83%
(5/6) on names that passed the HOLD ±3% test by sitting still (SND −0.41%,
CORN −2.75%, NKE −2.30%), not by skill. Pattern Holds was scored NO for
exactly this reason.
* At +10d those names finally moved: AG −16.63%, SND +8.72%, CORN −6.43%,
DOW −6.24% — all HOLD misses. The 40-49% band collapsed **83% → 17%**.
* Band trajectory (+5d → +10d): 40-49% 83% → 17%; 50-59% 64% → 36%; 60-69%
50% → 25%.

> ANALYST NOTE: This is inflation unwinding, not skill decaying. The cohort
> whose +5d hit rate we explicitly distrusted is the one that collapsed at
> +10d — the +10d data validates the 6/2 skepticism and strengthens the case
> that low-vol HOLD passes are fragile, hollow hits. Candidate Phase 3
> observation (not a finding, n=1 mechanism-match): +5d hit rates built on
> low-vol sitting-still passes should be expected to mean-revert at longer
> horizons. Also note 5/26 had the LOWEST +5d avg abs move of any cohort
> (2.92%) — a quiet week that caught up, consistent with magnitude-growth.

### Running +10d Tally (6 of 9 complete)

|Cohort|+5d|+10d|Δ|Decayed?|Abs move|Grew?|
|-|-|-|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|Yes|4.51→5.69|Yes|
|5/19|37.5%|37.5%|0.0pt|No|5.25→6.09|Yes|
|5/20|37.5%|33.3%|−4.2pt|Yes|5.54→6.28|Yes|
|5/21|41.7%|45.8%|+4.2pt|No|5.05→5.18|Yes|
|5/22|45.8%|50.0%|+4.2pt|No|4.52→4.09|No|
|**5/26**|**66.7%**|**29.2%**|**−37.5pt**|**Yes**|**2.92→4.47**|**Yes**|

* **Magnitude grew: 5 of 6** — recovered after the 5/22 exception.
* **Accuracy decayed: 3 of 6** — an exact coin flip. The decay claim stays
RETIRED as a general finding; what 5/26 adds is a *conditional* story
(decay severity tracks +5d inflation), not a directional rule.

### WMT Lag (H1) — Sixth Cohort, Still Resolved

WMT 5/26: HOLD 52%, +5d −4.89%, +10d **+0.01%**. The +10d trajectory:

|Cohort|Conf|+10d|
|-|-|-|
|5/18|62%|−15.19%|
|5/19|62%|−12.87%|
|5/20|62%|−12.24%|
|5/21|48%|−2.54%|
|5/22|45%|−0.00%|
|5/26|52%|+0.01%|

> ANALYST NOTE: Six consecutive cohorts, one clean arc: de-rating from 62% to
> the mid-40s/low-50s tracked the +10d loss collapsing from −15% to flat. H1
> remains the top Phase 3 hypothesis with no contrary evidence anywhere in the
> dataset.

### Near-Miss Tab Extended to +10d — Corroborating, Not Re-Litigating

The tab now carries +5d/+10d date and outcome columns. The four near-misses
with completed +10d windows (all entries formula-verified, dates
trading-day-correct):

|Date|Ticker|+5d|+10d|10d Right|
|-|-|-|-|-|
|5/19|NVDA|−3.62%|−2.64%|NO|
|5/21|SCHD|+1.22%|+0.59%|YES|
|5/22|NVDA|+3.50%|−3.75%|NO (flipped from +5d YES)|
|5/26|VTI|+1.14%|−1.75%|NO (flipped from +5d YES)|

**+10d: 1/4 = 25% hit, −1.89% avg** — worse than the +5d picture (4/7 = 57.1%,
−0.90%). Two +5d wins flipped to +10d losses.

> ANALYST NOTE: Q2 is FINAL on the +5d basis and this does not reopen it — but
> the +10d extension corroborates the verdict from the other side: the
> near-miss band gets WORSE, not better, with more time. Every horizon we
> check says the same thing about 60-69% BUYs.

### Q1 Re-Certified — Unchanged

50-59% leads at 61.3% (65/106) over 40-49% 43.1% (31/72) and 60-69% 50.0%
(19/38), n=216. The +10d entries do not touch the +5d hit column. Nothing
reopens.

### 6/9 Run Health + Bookkeeping Flags

Clean 24/24 AM run (avg confidence 51.3%), 5th consecutive clean run. NVDA
BUY 68% MEDIUM @ $207.40 — the 11th near-miss (5th consecutive trading day
with an NVDA near-miss BUY). HIGH DQ count dropped to 4/24 (recent days \~8/24)
— watch, not alarm.

Flags for the tab: (1) the 6/8 NVDA near-miss ($208.41, +5d due 6/15) and
today's 6/9 NVDA near-miss ($207.40, +5d due 6/16) are not yet rows in the
Near-Miss tab — summary still says Total = 9, should be 11; (2) the VERDICT
box still says "to be decided 2026-06-10" — stale, Q2 is FINAL, review is
6/12.

\---

## 2026-06-10 — Day 17: 5/27 +10d Lands on the Shock — −50pt, Regime-Contaminated; Near-Miss Registry Needs Repair

**Phase:** 2 (read-only dry run), Day 17 of 19
**Status:** 5/27 cohort +10d complete (7 of 9). 6/10 Middle East tension shock —
the +10d measurement date IS the shock day. 6/3 cohort +5d opportunistically
complete (22/22 max). Clean 24/24 run — second pure-HOLD day of Phase 2. Two
Near-Miss tab integrity findings.

### 5/27 Cohort +10d — −50.0pt, the Largest Decay, and Why It Can't Be Read at Face Value

|Window|Hit Rate|Avg Abs Move|
|-|-|-|
|+5d|19/24 = 79.2%|2.67%|
|+10d|7/24 = 29.2%|5.16%|

Band trajectory (+5d → +10d): 40-49% 67% → 17%; 50-59% 85% → 31%; 60-69% 80% → 40%.
Biggest +10d movers: AG −20.46%, PWR −11.06%, CBRS −8.15% (recovering from −16.82%
at +5d), GLD −8.00%, SND +6.84%, AAPL −6.64%.

Two compounding mechanisms, and neither is "the bot got worse":

1. **Quiet-week inflation (the 5/26 story, again, stronger).** 5/27 had the
LOWEST +5d avg abs move of Phase 2 (2.67%) and the HIGHEST hit rate (79.2%)
— hollow sitting-still HOLD passes. 5/26 and 5/27 are now a matched pair:
the two quietest cohorts at +5d are the two biggest decayers at +10d.
2. **The +10d measurement date IS the shock day.** The 6/10 Middle East tension
selloff is the close that prices this entire cohort's +10d. A market-wide
gap mechanically blows HOLDs out of the ±3% band regardless of selection
skill — all 24 of 5/27's signals were HOLDs, and 17 failed at +10d.

> ANALYST NOTE — REGIME CONTAMINATION: The 5/28 (+10d due 6/11) and 5/29 (due
> 6/12) windows also contain the shock. That means the remaining Phase 2 +10d
> data CANNOT cleanly arbitrate the accuracy-decay question — the retired claim
> stays retired, and late-cohort +10d hit rates should be reported with the
> regime flag at the review. The §6 "single market regime" caveat materialized
> inside Phase 2 itself. Do NOT update priors on bot skill from 5/26–5/29 +10d
> accuracy; DO note that magnitude-growth keeps confirming (it is
> regime-agnostic: 6 of 7).

> ANALYST NOTE — METHODOLOGICAL (Phase 3 candidate): HOLD ±3% correctness is
> regime-dependent by construction. Candidate design fix: market-relative HOLD
> bands (e.g., ±3% vs SPY-adjusted return) or vol-scaled bands. Pairs naturally
> with H2 (direction asymmetry) and H3 (stable-thesis language).

### Running +10d Tally (7 of 9 complete)

|Cohort|+5d|+10d|Δ|Decayed?|Abs move|Grew?|
|-|-|-|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|Yes|4.51→5.69|Yes|
|5/19|37.5%|37.5%|0.0pt|No|5.25→6.09|Yes|
|5/20|37.5%|33.3%|−4.2pt|Yes|5.54→6.28|Yes|
|5/21|41.7%|45.8%|+4.2pt|No|5.05→5.18|Yes|
|5/22|45.8%|50.0%|+4.2pt|No|4.52→4.09|No|
|5/26|66.7%|29.2%|−37.5pt|Yes|2.92→4.47|Yes|
|**5/27**|**79.2%**|**29.2%**|**−50.0pt**|**Yes**|**2.67→5.16**|**Yes**|

* **Magnitude grew: 6 of 7** — robust, and regime-agnostic (the shock grows
magnitudes too).
* **Accuracy decayed: 4 of 7** — but 2 of the 4 are regime-contaminated;
ex-shock the tally is 2 of 5. Claim stays RETIRED; report with the flag.

### WMT Lag (H1) — Seventh Cohort, Held Through the Shock

WMT 5/27: HOLD 55%, +5d −1.14%, +10d **+1.99%** — a HOLD hit on the shock day.
Trajectory: −15.19 → −12.87 → −12.24 → −2.54 → −0.00 → +0.01 → +1.99. Seven
cohorts, fully resolved, and the de-rated thesis survived a market-wide gap.

### Near-Miss Registry — Two Integrity Findings (Signals tab is authoritative)

**Finding 1 — the two "6/2" rows are actually 6/3 signals.** The tab's GLD
62% @ $408.50 and NVDA 66% @ $215.13 match the Signals tab's **6/3** rows
exactly (6/3 was the two-BUY day; 6/2 had one). Their +5d dates (6/10) and
entered outcomes (GLD −8.30% NO, NVDA −6.84% NO) are exactly correct FOR 6/3
signals — only the Signal Date cells are wrong. Fix: re-date both rows
6/2 → 6/3; no outcome recomputation needed.

**Finding 2 — five band BUYs are missing from the registry.** Per the Signals
tab, every 60-69% BUY on/after 6/1: 6/1 NVDA 68% ✓(in tab), 6/2 NVDA 68%
@ $227.93 **MISSING** (+5d was due 6/9: close $208.19 → −8.66% NO), 6/3 GLD ✓
and 6/3 NVDA ✓ (the mis-dated pair), 6/4 NVDA 65% @ $213.79 MISSING (+5d due
6/11), 6/5 NVDA 65% @ $211.98 MISSING (due 6/12), 6/8 NVDA 68% @ $208.41
MISSING (due 6/15), 6/9 NVDA 68% @ $207.40 MISSING (due 6/16). Registry should
total 14 (locked 7 + extended 7), not 9. Note: the notes' own daily entries
also missed the 6/4 and 6/5 near-misses (65% band) in real time.

> ANALYST NOTE: None of this touches Q2 — the locked verdict is the 7-of-7
> 5/19–6/1 cohort, which is intact and correctly recorded. But the EXTENDED
> tracking set now reads 0-for-3 on completed post-lock +5d outcomes (6/2
> −8.66%, 6/3 −8.30%, 6/3 −6.84%), all worse than anything in the locked
> cohort. Including extensions: 4/10 = 40% hit. Every new data point lands on
> the KEEP-70% side — the shock made rejected near-miss BUYs look even better
> rejected. Also: the tab's summary block (Total = 9, 44.4%) is built on the
> mis-dated registry and mixes locked + extended — suggest splitting the
> summary into LOCKED 7-of-7 (final) and EXTENDED (running). VERDICT box date
> still says 2026-06-10 — stale, review is 6/12.

### Near-Miss +10d Extension (informational)

NVDA 5/27 +10d completed today: $209.84 → $200.42 = −4.49% NO (correct +10d
date ✓). Five +10d outcomes now in: 1/5 = 20%, avg −2.41%. The +5d→+10d flips
remain one-directional (two YES→NO, zero NO→YES).

### Q1 Re-Certified — Unchanged

50-59% leads at 61.3% (65/106) vs 43.1% / 50.0%, n=216. All +5d data predates
the shock. Nothing reopens.

### 6/10 Run Health

Clean 24/24 AM run, avg confidence 51.2%, HIGH DQ 7/24 (recovered from
yesterday's 4/24). **Second pure-HOLD day of Phase 2** (first: 5/28) — zero
BUYs and zero SELLs on the shock morning; the NVDA near-miss streak ended at
six trading days (6/2–6/9). Worth carrying into H2/H3 thinking: confidence
compressed toward the middle on the shock (no signal cleared either threshold),
which is the conservative failure mode, not the dangerous one.

\---

## 2026-06-11 — Day 18: 5/28 +10d on the Bounce; WASDE Validates the CORN Blind Spot; Scope Correction on the Shock Set

**Phase:** 2 (read-only dry run), Day 18 of 19
**Status:** 5/28 cohort +10d complete (8 of 9 — only 5/29 remains, due at
tomorrow's review). WASDE released \~11:00 CST; 6/11 was a bounce day (SPY
+1.70%). 6/4 cohort +5d complete. One correction to my own 6/10 framing,
logged below. Clean 24/24 run.

### CORRECTION — Shock-Contaminated Set Is 5/27–5/29, NOT 5/26–5/29

The 6/10 entry and memo callout over-included 5/26 in the regime-contamination
flag. Verified against the trading-day calendar: the 5/26 +10d window ran
5/27 → **6/9** and closed the day BEFORE the 6/10 shock.

|Cohort|Window ends|Contains 6/10 shock?|
|-|-|-|
|5/26|6/9|**NO**|
|5/27|6/10 (shock day)|YES — measurement date|
|5/28|6/11 (bounce day)|YES — day 9 of 10|
|5/29|6/12|YES — day 8 of 10|

> ANALYST NOTE: The correction SHARPENS the finding rather than weakening it.
> 5/26's −37.5pt decay needed no shock — it is the clean, uncontaminated
> exhibit of the quiet-week inflation unwind (the 6/9 mechanism analysis used
> moves through the 6/9 close and stands as written). 5/27 is the same unwind
> PLUS the shock as its measurement day. The conditional observation is now
> two-for-two with and without a regime event: the two quietest +5d cohorts
> (2.92%, 2.67% abs moves) are the two biggest decayers.

### 5/28 Cohort +10d — −25.0pt, Measured on the Bounce

|Window|Hit Rate|Avg Abs Move|
|-|-|-|
|+5d|16/24 = 66.7%|3.28%|
|+10d|10/24 = 41.7%|4.69%|

Bands (+5d → +10d): 40-49% 56% → 22%; 50-59% 77% → 46%; 60-69% 50% → 100%
(2/2, tiny n — the band *improved*). Biggest movers: AG −15.19% (despite
+7.70% today), CBRS −13.01% (recovering from −17.29% at +5d), SND +19.47% →
+8.59% (reversion continuing), MSFT +1.01% → −7.89%, CORN −7.62%, GLD −5.62%.

5/28 was Phase 2's first pure-HOLD day, so this is 24 HOLDs against ±3%
through shock-then-bounce: 10 survived. The −25.0pt decay is milder than
5/27's −50.0pt largely because the measurement date caught the recovery —
SPY +1.70%, GLD +3.13%, AG +7.70% on 6/11.

> ANALYST NOTE — PATH DEPENDENCE: HOLD ±3% at a fixed horizon is
> path-dependent around a gap. 5/27 measured ON the shock (−50.0pt); 5/28
> measured one day later on the bounce (−25.0pt). Same regime event, 25pt of
> difference purely from where the window happened to close. Reinforces the
> Phase 3 candidate: market-relative or vol-scaled HOLD bands.

### Running +10d Tally (8 of 9 complete)

|Cohort|+5d|+10d|Δ|Decayed?|Abs move|Grew?|Shock?|
|-|-|-|-|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|Yes|4.51→5.69|Yes|—|
|5/19|37.5%|37.5%|0.0pt|No|5.25→6.09|Yes|—|
|5/20|37.5%|33.3%|−4.2pt|Yes|5.54→6.28|Yes|—|
|5/21|41.7%|45.8%|+4.2pt|No|5.05→5.18|Yes|—|
|5/22|45.8%|50.0%|+4.2pt|No|4.52→4.09|No|—|
|5/26|66.7%|29.2%|−37.5pt|Yes|2.92→4.47|Yes|**no — pre-shock**|
|5/27|79.2%|29.2%|−50.0pt|Yes|2.67→5.16|Yes|yes (close ON shock)|
|**5/28**|**66.7%**|**41.7%**|**−25.0pt**|**Yes**|**3.28→4.69**|**Yes**|**yes (closed on bounce)**|

* **Magnitude grew: 7 of 8** — robust across quiet weeks, the shock, and the
bounce.
* **Accuracy decayed: 5 of 8; ex-shock 3 of 6** — still a coin flip ex-shock.
Claim stays RETIRED. The durable structure is conditional: inflation-unwind
decay (severe, mechanism-driven: 5/26, 5/27) vs noise-band wobble
(5/18, 5/20 vs 5/19, 5/21, 5/22).

### WASDE / CORN — The Catalyst Test Lands on the Blind-Spot Side

|Item|Value|
|-|-|
|CORN 6/10 → 6/11|$17.07 → $16.72 = **−2.05%**|
|SPY same day|+1.70%|
|Market-relative move|**≈ −3.69%**|
|Bot's 6/11 AM signal (9:30 CST, pre-release)|HOLD **38%** MEDIUM @ $16.945|

CORN fell 2% on WASDE day against a +1.7% tape — a ≈3.7% market-relative move
on a scheduled, publicly-calendared release. The AM run, which precedes the
\~11:00 CST release, printed CORN at 38% confidence (lowest band) with no
event awareness: the bot did not know WASDE existed, let alone that it was
today. CORN has also bled −7.62% over the 5/28 +10d window.

> ANALYST NOTE: This is the natural-catalyst test the kickoff specified, and
> it reads as VALIDATING Path B (`commodity\_context.py` /
> `commodity\_backed\_equity\_context.py`): a knowable, scheduled event moved the
> asset materially and the equity-news pipeline was structurally blind to it.
> Honest sizing: one event, one move — supportive evidence for the Phase 3
> module thesis, not proof of effect size. Carry to memo §5d tomorrow.

### WMT Lag (H1) — Eighth Cohort

WMT 5/28: HOLD 55%, +5d −0.62%, +10d **+1.71%**. Trajectory: −15.19 → −12.87
→ −12.24 → −2.54 → −0.00 → +0.01 → +1.99 → +1.71. Eight cohorts, fully
resolved, stable through shock and bounce alike. H1 enters the review
untouched by anything in four weeks of data.

### Near-Miss Extended Set — 0-for-4

6/4 NVDA 65% near-miss completed +5d today: $213.785 → $204.87 = **−4.17%
NO** (computed from the 5/28 +10d price column — function output). Extended
post-lock set is now 0-for-4 (−8.66%, −8.30%, −6.84%, −4.17%), avg −7.0%.
Today's run added another: NVDA BUY **65%** @ $199.94 — extended set is 8
signals, registry should total 15. The 6/10 registry findings (re-date the
"6/2" pair to 6/3; five-now-six missing rows; split LOCKED vs EXTENDED
summary; stale verdict box) remain open — worth doing before tomorrow's
review so the tab presents clean.

### Q1 Re-Certified — Unchanged

50-59% leads at 61.3% (65/106), n=216, 6 of 9 Pattern Holds. Nothing reopens.

### 6/11 Run Health

Clean 24/24 AM run, avg confidence 51.5%, HIGH DQ 5/24 — fourth consecutive
depressed day (8 → 4 → 7 → 5); flag for the review's run-health summary but
no operational impact. NVDA near-miss streak resumed after the 6/10
pure-HOLD day; NVDA closed $204.87, +2.5% above the AM print, on the bounce.

\---

## 2026-06-12 — Day 19: Phase 2 CLOSED — Final Cohort, Final Scorecards, Review Decisions

**Phase:** 2 (read-only dry run), Day 19 of 19 — **FINAL DAY
Status:** 5/29 +10d complete. All 9 cohorts complete on both windows (n=216
banded +5d, 216 +10d). Phase 2 → Phase 3 review held; memo finalized (§0, §3,
§4, §5, §7). Phase 3-A approved, advisory-only. Clean 24/24 run.

### 5/29 Cohort +10d — Final Cohort In

|Window|Hit Rate|Avg Abs Move|
|-|-|-|
|+5d|13/24 = 54.2%|4.95%|
|+10d|9/24 = 37.5%|5.14%|

−16.7pt, shock at day 8 of the window, measured 6/12. Mildest of the three
shock-window decays — 5/29 carried no quiet-week inflation (its +5d abs move
was a normal 4.95%). Bands (+5d → +10d): 40-49% 14% → 29% (improved); 50-59%
73% → 36%; 60-69% 67% → 50%. Biggest movers: SND +16.41%, AG −12.99%, MSFT
−11.35%, CBRS −10.14%, JPM +8.39%.

### FINAL +10d Scorecards (9 of 9, locked)

|Cohort|+5d|+10d|Δ|Decayed?|Abs move|Grew?|Shock?|
|-|-|-|-|-|-|-|-|
|5/18|50.0%|41.7%|−8.3pt|Yes|4.51→5.69|Yes|—|
|5/19|37.5%|37.5%|0.0pt|No|5.25→6.09|Yes|—|
|5/20|37.5%|33.3%|−4.2pt|Yes|5.54→6.28|Yes|—|
|5/21|41.7%|45.8%|+4.2pt|No|5.05→5.18|Yes|—|
|5/22|45.8%|50.0%|+4.2pt|No|4.52→4.09|No|—|
|5/26|66.7%|29.2%|−37.5pt|Yes|2.92→4.47|Yes|no (pre-shock)|
|5/27|79.2%|29.2%|−50.0pt|Yes|2.67→5.16|Yes|yes (close ON shock)|
|5/28|66.7%|41.7%|−25.0pt|Yes|3.28→4.69|Yes|yes (closed on bounce)|
|5/29|54.2%|37.5%|−16.7pt|Yes|4.95→5.14|Yes|yes (shock day 8)|

* **Magnitude grew: 8 of 9** (5/22 the lone exception) — the robust +10d claim,
confirmed across quiet weeks, the shock, and the bounce. Finding #3 and the
memo §4 callout reconciled; worksheet v6 caveat edit is the carry-forward.
* **Accuracy decayed: 6 of 9; ex-shock 3 of 6** — coin flip; claim RETIRED with
the regime flag (5/27–5/29) and the conditional inflation-unwind observation
(5/26–5/27).

### WMT (H1) — The Arc Completes, With a Twist

WMT 5/29: HOLD 52%, +5d +2.45%, +10d **+4.31%** — the final point breaches the
±3% band on the FAVORABLE side (a HOLD "miss" that made money). Full +10d arc:

−15.19 → −12.87 → −12.24 → −2.54 → −0.00 → +0.01 → +1.99 → +1.71 → **+4.31**

> ANALYST NOTE: A fitting close. The lag self-corrected from −15% to flat
> (cohorts 1–6), held through the shock (7–8), and then the recovery ran past
> the band while confidence sat at 52% (9) — the lag is visible in BOTH
> directions: slow to de-rate into losses, slow to re-rate into recovery. This
> sharpens H1's test design (prior-5-day input should fix both sides) and
> mildly complicates H2's pure loss-asymmetry story — exactly what the A/B
> harness is for. H1 enters Phase 3 with nine cohorts of replication and zero
> contrary observations.

### Near-Miss Day — Two More, and the Extended Set Hits 0-for-5

* 5/29 NVDA near-miss +10d filled (by Rob, verified): $215.95 → $205.19 =
**−4.98% NO**. Near-miss +10d: 1/6 = 16.7%, avg −2.84%.
* 6/5 NVDA near-miss +5d due today (not yet a tab row): $211.975 → $205.19 =
**−3.20% NO**. Extended post-lock set: **0-for-5** (−8.66, −8.30, −6.84,
−4.17, −3.20), avg −6.23%.
* Today's run: **two near-misses** — VTI BUY **68% HIGH** @ $365.62 (first
non-NVDA since 5/26, and HIGH-DQ like both prior non-NVDA near-misses) and
NVDA BUY 62% MEDIUM @ $205.60. Registry should now total **17** (locked 7 +
extended 10).
* Registry fixes from 6/10 remain open (mis-dated "6/2" pair → 6/3; missing
rows; LOCKED vs EXTENDED summary split; stale verdict box). Promoted to a
Phase 3 engineering item: **auto-generate the registry from the Signals
tab** — the hand-maintained version drifted twice in one week.

### Q1 — FINAL CERTIFICATION

|Band|Hit Rate (n=216)|
|-|-|
|40-49%|43.1% (31/72)|
|50-59%|**61.3% (65/106)**|
|60-69%|50.0% (19/38)|

Pattern Holds 6 of 9. Unchanged through every data event of Week 4 — the 5/22
correction, the addendum, six +10d completions, the shock, and the bounce.
**Q1 = CALIBRATED is the certified Phase 2 result.**

### Review Decisions (memo §0/§5/§7 finalized)

|Decision|Outcome|
|-|-|
|Phase 2 calibration validated?|**YES** — Q1 CALIBRATED, n=216|
|Q2 threshold|**KEEP 70%** — 7-of-7 final + extended 0-for-5|
|Phase 3 approved?|**YES — Phase 3-A, prompt-level, advisory-only**|
|Triple blend|**Deferred to 3-B scoping**, gated on 3-A calibration data|
|First workstream|**H1 prior-5-day price input** (parallel eng.: CBRS exclusion, commodity modules, 429 backoff, registry auto-gen, HOLD-band methodology)|
|Hypothesis order|H1 → H3 → H2; H4 to backlog|
|Q1–Q5 leans|\~25 book · cross-asset deferred · rebuild-daily + price input · **advisory** · Risk Engine unchanged for 3-A|

### 6/12 Run Health + Phase 2 Operational Close

Clean 24/24 AM run, avg confidence 53.0%, HIGH DQ 7/24 (recovered). Phase 2
operational record: 19 trading days, 451 signal rows, 9 review cohorts ×
24 × 2 windows complete, two pure-HOLD days (5/28, 6/10), three 429-skip days
(6/1–6/3, fixed by spacing), zero missed runs. **Phase 2 is closed.**

\---

## 2026-06-15 — Phase 3-A Go-Live: First Advisory Run Captured; Analyzer Phase-Bug Fixed; Toolchain Hardened; Repo Reconciled

**Phase:** 3-A (prompt-level, advisory-only — **LIVE**), Day 1
**Status:** Phase 3-A is live. First 24/24 advisory run generated and captured to the Signals tab (rows 456–479). No orders — advisory-only, human-gated. One latent analyzer bug surfaced at the phase cutover and was fixed; the runner toolchain was hardened; the public repo was reconciled and a push bundle staged. First live cohort (6/15) is pending its +5d.

### Go-Live — First Advisory Run

Clean 24/24 AM run, **all HOLD**, risk engine APPROVED across the board, zero orders (advisory-only working as designed). The 24 control-arm signals parsed to the tracker at rows **456–479**, columns A–G matching the log exactly (AAPL 0.58/HIGH/295.46 … GLD 0.52/MEDIUM/400.17), H–J empty pending outcomes, K–N outcome formulas in place. The Dashboard swept the new rows in — **Total Signals 475** (451 Phase 2 + 24) — and the **50-59% guardrail still leads at 58.8%** (today's HOLDs add to the band totals but not to YES/NO, by design, since they have no +5d yet).

> ANALYST NOTE: The 451-vs-475 signal-distribution gap traced to AG and FTI — two \*\*price-only backfills\*\* (429-skipped on 6/1, so no signal was ever generated; their prices were filled for return tracking). Signal blank → Was-Right falls through to "" → both rows sit inert in every band and cohort while still carrying prices. Not a defect; nothing to fix.

### analyze\_log.py — Phase-Regex Fix (latent 19 days, broke on the cutover)

The analyzer reported **0 signals** on the 6/15 log while the parser read 24 from the same file. Root cause, one line: the summary regex was `PHASE \\d DRY RUN]`. `\\d` matches a **single digit**, so it matched `\[PHASE 2 DRY RUN]` cleanly but `\[PHASE 3-A DRY RUN]` — digit `3`, then `-A` — broke the match. `summary\_history.txt` is the audit trail: it parsed every Phase-2 day through 6/12 and dropped to 0 the instant the phase label changed on 6/15.

Fix: `PHASE \[\\w.-]+ DRY RUN(?: A)?]`. `\[\\w.-]+` matches any phase label (`2`, `3-A`, `3-B`, `4`…); `(?: A)?` accepts the no-suffix single-arm form **and** the control arm `… DRY RUN A]` while **excluding** variant `… DRY RUN B]`, so an A/B day summarizes the control arm only — consistent with the tracker paste. Reproduced in-sandbox: **0 → 24** on the single-arm log, **24 (not 48)** on the A/B log with no duplicate tickers; Phase 2 logs still parse.

> ANALYST NOTE: A textbook boundary bug — a single-digit assumption silently correct for 19 trading days, wrong the first morning the assumption changed. The class to watch in the rebuild is anywhere the phase string is parsed rather than passed. The two "0 signals" stanzas already in `summary\_history.txt` stay as the record; a re-run appends a fresh correct entry with no new API spend.

### Go-Live Toolchain Hardening

* **Bats (all three):** `set PYTHONUTF8=1` (UTF-8 I/O regardless of Windows locale); an openpyxl self-check in `run\_weekly\_review.bat`; new `requirements.txt` (openpyxl) for the analysis layer.
* **run\_daily.bat parser fix:** the `. was unexpected at this time.` error was unescaped parens — the literal `(non-fatal)` inside an `if errorlevel 1 (…)` block let cmd read the `)` as the block close. Rephrased the echo to drop the parens; the 9:30 run came through clean.
* **Harnesses h1–h4:** added `--since` / `--until` date slicing (module globals, **byte-identical default**) so Phase 3-A can be analyzed apart from the certified Phase 2 window.
* **Encoding:** UTF-8 file writes added to h1–h4 and the registry builder (cp1252 write trap).

### news\_client.py — Freshness Sort (the only change to an otherwise-untouched file)

Verdict: **correctly unchanged** for Phase 3-A — it returns lists (no file writes, so the cp1252 trap can't reach it), and news is fetched once per ticker and reused across both A/B arms, so it needs no phase or variant awareness. One robustness add: a newest-first `sorted(... key="datetime" ..., reverse=True)` after the empty-guard in **both** fetchers, guaranteeing freshness independent of Finnhub's (undocumented, comment-only) ordering — a degraded response can no longer quietly hand Claude the week's oldest headlines.

### Tracker Structure + Cohort Wiring

Filled the K:N outcome formulas down to row **2000**; added Cohort **Section 4: Phase 3-A Cohorts** (40 holiday-aware date rows, 6/15–8/11, mirroring Section 1); extended the Dashboard fixed ranges. Recalc: **0 errors / 8,584 formulas**. The text-date-vs-datetime risk (Section 4 dates are TEXT `"2026-06-15"`; Signals dates are real `datetime`) was **proven** harmless via a throwaway +5d injection across three bands — the 6/15 cohort immediately read Sample 3 with bands populated and correct hit rates; the scratch copy was discarded. Section 4 row 53 reads `0 / insufficient` today by design (the sample formula counts only resolved +5d) and lights up when col-H is entered (\~6/23).

### README + Risk-Engine Reconciliation

Rewrote the Phase-2-stale README to Phase 3-A reality: phase badge, Phased-Rollout table (Phase 2 closed, Phase 3-A current), a "Research \& validation tooling" section (h1–h4, registry, the three runners, `--since`), `requirements.txt` setup, and the calibration outcome (50-59% @ 61.3%, near-miss 70%). Corrected **MAX\_OPEN\_POSITIONS 30 → 8** — a pure **doc lag**: the live "Active Rules" block prints 8, so the engine has enforced 8 all along; only the committed README said 30. `risk\_engine.py` needs no edit (confirmed).

### EDGAR — Scoped to Phase 3 (decision, no code)

Decision: **do not build in 3-A; build at the Phase 3 boundary** as one `edgar\_client.py`, shaped like `news\_client.py` (lazy client, CIK cache, graceful `return \[]`, summarize-not-dump, `requests`/urllib only; risk\_engine needs nothing). Scope = **fast catalysts** (Form 4 insider, 8-K material events) + **slow context** (10-Q/10-K MD\&A + risk factors) + **optional** XBRL fundamentals (low value — duplicates Schwab P/E/EPS). **10-K folded in with 10-Q** — same submissions feed and the same MD\&A/risk-factor parser, near-zero incremental cost, richer annual Item 1A.

> ANALYST NOTE: The methodological key, and the reason this waited. The 3-A guardrail and cohort were calibrated on \*\*news-only\*\* input. Turning EDGAR onto the live path mid-phase would change what the guardrail was measured against and confound the 3-A cohort. So it enters as a \*\*measured A/B arm\*\* (reuse H2: A = news, B = + EDGAR), not a baseline upgrade — evidence first, calibrated baseline preserved. The roadmap's two SEC rows (2.5 fundamentals + 3 10-Q) were folded into a single Phase 3 SEC/EDGAR line to match.

### Repo Reconciliation + Push

Reconciled the local working set against the public repo (17 commits): `analyze\_log.py`, `README.md`, and `news\_client.py` updated; the four harnesses, the three runners, `parse\_log\_to\_tracker.py`, and `requirements.txt` added (never committed before). `.gitignore` confirmed secure — `.env`, `token.json`, `logs/`, the tracker, and the paste TSVs all excluded (docs and tracker intentionally local). Staged a flat, byte-faithful **13-file bundle** (`.bat`s CRLF-preserved); push commands provided. The sandbox can't authenticate to the repo, so the push itself is Rob's to run.

\---

## 2026-06-16 — Phase 3-A Day 2: First Live Near-Misses (VTI, NVDA) Logged; Near-Miss Tab Repaired

**Phase:** 3-A (advisory-only), Day 2
**Status:** 6/16 run captured — the first Phase 3-A BUY signals, both near-misses. VTI (68%) and NVDA (65%) recorded to the Near-Miss BUYs tab (rows 14–15, pending outcomes). The tab was repaired in passing: relabeled to span both phases, verdict box resolved, and the drifted +10d cells on rows 11–15 restyled. 6/15 re-run confirmed 0 near-misses; the 6/15 cohort's +5d is still pending (\~6/23).

### 6/16 Run — First Phase 3-A BUYs

24 signals, **2 BUY / 22 HOLD** — the first BUYs of Phase 3-A (6/15 was 24/24 HOLD). Both are scouts that landed in the 60-69% near-miss band and were rejected by the 70% threshold (risk engine APPROVED 22 / REJECTED 2):

|Ticker|Conf|Miss|DQ|Price|5-day context|
|-|-|-|-|-|-|
|VTI|68%|−2 pt|HIGH|$372.15|+3.94% run into its 52-wk-high zone|
|NVDA|65%|−5 pt|MEDIUM|$209.12|+4.35% recovery|

Average confidence 56.5% (up from 55.1% on 6/15); bands firmed toward the 60s — 11 in 40-59 / 11 in 60-69 (vs 6/15's 17 / 6). HIGH DQ 15/24. Pasted to Signals rows 480–503. (The 5/18 cohort's first **+20d** date also came due today — informational only; Phase 2's verdicts are closed on the +5d/+10d windows.)

> ANALYST NOTE: Both near-misses are momentum-driven (5-day run-ups), echoing the Phase 2 pattern where 60-69% BUYs clustered on recent strength. VTI at HIGH DQ is the cleaner probe — the project's read is that HIGH-DQ, non-NVDA near-misses are the least-confounded threshold tests. Their outcomes (+5d 6/24, +10d 7/1) are the first live evidence on whether KEEP-70% holds in Phase 3-A.

### Near-Miss Registry — Two New Entries

Logged VTI and NVDA to the **Near-Miss BUYs** tab (rows 14–15) on the existing schema — return and was-right formulas in place, +5d/+10d price cells left as pending yellow inputs (+5d resolves 6/24, +10d 7/1). COHORT SUMMARY ranges extended to row 15: **tab total now 11** (was 9); the resolved-outcome stats are unchanged — 9 complete +5d, 44.4% hit, avg −2.38% — since the two new rows are pending. 6/15 contributed none (24/24 HOLD). (These are additive to the *logged* set, not the registry reconciliation: the Phase-2 band-BUY backfill flagged on 6/12 — tab at 9 vs the \~17 the logs imply, the missing 6/4–6/9 entries — remains the open `build\_near\_miss\_registry.py` auto-gen item for Phase 3.)

### Near-Miss Tab Repairs

The tab had drifted (the registry-maintenance thread from the Phase 2 close). Three fixes, recalc clean at 0 errors:

* **Relabeled** — title now spans "Phase 2 + Phase 3-A"; subtitle marks rows 5–13 as Phase 2 (closed 6/12) and 14+ as Phase 3-A. Kept one continuous list (no section split) since the COHORT SUMMARY aggregates all rows.
* **Verdict resolved** — the box still read "to be decided 2026-06-10"; now "KEEP 70% (resolved 2026-06-05)", pointing at the actual outcome (+5d hit 44% ≤ 50%, avg −2.4% ≤ 0%) against the criteria already listed below it.
* **Rows 11–15 +10d cells** — the +10d price/return/was-right cells (J/L/N) had lost their fills (plain white vs the yellow-input / gray-formula convention); restyled to match the completed rows. Filled the +10d **dates** — H11 6/15, H12/H13 6/17 — each set to 5 trading days after that row's own +5d date.

> ANALYST NOTE: r12/r13's +5d dates read 6/10, where five trading days from the 6/2 signal lands on 6/9 — likely a hand-entry drift. The +10d dates I filled follow each row's existing +5d, so they stay internally consistent; if a +5d is later corrected, its +10d shifts by the same amount. Source-of-truth flag, not a blocker.

\---

## 2026-06-17 — Phase 3-A Day 3: First +20d Cohorts Confirm Magnitude Growth to 20 Days; Near-Miss +10d at 1/9

**Phase:** 3-A (advisory-only), Day 3
**Status:** 6/17 run captured (24/24 HOLD, clean). The first +20d outcomes resolved — 5/18 and 5/19 — and both extend the magnitude-growth finding to the 20-day horizon (2-for-2). Three more near-miss +10d outcomes landed, all NO, dropping the +10d hit rate to 1/9. The 50-59% guardrail holds (live 59.3%). Phase 3-A's own +5d is still pending (\~6/23).

### 6/17 Run + Integrity

24 signals, **24/24 HOLD** — no BUYs, so no new near-misses (VTI 58% and NVDA 55% sat below the 60-69% band). Rows 504–527, every ticker/account/confidence/DQ matching the log. Recalc clean (**0 errors / 8,592 formulas**); totals reconcile — **523 signals** (451 Phase 2 + 72 across 6/15–17), BUY 19 (17 Phase 2 + the two 6/16 near-misses), the AG/FTI price-only backfills still inert. +5d coverage now reaches the 6/10 cohort (403/523, 77%). One data note: 6/17's prices are captured at sub-cent precision (NVDA $207.5015, AIQ $65.475, CBRS $223.795) where 6/15–16 were 2-decimal — harmless for the return math, flagged for source-of-truth, not corrected.

### First +20d Cohorts — Magnitude Growth Extends to 20 Days

The first two +20d outcomes resolved (5/18 due 6/16, 5/19 due 6/17; 24 each — the only cohorts matured to +20d). Absolute-move trajectory:

|Cohort||move| +5d|+10d|+20d|avg ret +5d → +20d|
|-|-|-|-|-|
|5/18|4.51%|5.69%|**6.72%**|−0.32% → −1.96%|
|5/19|5.25%|6.09%|**7.17%**|+0.06% → −2.43%|

Both grow **monotonically** through +20d, so the Phase 2 magnitude finding (8/9 cohorts, +5d→+10d) **extends cleanly to the 20-day horizon — now 2-for-2.** Direction drifted net negative in both (−2.0%, −2.4% at +20d).

> ANALYST NOTE: The cleanest statement yet of why magnitude — not the retired accuracy-decay — is the robust finding. HOLD is a short-horizon signal: by +20d the typical absolute move is \~7%, far outside the 3%-band "no significant move" thesis the HOLD encodes. The signal isn't so much \*wrong\* at +20d as \*out of scope\* — its predictive window is \~5 days and the move keeps compounding past it. Carry into the Phase 3 horizon design.

### Near-Miss +10d — Extended Set Still 0-for-3, Hit Rate 1/9

The three +10d prices prepped on 6/16 were filled — NVDA 6/1, GLD 6/2, NVDA 6/2 — **all NO** (−4.12%, −4.87%, −4.87%). The Near-Miss tab is now 9-of-11 complete on +10d: **hit rate 11.1% (1/9)**, down from 16.7%, avg −3.43%. Every post-lock extended near-miss has now also failed at +10d (the +5d extended set closed 0-for-5; +10d echoes it).

> ANALYST NOTE: Corroborates \*\*KEEP 70%\*\* from the +10d angle — 60-69% BUYs convert at \~11% over ten days. The lone winner stays SCHD 5/21 (the one HIGH-conviction non-NVDA name). VTI/NVDA 6/16 are the first Phase 3-A near-misses, still pending (+5d 6/24, +10d 7/1).

### Guardrail / Coverage

Live +5d accuracy by band: **50-59% leads at 59.3%** (115/194), clear of 60-69% (50.7%, 37/73) and 40-49% (46.0%, 58/126). The lead has eased from the certified **61.3%** as more +5d resolved past the close — expected drift, ordering intact. DQ ordering also holds (HIGH 59.3% > MEDIUM 50.9% > LOW 44.4%). Section 1 (Phase 2) frozen — 10 of 17 cohorts hold the pattern. Section 4 (Phase 3-A) all pending; no live guardrail data until \~6/23.

\---

## 2026-06-18 — Phase 3-A Day 4: 5/20 +20d Makes Magnitude Growth 3-for-3; Near-Miss Registry Backfilled to 19; Guardrail Compression Traced; H1 Harness Live-Ready

**Phase:** 3-A (advisory-only), Day 4
**Status:** 6/18 run captured (24/24 HOLD, clean — no near-misses). In the day's data, the third +20d cohort (5/20) keeps the magnitude-growth streak at 3-for-3, and the 6/11 Phase 2 cohort's +5d resolved Pattern NO. Three workstreams were set up alongside the daily: the Phase-2 near-miss registry was **regenerated from the Signals tab (11 → 19 rows)**, closing the standing backfill item; a **guardrail-compression trace** was built and run; and the **H1 lag-trace harness was dry-run** against live data and is ready to fire on 6/23. Tomorrow is Juneteenth (closed) — no new data until Mon 6/22.

### 6/18 Run + Integrity

24 signals (rows 528–551), all HOLD / risk APPROVED, every ticker/account/confidence/DQ matched to `signals\_2026-06-18.log`. **No near-misses** — VTI and NVDA scouts both at 58%, below the band. Recalc clean: **0 errors / 8,592 formulas**. Totals reconcile — **547 signals** (451 Phase 2 + 96 across 6/15–18), **BUY 19** (unchanged). Three cohorts resolved today: 6/11 +5d, 6/4 +10d, 5/20 +20d.

> ANALYST NOTE: Sub-cent prices now run two sessions (6/17 + 6/18) — e.g., JPM $332.5063, VTI $369.3401 — so the higher-precision capture is the new standard, not a one-off. Several DQ values shifted vs 6/17 (AIQ HIGH→MEDIUM, DOW MEDIUM→HIGH, WMT/XLU HIGH→MEDIUM); normal day-to-day news-availability variation, not drift.

### Third +20d Cohort (5/20) — Magnitude Growth 3-for-3

|Cohort|abs move +5d → +10d → +20d|+20d avg ret|
|-|-|-|
|5/18|4.51 → 5.69 → 6.72%|−1.96%|
|5/19|5.25 → 6.09 → 7.17%|−2.43%|
|5/20|5.54 → 6.28 → **7.09%**|**−3.09%**|

5/20's absolute move grows monotonically like the first two — the magnitude finding now holds across **all three matured +20d cohorts (3-for-3)**, extending the 8/9 Phase 2 +10d result cleanly to the 20-day horizon.

> ANALYST NOTE: The +20d direction is net negative in all three and deepening (−1.96 → −2.43 → −3.09%), but the three +20d windows overlap and all close in the mid-June trough (6/16–6/18) — this is largely the same drawdown read from three near-adjacent start points, not three independent directional signals. The robust, in-scope finding is magnitude; the directional drift is a market-state artifact and should not be over-read. Same implication as the +10d work: HOLD's predictive window is \~5 days and the move keeps compounding past it.

### 6/11 Phase 2 Cohort +5d — Pattern NO; Section 1 Nearly Matured

6/11's +5d resolved: Section 1 row 23 populated at **50-59% = 50.0% (n=12)** — did not clear both neighbours, Pattern **NO**. The across-cohort tally is now **10 of 18 hold**. **6/12 is the last Phase 2 cohort still pending +5d** (resolves \~6/22 after Juneteenth); once it lands, Section 1 is fully matured. This does not touch the certified aggregate — the GO/NO-GO guardrail is the band hit rate, not the per-cohort count.

### Near-Miss Registry Backfilled — 11 → 19 (KEEP-70 Firmed)

Closed the standing backfill item by **regenerating the registry from the Signals tab** via `build\_near\_miss\_registry.py` (the source-of-truth auto-gen tool), rather than hand-patching the drifted tab. All 17 Phase 2 BUYs are scout/SCHD signals in the 0.62–0.68 band (every Phase 2 BUY is a near-miss); the old tab held 9 of them plus the two 6/16 Phase 3-A entries. The regenerated tab is **19 rows, date-sorted, 7 LOCKED (≤6/1) + 12 EXTENDED (>6/1)**, with three corrections the auto-gen caught:

* the genuine **6/2 NVDA @ $227.93** (−8.66% +5d, NO) is now included — it had been missing entirely;
* the **6/3 GLD / 6/3 NVDA** pair is correctly dated 6/3 (was mis-labelled 6/2), and 6/3 NVDA's confidence corrected to **0.66** (the Signals value);
* **6/16 NVDA** confidence corrected **0.68 → 0.65** — a hand-entry error the old tab carried.

Stats (closing prices, sourced from Signals): **LOCKED +5d 4/7 = 57.1%** (the immutable Q2 verdict basis, avg −0.90% — matches the frozen baseline), **LOCKED +10d now 1/7 = 14.3%** (avg −3.02%); **EXTENDED +5d 3/8 = 37.5%** (avg −3.01%), +10d 0/4 (avg −5.11%); **combined +5d 7/15 = 46.7%**. KEEP 70% is firmer than ever — near-miss BUYs convert below a coin flip at +5d and worse at +10d.

> ANALYST NOTE: The self-validation surfaced a real change — \*\*LOCKED +10d moved from the frozen 1/6 to 1/7\*\* because 6/1's +10d resolved NO \*after\* the Q2 baseline was frozen (its +5d, the actual verdict basis, is untouched). The frozen `LOCKED\_BASELINE\['comp10']` is now stale-by-one; the +10d portion is informational, not the invariant. Separately, `build\_near\_miss\_registry.py --emit-master-copy` had a cross-workbook style bug (`nc.\_style = c.\_style` copies a StyleArray \*index\*, which points into the source workbook's number-format table and scrambles in the destination — symptom: price cells rendered as 1900 dates). Fixed to copy style \*attributes\* (number\_format string + copied font/fill/border/alignment) plus merge ranges. The standalone `near\_miss\_registry.xlsx` was always correct; only the master-copy was affected.

### Guardrail-Compression Trace

Built `guardrail\_trace.py` (h1–h4 mould: reads Signals, computes per-cohort and running-cumulative +5d band hit rates, prints a trajectory table, renders a chart). The cumulative 50-59% lead over 60-69%:

* built to a **peak +12.3pt at 6/1** (50-59% at 62.3%, 60-69% at 50.0%);
* **compressed through the early-June shock cohorts** — 6/2 and 6/3 came in at 30% / 36% per-cohort on the 50-59% band, pulling the cumulative down;
* has since **stabilised in the high-50s** (57.4 → 58.7% over the last seven cohorts) while 60-69% hovers 48–51%;
* currently **+7.4pt** (50-59% 58.7%, 60-69% 51.3%, 40-49% 44.8%).

> ANALYST NOTE: The certified \*\*61.3%\*\* is exactly the cumulative 50-59% rate \*\*at 5/29\*\* — i.e., the n=216 snapshot was the pre-shock window. The "61.3 → 58.7" drift is therefore the early-June shock cohorts dragging the cumulative down from its peak, not a steady erosion. The lead gap narrowed from its peak (+12.3 → +7.4pt) but is not trending toward crossover — the band ordering holds with comfortable margin and the 50-59% line has flattened. Watch metric, not an alarm: the 60-69% band's per-cohort n is small (3–6) and noisy, so a few strong small-n cohorts can move the gap.

### H1 Live-Readiness (Dry-Run)

Dry-ran the real `h1\_lag\_trace.py` against the current tracker (WMT). It runs clean and **ingests the Phase 3-A rows** — 6/12 and 6/15–18 appear in the trace with confidence + trailing-5d move, forward returns blank (pending +5d). It reproduces the Phase 2 baseline: **estimated update lag = 5 sessions** (corr(conf, trailing-move\[t−L]) peaks +0.638 at L=5; −0.177 at L=0 — the lag signature), the WMT +10d arc **−15.19 → −1.66** (self-corrected), and the calibration guardrail with 50-59% leading (**61.3%**, the certified n=216 reference — distinct from the live 58.7% above; different scope, both correct). Verdict: harness is wired and ready.

> ANALYST NOTE — 6/23 runbook: once the 6/15 +5d resolves (\~Mon 6/23), re-run `python h1\_lag\_trace.py --tracker claude\_equity\_bot\_tracker.xlsx --ticker WMT --out-dir viz` on the full tracker — the 6/15–18 WMT rows begin populating forward returns. H1 success = the lag estimate shrinks from \~5 toward 0–1 sessions and corr(conf, trailing-move) rises from −0.177, \*\*without\*\* degrading the 50-59% +5d lead. Per-ticker n is small (\~19 cohorts), so the Phase 3-A lag estimate stabilises only after \~1–2 weeks of resolutions; the 6/23 run is the first end-to-end proof on live data, with the real comparison maturing through early July.

\---

## 2026-06-22 — Phase 3-A Day 5: Magnitude Growth 4-for-4 at +20d; Section 1 Closed Out (6/12 Holds); Guardrail Lead Widens to +8.2pt

**Phase:** 3-A (advisory-only), Day 5
**Status:** First session after Juneteenth. 6/22 run captured (24/24 HOLD, clean — no near-misses). The day's outcomes: 5/21's +20d makes magnitude growth **4-for-4**, and 6/12's +5d (the last Phase 2 cohort) **holds the 50-59% pattern**, fully maturing Section 1 at 11 of 19. The strong 6/12 cohort widened the guardrail lead back to **+8.2pt**, reversing last week's compression. The near-miss registry was refreshed (both 6/12 near-misses hit +5d) and the Guardrail Trace sheet extended to 6/12. Phase 3-A's own +5d is still pending — the first live cohort (6/15) resolves **tomorrow, 6/23**.

### 6/22 Run + Integrity

24 signals (rows 552–575), all HOLD / risk APPROVED, every ticker/account/confidence/DQ matched to `signals\_2026-06-22.log`. **No near-misses** — VTI 58%, NVDA 55%, both below the band; PWR 63% is in-band but a HOLD, not a BUY. Recalc clean: **0 errors / 8,634 formulas**. Totals reconcile — **571 signals** (451 Phase 2 + 120 across 6/15–22), **BUY 19** (unchanged). Three cohorts resolved: 6/12 +5d, 6/5 +10d, 5/21 +20d.

> ANALYST NOTE: Confidence drift worth watching — DOW eased to 38% (from 42%) and GM to 58% (from 62%), while PM rose to 65% and PWR to 63% (its first appearance in the 60-69 band, as a HOLD). The DQ shift (NTR HIGH→MEDIUM) is the usual day-to-day news-availability variation.

### +20d Magnitude Growth — 4-for-4 (5/21)

|Cohort|abs move +5d → +10d → +20d|+20d avg ret|
|-|-|-|
|5/18|4.51 → 5.69 → 6.72%|−1.96%|
|5/19|5.25 → 6.09 → 7.17%|−2.43%|
|5/20|5.54 → 6.28 → 7.09%|−3.09%|
|5/21|5.05 → 5.18 → **6.55%**|**−3.36%**|

5/21 grows monotonically, taking the +20d magnitude tally to **4-for-4** — but its +5d→+10d step is the shallowest of the four (5.05 → 5.18, nearly flat), with most of the growth back-loaded into the +10d→+20d window. The +20d direction keeps deepening (−1.96 → −2.43 → −3.09 → −3.36%); same caveat as before — these four +20d windows overlap and all close in the mid-June trough (5/21's ends 6/22), so it is largely one drawdown read from four near-adjacent start points, not four independent directional signals.

### Section 1 Closed Out — 6/12 Holds the Pattern

6/12's +5d resolved (the last Phase 2 cohort): Section 1 row 24 populated at **50-59% = 60.0% (n=10)**, clearing both neighbours, Pattern **✓ YES**. Across-cohort final tally: **11 of 19 cohorts hold** (up from 10 of 18). **Section 1 is now fully matured** — every Phase 2 cohort (5/18 → 6/12) has +5d data. The per-cohort count (11/19 ≈ 58% individually hold) is supplementary; the certified guardrail is the aggregate band rate below, which governs GO/NO-GO.

### Guardrail Lead Widens to +8.2pt — Compression Reversed

Live +5d bands: 50-59% **58.8%** (127/216) > 60-69% 50.6% (41/81) > 40-49% 45.0% (63/140). The 50-59 lead over 60-69 is now **+8.2pt**, up from +7.4pt on 6/11 — the strong 6/12 cohort (50-59 at 60% per-cohort) nudged the cumulative 50-59 up and 60-69 down. This confirms last week's read: the 61.3 → 58.7 drift was stabilisation, not a crossover trend; the lead gap over the last three cohorts is roughly flat (+8.6 → +8.2pt). The `guardrail\_trace.py` trajectory and the embedded **Guardrail Trace** sheet were refreshed through 6/12.

### Near-Miss Registry Refreshed — EXTENDED +5d to 5/10

Regenerated from the updated Signals tab (the two 6/12 near-misses and 6/5's +10d had resolved since the 6/18 build): **EXTENDED +5d 3/8 → 5/10 = 50.0%** (both 6/12 near-misses hit — NVDA +1.48%, VTI +0.87%), avg −2.2%; **+10d completed 4 → 5** (6/5 NVDA). LOCKED is unchanged at **4/7 = 57.1%** (immutable Q2 basis). **Combined +5d now 9/17 = 52.9%** (up from 46.7%).

> ANALYST NOTE: The combined near-miss hit rate ticked above a coin flip (52.9%), but \*\*KEEP 70% holds\*\* — and the reason is EV, not hit rate: average returns stay negative (LOCKED −0.90%, EXTENDED −2.2%), so lowering the threshold would still buy into net-negative-expectancy trades. The 6/12 pair won small (+1.48%, +0.87%); the cohort's losers lose more than its winners win. The verdict logic (anchored on the locked cohort + the negative average) auto-confirms KEEP 70%.

### Phase 3-A — First Live +5d Tomorrow

All five Phase 3-A blocks (6/15–22) are still 0/24 on +5d. The first live cohort, **6/15, resolves tomorrow (6/23)** — the first data point measured against the 50-59% guardrail in live advisory mode, and the trigger to re-run `h1\_lag\_trace.py` to begin the lag-compression comparison.

\---

## 2026-06-23 — Phase 3-A Day 6: First Live Cohort (6/15) Does NOT Hold the Guardrail; H1 Lag Unchanged; 5/22 the +20d Magnitude Exception

**Phase:** 3-A (advisory-only), Day 6
**Status:** The first live calibration day. 6/15's +5d resolved — and the 50-59% guardrail **did not hold out-of-sample**: the band came in at 40% (n=15), below 60-69% (50%), inverting the Phase 2 ordering on the cohort. n=24 (one cohort), so this is the expected single-cohort noise, not a verdict — the aggregate still leads (+7.0pt), and the next live cohorts (6/16–22) resolve over the coming sessions. H1's lag read is unchanged at 5 sessions (one quiet WMT cohort). 5/22's +20d confirms it as the magnitude exception (non-monotonic). Registry EXTENDED +10d ticked to 6; KEEP 70% holds.

### 6/23 Run + Integrity

The three resolutions are entered in full — **6/15 +5d, 6/8 +10d, 5/22 +20d**, each 24/24 with Was-Right computed. Recalc clean: **0 errors / 8,637 formulas**. Totals **595 signals** (451 Phase 2 + 144 across six Phase 3-A blocks), **BUY 19** (unchanged). The 6/23 morning block (rows 576–599) cross-checks **clean** against `signals\_2026-06-23.log` — all 24 signals reconcile on ticker, signal, confidence, data-quality, and price@signal; the five scouts carry the log's `\[—] \[SCOUT]` tag (= tracker "Scout"), and the block is **24/24 HOLD** (BUY total unchanged at 19). It has no +5d yet, so it does not bear on today's outcomes.

### First Live Guardrail — the 6/15 Cohort Does NOT Hold

Section 4 row 53 (6/15, the first Phase 3-A cohort): **50-59% = 40.0% (n=15), Pattern NO**. On the cohort the bands inverted — **40-49% 50% (1/2) = 60-69% 50% (3/6) > 50-59% 40% (6/15)** — so the 50-59 band was the *lowest* of the three labeled bands (DOW at 38% books in the separate 0-39% band). The 50-59 band did not lead out-of-sample on day one.

Cumulatively (Phase 2 + this cohort), the band still leads but the margin narrowed: **50-59% 57.6% > 60-69% 50.6% > 40-49% 45.1%**, lead **+7.0pt** — down from +8.2pt at 6/12, as the weak 6/15 cohort pulled the cumulative 50-59 down (drift from the certified 61.3% is now −3.7pt). The Guardrail Trace sheet now carries 6/15 as its first Phase 3-A point.

> ANALYST NOTE: \*\*This is n=24 — one cohort — so a single inversion is the expected noise, not a failure.\*\* Phase 2's guardrail was certified on n=216; a 24-name cohort at 40% is well within sampling variation. The signal to watch is not this point but the \*trend\* as 6/16–22 resolve over the next several sessions: if live cohorts keep landing below their Phase 2 band rates, that points to Phase 2 overfitting (the 50-59 lead was partly in-sample); if 6/15 is an outlier and the next few recover, the guardrail generalises. One cohort decides nothing. It remains advisory-only — nothing here is a trade signal, only a calibration read.

### H1 First Live Read — Lag Unchanged at 5 Sessions

WMT's 6/15 +5d came in at **−0.73%** (YES — within the ±3% HOLD band; a quiet, correct HOLD). The lag scan is essentially unchanged: **estimated lag still 5 sessions** (peak r +0.576 at L=5, vs +0.638 in the Phase 2 baseline), corr(conf, trailing-move) still −0.177. No improvement yet — expected, since one quiet cohort cannot move a per-ticker estimate built on \~19 cohorts. H1's read matures only as more live cohorts (and more adverse-move days) accrue; the harness ingests the live row cleanly.

### 5/22 +20d — The Magnitude Exception Confirmed

5/22's +20d completes its trajectory: |move| **4.52 → 4.09 → 5.93%** — the +20d level exceeds the +5d level (net growth, so the move-keeps-compounding finding holds 5-for-5 on net), but the path is **non-monotonic**: the move *shrank* +5d→+10d (4.52 → 4.09) before growing to +20d. This is the same cohort that was the lone +5d→+10d magnitude exception at Phase 2 close (8/9 grew; 5/22 did not), so monotonic +20d growth is **4-for-5**, with 5/22 the consistent exception. +20d direction −4.58%, the deepest yet (−1.96 → −2.43 → −3.09 → −3.36 → −4.58%) — same overlapping-mid-June-window caveat (5/22's +20d window ends on the 6/23 close).

### Near-Miss / Registry — EXTENDED +10d to 6

6/8 NVDA's +10d resolved at **−4.01% (NO)**, taking EXTENDED **+10d completed 5 → 6**. The +5d stats are unchanged (next near-miss +5d is 6/16's pair on 6/24); combined +5d holds at **9/17 = 52.9%**. LOCKED unchanged (4/7); **VERDICT KEEP 70%**.

\---

## 2026-06-24 — Phase 3-A Day 7: Second Live Cohort (6/16) Also Doesn't Hold — But It's a Down-Regime Cohort; Relative Ordering Holds While Absolute Calibration Slides

**Phase:** 3-A (advisory-only), Day 7
**Status:** The second live cohort resolved, and the picture is genuinely split. **Per-cohort**, 6/16 also failed to show 50-59% leading (30%, n=10) — but its guardrail bands are flat-low (50-59% 30% ≈ 60-69% 27%; 40-49% is a lone name) with every near-miss deeply negative, marking it a **down-regime cohort** where no band could separate. **Cumulatively**, the *relative* claim is holding and stable: 50-59% 56.4% > 60-69% 48.0%, lead +8.5pt (+7→+8.5 across both live cohorts). But the *absolute* level is drifting: −4.9pt below the certified 61.3%, with both live cohorts landing under Phase 2 — the single-regime caveat surfacing out-of-sample. H1's lag holds at 5; 5/26's +20d is cleanly monotonic (magnitude 5-for-6); registry EXTENDED +5d slips to 5/12 and KEEP 70% is reinforced.

### 6/24 Run + Integrity

This morning's 24 signals **cross-validate clean** against `signals\_2026-06-24.log` — ticker set, signal, confidence, data-quality, and price@signal all reconcile (the five scouts carry the log's `\[—] \[SCOUT]` tag = tracker "Scout"); the block (rows 600–623) is **24/24 HOLD**. The three resolutions — **6/16 +5d, 6/9 +10d, 5/26 +20d** — are entered in full (24/24 each, Was-Right computed). Recalc clean: **0 errors / 8,637 formulas**. Totals **619 signals**, **BUY 19** (unchanged — no new BUYs).

### Second Live Cohort — 6/16 Also Doesn't Hold, But Read the Regime

Section 4 row 54 (6/16): **50-59% = 30.0% (n=10), Pattern NO**. On the cohort the two guardrail bands are flat and low — **50-59% 30% (3/10), 60-69% 27% (3/11)** (40-49% is a single name, CORN, 1/1; the 0.38 CBRS/DOW book in the separate 0-39% band) — and all three near-misses resolved deeply negative (VTI −2.28%, NVDA −4.84%, 6/9 NVDA −4.05%). That signature — the guardrail bands \~30%, near-misses sharply down — says the 5 sessions after 6/16 fell broadly. In a directional down move, signals expecting stability are wrong regardless of confidence, so the bands can't separate. This is **less a calibration read than a regime read**.

### Correction — 40-49% band binning (caught building the scoreboard)

Building the Live Cohort Scoreboard surfaced a binning error in the per-cohort **40-49%** figures for 6/15 (in the 6/23 entry) and 6/16 (above), both now corrected. The daily hand-profiles had used `conf < 0.50`, which swept the **sub-40% names** (CBRS / CORN / DOW at 38%) into the 40-49% bucket. The tracker books those in its **separate 0-39% band** (Dashboard r32), and the literal `\[40%, 50%)` band the harness uses matches the tracker exactly — cumulative 40-49% = 65/143 = **45.5%**, identical to Dashboard r33. Corrected per-cohort 40-49%: **6/15 = 1/2 (50%)**, **6/16 = 1/1 (100%, CORN only)**.

> ANALYST NOTE: this touches only the auxiliary 40-49% band. The \*\*50-59% and 60-69% bands — the actual guardrail — were computed correctly throughout\*\*, so every conclusion stands (6/15 inverted with 50-59 the lowest labeled band; 6/16 compressed; cumulative 50-59 > 60-69 at +8.5pt). The scoreboard is now the source of truth for per-cohort bands; any Phase 2 per-cohort 40-49 cells built with the loose binning warrant the same `\[40%,50%)` pass separately.

### Relative vs Absolute — the Distinction That Matters Now

Two cohorts in, the live guardrail splits into two questions:

|Lens|Reading|Trend|
|-|-|-|
|**Relative** (does 50-59 lead 60-69?)|cumulative 50-59% **56.4%** > 60-69% 48.0%|lead **+8.5pt**, stable (+7.0 at 6/15 → +8.5 at 6/16) — **holding**|
|**Absolute** (is 50-59 near its 61.3% certified rate?)|50-59% **56.4%** vs 61.3%|drift **−4.9pt**, both live cohorts below Phase 2 — **sliding**|

Per-cohort 50-59%: 6/15 **40%** (n=15), 6/16 **30%** (n=10) — both below the Phase 2 band rate, both in weak tape.

> ANALYST NOTE: \*\*The ranking is holding; the absolute level is not — and both live cohorts landed in a down move.\*\* That pattern points to \*regime sensitivity\* (exactly the single-regime caveat Phase 2 flagged) rather than a broken ranking: when forward returns are broadly negative, every band's hit rate compresses toward (and below) 50%, but 50-59 still edges 60-69 because the higher-confidence calls overshoot hardest into the decline. The clean test is still ahead — \*\*a cohort that resolves into stable or rising tape.\*\* If 50-59 keeps leading \*and\* the absolute level recovers when the market isn't falling, the guardrail generalises; if the absolute level stays depressed across regimes, Phase 2's 61.3% was regime-luck. Two cohorts decide neither. Advisory-only throughout — a calibration read, not a trade signal.

### H1 — Lag Still 5 Sessions

WMT's 6/16 +5d came in at **−2.50%** (YES — within the ±3% HOLD band, though a larger move than 6/15's −0.73%, consistent with the broad decline). Lag scan essentially unchanged: **estimated lag still 5 sessions** (peak r +0.595, vs +0.576 at 6/15 and +0.638 baseline), corr(conf, trailing) −0.173. Two live cohorts remain too few to move a per-ticker estimate; the harness ingests both live rows cleanly.

### 5/26 +20d — Monotonic; Magnitude 5-for-6

5/26's trajectory is clean: |move| **2.92 → 4.47 → 7.46%** — fully monotonic. That takes the +20d magnitude-growth tally to **5-for-6 monotonic**, with 5/22 still the lone exception (the +5d→+10d dip). +20d direction **−6.40%**, deeper than 5/22's −4.58% — the same overlapping-window caveat, as every late-May cohort's +20d window now closes inside the mid-to-late-June decline, so the deepening is regime, not signal.

### Near-Miss / Registry — EXTENDED +5d 5/12; KEEP 70% Reinforced

All three near-miss resolutions today were NO: 6/16 VTI (−2.28%) and NVDA (−4.84%) at +5d, and 6/9 NVDA (−4.05%) at +10d. EXTENDED **+5d slips to 5/12 = 41.7%** (from 5/10), **+10d completed 7**, avg +5d −2.4%. Combined +5d **9/19 = 47.4%** (from 52.9%). LOCKED unchanged (4/7). The 60-69% BUYs keep underperforming into the decline — **VERDICT KEEP 70%, reinforced**.

\---

## 2026-06-25 — Phase 3-A Day 8: Third Live Cohort (6/17) Goes Against the Guardrail — and It's NOT Compressed; the Lead Narrows to +5.5pt

**Phase:** 3-A (advisory-only), Day 8
**Status:** The clean test arrived and it cut the wrong way. 6/17 is the first live cohort that wasn't return-compressed (cohort-wide hit 50%, regime *mixed* not *compressed*) — so its bands had room to separate — and **60-69% separated decisively above 50-59%: 75% (6/8) vs 38.5% (5/13)**. Pairwise, the guardrail has now held on just **1 of 3** live cohorts, and that one (6/16) was compressed noise. The cumulative 50-59 lead **narrowed +8.5 → +5.5pt** in a single cohort. The framing has to move: yesterday's "ranking holds, the slide is regime sensitivity" no longer fits, because the cohort with the *least* regime distortion is the one that most clearly favored 60-69. H1's lag holds at 5 (WMT's first live miss); 5/27's +20d is monotonic (magnitude 6-for-7); registry unchanged.

### 6/25 Run + Integrity

This morning's 24 signals cross-validate **23/24 clean** against `signals\_2026-06-25.log` (all HOLD, rows 624–647). **One catch:** GLD's price@signal reads **368** in the tracker vs **368.775** in the log — a 0.21% gap on the entry base, almost certainly a paste truncation. It doesn't affect any resolution today (GLD is a 6/25 HOLD that resolves \~7/2), but it should be corrected to **368.775** before GLD's +5d computes, or its forward returns run off a wrong base. The three resolutions — **6/17 +5d, 6/10 +10d, 5/27 +20d** — are entered in full (24/24 each, Was-Right computed). Recalc clean: **0 errors / 8,637 formulas**. Totals **643 signals**, **BUY 19** (unchanged).

### Third Live Cohort — 6/17 Goes Against the Guardrail, in a Regime That Could Separate

Section 4 row 55 (6/17): **50-59% = 38.5% (n=13), Pattern NO**. The band order is the story:

**60-69% 75% (6/8) > 50-59% 38% (5/13) > 40-49% 33% (1/3)** — cohort-wide hit **50%**, regime **mixed**.

This is categorically different from 6/15 and 6/16. Those were weak-tape cohorts (42% and 29% cohort-wide) where every band compressed toward \~30-40% and the ordering carried little information. 6/17 hit 50% cohort-wide — the bands had room to spread — and they did, with **60-69 nearly double 50-59**. The 60-69 names here were all HOLDs that stayed tight (6 of 8 within ±3%), while the 50-59 HOLDs moved more (only 5 of 13 within band). When confidence actually separated outcomes this cohort, it separated them the *opposite* way to the Phase 2 claim.

### The Guardrail Is Now Under Real Pressure — Updated Read

|Live cohort|50-59% (n)|Held (50-59>60-69)|Cohort band order (by hit, n)|Cum lead|Regime|
|-|-|-|-|-|-|
|6/15|40% (15)|NO|40-49 50%(2) = 60-69 50%(6) > 50-59 40%(15)|+7.0pt|mixed|
|6/16|30% (10)|YES|40-49 100%(1) > 50-59 30%(10) > 60-69 27%(11)|+8.5pt|compressed|
|6/17|38% (13)|**NO**|**60-69 75%(8)** > 50-59 38%(13) > 40-49 33%(3)|**+5.5pt**|mixed|

Cumulative through 6/17: 50-59% **55.5%** > 60-69% **50.0%**, lead **+5.5pt** (harness trend label: *narrowing*, +7.0 → +5.5pt). Absolute drift **−5.8pt** from certified 61.3%. **Pairwise held: 1 of 3.**

> ANALYST NOTE: \*\*the regime flag is what makes this read sharp.\*\* Of the three live cohorts, the only one where 50-59 "held" pairwise (6/16) is flagged \*compressed\* — a 30% vs 27% edge inside a cohort where nothing separated, i.e. noise. The two cohorts with room to separate (6/15 mixed, 6/17 mixed) both went to 60-69, and 6/17 went there hard. So the live signal isn't "50-59 leads with regime noise around it" — it's closer to "\*\*when confidence separates outcomes at all, it has so far favored 60-69, not 50-59.\*\*" That is the opposite of the Phase 2 guardrail. It is \*\*not yet a refutation\*\*: three cohorts, and 6/17's 60-69 cell is n=8 (6/8 → wide error bars; a single different outcome moves it \~12pt). But the burden has flipped — the guardrail now has to \*re-earn\* confidence from the upcoming non-compressed cohorts, rather than being assumed to hold through the down-regime noise. The next two mixed/clean cohorts (6/18, 6/22) are decisive. Advisory-only throughout — this is a live calibration check doing exactly what Phase 3-A was built to do, not a trade signal.

### H1 — Lag Still 5; First Live WMT Miss

WMT's 6/17 +5d came in at **−3.51% (NO)** — its first miss in the live cohorts (6/15 −0.73% YES, 6/16 −2.50% YES, 6/17 −3.51% NO), the move finally clearing the ±3% HOLD band as the decline deepened. Lag scan unchanged: **estimated lag still 5 sessions** (peak r +0.600, edging up from +0.595/+0.576 over the prior two cohorts), corr(conf, trailing) −0.172. Three live cohorts, lag steady at 5 — consistent, though still a per-ticker read that wants more names before it firms.

### 5/27 +20d — Monotonic; Magnitude 6-for-7

5/27's trajectory is clean: |move| **2.67 → 5.16 → 7.67%** — monotonic. The +20d magnitude-growth tally is now **6-for-7 monotonic**, 5/22 still the lone exception. +20d direction **−5.99%** — the same overlapping-window caveat (every late-May cohort's +20d window now closes inside the mid-to-late-June decline), so the depth is regime, not signal.

### Near-Miss / Registry — Unchanged

No near-miss BUYs resolved on 6/25 (neither the 6/17 nor the 6/10 cohort carried a 60-69% BUY). Registry holds: EXTENDED **+5d 5/12 = 41.7%, +10d 7**, avg +5d −2.4%; LOCKED 4/7; combined +5d 9/19 = 47.4%. **VERDICT KEEP 70%**, unchanged.

\---

## 2026-06-26 — Phase 3-A Day 9: 6/18 Is the Second Straight Non-Compressed Cohort to Favor 60-69 — the Guardrail Is Now Fairly Clearly Not Holding Out-of-Sample

**Phase:** 3-A (advisory-only), Day 9
**Status:** The pattern has firmed from "under pressure" to a consistent signal. 6/18 — cohort-wide hit 54%, room to separate — had **60-69% at 83% (5/6) beat 50-59% at 64% (7/11)**, the second non-compressed cohort in a row to do so. Across all four live cohorts, **every cohort that could separate (6/15, 6/17, 6/18) favored 60-69**; the only pairwise "held" (6/16) is flagged compressed noise. The cumulative lead has compressed **+8.5 → +4.1pt**, now below the entire Phase 2 +7–13pt range, driven by 60-69 climbing 48 → 52%. The honest call: the Phase 2 Q1 inversion (50-59 leads 60-69) is not reproducing out-of-sample, and it's time to plan a formal re-examination. H1 lag holds at 5 (WMT back to a hit); 5/28 +20d monotonic; registry EXTENDED +10d to 8.

### 6/26 Run + Integrity

This morning's 24 signals cross-validate **24/24 clean** against `signals\_2026-06-26.log`. Two notable items: the block carries the **first SELL signal of the live run — CBRS, 68%** (advisory-only, resolves \~7/6; CBRS had previously only appeared at 38% in the 0-39% band, so both its confidence and its direction shifted). And the **GLD fix half-landed**: price@signal now reads **367.775** vs the log's **368.775** — the decimals are right but the dollars are off by one; it still needs **368.775**. The three resolutions (6/18 +5d, 6/11 +10d, 5/28 +20d) are entered in full (24/24 each); recalc clean: **0 errors / 8,637 formulas**. Totals **667 signals**, **BUY 19**.

### Fourth Live Cohort — 6/18 Favors 60-69, in a Regime That Could Separate

Section 4 row 56 (6/18): **50-59% = 63.6% (n=11), Pattern NO**. The band order:

**60-69% 83% (5/6) > 50-59% 64% (7/11) > 40-49% 14% (1/7)** — cohort-wide **54%**, regime mixed.

This is the important nuance: **50-59 did well here in absolute terms** — 63.6% is above its certified 61.3% snapshot. It's not that 50-59 is failing; it's that on this cohort 60-69 did even better (83%). Same shape as 6/17 (60-69 75% vs 50-59 38.5%), now at a higher overall hit level. Two clean cohorts, same direction.

### The Guardrail Is Not Holding Out-of-Sample — the Pattern Is Now Consistent

|Live cohort|50-59% (n)|Held (50-59>60-69)|Cohort band order (by hit, n)|Cum lead|Regime|
|-|-|-|-|-|-|
|6/15|40% (15)|NO|40-49 50%(2) = 60-69 50%(6) > 50-59 40%(15)|+7.0pt|mixed|
|6/16|30% (10)|YES|40-49 100%(1) > 50-59 30%(10) > 60-69 27%(11)|+8.5pt|compressed|
|6/17|38% (13)|NO|60-69 75%(8) > 50-59 38%(13) > 40-49 33%(3)|+5.5pt|mixed|
|6/18|64% (11)|NO|**60-69 83%(6)** > 50-59 64%(11) > 40-49 14%(7)|**+4.1pt**|mixed|

Cumulative through 6/18: 50-59% **55.8%** > 60-69% **51.8%**, lead **+4.1pt** (harness: *narrowing*, +8.5 → +4.1pt). Drift **−5.5pt** from 61.3%. **Pairwise held: 1 of 4** — and that one is compressed.

> ANALYST NOTE: this is no longer "wait and see." \*\*Zero of the three non-compressed live cohorts support the guardrail\*\* — every cohort with room to separate put 60-69 above 50-59, two of them decisively. The cumulative lead has fallen below the entire Phase 2 range (+7 to +13pt over two months) to +4.1pt, and the narrowing is driven by \*\*60-69 rising\*\* (48 → 50 → 52%) as the clean cohorts resolve, not by 50-59 collapsing. The natural reading: the Phase 2 Q1 finding — that mid-confidence 50-59 is \*better\* calibrated than higher-confidence 60-69, a counterintuitive inversion — was likely \*\*regime-specific or overfit\*\*, and out-of-sample the conventional ordering (more confidence → more accuracy) is what holds. \*\*Recommendation: plan a formal re-examination of the Q1 certification.\*\* Caveats kept honest: four cohorts; per-cohort 60-69 n is small (6/18 n=6, 6/17 n=8); the cumulative lead is still positive (+4.1pt), not a completed crossover; and 6/22 is the next non-compressed read, worth having as confirmation. But the direction is now unambiguous. Worth stating plainly: \*\*this is exactly what Phase 3-A was built to catch\*\* — a certified finding that doesn't generalize, surfaced in advisory-only mode before a dollar was ever staked on it. The phase gate did its job. Advisory-only throughout.

### H1 — Lag Still 5; WMT Back to a Hit

WMT's 6/18 +5d came in at **−1.53% (YES)** — back inside the ±3% band after the 6/17 miss (live WMT now 3 of 4: 6/15 Y, 6/16 Y, 6/17 N, 6/18 Y). Lag scan unchanged: **estimated lag still 5 sessions** (peak r +0.599), corr(conf, trailing) −0.181. Four live cohorts, lag steady at 5 — a consistent per-ticker read.

### 5/28 +20d — Monotonic; Magnitude 7-for-8

5/28's trajectory: |move| **3.28 → 4.69 → 7.27%** — monotonic. The +20d magnitude-growth tally is now **7-for-8 monotonic**, 5/22 still the lone exception. +20d direction **−5.41%** — same overlapping-window caveat (late-May +20d windows all close inside the mid-to-late-June decline).

### Near-Miss / Registry — EXTENDED +10d to 8

One near-miss resolved: 6/11 NVDA (65%) at +10d, **−3.71% (NO)** — EXTENDED **+10d completed → 8**. +5d unchanged at 5/12 = 41.7%; LOCKED 4/7; combined +5d 9/19 = 47.4%. Another higher-confidence near-miss into the red — **VERDICT KEEP 70%**, reinforced.

\---

## 2026-06-29 — Phase 3-A Day 10: Confirmation Read Confirms — 6/22 Favors 60-69 Again; the Q1 Guardrail Is Firmly Not Holding Out-of-Sample

**Phase:** 3-A (advisory-only), Day 10
**Status:** The confirmation read confirms. 6/22 — cohort-wide 50%, room to separate — had **60-69% at 66.7% (4/6) beat 50-59% at 54.5% (6/11)**, the fourth non-compressed cohort in a row to favor 60-69. That makes **4 of 4 separable live cohorts** putting 60-69 above 50-59; pairwise held just **1 of 5**, and that one (6/16) is compressed noise. The cumulative lead is down to **+3.3pt** (from the +8.5 peak), below the entire Phase 2 +7–13pt range and still narrowing, driven by 60-69 climbing to 52.5%. The trigger I set Friday is met: **proceed with the regime-stratified Q1 re-examination.** GLD is fixed; H1 lag holds at 5 (WMT back to a hit); 5/29 +20d monotonic; registry EXTENDED +10d to 10.

### 6/29 Run + Integrity

This morning's 24 signals cross-validate **24/24 clean** against `signals\_2026-06-29.log` (all HOLD, rows 672–695). **GLD is now correct** — price@signal reads **368.775**, matching the log (resolves clean on 7/2). The three resolutions (6/22 +5d, 6/12 +10d, 5/29 +20d) are entered in full (24/24 each); recalc clean: **0 errors / 8,637 formulas**. Totals **691 signals**, **BUY 19**.

### Confirmation Read — 6/22 Favors 60-69 Again

Section 4 row 57 (6/22): **50-59% = 54.5% (n=11), Pattern NO**. The band order:

**60-69% 66.7% (4/6) > 50-59% 54.5% (6/11) > 40-49% 33% (2/6) > 0-39% 0% (0/1)** — cohort-wide **50%**, regime mixed.

Same direction as 6/17 and 6/18, at a more moderate margin. The 60-69 edge over 50-59 (66.7 vs 54.5) is narrower than 6/18's (83 vs 64) but unambiguous, and it's the fourth separable cohort running to put 60-69 on top.

### The Q1 Guardrail Is Not Holding Out-of-Sample — Confirmed

|Live cohort|50-59% (n)|Held (50-59>60-69)|Cohort band order (by hit, n)|Cum lead|Regime|
|-|-|-|-|-|-|
|6/15|40% (15)|NO|40-49 50%(2) = 60-69 50%(6) > 50-59 40%(15)|+7.0pt|mixed|
|6/16|30% (10)|YES|40-49 100%(1) > 50-59 30%(10) > 60-69 27%(11)|+8.5pt|compressed|
|6/17|38% (13)|NO|60-69 75%(8) > 50-59 38%(13) > 40-49 33%(3)|+5.5pt|mixed|
|6/18|64% (11)|NO|60-69 83%(6) > 50-59 64%(11) > 40-49 14%(7)|+4.1pt|mixed|
|6/22|55% (11)|NO|60-69 67%(6) > 50-59 55%(11) > 40-49 33%(6)|**+3.3pt**|mixed|

Cumulative through 6/22: 50-59% **55.8%** > 60-69% **52.5%**, lead **+3.3pt** (harness: *narrowing*, +5.5 → +3.3pt). Drift **−5.5pt** from 61.3%. **Pairwise held: 1 of 5.**

> ANALYST NOTE: the confirmation read confirms, and the conclusion is now firm enough to act on. \*\*Four of four separable live cohorts favor 60-69\*\*; the lone "held" is compressed noise; the cumulative lead has fallen from +8.5 to +3.3pt — below the entire Phase 2 two-month range — with 60-69 steadily climbing (48 → 50 → 52 → 52.5%) as clean cohorts resolve. The Phase 2 Q1 inversion (mid-confidence 50-59 \*better\* calibrated than higher-confidence 60-69) is not reproducing; out-of-sample the conventional ordering holds. \*\*Next step: run the regime-stratified Q1 re-examination\*\* — re-test 50-59 vs 60-69 across the full Phase 2 history split by the compressed/mixed/clean flag the scoreboard already computes. Working hypothesis: the Phase 2 inversion was concentrated in the compressed/down cohorts; if the 50-59 lead vanishes or flips in the \*clean\* Phase 2 cohorts, that explains the live failure mechanistically and tells us the guardrail was a regime artifact, not a calibration law. Honest caveats unchanged: per-cohort 60-69 n is small (6 on each recent cohort), and the cumulative lead is still positive (not a completed crossover) — but four independent cohorts plus a monotone-narrowing aggregate is robust enough to re-open the certification. \*\*This is the phase gate working exactly as intended\*\* — a GO/NO-GO finding shown not to generalize, in advisory-only mode, before any capital. Advisory-only throughout.

### H1 — Lag Still 5; WMT 4 of 5

WMT's 6/22 +5d came in at **−2.56% (YES)** — inside the ±3% band (live WMT now 4 of 5: 6/15 Y, 6/16 Y, 6/17 N, 6/18 Y, 6/22 Y). Lag scan unchanged: **estimated lag still 5 sessions** (peak r +0.594), corr(conf, trailing) −0.177. Five live cohorts, lag steady at 5 — a consistent per-ticker read across the whole live run.

### 5/29 +20d — Monotonic; Magnitude 8-for-9

5/29's trajectory: |move| **4.95 → 5.14 → 7.62%** — monotonic. The +20d magnitude-growth tally is now **8-for-9 monotonic**, 5/22 still the lone exception. +20d direction **−4.72%** — the late-May +20d windows continue to close inside the mid-to-late-June decline.

### Near-Miss / Registry — EXTENDED +10d to 10

Two near-misses resolved at +10d: 6/12 VTI (68%) **+0.41% (YES)** — a rare near-miss win, just positive — and 6/12 NVDA (62%) **−5.17% (NO)**. EXTENDED **+10d completed → 10**. +5d unchanged at 5/12 = 41.7%; LOCKED 4/7. The one win is marginal against another deep NVDA loss — **VERDICT KEEP 70%**, unchanged.

## 2026-06-30 — Phase 3-A Day 11: +10d Horizon Confirms the Reversal; Q1 Re-Examination Says It's NOT a Regime Artifact — Something Changed Between Phase 2 and Now

**Phase:** 3-A (advisory-only), Day 11
**Status:** Three results, the third a genuine surprise. (1) The **+10d horizon read confirms** — the 6/15 cohort has 60-69 above 50-59 at both +5d and +10d, the gap *wider* at +10d (67 vs 47). (2) **6/23 is the first clean live cohort** (75% cohort-wide) and still favors 60-69 (86 vs 80) — five non-compressed cohorts now, all the same way; cumulative lead down to +2.2pt. (3) The **regime-stratified Q1 re-examination refutes the regime-artifact hypothesis**: the Phase 2 50-59 lead held in *clean* cohorts too (+9.1pt), so it wasn't compression noise — it was a real Phase 2 feature that has since **reversed within the same regimes** live. The honest reframing: not "the guardrail was regime-luck," but "the 50-59>60-69 relationship genuinely flipped between Phase 2 and now." H1 lag holds at 5; 6/1 +20d non-monotonic (2nd exception).

### 6/30 Run + Integrity

This morning's 24 signals cross-validate **24/24 clean** against `signals\_2026-06-30.log` (all HOLD, rows 696–719). GLD holds correct at **368.775**. The three resolutions (6/23 +5d, 6/15 +10d, 6/1 +20d) are entered in full (24/24 each — 6/1's +20d is complete; an earlier 22/24 reading was a range-helper miscount, not a data gap); recalc clean: **0 errors / 8,637 formulas**. Totals **715 signals**, **BUY 19**.

### The +10d Horizon Read — Inversion Fails at Both Horizons

The question held for today: does the band pattern survive at +10d? For the 6/15 cohort:

|Band|+5d|+10d|
|-|-|-|
|50-59%|6/15 = 40%|7/15 = 47%|
|60-69%|3/6 = 50%|4/6 = 67%|

60-69 leads at **both** horizons, and the gap *widens* from +10pt (+5d) to +20pt (+10d). So the reversal isn't a +5d artifact — it persists, and strengthens, at the longer horizon. That materially supported running the re-examination.

### Sixth Live Cohort — 6/23 (First Clean Cohort) Still Favors 60-69

Section 4 row 58 (6/23): **50-59% = 80% (n=10), Pattern NO**. Band order: **60-69% 86% (6/7) > 50-59% 80% (10) > 40-49% 57% (4/7)** — cohort-wide **75%**, the first **clean** regime cohort of the live run. Even at high overall accuracy, 60-69 still edges 50-59. Five non-compressed live cohorts (6/15, 6/17, 6/18, 6/22, 6/23), all favoring 60-69; pairwise held **1 of 6**.

### Guardrail — Cumulative Lead Down to +2.2pt

|Live cohort|50-59% (n)|Held|Band order (by hit, n)|Cum lead|Regime|
|-|-|-|-|-|-|
|6/15|40% (15)|NO|40-49 50%(2) = 60-69 50%(6) > 50-59 40%(15)|+7.0pt|mixed|
|6/16|30% (10)|YES|40-49 100%(1) > 50-59 30%(10) > 60-69 27%(11)|+8.5pt|compressed|
|6/17|38% (13)|NO|60-69 75%(8) > 50-59 38%(13) > 40-49 33%(3)|+5.5pt|mixed|
|6/18|64% (11)|NO|60-69 83%(6) > 50-59 64%(11) > 40-49 14%(7)|+4.1pt|mixed|
|6/22|55% (11)|NO|60-69 67%(6) > 50-59 55%(11) > 40-49 33%(6)|+3.3pt|mixed|
|6/23|80% (10)|NO|60-69 86%(7) > 50-59 80%(10) > 40-49 57%(7)|**+2.2pt**|clean|

Cumulative: 50-59% **56.6%** > 60-69% **54.4%**, lead **+2.2pt** (narrowing, +4.1 → +2.2pt). Approaching crossover; 60-69 has climbed 48 → 54.4% over the live run.

### Phase 2 Q1 Re-Examination — the Lead Is NOT a Regime Artifact

Built `--stratify-regime` into the harness (regime\_stratification.md staged). Pooling 50-59 vs 60-69 +5d outcomes by regime, separately for the two phases:

**Phase 2 (certification period, 19 cohorts):**

|Regime|#coh|50-59% (h/n)|60-69% (h/n)|Lead|
|-|-|-|-|-|
|compressed|4|15/38 (39.5%)|5/18 (27.8%)|+11.7pt|
|mixed|8|52/92 (56.5%)|19/35 (54.3%)|+2.2pt|
|clean|7|60/86 (69.8%)|17/28 (60.7%)|**+9.1pt**|
|**ALL**|19|127/216 (58.8%)|41/81 (50.6%)|+8.2pt|

**Phase 3-A (live, 6 cohorts):**

|Regime|#coh|50-59% (h/n)|60-69% (h/n)|Lead|
|-|-|-|-|-|
|compressed|1|3/10 (30%)|3/11 (27.3%)|+2.7pt|
|mixed|4|24/50 (48%)|18/26 (69.2%)|**−21.2pt**|
|clean|1|8/10 (80%)|6/7 (85.7%)|−5.7pt|
|**ALL**|6|35/70 (50%)|27/44 (61.4%)|−11.4pt|

> ANALYST NOTE: \*\*this refutes the working hypothesis I'd been carrying.\*\* I expected the Phase 2 50-59 lead to be concentrated in compressed/down cohorts — a regime artifact that would vanish in clean cohorts and explain the live failure mechanically. It does not. In \*clean\* Phase 2 cohorts the 50-59 lead is \*\*+9.1pt\*\* (70% vs 61%), and it's positive in every Phase 2 stratum (compressed +11.7, mixed +2.2, clean +9.1). So the Q1 finding was a \*\*real, regime-robust Phase 2 feature\*\* — not stratification noise. Yet within the \*same\* regimes, Phase 3-A reverses it: clean +9.1pt → −5.7pt, mixed +2.2pt → −21.2pt. Holding regime constant, the band ordering flipped between the two periods. \*\*That is the "something changed" story — the more interesting one.\*\* Candidates, in rough order of how I'd chase them: (a) a market-regime shift between late-May/early-June and mid/late-June that the cohort-hit flag doesn't capture (e.g., a volatility-clustering or trend change — worth a finer regime axis than the ±3% hit rate); (b) drift in the signal generator between phases (data source, prompt, model) — checkable against the run logs; (c) temporal overfitting of the original Q1 finding to its window; (d) live small-sample noise — the Phase 3-A 60-69 n is still only 44 (mixed n=26 drives the −21.2pt), so the reversal is consistent but not yet large-n. \*\*Recommendation:\*\* keep the Q1 guardrail flagged as not-reproducing (do not rely on it for any actionable phase), and open a focused "what changed" investigation rather than a simple artifact write-off. The phase gate still did its job — it caught a certified edge degrading live — but the diagnosis is richer than expected. Advisory-only throughout.

### H1 — Lag Still 5; WMT 4 of 6

WMT's 6/23 +5d came in at **−5.22% (NO)** — a sharp move clearing the ±3% band (live WMT now 4 of 6: 6/15 Y, 6/16 Y, 6/17 N, 6/18 Y, 6/22 Y, 6/23 N). Lag scan unchanged: **estimated lag still 5 sessions** (peak r +0.579), corr(conf, trailing) consistent. Six live cohorts, lag steady at 5.

### 6/1 +20d — Non-Monotonic (2nd Exception)

6/1's trajectory: |move| **4.72 → 3.85 → 6.79%** — dips at +10d, then grows, so non-monotonic. Magnitude-growth tally now **8-for-10 monotonic**, with 5/22 and 6/1 the two exceptions (both dip at the +10d step). +20d direction **−3.48%**.

### Near-Miss / Registry — Unchanged

No near-miss BUYs resolved on 6/30 (neither the 6/23 nor 6/15 cohort carried a 60-69% BUY). Registry holds: EXTENDED +5d 5/12 = 41.7%, +10d completed 10; LOCKED 4/7. **VERDICT KEEP 70%**, unchanged.

## 2026-07-01 — Phase 3-A Day 12: Seventh Live Cohort (Clean) Again Favors 60-69; Cumulative Lead at Crossover (+0.4pt); Q1 Reversal Deepens

The reversal is strengthening, not settling. **6/24 is the 7th live cohort — clean (62% cohort-wide) — and favors 60-69 by 26 points (88% vs 62%)**, making it 6 of 6 non-compressed live cohorts against the guardrail. The cumulative 50-59 lead has **collapsed to +0.4pt** (56.8% vs 56.4%) — effectively at crossover, from +2.2pt yesterday. Refreshed with the new cohort, the live non-compressed stratum deepens to **−21.2pt** (clean stratum −5.7 → −14.4pt). Both 6/16 near-misses missed at +10d; H1 lag holds at 5 (WMT held 55% through a −8.99% +5d drop). Closeout worksheet updated to v2. **Decision: still EXTEND** — no gate green; H1 now one cohort from its verdict; the deepening reversal reinforces staying advisory.

### 7/1 Run + Integrity

This morning's 24 signals cross-validate **24/24 clean** against `signals\_2026-07-01.log` (rows 720–743; **23 HOLD + 1 BUY** — GLD 65% HIGH, scout, a near-miss). The three resolutions — **6/24 +5d, 6/16 +10d, 6/2 +20d** — are complete (24/24, 24/24, 21/21); recalc clean (**0 errors / 8,641 formulas**). Totals **739 signals**, **BUY 20**.

### Seventh Live Cohort — 6/24 (Clean) Again Favors 60-69; Lead at Crossover

6/24 cohort +5d bands: **60-69% 88% (7/8) > 50-59% 62% (5/8) > 40-49% 50% (3/6)** (0-39% 0/2), cohort-wide **62% → clean**. 50-59 did fine (62%), but 60-69 was near-perfect (88%). **Held NO.** That is the sixth consecutive non-compressed cohort to favor 60-69; the only pairwise "hold" remains 6/16, the lone compressed cohort — **pairwise held 1 of 7**.

|Live cohort|50-59% (n)|Held|Band order (by hit)|Cum lead|Regime|
|-|-|-|-|-|-|
|6/22|55% (11)|NO|60-69 67%(6) > 50-59 55%(11) > 40-49 33%(6)|+3.3pt|mixed|
|6/23|80% (10)|NO|60-69 86%(7) > 50-59 80%(10) > 40-49 57%(7)|+2.2pt|clean|
|6/24|62% (8)|NO|60-69 88%(8) > 50-59 62%(8) > 40-49 50%(6)|**+0.4pt**|clean|

Cumulative 50-59% **56.8%** vs 60-69% **56.4%**, lead **+0.4pt** (+2.2 → +0.4). One more strong 60-69 cohort flips the sign. 60-69 has climbed 48 → 56.4% across the live run.

### Q1 Re-Examination Refreshed — the Reversal Deepens (7 cohorts)

Re-ran `--stratify-regime` with 6/24 included. Phase 2 is fixed; Phase 3-A deepens:

|Stratum|Phase 2 lead|Phase 3-A lead (6/30)|Phase 3-A lead (7/1)|
|-|-|-|-|
|clean|+9.1pt|−5.7pt|**−14.4pt** (72.2% vs 86.7%, n 18/15)|
|non-compressed|**+5.8pt**|−19.4pt|**−21.2pt** (54.4% vs 75.6%, n 68/41)|
|ALL|+8.2pt|−11.4pt|−14.1pt (51.3% vs 65.4%)|

> ANALYST NOTE: adding a second clean cohort (6/24) pushed the live clean stratum from −5.7pt to −14.4pt and the pooled non-compressed lead to −21.2pt. The Phase 2 → live contrast within the same non-compressed regimes is now \~27pt (+5.8 → −21.2). This continues to refute the regime-artifact hypothesis and to sharpen the "something changed" read — the flip is getting larger as n grows, not regressing toward zero, which is weak evidence \*against\* the pure small-n explanation (though live 60-69 n is still only 52). The candidate causes are unchanged (vol/trend-regime shift the hit-flag misses, signal-generator drift, temporal overfit); the next concrete step remains a Phase-2-vs-live signal-generator log diff and/or a finer volatility axis. Advisory-only throughout.

### 6/16 +10d Horizon Read (compressed cohort)

For the compressed 6/16 cohort, holding the signal set fixed: **50-59% +5d 30% → +10d 50%; 60-69% +5d 27% → +10d 36%**. At +10d, 50-59 leads (50% vs 36%) — consistent with the guardrail. But 6/16 is the compressed outlier (the one cohort where 50-59 led at +5d too); it does not offset the six non-compressed cohorts that go the other way at +5d. Two horizons now read the same *within* each regime: 60-69 leads in non-compressed (6/15), 50-59 leads in compressed (6/16).

### Near-Miss / Registry — 6/16 Pair Miss +10d; GLD 65% Added; KEEP 70%

Both 6/16 near-misses resolved at +10d and **both missed**: VTI 68% **−0.77% (NO)**, NVDA 65% **−5.52% (NO)**. EXTENDED **+10d completed → 12**, hits **1/12 = 8.3%** (the lone winner still 6/12 VTI). Today's GLD 65% BUY (scout, HIGH DQ, $375.10) adds to EXTENDED (now **13 total; 20 near-misses overall** = 7 LOCKED + 13 EXTENDED); its +5d resolves \~7/9. EXTENDED +5d unchanged 5/12 = 41.7%; LOCKED 4/7 (+5d) / 1/7 (+10d). **VERDICT KEEP 70%**, reinforced — near-misses remain net-negative at both horizons.

### H1 — Lag Still 5; WMT 4 of 7 (−8.99% miss)

WMT's 6/24 +5d printed **−8.99% (NO)** — the bot held HOLD at 55% straight through a −8.99% five-day drop, a clean lag exhibit (confidence didn't react to the coming move). Live WMT now **4 of 7** (6/15 Y, 6/16 Y, 6/17 N, 6/18 Y, 6/22 Y, 6/23 N, 6/24 N). Lag scan **still 5 sessions** across 7 cohorts; corr(conf, trailing) still ≤ 0 (peak positive r +0.372). H1 continues to trend toward verdict (b) — the lag persists, the remedy (if measured) is not moving it.

### 6/2 +20d — Non-Monotonic (3rd Exception)

6/2's trajectory: |move| **5.07 → 4.85 → 7.44%** — dips at +10d before growing, so non-monotonic (n=21). That is the third +20d exception (5/22, 6/1, 6/2 — the latter two consecutive), so the magnitude-growth tally is now **8-for-11 monotonic**; net +5d→+20d growth still holds 11-for-11 (every cohort grows on net), but the +10d dip is recurring in the recent cluster. +20d direction **−5.14%**.

### Closeout Worksheet — v2 (7/1 readings)

Updated the Phase 3-A Closeout Decision Worksheet to **v2**. Movement since v1: **H1** 6 → 7 cohorts (one short of the ≥8 gate; verdict writable \~7/2), lag steady at 5; **Sample depth** 6 → 7 cohorts, live 60-69 n 44 → 52; **Q1-R** reversal deepened (clean −14.4pt, non-compressed −21.2pt, cumulative at +0.4pt) but root cause still open; **cumulative lead** +2.2 → +0.4pt. H3 and H2 remain not-started. Roll-up unchanged: **5 of 5 gates open → NOT YET / EXTEND.** H1 is now the nearest to closable; H3/H2 are the long poles; the deepening Q1 reversal is a standing reason to stay advisory.

## 2026-07-02 — Phase 3-A Day 13: CROSSOVER — Cumulative Lead Goes Negative (−0.7pt); H1 Gate Met at 8 Cohorts, Verdict (b) Drafted; Band-Composition Check Finds a Population Shift

*(7/2 close data, processed at the Mon 7/6 weekly review — Fri 7/3 market closed, July 4 observed.)*

Three finalizations today. (1) **The crossover happened**: the 6/25 cohort (8th live) makes the cumulative 50-59 lead **negative for the first time (−0.7pt)** — 60-69 (57.1%) is now ahead of 50-59 (56.4%) over the full live run. (2) **The H1 ≥8-cohort gate is met** — lag 5 sessions in all 8 cohorts, and the headline corr flip (+0.198) decomposes to the 7/1–7/2 catch-up itself (−0.153 without those two sessions) — **verdict (b) drafted for lock**: prompt-level remedy ineffective; the lag finding itself is confirmed and live-replicated. (3) The first Q1-R root-cause probe — a **band-composition check** — found the bands are **not stable populations across phases** (60-69 BUY share 21% → 3%; PM 29% → 75% within-band; NVDA exited 60-69; index ETFs entered 50-59), narrowing the "what changed" candidates toward generator-drift / population shift. Weekly MDs reviewed; worksheet finalized to v3.

### 7/2 Run + Integrity

The 7/2 signals cross-validate **24/24 clean** against `signals\_2026-07-02.log` (rows 744–767, all HOLD; `prompt\_variant` = **"A"** on all 24 — single live arm). Resolutions at the 7/2 close — **6/25 +5d (24/24), 6/17 +10d (24/24), 6/3 +20d (22/22)** — complete; recalc **0 errors / 8,641 formulas**. Totals **763 signals**, **BUY 20**. Guardrail Trace + Live Cohort Scoreboard sheets are Rob's weekly-review run (7/6 08:14–08:15) and were **left untouched** — read as authoritative, not regenerated.

### Eighth Live Cohort — 6/25 (Mixed): 50-59 Falls to Third; CROSSOVER

6/25 +5d bands: **60-69% 71% (5/7) > 40-49% 50% (3/6) > 50-59% 44% (4/9)** (0-39% 0/2), cohort-wide **50% → mixed**. 50-59 finished *bottom of the three main bands* (second time, after 6/15). Section 4 r60: 44.4%, Pattern NO. **Pairwise held 1 of 8**; 7 of 7 non-compressed cohorts favor 60-69. Scoreboard cumulative: **−0.7pt** — the certified guardrail's headline lead is now negative out-of-sample. Dashboard concurs (50-59 56.4%, 60-69 57.1%, 40-49 44.4%).

### 6/17 +10d Read — First Horizon Divergence

Fixed-set horizon read for 6/17 (mixed): **50-59% 38% → 62%; 60-69% 75% → 50%**. At +10d, 50-59 *leads* this cohort — the first divergence between horizons. Horizon tally so far: 6/15 (mixed) 60-69 leads both horizons and widens; 6/16 (compressed) 50-59 leads both; 6/17 (mixed) splits — 60-69 at +5d, 50-59 at +10d. The live reversal is sharpest and most consistent at **+5d**; the +10d picture is muddier (50-59 has led 2 of 3 cohorts at +10d). Recorded as-is; +10d reads continue accumulating one cohort behind.

### H1 — GATE MET (8 Cohorts); VERDICT (b) DRAFTED FOR LOCK

The pre-committed criterion — ≥8 live cohorts with a stable lag estimate and a written verdict — is met today.

**Evidence.** Estimated update lag **5 sessions in all 8 live cohorts** (and every daily read since 6/15). The weekly MD headline shows corr(conf, trailing move) = **+0.198**, which nominally breaks verdict (b)'s "corr ≤ 0" condition — but the decomposition (recomputed from tracker prices) shows the flip is produced entirely by the **7/1–7/2 WMT catch-up** (conf 52% → 45% *after* a −10% trailing move): excluding those two sessions, corr = **−0.153**, right at the 6/30 baseline. A delayed follower *generates* positive contemporaneous corr during sustained declines once it catches up — the flip is the lag's own signature, not responsiveness. Predictive corr(conf, +5d) remains **−0.583**. The live WMT arc now shows a complete second hold-then-correct cycle (held 52–55% through −3.51/−5.22/−8.99/−4.61% misses, then stepped to 45% — exactly the Phase 2 pattern of \~5 sessions late, \~10–14pt step).

> H1 VERDICT (drafted 2026-07-02 review, for Rob's lock): \*\*(b) INEFFECTIVE AT PROMPT LEVEL — RETIRE the prompt remedy; the lag finding itself is CONFIRMED.\*\* The \~5-session confidence-update lag is real, stable, and now fully live-replicated (8/8 cohorts, two complete hold→catch-up arcs, WMT tracer). The prompt-level remedy did not move the primary endpoint (lag 5, unchanged vs the Phase 2 \~3–5 baseline). The corr condition of branch (b) is treated as satisfied in substance: the +0.198 reading is episode-driven (−0.153 ex-catch-up) and mechanistically \*is\* the lag. \*\*Disposition:\*\* retire prompt-phrasing as a lag remedy; carry the finding to 3-B as a feature-level candidate (mechanical trailing-return input / confidence damping). \*\*Provenance condition (confirm at lock):\*\* all 3-A logs carry a single `prompt\_variant` = "A"; this verdict assumes A = the 3-A prompt \*including\* the H1 prior-5-day price input per the kickoff spec. If A does \*not\* include it, the verdict re-classes from "remedy ineffective" to "remedy untested — baseline lag confirmed live" (same disposition, different provenance) — submitting the live prompt file settles it.

### Weekly MD Review — H3 / H2 / H4 Baselines

**H3 (thesis stability)** — first portfolio-wide baseline: **26/737 day-over-day flips = 3.5%**, mean |dConf| 2.8pts, and **14 of 26 flips (54%) occurred on <1% moves** — churn-on-noise. Concentration is extreme: **NVDA 38.7%** flip rate, VTI 20.0%, GLD 12.9%, CBRS/SCHD 6.5%, and **19 of 24 tickers have zero flips**. Note for the A/B design: this baseline measures *day-over-day* churn; the original 5/29 baseline (9 of 24) was *AM/PM intraday* churn — two different axes. Recommend the day-over-day small-move flip rate as the primary A/B endpoint (continuously measurable from daily logs; no paired intraday runs needed), with AM/PM as a secondary check. Gate moves GRAY → YELLOW (baseline measured; A/B not run).

**H2 (direction asymmetry)** — baseline is **hypothesis-adverse at the portfolio level**: ratio **0.85** (sens\_down 1.51 / sens\_up 1.78) — *more* reactive to gains on average, opposite the loss-bias premise. Per-ticker it's heterogeneous in both directions (RTX 2.89, DOW 1.82, WMT 1.68 ↔ CBRS 0.33, GLD 0.45, AIQ 0.48). The original WMT-vs-GM pair does replicate directionally (1.68 vs 1.10), but it doesn't generalize. Flag for H2 kickoff: consider re-scoping from "fix a uniform loss-bias" to "reduce dispersion" — or deprioritize.

**H4 (DQ watchdog)** — **2 of 3 reopen conditions now met**: HIGH-DQ near-miss hit 75% (3/4) ✓ and HIGH ≥ MEDIUM overall (57.5% vs 48.9%) ✓; blocker is **n = 4 of ≥10 required**. GLD 7/1 (HIGH, 65%) resolves 7/9 and adds to HIGH-DQ n. Stays DEMOTED; watch.

### Q1-R — Composition Check: the Bands Are Not Stable Populations

Refreshed stratification (read-only, 8 cohorts): live **non-compressed −21.8pt** (53.2% vs 75.0%), ALL **−15.5pt** — still deepening (−19.4 → −21.2 → −21.8pt across three refreshes). First root-cause probe run today — per-ticker band composition, Phase 2 vs live:

|Band|Phase 2 (top constituents)|Phase 3-A (top constituents)|
|-|-|-|
|60-69|SCHD 18/18, **PM 5/17 (29%)**, NVDA 6/13, PWR 5/11 — **21% BUYs**|JPM 7/8, **PM 6/8 (75%)**, PWR 5/7, SCHD 6/7 — **3% BUYs**|
|50-59|MSFT 4/17, JPM 9/17, AAPL 10/16, RTX 13/16|MSFT 3/8, WMT 4/8, **SPY 8/8, QQQ 5/8, XLU 6/6**, NVDA 3/7|

> ANALYST NOTE: the certified Q1 property was a \*band-level\* claim, but the bands' \*membership\* shifted materially between phases: the 60-69 band shed its BUY near-misses (21% → 3% of the band) and its within-band problem children changed behavior (PM 29% → 75%); NVDA's HOLDs left 60-69 (its confidence migrated down); index ETFs (SPY/QQQ/XLU) entered live 50-59 alongside lag-afflicted WMT/NVDA. So "the 50-59 > 60-69 ordering flipped" may decompose into "different tickers, different signal mix, different market" rather than a single calibration failure. This \*narrows\* the root-cause candidates toward \*\*(b) generator drift / population shift\*\* and away from pure regime or pure small-n — but it is not yet a diagnosis. The decisive next test is the \*\*Phase-2-vs-live prompt + distribution diff\*\* (confidence histograms per ticker, band-membership flows, DQ mix) — which needs the prompt file(s) and a Phase 2 log week alongside a live week. Q1-R stays OPEN (yellow) with upgraded evidence.

### 6/3 +20d — Non-Monotonic (4th Exception, 3rd Consecutive)

6/3 (n=22): |move| **5.73 → 4.76 → 7.06%** — the +10d dip again. Monotonic tally **8-for-12**; the four exceptions are 5/22 and the consecutive 6/1–6/3 family, whose +5d windows contain the 6/10 shock at peak |move|, mean-revert by +10d, then re-expand into the late-June selloff — an event-driven cluster, not a magnitude-law failure. **Net growth (|+20d| > |+5d|) remains 12-for-12.** +20d direction −3.99%.

### Near-Miss / Registry — Unchanged

No near-miss resolutions at the 7/2 close (7/2 itself all HOLD). Registry per the weekly MD: **20 near-misses** (LOCKED 7: +5d 4/7, +10d 1/7; EXTENDED 13: +5d 5/12, **+10d 1/12 = 8.3%**, avg −3.7%). GLD 7/1 (HIGH, 65%) +5d resolves **7/9**. **KEEP 70%** — near-misses are failing both horizons decisively.

### Closeout Worksheet — v3 (Finalized at the 7/6 Weekly Review)

**H1 → MET** (criterion satisfied; verdict (b) drafted above — lockable at sign-off). **H3 → YELLOW** (baseline measured; A/B is now the critical path). **H2** baseline recorded (hypothesis-adverse; re-scope option flagged). **Q1-R** evidence upgraded (crossover; composition shift found; root cause narrowing but open). **Gate S**: 8 of \~10–12 cohorts; live 60-69 n **59** (target \~88). Roll-up: **once H1 locks, 4 of 5 gates open → NOT YET / EXTEND.** Critical path is now **H3's A/B launch**; Q1-R's prompt/log diff runs in parallel.

## 2026-07-06 — Phase 3-A Day 14 (FINAL): First SELL Misses Hard; Ninth Cohort Is the First Non-Compressed Hold; PHASE 3-A CLOSED BY SIGN-OFF — H1 Locked, H3/H2 Descoped, Q1-R Parked; 3-B Kickoff

**Phase 3-A is closed.** Rob signed Worksheet v3 today (H1 verdict lock ✓, Close: YES ✓, "Rob · July 6, 2026") with a same-day directive: terminate A/B testing, move to **Phase 3-B triple-blend development**, implement the H1 lag finding, and cut dead-weight hypotheses. The closeout is recorded in `Phase3A\_Closeout\_Memo.md` with honest disposition labels — **one verdict** (H1 locked), **two descopes** (H3 retired untested; H2 retired untested-and-unsupported), **one park** (Q1-R, with re-open triggers T1/T2/T3), **one waiver** (Gate S at 9 cohorts). The final day's data added two notable results: the **first SELL missed hard** (CBRS 68% → **+14.61%**, NO), and the **9th cohort (6/26, mixed) is the first non-compressed cohort where the guardrail held** (50-59 70% > 60-69 62%). Final live state: pairwise **2 of 9**, cumulative **−0.6pt** (crossover holds), non-compressed stratum **−18.0pt**.

### 7/6 Run + Integrity (final 3-A daily)

The 7/6 signals cross-validate **24/24 clean** against `signals\_2026-07-06.log` (rows 768–791, all HOLD, variant "A" ×24). Resolutions — **6/26 +5d, 6/18 +10d, 6/4 +20d** — all complete (24/24 each); recalc **0 errors / 8,641 formulas**. Totals **787 signals**, BUY 20, SELL 1. Guardrail/scoreboard sheets are Rob's weekly-run copies (authoritative); final-state numbers below computed read-only.

### First SELL — CBRS 68% Misses by +14.61%

The project's first and only SELL (CBRS, 6/26, 68%, resolved at today's close) printed **+14.61% → NO** — the stock rallied double-digits against a 68% SELL. One datapoint, no generalization — but it lands squarely on the ticker already flagged structural: consistent with the standing **Q3 Path A decision** (CBRS excluded to Q4 2026), and a fitting last exhibit for why that exclusion exists.

### Ninth (Final) Cohort — 6/26: the First Non-Compressed Hold

6/26 +5d bands: **50-59% 70% (7/10) > 60-69% 62% (5/8) > 40-49% 20% (1/5)**, cohort-wide **54% → mixed**. **Held YES** — the first of the eight non-compressed live cohorts where 50-59 led pairwise (the only other hold was compressed 6/16). Recorded without overweighting: the final tally is **7 of 8 non-compressed cohorts favoring 60-69**, pairwise held **2 of 9**, and the cumulative lead stays negative at **−0.6pt** (50-59 56.9% vs 60-69 57.4%). One late hold does not un-ring the crossover; it does keep the honest error bars visible.

### Final Live-Run State (certified into the memo)

|Metric|Final (9 cohorts)|
|-|-|
|Pairwise held (50-59 > 60-69)|**2 of 9** (6/16 compressed, 6/26 mixed)|
|Cumulative lead|**−0.6pt** (crossover reached 7/2, held)|
|Stratified non-compressed|**−18.0pt** (55.2% n=87 vs 73.2% n=56) — vs Phase 2 **+5.8pt**|
|Live band n|50-59: 97 @ 52.6% · 60-69: 67 @ 65.7%|
|+10d horizon reads|split 2–2 (6/15, 6/18 → 60-69; 6/16, 6/17 → 50-59) — the reversal is +5d-sharp|

### 6/18 +10d and 6/4 +20d

**6/18 +10d** (4th horizon read): both bands decline at +10d; 60-69 still leads (67% vs 45%) — the 2–2 split above. **6/4 +20d: MONOTONIC** (4.14 → 4.61 → 6.22%, n=24) — the +10d-dip cluster ends at 6/3, confirming it as the 6/10-shock cohort family. Final magnitude record: **net-growth 13-for-13**, monotonic 9-for-13 (exceptions: 5/22, 6/1–6/3 — all event-cluster). +20d direction −3.64%.

### Closeout Dispositions (see `Phase3A\_Closeout\_Memo.md` for the full record)

**H1 — VERDICT (b) LOCKED**: lag real and stable at 5 sessions (8 cohorts at lock, 9th consistent; two full hold→catch-up arcs); prompt remedy retired; provenance box left open at signature, documented as an assumption — moot, since implementation moves to feature level. **H3 — DESCOPED** (retired untested; baseline 3.5% flips, NVDA-concentrated — churn is a 3-ticker trait). **H2 — DESCOPED** (retired untested-and-unsupported; baseline ratio 0.85, hypothesis-adverse). **Q1-R — PARKED** with triggers: T1 mandatory before any execution consideration; T2 at 60-69 n≥88 if non-compressed lead ≤ −15pt → run the prompt/distribution diff; T3 before any design reliance on band ordering. **Gate S — WAIVED** at 9/\~10–12 cohorts, n=67/\~88; the depth target lives on inside T2. **A/B program terminated** (archived). **The Q1 guardrail is SUSPENDED as a decision input.**

> ANALYST NOTE: the disposition labels matter more than usual here. Phase 3-A produced exactly one evidence-complete verdict (H1). Everything else closed by \*decision\*: two hypotheses were cut before their tests ran (one of them, H2, with a baseline that argued against it anyway; the other, H3, with a baseline that shrank the premise), and the run's biggest open question — why a certified, regime-robust edge inverted out-of-sample — was parked, not answered. That is a legitimate scope call, and the advisory-only constraint plus triggers T1–T3 make it a \*safe\* one: no capital can touch this system while Q1-R is undiagnosed, and the monitors that would re-open it keep running for free inside the daily flow. The phase gate did its job — it caught the certified edge degrading before anything relied on it — and 3-A hands 3-B one implementable finding (the lag), one standing threshold (KEEP 70%), one robust invariant (magnitude net-growth 13-for-13), and one suspended guardrail with a tripwire on it. Advisory-only throughout; no orders; not financial advice.

### Registry / H4 — carried into 3-B monitoring

No near-miss resolutions today. Registry: 20 near-misses (LOCKED 4/7 \& 1/7; EXTENDED 5/12 \& 1/12). **KEEP 70%** standing. GLD 65% (HIGH) +5d resolves **7/9** — adds HIGH-DQ n toward H4's reopen gate (now 2 of 3 conditions, n=4/10). In-flight cohorts 6/29–7/6 resolve 7/7–7/13 under WS0 monitoring.

**Phase 3-A: opened 2026-06-15, closed 2026-07-06. Fourteen sessions, nine certified cohorts, zero orders. → `Phase3B\_Kickoff\_Prompt.md`.**





\---

# Active Touch Points

*Last updated: 2026-07-06 — **PHASE 3-A CLOSED BY SIGN-OFF** (Worksheet v3 signed; H1 verdict (b) LOCKED — lag 5 real/stable, prompt remedy retired, implement feature-level in 3-B; H3 DESCOPED untested (baseline 3.5%, NVDA-concentrated); H2 DESCOPED untested-and-unsupported (ratio 0.85 adverse); Q1-R PARKED w/ triggers T1 pre-execution / T2 n≥88 \& lead ≤ −15pt / T3 band-ordering reliance; Gate S waived at 9 cohorts; A/B terminated; Q1 guardrail SUSPENDED as decision input. Final live state: pairwise 2 of 9, cumulative −0.6pt (crossover holds), non-compressed −18.0pt, 60-69 n=67 @ 65.7% vs 50-59 n=97 @ 52.6%; first SELL CBRS 68% missed +14.61% (supports Path A); 6/26 = first non-compressed hold (70% > 62%); magnitude net-growth 13-for-13; KEEP 70%; GLD near-miss +5d due 7/9. <b>→ Phase 3-B open: WS1 triple-blend, WS2 H1 feature-level lag fix (accept: lag ≤2 over ≥4 cohorts), WS3 Q3 commodity/CBRS code, WS0 monitoring.</b> Docs: Phase3A\_Closeout\_Memo.md, Phase3B\_Kickoff\_Prompt.md)*

**Completed:**

* 5/26 (Day 6) — Captured 5/18 cohort outcomes (first calibration signal)
* 5/27 (Day 7) — Captured 5/19 cohort outcomes + first near-miss BUY (NVDA -3.62%, NO)
* 5/28 (Day 8) — Captured 5/20 cohort outcomes; **Q1 calibration verdict locked: CALIBRATED**
* 5/29 (Day 9) — Captured 5/21 cohort + first near-miss BUY win (SCHD +1.22%, YES); run\_daily.bat fix verified
* 6/1 (Day 10) — Captured 5/22 cohort (45.8%, Pattern NO on tie; corrected from 54.2% on 6/8); NVDA 5/22 near-miss WIN (+3.50%); AG/FTI 429-skipped
* 6/2 (Day 11) — Captured 5/26 cohort (66.7%, Pattern NO on low-vol confound) + VTI 5/26 near-miss WIN (+1.14%); **first +10d outcome (5/18 cohort): HOLD-decay finding**; deduped 5/18 to 24 rows; Decision Worksheet updated to v4; CORN/XLU/SPY 429-skipped
* 6/3 (Day 12) — Captured 5/27 cohort (**79.2%, strongest cohort**, Pattern YES) + NVDA 5/27 near-miss WIN (+2.34%); 5/19 +10d (decay did NOT replicate — partial); Cohort Analysis tab extended through 6/12; QQQ/VTI 429-skipped
* 6/4 (Day 13) — Captured 5/28 cohort (66.7%, Pattern YES) + 5/20 +10d (decay sided with 5/18, 2-of-3 at the time); WMT lag replicated 3rd time; clean 24/24 run
* 6/5 (Day 14) — Captured 5/29 cohort (54.2%, Pattern YES, final +5d cohort); 5/21 +10d (decay reverts to coin flip, 2/4); **Q2 VERDICT LOCKED: KEEP 70%** (4/6 hit, −0.07% avg); **Q1 FINALIZED: CALIBRATED 6 of 9, 50-59% at 61.3%**; Decision Worksheet updated to v5; fixed Near-Miss avg-return formula bug; clean 24/24 run
* 6/8 (Day 15) — NVDA 6/1 near-miss +5d recorded (−5.84%, NO): **Q2 7-of-7 FINAL 4/7 = 57.1%, −0.90% avg — KEEP 70% confirmed**; 5/22 +10d (45.8% → 50.0%, +4.2pt, did NOT decay; **abs move SHRANK 4.52→4.09 — first magnitude-growth exception, tally now 4/5**); WMT +10d −0.00% (H1 lag fully self-corrected); Q1 re-certified unchanged (61.3%, 6/9); corrected 5/22 +5d 54.2% → 45.8% (other 8 cohorts re-verified clean); clean 24/24 run
* 6/9 (Day 16) — Captured 5/26 +10d (66.7% → 29.2%, −37.5pt — **sharpest decay, low-vol confound unwound as the 6/2 entry predicted**; abs move grew 2.92→4.47, tally 5/6); WMT +10d +0.01% (H1 resolved, 6th cohort); Near-Miss tab extended to +10d (4 complete: 1/4 = 25%, −1.89% avg — corroborates KEEP 70%); Q1 re-certified unchanged; clean 24/24 run; 11th near-miss logged (NVDA 68% @ $207.40)
* 6/10 (Day 17) — Captured 5/27 +10d (79.2% → 29.2%, **−50.0pt — largest decay, REGIME-CONTAMINATED: the 6/10 Middle East shock IS the +10d close**; abs move grew 2.67→5.16, tally 6/7; decay 4/7 but 2 of 4 shock-flagged, claim stays retired); WMT +10d +1.99% (H1, 7th cohort, held through shock); NVDA 5/27 near-miss +10d −4.49% NO (1/5 = 20%); 6/3 cohort +5d complete (22/22 max); Near-Miss registry findings: '6/2' GLD+NVDA rows are 6/3 signals (re-date, outcomes correct), five band BUYs missing (6/2 @227.93 −8.66% NO complete; 6/4, 6/5, 6/8, 6/9 pending) — registry should total 14, not 9; extended near-misses 0-for-3 post-lock, all on the KEEP-70% side; second pure-HOLD day (shock morning, zero signals cleared); Q1 re-certified unchanged; clean 24/24 run
* 6/11 (Day 18) — Captured 5/28 +10d (66.7% → 41.7%, −25.0pt, **measured on the 6/11 bounce** — abs grew 3.28→4.69, tally 7/8; decay 5/8, ex-shock 3/6, claim stays retired); **CORRECTED shock-set scope to 5/27–5/29** (5/26 window ended 6/9 pre-shock — its −37.5pt is pure inflation-unwind, the clean exhibit); **WASDE: CORN −2.05% abs / ≈−3.7% mkt-rel on a pre-release HOLD 38% — validates Path B** (one-event caveat); WMT +10d +1.71% (H1, 8th cohort); 6/4 near-miss −4.17% NO (extended 0-for-4, avg −7.0%); 6/4 cohort +5d complete; new NVDA 65% near-miss @ $199.94 (registry should total 15; 6/10 registry fixes still open); Q1 re-certified unchanged; clean 24/24 run, HIGH DQ 5/24 (4th depressed day)
* 6/12 (Day 19) — **PHASE 2 CLOSED.** Captured 5/29 +10d (54.2% → 37.5%, −16.7pt, mildest shock-window decay); FINAL scorecards: magnitude 8/9, decay 6/9 (ex-shock 3/6, retired); WMT arc completed −15.19 → +4.31 (favorable-side breach — lag visible both directions); Q1 FINAL CERTIFIED (61.3%, n=216, 6/9); 5/29 near-miss +10d −4.98% NO, 6/5 near-miss −3.20% NO (extended 0-for-5, avg −6.23%); two new near-misses (VTI 68% HIGH, NVDA 62%) — registry should total 17, fixes promoted to Phase 3 auto-gen item; review held: memo §0/§3/§4/§5/§7 finalized — Phase 3-A approved (H1 → H3 → H2, advisory-only, triple-blend deferred to 3-B); clean 24/24 run
* 6/15 (Phase 3-A Day 1) — **PHASE 3-A LIVE** (advisory-only, no orders). First run 24/24 all HOLD, risk APPROVED → tracker rows 456–479 (Section 4 cohort wired, pending +5d; Dashboard 475 total, **50-59% guardrail holds 58.8%**; AG/FTI confirmed price-only backfills, inert). **analyze\_log.py phase-regex fix** (`\\d` matched one digit → `\[PHASE 3-A DRY RUN]` parsed 0; broke exactly on the cutover; fixed to phase-agnostic `\[\\w.-]+`, control-arm-only; reproduced 0 → 24, A/B 24 not 48). Go-live hardening: PYTHONUTF8 + openpyxl self-check + requirements.txt in the bats; run\_daily.bat paren-parse fix; harness `--since`/`--until`; UTF-8 writes; news\_client.py newest-first sort. Tracker K:N filled to row 2000 + Section 4 added (recalc 0 errors); date-coercion proven via throwaway injection. README rewritten to Phase 3-A (MAX\_OPEN\_POSITIONS doc-lag 30 → 8; engine was always 8). EDGAR scoped to Phase 3 as one edgar\_client.py (Form 4/8-K + 10-Q/10-K MD\&A; A/B arm, not baseline; roadmap folded to one line). Repo reconciled; 13-file bundle staged for push.
* 6/16 (Phase 3-A Day 2) — 6/16 run **24 signals, 2 BUY / 22 HOLD** — first Phase 3-A BUYs, both near-misses (**VTI 68% HIGH @ $372.15**, **NVDA 65% MEDIUM @ $209.12**, scouts, rejected by the 70% threshold). Logged to Near-Miss tab rows 14–15 (+5d 6/24, +10d 7/1; **tab 9 → 11**, resolved stats unchanged at 44.4% / −2.38%). Near-Miss tab repaired: relabeled (Phase 2 + Phase 3-A); **verdict resolved → KEEP 70%** (was stale "to be decided 6/10"); rows 11–15 +10d cells restyled (drifted fills) + +10d dates filled (H11 6/15, H12/H13 6/17 = +5d + 5 trading days). 6/15 re-run confirmed 0 near-misses (24/24 HOLD); 6/15 cohort +5d pending (\~6/23).
* 6/17 (Phase 3-A Day 3) — 6/17 run **24/24 HOLD** (no near-misses; VTI 58% / NVDA 55% below band). **First +20d cohorts resolved (5/18, 5/19): magnitude grows to 20 days** — |move| 4.51 → 5.69 → **6.72%** (5/18), 5.25 → 6.09 → **7.17%** (5/19), both monotonic, **2-for-2** extending the 8/9 Phase 2 finding; +20d direction net negative (−2.0%, −2.4%). **Near-miss +10d: 3 new (NVDA 6/1, GLD 6/2, NVDA 6/2), all NO → hit rate 1/9 = 11.1%** (from 16.7%), corroborates KEEP 70%. Guardrail holds: live 50-59% **59.3%** (eased from certified 61.3%) > 60-69% 50.7% > 40-49% 46.0%. Totals reconcile (523 = 451 + 72, BUY 19); +5d coverage through 6/10 (77%); recalc 0 errors. 6/17 prices at sub-cent precision (flagged). Phase 3-A +5d pending (\~6/23).
* 6/18 (Phase 3-A Day 4) — 6/18 run **24/24 HOLD** (no near-misses; VTI/NVDA 58% below band). **5/20 +20d: magnitude growth 3-for-3** — |move| 5.54 → 6.28 → **7.09%**, monotonic; +20d −3.09% (deepening, but overlapping mid-June windows). **6/11 cohort +5d Pattern NO** (50-59% 50%, n=12; across-cohort 10 of 18); 6/12 last Phase 2 +5d pending (\~6/22). **Near-miss registry backfilled 11 → 19** via build\_near\_miss\_registry.py (7 LOCKED + 12 EXTENDED): genuine 6/2 NVDA added, 6/3 pair re-dated, 6/16 NVDA conf 0.68→0.65; **combined +5d 7/15 = 46.7%**, LOCKED +5d 4/7 (immutable) / +10d 1/7 (6/1 resolved NO post-freeze); fixed the script cross-workbook style bug. **guardrail\_trace.py built + run** — 50-59 lead peaked +12.3pt (6/1), compressed post-shock to +7.4pt (6/11), stabilising, no crossover (certified 61.3% = cum at 5/29). **h1\_lag\_trace.py dry-run** — runs clean, ingests Phase 3-A rows, reproduces baseline (lag 5 sessions, arc −15.19→−1.66); ready for 6/23. Totals reconcile (547 = 451 + 96, BUY 19); recalc 0 errors; sub-cent prices 2nd session (new standard).
* 6/22 (Phase 3-A Day 5) — 6/22 run **24/24 HOLD** (no near-misses; VTI 58% / NVDA 55% below band, PWR 63% in-band HOLD). **5/21 +20d: magnitude growth 4-for-4** — |move| 5.05 → 5.18 → **6.55%**, monotonic (shallow +10d step, back-loaded); +20d −3.36% (deepening, overlapping mid-June windows). **Section 1 closed out — 6/12 holds** (50-59% 60%, n=10, Pattern YES; final **11 of 19** cohorts hold; Section 1 fully matured). **Guardrail lead widened to +8.2pt** (50-59% 58.8% > 60-69% 50.6% > 40-49% 45.0%) — the 6/12 cohort reversed the compression (was +7.4pt at 6/11). **Near-miss registry refreshed**: EXTENDED +5d 3/8 → **5/10** (both 6/12 near-misses hit, +1.48% / +0.87%), +10d completed 4 → 5 (6/5 NVDA); combined **9/17 = 52.9%**; LOCKED 4/7 immutable; **KEEP 70% holds** (negative avg returns despite hit-rate uptick — net-negative EV). Guardrail Trace sheet refreshed through 6/12. Totals reconcile (571 = 451 + 120, BUY 19); recalc 0 errors. Phase 3-A +5d still pending — 6/15 resolves 6/23.
* 6/23 (Phase 3-A Day 6) — **First live calibration day.** 6/15 +5d, 6/8 +10d, 5/22 +20d entered (24/24 each); recalc 0 errors; totals 595, BUY 19. **First live guardrail: 6/15 cohort does NOT hold** — Section 4 r53 50-59% 40% (n=15), Pattern NO; bands inverted (60-69 50% > 50-59 40% > 40-49 33%). Cumulative still leads but narrowed: 50-59% **57.6%** > 60-69% 50.6% (+7.0pt, down from +8.2 at 6/12; drift −3.7pt from certified). **n=24, one cohort — expected noise, not a verdict; watch 6/16–22.** **H1 first live read: lag unchanged at 5** (WMT 6/15 −0.73% YES; corr −0.177; one quiet cohort). **5/22 +20d the magnitude exception**: 4.52 → 4.09 → 5.93 (non-monotonic — shrank +5d→+10d, the known exception; net +20d growth 5-for-5, monotonic 4-for-5); +20d −4.58% (deepest). **Registry EXTENDED +10d 5 → 6** (6/8 NVDA −4.01% NO); combined +5d 9/17 = 52.9%; KEEP 70% holds. 6/23 morning block verified clean against the log (24/24 reconcile on signal/conf/DQ/price; all HOLD).
* 6/24 (Phase 3-A Day 7) — **2nd live cohort + morning signals cross-validate clean** (24/24 reconcile, all HOLD; rows 600–623). Resolutions 6/16 +5d, 6/9 +10d, 5/26 +20d entered (24/24 each); recalc 0 errors; totals 619, BUY 19. **6/16 cohort also does NOT hold** — Section 4 r54 50-59% **30% (n=10), NO**; but guardrail bands flat-low (50-59% 30%, 60-69% 27%; 40-49% a lone name), all near-misses deeply negative (VTI −2.28%, NVDA −4.84%, 6/9 NVDA −4.05%) = a **down-regime cohort**, not a clean calibration read. **Relative vs absolute:** cumulative 50-59% **56.4%** > 60-69% 48.0% (lead **+8.5pt**, stable +7→+8.5 across both live cohorts — ranking holds), but absolute **drift −4.9pt** from 61.3% (both below Phase 2 → regime effect, the single-regime caveat surfacing). **H1 lag still 5** (WMT 6/16 −2.50% YES; corr −0.173). **5/26 +20d monotonic** (2.92→4.47→7.46), magnitude **5-for-6** (5/22 still lone exception); +20d −6.40% (deepest). **Registry EXTENDED +5d 5/12 = 41.7%, +10d 7** (all three 6/24 near-miss resolutions NO); combined +5d 9/19 = 47.4%; **KEEP 70% reinforced**.
* 6/25 (Phase 3-A Day 8) — **3rd live cohort + morning signals cross-validate** (23/24 reconcile, all HOLD, rows 624–647; **one catch — GLD Px@signal tracker 368 vs log 368.775**, paste truncation, fix to 368.775 before GLD's +5d \~7/2). Resolutions 6/17 +5d, 6/10 +10d, 5/27 +20d entered (24/24 each); recalc 0 errors; totals 643, BUY 19. **6/17 cohort goes AGAINST the guardrail — and it's not compressed:** Section 4 r55 50-59% **38.5% (n=13), NO**; band order **60-69% 75% (6/8) > 50-59% 38% (5/13) > 40-49% 33% (1/3)**, cohort-wide **50%** (mixed — bands had room to separate, and 60-69 separated *above*). **The clean test arrived and favored 60-69.** Cumulative lead **narrows +8.5 → +5.5pt**; **pairwise held just 1 of 3** (the 1, 6/16, was compressed noise); absolute **drift −5.8pt**. Read shifted from 'ranking holds, regime sensitivity' to **'guardrail under real pressure'** — not yet definitive (n=3, 60-69 n=8 on 6/17), but the next non-compressed cohorts are decisive. **H1 lag still 5** (WMT 6/17 −3.51% **NO** — first live WMT miss; peak r +0.600). **5/27 +20d monotonic** (2.67→5.16→7.67), magnitude **6-for-7** (5/22 lone exception); +20d −5.99%. **Registry unchanged**; EXTENDED +5d 5/12, +10d 7; **KEEP 70%**.
* 6/26 (Phase 3-A Day 9) — **4th live cohort + morning signals cross-validate** (24/24 reconcile; rows 648–671; **first SELL signal — CBRS 68%**, advisory-only, resolves \~7/6). **GLD fix half-landed** — now 367.775 vs log 368.775 (decimals right, dollars off by $1; needs 368.775). Resolutions 6/18 +5d, 6/11 +10d, 5/28 +20d entered (24/24 each); recalc 0 errors; totals 667, BUY 19. **6/18 = 2nd straight non-compressed cohort to favor 60-69:** Section 4 r56 50-59% **63.6% (n=11), NO**; band order **60-69% 83% (5/6) > 50-59% 64% (7/11) > 40-49% 14% (1/7)**, cohort-wide **54%** (50-59 did *well* — above certified — but 60-69 did better). **All 3 non-compressed live cohorts (6/15, 6/17, 6/18) favor 60-69; pairwise held 1 of 4** (the 1, 6/16, compressed noise). Cumulative lead **compressed +8.5 → +4.1pt** — below the Phase 2 +7–13pt range, driven by 60-69 climbing 48→52%. Read moved from 'under pressure' to **'fairly clearly not holding out-of-sample'** — recommend a formal **Phase 2 Q1 re-examination** (6/22 = confirmation; lead still positive, per-cohort 60-69 n small). Phase 3-A working as designed — a non-generalizing finding caught advisory-only. **H1 lag still 5** (WMT 6/18 −1.53% YES, 3 of 4 live). **5/28 +20d monotonic** (3.28→4.69→7.27), magnitude **7-for-8**; +20d −5.41%. **Registry EXTENDED +10d → 8** (6/11 NVDA −3.71% NO); +5d 5/12; **KEEP 70%**.
* 6/29 (Phase 3-A Day 10) — **CONFIRMATION READ + morning signals cross-validate** (24/24 reconcile, all HOLD, rows 672–695). **GLD fixed** (Px@signal now 368.775). Resolutions 6/22 +5d, 6/12 +10d, 5/29 +20d entered (24/24 each); recalc 0 errors; totals 691, BUY 19. **6/22 = 4th non-compressed cohort, favors 60-69 again:** Section 4 r57 50-59% **54.5% (n=11), NO**; band order **60-69% 66.7% (4/6) > 50-59% 54.5% (6/11) > 40-49% 33% (2/6)**, cohort-wide **50%** (mixed). **All 4 non-compressed live cohorts (6/15, 6/17, 6/18, 6/22) favor 60-69; pairwise held 1 of 5** (the 1, 6/16, compressed noise). Cumulative lead **+8.5 → +3.3pt** — below the Phase 2 +7–13pt range, 60-69 climbing to 52.5%. **The Q1 50-59>60-69 guardrail is firmly NOT holding out-of-sample — trigger met; proceed with the regime-stratified Q1 re-examination.** Phase 3-A worked as designed. **H1 lag still 5** (WMT 6/22 −2.56% YES — 4 of 5 live; peak r +0.594). **5/29 +20d monotonic** (4.95→5.14→7.62), magnitude **8-for-9**; +20d −4.72%. **Registry EXTENDED +10d → 10** (6/12 VTI +0.41% YES — rare win, NVDA −5.17% NO); +5d 5/12; **KEEP 70%**.
* 6/30 (Phase 3-A Day 11) — **+10d horizon read + Q1 re-examination built.** Morning signals cross-validate 24/24 (all HOLD, rows 696–719); resolutions 6/23 +5d, 6/15 +10d, 6/1 +20d complete (24/24 each); recalc 0 errors; totals 715, BUY 19. **+10d confirms the 6/15 inversion** — 60-69 leads at both horizons (67% vs 50-59 47% at +10d), gap *widens* (not a +5d artifact). **6/23 = 6th live cohort, first CLEAN (75%), still favors 60-69** (86% > 80%, Section 4 r58, Pattern NO); 5 non-compressed cohorts all favor 60-69, pairwise held 1 of 6; cumulative lead **+3.3 → +2.2pt** (near crossover). **`--stratify-regime` built into guardrail\_trace.py** (regime\_of() single-sourced, scoreboard byte-identical; writes regime\_stratification.md). **Verdict — NOT a regime artifact:** Phase 2 50-59 led in non-compressed cohorts **+5.8pt** (clean **+9.1pt**, mixed +2.2pt) — real across regimes — yet the SAME non-compressed regimes go **−19.4pt** live (mixed −21.2, clean −5.7, both flip sign). The 50-59>60-69 ordering **FLIPPED between Phase 2 and now** → "something changed," regime composition does not explain it (candidates: vol-regime shift, signal-generator drift, Q1 overfit, live small-n; 60-69 live n=44). **H1 lag still 5** (WMT 6/23 −5.22% NO, 4 of 6; peak |r| 0.584). **6/1 +20d non-monotonic** (4.72→3.85→6.79), 2nd exception, magnitude **8-for-10**; +20d −3.48%. **Registry unchanged**, KEEP 70%.
* 7/1 (Phase 3-A Day 12) — **7th live cohort + weekly review + worksheet v2.** Morning signals cross-validate 24/24 (23 HOLD + 1 BUY = GLD 65% scout; rows 720–743); resolutions 6/24 +5d, 6/16 +10d, 6/2 +20d complete; recalc 0 errors; totals 739, BUY 20. **6/24 = 7th live cohort, clean (62%), favors 60-69 88% (7/8) vs 50-59 62% (5/8), Held NO** — 6 of 6 non-compressed cohorts favor 60-69, pairwise held 1 of 7. **Cumulative lead +2.2 → +0.4pt — at crossover** (50-59 56.8% vs 60-69 56.4%). **Q1 re-examination refreshed (7 cohorts): live non-compressed −19.4 → −21.2pt, clean −5.7 → −14.4pt** — the flip deepens as n grows (weak evidence against pure small-n; live 60-69 n=52). **6/16 both near-misses miss +10d** (VTI −0.77%, NVDA −5.52%; extended +10d 1/12 = 8.3%); GLD 65% added (20 near-misses, 7 LOCKED + 13 EXTENDED); **KEEP 70%** reinforced. **H1 lag still 5** (WMT 6/24 −8.99% NO — held 55% through the drop; 4 of 7; peak +r 0.372). **6/2 +20d non-monotonic** (5.07→4.85→7.44), 3rd exception, magnitude **8-for-11**; +20d −5.14%. **Closeout Worksheet → v2**: H1 now 7 of ≥8 (verdict \~7/2), sample depth 60-69 n 44→52, Q1-R deepening but open — roll-up unchanged, **5 of 5 open → NOT YET / EXTEND**.
* 7/2, processed 7/6 (Phase 3-A Day 13) — **Crossover + H1 verdict drafted + worksheet v3.** 7/2 signals 24/24 clean (all HOLD, rows 744–767, variant "A" ×24); resolutions 6/25 +5d, 6/17 +10d, 6/3 +20d complete; recalc 0 errors; totals 763, BUY 20; Rob's weekly-review sheets read as authoritative (not regenerated). **6/25 = 8th live cohort (mixed): 60-69 71% > 40-49 50% > 50-59 44% — cumulative lead crosses NEGATIVE (−0.7pt)**, pairwise 1 of 8. **H1 ≥8-cohort gate MET; verdict (b) drafted for lock** — lag 5 in 8/8, corr +0.198 decomposes to the 7/1–7/2 WMT catch-up (−0.153 without it; catch-up IS the lag signature); retire prompt remedy, carry finding to 3-B feature-level; provenance condition: confirm variant "A" includes the H1 input. **6/17 +10d diverges** (50-59 62% > 60-69 50% — first +10d flip back). **Composition check (Q1-R probe #1): band populations shifted** — 60-69 BUY share 21%→3%, PM 29%→75% within-band, NVDA exits 60-69, SPY/QQQ/XLU enter 50-59 → narrows root cause toward generator drift/population shift; stratify @8 cohorts −21.8pt non-compressed. **Weekly MDs**: H3 baseline 26/737 = 3.5% flips (NVDA 38.7%/VTI 20%/GLD 12.9%; 54% of flips on <1% moves; endpoint recommendation: day-over-day small-move flip rate) → gate YELLOW; H2 baseline ratio 0.85 hypothesis-adverse (WMT/GM pair replicates 1.68/1.10 but doesn't generalize; re-scope flagged); H4 2 of 3 reopen conditions met (n=4 of ≥10; GLD 7/9 adds). **6/3 +20d non-mono** (5.73→4.76→7.06, 3rd consecutive shock-cluster exception), monotonic 8-for-12, net-growth 12-for-12. Registry unchanged (20 near-misses; extended +10d 1/12 = 8.3%); **KEEP 70%**. **Worksheet v3: H1 MET (lockable), H3 critical path — 4 of 5 open post-lock → NOT YET / EXTEND.**
* 7/6 (Phase 3-A Day 14 — FINAL) — **Phase closed by sign-off; closeout memo + 3-B kickoff produced.** 7/6 signals 24/24 clean (all HOLD, rows 768–791); resolutions 6/26 +5d, 6/18 +10d, 6/4 +20d complete; recalc 0 errors; totals 787. **First SELL missed hard**: CBRS 68% → +14.61% NO (n=1; supports Q3 Path A exclusion). **6/26 = 9th/final cohort, first non-compressed hold** (50-59 70% > 60-69 62%, mixed 54%) — final tally pairwise **2 of 9**, cumulative **−0.6pt**, non-compressed stratum **−18.0pt** (vs P2 +5.8pt), 7 of 8 non-compressed favored 60-69; +10d reads split 2–2 (reversal is +5d-sharp). 6/4 +20d monotonic — net-growth **13-for-13** final, monotonic 9-for-13 (shock cluster annotated). **Dispositions**: H1 VERDICT (b) LOCKED (provenance box open, documented; implementation → feature level); H3/H2 DESCOPED (untested; H2 baseline-adverse); Q1-R PARKED (T1/T2/T3); Gate S waived; A/B terminated; **guardrail SUSPENDED as decision input**. Registry KEEP 70%; H4 2-of-3 (GLD 7/9 adds HIGH-DQ n). Deliverables: **Phase3A\_Closeout\_Memo.md**, **Phase3B\_Kickoff\_Prompt.md**, final regime\_stratification.md.
* **7/7 (Phase 3-B Session 1 + Day 1) — phase transition: WS2 (S1+D1) built, deployed, first canonical cohort live.** **Provenance box CLOSED (CONFIRMED):** variant "A" carried the H1 prior-5-day input throughout 3-A — git frozen at go-live (`246494e`, 6/15 19:00 CDT) through 7/6, the 7/6 runtime log shows the `pricehistory` fetch on all 24 tickers, and the pre-go-live snapshot lacks the block; **verdict (b) stands as signed** (caveat: the 6/15 AM run predates the commit stamp → 13 of 14 sessions git-provable, immaterial to the verdict). **WS2 built at feature level — generator era "A-S1D1":** the kickoff's named trailing-5-day input (Lever 1) was found **already deployed** = the very remedy the lock scored ineffective, so WS2 pivoted to **S1** (prior-signal state input — the model's own last-5 *raw* confidences per ticker, the untried model-side channel) + **D1** (mechanical post-model confidence damping, θ5 / K1.5 / cap15 / floor35, sized on the WMT arc). **Ruling R1 — both levers together** → two-channel readout (`confidence\_raw` = model channel, operative = system truth, both logged every line; S1 feeds raw only, so D1 never contaminates the model-side test). **Ruling R2 — pool eras for the T2 counter** (the A-S1D1 stamp preserves post-hoc stratifiability). **Pre-deploy parser bug caught:** `parse\_log\_to\_tracker` `ACCOUNT\_RE` hardcoded `2 DRY RUN|3-A` → would have imported every 3-B row as Account="Unknown" (same class as the 6/15 `analyze\_log` break); fixed phase-agnostic before go-live. **Deploy hygiene — run-1 superseded:** first 7/7 run (09:45) skipped the seed → cold start (S1 empty, D1-only), archived `signals\_2026-07-07\_run1\_coldstart.log`, nothing pasted; re-seeded from the tracker (24 tickers; WMT chain …45, GM …52), re-ran (10:18) = **canonical 7/7 cohort, the first full S1+D1 cohort** (acceptance clock starts here; `WS2\_DEPLOY=2026-07-07`). **Cross-check 24/24** — log↔tracker operative reconcile verified incl. the damped names; DQ **18 HIGH / 6 MED / 0 LOW**; all HOLD; **0 near-misses (VTI 60% HOLD, not a BUY) → registry stays 20** (corrects an intra-session mis-count of 21 — the run-1 VTI BUY lived only in the archived cold-start log); totals **811, BUY 20, SELL 1**. **D1 first live activations (raw→op):** PWR 55→47 (trail −10.19%, damp 8), SND 42→40 (−6.19%, 2), AIQ 48→47 (−5.84%, 1), CBRS floored 35→35 (−20.48%, pre-floor 15) — arithmetic verified. **S1 first live read:** tracers WMT/GM both quiet (−1.16% / −1.02%, sub-material) → **null cohort for the acceptance instrument**; corroborating (non-tracer) **PWR raw stepped 62→55 same-session, reasoning cited "the stale 62% HOLD"** — the staleness-break S1 was built to surface (NTR "62 from 58", NKE "42 to 52" also verbally engaged their chains); **counterweight — anchoring also visible** (WMT 55→45, XLU 62→55, FTI 65→60, VTI BUY 65→HOLD 60 snapped toward chain endpoints vs the S1-free run). Both faces on Day 1; **no verdict** (n=1, diagnostic only — the cold/canonical pair differ by intraday drift + ordinary generator variance). **Weekly monitors (generated 7/07 15:27–28):** h1 traces **WMT lag 2 / GM lag 1 — full-series corr-scan BASELINE only** (§4b: a short-slice ≤2 is not success; the failed generator already reads lag 1), and **WMT's lag-5 episode (52→45 on 7/01) is entirely PRE-deploy** — post-deploy WMT is flat, so the acceptance read awaits a fresh material move on a tracer. **T2 depth: live 60-69 +5d-resolved n = 74** (6/29 cohort +7; band accuracy validated vs the memo — 50-59 n=107 @ 54.2%, 60-69 n=74 @ 63.5%), target 88 → **short 14 (\~2 cohorts, \~7/9–10)**. **T2 LEAD gate DISARMED — the two gates diverge:** `regime\_stratification.md` (through 6/29) puts the **non-compressed stratum lead at −13.1pt** (from −18.0 at close — the 6/29 non-compressed 50-59 hold, 70% > 60-69 43%, narrowed it), now **above the −15pt trigger**; cumulative all-cohort lead flipped +0.5pt, pairwise held 3 of 10. So **depth is arming toward 88 (74 now) while the lead has risen off the trigger — T2 is currently armed on NEITHER gate**, and will not fire even at n ≥ 88 unless the non-compressed lead drops back ≤ −15pt (margin thin at 1.9pt; live 60-69 n small → volatile). **The Q1-R finding is undisturbed:** Phase 2 non-compressed +5.8pt (clean +9.1pt — never a mere compressed artifact) vs Phase 3-A −13.1pt = a **\~19pt within-regime swing, sign firmly flipped** — only the specific tripwire is currently unmet. **Registry 20** (GLD 65% 7/1 → 7/9 pending, the only open +5d; also H4 HIGH-DQ n → 5); **H4 stays demoted** — HIGH 57.3% ≥ MEDIUM 48.7% ✓, near-miss HIGH 3/4 = 75% ✓, n-blocker 4. **git push `d4514fe`** (WS2 bundle on `origin/main`; a stray `Phase 3B Manifest/` duplicate folder + a non-canonical commit message went up with it — amend recommended, cosmetic). Session deliverables: `WS2\_H1\_Feature\_Spec.md`, `WS2\_Deploy\_Notes.md`, `Daily\_Workflow\_v4\_0\_Phase3B.docx`, `Phase3B\_Exit\_3C\_EDGAR\_Entry\_Criteria\_v1.docx` (G1–G6 exit / E1–E6 EDGAR entry / DP-1..5).
* **7/8–7/9 (Phase 3-B Days 2–3, monitoring) — GLD near-miss resolves (HIT); T2 depth reaches the doorstep (n=87/88).** **7/8 (reconstructed from tracker):** 24 signals pasted, no near-miss BUYs, no data-integrity items; folded here for continuity. **7/9 cross-check 24/24** — log↔tracker operative reconcile clean; **D1 quiet — zero effective damping today** (vs 4 activations 7/7: the −10% PWR / −20% CBRS trails rolled out of the 5-day window as prices steadied — calmer tape); DQ **17 HIGH / 7 MED / 0 LOW**; all HOLD; **0 near-misses (no BUY at all) → registry stays 20**; totals **859 rows**, BUY 20, SELL 1. **Resolution — GLD 65% near-miss (7/1) → +5d +0.82% → HIT** ($375.10 → $378.18); the 7/1 cohort resolved 24/24 and the registry's last pending +5d is filled (registry unchanged at 20). **Monitor deltas:** **T2 DEPTH now n=87** (live 60-69 +5d-resolved; from 74 at 7/7 — the 6/30 +6 and 7/1 +7 cohorts), **one short of the 88 trigger → crosses on the next cohort (7/2 resolves 7/10)**; band accuracy 50-59 n=131 @ 54.2%, 60-69 n=87 @ 64.4%. **T2 LEAD (non-compressed) −13.6pt** (from −13.1 at 7/7; the 7/1 cohort favored 60-69 86% > 50-59 67%, 6/30 was compressed and excluded), **still above the −15pt trigger by 1.4pt**. **→ The T2 picture has sharpened: depth is effectively satisfied (crosses 88 tomorrow), so the non-compressed lead is now the SOLE remaining gate** — T2 fires iff that lead dips ≤ −15pt as depth crosses 88; it is hovering −13 to −14pt on small, volatile 60-69 n → **read the non-compressed lead every session now.** Scoreboard (cached, as of 7/1): cumulative all-cohort lead **−0.7pt** (from +0.5 at 6/29 — 6/30 \& 7/1 both favored 60-69), pairwise held **3 of 12**. **H4 watchdog:** GLD's hit takes HIGH-DQ near-miss to **n=5, 4/5 = 80%** (≥60% ✓), HIGH 57.6% ≥ MEDIUM 48.2% ✓ → **2 of 3 reopen conditions met, n-blocker now 5** (needs ≥10); stays demoted. **S1 / acceptance clock:** tracers still quiet (WMT 45→47→46, GM 52→54 — no material post-deploy episode) → **3 cohorts logged (7/7–7/9), all null for the acceptance instrument**; the ≤2-session lag read awaits a genuine move on WMT/GM. **Workflow note:** the tracker upload had an empty Return/Right **formula cache** (computed from Price columns instead) — open + save in Excel before the next weekly so `h1\_lag\_trace.py`'s +5d column is live.



**Upcoming (Phase 3-B era; every date is a trading day unless noted):**

* **7/10 (Phase 3-B Day 4, weekly review) — T2 DEPTH GATE CROSSED (n=93/88), on forecast; lead is now the sole gate and drifting away from it.** **Cross-check 24/24** — log↔tracker operative reconcile clean; **no effective damping** (calm tape continues); DQ **18 HIGH / 6 MED / 0 LOW**; **23 HOLD + 1 BUY (NVDA 63%, rejected <70)**; totals **883 rows**. **New near-miss — NVDA 63% (MEDIUM), the first since 7/7 → registry 20 → 21** (+5d resolves 7/17). **Resolution:** 7/2 cohort +5d resolved 24/24 — the cohort that carried depth over the line. **T2 (run via `t2\\\_check.py`, exact match to the 7/10 `regime\\\_stratification.md`):** **DEPTH n=93 ≥ 88 → MET (crossed today)**; **LEAD (non-compressed) −12.7pt** (from −13.6 at 7/9 — the 7/2 cohort narrowed it another \~0.9pt), **still 2.3pt above the −15pt trigger and drifting the wrong way for a fire**. Lead trail: −18.0 (6/26) → −13.1 (6/29) → −13.6 (7/9) → −12.7 (7/10). **→ T2 is now depth-satisfied; the non-compressed lead is the sole remaining gate, and it is moving OUT of trigger range, not into it** — T2 fires only if it dips ≤ −15pt. Daily read is now one command (`t2.bat`). **Weekly monitors (generated 7/10 15:09–10):** regime non-compressed −12.7pt (Phase 2 +5.8 vs Phase 3-A −12.7 = \~18.5pt within-regime swing — **Q1-R finding stands, only the tripwire eased**); **h1 WMT lag estimate now 4** (was 2, was 1 — the bounce confirms it is the noisy full-series corr-scan, **not** the acceptance instrument, §4b; WMT's trail went *positive* post-deploy, 7/9 +4.3% / 7/10 +2.6%, so still no adverse episode to test); **H4** HIGH-DQ near-miss 4/5 = 80%, HIGH 58.3% ≥ MED 48.7% ✓, n-blocker 5 (needs 10) — unchanged; **registry 21** (NVDA added; GLD 7/1 confirmed +0.8% HIT). **S1 / acceptance clock:** WMT 45→47→46→47, GM 52→52→54→55 — both drifting (GM ticking up on recovery), neither with a material adverse move → **4 cohorts logged (7/7–7/10), all null for the tracers**; still awaiting a genuine episode. **Tooling:** `t2\\\_check.py` + `t2.bat` pushed (`cb79987`) — the standing five-second T2 read; validated in-field against the regime MD today. **Notes hygiene:** file has runaway `\\\_` escaping on underscores (compounding on paste) — cleaner one-liner recorded; paste splices as plain text henceforth.
* **T2 watch — now down to ONE number** — depth n=87 → 88 (crosses 7/10, effectively satisfied); **non-compressed lead −13.6pt is the sole remaining gate**, 1.4pt above the −15pt trigger, volatile on thin 60-69 n. **Read the non-compressed lead each session**; T2 fires only if it dips ≤ −15pt (both gates simultaneous) → then run the Phase-2-vs-live prompt + distribution diff (Tier-2E kit; era-stratifiable via A-S1D1). The **Q1-R finding (\~19pt Phase-2-vs-live swing) stands regardless** of the tripwire.
* **WS2 acceptance clock** — 3 cohorts logged (7/7–7/9), **all null for the tracers** (no material move). Needs **≥ 4 informative post-deploy cohorts**: WMT (primary) / GM (secondary) each with a material trailing move + confidence response ≤ 2 sessions, read on the RAW channel (`h1\_lag\_trace … --raw-from-logs "logs\\signals\_\*.log" --suffix \_raw\_3B`).
* **H4** — HIGH-DQ near-miss n=5 (GLD hit, 80%); reopen blocker is n ≥ 10. **Registry 20**, no pending +5d.
* **Tracker hygiene** — open + save in Excel before the next weekly review (refresh the Return/Right formula cache for `h1\_lag\_trace`).
* **WS1** — triple-blend design note (T3: no band-ordering reliance) — still open. **WS3** — commodity-context modules + CBRS Path-A switch — still open.
* **3-B exit criteria** — `Phase3B\_Exit\_3C\_EDGAR\_Entry\_Criteria\_v1` (G1–G6 / E1–E6 / DP-1..5). Operating doc: `Daily\_Workflow\_v4\_0\_Phase3B`. Exit review earliest late-Jul / early-Aug.
* **Q1-R stays parked** — **T1** (mandatory pre-execution) · **T2** (above) · **T3** (no band-ordering reliance). **Guardrail SUSPENDED** as a decision input (monitor-only). **KEEP 70%.**
7/13 (Phase 3-B Day 5) — WS1 GO-LIVE (first blend cohort) AND T2 TRIPWIRE FIRED (Q1-R re-open triggered). Two milestones same day. WS1 deployed — era `A-S1D1-B1`: `confidence\_blend` on all 24, cross-check 24/24 operative (base path byte-identical — shadow-parallel intact); blend adjusted exactly ONE signal (everything else HOLD, unchanged by design — confirms the small-footprint finding). NVDA BUY base 65 → blend\_op 70: sector −0.079 (XLK slightly down, opposes) + regime +0.609 (risk-on, confirms) → adj +0.079 → 65×1.079 = 70. First live GATE-FLIP — base 65 rejected (<70), blend 70 would APPROVE; the risk-on regime lifted the near-miss BUY to the threshold. Whether right resolves +5d 7/20. G2 clock: 1 cohort logged, no resolved post-deploy rows yet → `blend\_eval` produces reads \~7/20+. T2 TRIPWIRE FIRED (confirmed `t2\_check.py`, exit 10): DEPTH n=100 ≥ 88 MET; LEAD (non-compressed) swung to −15.4pt (from −12.7 @ 7/10 → the 7/6 cohort resolved today favoring 60-69, crossing the −15 trigger), 0.4pt past. Lead trail: −18.0 (6/26) → −13.1 (6/29) → −13.6 (7/9) → −12.7 (7/10) → −15.4 (7/13, FIRE). Both gates met simultaneously for the first time. Pre-registered action: run the Tier-2E Phase-2-vs-live prompt + distribution diff (the Q1-R diagnostic; era-stratifiable via A / A-S1D1 / A-S1D1-B1 stamps). Honesty note: the lead is marginal (0.4pt past, volatile −12.7↔−15.4) — the trigger is genuinely met per the pre-registered rule, so run the diff rather than move the goalposts; but expect possible oscillation. T1 unchanged (advisory-only) — this triggers a DIAGNOSTIC, not an execution change. Cross-check: 24/24; no effective damping (calm tape); DQ 19 HIGH / 5 MED / 0 LOW; 23 HOLD + 1 BUY; 7/6 cohort +5d resolved 24/24; totals 907 rows. NVDA 65% (HIGH) = new near-miss → registry 21 → 22; H4 HIGH-DQ near-miss → 6 (pending 7/20), still short of the n ≥ 10 blocker. Band accuracy (live): 50-59 56.9% (n130) vs 60-69 72.3% (n83).

## \--7/14 (Phase 3-B Day 6) — the 7/7 cohort (first full S1+D1) resolves 24/24 at 62.5%; Q4-R's volatility artifact shows up live; NVDA repeat near-miss. Cross-check 24/24 — log↔tracker operative reconcile clean; era `A-S1D1-B1`, blend fields on all 24; no effective damping (third calm session); DQ 17 HIGH / 7 MED / 0 LOW; 23 HOLD + 1 BUY (NVDA 65, rejected <70); totals 931 rows. NVDA 65% (HIGH) new near-miss — third in five sessions (7/10 @63 MED, 7/13 @65 HIGH, 7/14 @65 HIGH) → registry 22 → 23; all three +5d pending (7/17, 7/20, 7/21). RESOLUTION — 7/7 cohort (the first full S1+D1 cohort) resolved 24/24, accuracy 15/24 = 62.5%; its 60-69 band n=8 came in 4/8 = 50%. The four D1-damped names resolved: PWR HOLD op47 → +2.20% RIGHT; AIQ HOLD op47 → +0.29% RIGHT; SND HOLD op40 → +7.66% WRONG; CBRS HOLD op35 → +15.97% WRONG. Both "wrong" ones are precisely the Q4-R volatility artifact — CBRS median |+5d move| 10.42%, SND 5.09%, so a fixed ±3% HOLD band is near-impossible for them to satisfy; yesterday's scoping predicted this pattern and it appeared unprompted the next session. (D1's direction was defensible on both — it cut conviction on signals that proved wrong — but at n=4 that is an observation, not evidence; the acceptance instrument remains the WMT/GM tracer.) Q1-R robustness check: live 60-69 = 64.8% (n=108) vs 50-59 55.3% (n=159) — the diagnosis holds. The 7/7 cohort's 50% is within normal cohort variance (60-69 by cohort has ranged 27.3%–87.5% across the live era), not a trend — logged as a watch item only. Blend, day 2 — a same-signal / different-verdict pair: NVDA repeated BUY 65 but blended 65 → 66 today vs 65 → 70 yesterday — the sector score deteriorated sharply (−0.079 → −0.44, XLK selling off) while regime softened (+0.609 → +0.514), so the overlays nearly cancelled → no gate-flip today. Context-sensitivity working as designed, and a fair caution that 7/13's gate-flip was marginal; the two resolve 7/20 and 7/21 → a natural paired comparison for `blend\_eval`. H4: HIGH-DQ near-miss 4/5 resolved = 80%, total 7 (2 pending); HIGH 59.1% ≥ MEDIUM 42.7% ✓; n-blocker (≥10) unchanged → stays demoted. DQ live: HIGH 59.1% vs MEDIUM 42.7% — stable, and per Q4-R no action (volatility composition, not miscalibration). WS2 acceptance clock: WMT 45→45→47→46→47→47→47, GM 52→52→52→54→55→55→55 — 6 post-deploy cohorts (7/7–7/14), all null for the tracers; still awaiting a material episode. Flag: tracker arrived named `claude-equity-bot-tracker.xlsx` (hyphens) rather than `tracker\_with\_registry.xlsx` — identical schema, but if it has been renamed on disk, `t2.bat` / `seed\_signal\_state.py` / the weekly harnesses all reference the old name and would not find it.

## 7/15 (Phase 3-B Day 7) — 7/8 cohort resolves 24/24 at 66.7%; the 60-69 dip diagnosed as normal variance + a rally artifact; NVDA's fourth consecutive near-miss. Cross-check 24/24 — log↔tracker operative reconcile clean; era `A-S1D1-B1`, blend fields on all 24; no effective damping (fourth straight calm session); DQ 14 HIGH / 10 MED / 0 LOW; 23 HOLD + 1 BUY (NVDA 64, rejected <70); totals 955 rows. NVDA 64% (HIGH) — fourth consecutive near-miss (7/10 @63 MED, 7/13 @65 HIGH, 7/14 @65 HIGH, 7/15 @64 HIGH) → registry 23 → 24; all four +5d pending (7/17, 7/20, 7/21, 7/22). RESOLUTION — 7/8 cohort resolved 24/24, accuracy 16/24 = 66.7%; its 60-69 band came in 3/8 = 37.5% — the second consecutive sub-50% 60-69 cohort (7/7: 50.0%, 7/8: 37.5%), i.e. yesterday's watch item. Diagnosed as NON-EVENT on two independent checks: (a) historically unremarkable — three prior runs of ≥2 consecutive ≤50% cohorts exist in the live era, every one length-2 followed by recovery; the band's cohort range is 27%–88%, so this is the 4th such run, inside normal variance; (b) it coincides with a rally — the 7/7 cohort saw 17/24 tickers up at +5d (mean +2.18%), 7/8 saw 15/24 up (mean +1.32%); rising markets push HOLDs through the +3% band (the Q4-R artifact, market-wide rather than instrument-specific). The 7/8 cohort's four biggest movers were all "wrong" HOLDs: NVDA +7.81%, AG +6.08%, AAPL +5.94%, JPM +3.93% (JPM's median move is 1.04% — a genuine outlier for that name). Q1-R HOLDS: live 60-69 = 62.9% (n=116) vs 50-59 56.3% (n=167) — lead narrowed (64.8 → 62.9) but the ordering is intact; no action (T2 retired; the diagnosis does not hinge on the current margin). DQ-mix check (second watch item) — also a non-event: today's 42% MEDIUM looked elevated against the recent 21–29% run, but the series oscillates (7/6 was 46%, 7/2 38%) → noise, not drift. Noted because Q1-R attributed part of the go-live gain to the DQ-mix flip; a genuine MEDIUM uptrend would partly unwind that composition effect. It isn't happening. Blend, day 3 — the NVDA series is becoming a well-controlled natural experiment: same name, same call, three different verdicts driven purely by sector/regime context — 7/13 base 65 → blend 70 (GATE-FLIP; sec −0.079 / reg +0.609); 7/14 base 65 → blend 66 (no flip; sec −0.44 / reg +0.514); 7/15 base 64 → blend 67 (no flip; sec −0.311 / reg +0.673) — the blend tracking XLK's swings. They resolve back-to-back (7/17, 7/20, 7/21, 7/22) → an overlay-predictive-value read arriving earlier than the ≥5-cohort G2 window. H4: HIGH-DQ near-miss 4/5 resolved = 80%, total 8 (3 pending); HIGH 59.6% ≥ MEDIUM 43.9% ✓; blocker (n≥10 resolved) unchanged → stays demoted. WS2 acceptance clock: WMT 45→47→46→47→47→47→47 (flat), GM 52→52→54→55→55→55→55 (flat) — 7 post-deploy cohorts (7/7–7/15), all null for the tracers; still awaiting a material episode. Watchlist question raised (no change made): replacing CBRS with JEPI was considered — CBRS is NOT in `main.py` (scout list is only SPY/QQQ/VTI/NVDA/GLD; the watchlist is `sorted(all\_held) + WATCHLIST\_SCOUT`, so CBRS is signaled because it is HELD in Schwab). Two independent decisions: selling CBRS is a portfolio action, adding JEPI is a `WATCHLIST\_SCOUT` edit. Research finding: removing CBRS alone would raise live accuracy 53.9% → 55.7% (+1.8pt) with zero model change (and narrow the HIGH−MED gap +16.4 → +13.4pt; CBRS is 13 of its 15 signals at MEDIUM, median |+5d move| 10.42%, accuracy 13.3%); swapping it for a structurally low-vol covered-call ETF (JEPI's proxies: SCHD 1.00% median move / 93.3% acc; XLU 0.80% / 100%) would inflate every accuracy number further — a deliberate re-run of the exact composition confound Q1-R spent a session untangling. Ruling: no mid-window population change — if JEPI is wanted, land it at the 3-B exit / 3-C entry boundary where a population change is expected, documented and era-stratifiable. A portfolio decision on CBRS remains Rob's alone and must not be driven by data-collection convenience; if it happens, record the date as a population-change boundary and treat pre/post accuracy as non-comparable (same handling as the go-live cutover).

* **7/16 (Phase 3-B Day 8) — both watch items CLOSED as non-events (60-69 bounced to 87.5% on cue); GLD's near-miss reverses at +10d (KEEP-70% reinforced); NVDA's fifth consecutive near-miss with visible conviction decay.** **Cross-check 24/24** — log↔tracker operative reconcile clean; era `A-S1D1-B1`, blend fields on all 24; DQ **16 HIGH / 8 MED / 0 LOW**; **23 HOLD + 1 BUY (NVDA 62, rejected <70)**; totals **979 rows**. **D1 fired after four quiet sessions** — AG 45→44 (trail −5.93%, damp 1), AIQ 44→43 (trail −5.94%, damp 1); arithmetic verified; small damps, calm tape continuing. **WATCH ITEM 1 — 60-69 cohort accuracy: CLOSED, non-event.** The 7/9 cohort's 60-69 band came in **7/8 = 87.5%**, ending the two-cohort sub-50% run (7/7: 50.0%, 7/8: 37.5%) at exactly length two — **the 4th such run in the live era, and the 4th to recover immediately**, precisely as the 7/15 historical check predicted. Live **60-69 = 64.5% (n=124)** vs 50-59 **55.1% (n=176)** → **Q1-R's ordering intact and the lead widened back out** (62.9 → 64.5). **WATCH ITEM 2 — DQ mix: CLOSED, non-event.** Pulled back to **33% MEDIUM** (from 42% on 7/15), continuing to oscillate inside its 21–46% range → confirmed noise, not drift; Q1-R's composition driver is not unwinding. Both items come off the watch list absent something genuinely new. **RESOLUTION — 7/9 cohort resolved 24/24, accuracy 14/24 = 58.3%** (16/24 tickers up at +5d — another mildly rising tape). **RESOLUTION — GLD 7/1 near-miss (65%) at +10d: −2.70% → WRONG** (it was RIGHT at +5d with +0.82%) — a horizon flip, consistent with the standing 3-A finding that near-miss BUYs failed both forward horizons live → **further support for the KEEP-70% gate** (the registry asks "should these rejected BUYs have been taken?"; GLD's +10d answer is no). **NVDA 62% (MEDIUM) — fifth consecutive near-miss (7/10 @63 MED, 7/13 @65 HIGH, 7/14 @65 HIGH, 7/15 @64 HIGH, 7/16 @62 MED) → registry 24 → 25**; all five +5d pending, resolving consecutively 7/17, 7/20, 7/21, 7/22, 7/23. **The series is now decaying on two axes at once:** base conviction grinding down **65 → 65 → 64 → 62** and self-assessed **DQ slipping HIGH → MEDIUM**, while the model keeps calling BUY into a weakening sector (XLK sec −0.444) that a strengthening risk-on regime (reg +0.747) partly offsets. Blend trajectory: 7/13 **65 → 70 (GATE-FLIP)**, 7/14 65 → 66, 7/15 64 → 67, 7/16 62 → 65 (no flips after the first). Whether the conviction decay reflects the S1 state loop (the model reading its own softening chain) or plain price action is **not separable from one series** — but it is exactly the behavior S1 was built to surface; **observation only, no verdict.** **H4:** unchanged — HIGH-DQ near-miss **4/5 resolved = 80%**, total 8 (3 pending); HIGH 60.3% ≥ MEDIUM 43.1% ✓; blocker (n≥10 resolved) still the gate → stays demoted. **WS2 acceptance clock:** WMT trail +0.25% (conf 47 flat), GM trail −0.66% (conf 54) — **8 post-deploy cohorts (7/7–7/16), all null for the tracers**; still awaiting a material episode.
--
7/17 (Phase 3-B Day 9) — NVDA's first near-miss resolves WRONG (gate correct); the near-miss aggregate now strongly supports KEEP-70%; the blend records its FIRST DISCOUNT. Cross-check 24/24 — log↔tracker operative reconcile clean; era `A-S1D1-B1`, blend fields on all 24; no effective damping; DQ 17 HIGH / 7 MED / 0 LOW; 23 HOLD + 1 BUY (NVDA 62, rejected <70); totals 1,003 rows. NVDA 62% (HIGH) — sixth consecutive near-miss → registry 25 → 26; five still pending (7/13, 7/14, 7/15, 7/16, 7/17), resolving 7/20–7/24. RESOLUTION — NVDA 7/10 near-miss (63%, MEDIUM) +5d = −3.09% → WRONG; the 70% gate was correct (the rejected BUY would have lost). NVDA's full registry history reframes the series: 20 entries back to 5/19; of the 15 resolved, only 5 would have paid = 33.3%. The model has wanted to buy NVDA at 62–68% for two months and the gate has been right to refuse \~2 of 3 times. Aggregate — ALL resolved near-miss BUYs: 10/21 = 47.6% → fewer than half of rejected BUYs would have been profitable: live evidence reinforcing KEEP-70%, now alongside GLD's +10d reversal (7/16). RESOLUTION — 7/10 cohort resolved 24/24, accuracy 14/24 = 58.3%; 60-69 band 4/7 = 57.1%; only 10/24 tickers up at +5d — the tape turned down (vs 15–17/24 up in the prior three cohorts). BLEND — first DISCOUNT recorded: NVDA base 62 → blend 58 (sector collapsed to −0.847, XLK selling off hard; regime softened to +0.465 → overlays net-negative for the first time). Series to date: 7/13 65→70 (GATE-FLIP, confirm), 7/14 65→66 (confirm), 7/15 64→67 (confirm), 7/16 62→65 (confirm), 7/17 62→58 (DISCOUNT). Mechanically important: `blend\_eval`'s primary read compares CONFIRMED vs DISCOUNTED signals, and until today the discount arm was empty — the test could not run at all. It now has both arms (4 confirm / 1 discount), all on the same ticker and same call → unusually well-controlled, though n is tiny. Q1-R holds: live 60-69 = 64.1% (n=131) vs 50-59 55.7% (n=185). H4: HIGH-DQ near-miss 4/5 resolved = 80%, total now 9 (4 pending: 7/13, 7/14, 7/15, 7/17 — 7/16 was MEDIUM); HIGH 60.7% ≥ MEDIUM 42.6% ✓. H4's reopen blocker is now close — those four resolve 7/20–7/24 taking resolved 5 → 9; blocker is n ≥ 10, so one further HIGH-DQ near-miss (likely on NVDA's cadence) would trip it. If the 80% hit rate survives to n=10, H4 reopens as a live question (are HIGH-DQ near-misses worth taking?) — be ready, and note the contrast: HIGH-DQ near-miss 80% (n=5) vs ALL near-miss 47.6% (n=21), i.e. MEDIUM-DQ near-misses ≈ 6/16 = 37.5%. WS2 acceptance clock: WMT pinned at conf 47 for nine straight sessions (trail +0.72%), GM 55→54 (trail +0.47%) — 9 post-deploy cohorts (7/7–7/17), all null for the tracers; still no material episode.
--
7/20 (Phase 3-B Day 10) — the GATE-FLIP VERDICT: the blend LOST (base was right); first `blend\_eval` read is directionally against the blend but n=1; NVDA seventh near-miss + second discount. Cross-check 24/24 — log↔tracker operative reconcile clean; era `A-S1D1-B1`; D1 fired: AG 40→37 (trail −6.82%, damp 3); DQ 19 HIGH / 5 MED / 0 LOW; 23 HOLD + 1 BUY (NVDA 61, rejected <70); totals 1,027 rows. NVDA 61% (HIGH) — seventh consecutive near-miss → registry 26 → 27; five pending (7/14, 7/15, 7/16, 7/17, 7/20). RESOLUTION — 7/13 cohort (first WS1 blend cohort) resolved 24/24, accuracy 17/24 = 70.8% (strong cohort). ★ GATE-FLIP VERDICT — NVDA 7/13: base 65 (REJECT, <70) vs blend 70 (APPROVE). +5d = −2.05% → the APPROVE (blend) was WRONG, the REJECT (base) was RIGHT → BLEND LOST. The one gate-changing decision the blend has made in its entire live history was a bad call — the risk-on regime that drove the 65→70 lift pushed conviction the wrong way on a name that fell. `blend\_eval --since 2026-07-13` (6 cohorts, 24 resolved, 6 adjusted = 4 lift / 2 cut): overlays-CONFIRMED n=1 acc 0.0% (−2.05%); overlays-DISCOUNTED 0 resolved yet; gate-flip net −1 (blend worse). Read, honestly threefold: (1) directionally early evidence is AGAINST the blend; (2) it is NOWHERE near a G2 verdict — one resolved flip on one ticker, vs the bar of confirm>discount across folds AND gate-flip net ≥ 0 over ≥5 cohorts; (3) the single-name caveat now bites — the entire blend footprint is NVDA, so even when all six resolve it is a one-ticker result (the caveat logged 7/17; today is why it mattered). Quiet irony worth tracking: the overlays leaned risk-on all week and kept trying to LIFT NVDA while the base model's conviction was DECAYING (65→61) and the near-misses kept resolving wrong — so far the base's skepticism has beaten the blend's context. Early, but that is the direction. TRACKER — EMPTY FORMULA CACHE (verified; supersedes an in-session mis-diagnosis): the Return +5d/+10d and Right?(5d) columns are entirely formulas (`=IF(H="","",(H-G)/G)`) whose stored values are absent because the workbook has not been recalculated in Excel since the last paste — `openpyxl(data\_only=True)` therefore reads `None` for every one of them. This is an EMPTY cache, not a stale or corrupted one; the file is not damaged and contains no bad values (a full column scan found 0 absurd cached figures). Correction for the record: a `193%` band figure appeared mid-session and was initially attributed to a corrupted tracker cell — it was in fact a divide bug in an ad-hoc diagnostic print on this end, not data from the tracker; the tracker was never at fault. The operational consequence is real and now verified by code inspection: `h1\_lag\_trace.py` reads `r5` (col 11), `r10` (col 12) and `right5` (col 14) directly (it pulls Price only for display), so on an unrecalculated workbook its correlations, +10d arc and calibration guardrail run on blanks. Fix before each weekly: open the tracker in Excel → F9 → save. Everything in this entry is price-computed and unaffected. H4 — total reached n=10 but RESOLVED only 6, and the hit rate DROPPED to 4/6 = 67% (from 80%) as NVDA 7/13 + another resolved wrong; the reopen bar is n ≥ 10 resolved at ≥ 60% — so the reopen question is getting WEAKER, not stronger; four more HIGH-DQ near-misses resolve this week and will settle it (if they keep resolving like NVDA's, H4 stays demoted on merit). KEEP-70% reinforced again: all resolved near-miss BUYs 10/22 = 45.5%. Q1-R holds (band figures this session were price-computed and clean; nothing in the data suggests a change). BLEND — second DISCOUNT: NVDA 61 → 57 (sector −0.814, XLK still weak). WS2 acceptance clock: WMT pinned at conf 47 for TEN straight sessions (trail −0.08%), GM 54 (trail −0.75%) — 10 post-deploy cohorts (7/7–7/20), all null for the tracers; still no material episode.

\---

## 7/21 (Phase 3-B Day 11) — H4's hit rate falls BELOW its reopen bar (now failing on merit, not sample); NVDA 7/14 resolves wrong with blend and base AGREEING; tracers move but not materially. Cross-check 24/24 — log↔tracker operative reconcile clean; era `A-S1D1-B1`; no effective damping; DQ 18 HIGH / 6 MED / 0 LOW; 23 HOLD + 1 BUY (NVDA 61, rejected <70); totals 1,051 rows. NVDA 61% (HIGH) — eighth consecutive near-miss → registry 27 → 28; five pending (7/15, 7/16, 7/17, 7/20, 7/21). RESOLUTION — 7/14 cohort resolved 24/24, accuracy 16/24 = 66.7% (12/24 up — flat tape). RESOLUTION — NVDA 7/14 near-miss (65%, HIGH) +5d = −0.43% → WRONG; the gate was right again. Notable for WS1: the blend did not flip this one (blend 66, below the 70 gate), so blend and base AGREED and both were correctly cautious — the first case where the overlays' judgment aligned with the correct outcome. ★ H4 — the reopen question is now FAILING ON MERIT, not just sample size. HIGH-DQ near-miss hit rate 4/7 = 57%, which is below the ≥60% reopen bar; trajectory 80% → 67% → 57% as the NVDA cases resolve wrong. Criteria status: n ≥ 10 resolved → 7 (short); hit ≥ 60% → 57% (now FAILING); HIGH ≥ MEDIUM overall → 61.9% vs 43.9% ✓. A week ago H4 looked one signal from reopening; it is now failing the quality bar itself. If this holds, H4 stays demoted because the evidence says so — a cleaner outcome than tripping on a technicality. KEEP-70% strengthening again: all resolved near-miss BUYs 10/23 = 43.5% (from 45.5%) — under half of rejected BUYs would have paid. Q1-R holds: live 60-69 = 64.3% (n=143) vs 50-59 57.1% (n=203). DQ live: HIGH 61.9% vs MEDIUM 43.9% — stable; no action per Q4-R. BLEND: NVDA 61 → 62 (sector −0.232, regime softened to +0.288 — the weakest risk-on reading of the series); no flip. WS2 acceptance clock — tracers MOVED but it is NOT an episode: GM 54 → 58 (+4, the largest post-deploy single-session move) and WMT 47 → 45, ending WMT's ten-session pin. But GM's trail was +0.63% — confidence rose on a SMALL POSITIVE move, whereas the acceptance test requires a material ADVERSE trailing move with a ≤ 2-session confidence response. This does not qualify. 11 post-deploy cohorts (7/7–7/21), still all null for the acceptance instrument.

## 7/22 (Phase 3-B Day 12) — regime flips RISK-OFF for the first time (both BUYs discounted); first double near-miss session; NVDA's first winning resolution reverses H4 back above its bar; WMT closes to 0.6pt of the first acceptance episode. Cross-check 24/24 — `signals\_2026-07-22.log` ↔ `tracker\_with\_registry.xlsx` operative reconcile clean; era `A-S1D1-B1`; D1 fired: NKE 38→36 (trail −6.34%, damp 2); DQ 16 HIGH / 8 MED / 0 LOW; 22 HOLD + 2 BUY; totals 1,075 rows. ★ REGIME FLIPPED RISK-OFF — `regime\_score −0.205`, the first negative reading after eleven consecutive positives (+0.288 to +0.747). Immediate blend consequence: both BUYs were DISCOUNTED — NVDA 62 → 59 (sector −0.154), GLD 62 → 60 (sector 0.0, so the cut is regime-only) — discounts #3 and #4, and the first driven by the cross-asset leg rather than sector. DOUBLE NEAR-MISS (first of the run): NVDA 62% (MEDIUM) + GLD 62% (HIGH) → registry 28 → 30. GLD's first near-miss since 7/1 (which resolved +0.82% at +5d then reversed to −2.70% at +10d). RESOLUTION — 7/15 cohort resolved 24/24, accuracy 16/24 = 66.7% (15/24 up). RESOLUTION — NVDA 7/15 near-miss (64%, HIGH; blend 67, no flip) +5d = +1.13% → RIGHT — the first of the eight-deep NVDA near-miss series to pay. H4 REVERSED back above its bar: HIGH-DQ near-miss hit rate 57% → 62% (5/8) on that resolution; criteria now n ≥ 10 resolved → 8 (short), hit ≥ 60% → 62% (PASSING), HIGH ≥ MEDIUM ✓. Correction to the 7/21 entry: yesterday's "failing on merit" read was one resolution deep and did not hold — H4 is again short on sample only. Record the reversal rather than the stronger claim. KEEP-70% still supported: all resolved near-miss BUYs 11/24 = 45.8% (from 43.5% — the NVDA hit lifted it, still under half). Q1-R holds: live 60-69 = 65.1% (n=149) vs 50-59 57.7% (n=208). ★ WS2 — WMT is 0.6pt from the first post-deploy episode. Trailing 5-session move −4.40% (`tracker\_with\_registry.xlsx`) / −4.91% (log H1 tag) against the pre-registered THETA = 5.0%, so it does NOT formally qualify and the clock still reads 0 post-deploy episodes in 12 sessions. But the response behaviour is already visible: WMT confidence 47 → 45 → 42 over three sessions. GM is the mirror image — trailing +6.25%, confidence 54 → 58 → 63. This is the closest the tracers have come since deploy; a modest further WMT slide would produce G1's first genuine test case. `monitor\_strip.py` reads: WS1/G2 gate-flip net −1, confirm 33% (n=3) vs discount 0 resolved; WS2/G1 both tracers NO TEST CASES YET; H4 62% (5/8); KEEP-70 45.8%. Tooling committed this session (`t2\_check.py`, `t2.bat`, `blend\_eval.py`, `monitor\_strip.py`, `monitor.bat`, `guardrail\_trace.py --weekly`): all now default to `logs\\claude\_equity\_bot\_tracker.xlsx` (the master) rather than `tracker\_with\_registry.xlsx` (the generated report copy) — reading the copy had understated the T2 depth count (100 vs 149). Also fixed an inverted verdict label in `t2\_check.py` that printed "depth gate open" while depth was MET. T2 status: depth 149/88 MET, lead −8.7pt vs the −15 trigger and moving away (−15.4 → −12.7 → −8.7) — consistent with Q1-R's finding.

## 7/23 (Phase 3-B Day 13) — ★ THE FIRST WS2/G1 EPISODE LANDED, and the response was LAG-0 on the RAW channel with D1 contributing nothing. Detector bug found and fixed in the same session. Cross-check 24/24 — `signals\_2026-07-23.log` ↔ `tracker\_with\_registry.xlsx` operative reconcile clean; era `A-S1D1-B1`; no effective damping anywhere; DQ 19 HIGH / 5 MED / 0 LOW; 23 HOLD + 1 BUY (NVDA 62, MEDIUM, rejected <70); totals 1,099 rows. ★ WS2 / G1 — FIRST POST-DEPLOY EPISODE (13 sessions after deploy). WMT trailing 5-session move −5.24% (log H1 tag, Schwab daily closes) / −5.19% (`tracker\_with\_registry.xlsx`, Price-at-Signal) — both past the pre-registered THETA = 5.0%, so it qualifies on either series. `monitor\_strip.py` now reads "1 post-deploy episode … readable", ending twelve consecutive null sessions. THE RESPONSE — lag 0, −9 points, entirely MODEL-SIDE: WMT confidence 47 → 47 → 47 → 45 → 42 → 38 across 7/16–7/23, i.e. it came down with the slide rather than after it. Critically, `damp=0` on every one of those sessions (the trail only crossed THETA on the final session, and then by 0.24pt, which rounds to zero damping) — so the entire decline is `confidence\_raw`, the model's own channel, not D1. That is exactly what G1 measures and exactly what S1 (the prior-signal state input) was built to produce. Contrast the certified Phase 2 baseline behaviour: WMT held 62% through a −11% May slide, catching up only after 3–5 sessions. DISCIPLINE — this is n = 1. The criterion is a table read sustained over ≥ 4 consecutive post-deploy cohorts; this is the first. It is also a smaller slide (−5.2% vs −11%), so it is not a like-for-like comparison with the Phase 2 exhibit, and with a single episode there is no way to separate S1's contribution from ordinary model behaviour. Encouraging, not a verdict. GM remains at 0 post-deploy episodes (trailing +4.72%, confidence rising 54 → 58 → 63 → 62 — the mirror case). ★ DETECTOR BUG FOUND AND FIXED (`monitor\_strip.py`). The tool first reported the episode as "0 served ≤2", which was wrong. The `served` test compared confidence at the episode session against confidence in the following two sessions, looking for a further decline — so a same-session (lag-0) response, the strongest possible outcome, scored as "not served." Corrected: the baseline is now the confidence at the start of the trailing window (i−5, pre-slide), and the tool reports the actual response lag and drop magnitude. It now reads `2026-07-23 lag 0 (47→38, −9pt)`. This is the second bug found in `monitor\_strip.py` since it was written (the first was the pre/post-deploy episode split on 7/22); the WS2 rows should be treated as provisional until a few more episodes exercise the logic. ★ FORMAL RAW-CHANNEL ACCEPTANCE READ RUN (first one with an episode in it). `python h1\_lag\_trace.py --since 2026-07-07 --ticker WMT --raw-from-logs "logs\\signals\_\*.log" --suffix \_raw\_3B --tracker logs\\claude\_equity\_bot\_tracker.xlsx` → `h1\_lag\_trace\_WMT\_raw\_3B.md`. Provenance confirmed: 13 of 13 rows use log RAW confidence (the archived `signals\_2026-07-07\_run1\_coldstart.log` correctly skipped). TABLE READ (the criterion, per §4b): 7/17 trail +1.52% conf 47 · 7/20 −0.90% conf 47 · 7/21 −3.85% conf 45 · 7/22 −4.40% conf 42 · 7/23 −5.19% conf 38 — the response is CONTEMPORANEOUS, and it began at −3.85%, i.e. BEFORE the trail crossed THETA (5.0%). The model's own sensitivity is therefore finer-grained than D1's trigger; S1 is doing the work, D1 never engaged. PRE-REGISTERED SUCCESS METRIC — the number that matters: corr(conf, trailing move) is +0.842 post-deploy RAW vs −0.098 on the full series (old generator). Phase 2 WMT held confidence against the move (the H1 pathology in one figure); the post-deploy raw channel tracks it strongly. DISREGARD the scan's "Estimated update lag = 2 sessions." L=0 +0.842, L=1 +0.937, L=2 +0.958, L=3 +0.800 — L0/L1/L2 are flat within noise, and the "peak" beats L=1 by 0.021 on roughly six pairs. §4b pre-registered exactly this: the scan is confirmatory only at n ≈ 8–10 and a scan pass alone is not success. The table says prompt; the scan cannot discriminate lag 0 from 2 on this sample. Caveat: one clean directional slide, \~8 usable rows, favourable conditions — episodes 2–4 are what convert this into a G1 verdict. TOOLING — stale retired-criterion banner found and patched (`h1\_lag\_trace.py`). Its output still printed `CALIBRATION GUARDRAIL — (50-59% must lead)` and a `\[PASS] 50-59% band leads` verdict — a retired criterion asserted as a live pass/fail, the same class of drift as the weekly runner's T2 banner fixed 7/22, and a T3 hazard. Patched on all three surfaces (console header, verdict line, success-metric bullet, and the `.md` writer) to read "RETIRED (Q1-R closed 2026-07-13) — historical context only; T3: no band-ordering reliance", with a note that the block's rates use the run's `--since` slice and will therefore differ from the live 6/15+ figures in these notes (47.1%/39.6% vs 57.0%/65.8%). RESOLUTION — 7/16 cohort resolved 24/24, accuracy 13/24 = 54.2% — the weakest cohort of the month (15/24 up; a rising tape marking HOLDs wrong, the familiar ±3%-band artifact). RESOLUTION — NVDA 7/16 near-miss (62%, MEDIUM; blend 65, no flip) +5d = +1.39% → RIGHT — the second consecutive NVDA near-miss to pay (after 7/15's +1.13%). KEEP-70% — now a WATCH ITEM. All resolved near-miss BUYs 12/25 = 48.0%, up from 43.5% (7/21) → 45.8% (7/22) → 48.0%. Still under the 50% line that supports the gate, but two consecutive NVDA wins have moved it three sessions running. If it crosses 50%, the live evidence for KEEP-70 weakens and the threshold question deserves re-examination — flag it, do not act on it yet. NVDA 62% (MEDIUM) — ninth near-miss → registry 30 → 31; six pending (7/17, 7/20, 7/21, 7/22 NVDA + GLD, 7/23). BLEND: NVDA 62 → 58 discounted again (sector −0.356, regime −0.029 — nearly flat after yesterday's −0.205, so the cut is sector-driven today). Fifth discount; still none resolved — the discount arm populates 7/24. WS1 confirm arm now 50% (n=4). Q1-R holds: live 60-69 = 65.8% (n=155) vs 50-59 57.0% (n=214). DQ live: HIGH 62.3% (n=361) vs MEDIUM 44.6% (n=166) — stable; no action per Q4-R.

## 7/24 (Phase 3-B Day 14) — ★ RECONSTRUCTED 2026-08-04 FROM `logs\\signals\_2026-07-24.log` AND THE MASTER, CLOSING THE RECORD GAP FLAGGED IN THE 7/30 ENTRY. The notes ran 7/23 (Day 13) directly to 7/27 (Day 15) with no Day 14 entry anywhere in the file, while the master carried a complete 24-row 7/24 cohort — and 7/24 is the very date the WS2 coalescing correction turns on, so the gap sat exactly where G1's evidence is thinnest. THIS ENTRY IS WRITTEN AFTER THE FACT AND IS DATED AS SUCH; it is a reconstruction from primary artifacts, not a contemporaneous session record, and it carries no observations that were not recoverable from the log or the master. RETROSPECTIVE CROSS-CHECK 24/24 CLEAN `\[V]` — `signals\_2026-07-24.log` ↔ `logs\\claude\_equity\_bot\_tracker.xlsx` reconcile on signal, confidence, data quality and price at full precision across all 24 rows, run on 2026-08-04. G4's cross-check streak requirement is therefore satisfied for 7/24 retrospectively, and the entry records that the check was NOT run contemporaneously. COHORT: era `A-S1D1-B1`; 23 HOLD + 1 BUY; DQ 20 HIGH / 4 MEDIUM / 0 LOW; `regime\_score` uniform at +0.185 across all 24 names as designed; confidence mean 52.2, median 51.0, sd(pop) 11.57, range 32–72; totals through this session 1,123 rows, 47 cohorts. RISK ENGINE: 23 APPROVED (all HOLDs through CHECK 2) and 1 REJECTED — NVDA BUY at 63%, `BUY confidence too low: 63% < required 70%`, the tenth consecutive NVDA near-miss. NO DAMPING ANYWHERE — zero rows carry a non-zero `damp`, so operative ≡ raw across the whole cohort. NO BLEND ADJUSTMENT ANYWHERE — `base == blend` on all 24 rows, so WS1 contributed nothing this session. ★★ THE WS2 DATUM THAT MATTERS, AND WHY THIS DATE BECAME CONTENTIOUS: WMT read trail5d −2.75% with confidence 38 and a prior chain of 47,47,45,42,38 (dconf −9). The trailing move had RECOVERED above −THETA from the previous session's −5.62%, so 7/24 is NOT an independent episode — it is the tail of the single 7/23 slide, which is precisely what the 2026-07-27 coalescing correction established when post-deploy WMT episodes went 2 → 1. GM was the mirror image at trail5d +10.34%, confidence 65, chain 54,54,58,63,62 (dconf +8) — a large FAVOURABLE move, which under the pre-registered adverse-only definition (DP-8, ruled 7/29) is not an episode and is not counted. ★ THE COHORT RESOLVED 7/31 AT 14/24 = 58.3% — mean +5d −0.41%, dispersion (sd, population) 6.00%, 10 HOLD band-breaches split 3 UP / 7 DOWN; biggest movers MSFT +20.6%, SND −11.0%, AG −10.2%, AAPL −6.9%, FTI −6.6%. Consistent with the identity recorded 7/30: accuracy is the band-breach count, and a moderate breach count on elevated dispersion produces a middling cohort regardless of signal quality. ★ RECORDED AS A PROCESS FINDING: a session can be fully evidenced in the primary artifacts and still be absent from the record, and the absence is invisible to every tool — `retired\_criteria\_audit.py` scans source files, the cross-check reads the master, and neither knows that a date exists in one and not the other. The gap was found only because the 7/30 entry compared the notes against the master by hand. A cohort-versus-entry reconciliation belongs in the exit checklist. ★ SELF-CORRECTION, SAME SESSION: this entry and the two tool patches made alongside it were first stamped 2026-08-05 and are corrected to 2026-08-04. The cause is the SAME defect already carried on the open list — a UTC clock read at 22:04 CDT returns tomorrow's date — reproduced by hand in dated provenance rather than by code. Recorded because a retrospective cross-check dated to a session that had not yet happened would be unresolvable later, and because the defect class is now demonstrated to reach manual work as well as `datetime.now(timezone.utc)`.

## 7/27 (Phase 3-B Day 15) — ★ CROSS-CHECK 24/24 CLEAN; H4 CROSSED ITS REOPENING BAR BY THE THINNEST POSSIBLE MARGIN; AND THE FIRST LIVE RUN OF THE NEW TOOLING EXPOSED THREE DEFECTS, ONE OF WHICH CHANGES A GATE READ. Cross-check 24/24 — `signals\_2026-07-27.log` ↔ `tracker\_with\_registry.xlsx` reconcile clean (±0.05 conf, signal match); era `A-S1D1-B1`; 24 HOLD / 0 BUY; DQ 17 HIGH / 7 MEDIUM / 0 LOW; totals 1,147 rows, 48 cohorts. ★ H4 REOPENS — but read the margin before acting. HIGH-DQ near-miss is now 6/10 resolved = 60.0000% against a ≥60.0% bar, with n exactly at the ≥10 bar and HIGH ≥ MEDIUM overall (63.0%, n=397 vs 46.1%, n=178). All three pre-registered conditions PASS, so by its own rule H4 leaves the backlog. But the hit rate FELL to get there (66.7% → 60.0%); the state flipped only because n crossed 10, and the verdict sits exactly ON the bar — one resolution either way flips it. This is a mechanical threshold crossing on the weakest admissible evidence, not a finding. Recommend recording H4 as REOPENED-BY-RULE and requiring a second consecutive pass at n ≥ 12 before any DQ-conditional design work. ★ KEEP-70 back under the line: 48.1% (13/27), down from 50.0% (13/26) — the watch item flagged 7/23 has retreated; the gate remains supported. ★ WS1 / G2: first gate-flip resolved — 7/13 NVDA base 65 → blend 70, +5d −2.05%, blend WRONG; net −1 on one flip; confirm arm 50% (n=4), discount arm 50% (n=2); 6 blended cohorts +5d-resolved against DP-1's proposed N=5. ★ WMT recovered — trail −5.62% (7/24) → −1.49% (7/27), confidence 38 → 42. ★ THE Q1 GUARDRAIL INFRASTRUCTURE IS RETIRED, the review cadence moves WEEKLY → DAILY, and the chart "squish" turned out to be a structural defect in the x-axis, not a rendering one. ★ GUARDRAIL RETIREMENT — one tool, three artifacts. `guardrail\_trace.py` is out of the runner. Retiring it necessarily retires everything it wrote, and all three answered the question Q1-R closed on 7/13: the `Guardrail Trace` sheet (cumulative +5d hit rate by band; header literally reads "The 50-59% band must lead 60-69%"), the `Live Cohort Scoreboard` sheet (columns `Held (50-59>60-69)` and `Cum lead (pt)` — a per-cohort verdict on a suspended decision input), and `regime\_stratification.md` (which existed to feed T2's second condition; T2 itself was retired with Q1-R). The `.py` stays in the repo for the record — this is a cadence removal, not a deletion. The closing banner of the runner had to be rewritten in the same edit: it instructed the operator to check two artifacts that would no longer be produced. Population monitoring survives as the weekly band chart on the monitor strip, explicitly labelled context only. ★ THE RETIREMENT IS NOW SELF-ENFORCING — and this matters more than the removal. `build\_near\_miss\_registry.py --emit-master-copy` rebuilds `tracker\_with\_registry.xlsx` from the master on every run, so a retired tab still sitting in `logs\\claude\_equity\_bot\_tracker.xlsx` would be resurrected into the copy indefinitely — stale, with no tool refreshing it, and looking exactly as authoritative as a live one. `monitor\_strip.py` therefore drops both retired sheets from the COPY on every run (never the master; guarded) and prints what it dropped. That print is a diagnostic: if it appears on every run, the master still carries the tabs and they should be deleted there once. It did print against the uploaded workbook. ★ CADENCE: WEEKLY → DAILY (`run\_weekly\_review.bat` → `run\_daily\_review.bat`). The trigger was a concrete inconsistency: the `Guardrail Trace` sheet read as of 2026-07-17 while the `Signals` tab of the same workbook ran to 7/24 — five sessions stale inside a file being used for daily review. A weekly embed of a daily-glance artifact is not merely late, it is misleadingly current-looking, which is the failure mode this project has already been bitten by twice. Ordering constraint recorded in the bat header: registry regen → strip embed, always (the regen resets the copy, so any earlier embed is destroyed). ANALYST NOTE carried into the runner: running daily is not reading daily — G1/G2 are TABLE reads at their stated n, and a one-session move in any of them is noise. ★ THE SQUISH — I had the wrong diagnosis and the correction is the durable finding. My first read was a rendering bug, and that part is real: `guardrail\_trace.py` embeds via `scale = min(1.0, 760.0/img.width)`, so a 1632×884 chart was displayed at 760×411 = 46.6% scale, handing Excel an oversized bitmap and asking Excel to resample it. But that is downstream. The actual defect is the growth rate of the x-axis. One x-tick per cohort on an unbounded time series grows at \~+5 ticks/week; no resolution, figure width or embed scale survives that indefinitely — the 760px cap was fixed while the tick count was not. Weekly aggregation changes the growth rate to +1/week. On current data: 47 cohorts → 9 resolved weeks, and the density improves in the same move — per-cohort band n runs 2–15 (median 8) with hit rates swinging 14%–88%, while per-week band n runs 17–57 (median 38) with hit rates reading 38%–77%. Same series; the per-cohort view was mostly noise. Both fixes shipped, but they are not equals: the resample is a one-time correctness fix, the aggregation is the one that still works at the 3-B exit review. RENDERING RULE recorded in the module header: render big, resample once to the exact embed width (PIL/LANCZOS), then anchor at native size so Excel scales by 0% — never hand openpyxl an oversized PNG and shrink it via `img.width`/`img.height`. ★ `monitor\_strip.py` gained `--embed-into`, mirroring the old `guardrail\_trace.py` contract: reads the master, writes the generated copy, hard-errors if the two are the same path. The sheet carries an as-of/provenance line, the four open questions, the WS1 gate-flip table, and a WS2/G1 episode ledger (per-episode lag, conf-pre, conf-at-response, drop, served). It is a rendering of the metrics dict, not a transcription — `question\_rows()`, `context\_line()` and `provenance()` are shared with `monitor\_strip.md`, so the two cannot drift. Idempotent (sheet replaced, never stacked) and re-parked in canonical tab order each run. Theme is dark by default and styles the whole sheet, not just the image, so the strip reads as a designed tile rather than a black rectangle on a white grid. ★ NEW TOOL — `retired\_criteria\_audit.py`. Retiring a question has now taken four separate discoveries, weeks apart, each found by accident: `h1\_lag\_trace.py` printing the guardrail criterion as a live pass/fail (patched \~7/23), the T2 tripwire firing on a suspended input, the two guardrail sheets, and the runner banner. This tool finds the rest on purpose. It is deliberately two-factor — a retired TOPIC token and live-criterion grammar (`PASS`/`FAIL`/`verdict`/`must lead`/`tripwire`/`reopen`) on the same line — because mentioning a retired question is correct and necessary in provenance and history; the defect is stating it in the grammar of a live decision input. A retirement marker within ±3 lines clears a finding, `# audit: retired-ok` is an explicit opt-out, and it exits 1 on HIGH/MEDIUM so it can become a pre-commit hook. It immediately caught a true positive in my own new code — `context\_line()` reported the live 50-59 vs 60-69 split with no retirement marker while the chart beside it was correctly labelled context only. Now marked "monitoring only — the Q1 guardrail is retired; the band split below is population context, not a decision input." ★ PROVENANCE GUARD ADDED, after the check I wrote failed silently. `monitor\_strip.py` falls back to a local `THETA = 5.0` when `risk\_engine` will not import. Embedding a WS2 episode ledger built on a fallback THETA is a provenance break — it may not match what D1 actually damps on — so the tool now warns loudly before writing. My first implementation of that warning never fired: I tested `"risk\_engine" not in THETA\_SRC`, but the fallback string is `"local default (risk\_engine unavailable)"`, which contains that substring. Replaced with an explicit `THETA\_OK` boolean set at import time; the trap is documented in place. Verification: two consecutive embeds → 1 image, not 2 (idempotent); image 1100×482 native, ext 1100×482, 100% scale, `OneCellAnchor`; every drawn bar reconciles to the weekly data within 0.14pt (measured off the rendered pixels); tab order `Dashboard > Signals > Near-Miss BUYs > Cohort Analysis > Monitor Strip > How to Use`; formulas 8,689 → 8,689, LibreOffice recalc 0 errors; workbook 495 KB → 324 KB (the two retired sheets took the old guardrail PNG with them); audit CLEAN / exit 0 on the patched files and exit 1 on the pre-change bat as a positive control. ★ AUDIT RUN — and it found the fourth instance, in the file I did not suspect. `h1\_lag\_trace.py` was already clean: the 7/23 patch is in place and correctly prints the block as "RETIRED (Q1-R closed 2026-07-13) — historical context only; T3: no band-ordering reliance." `h4\_dq\_threshold.py` carried the identical block, unpatched — `print("CALIBRATION GUARDRAIL — cohort-window +5d bands (50-59% must lead)")` followed by `ok = lead == "50-59"` and a live `\[PASS/WARN]` verdict, i.e. a retired criterion presented as a passing test on every run. Fixed by porting h1's already-approved wording verbatim rather than drafting new language, so the two harnesses now read identically; the patch is dated in place. Both files' `--since/--until` notices reworded from "calibration guardrail uses this same window" to "the retired band-calibration block uses this same window." The audit also produced one FALSE POSITIVE worth recording, because it is a real ambiguity in the project's vocabulary and not a tooling bug: it flagged h4's near-miss lever (`BUY \& 60-69% by DQ`). The 60-69 band belongs to two different questions — the RETIRED Q1 guardrail (the 50-59 vs 60-69 comparison) and the LIVE KEEP-70 near-miss band (BUYs the 70% gate rejects), which both H4 and KEEP-70 still turn on. Bare `60-69` was therefore removed as a token; `50-59` and `guardrail` only ever mean the retired comparison. The audit also flagged itself (its own pattern tables are by construction full of these tokens) and now skips its own file, `--include-self` to override. Post-patch: HIGH 0 · MEDIUM 0 · LOW 23, exit 0 across `h1\_lag\_trace.py`, `h4\_dq\_threshold.py`, `monitor\_strip.py`, `run\_daily\_review.bat` and the audit itself; every LOW is an internal variable name or a provenance comment. Cross-validation: patched h4 reports HIGH-DQ near-miss 9 resolved / 66.7%, matching the monitor strip's H4 card exactly (`67%`, `6/9`, n short, rate ok) — two independently-written tools agreeing on the same reading. ★★ FIRST LIVE RUN — THREE DEFECTS, AND THE SELF-ENFORCING RETIREMENT CLAIM FAILED ON ITS FIRST OUTING. The 7/27 `run\_daily\_review.bat` execution confirmed the two things I asked to be checked — THETA read `risk\_engine.DampingConfig.THETA` (provenance-clean, warning correctly silent) and WS1 read a non-zero flip count — and then broke in three places. (1) THE RETIREMENT PURGE MISSED A RENAMED TAB. The report copy came back carrying a sheet named `Sheet1` which is the retired guardrail trace: header "Guardrail Compression Trace — cumulative +5d hit rate by confidence band", subtitle "Auto-generated by guardrail\_trace.py … as of 2026-07-20. The 50-59% band must lead 60-69%", 42 cohort rows and the chart image. It survived because `RETIRED\_SHEETS` matched on sheet NAME, and this one had been renamed in the master. A retired artifact must be identified by what it SAYS, not by what it is called — the purge is now content-based (`RETIRED\_SIGNATURES` matched against the first three cells of column A) and catches it. Note the compounding failure: the retired criterion re-entered the workbook and went undetected by `retired\_criteria\_audit.py`, because the audit scans source files, not workbook contents. (2) THE WS2 EPISODE DETECTOR DOUBLE-COUNTS A SINGLE SLIDE — third bug in this detector, and it CHANGES THE G1 READ. WMT 7/23 (trail −5.19%) and 7/24 (−5.62%) were reported as two post-deploy episodes with identical conf-pre and response (47→38, −9pt) — the tell. A slide holds the trailing window below −THETA for as long as it lasts, so the detector emitted one "episode" per SESSION of one decline. Corrected by coalescing: an episode is now the first session of a qualifying run, which continues until the trail recovers above −THETA. Post-deploy WMT episodes: 2 → 1. Pre-deploy: 4 → 1. G1 therefore has ONE independent test case, not two, and the 7/23 entry's "this is n = 1" discipline still stands unchanged a week later. (3) `h4\_dq\_threshold.py` PRINTED A VERDICT ON ZERO EVIDENCE. Run against the freshly generated report copy it reported `0/0` on every DQ tier and concluded "STAYS DEMOTED" — while the monitor strip, on the same workbook, read REOPEN. Cause: `Return+5d` and `Was-Right-5d` are formulas, openpyxl reads cached values, and any openpyxl save blanks that cache — which the daily runner now does every session when it embeds the strip. 2,390 formula cells, 100% blank. `monitor\_strip.py` is immune by design (it computes returns from the Price columns); h4 reads the formula columns by design. h4 now refuses and exits non-zero rather than print a verdict, naming the cache as the cause and the master as the fix. This is the same failure class the audit was built for — a tool asserting a conclusion it has no evidence for — arriving through a channel the audit cannot see. Post-patch audit across all five files: CLEAN, exit 0.

## 7/28 (Phase 3-B Day 16) — ★ H4's REOPEN LASTED EXACTLY ONE SESSION; G2 IS NOW NEGATIVE ON BOTH READS AND NOT ROBUST; AND THE RETIRED-CRITERIA AUDIT RAN ACROSS THE FULL REPO FOR THE FIRST TIME. Cross-check 24/24 — `signals\_2026-07-28.log` ↔ `tracker\_with\_registry.xlsx` reconcile clean (±0.05 conf, signal match); era `A-S1D1-B1`; 24 HOLD / 0 BUY; DQ 17 HIGH / 7 MEDIUM / 0 LOW; totals 1,171 rows, 49 cohorts. Resolutions complete through 7/21. ★★ H4 — REOPENED 7/27, DEMOTED AGAIN 7/28. Record it as STAYING DEMOTED; the 7/27 pass was an artifact of n crossing its bar, not a finding. Yesterday HIGH-DQ near-miss read 6/10 = 60.0000% against a ≥60.0% bar with n exactly at 10 — all three conditions passing on the weakest evidence the rule admits, and flagged at the time as "one resolution either way flips it." The 11th resolved today and missed: 6/11 = 54.5%, `\[FAIL] hit rate ≥ 60.0%`. n and the HIGH ≥ MEDIUM condition still pass (HIGH 61.1% n=535 vs MEDIUM 49.1% n=493), so the binding constraint has moved from sample size to rate. THE n ≥ 12 CONFIRMATION RULE PROPOSED YESTERDAY IS VINDICATED WITHIN 24 HOURS — had the REOPEN been recorded as a disposition it would have needed reversing in a single session. Adopt it: no DQ-conditional design work until HIGH-DQ near-miss passes on two consecutive readings at n ≥ 12. TOOL DEFECT (`h4\_dq\_threshold.py`): the run closes with "The binding gap is sample size on HIGH-DQ near-misses; only a larger 3-A near-miss sample can reopen it." That is now false — n passes at 11 and the rate is what fails. The string is hardcoded and assumes the n-condition is the failing one. Small, but it is a tool explaining a failure incorrectly, which is the same class cleared four times this week. ★★ WS1 / G2 — NEGATIVE ON BOTH READS, AND THE CROSS-VALIDATION IS NOT ROBUST. `blend\_eval.py --since 2026-07-13`: 12 cohorts, 288 signals, 168 +5d-resolved, 10 blend-adjusted (lift 5, cut 5 — now symmetric, previously discount-heavy\*\*)\*. (A) Overlay predictive value \[primary]: overlays CONFIRMED 40.0% (n=5) vs overlays DISCOUNTED 50.0% (n=2) → gap −10.0pt, i.e. the wrong direction — the signals the overlays liked did worse than the ones they disliked. (B) Gate-flip @ 70%: 1 disagreement of 7 resolved BUYs — 7/13 NVDA base 65 / blend 70, blend APPROVES, +5d −2.1%, blend worse → net −1. (C) Leave-one-cohort-out folds: `\[+0, +0, −25, −25, +40, −60, +0, −10, −10, −10, −10, −10]`, min −60pt and signs MIXED — the criterion requires all folds the same sign, so robustness fails independently of the point estimate. DISCIPLINE: this is NEGATIVE AND UNDERPOWERED, not a verdict. n=5 vs n=2 on the primary read cannot carry a conclusion in either direction, and the footprint remains near-single-name. But it is worth stating plainly that G2's evidence has never once pointed the right way, and G2's allowed dispositions are VERDICT or DESCOPE — it cannot be parked. ★★ DP-6 AND DP-7 RULED (both dated 2026-07-28). DP-6 — G1 counting basis = EPISODES, not cohorts, on the reasoning that a cohort with no material move carries no information about response-to-material-move, so a cohort reading would close G1 on evidence that is substantively one data point. This ruling makes G1 STRICTER: it moves from "15 post-deploy cohorts logged, count met" to 1 independent episode of the 4 required. DP-7 — G2 gains a BREADTH condition: ≥ 2 distinct tickers with resolved adjusted signals. Currently NVDA-only; GLD's 7/22 BUY (conf 62) resolves 7/29, which is when the condition is met. NOTED AND NOT YET RULED: a 6:1 NVDA:GLD split clears the letter of "≥ 2 tickers" while leaving the footprint essentially single-name — a per-ticker minimum or concentration cap remains open. DP-8 (bidirectional episodes) and DP-9 (universe beyond WMT/GM) were RAISED AND DELIBERATELY LEFT UNRULED; both would increase the episode count on a gate that is blocking the exit, and DP-9 contradicts explicit pre-registered wording ("WMT primary / GM secondary"), so neither may be adopted silently. ★★ FIRST FULL-REPO AUDIT RUN — 23 HIGH / 34 MEDIUM, of which roughly FIVE are genuine. The headline count is misleading and the triage matters more than the total. GENUINE (fix): `t2\_check.py` and `t2.bat` still print " T2 FIRES — both gates met. Run the Tier-2E diff. \*" and describe the firing conditions in the present tense. T2 is retired; this is a live instruction on a dead tripwire, and it is exactly the defect pattern found in `h1\_lag\_trace.py` (7/23) and `h4\_dq\_threshold.py` (7/27). EXPECTED (housekeeping): `run\_weekly\_review.bat` (delete — superseded 7/27) and `guardrail\_trace.py` ×3 (retained-but-unmaintained; needs a RETIRED header block so its own file declares its status). FALSE POSITIVES — three classes, each a real ambiguity in the project's vocabulary rather than a tooling bug: (i) `Retired\\h2\_direction\_asymmetry.py` and `Retired\\h3\_thesis\_stability.py` ×4 — already retired by location; the audit should skip a `Retired\\` directory. (ii) `docs\\analyst\_notes.md` ×4 — historical entries SHOULD describe the guardrail as live, because it was live then. The record must never be rewritten to match present belief; the audit must exclude the notes. (iii) `WS1\_Deploy\_Notes.md`, `WS2\_Deploy\_Notes.md`, `WS2\_H1\_Feature\_Spec.md`, `Phase3B\_Session\_Manifest.md` ×5 — `T2` there is a TEST-CASE ID (`|T2|Blend math table`, `|T2|Damping table`), not the tripwire. This is precisely parallel to the bare-`60-69` ambiguity fixed on 7/27, where one token served both a retired and a live question. The audit is not hook-ready until those three exclusions land. ★ 7/21 COHORT RESOLVED 10/24 = 41.7% — the weakest since 7/16, and it is a DISPERSION artifact, not a directional one. 13 of the 14 wrong calls were HOLDs marked wrong by breaching the ±3% band, and those breaches split 7 UP / 6 DOWN on a cohort whose mean +5d was +0.03% with 11 of 24 names up. A flat tape with high dispersion marks HOLDs wrong in both directions simultaneously. This is not the rising-tape variant seen on 7/16; it is the same underlying ±3%-band volatility sensitivity presenting symmetrically, and it is the strongest single-cohort argument yet for the parked Q4-2 vol-scaled secondary metric. ★ DATA INTEGRITY — TWO GHOST ROWS FOUND (new, G4-relevant). `h4\_dq\_threshold.py` reported `other: 2 (0.2%)` in its DQ distribution. Traced to Signals rows 222 and 226, both dated 2026-06-01 — AG and FTI — carrying a date and ticker but NULL signal, NULL confidence and NULL data\_quality. They are not 429-skips (those produce no row at all per the workflow §14) and not parse-error signals (those carry conf 0 plus an error flag). Most likely a partial paste from the 6/01 session. Impact is small but real: they inflate every denominator computed as "signal rows" by 2, and they are an OPEN DATA-INTEGRITY ITEM, which G4 requires to be empty at exit. Decide whether to delete the rows or annotate them, and record which. ★ KEEP-70 STRENGTHENED: 13/28 = 46.4%, down from 48.1% (7/27) and 50.0% (7/24) — the watch item raised 7/23 has now retreated two sessions running and sits comfortably under the 50% line that supports the gate. ★ WS2 / G1 UNCHANGED — still 1 independent post-deploy episode of 4 (WMT 7/23, lag 0, 47→38). No new episode on 7/28; GM still has none. ★ CONTEXT (monitoring only, no criterion attached): within the 60-69 band, HIGH-DQ reads 64.0% (n=214) vs MEDIUM 40.5% (n=42) — a 23.5pt spread; Q4-R closed this as a volatility artifact and no DQ lever follows. LOW-DQ overall 9/21 = 42.9%, avg +5d −4.85% — consistently poor but n=21. ★ DEPLOYMENTS AND DOCUMENTS. `h1\_lag\_trace.py`, `h4\_dq\_threshold.py` and `retired\_criteria\_audit.py` replaced in root today (7/28); `monitor\_strip.py` and `run\_daily\_review.bat` were deployed 7/27 and confirmed live by the Monitor Strip tab reading the coalesced episode count. `Daily\_Workflow\_v5\_3\_Phase3B.docx` drafted — cadence change, the formula-cache section rewritten, retired-artifact list, two new operator lessons ("a renamed tab is still the tab it was"; "a clean console is not a completed run") and a new §17 on retired-criteria discipline. `Phase3B\_Closeout\_Decision\_Worksheet\_v1.docx` drafted (G6 "drafted" satisfied). ★ OPERATIONAL CONFIRMATION: the uploaded `tracker\_with\_registry.xlsx` carried a LIVE formula cache (only pending-resolution rows blank), confirming the "open in Excel after the daily run" step is being followed — the step that became load-bearing when the strip embed started blanking the cache every session.

## 7/29 (Phase 3-B Day 17, FOMC decision day) — ★ G2's PRIMARY READ FLIPPED SIGN ON TWO OBSERVATIONS AND STILL FAILS; THE 7/22 COHORT RESOLVED AT 29.2% AND IT IS A MEASUREMENT ARTIFACT, NOT A GENERATOR FAILURE; H4 CONFIRMED DEMOTED AT THE n ≥ 12 THRESHOLD. Cross-check 24/24 — `signals\_2026-07-29.log` ↔ `tracker\_with\_registry.xlsx` reconcile clean (±0.05 conf, signal match); era `A-S1D1-B1`; 24 HOLD / 0 BUY; DQ 18 HIGH / 6 MEDIUM / 0 LOW; `regime\_score` uniform at −0.057 across all 24 names as designed; totals 1,195 rows, 50 cohorts. PROTOCOL HELD ON A FED DAY, DELIBERATELY. The AM canonical run went ahead unchanged roughly 3.5 hours ahead of the 2:00 PM ET announcement, so today's signals are generated on pre-announcement information with no leakage — only a resolution window that spans the event. Skipping high-volatility days would have been a selection decision made on an expected outcome, conditioning the entire accuracy series on calm markets and silently biasing every cohort statistic in the project. That contamination would be far worse than including the day, and it is the same principle that governs DP-6 and the unruled DP-8/DP-9: a criterion does not move because the operator can see what is coming. Today's cohort is tagged Fed-decision-adjacent; its +5d resolves \~8/5. ★★ WS1 / G2 — THE PRIMARY READ FLIPPED FROM −10.0pt TO +15.0pt IN ONE SESSION. IT STILL FAILS, AND THE FLIP IS THE MORE IMPORTANT FINDING. `blend\_eval.py --since 2026-07-13`: 13 cohorts, 312 signals, 192 +5d-resolved, 10 blend-adjusted (lift 5, cut 5). (A) Overlay predictive value \[primary]: CONFIRMED 40.0% (n=5), mean favorable −0.89%; DISCOUNTED 25.0% (n=4), mean favorable −3.75% → gap +15.0pt, "blend adds value" — the first time in the WS1 record the primary read has pointed the right way. The mechanism is legible: the discount arm went from n=2 to n=4 and both new resolutions did badly, so the overlays correctly flagged the weaker signals. THE ARITHMETIC ALSO SETTLES WHAT THE LOG WOULD HAVE TOLD US: GLD 7/22 WAS A DISCOUNT CASE, not a lift. BUT — AND THIS WAS PRE-COMMITTED BEFORE THE NUMBER WAS SEEN — THE SIGN FLIPPED ON TWO OBSERVATIONS, AND A CONCLUSION THAT TWO DATA POINTS CAN REVERSE IS NOT A CONCLUSION IN EITHER DIRECTION. Yesterday's −10.0pt was not evidence of harm and today's +15.0pt is not evidence of value; both are n=5-vs-n=4 reads on a near-single-name footprint. H4 demonstrated exactly this fragility twice in three days (60.0000% → 54.5% → 50.0%), which is why the caveat was written down in advance rather than after. (C) Leave-one-cohort-out folds: `\[+25, +25, +0, +0, +40, +7, +25, −10, +15, +15, +15, +15, +15]` — twelve of thirteen positive, a large improvement on yesterday's `\[−60 … +40]`, but one fold is −10pt and the criterion requires ALL folds the same sign. (A) is therefore NOT ROBUST as stated. (B) Gate-flip @ 70%: net −1, UNCHANGED — still the single 7/13 NVDA disagreement (base 65 / blend 70, blend APPROVES, +5d −2.1%, blend worse) out of 9 resolved BUYs. G2 REQUIRES BOTH (A) ROBUST AND (B) NET ≥ 0. IT FAILS BOTH. NO DISPOSITION IS TAKEN. ★ DP-7 BREADTH CONDITION IS MET (2026-07-29). GLD 7/22 (BUY, conf 62) resolved 381.12 → 371.08 = −2.63% — the first non-NVDA adjusted signal to resolve in the entire WS1 record, giving two distinct tickers with resolved adjusted signals. THE CONCENTRATION CAVEAT RAISED WHEN DP-7 WAS RULED HAS WORSENED, NOT IMPROVED: of 9 resolved adjusted signals, 8 are NVDA and 1 is GLD. The condition is satisfied in letter and almost entirely unsatisfied in spirit. A per-ticker minimum or concentration cap remains unruled and should be ruled before G2 is scored. GLD's failure to pay is also a further point for KEEP-70. ★★ 7/22 COHORT RESOLVED 7/24 = 29.2% — THE WEAKEST OF THE LIVE PERIOD, AND IT IS THE ±3% BAND MEASURING VOLATILITY RATHER THAN SKILL. The three-cohort sequence reads 70.8% (7/20) → 41.7% (7/21) → 29.2% (7/22) and would, taken at face value, look like generator degradation. It is not. 7/22: mean +5d −2.78%, dispersion (sd) 7.54%, 9 of 24 names up, and 15 of the 17 wrong calls were HOLDs marked wrong purely by breaching the ±3% band (7 UP / 8 DOWN). FIFTEEN HOLD NAMES MOVED MORE THAN 3% IN FIVE SESSIONS — the band marked them wrong by construction, so the cohort's accuracy was set by market dispersion before any signal quality entered the calculation. Biggest movers: CBRS −22.6%, SND −14.2%, AG −13.3%, PWR −12.5%, RTX +10.3%; the +5d window (7/23–7/29) spans the FOMC decision. This is the second consecutive high-dispersion cohort — 7/21 read sd 6.02% with 13 band-breaches split 7 UP / 6 DOWN on a mean of +0.03%, i.e. a flat tape marking HOLDs wrong in both directions simultaneously, and 7/22 is the same mechanism amplified. RECORD THIS EXPLICITLY IN THE CLOSEOUT NARRATIVE: the recent accuracy decline is substantially a MEASUREMENT ARTIFACT, not a degradation of the signal generator. Read without that annotation, a future reader sees three cohorts falling from 70.8% to 29.2% and reaches the wrong conclusion about 3-B. This is now the strongest evidence in the project for the parked Q4-2 volatility-scaled secondary metric — which remains a PARALLEL SECONDARY report and never a re-baseline; the ±3% band is NOT changed. ★ H4 — CONFIRMED DEMOTED AT THE CONFIRMATION THRESHOLD. `h4\_dq\_threshold.py` against the master: n = 12 (the threshold proposed 7/27 and vindicated 7/28) and the rate reads 6/12 = 50.0% against a ≥60.0% bar — `\[FAIL]`. Overall HIGH 333/551 = 60.4% ≥ MEDIUM 243/501 = 48.5% still passes, LOW 9/21 = 42.9% (avg +5d −4.85%). Near-miss by DQ: HIGH 6/12 = 50.0%, MEDIUM 7/18 = 38.9%. Three consecutive declining reads (60.0000% → 54.5% → 50.0%). The n ≥ 12 rule, applied as intended, CONFIRMS DEMOTED — the 7/27 pass is now unambiguously an artifact of n crossing its bar. The `.md` exhibit's verdict line states all three conditions correctly; the stale "binding gap is sample size" string is console-only and still wants patching. ★ KEEP-70 — FIFTH CONSECUTIVE IMPROVEMENT: 13/30 = 43.3% (from 46.4% on 7/28, 48.1% on 7/27, 50.0% on 7/24, 48.0% on 7/23). The watch item raised 7/23 is now well clear of the 50% line and the gate is comfortably supported. ★ WS2 / G1 — UNCHANGED, 1 INDEPENDENT POST-DEPLOY EPISODE OF 4 (WMT 7/23, lag 0, 47→38). No new episode; GM still has none. NOTE: today's AM run is pre-announcement, so any FOMC-driven move on WMT or GM enters the trailing window TOMORROW, not today. ★ OPERATIONAL — THE FORMULA-CACHE STEP CAUGHT ITSELF. The first `tracker\_with\_registry.xlsx` uploaded today carried a 100% blank formula cache (2,590 cells) — the daily run had not been followed by opening the file in Excel. Detected immediately because the Return/Right columns read empty across every cohort including ones resolved days earlier; the re-upload after opening in Excel reads 17% blank (pending rows only). All figures in this entry are computed from the Price columns and are unaffected either way, but the episode confirms the §6 rule: h4\_dq\_threshold.py would have REFUSED against the first copy, which is the guard working as designed. ★ INSTRUMENTS — `Phase3B\_Closeout\_Decision\_Worksheet\_v1.1` ISSUED. G5 (Trigger service) CLOSED — VERDICT: SERVED, on complete evidence and a disposition already in the record. DP-6 and DP-7 recorded as ruled 7/28 with the reasoning as given. H4's disposition recorded (STAYS DEMOTED, confirmed at n=12, with the two-consecutive-readings rule attached). DP-8 and DP-9 formally entered as OPEN AND UNRULED. No other gate was closed — G1 (1 episode of 4), G2 (fails both reads), G3 (repo state unverified), G4 (four open integrity items) and G6 (memo unwritten, notes backlog) all remain open with the specific blocking gap named against each.

## 7/30 (Phase 3-B Day 18) — ★ THE ±3% BAND FINDING IS NOW AN IDENTITY RATHER THAN AN INTERPRETATION; G1 IS UNCHANGED WHILE ITS OWN MONITOR PRINTS AN EPISODE DATE THE RECORD RETIRED; AND D1 ENGAGED FOR THE FIRST TIME POST-DEPLOY WITH A DAMP FIELD THAT DOES NOT RECONCILE. Cross-check 24/24 — signals\_2026-07-30.log ↔ logs\\claude\_equity\_bot\_tracker.xlsx reconcile clean (±0.05 conf, signal match), run by log\_tracker\_crosscheck.py rather than by hand; era A-S1D1-B1; 24 HOLD / 0 BUY; DQ 18 HIGH / 5 MEDIUM / 1 LOW — SND drops to LOW, THE FIRST LOW-DQ ROW SINCE 2026-06-24, twenty-four clean sessions ago; regime\_score uniform at −0.061 across all 24 names as designed; totals 1,219 rows, 51 cohorts. Resolutions entered at all three horizons: 7/23 (+5d), 7/16 (+10d), 7/01 (+20d). ★★ THE DISPERSION ARTIFACT IS NOW ARITHMETIC, NOT A READING. The 7/29 entry recorded the recent accuracy decline as substantially a measurement artifact. That claim is today upgraded from an interpretation to an identity, computed across the whole record. Over all 46 resolved +5d cohorts, corr(HOLD band-breach count, cohort accuracy) = −0.9654, and the relation accuracy == (n − breaches − directional misses)/n holds EXACTLY in 46 of 46 cohorts, with directional misses averaging 0.43 per cohort. Because the watchlist runs \~96% HOLD, MEASURED COHORT ACCURACY IS THE BAND-BREACH COUNT PLUS A ROUNDING TERM. The non-trivial part is what the breach count depends on: market dispersion, not the generator. The horizon data makes the point sharper still — HOLD rows breaching the fixed ±3% band run 479/1,065 = 45.0% at +5d (median |move| 2.62%), 533/951 = 56.0% at +10d (3.56%), and 480/716 = 67.0% at +20d (5.38%). THE MEDIAN HOLD CROSSES THE BAND SOMEWHERE BETWEEN +5d AND +10d, so at +10d and beyond being scored wrong is the MODAL outcome for a HOLD irrespective of signal quality. Today's three resolutions demonstrate the gradient directly on cohorts one week apart in signal date: 7/23 at +5d = 58.3% with 9 breaches; 7/16 at +10d = 50.0% with 11 breaches; 7/01 at +20d = 25.0% with 18 of 23 HOLDs breaching. THE CLOSEOUT NARRATIVE MUST CARRY THIS ANNOTATION AGAINST THE +20d SERIES SPECIFICALLY, or a future reader will read 25.0% as collapse when it is the fixed band meeting a twenty-day horizon on a rising tape (7/01 mean +20d +2.34%, 12 of the 18 breaches upward). The ±3% band is NOT re-baselined and no prior conclusion moves; this strengthens the case for the parked Q4-2 volatility-scaled metric as a PARALLEL SECONDARY report only. ★ 7/23 COHORT RESOLVED 14/24 = 58.3% — a recovery from 29.2%, and the recovery has the same cause as the decline. Mean +5d +0.19%, dispersion (sd, population) 6.25%, 13 of 24 names up, 9 HOLD band-breaches split 4 UP / 5 DOWN, plus one directional miss (NVDA BUY, conf 62, −5.7%). Biggest movers MSFT +19.5%, SND −13.8%, GM +11.0%, FTI −10.3%, NVDA −5.7%. This is the THIRD consecutive elevated-dispersion cohort (sd 6.02% → 7.54% → 6.25%) yet accuracy rose 29 points, because breaches fell 15 → 9. Dispersion stayed high; the count of names crossing the band did not. That decoupling is the cleanest single illustration of the identity above. 7/16 at +10d reads 50.0% (11 breaches, 7 UP / 4 DOWN, mean +1.43%, sd 6.27%) and 7/01 at +20d reads 25.0% (18 breaches, 12 UP / 6 DOWN, mean +2.34%, sd 8.56%). ★★ TOOL DEFECT (monitor\_strip.py) — THE WMT CLOCK PRINTS AN EPISODE DATE THE 7/27 COALESCING CORRECTION RETIRED. The WS2 / G1 WMT row reads, verbatim: "1 post-deploy episode(s) in 18 session(s) (1 responded ≤2 sessions); 1 pre-deploy; last episode 2026-07-24, 4 session(s) ago. Episodes: 2026-07-23 lag 0 (47.0→38.0, −9.0pt)". The COUNT is coalesced and the LEDGER is coalesced — both correctly show the single 7/23 episode — but the "last episode" DATE is computed from the raw qualifying-session series and still reports 7/24, which is precisely the row the 7/27 correction folded into 7/23 when post-deploy went 2 → 1. A reader taking the strip at face value sees an episode on a date the record explicitly struck, on the gate that is blocking the entire exit. This is the fifth instance of the same class — a corrected value surviving in a second code path — after h1\_lag\_trace.py (7/23), h4\_dq\_threshold.py (7/27), t2\_check.py / t2.bat (7/28) and the renamed retired sheet. Fix the date field to derive from the coalesced ledger, not the qualifying-session series. ★★ D1 ENGAGED FOR THE FIRST TIME SINCE DEPLOY, AND ITS DAMP FIELD DOES NOT RECONCILE ON TWO ROWS. Every post-deploy session through 7/29 recorded D1 contributing zero damping, so the operative channel was identically the raw channel and E2 was trivially satisfied. That ends today: FTI (trail5d −10.50%, raw 55 → op 47, damp 8), AG (−9.23%, raw 32 → op 32, damp 6), SND (−8.79%, raw 38 → op 35, damp 6) and NVDA (−5.98%, raw 50 → op 49, damp 1). FTI and NVDA reconcile exactly. AG AND SND DO NOT: AG reports damp 6 against a raw−op delta of 0, and SND reports damp 6 against a delta of 3. The D tag is therefore reporting damping that was not applied to the operative confidence — a clamp or floor either firing silently or being reported before application. Same class as the two tool defects cleared this week: a tool printing a number it did not act on. Check risk\_engine.DampingConfig before the next session. CRITICALLY, E2 IS NOT ADVANCED BY ANY OF THIS — all four damped names are outside the WS2 tracer universe, and WMT and GM both read damp 0, so operative ≡ raw on both tracers and E2 remains trivially satisfied and substantively untested. ★ CHANNEL NOMENCLATURE — confidence\_blend CARRIES THE POST-DAMPING VALUE. Computed rather than recalled, from the three rows where the two candidates differ: the JSON field confidence\_blend tracks the B tag's blend\_op in 3 of 3, and the B tag's blend in 0 of 3. So the field named for the blend channel carries the value AFTER damping, while the B tag's blend= carries the value before it. Two similarly-named fields, two different channels — exactly the collision the three-channel naming discipline exists to prevent. n is only 3; the reading firms up as damped rows accumulate, and the scan reports the count rather than asserting the design. ★ WS2 / G1 — UNCHANGED, 1 INDEPENDENT POST-DEPLOY EPISODE OF 4 (WMT 7/23, lag 0, 47→38). The FOMC watch item raised yesterday resolved as a NON-EVENT for G1: the decision moved both tracers UP. WMT trail5d +1.95%, GM +5.24% — both favourable, neither adverse, no episode. GM still has none post-deploy and the strip correctly labels its clock NO TEST CASES YET. RECORDED DELIBERATELY AND NOT COUNTED: today is the first post-deploy session on which the ruled-out episode definitions would each have produced episodes — GM's +5.24% clears THETA in magnitude and would qualify under a bidirectional rule (DP-8), and FTI −10.50%, AG −9.23%, SND −8.79% and NVDA −5.98% would all qualify under a widened universe (DP-9). Under both, G1 would move from 1 to 6 on a single day's data. NONE OF THESE ARE EPISODES AND NONE ARE COUNTED. The counterfactual is recorded so that the cost of holding the pre-registered definition is visible in the record rather than invisible, which is the whole point of pre-registering it. ★ WS1 / G2 — THE PRIMARY READ HAS NOW TAKEN A THIRD VALUE IN THREE SESSIONS AND STILL FAILS. monitor\_strip.py: overlays CONFIRMED 40.0% (n=5) vs overlays DISCOUNTED 20.0% (n=5) → gap +20.0pt, from +15.0pt yesterday and −10.0pt the day before. The mechanism is again legible — the discount arm gained its fifth resolution and it lost, so the arm the overlays disliked got worse. But THE SEQUENCE −10.0 → +15.0 → +20.0 ON n≈5 IS THE FINDING, not the level: three sessions, three values, one sign change, on a footprint that is still near-single-name. (B) Gate-flip @ 70%: net −1, UNCHANGED — still the single 7/13 NVDA disagreement. G2 requires both (A) robust and (B) net ≥ 0 and FAILS BOTH. NO DISPOSITION IS TAKEN. Resolved adjusted signals moved 9 → 10; the per-ticker split is NOT re-derived in this entry and must be recomputed with blend\_eval.py --since 2026-07-13 before G2 is scored, because if the new discount resolution is NVDA the concentration is 9:1 = 90% and DP-10 becomes binding. ★ KEEP-70 — SIXTH CONSECUTIVE IMPROVEMENT: 13/31 = 41.9% (from 43.3% on 7/29, 46.4% on 7/28, 48.1% on 7/27, 50.0% on 7/24, 48.0% on 7/23). Registry now 32 near-miss BUYs. The gate is comfortably supported and the watch item raised 7/23 is closed in substance. ★ H4 — UNCHANGED AND STILL DEMOTED. HIGH-DQ near-miss 6/12 = 50.0% against the ≥60.0% bar, 13 total. No movement against the two-consecutive-readings-at-n≥12 rule. No DQ-conditional design work. ★ DATA INTEGRITY — THE RETIRED SHEET IS STILL IN THE MASTER. The Monitor Strip footer reads "Retired 2026-07-30: Sheet1 — Q1-R closed the guardrail question; guardrail\_trace.py is out of the runner." Per §7 of the workflow, the notice appearing on every run is itself the evidence that the master still carries the tab: the purge is dropping it from the generated copy each session rather than the tab having been deleted at source. Direct inspection of logs\\claude\_equity\_bot\_tracker.xlsx confirms a sheet named Sheet1 whose first row reads "Guardrail Compression Trace — cumulative +5d hit rate by con…", generated by guardrail\_trace.py, carrying 43 cohort rows that stop at 2026-07-20 and a column headed "lead gap (pt)" — a retired criterion, stale by eight sessions, stated in live-criterion grammar, sitting in the workbook that every harness reads. retired\_criteria\_audit.py cannot see it; the audit scans source files, and a workbook tab is its known blind spot. Delete it in the master once; the notice going quiet is the confirmation. ★ RECORD GAP — THERE IS NO 7/24 ENTRY. docs\\analyst\_notes.md runs 7/23 (Day 13) directly to 7/27 (Day 15); no Day 14 entry exists and no 7/24 daily context appears anywhere in the file, yet the master carries a complete 24-row 7/24 cohort and 7/24 is the very date the WS2 coalescing correction turns on. G4's cross-check streak and G6 both cite the notes as evidence source, so 7/24 is currently UNEVIDENCED. Reconstruct it from logs\\signals\_2026-07-24.log or void it explicitly with a dated note saying which was done. ★ SELF-CORRECTION ON THE GHOST ROWS. The record describes Signals 222 / 226 as carrying "date and ticker only." Direct inspection corrects this: they are EXCEL ROWS 222 and 226, which are signals #218 and #222 (data begins at row 5), and they carry a COMPLETE price series across all four columns — AG 19.91 → 17.17 / 18.90 / 16.96 and FTI 68.11 → 68.75 / 68.51 / 66.30, resolved at +5d, +10d and +20d alike. Only Signal, Confidence and Data Quality are null. The rows are therefore not empty shells but fully resolved outcomes missing their signal fields, all three of which are recoverable from logs\\signals\_2026-06-01.log. ANNOTATE RATHER THAN DELETE: deleting them discards two resolved price series to fix a metadata gap. Still an open G4 item either way. ★ DP-8 / DP-9 / DP-10 — THE INSTRUMENT AND THE RECORD DISAGREE, AND THE DISCREPANCY IS RECORDED HERE UNRESOLVED. Phase3B\_Closeout\_Decision\_Worksheet\_v1\_1.docx §3 now shows all three decision points with rulings and a status stamp reading "RULED 7/29 · MET 7/30". This entry's immediate predecessor, dated 7/29, states that "DP-8 and DP-9 \[were] formally entered as OPEN AND UNRULED," and NEW\_CHAT\_BOOT\_PROMPT.md, written at the close of that same session, lists all three as OPEN. THE RULING DATE IS THEREFORE UNVERIFIED AND IS NOT ASSERTED IN THIS RECORD. Three further defects are noted against the worksheet text irrespective of date: (i) "MET 7/30" has no defined meaning for a decision point — DPs are ruled, not met; (ii) DP-9's ruling reads "do not expand episode universe to GM," but GM is ALREADY pre-registered in the universe as the secondary tracer, so the sentence read literally would SHRINK the universe below the pre-registration — the intended ruling is "not past WMT/GM"; (iii) DP-10 rules that a concentration cap applies but sets no number, and any cap below the current 88.9% single-name share flips DP-7 from MET back to NOT MET, which removes G2's breadth condition that was only satisfied on 7/29. NOTED IN FAIRNESS: the substance of the DP-8 and DP-9 rulings runs AGAINST the operator's convenience — both keep G1 blocking, and today is the first session on which relaxing either would have closed it. Only the provenance is in question, not the direction. ★ TOOLING DEPLOYED — signal\_scan.py AND log\_tracker\_crosscheck.py. Two harnesses built today and run against this session. signal\_scan.py reads one signals log and reports run integrity (count, era, channel presence, regime uniformity, S1 cold starts), the per-ticker channel table, channel reconciliation assertions and the cohort profile; it caught the D1 damp mismatch and the confidence\_blend semantics without being asked to look for either. It deliberately DOES NOT count WS2 episodes — coalescing lives in h1\_lag\_trace.py and a second tool emitting an episode count is how two figures that are both correct get quoted as each other. log\_tracker\_crosscheck.py performs the daily 24/24 reconciliation and HARD-REFUSES tracker\_with\_registry.xlsx as an input, exiting 2; it also separates a PRECISION finding (log value rounded to the master's decimal places, the GLD paste signature) from a genuine MISMATCH. Both are formula-cache immune by construction — the scan touches no workbook, the cross-check reads only the pasted columns A–G. Both write nothing. Both exit 1 on findings for future hook use, though neither is in the pre-commit hook, because a legitimate finding like today's damp mismatch would block unrelated commits. THETA provenance confirmed clean end-to-end: the strip reports "THETA=5.0% from risk\_engine.DampingConfig.THETA" and the scan imports the same constant rather than defining its own. ★ OPERATIONAL — THE WRONG WORKBOOK WAS UPLOADED, AND THE GUARD CAUGHT IT. tracker\_with\_registry.xlsx was supplied for the review rather than logs\\claude\_equity\_bot\_tracker.xlsx; §6 makes the report copy output-only and never an input, and log\_tracker\_crosscheck.py refused it outright. The session was completed without compromise because columns A–G proved byte-identical across all 1,219 rows between the report copy and the master held from earlier in the day, so the cross-check ran validly against the master and every resolution figure in this entry is computed from the Price columns. The report copy's formula cache reads 19.7% blank (pending rows only), confirming the open-in-Excel step was followed. Noted so the pattern does not become habit: the master is the monitoring input, and the master on the review side is now one edit behind the operator's.

## 7/31 (Phase 3-B Day 19) — ★ THE DP-8 / DP-9 / DP-10 LOOP IS CLOSED IN THE RECORD AT THE WORKSHEET'S DATE; G2 TAKES **DESCOPE** RATHER THAN A NEGATIVE VERDICT, BECAUSE A GENERAL-FORM STANDARD APPLIED HONESTLY SUPPORTS NEITHER; AND G1 IS RECORDED **INSUFFICIENT TEST CONDITIONS** ON COMPUTED ARRIVAL-RATE EVIDENCE. **CROSS-CHECK NOT RUN — `logs\\signals\_2026-07-31.log` was not supplied to the review, so today's 24/24 reconciliation is NOT VERIFIED and today's era stamp, channel presence and regime uniformity are unconfirmed.** This is recorded as a gap, not a pass: G4 requires the cross-check streak clean THROUGH the exit review, so 7/31 must be reconciled with `log\_tracker\_crosscheck.py` before G4 is signed. From the master via the report copy: totals 1,243 rows, 52 cohorts; today's cohort is 24 HOLD / 0 BUY, DQ 18 HIGH / 6 MEDIUM / 0 LOW, confidence mean 50.5, sd(pop) 12.02, range 30–68, none at the 70% gate. Resolutions are COMPLETE at all three horizons with zero missing — the first session in the 3-B record with no outstanding resolution at any horizon. ★★ DP-8 / DP-9 / DP-10 — LOOP CLOSED, WITH THE DISCREPANCY PRESERVED RATHER THAN ERASED. Ruling date of record is **2026-07-29** per `Phase3B\_Closeout\_Decision\_Worksheet\_v1\_1.docx` §3, entered into this record on 2026-07-31. DP-8 — episodes stay ONE DIRECTION (adverse only). DP-9 — the episode universe is NOT widened. DP-10 — a cap applies on any single name's share of resolved adjusted signals. THE RECORD SHOWS A CONFLICT AND IT IS LEFT VISIBLE: the 7/29 entry in this file states that "DP-8 and DP-9 \[were] formally entered as OPEN AND UNRULED," and `NEW\_CHAT\_BOOT\_PROMPT.md`, written at the close of that same session, lists all three as OPEN. THE 7/29 ENTRY IS NOT EDITED. The standing rule that historical entries describe what was believed at the time — the same rule that excludes this file from `retired\_criteria\_audit.py` — applies to the operator's own record exactly as it applies to the guardrail. A reader will therefore find an entry saying "unruled" followed two days later by a ruling dated to that same day; that is the honest shape of what happened and it is preferable to a clean record that is wrong. NOTED FOR THE RECORD: the substance of DP-8 and DP-9 runs AGAINST the operator's convenience — both keep G1 blocking, and 7/30 was the first session on which relaxing either would have closed it (GM +5.24% under DP-8; FTI −10.50%, AG −9.23%, SND −8.79%, NVDA −5.98% under DP-9; together 1 → 6). Only the provenance was ever in question, never the direction. TWO DEFECTS REMAIN IN THE WORKSHEET TEXT AND ARE NOT DATE QUESTIONS. (i) DP-9's ruling reads "do not expand episode universe **to GM**," but GM is already pre-registered as the secondary tracer — read literally the sentence SHRINKS the universe below the pre-registration. The intended and recorded meaning is "not PAST WMT/GM." (ii) DP-10 rules that a cap applies but sets no number, so it cannot be scored. Recorded consequence: any cap below the current single-name share flips DP-7 from MET back to NOT MET. Both need a dated edit before signature. ★ G5 — SIGNED. Trigger service, VERDICT: SERVED, closed 2026-07-29 on complete evidence with the disposition already in the record. G5 was independent of every other gate and needed nothing further; the signature line had been open three days for no reason. ★★ G2 — THE NEGATIVE-VERDICT STANDARD WAS RULED IN GENERAL FORM FIRST, THEN APPLIED, AND IT DOES NOT PRODUCE A NEGATIVE VERDICT. The standard, ruled 2026-07-31 and written before scoring: a REJECT-AND-RETAIN-BASE verdict requires ALL of — (i) DP-1's count satisfied, so the window was genuinely given its chance; (ii) (A) overlay predictive value NOT ROBUST under leave-one-cohort-out; (iii) (B) gate-flip net < 0; (iv) NEITHER failure attributable to a single cohort or single observation — the failure must persist when the largest-effect cohort is removed; (v) the reading STABLE across at least two consecutive sessions. Conditions (iv) and (v) are the direct lessons of H4 reversing twice in three days and of G2's own primary read taking three values in three sessions; they are stated in general form and are neutral as to which way the current numbers fall. SCORED AGAINST IT: (i) MET — 13 cohorts against N=5. (ii) MET — one fold at −10pt, and the criterion requires all folds the same sign. (iii) MET — net −1. (iv) **FAILS** — the entire (B) deficit is the single 7/13 NVDA gate-flip; remove that one observation and net is 0. (v) **FAILS on (A)** — the primary read ran −10.0 → +15.0 → +20.0pt across three consecutive sessions. TWO OF FIVE CONDITIONS FAIL, SO A NEGATIVE VERDICT IS NOT SUPPORTED. It is also worth saying plainly that a POSITIVE verdict is further from support than a negative one. THE HONEST CLOSE IS **DESCOPE**, and G2 explicitly admits it. DESCOPE is defined in the 3-A vocabulary as deliberate termination BEFORE test — a decision, not a finding — and that is exactly the true statement here: the blend was never adequately tested. n=5 vs n=5 on a near-single-name footprint, one gate-flip in the whole record, and a primary read that moves 30 points on two observations is not an evidence base from which to conclude anything about the blend's value in either direction. Recording it as a negative VERDICT would overstate what the data supports and would put a false finding into the permanent record; recording it as DESCOPE states the truth, retains the base signal, and leaves the door open on documented triggers. DISPOSITION: **G2 — DESCOPE. Blend shelved, base signal retained as the official advisory output, re-open triggers recorded.** PRECONDITION BEFORE SIGNATURE: the fold array scored above is from the 7/29 `blend\_eval.py --since 2026-07-13` run and is two sessions stale; re-run it and confirm (ii)/(iii)/(iv) against fresh output before the disposition is signed. Do not sign on a stale exhibit. ★ WS1 DESIGN NOTE — SIGNABLE, AND THE `\[?]` IS CLOSED. `WS1\_TripleBlend\_Design\_Note.md` reads Status: DRAFT v1.0, UNSIGNED. Its own signature condition — "once weights (DP-W2) and the component set (DP-W1) are ruled and the blend produces its first cohorts" — is fully met: `WS1\_Deploy\_Notes.md` records DP-W1 (all three components) and DP-W2 (0.15/0.15) as ruled, and thirteen blended cohorts have resolved. Its T3 compliance holds on inspection — §2's rule uses direction-agreement times overlay magnitude on continuous confidence and never references band membership. So G2's design-note condition was NOT MET for want of a signature, not for want of evidence, and that six-day-old `\[?]` is now resolved as a verified fact. Under a DESCOPE the note is signed as the record of what was built and then marked SUPERSEDED BY DESCOPE, rather than left as an unsigned draft that a future reader cannot tell was ever agreed. ★ DP-5 — RULED 2026-07-31: OVERLAP PERMITTED, SCOPE WORK ONLY. Phase 3-C design and scoping may proceed while Phase 3-B gates remain open. THE RULING IS NARROW AND ITS LIMITS ARE PART OF IT: no 3-C go-live, no code deployed to the live runner, no era-label change, and NO 3-B GATE CLOSES OR RELAXES BY REASON OF THIS RULING. This is not an amendment. E6 pre-registers exactly this option — "Overlap only by explicit scope ruling (DP-5; default sequential)" — so exercising it is using the instrument as written rather than bending it. The distinction that makes it safe is that overlap moves DESIGN work forward while leaving every EVIDENCE question untouched; nothing about G1's episode count, G2's folds or G4's integrity items changes because 3-C scoping is underway. ★★ G1 — DISPOSITION: **INSUFFICIENT TEST CONDITIONS**, ON COMPUTED EVIDENCE. G1's pre-registered dispositions are PASS ("lag compressed") and FAIL ("model-side remedy class exhausted at 3-B"). NEITHER FITS, AND THE INSTRUMENT HAS NO THIRD OPTION — that gap is itself the finding. FAIL is unavailable because the one post-deploy episode is a SUCCESS: WMT 7/23, lag 0, confidence 47→38, with D1 contributing zero damping, so the response was entirely model-side, which is precisely what S1 was built to produce. One cannot record "the raw channel did not move" when it demonstrably did. PASS is unavailable because n = 1 against a pre-registered 4. THE EVIDENCE FOR THE DISPOSITION IS THE ARRIVAL RATE, COMPUTED FROM THE MASTER RATHER THAN ESTIMATED: adverse tracer episodes at THETA = 5.0%, coalesced — WMT 2 pre-deploy in 28 sessions and 1 post-deploy in 19; GM 3 pre-deploy in 28 and 0 post-deploy in 19. Blended full-record rate 0.115 episodes per session; observed post-deploy rate 0.053. THREE MORE EPISODES ARE REQUIRED. At the full-record rate that is approximately 26 further sessions, about five weeks; at the observed post-deploy rate, approximately 57 sessions, about eleven weeks. RECORDED DIVERGENCE: this count reads 2 WMT pre-deploy episodes where `monitor\_strip.py` reports 1 — the strip's coalescing or price series differs from the simple consecutive-run rule used here. The divergence is noted rather than resolved because it does not move the conclusion; post-deploy is 1 on both counts. THE CRITERIA DOCUMENT'S OWN PROJECTION IS THEREFORE FALSIFIED: "Earliest realistic exit review: late July – early August 2026" was computed on COHORTS, and DP-6 correctly moved the basis to EPISODES on 7/28 without anyone re-deriving the timeline afterwards. That is a self-correction the record should carry. THE DISPOSITION SAYS WHAT IS TRUE: the remedy could not be evaluated because the market did not supply test cases, the one test case available was passed, and the bar is NOT LOWERED to manufacture a close. DP-8 and DP-9 are NOT reopened for this purpose — widening the detector under schedule pressure is the exact failure mode pre-registration exists to prevent, and 7/30 demonstrated its size. ★ G3 — DISPOSITION: **PARK**, WITH TRIGGER; AND E1's TECHNICAL PREREQUISITE IS AMENDED, STATED AS AN AMENDMENT. WS3 was never built — `commodity\_context.py` and `commodity\_backed\_equity\_context.py` appear ZERO times across the whole of this file, and `WS1\_Deploy\_Notes.md` §7 still carries WS3 as an open item. PARK trigger: G3 re-opens if a downstream workstream requires commodity context in the prompt, or at the 3-C build if the provider registry proves an insufficient integration template. THE AMENDMENT, RECORDED PLAINLY BECAUSE IT IS ONE: E1 states that "G3 is therefore a technical prerequisite (WS3 is the integration template)." The integration template in fact exists — WS1 shipped `context\_providers.py` with `run\_prompt\_context` wired and the prompt-provider slots deliberately empty, and `Phase3C\_EDGAR\_Scope\_Spec.md` §3 shows `edgar\_client` registering in a single line. So E1's stated RATIONALE is satisfied by other means while E1's LETTER is not. Adopting the rationale over the letter unblocks the thing the operator wants to do, which is exactly why it is being written down as a dated amendment rather than absorbed as a reading. AMENDED: E1's technical prerequisite is satisfied by the WS1 provider registry rather than by WS3; G3 PARKS without blocking E1. ★ G4 — CLERICAL ITEMS CLEARED OR SCHEDULED. The two ghost rows are ANNOTATED, not deleted: Excel rows 222 and 226 (signals #218 and #222), 2026-06-01, AG and FTI, carrying NULL signal, confidence and data quality but a COMPLETE price series at all four columns — AG 19.91 → 17.17 / 18.90 / 16.96 and FTI 68.11 → 68.75 / 68.51 / 66.30. Deleting them would discard two fully resolved outcomes to repair a metadata gap; the three missing fields are recoverable from `logs\\signals\_2026-06-01.log`. `Sheet1` — the retired Guardrail Compression Trace — WAS DROPPED AGAIN ON 7/31, the second consecutive session, which per §7 is the standing evidence that the master still carries it; it is deleted at source in `logs\\claude\_equity\_bot\_tracker.xlsx` and the drop notice going silent on the next run is the confirmation. The missing 7/24 entry is reconstructed from `logs\\signals\_2026-07-24.log`. OUTSTANDING AND BLOCKING G4's SIGNATURE: the 7/31 cross-check itself, which cannot be run without today's log. ★ 7/24 COHORT RESOLVED 14/24 = 58.3% — mean +5d −0.41%, dispersion (sd, population) 6.00%, 9 HOLD band-breaches split 3 UP / 6 DOWN; movers MSFT +20.6%, SND −11.0%, AG −10.2%, AAPL −6.9%, FTI −6.6%. Identical accuracy to 7/23 on an identical breach count, which is the identity behaving exactly as described. IDENTITY REFRESHED ON THE LARGER SAMPLE: across 47 resolved +5d cohorts, corr(band-breach count, cohort accuracy) = −0.9650, essentially unchanged from −0.9654 at 46. The result is stable as n grows, which is what distinguishes it from every small-n reading in this project. ★ H4 — DECLINED AGAIN: HIGH-DQ near-miss 6/13 = 46.2%, from 50.0%, against the ≥60% bar. Four consecutive declining reads (60.0000% → 54.5% → 50.0% → 46.2%). STAYS DEMOTED; no DQ-conditional design work. ★ KEEP-70 — SEVENTH CONSECUTIVE IMPROVEMENT: 13/32 = 40.6%, from 41.9%. The gate is comfortably supported and the 7/23 watch item is closed in substance. ★ WS2 / G1 MONITOR — the "last episode 2026-07-24" defect in `monitor\_strip.py` is UNFIXED and now reads "5 session(s) ago" while the coalesced ledger still correctly shows the single 7/23 episode. It is now attached to a gate carrying a formal disposition, so the fix is no longer cosmetic.

## 8/02 (Phase 3-C EW1 build session) — ★ EDGAR BUILT; THREE DECISION POINTS RULED BEFORE GO-LIVE; ALL SIX 3-C ENTRY GATES DISPOSITIONED; SEVENTEEN DEFECTS FOUND AND FIXED, SIXTEEN OF THEM FROM LIVE RUNS RATHER THAN FROM THE 102 SELF-TEST ASSERTIONS. Build session, no cohort. ★★ DP-3C-g RULED — the 3-C filing set INCLUDES XBRL FINANCIAL STATEMENTS alongside the MD\&A extract, widening Kickoff §1's "Form 4 · 8-K · 10-Q/10-K MD\&A extracts" which was written under the heading "this and nothing more." Rationale of record: the mandate is PRIMARY-SOURCE filing context and MD\&A is management's narrative ABOUT the statements, so shipping the commentary without the numbers serves the letter of the scope against its purpose. Timing is the reason it was ruled now rather than later — the treatment was not yet live, so the widening cost nothing, whereas the same widening after go-live would change the treatment mid-measurement. ★ DP-2 RULED — single live arm, era `A-S1D1-B1-E1`; A/B stays terminated; the era stamp lives in the JSON `prompt\_variant` field and NEVER inside the phase bracket. ★ DP-3C-e RULED — E4 cohorts stratify by COVERAGE TIER, not by era stamp alone. DP-3, DP-4 and DP-3C-a/b/c implemented at their pre-registered defaults, unchanged. NEW AND UNRULED — DP-3C-f: AG and NTR confirmed foreign private issuers (40-F/6-K); extending the filing set would move both T-C → T-A and raise practical coverage 15/24 → 17/24; proposed no change in v1. ★ ENTRY GATES — ALL SIX DISPOSITIONED. E1 scope entered (amended by DP-3C-g) · E2 RULED (DP-2) · E3 PASSED (`edgar\_parser\_audit.py` against the real parsers on a synthetic 24-row 3-C log) · E4 PRE-REGISTERED before go-live per Kickoff §5 (`Phase3C\_E4\_Endpoint\_PreRegistration\_v1.md`) · E5 compliant · E6 MET (worksheet v1.2 signed 7/31). ★★ COVERAGE MEASURED, AND IT CORRECTS THE KICKOFF — IN THE DIRECTION THAT WARRANTS THE MOST SCEPTICISM. `\[V]` `edgar\_client.py --coverage`, 90-day window, live SEC: T-A live event flow 14 (AAPL, CORN, DOW, FTI, GM, JPM, MSFT, NKE, NVDA, PM, PWR, RTX, SND, WMT) · T-B periodic only 1 (GLD) · T-C dark 8 (AIQ, AG, NTR, QQQ, SCHD, SPY, VTI, XLU) · skipped 1 (CBRS). PRACTICAL COVERAGE 15/24 = 62.5% — the tool's own summary line reads 17/24 = 70.8% because it counts all-time form presence, and AG and QQQ have historical filings but nothing in window and no periodic, so their sections render empty. 62.5% is E4's denominator. Event supply: 8-K 50/90d = 16.9/month = 0.81/session; Form 4 206/90d = 69.7/month = 3.32/session; WMT alone is 24% of Form 4 volume and the top three names 59%. THREE CORRECTIONS TO KICKOFF §2, ALL `\[V]`: AG and NTR `\[?]` resolved as foreign filers; CORN is NOT filing-less (CIK 0001471824, 2 8-Ks in 90d, 10-Q filed 5/11); GLD is NOT filing-less (CIK 0001222333, 10-Q filed 5/05). §2 argued \~100 MEDIUM-DQ rows were untreatable across CORN (39), GLD (33) and AIQ (29); two of the three are reachable and only AIQ's 29 hold. THIS CORRECTION RUNS TOWARD THE TREATMENT AND IS FLAGGED AS SUCH — it makes EDGAR look better than the pre-registered scoping did, which is exactly the direction to distrust; it is recorded because it is measured, not because it is convenient, and the raw `--coverage` output is the exhibit. ★ BUILT: `edgar\_client.py` NEW (prompt provider, SEC fetch/cache/extract, `--coverage` / `--ticker` / `--xbrl` / `--selftest`, 102 self-test assertions all passing); `edgar\_parser\_audit.py` NEW (E3 pre-deploy audit against the real parsers); `main.py` +65/−8 (EQUITY\_EDGAR flag, era derived from it, conditional registration, `run\_prompt\_context` call, `prompt\_caches` threaded, the `E\[…]` tag); `claude\_signal.py` +18/−1 (`extra\_context` parameter appended as a prompt section); `context\_providers.py` UNCHANGED as Scope Spec §8 requires; the two bats unchanged and confirmed correct. FLAG-AND-ERA ATOMICITY: `EDGAR\_ENABLED` and `PROMPT\_VARIANT` are derived from one another so EDGAR cannot go live under the pre-EDGAR stamp — treated rows filed as control rows would poison E4's split unrecoverably, and the state is now unrepresentable rather than merely discouraged. ★★ SEVENTEEN DEFECTS, SIXTEEN FROM LIVE RUNS AGAINST REAL FILERS; SELF-TESTS CAUGHT ONE, AND TWO OF MY OWN TESTS WERE THEMSELVES DEFECTIVE (one vacuous — it asserted "instant items have no YoY" and passed only because the fixture had a single entry; one pinning a bug as correct — it asserted the MD\&A extract should open with the orphaned tail of a section heading). Grouped by root cause: (i) `companyfacts` IS AN APPEND-ONLY ARCHIVE, NOT A CURRENT VIEW — concepts a filer abandons persist forever; RTX rendered a 2020 gross profit and a 2024 debt balance as current, and NVDA lost its revenue line entirely because the preferred concept fossilised at FY2022 while a live alternative sat unused; fixed by a staleness rule (every line must end on the anchor date) plus concept selection by currency rather than mere presence. (ii) CACHES MASKING CORRECT FIXES, THREE TIMES — rendered-HTML Form 4s served for raw-XML requests, `\_cache\_path` collapsing directories via `basename`, and the derived `fin\_\*.json` keyed on an accession that does not change when the extractor does; fixed by read-time validation, full-path keys and an `EXTRACT\_SCHEMA` version. (iii) VALUES THE TOOL DID NOT COMPUTE — `net direction: mixed` printed from 0 buys / 0 sells; RSU grants (code A) counted as purchases, which would have read as "buying" every vesting quarter at MSFT/WMT/JPM; percent change across zero (CORN's +$30.4M from −$3.1M rendered as −1077.9%). (iv) MIXED OR MISLEADING PRESENTATION — statement lines from different periods in one block (operating income exceeding gross profit), XBRL lagging the filing with no note, XBRL viewer renderings used as 8-K bodies, silent truncation at 8 lines while the tag said 9. (v) EXTRACTION QUALITY — MD\&A landing on forward-looking boilerplate, tables of contents or mid-sentence; the 8-K exhibit fallback missing "Exhibit No. 99". TWO SELF-INFLICTED REGRESSIONS, BOTH SURFACING AS ABSENCES RATHER THAN ERRORS: a TOC guard that deleted DOW's genuine net-sales table, and a strict duration match that would have removed operating cash flow for every YTD-only filer. ★ CARRIED: `context\_providers.py` latent trap — providers are called as `p.fn(ticker, caches or {})` and an empty dict is falsy, so `{} or {}` hands the provider a throwaway; harmless today because prefetch populates first, but no provider can lazily warm an empty cache; the fix is `caches if caches is not None else {}` and it is NOT applied because Scope Spec §8 pins the file at no-change for 3-C. UTC date stamp — the section header uses `datetime.now(timezone.utc)` so evening runs in Texas read tomorrow's date; no effect on the 9:30 CST canonical run.

## 8/03 (Phase 3-C EW2 go-live — FIRST LIVE EDGAR COHORT) — ★★ EDGAR WENT LIVE AND THE PLUMBING HELD, BUT THE COHORT IS NOT USABLE AS A MEASUREMENT AND IS RULED A SHAKEDOWN, EXCLUDED FROM E4 ENTIRELY. Cross-check 24/24 — `signals\_2026-08-03.log` ↔ `logs\\claude\_equity\_bot\_tracker.xlsx` reconcile clean, reproduced independently from the log JSON at full sub-cent precision; era `A-S1D1-B1-E1` present in every Signal JSON and in NO phase bracket; E-tag distribution exactly the pre-registered 15 covered / 9 dark (AG, AIQ, CBRS, NTR, QQQ, SCHD, SPY, VTI, XLU); all three parsers — `analyze\_log.py`, `parse\_log\_to\_tracker.py`, `signal\_scan.py` — independently read 24 rows with real Accounts; 23 HOLD + 1 BUY (NVDA 68, rejected); DQ 21 HIGH / 3 MEDIUM; totals 1,267 rows, 53 cohorts; recalc 0 errors on 8,542 formulas; resolutions complete at all three horizons. ★★ N-1 — YTD FIGURES RENDERED UNDER A QUARTER LABEL, AND THE `\[6M YTD]` MARKER §11 PRE-REGISTERS NEVER FIRES. `\[V]` `edgar\_client.py --xbrl PWR`: both buckets sit in the SAME accession `0001050915-26-000025` — revenue 180d \[H] $17,431,784,000 versus 90d \[Q] $9,556,997,000, and the H figure was rendered under the header "10-Q Q2 FY2026"; identical on gross profit, operating income, net income and diluted EPS. Per §10.2's own dichotomy this is a CLIENT SELECTION BUG, NOT a filer tagging quirk. Corroborated against each name's own 8-K in the same section: PWR 8-K reports Q2 revenue $9.6B, FTI MD\&A $2,763.1M, RTX 8-K $24.7B, GM 8-K $48.0B, PM 8-K Q2 diluted EPS $1.80 against a rendered 3.36, and AAPL 8-K quarterly revenue $109.4B against a rendered $364.4B (the 9M variant). THE FIX IS TWO-PART AND PWR DEMONSTRATES BOTH IN ONE NAME: PWR's operating cash flow has NO 90-day bucket for 2026 — only H1 $1,487,188,000, because 10-Q cash-flow statements are cumulative by construction — and its rendered +176.0% is H1-vs-H1 and arithmetically correct, so "always prefer Q" would break it. Rule of record: for flow concepts prefer the bucket whose duration matches the fiscal quarter (\~90d) AND whose end date equals the anchor date; where only a cumulative bucket exists, render it and FIRE the `\[6M YTD]` / `\[9M YTD]` label; YoY stays same-duration either way, which already works; and the section header must state the period the block actually reports. SCOPE, CHARACTERISED EXACTLY `\[V]`: affected iff the latest periodic is Q2 or later in the filer's fiscal year — AFFECTED 6 (AAPL 9M-as-Q3; FTI, GM, PM, PWR, RTX H1-as-Q2), IMMUNE 9 (CORN, DOW, GLD, JPM, NVDA, SND, WMT are Q1 filers where YTD ≡ Q1; MSFT and NKE are 10-K FY). THE FOOTPRINT EXPANDS WITHOUT ANY CODE CHANGING — WMT, JPM, NVDA, SND, CORN and GLD all file their next periodic inside the E4-2 measurement window and roll from immune to affected, taking 6/15 toward roughly 13/15 by the first read. IT REACHED THE MODEL: FTI's signal cited "long-term debt down 33%, operating income up 34%" (both H1 statements figures, read as current-quarter) and AAPL's mixed the 8-K's quarterly 16% revenue with the statements block's 9M +43.1% operating cash flow in a single clause. ★★ F-1 — BUDGET EXHAUSTION SILENTLY DROPS THE XBRL STATEMENTS BLOCK. The warning fired 09:49:12.540 during JPM. Split at that boundary: pre-budget AAPL, CORN, DOW, FTI, GM, JPM all carry `fin=`; post-budget MSFT, NKE, PM, PWR, RTX, SND, WMT, NVDA ALL LACK IT; and GLD — post-budget but needing no schema recompute — carries it, which is the control that isolates the mechanism. Confirmed by standalone reproduction: the eight dropped names ALL re-logged `schema N != 6 — recomputing` when run individually while the six pre-budget names did not, so the in-run recompute started, was abandoned at budget, and NEVER WROTE TO CACHE. Cache writes DO persist `\[V]` — a second `--ticker MSFT` logged no recompute line, and all 15 covered names are now warm at EXTRACT\_SCHEMA 6. THE BUDGET IS MEASURING THE WRONG THING: prefetch ended 09:47:08.210 and the warning fired at 09:49:12.540 = 124.3s of WALL CLOCK containing 8 Claude signal calls (\~94s), 8 news fetches (AAPL alone 10.2s) and the quote/price-history round trips; EDGAR fetch/extract is roughly 7s of it, about 6% of a budget nominally allocated to EDGAR. Raising `EDGAR\_MAX\_SECONDS` buys more Claude API time. ★★ FOUR DECISION POINTS RULED 2026-08-03. DP-3C-h — retain 8/03 tagged `partial-treatment` with a pre-committed exclusion rule; RULED AND THEN SUPERSEDED THE SAME SESSION by DP-3C-k, and recorded rather than deleted because it was ruled against F-1 alone, before N-1 was found, and F-1 is a MISSING treatment while N-1 is a WRONG one — a `partial-treatment` tag does not describe wrong values. DP-3C-i — the `E\[…]` tag CARRIES FILING DATES, because E4-2's ADJACENT (filing within K = 5 trading days) versus COVERED-QUIET split is not reconstructible from the durable record as the tag stands: `edgar\_cache\\` is gitignored, deletable and re-fetchable, so window membership survives nowhere permanent. Log-only change; does not touch the prompt; safe mid-measurement. ONE DISAMBIGUATION THE AMENDMENT FORCES: E4-2 defines ADJACENT as an 8-K OR Form 4 within the window with no restriction to open-market transactions, so `form4=…@D` must carry the date of the most recent Form 4 of ANY transaction code — including grants (A), option exercises (M) and tax withholding (F), which never move net direction — or the tag's date and the endpoint's definition disagree and the disagreement will not surface until the E4-2 read. DP-3C-j — the EDGAR budget bounds time spent INSIDE `edgar\_client` fetch/extract, not run wall clock; degradation becomes visible PER TICKER in the tag (`fin=degraded`, distinct from `fin=none`) rather than once at run level, because a tag that omits `fin=` for two different reasons is a tool reporting a value it did not compute; and Workflow §18's "later tickers silently ran without filings" is factually wrong and is corrected to "lost the statements block only." ★★ DP-3C-k — FIX N-1 NOW; 2026-08-03 IS A SHAKEDOWN COHORT, EXCLUDED FROM E4 ENTIRELY; THE E4 CLOCK STARTS AT THE FIRST CLEAN COHORT. Cost one cohort of \~20; fixing at cohort 10 costs ten, and every intervening cohort carries a known-defective treatment. THE EXCLUSION IS E4-SCOPED, NOT RECORD-SCOPED — all 24 rows still paste into the master, the +5d/+10d/+20d resolutions are still entered, and NVDA's near-miss still counts toward KEEP-70, H4 and the monitor strip; only E4-1, E4-2 and E4-3 exclude the cohort, and over-excluding would silently move KEEP-70's denominator. ★ TWO SELF-CORRECTIONS THIS SESSION. (1) F-1b (Form 4 truncation) was ASSERTED AND THEN RETRACTED: the claim that post-budget names lost \~39 Form 4 filings was inferred by dividing 90-day `--coverage` counts by 3 to predict a 30-day window, and standalone reproduction shows all eight post-budget names return BYTE-IDENTICAL 8-K counts, Form 4 direction and periodic. The division was invalid on the pre-registration's own terms — §2 states Form 4s cluster at \~3 filings per event, so uniform arrival was never a safe assumption. The original reading ("lost only the statements block") was correct and the retraction of it was the error; net effect, the error INFLATED apparent damage. (2) F-4 (event-supply shortfall) RETRACTED, same root cause: today's `--coverage` reads 8-K 49/90d = 16.6/month and Form 4 197/90d = 66.6/month against 16.9 and 69.7 pre-registered, within noise on a window rolled forward one day — E4's rates are intact and the tiers unchanged. ★ SMALLER FINDINGS: N-2 `\[?]` — DOW's revenue YoY (−6.1%) implies a prior-year Q1 that appears nowhere tagged (H1 2025 20,535 − Q2 2025 10,104 = 10,431, and 9,794/10,431 − 1 = −6.11%), which if derived is adjustment where §11 promises lines are DROPPED not adjusted; unresolved pending N-6. N-3 — WMT renders "0 buys / 2 sells" then "1 of 5 filed under a 10b5-1 plan" and the 5 has no referent in the block; reproduces standalone, so not a budget artifact. N-4 — `--coverage` buckets contradict its own rows (AG bucketed "insider only" while its row reads 0 Form 4 and "outside the 3-C filing set"; QQQ bucketed "event only" with 0/0 and no periodic), it prints "ANY coverage 17/24 = 70.8%" prominently, and it NEVER EMITS the T-A/T-B/T-C tiers though the pre-registration cites its raw output as the exhibit for a 62.5% denominator. N-5 — DOW operating cash flow YoY +1135.2% off a $91M base; correct and correctly sourced, but the near-zero denominator makes the percentage uninformative. N-6 `\[?]` — `--xbrl` appears to cap output at 6 entries per concept with no truncation notice, which defeats the absence-checking §10.2 explicitly asks it to support. ★ WHAT WORKED, RECORDED BECAUSE ABSENCES WERE THE STATED RISK `\[V]`: DOW's fossilised `GrossProfit` (FY2020) and `LongTermDebt` (2024-12-31) are both correctly ABSENT from the rendered section; DOW reports "(no concept tagged; tried OperatingIncomeLoss)" and "(no concept tagged; tried Liabilities)" rather than substituting a near-miss concept; percent-across-zero held on three names (DOW net income, PM shareholders equity, SND operating income); the PRIOR-period note fired on DOW; Form 4 transaction-code discipline held on MSFT, SND and NVDA ("compensation mechanics, not a discretionary view"); and `signal\_scan`'s `\[FAIL] D.op == B.blend\_op` on NVDA (op 68 vs blend\_op 70) is CORRECT BEHAVIOUR — the risk engine rejected at 68 < 70, and had it read the blend channel it would have APPROVED a BUY, so the descoping is load-bearing on the gate and behaved; the check's wording predates the descope and should be rephrased as informational. `ticker\_suggester.py` DOES still run (09:52:44–09:53:07, 751 in / 1,104 out, excluded from `analyze\_log`'s cost line), closing a `\[?]`. ★ CHANGE ORDER, DO NOT REORDER: (1) add `signal\_scan.py` to `edgar\_parser\_audit.py` — it parses the E tag, it is NOT in the audit, and it was already the third instance of the hardcoded-phase-token defect class after `analyze\_log.py` 6/15 and `parse\_log\_to\_tracker.py` 7/07, so amending the tag before adding it repeats that defect a fourth time; (2) update the audit to synthesise the amended tag and the 3-C phase token; (3) apply N-1's bucket-selection and YTD-label fix; (4) apply DP-3C-i and DP-3C-j; (5) correct the `\[PHASE 3-B DRY RUN]` token in `main.py`; (6) re-run `edgar\_parser\_audit.py`, exit 0 required; (7) `--selftest` with a new regression test carrying both an H and a Q bucket and one with H only; (8) only then `set EQUITY\_EDGAR=1` and run. ★ NOTE FOR THE RECORD: the 13:31:50 audit run PASSED against the CURRENT tag and says nothing about the amended one. Defect count for this client now stands at 17 from the build plus 6 from the first live run; nineteen of twenty-three surfaced from live runs rather than tests.

## 8/04 (Phase 3-C — CONTROL COHORT, EDGAR FLAG NOT SET) — ★★ THE 70% BUY GATE WAS TESTED FOR THE FIRST TIME IN THE PROJECT'S HISTORY AND A DIFFERENT RULE ANSWERED; THE RISK ENGINE HAS NEVER APPROVED A DIRECTIONAL SIGNAL; AND THE 7/28 COHORT RESOLVED AT THE HIGHEST DISPERSION IN THE RECORD. Cross-check 24/24 — `signals\_2026-08-04.log` ↔ `logs\\claude\_equity\_bot\_tracker.xlsx` reconcile clean, reproduced independently from the log JSON at full precision; era `A-S1D1-B1` with ZERO `E\[…]` tags, no `\[EDGAR] prefetch` line and no budget warning — byte-identical to a 3-B run exactly as Workflow §1 promises; 23 HOLD + 1 BUY; DQ 19 HIGH / 5 MEDIUM; totals 1,291 rows, 54 cohorts; recalc 0 errors on 8,542 formulas; resolutions complete at all three horizons with zero unresolved-but-due; no premature K:N values on today's rows. ★ THE FLAG WAS NOT SET — OPERATOR OMISSION, NOT A DEFECT, AND THE SAFETY PROPERTY WORKED AS DESIGNED. A Schwab token expiry forced a browser reauthorisation and `set EQUITY\_EDGAR=1` was missed in the new console; the run therefore executed 11:08–11:14 CST rather than at the canonical 9:30, so Px@signal for all 24 rows is a mid-session quote roughly 1.5 hours later than every other cohort — immaterial to +Nd returns (closing prices) and to any within-cohort comparison, but recorded. A FORGOTTEN FLAG PRODUCED A CORRECTLY LABELLED CONTROL RUN RATHER THAN A MISLABELLED TREATMENT ONE, which is the whole point of the flag-and-era atomicity ruled on 8/02. NO SECOND RUN WAS TAKEN: `signal\_state.json` had already appended, the log had been written, a second cohort on one date would break the trading-day index that computes every resolution, and N-1 REMAINS UNFIXED so an EDGAR run today would have produced a second defective cohort rather than a clean one. THE E4 CLOCK THEREFORE HAS STILL NOT STARTED, and accumulating further control cohorts is now a RECORDED CHOICE rather than drift — E4-1 reads DQ-mix pre-era versus post-era and control cohorts ARE its baseline. ★★ NVDA BUY AT 72% — THE FIRST AND ONLY BUY TO CLEAR THE 70% GATE IN 1,291 ROWS `\[V]`, and the risk engine rejected it anyway on `Too many open positions: 16 >= max 8`. ★★ THREE DEFECTS IN `risk\_engine.check\_signal` CHECK 6. D-1 SINGLE-ACCOUNT SCOPE `\[V]` FROM SOURCE — `main.py` L285–286 reads `portfolio = portfolios\[0] if portfolios else {}` under the comment "Use the first portfolio for risk eval — simplest for Phase 2", so the engine sees ONE account; Roth IRA carries 16 positions and the Individual account's 20 are invisible, and the engine's reported 16 matches Roth's raw count exactly. D-2 INSTRUMENT-TYPE BLINDNESS — three bond CUSIPs inside that 16 count toward an EQUITY position cap; Roth's actual equity holdings number 13 and the union of held equity tickers across both accounts is 19. D-3 CHECK 6 BLOCKS SELLS — there is no `if sig == "BUY"` guard, while CHECK 8 ten lines below states the correct principle explicitly ("block new BUY signals. SELL signals still allowed (to cut losses)"); concentration is a reason to refuse to OPEN, never to refuse to EXIT, and being at max positions is precisely when you most want out. D-4 LATENT — CHECK 7's duplicate-position guard builds `held\_tickers` from the same single-account list, so a BUY on an Individual-only holding (RTX, CBRS, CORN, SND, AG, FTI) would pass it; masked today because CHECK 6 rejects first. ★★ SELF-CORRECTION, THE SECOND IN TWO SESSIONS: I recorded CBRS SELL 6/26 (conf 68 ≥ the 65 SELL gate) as "the positive control KEEP-70 has always lacked." WRONG. `logs\\signals\_2026-06-26.log` reads `Risk: REJECTED | Reason: Too many open positions: 16 >= max 8.` — it cleared its CONFIDENCE gate and CHECK 6 rejected it anyway, under D-3. `\[V]` FROM THE LOG, not from the code path. THE CORRECTED STATEMENT IS THE HEADLINE: THE RISK ENGINE HAS NEVER APPROVED A DIRECTIONAL SIGNAL — 35 directional signals across 54 cohorts, ZERO approvals; the 23 APPROVED rows in today's tally are HOLDs passing through CHECK 2. Note also that the count read 16 on 2026-06-26 and reads 16 today, six weeks and a changed portfolio apart, which is further evidence for D-1. ★★ `analyze\_log.py` CONTRADICTS ITSELF IN THE SAME REPORT — TWELFTH INSTANCE OF THE TOOL-REPORTS-A-VALUE-IT-DID-NOT-COMPUTE CLASS. It filed NVDA under "✅ ACTIONABLE SIGNALS (Risk Engine Approved)" while its own RISK ENGINE OUTCOMES block read `APPROVED 23 / REJECTED 1`, that one rejection being NVDA. Cause: `classify\_directional\_signal` (L220–251) keys on `signal` and `confidence` ONLY, though the risk decision IS parsed at L148 and IS used at L467 — the same dict, in scope, holds the answer. Latent for 1,291 rows because no BUY had ever cleared 70% and the `Risk:` field is a constant for directional rows. Minimal fix: `return "actionable" if s.get("risk") == "APPROVED" else "gate\_cleared\_rejected"`, which produces the DP-3C-l ledger population as a by-product. TWO SMALLER NOTES ON THE SAME FILE: L33–34 duplicate `risk\_engine`'s 70/65 thresholds and L29's own comment admits the hazard — two sources of truth for the gate KEEP-70 measures, so changing `risk\_engine` alone would silently desync the analyzer's tiering AND the near-miss band that defines the registry; and L232's Phase-2 note ("zero BUYs below 60% or SELLs below 55%") STILL HOLDS at 54 cohorts — zero BUYs below 60% in 1,291 rows `\[V]`, a scoping assumption surviving a 10× sample. ★ KEEP-70'S DENOMINATOR IS CLEAN `\[V]` — all 33 registry rows sit in 0.61–0.68, no BUY below 0.60 exists anywhere in the record, and the rejection-reason ordering is confidence-first (8/03 NVDA at 68% with the SAME 16 open positions was rejected for "BUY confidence too low"), so CHECK 6 has never pre-empted the confidence gate for a sub-70 BUY. Today's 72% row is correctly OUT of the registry, which stayed at 33. ★ DIRECTIONAL ROWS USE A SIGN TEST, NOT THE ±3% BAND `\[V]` — SCHD +1.22% YES, NVDA +0.005% YES, CBRS SELL +14.61% NO — which independently confirms why the band-breach identity is HOLD-only. ★★ THE 7/28 COHORT RESOLVED 7/24 = 29.2%, TIED WEAKEST, ON THE HIGHEST DISPERSION IN THE ENTIRE RECORD. sd(pop) 9.09% — above 5/20's 7.62% and 7/22's 7.54%; mean +5d +3.45%; 17 of 24 breached the ±3% band, split 11 UP / 6 DOWN (CBRS +27.1%, MSFT +24.0%, PWR +19.6% against PM −9.6%, AAPL −8.5%). IT IS A 24-ROW ALL-HOLD COHORT WITH ZERO DIRECTIONAL SIGNALS, so accuracy is PURELY the band-breach count and nothing about the generator enters it. ★ THE IDENTITY NOW READS 48/48 EXACT ON THE HOLD POPULATION `\[V]`, with correlation −1.0000 — and on the HOLD population it is not a strong correlation but a DEFINITION, since "Was Claude Right (5d)" IS |return| ≤ 3%, the exact complement of a band breach, leaving zero residual. `\[?]` UNRECONCILED: the record's 7/30 figure of r = −0.9650 exact in 46/46 does not reproduce — my all-rows computation gives −0.9934 and 41/47, HOLD-only gives −1.0000 and 48/48; one of the accuracy definition, the breach threshold or the cohort inclusion rule differs, and this must be reconciled BEFORE E4-2, because if accuracy is definitionally 1 − breach rate on HOLD rows then E4-2's mandatory "report accuracy alongside band-breach count" is reporting one number twice and the safeguard is weaker than it reads. Horizon breach rates refreshed and stable against 7/30: +5d 45.5% (median |move| 2.64%), +10d 55.4% (3.51%), +20d 66.5% (5.15%). Also resolved today: 7/21 at +10d (13 breaches, mean +3.17%, sd 6.93%) and 7/07 at +20d (14 breaches, mean +4.92%, sd 8.14%). ★ E4-1 BASELINE MEASURED FOR FREE — DQ moved 21 HIGH / 3 MEDIUM to 19 / 5 with NO treatment and the era unchanged (NTR and GLD both HIGH → MEDIUM in one session). E4-1 reads DQ-mix shift with T-C names as the control, so ±2 names of movement is now a MEASURED no-treatment noise floor, and the endpoint should state a minimum shift size. EDGAR's cost premium also reads cleanly: input tokens 37,107 today versus 46,545 on 8/03 = a 9,438-token premium across 15 covered names, and that was the DEGRADED run missing eight statements blocks; session cost $0.2628 versus $0.32. ★ `\[?]` CLOSED FROM THE RECORD: the doubled 2026-07-07 API bill (\~$0.53 against a \~$0.27 baseline) is explained by the 7/07 entry itself — the 09:45 run skipped the seed, produced a cold start, was archived as `signals\_2026-07-07\_run1\_coldstart.log` and NOTHING WAS PASTED; the canonical cohort came from the 10:18 re-run. The master carries exactly 24 rows for 7/07 with no duplicate tickers `\[V]`. My "two runs that day" hypothesis was right; my attribution to the parser break was wrong. ★ SHEET1 IDENTIFIED, CORRECTING AN OPERATOR READING: `Sheet1` in `logs\\claude\_equity\_bot\_tracker.xlsx` is NOT a manually-maintained tab. Direct inspection reads row 1 "Guardrail Compression Trace — cumulative +5d hit rate by confidence band" and row 2 "Auto-generated by guardrail\_trace.py · source: Signals tab · as of 2026-07-20. The 50-59% band must lead 60-69%", with 43 cohort rows stopping at 7/20, a `lead gap (pt)` column and one embedded chart image. It is the RETIRED guardrail artifact, frozen 12 sessions ago, stating a retired criterion in live-criterion grammar inside the workbook every harness reads. The manually-maintained sheet in the master is `Signals` (the paste plus closing prices); `Dashboard` and `Cohort Analysis` are formula-driven. Master tabs are Dashboard / Signals / Cohort Analysis / Sheet1 / How to Use; the generated copy is Dashboard / Signals / Near-Miss BUYs / Cohort Analysis / Monitor Strip / How to Use — the purge drops Sheet1 from the COPY every run, which is why the notice keeps firing. ★ RECORD DEFECT FOUND WHILE SPLICING: `docs\\analyst\_notes.md` carried TWO Upcoming blocks — the 7/29 multi-line version was never removed when the 7/30 single-line version was appended. Superseded in this splice by a single current block. ★ MONITOR STRIP UNCHANGED WHERE IT SHOULD BE: WS2/G1 1 post-deploy episode in 21 sessions (GM still zero, 22 sessions since its last pre-deploy episode); H4 6/13 = 46%, 14 total; KEEP-70 40.6% (13/32); WS1/G2 net −1. STILL STALE AND NOW FIVE OR MORE SESSIONS OLD: the H4 card prints the `n ≥ 10` bar superseded 7/28 by `n ≥ 12 on two consecutive readings`, and the WMT clock still prints "last episode 2026-07-24" against a ledger correctly reading the coalesced 7/23. ★★ DP-3C-l — RULED, RW 2026-08-04 — GATE-CLEARED DIRECTIONAL LEDGER. QUESTION: where do directional signals that clear their OWN confidence gate belong, and what is read from them? RULING: a separate GATE-CLEARED ledger is opened, DESCRIPTIVE ONLY — it does not modify KEEP-70, does not gate any decision, and carries no pass/fail standard. MEMBERSHIP: any BUY at conf ≥ 70 or SELL at conf ≥ 65, REGARDLESS OF RISK-ENGINE DISPOSITION, applied retroactively across the full record. Membership is deliberately independent of the `Decision` field so that a future change to `MAX\_OPEN\_POSITIONS` — ruled a Phase-2 artifact the same day — cannot silently redefine the population; had membership keyed on "rejected", the definition would have changed the day the cap moved. READ: the existing +5d SIGN TEST (BUY right if return > 0, SELL right if return < 0), with the risk-engine `Decision` and its verbatim reason reported alongside each row; the disposition is RECORDED, NOT STRATIFIED ON, because at n=2 stratifying produces two arms of one. STANDARD: NONE. EXIT DISPOSITION, PRE-COMMITTED: INSUFFICIENT TEST CONDITIONS. Measured supply is 2 events in 54 cohorts = 0.037/session, so 20 rows require \~540 sessions (\~2 years); stressed against the wide error bars on a two-event Poisson estimate, even TRIPLE the observed rate needs \~180 sessions (\~8.6 months), still past any plausible 3-C exit, so the conclusion survives the uncertainty. Kickoff §5's binding rule applies — an endpoint whose event supply cannot deliver a read inside the phase is entered as a STATED LIMITATION, not pre-registered and discovered later. THE BAR IS NOT LOWERED, AND THIS IS RECORDED WHILE IT IS STILL A FORECAST RATHER THAN A CONCESSION. This is the FIRST time in the project a starved endpoint has been identified BEFORE the data arrived rather than at the exit review; G1 and G2 both died of exactly this and neither was seen coming. EXPLICITLY REJECTED, WITH REASONS: (A) folding either row into KEEP-70 — neither was rejected by the CONFIDENCE gate, and admitting a 72% row would require widening the registry's 60–69 band mid-flight; (C) excluding both entirely — that discards the only two rows bearing on whether the gate's ACCEPTED side pays, and contradicts the 7/30 precedent of recording counterfactuals so their cost is visible rather than invisible; (D) attaching a complement clause to KEEP-70's criterion ("the gate is supported when rejected BUYs pay <50% AND cleared BUYs pay more than rejected ones") — intellectually the right question and THE DANGEROUS MOVE, because it would convert a currently READABLE criterion (supported, 40.6%, n=32) into an unreadable one by attaching a clause needing \~2 years of supply, i.e. importing the G1/G2 failure mode into a gate that works. KEEP-70 IS UNCHANGED AND REMAINS SUPPORTED at 13/32 = 40.6%, registry 33, denominator verified uncontaminated (all rows 0.61–0.68; rejection ordering is confidence-first). CONTENTS AT RULING: CBRS SELL 2026-06-26, conf 68, REJECTED (position count), +5d +14.61% → NO; NVDA BUY 2026-08-04, conf 72, REJECTED (position count), +5d resolves 2026-08-11 → pending. IMPLEMENTATION: no workbook tab — the ledger lives in `docs\\analyst\_notes.md` and falls out of the `analyze\_log.py` fix as its third bucket (`gate\_cleared\_rejected`); no new file, no new harness. NOTED AND NOT ACTED ON PER "SIGN AS WRITTEN": the label `DP-3C-l` uses a lowercase L that renders nearly identically to a 1 in most fonts, beside an existing DP-1…DP-10 series; the collision hazard is recorded here rather than renamed. RECORDED IN FAIRNESS: this ruling makes the phase look WORSE, converting a would-be finding into a stated limitation, and the direction therefore runs against convenience — the same test applied to DP-8 and DP-9 on 7/30. IT DOES NOT RESOLVE whether KEEP-70's evidentiary basis is one-sided: KEEP-70 has only ever measured the rejected side, and this ledger documents why that cannot be fixed inside this phase rather than fixing it. If the 70% gate is ever revisited, the asymmetry belongs in the memo explicitly rather than left implicit.

## 8/05 (Phase 3-C — SECOND CONTROL COHORT, EDGAR FLAG DELIBERATELY UNSET) — ★★ E4-2 WAS FOUND TO BE MEASURING REALISED VOLATILITY RATHER THAN EDGAR, AND IT WAS FOUND BEFORE THE CLOCK STARTED RATHER THAN AT THE READ; THE BAND-BREACH IDENTITY IS PROVEN DEFINITIONAL AND THE `r = −0.9650` FIGURE IS RETIRED AS A PROXY THAT DOES NOT REPRODUCE; AND THE 8/04 ENTRY'S Px@signal CLAIM IS CORRECTED FROM THE MASTER'S OWN FORMULA. Cross-check 24/24 — `signals\_2026-08-05.log` ↔ `logs\\claude\_equity\_bot\_tracker.xlsx` reconcile clean via `log\_tracker\_crosscheck.py`, and Px@signal was independently reproduced from the log JSON at full sub-cent precision, 24/24 byte-exact; era `A-S1D1-B1` with ZERO `E\[…]` tags, no `\[EDGAR] prefetch` line and no budget warning; 22 HOLD + 2 BUY; DQ 16 HIGH / 8 MEDIUM / 0 LOW; conf mean 54.6, median 57.5, sd(pop) 11.41, range 32–74; totals 1,315 rows, 55 cohorts; recalc 0 errors on 8,542 formulas; `paste\_today.tsv` 24 rows with real Accounts and no "Unknown"; no premature K:N on today's rows; RESOLUTIONS COMPLETE AT ALL THREE HORIZONS WITH ZERO UNRESOLVED-BUT-DUE (first blank +5d is 7/30, due 8/06; first blank +10d is 7/23; first blank +20d is 7/09). The flag was left unset by decision, not omission — DP-3C-k holds and N-1 is unfixed, so this is the second cohort of the recorded control window. Run executed 09:52:59–09:58:40 CST, twenty-three minutes past the 9:30 canonical; recorded because 8/04's much larger offset turned out to matter (see the Px@signal correction below).

★★ DP-3C-m — RULED, RW 2026-08-05 — CONSECUTIVE SAME-TICKER GATE-CLEARED ROWS COALESCE INTO ONE EPISODE. QUESTION: DP-3C-l opened the GATE-CLEARED ledger with per-row membership and no coalescing rule, and one session later NVDA supplied a second row. Are those two rows two events? RULING: NO. Consecutive sessions on the same ticker whose directional signal is unbroken and continues to clear its own gate constitute ONE episode, DATED AT FIRST CLEARANCE, with the confidence path across the episode recorded and the +5d outcome measured from the first-clearance row. An episode ENDS when the ticker reverts to HOLD, flips direction, or falls below its gate for at least one session; a later re-clearance opens a NEW episode. MEMBERSHIP IS OTHERWISE UNCHANGED — BUY at conf ≥ 70 or SELL at conf ≥ 65, regardless of risk-engine disposition, applied retroactively. PRECEDENT IS DP-6, which moved G1 from cohorts to coalesced episodes on the ground that a period carrying no independent information should not be counted as though it did; the same argument applies exactly here. THE EVIDENCE IS FROM THE MASTER, NOT INFERRED `\[V]`: NVDA reads HOLD 55 (7/27), 49, 46, 49, 50 (7/31), then BUY 68 (8/03), BUY 72 (8/04), BUY 74 (8/05) — one regime change on 8/03 followed by a strengthening stance, not three independent draws. The 8/04 and 8/05 rows share four of their five resolution days (+5d 8/11 and 8/12), so their outcomes will agree by construction and n=2 carries roughly n≈1 of information. LEDGER RESTATED UNDER THE RULING: 3 rows become 2 EPISODES — (i) CBRS SELL 2026-06-26, conf 68, single session, REJECTED on position count, +5d +14.61% → NO; (ii) NVDA BUY opening 2026-08-04 at conf 72, path 72 → 74, REJECTED on position count both sessions, +5d measured from 8/04 and resolving 2026-08-11. NOTE THE BOUNDARY, WHICH IS NOT ARBITRARY: the NVDA BUY run begins 8/03 but the episode begins 8/04, because membership keys on GATE CLEARANCE and 8/03's 68 did not clear. The 8/03 row therefore belongs to the KEEP-70 near-miss registry instead, and a single continuous three-day BUY run contributes exactly one row to KEEP-70 and one episode to the gate-cleared ledger with no double-count. SUPPLY RECOMPUTED: row-count basis 3/55 = 0.0545/session; COALESCED basis 2/55 = 0.0364/session. BOTH SIT INSIDE THE ×3 STRESS BAND (0.111/session) THAT DP-3C-l PRE-COMMITTED AGAINST ON 8/04, so the pre-committed exit disposition of INSUFFICIENT TEST CONDITIONS STANDS WITHOUT REVISION and is strengthened rather than weakened by the update. RECORDED IN FAIRNESS, TWICE OVER: first, the ruling REDUCES the ledger and makes a starved endpoint more starved, so the direction runs against convenience — the same test applied to DP-8/DP-9 on 7/30 and to DP-3C-l itself; second, and more uncomfortably, THE SAME SERIAL-DEPENDENCE PROBLEM APPLIES TO KEEP-70 AND IS DELIBERATELY LEFT UNFIXED. KEEP-70's registry carries 25 of its 32 resolved rows on NVDA `\[V]` = 78.1%, many of them consecutive-session repeats of one stance, and DP-3C-m DOES NOT TOUCH IT. The reason is the hazard DP-3C-l rejected as option (D): KEEP-70 is a currently READABLE criterion at n=32 and attaching a coalescing rule mid-flight would redefine its denominator and could move a supported gate. This is entered as a KNOWN LIMITATION of KEEP-70's evidence base, not as a fixed problem, and it belongs in the memo explicitly if the 70% gate is ever revisited.

★★ DP-3C-n — RULED, RW 2026-08-05 — E4-2 STRATIFIES ON VOLATILITY, AND ITS MANDATORY REPORTING IS REPLACED BECAUSE THE EXISTING SAFEGUARD IS VACUOUS. QUESTION: given that HOLD accuracy is definitionally the complement of a band breach, what is E4-2 actually measuring? THE PROBLEM, STATED PLAINLY. `Phase3C\_E4\_Endpoint\_PreRegistration\_v1.md` §3 fixes E4-2's population as HOLD ROWS ONLY and its read as ACCURACY AT +5d, with ADJACENT defined as a covered name carrying an 8-K or Form 4 inside a five-trading-day window and COVERED-QUIET as a covered name without one. Substituting the identity, E4-2 asks whether names that just filed an 8-K or a Form 4 cross the ±3% band LESS OFTEN than covered names that did not. 8-Ks are earnings and material events; Form 4 clusters follow corporate events; those windows carry ELEVATED REALISED VOLATILITY BY CONSTRUCTION. E4-2 AS PRE-REGISTERED THEREFORE HAS A MECHANICALLY EXPECTED NEGATIVE SIGN THAT IS INDEPENDENT OF ANY TREATMENT EFFECT, and its pre-committed NEGATIVE disposition would fire on a volatility artifact and enter the permanent record as evidence that EDGAR HURTS. THIS IS THE SAME TRAP THE PRE-REGISTRATION ITSELF CAUGHT ONCE AND HALF-FIXED: §3 correctly rejected a pre/post read because dispersion varies ACROSS TIME and moved to a within-cohort design, which holds the MARKET constant — but not NAME-LEVEL EVENT VOLATILITY, and event volatility is precisely what defines the strata. The project has diagnosed this exact confound before: Q4-R found DQ's raw +15.5pt accuracy gap collapse to +0.5pt within-ticker at constant volatility, because MEDIUM-DQ names simply move about twice as much. RULING, IN THREE PARTS. (1) PRIMARY READ BECOMES A WITHIN-TICKER PAIRED DIFFERENCE: for each covered ticker supplying at least 3 resolved rows in EACH arm, compute its own ADJACENT-minus-COVERED-QUIET breach-rate difference at +5d, then pool the per-ticker differences. Same instrument in both arms holds volatility exactly constant, which is what Q4-R's decisive control did across 9 tickers. (2) FALLBACK FOR TICKERS THAT CANNOT SUPPLY BOTH ARMS: pool them by VOLATILITY TIER, tiers assigned from each ticker's own historical median |+5d move| computed from the master and FROZEN BEFORE THE FIRST READ. The count of tickers qualifying for the primary read and the count falling to the fallback are both reported. (3) MANDATORY REPORTING REPLACED: the existing safeguard — "every accuracy figure is reported with its band-breach count" — is VACUOUS on a HOLD-only population because it reports one number twice. It is replaced by MEAN SIGNED RETURN and sd BY STRATUM, which are NOT determined by accuracy, plus the UP/DOWN BREACH SPLIT. The raw unadjusted ADJACENT-vs-QUIET gap continues to be reported but as a DESCRIPTIVE CONTROL that is EXPECTED NEGATIVE on volatility grounds alone, so that a figure like −8pt cannot later be read as a treatment effect. THE BAR DOES NOT MOVE, AND THIS IS THE PART TO WATCH: the ≥ 5pt magnitude, the leave-one-cohort-out condition, the drop-largest-ticker condition and n ≥ 150 resolved ADJACENT rows ALL CARRY OVER UNCHANGED. Only the comparison unit and the reporting set change. Amending an endpoint is exactly where a bar slips quietly, so it is stated here that none of the four acceptance conditions was touched. AN INCIDENTAL BENEFIT, RECORDED BECAUSE IT LOOKS TOO CONVENIENT NOT TO NAME: the within-ticker design also disarms §2's concentration warning. WMT supplies 24% of all Form 4 volume and may be ADJACENT on nearly every session; a name that is never QUIET contributes NOTHING to a within-ticker read, so the fix for the volatility confound is also the fix for the single-name footprint that made G2 unscoreable. TIMING IS THE REASON THIS IS RULED NOW rather than later — the E4 clock has not started, so amending costs nothing, whereas the same amendment after the first read would be moving a criterion with data in view. This is the DP-3C-g argument applied a second time. DIRECTION: the ruling makes the phase HARDER, converting a ready endpoint into one requiring redesign and a frozen vol-tier table before go-live, so it runs against convenience.

★★ THE BAND-BREACH `\[?]` IS CLOSED — AND CLOSED AS A DEFINITION, NOT AS A CORRELATION. The 7/30 entry recorded the dispersion artifact as an identity on the strength of `corr(HOLD band-breach count, cohort accuracy) = −0.9654` exact in 46/46, refreshed 7/31 to −0.9650 across 47, and the 8/04 entry flagged `\[?]` that neither figure reproduced. IT IS NOW SETTLED BY READING THE MASTER'S OWN FORMULA RATHER THAN BY COMPUTING ANOTHER CORRELATION `\[V]`: column N is `=IF(H="","",IF(D="HOLD",IF(ABS(K)<0.03,"YES","NO"),…))` and column K is `(H−G)/G`, so for a HOLD row "Was Claude Right (5d)" IS `|Return+5d| < 3%`, the exact complement of a band breach. Tested directly across every resolved HOLD row in the record: `(N=="YES") ⟺ (|ret5| < 3%)` holds 1,160 OF 1,160. On the HOLD population, accuracy and 1 − breach RATE are THE SAME NUMBER, and the correlation between them is `r = −1.000000` exactly, by construction rather than by measurement. Breach COUNT against accuracy reads −0.9833, and the ONLY thing degrading it from −1 is varying HOLD-cohort size (sizes observed: 20 twice, 21 once, 22 three times, 23 twenty-three times, 24 twenty-one times). All-rows count-versus-accuracy reads −0.9629 with the identity `accuracy = (n − breaches − directional misses)/n` exact in 49 of 50 resolved cohorts. THE RECORD'S −0.9650 DOES NOT REPRODUCE UNDER ANY INCLUSION RULE TESTED: first-46 cohorts −0.9606, first-47 −0.9603, breach-rate basis −0.9886, strict `> 0.03` threshold −0.9629. DISPOSITION: THE CORRELATION FIGURE IS RETIRED RATHER THAN CHASED. It was always a proxy for something provable directly from the spreadsheet formula, the residual is second-order, and no conclusion in the record depends on which value is right — the 7/30 and 7/31 findings stand exactly as written, on stronger ground than they were stated. THE 7/30 AND 7/31 ENTRIES ARE NOT EDITED, per the standing rule that historical entries describe what was believed when written. Any future citation should read: on the HOLD population the identity is definitional, verified 1,160/1,160 on 2026-08-05; the correlation coefficients were an early proxy and are withdrawn.

★★ SELF-CORRECTION — THE 8/04 ENTRY'S Px@signal CLAIM IS WRONG AS WRITTEN, AND MY OWN FRAMING OF THE PROBLEM WAS ALSO WRONG. The 8/04 entry records that run's 11:08 CST execution as producing a Px@signal "roughly 1.5 hours later than every other cohort — immaterial to +Nd returns (closing prices)". `\[V]` FROM THE MASTER: column K reads `=IF(H="","",(H−G)/G)` where G is Price at Signal, a QUOTE, and H is the +5d CLOSE. RETURNS IN THIS PROJECT ARE QUOTE-TO-CLOSE, NOT CLOSE-TO-CLOSE. The parenthetical mis-describes the metric and the conclusion of immateriality does not follow from it. BUT THE CORRECTION CUTS BOTH WAYS AND MY OWN FIRST READING WAS ALSO WRONG: I raised this as a possible data-integrity problem, and it is not one. A quote taken at any hour is UNBIASED for a close five sessions later, so 8/04 is not incorrect — it is NOISIER IN A WAY NO OTHER COHORT IS. The effect is VARIANCE, NOT BIAS. SIZED RATHER THAN ASSERTED `\[V]`: of 1,160 resolved HOLD rows, 2.41% sit within 0.10pp of the ±3% line, 12.76% within 0.50pp (≈3.1 rows per 24-row cohort) and 26.03% within 1.00pp (≈6.3 rows); and measured intraday drift on 8/04 from the 11:08 quote to that day's close averaged 1.00pp with a median of 0.69pp, 17 of 24 rows moving at least 0.50pp and CBRS moving 4.44%. That drift spans about 4.5 hours where the displacement of concern spans 1.5, so the honest order of magnitude is ONE TO THREE OF 8/04's TWENTY-FOUR ROWS landing on the other side of the ±3% line than they would have at the canonical time — four to twelve accuracy points on that cohort. HANDLING: 8/04's PRICES ARE NOT RESTATED. Backfilling a 9:30 quote that was never taken is manufacturing data, which is worse than the defect. The cohort is TAGGED with its Px@signal timestamp and carries the caveat; today's cohort is tagged likewise at +23 minutes, materially smaller. THE POINT THAT OUTLIVES 8/04: every cohort's denominator is a mid-session quote taken at a time that has drifted across the record, so THE ±3% BAND'S RESOLUTION IS BOUNDED BY QUOTE-TIMING VARIANCE. This is a SECOND AND INDEPENDENT argument for the parked Q4-2 volatility-scaled secondary metric, distinct from the dispersion argument, and it is recorded as a separate line of reasoning rather than folded into the existing one. THE ±3% BAND IS NOT RE-BASELINED AND NO PRIOR CONCLUSION MOVES.

★ 7/29 COHORT RESOLVED 9/24 = 37.5% — AND IT IS THE CLEANEST INSTANCE OF THE IDENTITY YET RECORDED. Mean +5d +4.08%, dispersion (sd, population) 8.64%, 12 of 24 names up, median |move| 4.47%; 15 HOLD band-breaches split 10 UP / 5 DOWN; ZERO directional signals in the cohort, so accuracy is `(24 − 15)/24` and NOTHING ABOUT THE GENERATOR ENTERS IT. Biggest movers MSFT +23.4%, CBRS +19.9%, PWR +19.5%, AG +16.4%, NVDA +13.7% — the +5d window (7/30–8/05) spans the post-FOMC rally, so a rising tape marked ten HOLDs wrong upward. SELF-CORRECTION WITHIN THIS SESSION: I first described 37.5% as the second-weakest cohort in the record. `\[V]` IT IS TIED FIFTH-WEAKEST at +5d — 6/03 22.7%, then 6/16, 7/22 and 7/28 all at 29.2%, then 5/19, 5/20 and 7/29 tied at 37.5%. What IS second is the DISPERSION: sd 8.64%, behind only 7/28's 9.09%. Two rankings were conflated and the wrong one was stated first. THE 7/29 PRE-COMMITMENT IS VINDICATED: that entry ran the Fed-day cohort deliberately rather than skipping it, on the ground that conditioning on expected calm would bias every cohort statistic in the project. The cohort duly came in weak, and because the reasoning was written down BEFORE the number it reads as dispersion rather than as degradation — which is the entire purpose of writing it down first. A CAUSAL NOTE WORTH KEEPING: NVDA rose 13.7% inside 7/29's resolution window, and that same tape is what drove NVDA's confidence from 50 on 7/31 to 68, 72 and 74. THE GENERATOR'S ONLY GATE-CLEARING BUY IS DOWNSTREAM OF THE SAME MOVE THAT MARKED TEN HOLDS WRONG UPWARD — one tape, two opposite-signed readings on the same instrument.

★ 7/22 AT +10d = 12/24 = 50.0% and 7/08 AT +20d = 10/24 = 41.7%. 7/22: mean +1.44%, sd 7.45%, 15 of 24 up, 12 breaches split 6 UP / 6 DOWN, zero directional misses — BOTH of its BUYs went positive over the longer window, including GLD, which had LOST 2.63% at +5d. That cohort read 29.2% at +5d and 50.0% at +10d on a FALLING breach count, which is the identity again and a useful counterexample to the assumption that the +10d and +20d series only degrade. 7/08: mean +4.40%, sd 8.17%, 19 of 24 up, 14 breaches split 12 UP / 2 DOWN, movers MSFT +27.5%, GM +18.0%, SND −15.2%, CBRS +14.5%, RTX +11.8% — well above 7/01's 25.0% at the same horizon. HORIZON BREACH RATES REFRESHED AND STABLE `\[V]`: +5d 532/1,160 = 45.9% (median |move| 2.66%), +10d 577/1,042 = 55.4% (3.51%), +20d 538/812 = 66.3% (5.12%), against 45.5 / 55.4 / 66.5 on 8/04.

★★ E4-1's CONTROL ARM IS ALREADY MOVING, AND ITS OWN INVALIDATION RULE IS FIRING IN THE BASELINE. DQ mix runs 21 HIGH / 3 MEDIUM (8/03, treated) → 19/5 (8/04, untreated) → 16/8 (8/05, untreated) `\[V]`. Named movers: GLD and NTR on 8/04; RTX, VTI and WMT on 8/05. TWO THINGS THE AGGREGATE HID. First, ALL FIVE MOVES ARE ONE-WAY (HIGH → MEDIUM) AND NONE HAS REVERTED — random noise reverts, and E4-1 reads a pre/post DQ MIX, so a monotone pre-era drift would be read as a treatment effect at the post-era read. Second, TWO OF THE FIVE MOVERS — NTR AND VTI — ARE T-C DARK NAMES, which are E4-1's designated internal control, and the endpoint pre-commits that "a shift in T-C names invalidates the read." THAT RULE IS FIRING WITH NO TREATMENT APPLIED. E4-1 needs BOTH a stated minimum shift size AND a T-C tolerance, and both must be derived from measured control variance, which requires several more control cohorts before a number can be set honestly. The control window is earning its keep.

★★ `analyze\_log.py` REPRODUCED ITS 8/04 DEFECT AND EXPOSED A SECOND VARIANT — THIRTEENTH INSTANCE OF THE TOOL-REPORTS-A-VALUE-IT-DID-NOT-COMPUTE CLASS, AND NO LONGER LATENT. Three mutually inconsistent statements in one report `\[V]`: the CONFIDENCE STATS block prints `>= 70% (actionable): 2`, which counts MSFT, A HOLD AT 70, under a label with no signal-type guard; the ACTIONABLE SIGNALS section files NVDA under "Risk Engine Approved" when NVDA was REJECTED; and the RISK ENGINE OUTCOMES block correctly reads APPROVED 22 / REJECTED 2. THE TRUE COUNT OF RISK-APPROVED DIRECTIONAL SIGNALS TODAY IS ZERO. The word "actionable" carries three meanings in a single report. ESCALATION: this is the SECOND CONSECUTIVE SESSION on which a false ACTIONABLE line has been appended to `logs\\summary\_history.txt`, which is a durable artifact that nothing reconciles against the master — the defect has moved from latent to actively contaminating the record. The change-order 5b one-liner fixes the section but NOT the CONFIDENCE STATS label, which is a separate string. NOTE ALSO THAT `signal\_scan.py` ALREADY CARRIES THE GUARD 5b NEEDS: its cohort profile prints "conf 60-69: 8 row(s), of which DIRECTIONAL (true KEEP-70 near-misses): GLD (a HOLD in that band is not a near-miss BUY — do not pool them)". Replicate that discipline in the `gate\_cleared\_rejected` bucket or MSFT-at-70 lands in the DP-3C-l ledger.

★ RISK ENGINE — D-1 AND D-2 CONFIRMED A THIRD TIME; D-3 UNTESTED TODAY. NVDA's BUY at 74 was rejected on `Too many open positions: 16 >= max 8`, with the same run's portfolio overview showing Roth IRA 16, Individual 20, 36 total `\[V]`. The engine's 16 is Roth's raw count exactly — three data points now, 2026-06-26, 08-04 and 08-05. Roth's 16 includes three bond CUSIPs (254673Q90, 14042THN0, 61768U4F1), so its actual equity holdings number 13, and the union of held equity tickers across both accounts is 19, matching the run's own "19 held + 5 scouting" line. D-3 produced no observable effect today because no SELL was emitted; that is not evidence either way. DIRECTIONAL SCARCITY REFRESHED `\[V]`: 37 directional signals in 1,315 rows (36 BUY, 1 SELL), of which NVDA is 28 = 75.7% single-name, and RISK-ENGINE APPROVALS REMAIN ZERO across 55 cohorts.

★ MONITOR STRIP — BOTH 8/04 PATCHES LANDED AND VERIFY, AND ONE NEW STALE-CRITERION FINDING. The WMT clock now reads "last episode 2026-07-23, 9 session(s) ago" — the "2026-07-24" date defect, outstanding since 7/30, is FIXED, and 9 trading days is confirmed by independent computation. The H4 card now prints the correct `n ≥ 12 resolved AND hit ≥ 60% on 2 consecutive readings` bar, retiring the superseded `n ≥ 10` string. All four strip readings reproduce exactly from the master `\[V]`: registry 34, KEEP-70 13/32 = 40.6%, H4 6/13 = 46.2% with 14 total, WMT 1 post-deploy episode in 22 sessions. NEW FINDING — THE STRIP STATES A LIVE CRITERION FOR A DESCOPED GATE. Its WS1/G2 row prints a Bar of "net ≥ 0 \& confirm > discount, ≥5 cohorts" and a State of "negative". G2 has carried DESCOPE since 2026-07-31, and that ruling found EXPLICITLY that a negative VERDICT was NOT supported, failing two of five conditions. The strip's state word therefore contradicts the signed disposition on the gate whose disposition was the most carefully reasoned in the phase. Same class as the `run\_daily\_review.bat` banner items and squarely inside `retired\_criteria\_audit.py`'s known blind spot — criteria that were live when written and disposed since. Relabel to DESCOPED with the re-open triggers T-G2-a/b/c, not a bar and a state.

★ `signal\_scan.py` — THE BLEND-CHANNEL CHECK FIRED FOR THE SECOND TIME AND HAS NOW FIRED BOTH WAYS. `\[FAIL] D.op == B.blend\_op 23/24`, NVDA op 74 versus blend\_op 75. This is CORRECT BEHAVIOUR with wording that predates the DESCOPE, as recorded 8/03, but the two occurrences differ in a way worth keeping: on 8/03 the divergence WAS load-bearing (op 68 versus blend\_op 70 — reading the blend channel would have APPROVED a BUY the risk engine rejected), whereas today it is not (74 and 75 both clear the 70% gate, and the rejection was on position count). Rephrase to informational. TWO STALE STRINGS IN THE SAME TOOL: its RUN INTEGRITY header cites `Daily\_Workflow\_v5\_3` section 4 when v6.0 is current, and its era line reads "pre-EDGAR (3-B)", which is the same phase-token string class as `main.py`.

★ CHANNELS AND D1 — CLEAN, AND ONE FINDING FIRMS UP. D1 reconciles 24/24 against the floor-aware rule `op = raw if raw < FLOOR else max(FLOOR, raw − damp)` with FLOOR 35, THETA 5.0% and damp `min(CAP, round((|trail| − THETA) × K))` at K = 1.5 and CAP 15 `\[V]`. Only two rows breached THETA adversely — AAPL (trail5d −6.69%, raw 50 → op 47, damp 3) and NTR (−5.50%, raw 43 → op 42, damp 1) — and both reconcile exactly, with no repeat of the apparent mismatch raised 7/30 and resolved at the 3-B closeout §4.4. Damping remains ONE-DIRECTIONAL as DP-8 ruled: AG +12.52%, NVDA +12.43%, MSFT +8.84% and QQQ +5.76% all damp 0. THE `confidence\_blend` SEMANTICS FINDING FIRMS FROM n=3 TO n=5: AAPL and NTR are the two rows today where blend and blend\_op differ, and in both the JSON field `confidence\_blend` tracks blend\_op (post-damping), 0 of 2 tracking blend. The field named for the blend channel carries the value AFTER damping, on five discriminating rows across three sessions.

★ WS2 / G1 — UNCHANGED, 1 INDEPENDENT POST-DEPLOY EPISODE OF 4, NOW 22 SESSIONS. WMT trail5d +1.30% and GM +0.48%, both favourable, neither adverse, no episode; GM still has none post-deploy. RECORDED DELIBERATELY AND NOT COUNTED, per the 7/30 precedent: AAPL at −6.69% and NTR at −5.50% would both qualify under DP-9's rejected widened universe, taking G1 from 1 to 3 on today's data alone. The cost of holding the pre-registered definition stays visible in the record rather than invisible.

★ KEEP-70 AND H4. KEEP-70 UNCHANGED AND SUPPORTED at 13/32 = 40.6%; the registry grows 33 → 34 with GLD's BUY at conf 62, whose +5d resolves 2026-08-12. Denominator verified uncontaminated `\[V]` — all 34 rows sit in 0.61–0.68, no BUY below 0.60 exists anywhere in the record, NVDA's 74 is correctly OUT, and by ticker the registry reads NVDA 26 / GLD 4 / VTI 3 / SCHD 1. H4 UNCHANGED AT 6/13 = 46.2%, 14 total, AND THIS IS NOT A FIFTH CONSECUTIVE DECLINE — GLD's new near-miss carries MEDIUM data quality, so H4's HIGH-DQ denominator did not move. STAYS DEMOTED; no DQ-conditional design work.

★ SMALLER ITEMS. The phase token still reads `\[PHASE 3-B DRY RUN]` on every signal line, with the banner and footer to match, so the durable record of the 3-C control window is stamped 3-B; E4-1 is unaffected because it discriminates on the JSON `prompt\_variant`, but any tool selecting by phase bracket will mis-bucket 8/04 and 8/05, and change-order steps 3 and 4 must land before step 7 or the parsers silently return zero. Workflow §4 documents "\~7 sector ETF(s)" for the WS1 blend context while the live run emits 8 (XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLY) — same class as the 15/24-versus-19/24 prefetch item already carried for v6.0.1. Two names returned no news (NTR, SND) and both carry MEDIUM DQ. Session cost $0.2675 on 37,065 input / 10,418 output tokens, against 37,107 input and $0.2628 on 8/04 — the control-run token baseline is stable across two sessions, which firms up the \~9,438-token EDGAR premium measured on 8/03. `ticker\_suggester.py` ran at 09:58:18–09:58:40 for 770 in / 1,178 out and remains excluded from `analyze\_log`'s cost line.

## 8/06 (Phase 3-C — THIRD CONTROL COHORT, EDGAR FLAG DELIBERATELY UNSET) — ★★ THE ±3% BAND IS BREACHED BY TWO INDEPENDENT MECHANISMS AND THE RECORD HAS ONLY EVER NAMED ONE; THERE IS NO "WAS CLAUDE RIGHT" COLUMN AT +10d OR +20d, SO ACCURACY AT THOSE HORIZONS HAS NEVER BEEN ANYTHING BUT THE BREACH COUNT RESTATED; AND `risk\_engine.py` READ AT SOURCE CONFIRMS THE CHECK-6 COUNTERFACTUAL AND SURFACES THREE FURTHER DEFECTS. Cross-check 24/24 — `signals\_2026-08-06.log` ↔ `logs\\claude\_equity\_bot\_tracker.xlsx` reconcile clean on signal, confidence, data quality and Px@signal at full sub-cent precision. RECORDED AS A GAP IN THE EVIDENCE TRAIL, NOT A PASS BY ANOTHER ROUTE: `log\_tracker\_crosscheck.py` output was NOT in the supplied set — only `signal\_scan\_2026-08-06.md` — so today's 24/24 was reproduced independently from the log JSON against the master rather than by the harness of record. G4 requires the cross-check STREAK, so run the harness on 8/06 before the streak is cited at exit. Era `A-S1D1-B1` with ZERO `E\[…]` tags, no `\[EDGAR] prefetch` line and no budget warning; 22 HOLD + 2 BUY; DQ 18 HIGH / 6 MEDIUM / 0 LOW; conf mean 55.0, median 58.5, sd(pop) 11.56, range 32–72; totals 1,339 rows, 56 cohorts; recalc 0 errors on 8,542 formulas; accounts Roth IRA 7 / Individual 6 / both 6 / Scout 5 with no "Unknown"; no premature K:N; D1 reconciles 24/24 against the floor-aware rule; RESOLUTIONS COMPLETE AT ALL THREE HORIZONS WITH ZERO UNRESOLVED-BUT-DUE (first blanks 7/31, 7/24, 7/10, none of them due). The report copy `tracker\_with\_registry.xlsx` was supplied and reads 18.0% blank in K:N — pending rows only, so the open-in-Excel step was followed; it was OBSERVED ONLY AND NOT USED AS AN INPUT, per §6. Master tabs remain Dashboard / Signals / Cohort Analysis / Sheet1 / How to Use, Sheet1 retained by the 8/04 ruling. Run window 10:09:05–10:14:26 CST, THIRTY-NINE MINUTES PAST THE 9:30 CANONICAL — the third consecutive off-canonical run after 8/04 (+98 min) and 8/05 (+23 min), which given yesterday's Px@signal finding is now a PATTERN RATHER THAN AN INCIDENT and needs each cohort's Px@signal timestamp tagged.

★★ THE BREACH COUNT HAS TWO DRIVERS — DISPERSION *AND* COHORT DRIFT — AND EVERY PRIOR ENTRY NAMED ONLY THE FIRST. The 7/29 and 7/30 entries and closeout memo §4.1 attribute weak cohorts to MARKET DISPERSION. Today's resolution forces a refinement, and it is a refinement of the mechanism rather than a reversal of the conclusion. 7/30 RESOLVED 10/24 = 41.7% ON THE LOWEST DISPERSION OF THE RECENT RUN: reading 7/28, 7/29, 7/30 in sequence, accuracy runs 29.2% → 37.5% → 41.7% while sd(pop) runs 9.09% → 8.64% → 5.24% and the breach count barely moves at 17 → 15 → 14. sd fell by 3.4 points and the band kept marking names wrong, BECAUSE 7/30's COHORT MEAN OF +3.40% EXCEEDS THE BAND ITSELF — 18 of 24 names up, 12 of the 14 breaches upward. When the whole tape drifts more than 3%, the majority breaches by construction AT ANY DISPERSION, INCLUDING ZERO. THE CLEAN FALSIFYING CASE IS 2026-06-16 `\[V]`: sd 3.87%, squarely in the low-dispersion group, |mean| 4.89%, BREACH RATE 68.2% — more than double the rate of the comparably tight 7/14 (sd 2.73%, |mean| 0.50%, 30.4%), 7/02 (2.99%, 1.32%, 29.2%) and 6/23 (3.18%, 0.73%, 25.0%). 6/16 is also one of the record's weakest cohorts at 29.2%, and the dispersion account does not explain it at all. ACROSS ALL 51 RESOLVED COHORTS `\[V]`: corr(breach rate, sd) = +0.6196 and corr(breach rate, |cohort mean|) = +0.4400. Both are material; neither subsumes the other. 7/09's +20d read demonstrates the two pulling APART — mean +3.59% and sd 7.88%, both high, yet only 10 breaches, because the median |move| was 2.77% and a handful of large movers carried the mean while most names sat inside the band. WHAT DOES NOT CHANGE: both mechanisms are MARKET-SIDE, so the durable finding stands untouched and is arguably stronger — the headline accuracy metric is a measurement of the market, now identified as drift AND dispersion rather than dispersion alone. WHAT DOES CHANGE, AND IT IS PARKED-ITEM SCOPE: **Q4-2 MUST BE RE-SCOPED IF IT IS EVER TAKEN UP.** A volatility-scaled band corrects for DISPERSION and does NOTHING ABOUT DRIFT — on a strongly trending tape a vol-scaled metric would still mark an entire cohort wrong, because every name moved in the same direction by more than the band. Q4-2 was parked as a PARALLEL SECONDARY report on the strength of the dispersion argument alone; that justification is now known to be half the problem. Recorded against Q4-2 while it is still parked, so that a future reader does not adopt a vol-scaled secondary in the belief that it addresses the artifact. THE ±3% BAND IS NOT RE-BASELINED AND NO PRIOR CONCLUSION MOVES. DP-3C-n IS NOT DISTURBED AND DOES NOT NEED REOPENING: E4-2's within-cohort design holds cohort drift constant BY CONSTRUCTION, because both arms experience the same tape on the same day, and the within-ticker refinement handles the volatility axis. The ruling survives this finding intact, which is worth stating explicitly so that nobody reopens it on the strength of the headline.

★★ THERE IS NO VERDICT COLUMN AT +10d OR +20d — SO AT THOSE HORIZONS "ACCURACY" IS THE BREACH COUNT BY DERIVATION, NOT BY MEASUREMENT. `\[V]` The Signals header row reads: K `Return +5d`, L `Return +10d`, M `Return +20d`, N `Was Claude Right? (5d)`, O `Notes / Outcome`. THERE IS NO "Was Claude Right (10d)" AND NO "(20d)" ANYWHERE IN THE MASTER. Every +10d and +20d accuracy figure in this record — including the closeout memo §4.1 table's 43.3% at +10d and 32.6% at +20d — is DERIVED BY THE NOTES as `(n − breaches − directional misses)/n`. THIS SHARPENS YESTERDAY'S IDENTITY FINDING RATHER THAN REPEATING IT: at +5d the identity is a property of a spreadsheet formula, verified 1,160/1,160; at +10d and +20d THERE IS NOT EVEN A FORMULA — the identity IS the derivation rule, so the two numbers were never independent quantities at any point in the project's history. CONSEQUENCE FOR THE MEMO: §4.1's table sets an Accuracy column beside a "HOLD rows breaching ±3%" column at all three horizons, and at +10d and +20d those are two forms of the same number presented as corroboration. A dated documentation correction is owed; the FINDINGS in §4.1 are unaffected because they never rested on the pairing. CONSEQUENCE FOR E4-2: the pre-registration's secondary +10d/+20d reads inherit this and cannot carry the replaced safeguard either — DP-3C-n's substitute reporting (mean signed return, sd by stratum, UP/DOWN breach split) applies at all three horizons, not only at +5d. ★ PROCESS NOTE, SELF-CAUGHT BEFORE REPORTING: my review harness read column N for all three horizons this session, which produced "7/23 @ +10d = 58.3%" — that is the +5d VERDICT for that cohort, not a +10d read. It was caught because 17 breaches cannot coexist with 14 hits in 24 rows, and the figures below are recomputed from returns. The 8/05 session's +10d and +20d figures were computed rather than read from N and are UNAFFECTED; this was checked rather than assumed. RECORDED BECAUSE THE FAILURE MODE IS THE PROJECT'S OWN: a harness silently returning a value from the wrong column is the same class as the twelve tool-reports-a-value-it-did-not-compute instances, and the only reason it did not enter the record is that the arithmetic was cross-checked against a second quantity.

★ RESOLUTIONS ENTERED. 7/30 AT +5d = 10/24 = 41.7% — mean +3.40%, sd(pop) 5.24%, 18 of 24 up, median |move| 4.23%, 14 HOLD breaches split 12 UP / 2 DOWN, zero directional signals in a 24-row all-HOLD cohort so accuracy is purely the breach count; movers AG +16.7%, NVDA +12.6%, MSFT +11.8%, AIQ +7.1%, SND +6.3%. 7/23 AT +10d = 7/24 = 29.2% `\[V] recomputed` — mean +2.45%, sd 7.92%, 16 of 24 up, 17 breaches split 12 UP / 5 DOWN; movers MSFT +32.4%, FTI −9.3%, GM +9.1%, SND −8.7%, RTX +6.6%. THAT COHORT READ 58.3% AT +5d ON 9 BREACHES AND 29.2% AT +10d ON 17 — a 29-point fall on a doubled breach count, which is the horizon gradient behaving exactly as described. 7/09 AT +20d = 14/24 = 58.3% — mean +3.59%, sd 7.88%, 15 of 24 up, only 10 breaches split 8 UP / 2 DOWN, median |move| 2.77%; movers MSFT +31.7%, RTX +14.8%, GM +14.3%, SND −9.1%, NVDA +8.8%. THIS IS THE STRONGEST +20d READ IN THE RECENT RECORD, well above 7/01's 25.0% and 7/08's 41.7%, and it is strong for the reason set out above — drift and dispersion pulled apart. HORIZON BREACH RATES REFRESHED AND STABLE `\[V]`: +5d 546/1,184 = 46.1% (median |move| 2.68%), +10d 594/1,065 = 55.8% (3.54%), +20d 548/836 = 65.6% (5.04%).

★★ SELF-CORRECTION — YESTERDAY'S DQ READING WAS WRONG, AND IT WAS WRONG IN THE DIRECTION THAT MADE E4-1 LOOK MORE BROKEN THAN IT IS. The 8/05 entry recorded that all five HIGH → MEDIUM moves across 8/04 and 8/05 were "one-way and none has reverted", and argued that a monotone pre-era drift would be read as a treatment effect at the post-era read. THREE OF THE FIVE REVERTED WITHIN A SINGLE SESSION `\[V]`: today GLD, RTX and VTI all return to HIGH while AAPL moves HIGH → MEDIUM, taking the mix to 18 HIGH / 6 MEDIUM. THE MONOTONE-DRIFT ARGUMENT IS WITHDRAWN. What survives, and is now better measured, is the NOISE FLOOR: four consecutive no-treatment sessions produced 0, 2, 3 and 4 name-changes, BIDIRECTIONAL, with HIGH running 21 → 19 → 16 → 18. E4-1 still needs a stated minimum shift size and a T-C tolerance, and the T-C question is live on its own terms — VTI is a T-C dark control name and it moved out of HIGH and back within two sessions, while NTR moved on 8/04 and has stayed. FOUR CONTROL SESSIONS REMAINS A THIN VARIANCE ESTIMATE and neither number should be set before three or four more.

★★ `risk\_engine.py` READ AT SOURCE — THE CHECK-6 COUNTERFACTUAL IS NOW `\[V]` RATHER THAN `\[?]`, AND THREE FURTHER DEFECTS SURFACE THAT THE LOGS COULD NOT SHOW. The check sequence returns on the FIRST failure, in this order: CHECK 1 error, CHECK 2 HOLD auto-approve, CHECK 3 banned ticker, CHECK 4 data quality, CHECK 5 confidence, CHECK 6 open positions, CHECK 7 duplicate position, CHECK 8 daily loss, CHECK 9 human approval. SCORING NVDA 8/06 AGAINST THE ACTUAL SOURCE: no error; not HOLD; `BANNED\_TICKERS` is an empty list; HIGH ≥ MEDIUM; 72 ≥ 70; CHECK 6 REJECTS at `len(open\_positions) 16 >= 8`. ABSENT CHECK 6 the row continues — CHECK 7 passes because NVDA is `\[SCOUT]` and not in `held\_tickers`; CHECK 8 is a no-op (see D-5); CHECK 9 returns `(True, "PENDING HUMAN APPROVAL — Signal passed all automated checks…")`. **NVDA WOULD HAVE BEEN APPROVED ON 8/04, 8/05 AND 8/06.** Recorded as a COUNTERFACTUAL AND NOT COUNTED, per the 7/30 precedent. ★ D-1 IS NOT A `risk\_engine.py` DEFECT AND THE ATTRIBUTION IS CORRECTED HERE: `evaluate\_signal` receives a single `portfolio` dict and reads `portfolio.get("positions", \[])`; the single-account restriction happens at the CALL SITE in `main.py` L285–286. The fix for D-1 is in `main.py`; the fix for D-2 is in `risk\_engine.py`. Two files, and the 8/04 entry implied one. ★ D-2 CONFIRMED FROM SOURCE — `open\_positions` is the raw position list with NO instrument-type filter, so three bond CUSIPs occupy equity slots. ★ D-3 CONFIRMED FROM SOURCE AND IT IS WORSE THAN DESCRIBED — CHECK 6 carries no `if sig == "BUY"` guard and therefore blocks SELL, while CHECK 8 TWELVE LINES BELOW STATES THE CORRECT PRINCIPLE VERBATIM in its own comment ("block new BUY signals. SELL signals still allowed (to cut losses)"). The correct rule is written down in the same function and not applied. ★ NEW — D-5: CHECK 8 IS A NO-OP. Its body is `if sig == "BUY": pass` with a TODO deferring daily P\&L tracking to Phase 4, so `DAILY\_LOSS\_LIMIT\_PCT = 0.02` is a configured constant that controls nothing. It is NOT printed in the Active Rules banner, so it is not falsely advertised — but it is a documented risk control that does not exist, and under T1 that is latent rather than harmless. ★ NEW — D-6: `MAX\_POSITION\_PCT` IS PRINTED AS AN ACTIVE RULE AND IS NEVER CONSULTED BY THE EVALUATOR. `evaluate\_signal` does not reference it at any of the nine checks `\[V]`; it appears only in `calculate\_position\_size`, which `print\_risk\_report` calls solely when `approved and signal == "BUY"` — a branch that has never executed in 1,339 rows. Yet the banner prints "Max position size : 5.0% of portfolio" under the heading "Active Rules" on EVERY signal. THIS IS THE THIRTEENTH INSTANCE OF THE TOOL-REPORTS-A-VALUE-IT-DID-NOT-COMPUTE CLASS and the first found in the risk engine itself. `\[?]` whether `main.py` enforces position sizing independently; the claim here is scoped to `evaluate\_signal`. ★★ NEW — D-7, AND IT IS A PRE-CONDITION ON ANY CAP CHANGE: THE PARSERS HAVE NEVER SEEN THE APPROVAL PATH FOR A DIRECTIONAL SIGNAL. Because `REQUIRE\_HUMAN\_APPROVAL` is True, an approved BUY returns reason `"PENDING HUMAN APPROVAL — Signal passed all automated checks. Action: BUY NVDA at 72% confidence. Review and approve manually before executing."` — a multi-sentence string containing periods and an em dash, in a field that has carried only short single-clause reasons across 1,339 rows, and `print\_risk\_report` would additionally emit a "Shares : N shares recommended" line that has never appeared in any log. `analyze\_log.py`, `parse\_log\_to\_tracker.py` and `signal\_scan.py` have never been exercised against either. A PARSER THAT HAS NEVER SEEN ITS OWN SUCCESS PATH IS A LATENT DEFECT OF EXACTLY THE CLASS THAT HAS ALREADY BROKEN THIS PROJECT THREE TIMES AT PHASE CUTOVERS. RULE OF RECORD: before CHECK 6 is touched, `edgar\_parser\_audit.py` must synthesise an APPROVED directional row carrying the full PENDING-HUMAN-APPROVAL reason string and the Shares line, and pass. ★ CHECK 5 PRECEDES CHECK 6, CONFIRMED FROM SOURCE — so a sub-70 BUY can NEVER be pre-empted by the position count, and KEEP-70's near-miss denominator is STRUCTURALLY uncontaminated rather than merely observed to be clean. That closes the question by construction; today's GLD at 65 rejecting on confidence with the same 16 open positions is the observational confirmation. ★ THE CAP'S OWN ANALYST NOTE ARGUES AGAINST THE CAP. `RiskConfig` L59–63 reads: "Maximum number of open positions at any time. Fewer positions = more concentration risk but easier to monitor. More positions = more diversification but harder to track." By its own documentation CHECK 6 IS A MONITORING-BURDEN CAP, NOT A RISK CAP — and it caps DIVERSIFICATION, which its own comment identifies as risk-reducing. The system it guards analyses 24 tickers daily under advisory-only operation and has no monitoring burden to speak of. Meanwhile the rule that DOES measure concentration, `MAX\_POSITION\_PCT`, is the one not enforced (D-6). PROPOSED DP-3C-o, NOT RULED TODAY: (i) guard CHECK 6 to BUY-only, unconditionally and independent of the cap question — this is D-3 and it stands on its own; (ii) enforce `MAX\_POSITION\_PCT` inside `evaluate\_signal`, so the rule that measures concentration is the rule that runs; (iii) demote CHECK 6 from a rejection to a reported risk flag, which preserves the information, removes a refusal whose stated rationale is monitoring burden, and avoids picking an arbitrary number. SEQUENCING IS UNCHANGED AND BINDING: D-3 and the analyzer fix first; D-1 and D-2 together, since neither alone changes any outcome (D-1 alone shows 36 positions, D-2 alone shows 13, D-1+D-2 shows 19, and all three still reject against a cap of 8); the cap question LAST, as a dated ruling and not a code tweak; and D-7's parser audit before any of the cap work lands. RECORDED IN FAIRNESS: FIXING THE CAP MAKES THE RECORD LOOK BETTER. "39 directional signals across 56 cohorts, zero risk-engine approvals" is one of the sharper findings in the project, and a cap change converts it to "it approves now". If the cap is changed, the ruling must carry a dated note PRESERVING the pre-change finding — zero approvals in 56 cohorts under the Phase-2 cap, timestamped and not retroactively invalidated, exactly as the guardrail was retired rather than deleted.

★ DIRECTIONAL ROWS — THE NVDA EPISODE EXTENDS TO A FOURTH SESSION AND GLD's SECOND NEAR-MISS IS THE FIRST LIVE ACCRUAL OF THE KEEP-70 LIMITATION RULED YESTERDAY. NVDA BUY at conf 72, REJECTED on `Too many open positions: 16 >= max 8`; chain reads 50, 50, 68, 72, 74 → 72, so FOUR CONSECUTIVE BUYS AND THREE CONSECUTIVE GATE CLEARANCES, unbroken. UNDER DP-3C-m THIS REMAINS ONE EPISODE, opened 2026-08-04, path now 72 → 74 → 72, +5d measured from 8/04 and resolving 2026-08-11. THE LEDGER STANDS AT 2 EPISODES FROM 4 ROWS — the coalescing ruling is doing precisely the work it was written for, one session after being made, which is the strongest available evidence that ruling it before the data arrived was correct. GLD BUY at conf 65, REJECTED on confidence, entering the near-miss registry as row 35 with +5d resolving 2026-08-13. GLD's 8/05 row at 62 and today's at 65 ARE ONE STANCE, and their +5d windows overlap four of five days. THE LIMITATION RECORDED YESTERDAY AS THEORETICAL IS NOW ACCRUING: KEEP-70 carries 5 GLD rows alongside 26 NVDA, and DP-3C-m deliberately does not touch it. Registry 35 rows / 32 resolved, so KEEP-70 READS 13/32 = 40.6% UNCHANGED and SUPPORTED, denominator verified clean at 0.61–0.68 `\[V]`. H4 UNCHANGED at 6/13 = 46.2%, 14 total — GLD's new row is HIGH-DQ but unresolved, so it enters H4's TOTAL and not its ratio; WATCH THIS, because the HIGH count in the registry is now 15 and the next resolution moves H4's denominator for the first time in five sessions. DIRECTIONAL SCARCITY: 39 signals in 1,339 rows (38 BUY, 1 SELL), NVDA 29 = 74.4% single-name; RISK-ENGINE APPROVALS REMAIN ZERO ACROSS 56 COHORTS.

★ THE BLEND DISCOUNTED BOTH DIRECTIONAL ROWS FOR THE FIRST TIME, ON A REGIME SWING, AND STILL PRODUCED NO GATE FLIP. `regime\_score` moved uniformly from +0.009 to −0.181 in one session — the SPY−GLD overlay responding to gold's run — and `signal\_scan` flagged `\[FAIL] D.op == B.blend\_op 22/24`: NVDA base 72 → blend 71, GLD base 65 → blend 63. Under the G2 DESCOPE there is no gate read and none is taken. THE OPERATIONAL FACT IS WORTH BANKING: the blend has now disagreed with base on THREE directional rows across TWO sessions and produced ZERO gate flips — 71 and 72 both clear the 70% gate, 63 and 65 both miss it — so the descope continues to cost nothing operationally. This is the THIRD firing of a check whose wording predates the descope; rephrase it to informational. `confidence\_blend` semantics read UNDETERMINED today because no row was damped, so that finding holds at n=5.

★ WS2 / G1 — UNCHANGED, 1 INDEPENDENT POST-DEPLOY EPISODE OF 4, NOW 23 SESSIONS. WMT trail5d +0.93% and GM −0.33%, neither adverse, no episode; GM still has none. NTR at −5.18% was the only THETA breach and its computed damp rounds to zero, which is correct arithmetic and not a missing damp — the excess over THETA is 0.18pp and `round(0.18 × 1.5)` is 0. Recorded because a damp of 0 on a breaching row looks like a defect and is not.

★ SMALLER ITEMS. Phase token still `\[PHASE 3-B DRY RUN]` with the banner reading "Phase 3-B" — the FOURTH cohort stamped 3-B while the project is in 3-C. `signal\_scan.py` still cites `Daily\_Workflow\_v5\_3` §4 and labels the era "pre-EDGAR (3-B)". `analyze\_log.py` output was not in the supplied set; assume the false ACTIONABLE line fired a third time on NVDA-at-72 and check `logs\\summary\_history.txt` when 5b lands. Session cost figures: 37,056 input / 10,111 output tokens, against 37,065 and 37,107 on the two prior control sessions — the control baseline is now tight across three sessions, which is a good denominator for the EDGAR premium measured on 8/03.

★ OPEN QUESTION RAISED AND NOT RULED — SHOULD THE GATE-CLEARED LEDGER BE GENERATED RATHER THAN HAND-MAINTAINED? DP-3C-l ruled "no workbook tab — the ledger lives in `docs\\analyst\_notes.md`", on the ground of no new file and no new harness. That was right at n=1. It is now a four-row, two-episode ledger with a COALESCING RULE attached (DP-3C-m), maintained in prose, and every element of it — date, ticker, signal, confidence, risk decision, +5d outcome — is derivable from the master and the logs. A RULE APPLIED BY HAND IN ONE PLACE AND QUOTED IN ANOTHER IS THE EXACT SHAPE OF THE CORRECTED-VALUE-SURVIVING-IN-A-SECOND-CODE-PATH DEFECT that has recurred five times in this project. The argument FOR generating it is that a derived ledger cannot drift from the master and applies DP-3C-m identically to every row including retroactively; the argument AGAINST is DP-3C-l's own constraint and the fact that a workbook tab is `retired\_criteria\_audit.py`'s known blind spot, which is how `Sheet1` survived. A middle path exists and is proposed for ruling next session: EXTEND `build\_near\_miss\_registry.py` rather than write a new harness — it already scans the master for BUYs in a confidence band and emits a tab, and the gate-cleared ledger is the same scan at a different threshold plus a coalescing pass, so it is a parameter and not a new instrument. Any such tab must carry a header stating DESCRIPTIVE ONLY, NO STANDARD, EXIT DISPOSITION PRE-COMMITTED INSUFFICIENT, written into the generator so a future reader cannot mistake it for a live criterion.



## 8/07 (Phase 3-C — FOURTH CONTROL COHORT, EDGAR FLAG DELIBERATELY UNSET) — ★★ A SINGLE MANUAL PRICE ENTRY CORRUPTED THREE COHORTS AT ONCE AND BOTH INTEGRITY GATES PASSED WITH IT IN PLACE; THE COHORT PRODUCED THREE BUY SIGNALS, THE MOST IN THE PROJECT'S HISTORY, AND THE FIRST GENUINELY NEW DIRECTIONAL TICKER IN MONTHS; AND THE DRIFT MECHANISM RECORDED YESTERDAY CORROBORATED ON FRESH DATA ONE SESSION AFTER BEING WRITTEN DOWN. Cross-check 24/24 — `signals\_2026-08-07.log` ↔ `logs\\claude\_equity\_bot\_tracker.xlsx` reconcile clean, run by `log\_tracker\_crosscheck.py` itself, which also closes the 8/06 gap where only `signal\_scan` output was available. Era `A-S1D1-B1`, zero `E\[…]` tags, no `\[EDGAR] prefetch` line, no budget warning; 21 HOLD + 3 BUY; DQ 18 HIGH / 6 MEDIUM / 0 LOW; conf mean 55.9, median 62.0, sd(pop) 11.95, range 33–72; totals 1,363 rows, 57 cohorts; recalc 0 errors on 8,542 formulas; accounts Roth IRA 7 / Individual 6 / both 6 / Scout 5 with no "Unknown"; no premature K:N; D1 reconciles 24/24 with zero damped rows and no material adverse move anywhere in the cohort; RESOLUTIONS COMPLETE AT ALL THREE HORIZONS WITH ZERO UNRESOLVED-BUT-DUE. RUN WINDOW 09:33:31–09:37:54 CST — CANONICAL, +3.5 MINUTES, the first on-time run since 8/03 after offsets of +98, +23 and +39 minutes. Recorded because yesterday's Px@signal finding made run timing a live variable rather than a housekeeping detail.

★★ DATA-INTEGRITY INCIDENT — WMT's 2026-08-07 CLOSING PRICE WAS ENTERED AS 11.85 INSTEAD OF 111.85, A DROPPED LEADING DIGIT, AND IT CORRUPTED THREE COHORTS SIMULTANEOUSLY. ATTRIBUTION, STATED BY THE OPERATOR AND CLOSED 2026-08-10 `\[V]`: an operator data-entry error (RW), corrected at source immediately once the review flagged it. The copy of the master first supplied to the 8/07 review session carried 11.85; the corrected copy supplied later the same session carried 111.85. RECORDED BECAUSE THE CONVENTION IS DATED ATTRIBUTION AND VISIBLE SELF-CORRECTION, NOT A SILENT FIX — the error is unremarkable and the handling is the part worth keeping: it was owned, corrected at source rather than worked around, and entered in the record on the same date it was found. NO FIGURE COMPUTED ON THE CORRUPTED VALUE ENTERED THE RECORD; the corrupted reads (7/31 at 41.7%, 7/24 at 25.0%, 7/10 at 45.8%) exist only in the review session and are superseded by the corrected figures below. THE MECHANISM IS STRUCTURAL AND IS THE PART THAT MATTERS: 2026-08-07 is simultaneously the +5d resolution date for 7/31, the +10d date for 7/24 and the +20d date for 7/10, SO EVERY TRADING DAY IS THE RESOLUTION DATE FOR THREE COHORTS AND EVERY MANUAL OUTCOME-PRICE ENTRY CARRIES A 3× BLAST RADIUS BY CONSTRUCTION. Measured impact against the corrupted copy: 7/31 at +5d read 41.7% with 14 breaches and sd(pop) 19.71% against a corrected 45.8% / 13 / 6.37%; 7/24 at +10d read 25.0% / 18 / 20.06% against 29.2% / 17 / 8.02%; 7/10 at +20d read 45.8% / 13 / 20.08% against 50.0% / 12 / 7.34%. Every cohort moved 4.2 accuracy points and every dispersion figure tripled. ★★ BOTH INTEGRITY GATES RAN AND BOTH PASSED WITH THE BAD VALUE IN PLACE, AND NEITHER FAILURE IS A BUG — BOTH ARE SCOPE. `recalc.py` returned 0 errors on 8,542 formulas because 11.85 IS A VALID NUMBER; recalc catches FORMULA errors, never MAGNITUDE errors. `log\_tracker\_crosscheck.py` returned 24/24 CLEAN because it reconciles COLUMNS A–G, the PASTED block, while the outcome prices live in H/I/J and are MANUAL ENTRY; the harness is structurally incapable of seeing them and was never claimed to. THE CONCLUSION IS THEREFORE NOT "A TOOL FAILED" BUT "THE HIGHEST-LEVERAGE MANUAL SURFACE IN THE PROJECT HAS NO GATE AT ALL". This is a different class from the thirteen tool-reports-a-value-it-did-not-compute instances: nothing reported a value it did not compute; a value nothing was watching was simply wrong. ★ CLEAN SWEEP OF THE RECORD FOR SIBLINGS `\[V]`: zero returns with |move| ≥ 40% at any horizon across all 1,363 rows, and zero resolved +5d cohorts with sd(pop) > 12%. No prior truncation of this magnitude is hiding. ★ REMEDY PROPOSED AND SCHEDULED AHEAD OF THE EDGAR CHAIN: a same-day quote-versus-close check on the outcome columns, comparing every entered +Nd price against that ticker's own `Px@signal` in the resolution-date cohort — both are prices for one instrument on one day, both already sit in the master, and 11.85 against 112.01 is an 89% discrepancy that no threshold could miss. THE REASON IT MOVES AHEAD OF THE EDGAR WORK IS TIMING, NOT SEVERITY: today's error landed on a control cohort and cost a scare, whereas the same error after go-live lands inside E4-2's measurement population, where it would be a corrupted treatment row rather than a re-readable control row.

★★ THREE BUY SIGNALS IN ONE COHORT — A RECORD, AND THE CONCENTRATION MOVES FOR THE FIRST TIME. `\[V]` No cohort in 57 has produced more than two BUYs; the prior maximum of two occurred on 6/03, 6/12, 6/16 and 7/22. Today: NVDA at conf 72 (gate-cleared, REJECTED on `Too many open positions: 16 >= max 8`), GLD at 67 and QQQ at 62 (both near-misses, REJECTED on confidence). QQQ IS A NEW TICKER IN THE NEAR-MISS REGISTRY. The registry moves 35 → 37 and reads NVDA 26 / GLD 6 / VTI 3 / SCHD 1 / QQQ 1, taking NVDA's share from 74.3% to 70.3%, while NVDA's share of ALL directional output moves from 74.4% to 71.4% (30 of 42 in 1,363 rows). THIS IS THE FIRST MOVEMENT AGAINST THE SINGLE-NAME STRUCTURAL CONSTRAINT that underwrote G2's failure, DP-7 and DP-10's collision, and DP-3C-l's starvation forecast. IT IS THREE OBSERVATIONS AND NOTHING IS READ FROM IT — a structural finding established across 1,243 rows does not move on one session, and the correct posture is to watch whether the regime shift is broadening directional output, not to conclude that it has. Recorded now precisely so that if it continues, the date it started is in the record rather than reconstructed later. ★ NVDA's RUN REACHES A FIFTH CONSECUTIVE BUY — 68 (8/03), 72, 74, 72, 72 — with four consecutive gate clearances. UNDER DP-3C-m THIS REMAINS ONE EPISODE, opened 2026-08-04, path 72 → 74 → 72 → 72, +5d measured from 8/04 and resolving 2026-08-11. Four rows of accrual, one episode; the ruling made on 8/05 has now absorbed three further sessions exactly as intended. GLD reaches a third consecutive BUY (62 → 65 → 67), adding a second registry row from one stance, which is the KEEP-70 serial-dependence limitation continuing to accrue as recorded. KEEP-70 UNCHANGED AND SUPPORTED at 13/32 = 40.6%, denominator verified clean at 0.61–0.68. H4 UNCHANGED at 6/13 = 46.2% with 17 HIGH-DQ rows now in the registry, so the denominator moves within the week. RISK-ENGINE APPROVALS REMAIN ZERO ACROSS 57 COHORTS.

★ RESOLUTIONS, ON THE CORRECTED MASTER. 7/31 AT +5d = 11/24 = 45.8% — mean +3.87%, sd(pop) 6.37%, 17 of 24 up, median |move| 3.96%, 13 HOLD breaches split 12 UP / 1 DOWN in a 24-row ALL-HOLD cohort, so accuracy is purely the breach count; movers AG +23.0%, NVDA +14.1%, CBRS +13.3%, MSFT +9.2%, AIQ +8.4%. **THIS IS THE THIRD CONSECUTIVE CORROBORATION OF THE DRIFT MECHANISM AND IT ARRIVED ONE SESSION AFTER THE MECHANISM WAS WRITTEN DOWN**: the cohort mean of +3.87% EXCEEDS THE ±3% BAND ITSELF, so twelve of thirteen breaches are upward on unremarkable dispersion of 6.37%. Following 7/30 at mean +3.40% with sd 5.24%, the pattern is holding on fresh data rather than being fitted to old, which is the distinction that separates it from every small-n reading in this project. 7/24 AT +10d = 7/24 = 29.2% — mean +2.86%, sd 8.02%, 17 breaches split 11 UP / 6 DOWN; movers MSFT +29.8%, CBRS +14.9%, AG +10.0%, FTI −9.3%. 7/10 AT +20d = 12/24 = 50.0% — mean +3.89%, sd 7.34%, 12 breaches split 9 UP / 3 DOWN; movers MSFT +30.0%, RTX +14.7%, GM +12.0%. TWO NEAR-MISS BUYS PAID AT THE LONGER HORIZONS, RECORDED SO A FUTURE READER DOES NOT MISCOUNT THEM: NVDA at conf 63 returned +6.68% at +10d on the 7/24 cohort and +6.78% at +20d on the 7/10 cohort. NEITHER TOUCHES KEEP-70, which reads +5d only. HORIZON BREACH RATES REFRESHED `\[V]`: +5d 559/1,208 = 46.3% (median |move| 2.68%), +10d 611/1,088 = 56.2% (3.57%), +20d 560/859 = 65.2% (4.97%).

★★ E4-1 — TODAY SEPARATES CHURN FROM NET SHIFT, AND THE DISTINCTION IS THE THRESHOLD. SIX names changed data quality — AAPL, NTR and WMT to HIGH; NKE, PWR and XLU to MEDIUM — which is THE MAXIMUM CHURN OBSERVED IN THE ERA, and THE HIGH COUNT DID NOT MOVE AT ALL, holding at 18. Envelope refreshed across 19 same-era untreated cohorts `\[V]`: churn mean 4.50 with a maximum of 6; HIGH count mean 17.6, sd(pop) 1.39, range 14–20; |ΔHIGH| session-to-session p95 = 3 and maximum = 3. THE PRE-REGISTERABLE THRESHOLD IS THEREFORE ON THE NET, NOT THE CHURN: E4-1 requires |ΔHIGH| > 3 NAMES before a movement is a candidate signal at all, and today strengthens it — a maximum-churn session left the net completely unmoved, so a tool counting name-changes rather than net shift would have reported a treatment-sized event on a day when nothing happened. THIS ALSO CLOSES THE "NEEDS MORE CONTROL COHORTS" QUESTION: the baseline is not the four-session control window but every same-era untreated cohort since 7/13, which is 19 and sufficient. Further control cohorts have NO remaining marginal value to E4-1, and none to E4-2 or E4-3, which read post-deploy only.

★ THE BLEND DISCOUNTED ALL THREE DIRECTIONAL ROWS AND STILL PRODUCED NO GATE FLIP. `regime\_score` deepened for a third consecutive session, +0.009 → −0.181 → −0.546, and `signal\_scan` flagged `\[FAIL] D.op == B.blend\_op 21/24`: QQQ 62 → 57, NVDA 72 → 70, GLD 67 → 62. Under the G2 DESCOPE no gate read is taken. THE OPERATIONAL TALLY IS WORTH BANKING: the blend has now disagreed with base on SIX directional rows across THREE sessions and produced ZERO operational differences — NVDA's 70 clears the gate either way, QQQ and GLD miss it either way. The descope continues to cost nothing. Fourth firing of a check whose wording predates the descope; rephrase to informational. `confidence\_blend` semantics UNDETERMINED again (no damped rows), so that finding holds at n=5.

★ WS2 / G1 — UNCHANGED, 1 INDEPENDENT POST-DEPLOY EPISODE OF 4, NOW 24 SESSIONS. WMT trail5d +1.19%, GM −1.07%; no THETA breach anywhere in the cohort, so no counterfactual to record today. GM still has none post-deploy.

★ SMALLER ITEMS. Phase token still `\[PHASE 3-B DRY RUN]` with the banner reading "Phase 3-B" — the fifth cohort stamped 3-B while the project is in 3-C. `signal\_scan.py` still cites `Daily\_Workflow\_v5\_3` §4 and labels the era "pre-EDGAR (3-B)". MSFT closed at conf 72 as a HOLD, above the BUY gate, which `signal\_scan` correctly lists under "at/above the 70% BUY gate" alongside NVDA while separately and correctly excluding it from the near-miss count — the guard that change-order item 5b still needs.



## 8/10 (Phase 3-C — TOOLING, SOURCE REVIEW AND RECORD REPAIR; NO COHORT REVIEWED) — ★★ A GUARD WAS BUILT FOR THE ONLY MANUAL SURFACE IN THE PROJECT WITH NO GATE, AND IT FOUND TWO PREVIOUSLY UNDETECTED DATA ERRORS ON ITS FIRST RUN; `main.py` READ AT SOURCE CLOSES D-1 AND D-6 AND SURFACES D-8, A DISPATCH LANDMINE THAT WOULD HAVE DESTROYED A COHORT SILENTLY AT CHANGE-ORDER STEP 7; AND THE RECORD ITSELF WAS REPAIRED AFTER THE TWO-UPCOMING-BLOCKS DEFECT RECURRED. **NO DAILY COHORT WAS REVIEWED THIS SESSION AND THIS IS RECORDED AS A GAP, NOT A PASS.** 2026-08-10 is a trading day; whether the canonical run executed is not established here, no log or master was supplied for review, and and the resolutions due today — +5d for the 8/03 cohort, +10d for 7/27, +20d for 7/13 — are NOT confirmed entered. G4 requires the cross-check streak clean THROUGH the exit review, so 8/10 must be reconciled with `log\_tracker\_crosscheck.py` and `outcome\_sanity.py` before the streak is cited. Session work was tooling, source review and record repair only.

★★ `outcome\_sanity.py` BUILT, CALIBRATED AND REGRESSION-TESTED — THE 8/07 HOLE IS CLOSED. The 8/07 incident established that the outcome columns are the only manual-entry surface with no gate and that a single cell carries a 3x blast radius, because every trading day is simultaneously the +5d, +10d and +20d resolution date for three cohorts. FOUR CHECKS. (A) QUOTE-VERSUS-CLOSE, the primary: a +Nd price entered for resolution date D is a CLOSE for date D, and the master already holds that ticker's `Px@signal` for date D in the D cohort — same instrument, same day, so they cannot differ much. This is the check that catches 11.85 against 112.01. (B) CROSS-HORIZON AGREEMENT: several cohorts resolve on the same date for the same ticker and those cells must hold the SAME price. (C) HORIZON-SCALED MAGNITUDE. (D) COHORT DISPERSION. THE TRADING-DAY INDEX IS DERIVED FROM THE MASTER'S OWN COHORT DATES rather than from a holiday table — verified `\[V]` that the cohort sequence equals the true trading calendar exactly, 57 cohorts against 57 trading days with zero gaps and zero non-trading dates — so there is no second source of truth to drift, which is the defect class that has recurred five times in this project. It refuses `tracker\_with\_registry.xlsx` as an input at exit 2, the same guard `log\_tracker\_crosscheck.py` carries. It writes nothing. ★ CALIBRATION IS ITSELF A FINDING, AND THE FIRST PASS WAS WRONG. A flat 25% magnitude threshold produced 29 findings on a clean master and BURIED THE REAL DEFECT IN TRUE POSITIVES: CBRS genuinely moved −34.8% at +20d and MSFT +31.7%, and a guard that fires 29 times is a guard that gets ignored. Retuned to horizon-scaled thresholds (+5d 30%, +10d 40%, +20d 50%) with a 0.05% rounding tolerance on cross-horizon agreement, which absorbs a one-cent SPY difference while still flagging a one-dollar GLD one. Four findings on the clean master, both of them real. THE LESSON IS THE MIRROR OF THE 3-B CLOSEOUT §4.4 LESSON: an assertion that does not model the mechanism produces false positives at exactly the rate it produces confidence, and a threshold set without measuring the legitimate extremes is the same error in a different direction. ★ REGRESSION-TESTED THREE WAYS BEFORE SHIPPING `\[V]`: against the corrected master, the four genuine findings below and nothing else; against the 2026-08-07 defect RE-INJECTED into all three cells, caught on every one plus the dispersion tell, exit 1; against the report copy, refused at exit 2. ADD TO `scan.bat` AFTER THE PASTE, alongside the cross-check.

★★ TWO PREVIOUSLY UNDETECTED DATA ERRORS, FOUND BY THE GUARD ON ITS FIRST RUN AGAINST THE FULL RECORD. (i) AG's CLOSE FOR 2026-06-26 IS ENTERED AS 19.89 IN THREE CELLS — the 5/28 +20d, 6/11 +10d and 6/18 +5d rows, all three carrying the same value, so it is a single wrong figure entered once and read three times rather than three independent typos. THE EVIDENCE THAT IT CANNOT BE RIGHT `\[V]`: AG's quote on the morning of 6/26 was 17.13 and the next session's was 16.60, and the implied close series across 6/22 to 6/30 reads 17.72, 16.50, 16.06, 16.50, \[19.89], 16.81, 16.96 — a single 20% spike up and 15% back down inside an otherwise smoothly declining series. A close of 19.89 requires AG to close 16% above its own morning quote and then open the next session 17% lower. RULED OUT AS A DATE-MAPPING ARTIFACT BEFORE BEING CALLED AN ERROR: only 2 of 24 tickers show a >5% gap on 6/26, so the calendar mapping is sound and the problem is ticker-specific; the other name, CBRS at 8.4%, is the project's most volatile instrument and is left alone. THE TRUE VALUE IS NOT ASSERTED HERE AND MUST BE VERIFIED EXTERNALLY against Schwab price history for 2026-06-26 — inferring it from the surrounding series would be manufacturing data, which is the same objection that stopped 8/04's Px@signal from being restated. Correcting it moves the 6/18 +5d, 6/11 +10d and 5/28 +20d cohort reads. (ii) GLD HAS TWO DIFFERENT CLOSES ENTERED FOR 2026-07-02 — 378.13 from the 6/03 +20d row against 379.13 from the 6/17 +10d and 6/25 +5d rows. One date cannot have two closes, so one of them is wrong by construction; which one is not determinable from the master alone. ★ CLEAN SWEEP FOR FURTHER SIBLINGS `\[V]`: across all 1,363 rows there are ZERO returns with |move| >= 40% at any horizon and ZERO resolved +5d cohorts with sd(pop) > 12%. Nothing of the 8/07 magnitude is hiding anywhere in the record. ★ RECORDED PLAINLY: THESE TWO ERRORS HAVE BEEN IN THE MASTER SINCE JUNE AND EVERY GATE THE PROJECT HAS RUN SINCE THEN PASSED OVER THEM. `recalc.py` cannot see them because both values are valid numbers; `log\_tracker\_crosscheck.py` cannot see them because it reconciles the PASTED columns A-G and these live in the manual H/I/J. That is not a tool failure — neither tool ever claimed the ground — but it means every cohort read that touched those rows was computed on an unverified figure, and the guard should have existed before the 8/07 incident rather than because of it.

★★ `main.py` READ AT SOURCE — D-1 AND D-6 CLOSE, AND D-8 IS NEW AND BLOCKING. ★ D-6 CLOSED, AND IT IS BROADER THAN THE 8/06 SCOPE `\[V]`. The 8/06 entry established that `evaluate\_signal` never consults `MAX\_POSITION\_PCT` and flagged `\[?]` whether `main.py` enforced position sizing independently. It does not: `calculate\_position\_size` is IMPORTED at `main.py` L41 and NEVER CALLED anywhere in the file, and its only call site in the codebase is inside `risk\_engine.print\_risk\_report` L311, on the `approved and BUY` branch that has never executed in 1,363 rows. SO "Max position size : 5.0% of portfolio" IS PRINTED AS AN ACTIVE RULE ON EVERY SIGNAL AND IS ENFORCED NOWHERE IN THE SYSTEM. The unused import is the tell. Thirteenth instance of the tool-reports-a-value-it-did-not-compute class, now fully characterised rather than partially. ★ D-1 CLOSED — AND THE RECORD CITED THE WRONG LINE, WHICH IS CORRECTED HERE. `portfolio = portfolios\[0] if portfolios else {}` appears TWICE in `main.py`: at L286 inside `handle\_phase2`, and at L330 inside `handle\_phase3a`. THE 8/04 ENTRY CITES "L285-286", WHICH IS THE PHASE-2 HANDLER — DEAD CODE, SINCE `PHASE` IS "3-B" AND L542 DISPATCHES PHASE 2 ONLY WHEN `PHASE == 2`. The live defect is at L330. The reasoning in the 8/04 entry was correct and its citation pointed at code that never runs; a fix applied only where the record points would have changed nothing and would have appeared to fail. THE 8/04 ENTRY IS NOT EDITED — the correction is recorded here, per the standing rule. ★★ D-8 — NEW, AND IT IS A BLOCKING PRE-CONDITION ON CHANGE-ORDER STEP 7. `PHASE = "3-B"` is a module constant at L63, and step 7 of the change order is "correct the `\[PHASE 3-B DRY RUN]` token in `main.py`". SETTING IT TO "3-C" BREAKS EVERY SIGNAL IN THE RUN, SILENTLY. L542 reads `if PHASE == 2`, L544 reads `elif PHASE in ("3-A", "3A", 3, "3-B", "3B")`, and L550 falls through to `log.error(f"Phase {PHASE} handler not implemented in this build.")`. "3-C" matches neither branch. THE FAILURE IS A LOGGED ERROR, NOT AN EXCEPTION, so the loop continues through all 24 tickers and the run reports "Bot run complete." CONSEQUENCE CHAIN, EACH ITEM VERIFIED FROM SOURCE `\[V]`: zero `Signal JSON:` lines are emitted, so there is no cohort, no phase bracket and nothing for any parser to read; all 24 Claude API calls are still made and paid for, because the dispatch sits DOWNSTREAM of `get\_signal`; `analyze\_log.py` reports 0 signals; and — the compounding failure — `signal\_state.json` STILL UPDATES, because the S1 raw-confidence write at L558-566 sits OUTSIDE the if/elif/else. The S1 chain would therefore advance on a date that has no rows in the master, and the next session's `prior=` chain would be built on signals that were never logged, recoverable only by re-seeding from the master. `edgar\_parser\_audit.py` CANNOT CATCH THIS — it runs the real parsers against a SYNTHESISED log and never executes `main.py`, so step 8's "exit 0" gives false assurance about step 7, exactly as the 8/03 audit run passed against the current tag and said nothing about the amended one. FIX: extend the L544 tuple to include "3-C" and "3C" IN THE SAME EDIT as L63, never separately. RECORDED AS STEP 7b, bound to step 7, with a verification that is not the audit: one live run showing 24 `Signal JSON:` lines. NOTE THE SYMPTOM COLLISION — Workflow §18's troubleshooting table already maps "analyze\_log reports 0 signals" to "era label leaked into the phase bracket". Same symptom, different cause; the table would send the operator hunting the wrong thing, and §18 needs a second row.

★ WHAT HOLDS UP IN `main.py`, RECORDED BECAUSE ABSENCES AND NON-EVENTS ARE WORTH THE SAME ATTENTION AS DEFECTS `\[V]`. The flag-and-era atomicity ruled on 8/02 is real in the source rather than aspirational: L94 derives `EDGAR\_ENABLED` from the environment, L96 derives `PROMPT\_VARIANT` from `EDGAR\_ENABLED`, and L55 gates the `edgar\_client` import on the same variable — three independent behaviours moving on one switch, with the reasoning written into the comment block at L85-90. That design is precisely why 8/04's forgotten flag produced a correctly-labelled CONTROL run rather than a mislabelled TREATMENT one, and it is the single strongest piece of defensive design in the codebase.

★ PROCESS FINDING — THE DEFECT-DISCOVERY CHANNEL HAS SHIFTED, AND THE RECORD'S STANDING LESSON NEEDS A QUALIFIER. The 8/02 entry established that sixteen of seventeen `edgar\_client.py` defects came from live runs rather than from the 102-assertion self-test suite, and "the first live run of anything is where the defects are" became an operator note in Workflow §19. FOUR OF THE LAST FIVE DEFECTS WERE FOUND BY READING SOURCE, NOT BY RUNNING ANYTHING: D-5, D-6 and D-7 from `risk\_engine.py` on 8/06, and D-8 from `main.py` today. THE QUALIFIER: the standing lesson holds for defects in BEHAVIOUR — wrong values, bad extractions, cache masking — because those need real inputs to surface. It does NOT hold for defects of ABSENCE: a rule that is advertised and never enforced (D-6), a check whose body is `pass` (D-5), a success path no parser has seen (D-7) and a dispatch that silently declines to run (D-8) are all invisible to a live run precisely because the live run behaves normally. D-8 is the sharpest case — it would only have surfaced in a live run BY DESTROYING THE COHORT. Both channels are needed and they find different classes.

★★ THE RECORD ITSELF WAS REPAIRED — THE TWO-UPCOMING-BLOCKS DEFECT RECURRED, AND THE ESCAPE COMPOUNDING HAD REACHED THREE DEEP. `docs\\analyst\_notes.md` was found carrying an EMPTY `Upcoming` header, a stray `## \\---` heading, a stranded closing advisory line mid-file, and then the real Upcoming block — the same defect the 8/04 entry recorded and superseded, recurring on the very next splice. It is now a two-time occurrence and the cause is the paste step, not the content, so the instruction is written into the Upcoming block: exactly ONE Upcoming block, delete the old one, never append beside it. Structural repairs: the 8/07 entry inserted; the two Upcoming blocks collapsed to one and rewritten current; the orphan heading, stray separator and stranded advisory line removed; the `## ` prefix added to the 8/05, 8/06 and 8/07 entries to match the file's convention (13 headings to 16); the closing separator and advisory line restored to the actual end of file. ★ DE-ESCAPING — 1,715 ARTIFACTS REMOVED IN A FORMATTING-ONLY PASS, backslashes falling from 1,775 to 48, with every one of the 48 survivors a genuine Windows path (28 `logs\\`, 5 `docs\\`) or an intentional regex character. Workflow §8 warns that markdown editors auto-escape on paste and that the escapes COMPOUND on each save; the master had reached three-deep sequences. THE PASS WAS GATED, NOT TRUSTED: the script verified that every pre-existing content line survives verbatim once backslashes are stripped, 0 missing, so only backslash characters changed. NO WORDS, NUMBERS OR CONCLUSIONS WERE ALTERED AND NO HISTORICAL ENTRY WAS REWRITTEN. Two judgment calls are recorded because they were close: six regex strings discussing a Python pattern were initially left alone as ambiguous between `\\d` and `\\\\d`, then corrected once the surrounding prose settled it ("`\\d` matches a single digit"); and a 6/15 entry reading "Notes hygiene: file has runaway escaping" was itself over-escaped, which is the defect describing itself.

★ 8/07 WMT ATTRIBUTION CLOSED (RW, 2026-08-10) — an operator data-entry error, corrected at source immediately once the review flagged it. Recorded because the convention is dated attribution and visible self-correction; the error itself is unremarkable and the handling is the part worth keeping — owned, corrected AT SOURCE rather than worked around downstream, and entered on the date found. No figure computed on the corrupted value entered the record.

★ COMMIT BACKLOG — RUNBOOK ISSUED, NOT YET EXECUTED. One command at a time, with a credential pre-flight carrying two hard STOP conditions: `token.json` and `.env` sit in the project root, and `git ls-files` must be checked for both BEFORE anything is staged, because a secret already in history needs a rotated Schwab token and possibly a history rewrite rather than another commit on top. `.gitignore` commits and pushes ALONE first, so the push path is proven while only one harmless commit is at risk. THE BACKLOG IS NOT RETIRED UNTIL THE FILES ARE VISIBLE ON THE REMOTE. ★ RAISED AND UNRULED — ARE `logs\\signals\_\*.log` AND THE MASTER TRACKED? DP-3C-i ruled that the `E\[…]` tag must carry filing dates BECAUSE `edgar\_cache\\` is gitignored and deletable, so window membership "survives nowhere permanent". THAT REASONING ASSUMES THE LOGS ARE DURABLE. If they are untracked they are as impermanent as the cache, and E4-2's ADJACENT versus COVERED-QUIET split is not reconstructible after a disk loss — the exact hazard DP-3C-i exists to close. The master carries the argument with more force still: manual-entry-only, ground truth for every harness, one copy. Tracking binaries and a growing log directory has real costs, so this belongs in a dated ruling either way and is flagged so it is not decided by omission.

★ SESSION DECISION — THE BUILD IS HELD TO THE WEEKEND, AND THE CONTROL-COLLECTION FRAMING IS CORRECTED WHILE IT IS STILL A CHOICE. The 8/04 entry recorded control collection as "a deliberate and recorded choice, not drift", justified because control cohorts ARE E4-1's pre-era baseline. THAT JUSTIFICATION EXPIRED ON 8/07, when the E4-1 envelope was measured across 19 same-era untreated cohorts rather than the four-session control window. Further control cohorts have NO marginal value to E4-1, and none to E4-2 or E4-3 which read post-deploy only. SO THE CONTROL WINDOW NOW CONTINUES BECAUSE N-1 IS UNFIXED, FULL STOP — it is a CONSEQUENCE, not a choice, and "keep collecting controls" is a comfortable sentence that makes a delay sound like a decision. Recorded in that form deliberately. THE COST IS REAL AND STATED: E4-2 needs roughly 20 post-deploy cohorts for 150 ADJACENT rows, so every deferred day moves the first read later. ALSO RECORDED: only change-order step 7 onward needs a contiguous block — D-3, 5b, the audit additions, N-1's fix and DP-3C-i/j are dormant or non-runtime while `EQUITY\_EDGAR` is unset and can each land singly on a weekday, so the weekend-shaped piece is smaller than the whole change order.



\## 8/11 (Phase 3-C — CHANGE ORDER, SESSION 2; EVERY REMAINING STEP LANDED EXCEPT THE LIVE VERIFICATION) — ★★ THE CHANGE ORDER IS COMPLETE TO THE EDGE OF WHAT A HARNESS CAN PROVE. D-7, D-3, 5b, 7+7b, D-1/D-2 and DP-3C-o (i)(ii)(iii) are all landed and written back; a new `phase\_dispatch\_audit.py` closes D-8; four gates exit 0 (`edgar\_client --selftest`, `edgar\_parser\_audit` at 38 checks, `phase\_dispatch\_audit`, `xbrl\_sweep --selftest`) and `analyze\_log` runs clean against the real 8/10 log. WHAT REMAINS IS EXACTLY ONE THING AND NO HARNESS CAN SUBSTITUTE FOR IT: a live `main.py` run emitting 24 `Signal JSON:` lines. `EQUITY\_EDGAR` STAYS UNSET until that run is read.

&#x20;

★★ THE CHANGE ORDER'S OWN STATED ORDER WAS WRONG, AND FOLLOWING IT WOULD HAVE REPEATED THE DEFECT CLASS THIS PROJECT KEEPS PAYING FOR. The change order lists `(D-3) guard CHECK 6 to BUY-only` FIRST and D-7's approval-path audit NINTH. D-7's own text says: \*"Before CHECK 6 is touched, `edgar\_parser\_audit.py` must synthesise an APPROVED directional row carrying both and pass."\* Both cannot hold. \*\*D-7 WINS, and the reason is mechanical:\*\* D-3 is the change that makes directional APPROVALS possible for the first time, and an approved signal emits a multi-sentence `PENDING HUMAN APPROVAL — …` reason that has never appeared in any of 1,363 rows. Landing D-3 first would have shipped a never-parsed line shape into a canonical cohort — the 2026-06-15 / 2026-07-07 / 2026-08-10 failure, a fourth time, this time self-inflicted by following our own list. THE LIST IS NOT EDITED, per the standing rule; the correction is recorded here. \*\*METHOD NOTE: an ordering constraint stated inside an item's own text OUTRANKS the position of that item in a list.\*\* The list is a convenience; the constraint is the specification.

&#x20;

★★ D-7 LANDED FIRST AND IS NOW 16 CHECKS INSIDE `edgar\_parser\_audit.py`. The harness synthesises a 24-row log in which RTX is an APPROVED BUY and GM an APPROVED SELL — the SELL chosen deliberately, because D-3 exists precisely to stop CHECK 6 rejecting SELLs, so a SELL is the FIRST approval the change produces in practice. The reason text is reproduced VERBATIM from `risk\_engine` L224-228 rather than paraphrased. Asserts: all three parsers still return 24 rows; accounts survive; RTX parses BUY and GM SELL rather than HOLD; the D/B/E tags STILL PARSE DOWNSTREAM of the reason (the reason sits between the header and every tag, so a reason that disturbs a delimiter loses the tags SILENTLY, a missing tag reading as an absent feature rather than a parse failure); and the reason does not leak into a tracker field. ★ THE DISCRIMINATING ASSERTION IS WORTH RECORDING: the synthetic reason states `at 99% confidence` while the header carries the row's real confidence. IN PRODUCTION THE TWO ARE IDENTICAL, WHICH IS EXACTLY WHY A PARSER READING THE WRONG ONE WOULD BE INVISIBLE FOREVER. Making them differ in the fixture is the only way the assertion can discriminate. Both parsers read the header `\[V]`. A units error in the first draft of that check (`parse\_log\_to\_tracker` stores `Conf %` as a FRACTION — 0.64 — matching the master tracker's own 0.62 for WMT, while `signal\_scan` keeps integer percent) was fixed IN THE TEST, and the divergence is now documented rather than papered over.

&#x20;

★★ RULED 2026-08-11 — DP-3C-o, ALL THREE PARTS. RW.

&#x20; \*\*(i) = D-3, CHECK 6 GUARDED TO BUY-ONLY.\*\* A SELL REDUCES the position count; rejecting one for "too many open positions" is the rule firing in the opposite direction to its own purpose. This is what rejected CBRS's SELL at conf 68 on 2026-06-26, standing in the DP-3C-l ledger as "REJECTED — position count".

&#x20; \*\*(iii) CHECK 6 DEMOTED FROM REJECTION TO A REPORTED FLAG.\*\* Rationale of record: `MAX\_OPEN\_POSITIONS` is a monitoring-burden cap, not a risk cap, and `RiskConfig`'s own note (L59-63) says so in as many words — \*"Fewer positions = more concentration risk but easier to monitor. More positions = more diversification but harder to track."\* BY ITS OWN COMMENT THE CAP BUYS MONITORING CONVENIENCE BY ACCEPTING CONCENTRATION RISK. A rule that increases the risk it is filed under should not hold a veto. DEMOTED, NOT DELETED, and the distinction was ruled explicitly: the monitoring burden is real — 16 positions genuinely are harder to track than 8 — so the flag preserves the one thing the cap was legitimately measuring while removing its veto.

&#x20; \*\*(ii) `MAX\_POSITION\_PCT` NOW ENFORCED INSIDE `evaluate\_signal` (CHECK 6b).\*\* It was printed as an Active Rule on every signal and consulted by nothing — D-6, the thirteenth instance of the tool-reports-a-value-it-did-not-compute class and the first found in the risk engine. \*\*WHY THIS ENFORCES WHILE CHECK 6 ONLY FLAGS:\*\* `MAX\_POSITION\_PCT` is a REAL risk cap by its own note ("prevents catastrophic loss if one position goes to zero"); `MAX\_OPEN\_POSITIONS` is a burden cap by its own note. THE REAL CAP GATES; THE BURDEN CAP REPORTS.

&#x20; \*\*PRESERVED FINDING, REQUIRED BY THE RULING AND WRITTEN INTO THE CODE:\*\* under the Phase-2 cap the risk engine approved ZERO directional signals across 57 cohorts. That is the pre-change record. This amendment makes the approval rate look better BY CONSTRUCTION, so \*\*any future reading of approval counts MUST date-split on 2026-08-11 rather than pool across it.\*\* Recorded as making the record look better, which is the direction warranting the most scepticism.

&#x20;

★★ RULED 2026-08-11 — D-1 / D-2. PER-ACCOUNT, NOT CONSOLIDATED. RW. THE DEFECT: `main.py` `handle\_phase3a` passed `portfolios\[0] if portfolios else {}` into the risk engine — whichever account Schwab returned first. \*\*EVERY RISK DECISION IN 57 COHORTS WAS COMPUTED AGAINST ONE ARBITRARY ACCOUNT\*\* while the bot trades across Roth IRA, Individual and Scout. `print\_aggregate\_summary` and `build\_consolidated\_position` both walk every portfolio correctly; the risk engine alone did not. The rejection that killed NVDA and CBRS — "Too many open positions: 16 >= max 8" — cited a count describing a FRACTION of the portfolio. \*(Citation corrected 8/06 and restated here: the live site is in `handle\_phase3a`, NOT the identical line in `handle\_phase2`, which is dead code since `PHASE` is never 2. The dead site is deliberately left untouched.)\*

&#x20; \*\*RULING RATIONALE OF RECORD (RW):\*\* per-account is tighter and more accurate; consolidation invites misleading aggregates and turns grey the case where 5% of the combined value exceeds 5% of the account actually holding the position.

&#x20; \*\*DEMONSTRATED `\[V]`, and this pair is the whole argument:\*\* a $6,000 PM position is \*\*6% of Individual ($100,000) and REJECTED\*\*, and \*\*3% of Roth IRA ($200,000) and APPROVED\*\*. Identical dollars, opposite dispositions, decided entirely by which account holds it. Consolidation makes that distinction unreadable.

&#x20; \*\*TARGETING (RW):\*\* SELL is evaluated ONLY against accounts that HOLD the ticker — you cannot sell what is not there, and the Roth is never consulted for a name held solely in Individual. BUY is evaluated against EVERY account, because a new position could land in any of them and no account should be privileged by assumption.

&#x20; \*\*COLLAPSE (RW):\*\* the single `Risk:` token reads APPROVED when the signal is actionable in AT LEAST ONE account, and the per-account split is preserved VERBATIM in the reason rather than discarded — "actionable in the Roth but not the Individual" is the actual answer, and collapsing it to one bit destroys the very fact the ruling exists to expose. Engine-generated flags now carry their account (`\[Roth IRA] RISK-ENGINE: 16 open positions…`), because an unattributed "16 positions" is the same ambiguity D-1 just fixed.

&#x20;

★★ A NEW BREAK WAS NARROWLY AVOIDED IN FRESHLY-AUDITED TERRITORY, AND IT IS THE MOST INSTRUCTIVE ITEM OF THE SESSION. `main.py` joins log-line fields with `" | "`. The per-account reason is BUILT BY `risk\_engine`, and a `" | "` inside it would truncate every downstream parser's capture at the wrong point. The separator is `"; "` deliberately, and the audit now asserts the invariant directly. \*\*D-7 PROVED THE PARSERS TOLERATE A LONG MULTI-SENTENCE REASON; IT DID NOT PROVE THEY TOLERATE ONE CONTAINING THE FIELD DELIMITER\*\*, and this change must not have been the thing that found out. Related, and arriving one day after the note that warns about it: D-7's own fixture had to be UPDATED, because the shipped reason now carries the `PER-ACCOUNT:` suffix and the fixture would otherwise have been testing a string that no longer exists — precisely the "a fixture that approximates the string under test proves nothing about the string that ships" hazard D-7's docstring names.

&#x20;

★ 5b — TWO LABELS THAT ASSERTED WHAT THEY HAD NOT COMPUTED, BOTH DEMONSTRATED ON A REAL COHORT `\[V]`. (a) CONFIDENCE STATS counted EVERY row at >= 70 and called the total "actionable". On a watchlist that runs \~96% HOLD the modal member of that count is a HOLD — the model DECLINING to act, counted as actionable. On 2026-08-10 the split is \*\*1 directional against 4 total: a 4x overstatement.\*\* The guard is copied from `signal\_scan.py` so the two tools cannot disagree about the same number, and the unguarded total is RETAINED on its own line, because it is a real distributional fact and what was wrong was the label, not the arithmetic. (b) The section header read `ACTIONABLE SIGNALS (Risk Engine Approved)` while `classify\_directional\_signal` tests CONFIDENCE THRESHOLDS ONLY and never reads the risk engine's Decision — materially false, since the engine approved ZERO directional signals in 57 cohorts while any BUY at >= 70 still printed under that heading. \*\*DP-3C-o (iii) makes an uncomputed claim MORE dangerous, not less, because it would now sometimes be right.\*\*

&#x20;

★ 7 + 7b LANDED AS ONE EDIT, AND D-8 IS NOW GATED BY A HARNESS THAT WAS PROVEN TO FAIL. `PHASE = "3-C"` (L63) and the dispatch tuple (L553, now carrying `"3-C"`/`"3C"`) moved together. New `phase\_dispatch\_audit.py` reads `main.py`'s AST rather than importing it — no credentials, no API spend, no state mutation, because the pairing under test is STATIC. \*\*NEGATIVE-TESTED `\[V]`: reverting the tuple to reproduce D-8 exactly makes the audit exit 1\*\* and print the specific consequence — 24 API calls spent, ZERO `Signal JSON:` lines, `signal\_state.json` still advancing. A GATE THAT HAS NEVER BEEN SHOWN TO FAIL IS NOT A GATE. It also asserts every `PHASE in (...)` test agrees with the others, and that the logged bracket is built from `PHASE` itself so the constant and the log token cannot diverge. THIS CLOSES THE GAP THE RECORD NAMED: "the parser audit cannot see it because it never executes `main.py`".

&#x20;

★ TWO RULING AMBIGUITIES WERE CLARIFIED RATHER THAN INFERRED, AND THE SECOND ONE MATTERED. A ruling reading "remove the rule entirely" was implemented as DP-3C-o's WRITTEN form — demotion to a flag — and flagged for correction rather than executed as literally worded; the correction confirmed demotion was intended. A later message labelled "DP-3C-o ruling" restated what (ii) and (iii) DO without stating a decision, and was NOT treated as a ruling; the explicit ruling followed. \*\*RECORDED AS METHOD:\*\* on a change that alters whether the system approves a trade, an ambiguous restatement is not a ruling, and the cost of asking is one exchange against a risk-engine change made on an inferred mandate.

&#x20;

★ ERRORS MADE AND CORRECTED IN THIS SESSION, RECORDED AGAINST MYSELF. A test asserted a HARD verdict on a balance residual that was legitimately inside tolerance; a YoY expectation of +9.2% where the correct figure is +9.15%; a units expectation of integer percent where `parse\_log\_to\_tracker` correctly stores a fraction. \*\*ALL THREE WERE ERRORS IN THE TEST AND ALL THREE WERE FIXED IN THE TEST — none by moving the code or the threshold.\*\* A fourth: `main.py`'s import block is multi-line, and a patch asserted against the single-line form failed cleanly and wrote nothing, which is the behaviour to want from a failed patch.

&#x20;

★ KNOWN INCONSISTENCY, NOT BLOCKING, AND IT BECOMES VISIBLE FOR THE FIRST TIME TOMORROW. `print\_risk\_report` still sizes its `Shares : N shares recommended` line off `portfolios\[0]`, while the DECISION is now per-account. No order executes and the risk decision is unaffected, but if tomorrow produces the first approved BUY in 58 cohorts, the console will print a share count computed against an account that may not be the account the approval applies to. Recorded now, before it is seen, rather than explained after.

&#x20;

★ CHANGE ORDER — STATUS. LANDED: audit additions, N-1 (both routes), DP-3C-i, DP-3C-j, DP-3C-q, step 8, step 8b, D-7, D-3, 5b, 7+7b, D-1/D-2, DP-3C-o (i)(ii)(iii), `phase\_dispatch\_audit.py`. REMAINING BEFORE `EQUITY\_EDGAR=1`: \*\*one live run showing 24 `Signal JSON:` lines.\*\* Expect four visible differences tomorrow, all intended: `\[PHASE 3-C DRY RUN]`; era still `A-S1D1-B1` (EDGAR off); per-account reasons on any directional signal; and possibly THE FIRST NON-ZERO RISK-ENGINE APPROVALS IN 58 COHORTS. ROLLBACK IS ONE WORD — `PHASE` back to `"3-B"` — and the rest of the block is independent of it.

&#x20;

★ THE TWO 8/10 DATA-INTEGRITY FINDINGS REMAIN OPEN. AG 2026-06-26 close still 19.89 in three cells; GLD 2026-07-02 still carries two closes (378.13 / 379.13). Untouched this session; both still pending external verification against Schwab price history.

&#x20;

WS2 / G1 — 1 independent post-deploy episode of 4, unchanged; GM has none. INSUFFICIENT TEST CONDITIONS at the 3-B close; bar not lowered.

H4 — STAYS DEMOTED at 7/14 = 50.0%, 18 total. No DQ-conditional design work until two consecutive readings pass at n >= 12.

E4 endpoints are TABLE READS at their stated n. THE CLOCK HAS NOT STARTED. The 2026-08-03 shakedown cohort remains excluded from E4-1/2/3 but stays in the master, the registry, H4 and KEEP-70.

Standing: T1 (advisory-only, pre-execution, mandatory) · T3 (no band-ordering reliance, tool-enforced). Q1 guardrail RETIRED. T2 RETIRED. KEEP 70%. +/-3% HOLD band unchanged and NOT re-baselined. Blend (WS1) DESCOPED. CBRS excluded from EDGAR to the Q4 2026 Path-A review. Advisory-only - no orders.



\## 8/11 (Phase 3-C — CHANGE ORDER STEPS 8 AND 8b LANDED; N-1 CLOSED AND VERIFIED LIVE; DP-3C-q RULED; FULL 15-NAME FINANCIAL EXTRACT SWEEP) — ★★ N-1 IS FIXED, CONFIRMED AGAINST RTX'S OWN 8-K, AND THE FIX THAT PASSED ITS OWN TEST SUITE WAS NULLIFIED DOWNSTREAM BY A SECOND MECHANISM THAT NO TEST COVERED. `edgar\_client.py --ticker RTX` now renders Revenue \*\*$24.7B YoY +14.5%\*\* against RTX's own 2026-07-23 8-K text "Sales of $24.7 billion, up 14 percent versus prior year" `\[V]` — the tool agreeing with the filer's own earnings release, which is the only external check available and the one that matters. Diluted EPS reads the quarter's 1.57, not the half-year 3.08; Operating cash flow reads $5.4B \*\*carrying `\[6M YTD]`\*\*, which is the decisive tell, because that label fires only when the anchor is Q and the cumulative line is being marked as the exception. Balance-sheet lines unchanged. BEFORE THIS SESSION the same command rendered Revenue $46.8B unlabelled, EPS 3.08, and operating income $5.4B — the H1-cumulative figures under a "Q2 FY2026" header with nothing anywhere to say so.

&#x20;

★★ THE DEFECT WAS NOT AN RTX QUIRK. IT WAS THE MAJORITY OF THE COVERED SET. The 2026-08-11 sweep reports SPLIT-VOTE — headline-concept vote disagreeing with the universe-wide poll — on \*\*8 of the 15 covered names\*\* `\[V]`: AAPL, FTI, GLD, GM, JPM, PM, PWR, RTX. AAPL and GLD were voting `9M`; the other six `H`. Every one of those would have rendered a cumulative figure as the quarter, unlabelled, for as long as the treatment had been live. AAPL would have shown roughly nine-month revenue as a quarterly figure. This is recorded because the 8/10 entry framed N-1 as a defect observed on six named tickers; the correct statement is that it was a SYSTEMIC property of the anchor mechanism and the named tickers were simply the ones anyone had looked at.

&#x20;

★★ THE FINDING WORTH KEEPING IS THE SHAPE OF THE FAILURE, NOT THE DEFECT. `extract\_financials()` establishes its reporting-period anchor TWICE. Pass 1 votes among the \~6 HEADLINE concepts that can become rendered lines; the 2026-08-03 N-1 fix (duration-aware tie-break in `\_pick\_periods`, replacing a list-order-dependent `rows\[-1]`) lives there and works — traced live at 4-1 for Q `\[V]`. A SECOND mechanism then recomputed the anchor's duration bucket: the report-date override added 2026-08-02 for GLD called `\_modal\_flow\_bucket`, which polls \*\*every us-gaap concept in companyfacts\*\* — hundreds of footnote, segment and supplementary tags that never appear in the output. A 10-Q tags those year-to-date by convention. RTX's live feed at 2026-06-30 runs \*\*H:70 against Q:39\*\* `\[V]`, so the footnotes outvoted the income statement and the corrected headline vote was discarded one function later. THE FIX WAS CORRECT AND WAS BEING THROWN AWAY DOWNSTREAM. RECORDED AS A DEFECT CLASS: when a value is computed in one place and RE-computed in another, a unit test of the first is not evidence about the rendered output. Fixed by `\_headline\_flow\_bucket` — one vote per RENDERED LINE, each voting its shortest available duration, ties to the shortest bucket. The DATE override is untouched (it is what fixed GLD); `\_modal\_flow\_bucket` is retained as the fallback for the filer shape it was written for. Entry-counting was rejected during design and the rejection is recorded: counting ENTRIES rather than LINES gives RTX H:5/Q:4 and elects H, because every headline concept contributes both its quarter and its cumulative entry.

&#x20;

★★ RULED 2026-08-11 — DP-3C-q. TOTAL REVENUE SUPERSEDES THE CONTRACT-REVENUE COMPONENT, REVENUE LINE ONLY. For the Revenue line only, prefer `Revenues` when the filer tags it AT THE ANCHOR PERIOD and it exceeds the ASC 606 contract-revenue concept by more than 2%. EVIDENCE OF RECORD `\[V]`: GM tags `RevenueFromContractWithCustomerExcludingAssessedTax` at $43.762B for Q2 FY2026 and `Revenues` at \*\*$48.026B for the same period\*\*, and GM's own 8-K states "revenue of $48.0 billion" — the total matches the press release to 0.05% while the component sits 9.7% below it. ASC 606 contract revenue excludes GM Financial's interest and leasing income, so for any filer with a captive finance arm the first entry in the preference list is a COMPONENT rendered under the label "Revenue"; a model would have understated GM's top line by 9.7% and computed every margin off the wrong denominator. THE PERIOD WAS CORRECT — this is a THIRD defect class, distinct from N-1, and invisible to every internal-coherence check (GM's block passed BALANCE at 0.58% and SHARES at 925.5M implied). SCOPE DELIBERATELY NARROW: reordering `FINANCIAL\_CONCEPTS` outright would change what the model sees for all 15 names on evidence from one, so the swap fires only when the total is MATERIALLY LARGER and at the SAME period. Four of the nine regression fixtures are no-op cases (no `Revenues` tagged / within the 2% margin / a SMALLER `Revenues` / a larger `Revenues` at a DIFFERENT period — the last guarding against reintroducing the mixed-period defect). VERIFIED POST-RULING `\[V]`: GM moves to $48.026B and reads 8K-AGREE at 0.05%; the other 14 names' revenue figures are byte-identical to the pre-ruling sweep. TIMING: ruled before the E4 clock starts, so amending costs nothing — the DP-3C-g argument applied a third time.

&#x20;

★★ FOUR EXTERNAL CORROBORATIONS, WHICH IS THE ONLY EVIDENCE THAT SPEAKS TO TRUTH RATHER THAN COHERENCE `\[V]`. AAPL $109.417B against "revenue of $109.4 billion" (0.02%); RTX $24.708B against "Sales of $24.7 billion" (0.03%); GM $48.026B against "revenue of $48.0 billion" (0.05%); PWR $9.556997B against "Revenues of $9.6 Billion" (0.45%). THREE OF THE FOUR ARE SPLIT-VOTE NAMES — that is, drawn from exactly the population that was broken — so the fix is confirmed against filers' own words and not merely against itself. Independently: every implied share count in the sweep is plausible against the real companies (AAPL 14.747B, NVDA 24.402B, WMT 7.955B, MSFT 7.451B, JPM 2.747B, PM 1.565B, NKE 1.480B, RTX 1.362B, GM 925.5M, FTI 403M, PWR 152.5M), a figure nothing in the pipeline targets and which twelve names therefore corroborate by accident.

&#x20;

★ NEW INSTRUMENT — `xbrl\_sweep.py`, AND THE REASON IT CHECKS ACROSS TICKERS. A coherence-and-corroboration sweep over the covered set: HARD findings (block provably incoherent — mixed period, accounting identity, balance sheet) and FLAGs (needs a human read — SPLIT-VOTE, 8K-DISAGREE, CUMULATIVE-ANCHOR, SCOPE, YOY, XBRL-LAG, THIN, DEGRADED). 33 offline checks under `--selftest`. FINAL STATE OF THE COVERED SET: \*\*0 HARD findings across all 15 names\*\*, 19 FLAGs, all of which are informational — 8 SPLIT-VOTE (historical risk markers, now corrected), 8 extreme-YoY on small bases, 2 THIN (CORN and GLD, structurally, being commodity vehicles), 1 XBRL-LAG (DOW, a genuine SEC publication lag, already surfaced in the rendered block by its own PRIOR-period NOTE). THE STANDING LIMITATION IS STATED IN THE TOOL ITSELF: a clean sweep is evidence of COHERENCE, not a certificate of accuracy. Only the 8-K cross-check reaches outside the XBRL feed.

&#x20;

★ THE SWEEP'S OWN FIRST RUN PRODUCED THREE FALSE POSITIVES AND THEY WERE ALL MINE, NOT THE EXTRACT'S. Recorded because a new instrument's error rate is part of its provenance. (1) MSFT read as a 72.9% disagreement — comparing a 10-K ANNUAL figure ($331.839B) against a quarterly earnings 8-K ($90.0B); 3.69x is what four quarters should look like. Now reports 8K-ANNUAL, and flags the genuine failure instead: an "annual" revenue NOT materially above one quarter. (2) DOW read as a 23.5% disagreement while ALSO carrying XBRL-LAG — the block is Q1 and the 8-K is the Q2 release, different quarters by construction. Now reports 8K-NOT-COMPARABLE rather than double-counting the lag. (3) The SCOPE check fired 15 times of which \*\*14 were correct-by-design pairs\*\* — `LongTermDebtNoncurrent` vs `LongTermDebt` (the current portion, reported separately), `NetIncomeLoss` vs `ProfitLoss` (noncontrolling interests; the parent figure is the EPS numerator), `StockholdersEquity` vs the including-NCI concept (same). A check wrong 14 times in 15 does not get read, and an unread check is worse than none because it looks like coverage. Reclassified to SCOPE-BY-DESIGN (informational, difference still reported) with the four pairs enumerated rather than suppressed by threshold; only GM's `Revenues` survived as a genuine finding.

&#x20;

★ A TOLERANCE BECAME AN IDENTITY. The balance check originally allowed a 5% band because `StockholdersEquity` excludes noncontrolling interests. The by-design triage showed the "tolerance" had been MEASURING NCI all along: GM's equity-concept delta is $1.641B and its balance residual was 0.58% — the same number. The check now derives NCI from the two tagged equity concepts and verifies `assets = liabilities + equity + NCI` exactly. RESULT `\[V]`: residual \*\*exactly 0\*\* on GM ($282.742B of assets), FTI, PM and PWR; RTX carries a residual of $28M on $173.972B (0.016%), the only non-zero one, plausibly redeemable/temporary equity which sits outside both concepts — noted as an observation, not a concern, and NOT asserted without checking. Names not tagging the NCI concept (AAPL, JPM, MSFT, NVDA, SND) close to 0.00% and are reported as tolerated-not-verified, which is the honest distinction.

&#x20;

★ THE CACHE EPISODE IS A SEPARATE, REAL, AND SEPARATELY-RECORDED BUG — AND THE FIRST DIAGNOSIS OF IT WAS WRONG. `extract\_financials()` caches derived output keyed on the periodic ACCESSION, guarded by `EXTRACT\_SCHEMA`. The N-1 and DP-3C-j edits changed extraction behaviour without bumping it. That is the FOURTH occurrence of a pattern already documented in a standing ANALYST NOTE directly above the constant ("\*This is the THIRD time a cache has masked a working fix in this build\*"), repeated anyway, in the same file, by the same edit the note was warning about. Bumped 6 -> 7. \*\*BUT THE 7 RECOMPUTE STILL RENDERED $46.8B\*\* `\[V]` — cache mtime and `"schema": 7` both confirmed the recompute happened. So the cache was masking NOTHING; it was a genuine hygiene defect whose repair is what made the real defect visible instead of leaving it behind a plausible "probably just stale" story. RECORDED BECAUSE THE WRONG DIAGNOSIS WAS STATED WITH CONFIDENCE BEFORE THE SECOND RUN FALSIFIED IT. Now at `EXTRACT\_SCHEMA = 9` (8 -> 9 for DP-3C-q, bumped in the SAME edit as the behaviour change). Invalidation is now visible in console rather than silent.

&#x20;

★ WHAT ACTUALLY CAUGHT EACH DEFECT, AND NOTHING ELSE WOULD HAVE. N-1's tie-break: reading the source. The anchor override: a throwaway diagnostic (`diag\_anchor.py`, not committed) printing the Pass-1 tally against the override's vote on live data — reading the source had produced a CONFIDENT AND WRONG first answer. GM's concept scope: the 8-K cross-check, and only that. THE INTERNAL-COHERENCE CHECKS CAUGHT NONE OF THE THREE. Both green harnesses passed throughout. Stated as a method finding: internal checks catch corruption; only external corroboration catches a block that is uniformly, plausibly wrong.

&#x20;

★ PROCESS FAILURE, RECORDED AGAINST MYSELF. Steps 8 and 8b were marked COMPLETE on the strength of two green harnesses before any live check had been run. N-1 was in fact still live at that moment. THE HARNESSES WERE NOT AT FAULT AND THEIR PASSES WERE NOT FALSE — they tested what they covered, correctly; the error was treating their scope as the system's scope. STANDING RULE PROPOSED: no EDGAR extraction change is recorded as complete until a live `--ticker` render on an affected name has been read and reconciled against an external figure — the filer's own 8-K where one exists. Green harnesses gate DEPLOYMENT; a live render gates the word "fixed". A second, smaller instance the same day: a sweep test asserted a HARD verdict on a balance residual that was legitimately inside tolerance, and one asserted a YoY of +9.2% where the correct figure is +9.15%. Both were errors in the TEST, fixed in the test rather than by moving the code or the threshold.

&#x20;

★ ALSO LANDED THIS SESSION. `signal\_scan.py` is now the THIRD parser under `edgar\_parser\_audit.py` (7 new checks: 24/24 rows, E tag on every row, "no filings" landing on exactly the non-EDGAR names, covered names never reading "no filings", the synthetic log exercising all three DP-3C-j `fin=` states, and the control log reading as UNTAGGED rather than as a degenerate all-"no filings" run) — closing the gap the 8/10 entry named, and closing it BEFORE the tag was amended rather than after. DP-3C-i (8k= and form4= carry `@date`) and DP-3C-j (`fin=` always one of `N@period` / `degraded` / `none`) are implemented and tag-verified. The E4-2 VOLATILITY-TIER TABLE IS BUILT AND FROZEN (step 8b) — 15 covered tickers, terciles of 5, median |+5d| from all resolved rows as of 2026-08-10: LOW {JPM 1.834%, GLD 1.931%, CORN 1.990%, RTX 2.021%, WMT 2.559%}, MID {GM 2.592%, PM 3.188%, FTI 3.201%, PWR 3.343%, NVDA 3.595%}, HIGH {DOW 3.598%, NKE 3.598%, AAPL 3.779%, MSFT 3.910%, SND 5.517%}. The MID/HIGH boundary is a NEAR-TIE (NVDA 3.595% vs DOW/NKE 3.598%, a 0.003pp gap against a next-closest gap of 0.181pp) — flagged AT FREEZE TIME as a sensitivity check rather than re-cut, per DP-3C-n's freeze rule. The DP-3C-l/m/n amendment pack is APPLIED; `Phase3C\_E4\_Endpoint\_PreRegistration\_v1.md` is now v1.1, which closes the "three rulings live only in the notes" item. \*\*DP-3C-q IS NOT YET IN THAT DOCUMENT\*\* — it changes what the model receives, as DP-3C-g did, and belongs in §5 by the same argument; entered here first and OWED there.

&#x20;

★ CHANGE ORDER — REMAINING, AND EDGAR=1 IS STILL NOT SAFE. LANDED: the audit additions, N-1 (both routes), DP-3C-i, DP-3C-j, DP-3C-q, step 8 (both harnesses exit 0), step 8b (vol-tier table frozen). NOT LANDED AND STILL GATING: (7) the `\[PHASE 3-B DRY RUN]` token AND (7b, BINDING, SAME EDIT) the L544 dispatch extension to accept "3-C"/"3C" — D-8 stands unchanged: setting `PHASE` without it makes every ticker fall to a logged error, emits ZERO signal lines, still spends 24 API calls and STILL ADVANCES `signal\_state.json`, and the parser audit cannot see it because it never executes `main.py`; verification requires one live run showing 24 `Signal JSON:` lines. Also outstanding: (D-3) guard CHECK 6 to BUY-only; (5b) the `analyze\_log.classify\_directional\_signal` one-liner plus the CONFIDENCE STATS ">= 70% (actionable)" label plus the directional guard copied from `signal\_scan.py`; D-7's approval-path audit; D-1/D-2; DP-3C-o and the cap. THE CONTROL WINDOW THEREFORE CONTINUES as a CONSEQUENCE of unlanded work, and it no longer continues because N-1 is unfixed.

&#x20;

★ THE TWO 8/10 DATA-INTEGRITY FINDINGS REMAIN OPEN. AG 2026-06-26 close still 19.89 in three cells; GLD 2026-07-02 still carries two closes (378.13 / 379.13). Neither touched this session; both still pending external verification against Schwab price history, per the standing rule against inferring a figure from the surrounding series.

&#x20;

WS2 / G1 — 1 independent post-deploy episode of 4, unchanged; GM has none. INSUFFICIENT TEST CONDITIONS at the 3-B close; bar not lowered.

H4 — STAYS DEMOTED at 7/14 = 50.0%, 18 total. No DQ-conditional design work until two consecutive readings pass at n >= 12.

E4 endpoints are TABLE READS at their stated n. THE CLOCK HAS NOT STARTED. The 2026-08-03 shakedown cohort remains excluded from E4-1/2/3 but stays in the master, the registry, H4 and KEEP-70.

Standing: T1 (advisory-only, pre-execution, mandatory) · T3 (no band-ordering reliance, tool-enforced). Q1 guardrail RETIRED. T2 RETIRED. KEEP 70%. +/-3% HOLD band unchanged and NOT re-baselined. Blend (WS1) DESCOPED. CBRS excluded from EDGAR to the Q4 2026 Path-A review. Advisory-only - no orders.


## 8/11 (Phase 3-C — DAILY COHORT REVIEW: CROSS-CHECK CLEAN; DP-3C-l LEDGER'S SECOND EPISODE RESOLVES AND CLOSES ON THE SAME SESSION; EQUITY_EDGAR CORRECTLY STILL UNSET) — Closing review for `signals_2026-08-11.log`, `claude_equity_bot_tracker.xlsx` and `tracker_with_registry.xlsx` as supplied. This is a REVIEW OF THE DAILY COHORT ONLY — it does not touch the change-order work recorded earlier today (N-1 fix, DP-3C-q, DP-3C-o, D-1/D-2, xbrl_sweep.py), which stands as written above.

★ CROSS-CHECK 24/24 [V] — reproduced independently from the log JSON against the master (signal, confidence, data quality, Price@Signal), all 24 tickers byte/percent-exact, zero mismatches. Era `A-S1D1-B1`, `[PHASE 3-B DRY RUN]` on every line, ZERO `E[...]` tags, no `[EDGAR] prefetch` line, no budget warning. THIS IS CORRECT AND NOT A DEFECT: the earlier 8/11 entry states change-order steps 7 and 7b (the phase token and the L544 dispatch extension, bound together per D-8) had not landed as of that entry's close, and that `EQUITY_EDGAR` "stays unset until [a live verification] run is read." Today's run is consistent with that state and is NOT itself the live-verification run the change order is waiting on — `PHASE` is still `"3-B"` throughout, so steps 7/7b remain the one item gating `EQUITY_EDGAR=1`.

★ COHORT PROFILE. 22 HOLD + 2 BUY (NVDA 68%, GLD 68%), both REJECTED on confidence — raw/base confidence 68% < the 70% gate, checked at CHECK 5 before CHECK 6 is ever reached, so neither row exercises today's freshly-ruled DP-3C-o (CHECK 6 demotion) or D-1/D-2 (per-account scope) in practice; no observational evidence either way from today's cohort. Blend discounted both (blend_op 65 and 62 respectively) with no gate-flip consequence, consistent with G2's shadow-parallel non-effect. DQ 17 HIGH / 7 MEDIUM. Confidence mean 55.75, median 60.0, sd(pop) 12.00%, range 33–72. `regime_score` uniform at −0.576 across all 24 names as designed — deepening negative for a third consecutive reviewed session (+0.009 on 8/03 → −0.181 on 8/06 → −0.546 on 8/07 → −0.576 today; 8/10 has no reviewed reading, see below). D1 reconciles clean, 24/24, ZERO damped rows — no adverse move ≥5% anywhere in the cohort (largest adverse trail was NKE −2.41%). Accounts Roth IRA 7 / Individual 6 / both 6 / Scout 5, no "Unknown." Totals now 1,411 rows, 59 cohorts. Run window 09:57:28–10:02:23 CST (first to last Claude call), +27 minutes past the 9:30 canonical — tagged per the standing Px@signal-timing practice; smaller than 8/04's +98min or 8/06's +39min but still off-canonical, so today's quote carries the same quote-vs-close variance the record has flagged since 8/05. Session cost 37,248 input / 10,263 output tokens (plus 796/1,011 for `ticker_suggester.py`, excluded from the cost line as usual) — within noise of the established control-window baseline (37,065–37,107 on 8/05–8/07).

★ RESOLUTIONS COMPLETE AT ALL THREE HORIZONS, ZERO UNRESOLVED-BUT-DUE [V], recomputed from the Price columns: 8/04 @+5d = 16/24 = 66.7%, mean +2.50%, sd(pop) 3.86%, 18/24 up, 8 HOLD breaches (7 UP / 1 DOWN), zero directional misses — NVDA's lone BUY resolved 210.47 → 217.50 = +3.34%, correct. THIS IS THE STRONGEST, LOWEST-DISPERSION +5d COHORT OF THE CONTROL WINDOW SO FAR, and it is the calm-tape counterpoint the drift/dispersion mechanism (established 8/06–8/07) predicts: 8 breaches at sd 3.86% is a materially calmer tape than 7/28's or 7/14's. 7/28 @+10d = 7/24 = 29.2%, mean +5.31%, sd 10.30%, 17/24 up, 17 breaches (13 UP / 4 DOWN) — the cohort mean itself clears the ±3% band, so the drift mechanism is doing the work again; movers CBRS +31.4%, MSFT +26.8%, AG +22.4%. 7/14 @+20d = 10/24 = 41.7%, mean +4.76%, sd 8.35%, 17/24 up, 14 breaches (10 UP / 4 DOWN); movers MSFT +30.2%, CBRS +21.6%, GM +16.4%. None of these three add new information to the horizon-breach-rate gradient already established; not recomputed in full this session.

★★ DP-3C-l / DP-3C-m LEDGER — EPISODE 2 (NVDA, OPENED 2026-08-04) RESOLVES ITS +5d OUTCOME AND CLOSES, BOTH ON TODAY'S SESSION, FOR TWO UNRELATED REASONS [V]. First, NVDA's 8/04 price@signal was 210.47 and the master's +5d close for that row is 217.50 → return +3.34%, correct under the sign test (BUY right if return > 0) → YES. Second, and separately, today's own NVDA signal is BUY at 68% — below its own 70% gate — and DP-3C-m rules an episode "ENDS when...[a name] falls below its gate for at least one session," so episode 2 closes as of today regardless of the resolution. The confidence path across the episode was 72 (8/04) → 74 → 72 → 72 → 70 (8/10) → 68 (8/11, below gate) — five sessions of unbroken gate clearance, the longest run in the ledger's history, closing exactly as it resolves. THE LEDGER NOW STANDS AT 2 OF 2 EPISODES FULLY RESOLVED: CBRS SELL 6/26 → NO; NVDA BUY 8/04 → YES. PER DP-3C-l's OWN STANDARD ("NONE") AND THE 8/04 PRE-COMMITMENT, NO DISPOSITION IS READ FROM n=2 — one right, one wrong, and the ruling that opened the ledger anticipated exactly this outcome shape and pre-committed not to score it. Supply recomputed: coalesced basis 2 episodes / 59 cohorts = 0.0339/session, essentially unchanged from 0.0364 at n=55 and still inside DP-3C-l's ×3 stress band (0.111/session) — INSUFFICIENT TEST CONDITIONS stands, unrevised. THIS CLOSES THE 8/04 UPCOMING ACTION ITEM ("record NVDA's 2026-08-11 +5d outcome in the ledger when it resolves, and do NOT read anything from n=2") — done, and the caveat honored. Separately: today's own NVDA (68%, HIGH DQ) and GLD (68%, HIGH DQ) are both near-misses, not gate clearances, and both enter the KEEP-70 registry rather than the gate-cleared ledger; no new episode opens.

★ KEEP-70 / H4 / WS2-G1, READ FROM THE FRESHLY REGENERATED REPORT COPY (`tracker_with_registry.xlsx`, generator timestamp 2026-08-11 16:16 — already incorporates today's paste and today's resolutions) [V], OBSERVED ONLY PER §6, NOT USED AS A CROSS-CHECK INPUT. KEEP-70 now reads 14/33 = 42.4% combined across the LOCKED (4/7) and EXTENDED (10/26) sub-cohorts — comfortably under the 50% line, SUPPORTED. FLAGGED RATHER THAN SILENTLY SPLICED: this combined figure is not directly comparable to the "13/32 = 40.6%" the notes carried through 8/07 — that figure was an EXTENDED-only reading at an earlier n, and whoever reads this sequence next should confirm which population each entry used before treating it as one unbroken series. Registry total 40 near-miss BUYs (33 extended + 7 locked), up from 37 on 8/07: GLD ×2 (8/10, 8/11) and NVDA ×1 (8/11) — NVDA's 8/10 row at exactly 70% correctly does NOT add to this count, since it is a gate clearance (the ledger episode above), not a near-miss. H4 (HIGH-DQ near-miss) now reads 7/14 = 50.0%, 20 total (up from 18) — today's two HIGH-DQ near-misses (NVDA, GLD) both land in the total, neither yet resolved at +5d. STAYS DEMOTED; the tool's own label reads "demoted (n ok, rate FAILING)" against the n≥12-on-two-consecutive-readings bar, correctly worded — unlike the WS1/G2 row below. WS2/G1: WMT 1 post-deploy episode in 26 sessions (last episode 7/23, 13 sessions ago), GM 0 post-deploy in 26 sessions ("NO TEST CASES YET"). Unchanged; INSUFFICIENT TEST CONDITIONS stands from the 3-B close, bar not lowered.

★ STILL-OPEN DEFECT, RAISED AGAIN, NOT YET FIXED. The report copy's Monitor Strip WS1/G2 row still prints a live acceptance bar ("net ≥ 0 & confirm > discount, ≥5 cohorts") and a state of "on track" for a gate that has carried DESCOPE since 2026-07-31 — first flagged 8/05 and unaddressed through at least three regenerations since. The underlying shadow-parallel blend has also logged a SECOND gate-flip since descope (2026-08-03, NVDA base 68/blend 70, blend favorable +5.44% at +5d) that the strip now folds into a "net +1, confirm 100% (n=2)" reading — a number with nowhere to attach, because there is no live criterion left to move it against. Relabel to DESCOPED with the T-G2-a/b/c triggers, as recorded three times already.

★ A SECOND, DISTINCT INSTANCE OF THE SAME DEFECT CLASS, FOUND THIS SESSION IN THE DASHBOARD TAB RATHER THAN A PYTHON HARNESS. The report copy's Dashboard prints "# Signals ≥ 70% (actionable): 40" — this is a WORKBOOK FORMULA, not `analyze_log.py`'s CONFIDENCE STATS line, so today's 5b fix (Python-side, landed earlier this session per the change-order entry above) does not touch it. On a watchlist that is ~97% HOLD (1,363/1,411), the true directional-actionable count is a small fraction of 40; the same "counts every row ≥70% including HOLDs" defect that was fixed in one instrument survives, unfixed, in a second. New item, not assumed closed by the code-side fix.

★ E4-1 CONTROL-ARM CHECK, ONE MORE DATA POINT AGAINST THE ESTABLISHED ENVELOPE [V]. DQ mix held 17 HIGH / 7 MEDIUM (8/10) → 17 HIGH / 7 MEDIUM (8/11) on the aggregate, net change 0, but six names churned underneath it (AAPL, AIQ, DOW, GM, PWR, NVDA all flipped) — TIES THE MAXIMUM CHURN OBSERVED IN THE ERA (8/07's six), again with zero net movement, now the SECOND time maximum churn has coincided with zero net shift. One T-C dark/control name moved (AIQ, HIGH→MEDIUM) — a single-session move, inside the noise floor already established across the four-session control window (0–4 T-C moves/session) and not itself a finding. No revision to E4-1's |ΔHIGH| > 3 threshold or the T-C tolerance is warranted from one more session.

★ THE 8/10 GAP REMAINS OPEN, AND THIS SESSION DOES NOT CLOSE IT. `signals_2026-08-10.log` was not part of the file set supplied for this review. The master's own 8/10 rows are visible and were used above (the E4-1 churn check, the near-miss registry, the ledger's episode path), but the 8/10 RISK-ENGINE REASON strings, D1 behavior and the pre-DP-3C-o CHECK 6 disposition for that date cannot be verified without the log itself. Per G4 the cross-check streak must be clean through the exit review; 8/10 is still an unreconciled gap in that streak and should be closed with `log_tracker_crosscheck.py` and `outcome_sanity.py` against the actual 8/10 log before the streak is next cited as clean.

★ FORMULA CACHES CLEAN ON BOTH FILES [V]. Master: 0 of 1,291 rows carrying a +5d close show a blank cached Return+5d. Report copy: same, 0 of 1,291 — the post-run open-in-Excel step was followed on both files supplied.

WS2 / G1 — 1 independent post-deploy episode of 4, unchanged; GM has none. INSUFFICIENT TEST CONDITIONS at the 3-B close; bar not lowered.
H4 — STAYS DEMOTED at 7/14 = 50.0%, 20 total. No DQ-conditional design work until two consecutive readings pass at n ≥ 12.
KEEP-70 — SUPPORTED at 14/33 = 42.4% combined (locked 4/7, extended 10/26). Registry 40.
DP-3C-l/m gate-cleared ledger — 2 of 2 episodes fully resolved (CBRS NO, NVDA YES); coalesced rate 0.0339/session; standard NONE, INSUFFICIENT TEST CONDITIONS stands, no disposition read from n=2.
E4 endpoints are TABLE READS at their stated n. THE CLOCK HAS NOT STARTED. The 2026-08-03 shakedown cohort remains excluded from E4-1/2/3 but stays in the master, the registry, H4 and KEEP-70.
Standing: T1 (advisory-only, pre-execution, mandatory) · T3 (no band-ordering reliance, tool-enforced). Q1 guardrail RETIRED. T2 RETIRED. ±3% HOLD band unchanged and NOT re-baselined. Blend (WS1) DESCOPED. CBRS excluded from EDGAR to the Q4 2026 Path-A review. Advisory-only · no orders.


## 8/12 (Phase 3-C — CHANGE-ORDER LIVE VERIFICATION PASSED; AND THE DIRECTIONAL-SCARCITY FINDING IS RE-DIAGNOSED: IT IS NOT THE SYSTEM'S NATURE, IT IS OWNERSHIP) — ★★ D-8 IS CLOSED ON LIVE EVIDENCE RATHER THAN ON A HARNESS. The 09:32 canonical run emitted 24 `Signal JSON:` lines under `[PHASE 3-C DRY RUN]`, which is the one thing no audit could establish. Separately and more importantly, a decomposition never previously run shows that DIRECTIONAL OUTPUT IS 84x MORE LIKELY ON A NAME THE PORTFOLIO DOES NOT HOLD, which re-scopes three conclusions already in the record.

**SCOPE OF THIS ENTRY, STATED FIRST.** This is a VALIDATION AND FINDINGS session, NOT a daily cohort review. **NO LOG-TO-MASTER CROSS-CHECK WAS RUN FOR 8/12** — the run was read from console output supplied to the review; `logs\signals_2026-08-12.log` was not supplied as a file and the master had not yet received the paste. Today's 24/24 reconciliation, the resolutions due today (+5d for 8/05, +10d for 7/29, +20d for 7/15) and the recalc check are all UNVERIFIED HERE. G4 requires the cross-check streak clean THROUGH the exit review, so 8/12 joins 8/10 as an open item in that streak. Figures below that come from the master are computed against the master as of 8/11 (1,411 rows, 59 cohorts) and are labelled as such.

★★ THE FOUR PRE-COMMITTED VALIDATION CHECKS, ALL PASS `[V]` FROM CONSOLE OUTPUT. These were written down on 8/11 BEFORE the run, which is the only reason reading them today is a test rather than a description. (1) PHASE TOKEN — `[PHASE 3-C DRY RUN]` on all 24 lines, banner "Phase 3-C", footer "PHASE 3-C (advisory-only)". (2) TWENTY-FOUR SIGNAL LINES — `analyze_log` 24 analyzed, `parse_log_to_tracker` 24 parsed, `paste_today.tsv` 24 rows; three independent parsers agreeing is the assertion, not any one of them. (3) ERA UNCHANGED — `A-S1D1-B1` in every JSON, no `[EDGAR] prefetch` line, no `E[...]` tags, no budget warning; EDGAR correctly still OFF. (4) PER-ACCOUNT REASONS — `PER-ACCOUNT: Roth IRA=...; Individual=...` on all 24. **D-8'S SIGNATURE WAS ZERO SIGNAL LINES WITH A NORMAL-LOOKING COMPLETION AND `signal_state.json` ADVANCING ANYWAY. Twenty-four lines is the falsification.** The L63 constant and the L553 dispatch tuple move together in production, not merely in `phase_dispatch_audit.py`'s AST read.

★ TWO THINGS VERIFIED LIVE THAT WERE PREVIOUSLY SYNTHETIC-ONLY. The `" | "` DELIMITER INVARIANT HELD AGAINST A REAL STRING: NVDA and GLD's rejection reason is four clauses across two sentences carrying colons, semicolons and an em dash — "Rejected in every account. PER-ACCOUNT: Roth IRA=REJECTED; Individual=REJECTED. Roth IRA: BUY confidence too low: 68% < required 70%; Individual: ..." — and every `H1`/`S1`/`D`/`B` tag DOWNSTREAM of it still parsed on both rows. That is the core of D-7's hazard (a long reason silently truncating tag capture, with a missing tag reading as an absent feature rather than a parse failure) tested against production text. The `PENDING HUMAN APPROVAL` variant specifically remains fixture-only. And 5b LANDED VISIBLY: `>= 70% DIRECTIONAL (actionable) : 0` now sits beside `>= 70% any signal, incl. HOLD : 2`, the ACTIONABLE header explicitly disclaims consulting the risk engine, and MSFT at 70 and FTI at 72 — both HOLDs — are correctly excluded from the near-miss list while still counting in the unguarded total.

★★ WHAT THE RUN DID NOT TEST, RECORDED SO IT IS NOT MISTAKEN FOR COVERAGE. No directional signal cleared CHECK 5 — NVDA and GLD both rejected at 68% — and CHECK 5 precedes CHECK 6. **DP-3C-o (iii)'s demotion of CHECK 6 to a reported flag, (ii)'s new CHECK 6b `MAX_POSITION_PCT` enforcement, and the approval path all remain UNEXERCISED IN PRODUCTION.** The plumbing is verified; the new risk logic is not. Related and unfixed: the Active Rules banner still prints "Max open positions : 8" in the same list and the same grammar as rules that actually gate, though it now only flags — the same label-versus-behaviour shape as D-6, and it becomes MORE misleading under DP-3C-o (iii), not less, because the rule is now sometimes right about nothing.

★ RUN PROFILE `[V]` FROM CONSOLE. Window 09:32:35 to 09:38:11 CST, first Claude call 09:32:56 — CANONICAL at +2.5 minutes, the best timing since 8/07 and the second on-time run in the era after offsets of +98, +23, +39 and +27 minutes. 22 HOLD + 2 BUY (NVDA 68, GLD 68, both REJECTED on confidence in every account). DQ 19 HIGH / 5 MEDIUM. Confidence mean 56.2%, range 33-72; bands 0-39 (1), 40-59 (11), 60-69 (10), 70-79 (2), 80+ (0). Risk engine APPROVED 22 / REJECTED 2. D1 reconciles with ZERO damped rows — no adverse trailing move anywhere in the cohort. `regime_score` uniform at −0.836, DEEPENING FOR A FIFTH CONSECUTIVE REVIEWED SESSION (+0.009 on 8/03, −0.181 on 8/06, −0.546 on 8/07, −0.576 on 8/11, −0.836 today) as gold's run drives the SPY−GLD overlay. Blend discounted both directional rows again — NVDA 68 to 66, GLD 68 to 59, the largest single-row blend discount in the record — with no operational consequence, since both miss the 70% gate either way. Session cost 36,845 in / 10,225 out, $0.2639, inside the control-window baseline of 37,056-37,248.

★ PORTFOLIO COMPOSITION MOVED, AND IT MATTERS NOW IN A WAY IT DID NOT BEFORE `[V]`. Roth IRA 16 positions / Individual 18 / 34 total, against Roth 16 / Individual 20 / 36 recorded on 8/05. GM and AIQ are Roth-only today; both read `Roth IRA,Individual` on 8/11. Held equity union is unchanged at 19 and the run's own "19 held + 5 scouting" line agrees. Recorded because D-1/D-2 landed yesterday and the risk engine now evaluates EVERY account rather than `portfolios[0]`, so account composition became load-bearing on 8/11 and this is the first session where a change in it could alter a disposition.

★ NEW DEFECT, SMALL AND REAL, FOUND ON THE FIRST LIVE RUN OF THE AMENDED ANALYZER. `analyze_log.py` does not unicode-decode the reasoning field before truncating it for the LOW-CONFIDENCE HOLDS section: XLU renders `($43.13–$43.96)` as a literal escape sequence. XLU is the only row whose truncation window contained a non-ASCII character, which is why it is the only visible instance rather than the only occurrence. It lands in `logs\summary_history.txt`, a durable artifact that nothing reconciles against the master — the same file the 8/05 entry flagged for false ACTIONABLE lines. Cosmetic in effect, but it is the fourteenth-ish instance of a tool emitting a representation it did not compute, and it surfaced exactly where the standing lesson says it would: the first live run of a changed component.

★★ RECORD DEFECT — THE TWO 8/11 ENTRIES ARE SPLICED IN REVERSE CHRONOLOGICAL ORDER, AND THE APPARENT CONTRADICTION IS A SEQUENCING ARTIFACT RATHER THAN A DISAGREEMENT. The file carries "CHANGE ORDER, SESSION 2 ... EVERY REMAINING STEP LANDED EXCEPT THE LIVE VERIFICATION" BEFORE "CHANGE ORDER STEPS 8 AND 8b LANDED; N-1 CLOSED AND VERIFIED LIVE; DP-3C-q RULED". The second describes SESSION 1 — the label "Session 2" in the first entry is itself the evidence — so the later session is filed above the earlier one. The visible consequence is that the file states 7 and 7b as LANDED in one entry and "NOT LANDED AND STILL GATING" in the next, with neither citing the other, which reads as an unreconciled contradiction on the one step that gated go-live. **TODAY'S RUN SETTLES IT EMPIRICALLY: the phase token is 3-C and the dispatch works, so 7/7b had in fact landed, and Session 2's status line was the accurate one.** THE ENTRIES ARE NOT REWRITTEN, per the standing rule. The ordering is the thing to fix, and it is the THIRD instance of a record-structure defect after the two-Upcoming-blocks escape recurring twice — same root cause, the paste step rather than the content. Splice in chronological order and stamp each same-day entry with its session, not just its date.

★★★ THE DIRECTIONAL-SCARCITY FINDING IS RE-DIAGNOSED. IT IS NOT "A HOLD-DOMINATED SYSTEM"; IT IS OWNERSHIP, AND THE DECOMPOSITION HAS NEVER BEEN RUN BEFORE `[V]` (master as of 8/11, 1,411 rows, 59 cohorts). **SCOUT rows (names not held): 292, of which 44 directional = 15.07%. HELD rows: 1,119, of which 2 directional = 0.18%. An 84x difference.** The two held-name directional signals in the ENTIRE record are SCHD BUY 2026-05-21 at conf 68 (Roth IRA) and CBRS SELL 2026-06-26 at conf 68 (Individual) — both inside the first six weeks, and nothing since. **THIS IS NOT A CONFIDENCE-DISTRIBUTION EFFECT, WHICH IS WHAT RULES OUT THE OBVIOUS EXPLANATION** `[V]`: mean confidence is SCOUT 53.3% against HELD 52.9%, median 52% in both, and held names clear 70% MORE often — 35 times against 5 — with the record's single highest confidence, FTI at 76%, belonging to a held name that has produced ZERO directional signals in 59 rows. MSFT, GM, JPM, PM and RTX have each peaked at 72% with zero directional output. Meanwhile NVDA runs 32 directional signals in 59 rows = 54.2%, GLD 13.6%, VTI 5.2%. **THE MODEL IS NOT LESS CERTAIN ABOUT NAMES THE PORTFOLIO OWNS. Conviction on a held name expresses as HOLD; the same conviction on an unheld name expresses as BUY. Ownership changes what the signal MEANS, not how sure the model is.** The mechanism is visible in the prompt: held names carry cost basis, unrealized P&L, per-account tax treatment and a required `position_note`, and the reasoning text cites tax framing almost every session ("tax-free growth context makes holding low-cost"; "gains would be taxable so threshold for trimming should be..."). The held prompt asks SHOULD YOU DISTURB THIS POSITION; the scout prompt asks IS THIS ATTRACTIVE. Only one of those has a directional answer. ALSO `[V]`: eight held names — AIQ, CORN, DOW, NKE, NTR, SND, WMT, XLU — have never reached 65% on ANY signal type, so they cannot clear a gate in either direction.

★★ THREE RECORDED CONCLUSIONS ARE RE-SCOPED BY THE ABOVE, AND THIS IS A CORRECTION OF READING RATHER THAN OF ARITHMETIC. (i) **Closeout memo section 4.2 generalises too far.** It states that "in a HOLD-dominated advisory system, any mechanism gated on directional output will be starved." The accurate statement is narrower and testable: HELD names emit directional signals at 0.18%, while the scout subset runs at 15.07%, which is a workable rate. The scarcity has a named cause; it is not the system's nature. The DISPOSITIONS that rested on scarcity — G1 and G2 both INSUFFICIENT/DESCOPE — are UNAFFECTED, because those failed on tracer-episode and gate-flip supply specifically. It is the generalisation that needs the qualifier. (ii) **THE 8/07 ENTRY MISREAD ITS OWN EVIDENCE, AND I AM CORRECTING IT AGAINST MY OWN PRIOR READING.** That entry recorded QQQ entering the near-miss registry as "THE FIRST MOVEMENT AGAINST THE SINGLE-NAME STRUCTURAL CONSTRAINT that underwrote G2's failure, DP-7 and DP-10's collision, and DP-3C-l's starvation forecast." QQQ IS A SCOUT NAME. The registry broadened WITHIN the scout set; the held set has not moved since 2026-06-26. The entry's caution — "it is three observations and nothing is read from it" — was right, but for a weaker reason than the one available. The 8/07 entry is NOT edited. (iii) **KEEP-70, H4 and the DP-3C-l ledger are effectively measuring FIVE tickers, not twenty-four** — SPY, QQQ, VTI, NVDA, GLD — which is a tighter and more structural limitation than the "78% NVDA" concentration already on the record, and it belongs beside that figure wherever it is cited.

★★ RAISED AND NOT RULED — DP-3C-s. IS THE HELD/SCOUT DIRECTIONAL ASYMMETRY INTENDED? Two dispositions are available and the choice is a design ruling, not a defect report. **(A) INTENDED — document it as a scope property.** Asymmetric treatment of existing versus new positions is defensible on its own terms: taxes and transaction costs genuinely raise the bar for churning something already owned, and a system that fires SELL signals casually on held positions would be worse, not better. If this is the ruling, it must be WRITTEN DOWN as a property of the instrument, and every directional-supply figure in the record must be reported held/scout-split rather than pooled. **(B) UNINTENDED — a prompt-symmetry fix**, so a held name can be asked whether it is attractive at this price independently of whether it is already owned. **NOT RULED TODAY AND EXPLICITLY NOT ACTED ON.** Changing the held-name prompt alters the signal distribution and therefore E4-2's population, which is HOLD ROWS ONLY — that is a treatment change mid-measurement, the exact hazard DP-3C-g, DP-3C-n and DP-3C-q each refused. **IT DOES NOT BLOCK EDGAR GO-LIVE:** E4-1 reads the DQ mix, E4-2 the HOLD population and E4-3 `confidence_raw` around 8-K dates, all of which are HOLD-population reads by design — Kickoff section 5 chose that deliberately ("prefer endpoints measured on the HOLD population, which is where the data is"). No endpoint, arm, threshold, robustness condition, n or rate changes. **RECORDED TODAY, BEFORE EDGAR GOES LIVE, SPECIFICALLY SO THE DISCOVERY DATE UNAMBIGUOUSLY PRECEDES THE TREATMENT** — a finding of this shape surfacing at the 3-C exit would be indistinguishable from a post-hoc excuse for a weak read. Whichever way it is ruled, the ruling carries a dated note preserving the pre-change record — 2 held-name directional signals in 1,119 rows across 59 cohorts — exactly as DP-3C-o preserved "zero risk-engine approvals in 57 cohorts."

★★ RAISED AND PROPOSED PARK — DP-3C-r. SHOULD HOLD CARRY A CONFIDENCE THRESHOLD, AS BUY AND SELL DO? **PROPOSED: PARK, WITH TRIGGERS. DO NOT BUILD ONE.** The question was raised as an apparent asymmetry — BUY gates at 70, SELL at 65, HOLD at nothing — and the asymmetry turns out to be structural rather than an oversight. FOUR GROUNDS, IN ORDER OF FORCE. **(1) IT WOULD BE A TICKER BLACKLIST WEARING A CONFIDENCE LABEL, AND THIS IS THE DECISIVE ONE** `[V]`. Pooled across 1,254 resolved HOLD rows the gradient looks compelling — breach rate 54.1% (<50) to 42.4% (50-59) to 40.5% (60-69) to 30.8% (70+), with sd falling 7.43% to 3.50% — but band membership is very nearly ticker identity: TEN of twenty-four names sit at 60% or below on 100% of their HOLD rows (AG, CBRS, CORN, DOW, GLD, NKE, NVDA, QQQ, SND, SPY), while SCHD is there 1.9% of the time and PM 11.1%. And the gradient does not survive the control: WITHIN-TICKER, the median absolute +5d move difference between the two arms pools to **−1.09pp and is positive on only 5 of 13 qualifying tickers** — it vanishes and flips sign. That is Q4-R replicated on a new variable, where a raw +15.5pt DQ accuracy gap collapsed to +0.5pt once volatility was held constant. A threshold at 60 would permanently flag the volatile half of the watchlist by name. **(2) IT CANNOT BE VALIDATED ON ACCURACY**, because on the HOLD population accuracy IS 1 − breach rate, verified 1,160/1,160, so "sub-60 HOLDs are less accurate" can only ever mean "they move more than 3% more often." **(3) T3 FORBIDS IT** and `retired_criteria_audit.py` enforces it: a cut point asserting that HOLDs above X beat HOLDs below X is a band-ordering claim, the same class as the retired Q1 guardrail. **(4) THE GATE HAS NOTHING TO GATE** — BUY and SELL thresholds block an action, HOLD is the null action, and under T1 nothing executes regardless. RECORDED AGAINST THE PROPOSAL IN FAIRNESS: the within-ticker MEAN SIGNED RETURN difference does read +1.85pp pooled, above the 1.0pp I pre-committed to before computing it — but it FAILS the project's own drop-largest-ticker condition (WMT alone contributes +10.62pp on an arm of n=3; ex-WMT the pooled figure falls to roughly +1.1pp), most arms are severely unbalanced, and the design does NOT hold cohort drift constant the way E4-2's within-cohort arms do, since a confidence split inside one ticker spans different sessions. Given corr(breach rate, |cohort mean|) = +0.44 from 8/06, that confound is live. **AND THE SIGN RUNS OPPOSITE TO THE PROPOSAL'S PREMISE ANYWAY** — low-confidence HOLDs drift slightly UP within-ticker, so there is no latent SELL hiding in the low band. PARK TRIGGERS: re-open if an ABSTAIN/NO-OPINION signal state is ever built (below), or if a vol-scaled secondary metric is ever taken up under a re-scoped Q4-2.

★ WHAT IS ACTUALLY BROKEN UNDER THE THRESHOLD QUESTION IS A TAXONOMY, NOT A CUT POINT — AND THE ANALYZER ALREADY SAYS SO IN ITS OWN OUTPUT. HOLD is doing two jobs: FTI at 72 means CONVICTION TO HOLD, NKE at 33 means I COULD NOT FORM A VIEW. `analyze_log.py`'s own LOW-CONFIDENCE HOLDS section states it verbatim — "These HOLDs reflect Claude's uncertainty, NOT confidence in the position." The fix for that is a distinct ABSTAIN or NO_OPINION signal state the model can emit, which is a GENERATOR change and therefore post-3-C, not a threshold on a continuous variable. Note also that a de facto HOLD flag ALREADY EXISTS at <50% as a REPORTING artifact with no gate attached, which is the correct treatment under T1; today it surfaced NKE 33, XLU 40, CBRS 42, DOW 42, NTR 42, CORN 43, WMT 44 and AAPL 47.

★ THE OPERATIONALLY USEFUL VERSION, SAFE TO BUILD NOW AND PROPOSED AS PART OF DP-3C-r: PERSISTENCE, NOT LEVEL. NKE has read 32, 32, 33, 33, 33 and 33 today — six consecutive sessions of the model declining to form a view on a HELD, underwater position pressing a 52-week low. No single-row threshold captures that as well as the run does. A persistence trigger SIDESTEPS T3 ENTIRELY because it does not rely on band ordering; it relies on the stability of the model's own uncertainty, which is a different construct. It maps onto the project's existing episode grammar (DP-6, and DP-3C-m's coalescing rule), it is DESCRIPTIVE ONLY with no gate and no pass/fail standard, and — the point that makes it safe mid-phase — **it is a reporting layer OVER the HOLD population and never alters what counts as a HOLD, so E4-2's denominator is untouched.**

★ E4-1 CONTROL READING, ONE MORE UNTREATED COHORT `[V]` (from console DQ counts against the master's 8/11 mix). HIGH count 17 to 19, net +2, INSIDE the pre-registered |ΔHIGH| > 3 threshold and therefore not a candidate signal. Four names churned — AG, AIQ and DOW to HIGH, XLU to MEDIUM. TWO T-C DARK CONTROL NAMES MOVED: AIQ reverted to HIGH one session after moving to MEDIUM, and XLU moved out of HIGH. Both are inside the control-window noise floor already measured across 19 same-era untreated cohorts, and neither revises the T-C tolerance. This is the LAST untreated cohort if EDGAR goes live on 8/13.

★ EDGAR GO-LIVE — CLEARED BY THE CHANGE ORDER'S OWN GATE, WITH ONE PRE-COMMITMENT OWED BEFORE THE FLAG IS SET. The change order's stated remaining item was "one live run showing 24 `Signal JSON:` lines"; that is satisfied. STILL OPEN BUT NOT GO-LIVE BLOCKERS: the 8/10 and 8/12 cross-check gaps, and the two 8/10 data-integrity findings (AG 2026-06-26 close still 19.89 in three cells; GLD 2026-07-02 still carrying two closes). **PRE-COMMITMENT PROPOSED NOW, WHILE IT IS STILL A FORECAST:** the first EDGAR-live cohort has never emitted a real `E[...]` tag under the amended DP-3C-i/j format — the parser audit covers it SYNTHETICALLY, and all three phase-cutover breaks in this project's history were "the parser had never seen the real string." Adopt a READ-BEFORE-COUNT rule on the DP-3C-k pattern: the first EDGAR cohort enters E4 only if that day's review finds no extraction defect; otherwise it is tagged SHAKEDOWN, excluded from E4-1/2/3 only, and the clock starts at the next clean cohort. Cost in the bad case is one cohort of roughly twenty; cost of deciding in advance is nothing, and deciding afterwards is deciding with data in view.

★ DP-3C-q IS ALREADY IN THE PRE-REGISTRATION, CORRECTING A STALE UPCOMING ITEM. The 8/11 entry recorded DP-3C-q as "NOT YET IN THAT DOCUMENT ... entered here first and OWED there." `Phase3C_E4_Endpoint_PreRegistration_v1.md` is now at **v1.2, amended 2026-08-11**, and carries the full DP-3C-q ruling in section 5 along with the v1.1 DP-3C-l/m/n pack. That item is CLOSED; the Upcoming block was stale on it.

WS2 / G1 — 1 independent post-deploy episode of 4, unchanged; GM has none. INSUFFICIENT TEST CONDITIONS at the 3-B close; bar not lowered.
H4 — STAYS DEMOTED at 7/14 = 50.0%, 20 total. No DQ-conditional design work until two consecutive readings pass at n >= 12. Note the evidence base is almost entirely scout names — see DP-3C-s.
KEEP-70 — SUPPORTED at 14/33 = 42.4% combined (locked 4/7, extended 10/26), registry 40 as of the 8/11 regeneration. Effectively a five-ticker criterion — see DP-3C-s.
DP-3C-l/m gate-cleared ledger — 2 of 2 episodes resolved (CBRS NO, NVDA YES); standard NONE, INSUFFICIENT TEST CONDITIONS stands, no disposition read from n=2.
E4 endpoints are TABLE READS at their stated n. THE CLOCK HAS NOT STARTED. The 2026-08-03 shakedown cohort remains excluded from E4-1/2/3 but stays in the master, the registry, H4 and KEEP-70.
Standing: T1 (advisory-only, pre-execution, mandatory) · T3 (no band-ordering reliance, tool-enforced). Q1 guardrail RETIRED. T2 RETIRED. KEEP 70%. +/-3% HOLD band unchanged and NOT re-baselined. Blend (WS1) DESCOPED. CBRS excluded from EDGAR to the Q4 2026 Path-A review. Advisory-only - no orders.


\--



Upcoming (Phase 3-C era; every date is a trading day unless noted):
★ DP-3C-s RAISED AND UNRULED (2026-08-12) — IS THE HELD/SCOUT DIRECTIONAL ASYMMETRY INTENDED? Measured `[V]`: SCOUT rows 292 with 44 directional = 15.07%; HELD rows 1,119 with 2 directional = 0.18%, an 84x gap, and the only two held-name directional signals in the record are SCHD BUY 5/21 and CBRS SELL 6/26. NOT a confidence effect — mean conf SCOUT 53.3% vs HELD 52.9%, and held names clear 70% more often (35 vs 5), with the record's highest confidence (FTI 76%) on a held name that has never gone directional. Options: (A) INTENDED, document as a scope property and report every directional-supply figure held/scout-split rather than pooled; (B) UNINTENDED, prompt-symmetry fix. DO NOT ACT BEFORE THE 3-C EXIT — changing the held-name prompt alters E4-2's HOLD-only population mid-measurement. Does NOT block EDGAR; no E4 endpoint changes. Whichever way it is ruled, preserve the pre-change record: 2 held directional signals in 1,119 rows across 59 cohorts.
★ DP-3C-r PROPOSED PARK (2026-08-12) — NO CONFIDENCE THRESHOLD FOR HOLD. A cut point would be a ticker blacklist: ten of 24 names sit at <=60% on 100% of their HOLD rows while SCHD sits there 1.9% of the time, and the within-ticker median |+5d move| difference pools to −1.09pp, positive on only 5 of 13 tickers — the pooled gradient vanishes and flips under control, Q4-R replicated. Also unvalidatable on accuracy (band-breach identity), blocked by T3, and there is no action for it to gate under T1. The within-ticker mean-return read of +1.85pp FAILS drop-largest-ticker (WMT +10.62pp on n=3; ex-WMT ~+1.1pp) and does not hold cohort drift constant. PARK TRIGGERS: an ABSTAIN/NO_OPINION signal state, or a re-scoped Q4-2. PROPOSED AND SAFE NOW: a PERSISTENCE trigger (e.g. NKE at 32-33 for six consecutive sessions on a held, underwater position) — descriptive only, sidesteps T3, and never alters what counts as a HOLD so E4-2's denominator is untouched.
★ FIRST EDGAR COHORT — PRE-COMMIT READ-BEFORE-COUNT BEFORE SETTING THE FLAG (raised 2026-08-12). The `E[...]` tag has never appeared in a live log under the amended DP-3C-i/j format; the parser audit covers it synthetically, and all three phase-cutover breaks in this project were "the parser had never seen the real string." On the DP-3C-k pattern: the first EDGAR cohort enters E4 only if that day's review finds no extraction defect; otherwise SHAKEDOWN, excluded from E4-1/2/3 only, clock starts at the next clean cohort.
★ 8/12 CROSS-CHECK NOT RUN — the run was reviewed from console output; `logs\signals_2026-08-12.log` was not supplied as a file and the master had not received the paste. Today's 24/24, the resolutions due (+5d 8/05, +10d 7/29, +20d 7/15) and the recalc check are unverified. Joins the 8/10 gap in the G4 streak; close both with `log_tracker_crosscheck.py` and `outcome_sanity.py`.
★ RECORD ORDERING — THE TWO 8/11 ENTRIES ARE SPLICED IN REVERSE CHRONOLOGICAL ORDER (found 2026-08-12). "Session 2" is filed above the session it followed, which is what makes 7/7b read as LANDED in one entry and "NOT LANDED AND STILL GATING" in the next with neither citing the other. Today's live run settles it: 7/7b had landed. Reorder and stamp same-day entries with their session, not just the date. Third instance of a record-structure defect after the two-Upcoming-blocks escape twice; the cause is the paste step, not the content.
★ `analyze_log.py` DOES NOT UNICODE-DECODE THE REASONING FIELD before truncating it for LOW-CONFIDENCE HOLDS — XLU rendered an en dash as a literal `–` escape on 2026-08-12. Only XLU's truncation window held a non-ASCII character, so it is the only visible instance, not the only occurrence. Lands in `logs\summary_history.txt`, which nothing reconciles.
★ ACTIVE RULES BANNER STILL LISTS "Max open positions : 8" IN GATING GRAMMAR (raised 2026-08-12) though DP-3C-o (iii) demoted CHECK 6 to a reported flag. Same shape as D-6, and more misleading after the demotion rather than less.
★ DP-3C-o (ii) AND (iii) AND THE APPROVAL PATH REMAIN UNEXERCISED IN PRODUCTION (2026-08-12) — no directional signal has cleared CHECK 5 since they landed, and CHECK 5 precedes CHECK 6. The plumbing is verified; the new risk logic is not. First gate-clearing BUY or any SELL will be the real test.
★ DP-3C-q IS CLOSED AGAINST THE PRE-REGISTRATION — `Phase3C_E4_Endpoint_PreRegistration_v1.md` is at v1.2 (amended 2026-08-11) and carries DP-3C-q in section 5 alongside the v1.1 DP-3C-l/m/n pack. The prior "three rulings live only in the notes" item and the "DP-3C-q OWED there" item are both satisfied.
★ 8/10 COHORT UNREVIEWED (raised 2026-08-11) — `signals_2026-08-10.log` has never been supplied for review. The master's own 8/10 rows are visible (used for the 8/11 E4-1 churn check and confirmed in the near-miss registry and gate-cleared ledger), but risk-engine reason strings, D1 behavior and pre-DP-3C-o CHECK 6 disposition for that date are unverified. Close with `log_tracker_crosscheck.py` and `outcome_sanity.py` against the real 8/10 log before the G4 streak is next cited as clean.
★ MONITOR STRIP WS1/G2 ROW STILL LIVE-WORDED (flagged 8/05, still unfixed as of the 8/11 16:16 regeneration) — prints a live acceptance bar and a state of "on track" / "net +1" for a gate DESCOPED since 2026-07-31. Relabel to DESCOPED with the T-G2-a/b/c triggers.
★ DASHBOARD "# Signals ≥ 70% (actionable)" CARRIES THE SAME DEFECT AS 5b, UNFIXED (found 2026-08-11) — this is a workbook FORMULA on the report copy's Dashboard tab, not `analyze_log.py`'s CONFIDENCE STATS line, so today's Python-side 5b fix does not reach it. Counts every row ≥70% including HOLDs on a ~97%-HOLD watchlist.
★ THIS FILE'S UPCOMING SECTION IS STALE RELATIVE TO TODAY'S OWN ENTRIES (noted 2026-08-11) — several items below (D-7, D-3, 5b, D-1/D-2, DP-3C-o, N-1) are recorded as LANDED in the 8/11 change-order entries above but are not yet pruned from this list. Reconcile at the next housekeeping session rather than trusting this list's staleness silently, per the standing convention.
★ OPEN DATA-INTEGRITY ITEMS — TWO, BOTH FOUND 2026-08-10 BY `outcome\_sanity.py` ON ITS FIRST RUN; full evidence is in the 8/10 entry. (i) AG's close for 2026-06-26 is entered as 19.89 in three cells — the 5/28 +20d, 6/11 +10d and 6/18 +5d rows. AG's quote that morning was 17.13 and the next session's was 16.60, and the implied close series around it reads 17.72, 16.50, 16.06, 16.50, \[19.89], 16.81, 16.96. A close of 19.89 requires AG to close 16% above its own morning quote and open 17% lower the next session. Ruled out as a date-mapping artifact: only 2 of 24 tickers show a >5% gap on 6/26, and the cohort-date sequence equals the true trading calendar exactly (57 cohorts, 57 trading days, zero gaps) \[V]. VERIFY THE TRUE VALUE EXTERNALLY against Schwab price history before correcting; do not infer it from the series. Correcting it moves the 6/18 +5d, 6/11 +10d and 5/28 +20d cohort reads. (ii) GLD has TWO different closes entered for 2026-07-02 — 378.13 from the 6/03 +20d row against 379.13 from the 6/17 +10d and 6/25 +5d rows. One date cannot have two closes; one of them is wrong by construction.
★ `outcome\_sanity.py` BUILT 2026-08-10 — the magnitude guard for the manual-entry outcome columns, closing the hole the 8/07 WMT incident exposed. Four checks: quote-versus-close against the same-day Px@signal already in the master; cross-horizon agreement; horizon-scaled magnitude (+5d 30% / +10d 40% / +20d 50%, calibrated against the record's legitimate extremes of CBRS −34.8% and MSFT +31.7%); cohort dispersion. Derives the trading-day index from the master's own cohort dates, so there is no holiday table and no second source of truth to drift. Refuses `tracker\_with\_registry.xlsx` as an input (exit 2), same guard as `log\_tracker\_crosscheck.py`. Regression-tested against the re-injected 8/07 defect: caught on all three cells plus the dispersion tell. ADD TO `scan.bat` AFTER THE PASTE, alongside the cross-check.
★ COMMIT BACKLOG — RUNBOOK ISSUED 2026-08-10, one command at a time, with a credential pre-flight that must not be skipped: `token.json` and `.env` sit in the project root and `git ls-files` must be checked for them BEFORE anything is added. Files: `run\_daily\_review.bat`, `retired\_criteria\_audit.py`, `log\_tracker\_crosscheck.py`, `scan.bat`, `signal\_scan.py`, `edgar\_client.py`, `edgar\_parser\_audit.py`, `outcome\_sanity.py`, `main.py`, `claude\_signal.py`, the 8/04 patches to `monitor\_strip.py` and `h4\_dq\_threshold.py`, Workflow v6.0, the instruments, and this file. Largest unhedged risk in the project and the only one that grows every session. UNTIL THE FILES ARE VISIBLE ON THE REMOTE, THE BACKLOG IS NOT RETIRED.
★ UNRULED AND RAISED SO IT IS NOT DECIDED BY DEFAULT — ARE `logs\\signals\_\*.log` AND THE MASTER TRACKED? DP-3C-i ruled that the `E\[…]` tag must carry filing dates BECAUSE `edgar\_cache\\` is gitignored and deletable, so window membership "survives nowhere permanent." That reasoning assumes THE LOGS ARE DURABLE. If they are untracked they are as impermanent as the cache, and E4-2's ADJACENT/COVERED-QUIET split is not reconstructible after a disk loss — the exact hazard DP-3C-i exists to close. The master carries the argument with more force: manual-entry-only, ground truth for every harness, one copy. Tracking binaries and a growing log directory has real costs, so this belongs in a dated ruling either way.
★ DP-3C-o PROPOSED, NOT RULED — CHECK 6 disposition, drafted 2026-08-06 from `risk\_engine.py` at source. (i) Guard CHECK 6 to BUY-only (this is D-3, stands alone, three words); (ii) ENFORCE `MAX\_POSITION\_PCT` inside `evaluate\_signal` so the rule that measures concentration is the rule that runs; (iii) demote CHECK 6 from a rejection to a reported risk flag — by its own analyst note at `RiskConfig` L59-63 it is a MONITORING-BURDEN cap, not a risk cap, and it caps the diversification its own comment identifies as risk-reducing. PRE-CONDITION, BINDING: D-7's parser audit must pass first. If the cap changes, the ruling carries a dated note PRESERVING "zero risk-engine approvals in 57 cohorts under the Phase-2 cap" — the change makes the record look better and the pre-change finding must not be erased.
★ D-7 — THE PARSERS HAVE NEVER SEEN THE APPROVAL PATH. An approved directional signal returns a multi-sentence `PENDING HUMAN APPROVAL — …` reason and triggers a "Shares : N shares recommended" line, neither of which has appeared in 1,363 rows. Before CHECK 6 is touched, `edgar\_parser\_audit.py` must synthesise an APPROVED directional row carrying both and pass. Same defect class as the three hardcoded-phase-token breaks.
★ D-5 (CHECK 8 is `pass`, so `DAILY\_LOSS\_LIMIT\_PCT` controls nothing) and D-6 (`MAX\_POSITION\_PCT` printed as an Active Rule on every signal and never consulted by `evaluate\_signal` — thirteenth instance of the tool-reports-a-value-it-did-not-compute class, first found in the risk engine). D-1's fix is in `main.py` at **L330** (`handle\_phase3a`, the live path) — NOT L285-286, which is the dead `handle\_phase2` handler the 8/04 entry mistakenly cited; D-2's is in `risk\_engine.py`. Two files, corrected attribution. D-6 is CLOSED and broader than first scoped: `calculate\_position\_size` is imported at `main.py` L41 and never called anywhere, so `MAX\_POSITION\_PCT` is advertised on every signal and enforced nowhere.
★ Q4-2 MUST BE RE-SCOPED IF TAKEN UP (recorded 2026-08-06). A vol-scaled band corrects DISPERSION and does nothing about DRIFT. Q4-2 was parked on the dispersion argument alone and that justification is now known to be half the mechanism: corr(breach rate, sd) = +0.62 against corr(breach rate, |cohort mean|) = +0.44, with 2026-06-16 (sd 3.87%, |mean| 4.89%, breach rate 68.2%) as the falsifying case. DP-3C-n is NOT disturbed — within-cohort holds drift constant by construction.
★ MEMO §4.1 DOCUMENTATION CORRECTION OWED. There is no "Was Claude Right" column at +10d or +20d, so accuracy at those horizons is (n − breaches − misses)/n by DERIVATION. §4.1's table sets Accuracy beside breach rate at all three horizons; at +10d and +20d those are two forms of one number presented as corroboration. Findings unaffected. DP-3C-n's substitute reporting applies at ALL THREE horizons, not only +5d.
★ E4-1's TWO NUMBERS ARE NOW DERIVABLE AND THE "NEEDS MORE CONTROL COHORTS" QUESTION IS CLOSED. The baseline is not the four-session control window but every same-era untreated cohort since 7/13 — 19 of them \[V]: churn mean 4.50 with a maximum of 6, HIGH count mean 17.6 with sd(pop) 1.39 and range 14-20, |ΔHIGH| session-to-session p95 = 3 and maximum = 3. MINIMUM SHIFT SIZE: |ΔHIGH| > 3 NAMES, measured on the NET and not the churn — 8/07 moved six names with zero net change. T-C tolerance derives the same way on the eight dark names. Further control cohorts have NO marginal value to E4-1, and none to E4-2 or E4-3, which read post-deploy only.
★ GATE-CLEARED LEDGER — GENERATE OR HAND-MAINTAIN? Proposed for ruling as DP-3C-p: extend `build\_near\_miss\_registry.py` (a parameter, not a new harness — the same scan at a different threshold plus a coalescing pass) rather than maintain a prose ledger with DP-3C-m's coalescing rule applied by hand. Any tab carries a generator-written header: DESCRIPTIVE ONLY, NO STANDARD, EXIT DISPOSITION PRE-COMMITTED INSUFFICIENT. Note this amends DP-3C-l on CHANGED GROUNDS (DP-3C-m did not exist when it was ruled), not on a small-n read.
★ THE CONTROL-COHORT WINDOW ENDS ON AN EVENT, NOT A DATE — change-order STEP 8 (`edgar\_parser\_audit.py` exit 0 AND `--selftest` with the N-1 regression fixtures) AND STEP 8b (the frozen E4-2 vol-tier table). Four control cohorts observed (8/04-8/07). NOTED HONESTLY 2026-08-10: control collection no longer has independent measurement value now that E4-1's envelope is set, so the window continues because N-1 is unfixed, not because more controls help. It is a consequence, not a choice.
★ D-8 — BLOCKING PRE-CONDITION ON CHANGE-ORDER STEP 7 (found 2026-08-10 from `main.py` at source). `PHASE` is a module constant at L63 and the dispatch at L544 accepts only ("3-A","3A",3,"3-B","3B"). Setting PHASE="3-C" alone matches neither branch, falls to `log.error` at L550 — A LOGGED ERROR, NOT AN EXCEPTION — and the run completes normally having emitted no signal lines at all. Workflow §18 maps that exact symptom ("analyze\_log reports 0 signals") to a different cause and needs a second row.
★ CHANGE ORDER — NOT STARTED, NOTHING HAS LANDED. (D-3) guard CHECK 6 to BUY-only; (5b) the `analyze\_log.classify\_directional\_signal` one-liner, PLUS the separate CONFIDENCE STATS ">= 70% (actionable)" label, PLUS a directional guard so a HOLD at 70 cannot enter the ledger (`signal\_scan.py` already carries this guard — copy it); then `signal\_scan.py` into `edgar\_parser\_audit.py`, which gates everything below; then the audit's synthesised tag and 3-C token; then N-1's bucket selection and the \[6M YTD] / \[9M YTD] label; then DP-3C-i and DP-3C-j; then (7) the \[PHASE 3-B DRY RUN] token AND (7b, BINDING, SAME EDIT) extend the L544 phase dispatch to accept "3-C"/"3C" — see D-8: setting PHASE without it makes every ticker fall to a logged error, emits ZERO signal lines, still spends 24 API calls and STILL ADVANCES `signal\_state.json`, and the parser audit cannot see it because it never executes `main.py`; verify with one live run showing 24 `Signal JSON:` lines; then (8) re-run the audit (exit 0 required) and `--selftest`; then (8b) BUILD AND FREEZE THE E4-2 VOLATILITY-TIER TABLE per DP-3C-n section 3.3; then D-7's approval-path audit; then D-1/D-2; then DP-3C-o and the cap. Any cap change lands AFTER 5b or the fix becomes unverifiable. SLICING NOTE (2026-08-10): only the phase-token step onward needs a contiguous block — D-3, 5b, the audit additions, N-1 and DP-3C-i/j are all dormant or non-runtime while `EQUITY\_EDGAR` is unset and can land singly on a weekday.
★ THREE RULINGS STILL LIVE ONLY IN THE NOTES — DP-3C-l, DP-3C-m and DP-3C-n must be entered into `Phase3C\_E4\_Endpoint\_PreRegistration\_v1.md` (section 5 for all three, section 3 rewritten for DP-3C-n). Amendment pack drafted 2026-08-05 and NOT yet applied. The DP-8/DP-9/DP-10 provenance loop is the precedent for what happens when an instrument and the record disagree.
★ Px@signal — returns are QUOTE-TO-CLOSE (K = (H−G)/G), so an off-canonical Px@signal is not immaterial. Effect is VARIANCE, not bias; prices are NOT restated. Run timing: 8/04 +98 min, 8/05 +23 min, 8/06 +39 min, 8/07 CANONICAL at +3.5 min. Tag each cohort's Px@signal timestamp. Quote-timing variance is a second, independent argument for the parked Q4-2 metric.
★ HOUSEKEEPING — relabel the monitor strip's WS1/G2 row to DESCOPED with the T-G2-a/b/c triggers (it currently prints a live acceptance bar and a state of "negative" for a gate whose 7/31 ruling found a negative VERDICT explicitly NOT supported); `signal\_scan.py`'s `Daily\_Workflow\_v5\_3` header reference and its "pre-EDGAR (3-B)" era line; the `run\_daily\_review.bat` closing banner (G2, G1, H4); `run\_daily.bat`'s header era; the blend-channel check wording, now fired four times.
★ `analyze\_log.py` has contaminated `logs\\summary\_history.txt` with false ACTIONABLE lines on consecutive sessions. Check and annotate that file when 5b lands; nothing reconciles it against the master.
★ N-1 IS UNFIXED and its footprint grows on its own as Q1 filers roll forward — 6/15 affected toward roughly 13/15 by the first E4-2 read.
★ Workflow v6.0.1 — `scan.bat`, `log\_tracker\_crosscheck.py` and `outcome\_sanity.py` missing from sections 3 and 16; section 4 documents 15/24 prefetch against a live 19/24 and "\~7 sector ETF(s)" against a live 8; section 18's budget row is wrong per DP-3C-j; section 11 needs the N-1 rule; `scan.bat` runs the cross-check BEFORE the paste, producing false MISSING rows.
★ RESOLVE THE TWO GHOST ROWS — Excel rows 222/226 = signals #218/#222, 2026-06-01 AG and FTI, complete price series at all three horizons but NULL Signal / Confidence / Data Quality. Annotate, do not delete; record which was done. G4 requires no open data-integrity items at exit. Note 6/01 recorded skips as blank-field ROWS while 6/02 (21 rows) and 6/03 (22 rows) recorded them as ABSENT rows — two conventions for one condition.
★ Add a cohort-versus-entry reconciliation to the exit checklist. No existing tool can see a date present in the master and absent from the notes.
★ `Sheet1` stays in the master by ruling (2026-08-04). Suggested, unruled: mark it retired in place so row 2 stops asserting a retired criterion in live grammar.
★ DP-3C-f unruled (AG and NTR as 40-F/6-K foreign filers; proposed no change in v1). Worksheet v1.3 clerical corrections outstanding. `context\_providers.py` latent trap unfixed by design (Scope Spec section 8 pins the file). UTC date stamp in the filing-section header. `DP-3C-l` label collision (lowercase L beside DP-1 through DP-10) recorded, not renamed.
★ NOTES HYGIENE — this file was de-escaped on 2026-08-10. Markdown editors auto-escape on paste and the escapes COMPOUND on each save; the master had reached three-deep sequences. Escape artifacts were removed in a FORMATTING-ONLY pass, verified by a gate proving the two versions are byte-identical once every backslash is stripped. NO WORDS, NUMBERS OR CONCLUSIONS WERE CHANGED and no historical entry was rewritten. PASTE EVERY FUTURE SPLICE AS PLAIN TEXT, and prefix each dated entry with "## " to match the file's heading convention.
WS2 / G1 — 1 independent post-deploy episode of 4, unchanged for 24 sessions; GM has none. Episodes arrive only when the market produces a material adverse move on WMT or GM and cannot be accelerated. G1 was recorded INSUFFICIENT TEST CONDITIONS at the 3-B close and the bar was NOT lowered.
H4 — STAYS DEMOTED at 6/13 = 46.2%, 14 total, with 17 HIGH-DQ rows now in the registry so the denominator moves within the week. No DQ-conditional design work until two consecutive readings pass at n >= 12.
E4 endpoints are TABLE READS at their stated n — E4-1 \~10 cohorts, E4-2 150 resolved ADJACENT rows, E4-3 20 events. THE CLOCK HAS NOT STARTED. Do not read them early; a one-session move is noise. The 2026-08-03 shakedown cohort is excluded from all three but remains in the master, in the registry, in H4 and in KEEP-70.
Standing: T1 (advisory-only, pre-execution, mandatory) · T3 (no band-ordering reliance, tool-enforced). Q1 guardrail RETIRED. T2 RETIRED. KEEP 70%. ±3% HOLD band unchanged and NOT re-baselined. Blend (WS1) DESCOPED. CBRS excluded from EDGAR to the Q4 2026 Path-A review. Advisory-only · no orders.

\---

*Advisory-only · no orders · not financial advice.*

