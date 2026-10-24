#!/usr/bin/env python3
"""
prune_signal_state.py - drop departed names from signal_state.json, with a backup.

WHY THIS EXISTS (owed since 2026-09-21; the departed-name window closed 10-14)
    signal_state.json is the S1 prior-signal cache main.py writes. Nothing ever
    removes a ticker from it, so it still carries names that left the watchlist
    (AG, AIQ and XLU per the record), and quote_dump.py, which used to derive
    its universe from this file, asked Schwab for 31 names against a 28-name
    cohort. The prune was held until every departed name's last outcome cell
    resolved (+20d of the 2026-09-14 cohort, 2026-10-14) because enter_closes
    needed their closes; the 10-19 check found 0 blank cells, so it is due.

RULES
    * The watchlist is read from THE LATEST SESSION LOG (the tickers it wrote),
      never typed here. A ticker the latest run wrote is never dropped.
    * Refuses when the latest log looks partial (fewer than --min-tickers
      tickers), since a partial log would make live names look departed.
    * Dry run by default; --apply backs the file up first
      (signal_state.json.bak-<stamp>, git-ignored) and writes through
      signal_state.save_signal_state (temp file + os.replace).
    * Prints ticker NAMES only - never the stored signals or confidences.

USAGE
    python prune_signal_state.py            # dry run
    python prune_signal_state.py --apply
    python prune_signal_state.py --selftest

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import glob
import os
import re
import shutil
import sys

_TK = re.compile(r'Signal JSON: \{"ticker": "([A-Z][A-Z.\-]*)"')
_LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")


def latest_log_tickers(log_dir):
    logs = []
    for p in glob.glob(os.path.join(log_dir, "signals_*.log")):
        m = _LOGDATE.search(os.path.basename(p))
        if m:
            logs.append((m.group(1), p))
    if not logs:
        return None, set()
    d, p = max(logs)
    with open(p, encoding="utf-8", errors="replace") as fh:
        return d, {m.group(1) for ln in fh for m in [_TK.search(ln)] if m}


def plan(state_keys, live):
    keep = sorted(k for k in state_keys if k in live)
    drop = sorted(k for k in state_keys if k not in live)
    return keep, drop


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prune departed names from signal_state.json.")
    ap.add_argument("--state", default="signal_state.json")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--min-tickers", type=int, default=20)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import signal_state as ss
    d, live = latest_log_tickers(a.logs)
    if not live:
        print("REFUSED: no session log with signal rows under %s." % a.logs)
        return 1
    if len(live) < a.min_tickers:
        print("REFUSED: the latest log (%s) wrote %d ticker(s), fewer than %d - it looks "
              "partial, and live names would look departed." % (d, len(live), a.min_tickers))
        return 1
    if not os.path.exists(a.state):
        print("Nothing to prune: %s does not exist." % a.state)
        return 0
    state = ss.load_signal_state(a.state)
    keep, drop = plan(state.keys(), live)
    print("PRUNE signal_state.json [%s] - watchlist from the %s log: %d ticker(s)"
          % ("APPLY" if a.apply else "DRY RUN", d, len(live)))
    print("  state holds %d ticker(s): keep %d, drop %d%s"
          % (len(state), len(keep), len(drop), (": " + ", ".join(drop)) if drop else ""))
    missing = sorted(live - set(state))
    if missing:
        print("  (in the log but not in the state, left alone - main.py adds them: %s)"
              % ", ".join(missing))
    if not drop:
        print("  Nothing to prune.")
        return 0
    if not a.apply:
        print("  DRY RUN - nothing written. Re-run with --apply.")
        return 0
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak-%s" % (a.state, stamp)
    shutil.copy2(a.state, backup)
    ss.save_signal_state({k: state[k] for k in keep}, a.state)
    print("  backup : %s" % backup)
    print("  WROTE  : %s (%d ticker(s))" % (a.state, len(keep)))
    return 0


def selftest():
    import json
    import tempfile
    tmp = tempfile.mkdtemp(prefix="prune_")
    fails = []
    try:
        os.makedirs(os.path.join(tmp, "logs"))
        live = ["T" + chr(65 + i) for i in range(22)]
        with open(os.path.join(tmp, "logs", "signals_2026-10-22.log"), "w") as fh:
            for t in live:
                fh.write('x | INFO | Signal JSON: {"ticker": "%s", "signal": "HOLD"}\n' % t)
        with open(os.path.join(tmp, "logs", "signals_2026-10-21.log"), "w") as fh:
            fh.write('x | INFO | Signal JSON: {"ticker": "OLD1"}\n')
        st = os.path.join(tmp, "signal_state.json")
        data = {t: [{"date": "2026-10-22", "signal": "HOLD", "conf": 50}] for t in live + ["OLD1", "OLD2"]}
        with open(st, "w") as fh:
            json.dump(data, fh)
        rc = main(["--state", st, "--logs", os.path.join(tmp, "logs")])
        with open(st) as fh:
            ok = rc == 0 and len(json.load(fh)) == 24
        print("  [%s] dry run writes nothing" % ("PASS" if ok else "FAIL")); ok or fails.append("dry")
        rc = main(["--state", st, "--logs", os.path.join(tmp, "logs"), "--apply"])
        with open(st) as fh:
            after = json.load(fh)
        ok = rc == 0 and sorted(after) == live and glob.glob(st + ".bak-*")
        print("  [%s] --apply drops only the departed names, with a backup"
              % ("PASS" if ok else "FAIL")); ok or fails.append("apply")
        rc = main(["--state", st, "--logs", os.path.join(tmp, "logs"), "--min-tickers", "30"])
        ok = rc == 1
        print("  [%s] a partial latest log is refused" % ("PASS" if ok else "FAIL")); ok or fails.append("partial")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("  prune_signal_state selftest: %s" % ("ALL PASS" if not fails else "FAIL " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
