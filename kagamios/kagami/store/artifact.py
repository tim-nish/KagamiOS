import hashlib
from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.registry import load_registry
from kagami.store.atomic import atomic_write
from kagami.store.ids import mint_id
from kagami.store.locking import acquire_run_lock
from kagami.store.markdown_doc import Section, parse_document, render_document
from kagami.timeutil import utc_now_iso

REQUIRED_METADATA_FIELDS = (
    "id",
    "type",
    "version",
    "status",
    "depends_on",
    "elicited_from",
    "decided_by",
    "summary",
    "created",
    "updated",
)

HUMAN_TOUCHED_AUTHOR_CLASSES = ("human", "ai-drafted-human-confirmed")

SUMMARY_MIN_LINES = 5
SUMMARY_MAX_LINES = 10

GAP_REGISTER_TYPE_SLUG = "gap-register"
CANDIDATE_DIRECTION_GENERATION_WINDOW = "propose"
DISSOLUTION_MEMO_TYPE_SLUG = "dissolution-memo"


class ArtifactError(Exception):
    pass


class RejectedWriteError(ArtifactError):
    pass


def pin_dependency(dependency_id: str, version: int) -> str:
    return f"{dependency_id}@v{version}"


def missing_required_metadata_fields(fields: dict) -> list[str]:
    return [name for name in REQUIRED_METADATA_FIELDS if fields.get(name) in (None, "")]


def validate_can_accept(fields: dict) -> None:
    missing = missing_required_metadata_fields(fields)
    if missing:
        raise ArtifactError(
            f"artifact cannot reach accepted status, missing required fields: {missing} (FR-9)"
        )


def _artifact_dir(run_dir: Path, type_slug: str, art_id: str) -> Path:
    return run_dir / "artifacts" / type_slug / art_id


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_meta(meta_path: Path) -> dict:
    return yaml.safe_load(meta_path.read_text())


def _write_meta(meta_path: Path, meta: dict) -> None:
    atomic_write(meta_path, yaml.safe_dump(meta, sort_keys=False))


def _is_gate_loosened(run_dir: Path, type_slug: str) -> bool:
    """FR-5: whether this run's own researcher has approved collapsing
    `type_slug`'s review gate into a notification (`kernel/gate_trust`).
    Read directly off the manifest rather than importing the kernel module,
    keeping the store layer's chokepoints self-contained."""
    manifest_path = run_dir / "manifest.yaml"
    if not manifest_path.exists():
        return False
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    return type_slug in (manifest.get("loosened_gates") or [])


def is_gap_register_accepted(run_dir: Path) -> bool:
    """AD-9: the Candidate-Direction generation window keys off run-level
    Gap Register acceptance rather than per-cluster derived state (unlike
    every other window) — any Gap Register in the run reaching `accepted`
    opens it. Per PRD §7.1 this same fact is MVP's terminal deliverable,
    since Decided is unreachable while Propose/Decide don't exist yet.
    """
    gap_register_root = run_dir / "artifacts" / GAP_REGISTER_TYPE_SLUG
    if not gap_register_root.exists():
        return False
    return any(
        _read_meta(meta_path).get("status") == "accepted"
        for meta_path in gap_register_root.glob("*/meta.yaml")
    )


def is_dissolution_memo_accepted(run_dir: Path) -> bool:
    """FR-7: Dissolved carries the same standing as Decided or an accepted
    Gap Register — checkable purely from whether any Dissolution Memo in
    the run has reached `accepted`, the same pattern as
    `is_gap_register_accepted`."""
    memo_root = run_dir / "artifacts" / DISSOLUTION_MEMO_TYPE_SLUG
    if not memo_root.exists():
        return False
    return any(
        _read_meta(meta_path).get("status") == "accepted"
        for meta_path in memo_root.glob("*/meta.yaml")
    )


