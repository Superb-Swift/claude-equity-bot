#!/usr/bin/env python3
"""value_anchor.py — the first PRICE-REFERENCED number in the project.

WHAT IT COMPUTES, AND NOTHING MORE
    Per covered name, from filings and price only:

        book equity per share  = book equity / implied shares
        M/B                    = price / book value per share
        MVA (dollars)          = market cap - book equity        [packet p.1067]
        MVA / book equity      = M/B - 1                         [identity]

    THAT IS THE WHOLE OUTPUT. There is no discounted cash flow here, no
    horizon value, no growth rate, no discount rate, and no price target.
    Every number above is forecast-free: it contains no assumption about the
    future at all. That is the entire point.

WHY THIS AND NOT A DCF
    A DCF on this data would be ~77% terminal value and would move ~13% on
    100bp of a growth rate nobody can observe. It would be the most
    confidently-stated and least defensible figure in the system, in a
    codebase carrying twelve-plus "tool reported a value it did not compute"
    findings. M/B assumes nothing, so it cannot be wrong in that way. It is
    also the input the inverted value-driver identity needs later:

        MVA / OpCap = ((1+g)*ROIC - WACC) / (WACC - g)

    so measuring the left-hand side now, honestly, is the prerequisite for
    ever solving the right-hand side. This tool deliberately stops at the
    left-hand side.

WHAT IT DOES NOT DO
    Not a valuation. Not a signal. Not an input to any gate. Does not touch
    the prompt, edgar_client.py, any E4 endpoint, arm, threshold, n or rate,
    KEEP-70, H4, or the +/-3% band. Reads and prints. Writes nothing unless
    --md is passed.

HOW IT KNOWS WHICH FILING BELONGS TO WHICH TICKER
    The derived cache is keyed on ACCESSION (fin_<accession>.json) and carries
    no ticker. The join is therefore made twice and both must agree:

      (1) FILENAME EVIDENCE. Sibling raw documents in edgar_cache are named
          <accession>_<doc>, and <doc> usually opens with the ticker
          (gm-20260630.htm, gld20260630_10q.htm). The first alphabetic run is
          matched for EXACT equality against the watchlist -- not prefix
          equality, so sndk- does not match SND.

      (2) LOG EVIDENCE. The session log's E[...] tag carries fin=<N>@<date>
          per ticker. The cache file's line count and anchor date must match.

    A name is reported ONLY if both agree. Filename-only, tag-only and
    conflicting joins are all reported as UNVERIFIED and are NOT used.
    This matters: CORN's periodic is filed by Teucrium Commodity Trust as one
    document covering several series, so the raw file is named for a different
    series and CORN does not join. The correct behaviour is to say so.

HOUSE RULES OBSERVED
    * Reads the MASTER; hard-refuses the report copies and exits 2.
    * Writes nothing. Never mutates the master.
    * NO HARDCODED TICKER LIST. The watchlist is derived from the master's
      most recent cohort, so it cannot drift out of date the way a literal
      would. This is deliberate -- the record carries a hardcoded-expected-
      count defect in signal_scan.py and a hardcoded-phase-token class with
      three instances.
    * NOT COMPUTED with a stated reason, never a substituted near-miss. The
      2026-08-03 finding that DOW reported "(no concept tagged; tried
      Liabilities)" rather than substituting is the standard being followed.
    * Exits 1 on findings for future hook use.

DEPENDENCY WARNING, STATED PLAINLY
    edgar_cache\\ is GITIGNORED, DELETABLE AND RE-FETCHABLE. This tool reads
    it. If the cache is cleared, this tool reports NOT COMPUTED for every
    name until the next run repopulates it. It never fetches. That is a real
    fragility and it is the reason this tool is separate from band_price.py,
    which depends on the master alone.

USAGE
    python value_anchor.py
    python value_anchor.py --log logs\\signals_2026-08-17.log
    python value_anchor.py --selftest

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

REFUSED_INPUTS = ("tracker_with_registry.xlsx", "actionable_registry.xlsx",
                  "near_miss_registry.xlsx")
DEFAULT_TRACKER = os.path.join("logs", "claude_equity_bot_tracker.xlsx")
DEFAULT_CACHE = "edgar_cache"

# Labels as emitted by edgar_client.FINANCIAL_CONCEPTS. Read from source
# 2026-08-17, edgar_client.py L265-285. If that list is relabelled these
# strings must follow; a missing label degrades to NOT COMPUTED with a stated
# reason rather than to a wrong number, so a rename fails loudly.
L_EQUITY = "Shareholders equity"
L_ASSETS = "Total assets"
L_LIABS = "Total liabilities"
L_NI = "Net income"
L_EPS = "Diluted EPS"

# Implied share count sanity window. A US listed issuer outside this range is
# not impossible, it is merely worth a human look -- so this FLAGS, it does
# not reject. Widened deliberately: rejecting on a plausibility prior is how
# a correct outlier gets silently dropped.
SHARES_MIN = 1e6
SHARES_MAX = 5e10

# Balance-sheet identity residual, as a fraction of total assets, above which
# the block is flagged. Assets - Liabilities - Equity should equal exactly the
# noncontrolling interest, which is small for most filers and legitimately
# large for a few. FLAGS, does not reject.
#
# ANALYST NOTE (2026-09-08): the flag is a PERCENTAGE OF ASSETS, but the
#   quantity it tests is an absolute balance-sheet line. PM tripped it on
#   2026-06-30 at 2.82% -- $1.93B of residual against a $68.27B asset base --
#   while GM ($1.64B) and RTX ($1.77B) carry residuals of the same ORDER and
#   pass, purely because their asset bases are two to four times larger. PM is
#   also the one name in the covered set with NEGATIVE book equity, which
#   shrinks the denominator further. A filer that consolidates majority-owned
#   subsidiaries will trip this on arithmetic before it trips on error.
#
#   The identity's own docstring already says what the residual SHOULD equal:
#   noncontrolling interest. Where the filer tags that concept, comparing
#   against it turns a magnitude heuristic into the identity check this is
#   described as. BS_NCI_TOL is the tolerance for that comparison, as a
#   fraction of assets; the percentage flag below is retained only as the
#   fallback for filers that tag no NCI at all.
BS_RESIDUAL_FLAG = 0.02
BS_NCI_TOL = 0.005

# Fund-like instruments: passive funds and commodity trusts, which have no
# earnings in the corporate sense and whose market-to-book is ~1.0 BY
# CONSTRUCTION because the trust IS its net asset value. Excluded from the
# VALUATION LAYER ONLY (DP-3C-k) -- untouched in the signal pipeline, the
# accuracy series, KEEP-70, H4 and E4.
#
# Membership is EVIDENCED, never inferred from a name looking fund-shaped.
# Each entry carries the observation that puts it here.
FUND_LIKE = {
    "CORN": ("Teucrium Corn Fund -- commodity trust; periodic filed for the "
             "Teucrium trust and cached under a `tags*` document name "
             "(tags20260630_10q.htm). Quote payload flags [ETF], no eps."),
    "GLD":  ("SPDR Gold Trust -- grantor trust holding bullion. Quote payload "
             "flags [ETF]; no Diluted EPS in the filing."),
    "USO":  ("United States Oil Fund -- commodity pool. Quote payload flags "
             "[ETF]; no Diluted EPS in the filing."),
}


# =============================================================================
# JOIN: accession -> ticker
# =============================================================================

def first_alpha_run(s: str) -> str:
    m = re.match(r"[^A-Za-z]*([A-Za-z]+)", s)
    return m.group(1).lower() if m else ""


def filename_join(cache_dir: str, watchlist):
    """accession -> ticker, from sibling raw document filenames.

    EXACT equality on the first alphabetic run, never prefix equality.
    'sndk-20260403.htm' yields 'sndk', which is not SND. Prefix matching here
    would silently attribute SanDisk's filing to Smart Sand.
    """
    wl = {t.lower(): t for t in watchlist}
    cand = {}
    for path in glob.glob(os.path.join(cache_dir, "*")):
        base = os.path.basename(path)
        if base.startswith("fin_"):
            continue
        if "_" not in base:
            continue
        acc, rest = base.split("_", 1)
        if not acc.isdigit():
            continue
        tok = first_alpha_run(rest)
        if tok in wl:
            cand.setdefault(acc, set()).add(wl[tok])
    return {acc: next(iter(s)) for acc, s in cand.items() if len(s) == 1}, \
           {acc: s for acc, s in cand.items() if len(s) > 1}


E_TAG = re.compile(r"E\[(?P<body>[^\]]*)\]")
SIG_TICKER = re.compile(r'Signal JSON:\s*\{.*?"ticker"\s*:\s*"([A-Z.\-]+)"')


def parse_log_tags(log_path: str):
    """ticker -> {fin_lines, fin_anchor, degraded, periodic}

    The E[...] tag sits AFTER the Signal JSON on the same log line, so the
    ticker and the tag are read from one line and cannot be mis-paired. An
    earlier attempt at this paired the tag with the nearest preceding ticker
    mention and produced nothing usable; recorded so the approach is not
    retried.
    """
    out = {}
    if not log_path or not os.path.exists(log_path):
        return out
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            mt = SIG_TICKER.search(line)
            me = E_TAG.search(line)
            if not mt or not me:
                continue
            tk = mt.group(1)
            body = me.group("body")
            rec = {"raw": body, "degraded": "fin=degraded" in body,
                   "fin_lines": None, "fin_anchor": None, "periodic": None}
            mf = re.search(r"fin=(\d+)@(\d{4}-\d{2}-\d{2})", body)
            if mf:
                rec["fin_lines"] = int(mf.group(1))
                rec["fin_anchor"] = mf.group(2)
            mp = re.search(r"periodic=([^;\]]+)", body)
            if mp:
                rec["periodic"] = mp.group(1).strip()
            out[tk] = rec
    return out


# =============================================================================
# THE NUMBERS
# =============================================================================

def _check_candidate(fin, tag):
    """(ok, reason) for ONE accession against the ticker's E[...] tag."""
    n_lines = len(fin.get("lines", []))
    anchor = fin.get("period")
    if tag is None:
        return False, "ticker has no E[...] tag in the supplied log"
    if tag["degraded"]:
        return False, ("tag reads fin=degraded (DP-3C-t(b)); treatment not "
                       "received, cache may be stale")
    if tag["fin_lines"] is None:
        return False, f"tag carries no fin=N@date ({tag['raw'][:40]})"
    if tag["fin_lines"] != n_lines or tag["fin_anchor"] != anchor:
        return False, (f"tag says fin={tag['fin_lines']}@{tag['fin_anchor']}, "
                       f"cache has {n_lines}@{anchor}")
    return True, None


