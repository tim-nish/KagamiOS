import urllib.parse

import pytest

from kagami.corpus.adapters import (
    PROVIDER_REGISTRY,
    ArxivProvider,
    DEFAULT_LITERATURE_PROVIDER,
    GitHubProvider,
    OpenAlexProvider,
    SemanticScholarProvider,
    _parse_arxiv_feed,
    resolve_provider,
)
from kagami.corpus.provider import LiteratureProvider, ProviderError


def test_resolve_provider_threads_backoff_config_into_the_adapter():
    provider = resolve_provider(
        {"literature_provider": "arxiv", "provider_max_retries": 7, "provider_base_delay_seconds": 0.1}
    )
    assert provider._max_retries == 7
    assert provider._base_delay_seconds == 0.1


def test_resolve_provider_without_backoff_config_uses_adapter_defaults():
    from kagami.corpus.backoff import DEFAULT_BASE_DELAY_SECONDS, DEFAULT_MAX_RETRIES

    provider = resolve_provider({"literature_provider": "arxiv"})
    assert provider._max_retries == DEFAULT_MAX_RETRIES
    assert provider._base_delay_seconds == DEFAULT_BASE_DELAY_SECONDS

FIXTURES = {
    "openalex": {
        "search": {"results": [{"doi": "10.1/a", "title": "Paper A"}]},
        "metadata": {"doi": "10.1/a", "title": "Paper A", "referenced_works": ["https://openalex.org/W3"]},
        # Recorded shape of `/works?filter=cites:{id}` — the real list endpoint,
        # not the non-existent `/works/{id}/citations` sub-resource.
        "citations": {"results": [{"id": "https://openalex.org/W2"}]},
    },
    "semantic-scholar": {
        "search": {"data": [{"paperId": "ss-1", "title": "Paper B"}]},
        "metadata": {"paperId": "ss-1", "title": "Paper B"},
        # Recorded shape of the real /citations and /references endpoints: each
        # `data` item nests the neighbor paper under citingPaper/citedPaper.
        "citations": {"data": [{"citingPaper": {"paperId": "ss-2"}}]},
        "references": {"data": [{"citedPaper": {"paperId": "ss-3"}}]},
    },
    "arxiv": {
        "search": {"entries": [{"arxiv_id": "2101.00001", "title": "Paper C"}]},
        "metadata": {"entries": [{"arxiv_id": "2101.00001", "title": "Paper C"}]},
        "citations": {},
    },
    "github": {
        "search": {"items": [{"full_name": "org/repo"}]},
        "metadata": {"full_name": "org/repo"},
        "citations": {},
    },
}


def _fake_fetch(name):
    calls = {"search": 0, "metadata": 0, "citations": 0, "references": 0}

    def fetch(url: str) -> dict:
        if "search" in url or "query=" in url:
            calls["search"] += 1
            return FIXTURES[name]["search"]
        # FR-51: check "references" before "citations" — Semantic Scholar's
        # references endpoint is its own URL, distinct from /citations.
        if "references" in url:
            calls["references"] += 1
            return FIXTURES[name]["references"]
        # OpenAlex's incoming-citations query is `/works?filter=cites:{id}`, not
        # a `/citations` sub-resource — dispatch it to the same fixture bucket.
        if "citations" in url or "filter=cites:" in url:
            calls["citations"] += 1
            return FIXTURES[name]["citations"]
        calls["metadata"] += 1
        return FIXTURES[name]["metadata"]

    fetch.calls = calls
    return fetch


ADAPTER_CLASSES = [OpenAlexProvider, SemanticScholarProvider, ArxivProvider, GitHubProvider]


