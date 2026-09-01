# Phase 3-B Kickoff — Triple-Blend Development

*Claude Equity Bot · Phase 3-B (advisory-only development) · opened 2026-07-06 on the signed Phase 3-A closeout (Worksheet v3; `Phase3A_Closeout_Memo.md`). No order execution. Not financial advice.*

## Mandate (from the 7/6 sign-off)
Build the triple-blend architecture deferred from Phase 2; implement the certified H1 lag finding at feature level; keep scope tight — descoped items stay descoped.

## Workstreams

### WS1 — Triple-blend architecture (primary)
The deferred Phase 2 design: blend the base signal with complementary inputs into a single advisory output. Session 1 deliverable: a one-page design note fixing (a) the three blend components, (b) the combination rule (weights/logic and who sets them), (c) what the tracker logs per blended signal, (d) how blended signals are evaluated against the same +5d/+10d/+20d framework. Constraint T3 applies: the design may not rely on confidence-band ordering (Q1 guardrail is suspended).

### WS2 — H1 lag implementation (feature level)
Per the locked H1 verdict: add a **mechanical trailing 5-day return input** to the signal context (numeric, computed — not prompt phrasing), with an optional confidence-damping rule as a second lever.
**Pre-registered acceptance test:** `h1_lag_trace.py` estimated lag **≤ 2 sessions, sustained over ≥ 4 live cohorts** after deploy (WMT primary tracer; GM secondary). If the feature doesn't move the lag either, the finding stands but the remedy class is exhausted at 3-B level — record and move on.

### WS3 — Q3 structural code (carryover)
`commodity_context.py` + `commodity_backed_equity_context.py` for CORN / GLD / AG (Path B); CBRS Path A exclusion switch (excluded to Q4 2026 — the 6/26 SELL miss at +14.61% is consistent with this call).

### WS0 — Operations & monitoring (background, unchanged)
Daily flow continues: post-close upload → cross-check → resolutions → registry/H4 watchdog → weekly review. The scoreboard, regime stratification, and registry now run as **monitors** — they are the sensors for the Q1-R re-open triggers. In-flight cohorts 6/29–7/6 resolve 7/7–7/13; GLD 65% near-miss +5d lands **7/9** (adds HIGH-DQ n toward H4's n≥10).

## Explicitly OUT of scope
H3/H2 prompt A/Bs (descoped 7/6 — terminated, archived); new hypotheses without a worksheet entry; anything execution-related (T1: no execution consideration while Q1-R is undiagnosed).

## Q1-R triggers carried (from the memo)
**T1** mandatory before any execution-gate consideration · **T2** at live 60-69 n ≥ 88, if non-compressed lead ≤ −15pt → run the prompt/distribution diff · **T3** before any design reliance on band ordering.

## Exit
A 3-B Closeout Decision Worksheet gets drafted once WS1 produces signals and WS2's acceptance test has ≥ 4 post-deploy cohorts — same verdict-driven pattern as 3-A.

## Session 1 menu
(a) WS2 spec: exact feature definition + where it enters the context + the damping option, ready to code · (b) WS1 design note: the three components + combination rule · (c) both, WS2 first (it's smaller and unblocks live measurement).
