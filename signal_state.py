# =============================================================================
# signal_state.py
# =============================================================================
# PURPOSE:
#   Persistence for the WS2 "S1" prior-signal state input (H1 feature-level):
#   the bot's own last-N outputs per ticker, fed back into the next prompt so
#   the model can see its own staleness against the price trajectory it is
#   already shown.
#
# ANALYST NOTE:
#   - Stores RAW confidence only (the model's own output, pre-damping). Lever
#     A's operative values must never enter this file, or the model-side
#     channel is contaminated and the WS2 two-channel readout collapses.
#   - Same-date updates OVERWRITE (last run of a date wins). Consequence: a PM
#     diagnostic run replaces that date's AM entry — re-run
#     seed_signal_state.py from the tracker afterwards to restore the
#     AM-canonical chain. The tracker is always ground truth; this file is a
#     derived cache and is re-seedable at any time.
#   - The file is gitignored runtime data. Missing/corrupt file degrades to {}
#     (the prompt section renders its "no prior state" form and the chain
#     rebuilds from today) — it must never crash the daily run.
#
# DEPENDENCIES:
#   Standard library only (json, os).
# =============================================================================

import json
import os

STATE_FILE = "signal_state.json"
KEEP_LAST = 5


def load_signal_state(path: str = STATE_FILE) -> dict:
    """
    Load {TICKER: [{"date": "YYYY-MM-DD", "signal": "HOLD", "conf": 52}, ...]}
    — entries oldest-first, at most KEEP_LAST per ticker.

    Returns {} on a missing or unreadable file (never raises into the run).
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        return state if isinstance(state, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"[signal_state] Could not read {path} ({e}) — starting empty. "
              f"Re-seed from the tracker with seed_signal_state.py if needed.")
        return {}


def save_signal_state(state: dict, path: str = STATE_FILE) -> None:
    """
    Atomic-ish write: temp file + os.replace (safe on Windows), so a crash
    mid-write can never leave a truncated state file behind.
    """
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except OSError as e:
        print(f"[signal_state] WARNING: could not save {path}: {e}")


def update_signal_state(state: dict, ticker: str, date_str: str,
                        signal: str, conf_raw: int, keep: int = KEEP_LAST) -> None:
    """
    Append/replace the ticker's entry for date_str and keep the last `keep`.

    ANALYST NOTE:
        Entries are kept date-sorted so seeded and live entries interleave
        correctly regardless of write order; same-date entries collapse to
        the most recent write (see the PM-diagnostic note in the header).
    """
    entries = [e for e in state.get(ticker, []) if e.get("date") != date_str]
    entries.append({"date": date_str, "signal": signal, "conf": int(conf_raw)})
    entries.sort(key=lambda e: e.get("date", ""))
    state[ticker] = entries[-keep:]
