from pathlib import Path

from kagami.registry import load_registry
from kagami.store.artifact import create_artifact, read_current, update_frontmatter_field


class DossierError(Exception):
    pass


def create_cluster_dossier(
    run_dir: Path, field_map_id: str, representative_paper_ids: list[str], registry=None
) -> dict:
    """Story 7.5: discovered missing while driving the golden toy run —
    Historian's Evolution write and `mark_representative_paper_read` both
    only ever touch an *already-existing* Cluster Dossier; nothing in
    Epic 3 exposed how that artifact comes to exist through the chokepoint.
    Minimal CLI-reachable creation path: an empty `evolution` section for
    Historian to write, and `representative_papers` seeded unread so
    Deepen's exit criterion (every representative paper `human_read`) has
    something concrete to be checked against.
    """
    registry = registry or load_registry()
    return create_artifact(
        run_dir,
        "cluster-dossier",
        {
            "depends_on": [f"{field_map_id}@v1"],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "representative_papers": [
                {"paper_id": pid, "human_read": False} for pid in representative_paper_ids
            ],
        },
        sections={"evolution": ""},
        registry=registry,
    )


def mark_representative_paper_read(run_dir: Path, art_id: str, paper_id: str, reaction: str) -> dict:
    """FR-28: the researcher's own reading — not the AI's draft — closes out
    a cluster. Marks a representative paper `human_read` with a one-line
    reaction."""

    def _update(papers):
        papers = papers or []
        entry = next((p for p in papers if p.get("paper_id") == paper_id), None)
        if entry is None:
            raise DossierError(f"'{paper_id}' is not a representative paper on dossier {art_id}")
        entry["human_read"] = True
        entry["reaction"] = reaction
        return papers

    return update_frontmatter_field(
        run_dir,
        "cluster-dossier",
        art_id,
        "representative_papers",
        _update,
        event_family="human_edit",
        event_payload={
            "kind": "representative_paper_marked_read",
            "artifact_id": art_id,
            "paper_id": paper_id,
        },
    )


def validate_deepen_exit(run_dir: Path, art_id: str) -> dict:
    """FR-28: a dossier missing a `human_read` flag on any representative
    paper has not met the Deepen exit criterion for that cluster."""
    frontmatter, _ = read_current(run_dir, "cluster-dossier", art_id)
    violations = []

    if frontmatter.get("status") != "accepted":
        violations.append(f"dossier {art_id} is not yet accepted")

    for paper in frontmatter.get("representative_papers") or []:
        if not paper.get("human_read"):
            violations.append(f"representative paper '{paper.get('paper_id')}' missing human_read")

    return {"ok": len(violations) == 0, "violations": violations}
