from kagami.hookguard import evaluate, is_sanctioned_kagami_invocation, references_output_root
from kagami.paths import resolve_output_root


def test_write_referencing_output_root_is_denied(tmp_path):
    decision = evaluate(
        "Write",
        {"file_path": str(tmp_path / "_kagami-output" / "runs" / "run-1" / "current.md")},
        str(tmp_path),
    )
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "AD-2" in decision["hookSpecificOutput"]["permissionDecisionReason"]


def test_bash_write_referencing_output_root_is_denied(tmp_path):
    decision = evaluate(
        "Bash",
        {"command": "echo hi >> _kagami-output/runs/run-1/events.jsonl"},
        str(tmp_path),
    )
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_command_unrelated_to_output_root_is_allowed(tmp_path):
    decision = evaluate("Bash", {"command": "ls -la"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "permissionDecisionReason" not in decision["hookSpecificOutput"]


def test_edit_unrelated_to_output_root_is_allowed(tmp_path):
    decision = evaluate("Edit", {"file_path": str(tmp_path / "README.md")}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_sanctioned_kagami_bash_invocation_referencing_output_root_is_allowed(tmp_path):
    decision = evaluate(
        "Bash",
        {
            "command": (
                "uv run --project /plugin/root kagami scan "
                "--path _kagami-output/runs/run-1"
            )
        },
        str(tmp_path),
    )
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_is_sanctioned_kagami_invocation_requires_bash_and_uv_run_prefix():
    assert is_sanctioned_kagami_invocation(
        "Bash", {"command": "uv run --project /plugin kagami run open"}
    )
    assert not is_sanctioned_kagami_invocation(
        "Bash", {"command": "python -m kagami run open"}
    )
    assert not is_sanctioned_kagami_invocation(
        "Write", {"file_path": "uv run --project /plugin kagami run open"}
    )


def test_references_output_root_checks_configured_marker(tmp_path):
    output_root = resolve_output_root(tmp_path)
    assert references_output_root(
        "Bash", {"command": f"cat {output_root}/runs/run-1/manifest.yaml"}, output_root
    )
    assert not references_output_root("Bash", {"command": "cat README.md"}, output_root)
