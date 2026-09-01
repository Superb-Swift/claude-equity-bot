# Close Runbook — 2026-08-27, the last session before the gap

*Claude Equity Bot · Phase 3-C · **execute after the 15:00 CDT close** · era `A-S1D1-B1-E1` → `A-S1D2-B1-E1` at step 6. Advisory-only · no orders · not financial advice.*

---

## Why this session is not a normal one

Three things land on the same evening, and the **order between them is binding**:

1. **2026-08-27 is the last bot session before a two-session gap** (2026-08-28 and 2026-08-31, pre-registered in `Phase3C_VacationGap_PreRegistration_2026-08-26.md`).
2. **It is E4 cohort 10 of ~10.** The 2026-08-26 review recorded cohort 9. If E4 completes here, it completes entirely under one definition — which is only true if step 6 runs *after* steps 1–5.
3. **The H1 window ruling is applied tonight** — an era bump from `A-S1D1-B1-E1` to `A-S1D2-B1-E1`.

**The happy accident worth protecting:** applying the ruling after tonight's work puts the D1→D2 boundary *exactly on the vacation gap*. Last D1 cohort 08-27, two sessions of nothing, first D2 cohort 09-01. You will not get a cleaner fence than that, and doing step 6 early throws it away.

**If you are short on time, stop after step 5.** Steps 1–5 are the session. Step 6 is a ruling that can wait until you are back — it has waited since it was diagnosed. What must not happen is step 6 *before* step 4.

---

## Step 0 · Before the close — nothing to do

Signals are run and pasted. **Do not enter outcome prices before 15:00 CDT.**

`OutcomeSanity_Findings_Triage_2026-08-26.md` action item 8 is open precisely because two cells were once filled from 09:39 quotes and had to be repaired. JPM moved 33 cents from that morning quote to the close and NTR 62 cents; **both happened to land right, and the practice that produced them was still wrong.**

---

## Step 1 · Record tonight's outcomes — 75 cells

Resolution date **2026-08-27**. Three cohorts resolve on it:

| column | horizon | cohort | rows | master rows |
|---|---|---|---|---|
| **H** | +5d | 2026-08-20 | 26 | 1567–1592 |
| **I** | +10d | 2026-08-13 | 25 | 1440–1464 |
| **J** | +20d | 2026-07-30 | 24 | 1200–1223 |
| | | | **75** | |

All three hold the **same close per ticker** — that is Check B's whole premise. The +10d cohort is 25 and the +20d is 24 because of GM's missing 2026-08-18 row and the smaller early cohorts; **that is expected, not a shortfall.**

> ⚠ **Enter settled closes only.** If you are entering before 16:15 ET, stop and wait.

---

## Step 2 · `scan.bat 2026-08-27`

```
cd C:\Users\rober\claude-equity-bot
venv\Scripts\activate
scan.bat 2026-08-27
```

**What a good result looks like:**

| block | expect |
|---|---|
| trading calendar | `ALL PASS`, and a `[note]` naming 08-28 and 08-31 as pre-registered absent |
| signal_scan | `[OK] era stamp A-S1D1-B1-E1` · `[OK] era unchanged since 2026-08-26` |
| cross-check | `RESULT: 0 finding(s)` |
| outcome sanity | `RESULT: CLEAN` |
| H1 audit | *"defect is still present and still UNRULED"* — **correct, you have not applied it yet** |
| footer | `SCAN FINDINGS` |

**`SCAN FINDINGS` is the expected outcome, not a problem.** It comes from the one known `[FAIL] D.op == B.blend_op` on NVDA — a descoped WS1 channel, owed a rephrase since 2026-08-19. If that is the *only* finding, you are clean.

**STOP AND DO NOT PROCEED** if you see any of:

- a `[CAL]` finding — a session went missing that the pre-registration does not cover;
- `[A]`, `[B]`, `[C]` or `[D]` findings — an outcome price is implausible. Fix at source, re-run, *then* continue;
- `RESULT: 0 finding(s)` missing from the cross-check.

`[F]` findings are **reporting only** and do not block. Expect roughly 19, of which 13 carry a single mis-keyed digit. **Do not fix any of them tonight** — see step 7.

---

## Step 3 · `value.bat 2026-08-27`

Produces `value_anchor`, `implied_return`, `band_price` for the date. Nothing here writes to a workbook.

