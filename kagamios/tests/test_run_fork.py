import json

import pytest
import yaml

from kagami.kernel.derived_state import set_depth_budgets
from kagami.kernel.metrics import compute_rediscovery_rate
from kagami.kernel.scout import search_corpus
from kagami.kernel.state_machine import enter_state
from kagami.corpus.provider import LiteratureProvider
from kagami.schema_version import CURRENT_SCHEMA_REGISTRY_VERSION
from kagami.store.artifact import create_artifact
from kagami.store.markdown_doc import parse_document
from kagami.store.run import RunForkError, fork_run, open_run


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
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


class _StubProvider(LiteratureProvider):
    name = "stub"

    def __init__(self, results):
        self._results = results

    def search(self, query, limit=20):
        return self._results

    def paper_metadata(self, canonical_key):
        raise NotImplementedError

    def citation_graph(self, canonical_key):
        raise NotImplementedError


def _build_parent_through_map(run_dir):
    """entry -> frame (with content) -> map (with content); the parent's
    `current_state` ends at 'map'."""
    enter_state(run_dir, "frame")
    profile = create_artifact(run_dir, "researcher-profile", _base_fields(), sections={"notes": "background"})
    frame = create_artifact(
        run_dir, "inquiry-frame", _base_fields(),
        sections={"intuition_restated": "x", "unprimed_hunch": "y"},
    )
    enter_state(run_dir, "map")
    field_map = create_artifact(run_dir, "field-map", _base_fields(), sections={"cluster_name": "cluster A"})
    return {"profile": profile, "frame": frame, "field_map": field_map}


def _build_parent_through_deepen(run_dir):
    """Extends `_build_parent_through_map` on into Deepen, with a Cluster
    Dossier actually created — the parent's `current_state` ends at
    'deepen'."""
    ids = _build_parent_through_map(run_dir)
    set_depth_budgets(run_dir, ["cluster-1"], papers_per_cluster=5, time_horizon="1 week")
    enter_state(run_dir, "deepen")
    dossier = create_artifact(
        run_dir, "cluster-dossier",
        _base_fields(representative_papers=[
            {"paper_id": "ppr-1", "rating": None, "confidence": None, "note": "", "actor": None}
        ]),
        sections={"evolution": ""},
    )
    ids["dossier"] = dossier
    return ids


def _open(tmp_path, run_id):
    output_root = tmp_path / "_out"
    open_run(run_id=run_id, output_root=output_root)
    return output_root / "runs" / run_id, output_root


def test_fork_creates_a_new_run_dir_without_rewriting_the_parent_log(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)
    parent_log_before = (parent_dir / "events.jsonl").read_text()

    result = fork_run("run-parent", "map", run_id="run-child", output_root=output_root)

    assert result["ok"] is True
    assert result["run_id"] == "run-child"
    child_dir = output_root / "runs" / "run-child"
    assert child_dir.is_dir()
    assert child_dir != parent_dir

    # FR-60/AD-11: the parent's own log is byte-identical after the fork —
    # forking only ever reads it.
    assert (parent_dir / "events.jsonl").read_text() == parent_log_before


