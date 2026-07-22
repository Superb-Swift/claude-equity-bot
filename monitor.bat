@echo off
REM ===========================================================================
REM monitor.bat  —  open-questions monitor strip (daily glance)
REM ===========================================================================
REM PURPOSE:
REM   Activates the venv and runs monitor_strip.py against the tracker + logs.
REM   Reports the state of every OPEN Phase 3-B question in one read:
REM     WS1/G2 blend vs base . WS2/G1 acceptance clock (episode detector)
REM     H4 DQ gate . KEEP-70 . registry + live band context
REM
REM USAGE (from the project root, AFTER pasting the day's rows):
REM     C:\Users\rober\claude-equity-bot> monitor.bat
REM     C:\Users\rober\claude-equity-bot> monitor.bat --no-png
REM   ( %* passes any flags straight through to monitor_strip.py. )
REM
REM WHY IT IS NOT INSIDE run_daily.bat:
REM   run_daily.bat ENDS by writing paste_today.tsv - the tracker does not
REM   contain today's rows until you paste them. Running the strip inside the
REM   daily runner would therefore report the PREVIOUS session's state
REM   (registry count, near-miss totals, resolutions). Run this after the
REM   paste so the numbers are current. Same standalone pattern as t2.bat.
REM
REM OUTPUTS:  monitor_strip.md (git-friendly, greppable for the notes splice)
REM           monitor_strip.png (embeds/pastes like the guardrail chart)
REM
REM ANALYST NOTE:
REM   The strip reads confidence_blend from logs\signals_*.log (the blend
REM   channel has no tracker column by design), so it must run from the
REM   project root where logs\ lives. Returns are computed from the Price
REM   columns, so an unrecalculated formula cache cannot affect it.
REM   The WS2 episode threshold is imported from risk_engine.DampingConfig
REM   (THETA) - one definition of "material adverse move" system-wide.
REM ===========================================================================

setlocal
set PYTHONUTF8=1
set TRACKER=logs\claude_equity_bot_tracker.xlsx

call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Could not activate venv. Is venv\Scripts\activate.bat present?
    exit /b 1
)

REM ---- matplotlib is only needed for the PNG; degrade gracefully without it ----
python -c "import matplotlib" 2>nul || (
    echo NOTE: matplotlib not present - writing monitor_strip.md only.
    python monitor_strip.py --tracker "%TRACKER%" --no-png %*
    endlocal
    exit /b 0
)

REM ---- The MASTER tracker is logs\claude_equity_bot_tracker.xlsx (the file you
REM      paste into; Excel keeps its formula cache live). tracker_with_registry.xlsx
REM      is a GENERATED report copy - openpyxl writes it, so its cache is always
REM      empty. Read the master; fall back to the copy only if the master is gone.
if not exist "%TRACKER%" (
    if exist "tracker_with_registry.xlsx" (
        set TRACKER=tracker_with_registry.xlsx
    ) else (
        echo ERROR: no tracker found ^(tried %TRACKER% and tracker_with_registry.xlsx^).
        exit /b 1
    )
)

python monitor_strip.py --tracker "%TRACKER%" %*
set RC=%ERRORLEVEL%

endlocal
exit /b %RC%
