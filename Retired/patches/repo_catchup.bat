@echo off
setlocal
REM ==========================================================================
REM  repo_catchup.bat  -  v3, 2026-08-22
REM  Claude Equity Bot . repo Superb-Swift/claude-equity-bot
REM
REM  v2 CHANGES, after the v1 live run of 2026-08-21:
REM   1. PARSE BUG FIXED. v1 wrote  set "FAIL=...commit(s)"  inside a
REM      parenthesised IF block. cmd closes the block on the ")" in "(s)" and
REM      chokes -> "BEHIND was unexpected at this time." The STOP was correct;
REM      only its reporting broke. Every IF here uses goto-labels instead.
REM   2. NO HARDCODED ADD-LIST. v1's file list came from a stale GitHub web
REM      view. v2+ stages by category and tolerates missing paths.
REM
REM  v3 CHANGES, after the v2 live run of 2026-08-22:
REM   3. MERGE, NOT REBASE. v2's rebase aborted - correctly, protecting your
REM      data. One of your two local commits removed docs/analyst_notes.md
REM      from tracking (reorganised into analyst_notes_current.md + dated
REM      splices); rebuild_notes.py then regenerated it on disk as an
REM      UNTRACKED file, while origin still tracks the old copy. A rebase must
REM      check out origin's tree, which would overwrite your 666KB running
REM      record - so git refused. A MERGE touches only files that actually
REM      differ, which here is README.md alone, and never checks out origin's
REM      full tree. Rehearsed on a mock of exactly this shape: 1 file changed,
REM      record untouched on disk, push lands as a fast-forward.
REM   4. README HANDLING IS STATE-AWARE. v2 assumed README.md still carried
REM      local changes; v2's own run had already discarded them, so a re-run
REM      would have hit the "differs" stop for the wrong reason.
REM   5. REFUSES TO START MID-REBASE OR MID-MERGE.
REM
REM  JOB A ONLY. The history rewrite is JOB B, manual, in
REM  Repo_Catchup_Runbook_2026-08-21.txt.
REM ==========================================================================

cd /d "%~dp0"
set "FAIL="
echo.
echo ==========================================================================
echo   REPO CATCH-UP v3 - JOB A          %DATE% %TIME%
echo   %CD%
echo ==========================================================================

REM ---------------------------------------------------------------- PHASE 0
echo.
echo --- PHASE 0: SAFETY PRE-FLIGHT ------------------------------------------

where git >nul 2>&1
if errorlevel 1 set "FAIL=git is not on PATH" & goto :fail

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 set "FAIL=this folder is not a git repository" & goto :fail

if exist ".git\rebase-merge" goto :mid_operation
if exist ".git\rebase-apply" goto :mid_operation
if exist ".git\MERGE_HEAD"   goto :mid_operation

echo [0.1] No secret already tracked?
git ls-files > "%TEMP%\ceb_tracked.txt"
if errorlevel 1 set "FAIL=git ls-files failed" & goto :fail
findstr /I /C:"token.json" /C:".env" /C:"secret" /C:"credential" "%TEMP%\ceb_tracked.txt" >nul 2>&1
if not errorlevel 1 goto :secret_tracked
echo       ok.

echo [0.2] Index empty?
git diff --cached --quiet
if errorlevel 1 goto :index_dirty
echo       ok.

echo [0.3] Remote reachable?
git fetch origin
if errorlevel 1 set "FAIL=git fetch origin failed - fix credentials first" & goto :fail
echo       ok.

REM ------------------------------------------------------- PHASE 0.5 RECONCILE
echo.
echo --- PHASE 0.5: RECONCILE WITH ORIGIN ------------------------------------
git rev-list --count HEAD..origin/main > "%TEMP%\ceb_behind.txt" 2>nul
set "BEHIND=?"
if exist "%TEMP%\ceb_behind.txt" set /p BEHIND=<"%TEMP%\ceb_behind.txt"
echo       behind origin/main by: %BEHIND%
if "%BEHIND%"=="?" set "FAIL=could not determine distance from origin/main" & goto :fail
if "%BEHIND%"=="0" goto :reconciled

echo       Local is behind. origin carries 7f60462 - your README web upload.
git diff --quiet -- README.md
if not errorlevel 1 goto :readme_clean

