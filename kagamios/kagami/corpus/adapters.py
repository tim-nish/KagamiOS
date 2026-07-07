import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable

from kagami.corpus.backoff import DEFAULT_BASE_DELAY_SECONDS, DEFAULT_MAX_RETRIES, with_backoff
from kagami.corpus.provider import LiteratureProvider, ProviderError

Fetch = Callable[[str], dict]

_ARXIV_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_ARXIV_VERSION_SUFFIX = re.compile(r"v\d+$")


def _default_fetch(url: str) -> dict:
    with urllib.request.urlopen(url) as response:  # pragma: no cover - real network path
        return json.loads(response.read())


def _parse_arxiv_feed(raw_xml: bytes | str) -> dict:
    """The real arXiv API returns an Atom/XML feed, not JSON — every other
    adapter's `_fetch` returns a dict straight from `json.loads`, so this
    normalizes arXiv's response into the same `{"entries": [...]}` shape
    `ArxivProvider` already expects, keeping the shared `Fetch` contract intact."""
    root = ET.fromstring(raw_xml)
    entries = []
    for entry in root.findall("atom:entry", _ARXIV_ATOM_NS):
        id_el = entry.find("atom:id", _ARXIV_ATOM_NS)
        title_el = entry.find("atom:title", _ARXIV_ATOM_NS)
        raw_id = (id_el.text or "").strip() if id_el is not None else ""
        arxiv_id = _ARXIV_VERSION_SUFFIX.sub("", raw_id.rsplit("/", 1)[-1])
        title = " ".join((title_el.text or "").split()) if title_el is not None else ""
        entries.append({"arxiv_id": arxiv_id, "title": title})
    return {"entries": entries}


def _arxiv_default_fetch(url: str) -> dict:
    with urllib.request.urlopen(url) as response:  # pragma: no cover - real network path
        return _parse_arxiv_feed(response.read())


def _reconstruct_openalex_abstract(inverted_index: dict | None) -> str:
    """FR-54/change-signal-paper-content-2026-07-06.md: OpenAlex never
    returns a plain abstract string — `abstract_inverted_index` maps each
    word to its position(s) in the original text (to dodge publisher
    copyright on full-text redistribution). Reassembling it is zero extra
    retrieval: the index already rides on the same search/works response
    `_to_result` reads everything else from."""
    if not inverted_index:
        return ""
    positioned = [(pos, word) for word, positions in inverted_index.items() for pos in positions]
    positioned.sort()
    return " ".join(word for _, word in positioned)


class _BackoffMixin:
    """NFR7: every adapter's `_fetch` call goes through this so a
    documented rate limit is retried with backoff, never surfaced as a
    raw crash. `max_retries`/`base_delay_seconds`/`sleep_fn` are
    constructor-injectable so tests exercise real retry counts without
    real wall-clock sleeps."""

    def _fetch_with_backoff(self, url: str) -> dict:
        return with_backoff(
            lambda: self._fetch(url),
            self.name,
            max_retries=self._max_retries,
            base_delay_seconds=self._base_delay_seconds,
            sleep_fn=self._sleep_fn,
        )


