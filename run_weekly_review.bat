@echo off
REM ===========================================================================
REM run_weekly_review.bat  —  periodic (weekly) analysis, READ-ONLY on tracker
REM ===========================================================================
REM PURPOSE:
REM   Runs the four hypothesis harnesses and regenerates the near-miss
REM   registry in one go. None of these touch the bot or place orders; they
REM   only read the tracker, and each prints the 50-59% calibration guardrail.
REM
REM   This is NOT part of the daily routine — run it weekly (or after a
REM   meaningful batch of new outcomes) during the reflection step.
REM
REM USAGE (from the project root):
REM     C:\Users\rober\claude-equity-bot> run_weekly_review.bat
REM
REM ANALYST NOTE:
REM   The tracker lives in logs\, but every tool defaults to the bare
REM   filename, so we pass --tracker explicitly. Markdown exhibits land in
REM   the project root (override with --out-dir on any single tool). A tool
REM   erroring prints and continues; the others still run.
REM ===========================================================================

setlocal

REM ---- Force UTF-8 for file I/O + stdout (prevents cp1252 UnicodeEncodeError on Windows) ----
set PYTHONUTF8=1
set TRACKER=logs\claude_equity_bot_tracker.xlsx

call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Could not activate venv.
    exit /b 1
)

REM ---- Ensure openpyxl is present (the harnesses + registry need it) ----
python -c "import openpyxl" 2>nul || (
    echo openpyxl not found - installing into the active venv...
    python -m pip install openpyxl
)

echo.
echo ===================== H1 - update lag (WMT) =====================
python h1_lag_trace.py --tracker "%TRACKER%" --ticker WMT

echo.
echo ===================== H3 - thesis stability =====================
python h3_thesis_stability.py --tracker "%TRACKER%"

echo.
echo ============== H2 - direction asymmetry (baseline) ==============
python h2_direction_asymmetry.py --tracker "%TRACKER%"
echo   (after an A/B stretch: python h2_direction_asymmetry.py --logs "logs\signals_*.log")

echo.
echo ================== H4 - DQ watchdog (demoted) ===================
python h4_dq_threshold.py --tracker "%TRACKER%"

echo.
echo ===================== Near-miss registry ========================
python build_near_miss_registry.py --tracker "%TRACKER%"

echo.
echo ============================================================
echo   Weekly review complete. Re-check: does 50-59%% still lead?
echo ============================================================
endlocal
