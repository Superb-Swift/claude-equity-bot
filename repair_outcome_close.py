#!/usr/bin/env python3
"""
repair_outcome_close.py — source a manual outcome close and repair the master.

WHY THIS EXISTS
---------------
2026-08-26: outcome_sanity.py Check A flagged AG's 2026-06-26 close (19.89)
against that day's own Px@signal (17.13), a +16.1% gap. The value sits in THREE
cells at once (+20d of 2026-05-28, +10d of 2026-06-11, +5d of 2026-06-18) and
all three agreed, so Check B was silent by construction. Cross-horizon majority
— the rule that resolved the GLD/NTR/JPM findings the same day — had nothing to
appeal to, and Px@signal is a MORNING QUOTE, not a close. Substituting it would
have written a fabricated close into the master: the exact failure class the
gate exists to prevent.

The only honest resolution is an external close. This fetches it from the same
Schwab feed the rest of the file is sourced from, and repairs every cell the
date touches in one pass.

SCOPE / DISCIPLINE
------------------
  * DRY RUN BY DEFAULT. Prints what it would change and exits 0. Nothing is
    written without --apply.
  * --apply takes a timestamped backup of the master first, always.
  * HARD-REFUSES tracker_with_registry.xlsx as an input (exit 2), same guard as
    outcome_sanity.py and log_tracker_crosscheck.py.
  * Derives the trading-day index from the master's own cohort dates. No
    holiday table, no second source of truth to drift. Same rule as the gate.
  * Finds the affected cells BY RESOLUTION DATE, never by hardcoded row number.
    Row numbers shift as cohort size changes (24 -> 25 -> 26 across Aug 2026).
  * Cell-scoped XML surgery, NOT an openpyxl round-trip. openpyxl drops every
    cached formula value on save, which would blind every data_only=True reader
    of K/L/M/N across the whole book. Formulas, styles and the other sheets are
    preserved byte-for-byte; only the targeted <v> elements move.
  * PLAUSIBILITY GUARD. The fetched close is checked against the master's own
    neighbouring recorded closes before it is allowed in. A repair that writes
    a second bad number is worse than no repair. --force to override.

  Exit 0 = clean (or dry run). Exit 1 = refused / implausible. Exit 2 = usage.

USAGE
-----
  # what the gate is asking about, dry run:
  python repair_outcome_close.py --ticker AG --date 2026-06-26

  # same, write it:
  python repair_outcome_close.py --ticker AG --date 2026-06-26 --apply

  # broker unreachable, or you have the close from a statement:
  python repair_outcome_close.py --ticker AG --date 2026-06-26 --price 17.22 --apply

Advisory-only - no orders - not financial advice.
"""

import argparse
import datetime
import os
import re
import shutil
import sys
import zipfile

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not available. Activate the venv.", file=sys.stderr)
    sys.exit(2)

REFUSED = "tracker_with_registry.xlsx"

DATE_COL, TICKER_COL, SIGNAL_COL, PXSIG_COL = 1, 2, 4, 7
FIRST_DATA_ROW = 5
# label, price column letter, return column letter, sessions forward
HORIZONS = [("+5d", "H", "K", 5), ("+10d", "I", "L", 10), ("+20d", "J", "M", 20)]
BAND = 0.03          # N column HOLD band, read here, never written
PLAUS_PCT = 12.0     # fetched close vs adjacent recorded closes


# ----------------------------------------------------------------- reading
def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def load_rows(path):
    if os.path.basename(path).lower() == REFUSED.lower():
        print("=" * 78)
        print("REFUSED: %s is the GENERATED REPORT COPY, never an input." % REFUSED)
        print("Run against logs\\claude_equity_bot_tracker.xlsx (THE MASTER).")
        print("=" * 78)
        sys.exit(2)
    wb = openpyxl.load_workbook(path, data_only=True)
    if "Signals" not in wb.sheetnames:
        print("ERROR: no 'Signals' tab in %s" % path, file=sys.stderr)
        sys.exit(2)
    ws = wb["Signals"]
    rows = []
    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        d = ws.cell(r, DATE_COL).value
        if not isinstance(d, datetime.datetime):
            continue
        rows.append({
            "row": r, "date": d.date(),
            "tkr": ws.cell(r, TICKER_COL).value,
            "sig": str(ws.cell(r, SIGNAL_COL).value or "").strip().upper(),
            "g": ws.cell(r, PXSIG_COL).value,
            "H": ws.cell(r, 8).value, "I": ws.cell(r, 9).value, "J": ws.cell(r, 10).value,
        })
    wb.close()
    return rows


