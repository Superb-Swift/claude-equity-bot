# Instrument Fixes — 2026-08-21

*Claude Equity Bot · Phase 3-C · four changes landed in one session · advisory-only · no orders · not financial advice.*

**Companion to `Phase3C_ClosingReview_2026-08-21.md`.** Four files changed. Two are defect fixes, one lands a change-order item that has been quoted as blocked for ten sessions, one is a provenance correction. **No endpoint, bar, arm, n or disposition is changed by any of them.**

| # | file | class | verified by |
|---|---|---|---|
| 1 | `h1_lag_trace.py` | defect — display truncation on a G1 acceptance exhibit | regeneration against the master; 4 corrected values, all verdicts byte-identical |
| 2 | `signal_scan.py` | change-order item — membership check replaces `EXPECTED_N` | selftest 30/30; `edgar_parser_audit` exit 0; retro-run on real logs |
| 3 | `monitor_strip.py` | disclosure — which channel, which basis | regenerated; every published figure reproduces |
| 4 | `implied_return.py` | provenance correction + evidence | compiles; literal-only emissions. **Not yet exercised on a live cache run** |

---

## 1 · `h1_lag_trace.py` — the truncation defect

### 1.1 What was wrong

`h1_lag_trace_GM_3B.md` shipped with three values that appear in no channel anywhere in the system:

| date | shipped operative | shipped raw | tracker `Conf %` | log `confidence` | `confidence_raw` | `confidence_blend` |
|---|---|---|---|---|---|---|
| 2026-07-21 | 57% | 57% | **58** | — | — | — |
| 2026-08-17 | 56% | 57% | **57** | 57 | 57 | 57 |
| 2026-08-20 | 56% | 57% | **57** | 57 | 57 | 57 |

GM carries `damp 0` on both August sessions — `D[raw=57; op=57; trail=−2.89%; damp=0]` on 8/20 — so the operative and raw channels **cannot** differ. They differed anyway, which is what made the defect findable at all.

### 1.2 Mechanism

```python
# before
def conf_pct(v):
    if v is None:
        return None
    return v * 100.0 if v <= 1.0 else float(v)     # 0.57 -> 56.99999999999999
...
f"{(str(int(x['conf']))+'%') ...}"                  # int() TRUNCATES -> 56
```

Tracker `Conf %` cells are stored as fractions. IEEE-754 makes `0.57 * 100 == 56.99999999999999`, and both display paths printed `int(conf)`.

**Exactly three two-decimal fractions in [0.01, 1.00] have this property:**

```
>>> [x for x in range(1, 101) if int((x/100)*100) != x]
[29, 57, 58]
```

So every confidence of 29, 57 or 58 rendered one point low, and nothing else did.

**Why the raw exhibit differed from the operative one.** `--raw-from-logs` replaces `x["conf"]` with an integer parsed straight out of the Signal JSON (`r'"confidence_raw":\s*(\d+)'`). Overridden rows are exact; rows outside the log glob keep the tracker float and truncate. GM 8/17 and 8/20 are inside the glob (raw correct at 57), 2026-07-21 is outside it (both files truncate 0.58 → 57). That asymmetry is the entire explanation for two exhibits disagreeing on a name that cannot be damped.

### 1.3 Scope — the two halves are different sizes, and the distinction matters

- **Display: wrong.** Four values across two exhibits.
- **Statistics: never affected.** `confs = [x["conf"] for x in rows]` uses the *unrounded float*; only the printed cell went through `int()`. The lag scan, `corr(conf, trailing move)` and `corr(conf, +5d)` were computed on 56.99999999999999, which is 57 to any precision that matters.

**Verified, not assumed.** All four exhibits regenerated against `logs\claude_equity_bot_tracker.xlsx`:

| exhibit | rows | values corrected | lag verdict | corr(conf, trail) |
|---|---|---|---|---|
| `h1_lag_trace_WMT_3B.md` | 34 | **none** | 0 — unchanged | +0.841 — unchanged |
| `h1_lag_trace_WMT_raw_3B.md` | 34 | **none** | 1 — unchanged | +0.721 — unchanged |
| `h1_lag_trace_GM_3B.md` | 33 | **3** (7/21 57→58, 8/17 56→57, 8/20 56→57) | 0 — unchanged | +0.694 — unchanged |
| `h1_lag_trace_GM_raw_3B.md` | 33 | **1** (7/21 57→58) | 0 — unchanged | +0.694 — unchanged |

**No G1 reading moves.** And after the fix **GM's operative and raw exhibits are byte-identical**, which is what `damp 0` on every post-deploy session requires.

### 1.4 Why it survived, and the sentence that helped it

WMT never held a confidence of 29, 57 or 58 in the post-deploy window, so the **primary** tracer's exhibit is untouched and nobody had cause to re-derive the secondary's.

And the tool asserted its own correctness. Its degraded-cache block read:

> *"UNAFFECTED: Date | Sig | Conf | Trail — the columns the G1 table read is scored on. Confidence is a raw value; the trailing move is computed from the Price columns. THE ACCEPTANCE READ IS VALID."*

