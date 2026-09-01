"""Apply the DOW co-registrant / provisional-cache fix to edgar_client.py.

Exact-match replacements only. If any anchor text has drifted the script
refuses and changes nothing, so it is safe to run twice or on a newer file.

    python apply_dow_fix.py edgar_client.py
"""
import io
import os
import shutil
import sys

EDITS = []


def edit(name, old, new):
    EDITS.append((name, old, new))


# ---------------------------------------------------------------------------
# 1. New constants: the index-headers URL and the provisional re-check window.
# ---------------------------------------------------------------------------
edit(
    "constants",
    '''FILING_INDEX_URL = ("https://www.sec.gov/Archives/edgar/data/{cik}/"
                    "{accession_nodash}/index.json")
XBRL_FACTS_URL   = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"''',
    '''FILING_INDEX_URL = ("https://www.sec.gov/Archives/edgar/data/{cik}/"
                    "{accession_nodash}/index.json")
FILING_HEADER_URL = ("https://www.sec.gov/Archives/edgar/data/{cik}/"
                     "{accession_nodash}/{accession}-index-headers.html")
XBRL_FACTS_URL   = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

# A PROVISIONAL extract is one whose period is not the period the filing
# itself reports, because the facts for that period were not in this CIK's
# companyfacts feed when it was computed. The fin_ cache is keyed by the
# LATEST PERIODIC ACCESSION, which is right for an immutable document and
# wrong for a feed that fills in afterwards: without this, one provisional
# extract is pinned until the NEXT periodic is filed -- a full quarter.
# Found on DOW 2026-08-26: the Q2 extract written 2026-08-11 would have been
# served unchanged until the Q3 10-Q in late October.
PROVISIONAL_RECHECK_SECONDS = 6 * 3600''',
)

# ---------------------------------------------------------------------------
# 2. Co-registrant recovery, inserted above extract_financials().
# ---------------------------------------------------------------------------
edit(
    "co-registrant helpers",
    '''def extract_financials(cik10, latest_accession=None, fetch=True, facts=None,
                       report_date=None):''',
    '''_CIK_IN_HEADER = re.compile(r"CENTRAL\\s+INDEX\\s+KEY:\\s*(\\d{10})", re.I)


def _submission_filer_ciks(cik10, accession):
    """Every FILER CIK on one submission, in the order the header lists them.

    ANALYST NOTE (2026-08-26, DOW). A COMBINED FILING is one document with
    two registrants -- a parent and a subsidiary co-registering a single
    10-Q. SEC's XBRL ingest attributes the facts to ONE CIK, and it is not
    always the primary filer's. DOW Inc. (CIK 1751788) filed accession
    0001751788-26-000147 for the period ended 2026-06-30 with The Dow
    Chemical Company (CIK 29915) as co-filer, and companyfacts placed the
    ENTIRE Q2 statement set under 29915. CIK 1751788's feed stops at the Q1
    accession; CIK 29915's own history stops in 2018 and then resumes with
    this one accession. Verified against data.sec.gov on 2026-08-26.

    Returns [] on any failure -- this is an exception path and must never
    raise into a run (E3).
    """
    if not accession:
        return []
    body = _http_get(FILING_HEADER_URL.format(
        cik=cik10.lstrip("0") or "0",
        accession_nodash=accession.replace("-", ""),
        accession=accession))
    if not body:
        return []
    out, seen = [], set()
    for m in _CIK_IN_HEADER.finditer(body):
        c = m.group(1)
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _facts_from_co_registrant(cik10, accession, report_date):
    """Recover one filing's facts from a co-filer's companyfacts feed.

    THE ACCESSION IS THE JOIN KEY AND THE ONLY ONE. Entries tagged with this
    accession came from the document already identified, whichever CIK SEC
    filed them under. Entries tagged with any OTHER accession are a different
    registrant's numbers -- in a parent/subsidiary pair they are genuinely
    different financials -- and are DROPPED, never merged. This is the same
    discipline value_anchor's two-route join uses when it refuses to resolve
    a ticker on a filename prefix: match exactly or report nothing.

    Returns (facts_subset, cik) or (None, None).
    """
    for cand in _submission_filer_ciks(cik10, accession):
        if cand == cik10:
            continue
        facts = _http_get(XBRL_FACTS_URL.format(cik10=cand), as_json=True)
        if not facts:
            continue
        gaap = (facts.get("facts") or {}).get("us-gaap") or {}
        kept = {}
        for concept, node in gaap.items():
            units = {}
            for unit_key, entries in (node.get("units") or {}).items():
                rows = [e for e in entries if e.get("accn") == accession]
                if rows:
                    units[unit_key] = rows
            if units:
                kept[concept] = dict(node, units=units)
        if kept and _has_entry_at(kept, report_date):
            log.info("[EDGAR] %s: facts for %s absent from CIK %s; recovered "
                     "%d concept(s) from co-registrant CIK %s on the SAME "
                     "accession %s", accession, report_date, cik10,
                     len(kept), cand, accession)
            return {"facts": {"us-gaap": kept}}, cand
    return None, None


def extract_financials(cik10, latest_accession=None, fetch=True, facts=None,
                       report_date=None):''',
)

