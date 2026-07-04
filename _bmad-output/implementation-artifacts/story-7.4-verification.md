# Story 7.4 Verification — Safety Discipline: Refusal Ceiling and Provider Backoff

Core code, fully covered by AD-25's pytest suite.

## Refusal-retry ceiling (FR-48, AD-26a)

Implemented as CLI-boundary middleware in `kagami/cli.py::main()` rather than threading event-logging into every individual kernel refusal path — a deliberate architectural choice: manually extending FR-31's rejected-write-event pattern to every raise site across `kagami/kernel/` would touch dozens of functions for the same net effect the chokepoint (the CLI boundary itself, per AD-2) can already guarantee generically.

- `kagami/kernel/refusal.py` — `consecutive_refusal_count` (pure function over the tail of `events.jsonl`, per AD-20's derived-state philosophy) and `record_refusal_and_check_ceiling` (logs the refusal, returns whether this attempt crosses the ceiling).
- `kagami/cli.py::main()` — after any command returns `{"ok": false, ...}` for a run-scoped call, computes an `(entrypoint, target)` key from the full subcommand path and argument set, and applies the ceiling. At the ceiling, the response is replaced with `{"ok": false, "status": "requires_researcher", ...}` — a synchronous CLI reply, never a Question Ledger entry (verified: `test_requires_researcher_never_enters_the_question_ledger` confirms no ledger file is ever created by the escalation path).

**Design choice flagged for review:** "identical" is operationalized as strict adjacency in the event log — the streak resets the moment *any* other event intervenes, not just a success for the same tuple. This is simpler to implement correctly than tracking a synthetic "success" marker for every call, and is defensible (a true retry-storm calls the same failing thing back-to-back with nothing else happening), but it's a real trade-off: an AI that fails on X, does something else, then fails on X again resets to zero rather than accumulating. Documented in the module docstring and covered by `test_a_different_targets_refusal_does_not_inflate_the_first_targets_count`.

**Incidental fix discovered while testing this:** `_cmd_frame_complete` (and likely other `_cmd_*` functions parsing a `--X-json` argument) called `json.loads` *before* their own try/except block, so malformed JSON crashed the whole process with an unhandled traceback instead of a clean refusal — which the new ceiling logic couldn't even see, since `main()` never got a `result` dict to inspect. Fixed generically at the `main()` boundary: any `json.JSONDecodeError` from `args.func(args)` becomes a normal `{"ok": false}` result before the ceiling check runs. This is in-scope for this story specifically because a crash is a *worse* safety failure than the silent hang/unbounded retry the story is about — an uncaught exception is at least as bad as either.

## Provider backoff (NFR7, AD-7)

- `kagami/corpus/backoff.py` — `with_backoff`, wrapping a fetch call with bounded exponential-backoff retry against HTTP 429 (standard rate-limit) and 403 (GitHub's rate-limit signal on some endpoints). Any other HTTP error is raised immediately, never retried. Exhausted retries raise `ProviderRateLimitError` (a `ProviderError` subclass) naming the provider and attempt count — never a bare exception, never a silent hang, never an unbounded loop (retries are always `max_retries + 1`, hard-bounded).
- Wired into all four adapters (`OpenAlexProvider`, `SemanticScholarProvider`, `ArxivProvider`, `GitHubProvider`) via a shared `_BackoffMixin`, replacing every direct `self._fetch(url)` call site (12 total across `search`/`paper_metadata`/`citation_graph`).
- `max_retries`, `base_delay_seconds`, and `sleep_fn` are constructor-injectable on every adapter, so tests exercise real retry counts and exponential-delay math without real wall-clock sleeps or network calls.

## Test suite

`376 passed` (20 new: 7 in `test_refusal.py`, 4 in `test_refusal_ceiling_cli.py`, 8 in `test_backoff.py`, 2 in `test_corpus_adapters.py`; the original `test_corpus_adapters.py` tests still pass unmodified, confirming the backoff wrapping is transparent to callers when there's no rate limit).

## Config surface

Both new safety mechanisms are researcher-configurable via `config.yaml`, matching the pattern `token_budget_soft_limit` (Story 7.2) already set:

- `refusal_ceiling` (int, default 3) — read in `main()`.
- `provider_max_retries` / `provider_base_delay_seconds` — read in `resolve_provider`, threaded into whichever adapter gets instantiated. Unset means the adapter's own defaults (3 retries, 1.0s base delay) apply — confirmed by `test_resolve_provider_without_backoff_config_uses_adapter_defaults`.
