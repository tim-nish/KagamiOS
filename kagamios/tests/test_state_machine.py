import json

import pytest

from kagami.kernel.state_machine import StateMachineError, enter_state, get_state_cache
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-sm"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_first_entry_into_frame_is_legal_with_no_violation(tmp_path):
    run_dir = _open(tmp_path)
    result = enter_state(run_dir, "frame")
    assert result == {"ok": True, "state": "frame", "violation": None}
    assert get_state_cache(run_dir)["current_state"] == "frame"


def test_nominal_forward_progression_requires_nothing_extra(tmp_path):
    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    result = enter_state(run_dir, "map")
    assert result["violation"] is None
    assert get_state_cache(run_dir)["current_state"] == "map"


def test_skipping_frame_without_a_waiver_is_flagged_as_a_violation(tmp_path):
    run_dir = _open(tmp_path)
    result = enter_state(run_dir, "map")
    assert result["ok"] is True
    assert result["violation"] is not None
    assert get_state_cache(run_dir)["current_state"] == "map"

    violations = get_state_cache(run_dir)["integrity_violations"]
    assert len(violations) == 1
    assert violations[0]["kind"] == "skipped_state"

    events = _events(run_dir)
    integrity_events = [e for e in events if e.get("kind") == "integrity_violation"]
    assert len(integrity_events) == 1
    assert integrity_events[0]["family"] == "gate_event"


def test_skipping_a_state_with_a_waiver_is_not_a_violation(tmp_path):
    run_dir = _open(tmp_path)
    result = enter_state(run_dir, "map", waiver="researcher already had a clear frame in mind")
    assert result["violation"] is None
    assert get_state_cache(run_dir)["integrity_violations"] == []


def test_re_entering_the_current_state_is_not_a_skip(tmp_path):
    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    result = enter_state(run_dir, "frame")
    assert result["violation"] is None


def test_backward_transition_requires_a_cause_and_is_refused_without_one(tmp_path):
    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    enter_state(run_dir, "map")
    enter_state(run_dir, "deepen")

    with pytest.raises(StateMachineError):
        enter_state(run_dir, "frame")  # deepen -> frame is a registered backward transition


def test_backward_transition_with_a_cause_succeeds_and_logs_it(tmp_path):
    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    enter_state(run_dir, "map")
    enter_state(run_dir, "deepen")

    result = enter_state(run_dir, "frame", cause="reading reframed the intuition")
    assert result["violation"] is None

    events = _events(run_dir)
    backward_event = [e for e in events if e.get("kind") == "entered" and e.get("state") == "frame"][-1]
    assert backward_event["cause"] == "reading reframed the intuition"


def test_dissolved_is_reachable_from_any_state_without_a_waiver(tmp_path):
    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    result = enter_state(run_dir, "dissolved")
    assert result["violation"] is None


def test_every_transition_is_logged_as_a_state_transition_event(tmp_path):
    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    enter_state(run_dir, "map")

    events = [e for e in _events(run_dir) if e["family"] == "state_transition" and e["kind"] == "entered"]
    kinds = [(e["state"], e["from"]) for e in events]
    assert ("frame", None) in kinds
    assert ("map", "frame") in kinds


def test_unrecognized_state_raises(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(StateMachineError):
        enter_state(run_dir, "not-a-real-state")
