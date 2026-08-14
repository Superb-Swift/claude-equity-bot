#!/usr/bin/env python3
"""
outcome_sanity.py — magnitude guard for the MANUAL-ENTRY outcome columns.

WHY THIS EXISTS
---------------
2026-08-07: WMT's closing price was entered as 11.85 instead of 111.85 (dropped
leading digit). It corrupted THREE cohorts at once, because every trading day is
simultaneously the +5d, +10d and +20d resolution date for three different cohorts.

Both existing gates ran and BOTH PASSED with the bad value in place:
  * recalc.py            -> 0 errors. 11.85 is a valid number; recalc catches
                            FORMULA errors, not MAGNITUDE errors.
  * log_tracker_crosscheck.py -> 24/24 CLEAN. It reconciles columns A-G, the
                            PASTED block. Columns H/I/J are manual entry and it
                            is structurally incapable of seeing them.

The outcome columns are the only manual surface in the project with no gate,
and they carry a 3x blast radius per cell. This closes that hole.

SCOPE / DISCIPLINE
------------------
  * Reads logs\\claude_equity_bot_tracker.xlsx (THE MASTER). Writes nothing.
  * HARD-REFUSES tracker_with_registry.xlsx as an input (exit 2), same guard as
    log_tracker_crosscheck.py.
  * Formula-cache immune: reads only Price columns G/H/I/J, never K/L/M/N.
  * Derives the trading-day index from the master's own cohort dates. No holiday
    table, no network, no second source of truth to drift.
  * Exit 0 = clean. Exit 1 = findings. Exit 2 = wrong input / usage error.

CHECKS
------
  A  QUOTE-vs-CLOSE (primary).  A +Nd price for resolution date D is a CLOSE for
     date D. The master already holds that ticker's Px@signal for date D in the D
     cohort. Same instrument, same day: they cannot differ much. This is the check
     that catches 11.85 against 112.01.
  B  CROSS-HORIZON AGREEMENT.  Several cohorts resolve on the same date for the
     same ticker (+5d of C, +10d of C-5, +20d of C-15). Those cells must hold the
     SAME price. Catches single-cell typos. Free.
  C  MAGNITUDE BACKSTOP.  |return| >= MAG_PCT at any horizon. Needs no calendar,
     so it still fires if A and B are unavailable.
  D  COHORT DISPERSION.  sd(pop) of a resolved cohort > SD_PCT. A corrupted row
     blows up dispersion before it changes the mean.

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime
import os
import statistics as st
import sys

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not available. Activate the venv.", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------- thresholds
QUOTE_CLOSE_PCT = 10.0   # Check A: quote-to-close gap that warrants a look
AGREE_PCT       = 0.05   # Check B: tolerance for rounding on the same close
# Check C is horizon-scaled. Calibrated 2026-08-10 against the full record:
# the largest LEGITIMATE moves are CBRS -34.8% and MSFT +31.7% at +20d, so a
# flat 25% buried the real defect in true positives. These sit clear of both.
MAG_PCT = {"+5d": 30.0, "+10d": 40.0, "+20d": 50.0}
# The HOLD band, for the Check E breach split ONLY. This module does not and
# must not re-baseline it (Q4-2 parked); it is read here, never written.
BAND_PCT = 3.0
SD_PCT          = 12.0   # Check D: cohort dispersion ceiling

DATE_COL, TICKER_COL, SIGNAL_COL, PXSIG_COL = 1, 2, 4, 7
HORIZONS = [("+5d", 8, 5), ("+10d", 9, 10), ("+20d", 10, 20)]
FIRST_DATA_ROW = 5

REFUSED = "tracker_with_registry.xlsx"


def load(path):
    if os.path.basename(path).lower() == REFUSED.lower():
        print("=" * 78)
        print("REFUSED: %s is the GENERATED REPORT COPY, never an input." % REFUSED)
        print("Run against logs\\claude_equity_bot_tracker.xlsx (THE MASTER).")
        print("=" * 78)
        sys.exit(2)
    wb = openpyxl.load_workbook(path, data_only=True)
    if "Signals" not in wb.sheetnames:
        print("ERROR: no 'Signals' tab in %s" % path, file=sys.stderr)
        sys.exit(2)
    ws = wb["Signals"]
    rows = []
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        d = ws.cell(r, DATE_COL).value
        if not isinstance(d, datetime.datetime):
            continue
        rows.append({
            "row": r,
            "date": d.date(),
            "tkr": ws.cell(r, TICKER_COL).value,
            "sig": ws.cell(r, SIGNAL_COL).value,
            "g": ws.cell(r, PXSIG_COL).value,
            "h": ws.cell(r, 8).value,
            "i": ws.cell(r, 9).value,
            "j": ws.cell(r, 10).value,
        })
    return rows


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def main():
    ap = argparse.ArgumentParser(description="Magnitude guard for manual outcome columns.")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--quiet", action="store_true", help="findings only")
    ap.add_argument("--quote-close-pct", type=float, default=QUOTE_CLOSE_PCT)
    ap.add_argument("--mag-scale", type=float, default=1.0,
                    help="multiplier on the horizon-scaled magnitude thresholds")
    ap.add_argument("--sd-pct", type=float, default=SD_PCT)
    ap.add_argument("--shape-n", type=int, default=10,
                    help="how many recent cohorts to show in the Check E shape table")
    args = ap.parse_args()

    if not os.path.exists(args.tracker):
        print("ERROR: not found: %s" % args.tracker, file=sys.stderr)
        sys.exit(2)

    rows = load(args.tracker)
    dates = sorted({r["date"] for r in rows})
    idx = {d: i for i, d in enumerate(dates)}          # trading-day index
    # (date, ticker) -> Px@signal, our same-day reference price
    pxsig = {(r["date"], r["tkr"]): r["g"] for r in rows if num(r["g"])}

    findings = []
    checked_a = skipped_a = 0

    # ---- Check A: quote-vs-close, and Check B: cross-horizon agreement ------
    resolved_at = {}   # (resolution_date, ticker) -> list of (label, row, price)
    for r in rows:
        i = idx[r["date"]]
        for label, col, n in HORIZONS:
            v = r[{8: "h", 9: "i", 10: "j"}[col]]
            if not num(v):
                continue
            if i + n >= len(dates):
                continue                                # not yet resolvable
            rdate = dates[i + n]
            resolved_at.setdefault((rdate, r["tkr"]), []).append((label, r["row"], v, r["date"]))

            ref = pxsig.get((rdate, r["tkr"]))
            if not num(ref) or ref == 0:
                skipped_a += 1
                continue
            checked_a += 1
            gap = (v - ref) / ref * 100.0
            if abs(gap) > args.quote_close_pct:
                findings.append(
                    "[A] %-5s row %-5d %s %s price %.4f vs Px@signal %.4f on %s "
                    "-> %+.1f%% quote-to-close gap"
                    % (r["tkr"], r["row"], r["date"], label, v, ref, rdate, gap))

    for (rdate, tkr), entries in sorted(resolved_at.items()):
        vals = [e[2] for e in entries]
        if vals and (max(vals) - min(vals)) / max(abs(min(vals)), 1e-9) * 100.0 > AGREE_PCT:
            detail = "; ".join("%s from %s (row %d) = %.4f" % (e[0], e[3], e[1], e[2]) for e in entries)
            findings.append("[B] %-5s disagreeing closes for %s -> %s" % (tkr, rdate, detail))

    # ---- Check C: magnitude backstop ---------------------------------------
    for r in rows:
        if not num(r["g"]) or r["g"] == 0:
            continue
        for label, col, _ in HORIZONS:
            v = r[{8: "h", 9: "i", 10: "j"}[col]]
            if not num(v):
                continue
            ret = (v - r["g"]) / r["g"] * 100.0
            if abs(ret) >= MAG_PCT[label] * args.mag_scale:
                findings.append(
                    "[C] %-5s row %-5d %s %s return %+.1f%% (%.4f -> %.4f)"
                    % (r["tkr"], r["row"], r["date"], label, ret, r["g"], v))

    # ---- Check D: cohort dispersion ----------------------------------------
    for d in dates:
        rr = []
        for r in rows:
            if r["date"] != d or not num(r["g"]) or r["g"] == 0 or not num(r["h"]):
                continue
            rr.append((r["h"] - r["g"]) / r["g"])
        if len(rr) >= 5:
            sd = st.pstdev(rr) * 100.0
            if sd > args.sd_pct:
                findings.append("[D] cohort %s +5d dispersion sd(pop) %.2f%% exceeds %.1f%%"
                                % (d, sd, args.sd_pct))

    # ---- Check E: COHORT SHAPE — off-centering and breach asymmetry ---------
    # ADDED 2026-08-13. NOT A FINDING and deliberately not appended to
    # `findings`: this reports, it does not gate.
    #
    # WHY IT BELONGS HERE. +5d "accuracy" on a ~92% HOLD population is one minus
    # the band-breach rate, and the band is pinned at 0 +/- 3% while the return
    # distribution sits at its own mean. Two numbers therefore explain almost all
    # of it, and neither is printed anywhere today:
    #   OFF-CENTERING = cohort mean / cohort sd. Measured over 56 resolved
    #     cohorts, %UP-breach against off-centering gives pearson r = +0.926.
    #     That correlation is MECHANICAL, not a discovery -- it is the band-breach
    #     identity restated -- which is exactly why it is a useful diagnostic and
    #     must never be quoted as a finding. All-56 median is 0.03; 2026-08-03
    #     through 08-06 ran 0.53-0.65, roughly twenty times the central value.
    #   UP/DOWN SPLIT of the breaches. Pooled across 56 cohorts it is 311/279 =
    #     52.7% up, near a coin flip. Over 2026-08-03..08-06 it was 30 UP / 1 DOWN.
    #     "It rose while we held" and "it fell while we held" score identically
    #     under a symmetric band; for a system whose terminal intent is execution
    #     they are not the same error.
    #
    # The E4 clock started 2026-08-13 into an unusually calm, strongly up-drifting
    # tape. If drift mean-reverts inside the E4 window, +5d accuracy falls for
    # reasons that have nothing to do with EDGAR. This block is what makes that
    # separable at the read.
    #
    # HONEST SCOPE NOTE (2026-08-13): an earlier draft of this rationale claimed
    # the figures were "unreconstructable for cohorts already past." THAT WAS
    # WRONG. Both derive from the Price columns, which are retained, so any past
    # cohort can be recomputed at any time. Printing them is a convenience and a
    # habit-former, NOT a data-preservation measure, and nothing here needed to
    # be rushed on that basis. Recorded rather than quietly dropped.
    shape = []
    for d in dates:
        vals, hold_vals = [], []
        for r in rows:
            if r["date"] != d or not num(r["g"]) or r["g"] == 0 or not num(r["h"]):
                continue
            ret = (r["h"] - r["g"]) / r["g"] * 100.0
            vals.append(ret)
            # The +/-3% band scores HOLD rows ONLY. A directional row is scored by
            # the sign test and can never "breach" - pooling it here would inflate
            # the count with rows the band was never applied to.
            if str(r["sig"]).strip().upper() == "HOLD":
                hold_vals.append(ret)
        if len(vals) < 5:
            continue
        mean, sd = st.mean(vals), st.pstdev(vals)
        breaches = [v for v in hold_vals if abs(v) > BAND_PCT]
        up = sum(1 for v in breaches if v > 0)
        shape.append((d, len(vals), mean, sd, (mean / sd if sd else float("nan")),
                      len(breaches), up, len(breaches) - up))

    if not args.quiet and shape:
        print("-" * 78)
        print("  COHORT SHAPE - context only, NOT a gate. Last %d resolved cohort(s):"
              % min(args.shape_n, len(shape)))
        print("    %-12s %4s %8s %7s %9s   %s" %
              ("cohort", "n", "mean%", "sd%", "off-ctr", "breach (UP/DOWN)"))
        for d, n_, mean, sd, oc, nb, up, dn in shape[-args.shape_n:]:
            print("    %-12s %4d %+8.2f %7.2f %9.2f   %3d (%d UP / %d DOWN)"
                  % (d, n_, mean, sd, oc, nb, up, dn))
        print("    off-ctr = mean/sd against a band fixed at 0 +/- %.0f%%. It is a"
              % BAND_PCT)
        print("    DEFINITIONAL restatement of the breach rate, not evidence.")

    # ---- report -------------------------------------------------------------
    if not args.quiet:
        print("=" * 78)
        print("OUTCOME-COLUMN SANITY CHECK - %s" % datetime.date.today())
        print("=" * 78)
        print("  master  : %s" % args.tracker)
        print("  rows    : %d | cohorts %d | %s -> %s" % (len(rows), len(dates), dates[0], dates[-1]))
        print("  thresholds: quote-close %.1f%% | magnitude %s (x%.2f) | dispersion %.1f%%"
              % (args.quote_close_pct,
                 "/".join("%s %.0f%%" % (k, v) for k, v in MAG_PCT.items()),
                 args.mag_scale, args.sd_pct))
        print("  [A] quote-vs-close comparisons made: %d (skipped %d - no same-day reference)"
              % (checked_a, skipped_a))
        print("-" * 78)

    if findings:
        print("  %d FINDING(S) - VERIFY BEFORE READING ANY RESOLUTION:" % len(findings))
        for f in findings:
            print("    " + f)
        print("-" * 78)
        print("  A manual outcome price is entered once and read by THREE cohorts")
        print("  (+5d, +10d, +20d all land on the same date). Fix at source in the")
        print("  master, then re-run. Do not read cohort accuracy until this is clean.")
        print("=" * 78)
        return 1

    if not args.quiet:
        print("  RESULT: CLEAN - no implausible outcome prices.")
        print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
