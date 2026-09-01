@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ===========================================================================
REM  cleanup_docs.bat  --  claude-equity-bot  --  OPTIONAL, run after step 1
REM ---------------------------------------------------------------------------
REM  WHY THIS IS SEPARATE
REM    Step 1 (cleanup_root.bat) touches only untracked / derived files. This
REM    script MOVES TRACKED DOCS, which git records as renames. It is safe --
REM    repo_catchup.bat stages docs with `git add -A -- docs`, so both sides of
REM    every rename are picked up -- but it is a repo-visible change, so it is
REM    opt-in and separate. Run it only when you are ready to commit renames.
REM
REM  WHAT IT DOES
REM    1. docs\ already has "Phase 2 docs\", "Phase 3-A docs\", "Phase 3-B docs\"
REM       but the ~24 Phase 3-C documents sit loose at docs\ root. This gives
REM       them "Phase 3-C docs\" and completes the convention.
REM    2. Retires superseded boot/kickoff prompts to prompts\Archived\.
REM
REM  WHAT IT DELIBERATELY LEAVES AT docs\ ROOT
REM    analyst_notes.md / analyst_notes_current.md / analyst_notes_2026-08-17.md
REM        -- the running record. repo_catchup.bat and rebuild_notes.py both
REM           depend on the current names and locations. DO NOT MOVE.
REM    rebuild_notes.py        -- resolves its default input relative to docs\
REM    Daily_Workflow_v7_1_Phase3C.docx -- current workflow; wanted at the top
REM    Phase4_Execution_Readiness_Register_v1.md -- forward-looking, not 3-C
REM    Examples.txt, commit_backlog_runbook_2026-08-10.txt -- cross-phase
REM
REM  USAGE
REM    cleanup_docs.bat          -> DRY RUN
REM    cleanup_docs.bat APPLY    -> performs the moves, writes an undo script
REM ===========================================================================

cd /d "%~dp0"
if not exist "signal_scan.py" goto :wrongdir
if not exist "docs\"          goto :wrongdir

set "DO=0"
if /i "%~1"=="APPLY" set "DO=1"

set "P3C=docs\Phase 3-C docs"
set "PARC=prompts\Archived"

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "LDT=%%I"
if not defined LDT set "LDT=00000000000000"
set "STAMP=%LDT:~0,8%_%LDT:~8,6%"
set "MANIFEST=cleanup_docs_manifest_%STAMP%.txt"
set "UNDO=undo_cleanup_docs_%STAMP%.bat"

set /a MOVED=0, MISSING=0, CONFLICT=0, FAILED=0

echo.
if "%DO%"=="1" (echo   MODE: APPLY   -- files will be moved) else (echo   MODE: DRY RUN -- nothing will be moved)
echo   Manifest: %MANIFEST%
echo.

>"%MANIFEST%" echo # claude-equity-bot docs regrouping -- %DATE% %TIME%
>>"%MANIFEST%" echo # mode: %DO% ^(1=APPLY, 0=DRY RUN^)
>>"%MANIFEST%" echo.

if "%DO%"=="1" (
  >"%UNDO%" echo @echo off
  >>"%UNDO%" echo setlocal EnableExtensions
  >>"%UNDO%" echo REM Reverses cleanup_docs.bat run %STAMP%. Run from the project root.
  >>"%UNDO%" echo cd /d "%%~dp0"
)

REM ===========================================================================
echo --- 1. Phase 3-C documents -^> %P3C% ---
>>"%MANIFEST%" echo == 1. Phase 3-C documents -^> %P3C%
REM  Snapshot the list before moving anything.
for /f "delims=" %%F in ('dir /b /a-d "docs\Phase3C_*.md" "docs\Phase3C_*.txt" "docs\Phase 3-C *E4 Endpoint*.md" 2^>nul') do call :arc "docs\%%F" "%P3C%"
for %%F in (
  "docs\DP-3C-j_Implementation_2026-08-20.md"
  "docs\E4_2_Volatility_Tier_Table_FROZEN_2026-08-10.md"
  "docs\EDGAR_GoLive_Runbook_2026-08-13.md"
  "docs\H1LagTrace_Truncation_Defect_2026-08-21.md"
  "docs\value_pass_exit_code_fix_2026-08-19.md"
  "docs\Repo_Catchup_Runbook_2026-08-21.txt"
) do call :arc "%%~F" "%P3C%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- 2. Superseded prompts -^> %PARC% ---
>>"%MANIFEST%" echo == 2. Superseded prompts -^> %PARC%
REM  Current and staying put: NEW_CHAT_BOOT_PROMPT_2026-08-05.md (newest boot
REM  prompt) and Phase3C_Kickoff_Prompt.md (the live phase).
for %%F in (
  "prompts\NEW_CHAT_BOOT_PROMPT.md"
  "prompts\NEW_CHAT_BOOT_PROMPT_2026-08-03.md"
  "prompts\Phase3A_Kickoff_Prompt.md"
  "prompts\Phase3B_Kickoff_Prompt.md"
  "prompts\1 I'm continuing work on my claude-eq.txt"
) do call :arc "%%~F" "%PARC%"
>>"%MANIFEST%" echo.

>>"%MANIFEST%" echo == SUMMARY
>>"%MANIFEST%" echo   moved/would move : %MOVED%
>>"%MANIFEST%" echo   not present      : %MISSING%
>>"%MANIFEST%" echo   name conflicts   : %CONFLICT%
>>"%MANIFEST%" echo   failures         : %FAILED%

echo.
echo   moved/would move : %MOVED%
echo   not present      : %MISSING%
echo   name conflicts   : %CONFLICT%
echo   failures         : %FAILED%
echo.
if "%DO%"=="0" (
  echo   DRY RUN only. Read %MANIFEST%, then re-run as:
  echo       cleanup_docs.bat APPLY
) else (
  echo   Done. Undo script: %UNDO%
  echo   Now commit the renames so repo_catchup.bat sees a clean tree:
  echo       git add -A -- docs prompts
  echo       git commit -m "chore: group Phase 3-C docs, retire superseded prompts"
)
echo.
endlocal
exit /b 0

REM ===========================================================================
:arc
set "SRC=%~1"
set "DST=%~2"
set "BASE=%~nx1"
if not exist "!SRC!" goto :arc_missing
if exist "!DST!\!BASE!" goto :arc_conflict
if "%DO%"=="0" goto :arc_log
if not exist "!DST!" mkdir "!DST!" 2>nul
move /Y "!SRC!" "!DST!\" >nul 2>&1
if errorlevel 1 goto :arc_fail
>>"%UNDO%" echo move /Y "!DST!\!BASE!" "!SRC!"
:arc_log
>>"%MANIFEST%" echo   [move ] !SRC!  -^>  !DST!\
set /a MOVED+=1
goto :eof
:arc_missing
>>"%MANIFEST%" echo   [none ] !SRC!  ^(not present^)
set /a MISSING+=1
goto :eof
:arc_conflict
>>"%MANIFEST%" echo   [CONF ] !SRC!  target already holds that name -- LEFT IN PLACE
set /a CONFLICT+=1
goto :eof
:arc_fail
>>"%MANIFEST%" echo   [FAIL ] !SRC!  ^(move failed -- file open?^)
set /a FAILED+=1
goto :eof

:wrongdir
echo.
echo   REFUSING TO RUN. Expected the claude-equity-bot root ^(signal_scan.py
echo   and docs\ beside this script^). Current directory: %CD%
echo.
endlocal
exit /b 1
