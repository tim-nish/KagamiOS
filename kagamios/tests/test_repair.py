import json

from kagami.kernel.repair import apply_tier2_repair, repair_artifact
from kagami.store.artifact import create_artifact, mark_dependents_stale, pin_dependency


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
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_repair_resolves_at_tier0_when_artifact_is_not_stale(tmp_path):
    dossier = create_artifact(tmp_path, "cluster-dossier", _base_fields(), sections={"evolution": "x"})

    result = repair_artifact(tmp_path, "cluster-dossier", dossier["id"])
    assert result == {"ok": True, "tier": 0, "resolved": True, "needs_llm": None}

    events = _events(tmp_path)
    assert any(e["kind"] == "repair_resolved_at_tier0" for e in events)
    assert not any(e["family"] == "llm_call" for e in events)


def test_repair_escalates_to_tier1_needs_llm_work_item_when_stale(tmp_path):
    dep = create_artifact(tmp_path, "field-map", _base_fields(), sections={"cluster_name": "x"})
    dossier = create_artifact(
        tmp_path,
        "cluster-dossier",
        _base_fields(depends_on=[pin_dependency(dep["id"], 1)]),
        sections={"evolution": "x"},
    )
    mark_dependents_stale(tmp_path, dep["id"], dependency_new_version=2)

    result = repair_artifact(tmp_path, "cluster-dossier", dossier["id"])
    assert result["ok"] is True
    assert result["tier"] == 1
    assert result["resolved"] is False
    assert result["needs_llm"] == {
        "operation_class": "tier1_plausibility_check",
        "artifact_type": "cluster-dossier",
        "artifact_id": dossier["id"],
    }

    events = _events(tmp_path)
    assert any(e["kind"] == "repair_escalated_to_tier1" for e in events)
    assert not any(e["family"] == "llm_call" for e in events)


def test_tier2_applies_fix_to_an_untouched_section(tmp_path):
    dossier = create_artifact(tmp_path, "cluster-dossier", _base_fields(), sections={"frontier": "old"})

    result = apply_tier2_repair(tmp_path, "cluster-dossier", dossier["id"], {"frontier": "new content"})
    assert result["ok"] is True
    assert result["applied"] == ["frontier"]
    assert result["quarantined"] == []


def test_tier2_quarantines_a_fix_targeting_a_human_touched_section(tmp_path):
    from kagami.store.artifact import scan

    dossier = create_artifact(tmp_path, "cluster-dossier", _base_fields(), sections={"frontier": "old"})
    art_dir = tmp_path / "artifacts" / "cluster-dossier" / dossier["id"]
    current_text = (art_dir / "current.md").read_text()
    (art_dir / "current.md").write_text(current_text.replace("old", "the researcher's own words"))
    scan(tmp_path, "cluster-dossier", dossier["id"])  # flips frontier to human-confirmed

    result = apply_tier2_repair(tmp_path, "cluster-dossier", dossier["id"], {"frontier": "AI repair attempt"})
    assert result["ok"] is True
    assert result["applied"] == []
    assert len(result["quarantined"]) == 1
    assert result["quarantined"][0]["section"] == "frontier"

    from kagami.store.artifact import read_current

    _, sections = read_current(tmp_path, "cluster-dossier", dossier["id"])
    frontier = next(s for s in sections if s.title == "frontier")
    assert "researcher's own words" in frontier.body
    assert "AI repair attempt" not in frontier.body
