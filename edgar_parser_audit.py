# =============================================================================
# edgar_parser_audit.py  —  E3 PRE-DEPLOY PARSER AUDIT  (Phase 3-C / EW2)
# =============================================================================
# WHAT THIS IS:
#   The non-negotiable gate that comes BEFORE 3-C go-live (Phase3C_EDGAR_
#   Scope_Spec.md §5). It synthesises a full 24-row Phase 3-C log — new phase
#   token, the live era stamp (read from main.py; `A-S1D2-B1-E1` since the
#   2026-08-31 H1 fix), and the trailing E[...] tag — and
#   runs the REAL parsers against it. Not a re-implementation of their regexes:
#   it imports analyze_log.parse_log and parse_log_to_tracker.parse_log_file
#   and asserts on what they actually return.
#
# WHY IT EXISTS:
#   A tag or era change has silently broken the parsers TWICE at a phase
#   cutover:
#     * 2026-06-15  analyze_log.py     `PHASE \d DRY RUN` matched one digit,
#                                      so "3-A" parsed 0 signals.
#     * 2026-07-07  parse_log_to_tracker.py  ACCOUNT_RE hardcoded
#                                      "2 DRY RUN|3-A", so every 3-B row would
#                                      have imported as Account="Unknown".
#   Both were SILENT. Neither raised. The 6/15 case shipped and was found
#   after the fact. This harness exists so the third cutover is caught before
#   it reaches a canonical cohort rather than after.
#
# WHAT IT ASSERTS (Scope Spec §5, items 1-3):
#   1. analyze_log.parse_log            returns 24 signals
#   2. parse_log_to_tracker.parse_log_file returns 24 rows
#   3. Accounts are REAL — zero "Unknown"
#   4. Base operative confidence is UNCHANGED by the E[...] tag: a control
#      log without the tag and a treatment log with it must yield identical
#      confidences, signals, DQ and prices, ticker by ticker
#   5. The live era label does NOT trip the variant-"B" skip
#   6. The E[...] tag does not leak into any parsed FIELD other than the
#      reason text (where H1/S1/D/B already land by the same mechanism)
#   7. signal_scan.parse_log — the THIRD consumer of the E[...] tag, added
#      2026-08-10 to close the gap the analyst notes flagged: signal_scan.py
#      was already the third file to hardcode a phase/era assumption
#      (2026-06-15 analyze_log, 2026-07-07 parse_log_to_tracker) and had
#      never been added to this audit, even though it parses the same
#      E[...] blob as a field. Asserts 24/24 rows, the tag present on every
#      row once EDGAR is live, "no filings" landing on exactly the
#      non-EDGAR names, EDGAR-covered names never reading "no filings", the
#      synthetic log actually exercising all three DP-3C-j fin= states
#      (N@period / degraded / none), and the control log (no tag at all)
#      reading as untagged rather than as a degenerate all-"no filings" run.
#   9. log_tracker_crosscheck.parse_log — the FOURTH log reader, added
#      2026-08-12 after it returned ZERO rows against the first live 3-C
#      cohort. Its LINE_RE hardcoded "[PHASE 3-B DRY RUN]", so the 3-C
#      token matched nothing and all 24 master rows reported as EXTRA.
#      FOURTH instance of the hardcoded-phase-token class, and the first
#      to reach a canonical cohort since 2026-07-07.
#      THE DEFECT WAS COVERAGE, NOT THE REGEX: the three parsers already
#      in this audit all handled the cutover correctly. This tool was
#      built 2026-07-30, this list was enumerated 2026-08-03, and nobody
#      re-derived it when a new log reader appeared. Asserts 24/24 on the
#      treatment, control and approval logs, that the phase token is
#      captured rather than assumed, and — the check that actually
#      prevents recurrence — that a token this project has NEVER emitted
#      still parses. A parser that is merely correct for TODAY's token is
#      what failed on 8/12.
#
# USAGE (project root, venv active):
#     python edgar_parser_audit.py
#     python edgar_parser_audit.py --keep      (leave the synthetic logs on disk)
#
# EXIT CODES:  0 = audit passed, go-live unblocked on this criterion
#              1 = audit FAILED, DO NOT DEPLOY
#              2 = harness could not run (missing parser module)
#
# ANALYST NOTE — WHAT THIS DOES *NOT* PROVE:
#   It proves the PARSERS tolerate the 3-C line shape. It does NOT prove the
#   SEC fetch path works, that the CIK map resolves, or that any real filing
#   was retrieved. Those are `edgar_client.py --coverage` and `--ticker`, and
#   they are separate go-live conditions. Passing this audit while EDGAR
#   silently fetches nothing would produce a clean 24/24 run in which every
#   E tag reads "E[no filings]" — which is exactly why the coverage run is
#   listed alongside, not instead.
#
# Advisory-only · no orders · not financial advice.
# =============================================================================

