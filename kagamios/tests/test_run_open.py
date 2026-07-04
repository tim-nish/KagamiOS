import json

import yaml

from kagami.schema_version import CURRENT_SCHEMA_REGISTRY_VERSION
from kagami.store.artifact import claim_section, create_artifact
from kagami.store.run import open_run


def test_open_run_creates_expected_scaffold(tmp_path):
    result = open_run(run_id="run-test1", output_root=tmp_path / "_kagami-output")

    assert result["ok"] is True
    assert result["created"] is True
    run_dir = tmp_path / "_kagami-output" / "runs" / "run-test1"
    assert run_dir.is_dir()
    assert (run_dir / ".lock").is_file()
    assert (run_dir / ".lease").is_file()
    assert (run_dir / "manifest.yaml").is_file()
    assert (run_dir / "events.jsonl").is_file()
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert len(events) == 1
    assert events[0]["family"] == "state_transition"
    assert events[0]["kind"] == "run_opened"


def test_open_run_manifest_is_stamped_with_schema_version(tmp_path):
    open_run(run_id="run-test2", output_root=tmp_path / "_kagami-output")

    manifest_path = tmp_path / "_kagami-output" / "runs" / "run-test2" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    assert manifest["schema_registry_version"] == CURRENT_SCHEMA_REGISTRY_VERSION
    assert manifest["run_id"] == "run-test2"
    assert manifest["created"]


def test_open_run_lease_contains_holder_and_timestamps(tmp_path):
    result = open_run(run_id="run-test3", output_root=tmp_path / "_kagami-output")

    lease_path = tmp_path / "_kagami-output" / "runs" / "run-test3" / ".lease"
    lease = json.loads(lease_path.read_text())
    assert lease["holder"] == result["lease"]["holder"]
    assert lease["opened_at"] == lease["heartbeat"]


def test_open_run_without_run_id_generates_unique_ids(tmp_path):
    first = open_run(output_root=tmp_path / "_kagami-output")
    second = open_run(output_root=tmp_path / "_kagami-output")

    assert first["run_id"] != second["run_id"]
    assert first["run_id"].startswith("run-")


def test_reopening_existing_run_refreshes_lease_without_recreating_manifest(tmp_path):
    output_root = tmp_path / "_kagami-output"
    first = open_run(run_id="run-test4", output_root=output_root)
    second = open_run(run_id="run-test4", output_root=output_root)

    assert second["created"] is False
    assert first["run_id"] == second["run_id"]

    run_dir = output_root / "runs" / "run-test4"
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    kinds = [e["kind"] for e in events]
    assert kinds == ["run_opened", "run_resumed"]


def test_reopening_a_run_reaps_claims_from_the_crashed_prior_session(tmp_path):
    """AD-10/AD-15: a worker's session crashes mid-claim; reopening the run
    reaps its expired claims rather than leaving the section wedged."""
    output_root = tmp_path / "_kagami-output"
    first = open_run(run_id="run-test5", output_root=output_root)
    run_dir = output_root / "runs" / "run-test5"

    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        {
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
        },
        sections={"evolution": "x"},
    )
    art_dir = run_dir / "artifacts" / "cluster-dossier" / dossier["id"]
    section_id = yaml.safe_load((art_dir / "meta.yaml").read_text())["sections"][0]["id"]

    # The "crashed" worker claims a section under the first session's lease.
    assert claim_section(run_dir, "cluster-dossier", dossier["id"], section_id, first["lease"]["holder"])

    # Reopening mints a brand-new lease holder — the old claim is now stale.
    second = open_run(run_id="run-test5", output_root=output_root)
    assert second["reaped_claims"] == [
        {"artifact_id": dossier["id"], "section_id": section_id, "previous_holder": first["lease"]["holder"]}
    ]

    meta = yaml.safe_load((art_dir / "meta.yaml").read_text())
    assert meta["claims"] == {}

    # The section is claimable again under the new session's holder.
    assert claim_section(run_dir, "cluster-dossier", dossier["id"], section_id, second["lease"]["holder"])
