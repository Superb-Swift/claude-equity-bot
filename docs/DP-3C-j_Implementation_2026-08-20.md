# DP-3C-j — IMPLEMENTED 2026-08-20

*Claude Equity Bot · Phase 3-C · seventeen days after the ruling · advisory-only · no orders · not financial advice.*

DP-3C-j was ruled **2026-08-03**: *"the EDGAR budget bounds time spent INSIDE `edgar_client` fetch/extract, not run wall clock."* The per-ticker half (`fin=degraded` distinct from `fin=none`) shipped the same week. **The timer half did not, and the record has re-observed its absence on 8/03, 8/18, 8/19 and 8/20 without it moving.** It is implemented now.

---

## 1 · What was wrong

`reset_budget()` was called once from `prefetch_edgar_context()` and `budget_exceeded()` compared `time.monotonic() - start` against `EDGAR_MAX_SECONDS`. **Every Claude signal call, news fetch and quote round-trip in the entire run was charged to a ceiling nominally allocated to EDGAR.** The 2026-08-03 measurement put real EDGAR work at ~6% of the window it was billed for.

What that cost, from the record:

| date | warning fired | names that actually degraded |
|---|---|---|
| 2026-08-03 | at JPM | 8 lost the statements block; the in-run recompute was abandoned before it cached (**F-1**) |
| 2026-08-18 | at NTR, 11th of 25, 15 remaining | **1** — CORN |
| 2026-08-20 | again | **1** — CORN, the last ticker in the order |

**CORN is the case that shows the mechanism.** It filed a **new 10-Q on 2026-08-14**. A new accession is a cold cache entry needing fetch and extract on first encounter; CORN is processed last; the budget was long gone by then; the cold extraction was abandoned every session and therefore never written. Both degraded tags carry `periodic=10-Q@2026-08-14`, which is the fingerprint.

**This was never a CORN problem.** Any covered name whose new periodic lands while it sits late in the processing order does the same thing, silently, on a quarterly cadence — and the order is not stable, because it follows the held/scouting split.

---

## 2 · What changed

### 2.1 The budget is an accumulator, not a wall clock

```python
_budget = {"spent": 0.0, "depth": 0, "t0": None, "tripped": False}
```

- **`_charge()`** — a re-entrant context manager. `edgar_context()` wraps a whole ticker and calls `_http_get()` several times inside it, so only the **outermost** span charges; nested spans are measured once, not once per level.
- **`budget_spent()`** — includes any span **currently open**. Without that term a single long fetch could pass the ceiling and never trip it, because nothing is added to the accumulator until the fetch returns.
- **`_http_get()`** is wrapped, including the throttle sleep — a rate-limit wait is time this module spends, and a ceiling that ignored it would under-count the thing it bounds.
- **`edgar_context()`** is wrapped, so **extraction and parsing count, not only network time**. That span covers nothing else, because the function does nothing else.

Measured, in the smoke test:

```
after reset            : 0.0 s
after 0.30s NON-EDGAR  : 0.0 s   <- charged before the fix, not now
after 0.10s EDGAR work : 0.1 s
OLD MODEL would have charged 0.40s   NEW MODEL charges 0.10s
```

### 2.2 The run-level warning text is retired

The old line — *"remaining tickers degrade to no-EDGAR for this run"* — asserted a run-wide consequence that the per-ticker tags in the same file contradicted on 8/18 and 8/20, when fourteen of fifteen remaining names rendered full sections from warm cache and exactly one degraded. It now reads:

> `[EDGAR] budget of 120s of EDGAR fetch/extract time is spent. Names already served from warm cache are UNAFFECTED; only a ticker needing a COLD fetch from here on degrades, and each one says so in its own fin= tag. Read the tags, not this line.`

### 2.3 A KNOWN LIMIT the code itself named is closed

`extract_financials` set `out["degraded"] = budget_exceeded()`, and its own comment said why that was wrong:

> *"if the budget happened to trip for unrelated reasons in the same window a genuinely-filing-less ticker was also fetched, this reads 'degraded' rather than 'none' — the two are not perfectly separable from here without instrumenting `_http_get` itself, which is out of scope for this fix."*

`_http_get` now records **why** it returned nothing (`budget` / `no-user-agent` / `http-NNN` / `fetch-failed`), so `degraded` names the actual cause instead of inferring it. A filer with no XBRL facts reads `fin=none` even on a session where the budget tripped for someone else — which is what DP-3C-j asked for, since a tag meaning two different things is a tool reporting a value it did not compute.

### 2.4 The budget can now state its own spend

`budget_report()`, logged from `main.py` at the end of the run:

> `[EDGAR] budget: 7.4s of EDGAR fetch/extract used of 120s (6% of ceiling)`

**The pre-fix budget could not answer the question it existed to enforce.** The 8/03 "~6%" figure was inferred from log timestamps; it is measured from now on.

### 2.5 A degraded name is now a FAIL, not something found by hand

`signal_scan` gains:

