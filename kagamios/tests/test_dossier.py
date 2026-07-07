import json

import pytest

from kagami.kernel.dossier import (
    HUMAN_ACTOR,
    DossierError,
    create_cluster_dossier,
    mark_representative_paper_read,
    validate_deepen_exit,
)
from kagami.store.artifact import accept_artifact, create_artifact, read_current, review_artifact
from kagami.store.run import open_run


def test_create_cluster_dossier_is_reachable_without_a_direct_create_artifact_import(tmp_path):
    open_run(run_id="run-dossier-create", output_root=tmp_path / "_out")
    run_dir = tmp_path / "_out" / "runs" / "run-dossier-create"

    result = create_cluster_dossier(run_dir, "art-fieldmap1", ["ppr-1", "ppr-2"])
    assert result["ok"] is True

    frontmatter, sections = read_current(run_dir, "cluster-dossier", result["id"])
    assert frontmatter["depends_on"] == ["art-fieldmap1@v1"]
    assert frontmatter["representative_papers"] == [
        {"paper_id": "ppr-1", "rating": None, "confidence": None, "note": "", "actor": None},
        {"paper_id": "ppr-2", "rating": None, "confidence": None, "note": "", "actor": None},
    ]
    bodies = {s.title: s.body for s in sections}
    assert bodies["evolution"] == ""


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _create_dossier_with_representatives(run_dir, paper_ids):
    return create_artifact(
        run_dir,
        "cluster-dossier",
        _base_fields(
            representative_papers=[
                {"paper_id": pid, "rating": None, "confidence": None, "note": "", "actor": None}
                for pid in paper_ids
            ]
        ),
        sections={"evolution": "founding problem"},
    )


def test_mark_representative_paper_read_sets_rating_confidence_and_note(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1", "ppr-2"])

    result = mark_representative_paper_read(
        tmp_path, dossier["id"], "ppr-1", "strong", "high", "human", note="surprisingly foundational"
    )
    assert result["ok"] is True

    frontmatter, _ = read_current(tmp_path, "cluster-dossier", dossier["id"])
    entry = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-1")
    assert entry["rating"] == "strong"
    assert entry["confidence"] == "high"
    assert entry["note"] == "surprisingly foundational"
    assert entry["actor"] == "human"

    untouched = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-2")
    assert untouched["rating"] is None
    assert untouched["actor"] is None


def test_mark_representative_paper_read_note_is_optional(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", "human")

    frontmatter, _ = read_current(tmp_path, "cluster-dossier", dossier["id"])
    entry = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-1")
    assert entry["note"] == ""


@pytest.mark.parametrize("rating,confidence", [("", "high"), ("strong", ""), ("", "")])
def test_mark_representative_paper_read_requires_rating_and_confidence(tmp_path, rating, confidence):
    """FR-59: a confirmation missing either rating or confidence is
    refused — the gate can't check for something that was never required
    at write time."""
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", rating, confidence, "human")


def test_mark_representative_paper_read_logs_a_human_edit_event(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", "human")

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    marks = [e for e in events if e.get("kind") == "representative_paper_confirmed"]
    assert len(marks) == 1
    assert marks[0]["family"] == "human_edit"
    assert marks[0]["paper_id"] == "ppr-1"
    assert marks[0]["rating"] == "strong"
    assert marks[0]["confidence"] == "high"


def test_mark_unknown_paper_id_is_refused(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-does-not-exist", "strong", "high", "human")


@pytest.mark.parametrize("actor", ["historian", "scout", "worker", "ai", "", "Human"])
def test_mark_representative_paper_read_refuses_a_non_human_actor(tmp_path, actor):
    """FR-58/AD-30: a confirmation means what its actor field says only if
    an AI-declared actor is refused, not merely defaulted around —
    including an AI role name, a blank actor, and a near-miss casing of
    the human sentinel itself."""
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", actor)

    frontmatter, _ = read_current(tmp_path, "cluster-dossier", dossier["id"])
    entry = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-1")
    assert entry["rating"] is None
    assert entry["actor"] is None


def test_mark_representative_paper_read_would_have_caught_run_1s_ai_declared_human_read(tmp_path):
    """FR-58: run 1's actual `human_read` writes went through under an
    AI-declared role with no actor check at all — this is the specific
    shape of that violation, replayed against the new enforcement."""
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", "historian")


def test_mark_representative_paper_read_records_the_actor_on_the_event(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", HUMAN_ACTOR)

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    marks = [e for e in events if e.get("kind") == "representative_paper_confirmed"]
    assert marks[0]["actor"] == HUMAN_ACTOR


def test_validate_deepen_exit_fails_when_a_representative_paper_is_unconfirmed(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1", "ppr-2"])
    review_artifact(tmp_path, "cluster-dossier", dossier["id"])
    accept_artifact(tmp_path, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", "human")

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result["ok"] is False
    assert any("ppr-2" in v for v in result["violations"])


def test_validate_deepen_exit_passes_once_every_representative_is_confirmed(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1", "ppr-2"])
    review_artifact(tmp_path, "cluster-dossier", dossier["id"])
    accept_artifact(tmp_path, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", "human")
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-2", "weak", "low", "human")

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result == {"ok": True, "violations": []}


def test_validate_deepen_exit_fails_for_an_unaccepted_dossier(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "strong", "high", "human")

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result["ok"] is False


def test_validate_deepen_exit_does_not_trust_a_record_missing_actor_attribution(tmp_path):
    """FR-59 composes with Story 11.2's enforcement rather than bypassing
    it: a confirmation record with rating/confidence but no (or a
    non-human) actor — e.g. a pre-Story-11.2 dossier, or any other write
    path that reached the field directly — does not satisfy the gate."""
    dossier = create_artifact(
        tmp_path,
        "cluster-dossier",
        _base_fields(
            representative_papers=[
                {"paper_id": "ppr-1", "rating": "strong", "confidence": "high", "note": "", "actor": "historian"}
            ]
        ),
        sections={"evolution": "founding problem"},
    )
    review_artifact(tmp_path, "cluster-dossier", dossier["id"])
    accept_artifact(tmp_path, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result["ok"] is False
    assert any("not human-attributed" in v for v in result["violations"])
