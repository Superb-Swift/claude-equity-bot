#!/usr/bin/env python3
"""
e4_exit_read.py - the Phase 3-C ONE-TIME exit reads of E4-2 and E4-3.

WHAT IT READS (pre-registration v1.3; rulings DP-3C-ay, -bb, -bl, -bn, DP-3C-t)
    E4-2  filing-adjacent accuracy, the primary endpoint. HOLD rows only, in the
          13 ADJACENT-eligible names (T-A minus CORN), admitted EDGAR-live
          cohorts, ADJACENT = an 8-K or Form 4 within K = 5 sessions, DEGRADED
          rows (fin=degraded) excluded under DP-3C-t (b). Rows whose +5d
          session is on or before rulings.EXIT_CUT["e42_resolved_through"].
          The population is e4_counter's, row for row (checked at run time).
          Breach = column N's own rule, evaluated as column N evaluates it:
          K = (H - G) / G in floating point, "right" iff ABS(K) < 0.03
          (repair_outcome_close.band_flag, the project's Python twin of N).
          Rows within 1e-9 of the band are counted in the write-up.
          s3.2 PRIMARY: per ticker with >= 3 resolved rows in BOTH arms,
              d_ticker = breach(ADJACENT) - breach(COVERED-QUIET);
              pooled d = UNWEIGHTED mean of d_ticker (DP-3C-bn a). Rates and d
              are EXACT fractions of row counts, so the +/-5.0pt bar is never
              decided by float error; each row's verdict is column N's.
              Accuracy-equivalent dacc = -d. Negative d = ADJACENT scores better.
          DISPOSITION (DP-3C-bn b, c), on the primary alone:
              POSITIVE  dacc >= +5.0 pt and the sign survives BOTH robustness
                        conditions (leave-one-cohort-out; drop the largest ticker)
              NEGATIVE  dacc <= -5.0 pt and both hold
              INSUFFICIENT otherwise; INSUFFICIENT TEST CONDITIONS if fewer than
              150 resolved ADJACENT rows or fewer than 7 of 13 primary names.
          s3.3 FALLBACK (non-dispositive, DP-3C-bn h) and NVDA->HIGH sensitivity.
          s3.4 REPORTING set, the raw gap as a DESCRIPTIVE CONTROL EXPECTED
              NEGATIVE, primary/fallback counts and rows, three denominators,
              re-tier MEMBERSHIP, fin-staleness count, SHAKEDOWN / PENDING /
              DEGRADED counts.
    E4-3  8-K event window, descriptive. Each (ticker, filing date) on a T-A name
          filed EXIT_CUT["e43_filed_from"]..["e43_filed_through"], OBSERVABLE when
          admitted, non-DEGRADED rows with confidence_raw exist on the filing
          date and the next session (e4_counter's definition). RAW channel only.
          VERDICT-descriptive at >= 20 observable events, else INSUFFICIENT.

BLIND BY DEFAULT
    Without --read: populations at the cut (counts only) and gates 0, 1 and 5.
    No return, breach, confidence value or rate is computed.

ONE READ, ON CODE THAT CANNOT CHANGE (exit_read_guard)
    --read computes only when gates 0-5 all pass, then records E4-2@exit and
    E4-3@exit in ONE atomic, verified write. Nothing is shown until that write
    is verified; the write-up is written after it, from the recorded text. A
    later run prints the record (and restores a missing write-up from it); it
    never recomputes.

USAGE  (from the repo folder)
    python e4_exit_read.py              blind preview
    python e4_exit_read.py --read       the one-time read, if every gate passes
    python e4_exit_read.py --selftest   synthetic data only

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime as dt
import os
import re
import statistics
import sys
import tempfile
from collections import defaultdict
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import e4_counter as ec          # noqa: E402  one definition of every population
import trading_calendar as cal   # noqa: E402

# --------------------------------------------------------------------------- #
# Definitions (each names its source)
# --------------------------------------------------------------------------- #
BAND = 0.03                       # column N: HOLD right iff ABS(K) < 0.03 (float, as N)
NEAR_BAND = 1e-9                  # rows this close to the band are counted in the write-up
BAR = Fr(5, 100)                  # pre-reg s3.1: 5 points
MIN_PER_ARM = ec.E42_MIN_PER_ARM  # pre-reg s3.2 (3)
N_REQUIRED = ec.E42_N             # pre-reg s3.1 (150)
ADEQUATE_QUALIFIERS = 7           # DP-3C-bn f
E43_N = ec.E43_N                  # 20
INSTR_E42, INSTR_E43 = "E4-2@exit", "E4-3@exit"

# E4-2 volatility tiers, FROZEN 2026-08-10 (E4_2_Volatility_Tier_Table_FROZEN_2026-08-10.md).
FROZEN_TIERS = {
    "JPM": "LOW", "GLD": "LOW", "CORN": "LOW", "RTX": "LOW", "WMT": "LOW",
    "GM": "MID", "PM": "MID", "FTI": "MID", "PWR": "MID", "NVDA": "MID",
    "DOW": "HIGH", "NKE": "HIGH", "AAPL": "HIGH", "MSFT": "HIGH", "SND": "HIGH",
}
TIERS = ("LOW", "MID", "HIGH")
COVERED = tuple(FROZEN_TIERS)
WATCHLIST_DENOMINATOR = 24

# Every 8-K item code by (ticker, filing date), DP-3C-bn j. Built 2026-11-06
# from the 8-K documents in edgar_cache first written on the run each event was
# first seen (registrant, date of report and items read from each document).
ITEMS_8K = {
    ("MSFT", dt.date(2026, 9, 2)): (("0001193125-26-380280", "7.01, 9.01"),),
    ("NVDA", dt.date(2026, 9, 3)): (("0001045810-26-000078", "8.01, 9.01"),),
    ("SND", dt.date(2026, 9, 3)): (("0001529628-26-000104", "1.01, 2.03, 9.01"),),
    ("PM", dt.date(2026, 9, 8)): (("0001628280-26-060806", "7.01, 9.01"),
                                  ("0001628280-26-060822", "7.01, 9.01")),
    ("NKE", dt.date(2026, 9, 10)): (("0000320187-26-000143", "5.02, 5.07, 9.01"),),
    ("PWR", dt.date(2026, 9, 15)): (("0001193125-26-391989", "5.02, 7.01, 9.01"),),
    ("RTX", dt.date(2026, 9, 15)): (("0001140361-26-036662", "5.02, 9.01"),),
    ("NKE", dt.date(2026, 9, 16)): (("0000320187-26-000170", "5.02, 7.01, 9.01"),),
    ("PM", dt.date(2026, 9, 18)): (("0001628280-26-062621", "7.01, 9.01"),),
    ("CORN", dt.date(2026, 9, 24)): (("0001437749-26-031115", "8.01, 9.01"),),
    ("NKE", dt.date(2026, 10, 1)): (("0000320187-26-000184", "2.02, 2.05, 9.01"),),
    ("JPM", dt.date(2026, 10, 13)): (("0001628280-26-065582", "2.02, 9.01"),
                                     ("0001628280-26-065616", "7.01, 9.01")),
    ("GM", dt.date(2026, 10, 20)): (("0001467858-26-000056", "2.02"),),
    ("JPM", dt.date(2026, 10, 20)): (("0001193125-26-426704", "8.01, 9.01"),),
    ("RTX", dt.date(2026, 10, 20)): (("0000101829-26-000030", "2.02, 9.01"),),
    ("PM", dt.date(2026, 10, 21)): (("0001628280-26-066596", "2.02, 9.01"),),
    ("DOW", dt.date(2026, 10, 22)): (("0001751788-26-000155", "2.02, 9.01"),),
    ("WMT", dt.date(2026, 10, 23)): (("0001193125-26-429539", "8.01, 9.01"),),
    ("GM", dt.date(2026, 10, 27)): (("0001193125-26-432602", "3.01, 5.03, 7.01, 9.01"),),
    ("MSFT", dt.date(2026, 10, 28)): (("0001193125-26-436122", "2.02, 9.01"),
                                      ("0001193125-26-436149", "8.01, 9.01")),
    ("FTI", dt.date(2026, 10, 29)): (("0001681459-26-000050", "2.02, 9.01"),),
    ("GM", dt.date(2026, 10, 29)): (("0001193125-26-437768", "5.02"),),
    ("PWR", dt.date(2026, 10, 29)): (("0001193125-26-436949", "2.02, 7.01, 9.01"),),
    ("AAPL", dt.date(2026, 11, 2)): (("0000320193-26-000024", "2.02, 9.01"),),
    ("MSFT", dt.date(2026, 11, 5)): (("0001193125-26-447173", "8.01, 9.01"),
                                     ("0001193125-26-448357", "5.02")),
    ("SND", dt.date(2026, 11, 5)): (("0001529628-26-000107", "7.01, 8.01, 9.01"),),
}

REQUIRED_FILES = ("e4_exit_read.py", "e4_counter.py", "exit_read_guard.py", "rulings.py",
                  "trading_calendar.py", "signal_logs.py", "outcome_sanity.py",
                  "trail_basis_audit.py", "log_tracker_crosscheck.py", "repair_outcome_close.py",
                  "repair_return_formulas.py")

_RAWVAL = re.compile(r'"confidence_raw": (-?\d+(?:\.\d+)?)')
_PERIODIC = re.compile(r"periodic=[^;\]@]*@(\d{4}-\d{2}-\d{2})")
_FIN = re.compile(r"fin=\d+@(\d{4}-\d{2}-\d{2})")


def cut():
    import rulings
    return rulings.EXIT_CUT


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def log_paths(pattern):
    import signal_logs
    paths, _ = signal_logs.discover(pattern)
    return [p for p in paths if ec._LOGDATE.search(os.path.basename(p))]


def load_log_extras(paths):
    """{(date, ticker): dict(raw, periodic, fin, pv)} from the same lines e4_counter reads."""
    out = {}
    for p in paths:
        d = dt.date.fromisoformat(ec._LOGDATE.search(os.path.basename(p)).group(1))
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                t = ec._TK.search(line)
                if not t:
                    continue
                rv = _RAWVAL.search(line)
                e = ec._ETAG.search(line)
                tag = e.group(1) if e else ""
                pm, fm, pv = _PERIODIC.search(tag), _FIN.search(tag), ec._PV.search(line)
                out[(d, t.group(1))] = dict(
                    raw=Fr(rv.group(1)) if rv else None,
                    periodic=dt.date.fromisoformat(pm.group(1)) if pm else None,
                    fin=dt.date.fromisoformat(fm.group(1)) if fm else None,
                    pv=pv.group(1) if pv else "")
    return out


def _num(v):
    """The cell's number exactly as stored (int or float), or None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v


