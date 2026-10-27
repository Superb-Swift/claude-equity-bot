@echo off
REM ============================================================================
REM  selftest.bat - every instrument that can be shown to FAIL, shown to pass
REM  Claude Equity Bot - advisory-only - no orders (DP-T1)
REM
REM  ADDED 2026-09-16. "A gate that has never been shown to fail is not a gate"
REM  (Phase 3-C exit review 6.2). Each tool below carries a --selftest that
REM  includes at least one NEGATIVE case: synthetic input the check must reject.
REM  Run this after any code change and before trusting a clean scan.
REM
REM  Reads nothing but the master (read-only) and writes nothing.
REM  Exit 0 = all pass. Exit 1 = at least one selftest failed.
REM ============================================================================
setlocal
set PYTHONUTF8=1
set "MASTER=logs\claude_equity_bot_tracker.xlsx"

call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: could not activate venv
    exit /b 2
)

set "RC=0"
REM Offline selftests. value_anchor, xbrl_sweep and edgar_client run on fixtures
REM (no network), added 2026-09-17 per repo remediation R8b.
REM AMENDED 2026-10-22: e4_counter (it had a selftest and was never in this
REM list), outcome_sanity (Checks H and I), enter_closes (catch-up, R9),
REM risk_engine (P4-1: every declared rule), run_guard (R2), and the new local
REM tools decision_journal, prune_signal_state, ttm_eps, earnings_calendar.
REM AMENDED 2026-10-24: sec_facts (the shared SEC reader) and sec_data_audit.
for %%T in (episodes advisory_guard trail_basis_audit shadow_damper signal_scan band_price implied_return value_anchor xbrl_sweep edgar_client value_card e4_counter outcome_sanity enter_closes risk_engine run_guard decision_journal prune_signal_state ttm_eps earnings_calendar sec_facts sec_data_audit) do (
    python %%T.py --selftest >nul 2>&1
    if errorlevel 1 (
        echo   [FAIL] %%T --selftest   detail: python %%T.py --selftest
        set "RC=1"
    ) else (
        echo   [PASS] %%T
    )
)

python trading_calendar.py --selftest --tracker "%MASTER%" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] trading_calendar --selftest   detail: python trading_calendar.py --selftest --tracker "%MASTER%"
    set "RC=1"
) else (
    echo   [PASS] trading_calendar
)

python discovery_scan.py --selftest --tracker "%MASTER%" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] discovery_scan --selftest   detail: python discovery_scan.py --selftest
    set "RC=1"
) else (
    echo   [PASS] discovery_scan
)

REM Pre-deploy audits: the four log parsers against a synthetic log (the era
REM label is read from main.py), and the phase dispatcher.
for %%A in (edgar_parser_audit phase_dispatch_audit) do (
    python %%A.py >nul 2>&1
    if errorlevel 1 (
        echo   [FAIL] %%A   detail: python %%A.py
        set "RC=1"
    ) else (
        echo   [PASS] %%A
    )
)

python rulings.py >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] rulings.py does not import
    set "RC=1"
) else (
    echo   [PASS] rulings registry imports
)

echo.
if "%RC%"=="0" (
    echo SELFTEST CLEAN - every gate was shown to reject what it exists to reject.
) else (
    echo SELFTEST FAILURES - fix before trusting any scan result.
)
exit /b %RC%
