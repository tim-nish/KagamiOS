import json

import pytest

from kagami.kernel.synthesize import (
    SynthesizeError,
    create_landscape_synthesis,
    validate_landscape_synthesis,
    validate_solved_open_table,
    validate_source_dossiers_accepted,
    synthesize_write,
)
from kagami.store.artifact import accept_artifact, create_artifact, read_current, review_artifact
from kagami.store.run import open_run


def test_create_landscape_synthesis_is_reachable_without_a_direct_create_artifact_import(tmp_path):
    open_run(run_id="run-ls-create", output_root=tmp_path / "_out")
    run_dir = tmp_path / "_out" / "runs" / "run-ls-create"

    result = create_landscape_synthesis(run_dir)
    assert result["ok"] is True

    frontmatter, _ = read_current(run_dir, "landscape-synthesis", result["id"])
    assert frontmatter["type"] == "landscape-synthesis"
    assert frontmatter["status"] == "draft"


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _accept(run_dir, type_slug, art_id):
    review_artifact(run_dir, type_slug, art_id)
    accept_artifact(run_dir, type_slug, art_id, "\n".join(f"line {i}" for i in range(6)))


def _create_accepted_dossier(run_dir):
    dossier = create_artifact(
        run_dir, "cluster-dossier", _base_fields(), sections={"evolution": "founding problem"}
    )
    _accept(run_dir, "cluster-dossier", dossier["id"])
    return dossier["id"]


def _create_landscape_synthesis(run_dir):
    return create_artifact(run_dir, "landscape-synthesis", _base_fields(), sections={})


def _solved_row(claim="approach X solves problem Y"):
    return {"claim": claim, "status": "solved"}


def _open_row(claim="nobody has tried Z", evidence="searched venues A/B 2019-2025, zero hits"):
    return {"claim": claim, "status": "open", "absence_evidence": evidence}


def test_validate_solved_open_table_accepts_solved_and_well_evidenced_open_rows():
    validate_solved_open_table([_solved_row(), _open_row()])


def test_validate_solved_open_table_rejects_open_claim_without_absence_evidence():
    with pytest.raises(SynthesizeError):
        validate_solved_open_table([{"claim": "nobody has tried Z", "status": "open"}])


def test_validate_solved_open_table_rejects_open_claim_with_blank_absence_evidence():
    with pytest.raises(SynthesizeError):
        validate_solved_open_table([{"claim": "nobody has tried Z", "status": "open", "absence_evidence": "   "}])


def test_validate_solved_open_table_rejects_non_string_absence_evidence():
    with pytest.raises(SynthesizeError):
        validate_solved_open_table([{"claim": "x", "status": "open", "absence_evidence": ["not", "a", "string"]}])


def test_validate_solved_open_table_rejects_unknown_status():
    with pytest.raises(SynthesizeError):
        validate_solved_open_table([{"claim": "x", "status": "maybe"}])


def test_validate_solved_open_table_rejects_missing_claim():
    with pytest.raises(SynthesizeError):
        validate_solved_open_table([{"status": "solved"}])


def test_validate_source_dossiers_accepted_refuses_a_draft_dossier(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "founding problem"}
    )
    with pytest.raises(SynthesizeError):
        validate_source_dossiers_accepted(tmp_path, [dossier["id"]])


def test_validate_source_dossiers_accepted_passes_for_accepted_dossiers(tmp_path):
    dossier_id = _create_accepted_dossier(tmp_path)
    validate_source_dossiers_accepted(tmp_path, [dossier_id])


def test_synthesize_write_drafts_solved_open_table_from_accepted_dossiers(tmp_path):
    dossier_id = _create_accepted_dossier(tmp_path)
    synth = _create_landscape_synthesis(tmp_path)

    rows = [_solved_row(), _open_row()]
    result = synthesize_write(tmp_path, synth["id"], "solved_open_table", rows, [dossier_id])
    assert result["ok"] is True

    frontmatter, _ = read_current(tmp_path, "landscape-synthesis", synth["id"])
    assert frontmatter["solved_open_table"] == rows


