import json

from kagami.events import EVENT_FAMILIES
from kagami.kernel.frontier import select_and_log
from kagami.store import ledger
from kagami.store.artifact import (
    accept_artifact,
    attempt_ai_write,
    claim_section,
    create_artifact,
    mark_dependents_stale,
    pin_dependency,
)
from kagami.store.markdown_doc import parse_document
from kagami.store.read import read_artifact
from kagami.store.run import open_run


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _events(run_dir):
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_every_epic_1_operation_logs_a_correctly_tagged_event(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    open_run(run_id="run-coverage", output_root=tmp_path / "_out")
    run_dir = tmp_path / "_out" / "runs" / "run-coverage"

    # artifact_event: created, section_claimed, ai_write, proposed_diff_quarantined, accepted
    dep = create_artifact(
        run_dir, "field-map", _base_fields(), sections={"scope": "draft", "alternative_cut": "cut-a"}
    )
    consumer = create_artifact(
        run_dir,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"statement": "x"},
    )
    art_dir = run_dir / "artifacts" / "field-map" / dep["id"]
    import yaml

    meta = yaml.safe_load((art_dir / "meta.yaml").read_text())
    section_id = meta["sections"][0]["id"]
    claim_section(run_dir, "field-map", dep["id"], section_id, "worker-1")
    attempt_ai_write(run_dir, "field-map", dep["id"], "alternative_cut", "revised cut")

    current_text = (art_dir / "current.md").read_text()
    (art_dir / "current.md").write_text(current_text.replace("revised cut", "researcher's own words"))
    from kagami.store.artifact import scan

    scan(run_dir, "field-map", dep["id"])  # human_edit
    attempt_ai_write(run_dir, "field-map", dep["id"], "alternative_cut", "ai overwrite attempt")  # quarantined

    accept_artifact(run_dir, "gap-register", consumer["id"], "\n".join(f"l{i}" for i in range(6)))

    # human_edit already covered by scan() above.

    # question_event: asked, answered, consumed, revised, deferred_default_applied,
    # blocker_defaulted, resolved_via_edit
    emitted = ledger.emit_batch(
        run_dir, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu", "default": "1,2"}]
    )
    q_id = emitted["ids"][0]
    ledger.answer_question(run_dir, q_id, "1,2,4")
    ledger.consume_answer(run_dir, q_id, "field-map", dep["id"])
    ledger.revise_answer(run_dir, q_id, "1,2")
    ledger.apply_deferred_default(run_dir, "field-map.other", "L2", "background")

    blocker = ledger.emit_batch(
        run_dir,
        [{"target": "gap-register.statement", "leverage_class": "L5", "form": "confirm", "default": "meaningful"}],
    )
    blocker_id = blocker["ids"][0]
    another = create_artifact(run_dir, "gap-register", _base_fields(), sections={"statement": "y"})
    ledger.apply_default_for_unanswered_blocker(run_dir, blocker_id, "gap-register", another["id"])

    edit_target_question = ledger.emit_batch(
        run_dir, [{"target": "gap-register.statement", "leverage_class": "L5", "form": "confirm"}]
    )
    ledger.resolve_via_edit(run_dir, edit_target_question["ids"][0])

    # frontier_decision
    select_and_log(run_dir, {"deferred_work": ["some-item"]})

    # retrieval: summary_read, full_text_pull
    read_artifact(run_dir, "deepen", "field-map", dep["id"], "summary")
    read_artifact(run_dir, "deepen", "field-map", dep["id"], "full")

    events = _events(run_dir)
    assert events, "expected events to have been logged"

    for event in events:
        assert event["family"] in EVENT_FAMILIES, f"unknown family {event['family']!r}"
        assert "timestamp" in event

    kinds_by_family = {}
    for event in events:
        kinds_by_family.setdefault(event["family"], set()).add(event.get("kind"))

    assert kinds_by_family["state_transition"] == {"run_opened"}
    assert {"created", "section_claimed", "ai_write", "proposed_diff_quarantined", "accepted", "staled"} <= (
        kinds_by_family["artifact_event"]
    )
    assert kinds_by_family["human_edit"] == {"scan_detected_change"}
    assert {
        "asked",
        "answered",
        "consumed",
        "revised",
        "deferred_default_applied",
        "blocker_defaulted",
        "resolved_via_edit",
    } <= kinds_by_family["question_event"]
    assert kinds_by_family["frontier_decision"] == {None}
    assert kinds_by_family["retrieval"] == {"summary_read", "full_text_pull"}


def test_deleting_the_event_log_has_zero_effect_on_subsequent_behavior(tmp_path):
    """FR-36/AD-11: a run with its trace deleted behaves identically to one
    with the trace intact — no runtime code path reads events.jsonl back."""
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"scope": "draft"})
    emitted = ledger.emit_batch(
        tmp_path, [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu", "default": "1,2"}]
    )
    q_id = emitted["ids"][0]
    ledger.answer_question(tmp_path, q_id, "1,2,4")

    (tmp_path / "events.jsonl").unlink()

    # Every subsequent operation must still work with no event log present.
    result = ledger.consume_answer(tmp_path, q_id, "field-map", dep["id"])
    assert result["ok"] is True

    art_dir = tmp_path / "artifacts" / "field-map" / dep["id"]
    frontmatter, _ = parse_document((art_dir / "current.md").read_text())
    assert any(ref.startswith(q_id) for ref in frontmatter["elicited_from"])

    # The log is simply recreated by the next append — nothing depended on
    # its prior contents or even its prior existence.
    assert (tmp_path / "events.jsonl").is_file()


def test_mark_dependents_stale_events_use_artifact_event_family(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"scope": "draft"})
    dependent = create_artifact(
        tmp_path,
        "gap-register",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"statement": "x"},
    )

    mark_dependents_stale(tmp_path, dep["id"], dependency_new_version=2)

    events = _events(tmp_path)
    staled_events = [e for e in events if e.get("kind") == "staled"]
    assert len(staled_events) == 1
    assert staled_events[0]["family"] == "artifact_event"
    assert staled_events[0]["artifact_id"] == dependent["id"]
