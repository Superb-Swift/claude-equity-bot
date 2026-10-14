#!/usr/bin/env python3
"""
e4_counter.py - the Phase 3-C exit criteria, COUNTED. Never read.

WHY (2026-10-09). E4-2's binding exit criterion (150 resolved ADJACENT rows)
crossed on 2026-10-01 and no instrument said so: the count had only ever been
taken by hand in reviews. DP-3C-ay (Rob, 2026-10-09) then held the exit for
E4-3's 20 events, which nothing counted either. "A bar no instrument can
evaluate is a note asking the operator to remember" (2026-09-08).

WHAT IT COUNTS - definitions read at source, never recalled:
  Phase3C_E4_Endpoint_PreRegistration_v1.md (v1.3) and the rulings named below.

  CLOCK    admitted EDGAR-live cohorts: logs whose rows carry a prompt_variant
           ending "-E1", on or after 2026-08-13 (DP-3C-t: 08-03 was SHAKEDOWN;
           the clock starts 08-13). A control cohort (no -E1, e.g. 08-19) is
           absent from E4, not excluded from it.
  E4-2     HOLD rows on the 13 ADJACENT-eligible names (T-A minus CORN; GLD is
           T-B - ruled 2026-08-20), on admitted cohorts. ADJACENT = the row's
           own E tag carries an 8-K or Form 4 dated on, or within K = 5 NYSE
           sessions before, the signal date (pre-reg 3.1). Otherwise
           COVERED-QUIET. RESOLVED = the master's Price +5d is filled and the
           +5d session is on or before the as-of date. PRIMARY QUALIFIER =
           a name with >= 3 resolved rows in EACH arm (pre-reg 3.2).
           Validated: reproduces the 2026-09-02 standing exactly
           (12 / 141 / 69 / 57 / 50 / 6 qualifiers) - see --reproduce-0902.
  E4-3     8-Ks on T-A names (14, CORN included) filed on or after 2026-09-01
           (DP-3C-ac restart). An event is OBSERVABLE when an admitted row
           with confidence_raw exists for that name on the filing date AND on
           the following NYSE session (pre-reg E4-3 "Read"). 20 observable
           events are needed (DP-3C-ay; backstop 2026-11-20).
           8-K dates come from the E tag (`8k=N@latest`), so two 8-Ks filed
           between consecutive runs would show as one. Where the 30-day count
           N rises by more than the new dates explain, the gap is printed as
           POSSIBLE UNSEEN - never added to the count.

WHAT IT NEVER DOES - BLIND by construction (DP-3C-ah, DP-3C-ay):
  It reads no return, no breach, no confidence value. "Resolved" is the
  presence of a close, and "observable" is the presence of confidence_raw.
  No rate, IC, rho or accuracy is computed anywhere in this file.

Read-only. Refuses tracker_with_registry.xlsx. Exit 0 = counted, 2 = could not.
Advisory-only - no orders - not financial advice.
"""
import argparse
import datetime as dt
import os
import re
import sys
from collections import Counter, defaultdict

import trading_calendar as cal

# --------------------------------------------------------------------------- #
# Definitions (each names its source)
# --------------------------------------------------------------------------- #
T_A = ("AAPL", "CORN", "DOW", "FTI", "GM", "JPM", "MSFT", "NKE", "NVDA", "PM",
       "PWR", "RTX", "SND", "WMT")                     # pre-reg 1, coverage tier T-A
E42_ELIGIBLE = tuple(t for t in T_A if t != "CORN")   # ruled 2026-08-20: 13 names
CLOCK_START = dt.date(2026, 8, 13)                    # DP-3C-t / first-cohort disposition
E43_START = dt.date(2026, 9, 1)                       # DP-3C-ac
K = 5                                                 # pre-reg 3.1
E42_N = 150                                           # pre-reg 3.1
E42_MIN_PER_ARM = 3                                   # pre-reg 3.2
E43_N = 20                                            # pre-reg E4-3 / DP-3C-ay
E43_BACKSTOP = dt.date(2026, 11, 20)                  # DP-3C-ay (i)
REFUSED = ("tracker_with_registry.xlsx",)

