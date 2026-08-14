# Phase 3-C — E4 Endpoint Pre-Registration

*Claude Equity Bot · v1.2 · v1.0 drafted 2026-08-02 and written BEFORE go-live as Kickoff §5 requires · v1.1 AMENDED 2026-08-05 · v1.2 AMENDED 2026-08-11, all still before the E4 clock starts. Provenance unchanged for v1.0. The v1.1 amendments entered DP-3C-l (2026-08-04), DP-3C-m and DP-3C-n (both 2026-08-05) and rewrote §3's E4-2 block per DP-3C-n. **v1.2 enters DP-3C-q (2026-08-11)**, which changes which XBRL concept the revenue line reports on — the first amendment to alter what the model RECEIVES since DP-3C-g, and recorded here for the same reason. No acceptance threshold, robustness condition or n is changed by either revision; §3.1 states that explicitly for v1.1 and §5's DP-3C-q block states it for v1.2. Advisory-only · no orders · not financial advice.*

\---

## 0 · Conclusions first

**All three endpoints are readable inside the phase. None is event-starved.** This is the first pre-registration in the project where that could be stated from measured supply rather than hoped for, and it is the direct answer to the failure that closed G1 and G2.

||Rate|Time-to-read|
|-|-|-|
|**G1 (3-B, failed)**|0.053 adverse tracer episodes/session|3 more episodes = **57 sessions (\~11 weeks)**|
|**G2 (3-B, failed)**|1 gate-flip in 1,243 rows|indeterminate|
|**E4-1**|24 DQ readings/session|**\~10 sessions (2 weeks)**|
|**E4-2**|\~7.6 filing-adjacent rows/session|**\~20 sessions (4 weeks)**|
|**E4-3**|0.81 8-K events/session|20 events = **\~25 sessions (5 weeks)**|

**Two design rulings are load-bearing and both reverse the Scope Spec §6 draft:**

1. **E4-2 is a WITHIN-COHORT comparison, not a pre/post-era comparison.** The 2026-07-30 identity — cohort accuracy ≈ band-breach count, `r = −0.9650` exact in 47 of 47 cohorts — means a pre/post accuracy read measures market dispersion, not EDGAR. Comparing treated and untreated names *on the same day* holds dispersion constant by construction.
2. **Stratify on what a name actually receives, not on the era stamp.** Coverage is not binary; three tiers below.

\---

## 1 · Coverage — measured, and it corrects the record

`\[V]` 2026-08-02, `edgar\_client.py --coverage`, 90-day window.

|Tier|n|Names|What EDGAR delivers|
|-|-|-|-|
|**T-A · live event flow**|**14**|AAPL, CORN, DOW, FTI, GM, JPM, MSFT, NKE, NVDA, PM, PWR, RTX, SND, WMT|8-K and/or Form 4 in window, plus periodic MD\&A|
|**T-B · periodic only**|**1**|GLD|10-Q MD\&A; 0 8-K and 0 Form 4 in 90d|
|**T-C · dark**|**8**|AIQ, AG, NTR, QQQ, SCHD, SPY, VTI, XLU|Empty section — contributes nothing|
|**skipped (DP-3)**|**1**|CBRS|Excluded to the Q4 2026 Path-A review|

**Practical coverage: 15/24 = 62.5%** — names that will emit a non-empty prompt section on a typical day. The `--coverage` summary line reads 17/24 = 70.8% because it counts all-time form presence; AG and QQQ have historical filings but nothing in window and no periodic, so their sections render empty. **62.5% is E4's denominator.**

### Three corrections to Kickoff §2, recorded as corrections

|§2 claim|Measured|Direction|
|-|-|-|
|AG and NTR `\[?]` — may file 40-F/6-K|**Confirmed foreign filers.** Uncovered for the 3-C filing set. AG files genuine Form 4s but none in 90d|as flagged|
|CORN — "no filings at all", 39 MEDIUM rows untreatable|**CIK 0001471824; 2 8-Ks in 90d; 10-Q filed 2026-05-11**|**against §2**|
|GLD — "no filings at all", 33 MEDIUM rows untreatable|**CIK 0001222333; 10-Q filed 2026-05-05**|**against §2**|