def k_of(p0, p5):
    """Column K as the canonical formula computes it: (H - G) / G, in floats."""
    return (float(p5) - p0) / p0


def load_master(path):
    """({(date, ticker): dict(p0, p5)}, newest cohort). Price columns G and H
    only. The formula cache is never read (DP-3C-bn g)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    ws = wb["Signals"]
    out, newest = {}, None
    for r in ws.iter_rows(min_row=5, max_col=8, values_only=True):
        if not r or not isinstance(r[0], dt.datetime) or not r[1]:
            continue
        d = r[0].date()
        out[(d, str(r[1]).strip())] = dict(p0=_num(r[6]), p5=_num(r[7]), p5_raw=r[7])
        newest = d if newest is None or d > newest else newest
    wb.close()
    return out, newest


# --------------------------------------------------------------------------- #
# E4-2
# --------------------------------------------------------------------------- #
def e42_population(rows, master, through, resolved, outcomes=True):
    """Resolved, non-DEGRADED HOLD rows tagged ADJ / QUIET. `resolved` is the
    counter's own map (ec.load_resolved). Raises if the row set differs from
    e4_counter.count_e42 at the same cut, or a resolved row has no exact prices."""
    pop = []
    for r in rows:
        if not (ec.admitted(r) and r["d"] <= through and r["sig"] == "HOLD"
                and r["tk"] in ec.E42_ELIGIBLE and not r.get("degraded")):
            continue
        if not (resolved.get((r["d"], r["tk"]), False) and cal.shift_sessions(r["d"], 5) <= through):
            continue
        m = master.get((r["d"], r["tk"]))
        if not m or m["p0"] is None or m["p0"] <= 0 or m["p5"] is None:
            raise ValueError(f"{r['tk']} {r['d']}: resolved, but Price at Signal / Price +5d is not "
                             f"a number (p0={m and m['p0']}, p5={m and m['p5_raw']!r})")
        x = dict(d=r["d"], tk=r["tk"], arm="ADJ" if ec.is_adjacent(r) else "QUIET",
                 res=cal.shift_sessions(r["d"], 5))
        if outcomes:
            import repair_outcome_close as roc
            x["ret5"] = k_of(m["p0"], m["p5"])
            x["breach"] = roc.band_flag("HOLD", x["ret5"]) == "NO"
            x["near"] = abs(abs(x["ret5"]) - BAND) < NEAR_BAND
        pop.append(x)
    c = ec.count_e42(rows, resolved, through)
    got = (sum(1 for x in pop if x["arm"] == "ADJ"), sum(1 for x in pop if x["arm"] == "QUIET"))
    if got != (c["adj_resolved"], c["quiet_resolved"]):
        raise ValueError(f"population mismatch with e4_counter: read {got}, counter "
                         f"{(c['adj_resolved'], c['quiet_resolved'])}")
    return pop, c


def per_ticker(pop):
    t = defaultdict(lambda: {"ADJ": [], "QUIET": []})
    for x in pop:
        t[x["tk"]][x["arm"]].append(x)
    out = {}
    for tk in ec.E42_ELIGIBLE:
        a, q = t[tk]["ADJ"], t[tk]["QUIET"]
        ba = Fr(sum(x["breach"] for x in a), len(a)) if a else None
        bq = Fr(sum(x["breach"] for x in q), len(q)) if q else None
        qual = len(a) >= MIN_PER_ARM and len(q) >= MIN_PER_ARM
        out[tk] = dict(nA=len(a), nQ=len(q), bA=ba, bQ=bq, qual=qual, d=(ba - bq) if qual else None)
    return out


def _mean(xs):
    xs = list(xs)
    return sum(xs, Fr(0)) / len(xs) if xs else None


def pooled_d(pop):
    tab = per_ticker(pop)
    qs = sorted(tk for tk, v in tab.items() if v["qual"])
    return _mean(tab[tk]["d"] for tk in qs), qs, tab


def _sign(x):
    return 0 if x is None or x == 0 else (1 if x > 0 else -1)


def loco(pop):
    out = []
    for c in sorted({x["d"] for x in pop}):
        d, qs, _ = pooled_d([x for x in pop if x["d"] != c])
        out.append((c, d, len(qs)))
    return out


def largest_qualifier(tab, qs):
    if not qs:
        return None
    return sorted(qs, key=lambda tk: (-tab[tk]["nA"], -(tab[tk]["nA"] + tab[tk]["nQ"]), tk))[0]


def drop_largest(tab, qs):
    big = largest_qualifier(tab, qs)
    if big is None:
        return None, None
    return big, _mean(tab[tk]["d"] for tk in qs if tk != big)


def disposition(d, n_adj, n_qual, loco_rows, dropped_d):
    if n_adj < N_REQUIRED or n_qual < ADEQUATE_QUALIFIERS:
        return "INSUFFICIENT TEST CONDITIONS", [
            f"resolved ADJACENT {n_adj} (need {N_REQUIRED}); primary qualifiers {n_qual} "
            f"(need {ADEQUATE_QUALIFIERS} of 13)"]
    s = _sign(d)
    if s == 0:
        return "INSUFFICIENT", ["pooled d is exactly 0 or undefined: no sign to survive"]
    held = sum(_sign(x[1]) == s for x in loco_rows)
    r1 = held == len(loco_rows)
    r2 = _sign(dropped_d) == s
    why = [f"dacc {_pt(-d)} against the +/-5.0 pt bar (exact: {-d * 100} pt)",
           f"leave-one-cohort-out: sign held in {held} of {len(loco_rows)} folds",
           f"drop the largest ticker: sign {'held' if r2 else 'did NOT hold'}"]
    if abs(d) >= BAR and r1 and r2:
        return ("POSITIVE" if d < 0 else "NEGATIVE"), why
    return "INSUFFICIENT", why


def fallback(pop, qs, tiers):
    fb = [tk for tk in ec.E42_ELIGIBLE if tk not in qs]
    per = {}
    for t in TIERS:
        a = [x for x in pop if x["arm"] == "ADJ" and x["tk"] in fb and tiers.get(x["tk"]) == t]
        q = [x for x in pop if x["arm"] == "QUIET" and tiers.get(x["tk"]) == t]
        ok = len(a) >= MIN_PER_ARM and len(q) >= MIN_PER_ARM
        ba = Fr(sum(x["breach"] for x in a), len(a)) if a else None
        bq = Fr(sum(x["breach"] for x in q), len(q)) if q else None
        per[t] = dict(fb=[tk for tk in fb if tiers.get(tk) == t], nA=len(a), nQ=len(q),
                      bA=ba, bQ=bq, d=(ba - bq) if ok else None)
    return fb, per, _mean(v["d"] for v in per.values() if v["d"] is not None)


def stratum(xs):
    if not xs:
        return dict(n=0)
    r = [x["ret5"] for x in xs]
    br = sum(x["breach"] for x in xs)
    return dict(n=len(xs), breach=Fr(br, len(xs)), acc=1 - Fr(br, len(xs)),
                mean=statistics.fmean(r), sd=statistics.pstdev(r),
                up=sum(1 for x in xs if x["breach"] and x["ret5"] > 0),
                down=sum(1 for x in xs if x["breach"] and x["ret5"] < 0))


def tier_drift(master, through):
    med = {}
    for tk in COVERED:
        v = [abs(k_of(m["p0"], m["p5"])) for (d, t), m in master.items()
             if t == tk and m["p0"] and m["p5"] is not None and cal.shift_sessions(d, 5) <= through]
        med[tk] = statistics.median(v) if v else None
    ranked = sorted((tk for tk in COVERED if med[tk] is not None), key=lambda tk: (med[tk], tk))
    now = {tk: TIERS[min(i // 5, 2)] for i, tk in enumerate(ranked)}
    moved = [(tk, FROZEN_TIERS[tk], now[tk], med[tk]) for tk in COVERED
             if tk in now and now[tk] != FROZEN_TIERS[tk]]
    return med, now, moved


def fin_stale(extras, cohort):
    out, seen = [], 0
    for tk in COVERED:
        e = extras.get((cohort, tk))
        if not e or not e["periodic"] or not e["fin"]:
            continue
        seen += 1
        lag = (e["periodic"] - e["fin"]).days
        if lag > 60:
            out.append((tk, lag))
    return out, seen


# --------------------------------------------------------------------------- #
# E4-3
# --------------------------------------------------------------------------- #
def e43_events(rows, c):
    as_of = cal.next_session(c["e43_filed_through"])
    res = ec.count_e43(rows, as_of)
    ev = [(tk, f, s) for tk, f, s in res["detail"] if c["e43_filed_from"] <= f <= c["e43_filed_through"]]
    return ev, res


def e43_trace(events, extras):
    out = []
    for tk, f, s in events:
        if not s.startswith("OBSERVABLE"):
            continue
        n = cal.next_session(f)
        e0, e1 = extras.get((f, tk)) or {}, extras.get((n, tk)) or {}
        r0, r1 = e0.get("raw"), e1.get("raw")
        items = ITEMS_8K.get((tk, f))
        out.append(dict(tk=tk, f=f, nxt=n, raw0=r0, raw1=r1,
                        delta=(r1 - r0) if r0 is not None and r1 is not None else None,
                        d2=("S1D2" in e0.get("pv", "")) and ("S1D2" in e1.get("pv", "")),
                        items="; ".join(f"{i} ({a})" for a, i in items) if items else "not resolved"))
    return out


def e43_verdict(n_obs):
    return "VERDICT-descriptive" if n_obs >= E43_N else "INSUFFICIENT"


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _p(x, nd=1):
    return "n/a" if x is None else f"{100 * float(x):.{nd}f}%"


def _pt(x, nd=2):
    return "n/a" if x is None else f"{100 * float(x):+.{nd}f} pt"


def _share(a, n):
    return "n/a" if not n else f"{a / n:.1%}"


def render_preview(c, counts, n_events, n_obs, lines):
    return "\n".join([
        "=" * 78, "E4 EXIT READ - BLIND PREVIEW (counts only; nothing is read without --read)", "=" * 78,
        f"  cut (rulings.EXIT_CUT, DP-3C-bl): review {c['review_date']}; E4-2 +5d <= "
        f"{c['e42_resolved_through']}; E4-3 filed {c['e43_filed_from']}..{c['e43_filed_through']}",
        f"  E4-2 resolved ADJACENT {counts['adj_resolved']} of {N_REQUIRED}; COVERED-QUIET "
        f"{counts['quiet_resolved']}; primary qualifiers {len(counts['qualifiers'])} of 13 "
        f"[{', '.join(counts['qualifiers'])}]; DEGRADED rows excluded {counts.get('degraded', 0)}",
        f"  E4-3 events in the cut {n_events}; observable {n_obs}", "", "  GATES:"] + lines + [
        "", "  BLIND: no breach, return, confidence value or rate was computed.",
        "  Advisory-only - no orders - not financial advice."])


def render_read(c, R):
    L = []
    a = L.append
    d = R["d"]
    fb, per, fbd = R["fallback"]
    disagree = _sign(fbd) != 0 and _sign(d) != 0 and _sign(fbd) != _sign(d)
    a(f"# E4 exit reads - Phase 3-C (taken {R['taken_at']})")
    a("")
    a(f"*Cut (rulings.EXIT_CUT, DP-3C-bl): exit-review date {c['review_date']}; E4-2 rows whose +5d session is "
      f"on or before {c['e42_resolved_through']}; E4-3 8-Ks filed {c['e43_filed_from']}..{c['e43_filed_through']}. "
      f"Mechanics: DP-3C-bn. Read once, recorded as {INSTR_E42} and {INSTR_E43}. "
      "Advisory-only - no orders - not financial advice.*")
    a("")
    a("## E4-2 - filing-adjacent accuracy (primary)")
    a("")
    a(f"**DISPOSITION: {R['disp']}**"
      + (" - **the s3.3 fallback disagrees in sign with the primary**" if disagree else ""))
    a("")
    for w in R["why"]:
        a(f"- {w}")
    a(f"- pooled d (unweighted mean of d_ticker over {len(R['qs'])} primary names) = {_pt(d)} on the breach "
      f"rate; accuracy-equivalent {_pt(None if d is None else -d)}. Negative d = ADJACENT scores better.")
    a(f"- s3.3 fallback (non-dispositive), names {', '.join(fb) or 'none'}: tier-pooled d = {_pt(fbd)}.")
    nfa = sum(R["tab"][tk]["nA"] for tk in fb)
    a(f"- rows: {R['n_adj']} resolved ADJACENT, of which {R['n_adj'] - nfa} on the primary read and {nfa} "
      f"({_share(nfa, R['n_adj'])}) on the fallback; {R['n_quiet']} COVERED-QUIET; "
      f"{R['counts'].get('degraded', 0)} DEGRADED rows excluded (DP-3C-t (b)); "
      f"{sum(1 for x in R['pop'] if x.get('near'))} row(s) within 1e-9 of the 3% band, each decided by "
      "column N's own float rule.")
    a("")
    a("### Per ticker (s3.2)")
    a("")
    a("| Ticker | Tier | ADJ n | QUIET n | ADJ breach | QUIET breach | d_ticker | Read | ADJ share |")
    a("|---|---|---|---|---|---|---|---|---|")
    for tk in ec.E42_ELIGIBLE:
        v = R["tab"][tk]
        a(f"| {tk} | {FROZEN_TIERS[tk]} | {v['nA']} | {v['nQ']} | {_p(v['bA'])} | {_p(v['bQ'])} | "
          f"{_pt(v['d'], 1)} | {'primary' if v['qual'] else 'fallback'} | {_share(v['nA'], R['n_adj'])} |")
    w = R["tab"].get("WMT", {})
    a("")
    a(f"WMT's share of resolved ADJACENT rows (pre-reg s2): {w.get('nA', 0)}/{R['n_adj']} = "
      f"{_share(w.get('nA', 0), R['n_adj'])}.")
    a("")
    a("### Robustness")
    a("")
    lv = [x[1] for x in R["loco"] if x[1] is not None]
    a(f"- leave-one-cohort-out: {len(R['loco'])} folds; pooled d ranged {_pt(min(lv) if lv else None)} to "
      f"{_pt(max(lv) if lv else None)}; qualifiers per fold {min((x[2] for x in R['loco']), default=0)}.."
      f"{max((x[2] for x in R['loco']), default=0)}.")
    flips = [x for x in R["loco"] if _sign(x[1]) != _sign(d)]
    a(f"- folds where the sign did not hold: {', '.join(str(x[0]) for x in flips) or 'none'}.")
    a(f"- drop the largest ticker ({R['dropped'][0]}): pooled d = {_pt(R['dropped'][1])}.")
    a("")
    a("### Reporting set (s3.4)")
    a("")
    a("| Stratum | n | breach | accuracy | mean signed ret5 | sd (pop) | UP | DOWN |")
    a("|---|---|---|---|---|---|---|---|")
    for name, s in R["strata"]:
        if s["n"]:
            a(f"| {name} | {s['n']} | {_p(s['breach'])} | {_p(s['acc'])} | {_p(s['mean'], 2)} | "
              f"{_p(s['sd'], 2)} | {s['up']} | {s['down']} |")
        else:
            a(f"| {name} | 0 | | | | | | |")
    a("")
    a(f"**Raw pooled gap, ADJACENT minus COVERED-QUIET accuracy: {_pt(R['raw_gap'])}. DESCRIPTIVE CONTROL, "
      "EXPECTED NEGATIVE on volatility grounds alone (pre-reg s3.4 item 5). Not a treatment effect.**")
    a("")
    a("### Fallback detail and tier sensitivity (s3.3)")
    a("")
    a("| Tier | fallback names | ADJ n | QUIET n | ADJ breach | QUIET breach | d_tier |")
    a("|---|---|---|---|---|---|---|")
    for t in TIERS:
        v = per[t]
        a(f"| {t} | {', '.join(v['fb']) or '-'} | {v['nA']} | {v['nQ']} | {_p(v['bA'])} | {_p(v['bQ'])} | "
          f"{'not pooled (< 3 per arm)' if v['d'] is None else _pt(v['d'], 1)} |")
    a("")
    a(f"NVDA reclassified MID -> HIGH (the near-tie flagged at freeze): tier-pooled fallback d = "
      f"{_pt(R['fallback_nvda_high'][2])}.")
    a("LOW tier: GLD and CORN are frozen into LOW but cannot be ADJACENT (ruled 2026-08-20); the LOW "
      "comparison draws on JPM, RTX and WMT only.")
    med, now, moved = R["drift"]
    a("")
    a("Re-tier membership at the cut (frozen rule re-applied; table NOT re-cut): "
      + (", ".join(f"{tk} {f} -> {n} ({100 * float(m):.3f}%)" for tk, f, n, m in moved) or "none")
      + f" - {len(moved)} of 15."
      + (f" No resolved rows: {', '.join(tk for tk in COVERED if med[tk] is None)}."
         if any(med[tk] is None for tk in COVERED) else ""))
    a("")
    a("### Denominators and admissibility")
    a("")
    named = sorted({x['tk'] for x in R['pop']})
    a(f"- covered (pre-registered) 15/{WATCHLIST_DENOMINATOR}; ADJACENT-eligible 13/{WATCHLIST_DENOMINATOR}; "
      f"names with resolved rows in this read {len(named)}/13.")
    st, seen = R["stale"]
    a(f"- covered names whose fin period trails their periodic date by > 60 days on {R['stale_cohort']} "
      f"(the read's last signal cohort): "
      + (f"{len(st)} of {seen} ({', '.join(f'{tk} {lag}d' for tk, lag in st) or 'none'})" if seen
         else "NOT COMPUTED - no periodic/fin dates parsed on that cohort") + ".")
    a(f"- SHAKEDOWN cohorts (-E1 stamp before the clock): {R['shakedown']}, outside the read by construction. "
      "PENDING VERIFICATION: 0 (the integrity gate passed). "
      f"DEGRADED rows excluded: {R['counts'].get('degraded', 0)}.")
    a("")
    a("## E4-3 - 8-K event window (descriptive)")
    a("")
    tr = R["e43"]
    a(f"**{R['e43_verdict']}**: {len(tr)} observable of {len(R['e43_events'])} events in the cut "
      f"(bar {E43_N}). Raw channel only. D2 on both rows: {sum(t['d2'] for t in tr)} of {len(tr)}. "
      "No disposition beyond VERDICT-descriptive.")
    a("")
    a("| Ticker | Filed | Next session | raw (filed) | raw (next) | change | 8-K items (accession) |")
    a("|---|---|---|---|---|---|---|")
    for t in tr:
        f0 = "n/a" if t["raw0"] is None else f"{float(t['raw0']):g}"
        f1 = "n/a" if t["raw1"] is None else f"{float(t['raw1']):g}"
        dd = "n/a" if t["delta"] is None else f"{float(t['delta']):+g}"
        a(f"| {t['tk']} | {t['f']} | {t['nxt']} | {f0} | {f1} | {dd} | {t['items']} |")
    ups = sum(1 for t in tr if t["delta"] is not None and t["delta"] > 0)
    dns = sum(1 for t in tr if t["delta"] is not None and t["delta"] < 0)
    flat = sum(1 for t in tr if t["delta"] is not None and t["delta"] == 0)
    na = sum(1 for t in tr if t["delta"] is None)
    a("")
    a(f"Raw confidence on the session after the 8-K: up {ups}, flat {flat}, down {dns}, not parsed {na}.")
    for tk, f, s in R["e43_events"]:
        if not s.startswith("OBSERVABLE"):
            a(f"- {tk} {f}: {s}")
    u = R["e43_unseen"]
    a(f"- POSSIBLE UNSEEN 8-Ks (e4_counter): {u['n']} flagged, {u['open']} unexplained; never added to the count.")
    a("")
    a("## Provenance")
    a("")
    a(f"- master snapshot sha256 {R['master_sha']} (copied from {R['master_src']})")
    a(f"- integrity gate: {R.get('integrity', 'n/a')}")
    a(f"- {len(R['log_hashes'])} logs hashed at the start and verified unchanged at the end")
    for f, b in sorted(R["blobs"].items()):
        a(f"- `{f}` git blob {b}")
    a(f"- git HEAD {R['git_head']}")
    a("")
    a("*Advisory-only - no orders - not financial advice.*")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# The read
# --------------------------------------------------------------------------- #
def compute(rows, master, resolved, extras, c):
    pop, counts = e42_population(rows, master, c["e42_resolved_through"], resolved)
    d, qs, tab = pooled_d(pop)
    lo = loco(pop)
    dropped = drop_largest(tab, qs)
    n_adj = sum(1 for x in pop if x["arm"] == "ADJ")
    disp, why = disposition(d, n_adj, len(qs), lo, dropped[1])
    adj = [x for x in pop if x["arm"] == "ADJ"]
    qui = [x for x in pop if x["arm"] == "QUIET"]
    strata = [("ADJACENT (all)", stratum(adj)), ("COVERED-QUIET (all)", stratum(qui))]
    for t in TIERS:
        strata.append((f"ADJACENT, {t}", stratum([x for x in adj if FROZEN_TIERS[x['tk']] == t])))
        strata.append((f"COVERED-QUIET, {t}", stratum([x for x in qui if FROZEN_TIERS[x['tk']] == t])))
    sa, sq = stratum(adj), stratum(qui)
    ev, e43res = e43_events(rows, c)
    tr = e43_trace(ev, extras)
    last_cohort = max((x["d"] for x in pop), default=None)
    unseen_open = [(tk, day, k) for tk, day, k in e43res["unseen_at"] if (tk, day, k) not in ec.UNSEEN_EXPLAINED]
    return dict(
        pop=pop, counts=counts, d=d, qs=qs, tab=tab, loco=lo, dropped=dropped, n_adj=n_adj, n_quiet=len(qui),
        disp=disp, why=why, strata=strata,
        raw_gap=(sa["acc"] - sq["acc"]) if sa["n"] and sq["n"] else None,
        fallback=fallback(pop, qs, FROZEN_TIERS), fallback_nvda_high=fallback(pop, qs, dict(FROZEN_TIERS, NVDA="HIGH")),
        drift=tier_drift(master, c["e42_resolved_through"]),
        stale=fin_stale(extras, last_cohort) if last_cohort else ([], 0), stale_cohort=last_cohort,
        shakedown=len({r["d"] for r in rows if r["pv"].endswith("-E1") and r["d"] < ec.CLOCK_START}),
        e43_events=ev, e43=tr, e43_verdict=e43_verdict(len(tr)),
        e43_unseen=dict(n=e43res["unseen"], open=len(unseen_open)))


def observed_counts(counts, events):
    return dict(e42_adjacent=counts["adj_resolved"], e42_quiet=counts["quiet_resolved"],
                e42_qualifiers=len(counts["qualifiers"]), e42_degraded_excluded=counts.get("degraded", 0),
                e43_events=len(events), e43_observable=sum(1 for e in events if e[2].startswith("OBSERVABLE")))


def record_and_render(c, R, readings_path, md_path, exit_path=None):
    """Record both readings in one verified write, THEN write and return the
    write-up. Returns (ok, text or None, message): no text unless recorded."""
    import exit_read_guard as guard
    text = render_read(c, R)
    common = dict(cut={k: str(v) for k, v in c.items() if k != "expected"},
                  master_sha=R["master_sha"], log_hashes=R["log_hashes"], blobs=R["blobs"],
                  git_head=R["git_head"], md=md_path)
    entries = {
        INSTR_E42: (c["review_date"], R["disp"] == "POSITIVE", dict(
            common, disposition=R["disp"], dacc=None if R["d"] is None else str(-R["d"]),
            dacc_pts=None if R["d"] is None else round(-100 * float(R["d"]), 4),
            n_adjacent=R["n_adj"], n_quiet=R["n_quiet"], qualifiers=R["qs"],
            degraded_excluded=R["counts"].get("degraded", 0), fallback_names=R["fallback"][0],
            fallback_d=None if R["fallback"][2] is None else str(R["fallback"][2]),
            dropped=R["dropped"][0], dropped_d=None if R["dropped"][1] is None else str(R["dropped"][1]),
            loco_signs=[_sign(x[1]) for x in R["loco"]], text=text)),
        INSTR_E43: (c["review_date"], False, dict(
            common, verdict=R["e43_verdict"], n_events=len(R["e43_events"]), n_observable=len(R["e43"]),
            trace=[[t["tk"], str(t["f"]), None if t["raw0"] is None else float(t["raw0"]),
                    None if t["raw1"] is None else float(t["raw1"]),
                    None if t["delta"] is None else float(t["delta"]), t["items"]] for t in R["e43"]])),
    }
    if exit_path:
        ok, msg = guard.record_exit(entries, exit_path, readings_path)
    else:
        ok, msg = guard.record_once(entries, readings_path)
    if not ok:
        return False, None, msg
    try:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except OSError as exc:
        return True, text, f"{msg}; write-up NOT written ({exc}) - run again to restore it from the record"
    return True, text, msg


def print_recorded(prior, md_path):
    e2, e3 = prior[INSTR_E42][0], prior[INSTR_E43][0]
    print(f"E4 EXIT READS ARE ON THE RECORD (taken {e2['detail'].get('recorded_at')}); printed, never recomputed.")
    print(f"  {INSTR_E42}: {e2['detail'].get('disposition')}  dacc {e2['detail'].get('dacc_pts')} pt  "
          f"n {e2['detail'].get('n_adjacent')}")
    print(f"  {INSTR_E43}: {e3['detail'].get('verdict')}  observable {e3['detail'].get('n_observable')}")
    md = e2["detail"].get("md") or md_path
    if md and not os.path.exists(md) and e2["detail"].get("text"):
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(e2["detail"]["text"] + "\n")
        print(f"  write-up {md} was missing: restored from the record")
    else:
        print(f"  full write-up: {md}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Phase 3-C one-time exit reads of E4-2 and E4-3.")
    ap.add_argument("--tracker", default=os.path.join(HERE, "logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--logs", default=os.path.join(HERE, "logs", "signals_*.log"))
    ap.add_argument("--read", action="store_true", help="take the one-time read (gated)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if os.path.basename(a.tracker).lower() in {n.lower() for n in ec.REFUSED}:
        print("refused: read THE MASTER, not the generated report copy")
        return 2
    import rulings
    import exit_read_guard as guard
    c = cut()
    md_path = os.path.join(HERE, f"e4_exit_read_{c['review_date']}.md")
    readings_path, exit_path = rulings.READINGS_PATH, rulings.EXIT_READINGS_PATH
    tracker, logs_glob = os.path.abspath(a.tracker), os.path.abspath(a.logs)

    try:
        prior = guard.load_exit_records([INSTR_E42, INSTR_E43], [exit_path, readings_path])
    except (OSError, ValueError) as exc:
        print(f"STOP: a readings file is unreadable ({exc}). Nothing read.")
        return 2
    have2, have3 = bool(prior.get(INSTR_E42)), bool(prior.get(INSTR_E43))
    if have2 or have3:
        if have2 != have3:
            print(f"ANOMALY: only one of {INSTR_E42} / {INSTR_E43} is recorded. Nothing recomputed.")
            return 2
        print_recorded(prior, md_path)
        return 0

    import shutil
    work = tempfile.mkdtemp(prefix="e4_exit_read_")
    try:
        return _run(a, c, guard, tracker, logs_glob, readings_path, exit_path, md_path, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)        # the master copy never outlives the run


def _run(a, c, guard, tracker, logs_glob, readings_path, exit_path, md_path, work):
    try:
        paths = log_paths(logs_glob)
        snap = guard.snapshot(tracker, paths, work)
        rows, _ = ec.load_logs(logs_glob)
        master, newest = load_master(snap["master"])
        resolved = ec.load_resolved(snap["master"])
        pop, counts = e42_population(rows, master, c["e42_resolved_through"], resolved, outcomes=False)
        ev, _ = e43_events(rows, c)
    except Exception as exc:                                     # noqa: BLE001
        print(f"E4 EXIT READ COULD NOT RUN: {exc}")
        return 2
    got = observed_counts(counts, ev)
    log_dates = {dt.date.fromisoformat(ec._LOGDATE.search(os.path.basename(p)).group(1)) for p in paths}
    cohorts = {d for d, _ in master if d >= ec.CLOCK_START}
    missing = sorted(cohorts - log_dates)
    from collections import Counter
    dups = sorted(k for k, n in Counter((r["d"], r["tk"]) for r in rows).items() if n > 1)
    if dups:
        missing_txt = "duplicate log lines for " + ", ".join(f"{t} {d}" for d, t in dups[:5])
    else:
        missing_txt = None
    gates = [("0 run from the repo folder", *guard.gate_cwd()),
             ("1 read protection (DP-3C-bb)", *guard.gate_read_protection([x["res"] for x in pop], newest)),
             ("5 inputs as ruled", *guard.gate_inputs(
                 dict(c["expected"]), got, extra_ok=not missing and not dups,
                 extra_detail=(missing_txt if dups else
                               "logs cover every master cohort since the clock; one line per ticker per log"
                               if not missing else "no log for master cohort(s) " + ", ".join(map(str, missing)))))]
    if not a.read:
        print(render_preview(c, counts, len(ev), got["e43_observable"], guard.gate_lines(gates)))
        print("\n  (gates 2-4 run only with --read)")
        return 0
    newest_log = max(paths, key=lambda p: ec._LOGDATE.search(os.path.basename(p)).group(1))
    integ = guard.gate_integrity(snap["master"], logs_glob, newest_log)
    gates.insert(2, ("2 integrity (DP-3C-bm)", *integ))
    ok3, det3, blobs = guard.gate_git_strict(list(REQUIRED_FILES))
    gates.insert(3, ("3 committed code", ok3, det3))
    gates.insert(4, ("4 not already read", *guard.gate_not_recorded([INSTR_E42, INSTR_E43],
                                                                     [exit_path, readings_path])))
    print(render_preview(c, counts, len(ev), got["e43_observable"], guard.gate_lines(gates)))
    if not guard.all_ok(gates):
        print("\nREAD NOT TAKEN: a gate stopped it. Counts only; nothing recorded.")
        return 1

    extras = load_log_extras(paths)
    R = compute(rows, master, resolved, extras, c)
    okl, detl = guard.logs_unchanged(snap)
    if not okl:
        print(f"\nREAD NOT TAKEN: {detl}. Nothing recorded, nothing shown.")
        return 1
    R.update(taken_at=dt.datetime.now().isoformat(timespec="seconds"), master_sha=snap["master_sha"],
             master_src=snap["master_src"], log_hashes={os.path.basename(p): h for p, h in snap["logs"].items()},
             blobs=blobs, git_head=guard.git_head(), integrity=integ[1])
    ok, text, msg = record_and_render(c, R, readings_path, md_path, exit_path=exit_path)
    if not ok:
        print(f"\n*** RECORDING FAILED: {msg}. The read is NOT shown and NOT recorded. Fix the cause and run "
              "again; nothing was seen. ***")
        return 2
    print("\n" + text)
    print(f"\n{msg}. Write-up {md_path}. Later runs print the record and never recompute.")
    return 0


# --------------------------------------------------------------------------- #
# Selftest - SYNTHETIC DATA ONLY
# --------------------------------------------------------------------------- #
def selftest():
    import shutil
    import types
    import exit_read_guard as guard
    fails = []

    def check(name, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")
        if not ok:
            fails.append(name)

    D = dt.date
    S = cal.shift_sessions

    def mk(tks, n_cohorts, start=D(2026, 9, 1), adj_breach=None, quiet_breach=None, override=None, degraded=()):
        rows, master, days, d = [], {}, [], start
        while len(days) < n_cohorts:
            if cal.is_trading_day(d) and d not in cal.BOT_ABSENT:
                days.append(d)
            d += dt.timedelta(days=1)
        for tk in tks:
            cnt = {"ADJ": 0, "QUIET": 0}
            for i, day in enumerate(days):
                arm = "ADJ" if i % 2 == 0 else "QUIET"
                rate = (adj_breach or {}).get(tk, 0.2) if arm == "ADJ" else (quiet_breach or {}).get(tk, 0.2)
                k = cnt[arm]
                cnt[arm] += 1
                br = (k % 10) < round(rate * 10)
                ret = (0.05 if k % 2 == 0 else -0.05) if br else 0.01
                if override and (tk, day) in override:
                    ret = override[(tk, day)]
                rows.append(dict(d=day, tk=tk, sig="HOLD", pv="A-S1D2-B1-E1", raw=True, k8_n=1,
                                 k8_date=day if arm == "ADJ" else None, f4_date=None,
                                 degraded=(tk, day) in degraded))
                master[(day, tk)] = dict(p0=100.0, p5=100 * (1 + ret), p5_raw=100 * (1 + ret))
        return rows, master, days

    res = lambda m: {k: v["p5"] is not None for k, v in m.items()}
    tks = ["AAPL", "DOW", "FTI", "GM", "JPM", "MSFT", "NKE", "NVDA", "PM", "PWR", "RTX", "SND", "WMT"]
    far = dict(review_date=D(2027, 1, 4), e42_resolved_through=D(2027, 1, 4),
               e43_filed_from=D(2026, 9, 1), e43_filed_through=D(2026, 12, 31))

    # 1 breach boundary, exact
    rows, master, days = mk(["GM"], 4, override={("GM", D(2026, 9, 1)): 0.03, ("GM", D(2026, 9, 2)): 0.0299,
                                                    ("GM", D(2026, 9, 3)): -0.03})
    b = {x["d"]: x["breach"] for x in e42_population(rows, master, D(2026, 12, 31), res(master))[0]}
    check("ret5 = +3.00% is a breach", b[D(2026, 9, 1)], True)
    check("ret5 = +2.99% is not", b[D(2026, 9, 2)], False)
    check("ret5 = -3.00% is a breach", b[D(2026, 9, 3)], True)
    # 1b the verdict is column N's float rule, not exact arithmetic: 7.00 -> 7.21 is K = 0.029999999999999995
    rows, master, days = mk(["GM"], 2)
    master[(days[0], "GM")] = dict(p0=7.0, p5=7.21, p5_raw=7.21)
    master[(days[1], "GM")] = dict(p0=7.0, p5=6.79, p5_raw=6.79)
    pop = {x["d"]: x for x in e42_population(rows, master, D(2026, 12, 31), res(master))[0]}
    check("7.00 -> 7.21 is not a breach (column N says YES)", pop[days[0]]["breach"], False)
    check("7.00 -> 6.79 is not a breach either", pop[days[1]]["breach"], False)
    check("...and both are flagged as near the band", (pop[days[0]]["near"], pop[days[1]]["near"]), (True, True))
    import repair_outcome_close as roc
    check("the read's verdict equals band_flag on K", roc.band_flag("HOLD", k_of(7.0, 7.21)), "YES")
    # 2 the cut, both edges, and the blind path
    rows, master, days = mk(["GM"], 12)
    through = S(days[5], 5)
    pop, _ = e42_population(rows, master, through, res(master))
    check("a row whose +5d session IS the cut enters", days[5] in {x["d"] for x in pop}, True)
    check("a row whose +5d session is after the cut does not", days[6] in {x["d"] for x in pop}, False)
    blind = e42_population(rows, master, through, res(master), outcomes=False)[0]
    check("the blind population carries no return or breach", any("ret5" in x or "breach" in x for x in blind), False)
    # 3 DEGRADED rows are excluded, by the counter and the read alike
    rows, master, days = mk(["GM"], 12, degraded={("GM", D(2026, 9, 1))})
    pop, cnt = e42_population(rows, master, D(2027, 1, 4), res(master))
    check("a DEGRADED row is not in the read", D(2026, 9, 1) in {x["d"] for x in pop}, False)
    check("...and the counter reports it", cnt["degraded"], 1)
    # 4 a MUST-FAIL: text in Price +5d that the counter calls resolved
    rows, master, days = mk(["GM"], 8)
    master[(days[0], "GM")] = dict(master[(days[0], "GM")], p5=None, p5_raw="n/a")
    try:
        e42_population(rows, master, D(2027, 1, 4), {k: True for k in master})
        check("a resolved row whose Price +5d is not a number raises", False, True)
    except ValueError:
        check("a resolved row whose Price +5d is not a number raises", True, True)
    # 5 clear POSITIVE / NEGATIVE end to end
    adj, qb = {tk: 0.1 for tk in tks}, {tk: 0.4 for tk in tks}
    rows, master, days = mk(tks, 40, adj_breach=adj, quiet_breach=qb)
    R = compute(rows, master, res(master), {}, far)
    check("clear effect reads POSITIVE", R["disp"], "POSITIVE")
    check("pooled d is exactly -30 pt", R["d"], Fr(-3, 10))
    rows2, master2, _ = mk(tks, 40, adj_breach=qb, quiet_breach=adj)
    check("mirror effect reads NEGATIVE", compute(rows2, master2, res(master2), {}, far)["disp"], "NEGATIVE")
    # 6 the bar in exact arithmetic (the float version read 4.999999999999999)
    dd = _mean([Fr(-1, 20)] * 7)
    check("seven tickers at exactly -5 pt pool to exactly -1/20", dd, Fr(-1, 20))
    check("exactly 5.0 pt reads POSITIVE", disposition(dd, 200, 12, [(D(2026, 9, 1), dd, 12)], dd)[0], "POSITIVE")
    check("4.99 pt reads INSUFFICIENT", disposition(Fr(-499, 10000), 200, 12, [], Fr(-499, 10000))[0], "INSUFFICIENT")
    check("a LOCO sign flip reads INSUFFICIENT",
          disposition(Fr(-1, 10), 200, 12, [(D(2026, 9, 1), Fr(-1, 10), 12), (D(2026, 9, 2), Fr(1, 100), 12)],
                      Fr(-1, 10))[0], "INSUFFICIENT")
    check("a drop-largest sign flip reads INSUFFICIENT",
          disposition(Fr(-1, 10), 200, 12, [(D(2026, 9, 1), Fr(-1, 10), 12)], Fr(1, 50))[0], "INSUFFICIENT")
    check("d = 0 reads INSUFFICIENT", disposition(Fr(0), 200, 12, [], Fr(0))[0], "INSUFFICIENT")
    check("n < 150 reads INSUFFICIENT TEST CONDITIONS", disposition(Fr(-1, 5), 149, 12, [], Fr(-1, 5))[0],
          "INSUFFICIENT TEST CONDITIONS")
    check("6 of 13 reads INSUFFICIENT TEST CONDITIONS", disposition(Fr(-1, 5), 200, 6, [], Fr(-1, 5))[0],
          "INSUFFICIENT TEST CONDITIONS")
    # 7 unweighted mean, qualification, largest ticker, fallback
    X = lambda tk, arm, br: dict(d=D(2026, 9, 1), tk=tk, arm=arm, ret5=Fr(0), breach=br)
    pp = ([X("GM", "ADJ", False)] * 3 + [X("GM", "QUIET", True)] * 3 + [X("WMT", "ADJ", False)] * 30
          + [X("WMT", "QUIET", False)] * 30 + [X("AAPL", "ADJ", True)] * 9 + [X("AAPL", "QUIET", False)] * 2)
    d, qs, tab = pooled_d(pp)
    check("pooled d is the UNWEIGHTED mean (GM -100, WMT 0 -> -50)", d, Fr(-1, 2))
    check("a name with 2 QUIET rows falls to the fallback", "AAPL" in qs, False)
    check("largest qualifier = most ADJACENT rows", largest_qualifier(tab, qs), "WMT")
    fb, per, fbd = fallback(pp, qs, FROZEN_TIERS)
    check("fallback pools AAPL's ADJ against the HIGH tier's QUIET", (per["HIGH"]["nA"], per["HIGH"]["nQ"]), (9, 2))
    check("a tier under 3 per arm is not pooled", per["HIGH"]["d"], None)
    check("one cohort only -> one fold with no qualifiers", [x[2] for x in loco(pp)], [0])
    # 8 tier drift membership
    m = {(D(2026, 9, 1) + dt.timedelta(days=7 * k), tk): dict(p0=100.0, p5=100 * (1 + (i + 1) / 1000))
         for i, tk in enumerate(sorted(COVERED)) for k in range(3)}
    _, now, moved = tier_drift(m, D(2027, 1, 4))
    check("alphabetical medians put AAPL in LOW", now["AAPL"], "LOW")
    check("re-tier lists the names that moved, with both tiers", ("AAPL", "HIGH", "LOW") in [x[:3] for x in moved], True)
    # 9 fin staleness
    ex = {(D(2026, 10, 29), "DOW"): dict(raw=None, periodic=D(2026, 10, 28), fin=D(2026, 6, 30), pv=""),
          (D(2026, 10, 29), "GM"): dict(raw=None, periodic=D(2026, 10, 28), fin=D(2026, 9, 30), pv="")}
    check("fin trailing periodic by > 60 days is counted", fin_stale(ex, D(2026, 10, 29)), ([("DOW", 120)], 2))
    # 10 E4-3: the window's edges, items, verdict
    def ev_rows(tk, f):
        n = cal.next_session(f)
        return [dict(d=f, tk=tk, sig="HOLD", pv="A-S1D2-B1-E1", raw=True, k8_n=1, k8_date=f, f4_date=None),
                dict(d=n, tk=tk, sig="HOLD", pv="A-S1D2-B1-E1", raw=True, k8_n=1, k8_date=f, f4_date=None)]
    c = dict(review_date=D(2026, 11, 7), e42_resolved_through=D(2026, 11, 5),
             e43_filed_from=D(2026, 9, 1), e43_filed_through=D(2026, 11, 5))
    erows = ev_rows("MSFT", D(2026, 10, 28)) + ev_rows("GM", D(2026, 9, 1)) + ev_rows("PM", D(2026, 8, 31)) \
        + ev_rows("JPM", D(2026, 11, 5)) + ev_rows("NKE", D(2026, 11, 9))
    ev, _ = e43_events(erows, c)
    check("E4-3 includes 09-01 and 11-05, excludes 08-31 and 11-09",
          sorted((e[0], str(e[1])) for e in ev), [("GM", "2026-09-01"), ("JPM", "2026-11-05"), ("MSFT", "2026-10-28")])
    f, n = D(2026, 10, 28), cal.next_session(D(2026, 10, 28))
    ex = {(f, "MSFT"): dict(raw=Fr(74), periodic=None, fin=None, pv="A-S1D2-B1-E1"),
          (n, "MSFT"): dict(raw=Fr(85), periodic=None, fin=None, pv="A-S1D2-B1-E1")}
    tr = e43_trace([("MSFT", f, "OBSERVABLE")], ex)
    check("trace: raw on both days, the change, D2 flag", (tr[0]["raw0"], tr[0]["raw1"], tr[0]["delta"], tr[0]["d2"]),
          (Fr(74), Fr(85), Fr(11), True))
    check("trace lists BOTH 10-28 MSFT 8-Ks", tr[0]["items"].count("0001193125-26-4361"), 2)
    check("an unmapped event says so", e43_trace([("GM", D(2026, 9, 9), "OBSERVABLE")], {})[0]["items"], "not resolved")
    check("E4-3 below 20 observable is INSUFFICIENT", e43_verdict(19), "INSUFFICIENT")
    check("E4-3 at 20 is VERDICT-descriptive", e43_verdict(20), "VERDICT-descriptive")
    tmp = tempfile.mkdtemp(prefix="e4x_")
    try:
        # 11 log-line parsing on real-format lines
        lp = os.path.join(tmp, "signals_2026-11-05.log")
        with open(lp, "w", encoding="utf-8") as fh:
            fh.write('2026-11-05 09:50:35,289 | INFO | Signal JSON: {"ticker": "MSFT", "signal": "BUY", '
                     '"confidence": 80, "confidence_raw": 80, "prompt_variant": "A-S1D2-B1-E1"} | [PHASE 3-C DRY RUN] '
                     'MSFT | E[8k=4@2026-11-05; form4=+0/-3@2026-10-15; periodic=10-Q@2026-10-28; fin=11@2026-09-30]\n')
            fh.write('2026-11-05 09:51:00,000 | INFO | Signal JSON: {"ticker": "DOW", "signal": "HOLD", '
                     '"confidence": 50, "confidence_raw": 50, "prompt_variant": "A-S1D2-B1-E1"} | DOW | '
                     'E[8k=0; form4=0f; periodic=10-Q@2026-10-23; fin=7@2026-06-30+coreg0000029915]\n')
            fh.write('2026-11-05 09:52:00,000 | INFO | Signal JSON: {"ticker": "SND", "signal": "HOLD", '
                     '"confidence": 40, "confidence_raw": 40, "prompt_variant": "A-S1D1-B1-E1"} | SND | '
                     'E[8k=2@2026-08-11; form4=1f@2026-07-27; periodic=10-Q@2026-08-11; fin=degraded]\n')
        ex = load_log_extras([lp])
        k = (D(2026, 11, 5), "MSFT")
        check("parses raw, periodic and fin from a real-format line",
              (ex[k]["raw"], ex[k]["periodic"], ex[k]["fin"]), (Fr(80), D(2026, 10, 28), D(2026, 9, 30)))
        check("parses a co-registrant fin date", ex[(D(2026, 11, 5), "DOW")]["fin"], D(2026, 6, 30))
        with open(lp, encoding="utf-8") as fh:
            crow = ec.parse_log_lines(D(2026, 11, 5), fh)
        check("e4_counter flags fin=degraded on a real-format line", [r["degraded"] for r in crow], [False, False, True])

        # 12 THE MAIN FLOW: record once, atomically, verified, then show
        R.update(taken_at="selftest", master_sha="0" * 64, master_src="synthetic", log_hashes={},
                 blobs={"e4_exit_read.py": "f" * 40}, git_head="selftest")
        rp, md = os.path.join(tmp, "logs", "instrument_readings.json"), os.path.join(tmp, "e4.md")
        ok, text, msg = record_and_render(far, R, rp, md)
        check("a verified record returns the write-up", (ok, text is not None, os.path.exists(md)), (True, True, True))
        stored = guard.load_readings_strict(rp)
        check("both readings are in one record", sorted(stored), [INSTR_E42, INSTR_E43])
        check("the stored disposition is the computed one", stored[INSTR_E42][0]["detail"]["disposition"], "POSITIVE")
        ok2, text2, _ = record_and_render(far, R, rp, md)
        check("a second record is REFUSED and shows nothing", (ok2, text2), (False, None))
        os.remove(md)
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):     # synthetic record: keep it off the console
            print_recorded(stored, md)
        check("a missing write-up is restored from the record, not recomputed", os.path.exists(md), True)
        with open(rp, "w") as fh:
            fh.write("not json")
        ok3, text3, _ = record_and_render(far, R, rp, md)
        check("a corrupt readings log refuses the record and shows nothing", (ok3, text3), (False, None))
        bad_rp = os.path.join(tmp, "isadir")
        os.makedirs(bad_rp)
        ok4, text4, _ = record_and_render(far, R, bad_rp, md)
        check("an unwritable readings path refuses and shows nothing", (ok4, text4), (False, None))
        # 12b the authoritative exit file: survives a nightly rewrite of the shared log
        ep, sp = os.path.join(tmp, "x", "exit_readings.json"), os.path.join(tmp, "x", "instrument_readings.json")
        ok5, text5, _ = record_and_render(far, R, sp, md, exit_path=ep)
        check("an exit record lands in the exit file AND the shared log",
              (ok5, sorted(guard.load_readings_strict(ep)), sorted(guard.load_readings_strict(sp))),
              (True, [INSTR_E42, INSTR_E43], [INSTR_E42, INSTR_E43]))
        with open(sp, "w") as fh:
            fh.write("{}")                                      # a nightly writer that drops the entry
        found = guard.load_exit_records([INSTR_E42, INSTR_E43], [ep, sp])
        check("the record is still found after the shared log loses it", sorted(found), [INSTR_E42, INSTR_E43])
        ok6, _ = guard.gate_not_recorded([INSTR_E42, INSTR_E43], [ep, sp])
        check("gate 4 still refuses a second read", ok6, False)
        ok7, text7, _ = record_and_render(far, R, sp, md, exit_path=ep)
        check("a second exit record is REFUSED and shows nothing", (ok7, text7), (False, None))
        txt = render_read(far, R)
        check("the raw gap is labelled a control EXPECTED NEGATIVE", "EXPECTED NEGATIVE" in txt, True)
        check("a zero-ADJACENT write-up renders (no division by zero)", "DISPOSITION" in render_read(far, dict(R, n_adj=0)), True)
        prev = render_preview(far, ec.count_e42(rows, res(master), far["e42_resolved_through"]), 0, 0, [])
        check("the blind preview prints no percentage", "%" in prev, False)
        check("the ruled cut is immutable", isinstance(cut(), types.MappingProxyType), True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("e4_exit_read selftest (synthetic data only): " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
