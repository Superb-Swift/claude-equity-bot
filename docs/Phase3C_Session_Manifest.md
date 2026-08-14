# Phase 3-C Session Manifest v1 — Files, Uploads \& Repo Organization

*Claude Equity Bot · companion to `Phase3C\_Kickoff\_Prompt.md` (to be written), `Phase3B\_Closeout\_Memo.md`, and `Phase3C\_EDGAR\_Scope\_Spec.md`. Written **2026-07-31** at the Phase 3-B closeout, superseding `Phase3B\_Session\_Manifest.md` v2 for new sessions. Purpose: make any new chat productive in one upload pass. Advisory-only · no orders · not financial advice.*

## How new chats work (why this manifest exists)

Claude's workspace **resets between conversations**. Memory carries the project's *story* — phases, verdicts, constraints, conventions — but **not file contents**, so every new chat needs its working files uploaded fresh or pulled from the repo (Option B). Within a conversation files persist across messages; you only re-upload when data changes (a new day's `logs\\claude\_equity\_bot\_tracker.xlsx` or `logs\\signals\_YYYY-MM-DD.log`) or after you edit a file (splicing the notes, signing an instrument).

**Source-of-truth rule:** uploaded files always win. The repo lags your working tree between pushes, so upload *your current* `docs\\analyst\_notes.md` and `logs\\claude\_equity\_bot\_tracker.xlsx`, never the repo copies, whenever they are ahead.

**Naming rule, unchanged and load-bearing:** `logs\\claude\_equity\_bot\_tracker.xlsx` is **THE MASTER**. `tracker\_with\_registry.xlsx` is the **GENERATED REPORT COPY**. Never a bare "tracker." Monitoring reads the master; the report copy is an output and is refused as an input by `log\_tracker\_crosscheck.py`.

\---

## Tier 0 — NEVER upload, never push

|File|Why|
|-|-|
|`token.json`|Schwab OAuth token — secret|
|`.env`|API keys (Anthropic, Finnhub) **and, new in 3-C, `SEC\_USER\_AGENT`** — secret|
|`signal\_state.json`|WS2 runtime cache (S1 prior-signal state); re-seedable from the master via `seed\_signal\_state.py`, so a derived artifact and never a chat input|
|`edgar\_cache/` *(new in 3-C, if it lands on disk)*|Cached CIK map + per-ticker submissions. Derived, re-fetchable, and potentially large|

All gitignored. Verify before every push: `git ls-files | findstr /i "token .env signal\_state edgar\_cache"` must return nothing.

**3-C note:** `SEC\_USER\_AGENT` is mandatory for EDGAR access — a missing or generic User-Agent returns 403 and a \~10-minute IP block. It is a secret by Tier-0 convention even though it is only an identifying string.

\---

## Tier 1 — The boot set (start of any new 3-C chat)

|File (location)|Size|Role|
|-|-|-|
|`prompts/Phase3C\_Kickoff\_Prompt.md`|\~13 KB|**E1's named instrument** — mandate and worksheet-entered scope, the EDGAR coverage finding, the E4 rate rule, standing constraints, DPs, exit clause, session menu. Written 2026-07-31|
|`docs/Phase3B\_Closeout\_Memo.md`|\~35 KB|Dispositions, standing constraints (§6), what 3-C inherits (§7). **The 3-A/3-B equivalent — this is the constraints anchor**|
|`docs/analyst\_notes.md`|\~290 KB|The running record — upload **with the latest dated splice applied**. Required whenever a session should end with a spliced entry (most sessions)|

These three anchor any session: mandate, constraints, and the place the session gets recorded.

**Governance reference (local-only — `\*.docx` is gitignored, so upload directly when a session touches process or gates):**

* `Phase3B\_Exit\_3C\_EDGAR\_Entry\_Criteria\_v1.docx` — the pre-registered **E1–E6** entry gates and DP-1…DP-5. The instrument 3-C is judged against.
* `Phase3B\_Closeout\_Decision\_Worksheet\_v1\_2.docx` — signed 2026-07-31; carries the DP-5 overlap ruling and the E1 prerequisite amendment.
* `Daily\_Workflow\_v5\_3\_Phase3B.docx` — the operating procedure the monitors are read against. **Needs a v6 revision for 3-C** (the `E\[…]` tag, the new era label, and the two new harnesses).
* `Phase3C\_EDGAR\_Scope\_Spec.md` — the E1 scope content plus E3/E4 pre-registration. Repo-pullable once pushed.

\---

## Tier 2 — Add-ons by session type

### A. Daily / monitoring session

|Upload|Notes|
|-|-|
|`logs\\claude\_equity\_bot\_tracker.xlsx`|**THE MASTER — this is the monitoring input.** Upload *after* the day's paste and after opening the report copy in Excel|
|`logs\\signals\_YYYY-MM-DD.log`|The day's AM log for the cross-check. PM runs are diagnostic-only — never paste PM rows, and re-seed S1 state after one|
|`tracker\_with\_registry.xlsx`|*Optional and secondary.* Carries the Monitor Strip and Near-Miss registry tabs. Useful for reading those embeds; **not** a substitute for the master|

Run before the session: `scan.bat` (or `signal\_scan.py` + `log\_tracker\_crosscheck.py` separately). Both are formula-cache immune and write nothing.

### B. EDGAR build session (the 3-C workstream)

|Upload / pull|Why|
|-|-|
|`context\_providers.py`|The registry EDGAR rides. `run\_prompt\_context` is the wired hook and returns `""` until a provider registers. Repo-pullable|
|`claude\_signal.py`, `main.py`|The one-parameter integration surface — `get\_signal(..., extra\_context="")` and the `run\_prompt\_context` call. Repo-pullable|
|`analyze\_log.py`, `parse\_log\_to\_tracker.py`|**Required for the E3 pre-deploy parser audit.** The regex surfaces must be reviewed against the `E\[…]` tag and the new era label *before* go-live|
|`Phase3C\_EDGAR\_Scope\_Spec.md`|The build spec: data path, extraction shape, provider signature, parser-audit checklist|

### C. Acceptance / measurement session (post-deploy)

|Upload / pull|Why|
|-|-|
|`logs\\claude\_equity\_bot\_tracker.xlsx` + `logs\\signals\_\*.log`|Outcomes plus the `E\[…]` tag source|
|The E4 endpoint exhibits, once the readers exist|DQ-mix shift, filing-adjacent accuracy, event-window behaviour|
|`signal\_scan.py`, `log\_tracker\_crosscheck.py`|The per-session harnesses. Repo-pullable once pushed|

### D. 3-B legacy (only when a session revisits a closed question)

|Upload|Why|
|-|-|
|`Q1R\_Diagnostic\_Memo.md` / `Q4R\_Scoping.md`|The guardrail and DQ questions, both closed. Needed only if a re-open trigger fires|
|`WS1\_\*` / `WS2\_\*` docs|The blend (DESCOPED) and the S1/D1 build. Needed only for a G2 re-open or a G1 episode read|
|`h1\_lag\_trace.py`|Still the episode-counting instrument of record if G1 is ever revisited|

\---

## New in 3-C — modules \& conventions

*Nothing below is live yet. This section is written so a fresh chat is not surprised when it lands.*

* **New module:** `edgar\_client.py` — a `ContextProvider(mode="prompt")` appended to `REGISTRY`. Covers Form 4 (insider transactions), 8-K (material events), and 10-Q/10-K MD\&A extracts. One client, per-ticker, cached.
* **Integration surface is one line.** `main.py` calls `run\_prompt\_context(ticker, caches)` and passes the text to `get\_signal(..., extra\_context="")`. The blend engine, risk gate, tracker schema and logging are untouched. This is the payoff of the WS1 provider registry — and the reason E1's WS3 prerequisite was amended at the 3-B closeout.
* **Era stamp:** `A-S1D1-B1` → **`A-S1D1-B1-E1`** (DP-2 default: single live arm, a generator-version stamp, **not** an A/B — the A/B program stays terminated). *DP-2 is not yet ruled; rule it at the kickoff review.*
* **Log tag:** `E\[8k=2; form4=+3/-1; periodic=10-Q@2026-05-01]`, appended after `B\[…]`. Both parsers tolerate trailing tags by pattern — **verify, do not assume** (E3).
* **Graceful degradation:** any fetch failure or missing filing omits the EDGAR section and the run continues, exactly as a missing `S1` or trajectory section degrades today.
* **SEC etiquette:** mandatory `SEC\_USER\_AGENT`; **≥120 ms** between calls (10 req/sec per IP); no API key. Cache the CIK map (static) and per-ticker submissions per run.
* **DP-4 default:** filing presence does **not** feed `data\_quality` in v1. Measure first; couple later only if E4-2 supports it.
* **DP-3 default:** EDGAR **skips CBRS** entirely until the Q4 2026 Path-A review.

### Carried from 3-B — conventions a new chat must not relearn

* **Three confidence channels**, all logged every line: `confidence\_raw` (model) → `confidence` (base operative, official) and in parallel `confidence\_blend`. **Note the naming trap:** the JSON field `confidence\_blend` carries the value *after* D1 damping, while the `B\[…]` tag's `blend=` carries the value *before* it.
* **D1's FLOOR = 35** clamps the reduction and never raises confidence. The `D\[…]` tag reports the *computed* damp, not the *applied* reduction, so `raw − op` is smaller than `damp` whenever the floor binds. Not a defect (closeout memo §4.4).
* **The formula cache.** `Return+5d` / `Return+10d` / `Was-Right-5d` are formulas; openpyxl reads *cached* values and any openpyxl save clears them, which the daily runner does every session. **Open `tracker\_with\_registry.xlsx` in Excel after each run.** Compute from the Price columns wherever possible — those are cache-independent.
* **Phase tag** `\[PHASE 3-B DRY RUN]` — the literal "DRY RUN" is load-bearing for `analyze\_log`'s regex. **Changing the phase token is an E3 audit item.**
* **Seed / re-seed discipline** — `python seed\_signal\_state.py --tracker tracker\_with\_registry.xlsx` before the first live day and again after any PM diagnostic run.

\---

## Standing constraints in force at 3-C entry

|Constraint|Status|
|-|-|
|**T1 — advisory only**|In force. No execution, ever. Execution remains its own future gate|
|**T3 — no band-ordering reliance**|In force, tool-enforced by `retired\_criteria\_audit.py`|
|**Q1 guardrail**|**RETIRED** — not suspended. Q1-R diagnosed it as a calibration improvement|
|**T2**|**RETIRED.** No standing tripwire on band ordering remains|
|**KEEP 70%**|Unchanged. Near-miss BUYs that would have paid: 13/32 = 40.6%|
|**±3% HOLD band**|Unchanged and **NOT re-baselined**. Vol-scaled reporting is parallel-secondary only|
|**CBRS Path A**|Excluded to Q4 2026|
|**Watchlist**|24 tickers; frozen through 3-B, reviewable at this boundary|
|**DP-5**|**RULED 2026-07-31** — overlap permitted for 3-C scope work only; no go-live, no 3-B gate closes or relaxes|
|**G2 / the blend**|**DESCOPED.** Base signal is the official advisory output. Re-open triggers T-G2-a/b/c|
|**G1 / WS2**|**INSUFFICIENT TEST CONDITIONS.** S1+D1 remain deployed and running|

\---

## The measurement lesson 3-C must apply

Two of 3-B's six gates could not be settled, and both failed for the same reason: **the pre-registered criteria required event counts that the system's own output rate cannot supply on a phase timescale.** G1 needed four adverse tracer moves; the market gave one in nineteen sessions. G2's gate-flip condition needed a favourable base-vs-blend disagreement; the system emitted 32 BUYs in 1,243 rows and produced one flip.

**At E4 pre-registration, every endpoint must carry an explicit expected event rate and the resulting time-to-read, computed before go-live.** If an endpoint needs more filing-adjacent cohorts than a 24-ticker watchlist can produce in a phase, that has to be visible at pre-registration — not discovered at the exit review. See `Phase3B\_Closeout\_Memo.md` §0 and §7.

Related and relevant to E4-2: directional signals are 2.6% of output and 78% single-name. Any endpoint gated on BUY/SELL volume will be starved.

\---

## Option B — repo pull instead of code uploads

The repo is public (`Superb-Swift/claude-equity-bot`) and Claude's sandbox can reach GitHub, so for **code files** you can say "pull from the repo" instead of uploading. Caveats: uploaded files always win (the repo lags between pushes); **data files** — the master, day logs, fresh exhibits — should still be uploaded since they change daily; and the **`\*.docx` governance docs are gitignored**, so those are upload-only.

**Commit backlog to clear before relying on Option B for 3-C:** `signal\_scan.py`, `log\_tracker\_crosscheck.py`, `scan.bat`, `monitor\_strip.py`, `retired\_criteria\_audit.py`, `run\_daily\_review.bat`, the 7/30 and 7/31 splices, and this manifest.

\---

## Repo map (at the 3-B/3-C boundary)

* **root** — live code + `tracker\_with\_registry.xlsx`. WS1 additions: `sector\_map.py`, `context\_providers.py`, `blend\_providers.py`, `blend\_engine.py`. WS2: `signal\_state.py`, `seed\_signal\_state.py`. Harnesses: `h1\_lag\_trace.py`, `h4\_dq\_threshold.py`, `blend\_eval.py`, `build\_near\_miss\_registry.py`, `monitor\_strip.py`, `retired\_criteria\_audit.py`, `signal\_scan.py`, `log\_tracker\_crosscheck.py`.
* **`prompts/`** — `Phase3A\_Kickoff\_Prompt.md`, `Phase3B\_Kickoff\_Prompt.md`, and `Phase3C\_Kickoff\_Prompt.md` once written.
* **`docs/`** — `Phase3A\_Closeout\_Memo.md`, `Phase3B\_Closeout\_Memo.md`, `analyst\_notes.md`, the WS1/WS2 docs, `Q1R\_Diagnostic\_Memo.md`, `Q4R\_Scoping.md`, `Phase3C\_EDGAR\_Scope\_Spec.md`, this manifest.
* **`docs/Archived/`** — frozen 3-A snapshots. **`Phase 3A Files/`** — frozen closeout code snapshots. **`docs/Phase 2 docs/`** — Phase 2 archive.
* **`Retired/`** — `run\_ab\_test.bat`, retired hypothesis MDs, and the guardrail artifacts. `guardrail\_trace.py` still wants a RETIRED header block.

\---

## Housekeeping carried into 3-C

1. **Enter the kickoff scope into the worksheet** to close E1 (`Phase3C\_Kickoff\_Prompt.md` is written).
2. **Rule DP-2** (deploy mode) at the kickoff review; DP-3, DP-4, DP-3C-a/b/c follow.
3. **Issue worksheet v1.3** — DP-10's signature line reads "70%" while the ruling is **No Cap**; §6.2's G2 scoring is superseded by the 07-31 `blend\_eval.py` run; DP-9's correction note is attached to the wrong sentence. See closeout memo §3.7.
4. **Revise the daily workflow to v6** for the `E\[…]` tag, the new era label, and the two new harnesses.
5. **Carried tooling items:** `monitor\_strip.py`'s "last episode" date is computed pre-coalescing; T2's tooling still prints live instructions; three audit exclusions before the pre-commit hook (`Retired\\`, `docs\\analyst\_notes.md`, `T2`-as-test-case-ID); `build\_near\_miss\_registry.py` and `blend\_eval.py` unaudited for formula-cache exposure; `h4\_dq\_threshold.py`'s stale console string.
6. **Keep this manifest current** — add a Tier-2 row when `edgar\_client.py` lands.

\---

## Paste-ready chat opener (new 3-C session)

> \*\*Phase 3-C session — \[EDGAR build / acceptance read / daily monitoring / kickoff review].\*\*
> Attached: \[list uploads per the tier tables] — \*or\* "pull code from the repo."
> Goal for this session: \[one line].
> State in force: advisory-only, no orders; generator era \*\*A-S1D1-B1\*\* (S1 + D1 live, blend DESCOPED and shadow-only); \*\*T1\*\* mandatory pre-execution; \*\*T3\*\* no band-ordering reliance; guardrail \*\*RETIRED\*\*, \*\*T2 RETIRED\*\*; \*\*KEEP 70%\*\*; ±3% HOLD band not re-baselined; CBRS Path A excluded to Q4 2026.
> Phase 3-B closed 2026-07-31 — G5 SERVED, G1 INSUFFICIENT TEST CONDITIONS, G2 DESCOPE, G3 PARK, G4 and G6 VERDICT.

\---

## Phase 4 horizon (for planning, not active)

Nothing is scoped. Two threads are parked and would be the natural candidates: the **Q4-2 volatility-scaled secondary metric** (the case for which 3-B quantified — parallel report only, never a re-baseline), and **execution readiness under T1**, which remains its own gate requiring Q1-R diagnosed (done), positive live paper-EV over a pre-set cohort count, and validated risk controls.

\---

*This manifest is a living doc — update it when 3-C adds modules. Advisory-only · no orders · not financial advice.*

