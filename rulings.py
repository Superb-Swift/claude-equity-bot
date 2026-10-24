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

2026-09-30 UPDATE
    Transcribed DP-3C-ax (ruled by Rob, 2026-09-30) from
    claude/Phase3C_AbsenceGap_PreRegistration_2026-09-30.md §5.3: G1's
    trailing window is five NYSE sessions, not five tracker rows. Registry
    only -- the tools that measure the window change after 2026-10-06.

2026-10-12 UPDATE
    Transcribed DP-3C-ay (ruled by Rob, 2026-10-09) from
    claude/Phase3C_Ruling_DP-3C-ay_2026-10-09.md: Phase 3-C stays open until
    E4-3 reaches 20 events on its pre-registered definition (backstop
    2026-11-20), and every E4 endpoint is read once at the exit. The note
    carries the same-day count correction (10 of 20, from e4_counter.py).
    Registry only -- no tool's behaviour changes; e4_counter.py reads no
    ruling from here.

2026-10-22 UPDATE
    Transcribed DP-3C-az..DP-3C-bk from
    claude/Phase3C_Rulings_Delegated_2026-10-22.md. Ruled by Claude under
    Rob's delegation of 2026-10-22 ("make the best practice decisions when
    deciding rulings earned"); each is marked DELEGATED and is reversible by
    Rob at any time, with no evidence to wait for. DP-3C-bk is Rob's own
    decision (the watchlist change deferred to the exit), transcribed.
    Adds read_protection() (DP-3C-bb, R1): the one rule every one-time
    reading must pass before it is recorded. DP-3C-w and DP-3C-am carry
    dated notes; their status lines are unchanged except where ruled.

2026-10-23 UPDATE
    DP-3C-bk amended: Rob's reason recorded verbatim; the deferral
    re-examined under the 10-22 delegation and kept; the 10-22 note's list of
    measurement roles corrected (GLD and SNOW were missing); and a
    `measurement_only` tuple that value_card.py reads to label those names on
    the decision card (reporting only).

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

