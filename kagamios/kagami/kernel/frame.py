from pathlib import Path

from kagami.store import ledger
from kagami.store.artifact import accept_artifact, review_artifact


def complete_frame(
    run_dir: Path,
    unprimed_answer: str,
    scope_answer: str,
    fields: dict,
    sections: dict,
    summary: str,
    registry=None,
) -> dict:
    """FR-10/FR-24: Frame's exit.

    The unprimed E6 question and the menu-form scope question are both
    answered — the unprimed one *before* the Inquiry Frame's AI-drafted
    content is created (ask-before-show, enforced by
    `ledger.create_frame_artifact`) — and the artifact then moves
    draft -> reviewed -> accepted.
    """
    unprimed = ledger.emit_batch(run_dir, [{"form": "free-text", "unprimed": True}])
    unprimed_id = unprimed["ids"][0]
    ledger.answer_question(run_dir, unprimed_id, unprimed_answer)

    scope_q = ledger.emit_batch(
        run_dir,
        [{"target": "inquiry-frame.in_scope_readings", "leverage_class": "L2", "form": "menu"}],
    )
    scope_id = scope_q["ids"][0]
    ledger.answer_question(run_dir, scope_id, scope_answer)

    created = ledger.create_frame_artifact(
        run_dir, fields, sections, unprimed_question_id=unprimed_id, registry=registry
    )
    art_id = created["id"]

    ledger.consume_answer(run_dir, unprimed_id, "inquiry-frame", art_id)
    ledger.consume_answer(run_dir, scope_id, "inquiry-frame", art_id)

    review_artifact(run_dir, "inquiry-frame", art_id)
    accept_artifact(run_dir, "inquiry-frame", art_id, summary)

    return {
        "ok": True,
        "inquiry_frame_id": art_id,
        "unprimed_question_id": unprimed_id,
        "scope_question_id": scope_id,
    }
