# Amendment Pack — `Phase3C_E4_Endpoint_PreRegistration_v1.md` v1.2 → v1.3

*Claude Equity Bot · drafted 2026-08-12 · carries **DP-3C-t** into the pre-registration. Same argument that carried DP-3C-l/m/n into v1.1 and DP-3C-q into v1.2: a ruling that governs E4 must live in E4's instrument, not only in the notes. **Apply before the first EDGAR-live cohort is read.** Advisory-only · no orders · not financial advice.*

---

## Why this pack exists

DP-3C-t decides **which cohorts are admissible to E4-1, E4-2 and E4-3**. That is squarely an E4 matter, and the record's own precedent is unambiguous: when an instrument and the notes disagree about a criterion, the disagreement is discovered late and costs a provenance loop (DP-8 / DP-9 / DP-10, 2026-07-29 → 07-31).

**Nothing in this pack changes any threshold, arm, population, n, robustness condition, event rate or time-to-read.** It adds an admissibility rule and two dispositions.

---

## Edit 1 — masthead

**Replace** the version line with:

> *Claude Equity Bot · v1.3 · v1.0 drafted 2026-08-02 and written BEFORE go-live as Kickoff §5 requires · v1.1 AMENDED 2026-08-05 · v1.2 AMENDED 2026-08-11 · **v1.3 AMENDED 2026-08-12, still before the E4 clock starts.** v1.3 enters **DP-3C-t**, which governs which cohorts are ADMISSIBLE to E4 rather than what any endpoint measures. No acceptance threshold, arm, population, robustness condition, n or rate is changed by any revision; §3.1 states that for v1.1, §5's DP-3C-q block for v1.2, and §5's DP-3C-t block for v1.3. Advisory-only · no orders · not financial advice.*

---

## Edit 2 — new §5 block, appended after the DP-3C-q ruling

> **RULED 2026-08-12 — DP-3C-t. READ-BEFORE-COUNT ON THE FIRST EDGAR-LIVE COHORT.**
>
> The first cohort generated under `EQUITY_EDGAR=1` enters E4-1/2/3 **only if that day's review finds no extraction defect.** Otherwise it is tagged **SHAKEDOWN**, excluded from E4-1/2/3 only, and the E4 clock starts at the next clean cohort.
>
> *Precedent:* DP-3C-k, which did exactly this for 2026-08-03 and cost one cohort of roughly twenty.
>
> *Rationale of record:* the `E[…]` tag has never appeared in a live log under the amended DP-3C-i/j format. `edgar_parser_audit.py` covers it **synthetically**, and all four instances of the hardcoded-phase-token defect class in this project were "the parser had never seen the real string" — the fourth of them, `log_tracker_crosscheck.py`, reached a canonical cohort on 2026-08-12.
>
> *Timing is the reason this is ruled now rather than later:* the E4 clock has not started, so the criterion is not being set with data in view. The DP-3C-g argument applied a fourth time.
>
> **DEFECT TIERS — defined here because an undefined rule is a judgement made later with the data visible.** The test is one line: **is the ARTIFACT wrong, or is the READER wrong?**
>
> **(a) COHORT-LEVEL — the cohort is tagged SHAKEDOWN and excluded from E4-1/2/3.** Defects in what the model RECEIVED or EMITTED, or in the record that resulted:
> - a mixed-period rendered line (the N-1 class) on any covered name;
> - a rendered figure disagreeing with that filer's own 8-K by more than **2%**, where an 8-K exists to check against;
> - an `E[…]` tag malformed, or absent where one is due, **in the log itself**;
> - a wrong era stamp or phase token **in the log**;
> - a master row that does not reconcile to its log row.
>
> **(b) NAME-LEVEL — that ticker's rows are marked DEGRADED for E4; the cohort survives.** `fin=degraded` on a covered name, or budget exhaustion affecting specific names. This is **not a defect** — DP-3C-j built that visibility deliberately — but a name that did not receive the statements block did not receive the treatment and must not be counted as though it did.
>
> **(c) READ-BLOCKING — the cohort is NOT excluded; the READ is deferred.** Any *tool* that cannot read correct inputs: `log_tracker_crosscheck`, `outcome_sanity`, `h1_lag_trace`, `build_near_miss_registry`, `monitor_strip`, `h4_dq_threshold`, `xbrl_sweep`. The measurement is intact; our view of it is not.
>
> **THE DEFERRAL IS BINDING AND IS NOT A PASS.** A read-blocked cohort enters E4 **only after the tool is fixed and re-run clean against that cohort's own log and master.** Until then it is held **PENDING VERIFICATION**, named explicitly in the notes entry for its date, and carried in the Upcoming block until cleared. This is safe precisely because the log and the master are **durable** — a harness fixed a week later re-reads the same bytes — which is not true of anything on list (a).
>
> **EXPLICITLY NOT A DEFECT:** an informational sweep FLAG (SPLIT-VOTE, extreme YoY on a small base, THIN, XBRL-LAG); a PRIOR-period NOTE firing correctly; a `[6M YTD]` or `[9M YTD]` label firing correctly — that label **firing** is evidence the N-1 fix works, not evidence against it.
>
> *Worked example, 2026-08-12:* `log_tracker_crosscheck.py` returned zero rows against the first `[PHASE 3-C DRY RUN]` cohort because its `LINE_RE` hardcoded the 3-B token, and reported all 24 correct master rows as EXTRA. The cohort was clean throughout and had already reconciled 24/24 by hand that morning. Under (a) read strictly it would have been excluded; under (c) it is deferred, the tool was fixed and negative-tested the same session, and the cohort stands.
>
> *Direction, stated because it runs toward convenience:* the (c) tier makes it EASIER for a cohort to count than the unscoped rule would. It is adopted only because list (a) is simultaneously unchanged and the deferral is binding.
>
> **Effect on this document's endpoints: NONE.** No endpoint, arm, threshold, robustness condition, n or rate changes. DP-3C-t governs admissibility only.

---

## Edit 3 — §7 Exit-review inputs, appended

> **Two admissibility dispositions may attach to a cohort under DP-3C-t and both are reported at the exit:** **SHAKEDOWN** (excluded from E4-1/2/3, retained in the master, the registry, H4 and KEEP-70 — the DP-3C-k scoping) and **PENDING VERIFICATION** (read-blocked, admissible once its harness is fixed and re-run clean). **The count of each is stated at every E4 read**, alongside the §3.3 primary-versus-fallback counts. A phase that admitted cohorts while carrying unresolved PENDING VERIFICATION items has not read its endpoints; it has estimated them.

---

## Application checklist

- [ ] Masthead → v1.3 (Edit 1)
- [ ] §5 → append the DP-3C-t block (Edit 2)
- [ ] §7 → append the dispositions note (Edit 3)
- [ ] Confirm no threshold, arm, population, n, robustness condition or rate was touched
- [ ] Record the application date in `docs\analyst_notes.md` and clear the Upcoming item

---

*Advisory-only · no orders · not financial advice.*