# ---------------------------------------------------------------------------
# 3. Cache read: do not pin a provisional extract for a quarter.
# ---------------------------------------------------------------------------
edit(
    "cache read",
    '''                if cached.get("schema") == EXTRACT_SCHEMA:
                    return cached
                log.info("[EDGAR] financials cache schema %s != %s — recomputing",
                         cached.get("schema"), EXTRACT_SCHEMA)''',
    '''                if cached.get("schema") == EXTRACT_SCHEMA:
                    # An extract whose period is not the filing's own period
                    # was computed before the feed caught up. Accession-keying
                    # would serve it until the NEXT periodic, so re-check it on
                    # an interval instead. Derived here rather than trusted
                    # from the file, so caches written before this change are
                    # classified correctly without a schema bump -- bumping
                    # would invalidate every ticker's extract at once and
                    # spend the whole EDGAR budget refetching companyfacts.
                    provisional = bool(report_date and cached.get("period")
                                       and cached["period"] != report_date)
                    if not provisional:
                        return cached
                    try:
                        age = time.time() - os.path.getmtime(cache_file)
                    except OSError:
                        age = PROVISIONAL_RECHECK_SECONDS
                    if age < PROVISIONAL_RECHECK_SECONDS:
                        cached["provisional"] = True
                        return cached
                    log.info("[EDGAR] financials for %s are PROVISIONAL "
                             "(extract at %s, filing reports %s) — re-checking",
                             latest_accession, cached["period"], report_date)
                else:
                    log.info("[EDGAR] financials cache schema %s != %s — recomputing",
                             cached.get("schema"), EXTRACT_SCHEMA)''',
)

# ---------------------------------------------------------------------------
# 4. After the main pass: try the co-registrant, then stamp `provisional`.
# ---------------------------------------------------------------------------
edit(
    "co-registrant retry + provisional stamp",
    '''    out["dropped"] = _consistency_filter(out["lines"])

    if cache_file and out["lines"]:''',
    '''    out["dropped"] = _consistency_filter(out["lines"])

    # The primary CIK's feed did not carry the filing's own period. Before
    # accepting the prior period as the answer, check whether a co-registrant
    # on the SAME accession carries it. Only reached on the exception path, so
    # it costs nothing on a healthy ticker.
    if (fetch and report_date and latest_accession
            and out.get("period") and out["period"] != report_date):
        alt, alt_cik = _facts_from_co_registrant(
            cik10, latest_accession, report_date)
        if alt:
            rec = extract_financials("0", None, fetch=False, facts=alt,
                                     report_date=report_date)
            if rec.get("lines") and rec.get("period") == report_date:
                rec["co_registrant_cik"] = alt_cik
                out = rec

    # Stamped on the object AND written to the cache so the next run can tell
    # a settled extract from one still waiting on the feed. DP-3C-j's rule:
    # a field that means two different things is a tool reporting a value it
    # did not compute.
    out["provisional"] = bool(report_date and out.get("period")
                              and out["period"] != report_date)

    if cache_file and out["lines"]:''',
)

