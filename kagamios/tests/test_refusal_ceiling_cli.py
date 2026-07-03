import json

from kagami.cli import main


def _repeat_bad_frame_complete(run_id, n):
    """A call guaranteed to fail identically every time: `--fields` isn't
    valid JSON, so `json.loads` raises before any state mutation — the
    same (entrypoint, target) refused over and over, exactly the
    retry-storm shape FR-48 exists to catch."""
    results = []
    for _ in range(n):
        main(
            [
                "frame", "complete", "--run-id", run_id,
                "--unprimed-answer", "x", "--scope-answer", "y",
                "--fields", "not-valid-json", "--sections", "{}", "--summary", "z",
            ]
        )
    return results


def test_identical_refusals_escalate_to_requires_researcher_at_the_ceiling(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-ceiling-test"])
    capsys.readouterr()

    outcomes = []
    for _ in range(4):
        main(
            [
                "frame", "complete", "--run-id", "run-ceiling-test",
                "--unprimed-answer", "x", "--scope-answer", "y",
                "--fields", "not-valid-json", "--sections", "{}", "--summary", "z",
            ]
        )
        outcomes.append(json.loads(capsys.readouterr().out))

    # Default ceiling is 3: attempts 1-2 are ordinary refusals, attempt 3
    # is the one that crosses it, attempt 4 stays escalated.
    assert [o.get("status") for o in outcomes] == [None, None, "requires_researcher", "requires_researcher"]
    assert outcomes[2]["consecutive_refusals"] == 3
    assert all(o["ok"] is False for o in outcomes)


def test_requires_researcher_never_enters_the_question_ledger(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-ceiling-ledger-test"])
    capsys.readouterr()

    for _ in range(3):
        main(
            [
                "frame", "complete", "--run-id", "run-ceiling-ledger-test",
                "--unprimed-answer", "x", "--scope-answer", "y",
                "--fields", "not-valid-json", "--sections", "{}", "--summary", "z",
            ]
        )
        capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-ceiling-ledger-test"
    ledger_dir = run_dir / "ledger"
    # No ledger entries were ever created by the escalation path — a
    # requires_researcher response is a synchronous CLI reply, never a
    # scheduled question (AD-8, AD-14).
    assert not ledger_dir.exists() or not any(ledger_dir.glob("*.yaml"))


def test_a_different_call_does_not_inherit_another_calls_refusal_streak(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-ceiling-independent"])
    capsys.readouterr()

    # Two failing calls against one bad payload...
    for _ in range(2):
        main(
            [
                "frame", "complete", "--run-id", "run-ceiling-independent",
                "--unprimed-answer", "x", "--scope-answer", "y",
                "--fields", "not-valid-json", "--sections", "{}", "--summary", "z",
            ]
        )
        capsys.readouterr()

    # ...then a single failing call with *different* content — a
    # different target, so it should not already be escalated.
    main(
        [
            "frame", "complete", "--run-id", "run-ceiling-independent",
            "--unprimed-answer", "x", "--scope-answer", "y",
            "--fields", "still-not-json", "--sections", "{}", "--summary", "z",
        ]
    )
    result = json.loads(capsys.readouterr().out)
    assert result.get("status") != "requires_researcher"


def test_a_successful_call_is_never_escalated(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    exit_code = main(["run", "open", "--run-id", "run-ceiling-success"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert "status" not in result


def test_a_repeated_violations_check_never_escalates_even_past_the_ceiling(tmp_path, monkeypatch, capsys):
    """Discovered live during the Story 7.5 toy run: validate_deepen_exit
    (and its siblings validate_locate_exit, validate_landscape_synthesis,
    validate_minimal_profile) return {"ok": False, "violations": [...]}
    as their *normal* not-yet-satisfied result, not a real refusal — a
    researcher legitimately re-checking the same incomplete artifact more
    than the ceiling's worth of times (while fixing it one field at a
    time) must never see requires_researcher for that."""
    from kagami.store.artifact import create_artifact
    from kagami.store.run import open_run

    monkeypatch.chdir(tmp_path)
    open_run(run_id="run-violations-check", output_root=tmp_path / "_kagami-output")
    run_dir = tmp_path / "_kagami-output" / "runs" / "run-violations-check"
    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        {
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "", "representative_papers": [{"paper_id": "ppr-1", "human_read": False}],
        },
        sections={"evolution": "draft text"},
    )
    capsys.readouterr()

    outcomes = []
    for _ in range(5):
        main(["dossier", "validate-deepen-exit", "--run-id", "run-violations-check", "--art-id", dossier["id"]])
        outcomes.append(json.loads(capsys.readouterr().out))

    assert all(o["ok"] is False for o in outcomes)  # genuinely still incomplete every time
    assert all(o.get("status") != "requires_researcher" for o in outcomes)
    assert all("violations" in o for o in outcomes)
