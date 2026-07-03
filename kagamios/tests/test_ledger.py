import json

import pytest

from kagami.store import ledger
from kagami.store.artifact import create_artifact
from kagami.store.ledger import LedgerError


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "a short summary",
    }
    fields.update(overrides)
    return fields


def test_emit_batch_rejects_more_than_five_questions(tmp_path):
    questions = [
        {"target": f"field-map.scope{i}", "leverage_class": "L2", "form": "menu"} for i in range(6)
    ]
    with pytest.raises(LedgerError):
        ledger.emit_batch(tmp_path, questions)

    assert not (tmp_path / "ledger").exists()


def test_emit_batch_requires_target_and_leverage_class_except_unprimed(tmp_path):
    with pytest.raises(LedgerError):
        ledger.emit_batch(tmp_path, [{"leverage_class": "L2", "form": "menu"}])

    with pytest.raises(LedgerError):
        ledger.emit_batch(tmp_path, [{"target": "field-map.scope", "form": "menu"}])

    result = ledger.emit_batch(tmp_path, [{"form": "free-text", "unprimed": True}])
    assert result["ok"] is True


def test_emit_batch_writes_ledger_entries_and_logs_question_events(tmp_path):
    result = ledger.emit_batch(
        tmp_path,
        [
            {"target": "field-map.scope", "leverage_class": "L2", "form": "menu", "default": "1,2"},
        ],
    )
    assert result["ok"] is True
    q_id = result["ids"][0]

    entry_path = tmp_path / "ledger" / f"{q_id}.yaml"
    assert entry_path.is_file()

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    asked = [e for e in events if e["family"] == "question_event" and e["kind"] == "asked"]
    assert len(asked) == 1
    assert asked[0]["id"] == q_id
    assert asked[0]["target"] == "field-map.scope"
    assert asked[0]["leverage_class"] == "L2"


def test_free_text_form_requires_cheaper_forms_considered_and_rejected(tmp_path):
    with pytest.raises(LedgerError):
        ledger.emit_batch(
            tmp_path,
            [{"target": "field-map.scope", "leverage_class": "L2", "form": "free-text"}],
        )

    result = ledger.emit_batch(
        tmp_path,
        [
            {
                "target": "field-map.scope",
                "leverage_class": "L2",
                "form": "free-text",
                "cheaper_forms_rejected": True,
            }
        ],
    )
    assert result["ok"] is True


def test_apply_deferred_default_records_default_without_asking(tmp_path):
    result = ledger.apply_deferred_default(tmp_path, "field-map.scope", "L2", "background")
    assert result["ok"] is True

    entry = _load_entry(tmp_path, result["id"])
    assert entry["default_applied"] is True
    assert entry["answer"] == "background"
    assert entry["asked_at"] is None

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any(e["kind"] == "deferred_default_applied" for e in events)


def test_answer_question_records_answer_and_timestamp(tmp_path):
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu"}]
    )
    q_id = emitted["ids"][0]

    result = ledger.answer_question(tmp_path, q_id, "1,2,4 in scope")
    assert result["ok"] is True

    entry = _load_entry(tmp_path, q_id)
    assert entry["answer"] == "1,2,4 in scope"
    assert entry["answered_at"] is not None
    assert entry["default_applied"] is False


def test_consume_answer_pins_elicited_from_and_marks_dependents_stale(tmp_path):
    consuming = create_artifact(tmp_path, "field-map", _base_fields(), sections={"scope": "draft"})
    dependent = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[f"{consuming['id']}@v1"]),
        sections={"statement": "x"},
    )

    emitted = ledger.emit_batch(
        tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu"}]
    )
    q_id = emitted["ids"][0]
    ledger.answer_question(tmp_path, q_id, "1,2 in scope")

    result = ledger.consume_answer(tmp_path, q_id, "field-map", consuming["id"])
    assert result["ok"] is True
    assert result["elicited_from"] == f"{q_id}@v1"
    assert dependent["id"] in result["staled"]

    frontmatter, _ = _read_current(tmp_path, "field-map", consuming["id"])
    assert f"{q_id}@v1" in frontmatter["elicited_from"]

    entry = _load_entry(tmp_path, q_id)
    assert any(ref.startswith(consuming["id"]) for ref in entry["consumed_by"])


def test_consume_answer_refuses_unanswered_question(tmp_path):
    consuming = create_artifact(tmp_path, "field-map", _base_fields(), sections={"scope": "draft"})
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu"}]
    )
    q_id = emitted["ids"][0]

    with pytest.raises(LedgerError):
        ledger.consume_answer(tmp_path, q_id, "field-map", consuming["id"])


