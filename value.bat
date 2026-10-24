@echo off
REM ============================================================================
REM  value.bat - valuation-layer pass: band pricing, market-vs-book, and the
REM  value-driver identity run backwards
REM  Claude Equity Bot - Phase 3-C - advisory-only - no orders
REM
REM  RUN THIS AFTER THE PASTE, for the same reason scan.bat does.
REM  value_anchor and implied_return take PRICE from the master's LATEST COHORT.
REM  If the master does not yet carry today, they silently price against
REM  yesterday's close and every M/B, MVA and implied return is quietly wrong
REM  rather than visibly absent. Step 0 refuses on that condition instead of
REM  trusting the operator to remember. Ordering is binding.
REM
REM  DEPENDENCY CHAIN - stated so it is not reordered later:
REM    quote_dump.py     -> live Schwab call; writes quote_dump.json
REM    band_price.py     -> the MASTER only. Independent of everything else here,
REM                         so it still runs when Schwab or EDGAR is unavailable.
REM    value_anchor.py   -> master + edgar_cache + today's signals log
REM    implied_return.py -> all of the above INCLUDING quote_dump.json, so it is
REM                         LAST. It imports value_anchor for the accession-to-
REM                         ticker join, so value_anchor.py must sit beside it.
REM    value_card.py     -> ADDED 2026-10-14. Reads implied_return's dated
REM                         exhibit (and the earlier ones), today's log,
REM                         quote_dump.json and the master's BUY rows (date,
REM                         ticker, confidence only). It is now the LAST step.
REM                         Counterfactual only: no gate, no outcome, no prompt.
REM                         AMENDED 2026-10-24 (DP-V4): its class reads 12-month
REM                         ROE from valuation_cache\ (written by ttm_eps), and
REM                         its expectations panel reads the calendar's consensus
REM                         (earnings_calendar). Both run before it below.
REM    step 5b           -> ADDED 2026-10-14. Embeds the card as the 'Value Card'
REM                         sheet in tracker_with_registry.xlsx. So value.bat now
REM                         runs AFTER run_daily_review.bat (which rebuilds that
REM                         copy) and BEFORE the Excel cache refresh (workflow
REM                         step 6), because an openpyxl save drops Excel's
REM                         cached formula results.
REM
REM  NOTHING HERE WRITES TO THE MASTER. Nothing touches the prompt,
REM  edgar_client.py, any E4 endpoint, KEEP-70, H4 or the +/-3%% band. The only
REM  files written are quote_dump.json and the dated .md exhibits (plus, from
REM  2026-10-14, value_card_<date>.json beside value_card_<date>.md).
REM  AMENDED 2026-10-14: until today this line read "NOTHING HERE WRITES TO ANY
REM  WORKBOOK". Step 5b now writes ONE sheet, 'Value Card', into the GENERATED
REM  report copy only. It refuses while Excel has the copy open (or its ~$ owner
REM  file exists), refuses the master, refuses a copy the review has not
REM  rebuilt for today, and swaps the file in atomically.
REM
REM  NOT IN THIS PASS: fundamental_probe.py. It is a one-off diagnostic for the
REM  open peRatio-semantics question, not a daily step. Run it by hand.
REM
REM  Usage:  value.bat                 (uses today's date)
REM          value.bat 2026-08-17      (explicit date)
REM
REM  Exit 0 = clean. Exit 1 = findings. Exit 2 = a step could not run.
REM
REM  IMPLEMENTATION NOTE, deliberate: this script never READS an accumulator
REM  variable inside a parenthesised block. cmd expands %VAR% when it PARSES the
REM  block, not when it runs it, so "if not "%RC%"=="2" set RC=1" inside an
REM  if/else body reads a stale value. Steps therefore only ever SET the flags
REM  FAIL2 and FIND1, and the exit code is resolved once, at the end, at top
REM  level. Same class as the ordering defects already on the record - a
REM  correct-looking construct that silently reports the wrong thing.
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

set "MASTER=logs\claude_equity_bot_tracker.xlsx"
set "LOGFILE=logs\signals_%RUNDATE%.log"
set "CACHE=edgar_cache"

if not exist "%MASTER%" (
    echo ERROR: master not found at %MASTER%
    exit /b 2
)
if not exist "%LOGFILE%" (
    echo ERROR: no log for %RUNDATE% at %LOGFILE%
    echo        NYSE holiday? No log is produced and there is nothing to value.
    exit /b 2
)
if not exist "%CACHE%" (
    echo ERROR: %CACHE% not found. It is gitignored and re-fetchable; run the
    echo        daily pipeline once to repopulate it. These tools never fetch.
    exit /b 2
)

set "FAIL2=0"
set "FIND1=0"

REM ---------------------------------------------------------------------------
REM  ARTIFACT GUARD, added 2026-08-19. Read this before touching any step below.
REM
REM  On 2026-08-19 value_anchor.py returned 1 (FINDINGS) on a state in which it
REM  had computed nothing, and its `return` fired BEFORE it wrote its exhibit.
REM  This script read 1 as FINDINGS, did not set FAIL2, did not skip step 4, and
REM  closed on "VALUE PASS FINDINGS - Findings are the NORMAL state here, not a
REM  failure." No value_anchor_2026-08-19.md was ever written and nothing said so.
REM
REM  value_anchor.py now returns 2 for that state. THAT FIX ALONE IS NOT ENOUGH:
REM  an unhandled Python traceback ALSO exits 1, so any crash in any of the three
REM  tools would still read as a clean findings run. An exit code is a CLAIM; the
REM  dated .md file is the EVIDENCE. Each producing step is therefore followed by
REM  a check that the exhibit exists AND was written by THIS run.
REM
REM  T0 is the run's start time. Comparing mtime against it rather than merely
REM  testing `if exist` is deliberate: `value.bat 2026-08-17` re-runs an earlier
REM  date by design, so yesterday's file is often already sitting there and a bare
REM  existence test would pass on it. That would be the same defect one layer out.
REM ---------------------------------------------------------------------------
for /f %%t in ('python -c "import time;print(int(time.time()))"') do set "T0=%%t"

REM ---------------------------------------------------------------------------
REM  Step 0 - PASTE GUARD. The ordering hazard, checked rather than trusted.
REM ---------------------------------------------------------------------------
echo.
echo ### 0. paste guard - does the master already carry %RUNDATE%?
python -c "import openpyxl,sys;wb=openpyxl.load_workbook(sys.argv[1],data_only=True,read_only=True);ws=wb['Signals'];d=max((str(r[0])[:10] for r in ws.iter_rows(min_row=5,values_only=True) if r and r[0] and r[1]),default='');wb.close();print('   master latest cohort:',d,'  expected:',sys.argv[2]);sys.exit(0 if d==sys.argv[2] else 1)" "%MASTER%" "%RUNDATE%"
if errorlevel 1 (
    echo.
    echo   REFUSING TO RUN. The master's latest cohort is not %RUNDATE%.
    echo   value_anchor and implied_return would price against the wrong session
    echo   and produce plausible wrong numbers rather than an obvious error.
    echo   Paste today's rows into the master, open it in Excel, then re-run.
    echo   band_price.py alone is safe right now if you want it: it reads only
    echo   resolved returns and never the latest cohort's price.
    exit /b 2
)

REM ---------------------------------------------------------------------------
REM  Step 1 - quote_dump, but only if today's is not already captured. Skipping
REM  a same-day dump avoids 26 needless API calls and stops the
REM  quote_dump_<stamp>.json backups accumulating one per run.
REM  The dump's own lastPrice is NOT used for valuation - implied_return takes
REM  price from the master. Only eps and divYield come from here and both move
REM  quarterly, so the capture time of day does not matter.
REM ---------------------------------------------------------------------------
echo.
echo ### 1. quote dump - Schwab fundamentals ^(eps, peRatio, divYield^)
python -c "import json,sys,os;p='quote_dump.json';d=(json.load(open(p)).get('captured_local','') if os.path.exists(p) else '');sys.exit(0 if d[:10]==sys.argv[1] else 1)" "%RUNDATE%"
if errorlevel 1 (
    echo   no dump for %RUNDATE% yet - fetching
    python quote_dump.py
    if errorlevel 2 set "FAIL2=1"
    if errorlevel 1 set "FAIL2=1"
) else (
    echo   quote_dump.json already captured %RUNDATE% - reusing, no API calls
)

REM ---------------------------------------------------------------------------
REM  Step 2 - band pricing. Master only, so it runs even if Schwab is down.
REM ---------------------------------------------------------------------------
echo.
echo ### 2. band price - the fixed +/-3%% HOLD band, priced per name
python band_price.py --tracker "%MASTER%" --md "band_price_%RUNDATE%.md"
if errorlevel 2 (
    echo   NOTE: band_price could not run. NOTHING in that block was checked.
    set "FAIL2=1"
) else if errorlevel 1 (
    set "FIND1=1"
)
python -c "import os,sys;p=sys.argv[1];sys.exit(0 if os.path.exists(p) and os.path.getmtime(p)>=float(sys.argv[2]) else 1)" "band_price_%RUNDATE%.md" "%T0%"
if errorlevel 1 (
    echo   NOTE: band_price wrote NO EXHIBIT this run ^(absent, or left over from
    echo         an earlier run^). Treating as could-not-run regardless of its
    echo         exit code -- see 2026-08-19.
    set "FAIL2=1"
)

REM ---------------------------------------------------------------------------
REM  Step 3 - market vs book.
REM ---------------------------------------------------------------------------
echo.
echo ### 3. value anchor - forecast-free market-vs-book
python value_anchor.py --tracker "%MASTER%" --cache "%CACHE%" --log "%LOGFILE%" --md "value_anchor_%RUNDATE%.md"
if errorlevel 2 (
    echo   NOTE: value_anchor could not run. If it reported "Nothing verified",
    echo         the log for %RUNDATE% carries no E[...] tags -- which means the
    echo         run executed with EQUITY_EDGAR unset and there is no treatment
    echo         to value. That is not fixable by re-running this script.
    set "FAIL2=1"
) else if errorlevel 1 (
    set "FIND1=1"
)
python -c "import os,sys;p=sys.argv[1];sys.exit(0 if os.path.exists(p) and os.path.getmtime(p)>=float(sys.argv[2]) else 1)" "value_anchor_%RUNDATE%.md" "%T0%"
if errorlevel 1 (
    echo   NOTE: value_anchor wrote NO EXHIBIT this run ^(absent, or left over from
    echo         an earlier run^). Treating as could-not-run regardless of its
    echo         exit code -- see 2026-08-19.
    set "FAIL2=1"
)

REM ---------------------------------------------------------------------------
REM  Step 4 - the inversion. LAST, because it needs steps 1 and 3.
REM  FAIL2 is read here at TOP LEVEL, not inside a block, so the value is current.
REM ---------------------------------------------------------------------------
echo.
if "%FAIL2%"=="1" goto skip4

echo ### 4. implied return - the value-driver identity, run backwards
python implied_return.py --tracker "%MASTER%" --cache "%CACHE%" --log "%LOGFILE%" --quotes quote_dump.json --md "implied_return_%RUNDATE%.md"
if errorlevel 2 (
    echo   NOTE: implied_return could not run.
    set "FAIL2=1"
) else if errorlevel 1 (
    set "FIND1=1"
)
python -c "import os,sys;p=sys.argv[1];sys.exit(0 if os.path.exists(p) and os.path.getmtime(p)>=float(sys.argv[2]) else 1)" "implied_return_%RUNDATE%.md" "%T0%"
if errorlevel 1 (
    echo   NOTE: implied_return wrote NO EXHIBIT this run ^(absent, or left over
    echo         from an earlier run^). Treating as could-not-run regardless of
    echo         its exit code -- see 2026-08-19.
    set "FAIL2=1"
)
goto step5

:skip4
echo ### 4. implied return - SKIPPED
echo   A prerequisite step could not run. implied_return needs a valid
echo   quote_dump.json plus the same master and cache; running it now would
echo   report against inputs that were never verified.

REM ---------------------------------------------------------------------------
REM  Step 5 - value card. ADDED 2026-10-14 (claude/ValuePass_WhatItMeasures_
REM  2026-10-14.md). Builds on step 4's exhibit, so it runs only when every
REM  earlier step produced its evidence. FAIL2 is read here at TOP LEVEL.
REM  It prints: coverage; what changed since the previous exhibit (filings,
REM  class crossings split into price and filing parts, robustness); the
REM  decision card; the six-way robustness of every class; DP-V2's
REM  counterfactual flip ledger (COUNTS ONLY); book-free reads; and a check
REM  that the class still reconstructs as a trailing-FY P/E.
REM ---------------------------------------------------------------------------
:step5
REM ---------------------------------------------------------------------------
REM  Steps 6-7 - ADDED 2026-10-22 (value layer V5 and V2; DP-V3). CONTEXT
REM  exhibits, run BEFORE the value card so it can show them beside the class.
REM  They run on every path and NEVER change the exit code: a failure prints a
REM  NOTE, and the pass stays exactly as clean or incomplete as steps 1-5 make
REM  it. Nothing in either reaches the prompt or a gate (DP-V1).
REM ---------------------------------------------------------------------------
echo.
echo ### 6. earnings calendar - next report date per name (V5, context only)
python earnings_calendar.py --date %RUNDATE%
if errorlevel 1 echo   NOTE: earnings_calendar did not complete - context only; exit code unchanged.
echo.
echo ### 7. TTM EPS and ROE - SEC companyfacts in valuation_cache (V2, context only)
python ttm_eps.py --date %RUNDATE% --quotes quote_dump.json
if errorlevel 2 echo   NOTE: ttm_eps could not run - context only; exit code unchanged.
REM  Step 7b - ADDED 2026-10-24. The SEC data audit (sec_data_audit.py): every
REM  name's filing and quarter gaps, the prompt's statement block against SEC
REM  for the same period, and the value card's ROE basis against TTM. It reads
REM  the cache ttm_eps just refreshed, writes sec_data_audit_<date>.md, and like
REM  steps 6-7 NEVER changes the exit code. Reporting only (DP-V1, DP-V3).
echo.
echo ### 7b. SEC data audit - gaps, period basis, ROE basis vs TTM (reporting only)
python sec_data_audit.py --date %RUNDATE% --quotes quote_dump.json > nul
if errorlevel 2 (
    echo   NOTE: sec_data_audit could not run - reporting only; exit code unchanged.
) else if errorlevel 1 (
    echo   NOTE: sec_data_audit has findings - read sec_data_audit_%RUNDATE%.md; exit code unchanged.
) else (
    echo   sec_data_audit_%RUNDATE%.md written - no unresolved gap or mismatch.
)

echo.
if "%FAIL2%"=="1" goto skip5

echo ### 5. value card - decisions, changes, robustness, DP-V2 counterfactual ledger
python value_card.py --date %RUNDATE% --tracker "%MASTER%" --log "%LOGFILE%" --quotes quote_dump.json --md "value_card_%RUNDATE%.md" --json "value_card_%RUNDATE%.json"
if errorlevel 2 (
    echo   NOTE: value_card could not run.
    set "FAIL2=1"
) else if errorlevel 1 (
    set "FIND1=1"
)
python -c "import os,sys;p=sys.argv[1];sys.exit(0 if os.path.exists(p) and os.path.getmtime(p)>=float(sys.argv[2]) else 1)" "value_card_%RUNDATE%.md" "%T0%"
if errorlevel 1 (
    echo   NOTE: value_card wrote NO EXHIBIT this run ^(absent, or left over
    echo         from an earlier run^). Treating as could-not-run regardless of
    echo         its exit code -- see 2026-08-19.
    set "FAIL2=1"
)

REM ---------------------------------------------------------------------------
REM  Step 5b - embed the card into the report copy. ADDED 2026-10-14.
REM  Today's run only: a re-run for an earlier date has no report copy to match.
REM  Read at TOP LEVEL, like every other flag here.
REM ---------------------------------------------------------------------------
echo.
if "%FAIL2%"=="1" goto summary
for /f %%d in ('python -c "import datetime;print(datetime.date.today().isoformat())"') do set "TODAYD=%%d"
if not "%RUNDATE%"=="%TODAYD%" goto skip5b

echo ### 5b. value card - embed the 'Value Card' sheet into tracker_with_registry.xlsx
python value_card.py --embed-from "value_card_%RUNDATE%.json" --embed-into tracker_with_registry.xlsx --tracker "%MASTER%"
if errorlevel 1 (
    echo   NOTE: the Value Card sheet was NOT embedded ^(reason above^). The exhibit
    echo         value_card_%RUNDATE%.md is unaffected. Close Excel, then re-run
    echo         value.bat, or only: python value_card.py --embed-from value_card_%RUNDATE%.json --embed-into tracker_with_registry.xlsx
    set "FAIL2=1"
)
goto summary

:skip5b
echo ### 5b. value card embed - SKIPPED: %RUNDATE% is not today, and the report
echo   copy only ever holds today's review.
goto summary

:skip5
echo ### 5. value card - SKIPPED
echo   It is built on implied_return's exhibit, and an earlier step could not run.

:summary
set "RC=0"
if "%FIND1%"=="1" set "RC=1"
if "%FAIL2%"=="1" set "RC=2"

echo.
echo ============================================================================
if "%RC%"=="0" (
    echo VALUE PASS CLEAN - no findings from any step.
) else if "%RC%"=="2" (
    echo VALUE PASS INCOMPLETE - a step could not run. Nothing above is a clean
    echo result, and any figure printed before the failure should be re-derived
    echo once the blocking condition is fixed.
) else (
    echo VALUE PASS FINDINGS - review the blocks above. Findings are the NORMAL
    echo state here, not a failure: a re-tier count or an excluded name is the
    echo instrument reporting, not breaking.
)
echo.
echo Exhibits ^(state read from disk, not assumed^):
REM  The old banner listed all three names unconditionally, including on
REM  2026-08-19 when value_anchor_2026-08-19.md did not exist. A closing summary
REM  that names a file it never checked for is the same defect this script now
REM  guards against, printed one line lower down.
python -c "import os,sys,time;t0=float(sys.argv[1]);[print('   {:<28} {}'.format(p,('WRITTEN this run' if os.path.getmtime(p)>=t0 else 'STALE - left from an earlier run') if os.path.exists(p) else 'ABSENT')) for p in sys.argv[2:]]" "%T0%" "band_price_%RUNDATE%.md" "value_anchor_%RUNDATE%.md" "implied_return_%RUNDATE%.md" "value_card_%RUNDATE%.md" "earnings_calendar_%RUNDATE%.md" "ttm_eps_%RUNDATE%.md" "sec_data_audit_%RUNDATE%.md"
echo.
echo No valuation is asserted and no price target is implied by any step.
echo Advisory-only - no orders - not financial advice.
echo ============================================================================

exit /b %RC%
