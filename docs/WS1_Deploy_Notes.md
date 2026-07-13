# WS1 Deploy Notes — Triple Blend (shadow-parallel, era A-S1D1-B1)

*Claude Equity Bot · Phase 3-B WS1 · 2026-07-10 · build base: repo @ `cb79987`. Implements `WS1_Implementation_Spec.md` with rulings DP-W1 (all three components) + DP-W2 (0.15/0.15). Advisory-only · no orders · not financial advice.*

## 1 · What shipped (6 files: 4 new, 2 edited)

| File | Δ | Role |
|---|---|---|
| `sector_map.py` | NEW | ticker→sector-ETF + category policy (all 24 covered) |
| `context_providers.py` | NEW | provider registry — the EDGAR-forward spine (blend + prompt modes) |
| `blend_providers.py` | NEW | C2 sector-backbone + C3 cross-asset-regime scores (registered) |
| `blend_engine.py` | NEW | the 0.15/0.15 combination rule (direction-preserving, T3-safe) |
| `main.py` | ~72 ln | prefetch blend context once/run; thread `blend_caches`; compute the shadow blend after base D1; `B[…]` tag; era `A-S1D1-B1` |
| `risk_engine.py` | ~58 ln | extracted `damp_confidence_value` (reused on the blend channel); **base path byte-identical** |

## 2 · The design in one paragraph

The blend runs **shadow-parallel**: the base signal stays the official advisory output (`confidence` = D1(raw), unchanged), while the blend is computed on the model's raw confidence, damped through the **same** D1, and written to `confidence_blend` — logged and measured for G2 but **not driving the risk gate**. Three confidence channels now ride every line: `confidence_raw` (model) → `confidence` (base op, official) and, in parallel, `confidence_blend` (blend op, candidate). The blend lives **entirely in the logs** — **no tracker schema change**, so `h1_lag_trace` / `t2_check` / the formulas are untouched. Trend scopes stay disjoint: C2 = sector, C3 = market, D1 = ticker — no double-counting.

## 3 · Parameters & conventions

| Item | Value |
|---|---|
| Components | C2 sector-backbone + C3 cross-asset-regime (DP-W1) |
| Weights | sector 0.15 / regime 0.15 (DP-W2; fixed, pre-registered, **unfitted**) |
| Windows / scales | 20-day trend, 10% = full ±1.0 (both C2 and C3) |
| Regime proxy | SPY − GLD (DP-W7; both on the watchlist) |
| HOLD | overlays leave HOLD confidence unchanged (DP-W3) |
| FLOOR | 35 (matches D1) |
| Era stamp | `A-S1D1-B1` (single live arm, not an A/B) |
| Log tag | `B[sec=…; reg=…; w=0.15/0.15; base=<raw>; blend=<pure>; blend_op=<blend after D1>]` |
| JSON fields | `confidence_blend`, `sector_score`, `regime_score` |
| Fetch load | ~7 incremental price pulls/run (unique sector ETFs; XLU/SPY/GLD already fetched) |

## 4 · Test evidence (sandbox)

| # | Test | Result |
|---|---|---|
| T1 | Base D1 path vs the **original** `apply_conf_damping`, 4000 random cases | **4000/4000 identical** (confidence, confidence_raw, damp) |
| T2 | Blend math table — direction integrity, confirm/oppose symmetry, HOLD untouched, floor 35, parse-error | PASS |
| T3 | C2 clips at ±1; C3 = SPY−GLD gap; broad/commodity → neutral; unknown → neutral + flag | PASS |
| T4 | End-to-end arithmetic (confirm +24%, oppose −19.5%) | PASS |
| T5 | Integration: registry → `run_blend_scores` → `blend_confidence` → dual D1 → `B[…]` tag → JSON parses | PASS |
| T6 | `parse_log_to_tracker` output byte-identical to original; tracker gets **base** operative; blend stays in log | PASS |

## 5 · Deploy runbook

1. Add the 4 new files + replace `main.py` / `risk_engine.py` (`git diff --stat` matches §1).
2. **PM diagnostic smoke** (PM = diagnostic-only): `python main.py`, then verify — banner `A-S1D1-B1`; log line `"[WS1] blend context: N sector ETF(s), regime ['GLD','SPY'] loaded"` (~7 ETFs); every signal line carries `B[…]` + `confidence_blend`/`sector_score`/`regime_score` in the JSON; a hand spot-check (a tech BUY with its XLK up + risk-on → `blend > raw`; the same with XLK down → `blend < raw`); **base `Conf %` unchanged** in the paste file (shadow-parallel intact); `analyze_log` + `parse_log_to_tracker` still 24/24.
3. **Re-seed S1 state** after the PM run (unchanged discipline).
4. Go live next AM. Daily flow unchanged; the blend accrues silently in the logs.

## 6 · Acceptance — Gate G2

Blend deployed shadow-parallel; **≥ N=5** blended cohorts +5d-resolved; blend **no-worse** than base on +5d accuracy **and** magnitude, cross-validated (leave-one-cohort-out — no single cohort carries it); T3 throughout. Read from the logs: `confidence_blend` per cohort joined to the tracker's +5d resolutions by date+ticker (a small reader, like the raw-channel `h1_lag_trace --raw-from-logs`, to be added). → **VERDICT** adopt (flip the gate to the blend — one line) / reject-and-retain-base, or **DESCOPE**.

## 7 · Open items

- **Blend evaluation reader** — the log→+5d base-vs-blend comparator (not built here; the G2 measurement tool, analogous to the raw-channel acceptance read).
- **WS3 + EDGAR** — register into `context_providers` as prompt providers (see the EDGAR scope spec); `run_prompt_context` is the wired hook.
- Optional: retrofit `news_client` into the registry as the reference prompt provider.

---

*Advisory-only · no orders · not financial advice.*
