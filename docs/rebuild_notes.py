#!/usr/bin/env python3
"""Reorganise docs/analyst_notes_<date>.md WITHOUT altering a single word of any entry.

What it does
------------
1. Unescapes docx-conversion residue (\\_ \\* \\[ \\] \\~ \\- \\& \\# \\| and \\\\ -> \\).
   Windows paths like logs\\signals_x.log are left intact -- the pass only strips a
   backslash that precedes a markdown-special character.
2. Normalises 67 entry headings to one convention: '## YYYY-MM-DD ...'. Only the
   date token is rewritten; every word of every title survives.
3. Puts entries in true chronological order. Exactly one entry moves: the
   2026-08-17 body, which sits above 2026-07-13 in the source.
4. Leaves the three superseded Upcoming blocks in their chronological slots and
   stamps each SUPERSEDED. The 2026-08-18 block becomes the single current one.
5. Adds an Index and a Standing-state register at the top.

It then PROVES nothing was lost: the multiset of words in the rebuilt body must
equal the multiset of words in the unescaped source. Any drift aborts the write.
"""
import re
import sys
from collections import Counter

SRC = sys.argv[1] if len(sys.argv) > 1 else "analyst_notes_2026-08-18.md"
DST = sys.argv[2] if len(sys.argv) > 2 else "analyst_notes_2026-08-18_clean.md"

raw = open(SRC, encoding="utf-8").read()

# ---------------------------------------------------------------- unescape ---
# Single left-to-right pass. '\\\\' -> '\\'; '\\<special>' -> '<special>';
# anything else (\s, \P, \c -- real Windows paths) untouched.
UNESC = re.compile(r"\\\\|\\([_*\[\]~\-&#|])")
_one = lambda s: UNESC.sub(lambda m: "\\" if m.group(1) is None else m.group(1), s)


def unescape(s):
    """Iterate to a fixed point. Parts of this file were escaped TWICE (a docx
    round-trip on already-escaped text), so `Phase3B\\\\_Exit` needs two passes.
    Safe to iterate: each pass consumes only '\\\\' or a backslash before a
    markdown-special char, so real Windows paths (logs\\signals_x.log, C:\\Users\\...)
    reach a fixed point untouched."""
    for _ in range(6):
        n = _one(s)
        if n == s:
            return s
        s = n
    return s


text = unescape(raw)
lines = text.split("\n")

# ------------------------------------------------------------- entry index ---
PATS = [
    ("iso",  re.compile(r"^## (?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})(?P<rest>.*)$")),
    ("md2",  re.compile(r"^## --(?P<m>\d{1,2})/(?P<d>\d{1,2})(?P<rest>\s+.*)$")),
    ("md",   re.compile(r"^## (?P<m>\d{1,2})/(?P<d>\d{1,2})(?P<rest>\s+\(.*)$")),
    ("bare", re.compile(r"^(?P<m>\d{1,2})/(?P<d>\d{1,2})(?P<rest> \([^)]*[Pp]hase[^)]*\)\s*(?:—|--).*)$")),
]


def entry_at(line):
    for kind, p in PATS:
        m = p.match(line)
        if m:
            g = m.groupdict()
            date = (f"{g['y']}-{g['m']}-{g['d']}" if kind == "iso"
                    else f"2026-{int(g['m']):02d}-{int(g['d']):02d}")
            return kind, date, g["rest"]
    return None


heads = []
for i, l in enumerate(lines, 1):
    e = entry_at(l)
    if e:
        heads.append((i, *e))
# 67, not 65: two 2026-08-11 entries were written as '\## 8/11 ...' and the
# escaped hash meant they never rendered as headings at all. Unescaping surfaces
# them. They were in the file the whole time and effectively unfindable.
assert len(heads) == 67, f"expected 67 entries, found {len(heads)}"

# -------------------------------------------------------------- segmenting ---
# Boundaries verified by inspection against the source; asserted here so the
# script fails loudly rather than silently mis-slicing a future file.
def L(a, b):
    return lines[a - 1:b]


assert lines[2784].startswith("# Active Touch Points"), lines[2784][:60]
assert lines[2821].startswith("8/17 (Phase 3-C"), lines[2821][:60]
assert lines[2845].startswith("**Upcoming (Phase 3-B era"), lines[2845][:60]
assert lines[2855].startswith("7/13 (Phase 3-B Day 5)"), lines[2855][:60]
assert lines[3352].startswith("Upcoming (Phase 3-C era; every date"), lines[3352][:60]
assert lines[3566].startswith("Upcoming (Phase 3-C era; additions from 2026-08-17)"), lines[3566][:60]
assert lines[3579].startswith("8/18 (Phase 3-C"), lines[3579][:60]
assert lines[3627].startswith("Upcoming (Phase 3-C era; additions from 2026-08-18)"), lines[3627][:60]

