@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ===========================================================================
REM  cleanup_root.bat  --  claude-equity-bot  --  ARCHIVE-ONLY root tidy
REM ---------------------------------------------------------------------------
REM  WHAT IT DOES
REM    Moves stale / superseded / derived files out of the project root into
REM    dated archive folders. NOTHING IS EVER DELETED. Every action is a move,
REM    every move is logged, and every move is reversed by the undo script this
REM    run writes for you.
REM
REM  WHAT IT DELIBERATELY DOES NOT TOUCH
REM    - Any .py module, any .bat runner, .env, token.json, requirements.txt,
REM      README.md, LICENSE, .gitignore
REM    - signal_state.json, the live tracker, the current registries
REM    - The three most recent dates of every exhibit family (KEEP_MD below)
REM    - docs\analyst_notes*.md  (the running record; repo_catchup.bat and
REM      rebuild_notes.py both depend on the current naming)
REM    - repo_purge_history.bat  (JOB B may still be pending -- see runbook)
REM
REM  USAGE
REM    cleanup_root.bat          -> DRY RUN. Writes a manifest, changes nothing.
REM    cleanup_root.bat APPLY    -> Performs the moves and writes undo_cleanup.bat
REM
REM  RE-RUNNABLE. Roll KEEP_MD / KEEP_QD forward and run it again next month.
REM ===========================================================================

cd /d "%~dp0"

REM ---- guard: refuse to run anywhere that is not the project root -----------
if not exist "signal_scan.py" goto :wrongdir
if not exist "main.py"        goto :wrongdir
if not exist ".gitignore"     goto :wrongdir

REM ---- mode ----------------------------------------------------------------
set "DO=0"
if /i "%~1"=="APPLY" set "DO=1"

REM ---- which exhibit dates stay in the root ---------------------------------
REM  .md exhibits use 2026-08-24 style; quote_dump uses 20260824 style.
set "KEEP_MD=2026-08-24 2026-08-25 2026-08-26"
set "KEEP_QD=20260824 20260825"

REM ---- destinations --------------------------------------------------------
set "EXH=exhibits\archive"
set "PAT=Retired\patches"
set "BAK=Retired\patches\backups"
set "LOGRET=logs\Retired"
set "DOCARC=docs\Archived"

REM ---- run stamp -----------------------------------------------------------
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "LDT=%%I"
if not defined LDT set "LDT=00000000000000"
set "STAMP=%LDT:~0,8%_%LDT:~8,6%"
set "MANIFEST=cleanup_manifest_%STAMP%.txt"
set "UNDO=undo_cleanup_%STAMP%.bat"

set /a MOVED=0, KEPT=0, MISSING=0, CONFLICT=0, FAILED=0

echo.
if "%DO%"=="1" (echo   MODE: APPLY   -- files will be moved) else (echo   MODE: DRY RUN -- nothing will be moved)
echo   Manifest: %MANIFEST%
echo.

>"%MANIFEST%" echo # claude-equity-bot root cleanup -- %DATE% %TIME%
>>"%MANIFEST%" echo # mode: %DO% ^(1=APPLY, 0=DRY RUN^)
>>"%MANIFEST%" echo # keep dates: %KEEP_MD% ^| %KEEP_QD%
>>"%MANIFEST%" echo.

if "%DO%"=="1" (
  >"%UNDO%" echo @echo off
  >>"%UNDO%" echo setlocal EnableExtensions
  >>"%UNDO%" echo REM Reverses cleanup_root.bat run %STAMP%. Run from the project root.
  >>"%UNDO%" echo cd /d "%%~dp0"
)