def candidates_by_ticker(fins, fn_map):
    """ticker -> [(accession, fin), ...], sorted oldest period first."""
    by_tk = {}
    for acc, fin in fins.items():
        tk = fn_map.get(acc)
        if tk is None:
            continue                     # not a watchlist name at all; silent
        by_tk.setdefault(tk, []).append((acc, fin))
    for tk in by_tk:
        by_tk[tk].sort(key=lambda c: ((c[1].get("period") or ""), c[0]))
    return by_tk


def verified_join(fins, fn_map, tags):
    """(verified, unverified) — a cache file is used ONLY when the filename
    route and the log-tag route agree on line count and anchor date.

    RESOLVES PER TICKER, NOT PER ACCESSION. edgar_cache accumulates every
    filing it has ever fetched, so a ticker routinely has SEVERAL accessions
    -- GLD carries both its 2026-03-31 and 2026-06-30 10-Qs, JPM likewise.
    Both map to the same ticker.

    DEFECT FIXED 2026-08-17, found on the operator's real cache and NOT
    reproducible on the 17-file subset used to develop this: the previous
    version wrote `verified[tk]` and `unverified[tk]` while looping over
    accessions, so a ticker with one matching and one stale accession landed
    in BOTH dicts and the last write won. Section 0 reported GLD and JPM as
    "UNVERIFIED (not used)" while section 1 went on to use them -- a tool
    reporting a state it did not act on, which is the defect class this
    record already carries twelve-plus instances of.

    Now: every candidate is checked, a ticker is VERIFIED if ANY candidate
    verifies (the latest such period wins, deterministically), and it appears
    in `unverified` only when NO candidate verifies.
    """
    verified, unverified = {}, {}
    for tk, cands in candidates_by_ticker(fins, fn_map).items():
        tag = tags.get(tk)
        ok_list, fail_list = [], []
        for acc, fin in cands:
            ok, why = _check_candidate(fin, tag)
            (ok_list if ok else fail_list).append((acc, fin, why))
        if ok_list:
            acc, fin, _ = ok_list[-1]        # latest verifying period
            verified[tk] = (acc, fin)
        elif fail_list:
            acc, _fin, why = fail_list[-1]   # newest failure carries the reason
            extra = (f" ({len(fail_list)} cached accessions, none matching)"
                     if len(fail_list) > 1 else "")
            unverified[tk] = (acc, why + extra)
    return verified, unverified


