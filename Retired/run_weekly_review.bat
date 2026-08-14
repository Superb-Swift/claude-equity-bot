@echo off
REM ===========================================================================
REM run_weekly_review.bat  —  periodic (weekly) analysis, READ-ONLY on tracker
REM ===========================================================================
REM PURPOSE:
REM   Runs the standing monitors: the H1 lag tracers (WMT + GM, full-series
REM   AND the WS2 post-deploy two-channel acceptance slices), the H4 DQ
REM   watchdog, the near-miss registry, and the guardrail/scoreboard trace
REM   with regime stratification (the T2 tripwire sensors). None of these
REM   touch the bot or place orders; they only READ the original tracker. The
REM   registry tab and the trace chart are written into a COPY
REM   (tracker_with_registry.xlsx) — the original is never modified — and the
REM   harnesses still print the 50-59% band table, MONITOR ONLY: the Q1
REM   guardrail is SUSPENDED as a decision input (T3). Watch the T2 tripwire
REM   instead (see the closing banner).
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

REM ANALYST NOTE (WS2): first live AM under era A-S1D1. Edit ONLY if go-live
REM slips past 2026-07-07. Drives the post-deploy acceptance slices below.
set WS2_DEPLOY=2026-07-07

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
echo ============== H1 - update lag tracers (full series) ==============
python h1_lag_trace.py --tracker "%TRACKER%" --ticker WMT
python h1_lag_trace.py --tracker "%TRACKER%" --ticker GM

echo.
echo ======== H1 - WS2 acceptance slices (post-deploy, 2-channel) ======
REM Operative channel (tracker conf = damped) and RAW channel (model-side,
REM recovered from the Signal JSON log lines) for both tracers. The RAW
REM table read is the Lever-B verdict input. ANALYST NOTE: the corr-scan is
REM confirmatory only at n at/past ~8-10 - the 3-A baseline slice already
REM reads lag 1 (WS2_Deploy_Notes.md, 4b) - the TABLE read is the criterion.
REM Only top-level logs\signals_*.log are scanned: May/June logs are boxed
REM in subfolders and predate confidence_raw anyway.
python h1_lag_trace.py --tracker "%TRACKER%" --ticker WMT --since %WS2_DEPLOY% --suffix _3B
python h1_lag_trace.py --tracker "%TRACKER%" --ticker GM --since %WS2_DEPLOY% --suffix _3B
python h1_lag_trace.py --tracker "%TRACKER%" --ticker WMT --since %WS2_DEPLOY% --raw-from-logs "logs\signals_*.log" --suffix _raw_3B
python h1_lag_trace.py --tracker "%TRACKER%" --ticker GM --since %WS2_DEPLOY% --raw-from-logs "logs\signals_*.log" --suffix _raw_3B

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
REM --stratify-regime also refreshes regime_stratification.md - the
REM non-compressed 50-59 vs 60-69 lead that feeds T2's second condition.
python guardrail_trace.py --tracker "%TRACKER%" --embed-into tracker_with_registry.xlsx --stratify-regime
echo   (open tracker_with_registry.xlsx in Excel to refresh the formula cache)

echo.
echo ============================================================
echo   Weekly review complete. T2 TRIPWIRE CHECK - Q1-R re-open:
echo     1. Pooled live 60-69 n at or past 88?   Live Cohort Scoreboard
echo     2. Non-compressed lead at/below -15pt?  regime_stratification.md
echo   BOTH true = T2 FIRES: run the Phase-2-vs-live prompt+distribution
echo   diff - Tier-2E kit - before further design work. The Q1 guardrail
echo   remains SUSPENDED as a decision input (T3).
echo ============================================================
endlocal
