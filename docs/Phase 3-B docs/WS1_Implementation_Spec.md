# WS1 — Triple-Blend Implementation Spec

*Claude Equity Bot · Phase 3-B WS1 · drafted 2026-07-10 from repo @ `cb79987`. Code-ready companion to `WS1\\\\\\\\\\\\\\\_TripleBlend\\\\\\\\\\\\\\\_Design\\\\\\\\\\\\\\\_Note.md` (the signed design), consuming rulings **DP-W1 = all three components** and <b>DP-W2 = 0.15 / 0.15</b>. Built around a common provider registry so <b>WS3 (commodity context) and Phase 3-C (EDGAR filings) drop in without touching the blend.</b> Advisory-only · no orders · not financial advice.*

\---

## 0 · The unifying abstraction — a provider registry (why EDGAR is free later)

Four things that looked like "per-ticker context" are actually **two families**, and separating them is what makes EDGAR a one-line add later:

|Family|Members|Contributes|When|
|-|-|-|-|
|**Prompt providers** (text → the model reads it)|`news\\\\\\\\\\\\\\\_client` (exists), **WS3 commodity context**, **3-C EDGAR filings**|a text section appended to the LLM prompt|pre-model|
|**Blend providers** (numeric → adjusts conviction)|**C2 sector-backbone**, **C3 cross-asset-regime**|a score in \[−1,+1] feeding the blend engine|post-model|

Both register through one interface:

```python
# context\\\\\\\\\\\\\\\_providers.py  (new)
class ContextProvider:
    name: str
    mode: str            # "prompt" | "blend"
    def fetch(self, ticker, run\\\\\\\\\\\\\\\_cache) -> object:  ...   # cached per run (see §caching)
    def contribute(self, ticker, raw):             ...   # -> str (prompt) | float (blend)

REGISTRY = \\\\\\\\\\\\\\\[ ]           # providers append here; main.py iterates the registry
```

**Consequence for 3-C:** `edgar\\\\\\\\\\\\\\\_client` becomes a `ContextProvider(mode="prompt")` appended to `REGISTRY` — the blend engine, the risk gate, and the logging never change. WS3 commodity context is the same. This spec builds C2/C3 (blend) now and leaves the two prompt-provider slots wired and empty. (Retrofitting `news\\\\\\\\\\\\\\\_client` into the registry is optional cleanup — §7 — not required for WS1.)

\---

## 1 · C2 — Sector-backbone blend provider

**Definition (design note §1).** For a ticker, the trailing trend of its sector ETF, per `sector\\\\\\\\\\\\\\\_map.py`.

**Data + caching.** Uses `schwab\\\\\\\\\\\\\\\_client.get\\\\\\\\\\\\\\\_price\\\\\\\\\\\\\\\_history(etf, days=N\\\\\\\\\\\\\\\_SECTOR)`. The fetch load is **\~7 incremental pulls per run** — `sector\\\\\\\\\\\\\\\_map.sector\\\\\\\\\\\\\\\_reference()` returns 8 unique ETFs across the watchlist, but XLU/SPY/GLD are already fetched as watchlist tickers, so only XLK/XLF/XLE/XLI/XLB/XLP/XLY are new. **Cache each unique ETF once per run** in a `sector\\\\\\\\\\\\\\\_cache` (mirrors the existing `history\\\\\\\\\\\\\\\_cache` in `main.py`); XLK is pulled once and shared by all 5 tech names.

```python
# blend\\\\\\\\\\\\\\\_providers.py
from sector\\\\\\\\\\\\\\\_map import sector\\\\\\\\\\\\\\\_reference
N\\\\\\\\\\\\\\\_SECTOR = 20            # trading-day sector-trend window (DP-W-a; monthly trend)
SECTOR\\\\\\\\\\\\\\\_SCALE = 0.10      # a 10% ETF move = full ±1.0 (DP-W-b)

def sector\\\\\\\\\\\\\\\_score(ticker, sector\\\\\\\\\\\\\\\_cache):
    ref = sector\\\\\\\\\\\\\\\_reference(ticker)
    if ref is None:                       # broad / commodity / unknown -> neutral
        return 0.0, {"ref": None}
    closes = sector\\\\\\\\\\\\\\\_cache.get(ref)        # prefetched per run; None if fetch failed
    if not closes or len(closes) < 2 or not closes\\\\\\\\\\\\\\\[0]:
        return 0.0, {"ref": ref, "note": "no data"}
    ret = closes\\\\\\\\\\\\\\\[-1] / closes\\\\\\\\\\\\\\\[0] - 1.0
    return max(-1.0, min(1.0, ret / SECTOR\\\\\\\\\\\\\\\_SCALE)), {"ref": ref, "ret": ret}
```

