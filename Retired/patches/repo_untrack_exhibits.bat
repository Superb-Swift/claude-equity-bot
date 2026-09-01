@echo off
setlocal
REM ==========================================================================
REM  repo_untrack_exhibits.bat  -  2026-08-22
REM  Claude Equity Bot . repo Superb-Swift/claude-equity-bot
REM
REM  RUN THIS AFTER JOB A, BEFORE JOB B.
REM
REM  WHY IT EXISTS. JOB A appended exhibit patterns to .gitignore, and for the
REM  NEW dated exhibits that worked - none of band_price_2026-08-*,
REM  implied_return_2026-08-*, value_anchor_2026-08-* or the 8/17-8/21 scans
REM  were committed. But .gitignore DOES NOT UNTRACK. Twenty exhibit files
REM  were already tracked from earlier commits, so the new rules are INERT for
REM  them: they stay tracked and churn on every session forever.
REM
REM  This is the THIRD instance of that class in this repo - the same shape as
REM  tracker_with_registry.xlsx and Retired/near_miss_registry.xlsx. An ignore
REM  rule added after the fact only ever governs the future.
REM
REM  WHAT THIS DOES. git rm --cached only. Files stay on disk untouched; they
REM  simply stop being tracked from the next commit onward. History is NOT
REM  rewritten - that is JOB B, and only for the two spreadsheets.
REM ==========================================================================

cd /d "%~dp0"
set "FAIL="
echo.
echo ==========================================================================
echo   UNTRACK GENERATED EXHIBITS          %DATE% %TIME%
echo ==========================================================================

where git >nul 2>&1
if errorlevel 1 set "FAIL=git is not on PATH" & goto :fail
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 set "FAIL=not a git repository" & goto :fail
git diff --cached --quiet
if errorlevel 1 goto :index_dirty

echo.
echo --- what is about to STOP being tracked -----------------------------------
echo   20 generated exhibits, plus one exposed spreadsheet:
echo     actionable_registry.md          near_miss_registry.md
echo     monitor_strip.md                h4_dq_threshold_baseline.md
echo     h1_lag_trace_*.md   x6          signal_scan_2026-*.md  x9
echo     sweep_2026-08-11.md
echo     Retired/near_miss_registry.xlsx   ^<- account labels, prices, conf
echo.
echo   Every one stays ON DISK. Only the tracking stops.
echo   Ctrl+C to abort.
pause

for %%F in (actionable_registry.md monitor_strip.md near_miss_registry.md h4_dq_threshold_baseline.md sweep_2026-08-11.md) do git rm -q --cached --ignore-unmatch -- "%%F"
for %%F in (h1_lag_trace_GM.md h1_lag_trace_GM_3B.md h1_lag_trace_GM_raw_3B.md h1_lag_trace_WMT.md h1_lag_trace_WMT_3B.md h1_lag_trace_WMT_raw_3B.md) do git rm -q --cached --ignore-unmatch -- "%%F"
for %%F in (signal_scan_2026-07-30.md signal_scan_2026-07-31.md signal_scan_2026-08-03.md signal_scan_2026-08-05.md signal_scan_2026-08-06.md signal_scan_2026-08-07.md signal_scan_2026-08-12.md signal_scan_2026-08-13.md signal_scan_2026-08-14.md) do git rm -q --cached --ignore-unmatch -- "%%F"
git rm -q --cached --ignore-unmatch -- "Retired/near_miss_registry.xlsx"

echo.
echo --- adding near_miss_registry.xlsx to .gitignore --------------------------
findstr /C:"Retired/near_miss_registry.xlsx" .gitignore >nul 2>&1
if not errorlevel 1 goto :ignore_done
>>.gitignore echo.
>>.gitignore echo # Generated registry copy - carries account labels, prices and confidences.
>>.gitignore echo # Untracked 2026-08-22; its history is purged in JOB B.
>>.gitignore echo Retired/near_miss_registry.xlsx
echo       appended.
:ignore_done
git add .gitignore

echo.
echo --- REVIEW ----------------------------------------------------------------
git status --short
echo.
echo   Everything above should be "D " (deleted from the index) plus the
echo   .gitignore edit. Confirm the files still exist on disk.
echo   Ctrl+C to abort - nothing has left this machine yet.
pause

git commit -q -m "chore: untrack generated exhibits and the registry copy" -m "gitignore does not untrack. JOB A's exhibit patterns were inert for twenty files already tracked from earlier commits, and for Retired/near_miss_registry.xlsx. This is git rm --cached only: every file stays on disk and history is untouched. The registry copy's HISTORY is purged separately in JOB B, because it carries account labels, prices and confidences."
if errorlevel 1 set "FAIL=commit failed" & goto :fail
git push origin main
if errorlevel 1 set "FAIL=push failed" & goto :fail

echo.
echo ==========================================================================
echo   DONE. Verify the ignores now bite:
echo       git check-ignore -v monitor_strip.md
echo       git check-ignore -v Retired/near_miss_registry.xlsx
echo   Each must name a .gitignore line. Then run JOB B.
echo ==========================================================================
pause
exit /b 0

:index_dirty
echo.
echo   *** STOP *** Something is already staged; it would be swept into this
echo   commit. Commit it yourself first, or run: git reset
git diff --cached --name-status
set "FAIL=index is not empty"
goto :fail

:fail
echo.
echo ==========================================================================
echo   STOPPED: %FAIL%
echo ==========================================================================
pause
exit /b 1
