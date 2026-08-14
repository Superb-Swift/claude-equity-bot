# =============================================================================
# edgar_client.py  —  SEC EDGAR filing context provider  (Phase 3-C / EW1)
# =============================================================================
# WHAT THIS IS:
#   The FIRST prompt-provider on the WS1 registry. A ContextProvider(mode=
#   "prompt") appended to context_providers.REGISTRY, surfaced by
#   run_prompt_context(). The blend engine, risk gate, tracker schema and
#   logging are UNTOUCHED — see Phase3C_EDGAR_Scope_Spec.md §3.
#
#   Filing set (Scope Spec §0, from the 2026-06-15 scoping):
#     * Form 4        insider transactions        (last WINDOW_DAYS)
#     * 8-K           material events + item codes(last WINDOW_DAYS)
#     * 10-Q / 10-K   latest periodic + bounded MD&A extract
#
# WHAT THIS IS NOT:
#   It does NOT touch confidence, the blend, or the risk gate. EDGAR shapes
#   the signal only through the model's reasoning on the prompt section.
#   DP-4 default: filing presence does NOT feed data_quality in v1.
#
# BUILD STATUS (2026-08-02, EW1):
#   Built against Phase3C_EDGAR_Scope_Spec.md v1.0. WIRING IS DEFERRED — this
#   module registers itself on import, but main.py does not yet call
#   run_prompt_context() and claude_signal.get_signal() has no extra_context
#   parameter. Until both land, importing this module changes nothing about
#   the live run except one CIK-map fetch if prefetch is called.
#
#   NOT LIVE-TESTED AGAINST SEC. The build sandbox has no egress to
#   www.sec.gov / data.sec.gov, so every fetch path here is exercised against
#   fixtures only (--selftest). The first real fetch happens on the operator's
#   Windows host and is an EW2 item, BEFORE the parser audit and PM smoke.
#
# ANALYST NOTE — WHY THE COVERAGE AUDIT LIVES IN THIS FILE:
#   Phase3C_Kickoff_Prompt.md §2 says EDGAR reaches at most 16 of 24 names and
#   flags AG and NTR as [?] (possible 40-F/6-K filers). That denominator sets
#   E4's stratification and it should be COMPUTED, not asserted. `--coverage`
#   resolves every watchlist ticker against the live CIK map and reports the
#   form types actually present. Run it once before E4 is pre-registered.
#
# ANALYST NOTE — CBRS:
#   DP-3 default is EDGAR SKIPS CBRS ENTIRELY until the Q4 2026 Path-A review.
#   That is enforced here in one place (SKIP_TICKERS) rather than by the
#   caller, so the exclusion cannot be lost in wiring. --coverage still
#   REPORTS CBRS (marked skipped) so the record shows what was excluded.
# =============================================================================

import os
import re
import sys
import json
import time
import html
import logging
import argparse
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from context_providers import Provider, register

load_dotenv()

log = logging.getLogger(__name__)

# --- HTTP layer -------------------------------------------------------------
# ANALYST NOTE: `requests` is almost certainly already installed (the Schwab
#   and Finnhub clients use it), but this module must never be the reason a
#   run fails to import. Fall back to the stdlib rather than hard-depend.
try:
    import requests as _requests
except ImportError:                                     # pragma: no cover
    _requests = None
    import urllib.request as _urlreq
    import urllib.error as _urlerr


# =============================================================================
# CONFIGURATION
# =============================================================================

CIK_MAP_URL      = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL  = "https://data.sec.gov/submissions/CIK{cik10}.json"
ARCHIVES_URL     = ("https://www.sec.gov/Archives/edgar/data/{cik}/"
                    "{accession_nodash}/{document}")
FILING_INDEX_URL = ("https://www.sec.gov/Archives/edgar/data/{cik}/"
                    "{accession_nodash}/index.json")
XBRL_FACTS_URL   = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

# SEC etiquette (Scope Spec §1). 10 req/sec per IP; the spec asks for >=120 ms.
# A missing or generic User-Agent returns 403 plus a ~10-minute IP block.
RATE_LIMIT_DELAY = 0.125          # seconds between ANY two SEC calls
HTTP_TIMEOUT     = 20             # seconds
MAX_RETRIES      = 2              # on 429 / transient error

# --- Run budget -------------------------------------------------------------
# ANALYST NOTE (2026-08-02, added at the workflow-fit review): the AM 9:30 CST
#   run is CANONICAL and time-boxed. EDGAR must never be the reason it is late.
#   Worst case without a ceiling is ~180 fetches x (20s timeout x 3 attempts),
#   which is pathological. Past the budget every remaining fetch returns None
#   and those tickers degrade to no-EDGAR — a partial-coverage run, logged as
#   such, rather than a slow one. Override with EDGAR_MAX_SECONDS in .env.
EDGAR_MAX_SECONDS = float(os.getenv("EDGAR_MAX_SECONDS", "120"))

# --- Document cache ---------------------------------------------------------
# ANALYST NOTE (2026-08-02, SELF-CORRECTION): the first EW1 build cached the
#   CIK map and submissions per run but re-fetched every Form 4 and every
#   10-K/10-Q DOCUMENT on every run. Scope Spec §1 says "only re-fetch
#   documents on a new accession" and the build did not honour it — a 10-K
#   primary document runs to several MB and changes QUARTERLY, so the daily
#   run was re-downloading it ~60 times per filing. Documents are immutable
#   once filed, so the accession number is a safe cache key forever.
#   Manifest Tier 0 already anticipates this directory: edgar_cache/ is
#   gitignored, derived, re-fetchable, and never a chat input.
EDGAR_CACHE_DIR = os.getenv("EDGAR_CACHE_DIR", "edgar_cache")

# ANALYST NOTE (2026-08-02): DERIVED caches must carry a schema version.
#   Raw documents are immutable, so an accession is a safe key forever. An
#   EXTRACT is not — it is a function of the code that produced it, and the
#   financials cache is keyed on the periodic accession, which does not change
#   when the extractor is fixed. That made the period-anchor fix invisible on
#   RTX: correct code ran, stale output was served. This is the THIRD time a
#   cache has masked a working fix in this build. Bump on any change to the
#   extraction shape and every stale entry is ignored automatically.
#
# ANALYST NOTE (2026-08-10, FOURTH occurrence, live on RTX): the N-1 fix and
#   DP-3C-j's `degraded` field both changed extract_financials()'s behavior
#   and output shape without this bump, on the exact ticker the ANALYST NOTE
#   above was written about. `--xbrl RTX` confirmed both a Q ($24.708B) and
#   an H1 ($46.784B) entry exist for Revenue, tied on end date — the fixed
#   selection logic traced correctly by hand — but `--ticker RTX` still
#   rendered the unlabelled $46.8B H1 figure, because RTX's accession
#   0000101829-26-000027 was already cached under schema 6 from before the
#   fix landed. Caught live rather than assumed fixed. 6 -> 7.
#
# ANALYST NOTE (2026-08-10, same session, FIFTH bump): 7 recomputed cleanly
#   and RTX STILL rendered $46.8B unlabelled — proving the cache was only
#   ever masking the symptom, not causing it. `diag_anchor.py` traced the
#   real defect to the report-date override's bucket vote
#   (_modal_flow_bucket, H:70 vs Q:39 across all of companyfacts, overruling
#   a 4-1 headline vote for Q). Fixed by _headline_flow_bucket. 7 -> 8
#   because that changes which period every cached extract describes.
#
# ANALYST NOTE (2026-08-11): 8 -> 9 for DP-3C-q (total revenue supersedes the
#   contract-revenue component). Changes which CONCEPT the revenue line
#   reports on affected filers -- GM moves from $43.762B to $48.026B -- so
#   every cached extract must recompute. Bumped in the SAME edit as the
#   behaviour change, which is the discipline the four notes above exist to
#   enforce and which was missed on 2026-08-10.
EXTRACT_SCHEMA = 9

# DP-3C-b — filing windows and counts.
WINDOW_DAYS      = 30             # 8-K and Form 4 lookback
# DP-3C-a — bounded MD&A extract + filed date; NO separate LLM call in v1.
MDA_MAX_CHARS    = 1200
# DP-3C-c — Form-4 net direction plus rough size. Each Form 4 costs one fetch,
# so the per-ticker document budget is bounded; beyond it we degrade to a
# COUNT-ONLY read and say so in the section rather than guessing direction.
MAX_FORM4_DOCS   = 10
# 8-K bodies. ANALYST NOTE (2026-08-02, v1.1): the first build read only the
#   `items` field from the submissions index — a COUNT and an item CODE. That
#   is metadata, not content: an Item 2.02 beat and an Item 2.02 miss render
#   identically, and 8-K is the material-events channel the phase exists to
#   surface. Bodies are now fetched and extracted. 8-Ks are short (a page or
#   two) so this is cheap relative to a 10-K, and the accession cache makes it
#   a once-ever cost per filing.
MAX_8K_DOCS      = 5
EIGHTK_MAX_CHARS = 450

# DP-3 — CBRS is excluded from EDGAR entirely until the Q4 2026 Path-A review.
SKIP_TICKERS = {"CBRS"}

# FALLBACK watchlist for --coverage only. The live run NEVER reads this — it
# gets its universe from main.py, which builds `sorted(all_held) +
# WATCHLIST_SCOUT` from live Schwab positions, so a newly opened position is
# picked up automatically with no code change here.
#
# ANALYST NOTE (2026-08-02): this constant is a hand-copied SNAPSHOT of a list
#   that moves, and DP-3C-d unfreezes the watchlist at this boundary. Two
#   sources of truth for one list is how E4's denominator goes stale without
#   anyone noticing. --coverage therefore derives its universe from the most
#   recent signals log by default — the tickers the bot ACTUALLY ran — and
#   falls back to this constant only when no log is readable, saying so.
#   [R] Phase3C_Kickoff_Prompt §2, as of 2026-07-31.
WATCHLIST_24 = [
    "AAPL", "AG", "AIQ", "CBRS", "CORN", "DOW", "FTI", "GLD",
    "GM", "JPM", "MSFT", "NKE", "NTR", "NVDA", "PM", "PWR",
    "QQQ", "RTX", "SCHD", "SND", "SPY", "VTI", "WMT", "XLU",
]

# 8-K item codes worth naming in the prompt. Item 9.01 (financial statements
# and exhibits) is attached to a large share of 8-Ks as boilerplate and
# carries no event information on its own, so it is suppressed unless it is
# the ONLY item on the filing.
EIGHTK_ITEM_LABELS = {
    "1.01": "material agreement entered",
    "1.02": "material agreement terminated",
    "2.01": "acquisition or disposition",
    "2.02": "results of operations",
    "2.03": "material direct financial obligation",
    "2.05": "costs from exit or disposal",
    "3.01": "listing / delisting notice",
    "4.01": "auditor change",
    "4.02": "non-reliance on prior financials",
    "5.02": "officer or director change",
    "5.03": "charter or bylaw amendment",
    "5.07": "shareholder vote results",
    "7.01": "Reg FD disclosure",
    "8.01": "other events",
    "9.01": "financial statements and exhibits",
}
NOISE_ITEMS = {"9.01"}

# Form 4 transaction codes. P/A are acquisitions, S/D dispositions. M
# (option exercise) and F (tax withholding) are excluded from the net tally:
# both are mechanical and neither signals a discretionary insider view.
# ANALYST NOTE (2026-08-02, DEFECT FOUND ON THE FIRST LIVE COVERAGE RUN):
#   form-type matching was `form.startswith("4")`, which also matches 40-F,
#   40FR12B, 424B2/B3/B5, 485APOS/BPOS and 497. Every foreign private issuer
#   and every prospectus filer read as an insider filer. Worse in the live
#   provider than in the audit: extract_form4 would have DOWNLOADED those
#   prospectuses (multi-MB) inside the run budget and parsed them for
#   transactionCode, finding none and reporting direction "mixed" — a number
#   the tool did not compute, which is the defect class cleared five times in
#   3-B. Form 4 and its amendment are the only insider forms; match exactly.
FORM4_FORMS = {"4", "4/A"}

# ANALYST NOTE (2026-08-02, v1.3): the first build counted code A (grant or
#   award) as a BUY. An RSU or option grant is COMPENSATION, not a purchase —
#   under that rule every vesting quarter would have read as "net direction:
#   buying" on the largest employers in the watchlist, which is the opposite
#   of a signal. Direction is computed from OPEN-MARKET transactions only:
#     P  open-market or private purchase   -> buy
#     S  open-market or private sale       -> sell
#   Everything else is reported but never moves the direction:
#     A  grant / award            M  option exercise
#     F  tax withholding          D  disposition to the issuer
#   The parse is also restricted to the NON-DERIVATIVE table; the derivative
#   table carries option grants and exercises, which are not share trades.
FORM4_BUY_CODES  = {"P"}
FORM4_SELL_CODES = {"S"}
FORM4_AWARD_CODES = {"A"}
FORM4_MECH_CODES  = {"M", "F", "D", "G", "C", "E", "H", "I"}

PERIODIC_FORMS = ("10-Q", "10-K")

