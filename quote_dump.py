#!/usr/bin/env python3
"""quote_dump.py — snapshot the Schwab quote payload to a JSON file.

WHY THIS EXISTS
    schwab_client.get_quote() returns TTM `eps`, `peRatio` and `divYield`, and
    claude_signal.py L157-163 puts all three into the prompt. None of them is
    ever written to a machine-readable field, so the only place they survive is
    inside the model's prose reasoning. Reading a number out of the model's
    prose would be the "tool reports a value it did not compute" defect class
    the record carries twelve-plus instances of. This dumps the source instead.

WHAT IT NEEDS THEM FOR
    ROE = eps(TTM) / book value per share      -> the value-driver inversion
    ROE = (M/B) / (P/E)                        -> the same ROE, independent route
    divYield                                   -> the dividend-form inversion,
                                                  r_s = D0(1+g)/P0 + g, and the
                                                  Ch.12 self-supporting-g ceiling

WHAT IT DOES NOT DO
    Touches no existing file. Reads signal_state.json to learn the watchlist so
    there is no hardcoded ticker list to drift. Writes exactly one new file,
    quote_dump.json. Places no orders. Changes no signal, gate or endpoint.

    It DOES make live Schwab API calls -- one quote per ticker, the same volume
    the daily run already makes. If the OAuth token has expired the calls will
    fail and the script says so plainly rather than writing an empty file and
    looking like it worked.

USAGE
    python quote_dump.py

Advisory-only - no orders - not financial advice.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

STATE = "signal_state.json"
OUT = "quote_dump.json"

# The three fields this exists to capture. Reported per ticker so a run that
# succeeded but returned nothing useful is visibly distinct from one that
# worked -- the F-1 lesson: a missing value and a wrong value are different
# states and must not share a presentation.
WANTED = ("eps", "peRatio", "divYield")

# Politeness delay between calls. The daily run makes the same number of
# requests, so this adds no load the API has not already seen.
DELAY_S = 0.15


def watchlist():
    """Derive the tickers from signal_state.json rather than hardcoding them.

    The record carries a hardcoded-expected-count defect in signal_scan.py and
    a hardcoded-phase-token class with three instances; a literal ticker list
    would be the same mistake in a new file. Verified 2026-08-17: this file's
    keys match the 2026-08-17 cohort exactly, 26 of 26, no drift either way.
    """
    if not os.path.exists(STATE):
        sys.stderr.write(
            f"REFUSED: {STATE} not found. Run from the project root so the\n"
            f"watchlist can be derived rather than assumed.\n")
        sys.exit(2)
    with open(STATE, encoding="utf-8") as fh:
        return sorted(json.load(fh))


def session_check():
    """Refuse-by-default on a non-session day, unless the operator insists.

    ANALYST NOTE (2026-09-08): a dump was captured on 2026-09-07 at 09:41 and
    preserved as quote_dump_20260907_094139.json. 2026-09-07 was LABOR DAY, and
    the same day's scan.bat asserted -- correctly, in this same toolchain --
    "[PASS] Labor Day 2026-09-07 is NOT a session".

    The guard in value.bat asks "does a dump exist for today's DATE"; it never
    asks whether that date is a trading session. On a holiday the API returns
    the PREVIOUS session's marks, which are then written under today's stamp
    and used as the drift reference in implied_return section 1. A stale mark
    presented as a current one is precisely the class of defect the
    price-provenance note in value_anchor exists to bound, arriving through a
    door nothing was watching.

    The project HAS a rigorous trading_calendar module; the quote path simply
    never consulted it. This does not block the operator -- one flag overrides
    it -- it stops a holiday capture happening SILENTLY.
    """
    try:
        import trading_calendar as tc
    except Exception as e:
        print(f"[calendar] unavailable ({e}) -- session not verified")
        return True
    today = datetime.now().date()
    for fn in ("is_session", "is_trading_day", "is_market_open", "is_trading_session"):
        f = getattr(tc, fn, None)
        if not callable(f):
            continue
        try:
            ok = bool(f(today))
        except Exception:
            continue
        if ok:
            return True
        print(f"REFUSED: {today} is NOT a trading session (trading_calendar.{fn}).")
        print("  Quotes captured on a non-session carry the PREVIOUS session's")
        print("  marks and would be stamped as today's -- which is what happened")
        print("  on Labor Day 2026-09-07 (quote_dump_20260907_094139.json).")
        print("  Re-run with --allow-non-session if that is intended.")
        return False
    print("[calendar] no session predicate found -- session not verified")
    return True


def main():
    if "--allow-non-session" in sys.argv:
        print("[calendar] non-session capture explicitly allowed by flag")
    elif not session_check():
        return 2

    if os.path.exists(OUT):
        # Do not clobber silently. An older snapshot may be the one that was
        # analysed; overwriting it without a word is how provenance is lost.
        stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(os.path.getmtime(OUT)))
        backup = f"quote_dump_{stamp}.json"
        os.rename(OUT, backup)
        print(f"[existing {OUT} preserved as {backup}]")

    try:
        import schwab_client
    except ImportError as e:
        sys.stderr.write(f"REFUSED: cannot import schwab_client ({e}).\n"
                         f"Activate the venv and run from the project root.\n")
        return 2

    tickers = watchlist()
    print(f"watchlist derived from {STATE}: {len(tickers)} tickers")
    print("requesting quotes ...")

    quotes, failed = {}, []
    for i, t in enumerate(tickers, 1):
        try:
            q = schwab_client.get_quote(t)
        except Exception as e:                       # noqa: BLE001
            q = {}
            print(f"  {t:>6}  EXCEPTION {type(e).__name__}: {e}")
        if not q:
            failed.append(t)
            print(f"  {t:>6}  FAILED (empty payload)")
        else:
            quotes[t] = q
            have = [k for k in WANTED
                    if q.get(k) is not None and q.get(k) != 0]
            miss = [k for k in WANTED if k not in have]
            note = "" if not miss else f"   no {'/'.join(miss)}"
            etf = " [ETF]" if q.get("is_etf") else ""
            print(f"  {t:>6}  ok  price {q.get('lastPrice')}{etf}{note}")
        if i < len(tickers):
            time.sleep(DELAY_S)

    payload = {
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "captured_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "schwab_client.get_quote",
        "watchlist_source": STATE,
        "requested": len(tickers),
        "succeeded": len(quotes),
        "failed": failed,
        "quotes": quotes,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)

    print()
    print(f"wrote {OUT}: {len(quotes)} of {len(tickers)} quotes")
    if failed:
        print(f"FAILED: {failed}")

    if not quotes:
        print()
        print("EVERY CALL FAILED. The usual cause is an expired Schwab OAuth")
        print("token -- the record has one instance of exactly this on 2026-08-04,")
        print("which required a browser reauthorisation. Re-authorise and re-run.")
        print("The file written above is deliberately NOT empty-but-plausible:")
        print("it records succeeded=0 so it cannot be mistaken for a good run.")
        return 1

    # What the caller actually cares about, stated rather than left to inspection.
    usable = [t for t, q in quotes.items()
              if q.get("eps") not in (None, 0) or q.get("peRatio") not in (None, 0)]
    withdiv = [t for t, q in quotes.items() if q.get("divYield") not in (None, 0)]
    print(f"  carry eps or peRatio (equities): {len(usable)}  {sorted(usable)}")
    print(f"  carry a dividend yield:          {len(withdiv)}")
    print()
    print("Nothing else was modified. No orders. Advisory-only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
