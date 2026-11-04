#!/usr/bin/env python3
"""
feed_consistency.py - does the quote feed agree with itself, and does the
data-quality rating hold still? REPORTS ONLY.

Claude Equity Bot - Phase 3-C - advisory-only - no orders (DP-T1).

WHY THIS EXISTS (added 2026-11-03, change E, approved by Rob 2026-11-03)
    The SPCX risk-flag review (claude/SPCX_RiskFlags_Review_2026-11-03.md)
    found that the prompt shows Schwab's `eps` and `peRatio` side by side as
    "P/E Ratio | EPS" with no period. They are on different bases:
        eps      last fiscal year (DOW's -3.70152 is its FY2025 EPS exactly)
        peRatio  price / trailing 12 months
    and for two 2026 IPOs (SPCX, CBRS) `eps` is 0.0 while the same payload's
    P/E is non-zero, which no real 0.0 could produce. The model flagged it,
    misdiagnosed it, and SPCX's data_quality alternated MEDIUM/HIGH while
    the defect stayed constant. Fixing the prompt is a Phase 4b item
    (DP-3C-ai freezes what the model sees). This tool only COUNTS, so the
    defect is visible every day until then.

WHAT IT REPORTS (pre-registered 2026-11-03; triggers are reporting
thresholds, not bars, and nothing gates on them)
    1. Feed EPS against the feed's own P/E, equities only (the prompt shows
       neither for ETFs). implied = price / peRatio, the 12-month EPS the
       P/E implies. Each equity gets ONE finding, first match wins:
         ZERO     eps == 0 and peRatio non-zero: a contradictory zero
         MISSING  eps absent and peRatio non-zero: renders "N/A" (08-17 rule)
         NO P/E   peRatio absent or zero: no implied figure
         SIGN     eps and implied have opposite signs
         GAP      |eps / implied - 1| >= 25%: the two bases diverge
         ok       otherwise
       25% sits far above the price-basis noise (the P/E may be struck on a
       different price than lastPrice; that moves the ratio by a few %).
    2. Per-name data_quality flips over the last N sessions (default 10),
       read AM-canonically with signal_scan.parse_log from every log
       signal_logs.discover finds (archive subfolders included, Retired/
       excluded). A flip is a change between consecutive sessions in which
       the name was rated; a missing session is skipped, not a flip.
       UNSTABLE = 2 or more flips in the window.
    The two are shown side by side. That is CO-OCCURRENCE, NOT CAUSE: a
    rating can move because a filing, a headline or the price moved.

WHERE THE QUOTE COMES FROM
    Primary: logs/inputs_<date>.jsonl, field `quote` (capture_version 2,
    change D, from the 2026-11-04 run). That is the exact quote the AM
    prompt was built from; the first record per ticker wins (a PM rerun
    appends later lines).
    Fallback: quote_dump.json, labelled with its capture time. In the
    evening chain scan.bat runs BEFORE value.bat refreshes it, so on a
    normal evening it is the PRIOR session's close capture. Good enough for
    ZERO and MISSING (the fiscal-year eps does not move day to day); the
    gap figures are approximate.

WHAT IT DOES NOT DO
    It writes one markdown file and prints a few lines. It reads no
    workbook, writes no log, changes no prompt, damping, population or
    gate, and never changes the scan verdict: scan.bat ignores its exit
    code apart from printing a note when it could not run.

Exit 0 = ran (findings or not). Exit 2 = could not run.

Usage
    python feed_consistency.py                       (today)
    python feed_consistency.py --date 2026-11-03 --sessions 10 --md out.md
    python feed_consistency.py --selftest
"""

import argparse
import datetime as dt
import json
import os
import statistics
import sys

GAP_TRIGGER = 0.25          # pre-registered 2026-11-03: reporting trigger, not a bar
UNSTABLE_FLIPS = 2          # pre-registered 2026-11-03: reporting trigger, not a bar
DEFAULT_SESSIONS = 10
ORDER = {"ZERO": 0, "MISSING": 1, "SIGN": 2, "GAP": 3, "NO P/E": 4, "ok": 5}
DQ_SHORT = {"HIGH": "H", "MEDIUM": "M", "LOW": "L"}


