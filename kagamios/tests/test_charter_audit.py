import pytest

from kagami.events import append_event
from kagami.kernel.charter_audit import audit_charter_violations
from kagami.kernel.historian import HistorianError, historian_write
from kagami.kernel.skeptic import SkepticError, skeptic_write
from kagami.store.artifact import accept_artifact, create_artifact, review_artifact


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
            "skeptic_proposed_an_alternative": [],
            "historian_spoke_outside_evolution": [],
            "non_scout_touched_raw_corpus": [],
        },
    }


def test_audit_surfaces_a_real_skeptic_write_scope_violation(tmp_path):
    _accept_a_gap_register(tmp_path)
    candidate = create_artifact(
        tmp_path, "candidate-direction", _base_fields(), sections={"direction": "x", "red_team_notes": ""}
    )

    with pytest.raises(SkepticError):
        skeptic_write(tmp_path, "candidate-direction", candidate["id"], "direction", "a new proposed direction")

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 1
    violations = result["violations"]["skeptic_proposed_an_alternative"]
    assert len(violations) == 1
    assert violations[0]["role"] == "skeptic"
    assert violations[0]["artifact_id"] == candidate["id"]


def test_audit_surfaces_a_real_historian_write_scope_violation(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )

    with pytest.raises(HistorianError):
        historian_write(tmp_path, dossier["id"], "frontier", "off-limits content")

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 1
    violations = result["violations"]["historian_spoke_outside_evolution"]
    assert len(violations) == 1
    assert violations[0]["role"] == "historian"
    assert violations[0]["artifact_id"] == dossier["id"]


def test_audit_surfaces_historian_frontier_speculation_inside_evolution(tmp_path):
    dossier = create_artifact(
        tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x", "frontier": "y"}
    )

    with pytest.raises(HistorianError):
        historian_write(tmp_path, dossier["id"], "evolution", "this could enable a new class of methods")

    result = audit_charter_violations(tmp_path)
    assert len(result["violations"]["historian_spoke_outside_evolution"]) == 1


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


def test_audit_does_not_flag_a_scout_retrieval_llm_call(tmp_path):
    append_event(tmp_path, "llm_call", {"role": "scout", "operation_class": "corpus_search"})

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0


def test_audit_ignores_llm_calls_from_other_roles_when_checking_scout_scope(tmp_path):
    append_event(tmp_path, "llm_call", {"role": "historian", "operation_class": "draft"})

    result = audit_charter_violations(tmp_path)
    assert result["violation_count"] == 0
