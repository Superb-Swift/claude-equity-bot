# Claude Equity Bot — new-chat boot prompt

*Paste this as the first message of the new conversation, then upload the boot set listed in §9. Written 2026-07-29 at the close of the Phase 3-B Day 17 session.*

\---

## 1 · Who I am and what this is

I run **Claude Equity Bot** — a Python advisory-only equity signal system (schwab-py, Anthropic SDK, Finnhub, Flask) on Windows, Python 3.14, PowerShell/cmd. Repo: `C:\\\\Users\\\\rober\\\\claude-equity-bot` (`Superb-Swift/claude-equity-bot`).

It watches a fixed **24-ticker** watchlist, emits BUY/HOLD/SELL with a confidence score, and **places no orders, ever**. We are in **Phase 3-B**, currently at the exit review. Signals run to **2026-07-29: 1,195 rows, 50 cohorts**.

**This is a research project, not a trading system.** Almost all the work is measurement discipline: pre-registering criteria, then judging evidence against them rather than against what would be convenient.

## 2 · How I want you to work

* **Conclusions first**, then the evidence. Structured output — tables for comparisons, bullets for lists.
* **Explicit file naming, always.** `logs\\\\claude\\\_equity\\\_bot\\\_tracker.xlsx` is THE MASTER. `tracker\\\_with\\\_registry.xlsx` is the GENERATED REPORT COPY. **Never write a bare "tracker."**
* **Read master / write generated copy.** Hard-guarded in code.
* **One git command at a time.**
* **Dated provenance and visible self-corrections.** If you were wrong earlier, say so in the record rather than quietly fixing it.
* **Identify full blast radius** from any directional decision — dependency chains, not isolated edits.
* **Tell me when evidence is being read toward a convenient conclusion** rather than against a pre-committed standard. This has mattered repeatedly.
* Verify before asserting. Compute it rather than recalling it. Distinguish `\\\[V]` verified this session / `\\\[R]` from the record / `\\\[?]` needs confirmation.
* CRLF for `.bat`. Idempotent sheet embeds (delete-then-recreate).

## 3 · Standing constraints

|Constraint|Meaning|
|-|-|
|**T1 — advisory only**|No execution, ever. Execution is a separate future gate.|
|**T3 — no band-ordering reliance**|The Q1 guardrail is RETIRED. Now enforced in tooling by `retired\\\_criteria\\\_audit.py`.|
|**KEEP 70%**|BUY gate unchanged. Live near-miss BUYs 13/30 = 43.3% would have paid — under the 50% line that supports the gate.|
|**Q1-R CLOSED · Q4-R CLOSED · T2 RETIRED**|No standing tripwire on band ordering remains.|
|**Watchlist frozen**|No mid-window population change until the 3-B/3-C boundary.|
|**±3% HOLD band locked**|A HOLD is "right" if the name moved <3% over +5d. See §7 — this is currently the dominant driver of measured accuracy.|
|**CBRS Path A excluded**|To Q4 2026.|

## 4 · Phase 3-B gate status (Worksheet v1.1, 2026-07-29)

|Gate|Subject|Status|
|-|-|-|
|**G5**|Trigger service|**CLOSED — VERDICT: SERVED.** Signature line pending|
|**G1**|WS2 (H1 feature, S1+D1)|**1 independent episode of 4.** VERDICT-only, cannot be parked → **binding constraint on the whole exit**|
|**G2**|WS1 (triple-blend)|Fails both evidence conditions. VERDICT or DESCOPE only|
|**G3**|WS3 (commodity context)|Workstream appears unbuilt. PARK proposed. Prerequisite for 3-C entry gate E1|
|**G4**|Operational integrity|Four open integrity items|
|**G6**|Instruments|Worksheet drafted; closeout memo unwritten; notes backlog|

**G1 detail.** WS2 deployed 2026-07-07. One post-deploy episode: **WMT 7/23, lag 0, confidence 47→38, D1 contributed zero damping** — entirely model-side, which is what S1 was built to produce. GM has **none**. Episodes only arrive when the market produces a material adverse move on WMT or GM; this cannot be accelerated.

