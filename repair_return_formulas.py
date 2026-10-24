#!/usr/bin/env python3
"""
repair_return_formulas.py - restore the canonical K..N outcome formulas on the
MASTER's Signals sheet, by cell-scoped XML surgery.

WHY THIS EXISTS (2026-10-20)
    Rows 5..2031 carry the ruled return definitions: every return is measured
    FROM THE SIGNAL PRICE (column G).

        K  Return +5d    IF(H="","",(H-G)/G)
        L  Return +10d   IF(I="","",(I-G)/G)
        M  Return +20d   IF(J="","",(J-G)/G)
        N  Right? (5d)   IF(H="","",IF(D="HOLD",IF(ABS(K)<0.03,...)))

    From row 2032 (cohort 2026-09-16, last row) to row 3000 the sheet carries a
    CHAINED pattern instead - the shape a fill-RIGHT of the K formula produces:

        L  IF(I="","",(I-H)/H)     the +5d -> +10d leg, not the +10d return
        M  IF(J="","",(J-I)/I)     the +10d -> +20d leg, not the +20d return
        N  IF(K="","",(K-J)/J)     rows 2729..3000 only (template rows not yet used)

    The 09-16 cleanup left rows 2001..2032 canonical; the pattern was written
    after it and has been copied into every new cohort since by Workflow
    step 2's "drag K:N formulas down from the row above". Every data_only=True
    reader of L/M (both registries' +10d columns, h1_lag_trace's r10, the
    Dashboard's Avg Return 10-Day / 20-Day, the report copy) has been reading
    the leg, not the return, for every cohort from 09-16. enter_closes.py
    writes the FROM-SIGNAL value into the cache, so between an enter_closes
    write and the next Excel recalc the two definitions sit side by side.

    K is canonical everywhere, so N's +5d verdict, the band identity, KEEP-70,
    the gate-cleared ledger and H4 (all +5d) are NOT affected. Prices are never
    touched.

WHAT IT DOES
    * finds every K..N cell from row 5 to the sheet's last row whose effective
      formula (shared formulas resolved) is not the canonical one;
    * rewrites it - and every other member of any shared-formula group it
      belongs to - as an explicit canonical formula, so no group is orphaned;
    * sets each rewritten cell's cached value to what the canonical formula
      returns on the cell's own prices (so data_only=True readers are right
      immediately, before any Excel recalc);
    * refuses while Excel holds the master, backs up first, keeps the cell
      count and every non-K..N byte identical, sets fullCalcOnLoad, and writes
      a per-cell CSV plus one line to logs/formula_repairs.log.

USAGE (from the project root, Excel closed)
    python repair_return_formulas.py            # dry run: counts and samples
    python repair_return_formulas.py --apply    # write it

Exit 0 = nothing to do or written. 1 = refused. 2 = usage.
Advisory-only - no orders - not financial advice.
"""

import argparse
import csv
import datetime
import os
import re
import shutil
import sys
import zipfile

import repair_outcome_close as roc

try:
    from openpyxl.formula.translate import Translator
except ImportError:                                           # pragma: no cover
    print("ERROR: openpyxl not available. Activate the venv.", file=sys.stderr)
    sys.exit(2)

COLS = ("K", "L", "M", "N")
CANON = {
    "K": 'IF(H{r}="","",(H{r}-G{r})/G{r})',
    "L": 'IF(I{r}="","",(I{r}-G{r})/G{r})',
    "M": 'IF(J{r}="","",(J{r}-G{r})/G{r})',
    "N": ('IF(H{r}="","",IF(D{r}="HOLD",IF(ABS(K{r})<0.03,"YES","NO"),'
          'IF(D{r}="BUY",IF(K{r}>0,"YES","NO"),IF(D{r}="SELL",IF(K{r}<0,"YES","NO"),""))))'),
}
PRICE_OF = {"K": "H", "L": "I", "M": "J"}
CELL_RE = re.compile(r'<c r="([K-N])(\d+)"(?=[\s>/])[^>]*?(?:/>|>.*?</c>)', re.S)
F_RE = re.compile(r"<f\b([^>]*?)(?:/>|>(.*?)</f>)", re.S)


def xml_unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&amp;", "&"))


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def attr(a, name):
    m = re.search(r'\b%s="([^"]*)"' % name, a)
    return m.group(1) if m else None


