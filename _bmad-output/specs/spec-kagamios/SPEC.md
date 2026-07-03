---
id: SPEC-kagamios
companions:
  - ../../planning-artifacts/prds/prd-KagamiOS-2026-07-02/prd.md
  - ../../planning-artifacts/prds/prd-KagamiOS-2026-07-02/addendum.md
  - ../../planning-artifacts/architecture/architecture-KagamiOS-2026-07-02/ARCHITECTURE-SPINE.md
sources:
  - ../../../archive/docs-spec/README.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# SPEC: KagamiOS v1

## Why

A vision to realize, with a self-imposed mandate on *how* it must be built. A single researcher sitting on a vague intuition needs the tractable landscape work — search, clustering, gap-finding — done automatically, while every judgment that actually defines the research direction (scope, gap meaningfulness, direction selection) stays mechanically reserved for them, because the deep failure mode of AI-assisted discovery is homogenization: the AI's fluent framing quietly becoming the researcher's own framing. That reservation must be provable, not promised — which is why KagamiOS v1 is a deterministic gatekeeper core, not a set of prompted instructions: write-guards, generation windows, and provenance are store refusals a future builder can verify against an event log, never conventions a skill happens to follow.

## Capabilities

- **CAP-1**
  - **intent:** A researcher can drive one investigation through the deterministic state machine (Frame → Map → Deepen → Synthesize → Locate) with loop-backs and skip-waivers, reaching Dissolved, Dormant, or an accepted Gap Register. (Decide/Propose exist in the schema but have no v1 flow — see Non-goals.)
  - **success:** Every state transition is a logged `state_transition` event with a cause annotation on loop-backs; derived per-cluster state (a pure function, never a hand-maintained flag) matches the schema registry's exit criteria with no manual override.

- **CAP-2**
  - **intent:** The system stores every artifact as an immutable-versioned, schema-validated, provenance-tracked file, so no AI write can reach a human-only field and no human edit can be silently lost to a race.
  - **success:** A write-guard violation is mechanically refused and logged — zero occurrences reach `accepted` status in the standing golden-fixture test suite. A human edit always survives a concurrent queued AI write to the same artifact: the AI write is refused and re-emitted as a proposed diff, never silently applied over it.

- **CAP-3**
  - **intent:** The system asks the researcher only the questions a schema/artifact diff could not resolve itself, batched at most five at a time, ranked by leverage, always against evidence already shown.
  - **success:** Every ledger entry other than the two ask-before-show unprimed questions carries a non-empty target and leverage class; no batch in the event log exceeds five questions; a rent audit shows every non-deferred question's answer was actually consumed by a downstream artifact.

- **CAP-4**
  - **intent:** Role-scoped AI work (search, clustering, history-writing, adversarial critique, section drafting) runs in isolated, read-set-bound contexts, so no role can act outside its charter or see another role's drafting rationale.
  - **success:** Every model-call event carries a non-null role tag and a valid, unexpired engagement token; a charter-violation audit (the critique role proposing an alternative, the history role speculating about the frontier, any non-search role touching the raw corpus) returns zero matches against the event log.

- **CAP-5**
  - **intent:** No direction-shaped content can be generated before the run's Gap Register is accepted, and no AI framing artifact can be created before the corresponding unprimed researcher answer is recorded.
  - **success:** Artifact creation outside its registry-declared generation window is refused, not merely discouraged; refused content is quarantined, never silently dropped; the two unprimed-question artifact-creation timestamps are always later than their ledger entries, provably from the log.

- **CAP-6**
  - **intent:** A researcher's literature search draws from multiple interchangeable providers (OpenAlex, Semantic Scholar, arXiv, GitHub) with no provider hard-coded at any call site, producing reusable paper cards.
  - **success:** Swapping the configured default provider requires no code change and passes the same adapter contract test; a paper card is computed once per paper and reused across runs rather than recomputed.

- **CAP-7**
  - **intent:** The system logs its own run deterministically, in enough detail for a human to later evaluate KagamiOS's effectiveness, without any runtime decision ever reading that log back.
  - **success:** Deleting a completed run's event log changes no other run's behavior; recomputing metrics from the same log always yields identical numbers; the fields a future cross-run analysis loop cannot retrofit (a stable question-classification key, run-id outcome joins, a permanent audit-exemption flag on the researcher's reserved decisions) are populated from run 1, even though that analysis loop itself is out of scope for v1.

- **CAP-8**
  - **intent:** A researcher installs KagamiOS as a Claude Code plugin alongside BMAD and runs it entirely on their own machine, with all researcher-owned data living in their project, never inside the plugin.
  - **success:** Plugin install/uninstall never touches the researcher's run data; the tool resolves correctly regardless of the invoking working directory; a schema upgrade refuses to mutate a run written under an older schema rather than silently corrupting it.

## Constraints

- All mechanical guarantees (write-guards, generation windows, question batching, versioning, event logging, staleness) must be deterministic code inside the plugin's core library, never prompt convention or skill instruction.
- KagamiOS ships as a Claude Code plugin co-installable with BMAD, following its layout and toolchain conventions — not a standalone application.
- The deterministic core must remain standalone-capable as a library importing no harness API, so a future non-plugin runtime is an adapter, never a rewrite.
- Literature-provider choice is never hard-coded at a call site — provider availability and pricing policy are known to drift.
- v1 scope ends at an accepted Gap Register (or Dissolved/Dormant); Propose and Decide are v2 — but the schema registry, state model, and generation-window table ship complete from v1 so v2 is additive, never a breaking migration.
- Privacy default is off: no run data leaves the researcher's local store without explicit opt-in; any future shared aggregation is content-stripped.
- Researcher-owned data lives under a configurable output root in the user's project, never inside the plugin install.

## Non-goals

- Anthropomorphic AI personas, a portfolio terminal event, a first-class knowledge hierarchy, a database as ground truth, retrieval-augmented search over the artifact graph, mechanical auto-closure of the decision gate, analytics-driven self-modification, or any research-lifecycle stage beyond one bounded, researcher-executed feasibility probe.
- Multi-researcher or lab-as-shared-gate use in v1; an advisor consumes the finished handoff bundle but never gates a run from inside it.
- A local embedding index over paper cards in v1 — a recorded, deliberate deviation from the original design's corpus-tier retrieval approach; the interim substitute is citation-graph communities plus provider-side relevance search.
- A CLI or non-plugin runtime, learned/adaptive model routing, machine-side token budgets, and the cross-run self-improvement analysis loop — all deferred past v1 with their own future adoption triggers.

## Success signal

A researcher runs one real investigation through KagamiOS v1, from an initial intuition to an accepted Gap Register or a documented dissolution, using only the minimal-run profile — and the run's event log shows zero write-guard or generation-window violations, full consumed-by traceability on every answered question, and survives a mid-run session restart without state corruption. Demonstrable directly from the run's own event log and derived metrics; no dashboard required.

## Assumptions

- MVP scope breadth (the full artifact chain through an accepted Gap Register, not narrower) and the decision to skip a hand-run paper validation before building are carried from the PRD as settled, not re-opened here.
- The original design specification is treated as fully absorbed for build purposes: every capability-relevant claim needed to implement v1 now lives in the companion PRD (as functional requirements) or the companion architecture spine (as architecture decisions); the original spec remains available for rationale but downstream build work should not need to consult it directly.

## Open Questions

- None at adoption time — both companion documents (PRD, architecture spine) carry status `final` and their own resolved open-items lists. Future open questions belong in the next downstream step (epics/stories), not here.
