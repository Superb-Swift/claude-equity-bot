@echo off
setlocal
REM ==========================================================================
REM  repo_purge_history.bat  -  JOB B prep  -  2026-08-22
REM  Claude Equity Bot . repo Superb-Swift/claude-equity-bot
REM
REM  WHAT THIS DOES AND DELIBERATELY DOES NOT DO
REM    It installs git-filter-repo if missing, makes a FRESH CLONE in a
REM    sibling folder, purges the two spreadsheets from every commit, verifies
REM    the purge, restores the remote - and then STOPS and prints the single
REM    force-push command for you to paste yourself.
REM
REM    The force-push stays manual on purpose. Everything this script does is
REM    undoable by deleting the clone folder. The push is not.
REM
REM  WHY A FRESH CLONE MATTERS - THE REAL RISK IN THE COMMAND YOU TRIED
REM    You ran filter-repo inside C:\Users\rober\claude-equity-bot, your
REM    WORKING folder. filter-repo normally refuses that, but --force
REM    OVERRIDES the check. It would have rewritten your working repo in
REM    place and deleted its remote, leaving your day-to-day folder on an
REM    orphaned history. Recoverable, since origin still had everything, but
REM    an ugly hour. This script never touches your working folder.
REM
REM  ALSO: the command you typed ended with a bare "--path" and no value.
REM    Both paths are spelled out below so that cannot happen.
REM ==========================================================================

set "REPO=https://github.com/Superb-Swift/claude-equity-bot.git"
set "WORK=C:\Users\rober\ceb-rewrite"
set "FAIL="

echo.
echo ==========================================================================
echo   JOB B PREP - HISTORY PURGE          %DATE% %TIME%
echo ==========================================================================
echo.
echo   Purging from ALL history:
echo     tracker_with_registry.xlsx         4 commits
echo     Retired/near_miss_registry.xlsx    3 commits
echo.
echo   Both are already untracked going forward - commits 909bda7 and 560061e.
echo   This is only about the copies still reachable in history.
echo.

REM ---------------------------------------------------------------- step 1
echo --- 1. git-filter-repo present? -----------------------------------------
git filter-repo --version >nul 2>&1
if not errorlevel 1 goto :have_tool
echo       not installed. Installing into the active venv...
pip install git-filter-repo
if errorlevel 1 set "FAIL=pip install git-filter-repo failed" & goto :fail
git filter-repo --version >nul 2>&1
if errorlevel 1 set "FAIL=git-filter-repo installed but git still cannot find it - open a new shell with the venv active and re-run" & goto :fail
:have_tool
for /f "delims=" %%V in ('git filter-repo --version 2^>^&1') do echo       ok - filter-repo %%V

REM ---------------------------------------------------------------- step 2
echo.
echo --- 2. fresh clone at %WORK% --------------------
if not exist "%WORK%" goto :do_clone
echo       %WORK% already exists.
echo       It must be removed so the clone is genuinely fresh. Ctrl+C to keep it.
pause
rmdir /s /q "%WORK%"
:do_clone
git clone "%REPO%" "%WORK%"
if errorlevel 1 set "FAIL=clone failed" & goto :fail
cd /d "%WORK%"
echo       cloned.

REM ---------------------------------------------------------------- step 3
echo.
echo --- 3. confirm both files ARE in history before purging -----------------
git log --oneline --all -- tracker_with_registry.xlsx Retired/near_miss_registry.xlsx near_miss_registry.xlsx > "%TEMP%\ceb_hist.txt"
for /f %%C in ('find /c /v "" ^< "%TEMP%\ceb_hist.txt"') do set "NHIST=%%C"
echo       commits touching them: %NHIST%
if "%NHIST%"=="0" set "FAIL=neither file appears in history - nothing to purge, do NOT force-push" & goto :fail
type "%TEMP%\ceb_hist.txt"

REM ---------------------------------------------------------------- step 4
echo.
echo --- 4. PURGE ------------------------------------------------------------
echo       Still fully undoable - delete %WORK% and nothing happened.
pause
git filter-repo --path tracker_with_registry.xlsx --path Retired/near_miss_registry.xlsx --path near_miss_registry.xlsx --invert-paths --force
if errorlevel 1 set "FAIL=filter-repo failed" & goto :fail

REM ---------------------------------------------------------------- step 5
echo.
echo --- 5. VERIFY the purge BEFORE anything is pushed -----------------------
git log --oneline --all -- tracker_with_registry.xlsx Retired/near_miss_registry.xlsx near_miss_registry.xlsx > "%TEMP%\ceb_after.txt"
for /f %%C in ('find /c /v "" ^< "%TEMP%\ceb_after.txt"') do set "NAFTER=%%C"
echo       commits still touching them: %NAFTER%   (must be 0)
if not "%NAFTER%"=="0" set "FAIL=purge did not take - do NOT push" & goto :fail
git rev-list --objects --all | findstr /I "tracker_with_registry near_miss_registry.xlsx" >nul 2>&1
if not errorlevel 1 set "FAIL=blob references remain - do NOT push" & goto :fail
echo       ok - zero commits, zero reachable blobs.
echo.
echo       commits survive with new SHAs:
git log --oneline -6

REM ---------------------------------------------------------------- step 6
echo.
echo --- 6. restore the remote -----------------------------------------------
echo       filter-repo removes it on purpose, as a safety measure.
git remote add origin "%REPO%"
if errorlevel 1 echo       (remote already present - continuing)
git remote -v

echo.
echo ==========================================================================
echo   PREP COMPLETE. NOTHING HAS BEEN PUSHED.
echo.
echo   Run these TWO commands yourself, from %WORK%:
echo.
echo       git push origin --force --all
echo       git push origin --force --tags
echo.
echo   THEN, to re-point your working folder at the rewritten history:
echo       cd C:\Users\rober\claude-equity-bot
echo       git status                  ^<- must be clean first
echo       git fetch origin
echo       git reset --hard origin/main
echo.
echo   THEN verify on GitHub that neither .xlsx resolves, and open a Support
echo   request asking them to garbage-collect unreachable objects - a
echo   force-push alone does not purge GitHub's cached views.
echo.
echo   FINALLY: rmdir /s /q %WORK%
echo ==========================================================================
pause
exit /b 0

:fail
echo.
echo ==========================================================================
echo   STOPPED: %FAIL%
echo   Nothing was pushed. Your working folder was never touched.
echo ==========================================================================
pause
exit /b 1
