import json

import pytest

from kagami.events import append_event


def test_append_event_writes_one_json_line(tmp_path):
    append_event(tmp_path, "artifact_event", {"kind": "test"})
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["family"] == "artifact_event"
    assert event["kind"] == "test"
    assert "timestamp" in event


def test_append_event_appends_without_truncating(tmp_path):
    append_event(tmp_path, "state_transition", {"n": 1})
    append_event(tmp_path, "state_transition", {"n": 2})
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["n"] == 1
    assert json.loads(lines[1])["n"] == 2


def test_append_event_rejects_unknown_family(tmp_path):
    with pytest.raises(ValueError):
        append_event(tmp_path, "not_a_real_family", {})