_TK = re.compile(r'Signal JSON: \{"ticker": "([A-Z][A-Z.\-]*)"')
_SIG = re.compile(r'"signal": "([A-Z]+)"')
_PV = re.compile(r'"prompt_variant": "([^"]+)"')
_RAW = re.compile(r'"confidence_raw": -?\d')
_ETAG = re.compile(r"E\[([^\]]*)\]")
_8K = re.compile(r"8k=(\d+)(?:@(\d{4}-\d{2}-\d{2}))?")
_F4 = re.compile(r"form4=[^;\]]*?@(\d{4}-\d{2}-\d{2})")
_LOGDATE = re.compile(r"signals_(\d{4}-\d{2}-\d{2})\.log$")


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def parse_log_lines(date, lines):
    """One record per Signal JSON line. Reads presence and dates only."""
    out = []
    for line in lines:
        m = _TK.search(line)
        if not m:
            continue
        sig = _SIG.search(line)
        pv = _PV.search(line)
        e = _ETAG.search(line)
        etag = e.group(1) if e else None
        k8 = _8K.search(etag or "")
        f4 = _F4.search(etag or "")
        out.append(dict(
            d=date, tk=m.group(1), sig=sig.group(1) if sig else None,
            pv=pv.group(1) if pv else "", raw=bool(_RAW.search(line)),
            k8_n=int(k8.group(1)) if k8 else None,
            k8_date=dt.date.fromisoformat(k8.group(2)) if k8 and k8.group(2) else None,
            f4_date=dt.date.fromisoformat(f4.group(1)) if f4 else None,
        ))
    return out


def load_logs(pattern):
    import signal_logs
    paths, info = signal_logs.discover(pattern)
    rows = []
    for p in paths:
        m = _LOGDATE.search(os.path.basename(p))
        if not m:                      # e.g. *_run1_coldstart.log is not a cohort
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            rows.extend(parse_log_lines(dt.date.fromisoformat(m.group(1)), fh))
    return rows, info


def load_resolved(master):
    """{(date, ticker): True} where the master's Price +5d is filled."""
    import openpyxl
    wb = openpyxl.load_workbook(master, read_only=True, data_only=True)
    ws = wb["Signals"]
    out = {}
    for r in ws.iter_rows(min_row=5, values_only=True):
        if r and isinstance(r[0], dt.datetime) and r[1]:
            out[(r[0].date(), str(r[1]).strip())] = r[7] is not None
    wb.close()
    return out


# --------------------------------------------------------------------------- #
# Counts
# --------------------------------------------------------------------------- #
def admitted(r):
    return r["d"] >= CLOCK_START and r["pv"].endswith("-E1")


def gap_sessions(earlier, later):
    """NYSE sessions from `earlier` forward to `later` (0 when the same day)."""
    return len(cal.sessions_between(earlier, later)) - 1


def is_adjacent(r):
    for f in (r["k8_date"], r["f4_date"]):
        if f and f <= r["d"] and gap_sessions(f, r["d"]) <= K:
            return True
    return False


def count_e42(rows, resolved, as_of):
    adm = [r for r in rows if admitted(r) and r["d"] <= as_of]
    cohorts = sorted({r["d"] for r in adm})
    hold = [r for r in adm if r["sig"] == "HOLD" and r["tk"] in E42_ELIGIBLE]
    out = dict(cohorts=len(cohorts), hold=len(hold))
    arm = {"ADJ": [], "QUIET": []}
    for r in hold:
        arm["ADJ" if is_adjacent(r) else "QUIET"].append(r)
    out["adjacent"] = len(arm["ADJ"])

    def res(r):
        return resolved.get((r["d"], r["tk"]), False) and cal.shift_sessions(r["d"], 5) <= as_of

    radj = [r for r in arm["ADJ"] if res(r)]
    rq = [r for r in arm["QUIET"] if res(r)]
    out["adj_resolved"], out["quiet_resolved"] = len(radj), len(rq)
    ca, cq = Counter(r["tk"] for r in radj), Counter(r["tk"] for r in rq)
    out["qualifiers"] = sorted(t for t in E42_ELIGIBLE
                               if ca[t] >= E42_MIN_PER_ARM and cq[t] >= E42_MIN_PER_ARM)
    out["per_ticker"] = {t: (ca[t], cq[t]) for t in E42_ELIGIBLE}
    out["supply"] = (out["adjacent"] / out["cohorts"]) if out["cohorts"] else 0.0
    return out


