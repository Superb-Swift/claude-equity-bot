@echo off
REM ===========================================================================
REM t2.bat  —  five-second T2 tripwire read (Q1-R re-open gate)
REM ===========================================================================
REM PURPOSE:
REM   Activates the venv (where openpyxl lives) and runs t2_check.py against
REM   the tracker. One command, every session, answers the only open T2
REM   question: are BOTH gates met? (depth n >= 88 AND non-compressed lead
REM   <= -15pt). Reads the Signals tab only; returns are computed from the
REM   Price columns, so a stale/empty Return-column formula cache is fine.
REM
REM USAGE (from the project root):
REM     C:\Users\rober\claude-equity-bot> t2.bat
REM     C:\Users\rober\claude-equity-bot> t2.bat --history
REM   ( %* passes any flags straight through to t2_check.py. )
REM
REM ANALYST NOTE:
REM   The activate step is the whole point — running t2_check.py with the
REM   system Python fails on ModuleNotFoundError: openpyxl. Mirrors the venv
REM   handling in run_daily.bat / run_weekly_review.bat. Exit code from
REM   t2_check.py: 10 = BOTH gates met (T2 fires); 0 = not fired. This bat
REM   surfaces a FIRE banner on 10 so it can't be missed.
REM ===========================================================================

setlocal
set PYTHONUTF8=1
set TRACKER=tracker_with_registry.xlsx

call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Could not activate venv. Is venv\Scripts\activate.bat present?
    exit /b 1
)

REM ---- Prefer the root tracker (Guardrail Trace + Scoreboard); fall back to logs\ ----
if not exist "%TRACKER%" (
    if exist "logs\claude_equity_bot_tracker.xlsx" (
        set TRACKER=logs\claude_equity_bot_tracker.xlsx
    ) else (
        echo ERROR: no tracker found ^(tried %TRACKER% and logs\claude_equity_bot_tracker.xlsx^).
        exit /b 1
    )
)

python t2_check.py --tracker "%TRACKER%" %*
set RC=%ERRORLEVEL%

REM ---- errorlevel 10 = both gates met. Shout. ----
if %RC% GEQ 10 (
    echo.
    echo ============================================================
    echo   *** T2 FIRED — both gates met. Pull the Tier-2E kit and
    echo       run the Phase-2-vs-live prompt + distribution diff. ***
    echo ============================================================
)

endlocal
exit /b %RC%
