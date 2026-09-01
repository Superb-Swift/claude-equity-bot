#!/usr/bin/env python3
"""
signal_scan.py - per-ticker read of ONE day's signals log.

Claude Equity Bot - Phase 3-B - advisory-only - no orders - not financial advice.

WHAT THIS IS
    A reproducible replacement for the ad-hoc per-ticker table produced during a
    monitoring session. Reads exactly one logs\\signals_YYYY-MM-DD.log and reports:
      1. provenance + run integrity (the Daily_Workflow_v6_0 section 4 checks)
      2. the per-ticker channel table (trail5d / raw / op / damp / base / blend)
      3. channel reconciliation assertions
      4. today's tracer episode CANDIDACY (single-session only - see below)
      5. cohort profile

WHAT THIS IS NOT
    It does NOT count WS2/G1 episodes. Episode counting requires coalescing across
    the full post-deploy series, which h1_lag_trace.py already implements and which
    has already been debugged once (the 7/27 correction, post-deploy 2 -> 1).
    Two tools emitting an episode count is how you get two figures that are both
    correct and get quoted as each other. This tool reports whether TODAY'S session
    qualifies as a material adverse move and defers the count, deliberately.

FORMULA CACHE
    Immune. Reads the log only; touches no workbook.

CONSOLE ENCODING
    Output is ASCII-only on purpose. cmd/PowerShell under cp1252 raises
    UnicodeEncodeError on em-dashes and arrows, which would look like a crash.

USAGE
    python signal_scan.py --log logs\\signals_2026-07-30.log
    python signal_scan.py --log logs\\signals_2026-07-30.log --md signal_scan_2026-07-30.md
    python signal_scan.py --log logs\\signals_2026-07-30.log --quiet   (exit 1 on findings)
    python signal_scan.py --log logs\\signals_2026-07-30.log --counterfactual
"""

import argparse
import json
import re
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

TRACERS = ("WMT", "GM")          # pre-registered: WMT primary / GM secondary
# EXPECTED_N RETIRED 2026-08-21. It was 24, and it had been wrong against six
# successive true values (25 on 8/13-8/14, 26 on 8/17, 25 on 8/18, 26 on
# 8/19-8/21). The cohort-membership set-difference in run_integrity() replaces
# it: the count is printed, never asserted. Left as a named grave marker so a
# reader looking for the constant finds why it went rather than concluding it
# was lost. Do NOT reintroduce a hardcoded cohort size.
# ANALYST NOTE (2026-08-03): the era is no longer a single hardcoded string.
#   Two are live across the 3-B/3-C boundary and the scan must read whichever
#   the log actually carries rather than assert one. The check is: exactly one
#   era across all rows, AND that era is a known one. An unknown era FAILS
#   loudly instead of a mismatch reading as a data problem.
KNOWN_ERAS = {
    "A-S1D1-B1":    "pre-EDGAR (3-B)",
    "A-S1D1-B1-E1": "EDGAR live (3-C)",
    # ADDED 2026-08-26 with the H1 window ruling. D2 = trailing move over
    # five COMPLETED sessions; D1 = the shifted window ending on a live
    # intraday print. Same treatment, different measurement.
    "A-S1D2-B1":    "pre-EDGAR (3-B), H1 window corrected",
    "A-S1D2-B1-E1": "EDGAR live (3-C), H1 window corrected",
}
# Treatment rank, for the era-change alarm's DIRECTION rule (added 2026-08-20).
#   higher = more treatment. A move DOWN is a regression; a move UP is a recovery.
# ANALYST NOTE (2026-08-20): the alarm shipped 2026-08-19 without this, because it
#   was written on the session the flag was LOST and a loss was the only case in
#   view. On its FIRST live run it fired on the RECOVERY -- A-S1D1-B1 ->
#   A-S1D1-B1-E1 -- as a FAIL reading "THE RUN EXECUTED ON A DIFFERENT ARM. Check
#   EQUITY_EDGAR." The detection was right and the advice was exactly backwards:
#   today's flag was correct and yesterday's was not. A FAIL whose advice is wrong
#   teaches the reader to skim it, which is the failure mode this alarm exists to
#   prevent. Five test cases passed on 8/19 and none of them was a recovery,
#   because on 8/19 a recovery had not happened yet.
ERA_RANK = {
    "A-S1D1-B1":    0,
    "A-S1D1-B1-E1": 1,
    # RANK IS TREATMENT, and the H1 window ruling changes none of it: the
    # EDGAR arm is untouched. Equal rank across the D1->D2 line is the
    # correct statement and is what routes it to the third branch below.
    "A-S1D2-B1":    0,
    "A-S1D2-B1-E1": 1,
}
BUY_GATE = 70                    # KEEP 70% - unchanged
SELL_GATE = 65                   # risk_engine.RiskConfig.MIN_CONFIDENCE_SELL
                                 # ADDED 2026-08-13: CHECK 5 has TWO thresholds.
FALLBACK_THETA = 5.0
D1_FLOOR = 35                    # risk_engine.DampingConfig FLOOR - clamps, never raises

# Signal JSON ... | [PHASE 3-C DRY RUN] [accounts] [HELD|SCOUT] TICKER | Signal: ...
#
# ANALYST NOTE (2026-08-03, 3-C cutover): the phase token was hardcoded as
#   "3-B". At the 3-C cutover this regex would have matched ZERO lines and the
#   scan would have reported an empty run with no error — the SAME failure as
#   analyze_log.py at the 3-A cutover (2026-06-15, single-digit phase match)
#   and parse_log_to_tracker.py at the 3-B cutover (2026-07-07, hardcoded
#   ACCOUNT_RE). Third occurrence, third file. [\w.-]+ matches any phase label;
#   the optional trailing group tolerates an A/B arm suffix if one ever returns.
LINE_RE = re.compile(
    r"Signal JSON: (?P<json>\{.*?\})\s*\|\s*\[PHASE [\w.-]+ DRY RUN(?:\s+[\w.-]+)?\]"
    r"\s*\[(?P<accounts>[^\]]*)\]\s*\[(?P<hold>[^\]]*)\]\s*(?P<ticker>[A-Z.\-]+)\s*\|"
)
H1_RE = re.compile(r"H1\[trail5d=(?P<trail>[-+0-9.]+)%(?:;\s*closes=(?P<closes>[^\]]*))?\]")
S1_RE = re.compile(r"S1\[(?:prior=(?P<prior>[^;\]]*);\s*dconf=(?P<dconf>[-+0-9]+)|(?P<cold>no prior state))\]")
D_RE = re.compile(r"D\[raw=(?P<raw>\d+);\s*op=(?P<op>\d+);\s*trail=(?P<trail>[-+0-9.]+)%;\s*damp=(?P<damp>\d+)\]")
B_RE = re.compile(
    r"B\[sec=(?P<sec>[-+0-9.]+);\s*reg=(?P<reg>[-+0-9.]+);\s*w=(?P<w>[^;]*);"
    r"\s*base=(?P<base>\d+);\s*blend=(?P<blend>\d+);\s*blend_op=(?P<blend_op>\d+)\]"
)
# Phase 3-C EDGAR tag, appended after B[...]:
#   E[8k=1; form4=+0/-5; periodic=10-Q@2026-07-23; fin=9@2026-06-30]  or  E[no filings]
E_RE = re.compile(r"E\[(?P<edgar>[^\]]*)\]")

TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})")

# ---------------------------------------------------------------------------
# ERA-CHANGE ALARM  (added 2026-08-19)
# ---------------------------------------------------------------------------
# ANALYST NOTE (2026-08-19): on 2026-08-19 the canonical run executed with
#   EQUITY_EDGAR unset. main.py L104-106 derives BOTH the flag and the era from
#   that one variable, so the log was CORRECTLY stamped A-S1D1-B1 and this tool
#   printed, verbatim:
#
#       [OK  ] era stamp A-S1D1-B1 - pre-EDGAR (3-B)
#
#   The existing check asks only whether the stamp is UNIFORM and KNOWN. It was
#   both. Nothing anywhere in the stack compared it against the arm that was
#   INTENDED, so an E4 measurement cohort was spent on a control run and the
#   only symptom in the whole pipeline was a missing value_anchor exhibit --
#   which value.bat in turn reported as a routine findings run.
#
#   The comparison that catches it needs no new configuration and no expected
#   value to maintain, because THE PRIOR SESSION'S LOG ALREADY STATES WHICH ARM
#   WAS RUNNING. An era change mid-phase is a finding by construction: during
#   E4 an ARM change is a larger finding than a watchlist edit.
#
#   THREE STATES, KEPT DISTINCT ON PURPOSE. A tool that prints a pass when it
#   could not run the check is the exact class DP-3C-j ruled on, and it is the
#   class that produced the [OK] above:
#       OK    - compared against a prior session, era unchanged
#       FAIL  - compared, era CHANGED
#       NOCHK - NOT COMPARED (no prior canonical log, or it is unusable)
#   NOCHK is a distinct level rather than a WARN because it SETS THE FINDINGS
#   FLAG. WARN does not, and "I could not check" must never cost less attention
#   than "I checked and it is fine".
#
# ANCHORED ON PURPOSE. logs\ contains signals_2026-07-07_run1_coldstart.log --
#   a real archived cold-start run that was never pasted and is not a cohort. A
#   loose signals_*.log glob selects it and the alarm would then compare today
#   against a run that never entered the record.
LOG_NAME_RE = re.compile(r"^signals_(\d{4}-\d{2}-\d{2})\.log$")


def resolve_theta():
    """Import THETA from risk_engine so the definition of 'material adverse move'
    is the same constant D1 uses. One definition system-wide."""
    try:
        from risk_engine import DampingConfig  # type: ignore
    except Exception as exc:
        return FALLBACK_THETA, f"local default (risk_engine unavailable: {exc.__class__.__name__}) - NOT PROVENANCE-CLEAN"
    for attr in ("THETA", "theta", "theta_pct", "trail_theta", "TRAIL_THETA"):
        if hasattr(DampingConfig, attr):
            try:
                return float(getattr(DampingConfig, attr)), f"risk_engine.DampingConfig.{attr}"
            except (TypeError, ValueError):
                pass
    return FALLBACK_THETA, "local default (DampingConfig found, THETA attribute not - NOT PROVENANCE-CLEAN)"


