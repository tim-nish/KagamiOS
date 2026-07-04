import json

import pytest

from kagami.kernel.entry import start_run_from_entry
from kagami.kernel.frame import complete_frame
from kagami.kernel.state_machine import enter_state, get_state_cache
from kagami.store.artifact import RejectedWriteError, attempt_ai_write, read_current
from kagami.store.run import open_run


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_a_real_intuition_reaches_an_accepted_inquiry_frame_from_any_entry_mode(tmp_path):
    open_run(run_id="run-first-framed", output_root=tmp_path / "_out")
    run_dir = tmp_path / "_out" / "runs" / "run-first-framed"

    # AC1 (FR-6): any entry mode backfills a non-empty Intuition Note and
    # roots the run at Frame before Map begins.
    entry_result = start_run_from_entry(
        run_dir, "paper-first", "a paper on signature methods sparked this"
    )
    assert entry_result["ok"] is True
    intuition_frontmatter, intuition_sections = read_current(
        run_dir, "intuition-note", entry_result["intuition_note_id"]
    )
    assert any(s.body for s in intuition_sections)
    assert get_state_cache(run_dir)["current_state"] == "frame"

    # AC2 (FR-10, FR-24): completing Frame answers the unprimed E6 question
    # and the menu-form scope question, and the Inquiry Frame reaches
    # accepted via draft -> reviewed -> accepted.
    frame_result = complete_frame(
        run_dir,
        unprimed_answer="I suspect signatures are just feature maps in disguise",
        scope_answer="readings 1 and 2 are in scope",
        fields={
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "in_scope_readings": ["ppr-1", "ppr-2"],
            "exclusions": ["ppr-3"],
            "hard_constraints": ["compute-limited"],
        },
        sections={"intuition_restated": "signatures as building blocks", "unprimed_hunch": "placeholder"},
        summary="\n".join(f"line {i}" for i in range(6)),
    )
    assert frame_result["ok"] is True
    art_id = frame_result["inquiry_frame_id"]

    frontmatter, _ = read_current(run_dir, "inquiry-frame", art_id)
    assert frontmatter["status"] == "accepted"

    v1_frontmatter, _ = _read_version(run_dir, art_id, 1)
    assert v1_frontmatter["status"] == "draft"
    statuses_seen = {
        _read_version(run_dir, art_id, v)[0]["status"] for v in range(1, frontmatter["version"] + 1)
    }
    assert "draft" in statuses_seen
    assert "reviewed" in statuses_seen
    assert "accepted" in statuses_seen

    # AC4 (FR-4, FR-31): scope/attention allocation is constitutive-triad —
    # no AI write to it succeeds, at any level.
    with pytest.raises(RejectedWriteError):
        attempt_ai_write(run_dir, "inquiry-frame", art_id, "in_scope_readings", ["ppr-hijacked"])

    # AC5 (FR-1): every state transition taken so far is logged.
    enter_state(run_dir, "map")
    state_events = [e for e in _events(run_dir) if e["family"] == "state_transition" and e["kind"] == "entered"]
    states_entered = [e["state"] for e in state_events]
    assert states_entered == ["frame", "map"]


def test_skipping_frame_entirely_is_flagged_as_a_data_integrity_violation(tmp_path):
    # AC3 (FR-2): jumping straight to Map without ever entering Frame, and
    # without recording a waiver, is a detectable violation.
    open_run(run_id="run-skip-frame", output_root=tmp_path / "_out")
    run_dir = tmp_path / "_out" / "runs" / "run-skip-frame"

    result = enter_state(run_dir, "map")
    assert result["violation"] is not None
    assert get_state_cache(run_dir)["integrity_violations"]


def _read_version(run_dir, art_id, version):
    from kagami.store.artifact import read_version

    return read_version(run_dir, "inquiry-frame", art_id, version)
