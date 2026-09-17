#!/usr/bin/env python3
"""
h4_dq_threshold.py  —  Claude Equity Bot, Phase 3-A · H4 watchdog

STATUS (amended 2026-09-16): H4 was PROMOTED to ACTIVE by DP-3C-x (ruled
2026-09-03, effective 2026-09-01); the live status is read from rulings.py and
this tool emits no verdict while it is ruled. DP-3C-ak (2026-09-16): the
promotion stands although the reading has since fallen below its bar; any
DQ-conditional design must compare within names or frozen tiers, use the
episode basis, and carry a DQ-channel stability read. The history below is
kept as written.

HISTORY: H4 (DQ-conditional KEEP threshold) was DEMOTED. The Phase 2 closeout: the
HIGH-DQ near-miss split finished 2/2 (SCHD, VTI) — real but n=2, far too small;
the same-ticker NVDA series went 2 wins / 2 losses (a coin flip); and broadly
"DQ measures input completeness, not directional accuracy" — HIGH-DQ HOLDs
(MSFT, PM) were among the biggest misses. So H4 is NOT a live change: there is
no threshold edit here and none is recommended. This script is the OBSERVATION
hook that says whether 3-A data ever reopens it.

It does four things, read-only on the tracker:
    1. DQ-stratified accuracy — does HIGH-DQ actually out-predict MEDIUM, across
       all resolved signals and within the 50-59% / 60-69% bands?
    2. The near-miss lever — BUY & 60-69% by DQ (where a DQ-conditional KEEP
       threshold would bite), with resolved hit rates.
    3. "DQ != thesis quality" check — the biggest HIGH-DQ +5d misses.
    4. A COUNTERFACTUAL — if HIGH-DQ near-miss BUYs had been kept at a lowered
       threshold, what would those extra kept signals have returned? (+ the n caveat.)
Then it applies a REOPENING RULE and prints the verdict. The band-calibration
block is also printed, but the guardrail is RETIRED (Q1-R closed 2026-07-13):
history only, no PASS/FAIL, and T3 forbids relying on band ordering.

USAGE
    python h4_dq_threshold.py
    python h4_dq_threshold.py --tracker claude_equity_bot_tracker.xlsx
    python h4_dq_threshold.py --reopen-n 12 --reopen-hit 60
"""

from __future__ import annotations
import argparse
import datetime as dt
import os
import sys

import openpyxl

SIGNALS_SHEET = "Signals"
FIRST_DATA_ROW = 5
COL = dict(date=1, ticker=2, account=3, signal=4, conf=5, dq=6, p0=7,
           ret5=11, right5=14)
COHORT_START = dt.date(2026, 5, 18)
COHORT_END = dt.date(2026, 5, 29)
# ---- optional date-window slice (--since / --until) --------------------------
# When either bound is set, the analysis AND the calibration guardrail are
# computed over [SINCE, UNTIL]. With no bounds: analysis uses all rows and the
# guardrail uses the certified Phase 2 cohort window (COHORT_START..COHORT_END).
SINCE = None
UNTIL = None


# The consecutive-readings component of H4's bar. Named rather than inlined
# because the record shows this bar being misquoted from memory: on 2026-08-13
# the RATE component was reported as 50%, imported from KEEP-70, and a ruling
# was solicited on the malformed question before being retracted the same
# session. A bar that lives in a constant cannot be misremembered.
REOPEN_CONSECUTIVE = 2


def _in_window(d):
    if not isinstance(d, dt.date):
        return False
    if SINCE is not None and d < SINCE:
        return False
    if UNTIL is not None and d > UNTIL:
        return False
    return True


def _guardrail_window():
    if SINCE is not None or UNTIL is not None:
        return (SINCE or dt.date.min, UNTIL or dt.date.max)
    return (COHORT_START, COHORT_END)


def _window_label():
    if SINCE is not None or UNTIL is not None:
        return (str(SINCE) if SINCE else 'earliest') + ' .. ' + (str(UNTIL) if UNTIL else 'latest')
    return 'ALL ROWS (guardrail = Phase 2 cohort window)'

DQ_TIERS = ("HIGH", "MEDIUM", "LOW")


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    return v if isinstance(v, dt.date) else None


