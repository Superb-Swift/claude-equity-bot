"""Functional tests for the DOW co-registrant / provisional-cache fix.

Synthetic facts only -- no network. Mirrors the real DOW shape: the primary
CIK's feed stops at the prior quarter, the co-registrant's carries the current
one under the SAME accession.
"""
import os
import json
import time
import shutil
import tempfile

import edgar_client as ec

ACC = "0001751788-26-000147"
OTHER_ACC = "0001751788-26-000134"
PRIMARY = "0001751788"
COREG = "0000029915"
REPORT = "2026-06-30"
PRIOR = "2026-03-31"

FAILS = []


def check(label, got, want):
    ok = got == want
    print(("  [PASS] " if ok else "  [FAIL] ") + label)
    if not ok:
        print("         got  %r\n         want %r" % (got, want))
        FAILS.append(label)


def _flow(concept, rows):
    return {concept: {"units": {"USD": rows}}}


def _row(start, end, val, accn, form="10-Q"):
    return {"start": start, "end": end, "val": val, "accn": accn,
            "form": form, "fy": 2026, "fp": "Q2"}


def primary_facts():
    """Stops at Q1, exactly like CIK 1751788 does today."""
    g = {}
    g.update(_flow("RevenueFromContractWithCustomerIncludingAssessedTax", [
        _row("2025-01-01", "2025-03-31", 10_431_000_000, OTHER_ACC),
        _row("2026-01-01", PRIOR, 9_794_000_000, OTHER_ACC)]))
    g.update(_flow("NetIncomeLoss", [
        _row("2025-01-01", "2025-03-31", -307_000_000, OTHER_ACC),
        _row("2026-01-01", PRIOR, -533_000_000, OTHER_ACC)]))
    g.update({"Assets": {"units": {"USD": [
        {"end": PRIOR, "val": 59_780_000_000, "accn": OTHER_ACC, "form": "10-Q"}]}}})
    return {"facts": {"us-gaap": g}}


def coreg_facts(accn=ACC, extra_noise=True):
    """Q2 under the co-registrant, plus that filer's own unrelated history."""
    g = {}
    g.update(_flow("RevenueFromContractWithCustomerIncludingAssessedTax", [
        _row("2025-04-01", "2025-06-30", 10_104_000_000, accn),
        _row("2026-04-01", REPORT, 12_092_000_000, accn)]))
    g.update(_flow("NetIncomeLoss", [
        _row("2025-04-01", "2025-06-30", -835_000_000, accn),
        _row("2026-04-01", REPORT, 401_000_000, accn)]))
    g.update({"StockholdersEquity": {"units": {"USD": [
        {"end": REPORT, "val": 15_860_000_000, "accn": accn, "form": "10-Q"}]}}})
    if extra_noise:
        # The subsidiary's OWN 2018 filings. Different registrant, different
        # numbers, different accession -- must never be merged in.
        g["RevenueFromContractWithCustomerIncludingAssessedTax"]["units"]["USD"].append(
            _row("2018-01-01", "2018-12-31", 60_278_000_000,
                 "0000029915-19-000008", form="10-K"))
    return {"facts": {"us-gaap": g}}


HEADER = """
FILER:
  COMPANY DATA:
    COMPANY CONFORMED NAME: DOW INC.
    CENTRAL INDEX KEY:      0001751788
FILER:
  COMPANY DATA:
    COMPANY CONFORMED NAME: DOW CHEMICAL CO /DE/
    CENTRAL INDEX KEY:      0000029915
"""


def install_http(coreg_payload, header=HEADER):
    calls = []

    def fake(url, as_json=False):
        calls.append(url)
        if "index-headers" in url:
            return header
        if "companyfacts" in url:
            if COREG in url:
                return coreg_payload
            return None
        return None
    ec._http_get = fake
    return calls