echo       README.md has uncommitted changes; checking them against origin's.
git show origin/main:README.md > "%TEMP%\ceb_origin_readme.md" 2>nul
if errorlevel 1 set "FAIL=could not read README.md from origin/main" & goto :fail
fc /b README.md "%TEMP%\ceb_origin_readme.md" >nul 2>&1
if errorlevel 1 goto :readme_differs
echo       Byte-identical to origin's - discarding the redundant local copy.
git checkout -- README.md
if errorlevel 1 set "FAIL=git checkout -- README.md failed" & goto :fail

:readme_clean
echo.
echo       MERGING rather than rebasing. A rebase must check out origin's
echo       tree, which would overwrite your UNTRACKED docs\analyst_notes.md -
echo       the 666KB running record. That is exactly why v2 aborted. A merge
echo       touches only files that differ, which here is README.md alone.
echo.
echo       About to run:  git merge origin/main
echo       Ctrl+C to abort.
pause
git merge origin/main -m "Merge origin/main: README rewrite uploaded via the GitHub web UI"
if errorlevel 1 set "FAIL=merge failed - resolve by hand; your working tree is intact" & goto :fail
echo       merged.

:reconciled
git status -sb
echo.
echo   PHASE 0 PASSED.
pause

REM ---------------------------------------------------------------- PHASE 1
echo.
echo --- PHASE 1: .gitignore for generated exhibits and scratch --------------
findstr /C:"Generated review exhibits" .gitignore >nul 2>&1
if not errorlevel 1 goto :ignore_done
>>.gitignore echo.
>>.gitignore echo # Generated review exhibits - rewritten by the runners every session.
>>.gitignore echo # The numbers survive in docs/Phase3C_ClosingReview_*.md, which ARE tracked.
>>.gitignore echo band_price_*.md
>>.gitignore echo implied_return_*.md
>>.gitignore echo value_anchor_*.md
>>.gitignore echo signal_scan_*.md
>>.gitignore echo h1_lag_trace_*.md
>>.gitignore echo sweep_*.md
>>.gitignore echo monitor_strip.md
>>.gitignore echo near_miss_registry.md
>>.gitignore echo actionable_registry.md
>>.gitignore echo h4_dq_threshold_baseline.md
>>.gitignore echo quote_dump*.json
>>.gitignore echo fundamental_probe.json
>>.gitignore echo value_notes.html
>>.gitignore echo git_push_monitor.txt
echo       appended.
:ignore_done
git add .gitignore
git diff --cached --quiet
if not errorlevel 1 goto :p1_done
git commit -q -m "chore: ignore generated review exhibits and local scratch" -m "The runners rewrite these every session; tracking them churns the repo on every commit. Every figure they carry is quoted with [V] in the dated closing reviews under docs/, which remain tracked."
:p1_done

REM ---------------------------------------------------------------- PHASE 2
echo.
echo --- PHASE 2: retire Phase 3-A/3-B tooling to Retired\ --------------------
for %%F in (guardrail_trace.py run_weekly_review.bat t2.bat t2_check.py) do git add -A -- "%%F" >nul 2>&1
git add -A -- Retired >nul 2>&1
git diff --cached --quiet
if not errorlevel 1 goto :p2_done
git commit -q -m "refactor: move retired Phase 3-A/3-B tooling to Retired/" -m "guardrail_trace measured the Q1 confidence-band guardrail, retired at Q1-R close 2026-07-13; T3 now forbids band-ordering reliance. t2_check and t2.bat were the T2 tripwire sensors, retired with it. run_weekly_review.bat is superseded by run_daily_review.bat. Retained for archival reproducibility, not deleted."
:p2_done

REM ---------------------------------------------------------------- PHASE 3
echo.
echo --- PHASE 3: the Phase 3-C layer + docs ---------------------------------
for %%F in (band_price.py build_actionable_registry.py edgar_client.py edgar_parser_audit.py fundamental_probe.py implied_return.py log_tracker_crosscheck.py outcome_sanity.py phase_dispatch_audit.py quote_dump.py retired_criteria_audit.py signal_scan.py value_anchor.py xbrl_sweep.py run_daily_review.bat scan.bat value.bat) do git add -- "%%F" >nul 2>&1
git add -A -- docs >nul 2>&1
git diff --cached --quiet
if not errorlevel 1 goto :p3_done
git commit -q -m "feat: Phase 3-C - EDGAR context, valuation layer, integrity pass, audits" -m "edgar_client delivers Form 4, 8-K and the latest 10-Q/10-K narrative extract plus an XBRL statements block, as a prompt section that touches no gate and no confidence channel. value_anchor and implied_return are the forecast-free valuation layer, deliberately off-prompt per DP-V1. signal_scan, log_tracker_crosscheck and outcome_sanity are the daily integrity pass; edgar_parser_audit, phase_dispatch_audit and retired_criteria_audit are the pre-deploy audits. These files land already carrying their 2026-08-21 corrections - see docs/H1LagTrace_Truncation_Defect_2026-08-21.md. Advisory-only; no orders."
:p3_done

