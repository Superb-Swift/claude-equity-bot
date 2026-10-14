# Repo Cleanup Runbook — 2026-09-01

**Scope:** `C:\Users\rober\claude-equity-bot` root + `docs\`, `logs\`, `prompts\`, `Retired\`, `Phase 3A Files\`
**Posture chosen:** archive-only, flat root. Nothing deleted. No `.py` module, `.bat` runner, or import path changes.
**Deliverables:** `cleanup_root.bat` (step 1, required), `cleanup_docs.bat` (step 2, optional), this runbook.

---

## 1. Explore — what the tree actually holds

| Location | Entries | Character |
|---|---|---|
| root | 146 | 37 live `.py` modules + 6 `.bat` runners **buried under ~90 dated artifacts** |
| `docs\` | 40 loose + 5 subfolders | per-phase folders exist for Phase 2 / 3-A / 3-B; **Phase 3-C is loose** |
| `logs\` | 24 files + 4 subfolders | fully gitignored; 3 tracker backups mixed with the live master |
| `prompts\` | 7 | 3 generations of boot prompt, 3 kickoff prompts, 1 May-2026 scratch note |
| `Retired\` | 15 | already a working archive; tracked wholesale by `repo_catchup.bat` |
| `edgar_cache\` | 244 | gitignored working cache — **left alone** |
| `Phase 3A Files\` | 3 | root-level orphan duplicating the `docs\Phase 3-A docs\` convention |

**Root signal-to-noise:** 43 files you actually run, 103 files you don't. That ratio is the whole problem.

---

## 2. Profile — how the clutter got there (four distinct mechanisms)

| # | Mechanism | Evidence | Files |
|---|---|---|---|
| 1 | **Runners write dated exhibits to the root** | `value.bat:142/162/188`, `scan.bat:65` write `*_%RUNDATE%.md` | ~60 |
| 2 | **Defect campaigns left their tooling behind** | `apply_*.py`, `propose_*.py`, `test_dow_fix.py`, `dow_fix.diff` | 8 |
| 3 | **Patch scripts wrote `.bak` siblings** | `edgar_client.py.bak`, three `.bak-20260831_172015` | 4 |
| 4 | **Doc versioning without retirement** | `Daily_Workflow` v6_0 / v7_0 / v7_1; boot prompt ×3 | ~8 |

Each mechanism gets a different treatment below. That is the point of separating them — a single "move old stuff" rule would have caught live files.

---

## 3. Clean — what the scripts do

### `cleanup_root.bat` — step 1 (safe, run first)

`cleanup_root.bat` = **dry run**, writes a manifest, changes nothing.
`cleanup_root.bat APPLY` = performs the moves and writes `undo_cleanup_<stamp>.bat`.

| § | Action | Destination | Count |
|---|---|---|---|
| A | Dated exhibits older than the 3 kept dates | `exhibits\archive\` | **35** |
| B | One-off defect / repair scripts | `Retired\patches\` | 10 |
| C | `*.bak`, `*.bak-*`, `~$*` Office lock files | `Retired\patches\backups\` | 5 |
| D | Superseded tracker backups | `logs\Retired\` | 2 |
| E | Superseded workflow docs (v6_0, v7_0, dup `value_notes.html`, `.txt` register) | `docs\Archived\` | 4 |
| F | `Phase 3A Files\` folder, whole | `docs\Archived\` | 1 dir |
| G | `.gitignore` += `*.bak`, `*.bak-*` | in place | — |

**Net: root drops from 146 entries to ~92, and from ~90 dated artifacts to 14.**

**The keep rule (§A) is date-driven, not hardcoded** — roll `KEEP_MD` / `KEEP_QD` forward at the top of the script and re-run it monthly:

```bat
set "KEEP_MD=2026-08-24 2026-08-25 2026-08-26"
set "KEEP_QD=20260824 20260825"
```

Verified against the live tree: 35 files archived, 14 kept, **zero** live modules or non-dated exhibits caught by the patterns.

### `cleanup_docs.bat` — step 2 (optional, run when ready to commit renames)

Separate because it moves **tracked** files, which git records as renames.

1. Gives Phase 3-C its own `docs\Phase 3-C docs\`, completing the convention that already exists for Phases 2, 3-A and 3-B (~24 files).
2. Retires superseded boot/kickoff prompts to `prompts\Archived\` (5 files).

Safe with respect to `repo_catchup.bat`, which stages docs with `git add -A -- docs` (line 161) — a whole-directory add that picks up both sides of every rename.

---

## 4. Analyst notes — why specific things were *not* touched

This is the part worth reading before you run anything.

| Left alone | Reason |
|---|---|
| **`h1_lag_trace_*.md`** (6 files) | All written 2026-08-31 — this is the *current* generation, not backlog. No older generation exists to archive. |
| **`docs\analyst_notes*.md`** | The 666 KB running record. `repo_catchup.bat:17-18` and `rebuild_notes.py:24` both depend on the current names and locations. Moving any of the three would break the splice workflow. **Highest-risk file in the tree; explicitly excluded.** |
| **`repo_purge_history.bat`** | `.gitignore:62` says `Retired/near_miss_registry.xlsx` "history is purged in **JOB B**". I cannot verify from here whether JOB B has run. Left in root — confirm, then archive it manually. |
| **`edgar_cache\`** (244 files, ~120 MB) | Gitignored working cache keyed by accession number. `value.bat` passes it as `--cache`. Pruning needs a retention rule tied to filing dates, not a file-age sweep. Separate job. |
| **`Retired\`** existing contents | Already a curated archive with its own commit rationale (`repo_catchup.bat:154`). Adding to it, not reorganising it. |
| **`docs\Daily_Workflow_v7_1_Phase3C.docx`** | Current workflow — belongs at the top of `docs\`, not filed in a phase folder. |
| **`__pycache__\`, `venv\`** | Gitignored, regenerated. Deleting them is a rebuild, not a cleanup. |

### The `.gitignore` finding (§G) — this one matters

`repo_catchup.bat:151` runs `git add -A -- Retired`. `Retired\` is committed **wholesale**. So the moment §C archives `edgar_client.py.bak` (147 KB) and three more `.bak-*` files under `Retired\patches\backups\`, your next catchup run would commit **~360 KB of source backups** whose content git already has in history.

§G adds `*.bak` and `*.bak-*` to `.gitignore` in the same run that creates them. The files stay on disk for reproducibility; the repo never sees them. Ordering is deliberate — the ignore rule is written before you next run `repo_catchup.bat`, not after.

---

## 5. Separate finding — `docs\` has drifted from the project knowledge base

Not a cleanup item, but surfaced by the inventory. **17 Phase 3-C documents exist in the Claude project with no counterpart on disk**, including:

- `H1_Window_OffByOne_Defect_2026-08-26.md` — **`scan.bat:90` prints "Decide: H1_Window_OffByOne_Defect_2026-08-26.md" to the operator, and that file is not on disk.** The runner points at a document you cannot open from the repo.
- `Phase3C_ClosingReview_2026-08-13 / -14 / -24 / -25 / -26.md` — five closing reviews. `.gitignore:45` justifies ignoring the exhibits on the grounds that "the numbers survive in `docs/Phase3C_ClosingReview_*.md`, which ARE tracked." For five dates, they don't — locally.
- `DOW_CoRegistrant_XBRL_Defect_2026-08-26.md`, `OutcomeSanity_Findings_Triage_2026-08-26.md`, `Phase3C_VacationGap_PreRegistration_2026-08-26.md`, `ImpliedReturn_Sections3and4_Reading_Guide_2026-08-26.md`, `Phase3C_BandInstrument_Tooling_Proposal_2026-08-25.md`, `Phase3C_ValueGate_Amendment_Proposal_2026-08-24.md`, `Phase3C_CBRS_PathA_Evidence_v1.md`, `Phase3C_Monday_PreCommitment_2026-08-17.md`, `Phase3C_PeerRelative_NegativeResult_2026-08-17.md`, `Phase3C_ValuationLayer_SpliceEntry_2026-08-17.md`, `Phase3C_Valuation_Instrument_Scoping_WS4_v1.md`, `Phase3C_PreVacation_Closeout_Runbook_2026-08-27.md`

Three more exist under **different names** on each side (`ValuePass_ExitCode_Defect` vs `value_pass_exit_code_fix`; `Phase3C_SpliceEntry_2026-08-19/-20` vs `docs\note splices\splice_2026-08-19/-20.md`; `Repo_Catchup_Runbook` `.md` vs `.txt`).

The `.gitignore` rationale for discarding exhibits depends on the closing reviews being tracked. Syncing these down closes that gap. Say the word and I'll write all 17 into `docs\Phase 3-C docs\`.

---

## 6. Run order

```bat
cd /d C:\Users\rober\claude-equity-bot

