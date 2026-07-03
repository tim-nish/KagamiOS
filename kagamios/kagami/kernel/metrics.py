import json
from pathlib import Path


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