import os
import re
import sys
import json
import argparse
import importlib
from datetime import datetime

# The 24-name watchlist [R] Phase3C_Kickoff_Prompt §2.
TICKERS = ["AAPL", "AG", "AIQ", "CBRS", "CORN", "DOW", "FTI", "GLD",
           "GM", "JPM", "MSFT", "NKE", "NTR", "NVDA", "PM", "PWR",
           "QQQ", "RTX", "SCHD", "SND", "SPY", "VTI", "WMT", "XLU"]

# Accounts mirror the live mix: held names carry real account labels, scouts
# carry the em-dash that normalize_account maps to "Scout".
# NOTE (2026-09-17): TICKERS/HELD are a FIXED SYNTHETIC FIXTURE, not a copy of
# the live watchlist. The audit tests how the four parsers read a log line, and
# its row-count assertions are written against this fixture. The live cohort
# size is checked where it belongs: signal_scan's membership check and
# log_tracker_crosscheck's derived count.
HELD = {"AAPL", "AG", "CBRS", "DOW", "FTI", "GM", "JPM", "MSFT", "NKE",
        "NTR", "NVDA", "PM", "PWR", "RTX", "SND", "WMT"}
ACCOUNTS = ["Roth IRA", "Individual", "Roth IRA,Individual"]

PHASE = "3-C"


def _live_eras():
    """(control, treatment) era labels, READ from main.py's source.

    2026-09-17 (repo remediation R7a): these were pinned at A-S1D1-B1 /
    A-S1D1-B1-E1 and went stale when the H1 window fix moved the generator to
    D2 (applied 2026-08-31, first D2 cohort 2026-09-01). The audit was then
    proving the parsers tolerate an era the generator no longer emits. Same
    defect class as the hardcoded `expected 24`, same fix: derive, don't
    restate. The source is parsed as text rather than imported, so the audit
    carries no import side effects (main.py pulls in the broker and model
    clients, and EDGAR when EQUITY_EDGAR=1).
    """
    import os
    import re
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    try:
        with open(path, encoding="utf-8") as fh:
            m = re.search(r'^PROMPT_VARIANT\s*=\s*"([^"]+)"\s+if\s+EDGAR_ENABLED\s+'
                          r'else\s+"([^"]+)"', fh.read(), re.M)
        if m:
            return m.group(2), m.group(1)
    except OSError:
        pass
    raise SystemExit("edgar_parser_audit: could not read PROMPT_VARIANT from main.py "
                     "- refusing to audit against a guessed era label (exit 2)")


ERA_CONTROL, ERA_TREATMENT = _live_eras()     # e.g. A-S1D2-B1, A-S1D2-B1-E1

# Names that receive an EDGAR section. CBRS is excluded by DP-3; the ETFs and
# commodity trusts are left to render "E[no filings]" so the audit also covers
# the empty-tag path, which is what ~⅓ of the watchlist will emit every day.
EDGAR_NAMES = sorted(HELD - {"CBRS"})


