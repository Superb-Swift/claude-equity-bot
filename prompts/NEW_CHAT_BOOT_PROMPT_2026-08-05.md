# New-Chat Boot Prompt — Phase 3-C, control-cohort window

*Claude Equity Bot · written 2026-08-04 · hands off from the 2026-08-03 EDGAR go-live and the 2026-08-04 control-cohort session. Paste this whole file as the first message of the new chat, then attach the uploads in §2. Advisory-only · no orders · not financial advice.*

\---

## 1 · Session header

> \\\\\\\*\\\\\\\*Phase 3-C session — EW0 daily monitoring, control-cohort window.\\\\\\\*\\\\\\\*
> \\\\\\\*\\\\\\\*Goal:\\\\\\\*\\\\\\\* run the daily cycle, resolve, cross-check, splice. \\\\\\\*\\\\\\\*EDGAR stays OFF until N-1 is fixed.\\\\\\\*\\\\\\\*
> \\\\\\\*\\\\\\\*State in force:\\\\\\\*\\\\\\\* advisory-only, no orders; generator era \\\\\\\*\\\\\\\*`A-S1D1-B1`\\\\\\\*\\\\\\\* while EDGAR is off, \\\\\\\*\\\\\\\*`A-S1D1-B1-E1`\\\\\\\*\\\\\\\* when it is on (S1 + D1 live, blend DESCOPED); \\\\\\\*\\\\\\\*T1\\\\\\\*\\\\\\\* mandatory pre-execution; \\\\\\\*\\\\\\\*T3\\\\\\\*\\\\\\\* no band-ordering reliance; Q1 guardrail \\\\\\\*\\\\\\\*RETIRED\\\\\\\*\\\\\\\*, \\\\\\\*\\\\\\\*T2 RETIRED\\\\\\\*\\\\\\\*; \\\\\\\*\\\\\\\*KEEP 70%\\\\\\\*\\\\\\\*; ±3% HOLD band not re-baselined; CBRS excluded from EDGAR to the Q4 2026 Path-A review.
> \\\\\\\*\\\\\\\*Phase 3-B closed 2026-07-31\\\\\\\*\\\\\\\* — G5 SERVED · G1 INSUFFICIENT TEST CONDITIONS · G2 DESCOPE · G3 PARK · G4 VERDICT · G6 VERDICT.
> \\\\\\\*\\\\\\\*Phase 3-C entry gates: all six dispositioned.\\\\\\\*\\\\\\\* EDGAR went live 2026-08-03 and that cohort is a \\\\\\\*\\\\\\\*SHAKEDOWN, excluded from E4 entirely\\\\\\\*\\\\\\\* (DP-3C-k).
> \\\\\\\*\\\\\\\*THE E4 CLOCK HAS NOT STARTED.\\\\\\\*\\\\\\\* N-1 is unfixed, so every cohort until it lands is a control cohort. This is a recorded choice, not drift — see §5.

\---

## 2 · Uploads

**Tier 1 — boot set (always):**

* `docs\\\\\\\\analyst\\\\\\\_notes.md` — **current through 2026-08-04**, no pending splices
* `Phase3C\\\\\\\_Kickoff\\\\\\\_Prompt.md`
* `Phase3B\\\\\\\_Closeout\\\\\\\_Memo.md`
* `Daily\\\\\\\_Workflow\\\\\\\_v6\\\\\\\_0\\\\\\\_Phase3C.docx`

**Tier 2 — this session:**

* `logs\\\\\\\\signals\\\\\\\_YYYY-MM-DD.log`
* `signal\\\\\\\_scan\\\\\\\_YYYY-MM-DD.md` (or the full `scan.bat` console output)
* `paste\\\\\\\_today.tsv`
* `monitor\\\\\\\_strip.md`
* `Phase3C\\\\\\\_E4\\\\\\\_Endpoint\\\\\\\_PreRegistration\\\\\\\_v1.md`
* `logs\\\\\\\\claude\\\\\\\_equity\\\\\\\_bot\\\\\\\_tracker.xlsx` (**THE MASTER**)
* `tracker\\\\\\\_with\\\\\\\_registry.xlsx` (the generated report copy — output only, never an input)

**Only if a defect surfaces:** `edgar\\\\\\\_client.py`, `main.py`, `risk\\\\\\\_engine.py`, `analyze\\\\\\\_log.py`, `parse\\\\\\\_log\\\\\\\_to\\\\\\\_tracker.py`, `signal\\\\\\\_scan.py`, `monitor\\\\\\\_strip.py`, `h4\\\\\\\_dq\\\\\\\_threshold.py`.

