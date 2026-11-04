#!/usr/bin/env python3
"""
input_capture.py - the quote line and position block, as the model saw them.

Claude Equity Bot - Phase 3-C - advisory-only - no orders (DP-T1).

WHAT THIS IS (added 2026-11-03, change D, approved by Rob 2026-11-03)
    `main.capture_inputs` (gap #5 / R6, 2026-10-22) records most of what goes
    into each prompt: headlines, prior closes, prior signals, the SEC block and
    the last price. It did NOT record the quote line (price, OHLC, volume,
    52-week range, P/E, EPS, dividend yield) or the position block. So a risk
    flag that cites those inputs could not be audited from the record. The
    SPCX review of 2026-11-03 hit exactly that: "P/E -245" and "volume 24.9M"
    were known only from the model's own text, and "+$27.90" open P&L could
    not be checked at all (claude/SPCX_RiskFlags_Review_2026-11-03.md, s.4).

    It also completes DP-3C-bg ("generator continuity = parallel old/new on
    captured inputs"): without the quote and position, no captured record
    could be replayed into a prompt.

WHAT IT RECORDS (all added to the same inputs_<date>.jsonl record)
    capture_version   2 (records without this key are version 1)
    quote             the raw quote dict exactly as get_signal received it
    quote_lines       the market-data + fundamentals lines, rendered by
                      claude_signal's OWN builders (not a copy of them)
    position_lines    the position block, rendered by claude_signal's own
                      builder. For a scouted name this is the one-line
                      "Scouting - not currently held" header.
    held              True when the position block is a holding
    user_prompt_sha256 / user_prompt_chars
                      a fingerprint of the full user prompt, rebuilt from
                      the same builders in get_signal's order. --selftest
                      proves the rebuild equals what get_signal sends, on
                      fixtures, with the API client stubbed (no network).
                      It covers the USER prompt only; the system prompt
                      depends only on the prompt variant, which the signals
                      log already records.

WHY IT CANNOT CHANGE WHAT THE MODEL SEES (DP-3C-ai)
    * It is called from capture_inputs, BEFORE get_signal, with the same
      objects. It only reads them (.get, formatting); --selftest checks the
      objects are deep-equal before and after.
    * It never imports into, patches or wraps claude_signal; it calls its
      pure section builders, which have no side effects.
    * main.py wraps the call in its own try/except: any failure here leaves
      the version-1 record intact and the run unaffected (fail-open).

PRIVACY
    Holdings now reach logs/inputs_<date>.jsonl, which is git-ignored
    (logs/* with three named exceptions, none of them inputs). The position
    lines carry account LABELS ("Roth IRA", "Individual"), never account
    numbers. Belt and braces: if a label ever falls back to
    "Account <number>" (schwab_client's fallback for an unmapped account),
    the number is masked to its last four digits and position_lines_masked
    is set, which also marks the fingerprint as not reproducible from the
    record.

Usage
    python input_capture.py --selftest
"""

import copy
import hashlib
import json
import re
import sys

CAPTURE_VERSION = 2
PROMPT_MIRROR = "claude_signal.get_signal assembly as of 2026-11-03"

_ACCOUNT_NUM_RE = re.compile(r"Account (\d{4,})")


def _mask_account_numbers(lines):
    """('Account 12345678' -> 'Account ...5678') for every line; (lines, masked?)."""
    out, masked = [], False
    for ln in lines:
        new = _ACCOUNT_NUM_RE.sub(lambda m: "Account ..." + m.group(1)[-4:], ln)
        masked = masked or (new != ln)
        out.append(new)
    return out, masked


def rebuild_user_prompt(quote, position, headlines, price_history,
                        prior_signals, extra_context, metrics=None, cs=None):
    """The user prompt get_signal assembles, rebuilt from claude_signal's own
    section builders in the same order. Mirrors claude_signal.get_signal
    (2026-11-03); --selftest compares the two byte for byte."""
    if cs is None:
        import claude_signal as cs
    parts = []
    parts.extend(cs._build_market_data_section(quote))
    parts.extend(cs._build_fundamentals_section(quote))
    parts.extend(cs._build_price_history_section(price_history))
    parts.extend(cs._build_prior_signal_section(prior_signals))
    parts.extend(cs._build_position_section(position))
    if headlines:
        parts.append("\nRecent News Headlines:")
        for i, headline in enumerate(headlines[:5], 1):
            parts.append(f"  {i}. {headline}")
    else:
        parts.append("\nRecent News Headlines: None provided")
    if metrics:
        parts.append("\nKey Financial Metrics:")
        for key, value in metrics.items():
            parts.append(f"  {key}: {value}")
    if extra_context:
        parts.append("\n" + extra_context.strip())
    parts.append("\nBased on this data, generate your structured JSON signal.")
    return "\n".join(parts)