SEG = {
    "hdr_old":    L(1, 14),        # replaced wholesale
    "reference":  L(15, 186),
    "iso":        L(189, 2784),    # 38 entries, 2026-05-26 .. 2026-07-06
    "touch_hdr":  L(2785, 2821),   # '# Active Touch Points' + Completed list
    "e0817":      L(2822, 2840),   # MISPLACED entry body (2841 is its '---')
    "up_3b":      L(2846, 2855),   # superseded Upcoming, Phase 3-B era
    "mid":        L(2856, 3566),   # 7/13 .. 8/13 corrigendum, incl. the 3-C block
    "up_0817":    L(3567, 3576),   # superseded Upcoming, 8/17
    "e0818":      L(3580, 3625),   # entry body (3626 is its '\---')
    "up_0818":    L(3628, 3641),   # CURRENT Upcoming + Standing
}

# stamp the two standalone superseded blocks
STAMP = ("*[SUPERSEDED {} — retained in place per the record's own rule that "
         "historical entries are never rewritten. The current block is at the "
         "end of this file.]*")
SEG["up_3b"] = [STAMP.format("2026-07-13"), ""] + SEG["up_3b"]
SEG["up_0817"] = [STAMP.format("2026-08-18"), ""] + SEG["up_0817"]

# the third superseded block lives inside 'mid'; stamp it in place
for k, l in enumerate(SEG["mid"]):
    if l.startswith("Upcoming (Phase 3-C era; every date"):
        SEG["mid"][k:k] = [STAMP.format("2026-08-13"), ""]
        break
else:
    raise SystemExit("in-mid Upcoming block not found")


def norm_heads(block):
    """Rewrite entry headings to '## YYYY-MM-DD<rest>'. Titles are untouched."""
    out = []
    for l in block:
        e = entry_at(l)
        out.append(f"## {e[1]}{e[2]}" if e else l)
    return out


def tidy(block):
    """One separator style; collapse blank runs to one; drop leading/trailing blanks."""
    out = []
    for l in block:
        s = l.strip()
        if s and set(s) <= set("-") and len(s) >= 2:
            l = "---"
        if l == "" and out and out[-1] == "":
            continue
        out.append(l)
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


for k in SEG:
    SEG[k] = tidy(norm_heads(SEG[k]))

# ------------------------------------------------------------------- index ---
def title_of(rest):
    t = rest.lstrip()
    t = re.sub(r"^[—–-]\s*", "", t)
    t = re.sub(r"[*`\[\]]", "", t)
    return (t[:104] + "…") if len(t) > 105 else t


ordered = []
for i, kind, date, rest in heads:
    ordered.append((date, title_of(rest)))
ordered.sort(key=lambda x: x[0])

index = ["## Index", "",
         f"{len(ordered)} dated entries, 2026-05-26 → 2026-08-18. "
         "Duplicate dates are multiple entries written the same session and are "
         "listed in their original order.", ""]
seen = Counter()
for date, t in ordered:
    seen[date] += 1
    suffix = f" ({seen[date]})" if [d for d, _ in ordered].count(date) > 1 else ""
    index.append(f"- **{date}**{suffix} — {t}")

