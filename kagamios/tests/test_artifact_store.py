import json
from pathlib import Path

import pytest

from kagami.store.artifact import (
    ArtifactError,
    RejectedWriteError,
    accept_artifact,
    claim_section,
    create_artifact,
    mark_dependents_stale,
    missing_required_metadata_fields,
    pin_dependency,
    read_version,
    scan,
    validate_can_accept,
    attempt_ai_write,
)
from kagami.store.ids import mint_id


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "a short summary",
    }
    fields.update(overrides)
    return fields


def test_create_artifact_produces_v1_current_and_meta(tmp_path):
    result = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(),
        sections={"statement": "there is a gap"},
    )

    art_dir = tmp_path / "artifacts" / "gap-register" / result["id"]
    assert (art_dir / "v1.md").is_file()
    assert (art_dir / "current.md").is_file()
    assert (art_dir / "meta.yaml").is_file()
    assert (art_dir / "v1.md").read_text() == (art_dir / "current.md").read_text()


def test_scan_with_no_edit_is_a_noop(tmp_path):
    result = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})
    outcome = scan(tmp_path, "gap-register", result["id"])
    assert outcome == {"ok": True, "changed": False, "version": 1}


def test_scan_detects_human_edit_mints_new_version_and_flips_author(tmp_path):
    result = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})
    art_dir = tmp_path / "artifacts" / "gap-register" / result["id"]

    current_text = (art_dir / "current.md").read_text()
    edited_text = current_text.replace("x", "x, edited by the researcher")
    (art_dir / "current.md").write_text(edited_text)

    outcome = scan(tmp_path, "gap-register", result["id"])

    assert outcome["ok"] is True
    assert outcome["changed"] is True
    assert outcome["version"] == 2
    assert (art_dir / "v2.md").is_file()
    assert "edited by the researcher" in (art_dir / "v2.md").read_text()
    assert "edited by the researcher" not in (art_dir / "v1.md").read_text()

    meta = _load_meta(art_dir)
    changed_section = next(s for s in meta["sections"] if s["title"] == "statement")
    assert changed_section["author"] == "ai-drafted-human-confirmed"


def test_attempt_ai_write_refused_for_schema_human_field_and_logs_event(tmp_path):
    result = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(),
        sections={"meaningful_to_me": "meaningful"},
    )

    with pytest.raises(RejectedWriteError):
        attempt_ai_write(tmp_path, "gap-register", result["id"], "meaningful_to_me", "suspicious")

    events = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(events) == 1
    event = json.loads(events[0])
    assert event["family"] == "artifact_event"
    assert event["kind"] == "rejected_write"
    assert event["field"] == "meaningful_to_me"


def test_attempt_ai_write_succeeds_for_ai_authored_section(tmp_path):
    result = create_artifact(
        tmp_path, "gap-register", _base_fields(), sections={"statement": "draft text"}
    )

    outcome = attempt_ai_write(tmp_path, "gap-register", result["id"], "statement", "revised text")

    assert outcome == {"ok": True}
    art_dir = tmp_path / "artifacts" / "gap-register" / result["id"]
    assert "revised text" in (art_dir / "current.md").read_text()
    _, v1_sections = read_version(tmp_path, "gap-register", result["id"], 1)
    assert v1_sections[0].body == "draft text"


def test_ai_write_to_human_touched_section_is_refused_and_quarantined_as_proposed_diff(tmp_path):
    result = create_artifact(
        tmp_path, "gap-register", _base_fields(), sections={"statement": "draft text"}
    )
    art_dir = tmp_path / "artifacts" / "gap-register" / result["id"]

    current_text = (art_dir / "current.md").read_text()
    (art_dir / "current.md").write_text(current_text.replace("draft text", "researcher's own words"))
    scan(tmp_path, "gap-register", result["id"])

    outcome = attempt_ai_write(tmp_path, "gap-register", result["id"], "statement", "AI overwrite attempt")

    assert outcome["ok"] is False
    assert "quarantined_as" in outcome
    proposed_diff_path = Path(outcome["quarantined_as"])
    assert proposed_diff_path.is_file()
    assert proposed_diff_path.read_text() == "AI overwrite attempt"

    _, sections = read_version(tmp_path, "gap-register", result["id"], 2)
    statement = next(s for s in sections if s.title == "statement")
    assert "researcher's own words" in statement.body
    assert "AI overwrite attempt" not in statement.body


def test_missing_required_metadata_fields_blocks_accepted_status():
    incomplete = {"id": "art-1", "type": "gap-register"}
    missing = missing_required_metadata_fields(incomplete)
    assert "version" in missing
    assert "status" in missing
    assert "summary" in missing

    with pytest.raises(ArtifactError):
        validate_can_accept(incomplete)