§2 argued \~100 MEDIUM-DQ rows sit in a category the treatment cannot touch. Two of the three named tickers are reachable; only AIQ (29 rows) holds. **The correction runs toward the treatment, and is flagged as such** — it makes EDGAR look better than the pre-registered scoping did, which is exactly the direction that warrants the most scepticism. It is recorded because it is measured, not because it is convenient, and the raw `--coverage` output is the exhibit.

\---

## 2 · Event supply

`\[V]` 90-day trailing window, 62 trading sessions, covered set only.

|Event|90d|/month|/session|
|-|-|-|-|
|8-K|50|16.9|**0.81**|
|Form 4|206|69.7|**3.32**|

Form 4s cluster — one corporate event produces several insiders' filings. At an assumed 3 filings per cluster, distinct Form-4 ticker-days run \~1.11/session. Busiest names: **WMT (2 8-K + 49 F4), MSFT (3 + 32), JPM (11 + 21)**.

**Concentration warning, carried forward from DP-10's unresolved cap.** WMT alone supplies 24% of all Form 4 volume, and the top three names supply 59%. E4-2 must report its per-ticker split, because a "significant" filing-adjacent effect that is 60% WMT is the same near-single-name footprint that made G2 unscoreable.

\---

## 3 · Endpoints

### E4-1 · DQ-mix shift *(descriptive; no criterion attached)*

**Question.** Does the filing section change the HIGH/MEDIUM/LOW distribution the model emits?

**Read.** HIGH/MED/LOW counts per cohort, T-A+T-B names only, pre-era (`A-S1D1-B1`) vs post-era (`A-S1D1-B1-E1`). T-C names are the internal control — their DQ must not move, and if it does, something other than EDGAR changed.

**Rate.** 15 covered readings/session. **Readable at \~10 post-deploy cohorts, \~2 weeks.**

**Pre-committed interpretation.** Descriptive only. DP-4 holds — filings do not feed `data\_quality`, so any shift is model-side reasoning, and a shift is neither pass nor fail. **A shift in T-C names invalidates the read** and points at a confound.

\---

### E4-2 · Filing-adjacent accuracy *(primary)* — AMENDED 2026-08-05 per DP-3C-n

**Question.** On a given session, do names with a recent filing score better than covered names without one?

**AMENDMENT NOTICE.** v1.0 specified a within-cohort comparison of raw accuracy between ADJACENT and COVERED-QUIET arms. That specification is superseded. **It measured realised volatility, not EDGAR**, for the reason set out in §3.0 below. The amendment changes the *comparison unit* and the *reporting set*. **It changes no threshold, no robustness condition and no n** — see §3.1.

\---

#### 3.0 · Why the v1.0 read was invalid

`\[V]` 2026-08-05, from `claude\_equity\_bot\_tracker.xlsx` column formulas and all 1,160 resolved HOLD rows.

Column N reads `=IF(H="","",IF(D="HOLD",IF(ABS(K)<0.03,"YES","NO"),…))` and column K reads `(H−G)/G`. For a HOLD row, **"Was Claude Right (5d)" *is* |Return+5d| < 3%** — the exact complement of a band breach. Tested across every resolved HOLD row: `(N=="YES") ⟺ (|ret5| < 3%)` holds **1,160 of 1,160**. On the HOLD population accuracy and 1 − breach rate are **the same number**; the correlation between them is `r = −1.000000` by construction.

E4-2's population is HOLD rows only. Substituting the identity, the v1.0 read asked:

> *Do names that just filed an 8-K or Form 4 cross the ±3% band **less often** than covered names that did not?*

