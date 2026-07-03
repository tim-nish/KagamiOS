from kagami.events import append_event
from kagami.kernel.metrics import count_full_pull_after_summary


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
