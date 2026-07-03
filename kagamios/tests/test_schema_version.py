import pytest
import yaml

from kagami.schema_version import CURRENT_SCHEMA_REGISTRY_VERSION, SchemaVersionError, assert_run_mutable
from kagami.store.run import open_run


def test_assert_run_mutable_accepts_matching_version():
    assert_run_mutable(CURRENT_SCHEMA_REGISTRY_VERSION)


def test_assert_run_mutable_refuses_newer_version():
    with pytest.raises(SchemaVersionError):
        assert_run_mutable(CURRENT_SCHEMA_REGISTRY_VERSION + 1)


def test_assert_run_mutable_refuses_older_version():
    with pytest.raises(SchemaVersionError):
        assert_run_mutable(CURRENT_SCHEMA_REGISTRY_VERSION - 1)


def test_open_run_refuses_to_mutate_run_from_newer_schema_registry(tmp_path):
    output_root = tmp_path / "_kagami-output"
    run_dir = output_root / "runs" / "run-future"
    run_dir.mkdir(parents=True)
    manifest = {
        "run_id": "run-future",
        "schema_registry_version": CURRENT_SCHEMA_REGISTRY_VERSION + 1,
        "created": "2026-01-01T00:00:00Z",
    }
    manifest_path = run_dir / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))
    original_manifest_text = manifest_path.read_text()

    with pytest.raises(SchemaVersionError):
        open_run(run_id="run-future", output_root=output_root)

    assert not (run_dir / ".lock").exists()
    assert not (run_dir / ".lease").exists()
    assert manifest_path.read_text() == original_manifest_text