def count_e43(rows, as_of):
    by_tk = defaultdict(list)
    for r in rows:
        if r["tk"] in T_A and r["d"] <= as_of:
            by_tk[r["tk"]].append(r)
    have_raw = {(r["d"], r["tk"]) for r in rows if admitted(r) and r["raw"] and r["d"] <= as_of}
    events, unseen, unseen_at = [], 0, []
    for tk, rs in by_tk.items():
        rs.sort(key=lambda r: r["d"])
        seen, prev = set(), None
        for r in rs:
            if r["k8_date"] and r["k8_date"] >= E43_START and r["k8_date"] not in seen:
                seen.add(r["k8_date"])
                new_here = 1
            else:
                new_here = 0
            if prev is not None and r["k8_n"] is not None and prev["k8_n"] is not None:
                rise = r["k8_n"] - prev["k8_n"]
                if rise > new_here and (r["k8_date"] or dt.date.min) >= E43_START:
                    unseen += rise - new_here
                    unseen_at.append((tk, r["d"], rise - new_here))
            prev = r
        for f in sorted(seen):
            events.append((tk, f))
    status = Counter()
    detail = []
    for tk, f in sorted(events, key=lambda x: (x[1], x[0])):
        if not cal.is_trading_day(f):
            s = "UNOBSERVABLE (filed on a non-session)"
        else:
            nxt = cal.next_session(f)
            if nxt > as_of:
                s = "PENDING (next session not yet run)"
            elif (f, tk) in have_raw and (nxt, tk) in have_raw:
                s = "OBSERVABLE"
            elif f in cal.BOT_ABSENT or nxt in cal.BOT_ABSENT:
                s = "UNOBSERVABLE (pre-registered no-run session)"
            else:
                s = "UNOBSERVABLE (no admitted row with confidence_raw)"
        status[s.split(" ")[0]] += 1
        detail.append((tk, f, s))
    return dict(events=len(events), status=status, detail=detail, unseen=unseen,
                unseen_at=unseen_at)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def report(e42, e43, as_of, log_info):
    L = []
    L.append("=" * 78)
    L.append(f"E4 EXIT COUNTER - counts only, as of {as_of}  (DP-3C-ay; never a read)")
    L.append("=" * 78)
    L.append(f"  logs: {log_info.get('n', 0)} ({log_info.get('first')} .. {log_info.get('last')})")
    L.append("")
    L.append(f"  CLOCK   admitted EDGAR-live cohorts: {e42['cohorts']} of ~10   "
             f"{'MET' if e42['cohorts'] >= 10 else 'collecting'}")
    L.append("")
    L.append(f"  E4-2    resolved ADJACENT rows: {e42['adj_resolved']} of {E42_N}   "
             f"{'n MET' if e42['adj_resolved'] >= E42_N else 'collecting'}")
    L.append(f"          ADJACENT rows {e42['adjacent']} ({e42['supply']:.2f}/cohort; "
             f"pre-registered ~7.6) | COVERED-QUIET resolved {e42['quiet_resolved']}")
    L.append(f"          primary qualifiers (>= {E42_MIN_PER_ARM} resolved per arm): "
             f"{len(e42['qualifiers'])} of {len(E42_ELIGIBLE)} "
             f"[{', '.join(e42['qualifiers'])}]; the rest read under the fallback")
    top = sorted(e42["per_ticker"].items(), key=lambda kv: -kv[1][0])[:3]
    if e42["adj_resolved"]:
        L.append("          largest ADJACENT shares (concentration, pre-reg 2): "
                 + ", ".join(f"{t} {a}/{e42['adj_resolved']}" for t, (a, _q) in top))
    L.append("")
    obs = e43["status"].get("OBSERVABLE", 0)
    L.append(f"  E4-3    observable 8-K events on T-A since {E43_START}: {obs} of {E43_N}   "
             f"{'n MET' if obs >= E43_N else 'collecting'}   (backstop {E43_BACKSTOP})")
    L.append(f"          detected {e43['events']}: " + ", ".join(
        f"{k} {v}" for k, v in sorted(e43["status"].items())))
    if e43["unseen"]:
        L.append(f"          POSSIBLE UNSEEN 8-Ks (30-day count rose more than new dates explain): "
                 f"{e43['unseen']} - not counted; check edgar_cache if it matters")
        for tk, day, k in e43["unseen_at"]:
            L.append(f"            {tk} on the {day} run: {k} more 8-K(s) than new dates")
    for tk, f, s in e43["detail"]:
        L.append(f"            {f}  {tk:<5} {s}")
    L.append("")
    L.append("  BLIND: no return, breach, confidence value or rate is read by this tool.")
    L.append("  Advisory-only - no orders - not financial advice.")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Self-test: synthetic, offline, each rule with a case that must fail
