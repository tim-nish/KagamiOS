from pathlib import Path

from kagami.events import append_event
from kagami.store.artifact import read_current, update_frontmatter_field

LANDSCAPE_SYNTHESIS_TYPE = "landscape-synthesis"
SOLVED_OPEN_TABLE_FIELD = "solved_open_table"

STATUS_SOLVED = "solved"
STATUS_OPEN = "open"
VALID_STATUSES = (STATUS_SOLVED, STATUS_OPEN)


class SynthesizeError(Exception):
    pass


def validate_solved_open_table(rows: list[dict]) -> None:
    """PRD Glossary — Landscape Synthesis: every 'open' claim must carry
    evidence of its absence, not just an absent citation. An empty or
    missing `absence_evidence` can never satisfy this on its own, however
    thin the surrounding citation trail is.
    """
    for row in rows:
        claim = row.get("claim")
        if not claim:
            raise SynthesizeError("solved/open table row is missing a 'claim'")

        status = row.get("status")
        if status not in VALID_STATUSES:
            raise SynthesizeError(
                f"claim '{claim}' has status {status!r}; expected one of {VALID_STATUSES}"
            )

        evidence = row.get("absence_evidence")
        if status == STATUS_OPEN and not (isinstance(evidence, str) and evidence.strip()):
            raise SynthesizeError(
                f"claim '{claim}' is marked open but carries no absence_evidence — an "
                "absent citation is not evidence of a gap (PRD Glossary — Landscape Synthesis)"
            )


def validate_source_dossiers_accepted(run_dir: Path, dossier_ids: list[str]) -> None:
    """Synthesize drafts the solved/open table only from accepted Cluster
    Dossiers — never from work still in flight (Story 4.1 AC1)."""
    for art_id in dossier_ids:
        frontmatter, _ = read_current(run_dir, "cluster-dossier", art_id)
        if frontmatter.get("status") != "accepted":
            raise SynthesizeError(
                f"cluster dossier {art_id} is not accepted; Synthesize may only draft the "
                "solved/open table from accepted Cluster Dossiers"
            )


def validate_landscape_synthesis(run_dir: Path, art_id: str) -> dict:
    """Re-checks the evidence-of-absence invariant against whatever is
    currently stored — the same check `synthesize_write` runs before ever
    persisting a row, exposed here for post-hoc inspection (e.g. after a
    human hand-edits the table directly)."""
    frontmatter, _ = read_current(run_dir, LANDSCAPE_SYNTHESIS_TYPE, art_id)
    rows = frontmatter.get(SOLVED_OPEN_TABLE_FIELD) or []
    try:
        validate_solved_open_table(rows)
    except SynthesizeError as exc:
        return {"ok": False, "violations": [str(exc)]}
    return {"ok": True, "violations": []}


def synthesize_write(
    run_dir: Path, art_id: str, field_name: str, rows: list[dict], dossier_ids: list[str]
) -> dict:
    """PRD §7.1: Synthesize is confined to the solved/open table at
    minimal-profile depth for MVP — the full competing-approaches matrix
    (`competing_approaches_matrix`, `trend_directions`) is out of scope, and
    any attempt to write it is refused and logged as a generation-window
    violation, the same treatment Historian gets for writing outside
    Evolution (FR-28).
    """
    if field_name != SOLVED_OPEN_TABLE_FIELD:
        append_event(
            run_dir,
            "gate_event",
            {
                "kind": "generation_window_violation",
                "role": "synthesize",
                "detail": (
                    f"Synthesize attempted to write '{field_name}'; confined to "
                    f"'{SOLVED_OPEN_TABLE_FIELD}' at minimal-profile depth for MVP (PRD §7.1)"
                ),
                "artifact_id": art_id,
            },
        )
        raise SynthesizeError(
            f"Synthesize may only write '{SOLVED_OPEN_TABLE_FIELD}', not '{field_name}' (PRD §7.1)"
        )

    validate_source_dossiers_accepted(run_dir, dossier_ids)
    validate_solved_open_table(rows)

    return update_frontmatter_field(
        run_dir,
        LANDSCAPE_SYNTHESIS_TYPE,
        art_id,
        SOLVED_OPEN_TABLE_FIELD,
        lambda _current: rows,
        event_family="artifact_event",
        event_payload={
            "kind": "ai_write",
            "artifact_type": LANDSCAPE_SYNTHESIS_TYPE,
            "artifact_id": art_id,
            "field": SOLVED_OPEN_TABLE_FIELD,
        },
    )
