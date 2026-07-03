import pytest

from kagami.corpus.adapters import (
    PROVIDER_REGISTRY,
    ArxivProvider,
    DEFAULT_LITERATURE_PROVIDER,
    GitHubProvider,
    OpenAlexProvider,
    SemanticScholarProvider,
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
        "metadata": {"arxiv_id": "2101.00001", "title": "Paper C"},
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
