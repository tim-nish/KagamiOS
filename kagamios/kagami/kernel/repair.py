from pathlib import Path

from kagami.events import append_event
from kagami.store.artifact import attempt_ai_write, read_current


def repair_artifact(run_dir: Path, type_slug: str, art_id: str, registry=None) -> dict:
    """FR-35: the tiered repair pipeline's entry point.

    Tier 0 — deterministic, no model call: is the artifact even stale?
    (Staleness is itself the dependency check, per FR-13's pure graph
    traversal — no further work is needed if it already resolved to
    "not stale.") If it *is* stale, Tier 0 alone cannot say which
    sections plausibly need regenerating without a model in the loop, so
    repair escalates to Tier 1 — never a full artifact rewrite, and never
    a model call made directly by this chokepoint (per the runtime
    contract, the core returns a typed `needs_llm` work item for the
    harness to fulfill, then submits the result through
    `apply_tier2_repair`).
    """
    frontmatter, _ = read_current(run_dir, type_slug, art_id)

    if frontmatter.get("status") != "stale":
        append_event(
            run_dir,
            "artifact_event",
            {"kind": "repair_resolved_at_tier0", "artifact_type": type_slug, "artifact_id": art_id},
        )
        return {"ok": True, "tier": 0, "resolved": True, "needs_llm": None}

    append_event(
        run_dir,
        "artifact_event",
        {"kind": "repair_escalated_to_tier1", "artifact_type": type_slug, "artifact_id": art_id},
    )
    return {
        "ok": True,
        "tier": 1,
        "resolved": False,
        "needs_llm": {
            "operation_class": "tier1_plausibility_check",
            "artifact_type": type_slug,
            "artifact_id": art_id,
        },
    }


def apply_tier2_repair(
    run_dir: Path, type_slug: str, art_id: str, section_fixes: dict, registry=None
) -> dict:
    """FR-35/FR-12/AD-16: Tier 2 — regenerate only the specific failing
    section IDs the harness identified. Reuses the existing
    human-touch-aware write guard: a fix targeting a human-touched span is
    refused and re-emitted as a proposed diff for review, never applied
    over it.
    """
    applied = []
    quarantined = []
    for section_title, new_body in section_fixes.items():
        result = attempt_ai_write(run_dir, type_slug, art_id, section_title, new_body, registry=registry)
        if result["ok"]:
            applied.append(section_title)
        else:
            quarantined.append({"section": section_title, "quarantined_as": result["quarantined_as"]})

    append_event(
        run_dir,
        "artifact_event",
        {
            "kind": "repair_tier2_applied",
            "artifact_type": type_slug,
            "artifact_id": art_id,
            "applied": applied,
            "quarantined": [q["section"] for q in quarantined],
        },
    )
    return {"ok": True, "tier": 2, "applied": applied, "quarantined": quarantined}
