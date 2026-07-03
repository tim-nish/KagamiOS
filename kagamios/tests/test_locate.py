import json

import pytest

from kagami.kernel.locate import (
    LocateError,
    check_mvp_terminal,
    locate_write,
    mark_gap_meaningful,
    record_micro_probe_evidence,
    validate_locate_exit,
)
from kagami.store.artifact import RejectedWriteError, accept_artifact, create_artifact, read_current, review_artifact


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _create_gap_register(run_dir, **sections):
    base_sections = {
        "statement": "",
        "evidence_of_absence": "",
        "why_does_this_gap_exist": "",
        "meaningful_to_me": "",
    }
    base_sections.update(sections)
    return create_artifact(run_dir, "gap-register", _base_fields(), sections=base_sections)


def test_locate_write_drafts_statement_and_evidence_of_absence(tmp_path):
    gap = _create_gap_register(tmp_path)

    locate_write(tmp_path, gap["id"], "statement", "nobody has combined X with Y")
    result = locate_write(tmp_path, gap["id"], "evidence_of_absence", "searched venues A/B 2019-2025, zero hits")
    assert result["ok"] is True

    _, sections = read_current(tmp_path, "gap-register", gap["id"])
    bodies = {s.title: s.body for s in sections}
    assert bodies["statement"] == "nobody has combined X with Y"
    assert bodies["evidence_of_absence"] == "searched venues A/B 2019-2025, zero hits"


def test_locate_write_accepts_a_valid_why_does_this_gap_exist_value(tmp_path):
    gap = _create_gap_register(tmp_path)
    result = locate_write(tmp_path, gap["id"], "why_does_this_gap_exist", "genuinely_open")
    assert result["ok"] is True


def test_locate_write_refuses_a_missing_why_does_this_gap_exist_explanation(tmp_path):
    gap = _create_gap_register(tmp_path)
    with pytest.raises(LocateError):
        locate_write(tmp_path, gap["id"], "why_does_this_gap_exist", "")

    _, sections = read_current(tmp_path, "gap-register", gap["id"])
    bodies = {s.title: s.body for s in sections}
    assert bodies["why_does_this_gap_exist"] == ""


def test_locate_write_refuses_an_unrecognized_why_does_this_gap_exist_value(tmp_path):
    gap = _create_gap_register(tmp_path)
    with pytest.raises(LocateError):
        locate_write(tmp_path, gap["id"], "why_does_this_gap_exist", "nobody-cited-it")


def test_locate_write_refuses_writing_meaningful_to_me_and_logs_it(tmp_path):
    gap = _create_gap_register(tmp_path)

    with pytest.raises(RejectedWriteError):
        locate_write(tmp_path, gap["id"], "meaningful_to_me", "meaningful")

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    rejected = [e for e in events if e.get("kind") == "rejected_write"]
    assert len(rejected) == 1
    assert rejected[0]["field"] == "meaningful_to_me"
    assert rejected[0]["reason"] == "schema declares author: human (FR-31)"

    _, sections = read_current(tmp_path, "gap-register", gap["id"])
    bodies = {s.title: s.body for s in sections}
    assert bodies["meaningful_to_me"] == ""


def test_mark_gap_meaningful_sets_the_disposition_via_the_human_edit_surface(tmp_path):
    gap = _create_gap_register(tmp_path)

    result = mark_gap_meaningful(tmp_path, gap["id"], "suspicious")
    assert result["ok"] is True

    _, sections = read_current(tmp_path, "gap-register", gap["id"])
    bodies = {s.title: s.body for s in sections}
    assert bodies["meaningful_to_me"] == "suspicious"


def test_mark_gap_meaningful_refuses_an_unrecognized_disposition(tmp_path):
    gap = _create_gap_register(tmp_path)
    with pytest.raises(LocateError):
        mark_gap_meaningful(tmp_path, gap["id"], "definitely-maybe")


def test_record_micro_probe_evidence_writes_only_that_one_field_and_mints_no_artifact(tmp_path):
    gap = _create_gap_register(tmp_path, micro_probe_evidence="")
    before_dirs = sorted(p.name for p in (tmp_path / "artifacts").glob("*/*"))

    result = record_micro_probe_evidence(tmp_path, gap["id"], "ran a 2hr feasibility check: approach compiles")
    assert result["ok"] is True

    after_dirs = sorted(p.name for p in (tmp_path / "artifacts").glob("*/*"))
    assert after_dirs == before_dirs

    _, sections = read_current(tmp_path, "gap-register", gap["id"])
    bodies = {s.title: s.body for s in sections}
    assert bodies["micro_probe_evidence"] == "ran a 2hr feasibility check: approach compiles"


def test_validate_locate_exit_fails_when_a_minimal_profile_field_is_blank(tmp_path):
    gap = _create_gap_register(tmp_path, statement="a real gap")
    review_artifact(tmp_path, "gap-register", gap["id"])
    accept_artifact(tmp_path, "gap-register", gap["id"], "\n".join(f"line {i}" for i in range(6)))

    result = validate_locate_exit(tmp_path, gap["id"])
    assert result["ok"] is False
    assert any("evidence_of_absence" in v for v in result["violations"])
    assert any("why_does_this_gap_exist" in v for v in result["violations"])
    assert any("meaningful_to_me" in v for v in result["violations"])


def test_validate_locate_exit_fails_for_an_unaccepted_gap_register(tmp_path):
    gap = _create_gap_register(
        tmp_path,
        statement="a real gap",
        evidence_of_absence="searched, found nothing",
        why_does_this_gap_exist="genuinely_open",
    )
    mark_gap_meaningful(tmp_path, gap["id"], "meaningful")

    result = validate_locate_exit(tmp_path, gap["id"])
    assert result["ok"] is False
    assert any("not yet accepted" in v for v in result["violations"])


def test_validate_locate_exit_passes_once_every_minimal_profile_section_is_populated(tmp_path):
    gap = _create_gap_register(
        tmp_path,
        statement="a real gap",
        evidence_of_absence="searched, found nothing",
        why_does_this_gap_exist="genuinely_open",
    )
    mark_gap_meaningful(tmp_path, gap["id"], "meaningful")
    review_artifact(tmp_path, "gap-register", gap["id"])
    accept_artifact(tmp_path, "gap-register", gap["id"], "\n".join(f"line {i}" for i in range(6)))

    result = validate_locate_exit(tmp_path, gap["id"])
    assert result == {"ok": True, "violations": []}


def test_check_mvp_terminal_is_not_reached_before_any_gap_register_is_accepted(tmp_path):
    _create_gap_register(tmp_path, statement="a real gap")

    assert check_mvp_terminal(tmp_path) == {"ok": True, "terminal_reached": False}


def test_check_mvp_terminal_is_reached_once_a_gap_register_is_accepted(tmp_path):
    gap = _create_gap_register(
        tmp_path,
        statement="a real gap",
        evidence_of_absence="searched, found nothing",
        why_does_this_gap_exist="genuinely_open",
    )
    mark_gap_meaningful(tmp_path, gap["id"], "meaningful")
    review_artifact(tmp_path, "gap-register", gap["id"])
    accept_artifact(tmp_path, "gap-register", gap["id"], "\n".join(f"line {i}" for i in range(6)))

    assert check_mvp_terminal(tmp_path) == {"ok": True, "terminal_reached": True}
