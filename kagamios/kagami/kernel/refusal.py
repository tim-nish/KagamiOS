import json
from pathlib import Path

from kagami.events import append_event
from kagami.store.locking import acquire_run_lock

DEFAULT_REFUSAL_CEILING = 3


def consecutive_refusal_count(run_dir: Path, entrypoint: str, target: str) -> int:
    """AD-26(a): a pure function over the tail of `events.jsonl` — no new
    store. "Consecutive" means strictly adjacent in the log: the count
    stops at the first event, of any kind, that is not an
    `entrypoint_refused` gate_event for this exact `(entrypoint, target)`
    tuple. This is a conservative but simple operationalization of "resets
    on any intervening non-refusal event for that tuple" — a genuine
    runaway retry loop calls the same failing thing back-to-back with
    nothing else in between; anything else breaking the streak is, by
    construction, not that failure mode.
    """
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return 0

    count = 0
    for line in reversed(path.read_text().splitlines()):
        event = json.loads(line)
        if (
            event.get("family") == "gate_event"
            and event.get("kind") == "entrypoint_refused"
            and event.get("entrypoint") == entrypoint
            and event.get("target") == target
        ):
            count += 1
        else:
            break
    return count


def record_refusal_and_check_ceiling(
    run_dir: Path,
    entrypoint: str,
    target: str,
    error: str | None,
    ceiling: int = DEFAULT_REFUSAL_CEILING,
) -> dict:
    """FR-48/AD-26(a): logs this refusal as an event, then checks whether
    this attempt is the one that crosses the configured ceiling of
    consecutive identical refusals for `(entrypoint, target)`. Returns
    `{"escalate": True, "count": N}` when it does — the caller (the CLI
    boundary) is responsible for turning that into a `requires_researcher`
    response instead of the ordinary refusal, never entering the Question
    Ledger or `kagami ask`'s queue (AD-8, AD-14): this is a synchronous
    CLI response, not a scheduled question.
    """
    with acquire_run_lock(run_dir / ".lock"):
        prior_count = consecutive_refusal_count(run_dir, entrypoint, target)
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "entrypoint_refused",
                "entrypoint": entrypoint,
                "target": target,
                "error": error,
            },
        )
    new_count = prior_count + 1
    return {"escalate": new_count >= ceiling, "count": new_count}
