import json

import pytest

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


def test_run_validate_profile_reports_ok_with_no_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-validate-test"])
    capsys.readouterr()

    exit_code = main(["run", "validate-profile", "--run-id", "run-validate-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "violations": []}


def test_run_fork_cli_seeds_a_new_run_at_the_named_boundary(tmp_path, monkeypatch, capsys):
    from kagami.kernel.state_machine import enter_state
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-fork-parent"])
    capsys.readouterr()

    parent_dir = tmp_path / "_kagami-output" / "runs" / "run-fork-parent"
    enter_state(parent_dir, "frame")
    create_artifact(
        parent_dir, "researcher-profile",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"notes": "background"},
    )

    exit_code = main(
        ["run", "fork", "--run-id", "run-fork-parent", "--from-state", "frame", "--new-run-id", "run-fork-child"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["run_id"] == "run-fork-child"
    assert result["parent_run_id"] == "run-fork-parent"

    child_dir = tmp_path / "_kagami-output" / "runs" / "run-fork-child"
    assert (child_dir / "artifacts" / "researcher-profile").is_dir()


def test_run_fork_cli_refuses_a_boundary_never_reached(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-fork-refuse"])
    capsys.readouterr()

    exit_code = main(
        ["run", "fork", "--run-id", "run-fork-refuse", "--from-state", "synthesize"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_run_fork_cli_from_state_argument_is_case_normalized(tmp_path, monkeypatch, capsys):
    from kagami.kernel.state_machine import enter_state

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-fork-case-test"])
    capsys.readouterr()

    parent_dir = tmp_path / "_kagami-output" / "runs" / "run-fork-case-test"
    enter_state(parent_dir, "frame")

    exit_code = main(
        ["run", "fork", "--run-id", "run-fork-case-test", "--from-state", " Frame ", "--new-run-id", "run-fork-case-child"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True


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

    exit_code = main(
        ["review", "--run-id", "run-accept-test", "--type", "researcher-profile", "--art-id", result["id"]]
    )
    reviewed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert reviewed["ok"] is True
    assert reviewed["version"] == 2

    summary = "\n".join(f"line {i}" for i in range(6))
    exit_code = main(
        ["accept", "--run-id", "run-accept-test", "--type", "researcher-profile", "--art-id", result["id"], "--summary", summary]
    )
    accepted = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert accepted["ok"] is True
    assert accepted["version"] == 3

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


def test_read_state_argument_is_case_normalized_through_cli(tmp_path, monkeypatch, capsys):
    """docs/dogfooding-review.md finding 10: 'Frame' must be accepted the
    same as 'frame' — the same input form is never accepted in one
    entrypoint and refused in another."""
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-state-case-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-state-case-test"
    result = create_artifact(
        run_dir,
        "researcher-profile",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"notes": "background"},
    )

    exit_code = main(
        ["read", "--run-id", "run-state-case-test", "--state", "  Frame  ", "--type", "researcher-profile",
         "--art-id", result["id"], "--resolution", "summary"]
    )
    read_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert read_out["ok"] is True


def test_state_enter_argument_is_case_normalized_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-state-enter-case-test"])
    capsys.readouterr()

    exit_code = main(["state", "enter", "--run-id", "run-state-enter-case-test", "--state", "Frame"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True


def test_entry_start_state_enter_frame_complete_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-cli-frame"])
    capsys.readouterr()

    exit_code = main(
        [
            "entry", "start",
            "--run-id", "run-cli-frame",
            "--entry-mode", "intuition-first",
            "--raw-capture", "signatures might be useful building blocks",
        ]
    )
    entry_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert entry_out["ok"] is True

    fields = json.dumps(
        {
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "", "in_scope_readings": ["ppr-1"], "exclusions": [], "hard_constraints": [],
        }
    )
    sections = json.dumps({"intuition_restated": "x", "unprimed_hunch": "y"})
    exit_code = main(
        [
            "frame", "complete",
            "--run-id", "run-cli-frame",
            "--unprimed-answer", "my hunch",
            "--scope-answer", "1 in scope",
            "--fields", fields,
            "--sections", sections,
            "--summary", "\n".join(f"line {i}" for i in range(6)),
        ]
    )
    frame_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert frame_out["ok"] is True

    exit_code = main(["state", "enter", "--run-id", "run-cli-frame", "--state", "map"])
    state_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert state_out["violation"] is None


def test_state_enter_skip_without_waiver_is_flagged(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-cli-skip"])
    capsys.readouterr()

    exit_code = main(["state", "enter", "--run-id", "run-cli-skip", "--state", "map"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["violation"] is not None


def test_state_enter_backward_transition_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-cli-backward"])
    capsys.readouterr()

    main(["state", "enter", "--run-id", "run-cli-backward", "--state", "frame"])
    capsys.readouterr()
    main(["state", "enter", "--run-id", "run-cli-backward", "--state", "map"])
    capsys.readouterr()
    main(
        ["budgets", "set", "--run-id", "run-cli-backward", "--clusters", json.dumps(["cluster-1"]),
         "--papers-per-cluster", "5", "--time-horizon", "1 week"]
    )
    capsys.readouterr()
    main(["state", "enter", "--run-id", "run-cli-backward", "--state", "deepen"])
    capsys.readouterr()

    # deepen -> frame is a registered backward transition (FR-1): refused without a cause...
    exit_code = main(["state", "enter", "--run-id", "run-cli-backward", "--state", "frame"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    # ...accepted and logged once a cause is supplied.
    exit_code = main(
        ["state", "enter", "--run-id", "run-cli-backward", "--state", "frame",
         "--cause", "reading reframed the intuition"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["violation"] is None

    # deepen -> map is backward but not a defined transition: refused outright, cause or not.
    main(["state", "enter", "--run-id", "run-cli-backward", "--state", "map"])
    capsys.readouterr()
    main(["state", "enter", "--run-id", "run-cli-backward", "--state", "deepen"])
    capsys.readouterr()

    exit_code = main(
        ["state", "enter", "--run-id", "run-cli-backward", "--state", "map", "--cause", "trying anyway"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_deepen_claim_and_repair_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact, mark_dependents_stale, pin_dependency

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-deepen-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-deepen-test"
    dep = create_artifact(
        run_dir,
        "field-map",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"cluster_name": "x"},
    )
    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        {
            "depends_on": [pin_dependency(dep["id"], 1)], "elicited_from": [],
            "decided_by": "ai-drafted/human-reviewed", "summary": "",
        },
        sections={"evolution": "x", "frontier": "y"},
    )
    import yaml

    section_ids = [
        sm["id"] for sm in yaml.safe_load(
            (run_dir / "artifacts" / "cluster-dossier" / dossier["id"] / "meta.yaml").read_text()
        )["sections"]
    ]

    exit_code = main(
        ["deepen", "claim", "--run-id", "run-deepen-test", "--art-id", dossier["id"],
         "--sections", json.dumps(section_ids), "--holder", "worker-1"]
    )
    claim_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert claim_out["ok"] is True

    exit_code = main(
        ["repair", "check", "--run-id", "run-deepen-test", "--type", "cluster-dossier", "--art-id", dossier["id"]]
    )
    check_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert check_out["tier"] == 0
    assert check_out["resolved"] is True

    mark_dependents_stale(run_dir, dep["id"], dependency_new_version=2)
    exit_code = main(
        ["repair", "check", "--run-id", "run-deepen-test", "--type", "cluster-dossier", "--art-id", dossier["id"]]
    )
    check_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert check_out["tier"] == 1
    assert check_out["needs_llm"]["operation_class"] == "tier1_plausibility_check"

    exit_code = main(
        ["repair", "apply", "--run-id", "run-deepen-test", "--type", "cluster-dossier", "--art-id", dossier["id"],
         "--fixes", json.dumps({"frontier": "repaired content"})]
    )
    apply_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert apply_out["applied"] == ["frontier"]


def test_skeptic_context_write_and_critique_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import accept_artifact, create_artifact, review_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-skeptic-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-skeptic-test"
    base_fields = {
        "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": "",
    }
    gap = create_artifact(run_dir, "gap-register", base_fields, sections={"statement": "x"})
    review_artifact(run_dir, "gap-register", gap["id"])
    accept_artifact(run_dir, "gap-register", gap["id"], "\n".join(f"line {i}" for i in range(6)))

    candidate = create_artifact(
        run_dir,
        "candidate-direction",
        {
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
        },
        sections={"direction": "x", "red_team_notes": ""},
    )

    exit_code = main(
        ["skeptic", "context", "--run-id", "run-skeptic-test", "--type", "candidate-direction",
         "--art-id", candidate["id"]]
    )
    context_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert context_out["target"]["id"] == candidate["id"]

    exit_code = main(
        ["skeptic", "write", "--run-id", "run-skeptic-test", "--type", "candidate-direction",
         "--art-id", candidate["id"], "--section", "red_team_notes", "--body", "weak evidence"]
    )
    write_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert write_out["ok"] is True

    exit_code = main(
        ["skeptic", "write", "--run-id", "run-skeptic-test", "--type", "candidate-direction",
         "--art-id", candidate["id"], "--section", "direction", "--body", "a new direction"]
    )
    refused_out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert refused_out["ok"] is False

    exit_code = main(
        ["skeptic", "critique", "--run-id", "run-skeptic-test", "--type", "candidate-direction",
         "--art-id", candidate["id"], "--objection", "the claim overreaches", "--evidence", json.dumps(["ppr-1"])]
    )
    critique_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert critique_out["ok"] is True


def test_historian_write_refuses_a_non_evolution_section_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-historian-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-historian-test"
    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        {
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
        },
        sections={"evolution": "x", "frontier": "y"},
    )

    exit_code = main(
        ["historian", "write", "--run-id", "run-historian-test", "--art-id", dossier["id"],
         "--section", "frontier", "--body", "off-limits content"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    exit_code = main(
        ["historian", "write", "--run-id", "run-historian-test", "--art-id", dossier["id"],
         "--section", "evolution", "--body", "the field began with X"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True


def test_historian_write_section_argument_is_case_normalized_through_cli(tmp_path, monkeypatch, capsys):
    """docs/dogfooding-review.md finding 10: 'Evolution' must be accepted
    the same as 'evolution'."""
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-historian-case-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-historian-case-test"
    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"evolution": "x", "frontier": "y"},
    )

    exit_code = main(
        ["historian", "write", "--run-id", "run-historian-case-test", "--art-id", dossier["id"],
         "--section", " Evolution ", "--body", "the field began with X"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True


def test_dossier_mark_read_and_validate_deepen_exit_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import accept_artifact, create_artifact, review_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-dossier-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-dossier-test"
    dossier = create_artifact(
        run_dir,
        "cluster-dossier",
        {
            "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed",
            "summary": "",
            "representative_papers": [
                {"paper_id": "ppr-1", "rating": None, "confidence": None, "note": "", "actor": None}
            ],
        },
        sections={"evolution": "founding problem"},
    )
    review_artifact(run_dir, "cluster-dossier", dossier["id"])
    accept_artifact(run_dir, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))

    exit_code = main(
        ["dossier", "validate-deepen-exit", "--run-id", "run-dossier-test", "--art-id", dossier["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    exit_code = main(
        ["dossier", "mark-read", "--run-id", "run-dossier-test", "--art-id", dossier["id"],
         "--paper-id", "ppr-1", "--rating", "strong", "--confidence", "high",
         "--note", "foundational", "--actor", "historian"]
    )
    refused_result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert refused_result["ok"] is False

    exit_code = main(
        ["dossier", "mark-read", "--run-id", "run-dossier-test", "--art-id", dossier["id"],
         "--paper-id", "ppr-1", "--rating", "strong", "--confidence", "high",
         "--note", "foundational", "--actor", "human"]
    )
    mark_result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert mark_result["ok"] is True

    exit_code = main(
        ["dossier", "validate-deepen-exit", "--run-id", "run-dossier-test", "--art-id", dossier["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True


def test_dissolution_full_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-dissolution-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-dissolution-test"
    dep = create_artifact(
        run_dir,
        "field-map",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"cluster_name": "x"},
    )
    evidence = json.dumps([f"{dep['id']}@v1"])

    exit_code = main(
        ["dissolution", "draft", "--run-id", "run-dissolution-test",
         "--intuition-summary", "combining X and Y for Z",
         "--dissolving-evidence", evidence]
    )
    draft_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert draft_out["ok"] is True
    memo_id = draft_out["id"]

    exit_code = main(["dissolution", "check-terminal", "--run-id", "run-dissolution-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "terminal_reached": False}

    exit_code = main(
        ["dissolution", "spin-off-fragment", "--run-id", "run-dissolution-test", "--art-id", memo_id,
         "--raw-capture", "the sub-idea about Y might still work"]
    )
    spin_off_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert spin_off_out["ok"] is True

    exit_code = main(
        ["dissolution", "record-learned", "--run-id", "run-dissolution-test", "--art-id", memo_id,
         "--content", "the mechanism doesn't generalize"]
    )
    assert exit_code == 0
    capsys.readouterr()

    exit_code = main(
        ["dissolution", "record-revival-conditions", "--run-id", "run-dissolution-test", "--art-id", memo_id,
         "--content", "revisit if a new dataset appears"]
    )
    assert exit_code == 0
    capsys.readouterr()

    main(["review", "--run-id", "run-dissolution-test", "--type", "dissolution-memo", "--art-id", memo_id])
    capsys.readouterr()
    main(
        ["accept", "--run-id", "run-dissolution-test", "--type", "dissolution-memo", "--art-id", memo_id,
         "--summary", "\n".join(f"line {i}" for i in range(6))]
    )
    capsys.readouterr()

    exit_code = main(
        ["dissolution", "validate-exit", "--run-id", "run-dissolution-test", "--art-id", memo_id]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "violations": []}

    exit_code = main(["dissolution", "check-terminal", "--run-id", "run-dissolution-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "terminal_reached": True}

    exit_code = main(["state", "enter", "--run-id", "run-dissolution-test", "--state", "dissolved"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["violation"] is None


def test_budgets_set_get_and_check_exhaustion_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-budgets-test"])
    capsys.readouterr()

    exit_code = main(
        [
            "budgets", "set",
            "--run-id", "run-budgets-test",
            "--clusters", json.dumps(["cluster-1"]),
            "--papers-per-cluster", "5",
            "--time-horizon", "1 week",
        ]
    )
    set_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert set_out["depth_budgets"]["papers_per_cluster"] == 5

    exit_code = main(["budgets", "get", "--run-id", "run-budgets-test"])
    get_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert get_out["depth_budgets"]["papers_per_cluster"] == 5

    exit_code = main(
        [
            "budgets", "check-exhaustion",
            "--run-id", "run-budgets-test",
            "--cluster-id", "cluster-1",
            "--papers-read-count", "5",
        ]
    )
    check_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert check_out["exhausted"] is True
    assert check_out["newly_asked"] is True


def test_state_derive_reports_modal_cluster_state_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-derive-test"])
    capsys.readouterr()
    main(["state", "enter", "--run-id", "run-derive-test", "--state", "frame"])
    capsys.readouterr()

    exit_code = main(["state", "derive", "--run-id", "run-derive-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["nominal_state"] == "frame"


def test_monitor_mark_dormant_and_sweep_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact, mark_dependents_stale, pin_dependency

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-monitor-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-monitor-test"
    main(
        ["budgets", "set", "--run-id", "run-monitor-test", "--clusters", json.dumps(["cluster-1"]),
         "--papers-per-cluster", "5", "--time-horizon", "1 week"]
    )
    capsys.readouterr()

    base_fields = {
        "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": "",
    }
    dep = create_artifact(run_dir, "field-map", base_fields, sections={"cluster_name": "x"})
    dossier = create_artifact(
        run_dir, "cluster-dossier", {**base_fields, "depends_on": [pin_dependency(dep["id"], 1)]},
        sections={"evolution": "x", "frontier": "y"},
    )

    exit_code = main(
        ["monitor", "mark-dormant", "--run-id", "run-monitor-test",
         "--revival-conditions", "revisit if a related paper appears"]
    )
    dormant_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert dormant_out["ok"] is True

    exit_code = main(["monitor", "sweep", "--run-id", "run-monitor-test"])
    swept_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert swept_out == {"ok": True, "swept": True, "reopened": False, "stale_artifact_ids": []}

    mark_dependents_stale(run_dir, dep["id"], dependency_new_version=2)

    exit_code = main(["monitor", "sweep", "--run-id", "run-monitor-test"])
    reopened_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert reopened_out["reopened"] is True
    assert reopened_out["affected_state"] == "deepen"
    assert reopened_out["stale_artifact_ids"] == [dossier["id"]]

    # confirm the run is genuinely back at 'deepen': its nominal-next transition is now legal
    exit_code = main(["state", "enter", "--run-id", "run-monitor-test", "--state", "synthesize"])
    enter_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert enter_out["violation"] is None


def test_cartographer_draft_then_create_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-cartographer-test"])
    capsys.readouterr()

    papers = json.dumps(
        [
            {"id": "ppr-1", "method_class": "empirical", "source": "openalex"},
            {"id": "ppr-2", "method_class": "empirical", "source": "arxiv"},
            {"id": "ppr-3", "method_class": "theoretical", "source": "arxiv"},
        ]
    )
    exit_code = main(["cartographer", "draft", "--papers", papers])
    draft_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert draft_out["ok"] is True
    assert len(draft_out["cuts"]) >= 2

    exit_code = main(
        [
            "cartographer", "create",
            "--run-id", "run-cartographer-test",
            "--papers", papers,
            "--cuts", json.dumps(draft_out["cuts"]),
            "--chosen-basis", draft_out["cuts"][0]["basis"],
        ]
    )
    create_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert create_out["ok"] is True
    assert len(create_out["field_map_ids"]) >= 1


def test_cartographer_draft_rejects_a_single_indistinguishable_clustering(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    papers = json.dumps([{"id": "ppr-1", "method_class": "x", "source": "x"}])
    exit_code = main(["cartographer", "draft", "--papers", papers])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_corpus_search_cli_resolves_provider_from_config_not_a_hardcoded_call_site(
    tmp_path, monkeypatch, capsys
):
    import kagami.cli as cli_module
    from kagami.corpus.provider import LiteratureProvider

    class _StubProvider(LiteratureProvider):
        name = "stub"

        def search(self, query, limit=20):
            return [{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}]

        def paper_metadata(self, canonical_key):
            raise NotImplementedError

        def citation_graph(self, canonical_key):
            raise NotImplementedError

    captured_config = {}

    def _fake_resolve_provider(config, fetch=None, provider_override=None):
        captured_config.update(config)
        return _StubProvider()

    monkeypatch.setattr(cli_module, "resolve_provider", _fake_resolve_provider)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("literature_provider: stub\n")

    main(["run", "open", "--run-id", "run-corpus-test"])
    capsys.readouterr()

    exit_code = main(
        ["corpus", "search", "--run-id", "run-corpus-test", "--role", "scout", "--query", "signatures"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["papers"][0]["bibliographic_identity"] == "10.1/a"
    assert captured_config == {"literature_provider": "stub"}


def test_corpus_search_cli_provider_flag_overrides_configs_default(tmp_path, monkeypatch, capsys):
    """Story 9.3/FR-15/FR-25: `--provider` routes around a single broken or
    rate-limited provider without losing the whole search — resilience run
    1 had no route around."""
    import kagami.cli as cli_module

    captured_override = {}

    def _fake_resolve_provider(config, fetch=None, provider_override=None):
        captured_override["value"] = provider_override

        class _StubProvider:
            name = "stub"

            def search(self, query, limit=20):
                return []

        return _StubProvider()

    monkeypatch.setattr(cli_module, "resolve_provider", _fake_resolve_provider)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("literature_provider: openalex\n")

    main(["run", "open", "--run-id", "run-corpus-provider-test"])
    capsys.readouterr()

    exit_code = main(
        ["corpus", "search", "--run-id", "run-corpus-provider-test", "--role", "scout",
         "--query", "signatures", "--provider", "arxiv"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert captured_override["value"] == "arxiv"


def test_corpus_search_cli_defaults_limit_to_eight_and_forwards_an_explicit_override(
    tmp_path, monkeypatch, capsys
):
    import kagami.cli as cli_module
    from kagami.corpus.provider import LiteratureProvider
    from kagami.kernel.scout import DEFAULT_SEARCH_LIMIT

    captured_limits = []

    class _StubProvider(LiteratureProvider):
        name = "stub"

        def search(self, query, limit=20):
            captured_limits.append(limit)
            return []

        def paper_metadata(self, canonical_key):
            raise NotImplementedError

        def citation_graph(self, canonical_key):
            raise NotImplementedError

    monkeypatch.setattr(cli_module, "resolve_provider", lambda config, fetch=None, provider_override=None: _StubProvider())
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-limit-test"])
    capsys.readouterr()

    main(["corpus", "search", "--run-id", "run-corpus-limit-test", "--role", "scout", "--query", "x"])
    capsys.readouterr()
    assert captured_limits == [DEFAULT_SEARCH_LIMIT]

    main(
        ["corpus", "search", "--run-id", "run-corpus-limit-test", "--role", "scout", "--query", "x",
         "--limit", "3"]
    )
    capsys.readouterr()
    assert captured_limits == [DEFAULT_SEARCH_LIMIT, 3]


def test_corpus_search_and_expand_cli_administrative_flag_lands_on_the_retrieval_event(
    tmp_path, monkeypatch, capsys
):
    """FR-57: `--administrative` is opt-in (defaults to organic/False) and
    is self-declared by the caller at the point of issuance."""
    import kagami.cli as cli_module
    from kagami.corpus.provider import LiteratureProvider

    class _StubProvider(LiteratureProvider):
        name = "stub"

        def search(self, query, limit=20):
            return [{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}]

        def paper_metadata(self, canonical_key):
            return {"canonical_key": canonical_key, "title": "Neighbor", "source": "stub"}

        def citation_graph(self, canonical_key):
            return {"canonical_key": canonical_key, "cited_by": [], "references": []}

    monkeypatch.setattr(cli_module, "resolve_provider", lambda config, fetch=None, provider_override=None: _StubProvider())
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-admin-test"])
    capsys.readouterr()

    main(["corpus", "search", "--run-id", "run-corpus-admin-test", "--role", "scout", "--query", "x"])
    capsys.readouterr()
    main(
        ["corpus", "search", "--run-id", "run-corpus-admin-test", "--role", "scout", "--query", "y",
         "--administrative"]
    )
    capsys.readouterr()
    main(
        ["corpus", "expand", "--run-id", "run-corpus-admin-test", "--role", "scout",
         "--canonical-key", "10.1/a", "--administrative"]
    )
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-corpus-admin-test"
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    retrievals = [e for e in events if e["family"] == "retrieval"]
    assert [e["administrative"] for e in retrievals] == [False, True, True]


def test_corpus_search_cli_refuses_a_non_scout_role(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-refuse"])
    capsys.readouterr()

    exit_code = main(
        ["corpus", "search", "--run-id", "run-corpus-refuse", "--role", "cartographer", "--query", "x"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_corpus_expand_cli_mints_neighbor_cards_and_logs_edges(tmp_path, monkeypatch, capsys):
    import kagami.cli as cli_module
    from kagami.corpus.provider import LiteratureProvider

    class _StubProvider(LiteratureProvider):
        name = "stub"

        def search(self, query, limit=20):
            raise NotImplementedError

        def paper_metadata(self, canonical_key):
            return {"canonical_key": canonical_key, "title": "Neighbor", "source": "stub"}

        def citation_graph(self, canonical_key):
            return {"canonical_key": canonical_key, "cited_by": ["10.1/b"], "references": []}

    monkeypatch.setattr(cli_module, "resolve_provider", lambda config, fetch=None, provider_override=None: _StubProvider())
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-expand-test"])
    capsys.readouterr()

    exit_code = main(
        ["corpus", "expand", "--run-id", "run-corpus-expand-test", "--role", "scout", "--canonical-key", "10.1/a"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert len(result["edges"]) == 1
    assert result["edges"][0]["direction"] == "cited_by"


def test_corpus_expand_cli_provider_flag_overrides_configs_default(tmp_path, monkeypatch, capsys):
    import kagami.cli as cli_module
    from kagami.corpus.provider import LiteratureProvider

    captured_override = {}

    class _StubProvider(LiteratureProvider):
        name = "stub"

        def search(self, query, limit=20):
            raise NotImplementedError

        def paper_metadata(self, canonical_key):
            return {"canonical_key": canonical_key, "title": "Neighbor", "source": "stub"}

        def citation_graph(self, canonical_key):
            return {"canonical_key": canonical_key, "cited_by": [], "references": []}

    def _fake_resolve_provider(config, fetch=None, provider_override=None):
        captured_override["value"] = provider_override
        return _StubProvider()

    monkeypatch.setattr(cli_module, "resolve_provider", _fake_resolve_provider)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("literature_provider: openalex\n")
    main(["run", "open", "--run-id", "run-corpus-expand-provider-test"])
    capsys.readouterr()

    exit_code = main(
        ["corpus", "expand", "--run-id", "run-corpus-expand-provider-test", "--role", "scout",
         "--canonical-key", "10.1/a", "--provider", "arxiv"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert captured_override["value"] == "arxiv"


def test_corpus_expand_cli_refuses_a_non_scout_role(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-expand-refuse"])
    capsys.readouterr()

    exit_code = main(
        ["corpus", "expand", "--run-id", "run-corpus-expand-refuse", "--role", "historian",
         "--canonical-key", "10.1/a"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_corpus_show_cli_reads_a_paper_card_and_logs_a_retrieval_event(tmp_path, monkeypatch, capsys):
    """FR-55: Historian (or any role whose job needs it) reads paper-card
    content through the sanctioned `corpus show` entrypoint, which
    appends its own retrieval event — the same logged-read pattern
    `read_artifact`'s `summary_read`/`full_text_pull` already established."""
    from kagami.corpus.cache import get_or_create_paper_card
    from kagami.paths import resolve_output_root

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-show-test"])
    capsys.readouterr()

    output_root = resolve_output_root()
    card, _ = get_or_create_paper_card(output_root, "10.1/a", lambda: {"title": "Paper A", "source": "openalex"})

    exit_code = main(
        ["corpus", "show", "--run-id", "run-corpus-show-test", "--state", "deepen", "--paper-id", card["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["card"]["id"] == card["id"]

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-corpus-show-test"
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    retrievals = [e for e in events if e["family"] == "retrieval" and e["kind"] == "paper_card_read"]
    assert len(retrievals) == 1
    assert retrievals[0]["paper_id"] == card["id"]


def test_corpus_show_cli_state_argument_is_case_normalized(tmp_path, monkeypatch, capsys):
    from kagami.corpus.cache import get_or_create_paper_card
    from kagami.paths import resolve_output_root

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-show-case-test"])
    capsys.readouterr()

    output_root = resolve_output_root()
    card, _ = get_or_create_paper_card(output_root, "10.1/a", lambda: {"title": "Paper A"})

    exit_code = main(
        ["corpus", "show", "--run-id", "run-corpus-show-case-test", "--state", " Deepen ", "--paper-id", card["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True


def test_corpus_show_cli_is_refused_from_a_state_without_a_defined_brief(tmp_path, monkeypatch, capsys):
    from kagami.corpus.cache import get_or_create_paper_card
    from kagami.paths import resolve_output_root

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-corpus-show-refuse-test"])
    capsys.readouterr()

    output_root = resolve_output_root()
    card, _ = get_or_create_paper_card(output_root, "10.1/a", lambda: {"title": "Paper A"})

    exit_code = main(
        ["corpus", "show", "--run-id", "run-corpus-show-refuse-test", "--state", "synthesize", "--paper-id", card["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False


def test_appraisal_record_cli_writes_an_entry(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-appraisal-test"])
    capsys.readouterr()

    exit_code = main(
        ["appraisal", "record", "--run-id", "run-appraisal-test", "--paper-id", "ppr-abc",
         "--judgment", "relevant", "--frame-version", "frame-v1", "--reason", "anchors the cluster",
         "--role", "worker"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["id"].startswith("apr-")


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


def test_metrics_derived_reports_all_four_blocks_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-derived-metrics-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-derived-metrics-test"
    create_artifact(
        run_dir, "field-map",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"cluster_name": "x"},
    )

    exit_code = main(["metrics", "derived", "--run-id", "run-derived-metrics-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert "question_economics" in result
    assert "token_ledger" in result
    assert "override_profile" in result
    assert result["decision_block"]["candidate_origins"] == []
    assert result["decision_block"]["falsifiable_claims"] == []
    assert result["decision_block"]["provisional_count"] == 0
    assert result["rediscovery_rate"]["sample_size"] == 0
    assert result["rediscovery_rate"]["rediscovery_rate"] is None


def test_metrics_rediscovery_rate_cli_computes_over_real_corpus_search_events(
    tmp_path, monkeypatch, capsys
):
    import kagami.cli as cli_module
    from kagami.corpus.provider import LiteratureProvider

    class _StubProvider(LiteratureProvider):
        name = "stub"

        def __init__(self):
            self._calls = 0

        def search(self, query, limit=20):
            self._calls += 1
            # First call is a fresh paper; second call re-finds the same one.
            return [{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}]

        def paper_metadata(self, canonical_key):
            raise NotImplementedError

        def citation_graph(self, canonical_key):
            raise NotImplementedError

    monkeypatch.setattr(cli_module, "resolve_provider", lambda config, fetch=None, provider_override=None: _StubProvider())
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-rediscovery-test"])
    capsys.readouterr()

    main(["corpus", "search", "--run-id", "run-rediscovery-test", "--role", "scout", "--query", "q"])
    capsys.readouterr()
    main(["corpus", "search", "--run-id", "run-rediscovery-test", "--role", "scout", "--query", "q"])
    capsys.readouterr()

    exit_code = main(["metrics", "rediscovery-rate", "--run-id", "run-rediscovery-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["sample_size"] == 2
    assert result["rediscovery_rate"] == pytest.approx(0.5)  # first miss, second reused


def test_metrics_charter_audit_detects_a_refused_historian_write_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-charter-audit-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-charter-audit-test"
    dossier = create_artifact(
        run_dir, "cluster-dossier",
        {"depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": ""},
        sections={"evolution": "x", "frontier": "y"},
    )

    exit_code = main(["metrics", "charter-audit", "--run-id", "run-charter-audit-test"])
    clean_result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert clean_result == {
        "ok": True,
        "violation_count": 0,
        "violations": {
            "scout_produced_interpretation": [],
            "non_scout_touched_raw_corpus": [],
        },
        "refusals_held": 0,
        "refusals": {
            "skeptic_proposed_an_alternative": [],
            "historian_spoke_outside_evolution": [],
        },
    }

    exit_code = main(
        ["historian", "write", "--run-id", "run-charter-audit-test", "--art-id", dossier["id"],
         "--section", "frontier", "--body", "off-limits content"]
    )
    assert exit_code == 1
    capsys.readouterr()

    exit_code = main(["metrics", "charter-audit", "--run-id", "run-charter-audit-test"])
    refused_result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    # A guard doing its job (FR-28) is a refusal, never a violation.
    assert refused_result["violation_count"] == 0
    assert refused_result["refusals_held"] == 1
    assert len(refused_result["refusals"]["historian_spoke_outside_evolution"]) == 1


def test_metrics_shared_payload_refuses_by_default_then_succeeds_once_opted_in_through_cli(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-shared-payload-test"])
    capsys.readouterr()

    exit_code = main(["metrics", "shared-payload", "--run-id", "run-shared-payload-test"])
    refused = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert refused["ok"] is False

    (tmp_path / "config.yaml").write_text("sharing_enabled: true\n")

    exit_code = main(["metrics", "shared-payload", "--run-id", "run-shared-payload-test"])
    allowed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert allowed["ok"] is True
    assert "event_class_counts" in allowed


def test_report_llm_call_auto_mints_a_call_id_when_omitted_through_cli(tmp_path, monkeypatch, capsys):
    """AD-26/docs/dogfooding-review.md finding 10: the guard's purpose is
    idempotency, not ceremony — a harness that omits `--call-id` still
    gets a logged, well-formed event instead of the first-attempt stumble
    every role hit in run 1."""
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-report-autoid-test"])
    capsys.readouterr()

    exit_code = main(
        ["report", "llm-call", "--run-id", "run-report-autoid-test", "--role", "scout",
         "--operation-class", "paper_card_extraction", "--model-tier", "cheap-model",
         "--tokens-in", "10", "--tokens-out", "5", "--cache-hit", "false"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True
    assert result["event"]["call_id"]

    # A second omitted-call-id report is a distinct call, not a refused
    # duplicate — each auto-minted id is fresh.
    exit_code = main(
        ["report", "llm-call", "--run-id", "run-report-autoid-test", "--role", "scout",
         "--operation-class", "paper_card_extraction", "--model-tier", "cheap-model",
         "--tokens-in", "10", "--tokens-out", "5", "--cache-hit", "false"]
    )
    second = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert second["ok"] is True
    assert second["event"]["call_id"] != result["event"]["call_id"]


def test_report_llm_call_duplicate_explicit_call_id_is_still_refused_through_cli(tmp_path, monkeypatch, capsys):
    """Confirms auto-minting doesn't weaken AD-26: a harness that opts into
    the idempotency guarantee by passing its own `--call-id` is still
    protected against a retried report double-inflating the ledger."""
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-report-dup-test"])
    capsys.readouterr()

    argv = [
        "report", "llm-call", "--run-id", "run-report-dup-test", "--role", "scout",
        "--operation-class", "paper_card_extraction", "--model-tier", "cheap-model",
        "--tokens-in", "10", "--tokens-out", "5", "--cache-hit", "false", "--call-id", "call-fixed",
    ]
    exit_code = main(argv)
    first = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert first["ok"] is True

    exit_code = main(argv)
    second = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert second["ok"] is False


def test_gate_propose_and_approve_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-gate-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-gate-test"
    base_fields = {
        "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": "",
    }
    dossier = create_artifact(run_dir, "cluster-dossier", base_fields, sections={"evolution": "x"})

    exit_code = main(["gate", "propose", "--run-id", "run-gate-test", "--type", "cluster-dossier"])
    propose_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert propose_out["ok"] is True
    assert "statistic" in propose_out

    exit_code = main(["gate", "propose", "--run-id", "run-gate-test", "--type", "gap-register"])
    refused_out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert refused_out["ok"] is False

    exit_code = main(["accept", "--run-id", "run-gate-test", "--type", "cluster-dossier",
                       "--art-id", dossier["id"], "--summary", "\n".join(f"l{i}" for i in range(6))])
    still_strict_out = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert still_strict_out["ok"] is False

    exit_code = main(["gate", "approve", "--run-id", "run-gate-test", "--type", "cluster-dossier"])
    approve_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert approve_out["ok"] is True
    assert approve_out["loosened"] is True

    exit_code = main(["accept", "--run-id", "run-gate-test", "--type", "cluster-dossier",
                       "--art-id", dossier["id"], "--summary", "\n".join(f"l{i}" for i in range(6))])
    accepted_out = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert accepted_out["ok"] is True


def test_synthesize_write_and_validate_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import accept_artifact, create_artifact, review_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-synthesize-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-synthesize-test"
    base_fields = {
        "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": "",
    }
    dossier = create_artifact(
        run_dir, "cluster-dossier", base_fields, sections={"evolution": "founding problem"}
    )
    review_artifact(run_dir, "cluster-dossier", dossier["id"])
    accept_artifact(run_dir, "cluster-dossier", dossier["id"], "\n".join(f"l{i}" for i in range(6)))

    synth = create_artifact(run_dir, "landscape-synthesis", base_fields, sections={})

    rows = [
        {"claim": "approach X solves problem Y", "status": "solved"},
        {"claim": "nobody has tried Z", "status": "open"},  # missing absence_evidence
    ]
    exit_code = main(
        ["synthesize", "write", "--run-id", "run-synthesize-test", "--art-id", synth["id"],
         "--field", "solved_open_table", "--rows", json.dumps(rows),
         "--dossier-ids", json.dumps([dossier["id"]])]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    rows[1]["absence_evidence"] = "searched venues A/B 2019-2025, zero hits"
    exit_code = main(
        ["synthesize", "write", "--run-id", "run-synthesize-test", "--art-id", synth["id"],
         "--field", "solved_open_table", "--rows", json.dumps(rows),
         "--dossier-ids", json.dumps([dossier["id"]])]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True

    exit_code = main(
        ["synthesize", "write", "--run-id", "run-synthesize-test", "--art-id", synth["id"],
         "--field", "competing_approaches_matrix", "--rows", json.dumps([{"x": "y"}]),
         "--dossier-ids", json.dumps([dossier["id"]])]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    exit_code = main(
        ["synthesize", "validate", "--run-id", "run-synthesize-test", "--art-id", synth["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "violations": []}


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


def test_locate_write_mark_meaningful_and_validate_exit_round_trip_through_cli(tmp_path, monkeypatch, capsys):
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-locate-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-locate-test"
    base_fields = {
        "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": "",
    }
    gap = create_artifact(
        run_dir,
        "gap-register",
        base_fields,
        sections={
            "statement": "",
            "evidence_of_absence": "",
            "why_does_this_gap_exist": "",
            "meaningful_to_me": "",
            "micro_probe_evidence": "",
        },
    )

    exit_code = main(
        ["locate", "write", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--field", "why_does_this_gap_exist", "--content", "not-a-real-reason"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    exit_code = main(
        ["locate", "write", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--field", "why_does_this_gap_exist", "--content", "genuinely_open"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True

    main(
        ["locate", "write", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--field", "statement", "--content", "nobody has combined X with Y"]
    )
    capsys.readouterr()
    main(
        ["locate", "write", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--field", "evidence_of_absence", "--content", "searched venues A/B 2019-2025, zero hits"]
    )
    capsys.readouterr()

    exit_code = main(
        ["locate", "write", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--field", "meaningful_to_me", "--content", "meaningful"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False

    exit_code = main(
        ["locate", "mark-meaningful", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--disposition", "meaningful"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True

    exit_code = main(
        ["locate", "record-micro-probe", "--run-id", "run-locate-test", "--art-id", gap["id"],
         "--evidence", "ran a 2hr feasibility check: approach compiles"]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["ok"] is True

    main(["review", "--run-id", "run-locate-test", "--type", "gap-register", "--art-id", gap["id"]])
    capsys.readouterr()
    main(
        ["accept", "--run-id", "run-locate-test", "--type", "gap-register", "--art-id", gap["id"],
         "--summary", "\n".join(f"line {i}" for i in range(6))]
    )
    capsys.readouterr()

    exit_code = main(
        ["locate", "validate-locate-exit", "--run-id", "run-locate-test", "--art-id", gap["id"]]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "violations": []}


def test_locate_check_terminal_flips_true_only_after_gap_register_accepted_through_cli(
    tmp_path, monkeypatch, capsys
):
    from kagami.store.artifact import accept_artifact, create_artifact, review_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-terminal-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-terminal-test"
    base_fields = {
        "depends_on": [], "elicited_from": [], "decided_by": "ai-drafted/human-reviewed", "summary": "",
    }

    exit_code = main(["locate", "check-terminal", "--run-id", "run-terminal-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "terminal_reached": False}

    gap = create_artifact(run_dir, "gap-register", base_fields, sections={"statement": "a real gap"})

    premature = create_artifact(
        run_dir, "candidate-direction", base_fields, sections={"direction": "too soon"}
    )
    assert premature["ok"] is False
    assert not (run_dir / "artifacts" / "candidate-direction").exists()

    review_artifact(run_dir, "gap-register", gap["id"])
    accept_artifact(run_dir, "gap-register", gap["id"], "\n".join(f"line {i}" for i in range(6)))

    exit_code = main(["locate", "check-terminal", "--run-id", "run-terminal-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "terminal_reached": True}

    legitimate = create_artifact(
        run_dir, "candidate-direction", base_fields, sections={"direction": "a real candidate"}
    )
    assert legitimate["ok"] is True