def prompt_sections(quote, position, headlines, price_history, prior_signals,
                    extra_context, cs=None):
    """The fields change D adds to an inputs record. Reads its arguments only."""
    if cs is None:
        import claude_signal as cs
    q = quote or {}
    quote_lines = (list(cs._build_market_data_section(q))
                   + list(cs._build_fundamentals_section(q)))
    position_lines, masked = _mask_account_numbers(cs._build_position_section(position))
    prompt = rebuild_user_prompt(q, position, headlines, price_history,
                                 prior_signals, extra_context, cs=cs)
    return {
        "capture_version": CAPTURE_VERSION,
        "quote": dict(q),
        "quote_lines": quote_lines,
        "position_lines": position_lines,
        "position_lines_masked": masked,
        "held": bool(position and position.get("is_held")),
        "user_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "user_prompt_chars": len(prompt),
        "prompt_mirror": PROMPT_MIRROR,
    }


def rebuild_from_record(rec, cs=None):
    """Replay a version-2 record into the user prompt (DP-3C-bg). The position
    block is taken from the record's rendered lines, since the raw position is
    not stored. Returns (prompt, sha_matches)."""
    if cs is None:
        import claude_signal as cs
    q = rec.get("quote") or {}
    parts = []
    parts.extend(cs._build_market_data_section(q))
    parts.extend(cs._build_fundamentals_section(q))
    parts.extend(cs._build_price_history_section(rec.get("price_history")))
    parts.extend(cs._build_prior_signal_section(rec.get("prior_signals")))
    parts.extend(rec.get("position_lines") or [])
    heads = rec.get("headlines")
    if heads:
        parts.append("\nRecent News Headlines:")
        for i, h in enumerate(heads[:5], 1):
            parts.append(f"  {i}. {h}")
    else:
        parts.append("\nRecent News Headlines: None provided")
    ctx = rec.get("extra_context") or ""
    if ctx:
        parts.append("\n" + ctx.strip())
    parts.append("\nBased on this data, generate your structured JSON signal.")
    prompt = "\n".join(parts)
    sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return prompt, sha == rec.get("user_prompt_sha256")


# ----------------------------------------------------------------------------
# selftest: offline, the API client stubbed, at least one negative case each
# ----------------------------------------------------------------------------

_FIX_QUOTE = {
    "ticker": "SPCX", "companyName": "SPACE EXPLORATION TECH", "is_etf": False,
    "asset_type": "EQUITY", "exchange": "NASDAQ", "lastPrice": 142.67,
    "netChange": 6.30, "netPercentChange": 4.62, "openPrice": 138.0,
    "highPrice": 143.5, "lowPrice": 137.2, "closePrice": 136.37,
    "bidPrice": 142.6, "askPrice": 142.7, "totalVolume": 24912345,
    "avg10DayVolume": 120812345.0, "fiftyTwoWeekLow": 98.1,
    "fiftyTwoWeekHigh": 225.64, "peRatio": -245.1, "eps": 0.0, "divYield": 0.0,
}
_FIX_ETF = dict(_FIX_QUOTE, ticker="SPY", companyName="SPDR S&P 500", is_etf=True,
                peRatio=None, eps=None, divYield=1.12)
_FIX_POS_ONE = {"is_held": True, "quantity": 10, "average_price": 139.50,
                "market_value": 1426.70, "current_day_pnl": 63.0,
                "long_open_pnl": 31.70, "held_in_accounts": ["Individual"],
                "account_breakdown": [{"account_label": "Individual", "quantity": 10,
                                       "average_price": 139.5, "market_value": 1426.7,
                                       "long_open_pnl": 31.7}]}
_FIX_POS_MULTI = {"is_held": True, "quantity": 30, "average_price": 50.0,
                  "market_value": 1600.0, "current_day_pnl": -5.0,
                  "long_open_pnl": 100.0,
                  "held_in_accounts": ["Roth IRA", "Account 98765432"],
                  "account_breakdown": [
                      {"account_label": "Roth IRA", "quantity": 10, "average_price": 50.0,
                       "market_value": 533.3, "long_open_pnl": 33.3},
                      {"account_label": "Account 98765432", "quantity": 20,
                       "average_price": 50.0, "market_value": 1066.7,
                       "long_open_pnl": 66.7}]}
_FIX_HIST = [{"date": "2026-10-27", "close": 148.58}, {"date": "2026-10-28", "close": 145.23},
             {"date": "2026-10-29", "close": 143.89}, {"date": "2026-10-30", "close": 134.72},
             {"date": "2026-11-02", "close": 136.37}]
_FIX_PRIOR = [{"date": "2026-10-30", "signal": "BUY", "conf": 70},
              {"date": "2026-11-02", "signal": "BUY", "conf": 72}]
_FIX_HEADS = [f"[Yahoo] headline {i}" for i in range(1, 8)]      # 7: get_signal keeps 5
_FIX_CTX = "--- SEC FILINGS (recent, as of 2026-11-03) ---\n8-K: fixture text\n"


class _StubResp:
    class _C:
        text = '{"ticker": "X", "signal": "HOLD", "confidence": 50, "data_quality": "HIGH"}'
    class _U:
        input_tokens = 1
        output_tokens = 1
    content = [_C()]
    usage = _U()


class _StubClient:
    """Records what get_signal would send; never touches the network."""
    def __init__(self):
        self.calls = []
        outer = self

        class _M:
            def create(self, **kw):
                outer.calls.append(kw)
                return _StubResp()
        self.messages = _M()