8-Ks are earnings and material events. Form 4 clusters follow corporate events. **Those windows carry elevated realised volatility by construction.** The v1.0 read therefore had a **mechanically expected negative sign independent of any treatment effect**, and its pre-committed NEGATIVE disposition would have fired on a volatility artifact and entered the permanent record as evidence that EDGAR harms the signal.

This is the same trap this document caught once and half-fixed. §3 v1.0 correctly rejected a pre/post read because dispersion varies *across time*, and moved to within-cohort. **Within-cohort holds the market constant. It does not hold name-level event volatility constant — and event volatility is precisely what defines the strata.**

Direct precedent: **Q4-R** found data quality's raw +15.5pt accuracy gap collapse to **+0.5pt across 9 tickers** once volatility was held constant within-ticker, because MEDIUM-DQ names simply move about twice as much.

\---

#### 3.1 · What does NOT change

Stated first, and separately, because amending an endpoint is exactly where a bar slips quietly.

|Carried over unchanged||
|-|-|
|Effect-size threshold|**≥ 5pt**|
|Robustness condition 1|sign survives **leave-one-cohort-out**|
|Robustness condition 2|sign survives **dropping the largest single ticker**|
|Pre-registered n|**150 resolved ADJACENT rows**|
|Population|**HOLD rows only**|
|Arm definitions|ADJACENT / COVERED-QUIET / DARK, K = 5 trading days, unchanged|
|Disposition vocabulary|POSITIVE / NEGATIVE / INSUFFICIENT, unchanged|

**Nothing in this amendment lowers a bar.** If the amended design cannot reach its n inside the phase, the endpoint is entered **INSUFFICIENT TEST CONDITIONS** under Kickoff §5's binding rule, and the bar is not lowered to manufacture a close.

\---

#### 3.2 · PRIMARY READ — within-ticker paired difference

For each covered ticker (T-A and T-B) that supplies **at least 3 resolved rows in each arm**:

```
d_ticker = breach_rate(ADJACENT rows, +5d) − breach_rate(COVERED-QUIET rows, +5d)
```

Pool the per-ticker differences `d\_ticker`. **The same instrument appears in both arms, so volatility is held exactly constant by construction** — the design Q4-R's decisive control used.

Report: the pooled mean `d`, the per-ticker table of `d\_ticker` with each ticker's n in each arm, and the count of tickers qualifying.

**Sign convention, stated before any number is seen:** a **negative** `d` means ADJACENT names breach *less* often, i.e. the treatment arm scores *better*. POSITIVE / NEGATIVE dispositions are read on the accuracy-equivalent, not on the breach rate, to keep §3.1's threshold in its original units.

\---

#### 3.3 · FALLBACK — volatility-tier matching

For covered tickers that cannot supply both arms at n ≥ 3, pool by **volatility tier**.

- **Tier assignment:** each ticker's own historical **median |+5d move|** computed from `claude\_equity\_bot\_tracker.xlsx` across the full record, cut into three tiers.
- **The tier table is built and FROZEN before the first E4 cohort resolves.** This is a **go-live prerequisite** that did not exist before 2026-08-05. It is entered as **change-order step 8b** (RW 2026-08-05), on equal footing with step 8's audit and selftest, because both gate the same event — the end of the control-cohort window. Freezing the table after the first E4 cohort resolves would be fitting a control to the data it exists to control for. **Frozen 2026-08-10** `\[V]` — 15 covered tickers, terciles of 5, computed from all resolved rows as of the freeze date (see the E4-2 Volatility-Tier Table, FROZEN 2026-08-10 exhibit, delivered alongside this amendment). LOW: JPM, GLD, CORN, RTX, WMT. MID: GM, PM, FTI, PWR, NVDA. HIGH: DOW, NKE, AAPL, MSFT, SND. The MID/HIGH boundary (NVDA 3.595% vs DOW/NKE 3.598%) is a near-tie, flagged in the exhibit as a sensitivity check rather than re-cut.
- Compare ADJACENT vs COVERED-QUIET **within tier**, pooled across tiers.

