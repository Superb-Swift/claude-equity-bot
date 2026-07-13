# =============================================================================
# context_providers.py  —  per-ticker context provider registry
# =============================================================================
# The single extension point for external per-ticker context. Two families:
#
#   mode="blend"   numeric score in [-1,+1]  -> feeds the WS1 blend engine
#                  (C2 sector-backbone, C3 cross-asset-regime)   [BUILT NOW]
#   mode="prompt"  text section              -> appended to the LLM prompt
#                  (news, WS3 commodity context, 3-C EDGAR filings)  [SLOTS]
#
# WHY THIS EXISTS:
#   Adding a new data source (e.g. EDGAR) becomes ONE registration — the blend
#   engine, the risk gate, and the logging never change. This is exactly what
#   the exit-criteria doc meant by "WS3 is EDGAR's technical template."
#   See WS1_Implementation_Spec.md §0 and the EDGAR scope spec.
#
# CONTRACT:
#   A provider is Provider(name, mode, fn). fn is called fn(ticker, caches):
#     blend  -> returns (score: float in [-1,+1], meta: dict)
#     prompt -> returns (text: str, meta: dict)   ("" text = contributes nothing)
#   `caches` is a per-run dict the caller populates once (avoids re-fetching);
#   providers read only the sub-cache they need and must never raise into the
#   run (return a neutral score / empty text on any failure).
# =============================================================================

from dataclasses import dataclass
from typing import Callable


@dataclass
class Provider:
    name: str
    mode: str          # "blend" | "prompt"
    fn: Callable       # fn(ticker, caches) -> (value, meta)


REGISTRY: list = []


def register(provider: Provider) -> Provider:
    """Append a provider. Idempotent by name (re-registration replaces)."""
    global REGISTRY
    REGISTRY = [p for p in REGISTRY if p.name != provider.name]
    REGISTRY.append(provider)
    return provider


def blend_providers() -> list:
    return [p for p in REGISTRY if p.mode == "blend"]


def prompt_providers() -> list:
    return [p for p in REGISTRY if p.mode == "prompt"]


def run_blend_scores(ticker: str, caches: dict):
    """Run every blend provider. Returns ({name: score}, {name: meta}).

    A provider that raises is isolated: it scores 0.0 (neutral) and its
    exception is captured in meta, so one bad provider never breaks the run.
    """
    scores, metas = {}, {}
    for p in blend_providers():
        try:
            s, m = p.fn(ticker, caches or {})
            scores[p.name] = float(s)
            metas[p.name] = m
        except Exception as e:                      # never raise into the run
            scores[p.name] = 0.0
            metas[p.name] = {"error": str(e)}
    return scores, metas


def run_prompt_context(ticker: str, caches: dict) -> str:
    """Concatenated text from all prompt providers. Empty until WS3/EDGAR
    register — this is the hook their filings/commodity sections flow through."""
    parts = []
    for p in prompt_providers():
        try:
            text, _ = p.fn(ticker, caches or {})
            if text:
                parts.append(text)
        except Exception:
            continue
    return "\n\n".join(parts)
