import glob
import re
import shlex
from pathlib import Path

from kagami.paths import resolve_output_root

KAGAMI_INVOCATION_PATTERN = re.compile(r"^\s*uv run --project\s+\S+\s+kagami\b")

_PATH_KEYS = ("file_path", "path", "notebook_path")
_GLOB_CHARS = ("*", "?", "[")


def _tool_call_strings(tool_name: str, tool_input: dict) -> list[str]:
    if tool_name == "Bash":
        return [tool_input.get("command", "")]
    return [str(tool_input[key]) for key in _PATH_KEYS if key in tool_input]


def _resolve_token(token: str, parent: Path) -> Path | None:
    try:
        path = Path(token)
        return (path if path.is_absolute() else parent / path).resolve()
    except (OSError, ValueError):
        return None


def _bash_command_reaches_output_root(command: str, output_root: Path) -> bool:
    """Beyond the literal substring check: expand every shell-glob-looking
    token in the command (relative or absolute) and see if any expansion
    resolves to the output root itself, or to something inside it. A pure
    substring check never catches a glob like `_kag*-output` — it never
    contains the literal marker string, even though it expands to exactly
    the protected directory on the real filesystem. This is still a static,
    pre-execution check: it cannot follow indirection through shell
    variables or command substitution, since that would require actually
    executing the shell. It deliberately does *not* flag every reference to
    some ancestor of the output root (e.g. the project root) — that would
    make ordinary navigation unusable; the ancestor-deletion case is a
    separate, out-of-scope risk.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()  # unbalanced quotes etc. - fail open on parsing, not on safety

    resolved_root = output_root.resolve()
    parent = output_root.parent
    for token in tokens:
        if not token:
            continue
        if any(ch in token for ch in _GLOB_CHARS):
            # glob.glob resolves an absolute pattern on its own and ignores
            # root_dir in that case; a relative pattern is matched against
            # root_dir and returned relative to it, which _resolve_token's
            # `parent / path` branch then anchors correctly.
            is_absolute = Path(token).is_absolute()
            matches = glob.glob(token) if is_absolute else glob.glob(token, root_dir=str(parent))
        else:
            matches = [token]
        for match in matches:
            resolved = _resolve_token(match, parent)
            if resolved is None:
                continue
            if resolved == resolved_root or resolved_root in resolved.parents:
                return True
    return False


def references_output_root(tool_name: str, tool_input: dict, output_root: Path) -> bool:
    marker = output_root.name
    if any(marker in s for s in _tool_call_strings(tool_name, tool_input)):
        return True
    if tool_name == "Bash":
        return _bash_command_reaches_output_root(tool_input.get("command", ""), output_root)
    return False


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
