# Phase 3-C Kickoff Prompt — EDGAR Filing Context

*Claude Equity Bot · v1.0 · written 2026-07-31 · **this document is E1's named instrument.** Provenance: `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1.docx` Part II (E1–E6) and Part III (DP-1…DP-5); `Phase3C_EDGAR_Scope_Spec.md` (the technical scope this enters into the record); `Phase3B_Closeout_Memo.md` §6–§7 (standing constraints and inheritance). Advisory-only · no orders · not financial advice.*

---

## 0 · Status and what opens this phase

**Phase 3-B is closed.** `Phase3B_Closeout_Decision_Worksheet_v1_2.docx` was signed 2026-07-31 with all six gates carrying a disposition: G5 SERVED · G1 INSUFFICIENT TEST CONDITIONS · G2 DESCOPE · G3 PARK with trigger · G4 VERDICT · G6 VERDICT. **E6 is therefore MET and Phase 3-C opens on its own terms**, not merely under the DP-5 overlap ruling — which stands but is now moot.

Three clerical corrections to the signed worksheet are outstanding (v1.3, per closeout memo §3.7). None reopens a disposition and none blocks this phase.

**The E1 prerequisite was amended at the closeout.** E1 named G3/WS3 as the technical template; WS3 was never built, and the template in fact arrived with WS1 — `context_providers.py` ships with `run_prompt_context` wired and the prompt-provider slots empty. The amendment is dated and signed. **EDGAR registers on the WS1 registry, not on a WS3 pattern.**

---

## 1 · Mandate — worksheet-entered scope

Give the model **primary-source SEC filing context per ticker**, so signals can respond to insider activity and material events rather than price and news alone.

**In scope — this and nothing more:**

| Item | Scope |
|---|---|
| **One client** | `edgar_client.py`, a `ContextProvider(mode="prompt")` appended to `REGISTRY` |
| **Filing set** | **Form 4** (insider transactions) · **8-K** (material events) · **10-Q/10-K MD&A** extracts |
| **Wiring** | Per-ticker context module on the WS1 provider registry; `main.py` calls `run_prompt_context`, `get_signal(..., extra_context="")` appends the section. **One parameter — that is the whole integration** |
| **Effect on confidence** | **None directly.** EDGAR shapes the signal through the model's reasoning. It does not touch confidence, the blend, or the risk gate |
| **Deployment** | Single live arm under an extended era stamp. The A/B program stays terminated |

**Explicitly out of scope.** Any confidence lever driven by filings (DP-4 default: filing presence does *not* feed `data_quality` in v1). Any execution capability (T1). Any change to KEEP 70%, the ±3% HOLD band, or the retired guardrail. Reviving H2, H3 or the triple blend — each descoped, each requiring its own worksheet entry. Keep scope tight; descoped items stay descoped.

---

## 2 · Coverage reality — read this before pre-registering anything

**EDGAR can reach at most 16 of the 24 watchlist names.**

| Category | n | Names |
|---|---|---|
| ETFs and commodity trusts — **no 8-K, no Form 4** | 8 | AIQ, CORN, GLD, QQQ, SCHD, SPY, VTI, XLU |
| Operating companies — SEC filers | 16 | AAPL, AG, CBRS, DOW, FTI, GM, JPM, MSFT, NKE, NTR, NVDA, PM, PWR, RTX, SND, WMT |
| **[?]** of those, domicile and form type unconfirmed | 2 | AG, NTR — may file 40-F/6-K rather than 10-K/8-K/Form 4 |

**Confident coverage: 14/24 = 58%. Best case: 16/24 = 67%.** Confirm the two `[?]` names against the CIK map before pre-registering E4 — it is a single fetch and it moves the denominator.

**This blunts the original targeting rationale, and the record already said so.** Q4-R scoped EDGAR as Option C, the input-improvement path for thin-data MEDIUM-DQ names — while noting it "helps only SEC filers … not commodities/ETFs which structurally lack filings." Quantified: of the eight heaviest MEDIUM-DQ tickers, **three have no filings at all** — CORN (39 MEDIUM rows), GLD (33), AIQ (29). Roughly 100 MEDIUM rows sit in a category the treatment cannot touch.

**The measurement consequence is the one that matters.** If E4-2 compares pre/post-EDGAR accuracy pooled across all 24 names, about a third of the population is untreatable by construction and dilutes any real effect before measurement begins. **Stratify by EDGAR coverage; do not pool.** This is the same lesson as the WS2 channel split, where pooling adverse and favourable episodes would have buried the strongest result in the project.

---

## 3 · Workstreams

