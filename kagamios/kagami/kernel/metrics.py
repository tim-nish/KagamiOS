import json
from pathlib import Path


def compute_override_rate(run_dir: Path, type_slug: str) -> dict:
    """FR-5's evidence base: of this run's own artifacts of `type_slug` that
    reached `accepted`, what fraction ever needed a human edit first — the
    aggregated, per-researcher statistic a gate-loosening proposal for that
    type must cite (AD-11's sanctioned read exception; never raw events at
    the point of decision, only this derived aggregate).
    """
    path = run_dir / "events.jsonl"
    accepted_ids: set[str] = set()
    overridden_ids: set[str] = set()

    if path.is_file():
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event.get("artifact_type") != type_slug:
                continue
            if event.get("family") == "artifact_event" and event.get("kind") == "accepted":
                accepted_ids.add(event["artifact_id"])
            elif event.get("family") == "human_edit":
                overridden_ids.add(event["artifact_id"])

    overridden_count = len(accepted_ids & overridden_ids)
    accepted_count = len(accepted_ids)
    override_rate = (overridden_count / accepted_count) if accepted_count else 0.0

    return {
        "type": type_slug,
        "accepted_count": accepted_count,
        "overridden_count": overridden_count,
        "override_rate": override_rate,
    }


def count_full_pull_after_summary(run_dir: Path) -> int:
    """FR-33: the summary-sufficiency signal.

    Counts artifacts where a full-text pull immediately followed a summary
    read of that same artifact — a detectable sign the summary was too thin.
    Computed after the fact from the event log (AD-11's sanctioned `kagami
    metrics` read exception), never consulted at runtime.
    """
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return 0

    last_read_kind: dict[str, str] = {}
    count = 0
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event.get("family") != "retrieval":
            continue
        artifact_id = event.get("artifact_id")
        kind = event.get("kind")
        if kind == "summary_read":
            last_read_kind[artifact_id] = "summary_read"
        elif kind == "full_text_pull":
            if last_read_kind.get(artifact_id) == "summary_read":
                count += 1
            last_read_kind[artifact_id] = "full_text_pull"

    return count