Report the count of tickers reading under §3.2 and the count falling to §3.3, always. A read dominated by the fallback is weaker than one dominated by the primary and must say so.

\---

#### 3.4 · Mandatory reporting — REPLACED

v1.0 required *"every accuracy figure is reported with its band-breach count."* **That safeguard is vacuous.** On a HOLD-only population it reports one number twice, so it detects nothing.

**Replaced by, for every stratum:**

1. **Mean signed return** — not determined by accuracy.
2. **Dispersion (sd, population)** — not determined by accuracy.
3. **UP / DOWN breach split** — distinguishes a rising tape from a falling one.
4. **Per-ticker split**, with WMT's share stated explicitly (carried from v1.0).
5. **The raw unadjusted ADJACENT-vs-COVERED-QUIET gap**, reported as a **DESCRIPTIVE CONTROL that is EXPECTED NEGATIVE on volatility grounds alone**. Pre-registering that expectation is the point: it prevents a figure such as −8pt being read later as a treatment effect.

\---

#### 3.5 · Rate and time-to-read — REVISED, and the revision may cost time

v1.0 measured \~7.6 ADJACENT rows/session (32% of output), giving 150 rows in \~20 sessions.

**The row supply is unchanged. The *usable* supply may be lower**, because the primary read requires a ticker to appear in **both** arms:

- **A name that is almost always ADJACENT contributes nothing to §3.2.** WMT supplies 24% of all Form 4 volume and is the leading candidate; MSFT and JPM follow.
- Names that are almost always QUIET are equally uninformative.

**Recorded as a benefit, and flagged because it looks convenient:** this is *also* the fix for §2's concentration warning. A within-ticker design automatically neutralises the single-name footprint that made G2 unscoreable — the same change solves both problems. It is recorded because it follows from the design, not because it is welcome.

**Pre-committed now, while it is still a forecast rather than a concession:** if the amended design does not reach **150 resolved ADJACENT rows with an adequate qualifying-ticker count** by the exit review, E4-2 is flagged **INSUFFICIENT TEST CONDITIONS** and **the bar is not lowered**. The qualifying-ticker count is reported at the first read (\~10 cohorts) as an early supply check, and if it is starved at that point, say so then rather than at the exit.

\---

### E4-3 · 8-K event-window behaviour *(secondary; trace table)*

**Question.** Does raw model confidence move on the session after a material 8-K?

**Read.** For each 8-K on a T-A name, tabulate `confidence\_raw` on the filing date and the following session, with the 8-K item code. **Raw channel only** — D1 damping is a mechanical post-model rule and would contaminate a model-side read, exactly as the WS2 two-channel design established.

**Rate.** 0.81 8-K/session → **20 events in \~25 sessions (5 weeks)**.

**Pre-committed interpretation.** Trace table, WMT/GM style. Descriptive at n < 20. No disposition attaches; this endpoint exists to make the mechanism legible if E4-2 reads positive, and to show whether nothing moved if it reads negative.

\---

## 4 · What is NOT pre-registered, and why

|Not registered|Reason|
|-|-|
|Any endpoint gated on BUY/SELL volume|32 BUYs in 1,243 rows. G2 died here|
|Pooled all-24 pre/post accuracy|\~9 of 24 names untreatable by construction; dilutes any effect by \~⅓ before measurement (Kickoff §2)|
|Any filings → `data\_quality` coupling read|DP-4 holds. Separately blocked: no DQ-conditional design work until HIGH-DQ near-miss passes twice at n ≥ 12 (currently 6/13 = 46.2%, four consecutive declines)|
|+10d / +20d as primary|56% and 67% of HOLD rows breach the fixed band at those horizons; being wrong is the modal outcome. Reported as secondary with breach counts|
|MD\&A-quality endpoint|v1 takes a bounded extract with no LLM pass (DP-3C-a). No instrument exists to score it|

\---

## 5 · Decision points this document assumes

Both must be ruled and dated **before** `EQUITY\_EDGAR=1`.