# AMENDED 2026-08-26. Cell location used to run off an index derived from
# the master's own cohort dates. That is a list of days somebody ran the bot,
# not a calendar, and this module WRITES: across a missed session it would
# have located a cell two sessions from the one it names. See
# Phase3C_VacationGap_PreRegistration_2026-08-26.md.
try:
    from trading_calendar import shift_sessions as _shift, is_trading_day as _is_sess
except ImportError:                                    # pragma: no cover
    _shift = _is_sess = None



def _resolve(cohort_date, n, idx, dates):
    """The +n-trading-day resolution date for `cohort_date`.

    Uses the NYSE calendar when available, so it is correct whether or not the
    bot ran on any session in between. Falls back to the old cohort-derived
    index only if trading_calendar.py is missing -- in which case it is wrong
    across a gap, exactly as before, and the caller has been warned.
    """
    if _shift is not None:
        return _shift(cohort_date, n)
    i = idx.get(cohort_date)                               # pragma: no cover
    if i is None or i + n >= len(dates):
        return None
    return dates[i + n]


def recorded_close(rows, idx, dates, tkr, on_date):
    """What the master currently believes `tkr` closed at on `on_date`,
    read off whichever cohorts resolve there. Returns the set of values."""
    vals = set()
    for r in rows:
        if r["tkr"] != tkr:
            continue
        for label, pcol, _, n in HORIZONS:
            v = r[pcol]
            if not num(v):
                continue
            if _resolve(r["date"], n, idx, dates) == on_date:
                vals.add(round(float(v), 6))
    return vals


# ----------------------------------------------------------------- fetching
def market_settled(on_date):
    """Is `on_date`'s regular session over? (settled_bool, explanation).

    WHY THIS GATE EXISTS. The daily-candle endpoint returns a candle for the
    CURRENT session while it is still running, and its 'close' field is then
    the last print, not the settled close. schwab_client.get_price_history()
    drops today's candle for exactly this reason; this module cannot, because
    repairing today's resolution row is a legitimate use. So the check moves
    here instead of being silently inherited.

    This is the same defect the module was written to fix: NTR 2026-08-25 and
    JPM 2026-08-26 both carried a +5d cell filled from an intraday quote at
    09:39 while two other horizons held a different number. Writing an
    in-progress print into a column labelled 'close' would reproduce that by
    machine, faster and with more authority.

    Degrades safely: if the zone database is unavailable (a bare Windows
    python with no tzdata), settlement cannot be established and the answer
    is False, which routes the caller to --force.
    """
    today = datetime.date.today()
    if on_date < today:
        return True, "prior session"
    if on_date > today:
        return False, "%s is in the future" % on_date
    try:
        from zoneinfo import ZoneInfo
        now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    except Exception:                                          # noqa: BLE001
        return False, ("today's session - settlement UNVERIFIABLE (no zone "
                       "database available to check the ET clock)")
    if (now_et.hour, now_et.minute) >= (16, 15):
        return True, "today's session, settled at %s ET" % now_et.strftime("%H:%M")
    return False, ("today's session, NOT settled - it is %s ET and the regular "
                   "session ends 16:00" % now_et.strftime("%H:%M"))


def fetch_daily_closes(ticker, quiet=False):
    """{date: close} for every daily candle the Schwab feed returns (~1 year),
    INCLUDING the current session's candle. The caller must gate on
    market_settled() before trusting the newest one. Returns {} on failure.

    Split out of fetch_close() on 2026-09-16 so enter_closes.py and
    fetch_closes.py share one fetch and one dating rule.
    schwab_client.get_price_history() cannot be used for this: it drops
    today's candle by design (the H1 prompt window), which makes an evening
    entry of today's close impossible."""
    try:
        import schwab_client
    except ImportError:
        print("ERROR: schwab_client.py not importable. Run from the repo root.", file=sys.stderr)
        return {}
    try:
        client = schwab_client.get_client()
        resp = client.get_price_history_every_day(ticker)
        candles = resp.json().get("candles", [])
    except Exception as e:                                    # noqa: BLE001
        print("  [schwab] fetch failed for %s: %s" % (ticker, e))
        return {}
    seen = {}
    for c in candles:
        ts, close = c.get("datetime"), c.get("close")
        if ts is None or close is None:
            continue
        # FIXED 2026-09-16: was datetime.fromtimestamp(ts / 1000), i.e. the
        # MACHINE'S local zone. Schwab stamps a daily candle at midnight
        # US/Central, which is 05:00-06:00 UTC of the same date, so UTC dating
        # is correct everywhere; local dating is correct only west of UTC and
        # silently shifts every candle one day back anywhere east of it. Same
        # rule as schwab_client.get_price_history().
        seen[datetime.datetime.fromtimestamp(
            ts / 1000, tz=datetime.timezone.utc).date()] = float(close)
    if not seen and not quiet:
        print("  [schwab] no candles returned for %s" % ticker)
    return seen


