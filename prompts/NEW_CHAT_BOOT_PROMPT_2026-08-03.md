# New-Chat Boot Prompt — Phase 3-C, first live EDGAR cohort

*Claude Equity Bot · written 2026-08-03 · hands off from the 2026-08-02 EW1 build session. Paste this whole file as the first message of the new chat, then attach the uploads listed in §2. Advisory-only · no orders · not financial advice.*

\---

## 1 · Session header

> \*\*Phase 3-C session — first live EDGAR cohort review (EW0 daily monitoring + EW2 acceptance).\*\*
> \*\*Goal:\*\* verify the first `EQUITY\_EDGAR=1` run end to end — parsers, tags, era stamp, filing sections — then splice the record.
> \*\*State in force:\*\* advisory-only, no orders; generator era \*\*`A-S1D1-B1-E1`\*\* (S1 + D1 live, blend DESCOPED, \*\*EDGAR live as of this run\*\*); \*\*T1\*\* mandatory pre-execution; \*\*T3\*\* no band-ordering reliance; Q1 guardrail \*\*RETIRED\*\*, \*\*T2 RETIRED\*\*; \*\*KEEP 70%\*\*; ±3% HOLD band not re-baselined; CBRS Path A excluded to Q4 2026.
> \*\*Phase 3-B closed 2026-07-31\*\* — G5 SERVED · G1 INSUFFICIENT TEST CONDITIONS · G2 DESCOPE · G3 PARK · G4 VERDICT · G6 VERDICT.
> \*\*Phase 3-C entry gates: all six dispositioned.\*\* E1 scope entered (amended by DP-3C-g) · E2 ruled · E3 parser audit PASSED · E4 pre-registered before go-live · E5 compliant · E6 met.

\---

## 2 · Uploads

**Tier 1 — boot set (always):**

* `docs\\analyst\_notes.md` — with `splice\_2026-07-31.md` **and** `splice\_2026-08-02.md` applied
* `Phase3C\_Kickoff\_Prompt.md`
* `Phase3B\_Closeout\_Memo.md`
* `Daily\_Workflow\_v6\_0\_Phase3C.docx`

**Tier 2 — this session:**

* `logs\\signals\_2026-08-03.log` — **the first 3-C log**
* `signal\_scan\_2026-08-03.md`
* `paste\_today.tsv`
* `monitor\_strip.md`
* `Phase3C\_E4\_Endpoint\_PreRegistration\_v1.md`
* `logs\\claude\_equity\_bot\_tracker.xlsx` (THE MASTER)

**Only if a defect surfaces:** `edgar\_client.py`, `main.py`, `signal\_scan.py`, `analyze\_log.py`, `parse\_log\_to\_tracker.py`.

\---

## 3 · What changed on 2026-08-02 (the build session)

**EDGAR is live.** `edgar\_client.py` is the first prompt-provider on the WS1 registry. Each covered ticker's prompt gains a SEC FILINGS section: 8-K bodies (including the EX-99 press release when the primary document is a wrapper), Form 4 insider direction from the raw ownership XML, a bounded MD\&A extract, and **XBRL financial statements** with year-over-year.

**One switch, two effects.** `set EQUITY\_EDGAR=1` enables EDGAR *and* moves the era stamp to `A-S1D1-B1-E1`. They are derived from one another in `main.py`, so EDGAR cannot go live under the pre-EDGAR stamp — treated rows can never be filed as control rows.

**New log tag,** appended after `B\[…]`:
`E\[8k=1; form4=+0/-5; periodic=10-Q@2026-07-23; fin=9@2026-06-30]` or `E\[no filings]`.

**Three decision points ruled 2026-08-02:**

|DP|Ruling|
|-|-|
|**DP-3C-g**|Filing set **includes XBRL financial statements** alongside the MD\&A extract. Widens Kickoff §1. Ruled before go-live deliberately — the same widening afterwards would change the treatment mid-measurement|
|**DP-2**|Single live arm, era `A-S1D1-B1-E1`. A/B stays terminated|
|**DP-3C-e**|E4 stratifies by **coverage tier**, not era stamp alone|

**Unruled:** DP-3C-f — AG and NTR are confirmed 40-F/6-K foreign filers. Extending the filing set would move both T-C → T-A. Proposed: no change in v1.

**Coverage `\[V]`, measured against live SEC:** T-A live event flow **14** (AAPL, CORN, DOW, FTI, GM, JPM, MSFT, NKE, NVDA, PM, PWR, RTX, SND, WMT) · T-B periodic only **1** (GLD) · T-C dark **8** (AIQ, AG, NTR, QQQ, SCHD, SPY, VTI, XLU) · skipped **1** (CBRS). **Practical coverage 15/24 = 62.5%.** Event supply: 8-K 16.9/month (0.81/session); Form 4 69.7/month (3.32/session). WMT alone is 24% of Form 4 volume.

**Three corrections to Kickoff §2 `\[V]`:** AG and NTR confirmed foreign filers; **CORN and GLD are NOT filing-less** — both file 10-Qs, CORN files 8-Ks. §2's "\~100 untreatable MEDIUM rows" argument loses two of its three names; only AIQ (29 rows) holds. This correction runs *toward* the treatment and is flagged as such.

\---

## 4 · First task in the new chat

Work through this order before anything else.

