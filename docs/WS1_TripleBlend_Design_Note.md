# WS1 — Triple-Blend Architecture: Design Note

*Claude Equity Bot · Phase 3-B WS1 · DRAFT v1.0 · drafted 2026-07-10 · companion to `Phase3B_Kickoff_Prompt.md` §WS1. Fixes the four deliverables the kickoff requires — (a) three blend components, (b) combination rule + who sets weights, (c) per-blend tracker logging, (d) evaluation on the +5d/+10d/+20d framework — under constraint **T3** (no reliance on confidence-band ordering; the Q1 guardrail is suspended). This is the G2 instrument: for review now, for signature once the blend produces signals. Advisory-only · no orders · not financial advice.*

---

## 0 · Heritage and the reconciliation problem

The "triple blend" (analyst_notes ~935; Phase 2 outline §5a) was a synthesis of three **sources**: our calibrated daily bot + Grok Portfolio's **portfolio-level architecture** (sector-ETF backbone, cross-asset via bonds, explicit sizing) + Claude Portfolio's **per-position depth**. The tension this note resolves: that heritage is *portfolio construction*, but our bot emits **per-ticker signals** scored on **per-signal +5d/+10d/+20d accuracy**. A portfolio allocator and a signal-accuracy harness are different objects.

**Reconciliation principle.** Keep what the evaluation framework can actually measure. Map the heritage's *useful elements* onto three **per-ticker signal components** that (i) fit the existing signal→confidence→resolution pipeline, (ii) are scorable on +5d/+10d/+20d, and (iii) are T3-compliant. Two heritage elements fall out and are accounted for explicitly: **sizing** is an execution concern (Phase 4 — advisory-only cannot size) and **per-position thesis depth** is H3 territory (DESCOPED at the 3-A closeout). Neither is silently dropped; both are DPs below if you want them back.

---

## 1 · (a) The three blend components

Each is a per-ticker score on a common signed scale **[−1, +1]**, direction-carrying where meaningful.

