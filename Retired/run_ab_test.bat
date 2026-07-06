@echo off
REM ===========================================================================
REM run_ab_test.bat  —  run ONE day in H2 A/B mode (both prompt arms)
REM ===========================================================================
REM PURPOSE:
REM   Sets EQUITY_AB_TEST=1 so main.py scores every ticker under BOTH prompt
REM   variants on identical inputs, then reuses the normal daily chain:
REM       variant A = control (current H1 + H3 build)
REM       variant B = control + the H2 symmetric-framing addendum
REM
REM   The control (A) arm still feeds the tracker exactly as on a normal day
REM   (parse_log_to_tracker.py skips variant B via its prompt_variant guard),
REM   so calibration continuity is preserved. The B arm is logged for:
REM       python h2_direction_asymmetry.py --logs "logs\signals_*.log"
REM
REM USAGE (from the project root):
REM     C:\Users\rober\claude-equity-bot> run_ab_test.bat
REM     C:\Users\rober\claude-equity-bot> run_ab_test.bat --no-parse
REM
REM ANALYST NOTE:
REM   ~2x Anthropic token cost (two calls per ticker), so use this only for
REM   A/B sessions, then return to run_daily.bat. setlocal/endlocal scope the
REM   EQUITY_AB_TEST flag to this script, so it can never leak into a later
REM   run_daily.bat in the same window. The toggle is read in main.py as
REM   AB_TEST = os.environ.get("EQUITY_AB_TEST", "0") == "1".
REM ===========================================================================

setlocal

REM ---- Force UTF-8 for file I/O + stdout (prevents cp1252 UnicodeEncodeError on Windows) ----
set PYTHONUTF8=1
echo.
echo ************************************************************
echo   H2 A/B MODE: both prompt arms (A=control, B=symmetric).
echo   ~2x token cost. Tracker still imports the control arm only.
echo ************************************************************

set EQUITY_AB_TEST=1
call run_daily.bat %*
endlocal
