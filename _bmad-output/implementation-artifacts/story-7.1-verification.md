# Story 7.1 Verification — Walking Skeleton

Per AD-27 (testing convention for prompt artifacts), `skills/kagami-discovery/SKILL.md` cannot be exercised by AD-25's pytest suite — that suite covers `kagami/` and `hooks/` only. This document is the recorded-verification artifact AD-27 requires in place of a test run, plus an honest statement of what it does *not* cover.

## What was verified (2026-07-03, this session)

### 1. The exact CLI sequence SKILL.md instructs — run for real, not paraphrased

Against a scratch `KAGAMI_OUTPUT_ROOT`:

```
$ uv run kagami run open
{"ok": true, "run_id": "run-27f5d74cc0e0", ...}

$ uv run kagami entry start --run-id run-27f5d74cc0e0 --entry-mode paper-first \
    --raw-capture "a paper on signature methods sparked this"
{"ok": true, "intuition_note_id": "art-b9ba4f14cd35", "entry_mode": "paper-first"}

$ uv run kagami frame complete --run-id run-27f5d74cc0e0 \
    --unprimed-answer "I suspect signatures are just feature maps in disguise" \
    --scope-answer "readings 1 and 2 are in scope" \
    --fields '{...}' --sections '{...}' --summary "..."
{"ok": true, "inquiry_frame_id": "art-ea56a90f32ff",
 "unprimed_question_id": "q-f0244a6625a4", "scope_question_id": "q-9fbf852efa3a"}
```

All three calls succeeded on the first attempt with the flags and JSON shapes SKILL.md documents — the instructions are technically accurate, not aspirational.

### 2. The PreToolUse guard's decision logic, against four payload shapes

Invoked `hooks/guard.py` directly with simulated PreToolUse JSON (this is exactly AD-25's existing test strategy for hooks — "tested against recorded PreToolUse payloads" — applied here to confirm the guard behaves as SKILL.md claims):

| Call | Decision |
|---|---|
| Direct `Write` to a path under the output root | **deny**, reason cites AD-2 |
| `Bash` running the sanctioned `uv run --project ... kagami run open` form | **allow** |
| `Bash` running an unrelated command (`ls -la`) | **allow** |
| `Bash` running `sed -i` against a file under the output root (a blocklist-evasion attempt) | **deny**, reason cites AD-2 |

This confirms the default-deny-with-single-allow-pattern design (AD-2) holds for the specific evasion vector (`sed -i`) the Architecture Spine calls out by name, and that it doesn't false-positive on ordinary unrelated commands.

### 3. The hook's failure mode (a bad `CLAUDE_PLUGIN_ROOT`)

```
$ CLAUDE_PLUGIN_ROOT=/nonexistent/plugin/root
$ echo '<PreToolUse payload>' | uv run --project "$CLAUDE_PLUGIN_ROOT" python "$CLAUDE_PLUGIN_ROOT/hooks/guard.py"
warning: Project directory `/nonexistent/plugin/root` does not exist...
/usr/local/bin/python: can't open file '/nonexistent/plugin/root/hooks/guard.py': [Errno 2] No such file or directory
exit code: 2
```

A bad plugin root produces **no JSON output and a non-zero exit (2)** — it does not silently print an `allow` decision. Per Claude Code's documented PreToolUse hook contract, a non-zero exit is treated as a blocking error, which is the fail-*closed* direction. This part of the claim (how the harness treats a failed hook command) is about Claude Code's own behavior, not KagamiOS's — recorded here as the best evidence available from this environment, not as an independently-verified harness test.

## What was NOT verified — the honest gap

This session's Claude Code instance does **not** have the `kagamios` plugin installed via Claude Code's own plugin mechanism (checked: no `.claude-plugin` registration and empty `settings.json`/`settings.local.json` in this project). That means the PreToolUse hook is not actually wired into *this* session's tool-call path, and section 2 above is a direct-invocation test of the guard script, not a live end-to-end proof that Claude Code itself routes a real `Write`/`Edit`/`Bash` call through it and honors the `deny`.

**This is Story 7.1's residual honest gap (AD-11), not a passed acceptance criterion:** before relying on this plugin for a real investigation, install it in an actual Claude Code session (plugin marketplace or manual settings registration) and confirm, in that live session, that an attempted direct write to the output root is actually blocked by Claude Code — not just that `guard.py` would have said `deny` if asked. Story 7.5's golden toy run is the right place to close this gap for real, since it already requires a real harness-driven session.

## Test suite regression check

Full existing suite re-run after adding `skills/kagami-discovery/SKILL.md` (a new file only, no `kagami/` changes in this story):

```
337 passed
```

No regression — expected, since this story added no code, only the orchestration file and this verification.