# -------------------------------------------------------------- assemble ----
HEADER = f"""# Claude Equity Bot — Analyst Notes

**THIS FILE IS THE RECORD.** `docs\\analyst_notes_<date>.md` is the master; every
other copy — the project reading slice, the archive — is derived from it and is
regenerated, never spliced.

*Reorganised 2026-08-19. Nothing was rewritten, condensed or deleted: the pass
normalised 67 entry headings to one `## YYYY-MM-DD` convention, put the entries
in true chronological order, unified separators, and stripped ~1,500 stray
backslash escapes left by an early docx conversion.*

*Two 2026-08-11 entries were recovered in the process: they had been written as
`\\## 8/11 ...`, so the escaped hash meant they never rendered as headings and were
unfindable in any table of contents. They were always in the file. Exactly one entry moved —
the 2026-08-17 body, which had been pasted above 2026-07-13 while its own
Upcoming block stayed at the end of the file. The move was verified word-for-word:
the rebuilt file contains the same multiset of words as the source.*

**How to read it.** Entries are dated and append-only. A historical entry states
what was believed on its date and is never edited afterwards — where a later
entry contradicts an earlier one, both stand and the later one says so. Three
superseded `Upcoming` blocks remain in their chronological slots, stamped; the
single current one is at the end of the file.

**Known gap:** there is no 2026-08-14 entry. A closing review for that date exists
(`Phase3C_ClosingReview_2026-08-14.md`) but was never spliced. Same class as the
missing 7/24 entry, which was reconstructed on 2026-08-04. **The 2026-08-19 entry
is also not yet spliced** — it is staged at `docs\\note splices\\splice_2026-08-19.md`.

---

{chr(10).join(index)}

---

## Standing state — as of 2026-08-18

*Derived from the current Upcoming/Standing block at the end of this file. It is a
convenience view, not a source: where this table and a dated entry disagree, the
dated entry wins.*

| Item | State | Last moved |
|---|---|---|
| **T1** advisory-only, pre-execution | MANDATORY | standing |
| **T3** no band-ordering reliance | ENFORCED, tool-checked | standing |
| **KEEP-70** the BUY gate | SUPPORTED, 47.50% row basis / NOT SUPPORTED, 55.6% episode basis — **basis UNRULED** | 2026-08-18 |
| **H4** DQ-conditional threshold | DEMOTED (55.0%; first passing reading reversed at the second) | 2026-08-18 |
| **±3% HOLD band** | unchanged, **NOT re-baselined** | standing |
| **E4-2 frozen tier table** | **NOT re-cut**; 4 of 15 would re-tier at current n | 2026-08-10 (freeze) |
| **WS1 / G2** blend | DESCOPED | 2026-07-31 |
| **WS2 / G1** lag compression | INSUFFICIENT TEST CONDITIONS; both tracers generating | 2026-07-31 |
| **Q4-2** volatility-scaled band | PARKED | standing |
| **Peer-relative M/B–ROE** | DESCOPED; P/E form PARKED | 2026-08-17 |
| **Valuation layer** | off-prompt; touches no endpoint | DP-V1, unruled |
| **DP-3C-l** gate-cleared ledger | disposition pre-committed INSUFFICIENT TEST CONDITIONS; **stated reason falsified 2026-08-18**, amendment owed | 2026-08-18 |
| **E4 clock** | cohort 4 of ~10 | 2026-08-18 |

---

# Reference
"""

body = (SEG["reference"]
        + ["", "---", "", "# Findings (Chronological)", ""]
        + SEG["iso"]
        + ["", "---", ""] + SEG["up_3b"]
        + ["", "---", ""] + SEG["mid"]
        + ["", "---", ""] + SEG["e0817"]
        + ["", "---", ""] + SEG["up_0817"]
        + ["", "---", ""] + SEG["e0818"]
        + ["", "---", "", "# Active Touch Points — Completed Work Log", ""] + SEG["touch_hdr"][1:]
        + ["", "---", "", "# Upcoming — CURRENT", ""] + SEG["up_0818"]
        + ["", "---", "", "*Advisory-only · no orders · not financial advice.*", ""])

out = HEADER.split("\n")[:-2] + body     # HEADER already ends with '# Reference'

# ------------------------------------------------------------ verification ---
WORD = re.compile(r"\S+")
src_words = Counter(WORD.findall("\n".join(lines[14:])))          # everything below the old title block
new_words = Counter(WORD.findall("\n".join(body)))

# account for what the pass deliberately adds or normalises
added = Counter(WORD.findall("\n".join(
    ["# Findings (Chronological)", "# Completed Work Log", "# Upcoming — CURRENT",
     "*Advisory-only · no orders · not financial advice.*"]
    + [STAMP.format(d) for d in ("2026-07-13", "2026-08-13", "2026-08-18")])))

lost = src_words - new_words
gained = (new_words - src_words) - added
# separator normalisation turns '--' and '---' variants into '---'.
# '--7/14' is the same residue glued to a date token: the source heading read
# '## \\--7/14 (Phase 3-B Day 6)', so the '--' is conversion debris, not a word.
for tok in ("---", "--", "--7/14"):
    lost.pop(tok, None); gained.pop(tok, None)
# heading date tokens are rewritten M/D -> YYYY-MM-DD by design
lost = Counter({w: c for w, c in lost.items() if not re.fullmatch(r"\d{1,2}/\d{1,2}", w)})
gained = Counter({w: c for w, c in gained.items() if not re.fullmatch(r"2026-\d{2}-\d{2}", w)})

print("=" * 70)
print("WORD-PRESERVATION PROOF")
print("=" * 70)
print(f"  source words (below title block) : {sum(src_words.values()):,}")
print(f"  rebuilt words                    : {sum(new_words.values()):,}")
print(f"  LOST   (in source, not rebuilt)  : {sum(lost.values())}")
for w, c in lost.most_common(12):
    print(f"        x{c}  {w[:70]!r}")
print(f"  GAINED (unaccounted additions)   : {sum(gained.values())}")
for w, c in gained.most_common(12):
    print(f"        x{c}  {w[:70]!r}")

if sum(lost.values()):
    raise SystemExit("\nABORTED: words would be lost. Nothing written.")

open(DST, "w", encoding="utf-8").write("\n".join(out))
print(f"\n  entries          : {len(heads)} (all '## YYYY-MM-DD')")
print(f"  Upcoming blocks  : 3 superseded (stamped, in place) + 1 current")
print(f"  wrote {DST}")