# The 2026-10-22 delegated ruling set (DP-3C-az..bk).
DOC_1022 = "claude/Phase3C_Rulings_Delegated_2026-10-22.md"

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
            "the Phase 3-C exit review. "
            # extended 2026-10-22 (DP-3C-bl): provenance, recorded not rewritten
            "PROVENANCE (DP-3C-bl): the 2026-10-13 reading (NOT DECIDED, rho "
            "-0.334, n 10) was recorded 2026-10-13 15:37:12, BEFORE its resolving "
            "close (BBWI 2026-10-13) had been carried by a later log; it was "
            "verified 2026-10-14 against that log (BBWI 18.00 = 18.00), so the "
            "reading stands. The exit re-read goes through read_protection() "
            "(DP-3C-bb) and is recorded as instrument 'DP-3C-w@exit'."
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
        status="D9 DONE 2026-10-22 (master closes = official unadjusted closes; the log channel can be back-adjusted); D6 DEFERRED (API cost is Rob's call)",
        open=True, ruled_on=dt.date(2026, 9, 16), effective=dt.date(2026, 9, 16),
        doc="claude/Rulings_DP-T1_and_DP-3C-af-am_2026-09-16.md",
        bar="D9: four closes (AAPL, PM, SCHD, MSFT) checked against an external source",
        note=("AMENDED 2026-09-25: MSFT added to D9 after two machine-vs-source "
              "disagreements in three sessions (09-15, 09-17). The MSFT 09-15 "
              "repair stays ON HOLD until D9 is done. "
              # extended 2026-10-22, recorded not rewritten
              "2026-10-22 [R: outcome_close_repairs.log 09:22-09:39]: the MATERIAL "
              "queue was repaired against external closes (GM 08-20 86.15, NVDA "
              "07-23 208.76, 08-07 223.96, 06-18 210.69) and JPM 07-02 by the "
              "dividend identity (master 332.97 = log 334.47 - 1.50 dividend). "
              "D9 SPOT CHECK, 2026-10-22 (claude/Phase3C_Rulings_Delegated_"
              "2026-10-22.md section D9): master sessions agree with an external "
              "official Close on AAPL 65/65, SCHD 49/49, SND 65/65, PM 1/1 and "
              "MSFT 20/21 (the one miss, 10-19, is the aggregator's: master and "
              "log both 533.52). AG 2026-09-16 18.38 is wrong (external 18.33 = "
              "the machine close) and is repaired. FINDING: the master holds "
              "official UNADJUSTED closes; the log's H1 series is unadjusted for "
              "regular dividends (JPM, SCHD) but was BACK-ADJUSTED for SND's "
              "~07-28 distribution. Source precedence: DP-3C-bd. D9 is closed; "
              "the entry stays open for D6."),
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
    "DP-3C-ax": dict(
        dp="DP-3C-ax",
        question="G1 trailing windows across missing sessions (bot-absent days, run-fault dropouts)",
        status="RULED (Rob) — G1 window = 5 NYSE sessions; no row at the base = NOT EVALUABLE",
        open=False, ruled_on=dt.date(2026, 9, 30), effective=dt.date(2026, 9, 30),
        doc="claude/Phase3C_AbsenceGap_PreRegistration_2026-09-30.md",
        bar="unchanged: read at n = 4 pooled evidence episodes; >= 1 responding <= 2 sessions",
        note=("Amends DP-3C-an's window from 5 tracker rows to 5 NYSE sessions "
              "(trading_calendar); channel (RAW), basis (Price at Signal) and read "
              "point unchanged. Record-neutral when ruled: all 4 post-deploy "
              "episodes unchanged. Ruled before the 2026-10-01 / 10-05 bot-absent "
              "sessions and before any affected row existed. Code "
              "(monitor_strip.ws2_episodes, h1_lag_trace trailing series) changes "
              "after 2026-10-06; until then tracer rows 2026-10-02..10-12 are "
              "re-checked by hand before any G1 count."),
    ),
    "DP-3C-ay": dict(
        dp="DP-3C-ay",
        question="Phase 3-C exit timing: read E4-3 INSUFFICIENT now, or hold the exit for it",
        status="RULED (Rob) - Phase 3-C stays open until E4-3 reaches 20 events; all E4 endpoints read once at the exit",
        open=False, ruled_on=dt.date(2026, 10, 9), effective=dt.date(2026, 10, 9),
        doc="claude/Phase3C_Ruling_DP-3C-ay_2026-10-09.md",
        bar=("E4-3: 20 events on its pre-registered definition, backstop 2026-11-20 (then INSUFFICIENT); "
             "E4-2 read on every ADJACENT row resolved by the exit date; DP-3C-ai freeze runs to the exit"),
        note=("Ruled with E4-2 at 160/150 by count and E4-3 at >= 12 events (lower bound), "
              "no endpoint rate computed. Sub-items (i) backstop 2026-11-20 and (ii) E4-2 "
              "read on all rows resolved by the exit date proposed and confirmed by Rob "
              "the same day, before any arm rate existed. "
              # extended 2026-10-09 (later): count correction, recorded rather than rewritten
              "Count corrected the same day by e4_counter.py: E4-3 10 of 20 on the "
              "pre-registered definition (the >= 12 included GLD, tier T-B, and NKE 10-01, "
              "unobservable); expected exit ~2026-11-13..18; the backstop may bind."),
    ),
    # ------------------------------- 2026-10-22, ruled under delegation --
    # Ruled by Claude under Rob's delegation of 2026-10-22. Every entry is
    # reversible by Rob; none moves an E4 bar, arm, n, threshold or the freeze.
    "DP-3C-az": dict(
        dp="DP-3C-az",
        question="G1 disposition after its Phase 3-C read (n = 4 pooled, 2026-10-21)",
        status="RULED (DELEGATED) - G1 3-C read RECORDED BESIDE 3-B's INSUFFICIENT TEST CONDITIONS; it does not amend it",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="unchanged (>= 1 of 4 responding <= 2 sessions); read once, 2026-10-21: MET (weak)",
        note=("The read is MET at n = 4 (4 of 4 at lag 0) and carries four flags "
              "toward convenience: unfailable since 09-30; tracer pooling (DP-3C-an); "
              "3 of 4 episodes are GM with -3/-3/-6 steps; the run basis disagrees "
              "on every GM episode (cross-read 0 of 1 resolved). The 3-B closeout "
              "memo forbids lowering a bar after the fact, so the 3-B disposition "
              "stands and the 3-C read is recorded beside it as 'MET (weak)'. G1 is "
              "not re-read in Phase 3-C; the strip shows the recorded read, and the "
              "run-basis cross-read is reported, never scored. Rob may instead rule "
              "that the read amends 3-B; nothing would need to be recomputed."),
    ),
    "DP-3C-ba": dict(
        dp="DP-3C-ba",
        question="data-integrity guards proposed 2026-10-20 (G-a..G-d) and R9",
        status="RULED (DELEGATED) - adopted: Check H (due-but-blank) and Check I (K..N formula and cache) GATE; enter_closes --catch-up; UNGUARDED refused",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="n/a - integrity gates on the record, not on any endpoint",
        note=("enter_closes refuses a session whose cohort is not yet in the "
              "master (paste first) and any ticker with neither content guard "
              "unless --allow-unguarded (departed names, gap sessions), and labels "
              "such cells UNGUARDED in the ledger. Workflow step 2's drag check "
              "(G-d) is now made by Check I on every scan. run_daily_review.bat "
              "warns when the previous session's value.bat or step-7 refresh did "
              "not run."),
    ),
    "DP-3C-bb": dict(
        dp="DP-3C-bb",
        question="when may a one-time reading be recorded? (R1)",
        status="RULED (DELEGATED) - only when every resolving close predates the newest cohort in the master; before that, counts only, no statistic",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="n/a - recording rule; rulings.read_protection()",
        note=("Applies to the DP-3C-w exit re-read, PR-1..PR-3, the exit reads of "
              "E4-2 and E4-3, and any future one-time arm. A close entered in the "
              "evening has not been compared with any log; the next session's log "
              "carries it and Check F compares it. Implemented in "
              "build_actionable_registry.py and discovery_scan.py."),
    ),
    "DP-3C-bc": dict(
        dp="DP-3C-bc",
        question="how the P4 gates are read, and how Phase 4 opens",
        status="RULED (DELEGATED) - P4-1..P4-5 are Phase 4 ACCEPTANCE gates; Phase 4a (no prompt change) opens at the exit ruling, 4b (prompt changes) only after its own pre-registration and E4-3",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="Phase 4 closes only when P4-1..P4-5 are met",
        note=("P4-4 and P4-5 need work reserved for Phase 4, so they cannot be "
              "entry gates. Work that does not touch what the model sees may "
              "land before the exit: P4-1 rule tests (risk_engine --selftest) "
              "and the P4-3 console fix are reporting and test code."),
    ),
    "DP-3C-bd": dict(
        dp="DP-3C-bd",
        question="which close wins when a filled cell and the next session's log disagree (R10, D9 class)",
        status="RULED (DELEGATED) - PRECISION tier: the log close wins when every log carrying it agrees; MATERIAL tier: an external official close decides, one repair at a time",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar=("PRECISION = |cell - log| > 0.0051 and < 0.05%; applied by "
             "enter_closes.py --settle-precision; MATERIAL (>= 0.05%) via "
             "repair_outcome_close.py --price with --source-note"),
        note=("Ratifies the 95-cell 'settle_precision R10' application of "
              "2026-10-22 09:22 [R: ledger], which predates this written ruling. "
              "The log close is the Schwab daily candle as carried by the next "
              "session's H1 trace, after Schwab's overnight settlement; an "
              "evening candle can still be a consolidated last trade. The log "
              "channel can also be BACK-ADJUSTED after a distribution (SND, D9 "
              "2026-10-22), so a MATERIAL item is never settled to the log "
              "without an external Close (and Adjusted Close) column read first, "
              "and --settle-precision skips any candidate whose logs disagree or "
              "that would flip a verdict (those go to D9). With the queue "
              "adjudicated, outcome_sanity Check F gates (DP-3C-bj)."),
    ),
    "DP-3C-be": dict(
        dp="DP-3C-be",
        question="where the G6 record lives (R8), and the tracked notes slice",
        status="RULED (DELEGATED) - G6 = the dated LOCAL notes master docs/analyst_notes_<date>.md (now 2026-10-09); never published; analyst_notes_current.md untracked (option A)",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="n/a - record location",
        note=("Each review's splice lands in the dated master the same session or "
              "the next; the claude/ project docs are its cited sources. "
              "docs/analyst_notes.md and analyst_notes_2026-08-17.md are frozen "
              "history. docs/analyst_notes_current.md is removed from the index "
              "(git rm --cached) and excluded locally, so a regenerated slice can "
              "never publish the master's content. A new dated master opens at "
              "the Phase 3-C exit review."),
    ),
    "DP-3C-bf": dict(
        dp="DP-3C-bf",
        question="the DP-3C-ah arms (PR-1..PR-3) against a Phase 4b prompt change",
        status="RULED (DELEGATED) - TRUNCATE: each arm's population ends the session before any 4b go-live; post-go-live rows reported separately, never pooled",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="unchanged; an arm short of its dates at its read date reads INSUFFICIENT",
        note=("Keeps every arm on the treatment it was registered on and spends no "
              "API budget. The alternative that keeps power, a frozen reference "
              "prompt run log-only beside 4b (option A), doubles calls and is "
              "Rob's budget decision; it must be decided before any 4b go-live."),
    ),
    "DP-3C-bg": dict(
        dp="DP-3C-bg",
        question="generator continuity (claude-sonnet-4-6, retirement not before 2027-02-17)",
        status="RULED (DELEGATED) - on any retirement notice, run old and new generators in parallel on identical inputs for the notice period; arms read on the old population only",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="n/a - pre-registered procedure",
        note=("The new model runs log-only; its output reaches no risk engine, "
              "paste, gate or daily view. A forced change truncates each open arm "
              "as in DP-3C-bf. Captured inputs (logs/inputs_<date>.jsonl) make "
              "the parallel run reproducible. No voluntary model change in 3-C."),
    ),
    "DP-3C-bh": dict(
        dp="DP-3C-bh",
        question="shadow calls, D6, and the gap-analysis pre-registrations (#1, #2)",
        status="RULED (DELEGATED) - a log-only shadow call is not a treatment change; #1 and #2 pre-registered now; #1 starts at Phase 4a; D6 stays DEFERRED (API cost, Rob)",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="as pre-registered in the 2026-10-22 rulings doc, sections #1 and #2",
        note=("A shadow call is outside DP-3C-ai only if its output reaches none "
              "of: the risk engine, the paste, any registry gate, Rob's daily "
              "view. #2 (baseline arm, PR-5) is counted blind from signal dates "
              "after 2026-10-22. The arithmetic-only 'advice followed' P&L is "
              "NOT ruled here: it borders DP-T1's retired X7, and DP-T1 is "
              "reopened only by Rob."),
    ),
    "DP-3C-bi": dict(
        dp="DP-3C-bi",
        question="where held/scout transition lines are recorded",
        status="RULED (DELEGATED) - in the local decision journal (logs/decision_journal.tsv), not in main.py",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="n/a - record location",
        note=("main.py is public and frozen under DP-3C-ai; a dated holding line "
              "is personal data and a code change. The journal is git-ignored "
              "and records each transition as an attribute, never a filter."),
    ),
    "DP-3C-bj": dict(
        dp="DP-3C-bj",
        question="Check F gating, and the remaining MATERIAL items",
        status="RULED (DELEGATED) - CHECK_F_GATES_EXIT = True (its precondition, GM 2026-08-20, was adjudicated 2026-10-22); SND 07-24/07-27 retired as LOG-side adjustments (master correct)",
        open=False, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar="n/a - integrity gate",
        note=("outcome_sanity named its own condition for gating: 'Flip to True "
              "once that is settled'. A MATERIAL Check F item now turns the scan "
              "red; PRECISION items never gate. D9 (2026-10-22) found SND's two "
              "single-digit items were NOT typos: the master holds the official "
              "close (65 of 65 SND sessions agree with financialcontent.com's "
              "Close column) and the logs fetched after SND's ~07-28 ex-date "
              "carry the back-adjusted close (x0.9786; the external Adjusted "
              "Close). Both are retired through outcome_sanity's pinned "
              "VERIFIED_LOG_ADJUSTED allowlist; no master cell changes. The "
              "digit-signature heuristic is amended: on a low-priced name a "
              "proportional adjustment can move one digit."),
    ),
    "DP-3C-bk": dict(
        dp="DP-3C-bk",
        question="Rob's 2026-10-22 watchlist edit to main.py (WATCHLIST_SCOUT)",
        status=("RULED (Rob) - DEFERRED whole to the Phase 3-C exit review; main.py restored "
                "to HEAD on 2026-10-22; re-examined 2026-10-23 on Rob's stated reason: the "
                "deferral stands"),
        open=True, ruled_on=dt.date(2026, 10, 22), effective=dt.date(2026, 10, 22),
        doc=DOC_1022,
        bar=("applied at the first session after the exit ruling (DP-3C-ay), as an era "
             "change, never inside DP-3C-ai"),
        # The names the edit removes. Until the change is applied, the value card
        # labels them "thesis broken (Rob)": kept in the run for measurement only.
        measurement_only=("BBWI", "CORN", "EFA", "GLD", "NTR", "SNOW", "TWST"),
        note=("Rob's answer, 2026-10-22: 'Defer the whole change'. The edit would "
              "have removed CORN (T-A, E4-3's frozen population) and NTR (T-C, "
              "leaving the control arm at its 4-of-8 floor). Post-exit list, "
              "verbatim: GM, UNH, VHT, XLV, O, SPY, QQQ, VTI, IWM, VOE, USO, KRE, "
              "VXUS. His edited file is kept at Retired/patches/backups/"
              "main.py.edit-2026-10-22. OPEN until applied. "
              "REASON (Rob, 2026-10-23 07:48 CT, verbatim): 'The thesis for the tickers I "
              "removed earlier is broken, and that's why I changed them to include REITs, "
              "Healthcare, major index ETFs, and a single name, UNH.' "
              "RE-EXAMINED 2026-10-23 (DELEGATED): the reason is a portfolio reason; the "
              "cost of removing the names before the exit falls on the measurement, which "
              "it does not change. CORN supplied 1 of the 15 E4-3 events (2026-09-24); NTR "
              "keeps T-C at 5 of 8 (floor 4); GLD is in the frozen tier table (DP-3C-ai); "
              "SNOW and NTR are 2 of DP-3C-w's 8 tickers; TWST and EFA carry no role. "
              "CORRECTION to the 10-22 note: it named CORN and NTR only. Rob may apply the "
              "whole change, or the additions alone, at any time."),
    ),
    "DP-V4": dict(
        dp="DP-V4",
        question=("the value card's class basis: Schwab's last-fiscal-year ROE, or 12-month ROE "
                  "from SEC filings"),
        status=("RULED (Rob) - the class reads 12-month ROE (SEC filings, point in time); the "
                "DP-V2 ledger is rebuilt on it from 2026-08-24 and the last-FY ledger CLOSED, "
                "never pooled"),
        open=False, ruled_on=dt.date(2026, 10, 24), effective=dt.date(2026, 10, 24),
        doc="claude/DP-V4_ValueCard_TTM_2026-10-24.md",
        bar=("unchanged: the 2.00x / 1.50x lines, r = 9%, g = 3%, and DP-V2's bar (12 flip rows "
             "on 3 tickers by 2026-12-31, else withdrawn)"),
        note=("Rob, 2026-10-24 11:23 CT, verbatim: 'what the project needs is the most "
              "informative version possible ... The goal of the valuation card is to provide an "
              "under the hood view of the vehicle and help inform a buy, hold, sell decision "
              "from the user.' Asked how to build it, he chose 'Full build now (Recommended)' "
              "in the same conversation. "
              "DEFINITIONS, fixed here before anything further was read: ROE = 12-month net "
              "income / shareholders' equity at the latest period end (ttm_eps.read_name's "
              "rule); fallback tags only labelled; no 12-month figure -> NO READ, never a "
              "last-FY fallback; point in time: the card reads filings made on or before its "
              "date, the DP-V2 ledger only filings made BEFORE the session (the BUY was decided "
              "that morning); rebuilt rows count (each uses only what was public before its "
              "session and the exhibit written that day); robustness = the r 7/9/11% grid on "
              "this basis plus the distance to the nearest line; the last-FY class is printed "
              "for reference only. The forward panel (Finnhub's adjusted consensus) is context "
              "and never enters the class or the ledger. "
              "AMENDS DP-V3 (2026-10-22): TTM is no longer only context beside the class. "
              "KNOWN WHEN RULED (counts, no outcome): on the 12-month basis the ledger reads 6 "
              "rows, all FTI REJECT->ADMIT (10-15..10-23), 1 of 3 tickers; the closed last-FY "
              "ledger reads 3 (NVDA 09-14, 09-21; SPCX 10-23), all ADMIT->REJECT. Four classes "
              "change today (NVDA, SND DEMANDING->NEUTRAL; GM, FTI NEUTRAL->UNDEMANDING); SPCX "
              "becomes NO READ (no 10-K yet). The basis is chosen on B1 of the 2026-08-24 memo "
              "(written before any of these counts), not on which rows survive."),
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

def read_protection(resolution_sessions, as_of):
    """DP-3C-bb (R1): may a one-time reading be RECORDED now?

    resolution_sessions: the sessions whose closes the reading rests on (the
        +h resolution date of every row it scores). as_of: the newest cohort
        date in the master.

    A close entered on the evening of session S has not been compared with
    any log: the log of the session after S carries it, and Check F compares
    it there. So a reading is recordable only when EVERY resolving close is
    strictly before the newest cohort. Returns (ok, last_session). Before
    that point a caller prints counts only - no rho, mean or verdict - so an
    evening run cannot show a value that the next morning then records.

    Never raises: an empty list is (False, None), i.e. nothing to read yet."""
    sess = [d for d in resolution_sessions if d is not None]
    if not sess or as_of is None:
        return False, None
    last = max(sess)
    return last < as_of, last


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
