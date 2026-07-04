#!/usr/bin/env python3
import json
import sys


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    # AD-2/AD-3: this hook is the default-deny chokepoint. Claude Code treats
    # a non-JSON/non-zero-exit hook failure as a *non-blocking* error and lets
    # the tool call proceed — so any failure here (bad stdin, a missing
    # `kagami` import, a bug in `evaluate`) must still emit a well-formed
    # deny decision, never let a crash fall through to fail-open.
    try:
        payload = json.load(sys.stdin)
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {}) or {}
        cwd = payload.get("cwd") or "."
        from kagami.hookguard import evaluate

        result = evaluate(tool_name, tool_input, cwd)
    except Exception as exc:
        result = _deny(
            f"kagamios guard hook failed to execute ({exc.__class__.__name__}: {exc}); "
            "denying by default rather than failing open (AD-2)."
        )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
