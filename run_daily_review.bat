@echo off
REM ===========================================================================
REM run_daily_review.bat  —  standing analysis pass, READ-ONLY on the master
REM ===========================================================================
REM SUPERSEDES run_weekly_review.bat (cadence changed to DAILY 2026-07-27).
REM
REM PURPOSE:
REM   Runs the standing monitors: the H1 lag tracers (WMT + GM, full-series
REM   AND the WS2 post-deploy two-channel acceptance slices), the H4 DQ
REM   watchdog, the near-miss registry, the actionable-directional registry,
REM   and the open-questions monitor strip.
REM   None of these touch the bot or place orders; they only READ the master
REM   tracker. The registry tab and the monitor strip are written into a COPY
REM   (tracker_with_registry.xlsx) — the master is never modified.
REM
REM RETIRED 2026-07-27 — guardrail_trace.py is OUT of this runner. Q1-R closed
REM   the guardrail question (50-59 vs 60-69); the guardrail and T2 were both
REM   retired. Removing it also retires the 'Guardrail Trace' sheet, the 'Live
REM   Cohort Scoreboard' sheet and regime_stratification.md — all three were
REM   written by that one tool and all three answered the closed question.
REM   monitor_strip.py drops the two stale sheets from the COPY on every run.
REM   Population monitoring survives as the weekly band chart on the strip,
REM   labelled context-only. The .py stays in the repo for the record; it is
REM   simply no longer part of the cadence.
REM
REM WHY DAILY:
REM   The monitor strip is a daily-glance artifact, and the embedded sheet is
REM   only honest if it is regenerated on the same cadence as the strip. A
REM   weekly embed goes stale mid-week while still LOOKING authoritative
REM   (7/17 sheet sitting in a workbook whose Signals tab ran to 7/24 is what
REM   prompted the change). Run this after the daily signal run.
REM
REM ANALYST NOTE (cadence discipline): running daily does NOT mean reading
REM   daily. The G1/G2 criteria are TABLE reads at their stated n; a one-
REM   session move in any of these numbers is noise. The strip exists so the
REM   state is always CURRENT, not so it is checked for drama.
REM
REM USAGE (from the project root):
REM     C:\Users\rober\claude-equity-bot> run_daily_review.bat
REM
REM ANALYST NOTE:
REM   The master lives in logs\, but every tool defaults to the bare filename,
REM   so we pass --tracker explicitly. Markdown exhibits + the refreshed
REM   tracker_with_registry.xlsx land in the project root (override with
REM   --out-dir on any single tool). A tool erroring prints and continues; the
REM   others still run.
REM
REM AMENDED 2026-10-09: two additions, neither touching what the model sees.
REM   * e4_counter.py - the Phase 3-C exit criteria COUNTED on their
REM     pre-registered definitions (E4-2 resolved ADJACENT rows, E4-3
REM     observable 8-K events, the clock). Counts only; never a read
REM     (DP-3C-ay). E4-2 crossed 150 on 2026-10-01 and nothing said so.
REM   * review_artifacts.py - checks that THIS run wrote every exhibit and
REM     sheet, prints WRITTEN / STALE / ABSENT, and sets the exit code.
REM     Same lesson as value.bat's 2026-08-19 guard: an exit code is a
REM     claim; the artifact is the evidence. Exit 0 = complete, 1 = not.
REM
REM AMENDED 2026-10-22 (DP-3C-ba): chain_check.py runs FIRST and WARNS when
REM   the evening chain is out of order: no scan for today, blank closes on a
REM   settled session (enter_closes did not run), no value.bat for the previous
REM   session, or a report copy never refreshed in Excel (step 7). It must run
REM   before the copy is rebuilt, which erases the evidence for the last one.
REM   The 10-19 and 10-20 breaks would each have printed a WARN here.
REM
REM ORDERING CONSTRAINT (do not reorder the last two blocks):
REM   build_near_miss_registry.py --emit-master-copy REBUILDS
REM   tracker_with_registry.xlsx from the master. Any sheet embedded before
REM   that step is destroyed. Registry regen -> strip embed. Always.
REM ===========================================================================

setlocal

REM ---- Force UTF-8 for file I/O + stdout (prevents cp1252 UnicodeEncodeError on Windows) ----
set PYTHONUTF8=1
set TRACKER=logs\claude_equity_bot_tracker.xlsx
set REPORT=tracker_with_registry.xlsx

REM ANALYST NOTE (WS2): first live AM under era A-S1D1. Edit ONLY if go-live
REM slips past 2026-07-07. Drives the post-deploy acceptance slices below.
set WS2_DEPLOY=2026-07-07

call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Could not activate venv.
    exit /b 1
)

REM Run start time, for review_artifacts.py (added 2026-10-09).
for /f %%t in ('python -c "import time;print(int(time.time()))"') do set "T0=%%t"

echo.
echo ============ Chain check - did tonight's chain run in order? ============
REM ADDED 2026-10-22 (DP-3C-ba). It never stops the review; a warning makes
REM the review's exit code non-zero (folded in at the end).
python chain_check.py --tracker "%TRACKER%" --report "%REPORT%"
set "CHAIN_RC=%ERRORLEVEL%"

