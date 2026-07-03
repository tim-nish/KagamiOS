import json

from kagami.kernel.frontier import select_and_log, select_next


def test_blocking_next_gate_wins_over_everything_else():
    candidates = {
        "blocking_next_gate": ["gate-item"],
        "stale_repairs_active_path": ["repair-item"],
        "checklist_holes": ["hole-item"],
        "deferred_work": ["deferred-item"],
    }
    assert select_next(candidates) == {"priority_class": "blocking_next_gate", "item": "gate-item"}


def test_falls_through_to_next_nonempty_class_in_fixed_order():
    candidates = {
        "blocking_next_gate": [],
        "stale_repairs_active_path": [],
        "checklist_holes": ["hole-item"],
        "deferred_work": ["deferred-item"],
    }
    assert select_next(candidates) == {"priority_class": "checklist_holes", "item": "hole-item"}


def test_no_candidates_anywhere_returns_none_class():
    assert select_next({}) == {"priority_class": None, "item": None}


def test_select_and_log_writes_frontier_decision_event_with_priority_class(tmp_path):
    candidates = {"deferred_work": ["only-item"]}
    decision = select_and_log(tmp_path, candidates)
    assert decision["priority_class"] == "deferred_work"

    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["family"] == "frontier_decision"
    assert event["priority_class"] == "deferred_work"
