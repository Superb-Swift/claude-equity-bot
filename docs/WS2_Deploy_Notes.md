# WS2 Deploy Notes — S1 + D1 (Both Levers, Ruling R1)

*Claude Equity Bot · Phase 3-B Session 1 · 2026-07-06 · build base: repo @ `134a7d6` (tonight's closeout push). Companion to `WS2_H1_Feature_Spec.md` (the proposal instrument; this document records the decisions and the shipped build). Advisory-only; not financial advice.*

---

## 1 · Rulings of record (2026-07-06, session buttons)

| Ruling | Decision | Recorded implications |
|---|---|---|
| **R1 — sequencing** | **Both levers together** (spec recommended B-first) | Deployed as a **two-channel readout**: because Lever A is a deterministic post-process, `confidence_raw` carries the clean Lever-B test (did the state input move the *model's* lag?) while `confidence` (operative) carries the engineered system output. Attribution survives — **provided** the raw channel is logged on every line (it is) and the S1 state feeds the model its **raw** history (it does; feeding damped values back would contaminate the model-side channel). |
| **R2 — T2 depth counter** | **Pool across eras** (spec recommended A-era freeze) | The n ≥ 88 tripwire counts all live 60-69 rows. The *diagnosis* remains stratifiable: every post-deploy row carries the era stamp (`prompt_variant: "A-S1D1"`), so the Q1-R diff can separate generator eras post-hoc. Pooled trigger, stratifiable diagnosis. |

## 2 · Change manifest (8 files)

| File | Δ | What changed |
|---|---|---|
| `claude_signal.py` | ~42 lines | `_build_prior_signal_section()` (S1); `get_signal(..., prior_signals=None)`; wired directly under the PRICE TRAJECTORY section; one schema line added to SYSTEM_PROMPT (input documentation only — no behavioral phrasing); `print_signal` shows `op% (raw N%)` when they differ |
| `main.py` | ~85 lines | `PHASE = "3-B"`; era label `PROMPT_VARIANT = "A-S1D1"`; damping hook at the top of `handle_phase3a` (before the risk engine); `S1[...]` + `D[...]` log tags appended after `H1[...]`; phase tag now derives from `PHASE` (keeps literal "DRY RUN"); state load/pass/update/save plumbing; 3-B added to the phase routing |
| `risk_engine.py` | ~89 lines | New section: `DampingConfig` + `compute_trail_pct()` + `apply_conf_damping()`. Adds a deterministic rule that can only LOWER confidence; no existing RiskConfig rule is modified; `evaluate_signal()` runs unchanged on the operative value |
| `signal_state.py` | NEW | Raw-confidence state persistence (last 5/ticker, date-sorted, same-date last-write-wins, atomic-ish save, degrades to `{}`) |
| `seed_signal_state.py` | NEW | One-shot (re-)seed from the tracker Signals tab — warm day-1 state and the recovery path after PM diagnostic runs |
| `parse_log_to_tracker.py` | 7 lines | `ACCOUNT_RE` made phase-agnostic (mirrors the 6/15 `analyze_log` fix). **Bug caught pre-deploy:** the old alternation hardcoded `2 DRY RUN\|3-A…`, so the 3-B cutover would have silently imported every row with `Account="Unknown"` |
| `h1_lag_trace.py` | ~76 lines | `--raw-from-logs` (raw-channel reads straight from Signal JSON lines) + `--suffix` (e.g. `_raw` so channel MDs don't clobber each other); default path is **byte-identical** to the original (regression-proven) |
| `.gitignore` | 3 lines | `signal_state.json` (runtime data, re-seedable) |

## 3 · Parameters & conventions

| Item | Value | Note |
|---|---|---|
| Era label | `prompt_variant = "A-S1D1"` | Generator-version stamp, single live arm. Never bare `"B"` — both `build_system_prompt()` and the parser treat exact `"B"` as the retired H2 arm |
| Phase tag | `[PHASE 3-B DRY RUN]` | The literal "DRY RUN" is load-bearing — `analyze_log`'s regex anchors on it; the phase token is agnostic on both parsers as of this deploy |
| Damping | THETA 5.0% · K 1.5 pts/% · CAP 15 · FLOOR 35 | Sized on the locked WMT arc: trail −9.99% → damp 7 → 55 → 48 (the model's own eventual step was 55 → 45). Floor clamps but never raises |
| S1 state | last 5 sessions/ticker, **raw** conf, `signal_state.json` (gitignored) | Tracker = ground truth; state = derived cache, re-seedable any time |
| Log tags | `H1[...] \| S1[prior=…; dconf=…] \| D[raw=…; op=…; trail=…; damp=…]` | Appended fields — both parsers ignore trailing tags (proven pattern; H1 tag has ridden there all of 3-A) |

## 4 · Two calibration facts recorded (know these before reading results)

**4a — Gate-onset math (corrects an earlier test-case error of mine, not a code bug).** Damping interacts with the risk gates only past an onset threshold. With the defaults:

| Case | Crosses its gate when |
|---|---|
| BUY @ 72% vs the 70 gate | \|trail\| ≥ ~6.7% (damp ≥ 3) — at −6.5% it sits exactly AT 70 |
| BUY @ 75% vs the 70 gate | \|trail\| ≥ ~8.7% (damp ≥ 6) |
| SELL @ 68% vs the 65 gate | trail ≥ ~+7.3% (damp ≥ 4) — the CBRS-shaped case |

**4b — Acceptance-scan baseline (the important one).** The corr-scan estimator on the **3-A-only slice** (`--since 2026-06-15`, WMT, old generator, original script) already reads:

> Estimated update lag = **1 session** (peak positive r = **+0.831**)

A ~14-row, single-episode window aligns the 7/1 catch-up with the trail trough and cannot resolve onset-lateness — so **a post-deploy scan reading ≤ 2 is NOT by itself evidence of success**; the failed generator already produces it on a short slice. This is recorded so nobody later mistakes a scan pass for the win. **The operative criterion is the trace-table read** (confidence responds within ≤ 2 sessions of a *material* trailing move, in ≥ 4 consecutive post-deploy cohorts, WMT primary / GM secondary), exactly as pre-registered in the spec; the scan is confirmatory at post-deploy n ≥ ~8–10 only. The certified lag-5 finding is untouched — it is a full-series, arc-level property.

## 5 · Test evidence (sandbox, Python 3.12; build is stdlib + openpyxl, 3.14-compatible)

| # | Test | Result |
|---|---|---|
| T1 | S1 section render; era label → base prompt; `"B"` arm intact; schema line present | PASS |
| T2 | Damping table (10 cases): WMT sizing (−9.99% → damp 7, 55→48), never-raises, raw always stamped, error-code untouched, floor-never-raises, gate onset (4a) | PASS |
| T3 | State semantics: date-sorted, same-date last-write-wins, trim to 5, missing file → `{}` | PASS |
| T4 | **Seed vs the real tracker**: 24 tickers; WMT chain 52,52,45,45,45 (6/29→7/6) matches tracker + the 7/6 log; GM chain 58,52,52,52,52 | PASS |
| T5 | Synthetic post-deploy 3-B line: `analyze_log` regex extracts operative conf with S1/D tags present; NEW parser → correct Account; OLD parser → `"Unknown"` (the fixed bug, demonstrated) | PASS |
| T6 | Parser regression, real 7/6 log: old vs new **identical**, 24 rows | PASS |
| T7 | Trace regression: default path **byte-identical** old vs new (console + MD); raw-channel dry run prints explicit 0-override audit line; `_raw` MD written separately | PASS |

## 6 · Deploy runbook

1. **Replace the 8 files** in the working tree (or pull once pushed); `git diff --stat` should match §2.
2. **Seed the state:** `python seed_signal_state.py --tracker tracker_with_registry.xlsx` — expect 24 tickers and the WMT/GM chains printed as in T4.
3. **PM diagnostic smoke (today; PM = diagnostic-only per convention):** `python main.py`, then verify: banner says Phase 3-B · "Prior-signal state loaded: 24 ticker(s)" · every signal line has `[PHASE 3-B DRY RUN]`, JSON `prompt_variant: "A-S1D1"` **and** `confidence_raw`, plus `S1[...]` and `D[...]` tags · `analyze_log` parses 24 · `parse_log_to_tracker` yields 24 rows with real Accounts. **Do not paste PM rows into the tracker.**
4. **Re-seed** (`step 2 again`) — restores the AM-canonical state chain the PM run overwrote for today's date.
5. **Go live next AM.** Daily flow unchanged: paste AM rows, drag K:N, cross-check as always (the cross-check compares operative conf on both sides — consistent by construction).
6. **Acceptance reads** (post-deploy, per cohort):
   - Operative channel: `python h1_lag_trace.py --since <deploy-date> --ticker WMT` (and `--ticker GM`)
   - Raw / model-side channel (the Lever-B verdict input): add `--raw-from-logs "logs/signals_2026-07-*.log" --suffix _raw`

## 7 · Pre-registered endpoints (unchanged from the spec, restated for the record)

- **Lever B verdict input:** RAW-channel trace-table read — confidence responds within ≤ 2 sessions of a material trailing move, sustained over ≥ 4 consecutive post-deploy cohorts (WMT primary, GM secondary). Scan confirmatory at n ≥ ~8–10 (see 4b).
- **Lever A:** operative-channel lag is by construction (report only). **E1:** raw lag expected ~5 — the finding stands and stays auditable. **E2:** quality-no-worse — operative WMT/GM table + +5d behavior must not degrade vs raw over the window.
- **Failure clause (kickoff):** if the raw channel doesn't move, the model-side remedy class is exhausted at 3-B level — record and move on; Lever A keeps running as the engineered fix.

## 8 · Open items

- **Notes splice** — dated 3-B Session 1 entry (provenance-box closure, rulings R1/R2, this deploy record) ready to draft into `analyst_notes.md` on request; deploy-date placeholder resolves at go-live.
- **Optional** — one-line dated addendum at the memo's H1 row noting the provenance box closed CONFIRMED (2026-07-06 evidence: git + runtime log + archive diff).
- **T2 watch** — pooled counter likely reaches n ≥ 88 during the 7/7–7/13 resolutions with the lead at −18.0pt; stage the Tier-2E diff kit.
- **Push** — after smoke, commit as the "WS2 S1+D1 deploy" bundle (8 files + these notes + the spec).

---

*Advisory-only · no orders · not financial advice.*
