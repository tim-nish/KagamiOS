import hashlib
from pathlib import Path
from typing import Callable

import yaml

from kagami.corpus.extraction import (
    CONTENT_SOURCE_ABSTRACT,
    CONTENT_SOURCE_NONE,
    Extractor,
    extract_card_content,
)
from kagami.events import append_event
from kagami.registry import load_registry
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock
from kagami.store.read import ConsumptionError

PAPER_CARD_SCHEMA_VERSION = 1

# FR-55: the `retrieval` event kind a sanctioned paper-card read appends —
# the corpus-cache analogue of `read_artifact`'s `summary_read`/
# `full_text_pull`, distinctly loggable the same way.
PAPER_CARD_READ_KIND = "paper_card_read"

# FR-52/AD-28: a paper card is a frame-independent fact, cached forever
# across runs — a frame-dependent valuation may never land on it. This is
# the hard schema invariant enforced at the write chokepoint; a judgment
# about a paper belongs in the appraisal store (`kagami/store/appraisal.py`),
# stamped with the frame version that produced it, never here.
FORBIDDEN_CARD_FIELDS = frozenset({"relevance", "priority", "judgment", "meaningful_to_me"})


class CorpusCacheError(Exception):
    pass


def _reject_frame_dependent_fields(raw: dict) -> None:
    present = FORBIDDEN_CARD_FIELDS & set(raw)
    if present:
        raise CorpusCacheError(
            f"paper card write refused: frame-dependent field(s) {sorted(present)} may never "
            "appear on a paper card (FR-52/AD-28) — record a judgment via the appraisal store instead"
        )


def mint_paper_id(canonical_key: str) -> str:
    """AD-18: content-derived, not opaque-random — concurrent minting of the
    same paper (by DOI/arXiv-ID) converges instead of colliding."""
    if not canonical_key:
        raise CorpusCacheError("cannot mint a paper id from an empty canonical_key")
    digest = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:12]
    return f"ppr-{digest}"


def _corpus_dir(output_root: Path) -> Path:
    return output_root / "corpus"


def _paper_path(output_root: Path, paper_id: str) -> Path:
    return _corpus_dir(output_root) / f"{paper_id}.yaml"


def get_or_create_paper_card(
    output_root: Path,
    canonical_key: str,
    compute: Callable[[], dict],
    extract: Extractor = extract_card_content,
) -> tuple[dict, bool]:
    """AD-18/SPEC CAP-6: a paper card is computed once and reused across runs.

    Returns (card, reused) — `reused` is True when an existing cache entry
    satisfied the request without calling `compute` (or `extract`).

    FR-54/AD-29: on a cache miss, `extract` runs at most once — never on a
    cache hit — populating the card's content fields from `compute()`'s
    title+abstract. A provider result with no abstract (or no `extract`
    injected) leaves the content fields empty and marks `content_source`
    accordingly — a real sensor bias, exposed rather than papered over,
    never fabricated or approximated content.
    """
    paper_id = mint_paper_id(canonical_key)
    corpus_dir = _corpus_dir(output_root)
    lock_path = corpus_dir / ".lock"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    with acquire_run_lock(lock_path):
        path = _paper_path(output_root, paper_id)
        if path.is_file():
            return yaml.safe_load(path.read_text()), True

        raw = compute()
        _reject_frame_dependent_fields(raw)

        abstract = (raw.get("abstract") or "").strip()
        if abstract and extract is not None:
            content = extract(raw.get("title", ""), abstract)
            content_source = CONTENT_SOURCE_ABSTRACT
        else:
            content = {"contribution_line": "", "method_class": "", "evidence_type": "", "key_claims": []}
            content_source = CONTENT_SOURCE_NONE

        card = {
            "id": paper_id,
            "schema_version": PAPER_CARD_SCHEMA_VERSION,
            "bibliographic_identity": canonical_key,
            "contribution_line": content["contribution_line"],
            "method_class": content["method_class"],
            "evidence_type": content["evidence_type"],
            "key_claims": content["key_claims"],
            "content_source": content_source,
            "title": raw.get("title", ""),
            "source": raw.get("source", ""),
        }
        atomic_write(path, yaml.safe_dump(card, sort_keys=False))
        return card, False


def read_paper_card(
    run_dir: Path, output_root: Path, state: str, paper_id: str, registry=None
) -> dict:
    """FR-55: the sole sanctioned way to read a paper card's content — no
    role reads a corpus-cache file off disk directly (that would be the
    off-charter workaround `change-signal-paper-content-2026-07-06.md`'s
    verified state describes).

    Gated per state via `registry.can_read_paper_card`, an allowlist
    audited separately from FR-15's artifact-only `consumption_map`
    because a paper card lives in the AD-18 corpus-cache store, not the
    versioned artifact store `consumption_map` gates. Every successful
    read appends its own `retrieval` event — the same logged-read pattern
    `read_artifact`'s `summary_read`/`full_text_pull` already established.
    """
    registry = registry or load_registry()
    if not registry.can_read_paper_card(state):
        raise ConsumptionError(
            f"state '{state}' has no defined brief for reading paper-card content (FR-55)"
        )

    path = _paper_path(output_root, paper_id)
    if not path.is_file():
        raise CorpusCacheError(f"no paper card found for id '{paper_id}'")
    card = yaml.safe_load(path.read_text())

    append_event(
        run_dir, "retrieval", {"kind": PAPER_CARD_READ_KIND, "state": state, "paper_id": paper_id}
    )

    return {"ok": True, "card": card}
