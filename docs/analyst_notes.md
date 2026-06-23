# Claude Equity Bot — Analyst Notes

**Project:** claude-equity-bot
**Phase:** 2 (read-only dry run)
**Window:** 2026-05-18 to 2026-06-12 (closed)
**Maintainer:** Robert

This file documents structural findings, calibration evidence, and
decisions during Phase 2. Entries are organized into two sections:
**Reference** (glossary, definitions — stable) and **Findings**
(dated entries — chronological).

---

# Reference

## Glossary — Metric Definitions

Locked in 2026-05-28 to prevent terminology drift over the remaining
~7 days of Phase 2.

### "Hit" — Was Claude Right?

A "hit" means Claude's signal was correct on a given row. The formula
in the tracker's column N evaluates each signal type differently:

|Signal|"Right" Means|Tracker Formula|
|-|-|-|
|HOLD|Stock stayed within ±3% over 5 days|`IF(ABS(K_) < 0.03, "YES", "NO")`|
|BUY|Stock went up (positive return)|`IF(K_ > 0, "YES", "NO")`|
|SELL|Stock went down (negative return)|`IF(K_ < 0, "YES", "NO")`|

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

---

## Structural Gap Taxonomy

Locked in 2026-05-26. The four chronic-LOW tickers represent three
distinct gap types, each requiring a different Phase 3 response.

|Type|Definition|Tickers|Phase 3 Fix|
|-|-|-|-|
|**Type 1: Asset-class mismatch**|Pipeline built for equities; ticker is a commodity ETF. News flows around the underlying, not to the ticker.|CORN, GLD|`commodity_context.py` module|
|**Type 2: Driver context gap**|Right data source, but dominant price driver is an exogenous commodity not in news feed.|AG (silver)|`commodity_backed_equity_context.py`|
|**Type 3: News density gap**|Right source, insufficient ticker coverage (e.g., recent IPO).|CBRS|Time only — or exclude from auto-analysis|

**Key insight:** Three of four chronic-LOW tickers share the same root
cause — pipeline treats every ticker as an equity, but commodity ETFs
and commodity-backed equities have different dominant price drivers.

### Phase 3 Priority Order

1. `commodity_context.py` — fixes CORN + GLD + future commodity ETFs
2. `commodity_backed_equity_context.py` — fixes AG + future miners
3. CBRS exclusion config change (5 minutes)

---

# Findings (Chronological)

## 2026-05-26 — Structural Data Gap: CORN (Commodity ETF Class)

**Phase:** 2 (read-only dry run), Day 6 of ~15 (pattern first observed Day 5, 2026-05-22)
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

Finnhub's `company_news` endpoint returns articles tagged with the
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
`MIN_DATA_QUALITY = "MEDIUM"`. The risk engine is doing its job.
3. The persistent low-confidence HOLD output is the *correct* output
for a ticker the bot cannot confidently analyze.

### Deferred Decision (June 10 Review)

Three paths to evaluate against ~15 days of CORN data:

* **Path A — Exclude CORN from auto-analysis.** Move to manual monthly
review around WASDE release dates. Lowest effort.
* **Path B — Build `commodity_context.py` module in Phase 3.** Free
data sources (USDA WASDE schedule + NASS QuickStats API + yfinance
ZC=F + NOAA Corn Belt outlook during growing season). Adds
~$0.06/month in Claude tokens. ~3 hours build. Module would also
serve GLD and any future commodity ETFs.
* **Path C — Keep current behavior.** Accept that LOW data quality
is honest signal and the auto-rejection is the correct outcome.

### Rejected Approaches (and Why)

|Approach|Reason Rejected|
|-|-|
|Barchart CORN news page|Public page requires scraping (ToS risk); their `getNews` API is paid (Barchart OnDemand).|
|WeatherWealth subscription|Paid (~$25-50/mo). Violates the "no added subscription cost" constraint.|
|Increase Finnhub `NEWS_LIMIT` for CORN|Doesn't address relevance — more tangential headlines ≠ better signal.|
|Add commodity risk-mgmt rules (stop-loss, calendar spreads)|Belongs in Phase 4 execution, not Phase 2 analysis. Stop-loss already in risk engine; calendar spreads not applicable to ETF holdings.|

### Next Touch Points

* June 10, 2026 — Phase 2 evaluation; decide Path A/B/C
* Next WASDE release: June 11, 2026 (one day after eval — useful as
natural catalyst test for whichever path is chosen)

---

## 2026-05-26 — Structural Gap Taxonomy: Chronic-LOW Ticker Class

Extending the CORN analysis above, applied same diagnostic lens to
AG, GLD, CBRS. Full taxonomy now lives in the Reference section above.

Quick summary:

|Ticker|Gap Type|Phase 3 Action|
|-|-|-|
|CORN|Asset-class mismatch|`commodity_context.py`|
|GLD|Asset-class mismatch|Same module as CORN|
|AG|Driver context gap (silver spot missing)|`commodity_backed_equity_context.py`|
|CBRS|News density gap (recent IPO)|Exclude until Q4 2026|

See CORN entry above for full evidence and rejected approaches.

---

## 2026-05-26 — May 18 Cohort Day-5 Outcomes: First Calibration Signal

**Phase:** 2 (read-only dry run), Day 6 of ~15
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

---

## 2026-05-27 — Day 7 Run: Two Structural-Gap Confirmations

**Phase:** 2 (read-only dry run), Day 7 of ~15
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

---

## 2026-05-27 — May 19 Cohort Day-5 Outcomes: Mixed Calibration Signal

**Phase:** 2 (read-only dry run), Day 7 of ~15
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

**Phase:** 2 (read-only dry run), Day 8 of ~15
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

run_daily.bat threw ". was unexpected at this time" after parser
completed. Cause: unquoted `if exist paste_today.tsv echo ...` line
in summary block. Fixed by parenthesizing the conditional echo.

---

## 2026-05-28 — May 20 Cohort: Calibration Verdict Reached

**Phase:** 2 (read-only dry run), Day 8 of ~15
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

---

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



---

## 2026-05-29 — Day 9 Run: Fix Verified, Log Recovery, AM/PM Diagnostic

**Phase:** 2 (read-only dry run), Day 9 of ~15
**Status:** run_daily.bat fix verified; bot ran cleanly; log file
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

The `. was unexpected at this time` error in run_daily.bat is gone.
Root cause was an unquoted `if not exist` block where the variable
expansion `%TODAY%.log` confused cmd.exe's parser. Single fix:
quoted the path in line `if not exist "logs\signals_%TODAY%.log"`.
Verified by clean run today. Lesson learned: yesterday's fix
targeted the wrong block; should have asked to see the file
contents before claiming a fix.

