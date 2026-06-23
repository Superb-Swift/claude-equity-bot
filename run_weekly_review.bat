@echo off
REM ===========================================================================
REM run_weekly_review.bat  —  periodic (weekly) analysis, READ-ONLY on tracker
REM ===========================================================================
REM PURPOSE:
REM   Runs the four hypothesis harnesses, regenerates the near-miss registry,
REM   and refreshes the guardrail-compression trace in one go. None of these
REM   touch the bot or place orders; they only READ the original tracker. The
REM   registry tab and the trace chart are written into a COPY
REM   (tracker_with_registry.xlsx) — the original is never modified — and the
REM   harnesses print the 50-59% calibration guardrail.
REM
REM   This is NOT part of the daily routine — run it weekly (or after a
REM   meaningful batch of new outcomes) during the reflection step.
REM
REM USAGE (from the project root):
REM     C:\Users\rober\claude-equity-bot> run_weekly_review.bat
REM
REM ANALYST NOTE:
REM   The tracker lives in logs\, but every tool defaults to the bare
REM   filename, so we pass --tracker explicitly. Markdown exhibits + the
REM   refreshed tracker_with_registry.xlsx land in the project root (override
REM   with --out-dir on any single tool). A tool erroring prints and
REM   continues; the others still run.
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

REM ---- Ensure openpyxl + Pillow are present (registry needs openpyxl; the ----
REM ---- guardrail-trace embed needs matplotlib + Pillow for the chart image) ----
python -c "import openpyxl, matplotlib, PIL" 2>nul || (
    echo dependencies missing - installing into the active venv...
    python -m pip install openpyxl matplotlib pillow
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
REM --emit-master-copy regenerates the Near-Miss tab inside a COPY
REM (tracker_with_registry.xlsx); the original tracker is never touched.
python build_near_miss_registry.py --tracker "%TRACKER%" --emit-master-copy

echo.
echo ================= Guardrail compression trace ===================
REM Reads the original tracker (cached outcomes) for the trajectory, then
REM embeds a refreshed 'Guardrail Trace' sheet (table + chart) into the
REM registry copy from the step above, producing one tracker_with_registry.xlsx
REM that carries both the refreshed registry and the chart.
python guardrail_trace.py --tracker "%TRACKER%" --embed-into tracker_with_registry.xlsx
echo   (open tracker_with_registry.xlsx in Excel to refresh the formula cache)

echo.
echo ============================================================
echo   Weekly review complete. Re-check: does 50-59%% still lead?
echo ============================================================
endlocal
