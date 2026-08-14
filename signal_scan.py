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
EXPECTED_N = 24                  # frozen watchlist
# ANALYST NOTE (2026-08-03): the era is no longer a single hardcoded string.
#   Two are live across the 3-B/3-C boundary and the scan must read whichever
#   the log actually carries rather than assert one. The check is: exactly one
#   era across all rows, AND that era is a known one. An unknown era FAILS
#   loudly instead of a mismatch reading as a data problem.
KNOWN_ERAS = {
    "A-S1D1-B1":    "pre-EDGAR (3-B)",
    "A-S1D1-B1-E1": "EDGAR live (3-C)",
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


def fmt(v, spec="", dash="--"):
    """Format that survives None. The h1_lag_trace crash of 7/28 was a bare
    {:+.3f} meeting a blank value after the console trace already looked correct."""
    if v is None:
        return dash
    try:
        return format(v, spec)
    except (TypeError, ValueError):
        return str(v)


def run_integrity(records, theta_src, warnings):
    """Daily_Workflow_v6_0 section 4 checks, as assertions. Returns list of
    (level, message) where level is OK / WARN / FAIL."""
    out = []
    n = len(records)
    out.append(("OK" if n == EXPECTED_N else "FAIL",
                "signal count {} (expected {})".format(n, EXPECTED_N)))

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


def render(records, theta, theta_src, warnings, counterfactual):
    L = []
    add = L.append
    date = next((r["date"] for r in records if r["date"]), "unknown")
    times = sorted(r["time"] for r in records if r["time"])

    integrity = run_integrity(records, theta_src, warnings)
    checks, (n_disc, pre, post) = reconcile(records)
    fails = [c for c in integrity if c[0] == "FAIL"] + [c for c in checks if c[3]]

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


def main():
    ap = argparse.ArgumentParser(description="Per-ticker read of one day's signals log.")
    ap.add_argument("--log", required=True,
                    help=r"explicit path, e.g. logs\signals_2026-07-30.log")
    ap.add_argument("--md", help="write a markdown exhibit to this path")
    ap.add_argument("--theta", type=float, help="override THETA (non-canonical; warns)")
    ap.add_argument("--counterfactual", action="store_true",
                    help="print the NOT-IN-EVIDENCE DP-8/DP-9 block")
    ap.add_argument("--quiet", action="store_true", help="suppress stdout; exit 1 on findings")
    args = ap.parse_args()

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

    report, fails = render(records, theta, theta_src, warnings, args.counterfactual)
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
