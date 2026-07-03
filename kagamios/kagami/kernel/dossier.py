from pathlib import Path

from kagami.store.artifact import read_current, update_frontmatter_field


class DossierError(Exception):
    pass


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