def test_synthesize_write_refuses_when_a_source_dossier_is_not_accepted(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "founding problem"}
    )
    synth = _create_landscape_synthesis(tmp_path)

    with pytest.raises(SynthesizeError):
        synthesize_write(tmp_path, synth["id"], "solved_open_table", [_solved_row()], [dossier["id"]])

    frontmatter, _ = read_current(tmp_path, "landscape-synthesis", synth["id"])
    assert frontmatter.get("solved_open_table") is None


def test_synthesize_write_refuses_an_open_claim_without_absence_evidence(tmp_path):
    dossier_id = _create_accepted_dossier(tmp_path)
    synth = _create_landscape_synthesis(tmp_path)

    bad_row = {"claim": "nobody has tried Z", "status": "open"}
    with pytest.raises(SynthesizeError):
        synthesize_write(tmp_path, synth["id"], "solved_open_table", [bad_row], [dossier_id])

    frontmatter, _ = read_current(tmp_path, "landscape-synthesis", synth["id"])
    assert frontmatter.get("solved_open_table") is None


def test_synthesize_write_refuses_writing_outside_the_solved_open_table_and_logs_it(tmp_path):
    dossier_id = _create_accepted_dossier(tmp_path)
    synth = _create_landscape_synthesis(tmp_path)

    with pytest.raises(SynthesizeError):
        synthesize_write(
            tmp_path, synth["id"], "competing_approaches_matrix", [{"x": "y"}], [dossier_id]
        )

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    violations = [e for e in events if e.get("kind") == "generation_window_violation"]
    assert len(violations) == 1
    assert violations[0]["family"] == "gate_event"
    assert violations[0]["role"] == "synthesize"

    frontmatter, _ = read_current(tmp_path, "landscape-synthesis", synth["id"])
    assert frontmatter.get("competing_approaches_matrix") is None


def test_validate_landscape_synthesis_reports_a_hand_edited_open_row_missing_evidence(tmp_path):
    dossier_id = _create_accepted_dossier(tmp_path)
    synth = _create_landscape_synthesis(tmp_path)
    synthesize_write(tmp_path, synth["id"], "solved_open_table", [_solved_row()], [dossier_id])

    from kagami.store.artifact import update_frontmatter_field

    update_frontmatter_field(
        tmp_path,
        "landscape-synthesis",
        synth["id"],
        "solved_open_table",
        lambda rows: rows + [{"claim": "hand-added claim", "status": "open"}],
        event_family="human_edit",
        event_payload={"kind": "table_hand_edited", "artifact_id": synth["id"]},
    )

    result = validate_landscape_synthesis(tmp_path, synth["id"])
    assert result["ok"] is False
    assert any("hand-added claim" in v for v in result["violations"])


def test_validate_landscape_synthesis_passes_for_a_well_formed_table(tmp_path):
    dossier_id = _create_accepted_dossier(tmp_path)
    synth = _create_landscape_synthesis(tmp_path)
    synthesize_write(tmp_path, synth["id"], "solved_open_table", [_solved_row(), _open_row()], [dossier_id])

    result = validate_landscape_synthesis(tmp_path, synth["id"])
    assert result == {"ok": True, "violations": []}


def test_landscape_synthesis_summary_is_regenerated_at_acceptance(tmp_path):
    """FR-33: the summary is written by `accept_artifact` alone, and only at
    acceptance — the same generic contract every artifact type gets."""
    dossier_id = _create_accepted_dossier(tmp_path)
    synth = _create_landscape_synthesis(tmp_path)
    synthesize_write(tmp_path, synth["id"], "solved_open_table", [_solved_row(), _open_row()], [dossier_id])

    frontmatter, _ = read_current(tmp_path, "landscape-synthesis", synth["id"])
    assert frontmatter["summary"] == ""

    review_artifact(tmp_path, "landscape-synthesis", synth["id"])
    new_summary = "\n".join(f"landscape line {i}" for i in range(6))
    accept_artifact(tmp_path, "landscape-synthesis", synth["id"], new_summary)

    frontmatter, _ = read_current(tmp_path, "landscape-synthesis", synth["id"])
    assert frontmatter["summary"] == new_summary
    assert frontmatter["status"] == "accepted"