def load_fins(cache_dir):
    """accession -> parsed fin_*.json. Returns (fins, errors)."""
    fins, errors = {}, []
    for p in sorted(glob.glob(os.path.join(cache_dir, "fin_*.json"))):
        acc = os.path.basename(p)[4:-5]
        try:
            with open(p, encoding="utf-8") as fh:
                fins[acc] = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"unreadable cache file {os.path.basename(p)}: {e}")
    return fins, errors


def line_map(fin):
    return {ln["label"]: ln for ln in fin.get("lines", [])}


def book_equity(fin):
    """Returns (value, source, note). Prefers the tagged equity line; falls
    back to Assets - Liabilities, which INCLUDES noncontrolling interest and
    is therefore labelled as a different quantity, not silently equated."""
    lm = line_map(fin)
    if L_EQUITY in lm:
        return lm[L_EQUITY]["value"], "StockholdersEquity", None
    if L_ASSETS in lm and L_LIABS in lm:
        return (lm[L_ASSETS]["value"] - lm[L_LIABS]["value"],
                "Assets-Liabilities",
                "includes noncontrolling interest; not common equity")
    return None, None, "no equity line and cannot derive (needs Assets and Liabilities)"


def implied_shares(fin):
    """Net income / Diluted EPS, ONLY when both report the same period.

    The period check is not decoration. A 10-Q can tag net income for the
    quarter and cash flow for six months in the same accession -- that is the
    N-1 defect the 2026-08-03 fix addressed, and period_note is where the
    result of that fix is recorded. Dividing a six-month numerator by a
    quarterly denominator would double the share count and halve M/B.
    """
    lm = line_map(fin)
    if L_NI not in lm or L_EPS not in lm:
        missing = [x for x in (L_NI, L_EPS) if x not in lm]
        return None, f"missing {' and '.join(missing)}"
    ni, eps = lm[L_NI], lm[L_EPS]
    if ni.get("period_note") != eps.get("period_note"):
        return None, (f"period mismatch: net income [{ni.get('period_note')}] "
                      f"vs EPS [{eps.get('period_note')}]")
    if ni.get("end") != eps.get("end"):
        return None, f"period end mismatch: {ni.get('end')} vs {eps.get('end')}"
    if not eps["value"]:
        return None, "diluted EPS is zero"
    sh = ni["value"] / eps["value"]
    if sh <= 0:
        return None, (f"implied share count is not positive ({sh:,.0f}) -- "
                      f"net income and EPS disagree in sign")
    return sh, None


def bs_residual(fin):
    """Assets - Liabilities - Equity. Should equal noncontrolling interest.

    This is the substitute for DP-3C-q's press-release corroboration, which
    has no analogue for balance-sheet detail: filers rarely restate the
    balance sheet in an 8-K, so an internal identity is the only available
    check. Verified against the record: GM 2026-06-30 residual is $1.641B of
    noncontrolling interest.
    """
    lm = line_map(fin)
    if not all(k in lm for k in (L_ASSETS, L_LIABS, L_EQUITY)):
        return None, None
    a, l, e = lm[L_ASSETS]["value"], lm[L_LIABS]["value"], lm[L_EQUITY]["value"]
    r = a - l - e
    return r, (r / a if a else None)


def bs_nci(fin):
    """The filer's own tagged noncontrolling interest, when it tagged one.

    ANALYST NOTE (2026-09-08): bs_residual's docstring says the residual
    "should equal noncontrolling interest", and then the caller tests it
    against a percentage of ASSETS instead -- which is a magnitude heuristic,
    not the identity. The two disagree exactly where it matters. PM's residual
    is $1.93B against $68.27B of assets (2.82%, FLAGGED) while GM's is $1.64B
    (0.58%, passes) and RTX's $1.77B (1.02%, passes). The three are the same
    order of magnitude; only the denominators differ. PM additionally carries
    NEGATIVE book equity, so its asset base is the smallest of the three
    relative to what it consolidates.

    Where the filer tags NCI, compare against it and the check becomes the
    identity it claims to be. Where it does not, the caller falls back to the
    percentage flag -- unchanged, and now correctly labelled as a fallback.

    Returns (value, label) or (None, None). Never guesses a concept: an
    untagged NCI reads as absent, not as zero, because zero is a claim.
    """
    lm = line_map(fin)
    for key in ("Noncontrolling interest", "Minority interest",
                "MinorityInterest", "Noncontrolling interests"):
        if key in lm and lm[key].get("value") is not None:
            return lm[key]["value"], key
    return None, None


def vq_string(fin):
    """Input completeness, reported per name. Proposed as DP-V4's `vq=` field:
    descriptive only, and DELIBERATELY NOT coupled to `data_quality`, which
    DP-4 keeps independent of filings."""
    lm = line_map(fin)
    have = [k for k in (L_ASSETS, L_LIABS, L_EQUITY, L_NI, L_EPS) if k in lm]
    return f"{len(have)}/5", have


def money(v):
    if v is None:
        return "n/a"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{v/div:,.2f}{suf}"
    return f"{v:,.2f}"


# =============================================================================
# LOAD
# =============================================================================

