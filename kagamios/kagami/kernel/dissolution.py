from pathlib import Path

from kagami.kernel.entry import ENTRY_MODES
from kagami.registry import load_registry
from kagami.store.artifact import (
    create_artifact,
    human_write_section,
    is_dissolution_memo_accepted,
    pin_dependency,
    read_current,
    update_frontmatter_field,
)

DISSOLUTION_MEMO_TYPE = "dissolution-memo"
WHAT_WAS_LEARNED_FIELD = "what_was_learned"
REVIVAL_CONDITIONS_FIELD = "revival_conditions"
SALVAGED_FRAGMENTS_FIELD = "salvaged_fragments"


class DissolutionError(Exception):
    pass


def draft_dissolution_memo(
    run_dir: Path,
    intuition_summary: str,
    dissolving_evidence: list,
    dissolving_ledger_refs: list | None = None,
    registry=None,
) -> dict:
    """FR-7/FR-9: a dissolution is documented, not merely a run marked
    "abandoned" — `depends_on`/`elicited_from` (and the `what_dissolved_it`
    field itself) must trace back to the specific evidence that dissolved
    the intuition; an empty citation is refused outright.
    """
    if not dissolving_evidence:
        raise DissolutionError(
            "a Dissolution Memo must cite the specific evidence that dissolved the intuition "
            "(FR-7/FR-9) — depends_on/what_dissolved_it cannot be empty"
        )

    registry = registry or load_registry()
    return create_artifact(
        run_dir,
        DISSOLUTION_MEMO_TYPE,
        {
            "depends_on": list(dissolving_evidence),
            "elicited_from": list(dissolving_ledger_refs or []),
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "what_dissolved_it": list(dissolving_evidence),
            SALVAGED_FRAGMENTS_FIELD: [],
        },
        sections={
            "intuition_summary": intuition_summary,
            WHAT_WAS_LEARNED_FIELD: "",
            REVIVAL_CONDITIONS_FIELD: "",
        },
        registry=registry,
    )


def record_what_was_learned(run_dir: Path, art_id: str, content: str) -> dict:
    """FR-7: the researcher's own account of what they learned — written
    through the human-edit-surface path, never a drafting role's write."""
    return human_write_section(run_dir, DISSOLUTION_MEMO_TYPE, art_id, WHAT_WAS_LEARNED_FIELD, content)


def record_revival_conditions(run_dir: Path, art_id: str, content: str) -> dict:
    """FR-7: explicit revival conditions, in the researcher's own words."""
    return human_write_section(run_dir, DISSOLUTION_MEMO_TYPE, art_id, REVIVAL_CONDITIONS_FIELD, content)


def spin_off_salvaged_fragment(
    run_dir: Path,
    dissolution_memo_id: str,
    raw_capture: str,
    entry_mode: str = "intuition-first",
    registry=None,
) -> dict:
    """PRD Glossary — Dissolution Memo: any salvageable fragment is spun off
    as a new Intuition Note (never inlined as free text on the memo) and
    pinned onto `salvaged_fragments` — a real artifact a future run can
    cite, not a note-to-self."""
    if entry_mode not in ENTRY_MODES:
        raise DissolutionError(f"'{entry_mode}' is not a recognized entry mode; must be one of {ENTRY_MODES}")

    registry = registry or load_registry()
    note = create_artifact(
        run_dir,
        "intuition-note",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "human",
            "summary": "",
            "entry_mode": entry_mode,
        },
        sections={"raw_capture": raw_capture},
        registry=registry,
    )

    def _append_fragment(current):
        fragments = list(current or [])
        fragments.append(pin_dependency(note["id"], note["version"]))
        return fragments

    update_frontmatter_field(
        run_dir,
        DISSOLUTION_MEMO_TYPE,
        dissolution_memo_id,
        SALVAGED_FRAGMENTS_FIELD,
        _append_fragment,
        "artifact_event",
        {
            "kind": "salvaged_fragment_spun_off",
            "artifact_type": DISSOLUTION_MEMO_TYPE,
            "artifact_id": dissolution_memo_id,
            "intuition_note_id": note["id"],
        },
    )

    return {"ok": True, "intuition_note_id": note["id"]}


def validate_dissolution_exit(run_dir: Path, art_id: str, registry=None) -> dict:
    """FR-7/FR-9: "complete", not merely accepted — every minimal-profile
    section is populated, mirroring `locate.validate_locate_exit`."""
    registry = registry or load_registry()
    schema = registry.get_artifact_schema(DISSOLUTION_MEMO_TYPE)
    frontmatter, sections = read_current(run_dir, DISSOLUTION_MEMO_TYPE, art_id)
    section_bodies = {s.title: s.body for s in sections}
    violations = []

    if frontmatter.get("status") != "accepted":
        violations.append(f"dissolution memo {art_id} is not yet accepted")

    for field_name, field_spec in schema.fields.items():
        if field_spec.profile != "minimal":
            continue
        value = frontmatter.get(field_name, section_bodies.get(field_name))
        if value in (None, ""):
            violations.append(f"dissolution memo {art_id} missing minimal-profile field '{field_name}'")

    return {"ok": len(violations) == 0, "violations": violations}


def check_dissolution_terminal(run_dir: Path) -> dict:
    """FR-7: Dissolved carries the same standing as Decided or an accepted
    Gap Register — checkable purely from artifact-store state (G1), via the
    same pattern as `kernel.locate.check_mvp_terminal`."""
    return {"ok": True, "terminal_reached": is_dissolution_memo_accepted(run_dir)}
