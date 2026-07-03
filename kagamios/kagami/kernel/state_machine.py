from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.kernel.derived_state import DEEPEN_STATE, DepthBudgetError, assert_depth_budgets_set
from kagami.registry import load_registry
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock

TERMINALS_REACHABLE_ANYTIME = ("dissolved", "dormant")


class StateMachineError(Exception):
    pass


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "manifest.yaml"


def _read_manifest(run_dir: Path) -> dict:
    return yaml.safe_load(_manifest_path(run_dir).read_text())


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    atomic_write(_manifest_path(run_dir), yaml.safe_dump(manifest, sort_keys=False))


def get_state_cache(run_dir: Path) -> dict:
    manifest = _read_manifest(run_dir)
    state_cache = manifest.get("state_cache")
    return state_cache if state_cache is not None else {}


def enter_state(
    run_dir: Path, state: str, waiver: str | None = None, cause: str | None = None, registry=None
) -> dict:
    """FR-1/FR-2: advance the run's nominal state, logging every transition.

    - A forward move to the immediate nominal-next state, or to Dissolved/
      Dormant from any state, needs nothing extra.
    - A registered backward transition (state_machine.yaml) requires a
      one-line `cause` and is refused without one (FR-1).
    - Anything else — the frontier proceeding past a working state — is a
      *skip*. It requires a one-line `waiver`; without one, the transition
      still applies but is flagged as a detectable data-integrity violation
      rather than blocked (FR-2).
    """
    registry = registry or load_registry()
    states = registry.states()
    if state not in states and state not in TERMINALS_REACHABLE_ANYTIME:
        raise StateMachineError(f"'{state}' is not a valid state")

    if state == DEEPEN_STATE:
        try:
            assert_depth_budgets_set(run_dir)
        except DepthBudgetError as exc:
            raise StateMachineError(str(exc)) from None

    with acquire_run_lock(run_dir / ".lock"):
        manifest = _read_manifest(run_dir)
        if manifest.get("state_cache") is None:
            manifest["state_cache"] = {}
        state_cache = manifest["state_cache"]
        current = state_cache.get("current_state")
        visited = state_cache.setdefault("visited", [])
        violations = state_cache.setdefault("integrity_violations", [])

        violation = None
        if state in TERMINALS_REACHABLE_ANYTIME or state == current:
            pass
        elif current is None:
            if state != states[0]:
                violation = f"entered '{state}' without ever entering '{states[0]}'"
        else:
            nominal_next = None
            if current in states:
                idx = states.index(current)
                if idx + 1 < len(states):
                    nominal_next = states[idx + 1]
            backward_targets = {t for f, t in registry.backward_transitions() if f == current}

            if state == nominal_next:
                pass
            elif state in backward_targets:
                if not cause:
                    raise StateMachineError(
                        f"backward transition '{current}' -> '{state}' requires a one-line "
                        "'cause' annotation before it is accepted (FR-1)"
                    )
            else:
                violation = f"entered '{state}' from '{current}', skipping intermediate state(s)"

        if violation and not waiver:
            violations.append({"kind": "skipped_state", "detail": violation, "state": state})
        else:
            violation = None

        state_cache["current_state"] = state
        visited.append(state)
        _write_manifest(run_dir, manifest)

        event_payload = {"kind": "entered", "state": state, "from": current}
        if waiver:
            event_payload["waiver"] = waiver
        if cause:
            event_payload["cause"] = cause
        append_event(run_dir, "state_transition", event_payload)

        if violation:
            append_event(
                run_dir, "gate_event", {"kind": "integrity_violation", "detail": violation, "state": state}
            )

    return {"ok": True, "state": state, "violation": violation}