def load_master(path):
    base = os.path.basename(path).lower()
    for bad in REFUSED_INPUTS:
        if base == bad.lower():
            sys.stderr.write(
                f"REFUSED: {base} is an OUTPUT copy, never an input "
                f"(workflow section 6). Pass the master.\n")
            sys.exit(2)
    if not os.path.exists(path):
        sys.stderr.write(f"REFUSED: master not found at {path}\n")
        sys.exit(2)
    try:
        import openpyxl
    except ImportError:
        sys.stderr.write("REFUSED: openpyxl not installed.\n")
        sys.exit(2)
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if "Signals" not in wb.sheetnames:
        sys.stderr.write("REFUSED: no 'Signals' tab; is this the master?\n")
        sys.exit(2)
    rows = []
    for r in wb["Signals"].iter_rows(min_row=5, values_only=True):
        if r is None or len(r) < 7 or r[0] is None or r[1] is None:
            continue
        try:
            px = float(r[6])
        except (TypeError, ValueError):
            px = None
        rows.append((str(r[0])[:10], str(r[1]).strip(), r[2], px))
    wb.close()
    return rows


def latest_cohort(rows):
    if not rows:
        return None, {}
    d = max(r[0] for r in rows)
    return d, {r[1]: {"px": r[3], "acct": r[2]} for r in rows if r[0] == d}


# =============================================================================
# REPORT
# =============================================================================

