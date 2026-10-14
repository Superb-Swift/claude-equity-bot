#!/usr/bin/env python3
"""
value_card.py -- the valuation layer, organised around decisions and changes.

WHY (2026-10-14, claude/ValuePass_WhatItMeasures_2026-10-14.md)
    implied_return prints about 27 KB a day, and across the 29 dated exhibits
    from 2026-08-24 to 10-14, 14 of 15 headline classes never changed. Three
    findings explain why, and each section below answers one of them:

    1. THE CLASS IS A TRAILING-FISCAL-YEAR P/E. Book value cancels out of
       `implied/trailing @9%`:
           ratio = (P/EPS) * (r-g)/(1+g) + g/((1+g) ROE)  =  0.0583 * P/E + 0.0291/ROE
       Schwab's eps is the last fiscal year and does not move on a quarterly
       report, so the class moves only with price or a 10-K. Section 6 checks
       this identity every run and FLAGS it if the exhibit stops satisfying it.
    2. THE DAILY REPRINT HIDES THE DAYS THAT MATTER. Section 1 prints only
       what changed since the previous dated exhibit, and splits every ratio
       move into a PRICE part and a FILING part.
    3. THE CLASSES ARE FRAGILE. Neither ROE route is trailing-twelve-month.
       Section 3 re-derives every class under both routes and r = 7/9/11%,
       and calls a class ROBUST only if all six agree.

    Section 2 is the decision card the 2026-08-24 DP-V2 memo specified as
    stage 1 and the 2026-10-09 review ranked V1. Section 4 is DP-V2's
    counterfactual flip ledger: COUNTS ONLY, never an outcome.

WHAT IT DOES NOT DO
    It reads no return, breach, hit or +Nd cell. It modifies no gate, admits
    and rejects nothing, touches no workbook, no prompt, no endpoint, no
    edgar_client extract. DP-V1 stands: nothing here reaches the model. The
    DP-V2 gate column is COUNTERFACTUAL and is never applied.

INPUTS
    implied_return_<date>.md   today's, plus every earlier dated exhibit found
                               in the root or exhibits\\archive (sections 1, 4)
    logs\\signals_<date>.log   signal, confidence, held/scout, per-account
    quote_dump.json            divYield and eps for the book-free reads (5)
    the MASTER                 BUY rows since 2026-08-24 for the ledger (4).
                               tracker_with_registry.xlsx is REFUSED.

USAGE
    python value_card.py --date 2026-10-14 --tracker logs\\claude_equity_bot_tracker.xlsx
           --log logs\\signals_2026-10-14.log --quotes quote_dump.json
           --md value_card_2026-10-14.md [--json value_card_2026-10-14.json]
    python value_card.py --selftest

EXIT  0 = exhibit written.  1 = written, with FINDINGS (identity check failed,
      or a parse anomaly).  2 = could not run (no exhibit for the date, report
      copy given as input, unreadable master or log). Nothing is written on 2.

Advisory-only - no orders - not financial advice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

R_GRID = (7.0, 9.0, 11.0)      # cost-of-equity grid printed by implied_return 4
R_BASE = 9.0                   # the pre-registered class rate (DP-V2 memo 3.1)
G_BASE = 3.0                   # implied_return's g
DEMANDING_AT = 2.00            # DP-V2 memo 3.1, frozen at first run, never re-cut
NEUTRAL_AT = 1.50
DPV2_GATE = {"DEMANDING": 75, "NEUTRAL": 70, "UNDEMANDING": 65, "NO READ": 70}
DPV2_BASE_GATE = 70
DPV2_SINCE = dt.date(2026, 8, 24)      # first day the layer printed section 4
DPV2_STOP = dt.date(2026, 12, 31)      # DP-V2 memo 6: withdrawn, not extended
DPV2_MIN_ROWS, DPV2_MIN_TICKERS = 12, 3
INSTALLED = dt.date(2026, 10, 14)      # rows on or before this are BACKFILLED
# The identity is checked against the ROUNDING of the printed inputs (px, BVPS,
# ROE% and the ratio are all printed to 2dp), so SND's 0.51% ROE gets the wide
# bound it needs and a 2.7x name gets a tight one. Verified on all 29 exhibits
# 2026-08-24..10-14: no name exceeds its bound.
REFUSED = "tracker_with_registry.xlsx"
SECTION_RULE = re.compile(r"^-{20,}")

ACCT_RE = re.compile(r"\] \[([^\]]+)\] \[(HELD|SCOUT)\] ([A-Z][A-Z0-9.]*) \| Signal: (\w+) \| "
                     r"Confidence: (\d+)% \| Risk: (\w+)")
PER_RE = re.compile(r"PER-ACCOUNT: ([^.|]+)")


# --------------------------------------------------------------------------- #
# Parsing the implied_return exhibit (format stable since 2026-08-24)
# --------------------------------------------------------------------------- #

def _num(s):
    s = str(s).strip().rstrip("%x").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _section(lines, title_re):
    """The body lines of the section whose title matches title_re."""
    out, on = [], False
    for i, line in enumerate(lines):
        if SECTION_RULE.match(line) and i + 1 < len(lines) and re.match(title_re, lines[i + 1]):
            on = True
            continue
        if on and SECTION_RULE.match(line) and out and not re.match(title_re, lines[i - 1]):
            break
        if on:
            out.append(line)
    return out


S1_RE = re.compile(
    r"^\s+([A-Z][A-Z0-9.]*)\s+(\d{4}-\d{2}-\d{2})\s+(-?[\d.]+)\s+(-?[\d.]+)\s+([+-][\d.]+%)\s+"
    r"(n/a|-?[\d.]+%)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(?:([\d.]+)Q\s+([\d.]+)Q\s+)?(.*)$")
S1A_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*)\s+(Q\d|FY)\s+(n/a|-?[\d.]+%)\s+(n/a|-?[\d.]+%)\s+")
S4_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*)\s+(-?[\d.]+)\s+(-?[\d.]+%|n/a)\s+(-?[\d.]+)%\s+"
                   r"(-?[\d.]+)%\s+(-?[\d.]+)%\s+(n/a|-?[\d.]+x)")
S4B_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(n/a|-?[\d.]+%)\s+"
                    r"(NO CONVERGENT g|-?[\d.]+%)\s+(.*)$")
BLOCK_RE = re.compile(r"^\s+([A-Z][A-Z0-9.]*) NOT COMPUTED -- (.*)$")
DATE_RE = re.compile(r"implied_return_(\d{4}-\d{2}-\d{2})\.md$")


def parse_exhibit(path):
    """{ticker: fields} and {ticker: blocked reason} from one implied_return exhibit."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().replace("\r", "").split("\n")
    rec, blocked = {}, {}
    for line in _section(lines, r"^1\. INPUTS"):
        m = S1_RE.match(line)
        if m:
            rec[m.group(1)] = dict(
                anchor=m.group(2), bvps=_num(m.group(3)), px=_num(m.group(4)),
                roe=None if m.group(6) == "n/a" else _num(m.group(6)),
                mb=_num(m.group(7)), divy=_num(m.group(8)),
                anc_age=_num(m.group(9)) if m.group(9) else None,
                num_age=_num(m.group(10)) if m.group(10) else None,
                basis=m.group(11).strip())
    for line in _section(lines, r"^1a\."):
        m = S1A_RE.match(line)
        if m and m.group(1) in rec:
            rec[m.group(1)]["roe_edgar"] = None if m.group(4) == "n/a" else _num(m.group(4))
    for line in _section(lines, r"^4\. \(II\)"):
        m = S4_RE.match(line)
        if m and m.group(1) in rec:
            rec[m.group(1)].update(
                i7=_num(m.group(4)), i9=_num(m.group(5)), i11=_num(m.group(6)),
                ratio=None if m.group(7) == "n/a" else _num(m.group(7)))
    for line in _section(lines, r"^4b\."):
        m = S4B_RE.match(line)
        if m and m.group(1) in rec:
            rec[m.group(1)]["g_impl"] = None if "NO" in m.group(5) else _num(m.group(5))
    for line in lines:
        m = BLOCK_RE.match(line)
        if m:
            blocked[m.group(1)] = m.group(2).strip()
    return rec, blocked