def _quarantine_premature_idea(run_dir: Path, type_slug: str, fields: dict, sections: dict) -> dict:
    """FR-46/AD-9: content generated outside its open generation window is
    refused, not merely discouraged — and never discarded or leaked into a
    legitimate artifact. It is quarantined to `premature_ideas/` instead,
    carrying the content that would have been written."""
    frontmatter = {"type": type_slug, "created": utc_now_iso(), **fields}
    section_objs = [Section(mint_id("sec-"), title, body) for title, body in sections.items()]
    doc_text = render_document(frontmatter, section_objs)

    quarantine_dir = run_dir / "premature_ideas"
    quarantine_path = quarantine_dir / f"{mint_id('premature-')}.md"
    reason = (
        f"'{type_slug}' generation window is not open: no Gap Register has reached "
        "accepted in this run yet (FR-46, AD-9)"
    )

    with acquire_run_lock(run_dir / ".lock"):
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(quarantine_path, doc_text)
        append_event(
            run_dir,
            "artifact_event",
            {
                "kind": "premature_idea_quarantined",
                "artifact_type": type_slug,
                "quarantined_as": str(quarantine_path),
                "reason": reason,
            },
        )

    return {"ok": False, "quarantined_as": str(quarantine_path), "reason": reason}


def create_artifact(
    run_dir: Path,
    type_slug: str,
    fields: dict,
    sections: dict,
    art_id: str | None = None,
    registry=None,
) -> dict:
    registry = registry or load_registry()
    schema = registry.get_artifact_schema(type_slug)

    if schema.generation_window == CANDIDATE_DIRECTION_GENERATION_WINDOW and not is_gap_register_accepted(
        run_dir
    ):
        return _quarantine_premature_idea(run_dir, type_slug, fields, sections)

    art_id = art_id or mint_id("art-")
    now = utc_now_iso()
    frontmatter = {
        "id": art_id,
        "type": type_slug,
        "version": 1,
        "status": "draft",
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
        "created": now,
        "updated": now,
        **fields,
    }

    section_objs = []
    section_meta = []
    for title, body in sections.items():
        section_id = mint_id("sec-")
        section_objs.append(Section(section_id, title, body))
        section_meta.append(
            {
                "id": section_id,
                "title": title,
                "author": "ai",
                "content_hash": _content_hash(body),
            }
        )

    doc_text = render_document(frontmatter, section_objs)
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    art_dir.mkdir(parents=True, exist_ok=False)

    with acquire_run_lock(run_dir / ".lock"):
        atomic_write(art_dir / "v1.md", doc_text)
        atomic_write(art_dir / "current.md", doc_text)
        _write_meta(
            art_dir / "meta.yaml",
            {
                "id": art_id,
                "type": type_slug,
                "current_version": 1,
                "status": "draft",
                "sections": section_meta,
                "claims": {},
                "content_hash": _content_hash(doc_text),
            },
        )
        append_event(
            run_dir, "artifact_event", {"kind": "created", "artifact_type": type_slug, "artifact_id": art_id}
        )

    return {"ok": True, "id": art_id, "path": str(art_dir), "version": 1}


def read_current(run_dir: Path, type_slug: str, art_id: str) -> tuple[dict, list[Section]]:
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    return parse_document((art_dir / "current.md").read_text())


def read_version(run_dir: Path, type_slug: str, art_id: str, version: int) -> tuple[dict, list[Section]]:
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    return parse_document((art_dir / f"v{version}.md").read_text())


def claim_section(run_dir: Path, type_slug: str, art_id: str, section_id: str, holder: str) -> bool:
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        claims = meta.setdefault("claims", {})
        existing_holder = claims.get(section_id)
        if existing_holder is not None and existing_holder != holder:
            return False
        claims[section_id] = holder
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "artifact_event",
            {
                "kind": "section_claimed",
                "artifact_type": type_slug,
                "artifact_id": art_id,
                "section_id": section_id,
                "holder": holder,
            },
        )
        return True