# ---------------------------------------------------------------------------
# 1 - the quote source
# ---------------------------------------------------------------------------

def load_quotes(rundate, inputs_dir="logs", quote_dump="quote_dump.json"):
    """({ticker: quote}, source_label, is_primary). Never raises."""
    path = os.path.join(inputs_dir, f"inputs_{rundate}.jsonl")
    quotes = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    q = rec.get("quote")
                    tk = rec.get("ticker")
                    if tk and isinstance(q, dict) and tk not in quotes:
                        quotes[tk] = q
        except (OSError, ValueError):
            quotes = {}
    if quotes:
        return quotes, f"AM prompt quote, {path} (capture_version 2)", True

    if os.path.exists(quote_dump):
        try:
            with open(quote_dump, encoding="utf-8") as fh:
                d = json.load(fh)
            qs = d.get("quotes") or {}
            if isinstance(qs, list):
                qs = {q.get("ticker"): q for q in qs if isinstance(q, dict)}
            if qs:
                cap = str(d.get("captured_local") or "?")
                why = ("no capture_version-2 records for this date"
                       if os.path.exists(path) else f"no {path}")
                stale = "" if cap[:10] == rundate else f"; NOT {rundate}'s quote"
                return qs, (f"FALLBACK {quote_dump} captured {cap} ({why}{stale}). "
                            f"Gap figures are approximate"), False
        except (OSError, ValueError):
            pass
    return {}, "NO QUOTE SOURCE (no capture_version-2 inputs and no readable quote_dump.json)", False


