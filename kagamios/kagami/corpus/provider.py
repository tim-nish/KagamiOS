from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


class LiteratureProvider(ABC):
    """AD-7: one port — search, paper metadata, citation graph.

    No call site should ever name a concrete adapter; callers receive an
    instance via `kagami.corpus.adapters.resolve_provider`, which reads the
    default from config, never from code.
    """

    name: str

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Returns a list of raw result dicts, each carrying at least a
        `canonical_key` (the bibliographic identity used to mint a
        content-derived paper id, AD-18) and a `title`."""

    @abstractmethod
    def paper_metadata(self, canonical_key: str) -> dict:
        ...

    @abstractmethod
    def citation_graph(self, canonical_key: str) -> dict:
        """FR-51: returns `{"canonical_key", "cited_by": [...], "references": [...]}`
        — both keys always present, even when empty. `cited_by` is papers
        that cite this one, `references` is papers this one cites. An
        adapter with no real source for one or both directions (arXiv,
        GitHub, as of this writing) legitimately returns an empty list —
        an exposed provider bias, not a gap to paper over."""