def conf_pct(v):
    if v is None:
        return None
    return v * 100.0 if v <= 1.0 else float(v)


def num(v):
    return float(v) if isinstance(v, (int, float)) else None


def pct_num(v):
    """Return+Nd columns are stored as fractions (-0.116 = -11.6%); to percent."""
    return float(v) * 100.0 if isinstance(v, (int, float)) else None


def fmt(x, nd=1, suffix="", dash="—"):
    return dash if x is None else f"{x:.{nd}f}{suffix}"


def load_rows(tracker):
    wb = openpyxl.load_workbook(tracker, data_only=True)
    ws = wb[SIGNALS_SHEET]
    rows = []
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        d = as_date(ws.cell(row=r, column=COL["date"]).value)
        tk = ws.cell(row=r, column=COL["ticker"]).value
        if not _in_window(d) or not tk:
            continue
        rows.append(dict(
            date=d, ticker=str(tk).strip().upper(),
            signal=str(ws.cell(row=r, column=COL["signal"]).value or "").strip().upper(),
            conf=conf_pct(ws.cell(row=r, column=COL["conf"]).value),
            dq=str(ws.cell(row=r, column=COL["dq"]).value or "").strip().upper(),
            ret5=pct_num(ws.cell(row=r, column=COL["ret5"]).value),
            right5=str(ws.cell(row=r, column=COL["right5"]).value or "").strip().upper(),
        ))
    wb.close()
    return rows


def hit_stats(subset):
    """(hits, resolved_n, hit_rate, avg_ret5 over resolved) for rows with YES/NO."""
    res = [x for x in subset if x["right5"] in ("YES", "NO")]
    hits = sum(1 for x in res if x["right5"] == "YES")
    rets = [x["ret5"] for x in res if x["ret5"] is not None]
    rate = (hits / len(res) * 100.0) if res else None
    avg = (sum(rets) / len(rets)) if rets else None
    return hits, len(res), rate, avg