def _conf(i):
    """Deterministic per-ticker confidence. The point of the control/treatment
    pair is that this value must be IDENTICAL in both logs — the E tag is a
    log-line addition and must not perturb any parsed field."""
    return 38 + (i * 7) % 30


def build_line(i, ticker, era, with_e_tag,
               signal="HOLD", risk="APPROVED", reason="Within band",
               risk_flags=None):
    held = ticker in HELD
    account = ACCOUNTS[i % len(ACCOUNTS)] if held else "\u2014"
    conf = _conf(i)
    dq = ["HIGH", "HIGH", "HIGH", "MEDIUM"][i % 4]
    price = round(20 + i * 7.3125, 4)

    payload = {
        "ticker": ticker,
        "signal": signal,
        "confidence": conf,
        "confidence_raw": conf,
        "confidence_blend": conf,
        "data_quality": dq,
        "reasoning": "Within band; no directional edge {braces} and \"quotes\".",
        "risk_flags": list(risk_flags or []),
        "lastPrice": price,
        "sector_score": 0.0,
        "regime_score": -0.061,
        "prompt_variant": era,
        "model": "claude-opus-5",
    }

    tags = (f"H1[trail5d={-1.2 - i * 0.1:+.2f}%; closes=10.00>10.10] | "
            f"S1[prior={conf + 3},{conf}; dconf=-3] | "
            f"D[raw={conf}; op={conf}; trail={-1.2 - i * 0.1:+.2f}%; damp=0] | "
            f"B[sec=0.0; reg=-0.061; w=0.15/0.15; base={conf}; "
            f"blend={conf}; blend_op={conf}]")

    if with_e_tag:
        if ticker in EDGAR_NAMES:
            # DP-3C-g (ruled 2026-08-02): the E tag now also carries the
            # XBRL statement count and period. The tag GREW after the first
            # audit run, so it is re-audited rather than assumed — a longer
            # trailing tag is exactly the shape that has broken parsers twice.
            #
            # DP-3C-i (2026-08-03): 8k= and form4= now carry an @date for the
            # most recent filing of each type — omitted when the count is
            # zero, exactly as edgar_tag() itself omits it. DP-3C-j
            # (2026-08-03): fin= is now ALWAYS one of fin=N@period /
            # fin=degraded / fin=none, never silently absent — the synthetic
            # log below cycles through all three so this audit actually
            # exercises the amendment instead of only ever synthesizing the
            # happy path.
            eightk_n = i % 3
            eightk_part = f"8k={eightk_n}"
            if eightk_n:
                eightk_part += f"@2026-08-{1 + i % 9:02d}"

            buys, sells = i % 4, i % 2
            form4_part = f"form4=+{buys}/-{sells}"
            if buys or sells:
                form4_part += f"@2026-08-{1 + (i + 3) % 9:02d}"

            periodic_part = f"periodic=10-Q@2026-05-0{1 + i % 9}"

            fin_mode = i % 3
            if fin_mode == 0:
                fin_part = f"fin={8 + i % 4}@2026-06-27"
            elif fin_mode == 1:
                fin_part = "fin=degraded"
            else:
                fin_part = "fin=none"

            tags += f" | E[{eightk_part}; {form4_part}; {periodic_part}; {fin_part}]"
        else:
            tags += " | E[no filings]"

    return (f"2026-08-03 09:30:{i:02d} INFO Signal JSON: {json.dumps(payload)} | "
            f"[PHASE {PHASE} DRY RUN] [{account}] "
            f"[{'HELD' if held else 'SCOUT'}] {ticker} | "
            f"Signal: {signal} | Confidence: {conf}% | Risk: {risk} | "
            f"Reason: {reason} | {tags}\n")


def write_log(path, era, with_e_tag):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"2026-08-03 09:30:00 INFO Claude Equity Bot "
                f"\u2014 Phase {PHASE} \u2014 2026-08-03 09:30:00\n")
        for i, t in enumerate(TICKERS):
            f.write(build_line(i, t, era, with_e_tag))
    return path