@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES)
def test_every_adapter_passes_the_same_contract_test(adapter_cls):
    """SPEC CAP-6 / AD-7: swapping providers requires no code change — every
    adapter must satisfy the same shape for search/paper_metadata/citation_graph."""
    provider = adapter_cls(fetch=_fake_fetch(adapter_cls.name))
    assert isinstance(provider, LiteratureProvider)

    results = provider.search("signature methods")
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["canonical_key"]
    assert results[0]["title"]
    assert results[0]["source"] == adapter_cls.name

    metadata = provider.paper_metadata(results[0]["canonical_key"])
    assert metadata["canonical_key"]
    assert metadata["source"] == adapter_cls.name

    graph = provider.citation_graph(results[0]["canonical_key"])
    assert graph["canonical_key"] == results[0]["canonical_key"]
    assert "cited_by" in graph
    assert "references" in graph  # FR-51: both keys always present, even when empty


def test_openalex_search_reconstructs_abstract_from_the_inverted_index():
    """FR-54: OpenAlex never returns a plain abstract string —
    `abstract_inverted_index` maps each word to its position(s); this is
    zero extra retrieval since the index rides on the same search response
    `_to_result` already reads title/doi from."""
    fetch = lambda url: {
        "results": [
            {
                "doi": "10.1/a",
                "title": "Paper A",
                "abstract_inverted_index": {"We": [0], "prove": [1], "a": [2], "theorem": [3]},
            }
        ]
    }
    provider = OpenAlexProvider(fetch=fetch)
    results = provider.search("signature methods")
    assert results[0]["abstract"] == "We prove a theorem"


def test_openalex_search_with_no_inverted_index_yields_an_empty_abstract():
    provider = OpenAlexProvider(fetch=_fake_fetch("openalex"))
    results = provider.search("signature methods")
    assert results[0]["abstract"] == ""


def test_semantic_scholar_passes_through_a_provided_abstract():
    fetch = lambda url: {"data": [{"paperId": "ss-1", "title": "Paper B", "abstract": "We prove a bound."}]}
    provider = SemanticScholarProvider(fetch=fetch)
    results = provider.search("signature methods")
    assert results[0]["abstract"] == "We prove a bound."


@pytest.mark.parametrize("adapter_cls", [ArxivProvider, GitHubProvider])
def test_arxiv_and_github_carry_no_abstract_field(adapter_cls):
    """FR-54: arXiv and GitHub have no abstract data as of this writing —
    `_to_result` must not fabricate one; `get_or_create_paper_card` reads
    its absence as `content_source: none`."""
    provider = adapter_cls(fetch=_fake_fetch(adapter_cls.name))
    results = provider.search("signature methods")
    assert "abstract" not in results[0]


def test_openalex_citation_graph_returns_both_directions():
    provider = OpenAlexProvider(fetch=_fake_fetch("openalex"))
    graph = provider.citation_graph("10.1/a")
    assert graph["cited_by"] == ["https://openalex.org/W2"]
    assert graph["references"] == ["https://openalex.org/W3"]


def test_semantic_scholar_citation_graph_returns_both_directions():
    provider = SemanticScholarProvider(fetch=_fake_fetch("semantic-scholar"))
    graph = provider.citation_graph("ss-1")
    assert graph["cited_by"] == ["ss-2"]
    assert graph["references"] == ["ss-3"]


def _recording_fetch(name):
    """Recorded-fixture contract helper: dispatches on the *real*, documented
    URL shape for each provider (not a loose substring match), so a call to a
    non-existent or renamed endpoint fails the test instead of silently
    falling through to an unrelated fixture."""
    requested = []

    def fetch(url: str) -> dict:
        requested.append(url)
        if name == "openalex":
            if url.startswith("https://api.openalex.org/works?filter=cites:"):
                return FIXTURES["openalex"]["citations"]
            if url.startswith("https://api.openalex.org/works/"):
                return FIXTURES["openalex"]["metadata"]
        if name == "semantic-scholar":
            if url == "https://api.semanticscholar.org/graph/v1/paper/ss-1/citations":
                return FIXTURES["semantic-scholar"]["citations"]
            if url == "https://api.semanticscholar.org/graph/v1/paper/ss-1/references":
                return FIXTURES["semantic-scholar"]["references"]
        raise AssertionError(f"unexpected URL for provider '{name}': {url}")

    fetch.requested = requested
    return fetch


