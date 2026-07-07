@echo off
REM ===========================================================================
REM run_daily.bat
REM ===========================================================================
REM PURPOSE:
REM   One-shot daily runner for the Claude Equity Bot.
REM   Chains: venv activation -> bot run -> log analyzer -> tracker parser
REM
REM USAGE:
REM   Double-click or run from any cmd.exe in the project root:
REM     C:\Users\rober\claude-equity-bot> run_daily.bat
REM
REM   To skip the tracker parsing step (if you only want bot + analyzer):
REM     C:\Users\rober\claude-equity-bot> run_daily.bat --no-parse
REM
REM   PM runs are DIAGNOSTIC-ONLY (the AM 9:30 CST run is canonical). A PM
REM   run overwrites today's signal_state.json entries and paste_today.tsv -
REM   do NOT paste PM rows, and re-seed the state afterwards:
REM     python seed_signal_state.py --tracker tracker_with_registry.xlsx
REM   (A/B program terminated at the 3-A closeout; run_ab_test.bat retired.)
REM
REM ANALYST NOTE:
REM   This is a thin orchestration layer, not new logic. Each underlying
REM   tool is still independently runnable. If any step fails, the script
REM   exits early with a non-zero code so you know what to investigate.
REM   The --no-parse flag exists because backfill days won't have a
REM   matching signals_TODAY.log to parse.
REM
REM   Phase / generator era are controlled in main.py (PHASE = "3-B"; era
REM   "A-S1D1" = the H1/H3 prompt blocks + S1 prior-signal state input + D1
REM   confidence damping). main.py maintains signal_state.json automatically
REM   on every run. This runner stays phase-agnostic and does not need to
REM   change when the phase advances.
REM ===========================================================================

setlocal enabledelayedexpansion

REM ---- Force UTF-8 for file I/O + stdout (prevents cp1252 UnicodeEncodeError on Windows) ----
set PYTHONUTF8=1

REM ---- Get today's date in YYYY-MM-DD format via PowerShell ----
REM (Native cmd date formatting is locale-dependent; PowerShell is reliable.)
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%a

echo.
echo ============================================================
echo   Claude Equity Bot - Daily Run - %TODAY%
echo ============================================================
echo.

REM ---- Step 1: Activate venv ----
echo [1/4] Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Could not activate venv. Is venv\Scripts\activate.bat present?
    exit /b 1
)

REM ---- Step 2: Run the bot ----
echo.
echo [2/4] Running bot (main.py)...
if not exist "signal_state.json" (
    echo WARN: signal_state.json not found - the S1 prior-signal input runs
    echo       cold today. To warm it from the tracker first, run:
    echo         python seed_signal_state.py --tracker tracker_with_registry.xlsx
)
echo ------------------------------------------------------------
python main.py
if errorlevel 1 (
    echo.
    echo ERROR: main.py failed. Check the error above.
    exit /b 1
)

REM ---- Step 3: Run the log analyzer ----
echo.
echo [3/4] Running analyzer (analyze_log.py)...
echo ------------------------------------------------------------
python analyze_log.py
if errorlevel 1 (
    echo.
    echo ERROR: analyze_log.py failed. Check the error above.
    exit /b 1
)

REM ---- Step 4 (optional): Parse log into tracker-paste TSV ----
if "%1"=="--no-parse" goto :skip_parse

echo.
echo [4/4] Generating tracker paste-ready rows...
echo ------------------------------------------------------------
if not exist "logs\signals_%TODAY%.log" (
    echo WARN: No log file found at logs\signals_%TODAY%.log
    echo       Skipping parser step. Maybe markets are closed today?
    goto :done
)
python parse_log_to_tracker.py logs\signals_%TODAY%.log -o paste_today.tsv
if errorlevel 1 (
    echo.
    echo WARN: Parser failed - non-fatal. Bot run and analyzer succeeded.
    goto :done
)
echo.
echo Tracker-paste rows written to: paste_today.tsv

:skip_parse
:done
echo.
echo ============================================================
echo   Done.
echo   Today's log:       logs\signals_%TODAY%.log
echo   Summary appended:  logs\summary_history.txt
echo   S1 state updated:  signal_state.json (raw-conf chain, last 5 per ticker)
if exist "paste_today.tsv" (
    echo   Paste into tracker: paste_today.tsv
)
echo ============================================================
echo.

endlocal