REM  1. Look before you leap
cleanup_root.bat
notepad cleanup_manifest_*.txt

REM  2. Execute
cleanup_root.bat APPLY

REM  3. Confirm the runners still work end to end
scan.bat
value.bat

REM  4. Commit (§G changed .gitignore; §B/§C added files under Retired\)
git status
git add -A
git commit -m "chore: archive dated exhibits and one-off patch tooling; ignore *.bak"

REM  5. OPTIONAL, when ready for rename churn
cleanup_docs.bat
cleanup_docs.bat APPLY
git add -A -- docs prompts
git commit -m "chore: group Phase 3-C docs, retire superseded prompts"
```

**Rollback at any point:** run the `undo_cleanup_<stamp>.bat` the APPLY run wrote. Every action is a `move`; the undo is the same moves reversed.

### Guards built into both scripts

- Refuse to run unless `main.py`, `signal_scan.py` and `.gitignore` sit beside them (no accidental run in the wrong folder).
- Never overwrite: a name collision at the destination is logged `[CONF]` and the file is **left in place**.
- `dir /b` snapshots each file list before the loop moves anything.
- Dry run is the default; `APPLY` must be typed.
- Every run writes a timestamped manifest, so you can diff two runs.

### Two things to expect

1. Step 3 (`scan.bat` / `value.bat`) will regenerate today's exhibits into the root. That is correct — the keep-window is about *old* dates. §A archived nothing dated 08-24 or later.
2. `cleanup_docs.bat` matches `docs\Phase 3-C — E4 Endpoint Pre-Registration v1_2.md` by wildcard because the filename contains an em dash. If your console codepage mangles it, the manifest will show `[none]` or `[FAIL]` for that one file — move it by hand and ignore the rest of the noise.
