# Phase 3-C — EDGAR Filing Context: Scope Spec

*Claude Equity Bot · Phase 3-C · DRAFT v1.0 · drafted 2026-07-10 · the E1 scope instrument + E3/E4 pre-registration from `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1`, built on the WS1 provider registry (`context_providers.py`, now live @ `cb79987`+WS1). Advisory-only · no orders · not financial advice. Not active until Phase 3-B exit (Part I) is signed — this is the scope, not the build.*

---

## 0 · Objective & fit (E1)

Give the model **primary-source SEC filing context** per ticker, so signals can react to insider activity and material events rather than price + news alone. `edgar_client.py` is the **first prompt-provider** on the WS1 registry: `ContextProvider(mode="prompt")`, appended to `REGISTRY`, surfaced by `run_prompt_context()` — the blend engine, risk gate, and logging are untouched. This is the concrete payoff of "WS3 is EDGAR's technical template."

**Filing set (from the 2026-06-15 scoping):** Form 4 (insider transactions), 8-K (material events), and 10-Q/10-K MD&A extracts. One client, per-ticker, cached.

---

## 1 · Data path & access (E3 preconditions)

**SEC EDGAR REST API — no key, but strict etiquette.**

| Item | Value |
|---|---|
| Ticker → CIK | `https://www.sec.gov/files/company_tickers.json` (fetch once, cache; CIK zero-padded to 10 digits) |
| Filing history | `https://data.sec.gov/submissions/CIK{cik10}.json` — form types, accession numbers, dates; includes `insiderTransactionForIssuerExists` |
| Full-text search | `https://efts.sec.gov/LATEST/search-index?q=…&forms=…&dateRange=…` (filings since 2001) |
| Filing documents | `https://www.sec.gov/Archives/edgar/…` (from accession numbers) |
| **User-Agent** | **MANDATORY** — `SEC_USER_AGENT` in `.env` (e.g. `"Rob <email>"`); missing/generic → **403 Forbidden** and a ~10-min IP block. (Tier-0: `.env` is a secret; never commit.) |
| Rate limit | **10 req/sec per IP** → 429 + temp block; add a **≥120 ms** delay between calls |
| Caching | filings change ~quarterly — cache the CIK map (static) and per-ticker submissions per run; only re-fetch documents on a new accession |

**Environment note.** The bot's Windows host reaches these fine; if run under restricted egress, add `data.sec.gov`, `efts.sec.gov`, `www.sec.gov` to the allowlist. **Graceful degradation** (E3): any fetch failure / missing filing → the EDGAR prompt section is **omitted**, the run continues, the signal proceeds on price+news (exactly how a missing `S1`/trajectory section degrades today).

---

## 2 · Extraction → prompt section

For each ticker (mapped to CIK), assemble a compact section the model reads:

```
--- SEC FILINGS (recent, as of <run date>) ---
8-K (material events, last 30d): 2 — [Item 2.02 Results; Item 5.02 Officer change]
Form 4 (insider, last 30d): 3 buys / 1 sell  (net direction: buying)
Latest periodic: 10-Q filed 2026-05-01 — MD&A extract: "<3–5 key sentences>"
```

- **8-K:** count + item codes/labels in the window (item codes carry the event type — e.g. 2.02 earnings, 5.02 officer change, 1.01 material agreement).
- **Form 4:** net insider buy/sell tally in the window (direction + rough magnitude).
- **10-Q/10-K MD&A:** the heaviest piece — MD&A is long. **DP-3C-a:** full extract vs a pre-summarization pass vs a recency flag only. Default: a short bounded extract (first N chars of MD&A) + filed-date, no separate LLM call in v1.

Windows/counts are parameters (DP-3C-b). The section is **text only** — EDGAR shapes the signal through the model's reasoning, not by touching confidence (that stays the blend's job).

---

## 3 · Provider shape + the one hook

```python
# edgar_client.py
from context_providers import Provider, register
def edgar_context(ticker, caches):
    cik = caches["edgar_cik"].get(ticker.upper())        # from the cached CIK map
    if cik is None: return "", {"note": "no CIK"}
    subs = caches["edgar_subs"].get(cik) or fetch_submissions(cik)   # cached per run
    section = build_filings_section(subs, ticker)        # 8-K / Form 4 / MD&A
    return section, {"filings": summarize_counts(subs)}
register(Provider("edgar", "prompt", edgar_context))
```

**The single integration hook (add at 3-C build):** `main.py` calls `run_prompt_context(ticker, caches)` and passes the text into `get_signal(...)`, which appends it as a prompt section — **one parameter** on `get_signal` (`extra_context: str = ""`). That is the entire wiring; `run_prompt_context` already exists and returns `""` until EDGAR registers.

**Log tag** (following the H1/S1/D/B precedent): `E[8k=2; form4=+3/-1; periodic=10-Q@2026-05-01]`, appended after `B[…]`.

---

## 4 · Deployment mode (E2 — resolve the 6/15 conflict)