def reap_expired_claims(run_dir: Path, current_holder: str) -> list[dict]:
    """AD-10/AD-15: a claim carries its session lease id and expires with
    it. Called at `kagami run open` — since every open mints a fresh lease
    holder, any claim not held by the new holder belongs to a session that
    never explicitly released it (most commonly a crash) and is reaped so
    it never wedges a section forever.
    """
    artifacts_root = run_dir / "artifacts"
    reaped = []
    if not artifacts_root.exists():
        return reaped

    with acquire_run_lock(run_dir / ".lock"):
        for meta_path in artifacts_root.glob("*/*/meta.yaml"):
            meta = _read_meta(meta_path)
            claims = meta.get("claims") or {}
            expired = {sec_id: holder for sec_id, holder in claims.items() if holder != current_holder}
            if not expired:
                continue

            for sec_id in expired:
                del claims[sec_id]
            _write_meta(meta_path, meta)

            reaped_here = [
                {"artifact_id": meta["id"], "section_id": sec_id, "previous_holder": holder}
                for sec_id, holder in expired.items()
            ]
            reaped.extend(reaped_here)
            append_event(
                run_dir,
                "artifact_event",
                {
                    "kind": "claims_reaped",
                    "artifact_id": meta["id"],
                    "section_ids": list(expired),
                },
            )

    return reaped


def attempt_ai_write(
    run_dir: Path,
    type_slug: str,
    art_id: str,
    section_title: str,
    new_body: str,
    registry=None,
) -> dict:
    registry = registry or load_registry()
    schema = registry.get_artifact_schema(type_slug)
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        field_spec = schema.fields.get(section_title)
        if field_spec is not None and field_spec.author == "human":
            append_event(
                run_dir,
                "artifact_event",
                {
                    "kind": "rejected_write",
                    "artifact_type": type_slug,
                    "artifact_id": art_id,
                    "field": section_title,
                    "reason": "schema declares author: human (FR-31)",
                },
            )
            raise RejectedWriteError(
                f"AI write to '{section_title}' on {type_slug} refused: schema declares author: human (FR-31)"
            )

        meta = _read_meta(meta_path)
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        target = next((s for s in sections if s.title == section_title), None)
        if target is None:
            raise ArtifactError(f"no section named '{section_title}' on artifact {art_id}")

        section_meta = next(sm for sm in meta["sections"] if sm["id"] == target.id)

        if section_meta["author"] in HUMAN_TOUCHED_AUTHOR_CLASSES:
            diff_path = art_dir / f"proposed-diff-{mint_id('pd-')}.md"
            atomic_write(diff_path, new_body)
            append_event(
                run_dir,
                "artifact_event",
                {
                    "kind": "proposed_diff_quarantined",
                    "artifact_type": type_slug,
                    "artifact_id": art_id,
                    "field": section_title,
                    "quarantined_as": str(diff_path),
                },
            )
            return {
                "ok": False,
                "quarantined_as": str(diff_path),
                "reason": "target section is human-touched; refused and re-emitted as a proposed diff (AD-16)",
            }

        target.body = new_body
        new_text = render_document(frontmatter, sections)
        atomic_write(art_dir / "current.md", new_text)
        section_meta["content_hash"] = _content_hash(new_body)
        section_meta["author"] = "ai"
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "artifact_event",
            {"kind": "ai_write", "artifact_type": type_slug, "artifact_id": art_id, "field": section_title},
        )
        return {"ok": True}