def test_openalex_citation_graph_queries_the_real_cites_filter_endpoint():
    """Recorded-fixture contract test (docs/dogfooding-review.md finding 1):
    OpenAlex has no `/works/{id}/citations` sub-resource — incoming citations
    must come from the `/works` list endpoint filtered by `cites`."""
    fetch = _recording_fetch("openalex")
    provider = OpenAlexProvider(fetch=fetch)

    graph = provider.citation_graph("10.1/a")

    assert "https://api.openalex.org/works?filter=cites:10.1/a" in fetch.requested
    assert not any(url.endswith("/10.1/a/citations") for url in fetch.requested)
    assert graph["cited_by"] == ["https://openalex.org/W2"]
    assert graph["references"] == ["https://openalex.org/W3"]


def test_semantic_scholar_citation_graph_unwraps_the_nested_paper_objects():
    """Recorded-fixture contract test: the real /citations and /references
    responses nest each neighbor under citingPaper/citedPaper — a flat
    `paperId` silently resolves to None against the live API."""
    fetch = _recording_fetch("semantic-scholar")
    provider = SemanticScholarProvider(fetch=fetch)

    graph = provider.citation_graph("ss-1")

    assert "https://api.semanticscholar.org/graph/v1/paper/ss-1/citations" in fetch.requested
    assert "https://api.semanticscholar.org/graph/v1/paper/ss-1/references" in fetch.requested
    assert graph["cited_by"] == ["ss-2"]
    assert graph["references"] == ["ss-3"]
    assert None not in graph["cited_by"]
    assert None not in graph["references"]


@pytest.mark.parametrize("adapter_cls", [ArxivProvider, GitHubProvider])
def test_arxiv_and_github_citation_graph_makes_no_network_call(adapter_cls):
    """Recorded-fixture contract test: arXiv and GitHub have no citation-graph
    API in either direction (FR-51) — `citation_graph` must return the empty
    edges as a hardcoded, honest bias, never attempt a request that would 404."""

    def failing_fetch(url: str) -> dict:
        raise AssertionError(f"{adapter_cls.name}.citation_graph should never call fetch, got {url}")

    provider = adapter_cls(fetch=failing_fetch)
    graph = provider.citation_graph("some-key")
    assert graph == {"canonical_key": "some-key", "cited_by": [], "references": []}


@pytest.mark.parametrize("adapter_cls", [ArxivProvider, GitHubProvider])
def test_arxiv_and_github_legitimately_return_empty_citation_graphs_in_both_directions(adapter_cls):
    """FR-51: no real citation-graph source in either direction for these
    two adapters — an exposed provider bias, not a gap to fabricate around."""
    provider = adapter_cls(fetch=_fake_fetch(adapter_cls.name))
    graph = provider.citation_graph("some-key")
    assert graph["cited_by"] == []
    assert graph["references"] == []


def test_resolve_provider_defaults_to_config_value_no_call_site_hardcodes_it():
    provider = resolve_provider({"literature_provider": "arxiv"}, fetch=_fake_fetch("arxiv"))
    assert isinstance(provider, ArxivProvider)


def test_resolve_provider_override_wins_over_configs_default():
    """FR-15/FR-25/story 9.3: `--provider` routes around a single broken
    or rate-limited provider without needing to edit `config.yaml`."""
    provider = resolve_provider(
        {"literature_provider": "openalex"}, fetch=_fake_fetch("arxiv"), provider_override="arxiv"
    )
    assert isinstance(provider, ArxivProvider)


def test_resolve_provider_falls_back_to_default_when_config_is_empty():
    provider = resolve_provider({}, fetch=_fake_fetch(DEFAULT_LITERATURE_PROVIDER))
    assert provider.name == DEFAULT_LITERATURE_PROVIDER


