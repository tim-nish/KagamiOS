from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.kernel.state_machine import enter_state, get_state_cache
from kagami.registry import load_registry
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock

MONITORED_STATUSES = ("dormant", "decided")


class MonitorError(Exception):
    pass


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "manifest.yaml"


def _read_manifest(run_dir: Path) -> dict:
    return yaml.safe_load(_manifest_path(run_dir).read_text())


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    atomic_write(_manifest_path(run_dir), yaml.safe_dump(manifest, sort_keys=False))


def _stale_artifacts(run_dir: Path) -> list:
    artifacts_root = run_dir / "artifacts"
    if not artifacts_root.exists():
        return []
    stale = []
    for meta_path in artifacts_root.glob("*/*/meta.yaml"):
        meta = yaml.safe_load(meta_path.read_text())
        if meta.get("status") == "stale":
            stale.append({"id": meta["id"], "type": meta["type"]})
    return stale


def mark_dormant(run_dir: Path, revival_conditions: str, registry=None) -> dict:
    """FR-7: park a run with explicit revival conditions on record — it
    keeps receiving monitoring updates via the sweep (`kagami monitor`),
    never a background process the researcher can't see (AD-24)."""
    if not revival_conditions or not revival_conditions.strip():
        raise MonitorError("marking a run Dormant requires explicit revival conditions (FR-7)")

    registry = registry or load_registry()
    parked_at_state = get_state_cache(run_dir).get("current_state")

    enter_state(run_dir, "dormant", registry=registry)

    with acquire_run_lock(run_dir / ".lock"):
        manifest = _read_manifest(run_dir)
        manifest["monitoring"] = {
            "status": "dormant",
            "revival_conditions": revival_conditions,
            "parked_at_state": parked_at_state,
        }
        _write_manifest(run_dir, manifest)
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "marked_dormant",
                "revival_conditions": revival_conditions,
                "parked_at_state": parked_at_state,
            },
        )

    return {"ok": True, "revival_conditions": revival_conditions, "parked_at_state": parked_at_state}


def monitor_sweep(run_dir: Path, registry=None) -> dict:
    """AD-24: `kagami monitor` executes as a sweep at run open / skill
    activation — never a background daemon. Dormant reopening (FR-7)
    therefore happens synchronously, at the next session, never
    asynchronously.

    Generic on purpose: the reopening logic keys off the manifest's
    `monitoring` status and existing stale artifacts, not off "Dormant"
    specifically, so v2's post-decision staleness (FR-8) reuses this
    unchanged once Decided is reachable.
    """
    registry = registry or load_registry()
    manifest = _read_manifest(run_dir)
    monitoring = manifest.get("monitoring")

    if monitoring is None or monitoring.get("status") not in MONITORED_STATUSES:
        return {"ok": True, "swept": False, "reopened": False}

    stale = _stale_artifacts(run_dir)
    if not stale:
        append_event(
            run_dir,
            "gate_event",
            {"kind": "dormant_monitoring_checked", "status": monitoring["status"], "stale_artifact_ids": []},
        )
        return {"ok": True, "swept": True, "reopened": False, "stale_artifact_ids": []}

    states = registry.states()
    candidate_windows = [registry.generation_window(a["type"]) for a in stale]
    reenterable_states = [s for s in candidate_windows if s in states]
    if not reenterable_states:
        raise MonitorError(
            "monitor sweep found stale artifacts but none map to a re-enterable working "
            f"state (generation windows seen: {sorted(set(candidate_windows))})"
        )
    affected_state = min(reenterable_states, key=states.index)

    was_status = monitoring["status"]
    enter_state(
        run_dir,
        affected_state,
        waiver=f"staling alert reopened a {was_status} run at its affected state (FR-7/FR-8, AD-24)",
        registry=registry,
    )

    with acquire_run_lock(run_dir / ".lock"):
        manifest = _read_manifest(run_dir)
        manifest["monitoring"]["status"] = "reopened"
        manifest["monitoring"]["reopened_at_state"] = affected_state
        _write_manifest(run_dir, manifest)
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "staling_alert_reopened_run",
                "was_status": was_status,
                "affected_state": affected_state,
                "stale_artifact_ids": [a["id"] for a in stale],
            },
        )

    return {
        "ok": True,
        "swept": True,
        "reopened": True,
        "affected_state": affected_state,
        "stale_artifact_ids": [a["id"] for a in stale],
    }
