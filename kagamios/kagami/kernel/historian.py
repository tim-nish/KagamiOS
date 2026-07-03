from pathlib import Path

from kagami.events import append_event
from kagami.store.artifact import attempt_ai_write

EVOLUTION_SECTION = "evolution"

# Deterministic, keyword-based detector — no model call. Deliberately
# narrow: false negatives (missed speculation) are cheaper than false
# positives blocking legitimate history, but each phrase here is
# unambiguously forward-looking, never descriptive of the past.
FRONTIER_SPECULATION_MARKERS = (
    "could enable",
    "could lead to",
    "may open the door to",
    "opens up new",
    "future work",
    "next steps could include",
    "potential future",
    "this suggests a promising direction",
)


class HistorianError(Exception):
    pass


def detect_frontier_speculation(text: str) -> str | None:
    lowered = text.lower()
    for marker in FRONTIER_SPECULATION_MARKERS:
        if marker in lowered:
            return marker
    return None


def historian_write(run_dir: Path, art_id: str, section_title: str, new_body: str, registry=None) -> dict:
    """FR-28: Historian writes only the Cluster Dossier's Evolution section,
    and never frontier-facing speculation even there. Both violations are
    refused and logged as generation-window violations attributed to the
    Historian role — never silently written and never silently dropped.
    """
    if section_title != EVOLUTION_SECTION:
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "generation_window_violation",
                "role": "historian",
                "detail": (
                    f"Historian attempted to write '{section_title}'; confined to "
                    f"'{EVOLUTION_SECTION}' (FR-28)"
                ),
                "artifact_id": art_id,
            },
        )
        raise HistorianError(
            f"Historian may only write the '{EVOLUTION_SECTION}' section, not '{section_title}' (FR-28)"
        )

    speculation = detect_frontier_speculation(new_body)
    if speculation:
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "generation_window_violation",
                "role": "historian",
                "detail": f"frontier-facing speculation detected: {speculation!r} (FR-28)",
                "artifact_id": art_id,
            },
        )
        raise HistorianError(
            f"Historian content contains frontier-facing speculation: {speculation!r} (FR-28)"
        )

    return attempt_ai_write(
        run_dir, "cluster-dossier", art_id, EVOLUTION_SECTION, new_body, registry=registry
    )