REM ---------------------------------------------------------------- PHASE 4
echo.
echo --- PHASE 4: instrument corrections -------------------------------------
for %%F in (README.md h1_lag_trace.py monitor_strip.py main.py risk_engine.py schwab_client.py) do git add -- "%%F" >nul 2>&1
git diff --cached --quiet
if not errorlevel 1 goto :p4_done
git commit -q -m "fix: instrument corrections carried into the tracked copies" -m "h1_lag_trace: conf_pct scaled a fraction and the display truncated with int(), so any confidence of 0.29, 0.57 or 0.58 rendered one point low - four wrong values on the GM exhibits. Display only; the lag verdicts and correlations were computed on the unrounded float and are unchanged. monitor_strip: the G1 rows now state which confidence channel scored the lag, operative and post-damping, and which trailing-move basis they use. risk_engine and main carry the DP-3C-o and era-derivation rulings."
:p4_done

REM ---------------------------------------------------------------- PHASE 5
echo.
echo --- PHASE 5: REVIEW BEFORE PUSH -----------------------------------------
git status
echo.
git log --oneline --graph -8
echo.
echo   Read the above. Anything unexpected staged, committed, or still
echo   untracked that should not be? Ctrl+C now - nothing has left this
echo   machine yet.
echo.
echo   NOTE: docs\analyst_notes.md - your 666KB running record - is being
echo   ADDED by Phase 3, replacing the old 191KB copy origin carries. It was
echo   scanned on 2026-08-22: no account numbers, no portfolio values, and its
echo   single "cost basis" mention DESCRIBES the prompt mechanism rather than
echo   disclosing a position. The only judgement call is one worked example
echo   citing a $6,000 position against $100,000 and $200,000 account sizes.
echo   If those round numbers are real rather than illustrative, Ctrl+C and
echo   redact that line before pushing.
pause

git push origin main
if errorlevel 1 set "FAIL=git push failed" & goto :fail

echo.
echo ==========================================================================
echo   JOB A COMPLETE.
echo.
echo   STILL EXPOSED - JOB B, manual, in Repo_Catchup_Runbook_2026-08-21.txt:
echo     tracker_with_registry.xlsx        Signals tab, accounts, outcomes
echo     Retired/near_miss_registry.xlsx   accounts, prices, confidences
echo   Both are tracked and public. JOB B force-pushes and cannot be undone.
echo ==========================================================================
pause
exit /b 0

:secret_tracked
echo.
echo   *** STOP CONDITION *** A credential-shaped file is ALREADY TRACKED:
findstr /I /C:"token.json" /C:".env" /C:"secret" /C:"credential" "%TEMP%\ceb_tracked.txt"
echo   Needs git rm --cached, a ROTATED Schwab token, and a history rewrite.
set "FAIL=secret already tracked"
goto :fail

:index_dirty
echo.
echo   *** STOP CONDITION *** Something is ALREADY STAGED. Every commit below
echo   would sweep it into a labelled commit it does not belong in.
git diff --cached --name-status
echo   Commit it yourself first, or run:  git reset
set "FAIL=index is not empty"
goto :fail

:readme_differs
echo.
echo   *** STOP CONDITION *** README.md has uncommitted changes that do NOT
echo   match origin's copy, so discarding them would lose work. Inspect:
echo       git diff origin/main -- README.md
set "FAIL=README.md diverged from origin"
goto :fail

:mid_operation
echo.
echo   *** STOP CONDITION *** A rebase or merge is already in progress.
echo   Finish or abort it before running this script:
echo       git rebase --abort      (or)      git merge --abort
set "FAIL=repository is mid-rebase or mid-merge"
goto :fail

:fail
echo.
echo ==========================================================================
echo   STOPPED: %FAIL%
echo   Nothing further was attempted.
echo ==========================================================================
pause
exit /b 1
