import json

import pytest

from kagami.kernel.skeptic import (
    SkepticError,
    build_skeptic_context,
    record_skeptic_critique,
    skeptic_write,
)
from kagami.store.artifact import create_artifact, pin_dependency, read_current


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _candidate(run_dir, **overrides):
    return create_artifact(
        run_dir,
        "candidate-direction",
        _base_fields(**overrides),
        sections={"direction": "x", "red_team_notes": ""},
    )


def test_skeptic_write_succeeds_only_for_red_team_notes(tmp_path):
    candidate = _candidate(tmp_path)
    result = skeptic_write(tmp_path, "candidate-direction", candidate["id"], "red_team_notes", "weak evidence")
    assert result["ok"] is True

    _, sections = read_current(tmp_path, "candidate-direction", candidate["id"])
    notes = next(s for s in sections if s.title == "red_team_notes")
    assert "weak evidence" in notes.body


def test_skeptic_write_refuses_any_other_field_on_candidate_direction(tmp_path):
    candidate = _candidate(tmp_path)
    with pytest.raises(SkepticError):
        skeptic_write(tmp_path, "candidate-direction", candidate["id"], "direction", "a new proposed direction")


def test_skeptic_write_refuses_a_constitutive_triad_field(tmp_path):
    gap_register = create_artifact(
        tmp_path, "gap-register", _base_fields(), sections={"statement": "x", "meaningful_to_me": "y"}
    )
    with pytest.raises(SkepticError):
        skeptic_write(tmp_path, "gap-register", gap_register["id"], "meaningful_to_me", "suspicious")


def test_skeptic_write_refusal_is_logged_as_a_generation_window_violation(tmp_path):
    candidate = _candidate(tmp_path)
    with pytest.raises(SkepticError):
        skeptic_write(tmp_path, "candidate-direction", candidate["id"], "why_now", "a new argument")

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    violations = [e for e in events if e.get("kind") == "generation_window_violation"]
    assert len(violations) == 1
    assert violations[0]["family"] == "gate_event"
    assert violations[0]["role"] == "skeptic"


def test_record_skeptic_critique_on_non_candidate_type_is_event_only(tmp_path):
    field_map = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "x"})

    result = record_skeptic_critique(
        tmp_path, "field-map", field_map["id"], "this partition hides an obvious sub-cluster", ["ppr-1"]
    )
    assert result == {"ok": True, "recorded_as": "event_only"}

    # the artifact itself was never touched
    frontmatter, _ = read_current(tmp_path, "field-map", field_map["id"])
    assert frontmatter["version"] == 1

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    critiques = [e for e in events if e.get("kind") == "skeptic_critique"]
    assert len(critiques) == 1
    assert critiques[0]["role"] == "skeptic"
    assert critiques[0]["objection"] == "this partition hides an obvious sub-cluster"


def test_record_skeptic_critique_on_candidate_direction_writes_red_team_notes(tmp_path):
    candidate = _candidate(tmp_path)
    result = record_skeptic_critique(
        tmp_path, "candidate-direction", candidate["id"], "the evidence doesn't support this claim", ["ppr-2"]
    )
    assert result["ok"] is True

    _, sections = read_current(tmp_path, "candidate-direction", candidate["id"])
    notes = next(s for s in sections if s.title == "red_team_notes")
    assert "doesn't support" in notes.body


def test_skeptic_context_includes_target_and_cited_evidence_but_not_elicited_from(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(summary="a five word summary"), sections={"cluster_name": "x"})
    target = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)], elicited_from=["q-abc@v1"]),
        sections={"statement": "there is a gap"},
    )

    context = build_skeptic_context(tmp_path, "gap-register", target["id"])
    assert context["target"]["id"] == target["id"]
    assert any(s["title"] == "statement" for s in context["target"]["sections"])
    assert "elicited_from" not in context["target"]

    assert len(context["cited_evidence"]) == 1
    assert context["cited_evidence"][0]["id"] == dep["id"]
    assert context["cited_evidence"][0]["summary"] == "a five word summary"


def test_two_consecutive_skeptic_invocations_share_nothing(tmp_path):
    dep_a = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "a"})
    target_a = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep_a["id"], 1)]),
        sections={"statement": "gap A"},
    )
    dep_b = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "b"})
    target_b = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep_b["id"], 1)]),
        sections={"statement": "gap B"},
    )

    context_a = build_skeptic_context(tmp_path, "gap-register", target_a["id"])
    context_b = build_skeptic_context(tmp_path, "gap-register", target_b["id"])

    assert context_a["target"]["id"] != context_b["target"]["id"]
    cited_ids_a = {e["id"] for e in context_a["cited_evidence"]}
    cited_ids_b = {e["id"] for e in context_b["cited_evidence"]}
    assert cited_ids_a.isdisjoint(cited_ids_b)
    assert dep_b["id"] not in cited_ids_a
    assert dep_a["id"] not in cited_ids_b
