# First EDGAR-Live Cohort — DP-3C-t Disposition **v2 · CLEARED**

*Claude Equity Bot · Phase 3-C · cohort **2026-08-13** · v1 written before `--xbrl DOW`, **v2 written after it and supersedes v1**. Advisory-only · no orders · not financial advice.*

---

## Verdict

**ADMITTED to E4-1/2/3. The E4 clock starts 2026-08-13.**

| DP-3C-t | Disposition |
|---|---|
| (a) cohort-level | **CLEAR on all five items** |
| (b) name-level | **SND DEGRADED** (`fin=degraded`) — one name, does not count as treated |
| (c) read-blocking | **none** — the PENDING VERIFICATION hold from v1 is **cleared** |

E4 denominators stay at **24**; E4-2 coverage stays **15/24 = 62.5%**. SPCX has no tier in the FROZEN 2026-08-10 table and does not enter this phase.

---

## 1 · What `--xbrl DOW` settled

**DOW's company-facts contain no 2026Q2 data at all.** The newest accession present is `0001751788-26-000134` — the **2026Q1** 10-Q. The 10-Q filed 2026-07-24 has not been ingested into the facts feed. The renderer therefore selected the newest period that exists, `2026-03-31`.

That is correct behaviour. The 115-day lag is **upstream XBRL ingestion**, not extractor selection — and XBRL-LAG is explicitly not a defect under DP-3C-t.

### The `fin=7@2026-03-31` tag reconciles exactly

| Concept | At 2026-03-31? | Newest available |
|---|---|---|
| Revenue | **YES** | 2026Q1 [Q] 9,794,000,000 |
| Net income | **YES** | 2026Q1 [Q] −533,000,000 |
| Diluted EPS | **YES** | 2026Q1 [Q] −0.74 |
| Operating cash flow | **YES** | 2026Q1 [Q] 1,124,000,000 |
| Total assets | **YES** | @2026-03-31 59,780,000,000 |
| Shareholders equity | **YES** | @2026-03-31 15,249,000,000 |
| Cash and equivalents | **YES** | @2026-03-31 4,110,000,000 |
| Gross profit | no | **2020Q4 — 5.3 years stale** |
| Long-term debt | no | **@2024-12-31 — 15 months stale** |
| Operating income | no | no concept tagged |
| Total liabilities | no | no concept tagged |

**Seven available. The tag said seven.** `[V]`

**The renderer applied a period filter and it rejected a gross-profit figure 5.3 years old and a long-term-debt figure 15 months old.** DOW is the one covered name with stale-but-present concepts sitting in the facts, available to be wrongly selected. They were not selected. **This is a live positive test of precisely the failure mode item 1 exists to catch — stronger evidence than any of the fifteen names that were easy to check.**

---

## 2 · The model's arithmetic confirms which source fed what

| Claim in the signal | Source | Check |
|---|---|---|
| *"Shareholders equity declining YoY (−9.2%)"* | **statements block** | (15,249 − 16,788) / 16,788 = **−9.167%** `[V]` |
| *"Q2 2026 results showed impressive 20% YoY revenue growth"* | **8-K of 2026-07-23 / news** | **not derivable from the block** |

The equity figure pairs two instants from the same accession — a **same-period Q1-vs-Q1 comparison**, not a mixed period, and exactly the right computation.

The +20% is not in the facts on any reading. 2025Q1 revenue is absent as a `[Q]` entry and must be derived (H1 20,535 − Q2 10,104 = 10,431), against which 2026Q1's 9,794 is **−6.11%** — a decline. A +20% against 9,794 would need a prior-year 8,162, which does not exist anywhere in the output. The polyethylene pricing language is earnings-release narrative.

**The block was used correctly, the narrative came from elsewhere, and the two never crossed inside a rendered line.** Items 1 and 2 do not fire.

### Restatement scan (the tool's own closing hint)

Three same-end-date pairs appear from two accessions each — OCF 2025Q1 (91,000,000 twice), assets @2025-12-31 (58,538,000,000 twice), equity @2025-12-31 (16,008,000,000 twice). **All three identical. No restatements, no scope differences.** `[V]`

---

## 3 · Correction against myself

In v1 I wrote that DOW was *"the single name where the EDGAR treatment is most likely to have gone wrong"* and that clearing on the strength of the other fifteen *"would be reading the evidence toward the conclusion I want."*

**The caution about the procedure was right and I would repeat it. The direction of the suspicion was wrong.**

A 115-day lag against a 30-day median is a real outlier and was worth stopping for — but **a lag is a statement about the filer's XBRL ingestion, not about the extractor**, and I conflated the two. The tell I had and did not use: **`fin=7` is a countable claim.** Counting it against the facts would have resolved the question without the round trip. *Compute rather than recall* applies to my own hypotheses, not only to the tool's.

