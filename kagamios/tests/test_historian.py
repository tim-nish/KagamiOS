import json

import pytest

from kagami.kernel.historian import HistorianError, detect_frontier_speculation, historian_write
from kagami.store.artifact import create_artifact, read_current


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _create_dossier(run_dir):
    return create_artifact(
        run_dir, "cluster-dossier", _base_fields(), sections={"evolution": "founding problem"}
    )


def test_historian_can_write_the_evolution_section(tmp_path):
    dossier = _create_dossier(tmp_path)
    result = historian_write(tmp_path, dossier["id"], "evolution", "the field began with X, then shifted to Y")
    assert result["ok"] is True

    frontmatter, sections = read_current(tmp_path, "cluster-dossier", dossier["id"])
    evolution = next(s for s in sections if s.title == "evolution")
    assert "shifted to Y" in evolution.body


def test_historian_writing_outside_evolution_is_refused_and_logged(tmp_path):
    dossier = create_artifact(
        tmp_path,
        "cluster-dossier",
        _base_fields(),
        sections={"evolution": "x", "frontier": "y"},
    )

    with pytest.raises(HistorianError):
        historian_write(tmp_path, dossier["id"], "frontier", "some frontier content")

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    violations = [e for e in events if e.get("kind") == "generation_window_violation"]
    assert len(violations) == 1
    assert violations[0]["family"] == "gate_event"
    assert violations[0]["role"] == "historian"

    # the frontier section itself was never touched
    _, sections = read_current(tmp_path, "cluster-dossier", dossier["id"])
    frontier = next(s for s in sections if s.title == "frontier")
    assert frontier.body == "y"


def test_detect_frontier_speculation_flags_forward_looking_phrases():
    assert detect_frontier_speculation("this could enable new applications") == "could enable"
    assert detect_frontier_speculation("the founding problem was X in 1990") is None


def test_historian_frontier_speculation_within_evolution_is_refused_and_logged(tmp_path):
    dossier = _create_dossier(tmp_path)

    with pytest.raises(HistorianError):
        historian_write(
            tmp_path, dossier["id"], "evolution", "the field shifted, and this could enable new applications"
        )

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    violations = [e for e in events if e.get("kind") == "generation_window_violation"]
    assert len(violations) == 1
    assert violations[0]["role"] == "historian"

    # the evolution section was never overwritten with the speculative draft
    _, sections = read_current(tmp_path, "cluster-dossier", dossier["id"])
    evolution = next(s for s in sections if s.title == "evolution")
    assert evolution.body == "founding problem"
