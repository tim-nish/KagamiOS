from pathlib import Path

from kagami.registry import load_registry
from kagami.store.artifact import (
    attempt_ai_write,
    create_artifact,
    human_write_section,
    is_gap_register_accepted,
    read_current,
)

GAP_REGISTER_TYPE = "gap-register"
WHY_DOES_THIS_GAP_EXIST_FIELD = "why_does_this_gap_exist"
MEANINGFUL_TO_ME_FIELD = "meaningful_to_me"
MICRO_PROBE_EVIDENCE_FIELD = "micro_probe_evidence"

WHY_DOES_THIS_GAP_EXIST_OPTIONS = (
    "hard",
    "uninteresting",
    "impossible",
    "recently_filled",
    "genuinely_open",
)

MEANINGFUL_TO_ME_OPTIONS = ("meaningful", "real-but-not-mine", "suspicious")


class LocateError(Exception):
    pass


def create_gap_register(run_dir: Path, statement: str, evidence_of_absence: str, registry=None) -> dict:
    """Story 7.5: discovered missing while driving the golden toy run —
    `locate_write` only ever writes a field on an *already-existing* Gap
    Register; nothing in Epic 4 exposed how that artifact comes to exist
    through the chokepoint. Minimal CLI-reachable creation path.

    `why_does_this_gap_exist` and `meaningful_to_me` are schema-typed as
    `enum` fields but `locate_write`/`mark_gap_meaningful` reach them
    through `attempt_ai_write`, which only resolves *sections* (parsed
    markdown bodies), never frontmatter fields directly — so both must be
    seeded here as empty placeholder sections or every later write to them
    is refused with "no section named ...". This exact mismatch was
    already worked around in `tests/test_locate.py`'s own fixture helper;
    this function had missed it until the toy run's real CLI-driven write
    hit it live, refusing on the first attempt (see
    story-7.5-verification.md).
    """
    registry = registry or load_registry()
    return create_artifact(
        run_dir,
        GAP_REGISTER_TYPE,
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
        },
        sections={
            "statement": statement,
            "evidence_of_absence": evidence_of_absence,
            "why_does_this_gap_exist": "",
            "meaningful_to_me": "",
        },
        registry=registry,
    )


def locate_write(run_dir: Path, art_id: str, field_name: str, content: str, registry=None) -> dict:
    """PRD Glossary — Gap Register: a candidate gap is never legitimate
    without its mandatory `why_does_this_gap_exist` explanation — an absence
    from the record alone is not a gap (AC1). `meaningful_to_me` (and any
    other schema `author: human` field, e.g. `micro_probe_evidence`) is
    refused here by the same generic FR-31 write-guard every drafting role
    goes through (`attempt_ai_write`) — this path adds no override (FR-4).
    """
    if field_name == WHY_DOES_THIS_GAP_EXIST_FIELD and content not in WHY_DOES_THIS_GAP_EXIST_OPTIONS:
        raise LocateError(
            f"'{WHY_DOES_THIS_GAP_EXIST_FIELD}' must be one of {WHY_DOES_THIS_GAP_EXIST_OPTIONS}, "
            f"got {content!r} — a candidate gap needs a real explanation of why it exists, not "
            "just its absence from the record (PRD Glossary — Gap Register)"
        )

    return attempt_ai_write(run_dir, GAP_REGISTER_TYPE, art_id, field_name, content, registry=registry)


def mark_gap_meaningful(run_dir: Path, art_id: str, disposition: str) -> dict:
    """FR-4/FR-31: the gap-meaningfulness leg of the constitutive triad —
    only the researcher marks a Gap Register entry `meaningful_to_me`,
    through the human-edit-surface path, never a drafting role's path.
    """
    if disposition not in MEANINGFUL_TO_ME_OPTIONS:
        raise LocateError(
            f"'{MEANINGFUL_TO_ME_FIELD}' must be one of {MEANINGFUL_TO_ME_OPTIONS}, got {disposition!r}"
        )
    return human_write_section(run_dir, GAP_REGISTER_TYPE, art_id, MEANINGFUL_TO_ME_FIELD, disposition)


def record_micro_probe_evidence(run_dir: Path, art_id: str, evidence_ref: str) -> dict:
    """PRD Glossary — Micro-probe: a researcher-run result is admitted as
    evidence for exactly one Gap Register field and mints no artifact of its
    own — this writes only the `micro_probe_evidence` field on the existing
    Gap Register entry, through the same human-edit-surface path as
    `mark_gap_meaningful`, never `create_artifact`.
    """
    return human_write_section(run_dir, GAP_REGISTER_TYPE, art_id, MICRO_PROBE_EVIDENCE_FIELD, evidence_ref)


def validate_locate_exit(run_dir: Path, art_id: str, registry=None) -> dict:
    """FR-11/FR-16: Locate's exit criterion — the Gap Register reaches
    accepted only once every minimal-profile section, including
    `why_does_this_gap_exist` and the human `meaningful_to_me` mark, is
    populated, not merely drafted.
    """
    registry = registry or load_registry()
    schema = registry.get_artifact_schema(GAP_REGISTER_TYPE)
    frontmatter, sections = read_current(run_dir, GAP_REGISTER_TYPE, art_id)
    section_bodies = {s.title: s.body for s in sections}
    violations = []

    if frontmatter.get("status") != "accepted":
        violations.append(f"gap register {art_id} is not yet accepted")

    for field_name, field_spec in schema.fields.items():
        if field_spec.profile != "minimal":
            continue
        value = frontmatter.get(field_name, section_bodies.get(field_name))
        if value in (None, ""):
            violations.append(f"gap register {art_id} missing minimal-profile field '{field_name}'")

    return {"ok": len(violations) == 0, "violations": violations}


def check_mvp_terminal(run_dir: Path) -> dict:
    """PRD §7.1: an accepted Gap Register is MVP's terminal deliverable.
    Checkable purely from artifact-store state (G1/FR-36: no runtime
    behavior may depend on reading the event log back) — Decided remains
    unreachable by construction since Propose/Decide don't exist yet.
    """
    return {"ok": True, "terminal_reached": is_gap_register_accepted(run_dir)}
