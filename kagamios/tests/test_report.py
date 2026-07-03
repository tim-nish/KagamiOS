import json

import pytest

from kagami.kernel.report import ReportError, report_llm_call
from kagami.store.run import open_run


def _open(tmp_path):
    open_run(run_id="run-report", output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / "run-report"


def test_report_llm_call_appends_a_validated_event(tmp_path):
    run_dir = _open(tmp_path)
    result = report_llm_call(
        run_dir,
        role="scout",
        operation_class="paper_card_extraction",
        model_tier="cheap-model",
        tokens_in=100,
        tokens_out=20,
        cache_hit=False,
        call_id="call-1",
    )
    assert result["ok"] is True

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    llm_calls = [e for e in events if e["family"] == "llm_call"]
    assert len(llm_calls) == 1
    assert llm_calls[0]["role"] == "scout"
    assert llm_calls[0]["operation_class"] == "paper_card_extraction"
    assert llm_calls[0]["model_tier"] == "cheap-model"
    assert llm_calls[0]["tokens_in"] == 100
    assert llm_calls[0]["tokens_out"] == 20
    assert llm_calls[0]["cache_hit"] is False
    assert llm_calls[0]["call_id"] == "call-1"


def test_a_duplicate_call_id_is_refused_not_double_appended(tmp_path):
    run_dir = _open(tmp_path)
    report_llm_call(
        run_dir, "scout", "paper_card_extraction", "cheap-model", 100, 20, False, "call-1"
    )
    with pytest.raises(ReportError):
        report_llm_call(
            run_dir, "scout", "paper_card_extraction", "cheap-model", 100, 20, False, "call-1"
        )

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    llm_calls = [e for e in events if e["family"] == "llm_call"]
    assert len(llm_calls) == 1


def test_two_different_call_ids_both_land(tmp_path):
    run_dir = _open(tmp_path)
    report_llm_call(
        run_dir, "scout", "paper_card_extraction", "cheap-model", 100, 20, False, "call-1"
    )
    report_llm_call(
        run_dir, "scout", "paper_card_extraction", "cheap-model", 50, 10, True, "call-2"
    )

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    llm_calls = [e for e in events if e["family"] == "llm_call"]
    assert len(llm_calls) == 2


def test_an_empty_call_id_is_refused(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(ReportError):
        report_llm_call(run_dir, "scout", "paper_card_extraction", "cheap-model", 1, 1, False, "")


def test_a_missing_role_is_refused_per_fr29(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(ReportError):
        report_llm_call(run_dir, "", "paper_card_extraction", "cheap-model", 1, 1, False, "call-1")
