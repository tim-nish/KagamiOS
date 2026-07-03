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


def test_run_validate_profile_reports_ok_with_no_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-validate-test"])
    capsys.readouterr()

    exit_code = main(["run", "validate-profile", "--run-id", "run-validate-test"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result == {"ok": True, "violations": []}


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
    from kagami.store.artifact import create_artifact

    monkeypatch.chdir(tmp_path)
    main(["run", "open", "--run-id", "run-skeptic-test"])
    capsys.readouterr()

    run_dir = tmp_path / "_kagami-output" / "runs" / "run-skeptic-test"
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
            "representative_papers": [{"paper_id": "ppr-1", "human_read": False, "reaction": ""}],
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
         "--paper-id", "ppr-1", "--reaction", "foundational"]
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

    def _fake_resolve_provider(config, fetch=None):
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
