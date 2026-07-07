import re
from pathlib import Path

import pytest

from kagami.events import append_event
from kagami.kernel.charter_audit import SCOUT_ALLOWED_OPERATION_CLASSES, audit_charter_violations
from kagami.kernel.historian import HistorianError, historian_write
from kagami.kernel.skeptic import SkepticError, skeptic_write
from kagami.store.artifact import accept_artifact, create_artifact, review_artifact

SCOUT_CHARTER_PATH = Path(__file__).resolve().parent.parent / "agents" / "scout.md"


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _accept_a_gap_register(run_dir):
    gap = create_artifact(run_dir, "gap-register", _base_fields(), sections={"statement": "x"})
    review_artifact(run_dir, "gap-register", gap["id"])
    accept_artifact(run_dir, "gap-register", gap["id"], "\n".join(f"line {i}" for i in range(6)))


def test_audit_returns_zero_matches_when_no_violations_occurred(tmp_path):
    result = audit_charter_violations(tmp_path)
    assert result == {
        "ok": True,
        "violation_count": 0,
        "violations": {
            "scout_produced_interpretation": [],
            "non_scout_touched_raw_corpus": [],
        },
        "refusals_held": 0,
        "refusals": {
            "skeptic_proposed_an_alternative": [],
            "historian_spoke_outside_evolution": [],
        },
    }


def test_audit_surfaces_a_refused_skeptic_write_as_a_refusal_not_a_violation(tmp_path):
    """A guard doing its job (FR-27) must not read as a breach that
    happened — the write never landed, so it belongs in `refusals_held`,
    never `violation_count` (docs/dogfooding-review.md finding 5)."""
    _accept_a_gap_register(tmp_path)
    candidate = create_artifact(
        tmp_path, "candidate-direction", _base_fields(), sections={"direction": "x", "red_team_notes": ""}
    )

    with pytest.raises(SkepticError):
        skeptic_write(tmp_path, "candidate-direction", candidate["id"], "direction", "a new proposed direction")

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0
    assert result["refusals_held"] == 1
    refusals = result["refusals"]["skeptic_proposed_an_alternative"]
    assert len(refusals) == 1
    assert refusals[0]["role"] == "skeptic"
    assert refusals[0]["artifact_id"] == candidate["id"]


def test_audit_surfaces_a_refused_historian_write_as_a_refusal_not_a_violation(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )

    with pytest.raises(HistorianError):
        historian_write(tmp_path, dossier["id"], "frontier", "off-limits content")

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0
    assert result["refusals_held"] == 1
    refusals = result["refusals"]["historian_spoke_outside_evolution"]
    assert len(refusals) == 1
    assert refusals[0]["role"] == "historian"
    assert refusals[0]["artifact_id"] == dossier["id"]


def test_audit_surfaces_historian_frontier_speculation_inside_evolution_as_a_refusal(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )

    with pytest.raises(HistorianError):
        historian_write(tmp_path, dossier["id"], "evolution", "this could enable a new class of methods")

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0
    assert len(result["refusals"]["historian_spoke_outside_evolution"]) == 1


def test_audit_does_not_flag_a_legitimate_skeptic_or_historian_write(tmp_path):
    _accept_a_gap_register(tmp_path)
    candidate = create_artifact(
        tmp_path, "candidate-direction", _base_fields(), sections={"direction": "x", "red_team_notes": ""}
    )
    skeptic_write(tmp_path, "candidate-direction", candidate["id"], "red_team_notes", "weak evidence")

    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )
    historian_write(tmp_path, dossier["id"], "evolution", "the field began with X in 2015")

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0
    assert result["refusals_held"] == 0


def test_audit_flags_a_non_scout_role_touching_the_raw_corpus(tmp_path):
    append_event(
        tmp_path, "retrieval",
        {"kind": "corpus_search", "role": "cartographer", "provider": "stub", "query": "x", "paper_ids": []},
    )

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 1
    assert len(result["violations"]["non_scout_touched_raw_corpus"]) == 1