*Labelled **EW0–EW3** deliberately. "WS1/WS2/WS3" have fixed meanings in the record — triple-blend, H1 feature, commodity context — and must not be reused.*

| WS | Deliverable | Gate |
|---|---|---|
| **EW0** | **Daily monitoring.** Unchanged routine: AM run → paste → resolutions → `scan.bat` → notes splice | E-gate for operational integrity |
| **EW1** | **Build.** `edgar_client.py`: CIK map, submissions fetch, cache, extraction into the prompt section | E1 |
| **EW2** | **Deploy.** Pre-deploy parser audit → PM diagnostic smoke → go-live next AM under the new era stamp | E3 |
| **EW3** | **Measure.** The E4 endpoints, read against the pre-registered rates | E4 |

**EW1 → EW2 → EW3 is strictly sequential.** The parser audit is non-negotiable and comes before go-live.

---

## 4 · Standing constraints

| Constraint | Status |
|---|---|
| **T1 — advisory only** | In force. No orders, ever. Execution is its own future gate |
| **T3 — no band-ordering reliance** | In force, tool-enforced by `retired_criteria_audit.py` |
| **Q1 guardrail** | **RETIRED** — not suspended. Q1-R diagnosed it as a calibration improvement |
| **T2** | **RETIRED.** No standing tripwire on band ordering remains |
| **KEEP 70%** | Unchanged. Near-miss BUYs that would have paid: 13/32 = 40.6% |
| **±3% HOLD band** | Unchanged and **NOT re-baselined.** Vol-scaled reporting is parallel-secondary only |
| **CBRS Path A** | Excluded to Q4 2026. **DP-3 default: EDGAR skips CBRS entirely** |
| **Watchlist** | 24 tickers. Frozen through 3-B; **reviewable at this boundary** — see DP-3C-d |
| **Blend (WS1)** | **DESCOPED.** Base signal is the official advisory output. Re-open triggers T-G2-a/b/c |
| **S1 + D1 (WS2)** | Deployed and running. G1 unresolved for want of test cases, not for want of a result |

---

## 5 · The measurement rule this phase inherits

**Both of Phase 3-B's unsettled gates failed for the same reason: the criteria required event counts the system's own output rate could not supply.** G1 needed four adverse tracer moves and the market gave one in nineteen sessions. G2's gate-flip condition needed a favourable base-vs-blend disagreement; the system emitted 32 BUY signals in 1,243 rows and produced one flip.

**Binding rule for E4, not advice:**

> Every pre-registered endpoint carries an explicit **expected event rate** and the **time-to-read** that follows from it, computed and written down **before go-live**. An endpoint whose event supply cannot deliver a read inside the phase is either rescoped or entered as a stated limitation. It is not pre-registered and discovered later.

Concretely, before E4 is signed: how many 8-K filings per month across ~14–16 covered names? How many Form 4 clusters? How many signals fall inside a K-day event window? If the answer to any of those puts a read beyond the phase, say so now.

Related and relevant: **directional signals are 2.6% of output (32 BUYs in 1,243 rows) and 78% single-name.** Any endpoint gated on BUY/SELL volume will be starved. Prefer endpoints measured on the HOLD population, which is where the data is.

---

## 6 · Entry gates — status at kickoff

| Gate | Requirement | Status |
|---|---|---|
| **E1** | Kickoff prompt with worksheet-entered scope; single `edgar_client.py`; the filing set; registry wiring | **This document.** Enter into the worksheet to close |
| **E2** | Deploy-mode ruling — era-stamp single arm vs A/B re-open | **OPEN — DP-2.** Default: single arm, `A-S1D1-B1-E1` |
| **E3** | Access path pinned; graceful degradation; log-tag convention; **pre-deploy parser audit** | Specified in `Phase3C_EDGAR_Scope_Spec.md` §1 and §5. Audit not yet run |
| **E4** | Endpoints pre-registered before go-live, with the §5 rate rule applied | **NOT DONE.** The phase's most important remaining instrument |
| **E5** | Advisory-only; T1/T3 untouched; KEEP 70% unchanged; CBRS ruled | §4 above. Compliant |
| **E6** | Part I signed before 3-C opens | **MET** — worksheet v1.2 signed 2026-07-31 |

---

## 7 · Open decision points