REM ---- Ensure openpyxl + matplotlib + Pillow are present. openpyxl: registry ----
REM ---- + both embeds. matplotlib: the trace chart and the strip cards.       ----
REM ---- Pillow: image embedding AND the strip's no-squish resample.           ----
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
REM AMENDED 2026-09-16: the glob below is resolved RECURSIVELY by
REM signal_logs.discover() (since 2026-09-08), so the month subfolders are
REM read too; logs that predate confidence_raw simply contribute nothing.
python h1_lag_trace.py --tracker "%TRACKER%" --ticker WMT --since %WS2_DEPLOY% --suffix _3B
python h1_lag_trace.py --tracker "%TRACKER%" --ticker GM --since %WS2_DEPLOY% --suffix _3B
python h1_lag_trace.py --tracker "%TRACKER%" --ticker WMT --since %WS2_DEPLOY% --raw-from-logs "logs\signals_*.log" --suffix _raw_3B
python h1_lag_trace.py --tracker "%TRACKER%" --ticker GM --since %WS2_DEPLOY% --raw-from-logs "logs\signals_*.log" --suffix _raw_3B

echo.
echo ========== H4 - DQ watchdog (PROMOTED, monitoring only) ==========
python h4_dq_threshold.py --tracker "%TRACKER%"

echo.
echo ===================== Near-miss registry ========================
REM --emit-master-copy REBUILDS the report copy from the master. This is the
REM step that resets tracker_with_registry.xlsx, so the strip embed below
REM must follow it - never precede it.
python build_near_miss_registry.py --tracker "%TRACKER%" --emit-master-copy

echo.
echo ================ Actionable directional registry ================
REM RULED 2026-08-13. Mirror of the near-miss registry: directional signals that
REM CLEARED CHECK 5 at their OWN gate (BUY >=70%%, SELL >=65%%) rather than failing
REM it. Read-only on the master; embeds into the report copy.
REM
REM ORDERING: this MUST follow build_near_miss_registry.py --emit-master-copy
REM (which rebuilds the copy and would destroy this sheet) and MUST precede the
REM strip embed. The tool refuses to embed if the copy is absent - exit 3.
python build_actionable_registry.py --tracker "%TRACKER%" --emit-into-copy --copy "%REPORT%"

echo.
echo =============== Monitor strip - open questions ==================
REM Reads the master for the data and the top-level logs for the blend
REM channel, then embeds a refreshed 'Monitor Strip' sheet (as-of line +
REM auditable table + WS2 episode ledger + strip image) into the report copy,
REM parked after 'Cohort Analysis'. The image is resampled to its embed
REM width first, so Excel renders it at 100% - no squish. --theme dark
REM styles the whole sheet to match the image and hides gridlines. This step
REM also drops the retired 'Guardrail Trace' / 'Live Cohort Scoreboard' tabs
REM from the copy; if that notice prints EVERY run, the master still has them.
python monitor_strip.py --tracker "%TRACKER%" --logs "logs\signals_*.log" --embed-into "%REPORT%" --theme dark
echo   STEP 7: open %REPORT% in Excel, let it recalculate, save and close.
echo   Tomorrow's chain_check fails if this is skipped.

echo.
echo ========= Prospective arms - counts only (DP-3C-ah) ==========
REM ADDED 2026-09-16. PR-1/PR-2/PR-3 read HOLD rows on signal dates after the
REM discovery cutoff (2026-09-16). Before each arm's read date this prints
REM n only - never an IC - so nobody looks early. PR-4 is report-only.
python discovery_scan.py --tracker "%TRACKER%" --progress
python shadow_damper.py --tracker "%TRACKER%" --progress

echo.
echo ========== E4 exit counter - counts only (DP-3C-ay) ==========
REM ADDED 2026-10-09. E4-2 resolved ADJACENT rows, E4-3 observable 8-K events
REM and the clock, on their pre-registered definitions. Reads no return,
REM breach or confidence value. Check: python e4_counter.py --reproduce-0902
python e4_counter.py --tracker "%TRACKER%" --md e4_counter.md

echo.
echo ============= Review artifacts - written by THIS run? =============
python review_artifacts.py --t0 %T0%
set "RC=%ERRORLEVEL%"
REM 2026-10-22: a chain_check warning makes the review exit 1 (never 0).
if not "%CHAIN_RC%"=="0" if "%RC%"=="0" (
    echo   chain_check reported the chain out of order - exit code set to 1.
    set "RC=1"
)

echo.
echo ============================================================
echo   Daily review complete. Read the questions on the 'Monitor Strip'
echo   tab or in monitor_strip.md. STANDING, read from rulings.py - the
echo   footer is no longer hardcoded (DP-3C-al, 2026-09-16):
python rulings.py --standing
echo.
echo   These are TABLE reads at their stated n. A one-session move in
echo   any of them is noise - the strip exists to stay CURRENT, not
echo   to be checked for drama. Prospective arms (DP-3C-w, PR-1..PR-3)
echo   print counts only until their read date: python discovery_scan.py --progress
echo   Advisory-only - no orders - not financial advice (DP-T1).
echo ============================================================
endlocal & exit /b %RC%
