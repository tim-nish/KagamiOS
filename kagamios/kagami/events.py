import json
from pathlib import Path

from kagami.timeutil import utc_now_iso

EVENT_FAMILIES = (
    "llm_call",
    "retrieval",
    "artifact_event",
    "question_event",
    "human_edit",
    "frontier_decision",
    "gate_event",
    "budget_event",
    "state_transition",
    "terminal_event",
)


def append_event(run_dir: Path, family: str, payload: dict) -> dict:
    if family not in EVENT_FAMILIES:
        raise ValueError(f"unknown event family '{family}'")
    event = {"family": family, "timestamp": utc_now_iso(), **payload}
    with open(run_dir / "events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")
    return event
