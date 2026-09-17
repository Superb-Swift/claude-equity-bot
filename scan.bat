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
REM  None of the tools writes to any workbook. All are formula-cache immune.
REM
REM  AMENDED 2026-08-26: two checks added so nobody has to remember them.
REM    * trading_calendar --selftest    - the NYSE session calendar, reconciled
REM      against the master. Gates: a calendar that disagrees with the record
REM      makes every horizon mapping below it untrustworthy.
REM    * trail_basis_audit              - measures the H1 trailing window.
REM      REPORTS ONLY. It is expected to find the known open window defect
REM      (H1_Window_OffByOne_Defect_2026-08-26.md) and must not turn the scan
REM      red every day for an item awaiting a ruling.
REM  outcome_sanity now also carries Check F (log-close reconciliation), which
REM  likewise reports without gating. No new commands to run.
REM
REM  AMENDED 2026-09-16 (DP-T1, DP-3C-ag, DP-3C-aj):
REM    * advisory_guard - DP-T1 made mechanical. GATES: any order-placing code,
REM      or REQUIRE_HUMAN_APPROVAL not True, turns the scan red.
REM    * outcome_sanity Check G - a close entered for a session that has not
REM      settled GATES (80 such cells passed silently on 2026-09-16).
REM    * trail_basis_audit now GATES. The window fix was applied 2026-08-31;
REM      D1 logs are history, and a D2 log on the shifted window is a regression.
REM    * Enter outcome closes with enter_closes.py BEFORE this scan (see the
REM      daily workflow v8.0). It refuses unsettled sessions.
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
    REM Distinguish "market was shut" from "the bot did not run", which are not
    REM the same fact and used to print the same message.
    python -c "import datetime,sys;sys.path.insert(0,'.');import trading_calendar as c;d=datetime.date.fromisoformat('%RUNDATE%');print('        NOT AN NYSE SESSION (weekend or holiday) - nothing to scan.') if not c.is_trading_day(d) else (print('        PRE-REGISTERED NO-RUN SESSION: '+c.BOT_ABSENT[d][0]) or print('        See '+c.BOT_ABSENT[d][1]+'. The market traded; the bot did not.') if d in c.BOT_ABSENT else print('        Market was OPEN and no log exists. That is a MISSED RUN, not a holiday.'))" 2>nul
    exit /b 2
)

set "RC=0"

echo.
echo ### trading calendar - selftest and reconciliation vs the master
python trading_calendar.py --selftest --tracker "%MASTER%"
if errorlevel 1 (
    echo   STOP: the session calendar disagrees with the record. Every horizon
    echo         mapping below this line is untrustworthy until that is resolved.
    set "RC=1"
)

echo.
echo ### signal_scan - %RUNDATE%
python signal_scan.py --log "%LOGFILE%" --md "signal_scan_%RUNDATE%.md"
if errorlevel 1 set "RC=1"

echo.
echo ### log/master cross-check - %RUNDATE%
python log_tracker_crosscheck.py --log "%LOGFILE%" --tracker "%MASTER%"
if errorlevel 1 set "RC=1"

echo.
echo ### outcome sanity - manual outcome columns, + Check F (log-close reconcile)
python outcome_sanity.py --tracker "%MASTER%"
if errorlevel 2 (
    echo   NOTE: outcome_sanity could not run. It must be given the MASTER,
    echo         never tracker_with_registry.xlsx. NOTHING was checked.
    set "RC=2"
) else if errorlevel 1 (
    set "RC=1"
)

echo.
echo ### H1 trailing-window audit - regression gate since the 2026-08-31 fix
python trail_basis_audit.py --tracker "%MASTER%" >nul 2>&1
if errorlevel 2 (
    echo   NOTE: trail_basis_audit could not run. Detail: python trail_basis_audit.py
    set "RC=2"
) else if errorlevel 1 (
    echo   REGRESSION: a D2 log spans the shifted window, or its alignment could
    echo   not be determined. Detail: python trail_basis_audit.py
    echo   Diagnosis: H1_Window_OffByOne_Defect_2026-08-26.md
    set "RC=1"
) else (
    echo   Every D2 log spans the window its label claims. D1 logs are history.
)

echo.
echo ### advisory guard - DP-T1: this system never places an order
python advisory_guard.py --quiet
if errorlevel 1 set "RC=1"

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
