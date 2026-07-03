# Addendum: KagamiOS PRD

Technical-how, mechanism depth, and rationale that doesn't belong in the PRD's main narrative but a downstream reader (architecture, epics) may need. Source of truth for anything not reproduced here in full remains `docs-spec/`; this addendum does not duplicate the machine-readable schema registry, it points to it.

## A1. Authoritative source pointers by topic

| Topic | Authoritative doc |
|---|---|
| Per-artifact field-level schema, minimal/full profile marking | `docs-spec/04_artifacts.md` §1–§5 |
| Schema registry YAML shape, write-guards, identity/versioning | `docs-spec/07_runtime.md` §1–§2 |
| Full state table (per-state input/output artifacts, AI actions, exit criteria) | `docs-spec/03_state_machine.md` §3 |
| Question card / ledger entry exact field list | `docs-spec/05_elicitation.md` §4–§5 |
| Role charter full text (permitted/forbidden outputs per role) | `docs-spec/06_roles.md` |
| Run event log event-family payload schemas | `docs-spec/08_observability.md` §2 |

The PRD (§4) states the *behavioral contract* each of these mechanisms must satisfy; it does not restate their schemas. An implementer needing the exact field list works from `docs-spec/`, not this PRD.

## A2. Dispatch table tiers (deterministic-vs-LLM routing)

Static, human-maintained mapping of operation → tier: deterministic / deterministic-ML / cheap-model / frontier-model. Every LLM call logs its operation class so the mapping is auditable against actual usage. Learned or dynamic routing is explicitly out of scope until multi-run cost data exists (`07_runtime.md` §5) — do not build an adaptive router for v1.

## A3. Generation windows (per artifact type, earliest permitted state)

Binding rule: no direction-shaped content may be generated anywhere in the system until the run-level Gap Register is accepted. Violating content is quarantined to a `premature_ideas` bucket rather than silently discarded (preserves it for audit without letting it leak into legitimate artifacts). Two unprimed questions (at Frame and at Propose) are recorded in the ledger *before* any AI output for that state is shown, specifically to protect the researcher's unprimed signal (E6). Exact per-state generation-window table: `docs-spec/05_elicitation.md` §6.

## A4. Cache and cost guidance (explicitly "guidance, not contract" in the spec)

- Prompt-cache prefix ordering: stable content (schema, role charter, artifact-under-construction) before volatile content (this turn's retrieval results). Adopt at first implementation (O2/O5).
- Machine-side token budgets / live meters: deferred (O6) until the cost ledger shows a state chronically overrunning.
- Explicit "out of scope as premature" list (`07_runtime.md` §8): vector index over artifacts, learned routing, speculative pre-generation of next-state artifacts (this would collide with generation windows — see A3), cross-run shared knowledge bases beyond paper cards/entity registry, distributed execution. The spec's framing: "one researcher, one run, one machine." Do not build any of these for v1 even if they look like natural optimizations — each was considered and rejected for now.

## A5. The design test — and the worked scale reference it comes from

`docs-spec/01_vision.md` holds every mechanism in the system to one test: *would this have moved a real investigation toward a confident choice, or would it have been overhead?* This is not a UX nicety — it is the acceptance test for whether a proposed feature, question type, or artifact field belongs in KagamiOS at all, and it should be the first thing an architect or story-writer applies when a requirement in this PRD seems ambiguous in scope.

The worked instance of that test is the "Signature investigation" dogfooding example (`docs-spec/05_elicitation.md` §7), which walks a full run end to end and documents roughly 10–15 total researcher-facing questions across the whole run, at ≤5 per batch. That number is a secondary, derived signal — useful as a volume sanity check during design and testing (if a real run is producing questions far above this order of magnitude, something in the rent test or triage is likely mis-tuned) — but it is downstream of the design test above, not a replacement for it.

## A6. Why MVP scope = the minimal-run profile, not the full artifact set

`docs-spec/09_open_items.md` OQ1 (still open) states the smallest version worth dogfooding is the *minimal-run profile* run by hand first — Inquiry Frame with its menu question, Field Map with the L2/L4 cluster question, one Cluster Dossier with a mandatory Evolution section, Gap Register with both `why_does_this_gap_exist` and `meaningful_to_me`, Question Ledger as an appended log — with the explicit test: "if the questions feel like the system reading your mind, build tooling; if they feel like a form, no tooling will save the design." The spec treats this as unresolved validation, not a decided scope call. This PRD's MVP (§7.1) targets tooling for that same minimal-run profile, on the premise that the hand-run validation either has already happened or is happening in parallel — **flagged as an open item for the PM to confirm (§9, OQ-A)** rather than silently assumed.

## A7. Rejected-alternative rationale (kept out of the PRD body per the spec's own Standing Refusals)

See PRD §6 for the list; each item there links to the originating review document (`docs-discovery-review/`, `docs-runtime-review/`) where the argument against it was made. This addendum does not re-litigate them — the PRD instruction is not to redesign KagamiOS, and re-arguing settled refusals would be exactly that.