def test_audit_does_not_flag_a_scout_corpus_search(tmp_path):
    append_event(
        tmp_path, "retrieval",
        {"kind": "corpus_search", "role": "scout", "provider": "stub", "query": "x", "paper_ids": []},
    )

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0


def test_audit_flags_a_non_scout_role_touching_the_raw_corpus_via_expand(tmp_path):
    """FR-50: corpus_expand is Scout's second sanctioned corpus-touching
    action — a non-Scout role's expand event must be caught by the same
    defense-in-depth check as corpus_search."""
    append_event(
        tmp_path, "retrieval",
        {"kind": "corpus_expand", "role": "historian", "provider": "stub", "origin_paper_id": "ppr-x", "edges": []},
    )

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 1
    assert len(result["violations"]["non_scout_touched_raw_corpus"]) == 1


def test_audit_does_not_flag_a_scout_corpus_expand(tmp_path):
    append_event(
        tmp_path, "retrieval",
        {"kind": "corpus_expand", "role": "scout", "provider": "stub", "origin_paper_id": "ppr-x", "edges": []},
    )

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0


def test_audit_flags_scout_llm_call_outside_the_retrieval_allowlist(tmp_path):
    append_event(tmp_path, "llm_call", {"role": "scout", "operation_class": "draft"})

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 1
    assert len(result["violations"]["scout_produced_interpretation"]) == 1


def test_audit_does_not_flag_a_scout_paper_card_extraction_llm_call(tmp_path):
    """paper_card_extraction is the one operation class Scout's own charter
    (agents/scout.md) directs it to report — charter-mandated, not a
    violation (docs/dogfooding-review.md finding 5)."""
    append_event(tmp_path, "llm_call", {"role": "scout", "operation_class": "paper_card_extraction"})

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0


def test_audit_ignores_llm_calls_from_other_roles_when_checking_scout_scope(tmp_path):
    append_event(tmp_path, "llm_call", {"role": "historian", "operation_class": "draft"})

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0


def test_scout_allowed_operation_classes_matches_operation_classes_named_in_the_charter():
    """Pinning test (docs/dogfooding-review.md finding 5): the allowlist and
    agents/scout.md drifted apart once already — paper_card_extraction was
    charter-mandated but absent from SCOUT_ALLOWED_OPERATION_CLASSES, so
    every compliant Scout run reported 13+ false violations. This fails the
    moment either file changes without the other."""
    charter_text = SCOUT_CHARTER_PATH.read_text()
    named_classes = set(re.findall(r"--operation-class\s+([\w-]+)", charter_text))
    assert named_classes, "expected agents/scout.md to name at least one --operation-class"
    assert named_classes == SCOUT_ALLOWED_OPERATION_CLASSES


def test_replaying_run_1s_event_log_reports_zero_violations_and_one_refusal_held(tmp_path):
    """Replays the charter-relevant shape of run-2afeef8fb9a9 (docs/
    dogfooding-review.md finding 5): 13 Scout paper_card_extraction calls
    that the old allowlist misreported as violations, and one Historian
    write the chokepoint correctly refused-and-blocked (frontier-facing
    speculation, FR-28). Corrected audit: violation_count == 0,
    refusals_held == 1 — trusting `violation_count == 0` requires this to
    hold against the real run that first exposed the bug, not just synthetic
    events."""
    for call_id in range(13):
        append_event(
            tmp_path,
            "llm_call",
            {
                "role": "scout",
                "operation_class": "paper_card_extraction",
                "model_tier": "cheap-model",
                "call_id": f"call-{call_id}",
            },
        )
    append_event(
        tmp_path,
        "gate_event",
        {
            "kind": "generation_window_violation",
            "role": "historian",
            "detail": "frontier-facing speculation detected: 'this suggests a promising direction' (FR-28)",
            "artifact_id": "art-f969a75f8b10",
        },
    )

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0
    assert result["refusals_held"] == 1