def human_write_section(
    run_dir: Path,
    type_slug: str,
    art_id: str,
    section_title: str,
    new_body: str,
) -> dict:
    """The human-edit-surface write path (AD-6) for a schema field the
    researcher records directly — e.g. a constitutive-triad field like
    `gap-register.meaningful_to_me` (FR-4) or micro-probe evidence. Unlike
    `attempt_ai_write`, there is no `author: human` refusal (the researcher
    is exactly who is allowed to write here) and no human-touched-span
    quarantine (a researcher overwriting their own prior mark is never a
    conflict) — the section's author class is set to `human` directly.
    """
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        target = next((s for s in sections if s.title == section_title), None)
        if target is None:
            raise ArtifactError(f"no section named '{section_title}' on artifact {art_id}")

        section_meta = next(sm for sm in meta["sections"] if sm["id"] == target.id)

        target.body = new_body
        new_text = render_document(frontmatter, sections)
        atomic_write(art_dir / "current.md", new_text)
        section_meta["content_hash"] = _content_hash(new_body)
        section_meta["author"] = "human"
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "human_edit",
            {"kind": "human_write", "artifact_type": type_slug, "artifact_id": art_id, "field": section_title},
        )
        return {"ok": True}


def scan(run_dir: Path, type_slug: str, art_id: str) -> dict:
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        current_text = (art_dir / "current.md").read_text()
        current_hash = _content_hash(current_text)

        if current_hash == meta["content_hash"]:
            return {"ok": True, "changed": False, "version": meta["current_version"]}

        frontmatter, sections = parse_document(current_text)
        changed_sections = []
        for section in sections:
            section_meta = next(sm for sm in meta["sections"] if sm["id"] == section.id)
            new_hash = _content_hash(section.body)
            if new_hash != section_meta["content_hash"]:
                section_meta["content_hash"] = new_hash
                if section_meta["author"] == "ai":
                    section_meta["author"] = "ai-drafted-human-confirmed"
                changed_sections.append({"id": section.id, "title": section.title})

        new_version = meta["current_version"] + 1
        frontmatter["version"] = new_version
        frontmatter["updated"] = utc_now_iso()
        new_text = render_document(frontmatter, sections)

        atomic_write(art_dir / f"v{new_version}.md", new_text)
        atomic_write(art_dir / "current.md", new_text)
        meta["current_version"] = new_version
        meta["content_hash"] = _content_hash(new_text)
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "human_edit",
            {
                "kind": "scan_detected_change",
                "artifact_type": type_slug,
                "artifact_id": art_id,
                "version": new_version,
                "changed_sections": changed_sections,
            },
        )

        return {
            "ok": True,
            "changed": True,
            "version": new_version,
            "changed_sections": changed_sections,
        }


def review_artifact(run_dir: Path, type_slug: str, art_id: str) -> dict:
    """FR-10: draft -> reviewed, the step before the human accept gate.

    `accept_artifact` refuses to run until an artifact has passed through
    here — an AI-authored draft is never treated as `current` (accepted)
    without this intermediate human checkpoint.
    """
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        if meta["status"] != "draft":
            raise ArtifactError(
                f"cannot review artifact {art_id} in status '{meta['status']}'; expected 'draft' (FR-10)"
            )
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        frontmatter["status"] = "reviewed"
        new_version = meta["current_version"] + 1
        frontmatter["version"] = new_version
        frontmatter["updated"] = utc_now_iso()
        new_text = render_document(frontmatter, sections)

        atomic_write(art_dir / f"v{new_version}.md", new_text)
        atomic_write(art_dir / "current.md", new_text)
        meta["current_version"] = new_version
        meta["status"] = "reviewed"
        meta["content_hash"] = _content_hash(new_text)
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "artifact_event",
            {"kind": "reviewed", "artifact_type": type_slug, "artifact_id": art_id, "version": new_version},
        )

    return {"ok": True, "version": new_version}


