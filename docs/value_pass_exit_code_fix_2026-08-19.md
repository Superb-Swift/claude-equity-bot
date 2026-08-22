# `value.bat` — the exit-code contract is unenforceable as written

*Claude Equity Bot · Phase 3-C · 2026-08-19 · advisory-only · no orders · not financial advice.*

**Reproduced end-to-end against the operator's real master, real `edgar_cache` and both real
logs. Nothing below is inferred from reading the code alone.**

---

## 1 · What happened on 2026-08-19

`value_anchor_2026-08-19.md` **does not exist**. `band_price_2026-08-19.md` and
`implied_return_2026-08-19.md` both do, written 16:41:22 and 16:41:23 CDT. Step 4 ran after
step 3 produced no exhibit, and the pass closed on the **`VALUE PASS FINDINGS`** banner — the
one whose own text reads *"Findings are the NORMAL state here, not a failure."*

The chain, each link verified:

| # | link | evidence |
|---|---|---|
| 1 | `EQUITY_EDGAR` was not `1` for the 09:30 run | `"prompt_variant": "A-S1D1-B1"` on all 26 Signal JSONs (8/18: `A-S1D1-B1-E1` on all 25); zero `[EDGAR]` lines; zero `E[…]` tags (8/18: 25) |
| 2 | no `E[…]` tags ⇒ `parse_log_tags()` returns `{}` | `value_anchor.py` L157–190 keys strictly on `E\[…\]` on the same line as the Signal JSON |
| 3 | empty tags ⇒ every candidate fails `_check_candidate` | `"ticker has no E[...] tag in the supplied log"` × 16 |
| 4 | `verified` empty ⇒ **`return 1` at L493, before the `md_path` write at L630** | reproduced: exit 1, **no file created** |
| 5 | `value.bat` step 3 reads `errorlevel 1` as FINDINGS, not FAILURE | sets `FIND1=1`, leaves `FAIL2=0` |
| 6 | `FAIL2=0` ⇒ step 4 is **not** skipped | `implied_return_2026-08-19.md` exists, `join: 0 verified, 16 unverified`, every table empty |
| 7 | banner reports FINDINGS | `RC=1` |