def test_resolve_provider_rejects_unknown_provider_name():
    with pytest.raises(ProviderError):
        resolve_provider({"literature_provider": "not-a-real-provider"})


def test_swapping_the_configured_provider_is_a_config_change_not_a_code_change():
    for name in PROVIDER_REGISTRY:
        provider = resolve_provider({"literature_provider": name}, fetch=_fake_fetch(name))
        assert provider.name == name


def test_openalex_credential_comes_from_environment_never_from_config(monkeypatch):
    monkeypatch.setenv("KAGAMI_OPENALEX_EMAIL", "researcher@example.com")
    provider = OpenAlexProvider(fetch=_fake_fetch("openalex"))
    assert provider._email == "researcher@example.com"

    # config.yaml never carries the credential, even if someone tries to smuggle it in
    monkeypatch.delenv("KAGAMI_OPENALEX_EMAIL", raising=False)
    provider = resolve_provider(
        {"literature_provider": "openalex", "email": "should-be-ignored@example.com"},
        fetch=_fake_fetch("openalex"),
    )
    assert provider._email is None


def test_semantic_scholar_credential_comes_from_environment(monkeypatch):
    monkeypatch.setenv("KAGAMI_SEMANTIC_SCHOLAR_API_KEY", "secret-key")
    provider = SemanticScholarProvider(fetch=_fake_fetch("semantic-scholar"))
    assert provider._api_key == "secret-key"


def test_github_credential_comes_from_environment(monkeypatch):
    monkeypatch.setenv("KAGAMI_GITHUB_TOKEN", "ghp_secret")
    provider = GitHubProvider(fetch=_fake_fetch("github"))
    assert provider._token == "ghp_secret"


@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES)
def test_multi_word_queries_are_url_encoded_not_left_as_raw_spaces(adapter_cls):
    """Bug found in the first live smoke test: an un-encoded space in the
    query string is an invalid URL (`http.client.InvalidURL`), so every
    multi-word search crashed before a single request went out."""
    captured = {}

    def capturing_fetch(url: str) -> dict:
        captured["url"] = url
        return FIXTURES[adapter_cls.name]["search"]

    provider = adapter_cls(fetch=capturing_fetch)
    provider.search("in-context learning transformers")

    assert " " not in captured["url"]
    assert "in-context learning transformers" in urllib.parse.unquote_plus(captured["url"])


ARXIV_ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2101.00001v2</id>
    <title>  A Paper
      With A Wrapped Title  </title>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2202.03334v1</id>
    <title>Another Paper</title>
  </entry>
</feed>"""


def test_parse_arxiv_feed_strips_version_suffix_and_normalizes_whitespace():
    """Bug found in the first live smoke test: arXiv's real API returns an
    Atom/XML feed, not JSON, so `json.loads` on the raw response crashed
    every arXiv search and metadata lookup before a single result was ever
    returned to the Cartographer/Scout."""
    parsed = _parse_arxiv_feed(ARXIV_ATOM_SAMPLE)
    assert parsed == {
        "entries": [
            {"arxiv_id": "2101.00001", "title": "A Paper With A Wrapped Title"},
            {"arxiv_id": "2202.03334", "title": "Another Paper"},
        ]
    }


def test_parse_arxiv_feed_with_no_entries_returns_an_empty_list():
    empty_feed = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert _parse_arxiv_feed(empty_feed) == {"entries": []}


def test_arxiv_paper_metadata_extracts_the_first_entry_from_the_feed_shaped_response():
    provider = ArxivProvider(fetch=lambda url: {"entries": [{"arxiv_id": "2101.00001", "title": "Paper C"}]})
    assert provider.paper_metadata("2101.00001") == {
        "canonical_key": "2101.00001",
        "title": "Paper C",
        "source": "arxiv",
    }


def test_arxiv_paper_metadata_raises_provider_error_when_the_id_is_not_found():
    provider = ArxivProvider(fetch=lambda url: {"entries": []})
    with pytest.raises(ProviderError):
        provider.paper_metadata("9999.99999")
