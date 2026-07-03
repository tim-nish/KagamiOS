import yaml
import pytest

from kagami.kernel.frame import complete_frame
from kagami.store.artifact import RejectedWriteError, attempt_ai_write, read_current, read_version


def _frame_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
        "in_scope_readings": ["ppr-1", "ppr-2"],
        "exclusions": ["ppr-3"],
        "hard_constraints": ["compute-limited"],
    }
    fields.update(overrides)
    return fields


def _six_line_summary():
    return "\n".join(f"line {i}" for i in range(6))


def test_complete_frame_reaches_accepted_with_both_questions_answered(tmp_path):
    result = complete_frame(
        tmp_path,
        unprimed_answer="I suspect signatures are just feature maps in disguise",
        scope_answer="readings 1 and 2 are in scope, 3 is background",
        fields=_frame_fields(),
        sections={"intuition_restated": "signatures as building blocks", "unprimed_hunch": "placeholder"},
        summary=_six_line_summary(),
    )
    assert result["ok"] is True

    art_id = result["inquiry_frame_id"]
    frontmatter, _ = read_current(tmp_path, "inquiry-frame", art_id)
    assert frontmatter["status"] == "accepted"
    assert frontmatter["summary"] == _six_line_summary()
    assert any(ref.startswith(result["unprimed_question_id"]) for ref in frontmatter["elicited_from"])
    assert any(ref.startswith(result["scope_question_id"]) for ref in frontmatter["elicited_from"])


def test_complete_frame_pins_the_unprimed_answer_before_the_frame_artifact_is_created(tmp_path):
    """FR-24: the ledger answer's timestamp must precede the artifact's
    creation timestamp — proof the ask-before-show ordering actually held."""
    result = complete_frame(
        tmp_path,
        unprimed_answer="my unprimed hunch",
        scope_answer="1,2 in scope",
        fields=_frame_fields(),
        sections={"intuition_restated": "x", "unprimed_hunch": "y"},
        summary=_six_line_summary(),
    )
    entry = yaml.safe_load(
        (tmp_path / "ledger" / f"{result['unprimed_question_id']}.yaml").read_text()
    )
    v1_frontmatter, _ = read_version(tmp_path, "inquiry-frame", result["inquiry_frame_id"], 1)
    assert entry["answered_at"] <= v1_frontmatter["created"]


def test_constitutive_triad_field_on_inquiry_frame_refuses_ai_write(tmp_path):
    result = complete_frame(
        tmp_path,
        unprimed_answer="my unprimed hunch",
        scope_answer="1,2 in scope",
        fields=_frame_fields(),
        sections={"intuition_restated": "x", "unprimed_hunch": "y"},
        summary=_six_line_summary(),
    )
    art_id = result["inquiry_frame_id"]

    with pytest.raises(RejectedWriteError):
        attempt_ai_write(tmp_path, "inquiry-frame", art_id, "in_scope_readings", ["ppr-99"])

    with pytest.raises(RejectedWriteError):
        attempt_ai_write(tmp_path, "inquiry-frame", art_id, "exclusions", ["ppr-98"])