def test_forked_manifest_records_parent_provenance_and_boundary_state(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    fork_run("run-parent", "map", run_id="run-child", output_root=output_root)

    manifest = yaml.safe_load((output_root / "runs" / "run-child" / "manifest.yaml").read_text())
    assert manifest["parent_run_id"] == "run-parent"
    assert manifest["forked_from_state"] == "map"
    assert manifest["state_cache"]["current_state"] == "map"
    assert manifest["schema_registry_version"] == CURRENT_SCHEMA_REGISTRY_VERSION


def test_fork_copies_artifacts_strictly_before_the_boundary_not_its_own(tmp_path):
    """FR-60: forking 'from deepen' gets everything Frame/Map produced,
    but not the Cluster Dossier — deepen's own output — even though the
    parent has already created one."""
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_deepen(parent_dir)

    fork_run("run-parent", "deepen", run_id="run-child", output_root=output_root)

    child_artifacts = output_root / "runs" / "run-child" / "artifacts"
    assert (child_artifacts / "researcher-profile").is_dir()
    assert (child_artifacts / "inquiry-frame").is_dir()
    assert (child_artifacts / "field-map").is_dir()
    assert not (child_artifacts / "cluster-dossier").exists()


def test_fork_from_frame_copies_only_entry_and_frame_artifacts(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    fork_run("run-parent", "frame", run_id="run-child", output_root=output_root)

    child_artifacts = output_root / "runs" / "run-child" / "artifacts"
    assert (child_artifacts / "researcher-profile").is_dir()
    assert not (child_artifacts / "inquiry-frame").exists()  # frame's own output
    assert not (child_artifacts / "field-map").exists()


def test_forked_artifacts_are_stamped_inherited(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    ids = _build_parent_through_map(parent_dir)

    fork_run("run-parent", "map", run_id="run-child", output_root=output_root)

    child_dir = output_root / "runs" / "run-child"
    current_path = child_dir / "artifacts" / "researcher-profile" / ids["profile"]["id"] / "current.md"
    frontmatter, _ = parse_document(current_path.read_text())
    assert frontmatter["inherited"] is True


def test_forked_artifacts_historical_versions_are_untouched(tmp_path):
    """Only the live `current.md` is stamped `inherited` — the historical
    `v1.md` is copied verbatim, an honest record of the parent's history."""
    parent_dir, output_root = _open(tmp_path, "run-parent")
    ids = _build_parent_through_map(parent_dir)

    fork_run("run-parent", "map", run_id="run-child", output_root=output_root)

    child_dir = output_root / "runs" / "run-child"
    v1_path = child_dir / "artifacts" / "researcher-profile" / ids["profile"]["id"] / "v1.md"
    frontmatter, _ = parse_document(v1_path.read_text())
    assert "inherited" not in frontmatter


def test_fork_refuses_a_boundary_the_parent_never_entered(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    with pytest.raises(RunForkError):
        fork_run("run-parent", "synthesize", output_root=output_root)


def test_fork_refuses_an_invalid_state_name(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    with pytest.raises(RunForkError):
        fork_run("run-parent", "not-a-real-state", output_root=output_root)


def test_fork_refuses_a_nonexistent_parent_run(tmp_path):
    output_root = tmp_path / "_out"
    (output_root / "runs").mkdir(parents=True)

    with pytest.raises(RunForkError):
        fork_run("run-does-not-exist", "map", output_root=output_root)


def test_fork_refuses_a_new_run_id_that_already_exists(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)
    open_run(run_id="run-existing", output_root=output_root)

    with pytest.raises(RunForkError):
        fork_run("run-parent", "map", run_id="run-existing", output_root=output_root)


def test_fork_generates_a_run_id_when_none_provided(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    result = fork_run("run-parent", "map", output_root=output_root)
    assert result["run_id"]
    assert result["run_id"] != "run-parent"
    assert result["run_id"].startswith("run-")


def test_fork_logs_its_own_run_forked_event_only_on_the_child(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    fork_run("run-parent", "map", run_id="run-child", output_root=output_root)

    child_dir = output_root / "runs" / "run-child"
    child_events = _events(child_dir)
    parent_events = _events(parent_dir)

    forked_events = [e for e in child_events if e.get("kind") == "run_forked"]
    assert len(forked_events) == 1
    assert forked_events[0]["parent_run_id"] == "run-parent"
    assert forked_events[0]["state"] == "map"

    assert not any(e.get("kind") == "run_forked" for e in parent_events)
    # The child's log is the parent's prefix (up to, not including, the
    # transition into 'map') plus exactly one new event appended.
    assert child_events[:-1] == parent_events[: len(child_events) - 1]


def test_fork_preserves_depth_budgets_and_monitoring_from_parent(tmp_path):
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_deepen(parent_dir)

    fork_run("run-parent", "deepen", run_id="run-child", output_root=output_root)

    manifest = yaml.safe_load((output_root / "runs" / "run-child" / "manifest.yaml").read_text())
    assert manifest["depth_budgets"]["clusters_to_deepen"] == ["cluster-1"]


def test_metrics_on_a_forked_run_never_blend_parent_and_child_events(tmp_path):
    """FR-60/FR-57: after the fork, each run's own retrieval activity
    stays scoped to its own event log — the child's rediscovery-rate
    computation never sees the parent's post-fork lookups, and vice
    versa."""
    parent_dir, output_root = _open(tmp_path, "run-parent")
    _build_parent_through_map(parent_dir)

    fork_run("run-parent", "map", run_id="run-child", output_root=output_root)
    child_dir = output_root / "runs" / "run-child"

    # Distinct post-fork retrieval activity in each run.
    search_corpus(
        parent_dir, output_root,
        _StubProvider([{"canonical_key": "10.1/parent-only", "title": "P", "source": "stub"}]),
        "q", role="scout",
    )
    search_corpus(
        child_dir, output_root,
        _StubProvider([{"canonical_key": "10.1/child-only-a", "title": "A", "source": "stub"}]),
        "q", role="scout",
    )
    search_corpus(
        child_dir, output_root,
        _StubProvider([{"canonical_key": "10.1/child-only-a", "title": "A", "source": "stub"}]),
        "q2", role="scout",
    )

    child_result = compute_rediscovery_rate(child_dir)
    # Only the child's two lookups count; the second is a genuine within-
    # run repeat of the first — the parent's lookup is invisible to it.
    assert child_result["sample_size"] == 2
    assert child_result["rediscovery_rate"] == pytest.approx(0.5)

    parent_result = compute_rediscovery_rate(parent_dir)
    assert parent_result["sample_size"] == 1
    assert parent_result["rediscovery_rate"] == 0.0