def parse_log(path):
    """Return (records, warnings). AM-canonical: first occurrence per ticker wins,
    so a PM diagnostic append can never shadow the AM value (Workflow section 9)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    records, seen, warnings, pm_shadowed = [], set(), [], []

    for raw_line in text.splitlines():
        m = LINE_RE.search(raw_line)
        if not m:
            continue
        ticker = m.group("ticker")
        try:
            payload = json.loads(m.group("json"))
        except json.JSONDecodeError as exc:
            warnings.append(f"{ticker}: unparseable Signal JSON ({exc.msg}) - row skipped")
            continue

        if ticker in seen:
            pm_shadowed.append(ticker)
            continue
        seen.add(ticker)

        ts = TS_RE.match(raw_line)
        rec = {
            "ticker": ticker,
            "time": ts.group(2) if ts else None,
            "date": ts.group(1) if ts else None,
            "accounts": m.group("accounts"),
            "held": m.group("hold"),
            "signal": payload.get("signal"),
            "conf": payload.get("confidence"),
            "dq": payload.get("data_quality"),
            "era": payload.get("prompt_variant"),
            "px": payload.get("lastPrice"),
            "j_raw": payload.get("confidence_raw"),
            "j_blend": payload.get("confidence_blend"),
            "sector_score": payload.get("sector_score"),
            "regime_score": payload.get("regime_score"),
            "error": payload.get("error"),
        }
        for rex, keys in ((H1_RE, ("trail", "closes")),
                          (S1_RE, ("prior", "dconf", "cold")),
                          (D_RE, ("raw", "op", "damp")),
                          (B_RE, ("sec", "reg", "base", "blend", "blend_op")),
                          (E_RE, ("edgar",))):
            hit = rex.search(raw_line)
            for k in keys:
                rec[k] = hit.group(k) if hit else None

        for k in ("raw", "op", "damp", "base", "blend", "blend_op", "dconf"):
            if rec.get(k) is not None:
                rec[k] = int(rec[k])
        if rec.get("trail") is not None:
            rec["trail"] = float(rec["trail"])
        records.append(rec)

    if pm_shadowed:
        warnings.append(
            "PM append detected - {} repeat ticker row(s) ignored, AM value kept: {}"
            .format(len(pm_shadowed), ", ".join(sorted(set(pm_shadowed))))
        )
    return records, warnings


def prior_session_log(this_log):
    """(Path, 'YYYY-MM-DD') of the newest canonical cohort log strictly BEFORE
    this one, or (None, None). See the anchoring note above LOG_NAME_RE."""
    this_log = Path(this_log)
    m = LOG_NAME_RE.match(this_log.name)
    if not m:
        return None, None
    this_date = m.group(1)
    cands = []
    for p in this_log.parent.glob("signals_*.log"):
        mm = LOG_NAME_RE.match(p.name)
        if mm and mm.group(1) < this_date:      # ISO dates sort lexically
            cands.append((mm.group(1), p))
    if not cands:
        return None, None
    d, p = max(cands, key=lambda c: c[0])
    return p, d


def prior_era(this_log, explicit=None):
    """('ok', (era, date, name, nrows, tickers)) or ('not-compared', reason).

    `tickers` added 2026-08-21 so the membership check runs off the SAME parse
    as the era alarm. Deliberately not a second read of the file: the 8/03
    lesson (analyze_log's thresholds desyncing from risk_engine) is that one
    field must have one source, and "which names ran yesterday" is one field.

    The prior era is read with parse_log -- the SAME extraction path today's era
    uses. Deliberately not a second regex: two sources of truth for one field is
    how analyze_log's gate thresholds desynced from risk_engine (2026-08-04)."""
    if explicit is not None:
        path = Path(explicit)
        m = LOG_NAME_RE.match(path.name)
        date = m.group(1) if m else path.name
        if not path.is_file():
            return "not-compared", "--prior-log {} does not exist".format(path)
    else:
        path, date = prior_session_log(this_log)
        if path is None:
            return "not-compared", ("no prior canonical signals_<date>.log beside {}"
                                    .format(Path(this_log).name))
    try:
        recs, _ = parse_log(path)
    except OSError as exc:
        return "not-compared", "prior log {} unreadable ({})".format(
            path.name, exc.__class__.__name__)
    if not recs:
        return "not-compared", "prior log {} parsed 0 signal rows".format(path.name)
    eras = sorted({r["era"] for r in recs if r["era"]})
    if len(eras) != 1:
        return "not-compared", ("prior log {} is not era-uniform ({}) - nothing to "
                                "compare against".format(path.name, eras or "no era stamp"))
    return "ok", (eras[0], date, path.name, len(recs),
                  frozenset(r["ticker"] for r in recs if r.get("ticker")))


def fmt(v, spec="", dash="--"):
    """Format that survives None. The h1_lag_trace crash of 7/28 was a bare
    {:+.3f} meeting a blank value after the console trace already looked correct."""
    if v is None:
        return dash
    try:
        return format(v, spec)
    except (TypeError, ValueError):
        return str(v)


def run_integrity(records, theta_src, warnings, prior=None):
    """Daily_Workflow_v6_0 section 4 checks, as assertions. Returns list of
    (level, message) where level is OK / WARN / FAIL / NOCHK.

    `prior` is the (state, detail) pair from prior_era(), or None if the caller
    did not ask for the era-change comparison at all."""
    out = []
    n = len(records)
    # ---- COHORT MEMBERSHIP ------------------------------------------------
    # LANDED 2026-08-21; built and tested 2026-08-18, then held on an ordering
    # prerequisite that had ALREADY BEEN SATISFIED on 2026-08-10 (signal_scan
    # entered edgar_parser_audit as parser [7]; log_tracker_crosscheck followed
    # on 8/12). The blocker was quoted as live on 8/18, 8/19 and 8/20 -- a
    # RETIRED BLOCKER STATED IN LIVE-BLOCKER GRAMMAR, which retired_criteria_audit
    # cannot see because it scans for retired criteria, not for satisfied
    # prerequisites.
    #
    # WHAT IT REPLACES. `EXPECTED_N = 24` was a hardcoded constant that had been
    # wrong against SIX successive true values. A check that cannot pass is
    # noise, and noise is how a real finding gets skipped -- the exact failure
    # mode the era alarm was built against and then reproduced on 8/20.
    #
    # MEMBERSHIP SUBSUMES THE COUNT: an unchanged set has an unchanged size, and
    # the set says WHICH name moved, which the count never could. GM left the
    # cohort for exactly one session on 2026-08-18 and nothing in the stack saw
    # it; this check is the thing that would have. An equal-size SWAP is the
    # case the count could never catch and case 6d pins it.
    #
    # THREE STATES KEPT DISTINCT, because a tool that prints a pass when it
    # could not run the check is the class DP-3C-j ruled on:
    #   OK    - compared against the prior session, unchanged
    #   FAIL  - compared, and the set CHANGED (during E4 a watchlist edit IS a
    #           finding on a measurement cohort)
    #   NOCHK - not compared; no usable prior log
    if prior is None:
        out.append(("NOCHK", "cohort membership NOT COMPARED - caller did not "
                             "request the prior-session comparison (count {})".format(n)))
    else:
        _p_state, _p_detail = prior
        if _p_state != "ok":
            out.append(("NOCHK", "cohort membership NOT COMPARED - {} (count {})"
                        .format(_p_detail, n)))
        elif len(_p_detail) < 5 or _p_detail[4] is None:
            out.append(("NOCHK", "cohort membership NOT COMPARED - prior log carries "
                                 "no ticker set (count {})".format(n)))
        else:
            _pe, _pdate, _pname, _pn, _ptk = _p_detail
            here = frozenset(r["ticker"] for r in records if r.get("ticker"))
            added, removed = sorted(here - _ptk), sorted(_ptk - here)
            if not added and not removed:
                out.append(("OK", "cohort membership UNCHANGED since {} ({} names; "
                                  "count {} vs {} in {})"
                            .format(_pdate, len(here), n, _pn, _pname)))
            else:
                bits = []
                if added:
                    bits.append("ADDED: " + ", ".join(added))
                if removed:
                    bits.append("REMOVED: " + ", ".join(removed))
                out.append(("FAIL",
                            "cohort membership CHANGED since {} ({} -> {} names) - {}"
                            "  ** during E4 a watchlist edit is a COHORT-LEVEL finding, "
                            "not a formatting one".format(_pdate, _pn, n, "; ".join(bits))))

    eras = sorted({r["era"] for r in records if r["era"]})
    if len(eras) == 1 and eras[0] in KNOWN_ERAS:
        out.append(("OK", "era stamp {} - {}".format(eras[0], KNOWN_ERAS[eras[0]])))
    elif len(eras) > 1:
        out.append(("FAIL", "era stamp NOT UNIFORM across rows: {}".format(eras)))
    elif not eras:
        out.append(("FAIL", "era stamp MISSING from every row"))
    else:
        out.append(("FAIL", "era stamp {} is UNKNOWN (known: {})"
                    .format(eras[0], sorted(KNOWN_ERAS))))

    # ---- ERA-CHANGE ALARM ------------------------------------------------
    # The check above asks "is this stamp uniform and known?". This one asks
    # "is it the SAME ARM AS YESTERDAY?" -- the question 2026-08-19 needed and
    # nothing asked. See the note above LOG_NAME_RE.
    if prior is not None:
        p_state, p_detail = prior
        this_era = eras[0] if len(eras) == 1 else None
        if p_state != "ok":
            out.append(("NOCHK", "era-change alarm NOT RUN - " + p_detail))
        elif this_era is None:
            out.append(("NOCHK", "era-change alarm NOT RUN - this log has no single era "
                                 "to compare"))
        else:
            p_era, p_date, p_name, p_n = p_detail[:4]
            if this_era == p_era:
                out.append(("OK", "era unchanged since {} ({}, {} rows in {})"
                            .format(p_date, p_era, p_n, p_name)))
            else:
                # DIRECTION MATTERS. Losing the treatment and restoring it are not
                # the same event and must not carry the same advice.
                was, now = ERA_RANK.get(p_era), ERA_RANK.get(this_era)
                if was is None or now is None:
                    out.append(("FAIL",
                                "era stamp CHANGED since {}: {} -> {}  ** one of these arms is "
                                "not in ERA_RANK, so the direction cannot be read. Treat as a "
                                "regression until it is classified"
                                .format(p_date, p_era, this_era)))
                elif now < was:
                    out.append(("FAIL",
                                "era stamp REGRESSED since {}: {} -> {}  ** TREATMENT LOST. "
                                "Check EQUITY_EDGAR. This cohort is a CONTROL run: it is ABSENT "
                                "from E4 rather than excluded from it, and the E4 clock does "
                                "not advance".format(p_date, p_era, this_era)))
                elif now == was:
                    # ADDED 2026-08-26. A deliberate generation bump at the SAME
                    # treatment rank is neither a loss nor a recovery, and the
                    # RESTORED advice below would be actively wrong for it.
                    out.append(("WARN",
                                "era stamp CHANGED since {}: {} -> {}  ** SAME treatment "
                                "rank, so nothing was lost or restored. This is a ruled "
                                "generation bump. Cohorts either side are DIFFERENT "
                                "MEASUREMENTS on the changed channel - do not pool across "
                                "the line. Confirm the ruling is recorded."
                                .format(p_date, p_era, this_era)))
                else:
                    out.append(("WARN",
                                "era stamp RESTORED since {}: {} -> {}  ** treatment is back and "
                                "THIS run is correct. The finding belongs to {}, not to today: "
                                "confirm that control cohort is recorded as ABSENT from E4"
                                .format(p_date, p_era, this_era, p_date)))

    # EDGAR coverage (3-C). Absent entirely on a pre-EDGAR run, which is not a
    # finding. On an EDGAR run, EVERY row carries an E tag; a row with none
    # means the tag was not emitted, which is a different problem from a
    # covered name legitimately having nothing to report.
    tagged = [r for r in records if r.get("edgar") is not None]
    if tagged:
        no_filings = [r["ticker"] for r in tagged if r["edgar"] == "no filings"]
        covered = len(tagged) - len(no_filings)
        untagged = [r["ticker"] for r in records if r.get("edgar") is None]
        if untagged:
            out.append(("FAIL", "E tag MISSING on: " + ", ".join(sorted(untagged))))
        elif covered == 0:
            out.append(("FAIL", "E tag present but EVERY row reads 'no filings' - "
                                "EDGAR fetched nothing (SEC_USER_AGENT / egress)"))
        else:
            out.append(("OK", "EDGAR sections on {}/{} row(s); {} dark: {}"
                        .format(covered, len(records), len(no_filings),
                                ", ".join(sorted(no_filings)) or "none")))

        # DEGRADED-NAME ALARM, added 2026-08-20.
        # ANALYST NOTE: `fin=degraded` is DP-3C-j's per-ticker degradation
        #   signal and it has always been correct. The problem was that nothing
        #   read it. CORN degraded on 2026-08-18 and again on 2026-08-20 and
        #   both were discovered by hand-reading tags during the review, days
        #   after the rows entered the master. A per-ticker signal nobody
        #   surfaces is a per-ticker signal nobody has.
        #   Every degraded name is a COVERED name that did not receive the
        #   treatment, on a measurement cohort. That is a FAIL, not a WARN.
        degraded = sorted(r["ticker"] for r in tagged
                          if "fin=degraded" in (r.get("edgar") or ""))
        if degraded:
            out.append(("FAIL",
                        "EDGAR DEGRADED on {}: {}  ** {} covered name(s) did NOT "
                        "receive the statements block. These rows are in the cohort "
                        "but not in the treatment. Warm the cache before the next "
                        "run: python edgar_client.py --ticker {}"
                        .format(len(degraded), ", ".join(degraded),
                                len(degraded), degraded[0])))
        else:
            out.append(("OK", "no covered name degraded (fin=degraded absent)"))

    miss_raw = [r["ticker"] for r in records if r["j_raw"] is None]
    out.append(("OK" if not miss_raw else "FAIL",
                "confidence_raw present on all rows" if not miss_raw
                else "confidence_raw MISSING on: " + ", ".join(miss_raw)))

    miss_blend = [r["ticker"] for r in records
                  if r["j_blend"] is None or r["base"] is None or r["blend"] is None]
    out.append(("OK" if not miss_blend else "FAIL",
                "blend channel present on all rows" if not miss_blend
                else "blend channel INCOMPLETE on: " + ", ".join(miss_blend)))

    regimes = sorted({r["regime_score"] for r in records if r["regime_score"] is not None})
    out.append(("OK" if len(regimes) == 1 else "FAIL",
                "regime_score uniform at {}".format(regimes[0]) if len(regimes) == 1
                else "regime_score NOT uniform: {}".format(regimes)))

    cold = [r["ticker"] for r in records if r.get("cold")]
    if cold:
        out.append(("WARN", "S1 cold start (no prior state) on: " + ", ".join(cold)))
    else:
        out.append(("OK", "S1 prior state present on all rows"))

    errs = [r["ticker"] for r in records if r.get("error") or r.get("conf") in (0, None)]
    if errs:
        out.append(("WARN", "parse-error / zero-confidence rows: " + ", ".join(errs)))

    out.append(("WARN" if "NOT PROVENANCE-CLEAN" in theta_src else "OK",
                "THETA source: " + theta_src))
    for w in warnings:
        out.append(("WARN", w))
    return out


def reconcile(records):
    """Channel reconciliation. Every identity is COMPUTED and counted, not asserted
    from recollection - the three confidence channels have collided before."""
    checks = []

    def tally(label, pred, detail):
        bad = [(r["ticker"], detail(r)) for r in records if not pred(r)]
        checks.append((label, len(records) - len(bad), len(records), bad))

    tally("json.confidence == D.op",
          lambda r: r["conf"] == r["op"],
          lambda r: "conf {} vs op {}".format(r["conf"], r["op"]))
    tally("json.confidence_raw == D.raw",
          lambda r: r["j_raw"] == r["raw"],
          lambda r: "confidence_raw {} vs raw {}".format(r["j_raw"], r["raw"]))
    tally("D.raw == B.base",
          lambda r: r["raw"] == r["base"],
          lambda r: "raw {} vs base {}".format(r["raw"], r["base"]))
    tally("D.op == B.blend_op",
          lambda r: r["op"] == r["blend_op"],
          lambda r: "op {} vs blend_op {}".format(r["op"], r["blend_op"]))
    # D1 applies FLOOR=35, which clamps the reduction and never raises confidence.
    # The D tag reports the COMPUTED damp, not the APPLIED reduction, so raw-op is
    # smaller than damp whenever the floor binds. Verified on 7/7 damped rows across
    # 2026-07-30 and 07-31. Assert the floor-aware identity, not the naive one.
    tally("D.op == floor-aware(raw, damp)  [FLOOR=35]",
          lambda r: r["op"] == (r["raw"] if r["raw"] < D1_FLOOR
                                else max(D1_FLOOR, r["raw"] - r["damp"])),
          lambda r: "op {} but floor-aware prediction {}".format(
              r["op"], r["raw"] if r["raw"] < D1_FLOOR
              else max(D1_FLOOR, r["raw"] - r["damp"])))
    tally("HOLD never blend-adjusted (B.blend == B.base)",
          lambda r: r["signal"] != "HOLD" or r["blend"] == r["base"],
          lambda r: "HOLD blend {} vs base {}".format(r["blend"], r["base"]))

    # json.confidence_blend is ambiguous by name. Decide which it tracks from the
    # rows that can actually distinguish the two (blend != blend_op, i.e. damped).
    disc = [r for r in records if r["blend"] != r["blend_op"]]
    tracks_pre = sum(1 for r in disc if r["j_blend"] == r["blend"])
    tracks_post = sum(1 for r in disc if r["j_blend"] == r["blend_op"])
    return checks, (len(disc), tracks_pre, tracks_post)


def render(records, theta, theta_src, warnings, counterfactual, prior=None):
    L = []
    add = L.append
    date = next((r["date"] for r in records if r["date"]), "unknown")
    times = sorted(r["time"] for r in records if r["time"])

    integrity = run_integrity(records, theta_src, warnings, prior)
    checks, (n_disc, pre, post) = reconcile(records)
    # NOCHK counts as a finding. "I could not check" must not cost less
    # attention than "I checked and it is fine" -- 2026-08-19.
    fails = [c for c in integrity if c[0] in ("FAIL", "NOCHK")] + [c for c in checks if c[3]]

    add("=" * 78)
    # ANALYST NOTE: print the era the LOG carries, never a constant. A header
    #   stating a value the tool did not read from the data is the defect class
    #   this project has paid for most often.
    obs_eras = sorted({r["era"] for r in records if r["era"]})
    era_str = obs_eras[0] if len(obs_eras) == 1 else (
        "MIXED:" + "/".join(obs_eras) if obs_eras else "MISSING")
    add("SIGNAL SCAN - {}  (era {}, {} rows)".format(date, era_str, len(records)))
    add("=" * 78)

    # ---- headline -------------------------------------------------------
    tr = {r["ticker"]: r for r in records if r["ticker"] in TRACERS}
    add("")
    add("HEADLINE")
    for t in TRACERS:
        r = tr.get(t)
        if not r:
            add("  {:<4} ABSENT from this log".format(t))
            continue
        q = r["trail"] is not None and r["trail"] <= -theta
        add("  {:<4} trail5d {:>+7.2f}%  raw {:>3} op {:>3} damp {:>2}   material adverse move: {}"
            .format(t, r["trail"], r["raw"], r["op"], r["damp"], "YES" if q else "no"))
    add("  Episode COUNT is not computed here - see h1_lag_trace.py (coalescing).")
    add("  {} integrity/reconciliation finding(s).".format(len(fails)) if fails
        else "  No integrity or reconciliation findings.")

    # ---- integrity ------------------------------------------------------
    add("")
    add("-" * 78)
    add("RUN INTEGRITY (Daily_Workflow_v6_0 section 4)")
    add("-" * 78)
    for level, msg in integrity:
        add("  [{:<4}] {}".format(level, msg))

    # ---- per-ticker table ----------------------------------------------
    add("")
    add("-" * 78)
    add("PER-TICKER CHANNELS (sorted by trailing 5-session move)")
    add("-" * 78)
    add("  {:<5} {:>8} {:>4} {:>4} {:>5} {:>5} {:>6} {:>7} {:<6} {:<22} {:>5}".format(
        "TKR", "trail5d", "raw", "op", "damp", "base", "blend", "blend_op", "DQ", "S1 prior chain", "dconf"))
    for r in sorted(records, key=lambda x: (x["trail"] is None, x["trail"])):
        add("  {:<5} {:>8} {:>4} {:>4} {:>5} {:>5} {:>6} {:>7} {:<6} {:<22} {:>5}".format(
            r["ticker"], fmt(r["trail"], "+.2f"), fmt(r["raw"]), fmt(r["op"]),
            fmt(r["damp"]), fmt(r["base"]), fmt(r["blend"]), fmt(r["blend_op"]),
            (r["dq"] or "--")[:6], (r["prior"] or ("COLD" if r.get("cold") else "--"))[:22],
            fmt(r["dconf"], "+d")))

    # ---- reconciliation -------------------------------------------------
    add("")
    add("-" * 78)
    add("CHANNEL RECONCILIATION")
    add("-" * 78)
    for label, ok, total, bad in checks:
        add("  [{:<4}] {:<44} {}/{}".format("OK" if not bad else "FAIL", label, ok, total))
        for tkr, detail in bad:
            add("           {:<6} {}".format(tkr, detail))
    add("")
    add("  json.confidence_blend semantics (rows where blend != blend_op: n={}):".format(n_disc))
    if n_disc == 0:
        add("    UNDETERMINED - no damped rows today, the two values coincide.")
    else:
        add("    tracks B.blend (pre-damping)  : {}/{}".format(pre, n_disc))
        add("    tracks B.blend_op (post-damp) : {}/{}".format(post, n_disc))
        if post == n_disc and pre != n_disc:
            add("    NOTE: the field named 'confidence_blend' carries the POST-damping value.")
            add("          Reading it as the blend channel before damping is a channel error.")

    # ---- today's adverse-move roster ------------------------------------
    add("")
    add("-" * 78)
    add("MATERIAL ADVERSE MOVES TODAY (trail5d <= -{:.1f}%)".format(theta))
    add("-" * 78)
    adverse = [r for r in records if r["trail"] is not None and r["trail"] <= -theta]
    if not adverse:
        add("  none")
    for r in sorted(adverse, key=lambda x: x["trail"]):
        add("  {:<5} {:>+7.2f}%   raw {:>3} -> op {:>3} (damp {})   tracer: {}".format(
            r["ticker"], r["trail"], r["raw"], r["op"], r["damp"],
            "YES" if r["ticker"] in TRACERS else "no"))
    add("  Non-tracer rows are context only. The WS2 episode universe is WMT/GM")
    add("  by pre-registration; widening it is an amendment, not a reading.")

    # ---- optional counterfactual ----------------------------------------
    if counterfactual:
        add("")
        add("-" * 78)
        add("*** NOT IN EVIDENCE - COUNTERFACTUAL ONLY - DO NOT CITE FOR G1 ***")
        add("-" * 78)
        add("  DP-8 (direction) and DP-9 (universe) are ruled. This block exists to")
        add("  show what the ruled-out definitions would have produced today, so the")
        add("  cost of the ruling is visible in the record. It is not gate evidence.")
        fav = [r for r in records if r["trail"] is not None and r["trail"] >= theta]
        add("    bidirectional would add (favourable, |trail| >= THETA):")
        for r in sorted(fav, key=lambda x: -x["trail"]):
            add("      {:<5} {:>+7.2f}%  tracer: {}".format(
                r["ticker"], r["trail"], "YES" if r["ticker"] in TRACERS else "no"))
        if not fav:
            add("      none")
        add("    full-universe would add (adverse, non-tracer): {}".format(
            ", ".join(r["ticker"] for r in sorted(adverse, key=lambda x: x["trail"])
                      if r["ticker"] not in TRACERS) or "none"))

    # ---- cohort profile --------------------------------------------------
    add("")
    add("-" * 78)
    add("COHORT PROFILE")
    add("-" * 78)
    sig_mix = {}
    dq_mix = {}
    for r in records:
        sig_mix[r["signal"]] = sig_mix.get(r["signal"], 0) + 1
        dq_mix[r["dq"]] = dq_mix.get(r["dq"], 0) + 1
    add("  signals : " + ", ".join("{} {}".format(k, v) for k, v in sorted(sig_mix.items())))
    add("  DQ      : " + ", ".join("{} {}".format(k, v) for k, v in sorted(dq_mix.items())))
    confs = [r["conf"] for r in records if isinstance(r["conf"], (int, float))]
    if confs:
        add("  conf    : mean {:.1f}  median {:.1f}  sd(pop) {:.2f}  min {}  max {}".format(
            st.mean(confs), st.median(confs), st.pstdev(confs), min(confs), max(confs)))
    # FIXED 2026-08-13. TWO defects lived in this block, both of them the
    # pooling error the block's own closing line warns about:
    #   (a) `at_gate` filtered on CONFIDENCE ALONE and listed HOLD rows under a
    #       heading that says "BUY gate". Measured across the 8 scans 7/30-8/13:
    #       12 names listed, 8 of them HOLDs. On 2026-08-03 and 2026-08-12 the
    #       line named 1 and 2 tickers while the true actionable count was ZERO.
    #       Same defect class as analyze_log.py's CONFIDENCE STATS (fixed
    #       2026-08-11) and the Dashboard's "# Signals >= 70% (actionable)".
    #   (b) `near_miss` admitted SELLs into a set labelled "near-miss BUYs".
    #       There is no single 70% gate: risk_engine CHECK 5 is BUY >= 70 and
    #       SELL >= 65, so a SELL at 66 CLEARS its gate and is not a near-miss
    #       at all. CBRS SELL @68 on 2026-06-26 would have printed here as a
    #       "true KEEP-70 near-miss" while build_near_miss_registry.py (BUY-only)
    #       correctly excluded it -- two instruments disagreeing on one row.
    # Gates mirrored from risk_engine.RiskConfig; a row clears ITS OWN gate.
    def _clears(r):
        if not isinstance(r["conf"], int):
            return False
        if r["signal"] == "BUY":
            return r["conf"] >= BUY_GATE
        if r["signal"] == "SELL":
            return r["conf"] >= SELL_GATE
        return False          # HOLD never clears anything - it is not a trade

    gate_cleared = [r for r in records if _clears(r)]
    hold_high = [r for r in records
                 if r["signal"] == "HOLD" and isinstance(r["conf"], int)
                 and r["conf"] >= BUY_GATE]
    band = [r for r in records if isinstance(r["conf"], int) and 60 <= r["conf"] < BUY_GATE]
    near_miss = [r for r in band if r["signal"] == "BUY"]
    add("  GATE-CLEARING DIRECTIONAL (BUY >= {}%, SELL >= {}%): {}".format(
        BUY_GATE, SELL_GATE,
        ", ".join("{} {} {}".format(r["ticker"], r["signal"], r["conf"])
                  for r in gate_cleared) or "none"))
    add("            (this is the actionable set - see build_actionable_registry.py)")
    add("  HOLD rows at/above {}% (CONTEXT ONLY, not actionable): {}".format(
        BUY_GATE, ", ".join(r["ticker"] for r in hold_high) or "none"))
    add("  conf 60-69: {} row(s), of which near-miss BUYs (KEEP-70 population): {}".format(
        len(band), ", ".join(r["ticker"] for r in near_miss) or "none"))
    add("            (a HOLD in that band is not a near-miss BUY - do not pool them;")
    add("             nor is a SELL, which clears its own {}% gate)".format(SELL_GATE))
    add("  run window: {} to {}".format(times[0] if times else "--", times[-1] if times else "--"))
    add("")
    add("Advisory-only - no orders - not financial advice.")
    return "\n".join(L), fails


# ---------------------------------------------------------------------------
# SELFTEST -- era-change alarm only. Negatives included on purpose: the failure
# mode this alarm exists to prevent is a check that quietly reads as a pass.
# ---------------------------------------------------------------------------

_SELFTEST_LINE = (
    '2026-08-19 09:30:40,742 | INFO | Signal JSON: {{"ticker": "AAPL", "signal": "HOLD", '
    '"confidence": 65, "data_quality": "HIGH", "prompt_variant": "{era}", "lastPrice": 316.38, '
    '"confidence_raw": 65, "confidence_blend": 65, "sector_score": 0.27, "regime_score": -0.65}} '
    '| [PHASE 3-C DRY RUN] [Roth IRA] [HELD] AAPL | Signal: HOLD | Confidence: 65% | '
    'Risk: APPROVED | H1[trail5d=+3.65%] | S1[prior=47,52; dconf=+5] | '
    'D[raw=65; op=65; trail=+3.65%; damp=0] | '
    'B[sec=0.27; reg=-0.65; w=0.15/0.15; base=65; blend=65; blend_op=65]\n'
)


def _st_write(d, name, era, tickers=("AAPL",)):
    """`tickers` added 2026-08-21 for the cohort-membership cases. The template
    line is AAPL's, so each extra name is that line with the ticker swapped in
    both the JSON and the human half -- the same substitution case 5 already
    used for its non-uniform-era fixture."""
    p = Path(d) / name
    body = ""
    for tk in tickers:
        line = _SELFTEST_LINE.format(era=era)
        if tk != "AAPL":
            line = (line.replace('"AAPL"', '"{}"'.format(tk))
                        .replace("] AAPL |", "] {} |".format(tk)))
        body += line
    p.write_text(body, encoding="utf-8")
    return p


def _st_check(label, got, want):
    ok = got == want
    print("  [{}] {}".format("PASS" if ok else "FAIL", label))
    if not ok:
        print("        got  {!r}\n        want {!r}".format(got, want))
    return ok


def selftest():
    import shutil
    import tempfile
    ok = True
    d = Path(tempfile.mkdtemp(prefix="signal_scan_selftest_"))
    try:
        print("\nera-change alarm -- selftest")

        # 1. POSITIVE: same era on consecutive sessions -> 'ok', and the tuple
        #    names the prior session rather than asserting a constant.
        _st_write(d, "signals_2026-08-18.log", "A-S1D1-B1-E1")
        today = _st_write(d, "signals_2026-08-19.log", "A-S1D1-B1-E1")
        state, detail = prior_era(today)
        ok &= _st_check("unchanged era -> state 'ok'", state, "ok")
        ok &= _st_check("...and it reports the prior era and date",
                        (detail[0], detail[1]), ("A-S1D1-B1-E1", "2026-08-18"))
        recs, _w = parse_log(today)
        levels = {m: lv for lv, m in run_integrity(recs, "test", [], (state, detail))}
        ok &= _st_check("...and renders OK",
                        any(lv == "OK" and m.startswith("era unchanged")
                            for m, lv in levels.items()), True)

        # 2. THE 2026-08-19 CASE: treatment LOST -> FAIL, because a lost arm
        #    costs a measurement cohort.
        today = _st_write(d, "signals_2026-08-19.log", "A-S1D1-B1")
        state, detail = prior_era(today)
        recs, _w = parse_log(today)
        integ = run_integrity(recs, "test", [], (state, detail))
        lost = [m for lv, m in integ if lv == "FAIL" and "era stamp REGRESSED" in m]
        ok &= _st_check("treatment LOST -> exactly one FAIL", len(lost), 1)
        ok &= _st_check("...naming both arms in order",
                        "A-S1D1-B1-E1 -> A-S1D1-B1" in lost[0], True)
        ok &= _st_check("...and saying the cohort is ABSENT from E4",
                        "ABSENT" in lost[0], True)

        # 2b. THE 2026-08-20 CASE, and the reason this rule exists: treatment
        #     RESTORED must NOT be a FAIL, and must NOT tell the operator to
        #     check a flag that is now correct.
        _st_write(d, "signals_2026-08-19.log", "A-S1D1-B1")
        today = _st_write(d, "signals_2026-08-20.log", "A-S1D1-B1-E1")
        state, detail = prior_era(today)
        recs, _w = parse_log(today)
        integ = run_integrity(recs, "test", [], (state, detail))
        back = [m for lv, m in integ if lv == "WARN" and "era stamp RESTORED" in m]
        ok &= _st_check("treatment RESTORED -> WARN, not FAIL", len(back), 1)
        ok &= _st_check("...and NO era FAIL is emitted",
                        any(lv == "FAIL" and "era stamp" in m for lv, m in integ), False)
        ok &= _st_check("...and it does NOT say 'Check EQUITY_EDGAR'",
                        "Check EQUITY_EDGAR" in back[0], False)
        ok &= _st_check("...and it points the finding at the PRIOR session",
                        "belongs to 2026-08-19" in back[0], True)
        _rep, fails = render(recs, 5.0, "test", [], False, (state, detail))
        ok &= _st_check("...and a correct run is not flagged as a finding",
                        any("era stamp" in c[1] for c in fails), False)

        # 3. NEGATIVE: no prior log at all must render NOCHK, never OK, and must
        #    set the findings flag. This is the whole point of the level.
        d2 = Path(tempfile.mkdtemp(prefix="signal_scan_selftest_lone_"))
        try:
            lone = _st_write(d2, "signals_2026-08-19.log", "A-S1D1-B1")
            state, detail = prior_era(lone)
            ok &= _st_check("no prior log -> 'not-compared'", state, "not-compared")
            recs, _w = parse_log(lone)
            integ = run_integrity(recs, "test", [], (state, detail))
            ok &= _st_check("...renders NOCHK and never OK",
                            any(lv == "NOCHK" for lv, m in integ)
                            and not any(lv == "OK" and "era unchanged" in m for lv, m in integ),
                            True)
            _rep, fails = render(recs, 5.0, "test", [], False, (state, detail))
            ok &= _st_check("...and NOCHK sets the findings flag",
                            any(c[0] == "NOCHK" for c in fails), True)
        finally:
            shutil.rmtree(d2, ignore_errors=True)

        # 4. NEGATIVE: an archived non-cohort run must never be selected as the
        #    comparison. signals_2026-07-07_run1_coldstart.log is real, was never
        #    pasted, and a loose glob picks it.
        d3 = Path(tempfile.mkdtemp(prefix="signal_scan_selftest_anchor_"))
        try:
            _st_write(d3, "signals_2026-08-18_run1_coldstart.log", "A-S1D1-B1")
            _st_write(d3, "signals_2026-08-17.log", "A-S1D1-B1-E1")
            t = _st_write(d3, "signals_2026-08-19.log", "A-S1D1-B1-E1")
            path, pdate = prior_session_log(t)
            ok &= _st_check("archived cold-start run is NOT selected as prior",
                            (path.name, pdate), ("signals_2026-08-17.log", "2026-08-17"))
        finally:
            shutil.rmtree(d3, ignore_errors=True)

        # 6. COHORT MEMBERSHIP (landed 2026-08-21). Five cases, three of them
        #    negatives, because the state that must never be reachable is "the
        #    check could not run and printed OK anyway".
        d5 = Path(tempfile.mkdtemp(prefix="signal_scan_selftest_member_"))
        try:
            E = "A-S1D1-B1-E1"
            # 6a. POSITIVE: identical sets -> OK, and no FAIL mentioning membership.
            _st_write(d5, "signals_2026-08-18.log", E, ("AAPL", "MSFT", "GM"))
            t = _st_write(d5, "signals_2026-08-19.log", E, ("AAPL", "MSFT", "GM"))
            state, detail = prior_era(t)
            recs, _w = parse_log(t)
            integ = run_integrity(recs, "test", [], (state, detail))
            ok &= _st_check("membership unchanged -> OK",
                            any(lv == "OK" and "membership UNCHANGED" in m
                                for lv, m in integ), True)
            ok &= _st_check("...and no membership FAIL is emitted",
                            any(lv == "FAIL" and "membership" in m for lv, m in integ), False)
            ok &= _st_check("...and the prior ticker set rides on the era tuple",
                            detail[4], frozenset({"AAPL", "MSFT", "GM"}))

            # 6b. THE 2026-08-18 CASE: a name LEAVES the cohort. This is the
            #     event that actually happened, to GM, and that nothing saw.
            t = _st_write(d5, "signals_2026-08-19.log", E, ("AAPL", "MSFT"))
            state, detail = prior_era(t)
            recs, _w = parse_log(t)
            integ = run_integrity(recs, "test", [], (state, detail))
            gone = [m for lv, m in integ if lv == "FAIL" and "membership CHANGED" in m]
            ok &= _st_check("a name LEAVING -> exactly one FAIL", len(gone), 1)
            ok &= _st_check("...naming the departed name", "REMOVED: GM" in gone[0], True)
            ok &= _st_check("...and not inventing an addition", "ADDED" in gone[0], False)

            # 6c. A name JOINS -> also a FAIL, and named.
            _st_write(d5, "signals_2026-08-18.log", E, ("AAPL", "MSFT"))
            t = _st_write(d5, "signals_2026-08-19.log", E, ("AAPL", "MSFT", "USO"))
            state, detail = prior_era(t)
            recs, _w = parse_log(t)
            integ = run_integrity(recs, "test", [], (state, detail))
            join = [m for lv, m in integ if lv == "FAIL" and "membership CHANGED" in m]
            ok &= _st_check("a name JOINING -> exactly one FAIL", len(join), 1)
            ok &= _st_check("...naming the arrival", "ADDED: USO" in join[0], True)

            # 6d. THE CASE THE RETIRED COUNT COULD NEVER CATCH: an equal-size
            #     SWAP holds n constant. EXPECTED_N would have passed it silently.
            _st_write(d5, "signals_2026-08-18.log", E, ("AAPL", "MSFT", "GM"))
            t = _st_write(d5, "signals_2026-08-19.log", E, ("AAPL", "MSFT", "USO"))
            state, detail = prior_era(t)
            recs, _w = parse_log(t)
            integ = run_integrity(recs, "test", [], (state, detail))
            swap = [m for lv, m in integ if lv == "FAIL" and "membership CHANGED" in m]
            ok &= _st_check("an EQUAL-SIZE SWAP is still caught", len(swap), 1)
            ok &= _st_check("...naming both sides",
                            "ADDED: USO" in swap[0] and "REMOVED: GM" in swap[0], True)
            _rep, fails = render(recs, 5.0, "test", [], False, (state, detail))
            ok &= _st_check("...and a membership FAIL sets the findings flag",
                            any("membership" in c[1] for c in fails), True)
        finally:
            shutil.rmtree(d5, ignore_errors=True)

        # 6e. NEGATIVE: no prior log -> NOCHK, never OK, and the count is still
        #     PRINTED. "I could not check" must not read as "I checked".
        d6 = Path(tempfile.mkdtemp(prefix="signal_scan_selftest_member_lone_"))
        try:
            lone = _st_write(d6, "signals_2026-08-19.log", "A-S1D1-B1-E1", ("AAPL", "MSFT"))
            state, detail = prior_era(lone)
            recs, _w = parse_log(lone)
            integ = run_integrity(recs, "test", [], (state, detail))
            ok &= _st_check("no prior log -> membership NOCHK, never OK",
                            any(lv == "NOCHK" and "membership NOT COMPARED" in m
                                for lv, m in integ)
                            and not any(lv == "OK" and "membership" in m for lv, m in integ),
                            True)
            ok &= _st_check("...and the count is still PRINTED, not asserted",
                            any("count 2" in m for lv, m in integ), True)
        finally:
            shutil.rmtree(d6, ignore_errors=True)

        # 5. NEGATIVE: a prior log that is not era-uniform cannot anchor the
        #    comparison, and must say so rather than compare against eras[0].
        d4 = Path(tempfile.mkdtemp(prefix="signal_scan_selftest_mixed_"))
        try:
            mixed = Path(d4) / "signals_2026-08-18.log"
            mixed.write_text(
                _SELFTEST_LINE.format(era="A-S1D1-B1")
                + _SELFTEST_LINE.format(era="A-S1D1-B1-E1").replace('"AAPL"', '"MSFT"')
                                                           .replace("] AAPL |", "] MSFT |"),
                encoding="utf-8")
            t = _st_write(d4, "signals_2026-08-19.log", "A-S1D1-B1-E1")
            state, detail = prior_era(t)
            ok &= _st_check("non-uniform prior log -> 'not-compared'", state, "not-compared")
            ok &= _st_check("...and says why", "not era-uniform" in detail, True)
        finally:
            shutil.rmtree(d4, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n{}\n".format("ALL PASS" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Per-ticker read of one day's signals log.")
    # NOT required=True: --selftest must be runnable without a log. Absence is
    # validated below so the error message stays specific.
    ap.add_argument("--log",
                    help=r"explicit path, e.g. logs\signals_2026-07-30.log")
    ap.add_argument("--md", help="write a markdown exhibit to this path")
    ap.add_argument("--theta", type=float, help="override THETA (non-canonical; warns)")
    ap.add_argument("--counterfactual", action="store_true",
                    help="print the NOT-IN-EVIDENCE DP-8/DP-9 block")
    ap.add_argument("--quiet", action="store_true", help="suppress stdout; exit 1 on findings")
    ap.add_argument("--prior-log", help="explicit prior-session log for the era-change alarm "
                                        "(default: newest canonical signals_<date>.log before "
                                        "this one, in the same directory)")
    ap.add_argument("--selftest", action="store_true",
                    help="run the era-change alarm's own tests and exit")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.log:
        print("ERROR: --log is required (or use --selftest)", file=sys.stderr)
        return 2
    log_path = Path(args.log)
    if not log_path.is_file():
        print("ERROR: no such log file: {}".format(log_path), file=sys.stderr)
        return 2

    theta, theta_src = resolve_theta()
    if args.theta is not None:
        theta, theta_src = args.theta, "--theta override ({}) - NOT PROVENANCE-CLEAN".format(args.theta)

    records, warnings = parse_log(log_path)
    if not records:
        print("ERROR: no signal rows parsed from {}".format(log_path), file=sys.stderr)
        return 2

    prior = prior_era(log_path, args.prior_log)
    report, fails = render(records, theta, theta_src, warnings, args.counterfactual, prior)
    if not args.quiet:
        print(report)

    if args.md:
        md_path = Path(args.md)
        body = "# signal_scan - {}\n\n*Generated {} from `{}`. Advisory-only.*\n\n```\n{}\n```\n".format(
            next((r["date"] for r in records if r["date"]), "unknown"),
            datetime.now().strftime("%Y-%m-%d %H:%M"), log_path, report)
        md_path.write_text(body, encoding="utf-8")
        # Print AFTER the write succeeds. A clean console is not a completed run.
        print("Wrote: {}".format(md_path.resolve()))

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