REM ===========================================================================
echo --- A. Dated review exhibits -^> %EXH% ---
>>"%MANIFEST%" echo == A. Dated review exhibits -^> %EXH%
REM  dir /b snapshots the list first -- a plain wildcard FOR is unreliable while
REM  the loop body is moving the very files being enumerated.
for /f "delims=" %%F in ('dir /b /a-d band_price_*.md implied_return_*.md value_anchor_*.md signal_scan_*.md sweep_*.md 2^>nul') do call :sift_md "%%F"
for /f "delims=" %%F in ('dir /b /a-d quote_dump_*.json 2^>nul') do call :sift_qd "%%F"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- B. One-off defect / repair scripts -^> %PAT% ---
>>"%MANIFEST%" echo == B. One-off defect / repair scripts -^> %PAT%
for %%F in (
  apply_dow_fix.py
  apply_h1_trace_fixes.py
  apply_h1_window_ruling.py
  apply_outcome_sanity_fixes.py
  apply_repair_calendar_fix.py
  propose_h1_window_fix.py
  test_dow_fix.py
  dow_fix.diff
  repo_untrack_exhibits.bat
  git_push_monitor.txt
) do call :arc "%%F" "%PAT%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- C. Source backups and Office lock files -^> %BAK% ---
>>"%MANIFEST%" echo == C. Source backups and Office lock files -^> %BAK%
for /f "delims=" %%F in ('dir /b /a-d *.bak *.bak-* 2^>nul') do call :arc "%%F" "%BAK%"
for /f "delims=" %%F in ('dir /b /a-d "~$*.xlsx" "~$*.docx" 2^>nul') do call :arc "%%F" "%BAK%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- D. Superseded tracker backups -^> %LOGRET% ---
>>"%MANIFEST%" echo == D. Superseded tracker backups -^> %LOGRET%
REM  The newest backup stays in logs\ for a fast restore; older ones retire.
call :arc "logs\claude_equity_bot_tracker_backup_2026-08-26_162552.xlsx" "%LOGRET%"
call :arc "logs\claude_equity_bot_tracker_backup_pre-2026-08-26-fix.xlsx" "%LOGRET%"
>>"%MANIFEST%" echo   [keep ] logs\claude_equity_bot_tracker_backup_2026-08-31_172930.xlsx  ^(newest restore point^)
>>"%MANIFEST%" echo   [keep ] logs\claude_equity_bot_tracker.xlsx  ^(LIVE MASTER^)
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- E. Superseded workflow docs -^> %DOCARC% ---
>>"%MANIFEST%" echo == E. Superseded workflow docs -^> %DOCARC%
REM  v7_1 is current; v6_0 and v7_0 retire. The docs\ copy of value_notes.html
REM  duplicates the root copy the runners rewrite. The .txt register is the
REM  pre-conversion paste of Phase4_Execution_Readiness_Register_v1.md.
call :arc "docs\Daily_Workflow_v6_0_Phase3C.docx" "%DOCARC%"
call :arc "docs\Daily_Workflow_v7_0_Phase3C.docx" "%DOCARC%"
call :arc "docs\value_notes.html" "%DOCARC%"
call :arc "docs\Phase4 execution readiness register v1.txt" "%DOCARC%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- F. Orphaned "Phase 3A Files" folder -^> %DOCARC% ---
>>"%MANIFEST%" echo == F. Orphaned "Phase 3A Files" folder -^> %DOCARC%
REM  Root-level duplicate of the docs\Phase 3-A docs\ convention. Moves whole.
call :arcdir "Phase 3A Files" "%DOCARC%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- G. .gitignore: keep backups out of the tracked Retired\ tree ---
>>"%MANIFEST%" echo == G. .gitignore hardening
REM  repo_catchup.bat runs `git add -A -- Retired`, so anything archived under
REM  Retired\ gets committed. edgar_client.py.bak alone is 147 KB of churn.
findstr /x /c:"*.bak" ".gitignore" >nul 2>&1
if not errorlevel 1 goto :gi_done
if "%DO%"=="1" (
  >>".gitignore" echo.
  >>".gitignore" echo # Source backups produced by the patch scripts. Kept on disk under
  >>".gitignore" echo # Retired\patches\backups\ for reproducibility; git already has the history.
  >>".gitignore" echo *.bak
  >>".gitignore" echo *.bak-*
)
>>"%MANIFEST%" echo   [edit ] .gitignore  +*.bak  +*.bak-*
:gi_done
>>"%MANIFEST%" echo.