Unknown tickers → 0.0 + a one-line WARN (`sector\\\\\\\\\\\\\\\_map.is\\\\\\\\\\\\\\\_mapped()` is False) so the name degrades to base-conviction until mapped.

\---

## 2 · C3 — Cross-asset-regime blend provider

**Definition (design note §1; DP-W7 = SPY vs GLD).** One market-wide risk-on/off scalar per run, shared by every ticker that day: equities' trend relative to the gold safe-haven.

```python
N\\\\\\\\\\\\\\\_REGIME = 20            # trading-day regime window (DP-W-a)
REGIME\\\\\\\\\\\\\\\_SCALE = 0.10

def regime\\\\\\\\\\\\\\\_score(regime\\\\\\\\\\\\\\\_cache):
    spy = regime\\\\\\\\\\\\\\\_cache.get("SPY"); gld = regime\\\\\\\\\\\\\\\_cache.get("GLD")
    if not (spy and gld and spy\\\\\\\\\\\\\\\[0] and gld\\\\\\\\\\\\\\\[0]):
        return 0.0, {"note": "no data"}
    spy\\\\\\\\\\\\\\\_ret = spy\\\\\\\\\\\\\\\[-1] / spy\\\\\\\\\\\\\\\[0] - 1.0
    gld\\\\\\\\\\\\\\\_ret = gld\\\\\\\\\\\\\\\[-1] / gld\\\\\\\\\\\\\\\[0] - 1.0
    risk = spy\\\\\\\\\\\\\\\_ret - gld\\\\\\\\\\\\\\\_ret              # >0 equities beating gold = risk-on
    return max(-1.0, min(1.0, risk / REGIME\\\\\\\\\\\\\\\_SCALE)), {"spy": spy\\\\\\\\\\\\\\\_ret, "gld": gld\\\\\\\\\\\\\\\_ret}
```

Computed **once per run** (SPY/GLD are watchlist tickers — reuse their fetched history; no incremental pulls). `S\\\\\\\\\\\\\\\_regime` is identical for all tickers in a session — it scales conviction by the day's regime, not by the name.

\---

## 3 · The blend engine

**Ruled parameters:** `w\\\\\\\\\\\\\\\_sector = w\\\\\\\\\\\\\\\_regime = 0.15`, `FLOOR = 35`. Direction integrity: the base owns BUY/HOLD/SELL; overlays only modulate conviction (design note §2).

```python
# blend\\\\\\\\\\\\\\\_engine.py
W\\\\\\\\\\\\\\\_SECTOR, W\\\\\\\\\\\\\\\_REGIME, FLOOR = 0.15, 0.15, 35

def blend\\\\\\\\\\\\\\\_confidence(signal, s\\\\\\\\\\\\\\\_sector, s\\\\\\\\\\\\\\\_regime):
    """conf\\\\\\\\\\\\\\\_raw -> conf\\\\\\\\\\\\\\\_blend. Returns (conf\\\\\\\\\\\\\\\_blend, meta). Direction unchanged."""
    raw = signal.get("confidence\\\\\\\\\\\\\\\_raw", signal.get("confidence"))
    if not isinstance(raw, (int, float)) or raw <= 0:      # parse-error -> untouched
        return raw, {"active": False}
    d = {"BUY": +1, "SELL": -1}.get(str(signal.get("signal")).upper(), 0)   # HOLD -> 0
    if d == 0:                                             # DP-W3: HOLD unchanged
        return int(raw), {"active": False, "dir": 0, "sec": s\\\\\\\\\\\\\\\_sector, "reg": s\\\\\\\\\\\\\\\_regime}

    def agree(score):                                     # +1 confirm, -1 oppose, 0 flat
        return 0 if abs(score) < 1e-9 else (1 if (score > 0) == (d > 0) else -1)

    adj = (W\\\\\\\\\\\\\\\_SECTOR \\\\\\\\\\\\\\\* agree(s\\\\\\\\\\\\\\\_sector) \\\\\\\\\\\\\\\* abs(s\\\\\\\\\\\\\\\_sector)
           + W\\\\\\\\\\\\\\\_REGIME \\\\\\\\\\\\\\\* agree(s\\\\\\\\\\\\\\\_regime) \\\\\\\\\\\\\\\* abs(s\\\\\\\\\\\\\\\_regime))
    conf\\\\\\\\\\\\\\\_blend = max(FLOOR, min(100, round(raw \\\\\\\\\\\\\\\* (1 + adj))))
    return conf\\\\\\\\\\\\\\\_blend, {"active": adj != 0, "dir": d, "sec": s\\\\\\\\\\\\\\\_sector,
                        "reg": s\\\\\\\\\\\\\\\_regime, "adj": adj, "raw": raw}
```

