import json

import pytest

from kagami.store.appraisal import (
    AppraisalError,
    current_appraisal_for_paper,
    list_appraisals_for_paper,
    record_appraisal,
)
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-appraisal"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_record_appraisal_writes_a_structured_entry_and_logs_an_event(tmp_path):
    run_dir = _open(tmp_path)

    result = record_appraisal(run_dir, "ppr-abc", "highly-relevant", "frame-v1", "anchors the cluster", "worker")

    assert result["ok"] is True
    entries = list_appraisals_for_paper(run_dir, "ppr-abc")
    assert len(entries) == 1
    assert entries[0]["id"] == result["id"]
    assert entries[0]["judgment"] == "highly-relevant"
    assert entries[0]["frame_version"] == "frame-v1"
    assert entries[0]["reason"] == "anchors the cluster"
    assert entries[0]["role"] == "worker"

    recorded = [e for e in _events(run_dir) if e["family"] == "artifact_event" and e["kind"] == "appraisal_recorded"]
    assert len(recorded) == 1
    assert recorded[0]["paper_id"] == "ppr-abc"
    assert recorded[0]["frame_version"] == "frame-v1"


def test_record_appraisal_requires_paper_id_judgment_and_frame_version(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(AppraisalError):
        record_appraisal(run_dir, "", "relevant", "frame-v1", "reason", "worker")
    with pytest.raises(AppraisalError):
        record_appraisal(run_dir, "ppr-abc", "", "frame-v1", "reason", "worker")
    with pytest.raises(AppraisalError):
        record_appraisal(run_dir, "ppr-abc", "relevant", "", "reason", "worker")


@pytest.mark.parametrize("role", ["", "not-a-real-role"])
def test_record_appraisal_requires_a_recognized_role(tmp_path, role):
    """FR-58: `role` is mandatory and validated — no default value silently
    satisfies the requirement, and an unrecognized role is refused the
    same as an empty one."""
    run_dir = _open(tmp_path)
    with pytest.raises(AppraisalError):
        record_appraisal(run_dir, "ppr-abc", "relevant", "frame-v1", "reason", role)

    assert list_appraisals_for_paper(run_dir, "ppr-abc") == []


def test_reappraisal_on_frame_revision_is_additive_not_an_edit(tmp_path):
    """FR-52: revising the frame never silently carries an old appraisal
    forward — re-appraising against the new frame_version is a distinct,
    separately recorded entry, and the old one is retained, not overwritten."""
    run_dir = _open(tmp_path)
    record_appraisal(run_dir, "ppr-abc", "relevant", "frame-v1", "first read", "worker")
    record_appraisal(run_dir, "ppr-abc", "marginal", "frame-v2", "reframed after Frame revision", "worker")

    entries = list_appraisals_for_paper(run_dir, "ppr-abc")
    assert len(entries) == 2
    assert {e["frame_version"] for e in entries} == {"frame-v1", "frame-v2"}


def test_current_appraisal_for_paper_is_scoped_to_the_requested_frame_version(tmp_path):
    run_dir = _open(tmp_path)
    record_appraisal(run_dir, "ppr-abc", "relevant", "frame-v1", "first read", "worker")

    assert current_appraisal_for_paper(run_dir, "ppr-abc", "frame-v1")["judgment"] == "relevant"
    assert current_appraisal_for_paper(run_dir, "ppr-abc", "frame-v2") is None


def test_list_appraisals_for_paper_is_empty_when_none_recorded(tmp_path):
    run_dir = _open(tmp_path)
    assert list_appraisals_for_paper(run_dir, "ppr-nonexistent") == []