def run(tracker, reopen_n, reopen_hit, out_dir):
    rows = load_rows(tracker)
    if not rows:
        sys.exit(f"ERROR: no signals in {tracker}")

    # ---- FORMULA-CACHE GUARD (added 2026-07-27) --------------------------
    # Return+5d and Was-Right-5d are FORMULAS. openpyxl reads their CACHED
    # values, and any openpyxl save blanks that cache — which the daily runner
    # now does every session when it embeds the Monitor Strip sheet. Run
    # against a freshly generated tracker_with_registry.xlsx, this script
    # therefore saw 0 resolved rows out of 2,390 formula cells and printed
    # "STAYS DEMOTED" — a VERDICT WITH NO EVIDENCE BEHIND IT, and the exact
    # failure class this harness exists to avoid. It now refuses instead.
    # monitor_strip.py is immune because it computes returns from the Price
    # columns; this script reads the formula columns by design.
    resolved_any = sum(1 for x in rows if x["right5"] in ("YES", "NO"))
    if resolved_any == 0:
        sys.exit(
            "\nERROR: 0 of %d rows have a resolved Was-Right-5d value.\n"
            "  This is almost certainly a BLANKED FORMULA CACHE, not missing data.\n"
            "  Return+5d / Was-Right-5d are formulas; openpyxl reads cached values,\n"
            "  and any openpyxl save (the daily Monitor Strip embed) clears them.\n"
            "  FIX: run against the MASTER (logs\\claude_equity_bot_tracker.xlsx),\n"
            "  which Excel keeps calculated — or open the report copy in Excel once\n"
            "  to refresh the cache, then re-run.\n"
            "  Refusing to print a verdict on zero evidence." % len(rows))

    # The header status is READ FROM THE RULING REGISTRY, never hardcoded.
    # It said "(DEMOTED)" on 2026-09-08, five days after DP-3C-x promoted H4.
    try:
        import rulings as _r
        _status = _r.status_of("H4") or "STATUS UNREGISTERED"
        _closed = not _r.is_open("H4")
    except Exception:
        _status, _closed = "STATUS UNAVAILABLE", False

    print("\n" + "=" * 80)
    print(f"H4 WATCHDOG — DQ-conditional threshold ({_status})   "
          f"source: {os.path.basename(tracker)}")
    print("=" * 80)
    if _closed:
        print("H4 has been RULED. No threshold change is made or recommended here,")
        print("and no reopening verdict is emitted; this is monitoring only.\n")
    else:
        print("H4 is on the backlog. No threshold change is made or recommended here;")
        print("this is the monitor that reports whether the data reopens it.\n")

    # ---- 1. DQ distribution ----
    from collections import Counter
    dist = Counter(x["dq"] or "(blank)" for x in rows)
    total = len(rows)
    print(f"DQ DISTRIBUTION ({total} signal rows):")
    for tier in DQ_TIERS:
        c = dist.get(tier, 0)
        print(f"   {tier:<7}: {c:>4}  ({c/total*100:.1f}%)")
    other = total - sum(dist.get(t, 0) for t in DQ_TIERS)
    if other:
        print(f"   other  : {other:>4}  ({other/total*100:.1f}%)")

    # ---- 2. broad DQ-accuracy test ----
    print("\nDQ-STRATIFIED +5d ACCURACY (all resolved signals; is HIGH better?):")
    print(f"   {'DQ':<7}{'hits/res':>10}{'hit%':>8}{'avg +5d ret':>13}")
    dq_overall = {}
    for tier in DQ_TIERS:
        h, n, rate, avg = hit_stats([x for x in rows if x["dq"] == tier])
        dq_overall[tier] = (rate, n)
        print(f"   {tier:<7}{f'{h}/{n}':>10}{fmt(rate,1,'%'):>8}{fmt(avg,2,'%'):>13}")

    print("\n   within bands, by DQ (the calibration premise of a DQ-conditional rule):")
    for lo, hi, name in ((50, 60, "50-59"), (60, 70, "60-69")):
        print(f"     band {name}:")
        for tier in DQ_TIERS:
            sub = [x for x in rows if x["dq"] == tier and x["conf"] is not None
                   and lo <= x["conf"] < hi]
            h, n, rate, avg = hit_stats(sub)
            if n:
                print(f"       {tier:<7}{f'{h}/{n}':>8}{fmt(rate,1,'%'):>8}")

    # ---- 3. near-miss lever ----
    print("\nNEAR-MISS LEVER — BUY & 60-69% by DQ (where a DQ-conditional KEEP bites):")
    nm = [x for x in rows if x["signal"] == "BUY" and x["conf"] is not None
          and 60 <= x["conf"] < 70]
    print(f"   {'DQ':<7}{'total':>7}{'hits/res':>10}{'hit%':>8}{'avg +5d ret':>13}")
    nm_high = None
    for tier in DQ_TIERS:
        sub = [x for x in nm if x["dq"] == tier]
        h, n, rate, avg = hit_stats(sub)
        if tier == "HIGH":
            nm_high = (h, n, rate, avg)
        if sub:
            print(f"   {tier:<7}{len(sub):>7}{f'{h}/{n}':>10}{fmt(rate,1,'%'):>8}{fmt(avg,2,'%'):>13}")
    # FIXED 2026-08-13: "17" was a hardcoded Phase-2 figure printed against a
    # live registry that had grown to 43 - a cross-check that could not fail
    # and therefore checked nothing. The registry is now recomputed here from
    # the SAME rule build_near_miss_registry.py uses (BUY, conf in [60,70)),
    # so a divergence between the two instruments is a real, visible finding.
    print(f"   ({len(nm)} near-miss BUYs total, recomputed from the master on "
          f"the build_near_miss_registry rule: BUY and 60 <= conf < 70.)")

    # ---- 4. DQ != thesis quality ----
    print("\nDQ != THESIS QUALITY — biggest HIGH-DQ +5d misses (input completeness")
    print("is not directional accuracy; cf. MSFT / PM high-DQ HOLD misses):")
    high_miss = sorted([x for x in rows if x["dq"] == "HIGH" and x["ret5"] is not None],
                       key=lambda x: x["ret5"])[:5]
    for x in high_miss:
        print(f"   {x['date']}  {x['ticker']:<5} {x['signal']:<4} "
              f"conf {fmt(x['conf'],0)}%  +5d {fmt(x['ret5'],2,'%')}")

    # ---- 5. counterfactual ----
    print("\nCOUNTERFACTUAL — keep HIGH-DQ near-miss BUYs at a lowered threshold:")
    if nm_high and nm_high[1]:
        h, n, rate, avg = nm_high
        print(f"   The {len([x for x in nm if x['dq']=='HIGH'])} HIGH-DQ near-miss BUYs "
              f"would become KEEPs; resolved {h}/{n} = {fmt(rate,1,'%')}, "
              f"avg +5d {fmt(avg,2,'%')}.")
        print(f"   Looks favorable, but n={n}. Not actionable on this sample.")
    else:
        print("   No resolved HIGH-DQ near-miss BUYs to simulate.")

    # ---- reopening rule ----
    print("\n" + "-" * 80)
    print("REOPENING RULE — H4 leaves the backlog ONLY if ALL hold:")
    print("-" * 80)
    cohort_date = max((x["date"] for x in rows if x.get("date")), default=None)
    h_rate, h_n = (nm_high[2], nm_high[1]) if nm_high else (None, 0)
    hi_ov = dq_overall.get("HIGH", (None, 0))[0]
    med_ov = dq_overall.get("MEDIUM", (None, 0))[0]
    c1 = h_n >= reopen_n
    c2 = (h_rate is not None) and (h_rate >= reopen_hit)
    c3 = (hi_ov is not None and med_ov is not None) and (hi_ov >= med_ov)
    print(f"   [{'PASS' if c1 else 'FAIL'}] HIGH-DQ near-miss resolved n ≥ {reopen_n}  "
          f"(now {h_n})")
    print(f"   [{'PASS' if c2 else 'FAIL'}] HIGH-DQ near-miss hit rate ≥ {reopen_hit}%  "
          f"(now {fmt(h_rate,1,'%')})")
    print(f"   [{'PASS' if c3 else 'FAIL'}] HIGH-DQ overall accuracy ≥ MEDIUM  "
          f"(HIGH {fmt(hi_ov,1,'%')} vs MEDIUM {fmt(med_ov,1,'%')})")
    reopen = c1 and c2 and c3

    # ANALYST NOTE (2026-09-08): record the reading BEFORE printing a verdict,
    #   and consult the ruling registry before printing one at all.
    #
    #   On 2026-09-08 this tool printed "VERDICT: H4 REOPENS — re-scope a
    #   DQ-conditional threshold" and, in its own header, "(DEMOTED)". DP-3C-x
    #   had ruled H4 PROMOTED five days earlier, effective 2026-09-01, on three
    #   consecutive passing readings against a bar of two. The tool was
    #   litigating a closed question, and because it also printed DEMOTED it
    #   left the operator believing the E4 §4 block on filings -> data_quality
    #   coupling still stood, when the promotion had spent it.
    #
    #   The tool could not have known: it said so itself — "this tool does not
    #   track prior readings and therefore does NOT assert that condition".
    #   Both halves are now fixed rather than disclaimed. rulings.py holds the
    #   settled decision points; the readings log makes the streak mechanical.
    #   record_reading is idempotent per cohort date, so re-running a session
    #   cannot manufacture consecutive passes.
    try:
        import rulings
        rulings.record_reading(
            "H4", cohort_date, reopen,
            detail={"n": h_n, "rate": h_rate, "high": hi_ov, "med": med_ov})
        ruled_closed = not rulings.is_open("H4")
        streak = rulings.streak_line("H4", REOPEN_CONSECUTIVE)
        reg_banner = rulings.banner("H4")
    except Exception as e:                       # never break the run on this
        ruled_closed, streak, reg_banner = False, f"   [streak] unavailable: {e}", ""

    if ruled_closed:
        print("\n   THIS QUESTION IS SETTLED — no verdict is emitted here.")
        print(reg_banner)
        print("\n   The readings below are MONITORING of a promoted instrument,")
        print("   not a reopening test. Today's figures are printed above and")
        print("   are recorded to the readings log; nothing is decided on them.")
        print(streak)
        if not reopen:
            # DP-3C-ak (2026-09-16): record plainly when the reading no longer
            # meets the bar the promotion stood on. No demotion rule was
            # pre-registered and none is applied here.
            print("   NOTE: today's reading does NOT meet the bar the promotion was")
            print("   granted on. Per DP-3C-ak the promotion stands (no demotion rule")
            print("   was pre-registered); any DQ-conditional design must cite this")
            print("   current reading, not the promotion reading.")
    else:
        print(f"\n   VERDICT: H4 {'REOPENS — re-scope a DQ-conditional threshold' if reopen else 'STAYS DEMOTED (backlog)'}.")
    if not ruled_closed and not reopen:
        # CORRECTED 2026-08-04. This block used to print a hardcoded
        # "the binding gap is sample size" regardless of which condition
        # actually failed. On 2026-07-28 n passed at 11 while the RATE failed,
        # so the tool explained its own verdict incorrectly — the same class of
        # defect (a tool reporting something it did not compute) cleared four
        # times that week. The explanation is now derived from c1/c2/c3.
        gaps = []
        if not c1:
            gaps.append(f"sample size (n {h_n} < {reopen_n})")
        if not c2:
            gaps.append(f"hit rate ({fmt(h_rate,1,'%')} < {reopen_hit}%)")
        if not c3:
            gaps.append("HIGH-DQ overall accuracy is not ≥ MEDIUM")
        print("   Binding gap: " + "; ".join(gaps) + ".")
        if not c1 and c2:
            print("   Only a larger resolved near-miss sample can reopen it.")
        elif c1 and not c2:
            print("   Sample size is NOT the constraint — the rate is. More rows")
            print("   alone will not reopen it.")
    elif not ruled_closed:
        # FIXED 2026-09-16: this was a bare `else:`, so once H4 was RULED the
        # settled branch above printed the streak AND this branch printed it
        # again — the duplicate [streak] line in the 2026-09-16 run.
        print(f"   NOTE: the 2026-07-28 ruling requires the pass to hold on")
        print(f"   {REOPEN_CONSECUTIVE} CONSECUTIVE readings at n ≥ {reopen_n} before any")
        print(f"   DQ-conditional design work. That condition is now TRACKED —")
        print(f"   see the streak line below, sourced from the readings log.")
        print(streak)

    # ---- guardrail ----
    agg = {"40-49": [0, 0], "50-59": [0, 0], "60-69": [0, 0]}
    glo, ghi = _guardrail_window()
    for x in rows:
        if not (glo <= x["date"] <= ghi) or x["conf"] is None:
            continue
        b = ("40-49" if 40 <= x["conf"] < 50 else "50-59" if 50 <= x["conf"] < 60
             else "60-69" if 60 <= x["conf"] < 70 else None)
        if b is None:
            continue
        agg[b][1] += 1
        if x["right5"] == "YES":
            agg[b][0] += 1
    lead = max(agg, key=lambda b: (agg[b][0] / agg[b][1]) if agg[b][1] else -1)
    # ---- calibration guardrail (RETIRED — historical context only) ----
    # Q1-R was DIAGNOSED and CLOSED 2026-07-13: the 50-59 vs 60-69 inversion was
    # a go-live calibration IMPROVEMENT (the 60-69 band gained +15.4pt), not a
    # guardrail failure. The guardrail is RETIRED and T2 is retired with it.
    # T3 forbids any decision or design relying on confidence-band ordering, so
    # this block is printed as HISTORY ONLY and carries no PASS/FAIL meaning.
    # Patched 2026-07-27 to match the treatment already applied in
    # h1_lag_trace.py; until then this file still printed a live [PASS/WARN].
    print("\nCALIBRATION GUARDRAIL — RETIRED (Q1-R closed 2026-07-13) — "
          "historical context only; T3: no band-ordering reliance")
    for b in ("40-49", "50-59", "60-69"):
        h, n = agg[b]
        rate = f"{h/n*100:.1f}%" if n else "—"
        mark = "  <-- leads" if b == lead else ""
        print(f"   {b}: {h}/{n} = {rate}{mark}")
    print(f"   (band ordering shown for the record: {lead} leads this window. "
          f"NOT a pass/fail signal — the guardrail is retired.)")
    print("   NOTE: this window is the run's --since/--until slice, so these "
          "rates will differ from the live 6/15+ figures in the notes.")

    # ---- markdown ----
    md = [f"# H4 Watchdog — DQ-conditional threshold ({_status})",
          f"*Source: `{os.path.basename(tracker)}` · generated {dt.datetime.now():%Y-%m-%d %H:%M}.*",
          "",
          ("**H4 has been RULED — no reopening verdict is emitted and no threshold "
           "change is made or recommended. Monitoring only.**"
           if _closed else
           "**H4 is on the backlog — no threshold change is made or recommended.** "
           "This is the monitor for whether 3-A data reopens it."), "",
          "## DQ-stratified +5d accuracy (all resolved)",
          "| DQ | hits/res | hit% | avg +5d ret |", "| --- | --- | --- | --- |"]
    for tier in DQ_TIERS:
        h, n, rate, avg = hit_stats([x for x in rows if x["dq"] == tier])
        md.append(f"| {tier} | {h}/{n} | {fmt(rate,1,'%')} | {fmt(avg,2,'%')} |")
    md += ["", "## Near-miss lever — BUY & 60-69% by DQ",
           "| DQ | total | hits/res | hit% |", "| --- | --- | --- | --- |"]
    for tier in DQ_TIERS:
        sub = [x for x in nm if x["dq"] == tier]
        h, n, rate, avg = hit_stats(sub)
        if sub:
            md.append(f"| {tier} | {len(sub)} | {h}/{n} | {fmt(rate,1,'%')} |")
    if _closed:
        md += ["", "## Status — RULED, no verdict emitted",
               reg_banner.replace("\n", "  \n") if reg_banner else _status,
               "",
               f"Today's monitoring figures: HIGH-DQ near-miss n = {h_n}, "
               f"hit = {fmt(h_rate,1,'%')}, HIGH {fmt(hi_ov,1,'%')} vs MEDIUM "
               f"{fmt(med_ov,1,'%')}. Recorded to the readings log; nothing is "
               f"decided on them.", "", streak.strip()]
    else:
        md += ["", f"## Verdict", f"H4 {'REOPENS' if reopen else 'STAYS DEMOTED (backlog)'} "
               f"— reopening needs HIGH-DQ near-miss n ≥ {reopen_n} (now {h_n}), "
               f"hit ≥ {reopen_hit}% (now {fmt(h_rate,1,'%')}), HIGH ≥ MEDIUM overall, "
               f"and the pass to hold on {REOPEN_CONSECUTIVE} consecutive readings.",
               "", streak.strip()]
    path = os.path.join(out_dir, "h4_dq_threshold_baseline.md")
    open(path, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"\nWrote: {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="H4 DQ-conditional-threshold watchdog.")
    ap.add_argument("--tracker", default="claude_equity_bot_tracker.xlsx")
    ap.add_argument("--reopen-n", type=int, default=12,
                    help="min resolved HIGH-DQ near-misses to consider reopening (default 12; raised from 10 on 2026-07-28)")
    ap.add_argument("--reopen-hit", type=float, default=60.0,
                    help="min HIGH-DQ near-miss hit%% to consider reopening (default 60)")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--since", default=None,
                    help="only analyze rows on/after YYYY-MM-DD (e.g. 2026-06-15 = Phase 3-A only)")
    ap.add_argument("--until", default=None,
                    help="only analyze rows on/before YYYY-MM-DD")
    args = ap.parse_args(argv)
    global SINCE, UNTIL
    if args.since:
        SINCE = dt.date.fromisoformat(args.since)
    if args.until:
        UNTIL = dt.date.fromisoformat(args.until)
    if SINCE is not None or UNTIL is not None:
        print("")
        print("[DATE SLICE] analyzing " + _window_label())
        print("   (the retired band-calibration block uses this same window)")
    if not os.path.exists(args.tracker):
        sys.exit(f"ERROR: tracker not found: {args.tracker}")
    os.makedirs(args.out_dir, exist_ok=True)
    run(args.tracker, args.reopen_n, args.reopen_hit, args.out_dir)


if __name__ == "__main__":
    main()
