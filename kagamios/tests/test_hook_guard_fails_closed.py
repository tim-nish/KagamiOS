import json
import subprocess
import sys
from pathlib import Path

GUARD_SCRIPT = Path(__file__).resolve().parents[1] / "hooks" / "guard.py"


def _run_guard(stdin_text: str, *, break_kagami_import: bool = False) -> subprocess.CompletedProcess:
    # `-S` skips site initialization, which is what makes this venv's editable
    # `kagami` install importable — the cleanest way to reproduce "the guard's
    # own environment is broken" without depending on what else happens to be
    # on the host's system Python.
    args = [sys.executable, *(["-S"] if break_kagami_import else []), str(GUARD_SCRIPT)]
    return subprocess.run(args, input=stdin_text, capture_output=True, text=True)


def _decision(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout)["hookSpecificOutput"]


def test_guard_allows_a_benign_call_when_it_can_actually_execute():
    """Regression/control case: with `kagami` importable, an unrelated Bash
    call is still allowed — the fail-closed change below must not turn this
    into a deny-everything hook."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": "."})
    result = _run_guard(payload)
    assert result.returncode == 0
    assert _decision(result)["permissionDecision"] == "allow"


def test_guard_fails_closed_when_kagami_cannot_be_imported():
    """Story 7.5 live smoke test finding: if the guard's own environment is
    broken (e.g. `uv run --project` resolves the wrong project, or the
    `kagami` package isn't installed), Claude Code treats a crashing hook's
    exit code as a *non-blocking* error and lets the tool call proceed. The
    default-deny chokepoint (AD-2/AD-3) must not fail open in that case."""
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x"}, "cwd": "."})
    result = _run_guard(payload, break_kagami_import=True)
    assert result.returncode == 0
    decision = _decision(result)
    assert decision["permissionDecision"] == "deny"
    assert "ModuleNotFoundError" in decision["permissionDecisionReason"]


def test_guard_fails_closed_on_malformed_stdin():
    result = _run_guard("not valid json")
    assert result.returncode == 0
    decision = _decision(result)
    assert decision["permissionDecision"] == "deny"
    assert "JSONDecodeError" in decision["permissionDecisionReason"]


def test_guard_fails_closed_on_empty_stdin():
    result = _run_guard("")
    assert result.returncode == 0
    assert _decision(result)["permissionDecision"] == "deny"
