# Phase 3-A Kickoff — Claude Equity Bot

Phase 2 closed 2026-06-12 (read-only calibration dry run, 19 trading days,
verdicts certified at the review). This chat begins Phase 3-A development.

Attached document set:
1. **analyst_notes.md** — institutional memory, current through 6/12. READ
   FIRST. The 6/12 closing entry carries the final scorecards and review
   decisions; the full findings history is the project's source of truth.
2. **Phase2_Closeout_Memo.md** — FINAL. Authoritative Phase 2 results and the
   approved Phase 3 decisions (§5 scope, §7 sign-off).
3. **Phase2_to_Phase3_Decision_Worksheet_v5.docx** — locked verdicts. NEEDS
   the v6 edit (First Task 1 below).
4. **claude_equity_bot_tracker.xlsx** — 9 cohorts complete on both windows
   (n=216 banded). +20d outcomes fill from 6/16 — informational only, outside
   the closed verdict set.
5. **phase3_design_concepts.md** — triple-blend reference. DEFERRED to a
   Phase 3-B scoping pass, gated on 3-A calibration data. Do not implement
   in 3-A.
6. **Daily_Workflow_v2_1.docx** — Phase 2 operational baseline; a v3 update
   is a 3-A deliverable once the new inputs land.
7. **Code files** — `claude_signal.py` (prompt builder: H1 + H3),
   `main.py` (orchestration, data assembly, ticker lists: H1 plumbing + CBRS
   exclusion), `schwab_client.py` (429 backoff; price-history capability for
   H1), `parse_log_to_tracker.py` (conventions for the registry auto-gen
   script), `README.md` (architecture orientation). Add `news_client.py`
   when Path B starts; `diagnostic_2026-05-29_AM` + `_PM` when the H3 design
   starts (primary evidence for the intraday-sensitivity finding);
   `ticker_suggester.py` / `risk_engine.py` only if referenced. NEVER upload
   `.env` or `token.json` (live credentials).

PHASE 2 CERTIFIED RESULTS — do not re-litigate:
- **Q1 CALIBRATED**: 50-59% band leads at 61.3% (65/106) over 40-49% (43.1%)
  and 60-69% (50.0%); n=216; 6 of 9 cohorts confirm.
- **Q2 KEEP 70%**: locked 7-of-7 = 57.1% hit, −0.90% avg +5d; extended
  post-lock set 0-for-5, avg −6.23%; near-miss +10d 1/6.
- **+10d**: magnitude grows 8 of 9 (robust, regime-agnostic); accuracy decay
  RETIRED — 6/9 raw but 3/6 ex-shock (5/27–5/29 windows contaminated by the
  6/10 Middle East shock; 5/26–5/27 are the quiet-week inflation-unwind pair;
  5/27 vs 5/28 showed 25pt of pure path dependence around the gap).
- **H1 (update lag) — strongest finding**: WMT traced across all nine cohorts,
  +10d arc −15.19 → +4.31; ~3–5 day self-correcting lag, visible in BOTH
  directions (slow to de-rate into losses, slow to re-rate into recovery).

PHASE 3-A APPROVED SCOPE (memo §5/§7): prompt-level changes, ADVISORY-ONLY.
Hypothesis order **H1 → H3 → H2**; H4 to backlog. Risk Engine unchanged
(BUY ≥70%, SELL ≥65%, max 5%/position, max 8 positions, human approval).
Book stays ~25. Cross-asset and full stateful-thesis deferred to 3-B.

ENGINEERING WORKSTREAM (parallel, not hypothesis-gated):
- CBRS excluded from runs (Path A — worst miss in 4 of 4 cohorts).
- `commodity_context.py` + `commodity_backed_equity_context.py` (Path B —
  WASDE-validated 6/11: CORN −2.05% abs / ≈−3.7% market-relative on a
  pre-release HOLD 38%).
- Exponential backoff/retry in `schwab_client` (429 burst-position artifact).
- **Near-miss registry auto-generated from the Signals tab** — the
  hand-maintained registry drifted twice in Week 4. Known open issues it
  must resolve: the two "6/2" rows are actually 6/3 signals; seven band BUYs
  missing through 6/12 (registry should total 17: locked 7 + extended 10);
  summary needs a LOCKED (7-of-7, final) vs EXTENDED (running) split; stale
  verdict box.
- HOLD-band methodology: add market-relative or vol-scaled bands to the 3-A
  evaluation ALONGSIDE the ±3% test (kept for cross-phase comparability).

LOCKED CONVENTIONS (carry forward unchanged): +Nd = N trading days, computed
from function output, never transcribed; AM (9:30 CST) canonical, PM
diagnostic-only; closing prices for all outcomes; integrity-check the
workbook on every upload; analyst-notes discipline (dated entries, ⚠️ Analyst
Note callouts, corrections logged visibly — including yours).

FIRST TASKS:
1. **Worksheet v6** — soften the "+10d grows (4/4)" caveat to the final 8/9.
2. **Registry auto-gen script** — supersedes the open hand-fixes above.
3. **H1 design spec** — define the prior-5-day price input: format, lookback
   representation in the prompt, per-ticker vs market-relative framing,
   success criteria, and the 3-A calibration plan (run length, what
   validates, how 3-A cohorts compare cleanly against the Phase 2 baseline).

To start: confirm you've read the files, integrity-check the tracker,
summarize the Phase 3-A scope in one paragraph, and propose the H1 design
spec outline so we can work forward from it.
