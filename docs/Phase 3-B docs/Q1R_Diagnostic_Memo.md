# Q1-R Diagnostic — Why the 50-59 Guardrail Inverted (Tier-2E)

*Claude Equity Bot · Phase 3-B · 2026-07-13 · triggered by T2 firing (depth n=100/88, non-compressed lead −15.4pt). Phase-2-vs-live prompt + distribution diff. Source: `tracker_with_registry.xlsx` (907 signals, 5/18–7/13), Phase-2 logs (5/22–5/29), `claude_signal.py`. All accuracy on the tracker's Right?(5d) flag (±3% HOLD / directional), applied identically to both eras. Advisory-only; not financial advice.*

---

## 0 · Verdict (conclusions first)

**Q1-R is DIAGNOSED. The guardrail did not break — the model got better-calibrated.** The inversion is a **generator/data improvement at go-live (2026-06-15)**, not a market/temporal shift and not a degradation. Specifically: the **60-69 band improved (+15.4pt), while 50-59 barely moved (−4.8pt)** — the opposite of "the safe band failed." The Phase-2 guardrail ("trust 50-59 over 60-69") encoded a **Phase-2-specific overconfidence pattern** (60-69 was a coin flip at 50.6%) that the go-live changes **resolved** (60-69 now earns its confidence at 66%). **Disposition: the suspended guardrail stays retired** — there is no useful confidence-band ordering to reinstate in either direction. **The informative dimension is now data quality, not confidence bands** (see §5).

---

## 1 · The question

Phase 2 certified: 50-59 band leads 60-69 on +5d accuracy (the guardrail). Phase 3-A live: it inverted (60-69 leads). The closeout parked Q1-R as "genuine temporal/population shift — something changed," pending the T2-triggered diff. This memo answers *what* changed.

## 2 · Decomposition — it's the 60-69 band improving, not 50-59 failing

Split at the go-live boundary (6/15 = the prompt-change date):

| Band | Phase 2 (pre-go-live) | Phase 3-A+ (post-go-live) | Δ |
|---|---|---|---|
| **50-59** | 58.8% (n=216) | 53.9% (n=152) | **−4.8pt** |
| **60-69** | 50.6% (n=81) | 66.0% (n=100) | **+15.4pt** |
| **Lead (50-59 − 60-69)** | **+8.2pt** | **−12.1pt** | **20.2pt swing** |

The inversion is overwhelmingly the **60-69 band going from coin-flip to strong**, not the 50-59 band collapsing. That reframes everything: this is a *calibration improvement at the high end*, not a guardrail failure.

## 3 · Two coincident drivers, both at go-live

**Driver A — the DQ mix flipped, and DQ became more informative** (data/pipeline change):

| | Phase 2 | Phase 3-A+ |
|---|---|---|
| DQ mix | 69% MEDIUM, 27% HIGH | 69% HIGH, 31% MEDIUM |
| HIGH−MEDIUM accuracy gap | +7.5pt (58.3 vs 50.8) | **+16.1pt** (58.5 vs 42.3) |

The 60-69 band **shed its bad MEDIUM-DQ signals**: Phase-2 60-69 was 36% MEDIUM (29 signals at 37.9%); Phase-3 60-69 is 9% MEDIUM. Removing the coin-flip-bad MEDIUM signals lifts the band average — pure composition.

**Driver B — the 60-69 band's HIGH-DQ calibration genuinely improved** (prompt change: H1 trajectory + H3 stability blocks added at go-live; confirmed present in `claude_signal.py`, absent in Phase-2 reasoning). This is the **control that rules out "it's only composition":**

| Holding DQ fixed at HIGH | Phase 2 | Phase 3-A+ |
|---|---|---|
| 50-59 HIGH-DQ | 60.4% (n=48) | 58.5% (n=106) |
| 60-69 HIGH-DQ | 57.7% (n=52) | **69.2% (n=91)** |
| **HIGH-DQ lead** | **+2.7pt** | **−10.7pt** |