def test_complete_metadata_passes_accept_validation():
    complete = {
        "id": "art-1",
        "type": "gap-register",
        "version": 1,
        "status": "reviewed",
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "human",
        "summary": "s",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-01-01T00:00:00Z",
    }
    validate_can_accept(complete)  # does not raise


def test_superseded_versions_remain_retrievable_never_deleted(tmp_path):
    result = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "v1 text"})
    art_dir = tmp_path / "artifacts" / "gap-register" / result["id"]
    (art_dir / "current.md").write_text(
        (art_dir / "current.md").read_text().replace("v1 text", "v2 text")
    )
    scan(tmp_path, "gap-register", result["id"])

    v1_frontmatter, v1_sections = read_version(tmp_path, "gap-register", result["id"], 1)
    v2_frontmatter, v2_sections = read_version(tmp_path, "gap-register", result["id"], 2)

    assert v1_sections[0].body == "v1 text"
    assert v2_sections[0].body == "v2 text"
    assert (art_dir / "v1.md").exists()
    assert (art_dir / "v2.md").exists()


def test_parallel_workers_on_different_sections_both_succeed(tmp_path):
    result = create_artifact(
        tmp_path,
        "field-map",
        _base_fields(),
        sections={"cluster_name": "cluster A", "scope": "deep"},
    )
    art_dir = tmp_path / "artifacts" / "field-map" / result["id"]
    meta = _load_meta(art_dir)
    name_section_id = next(s["id"] for s in meta["sections"] if s["title"] == "cluster_name")
    scope_section_id = next(s["id"] for s in meta["sections"] if s["title"] == "scope")

    assert claim_section(tmp_path, "field-map", result["id"], name_section_id, "worker-1") is True
    assert claim_section(tmp_path, "field-map", result["id"], scope_section_id, "worker-2") is True


def test_parallel_workers_on_same_section_second_is_rejected(tmp_path):
    result = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})
    art_dir = tmp_path / "artifacts" / "gap-register" / result["id"]
    section_id = _load_meta(art_dir)["sections"][0]["id"]

    assert claim_section(tmp_path, "gap-register", result["id"], section_id, "worker-1") is True
    assert claim_section(tmp_path, "gap-register", result["id"], section_id, "worker-2") is False


def test_mint_id_never_collides_across_many_calls():
    ids = {mint_id("art-") for _ in range(10_000)}
    assert len(ids) == 10_000


def test_pin_dependency_records_id_and_version():
    assert pin_dependency("art-abc123", 3) == "art-abc123@v3"


def test_create_artifact_stores_pinned_dependency_version(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "c"})
    dependent = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"statement": "x"},
    )
    frontmatter, _ = read_version(tmp_path, "gap-register", dependent["id"], 1)
    assert frontmatter["depends_on"] == [f"{dep['id']}@v1"]


def test_mark_dependents_stale_is_a_pure_graph_traversal(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "c"})
    dependent = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"statement": "x"},
    )

    staled = mark_dependents_stale(tmp_path, dep["id"], dependency_new_version=2)

    assert dependent["id"] in staled
    meta = _load_meta(tmp_path / "artifacts" / "gap-register" / dependent["id"])
    assert meta["status"] == "stale"


def test_mark_dependents_stale_ignores_artifacts_already_current(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "c"})
    unrelated = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})

    staled = mark_dependents_stale(tmp_path, dep["id"], dependency_new_version=2)

    assert unrelated["id"] not in staled


def test_accept_artifact_stores_summary_in_the_new_version_and_flips_status(tmp_path):
    result = create_artifact(
        tmp_path, "gap-register", _base_fields(summary=""), sections={"statement": "x"}
    )
    summary = "\n".join(f"line {i}" for i in range(6))

    outcome = accept_artifact(tmp_path, "gap-register", result["id"], summary)
    assert outcome["ok"] is True
    assert outcome["version"] == 2

    frontmatter, _ = read_version(tmp_path, "gap-register", result["id"], 2)
    assert frontmatter["summary"] == summary
    assert frontmatter["status"] == "accepted"

    v1_frontmatter, _ = read_version(tmp_path, "gap-register", result["id"], 1)
    assert v1_frontmatter["summary"] == ""


def test_accept_artifact_rejects_summary_outside_five_to_ten_lines(tmp_path):
    result = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})

    with pytest.raises(ArtifactError):
        accept_artifact(tmp_path, "gap-register", result["id"], "only one line")

    too_long = "\n".join(f"line {i}" for i in range(11))
    with pytest.raises(ArtifactError):
        accept_artifact(tmp_path, "gap-register", result["id"], too_long)


def _load_meta(art_dir):
    import yaml

    return yaml.safe_load((art_dir / "meta.yaml").read_text())
