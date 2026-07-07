from pathlib import Path

from kagami.corpus.cache import get_or_create_paper_card, mint_paper_id
from kagami.corpus.provider import LiteratureProvider
from kagami.events import append_event

SCOUT_ROLE = "scout"

# Charter discipline (agents/scout.md, Story 8.3): a small default limit so
# a single search doesn't anchor the whole corpus on one query's vocabulary
# — the CLI/charter previously had no way to lower the port's own
# `limit=20` default at all.
DEFAULT_SEARCH_LIMIT = 8

# FR-50: the two directions a citation-graph expansion can walk, matching
# FR-51's port-contract keys exactly — used both as the edge-list
# `direction` value and as the lookup key into `citation_graph`'s result.
EXPANSION_DIRECTIONS = ("cited_by", "references")


class CorpusAccessError(Exception):
    pass


def search_corpus(
    run_dir: Path,
    output_root: Path,
    provider: LiteratureProvider,
    query: str,
    role: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    administrative: bool = False,
) -> dict:
    """FR-25: Scout is the sole corpus-touching role.

    Only `role == "scout"` may reach this far; every other caller is
    refused before any provider is queried or any event is logged — no
    non-Scout call can ever show a raw-corpus retrieval in the event log.
    Each result's paper card is looked up by content-derived id (AD-18) and
    computed only on a cache miss.

    `limit` defaults to `DEFAULT_SEARCH_LIMIT` (8), not the port's own
    `search(query, limit=20)` default — the charter's iteration discipline
    (Story 8.3) depends on a single call not being able to flood the corpus.

    `administrative` (FR-57): self-declared by the caller, the same trust
    model AD-4 already uses for `role` — a non-exploration lookup (e.g. an
    orchestrator convenience re-query) sets it explicitly at the point of
    issuance, never inferred after the fact. `compute_rediscovery_rate`
    excludes any event carrying it.
    """
    if role != SCOUT_ROLE:
        raise CorpusAccessError(
            f"role '{role}' may not query the raw corpus; only '{SCOUT_ROLE}' can (FR-25)"
        )

    raw_results = provider.search(query, limit=limit)
    papers = []
    paper_ids = []
    reused_flags = []
    for raw in raw_results:
        canonical_key = raw["canonical_key"]
        card, reused = get_or_create_paper_card(output_root, canonical_key, lambda raw=raw: raw)
        papers.append({**card, "reused": reused})
        paper_ids.append(card["id"])
        reused_flags.append(reused)

    append_event(
        run_dir,
        "retrieval",
        {
            "kind": "corpus_search",
            "role": SCOUT_ROLE,
            "provider": provider.name,
            "query": query,
            "paper_ids": paper_ids,
            # FR-53: the cache-hit signal per paper_ids' position — kept on
            # the event itself (not just the returned `papers`) so the
            # rediscovery-rate metric is computable purely from the event
            # log, never by re-running the search (AD-11).
            "reused": reused_flags,
            "administrative": administrative,
        },
    )

    return {"ok": True, "papers": papers}


def corpus_expand(
    run_dir: Path,
    output_root: Path,
    provider: LiteratureProvider,
    canonical_key: str,
    role: str,
    administrative: bool = False,
) -> dict:
    """FR-50: Scout's second sanctioned corpus-touching action — grow
    outward from a paper already in the corpus via its citation graph,
    rather than only requerying with different keywords.

    Mirrors `search_corpus`'s role gate exactly (FR-25): refused before any
    provider is queried or any event is logged. For each neighbor id
    `citation_graph` (FR-51) returns, `paper_metadata` fetches its title/
    source so it can be minted through the same `get_or_create_paper_card`
    path a search result uses (AD-18) — an expanded card and a searched
    card are indistinguishable in the cache. The one `retrieval` event this
    appends carries an explicit edge list; replaying a run's `corpus_search`
    and `corpus_expand` events reconstructs the observed citation graph
    exactly, with no separate graph store anywhere (AD-11's derived-state
    pattern, same as AD-20's per-cluster state).

    `administrative` (FR-57): see `search_corpus` — same self-declared,
    at-issuance flag, same exclusion from `compute_rediscovery_rate`.
    """
    if role != SCOUT_ROLE:
        raise CorpusAccessError(
            f"role '{role}' may not query the raw corpus; only '{SCOUT_ROLE}' can (FR-25, FR-50)"
        )

    origin_paper_id = mint_paper_id(canonical_key)
    graph = provider.citation_graph(canonical_key)

    edges = []
    neighbor_paper_ids = []
    for direction in EXPANSION_DIRECTIONS:
        for neighbor_key in graph.get(direction) or []:
            raw = provider.paper_metadata(neighbor_key)
            neighbor_canonical_key = raw.get("canonical_key") or neighbor_key
            card, reused = get_or_create_paper_card(
                output_root, neighbor_canonical_key, lambda raw=raw: raw
            )
            neighbor_paper_ids.append(card["id"])
            # FR-53: `reused` rides on the edge itself for the same reason
            # search_corpus keeps it on the event — the rediscovery-rate
            # metric reads only the event log, never re-runs a query.
            edges.append(
                {"from": origin_paper_id, "to": card["id"], "direction": direction, "reused": reused}
            )

    append_event(
        run_dir,
        "retrieval",
        {
            "kind": "corpus_expand",
            "role": SCOUT_ROLE,
            "provider": provider.name,
            "origin_paper_id": origin_paper_id,
            "canonical_key": canonical_key,
            "edges": edges,
            "administrative": administrative,
        },
    )

    return {"ok": True, "origin_paper_id": origin_paper_id, "neighbor_paper_ids": neighbor_paper_ids, "edges": edges}