Two things to glance at, both carried forward from 2026-08-26:

- **CORN** should print as unjoinable at the valuation layer for a **sixth** session. Still owed: read the ticker from inside the document, or add a series→ticker alias. Not tonight.
- **DOW** should still show `fin=…@2026-06-30+coreg…`. If the `~prov` marker appears, a co-registrant filing has gone provisional — note it and carry on.

---

## Step 4 · `run_daily_review.bat` — and bank E4 cohort 10

```
run_daily_review.bat
```

**This is the step that must complete before step 6.** It regenerates the H1 tracers, the near-miss and actionable registries, and the monitor strip — all under era `A-S1D1-B1-E1`. Once it is done, cohort 10 is recorded under the same definition as cohorts 1–9.

**Expect three numbers to look different tonight, for reasons that are not the market** `[V]`:

1. **The retired calibration-guardrail block reads higher.** Its denominator was counting unresolved rows as misses; fixed 2026-08-26. On the 07-07 slice the three bands go 45.7 / 52.6 / 51.3 → **50.9 / 62.1 / 60.8**. The block is retired and gates nothing; the ordering is unchanged.
2. **The `h1_lag_trace` provenance line is new**, and on the `_raw_` variants now says the `Conf` column comes from the session logs rather than the tracker. It always did; the header was wrong.
3. **The TRAIL BASIS note is longer** and names three differences instead of two.

None of that is a data move. Do not write it up as one.

---

## Step 5 · Confirm the gate is clean, then decide

At this point the session is complete and E4 cohort 10 is banked. **If you stop here, nothing is broken and nothing is owed.**

Proceed to step 6 only if steps 1–4 came out as described.

---

## Step 6 · Apply the H1 window ruling

### 6a · Dry run — verification first

```
python apply_h1_window_ruling.py
```

The script makes **one live Schwab call** and asks a yes/no question: does `get_price_history()` return any date that is not an NYSE session? Under the diagnosis every candle is labelled one calendar day early, and any five consecutive sessions contain a Monday — whose label becomes a **Sunday**.

| verdict | meaning | what to do |
|---|---|---|
| **CONFIRMED** | a returned date is a weekend or holiday, and/or the newest is not before today | proceed to 6b |
| **REFUTED** | every returned date is a real session | **STOP.** The window discrepancy is real but its cause is not what we think. Do nothing further. Leave for vacation. |
| **UNAVAILABLE** | token expired / offline / import failed | fix the feed and re-run. **Do not pass `--force-diagnosis`** |

> ⚠ **`--force-diagnosis` exists for a case that is not tonight.** It does not bypass REFUTED — nothing does — and using it to get past UNAVAILABLE means writing to the file that sets every signal on the strength of a story nobody checked. If you cannot verify tonight, the ruling waits. It has waited this long.

The dry run also prints the full diff across **five edits in three files**. Read the `main.py` and `signal_scan.py` hunks at minimum.

### 6b · Apply

```
python apply_h1_window_ruling.py --apply
```

Writes, after a timestamped `.bak` per file:

| file | edit |
|---|---|
| `schwab_client.py` | date candles in UTC; compare against Eastern `today`; warn if an in-progress candle ever reaches the window again |
| `main.py` | era stamp `A-S1D1-B1-E1` → **`A-S1D2-B1-E1`** |
| `signal_scan.py` | register D2 in `KNOWN_ERAS`; give it D1's `ERA_RANK`; add the same-treatment-rank branch to the era-change alarm |

**Why the `signal_scan.py` edits are not optional.** An unregistered era FAILs by design. Without them your first run back is a red `era stamp … is UNKNOWN`, and with only the first two the alarm falls through to *"treatment RESTORED, the finding belongs to yesterday"* — advice that is actively wrong for a deliberate bump. That file's own note warns that a FAIL whose advice is wrong teaches the reader to skim it.

### 6c · What NOT to do after applying

- **Do not re-run `scan.bat`, `value.bat` or `run_daily_review.bat` for 2026-08-27.** Tonight's exhibits belong to the D1 era and are correct as generated.
- **Do not be alarmed that `trail_basis_audit.py` still reports the defect.** It reads *logs*, and no log has yet been written under the new code. It will report `COMPLETED_ONLY` after the 09-01 run. The script says this itself.
- **Do not re-run the bot tonight** to "test" the change. That would create a second 08-27 cohort under a different era.

