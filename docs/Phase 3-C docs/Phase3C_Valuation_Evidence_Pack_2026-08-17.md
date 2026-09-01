# Phase 3-C — Valuation Instrument Evidence Pack, 2026-08-17

*Claude Equity Bot · v1.0 · companion evidence for `Phase3C_Valuation_Instrument_Scoping_WS4_v1.md`, computed against the operator's own files after the project root was connected 2026-08-17. **Everything below is recomputed from source**; nothing is transcribed from the scoping memo, and where the two disagree the memo is corrected here rather than quietly amended.*

> **Inputs, all read at source.** `logs\claude_equity_bot_tracker.xlsx` (the MASTER — the report copy `tracker_with_registry.xlsx` was **not** used as an input, per §6 of the workflow), `logs\signals_2026-08-17.log`, `edgar_client.py`, `risk_engine.py`, `schwab_client.py`, `xbrl_sweep.py`. Nothing was written to the operator's machine.
>
> **NOTHING HERE IS RULED. No endpoint, arm, threshold, robustness condition, n or rate is changed.** The frozen E4-2 volatility-tier table is **not** re-cut. The ±3% band is **not** re-baselined.
>
> *Advisory-only · no orders · not financial advice.*

---

## 0 · Conclusions first

**Three of the scoping memo's claims are wrong and are corrected below. Two of the corrections run against the memo's own argument.** They are stated before the new findings, in the order the record's house practice requires.

**The single most consequential new result:** on the 15 EDGAR-covered names, measured HOLD accuracy is **statistically indistinguishable from a zero-skill dispersion baseline** — observed breach 49.48% (430/869) against a row-weighted model expectation of 48.27%, `z = +0.715`, two-sided `p = 0.475`. The memo argued the band measures dispersion rather than skill. **At n=869 on the covered set, the data does not distinguish the two at all.**

| # | Finding | Severity |
|---|---|---|
| C-1 | **CORN was not dropped.** The memo's composition claim is wrong; the error overstated the risk | correction |
| C-2 | **Two concepts the memo called absent are already extracted.** `EXTRACT_SCHEMA` is 9, not 6 | correction |
| C-3 | **The CAPM cross-check leg of the memo's central recommendation is not supportable on this data** | correction, against the memo |
| F-1 | Covered-15 HOLD accuracy indistinguishable from zero-skill dispersion (`p = 0.475`) | ★★ |
| F-2 | **`FINANCIAL_CONCEPTS` is walked by the anchor-period vote** — adding a flow concept can change what every other line reports | ★★ verified in source |
| F-3 | **4 of 15 names would re-tier at current n**, and the one boundary the freeze flagged is not among them | ★★ |
| F-4 | Band spread now **53.4 points** observed; model predicts 50.5 | ★★ |
| F-5 | **NVDA is the worst-fitting name** (−9.32pt) and the one both live instruments most depend on | ★★ |
| F-6 | Independent route reproduces the open **GLD 2026-07-02** price finding | corroboration |
| F-7 | Today's cohort is **26 rows against E4's frozen 24**; two names outside the population | ★ |

---

## 1 · Corrections to the scoping memo

### C-1 · CORN was not dropped from the watchlist. The memo's §3.3 composition claim is wrong.

The memo read the 8/14 close's *"CORN was SOLD and USO BOUGHT on 2026-08-14"* as a watchlist swap and priced the composition effect as a low-volatility name leaving. **The master says otherwise** `[V]`:

| session | n | roster change | CORN's `Account` field |
|---|---|---|---|
| 2026-08-13 | 25 | — | `Individual` |
| 2026-08-14 | 25 | **none** — no USO row exists | `Individual` |
| 2026-08-17 | **26** | **USO added** | **`Scout`** |

**CORN remains in the watchlist and in the accuracy series; only its account field moved `Individual` → `Scout`, and it moved on 8/17, not 8/14.** USO entered on **8/17**. The 8/14 close describes a *portfolio transaction*; the *signal watchlist* retained the name as a Scout. **The watchlist and the portfolio are different populations and the record's phrasing conflates them.**