**T3 (design note §2):** the rule references direction-agreement × overlay-magnitude and a continuous confidence — never confidence **bands** or their ordering. Compliant.

\---

## 4 · Pipeline wiring — compose with D1, run shadow-parallel

**Three-channel confidence** (extends the WS2 two-channel harness):

```
claude\\\\\\\\\\\\\\\_signal -> conf\\\\\\\\\\\\\\\_raw --\\\\\\\\\\\\\\\[blend\\\\\\\\\\\\\\\_confidence: C2+C3]--> conf\\\\\\\\\\\\\\\_blend --\\\\\\\\\\\\\\\[apply\\\\\\\\\\\\\\\_conf\\\\\\\\\\\\\\\_damping: D1]--> conf\\\\\\\\\\\\\\\_op -> risk gate -> log
```

`main.py` / `process\\\\\\\\\\\\\\\_ticker` per ticker, inside `handle\\\\\\\\\\\\\\\_phase3a` BEFORE the existing D1 call:

```python
s\\\\\\\\\\\\\\\_sec, sec\\\\\\\\\\\\\\\_meta = sector\\\\\\\\\\\\\\\_score(ticker, sector\\\\\\\\\\\\\\\_cache)
s\\\\\\\\\\\\\\\_reg, reg\\\\\\\\\\\\\\\_meta = regime\\\\\\\\\\\\\\\_score(regime\\\\\\\\\\\\\\\_cache)          # same value all tickers
conf\\\\\\\\\\\\\\\_blend, blend\\\\\\\\\\\\\\\_meta = blend\\\\\\\\\\\\\\\_confidence(signal, s\\\\\\\\\\\\\\\_sec, s\\\\\\\\\\\\\\\_reg)
signal\\\\\\\\\\\\\\\["confidence\\\\\\\\\\\\\\\_blend"] = conf\\\\\\\\\\\\\\\_blend
signal\\\\\\\\\\\\\\\["sector\\\\\\\\\\\\\\\_score"], signal\\\\\\\\\\\\\\\["regime\\\\\\\\\\\\\\\_score"] = round(s\\\\\\\\\\\\\\\_sec, 3), round(s\\\\\\\\\\\\\\\_reg, 3)
# D1 then damps conf\\\\\\\\\\\\\\\_blend -> conf\\\\\\\\\\\\\\\_op (change apply\\\\\\\\\\\\\\\_conf\\\\\\\\\\\\\\\_damping to read
#   confidence\\\\\\\\\\\\\\\_blend as its input, confidence\\\\\\\\\\\\\\\_raw still stamped separately)
```

**Shadow, not primary (design note §3).** During the acceptance window the **base signal stays the official advisory output** — `conf\\\\\\\\\\\\\\\_blend` is logged and resolved alongside it but does not yet drive the risk gate's confidence. Concretely: keep `signal\\\\\\\\\\\\\\\["confidence"]` on the base→D1 path as today; carry `confidence\\\\\\\\\\\\\\\_blend` (and its own damped variant `confidence\\\\\\\\\\\\\\\_blend\\\\\\\\\\\\\\\_op` if you want the blend's gate view) purely for measurement. Only on a G2 pass do we switch the gate to the blend. This is the measure-first switch, one line, flipped after the verdict.

**No double-count with D1** (design note §1): C2 reads the *sector's* trend, C3 the *market's*, D1 the *ticker's own* trailing return — three disjoint scopes.

\---

## 5 · Logging \& tracker

**Log line** — append after the existing `H1\\\\\\\\\\\\\\\[…] | S1\\\\\\\\\\\\\\\[…] | D\\\\\\\\\\\\\\\[…]`:

```
B\\\\\\\\\\\\\\\[sec=<s\\\\\\\\\\\\\\\_sector>; reg=<s\\\\\\\\\\\\\\\_regime>; w=0.15/0.15; base=<conf\\\\\\\\\\\\\\\_raw>; blend=<conf\\\\\\\\\\\\\\\_blend>]
```

**Signal JSON** — add `confidence\\\\\\\\\\\\\\\_blend`, `sector\\\\\\\\\\\\\\\_score`, `regime\\\\\\\\\\\\\\\_score`.

**Tracker** — a parallel **`Blend Conf %`** column on the Signals tab (or a `Blend` tab keyed date+ticker), so blend-vs-base joins on the same +5d/+10d/+20d resolutions — no second resolution pass. `parse\\\\\\\\\\\\\\\_log\\\\\\\\\\\\\\\_to\\\\\\\\\\\\\\\_tracker.py` reads `confidence\\\\\\\\\\\\\\\_blend` from the JSON into that column; base `Conf %` is unchanged.