1. **Run integrity** — `signal\_scan\_2026-08-03.md`'s RUN INTEGRITY block. Expect `era stamp A-S1D1-B1-E1 - EDGAR live (3-C)` and a new line `EDGAR sections on N/24 row(s)`.
2. **E-tag distribution** — present on the 15 covered names, `E\[no filings]` on the 8 dark names + CBRS. **If every row reads `E\[no filings]`, EDGAR fetched nothing** (workflow §18) — that is not "nothing was filed."
3. **Parser agreement** — `analyze\_log.py` reports 24 signals; `paste\_today.tsv` has 24 rows with real Accounts (never "Unknown"); `signal\_scan` reports 24. **All three parse the same log independently.** Any disagreement is the finding.
4. **Budget** — confirm the log does NOT contain `\[EDGAR] run budget of 120s exhausted`. If present, later tickers silently ran without filings.
5. **Read two filing sections in full** — one T-A name with an 8-K, one without. Check the statement block for arithmetic that cannot be true.
6. Then the normal cross-check: log ↔ master 24/24, resolution completeness, cohort profile, monitor reads, splice.

\---

## 5 · Known risk on this specific run

**Seventeen defects were found building this client. Sixteen surfaced from live runs, not from the 102 self-test assertions.** Every one appeared the first time something ran for real.

**Run-level behaviour has never executed.** The individual `--ticker` path was exercised on 19 names, but not: 15 tickers sequentially inside the 120-second budget, the prefetch, `E\[…]` tags landing in a real log, or three parsers reading them. That is what is new today.

**Read for ABSENCES as much as errors.** Two of the build's self-inflicted regressions showed up as *missing* sections, not wrong ones. A statement line that is absent, an E tag that is missing, an MD\&A that renders empty — none of these raise.

**Treat this cohort as a review, not a measurement.** E4 endpoints are TABLE READS at their stated n (E4-1 \~10 cohorts, E4-2 150 adjacent rows, E4-3 20 events). A one-session move is noise. Do not read them early.

\---

## 6 · Outstanding items (carried, none blocking)

* **`signal\_scan.py` is not yet in `edgar\_parser\_audit.py`.** It was patched 8/3 for the 3-C cutover (its phase token was hardcoded `3-B` — third occurrence of that defect, after `analyze\_log.py` 6/15 and `parse\_log\_to\_tracker.py` 7/07) but the pre-deploy audit still covers only two parsers. **Add it, and consider making the audit discover parsers rather than list them.**
* **Workflow v6.0.1** — `scan.bat` and `log\_tracker\_crosscheck.py` are live daily steps missing from §3 and §16 of the workflow doc.
* **Stale banner strings** — `run\_daily\_review.bat` prints live-criterion grammar for G2 (DESCOPED) and G1 (INSUFFICIENT TEST CONDITIONS), and H4 at `n ≥ 10` (superseded 7/28 by `n ≥ 12` on two consecutive readings). `run\_daily.bat`'s header names the era as `A-S1D1`. The retired-criteria audit now flags all four.
* **Uncommitted tooling** — `run\_daily\_review.bat`, `retired\_criteria\_audit.py`, `log\_tracker\_crosscheck.py`, `scan.bat`, `signal\_scan.py`, `edgar\_client.py`, `edgar\_parser\_audit.py` are all untracked. The entire post-7/27 generation exists on one disk.
* **`context\_providers.py` latent trap** — providers are called as `p.fn(ticker, caches or {})`; an empty dict is falsy, so `{} or {}` hands the provider a throwaway. Harmless today (prefetch populates first). Fix is `caches if caches is not None else {}`; not applied because Scope Spec §8 pins the file at no-change for 3-C.
* **`ticker\_suggester.py`** — last touched 5/18, pre-3-A. `\[?]` whether anything still calls it.
* **UTC stamp** — filing sections use `datetime.now(timezone.utc)`, so evening runs in Texas read tomorrow's date. No effect on the 9:30 CST canonical run.
* Worksheet v1.3 clerical corrections (closeout memo §3.7).

\---

## 7 · How I want you to work

Unchanged and non-negotiable:

* **Conclusions first**, then evidence. Tables for comparisons, bullets for lists.
* **Explicit file naming, always.** `logs\\claude\_equity\_bot\_tracker.xlsx` is THE MASTER; `tracker\_with\_registry.xlsx` is the GENERATED REPORT COPY. Never a bare "tracker."
* **Read master / write generated copy.** Open the report copy in Excel after every review run — openpyxl blanks the formula cache on save.
* **One git command at a time.** CRLF for `.bat`. Idempotent sheet embeds.
* **Dated provenance and visible self-corrections.** If you were wrong earlier, say so in the record rather than quietly fixing it.
* **Identify the full blast radius** of any directional decision — dependency chains, not isolated edits.
* **Tell me when evidence is being read toward a convenient conclusion** rather than against a pre-committed standard. This has mattered repeatedly, and it mattered most when it cost me the exit.
* **Verify before asserting. Compute rather than recall.** Mark `\[V]` verified this session / `\[R]` from the record / `\[?]` needs confirmation.
* **A tool that reports a value it did not compute is the most expensive defect class in this project.** It has appeared at least nine times. "mixed", "0.0", a hardcoded era in a header, and a stale date all look like measurements.
* **Caches hide fixes.** If a change appears to do nothing, suspect the cache before suspecting the change.

\---

## 8 · Useful commands

```
python edgar\_client.py --ticker RTX          # what the model saw for one name
python edgar\_client.py --xbrl NVDA           # raw XBRL behind the statements
python edgar\_client.py --coverage            # tiers + event rates, E4's denominator
python edgar\_client.py --selftest            # 102 offline assertions
python edgar\_parser\_audit.py                 # E3 pre-deploy audit
python retired\_criteria\_audit.py --quiet     # live cadence only
```

Full command appendix: `Daily\_Workflow\_v6\_0\_Phase3C.docx` §16. EDGAR troubleshooting: §18.

\---

*Advisory-only · no orders · not financial advice.*

