#!/usr/bin/env python3
"""
rulings.py — the settled decision points, and a durable log of instrument readings.

WHY THIS EXISTS (2026-09-08)
    Two defects with one cause, both found in the 2026-09-08 closing review.

    (1) `h4_dq_threshold.py` printed "H4 WATCHDOG — DQ-conditional threshold
        (DEMOTED)" and "VERDICT: H4 REOPENS — re-scope a DQ-conditional
        threshold" on 2026-09-08. DP-3C-x had ALREADY RULED H4 PROMOTED on
        2026-09-03, effective 2026-09-01. `run_daily_review.bat`'s closing
        banner said DEMOTED too. The toolchain was presenting a settled ruling
        as an open question, and the cost is not cosmetic: DP-3C-x's promotion
        LIFTED the E4 pre-registration §4 block on any filings -> data_quality
        coupling read, so a tool still printing DEMOTED actively suppresses
        work the ruling authorised.

    (2) The same tool disclaimed its own bar: "This tool does not track prior
        readings and therefore does NOT assert that condition" — the condition
        being "two consecutive readings at n >= 12". `monitor_strip.py` carried
        the identical disclaimer ("2 consecutive required, not tracked here").
        A bar that no instrument can evaluate is not a bar; it is a note asking
        the operator to remember. The record shows exactly how that goes: on
        2026-08-13 the H4 rate bar was misquoted as 50% (imported from KEEP-70)
        and a ruling was solicited on a malformed question before being
        retracted the same session.

    THE COMMON CAUSE: nothing in the chain persists a prior reading, so every
    instrument recomputes a live verdict from today's slice alone and cannot
    know either what it read yesterday or what has since been ruled.

WHAT THIS MODULE IS, AND IS NOT
    It is a REGISTRY, not a decider. It records what was ruled, by whom, on
    what date, with the source document — so a tool can ask "is this still my
    question?" before printing a verdict on it. It contains no thresholds that
    any instrument tests against, and it moves no bar. Adding an entry here is
    transcription from a ruling document; it is never where a ruling is made.

    The readings log is likewise a record, not an evaluator. It stores what an
    instrument read on a date. `consecutive_passes()` counts a streak; whether
    the streak clears a bar is the instrument's business, not this module's.

2026-09-16 UPDATE
    Transcribed DP-3C-u..ae (2026-09-03) in full, marked KEEP-70's basis
    (DP-3C-y) and the H1 window (applied 2026-08-31) as ruled, and added
    DP-T1 (advisory permanently) and DP-3C-af..am. `--standing` prints the
    closing block the daily runners now use instead of hardcoded text.
    `record_reading` stamps source and time on every reading.

2026-09-25 UPDATE
    Transcribed DP-3C-an..aw from claude/Phase3C_Rulings_2026-09-25.md
    (ruled under the operator's delegation of 2026-09-25). DP-3C-am's D9
    list gains MSFT; D9 stays an OWED operator check.

ADDING A RULING
    Transcribe it from the `claude/` ruling document. `doc` is mandatory and is
    the audit trail: a status here with no document behind it is exactly the
    unsourced assertion the 2026-08-13 retraction was about.
"""

import datetime as dt
import json
import os
import sys

READINGS_PATH = os.path.join("logs", "instrument_readings.json")

# --------------------------------------------------------------------------- #
# SETTLED DECISION POINTS
#
# `status` is free text quoted from the ruling, not an enum, so it cannot drift
# from the document's own wording. Tools should test `is_open()` /
# `status_of()` rather than string-matching in their own bodies.
# --------------------------------------------------------------------------- #

# The date after which outcomes stop being discovery (Rob, 2026-09-16). Every
# outcome resolved on or before this date has been looked at. A prospective
# read may only use SIGNAL dates strictly after it.
DISCOVERY_CUTOFF = dt.date(2026, 9, 16)

