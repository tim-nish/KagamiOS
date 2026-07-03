from kagami.events import append_event
from kagami.kernel.frame import complete_frame
from kagami.kernel.metrics import (
    compute_decision_block,
    compute_derived_metrics,
    compute_override_profile,
    compute_override_rate,
    compute_question_economics,
    compute_token_ledger,
    compute_unprimed_vs_final_diff_at_frame,
    count_full_pull_after_summary,
)
from kagami.kernel.repair import apply_tier2_repair, repair_artifact
from kagami.store import ledger
from kagami.store.artifact import count_provisional, create_artifact, mark_dependents_stale, pin_dependency


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


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def test_compute_question_economics_returns_an_empty_list_with_no_ledger(tmp_path):
    assert compute_question_economics(tmp_path) == []


def test_compute_question_economics_reads_ledger_fields_and_revision_count(tmp_path):
    result = ledger.emit_batch(
        tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu", "default": "1"}]
    )
    q_id = result["ids"][0]
    ledger.answer_question(tmp_path, q_id, "2")
    ledger.revise_answer(tmp_path, q_id, "3")

    entries = compute_question_economics(tmp_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["id"] == q_id
    assert entry["target"] == "field-map.scope"
    assert entry["leverage_class"] == "L2"
    assert entry["revision_count"] == 1
    assert entry["default_applied"] is False


def test_compute_question_economics_counts_consumption_and_staleness_cascade(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "x"})
    dependent = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"statement": "x"},
    )

    result = ledger.emit_batch(
        tmp_path, [{"target": "gap-register.statement", "leverage_class": "L2", "form": "menu"}]
    )
    q_id = result["ids"][0]
    ledger.answer_question(tmp_path, q_id, "an answer")
    ledger.consume_answer(tmp_path, q_id, "gap-register", dependent["id"])

    entry = next(e for e in compute_question_economics(tmp_path) if e["id"] == q_id)
    assert entry["consumed_by_count"] == 1

    mark_dependents_stale(tmp_path, q_id, dependency_new_version=2)
    entry = next(e for e in compute_question_economics(tmp_path) if e["id"] == q_id)
    assert entry["staleness_cascade_size"] == 1


def test_compute_token_ledger_aggregates_llm_calls_by_role_and_operation_class(tmp_path):
    append_event(
        tmp_path, "llm_call",
        {"role": "historian", "operation_class": "draft", "tokens_in": 100, "tokens_out": 50, "cache_hit": True},
    )
    append_event(
        tmp_path, "llm_call",
        {"role": "historian", "operation_class": "draft", "tokens_in": 200, "tokens_out": 20, "cache_hit": False},
    )
    append_event(
        tmp_path, "llm_call",
        {"role": "skeptic", "operation_class": "critique", "tokens_in": 10, "tokens_out": 10, "cache_hit": False},
    )

    ledger_metrics = compute_token_ledger(tmp_path)
    historian_bucket = ledger_metrics["spend_by_role_and_operation_class"]["historian::draft"]
    assert historian_bucket == {"calls": 2, "tokens_in": 300, "tokens_out": 70, "cache_hits": 1}
    assert ledger_metrics["spend_by_role_and_operation_class"]["skeptic::critique"]["calls"] == 1


def test_compute_token_ledger_computes_repair_vs_regen_ratio(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )
    repair_artifact(tmp_path, "cluster-dossier", dossier["id"])  # not stale -> tier 0

    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "x"})
    stale_dossier = create_artifact(
        tmp_path,
        "cluster-dossier",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"evolution": "x", "frontier": "y"},
    )
    mark_dependents_stale(tmp_path, dep["id"], dependency_new_version=2)
    apply_tier2_repair(tmp_path, "cluster-dossier", stale_dossier["id"], {"frontier": "repaired"})

    ledger_metrics = compute_token_ledger(tmp_path)
    assert ledger_metrics["repair_vs_regen"] == {"repaired_at_tier0": 1, "regenerated_at_tier2": 1}


def test_compute_override_profile_covers_every_type_present_in_the_run(tmp_path):
    create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "x"})
    create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})

    profile = compute_override_profile(tmp_path)
    assert set(profile) == {"field-map", "gap-register"}
    assert profile["field-map"]["type"] == "field-map"


def test_compute_override_profile_is_empty_with_no_artifacts(tmp_path):
    assert compute_override_profile(tmp_path) == {}


def test_compute_unprimed_vs_final_diff_at_frame_is_none_before_frame_is_accepted(tmp_path):
    assert compute_unprimed_vs_final_diff_at_frame(tmp_path) is None


def test_compute_unprimed_vs_final_diff_at_frame_reports_the_comparison_once_accepted(tmp_path):
    complete_frame(
        tmp_path,
        unprimed_answer="a raw hunch about X",
        scope_answer="1",
        fields={
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "", "in_scope_readings": ["ppr-1"], "exclusions": [], "hard_constraints": [],
        },
        sections={"intuition_restated": "a refined framing of X", "unprimed_hunch": "a raw hunch about X"},
        summary="\n".join(f"line {i}" for i in range(6)),
    )

    diff = compute_unprimed_vs_final_diff_at_frame(tmp_path)
    assert diff["unprimed_hunch"] == "a raw hunch about X"
    assert diff["final_restated"] == "a refined framing of X"
    assert diff["differs"] is True


def test_compute_decision_block_leaves_decide_only_fields_empty(tmp_path):
    block = compute_decision_block(tmp_path)
    assert block["candidate_origins"] == []
    assert block["falsifiable_claims"] == []
    assert block["provisional_count"] == count_provisional(tmp_path)


def test_compute_derived_metrics_provisional_count_matches_count_provisional(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )
    from kagami.store.artifact import flag_provisional

    flag_provisional(tmp_path, "cluster-dossier", dossier["id"])

    metrics = compute_derived_metrics(tmp_path)
    assert metrics["decision_block"]["provisional_count"] == count_provisional(tmp_path) == 1


def test_compute_derived_metrics_is_deterministic_across_repeated_calls(tmp_path):
    create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "x"})
    ledger.emit_batch(tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu"}])

    first = compute_derived_metrics(tmp_path)
    second = compute_derived_metrics(tmp_path)
    assert first == second
