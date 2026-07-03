from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.store import artifact
from kagami.store.atomic import atomic_write
from kagami.store.ids import mint_id
from kagami.store.locking import acquire_run_lock
from kagami.timeutil import utc_now_iso

MAX_ASK_BATCH = 5
FORM_LADDER = ("confirm", "menu", "rank", "free-text")


class LedgerError(Exception):
    pass


def _ledger_dir(run_dir: Path) -> Path:
    return run_dir / "ledger"


def _entry_path(run_dir: Path, q_id: str) -> Path:
    return _ledger_dir(run_dir) / f"{q_id}.yaml"


def _read_entry(run_dir: Path, q_id: str) -> dict:
    path = _entry_path(run_dir, q_id)
    if not path.is_file():
        raise LedgerError(f"no ledger entry '{q_id}'")
    return yaml.safe_load(path.read_text())


def _write_entry(run_dir: Path, entry: dict) -> None:
    _ledger_dir(run_dir).mkdir(parents=True, exist_ok=True)
    atomic_write(_entry_path(run_dir, entry["id"]), yaml.safe_dump(entry, sort_keys=False))


def _validate_candidate(question: dict) -> None:
    unprimed = bool(question.get("unprimed"))
    if not unprimed:
        if not question.get("target"):
            raise LedgerError(
                "candidate question missing 'target' (FR-22: every question other than "
                "the two unprimed E6 questions requires a non-empty target)"
            )
        if not question.get("leverage_class"):
            raise LedgerError(
                "candidate question missing 'leverage_class' (FR-22: every question other "
                "than the two unprimed E6 questions requires a non-empty leverage class)"
            )

    form = question.get("form")
    if form is not None and form not in FORM_LADDER:
        raise LedgerError(f"'{form}' is not a valid question form; must be one of {FORM_LADDER}")
    if form == "free-text" and not unprimed and not question.get("cheaper_forms_rejected"):
        raise LedgerError(
            "free-text form requires 'cheaper_forms_rejected: true' (FR-23: cheapest "
            "question form first — free text only once confirm/menu/rank were considered "
            "and rejected)"
        )


def emit_batch(run_dir: Path, questions: list[dict]) -> dict:
    """FR-18/FR-21/FR-22: the single-threaded ASK step.

    Refuses a batch over 5; every candidate question except the two unprimed
    E6 questions must declare a target and leverage class. Validates the
    whole batch before writing anything, so a rejected batch has no partial
    side effects.
    """
    if len(questions) > MAX_ASK_BATCH:
        raise LedgerError(
            f"ASK batch of {len(questions)} exceeds the maximum of {MAX_ASK_BATCH} (AD-8)"
        )

    for question in questions:
        _validate_candidate(question)

    now = utc_now_iso()
    ids = []
    for question in questions:
        q_id = mint_id("q-")
        entry = {
            "id": q_id,
            "target": question.get("target") or "",
            "leverage_class": question.get("leverage_class") or "",
            "form": question.get("form"),
            "answer": question.get("default"),
            "default_applied": False,
            "consumed_by": [],
            "asked_at": now,
            "answered_at": None,
            "version": 1,
        }
        _write_entry(run_dir, entry)
        append_event(
            run_dir,
            "question_event",
            {
                "kind": "asked",
                "id": q_id,
                "target": entry["target"],
                "leverage_class": entry["leverage_class"],
                "form": entry["form"],
                "unprimed": bool(question.get("unprimed")),
            },
        )
        ids.append(q_id)

    return {"ok": True, "ids": ids}


def apply_deferred_default(run_dir: Path, target: str, leverage_class: str, default_value) -> dict:
    """FR-17: a deferrable unknown's default is recorded even though nothing was asked."""
    q_id = mint_id("q-")
    entry = {
        "id": q_id,
        "target": target,
        "leverage_class": leverage_class,
        "form": None,
        "answer": default_value,
        "default_applied": True,
        "consumed_by": [],
        "asked_at": None,
        "answered_at": utc_now_iso(),
        "version": 1,
    }
    _write_entry(run_dir, entry)
    append_event(
        run_dir,
        "question_event",
        {"kind": "deferred_default_applied", "id": q_id, "target": target},
    )
    return {"ok": True, "id": q_id}


def answer_question(run_dir: Path, q_id: str, answer) -> dict:
    with acquire_run_lock(run_dir / ".lock"):
        entry = _read_entry(run_dir, q_id)
        entry["answer"] = answer
        entry["default_applied"] = False
        entry["answered_at"] = utc_now_iso()
        _write_entry(run_dir, entry)

    append_event(run_dir, "question_event", {"kind": "answered", "id": q_id})
    return {"ok": True, "id": q_id, "version": entry["version"]}


def revise_answer(run_dir: Path, q_id: str, new_answer) -> dict:
    """The E5 revision path (AD-8, AD-17): changing your mind stales dependents."""
    with acquire_run_lock(run_dir / ".lock"):
        entry = _read_entry(run_dir, q_id)
        entry["answer"] = new_answer
        entry["default_applied"] = False
        entry["answered_at"] = utc_now_iso()
        entry["version"] += 1
        _write_entry(run_dir, entry)

    staled = artifact.mark_dependents_stale(run_dir, q_id, entry["version"])
    append_event(run_dir, "question_event", {"kind": "revised", "id": q_id, "version": entry["version"]})
    return {"ok": True, "id": q_id, "version": entry["version"], "staled": staled}


