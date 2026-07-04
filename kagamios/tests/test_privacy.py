import json

import pytest

from kagami.events import append_event
from kagami.kernel.charter_audit import audit_charter_violations
from kagami.kernel.metrics import compute_derived_metrics
from kagami.kernel.monitor import mark_dormant
from kagami.kernel.privacy import PrivacyError, generate_shared_payload, sharing_enabled
from kagami.kernel.skeptic import record_skeptic_critique
from kagami.store import ledger
from kagami.store.artifact import create_artifact
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-privacy"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id


def test_sharing_enabled_defaults_to_off_with_no_config(tmp_path):
    assert sharing_enabled({}) is False


def test_sharing_enabled_is_off_unless_explicitly_true(tmp_path):
    assert sharing_enabled({"sharing_enabled": False}) is False
    assert sharing_enabled({"literature_provider": "arxiv"}) is False


def test_sharing_enabled_only_turns_on_via_explicit_true(tmp_path):
    assert sharing_enabled({"sharing_enabled": True}) is True


def test_generate_shared_payload_refuses_when_sharing_is_disabled(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(PrivacyError):
        generate_shared_payload(run_dir, {})

    with pytest.raises(PrivacyError):
        generate_shared_payload(run_dir, {"sharing_enabled": False})


def test_generate_shared_payload_produces_only_shapes_counts_and_classes(tmp_path):
    run_dir = _open(tmp_path)
    append_event(run_dir, "artifact_event", {"kind": "accepted", "artifact_type": "gap-register", "artifact_id": "art-1"})
    append_event(run_dir, "artifact_event", {"kind": "accepted", "artifact_type": "gap-register", "artifact_id": "art-2"})
    append_event(run_dir, "llm_call", {"role": "historian", "operation_class": "draft"})
    append_event(run_dir, "question_event", {"kind": "asked", "leverage_class": "L2"})

    payload = generate_shared_payload(run_dir, {"sharing_enabled": True})

    assert payload["ok"] is True
    assert payload["event_count"] == 5  # includes open_run's own 'run_opened' state_transition event
    assert payload["event_class_counts"]["artifact_event::accepted"] == 2
    assert payload["event_class_counts"]["llm_call::None"] == 1
    assert payload["role_counts"] == {"historian": 1}
    assert payload["leverage_class_counts"] == {"L2": 1}
    assert payload["artifact_type_counts"] == {"gap-register": 2}


def test_generate_shared_payload_never_leaks_free_text_content(tmp_path):
    """FR-39: question text, artifact content, and paper identities never
    leave the local store — plant distinctive content across several event
    kinds and assert none of it survives into the shared payload."""
    run_dir = _open(tmp_path)

    secret_revival_conditions = "REVISIT-IF-COMPETITOR-X-PUBLISHES-SECRET-METHOD"
    mark_dormant(run_dir, secret_revival_conditions)

    secret_query = "SECRET-RESEARCH-QUERY-ABOUT-UNPUBLISHED-METHOD"
    append_event(
        run_dir, "retrieval",
        {"kind": "corpus_search", "role": "scout", "provider": "stub", "query": secret_query, "paper_ids": ["ppr-secret-1"]},
    )

    secret_objection = "SECRET-OBJECTION-REVEALING-THE-CANDIDATE-DIRECTION"
    record_skeptic_critique(run_dir, "field-map", "art-x", secret_objection, ["ppr-secret-2"])

    secret_target = "gap-register.SECRET_FIELD_NAME"
    result = ledger.emit_batch(run_dir, [{"target": secret_target, "leverage_class": "L2", "form": "menu"}])
    ledger.answer_question(run_dir, result["ids"][0], "SECRET-ANSWER-TEXT")

    payload = generate_shared_payload(run_dir, {"sharing_enabled": True})
    serialized = json.dumps(payload)

    for secret in (
        secret_revival_conditions,
        secret_query,
        "ppr-secret-1",
        secret_objection,
        "ppr-secret-2",
        secret_target,
        "SECRET-ANSWER-TEXT",
        "art-x",
    ):
        assert secret not in serialized


def test_design_analytics_features_work_fully_without_sharing_enabled(tmp_path):
    """NFR4: no design-analytics feature may require sharing to function
    for a single researcher — compute_derived_metrics and
    audit_charter_violations never consult the sharing flag at all."""
    run_dir = _open(tmp_path)
    create_artifact(
        run_dir, "field-map",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"cluster_name": "x"},
    )

    metrics = compute_derived_metrics(run_dir)
    audit = audit_charter_violations(run_dir)

    assert metrics["ok"] is True
    assert audit["ok"] is True
