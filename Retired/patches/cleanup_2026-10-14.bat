@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ===========================================================================
REM  cleanup_2026-10-14.bat  --  claude-equity-bot  --  root and folder tidy
REM ---------------------------------------------------------------------------
REM  Supersedes cleanup_root.bat and cleanup_docs.bat (2026-09-01 / 09-17),
REM  whose fixed file lists are spent. Same design: a DRY RUN by default, a
REM  manifest of every action, and an undo script for every move.
REM
REM  WHAT IT DOES (Rob's choices, 2026-10-14)
REM    A. Dated exhibits older than the three newest sessions -> exhibits\archive
REM    B. Source backups (*.bak, *.bak-*)                     -> Retired\patches\backups
REM    C. DELETES three pieces of junk (APPLY only, NOT undoable):
REM         ~$tracker_with_registry.xlsx  stale Excel lock file from 2026-08-04
REM         "h origin main"               a git log printed to a file on 09-17
REM         __pycache__\                  Python rebuilds it on the next run
REM    D. Spent one-off scripts (tracked in git)              -> Retired\patches
REM    E. logs\ : the 09-14 console transcript -> logs\Retired; 09-17 Step 9:
REM         rename the logs\Retired file that shadows the live master's name,
REM         and move the byte-identical duplicate tracker (hash-checked here)
REM    F. docs\ : superseded / spent docs -> docs\Archived; loose Phase 3-C
REM         docs -> docs\Phase 3-C docs; the duplicate 08-27 closing review
REM         (hash-checked here) -> Retired\patches\backups
REM    G. .gitignore: add e4_counter.md (regenerated daily, not yet ignored)
REM
REM  WHAT IT DELIBERATELY DOES NOT TOUCH
REM    Any .py module or live runner; .env; token.json; signal_state.json;
REM    the live master and its two newest backups; the current exhibits;
REM    docs\analyst_notes*.md and docs\note splices\ (G6 location still open);
REM    edgar_cache\ (DP-3C-ai freeze); October logs (they move at month end);
REM    venv\; Claude outputs\.
REM
REM  USAGE (close Excel first)
REM    cleanup_2026-10-14.bat          -> DRY RUN. Writes a manifest, changes nothing.
REM    cleanup_2026-10-14.bat APPLY    -> Performs it and writes undo_cleanup_STAMP.bat
REM
REM  Advisory-only - no orders - not financial advice.
REM ===========================================================================

cd /d "%~dp0"

if not exist "signal_scan.py" goto :wrongdir
if not exist "main.py"        goto :wrongdir
if not exist ".gitignore"     goto :wrongdir

set "DO=0"
if /i "%~1"=="APPLY" set "DO=1"

REM ---- Excel must be closed: a live lock file must never be deleted, and an
REM      open workbook cannot be moved.
set "XL=0"
tasklist /fi "imagename eq EXCEL.EXE" 2>nul | find /i "EXCEL.EXE" >nul && set "XL=1"
if "%XL%"=="1" if "%DO%"=="1" (
  echo.
  echo   REFUSING TO APPLY: Excel is running. Save and close every workbook,
  echo   then run again. ^(A dry run is still allowed.^)
  echo.
  exit /b 1
)

set "KEEP_MD=2026-10-12 2026-10-13 2026-10-14"
set "KEEP_QD=20261012 20261013"

set "EXH=exhibits\archive"
set "PAT=Retired\patches"
set "BAK=Retired\patches\backups"
set "LOGRET=logs\Retired"
set "DOCARC=docs\Archived"
set "P3C=docs\Phase 3-C docs"

set "STAMP="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"`) do set "STAMP=%%I"
if not defined STAMP (
  echo   FATAL: could not resolve a run stamp. Refusing to run unstamped.
  exit /b 1
)
set "MANIFEST=cleanup_manifest_%STAMP%.txt"
set "UNDO=undo_cleanup_%STAMP%.bat"

set /a MOVED=0, KEPT=0, MISSING=0, CONFLICT=0, FAILED=0, DELETED=0

echo.
if "%DO%"=="1" (echo   MODE: APPLY   -- files will be moved, three junk items deleted) else (echo   MODE: DRY RUN -- nothing will be changed)
if "%XL%"=="1" echo   NOTE: Excel is running. Close it before APPLY.
echo   Manifest: %MANIFEST%
echo.

>"%MANIFEST%" echo # claude-equity-bot cleanup 2026-10-14 -- run %STAMP%
>>"%MANIFEST%" echo # mode: %DO% ^(1=APPLY, 0=DRY RUN^)
>>"%MANIFEST%" echo # keep dates: %KEEP_MD% ^| %KEEP_QD%
>>"%MANIFEST%" echo.

if "%DO%"=="1" (
  >"%UNDO%" echo @echo off
  >>"%UNDO%" echo setlocal EnableExtensions
  >>"%UNDO%" echo REM Reverses cleanup_2026-10-14.bat run %STAMP%. Run from the project root.
  >>"%UNDO%" echo REM The three deletions in section C cannot be undone.
  >>"%UNDO%" echo cd /d "%%~dp0"
)

REM ===========================================================================
echo --- A. Dated review exhibits -^> %EXH% ---
>>"%MANIFEST%" echo == A. Dated review exhibits -^> %EXH%
for /f "delims=" %%F in ('dir /b /a-d band_price_*.md implied_return_*.md value_anchor_*.md signal_scan_*.md sweep_*.md 2^>nul') do call :sift_md "%%F"
for /f "delims=" %%F in ('dir /b /a-d quote_dump_*.json 2^>nul') do call :sift_qd "%%F"
REM  Two stale one-off exhibits: value_notes.html (byte-identical to the copy
REM  already in docs\Archived; no runner writes it) and fundamental_probe.json.
call :arc "value_notes.html" "%EXH%"
call :arc "fundamental_probe.json" "%EXH%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- B. Source backups -^> %BAK% ---
>>"%MANIFEST%" echo == B. Source backups -^> %BAK%
for /f "delims=" %%F in ('dir /b /a-d *.bak *.bak-* 2^>nul') do call :arc "%%F" "%BAK%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- C. Junk: deleted on APPLY, not undoable ---
>>"%MANIFEST%" echo == C. Junk -- DELETED on APPLY ^(Rob, 2026-10-14^), not undoable
call :del_file "~$tracker_with_registry.xlsx"
call :del_file "h origin main"
call :del_dir "__pycache__"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- D. Spent one-off scripts -^> %PAT% ---
>>"%MANIFEST%" echo == D. Spent one-off scripts -^> %PAT%  ^(tracked: git records renames^)
call :arc "repo_catchup.bat" "%PAT%"
call :arc "repo_purge_history.bat" "%PAT%"
call :arc "cleanup_root.bat" "%PAT%"
call :arc "cleanup_docs.bat" "%PAT%"
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- E. logs ---
>>"%MANIFEST%" echo == E. logs
call :arc "logs\Windows PowerShell 2026-09-14.txt" "%LOGRET%"
REM  09-17 Step 9: this file carries the live master's name inside logs\Retired.
call :ren "logs\Retired\claude_equity_bot_tracker.xlsx" "logs\Retired\claude_equity_bot_tracker_backup_pre-2026-09-16-cleanup.xlsx"
REM  09-17 Step 9: move tracker.xlsx ONLY if it is byte-identical to its twin.
call :dup "logs\Retired\tracker.xlsx" "logs\Retired\claude_equity_bot_tracker 1.xlsx" "%BAK%\tracker_DUPLICATE_2026-09-09.xlsx"
>>"%MANIFEST%" echo   [keep ] logs\claude_equity_bot_tracker.xlsx  ^(LIVE MASTER^)
>>"%MANIFEST%" echo   [keep ] logs\claude_equity_bot_tracker_backup_*.xlsx  ^(newest restore points^)
>>"%MANIFEST%" echo   [keep ] logs\signals_2026-10-*.log  ^(October: moves at month end^)
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- F. docs ---
>>"%MANIFEST%" echo == F1. Superseded or spent docs -^> %DOCARC%
call :arc "docs\Daily_Workflow_v6_0_Phase3C.docx" "%DOCARC%"
call :arc "docs\Daily_Workflow_v7_1_Phase3C.docx" "%DOCARC%"
call :arc "docs\commit_backlog_runbook_2026-08-10.txt" "%DOCARC%"
call :arc "docs\Examples.txt" "%DOCARC%"
call :arc "docs\Repo_Cleanup_Runbook_2026-09-01.md" "%DOCARC%"
call :arc "docs\Repo_Review_2026-09-14.md" "%DOCARC%"
call :arc "docs\remediation_2026-09-14.md" "%DOCARC%"
REM  The v1_2 pre-registration (superseded by v1.3) has an em dash in its name,
REM  which cmd cannot type reliably. PowerShell finds it by wildcard.
call :arc_emdash
>>"%MANIFEST%" echo.
>>"%MANIFEST%" echo == F2. Loose Phase 3-C docs -^> %P3C%
call :arc "docs\Phase3C_ClosingReview_2026-09-01.md" "%P3C%"
call :arc "docs\Phase3C_ClosingReview_2026-09-02.md" "%P3C%"
call :arc "docs\Phase3C_Exit_and_Phase4_Standing_2026-09-02.md" "%P3C%"
call :arc "docs\Phase3C_Rulings_2026-09-03.md" "%P3C%"
call :arc "docs\OutcomeCells_Repair_2026-09-03.md" "%P3C%"
call :arc "docs\Implementation_Record_DP-T1_2026-09-16.md" "%P3C%"
call :arc "docs\Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md" "%P3C%"
call :arc "docs\Discovery_IC_2026-09-16.png" "%P3C%"
>>"%MANIFEST%" echo.
>>"%MANIFEST%" echo == F3. Duplicate 08-27 closing review ^(hash-checked^)
call :dup "docs\Phase3C_ClosingReview_2026-08-27.md" "%P3C%\Phase3C_ClosingReview_2026-08-27.md" "%BAK%\Phase3C_ClosingReview_2026-08-27_DUPLICATE.md"
>>"%MANIFEST%" echo   [keep ] docs\analyst_notes*.md, docs\note splices\, docs\rebuild_notes.py  ^(G6 location open^)
>>"%MANIFEST%" echo   [keep ] docs\Daily_Workflow_v8_0_Phase3C.docx, docs\Phase4_Execution_Readiness_Register_v1.md
>>"%MANIFEST%" echo.

REM ===========================================================================
echo --- G. .gitignore ---
>>"%MANIFEST%" echo == G. .gitignore
findstr /x /c:"e4_counter.md" ".gitignore" >nul 2>&1
if not errorlevel 1 (
  >>"%MANIFEST%" echo   [skip ] .gitignore already ignores e4_counter.md
  goto :gi_done
)
if "%DO%"=="1" (
  if not exist "%BAK%" mkdir "%BAK%" 2>nul
  copy /Y ".gitignore" "%BAK%\gitignore_%STAMP%.orig" >nul
  >>".gitignore" echo # E4 exit counter exhibit, rewritten by run_daily_review.bat ^(2026-10-14^)
  >>".gitignore" echo e4_counter.md
  >>"%UNDO%" echo copy /Y "%BAK%\gitignore_%STAMP%.orig" ".gitignore"
)
>>"%MANIFEST%" echo   [edit ] .gitignore  +e4_counter.md  ^(original kept as %BAK%\gitignore_%STAMP%.orig^)
:gi_done
>>"%MANIFEST%" echo.

REM ===========================================================================
if "%DO%"=="1" >>"%UNDO%" echo echo Undo complete. Re-check with: git status
>>"%MANIFEST%" echo == SUMMARY
>>"%MANIFEST%" echo   moved/would move : %MOVED%
>>"%MANIFEST%" echo   deleted/would del: %DELETED%
>>"%MANIFEST%" echo   kept in place    : %KEPT%
>>"%MANIFEST%" echo   not present      : %MISSING%
>>"%MANIFEST%" echo   name conflicts   : %CONFLICT%
>>"%MANIFEST%" echo   failures         : %FAILED%

echo.
echo   moved/would move : %MOVED%
echo   deleted/would del: %DELETED%
echo   kept in place    : %KEPT%
echo   not present      : %MISSING%
echo   name conflicts   : %CONFLICT%
echo   failures         : %FAILED%
echo.
if "%DO%"=="0" (
  echo   DRY RUN only. Read %MANIFEST%, then re-run as:
  echo       cleanup_2026-10-14.bat APPLY
) else (
  echo   Done. Undo script: %UNDO%
  echo   Next: selftest.bat, then the git steps in the 2026-10-14 cleanup runbook.
)
echo.
set "RCX=0"
if !FAILED! GTR 0 set "RCX=1"
endlocal & exit /b %RCX%

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
REM  %1 = source file, %2 = destination directory
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
>>"%MANIFEST%" echo   [CONF ] !SRC!  -^> !DST!\ already holds that name -- LEFT IN PLACE
set /a CONFLICT+=1
goto :eof
:arc_fail
>>"%MANIFEST%" echo   [FAIL ] !SRC!  ^(move failed -- file open or locked?^)
set /a FAILED+=1
goto :eof

:ren
REM  %1 = source file, %2 = full destination path (new name)
set "SRC=%~1"
set "DSTF=%~2"
if not exist "!SRC!" goto :arc_missing
if exist "!DSTF!" (
  >>"%MANIFEST%" echo   [CONF ] !SRC!  -^> !DSTF! already exists -- LEFT IN PLACE
  set /a CONFLICT+=1
  goto :eof
)
if "%DO%"=="0" goto :ren_log
move /Y "!SRC!" "!DSTF!" >nul 2>&1
if errorlevel 1 goto :arc_fail
>>"%UNDO%" echo move /Y "!DSTF!" "!SRC!"
:ren_log
>>"%MANIFEST%" echo   [rename] !SRC!  -^>  !DSTF!
set /a MOVED+=1
goto :eof

:dup
REM  %1 = candidate duplicate, %2 = the copy that stays, %3 = full destination
REM  Moves %1 to %3 ONLY if the two files hash identically (SHA-256).
set "SRC=%~1"
set "TWIN=%~2"
set "DSTF=%~3"
if not exist "!SRC!" goto :arc_missing
if not exist "!TWIN!" (
  >>"%MANIFEST%" echo   [keep ] !SRC!  ^(its twin !TWIN! is missing -- not a duplicate^)
  set /a KEPT+=1
  goto :eof
)
call :hash "!SRC!" H1
call :hash "!TWIN!" H2
if not defined H1 goto :dup_differ
if not "!H1!"=="!H2!" goto :dup_differ
>>"%MANIFEST%" echo   [hash ] SHA-256 identical: !SRC!  =  !TWIN!
call :ren "!SRC!" "!DSTF!"
goto :eof
:dup_differ
>>"%MANIFEST%" echo   [keep ] !SRC!  ^(differs from !TWIN! -- NOT moved^)
set /a KEPT+=1
goto :eof

:hash
REM  %1 = file, %2 = variable to receive the SHA-256 line
set "%~2="
for /f "skip=1 delims=" %%H in ('certutil -hashfile "%~1" SHA256 2^>nul') do if not defined %~2 set "%~2=%%H"
goto :eof

:arc_emdash
REM  docs\Phase 3-C (em dash) E4 Endpoint Pre-Registration v1_2.md -> docs\Archived
set "EMPAT=Phase 3-C*E4 Endpoint Pre-Registration v1_2.md"
powershell -NoProfile -Command "$f = Get-ChildItem -LiteralPath 'docs' -File | Where-Object { $_.Name -like '%EMPAT%' }; if (-not $f) { exit 2 }; if (Test-Path -LiteralPath (Join-Path 'docs\Archived' $f.Name)) { exit 3 }; if ($env:DO -eq '1') { Move-Item -LiteralPath $f.FullName -Destination 'docs\Archived\' -ErrorAction Stop }; exit 0"
set "RC=!errorlevel!"
if "!RC!"=="2" (
  >>"%MANIFEST%" echo   [none ] docs\%EMPAT%  ^(not present^)
  set /a MISSING+=1
  goto :eof
)
if "!RC!"=="3" (
  >>"%MANIFEST%" echo   [CONF ] docs\%EMPAT%  -^> docs\Archived\ already holds that name -- LEFT IN PLACE
  set /a CONFLICT+=1
  goto :eof
)
if not "!RC!"=="0" (
  >>"%MANIFEST%" echo   [FAIL ] docs\%EMPAT%  ^(move failed^)
  set /a FAILED+=1
  goto :eof
)
if "%DO%"=="1" >>"%UNDO%" echo powershell -NoProfile -Command "Get-ChildItem -LiteralPath 'docs\Archived' -File | Where-Object { $_.Name -like '%EMPAT%' } | Move-Item -Destination 'docs\'"
>>"%MANIFEST%" echo   [move ] docs\%EMPAT%  -^>  docs\Archived\
set /a MOVED+=1
goto :eof

:del_file
REM  %1 = file. Deleted on APPLY only; /a also matches hidden lock files.
set "SRC=%~1"
if not exist "!SRC!" goto :arc_missing
if "%DO%"=="1" del /f /q /a "!SRC!" >nul 2>&1
if "%DO%"=="1" if exist "!SRC!" goto :del_fail
>>"%MANIFEST%" echo   [del  ] !SRC!
set /a DELETED+=1
goto :eof
:del_fail
>>"%MANIFEST%" echo   [FAIL ] !SRC!  ^(delete failed -- in use?^)
set /a FAILED+=1
goto :eof

:del_dir
REM  %1 = folder. Removed on APPLY only.
set "SRC=%~1"
if not exist "!SRC!\" goto :arc_missing
if "%DO%"=="1" rmdir /s /q "!SRC!" >nul 2>&1
if "%DO%"=="1" if exist "!SRC!\" goto :del_fail
>>"%MANIFEST%" echo   [del  ] !SRC!\
set /a DELETED+=1
goto :eof

:wrongdir
echo.
echo   REFUSING TO RUN. This does not look like the claude-equity-bot root
echo   ^(expected main.py, signal_scan.py and .gitignore beside this script^).
echo   Current directory: %CD%
echo.
endlocal
exit /b 1