def consume_answer(run_dir: Path, q_id: str, consuming_type: str, consuming_id: str) -> dict:
    """FR-18 CONSUME: write the answer, pin elicited_from, stale dependents."""
    entry = _read_entry(run_dir, q_id)
    if entry.get("answered_at") is None:
        raise LedgerError(f"cannot consume unanswered ledger entry '{q_id}'")

    ledger_ref = f"{q_id}@v{entry['version']}"
    pin_result = artifact.pin_elicited_from(run_dir, consuming_type, consuming_id, ledger_ref)

    consuming_ref = f"{consuming_id}@v{pin_result['version']}"
    with acquire_run_lock(run_dir / ".lock"):
        entry = _read_entry(run_dir, q_id)
        if consuming_ref not in entry["consumed_by"]:
            entry["consumed_by"].append(consuming_ref)
            _write_entry(run_dir, entry)

    staled = (
        artifact.mark_dependents_stale(run_dir, consuming_id, pin_result["version"])
        if pin_result["changed"]
        else []
    )
    append_event(
        run_dir,
        "question_event",
        {"kind": "consumed", "id": q_id, "consuming_artifact": consuming_id},
    )
    return {"ok": True, "elicited_from": ledger_ref, "staled": staled}


def apply_default_for_unanswered_blocker(
    run_dir: Path, q_id: str, artifact_type: str, artifact_id: str
) -> dict:
    """FR-20: no silent blocking — apply the recorded default and flag `provisional`."""
    with acquire_run_lock(run_dir / ".lock"):
        entry = _read_entry(run_dir, q_id)
        if entry.get("answer") is None:
            raise LedgerError(f"ledger entry '{q_id}' has no recorded default to apply")
        entry["default_applied"] = True
        entry["answered_at"] = utc_now_iso()
        _write_entry(run_dir, entry)

    ledger_ref = f"{q_id}@v{entry['version']}"
    artifact.pin_elicited_from(run_dir, artifact_type, artifact_id, ledger_ref)
    artifact.flag_provisional(run_dir, artifact_type, artifact_id)
    provisional_count = artifact.count_provisional(run_dir)

    append_event(
        run_dir,
        "question_event",
        {"kind": "blocker_defaulted", "id": q_id, "artifact_id": artifact_id},
    )
    return {"ok": True, "id": q_id, "provisional_count": provisional_count}


def resolve_via_edit(run_dir: Path, q_id: str) -> dict:
    """FR-19: a direct edit resolves the unknown — no redundant question follows."""
    with acquire_run_lock(run_dir / ".lock"):
        entry = _read_entry(run_dir, q_id)
        if entry.get("answered_at") is not None:
            return {"ok": True, "id": q_id, "already_resolved": True}
        entry["answer"] = entry.get("answer") or "[resolved via direct edit]"
        entry["default_applied"] = False
        entry["answered_at"] = utc_now_iso()
        _write_entry(run_dir, entry)

    append_event(run_dir, "question_event", {"kind": "resolved_via_edit", "id": q_id})
    return {"ok": True, "id": q_id, "already_resolved": False}


def resolve_questions_for_target(run_dir: Path, target: str) -> list[str]:
    ledger_dir = _ledger_dir(run_dir)
    if not ledger_dir.exists():
        return []

    resolved = []
    for path in ledger_dir.glob("*.yaml"):
        entry = yaml.safe_load(path.read_text())
        if entry.get("target") == target and entry.get("answered_at") is None:
            resolve_via_edit(run_dir, entry["id"])
            resolved.append(entry["id"])
    return resolved


def scan_and_resolve(run_dir: Path, type_slug: str, art_id: str) -> dict:
    """Wraps `kagami scan` (AD-16) with FR-19: a saved edit resolves its unknown."""
    result = artifact.scan(run_dir, type_slug, art_id)
    resolved = []
    if result.get("changed"):
        for section in result.get("changed_sections", []):
            target = f"{type_slug}.{section['title']}"
            resolved.extend(resolve_questions_for_target(run_dir, target))
    result["resolved_questions"] = resolved
    return result


def create_frame_artifact(
    run_dir: Path, fields: dict, sections: dict, unprimed_question_id: str, registry=None
) -> dict:
    """FR-24/AD-9: the Frame draft cannot be created before the unprimed answer exists."""
    assert_unprimed_recorded(run_dir, unprimed_question_id)
    return artifact.create_artifact(run_dir, "inquiry-frame", fields, sections, registry=registry)


def assert_unprimed_recorded(run_dir: Path, q_id: str) -> None:
    """FR-24: ask-before-show — refuse to proceed until the unprimed answer exists."""
    try:
        entry = _read_entry(run_dir, q_id)
    except LedgerError:
        raise LedgerError(
            f"Frame unprimed question '{q_id}' has not been recorded; "
            "AI framing output may not be produced before it (FR-24, AD-9)"
        ) from None
    if entry.get("answered_at") is None:
        raise LedgerError(
            f"Frame unprimed question '{q_id}' is not yet answered; "
            "AI framing output may not be produced before it (FR-24, AD-9)"
        )