|DP|Assumed|Status|
|-|-|-|
|**DP-2**|Single live arm, era `A-S1D1-B1-E1`; A/B stays terminated|**RULED - RW 8/2/2026**|
|**DP-3C-e**|Stratify by coverage tier (T-A / T-B / T-C), not by era alone|**RULED - RW 8/2/2026**|

DP-3, DP-4, DP-3C-a/b/c are implemented at their stated defaults and need only ratification.

**New and unruled — DP-3C-f.** AG and NTR are foreign private issuers filing 40-F/6-K. Extending the filing set would move them from T-C to T-A and raise practical coverage from 15/24 to 17/24. **Proposed: no change in v1.** It is a scope expansion, it lands after go-live, and adding it now would change the treatment mid-measurement.

**RULED 2026-08-02 — DP-3C-g.** The 3-C filing set includes **XBRL financial statements alongside the MD\&A extract**. Kickoff §1 pre-registered the set as "Form 4 · 8-K · 10-Q/10-K MD\&A extracts" under the heading "this and nothing more"; this ruling widens it. Rationale of record: the mandate is *primary-source* SEC filing context, MD\&A is management's narrative **about** the statements, and shipping the commentary without the numbers serves the letter of the scope against its purpose. Timing is the reason it is ruled now rather than later — the treatment is not yet live, so widening costs nothing, whereas the same widening after go-live would change the treatment mid-measurement.

**DP-3C-g does not disturb this document.** E4-1 reads the DQ mix; E4-2 keys on filing *adjacency* (8-K and Form 4 windows) and within-cohort strata; E4-3 keys on 8-K dates. None of the three conditions on which subsections are extracted, so no endpoint, arm, standard or rate changes. The one measured consequence is recorded in §6.

\---

**RULED 2026-08-04 — DP-3C-l. GATE-CLEARED DIRECTIONAL LEDGER.** A separate ledger is opened for directional signals that clear their **own** confidence gate — BUY at conf ≥ 70 or SELL at conf ≥ 65 — **regardless of risk-engine disposition**, applied retroactively across the full record. **DESCRIPTIVE ONLY:** it modifies nothing, gates nothing, and carries no pass/fail standard. Membership is deliberately independent of the `Decision` field so that a future change to `MAX\_OPEN\_POSITIONS` cannot silently redefine the population. Read: the existing +5d sign test, with the risk-engine `Decision` and its verbatim reason reported alongside each row and **not stratified on**. **Standard: NONE. Exit disposition, PRE-COMMITTED: INSUFFICIENT TEST CONDITIONS**, on measured supply of 2 events in 54 cohorts = 0.037/session, requiring \~540 sessions for n=20; stressed at **triple** the observed rate it still needs \~180 sessions, past any plausible 3-C exit, so the conclusion survives the uncertainty on a two-event estimate. Kickoff §5's binding rule applies: an endpoint whose supply cannot deliver a read inside the phase is entered as a **stated limitation**, not pre-registered and discovered later. **This is the first time in the project a starved endpoint was identified BEFORE the data arrived rather than at the exit review.** KEEP 70% is unchanged and remains supported at 13/32 = 40.6%.

**RULED 2026-08-05 — DP-3C-m. THE GATE-CLEARED LEDGER COALESCES.** DP-3C-l opened the ledger with per-row membership and no coalescing rule; one session later NVDA supplied a second row. **Ruling: consecutive sessions on the same ticker whose directional signal is unbroken and continues to clear its own gate constitute ONE episode, dated at FIRST CLEARANCE**, with the confidence path recorded and the +5d outcome measured from the first-clearance row. An episode **ends** when the ticker reverts to HOLD, flips direction, or falls below its gate for at least one session; a later re-clearance opens a new episode. Membership is otherwise unchanged. **Precedent: DP-6**, which moved G1 from cohorts to coalesced episodes on the ground that a period carrying no independent information must not be counted as though it did.

