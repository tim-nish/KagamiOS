import re
from typing import Callable

# FR-54/AD-29 rung 2: the design doc describes mint-time extraction as
# "one model call." kagamios's core carries no LLM SDK dependency at all
# (`pyproject.toml`: pyyaml only) and describes itself as a "deterministic
# gatekeeper core" — `resolve_model` (kernel/dispatch.py) only ever *names*
# a tier/model for an external caller, it never invokes one. So this
# heuristic, not a live API call, is what actually runs today; it's a
# deterministic stand-in for the harness-backed extractor
# `dispatch.yaml`'s `paper_card_extraction: cheap-model` entry already
# reserves an operation-class home for, in the same spirit as
# `historian.py`'s `detect_frontier_speculation`. Swapping in a real call
# later doesn't need `get_or_create_paper_card`'s contract to change —
# only this function's body.

CONTENT_SOURCE_ABSTRACT = "abstract"
CONTENT_SOURCE_NONE = "none"

_THEORETICAL_MARKERS = (
    "theorem", "we prove", "proof", "bound", "theoretical", "lemma",
    "formally", "analysis shows",
)
_EMPIRICAL_MARKERS = (
    "experiment", "evaluat", "benchmark", "dataset", "empirical",
    "we measure", "we test", "results show",
)
_QUANTITATIVE_MARKERS = (
    "%", "accuracy", "precision", "recall", "improve", "outperform",
    "significant", "dataset", "benchmark",
)
_CLAIM_MARKERS = (
    "we show", "we demonstrate", "we find", "results indicate",
    "we propose", "we introduce", "our results",
)

Extractor = Callable[[str, str], dict]


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _matches_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def extract_card_content(title: str, abstract: str) -> dict:
    """FR-54: derive a card's content fields from provider-supplied
    title+abstract, once, at mint time. `method_class` is checked for
    theoretical markers before empirical ones — a paper proving a bound
    about its own experiments should read as theoretical work, the rarer
    and more specific signal.
    """
    sentences = _split_sentences(abstract)

    if _matches_any(abstract, _THEORETICAL_MARKERS):
        method_class = "theoretical"
    elif _matches_any(abstract, _EMPIRICAL_MARKERS):
        method_class = "empirical"
    else:
        method_class = "unspecified"

    evidence_type = "quantitative" if _matches_any(abstract, _QUANTITATIVE_MARKERS) else "qualitative"

    key_claims = [s for s in sentences if _matches_any(s, _CLAIM_MARKERS)]
    if not key_claims and sentences:
        key_claims = sentences[:1]

    return {
        "contribution_line": sentences[0] if sentences else "",
        "method_class": method_class,
        "evidence_type": evidence_type,
        "key_claims": key_claims,
    }