### 6d · Sanity check that costs nothing

```
python -c "import main; print(main.PROMPT_VARIANT)"
```

Expect `A-S1D2-B1-E1`. If it prints `A-S1D2-B1`, `EQUITY_EDGAR` is unset in that shell — harmless here, but the flag must be set at run time on 09-01.

---

## Step 7 · Leave. Explicitly do not do these.

| tempting | why not |
|---|---|
| Fix the 19 Check F candidates | Unadjudicated. 13 look like typos, 6 do not, and one of them (**GLD 2026-07-02**) says a repair made on 08-26 went the wrong way. Repairing on a hunch is how the AG defect propagated. |
| Enter 08-28 / 08-31 outcomes early | Those sessions have not happened. |
| `CHECK_F_GATES_EXIT = True` | Turns the gate red daily for a known-open item. |
| Re-cut the E4-2 tier table | 8 of 15 would re-tier. The table is **NOT re-cut**. |
| Rule on G1's basis tonight | Step 6 changes the input that question is about. Let one D2 session land first. |

---

## On return — the short version

Full detail in `Phase3C_VacationGap_PreRegistration_2026-08-26.md` §4.

1. `python trading_calendar.py --selftest` → `ALL PASS` plus the two absent-session notes.
2. Backfill **08-28 and 08-31** — 151 cells, six cohorts. `repair_outcome_close.py --ticker X --date 2026-08-28` now accepts non-cohort sessions.
3. Run the bot for **2026-09-01**, then `scan.bat 2026-09-01`. Expect:
   - `[OK] era stamp A-S1D2-B1-E1 - EDGAR live (3-C), H1 window corrected`
   - `[WARN] era stamp CHANGED since 2026-08-27 … SAME treatment rank … do not pool across the line`
   - the H1 audit line flipping to **`Window spans the sessions its label claims. Nothing owed.`**
4. Expect **09-01's trailing window to look wide**. It spans the gap — five bot sessions covering seven calendar days. THETA damps on it. A name that moved sharply on 08-28 or 08-31 may arrive carrying an anomalous-looking damp. **That is a wider window correctly measured. It is not a defect and it is not a signal.**

### What resolves while you are away

| row | +5d resolves | note |
|---|---|---|
| **NTR 2026-08-21 BUY 72** | 2026-08-28 | first non-NVDA post-era row in the record — **and NTR was exited to Scout on 08-26** |
| **GLD 2026-08-24 BUY 72** | 2026-08-31 | episode opening row |
| **GLD 2026-08-25 BUY 72** | 2026-09-01 | |

The post-era arm goes **0/4 → 0/7 resolved**. Quote both bases, row and episode. **Read nothing at n = 7.**

---

## Standing after tonight

**2026-08-27 is E4 cohort 10**, recorded under era `A-S1D1-B1-E1` in full. **From 2026-09-01 the era is `A-S1D2-B1-E1`** and the H1 trailing window is five completed sessions rather than a window shifted one session forward onto a live intraday print.

**DO NOT POOL ACROSS THE LINE.** H1 trailing moves, damping, and G1 episode state before and after are different measurements — DP-3C-o's precedent, which ruled nothing poolable.

**G1's episode history does not carry across.** The 2-of-4 post-deploy episodes were detected on the old window; on the corrected window WMT's 08-26 reading flips from "no adverse move" to a −7.80% damped one. G1's n most likely restarts. **Decide that after one D2 session, not tonight.**

**E4 is NOT contaminated and must not be voided.** The defect was constant across every row and both arms; E4-2 contrasts ADJACENT against COVERED-QUIET within tier, so a within-cohort comparison is unbiased by a constant level effect. This is **not** a tier-(a) SHAKEDOWN condition. Recorded here explicitly because the tier-(a) language is broad enough that a later reader could void ten cohorts over it.

**Unchanged tonight:** the ±3% band at +5d (**NOT re-baselined**), the frozen E4-2 tier table (**NOT re-cut**, 8 of 15 would re-tier), KEEP-70's unruled basis, H4 demoted, WS1 descoped, DP-3C-f unruled, and DP-V1 — nothing in the valuation layer touches the prompt.

*Advisory-only · no orders · not financial advice.*