*Evidence `\[V]`:* NVDA reads HOLD 55/49/46/49/50 through 2026-07-31, then BUY **68 (8/03) → 72 (8/04) → 74 (8/05)** — one regime change followed by a strengthening stance, not three independent draws. The 8/04 and 8/05 rows share four of five resolution days, so their outcomes agree by construction.

*Ledger under the ruling — 3 rows become 2 episodes:*

|#|Opened|Signal|Ticker|Conf path|Risk decision|+5d|
|-|-|-|-|-|-|-|
|1|2026-06-26|SELL|CBRS|68|REJECTED — position count|+14.61% → **NO**|
|2|2026-08-04|BUY|NVDA|72 → 74|REJECTED — position count|resolves **2026-08-11**|

*Boundary note, not arbitrary:* the NVDA BUY run begins 8/03 but the **episode** begins 8/04, because membership keys on **gate clearance** and 8/03's 68 did not clear. The 8/03 row belongs to the KEEP-70 near-miss registry instead, so one continuous three-day BUY run contributes exactly one row to KEEP-70 and one episode here, with no double-count.

*Supply recomputed:* row-count basis 3/55 = 0.0545/session; **coalesced basis 2/55 = 0.0364/session**. Both sit inside DP-3C-l's pre-committed ×3 stress band (0.111/session), so **the INSUFFICIENT TEST CONDITIONS forecast stands without revision** and is strengthened.

*Known limitation, deliberately unfixed:* **the same serial-dependence problem applies to KEEP-70** — 25 of its 32 resolved rows are NVDA (78.1%), many consecutive-session repeats of one stance. DP-3C-m **does not touch KEEP-70**, because it is a currently readable criterion at n=32 and attaching a coalescing rule mid-flight would redefine a working gate's denominator — the hazard DP-3C-l rejected as option (D). Recorded as a limitation of KEEP-70's evidence base, not as a fixed problem, and it belongs in the memo explicitly if the 70% gate is ever revisited.

**RULED 2026-08-05 — DP-3C-n. E4-2 STRATIFIES ON VOLATILITY.** §3 is rewritten accordingly: primary read becomes a **within-ticker paired difference**, with **volatility-tier matching** as the fallback and the tier table **frozen before the first read**; mandatory reporting is replaced because the accuracy-plus-breach-count pairing is vacuous on a HOLD-only population. **No threshold, robustness condition or n is changed** (§3.1). Rationale of record: the band-breach identity is definitional (verified 1,160/1,160), so the v1.0 read measured realised volatility rather than the treatment, and its NEGATIVE disposition would have fired on an artifact. Q4-R is the direct precedent for the confound and for the within-ticker remedy.

*Timing is the reason this is ruled now rather than later:* **the E4 clock has not started**, so amending costs nothing, whereas the same amendment after the first read would be moving a criterion with data in view. This is the DP-3C-g argument applied a second time.

*Direction:* the ruling makes the phase **harder** — it converts a ready endpoint into one requiring a frozen vol-tier table as a new go-live prerequisite, and it may extend time-to-read. It runs against convenience and is recorded as such.


**RULED 2026-08-11 — DP-3C-q. TOTAL REVENUE SUPERSEDES THE CONTRACT-REVENUE COMPONENT, REVENUE LINE ONLY.** For the Revenue line only, the extract prefers the `Revenues` concept when the filer tags it **at the anchor period** and it exceeds the ASC 606 contract-revenue concept by more than 2%.

*Evidence of record* `\[V]` *2026-08-11, `xbrl\_sweep.py` across all 15 covered names:* GM tags `RevenueFromContractWithCustomerExcludingAssessedTax` at **$43.762B** for Q2 FY2026 and `Revenues` at **$48.026B for the same period**. GM's own 8-K states "revenue of $48.0 billion" — the total matches the press release to **0.05%** while the component sits **9.7% below it**. ASC 606 contract revenue excludes GM Financial's interest and leasing income, so for a filer with a captive finance arm the first entry in the preference list is a COMPONENT rendered under the label "Revenue". The model would have understated GM's top line by 9.7% and computed every margin off the wrong denominator.