def report(tracker, cache_dir, log_path, md_path=None):
    L = []
    def out(s=""):
        L.append(s); print(s)

    findings = []

    rows = load_master(tracker)
    cohort_date, cohort = latest_cohort(rows)
    watchlist = sorted(cohort)

    out("=" * 100)
    out("VALUE ANCHOR -- forecast-free market-vs-book, per covered name")
    out("No DCF. No horizon value. No growth rate. No discount rate. No price target.")
    out("Changes nothing: not a gate, not a signal, not an input to any endpoint.")
    out("=" * 100)
    out(f"master cohort {cohort_date}   watchlist {len(watchlist)} names "
        f"(derived from the master, not hardcoded)")
    out(f"cache {cache_dir}   log {os.path.basename(log_path) if log_path else 'NOT SUPPLIED'}")
    out()

    if not os.path.isdir(cache_dir):
        out(f"NOT COMPUTED for every name: cache directory {cache_dir} absent.")
        out("edgar_cache is gitignored and re-fetchable; run the daily pipeline to repopulate.")
        out("This tool never fetches.")
        # EXIT 2, NOT 1 -- see the matching note in implied_return.py. No cache
        # means nothing was computed, which is a could-not-run state.
        return 2

    fn_map, fn_ambig = filename_join(cache_dir, watchlist)
    tags = parse_log_tags(log_path)

    fins, fin_errors = load_fins(cache_dir)
    findings.extend(fin_errors)

    # ---- the join, reported before any number
    out("-" * 100)
    out("0. THE JOIN -- accession to ticker, by TWO independent routes; both must agree")
    out("-" * 100)
    if not tags:
        out("  LOG NOT SUPPLIED OR CARRIES NO E[...] TAGS.")
        out("  Route 2 unavailable, so every join is FILENAME-ONLY and therefore UNVERIFIED.")
        out("  Nothing is computed. Pass --log logs\\signals_<date>.log.")
        findings.append("no log tags available; joins cannot be verified")
        out()
    verified, unverified = verified_join(fins, fn_map, tags)

    # COUNTS CORRECTED 2026-08-17. The previous line printed len(fn_map) under
    # the label "joined to a watchlist name", but fn_map counts accession ->
    # ticker mappings built from EVERY raw document in the cache, most of which
    # have no fin_*.json at all. On the real cache that read 35 against 18
    # actually joinable caches -- a number that looked like coverage and was not.
    cands = candidates_by_ticker(fins, fn_map)
    n_cand = sum(len(v) for v in cands.values())
    multi = {t: [a for a, _ in v] for t, v in cands.items() if len(v) > 1}
    out(f"  fin caches parsed                 {len(fins)}")
    out(f"  of those, for a watchlist name    {n_cand}  across {len(cands)} tickers")
    out(f"  accession->ticker filename map    {len(fn_map)}  (includes names with "
        f"no fin cache)")
    if multi:
        out(f"  tickers with MORE THAN ONE cached accession: {len(multi)}")
        for t, accs in sorted(multi.items()):
            out(f"     {t:>6} {len(accs)} accessions -- the latest VERIFYING one is used")
    out(f"  VERIFIED by both routes    {len(verified)}   {sorted(verified)}")
    if unverified:
        out(f"  UNVERIFIED (not used)      {len(unverified)}")
        for tk, (acc, why) in sorted(unverified.items()):
            out(f"     {tk:>6}  {why}")
    if fn_ambig:
        out(f"  AMBIGUOUS filenames        {len(fn_ambig)}")
        for acc, s in fn_ambig.items():
            out(f"     {acc}  matches {sorted(s)} -- not used")
        findings.append(f"{len(fn_ambig)} accessions match more than one ticker")
    missing = [t for t in watchlist if t not in verified and t in tags
               and not tags[t]["degraded"] and tags[t]["fin_lines"] is not None]
    # ANALYST NOTE (2026-09-08): CORN has been reported here as an unjoined
    #   cache file since at least 2026-08-27 -- a recurring FINDING implying an
    #   unfixed data defect. It is not one. CORN is the Teucrium Corn Fund, a
    #   commodity trust; its periodic is filed for the trust and cached under a
    #   `tags*` document name (edgar_cache holds tags20260630_10q.htm and
    #   tags20260831_8k.htm), which is exactly the cause the message below
    #   guesses at. But FIXING the join would be the wrong repair: it would
    #   produce a book-value figure for an object that section 6(a) of the
    #   exclusion table already says has none -- "a passive fund or trust has no
    #   earnings in the corporate sense and its market-to-book is ~1.0 BY
    #   CONSTRUCTION". CORN is the same object as GLD and USO and belongs beside
    #   them, not in a defect queue that can never be cleared.
    #
    #   MEMBERSHIP IS EVIDENCED, NOT GUESSED. Each name below is carried with
    #   the observation that puts it here, and the test is the same one already
    #   used for GLD and USO: the instrument is fund-like and reports no EPS.
    #   quote_dump independently flags all three [ETF] with no eps.
    #
    #   SCOPE, per the DP-3C-k precedent stated in section 6(a): this exclusion
    #   binds THE VALUATION LAYER ONLY. CORN stays in the watchlist, the signal
    #   pipeline, the accuracy series, KEEP-70, H4 and E4 with its denominator
    #   untouched. An exclusion scoped to one endpoint must not silently move
    #   another criterion's.
    struct_missing = [t for t in missing if t in FUND_LIKE]
    missing = [t for t in missing if t not in FUND_LIKE]
    if struct_missing:
        out(f"  STRUCTURALLY EXCLUDED, not a join defect: {struct_missing}")
        for t in struct_missing:
            out(f"     {t:>6}  {FUND_LIKE[t]}")
        out("     A passive fund or trust has no earnings in the corporate sense and its")
        out("     market-to-book is ~1.0 BY CONSTRUCTION. Joining the cache file would")
        out("     produce a number, not a valuation. VALUATION LAYER ONLY (DP-3C-k):")
        out("     these names are untouched in the signal pipeline and every criterion.")
    if missing:
        out(f"  covered in the log but NOT joined to a cache file: {missing}")
        out("     Most likely cause: the periodic is filed under a trust or parent whose")
        out("     document name carries a different series ticker. Reported, never guessed.")
        findings.append(f"{len(missing)} covered names have a fin= tag but no joinable cache file")
    out()

    if not verified:
        out("Nothing verified; no numbers reported.")
        # EXIT 2, NOT 1 -- CORRECTED 2026-08-19, and the argument was already
        # written three branches above: "No cache means nothing was computed,
        # which is a could-not-run state." NOTHING VERIFIED IS THE SAME STATE.
        # It returned 1 until today, and 1 is the FINDINGS code, so value.bat
        # set FIND1 instead of FAIL2, did not skip step 4, and closed the pass
        # on "VALUE PASS FINDINGS - Findings are the NORMAL state here, not a
        # failure." On 2026-08-19 that sentence was printed over a pass that
        # computed nothing at all, because the run had no E[...] tags to verify
        # against. Note also that this return fires BEFORE the md_path write at
        # the bottom of report(), so the exhibit is absent -- which is the only
        # signal the operator gets, and it was being labelled normal.
        return 2

    # ---- the numbers
    out("-" * 100)
    out("1. MARKET vs BOOK  (packet p.1067: MVA = market value of stock - total common equity)")
    out("-" * 100)
    out(f"{'tk':>6} {'vq':>5} {'anchor':>11} {'book equity':>13} {'impl shares':>13} "
        f"{'BVPS':>9} {'price':>9} {'M/B':>7} {'MVA':>11} {'MVA/BE':>8}")
    computed, skipped = [], []
    for tk in sorted(verified):
        acc, fin = verified[tk]
        vq, _have = vq_string(fin)
        be, be_src, be_note = book_equity(fin)
        sh, sh_why = implied_shares(fin)
        px = cohort.get(tk, {}).get("px")
        if be is None or sh is None or px is None:
            why = be_note if be is None else (sh_why if sh is None else "no price in cohort")
            skipped.append((tk, vq, why))
            out(f"{tk:>6} {vq:>5} {str(fin.get('period')):>11}   NOT COMPUTED -- {why}")
            continue
        bvps = be / sh
        mcap = px * sh
        mva = mcap - be
        # M/B IS UNDEFINED ON NON-POSITIVE BOOK EQUITY, and so is MVA/BE.
        # Both divide by book equity. A filer whose cumulative buybacks and
        # dividends exceed retained earnings carries NEGATIVE common equity --
        # a legitimate reported state, not a defect and not a bad extraction.
        # Dividing by it produces a large negative number that LOOKS like a
        # valuation and means nothing. MVA IN DOLLARS REMAINS VALID AND IS
        # STILL REPORTED, because it is a subtraction, not a ratio.
        mb = (px / bvps) if be > 0 else None
        computed.append(dict(tk=tk, vq=vq, be=be, be_src=be_src, be_note=be_note,
                             sh=sh, bvps=bvps, px=px, mcap=mcap, mva=mva, mb=mb,
                             anchor=fin.get("period"), fin=fin))
        mb_s = f"{mb:7.2f}" if mb is not None else "  UNDEF"
        rt_s = f"{mb-1:+8.2f}" if mb is not None else "   UNDEF"
        out(f"{tk:>6} {vq:>5} {str(fin.get('period')):>11} {money(be):>13} "
            f"{sh/1e6:12,.1f}M {bvps:9,.2f} {px:9,.2f} "
            f"{mb_s} {money(mva):>11} {rt_s}")
    out()
    neg_be = [c for c in computed if c["be"] <= 0]
    out(f"  computed {len(computed)} of {len(verified)} verified; "
        f"NOT COMPUTED {len(skipped)}; M/B UNDEFINED {len(neg_be)}")
    out("  BVPS = book equity / implied shares.  MVA/BE = M/B - 1 exactly (see --selftest).")
    out("  Negative MVA means the market values the operation BELOW its book capital.")
    if neg_be:
        out()
        out("  M/B UNDEFINED ON NON-POSITIVE BOOK EQUITY:")
        for c in neg_be:
            out(f"     {c['tk']:>6} book equity {money(c['be'])} -- ratio suppressed; "
                f"MVA {money(c['mva'])} still valid")
        out("     Cumulative buybacks and dividends exceeding retained earnings produce")
        out("     negative common equity. That is a REPORTED STATE, not a defect and not a")
        out("     bad extraction -- the balance-sheet identity below still holds for these")
        out("     names. But M/B and MVA/BE both divide by it, so both are suppressed rather")
        out("     than printed as a large negative that would read as a valuation.")
        findings.append(f"{len(neg_be)} name{'s' if len(neg_be) != 1 else ''} "
                        f"{'carry' if len(neg_be) != 1 else 'carries'} non-positive "
                        f"book equity; M/B suppressed as undefined")
    out()
    out("  PRICE PROVENANCE: Price at Signal from the master's latest cohort. The record")
    out("  documents quote-to-close drift of +2 to +98 minutes on this column; a 0.4% drift")
    out("  is a 0.4% error in M/B, which is immaterial at the precision reported here and is")
    out("  stated rather than assumed away.")
    out()
    out("  IMPLIED SHARES are net income / diluted EPS, NOT a reported share count. Schwab's")
    out("  quote payload carries no shares outstanding and no market cap (read at source,")
    out("  schwab_client.py L110-156), so the error propagates LINEARLY into M/B and MVA.")
    out()

    # ---- integrity of the blocks the numbers came from
    out("-" * 100)
    out("2. BALANCE-SHEET IDENTITY -- the only available check on concept selection")
    out("-" * 100)
    out("  Assets - Liabilities - Equity should equal noncontrolling interest exactly.")
    out("  DP-3C-q was caught by comparing against the filer's own 8-K; that route does not")
    out("  exist for balance-sheet detail, so this identity is the substitute.")
    out(f"{'tk':>6} {'assets':>12} {'liabilities':>12} {'equity':>12} "
        f"{'residual':>12} {'% assets':>9}  note")
    n_flag = 0
    for c in computed:
        r, frac = bs_residual(c["fin"])
        lm = line_map(c["fin"])
        if r is None:
            out(f"{c['tk']:>6} {'':>12} {'':>12} {'':>12} {'not checkable':>12} "
                f"{'':>9}  needs assets, liabilities and equity")
            continue
        note = ""
        nci, nci_label = bs_nci(c["fin"])
        if nci is not None:
            # The identity check proper: does the residual match the filer's
            # OWN noncontrolling interest? Scale is irrelevant here.
            gap = abs(r - nci)
            a_val = lm[L_ASSETS]["value"] or 0
            if a_val and gap / a_val > BS_NCI_TOL:
                note = (f"** residual {money(r)} vs tagged {nci_label} "
                        f"{money(nci)} -- gap {gap/a_val*100:.1f}% of assets, inspect")
                n_flag += 1
            else:
                note = f"= tagged {nci_label} {money(nci)}"
        elif frac is not None and abs(frac) > BS_RESIDUAL_FLAG:
            # FALLBACK ONLY, and now labelled as one. The filer tagged no NCI,
            # so the residual cannot be checked against what it should equal
            # and only its size is available. Size is a weak proxy: see the
            # ANALYST NOTE on bs_nci for the PM / GM / RTX comparison that
            # shows this flag firing on the asset base rather than on an error.
            note = (f"** residual {frac*100:.1f}% of assets, no NCI tagged -- "
                    f"size-only check, inspect")
            n_flag += 1
        out(f"{c['tk']:>6} {money(lm[L_ASSETS]['value']):>12} "
            f"{money(lm[L_LIABS]['value']):>12} {money(lm[L_EQUITY]['value']):>12} "
            f"{money(r):>12} {frac*100:8.2f}%  {note}")
    out("  Where the filer TAGS noncontrolling interest the residual is checked")
    out("  against it -- the identity this block claims to test. Where it does not,")
    out("  the size-only fallback applies and says so; size alone flags on the")
    out("  asset base as readily as on an error (PM 2.82% vs GM 0.58% on residuals")
    out("  of the same order), which is why the tagged comparison is preferred.")
    if n_flag:
        findings.append(f"{n_flag} name{'s' if n_flag != 1 else ''} "
                        f"{'carry' if n_flag != 1 else 'carries'} a balance-sheet "
                        f"residual above {BS_RESIDUAL_FLAG*100:.0f}% of assets")
    out()

    # ---- share-count plausibility
    odd = [c for c in computed if not (SHARES_MIN <= c["sh"] <= SHARES_MAX)]
    if odd:
        out("-" * 100)
        out("3. IMPLIED SHARE COUNTS OUTSIDE THE SANITY WINDOW -- FLAGGED, NOT REJECTED")
        out("-" * 100)
        for c in odd:
            out(f"  {c['tk']:>6} implied {c['sh']:,.0f} shares from "
                f"net income / diluted EPS -- worth a human look")
        findings.append(f"{len(odd)} implied share counts outside the sanity window")
        out()

    # ---- equity source disclosure
    derived = [c for c in computed if c["be_src"] != "StockholdersEquity"]
    if derived:
        out("-" * 100)
        out("4. NAMES WHERE BOOK EQUITY WAS DERIVED, NOT TAGGED")
        out("-" * 100)
        for c in derived:
            out(f"  {c['tk']:>6} equity from {c['be_src']} -- {c['be_note']}")
        out("  Assets - Liabilities is NOT common equity: it includes noncontrolling")
        out("  interest, so M/B for these names is understated by the NCI share.")
        out("  Labelled as a different quantity rather than silently equated.")
        out()

    out("=" * 100)
    if findings:
        out(f"FINDINGS: {len(findings)}")
        for f in findings:
            out(f"  - {f}")
    else:
        out("FINDINGS: none")
    out("=" * 100)
    out("Forecast-free. No valuation is asserted and no price target is implied.")
    out("Advisory-only - no orders - not financial advice.")

    if md_path:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write("# value_anchor exhibit\n\n```\n" + "\n".join(L) + "\n```\n")
        print(f"\n[wrote {md_path}]")
    return 1 if findings else 0