def _sent_prompt(cs, **kw):
    stub, real = _StubClient(), cs.client
    cs.client = stub
    try:
        cs.get_signal(**kw)
    finally:
        cs.client = real
    return stub.calls[-1]["messages"][0]["content"]


def selftest():
    import claude_signal as cs
    fails = []

    def check(label, ok):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            fails.append(label)

    cases = [
        ("equity, single-account holding", _FIX_QUOTE, _FIX_POS_ONE, _FIX_HEADS, _FIX_CTX),
        ("equity, scouted, no headlines, no SEC block", _FIX_QUOTE, None, [], ""),
        ("ETF, multi-account holding", _FIX_ETF, _FIX_POS_MULTI, _FIX_HEADS[:2], _FIX_CTX),
        ("equity, position {'is_held': False}", _FIX_QUOTE, {"is_held": False}, _FIX_HEADS, ""),
    ]
    for label, q, pos, heads, ctx in cases:
        args = dict(quote=q, position=pos, headlines=heads, price_history=_FIX_HIST,
                    prior_signals=_FIX_PRIOR, extra_context=ctx)
        before = copy.deepcopy(args)
        sec = prompt_sections(**args)
        check(f"{label}: arguments unchanged by capture", args == before)
        sent = _sent_prompt(cs, ticker=q["ticker"], metrics=None, prompt_variant="A", **args)
        check(f"{label}: rebuilt prompt == prompt get_signal sends (byte-identical)",
              hashlib.sha256(sent.encode("utf-8")).hexdigest() == sec["user_prompt_sha256"]
              and len(sent) == sec["user_prompt_chars"])
        check(f"{label}: quote_lines and position_lines appear verbatim in the sent prompt",
              all(ln in sent for ln in sec["quote_lines"])
              and (sec["position_lines_masked"] or all(ln in sent for ln in sec["position_lines"])))
        rec = dict(sec, headlines=heads, price_history=_FIX_HIST,
                   prior_signals=_FIX_PRIOR, extra_context=ctx)
        rec = json.loads(json.dumps(rec, default=str))           # through the file format
        _, match = rebuild_from_record(rec)
        check(f"{label}: record replays to the same fingerprint (DP-3C-bg)",
              match == (not sec["position_lines_masked"]))

    # Content checks on what was missing before 2026-11-03.
    sec = prompt_sections(_FIX_QUOTE, _FIX_POS_ONE, _FIX_HEADS, _FIX_HIST, _FIX_PRIOR, _FIX_CTX)
    check("quote_lines carry the P/E | EPS line as rendered",
          any(ln.startswith("P/E Ratio: -245.1 | EPS: $0.0") for ln in sec["quote_lines"]))
    check("quote_lines carry the volume line as rendered",
          any(ln.startswith("Volume: 24,912,345 (10-day avg: 120,812,345)") for ln in sec["quote_lines"]))
    check("position_lines carry Total Open P&L", any("Total Open P&L : $31.70" in ln
                                                     for ln in sec["position_lines"]))
    check("held flag set for a holding, clear for a scout",
          sec["held"] is True and prompt_sections(_FIX_QUOTE, None, [], [], [], "")["held"] is False)
    check("raw quote kept, eps 0.0 not coerced", sec["quote"]["eps"] == 0.0
          and sec["quote"]["peRatio"] == -245.1)

    # Masking: an account number never reaches the record.
    m = prompt_sections(_FIX_ETF, _FIX_POS_MULTI, [], [], [], "")
    blob = json.dumps(m)
    check("NEGATIVE: an unmapped account number is masked to its last four",
          "98765432" not in blob and "Account ...5432" in blob and m["position_lines_masked"])

    # NEGATIVE: the byte comparison is shown to fail when the rebuild differs.
    args = dict(quote=_FIX_QUOTE, position=_FIX_POS_ONE, headlines=_FIX_HEADS,
                price_history=_FIX_HIST, prior_signals=_FIX_PRIOR, extra_context=_FIX_CTX)
    sent = _sent_prompt(cs, ticker="SPCX", metrics=None, prompt_variant="A", **args)
    wrong = rebuild_user_prompt(**dict(args, extra_context=""))
    check("NEGATIVE: a rebuild without the SEC block does NOT match", wrong != sent)
    wrong = rebuild_user_prompt(**dict(args, headlines=_FIX_HEADS[:4]))
    check("NEGATIVE: a rebuild with 4 of 5 headlines does NOT match", wrong != sent)
    rec = json.loads(json.dumps(dict(prompt_sections(**args), headlines=_FIX_HEADS,
                                     price_history=_FIX_HIST, prior_signals=_FIX_PRIOR,
                                     extra_context=_FIX_CTX)))
    rec["quote"]["eps"] = 1.23
    check("NEGATIVE: a tampered record does NOT replay to its fingerprint",
          rebuild_from_record(rec)[1] is False)

    print()
    if fails:
        print(f"input_capture selftest: {len(fails)} FAILED")
        return 1
    print("input_capture selftest: all checks passed (offline; the API client was stubbed)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(0)
