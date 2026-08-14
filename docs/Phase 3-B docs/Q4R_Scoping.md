# Q4-R Scoping — Data-Quality as a Signal (and why not to down-weight it naively)

*Claude Equity Bot · Phase 3-B · DRAFT v1.0 · 2026-07-13 · spun off from the Q1-R diagnostic (`Q1R_Diagnostic_Memo.md`). Frames the DQ-weighting question and pre-registers the investigation. This is a SCOPE, not a build — and its provisional conclusion is "don't build the obvious lever." Source: `tracker_with_registry.xlsx`, `claude_signal.py`. Advisory-only; not financial advice.*

---

## 0 · Framing (conclusions first)

The Q1-R diff surfaced that, live, **data quality separates accuracy more than any confidence band** (HIGH 58.6% vs MEDIUM 43.1% on HOLDs). The tempting move is to **down-weight MEDIUM-DQ**. **On inspection, that is probably wrong** — the gap is **largely an instrument-volatility artifact**, not model miscalibration. So Q4-R is not "build a DQ down-weight"; it is **"determine whether any DQ signal survives a volatility control, and if so, use it correctly."** Provisional disposition: **no naive DQ lever**; investigate the confound first; the DQ signal's best near-term use is monitoring/EDGAR-targeting, not mechanical damping.

This is the same lesson as Q1-R: a fixed-threshold quality/confidence rule (the ±3% HOLD band; the 50-59 guardrail) can measure a **confound** rather than signal. The informative move is volatility-aware, not threshold-based.

---

## 1 · The raw finding (the tempting premise)

`data_quality` is the **model's self-assessment** in its JSON schema (HIGH/MEDIUM/LOW) — chiefly driven by input completeness (news "if available", fundamentals omitted for ETFs, etc.), not a mechanical pipeline metric. Live (6/15+):

| Live HOLDs (dominant signal) | n | +5d accuracy (±3%) |
|---|---|---|
| HIGH-DQ | 222 | 58.6% |
| MEDIUM-DQ | 109 | **43.1%** |

Robust across weeks (MEDIUM: 28% → 48% → 49% → 45%; consistently below HIGH). MEDIUM is **situational, not a broken-ticker set**: 18 of 19 MEDIUM tickers are *mixed* HIGH/MED day-to-day (only SND is persistently MEDIUM). It concentrates in **news/fundamentals-thin instruments** — commodities (CORN, GLD), miners (AG), ETFs (AIQ), and a new IPO (CBRS).

## 2 · The confound test — it's volatility, mostly

| Live HOLDs | mean \|+5d move\| | median | >3% breach |
|---|---|---|---|
| HIGH-DQ | 3.23% | 2.38% | 41% |
| MEDIUM-DQ | **4.65%** | **4.22%** | **57%** |

MEDIUM-DQ instruments **move ~2x more** (median 4.22% vs 2.38%), so they breach the fixed ±3% "HOLD = right" band far more — a property of the instruments, not the model. The MEDIUM-concentrated names are inherently volatile:

| MEDIUM-heavy | mean \|move\| | Stable HIGH-DQ | mean \|move\| |
|---|---|---|---|
| CBRS | 11.6% | XLU | 1.1% |
| AG | 6.9% | SCHD | 1.2% |
| SND | 4.8% | JPM | 1.4% |
| NVDA | 3.8% | PM | 2.0% |

**A CBRS (new IPO, 11.6% swings) or AG (silver, 6.9%) HOLD breaching ±3% is not the model being wrong — it's the instrument.** Down-weighting the model's confidence there penalizes correct behavior.

## 3 · The reframed question

The naive premise ("MEDIUM is weak → down-weight it") conflates two things. Q4-R must separate them:

1. **Residual calibration** — *after controlling for volatility*, does MEDIUM-DQ still underperform HIGH-DQ? (Bucket by realized/expected volatility; compare DQ within buckets.) Only a residual gap here would justify a DQ-based confidence adjustment.
2. **Metric fairness** — is the **fixed ±3% HOLD band** itself the wrong yardstick for volatile instruments? A volatility-scaled "right" band (e.g. ±1σ of the name's typical move) may show the model is *equally* calibrated across DQ once the band adapts.
3. **Best use of the DQ signal** — if there's no residual miscalibration, DQ is still informative *about the instrument* (thin data ↔ volatile), which is useful for **monitoring** and **input-targeting** (EDGAR), not for damping.

## 4 · Pre-registered investigation (the actual Q4-R work)

Before any lever is designed:
- **Q4-1 volatility-controlled DQ analysis** — partition live HOLDs into volatility buckets (by trailing realized vol or median \|move\| per ticker); within each bucket, compare HIGH vs MEDIUM accuracy. **Endpoint:** residual HIGH−MEDIUM gap after control. If ≈ 0 → the DQ gap is fully volatility; **no DQ lever**.
- **Q4-2 volatility-scaled metric** — recompute "Right?(5d)" with a per-instrument band (±k·typical move) and re-check whether DQ (and the whole 50-59/60-69 picture) still separates. **Endpoint:** does calibration equalize?
- **Q4-3 (only if a residual survives)** — design a DQ-based intervention under §5, pre-registered like WS1/D1.

## 5 · Candidate interventions (only if Q4-1/Q4-2 show residual signal)

| Option | What | Footprint / verdict |
|---|---|---|
| **A — DQ confidence damping** | mechanical: MEDIUM → lower confidence (a DQ analog of D1) | **Tiny actionable footprint** — HOLDs dominate and HOLD confidence drives no action (advisory-only); only matters at the BUY gate, and MEDIUM BUYs are rare (1 live). Same limit as the blend. |
| **B — tighten `MIN_DATA_QUALITY`** | reject MEDIUM (act only on HIGH) | Suppresses advisory coverage for held commodity/ETF positions Rob wants monitored — likely undesirable; also tiny BUY footprint |
| **C — input improvement (EDGAR)** | give the model primary-source data on the thin-data single stocks (CBRS, NVDA, SND, DOW) → fewer MEDIUM days | **Root-cause path**; but helps only SEC filers (single stocks), not commodities/ETFs (CORN, GLD, AG-ETF) which structurally lack filings |
| **D — monitoring/reporting** | surface DQ prominently; weight MEDIUM lower in *human* review; track DQ mix as a health metric | **Zero code risk, available now**; treats DQ as information, not a lever |
| **E — accept as known** | the model correctly flags thin-data/volatile instruments; no intervention | Honest default if residual ≈ 0 |

## 6 · Constraints & relationships

- **T3:** DQ-weighting is *not* confidence-band ordering — T3-compliant either way. But Q4-R's finding *reinforces* T3's spirit: fixed-threshold rules mislead; volatility-aware analysis is the right axis.
- **Composition:** any DQ lever would sit in the confidence pipeline alongside D1 (staleness) and the WS1 blend (sector/regime) — three scopes; a DQ scope would be "input reliability." Same three-channel logging pattern.
- **EDGAR (3-C):** Option C is the constructive link — EDGAR is the input-improvement path for the single-stock MEDIUM cases.
- **The ±3% HOLD band** is a project-wide metric (used by the guardrail work, `t2_check`, `blend_eval`). Q4-2 (volatility-scaling) would, if adopted, ripple into all of them — a significant, separate decision (DP-Q4-c).

## 7 · Recommendation & DPs

**Recommendation:** run Q4-1 and Q4-2 (analysis only, no code) before anything else; adopt **Option D (monitoring)** now as zero-risk; treat **Option C (EDGAR)** as the constructive input fix already on the roadmap. **Do not build a DQ down-weight (A/B) unless a residual gap survives the volatility control** — on current evidence it would penalize correct holds.

| DP | Question | Default |
|---|---|---|
| **DP-Q4-a** | Does DQ get a mechanical lever at all? | No, pending Q4-1 residual |
| **DP-Q4-b** | Volatility metric for the control | per-ticker median \|+5d move\| (simple, robust) |
| **DP-Q4-c** | Adopt a volatility-scaled Right? band project-wide? | Investigate in Q4-2; do NOT change the metric without a full re-baseline |
| **DP-Q4-d** | Priority vs WS1 G2 / EDGAR | After WS1 G2 reads (~7/20+); EDGAR carries the input-fix |

---

## 9 · RESOLUTION (Q4-1 + Q4-2 run 2026-07-13)

**Both analyses converge: NO DQ lever. The DQ→accuracy gap is volatility composition, not miscalibration.**

**Q4-1 — DQ accuracy within volatility tiers (fixed ±3%):**

| Volatility tier | HIGH | MEDIUM | residual gap |
|---|---|---|---|
| low (<2%) | 90.1% (n91) | 84.2% (n19) | +5.9pt |
| mid (2-4%) | 45.9% (n85) | 48.7% (n39) | −2.8pt |
| high (>4%) | 19.6% (n46) | 23.5% (n51) | −4.0pt |

The raw +15.5pt gap collapses within tiers (−4.0 to +5.9pt) and *reverses* in mid/high vol. **Within-ticker** (volatility held exactly constant): mean HIGH−MEDIUM diff = **+0.5pt** over 9 tickers → **no residual DQ signal.** The dominant effect is volatility itself (low-vol HOLDs 90% right vs high-vol 20%), not DQ.

**Q4-2 — volatility-scaled band:** HOLD DQ gap **+15.5pt (fixed) → +2.8pt (scaled)** — the fixed ±3% band was unfair to volatile (MEDIUM) names. **The 60-69 > 50-59 inversion SURVIVES scaling** (−12.1 → −12.9pt) → **Q1-R diagnosis robust to the metric.**

**DISPOSITION — Q4-R CLOSED: no DQ lever** (DP-Q4-a = No). DQ stays a monitoring / EDGAR-targeting signal (Options D/C). A mechanical DQ down-weight would penalize correct holds on volatile instruments.

**Spinoff — metric-fairness (the larger finding):** volatility dominates the fixed ±3% HOLD metric (90% low-vol vs 20% high-vol) — it substantially measures instrument volatility, not signal skill. The key inversions survive scaling, so **prior findings (Phase-2 baseline, Q1-R) stand**; but a **volatility-scaled accuracy metric is worth adding as a SECONDARY/parallel report**, NOT a replacement (switching would orphan the Phase-2 baseline and every prior finding). **DP-Q4-c disposition: parallel secondary metric, report both, do not re-baseline.** This is the successor thread worth its own scoping if pursued.



- `Q1R_Diagnostic_Memo.md` — the parent (DQ-as-signal spinoff; the same confound-not-signal lesson).
- `Phase3C_EDGAR_Scope_Spec.md` — Option C, the input-improvement path.
- `WS1_TripleBlend_Design_Note.md` — the confidence-pipeline a DQ lever would join; the HOLD-dominance footprint precedent.

---

*Status: DRAFT v1.0 — scope + pre-registered investigation. Provisional answer: investigate the confound; likely no naive DQ lever. Advisory-only · no orders · not financial advice.*