**Consequence for the memo:** the composition effect is not a swap that removes a low-dispersion name (CORN, `P(breach)` 31.9%). It is the **addition** of one name to a 25-name cohort, which dilutes rather than shifts. The memo's *"−1.69 to −2.69 points"* is **withdrawn**. The correct statement is that adding one name of unknown dispersion to 25 moves expected cohort accuracy by at most `(P_USO − mean_P)/26`, i.e. **under 1 point on any plausible USO dispersion** `[?]` — USO has no resolved rows yet, so its own median is still unmeasurable.

**Direction: the error overstated the risk.** Recorded because that is the direction that gets caught late.

### C-2 · Two concepts the memo listed as absent are already extracted

Read at source — `edgar_client.py` L265–285, `FINANCIAL_CONCEPTS`, **11 entries**:

| # | label | kind | first-preference concept |
|---|---|---|---|
| 1 | Revenue | flow | `RevenueFromContractWithCustomerExcludingAssessedTax` (+ DP-3C-q swap) |
| 2 | Gross profit | flow | `GrossProfit` |
| 3 | Operating income | flow | `OperatingIncomeLoss` |
| 4 | Net income | flow | `NetIncomeLoss` |
| 5 | Diluted EPS | flow | `EarningsPerShareDiluted` |
| 6 | Operating cash flow | flow | `NetCashProvidedByUsedInOperatingActivities` |
| 7 | **Total assets** | instant | `Assets` |
| 8 | Total liabilities | instant | `Liabilities` |
| 9 | Shareholders equity | instant | `StockholdersEquity` |
| 10 | **Cash and equivalents** | instant | `CashAndCashEquivalentsAtCarryingValue` |
| 11 | Long-term debt | instant | `LongTermDebtNoncurrent`, `LongTermDebt` |

**The memo's §7 wrongly listed `CashAndCashEquivalentsAtCarryingValue` and `Assets` as absent.** Both are present. **`EXTRACT_SCHEMA = 9`** (L148), not the 6 the 8/03 notes entry records — it has advanced three times since.

**This materially reduces the Tier-1 build.** With Total assets, Cash, Liabilities, Equity and Long-term debt already extracted:

- **MVA needs ZERO new concepts.** The packet's first MVA form (p. 1067) is `Market value of stock − Total common equity` = market cap − book equity. Price is in hand; book equity is line 9; shares come from the implied count (`Net income ÷ Diluted EPS`, lines 4 and 5). Likewise `M/B = market cap ÷ book equity`, so **`MVA / BookEquity = M/B − 1` exactly**, and both are computable today.
- **Net invested capital ≈ (LT debt + ST debt + Equity − Cash)** needs **one** concept: short-term debt.
- **NOPAT** needs **two**: income tax expense and pretax income.

**Revised: Tier 1 needs 3 new concepts, not 4 — and one of the three is materially safer than the other two (F-2).**

### C-3 · The CAPM cross-check leg of the memo's recommendation is not supportable on this data

The memo's §4.3 argued the inverted `WACC_implied` is defensible **because** it can be checked against a CAPM `WACC` built on a beta computed from the master. **The beta layer computes cleanly and the result will not carry that argument.**

Betas were computed by **two independent routes** — an assembled close series (from the `Price +5d/+10d/+20d` columns) and the `Price at Signal` column, different provenance:

| | route 1 ρ | route 2 ρ | agree within 0.20? |
|---|---|---|---|
| tickers | 23 | 23 | **21 / 23** |
| mean \|Δρ\| | — | — | **0.068** |

**The two routes agree, so the computation is right and the data is internally consistent.** The problem is what it says:

| ticker | ρ vs SPY, measured | ρ typical, real markets | β measured | β typical |
|---|---|---|---|---|
| VTI | 0.939 | ~0.98 | 0.985 | ~1.00 |
| QQQ | 0.920 | ~0.93 | 1.532 | ~1.15 |
| **SCHD** | **0.098** | **~0.85** | 0.208 | ~0.85 |
| **XLU** | **−0.127** | **~0.55** | −0.165 | ~0.55 |
| **AAPL** | **0.082** | **~0.70** | 0.547 | ~1.15 |
| **JPM** | **0.238** | **~0.70** | 0.406 | ~1.10 |
| **GLD** | **0.496** | **~0.10** | 1.111 | ~0.10 |

**The broad-index proxies behave correctly; individual equities and style/sector ETFs do not.** SCHD is a US dividend large-cap fund whose real correlation with SPY runs ~0.85; 0.098 is not a noisy estimate of 0.85. Two candidate explanations were **tested and rejected**:

1. *Quote-timing drift* (the documented +2 to +98 minute `Px@signal` offsets) would attenuate same-day correlation — **rejected**, because route 1 uses closes and agrees with route 2.
2. *Small sample* — `SE(ρ) ≈ 1/√57 = 0.132`, so AAPL's 0.082 sits **4.7 SE** from a true 0.70. **Rejected**; sampling error cannot produce this.

**What remains is a question about the price data's provenance, and it is marked `[?]` rather than asserted.** The check that settles it costs one minute: take any three of `AAPL`, `SCHD`, `XLU` and compare the master's close for a single date against an external source. If they match, the correlation structure is real and unusual; if they do not, the price series is not what CAPM assumes.

**Consequence for the memo, stated because it weakens my own recommendation:** until that check is done, `WACC_implied` from equation (II) has **no independent CAPM benchmark to be checked against**, which was the specific reason §4.3 preferred it over a point estimate. The inversion is still the right shape — it still has one free parameter instead of five, and it still fails loudly rather than quietly — but **the memo overstated the strength of the cross-check.**

---

## 2 · F-1 · The covered-15 breach rate, and what it closes

The memo's §3.3 carried a self-correction: it had compared a covered-15 expected breach rate against an all-names observed rate. **That is now computed properly** `[V]`, from all 1,387 resolved +5d rows in the master:

| population | breach | rate | accuracy-equivalent |
|---|---|---|---|
| **ALL names** | 633 / 1,387 | **45.64%** | 54.36% |
| **COVERED 15 only** | 430 / 869 | **49.48%** | **50.52%** |
| T-C dark 8 + CBRS | 203 / 518 | **39.19%** | 60.81% |

**The self-correction was right and the size of the contamination is 10.3 points.** The dark names — six of which are broad-market or sector funds whose dispersion is structurally suppressed by diversification — sit 10.3pt below the covered set. Any comparison that mixes them is invalid.

**Apples-to-apples, at last:**

```
row-weighted model expectation (covered 15) = 48.27%
observed covered-15 pooled breach           = 49.48%
gap                                         = +1.21 pt
n = 869    z = +0.715    two-sided p = 0.475
```

**The model's HOLD calls on the covered set are not distinguishable from a zero-skill dispersion baseline at n=869.** The sign is very slightly adverse — the model breaches marginally *more* than pure dispersion predicts — but 1.21pt on this n is noise.

**This is a stronger statement of the record's own 7/30 finding than the record currently makes, and it should be read carefully rather than dramatically.** It does **not** say the signal generator is worthless: it says *the ±3% band cannot see whether it is*, because the band's output is dominated by a quantity the generator does not control. That is exactly why the Phase 4 register §3 says these criteria *"do not transfer"* — and it is the argument for a price-referenced yardstick, made in a single number instead of a paragraph.

---

## 3 · F-2 · ★★ VERIFIED CODE HAZARD — the memo's §1.2 understated this

The memo warned that adding XBRL concepts could leak into the rendered prompt block. **Read at source, the coupling is through three paths, and the third is much worse than a leak.**

| path | location | effect of appending to `FINANCIAL_CONCEPTS` |
|---|---|---|
| extraction | `extract_financials` Pass 2, L1524 | the concept is extracted — intended |
| **rendering** | `format_financials(fin, max_lines=len(FINANCIAL_CONCEPTS))`, L1646 | **renders the new line AND raises the truncation limit** |
| **anchor-period vote** | `extract_financials` Pass 1 (L1492) and `_headline_flow_bucket` (L1268), **both loop `FINANCIAL_CONCEPTS` filtering `kind == "flow"`** | **can change which period EVERY OTHER LINE reports** |