# =============================================================================
# D-7 -- THE APPROVAL PATH THE PARSERS HAVE NEVER SEEN
# =============================================================================
# Every one of the 1,363 rows in the record was REJECTED or was a HOLD. An
# APPROVED directional signal returns a MULTI-SENTENCE reason from
# risk_engine.evaluate_signal L224-228, and that reason is interpolated into
# the log line at main.py L408, directly UPSTREAM of the H1/S1/D/B/E tags:
#
#   ... | Risk: APPROVED | Reason: <multi-sentence> | H1[...] | S1[...] | ...
#
# So a reason containing an unexpected character does not merely garble the
# reason field -- it sits between the header and every tag the harnesses read.
# This is the same defect class as the three hardcoded-phase-token breaks:
# a line shape that has never occurred, arriving for the first time in a
# canonical cohort.
#
# BINDING (D-7): this must pass BEFORE CHECK 6 is touched, because D-3 is
# precisely the change that makes directional approvals possible for the
# first time.
#
# The reason text is reproduced VERBATIM from risk_engine L224-228 rather
# than paraphrased; a fixture that approximates the string under test proves
# nothing about the string that ships.
# UPDATED 2026-08-11 for D-1/D-2: evaluate_signal_per_account() now appends a
# PER-ACCOUNT split to the reason, so the reason that SHIPS is longer than
# risk_engine's base text. The fixture tracks the shipped string; a fixture
# that approximates the string under test proves nothing about the string
# that ships, which is the note this block already carried and which the
# per-account change would otherwise have quietly falsified.
APPROVAL_REASON = (
    "PENDING HUMAN APPROVAL \u2014 Signal passed all automated checks. "
    "Action: {sig} {ticker} at {stated}% confidence. "
    "Review and approve manually before executing. "
    "PER-ACCOUNT: Roth IRA=APPROVED; Individual=REJECTED; Scout=APPROVED. "
    "NOT actionable in Individual: Too many open positions: 16 >= max 8."
)

# The tickers that carry an approved directional row in the D-7 log. RTX is a
# BUY and GM a SELL: the SELL matters because D-3 exists precisely to stop
# CHECK 6 rejecting SELLs on position count, so a SELL is the FIRST approval
# the change will produce in practice.
APPROVED_ROWS = {"RTX": "BUY", "GM": "SELL"}

# The reason states a confidence DELIBERATELY DIFFERENT from the header's.
# In production the two are identical, which is exactly why a parser reading
# the wrong one would be invisible forever. Making them differ in the fixture
# is the only way the assertion can discriminate.
STATED_CONF_IN_REASON = 99

# DP-3C-o (iii), ruled 2026-08-11: CHECK 6 no longer rejects, it records a
# flag. So `risk_flags` -- empty in all 1,363 rows of the record -- becomes
# POPULATED for the first time, and it is populated with a string containing
# commas, parentheses and a colon, inside the JSON payload that every parser
# json.loads(). A new JSON shape is the same defect class as a new line
# shape; it is fixtured here rather than discovered in a cohort.
CHECK6_FLAG = ["RISK-ENGINE: 16 open positions at or above the monitoring "
               "cap of 8 (CHECK 6, non-blocking per DP-3C-o)"]