def find_exhibits(root):
    """{date: path} for every dated implied_return exhibit in root and exhibits/archive."""
    out = {}
    for p in glob.glob(os.path.join(root, "implied_return_*.md")) + \
            glob.glob(os.path.join(root, "exhibits", "archive", "implied_return_*.md")):
        m = DATE_RE.search(os.path.basename(p))
        if m:
            d = dt.date.fromisoformat(m.group(1))
            if d not in out or os.path.dirname(p) == root:   # root copy wins
                out[d] = p
    return out


# --------------------------------------------------------------------------- #
# Valuation arithmetic -- the exhibit's own identity, nothing new
# --------------------------------------------------------------------------- #

def klass(ratio):
    if ratio is None:
        return "NO READ"
    if ratio >= DEMANDING_AT:
        return "DEMANDING"
    return "NEUTRAL" if ratio >= NEUTRAL_AT else "UNDEMANDING"


def implied_roe(mb, r=R_BASE, g=G_BASE):
    """implied_return (II), percent in and out: [r + (M/B - 1)(r - g)] / (1 + g),
    i.e. [M/B (r - g) + g] / (1 + g). Same expression as implied_return.py L179."""
    return (mb * (r - g) + g) / (1.0 + g / 100.0)


def ratio_from(px, bvps, roe, r=R_BASE):
    """implied/trailing at rate r. None where trailing ROE is not positive."""
    if not roe or roe <= 0 or not bvps or bvps <= 0 or not px:
        return None
    return implied_roe(px / bvps, r) / roe


def pe_lastfy(f):
    """Price over the EPS the class actually uses (ROE x BVPS)."""
    if not f.get("roe") or f["roe"] <= 0 or not f.get("bvps"):
        return None
    return f["px"] / (f["roe"] / 100.0 * f["bvps"])


def robustness(f):
    """Class under both ROE routes x the r grid. ROBUST only if all six agree."""
    combos = {}
    for route, key in (("Schwab", "roe"), ("EDGAR", "roe_edgar")):
        roe = f.get(key)
        for r, ik in zip(R_GRID, ("i7", "i9", "i11")):
            i = f.get(ik)
            ratio = (i / roe) if (i is not None and roe and roe > 0) else None
            combos[(route, r)] = (ratio, klass(ratio))
    base = klass(f.get("ratio"))
    ratios = [v[0] for v in combos.values() if v[0] is not None]
    classes = {v[1] for v in combos.values()}
    route_alt = combos[("EDGAR", R_BASE)]
    r_classes = {combos[("Schwab", r)][1] for r in R_GRID}
    return dict(
        base=base,
        tag=("ROBUST" if len(classes) == 1 and base != "NO READ" else
             ("—" if base == "NO READ" else "FRAGILE")),
        lo=min(ratios) if ratios else None, hi=max(ratios) if ratios else None,
        route_alt=route_alt,
        route_flip=(base != "NO READ" and route_alt[1] != base),
        r_flip=(base != "NO READ" and len(r_classes) > 1),
        r_classes=[combos[("Schwab", r)][1] for r in R_GRID])


def decompose(prev, cur):
    """Split a ratio move into PRICE (new price, old fundamentals) and FILING
    (new fundamentals at the new price). Returns None where either side has
    no ratio."""
    r0 = ratio_from(prev["px"], prev["bvps"], prev["roe"])
    rp = ratio_from(cur["px"], prev["bvps"], prev["roe"])
    r1 = ratio_from(cur["px"], cur["bvps"], cur["roe"])
    if None in (r0, rp, r1):
        return None
    return dict(r0=r0, r1=r1, price=rp - r0, filing=r1 - rp)


def dividend_implied_g(yield_pct, r=R_BASE):
    """Gordon, solved for g: P = D0(1+g)/(r-g)  ->  g = (r - y)/(1 + y)."""
    if yield_pct is None or yield_pct <= 0:
        return None
    y, rr = yield_pct / 100.0, r / 100.0
    return (rr - y) / (1.0 + y) * 100.0


# --------------------------------------------------------------------------- #
# Inputs other than the exhibit
# --------------------------------------------------------------------------- #