def test_revise_answer_bumps_version_and_stales_dependents(tmp_path):
    consuming = create_artifact(tmp_path, "field-map", _base_fields(), sections={"scope": "draft"})
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu"}]
    )
    q_id = emitted["ids"][0]
    ledger.answer_question(tmp_path, q_id, "1,2 in scope")
    ledger.consume_answer(tmp_path, q_id, "field-map", consuming["id"])

    result = ledger.revise_answer(tmp_path, q_id, "1,2,3 in scope")
    assert result["ok"] is True
    assert result["version"] == 2
    assert consuming["id"] in result["staled"]


def test_apply_default_for_unanswered_blocker_flags_provisional_and_counts_it(tmp_path):
    art = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})
    emitted = ledger.emit_batch(
        tmp_path,
        [{"target": "gap-register.statement", "leverage_class": "L5", "form": "confirm", "default": "meaningful"}],
    )
    q_id = emitted["ids"][0]

    result = ledger.apply_default_for_unanswered_blocker(tmp_path, q_id, "gap-register", art["id"])
    assert result["ok"] is True
    assert result["provisional_count"] == 1

    meta = _load_meta(tmp_path, "gap-register", art["id"])
    assert meta["status"] == "provisional"


def test_apply_default_for_unanswered_blocker_requires_a_recorded_default(tmp_path):
    art = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "x"})
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "gap-register.statement", "leverage_class": "L5", "form": "confirm"}]
    )
    q_id = emitted["ids"][0]

    with pytest.raises(LedgerError):
        ledger.apply_default_for_unanswered_blocker(tmp_path, q_id, "gap-register", art["id"])


def _artifact_dir(run_dir, type_slug, art_id):
    return run_dir / "artifacts" / type_slug / art_id


def test_resolve_via_edit_does_not_double_resolve(tmp_path):
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "gap-register.statement", "leverage_class": "L5", "form": "confirm"}]
    )
    q_id = emitted["ids"][0]

    first = ledger.resolve_via_edit(tmp_path, q_id)
    assert first["already_resolved"] is False

    second = ledger.resolve_via_edit(tmp_path, q_id)
    assert second["already_resolved"] is True


def test_scan_and_resolve_closes_out_pending_question_on_matching_edit(tmp_path):
    art = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "draft text"})
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "gap-register.statement", "leverage_class": "L5", "form": "confirm"}]
    )
    q_id = emitted["ids"][0]

    art_dir = _artifact_dir(tmp_path, "gap-register", art["id"])
    current_text = (art_dir / "current.md").read_text()
    (art_dir / "current.md").write_text(current_text.replace("draft text", "researcher's own words"))

    result = ledger.scan_and_resolve(tmp_path, "gap-register", art["id"])
    assert result["changed"] is True
    assert q_id in result["resolved_questions"]

    entry = _load_entry(tmp_path, q_id)
    assert entry["answered_at"] is not None


def test_scan_and_resolve_leaves_unrelated_questions_pending(tmp_path):
    art = create_artifact(tmp_path, "gap-register", _base_fields(), sections={"statement": "draft text"})
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "gap-register.some_other_field", "leverage_class": "L5", "form": "confirm"}]
    )
    q_id = emitted["ids"][0]

    art_dir = _artifact_dir(tmp_path, "gap-register", art["id"])
    current_text = (art_dir / "current.md").read_text()
    (art_dir / "current.md").write_text(current_text.replace("draft text", "researcher's own words"))

    result = ledger.scan_and_resolve(tmp_path, "gap-register", art["id"])
    assert q_id not in result["resolved_questions"]

    entry = _load_entry(tmp_path, q_id)
    assert entry["answered_at"] is None


def test_create_frame_artifact_refused_until_unprimed_question_answered(tmp_path):
    emitted = ledger.emit_batch(tmp_path, [{"form": "free-text", "unprimed": True}])
    q_id = emitted["ids"][0]

    frame_fields = _base_fields()
    with pytest.raises(LedgerError):
        ledger.create_frame_artifact(
            tmp_path, frame_fields, {"intuition_restated": "draft"}, unprimed_question_id=q_id
        )

    ledger.answer_question(tmp_path, q_id, "I suspect X is the interesting angle")

    result = ledger.create_frame_artifact(
        tmp_path, frame_fields, {"intuition_restated": "draft"}, unprimed_question_id=q_id
    )
    assert result["ok"] is True

    entry = _load_entry(tmp_path, q_id)
    frontmatter, _ = _read_current(tmp_path, "inquiry-frame", result["id"])
    assert entry["answered_at"] <= frontmatter["created"]


def _load_entry(run_dir, q_id):
    import yaml

    return yaml.safe_load((run_dir / "ledger" / f"{q_id}.yaml").read_text())


def _load_meta(run_dir, type_slug, art_id):
    import yaml

    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    return yaml.safe_load((art_dir / "meta.yaml").read_text())


def _read_current(run_dir, type_slug, art_id):
    from kagami.store.markdown_doc import parse_document

    art_dir = _artifact_dir(run_dir, type_slug, art_id)
    return parse_document((art_dir / "current.md").read_text())
