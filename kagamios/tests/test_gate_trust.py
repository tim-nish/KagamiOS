import json

import pytest

from kagami.kernel.gate_trust import (
    GateTrustError,
    approve_gate_loosening,
    is_gate_loosened,
    propose_gate_loosening,
)
from kagami.store.artifact import ArtifactError, accept_artifact, create_artifact, review_artifact
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-gate-trust"):
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


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_propose_gate_loosening_cites_the_aggregated_statistic(tmp_path):
    run_dir = _open(tmp_path)
    create_artifact(run_dir, "cluster-dossier", _base_fields(), sections={"evolution": "x"})

    result = propose_gate_loosening(run_dir, "cluster-dossier")

    assert result["ok"] is True
    assert result["type"] == "cluster-dossier"
    assert "statistic" in result
    assert result["statistic"]["type"] == "cluster-dossier"

    events = _events(run_dir)
    proposed = [e for e in events if e.get("kind") == "gate_loosening_proposed"]
    assert len(proposed) == 1
    assert proposed[0]["family"] == "gate_event"
    assert proposed[0]["statistic"] == result["statistic"]


@pytest.mark.parametrize(
    "type_slug", ["inquiry-frame", "field-map", "gap-register", "candidate-direction", "direction-decision"]
)
def test_propose_gate_loosening_refuses_a_type_carrying_a_constitutive_field(tmp_path, type_slug):
    run_dir = _open(tmp_path)
    with pytest.raises(GateTrustError):
        propose_gate_loosening(run_dir, type_slug)


@pytest.mark.parametrize(
    "type_slug", ["inquiry-frame", "field-map", "gap-register", "candidate-direction", "direction-decision"]
)
def test_approve_gate_loosening_refuses_a_type_carrying_a_constitutive_field(tmp_path, type_slug):
    run_dir = _open(tmp_path)
    with pytest.raises(GateTrustError):
        approve_gate_loosening(run_dir, type_slug)

    assert is_gate_loosened(run_dir, type_slug) is False


def test_gate_remains_strict_until_a_proposal_is_approved(tmp_path):
    run_dir = _open(tmp_path)
    dossier = create_artifact(run_dir, "cluster-dossier", _base_fields(), sections={"evolution": "x"})
    propose_gate_loosening(run_dir, "cluster-dossier")

    assert is_gate_loosened(run_dir, "cluster-dossier") is False
    with pytest.raises(ArtifactError):
        accept_artifact(run_dir, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))


def test_approve_gate_loosening_records_a_discrete_event_and_relaxes_the_gate(tmp_path):
    run_dir = _open(tmp_path)
    dossier = create_artifact(run_dir, "cluster-dossier", _base_fields(), sections={"evolution": "x"})

    result = approve_gate_loosening(run_dir, "cluster-dossier")
    assert result == {"ok": True, "type": "cluster-dossier", "loosened": True, "statistic": result["statistic"]}
    assert is_gate_loosened(run_dir, "cluster-dossier") is True

    events = _events(run_dir)
    approved = [e for e in events if e.get("kind") == "gate_loosening_approved"]
    assert len(approved) == 1
    assert approved[0]["family"] == "gate_event"
    assert approved[0]["artifact_type"] == "cluster-dossier"

    # the gate is loosened: accept succeeds straight from 'draft', no review_artifact call needed
    outcome = accept_artifact(run_dir, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))
    assert outcome["ok"] is True

    notifications = [e for e in _events(run_dir) if e.get("kind") == "gate_loosening_notification"]
    assert len(notifications) == 1
    assert notifications[0]["artifact_id"] == dossier["id"]


def test_approving_one_type_does_not_loosen_the_gate_for_another(tmp_path):
    run_dir = _open(tmp_path)
    approve_gate_loosening(run_dir, "cluster-dossier")
    assert is_gate_loosened(run_dir, "landscape-synthesis") is False

    synth = create_artifact(run_dir, "landscape-synthesis", _base_fields(), sections={})
    with pytest.raises(ArtifactError):
        accept_artifact(run_dir, "landscape-synthesis", synth["id"], "\n".join(f"l{i}" for i in range(6)))


def test_reviewed_artifacts_still_accept_normally_after_a_gate_is_loosened(tmp_path):
    run_dir = _open(tmp_path)
    dossier = create_artifact(run_dir, "cluster-dossier", _base_fields(), sections={"evolution": "x"})
    approve_gate_loosening(run_dir, "cluster-dossier")
    review_artifact(run_dir, "cluster-dossier", dossier["id"])

    outcome = accept_artifact(run_dir, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))
    assert outcome["ok"] is True

    # reviewed-then-accepted is not itself a gate-loosening notification
    notifications = [e for e in _events(run_dir) if e.get("kind") == "gate_loosening_notification"]
    assert notifications == []
