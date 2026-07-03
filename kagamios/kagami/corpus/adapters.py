import json
import os
import urllib.request
from typing import Callable

from kagami.corpus.provider import LiteratureProvider, ProviderError

Fetch = Callable[[str], dict]


def _default_fetch(url: str) -> dict:
    with urllib.request.urlopen(url) as response:  # pragma: no cover - real network path
        return json.loads(response.read())


class OpenAlexProvider(LiteratureProvider):
    """Peer adapter (AD-7). Credential: KAGAMI_OPENALEX_EMAIL (polite pool), optional."""

    name = "openalex"

    def __init__(self, fetch: Fetch = _default_fetch):
        self._fetch = fetch
        self._email = os.environ.get("KAGAMI_OPENALEX_EMAIL")

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch(f"https://api.openalex.org/works?search={query}")
        return [self._to_result(r) for r in data.get("results", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(self._fetch(f"https://api.openalex.org/works/{canonical_key}"))

    def citation_graph(self, canonical_key: str) -> dict:
        data = self._fetch(f"https://api.openalex.org/works/{canonical_key}/citations")
        return {"canonical_key": canonical_key, "cited_by": [r.get("id") for r in data.get("results", [])]}

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("doi") or raw.get("id"),
            "title": raw.get("title"),
            "source": self.name,
        }


class SemanticScholarProvider(LiteratureProvider):
    """Peer adapter (AD-7). Credential: KAGAMI_SEMANTIC_SCHOLAR_API_KEY, optional."""

    name = "semantic-scholar"

    def __init__(self, fetch: Fetch = _default_fetch):
        self._fetch = fetch
        self._api_key = os.environ.get("KAGAMI_SEMANTIC_SCHOLAR_API_KEY")

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch(f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}")
        return [self._to_result(r) for r in data.get("data", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(self._fetch(f"https://api.semanticscholar.org/graph/v1/paper/{canonical_key}"))

    def citation_graph(self, canonical_key: str) -> dict:
        data = self._fetch(f"https://api.semanticscholar.org/graph/v1/paper/{canonical_key}/citations")
        return {
            "canonical_key": canonical_key,
            "cited_by": [c.get("paperId") for c in data.get("data", [])],
        }

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("paperId") or raw.get("externalIds", {}).get("DOI"),
            "title": raw.get("title"),
            "source": self.name,
        }


class ArxivProvider(LiteratureProvider):
    """Complementary-source adapter (AD-7): preprints. No credential required."""

    name = "arxiv"

    def __init__(self, fetch: Fetch = _default_fetch):
        self._fetch = fetch

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch(f"http://export.arxiv.org/api/query?search_query={query}")
        return [self._to_result(r) for r in data.get("entries", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(self._fetch(f"http://export.arxiv.org/api/query?id_list={canonical_key}"))

    def citation_graph(self, canonical_key: str) -> dict:
        return {"canonical_key": canonical_key, "cited_by": []}  # arXiv has no citation graph API

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("arxiv_id"),
            "title": raw.get("title"),
            "source": self.name,
        }


class GitHubProvider(LiteratureProvider):
    """Complementary-source adapter (AD-7): code repositories. Credential:
    KAGAMI_GITHUB_TOKEN, optional (raises rate limits when present)."""

    name = "github"

    def __init__(self, fetch: Fetch = _default_fetch):
        self._fetch = fetch
        self._token = os.environ.get("KAGAMI_GITHUB_TOKEN")

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch(f"https://api.github.com/search/repositories?q={query}")
        return [self._to_result(r) for r in data.get("items", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(self._fetch(f"https://api.github.com/repos/{canonical_key}"))

    def citation_graph(self, canonical_key: str) -> dict:
        return {"canonical_key": canonical_key, "cited_by": []}  # repos aren't cited, they're forked/starred

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("full_name"),
            "title": raw.get("full_name"),
            "source": self.name,
        }


PROVIDER_REGISTRY = {
    "openalex": OpenAlexProvider,
    "semantic-scholar": SemanticScholarProvider,
    "arxiv": ArxivProvider,
    "github": GitHubProvider,
}

DEFAULT_LITERATURE_PROVIDER = "openalex"


def resolve_provider(config: dict | None = None, fetch: Fetch | None = None) -> LiteratureProvider:
    """AD-7: the default provider comes from config, never from a call site.

    `config` is the parsed `config.yaml` (or an empty dict); provider
    credentials are read by each adapter directly from environment
    variables, never passed through `config`.
    """
    config = config or {}
    provider_name = config.get("literature_provider", DEFAULT_LITERATURE_PROVIDER)
    try:
        provider_cls = PROVIDER_REGISTRY[provider_name]
    except KeyError:
        raise ProviderError(
            f"unknown literature provider '{provider_name}'; must be one of {sorted(PROVIDER_REGISTRY)}"
        ) from None

    kwargs = {}
    if fetch is not None:
        kwargs["fetch"] = fetch
    return provider_cls(**kwargs)