# =============================================================================
# FINANCIAL STATEMENTS (XBRL)
# =============================================================================
# ANALYST NOTE (2026-08-02, v1.2 — SCOPE WIDENED, see DP-3C-g):
#   The pre-registered filing set read "10-Q/10-K MD&A extracts". MD&A is
#   management's NARRATIVE; the financial statements are the primary-source
#   numbers the narrative describes, and a mandate for "primary-source SEC
#   filing context" that omits the statements is not serving its own purpose.
#
#   WHY XBRL AND NOT THE HTML TABLES: every 10-Q/10-K carries machine-readable
#   XBRL, exposed at data.sec.gov/api/xbrl/companyfacts. Scraping the rendered
#   statement tables out of a multi-megabyte HTML document is fragile in a way
#   that fails SILENTLY — a changed table layout yields plausible wrong numbers
#   rather than an error, which is the defect class this project has cleared
#   six times. XBRL is tagged by the filer and validated by the SEC.
#
#   THE FALLBACK LISTS ARE NOT OPTIONAL. Filers tag the same line item under
#   different us-gaap concepts (Apple uses RevenueFromContractWithCustomer...,
#   older filers use Revenues or SalesRevenueNet). First concept present wins;
#   a line item with no match is OMITTED rather than guessed at.
FINANCIAL_CONCEPTS = [
    ("Revenue", "flow", ["RevenueFromContractWithCustomerExcludingAssessedTax",
                         "RevenueFromContractWithCustomerIncludingAssessedTax",
                         "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"]),
    ("Gross profit", "flow", ["GrossProfit"]),
    ("Operating income", "flow", ["OperatingIncomeLoss"]),
    ("Net income", "flow", ["NetIncomeLoss", "ProfitLoss"]),
    ("Diluted EPS", "flow", ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"]),
    ("Operating cash flow", "flow",
     ["NetCashProvidedByUsedInOperatingActivities",
      "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]),
    ("Total assets", "instant", ["Assets"]),
    ("Total liabilities", "instant", ["Liabilities"]),
    ("Shareholders equity", "instant",
     ["StockholdersEquity",
      "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]),
    ("Cash and equivalents", "instant",
     ["CashAndCashEquivalentsAtCarryingValue"]),
    ("Long-term debt", "instant",
     ["LongTermDebtNoncurrent", "LongTermDebt"]),
]

# Only these forms count as a statement source — an 8-K exhibit may carry
# tagged facts too, and mixing them produces period comparisons that are not
# like-for-like.
XBRL_FORMS = {"10-Q", "10-K"}

# Foreign private issuers file 40-F / 6-K instead of 10-K / 10-Q / 8-K under
# the MJDS regime. NOT in the pre-registered 3-C filing set (Kickoff §1:
# Form 4, 8-K, 10-Q/10-K MD&A). Detected and REPORTED so the coverage table
# says WHY a name is uncovered rather than leaving it blank; extending the
# filing set to 40-F/6-K would be a new decision point, not a build choice.
FOREIGN_FORMS = {"40-F", "40-F/A", "6-K", "6-K/A", "20-F", "20-F/A"}


# =============================================================================
# HTTP
# =============================================================================

def _user_agent():
    """SEC_USER_AGENT is MANDATORY. Tier-0 secret — read from .env, never
    committed. Returns None if absent so callers can degrade rather than
    fetch with a generic UA and earn a ~10-minute IP block."""
    ua = os.getenv("SEC_USER_AGENT", "").strip()
    return ua or None


_last_call = [0.0]
_budget    = {"start": None, "tripped": False}


def reset_budget():
    """Start (or restart) the per-run EDGAR wall clock."""
    _budget["start"] = time.monotonic()
    _budget["tripped"] = False


def budget_exceeded():
    if _budget["start"] is None:
        reset_budget()
        return False
    over = (time.monotonic() - _budget["start"]) > EDGAR_MAX_SECONDS
    if over and not _budget["tripped"]:
        _budget["tripped"] = True
        log.warning("[EDGAR] run budget of %.0fs exhausted — remaining tickers "
                    "degrade to no-EDGAR for this run.", EDGAR_MAX_SECONDS)
    return over


def _throttle():
    """Enforce >= RATE_LIMIT_DELAY between any two SEC calls, process-wide."""
    elapsed = time.monotonic() - _last_call[0]
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_call[0] = time.monotonic()


def _http_get(url, as_json=False):
    """GET with SEC etiquette. Returns parsed JSON / text, or None.

    ANALYST NOTE: this NEVER raises. Graceful degradation (E3) means any
    fetch failure omits the EDGAR section and the run continues on price +
    news, exactly the way a missing S1 or trajectory section degrades today.
    """
    ua = _user_agent()
    if not ua:
        log.warning("[EDGAR] SEC_USER_AGENT is not set — skipping fetch. "
                    "Add it to .env (Tier-0 secret); a generic UA returns 403.")
        return None

    if budget_exceeded():
        return None

    headers = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}

    for attempt in range(MAX_RETRIES + 1):
        _throttle()
        try:
            if _requests is not None:
                r = _requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
                if r.status_code == 429:
                    time.sleep(1.0 + attempt)
                    continue
                if r.status_code == 403:
                    log.error("[EDGAR] 403 for %s — check SEC_USER_AGENT; "
                              "the IP may be blocked ~10 min.", url)
                    return None
                if r.status_code != 200:
                    log.warning("[EDGAR] HTTP %s for %s", r.status_code, url)
                    return None
                return r.json() if as_json else r.text
            else:                                        # pragma: no cover
                req = _urlreq.Request(url, headers=headers)
                with _urlreq.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body) if as_json else body
        except Exception as e:
            log.warning("[EDGAR] fetch failed (%s/%s) %s: %s",
                        attempt + 1, MAX_RETRIES + 1, url, e)
            time.sleep(0.5 * (attempt + 1))
    return None


# =============================================================================
# DOCUMENT CACHE  (accession-keyed; filings are immutable once filed)
# =============================================================================

def _cache_path(accession, document):
    """Cache filename for one filing document.

    ANALYST NOTE (2026-08-02, SELF-INFLICTED DEFECT): this used
    os.path.basename(document), so "xslF345X05/wf-form4_x.xml" and
    "wf-form4_x.xml" — the RENDERED HTML and the RAW XML, two different URLs
    with different content — collided on one cache key. The Form 4 fix that
    tried the raw path first was then served the cached rendered HTML and
    still found zero transactions. Include the directory component.
    """
    safe = (f"{accession.replace('-', '')}_"
            f"{document.replace('/', '__').replace(chr(92), '__')}")
    return os.path.join(EDGAR_CACHE_DIR, safe[:180])


def fetch_document(cik10, accession, document, use_cache=True, validator=None):
    """Fetch one filing document, disk-cached by accession (Scope Spec §1).

    Returns text or None. A cache read costs no SEC request and no throttle,
    so a PM diagnostic run after an AM run is nearly free, and the quarterly
    10-K is downloaded once per accession rather than once per session.
    """
    if not accession or not document:
        return None

    path = _cache_path(accession, document)
    if use_cache and os.path.exists(path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                cached = f.read()
            # ANALYST NOTE (2026-08-02): a cached entry is only trusted if it
            # still satisfies the caller's expectation. The Form 4 defect wrote
            # XSL-RENDERED HTML under a key the corrected code then read back as
            # if it were raw XML, so the fix was invisible until the cache was
            # cleared by hand. Validating on READ makes the cache self-healing:
            # a stale or wrong-shaped entry is re-fetched and overwritten rather
            # than silently served. An operator should never have to know that
            # a code change requires a cache wipe.
            if validator is None or validator(cached):
                return cached
            log.info("[EDGAR] cached %s failed validation — re-fetching", path)
        except OSError as e:
            log.warning("[EDGAR] cache read failed for %s: %s", path, e)

    text = _http_get(_document_url(cik10, accession, document))
    if text and use_cache:
        try:
            os.makedirs(EDGAR_CACHE_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as e:                  # cache failure is never fatal
            log.warning("[EDGAR] cache write failed for %s: %s", path, e)
    return text


# =============================================================================
# CIK MAP + SUBMISSIONS
# =============================================================================

def load_cik_map(caches=None):
    """Ticker -> zero-padded 10-digit CIK. Static; fetch once per run.

    company_tickers.json is a dict of {index: {cik_str, ticker, title}}.
    """
    caches = caches if caches is not None else {}
    if caches.get("edgar_cik"):
        return caches["edgar_cik"]

    payload = _http_get(CIK_MAP_URL, as_json=True)
    mapping = {}
    if payload:
        rows = payload.values() if isinstance(payload, dict) else payload
        for row in rows:
            try:
                mapping[str(row["ticker"]).upper()] = str(row["cik_str"]).zfill(10)
            except (KeyError, TypeError):
                continue
    else:
        log.warning("[EDGAR] CIK map unavailable — every ticker degrades to "
                    "no-EDGAR this run.")

    caches["edgar_cik"] = mapping
    return mapping


def fetch_submissions(cik10, caches=None):
    """Filing history for one CIK. Cached per run (filings change ~quarterly)."""
    caches = caches if caches is not None else {}
    subs_cache = caches.setdefault("edgar_subs", {})
    if cik10 in subs_cache:
        return subs_cache[cik10]

    payload = _http_get(SUBMISSIONS_URL.format(cik10=cik10), as_json=True)
    subs_cache[cik10] = payload
    return payload


def _recent_rows(subs):
    """Yield the 'recent' filing block as a list of per-filing dicts.

    ANALYST NOTE: EDGAR returns filings as PARALLEL ARRAYS under
    filings.recent (form[], filingDate[], accessionNumber[], ...), not as a
    list of records. Zipping them is the whole trick; doing it in one place
    keeps every downstream reader honest about index alignment.
    """
    if not subs:
        return []
    recent = (subs.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    if not forms:
        return []

    keys = ("form", "filingDate", "reportDate", "accessionNumber",
            "primaryDocument", "items")
    cols = {k: recent.get(k) or [""] * len(forms) for k in keys}

    rows = []
    for i in range(len(forms)):
        rows.append({k: (cols[k][i] if i < len(cols[k]) else "") for k in keys})
    return rows


def _within_window(date_str, since):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date() >= since
    except (ValueError, TypeError):
        return False


def _window_start(as_of=None, days=WINDOW_DAYS):
    as_of = as_of or datetime.now(timezone.utc).date()
    return as_of - timedelta(days=days)


# =============================================================================
# EXTRACTION — 8-K
# =============================================================================

_BOILER_RE = re.compile(
    r"(forward[- ]looking statements?|safe harbor|private securities "
    r"litigation reform act|cautionary (note|statement))", re.I)


def _skip_boilerplate(text, scan=1500):
    """Advance past a forward-looking-statements paragraph, to the END of the
    boilerplate SENTENCE rather than the end of the matched phrase — otherwise
    the tail of the disclaimer ("...within the meaning of the Act.") survives
    into the extract and reads as content."""
    b = _BOILER_RE.search(text[:scan])
    if not b:
        return text
    tail = text[b.end():]
    m = re.search(r"[.!?]\s+(?=[A-Z])", tail)
    return tail[m.end():] if m else tail


_VIEWER_RE = re.compile(r"IDEA:\s*XBRL\s+DOCUMENT|Document and Entity Information",
                        re.I)


def _clean_8k_body(text):
    """Trim SEC/EDGAR chrome and forward-looking boilerplate off an 8-K body.

    ANALYST NOTE: nearly every 8-K opens with the cover page (registrant name,
    commission file number, checkbox rubric) and often a forward-looking
    statements paragraph. Both are identical across filings and carry zero
    signal — feeding them to the model spends prompt budget to say nothing.
    Start after the item heading where one is present, and skip past a
    boilerplate marker when it appears early.
    """
    if not text:
        return ""
    # Strip EDGAR exhibit chrome: "EX-99.1 2 msft-ex99_1.htm EX-99.1 EX-99.1
    # Exhibit 99.1" is the renderer repeating the document header, not content.
    text = re.sub(
        r"^(?:\s*(?:EX-\d+(?:\.\d+)?|Exhibit\s+\d+(?:\.\d+)?|\d{1,3}|"
        r"[\w.\-]+\.html?)\s*){1,10}", "", text, flags=re.I)

    m = re.search(r"item\s+\d\.\d{2}[^A-Za-z0-9]{0,4}([A-Z][^.]{0,90})", text, re.I)
    if m:
        text = text[m.end():]
    text = _skip_boilerplate(text)
    return text.strip(" .;:-\u2014")


def fetch_8k_body(cik10, accession, primary_document):
    """Fetch the substantive text of one 8-K.

    An Item 2.02 earnings 8-K is usually a THIN WRAPPER — "the Company issued
    a press release ... attached as Exhibit 99.1" — and the numbers live in
    the exhibit, not the primary document. So: pull the primary document, and
    if it is short or points at an exhibit, pull the largest EX-99 from the
    filing index and use that instead. Both are cached by accession, so this
    is one-time per filing rather than per session.
    """
    body = fetch_document(cik10, accession, primary_document) or ""
    text = html_to_text(body)
    if _VIEWER_RE.search(text[:400]):
        text = ""                    # viewer rendering, not filing content

    # RTX writes "furnished herewith as Exhibit No. 99"; the original trigger
    # required "exhibit" immediately followed by "99" and never fired, so the
    # model received the Section-18 disclaimer instead of the quarter's
    # results. Match the wrapper by INTENT, not by one exact phrasing.
    wrapper_re = re.compile(
        r"(exhibit\s*(?:no\.?\s*)?9?9|furnished\s+herewith|"
        r"attached\s+(?:hereto\s+)?as\s+exhibit|issued\s+a\s+press\s+release)",
        re.I)
    needs_exhibit = len(text) < 2500 or bool(wrapper_re.search(text))
    if needs_exhibit:
        idx = _http_get(FILING_INDEX_URL.format(
            cik=str(int(cik10)), accession_nodash=accession.replace("-", "")),
            as_json=True)
        items = ((idx or {}).get("directory") or {}).get("item") or []
        def _is_ex99(name):
            # filenames vary: ex-99.1.htm, ex99_1.htm, rtx-20260723xex99.htm
            flat = re.sub(r"[^a-z0-9]", "", str(name).lower())
            return "ex99" in flat

        def _is_viewer_artifact(name):
            # R1.htm, R21.htm ... are the XBRL VIEWER renderings EDGAR
            # generates. They are "Document and Entity Information" tables, not
            # the filing's content. JPM and SND both surfaced one as their 8-K
            # body: "XML 21 R1.htm IDEA: XBRL DOCUMENT v3.26.1 ...".
            return bool(re.match(r"^R\d+\.html?$", str(name).strip(), re.I))

        items = [it for it in items
                 if not _is_viewer_artifact(it.get("name", ""))]

        cands = [it for it in items
                 if str(it.get("name", "")).lower().endswith((".htm", ".html"))
                 and _is_ex99(it.get("name", ""))]
        if not cands:
            cands = [it for it in items
                     if str(it.get("name", "")).lower().endswith((".htm", ".html"))
                     and str(it.get("name", "")) != primary_document]
        if cands:
            best = max(cands, key=lambda it: int(it.get("size", 0) or 0))
            ex = fetch_document(cik10, accession, best["name"])
            ex_text = html_to_text(ex)
            if _VIEWER_RE.search(ex_text[:400]):
                ex_text = ""
            if len(ex_text) > len(text):
                text = ex_text
    return _clean_8k_body(text)


def extract_8k(rows, since, cik10=None, fetch=True):
    """8-Ks in the window: count, item labels, AND a bounded body extract.

    DP-3C-b sets the window. The body extract is what turns "an Item 2.02
    happened" into something the model can reason about; without it the
    section reports that a material event occurred while withholding what it
    said, which is the difference between metadata and content.
    """
    hits = [r for r in rows
            if r["form"] == "8-K" and _within_window(r["filingDate"], since)]
    hits.sort(key=lambda r: r["filingDate"], reverse=True)

    labels, events = [], []
    for r in hits:
        codes = [c.strip() for c in str(r.get("items", "")).split(",") if c.strip()]
        meaningful = [c for c in codes if c not in NOISE_ITEMS] or codes
        names = []
        for c in meaningful:
            label = EIGHTK_ITEM_LABELS.get(c)
            entry = f"Item {c} {label}" if label else f"Item {c}"
            names.append(entry)
            if entry not in labels:
                labels.append(entry)
        events.append({"date": r["filingDate"], "items": names,
                       "accession": r["accessionNumber"],
                       "document": r.get("primaryDocument", ""), "body": ""})

    if fetch and cik10:
        for ev in events[:MAX_8K_DOCS]:
            body = fetch_8k_body(cik10, ev["accession"], ev["document"])
            if body:
                if len(body) > EIGHTK_MAX_CHARS:
                    body = body[:EIGHTK_MAX_CHARS].rsplit(" ", 1)[0] + " \u2026"
                ev["body"] = body

    return {"count": len(hits), "items": labels,
            "dates": [r["filingDate"] for r in hits],
            "events": events,
            "bodies": sum(1 for e in events if e["body"])}


# =============================================================================
# EXTRACTION — Form 4
# =============================================================================

_TXN_CODE_RE   = re.compile(r"<transactionCode>\s*([A-Z])\s*</transactionCode>")
_TXN_SHARES_RE = re.compile(
    r"<transactionShares>\s*<value>\s*([\d.]+)\s*</value>", re.S)
_TXN_PRICE_RE  = re.compile(
    r"<transactionPricePerShare>\s*<value>\s*([\d.]+)\s*</value>", re.S)


def _document_url(cik10, accession, document):
    return ARCHIVES_URL.format(
        cik=str(int(cik10)),
        accession_nodash=accession.replace("-", ""),
        document=document,
    )


def parse_form4_xml(text):
    """Net insider direction + rough size from one Form 4 ownership XML.

    Returns {'buys': n, 'sells': n, 'buy_value': $, 'sell_value': $}.

    ANALYST NOTE (DP-3C-c): 'rough size' is deliberate. Notional is shares x
    price-per-share summed over non-derivative transactions, which is an
    approximation — it ignores derivative tables and multi-lot averaging.
    Refining it is a later decision; over-precision here would imply a
    exactness the v1 extraction does not have.
    """
    out = {"buys": 0, "sells": 0, "buy_value": 0.0, "sell_value": 0.0,
           "awards": 0, "mechanical": 0, "plan_10b5_1": False, "role": ""}
    if not text:
        return out

    # ANALYST NOTE (2026-08-02, v1.1): a 10b5-1 sale is PRE-SCHEDULED — the
    #   insider set it up months earlier and it executes on a calendar, not on
    #   a view. Reporting it beside a discretionary open-market purchase
    #   implies information that is not there. Most insider SELLING is 10b5-1.
    #   Flagged, not filtered: the model is told which it is and can weigh it.
    if re.search(r"10b5-?1", text, re.I):
        out["plan_10b5_1"] = True

    title = re.search(r"<officerTitle>\s*([^<]{1,60})\s*</officerTitle>", text)
    if title:
        # XML escapes ampersands; "SVP &amp; Controller" reached the prompt raw.
        out["role"] = html.unescape(title.group(1)).strip()
    elif re.search(r"<isDirector>\s*(1|true)\s*</isDirector>", text, re.I):
        out["role"] = "Director"
    elif re.search(r"<isTenPercentOwner>\s*(1|true)\s*</isTenPercentOwner>", text, re.I):
        out["role"] = "10% owner"

    # Non-derivative table only. It precedes <derivativeTable> in the schema,
    # so truncating there confines the tally to actual share transactions.
    cut = text.find("<derivativeTable")
    scope = text[:cut] if cut != -1 else text

    codes  = _TXN_CODE_RE.findall(scope)
    shares = [float(s) for s in _TXN_SHARES_RE.findall(scope)]
    prices = [float(p) for p in _TXN_PRICE_RE.findall(scope)]

    for i, code in enumerate(codes):
        qty = shares[i] if i < len(shares) else 0.0
        px  = prices[i] if i < len(prices) else 0.0
        if code in FORM4_BUY_CODES:
            out["buys"] += 1
            out["buy_value"] += qty * px
        elif code in FORM4_SELL_CODES:
            out["sells"] += 1
            out["sell_value"] += qty * px
        elif code in FORM4_AWARD_CODES:
            out["awards"] += 1
        elif code in FORM4_MECH_CODES:
            out["mechanical"] += 1
    return out


def _fetch_form4_xml(cik10, accession, primary_document):
    """Return the RAW ownership XML for one Form 4.

    `primaryDocument` in the submissions feed points at the XSL-RENDERED view
    ("xslF345X05/wf-form4_1754....xml"), which is a styled HTML table with no
    <transactionCode> elements at all. The raw XML lives at the accession root
    under the same filename. Strategy:
      1. strip the xsl* directory and try the bare filename  (0 extra requests)
      2. if that yields no <transactionCode>, read the filing index and take
         the first .xml that is not under an xsl* path        (1 extra request)
    Step 2 exists because the xsl directory name is versioned (F345X03, X05,
    ...) and the flat-filename assumption is not guaranteed to hold forever.
    """
    tried = []
    cands = []
    if "/" in primary_document:
        cands.append(primary_document.rsplit("/", 1)[-1])
    cands.append(primary_document)

    for cand in cands:
        text = fetch_document(cik10, accession, cand)
        tried.append((cand, len(text or ""), bool(text and "<transactionCode>" in text)))
        if text and "<transactionCode>" in text:
            log.debug("[EDGAR] form4 raw xml via %s", cand)
            return text

    idx = _http_get(FILING_INDEX_URL.format(
        cik=str(int(cik10)), accession_nodash=accession.replace("-", "")),
        as_json=True)
    items = ((idx or {}).get("directory") or {}).get("item") or []
    for it in items:
        name = str(it.get("name", ""))
        if name.lower().endswith(".xml") and not name.lower().startswith("xsl"):
            text = fetch_document(cik10, accession, name)
            tried.append((name, len(text or ""), bool(text and "<transactionCode>" in text)))
            if text and "<transactionCode>" in text:
                log.debug("[EDGAR] form4 raw xml via index: %s", name)
                return text

    log.info("[EDGAR] form4 %s: no ownership XML found; tried %s",
             accession, tried)
    return None


def _is_ownership_xml(text):
    return bool(text) and ("<ownershipDocument" in text or "<transactionCode>" in text)


def _fetch_form4_xml(cik10, accession, primary_document):
    """Locate and fetch the RAW Form 4 ownership XML.

    `primaryDocument` points at the XSL-RENDERED view —
    "xslF345X05/wf-form4_1754....xml" — which is a styled HTML table with no
    <transactionCode> elements anywhere. Stripping the xsl directory usually
    yields the raw XML, but the naming is not guaranteed, so a failed guess
    falls through to the filing index and picks the real ownership document.
    Guess first (zero extra requests when it works), discover second.
    """
    tried = []

    if "/" in primary_document:
        cand = primary_document.split("/")[-1]
        tried.append(cand)
        text = fetch_document(cik10, accession, cand,
                              validator=_is_ownership_xml)
        if _is_ownership_xml(text):
            return text

    idx = _http_get(FILING_INDEX_URL.format(
        cik=str(int(cik10)), accession_nodash=accession.replace("-", "")),
        as_json=True)
    items = ((idx or {}).get("directory") or {}).get("item") or []
    xmls = [it.get("name", "") for it in items
            if str(it.get("name", "")).lower().endswith(".xml")
            and not str(it.get("name", "")).lower().startswith("xsl")
            and "-index" not in str(it.get("name", "")).lower()]
    # prefer a form4-looking name, else the largest .xml
    xmls.sort(key=lambda n: (0 if "form4" in n.lower() or "form345" in n.lower()
                             else 1, n))
    for name in xmls:
        if name in tried:
            continue
        tried.append(name)
        text = fetch_document(cik10, accession, name,
                              validator=_is_ownership_xml)
        if _is_ownership_xml(text):
            return text

    if primary_document not in tried:
        text = fetch_document(cik10, accession, primary_document,
                              validator=_is_ownership_xml)
        if _is_ownership_xml(text):
            return text
    return None


def extract_form4(rows, since, cik10, fetch=True):
    """Net insider buy/sell tally in the window.

    Degrades in two stages: full direction (documents fetched) -> count only
    (budget exceeded or fetch failed) -> nothing. The stage reached is
    reported in the returned dict so the prompt section never implies a
    direction it did not compute.
    """
    hits = [r for r in rows
            if r["form"] in FORM4_FORMS and _within_window(r["filingDate"], since)]

    result = {"filings": len(hits), "buys": 0, "sells": 0,
              "buy_value": 0.0, "sell_value": 0.0, "roles": [],
              "awards": 0, "mechanical": 0,
              "plan_filings": 0, "direction": None, "detail": "count-only",
              # DP-3C-i (2026-08-03): the DATE of the most recent Form 4 of
              # ANY transaction code — including grants (A), option exercises
              # (M) and tax withholding (F), none of which move direction —
              # because edgar_cache\ is gitignored and deletable, so window
              # membership for E4-2's ADJACENT/COVERED-QUIET split survives
              # nowhere else durable. Comes from the submissions index, so it
              # is available even in count-only mode (no document fetch).
              "dates": sorted((r["filingDate"] for r in hits), reverse=True)}

    if not hits or not fetch:
        return result

    if len(hits) > MAX_FORM4_DOCS:
        log.info("[EDGAR] %s Form 4s in window exceeds the %s-document budget "
                 "— reporting count only.", len(hits), MAX_FORM4_DOCS)
        return result

    parsed_any = False
    codes_seen = 0
    for r in hits:
        doc = r.get("primaryDocument") or ""
        if not doc:
            continue

        # ANALYST NOTE (2026-08-02, DEFECT FOUND ON THE FIRST LIVE --ticker RUN):
        #   `primaryDocument` for a Form 4 is the XSL-RENDERED HTML wrapper —
        #   "xslF345X05/wf-form4_1754....xml" — not the raw ownership XML. The
        #   rendered version has no <transactionCode> elements at all (it is a
        #   styled table), so every parse returned zero transactions while the
        #   10b5-1 footnote text still matched, producing "0 buys / 0 sells"
        #   beside "5 of 5 under a 10b5-1 plan". The raw XML sits at the same
        #   accession root under the filename AFTER the slash. Try raw first,
        #   fall back to the rendered path.
        text = _fetch_form4_xml(cik10, r["accessionNumber"], doc)
        if not text:
            continue
        parsed_any = True
        codes_seen += text.count("<transactionCode>")
        p = parse_form4_xml(text)
        result["buys"]       += p["buys"]
        result["sells"]      += p["sells"]
        result["buy_value"]  += p["buy_value"]
        result["sell_value"] += p["sell_value"]
        result["awards"]     += p["awards"]
        result["mechanical"] += p["mechanical"]
        if p["plan_10b5_1"]:
            result["plan_filings"] += 1
        if p["role"] and p["role"] not in result["roles"]:
            result["roles"].append(p["role"])

    if parsed_any:
        result["codes_seen"] = codes_seen
        if result["buys"] == 0 and result["sells"] == 0:
            # Filings exist but contain no open-market acquisition or
            # disposition — typically option exercises (M) and tax withholding
            # (F), both mechanical. Say that; do NOT say "mixed", which asserts
            # transactions in both directions that were never observed.
            result["detail"] = ("no open-market buy/sell transactions "
                                if codes_seen else "transactions not extracted")
            result["direction"] = None
        else:
            result["detail"] = "parsed"
            if result["buys"] > result["sells"]:
                result["direction"] = "buying"
            elif result["sells"] > result["buys"]:
                result["direction"] = "selling"
            else:
                result["direction"] = "mixed"
    return result


# =============================================================================
# EXTRACTION — latest periodic + MD&A
# =============================================================================

_TAG_RE     = re.compile(r"<[^>]+>")
_WS_RE      = re.compile(r"\s+")
# The heading runs "Item 2. Management's Discussion and Analysis of Financial
# Condition and Results of Operations (MD&A)". Matching only as far as
# "Management's Discussion" left the remainder of the TITLE as the first words
# of the extract — RTX opened with "and Analysis of Financial Condition and
# Results of Operations BUSINESS OVERVIEW ...". Consume the full title,
# including an optional parenthetical, so the slice begins at real content.
_MDA_START  = re.compile(
    r"item\s*[27][^a-z0-9]{0,8}.{0,80}?management[\u2019'`\s]*s\s+discussion"
    r"(?:\s+and\s+analysis)?"
    r"(?:\s+of\s+financial\s+condition)?"
    r"(?:\s+and\s+results\s+of\s+operations)?"
    r"(?:\s*\(\s*(?:MD&A|MD&amp;A)\s*\))?",
    re.I | re.S)
# ANALYST NOTE (2026-08-02, live run): the opening paragraphs of an MD&A are
#   almost entirely NAVIGATIONAL — "should be read in conjunction with", "is
#   provided as a supplement to", "for a discussion of the year ended ...
#   refer to". WMT's live extract was 100% of this and carried no financial
#   content whatsoever. Drop sentences matching these markers before taking
#   the slice; what remains is the substantive discussion.
_MDA_NAV_RE = re.compile(
    r"(should be read in conjunction|is provided as a supplement|"
    r"please refer to Part|refer to Part I|contained in our Annual Report|"
    r"is intended to help the reader|accompanying notes included in|"
    r"forward[- ]looking statements? (can|may) (also )?be identified|"
    r"words such as|similar (words and )?(terms|phrases)|"
    r"(assumes|undertakes) no obligation|"
    r"not (a )?guarantee(s)? of future|undue reliance|"
    r"for (information|a discussion|further discussion|additional)\b|"
    r"refer to\b[^.]{0,60}(below|above|Item|Note|Part)|"
    r"for a discussion of the (year|three months) ended)", re.I)

_MDA_END    = re.compile(
    r"item\s*[38][^a-z0-9]{0,8}.{0,60}?(quantitative|financial\s+statements|"
    r"controls\s+and\s+procedures)", re.I | re.S)


def html_to_text(raw):
    """Crude but adequate HTML -> text. No lxml/bs4 dependency."""
    if not raw:
        return ""
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def extract_mda(raw_html, max_chars=MDA_MAX_CHARS):
    """Bounded MD&A extract (DP-3C-a default: bounded, no extra LLM call).

    ANALYST NOTE: this looks for 'Item 2 / Item 7 ... Management's Discussion'
    and takes the SECOND occurrence when there are two, because the first is
    almost always the table-of-contents line. If no heading is found we return
    "" and the caller falls back to a RECENCY FLAG — form type plus filed
    date, with no extract. That fallback is the honest degradation: a wrong
    1,200-character slice is worse than no slice.
    """
    text = html_to_text(raw_html)
    if not text:
        return ""

    starts = [m.end() for m in _MDA_START.finditer(text)]
    if not starts:
        return ""
    start = starts[1] if len(starts) > 1 else starts[0]

    tail = text[start:start + max_chars * 12]

    # ANALYST NOTE (2026-08-02, v1.1): the first 1,000-odd characters after the
    #   MD&A heading are almost always the forward-looking-statements
    #   cautionary paragraph — identical filing to filing, zero signal. Prefer
    #   the "Results of Operations" subsection when it is present; otherwise
    #   skip past the boilerplate marker. Falls back to the raw head if
    #   neither is found, which is the old behaviour.
    # Always trim a forward-looking-statements block, whichever branch runs.
    tail = _skip_boilerplate(tail, scan=2500)

    ro = None
    for m in re.finditer(r"results\s+of\s+operations", tail, re.I):
        before = tail[max(0, m.start() - 30):m.start()].lower()
        if ("condition and" in before or "analysis of" in before
                or "refer to" in before or "see " in before):
            continue                      # a title cross-reference, not the section
        ro = m
        break
    if ro and ro.start() < max_chars * 8:
        tail = tail[ro.end():]
    else:
        tail = _skip_boilerplate(tail)
    end_m = _MDA_END.search(tail)
    body = tail[:end_m.start()] if end_m else tail

    # A slice can still open mid-sentence when a jump lands inside one. If the
    # first character is lowercase, the opening fragment is orphaned text —
    # drop to the next sentence boundary rather than feed the model a
    # half-clause it cannot parse.
    # ANALYST NOTE (2026-08-02, JPM): a 10-Q INDEX is not caught by the
    #   digit-density guard, because "Item 1. Legal Proceedings. 179" is full
    #   of periods. JPM's extract opened with ~380 characters of index before
    #   reaching the consolidated financial highlights. Three or more "Item N."
    #   entries in the head is an index; cut past the last one and its page
    #   reference. Trim rather than reject — the content after it is good.
    idx = list(re.finditer(r"Item\s+\d+[A-Z]?\.", body[:1800]))
    if len(idx) >= 3:
        cut = idx[-1].end()
        pg = re.match(r".{0,80}?\s\d{1,4}\s+", body[cut:cut + 120])
        body = body[cut + (pg.end() if pg else 0):]
        body = re.sub(r"^\d{1,4}\s+", "", body)      # stray leading page no.

    body = body.lstrip(" ,;:\u2014-\u201c\u201d\"'")
    if body[:1].islower():
        cut = re.search(r"[.!?]\s+", body)
        if cut and cut.end() < len(body) * 0.6:
            body = body[cut.end():]

    # Drop navigational sentences, keep the substance.
    sentences = re.split(r"(?<=[.!?])\s+", body)
    kept = [x for x in sentences if not _MDA_NAV_RE.search(x)]
    if kept:
        body = " ".join(kept)

    body = body.strip()
    # A table of contents survives sentence filtering because it contains
    # almost no sentences — JPM rendered its MD&A index as the extract ("9
    # Consolidated Balance Sheets and Cash Flows Analysis 12 Explanation and
    # Reconciliation 15 ..."). Detect it by digit density against sentence
    # count and return nothing rather than present an index as content.
    # ANALYST NOTE (2026-08-02): the first version of this guard rejected on
    #   digit density alone and deleted DOW's MD&A — a genuine net-sales table
    #   ("Net sales $ 12,092 $ 10,104"), which is exactly the content worth
    #   keeping. A table of contents is digit-dense AND carries no currency or
    #   percent markers, because its numbers are page references. That is the
    #   discriminator; density alone is not.
    sample = body[:400]
    if sample:
        digits = sum(c.isdigit() for c in sample)
        looks_financial = ("$" in sample or "%" in sample)
        if (digits / len(sample) > 0.06 and sample.count(".") < 4
                and not looks_financial):
            return ""

    if len(body) > max_chars:
        body = body[:max_chars].rsplit(" ", 1)[0] + " …"
    return body


def extract_periodic(rows, cik10, fetch=True):
    """Latest 10-Q or 10-K: form, filed date, accession, bounded MD&A extract."""
    periodic = [r for r in rows if r["form"] in PERIODIC_FORMS]
    if not periodic:
        return {"form": None, "filed": None, "mda": "", "accession": None}

    latest = max(periodic, key=lambda r: r["filingDate"] or "")
    out = {"form": latest["form"], "filed": latest["filingDate"], "mda": "",
           "report": latest.get("reportDate") or "",
           "accession": latest.get("accessionNumber")}

    if fetch and latest.get("primaryDocument"):
        raw = fetch_document(cik10, latest["accessionNumber"],
                             latest["primaryDocument"])
        out["mda"] = extract_mda(raw)
    return out


# =============================================================================
# EXTRACTION — financial statements (XBRL companyfacts)
# =============================================================================

def _fmt_money(v):
    a = abs(v)
    if a >= 1e9:  return f"${v / 1e9:,.1f}B"
    if a >= 1e6:  return f"${v / 1e6:,.1f}M"
    if a >= 1e3:  return f"${v / 1e3:,.1f}K"
    return f"${v:,.2f}"


def _duration_days(e):
    try:
        a = datetime.strptime(e["start"], "%Y-%m-%d").date()
        b = datetime.strptime(e["end"], "%Y-%m-%d").date()
        return (b - a).days
    except (KeyError, ValueError, TypeError):
        return None


def _bucket(days):
    """Collapse a reporting duration to a period type. XBRL durations wobble by
    a few days around quarter ends, so exact matching would split identical
    periods; bucketing keeps a 91-day and an 89-day quarter together while
    still separating a quarter from a half-year."""
    if days is None:
        return None
    for n, name in ((95, "Q"), (190, "H"), (285, "9M"), (400, "FY")):
        if days <= n:
            return name
    return "LT"


def _pick_periods(entries, kind, anchor=None):
    """Latest reported period plus the year-ago comparable.

    ANALYST NOTE: the year-ago match is the whole point and the easy thing to
    get wrong. For FLOW items (revenue, net income) the comparable must have
    the SAME DURATION — comparing a quarter against a trailing nine-month
    figure produces a nonsense growth rate, and both appear in the same
    companyfacts array. Duration is matched within 20 days and the end date
    within 45 days of one year prior; if nothing matches, the prior is left
    None and NO growth figure is printed rather than an approximate one.
    """
    rows = [e for e in entries
            if e.get("form") in XBRL_FORMS and e.get("val") is not None
            and e.get("end")]
    if not rows:
        return None, None

    if kind == "flow":
        rows = [e for e in rows if e.get("start")]
        if not rows:
            return None, None

    rows.sort(key=lambda e: e["end"])

    if anchor and kind == "flow":
        # Prefer the anchor's exact period; fall back to ANY period ending on
        # the anchor date. Cash-flow items are reported year-to-date by
        # convention — RTX tags operating cash flow only for H/9M/FY, never a
        # standalone quarter — so a strict duration match would silently
        # delete a genuinely current and useful line. Current-but-different is
        # kept and LABELLED; stale is dropped by the caller.
        exact = [e for e in rows
                 if e.get("end") == anchor[0]
                 and _bucket(_duration_days(e)) == anchor[1]]
        same_end = [e for e in rows if e.get("end") == anchor[0]]
        if exact:
            latest = exact[-1]
        elif same_end:
            latest = max(same_end, key=lambda e: _duration_days(e) or 0)
        else:
            return None, None
    elif kind == "flow":
        # N-1 (found 2026-08-03, live on PWR/FTI/GM/PM/RTX/AAPL): this branch
        # runs during the Pass-1 anchor VOTE, before any anchor exists. A 10-Q
        # tags the standalone quarter AND the six-month-to-date figure for the
        # same concept, both ending on the SAME date — sorting by end date
        # alone leaves them tied, and `rows[-1]` picked whichever happened to
        # sort last, which is duration-blind and let the cumulative bucket
        # outvote the quarter it contains. A filer whose quarterly earnings
        # release plainly reports $9.6B was rendered with a $17.4B "revenue"
        # figure carrying no indication it was six months, not three.
        #
        # Fix: among entries sharing the latest end date, prefer the SHORTEST
        # duration — the standalone quarter, when the filer tags one for this
        # concept. A concept that is ONLY ever reported cumulatively (cash
        # flow, by convention — see the anchor branch above) has no shorter
        # alternative at that end date, so this falls through to it unchanged
        # and the [6M YTD]/[9M YTD] label still fires downstream when THIS
        # concept's own vote does not win the plurality.
        max_end = rows[-1]["end"]
        tied = [e for e in rows if e.get("end") == max_end]
        latest = min(tied, key=lambda e: _duration_days(e) if _duration_days(e) is not None else 10**9)
    else:
        latest = rows[-1]

    prior = None
    try:
        l_end = datetime.strptime(latest["end"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return latest, None
    l_dur = _duration_days(latest) if kind == "flow" else None

    best = None
    for e in rows[:-1]:
        try:
            e_end = datetime.strptime(e["end"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        gap = abs((l_end - e_end).days - 365)
        if gap > 45:
            continue
        if kind == "flow":
            d = _duration_days(e)
            if d is None or l_dur is None or abs(d - l_dur) > 20:
                continue
        if best is None or gap < best[0]:
            best = (gap, e)
    if best:
        prior = best[1]
    return latest, prior


def _all_entries(gaap):
    for concept in gaap.values():
        for entries in (concept.get("units") or {}).values():
            for e in entries:
                yield e


def _has_entry_at(gaap, end):
    return any(e.get("end") == end and e.get("form") in XBRL_FORMS
               for e in _all_entries(gaap))


def _modal_flow_bucket(gaap, end):
    """Most common duration bucket among duration-typed entries ending on
    `end`. Returns None when only instants report there."""
    counts = {}
    for e in _all_entries(gaap):
        if e.get("end") != end or e.get("form") not in XBRL_FORMS:
            continue
        if not e.get("start"):
            continue
        b = _bucket(_duration_days(e))
        if b:
            counts[b] = counts.get(b, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else None


# Duration buckets, shortest first. Ties in the headline vote break toward the
# SHORTEST period, matching _pick_periods' own tie-break: when a filer tags
# both a quarter and the cumulative period containing it, the quarter is the
# statement and the cumulative figure is the supplement.
_BUCKET_ORDER = ("Q", "H", "9M", "FY", "LT")


def _headline_flow_bucket(gaap, end):
    """Modal duration bucket among the HEADLINE concepts reporting at `end`.

    One vote per statement LINE, not per XBRL entry, and each line votes for
    the SHORTEST duration it has available at that date — the same choice
    _pick_periods makes for that concept once the anchor is known.

    ANALYST NOTE (2026-08-10, N-1 SECOND ROUTE, found live on RTX): the
    report-date override in extract_financials() used _modal_flow_bucket,
    which polls EVERY us-gaap concept in companyfacts — hundreds of footnote,
    segment and supplementary tags, not the ~6 that can become rendered
    lines. A 10-Q tags those year-to-date far more often than quarterly:
    RTX's own feed at 2026-06-30 runs H:70 against Q:39. So the universe-wide
    poll elected H and OVERRODE a headline vote that had correctly gone 4-1
    for Q, and the block rendered six-month revenue ($46.8B) under a "Q2"
    header with no [6M YTD] label — the exact N-1 symptom the 2026-08-03 fix
    was written to kill, arriving by a completely different route.

    The anchor exists to describe the lines that get RENDERED, so only
    concepts that can become lines get a vote. _modal_flow_bucket is retained
    as the fallback for the case it was actually written for (2026-08-02,
    GLD): a filer that tags almost no headline flows at its own report date.
    """
    counts = {}
    for _label, kind, concepts in FINANCIAL_CONCEPTS:
        if kind != "flow":
            continue
        for c in concepts:                    # preference order, as Pass 2 uses
            if c not in gaap:
                continue
            units = gaap[c].get("units") or {}
            unit_key = (next((u for u in ("USD", "USD/shares") if u in units), None)
                        or next(iter(units), None))
            if not unit_key:
                continue
            here = [e for e in units[unit_key]
                    if e.get("end") == end and e.get("form") in XBRL_FORMS
                    and e.get("start") and e.get("val") is not None]
            if not here:
                continue                      # try the next concept in the list
            shortest = min(here, key=lambda e: _duration_days(e)
                           if _duration_days(e) is not None else 10**9)
            b = _bucket(_duration_days(shortest))
            if b:
                counts[b] = counts.get(b, 0) + 1
            break                             # this line item is decided
    if not counts:
        return None
    top = max(counts.values())
    tied = [b for b, n in counts.items() if n == top]
    return min(tied, key=lambda b: _BUCKET_ORDER.index(b)
               if b in _BUCKET_ORDER else len(_BUCKET_ORDER))


def _select_concept(gaap, concepts, kind, anchor=None):
    """Choose which us-gaap concept to use for one line item.

    ANALYST NOTE (2026-08-02, DEFECT FOUND ON THE NVDA DUMP): selection was
    `first concept present in the facts`. NVDA still carries
    RevenueFromContractWithCustomerExcludingAssessedTax, but its most recent
    entry is FY2022 — the company moved to a different tag years ago. The
    selector locked onto the fossil, the staleness rule then correctly dropped
    it, and NVDA rendered a statement block with NO REVENUE LINE while a
    current concept sat unused two positions down the fallback list.

    Presence is not currency. With an anchor known, take the first concept in
    PREFERENCE order that reports at that period; without one (the anchor
    vote), take whichever concept has the most recent data.
    """
    best = None
    for c in concepts:
        if c not in gaap:
            continue
        units = gaap[c].get("units") or {}
        unit_key = (next((u for u in ("USD", "USD/shares") if u in units), None)
                    or next(iter(units), None))
        if not unit_key:
            continue
        latest, prior = _pick_periods(units[unit_key], kind,
                                      anchor=anchor if kind == "flow" else None)
        if not latest:
            continue
        if anchor:
            if latest.get("end") != anchor[0]:
                continue
            return c, unit_key, latest, prior      # preference order wins
        if best is None or (latest.get("end") or "") > (best[2].get("end") or ""):
            best = (c, unit_key, latest, prior)
    return best


# DP-3C-q (RULED - RW 2026-08-11). For the REVENUE line only, prefer the
# total-revenue concept when the filer tags it at the anchor period AND it is
# materially larger than the ASC 606 contract-revenue concept.
#
# EVIDENCE OF RECORD: GM tags RevenueFromContractWithCustomerExcludingAssessed-
# Tax at $43.762B for Q2 FY2026 and Revenues at $48.026B for the SAME period.
# GM's own 8-K states "revenue of $48.0 billion" -- the total concept matches
# the press release to 0.05% and the contract concept is 9.7% below it. ASC 606
# contract revenue excludes GM Financial's interest and leasing income, so for
# any filer with a captive finance arm the first entry in the preference list
# is a COMPONENT rendered under the label "Revenue". Found 2026-08-11 by the
# 8-K cross-check in xbrl_sweep.py; the period was CORRECT, which is what
# makes this a different defect class from N-1 and invisible to every
# internal-coherence check (GM's block passes BALANCE at 0.58% and SHARES at
# 925.5M implied).
#
# SCOPE IS DELIBERATELY NARROW. Reordering FINANCIAL_CONCEPTS outright would
# change what the model sees for every covered name on evidence from one. The
# swap fires only when the total is MATERIALLY LARGER, so it is a no-op where
# the filer tags one concept, tags them equal, or tags a smaller Revenues --
# confirmed across the other 14 covered names by the 2026-08-11 sweep, none of
# which raised a revenue SCOPE finding.
#
# TIMING: ruled before the E4 clock starts, so amending costs nothing. The
# same change after go-live would alter the treatment mid-measurement. This is
# the DP-3C-g argument applied a third time.
TOTAL_REVENUE_CONCEPT = "Revenues"
TOTAL_REVENUE_MARGIN = 0.02


def _prefer_total_revenue(gaap, chosen, unit_key, latest, prior, anchor):
    """Swap a contract-revenue component for the filer's total revenue.

    Returns the selection unchanged unless every condition holds: the total
    concept exists, reports at the ANCHOR period (not merely somewhere), and
    exceeds the chosen figure by more than TOTAL_REVENUE_MARGIN. The prior is
    re-derived from the total concept's OWN history so the year-over-year is
    computed on one consistent basis rather than mixing the two.
    """
    if chosen == TOTAL_REVENUE_CONCEPT or TOTAL_REVENUE_CONCEPT not in gaap:
        return chosen, unit_key, latest, prior
    units = gaap[TOTAL_REVENUE_CONCEPT].get("units") or {}
    key = (next((u for u in ("USD", "USD/shares") if u in units), None)
           or next(iter(units), None))
    if not key:
        return chosen, unit_key, latest, prior

    tot_latest, tot_prior = _pick_periods(units[key], "flow", anchor=anchor)
    if not tot_latest or tot_latest.get("val") is None:
        return chosen, unit_key, latest, prior
    # Must describe the SAME period. A total tagged at a different date is a
    # different measurement, and swapping it in would reintroduce exactly the
    # mixed-period defect this file spent 2026-08-10 removing.
    if anchor and tot_latest.get("end") != anchor[0]:
        return chosen, unit_key, latest, prior

    cur = latest.get("val")
    if cur is None or cur <= 0:
        return chosen, unit_key, latest, prior
    if tot_latest["val"] <= cur * (1 + TOTAL_REVENUE_MARGIN):
        return chosen, unit_key, latest, prior

    log.info("[EDGAR] revenue: %s (%s) supersedes %s (%s) at %s per DP-3C-q",
             TOTAL_REVENUE_CONCEPT, f"{tot_latest['val']:,}",
             chosen, f"{cur:,}", tot_latest.get("end"))
    return TOTAL_REVENUE_CONCEPT, key, tot_latest, tot_prior


def extract_financials(cik10, latest_accession=None, fetch=True, facts=None,
                       report_date=None):
    """Headline financial statement lines from XBRL, with year-over-year.

    Cached by the LATEST PERIODIC ACCESSION, not by date: companyfacts is a
    large document and only changes when a new periodic is filed, so this is
    a quarterly cost per ticker rather than a daily one. Only the small
    extracted summary is written to disk — never the raw multi-megabyte feed.
    """
    out = {"schema": EXTRACT_SCHEMA, "lines": [], "period": None,
           "fy": None, "fp": None, "source": None,
           # DP-3C-j (2026-08-03): distinguish a fetch the run BUDGET cut
           # short from a ticker that genuinely has no XBRL. Both used to
           # render as a silently omitted `fin=` tag — a tool reporting a
           # value it did not compute for two different reasons. Only set
           # True below, at the point the distinction is actually knowable.
           "degraded": False}

    cache_file = None
    if latest_accession:
        cache_file = os.path.join(
            EDGAR_CACHE_DIR, f"fin_{latest_accession.replace('-', '')}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("schema") == EXTRACT_SCHEMA:
                    return cached
                log.info("[EDGAR] financials cache schema %s != %s — recomputing",
                         cached.get("schema"), EXTRACT_SCHEMA)
            except (OSError, ValueError, AttributeError):
                pass

    if facts is None:
        if not fetch:
            return out
        facts = _http_get(XBRL_FACTS_URL.format(cik10=cik10), as_json=True)
    if not facts:
        # budget_exceeded() is already True at this point iff the run clock
        # tripped it — checking, not tripping, it a second time. KNOWN LIMIT:
        # if the budget happened to trip for unrelated reasons in the same
        # window a genuinely-filing-less ticker was also fetched, this reads
        # "degraded" rather than "none" — the two are not perfectly
        # separable from here without instrumenting _http_get itself, which
        # is out of scope for this fix. Recorded rather than hidden.
        out["degraded"] = budget_exceeded()
        return out

    gaap = (facts.get("facts") or {}).get("us-gaap") or {}

    # ANALYST NOTE (2026-08-02, DEFECT FOUND ON THE LIVE RTX RUN):
    #   concepts were selected INDEPENDENTLY, so one line could resolve to the
    #   three-month figure and the next to the six-month, and the header stamped
    #   whichever line happened to come first. RTX rendered operating income
    #   ($2.8B) LARGER THAN gross profit ($2.2B) — arithmetically impossible
    #   within one period, and the only reason it was visible at all. A mixed
    #   block is worse than a missing one: every number is real, so nothing
    #   looks wrong unless you check the arithmetic.
    #
    #   Fix: establish ONE anchor period from the flow items — the (end,
    #   duration) pair reported by the most concepts — then admit only lines
    #   that match it. Non-conforming lines are DROPPED, not adjusted.
    # Pass 1 — establish the anchor period, choosing per label the concept
    # with the MOST RECENT data rather than the first one merely present.
    votes = {}
    for label, kind, concepts in FINANCIAL_CONCEPTS:
        if kind != "flow":
            continue
        sel = _select_concept(gaap, concepts, kind, anchor=None)
        if not sel:
            continue
        _c, _u, latest, _p = sel
        key = (latest.get("end"), _bucket(_duration_days(latest)))
        votes[key] = votes.get(key, 0) + 1
    anchor = max(votes.items(), key=lambda kv: (kv[1], kv[0][0]))[0] if votes else None

    # ANALYST NOTE (2026-08-02, GLD): the vote is a majority of FLOW concepts,
    #   which fails when a filer tags almost no flows. GLD's only flow concept
    #   reporting at 2026-03-31 was an operating-cash-flow placeholder tagged 0
    #   in every period ever filed — so a zero placeholder chose the anchor and
    #   the balance sheet was the only real content left. When the filing's own
    #   report date is known and ANY concept reports there, that date is a
    #   better anchor than a vote among however many concepts happen to exist.
    # ANALYST NOTE (2026-08-10): the DATE override is what fixed GLD and is
    #   kept. The BUCKET is now decided by the headline concepts that can
    #   actually become rendered lines (_headline_flow_bucket) rather than by
    #   a poll of every tag in companyfacts, which on RTX let 70 year-to-date
    #   footnote entries overrule a 4-1 headline vote for the quarter. See
    #   _headline_flow_bucket. _modal_flow_bucket remains the fallback for the
    #   filer shape it was written for — almost no headline flows at all.
    if report_date and _has_entry_at(gaap, report_date):
        bucket = (_headline_flow_bucket(gaap, report_date)
                  or _modal_flow_bucket(gaap, report_date)
                  or (anchor[1] if anchor else None))
        anchor = (report_date, bucket)

    # Pass 2 — with the anchor known, take the FIRST concept in preference
    # order that actually reports at that period.
    for label, kind, concepts in FINANCIAL_CONCEPTS:
        sel = _select_concept(gaap, concepts, kind, anchor=anchor)
        if not sel:
            continue                      # omit rather than guess
        chosen, unit_key, latest, prior = sel

        # DP-3C-q (RW 2026-08-11) -- revenue only; see _prefer_total_revenue.
        # Placed BEFORE the placeholder and staleness guards so the swapped
        # selection is subject to every one of them, not exempted from them.
        if label == "Revenue":
            chosen, unit_key, latest, prior = _prefer_total_revenue(
                gaap, chosen, unit_key, latest, prior, anchor)

        # A concept tagged 0 now and 0 a year ago is a PLACEHOLDER, not a
        # measurement — GLD carries operating cash flow as 0 in every period
        # it has ever filed. Rendering "$0.00" spends a line to say nothing
        # and, worse, made that concept eligible to set the anchor period.
        if latest.get("val") == 0 and (prior is None or prior.get("val") == 0):
            continue

        # STALENESS IS THE HARD RULE. Every line must end on the anchor date.
        # RTX stopped tagging GrossProfit after FY2020 and LongTermDebt after
        # FY2024; without this, the client rendered a 2020 quarter and a 2024
        # balance as though they were current — real numbers, five years old,
        # with a year-over-year computed off them.
        if anchor and latest.get("end") != anchor[0]:
            continue

        period_note = None
        if anchor and kind == "flow":
            b = _bucket(_duration_days(latest))
            if b != anchor[1]:
                period_note = {"Q": "quarter", "H": "6M YTD",
                               "9M": "9M YTD", "FY": "full year"}.get(b, b)

        # ANALYST NOTE (2026-08-02, found on the 20-ticker sweep): a percent
        #   change is only meaningful when BOTH endpoints are positive. CORN
        #   went from about -$3.1M to +$30.4M and rendered "YoY -1077.9%" — a
        #   large improvement displayed as a collapse. DOW, JPM, PM and SND all
        #   produced the same shape on negative bases. The arithmetic is
        #   correct and the meaning is inverted, which is the worst combination
        #   for an input a model reasons from. Below zero, show the prior VALUE
        #   and let the model do the comparison itself.
        yoy = None
        prior_display = None
        if prior and prior.get("val") is not None:
            pv, lv = prior["val"], latest["val"]
            if pv > 0 and lv > 0:
                yoy = (lv / pv - 1) * 100
            elif pv != lv:
                prior_display = pv

        out["lines"].append({
            "label": label, "concept": chosen, "unit": unit_key,
            "value": latest["val"], "end": latest.get("end"),
            "yoy": yoy, "form": latest.get("form"),
            "prior": prior_display, "period_note": period_note})

        if out["period"] is None:
            out["period"] = latest.get("end")
            out["fy"], out["fp"] = latest.get("fy"), latest.get("fp")
            out["source"] = latest.get("form")

    out["dropped"] = _consistency_filter(out["lines"])

    if cache_file and out["lines"]:
        try:
            os.makedirs(EDGAR_CACHE_DIR, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(out, f)
        except OSError:
            pass
    return out


# Accounting identities that hold for any single consolidated period. These
# are not heuristics — they are definitional, and a violation proves the lines
# are not describing what their labels say.
_IDENTITIES = [
    ("Gross profit", "Revenue", "gross profit exceeds revenue"),
    ("Operating income", "Gross profit", "operating income exceeds gross profit"),
]


def _consistency_filter(lines):
    """Drop lines that violate a definitional accounting identity.

    ANALYST NOTE (2026-08-02): RTX rendered operating income ($2.8B) larger
    than gross profit ($2.2B) for the same quarter, which cannot happen —
    operating income IS gross profit less operating expenses. The first
    hypothesis (mixed reporting periods) was WRONG: both lines match the
    anchor period, so something else is off in how RTX tags GrossProfit.

    The cause is not yet known, and that is exactly why this guard exists.
    When an identity fails we cannot tell WHICH line is wrong, so the
    dependent, optional line is dropped rather than the primary one — revenue
    and operating income are tagged near-universally and consistently, gross
    profit is neither. Dropping is the honest move: an omitted line is a gap,
    a wrong one is a false input the model will reason from. Use
    `--xbrl TICKER` to see what was actually tagged.
    """
    by_label = {ln["label"]: ln for ln in lines}
    dropped = []
    for dependent, primary, why in _IDENTITIES:
        d, pr = by_label.get(dependent), by_label.get(primary)
        if not d or not pr:
            continue
        if d["unit"] == "USD/shares" or pr["unit"] == "USD/shares":
            continue
        # Each identity is stated as: dependent <= primary. A violation is
        # simply dependent > primary; the earlier lo/hi swap inverted the
        # comparison for the operating-income case and the guard never fired.
        if d["value"] > pr["value"]:
            victim = "Gross profit"
            if victim in by_label:
                dropped.append({"label": victim, "reason": why,
                                "value": by_label[victim]["value"]})
                lines.remove(by_label.pop(victim))
    return dropped


def format_financials(fin, max_lines=len(FINANCIAL_CONCEPTS), periodic=None):
    """Compact statement block for the prompt section."""
    if not fin or not fin["lines"]:
        return []
    hdr = f"Financial statements (XBRL, {fin.get('source') or 'periodic'}"
    if fin.get("fy"):
        fp = fin.get("fp")
        hdr += f" FY{fin['fy']}" if fp in (None, "", "FY") else f" {fp} FY{fin['fy']}"
    if fin.get("period"):
        hdr += f", period ended {fin['period']}"
    lines = [hdr + "):"]

    # ANALYST NOTE (2026-08-02): SEC's XBRL feed can lag the filing itself. DOW
    #   showed "Latest periodic: 10-Q filed 2026-07-24" directly above a
    #   statement block for the period ended 2026-03-31 — the previous quarter,
    #   with nothing to say so. Both facts were right; the juxtaposition was
    #   silently misleading. Say it explicitly when the two disagree.
    if periodic and periodic.get("report") and fin.get("period"):
        if fin["period"] < periodic["report"]:
            lines.append(
                f"  NOTE: these are the PRIOR period's figures — XBRL data for "
                f"the {periodic.get('form')} covering {periodic['report']} is "
                f"not yet published by SEC.")

    for ln in fin.get("dropped", []):
        lines.append(f"  (a reported {ln['label'].lower()} figure was withheld: "
                     f"{ln['reason']} — tagging inconsistency)")

    # ANALYST NOTE (2026-08-02): max_lines was 8 while the concept list holds
    #   11, so RTX extracted 9 lines, rendered 8, and tagged fin=9. Cash and
    #   equivalents vanished with no indication. A silent truncation that
    #   disagrees with its own log tag is a small lie in the audit trail; the
    #   default now tracks the concept list, and any real overflow is stated.
    shown = fin["lines"][:max_lines]
    hidden = len(fin["lines"]) - len(shown)
    for ln in shown:
        v = (f"{ln['value']:,.2f}" if ln["unit"] == "USD/shares"
             else _fmt_money(ln["value"]))
        if ln["yoy"] is not None:
            yoy = f"  YoY {ln['yoy']:+.1f}%"
        elif ln.get("prior") is not None:
            pv = (f"{ln['prior']:,.2f}" if ln["unit"] == "USD/shares"
                  else _fmt_money(ln["prior"]))
            yoy = f"  vs {pv} prior year"
        else:
            yoy = ""
        note = f"  [{ln['period_note']}]" if ln.get("period_note") else ""
        lines.append(f"  {ln['label']:<22}{v:>12}{yoy}{note}")
    if hidden > 0:
        lines.append(f"  (+{hidden} further line item(s) not shown)")
    return lines


# =============================================================================
# SECTION ASSEMBLY
# =============================================================================

def build_filings_section(eightk, form4, periodic, as_of=None,
                          window=WINDOW_DAYS, financials=None):
    """Assemble the prompt section (Scope Spec §2). Text only.

    Returns "" when there is NOTHING to say — no 8-K, no Form 4, no periodic.
    An empty string contributes nothing to the prompt (see
    context_providers.run_prompt_context), which is the correct behaviour for
    the ETFs and commodity trusts that structurally lack these filings.
    """
    as_of = as_of or datetime.now(timezone.utc).date().isoformat()

    has_content = (eightk["count"] or form4["filings"] or periodic["form"]
                   or (financials and financials.get("lines")))
    if not has_content:
        return ""

    lines = [f"--- SEC FILINGS (recent, as of {as_of}) ---"]

    if eightk["count"]:
        lines.append(f"8-K (material events, last {window}d): {eightk['count']}")
        for ev in eightk.get("events", [])[:MAX_8K_DOCS]:
            head = f"  - {ev['date']} {'; '.join(ev['items'])}"
            lines.append(f"{head} — \"{ev['body']}\"" if ev.get("body") else head)
        extra = eightk["count"] - len(eightk.get("events", [])[:MAX_8K_DOCS])
        if extra > 0:
            lines.append(f"  - (+{extra} further 8-K(s) in window, not extracted)")
    else:
        lines.append(f"8-K (material events, last {window}d): 0")

    if form4["filings"]:
        if form4["direction"]:
            size = ""
            net = form4["buy_value"] - form4["sell_value"]
            if abs(net) >= 1000:
                size = f", net ~${abs(net):,.0f} {'bought' if net > 0 else 'sold'}"
            lines.append(
                f"Form 4 (insider, last {window}d): {form4['buys']} buys / "
                f"{form4['sells']} sells  (net direction: {form4['direction']}{size})")
            if form4.get("roles"):
                # Titles themselves contain commas ("President, Collins
                # Aerospace"), so a comma-joined list is unreadable.
                lines.append(f"  - filers: {'; '.join(form4['roles'][:5])}")
            plan = form4.get("plan_filings", 0)
            if plan:
                lines.append(
                    f"  - {plan} of {form4['filings']} filed under a 10b5-1 plan "
                    f"(pre-scheduled; weigh as weaker evidence of a view)")
        else:
            detail = form4.get("detail", "")
            if detail.startswith("no open-market"):
                bits = []
                if form4.get("awards"):
                    bits.append(f"{form4['awards']} grant/award")
                if form4.get("mechanical"):
                    bits.append(f"{form4['mechanical']} option-exercise or "
                                f"tax-withholding")
                what = " and ".join(bits) if bits else "non-trade"
                why = (f"no open-market purchases or sales ({what} entries only "
                       "\u2014 compensation mechanics, not a discretionary view)")
            elif detail.startswith("transactions not"):
                why = "transaction detail could not be read"
            else:
                why = "direction not extracted"
            lines.append(
                f"Form 4 (insider, last {window}d): {form4['filings']} filing(s); "
                f"{why}")
    else:
        lines.append(f"Form 4 (insider, last {window}d): none")

    if periodic["form"]:
        head = f"Latest periodic: {periodic['form']} filed {periodic['filed']}"
        if periodic["mda"]:
            lines.append(f"{head} — MD&A extract: \"{periodic['mda']}\"")
        else:
            lines.append(f"{head} (MD&A extract unavailable)")

    # Statements last: they are the densest block and the model reads the
    # narrative context above them first.
    lines.extend(format_financials(financials, periodic=periodic))

    return "\n".join(lines)


def edgar_tag(meta):
    """The E[...] log tag (Scope Spec §3), appended after B[...].

        E[8k=2@2026-07-23; form4=+3/-1@2026-07-30; periodic=10-Q@2026-05-01; fin=9@2026-06-30]

    DP-3C-i (2026-08-03): 8k= and form4= carry the date of the most recent
    filing of each type — ANY Form 4 transaction code, not just open-market
    buys/sells — because edgar_cache\\ is gitignored and deletable, so this
    tag is the only durable record of whether a signal was inside E4-2's
    K=5-trading-day ADJACENT window. Omitted when there is nothing of that
    type, exactly as before this amendment.

    DP-3C-j (2026-08-03): fin= is now always ONE of `fin=N@period`,
    `fin=degraded` (the run budget cut this ticker's fetch short) or
    `fin=none` (genuinely no financials extracted) — never silently omitted,
    which previously meant two different things with no way to tell them
    apart from the tag alone.

    ANALYST NOTE (E3): main.py appends this as a TRAILING tag on the log
    line, after B[...]. Verified 2026-08-02 against both parsers on synthetic
    3-C lines: analyze_log.py's summary_pattern absorbs trailing tags into
    its `reason` capture and parse_log_to_tracker.py's ACCOUNT_RE never reads
    past [HELD|SCOUT], so neither is disturbed. The era stamp must stay in
    the JSON prompt_variant field and OUT of the phase bracket — analyze_log
    hardcodes `DRY RUN(?: A)?\\]` and fails on anything else there.
    """
    if not meta or meta.get("skipped") or not meta.get("covered"):
        return "E[no filings]"
    eightk = meta.get("eightk", {})
    f4 = meta.get("form4", {})
    per = meta.get("periodic", {})

    eightk_dates = eightk.get("dates") or []
    parts = [f"8k={eightk.get('count', 0)}" +
             (f"@{eightk_dates[0]}" if eightk_dates else "")]

    f4_part = (f"form4=+{f4.get('buys', 0)}/-{f4.get('sells', 0)}"
              if f4.get("direction") else f"form4={f4.get('filings', 0)}f")
    f4_dates = f4.get("dates") or []
    if f4_dates:
        f4_part += f"@{f4_dates[0]}"
    parts.append(f4_part)

    if per.get("form"):
        parts.append(f"periodic={per['form']}@{per['filed']}")

    fin = meta.get("financials") or {}
    if fin.get("n_lines"):
        parts.append(f"fin={fin['n_lines']}@{fin.get('period')}")
    elif fin.get("degraded"):
        parts.append("fin=degraded")
    else:
        parts.append("fin=none")
    return "E[" + "; ".join(parts) + "]"


# =============================================================================
# THE PROVIDER
# =============================================================================

# ANALYST NOTE (2026-08-02): run_prompt_context() returns TEXT ONLY — it
#   discards meta by design (the context_providers.py contract), and Scope
#   Spec §8 requires context_providers.py to stay UNCHANGED. The E[...] log
#   tag needs the counts, so each call buffers its meta here and main.py
#   reads it back with last_meta().
#
#   The obvious alternative — stashing meta on the `caches` dict — DOES NOT
#   WORK RELIABLY, and the reason is a live trap worth recording:
#   run_prompt_context and run_blend_scores both call `p.fn(ticker, caches
#   or {})`. An EMPTY dict is falsy in Python, so `{} or {}` hands the
#   provider a THROWAWAY dict and any write is discarded. It happens to be
#   harmless in production (prefetch populates the caches before the first
#   provider call) but it means no provider can lazily warm an initially
#   empty cache. Flagged for the tooling backlog; not fixed here, because
#   Scope Spec §8 pins context_providers.py at "no change" for 3-C.
_LAST_META = {}


def reset_meta():
    """Clear the per-run E[...] tag buffer."""
    _LAST_META.clear()


def last_meta(ticker):
    """Meta from this run's edgar_context call for `ticker` (for the E tag)."""
    return _LAST_META.get((ticker or "").upper(), {})


def edgar_context(ticker, caches):
    """ContextProvider(mode="prompt") entry point.

    CONTRACT (context_providers.py): returns (text, meta). Never raises into
    the run; "" contributes nothing to the prompt.
    """
    meta = {"ticker": ticker, "covered": False, "skipped": False}
    try:
        tkr = (ticker or "").upper()

        # DP-3 — CBRS is excluded until the Q4 2026 Path-A review.
        if tkr in SKIP_TICKERS:
            meta.update({"skipped": True, "note": "DP-3: excluded from EDGAR"})
            return "", meta

        caches = caches if caches is not None else {}
        cik = load_cik_map(caches).get(tkr)
        if not cik:
            meta["note"] = "no CIK"
            return "", meta

        meta["cik"] = cik
        subs = fetch_submissions(cik, caches)
        if not subs:
            meta["note"] = "submissions unavailable"
            return "", meta

        rows  = _recent_rows(subs)
        since = _window_start()

        eightk   = extract_8k(rows, since, cik10=cik)
        form4    = extract_form4(rows, since, cik)
        periodic = extract_periodic(rows, cik)
        financials = extract_financials(cik, periodic.get("accession"),
                                        report_date=periodic.get("report"))

        section = build_filings_section(eightk, form4, periodic,
                                        financials=financials)

        meta.update({"covered": bool(section), "eightk": eightk,
                     "form4": form4, "periodic": periodic,
                     "financials": {"n_lines": len(financials["lines"]),
                                    "period": financials.get("period"),
                                    "degraded": financials.get("degraded", False)},
                     "forms_seen": sorted({r["form"] for r in rows})[:20]})
        return section, meta

    except Exception as e:                    # never raise into the run (E3)
        log.warning("[EDGAR] %s: context failed, degrading to no-EDGAR: %s",
                    ticker, e)
        meta["note"] = f"error: {e}"
        return "", meta
    finally:
        _LAST_META[(ticker or "").upper()] = meta


register(Provider("edgar", "prompt", edgar_context))


def prefetch_edgar_context(watchlist):
    """Warm the CIK map + submissions once per run. Mirrors
    main.prefetch_blend_context. Returns the caches dict."""
    reset_budget()
    reset_meta()
    caches = {}
    cik_map = load_cik_map(caches)
    hit = 0
    for t in watchlist:
        if t.upper() in SKIP_TICKERS:
            continue
        cik = cik_map.get(t.upper())
        if cik and fetch_submissions(cik, caches):
            hit += 1
    log.info("[EDGAR] prefetch: %s/%s ticker(s) resolved to submissions",
             hit, len(watchlist))
    return caches


# =============================================================================
# CLI — coverage audit, single-ticker render, offline self-test
# =============================================================================

def watchlist_from_latest_log(pattern=os.path.join("logs", "signals_*.log")):
    """Tickers from the most recent signal log — the universe actually run.

    Reads the same `Signal JSON:` payloads the tracker parser reads, so the
    coverage audit and the live run cannot disagree about the population.
    Returns None when no log is readable, so the caller can fall back.
    """
    try:
        import glob as _glob
        files = sorted(_glob.glob(pattern))
        if not files:
            return None
        tickers = set()
        with open(files[-1], encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r'"ticker"\s*:\s*"([A-Z.\-]{1,10})"', line)
                if m:
                    tickers.add(m.group(1).upper())
        return (sorted(tickers), os.path.basename(files[-1])) if tickers else None
    except OSError:
        return None


def cmd_coverage(tickers, days=90):
    """Resolve every watchlist name and report what it ACTUALLY files.

    This run does double duty. It fixes E4's DENOMINATOR (which names can
    receive EDGAR context at all) and it measures E4's EVENT RATES — 8-K and
    Form 4 counts over a trailing window, converted to filings per month.
    Kickoff §5 makes those rates a precondition of pre-registration: "how
    many 8-K filings per month across ~14-16 covered names? How many Form 4
    clusters?" Computing them here means the endpoints are written against
    measured supply rather than an estimate.

    COVERAGE IS NOT BINARY. A name can be insider-covered (Form 4) without
    being event-covered (8-K) — AG is exactly this. E4-2 should stratify on
    WHICH channel a name receives, not on a covered/uncovered flag.
    """
    reset_budget()
    caches = {}
    cik_map = load_cik_map(caches)
    if not cik_map:
        print("CIK map unavailable — cannot audit coverage. "
              "Check SEC_USER_AGENT in .env and network egress to www.sec.gov.")
        return 1

    since = _window_start(days=days)
    print(f"Trailing window: {days} days (since {since})\n")
    print(f"{'ticker':7}{'CIK':12}{'8-K':>5}{'Form4':>7}{'periodic':>12}"
          f"{'filed':>12}  note")
    print("-" * 84)

    rows_out, tot_8k, tot_f4 = [], 0, 0
    full, insider_only, event_only, none_cov, skipped = [], [], [], [], []

    for t in tickers:
        tkr = t.upper()
        if tkr in SKIP_TICKERS:
            skipped.append(tkr)
            print(f"{tkr:7}{'—':12}{'—':>5}{'—':>7}{'—':>12}{'—':>12}  SKIPPED (DP-3)")
            continue

        cik = cik_map.get(tkr)
        if not cik:
            none_cov.append(tkr)
            print(f"{tkr:7}{'—':12}{'—':>5}{'—':>7}{'—':>12}{'—':>12}  "
                  f"not in company_tickers.json (fund/series ticker)")
            continue

        rows  = _recent_rows(fetch_submissions(cik, caches))
        forms = {r["form"] for r in rows}

        n8k = sum(1 for r in rows
                  if r["form"] == "8-K" and _within_window(r["filingDate"], since))
        nf4 = sum(1 for r in rows
                  if r["form"] in FORM4_FORMS and _within_window(r["filingDate"], since))

        per = [r for r in rows if r["form"] in PERIODIC_FORMS]
        per_form  = max(per, key=lambda r: r["filingDate"])["form"] if per else "—"
        per_filed = max(per, key=lambda r: r["filingDate"])["filingDate"] if per else "—"

        has_8k = "8-K" in forms
        has_f4 = bool(forms & FORM4_FORMS)
        note = ""
        if forms & FOREIGN_FORMS:
            note = "foreign filer (40-F/6-K) — outside the 3-C filing set"

        if has_8k and has_f4:
            full.append(tkr)
        elif has_f4:
            insider_only.append(tkr)
        elif has_8k or per:
            event_only.append(tkr)
        else:
            none_cov.append(tkr)

        tot_8k += n8k
        tot_f4 += nf4
        rows_out.append((tkr, n8k, nf4))
        print(f"{tkr:7}{cik:12}{n8k:>5}{nf4:>7}{per_form:>12}{per_filed:>12}  {note}")

    n = len(tickers)
    covered = len(full) + len(insider_only) + len(event_only)
    months = days / 30.44

    print("-" * 84)
    print("COVERAGE — E4's denominator")
    print(f"  full (8-K + Form 4)      {len(full):>3}   {', '.join(full)}")
    print(f"  insider only (Form 4)    {len(insider_only):>3}   {', '.join(insider_only)}")
    print(f"  event only (8-K/periodic){len(event_only):>3}   {', '.join(event_only)}")
    print(f"  no coverage              {len(none_cov):>3}   {', '.join(none_cov)}")
    print(f"  skipped (DP-3)           {len(skipped):>3}   {', '.join(skipped)}")
    print(f"  ANY coverage            {covered}/{n} = {covered / n * 100:.1f}%")

    print("\nEVENT SUPPLY — E4's rate rule (Kickoff §5)")
    print(f"  8-K filings in {days}d      {tot_8k:>4}   -> {tot_8k / months:.1f}/month "
          f"across the covered set")
    print(f"  Form 4 filings in {days}d   {tot_f4:>4}   -> {tot_f4 / months:.1f}/month")
    if rows_out:
        busiest = sorted(rows_out, key=lambda r: -(r[1] + r[2]))[:3]
        print(f"  busiest names           {', '.join(f'{t} ({a}+{b})' for t, a, b in busiest)}")
    print("\n  Read these against the output rate before pre-registering E4:")
    print("  directional signals are 2.6% of output (32 BUYs in 1,243 rows) and")
    print("  78% single-name. Any endpoint gated on BUY/SELL volume is starved;")
    print("  prefer endpoints measured on the HOLD population.")
    return 0


def cmd_ticker(ticker):
    text, meta = edgar_context(ticker, {})
    print(f"--- {ticker.upper()} ---")
    print(text or "(no section — contributes nothing to the prompt)")
    print()
    print("log tag:", edgar_tag(meta))
    return 0


def _fixture():
    """Offline fixture mirroring the EDGAR submissions shape."""
    today = datetime.now(timezone.utc).date()
    d = lambda n: (today - timedelta(days=n)).isoformat()
    return {"filings": {"recent": {
        "form":            ["8-K", "8-K", "4", "4", "10-Q", "10-K", "8-K"],
        "filingDate":      [d(3), d(12), d(5), d(9), d(40), d(200), d(120)],
        "reportDate":      [d(3), d(12), d(5), d(9), d(45), d(210), d(120)],
        "accessionNumber": ["0000320193-26-000101", "0000320193-26-000092",
                            "0000320193-26-000088", "0000320193-26-000081",
                            "0000320193-26-000070", "0000320193-25-000110",
                            "0000320193-26-000040"],
        "primaryDocument": ["a8k.htm", "b8k.htm", "f4a.xml", "f4b.xml",
                            "q.htm", "k.htm", "c8k.htm"],
        "items":           ["2.02,9.01", "5.02", "", "", "", "", "8.01"],
    }}}


def cmd_xbrl(ticker, n=6):
    """Dump the raw XBRL entries behind each statement line, for diagnosis.

    Prints what the FILER tagged, not what the client rendered — the only way
    to tell a client bug from a tagging quirk. Added 2026-08-02 after RTX
    produced an internally impossible statement block that the period-anchor
    fix did not explain.
    """
    reset_budget()
    caches = {}
    cik = load_cik_map(caches).get(ticker.upper())
    if not cik:
        print(f"{ticker.upper()}: no CIK")
        return 1
    facts = _http_get(XBRL_FACTS_URL.format(cik10=cik), as_json=True)
    if not facts:
        print("companyfacts unavailable")
        return 1
    gaap = (facts.get("facts") or {}).get("us-gaap") or {}

    print(f"--- {ticker.upper()} (CIK {cik}) — raw XBRL entries ---\n")
    for label, kind, concepts in FINANCIAL_CONCEPTS:
        chosen = next((c for c in concepts if c in gaap), None)
        print(f"{label}  [{kind}]")
        if not chosen:
            print(f"    (no concept tagged; tried {', '.join(concepts)})\n")
            continue
        print(f"    concept: {chosen}")
        units = gaap[chosen].get("units") or {}
        for unit_key, entries in units.items():
            rows = [e for e in entries if e.get("form") in XBRL_FORMS]
            rows.sort(key=lambda e: (e.get("end") or "", e.get("start") or ""))
            for e in rows[-n:]:
                dur = _duration_days(e)
                print(f"    {unit_key:>10}  {e.get('start', '—'):>10} -> "
                      f"{e.get('end'):>10}  {str(dur) + 'd':>6} "
                      f"[{_bucket(dur) or '-':>3}]  {e.get('val'):>18,}  "
                      f"{e.get('form')} {e.get('fy')}{e.get('fp')} "
                      f"acc={e.get('accn')}")
        print()
    print("Look for: two entries with the SAME end date and duration but "
          "different values (restatement or a scope difference), or a value "
          "whose magnitude does not fit the label.")
    return 0


def cmd_selftest():
    """Exercise every extraction path offline. No network."""
    fails = []

    def check(name, got, want):
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"         got:  {got!r}\n         want: {want!r}")
            fails.append(name)

    rows  = _recent_rows(_fixture())
    since = _window_start()

    print("parallel-array unzip")
    check("row count", len(rows), 7)
    check("first form", rows[0]["form"], "8-K")

    print("8-K extraction (30d window, 9.01 suppressed)")
    e = extract_8k(rows, since, fetch=False)
    check("count in window", e["count"], 2)
    check("events captured", len(e["events"]), 2)
    check("items", e["items"],
          ["Item 2.02 results of operations", "Item 5.02 officer or director change"])

    print("Form 4 (no fetch -> count-only degradation)")
    f = extract_form4(rows, since, "0000320193", fetch=False)
    check("filings in window", f["filings"], 2)
    check("direction withheld", f["direction"], None)

    print("Form 4 XML parse")
    xml = ("<transactionCode>P</transactionCode>"
           "<transactionShares><value>1000</value></transactionShares>"
           "<transactionPricePerShare><value>50.00</value></transactionPricePerShare>"
           "<transactionCode>S</transactionCode>"
           "<transactionShares><value>200</value></transactionShares>"
           "<transactionPricePerShare><value>55.00</value></transactionPricePerShare>"
           "<transactionCode>M</transactionCode>"
           "<transactionShares><value>900</value></transactionShares>"
           "<transactionPricePerShare><value>0.00</value></transactionPricePerShare>")
    p = parse_form4_xml(xml)
    check("buys", p["buys"], 1)
    check("sells", p["sells"], 1)
    check("M excluded from the direction tally", p["buys"] + p["sells"], 2)
    check("M counted as mechanical", p["mechanical"], 1)
    check("buy notional", p["buy_value"], 50000.0)

    print("Form 4 — grants are not purchases; derivatives are out of scope")
    grant = parse_form4_xml(
        "<transactionCode>A</transactionCode>"
        "<transactionShares><value>5000</value></transactionShares>"
        "<transactionPricePerShare><value>0.00</value></transactionPricePerShare>"
        "<derivativeTable><transactionCode>P</transactionCode>"
        "<transactionShares><value>100</value></transactionShares>"
        "<transactionPricePerShare><value>1.00</value></transactionPricePerShare>"
        "</derivativeTable>")
    check("RSU award is not a buy", grant["buys"], 0)
    check("award counted separately", grant["awards"], 1)
    check("derivative-table entry ignored", grant["buys"] + grant["sells"], 0)

    print("cache key does not collapse directories")
    check("rendered vs raw differ",
          _cache_path("0000104169-26-000123", "xslF345X05/wf-form4_1.xml")
          != _cache_path("0000104169-26-000123", "wf-form4_1.xml"), True)
    check("ownership XML detected", _is_ownership_xml("<ownershipDocument>"), True)
    check("rendered HTML rejected", _is_ownership_xml("<html><table>"), False)

    print("periodic selection (latest 10-Q/10-K by filed date)")
    per = extract_periodic(rows, "0000320193", fetch=False)
    check("form", per["form"], "10-Q")

    print("MD&A extraction (TOC line skipped, bounded)")
    doc = ("<html><body><p>Item 2. Management's Discussion and Analysis .... 14</p>"
           "<p>Item 2. Management's Discussion and Analysis of Financial Condition"
           "</p><p>Revenue rose on stronger demand across segments. " + "x " * 900 +
           "</p><p>Item 3. Quantitative and Qualitative Disclosures</p>"
           "</body></html>")
    mda = extract_mda(doc)
    # SELF-CORRECTION (2026-08-02): this asserted the extract began with "and
    # Analysis of Financial Condition" — i.e. it PINNED THE DEFECT, treating
    # the orphaned tail of the section heading as correct output. A test that
    # encodes a bug passes forever and protects it. It now asserts what the
    # extract should actually contain: content, past the whole heading.
    check("TOC hit skipped and full heading consumed",
          mda.startswith("Revenue rose on stronger demand"), True)
    check("bounded", len(mda) <= MDA_MAX_CHARS + 2, True)

    print("section assembly")
    e2 = dict(e)
    e2["events"] = [dict(e["events"][0],
                         body="Q2 revenue of $94.0B, up 8% YoY; raised FY guidance.")]
    sec = build_filings_section(e2, {"filings": 4, "buys": 3, "sells": 1,
                                    "buy_value": 300000.0, "sell_value": 50000.0,
                                    "direction": "buying", "detail": "parsed",
                                    "roles": ["Chief Executive Officer", "Director"],
                                    "plan_filings": 1},
                                per, as_of="2026-08-02")
    check("header", sec.splitlines()[0],
          "--- SEC FILINGS (recent, as of 2026-08-02) ---")
    check("8-K body surfaced in section",
          "Q2 revenue of $94.0B" in sec, True)
    check("10b5-1 flagged in section", "10b5-1 plan" in sec, True)
    check("insider role surfaced", "Chief Executive Officer" in sec, True)

    print("Form 4 enrichment (10b5-1 + role)")
    p4 = parse_form4_xml(
        "<officerTitle>Chief Financial Officer</officerTitle>"
        "<transactionCode>S</transactionCode>"
        "<transactionShares><value>500</value></transactionShares>"
        "<transactionPricePerShare><value>10.0</value></transactionPricePerShare>"
        "<footnote>Sale under a Rule 10b5-1 trading plan adopted 2026-01-15.</footnote>")
    check("10b5-1 detected", p4["plan_10b5_1"], True)
    check("officer title", p4["role"], "Chief Financial Officer")

    print("8-K boilerplate trimming")
    check("cover page + FLS stripped",
          _clean_8k_body("Item 2.02 Results of Operations. Forward-looking "
                         "statements within the meaning of the Act. Revenue rose 8%."),
          "Revenue rose 8%")

    print("empty case (ETF / commodity trust — no filings at all)")
    empty = build_filings_section({"count": 0, "items": [], "dates": []},
                                  {"filings": 0, "buys": 0, "sells": 0,
                                   "buy_value": 0.0, "sell_value": 0.0,
                                   "direction": None, "detail": "count-only"},
                                  {"form": None, "filed": None, "mda": ""})
    check("contributes nothing", empty, "")

    print("DP-3 — CBRS excluded")
    text, meta = edgar_context("CBRS", {})
    check("CBRS text", text, "")
    check("CBRS skipped flag", meta["skipped"], True)
    check("CBRS tag", edgar_tag(meta), "E[no filings]")

    print("document cache (accession-keyed, Scope Spec §1)")
    check("cache key from accession",
          os.path.basename(_cache_path("0000320193-26-000070", "q.htm")),
          "000032019326000070_q.htm")
    check("no accession -> no fetch", fetch_document("0000320193", "", "q.htm"), None)

    print("run budget")
    reset_budget()
    check("fresh budget not exceeded", budget_exceeded(), False)
    _budget["start"] = time.monotonic() - (EDGAR_MAX_SECONDS + 1)
    check("expired budget trips", budget_exceeded(), True)
    check("fetch short-circuits when tripped", _http_get(CIK_MAP_URL), None)
    reset_budget()

    print("XBRL financial statements")
    def ent(start, end, val, form="10-Q", fy=2026, fp="Q3"):
        e = {"end": end, "val": val, "form": form, "fy": fy, "fp": fp}
        if start:
            e["start"] = start
        return e
    facts = {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            ent("2025-03-30", "2025-06-28", 85_777_000_000, fy=2025),
            ent("2025-09-28", "2026-06-27", 250_000_000_000, fy=2026),   # 9-month trap
            ent("2026-03-29", "2026-06-27", 94_036_000_000)]}},
        "NetIncomeLoss": {"units": {"USD": [
            ent("2025-03-30", "2025-06-28", 21_448_000_000, fy=2025),
            ent("2026-03-29", "2026-06-27", 23_600_000_000)]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            ent("2025-03-30", "2025-06-28", 1.40, fy=2025),
            ent("2026-03-29", "2026-06-27", 1.57)]}},
        "Assets": {"units": {"USD": [ent(None, "2026-06-27", 364_980_000_000)]}},
        "Revenues": {"units": {"USD": [ent("2026-03-29", "2026-06-27", 1)]}},
    }}}
    fin = extract_financials("0000320193", None, facts=facts)
    labels = [l["label"] for l in fin["lines"]]
    check("lines extracted", labels,
          ["Revenue", "Net income", "Diluted EPS", "Total assets"])
    rev = fin["lines"][0]
    check("concept fallback picks the tagged one first",
          rev["concept"], "RevenueFromContractWithCustomerExcludingAssessedTax")
    check("latest quarter selected", rev["value"], 94_036_000_000)
    check("YoY matches the SAME-DURATION prior, not the 9-month figure",
          round(rev["yoy"], 1), 9.6)
    # SELF-CORRECTION (2026-08-02): this previously asserted "instant items
    # have no YoY" and passed only because the fixture had ONE Assets entry.
    # Instant items DO get a year-over-year when a prior-year balance exists,
    # and that is correct and useful. The real invariant is that the prior
    # must be ~1 year back, which is what is now tested.
    check("instant item has no YoY when no prior exists",
          fin["lines"][3]["yoy"], None)
    check("period stamped", fin["period"], "2026-06-27")

    print("instant item YoY when a prior-year balance IS present")
    facts2 = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
        ent(None, "2025-06-28", 330_000_000_000, fy=2025),
        ent(None, "2026-06-27", 364_980_000_000)]}}}}}
    f2 = extract_financials("0", None, facts=facts2)
    check("balance-sheet YoY computed", round(f2["lines"][0]["yoy"], 1), 10.6)

    print("Form 4 — direction is never asserted without transactions")
    r = extract_form4([], _window_start(), "0", fetch=False)
    check("no filings -> no direction", r["direction"], None)
    only_mech = parse_form4_xml(
        "<transactionCode>M</transactionCode>"
        "<transactionShares><value>900</value></transactionShares>"
        "<transactionPricePerShare><value>0.00</value></transactionPricePerShare>")
    check("option exercise is neither buy nor sell",
          (only_mech["buys"], only_mech["sells"]), (0, 0))

    print("FY-period header does not double the FY")
    check("annual header",
          format_financials({"source": "10-K", "fy": 2026, "fp": "FY",
                             "period": "2026-06-30",
                             "lines": [{"label": "Revenue", "unit": "USD",
                                        "value": 1e9, "yoy": None}]})[0],
          "Financial statements (XBRL, 10-K FY2026, period ended 2026-06-30):")

    print("statement lines are anchored to ONE reporting period")
    facts3 = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            ent("2026-04-01", "2026-06-30", 24_700_000_000),
            ent("2025-04-01", "2025-06-30", 21_570_000_000, fy=2025)]}},
        "OperatingIncomeLoss": {"units": {"USD": [
            ent("2026-04-01", "2026-06-30", 2_800_000_000),
            ent("2025-04-01", "2025-06-30", 2_140_000_000, fy=2025)]}},
        # Gross profit tagged ONLY for the six-month period — the RTX defect.
        "GrossProfit": {"units": {"USD": [
            ent("2026-01-01", "2026-06-30", 2_200_000_000)]}},
        "Assets": {"units": {"USD": [
            ent(None, "2026-06-30", 174_000_000_000)]}},
    }}}
    f3 = extract_financials("0", None, facts=facts3)
    got = {l["label"]: l["value"] for l in f3["lines"]}
    check("off-period line dropped, not rendered",
          "Gross profit" in got, False)
    check("quarter lines kept", sorted(got), ["Operating income", "Revenue", "Total assets"])
    check("no impossible ordering survives",
          got.get("Operating income", 0) <= got.get("Revenue", 0), True)

    print("accounting-identity guard")
    bad = [{"label": "Revenue", "unit": "USD", "value": 24.7e9, "yoy": 14.5},
           {"label": "Gross profit", "unit": "USD", "value": 2.2e9, "yoy": -55.3},
           {"label": "Operating income", "unit": "USD", "value": 2.8e9, "yoy": 31.0}]
    dropped = _consistency_filter(bad)
    check("impossible gross profit removed",
          [l["label"] for l in bad], ["Revenue", "Operating income"])
    check("removal is recorded, not silent", dropped[0]["label"], "Gross profit")
    check("reason stated", dropped[0]["reason"],
          "operating income exceeds gross profit")

    ok = [{"label": "Revenue", "unit": "USD", "value": 100.0, "yoy": None},
          {"label": "Gross profit", "unit": "USD", "value": 40.0, "yoy": None},
          {"label": "Operating income", "unit": "USD", "value": 25.0, "yoy": None}]
    check("consistent block untouched", _consistency_filter(ok), [])
    check("all three retained", len(ok), 3)

    print("stale concepts are dropped; current-but-YTD is kept and labelled")
    facts4 = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            ent("2025-04-01", "2025-06-30", 21_570_000_000, fy=2025),
            ent("2026-04-01", "2026-06-30", 24_708_000_000)]}},
        # RTX's real shape: last tagged in 2020.
        "GrossProfit": {"units": {"USD": [
            ent("2020-10-01", "2020-12-31", 2_153_000_000, form="10-K", fy=2020)]}},
        # RTX's real shape: cash flow only ever year-to-date.
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            ent("2025-01-01", "2025-06-30", 1_763_000_000, fy=2025),
            ent("2026-01-01", "2026-06-30", 5_402_000_000)]}},
    }}}
    f4 = extract_financials("0", None, facts=facts4)
    got = {l["label"]: l for l in f4["lines"]}
    check("five-year-old gross profit dropped", "Gross profit" in got, False)
    check("YTD cash flow retained", "Operating cash flow" in got, True)
    check("YTD cash flow labelled",
          got["Operating cash flow"]["period_note"], "6M YTD")
    check("its YoY is same-duration",
          round(got["Operating cash flow"]["yoy"], 1), 206.4)
    check("quarter line unlabelled", got["Revenue"]["period_note"], None)
    check("schema stamped", f4["schema"], EXTRACT_SCHEMA)

    print("N-1 regression (found 2026-08-03, live on PWR/FTI/GM/PM/RTX/AAPL) — "
          "anchor vote is duration-aware, not list-order-dependent")
    # The pre-fix bug: Pass 1's anchor vote sorted candidates by end date only,
    # so a quarter entry and its own six-month-cumulative entry — which share
    # an end date in every real 10-Q — tied, and `rows[-1]` picked whichever
    # happened to sort last in whatever order SEC's feed returned them. PWR
    # rendered $17.4B as "revenue" against its own 8-K's $9.6B. Two of the
    # three fixtures below deliberately list the cumulative entry AFTER the
    # quarter (adversarial order) and one lists it BEFORE, so a fix that only
    # restores list-order luck cannot pass all three.
    facts5 = {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            ent("2025-04-01", "2025-06-30", 21_570_000_000, fy=2025),
            ent("2026-04-01", "2026-06-30", 24_700_000_000, fy=2026, fp="Q2"),
            ent("2026-01-01", "2026-06-30", 46_800_000_000, fy=2026, fp="Q2")]}},
        "NetIncomeLoss": {"units": {"USD": [
            ent("2026-01-01", "2026-06-30", 8_400_000_000, fy=2026, fp="Q2"),
            ent("2026-04-01", "2026-06-30", 4_200_000_000, fy=2026, fp="Q2")]}},
        # Cash flow tagged ONLY cumulative, as RTX's real shape — no shorter
        # alternative exists at this end date, so it must still resolve and
        # still carry the label once Revenue's vote sets the anchor to Q.
        # Prior-year cumulative entry included so the YoY check below has a
        # same-duration figure to compare against (its omission was the bug:
        # a single-entry concept has no prior to diff, and yoy resolves to
        # None rather than 206.4).
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            ent("2025-01-01", "2025-06-30", 1_763_000_000, fy=2025),
            ent("2026-01-01", "2026-06-30", 5_402_000_000, fy=2026, fp="Q2")]}},
    }}}
    f5 = extract_financials("0", None, facts=facts5)
    got5 = {l["label"]: l for l in f5["lines"]}
    check("N-1: quarter chosen over co-present H1 figure regardless of list order",
          got5["Revenue"]["value"], 24_700_000_000)
    check("N-1: quarter line unlabelled", got5["Revenue"]["period_note"], None)
    check("N-1: net income also resolves to the quarter, order-independent",
          got5["Net income"]["value"], 4_200_000_000)
    check("N-1: cash-flow-only-cumulative concept still resolves and is labelled 6M YTD",
          got5["Operating cash flow"]["period_note"], "6M YTD")
    check("N-1: its YoY is same-duration (H-vs-H), unaffected by the anchor fix",
          round(got5["Operating cash flow"]["yoy"], 1), 206.4)
    check("N-1: header states the quarter actually reported, not the half-year",
          format_financials(f5)[0],
          "Financial statements (XBRL, 10-Q Q2 FY2026, period ended 2026-06-30):")

    print("N-1 regression — H-bucket-only filer (no standalone quarter tagged anywhere)")
    # A concept with nothing but a cumulative bucket at the latest end date
    # must still win the anchor vote on its own — there is no quarter to
    # prefer, and the fix must not turn "no alternative" into "no result".
    facts6 = {"facts": {"us-gaap": {
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            ent("2025-01-01", "2025-06-30", 1_763_000_000, fy=2025),
            ent("2026-01-01", "2026-06-30", 5_402_000_000, fy=2026, fp="Q2")]}},
    }}}
    f6 = extract_financials("0", None, facts=facts6)
    check("H-only concept still resolves", len(f6["lines"]), 1)
    check("H-only concept sets its own anchor and is unlabelled (it IS the anchor)",
          f6["lines"][0]["period_note"], None)
    check("H-only period stamped at the half-year end date", f6["period"], "2026-06-30")

    print("N-1 SECOND ROUTE (found live on RTX 2026-08-10) — footnote tags do "
          "not outvote the income statement for the anchor bucket")
    # RTX's real shape at 2026-06-30: every headline line tags BOTH a
    # standalone quarter and the six-month cumulative, cash flow tags only
    # the cumulative, and the filer additionally carries a large pile of
    # footnote/segment concepts tagged ONLY year-to-date. Pass 1 votes Q 4-1,
    # but the old report-date override polled every concept in the feed and
    # elected H (RTX live: H:70 vs Q:39), silently rendering half-year
    # revenue under a Q2 header with no label. The fixture below reproduces
    # that ratio in miniature: 4 headline lines that can report Q, against 8
    # footnote concepts that only ever report H.
    hl = lambda q, h: {"units": {"USD": [
        ent("2026-04-01", "2026-06-30", q, fy=2026, fp="Q2"),
        ent("2026-01-01", "2026-06-30", h, fy=2026, fp="Q2")]}}
    facts7 = {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax":
            hl(24_708_000_000, 46_784_000_000),
        "OperatingIncomeLoss": hl(2_811_000_000, 5_366_000_000),
        "NetIncomeLoss":       hl(2_139_000_000, 4_198_000_000),
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            ent("2026-04-01", "2026-06-30", 1.57, fy=2026, fp="Q2"),
            ent("2026-01-01", "2026-06-30", 3.08, fy=2026, fp="Q2")]}},
        # Cash flow: cumulative only, exactly as RTX tags it.
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            ent("2026-01-01", "2026-06-30", 5_402_000_000, fy=2026, fp="Q2")]}},
        "Assets": {"units": {"USD": [ent(None, "2026-06-30", 173_972_000_000)]}},
    }}}
    # The footnote pile — none of these is a headline concept, so none can
    # become a rendered line, and none may influence the anchor.
    for i in range(8):
        facts7["facts"]["us-gaap"][f"SomeFootnoteConcept{i}"] = {"units": {"USD": [
            ent("2026-01-01", "2026-06-30", 1_000_000 * (i + 1), fy=2026, fp="Q2")]}}
    check("headline vote beats the footnote pile",
          _headline_flow_bucket(facts7["facts"]["us-gaap"], "2026-06-30"), "Q")
    check("the footnote pile would have won a universe-wide poll",
          _modal_flow_bucket(facts7["facts"]["us-gaap"], "2026-06-30"), "H")
    f7 = extract_financials("0", None, facts=facts7, report_date="2026-06-30")
    got7 = {l["label"]: l for l in f7["lines"]}
    check("RTX: revenue is the QUARTER, not the half-year",
          got7["Revenue"]["value"], 24_708_000_000)
    check("RTX: quarter line carries no period label",
          got7["Revenue"]["period_note"], None)
    check("RTX: EPS is the quarter's 1.57, not the half-year 3.08",
          got7["Diluted EPS"]["value"], 1.57)
    check("RTX: cumulative-only cash flow is RETAINED and LABELLED",
          got7["Operating cash flow"]["period_note"], "6M YTD")
    check("RTX: cash flow keeps its cumulative value",
          got7["Operating cash flow"]["value"], 5_402_000_000)
    check("RTX: balance sheet unaffected by the bucket fix",
          got7["Total assets"]["value"], 173_972_000_000)
    check("RTX: header states the quarter, not the half-year",
          format_financials(f7)[0],
          "Financial statements (XBRL, 10-Q Q2 FY2026, period ended 2026-06-30):")

    print("N-1 SECOND ROUTE — the GLD fallback still works (no headline flows)")
    # The shape _modal_flow_bucket was originally written for: a filer with
    # no headline flow concept at its own report date. _headline_flow_bucket
    # returns None and the fallback chain must still produce an anchor.
    facts8 = {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [ent(None, "2026-03-31", 155_167_600_000)]}},
        "Liabilities": {"units": {"USD": [ent(None, "2026-03-31", 56_775_000)]}},
    }}}
    check("no headline flows -> headline vote abstains",
          _headline_flow_bucket(facts8["facts"]["us-gaap"], "2026-03-31"), None)
    f8 = extract_financials("0", None, facts=facts8, report_date="2026-03-31")
    check("balance sheet still renders on the report date", f8["period"], "2026-03-31")
    check("both balance lines survive",
          sorted(l["label"] for l in f8["lines"]),
          ["Total assets", "Total liabilities"])

    print("DP-3C-q (RW 2026-08-11) -- total revenue supersedes the "
          "contract-revenue component, GM's real shape")
    def _gm(total_entries):
        """GM Q2 FY2026: contract revenue 43.762B, total 48.026B, same period."""
        g = {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
                ent("2025-04-01", "2025-06-30", 41_000_000_000, fy=2025),
                ent("2026-04-01", "2026-06-30", 43_762_000_000, fy=2026, fp="Q2"),
                ent("2026-01-01", "2026-06-30", 83_111_000_000, fy=2026, fp="Q2")]}},
             "NetIncomeLoss": {"units": {"USD": [
                ent("2026-04-01", "2026-06-30", 1_305_000_000, fy=2026, fp="Q2")]}},
             "Assets": {"units": {"USD": [ent(None, "2026-06-30", 282_742_000_000)]}}}
        if total_entries is not None:
            g["Revenues"] = {"units": {"USD": total_entries}}
        return {"facts": {"us-gaap": g}}

    gmq = _gm([ent("2025-04-01", "2025-06-30", 44_000_000_000, fy=2025),
               ent("2026-04-01", "2026-06-30", 48_026_000_000, fy=2026, fp="Q2"),
               ent("2026-01-01", "2026-06-30", 91_000_000_000, fy=2026, fp="Q2")])
    fq = extract_financials("0", None, facts=gmq, report_date="2026-06-30")
    rq = {l["label"]: l for l in fq["lines"]}
    check("DP-3C-q: revenue is the TOTAL, matching GM's own 8-K",
          rq["Revenue"]["value"], 48_026_000_000)
    check("DP-3C-q: the concept swap is recorded on the line",
          rq["Revenue"]["concept"], "Revenues")
    check("DP-3C-q: the total is still the QUARTER, not the half-year",
          rq["Revenue"]["period_note"], None)
    # 48.026 / 44.0 = +9.15%. The discriminating value: mixing the total
    # against the CONTRACT concept's prior (41.0B) would read +17.1%, so this
    # figure proves the prior was re-derived rather than inherited.
    check("DP-3C-q: YoY is recomputed on the total's OWN prior, not mixed",
          round(rq["Revenue"]["yoy"], 1), 9.1)

    print("DP-3C-q -- the no-op cases that keep the ruling narrow")
    solo = extract_financials("0", None, facts=_gm(None),
                              report_date="2026-06-30")
    rs = {l["label"]: l for l in solo["lines"]}
    check("no Revenues tagged: contract revenue is untouched",
          (rs["Revenue"]["value"], rs["Revenue"]["concept"]),
          (43_762_000_000, "RevenueFromContractWithCustomerExcludingAssessedTax"))

    equal = _gm([ent("2026-04-01", "2026-06-30", 43_800_000_000,
                     fy=2026, fp="Q2")])
    re_ = {l["label"]: l for l in extract_financials(
        "0", None, facts=equal, report_date="2026-06-30")["lines"]}
    check("Revenues within the 2% margin: NOT swapped",
          re_["Revenue"]["concept"],
          "RevenueFromContractWithCustomerExcludingAssessedTax")

    smaller = _gm([ent("2026-04-01", "2026-06-30", 30_000_000_000,
                       fy=2026, fp="Q2")])
    rsm = {l["label"]: l for l in extract_financials(
        "0", None, facts=smaller, report_date="2026-06-30")["lines"]}
    check("a SMALLER Revenues is never swapped in",
          rsm["Revenue"]["value"], 43_762_000_000)

    offperiod = _gm([ent("2026-01-01", "2026-03-31", 60_000_000_000,
                         fy=2026, fp="Q1")])
    ro = {l["label"]: l for l in extract_financials(
        "0", None, facts=offperiod, report_date="2026-06-30")["lines"]}
    check("a larger Revenues at a DIFFERENT period is never swapped in "
          "(would reintroduce the mixed-period defect)",
          ro["Revenue"]["value"], 43_762_000_000)

    print("statement block is never silently truncated")
    many = {"schema": EXTRACT_SCHEMA, "source": "10-Q", "fy": 2026, "fp": "Q2",
            "period": "2026-06-30", "dropped": [],
            "lines": [{"label": f"L{i}", "unit": "USD", "value": 1e9,
                       "yoy": None, "period_note": None} for i in range(11)]}
    blk = format_financials(many)
    check("all 11 lines rendered", len(blk) - 1, 11)
    check("explicit overflow note when capped",
          format_financials(many, max_lines=8)[-1],
          "  (+3 further line item(s) not shown)")

    print("8-K exhibit wrapper detection")
    for phrasing in ("furnished herewith as Exhibit No. 99 to this Report",
                     "attached as Exhibit 99.1", "issued a press release announcing",
                     "A copy is attached hereto as Exhibit 99.1"):
        check(f"wrapper detected: {phrasing[:34]}",
              bool(re.search(r"(exhibit\s*(?:no\.?\s*)?9?9|furnished\s+herewith|"
                             r"attached\s+(?:hereto\s+)?as\s+exhibit|"
                             r"issued\s+a\s+press\s+release)", phrasing, re.I)), True)

    print("no percent change across or below zero")
    signs = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            ent("2025-01-01", "2025-03-31", 10_000_000, fy=2025),
            ent("2026-01-01", "2026-03-31", 12_000_000)]}},
        "NetIncomeLoss": {"units": {"USD": [
            ent("2025-01-01", "2025-03-31", -3_100_000, fy=2025),
            ent("2026-01-01", "2026-03-31", 30_400_000)]}},
        "OperatingIncomeLoss": {"units": {"USD": [
            ent("2025-01-01", "2025-03-31", -2_020_000_000, fy=2025),
            ent("2026-01-01", "2026-03-31", -533_000_000)]}},
    }}}
    fs = extract_financials("0", None, facts=signs)
    m = {l["label"]: l for l in fs["lines"]}
    check("sign flip: no percentage", m["Net income"]["yoy"], None)
    check("sign flip: prior value shown", m["Net income"]["prior"], -3_100_000)
    check("negative to negative: no percentage", m["Operating income"]["yoy"], None)
    check("both positive: percentage kept", round(m["Revenue"]["yoy"], 1), 20.0)
    rendered = "\n".join(format_financials(fs))
    check("prior rendered as a value", "vs $-3.1M prior year" in rendered, True)
    check("no -1077.9% anywhere", "-1077" in rendered, False)

    print("XBRL lagging the latest periodic is stated")
    lag = format_financials(
        {"schema": EXTRACT_SCHEMA, "source": "10-Q", "fy": 2026, "fp": "Q1",
         "period": "2026-03-31", "dropped": [],
         "lines": [{"label": "Revenue", "unit": "USD", "value": 9.8e9,
                    "yoy": None, "prior": None, "period_note": None}]},
        periodic={"form": "10-Q", "filed": "2026-07-24", "report": "2026-06-30"})
    check("lag note present", "PRIOR period" in lag[1], True)

    print("XBRL viewer renderings are not filing content")
    check("R1.htm marker detected",
          bool(_VIEWER_RE.search("XML 21 R1.htm IDEA: XBRL DOCUMENT v3.26.1")), True)

    print("table of contents is not an MD&A extract")
    toc = ("9 Consolidated Balance Sheets and Cash Flows Analysis 12 Explanation "
           "and Reconciliation 15 Business Segment 17 Firmwide Risk 32 Capital 33")
    check("TOC rejected", extract_mda(
        "<p>Item 2. Management\u2019s Discussion and Analysis of Financial "
        "Condition and Results of Operations</p><p>" + toc + "</p>"), "")

    print("concept selection prefers CURRENT over merely present")
    nv = {"facts": {"us-gaap": {
        # NVDA's real shape: preferred concept fossilised at FY2022.
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            ent("2021-02-01", "2022-01-30", 26_914_000_000, form="10-K", fy=2022)]}},
        "Revenues": {"units": {"USD": [
            ent("2025-01-27", "2025-04-27", 44_062_000_000, fy=2025),
            ent("2026-01-26", "2026-04-26", 81_615_000_000)]}},
        "GrossProfit": {"units": {"USD": [
            ent("2025-01-27", "2025-04-27", 26_670_000_000, fy=2025),
            ent("2026-01-26", "2026-04-26", 61_157_000_000)]}},
    }}}
    fn = extract_financials("0", None, facts=nv)
    mm = {l["label"]: l for l in fn["lines"]}
    check("revenue no longer missing", "Revenue" in mm, True)
    check("fossil concept skipped", mm["Revenue"]["concept"], "Revenues")
    check("current value used", mm["Revenue"]["value"], 81_615_000_000)
    check("gross profit still present", mm["Gross profit"]["value"], 61_157_000_000)
    check("identity holds", mm["Gross profit"]["value"] <= mm["Revenue"]["value"], True)

    print("zero placeholders neither render nor set the anchor (GLD)")
    gld = {"facts": {"us-gaap": {
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            ent("2025-01-01", "2025-03-31", 0, fy=2025),
            ent("2026-01-01", "2026-03-31", 0)]}},
        "NetIncomeLoss": {"units": {"USD": [
            ent("2025-07-01", "2025-09-30", 16_830_571_000, fy=2025)]}},
        "Assets": {"units": {"USD": [
            ent(None, "2025-03-31", 93_474_000_000, fy=2025),
            ent(None, "2026-03-31", 155_167_600_000)]}},
        "Liabilities": {"units": {"USD": [
            ent(None, "2026-03-31", 56_775_000)]}},
    }}}
    g = extract_financials("0", None, facts=gld, report_date="2026-03-31")
    lab = [l["label"] for l in g["lines"]]
    check("zero placeholder not rendered", "Operating cash flow" in lab, False)
    check("balance sheet survives", sorted(lab), ["Total assets", "Total liabilities"])
    check("anchor is the filing's report date", g["period"], "2026-03-31")
    check("stale net income still dropped", "Net income" in lab, False)

    print("report date beats the flow vote")
    check("_has_entry_at", _has_entry_at(gld["facts"]["us-gaap"], "2026-03-31"), True)
    check("instants only -> no flow bucket",
          _modal_flow_bucket({"Assets": gld["facts"]["us-gaap"]["Assets"]},
                             "2026-03-31"), None)

    print("officer title entity handling")
    t = parse_form4_xml("<officerTitle>SVP &amp; Controller</officerTitle>"
                        "<transactionCode>S</transactionCode>"
                        "<transactionShares><value>10</value></transactionShares>"
                        "<transactionPricePerShare><value>1</value></transactionPricePerShare>")
    check("ampersand unescaped", t["role"], "SVP & Controller")

    print("financial block rendering")
    block = format_financials(fin)
    check("header", block[0],
          "Financial statements (XBRL, 10-Q Q3 FY2026, period ended 2026-06-27):")
    check("EPS as per-share not money", "1.57" in block[3], True)
    check("revenue as billions", "$94.0B" in block[1], True)

    print("missing concept is omitted, never guessed")
    thin = extract_financials("0000000000", None,
                              facts={"facts": {"us-gaap": {}}})
    check("no lines", thin["lines"], [])

    print("log tag")
    check("tag: fin=none stated explicitly, not omitted (DP-3C-j)",
          edgar_tag({"covered": True, "eightk": {"count": 2},
                    "form4": {"buys": 3, "sells": 1, "direction": "buying"},
                    "periodic": {"form": "10-Q", "filed": "2026-05-01"}}),
          "E[8k=2; form4=+3/-1; periodic=10-Q@2026-05-01; fin=none]")

    print("log tag — DP-3C-i, filing dates on 8k= and form4=")
    check("tag: 8k and form4 each carry their own most-recent date",
          edgar_tag({"covered": True,
                    "eightk": {"count": 2, "dates": ["2026-07-23", "2026-06-30"]},
                    "form4": {"buys": 0, "sells": 0, "direction": None,
                              "filings": 5, "dates": ["2026-07-30", "2026-07-28"]},
                    "periodic": {"form": "10-Q", "filed": "2026-05-01"},
                    "financials": {"n_lines": 9, "period": "2026-06-30"}}),
          "E[8k=2@2026-07-23; form4=5f@2026-07-30; periodic=10-Q@2026-05-01; fin=9@2026-06-30]")

    print("log tag — DP-3C-i, form4 date fires even in count-only mode "
          "(no direction, but a date exists — grants/exercises/withholding count)")
    check("tag: form4 date present without a computed direction",
          edgar_tag({"covered": True, "eightk": {"count": 0},
                    "form4": {"filings": 3, "direction": None,
                              "dates": ["2026-08-01"]},
                    "periodic": {}}),
          "E[8k=0; form4=3f@2026-08-01; fin=none]")

    print("log tag — DP-3C-j, fin=degraded distinct from fin=none")
    check("tag: budget-starved ticker reads fin=degraded, not silently omitted",
          edgar_tag({"covered": True, "eightk": {"count": 0},
                    "form4": {"filings": 0, "direction": None},
                    "periodic": {"form": "10-Q", "filed": "2026-05-01"},
                    "financials": {"n_lines": 0, "period": None, "degraded": True}}),
          "E[8k=0; form4=0f; periodic=10-Q@2026-05-01; fin=degraded]")

    print("extract_financials — degraded flag reflects the run budget, "
          "not a guess")
    reset_budget()
    check("fresh budget: absent financials read fin=none, not degraded",
          extract_financials("0", None, facts={})["degraded"], False)
    _budget["start"] = time.monotonic() - (EDGAR_MAX_SECONDS + 1)
    check("tripped budget: absent financials read degraded",
          extract_financials("0", None, fetch=True)["degraded"], True)
    reset_budget()

    print()
    print(f"{'ALL PASS' if not fails else str(len(fails)) + ' FAILURE(S): ' + ', '.join(fails)}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(
        description="EDGAR filing context provider (Phase 3-C / EW1). "
                    "Advisory-only; no orders; not financial advice.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--coverage", action="store_true",
                   help="audit the 24-name watchlist against the live CIK map")
    g.add_argument("--ticker", help="render the prompt section for one ticker")
    g.add_argument("--selftest", action="store_true",
                   help="offline extraction tests; no network")
    g.add_argument("--xbrl", metavar="TICKER",
                   help="dump raw XBRL entries per concept (diagnostic)")
    ap.add_argument("--tickers", nargs="+", default=None,
                    help="explicit ticker list for --coverage (default: the "
                         "universe from the most recent signals log)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reset_budget()

    if args.selftest:
        return cmd_selftest()
    if args.xbrl:
        return cmd_xbrl(args.xbrl)
    if args.coverage:
        tickers = args.tickers
        if tickers:
            print(f"Universe: {len(tickers)} ticker(s) given on the command line\n")
        else:
            derived = watchlist_from_latest_log()
            if derived:
                tickers, src = derived
                print(f"Universe: {len(tickers)} ticker(s) from {src} "
                      f"(the population the bot actually ran)\n")
            else:
                tickers = WATCHLIST_24
                print(f"Universe: no readable signals log — falling back to the "
                      f"{len(WATCHLIST_24)}-name snapshot in edgar_client.py. "
                      f"CONFIRM it still matches the live watchlist.\n")
        return cmd_coverage(tickers)
    return cmd_ticker(args.ticker)


if __name__ == "__main__":
    sys.exit(main())