RULINGS = {
    # ------------------------------------------------------------------ T1 --
    "DP-T1": dict(
        dp="DP-T1",
        question="terminal intent: will the bot ever place orders?",
        status="RULED — ADVISORY PERMANENTLY; no order path is ever built",
        open=False,
        ruled_on=dt.date(2026, 9, 16),
        effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="none — this is a scope ruling, not a measurement",
        note=(
            "Ruled by Rob. T1 (advisory, human decides) is the permanent "
            "ceiling, not a phase gate. No place/submit/paper order code is "
            "written; every trade is Rob's decision, taken outside the system. "
            "Phase 4 is re-scoped from execution readiness to decision-support "
            "quality: X1-X4 survive as advice-quality gates, X5 is replaced by "
            "a pre-registered decision-support yardstick, X6 (loss limit, kill "
            "switch) and X7 (paper execution) are RETIRED. Reopening needs a "
            "new ruling by Rob and the retired gates reinstated in full. "
            "advisory_guard.py enforces the no-order-path clause."
        ),
    ),
    # ------------------------------------------------------ 3-C, 2026-09-03 --
    "DP-3C-u": dict(
        dp="DP-3C-u",
        question="ledger admission and executability",
        status="RULED — admit on CHECK 5; Executability is a reported attribute, never a filter",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="revisit if PARTIAL > 25% of post-era ledger rows",
        note=(
            "EXECUTABLE / PARTIAL / BLOCKED from the log's PER-ACCOUNT field, "
            "recorded at signal time. CORRECTION 2026-09-16: the ruling text "
            "said 'every prior row -> EXECUTABLE', which contradicts its own "
            "reasoning (CHECK 6 rejected every pre-DP-3C-o directional). The "
            "field is read from the log, so pre-era rows read as logged."
        ),
    ),
    "DP-3C-v": dict(
        dp="DP-3C-v",
        question="D1-window artefacts in registry populations",
        status="RULED — registries record what was emitted; D1/D2 era column; PWR 2026-08-27 flagged D1-WINDOW",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="no split reading is taken; n far too small",
    ),
    "DP-3C-w": dict(
        dp="DP-3C-w",
        question="the confidence inversion — prospective arm",
        status="DISCOVERY QUARANTINED; PROSPECTIVE ARM OPEN",
        open=True,
        ruled_on=dt.date(2026, 9, 3),
        effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar=("POSITIVE at n >= 10 new episodes AND >= 4 distinct tickers AND "
             "rho <= -0.40; NEGATIVE at n >= 10 and rho >= 0"),
        note=(
            "Population: post-DP-3C-o BUY rows (gate-clearing and near-miss "
            "pooled), coalesced under DP-3C-m, ONE ROW PER EPISODE — the opening "
            "row. Only episodes OPENING on or after 2026-09-03 count; episodes "
            "already open on that date are discovery and never enter. The "
            "discovery sample (21 rows, 3 names, 4 episodes, rho = -0.834, "
            "resolved on or before 2026-09-02) is FROZEN and is never re-read. "
            "Expected 0.41-0.47 episodes/session; time-to-read ~21-24 sessions. "
            "READ MECHANICS (DP-3C-ah, 2026-09-16): rho is not computed until "
            "10 qualifying episodes have resolved; the first such session is "
            "the read date and its reading is recorded. POSITIVE or NEGATIVE "
            "there is the disposition; otherwise the arm is read once more at "
            "the Phase 3-C exit review."
        ),
    ),
    "H4": dict(
        dp="DP-3C-x",
        question="DQ-conditional KEEP threshold",
        status="PROMOTED — ACTIVE",
        open=False,
        ruled_on=dt.date(2026, 9, 3),
        effective=dt.date(2026, 9, 1),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="n >= 12 resolved AND hit >= 60% on 2 consecutive readings",
        met_by="18/30 = 60.0% (08-31), 19/31 = 61.3% (09-01), 20/32 = 62.5% (09-02)",
        note=(
            "Promotion authorises DESIGNING a DQ-conditional test, not passing "
            "one. It lifts the E4 pre-registration §4 block on any filings -> "
            "data_quality coupling read. It does NOT move the 70% gate and does "
            "NOT create a DQ-conditional threshold. Any such threshold needs its "
            "own pre-registration with its own n, rate and time-to-read. "
            "CAVEAT THAT TRAVELS WITH THE RULING: DQ is drifting on names that "
            "receive no treatment — the T-C dark control moved -12.5pt in HIGH "
            "share and 7 of 8 T-C names changed DQ at least once. "
            "DP-3C-ak (2026-09-16): the reading has since fallen below the bar "
            "it was promoted on (22/39 = 56.4% on 2026-09-16). No demotion rule "
            "was pre-registered and none is invented with data in view; the "
            "promotion stands, and any DQ-conditional design must cite the "
            "current reading, compare within names or frozen tiers, use the "
            "episode basis, and carry a DQ-channel stability read."
        ),
    ),
    "KEEP-70_BASIS": dict(
        dp="DP-3C-y",
        question="row basis vs episode basis for the BUY-gate registry",
        status="RULED — EPISODE basis, opening row; bar '<= 50.0% supports keeping 70'",
        open=False,
        ruled_on=dt.date(2026, 9, 3),
        effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="<= 50.0% of rejected near-miss BUY episodes paid at +5d supports keeping 70",
        met_by="ruled at EPISODE 11/20 = 55.00%, ROW 28/52 = 53.85% (both NOT SUPPORTED)",
        note=(
            "The ROW basis is printed beside it as descriptive and is never the "
            "verdict. Coalescing is DP-3C-m over consecutive COHORTS (DP-3C-ab). "
            "Does not extend to H4. A NOT SUPPORTED reading is not a reason to "
            "move the gate."
        ),
    ),
    "DP-3C-z": dict(
        dp="DP-3C-z",
        question="E4-1 pre-era baseline and disposition",
        status="RULED — stamped A-S1D1-B1 baseline; E4-1 INVALID (control shifted -12.5pt)",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="no E4-1 figure enters the exit disposition",
    ),
    "DP-3C-aa": dict(
        dp="DP-3C-aa",
        question="G1 post-deploy series after the H1 window fix",
        status="RULED — WMT 2026-08-20 response VACATED; only responses from 2026-09-01 count",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="G1 bar unchanged; corrected-channel episodes only",
        note="WMT 2026-07-23 survives recomputation and stands. GM untouched.",
    ),
    "DP-3C-ab": dict(
        dp="DP-3C-ab",
        question="coalescing across bot-absent sessions",
        status="RULED — consecutive COHORTS, not trading sessions",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="n/a — implemented once, in episodes.py",
    ),
    "DP-3C-ac": dict(
        dp="DP-3C-ac",
        question="pooling E4 endpoints across the D1/D2 line",
        status="RULED — E4-2 may pool; E4-1 may not (moot); E4-3 restarts 2026-09-01",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="n/a",
    ),
    "DP-3C-ad": dict(
        dp="DP-3C-ad",
        question="USO E4 scope",
        status="RULED — excluded from E4 (no frozen tier), as SPCX",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="ADJACENT-eligible denominator stays 13",
    ),
    "DP-3C-ae": dict(
        dp="DP-3C-ae",
        question="instrument fixes (trail label, cross-check count, blend INFO, regime bounds)",
        status="RULED — (i) points check + negative test; (ii) derived count; (iii) INFO; (iv) range FAIL, step > 0.50 WARN",
        open=False, ruled_on=dt.date(2026, 9, 3), effective=dt.date(2026, 9, 3),
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="step 0.50 is a reporting trigger; re-derive at 60+ observations",
        note="(ii) and (iii) applied 2026-09-08; (i) and (iv) applied 2026-09-16.",
    ),
    "DP-3C-s": dict(
        dp="DP-3C-s",
        question="X4: held/unheld directional asymmetry — the SELL path",
        status="DEFERRED TO PHASE 4 (decision-support quality) — recommendation only",
        open=True, ruled_on=None, effective=None,
        doc="claude/Phase3C_Rulings_2026-09-03.md",
        bar="Phase 4 gate: a demonstrated SELL-generation path on held names",
        note=(
            "Under DP-T1 this is advice quality, not capital control: a system "
            "that recommends buying and almost never recommends selling gives "
            "one-sided advice. It needs a prompt change, so it waits for Phase 4."
        ),
    ),
    "WS1_G2": dict(
        dp="WS1 / G2",
        question="blend vs base",
        status="DESCOPED",
        open=False,
        ruled_on=dt.date(2026, 7, 31),
        effective=dt.date(2026, 7, 31),
        doc="claude/Phase3C_ClosingReview_2026-08-27.md",
        bar="no live acceptance bar; reopens only on T-G2-a / T-G2-b / T-G2-c",
        note=(
            "Readings on this channel are CONTEXT ONLY and no disposition may be "
            "read from them. Recording a gate-flip is not an argument to reopen. "
            "The blend never admits a row to any ledger (DP-3C-af)."
        ),
    ),
    "H1_WINDOW": dict(
        dp="H1-WINDOW",
        question="trailing-window basis",
        status="RULED AND APPLIED — contract window; era D2 from 2026-09-01",
        open=False,
        ruled_on=dt.date(2026, 8, 27),
        effective=dt.date(2026, 8, 31),
        doc="claude/H1_Window_OffByOne_Defect_2026-08-26.md",
        bar="trail_basis_audit: a D2 log (>= 2026-09-01) whose window includes the in-progress session is a regression",
        note=(
            "Fix applied 2026-08-31; the first D2 cohort is 2026-09-01. Logs "
            "before that date are D1 and are reported as history, not findings "
            "(DP-3C-aj)."
        ),
    ),
    # ------------------------------------------------------ 3-C, 2026-09-16 --
    "DP-3C-af": dict(
        dp="DP-3C-af",
        question="which confidence channel admits a row to the actionable ledger",
        status="RULED — D.op admits; ChannelMargin records blend disagreement; never a filter",
        open=False, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="n/a — a reported attribute",
        note=(
            "The ledger records the decision the risk engine actually took, and "
            "CHECK 5 gates on json.confidence (D.op). ChannelMargin = ERASED when "
            "blend_op < gate <= D.op (MSFT 2026-08-27 and 2026-09-08 shape)."
        ),
    ),
    "DP-3C-ag": dict(
        dp="DP-3C-ag",
        question="outcome-entry safety (triage Action 8; cleanup items 5-7; D10)",
        status="RULED — Check G blocks unsettled/future cells; Check F reads every cell; enter_closes.py is the entry path",
        open=False, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="Check B tolerance unchanged (5%); sub-tolerance disagreements are INFO",
    ),
    "DP-3C-ah": dict(
        dp="DP-3C-ah",
        question="discovery cutoff and the prospective arms PR-1..PR-4 (D1, D3)",
        status="PRE-REGISTERED — PR-1/PR-2/PR-3 open and blind until their read dates; PR-4 report-only",
        open=True, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar=("PR-1: IC(dconf,+5d) <= -0.05 and t <= -2 at 144 dates; "
             "PR-2: IC(trail_skip,+20d) <= -0.05 and block-t <= -2 at 125 dates; "
             "PR-3: IC(damped) - IC(raw) >= +0.03 and t >= 2 at 144 dates"),
        note=(
            "Signal dates >= 2026-09-17, HOLD rows, close basis. Before the read "
            "date discovery_scan --progress prints counts only, never an IC. "
            "Shadow damper lambda = 0.5, fixed now, never tuned."
        ),
    ),
    "DP-3C-f": dict(
        dp="DP-3C-f",
        question="extend the filing set to 40-F/6-K foreign private issuers",
        status="RULED (DP-3C-ai) — no change through the Phase 3-C exit",
        open=False,
        ruled_on=dt.date(2026, 9, 16),
        effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="none set",
        note=("Affects AG and NTR at the valuation layer only. Changing the "
              "filing set mid-E4 would change what the treatment arm is shown."),
    ),
    "DP-3C-ai": dict(
        dp="DP-3C-ai",
        question="population and treatment parameters held through the exit",
        status="RULED — DP-3C-f, Form 4 code I, THETA = 5.0 and the frozen tier table unchanged through the exit",
        open=False, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="n/a",
        note="A sigma-scaled THETA is a Phase 4 pre-registration candidate.",
    ),
    "DP-3C-aj": dict(
        dp="DP-3C-aj",
        question="H1 instruments after the window fix (D2)",
        status="RULED — SUCCESS METRIC prints the forward sign; D1 logs are history; G1 counts corrected-channel responses only",
        open=False, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="G1 bar unchanged",
    ),
    "DP-3C-ak": dict(
        dp="DP-3C-ak",
        question="H4 standing and DQ-conditional design constraints (D8)",
        status="RULED — promotion stands; design must be within-name/tier, episode basis, with a DQ stability read",
        open=False, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="the H4 monitor stays on its row basis and is monitoring only",
    ),
    "DP-3C-al": dict(
        dp="DP-3C-al",
        question="reporting definitions (breach population, 1 - E/A label, within-name z, standing footer)",
        status="RULED — breach is HOLD-only everywhere; labels corrected; footer read from rulings.py",
        open=False, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="n/a",
    ),
    "DP-3C-am": dict(
        dp="DP-3C-am",
        question="price provenance (D9) and a wider shadow cross-section (D6)",
        status="D9 OWED (operator check) before any market-adjusted work; D6 DEFERRED (API cost is Rob's call)",
        open=True, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="D9: four closes (AAPL, PM, SCHD, MSFT) checked against an external source",
        note=("AMENDED 2026-09-25: MSFT added to D9 after two machine-vs-source "
              "disagreements in three sessions (09-15, 09-17). The MSFT 09-15 "
              "repair stays ON HOLD until D9 is done."),
    ),
    # ------------------------------------------------ 2026-09-25 ruling set --
    "DP-3C-an": dict(
        dp="DP-3C-an",
        question="which confidence channel and which trailing-move basis G1 scores on",
        status="RULED — RAW channel; TRACKER basis (5 rows off Price at Signal); run basis cross-read beside; read once at pooled n = 4",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar="unchanged: read at n = 4 evidence episodes (pooled WMT + GM); at the read, >= 1 responding <= 2 sessions",
        note=("Direction disclosed: the tracker basis gives 2 evidence episodes "
              "(both responded); the run basis would give 1 (GM 2026-09-21, no "
              "response <= 2). The tracker basis was the detection basis in use "
              "since July and was relied on by DP-3C-aa."),
    ),
    "DP-3C-ao": dict(
        dp="DP-3C-ao",
        question="departures from the dark/T-C control arm and its denominator",
        status="RULED — departures prospective; every dark-arm read reports N of 8; floor 4 names, below it the DQ-stability read is UNREADABLE",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar="T-C floor = 4 of the 8 pre-registered names",
    ),
    "DP-3C-ap": dict(
        dp="DP-3C-ap",
        question="point estimates vs surfaces; cohort statistics across membership changes",
        status="RULED — an argmax travels with its surface and margin; a cohort statistic across a membership change travels with its composition split",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md", bar="n/a — reporting",
    ),
    "DP-3C-aq": dict(
        dp="DP-3C-aq",
        question="ROE input staleness until the TTM rebuild",
        status="RULED — implied_return section 1 carries anchor age and numerator age (quarters); no figure changes",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md", bar="n/a — reporting",
    ),
    "DP-3C-ar": dict(
        dp="DP-3C-ar",
        question="a ticker the run was asked about but never wrote (run-fault dropout) in episode coalescing",
        status="RULED — absent for that ticker only: bridges, never splits; evidence-gated on the log; applies to every episode consumer",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar="n/a — population rule",
        note=("First instance MSFT 2026-09-23. Effect measured before ruling: "
              "DP-3C-w 10 -> 9 opened; actionable ledger 16 -> 15 episodes; "
              "KEEP-70 unchanged. Numbered DP-3C-ap in the 2026-09-25 weekly "
              "review by error (that letter was already proposed 2026-09-17)."),
    ),
    "DP-3C-as": dict(
        dp="DP-3C-as",
        question="gate logic that assumed BUY (ERASED; the WS1 gate-flip ledger)",
        status="RULED — signal-aware: SELL rows can be ERASED at 65; SELL gate-flips kept in a separate ledger",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md", bar="n/a — definitions",
        note="Corrects 3 rows: USO 2026-09-23, TWST 2026-09-24, TWST 2026-09-25 now ERASED.",
    ),
    "DP-3C-at": dict(
        dp="DP-3C-at",
        question="run faults vs watchlist edits; quote-fetch retry",
        status="RULED — ROW DROPPED is its own FAIL, never a membership change; one quote retry before a skip",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar="n/a",
        note="A retry changes whether a row exists, never what the model is shown: not a DP-3C-ai change; era stamp unchanged.",
    ),
    "DP-3C-au": dict(
        dp="DP-3C-au",
        question="KEEP-70 at the bar — margin and symmetry",
        status="RULED — never a state without its margin; KNIFE-EDGE when one resolution flips it; neither state moves or certifies the gate",
        open=False, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar="unchanged: <= 50.0% supports keeping 70 (DP-3C-y)",
    ),
    "DP-3C-av": dict(
        dp="DP-3C-av",
        question="per-account executability (DP-3C-u revisit condition, met 2026-09-16)",
        status="PRE-REGISTERED — per-account episode counts only; read ONCE at the Phase 3-C exit, descriptive, >= 10 resolved episodes per account",
        open=True, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25), doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar="descriptive only (DP-3C-l standard NONE); never pooled across accounts",
    ),
    "DP-3C-aw": dict(
        dp="DP-3C-aw",
        question="re-basing the damper's trailing move (owed since 2026-09-17)",
        status="PRE-REGISTERED — lands only after the Phase 3-C exit (DP-3C-ai); nothing changes before it",
        open=True, ruled_on=dt.date(2026, 9, 25), effective=dt.date(2026, 9, 25),
        doc="claude/Phase3C_Rulings_2026-09-25.md",
        bar=("adopt only if the before/after table (every D2 row; WMT 2026-07-23..08-26 "
             "window shown separately) is presented at the exit review and ruled on"),
    ),
}

