from pathlib import Path

from kagami.registry import load_registry
from kagami.store.artifact import create_artifact, read_current, update_frontmatter_field

# FR-58/AD-30: the sole actor value `mark_representative_paper_read` ever
# accepts — `human_read` means what its name says only if no AI-declared
# actor can set it, the same self-declared-but-enforced trust model AD-4
# uses for `role`, just checked against a single allowed value here.
HUMAN_ACTOR = "human"


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
    Historian to write, and `representative_papers` seeded unconfirmed so
    Deepen's exit criterion (FR-59: every representative paper carries a
    human-attributed rating + confidence confirmation) has something
    concrete to be checked against.
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
                {"paper_id": pid, "rating": None, "confidence": None, "note": "", "actor": None}
                for pid in representative_paper_ids
            ],
        },
        sections={"evolution": ""},
        registry=registry,
    )


def mark_representative_paper_read(
    run_dir: Path, art_id: str, paper_id: str, rating: str, confidence: str, actor: str, note: str = ""
) -> dict:
    """FR-28/FR-58/FR-59/AD-30: the researcher's own confirmation — not the
    AI's draft — closes out a cluster.

    FR-59 amendment: a binary `human_read` flag was too heavyweight a
    signal for early, unsettled exploration (the run-1 finding this story
    answers) — confirmation is now a lightweight `rating` + `confidence`,
    with an optional free-text `note`, replacing the old flag entirely.

    `actor` and both `rating`/`confidence` are mandatory and checked
    *before* any mutation: a call declaring anything other than
    `HUMAN_ACTOR`, or omitting rating/confidence, is refused at this
    chokepoint — the same enforcement class as AD-28's forbidden-fields
    check on paper cards.
    """
    if actor != HUMAN_ACTOR:
        raise DossierError(
            f"confirmation refused: actor '{actor}' is not the human researcher — only "
            f"'{HUMAN_ACTOR}' may confirm a representative paper (FR-58/FR-59/AD-30)"
        )
    if not rating or not confidence:
        raise DossierError(
            "a representative-paper confirmation requires both rating and confidence (FR-59)"
        )

    def _update(papers):
        papers = papers or []
        entry = next((p for p in papers if p.get("paper_id") == paper_id), None)
        if entry is None:
            raise DossierError(f"'{paper_id}' is not a representative paper on dossier {art_id}")
        entry["rating"] = rating
        entry["confidence"] = confidence
        entry["note"] = note or ""
        entry["actor"] = actor
        return papers

    return update_frontmatter_field(
        run_dir,
        "cluster-dossier",
        art_id,
        "representative_papers",
        _update,
        event_family="human_edit",
        event_payload={
            "kind": "representative_paper_confirmed",
            "artifact_id": art_id,
            "paper_id": paper_id,
            "rating": rating,
            "confidence": confidence,
            "actor": actor,
        },
    )


def validate_deepen_exit(run_dir: Path, art_id: str) -> dict:
    """FR-28/FR-59: a dossier missing a human-attributed rating +
    confidence confirmation on any representative paper has not met the
    Deepen exit criterion for that cluster — a `human_read` boolean alone
    no longer satisfies it.

    A confirmation record whose `actor` isn't `HUMAN_ACTOR` does not
    satisfy this gate either: FR-59 *composes* with Story 11.2's write-time
    enforcement (which already refuses a non-human actor before any
    mutation), it never trusts a record's mere presence as proof of who
    wrote it — a defense-in-depth re-check, not a duplicate of the same
    guarantee.
    """
    frontmatter, _ = read_current(run_dir, "cluster-dossier", art_id)
    violations = []

    if frontmatter.get("status") != "accepted":
        violations.append(f"dossier {art_id} is not yet accepted")

    for paper in frontmatter.get("representative_papers") or []:
        paper_id = paper.get("paper_id")
        if not paper.get("rating") or not paper.get("confidence"):
            violations.append(
                f"representative paper '{paper_id}' missing a rating/confidence confirmation"
            )
        elif paper.get("actor") != HUMAN_ACTOR:
            violations.append(
                f"representative paper '{paper_id}' confirmation is not human-attributed"
            )

    return {"ok": len(violations) == 0, "violations": violations}
