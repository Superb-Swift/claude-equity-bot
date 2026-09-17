#!/usr/bin/env python3
"""
shadow_damper.py — the D3 "confidence-change damper", computed OFFLINE, never shown to the model.

WHY THIS EXISTS (DP-3C-ah, 2026-09-16; Discovery 2026-09-16 §3, direction D3)
    On HOLD rows, a rise in confidence preceded UNDER-performance over the
    next five sessions (rank IC -0.097, t -2.76, stable across halves; -0.058
    after controlling for the latest price move). That is discovery and it is
    quarantined. The question it raises is testable without touching the bot:
    would a confidence that moves LESS from row to row rank names better?

    This module builds that shadow channel from the master's own Conf% column:

        damped[t] = damped[t-1] + LAMBDA * (conf[t] - damped[t-1])
        damped[first row] = conf[first row]

    with LAMBDA = 0.5, FIXED IN THE PRE-REGISTRATION BEFORE ANY PROSPECTIVE
    ROW EXISTS. It is never tuned: choosing LAMBDA on the discovery set is the
    same trap as the in-sample k that makes band_price §7 degenerate
    (Discovery §11.5).

WHAT IT IS NOT
    * Not a prompt change, not a risk-engine change, not a treatment. The
      value is computed after the fact from the tracker and printed. The model
      never sees it, the risk engine never reads it, and nothing the bot emits
      changes. It is safe mid-E4 for that reason (DP-3C-g, DP-8/9 untouched).
    * Not a signal. It is advice-quality research under DP-T1.

THE ARM (PR-3, pre-registered 2026-09-16 in DP-3C-ah)
    Population  HOLD rows, signal dates after the discovery cutoff (>= 2026-09-17)
    Read        per-date paired difference IC(damped, +5d close) - IC(conf, +5d close),
                mean with Newey-West t at lag 4
    POSITIVE    difference >= +0.03 AND t >= 2
    NEGATIVE    difference <= 0
    Read date   the first session with 144 resolved dates (the PR-1 clock)
    Before the read date only COUNTS are printed (`--progress`). The IC
    arithmetic lives in discovery_scan.py so there is one implementation.

USAGE
    python shadow_damper.py --progress              # counts only (daily runner)
    python shadow_damper.py --latest                # today's damped values, no outcomes
    python shadow_damper.py --selftest

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import os
import sys

LAMBDA = 0.5          # FIXED 2026-09-16. Never tuned. Changing it is a new arm.


def damped_series(confs, lam=LAMBDA):
    """EWMA of a confidence sequence (oldest first). None values are carried
    over: a missing confidence neither moves nor resets the damped value."""
    out, cur = [], None
    for c in confs:
        if c is None:
            out.append(cur)
            continue
        cur = c if cur is None else cur + lam * (c - cur)
        out.append(cur)
    return out


def attach(rows, key_tk="tk", key_d="d", key_conf="conf", out_key="damped"):
    """Add the damped value to each row dict, per ticker, in date order."""
    by = {}
    for r in rows:
        by.setdefault(r[key_tk], []).append(r)
    for xs in by.values():
        xs.sort(key=lambda r: r[key_d])
        for r, v in zip(xs, damped_series([r[key_conf] for r in xs])):
            r[out_key] = v
    return rows


def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print("  [%s] %s" % ("PASS" if cond else "FAIL", name))

    chk("first value is the raw value", damped_series([60])[0] == 60)
    chk("a +10 change is halved", damped_series([60, 70])[1] == 65)
    chk("no change stays put", damped_series([60, 60, 60]) == [60, 60, 60])
    chk("None carries the prior value", damped_series([60, None, 70]) == [60, 60, 65])
    chk("lambda is fixed at 0.5", LAMBDA == 0.5)
    rows = [dict(tk="A", d=dt.date(2026, 9, 18), conf=70),
            dict(tk="A", d=dt.date(2026, 9, 17), conf=60)]
    attach(rows)
    chk("attach orders by date per ticker", rows[0]["damped"] == 65)
    print("  RESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline confidence-change damper (PR-3).")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    import discovery_scan as ds
    rows, _close, _c, _idx = ds.build(ds.load(a.tracker))
    attach(rows)
    if a.latest:
        last = max(r["d"] for r in rows)
        print("SHADOW DAMPER (lambda %.1f) - cohort %s - NOT shown to the model" % (LAMBDA, last))
        for r in sorted((r for r in rows if r["d"] == last), key=lambda r: r["tk"]):
            if r["conf"] is None:
                continue
            print("  %-6s %-5s conf %5.1f  damped %5.1f  (%+.1f)"
                  % (r["tk"], r["sig"], 100 * r["conf"], 100 * r["damped"],
                     100 * (r["damped"] - r["conf"])))
        return 0
    # --progress (default): delegate to the one implementation of the PR clocks
    for line in ds.progress_lines(rows, only=("PR-3",)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
