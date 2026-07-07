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
        {"paper_id": "ppr-1", "human_read": False},
        {"paper_id": "ppr-2", "human_read": False},
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
            representative_papers=[{"paper_id": pid, "human_read": False, "reaction": ""} for pid in paper_ids]
        ),
        sections={"evolution": "founding problem"},
    )


def test_mark_representative_paper_read_sets_flag_and_reaction(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1", "ppr-2"])

    result = mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "surprisingly foundational", "human")
    assert result["ok"] is True

    from kagami.store.artifact import read_current

    frontmatter, _ = read_current(tmp_path, "cluster-dossier", dossier["id"])
    entry = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-1")
    assert entry["human_read"] is True
    assert entry["reaction"] == "surprisingly foundational"

    untouched = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-2")
    assert untouched["human_read"] is False


def test_mark_representative_paper_read_logs_a_human_edit_event(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "reaction", "human")

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    marks = [e for e in events if e.get("kind") == "representative_paper_marked_read"]
    assert len(marks) == 1
    assert marks[0]["family"] == "human_edit"
    assert marks[0]["paper_id"] == "ppr-1"


def test_mark_unknown_paper_id_is_refused(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-does-not-exist", "reaction", "human")


@pytest.mark.parametrize("actor", ["historian", "scout", "worker", "ai", "", "Human"])
def test_mark_representative_paper_read_refuses_a_non_human_actor(tmp_path, actor):
    """FR-58/AD-30: `human_read` means what its name says only if an
    AI-declared actor is refused, not merely defaulted around — including
    an AI role name, a blank actor, and a near-miss casing of the human
    sentinel itself."""
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "reaction", actor)

    from kagami.store.artifact import read_current

    frontmatter, _ = read_current(tmp_path, "cluster-dossier", dossier["id"])
    entry = next(p for p in frontmatter["representative_papers"] if p["paper_id"] == "ppr-1")
    assert entry["human_read"] is False


def test_mark_representative_paper_read_would_have_caught_run_1s_ai_declared_human_read(tmp_path):
    """FR-58: run 1's actual `human_read` writes went through under an
    AI-declared role with no actor check at all — this is the specific
    shape of that violation, replayed against the new enforcement."""
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    with pytest.raises(DossierError):
        mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "AI-drafted reaction", "historian")


def test_mark_representative_paper_read_records_the_actor_on_the_event(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "reaction", HUMAN_ACTOR)

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    marks = [e for e in events if e.get("kind") == "representative_paper_marked_read"]
    assert marks[0]["actor"] == HUMAN_ACTOR


def test_validate_deepen_exit_fails_when_a_representative_paper_is_unread(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1", "ppr-2"])
    review_artifact(tmp_path, "cluster-dossier", dossier["id"])
    accept_artifact(tmp_path, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "reaction", "human")

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result["ok"] is False
    assert any("ppr-2" in v for v in result["violations"])


def test_validate_deepen_exit_passes_once_every_representative_is_read(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1", "ppr-2"])
    review_artifact(tmp_path, "cluster-dossier", dossier["id"])
    accept_artifact(tmp_path, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "reaction 1", "human")
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-2", "reaction 2", "human")

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result == {"ok": True, "violations": []}


def test_validate_deepen_exit_fails_for_an_unaccepted_dossier(tmp_path):
    dossier = _create_dossier_with_representatives(tmp_path, ["ppr-1"])
    mark_representative_paper_read(tmp_path, dossier["id"], "ppr-1", "reaction", "human")

    result = validate_deepen_exit(tmp_path, dossier["id"])
    assert result["ok"] is False
