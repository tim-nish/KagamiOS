import json

import pytest

from kagami.corpus.cache import mint_paper_id
from kagami.corpus.provider import LiteratureProvider
from kagami.kernel.scout import CorpusAccessError, DEFAULT_SEARCH_LIMIT, corpus_expand, search_corpus
from kagami.store.run import open_run


class _StubProvider(LiteratureProvider):
    name = "stub"

    def __init__(self, results, graph=None, metadata_by_key=None):
        self._results = results
        self._graph = graph or {}
        self._metadata_by_key = metadata_by_key or {}

    def search(self, query, limit=20):
        return self._results

    def paper_metadata(self, canonical_key):
        return self._metadata_by_key[canonical_key]

    def citation_graph(self, canonical_key):
        return self._graph


def _open(tmp_path, run_id="run-scout"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id, tmp_path / "_out"


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_scout_role_search_succeeds_and_logs_a_retrieval_event(tmp_path):
    run_dir, output_root = _open(tmp_path)
    provider = _StubProvider([{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}])

    result = search_corpus(run_dir, output_root, provider, "signature methods", role="scout")
    assert result["ok"] is True
    assert len(result["papers"]) == 1
    assert result["papers"][0]["bibliographic_identity"] == "10.1/a"

    retrievals = [e for e in _events(run_dir) if e["family"] == "retrieval" and e["kind"] == "corpus_search"]
    assert len(retrievals) == 1
    assert retrievals[0]["role"] == "scout"
    assert retrievals[0]["provider"] == "stub"


def test_non_scout_role_is_refused_and_logs_nothing(tmp_path):
    run_dir, output_root = _open(tmp_path)
    provider = _StubProvider([{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}])

    with pytest.raises(CorpusAccessError):
        search_corpus(run_dir, output_root, provider, "signature methods", role="cartographer")

    events = _events(run_dir)
    assert not any(e["family"] == "retrieval" for e in events)


def test_search_corpus_defaults_to_the_small_charter_limit_not_the_ports_own_default(tmp_path):
    """Story 8.3: the charter's iteration discipline depends on a single
    search call not being able to flood the corpus — DEFAULT_SEARCH_LIMIT
    (8) must actually reach the provider, not just exist as a constant."""
    run_dir, output_root = _open(tmp_path)
    captured_limits = []

    class _CapturingProvider(LiteratureProvider):
        name = "capturing"

        def search(self, query, limit=20):
            captured_limits.append(limit)
            return []

        def paper_metadata(self, canonical_key):
            raise NotImplementedError

        def citation_graph(self, canonical_key):
            raise NotImplementedError

    search_corpus(run_dir, output_root, _CapturingProvider(), "q", role="scout")
    assert captured_limits == [DEFAULT_SEARCH_LIMIT]

    search_corpus(run_dir, output_root, _CapturingProvider(), "q", role="scout", limit=3)
    assert captured_limits == [DEFAULT_SEARCH_LIMIT, 3]


def test_second_search_reuses_the_cached_paper_card_across_runs(tmp_path):
    run_dir_1, output_root = _open(tmp_path, run_id="run-1")
    provider = _StubProvider([{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}])
    search_corpus(run_dir_1, output_root, provider, "q", role="scout")

    open_run(run_id="run-2", output_root=output_root)
    run_dir_2 = output_root / "runs" / "run-2"
    result = search_corpus(run_dir_2, output_root, provider, "q", role="scout")

    assert result["papers"][0]["reused"] is True


def test_corpus_expand_role_gate_refuses_before_any_provider_call(tmp_path):
    run_dir, output_root = _open(tmp_path)

    class _ExplodingProvider(LiteratureProvider):
        name = "exploding"

        def search(self, query, limit=20):
            raise AssertionError("search must not be called")

        def paper_metadata(self, canonical_key):
            raise AssertionError("paper_metadata must not be called")

        def citation_graph(self, canonical_key):
            raise AssertionError("citation_graph must not be called")

    with pytest.raises(CorpusAccessError):
        corpus_expand(run_dir, output_root, _ExplodingProvider(), "10.1/a", role="cartographer")

    assert not any(e["family"] == "retrieval" for e in _events(run_dir))


def test_corpus_expand_mints_neighbor_cards_and_logs_an_edge_carrying_retrieval_event(tmp_path):
    run_dir, output_root = _open(tmp_path)
    provider = _StubProvider(
        results=[],
        graph={"cited_by": ["10.1/b"], "references": ["10.1/c"]},
        metadata_by_key={
            "10.1/b": {"canonical_key": "10.1/b", "title": "Paper B", "source": "stub"},
            "10.1/c": {"canonical_key": "10.1/c", "title": "Paper C", "source": "stub"},
        },
    )

    result = corpus_expand(run_dir, output_root, provider, "10.1/a", role="scout")

    assert result["ok"] is True
    assert result["origin_paper_id"] == mint_paper_id("10.1/a")
    assert len(result["neighbor_paper_ids"]) == 2
    assert {e["direction"] for e in result["edges"]} == {"cited_by", "references"}
    assert all(e["from"] == result["origin_paper_id"] for e in result["edges"])

    expansions = [e for e in _events(run_dir) if e["family"] == "retrieval" and e["kind"] == "corpus_expand"]
    assert len(expansions) == 1
    assert expansions[0]["role"] == "scout"
    assert expansions[0]["origin_paper_id"] == result["origin_paper_id"]
    assert len(expansions[0]["edges"]) == 2


def test_corpus_expand_neighbor_card_goes_through_the_same_cache_path_as_search(tmp_path):
    """FR-50: an expanded card and a searched card must be indistinguishable
    in the cache — both go through `get_or_create_paper_card`, so a paper
    found by expand and later found again by search is reused, not
    recomputed."""
    run_dir, output_root = _open(tmp_path)
    expand_provider = _StubProvider(
        results=[],
        graph={"cited_by": ["10.1/b"], "references": []},
        metadata_by_key={"10.1/b": {"canonical_key": "10.1/b", "title": "Paper B", "source": "stub"}},
    )
    corpus_expand(run_dir, output_root, expand_provider, "10.1/a", role="scout")

    search_provider = _StubProvider([{"canonical_key": "10.1/b", "title": "Paper B", "source": "stub"}])
    result = search_corpus(run_dir, output_root, search_provider, "q", role="scout")

    assert result["papers"][0]["reused"] is True


def test_corpus_expand_with_empty_citation_graph_logs_an_event_with_no_edges(tmp_path):
    run_dir, output_root = _open(tmp_path)
    provider = _StubProvider(results=[], graph={"cited_by": [], "references": []})

    result = corpus_expand(run_dir, output_root, provider, "10.1/a", role="scout")

    assert result["edges"] == []
    assert result["neighbor_paper_ids"] == []
    expansions = [e for e in _events(run_dir) if e["family"] == "retrieval" and e["kind"] == "corpus_expand"]
    assert len(expansions) == 1
    assert expansions[0]["edges"] == []