def fetch_close(ticker, on_date):
    """Daily close from the Schwab feed. Uses schwab_client.get_client() so the
    auth path is identical to every other broker call in the project."""
    seen = fetch_daily_closes(ticker)
    if not seen:
        return None
    lo, hi = min(seen), max(seen)
    print("  [schwab] %d daily candles for %s, %s -> %s" % (len(seen), ticker, lo, hi))
    if on_date not in seen:
        if not (lo <= on_date <= hi):
            print("  [schwab] %s is OUTSIDE the returned window - the daily-candle "
                  "endpoint holds roughly one year." % on_date)
        else:
            print("  [schwab] %s is inside the window but has no candle - market "
                  "holiday, or a feed gap." % on_date)
        return None
    return seen[on_date]


# ----------------------------------------------------------------- writing
def signals_part(zin):
    """Resolve the Signals tab to its XML part through workbook.xml + rels.

    NOT hardcoded to sheet2.xml. Sheet ORDER and sheet FILENAME are independent
    of each other and of tab position; a tab inserted, deleted or reordered in
    Excel can leave 'Signals' living in any sheetN.xml. Writing prices into the
    wrong sheet on that basis would be a silent, total corruption, so this is
    resolved rather than assumed.
    """
    wbx = zin.read("xl/workbook.xml").decode("utf-8")
    m = re.search(r'<sheet\b[^>]*\bname="Signals"[^>]*>', wbx)
    if not m:
        raise AssertionError("no sheet named 'Signals' in the workbook")
    rid = re.search(r'r:id="([^"]+)"', m.group(0))
    if not rid:
        raise AssertionError("Signals sheet carries no r:id")
    rels = zin.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    rel = re.search(r'<Relationship\b[^>]*\bId="%s"[^>]*>' % re.escape(rid.group(1)), rels)
    if not rel:
        raise AssertionError("no relationship for %s" % rid.group(1))
    tgt = re.search(r'Target="([^"]+)"', rel.group(0)).group(1)
    part = tgt[1:] if tgt.startswith("/") else "xl/" + tgt.lstrip("./")
    if part not in zin.namelist():
        raise AssertionError("resolved part %r absent from the package" % part)
    return part


def cell_span(xml, ref):
    """Exact (start, end) of <c r="REF" ...>...</c>. Cell-scoped: never runs on
    into the next cell, which a naive .*? pattern will happily do."""
    m = re.search(r'<c r="%s"(?=[ />])' % re.escape(ref), xml)
    if not m:
        return None
    start = m.start()
    gt = xml.index(">", start)
    if xml[gt - 1] == "/":
        return start, gt + 1
    end = xml.index("</c>", gt) + 4
    if xml[start:end].count("<c ") != 1:
        raise AssertionError("span for %s ran into another cell" % ref)
    return start, end


