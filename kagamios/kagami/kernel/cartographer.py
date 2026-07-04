from pathlib import Path
from typing import Callable

from kagami.registry import load_registry
from kagami.store.artifact import create_artifact

DEFAULT_CUT_BASES = ("method_class", "source")


class CartographerError(Exception):
    pass


def _cluster_by(papers: list[dict], key_fn: Callable[[dict], str]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {}
    for paper in papers:
        key = key_fn(paper) or "unclassified"
        clusters.setdefault(key, []).append(paper["id"])
    return clusters


def draft_clusterings(papers: list[dict]) -> dict:
    """FR-26: a clustering pass drafts at least two structurally different
    ways of partitioning the field — deterministic (no model call), per the
    dispatch table's classical-ML/deterministic tier for candidate
    partitions.
    """
    cut_a = {"basis": "method_class", "clusters": _cluster_by(papers, lambda p: p.get("method_class"))}
    cut_b = {"basis": "source", "clusters": _cluster_by(papers, lambda p: p.get("source"))}
    return {"cuts": [cut_a, cut_b]}


def _partition_signature(cut: dict) -> frozenset:
    return frozenset(frozenset(ids) for ids in cut["clusters"].values())


def cuts_are_structurally_different(cut_a: dict, cut_b: dict) -> bool:
    return _partition_signature(cut_a) != _partition_signature(cut_b)


def validate_field_map_draft(cuts: list[dict]) -> None:
    """FR-26: a draft with only one distinguishable clustering fails
    validation — whether that's literally one cut, or two cuts that happen
    to produce the identical grouping of papers under different labels."""
    if len(cuts) < 2:
        raise CartographerError(
            f"Field Map draft has {len(cuts)} proposed clustering(s); at least 2 structurally "
            "different partitionings are required (FR-26)"
        )
    if not cuts_are_structurally_different(cuts[0], cuts[1]):
        raise CartographerError(
            "the two proposed clusterings partition the papers identically — not a genuine "
            "structural alternative (FR-26)"
        )


def compute_recency_profile(cluster_papers: list[dict]) -> str:
    """PRD §7.1: recorded at minimal-profile depth for MVP even though the
    field itself is schema-tagged profile:full — a shallow, deterministic
    descriptor, not the eventual full recency analysis."""
    sources = sorted({p.get("source") or "unknown" for p in cluster_papers})
    return (
        f"{len(cluster_papers)} paper(s) in cluster; sources: {', '.join(sources)} "
        "(minimal-profile depth — full recency analysis deferred)"
    )


def create_field_map_clusters(
    run_dir: Path,
    chosen_cut: dict,
    all_cuts: list[dict],
    papers_by_id: dict,
    registry=None,
) -> dict:
    """FR-26: instantiate the researcher's chosen cut as Field Map artifacts,
    one per cluster, each cross-referencing the rejected alternative(s) and
    carrying its own minimal-profile recency profile.
    """
    validate_field_map_draft(all_cuts)
    registry = registry or load_registry()

    other_bases = [cut["basis"] for cut in all_cuts if cut is not chosen_cut]

    created = []
    for cluster_name, paper_ids in chosen_cut["clusters"].items():
        cluster_papers = [papers_by_id[pid] for pid in paper_ids if pid in papers_by_id]
        result = create_artifact(
            run_dir,
            "field-map",
            {
                "depends_on": [],
                "elicited_from": [],
                "decided_by": "ai-drafted/human-reviewed",
                "summary": "",
                "recency_profile": compute_recency_profile(cluster_papers),
                "alternative_cut": ",".join(other_bases),
            },
            sections={"cluster_name": cluster_name},
            registry=registry,
        )
        created.append(result["id"])

    return {"ok": True, "field_map_ids": created}