**G2 detail.** WS1 deployed 2026-07-13. Primary read (A) confirmed 40.0% (n=5) vs discounted 25.0% (n=4) = **+15.0pt** — but it read **−10.0pt the previous session**; two resolutions reversed the sign. Folds `\\\[+25,+25,+0,+0,+40,+7,+25,−10,+15,+15,+15,+15,+15]` — one negative, and the criterion requires all folds the same sign, so **(A) is not robust**. **(B) gate-flip net −1**, unchanged. Footprint is **8 NVDA : 1 GLD**.

**H4 (not a gate).** STAYS DEMOTED. Touched its reopening bar for exactly one session: 6/10 = 60.0000% (7/27) → 6/11 = 54.5% (7/28) → 6/12 = 50.0% (7/29). Adopted rule: no DQ-conditional design work until two consecutive readings pass at n ≥ 12.

## 5 · Decision points

|DP|Status|
|-|-|
|DP-1|N=5 blended cohorts — MET (13 logged)|
|DP-2…DP-5|Carried to 3-C kickoff|
|**DP-6**|**RULED 7/28: G1 counts EPISODES, not cohorts.** Made G1 stricter|
|**DP-7**|**RULED 7/28: G2 needs ≥2 distinct tickers with resolved adjusted signals. MET 7/29** (GLD)|
|**DP-8**|**OPEN.** Should a WS2 episode be bidirectional? The criterion says "a material trailing move" and is silent on sign; adverse-only is a narrowing the *code* introduced|
|**DP-9**|**OPEN.** Should the episode universe extend past WMT/GM? Contradicts explicit pre-registered wording → genuine amendment, not reinterpretation|
|**DP-10**|**OPEN.** DP-7 is satisfied by 8:1 concentration. Needs a per-ticker minimum or cap to mean what it was written to mean|

**DP-8 and DP-9 are deliberately unruled** because both would *increase* the episode count on the gate that is blocking the exit. That is the pattern pre-registration exists to prevent.

**Also unruled and needed:** the standard of evidence for a **negative** G2 verdict — fixed before the next resolution, not after.

## 6 · Open loose ends

**Highest risk:** `docs\\\\analyst\\\_notes.md` backlog. As of 7/23 it was nine splices behind; splices for 7/27 (v2), 7/28 and 7/29 are also pending. Every gate cites the notes as its evidence source.

* Sign G5 on Worksheet v1.1
* **Retire T2's tooling** — `t2\\\_check.py` / `t2.bat` still print *"T2 FIRES — run the Tier-2E diff"* on a retired tripwire. Add a RETIRED header to `guardrail\\\_trace.py`
* **Three audit exclusions before the pre-commit hook**: skip `Retired\\\\`; skip `docs\\\\analyst\\\_notes.md`; stop tokenising `T2` where it's a test-case ID
* **Two ghost rows** — Signals 222 / 226, both 2026-06-01 (AG, FTI): date and ticker, NULL signal/conf/DQ. G4 requires no open integrity items
* Patch `h4\\\_dq\\\_threshold.py`'s stale *"binding gap is sample size"* console string
* Coalescing gap-tolerance: a rolling-window dip inside one sustained move still re-triggers
* **`build\\\_near\\\_miss\\\_registry.py` and `blend\\\_eval.py` are unaudited for formula-cache exposure** — `h1\\\_lag\\\_trace.py` and `h4\\\_dq\\\_threshold.py` both had it and neither was suspected
* `del run\\\_weekly\\\_review.bat`; grep `docs\\\\` for the old name
* Commit backlog: five `.py` files, `run\\\_daily\\\_review.bat`, `Daily\\\_Workflow\\\_v5\\\_3`, `Worksheet\\\_v1\\\_1`, three splices
* Six `\\\[?]` verifications in the worksheet: design-note signature, WS3 repo state, full 3-B cross-check streak, Tier-2E diff exhibit committed, closeout memo, archive/push

## 7 · Two findings that shape how to read everything

**(a) Recent accuracy decline is largely a measurement artifact.** Cohorts ran **70.8% (7/20) → 41.7% (7/21) → 29.2% (7/22)**. Dispersion rose from sd 6.02% to 7.54%; 13 then 15 HOLD names were marked wrong *purely* by breaching the ±3% band, splitting near-evenly up and down. Fifteen names moved >3% in five sessions — the band marked them wrong by construction. **Do not read this as generator degradation.** It is the strongest case yet for the parked Q4-2 volatility-scaled secondary metric (a PARALLEL SECONDARY report — the ±3% band is never re-baselined).