**`Conf` is not a raw cell value. It is a scaled one, and the scaling was the defect.** The `[raw-from-logs]` audit line made the same overreach, describing the fallback rows as *"exact for pre-deploy rows"* — the rows that truncate. Both are amended in place rather than deleted, because the wrong sentence is the more useful artifact: *a tool that certifies its own column as exact is a tool nobody re-derives.*

### 1.5 The change

- `conf_pct()` returns `round(v * 100.0, 6)` — the dust is removed once, at the source, so display, correlation and banding all see one number.
- Both display paths use `round()` instead of `int()`.
- The degraded-cache block now claims only "unaffected **by the blank cache**", and says why that is a weaker claim than "exact".
- The `[raw-from-logs]` line drops "exact" and states the construction that is actually true.
- A **TRAIL BASIS** note is added to the exhibit — see §3 below.

---

## 2 · `signal_scan.py` — the membership check, and `EXPECTED_N` retired

### 2.1 The blocker did not exist

The 8/03 change order's item (1) — *"add `signal_scan.py` to `edgar_parser_audit.py` FIRST"* — has been cited as blocking this edit on 8/18, 8/19 and 8/20. **It landed 2026-08-10**: the audit runs `signal_scan` as parser [7] and `log_tracker_crosscheck` joined as parser [9] on 8/12. This is a **retired blocker stated in live-blocker grammar**, and `retired_criteria_audit.py` cannot see it because it scans for retired *criteria*, not for satisfied *prerequisites*.

### 2.2 What `EXPECTED_N` was costing

`EXPECTED_N = 24` had been wrong against **six successive true values**: 25 on 8/13–8/14, 26 on 8/17, 25 on 8/18, 26 on 8/19, 8/20 and 8/21. A check that cannot pass is noise, and noise is how a real finding gets skipped — the failure mode the era alarm was built against on 8/19 and then reproduced on 8/20.

It is retired, not deleted: a named grave marker sits where the constant was, so a reader looking for it finds why it went rather than concluding it was lost.

### 2.3 What replaces it