Reproduction transcript (this container, operator's files):

```
$ python3 value_anchor.py --tracker logs/claude_equity_bot_tracker.xlsx \
      --cache edgar_cache --log logs/signals_2026-08-19.log \
      --md value_anchor_2026-08-19.md
  LOG NOT SUPPLIED OR CARRIES NO E[...] TAGS.
  VERIFIED by both routes    0   []
  UNVERIFIED (not used)      16
Nothing verified; no numbers reported.
EXIT CODE = 1
md written?  -> NO FILE

$ # control: identical invocation, 8/18 log (which carries the tags)
  VERIFIED by both routes    15   ['AAPL','DOW','FTI','GLD','JPM','MSFT','NKE',
                                   'NVDA','PM','PWR','RTX','SND','SPCX','USO','WMT']
EXIT CODE = 1
md written? -> 6494 bytes
```

**Both runs exit 1.** One computed fifteen names; the other computed nothing and wrote no file.
`value.bat` cannot tell them apart, and neither can the operator reading the banner.

---

## 2 · The two defects, stated separately because the remedies differ

### D-V1 — `value_anchor.py` returns 1 on a could-not-run state, contradicting its own rule three lines above

```python
    if not os.path.isdir(cache_dir):
        ...
        # EXIT 2, NOT 1 -- see the matching note in implied_return.py. No cache
        # means nothing was computed, which is a could-not-run state.
        return 2                                        # L432

    ...
    if not verified:
        out("Nothing verified; no numbers reported.")
        return 1                                        # L493  <-- same state, different code
```

"No cache ⇒ nothing computed ⇒ exit 2" and "nothing verified ⇒ nothing computed ⇒ exit 1" are
the same state under the file's own stated definition. The comment at L430 is the argument
against L493 and it is sitting in the same function.

**This is the record's standing defect class — a tool reporting a state it did not act on —
in its exit code rather than in its output.**

### D-V2 — `value.bat` treats "the step wrote no exhibit" as indistinguishable from a clean findings run

Two independent gaps:

1. **An unhandled Python exception also exits 1.** Any traceback in `band_price.py`,
   `value_anchor.py` or `implied_return.py` is currently read as FINDINGS and the pass
   continues. Today it was a deliberate `return 1` rather than a crash, but the script cannot
   distinguish the two cases and would behave identically.
2. **Nothing checks that the exhibit exists.** The script's own header names the dated `.md`
   files as the pass's only outputs, then never verifies one was written. The banner lists
   all three exhibit names unconditionally, including the one that does not exist.

---

## 3 · Recommended fix

Two edits. Neither touches the prompt, the master, `edgar_client.py`, any E4 endpoint, KEEP-70,
H4, or the ±3% band. Both are in the value pass only.

### 3.1 `value_anchor.py` — one line

```diff
     if not verified:
         out("Nothing verified; no numbers reported.")
-        return 1
+        # EXIT 2, NOT 1 -- identical reasoning to the absent-cache branch above.
+        # Nothing was computed, so this is a could-not-run state, and the caller
+        # must be able to distinguish it from a clean run that found something.
+        return 2
```

Consequence: `value.bat` step 3 sets `FAIL2=1`, step 4 is correctly skipped, and the pass
closes on `VALUE PASS INCOMPLETE` — which is the true statement.

### 3.2 `value.bat` — verify the artifact, do not trust the code

Add after each producing step. Shown for step 3; steps 2 and 4 take the same shape.

```bat
python value_anchor.py --tracker "%MASTER%" --cache "%CACHE%" --log "%LOGFILE%" --md "value_anchor_%RUNDATE%.md"
if errorlevel 2 (
    echo   NOTE: value_anchor could not run.
    set "FAIL2=1"
) else if errorlevel 1 (
    set "FIND1=1"
)
REM  ARTIFACT GUARD - the step's exit code is a claim; the file is the evidence.
REM  A Python traceback also exits 1, so a missing exhibit must not read as FINDINGS.
if not exist "value_anchor_%RUNDATE%.md" (
    echo   NOTE: value_anchor produced NO EXHIBIT. Treating as could-not-run
    echo         regardless of exit code - see 2026-08-19.
    set "FAIL2=1"
)
```

**Stale-artifact caveat, stated rather than left implicit:** `if not exist` passes on
*yesterday's* file if the run date is re-used, which `value.bat 2026-08-17` does by design.
If that matters, delete the three dated exhibits for `%RUNDATE%` immediately after step 0's
paste guard, so their presence at the end is proof of *this* run.

### 3.3 Optional, and the only one that closes the class rather than the instance

Give the three tools a distinct findings code — `return 3` for findings, reserving 1 for an
uncaught exception — and have `value.bat` read `errorlevel 3` as FINDINGS, `2` as could-not-run,
and `1` as **crash**. This is the only version in which a traceback cannot masquerade as a
clean result. It is a three-file edit and it changes an exit contract the record already
documents, so it wants a dated note rather than a quiet change.

---

## 4 · What is NOT wrong

Stated because the pass produced a real result today and it should not be discarded with the rest.

- **`band_price.py` ran correctly and its output is live.** Diffed against 8/18: master rows
  1536 → 1562, cohorts 64 → 65, every per-name median and every pooled figure moved. It is
  independent of EDGAR by design, exactly as the script header claims, and that claim is now
  demonstrated rather than asserted.
- **`quote_dump.json` captured 26/26 at 16:41:21.** Step 1 is clean.
- **The paste guard (step 0) worked.** The master carried 2026-08-19 before the pass ran.
- **`implied_return`'s join count is correct.** `0 verified, 16 unverified` is exactly what
  the imported join produces on a tagless log; the tool reported its inputs honestly.

---

## 5 · The finding that is larger than the plumbing

The value pass is the only instrument in the stack that noticed the arm reverted. `signal_scan`
printed `[OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)` — factually correct, and marked OK,
because the check verifies that the stamp matches the run rather than that the run matches the
intended arm. Nothing else in `run_daily.bat`, `scan.bat` or `run_daily_review.bat` mentions
`EQUITY_EDGAR` at all.

**So the missing `value_anchor` exhibit is currently the project's only alarm for a lost EDGAR
flag, and it raises that alarm by looking like a routine findings run.** That is worth more
attention than either defect above.

The go-live runbook already predicted the mechanism, in §2: *"`set` is per-console. The
2026-08-04 precedent is the one to avoid — a new console after a token reauth lost the flag and
produced a control cohort."* It happened again on 2026-08-19.

**Suggested guard, cheapest available:** have `run_daily.bat` echo the resolved era before the
run and refuse on a mismatch against an expected value, or have `signal_scan` compare today's
era stamp against the prior session's log and FAIL on a change — the same one-line
prior-session comparison already built for the membership check, applied to a second field.

---

*Advisory-only · no orders · not financial advice.*
