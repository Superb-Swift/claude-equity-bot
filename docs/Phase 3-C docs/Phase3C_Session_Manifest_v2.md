# Phase 3-C Session Manifest v2: what a Claude session reads, and where it lives

*Claude Equity Bot · v2.0 · written 2026-10-21 · **supersedes `Phase3C_Session_Manifest.md` v1 (2026-07-31)**, which stays in place until the next clean-up script moves it to `docs\Archived\`. Companion to Daily Workflow v8.1 §11 (step 8, the Claude monitoring session). Advisory-only · no orders · not financial advice.*

> **AMENDED 2026-10-22 (v2.1, before its first commit).** Sections 4, 5, 6 and 8 are updated for the 2026-10-22 tooling and rulings (DP-3C-az..bk; `claude/Phase3C_Rulings_Delegated_2026-10-22.md`, `claude/Implementation_Record_2026-10-22.md`). v1 has been moved to `docs\Archived\`. Nothing else changed. **2026-10-23:** §2 row 1 no longer calls R8 unruled (DP-3C-be ruled it on 10-22).

**Why v2.** Followed literally, v1 loads the wrong record. Its Tier 1 names `docs\analyst_notes.md`, which has been frozen since 08-20; the master has been `docs\analyst_notes_2026-10-09.md` since the 10-09 catch-up. The 3-B closeout memo has moved. v1 also cites Workflow v5.3 and era A-S1D1-B1, and it lists none of the exhibits the daily review now produces.

---

## 0 · How a session gets its files (two routes)

| Route | When | What happens |
|---|---|---|
| **A. Linked computer** (preferred) | The chat is open in the Claude desktop app with this computer linked | Claude reads `C:\Users\rober\claude-equity-bot` directly and pulls the tiers below itself. Nothing is uploaded. Claude writes to the device only when asked, and says what it wrote |
| **B. Upload** | No link | Upload Tier 1 and the Tier 2 set for the session type. Code can come from the repo (`Superb-Swift/claude-equity-bot`), but the repo lags the working tree |

**Also attached to every session:**

- **The Claude project.** Closing reviews, rulings and runbooks are filed under `claude/` there. A session reads them directly, so they never need uploading.
- **Memory.** It carries the story (phases, conventions, verdicts). It does not carry file contents.

**Source of truth, unchanged:** device files beat project copies, and project copies beat the repo. Where two disagree, say so.

**Naming, unchanged and load-bearing:**

- `logs\claude_equity_bot_tracker.xlsx` is **THE MASTER**.
- `tracker_with_registry.xlsx` is the **GENERATED REPORT COPY**. It is an output, and every tool that reads the master refuses it as an input.
- Never write a bare "tracker."

---

## 1 · Tier 0: never read, never uploaded, never pushed

| File | Why |
|---|---|
| `token.json` | Schwab OAuth token |
| `.env` | Anthropic, Finnhub and `SEC_USER_AGENT` secrets |
| `signal_state.json` | S1 runtime state. Derived; re-seed it with `seed_signal_state.py` against the master, never against the report copy |
| `edgar_cache\` | Derived filings cache (about 160 MB). Read-only under DP-3C-ai; a count-only check (E4-3's possible unseen 8-Ks) may read it |
| `venv\` | Environment |

**Held-back docs.** Several docs and the notes master name holdings by account. They stay local: commit by path, and never use a bare `git add -A` (Workflow v8.1 §22).

---

## 2 · Tier 1: the boot set (start of any 3-C session)

| # | File (location) | Role | How to read it |
|---|---|---|---|
| 1 | `docs\analyst_notes_2026-10-09.md` | **The record (G6).** The dated notes master; splices go here as plain text (Workflow v8.1 §11). R8 is ruled: this file is the G6 location, local only and never published (DP-3C-be, 2026-10-22) | About 880 KB, so do not read it whole. Read the header notes, both Index lists, the last three or four dated entries, and `# Upcoming — CURRENT` at the end |
| 2 | Latest closing review: `claude/Phase3C_ClosingReview_<date>.md` (project). Device copies are in `Claude outputs\` and, after housekeeping, `docs\Phase 3-C docs\` | Current findings, the current Upcoming block, and the Standing line | Whole |
| 3 | `python rulings.py --standing` (console output) | The standing rulings registry. The notes' Standing table is stale by design | Whole |
| 4 | `prompts\Phase3C_Kickoff_Prompt.md` | **E1's instrument:** the 3-C mandate, standing constraints, exit clause (§8) and working rules (§10). Its DPs have since been ruled; the registry governs | §1, §4, §8 and §10 |
| 5 | `docs\Phase 3-B docs\Phase3B_Closeout_Memo.md` | The constraints anchor: 3-B dispositions (G1 INSUFFICIENT TEST CONDITIONS, G2 DESCOPE), the measurement lesson, operational lessons | §0, §3.1, §4 and §8 |

**Governance reference, read when a session touches process or gates.** `*.docx` files are git-ignored, so they are local only.

- `docs\Daily_Workflow_v8_1_Phase3C.docx`: the operating procedure, effective 2026-10-16. A redline is in `Claude outputs\`.
- `docs\Phase4_Execution_Readiness_Register_v1.md`: P4-1 … P4-5.
- `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1.docx` and `Phase3B_Closeout_Decision_Worksheet_v1_2.docx`: E1–E6 and the signed 3-B dispositions.

---

## 3 · Tier 2: add-ons by session type

### 2A · Daily monitoring and closing review (Workflow step 8)

**Before the session:** the evening block (Workflow v8.1 §3) has run in order: paste and save, `enter_closes`, `scan.bat`, `run_daily_review.bat`, `value.bat`, then the Excel refresh of the report copy.

| File | Notes |
|---|---|
| `logs\claude_equity_bot_tracker.xlsx` | **THE MASTER. The monitoring input** |
| `logs\signals_<date>.log`, and the previous session's log | The cross-check, and the log that carries last night's closes for Check F. PM runs are diagnostic only |
| The `scan.bat` console output | Check F tiers, `[b]`, `[G]`, the calendar note, trail audit, advisory guard |
| `signal_scan_<date>.md` | Must exist and be written **before** the review |
| `near_miss_registry.md`, `actionable_registry.md`, `monitor_strip.md` | KEEP-70, the gate-cleared ledger, G1, DP-3C-w, the WS1 context |
| `e4_counter.md` | E4 clock, E4-2, E4-3. Counts only |
| `h4_dq_threshold_baseline.md` and the six `h1_lag_trace_{WMT,GM}{,_3B,_raw_3B}.md` | H4; the G1 tracers |
| `value_card_<date>.md` (and `.json`) | The valuation layer's "what changed" and decision card |
| The review and `value.bat` closing banners | WRITTEN / STALE / ABSENT; the value pass's state |
| The last lines of `logs\outcome_close_repairs.log`, plus `logs\formula_repairs.log` if present | Every close entered or repaired, and every formula repair, since the last session |
| `logs\instrument_readings.json` | The readings ledger (H4 streak, DP-3C-w) |
| `tracker_with_registry.xlsx` | Secondary. Carries the embedded sheets. **Check that step 7 ran:** cached returns present, Dashboard B53/B54 filled |
| *For a full re-run:* every `logs\signals_*.log`, including the month folders | The registries, strip and E4 counter read the whole history. On a partial set they will not reproduce the device exhibits |

**Checks the session makes** (Workflow v8.1 §11, plus the 10-20 additions):

1. The cross-check passes, the era reads `A-S1D2-B1-E1`, and the trail audit and advisory guard are clean.
2. Last night's closes produced no MATERIAL Check F item. No arm printed anything but a count.
3. `signal_scan_<date>.md` predates the review, and no STALE or ABSENT line appears.
4. **Due-but-blank = 0** on the NYSE calendar. `outcome_sanity` does not check this yet (proposed Check H).
5. **The K–N formulas are canonical.** `python repair_return_formulas.py` (a dry run) prints `Nothing to do`. Proposed Check I would automate this.
6. **Every directional row's executability, and any held-set transition**, feeds the #6a decision journal.
7. **G1 tracer rows on the DP-3C-ax session basis**, checked by hand until the code lands.

### 2B · Phase 3-C exit review (expected the week of 11-09; backstop 2026-11-20)

Everything in 2A, plus:

| File | Why |
|---|---|
| `docs\Phase 3-C docs\Phase3C_E4_Endpoint_PreRegistration_v1.md`, `Phase3C_E4_PreReg_v1_1_amendments.txt`, `Phase3C_E4_PreRegistration_v1_3_Amendment_DP-3C-t.md` | The endpoints as pre-registered and amended. v1.2 is in `docs\Archived\` |
| `docs\Phase 3-C docs\E4_2_Volatility_Tier_Table_FROZEN_2026-08-10.md` | E4-2's strata. Not re-cut |
| `claude/Phase3C_Ruling_DP-3C-ay_2026-10-09.md` (project) | The exit hold, the backstop, and "every endpoint read once, together" |
| `docs\Phase 3-C docs\Phase3C_Exit_and_Phase4_Standing_2026-09-02.md`, `Phase3C_Rulings_2026-09-03.md`, `Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md`; `Claude outputs\Phase3C_Rulings_2026-09-25.md` | The rulings the exit is judged under |
| `claude/OutcomesReview_GapAnalysis_2026-10-09.md` (project) | The rulings owed at the exit: the arms against a Phase 4 prompt, generator continuity, D6, the #1 and #2 pre-registrations |

**One-time reads at the exit, each once:** E4-2, E4-3, DP-3C-w (its second read), DP-3C-av and DP-3C-aw. Until R1 lands in code, they are protected by procedure only: read after a later log has carried every resolving close.

### 2C · Master repair and maintenance

The master, its newest backups (`logs\` and `logs\Retired\`), and both ledgers (`outcome_close_repairs.log`, `formula_repairs.log`). The tools: `enter_closes.py`, `repair_outcome_close.py`, `repair_return_formulas.py`, `outcome_sanity.py` and `trading_calendar.py`. All logs.

**Rule:** rehearse on a scratch copy first. The device write goes through the tool, never through an openpyxl save.

### 2D · Valuation layer

`value.bat`, `value_card.py`, `implied_return.py`, `value_anchor.py`, `band_price.py`, the dated exhibits (in the root and in `exhibits\archive\`), and `quote_dump.json`. `value_card` reads every dated `implied_return` exhibit in both places. Archive old exhibits; never delete them.

### 2E · Repo and housekeeping

`.gitignore`, the output of `git status --short`, `README.md`, and the latest clean-up script and manifest (`cleanup_2026-10-14.bat` is the model). Workflow v8.1 §22 governs.

### 2F · 3-B legacy (only to revisit a closed question)

`docs\Phase 3-B docs\`: `Q1R_Diagnostic_Memo.md`, `Q4R_Scoping.md`, the `WS1_*` and `WS2_*` docs. Also `Retired\` for retired harnesses.

---

## 4 · Map: who writes what (the files a session reads)

| Runner / tool | Writes |
|---|---|
| `run_daily.bat` (09:30 CT) | `run_guard.py` first (refuses a non-session or no-run day and a second run; asks for CONTROL if `EQUITY_EDGAR` is not 1; warns on a late start), then `logs\signals_<date>.log`, `logs\inputs_<date>.jsonl` (what the model was shown; local), `paste_today.tsv`, `signal_state.json`, `logs\summary_history.txt` and `logs\suggestions_history.txt` |
| You, in Excel (step 2) | The day's rows in the master (paste, drag K:N, save) |
| `enter_closes.py --catch-up` (step 3) | The master's H/I/J cells for every settled session still blank, PRECISION-tier cells settled to the log close (DP-3C-bd), their cached returns, a timestamped backup, and `logs\outcome_close_repairs.log`. `settle_precision.py` is the settle step alone |
| `scan.bat` (step 4) | `signal_scan_<date>.md`, plus console output (cross-check, `outcome_sanity`, calendar, trail audit, advisory guard) |
| `run_daily_review.bat` (step 5) | `chain_check.py` first (closes, scan, the previous session's value pass and step-7 refresh); then six `h1_lag_trace_*.md`, `h4_dq_threshold_baseline.md`, both registries (`.md`/`.xlsx`), `monitor_strip.md`/`.png`, `e4_counter.md`, `logs\instrument_readings.json`, and a rebuilt `tracker_with_registry.xlsx` |
| `value.bat` (step 6) | `quote_dump.json`, `band_price_` / `implied_return_` / `value_anchor_` / `value_card_<date>`, `earnings_calendar_<date>` (V5) and `ttm_eps_<date>` (V2, cache in `valuation_cache\`), and the Value Card sheet (step 5b, today's date only) with both beside the class (DP-V3) |
| Excel refresh (step 7) | Restores the report copy's formula cache |
| `repair_outcome_close.py`, `repair_return_formulas.py` | Master repairs, each with a backup and a ledger line (`--source-note` carries an external close's provenance) |
| `decision_journal.py` (operator) | `logs\decision_journal.tsv` and `logs\thesis_registry.tsv`: facts from the logs, reasons in the operator's words. Local; never read into a review as data about accounts |
| `prune_signal_state.py` (operator) | Departed names out of `signal_state.json`, with a backup |

---

## 5 · Conventions a new session must not relearn

**Data and procedure**

- **The formula cache.** Any openpyxl save blanks Excel's cached results. Step 7 restores them. Compute from the Price columns wherever possible.
- **K–N formulas measure from the signal price** (column G). "Drag K:N from the row above" copies whatever that row holds. Rows 2032–3000 carried a fill-right pattern from after the 09-16 cleanup until it was repaired on 2026-10-21.
- **The evening command is `enter_closes --catch-up`** (2026-10-22, DP-3C-ba). It enters every settled session still blank, so a missed evening is caught the next night; with no flag it still enters the last settled session only, which is how 10-19 was missed. `outcome_sanity` Check H now fails the scan on any settled-but-blank cell.
- **Order:** paste and save before `enter_closes`. Since 2026-10-22 it REFUSES a session whose cohort is not pasted, and skips any close no guard could check as `UNGUARDED` unless `--allow-unguarded`.
- **One-time reads are protected in code** (DP-3C-bb, `rulings.read_protection`): recorded only once a later log has carried the resolving close. The DP-3C-w exit re-read is `build_actionable_registry.py --exit-read`.
- **The log's close series can be back-adjusted** after a distribution (SND, D9 2026-10-22). The master holds official unadjusted closes; a Check F item is adjudicated against an external Close column, never by the digit signature alone.

**Instruments**

- **Channels:** `confidence_raw` → `confidence` (operative), with `confidence_blend` alongside. The JSON field `confidence_blend` carries the **post-damping** value. FLOOR is 35.
- **G1:** RAW channel (DP-3C-an), five-NYSE-session basis off Px@signal (DP-3C-ax, in code since 2026-10-22: a row whose base session has no row is NOT EVALUABLE). Read once on 2026-10-21: MET (weak); recorded beside 3-B's INSUFFICIENT TEST CONDITIONS, not amending it (DP-3C-az, delegated). Not re-read in Phase 3-C.
- **E4 is blind** (DP-3C-ay). Count; never read. Where a row is both a G1 row and an E4-3 event row, report only what G1 needs.

**The record**

- **Upcoming is a single block, replaced, never appended beside.** Superseded blocks stay in their slots in the notes, stamped.
- **Splices go into the dated notes master as plain text**, never into the reading slice. Corrections are dated and visible.
- **Verification taxonomy:** `[V]` verified this session, `[R]` from the record, `[?]` needs confirmation. Conclusions first. One git command at a time.

---

## 6 · Standing constraints (as of 2026-10-22)

| Constraint | Status |
|---|---|
| **T1, advisory only** | **Permanent** (DP-T1, Rob, 2026-09-16). Phase 4 means decision-support quality |
| **Era / generator** | `A-S1D2-B1-E1`; `claude-sonnet-4-6` (pinned; retirement not before 2027-02-17; temperature unset) |
| **Phase 3-C** | **OPEN** (DP-3C-ay):<br>• clock MET; E4-1 INVALID;<br>• E4-2 190/150, counts only;<br>• E4-3 15/20 (DOW 10-22 pending), backstop 2026-11-20;<br>• DP-3C-ai freeze to the exit: no prompt, damping or population change |
| **KEEP-70** | Basis ruled (DP-3C-y: episode, opening row, ≤ 50.0%). 20/35, NOT SUPPORTED. The gate does not move (DP-3C-au) |
| **H4** | PROMOTED (DP-3C-x; stands per DP-3C-ak). Live 32/62 |
| **Gate-cleared ledger** | 9/18 episode basis; DP-3C-l reading standard NONE |
| **G1** | Read at n = 4, bar MET (2026-10-21), flagged toward convenience. Recorded beside 3-B, does not amend it (DP-3C-az, delegated, reversible) |
| **T3, ±3% band, E4-2 tier table** | No band-ordering reliance; the band is NOT re-baselined; the tier table is NOT re-cut |
| **WS1 / G2** | DESCOPED; context only |
| **Valuation layer** | Off-prompt (DP-V1); DP-V2 counterfactual, counts only, stop 2026-12-31 |
| **Watchlist** | 28 rows; no mid-window population change. The operator's post-exit list is held for the exit review (DP-3C-bk) |

The registry (`python rulings.py --standing`) governs where this table and a ruling disagree.

---

## 7 · Paste-ready opener

> **Phase 3-C session: [closing review for <dates> / exit review / master repair / valuation / housekeeping].**
> Files: [linked computer: "read them from the project folder per Session Manifest v2"] or [attached: Tier 1 + Tier 2<x>].
> Goal: [one line].
> State in force: advisory-only, permanently (DP-T1); era **A-S1D2-B1-E1**; Phase 3-C open under DP-3C-ay (E4 blind, counts only; DP-3C-ai freeze to the exit); KEEP-70 on the episode basis; ±3% band not re-baselined.
> End with: the closing review in the project, a splice entry for `docs\analyst_notes_2026-10-09.md`, and a replacement Upcoming block.

---

## 8 · Housekeeping for this manifest

1. ~~Move v1 to `docs\Archived\`.~~ Done 2026-10-22; the commit records it as a rename.
2. **`docs\analyst_notes_current.md` is untracked** (DP-3C-be, option A): removed from the index and excluded locally, so a regenerated slice can never publish the master. Regenerate it locally if a reading slice is wanted; never commit it.
3. ~~R8: rule where the G6 record lives.~~ Ruled DP-3C-be: the dated local master `docs\analyst_notes_2026-10-09.md`, never published; a new dated master opens at the exit review.
4. **Keep this manifest current.** Add a row whenever a runner starts writing a new exhibit, and update §6 at each ruling.

*Advisory-only · no orders · not financial advice.*
