# EDGAR Go-Live Runbook — 2026-08-13

*Claude Equity Bot · Phase 3-C · written 2026-08-12, the evening before. One page, in order. Advisory-only · no orders · not financial advice.*

---

## 0 · State at the close of 2026-08-12

| | |
|---|---|
| Change order | **Complete.** Every step landed; the live-run gate was met by the 8/12 cohort |
| 8/12 cohort | 24/24 cross-check clean, 1,435 rows, 60 cohorts, resolutions complete at all three horizons |
| Runtime path | **Untouched by tonight's edits** `[V]` — `main.py` imports none of the four tools modified |
| `PHASE` dispatch | `phase_dispatch_audit` PASSED against the real `main.py`: `'3-C'` reaches a handler |
| Parser audit | PASSED with `log_tracker_crosscheck` added as the fourth parser; negative-tested to FAIL |
| Derived cache | Warm at `EXTRACT_SCHEMA = 9` — no cold-recompute budget risk |
| DP-3C-t | Ruled, and applied to the pre-registration (now **v1.3**) |
| `scan.bat` | Now runs `outcome_sanity.py` after the cross-check |

---

## 1 · Pre-flight (five minutes, before the run)

Run from the project root with the venv active. **All four are read-only.**

```
python edgar_client.py --selftest
python edgar_parser_audit.py
python phase_dispatch_audit.py
python xbrl_sweep.py --selftest
```

**All four must exit 0.** I have verified the middle two against your actual files; the two `--selftest` gates exercise the SEC extraction paths and should be run in your environment rather than approximated in mine.

Then confirm the SEC user agent loads, because a generic UA returns 403 and roughly a ten-minute IP block:

```
python -c "import os;from dotenv import load_dotenv;load_dotenv();print(repr(os.getenv('SEC_USER_AGENT')))"
```

---

## 2 · The run

```
venv\Scripts\activate
set EQUITY_EDGAR=1
run_daily.bat
```

`set` is per-console. **The 2026-08-04 precedent is the one to avoid** — a new console after a token reauth lost the flag and produced a control cohort. If the run reauthorises Schwab in a fresh window, re-check the flag before trusting the era stamp.

---

## 3 · Read these eight lines before anything else

| # | Expect | If wrong |
|---|---|---|
| 1 | Banner: `Claude Equity Bot — Phase 3-C` | stop |
| 2 | `[EDGAR] prefetch: N/24 ticker(s) resolved` — live has emitted **19/24**; Workflow §4's "15/24" is the known-stale figure | note it, not a defect |
| 3 | **`"prompt_variant": "A-S1D1-B1-E1"`** in every Signal JSON, and **never** inside the phase bracket | cohort-level defect (a) |
| 4 | `[PHASE 3-C DRY RUN]` on all 24 lines | cohort-level defect (a) |
| 5 | **24** `Signal JSON:` lines | cohort-level defect (a) |
| 6 | `E[…]` on the 15 covered names; `E[no filings]` on **9** — the 8 dark names **plus CBRS** | see the note below |
| 7 | `8k=…@date` and `form4=…@date` (DP-3C-i); `fin=` reading `N@period` / `degraded` / `none` (DP-3C-j) | malformed → (a); `degraded` → name-level (b) |
| 8 | **No** `run budget of 120s exhausted` | if present, name-level (b) for the affected names |

**On line 6:** nine names emitting `E[no filings]` is expected and only eight of them mean it — CBRS is a DP-3 policy exclusion wearing the same string. Recorded 8/12, not fixed, **not a defect under DP-3C-t.**

Token sanity: input tokens should land roughly **+9,400** above the control baseline of 36,800–37,250.

---

## 4 · After the paste

```
scan.bat
run_daily_review.bat
```

`scan.bat` now ends with the outcome guard. Expect it to flag the three known items until they are resolved at source — **AG ×3** (2026-06-26 close 19.89, +16.1% quote-to-close), **GLD** (two closes for 2026-07-02: 378.13 vs 379.13), **CBRS** (+46.6% at +10d, a true magnitude positive, not an error). Anything *new* is worth reading closely.

---

## 5 · The DP-3C-t decision, made once, at the end of the review

**Does the cohort enter E4, or is it a SHAKEDOWN?** The test: *is the artifact wrong, or is the reader wrong?*

**Tag SHAKEDOWN and exclude from E4-1/2/3 if any of:**

- a mixed-period rendered line on any covered name (the N-1 class)
- a rendered figure disagreeing with that filer's own 8-K by more than **2%**, where an 8-K exists
- an `E[…]` tag malformed, or absent where one is due, **in the log itself**
- a wrong era stamp or phase token **in the log**
- a master row that does not reconcile to its log row

**Mark the ticker DEGRADED, keep the cohort, if:** `fin=degraded`, or budget exhaustion hits specific names. Not a defect — but that name did not receive the treatment and must not count as though it did.

**Defer the READ, keep the cohort, if:** a review tool cannot read correct inputs. Hold **PENDING VERIFICATION**, name it in the dated entry, and admit it to E4 only once the tool is fixed and re-run clean against that cohort's own log and master.

**Not defects:** informational sweep flags (SPLIT-VOTE, extreme YoY on a small base, THIN, XBRL-LAG); a PRIOR-period NOTE firing; a `[6M YTD]` / `[9M YTD]` label firing — that label firing is evidence the N-1 fix *works*.

---

## 6 · Rollback

One word: `PHASE` back to `"3-B"` in `main.py` L64 — **and the L566 dispatch tuple already accepts both**, so nothing else moves. Unsetting `EQUITY_EDGAR` alone produces a byte-identical 3-B-behaviour run under the 3-C token.

---

## 7 · Known-open, none of them blocking

- **8/10 price findings** — AG 2026-06-26 and GLD 2026-07-02, both still live in the master and both reproduced by `outcome_sanity` on 8/12. Pre-EDGAR rows; they affect E4-1's baseline and should close before that read.
- **`E[no filings]` conflation** — fix the tag, `edgar_parser_audit`'s assertions and Workflow §4's checklist in one edit, never separately.
- **`xbrl_sweep` mezzanine blind spot** — would fire a false HARD finding on a recent-IPO balance sheet. Only reachable if CBRS is ever unblocked.
- **Two review-tool defects found 8/12** — `build_near_miss_registry`'s miswritten locked `+10d` assertion, and `h1_lag_trace`'s missing minimum-|r| floor.
- **Three stale strings** — `h4_dq_threshold`'s "Q2 registry of 17"; the review banner's `n ≥ 10` and its 2026-07-27 Q1-R date.

---

*Advisory-only · no orders · not financial advice.*
