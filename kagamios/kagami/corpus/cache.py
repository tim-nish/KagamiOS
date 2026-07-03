import hashlib
from pathlib import Path
from typing import Callable

import yaml

from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock

PAPER_CARD_SCHEMA_VERSION = 1


class CorpusCacheError(Exception):
    pass


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
    output_root: Path, canonical_key: str, compute: Callable[[], dict]
) -> tuple[dict, bool]:
    """AD-18/SPEC CAP-6: a paper card is computed once and reused across runs.

    Returns (card, reused) — `reused` is True when an existing cache entry
    satisfied the request without calling `compute`.
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
        card = {
            "id": paper_id,
            "schema_version": PAPER_CARD_SCHEMA_VERSION,
            "bibliographic_identity": canonical_key,
            "contribution_line": raw.get("contribution_line", ""),
            "method_class": raw.get("method_class", ""),
            "evidence_type": raw.get("evidence_type", ""),
            "key_claims": raw.get("key_claims", []),
            "title": raw.get("title", ""),
            "source": raw.get("source", ""),
        }
        atomic_write(path, yaml.safe_dump(card, sort_keys=False))
        return card, False