def status_of(key):
    """Ruling status for one key, or None when the key is not registered."""
    r = RULINGS.get(key)
    return r["status"] if r else None


def is_open(key):
    """True when the question is still live. An UNREGISTERED key is treated as
    OPEN, deliberately: a tool must never be silenced by a missing entry."""
    r = RULINGS.get(key)
    return True if r is None else bool(r.get("open", True))


def banner(key, width=80):
    """One block a tool can print instead of re-litigating a settled question."""
    r = RULINGS.get(key)
    if not r:
        return ""
    out = [f"   RULED {r['dp']}: {r['status']}"]
    if r.get("ruled_on"):
        eff = r.get("effective")
        out.append(f"   ruled {r['ruled_on']}"
                   + (f", effective {eff}" if eff and eff != r["ruled_on"] else "")
                   + f" — {r['doc']}")
    if r.get("met_by"):
        out.append(f"   met by: {r['met_by']}")
    if r.get("note"):
        words, line = r["note"].split(), "  "
        for w in words:
            if len(line) + len(w) + 1 > width - 3:
                out.append("  " + line)
                line = "  "
            line += (" " if line.strip() else "") + w
        if line.strip():
            out.append("  " + line)
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# READINGS LOG — so "N consecutive readings" is mechanical rather than recalled
# --------------------------------------------------------------------------- #

