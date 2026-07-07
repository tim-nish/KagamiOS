import json
import shutil
import uuid
from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.paths import resolve_output_root
from kagami.registry import load_registry
from kagami.schema_version import CURRENT_SCHEMA_REGISTRY_VERSION, assert_run_mutable
from kagami.store.artifact import reap_expired_claims
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock, write_lease
from kagami.store.markdown_doc import parse_document, render_document
from kagami.timeutil import utc_now_iso


class RunForkError(Exception):
    pass


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


def _read_events(run_dir: Path) -> list[dict]:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def _find_state_entry_index(events: list[dict], state: str) -> int | None:
    """The position of the *last* `state_transition`/`entered` event for
    `state` — if a run re-entered a state more than once (a defined
    backward transition, FR-1), the most recent entry is the meaningful
    boundary."""
    index = None
    for i, event in enumerate(events):
        if (
            event.get("family") == "state_transition"
            and event.get("kind") == "entered"
            and event.get("state") == state
        ):
            index = i
    return index


def _stamp_inherited(art_dir: Path) -> None:
    """FR-60: the live version of a copied artifact is marked `inherited`
    — whatever human decision (`decided_by`) produced it happened in the
    parent run, not this one. Historical versions (`vN.md`) are left
    untouched: they are an honest, verbatim record of the parent's own
    version history."""
    current_path = art_dir / "current.md"
    frontmatter, sections = parse_document(current_path.read_text())
    frontmatter["inherited"] = True
    atomic_write(current_path, render_document(frontmatter, sections))


def fork_run(
    parent_run_id: str,
    from_state: str,
    run_id: str | None = None,
    output_root: Path | None = None,
    registry=None,
) -> dict:
    """FR-60/AD-11/AD-20: seed a *new* run from an existing one, up to a
    chosen state boundary — the parent's `events.jsonl` is only ever read,
    never rewritten; forking always creates a new run directory.

    `from_state` is the state the new run lands *at* (its `current_state`
    once forked). The parent must have actually entered it — a
    `state_transition`/`entered` event for it must exist in the parent's
    log — or the fork is refused; forking from a boundary never reached
    would seed a run from nothing.

    Artifacts are copied by reusing each type's existing, declared
    `generation_window` (no new "which state produced this" metadata
    invented) — every type whose window is a state *strictly before*
    `from_state` (plus the always-present `entry`/`any` windows) is
    copied wholesale. `from_state`'s own artifacts are deliberately *not*
    copied: that boundary is what a fork exists to let a developer redo
    fresh, not inherit stale. The parent's event log is copied up to (not
    including) the moment it entered `from_state`, for the same reason.

    Each copied artifact's live (`current.md`) version is stamped
    `inherited: true` — see `_stamp_inherited`.
    """
    registry = registry or load_registry()
    output_root = output_root if output_root is not None else resolve_output_root()
    states = registry.states()

    if from_state not in states:
        raise RunForkError(
            f"'{from_state}' is not a valid fork boundary; must be one of {states} (FR-60)"
        )

    parent_run_dir = output_root / "runs" / parent_run_id
    parent_manifest_path = parent_run_dir / "manifest.yaml"
    if not parent_manifest_path.is_file():
        raise RunForkError(f"no parent run '{parent_run_id}' found to fork from (FR-60)")
    parent_manifest = yaml.safe_load(parent_manifest_path.read_text()) or {}
    assert_run_mutable(parent_manifest.get("schema_registry_version"))

    parent_events = _read_events(parent_run_dir)
    boundary_event_idx = _find_state_entry_index(parent_events, from_state)
    if boundary_event_idx is None:
        raise RunForkError(
            f"parent run '{parent_run_id}' never entered state '{from_state}' — "
            "nothing to fork from (FR-60)"
        )
    events_to_copy = parent_events[:boundary_event_idx]

    boundary_idx = states.index(from_state)
    copyable_windows = set(states[:boundary_idx]) | {"entry", "any"}
    artifact_types_to_copy = [
        type_slug
        for type_slug in registry.artifact_types()
        if registry.generation_window(type_slug) in copyable_windows
    ]

    run_id = run_id or generate_run_id()
    run_dir = output_root / "runs" / run_id
    if run_dir.exists():
        raise RunForkError(f"run '{run_id}' already exists (FR-60)")

    run_dir.mkdir(parents=True)
    copied_artifact_ids: list[str] = []
    with acquire_run_lock(run_dir / ".lock"):
        lease = write_lease(run_dir / ".lease")

        for type_slug in artifact_types_to_copy:
            parent_type_dir = parent_run_dir / "artifacts" / type_slug
            if not parent_type_dir.is_dir():
                continue
            for parent_art_dir in sorted(p for p in parent_type_dir.iterdir() if p.is_dir()):
                dst_dir = run_dir / "artifacts" / type_slug / parent_art_dir.name
                shutil.copytree(parent_art_dir, dst_dir)
                _stamp_inherited(dst_dir)
                copied_artifact_ids.append(parent_art_dir.name)

        manifest = {
            "run_id": run_id,
            "schema_registry_version": CURRENT_SCHEMA_REGISTRY_VERSION,
            "created": utc_now_iso(),
            "parent_run_id": parent_run_id,
            "forked_from_state": from_state,
            "rooting_intuition_note": parent_manifest.get("rooting_intuition_note"),
            "depth_budgets": parent_manifest.get("depth_budgets"),
            "monitoring": parent_manifest.get("monitoring"),
            "state_cache": {
                "current_state": from_state,
                "visited": list(states[: boundary_idx + 1]),
                "integrity_violations": [],
            },
        }
        atomic_write(run_dir / "manifest.yaml", yaml.safe_dump(manifest, sort_keys=False))

        (run_dir / "events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events_to_copy)
        )

        append_event(
            run_dir,
            "state_transition",
            {
                "kind": "run_forked",
                "state": from_state,
                "parent_run_id": parent_run_id,
                "copied_artifact_count": len(copied_artifact_ids),
            },
        )

    return {
        "ok": True,
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "from_state": from_state,
        "path": str(run_dir),
        "copied_artifact_count": len(copied_artifact_ids),
        "lease": lease,
    }
