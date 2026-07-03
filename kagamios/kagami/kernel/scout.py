from pathlib import Path

from kagami.corpus.cache import get_or_create_paper_card
from kagami.corpus.provider import LiteratureProvider
from kagami.events import append_event

SCOUT_ROLE = "scout"


class CorpusAccessError(Exception):
    pass


def search_corpus(
    run_dir: Path, output_root: Path, provider: LiteratureProvider, query: str, role: str
) -> dict:
    """FR-25: Scout is the sole corpus-touching role.

    Only `role == "scout"` may reach this far; every other caller is
    refused before any provider is queried or any event is logged — no
    non-Scout call can ever show a raw-corpus retrieval in the event log.
    Each result's paper card is looked up by content-derived id (AD-18) and
    computed only on a cache miss.
    """
    if role != SCOUT_ROLE:
        raise CorpusAccessError(
            f"role '{role}' may not query the raw corpus; only '{SCOUT_ROLE}' can (FR-25)"
        )

    raw_results = provider.search(query)
    papers = []
    paper_ids = []
    for raw in raw_results:
        canonical_key = raw["canonical_key"]
        card, reused = get_or_create_paper_card(output_root, canonical_key, lambda raw=raw: raw)
        papers.append({**card, "reused": reused})
        paper_ids.append(card["id"])

    append_event(
        run_dir,
        "retrieval",
        {
            "kind": "corpus_search",
            "role": SCOUT_ROLE,
            "provider": provider.name,
            "query": query,
            "paper_ids": paper_ids,
        },
    )

    return {"ok": True, "papers": papers}