def scan(xml, first_row):
    """{ref: dict(col,row,span,f_attrs,f_text,si)} for K..N cells with a formula,
    plus the shared-group map {si: [refs]} and masters {si: (ref, text)}."""
    cells, groups, masters = {}, {}, {}
    for m in CELL_RE.finditer(xml):
        col, row = m.group(1), int(m.group(2))
        if row < first_row:
            continue
        frag = m.group(0)
        fm = F_RE.search(frag)
        if not fm:
            continue
        a, text = fm.group(1), fm.group(2)
        si = attr(a, "si") if attr(a, "t") == "shared" else None
        ref = "%s%d" % (col, row)
        cells[ref] = dict(col=col, row=row, f_attrs=a,
                          f_text=xml_unescape(text) if text else None, si=si)
        if si is not None:
            groups.setdefault(si, []).append(ref)
            if text:
                masters[si] = (ref, xml_unescape(text))
    return cells, groups, masters


def effective(ref, c, masters):
    if c["f_text"]:
        return c["f_text"]
    if c["si"] in masters:
        mref, mtext = masters[c["si"]]
        return Translator("=" + mtext, origin=mref).translate_formula(ref)[1:]
    return None


def canonical_value(col, row, vals):
    """What the canonical formula returns, from the row's own cell values."""
    g, sig = vals.get("G"), str(vals.get("D") or "").strip().upper()
    if col in PRICE_OF:
        px = vals.get(PRICE_OF[col])
        if not roc.num(px) or not roc.num(g) or not g:
            return ("", False)
        return (repr((float(px) - g) / g), True)
    h = vals.get("H")
    if not roc.num(h) or not roc.num(g) or not g:
        return ("", False)
    return (roc.band_flag(sig, (float(h) - g) / g), False)


