# Story 7.2 Verification — `llm_call` Reporting and Launch-Time Model Resolution

Unlike Story 7.1, this story is core code (`kagami/kernel/report.py`, `kagami/kernel/dispatch.py`, `schemas/dispatch.yaml`, CLI wiring) and is fully covered by AD-25's pytest suite — no AD-27 transcript substitute needed here.

## What was built

- `schemas/dispatch.yaml` — the static operation-class → tier table (AD-12), covering the deterministic/deterministic-ML/cheap-model/frontier-model split for every named operation this codebase currently has or the archived spec's illustrative table names.
- `kagami/kernel/dispatch.py` — `resolve_model(operation_class, config)`. A `deterministic` tier resolves with `model: null` (no model needed); every other tier requires the researcher to have configured a concrete model in `config.yaml`'s `model_tiers` map, or the call is refused — never silently defaulted. `kagami dispatch resolve --operation-class <name>` exposes this at the CLI boundary.
- `kagami/kernel/report.py` — `report_llm_call(...)`, wired to `kagami report llm-call`. Appends a validated `llm_call` event under the run lock (AD-15), same pattern as every other mutating entrypoint in `kagami/store/artifact.py`. A `call_id` (harness-minted) that already appears among the run's `llm_call` events is refused — verified end-to-end (see below) that a retried report does not double-append.
- `kagami/kernel/metrics.py`'s `compute_budget_warning` + `compute_derived_metrics`'s new `budget_warning` field — a soft-limit comparison against `config.yaml`'s `token_budget_soft_limit`, `None` when unconfigured or under limit, and — critically — never an `"ok": false` or any field that would let a caller mistake it for a block.

## Verified

- Full test suite: `353 passed` (337 + 16 new tests across `test_report.py`, `test_dispatch.py`, and three additions to `test_kernel_metrics.py`).
- Live CLI smoke test (not just pytest) against a scratch output root:
  - `kagami report llm-call` with a real UUID call-id: succeeded, event appended with all fields.
  - Retried the identical call-id: refused with the AD-26 duplicate-report error, exit code 1 — confirmed via `token_ledger` inspection that the call was **not** double-counted (2 calls total from 2 distinct call-ids, not 3).
  - `kagami dispatch resolve --operation-class staleness_propagation` (deterministic): resolved with `model: null`.
  - `kagami dispatch resolve --operation-class paper_card_extraction` with no `config.yaml`: refused (`no model configured`), not silently defaulted to some placeholder model — this is the concrete proof for AC "no call site names a concrete model."
  - `kagami metrics derived` with `token_budget_soft_limit: 100` in `config.yaml` and 1200 cumulative tokens reported: `budget_warning` populated with the correct total, `ok: true` at the top level — confirms the warning never blocks the rest of the metrics computation.

## Honest note

The reporting entrypoint is infrastructure, not yet consumed: `skills/kagami-discovery/SKILL.md` (Story 7.1) does not call `kagami report llm-call` anywhere, because Frame drafting there is main-thread conversational work, not a distinguishable sub-invocation — reporting the main thread's own inference remains the pre-existing AD-11 honest-gap ("main-thread token/prompt accounting incomplete"), not something this story claims to close. The entrypoint becomes load-bearing starting with Story 7.3's role subagent dispatch.
