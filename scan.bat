@echo off
REM ============================================================================
REM  scan.bat - daily signal scan + log/master cross-check + outcome guard
REM  Claude Equity Bot - Phase 3-C - advisory-only - no orders
REM
REM  RUN THIS AFTER THE PASTE. The cross-check compares the log against rows in
REM  logs\claude_equity_bot_tracker.xlsx, so the master must already carry today.
REM  outcome_sanity reads the MANUAL outcome columns H/I/J, so it likewise needs
REM  today's resolutions already entered. Ordering is binding (ruled 2026-08-12).
REM
REM  Usage:  scan.bat                 (uses today's date)
REM          scan.bat 2026-07-30      (explicit date)
REM
REM  Exit 0 = clean. Exit 1 = findings. Exit 2 = could not run.
REM  None of the three tools writes to any workbook. All are formula-cache immune.
REM ============================================================================
setlocal

call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: could not activate venv
    exit /b 2
)

set "RUNDATE=%~1"
if "%RUNDATE%"=="" (
    for /f %%d in ('python -c "import datetime;print(datetime.date.today().isoformat())"') do set "RUNDATE=%%d"
)

set "LOGFILE=logs\signals_%RUNDATE%.log"
set "MASTER=logs\claude_equity_bot_tracker.xlsx"

if not exist "%LOGFILE%" (
    echo ERROR: no log for %RUNDATE% at %LOGFILE%
    echo        NYSE holiday? No log is produced and there is nothing to scan.
    exit /b 2
)

set "RC=0"

echo.
echo ### signal_scan - %RUNDATE%
python signal_scan.py --log "%LOGFILE%" --md "signal_scan_%RUNDATE%.md"
if errorlevel 1 set "RC=1"

echo.
echo ### log/master cross-check - %RUNDATE%
python log_tracker_crosscheck.py --log "%LOGFILE%" --tracker "%MASTER%"
if errorlevel 1 set "RC=1"

echo.
echo ### outcome sanity - manual-entry outcome columns
python outcome_sanity.py --tracker "%MASTER%"
if errorlevel 2 (
    echo   NOTE: outcome_sanity could not run. It must be given the MASTER,
    echo         never tracker_with_registry.xlsx. NOTHING was checked.
    set "RC=2"
) else if errorlevel 1 (
    set "RC=1"
)

echo.
echo ============================================================================
if "%RC%"=="0" (
    echo SCAN CLEAN - no integrity, reconciliation, outcome or cross-check findings.
) else if "%RC%"=="2" (
    echo SCAN INCOMPLETE - a step could not run. Nothing above is a clean result.
) else (
    echo SCAN FINDINGS - review the blocks above before splicing the notes.
)
echo Advisory-only - no orders - not financial advice.
echo ============================================================================

exit /b %RC%