def row_values(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["Signals"]
    out = {}
    for r, row in enumerate(ws.iter_rows(min_row=1, max_col=10, values_only=True), start=1):
        out[r] = dict(zip("ABCDEFGHIJ", row))
    wb.close()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Restore canonical K..N return formulas on the master.")
    ap.add_argument("--tracker", default=os.path.join("logs", "claude_equity_bot_tracker.xlsx"))
    ap.add_argument("--first-row", type=int, default=roc.FIRST_DATA_ROW)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    if os.path.basename(args.tracker).lower() == roc.REFUSED.lower():
        print("REFUSED: %s is the generated report copy. Repair the MASTER; the "
              "copy is rebuilt from it by run_daily_review.bat." % roc.REFUSED)
        return 2
    if not os.path.exists(args.tracker):
        print("ERROR: not found: %s" % args.tracker, file=sys.stderr)
        return 2

    print("=" * 78)
    print("RETURN-FORMULA REPAIR - Signals K..N   [%s]" % ("APPLY" if args.apply else "DRY RUN"))
    print("=" * 78)
    print("  master : %s" % args.tracker)

    zin = zipfile.ZipFile(args.tracker)
    part = roc.signals_part(zin)
    xml = zin.read(part).decode("utf-8")
    cells, groups, masters = scan(xml, args.first_row)

    bad = {}
    for ref, c in cells.items():
        eff = effective(ref, c, masters)
        if eff != CANON[c["col"]].format(r=c["row"]):
            bad[ref] = eff
    if not bad:
        print("  All %d K..N formula cells are canonical. Nothing to do." % len(cells))
        zin.close()
        return 0

    # Expand to whole shared groups, so no child is left pointing at a rewritten master.
    rewrite = set(bad)
    for ref in list(bad):
        si = cells[ref]["si"]
        if si is not None:
            rewrite.update(groups.get(si, []))
    by_col = {k: sorted(int(r[1:]) for r in bad if r[0] == k) for k in COLS}
    print("  K..N formula cells scanned : %d (rows %d..%d)"
          % (len(cells), args.first_row, max(c["row"] for c in cells.values())))
    print("  non-canonical              : %d" % len(bad))
    for k in COLS:
        rs = by_col[k]
        if rs:
            ex = "%s%d" % (k, rs[0])
            print("    %s  %4d cell(s)  rows %d..%d   e.g. %s = %s" % (k, len(rs), rs[0], rs[-1], ex, bad[ex]))
            print("        canonical:  %s" % CANON[k].format(r=rs[0]))
    print("  rewritten incl. shared-group members : %d" % len(rewrite))

    vals = row_values(args.tracker)
    changes = []
    n_before = len(re.findall(r"<c ", xml))
    for ref in sorted(rewrite, key=lambda x: (int(x[1:]), x[0])):
        c = cells[ref]
        span = roc.cell_span(xml, ref)
        s, e = span
        frag = xml[s:e]
        old_v = re.search(r"<v>([^<]*)</v>", frag)
        old_v = old_v.group(1) if old_v else ""
        new_f = "<f>%s</f>" % xml_escape(CANON[c["col"]].format(r=c["row"]))
        frag2 = F_RE.sub(lambda _m: new_f, frag, count=1)
        xml = xml[:s] + frag2 + xml[e:]
        text, numeric = canonical_value(c["col"], c["row"], vals.get(c["row"], {}))
        xml = roc.set_cached(xml, ref, text, numeric=numeric)
        changes.append((ref, bad.get(ref) or effective(ref, c, masters), old_v, text))

    # ---- verification before anything is written ---------------------------
    if len(re.findall(r"<c ", xml)) != n_before:
        zin.close()
        print("  REFUSED: cell count changed - nothing written.")
        return 1
    cells2, groups2, masters2 = scan(xml, args.first_row)
    left = [r for r, c in cells2.items() if effective(r, c, masters2) != CANON[c["col"]].format(r=c["row"])]
    orphans = [si for si in groups2 if si not in masters2]
    if left or orphans or len(cells2) != len(cells):
        zin.close()
        print("  REFUSED: post-check failed (non-canonical %d, orphaned groups %d, "
              "formula cells %d -> %d) - nothing written." % (len(left), len(orphans), len(cells), len(cells2)))
        return 1
    import xml.dom.minidom as _md
    _md.parseString(xml.encode("utf-8"))
    print("  post-check : every K..N cell canonical; 0 orphaned shared groups; "
          "%d formula cells before and after; XML well-formed" % len(cells2))

    moved = [(r, o, n) for r, _, o, n in changes if r[0] in "LM" and o not in ("", n)]
    print("  cached L/M values that change: %d" % len(moved))
    for r, o, n in moved[:6]:
        print("    %-6s %12s -> %s" % (r, o[:12], n[:12]))

    if not args.apply:
        zin.close()
        print("-" * 78)
        print("  DRY RUN - nothing written. Close Excel, then re-run with --apply.")
        print("=" * 78)
        return 0

    d, b = os.path.split(os.path.abspath(args.tracker))
    for owner in ("~$" + b, "~$" + b[2:]):
        if os.path.exists(os.path.join(d, owner)):
            zin.close()
            print("  REFUSED: the master is open in Excel (%s exists). Nothing written." % owner)
            return 1
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = "%s_backup_%s.xlsx" % (os.path.splitext(args.tracker)[0], stamp)
    shutil.copy2(args.tracker, backup)

    wbx = zin.read("xl/workbook.xml").decode("utf-8")
    if "fullCalcOnLoad" not in wbx:
        wbx = re.sub(r"(<calcPr\b[^>]*?)\s*/>", r'\1 fullCalcOnLoad="1"/>', wbx, count=1)
    tmp = args.tracker + ".tmp"
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
        os.replace(tmp, args.tracker)
    except OSError as e:
        print("  REFUSED: could not replace the master (%s). Edited copy at %s; original untouched." % (e, tmp))
        return 1

    detail = os.path.join(d, "formula_repair_%s.csv" % stamp)
    with open(detail, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "old_formula", "new_formula", "old_cached", "new_cached"])
        for ref, old_f, old_v, new_v in changes:
            w.writerow([ref, "=" + (old_f or ""), "=" + CANON[ref[0]].format(r=int(ref[1:])), old_v, new_v])
    ledger = os.path.join(d, "formula_repairs.log")
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write("%s\trewrote %d K..N cells (%s)\tcached L/M changed %d\tdetail=%s\tbackup=%s\n"
                 % (datetime.datetime.now().isoformat(timespec="seconds"), len(changes),
                    ", ".join("%s %d" % (k, len(by_col[k])) for k in COLS if by_col[k]),
                    len(moved), os.path.basename(detail), os.path.basename(backup)))
    print("-" * 78)
    print("  backup : %s" % backup)
    print("  WROTE  : %d cell(s) in %s (%s); fullCalcOnLoad set" % (len(changes), args.tracker, part))
    print("  detail : %s" % detail)
    print("  NEXT   : python outcome_sanity.py, then run_daily_review.bat")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