def _col_num(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def _split_ref(ref):
    m = re.fullmatch(r"([A-Z]+)(\d+)", ref)
    if not m:
        raise AssertionError("bad cell reference %r" % ref)
    return m.group(1), int(m.group(2))


def insert_cell(xml, ref):
    """Create an EMPTY <c> for `ref` if the sheet has none, and return the xml.

    ADDED 2026-09-16 for enter_closes.py. Rows 2001-2032 of the master carry no
    H/I/J elements at all (the template stopped at row 2000 and the 09-16
    cleanup added only K-N), so a close could not be ENTERED there by surgery,
    only repaired where a cell already existed.

    The new cell copies its style (s=) from the same column in the nearest row
    above that has one, so an entered close looks like a typed one. It is
    placed in column order inside its <row>; a missing <row> is refused rather
    than invented, because row creation changes the sheet's shape.
    """
    if cell_span(xml, ref) is not None:
        return xml
    col, rownum = _split_ref(ref)
    m = re.search(r'<row r="%d"(?=[ >])[^>]*?(/?)>' % rownum, xml)
    if not m:
        raise AssertionError("row %d absent from the sheet XML - refusing to create it"
                             % rownum)
    style = ""
    for back in range(1, 400):
        sp = cell_span(xml, "%s%d" % (col, rownum - back)) if rownum - back > 0 else None
        if sp:
            sm = re.search(r'\ss="(\d+)"', xml[sp[0]:xml.index(">", sp[0])])
            if sm:
                style = ' s="%s"' % sm.group(1)
            break
    new_cell = '<c r="%s"%s/>' % (ref, style)
    if m.group(1) == "/":                                  # <row .../> -> open it
        row_open = m.group(0)[:-2] + ">"
        return xml[:m.start()] + row_open + new_cell + "</row>" + xml[m.end():]
    row_end = xml.index("</row>", m.end())
    body = xml[m.end():row_end]
    want = _col_num(col)
    pos = len(body)
    for cm in re.finditer(r'<c r="([A-Z]+)%d"' % rownum, body):
        if _col_num(cm.group(1)) > want:
            pos = cm.start()
            break
    body = body[:pos] + new_cell + body[pos:]
    return xml[:m.end()] + body + xml[row_end:]


def set_cached(xml, ref, new_text, numeric=True):
    """Replace the cached <v> of a cell, leaving any <f> untouched.

    FIXED 2026-09-16, two defects:
      * the type marker was only cleared when t="str" came IMMEDIATELY after
        r=, but the master writes s= first (<c r="K2032" s="26" t="str">), so a
        numeric return written into a template cell stayed typed as TEXT;
      * a self-closing cell (<c r="I1749" s="16"/>, the shape a cleared close
        leaves) fell through to `frag[:-4] + ...`, which cut into the opening
        tag and produced malformed XML.
    A text result now always carries t="str"."""
    span = cell_span(xml, ref)
    if span is None:
        raise AssertionError("cell %s absent from the sheet XML" % ref)
    s, e = span
    frag = xml[s:e]
    if frag.endswith("/>"):                                # self-closing
        frag = frag[:-2].rstrip() + "></c>"
    gt = frag.index(">")
    head, rest = frag[:gt], frag[gt:]
    head = re.sub(r'\s+t="[^"]*"', "", head)
    if not numeric:
        head += ' t="str"'
    frag = head + rest
    if re.search(r"<v\s*/>", frag):
        frag = re.sub(r"<v\s*/>", "<v>%s</v>" % new_text, frag)
    elif re.search(r"<v>[^<]*</v>", frag):
        frag = re.sub(r"<v>[^<]*</v>", "<v>%s</v>" % new_text, frag)
    else:
        frag = frag[:-4] + "<v>%s</v></c>" % new_text
    return xml[:s] + frag + xml[e:]


def write_edits(tracker, edits, audit, tkr_of, src, target_of):
    """Back up, apply cell-scoped edits to the Signals part, set fullCalcOnLoad,
    and append one ledger line per edited price cell. Shared by this module
    and enter_closes.py so there is ONE writer for the master's outcome cells.

    edits : list of (row_dict, price_col, return_col, price, return_fraction)
    audit : parallel list of dicts (cell, label, old, new, old_ret, new_ret, flip)
    tkr_of / target_of : callables giving the ledger's ticker and resolution
    date for audit entry i.
    Returns (backup_path, ledger_path_or_None)."""
    # REFUSE WHILE THE WORKBOOK IS OPEN (added 2026-09-16). Excel holds the
    # file and leaves an owner file beside it; the final os.replace would fail
    # after the backup was taken, or Excel would later save its stale copy over
    # this edit. Checked before anything is written.
    d, b = os.path.split(os.path.abspath(tracker))
    for owner in ("~$" + b, "~$" + b[2:]):
        if os.path.exists(os.path.join(d, owner)):
            raise AssertionError("the master is open in Excel (%s exists) - close it "
                                 "and re-run; nothing was written" % owner)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = "%s_backup_%s.xlsx" % (os.path.splitext(tracker)[0], stamp)
    shutil.copy2(tracker, backup)

    zin = zipfile.ZipFile(tracker)
    part = signals_part(zin)
    xml = zin.read(part).decode("utf-8")
    n_before = len(re.findall(r"<c ", xml))
    n_inserted = 0
    for r, pcol, rcol, px, ret in edits:
        pref = "%s%d" % (pcol, r["row"])
        if cell_span(xml, pref) is None:
            xml = insert_cell(xml, pref)
            n_inserted += 1
        xml = set_cached(xml, pref, repr(float(px)))
        xml = set_cached(xml, "%s%d" % (rcol, r["row"]), repr(ret))
        if pcol == "H":                                    # N keys off K only
            xml = set_cached(xml, "N%d" % r["row"], band_flag(r["sig"], ret), numeric=False)
    if len(re.findall(r"<c ", xml)) != n_before + n_inserted:
        zin.close()
        raise AssertionError("cell count changed unexpectedly - refusing to write")
    # Well-formedness is checked before anything is replaced.
    import xml.dom.minidom as _md
    _md.parseString(xml.encode("utf-8"))

    wbx = zin.read("xl/workbook.xml").decode("utf-8")
    if "fullCalcOnLoad" not in wbx:
        wbx = re.sub(r"(<calcPr\b[^>]*?)\s*/>", r'\1 fullCalcOnLoad="1"/>', wbx, count=1)

    tmp = tracker + ".tmp"
    zout = zipfile.ZipFile(tmp, "w")
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename == part:
            data = xml.encode("utf-8")
        elif it.filename == "xl/workbook.xml":
            data = wbx.encode("utf-8")
        zout.writestr(it, data, zipfile.ZIP_DEFLATED)
    zout.close()
    zin.close()
    try:
        os.replace(tmp, tracker)
    except OSError as e:
        raise AssertionError("could not replace the master (%s) - is it open? The "
                             "edited copy is at %s; the original is untouched" % (e, tmp))

    ledger = os.path.join(os.path.dirname(os.path.abspath(tracker)), "outcome_close_repairs.log")
    try:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        with open(ledger, "a", encoding="utf-8") as fh:
            for i, a in enumerate(audit):
                fh.write("%s\t%s\t%s\t%s\t%s\told=%s\tnew=%.4f\t"
                         "ret %+.2f%% -> %+.2f%%\t%s\t%s\tbackup=%s\n"
                         % (now, tkr_of(i), target_of(i), a["cell"], a["label"],
                            ("%.4f" % a["old"]) if num(a["old"]) else "blank",
                            float(a["new"]), a["old_ret"], a["new_ret"],
                            a["flip"] or "-", src, os.path.basename(backup)))
    except OSError as e:
        print("  [WARN] audit ledger NOT written (%s). The edit IS applied; "
              "record it by hand." % e)
        ledger = None
    return backup, ledger, part


def band_flag(sig, k):
    if sig == "HOLD":
        return "YES" if abs(k) < BAND else "NO"
    if sig == "BUY":
        return "YES" if k > 0 else "NO"
    if sig == "SELL":
        return "YES" if k < 0 else "NO"
    return ""


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Source a manual outcome close and repair the master.")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True, help="resolution date, YYYY-MM-DD")
    ap.add_argument("--price", type=float, default=None,
                    help="manual override - use the broker feed unless it is unreachable "
                         "or you are entering a close off a statement")
    ap.add_argument("--apply", action="store_true", help="write the change (default is dry run)")
    ap.add_argument("--force", action="store_true", help="apply despite the plausibility guard")
    args = ap.parse_args()

    try:
        target = datetime.date.fromisoformat(args.date)
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 2
    if not os.path.exists(args.tracker):
        print("ERROR: not found: %s" % args.tracker, file=sys.stderr)
        return 2

    tkr = args.ticker.strip().upper()
    print("=" * 78)
    print("OUTCOME-CLOSE REPAIR - %s @ %s   [%s]"
          % (tkr, target, "APPLY" if args.apply else "DRY RUN"))
    print("=" * 78)
    print("  master : %s" % args.tracker)

    rows = load_rows(args.tracker)
    dates = sorted({r["date"] for r in rows})
    idx = {d: i for i, d in enumerate(dates)}          # legacy fallback only
    if _is_sess is not None:
        if not _is_sess(target):
            print("  ERROR: %s is not an NYSE session." % target)
            return 2
        if target not in idx:
            # A session with no cohort row is still a resolution date. This is
            # the pre-registered vacation-gap case (2026-08-28, 2026-08-31):
            # the market traded, outcomes exist, the bot did not run.
            print("  NOTE: %s is an NYSE session with no cohort row in the master."
                  % target)
            print("        Repairing its resolution cells anyway - the outcome is")
            print("        real whether or not the bot ran that morning.")
    elif target not in idx:                            # pragma: no cover
        print("  ERROR: %s is not a cohort date and trading_calendar.py is not "
              "importable, so no session calendar is available." % target)
        return 2

    # ---- locate every cell that resolves on the target date ----------------
    targets = []
    for r in rows:
        if r["tkr"] != tkr:
            continue
        for label, pcol, rcol, n in HORIZONS:
            if _resolve(r["date"], n, idx, dates) != target:
                continue
            targets.append((r, label, pcol, rcol))
    if not targets:
        print("  Nothing to do: no %s cohort resolves on %s." % (tkr, target))
        return 0

    print("-" * 78)
    print("  CELLS RESOLVING ON %s (located by date, not by row number)" % target)
    print("-" * 78)
    for r, label, pcol, rcol in targets:
        print("    %s%-5d  cohort %s  %-5s  currently %s   Px@signal %s"
              % (pcol, r["row"], r["date"], label, r[pcol], r["g"]))

    ref_px = next((r["g"] for r in rows if r["tkr"] == tkr and r["date"] == target), None)
    print("    %s's own Px@signal on %s = %s   (a MORNING QUOTE, not a close)"
          % (tkr, target, ref_px))

    # ---- source the close ---------------------------------------------------
    print("-" * 78)
    if args.price is not None:
        close = float(args.price)
        print("  SOURCE: manual override --price %.4f" % close)
    else:
        settled, why = market_settled(target)
        print("  SETTLEMENT: %s" % why)
        if not settled and not args.force:
            print("-" * 78)
            print("  REFUSED: the daily-candle endpoint reports an IN-PROGRESS candle for")
            print("  an unsettled session, and its 'close' is the last print, not the")
            print("  close. Writing that into a column labelled 'close' is the same")
            print("  defect this module exists to repair (NTR 08-25 / JPM 08-26).")
            print("  Re-run after 16:15 ET, or pass --price with a verified close.")
            print("=" * 78)
            return 1
        if not settled and args.force:
            print("    --force: proceeding on an UNSETTLED session. The value written")
            print("    will be an intraday print. Re-verify after the close.")
        print("  SOURCE: Schwab daily candles")
        close = fetch_close(tkr, target)
        if close is None:
            print("-" * 78)
            print("  Could not source a close. Nothing written.")
            print("  Re-run with --price <close> if you have it from another source.")
            print("=" * 78)
            return 1
        print("  [schwab] %s close on %s = %.4f" % (tkr, target, close))

    # ---- plausibility guard -------------------------------------------------
    if _shift is not None:
        prev_d = _shift(target, -1)
        next_d = _shift(target, 1)
        if next_d > dates[-1]:
            next_d = None
    else:                                              # pragma: no cover
        i_t = idx[target]
        prev_d = dates[i_t - 1] if i_t > 0 else None
        next_d = dates[i_t + 1] if i_t + 1 < len(dates) else None
    print("-" * 78)
    print("  PLAUSIBILITY (fetched close vs the master's own adjacent closes)")
    print("-" * 78)
    bad = []
    for d, tag in ((prev_d, "prev"), (next_d, "next")):
        if d is None:
            continue
        vals = recorded_close(rows, idx, dates, tkr, d)
        if not vals:
            print("    %-4s %s : no recorded close" % (tag, d))
            continue
        v = sorted(vals)[len(vals) // 2]
        gap = (close - v) / v * 100.0
        mark = "OK" if abs(gap) <= PLAUS_PCT else "IMPLAUSIBLE"
        print("    %-4s %s : recorded %.4f  -> %+.1f%%  [%s]" % (tag, d, v, gap, mark))
        if abs(gap) > PLAUS_PCT:
            bad.append((d, v, gap))
    if num(ref_px) and ref_px:
        gap = (close - ref_px) / ref_px * 100.0
        print("    quote %s : Px@sig  %.4f  -> %+.1f%%  [%s]"
              % (target, ref_px, gap, "OK" if abs(gap) <= PLAUS_PCT else "IMPLAUSIBLE"))
        if abs(gap) > PLAUS_PCT:
            bad.append((target, ref_px, gap))
    if bad and not args.force:
        print("-" * 78)
        print("  REFUSED: the sourced close is itself implausible against %d "
              "reference(s)." % len(bad))
        print("  A repair that writes a second bad number is worse than no repair.")
        print("  Verify the price, then re-run with --force if it is genuinely correct.")
        print("=" * 78)
        return 1
    if bad and args.force:
        print("    --force: proceeding over %d implausible reference(s)." % len(bad))

    # ---- effect -------------------------------------------------------------
    print("-" * 78)
    print("  EFFECT ON RETURNS")
    print("-" * 78)
    edits = []
    audit = []          # parallel record for the repair ledger; see the write step
    for r, label, pcol, rcol in targets:
        g = r["g"]
        old_v = r[pcol]
        old_ret = (old_v - g) / g * 100.0 if num(old_v) and num(g) and g else float("nan")
        new_ret = (close - g) / g * 100.0 if num(g) and g else float("nan")
        flip = ""
        if old_ret == old_ret and new_ret == new_ret:
            if (old_ret > 0) != (new_ret > 0):
                flip = "  SIGN FLIP"
            if r["sig"] == "HOLD" and (abs(old_ret) < 3.0) != (abs(new_ret) < 3.0):
                flip += "  BAND CROSSING"
        if num(old_v) and abs(float(old_v) - close) < 1e-9:
            # ADDED 2026-09-16: a cell already holding the close is reported,
            # not rewritten, so the ledger records only real changes.
            print("    %s%-5d %-5s  already %.4f - unchanged" % (pcol, r["row"], label, close))
            continue
        print("    %s%-5d %-5s  %+7.2f%% -> %+7.2f%%%s" % (pcol, r["row"], label, old_ret, new_ret, flip))
        edits.append((r, pcol, rcol, close, new_ret / 100.0))
        audit.append(dict(row=r["row"], cell="%s%d" % (pcol, r["row"]),
                          label=label, old=old_v, new=close,
                          old_ret=old_ret, new_ret=new_ret,
                          flip=flip.strip()))

    if not edits:
        print("-" * 78)
        print("  Nothing to change: every cell already holds %.4f." % close)
        print("=" * 78)
        return 0

    if not args.apply:
        print("-" * 78)
        print("  DRY RUN - nothing written. Re-run with --apply to commit.")
        print("=" * 78)
        return 0

    # ---- write --------------------------------------------------------------
    # The backup, surgery, fullCalcOnLoad and ledger now live in write_edits(),
    # shared with enter_closes.py (2026-09-16).
    #
    # ANALYST NOTE (2026-09-08): on 2026-09-08 `scan.bat` was run twice. The
    #   first run reported five findings; the second reported CLEAN. The master
    #   had been corrected between them, but THE RUN RECORD CONTAINED NO
    #   STATEMENT OF WHAT CHANGED. One append-only ledger line per repair
    #   (logs/outcome_close_repairs.log) closes that. Failure to write the
    #   ledger is reported but never blocks the repair.
    #   2026-09-16: the ledger now sits beside the tracker it describes rather
    #   than at a cwd-relative logs/ path.
    src = ("manual --price" if args.price is not None else "broker feed") \
        + (" FORCED" if args.force else "")
    try:
        backup, ledger, part = write_edits(
            args.tracker, edits, audit, lambda i: tkr, src,
            lambda i: target)
    except AssertionError as e:
        print("  ERROR: %s" % e, file=sys.stderr)
        return 1
    print("-" * 78)
    print("  backup : %s" % backup)
    print("  sheet  : Signals -> %s" % part)
    if ledger:
        print("  audit  : %s  (%d line(s) appended)" % (ledger, len(audit)))

    print("  WROTE  : %s  (%d price cell(s) + cached returns; fullCalcOnLoad set)"
          % (args.tracker, len(edits)))
    print("-" * 78)
    print("  NEXT: python outcome_sanity.py     <- must come back clean")
    print("        Open the master in Excel once so K/L/M/N recalculate and cache.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