# ---------------------------------------------------------------------------
# 5. The NOTE asserted a cause it could not know.
# ---------------------------------------------------------------------------
edit(
    "prompt NOTE wording",
    '''            lines.append(
                f"  NOTE: these are the PRIOR period's figures — XBRL data for "
                f"the {periodic.get('form')} covering {periodic['report']} is "
                f"not yet published by SEC.")''',
    '''            # CORRECTED 2026-08-26. This previously read "is not yet
            # published by SEC", which is a CAUSE the client cannot observe
            # and which was FALSE for DOW: the Q2 2026 facts were published
            # on the filing date, under the co-registrant's CIK. State what
            # was actually observed -- the facts are not in the feed this
            # client read -- and let the reason stay unclaimed.
            lines.append(
                f"  NOTE: these are the PRIOR period's figures — XBRL data for "
                f"the {periodic.get('form')} covering {periodic['report']} is "
                f"not present in this filer's companyfacts feed.")''',
)

# ---------------------------------------------------------------------------
# 6. The log tag must carry the distinction the prose already carries.
# ---------------------------------------------------------------------------
edit(
    "fin= tag",
    '''    fin = meta.get("financials") or {}
    if fin.get("n_lines"):
        parts.append(f"fin={fin['n_lines']}@{fin.get('period')}")''',
    '''    fin = meta.get("financials") or {}
    if fin.get("n_lines"):
        # DP-3C-j's rule applied to a second way this tag could mean two
        # things: `fin=7@2026-03-31` read identically whether that period IS
        # the filing's period or is a fallback because the feed lacks it. The
        # PROMPT said so in prose; the tag did not, and the exhibits read the
        # tag. `~prov` = provisional. `+coregNNNNNNNNNN` = recovered from a
        # co-registrant's feed on the same accession.
        tag = f"fin={fin['n_lines']}@{fin.get('period')}"
        if fin.get("provisional"):
            tag += "~prov"
        elif fin.get("co_registrant_cik"):
            tag += f"+coreg{fin['co_registrant_cik']}"
        parts.append(tag)''',
)

# ---------------------------------------------------------------------------
# 7. Propagate both flags into the meta the tag reads.
# ---------------------------------------------------------------------------
edit(
    "meta propagation",
    '''                     "financials": {"n_lines": len(financials["lines"]),
                                    "period": financials.get("period"),
                                    "degraded": financials.get("degraded", False)},''',
    '''                     "financials": {"n_lines": len(financials["lines"]),
                                    "period": financials.get("period"),
                                    "provisional": financials.get("provisional", False),
                                    "co_registrant_cik": financials.get("co_registrant_cik"),
                                    "degraded": financials.get("degraded", False)},''',
)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "edgar_client.py"
    # Read and write with newline="" so the file's own line endings survive.
    # The repo file is CRLF; normalising it to LF would turn a ~150-line patch
    # into a 3,000-line whole-file diff in git and bury the actual change.
    with io.open(path, encoding="utf-8", newline="") as f:
        raw = f.read()
    crlf = "\r\n" in raw
    src = raw.replace("\r\n", "\n")

    missing = [name for name, old, _ in EDITS if src.count(old) != 1]
    if missing:
        print("REFUSING — anchor text not found exactly once for: "
              + ", ".join(missing))
        print("Nothing was changed. The file has drifted from the reviewed "
              "version; re-derive the patch against it.")
        return 1

    for name, old, new in EDITS:
        src = src.replace(old, new, 1)

    if crlf:
        src = src.replace("\n", "\r\n")
    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    print("applied %d edit(s) to %s (backup: %s)" % (len(EDITS), path, backup))
    print("next: python edgar_client.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
