from pathlib import Path

from kagami.kernel.state_machine import enter_state
from kagami.registry import load_registry
from kagami.store.artifact import create_artifact

ENTRY_MODES = ("intuition-first", "paper-first", "field-first", "problem-first", "tool-first")


class EntryError(Exception):
    pass


def start_run_from_entry(run_dir: Path, entry_mode: str, raw_capture: str, registry=None) -> dict:
    """FR-6: any of the five entry modes backfills a non-empty Intuition Note
    and roots the run at Frame before Map may begin."""
    if entry_mode not in ENTRY_MODES:
        raise EntryError(f"'{entry_mode}' is not a recognized entry mode; must be one of {ENTRY_MODES}")
    if not raw_capture or not raw_capture.strip():
        raise EntryError("raw_capture must be non-empty (FR-6: a non-empty Intuition Note)")

    registry = registry or load_registry()
    result = create_artifact(
        run_dir,
        "intuition-note",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "human",
            "summary": "",
            "entry_mode": entry_mode,
        },
        sections={"raw_capture": raw_capture},
        registry=registry,
    )
    enter_state(run_dir, "frame", registry=registry)
    return {"ok": True, "intuition_note_id": result["id"], "entry_mode": entry_mode}
