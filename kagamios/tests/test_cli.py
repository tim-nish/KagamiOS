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