REM ===========================================================================
if "%DO%"=="1" >>"%UNDO%" echo echo Undo complete. Re-check with: git status
>>"%MANIFEST%" echo == SUMMARY
>>"%MANIFEST%" echo   moved/would move : %MOVED%
>>"%MANIFEST%" echo   kept in place    : %KEPT%
>>"%MANIFEST%" echo   not present      : %MISSING%
>>"%MANIFEST%" echo   name conflicts   : %CONFLICT%
>>"%MANIFEST%" echo   failures         : %FAILED%

echo.
echo   moved/would move : %MOVED%
echo   kept in place    : %KEPT%
echo   not present      : %MISSING%
echo   name conflicts   : %CONFLICT%
echo   failures         : %FAILED%
echo.
if "%DO%"=="0" (
  echo   DRY RUN only. Read %MANIFEST%, then re-run as:
  echo       cleanup_root.bat APPLY
) else (
  echo   Done. Undo script: %UNDO%
  echo   Next: git status    then    git add -A    and commit the renames.
)
echo.
endlocal
exit /b 0

REM ===========================================================================
REM  SUBROUTINES
REM ===========================================================================

:sift_md
set "F=%~nx1"
set "HIT="
for %%K in (%KEEP_MD%) do if not "!F:%%K=!"=="!F!" set "HIT=1"
if defined HIT goto :sift_keep
call :arc "!F!" "%EXH%"
goto :eof

:sift_qd
set "F=%~nx1"
set "HIT="
for %%K in (%KEEP_QD%) do if not "!F:%%K=!"=="!F!" set "HIT=1"
if defined HIT goto :sift_keep
call :arc "!F!" "%EXH%"
goto :eof

:sift_keep
>>"%MANIFEST%" echo   [keep ] !F!
set /a KEPT+=1
goto :eof

:arc
REM  %1 = source path (file), %2 = destination directory
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
>>"%MANIFEST%" echo   [CONF ] !SRC!  ^-^> !DST!\ already holds that name -- LEFT IN PLACE
set /a CONFLICT+=1
goto :eof
:arc_fail
>>"%MANIFEST%" echo   [FAIL ] !SRC!  ^(move failed -- file open or locked?^)
set /a FAILED+=1
goto :eof

:arcdir
REM  %1 = source directory, %2 = destination parent directory
set "SRC=%~1"
set "DST=%~2"
if not exist "!SRC!\" goto :dir_missing
if exist "!DST!\!SRC!\" goto :dir_conflict
if "%DO%"=="0" goto :dir_log
if not exist "!DST!" mkdir "!DST!" 2>nul
move /Y "!SRC!" "!DST!\" >nul 2>&1
if errorlevel 1 goto :dir_fail
>>"%UNDO%" echo move /Y "!DST!\!SRC!" "!SRC!"
:dir_log
>>"%MANIFEST%" echo   [movedir] !SRC!\  -^>  !DST!\
set /a MOVED+=1
goto :eof
:dir_missing
>>"%MANIFEST%" echo   [none ] !SRC!\  ^(not present^)
set /a MISSING+=1
goto :eof
:dir_conflict
>>"%MANIFEST%" echo   [CONF ] !SRC!\  ^-^> !DST!\ already holds that folder -- LEFT IN PLACE
set /a CONFLICT+=1
goto :eof
:dir_fail
>>"%MANIFEST%" echo   [FAIL ] !SRC!\  ^(move failed^)
set /a FAILED+=1
goto :eof

:wrongdir
echo.
echo   REFUSING TO RUN. This does not look like the claude-equity-bot root
echo   ^(expected main.py, signal_scan.py and .gitignore beside this script^).
echo   Current directory: %CD%
echo.
endlocal
exit /b 1