**Era stamp** — `PROMPT\\\\\\\\\\\\\\\_VARIANT` `A-S1D1` → **`A-S1D1-B1`** at deploy (a generator-version stamp; single live arm, not an A/B — the A/B program stays terminated). `t2\\\\\\\\\\\\\\\_check.py` and the monitors already stratify on the stamp.

\---

## 6 · Smoke + acceptance

**Smoke (PM diagnostic run, per convention):** verify banner `A-S1D1-B1`; every line carries the `B\\\\\\\\\\\\\\\[…]` tag + `confidence\\\\\\\\\\\\\\\_blend` in the JSON; `sector\\\\\\\\\\\\\\\_cache` shows \~7 ETF pulls (XLK once); `regime\\\\\\\\\\\\\\\_score` identical across tickers; a spot-check by hand (e.g. a tech BUY with XLK up and risk-on → `conf\\\\\\\\\\\\\\\_blend > conf\\\\\\\\\\\\\\\_raw`; the same BUY with XLK down → `conf\\\\\\\\\\\\\\\_blend < conf\\\\\\\\\\\\\\\_raw`); parsers still 24/24; the base `Conf %` column unchanged (shadow-parallel intact). Re-seed S1 state after the PM run.

**Acceptance — Gate G2 (design note §6):** blend deployed shadow-parallel; **≥ N = 5** blended cohorts +5d-resolved; blend **no-worse** than base on +5d accuracy **and** magnitude, cross-validated (leave-one-cohort-out — no single cohort carries it); T3 throughout. → **VERDICT** adopt (switch the gate to the blend) or reject-and-retain-base; or **DESCOPE**.

\---

## 7 · Drop-in points for WS3 + EDGAR (built now, filled later)

The registry (§0) leaves two prompt-provider slots wired:

* **WS3 — commodity context:** `commodity\\\\\\\\\\\\\\\_context.py` → `ContextProvider(mode="prompt")`; appends a commodities section to the prompt for CORN/GLD/AG (Path B). Registers in `REGISTRY`; no blend change.
* **Phase 3-C — EDGAR:** `edgar\\\\\\\\\\\\\\\_client.py` → `ContextProvider(mode="prompt")`; appends Form 4 / 8-K / 10-Q·10-K MD\&A extracts. Registers in `REGISTRY`; the E3 parser-audit + E4 measurement pre-registration (per the criteria doc) are its own spec — but the *integration surface is this one line*, which is exactly what E1 meant by "WS3 is EDGAR's technical template."

Optional cleanup: retrofit the existing `news\\\\\\\\\\\\\\\_client` call into the registry as the reference prompt-provider so all three text sources share one path. Nice-to-have, not on the WS1 critical path.

\---

## 8 · File manifest

|File|Δ|What|
|-|-|-|
|`sector\\\\\\\\\\\\\\\_map.py`|NEW|ticker→sector-ETF + category policy (delivered; all 24 covered)|
|`context\\\\\\\\\\\\\\\_providers.py`|NEW|the registry + `ContextProvider` interface (the EDGAR-forward surface)|
|`blend\\\\\\\\\\\\\\\_providers.py`|NEW|`sector\\\\\\\\\\\\\\\_score` (C2) + `regime\\\\\\\\\\\\\\\_score` (C3)|
|`blend\\\\\\\\\\\\\\\_engine.py`|NEW|`blend\\\\\\\\\\\\\\\_confidence` (the 0.15/0.15 rule)|
|`main.py`|edit|`sector\\\\\\\\\\\\\\\_cache`/`regime\\\\\\\\\\\\\\\_cache` (once-per-run); call blend before D1; `A-S1D1-B1`; `B\\\\\\\\\\\\\\\[…]` tag|
|`risk\\\\\\\\\\\\\\\_engine.py`|edit|`apply\\\\\\\\\\\\\\\_conf\\\\\\\\\\\\\\\_damping` reads `confidence\\\\\\\\\\\\\\\_blend` as input (raw still stamped)|
|`claude\\\\\\\\\\\\\\\_signal.py`|edit|(only if retrofitting news into the registry — §7; else untouched)|
|`parse\\\\\\\\\\\\\\\_log\\\\\\\\\\\\\\\_to\\\\\\\\\\\\\\\_tracker.py`|edit|read `confidence\\\\\\\\\\\\\\\_blend` → `Blend Conf %` column|
|tracker|edit|add `Blend Conf %` column / `Blend` tab|

**Sequence:** land `sector\\\\\\\\\\\\\\\_map.py` + the three blend files + wiring → smoke on a PM run → shadow-parallel live → first G2 read at deploy + 5 cohorts. WS3 and EDGAR register into the same rails when their specs land.

\---

*Advisory-only · no orders · not financial advice.*