# =============================================================================
# SELF-TESTS
# =============================================================================

def _check(name, got, want, tol=None):
    ok = (abs(got - want) <= tol) if tol is not None else (got == want)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")
    return ok


def _fin(lines, period="2026-06-30"):
    return {"schema": 9, "period": period, "lines": lines,
            "degraded": False, "dropped": []}


def _ln(label, value, note=None, end="2026-06-30", unit="USD"):
    return {"label": label, "value": value, "period_note": note,
            "end": end, "unit": unit, "yoy": None, "prior": None}


def selftest():
    print("value_anchor.py self-tests")
    ok = True

    print("\n first_alpha_run -- the join primitive")
    for s, want in (("gm-20260630.htm", "gm"), ("gld20260630_10q.htm", "gld"),
                    ("uso-20260630x10q.htm", "uso"), ("sndk-20260403.htm", "sndk"),
                    ("snd-20260630.htm", "snd"), ("R1.htm", "r"),
                    ("a2026q3release_ex991.htm", "a"), ("123.xml", "xml"),
                    ("earningsreleasepm-ex991.htm", "earningsreleasepm")):
        ok &= _check(f"first_alpha_run({s})", first_alpha_run(s), want)
    print("  NOTE sndk -> 'sndk' and snd -> 'snd'. EXACT equality is what keeps SanDisk's")
    print("       filing from being attributed to Smart Sand. Prefix matching would not.")

    print("\n implied_shares -- validated against the record's own figures")
    # GM 2026-06-30: net income 1,305M / diluted EPS 1.41 -> 925.5M (record: 925.5M)
    gm = _fin([_ln("Net income", 1_305_000_000), _ln("Diluted EPS", 1.41, unit="USD/shares")])
    sh, why = implied_shares(gm)
    ok &= _check("GM implied shares == 925.5M", round(sh / 1e6, 1), 925.5)
    # JPM: 21,155M / 7.70 -> 2,747M
    jpm = _fin([_ln("Net income", 21_155_000_000), _ln("Diluted EPS", 7.70, unit="USD/shares")])
    ok &= _check("JPM implied shares == 2,747M",
                 round(implied_shares(jpm)[0] / 1e6), 2747)
    # DOW: both negative -> positive share count
    dow = _fin([_ln("Net income", -533_000_000), _ln("Diluted EPS", -0.74, unit="USD/shares")])
    ok &= _check("DOW (both negative) -> positive shares",
                 round(implied_shares(dow)[0] / 1e6, 1), 720.3)

    print("\n NEGATIVE TESTS -- each guard shown to FIRE")
    # period mismatch must block
    bad = _fin([_ln("Net income", 1_305_000_000, note="6M YTD"),
                _ln("Diluted EPS", 1.41, unit="USD/shares")])
    sh, why = implied_shares(bad)
    ok &= _check("period_note mismatch BLOCKS implied shares", sh, None)
    ok &= _check("...and states the reason", "period mismatch" in (why or ""), True)
    # period END mismatch must block
    bad2 = _fin([_ln("Net income", 1e9, end="2026-06-30"),
                 _ln("Diluted EPS", 2.0, end="2026-03-31", unit="USD/shares")])
    ok &= _check("period END mismatch BLOCKS", implied_shares(bad2)[0], None)
    # sign disagreement must block
    bad3 = _fin([_ln("Net income", 1e9), _ln("Diluted EPS", -1.0, unit="USD/shares")])
    sh, why = implied_shares(bad3)
    ok &= _check("sign disagreement BLOCKS", sh, None)
    ok &= _check("...and says so", "not positive" in (why or ""), True)
    # zero EPS must block, not raise
    bad4 = _fin([_ln("Net income", 1e9), _ln("Diluted EPS", 0.0, unit="USD/shares")])
    ok &= _check("zero EPS BLOCKS without raising", implied_shares(bad4)[0], None)
    # missing lines must block with a named reason
    sh, why = implied_shares(_fin([_ln("Total assets", 1e9)]))
    ok &= _check("missing NI and EPS BLOCKS", sh, None)
    ok &= _check("...naming both", ("Net income" in why and "Diluted EPS" in why), True)

    print("\n book_equity -- prefers tagged, falls back, never silently equates")
    tagged = _fin([_ln("Shareholders equity", 62e9), _ln("Total assets", 282.742e9),
                   _ln("Total liabilities", 219.101e9)])
    v, src, note = book_equity(tagged)
    ok &= _check("tagged equity preferred", (v, src), (62e9, "StockholdersEquity"))
    ok &= _check("no caveat when tagged", note, None)
    fallback = _fin([_ln("Total assets", 130.098696e9), _ln("Total liabilities", 45.418e6)])
    v, src, note = book_equity(fallback)
    ok &= _check("falls back to Assets-Liabilities", src, "Assets-Liabilities")
    ok &= _check("...and CAVEATS the NCI difference",
                 "noncontrolling" in (note or ""), True)
    v, src, note = book_equity(_fin([_ln("Total assets", 1e9)]))
    ok &= _check("no equity and no liabilities -> None", v, None)
    ok &= _check("...with a stated reason", note is not None, True)

    print("\n bs_residual -- reproduces the record's GM noncontrolling interest")
    r, frac = bs_residual(tagged)
    ok &= _check("GM residual == 1.641B", round(r / 1e6), 1641)
    ok &= _check("...as a fraction of assets", round(frac, 5), round(1.641e9/282.742e9, 5))
    ok &= _check("not checkable without all three", bs_residual(_fin([_ln("Total assets", 1e9)]))[0], None)

    print("\n THE PACKET IDENTITY: MVA / book equity == M/B - 1, exactly")
    for be, sh_, px in ((62e9, 925.5e6, 85.99), (374.598e9, 2747e6, 363.41),
                        (15.249e9, 720.3e6, 31.18)):
        bvps = be / sh_
        mb = px / bvps
        mva = px * sh_ - be
        ok &= _check(f"MVA/BE == M/B-1 at px={px}", mva / be, mb - 1, 1e-9)

    print("\n NON-POSITIVE BOOK EQUITY -- M/B suppressed, MVA retained")
    print("  Real case: PM reports book equity of -8.58B on 2026-06-30. Buybacks and")
    print("  dividends exceeding retained earnings is a REPORTED STATE, not a defect.")
    be_neg, sh_neg, px_neg = -8.58e9, 1565.0e6, 187.98
    mva_neg = px_neg * sh_neg - be_neg
    ok &= _check("MVA on negative equity is a valid subtraction",
                 round(mva_neg / 1e9, 2), 302.77)
    ok &= _check("MVA is POSITIVE despite negative equity", mva_neg > 0, True)
    # the ratio the tool must refuse to print
    bad_mb = px_neg / (be_neg / sh_neg)
    ok &= _check("the naive ratio would print a large negative", round(bad_mb, 2), -34.29)
    ok &= _check("...which is why M/B is gated on be > 0", be_neg > 0, False)
    print("  A -34.29 in an M/B column reads as a valuation. It is not one. Suppressed.")

    print("\n vq completeness")
    ok &= _check("all five present -> 5/5", vq_string(_fin([
        _ln("Total assets", 1), _ln("Total liabilities", 1), _ln("Shareholders equity", 1),
        _ln("Net income", 1), _ln("Diluted EPS", 1)]))[0], "5/5")
    ok &= _check("three of five -> 3/5", vq_string(tagged)[0], "3/5")

    print("\n log tag parsing -- the tag sits AFTER the JSON on the same line")
    import tempfile
    line = ('2026-08-17 09:35:41,225 | INFO | Signal JSON: {"ticker": "AAPL", '
            '"signal": "HOLD", "confidence": 57} | D[x] | B[y] | '
            'E[8k=1@2026-07-30; form4=+0/-1@2026-08-13; periodic=10-Q@2026-07-31; '
            'fin=11@2026-06-27]\n')
    line2 = ('2026-08-17 09:36:00,000 | INFO | Signal JSON: {"ticker": "SPY", '
             '"signal": "HOLD"} | E[no filings]\n')
    line3 = ('2026-08-17 09:37:00,000 | INFO | Signal JSON: {"ticker": "SND", '
             '"signal": "HOLD"} | E[8k=2@2026-08-11; fin=degraded]\n')
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(line + line2 + line3)
        p = fh.name
    t = parse_log_tags(p)
    os.unlink(p)
    ok &= _check("three tickers parsed", sorted(t), ["AAPL", "SND", "SPY"])
    ok &= _check("AAPL fin lines", t["AAPL"]["fin_lines"], 11)
    ok &= _check("AAPL anchor", t["AAPL"]["fin_anchor"], "2026-06-27")
    ok &= _check("AAPL periodic", t["AAPL"]["periodic"], "10-Q@2026-07-31")
    ok &= _check("SPY 'no filings' -> no fin", t["SPY"]["fin_lines"], None)
    ok &= _check("SND degraded flagged", t["SND"]["degraded"], True)
    ok &= _check("missing log -> empty, no raise", parse_log_tags("/nonexistent"), {})

    print("\n verified_join -- MULTI-ACCESSION REGRESSION (found on the real cache)")
    print("  edgar_cache accumulates every filing ever fetched, so one ticker has")
    print("  several accessions. The previous version keyed both result dicts by")
    print("  TICKER while looping over ACCESSIONS, so a ticker with one matching and")
    print("  one stale filing landed in BOTH and the last write won -- reported")
    print("  UNVERIFIED in one section and used in the next.")
    stale = _fin([_ln("Net income", 1.0)], period="2026-03-31")
    fresh = _fin([_ln("Net income", 2.0)], period="2026-06-30")
    fins = {"000000000000000001": stale, "000000000000000002": fresh}
    fn_map = {"000000000000000001": "GLD", "000000000000000002": "GLD"}
    tags = {"GLD": {"fin_lines": 1, "fin_anchor": "2026-06-30",
                    "degraded": False, "raw": "", "periodic": None}}
    v, u = verified_join(fins, fn_map, tags)
    ok &= _check("one accession matches -> ticker is VERIFIED", "GLD" in v, True)
    ok &= _check("...and is NOT ALSO in unverified", "GLD" in u, False)
    ok &= _check("...and the VERIFYING accession is the one used",
                 v["GLD"][0], "000000000000000002")
    # neither matches -> unverified only, and the count is reported
    tags2 = {"GLD": {"fin_lines": 9, "fin_anchor": "2026-12-31",
                     "degraded": False, "raw": "", "periodic": None}}
    v2, u2 = verified_join(fins, fn_map, tags2)
    ok &= _check("no accession matches -> unverified", "GLD" in u2, True)
    ok &= _check("...and not verified", "GLD" in v2, False)
    ok &= _check("...and the reason names the candidate count",
                 "2 cached accessions" in u2["GLD"][1], True)
    # latest VERIFYING period wins when several verify
    tags3 = {"GLD": {"fin_lines": 1, "fin_anchor": None,
                     "degraded": False, "raw": "no fin", "periodic": None}}
    v3, u3 = verified_join(fins, fn_map, tags3)
    ok &= _check("a tag with no fin=N@date verifies nothing", "GLD" in v3, False)
    ok &= _check("candidates_by_ticker sorts oldest period first",
                 [a for a, _ in candidates_by_ticker(fins, fn_map)["GLD"]],
                 ["000000000000000001", "000000000000000002"])

    print("\n filename_join -- exact equality, ambiguity surfaced not resolved")
    with tempfile.TemporaryDirectory() as d:
        for n in ("000146785826000051_gm-20260630.htm",
                  "000162828026029401_sndk-20260403.htm",
                  "000152962826000095_snd-20260630.htm",
                  "000152962826000095_snd-pressrelease.htm",
                  "000143774926016164_weat20260331_10q.htm",
                  "000111111111111111_gm-x.htm",
                  "000111111111111111_snd-x.htm",
                  "fin_000146785826000051.json"):
            open(os.path.join(d, n), "w").close()
        m, amb = filename_join(d, ["GM", "SND", "CORN"])
        ok &= _check("GM joined", m.get("000146785826000051"), "GM")
        ok &= _check("SND joined from two consistent docs", m.get("000152962826000095"), "SND")
        ok &= _check("SNDK does NOT join to SND",
                     "000162828026029401" in m, False)
        ok &= _check("weat-named doc does NOT join to CORN",
                     "000143774926016164" in m, False)
        ok &= _check("conflicting docs -> AMBIGUOUS, not guessed",
                     sorted(amb.get("000111111111111111", [])), ["GM", "SND"])
        ok &= _check("...and ambiguous is excluded from the map",
                     "000111111111111111" in m, False)
        ok &= _check("fin_*.json is not itself treated as evidence",
                     all(not k.startswith("fin") for k in m), True)

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


# =============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Forecast-free market-vs-book per covered name. No DCF, no "
                    "price target. Reads the master and the derived XBRL cache; "
                    "writes nothing.")
    ap.add_argument("--tracker", default=DEFAULT_TRACKER)
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--log", default=None,
                    help="session log for E[...] tag verification; without it "
                         "no join is verified and nothing is computed")
    ap.add_argument("--md", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    log_path = a.log
    if log_path is None:
        cands = sorted(glob.glob(os.path.join("logs", "signals_*.log")))
        log_path = cands[-1] if cands else None
    return report(a.tracker, a.cache, log_path, md_path=a.md)


if __name__ == "__main__":
    sys.exit(main())
