# E4-2 Volatility-Tier Table — FROZEN 2026-08-10

*Claude Equity Bot · Phase 3-C · built and frozen per DP-3C-n §3.3 (ruled 2026-08-05), entered as change-order step 8b. This table is a **go-live prerequisite**, on equal footing with the E3 parser audit (step 8). Advisory-only · no orders · not financial advice.*

## Status

**FROZEN as of 2026-08-10, before the E4-2 clock has started (no post-deploy cohort has resolved).** Per §3.3: *"Freezing the table after the first E4 cohort resolves would be fitting a control to the data it exists to control for."* This table must **not** be recomputed once EDGAR go-live begins. If a ticker's classification is ever revisited, it is a new dated ruling, not a re-run of this script.

## Provenance `[V]`

Computed 2026-08-10 from `logs\claude_equity_bot_tracker.xlsx`, sheet `Signals`, all rows with a numeric `Return +5d` (column K) as of this freeze date — 52-53 of 57-58 rows per ticker, the remainder pending +5d resolution. Metric per ticker: **median of `|Return +5d|`** across every resolved row for that ticker, regardless of signal (HOLD/BUY/SELL) — this is a name-level volatility characteristic, not conditioned on what the model said that day. Scope: the 15 tickers covered by EDGAR (T-A + T-B per §1 of the pre-registration) — the 8 T-C "dark" names and CBRS (DP-3, skipped) are not stratified because they never populate the ADJACENT/COVERED-QUIET arms.

Tiers are **terciles** — the 15 covered tickers ranked by median |+5d| and cut 5/5/5 into LOW / MID / HIGH.

## The table

| Tier | Ticker | n resolved | n pending | Median \|Return +5d\| |
|---|---|---|---|---|
| LOW | JPM | 53 | 5 | 1.834% |
| LOW | GLD | 53 | 5 | 1.931% |
| LOW | CORN | 52 | 5 | 1.990% |
| LOW | RTX | 53 | 5 | 2.021% |
| LOW | WMT | 53 | 5 | 2.559% |
| MID | GM | 53 | 5 | 2.592% |
| MID | PM | 53 | 5 | 3.188% |
| MID | FTI | 53 | 5 | 3.201% |
| MID | PWR | 53 | 5 | 3.343% |
| MID | NVDA | 53 | 5 | 3.595% |
| HIGH | DOW | 53 | 5 | 3.598% |
| HIGH | NKE | 53 | 5 | 3.598% |
| HIGH | AAPL | 53 | 5 | 3.779% |
| HIGH | MSFT | 53 | 5 | 3.910% |
| HIGH | SND | 53 | 5 | 5.517% |

## Flagged, not smoothed over: the MID/HIGH boundary is a near-tie

NVDA (MID, 3.595%) sits **0.003 percentage points** below the DOW/NKE tie (HIGH, 3.598%) that opens the HIGH tier — the closest boundary in the table by two orders of magnitude versus every other adjacent gap (next-closest is DOW/NKE's own exact tie at 3.598%, then NKE→AAPL at 0.181pp). This is recorded here, at freeze time, rather than left to be noticed after a read comes back sensitive to it. **Per DP-3C-n's own freeze rule, this boundary is not adjustable once frozen** — a robustness note belongs in the E4-2 write-up (e.g., report the read with NVDA reclassified to HIGH as a sensitivity check), not a re-cut of the table.

## How this table is used (§3.3, restated for reference)

For covered tickers that cannot supply both the ADJACENT and COVERED-QUIET arms at n ≥ 3 each (the §3.2 primary within-ticker paired-difference design), pool by the tier assigned above: compare ADJACENT vs COVERED-QUIET **within tier**, pooled across tiers. Report the count of tickers reading under §3.2 (primary) versus §3.3 (this fallback) at every read — a read dominated by the fallback is weaker than one dominated by the primary and must say so per §3.3.

*Advisory-only · no orders · not financial advice.*