A set-difference of today's tickers against the prior session's log, riding on the **same parse** the era alarm already performs — `prior_era()` now returns `(era, date, name, nrows, tickers)`. One field, one source; the 8/03 lesson (analyze_log's thresholds desyncing from `risk_engine`) applies to "which names ran yesterday" as much as to a threshold.

Three states, kept distinct because a tool that prints a pass when it could not run the check is the class DP-3C-j ruled on:

| state | condition | emitted |
|---|---|---|
| **OK** | compared, sets identical | `cohort membership UNCHANGED since <date> (N names; count n vs n in <log>)` |
| **FAIL** | compared, sets differ | `cohort membership CHANGED since <date> (n → m names) - ADDED: … ; REMOVED: …` |
| **NOCHK** | no usable prior log | `cohort membership NOT COMPARED - <reason> (count n)` |

**The count is printed and never asserted.** Membership subsumes it — an unchanged set has an unchanged size — and the set says *which* name moved, which a count never could.

### 2.4 Verification

**`--selftest`: 30/30 ALL PASS** (17 before, 13 added, 3 of them negatives).

The case that justifies the design is 6d: an **equal-size swap**. `{AAPL, MSFT, GM}` → `{AAPL, MSFT, USO}` holds n constant at 3, so the retired `EXPECTED_N` check would have passed it in silence. The set-difference names both sides.

**`edgar_parser_audit.py`: PASSED at exit 0** with the patched file in place — the gate the 8/03 change order set.

**Retro-run against the real logs** — the strongest evidence, because it is the event the 8/18 entry recorded as invisible to every tool:

```
--- 2026-08-18 ---  [FAIL] cohort membership CHANGED since 2026-08-17 (26 -> 25 names) - REMOVED: GM
--- 2026-08-19 ---  [FAIL] cohort membership CHANGED since 2026-08-18 (25 -> 26 names) - ADDED: GM
--- 2026-08-20 ---  [OK  ] cohort membership UNCHANGED since 2026-08-19 (26 names; count 26 vs 26)
--- 2026-08-21 ---  [OK  ] cohort membership UNCHANGED since 2026-08-20 (26 names; count 26 vs 26)
```

**Run-integrity findings on 2026-08-21 fall 2 → 1.** The survivor is `[FAIL] D.op == B.blend_op 23/26`, documented noise on a DESCOPED channel, still owed a rephrase as informational.

---

## 3 · `monitor_strip.py` — which channel, and which basis

The 8/20 review's finding #2 asked for one thing: *"Make the monitor strip state which channel it scored."* It now states two, because looking for the first surfaced the second.

**Channel.** `ws2_episodes()` reads `x["conf"]`, which is the tracker's `Conf %` = `json.confidence` = **`D.op`, post-damping**. G1's FAIL condition is *"model-side remedy class exhausted at 3-B"*, and D1 is not the remedy under test — so the channel that **answers** G1 is the raw one. The strip now says which it used and points at `h1_lag_trace_<TK>_raw_3B.md` for the other.

**Basis.** The detector walks `ser[i-5]["p0"]` — five **tracker rows** off **Price at Signal** — while importing **THETA from `risk_engine`**, which damps on five **market sessions** off **closes**. Two definitions of "trailing five-session move", one threshold applied across both. On 2026-08-21 they gave GM **opposite signs**: the exhibit reads −0.31%, the run reads +2.75%, because GM's missing 2026-08-18 row moves the exhibit's t−5 anchor from 8/14 to 8/13.

Nothing turns on it today — WMT is far past −5% on both bases and GM far short on both. **It turns on it the first time a tracer sits near −5% and the two bases straddle it**, which is a question to settle before n = 4, not at it. Both the strip and the `h1_lag_trace` exhibits now carry the disclosure; **neither tool's numbers change.**

Regenerated and reproduced exactly: 2 post-deploy episodes in 34 sessions, GM 0 in 33, H4 57% (13/23, 29 total), KEEP-70 48.8% (21/43), registry 49, band splits identical.

---

## 4 · `implied_return.py` — a provenance claim that was false, and the evidence that settled a `[?]`

### 4.1 The false claim

§1 stated: *"px(quote) is shown as DRIFT ONLY. Every derived figure uses px(master), the record's Price at Signal, so there is exactly one price source."*

§5 computes `trail = r["qpx"] / r["eps"]` — the **quote** price. Checkable on the exhibit's own face:

| name | px(master) / eps | §5 prints | px(quote) / eps |
|---|---|---|---|
| WMT | 102.36 / 2.73 = 37.49 | **37.94** | 103.5892 / 2.73 = **37.94** |
| GM | 86.69 / 3.27 = 26.51 | **26.82** | 87.70 / 3.27 = **26.82** |

**The behaviour is right and the claim was wrong.** §5 exists to compare px/eps against Schwab's `peRatio`, and that field is struck on Schwab's own price; matching the basis is what makes the ratio mean anything, and using px(master) would inject a spurious drift term into the very quantity being read.

§1 now scopes its claim to sections 1–4b and names §5 as a documented exception with its reason. **A blanket provenance claim that is false in one place is worse than no claim at all — it is exactly the sentence a reader uses to stop checking.**

### 4.2 The `peRatio` natural experiment, landed in the exhibit

| field | 8/18 | 8/20 | 8/21 | 8/20 → 8/21 |
|---|---|---|---|---|
| WMT `eps` | 2.73 | 2.73 | 2.73 | **0.00%** |
| WMT `lastPrice` | 115.21 | 103.97 | 103.59 | −0.37% |
| WMT `peRatio` | 40.45 | 40.237 | 36.555 | **−9.16%** |
| implied denominator | 2.848 | 2.5839 | 2.8338 | **+9.67%** |

A trailing P/E would have moved −0.37%, with the price. Across every cohort name with a positive implied denominator that session, WMT's +9.67% is nearly **three times** the next mover (NKE +3.35%), and WMT is the only name with an earnings event in the window.

**`eps` is static last-fiscal-year; `peRatio` carries a forward, analyst-maintained denominator.** The `[?]` is **left standing** — its own stated resolution was Schwab's field reference for the `fundamental` block, and that document is still unread. Confirming a reading by experiment is not reading the documentation.

The exhibit also now warns that a §5 row is a statement about **denominator freshness**, not about a business: WMT was 'expected DOWN' on 8/20 (ratio 1.057) and 'expected UP' on 8/21 (0.963) on a −0.4% price move.

### 4.3 Verification status — stated honestly

The change is **text only**: five `out()` emissions with no interpolation and no new names. It compiles, `out()` has taken a default argument since it was written, and the two factual claims in the added text were derived independently from `quote_dump_*.json` and the master before being written into the tool.

**It has NOT been exercised on a live cache run**, because this container has no `edgar_cache`. The operator's next `value.bat` is its first live run — and per this project's own maxim, *the first live run of anything is where the defects are, not the test suite.*

---

## 5 · Side effects checked

- **`retired_criteria_audit.py`: 58 → 60 flagged lines.** Both additions are comments in `monitor_strip.py` and `h1_lag_trace.py` that name **G1 accurately as a live gate**. G1 is not retired, so a flagged mention is correct behaviour, and no wording clears it (`retired` / `closed` / `suspended` / `context only`) without misstating its status. Exit 1 is the pre-existing state of this audit, not a regression.
- **`edgar_parser_audit.py`: PASSED, exit 0.**
- **No tool's numbers changed** except the four corrected display values in §1.3.
- Nothing touches the prompt, `risk_engine`, `edgar_client`, the ±3% band, the frozen E4-2 tier table, KEEP-70, H4 or any E4 endpoint.

---

## 6 · Commit backlog

Now also carrying `h1_lag_trace.py`, `signal_scan.py`, `monitor_strip.py`, `implied_return.py`, and this memo, on top of the items outstanding from 8/20.

*Advisory-only · no orders · not financial advice.*
