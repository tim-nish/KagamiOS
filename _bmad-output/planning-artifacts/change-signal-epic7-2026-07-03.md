# Change Signal: Epic 7 — Driver & Harness Shell (2026-07-03)

## Trigger
All 21 stories in Epics 1–6 are implemented and merged (337 CLI-boundary tests passing).
The deterministic core is complete, but no epic ever covered the harness-facing shell the
Architecture Spine already specifies (Structural Seed: `skills/kagami-discovery/SKILL.md`,
`agents/`, `schemas/dispatch.yaml`). The system has a gatekeeper but no driver and cannot
be dogfooded. This is an epic-coverage gap, not a requirements rewrite: FR-17..24
(elicitation), FR-25..29 (role contracts), and FR-33/34 (read sets) already specify most
driver behavior — only their harness side was never scheduled.

## Verified gaps (code inspection, 2026-07-03)
1. No `skills/kagami-discovery/SKILL.md` — the Interviewer (AD-4) does not exist.
2. No `agents/` definitions for Scout, Cartographer, Historian, Skeptic, worker (AD-4).
3. No `kagami brief` / `kagami session` entrypoints; no `kagami/briefs/` package — AD-4's
   read-set bundles and engagement tokens are unimplemented. (Partial coverage exists:
   the per-state read gate in `kagami/store/read.py`, FR-15.)
4. No `schemas/dispatch.yaml` — AD-12's operation-class→tier table has no data, so
   launch-time tier→model resolution cannot happen.
5. No producer for `llm_call` events. Metrics (FR-37, Story 6.1) and the charter audit
   (FR-29, Story 6.2) consume them, but only tests inject them. In a real run the token
   ledger reads zero and the charter audit has nothing to audit.
6. `kagami/corpus/adapters.py` has no backoff/retry/rate-limit handling, despite the
   Spine Stack section requiring arXiv backoff and OpenAlex key handling from day one.
7. No driver-side operational discipline anywhere: no refusal-retry ceiling, no refusal
   surfacing to the researcher, no gate-time token-budget check.

## Decisions already made (record these; do not relitigate)
- Extend the existing PRD with §4.8 "Driver & Harness Shell". Do NOT create a separate
  driver PRD — the FRs already exist here and a second PRD would split ownership.
- New FRs (all mechanically testable at the CLI boundary where noted):
  a. Refusal-retry discipline: the chokepoint counts consecutive identical refusals per
     (entrypoint, target) and escalates to a `requires_researcher` response after N.
     Core-enforced backstop, not SKILL.md prose (AD-1).
  b. `llm_call` reporting: a validated `kagami` entrypoint the harness calls after every
     model invocation (AD-22's pattern in reverse). Subagent self-reporting is
     detect-and-audit — new AD-11 honest-gap entry.
  c. Token-budget checkpoint: extend FR-37's gate-time decision block with a warn-only
     threshold against a `config.yaml` soft limit. This does NOT reverse NFR5 or
     addendum A4/O6 — live budgets stay deferred; this is deterministic gate-time
     reporting that produces the cost evidence O6's adoption trigger waits for.
  d. Provider backoff: implement inside the AD-7 port per the recorded Stack
     commitments; at most a new testable consequence under FR-25.
- Architecture spine: amend, never renumber. Expected deltas:
  - AD-4: engagement tokens + `kagami session` deferred for v1-driver; "role attribution
    is trusted" recorded in AD-11's honest-gap register.
  - New AD: driver operational discipline (retry ceiling, reporting obligation, budget
    checkpoint).
  - New AD: testing convention for prompt artifacts — SKILL.md/agent definitions cannot
    be pytest-verified; "done" = recorded-transcript checks + checklist review + the
    golden toy-run protocol. AD-25 continues to cover the core only.
- Epics: APPEND Epic 7 to the existing `epics.md`. Epics 1–6 are implemented, merged,
  and traceable to PRs — preserve them verbatim. Update the Requirements Inventory and
  FR Coverage Map for the new FRs only.
- Proposed Epic 7 story cut (refine at story-design time):
  7.1 Walking skeleton: minimal SKILL.md that opens a run, resolves the plugin root, and
      traverses Frame end-to-end — including the live hook proof (default-deny verified
      in a real Claude Code session, incl. the guard-crash / fail-open case).
  7.2 `llm_call` reporting entrypoint + `schemas/dispatch.yaml` + launch-time tier→model
      resolution from config.
  7.3 Role agent definitions with read-set-compliant context assembly.
  7.4 Safety discipline: refusal-retry ceiling, FR-37 budget checkpoint, adapter backoff.
  7.5 Instrumented toy run — dogfooding as a story, with the evaluation rubric as
      acceptance criteria: refusal→correction (not retry-storm) patterns, ledger
      `consumed_by` coverage, override-profile review, `premature_ideas/` volume,
      known-cluster-miss check (the recorded embedding-index revisit trigger).
- Out of scope for Epic 7: Propose/Decide flows, cross-run analytics (FR-38/40/41),
  embedding index, any live budget enforcement.
