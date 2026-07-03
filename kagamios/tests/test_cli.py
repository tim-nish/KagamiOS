import json

from kagami.cli import main


def test_run_open_from_two_different_working_directories_stays_scoped(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("KAGAMI_OUTPUT_ROOT", raising=False)

    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()

    monkeypatch.chdir(project_a)
    exit_code_a = main(["run", "open", "--run-id", "run-a"])
    stdout_a = json.loads(capsys.readouterr().out)

    monkeypatch.chdir(project_b)
    exit_code_b = main(["run", "open", "--run-id", "run-b"])
    stdout_b = json.loads(capsys.readouterr().out)

    assert exit_code_a == 0
    assert exit_code_b == 0
    assert stdout_a["ok"] is True
    assert stdout_b["ok"] is True
    assert (project_a / "_kagami-output" / "runs" / "run-a").is_dir()
    assert (project_b / "_kagami-output" / "runs" / "run-b").is_dir()
    assert not (project_a / "_kagami-output" / "runs" / "run-b").exists()
    assert not (project_b / "_kagami-output" / "runs" / "run-a").exists()


def test_run_open_prints_single_line_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-single-line"])
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    json.loads(out)


def test_scan_subcommand_reports_no_change_then_a_new_version(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-scan-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-scan-test"
    result = create_artifact(
        run_dir,
        "gap-register",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "s",
        },
        sections={"statement": "draft"},
    )

    exit_code = main(["scan", "--run-id", "run-scan-test", "--type", "gap-register", "--art-id", result["id"]])
    unchanged = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert unchanged == {"ok": True, "changed": False, "version": 1}

    art_dir = run_dir / "artifacts" / "gap-register" / result["id"]
    (art_dir / "current.md").write_text(
        (art_dir / "current.md").read_text().replace("draft", "researcher edit")
    )

    exit_code = main(["scan", "--run-id", "run-scan-test", "--type", "gap-register", "--art-id", result["id"]])
    changed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert changed["changed"] is True
    assert changed["version"] == 2


def test_accept_and_read_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-accept-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-accept-test"
    result = create_artifact(
        run_dir,
        "researcher-profile",
        {
            "depends_on": [],
            "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
        },
        sections={"notes": "background"},
    )

    summary = "\n".join(f"line {i}" for i in range(6))
    exit_code = main(
        ["accept", "--run-id", "run-accept-test", "--type", "researcher-profile", "--art-id", result["id"], "--summary", summary]
    )
    accepted = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert accepted["ok"] is True
    assert accepted["version"] == 2

    exit_code = main(
        ["read", "--run-id", "run-accept-test", "--state", "frame", "--type", "researcher-profile", "--art-id", result["id"], "--resolution", "summary"]
    )
    read_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert read_out["summary"] == summary

    exit_code = main(
        ["read", "--run-id", "run-accept-test", "--state", "frame", "--type", "gap-register", "--art-id", "nonexistent", "--resolution", "summary"]
    )
    refused = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert refused["ok"] is False

    exit_code = main(["metrics", "summary-sufficiency", "--run-id", "run-accept-test"])
    metrics_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert metrics_out == {"ok": True, "full_pull_after_summary_count": 0}


def test_ask_emit_then_answer_then_revise_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-ask-test"])
    capsys.readouterr()

    questions = json.dumps(
        [{"target": "field-map.scope", "leverage_class": "L2", "form": "menu", "default": "1,2"}]
    )
    exit_code = main(["ask", "emit", "--run-id", "run-ask-test", "--questions", questions])
    emitted = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert emitted["ok"] is True
    q_id = emitted["ids"][0]

    exit_code = main(["ask", "answer", "--run-id", "run-ask-test", "--id", q_id, "--answer", "1,2,4"])
    answered = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert answered["ok"] is True

    exit_code = main(["ask", "revise", "--run-id", "run-ask-test", "--id", q_id, "--answer", "1,2"])
    revised = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert revised["version"] == 2


def test_ask_emit_over_batch_limit_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-ask-batch"])
    capsys.readouterr()

    questions = json.dumps(
        [{"target": f"field-map.scope{i}", "leverage_class": "L2", "form": "menu"} for i in range(6)]
    )
    exit_code = main(["ask", "emit", "--run-id", "run-ask-batch", "--questions", questions])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_metrics_provisional_count_reports_zero_with_no_provisional_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-metrics-test"])
    capsys.readouterr()

    exit_code = main(["metrics", "provisional-count", "--run-id", "run-metrics-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "provisional_count": 0}


def test_schema_version_refusal_exits_nonzero(tmp_path, monkeypatch, capsys):
    import yaml

    from kagami.schema_version import CURRENT_SCHEMA_REGISTRY_VERSION

    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "_kagami-output" / "runs" / "run-old"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump({"schema_registry_version": CURRENT_SCHEMA_REGISTRY_VERSION + 5})
    )

    exit_code = main(["run", "open", "--run-id", "run-old"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["ok"] is False
    assert "error" in result
