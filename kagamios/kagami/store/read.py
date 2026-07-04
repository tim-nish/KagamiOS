from pathlib import Path

from kagami.events import append_event
from kagami.registry import RegistryError, load_registry
from kagami.store.artifact import read_current

RESOLUTIONS = ("summary", "full")


class ConsumptionError(Exception):
    pass


def read_artifact(
    run_dir: Path,
    state: str,
    type_slug: str,
    art_id: str,
    resolution: str,
    registry=None,
) -> dict:
    """FR-15/FR-33: the only sanctioned read path — enforces the per-state
    consumption map and logs summary reads distinctly from full-text pulls.
    """
    if resolution not in RESOLUTIONS:
        raise ConsumptionError(f"resolution must be one of {RESOLUTIONS}, got '{resolution}'")

    registry = registry or load_registry()
    try:
        allowed = registry.can_read(state, type_slug)
    except RegistryError as exc:
        raise ConsumptionError(str(exc)) from None
    if not allowed:
        raise ConsumptionError(
            f"state '{state}' has no defined brief for reading '{type_slug}' (FR-15)"
        )

    frontmatter, sections = read_current(run_dir, type_slug, art_id)

    if resolution == "summary":
        append_event(
            run_dir,
            "retrieval",
            {"kind": "summary_read", "state": state, "artifact_type": type_slug, "artifact_id": art_id},
        )
        return {"ok": True, "resolution": "summary", "summary": frontmatter.get("summary", "")}

    append_event(
        run_dir,
        "retrieval",
        {"kind": "full_text_pull", "state": state, "artifact_type": type_slug, "artifact_id": art_id},
    )
    return {
        "ok": True,
        "resolution": "full",
        "frontmatter": frontmatter,
        "sections": [{"id": s.id, "title": s.title, "body": s.body} for s in sections],
    }