**The third path is the N-1 defect class — YTD figures under a quarter label — reachable by a route nobody has walked yet.** The anchor is chosen by a majority vote among *flow* concepts, and `_headline_flow_bucket` exists precisely because a wider poll got this wrong: its own analyst note (2026-08-10) records N-1 arriving *by a second route* on RTX, where 70 year-to-date footnote entries overruled a 4-1 headline vote for the quarter and the block rendered six-month revenue under a "Q2" header.

**Adding flow concepts for V-block use adds voters to that election.** Two of the three concepts Tier 1 needs are flows:

| concept | kind | anchor-vote risk |
|---|---|---|
| short-term debt (`DebtCurrent` / `ShortTermBorrowings`) | **instant** | **none** — instants do not vote |
| income tax expense (`IncomeTaxExpenseBenefit`) | **flow** | **votes; can move the anchor** |
| pretax income | **flow** | **votes; can move the anchor** |

**Proposed, not ruled: `VBLOCK_CONCEPTS` must be a genuinely separate list**, excluded from `format_financials`, with `max_lines` pinned to `len(FINANCIAL_CONCEPTS)` explicitly rather than by default, **and excluded from both `extract_financials` Pass 1 and `_headline_flow_bucket`.** The negative test is not optional and must be shown to fail: rendered block byte-identical across all 15 covered names with the V-block list populated and empty, **and the `fin=N@date` anchor identical on all 15**. The `fin=` tag already carries the anchor date, so the tag itself is the regression fixture — no new instrument needed.

**Build consequence: short-term debt is safe to add and the two flow concepts are not.** A first V-block that computes MVA, `M/B` and net invested capital while *assuming* a tax rate is strictly safer than one that extracts the tax rate — which inverts the usual preference for measured over assumed inputs, and is worth stating plainly because it is counter-intuitive.

---

## 4 · F-3 · ★★ Four of fifteen names would re-tier at current n

**The frozen table is not re-cut.** This is drift monitoring, and the freeze doc's own remedy — *"report the read with NVDA reclassified as a sensitivity check, not a re-cut"* — is what applies.

| tier@freeze | tk | frozen median | current median (n=57–58) | drift | would re-tier? |
|---|---|---|---|---|---|
| LOW | JPM | 1.834% | 1.633% | −0.201 | |
| LOW | GLD | 1.931% | 1.943% | +0.012 | |
| LOW | CORN | 1.990% | 2.031% | +0.041 | |
| LOW | RTX | 2.021% | 2.009% | −0.012 | |
| **LOW** | **WMT** | 2.559% | **2.730%** | +0.171 | **LOW → MID** |
| **MID** | **GM** | 2.592% | **2.428%** | −0.164 | **MID → LOW** |
| MID | PM | 3.188% | 2.968% | −0.220 | |
| **MID** | **FTI** | 3.201% | **3.813%** | **+0.612** | **MID → HIGH** |
| MID | PWR | 3.343% | 3.322% | −0.021 | |
| MID | NVDA | 3.595% | 3.489% | −0.106 | |
| HIGH | DOW | 3.598% | 3.861% | +0.263 | |
| HIGH | NKE | 3.598% | 3.566% | −0.032 | |
| **HIGH** | **AAPL** | 3.779% | **3.445%** | −0.334 | **HIGH → MID** |
| HIGH | MSFT | 3.910% | 3.714% | −0.196 | |
| HIGH | SND | 5.517% | 5.652% | +0.135 | |

