import json
from pathlib import Path

from kagami.hookguard import evaluate, is_sanctioned_kagami_invocation, references_output_root
from kagami.paths import resolve_output_root

HOOKS_JSON_PATH = Path(__file__).resolve().parents[1] / "hooks" / "hooks.json"


def test_hooks_json_pretooluse_matcher_includes_read():
    """FR-56: AD-2's default-deny claim covers 'any tool invocation whose
    arguments reference the output root' — `hooks/hooks.json`'s matcher
    must actually name `Read`, not just the guard function underneath
    knowing how to handle it (Review Focus: check the matcher pattern
    itself, not just stated intent)."""
    config = json.loads(HOOKS_JSON_PATH.read_text())
    matcher = config["hooks"]["PreToolUse"][0]["matcher"]
    matched_tools = set(matcher.split("|"))
    assert matched_tools == {"Write", "Edit", "NotebookEdit", "Bash", "Read"}


def test_read_referencing_output_root_is_denied_identically_to_write(tmp_path):
    """FR-56: a `Read` targeting the output root is denied through the same
    enforcement path as a denied `Write`/`Edit`/`Bash` — `evaluate` already
    handled `Read`'s `file_path` key generically; this pins that the denial
    it produces is the same shape/reason a `Write` denial gets."""
    write_decision = evaluate(
        "Write",
        {"file_path": str(tmp_path / "_kagami-output" / "corpus" / "ppr-x.yaml")},
        str(tmp_path),
    )
    read_decision = evaluate(
        "Read",
        {"file_path": str(tmp_path / "_kagami-output" / "corpus" / "ppr-x.yaml")},
        str(tmp_path),
    )
    assert read_decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        read_decision["hookSpecificOutput"]["permissionDecisionReason"]
        == write_decision["hookSpecificOutput"]["permissionDecisionReason"].replace("Write", "Read")
    )


def test_read_unrelated_to_output_root_is_allowed(tmp_path):
    decision = evaluate("Read", {"file_path": str(tmp_path / "README.md")}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


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


def test_bash_rm_via_output_root_glob_is_denied(tmp_path):
    """Real bypass found live during the first dogfooding run: Scout got a
    literal `_kagami-output` reference denied, then reformulated the same
    delete as `rm -rf ./_kag*-output` — a pure substring check never catches
    a glob, since the literal marker string never appears in the command
    text, even though it expands to exactly the protected directory."""
    output_root = resolve_output_root(tmp_path)
    output_root.mkdir()
    decision = evaluate("Bash", {"command": "rm -rf ./_kag*-output"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "AD-2" in decision["hookSpecificOutput"]["permissionDecisionReason"]


def test_bash_cd_to_a_parent_of_the_output_root_is_not_a_false_positive(tmp_path):
    """Regression: an early version of the glob-aware check resolved every
    token relative to the output root's parent and then flagged the match
    if the output root appeared anywhere in *either* direction of the
    ancestor chain — which made `cd <the project root itself>` a false
    positive, since the output root is trivially a descendant of it. Only
    the output root itself (or something inside it) should ever deny."""
    output_root = resolve_output_root(tmp_path)
    output_root.mkdir()
    decision = evaluate("Bash", {"command": f"cd {tmp_path} && pwd"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_bash_absolute_glob_reaching_the_output_root_is_denied(tmp_path):
    output_root = resolve_output_root(tmp_path)
    output_root.mkdir()
    decision = evaluate("Bash", {"command": f"rm -rf {tmp_path}/_kag*-output"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_glob_reconnaissance_of_output_root_is_denied(tmp_path):
    output_root = resolve_output_root(tmp_path)
    output_root.mkdir()
    decision = evaluate("Bash", {"command": "find ./_kag*/ -type f"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_glob_matching_output_root_parent_is_denied(tmp_path):
    """A broad glob that happens to also match the output root (not just an
    exact-name glob of it) must still be caught."""
    output_root = resolve_output_root(tmp_path)
    output_root.mkdir()
    decision = evaluate("Bash", {"command": "ls -la *output*"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_glob_matching_something_else_entirely_is_still_allowed(tmp_path):
    (tmp_path / "unrelated-output-notes.md").touch()
    decision = evaluate("Bash", {"command": "cat *notes*"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_bash_glob_matching_nothing_on_disk_is_allowed_not_a_crash(tmp_path):
    decision = evaluate("Bash", {"command": "ls -la *nonexistent-anything*"}, str(tmp_path))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_sanctioned_kagami_invocation_still_allowed_even_when_it_would_glob_match(tmp_path):
    output_root = resolve_output_root(tmp_path)
    output_root.mkdir()
    decision = evaluate(
        "Bash",
        {"command": "uv run --project /plugin/root kagami scan --path ./_kag*-output/runs/run-1"},
        str(tmp_path),
    )
    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_references_output_root_checks_configured_marker(tmp_path):
    output_root = resolve_output_root(tmp_path)
    assert references_output_root(
        "Bash", {"command": f"cat {output_root}/runs/run-1/manifest.yaml"}, output_root
    )
    assert not references_output_root("Bash", {"command": "cat README.md"}, output_root)
