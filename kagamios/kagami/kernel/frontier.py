from pathlib import Path

from kagami.events import append_event

PRIORITY_CLASSES = (
    "blocking_next_gate",
    "stale_repairs_active_path",
    "checklist_holes",
    "deferred_work",
)


def select_next(candidates: dict) -> dict:
    """FR-18: FRONTIER selects the next work item by fixed priority.

    `candidates` maps each priority class to a list of candidate work items;
    the first non-empty class in PRIORITY_CLASSES order wins.
    """
    for priority_class in PRIORITY_CLASSES:
        items = candidates.get(priority_class) or []
        if items:
            return {"priority_class": priority_class, "item": items[0]}
    return {"priority_class": None, "item": None}


def select_and_log(run_dir: Path, candidates: dict) -> dict:
    decision = select_next(candidates)
    append_event(
        run_dir,
        "frontier_decision",
        {"priority_class": decision["priority_class"], "item": decision["item"]},
    )
    return decision