**★ The freeze document flagged exactly one boundary as its sensitivity risk — the NVDA/DOW near-tie at 0.003pp — and that boundary did NOT flip.** NVDA is still below DOW at current n. **Four boundaries that were never flagged did flip.** The flagged risk was the wrong one to worry about, and the mechanism is legible: a 0.003pp gap is fragile to *any* movement, but the four that actually moved did so on genuine drift (FTI +0.612pp is the largest in the table, and FTI's `+14.6%` at +5d on the 8/07 cohort is visible in the 8/14 close's movers list).

**Why this matters to E4-2 and not merely to bookkeeping.** §3.3's fallback pools ADJACENT against COVERED-QUIET *within tier*. If the fallback dominates the read — and §3.5 pre-registered that risk explicitly — then **4 of 15 names are pooled against a volatility peer group they no longer belong to**, which is precisely the confound the tier table exists to remove. **The pre-registration already requires the fallback/primary split to be reported at every read; this adds that the re-tier count be reported alongside it.** Proposed, not ruled.

---

## 5 · F-4 and F-5 · The band priced per name, and NVDA

At current n, all 15 covered names, model against observation:

| tk | median \|r5\| | σ_5d | z | P(breach) model | **observed** | n | err (pt) |
|---|---|---|---|---|---|---|---|
| JPM | 1.633% | 2.422% | 1.2387 | 21.5% | **22.4%** | 58 | −0.87 |
| GLD | 1.943% | 2.881% | 1.0412 | 29.8% | 32.8% | 58 | −2.98 |
| RTX | 2.009% | 2.978% | 1.0074 | 31.4% | 32.8% | 58 | −1.38 |
| CORN | 2.031% | 3.011% | 0.9965 | 31.9% | 28.1% | 57 | +3.83 |
| GM | 2.428% | 3.600% | 0.8333 | 40.5% | 43.1% | 58 | −2.64 |
| WMT | 2.730% | 4.048% | 0.7411 | 45.9% | 44.8% | 58 | +1.03 |
| PM | 2.968% | 4.400% | 0.6818 | 49.5% | 48.3% | 58 | +1.26 |
| PWR | 3.322% | 4.925% | 0.6091 | 54.2% | 55.2% | 58 | −0.93 |
| AAPL | 3.445% | 5.107% | 0.5874 | 55.7% | 55.2% | 58 | +0.52 |
| **NVDA** | 3.489% | 5.173% | 0.5799 | 56.2% | **65.5%** | 58 | **−9.32** |
| NKE | 3.566% | 5.287% | 0.5674 | 57.0% | 55.2% | 58 | +1.87 |
| MSFT | 3.714% | 5.506% | 0.5449 | 58.6% | 62.1% | 58 | −3.49 |
| FTI | 3.813% | 5.653% | 0.5307 | 59.6% | 58.6% | 58 | +0.94 |
| DOW | 3.861% | 5.724% | 0.5241 | 60.0% | 62.1% | 58 | −2.05 |
| SND | 5.652% | 8.380% | 0.3580 | 72.0% | **75.9%** | 58 | −3.83 |

**F-4 — the distortion is larger than the memo's frozen-table version.** Observed `P(marked right)` runs **JPM 77.6% to SND 24.1% — a 53.4-point spread** with signal quality held identical. The one-parameter model predicts a 50.5-point spread. **Model and observation agree on the size of the distortion**, which is the point: the spread is a property of the *names*, not of the model used to describe them.

**F-5 — NVDA is the single worst-fitting name in the table, and it is the name the project's two live instruments most depend on.** NVDA breaches 65.5% against 56.2% predicted, **−9.32pt, more than double the next-largest miss.** Its median move is ordinary (3.489%, mid-table) but it breaches like a much more volatile name — the signature of fat tails or trending, i.e. moves that cluster rather than distributing around zero.

Set that beside the concentration the record already carries:

| instrument | NVDA's share | source |
|---|---|---|
| KEEP-70 registry | **28 of 43 rows (65.1%)**, 9 of 18 episodes | 8/14 close |
| KEEP-70 resolved rows, at the 8/05 reading | **25 of 32 (78.1%)** | DP-3C-m |
| H4 resolved base | **8 of 17 (47.1%)**; 12 of 17 in two names | 8/14 close |
| DP-3C-l/m ledger | 2 of 3 episodes | 8/14 close |