*Why this is a distinct defect class, and why it matters to this document:* **the period was CORRECT.** This is not the 2026-08-10 anchor defect arriving again — it is orthogonal to it, and it is invisible to every internal-coherence check. GM's block passes the balance-sheet identity exactly (residual 0 after $1.641B of noncontrolling interest) and its implied share count is coherent at 925.5M. Only the comparison against the filer's own press release dissented. Recorded because §6's monitoring note and E4-1's "extraction is failing on some names" language both assume a failure would be VISIBLE in the block; this class is not.

*Scope is deliberately narrow.* Reordering the concept preference list outright would change what the model sees for all 15 covered names on evidence from one. The swap fires only when the total is MATERIALLY LARGER **and at the SAME period**, so it is a no-op where the filer tags one concept, tags them within the margin, tags a smaller `Revenues`, or tags a larger `Revenues` at a different date — the last guarding against reintroducing the mixed-period defect. Four of the nine regression fixtures are those no-op cases. **Verified post-ruling** `\[V]`: GM moves to $48.026B and reads 8K-AGREE at 0.05%; the revenue figures of the other 14 covered names are byte-identical to the pre-ruling sweep.

*Effect on this document's endpoints: NONE.* E4-1 reads the DQ mix; E4-2 keys on filing adjacency and within-ticker strata; E4-3 keys on 8-K dates and `confidence\_raw`. No endpoint, arm, threshold, robustness condition, n or rate changes. The frozen E4-2 volatility-tier table is computed from `claude\_equity\_bot\_tracker.xlsx` price history, not from XBRL, and is therefore untouched.

*Timing is the reason this is ruled now rather than later:* **the E4 clock has not started**, so amending costs nothing, whereas the same amendment after go-live would change the treatment mid-measurement. This is the DP-3C-g argument applied a third time.

*Direction, stated because it runs toward the treatment:* the change makes the EDGAR context **more accurate and more favourable-looking** for affected names, which is the direction warranting the most scepticism. It is adopted because the filer's own 8-K corroborates the larger figure to 0.05%, not because it is convenient — and the correction was found by an instrument built to look for exactly this, not noticed in passing.

\---

## 6 · Prompt-length asymmetry introduced by DP-3C-g

Recorded because it is a difference between E4-2's arms that is **not** the treatment under test.

The filing section grew from \~4 lines to \~14 for a covered name with statements. T-C (dark) names still receive nothing. So covered and dark names now differ in prompt length by more than they did, and prompt length is not a variable this phase intends to manipulate.

**Why it does not invalidate E4-2:** the primary read is ADJACENT vs COVERED-QUIET, and **both arms are covered names carrying the statements block**. The length difference sits between covered and dark, which is not the primary comparison. It would matter for a covered-vs-dark read, and no such read is pre-registered.

**Monitoring, not a criterion:** `input\_tokens` is already logged on every signal. Report mean input tokens by stratum in the first E4-1 read. A large unexplained gap *within* the covered set would indicate extraction is failing on some names, which is worth knowing regardless.

\---

## 7 · Exit-review inputs

At the 3-C exit each endpoint carries a disposition on the 3-A vocabulary — **VERDICT**, **DESCOPE**, **PARK** with triggers, or **INSUFFICIENT TEST CONDITIONS**. E4-2 is the only one with a pass/fail standard; E4-1 and E4-3 are descriptive by design and close as VERDICT-descriptive or INSUFFICIENT.

**Forecast recorded now, while it is still a forecast rather than a concession:** if fewer than 150 ADJACENT rows resolve by the exit review, E4-2 is flagged **INSUFFICIENT TEST CONDITIONS** and **the bar is not lowered**. On measured supply that requires \~20 sessions, which the phase has; the failure mode that closed G1 is not present here.

\---

*Advisory-only · no orders · not financial advice.*
