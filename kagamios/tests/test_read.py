import json

import pytest

from kagami.store.artifact import create_artifact
from kagami.store.read import ConsumptionError, read_artifact


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def test_read_within_consumption_map_summary_is_logged_distinctly_from_full(tmp_path):
    art = create_artifact(tmp_path, "researcher-profile", _base_fields(), sections={"notes": "x"})

    summary_result = read_artifact(tmp_path, "frame", "researcher-profile", art["id"], "summary")
    assert summary_result["ok"] is True
    assert summary_result["resolution"] == "summary"

    full_result = read_artifact(tmp_path, "frame", "researcher-profile", art["id"], "full")
    assert full_result["ok"] is True
    assert full_result["resolution"] == "full"
    assert full_result["sections"][0]["body"] == "x"

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    retrievals = [e for e in events if e["family"] == "retrieval"]
    assert len(retrievals) == 2
    assert retrievals[0]["kind"] == "summary_read"
    assert retrievals[1]["kind"] == "full_text_pull"
    assert retrievals[0]["artifact_id"] == retrievals[1]["artifact_id"] == art["id"]


def test_read_outside_consumption_map_is_refused(tmp_path):
    art = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})

    with pytest.raises(ConsumptionError):
        read_artifact(tmp_path, "frame", "gap-register", art["id"], "summary")

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert not any(e["family"] == "retrieval" for e in events)


def test_read_rejects_unknown_resolution(tmp_path):
    art = create_artifact(tmp_path, "researcher-profile", _base_fields(), sections={"notes": "x"})
    with pytest.raises(ConsumptionError):
        read_artifact(tmp_path, "frame", "researcher-profile", art["id"], "half")