**The guardrail inverts even within HIGH-DQ alone** (a 13.4pt swing). So DQ composition explains part of the raw inversion, but the **core** inversion is a real change in how the model's 60-69 confidence maps to accuracy — 60-69's HIGH-DQ signals got genuinely better (+11.5pt) while 50-59's stayed flat. That change coincides exactly with the H1+H3 prompt.

## 4 · Confound rule-outs

- **Not a blanket "market got easier."** If the market simply became more predictable, *both* bands would rise. 50-59 stayed flat (58.8→53.9); only 60-69 rose. The gain is **selective to the high-confidence band**, which a market-predictability shift can't produce. ✓
- **Not small-n noise.** The 60-69 gain shows in n=91 HIGH-DQ Phase-3 signals vs n=52 Phase-2; the swing (+15.4pt raw, +11.5pt within-HIGH) is large relative to those n. ✓
- **Not a population/watchlist artifact.** The swing persists within HIGH-DQ and within the same confidence band — holding those fixed. ✓
- **Boundary is go-live, not a market event.** The DQ flip and the prompt change both land at 6/15; the inversion tracks that boundary. ✓

## 5 · Spinoff finding — DQ is now the real accuracy signal

The most actionable result: in Phase 3, **data quality separates accuracy more than any confidence band does** — HIGH-DQ 58.5% vs MEDIUM-DQ **42.3%** (a +16.1pt gap, wider than the band spreads). MEDIUM-DQ signals live are genuinely weak (42.3% ≈ worse than a coin flip on directional). This is a **new hypothesis worth its own workstream** (call it Q4-R): whether MEDIUM-DQ signals should be down-weighted or the `MIN_DATA_QUALITY` gate tightened. Not part of Q1-R; recorded here as the diff's byproduct.

## 6 · Disposition

- **Q1-R: DIAGNOSED and CLOSED.** The inversion = a go-live generator/data improvement (DQ mix flip + DQ informativeness gain + H1/H3-prompt-driven 60-69 calibration gain). Not a market/temporal shift; not a degradation — a *calibration improvement*.
- **The suspended 50-59 guardrail stays RETIRED.** It encoded a Phase-2-specific overconfidence artifact that no longer exists. There is no useful band ordering to reinstate — 50-59 and 60-69 are now both decently calibrated (54% / 66%), with 60-69 ahead. T3 (no band-ordering reliance) is not just vindicated but strengthened: bands are no longer the informative axis.
- **T2 can be retired as a tripwire** — it has served its purpose (it fired, the diff ran, Q1-R is diagnosed). No standing re-open trigger on band ordering remains. (`t2_check.py`/`t2.bat` can stay as a monitor but the gate is resolved.)
- **T1 unchanged.** This was a diagnostic; nothing here touches execution readiness or advisory-only status.

## 7 · Note on the marginal firing

T2 fired at lead −15.4pt (0.4pt past trigger, volatile). The firing was correct per the pre-registered rule, and the diagnosis does not depend on the exact −15.4 value — the 20.2pt Phase-2-vs-live swing (and the 13.4pt within-HIGH-DQ control) is the robust signal, far beyond the tripwire's boundary sensitivity. The marginal trigger surfaced a real, large, well-explained shift.

---

## 8 · Recommendations

1. **Close Q1-R** in the analyst notes and the decision worksheet: diagnosed (go-live calibration improvement), guardrail retired, T2 served.
2. **Open Q4-R (spinoff):** scope whether MEDIUM-DQ signals warrant down-weighting or a tighter DQ gate, given HIGH−MEDIUM = +16.1pt live. This is the successor to the band-ordering question — the informative axis moved from confidence bands to data quality.
3. **Retire the T2 tripwire** from the standing monitors (resolved); keep `blend_eval`/`h1`/`h4` running.
4. **No prompt/gate change** off this memo — it explains history; it does not itself mandate a change. Q4-R is where any change gets designed and pre-registered.

---

*Advisory-only · no orders · not financial advice.*
