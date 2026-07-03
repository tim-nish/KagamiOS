#!/usr/bin/env python3
import json
import sys

from kagami.hookguard import evaluate


def main() -> int:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    cwd = payload.get("cwd") or "."
    print(json.dumps(evaluate(tool_name, tool_input, cwd)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