def main():
    tmp = tempfile.mkdtemp()
    ec.EDGAR_CACHE_DIR = tmp
    real_http = ec._http_get

    print("co-registrant recovery — the DOW shape")
    calls = install_http(coreg_facts())
    out = ec.extract_financials(PRIMARY, ACC, facts=primary_facts(),
                                report_date=REPORT)
    check("period is the FILING's period, not the prior one", out["period"], REPORT)
    check("recovered CIK is recorded", out.get("co_registrant_cik"), COREG)
    check("not marked provisional once recovered", out.get("provisional"), False)
    rev = next((l for l in out["lines"] if l["label"] == "Revenue"), None)
    check("revenue is the Q2 figure", rev and rev["value"], 12_092_000_000)
    check("index-headers was fetched exactly once",
          sum("index-headers" in u for u in calls), 1)

    print("the accession is the join key — a co-filer's OWN filings are dropped")
    os.remove(os.path.join(tmp, "fin_%s.json" % ACC.replace("-", "")))
    install_http(coreg_facts(accn="0000029915-19-000008"))
    out2 = ec.extract_financials(PRIMARY, ACC, facts=primary_facts(),
                                 report_date=REPORT)
    check("wrong-accession facts are NOT admitted", out2["period"], PRIOR)
    check("...and the result is marked provisional", out2.get("provisional"), True)
    check("...and no co-registrant is claimed", out2.get("co_registrant_cik"), None)

    print("no co-registrant at all — unchanged fallback behaviour")
    os.remove(os.path.join(tmp, "fin_%s.json" % ACC.replace("-", "")))
    install_http(None, header="FILER:\n  CENTRAL INDEX KEY:      0001751788\n")
    out3 = ec.extract_financials(PRIMARY, ACC, facts=primary_facts(),
                                 report_date=REPORT)
    check("falls back to the prior period as before", out3["period"], PRIOR)
    check("...marked provisional", out3.get("provisional"), True)

    print("provisional cache is re-checked, not pinned for a quarter")
    cache = os.path.join(tmp, "fin_%s.json" % ACC.replace("-", ""))
    check("a provisional extract WAS cached", os.path.exists(cache), True)
    install_http(coreg_facts())
    fresh = ec.extract_financials(PRIMARY, ACC, facts=primary_facts(),
                                  report_date=REPORT)
    check("inside the window it is served from cache, still provisional",
          (fresh["period"], fresh.get("provisional")), (PRIOR, True))
    old = time.time() - ec.PROVISIONAL_RECHECK_SECONDS - 60
    os.utime(cache, (old, old))
    after = ec.extract_financials(PRIMARY, ACC, facts=primary_facts(),
                                  report_date=REPORT)
    check("past the window it re-checks and picks up the real period",
          after["period"], REPORT)
    check("...and is no longer provisional", after.get("provisional"), False)

    print("a settled extract is still served straight from cache")
    settled = os.path.join(tmp, "fin_settled.json")
    with open(settled, "w", encoding="utf-8") as f:
        json.dump({"schema": ec.EXTRACT_SCHEMA, "lines": [{"label": "Revenue"}],
                   "period": REPORT, "degraded": False}, f)
    ec._http_get = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must not fetch for a settled cache"))
    hit = ec.extract_financials(PRIMARY, "settled", report_date=REPORT)
    check("no fetch, cache returned verbatim", hit["period"], REPORT)

    print("log tag carries what the prose already carried")
    ec._http_get = real_http
    base = {"covered": True, "eightk": {"count": 0}, "form4": {"filings": 0},
            "periodic": {"form": "10-Q", "filed": "2026-07-24"}}
    check("provisional extract is marked ~prov",
          ec.edgar_tag(dict(base, financials={
              "n_lines": 7, "period": PRIOR, "provisional": True})),
          "E[8k=0; form4=0f; periodic=10-Q@2026-07-24; fin=7@2026-03-31~prov]")
    check("recovered extract names the co-registrant",
          ec.edgar_tag(dict(base, financials={
              "n_lines": 9, "period": REPORT, "co_registrant_cik": COREG})),
          "E[8k=0; form4=0f; periodic=10-Q@2026-07-24; "
          "fin=9@2026-06-30+coreg0000029915]")
    check("a healthy tag is byte-identical to before",
          ec.edgar_tag(dict(base, financials={
              "n_lines": 9, "period": REPORT})),
          "E[8k=0; form4=0f; periodic=10-Q@2026-07-24; fin=9@2026-06-30]")

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("ALL PASS" if not FAILS else "FAILURES: %s" % FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
