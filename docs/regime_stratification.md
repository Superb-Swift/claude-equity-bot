# Phase 2 Q1 Re-Examination — 50-59% vs 60-69% by Regime

*Generated 2026-06-26 · regime = cohort-wide +5d hit rate (compressed &lt;40%, clean &gt;55%, else mixed) · phases split at 2026-06-15 · +5d directional outcomes only*

**Question.** Was the certified **+61.3%** Phase 2 lead of the 50-59% band a real, regime-robust calibration feature, or an artifact carried by compressed/down cohorts? The decisive cell is the **non-compressed** (mixed + clean) Phase 2 row.

## Phase 2

| Stratum | Cohorts | 50-59% (n) | 60-69% (n) | Lead (50-59 − 60-69) |
|---|---:|---:|---:|---:|
| compressed | 4 | 39.5% (38) | 27.8% (18) | **+11.7pt** |
| mixed | 8 | 56.5% (92) | 54.3% (35) | **+2.2pt** |
| clean | 7 | 69.8% (86) | 60.7% (28) | **+9.1pt** |
| **non-compressed** | 15 | 62.9% (178) | 57.1% (63) | **+5.8pt** |
| ALL | 19 | 58.8% (216) | 50.6% (81) | **+8.2pt** |

## Phase 3-A

| Stratum | Cohorts | 50-59% (n) | 60-69% (n) | Lead (50-59 − 60-69) |
|---|---:|---:|---:|---:|
| compressed | 1 | 30.0% (10) | 27.3% (11) | **+2.7pt** |
| mixed | 6 | 50.7% (69) | 68.3% (41) | **-17.6pt** |
| clean | 2 | 72.2% (18) | 86.7% (15) | **-14.4pt** |
| **non-compressed** | 8 | 55.2% (87) | 73.2% (56) | **-18.0pt** |
| ALL | 9 | 52.6% (97) | 65.7% (67) | **-13.1pt** |

## Verdict

Phase 2 50-59 STILL leads in NON-COMPRESSED cohorts: +5.8pt (mixed +2.2pt, clean +9.1pt; compressed +11.7pt, all-Phase-2 +8.2pt).

**→** The guardrail was NOT merely a compressed-regime artifact: 50-59 led 60-69 across regimes in Phase 2, INCLUDING clean cohorts.

Yet within the SAME non-compressed regimes, Phase 3-A shows -18.0pt (all-live -13.1pt).

The relationship has FLIPPED between Phase 2 and now within the same regime stratum -> the more interesting story: SOMETHING CHANGED between Phase 2 and live, and regime composition does not explain it. Candidates: a market/volatility shift the hit-rate flag doesn't capture, signal-generator drift between phases (checkable vs the logs), temporal overfitting of Q1, or live small-sample noise.

NOTE: strata pool small n (especially live 60-69) — read leads as directional, weight by n, and let additional live cohorts firm the sign.
