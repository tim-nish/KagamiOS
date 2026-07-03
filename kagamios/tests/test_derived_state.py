import json

import pytest

from kagami.kernel.derived_state import (
    DepthBudgetError,
    assert_depth_budgets_set,
    compute_cluster_state,
    compute_run_nominal_state,
    detect_budget_exhaustion,
    get_depth_budgets,
    set_depth_budgets,
)
from kagami.store.artifact import create_artifact, review_artifact
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-derived"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _create_field_map(run_dir, cluster_name="cluster A"):
    return create_artifact(run_dir, "field-map", _base_fields(), sections={"cluster_name": cluster_name})


def test_cluster_still_draft_is_derived_as_map_state(tmp_path):
    run_dir = _open(tmp_path)
    fm = _create_field_map(run_dir)
    assert compute_cluster_state(run_dir, fm["id"]) == "map"


def test_cluster_reviewed_without_a_dossier_is_derived_as_deepen_state(tmp_path):
    run_dir = _open(tmp_path)
    fm = _create_field_map(run_dir)
    review_artifact(run_dir, "field-map", fm["id"])
    assert compute_cluster_state(run_dir, fm["id"]) == "deepen"


def test_cluster_with_an_accepted_dossier_is_derived_past_deepen(tmp_path):
    from kagami.store.artifact import accept_artifact, pin_dependency

    run_dir = _open(tmp_path)
    fm = _create_field_map(run_dir)
    review_artifact(run_dir, "field-map", fm["id"])

    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        _base_fields(depends_on=[pin_dependency(fm["id"], 1)]),
        sections={"evolution": "founding problem etc"},
    )
    review_artifact(run_dir, "cluster-dossier", dossier["id"])
    accept_artifact(run_dir, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))

    assert compute_cluster_state(run_dir, fm["id"]) == "synthesize"


def test_two_clusters_can_be_in_different_states_simultaneously(tmp_path):
    run_dir = _open(tmp_path)
    fm_a = _create_field_map(run_dir, "cluster A")
    fm_b = _create_field_map(run_dir, "cluster B")
    review_artifact(run_dir, "field-map", fm_b["id"])

    assert compute_cluster_state(run_dir, fm_a["id"]) == "map"
    assert compute_cluster_state(run_dir, fm_b["id"]) == "deepen"


def test_run_nominal_state_is_the_modal_cluster_state(tmp_path):
    run_dir = _open(tmp_path)
    _create_field_map(run_dir, "cluster A")
    _create_field_map(run_dir, "cluster B")
    fm_c = _create_field_map(run_dir, "cluster C")
    review_artifact(run_dir, "field-map", fm_c["id"])

    result = compute_run_nominal_state(run_dir)
    assert result["nominal_state"] == "map"  # 2 of 3 clusters are still in map


def test_run_nominal_state_falls_back_to_state_cache_with_no_clusters(tmp_path):
    from kagami.kernel.state_machine import enter_state

    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    result = compute_run_nominal_state(run_dir)
    assert result["nominal_state"] == "frame"


def test_set_depth_budgets_records_and_is_revisable_at_any_point(tmp_path):
    run_dir = _open(tmp_path)
    outcome = set_depth_budgets(run_dir, ["cluster-1", "cluster-2"], papers_per_cluster=5, time_horizon="1 week")
    assert outcome["ok"] is True
    assert get_depth_budgets(run_dir)["papers_per_cluster"] == 5

    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=10, time_horizon="2 weeks")
    assert get_depth_budgets(run_dir)["papers_per_cluster"] == 10


def test_depth_budgets_log_a_budget_event(tmp_path):
    run_dir = _open(tmp_path)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    budget_events = [e for e in events if e["family"] == "budget_event"]
    assert len(budget_events) == 1
    assert budget_events[0]["kind"] == "depth_budgets_set"


def test_assert_depth_budgets_set_raises_when_unset(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(DepthBudgetError):
        assert_depth_budgets_set(run_dir)

    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")
    assert_depth_budgets_set(run_dir)  # does not raise


def test_deepen_cannot_be_entered_without_depth_budgets(tmp_path):
    from kagami.kernel.state_machine import StateMachineError, enter_state

    run_dir = _open(tmp_path)
    enter_state(run_dir, "frame")
    enter_state(run_dir, "map")

    with pytest.raises(StateMachineError):
        enter_state(run_dir, "deepen")

    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")
    result = enter_state(run_dir, "deepen")
    assert result["ok"] is True


def test_exhaustion_below_budget_does_not_ask(tmp_path):
    run_dir = _open(tmp_path)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")

    result = detect_budget_exhaustion(run_dir, "cluster-1", papers_read_count=3)
    assert result == {"ok": True, "exhausted": False}


def test_exhaustion_at_budget_asks_exactly_one_extend_or_proceed_question(tmp_path):
    run_dir = _open(tmp_path)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")

    result = detect_budget_exhaustion(run_dir, "cluster-1", papers_read_count=5)
    assert result["exhausted"] is True
    assert result["newly_asked"] is True

    import yaml

    entry = yaml.safe_load((run_dir / "ledger" / f"{result['question_id']}.yaml").read_text())
    assert entry["form"] == "confirm"
    assert entry["leverage_class"] == "L6"
    assert entry["target"] == "depth-budget.cluster-1"


def test_repeated_exhaustion_check_does_not_duplicate_the_question(tmp_path):
    run_dir = _open(tmp_path)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")

    first = detect_budget_exhaustion(run_dir, "cluster-1", papers_read_count=5)
    second = detect_budget_exhaustion(run_dir, "cluster-1", papers_read_count=6)

    assert second["question_id"] == first["question_id"]
    assert second["newly_asked"] is False

    ledger_files = list((run_dir / "ledger").glob("*.yaml"))
    assert len(ledger_files) == 1


def test_exhaustion_check_requires_budgets_to_already_be_set(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(DepthBudgetError):
        detect_budget_exhaustion(run_dir, "cluster-1", papers_read_count=1)
