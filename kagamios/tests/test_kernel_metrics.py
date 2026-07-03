from kagami.events import append_event
from kagami.kernel.metrics import compute_override_rate, count_full_pull_after_summary


def test_full_pull_immediately_after_summary_is_counted(tmp_path):
    append_event(
        tmp_path, "retrieval", {"kind": "summary_read", "artifact_id": "art-1", "state": "map"}
    )
    append_event(
        tmp_path, "retrieval", {"kind": "full_text_pull", "artifact_id": "art-1", "state": "map"}
    )
    assert count_full_pull_after_summary(tmp_path) == 1


def test_full_pull_without_a_preceding_summary_read_is_not_counted(tmp_path):
    append_event(
        tmp_path, "retrieval", {"kind": "full_text_pull", "artifact_id": "art-1", "state": "map"}
    )
    assert count_full_pull_after_summary(tmp_path) == 0


def test_summary_only_read_is_not_counted(tmp_path):
    append_event(
        tmp_path, "retrieval", {"kind": "summary_read", "artifact_id": "art-1", "state": "map"}
    )
    assert count_full_pull_after_summary(tmp_path) == 0


def test_each_summary_read_only_credits_one_subsequent_full_pull(tmp_path):
    append_event(tmp_path, "retrieval", {"kind": "summary_read", "artifact_id": "art-1"})
    append_event(tmp_path, "retrieval", {"kind": "full_text_pull", "artifact_id": "art-1"})
    append_event(tmp_path, "retrieval", {"kind": "full_text_pull", "artifact_id": "art-1"})
    assert count_full_pull_after_summary(tmp_path) == 1


def test_different_artifacts_are_tracked_independently(tmp_path):
    append_event(tmp_path, "retrieval", {"kind": "summary_read", "artifact_id": "art-1"})
    append_event(tmp_path, "retrieval", {"kind": "summary_read", "artifact_id": "art-2"})
    append_event(tmp_path, "retrieval", {"kind": "full_text_pull", "artifact_id": "art-2"})
    assert count_full_pull_after_summary(tmp_path) == 1


def test_no_events_file_returns_zero(tmp_path):
    assert count_full_pull_after_summary(tmp_path) == 0


def test_override_rate_with_no_events_is_zero(tmp_path):
    assert compute_override_rate(tmp_path, "cluster-dossier") == {
        "type": "cluster-dossier",
        "accepted_count": 0,
        "overridden_count": 0,
        "override_rate": 0.0,
    }


def test_override_rate_counts_accepted_artifacts_never_overridden_as_zero(tmp_path):
    append_event(
        tmp_path, "artifact_event",
        {"kind": "accepted", "artifact_type": "cluster-dossier", "artifact_id": "art-1"},
    )
    result = compute_override_rate(tmp_path, "cluster-dossier")
    assert result["accepted_count"] == 1
    assert result["overridden_count"] == 0
    assert result["override_rate"] == 0.0


def test_override_rate_counts_a_human_edit_on_an_accepted_artifact(tmp_path):
    append_event(
        tmp_path, "artifact_event",
        {"kind": "accepted", "artifact_type": "cluster-dossier", "artifact_id": "art-1"},
    )
    append_event(
        tmp_path, "artifact_event",
        {"kind": "accepted", "artifact_type": "cluster-dossier", "artifact_id": "art-2"},
    )
    append_event(
        tmp_path, "human_edit",
        {"kind": "scan_detected_change", "artifact_type": "cluster-dossier", "artifact_id": "art-1"},
    )
    result = compute_override_rate(tmp_path, "cluster-dossier")
    assert result["accepted_count"] == 2
    assert result["overridden_count"] == 1
    assert result["override_rate"] == 0.5


def test_override_rate_ignores_other_artifact_types(tmp_path):
    append_event(
        tmp_path, "artifact_event",
        {"kind": "accepted", "artifact_type": "field-map", "artifact_id": "art-1"},
    )
    append_event(
        tmp_path, "human_edit",
        {"kind": "scan_detected_change", "artifact_type": "field-map", "artifact_id": "art-1"},
    )
    assert compute_override_rate(tmp_path, "cluster-dossier")["accepted_count"] == 0