def parse_log(path):
    """{ticker: dict(acct, held, signal, conf, risk, per)} from a signals log."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = ACCT_RE.search(line)
            if not m:
                continue
            per = PER_RE.search(line)
            per_map = {}
            if per:
                for part in per.group(1).split(";"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        per_map[k.strip()] = v.strip()
            px = None
            if "Signal JSON:" in line:
                try:
                    j, _ = json.JSONDecoder().raw_decode(line.split("Signal JSON:", 1)[1].strip())
                    px = j.get("lastPrice")
                except ValueError:
                    px = None
            out[m.group(3)] = dict(acct=m.group(1).strip(), held=m.group(2) == "HELD",
                                   signal=m.group(4).upper(), conf=int(m.group(5)),
                                   risk=m.group(6).upper(), per=per_map, px=px)
    return out


def executability(s):
    if s["signal"] == "HOLD":
        return "—"
    if not s["per"]:
        return "BLOCKED" if s["risk"] != "APPROVED" else "APPROVED"
    ok = [k for k, v in s["per"].items() if v == "APPROVED"]
    if len(ok) == len(s["per"]):
        return "EXECUTABLE"
    if ok:
        return "PARTIAL (" + ", ".join(ok) + " only)"
    return "REJECTED in every account"


def load_quotes(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        q = json.load(fh)
    return q.get("quotes", {}) if isinstance(q, dict) else {}


def load_buy_rows(tracker, since):
    """(date, ticker, conf) for BUY rows on/after `since`. Reads date, ticker,
    signal and confidence ONLY -- no price, return or outcome column is read."""
    import openpyxl
    from build_actionable_registry import (SIGNALS_SHEET, FIRST_DATA_ROW,
                                           LAST_DATA_ROW_CAP, COL, as_date, conf_pct)
    wb = openpyxl.load_workbook(tracker, data_only=True, read_only=True)
    ws = wb[SIGNALS_SHEET]
    out, blank = [], 0
    last = max(COL["date"], COL["ticker"], COL["signal"], COL["conf"])
    for vals in ws.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW_CAP,
                             min_col=1, max_col=last, values_only=True):
        d = as_date(vals[COL["date"] - 1])
        if d is None:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        if d < since or str(vals[COL["signal"] - 1] or "").strip().upper() != "BUY":
            continue
        c = conf_pct(vals[COL["conf"] - 1])
        if c is not None:
            out.append((d, str(vals[COL["ticker"] - 1] or "").strip().upper(), c))
    wb.close()
    return out


# --------------------------------------------------------------------------- #
# DP-V2 counterfactual flip ledger -- counts only
# --------------------------------------------------------------------------- #

def dpv2_flip(cls, conf):
    """'ADMIT->REJECT', 'REJECT->ADMIT' or None, for a BUY at `conf` under DP-V2."""
    gate = DPV2_GATE.get(cls, DPV2_BASE_GATE)
    now, then = conf >= DPV2_BASE_GATE, conf >= gate
    if now and not then:
        return "ADMIT->REJECT"
    if then and not now:
        return "REJECT->ADMIT"
    return None


def dpv2_ledger(buy_rows, classes_by_date):
    """classes_by_date: {date: {ticker: class}}. Returns flips, unscored rows.
    A row on a session with no exhibit is NEVER counted. It is reported as
    UNSCORED, with the class from the nearest EARLIER exhibit as a hint only,
    and only when that hint would have flipped it."""
    flips, unscored = [], []
    dates = sorted(classes_by_date)
    for d, tk, c in sorted(buy_rows):
        if d not in classes_by_date:
            prior = [x for x in dates if x < d]
            hint = classes_by_date[prior[-1]].get(tk, "NO READ") if prior else None
            if hint and dpv2_flip(hint, c):
                unscored.append((d, tk, c, hint, prior[-1]))
            continue
        cls = classes_by_date[d].get(tk, "NO READ")
        f = dpv2_flip(cls, c)
        if f:
            flips.append((d, tk, c, cls, f, "backfilled" if d <= INSTALLED else "live"))
    return flips, unscored


# --------------------------------------------------------------------------- #
# The exhibit
# --------------------------------------------------------------------------- #

def fmt(v, spec="{:.2f}", none="—"):
    return none if v is None else spec.format(v)


def build(date, root, log_path, quotes_path, tracker):
    exhibits = find_exhibits(root)
    if date not in exhibits:
        raise SystemExit(("no implied_return_%s.md in %s or exhibits/archive -- run "
                          "implied_return first; nothing to build on." % (date, root), 2))
    rec, blocked = parse_exhibit(exhibits[date])
    if not rec:
        raise SystemExit(("implied_return_%s.md parsed to zero names -- format changed?" % date, 2))
    earlier = sorted(d for d in exhibits if d < date)
    prev_date = earlier[-1] if earlier else None
    prev_rec, prev_blocked = parse_exhibit(exhibits[prev_date]) if prev_date else ({}, {})
    sig = parse_log(log_path)
    quotes = load_quotes(quotes_path)
    findings = []

    rob = {t: robustness(f) for t, f in rec.items()}
    held = sorted(t for t, s in sig.items() if s["held"])
    directional = sorted((t for t, s in sig.items() if s["signal"] in ("BUY", "SELL")),
                         key=lambda t: -sig[t]["conf"])

    L = []
    L.append("=" * 100)
    L.append("VALUE CARD -- the valuation layer organised around decisions and changes")
    L.append("Counterfactual only. Modifies no gate, admits and rejects nothing, reads no outcome.")
    L.append("=" * 100)
    L.append("as of %s   exhibit %s   previous exhibit %s   log %s" % (
        date, os.path.basename(exhibits[date]), prev_date or "none", os.path.basename(log_path)))
    L.append("class = implied_return 4 'implied/trailing @9%%' (Schwab ROE route), lines %.2fx / %.2fx "
             "(DP-V2 memo 3.1, frozen)" % (DEMANDING_AT, NEUTRAL_AT))
    L.append("")

    # ---- 0. coverage -------------------------------------------------------
    read = [t for t in rec if rob[t]["base"] != "NO READ"]
    held_read = [t for t in held if t in rec and rob[t]["base"] != "NO READ"]
    held_rob = [t for t in held_read if rob[t]["tag"] == "ROBUST"]
    dir_read = [t for t in directional if t in rec and rob[t]["base"] != "NO READ"]
    L.append("-" * 100)
    L.append("0. COVERAGE -- stated first, because it bounds everything below")
    L.append("-" * 100)
    L.append("  watchlist %d   classed %d   ROBUST %d" % (
        len(sig), len(read), sum(1 for t in read if rob[t]["tag"] == "ROBUST")))
    L.append("  held names %d   classed %d   ROBUST %d   %s" % (
        len(held), len(held_read), len(held_rob),
        ("(" + ", ".join(held_rob) + ")") if held_rob else ""))
    L.append("  today's directionals %d   classed %d   %s" % (
        len(directional), len(dir_read), ", ".join(dir_read) or ""))
    coverage = dict(watchlist=len(sig), classed=len(read),
                    robust=sum(1 for t in read if rob[t]["tag"] == "ROBUST"),
                    held=len(held), held_classed=len(held_read), held_robust=held_rob,
                    directional=len(directional), directional_classed=dir_read)
    L.append("")

    # ---- 1. what changed ---------------------------------------------------
    L.append("-" * 100)
    L.append("1. WHAT CHANGED since %s -- filings, class crossings, robustness, coverage"
             % (prev_date or "(no earlier exhibit)"))
    L.append("-" * 100)
    changes = []
    if prev_date:
        for t in sorted(set(rec) | set(prev_rec)):
            a, b = prev_rec.get(t), rec.get(t)
            if a is None and b is not None:
                changes.append("  %-5s ENTERED the computed set" % t)
                continue
            if b is None and a is not None:
                changes.append("  %-5s LEFT the computed set -- %s" % (t, blocked.get(t, "not in today's exhibit")))
                continue
            filing = a["anchor"] != b["anchor"] or a.get("roe") != b.get("roe")
            ca, cb = klass(a.get("ratio")), klass(b.get("ratio"))
            dec = decompose(a, b)
            if filing:
                part = (" | ratio %.2f -> %.2f: price %+.2f, filing %+.2f" % (
                    dec["r0"], dec["r1"], dec["price"], dec["filing"])) if dec else ""
                changes.append("  %-5s NEW FILING  anchor %s -> %s   BVPS %s -> %s   ROE %s -> %s%s" % (
                    t, a["anchor"], b["anchor"], fmt(a["bvps"]), fmt(b["bvps"]),
                    fmt(a.get("roe"), "{:.2f}%"), fmt(b.get("roe"), "{:.2f}%"), part))
            if ca != cb:
                why = (" (price %+.2f, filing %+.2f)" % (dec["price"], dec["filing"])) if dec else ""
                changes.append("  %-5s CLASS %s -> %s   ratio %s -> %s%s" % (
                    t, ca, cb, fmt(a.get("ratio")), fmt(b.get("ratio")), why))
            ra = robustness(a)
            if ra["tag"] != rob[t]["tag"]:
                lo, hi = rob[t]["lo"], rob[t]["hi"]
                edge = min((abs(x - line), x, line) for x in (lo, hi) if x is not None
                           for line in (NEUTRAL_AT, DEMANDING_AT)) if lo is not None else None
                changes.append("  %-5s ROBUSTNESS %s -> %s   six-way range %s%s" % (
                    t, ra["tag"], rob[t]["tag"],
                    ("%.2f-%.2f" % (lo, hi)) if lo is not None else "—",
                    ("   (edge %.2f vs the %.2fx line: borderline, expect flicker)" % (edge[1], edge[2]))
                    if edge and edge[0] < 0.05 else ""))
        for t in sorted(set(blocked) - set(prev_blocked)):
            changes.append("  %-5s newly BLOCKED -- %s" % (t, blocked[t]))
    quiet = None
    if changes:
        L.extend(changes)
    else:
        moves = []
        for t, b in rec.items():
            a = prev_rec.get(t)
            if a and a.get("ratio") is not None and b.get("ratio") is not None:
                moves.append((abs(b["ratio"] - a["ratio"]), t, a["ratio"], b["ratio"]))
        if moves:
            mv = max(moves)
            quiet = ("No valuation input changed. Price moves only; no class crossed a line. "
                     "Largest ratio move: %s %.2f -> %.2f" % (mv[1], mv[2], mv[3]))
            L.append("  NO VALUATION INPUT CHANGED. Price moves only; no class crossed a line.")
            L.append("  largest ratio move: %s %.2f -> %.2f" % (mv[1], mv[2], mv[3]))
        else:
            L.append("  nothing to compare.")
    L.append("")

    # ---- 2. decision card --------------------------------------------------
    L.append("-" * 100)
    L.append("2. DECISION CARD -- today's directionals, then held names")
    L.append("-" * 100)
    L.append("  %-5s %-22s %-9s %-26s %-19s %6s %-12s %-24s %7s %s" % (
        "tk", "held in", "today", "executability", "class (ratio)", "P/E", "range 6x",
        "robust", "g impl", "DP-V2 gate"))
    order = directional + [t for t in sorted(held, key=lambda t: -(rec.get(t, {}).get("ratio") or -1))
                           if t not in directional]
    card = []
    for t in order:
        s = sig[t]
        f = rec.get(t)
        rb = rob.get(t)
        cls = rb["base"] if rb else "NO READ"
        why = blocked.get(t) or ("negative trailing ROE" if f and rb["base"] == "NO READ" else
                                 ("not in the valuation set" if not f else ""))
        if s["signal"] == "BUY":
            gate = DPV2_GATE[cls]
            flip = dpv2_flip(cls, s["conf"])
            gate_s = "%d%s" % (gate, ("  FLIP " + flip) if flip else "")
        else:
            gate_s = "n/a" if s["signal"] == "SELL" else ""
        cls_s = ("%s (%.2f)" % (cls, f["ratio"])) if f and f.get("ratio") is not None else "NO READ"
        rng = ("%.2f-%.2f" % (rb["lo"], rb["hi"])) if rb and rb["lo"] is not None else "—"
        rtag = rb["tag"] if rb else "—"
        if rb and rtag == "FRAGILE":
            bits = []
            if rb["route_flip"]:
                bits.append("route->" + rb["route_alt"][1][:5])
            if rb["r_flip"]:
                bits.append("r")
            rtag = "FRAGILE " + ",".join(bits) if bits else "FRAGILE corner"
        L.append("  %-5s %-22s %-9s %-26s %-19s %6s %-12s %-24s %7s %s" % (
            t, s["acct"] if s["held"] else "scout", "%s %d" % (s["signal"], s["conf"]),
            executability(s)[:26], cls_s, fmt(pe_lastfy(f), "{:.1f}") if f else "—", rng, rtag,
            fmt(f.get("g_impl"), "{:.2f}%") if f else "—", gate_s))
        if cls == "NO READ" and why:
            L.append("  %-5s   NO READ: %s" % ("", why))
        card.append(dict(ticker=t, held=s["held"], account=s["acct"], signal=s["signal"],
                         conf=s["conf"], executability=executability(s), cls=cls,
                         ratio=f.get("ratio") if f else None, pe_lastfy=pe_lastfy(f) if f else None,
                         lo=rb["lo"] if rb else None, hi=rb["hi"] if rb else None,
                         robust=rb["tag"] if rb else "—", robust_detail=rtag,
                         g_impl=f.get("g_impl") if f else None,
                         dpv2_gate=DPV2_GATE[cls] if s["signal"] == "BUY" else None,
                         dpv2_flip=dpv2_flip(cls, s["conf"]) if s["signal"] == "BUY" else None,
                         num_age_q=f.get("num_age") if f else None, no_read_reason=why or None))
    L.append("")
    L.append("  range 6x: the class ratio under both ROE routes (Schwab last-FY, EDGAR quarter x4)")
    L.append("  at r = 7/9/11%. ROBUST only if all six give the same class. NEITHER route is TTM.")
    L.append("  DP-V2 gate: BUY gate under the PROPOSED modifier (75 / 70 / 65); NOT APPLIED.")
    L.append("")

    # ---- 3. robustness, every classed name ---------------------------------
    L.append("-" * 100)
    L.append("3. ROBUSTNESS -- every classed name, the six combinations")
    L.append("-" * 100)
    L.append("  %-5s %-12s %8s %8s | %-12s %-12s %-12s | %-8s" % (
        "tk", "class @9%", "Schwab", "EDGAR", "r=7%", "r=9%", "r=11%", "tag"))
    for t in sorted(read, key=lambda t: -(rec[t].get("ratio") or 0)):
        rb = rob[t]
        L.append("  %-5s %-12s %8s %8s | %-12s %-12s %-12s | %-8s" % (
            t, rb["base"], fmt(rec[t].get("ratio")), fmt(rb["route_alt"][0]),
            *rb["r_classes"], rb["tag"]))
    n_rob = sum(1 for t in read if rob[t]["tag"] == "ROBUST")
    n_route = sum(1 for t in read if rob[t]["route_flip"])
    L.append("  ROBUST %d of %d.  The EDGAR route alone flips %d of %d." % (n_rob, len(read), n_route, len(read)))
    L.append("")

    # ---- 4. DP-V2 counterfactual flip ledger -------------------------------
    L.append("-" * 100)
    L.append("4. DP-V2 COUNTERFACTUAL FLIP LEDGER -- COUNTS ONLY. No outcome is read here.")
    L.append("-" * 100)
    classes_by_date = {}
    for d, p in exhibits.items():
        if DPV2_SINCE <= d <= date:
            r_, _ = parse_exhibit(p)
            classes_by_date[d] = {t: klass(f.get("ratio")) for t, f in r_.items()}
    flips, unscored = [], []
    if tracker:
        rows = [r for r in load_buy_rows(tracker, DPV2_SINCE) if r[0] <= date]
        flips, unscored = dpv2_ledger(rows, classes_by_date)
    for d, tk, c, cls, f, src in flips:
        L.append("  %s  %-5s BUY %3.0f  %-11s %-14s %s" % (d, tk, c, cls, f, src))
    if not flips:
        L.append("  no flip rows.")
    for d, tk, c, hint, pd_ in unscored:
        L.append("  %s  %-5s BUY %3.0f  UNSCORED -- no exhibit that session; %s on %s would flip it. "
                 "Not counted [?]" % (d, tk, c, hint, pd_))
    try:
        import trading_calendar as cal
        left = len(cal.sessions_between(date + dt.timedelta(days=1), DPV2_STOP))
    except Exception:                                              # noqa: BLE001
        left = None
    tks = sorted({f[1] for f in flips})
    L.append("  flip rows %d of %d needed   tickers %d of %d (%s)   stop %s%s" % (
        len(flips), DPV2_MIN_ROWS, len(tks), DPV2_MIN_TICKERS, ", ".join(tks) or "none",
        DPV2_STOP, ("   sessions left %d" % left) if left is not None else ""))
    L.append("  If the n condition is unmet on %s, DP-V2 is WITHDRAWN, NOT EXTENDED (memo 6)." % DPV2_STOP)
    L.append("  Rows dated on or before %s are BACKFILLED from the exhibit written that day;" % INSTALLED)
    L.append("  whether they count toward DP-V2's n is a ruling, not this tool's call.")
    L.append("")

    # ---- 5. book-free reads ------------------------------------------------
    L.append("-" * 100)
    L.append("5. BOOK-FREE READS -- context only, for names the class cannot read")
    L.append("-" * 100)
    L.append("  P/E band: the class's own lines restated as P/E (about %.0f and %.0f, section 6)," % (
        DEMANDING_AT / ((R_BASE - G_BASE) / 100 / (1 + G_BASE / 100)),
        NEUTRAL_AT / ((R_BASE - G_BASE) / 100 / (1 + G_BASE / 100))))
    L.append("  on the same last-FY eps, priced at Px@signal. Dividend-implied g: Gordon at r = 9%,")
    L.append("  g = (r - y)/(1 + y). It ignores buybacks, so it UNDERSTATES for buyback-heavy names.")
    pe_hi = DEMANDING_AT / ((R_BASE - G_BASE) / (100 + G_BASE))
    pe_lo = NEUTRAL_AT / ((R_BASE - G_BASE) / (100 + G_BASE))
    bf = []
    for t in sorted(set(held) | set(directional)):
        if t in rec and rob[t]["base"] != "NO READ":
            continue
        q = quotes.get(t, {})
        # price basis = Px@signal from the log, as every other figure in the layer
        eps, px, y = q.get("eps"), sig[t].get("px") or q.get("lastPrice"), q.get("divYield")
        pe = (px / eps) if (eps and eps > 0 and px) else None
        band = None if pe is None else ("DEMANDING-equiv" if pe >= pe_hi else
                                        ("NEUTRAL-equiv" if pe >= pe_lo else "UNDEMANDING-equiv"))
        gdiv = dividend_implied_g(y)
        etf = q.get("is_etf") or q.get("asset_type") not in (None, "EQUITY")
        note = "fund: distributions, not earnings" if etf else ""
        bf.append((t, pe, band, y, gdiv, note))
        L.append("  %-5s P/E %7s  %-18s divY %6s  dividend-implied g %7s  %s" % (
            t, fmt(pe, "{:.1f}"), band or "no positive eps", fmt(y, "{:.2f}%"),
            fmt(gdiv, "{:.2f}%"), note))
    L.append("")

    # ---- 6. identity check -------------------------------------------------
    L.append("-" * 100)
    L.append("6. IDENTITY CHECK -- the class ratio as a P/E: (P/EPS)(r-g)/(1+g) + g/((1+g)ROE)")
    L.append("-" * 100)
    worst, breach, checked = 0.0, [], 0
    for t in read:
        f = rec[t]
        recon = ratio_from(f["px"], f["bvps"], f["roe"])
        if recon is None or f.get("ratio") is None:
            continue
        checked += 1
        diff = abs(recon - f["ratio"])
        bound = f["ratio"] * (0.005 / f["px"] + 0.005 / f["bvps"] + 0.005 / f["roe"]) + 0.005
        worst = max(worst, diff)
        if diff > bound:
            breach.append("%s %.3f vs %.2f (bound %.3f)" % (t, recon, f["ratio"], bound))
    k = (R_BASE - G_BASE) / (100.0 + G_BASE)
    L.append("  %d names reconstructed; max |reconstructed - printed| = %.3f; outside the rounding "
             "bound: %s" % (checked, worst, ", ".join(breach) or "none"))
    L.append("  so the class is %.4f x last-FY P/E + %.4f/ROE: DEMANDING ~ P/E >= %.1f, UNDEMANDING ~ < %.1f" % (
        k, G_BASE / (100.0 + G_BASE), DEMANDING_AT / k, NEUTRAL_AT / k))
    L.append("  (the ROE term is small except at low ROE -- GM and SND carry the most of it)")
    if breach:
        findings.append("identity check FAILED for %s: implied_return's class no longer reconstructs "
                        "as a P/E within rounding -- its formula or inputs changed; re-read section 1"
                        % ", ".join(b.split()[0] for b in breach))
    unparsed = [t for t in sig if t not in rec and t not in blocked]
    L.append("")
    L.append("=" * 100)
    L.append("FINDINGS: %d" % len(findings))
    for x in findings:
        L.append("  - " + x)
    L.append("  not in the valuation set (dark, fund, scope or negative ROE): %s" % (", ".join(sorted(unparsed)) or "none"))
    L.append("=" * 100)
    L.append("Counterfactual only. No gate modified. No valuation asserted, no price target implied.")
    L.append("Advisory-only - no orders - not financial advice.")

    # ASCII only on the way out: the runners redirect stdout through the Windows
    # ANSI code page, and a stray non-ASCII dash should never cost an exhibit.
    L = [line.replace("\u2014", "-") for line in L]
    snapshot = dict(date=str(date), exhibit=os.path.basename(exhibits[date]),
                    log=os.path.basename(log_path), coverage=coverage, quiet=quiet,
                    identity_outside_bound=breach,
                    identity=dict(checked=checked, max_diff=worst, k=k,
                                  pe_demanding=DEMANDING_AT / k, pe_undemanding=NEUTRAL_AT / k),
                    previous=str(prev_date) if prev_date else None, card=card,
                    robustness={t: dict(cls=rob[t]["base"], ratio=rec[t].get("ratio"),
                                        edgar_ratio=rob[t]["route_alt"][0], tag=rob[t]["tag"],
                                        lo=rob[t]["lo"], hi=rob[t]["hi"],
                                        r_classes=rob[t]["r_classes"]) for t in rec},
                    changes=[c.strip() for c in changes],
                    dpv2=dict(flip_rows=len(flips), tickers=tks, needed_rows=DPV2_MIN_ROWS,
                              needed_tickers=DPV2_MIN_TICKERS, stop=str(DPV2_STOP),
                              sessions_left=left,
                              unscored=[dict(date=str(u[0]), ticker=u[1], conf=u[2], hint=u[3])
                                        for u in unscored],
                              rows=[dict(date=str(d), ticker=tk, conf=c, cls=cl, flip=f, source=s)
                                    for d, tk, c, cl, f, s in flips]),
                    book_free=[dict(ticker=t, pe=pe, band=b, div_yield=y, g_div=g, note=n)
                               for t, pe, b, y, g, n in bf],
                    identity_max_diff=worst, findings=findings)
    return "\n".join(L), snapshot, findings


# --------------------------------------------------------------------------- #
# Embed into the GENERATED report copy (value.bat step 5b, added 2026-10-14)
# --------------------------------------------------------------------------- #
#
# The report copy (tracker_with_registry.xlsx) is the file read as the final
# word, so the card belongs in it. Four rules, each with the failure it stops:
#
#   1. NEVER WHILE EXCEL HAS IT OPEN. Excel holds the file with a deny-write
#      share lock and keeps an owner file "~$<name>" beside it. Writing under
#      it either fails half-way or is silently overwritten when Excel next
#      saves. Both are checked; a stale owner file (Excel closed) is refused
#      too, with the instruction to delete it -- the 2026-08-04 one sat in the
#      root for ten weeks.
#   2. NEVER INTO THE MASTER. The master is manual entry only.
#   3. ONLY INTO TODAY'S COPY. build_near_miss_registry --emit-master-copy
#      rebuilds the copy from the master on every review run (and drops every
#      embedded sheet). If the copy's latest cohort is not the card's date, the
#      review has not run today: embedding would put today's card into
#      yesterday's report.
#   4. ATOMIC. Saved to a temporary file beside the copy, then swapped in with
#      os.replace, so a failure never leaves a half-written report copy.
#
# openpyxl does not keep Excel's cached formula results when it saves. The
# workbook is therefore flagged fullCalcOnLoad, and the Excel refresh (daily
# workflow step 6) belongs AFTER value.bat, not before it.

VC_SHEET = "Value Card"
VC_AFTER = ("Monitor Strip", "Actionable BUYs", "Near-Miss BUYs", "Signals")
MASTER_NAME = "claude_equity_bot_tracker.xlsx"


def _probe_write(path):
    """Open for writing and close at once. Excel's open denies other writers on
    Windows, so this raises PermissionError while the workbook is open."""
    fh = open(path, "r+b")
    fh.close()


def excel_holds(path):
    """(reason, detail) if Excel has, or appears to have, the workbook open;
    (None, None) when it is safe to write."""
    folder, base = os.path.split(os.path.abspath(path))
    owner = os.path.join(folder, "~$" + base)
    try:
        _probe_write(path)
    except PermissionError:
        return "IN USE", "Excel (or another program) has %s open. Close it, then re-run value.bat" % base
    if os.path.exists(owner):
        return "OWNER FILE", ("%s exists. If Excel is closed it is stale: delete it, then re-run"
                              % os.path.basename(owner))
    return None, None


def latest_cohort(wb):
    """Newest date in the Signals sheet's date column."""
    from build_actionable_registry import SIGNALS_SHEET, FIRST_DATA_ROW, COL, as_date
    ws = wb[SIGNALS_SHEET]
    best, blank = None, 0
    for (v,) in ws.iter_rows(min_row=FIRST_DATA_ROW, min_col=COL["date"], max_col=COL["date"],
                             values_only=True):
        d = as_date(v)
        if d is None:
            blank += 1
            if blank >= 25:
                break
            continue
        blank = 0
        best = d if best is None or d > best else best
    return best