**The name that dominates every live instrument is the name where the dispersion model fits worst.** Neither fact is new; the conjunction is. It does not invalidate anything — KEEP-70 and H4 are sign tests on directional and near-miss rows, not band tests — but it means **the dispersion correction that works across the other fourteen names would work least well on the name carrying the most weight**, and any future volatility-scaled secondary metric should report NVDA separately rather than pooled. Proposed, not ruled.

---

## 6 · F-6 · Corroboration — an independent route reproduces an open price finding

A close-price series was assembled per ticker from the `Price +5d`, `+10d` and `+20d` columns by indexing the cohort-date sequence. **The same close is written by three different cohorts at three different horizons, so the construction self-validates** — this is the "triple-resolution day" property the 8/14 close checks by hand, applied across the whole record at once.

```
distinct (ticker, date) closes assembled : 1,392
disagreements                            : 3
common grid                              : 58 dates, all 24 tickers present on all 58
gap structure                            : 45 one-day, 10 weekend, 2 holiday-weekend — no missed sessions
```

**Three disagreements in 1,392, and two of them are the same already-open item:**

| ticker | date | values | status in the record |
|---|---|---|---|
| **GLD** | **2026-07-02** | **378.13 vs 379.13** ($1.00) | **carried open as "the GLD 7/02 price finding"** (8/14 close) |
| SPY | 2026-06-10 | 725.43 vs 725.42 ($0.01) | not in the record — rounding/paste artifact |

**The GLD 7/02 finding is reproduced by a route that was not looking for it**, from a different construction than whatever originally surfaced it. Recorded as corroboration, in the same spirit as the 8/14 review's two-route DOW disposition. The AG 6/26 finding carried alongside it in the record does **not** surface as a cross-horizon conflict, so it is a different defect shape.

---

## 7 · F-7 · Today's cohort against the E4 population

`[V]` from the master and `logs\signals_2026-08-17.log`:

| | 8/13 | 8/14 | **8/17** |
|---|---|---|---|
| cohort rows | 25 | 25 | **26** |
| E4 frozen population | 24 | 24 | 24 |
| outside the population | SPCX | SPCX | **SPCX, USO** |
| covered names with a populated `E[…]` | 16 | 16 | **17** |
| `E[no filings]` | 9 | 9 | 9 |
| `fin=degraded` | 0 | **1** (SND) | **2** |

**The 8/14 close recorded that a moving denominator *"needs a ruling before Monday's run."* Monday's run has happened, and the cohort now carries two out-of-population names rather than one.** No ruling appears in the record between then and now. The E4-1 and E4-2 denominators are stated as 24 and the cohort is 26; **the gap is documented rather than closed.**

Also `[V]` from today's tags, without comment beyond recording it:

- **DOW still reads `fin=7@2026-03-31` against `periodic=10-Q@2026-07-24`** — the 115-day lag persists on its third consecutive session, exactly as the 8/13 corrigendum predicted it would (upstream XBRL lag, cleared as **not** a defect). No new disposition needed.
- `fin=` line counts across the 17 covered names run **3 to 11**. The maximum equals `len(FINANCIAL_CONCEPTS) = 11` `[V]`, confirming the 8/02 truncation fix still holds. **One name renders only 3 lines** — for the V-block that name has essentially no valuation surface, and per-name input completeness should be reported (the `vq=` field proposed as DP-V4) rather than a value being produced from three lines.
- **The rendered EDGAR block is still not logged.** The 8/14 close promoted this from housekeeping to **blocking**; it remains open. The memo's §7 rendered-side question therefore stays `[?]` from the log — but it is closed from source code instead, which is stronger evidence than the log would have provided.
- **`FTI` HOLD at confidence 0.72** today — above the 0.70 BUY gate but a HOLD, so no gate is engaged and no registry row is created. Recorded because a 0.72 in the confidence column invites exactly the Dashboard B16 misreading the record already carries (`COUNTIF(...">=0.7")` = 49, of which 42 are HOLDs).
- **NVDA BUY 0.74, `Scout`** — under DP-3C-m this **extends episode 3** (opened 2026-08-13) to a third session; it does not open a fourth.