| DP | Question | Default |
|---|---|---|
| **DP-2** | Deploy mode | Single arm, era `A-S1D1-B1-E1` |
| **DP-3** | CBRS under EDGAR | Skip entirely until the Q4 2026 Path-A review |
| **DP-4** | Filings feed `data_quality`? | **No coupling in v1.** Measure first |
| **DP-3C-a** | MD&A: full extract / pre-summarise / recency flag | Bounded extract + filed date; no extra LLM call in v1 |
| **DP-3C-b** | Filing windows and counts | 8-K and Form 4 last 30d; latest periodic |
| **DP-3C-c** | Form-4 magnitude | Net direction plus rough size; refine later |
| **DP-3C-d** | **NEW.** The watchlist unfreezes at this boundary. Does it change, given 8 of 24 names can never receive EDGAR context? | **Propose: no change.** The ETFs are held positions Rob wants monitored; coverage is a measurement-design problem, not a population problem |
| **DP-3C-e** | **NEW.** How are cohorts stratified for E4? | **Propose: by EDGAR coverage, not by era alone.** An era stamp applied run-wide mixes treated and untreatable names and dilutes any effect by ~⅓ |

DP-1 and DP-5 are ruled and carry forward. DP-6 through DP-10 belong to 3-B and are closed.

---

## 8 · Exit clause (pre-registered now, judged later)

Phase 3-C closes when every gate below carries a disposition with evidence, on the 3-A vocabulary — **VERDICT**, **DESCOPE**, **PARK** with triggers, or **INSUFFICIENT TEST CONDITIONS** where the event supply did not permit a read.

1. **EDGAR is live or explicitly not** — `edgar_client.py` registered, era-stamped, parser audit passed, or a recorded decision not to deploy.
2. **The E4 endpoints have been read** against their pre-registered rates, stratified by coverage.
3. **Operational integrity** — cross-check streak clean through the exit review; no open data-integrity items.
4. **Instruments** — closeout worksheet drafted → signed; closeout memo written; `docs\analyst_notes.md` spliced through the final session; archive and push housekeeping.

**Explicitly not exit-blocking:** G1's episode count (3-B is closed; S1+D1 keep running); the descoped blend; execution readiness under T1; the parked Q4-2 vol-scaled metric.

---

## 9 · Session menu

Pick one per session and say which:

- **Kickoff review** — enter this scope into the worksheet; rule DP-2, DP-3, DP-4, DP-3C-a…e; close E1 and E2.
- **E4 pre-registration** — the endpoints doc, with the §5 rate rule applied. *Do this before EW1 builds anything measurable.*
- **EW1 build** — `edgar_client.py` against `Phase3C_EDGAR_Scope_Spec.md`.
- **EW2 parser audit + deploy** — E3's checklist, then PM smoke, then go-live next AM.
- **EW3 acceptance read** — the endpoints, stratified.
- **Daily monitoring** — the EW0 routine.
- **Housekeeping** — worksheet v1.3 corrections; daily-workflow v6; the carried tooling items.

---

## 10 · How I want you to work

Unchanged from 3-B and non-negotiable:

- **Conclusions first**, then evidence. Tables for comparisons, bullets for lists.
- **Explicit file naming, always.** `logs\claude_equity_bot_tracker.xlsx` is THE MASTER; `tracker_with_registry.xlsx` is the GENERATED REPORT COPY. Never a bare "tracker."
- **Read master / write generated copy.** Hard-guarded in code.
- **One git command at a time.**
- **Dated provenance and visible self-corrections.** If you were wrong earlier, say so in the record rather than quietly fixing it.
- **Identify the full blast radius** of any directional decision — dependency chains, not isolated edits.
- **Tell me when evidence is being read toward a convenient conclusion** rather than against a pre-committed standard. This has mattered repeatedly, and it mattered most when it cost me the exit.
- Verify before asserting. Compute rather than recall. Mark `[V]` verified this session / `[R]` from the record / `[?]` needs confirmation.
- CRLF for `.bat`. Idempotent sheet embeds. Open the report copy in Excel after every run — the formula cache is cleared on every openpyxl save.

---

## 11 · Cross-references

- `Phase3C_EDGAR_Scope_Spec.md` — the technical build spec: data path, extraction shape, provider signature, parser-audit checklist.
- `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1.docx` — E1–E6 as pre-registered.
- `Phase3B_Closeout_Decision_Worksheet_v1_2.docx` — signed Part I; the DP-5 ruling and the E1 amendment.
- `Phase3B_Closeout_Memo.md` — dispositions, the measurement lesson (§0, §4.2, §7), operational lessons (§8).
- `Phase3C_Session_Manifest.md` — what to upload, by session type.
- `Q4R_Scoping.md` — why EDGAR was scoped as Option C, and the coverage caveat this document quantifies.
- `docs\analyst_notes.md` — the institutional record.

---

*Advisory-only · no orders · not financial advice.*
