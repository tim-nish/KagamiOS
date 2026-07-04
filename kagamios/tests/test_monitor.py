import json

import pytest

from kagami.kernel.derived_state import set_depth_budgets
from kagami.kernel.monitor import MonitorError, mark_dormant, monitor_sweep
from kagami.kernel.state_machine import get_state_cache
from kagami.store.artifact import create_artifact, mark_dependents_stale, pin_dependency
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-monitor"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def test_mark_dormant_refuses_without_explicit_revival_conditions(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(MonitorError):
        mark_dormant(run_dir, "")


def test_mark_dormant_records_revival_conditions_and_enters_dormant_state(tmp_path):
    run_dir = _open(tmp_path)

    result = mark_dormant(run_dir, "revisit if a related paper appears")
    assert result["ok"] is True
    assert result["revival_conditions"] == "revisit if a related paper appears"
    assert get_state_cache(run_dir)["current_state"] == "dormant"

    events = _events(run_dir)
    marked = [e for e in events if e.get("kind") == "marked_dormant"]
    assert len(marked) == 1
    assert marked[0]["family"] == "gate_event"
    assert marked[0]["revival_conditions"] == "revisit if a related paper appears"


def test_monitor_sweep_is_a_noop_for_a_run_that_was_never_parked(tmp_path):
    run_dir = _open(tmp_path)
    assert monitor_sweep(run_dir) == {"ok": True, "swept": False, "reopened": False}


def test_monitor_sweep_checks_but_does_not_reopen_a_dormant_run_with_no_staleness(tmp_path):
    run_dir = _open(tmp_path)
    mark_dormant(run_dir, "revisit if a related paper appears")

    result = monitor_sweep(run_dir)
    assert result == {"ok": True, "swept": True, "reopened": False, "stale_artifact_ids": []}

    events = [e for e in _events(run_dir) if e.get("kind") == "dormant_monitoring_checked"]
    assert len(events) == 1


def test_monitor_sweep_reopens_a_dormant_run_at_the_affected_state_on_a_staling_alert(tmp_path):
    run_dir = _open(tmp_path)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")

    dep = create_artifact(run_dir, "field-map", _base_fields(), sections={"cluster_name": "x"})
    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"evolution": "x", "frontier": "y"},
    )
    mark_dormant(run_dir, "revisit if a related paper appears")

    mark_dependents_stale(run_dir, dep["id"], dependency_new_version=2)

    result = monitor_sweep(run_dir)
    assert result["ok"] is True
    assert result["swept"] is True
    assert result["reopened"] is True
    assert result["affected_state"] == "deepen"
    assert result["stale_artifact_ids"] == [dossier["id"]]

    assert get_state_cache(run_dir)["current_state"] == "deepen"

    events = [e for e in _events(run_dir) if e.get("kind") == "staling_alert_reopened_run"]
    assert len(events) == 1
    assert events[0]["was_status"] == "dormant"
    assert events[0]["affected_state"] == "deepen"


def test_monitor_sweep_reopening_is_recorded_on_the_manifest(tmp_path):
    run_dir = _open(tmp_path)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")
    dep = create_artifact(run_dir, "field-map", _base_fields(), sections={"cluster_name": "x"})
    create_artifact(
        run_dir,
        "cluster-dossier",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"evolution": "x", "frontier": "y"},
    )
    mark_dormant(run_dir, "revisit if a related paper appears")
    mark_dependents_stale(run_dir, dep["id"], dependency_new_version=2)
    monitor_sweep(run_dir)

    import yaml

    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())
    assert manifest["monitoring"]["status"] == "reopened"
    assert manifest["monitoring"]["reopened_at_state"] == "deepen"


def test_a_new_run_never_reuses_a_dormant_runs_state_or_monitoring(tmp_path):
    from kagami.kernel.entry import start_run_from_entry

    dormant_run = _open(tmp_path, run_id="run-dormant")
    mark_dormant(dormant_run, "revisit if a related paper appears")

    fresh_run = _open(tmp_path, run_id="run-fresh")
    start_run_from_entry(fresh_run, "intuition-first", "a completely unrelated hunch")

    assert get_state_cache(fresh_run)["current_state"] == "frame"
    assert monitor_sweep(fresh_run) == {"ok": True, "swept": False, "reopened": False}
    assert get_state_cache(dormant_run)["current_state"] == "dormant"
