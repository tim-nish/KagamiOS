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
        "metadata": {"doi": "10.1/a", "title": "Paper A"},
        "citations": {"results": [{"id": "https://openalex.org/W2"}]},
    },
    "semantic-scholar": {
        "search": {"data": [{"paperId": "ss-1", "title": "Paper B"}]},
        "metadata": {"paperId": "ss-1", "title": "Paper B"},
        "citations": {"data": [{"paperId": "ss-2"}]},
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
    calls = {"search": 0, "metadata": 0, "citations": 0}

    def fetch(url: str) -> dict:
        if "search" in url or "query=" in url:
            calls["search"] += 1
            return FIXTURES[name]["search"]
        if "citations" in url:
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


def test_resolve_provider_defaults_to_config_value_no_call_site_hardcodes_it():
    provider = resolve_provider({"literature_provider": "arxiv"}, fetch=_fake_fetch("arxiv"))
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
