#!/usr/bin/env python3
"""fundamental_probe.py — dump the RAW Schwab `fundamental` block, unflattened.

WHY THIS EXISTS
    schwab_client.get_quote() receives the complete `fundamental` object and
    keeps exactly three fields (peRatio, eps, divYield), discarding the rest.
    So the question "is `eps` trailing and `peRatio` forward?" is answerable
    from your own account without any documentation -- the answer is very
    likely already arriving on every call and being thrown away.

    Schwab's own schema for this block is behind the developer-portal login,
    and the schwab-py author states plainly that the returned JSON structure is
    undocumented and that experimentation is the intended route. This is that
    experiment, run once, recorded.

WHAT IT LOOKS FOR
    * Any field whose NAME disambiguates the period -- epsTTM, peRatioTTM,
      trailing/forward/estimate variants. If such a field exists, the [?] on
      the peRatio semantics closes immediately and empirically.
    * The internal inconsistency in context: CBRS reports eps 0.0 alongside a
      finite peRatio, which cannot both be true. Seeing the whole block shows
      whether some other field carries the real figure.
    * What a fund's block contains, since ETF eps/peRatio are suppressed
      upstream as unreliable and it is worth knowing what was suppressed.

WHAT IT DOES NOT DO
    Places no orders. Modifies nothing. Writes one new JSON file. Uses
    schwab_client.get_client() so it shares your existing auth and token
    rather than handling credentials itself -- if the token has expired this
    will trigger the same browser reauthorisation any other script would.

    Six tickers only, chosen to be diagnostic rather than exhaustive, so the
    API load is a fraction of one daily run.

USAGE
    python fundamental_probe.py
    python fundamental_probe.py --tickers AAPL,GM

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

OUT = "fundamental_probe.json"

# Chosen for what each one should reveal, not for coverage.
DEFAULT_TICKERS = [
    "AAPL",   # clean, growing -> peRatio BELOW price/eps if peRatio is forward
    "GM",     # declining earnings -> peRatio ABOVE price/eps under the same reading
    "CBRS",   # eps 0.0 with peRatio 479.19 -- the contradiction, in full context
    "SPCX",   # eps 0.0 with peRatio -58.60 -- the same, with a negative forward
    "DOW",    # genuinely negative eps, as the control for a real non-zero value
    "SCHD",   # a fund, to see what is being suppressed upstream as unreliable
]

# Substrings that would settle the period question by name alone.
PERIOD_HINTS = ("ttm", "trailing", "forward", "fwd", "estimate", "est",
                "next", "current", "annual", "quarter", "year")


def main():
    ap = argparse.ArgumentParser(
        description="Dump the raw Schwab `fundamental` block for a few tickers.")
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    a = ap.parse_args()
    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]

    try:
        import schwab_client
    except ImportError as e:
        sys.stderr.write(f"REFUSED: cannot import schwab_client ({e}).\n"
                         f"Activate the venv and run from the project root.\n")
        return 2

    try:
        client = schwab_client.get_client()
    except Exception as e:                                      # noqa: BLE001
        sys.stderr.write(f"REFUSED: could not authenticate ({e}).\n")
        return 2

    raw = {}
    for t in tickers:
        try:
            resp = client.get_quote(t)
            raw[t] = resp.json()
        except Exception as e:                                  # noqa: BLE001
            print(f"  {t:>6}  EXCEPTION {type(e).__name__}: {e}")

    if not raw:
        print("Every call failed -- most likely an expired token. Re-authorise "
              "and re-run.")
        return 1

    # ---- 1. the full key inventory, which is the actual deliverable
    print("=" * 96)
    print("RAW `fundamental` BLOCK -- every key Schwab returns, per ticker")
    print("=" * 96)
    all_keys = {}
    for t, payload in raw.items():
        block = (payload.get(t) or {})
        fund = block.get("fundamental") or {}
        print(f"\n{t}   assetMainType={block.get('assetMainType')!r} "
              f"assetSubType={block.get('assetSubType')!r}   "
              f"({len(fund)} fundamental keys)")
        if not fund:
            print("   (no fundamental block returned)")
            continue
        for k in sorted(fund):
            all_keys.setdefault(k, set()).add(t)
            hit = any(h in k.lower() for h in PERIOD_HINTS)
            print(f"   {'*' if hit else ' '} {k:<34} {fund[k]!r}")

    # ---- 2. does any field name settle the period question?
    print("\n" + "=" * 96)
    print("FIELDS WHOSE NAME CARRIES A PERIOD -- these are what close the [?]")
    print("=" * 96)
    flagged = sorted(k for k in all_keys
                     if any(h in k.lower() for h in PERIOD_HINTS))
    if flagged:
        for k in flagged:
            print(f"   {k:<34} present for {sorted(all_keys[k])}")
        print("\n   If one of these is an explicit TTM or forward variant of eps or")
        print("   peRatio, the semantics are settled by Schwab's own naming and the")
        print("   inference drawn on 2026-08-17 can be replaced with a fact.")
    else:
        print("   NONE. No field name disambiguates the period, so the reading stays")
        print("   an inference and the [?] stands. In that case the remaining routes")
        print("   are the developer-portal schema or a dated experiment: record eps")
        print("   and peRatio daily and watch whether peRatio moves on a day when")
        print("   price does not -- an estimate-driven field will, a trailing one")
        print("   cannot.")

    # ---- 3. the contradiction, shown in context
    print("\n" + "=" * 96)
    print("THE CONTRADICTION IN CONTEXT -- price/eps against peRatio")
    print("=" * 96)
    print(f"{'tk':>6} {'lastPrice':>11} {'eps':>11} {'price/eps':>11} "
          f"{'peRatio':>11} {'ratio':>7}")
    for t, payload in raw.items():
        block = payload.get(t) or {}
        q = block.get("quote") or {}
        f = block.get("fundamental") or {}
        px, eps, pe = q.get("lastPrice"), f.get("eps"), f.get("peRatio")
        if not px or eps in (None, 0) or pe in (None, 0):
            print(f"{t:>6} {(px or 0):11,.2f} {str(eps):>11} {'--':>11} "
                  f"{str(pe):>11} {'--':>7}")
            continue
        tr = px / eps
        print(f"{t:>6} {px:11,.2f} {eps:11,.4f} {tr:11,.2f} {pe:11,.2f} {pe/tr:7.3f}")
    print("\n  A ratio below 1 means peRatio is CHEAPER than trailing price/eps, i.e.")
    print("  earnings are expected to rise -- consistent with peRatio being forward.")
    print("  A name reporting eps exactly 0.0 beside a finite peRatio cannot have")
    print("  both be true, which is why implied_return.py treats that zero as a")
    print("  placeholder rather than a measurement.")

    payload = {
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "captured_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": ("RAW unflattened Schwab quote responses. Captured to settle whether "
                 "`eps` is trailing and `peRatio` is forward. schwab_client.get_quote "
                 "keeps only peRatio/eps/divYield and discards the rest."),
        "tickers": tickers,
        "raw": raw,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    print(f"\nwrote {OUT} ({len(raw)} raw responses)")
    print("Nothing else was modified. No orders. Advisory-only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