**Note on the container:** it resets between turns. Every file must be re-attached each session; nothing persists.

\---

## 3 · What happened 2026-08-03 and 2026-08-04

### EDGAR went live, then was ruled a shakedown

`edgar\\\\\\\_client.py` is the first prompt-provider on the WS1 registry. `set EQUITY\\\\\\\_EDGAR=1` both enables EDGAR and moves the era stamp to `A-S1D1-B1-E1`; the two are derived from one another so EDGAR cannot go live under the pre-EDGAR stamp. New log tag after `B\\\\\\\[…]`: `E\\\\\\\[8k=1; form4=+0/-5; periodic=10-Q@2026-07-23; fin=9@2026-06-30]` or `E\\\\\\\[no filings]`.

The first live cohort (8/03) reconciled 24/24 and every parser agreed, but two defects made the treatment unfit to measure:

* **N-1 (HIGH, UNFIXED).** YTD figures render under a quarter label; the `\\\\\\\[6M YTD]` marker Workflow §11 pre-registers never fires. `--xbrl PWR` proved both the 180d \[H] and 90d \[Q] buckets sit in the *same accession* and the client picked H — a CLIENT selection bug, not a filer quirk. Affects any name whose latest periodic is Q2 or later; **the footprint grows on its own** as Q1 filers roll forward, from 6/15 today toward \~13/15 by the first E4-2 read. The fix is two-part: prefer the \~90d bucket where one exists, and where only a cumulative bucket exists render it *and fire the label* (PWR's operating cash flow has no Q bucket at all, so "always prefer Q" would break it).
* **F-1 (HIGH).** Budget exhaustion silently drops the XBRL statements block for names needing a schema recompute; the recompute starts, is abandoned, and never writes to cache. The 120s budget measures **wall clock**, of which EDGAR fetch is \~6%.

### Decisions ruled

|DP|Ruling|Date|
|-|-|-|
|**DP-3C-g**|Filing set includes XBRL financial statements alongside MD\&A|2026-08-02|
|**DP-2**|Single live arm, era `A-S1D1-B1-E1`; A/B stays terminated|2026-08-02|
|**DP-3C-e**|E4 stratifies by coverage tier, not era stamp alone|2026-08-02|
|**DP-3C-h**|Retain 8/03 as `partial-treatment` — **RULED THEN SUPERSEDED same session** by DP-3C-k; kept in the record, not deleted|2026-08-03|
|**DP-3C-i**|The `E\\\\\\\[…]` tag carries **filing dates** — E4-2's ADJACENT window is otherwise unreconstructible from the durable record|2026-08-03|
|**DP-3C-j**|Budget bounds EDGAR fetch/extract time, not wall clock; degradation becomes visible per-ticker (`fin=degraded` ≠ `fin=none`)|2026-08-03|
|**DP-3C-k**|**Fix N-1 now. 8/03 is a SHAKEDOWN cohort, excluded from E4 entirely. The E4 clock starts at the first clean cohort**|2026-08-03|
|**DP-3C-l**|**GATE-CLEARED ledger** — descriptive only, no standard, exit disposition pre-committed **INSUFFICIENT TEST CONDITIONS** (supply 0.037/session ⇒ \~2 years for n=20)|2026-08-04|
|**MAX\_OPEN\_POSITIONS = 8**|Ruled an **artifact of the Phase-2 design**|2026-08-04|

**Unruled:** DP-3C-f (AG/NTR foreign filers; proposed no change in v1).

### 2026-08-04 — a control cohort, and three real findings

The `EQUITY\\\\\\\_EDGAR=1` flag was missed after a Schwab token reauth, so the run executed 11:08 CST at era `A-S1D1-B1` with zero E-tags. **No second run was taken** — `signal\\\\\\\_state.json` had already appended, and N-1 is unfixed anyway. The forgotten flag produced a *correctly labelled control run*, which is the flag-and-era atomicity working as designed.

1. **NVDA BUY at 72% — the first and only BUY to clear the 70% gate in 1,291 rows.** The risk engine rejected it on `Too many open positions: 16 >= max 8`.
2. **Three defects in `risk\\\\\\\_engine.check\\\\\\\_signal` CHECK 6.** **D-1**: `main.py` L285–286 passes `portfolios\\\\\\\[0]` only, so the engine sees Roth IRA alone (16 positions incl. 3 bond CUSIPs) while the Individual account's 20 are invisible; union of held equity tickers is 19. **D-2**: bond CUSIPs count toward an *equity* cap. **D-3 (fix first)**: CHECK 6 has no `if sig == "BUY"` guard and therefore **blocks SELLs**, though CHECK 8 ten lines below states the correct principle explicitly. **D-4 (latent)**: CHECK 7's duplicate guard inherits D-1.
3. **`analyze\\\\\\\_log.py` contradicts itself.** It filed NVDA under "ACTIONABLE SIGNALS (Risk Engine Approved)" while its own tally read `APPROVED 23 / REJECTED 1`. `classify\\\\\\\_directional\\\\\\\_signal` (L220–251) keys on confidence only, though the risk decision is parsed at L148 and used at L467. Latent for 1,291 rows.

**Consequence, confirmed `\\\\\\\[V]` from `logs\\\\\\\\signals\\\\\\\_2026-06-26.log`:** CBRS SELL 6/26 (conf 68 ≥ the 65 gate) was *also* rejected on position count. **The risk engine has never approved a directional signal — 35 signals, zero approvals.** The 23 APPROVED rows in any daily tally are HOLDs passing through CHECK 2.

### Measurement findings

* **The band-breach identity is exact at 48/48 on the HOLD population, r = −1.0000** — and on HOLD rows it is a *definition*, not a correlation: "Was Claude Right (5d)" *is* |return| ≤ 3%, the exact complement of a breach. **`\\\\\\\[?]` UNRECONCILED:** the record's 7/30 figure of r = −0.9650 exact in 46/46 does not reproduce (all-rows gives −0.9934 and 41/47). **Reconcile before E4-2** — if accuracy is definitionally 1 − breach rate, E4-2's mandatory paired reporting is one number twice.
* **7/28 resolved 29.2% on sd 9.09%** — the highest cohort dispersion in the record, on a 24-row all-HOLD cohort, so accuracy is purely the breach count.
* Horizon breach rates, stable: +5d 45.5% (median |move| 2.64%), +10d 55.4% (3.51%), +20d 66.5% (5.15%).
* **E4-1 noise floor, measured for free:** DQ moved 21 HIGH/3 MEDIUM → 19/5 with **no treatment**. E4-1 should state a minimum shift size.

\---

## 4 · First task in the new chat

1. **Run integrity** — `signal\\\\\\\_scan`'s RUN INTEGRITY block. Expect `era stamp A-S1D1-B1` and **no** EDGAR line while the flag is off.
2. **Parser agreement** — `analyze\\\\\\\_log` 24, `paste\\\\\\\_today.tsv` 24 rows with real Accounts (never "Unknown"), `signal\\\\\\\_scan` 24. Any disagreement is the finding.
3. **Cross-check** — `log\\\\\\\_tracker\\\\\\\_crosscheck.py` must read **24/24 clean** against the master. Note `scan.bat` runs this *before* the paste, which produces 24 false `\\\\\\\[MISSING]` rows; re-run after pasting.
4. **Recalc** — 0 formula errors on the master.
5. **Resolutions** — +5d / +10d / +20d entered per the calendar, computed from trading-day output and never transcribed.
6. **Monitor reads** — WS2/G1 clocks, H4, KEEP-70. **Table reads at their stated n; a one-session move is noise.**
7. **Splice** the session into `docs\\\\\\\\analyst\\\\\\\_notes.md`, plain text.

**Do not read the E4 endpoints.** E4-1 \~10 cohorts, E4-2 150 resolved ADJACENT rows, E4-3 20 events — and the clock has not started.

\---

## 5 · Standing decisions that shape this window

* **Control cohorts are deliberate.** N-1 is unfixed, so EDGAR stays off; E4-1 reads DQ-mix pre-era vs post-era and control cohorts *are* its baseline. **Record the date on which this choice ends.**
* **The 8/03 shakedown exclusion is E4-scoped, not record-scoped.** Those 24 rows remain in the master, in the near-miss registry, in H4 and in KEEP-70. Only E4-1/-2/-3 exclude them. Over-excluding would silently move KEEP-70's denominator.
* **KEEP-70 is unchanged and supported** — 13/32 = 40.6%, registry 33, denominator verified uncontaminated (all rows 0.61–0.68; rejection ordering is confidence-first).
* **The gate-cleared ledger holds two rows:** CBRS SELL 6/26 → NO (+14.61%); NVDA BUY 8/04 → **resolves 2026-08-11**. Record the outcome; **read nothing from n=2.**

\---

## 6 · Change order — NOT STARTED, do not reorder

1. **D-3** — guard CHECK 6 to BUY-only. Three words, live logic error. It does *not* mask the analyzer defect, because CHECK 6 still blocks every BUY afterwards.
2. **5b** — `analyze\\\\\\\_log.classify\\\\\\\_directional\\\\\\\_signal`: `return "actionable" if s.get("risk") == "APPROVED" else "gate\\\\\\\_cleared\\\\\\\_rejected"`. The third bucket *is* the DP-3C-l ledger population.
3. **`signal\\\\\\\_scan.py` into `edgar\\\\\\\_parser\\\\\\\_audit.py`** — it parses the E tag, is not in the audit, and was already the third instance of the hardcoded-phase-token defect class. This gates everything below it.
4. Update the audit to synthesise the amended tag and the 3-C phase token.
5. **N-1** — bucket selection + `\\\\\\\[6M YTD]` / `\\\\\\\[9M YTD]` label.
6. **DP-3C-i** (tag dates) and **DP-3C-j** (budget accounting, `fin=degraded`).
7. Correct the `\\\\\\\[PHASE 3-B DRY RUN]` token in `main.py` — it still reads 3-B under a 3-C phase.
8. Re-run `edgar\\\\\\\_parser\\\\\\\_audit.py` (**exit 0 required**) and `--selftest` with a new N-1 regression test carrying both an H and a Q bucket, and one with H only.
9. **D-1 / D-2** and the position-cap question — neither changes an outcome today, and any cap change must land *after* step 2 or the fix becomes unverifiable.

**One disambiguation DP-3C-i forces:** E4-2 defines ADJACENT as an 8-K **or Form 4** in the window with no restriction to open-market transactions, so `form4=…@D` must carry the date of the most recent Form 4 of *any* transaction code — including grants (A), exercises (M) and withholding (F), which never move net direction.

\---

## 7 · Outstanding (none blocking, none with a hard date)

* **Commit backlog — the largest unhedged risk.** The entire post-7/27 generation is untracked on one disk: `run\\\\\\\_daily\\\\\\\_review.bat`, `retired\\\\\\\_criteria\\\\\\\_audit.py`, `log\\\\\\\_tracker\\\\\\\_crosscheck.py`, `scan.bat`, `signal\\\\\\\_scan.py`, `edgar\\\\\\\_client.py`, `edgar\\\\\\\_parser\\\\\\\_audit.py`, plus the 8/04 patches to `monitor\\\\\\\_strip.py` and `h4\\\\\\\_dq\\\\\\\_threshold.py`. **One git command at a time.**
* **Enter DP-3C-l into `Phase3C\\\\\\\_E4\\\\\\\_Endpoint\\\\\\\_PreRegistration\\\\\\\_v1.md` §5** beside DP-2 / DP-3C-e / DP-3C-g. The ruling currently exists in the notes and nowhere else; the DP-8/DP-9/DP-10 provenance loop is the precedent for what happens when an instrument and the record disagree.
* **Ghost rows** — Excel rows 222/226 = signals #218/#222, 2026-06-01 AG and FTI: complete price series at all three horizons, NULL Signal/Conf/DQ, annotated in-cell as Schwab 429 skips. **Annotate, do not delete.** G4 requires no open data-integrity items at exit. Note 6/01 recorded skips as blank-field *rows* while 6/02 (21 rows) and 6/03 (22 rows) recorded them as *absent* rows — two conventions for one condition.
* **Add a cohort-versus-entry reconciliation to the exit checklist.** The 7/24 gap was invisible to every tool: the audit scans source files, the cross-check reads the master, and neither knows a date exists in one and not the other.
* **`Sheet1` stays in the master by ruling** (2026-08-04) as a historical artifact. It is the retired `guardrail\\\\\\\_trace.py` trace frozen at 2026-07-20, *not* a manually-maintained tab — the manual tab is `Signals`. Suggested but unruled: mark it retired in place so its row 2 stops asserting "The 50-59% band must lead 60-69%" in live-criterion grammar.
* **Workflow v6.0.1** — `scan.bat` and `log\\\\\\\_tracker\\\\\\\_crosscheck.py` missing from §3 and §16; §4 documents a 15/24 prefetch while the live run emits 19/24 (submissions resolved, not sections rendered); §18's budget row is wrong per DP-3C-j; §11 needs the N-1 rule.
* Stale banner strings in `run\\\\\\\_daily\\\\\\\_review.bat` (G2, G1, H4) and `run\\\\\\\_daily.bat`'s header era. `retired\\\\\\\_criteria\\\\\\\_audit.py` flags all four; 31 HIGH / 6 MEDIUM outstanding, mostly in `blend\\\\\\\_eval.py` and `monitor\\\\\\\_strip.py`.
* `context\\\\\\\_providers.py` latent trap (`caches or {}`) — unfixed **by design**, Scope Spec §8 pins the file for 3-C.
* **`DP-3C-l` label collision** — lowercase L beside a DP-1…DP-10 series. Recorded, not renamed, per the signature instruction.
* **UTC date stamps.** Filing sections use `datetime.now(timezone.utc)`, so evening runs in Texas read tomorrow's date. This defect reached *manual* work on 8/04 as well: the session's patches and the 7/24 reconstruction were first stamped 2026-08-05 and corrected. An evening session should take its date from the trading calendar, not a clock.

\---

## 8 · How I want you to work

Unchanged and non-negotiable:

* **Conclusions first**, then evidence. Tables for comparisons, bullets for lists.
* **Explicit file naming, always.** `logs\\\\\\\\claude\\\\\\\_equity\\\\\\\_bot\\\\\\\_tracker.xlsx` is THE MASTER; `tracker\\\\\\\_with\\\\\\\_registry.xlsx` is the GENERATED REPORT COPY. Never a bare "tracker."
* **Read master / write generated copy.** Open the report copy in Excel after every review run — openpyxl blanks the formula cache on save. Registry regen → strip embed, always.
* **One git command at a time.** CRLF for `.bat`. Idempotent sheet embeds.
* **Dated provenance and visible self-corrections.** If you were wrong earlier, say so in the record rather than quietly fixing it. **Three corrections were made across 8/03–8/04 and all three are in the notes.**
* **Identify the full blast radius** of any directional decision — dependency chains, not isolated edits.
* **Tell me when evidence is being read toward a convenient conclusion** rather than against a pre-committed standard.
* **Verify before asserting. Compute rather than recall.** Mark `\\\\\\\[V]` verified this session / `\\\\\\\[R]` from the record / `\\\\\\\[?]` needs confirmation.
* **`+Nd` always means N trading days, computed from function output — never transcribed.** All +Nd outcomes use closing prices.
* **A tool that reports a value it did not compute is the most expensive defect class in this project.** It has now appeared **twelve** times. `analyze\\\\\\\_log`'s actionable section is the latest, and it was latent for 1,291 rows because no BUY had ever cleared 70%.
* **Caches hide fixes.** If a change appears to do nothing, suspect the cache before suspecting the change.
* **The first live run of anything is where the defects are.** Of the 23 defects in `edgar\\\\\\\_client.py`, 19 surfaced from live runs rather than the 102 self-test assertions.

\---

## 9 · Useful commands

```
run\\\\\\\_daily.bat                                # EDGAR OFF — do not set EQUITY\\\\\\\_EDGAR while N-1 is unfixed
monitor.bat                                  # AFTER the paste
run\\\\\\\_daily\\\\\\\_review.bat                         # AFTER the paste; registry regen -> strip embed
scan.bat                                     # signal\\\\\\\_scan + log/master cross-check
python log\\\\\\\_tracker\\\\\\\_crosscheck.py             # re-run AFTER pasting; 24/24 required
python edgar\\\\\\\_client.py --ticker RTX          # what the model would see for one name
python edgar\\\\\\\_client.py --xbrl NVDA           # raw XBRL — CLIENT bug vs FILER quirk
python edgar\\\\\\\_client.py --coverage            # tiers + event rates, E4's denominator
python edgar\\\\\\\_client.py --selftest            # offline assertions
python edgar\\\\\\\_parser\\\\\\\_audit.py                 # E3 pre-deploy audit; exit 0 required
python retired\\\\\\\_criteria\\\\\\\_audit.py --quiet     # live cadence only
```

Full command appendix: `Daily\\\\\\\_Workflow\\\\\\\_v6\\\\\\\_0\\\\\\\_Phase3C.docx` §16. EDGAR troubleshooting: §18.

\---

*Advisory-only · no orders · not financial advice.*

