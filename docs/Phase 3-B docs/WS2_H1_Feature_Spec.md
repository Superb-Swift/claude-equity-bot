# WS2 — H1 Feature-Level Implementation Spec

*Claude Equity Bot · Phase 3-B Session 1 · drafted 2026-07-06 from repo @ `134a7d6` (tonight's closeout push) + `signals_2026-07-06.log`. Companion to `Phase3B_Kickoff_Prompt.md` §WS2 and `Phase3A_Closeout_Memo.md` §4. Advisory-only; not financial advice.*

---

## 0 · Provenance finding — the H1 box CLOSES (assumption CONFIRMED)

The locked verdict carried one open box: *does variant "A" include the H1 prior-5-day price input?* Evidence assembled this session:

| # | Evidence | Source | What it shows |
|---|---|---|---|
| 1 | `_build_price_history_section()` + the PRICE TRAJECTORY (H1) system-prompt block | `claude_signal.py` @ `134a7d6`, L26–100 / L165–188 / L269 | The live prompt contains the 5 prior completed daily closes **and** a computed trailing % change, plus the H1 phrasing |
| 2 | Last code change = the go-live commit | `git log` on `claude_signal.py`, `main.py`, `schwab_client.py` → `246494e`, 2026-06-15 19:00 CDT, "Phase 3-A go-live" | The generator was frozen from go-live through the 7/6 close (tonight's closeout commits touched no code) |
| 3 | Runtime proof on the final session | `signals_2026-07-06.log` (e.g. L303–304) | Per-ticker Schwab `pricehistory` GET + "Prior 5 closes loaded for H1 trajectory" — the input was fetched and fed live, all 24 tickers |
| 4 | Before/after | `Phase 3A Files/claude_signal.py` (pre-go-live snapshot) vs root | The H1 input + phrasing (and the H3 stability block) are exactly the go-live prompt change |

**Ruling: the box closes CONFIRMED — variant "A" included the H1 prior-5-day input (numeric + phrasing) throughout the run. Verdict (b) stands exactly as signed: remedy deployed, lag unchanged at 5 sessions.**

> **PROVENANCE CAVEAT (recorded, immaterial).** Commit `246494e` is timestamped 19:00 on 6/15 — after that morning's 09:33 run. The 6/15 AM prompt state is not git-provable and the 6/15 log is not on hand; 13 of 14 sessions are provable (frozen tree + 7/6 runtime), and the 6/15 analyst-notes entry describes the go-live work same-day. No bearing on the verdict.

> **SECONDARY OBSERVATION (record only).** The go-live prompt also folded the H3 stable-thesis text into the base build (code comment: *"A" = the current build (H1 + H3)*), with H2 kept as the untested B-arm addendum. The H3 language therefore ran live all of 3-A, uncontrolled — consistent with the closeout's "stable-thesis prompt never tested" (no A/B → no causal read), but it means the measured 3.5% flip baseline is a baseline *under* that text. Note also the built-in tension: the H3 block asks for confidence stability absent catalysts, which plausibly pulls against H1 responsiveness. Acting on that would be a prompt-level A/B — a retired remedy class, descoped. Observation only.

---

## 1 · Consequence — the kickoff's WS2 Lever 1 is already deployed

Kickoff WS2 mandate: *"add a mechanical trailing 5-day return input to the signal context (numeric, computed — not prompt phrasing)."* Section 0 shows that input has been live since go-live — it **is** the remedy the locked verdict scored ineffective (lag 5, unchanged, every cohort). Re-deploying it is a no-op, and the pre-registered acceptance test would simply re-measure the status quo.

**The input-side remedy class "show the model the number" is exhausted at 3-A level, alongside phrasing.** WS2 therefore pivots to the two genuinely untried levers below. Both are mechanical, numeric, and computed; neither adds persuasive phrasing; neither reads or relies on confidence-band ordering (T3 ✓).

---

## 2 · Lever B — prior-signal state input (model-side; the honest H1 implementation)

**Premise.** Every call is stateless: the model cannot see that *its own confidence has not moved* while price fell 10%. The lag may persist not because the model can't see the move (§0 — it can) but because it can't see its own staleness. Lever B feeds back per-ticker prior-output state — the last untried information channel at feature level.

**Feature definition.**
- `prior_signals(ticker)` = the last 5 sessions' `(date, signal, confidence)` for the ticker, from the bot's own outputs.
- Derived deltas presented alongside: net confidence change over the span (pts), juxtaposed with the trailing price change the model is already shown.

**Prompt insertion (mechanical — no exhortation).**
- New builder `_build_prior_signal_section(prior_signals)` in `claude_signal.py`, wired immediately after the trajectory section (after the L269 call in `get_signal`).
- Rendered block (example, WMT-shaped):

```
--- YOUR PRIOR SIGNALS (this ticker, last 5 sessions) ---
2026-06-29: HOLD 52% | 2026-06-30: HOLD 52% | 2026-07-01: HOLD 45% | 2026-07-02: HOLD 45% | 2026-07-06: HOLD 52%
Net confidence change over span: +0 pts | Trailing 5-session price change: -5.05%
```

- SYSTEM_PROMPT gains **one schema line** in the "You will receive" list: `- Your own prior 5 sessions' signals and confidences for this ticker (when available)`. Input documentation only — no new behavioral language (phrasing remedies are retired).
- Cold start: renders `(no prior-signal state available)` — degrades like the trajectory section.

**State persistence.**
- `signal_state.json` in repo root (gitignored — runtime data): `{ticker: [{date, signal, conf}, … last 5]}`.
- `main.py`: load at run start → pass `prior_signals` into `get_signal` → append today's outputs → write back at run end.
- **Seeding:** one-time backfill from the tracker Signals tab (`seed_signal_state.py`, ~25 lines; `data_only=True`, dynamic row scan per convention) so day 1 post-deploy is warm and the acceptance clock starts immediately.

**Log marker.** Append `S1[prior=52,52,45,45,52; dconf=+0]` after the existing `H1[...]` tag — the parser ignores trailing tags by the same pattern (verify tolerance in the smoke run).

**Era stamp.** `prompt_variant` "A" → **"A-S1"** at deploy. Single live arm continues; the label is a generator-version stamp, not an experiment arm. It flows via `signal["prompt_variant"]` into the Signal JSON on every log line; recommend also bumping the bracket tag to `[PHASE 3-B ADVISORY]` (the 6/15 analyzer fix made the phase regex agnostic — confirm in smoke).

**Risks (pre-registered).** Feeding prior confidence could *anchor* (stickier confidence, lag unchanged or worse) — that is exactly what the acceptance test measures; the kickoff's failure clause applies. Mild self-consistency pressure also interacts with the live H3 stability text — again measured, not assumed.

> **Basis footnote (declared once so nobody reconciles the two numbers later).** The model-visible trailing change is computed over the 5 prior *completed closes* — i.e., 4 close-to-close intervals ending at T−1 (the "5-day change" label in `_build_price_history_section` is off by one; cosmetic fix optional). The meter (`h1_lag_trace.py`) computes a true 5-session span on the *signal-capture* price series ending at T. Second-order skew at integer-session lag resolution; recorded here.

---

## 3 · Lever A — mechanical confidence damping (post-model; deterministic)

**Premise.** Stop waiting for the model: if the trailing move is materially adverse to the stance and conviction hasn't updated, damp it mechanically. This is an engineering fix, not a hypothesis test.

**Rule (proposed defaults — tunable; sized on the locked WMT arc).**

```
trail   = trailing 5-day % change already computed for the prompt (the number the model saw)
adverse = (signal in {BUY, HOLD} and trail <= -THETA) or (signal == SELL and trail >= +THETA)

if adverse:
    damp    = min(CAP, K * (abs(trail) - THETA))
    conf_op = max(FLOOR, conf_raw - round(damp))
else:
    conf_op = conf_raw

THETA = 5.0   # % move before damping engages
K     = 1.5   # confidence pts per % beyond THETA
CAP   = 15    # max damp per session
FLOOR = 35    # keep clear of the 0-conf parse-error convention
```

*Sizing sanity:* WMT held 52–55% through trail −9.99% → rule yields damp ≈ 7.5 → 55 → 47/48, within ~2 pts of the model's own eventual 55 → 45 catch-up step — the "correct" update in one session instead of five.

**Placement.** `apply_conf_damping(signal, price_history) -> (signal, meta)` in `risk_engine.py` (policy home); called at the top of `handle_phase3a`, **before** `evaluate_signal` — risk, print, log, and tracker all see the operative confidence.

**Logging (integrity — non-negotiable).**
- `signal["confidence"]` ← `conf_op` (operative; downstream truth for bands, registry, the 70% gate).
- `signal["confidence_raw"]` ← `conf_raw` (retained inside the Signal JSON blob on the same line).
- Append tag `D[raw=68; op=61; trail=-7.2%; th5/k1.5]` after the `H1[...]`/`S1[...]` tags.
- The raw series stays measurable → "the model still lags" remains auditable at any time.

**Interactions declared.**
- **70% gate:** damping only lowers confidence → it can convert a ≥70% BUY into a 60s near-miss during an adverse slide. That is the lever working as intended (don't escalate conviction into a 5-day slide). The registry reads operative confidence; raw is retained. KEEP 70% itself is untouched.
- **Monitors:** operative confidence is what all monitors read; the era stamp lets every monitor stratify pre/post deploy.

**Tautology adjustment (pre-registered).** On `conf_op` the lag test passes by construction (`conf_op` is a function of `trail`). If Lever A deploys, the informative endpoints shift:
- **E1** — `conf_raw` lag: expect ~5; the finding stands and stays auditable.
- **E2** — quality-no-worse: over the acceptance window, the WMT/GM trace-table read and +5d hit behavior on `conf_op` must not degrade vs raw (descriptive read; no band-ordering reliance).
The lag ≤ 2 criterion is reported on `conf_op` for the record but is not the informative endpoint under Lever A.

---

## 4 · Acceptance test — criterion unchanged, read operationalized

Pre-registered (kickoff): **estimated lag ≤ 2 sessions, sustained over ≥ 4 live cohorts post-deploy; WMT primary tracer, GM secondary; if unmoved → the remedy class is exhausted at 3-B level — record and move on.**

Operational read (per the script's own small-n note):
- **Primary evidence at n < 8:** the trace-table read — in each of ≥ 4 consecutive post-deploy cohorts, confidence responds within ≤ 2 sessions to a material trailing move. (This table read is how lag 5 was established in the first place.)
- **Confirmatory:** `python h1_lag_trace.py --since <deploy> --ticker WMT` (and `--ticker GM`) once post-deploy rows reach ~8–10 — the corr scan needs ≥ L+3 pairs at each L, so a 4-row slice returns n/a at high L by design.
- **Live context favors a fast read:** WMT is mid-episode (trail −5.33% at 7/2, confidence at 45) — new adverse or recovery legs give the table read material quickly.
- Under Lever A: report on `conf_op` for the record; E1/E2 (§3) are the informative endpoints.

---

## 5 · Sequencing recommendation + rulings needed

**Recommended sequencing: Lever B alone first.** Single-variable attribution; it is the last honest input-side test of the locked finding; the kickoff's failure clause already covers a miss. If B fails the read → record "model-side remedy class exhausted at 3-B" and deploy Lever A as the engineered fix under §3 endpoints. If B passes → no damping needed. Lever A stays fully specced and ready either way.

**Ruling R1 (scope).** Lever B is a *substitute* feature-level candidate under the locked H1 disposition ("carry the finding to 3-B as a feature-level candidate") — the disposition's named candidate (trailing-return input) turned out to be pre-existing (§1). Approving R1 gets a one-line worksheet-style record in the notes splice.

**Ruling R2 (T2 era accounting).** Post-deploy signals are a new generator era. Recommend: **T2's n ≥ 88 counts variant-A-era rows only** (6/15 → deploy). Projection: resolved 60-69 n grew 52 → 59 → 67 across the last cohorts (~7–8 per cohort); five A-era cohorts resolve 7/7–7/13, so **the depth condition is on track to be met from A-era rows alone this week**, with the lead condition already at −18.0pt (≤ −15pt) at close. Practical upshot: T2 likely fires mid-week *regardless* of WS2 timing — stage the Tier-2E diff kit. (Projection from logged growth rates; the monitors decide.)

---

## 6 · Constraints check

- **Advisory-only, no orders** — unchanged; neither lever touches execution. T1 untouched.
- **T3** — neither lever reads or relies on band ordering. ✓
- **KEEP 70%** — threshold unchanged (Lever A interaction declared in §3). ✓
- **Descopes stay descoped** — no prompt A/Bs; the single live arm continues under a new era label. ✓

---

## 7 · Implementation checklist (ready to code on R1)

**Lever B batch:**
1. `claude_signal.py` — add `_build_prior_signal_section`; extend `get_signal(..., prior_signals=None)`; wire after the trajectory section; +1 schema line in SYSTEM_PROMPT; variant label → "A-S1" at deploy.
2. `main.py` — load/save `signal_state.json`; pass `prior_signals`; append `S1[...]` tag in `handle_phase3a`; phase-label decision (`[PHASE 3-B ADVISORY]`).
3. `seed_signal_state.py` (new, ~25 lines) — backfill last-5 per ticker from the tracker Signals tab.
4. `.gitignore` — add `signal_state.json`.

**Lever A batch (held until triggered):**
5. `risk_engine.py` — `apply_conf_damping()`.
6. `main.py` / `handle_phase3a` — call + dual-confidence logging + `D[...]` tag.

**Smoke plan.** Deploy on a **PM diagnostic run** (PM = diagnostic-only per convention): verify 24/24 parse, `S1` tag present, Signal JSON carries "A-S1", parser/analyzer unaffected (trailing-tag tolerance), state file round-trips. Go live next AM. First acceptance read at deploy + 4 cohorts.

---

*Advisory-only · no orders · not financial advice.*
