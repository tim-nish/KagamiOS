from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.kernel.metrics import compute_override_rate
from kagami.registry import load_registry
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock


class GateTrustError(Exception):
    pass


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "manifest.yaml"


def _read_manifest(run_dir: Path) -> dict:
    return yaml.safe_load(_manifest_path(run_dir).read_text())


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    atomic_write(_manifest_path(run_dir), yaml.safe_dump(manifest, sort_keys=False))


def _constitutive_types(registry) -> set:
    return {type_slug for type_slug, _field_name in registry.audit_exempt_fields()}


def _assert_not_constitutive(type_slug: str, registry) -> None:
    if type_slug in _constitutive_types(registry):
        raise GateTrustError(
            f"'{type_slug}' carries a constitutive-triad field; its review gate can never be "
            "loosened, with or without approval — no trusted-mode override exists (FR-4)"
        )


def propose_gate_loosening(run_dir: Path, type_slug: str, registry=None) -> dict:
    """FR-5: for a non-constitutive review gate, the system may propose
    collapsing it to a notification, grounded in this researcher's own
    aggregated edit history for that type. The proposal alone changes
    nothing — the gate stays at full strictness until a discrete approval
    is recorded (`approve_gate_loosening`)."""
    registry = registry or load_registry()
    registry.get_artifact_schema(type_slug)
    _assert_not_constitutive(type_slug, registry)

    statistic = compute_override_rate(run_dir, type_slug)
    append_event(
        run_dir,
        "gate_event",
        {"kind": "gate_loosening_proposed", "artifact_type": type_slug, "statistic": statistic},
    )
    return {
        "ok": True,
        "type": type_slug,
        "proposal": "collapse review gate to a notification",
        "statistic": statistic,
    }


def is_gate_loosened(run_dir: Path, type_slug: str) -> bool:
    manifest = _read_manifest(run_dir)
    return type_slug in (manifest.get("loosened_gates") or [])


def approve_gate_loosening(run_dir: Path, type_slug: str, registry=None) -> dict:
    """FR-5: the only path by which a gate's strictness actually changes —
    recorded as a discrete approval event, citing a freshly computed
    statistic rather than trusting one supplied by the caller. Refused
    outright for any type carrying a constitutive-triad field, regardless
    of approval (FR-4)."""
    registry = registry or load_registry()
    registry.get_artifact_schema(type_slug)
    _assert_not_constitutive(type_slug, registry)

    statistic = compute_override_rate(run_dir, type_slug)

    with acquire_run_lock(run_dir / ".lock"):
        manifest = _read_manifest(run_dir)
        loosened = manifest.setdefault("loosened_gates", [])
        if type_slug not in loosened:
            loosened.append(type_slug)
        _write_manifest(run_dir, manifest)
        append_event(
            run_dir,
            "gate_event",
            {"kind": "gate_loosening_approved", "artifact_type": type_slug, "statistic": statistic},
        )

    return {"ok": True, "type": type_slug, "loosened": True, "statistic": statistic}
