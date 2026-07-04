import uuid
from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.paths import resolve_output_root
from kagami.schema_version import CURRENT_SCHEMA_REGISTRY_VERSION, assert_run_mutable
from kagami.store.artifact import reap_expired_claims
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock, write_lease
from kagami.timeutil import utc_now_iso


def generate_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def open_run(run_id: str | None = None, output_root: Path | None = None) -> dict:
    output_root = output_root if output_root is not None else resolve_output_root()
    runs_dir = output_root / "runs"
    run_id = run_id or generate_run_id()
    run_dir = runs_dir / run_id
    lock_path = run_dir / ".lock"

    if run_dir.exists():
        manifest_path = run_dir / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        assert_run_mutable(manifest.get("schema_registry_version"))
        with acquire_run_lock(lock_path):
            lease = write_lease(run_dir / ".lease")
            append_event(run_dir, "state_transition", {"kind": "run_resumed", "run_id": run_id})

        # AD-15's consistency repair: reaping happens as its own locked
        # operation (reap_expired_claims holds the lock itself) — never
        # nested inside the block above, which would deadlock.
        reaped = reap_expired_claims(run_dir, lease["holder"])

        return {
            "ok": True,
            "run_id": run_id,
            "path": str(run_dir),
            "created": False,
            "lease": lease,
            "reaped_claims": reaped,
        }

    run_dir.mkdir(parents=True)
    with acquire_run_lock(lock_path):
        lease = write_lease(run_dir / ".lease")
        manifest = {
            "run_id": run_id,
            "schema_registry_version": CURRENT_SCHEMA_REGISTRY_VERSION,
            "created": utc_now_iso(),
            "rooting_intuition_note": None,
            "depth_budgets": None,
            "monitoring": None,
            "state_cache": {},
        }
        atomic_write(run_dir / "manifest.yaml", yaml.safe_dump(manifest, sort_keys=False))
        (run_dir / "events.jsonl").touch()
        append_event(run_dir, "state_transition", {"kind": "run_opened", "run_id": run_id})

    return {
        "ok": True,
        "run_id": run_id,
        "path": str(run_dir),
        "created": True,
        "lease": lease,
    }