**(b) Small-n readings flip.** H4 reversed twice in three days; G2's primary read reversed on two observations. **Pre-commit to how a number will be read before seeing it.**

## 8 · Operational hazards learned the hard way

* **The formula cache.** `Return+5d` / `Return+10d` / `Was-Right-5d` are formulas. openpyxl reads *cached* values and any openpyxl save **clears** them — which the daily runner does every session. **Open `tracker\\\_with\\\_registry.xlsx` in Excel after each run.** `h4` refuses on a blank cache; `h1` warns and continues; `monitor\\\_strip` computes from Price columns and is immune. **Point every harness at the MASTER.**
* **A renamed tab is still the tab it was.** A retired guardrail sheet re-entered the report copy as "Sheet1" and slipped a name-based purge. Matching is now by content.
* **A clean console is not a completed run.** `h1\\\_lag\\\_trace.py` printed a full correct-looking trace, then crashed writing its `.md`, leaving the *previous* exhibit on disk looking current. Check the `Wrote:` line.
* **Retired criteria drift back.** Four separate instances found by accident before `retired\\\_criteria\\\_audit.py` was built.

## 9 · Boot set to upload

1. `docs\\\\analyst\\\_notes.md` — the institutional record (paste the three pending splices first, in order 7/27 → 7/28 → 7/29; only the last Upcoming block survives)
2. `Phase3B\\\_Closeout\\\_Decision\\\_Worksheet\\\_v1\\\_1.docx`
3. `Daily\\\_Workflow\\\_v5\\\_3\\\_Phase3B.docx`
4. `Phase3B\\\_Exit\\\_3C\\\_EDGAR\\\_Entry\\\_Criteria\\\_v1.docx`
5. Daily: `logs\\\\claude\\\_equity\\\_bot\\\_tracker.xlsx` + that day's `logs\\\\signals\\\_YYYY-MM-DD.log`

## 10 · Watch for on the next session

* **A second WS2 episode is genuinely possible.** The 7/29 AM run was pre-FOMC, so any decision-driven move on WMT or GM enters the trailing window on 7/30. This is the only thing that moves G1.
* **7/23 cohort resolves**, window also spanning the decision. A third consecutive high-dispersion cohort would settle the vol-scaling case.

\---

## Appendix — NOT IN EVIDENCE, pending DP-8/DP-9

*Produced 2026-07-28. Deliberately excluded from `analyst\\\_notes.md` because DP-8 and DP-9 are unruled. Do not cite as evidence for G1. Recorded only so it isn't lost.*

The WS2 episode detector applies four filters. Their marginal contribution to post-deploy episode count:

|Filter|Relaxed|Episodes|
|-|-|-|
|—|current (adverse, WMT+GM, 5-session, 5%)|**1**|
|Threshold → 3%||1|
|Window → 10-session||2|
|**Direction → bidirectional**||3|
|**Universe → all 24 tickers**||**13**|
|Direction + universe||**30**|

**The universe filter suppresses far more than the direction rule.** Under both relaxations:

|Era|Episodes|Confidence tracked the move|
|-|-|-|
|Pre-deploy|63|57.1%|
|Post-deploy|30|73.3%|

Split by direction — the part that matters:

|Channel|Pre-deploy|Post-deploy|
|-|-|-|
|**Adverse**|47.4% (n=38)|**100% (11/11)**|
|Favourable|72.0% (n=25)|57.9% (n=19)|

S1 fixed precisely what it was built to fix: adverse stickiness went from coin-flip to perfect across the portfolio. Favourable responsiveness did not improve. Pooled, this reads 57% → 73%; split, 47% → 100%. **Pooling would bury the strongest result in the project** — which is also why any future bidirectional detector must report the two channels separately.

Pre-deploy failures ran both ways (WMT 6/09 **+5.38%** with confidence flat at 52), so the H1 stickiness was **not** directional — the argument for DP-8 rests on that, not on episode starvation.