```
[FAIL] EDGAR DEGRADED on 1: CORN  ** 1 covered name(s) did NOT receive the
       statements block. These rows are in the cohort but not in the treatment.
       Warm the cache before the next run: python edgar_client.py --ticker CORN
```

Verified against the real `signals_2026-08-20.log`. `fin=degraded` has always been correct; **the problem was that nothing read it.** CORN degraded on 8/18 and again on 8/20 and both were found by hand-reading tags during review, days after the rows entered the master. A per-ticker signal nobody surfaces is a per-ticker signal nobody has. Every degraded name is a covered name that did not receive the treatment, on a measurement cohort — that is a FAIL.

---

## 3 · Expected effect, stated in advance so it can be checked

Against **~7s of real EDGAR work per run**, a **120s EDGAR-time ceiling should never trip**. If it does, that is a genuine EDGAR slowdown and worth reading — which is what a budget is for, and what this one has never been able to say.

**The check for tomorrow:** CORN should tag `fin=1@2026-06-30`, the degraded FAIL should not fire, and the run should log its EDGAR spend as a single-digit percentage of the ceiling.

**Recorded honestly: this makes the phase look better, and that is the direction to distrust.** The claim is narrow — the ceiling stops being spuriously binding. It does not make any name better covered, and §4 below is the finding that runs the other way.

---

## 4 · A blocker the record has carried for ten sessions does not exist

The 2026-08-03 change order's item (1) — *"add `signal_scan.py` to `edgar_parser_audit.py` FIRST"* — has been cited as blocking the membership check on **2026-08-18, 8/19 and 8/20**, and it is written into Daily Workflow v7.0 §6.1 and §13 as an open item.

**`[V]` It landed on 2026-08-10.** `edgar_parser_audit.py` header, verbatim:

> *"7. `signal_scan.parse_log` — the THIRD consumer of the `E[...]` tag, **added 2026-08-10** to close the gap the analyst notes flagged…"*

The audit runs it as parser [7], asserts row count, tag presence, `no filings` landing on exactly the non-EDGAR names, and — item (2) of the same change order — that **the synthetic fixture exercises all three `fin=` states** (`N@period` / `degraded` / `none`). `log_tracker_crosscheck` was added as parser [9] on 8/12. The audit passes today at exit 0.

**So the membership check has been unblocked for ten sessions and nothing noticed.** This is the same class as the 8/13 banner corrections that v6.0 still carried as open on 8/19: a resolved item restated as live because nothing re-derives the list. It is the *inverse* of the retired-criteria problem the project already audits for — a **retired blocker** stated in live-blocker grammar — and `retired_criteria_audit.py` cannot see it, because it scans for retired criteria, not for satisfied prerequisites.

**Consequence:** the hardcoded `EXPECTED_N = 24`, wrong against five successive true values, can be replaced whenever the operator chooses. The check was described as built and tested on 8/18 (5 cases, 2 negatives); it is not in the deployed `signal_scan.py`, so it is theirs to land, not mine to re-author.

---

## 5 · Verification

| gate | result |
|---|---|
| `python edgar_client.py --selftest` | **140/140 PASS**, exit 0 |
| `python signal_scan.py --selftest` | **17/17 PASS** across 6 cases, 4 negatives |
| `python edgar_parser_audit.py` | **E3 PARSER AUDIT: PASSED**, exit 0 — all four parsers |
| degraded alarm vs real `signals_2026-08-20.log` | fires, names CORN, prints the remedy |
| era alarm vs real 8/19 and 8/20 logs | FAIL on loss, WARN on recovery |

Nineteen assertions were added to `edgar_client --selftest`, covering the regression this fix exists to prevent (wall-clock time outside the module is not charged), re-entrancy, in-flight accounting, refused-fetch accounting, the retired warning text, and the degraded-vs-none separation.

**One test defect was found and fixed while writing them:** an assertion using `facts=None, fetch=False` returned before it ever reached the branch under test, so it passed without exercising anything. Recorded because **a test that cannot fail is the same defect class as a check that cannot pass** — which is the note this project already carries against the hardcoded 24.

---

## 6 · What is NOT claimed

- **No endpoint moves.** No cohort is re-read, no gate is re-scored, and the frozen E4-2 tier table is not re-cut.
- **Nothing improves coverage.** CORN and GLD remain structurally near-empty (1 and 3 statements lines, no 8-K, no Form 4). The 2026-08-20 finding on ADJACENT-eligible coverage of **13/24 = 54.2%** stands unchanged.
- **The 2026-08-18 and 2026-08-20 CORN rows are still degraded.** This prevents recurrence; it does not repair the two rows already in the master. Both are recorded, and E4-2 should carry them as a one-row treatment gap on each of those cohorts.
- **`prompt` untouched.** No change to `claude_signal.py`, `context_providers.py`, the prompt text, `data_quality`, KEEP-70, H4, the ±3% band or the risk gate. `main.py` gains one log line at end of run.

---

*Advisory-only · no orders · not financial advice.*