The 6/15 scoping said "A/B arm," but the A/B program was **terminated** at the 3-A closeout. **Ruling needed (DP-2):**
- **(a, recommended)** single-arm era-stamp deploy — label extends `A-S1D1-B1` → **`A-S1D1-B1-E1`**; pre/post-EDGAR cohorts stratify on the stamp (consistent with S1/D1/B1).
- **(b)** a formal A/B re-open via its own worksheet entry (reverses a closed decision — higher bar).

---

## 5 · Pre-deploy PARSER AUDIT (E3 — the ACCOUNT_RE lesson)

**This is non-negotiable and comes BEFORE go-live**, because a tag/era change silently broke the tracker parser at the 3-B cutover (`ACCOUNT_RE` hardcoded `2 DRY RUN|3-A`). Checklist:
1. Add `E[…]` to the known trailing-tag set; confirm `analyze_log.py` + `parse_log_to_tracker.py` **tolerate it** (they tolerate H1/S1/D/B by pattern — verify, don't assume).
2. Confirm the era label `A-S1D1-B1-E1` parses (both parsers are phase/label-agnostic as of the WS2 fix — re-verify).
3. Run both parsers on a **synthetic 3-C line** and assert 24/24, real Accounts, base operative confidence unchanged — exactly the T5/T6 checks used for WS1.
4. Only then deploy on a PM diagnostic run.

---

## 6 · Measurement pre-registration (E4)

Endpoints fixed **before** go-live (the small-n scan caveat from `WS2_Deploy_Notes.md §4b` applies — table-primary reads):

| Endpoint | What | Read |
|---|---|---|
| **E4-1 DQ-mix shift** | does filing context change the HIGH/MED/LOW distribution? | descriptive, pre/post era |
| **E4-2 filing-adjacent accuracy** | +5d/+10d/+20d accuracy on signals within K days of an 8-K/Form-4, EDGAR-on vs the pre-EDGAR base | table read over ≥ N cohorts; scan confirmatory only at n ≥ ~8–10 |
| **E4-3 event-window behavior** | confidence/direction change around material 8-K dates | trace-table, WMT/GM-style |

**DP-4 default:** filing presence/absence does **not** feed `data_quality` in v1 — measure first, couple later only if E4-2 supports it. **T3:** all reads are EDGAR-on-vs-base accuracy, never band-ordering.

---

## 7 · Constraint compliance (E5)

Advisory-only unchanged; T1/T3 untouched; KEEP 70% unchanged. **CBRS (DP-3):** EDGAR **skips CBRS** until the Q4 2026 Path-A review (a <6-month IPO with thin filing history and violent vol — consistent with its standing exclusion). Descopes stay descoped; single live arm continues.

---

## 8 · Sequencing (E6) & files

**Sequence:** Part I (3-B exit gates G1–G6) signed → 3-C kickoff review checks E1–E6 → build → PM smoke → shadow/era-stamped live → first read at deploy + N cohorts. Default **sequential** (DP-5); overlap only by explicit scope ruling.

| File | Δ |
|---|---|
| `edgar_client.py` | NEW — the prompt provider + SEC fetch/cache/extract |
| `context_providers.py` | none (registry already supports `mode="prompt"`) |
| `main.py` | small — call `run_prompt_context`; pass `extra_context` to `get_signal`; `E[…]` tag; era `…-E1` |
| `claude_signal.py` | one param — `get_signal(..., extra_context="")` appends the section |
| `.env` | add `SEC_USER_AGENT` (secret) |
| parsers | **no change** — audited (E3) to tolerate `E[…]` + the era label |

---

## 9 · Open decision points

| DP | Question | Default |
|---|---|---|
| **DP-2** (E2) | EDGAR deploy mode | single-arm era stamp `…-E1` |
| **DP-3** (E5) | CBRS under EDGAR | skip until Q4 2026 Path-A review |
| **DP-4** (E4) | filings feed `data_quality`? | no coupling in v1 |
| **DP-3C-a** | MD&A: full extract / pre-summarize / recency flag | bounded extract + filed-date, no extra LLM call |
| **DP-3C-b** | filing windows + counts | 8-K/Form-4 last 30d; latest periodic |
| **DP-3C-c** | Form-4 magnitude | net direction + rough $; refine later |

---

## 10 · Cross-references

- `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1` — E1–E6 gates, DP-1..5 (this doc is the E1 instrument + E3/E4 pre-registration).
- `WS1_Implementation_Spec.md` / `context_providers.py` — the registry EDGAR rides; `run_prompt_context` is the wired hook.
- `WS1_Deploy_Notes.md` — the prompt-provider slot; the parser-audit precedent (T5/T6).
- `Daily_Workflow_v4_0_Phase3B.docx` / `Phase3A_Closeout_Memo.md` — constraints (advisory-only, T1/T3, KEEP 70%, CBRS).

---

*Status: DRAFT v1.0 — scope for review; activates after 3-B exit is signed. Advisory-only · no orders · not financial advice.*