def _write_sheet(ws, snap):
    from openpyxl.styles import Alignment, Font, PatternFill
    f_title = Font(bold=True, size=13)
    f_sec = Font(bold=True, size=11)
    f_hdr = Font(bold=True, size=10)
    f_note = Font(italic=True, size=9, color="FF6B6B6B")
    fill_hdr = PatternFill("solid", fgColor="FFE7E6E1")
    fill_rob = PatternFill("solid", fgColor="FFDDEFD9")
    fill_frag = PatternFill("solid", fgColor="FFF6E7C8")
    top = Alignment(vertical="top", wrap_text=False)
    r = [1]

    def put(values, font=None, fill=None):
        for c, v in enumerate(values, start=1):
            cell = ws.cell(r[0], c, v)
            cell.alignment = top
            if font is not None:
                cell.font = font
            if fill is not None:
                cell.fill = fill
        r[0] += 1

    def gap():
        r[0] += 1

    d = snap["date"]
    put(["Value Card -- %s" % d], f_title)
    put(["as of %s | built by value_card.py from %s, %s, quote_dump.json and the master | "
         "COUNTERFACTUAL ONLY: modifies no gate, reads no outcome | advisory-only, no orders"
         % (d, snap["exhibit"], snap.get("log", "the signals log"))], f_note)
    gap()
    cv = snap["coverage"]
    put(["Coverage"], f_sec)
    put(["watchlist %d, classed %d, ROBUST %d | held %d, classed %d, ROBUST %d (%s) | "
         "today's directionals %d, classed %d (%s)" % (
             cv["watchlist"], cv["classed"], cv["robust"], cv["held"], cv["held_classed"],
             len(cv["held_robust"]), ", ".join(cv["held_robust"]) or "none",
             cv["directional"], len(cv["directional_classed"]),
             ", ".join(cv["directional_classed"]) or "none")])
    gap()
    put(["What changed since %s" % (snap.get("previous") or "(no earlier exhibit)")], f_sec)
    for line in (snap["changes"] or [snap.get("quiet") or "Nothing to compare."]):
        put([line])
    gap()
    put(["Decision card -- today's directionals, then held names"], f_sec)
    hdr = ["Ticker", "Held in", "Today", "Conf", "Executability", "Class", "Ratio",
           "Last-FY P/E", "Range low", "Range high", "Robust", "Why fragile", "Implied g %",
           "DP-V2 gate (not applied)", "Would flip", "NO READ reason"]
    put(hdr, f_hdr, fill_hdr)
    for c in snap["card"]:
        detail = (c.get("robust_detail") or "").replace("FRAGILE", "").strip()
        tag = c["robust"] if c["robust"] != "—" else ""
        put([c["ticker"], c["account"] if c["held"] else "scout", c["signal"], c["conf"],
             c["executability"].replace("—", ""), c["cls"], c["ratio"], c["pe_lastfy"],
             c["lo"], c["hi"], tag, detail, c["g_impl"], c.get("dpv2_gate"),
             c.get("dpv2_flip") or "", c.get("no_read_reason") or ""],
            fill=fill_rob if tag == "ROBUST" else (fill_frag if tag == "FRAGILE" else None))
    put(["Range: the class ratio under both ROE routes (Schwab last-FY, EDGAR quarter x4) at "
         "r = 7/9/11%. ROBUST only if all six give the same class. Neither route is TTM."], f_note)
    gap()
    put(["Robustness -- every classed name"], f_sec)
    put(["Ticker", "Class @9%", "Schwab ratio", "EDGAR ratio", "r = 7%", "r = 9%", "r = 11%", "Tag"],
        f_hdr, fill_hdr)
    rb = snap["robustness"]
    for t in sorted((t for t in rb if rb[t]["cls"] != "NO READ"),
                    key=lambda t: -(rb[t]["ratio"] or 0)):
        x = rb[t]
        put([t, x["cls"], x["ratio"], x["edgar_ratio"], *x.get("r_classes", ["", "", ""]), x["tag"]],
            fill=fill_rob if x["tag"] == "ROBUST" else fill_frag)
    gap()
    dp = snap["dpv2"]
    put(["DP-V2 counterfactual flip ledger -- COUNTS ONLY, no outcome read"], f_sec)
    put(["flip rows %d of %d needed | tickers %d of %d (%s) | stop %s | sessions left %s | "
         "withdrawn, not extended, if unmet on the stop date" % (
             dp["flip_rows"], dp["needed_rows"], len(dp["tickers"]), dp["needed_tickers"],
             ", ".join(dp["tickers"]) or "none", dp["stop"], dp.get("sessions_left"))])
    put(["Date", "Ticker", "BUY conf", "Class that day", "Flip", "Source"], f_hdr, fill_hdr)
    for x in dp["rows"]:
        put([x["date"], x["ticker"], x["conf"], x["cls"], x["flip"], x["source"]])
    for x in dp.get("unscored", []):
        put([x["date"], x["ticker"], x["conf"], "UNSCORED (prior: %s)" % x["hint"],
             "not counted", "no exhibit that session"])
    gap()
    put(["Book-free reads -- context only"], f_sec)
    put(["Ticker", "P/E (last-FY eps, Px@signal)", "P/E band", "Div yield %",
         "Dividend-implied g %", "Note"], f_hdr, fill_hdr)
    for x in snap["book_free"]:
        put([x["ticker"], x["pe"], x["band"] or "no positive eps", x["div_yield"], x["g_div"],
             x["note"]])
    gap()
    idn = snap.get("identity", {})
    put(["Identity check"], f_sec)
    put(["class = %.4f x last-FY P/E + %.4f/ROE (DEMANDING ~ P/E >= %.1f, UNDEMANDING ~ < %.1f) | "
         "%d names reconstructed, max diff %.3f | outside rounding bound: %s" % (
             idn.get("k", 0), G_BASE / (100.0 + G_BASE), idn.get("pe_demanding", 0),
             idn.get("pe_undemanding", 0), idn.get("checked", 0), idn.get("max_diff", 0),
             ", ".join(snap.get("identity_outside_bound") or []) or "none")])
    if snap.get("findings"):
        put(["FINDINGS: " + " | ".join(snap["findings"])], f_sec)
    # number formats and widths
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, float):
                cell.number_format = "0.00"
    widths = [8, 22, 7, 6, 26, 13, 8, 11, 10, 10, 9, 16, 11, 14, 15, 48]
    from openpyxl.utils import get_column_letter
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A3"