def _num(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def classify(q):
    """One finding for one quote. Returns a dict, or None for an ETF."""
    if q.get("is_etf"):
        return None
    eps, pe = _num(q.get("eps")), _num(q.get("peRatio"))
    price = _num(q.get("lastPrice")) or _num(q.get("closePrice"))
    implied = (price / pe) if (price and pe) else None
    ratio = (eps / implied + 0.0) if (eps is not None and implied) else None   # +0.0: no "-0.00"
    if eps == 0 and pe:
        code = "ZERO"
    elif eps is None and pe:
        code = "MISSING"
    elif not pe or implied is None:
        code = "NO P/E"
    elif eps * implied < 0:
        code = "SIGN"
    elif abs(ratio - 1) >= GAP_TRIGGER:
        code = "GAP"
    else:
        code = "ok"
    return {"eps": eps, "pe": pe, "price": price, "implied": implied,
            "ratio": ratio, "code": code}


def feed_findings(quotes):
    rows, etfs = {}, []
    for tk, q in quotes.items():
        c = classify(q)
        if c is None:
            etfs.append(tk)
        else:
            rows[tk] = c
    return rows, sorted(etfs)


# ---------------------------------------------------------------------------
# 2 - data-quality flips
# ---------------------------------------------------------------------------

def dq_history(rundate, sessions=DEFAULT_SESSIONS, pattern=os.path.join("logs", "signals_*.log")):
    """({ticker: [(date, 'H'|'M'|'L'), ...]}, [session dates], logs_report)."""
    import signal_logs
    import signal_scan
    paths, info = signal_logs.discover(pattern)
    dated = [(signal_logs.log_date(p), p) for p in paths]
    dated = [(d, p) for d, p in dated if d and d.isoformat() <= rundate]
    window = dated[-sessions:] if sessions > 0 else dated
    hist = {}
    for d, p in window:
        recs, _warn = signal_scan.parse_log(p)
        for r in recs:
            dq = (r.get("dq") or "").upper()
            if dq:
                hist.setdefault(r["ticker"], []).append((d.isoformat(), DQ_SHORT.get(dq, dq[:1])))
    return hist, [d.isoformat() for d, _ in window], signal_logs.report(info, indent="")


def flips(seq):
    vals = [v for _, v in seq]
    return sum(1 for a, b in zip(vals, vals[1:]) if a != b)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _f(v, spec):
    return "--" if v is None else format(v, spec)


def render(rundate, rows, etfs, source, hist, window, logs_line, n_sessions):
    out = [f"# Feed consistency - {rundate}", "",
           "*REPORTS ONLY. Nothing here changes the scan verdict, the prompt, damping "
           "or the population (DP-3C-ai). Change E, 2026-11-03. "
           "Advisory-only - no orders - not financial advice.*", ""]

    # --- 1
    codes = {}
    for tk, r in rows.items():
        codes.setdefault(r["code"], []).append(tk)
    n_eq = len(rows)
    gaps = [abs(r["ratio"] - 1) for r in rows.values()
            if r["ratio"] is not None and r["code"] in ("GAP", "SIGN", "ok")]
    out += ["## 1 - Feed EPS against the feed's own P/E", "",
            f"Source: {source}.", ""]
    if not rows:
        out += ["No equity quotes to check.", ""]
    else:
        out += ["| Finding | Count | Names |", "|---|---:|---|"]
        for code in sorted(codes, key=lambda c: ORDER.get(c, 9)):
            out.append(f"| {code} | {len(codes[code])} | {', '.join(sorted(codes[code]))} |")
        out += ["", f"{n_eq} equities checked; {len(etfs)} ETFs skipped (the prompt shows "
                f"neither P/E nor EPS for ETFs)."]
        if gaps:
            out.append(f"Median |eps / implied - 1| across the {len(gaps)} with a non-zero eps: "
                       f"{statistics.median(gaps):.0%}.")
        out += ["", "| Ticker | eps (feed, last FY) | P/E (feed, TTM) | Price | Implied TTM EPS "
                "(price / P/E) | eps / implied | Finding |",
                "|---|---:|---:|---:|---:|---:|---|"]
        for tk in sorted(rows, key=lambda t: (ORDER.get(rows[t]["code"], 9), t)):
            r = rows[tk]
            out.append(f"| {tk} | {_f(r['eps'], '.4g')} | {_f(r['pe'], '.2f')} | "
                       f"{_f(r['price'], '.2f')} | {_f(r['implied'], '.3f')} | "
                       f"{_f(r['ratio'], '.2f')} | {r['code']} |")
        out += ["", "ZERO = eps 0 with a non-zero P/E (no real 0.0 can produce a non-zero P/E). "
                "MISSING = no eps, renders N/A. SIGN = opposite signs. "
                f"GAP = the two bases differ by {GAP_TRIGGER:.0%} or more. "
                "Both bases are the feed's own; neither is checked against SEC here.", ""]

    # --- 2
    out += [f"## 2 - data_quality stability, last {n_sessions} sessions", "",
            f"Logs: {logs_line}. Window read: "
            f"{(window[0] + ' .. ' + window[-1]) if window else 'none'} ({len(window)} session(s)).", ""]
    if len(window) < n_sessions:
        out += [f"Only {len(window)} of {n_sessions} sessions are visible; counts cover those only.", ""]
    if not hist:
        out += ["No rated rows found.", ""]
    else:
        per = {tk: (flips(seq), seq) for tk, seq in hist.items()}
        n_flip_names = sum(1 for f, _ in per.values() if f)
        tot_f = sum(f for f, _ in per.values())
        tot_t = sum(max(len(s) - 1, 0) for _, s in per.values())
        unstable = sorted((tk for tk, (f, _) in per.items() if f >= UNSTABLE_FLIPS),
                          key=lambda t: (-per[t][0], t))
        out += [f"{len(per)} names rated; {n_flip_names} changed rating at least once; "
                f"{tot_f} flips in {tot_t} session-to-session transitions"
                + (f" ({tot_f / tot_t:.0%})." if tot_t else ".")
                + f" UNSTABLE ({UNSTABLE_FLIPS}+ flips): {len(unstable)}.", ""]
        shown = sorted((tk for tk, (f, _) in per.items() if f),
                       key=lambda t: (-per[t][0], t))
        if shown:
            out += ["| Ticker | Flips | Rated sessions | Sequence (oldest first) | Feed finding today |",
                    "|---|---:|---:|---|---|"]
            for tk in shown:
                f, seq = per[tk]
                feed = rows.get(tk, {}).get("code", "ETF" if tk in etfs else "--")
                out.append(f"| {tk}{' (UNSTABLE)' if f >= UNSTABLE_FLIPS else ''} | {f} | "
                           f"{len(seq)} | {' '.join(v for _, v in seq)} | {feed} |")
            out.append("")
        flagged_stable = sorted(tk for tk, r in rows.items()
                                if r["code"] in ("ZERO", "MISSING", "SIGN")
                                and tk in per and per[tk][0] == 0)
        if flagged_stable:
            out += ["Feed-flagged names whose rating did NOT move in the window: "
                    + ", ".join(f"{tk} ({''.join(sorted(set(v for _, v in per[tk][1])))})"
                                for tk in flagged_stable)
                    + ". The feed artifact alone does not make a rating unstable.", ""]

    out += ["## 3 - How to read this", "",
            "- Section 2 beside section 1 is co-occurrence, not cause. A rating can move "
            "because a filing, a headline or the price moved.",
            "- The fix for what the model is shown (label the EPS bases; render a contradictory "
            "zero as N/A) is Phase 4b, pre-registered after the exit. Until then this file "
            "is the daily count.",
            "- Source review: claude/SPCX_RiskFlags_Review_2026-11-03.md.", ""]
    return "\n".join(out)


def console(rows, etfs, source, hist, window, primary):
    codes = {}
    for tk, r in rows.items():
        codes.setdefault(r["code"], []).append(tk)
    lines = []
    if rows:
        z = sorted(codes.get("ZERO", []))
        lines.append(f"  feed EPS vs feed P/E: {len(z)} contradictory zero"
                     f"{' (' + ', '.join(z) + ')' if z else ''}; "
                     f"{len(codes.get('MISSING', []))} missing; "
                     f"{len(codes.get('SIGN', []))} sign; {len(codes.get('GAP', []))} basis gap >= "
                     f"{GAP_TRIGGER:.0%}; of {len(rows)} equities ({len(etfs)} ETFs skipped)")
    lines.append("  quote source: " + ("AM prompt quote (inputs jsonl, capture_version 2)" if primary
                 else source.split(" (")[0] + "; gap figures approximate" if source.startswith("FALLBACK")
                 else source))
    if hist:
        per = {tk: flips(s) for tk, s in hist.items()}
        unst = sorted((t for t, f in per.items() if f >= UNSTABLE_FLIPS), key=lambda t: (-per[t], t))
        tag = lambda t: (f"{t} {per[t]}" + (f" [{rows[t]['code']}]" if t in rows and rows[t]['code'] != 'ok' else ""))
        lines.append(f"  DQ flips, {len(window)} session(s): {sum(1 for f in per.values() if f)} of "
                     f"{len(per)} names moved; UNSTABLE ({UNSTABLE_FLIPS}+): "
                     + (", ".join(tag(t) for t in unst) if unst else "none"))
    else:
        lines.append("  DQ flips: no rated rows in the window")
    lines.append("  REPORTS ONLY - the scan verdict and everything the model sees are unchanged.")
    return "\n".join(lines)


def run(rundate, sessions, md_path, inputs_dir="logs", quote_dump="quote_dump.json",
        pattern=os.path.join("logs", "signals_*.log"), quiet=False):
    quotes, source, primary = load_quotes(rundate, inputs_dir, quote_dump)
    rows, etfs = feed_findings(quotes)
    hist, window, logs_line = dq_history(rundate, sessions, pattern)
    if not quotes and not window:
        if not quiet:
            print("  feed_consistency: nothing to read (no quote source and no signals logs).")
        return 2, None
    text = render(rundate, rows, etfs, source, hist, window, logs_line, sessions)
    if md_path:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if not quiet:
        print(console(rows, etfs, source, hist, window, primary))
        if md_path:
            print(f"  detail: {md_path}")
    return 0, text


# ---------------------------------------------------------------------------
# selftest - synthetic files only; negative cases included
# ---------------------------------------------------------------------------

def _st_line(date, tk, dq, n):
    payload = {"ticker": tk, "signal": "HOLD", "confidence": 60, "data_quality": dq,
               "prompt_variant": "C2", "lastPrice": 10.0}
    return (f"{date} 09:30:{n:02d},000 | INFO | Signal JSON: {json.dumps(payload)} | "
            f"[PHASE 3-C DRY RUN] [Individual] [SCOUT] {tk} | Signal: HOLD | Confidence: 60%")


def selftest():
    import tempfile
    fails = []

    def check(label, ok):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            fails.append(label)

    eq = lambda **k: dict({"is_etf": False, "lastPrice": 100.0}, **k)
    c = classify
    check("ZERO: eps 0.0 with P/E -243 (SPCX 2026-11-02)",
          c(eq(eps=0.0, peRatio=-243.0, lastPrice=136.93))["code"] == "ZERO")
    check("NEGATIVE: eps 0.0 with no P/E is not ZERO", c(eq(eps=0.0, peRatio=None))["code"] == "NO P/E")
    check("NEGATIVE: eps 0.0 with P/E 0 is not ZERO", c(eq(eps=0.0, peRatio=0))["code"] == "NO P/E")
    check("MISSING: eps absent with a non-zero P/E", c(eq(eps=None, peRatio=20.0))["code"] == "MISSING")
    check("GAP: NVDA eps 4.90 vs implied 7.83",
          c(eq(eps=4.90, peRatio=100.0, lastPrice=783.0))["code"] == "GAP")
    check("SIGN: eps -3.70 vs a positive implied", c(eq(eps=-3.70, peRatio=80.0))["code"] == "SIGN")
    check("NEGATIVE: eps 7.46 vs implied 7.50 is ok",
          c(eq(eps=7.46, peRatio=40.0, lastPrice=300.0))["code"] == "ok")
    check("NEGATIVE: a 20% gap is under the 25% trigger",
          c(eq(eps=1.20, peRatio=100.0, lastPrice=100.0))["code"] == "ok")
    check("boundary: a 25% gap triggers", c(eq(eps=1.25, peRatio=100.0, lastPrice=100.0))["code"] == "GAP")
    check("ETF skipped", c({"is_etf": True, "eps": 0.0, "peRatio": 5.0}) is None)
    check("closePrice used when lastPrice is absent",
          c({"is_etf": False, "eps": 2.0, "peRatio": 50.0, "closePrice": 100.0})["code"] == "ok")
    check("flips: M H M H M = 4", flips([("d", v) for v in "MHMHM"]) == 4)
    check("NEGATIVE: H H H H = 0", flips([("d", v) for v in "HHHH"]) == 0)
    check("NEGATIVE: one rated session = 0", flips([("d", "M")]) == 0)

    with tempfile.TemporaryDirectory() as td:
        logs = os.path.join(td, "logs")
        os.makedirs(os.path.join(logs, "10 October Signals"))
        os.makedirs(os.path.join(logs, "Retired"))
        days = ["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03"]
        seqs = {"SPCX": "MMHMHM", "CBRS": "MMMMMM", "AAPL": "HHHHHH", "GM": "HH-HMH"}
        for i, d in enumerate(days):
            sub = os.path.join(logs, "10 October Signals") if d.startswith("2026-10-2") else logs
            with open(os.path.join(sub, f"signals_{d}.log"), "w", encoding="utf-8") as fh:
                for n, (tk, s) in enumerate(sorted(seqs.items())):
                    if s[i] != "-":
                        fh.write(_st_line(d, tk, {"H": "HIGH", "M": "MEDIUM"}[s[i]], n) + "\n")
                # a PM rerun appended later must not shadow the AM row
                fh.write(_st_line(d, "AAPL", "LOW", 59) + "\n")
        with open(os.path.join(logs, "Retired", "signals_2026-11-03.log"), "w", encoding="utf-8") as fh:
            fh.write(_st_line("2026-11-03", "AAPL", "LOW", 1) + "\n")
        with open(os.path.join(logs, "signals_2026-11-04.log"), "w", encoding="utf-8") as fh:
            fh.write(_st_line("2026-11-04", "AAPL", "LOW", 1) + "\n")     # after the run date
        pat = os.path.join(logs, "signals_*.log")
        hist, window, _ = dq_history("2026-11-03", 10, pat)
        check("window = 6 sessions, archive subfolder read, Retired/ and a later date excluded",
              window == days)
        check("SPCX M M H M H M = 4 flips, UNSTABLE", flips(hist["SPCX"]) == 4)
        check("NEGATIVE: CBRS constant MEDIUM = 0 flips", flips(hist["CBRS"]) == 0)
        check("NEGATIVE: AAPL's appended LOW (PM rerun) never read", flips(hist["AAPL"]) == 0)
        check("a missing session is skipped, not a flip: GM H H . H M H = 2",
              flips(hist["GM"]) == 2 and len(hist["GM"]) == 5)
        hist3, w3, _ = dq_history("2026-11-03", 3, pat)
        check("--sessions 3 reads only the last three", w3 == days[-3:] and flips(hist3["SPCX"]) == 2)

        # quote source: v2 inputs win; a v1-only file falls back to quote_dump; neither = none
        qd = os.path.join(td, "quote_dump.json")
        with open(qd, "w", encoding="utf-8") as fh:
            json.dump({"captured_local": "2026-11-02T15:50:57-06:00", "quotes": {
                "SPCX": eq(ticker="SPCX", eps=0.0, peRatio=-243.0),
                "SPY": {"ticker": "SPY", "is_etf": True}}}, fh)
        inp = os.path.join(logs, "inputs_2026-11-03.jsonl")
        with open(inp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"ticker": "SPCX", "last_price": 1.0}) + "\n")   # version 1
        q, src, prim = load_quotes("2026-11-03", logs, qd)
        check("v1-only inputs -> FALLBACK quote_dump, labelled as another date's capture",
              not prim and src.startswith("FALLBACK") and "NOT 2026-11-03" in src and "SPCX" in q)
        with open(inp, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ticker": "SPCX", "capture_version": 2,
                                 "quote": eq(ticker="SPCX", eps=0.0, peRatio=-245.0)}) + "\n")
            fh.write(json.dumps({"ticker": "SPCX", "capture_version": 2,
                                 "quote": eq(ticker="SPCX", eps=9.9, peRatio=10.0)}) + "\n")
        q, src, prim = load_quotes("2026-11-03", logs, qd)
        check("v2 inputs -> primary source; first record per ticker wins",
              prim and q["SPCX"]["peRatio"] == -245.0)
        q, src, prim = load_quotes("2026-11-05", logs, os.path.join(td, "nope.json"))
        check("NEGATIVE: no inputs and no quote_dump -> NO QUOTE SOURCE", not q and src.startswith("NO QUOTE"))

        md = os.path.join(td, "out.md")
        rc, text = run("2026-11-03", 10, md, logs, qd, pat, quiet=True)
        check("run: exit 0 with findings present (reports, never gates)", rc == 0)
        check("report names SPCX as ZERO and as UNSTABLE (4 flips)",
              "| ZERO | 1 | SPCX |" in text and "SPCX (UNSTABLE) | 4 |" in text)
        rc2, _ = run("2026-11-03", 10, None, os.path.join(td, "x"), os.path.join(td, "nope.json"),
                     os.path.join(td, "x", "signals_*.log"), quiet=True)
        check("NEGATIVE: nothing to read -> exit 2", rc2 == 2)
        try:
            con = console(*feed_findings(q or {"SPCX": eq(eps=0.0, peRatio=-1.0)}), "s", hist, window, True)
            con.encode("ascii")
            check("console output is ASCII (safe under cp1252 when redirected)", True)
        except UnicodeEncodeError:
            check("console output is ASCII (safe under cp1252 when redirected)", False)

    print()
    if fails:
        print(f"feed_consistency selftest: {len(fails)} FAILED")
        return 1
    print("feed_consistency selftest: all checks passed")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Feed EPS consistency + DQ flips. REPORTS ONLY.")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--sessions", type=int, default=DEFAULT_SESSIONS)
    ap.add_argument("--md", default=None, help="default feed_consistency_<date>.md")
    ap.add_argument("--inputs-dir", default="logs")
    ap.add_argument("--quote-dump", default="quote_dump.json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        dt.date.fromisoformat(a.date)
    except ValueError:
        print(f"  feed_consistency: bad --date {a.date!r}")
        return 2
    try:
        rc, _ = run(a.date, a.sessions, a.md or f"feed_consistency_{a.date}.md",
                    a.inputs_dir, a.quote_dump)
        return rc
    except Exception as e:                      # noqa: BLE001 - a report must never crash a scan
        print(f"  feed_consistency could not run: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
