import pytest

from kagami.kernel.dissolution import (
    DissolutionError,
    check_dissolution_terminal,
    draft_dissolution_memo,
    record_revival_conditions,
    record_what_was_learned,
    spin_off_salvaged_fragment,
    validate_dissolution_exit,
)
from kagami.store.artifact import accept_artifact, create_artifact, read_current, review_artifact


def _dissolving_evidence(tmp_path):
    dep = create_artifact(
        tmp_path,
        "field-map",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"cluster_name": "x"},
    )
    return [f"{dep['id']}@v1"]


def test_draft_dissolution_memo_refuses_an_empty_evidence_citation(tmp_path):
    with pytest.raises(DissolutionError):
        draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=[])


def test_draft_dissolution_memo_pins_depends_on_and_what_dissolved_it_to_the_cited_evidence(tmp_path):
    evidence = _dissolving_evidence(tmp_path)

    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)

    frontmatter, sections = read_current(tmp_path, "dissolution-memo", memo["id"])
    assert frontmatter["depends_on"] == evidence
    assert frontmatter["what_dissolved_it"] == evidence
    bodies = {s.title: s.body for s in sections}
    assert bodies["intuition_summary"] == "the intuition was X"


def test_record_what_was_learned_and_revival_conditions_via_human_edit_surface(tmp_path):
    evidence = _dissolving_evidence(tmp_path)
    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)

    record_what_was_learned(tmp_path, memo["id"], "the mechanism doesn't generalize")
    record_revival_conditions(tmp_path, memo["id"], "revisit if a new dataset appears")

    _, sections = read_current(tmp_path, "dissolution-memo", memo["id"])
    bodies = {s.title: s.body for s in sections}
    assert bodies["what_was_learned"] == "the mechanism doesn't generalize"
    assert bodies["revival_conditions"] == "revisit if a new dataset appears"


def test_spin_off_salvaged_fragment_creates_a_real_intuition_note_and_pins_it(tmp_path):
    evidence = _dissolving_evidence(tmp_path)
    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)

    result = spin_off_salvaged_fragment(tmp_path, memo["id"], "the sub-idea about Y might still work")
    assert result["ok"] is True

    note_frontmatter, note_sections = read_current(tmp_path, "intuition-note", result["intuition_note_id"])
    assert note_frontmatter["entry_mode"] == "intuition-first"
    assert note_sections[0].body == "the sub-idea about Y might still work"

    memo_frontmatter, _ = read_current(tmp_path, "dissolution-memo", memo["id"])
    assert memo_frontmatter["salvaged_fragments"] == [f"{result['intuition_note_id']}@v1"]


def test_spin_off_salvaged_fragment_refuses_an_unrecognized_entry_mode(tmp_path):
    evidence = _dissolving_evidence(tmp_path)
    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)

    with pytest.raises(DissolutionError):
        spin_off_salvaged_fragment(tmp_path, memo["id"], "fragment", entry_mode="not-a-real-mode")


def test_validate_dissolution_exit_fails_when_a_minimal_profile_field_is_blank(tmp_path):
    evidence = _dissolving_evidence(tmp_path)
    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)
    review_artifact(tmp_path, "dissolution-memo", memo["id"])
    accept_artifact(tmp_path, "dissolution-memo", memo["id"], "\n".join(f"line {i}" for i in range(6)))

    result = validate_dissolution_exit(tmp_path, memo["id"])
    assert result["ok"] is False
    assert any("what_was_learned" in v for v in result["violations"])


def test_validate_dissolution_exit_passes_once_every_minimal_profile_section_is_populated(tmp_path):
    evidence = _dissolving_evidence(tmp_path)
    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)
    record_what_was_learned(tmp_path, memo["id"], "the mechanism doesn't generalize")
    review_artifact(tmp_path, "dissolution-memo", memo["id"])
    accept_artifact(tmp_path, "dissolution-memo", memo["id"], "\n".join(f"line {i}" for i in range(6)))

    result = validate_dissolution_exit(tmp_path, memo["id"])
    assert result == {"ok": True, "violations": []}


def test_check_dissolution_terminal_is_reached_only_once_a_memo_is_accepted(tmp_path):
    evidence = _dissolving_evidence(tmp_path)
    memo = draft_dissolution_memo(tmp_path, "the intuition was X", dissolving_evidence=evidence)

    assert check_dissolution_terminal(tmp_path) == {"ok": True, "terminal_reached": False}

    record_what_was_learned(tmp_path, memo["id"], "the mechanism doesn't generalize")
    review_artifact(tmp_path, "dissolution-memo", memo["id"])
    accept_artifact(tmp_path, "dissolution-memo", memo["id"], "\n".join(f"line {i}" for i in range(6)))

    assert check_dissolution_terminal(tmp_path) == {"ok": True, "terminal_reached": True}