def accept_artifact(run_dir: Path, type_slug: str, art_id: str, summary: str) -> dict:
    """FR-33: the 5-10 line summary is regenerated only at acceptance, as part
    of that version — `kagami accept` is the sole entrypoint that writes it."""
    line_count = len(summary.strip().splitlines())
    if not (SUMMARY_MIN_LINES <= line_count <= SUMMARY_MAX_LINES):
        raise ArtifactError(
            f"summary must be {SUMMARY_MIN_LINES}-{SUMMARY_MAX_LINES} lines, got {line_count} (FR-33)"
        )

    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        # FR-5: an approved gate-loosening collapses the mandatory review
        # step into a notification — accept may proceed straight from
        # 'draft'. Until that approval is recorded, the gate stays at full
        # strictness (still requires 'reviewed').
        gate_loosened = meta["status"] == "draft" and _is_gate_loosened(run_dir, type_slug)
        if meta["status"] != "reviewed" and not gate_loosened:
            raise ArtifactError(
                f"cannot accept artifact {art_id} in status '{meta['status']}'; "
                "expected 'reviewed' (FR-10: draft -> reviewed -> accepted)"
            )
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        frontmatter["summary"] = summary
        frontmatter["status"] = "accepted"
        validate_can_accept(frontmatter)

        new_version = meta["current_version"] + 1
        frontmatter["version"] = new_version
        frontmatter["updated"] = utc_now_iso()
        new_text = render_document(frontmatter, sections)

        atomic_write(art_dir / f"v{new_version}.md", new_text)
        atomic_write(art_dir / "current.md", new_text)
        meta["current_version"] = new_version
        meta["status"] = "accepted"
        meta["content_hash"] = _content_hash(new_text)
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "artifact_event",
            {"kind": "accepted", "artifact_type": type_slug, "artifact_id": art_id, "version": new_version},
        )
        if gate_loosened:
            append_event(
                run_dir,
                "gate_event",
                {"kind": "gate_loosening_notification", "artifact_type": type_slug, "artifact_id": art_id},
            )
        if type_slug == GAP_REGISTER_TYPE_SLUG:
            # PRD §7.1: an accepted Gap Register is MVP's terminal deliverable —
            # Decided is unreachable by construction since Propose/Decide don't
            # exist yet (FR-46).
            append_event(
                run_dir,
                "terminal_event",
                {"kind": "mvp_terminal_reached", "terminal": "gap-register-accepted", "artifact_id": art_id},
            )
        if type_slug == DISSOLUTION_MEMO_TYPE_SLUG:
            # FR-7: Dissolved carries the same standing as Decided or an
            # accepted Gap Register — never a lesser "abandoned" status.
            append_event(
                run_dir,
                "terminal_event",
                {"kind": "dissolution_reached", "terminal": "dissolved", "artifact_id": art_id},
            )

    return {"ok": True, "version": new_version}


def mark_dependents_stale(run_dir: Path, dependency_id: str, dependency_new_version: int) -> list[str]:
    """FR-13 / FR-18: stale anything pinning an outdated version of `dependency_id`.

    Checks both `depends_on` (artifact-to-artifact pins) and `elicited_from`
    (artifact-to-ledger-entry pins, per FR-18's CONSUME step and E5 answer
    revisions), since both use the same `id@vN` pin format.
    """
    artifacts_root = run_dir / "artifacts"
    staled = []
    if not artifacts_root.exists():
        return staled

    with acquire_run_lock(run_dir / ".lock"):
        for meta_path in artifacts_root.glob("*/*/meta.yaml"):
            current_path = meta_path.parent / "current.md"
            frontmatter, sections = parse_document(current_path.read_text())
            pins = (frontmatter.get("depends_on") or []) + (frontmatter.get("elicited_from") or [])

            staled_this_artifact = False
            for pin in pins:
                pinned_id, _, pinned_version_str = pin.partition("@v")
                if pinned_id != dependency_id or not pinned_version_str:
                    continue
                if int(pinned_version_str) < dependency_new_version:
                    staled_this_artifact = True
                break

            if staled_this_artifact:
                meta = _read_meta(meta_path)
                if meta["status"] != "stale":
                    meta["status"] = "stale"
                    _write_meta(meta_path, meta)
                frontmatter["status"] = "stale"
                atomic_write(current_path, render_document(frontmatter, sections))
                staled.append(meta["id"])
                append_event(
                    run_dir,
                    "artifact_event",
                    {
                        "kind": "staled",
                        "artifact_id": meta["id"],
                        "dependency_id": dependency_id,
                        "dependency_new_version": dependency_new_version,
                    },
                )

    return staled