# --------------------------------------------------------------------------- #
def selftest():
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] {name}: got {got!r}, want {want!r}")

    d = dt.date(2026, 9, 15)                       # a Tuesday session
    def row(tk, sig="HOLD", pv="A-S1D2-B1-E1", k8=None, f4=None, day=d, raw=True, n=None):
        return dict(d=day, tk=tk, sig=sig, pv=pv, raw=raw,
                    k8_n=n if n is not None else (1 if k8 else 0), k8_date=k8, f4_date=f4)

    five_back = cal.shift_sessions(d, -5)
    six_back = cal.shift_sessions(d, -6)
    check("filing 5 sessions back is ADJACENT", is_adjacent(row("GM", k8=five_back)), True)
    check("filing 6 sessions back is QUIET (negative case)", is_adjacent(row("GM", k8=six_back)), False)
    check("Form 4 on the signal date is ADJACENT", is_adjacent(row("GM", f4=d)), True)
    check("a filing AFTER the signal date is QUIET", is_adjacent(row("GM", k8=cal.next_session(d))), False)
    check("control cohort (no -E1) is not admitted", admitted(row("GM", pv="A-S1D2-B1")), False)
    check("pre-clock -E1 cohort is not admitted", admitted(row("GM", day=dt.date(2026, 8, 10))), False)
    rows = [row("GM", k8=five_back), row("CORN", k8=five_back), row("USO", k8=five_back),
            row("GM", sig="BUY", k8=five_back)]
    e = count_e42(rows, {}, d)
    check("E4-2 counts HOLD on eligible names only (CORN, USO, BUY out)", e["adjacent"], 1)
    check("nothing resolved without a filled close", e["adj_resolved"], 0)
    e = count_e42(rows, {(d, "GM"): True}, d)
    check("not resolved before its +5d session (as-of guard)", e["adj_resolved"], 0)
    e = count_e42(rows, {(d, "GM"): True}, cal.shift_sessions(d, 5))
    check("resolved once the +5d session has passed", e["adj_resolved"], 1)
    nxt = cal.next_session(d)
    ev = [row("NKE", k8=d, day=d), row("NKE", k8=d, day=nxt)]
    check("E4-3 event with rows on both sessions is OBSERVABLE",
          count_e43(ev, nxt)["status"].get("OBSERVABLE", 0), 1)
    ev2 = [row("NKE", k8=d, day=d, raw=False), row("NKE", k8=d, day=nxt)]
    check("E4-3 without confidence_raw is not observable (negative case)",
          count_e43(ev2, nxt)["status"].get("OBSERVABLE", 0), 0)
    check("E4-3 waits for the following session",
          count_e43([row("NKE", k8=d, day=d)], d)["status"].get("PENDING", 0), 1)
    check("E4-3 ignores names outside T-A",
          count_e43([row("SNOW", k8=d, day=d), row("SNOW", k8=d, day=nxt)], nxt)["events"], 0)
    old = [row("NKE", k8=dt.date(2026, 8, 28), day=d), row("NKE", k8=dt.date(2026, 8, 28), day=nxt)]
    check("E4-3 ignores 8-Ks before the 2026-09-01 restart", count_e43(old, nxt)["events"], 0)
    jump = [row("PM", k8=None, day=d, n=0), row("PM", k8=d, day=nxt, n=2)]
    check("a 30-day count rising by 2 on one new date flags 1 unseen", count_e43(jump, nxt)["unseen"], 1)
    src = open(__file__, encoding="utf-8").read()
    banned = ("breach_rate", "spearman", "accuracy(", "ret5", "Return +5d")
    check("no rate, correlation or return is computed in this file",
          [b for b in banned if src.count(b) > 1], [])
    print("ALL PASS" if ok else "SELFTEST FAILED")
    return ok


def reproduce_0902(rows, resolved):
    """The definitions must reproduce the hand count of the 2026-09-02 standing."""
    e = count_e42(rows, resolved, dt.date(2026, 9, 2))
    want = dict(cohorts=12, hold=141, adjacent=69, adj_resolved=57, quiet_resolved=50)
    got = {k: e[k] for k in want}
    ok = got == want and len(e["qualifiers"]) == 6
    print(f"  09-02 standing  want {want}, 6 qualifiers")
    print(f"  recomputed      got  {got}, {len(e['qualifiers'])} qualifiers {e['qualifiers']}")
    print("REPRODUCES" if ok else "DOES NOT REPRODUCE - do not trust the counts below")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Phase 3-C exit criteria, counted (never read).")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--logs", default=os.path.join("logs", "signals_*.log"))
    ap.add_argument("--as-of", type=dt.date.fromisoformat, default=None,
                    help="count as of this date (default: newest cohort in the logs)")
    ap.add_argument("--md", default=None, help="also write the report to this .md file")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reproduce-0902", action="store_true",
                    help="check the definitions against the 2026-09-02 hand count")
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 1
    if os.path.basename(a.tracker) in REFUSED:
        print("refused: read THE MASTER, not the generated report copy")
        return 2
    try:
        rows, info = load_logs(a.logs)
        resolved = load_resolved(a.tracker)
    except Exception as exc:                                  # noqa: BLE001
        print(f"E4 COUNTER COULD NOT RUN: {exc}")
        return 2
    if a.reproduce_0902:
        return 0 if reproduce_0902(rows, resolved) else 1
    as_of = a.as_of or max(r["d"] for r in rows)
    text = report(count_e42(rows, resolved, as_of), count_e43(rows, as_of), as_of, info)
    print(text)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write(f"# E4 exit counter\n\n```\n{text}\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