---

## 8 · What Schwab supplies, and what it does not

Read at source, `schwab_client.py` L110–156. The quote payload carries a `fundamental` block:

| field | available | use to the V-block |
|---|---|---|
| `peRatio` | equities only (suppressed for ETFs) | **P/E with no XBRL TTM assembly** — avoids the N-1 period surface entirely |
| `eps` | equities only | TTM EPS, so implied shares = `NetIncome_TTM ÷ eps` |
| `divYield` | **all names** | **`D₀/P₀` directly — feeds the JPM dividend branch**, `r_s = D₁/P₀ + g` (packet p. 1072) |
| `lastPrice`, `closePrice`, 52-week range, volumes | all | price inputs |
| **shares outstanding** | **absent** | — |
| **market capitalisation** | **absent** | — |

**Consequence:** market cap must still come from an *implied* share count, so `MVA` and `M/B` inherit that error and it **propagates linearly** — it does not cancel. `M/B = market cap ÷ book equity`, and market cap is `shares × price`, so a 1% share-count error is a 1% `M/B` error and a larger relative error in `MVA = market cap − book equity` whenever the two are close.

**Two things this does improve on the memo.** `peRatio` removes the TTM-assembly hazard the memo flagged for P/E, and `divYield` makes the JPM dividend branch (§5.3) cheaper than the FCF branch rather than an awkward exception — the input it needs is already flowing on every name, every session.

---

## 9 · Revised build order

Ordered by assumption count and by the F-2 hazard, not by interest.

| step | what | new concepts | anchor risk | blocked by |
|---|---|---|---|---|
| **1** | `M/B`, `MVA / BookEquity = M/B − 1`, per-name and per-cohort | **0** | **none** | nothing |
| **2** | Per-name band pricing + scaled-band secondary (§5), NVDA reported separately | **0** | **none** | nothing |
| **3** | Re-tier drift monitor reported at each E4-2 read (§4) | **0** | **none** | nothing |
| **4** | Net invested capital, `EVA` sign, `WACC_implied` from equation (II) with assumed tax rate | **1** (instant) | **none** | `VBLOCK_CONCEPTS` separation + negative test |
| **5** | Measured tax rate → `NOPAT`, `ROIC`, `OP`/`CR` | **2** (flow) | **HIGH** | step 4's negative test proven on `fin=` anchors |
| **6** | Beta / CAPM / portfolio beta | 0 | none | **C-3's provenance check** |
| **7** | Full `Vop` / `HV` chain | ~5 more | HIGH | steps 4–6, and it may never be worth it (§5.2 of the memo) |

**Steps 1–3 need no code in `edgar_client.py` at all** — they run off the master and the existing tag. They are also the three that bear on live, unruled questions (the E4-1 threshold, the E4-2 fallback, KEEP-70's and H4's basis). **Steps 5 and 7 are where the assumption count and the defect risk both jump**, and the memo's §5.2 sensitivity arithmetic argues step 7 may never repay its cost.

---

## 10 · Still open

| item | needed to close |
|---|---|
| **C-3's provenance question** | compare the master's close for one date on `AAPL`, `SCHD`, `XLU` against an external source. **This gates step 6 and the memo's §4.3 cross-check argument** |
| USO's dispersion | ~10 resolved +5d rows; first resolves ~2026-08-24 |
| SPCX classification | filer status; it entered 2026-08-13 and carries a populated tag with `fin=11` |
| E4 denominator ruling | outstanding since 8/14; cohort is now 26 against a stated 24 |
| Rendered EDGAR block in the log | still blocking per the 8/14 close |
| True portfolio weights | the master carries no position sizes, so `b_p = Σwᵢbᵢ` cannot be weighted; equal-weighting is a placeholder and **not** a portfolio beta |

---

*Advisory-only · no orders · not financial advice.*