def embed(snap, copy_path, master_path=None):
    """Write/refresh the Value Card sheet in the report copy. Returns
    (ok, message). Never raises for an expected refusal."""
    import openpyxl
    base = os.path.basename(copy_path).lower()
    if base == MASTER_NAME or (master_path and os.path.abspath(copy_path) == os.path.abspath(master_path)):
        return False, "REFUSED: %s is the MASTER. The card is embedded into the report copy only." % copy_path
    if not os.path.exists(copy_path):
        return False, "REFUSED: %s not found. Run run_daily_review.bat first." % copy_path
    why, detail = excel_holds(copy_path)
    if why:
        return False, "REFUSED (%s): %s." % (why, detail)
    wb = openpyxl.load_workbook(copy_path)            # data_only=False: keep formulas
    newest = latest_cohort(wb)
    if str(newest) != snap["date"]:
        wb.close()
        return False, ("REFUSED: the report copy's latest cohort is %s, the card's is %s -- "
                       "run_daily_review.bat has not rebuilt it for today." % (newest, snap["date"]))
    if VC_SHEET in wb.sheetnames:
        del wb[VC_SHEET]                              # replace, never stack
    ws = wb.create_sheet(VC_SHEET)
    _write_sheet(ws, snap)
    for after in VC_AFTER:
        if after in wb.sheetnames and after != VC_SHEET:
            target = wb.sheetnames.index(after) + 1
            wb.move_sheet(VC_SHEET, offset=target - wb.sheetnames.index(VC_SHEET))
            break
    try:
        wb.calculation.fullCalcOnLoad = True          # cached results are gone; recalc on open
    except AttributeError:
        pass
    tmp = copy_path + ".vc-tmp"
    try:
        wb.save(tmp)
        why, detail = excel_holds(copy_path)          # re-check: Excel may have opened it meanwhile
        if why:
            return False, "REFUSED (%s) at save time: %s. Nothing was changed." % (why, detail.rstrip("."))
        os.replace(tmp, copy_path)
    except PermissionError as e:
        return False, "REFUSED: could not replace %s (%s). Nothing was changed." % (copy_path, e)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return True, "EMBEDDED: sheet '%s' (%d card rows) written into %s for %s." % (
        VC_SHEET, len(snap["card"]), os.path.basename(copy_path), snap["date"])