def _load(path=READINGS_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def record_reading(instrument, cohort_date, passed, detail=None,
                   path=READINGS_PATH):
    """Append one dated reading. Idempotent per (instrument, cohort_date), so
    re-running a session's tools does not inflate a streak — which would be a
    way of manufacturing consecutive passes by re-running, and is exactly the
    failure a streak counter must not have.

    Returns the stored list for this instrument, oldest first. Never raises:
    a failed write costs the streak, not the run."""
    data = _load(path)
    series = data.setdefault(instrument, [])
    key = str(cohort_date)
    detail = dict(detail or {})
    # PROVENANCE (added 2026-09-16): which tool wrote this reading, and when.
    # A backfilled entry already carries its own `source`; a live one is
    # stamped here so a reading is never an unattributed number.
    detail.setdefault("source", os.path.basename(sys.argv[0]) or "interactive")
    detail.setdefault("recorded_at", dt.datetime.now().isoformat(timespec="seconds"))
    for e in series:
        if e.get("date") == key and e.get("pass") == bool(passed):
            # Same verdict on a re-run: keep the FIRST provenance stamp, so a
            # re-run cannot rewrite when a reading was first taken.
            for k in ("source", "recorded_at"):
                if k in e.get("detail", {}):
                    detail[k] = e["detail"][k]
    entry = {"date": key, "pass": bool(passed), "detail": detail}
    for i, e in enumerate(series):
        if e.get("date") == key:
            series[i] = entry
            break
    else:
        series.append(entry)
    series.sort(key=lambda e: e.get("date", ""))
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except OSError:
        pass
    return series


def readings(instrument, path=READINGS_PATH):
    return _load(path).get(instrument, [])


def consecutive_passes(instrument, path=READINGS_PATH):
    """Length of the current run of passing readings, counting back from the
    most recent. Counts READINGS, not sessions — a session with no reading
    neither extends nor breaks a streak, because absence of evidence is not a
    failed reading."""
    n = 0
    for e in reversed(readings(instrument, path)):
        if e.get("pass"):
            n += 1
        else:
            break
    return n


def streak_line(instrument, required, path=READINGS_PATH):
    """A one-line, quotable statement of the streak against its bar."""
    series = readings(instrument, path)
    if not series:
        return (f"   [streak] no prior readings recorded for {instrument} — "
                f"this is reading 1 of {required}")
    run = consecutive_passes(instrument, path)
    dates = [e["date"] for e in series[-required:]]
    marks = "".join("P" if e["pass"] else "." for e in series[-required:])
    return (f"   [streak] {run} consecutive passing reading(s) of {required} "
            f"required   [{marks}]  {', '.join(dates)}")


def standing_lines(width=100):
    """The closing-banner block for the daily runners (DP-3C-al).

    run_daily_review.bat and scan.bat used to hardcode their closing state
    ("H4 DEMOTED", "WMT 1 post-deploy episode") and went stale within days of
    each ruling. They now print this, which is read from the registry, so the
    banner cannot contradict a ruling that has been transcribed here."""
    out = []
    t1 = RULINGS.get("DP-T1")
    if t1:
        out.append(f"  {t1['dp']}: {t1['status']}")
    out.append(f"  Discovery cutoff: outcomes resolved on or before "
               f"{DISCOVERY_CUTOFF} are discovery; prospective reads use "
               f"signal dates after it.")
    opened = [(k, r) for k, r in RULINGS.items() if r.get("open", True)]
    ruled = [(k, r) for k, r in RULINGS.items()
             if not r.get("open", True) and k != "DP-T1"]
    out.append("  OPEN:")
    for k, r in opened:
        out.append(f"    {r['dp']:<10} {r['status']}"[:width])
    out.append("  RULED (most recent first):")
    for k, r in sorted(ruled, key=lambda kr: (kr[1].get("ruled_on") or dt.date.min),
                       reverse=True):
        out.append(f"    {r['dp']:<10} {r['status']}"[:width])
    return out


if __name__ == "__main__":
    if "--standing" in sys.argv:
        print("STANDING (from rulings.py — transcribed, never decided here)")
        print("\n".join(standing_lines()))
        sys.exit(0)
    print("RULINGS REGISTRY")
    print("=" * 78)
    for k, r in RULINGS.items():
        flag = "OPEN " if r.get("open", True) else "RULED"
        print(f"  [{flag}] {k:<16} {r['dp']:<12} {r['status']}")
    print()
    print(f"discovery cutoff: {DISCOVERY_CUTOFF}")
    print(f"readings log: {READINGS_PATH}")
    for inst, series in sorted(_load().items()):
        run = consecutive_passes(inst)
        print(f"  {inst:<24} {len(series)} reading(s), current streak {run}")