---

## 4 · Three findings the same output produced

### D-16 — stale-but-present concept *(new defect class)*

DOW's `GrossProfit` is tagged, present and **5.3 years old**; `LongTermDebt` is present and 15 months old.

The **absent** case is visibly handled — SPCX rendered *"(no concept tagged; tried GrossProfit)"*, a correct absence. The **stale-present** case is a different branch, and DOW is the first live demonstration that it exists in the wild.

It was handled correctly here. But **whether that is an explicit recency floor or an accident of the period-selection query is not established by this output.** Until it is read in the source, it is a **latent (a)-item-1 defect**: the case that fires is a filer whose stale concept happens to sit nearer the selected period.

> **Action: read the period-selection query in `edgar_client.py` before the next cohort; confirm or add an explicit recency floor; negative-test in `edgar_parser_audit.py` with a synthetic stale concept.**

### D-17 — DOW cannot be balance-checked and nothing says so

`Liabilities` is not tagged for DOW. The identity *assets = liabilities + equity* — the check that cleanly cleared SPCX — **has no inputs on this filer and silently does not run.** `xbrl_sweep` reports no finding, which is indistinguishable from reporting a pass.

Same family as the ~15 prior *"a tool reports a value it did not compute"* instances, in its purest form: **non-coverage rendering as clearance.**

> **Action: `xbrl_sweep` emits an explicit NOT-CHECKED for any filer missing an input to a check, and the count of NOT-CHECKED appears at every E4 read.**

### An E4-2 nuisance variable, pre-registered now rather than at the exit

DOW is the pattern: **when the statements block is a quarter stale and an 8-K is newer, the model writes the newer period's label over the older period's figures.**

No threshold, arm, population, n or robustness condition moves. But E4-2 measures filing-adjacent accuracy, and a name whose 8-K is fresh while its facts are stale is *filing-adjacent by the tag and Q-stale in substance*.

> **The count of covered names whose `fin` period trails their `periodic` date by more than 60 days is reported at the E4-2 read**, alongside the §3.3 primary-versus-fallback counts. Today that count is **1 of 15 (DOW)**. CORN (41d) and NKE (45d) are inside tolerance — both reflect real filing calendars rather than ingestion lag.

---

## 5 · Carried forward from v1, unchanged

- **D-15** — the budget warning claims "remaining tickers degrade to no-EDGAR"; eleven names followed it and ten carry full tags. Real scope: one statements fetch (SND).
- **Gate X8** — KEEP-70 gated on `op` (NVDA 70, GLD 65), not `blend_op` (75, 61). Doesn't discriminate today; under execution, "which number authorises an order" stops being cosmetic.
- **Two stale 24s** — `signal_scan.py` L47 and `log_tracker_crosscheck.py` L169 make `scan.bat` red every day on a count that is correct. Move to 25, watchlist-driven.
- **`E[no filings]` conflation** — three causes demonstrated in one run; three-place fix, one edit.
- **DP-3C-u** — extend (c) to re-derivable-but-unlogged artifact evidence; add the same-period qualifier to (a) item 2. Still required; no longer blocking.
- **Dose-response verification** — covered names +779 mean input tokens, dark names −2, no overlap. Should replace the runbook's aggregate token check.
- **My mezzanine prediction failed** — SPCX's balance closes exactly; the blind spot is specific to *pre-IPO* sheets like CBRS's, not recently-IPO'd filers as a class.

---

## 6 · Actions, in order

| # | Action | Blocks |
|---|---|---|
| 1 | **D-16** — verify/add the recency floor in `edgar_client.py`; negative-test it | the next cohort's item 1 |
| 2 | **D-17** — `xbrl_sweep` NOT-CHECKED emission | every E4 read |
| 3 | Two stale 24s → 25 | a live guard |
| 4 | D-15 — scope the budget warning to affected names | correct (b) tagging |
| 5 | DP-3C-u + log the rendered block or a per-name period stamp | the rule's own hole |
| 6 | `E[no filings]` three-place fix | E4-1's DQ-mix read |
| 7 | AG 2026-06-26 and GLD 2026-07-02 price findings | E4-1's baseline |

---

**E4 is now running.** E4-1 ~10 cohorts · E4-2 150 resolved ADJACENT rows · E4-3 20 events. **Clock started 2026-08-13, cohort 1 of ~10 in hand.** Do not read early. The 2026-08-03 shakedown cohort remains excluded from all three and retained in the master, the registry, H4 and KEEP-70.

*Advisory-only · no orders · not financial advice.*