### Log File Truncation Incident

After today's morning run, `signals_2026-05-29.log` was found
truncated to 3 bytes. Most likely cause: a second run of
run_daily.bat (to verify the fix worked) opened the log in write
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
`logs/diagnostic_2026-05-29_PM.txt`.

---

## 2026-05-29 — May 21 Cohort: First Pattern-Holds = NO, SCHD Near-Miss Wins

**Phase:** 2 (read-only dry run), Day 9 of ~15
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

---

## 2026-05-29 — Diagnostic Deep Dive Update: WMT and GM (Cohort 4)

**Phase:** 2 (read-only dry run), Day 9 of ~15
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
**Decision type:** Document hygiene — keep analyst_notes focused on Phase 2 execution

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
|Phase 3 design thinking moved to dedicated file|Keep analyst_notes focused on Phase 2 execution and findings|n/a|

### Where to Find the Design Thinking

**Document:** `phase3_design_concepts.md` (in project root)

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
The mechanism is clean: the bot's output is ~95% HOLD, and a HOLD is
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
> accuracy decays (~8pt) and the high-confidence band underperforms,
> driven by sustained adverse moves in high-conviction HOLDs (WMT, PM).
> The +5d window is where the signal lives; +10d is where HOLD theses
> expire.

This is ONE cohort (n=24) — a strong, mechanism-backed first reading,
not a verdict. The 5/19 +10d (due 6/3) is the replication test.

---

## 2026-06-02 — May 22 & May 26 Cohorts: Two More Non-Confirming, Aggregate Holds

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

---

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
average would need ~+5.6% each to clear the bar. **Realistic Phase 2
conclusion: the 70% threshold is correctly tight. That is the experiment
working — a read-only dry run talking us out of a premature change.**

---

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
`schwab_client`. Two consecutive skip-days after a clean week is enough
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

---

## 2026-06-03 — +10d Decay Finding Splits on Replication; H1 Hardens; Strongest Cohort Yet

**Phase:** 2 (read-only dry run), Day 12 of 19
**Status:** 5/27 cohort +5d complete; 5/19 +10d complete (replication test); Cohort Analysis tab extended through 6/12.

### Headline: The +10d "Decay" Finding Replicates Halfway

Yesterday (5/18 cohort) produced the week's marquee finding: HOLD
accuracy decayed ~8pt from +5d to +10d while absolute moves grew. The
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

---

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
|---|---|
|40-49%|56% (5/9)|
|50-59%|**77% (10/13)**|
|60-69%|50% (1/2)|

Overall 16/24 = 66.7%. Pattern Holds = ✓ YES (50-59% leads). DQ: HIGH 5/7,
MEDIUM 11/17. Worst: CBRS −17.3% (chronic excluded name, again). Best: SND
+19.5%.

> ANALYST NOTE: SND +19.5% is a HOLD that COUNTS AS A MISS (breached +3%) even
> though the position gained ~20%. The HOLD ±3% test scores large favorable
> moves as "wrong" because the bot didn't say BUY. Correct by the locked
> definition, but when reading cohort accuracy, remember some "misses" are
> gains left on the table, not losses the bot failed to avoid.

### 5/20 +10d — The Decay Tiebreaker

The decay question was 1-1 (5/18 decayed −8pt; 5/19 flat). 5/20 broke it:

|Cohort|+5d Hit|+10d Hit|Δ|Decayed?|
|---|---|---|---|---|
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

---

## 2026-06-05 — Day 14: Q2 VERDICT LOCKED; 5/29 Cohort; 5/21 +10d; Decay = Coin Flip

**Phase:** 2 (read-only dry run), Day 14 of 19
**Status:** All 9 cohorts +5d-complete. Q2 near-miss threshold verdict LOCKED.
Clean 24/24 run (3rd consecutive). The week's terminal data event.

### Q2 VERDICT — LOCKED: KEEP 70% Threshold

The complete near-miss cohort (6 of 7 outcomes; NVDA 6/1 due 6/8 as addendum):

|Date|Ticker|Conf|DQ|+5d Return|Right|
|---|---|---|---|---|---|
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
|---|---|
|40-49%|14% (1/7)|
|50-59%|**73% (8/11)**|
|60-69%|67% (4/6)|

Overall 13/24 = 54.2%. Pattern Holds = ✓ YES (50-59% leads decisively). This
is the 9th and final cohort to reach +5d.

### Q1 CALIBRATED — FINALIZED

All 9 cohorts +5d-complete. Final aggregate (n=216 band-sample):

|Band|Hit Rate|
|---|---|
|40-49%|43.1% (31/72)|
|50-59%|**61.3% (65/106)**|
|60-69%|50.0% (19/38)|

**Q1 FINAL: ✓ CALIBRATED — 6 of 9 cohorts confirm; 50-59% leads at 61.3%
in the combined data.** The 3 non-confirming cohorts (5/21, 5/22, 5/26) are
explained by tiny 60-69% samples and low-volatility names inflating the
40-49% band; none reverse the aggregate.

### 5/21 +10d — Decay Reverts to a COIN FLIP

|Cohort|+5d Hit|+10d Hit|Δ|
|---|---|---|---|
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
|---|---|---|---|
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
> held WMT through three identical ~−11% losses (5/18-5/20). Then it CAUGHT UP:
> confidence dropped to 48-55% as the losses simultaneously shrank (−5%, −4%,
> −1%), and by 5/29 WMT was +2.45%. The lag self-corrected over ~3-5 days —
> exactly H1's hypothesized window. H1 (add prior-5-day price input) is the
> top Phase 3 hypothesis: it is the only finding that replicated across every
> cohort AND has a clear mechanism AND a demonstrated resolution.

---

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
> across exactly the window NVDA fell from ~$228 to ~$205.

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
> de-rated WMT from 62% to 45–48%, the +10d loss collapsed from −15% to ~0%. H1
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

---

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
with an NVDA near-miss BUY). HIGH DQ count dropped to 4/24 (recent days ~8/24)
— watch, not alarm.

Flags for the tab: (1) the 6/8 NVDA near-miss ($208.41, +5d due 6/15) and
today's 6/9 NVDA near-miss ($207.40, +5d due 6/16) are not yet rows in the
Near-Miss tab — summary still says Total = 9, should be 11; (2) the VERDICT
box still says "to be decided 2026-06-10" — stale, Q2 is FINAL, review is
6/12.

---

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

---

## 2026-06-11 — Day 18: 5/28 +10d on the Bounce; WASDE Validates the CORN Blind Spot; Scope Correction on the Shock Set

