from pathlib import Path

from kagami.events import append_event
from kagami.registry import load_registry
from kagami.store.artifact import attempt_ai_write, read_current, read_version

RED_TEAM_TYPE = "candidate-direction"
RED_TEAM_FIELD = "red_team_notes"


class SkepticError(Exception):
    pass


def _find_artifact_type(run_dir: Path, art_id: str) -> str | None:
    artifacts_root = run_dir / "artifacts"
    if not artifacts_root.exists():
        return None
    for type_dir in artifacts_root.iterdir():
        if (type_dir / art_id).is_dir():
            return type_dir.name
    return None


def build_skeptic_context(run_dir: Path, type_slug: str, art_id: str) -> dict:
    """FR-27: fresh context per engagement — the artifact under attack
    (full) and its cited evidence, and nothing else.

    Deliberately omits `elicited_from` (the Question Ledger trail that
    produced the draft) — the drafting rationale Skeptic must never see —
    even though the artifact's own frontmatter retains it for provenance.
    Stateless: two calls for two different targets never share anything.
    """
    frontmatter, sections = read_current(run_dir, type_slug, art_id)

    target = {
        "type": type_slug,
        "id": art_id,
        "status": frontmatter.get("status"),
        "sections": [{"title": s.title, "body": s.body} for s in sections],
    }

    cited_evidence = []
    for pin in frontmatter.get("depends_on") or []:
        dep_id, _, version_str = pin.partition("@v")
        if not version_str:
            continue
        dep_type = _find_artifact_type(run_dir, dep_id)
        if dep_type is None:
            continue
        dep_frontmatter, _ = read_version(run_dir, dep_type, dep_id, int(version_str))
        cited_evidence.append(
            {
                "id": dep_id,
                "type": dep_type,
                "version": int(version_str),
                "summary": dep_frontmatter.get("summary", ""),
            }
        )

    return {"ok": True, "target": target, "cited_evidence": cited_evidence}


def record_skeptic_critique(
    run_dir: Path, type_slug: str, art_id: str, objection: str, evidence_cited: list[str], registry=None
) -> dict:
    """FR-27: Skeptic attacks — it never builds. An objection is always
    logged as an event (the auditable trace of the attack); the one
    schema-sanctioned artifact-write path is candidate-direction's
    red_team_notes (FR-43) — everything else is event-only, never a field
    Skeptic can single-handedly populate.
    """
    registry = registry or load_registry()

    append_event(
        run_dir,
        "gate_event",
        {
            "kind": "skeptic_critique",
            "role": "skeptic",
            "artifact_type": type_slug,
            "artifact_id": art_id,
            "objection": objection,
            "evidence_cited": evidence_cited,
        },
    )

    if type_slug == RED_TEAM_TYPE:
        return attempt_ai_write(run_dir, type_slug, art_id, RED_TEAM_FIELD, objection, registry=registry)

    return {"ok": True, "recorded_as": "event_only"}


def skeptic_write(
    run_dir: Path, type_slug: str, art_id: str, section_title: str, content: str, registry=None
) -> dict:
    """FR-27/FR-4: the only field Skeptic may ever write directly is
    candidate-direction's red_team_notes — never a constitutive-triad field,
    never any other field, on any type. Everything else is refused and
    logged as a generation-window violation attributed to the Skeptic role.
    """
    if type_slug != RED_TEAM_TYPE or section_title != RED_TEAM_FIELD:
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "generation_window_violation",
                "role": "skeptic",
                "detail": (
                    f"Skeptic attempted to write '{section_title}' on {type_slug}; only "
                    f"'{RED_TEAM_TYPE}.{RED_TEAM_FIELD}' is permitted (FR-27)"
                ),
                "artifact_id": art_id,
            },
        )
        raise SkepticError(
            f"Skeptic may only write '{RED_TEAM_TYPE}.{RED_TEAM_FIELD}', not "
            f"'{type_slug}.{section_title}' (FR-27)"
        )

    return attempt_ai_write(run_dir, type_slug, art_id, section_title, content, registry=registry)
