from kagami.kernel.profile import validate_minimal_profile
from kagami.store.artifact import accept_artifact, create_artifact, review_artifact


def _six_line_summary():
    return "\n".join(f"line {i}" for i in range(6))


def test_accepted_artifact_with_all_minimal_fields_populated_passes(tmp_path):
    result = create_artifact(
        tmp_path,
        "inquiry-frame",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "in_scope_readings": ["ppr-1"],
            "exclusions": ["ppr-2"],
            "hard_constraints": ["compute-limited"],
        },
        sections={"intuition_restated": "x", "unprimed_hunch": "my hunch"},
    )
    review_artifact(tmp_path, "inquiry-frame", result["id"])
    accept_artifact(tmp_path, "inquiry-frame", result["id"], _six_line_summary())

    outcome = validate_minimal_profile(tmp_path)
    assert outcome["ok"] is True
    assert outcome["violations"] == []


def test_full_profile_field_being_empty_never_fails_validation(tmp_path):
    result = create_artifact(
        tmp_path,
        "inquiry-frame",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "in_scope_readings": ["ppr-1"],
            "exclusions": ["ppr-2"],
            "hard_constraints": ["compute-limited"],
            "motivation": "",  # profile: full — legitimately empty
        },
        sections={"intuition_restated": "x", "unprimed_hunch": "my hunch"},
    )
    review_artifact(tmp_path, "inquiry-frame", result["id"])
    accept_artifact(tmp_path, "inquiry-frame", result["id"], _six_line_summary())

    outcome = validate_minimal_profile(tmp_path)
    assert outcome["ok"] is True


def test_empty_dependency_lists_are_a_legitimate_minimal_state_not_a_violation(tmp_path):
    result = create_artifact(
        tmp_path,
        "inquiry-frame",
        {
            "depends_on": [],  # profile: minimal, but "no dependencies" is legitimate
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "in_scope_readings": [],
            "exclusions": [],
            "hard_constraints": [],
        },
        sections={"intuition_restated": "x", "unprimed_hunch": "my hunch"},
    )
    review_artifact(tmp_path, "inquiry-frame", result["id"])
    accept_artifact(tmp_path, "inquiry-frame", result["id"], _six_line_summary())

    outcome = validate_minimal_profile(tmp_path)
    assert outcome["ok"] is True


def test_accepted_artifact_missing_a_minimal_text_field_fails_validation(tmp_path):
    result = create_artifact(
        tmp_path,
        "inquiry-frame",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "in_scope_readings": ["ppr-1"],
            "exclusions": ["ppr-2"],
            "hard_constraints": ["compute-limited"],
        },
        sections={"intuition_restated": "x", "unprimed_hunch": ""},  # profile: minimal — required
    )
    review_artifact(tmp_path, "inquiry-frame", result["id"])
    accept_artifact(tmp_path, "inquiry-frame", result["id"], _six_line_summary())

    outcome = validate_minimal_profile(tmp_path)
    assert outcome["ok"] is False
    assert any(v["field"] == "unprimed_hunch" for v in outcome["violations"])


def test_draft_artifacts_are_not_checked(tmp_path):
    create_artifact(
        tmp_path,
        "inquiry-frame",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
        },
        sections={},
    )

    outcome = validate_minimal_profile(tmp_path)
    assert outcome["ok"] is True


def test_no_artifacts_at_all_passes(tmp_path):
    outcome = validate_minimal_profile(tmp_path)
    assert outcome == {"ok": True, "violations": []}