# --------------------------------------------------------------------------- #
# Self-test (positive and negative cases)
# --------------------------------------------------------------------------- #

def _selftest():
    import tempfile
    fails = []

    def check(name, ok):
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        if not ok:
            fails.append(name)

    # thresholds and flips
    check("2.00x is DEMANDING", klass(2.00) == "DEMANDING")
    check("1.9999x is NEUTRAL", klass(1.9999) == "NEUTRAL")
    check("1.50x is NEUTRAL", klass(1.50) == "NEUTRAL")
    check("1.4999x is UNDEMANDING", klass(1.4999) == "UNDEMANDING")
    check("no ratio is NO READ", klass(None) == "NO READ")
    check("DEMANDING BUY 74 flips ADMIT->REJECT", dpv2_flip("DEMANDING", 74) == "ADMIT->REJECT")
    check("DEMANDING BUY 75 does not flip", dpv2_flip("DEMANDING", 75) is None)
    check("UNDEMANDING BUY 65 flips REJECT->ADMIT", dpv2_flip("UNDEMANDING", 65) == "REJECT->ADMIT")
    check("UNDEMANDING BUY 64 does not flip", dpv2_flip("UNDEMANDING", 64) is None)
    check("NEUTRAL BUY 72 does not flip", dpv2_flip("NEUTRAL", 72) is None)
    check("NO READ BUY 70 does not flip", dpv2_flip("NO READ", 70) is None)

    # identity: NVDA 2026-10-14 as printed by implied_return
    nv = dict(px=223.70, bvps=9.44, roe=51.92)
    check("identity reproduces NVDA 2.72x", abs(ratio_from(**nv) - 2.72) < 0.02)
    eps = nv["roe"] / 100 * nv["bvps"]
    k = (R_BASE - G_BASE) / (100 + G_BASE)
    check("ratio == k*P/E + g/((1+g)ROE) exactly",
          abs(ratio_from(**nv) - (k * nv["px"] / eps + (0.03 / 1.03) / 0.5192)) < 1e-9)
    check("BVPS cancels: doubling BVPS and halving ROE leaves the P/E term unchanged",
          abs(k * nv["px"] / eps - k * nv["px"] / ((nv["roe"] / 2 / 100) * (nv["bvps"] * 2))) < 1e-9)
    check("NEGATIVE: non-positive ROE gives no ratio", ratio_from(100, 10, -5) is None)

    # decomposition sums to the total
    a = dict(px=210.57, bvps=8.01, roe=61.17)
    b = dict(px=218.16, bvps=9.44, roe=51.92)
    dec = decompose(a, b)
    check("price + filing == total move", abs(dec["price"] + dec["filing"] - (dec["r1"] - dec["r0"])) < 1e-12)

    # robustness on a synthetic record
    f = dict(ratio=2.72, roe=51.92, roe_edgar=104.27, i7=94.97, i9=140.99, i11=187.02)
    rb = robustness(f)
    check("NVDA-like record is FRAGILE with a route flip", rb["tag"] == "FRAGILE" and rb["route_flip"])
    f2 = dict(ratio=6.03, roe=10.76, roe_edgar=18.73, i7=44.21, i9=64.87, i11=85.52)
    check("PWR-like record is ROBUST", robustness(f2)["tag"] == "ROBUST")

    # Gordon solved for g
    g = dividend_implied_g(3.0)
    check("dividend-implied g at y=3% is (9-3)/1.03", abs(g - 6.0 / 1.03) < 1e-9)
    check("NEGATIVE: no yield gives no g", dividend_implied_g(0) is None)

    # parsing real-format lines, then the end-to-end refusal paths
    tmp = tempfile.mkdtemp(prefix="value_card_selftest_")
    ex = "\n".join([
        "-" * 100, "1. INPUTS -- ROE is trailing eps over book value per share", "-" * 100,
        "    tk      anchor      BVPS  px(master)   drift      ROE     M/B  divY%  anc.age num.age  ROE basis",
        "  NVDA  2026-07-26      9.44      223.70  -1.01%   51.92%   23.70   0.44     0.9Q    2.9Q  Schwab last-FY",
        "", "-" * 100, "1a. THE TWO ROE ROUTES", "-" * 100,
        "  NVDA   Q2      51.92%     104.27%   +52.34  EDGAR quarterly x4",
        "", "-" * 100, "4. (II) WHAT ROE MUST THE MARKET BELIEVE?   <-- the headline read", "-" * 100,
        "  NVDA   23.70     51.92%     94.97%    140.99%    187.02%                   2.72x",
        "", "-" * 100, "4b. (III) WHAT GROWTH MUST THE MARKET BELIEVE?", "-" * 100,
        "  NVDA   23.70   0.9797        5.13%          6.95%  g (III)",
        "", "-" * 100, "5. WHY", "-" * 100,
        "         PM NOT COMPUTED -- book equity is non-positive (-8.58B); M/B undefined", ""])
    p = os.path.join(tmp, "implied_return_2026-10-14.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(ex)
    rec, bl = parse_exhibit(p)
    check("parses section 1 with the vintage columns", rec.get("NVDA", {}).get("num_age") == 2.9)
    check("parses the EDGAR route", rec["NVDA"].get("roe_edgar") == 104.27)
    check("parses the class ratio and g", rec["NVDA"].get("ratio") == 2.72 and rec["NVDA"].get("g_impl") == 6.95)
    check("parses a blocked name", "PM" in bl)
    log = os.path.join(tmp, "signals_2026-10-14.log")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("x | [PHASE 3-C DRY RUN] [Roth IRA,Individual] [HELD] NVDA | Signal: BUY | "
                 "Confidence: 74% | Risk: APPROVED | Reason: x PER-ACCOUNT: Roth IRA=APPROVED; "
                 "Individual=REJECTED. | H1[]\n")
    s = parse_log(log)
    check("parses held, accounts and per-account", s["NVDA"]["held"] and
          executability(s["NVDA"]) == "PARTIAL (Roth IRA only)")
    txt, snap, _ = build(dt.date(2026, 10, 14), tmp, log, None, None)
    check("end to end: the card carries NVDA and its counterfactual flip",
          "FLIP ADMIT->REJECT" in txt and snap["card"][0]["ticker"] == "NVDA")
    try:
        build(dt.date(2026, 10, 15), tmp, log, None, None)
        check("NEGATIVE: a date with no exhibit refuses", False)
    except SystemExit as e:
        check("NEGATIVE: a date with no exhibit refuses", isinstance(e.code, tuple) and e.code[1] == 2)
    check("NEGATIVE: the report copy is refused as --tracker",
          main(["--date", "2026-10-14", "--root", tmp, "--log", log, "--tracker",
                os.path.join(tmp, REFUSED), "--md", os.path.join(tmp, "x.md")]) == 2)
    # ---- the embed: guards first, then the write ----
    import openpyxl
    copy = os.path.join(tmp, "tracker_with_registry.xlsx")
    wb = openpyxl.Workbook()
    wb.active.title = "Signals"
    wb["Signals"].cell(5, 1, dt.datetime(2026, 10, 14))
    wb["Signals"].cell(5, 2, "NVDA")
    wb["Signals"]["K5"] = "=1+1"                       # a formula must survive the embed
    wb.create_sheet("Monitor Strip")
    wb.create_sheet("How to Use")
    wb.save(copy)
    snap_j = json.loads(json.dumps(snap, default=str))
    ok, msg = embed(snap_j, copy)
    names = openpyxl.load_workbook(copy).sheetnames
    check("embed writes the sheet right after Monitor Strip",
          ok and names.index(VC_SHEET) == names.index("Monitor Strip") + 1)
    ok2, _ = embed(snap_j, copy)
    check("re-embedding replaces, never stacks",
          ok2 and openpyxl.load_workbook(copy).sheetnames.count(VC_SHEET) == 1)
    check("formulas in the copy survive the embed",
          openpyxl.load_workbook(copy)["Signals"]["K5"].value == "=1+1")
    check("no temporary file is left behind", not os.path.exists(copy + ".vc-tmp"))
    owner = os.path.join(tmp, "~$tracker_with_registry.xlsx")
    open(owner, "w").close()
    ok3, msg3 = embed(snap_j, copy)
    check("NEGATIVE: an Excel owner file refuses the write", not ok3 and "OWNER FILE" in msg3)
    os.remove(owner)
    global _probe_write
    real = _probe_write

    def _held(path):
        raise PermissionError(13, "in use")
    _probe_write = _held
    try:
        before = os.path.getmtime(copy)
        ok4, msg4 = embed(snap_j, copy)
        check("NEGATIVE: a workbook open in Excel refuses the write, file untouched",
              not ok4 and "IN USE" in msg4 and os.path.getmtime(copy) == before)
    finally:
        _probe_write = real
    stale = dict(snap_j, date="2026-10-15")
    ok5, msg5 = embed(stale, copy)
    check("NEGATIVE: a copy the review has not rebuilt today is refused", not ok5 and "latest cohort" in msg5)
    ok6, msg6 = embed(snap_j, os.path.join(tmp, "claude_equity_bot_tracker.xlsx"))
    check("NEGATIVE: the master is never written", not ok6 and "MASTER" in msg6)
    print("SELFTEST %s (%d failed)" % ("PASSED" if not fails else "FAILED", len(fails)))
    return 1 if fails else 0


# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--tracker", help="the MASTER (logs\\claude_equity_bot_tracker.xlsx)")
    ap.add_argument("--log", help="logs\\signals_<date>.log")
    ap.add_argument("--quotes", default="quote_dump.json")
    ap.add_argument("--md", help="output exhibit (default value_card_<date>.md)")
    ap.add_argument("--json", help="also write a machine-readable snapshot here")
    ap.add_argument("--embed-from", help="a value_card_<date>.json snapshot to embed")
    ap.add_argument("--embed-into", help="the GENERATED report copy (tracker_with_registry.xlsx)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if a.embed_from or a.embed_into:
        if not (a.embed_from and a.embed_into):
            print("COULD NOT RUN: --embed-from and --embed-into go together.")
            return 2
        if not os.path.exists(a.embed_from):
            print("COULD NOT RUN: snapshot %s not found -- step 5 did not write it." % a.embed_from)
            return 2
        with open(a.embed_from, encoding="utf-8") as fh:
            snap = json.load(fh)
        ok, msg = embed(snap, a.embed_into, a.tracker)
        print("  " + msg)
        return 0 if ok else 2
    date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    if a.tracker and os.path.basename(a.tracker).lower() == REFUSED:
        print("REFUSED: %s is the GENERATED REPORT COPY, never an input. Pass the MASTER." % REFUSED)
        return 2
    log = a.log or os.path.join(a.root, "logs", "signals_%s.log" % date)
    if not os.path.exists(log):
        print("COULD NOT RUN: no signals log at %s" % log)
        return 2
    if a.tracker and not os.path.exists(a.tracker):
        print("COULD NOT RUN: master not found at %s" % a.tracker)
        return 2
    try:
        text, snap, findings = build(date, a.root, log, a.quotes, a.tracker)
    except SystemExit as e:
        msg, code = e.code if isinstance(e.code, tuple) else (str(e.code), 2)
        print("COULD NOT RUN: %s" % msg)
        return code
    md = a.md or os.path.join(a.root, "value_card_%s.md" % date)
    with open(md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# value_card exhibit\n\n```\n" + text + "\n```\n")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=1, default=str)
    print(text)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
