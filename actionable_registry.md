# Actionable Directional Registry — auto-generated

*Source: `claude_equity_bot_tracker.xlsx` · Signals tab · generated 2026-08-14 15:10. Admission = CHECK 5 clearance at the signal's own gate (BUY ≥ 70%, SELL ≥ 65%), never risk-engine approval. +Nd = trading days. Advisory-only · no orders.*

**Rows: 8 · Episodes: 3 · rows clearing by exactly 0 pts: 2**

## ⚠ READING STANDARD — NOT A VERDICT

INSUFFICIENT TEST CONDITIONS. DP-3C-l's reading standard is NONE and this tool does not change it. No disposition is read from this registry at any n until DP-3C-l is amended by a dated ruling. The ROW and EPISODE bases are both shown because the correct basis is UNRULED (2026-08-13); a figure quoted from one basis alone is incomplete.

## ⚠ ERA SPLIT

ERA SPLIT IS MANDATORY, NOT COSMETIC. Before 2026-08-11 the risk engine approved ZERO directional signals across 57 cohorts -- CHECK 6 rejected them on open-position count. DP-3C-o (iii) demoted CHECK 6 to a non-blocking flag on that date. risk_engine.py L201-207 requires that approval counts date-split here rather than pool, and records the change as one that makes the record look better. Do not quote a pooled hit rate across this line.

| Era | Rows | Resolved +5d | Hit +5d |
|---|---|---|---|
| PRE-DP-3C-o | 6 | 5 | 4 |
| POST-DP-3C-o | 2 | 0 | 0 |

## Both bases

- **ROW basis** — n = 8 · resolved +5d = 5 · hit = **4/5** (80.0%) · avg +5d = +4.8%
- **EPISODE basis** (DP-3C-m coalesced, scored on the opening row) — n = 3 · resolved +5d = 2 · hit = **1/2** (50.0%)

## Rows

| Date | Tkr | Sig | Conf | Gate | Margin | DQ | Price | +5d Ret | Hit 5d | Episode | Era |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-26 | CBRS | SELL | 68.0% | 65% | +3 | MEDIUM | $167.53 | +14.6% | NO | CBRS-20260626 *(open)* | PRE-DP-3C-o |
| 2026-08-04 | NVDA | BUY | 72.0% | 70% | +2 | HIGH | $210.47 | +3.3% | YES | NVDA-20260804 *(open)* | PRE-DP-3C-o |
| 2026-08-05 | NVDA | BUY | 74.0% | 70% | +4 | HIGH | $219.28 | +2.2% | YES | NVDA-20260804 | PRE-DP-3C-o |
| 2026-08-06 | NVDA | BUY | 72.0% | 70% | +2 | HIGH | $218.58 | +3.1% | YES | NVDA-20260804 | PRE-DP-3C-o |
| 2026-08-07 | NVDA | BUY | 72.0% | 70% | +2 | HIGH | $223.14 | +0.9% | YES | NVDA-20260804 | PRE-DP-3C-o |
| 2026-08-10 | NVDA | BUY | 70.0% | 70% | **0** | MEDIUM | $220.37 | pending | — | NVDA-20260804 | PRE-DP-3C-o |
| 2026-08-13 | NVDA | BUY | 70.0% | 70% | **0** | HIGH | $224.88 | pending | — | NVDA-20260813 *(open)* | POST-DP-3C-o |
| 2026-08-14 | NVDA | BUY | 72.0% | 70% | +2 | HIGH | $225.40 | pending | — | NVDA-20260813 | POST-DP-3C-o |

## Episodes

| Episode | Sig | Opened | Last | Sessions | Open conf | Open margin | Hit 5d | Era |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CBRS-20260626 | SELL | 2026-06-26 | 2026-06-26 | 1 | 68.0% | +3 | NO | PRE-DP-3C-o |
| NVDA-20260804 | BUY | 2026-08-04 | 2026-08-10 | 5 | 72.0% | +2 | YES | PRE-DP-3C-o |
| NVDA-20260813 | BUY | 2026-08-13 | 2026-08-14 | 2 | 70.0% | **0** | — | POST-DP-3C-o |
