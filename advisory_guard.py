#!/usr/bin/env python3
"""
advisory_guard.py — enforce DP-T1: this system never places an order.

WHY THIS EXISTS (DP-T1, ruled by Rob 2026-09-16)
    T1 (advisory; the human decides) is the permanent ceiling. A ruling that
    nothing checks is a note, and "no order path is ever built" is exactly the
    kind of clause that erodes one convenience function at a time. This gate
    makes the clause mechanical:

      1. no Python file in the repo calls an order-placing or order-building
         API (schwab-py's place_order / order builders, or a raw /orders
         endpoint);
      2. risk_engine.RiskConfig.REQUIRE_HUMAN_APPROVAL is True;
      3. every "no order placed" banner main.py prints is still present.

    `--selftest` shows the gate FAILING on a synthetic file that places an
    order, and passing on one that does not. A gate never shown to fail is not
    a gate (Phase 3-C exit review §6.2).

    Exit 0 = advisory posture intact. Exit 1 = a violation. Exit 2 = usage.
    Reopening execution needs a new ruling by Rob; editing this file to make
    it pass is not that.

Advisory-only - no orders - not financial advice.
"""

import argparse
import glob
import os
import re
import sys
import tempfile

# Order-path signatures. Word-bounded so prose like "in order to" never hits.
PATTERNS = [
    r"\bplace_order\s*\(",
    r"\breplace_order\s*\(",
    r"\bcancel_order\s*\(",
    r"\bsubmit_order\s*\(",
    r"\bplace_orders?\b\s*=",
    r"\bequity_(buy|sell)_(market|limit)\s*\(",
    r"\bOrderBuilder\b",
    r"\bschwab\.orders\b",
    r"from\s+schwab\.orders",
    r"['\"][^'\"]*/accounts/[^'\"]*/orders",
    r"\bpaper_(order|execute|trade)\w*\s*\(",
]
RX = re.compile("|".join(PATTERNS))
SELF = os.path.basename(__file__)
SKIP_DIRS = {"venv", ".venv", ".git", "__pycache__", "Retired", "edgar_cache"}


def scan(root):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".py") or fn == SELF:
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        code = line.split("#", 1)[0]
                        if RX.search(code):
                            hits.append("%s:%d: %s" % (os.path.relpath(p, root), i,
                                                       line.strip()[:100]))
            except OSError:
                continue
    return hits


def check_config(root):
    out = []
    sys.path.insert(0, root)
    try:
        import importlib
        re_mod = importlib.import_module("risk_engine")
        if getattr(re_mod.RiskConfig, "REQUIRE_HUMAN_APPROVAL", None) is not True:
            out.append("risk_engine.RiskConfig.REQUIRE_HUMAN_APPROVAL is not True")
    except Exception as e:                                    # noqa: BLE001
        out.append("risk_engine not importable (%s) - posture unverifiable" % e)
    finally:
        sys.path.pop(0)
    main_py = os.path.join(root, "main.py")
    if os.path.exists(main_py):
        with open(main_py, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
        if "No order placed" not in txt:
            out.append("main.py no longer prints 'No order placed'")
    return out


def run(root, quiet=False):
    hits = scan(root)
    cfg = check_config(root)
    if not quiet:
        print("=" * 78)
        print("ADVISORY GUARD (DP-T1) - %s" % os.path.abspath(root))
        print("=" * 78)
    if hits or cfg:
        print("  VIOLATION - DP-T1 says this system never places an order.")
        for h in hits:
            print("    [ORDER PATH] " + h)
        for c in cfg:
            print("    [POSTURE]    " + c)
        print("  Remove the order path. Reopening execution needs a new ruling by Rob.")
        return 1
    if not quiet:
        print("  CLEAN - no order-placing code; human approval is required;")
        print("  'No order placed' banners intact.")
    return 0


def selftest():
    ok = True

    def chk(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print("  [%s] %s" % ("PASS" if cond else "FAIL", name))

    d = tempfile.mkdtemp()
    with open(os.path.join(d, "clean.py"), "w") as fh:
        fh.write("# we sort in order to rank\nx = sorted([2, 1])\n")
    chk("prose 'in order to' is not an order path", scan(d) == [])
    with open(os.path.join(d, "bad.py"), "w") as fh:
        fh.write("def go(client, acct, spec):\n    return client.place_order(acct, spec)\n")
    chk("client.place_order(...) is caught", len(scan(d)) == 1)
    with open(os.path.join(d, "bad2.py"), "w") as fh:
        fh.write("from schwab.orders.equities import equity_buy_market\n")
    chk("schwab order builders are caught", len(scan(d)) == 2)
    with open(os.path.join(d, "commented.py"), "w") as fh:
        fh.write("# client.place_order(acct, spec)  <- never\n")
    chk("a commented-out mention is not a violation", len(scan(d)) == 2)
    print("  RESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="DP-T1 advisory posture gate.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else run(a.root, a.quiet))