class OpenAlexProvider(_BackoffMixin, LiteratureProvider):
    """Peer adapter (AD-7). Credential: KAGAMI_OPENALEX_EMAIL (polite pool), optional."""

    name = "openalex"

    def __init__(
        self,
        fetch: Fetch = _default_fetch,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._fetch = fetch
        self._email = os.environ.get("KAGAMI_OPENALEX_EMAIL")
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._sleep_fn = sleep_fn

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch_with_backoff(
            f"https://api.openalex.org/works?search={urllib.parse.quote_plus(query)}"
        )
        return [self._to_result(r) for r in data.get("results", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(self._fetch_with_backoff(f"https://api.openalex.org/works/{canonical_key}"))

    def citation_graph(self, canonical_key: str) -> dict:
        # FR-51/docs/dogfooding-review.md finding 1: `works/{id}/citations` is not a
        # real OpenAlex sub-resource (404 in the field). Incoming citations are the
        # list endpoint filtered by `cites`; outgoing references are the
        # `referenced_works` array already present on the work object.
        citing = self._fetch_with_backoff(f"https://api.openalex.org/works?filter=cites:{canonical_key}")
        work = self._fetch_with_backoff(f"https://api.openalex.org/works/{canonical_key}")
        return {
            "canonical_key": canonical_key,
            "cited_by": [r.get("id") for r in citing.get("results", [])],
            "references": work.get("referenced_works", []),
        }

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("doi") or raw.get("id"),
            "title": raw.get("title"),
            "source": self.name,
            "abstract": _reconstruct_openalex_abstract(raw.get("abstract_inverted_index")),
        }


class SemanticScholarProvider(_BackoffMixin, LiteratureProvider):
    """Peer adapter (AD-7). Credential: KAGAMI_SEMANTIC_SCHOLAR_API_KEY, optional."""

    name = "semantic-scholar"

    def __init__(
        self,
        fetch: Fetch = _default_fetch,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._fetch = fetch
        self._api_key = os.environ.get("KAGAMI_SEMANTIC_SCHOLAR_API_KEY")
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._sleep_fn = sleep_fn

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch_with_backoff(
            f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote_plus(query)}"
        )
        return [self._to_result(r) for r in data.get("data", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(
            self._fetch_with_backoff(f"https://api.semanticscholar.org/graph/v1/paper/{canonical_key}")
        )

    def citation_graph(self, canonical_key: str) -> dict:
        # FR-51: the endpoints are correct, but each `data` item nests the actual
        # paper under `citingPaper`/`citedPaper` — the flat `paperId` this used to
        # read never existed on the real response, so every neighbor silently
        # resolved to `None`.
        citing = self._fetch_with_backoff(
            f"https://api.semanticscholar.org/graph/v1/paper/{canonical_key}/citations"
        )
        referenced = self._fetch_with_backoff(
            f"https://api.semanticscholar.org/graph/v1/paper/{canonical_key}/references"
        )
        return {
            "canonical_key": canonical_key,
            "cited_by": [c.get("citingPaper", {}).get("paperId") for c in citing.get("data", [])],
            "references": [c.get("citedPaper", {}).get("paperId") for c in referenced.get("data", [])],
        }

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("paperId") or raw.get("externalIds", {}).get("DOI"),
            "title": raw.get("title"),
            "source": self.name,
            "abstract": raw.get("abstract") or "",
        }


class ArxivProvider(_BackoffMixin, LiteratureProvider):
    """Complementary-source adapter (AD-7): preprints. No credential required."""

    name = "arxiv"

    def __init__(
        self,
        fetch: Fetch = _arxiv_default_fetch,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._fetch = fetch
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._sleep_fn = sleep_fn

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch_with_backoff(
            f"https://export.arxiv.org/api/query?search_query={urllib.parse.quote_plus(query)}"
        )
        return [self._to_result(r) for r in data.get("entries", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        data = self._fetch_with_backoff(
            f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote_plus(canonical_key)}"
        )
        entries = data.get("entries", [])
        if not entries:
            raise ProviderError(f"arxiv: no entry found for id '{canonical_key}'")
        return self._to_result(entries[0])

    def citation_graph(self, canonical_key: str) -> dict:
        # FR-51: arXiv has no citation-graph API in either direction — a
        # real, exposed provider bias, not a gap to fabricate around.
        return {"canonical_key": canonical_key, "cited_by": [], "references": []}

    def _to_result(self, raw: dict) -> dict:
        return {
            "canonical_key": raw.get("arxiv_id"),
            "title": raw.get("title"),
            "source": self.name,
        }


class GitHubProvider(_BackoffMixin, LiteratureProvider):
    """Complementary-source adapter (AD-7): code repositories. Credential:
    KAGAMI_GITHUB_TOKEN, optional (raises rate limits when present)."""

    name = "github"

    def __init__(
        self,
        fetch: Fetch = _default_fetch,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._fetch = fetch
        self._token = os.environ.get("KAGAMI_GITHUB_TOKEN")
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._sleep_fn = sleep_fn

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._fetch_with_backoff(
            f"https://api.github.com/search/repositories?q={urllib.parse.quote_plus(query)}"
        )
        return [self._to_result(r) for r in data.get("items", [])[:limit]]

    def paper_metadata(self, canonical_key: str) -> dict:
        return self._to_result(self._fetch_with_backoff(f"https://api.github.com/repos/{canonical_key}"))

    def citation_graph(self, canonical_key: str) -> dict:
        # FR-51: repos aren't cited, they're forked/starred — no citation
        # graph in either direction, a real provider bias, not a gap.
        return {"canonical_key": canonical_key, "cited_by": [], "references": []}

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


def resolve_provider(
    config: dict | None = None,
    fetch: Fetch | None = None,
    provider_override: str | None = None,
) -> LiteratureProvider:
    """AD-7: the default provider comes from config, never hardcoded at a
    call site — but a caller may still name one explicitly via
    `provider_override` (FR-15/FR-25/AD-26 story 9.3: the CLI's
    `--provider` flag), which wins over `config.yaml`'s default so a
    single broken/rate-limited provider doesn't stall a whole search.

    `config` is the parsed `config.yaml` (or an empty dict); provider
    credentials are read by each adapter directly from environment
    variables, never passed through `config`.
    """
    config = config or {}
    provider_name = provider_override or config.get("literature_provider", DEFAULT_LITERATURE_PROVIDER)
    try:
        provider_cls = PROVIDER_REGISTRY[provider_name]
    except KeyError:
        raise ProviderError(
            f"unknown literature provider '{provider_name}'; must be one of {sorted(PROVIDER_REGISTRY)}"
        ) from None

    kwargs = {}
    if fetch is not None:
        kwargs["fetch"] = fetch
    # NFR7: backoff profile is researcher-configurable the same way
    # refusal_ceiling and token_budget_soft_limit are — only if the
    # researcher sets it; the adapter's own defaults apply otherwise.
    if "provider_max_retries" in config:
        kwargs["max_retries"] = config["provider_max_retries"]
    if "provider_base_delay_seconds" in config:
        kwargs["base_delay_seconds"] = config["provider_base_delay_seconds"]
    return provider_cls(**kwargs)