def write_approval_log(path, era):
    """A 24-row log in which two rows are APPROVED directional signals."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"2026-08-03 09:30:00 INFO Claude Equity Bot "
                f"\u2014 Phase {PHASE} \u2014 2026-08-03 09:30:00\n")
        for i, t in enumerate(TICKERS):
            if t in APPROVED_ROWS:
                sig = APPROVED_ROWS[t]
                f.write(build_line(
                    i, t, era, with_e_tag=True, signal=sig, risk="APPROVED",
                    reason=APPROVAL_REASON.format(
                        sig=sig, ticker=t, stated=STATED_CONF_IN_REASON),
                    risk_flags=(CHECK6_FLAG if sig == "BUY" else None)))
            else:
                f.write(build_line(i, t, era, with_e_tag=True))
    return path


class Audit:
    def __init__(self):
        self.fails = []

    def check(self, name, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"         got:  {got!r}")
            print(f"         want: {want!r}")
            self.fails.append(name)
        return ok


def main():
    ap = argparse.ArgumentParser(
        description="E3 pre-deploy parser audit for Phase 3-C EDGAR. "
                    "Advisory-only; no orders; not financial advice.")
    ap.add_argument("--keep", action="store_true",
                    help="leave the synthetic logs on disk for inspection")
    ap.add_argument("--dir", default="logs",
                    help="where to write the synthetic logs (default: logs)")
    args = ap.parse_args()

    print("=" * 72)
    print("  E3 PRE-DEPLOY PARSER AUDIT — Phase 3-C EDGAR")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    try:
        analyze_log = importlib.import_module("analyze_log")
        p2t = importlib.import_module("parse_log_to_tracker")
        signal_scan = importlib.import_module("signal_scan")
        ltc = importlib.import_module("log_tracker_crosscheck")
    except ImportError as e:
        print(f"\nHARNESS ERROR: could not import a parser module ({e}).")
        print("Run this from the project root with the venv active.")
        return 2

    os.makedirs(args.dir, exist_ok=True)
    ctl = write_log(os.path.join(args.dir, "signals_2026-08-03_AUDIT_CONTROL.log"),
                    ERA_CONTROL, with_e_tag=False)
    trt = write_log(os.path.join(args.dir, "signals_2026-08-03_AUDIT_TREATMENT.log"),
                    ERA_TREATMENT, with_e_tag=True)

    a = Audit()
    n = len(TICKERS)

    print(f"\nSynthesised {n} rows, phase [{PHASE}], era {ERA_TREATMENT}, "
          f"{len(EDGAR_NAMES)} with an E[...] payload / "
          f"{n - len(EDGAR_NAMES)} 'E[no filings]'.")

    # --- 1 / 2. Both parsers see all 24 rows --------------------------------
    print("\n[1] analyze_log.parse_log — treatment log")
    al_t = analyze_log.parse_log(trt)
    a.check("signal count", len(al_t), n)

    print("[2] parse_log_to_tracker.parse_log_file — treatment log")
    p2t_t = p2t.parse_log_file(trt)
    a.check("row count", len(p2t_t), n)

    # --- 3. Accounts are real ------------------------------------------------
    print("[3] accounts resolve (the 2026-07-07 ACCOUNT_RE failure class)")
    unknown = [r["Ticker"] for r in p2t_t if r["Account"] == "Unknown"]
    a.check("rows with Account='Unknown'", unknown, [])
    a.check("distinct accounts", sorted({r["Account"] for r in p2t_t}),
            sorted(set(ACCOUNTS) | {"Scout"}))

    # --- 4. The E tag perturbs NOTHING --------------------------------------
    print("[4] base operative confidence unchanged by the E[...] tag")
    al_c = analyze_log.parse_log(ctl)
    p2t_c = p2t.parse_log_file(ctl)
    a.check("control signal count", len(al_c), n)

    def key(rows, fields):
        return {r["Ticker"]: tuple(r[f] for f in fields) for r in rows}

    fields = ["Signal", "Conf %", "Data Quality", "Price at Signal", "Account"]
    a.check("tracker rows byte-identical control vs treatment",
            key(p2t_c, fields), key(p2t_t, fields))

    def conf_of(rows):
        out = {}
        for s in rows:
            t = s.get("ticker") or s.get("Ticker")
            c = s.get("confidence", s.get("Conf %"))
            if t is not None:
                out[t] = c
        return out
    a.check("analyze_log confidences identical control vs treatment",
            conf_of(al_c), conf_of(al_t))

    # --- 5. Era label does not trip the variant-B skip ----------------------
    print(f"[5] era label {ERA_TREATMENT} vs the variant-'B' skip")
    a.check("treatment rows survive the skip", len(p2t_t), n)
    a.check("a bare 'B' would still be skipped",
            len(p2t.parse_log_file(
                write_log(os.path.join(args.dir, "signals_2026-08-03_AUDIT_BARE_B.log"),
                          "B", with_e_tag=True))), 0)

    # --- 6. No E-tag leakage into parsed fields ------------------------------
    print("[6] E[...] confined to the reason text")
    leaked = []
    for r in p2t_t:
        for f in ("Ticker", "Account", "Signal", "Data Quality"):
            if "E[" in str(r[f]):
                leaked.append((r["Ticker"], f))
    a.check("E[ in a tracker field", leaked, [])

    tickers_ok = sorted(r["Ticker"] for r in p2t_t)
    a.check("all 24 tickers present", tickers_ok, sorted(TICKERS))

    # --- 7. signal_scan.py — the third E[...] consumer, added 2026-08-10 ----
    print("[7] signal_scan.parse_log — treatment log (third parser added to this audit)")
    ss_t, ss_t_warn = signal_scan.parse_log(trt)
    a.check("signal_scan row count", len(ss_t), n)

    ss_by_ticker = {r["ticker"]: r for r in ss_t}
    missing_edgar = sorted(t for t in TICKERS if ss_by_ticker.get(t, {}).get("edgar") is None)
    a.check("signal_scan: E tag present on every row", missing_edgar, [])

    no_filings_seen = sorted(t for t in TICKERS if t not in EDGAR_NAMES
                              and ss_by_ticker.get(t, {}).get("edgar") == "no filings")
    a.check("signal_scan: 'no filings' lands on exactly the non-EDGAR names",
            no_filings_seen, sorted(set(TICKERS) - set(EDGAR_NAMES)))

    covered_wrong = sorted(t for t in EDGAR_NAMES
                            if ss_by_ticker.get(t, {}).get("edgar") == "no filings")
    a.check("signal_scan: EDGAR-covered names never read 'no filings'",
            covered_wrong, [])

    # DP-3C-j: signal_scan treats E[...] as an opaque blob today (E_RE captures
    # the whole payload, no field-level fin= parsing), so it cannot itself be
    # broken by which fin= state is present. What CAN silently regress is the
    # synthetic log only ever exercising the happy path. Assert the fixture
    # itself carries all three states, so a future signal_scan change that
    # DOES start parsing fin= inherits fixtures for all three from day one.
    edgar_blobs = [ss_by_ticker.get(t, {}).get("edgar") or "" for t in EDGAR_NAMES]
    fin_n_seen = any(re.search(r"fin=\d+@", b) for b in edgar_blobs)
    fin_degraded_seen = any("fin=degraded" in b for b in edgar_blobs)
    fin_none_seen = any("fin=none" in b for b in edgar_blobs)
    a.check("synthetic log exercises fin=N@period / fin=degraded / fin=none",
            (fin_n_seen, fin_degraded_seen, fin_none_seen), (True, True, True))

    # Control log carries no E[...] tag at all. signal_scan must read that as
    # ABSENT (edgar is None on every row), not as a degenerate run where every
    # row happens to read "no filings" — run_integrity() branches on exactly
    # this distinction (pre-EDGAR run vs. EDGAR run that fetched nothing).
    ss_c, ss_c_warn = signal_scan.parse_log(ctl)
    a.check("signal_scan control row count", len(ss_c), n)
    ctl_tagged = sorted(r["ticker"] for r in ss_c if r.get("edgar") is not None)
    a.check("signal_scan: control log (no E tag) carries no edgar field on any row",
            ctl_tagged, [])

    # --- 8. D-7: the APPROVAL PATH, which no parser has ever seen -----------
    print("[8] D-7 -- APPROVED directional rows with the multi-sentence "
          "PENDING HUMAN APPROVAL reason")
    apr = write_approval_log(
        os.path.join(args.dir, "signals_2026-08-03_AUDIT_APPROVED.log"),
        ERA_TREATMENT)

    al_a = analyze_log.parse_log(apr)
    a.check("analyze_log still sees all 24 rows", len(al_a), n)
    p2t_a = p2t.parse_log_file(apr)
    a.check("parse_log_to_tracker still sees all 24 rows", len(p2t_a), n)
    ss_a, _w = signal_scan.parse_log(apr)
    a.check("signal_scan still sees all 24 rows", len(ss_a), n)

    a.check("accounts survive the multi-sentence reason",
            [r["Ticker"] for r in p2t_a if r["Account"] == "Unknown"], [])

    by_t = {r["Ticker"]: r for r in p2t_a}
    for tkr, sig in sorted(APPROVED_ROWS.items()):
        a.check(f"{tkr} parses as {sig}, not HOLD", by_t[tkr]["Signal"], sig)

    # The discriminating assertion. The reason says "at 99% confidence" while
    # the header says the row's real confidence. A parser that reads the
    # reason instead of the header returns 99 -- and in production, where the
    # two agree, that error would never surface.
    # UNITS DIFFER BY DESIGN, recorded here because the first draft of this
    # assertion got it wrong: parse_log_to_tracker stores Conf % as a
    # FRACTION (0.64) to drive Excel percentage formatting -- the master
    # tracker's own Signals sheet carries 0.62 for WMT -- while signal_scan
    # keeps an integer percent (64). Both are correct in their own units and
    # the assertion checks each in its own.
    ss_by_t = {r["ticker"]: r for r in ss_a}
    for tkr in sorted(APPROVED_ROWS):
        idx = TICKERS.index(tkr)
        a.check(f"{tkr} confidence read from the HEADER, not from the reason "
                f"text ({STATED_CONF_IN_REASON}%)",
                (by_t[tkr]["Conf %"], ss_by_t[tkr]["conf"]),
                (_conf(idx) / 100.0, _conf(idx)))
        # Stated separately and positively: whatever the units, the value the
        # reason text advertises must NOT be what either parser returned.
        a.check(f"{tkr}: neither parser picked up the reason's "
                f"{STATED_CONF_IN_REASON}%",
                (by_t[tkr]["Conf %"] == STATED_CONF_IN_REASON / 100.0,
                 ss_by_t[tkr]["conf"] == STATED_CONF_IN_REASON),
                (False, False))

    # The reason sits UPSTREAM of every tag. If it disturbs the delimiters,
    # the D/B/E tags are lost -- silently, because a missing tag reads as an
    # absent feature rather than as a parse failure.
    for tkr in sorted(APPROVED_ROWS):
        idx = TICKERS.index(tkr)
        rec = ss_by_t[tkr]
        a.check(f"{tkr}: D/B tags still parse downstream of the reason",
                (rec["raw"], rec["op"], rec["base"], rec["blend"]),
                (_conf(idx), _conf(idx), _conf(idx), _conf(idx)))
        a.check(f"{tkr}: E tag still parses downstream of the reason",
                rec["edgar"] is not None, True)

    leaked_a = []
    for r in p2t_a:
        for f_ in ("Ticker", "Account", "Signal", "Data Quality"):
            v = str(r[f_])
            if "PENDING" in v or "APPROVAL" in v or "Review and approve" in v:
                leaked_a.append((r["Ticker"], f_))
    a.check("the approval reason does not leak into a tracker field",
            leaked_a, [])

    a.check("populated risk_flags survives json.loads on every parser",
            [r["ticker"] for r in ss_a if r["ticker"] == "RTX"], ["RTX"])
    a.check("a populated risk_flags does not leak into a tracker field",
            [(r["Ticker"], f_) for r in p2t_a
             for f_ in ("Ticker", "Account", "Signal", "Data Quality")
             if "RISK-ENGINE" in str(r[f_])], [])

    # main.py joins log-line fields with " | ". A reason containing that
    # delimiter would truncate every downstream capture at the wrong point.
    # The per-account reason is BUILT by risk_engine, so this is a live
    # invariant, not a fixture property.
    a.check("no synthesised reason contains the ' | ' field delimiter",
            [t for t in APPROVED_ROWS
             if " | " in APPROVAL_REASON.format(
                 sig=APPROVED_ROWS[t], ticker=t,
                 stated=STATED_CONF_IN_REASON)], [])

    a.check("HOLD rows in the same log are unaffected",
            sorted(r["Ticker"] for r in p2t_a if r["Signal"] == "HOLD"),
            sorted(t for t in TICKERS if t not in APPROVED_ROWS))

    # --- 8. log_tracker_crosscheck.py — the FOURTH log reader --------------
    print("[9] log_tracker_crosscheck.parse_log — fourth parser in this audit")
    ltc_t, _d, _sh, ltc_phase = ltc.parse_log(trt)
    a.check("log_tracker_crosscheck row count", len(ltc_t), n)
    a.check("log_tracker_crosscheck: all 24 tickers present",
            sorted(ltc_t), sorted(TICKERS))
    a.check("log_tracker_crosscheck: phase token CAPTURED from the log, not assumed",
            ltc_phase, [f"PHASE {PHASE} DRY RUN"])
    ltc_c, _d, _sh, _p = ltc.parse_log(ctl)
    a.check("log_tracker_crosscheck control row count", len(ltc_c), n)
    ltc_a, _d, _sh, _p = ltc.parse_log(apr)
    a.check("log_tracker_crosscheck survives the approval reason", len(ltc_a), n)

    # THE CHECK THAT PREVENTS RECURRENCE. Asserting the parser handles the
    # CURRENT token proves only what was already true on 8/11. Rewrite the
    # log with a token this project has never emitted and require it to
    # still read 24 rows, and to REPORT the unseen token rather than
    # silently returning nothing — which is how the 8/12 break presented.
    fut = os.path.join(args.dir, "signals_2026-08-03_AUDIT_FUTUREPHASE.log")
    with open(trt, encoding="utf-8") as fh:
        mutated = fh.read().replace(f"[PHASE {PHASE} DRY RUN]", "[PHASE 9-Z DRY RUN X]")
    with open(fut, "w", encoding="utf-8") as fh:
        fh.write(mutated)
    ltc_f, _d, _sh, ltc_fphase = ltc.parse_log(fut)
    a.check("log_tracker_crosscheck is PHASE-AGNOSTIC (unseen token still parses)",
            len(ltc_f), n)
    a.check("log_tracker_crosscheck reports the unseen token rather than hiding it",
            ltc_fphase, ["PHASE 9-Z DRY RUN X"])

    if not args.keep:
        for p in (ctl, trt, apr, fut,
                  os.path.join(args.dir, "signals_2026-08-03_AUDIT_BARE_B.log")):
            try:
                os.remove(p)
            except OSError:
                pass
        print("\n(synthetic logs removed; --keep retains them)")
    else:
        print(f"\n(synthetic logs retained in {args.dir}\\)")

    print("\n" + "=" * 72)
    if a.fails:
        print(f"  E3 PARSER AUDIT: FAILED — {len(a.fails)} check(s)")
        for f in a.fails:
            print(f"    - {f}")
        print("  DO NOT DEPLOY. Fix the parser, then re-run this audit.")
        print("=" * 72)
        return 1

    print("  E3 PARSER AUDIT: PASSED")
    print("  All four parsers (analyze_log, parse_log_to_tracker, signal_scan,")
    print("  log_tracker_crosscheck) tolerate the 3-C phase token, the")
    print(f"  {ERA_TREATMENT} era label (read from main.py) and the")
    print("  amended (DP-3C-i/j) trailing E[...] tag, and none perturbs a")
    print("  single parsed field. This criterion no longer blocks go-live.")
    print("  STILL REQUIRED: the coverage run (SEC fetch path) and E4")
    print("  pre-registration. This audit says nothing about either.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