def pin_elicited_from(run_dir: Path, type_slug: str, art_id: str, ledger_ref: str) -> dict:
    """FR-18 CONSUME step: pin an answered ledger entry onto a consuming artifact."""
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        elicited_from = frontmatter.setdefault("elicited_from", [])
        if ledger_ref in elicited_from:
            return {"ok": True, "version": meta["current_version"], "changed": False}
        elicited_from.append(ledger_ref)

        new_version = meta["current_version"] + 1
        frontmatter["version"] = new_version
        frontmatter["updated"] = utc_now_iso()
        new_text = render_document(frontmatter, sections)

        atomic_write(art_dir / f"v{new_version}.md", new_text)
        atomic_write(art_dir / "current.md", new_text)
        meta["current_version"] = new_version
        meta["content_hash"] = _content_hash(new_text)
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "artifact_event",
            {
                "kind": "elicited_from_pinned",
                "artifact_type": type_slug,
                "artifact_id": art_id,
                "ledger_ref": ledger_ref,
            },
        )

    return {"ok": True, "version": new_version, "changed": True}


def flag_provisional(run_dir: Path, type_slug: str, art_id: str) -> dict:
    """FR-20: flag an artifact provisional when a blocking unknown went unanswered."""
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        frontmatter["status"] = "provisional"
        new_version = meta["current_version"] + 1
        frontmatter["version"] = new_version
        frontmatter["updated"] = utc_now_iso()
        new_text = render_document(frontmatter, sections)

        atomic_write(art_dir / f"v{new_version}.md", new_text)
        atomic_write(art_dir / "current.md", new_text)
        meta["current_version"] = new_version
        meta["status"] = "provisional"
        meta["content_hash"] = _content_hash(new_text)
        _write_meta(meta_path, meta)
        append_event(
            run_dir,
            "artifact_event",
            {"kind": "flagged_provisional", "artifact_type": type_slug, "artifact_id": art_id},
        )

    return {"ok": True, "version": new_version}


def update_frontmatter_field(
    run_dir: Path,
    type_slug: str,
    art_id: str,
    field_name: str,
    updater,
    event_family: str,
    event_payload: dict,
) -> dict:
    """Generic chokepoint primitive: read-lock-mutate-write a single
    frontmatter field via `updater(current_value) -> new_value`, bumping the
    version and logging exactly one event as part of the same locked span.
    `updater` may raise to refuse the mutation entirely (nothing is written).
    """
    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    meta_path = art_dir / "meta.yaml"

    with acquire_run_lock(run_dir / ".lock"):
        meta = _read_meta(meta_path)
        frontmatter, sections = parse_document((art_dir / "current.md").read_text())

        frontmatter[field_name] = updater(frontmatter.get(field_name))

        new_version = meta["current_version"] + 1
        frontmatter["version"] = new_version
        frontmatter["updated"] = utc_now_iso()
        new_text = render_document(frontmatter, sections)

        atomic_write(art_dir / f"v{new_version}.md", new_text)
        atomic_write(art_dir / "current.md", new_text)
        meta["current_version"] = new_version
        meta["content_hash"] = _content_hash(new_text)
        _write_meta(meta_path, meta)
        append_event(run_dir, event_family, event_payload)

    return {"ok": True, "version": new_version}


def count_provisional(run_dir: Path) -> int:
    """FR-20: the provisional count surfaced at the Decide gate rather than hidden."""
    artifacts_root = run_dir / "artifacts"
    if not artifacts_root.exists():
        return 0
    count = 0
    for meta_path in artifacts_root.glob("*/*/meta.yaml"):
        meta = _read_meta(meta_path)
        if meta.get("status") == "provisional":
            count += 1
    return count
