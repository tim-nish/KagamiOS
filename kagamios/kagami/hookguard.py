import re
from pathlib import Path

from kagami.paths import resolve_output_root

KAGAMI_INVOCATION_PATTERN = re.compile(r"^\s*uv run --project\s+\S+\s+kagami\b")

_PATH_KEYS = ("file_path", "path", "notebook_path")


def _tool_call_strings(tool_name: str, tool_input: dict) -> list[str]:
    if tool_name == "Bash":
        return [tool_input.get("command", "")]
    return [str(tool_input[key]) for key in _PATH_KEYS if key in tool_input]


def references_output_root(tool_name: str, tool_input: dict, output_root: Path) -> bool:
    marker = output_root.name
    return any(marker in s for s in _tool_call_strings(tool_name, tool_input))


def is_sanctioned_kagami_invocation(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "Bash":
        return False
    return bool(KAGAMI_INVOCATION_PATTERN.match(tool_input.get("command", "")))


def evaluate(tool_name: str, tool_input: dict, cwd: str) -> dict:
    output_root = resolve_output_root(Path(cwd))

    if not references_output_root(tool_name, tool_input, output_root):
        decision, reason = "allow", None
    elif is_sanctioned_kagami_invocation(tool_name, tool_input):
        decision, reason = "allow", None
    else:
        decision = "deny"
        reason = (
            f"{tool_name} references the KagamiOS output root ({output_root.name}/); "
            "only `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami <cmd>` may write "
            "there (AD-2)."
        )

    output: dict = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }
    if reason:
        output["hookSpecificOutput"]["permissionDecisionReason"] = reason
    return output