| # | Component | Definition | Native → normalized | Data source | Build status |
|---|---|---|---|---|---|
| **C1** | **Base signal** `S_base` | The calibrated LLM signal — the anchor | `dir × conf/100`, dir = +1 BUY / 0 HOLD / −1 SELL → **[−1,+1]** | `claude_signal.py` (already emitted every session) | ✅ exists |
| **C2** | **Sector backbone** `S_sector` | Trailing trend of the ticker's sector ETF — "is the ticker's sector in favor?" (Grok's sector-ETF backbone, per-ticker) | sector-ETF trailing N-day return, clipped/`tanh` → **[−1,+1]** | NEW: ticker→sector-ETF map + `schwab_client.get_price_history` on the ETF | 🔨 build |
| **C3** | **Cross-asset regime** `S_regime` | Market-wide risk-on/off, one value/day for all tickers (Grok's cross-asset element) | SPY trailing return vs a defensive proxy (GLD, ±TLT), clipped → **[−1,+1]** | SPY + GLD already on the watchlist; TLT optional (new fetch) | 🔨 build |

**Trend-scope separation (why there's no double-counting with D1).** Three components, three distinct trend scopes: **D1** damps on the *ticker's own* trailing return (idiosyncratic staleness); **C2** reads the *sector's* trend (systematic-sector); **C3** reads the *market's* trend (systematic-broad). Disjoint scopes → composable, no signal is counted twice.

---

## 2 · (b) The combination rule

**Direction integrity first.** The base signal owns DIRECTION — the blend never flips BUY↔SELL↔HOLD. The overlays only **modulate conviction**, bounded:

```
agree(dir, S) = +1 if sign(S) == dir, −1 if opposed, 0 if dir==HOLD or S≈0
adj           = w_sector · agree(dir_base, S_sector) · |S_sector|
              + w_regime · agree(dir_base, S_regime) · |S_regime|
conf_blend    = clip( conf_base · (1 + adj), FLOOR, 100 )
```

- Overlays **confirm** (nudge conviction up) or **discount** (nudge down) the base, in proportion to overlay magnitude and agreement. Bounded and direction-preserving.
- **Proposed defaults (tunable — DP-W2):** `w_sector = w_regime = 0.15` (max ±30% conviction swing when both overlays are extreme and aligned), `FLOOR = 35` (clear of the 0-confidence parse-error code, consistent with D1).
- **HOLD handling (DP-W3):** default — overlays leave HOLD confidence unchanged (a HOLD has no direction to confirm). Alternative: a mild regime-only nudge.

**Who sets the weights, and why fixed.** **You set them, pre-registered, and they stay fixed for the acceptance window** — changed only by a dated worksheet entry, never tuned mid-window. This is deliberate: the Q1 guardrail *certified* on Phase 2 data and *inverted* out-of-sample. A blend with weights fitted to 24 tickers would repeat that overfit exactly. Fixed conservative weights + shadow evaluation (below) is the anti-overfit posture the project earned.

**T3 compliance.** The rule uses confidence as a continuous **magnitude** and references direction-agreement × overlay-magnitude. It never mentions confidence **bands** or assumes any band is more accurate — so it carries no dependence on the suspended Q1 ordering. (A rule like "trust 50-59 over 60-69" would violate T3; this does not.)

---

## 3 · Pipeline integration (advisory-parallel, not replace)

**Order of operations:**

```
claude_signal → conf_raw ──[BLEND overlays]──▶ conf_blend ──[D1 damping]──▶ conf_op ──▶ risk_engine ──▶ log
                (model)                        (C2+C3)                       (ticker staleness)
```

A **third confidence channel** joins the two-channel WS2 harness: `conf_raw` (model) → `conf_blend` (after C2/C3) → `conf_op` (after D1). All three logged every line.

**Shadow, not primary.** The blend runs **in parallel** during the acceptance window — both the base and the blended signal are logged and resolved, but the **base remains the official advisory output**. The blend is a candidate measured against the base on +5d/+10d/+20d *before* it drives anything. Only on a G2 pass does the blend become primary. This mirrors WS2's measure-first discipline and the whole project ethos: no methodology is adopted on faith.

---

## 4 · (c) Per-blend tracker logging

| Where | What |
|---|---|
| **Log line tag** | `B[sec=<S_sector>; reg=<S_regime>; w=<w_sec>/<w_reg>; base=<conf_raw>; blend=<conf_blend>]` — appended after the existing `H1[…] \| S1[…] \| D[…]` tags (parsers already tolerate trailing tags) |
| **Signal JSON** | add `confidence_blend`, `sector_score`, `regime_score` alongside `confidence_raw` / `confidence` |
| **Tracker** | a parallel **`Blend Conf %`** column on the Signals tab (or a dedicated **Blend** tab keyed on date+ticker), so blend-vs-base joins cleanly on the same +5d/+10d/+20d resolutions — no second resolution pass needed |
| **Era stamp** | generator label extends, e.g. `A-S1D1` → **`A-S1D1-B1`**, single live arm (not an A/B); pre/post-blend cohorts stay stratifiable |

The base channel (`conf_raw`) stays fully auditable — "what would the base have said" is always recoverable, exactly as with D1.

---

## 5 · (d) Evaluation on the +5d/+10d/+20d framework

Same framework, computed for **both** the base and the blended signal per cohort (the tracker join in §4 makes this a single resolution pass):

- **Accuracy** — the `Right?` flag (±3% HOLD band; directional BUY/SELL) at +5d/+10d/+20d, base vs blend.
- **Magnitude** — average favorable move on directional signals, base vs blend.
- **The bar is NO-DEGRADE, cross-validated.** Given the Q1 lesson, the blend must be **no worse than the base** on +5d accuracy AND magnitude across the acceptance window, with **no single cohort carrying the result** (cross-validation / leave-one-cohort-out). "Better" is the goal; "not worse, robustly" is the pass line. A blend that only wins on one lucky cohort fails.
- **T3** — the comparison is base-vs-blend accuracy, never band-ordering.

---

## 6 · Pre-registered acceptance (Gate G2)

From the exit-criteria instrument (`Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1`, G2 + DP-1):

> **PASS** — design note signed (this document, T3-compliant ✓) AND the blend deployed advisory-parallel with **≥ N = 5** blended cohorts +5d-resolved under clean cross-validation, blend **no-worse** than base on +5d accuracy + magnitude → blend adopted as primary.
> **DESCOPE / REJECT-AND-RETAIN-BASE** — if the blend degrades or only wins on cherry-picked cohorts → record, keep the base signal, shelve the blend with re-open triggers.
> Disposition: **VERDICT** (adopt / reject) or **DESCOPE**. No band-ordering reliance at any step.

---

## 7 · Open decision points (defaults proposed; rulings are yours)

| DP | Question | Proposed default |
|---|---|---|
| **DP-W1** | Component set — confirm {base, sector-backbone, cross-asset-regime}? | Confirm as above (most faithful to heritage that the +5d framework can score) |
| **DP-W2** | Fixed weights `w_sector`, `w_regime` | 0.15 each (±30% max swing); **you set, pre-registered, unfitted** |
| **DP-W3** | Do overlays touch HOLD confidence? | No — HOLD has no direction to confirm |
| **DP-W4** | Blend↔D1 composition | Series (blend → D1), both bounded + logged (§3) |
| **DP-W5** | "Sizing" heritage element | Defer to Phase 4 (advisory-only cannot size); revisit at execution |
| **DP-W6** | Sector-ETF taxonomy + ticker→sector map | SPDR XL* set (XLK/XLF/XLE/XLU/XLP/XLV/XLI/XLY/XLB/XLC/XLRE); map the 24-ticker watchlist explicitly |
| **DP-W7** | Cross-asset proxy | SPY vs GLD only (both tracked) for v1; add TLT if you want a bond leg |
| **DP-W8** | Claude-depth / thesis-stability component | Excluded (that's H3, descoped) — reopen only via a worksheet entry |

---

## 8 · Cross-references

- `Phase3B_Kickoff_Prompt.md` §WS1 — the mandate (four deliverables + T3).
- `WS2_Deploy_Notes.md` — the two-channel logging pattern this extends to three; the anti-overfit / measure-first precedent.
- `Phase3A_Closeout_Memo.md` — Q1-R park (why fixed weights + no-degrade bar), H3 descope (why C-depth is out), T3 definition.
- `Phase3B_Exit_3C_EDGAR_Entry_Criteria_v1` — G2 (this note is its design-sign-off half) + DP-1 (N=5).

---

*Status: DRAFT v1.0 — for review; for signature once weights (DP-W2) and the component set (DP-W1) are ruled and the blend produces its first cohorts. Advisory-only · no orders · not financial advice.*