**Phase:** 2 (read-only dry run), Day 18 of 19
**Status:** 5/28 cohort +10d complete (8 of 9 — only 5/29 remains, due at
tomorrow's review). WASDE released ~11:00 CST; 6/11 was a bounce day (SPY
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
~11:00 CST release, printed CORN at 38% confidence (lowest band) with no
event awareness: the bot did not know WASDE existed, let alone that it was
today. CORN has also bled −7.62% over the 5/28 +10d window.

> ANALYST NOTE: This is the natural-catalyst test the kickoff specified, and
> it reads as VALIDATING Path B (`commodity_context.py` /
> `commodity_backed_equity_context.py`): a knowable, scheduled event moved the
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

---

## 2026-06-12 — Day 19: Phase 2 CLOSED — Final Cohort, Final Scorecards, Review Decisions

**Phase:** 2 (read-only dry run), Day 19 of 19 — **FINAL DAY**
**Status:** 5/29 +10d complete. All 9 cohorts complete on both windows (n=216
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
|Q1–Q5 leans|~25 book · cross-asset deferred · rebuild-daily + price input · **advisory** · Risk Engine unchanged for 3-A|

### 6/12 Run Health + Phase 2 Operational Close

Clean 24/24 AM run, avg confidence 53.0%, HIGH DQ 7/24 (recovered). Phase 2
operational record: 19 trading days, 451 signal rows, 9 review cohorts ×
24 × 2 windows complete, two pure-HOLD days (5/28, 6/10), three 429-skip days
(6/1–6/3, fixed by spacing), zero missed runs. **Phase 2 is closed.**

---

## 2026-06-15 — Phase 3-A Go-Live: First Advisory Run Captured; Analyzer Phase-Bug Fixed; Toolchain Hardened; Repo Reconciled

**Phase:** 3-A (prompt-level, advisory-only — **LIVE**), Day 1
**Status:** Phase 3-A is live. First 24/24 advisory run generated and captured to the Signals tab (rows 456–479). No orders — advisory-only, human-gated. One latent analyzer bug surfaced at the phase cutover and was fixed; the runner toolchain was hardened; the public repo was reconciled and a push bundle staged. First live cohort (6/15) is pending its +5d.

### Go-Live — First Advisory Run

Clean 24/24 AM run, **all HOLD**, risk engine APPROVED across the board, zero orders (advisory-only working as designed). The 24 control-arm signals parsed to the tracker at rows **456–479**, columns A–G matching the log exactly (AAPL 0.58/HIGH/295.46 … GLD 0.52/MEDIUM/400.17), H–J empty pending outcomes, K–N outcome formulas in place. The Dashboard swept the new rows in — **Total Signals 475** (451 Phase 2 + 24) — and the **50-59% guardrail still leads at 58.8%** (today's HOLDs add to the band totals but not to YES/NO, by design, since they have no +5d yet).

> ANALYST NOTE: The 451-vs-475 signal-distribution gap traced to AG and FTI — two **price-only backfills** (429-skipped on 6/1, so no signal was ever generated; their prices were filled for return tracking). Signal blank → Was-Right falls through to "" → both rows sit inert in every band and cohort while still carrying prices. Not a defect; nothing to fix.

### analyze_log.py — Phase-Regex Fix (latent 19 days, broke on the cutover)

The analyzer reported **0 signals** on the 6/15 log while the parser read 24 from the same file. Root cause, one line: the summary regex was `PHASE \d DRY RUN\]`. `\d` matches a **single digit**, so it matched `[PHASE 2 DRY RUN]` cleanly but `[PHASE 3-A DRY RUN]` — digit `3`, then `-A` — broke the match. `summary_history.txt` is the audit trail: it parsed every Phase-2 day through 6/12 and dropped to 0 the instant the phase label changed on 6/15.

Fix: `PHASE [\w.-]+ DRY RUN(?: A)?\]`. `[\w.-]+` matches any phase label (`2`, `3-A`, `3-B`, `4`…); `(?: A)?` accepts the no-suffix single-arm form **and** the control arm `… DRY RUN A]` while **excluding** variant `… DRY RUN B]`, so an A/B day summarizes the control arm only — consistent with the tracker paste. Reproduced in-sandbox: **0 → 24** on the single-arm log, **24 (not 48)** on the A/B log with no duplicate tickers; Phase 2 logs still parse.

> ANALYST NOTE: A textbook boundary bug — a single-digit assumption silently correct for 19 trading days, wrong the first morning the assumption changed. The class to watch in the rebuild is anywhere the phase string is parsed rather than passed. The two "0 signals" stanzas already in `summary_history.txt` stay as the record; a re-run appends a fresh correct entry with no new API spend.

### Go-Live Toolchain Hardening

* **Bats (all three):** `set PYTHONUTF8=1` (UTF-8 I/O regardless of Windows locale); an openpyxl self-check in `run_weekly_review.bat`; new `requirements.txt` (openpyxl) for the analysis layer.
* **run_daily.bat parser fix:** the `. was unexpected at this time.` error was unescaped parens — the literal `(non-fatal)` inside an `if errorlevel 1 (…)` block let cmd read the `)` as the block close. Rephrased the echo to drop the parens; the 9:30 run came through clean.
* **Harnesses h1–h4:** added `--since` / `--until` date slicing (module globals, **byte-identical default**) so Phase 3-A can be analyzed apart from the certified Phase 2 window.
* **Encoding:** UTF-8 file writes added to h1–h4 and the registry builder (cp1252 write trap).

### news_client.py — Freshness Sort (the only change to an otherwise-untouched file)

Verdict: **correctly unchanged** for Phase 3-A — it returns lists (no file writes, so the cp1252 trap can't reach it), and news is fetched once per ticker and reused across both A/B arms, so it needs no phase or variant awareness. One robustness add: a newest-first `sorted(... key="datetime" ..., reverse=True)` after the empty-guard in **both** fetchers, guaranteeing freshness independent of Finnhub's (undocumented, comment-only) ordering — a degraded response can no longer quietly hand Claude the week's oldest headlines.

### Tracker Structure + Cohort Wiring

Filled the K:N outcome formulas down to row **2000**; added Cohort **Section 4: Phase 3-A Cohorts** (40 holiday-aware date rows, 6/15–8/11, mirroring Section 1); extended the Dashboard fixed ranges. Recalc: **0 errors / 8,584 formulas**. The text-date-vs-datetime risk (Section 4 dates are TEXT `"2026-06-15"`; Signals dates are real `datetime`) was **proven** harmless via a throwaway +5d injection across three bands — the 6/15 cohort immediately read Sample 3 with bands populated and correct hit rates; the scratch copy was discarded. Section 4 row 53 reads `0 / insufficient` today by design (the sample formula counts only resolved +5d) and lights up when col-H is entered (~6/23).

### README + Risk-Engine Reconciliation

Rewrote the Phase-2-stale README to Phase 3-A reality: phase badge, Phased-Rollout table (Phase 2 closed, Phase 3-A current), a "Research & validation tooling" section (h1–h4, registry, the three runners, `--since`), `requirements.txt` setup, and the calibration outcome (50-59% @ 61.3%, near-miss 70%). Corrected **MAX_OPEN_POSITIONS 30 → 8** — a pure **doc lag**: the live "Active Rules" block prints 8, so the engine has enforced 8 all along; only the committed README said 30. `risk_engine.py` needs no edit (confirmed).

### EDGAR — Scoped to Phase 3 (decision, no code)

Decision: **do not build in 3-A; build at the Phase 3 boundary** as one `edgar_client.py`, shaped like `news_client.py` (lazy client, CIK cache, graceful `return []`, summarize-not-dump, `requests`/urllib only; risk_engine needs nothing). Scope = **fast catalysts** (Form 4 insider, 8-K material events) + **slow context** (10-Q/10-K MD&A + risk factors) + **optional** XBRL fundamentals (low value — duplicates Schwab P/E/EPS). **10-K folded in with 10-Q** — same submissions feed and the same MD&A/risk-factor parser, near-zero incremental cost, richer annual Item 1A.

> ANALYST NOTE: The methodological key, and the reason this waited. The 3-A guardrail and cohort were calibrated on **news-only** input. Turning EDGAR onto the live path mid-phase would change what the guardrail was measured against and confound the 3-A cohort. So it enters as a **measured A/B arm** (reuse H2: A = news, B = + EDGAR), not a baseline upgrade — evidence first, calibrated baseline preserved. The roadmap's two SEC rows (2.5 fundamentals + 3 10-Q) were folded into a single Phase 3 SEC/EDGAR line to match.

### Repo Reconciliation + Push

Reconciled the local working set against the public repo (17 commits): `analyze_log.py`, `README.md`, and `news_client.py` updated; the four harnesses, the three runners, `parse_log_to_tracker.py`, and `requirements.txt` added (never committed before). `.gitignore` confirmed secure — `.env`, `token.json`, `logs/`, the tracker, and the paste TSVs all excluded (docs and tracker intentionally local). Staged a flat, byte-faithful **13-file bundle** (`.bat`s CRLF-preserved); push commands provided. The sandbox can't authenticate to the repo, so the push itself is Rob's to run.

---

## 2026-06-16 — Phase 3-A Day 2: First Live Near-Misses (VTI, NVDA) Logged; Near-Miss Tab Repaired

**Phase:** 3-A (advisory-only), Day 2
**Status:** 6/16 run captured — the first Phase 3-A BUY signals, both near-misses. VTI (68%) and NVDA (65%) recorded to the Near-Miss BUYs tab (rows 14–15, pending outcomes). The tab was repaired in passing: relabeled to span both phases, verdict box resolved, and the drifted +10d cells on rows 11–15 restyled. 6/15 re-run confirmed 0 near-misses; the 6/15 cohort's +5d is still pending (~6/23).

### 6/16 Run — First Phase 3-A BUYs

24 signals, **2 BUY / 22 HOLD** — the first BUYs of Phase 3-A (6/15 was 24/24 HOLD). Both are scouts that landed in the 60-69% near-miss band and were rejected by the 70% threshold (risk engine APPROVED 22 / REJECTED 2):

| Ticker | Conf | Miss | DQ | Price | 5-day context |
|---|---|---|---|---|---|
| VTI | 68% | −2 pt | HIGH | $372.15 | +3.94% run into its 52-wk-high zone |
| NVDA | 65% | −5 pt | MEDIUM | $209.12 | +4.35% recovery |

Average confidence 56.5% (up from 55.1% on 6/15); bands firmed toward the 60s — 11 in 40-59 / 11 in 60-69 (vs 6/15's 17 / 6). HIGH DQ 15/24. Pasted to Signals rows 480–503. (The 5/18 cohort's first **+20d** date also came due today — informational only; Phase 2's verdicts are closed on the +5d/+10d windows.)

> ANALYST NOTE: Both near-misses are momentum-driven (5-day run-ups), echoing the Phase 2 pattern where 60-69% BUYs clustered on recent strength. VTI at HIGH DQ is the cleaner probe — the project's read is that HIGH-DQ, non-NVDA near-misses are the least-confounded threshold tests. Their outcomes (+5d 6/24, +10d 7/1) are the first live evidence on whether KEEP-70% holds in Phase 3-A.

### Near-Miss Registry — Two New Entries

Logged VTI and NVDA to the **Near-Miss BUYs** tab (rows 14–15) on the existing schema — return and was-right formulas in place, +5d/+10d price cells left as pending yellow inputs (+5d resolves 6/24, +10d 7/1). COHORT SUMMARY ranges extended to row 15: **tab total now 11** (was 9); the resolved-outcome stats are unchanged — 9 complete +5d, 44.4% hit, avg −2.38% — since the two new rows are pending. 6/15 contributed none (24/24 HOLD). (These are additive to the *logged* set, not the registry reconciliation: the Phase-2 band-BUY backfill flagged on 6/12 — tab at 9 vs the ~17 the logs imply, the missing 6/4–6/9 entries — remains the open `build_near_miss_registry.py` auto-gen item for Phase 3.)

### Near-Miss Tab Repairs

The tab had drifted (the registry-maintenance thread from the Phase 2 close). Three fixes, recalc clean at 0 errors:

* **Relabeled** — title now spans "Phase 2 + Phase 3-A"; subtitle marks rows 5–13 as Phase 2 (closed 6/12) and 14+ as Phase 3-A. Kept one continuous list (no section split) since the COHORT SUMMARY aggregates all rows.
* **Verdict resolved** — the box still read "to be decided 2026-06-10"; now "KEEP 70% (resolved 2026-06-05)", pointing at the actual outcome (+5d hit 44% ≤ 50%, avg −2.4% ≤ 0%) against the criteria already listed below it.
* **Rows 11–15 +10d cells** — the +10d price/return/was-right cells (J/L/N) had lost their fills (plain white vs the yellow-input / gray-formula convention); restyled to match the completed rows. Filled the +10d **dates** — H11 6/15, H12/H13 6/17 — each set to 5 trading days after that row's own +5d date.

> ANALYST NOTE: r12/r13's +5d dates read 6/10, where five trading days from the 6/2 signal lands on 6/9 — likely a hand-entry drift. The +10d dates I filled follow each row's existing +5d, so they stay internally consistent; if a +5d is later corrected, its +10d shifts by the same amount. Source-of-truth flag, not a blocker.

---

## 2026-06-17 — Phase 3-A Day 3: First +20d Cohorts Confirm Magnitude Growth to 20 Days; Near-Miss +10d at 1/9

**Phase:** 3-A (advisory-only), Day 3
**Status:** 6/17 run captured (24/24 HOLD, clean). The first +20d outcomes resolved — 5/18 and 5/19 — and both extend the magnitude-growth finding to the 20-day horizon (2-for-2). Three more near-miss +10d outcomes landed, all NO, dropping the +10d hit rate to 1/9. The 50-59% guardrail holds (live 59.3%). Phase 3-A's own +5d is still pending (~6/23).

### 6/17 Run + Integrity

24 signals, **24/24 HOLD** — no BUYs, so no new near-misses (VTI 58% and NVDA 55% sat below the 60-69% band). Rows 504–527, every ticker/account/confidence/DQ matching the log. Recalc clean (**0 errors / 8,592 formulas**); totals reconcile — **523 signals** (451 Phase 2 + 72 across 6/15–17), BUY 19 (17 Phase 2 + the two 6/16 near-misses), the AG/FTI price-only backfills still inert. +5d coverage now reaches the 6/10 cohort (403/523, 77%). One data note: 6/17's prices are captured at sub-cent precision (NVDA $207.5015, AIQ $65.475, CBRS $223.795) where 6/15–16 were 2-decimal — harmless for the return math, flagged for source-of-truth, not corrected.

### First +20d Cohorts — Magnitude Growth Extends to 20 Days

The first two +20d outcomes resolved (5/18 due 6/16, 5/19 due 6/17; 24 each — the only cohorts matured to +20d). Absolute-move trajectory:

| Cohort | \|move\| +5d | +10d | +20d | avg ret +5d → +20d |
|---|---|---|---|---|
| 5/18 | 4.51% | 5.69% | **6.72%** | −0.32% → −1.96% |
| 5/19 | 5.25% | 6.09% | **7.17%** | +0.06% → −2.43% |

Both grow **monotonically** through +20d, so the Phase 2 magnitude finding (8/9 cohorts, +5d→+10d) **extends cleanly to the 20-day horizon — now 2-for-2.** Direction drifted net negative in both (−2.0%, −2.4% at +20d).

> ANALYST NOTE: The cleanest statement yet of why magnitude — not the retired accuracy-decay — is the robust finding. HOLD is a short-horizon signal: by +20d the typical absolute move is ~7%, far outside the 3%-band "no significant move" thesis the HOLD encodes. The signal isn't so much *wrong* at +20d as *out of scope* — its predictive window is ~5 days and the move keeps compounding past it. Carry into the Phase 3 horizon design.

### Near-Miss +10d — Extended Set Still 0-for-3, Hit Rate 1/9

The three +10d prices prepped on 6/16 were filled — NVDA 6/1, GLD 6/2, NVDA 6/2 — **all NO** (−4.12%, −4.87%, −4.87%). The Near-Miss tab is now 9-of-11 complete on +10d: **hit rate 11.1% (1/9)**, down from 16.7%, avg −3.43%. Every post-lock extended near-miss has now also failed at +10d (the +5d extended set closed 0-for-5; +10d echoes it).

> ANALYST NOTE: Corroborates **KEEP 70%** from the +10d angle — 60-69% BUYs convert at ~11% over ten days. The lone winner stays SCHD 5/21 (the one HIGH-conviction non-NVDA name). VTI/NVDA 6/16 are the first Phase 3-A near-misses, still pending (+5d 6/24, +10d 7/1).

### Guardrail / Coverage

Live +5d accuracy by band: **50-59% leads at 59.3%** (115/194), clear of 60-69% (50.7%, 37/73) and 40-49% (46.0%, 58/126). The lead has eased from the certified **61.3%** as more +5d resolved past the close — expected drift, ordering intact. DQ ordering also holds (HIGH 59.3% > MEDIUM 50.9% > LOW 44.4%). Section 1 (Phase 2) frozen — 10 of 17 cohorts hold the pattern. Section 4 (Phase 3-A) all pending; no live guardrail data until ~6/23.

---

## 2026-06-18 — Phase 3-A Day 4: 5/20 +20d Makes Magnitude Growth 3-for-3; Near-Miss Registry Backfilled to 19; Guardrail Compression Traced; H1 Harness Live-Ready

**Phase:** 3-A (advisory-only), Day 4
**Status:** 6/18 run captured (24/24 HOLD, clean — no near-misses). In the day's data, the third +20d cohort (5/20) keeps the magnitude-growth streak at 3-for-3, and the 6/11 Phase 2 cohort's +5d resolved Pattern NO. Three workstreams were set up alongside the daily: the Phase-2 near-miss registry was **regenerated from the Signals tab (11 → 19 rows)**, closing the standing backfill item; a **guardrail-compression trace** was built and run; and the **H1 lag-trace harness was dry-run** against live data and is ready to fire on 6/23. Tomorrow is Juneteenth (closed) — no new data until Mon 6/22.

### 6/18 Run + Integrity

24 signals (rows 528–551), all HOLD / risk APPROVED, every ticker/account/confidence/DQ matched to `signals_2026-06-18.log`. **No near-misses** — VTI and NVDA scouts both at 58%, below the band. Recalc clean: **0 errors / 8,592 formulas**. Totals reconcile — **547 signals** (451 Phase 2 + 96 across 6/15–18), **BUY 19** (unchanged). Three cohorts resolved today: 6/11 +5d, 6/4 +10d, 5/20 +20d.

> ANALYST NOTE: Sub-cent prices now run two sessions (6/17 + 6/18) — e.g., JPM $332.5063, VTI $369.3401 — so the higher-precision capture is the new standard, not a one-off. Several DQ values shifted vs 6/17 (AIQ HIGH→MEDIUM, DOW MEDIUM→HIGH, WMT/XLU HIGH→MEDIUM); normal day-to-day news-availability variation, not drift.

### Third +20d Cohort (5/20) — Magnitude Growth 3-for-3

| Cohort | abs move +5d → +10d → +20d | +20d avg ret |
| --- | --- | --- |
| 5/18 | 4.51 → 5.69 → 6.72% | −1.96% |
| 5/19 | 5.25 → 6.09 → 7.17% | −2.43% |
| 5/20 | 5.54 → 6.28 → **7.09%** | **−3.09%** |

5/20's absolute move grows monotonically like the first two — the magnitude finding now holds across **all three matured +20d cohorts (3-for-3)**, extending the 8/9 Phase 2 +10d result cleanly to the 20-day horizon.

> ANALYST NOTE: The +20d direction is net negative in all three and deepening (−1.96 → −2.43 → −3.09%), but the three +20d windows overlap and all close in the mid-June trough (6/16–6/18) — this is largely the same drawdown read from three near-adjacent start points, not three independent directional signals. The robust, in-scope finding is magnitude; the directional drift is a market-state artifact and should not be over-read. Same implication as the +10d work: HOLD's predictive window is ~5 days and the move keeps compounding past it.

### 6/11 Phase 2 Cohort +5d — Pattern NO; Section 1 Nearly Matured

6/11's +5d resolved: Section 1 row 23 populated at **50-59% = 50.0% (n=12)** — did not clear both neighbours, Pattern **NO**. The across-cohort tally is now **10 of 18 hold**. **6/12 is the last Phase 2 cohort still pending +5d** (resolves ~6/22 after Juneteenth); once it lands, Section 1 is fully matured. This does not touch the certified aggregate — the GO/NO-GO guardrail is the band hit rate, not the per-cohort count.

### Near-Miss Registry Backfilled — 11 → 19 (KEEP-70 Firmed)

Closed the standing backfill item by **regenerating the registry from the Signals tab** via `build_near_miss_registry.py` (the source-of-truth auto-gen tool), rather than hand-patching the drifted tab. All 17 Phase 2 BUYs are scout/SCHD signals in the 0.62–0.68 band (every Phase 2 BUY is a near-miss); the old tab held 9 of them plus the two 6/16 Phase 3-A entries. The regenerated tab is **19 rows, date-sorted, 7 LOCKED (≤6/1) + 12 EXTENDED (>6/1)**, with three corrections the auto-gen caught:

* the genuine **6/2 NVDA @ $227.93** (−8.66% +5d, NO) is now included — it had been missing entirely;
* the **6/3 GLD / 6/3 NVDA** pair is correctly dated 6/3 (was mis-labelled 6/2), and 6/3 NVDA's confidence corrected to **0.66** (the Signals value);
* **6/16 NVDA** confidence corrected **0.68 → 0.65** — a hand-entry error the old tab carried.

Stats (closing prices, sourced from Signals): **LOCKED +5d 4/7 = 57.1%** (the immutable Q2 verdict basis, avg −0.90% — matches the frozen baseline), **LOCKED +10d now 1/7 = 14.3%** (avg −3.02%); **EXTENDED +5d 3/8 = 37.5%** (avg −3.01%), +10d 0/4 (avg −5.11%); **combined +5d 7/15 = 46.7%**. KEEP 70% is firmer than ever — near-miss BUYs convert below a coin flip at +5d and worse at +10d.

> ANALYST NOTE: The self-validation surfaced a real change — **LOCKED +10d moved from the frozen 1/6 to 1/7** because 6/1's +10d resolved NO *after* the Q2 baseline was frozen (its +5d, the actual verdict basis, is untouched). The frozen `LOCKED_BASELINE['comp10']` is now stale-by-one; the +10d portion is informational, not the invariant. Separately, `build_near_miss_registry.py --emit-master-copy` had a cross-workbook style bug (`nc._style = c._style` copies a StyleArray *index*, which points into the source workbook's number-format table and scrambles in the destination — symptom: price cells rendered as 1900 dates). Fixed to copy style *attributes* (number_format string + copied font/fill/border/alignment) plus merge ranges. The standalone `near_miss_registry.xlsx` was always correct; only the master-copy was affected.

### Guardrail-Compression Trace

Built `guardrail_trace.py` (h1–h4 mould: reads Signals, computes per-cohort and running-cumulative +5d band hit rates, prints a trajectory table, renders a chart). The cumulative 50-59% lead over 60-69%:

* built to a **peak +12.3pt at 6/1** (50-59% at 62.3%, 60-69% at 50.0%);
* **compressed through the early-June shock cohorts** — 6/2 and 6/3 came in at 30% / 36% per-cohort on the 50-59% band, pulling the cumulative down;
* has since **stabilised in the high-50s** (57.4 → 58.7% over the last seven cohorts) while 60-69% hovers 48–51%;
* currently **+7.4pt** (50-59% 58.7%, 60-69% 51.3%, 40-49% 44.8%).

> ANALYST NOTE: The certified **61.3%** is exactly the cumulative 50-59% rate **at 5/29** — i.e., the n=216 snapshot was the pre-shock window. The "61.3 → 58.7" drift is therefore the early-June shock cohorts dragging the cumulative down from its peak, not a steady erosion. The lead gap narrowed from its peak (+12.3 → +7.4pt) but is not trending toward crossover — the band ordering holds with comfortable margin and the 50-59% line has flattened. Watch metric, not an alarm: the 60-69% band's per-cohort n is small (3–6) and noisy, so a few strong small-n cohorts can move the gap.

### H1 Live-Readiness (Dry-Run)

Dry-ran the real `h1_lag_trace.py` against the current tracker (WMT). It runs clean and **ingests the Phase 3-A rows** — 6/12 and 6/15–18 appear in the trace with confidence + trailing-5d move, forward returns blank (pending +5d). It reproduces the Phase 2 baseline: **estimated update lag = 5 sessions** (corr(conf, trailing-move[t−L]) peaks +0.638 at L=5; −0.177 at L=0 — the lag signature), the WMT +10d arc **−15.19 → −1.66** (self-corrected), and the calibration guardrail with 50-59% leading (**61.3%**, the certified n=216 reference — distinct from the live 58.7% above; different scope, both correct). Verdict: harness is wired and ready.

> ANALYST NOTE — 6/23 runbook: once the 6/15 +5d resolves (~Mon 6/23), re-run `python h1_lag_trace.py --tracker claude_equity_bot_tracker.xlsx --ticker WMT --out-dir viz` on the full tracker — the 6/15–18 WMT rows begin populating forward returns. H1 success = the lag estimate shrinks from ~5 toward 0–1 sessions and corr(conf, trailing-move) rises from −0.177, **without** degrading the 50-59% +5d lead. Per-ticker n is small (~19 cohorts), so the Phase 3-A lag estimate stabilises only after ~1–2 weeks of resolutions; the 6/23 run is the first end-to-end proof on live data, with the real comparison maturing through early July.

---

## 2026-06-22 — Phase 3-A Day 5: Magnitude Growth 4-for-4 at +20d; Section 1 Closed Out (6/12 Holds); Guardrail Lead Widens to +8.2pt

**Phase:** 3-A (advisory-only), Day 5
**Status:** First session after Juneteenth. 6/22 run captured (24/24 HOLD, clean — no near-misses). The day's outcomes: 5/21's +20d makes magnitude growth **4-for-4**, and 6/12's +5d (the last Phase 2 cohort) **holds the 50-59% pattern**, fully maturing Section 1 at 11 of 19. The strong 6/12 cohort widened the guardrail lead back to **+8.2pt**, reversing last week's compression. The near-miss registry was refreshed (both 6/12 near-misses hit +5d) and the Guardrail Trace sheet extended to 6/12. Phase 3-A's own +5d is still pending — the first live cohort (6/15) resolves **tomorrow, 6/23**.

### 6/22 Run + Integrity

24 signals (rows 552–575), all HOLD / risk APPROVED, every ticker/account/confidence/DQ matched to `signals_2026-06-22.log`. **No near-misses** — VTI 58%, NVDA 55%, both below the band; PWR 63% is in-band but a HOLD, not a BUY. Recalc clean: **0 errors / 8,634 formulas**. Totals reconcile — **571 signals** (451 Phase 2 + 120 across 6/15–22), **BUY 19** (unchanged). Three cohorts resolved: 6/12 +5d, 6/5 +10d, 5/21 +20d.

> ANALYST NOTE: Confidence drift worth watching — DOW eased to 38% (from 42%) and GM to 58% (from 62%), while PM rose to 65% and PWR to 63% (its first appearance in the 60-69 band, as a HOLD). The DQ shift (NTR HIGH→MEDIUM) is the usual day-to-day news-availability variation.

### +20d Magnitude Growth — 4-for-4 (5/21)

| Cohort | abs move +5d → +10d → +20d | +20d avg ret |
| --- | --- | --- |
| 5/18 | 4.51 → 5.69 → 6.72% | −1.96% |
| 5/19 | 5.25 → 6.09 → 7.17% | −2.43% |
| 5/20 | 5.54 → 6.28 → 7.09% | −3.09% |
| 5/21 | 5.05 → 5.18 → **6.55%** | **−3.36%** |

5/21 grows monotonically, taking the +20d magnitude tally to **4-for-4** — but its +5d→+10d step is the shallowest of the four (5.05 → 5.18, nearly flat), with most of the growth back-loaded into the +10d→+20d window. The +20d direction keeps deepening (−1.96 → −2.43 → −3.09 → −3.36%); same caveat as before — these four +20d windows overlap and all close in the mid-June trough (5/21's ends 6/22), so it is largely one drawdown read from four near-adjacent start points, not four independent directional signals.

### Section 1 Closed Out — 6/12 Holds the Pattern

6/12's +5d resolved (the last Phase 2 cohort): Section 1 row 24 populated at **50-59% = 60.0% (n=10)**, clearing both neighbours, Pattern **✓ YES**. Across-cohort final tally: **11 of 19 cohorts hold** (up from 10 of 18). **Section 1 is now fully matured** — every Phase 2 cohort (5/18 → 6/12) has +5d data. The per-cohort count (11/19 ≈ 58% individually hold) is supplementary; the certified guardrail is the aggregate band rate below, which governs GO/NO-GO.

### Guardrail Lead Widens to +8.2pt — Compression Reversed

Live +5d bands: 50-59% **58.8%** (127/216) > 60-69% 50.6% (41/81) > 40-49% 45.0% (63/140). The 50-59 lead over 60-69 is now **+8.2pt**, up from +7.4pt on 6/11 — the strong 6/12 cohort (50-59 at 60% per-cohort) nudged the cumulative 50-59 up and 60-69 down. This confirms last week's read: the 61.3 → 58.7 drift was stabilisation, not a crossover trend; the lead gap over the last three cohorts is roughly flat (+8.6 → +8.2pt). The `guardrail_trace.py` trajectory and the embedded **Guardrail Trace** sheet were refreshed through 6/12.

### Near-Miss Registry Refreshed — EXTENDED +5d to 5/10

Regenerated from the updated Signals tab (the two 6/12 near-misses and 6/5's +10d had resolved since the 6/18 build): **EXTENDED +5d 3/8 → 5/10 = 50.0%** (both 6/12 near-misses hit — NVDA +1.48%, VTI +0.87%), avg −2.2%; **+10d completed 4 → 5** (6/5 NVDA). LOCKED is unchanged at **4/7 = 57.1%** (immutable Q2 basis). **Combined +5d now 9/17 = 52.9%** (up from 46.7%).

> ANALYST NOTE: The combined near-miss hit rate ticked above a coin flip (52.9%), but **KEEP 70% holds** — and the reason is EV, not hit rate: average returns stay negative (LOCKED −0.90%, EXTENDED −2.2%), so lowering the threshold would still buy into net-negative-expectancy trades. The 6/12 pair won small (+1.48%, +0.87%); the cohort's losers lose more than its winners win. The verdict logic (anchored on the locked cohort + the negative average) auto-confirms KEEP 70%.

### Phase 3-A — First Live +5d Tomorrow

All five Phase 3-A blocks (6/15–22) are still 0/24 on +5d. The first live cohort, **6/15, resolves tomorrow (6/23)** — the first data point measured against the 50-59% guardrail in live advisory mode, and the trigger to re-run `h1_lag_trace.py` to begin the lag-compression comparison.

---

# Active Touch Points

*Last updated: 2026-06-22 (Phase 3-A Day 5 — +20d magnitude growth 4-for-4; Section 1 closed out at 11/19, 6/12 holds; guardrail lead widened to +8.2pt; near-miss EXTENDED +5d 5/10, KEEP 70% holds; first live Phase 3-A +5d resolves 6/23)*

**Completed:**

* 5/26 (Day 6) — Captured 5/18 cohort outcomes (first calibration signal)
* 5/27 (Day 7) — Captured 5/19 cohort outcomes + first near-miss BUY (NVDA -3.62%, NO)
* 5/28 (Day 8) — Captured 5/20 cohort outcomes; **Q1 calibration verdict locked: CALIBRATED**
* 5/29 (Day 9) — Captured 5/21 cohort + first near-miss BUY win (SCHD +1.22%, YES); run_daily.bat fix verified
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
* 6/15 (Phase 3-A Day 1) — **PHASE 3-A LIVE** (advisory-only, no orders). First run 24/24 all HOLD, risk APPROVED → tracker rows 456–479 (Section 4 cohort wired, pending +5d; Dashboard 475 total, **50-59% guardrail holds 58.8%**; AG/FTI confirmed price-only backfills, inert). **analyze_log.py phase-regex fix** (`\d` matched one digit → `[PHASE 3-A DRY RUN]` parsed 0; broke exactly on the cutover; fixed to phase-agnostic `[\w.-]+`, control-arm-only; reproduced 0 → 24, A/B 24 not 48). Go-live hardening: PYTHONUTF8 + openpyxl self-check + requirements.txt in the bats; run_daily.bat paren-parse fix; harness `--since`/`--until`; UTF-8 writes; news_client.py newest-first sort. Tracker K:N filled to row 2000 + Section 4 added (recalc 0 errors); date-coercion proven via throwaway injection. README rewritten to Phase 3-A (MAX_OPEN_POSITIONS doc-lag 30 → 8; engine was always 8). EDGAR scoped to Phase 3 as one edgar_client.py (Form 4/8-K + 10-Q/10-K MD&A; A/B arm, not baseline; roadmap folded to one line). Repo reconciled; 13-file bundle staged for push.
* 6/16 (Phase 3-A Day 2) — 6/16 run **24 signals, 2 BUY / 22 HOLD** — first Phase 3-A BUYs, both near-misses (**VTI 68% HIGH @ $372.15**, **NVDA 65% MEDIUM @ $209.12**, scouts, rejected by the 70% threshold). Logged to Near-Miss tab rows 14–15 (+5d 6/24, +10d 7/1; **tab 9 → 11**, resolved stats unchanged at 44.4% / −2.38%). Near-Miss tab repaired: relabeled (Phase 2 + Phase 3-A); **verdict resolved → KEEP 70%** (was stale "to be decided 6/10"); rows 11–15 +10d cells restyled (drifted fills) + +10d dates filled (H11 6/15, H12/H13 6/17 = +5d + 5 trading days). 6/15 re-run confirmed 0 near-misses (24/24 HOLD); 6/15 cohort +5d pending (~6/23).
* 6/17 (Phase 3-A Day 3) — 6/17 run **24/24 HOLD** (no near-misses; VTI 58% / NVDA 55% below band). **First +20d cohorts resolved (5/18, 5/19): magnitude grows to 20 days** — |move| 4.51 → 5.69 → **6.72%** (5/18), 5.25 → 6.09 → **7.17%** (5/19), both monotonic, **2-for-2** extending the 8/9 Phase 2 finding; +20d direction net negative (−2.0%, −2.4%). **Near-miss +10d: 3 new (NVDA 6/1, GLD 6/2, NVDA 6/2), all NO → hit rate 1/9 = 11.1%** (from 16.7%), corroborates KEEP 70%. Guardrail holds: live 50-59% **59.3%** (eased from certified 61.3%) > 60-69% 50.7% > 40-49% 46.0%. Totals reconcile (523 = 451 + 72, BUY 19); +5d coverage through 6/10 (77%); recalc 0 errors. 6/17 prices at sub-cent precision (flagged). Phase 3-A +5d pending (~6/23).
* 6/18 (Phase 3-A Day 4) — 6/18 run **24/24 HOLD** (no near-misses; VTI/NVDA 58% below band). **5/20 +20d: magnitude growth 3-for-3** — |move| 5.54 → 6.28 → **7.09%**, monotonic; +20d −3.09% (deepening, but overlapping mid-June windows). **6/11 cohort +5d Pattern NO** (50-59% 50%, n=12; across-cohort 10 of 18); 6/12 last Phase 2 +5d pending (~6/22). **Near-miss registry backfilled 11 → 19** via build_near_miss_registry.py (7 LOCKED + 12 EXTENDED): genuine 6/2 NVDA added, 6/3 pair re-dated, 6/16 NVDA conf 0.68→0.65; **combined +5d 7/15 = 46.7%**, LOCKED +5d 4/7 (immutable) / +10d 1/7 (6/1 resolved NO post-freeze); fixed the script cross-workbook style bug. **guardrail_trace.py built + run** — 50-59 lead peaked +12.3pt (6/1), compressed post-shock to +7.4pt (6/11), stabilising, no crossover (certified 61.3% = cum at 5/29). **h1_lag_trace.py dry-run** — runs clean, ingests Phase 3-A rows, reproduces baseline (lag 5 sessions, arc −15.19→−1.66); ready for 6/23. Totals reconcile (547 = 451 + 96, BUY 19); recalc 0 errors; sub-cent prices 2nd session (new standard).
* 6/22 (Phase 3-A Day 5) — 6/22 run **24/24 HOLD** (no near-misses; VTI 58% / NVDA 55% below band, PWR 63% in-band HOLD). **5/21 +20d: magnitude growth 4-for-4** — |move| 5.05 → 5.18 → **6.55%**, monotonic (shallow +10d step, back-loaded); +20d −3.36% (deepening, overlapping mid-June windows). **Section 1 closed out — 6/12 holds** (50-59% 60%, n=10, Pattern YES; final **11 of 19** cohorts hold; Section 1 fully matured). **Guardrail lead widened to +8.2pt** (50-59% 58.8% > 60-69% 50.6% > 40-49% 45.0%) — the 6/12 cohort reversed the compression (was +7.4pt at 6/11). **Near-miss registry refreshed**: EXTENDED +5d 3/8 → **5/10** (both 6/12 near-misses hit, +1.48% / +0.87%), +10d completed 4 → 5 (6/5 NVDA); combined **9/17 = 52.9%**; LOCKED 4/7 immutable; **KEEP 70% holds** (negative avg returns despite hit-rate uptick — net-negative EV). Guardrail Trace sheet refreshed through 6/12. Totals reconcile (571 = 451 + 120, BUY 19); recalc 0 errors. Phase 3-A +5d still pending — 6/15 resolves 6/23.

**Upcoming (every date is a trading day unless noted):**

* **~Tue 6/23** — **First Phase 3-A +5d (6/15) resolves** → enter col-H for the 6/15 block → Section 4 + Was-Right populate — first live data vs the 50-59% guardrail; **re-run `h1_lag_trace.py`** to start the lag-compression comparison. 5/22 +20d also resolves (next +20d cohort; tally 4-for-4).
* **Wed 6/24** — VTI & NVDA near-miss +5d (the 6/16 entries) — enter +5d prices, then regenerate the registry
* **Wed 7/1** — VTI & NVDA near-miss +10d
* **Phase 3-A workstream** — H1 prior-5-day price input (harness ready; first live read 6/23) → H3 thesis-stability next; H2 A/B harness available (run `run_ab_test.bat` for a multi-day stretch once H1 matures, ~July); EDGAR (Form 4/8-K/10-Q/10-K) deferred to Phase 3 as a measured A/B arm
* **Toolkit** — near-miss registry + Guardrail Trace **auto-refresh from Signals** (`build_near_miss_registry.py` + `guardrail_trace.py`, wired into `run_weekly_review.bat`); re-run on any data change
