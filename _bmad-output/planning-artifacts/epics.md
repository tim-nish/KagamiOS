---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/specs/spec-kagamios/SPEC.md
  - _bmad-output/planning-artifacts/prds/prd-KagamiOS-2026-07-02/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-KagamiOS-2026-07-02/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/change-signal-epic7-2026-07-03.md
---

# KagamiOS - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for KagamiOS v1, decomposing the requirements from SPEC.md (primary specification, capability-framed), the finalized PRD (functional/non-functional requirements), and the Architecture Spine (technical decisions, invariants, structural seed) into implementable stories.

`docs-spec/` is **not** a design source for this breakdown — it is the audit trail SPEC.md was distilled from. Traceability, where needed, runs SPEC capability → PRD FR → Architecture AD, not back to `docs-spec/`.

**MVP boundary (binding for this breakdown):** v1 covers states Frame → Map → Deepen → Synthesize → Locate, terminating at an accepted Gap Register (or Dissolved/Dormant). Propose and the Decide gate are v2. Three requirement tiers appear below, taken directly from the Architecture Spine frontmatter (`binds` / `binds_non_preclusion` / `deferred_frs`):

- **[v1]** — full behavior implemented now.
- **[v1-schema-only]** — schema, window table, and exemption flags ship now (so v2 is additive, never a breaking migration); the researcher-facing flow does not.
- **[deferred]** — nothing ships now; needs accumulated multi-run data that MVP cannot produce.

## Requirements Inventory

### Functional Requirements

*(Numbering and wording follow the PRD's own FR-N convention for traceability. Tier tag in brackets.)*

**4.1 State Machine and Workflow Control**

FR-1: System moves a run through Frame→Map→Deepen→Synthesize→Locate→Propose→Decide with defined backward transitions (Deepen→Frame, Synthesize→Map, Locate→Deepen, Locate→Map, Propose→Locate, Decided→Propose); every transition is a logged `state_transition` event; every backward transition carries a mandatory cause annotation. [v1 — MVP exercises Frame→Map→Deepen→Synthesize→Locate only; Propose/Decide transitions are schema/window-table only]

FR-2: A researcher may skip a working state only by recording a one-line waiver at skip time; a skipped state with no waiver is a detectable data-integrity violation. [v1]

FR-3: Each cluster's derived state is computed independently as the earliest working state whose exit criteria it hasn't met; the run's nominal state is the modal cluster state; generation-window/gate logic reads per-cluster derived state, never run-level state alone. [v1]

FR-4: The constitutive triad (scope/attention allocation, gap meaningfulness, direction selection) is mechanically human-only via field-level write-guards with no trusted-mode override. [v1 for the two triad decisions in MVP scope — scope/attention and gap meaningfulness; the direction-selection leg's write-guard is schema/non-preclusion only, full flow is v2]

FR-5: For non-constitutive gates, the system may propose collapsing a review gate to a notification (grounded in the researcher's own aggregated edit history), taking effect only after explicit researcher approval that cites the specific statistic that motivated it. [v1]

FR-6: A researcher can start a run from any of five entry points (intuition-first, paper-first, field-first, problem-first, tool-first); every entry mode backfills a minimal Intuition Note and Inquiry Frame before Map begins. [v1]

FR-7: A run can end at Dissolved (Dissolution Memo) or Dormant (explicit revival conditions + continued monitoring) with the same standing as Decided; Dormant runs are reopened via a session-start sweep, never a background daemon. [v1 — both terminals reachable in MVP]

FR-8: Once Decided, monitoring continues; new evidence that stales the Direction Decision triggers an alert and reopens the existing run at the affected state, never a new run. [v1-schema-only — Decided is unreachable in MVP since Propose/Decide don't exist; the sweep mechanism it reuses (AD-24) is built for FR-7]

**4.2 Artifact System**

FR-9: Every artifact carries `id`, `type`, monotonic immutable `version`, `status`, `depends_on`, `elicited_from`, `decided_by`, a 5–10 line `summary`, and `created`/`updated` timestamps; a missing required field fails validation and blocks `accepted` status; version numbers never decrease or get reused. [v1]

FR-10: Artifacts move `draft`(AI)→`reviewed`→`accepted`(human gate); `current` always resolves to the latest accepted version, never a draft; superseded versions are retained, never deleted. [v1]

FR-11: Every artifact section has a stable, opaque ID; the artifact is `accepted` only once every minimal-profile section is accepted; citations can pin to a specific section ID; two parallel workers never write the same section simultaneously. [v1]

FR-12: Every field carries an author class (`ai`/`human`/`ai-drafted-human-confirmed`); a human edit to an AI-authored span permanently flips that span's author class; repair proposes a diff on human-touched spans rather than overwriting them. [v1]

FR-13: When a pinned dependency is re-accepted at a newer version, every dependent artifact is marked stale immediately (a pure, cheap graph traversal, no LLM call); regeneration happens only when the frontier next needs that artifact. [v1]

FR-14: The system implements the full catalog — 9 working + 2 terminal artifacts (11 total) and 5 infrastructure stores (Question Ledger, Corpus Cache, Entity Registry, Run Manifest, Run Event Log) sharing one ID space, each validating against its own schema; the Direction Decision's handoff bundle always includes the artifact graph plus a generated two-page portfolio brief. [v1-schema-only for Direction Decision/Candidate Direction types — registry ships complete per AD-14 even though unreachable in MVP; v1 in full for the other 9 artifact types + 5 stores]

FR-15: For each working state, the system defines which artifacts it reads and at what resolution (full text vs. summary only); a state never reads outside its defined consumption map; summary-only reads are logged distinctly from full-text pulls. [v1]

FR-16: Every schema field is marked `profile: minimal` or `profile: full`; a minimal-profile run validates and accepts end-to-end using only the minimal subset. [v1 — this is MVP's target profile]

**4.3 Elicitation Kernel and Question Scheduling**

FR-17: Every unknown is triaged as Computable / Human-only (candidate question, only if also blocking — the two-equally-competent-researchers test) / Deferrable (AI default applied and recorded); deferred defaults are always recorded in the Question Ledger. [v1]

FR-18: Six-step kernel loop — FRONTIER (blocking-next-gate → stale repairs on active path → checklist holes → deferred work) → ATTEMPT → TRIAGE → ASK (batch ≤5, ranked by leverage) → CONSUME (write answer to ledger, pin `elicited_from`, mark dependents stale) → repeat until Decide closes or the intuition dissolves. [v1]

FR-19: Editing an AI-authored draft directly is itself an elicitation event — it resolves the corresponding unknown and flips the edited span's provenance to human-confirmed; no redundant confirm-the-default question follows. [v1]

FR-20: If a blocking unknown goes unanswered, the system applies its recorded default, flags the resulting artifact `provisional`, and surfaces the total provisional count at the Decide gate rather than halting silently. [v1]

FR-21: Exactly one scheduler (ASK) owns batching and sequencing of researcher-facing questions, even though parallel workers may each emit candidate unknowns concurrently. [v1]

FR-22: A question may reach the researcher only if it declares a target and a leverage class, except the two unprimed E6 questions (FR-24). [v1]

FR-23: Questions are posed in ascending cost order — confirm-a-default, then menu, then rank/allocate — free text reserved for cases the cheaper forms can't express. [v1]

FR-24: At Frame and at Propose, the researcher's own unprimed answer is recorded in the ledger before any AI-generated output for that state is displayed. [v1 for the Frame-side question only, per PRD §7.1; the Propose-side unprimed question is v1-schema-only]

**4.4 AI Role Contracts**

FR-25: Only the Scout role queries the raw literature corpus (preprints, code repos, workshop venues, not just published papers); every other role works from already-processed artifacts. [v1]

FR-26: Every Field Map clustering pass produces at least two genuinely different partitionings; the researcher decides which to use or how to edit it; cluster names are human-editable and never silently reverted. [v1]

FR-27: The Skeptic role may only critique, never propose an alternative, and always runs from a fresh context excluding the target artifact's authoring conversation. [v1]

FR-28: The Historian role writes only the Cluster Dossier's Evolution section and is forbidden from frontier-facing speculation. [v1]

FR-29: Every LLM call in the event log records its acting role, so a charter violation is checkable mechanically against the log. [v1]

**4.5 Runtime Contracts**

FR-30: Each artifact type has one versioned, machine-readable schema; fields declare `type`, `profile`, `author` class, and where relevant `unknown_class_hint`/`leverage`. [v1]

FR-31: The store mechanically refuses any AI-originated write to a field marked `author: human`, regardless of role; refusals are logged, never silently dropped or allowed. [v1]

FR-32: Every artifact, ledger entry, paper card, entity, and trace event shares one ID space with stable IDs and monotonic immutable versions. [v1]

FR-33: Every artifact carries a 5–10 line summary regenerated only on acceptance; consuming states read the summary by default; a full-text pull is always an explicit, logged action. [v1]

FR-34: A working state reads artifacts only from the immediately preceding layer, never the raw corpus directly (Scout-only); no embedding index over the artifact graph (graph traversal only). [v1]

FR-35: Repair on a stale artifact runs a tiered check — Tier 0 deterministic, Tier 1 cheap-model plausibility, Tier 2 sectional regeneration — never whole-artifact regeneration. [v1]

**4.6 Observability and Self-Measurement**

FR-36: The run event log records every `llm_call`, `retrieval`, `artifact_event`, `question_event`, `human_edit`, `frontier_decision`, `gate_event`, `budget_event`, `state_transition`, `terminal_event`; no runtime behavior reads it back during the same run. [v1]

FR-37: At each gate and terminal, the system deterministically computes question economics, a token ledger, an override profile, and a decision block. [v1]

FR-38: Run summaries accumulate into a local, derived, rebuildable cross-run analytics store. [deferred — needs accumulated multi-run data]

FR-39: Traces are local-first and researcher-owned by default; aggregation is strictly opt-in and content-stripped. [v1]

FR-40: Periodic deterministic jobs over the cross-run corpus produce a human-gated Design Audit Report; the system never applies a finding automatically. [deferred — depends on FR-38]

FR-41: Every efficiency finding in a Design Audit Report ships paired with its quality-guard reading. [deferred — depends on FR-40]

**4.7 Propose, Decide, and Self-Improvement Guardrails**

FR-42: Propose presents 3–5 Candidate Directions on one fixed qualitative comparison table with no aggregate score. [v1-schema-only — v2 flow]

FR-43: Each Candidate Direction is red-teamed by the Skeptic in a fresh context before Decide. [v1-schema-only — v2 flow]

FR-44: The Decide gate exit criteria (checklist trace-complete, comparison written, dispositions recorded, human-read complete, signed). [v1-schema-only — v2 flow]

FR-45: At Map exit, the researcher sets per-cluster depth budgets, human-owned and revisable; budget exhaustion asks an extend-or-proceed question, never silently stops or continues. [v1]

FR-46: No direction-shaped content may be generated until the run-level Gap Register is accepted; violations are quarantined to `premature_ideas/`. [v1 — in MVP this means no direction-shaped content is ever legitimate, since Propose doesn't exist yet; the refusal mechanism itself is fully built]

FR-47: Constitutive-triad fields and the two unprimed E6 questions are permanently exempt from Design Audit statistical demotion. [v1-schema-only — the `audit_exempt: permanent` flag ships now; the loop that could threaten it (FR-40/41) is deferred]

**4.8 Driver & Harness Shell** *(added 2026-07-03 — Epics 1-6 shipped the deterministic core with no epic covering the harness that drives it; see change-signal-epic7-2026-07-03.md)*

FR-48: The chokepoint tracks consecutive identical refusals per `(entrypoint, target)`; the attempt past a configured ceiling returns a distinct `requires_researcher` status instead of an ordinary refusal, forcing a stop-and-surface outcome rather than an unbounded retry loop. [v1]

FR-49: The harness reports every model call it makes — role, operation class, model tier, token counts, cache-hit — through a validated `kagami` entrypoint immediately after the call; the core never invokes models itself and never infers these fields. [v1]

### NonFunctional Requirements

NFR1: **Platform.** KagamiOS installs and runs as a Claude Code plugin, co-installable with BMAD, following its layout conventions (skills + deterministic scripts + hooks). Mechanical guarantees are deterministic code inside the plugin — a script chokepoint is the only sanctioned mutation path, hooks block direct AI writes — never prompt convention. Accepted v1 trade-offs: main-thread token/prompt accounting is incomplete; scheduler obedience is detect-and-audit rather than prevent.

NFR2: **Auditability by construction.** Every mechanically enforceable rule (write-guards, generation windows, role charters, gate approvals) must be checkable against the run event log after the fact, not just assertable as intended behavior.

NFR3: **Determinism before generation.** Wherever a value can be computed deterministically (staleness, provisional counts, derived metrics, per-run summaries), it must be — never inferred by a model call.

NFR4: **Privacy is local-first by default, not opt-out.** Sharing is opt-in and content-stripped, never the reverse. No design-analytics feature may require sharing to function for a single researcher.

NFR5: **Cost discipline via retrieval boundaries, not budgets.** v1 controls token/compute cost through the context loading contract and retrieval boundary (FR-33, FR-34), not live budget enforcement; machine-side budgets/meters are explicitly deferred.

NFR6: **No silent data loss.** Superseded artifact versions are retained (FR-10); human-touched spans are never silently overwritten (FR-12); rejected writes are logged, not dropped (FR-31).

NFR7: **Provider resilience** *(added 2026-07-03)*. Literature-provider adapters implement backoff/retry against each provider's documented rate limits so transient throttling surfaces as a retry, never as a run-ending error.

### Additional Requirements

**Structural seed (functions as this project's starter template — Epic 1 Story 1 target):** the Architecture Spine's plugin tree is the exact greenfield scaffold to stand up first:
```
kagamios/                          # plugin root (code only)
  .claude-plugin/plugin.json
  pyproject.toml                   # AD-23: uv project for the core
  skills/kagami-discovery/SKILL.md # the Interviewer (AD-4)
  agents/                          # scout.md, cartographer.md, historian.md, skeptic.md, worker.md
  hooks/                           # default-deny guard, session/turn markers (AD-2, AD-3, AD-4)
  kagami/                          # deterministic core (AD-5): store/ kernel/ events/ corpus/ briefs/
  schemas/                         # versioned YAML registry (AD-12, AD-14)
```
Plus the user-project output tree under a configurable root (`_kagami-output/config.yaml`, `runs/<run-id>/`, `corpus/`, `registry/`, `profile/researcher-profile/`) — never inside the plugin install (AD-13).

**Architecture invariants (AD-1..AD-25) — each is an implementation requirement, not a suggestion:**

- AD-1: Claude Code plugin, deterministic gatekeeper core; no rule may exist only in a SKILL.md.
- AD-2: `kagami` CLI entrypoints are the only sanctioned mutation path; PreToolUse hook is default-deny for any tool call referencing the output root, single allow-pattern for the `kagami` invocation form.
- AD-3: Data-plane (`current.md`) vs. control-plane (`meta.yaml`, `manifest.yaml`, `events.jsonl`, `queue/`, ledger, locks) — control-plane is chokepoint-exclusive; out-of-band changes are corruption, detected by hash, refused, rebuilt where derivable.
- AD-4: Roles (Scout, Cartographer, Historian, Skeptic, `worker`) are subagents with role-restricted tools; sessions registered via `kagami session open/close`; `kagami brief <role> <state> <target>` renders read-set-compliant context and mints a single-use engagement token.
- AD-5: `kagami/` core imports no harness API; standalone-capable library; harness bindings are adapters.
- AD-6: Each artifact is a directory of immutable `vN.md` files + mutable `current.md` (only human edit surface) + `meta.yaml`; `kagami scan` diffs `current.md` against the latest hash to mint `v(N+1).md`.
- AD-7: One `LiteratureProvider` port; OpenAlex/Semantic Scholar as peer adapters, arXiv/GitHub as complementary; no call site names a provider; credentials from environment variables only, never `config.yaml`.
- AD-8: `kagami ask` is the only entrypoint creating researcher-facing questions; batch ≤5 enforced at the ledger; worker-emitted unknowns land in `queue/` first.
- AD-9: Generation windows enforced by store refusal, keyed to per-cluster derived state (except Candidate-Direction, keyed to run-level Gap Register acceptance); refused content quarantines to `premature_ideas/`.
- AD-10: Parallel writers claim sections; claims are lease-bound and reaped at run open if expired.
- AD-11: Event log is append-only JSONL, core-written only, no runtime read-back; `llm_call` events carry role/operation_class/model_tier/tokens/cache-hit; documents the honest-gap register of accepted detect-and-audit residuals.
- AD-12: Dispatch table (`schemas/dispatch.yaml`) maps operation classes to tiers (deterministic/deterministic-ML/cheap-model/frontier-model); `config.yaml` maps tiers to concrete models; code never names a model or provider directly.
- AD-13: User data (`runs/`, corpus cache, entity registry, researcher profile) lives under the configurable output root in the user's project, never in the plugin install.
- AD-14: State enum, schema registry, and generation-window table ship complete (all 6 states + Decide, all 11 artifact types) from v1; the stable question-class key, run-id outcome-join fields, and `audit_exempt: permanent` flag are locked in from run 1.
- AD-15: Every mutating entrypoint acquires an exclusive advisory lock (`flock`) on `runs/<run-id>/.lock`; one writer session per run via a lease file; fixed write order (version file → meta → event) via temp-file + fsync + atomic rename.
- AD-16: Scan-before-write — inside the same locked operation, `current.md` hash check runs first; an AI write overlapping a human-confirmed span is refused and re-emitted as a proposed-diff artifact, never applied.
- AD-17: Question Ledger entries are structured records (`ledger/q-NNN.yaml`) validated against the ledger schema; entry versions are immutable; `ledger.md` is a derived, regenerable render, not an edit surface.
- AD-18: `profile/researcher-profile/` is a normal AD-6 artifact directory; `corpus/` and `registry/` are derived, unversioned, content-derived-ID stores (`ppr-`, `ent-`) so concurrent minting converges.
- AD-19: Section IDs are opaque (`sec-` + minted suffix), created once, registered in `meta.yaml`, never content-derived; retirement is a logged event.
- AD-20: Per-cluster derived state is `kagami/kernel/`'s pure function over store + ledger; `manifest.yaml`'s state fields are a cache, never read for a guard decision.
- AD-21: Repair is tiered, frontier-triggered (never eager), sectional; human-touched spans get proposed diffs only.
- AD-22: Chokepoint entrypoints never invoke models directly — an operation either demands model output as a schema-validated input argument, or returns a typed `needs_llm` work item the harness fulfills and resubmits.
- AD-23: Every invocation is `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami <cmd>`; every write stamps `schema_registry_version`; the chokepoint refuses to mutate a run written under a newer registry; `kagami migrate` is the only path that rewrites old runs.
- AD-24: `kagami monitor` executes monitoring config as a sweep at run open / skill activation — never a background daemon.
- AD-25: The core is tested at the CLI entrypoint boundary (`kagami/` and `hooks/` only) with a scripted driver replacing the harness; a golden minimal-run fixture exercises windows, guards, staleness, E6 ordering, scan-before-write, lease/crash recovery.
- AD-26 *(added 2026-07-03)*: Driver operational discipline. The refusal-retry ceiling (FR-48) is a pure function over the tail of `events.jsonl`, no new store — `(entrypoint, target)` identity, resets on any intervening non-refusal event. `llm_call` reporting (FR-49) goes through the named entrypoint `kagami report llm-call`, harness-minted `--call-id` for idempotency, duplicate call-ids refused. `kagami metrics`'s decision block (FR-37) adds a gate-time soft-limit warning — reporting, never live budget enforcement (PRD §5 NFR / addendum A4 stay intact).
- AD-27 *(added 2026-07-03)*: Testing convention for prompt artifacts. `skills/` and `agents/` cannot be pytest-verified (AD-25 stops at `kagami/`/`hooks/`); a driver story's Definition of Done instead requires a recorded Claude Code session transcript, a charter checklist review, and — for the walking-skeleton and toy-run stories — the golden toy-run protocol (fixed topic/corpus/config, event log checked against a pre-agreed rubric).
- **v1-driver amendments (2026-07-03):** AD-4's `kagami session open/close` and single-use engagement tokens are deferred — role attribution collapses to one self-declared `--role` argument shared by content writes and AD-26's telemetry, with no session binding; the resulting weakening is logged as a new AD-11 honest-gap entry, not silently accepted. AD-11's "no runtime behavior reads the log back" claim is clarified: `kagami metrics` reading the raw log to *report* (FR-37, always allowed) is distinct from a *behavior-altering* read (FR-5's gate-loosening, the one sanctioned exception) — AD-26's gate-time warning is the former. AD-1 gained a note distinguishing enforceable core guarantees from AD-26(b)'s harness-side reporting obligation, which the core cannot compel, only leave visibly uncredited if skipped.

**Integration / infrastructure requirements (Stack table):**
- Python ≥3.12; `uv` toolchain shared with BMAD; plugin ships `pyproject.toml`.
- pydantic 2.13.x for schema registry validation; PyYAML 6.x (no comment round-trip — machine-owned YAML only).
- OpenAlex adapter needs an API key (env var) from day one — mandatory since Feb 2026, usage-based pricing.
- Semantic Scholar adapter should support an optional free key for the dedicated ~1 RPS tier over the throttled keyless pool.
- arXiv adapter needs backoff/etiquette handling (~1 req/3s, tightening 429s reported).
- GitHub search adapter needs a token (search rate limit ~30 req/min).

**Consistency conventions (cross-cutting, apply to every story):** one ID space with typed prefixes (`run-`, `art-`, `sec-`, `q-`, `ppr-`, `ent-`, `evt-`) minted only by the chokepoint; artifact type slugs are kebab-case matching schema registry filenames exactly; dates are ISO-8601 UTC everywhere; every `kagami` entrypoint echoes one-line JSON (`{"ok": bool, ...}`); event log is JSONL, one event per line; invocation is always `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami <cmd>`; `current.md` is the only human edit surface; credentials are environment variables only; PRD Glossary terms appear verbatim in code identifiers, schema names, and docs — no synonyms.

### UX Design Requirements

*None.* No UX design contract (`DESIGN.md`/`EXPERIENCE.md` or legacy `*ux*.md`) was found under `{planning_artifacts}`. KagamiOS v1's only human-facing surface is the Claude Code conversational interaction inside the elicitation kernel (FR-17..24) and the artifact Markdown files themselves — governed entirely by the FR/AD entries above, not a separate visual/interaction spec. Confirmed with user before proceeding (see step 1 confirmation).

### FR Coverage Map

FR-1: Epic 1 - state machine skeleton, state_transition event logging (loop-back consequences fully exercised in Epic 5)
FR-2: Epic 1 - skip-waiver mechanism
FR-3: Epic 2 - per-cluster derived state (first point clusters can diverge)
FR-4: Epic 1 - constitutive-triad write-guard mechanism + scope/attention leg (gap-meaningfulness leg exercised in Epic 4; direction-selection leg is v2)
FR-5: Epic 5 - gate-loosening proposal + researcher approval
FR-6: Epic 1 - five entry modes backfilling Intuition Note + Inquiry Frame
FR-7: Epic 5 - Dissolved/Dormant terminals, Dissolution Memo, monitoring sweep
FR-8: Epic 5 - post-decision staleness reopen (non-preclusion; reuses Epic 5's sweep)
FR-9: Epic 1 - common artifact metadata
FR-10: Epic 1 - draft-to-accepted lifecycle
FR-11: Epic 1 - section-level acceptance and addressing
FR-12: Epic 1 - field-level authorship and edit preservation
FR-13: Epic 1 - eager staleness marking
FR-14: Epic 1 - full artifact catalog (11 types) + 5 infrastructure stores, schema registry
FR-15: Epic 1 - per-state consumption map
FR-16: Epic 1 - minimal-run profile
FR-17: Epic 1 - three-way unknown triage
FR-18: Epic 1 - six-step kernel loop
FR-19: Epic 1 - edit-as-elicitation-event
FR-20: Epic 1 - provisional flag on unanswered blockers
FR-21: Epic 1 - single-threaded ASK step
FR-22: Epic 1 - well-formed questions only
FR-23: Epic 1 - cheapest question form first
FR-24: Epic 1 - Frame-side ask-before-show (Propose-side is v2/non-preclusion, covered here as schema only)
FR-25: Epic 2 - Scout is sole corpus-touching role
FR-26: Epic 2 - Cartographer's two-cut clustering requirement
FR-27: Epic 3 - Skeptic attacks-only, fresh context
FR-28: Epic 3 - Historian confined to Evolution section
FR-29: Epic 6 - role-tagged LLM calls, charter-violation auditability
FR-30: Epic 1 - schema registry with per-field metadata
FR-31: Epic 1 - write-guard rejects AI writes to human-only fields
FR-32: Epic 1 - stable identity and versioning
FR-33: Epic 1 - context loading contract (summary-by-default)
FR-34: Epic 2 - retrieval boundary (each state reads only the layer below; Scout-only raw corpus)
FR-35: Epic 3 - sectional repair pipeline
FR-36: Epic 1 - run event log, write-only during a run
FR-37: Epic 6 - deterministic per-run derived metrics
FR-38: **Deferred, no epic** - cross-run analytics store; needs accumulated multi-run data past MVP
FR-39: Epic 6 - trace privacy (local-first, opt-in, content-stripped)
FR-40: **Deferred, no epic** - Design Audit Report loop; depends on FR-38
FR-41: **Deferred, no epic** - anti-Goodhart pairing; depends on FR-40
FR-42: Epic 1 - Candidate-comparison schema (non-preclusion; v2 flow)
FR-43: Epic 1 - Candidate red-team schema (non-preclusion; v2 flow)
FR-44: Epic 1 - Decide-gate exit-criteria schema (non-preclusion; v2 flow)
FR-45: Epic 2 - depth budgets set at Map exit
FR-46: Epic 4 - generation-window enforcement, proven end-to-end at the Gap Register boundary
FR-47: Epic 1 - permanent audit-exemption flag on constitutive-triad + E6 fields
FR-48: Epic 7 - refusal-retry ceiling with mandatory escalation
FR-49: Epic 7 - llm_call reporting through a validated entrypoint

NFR1: Epic 1 - platform (plugin runtime, chokepoint architecture)
NFR2: Epic 1 - auditability by construction (mechanism); proven end-to-end in Epic 6
NFR3: Epic 1 - determinism before generation
NFR4: Epic 6 - privacy is local-first by default
NFR5: Epic 2 - cost discipline via retrieval boundaries
NFR6: Epic 1 - no silent data loss
NFR7: Epic 7 - provider resilience (backoff/retry against documented rate limits)

## Epic List

### Epic 1: Plugin Foundation, Chokepoint Substrate & First Framed Investigation
A researcher can install KagamiOS as a Claude Code plugin and take one real investigation through the entire Frame state — capture an Intuition Note from any of the five entry modes, answer the unprimed Frame question before seeing any AI framing, resolve the menu-form scope question, and reach a human-accepted Inquiry Frame — with every mechanical guarantee this whole system depends on already enforced and provable from the event log: the `kagami` chokepoint as the only mutation path, full artifact versioning/provenance/write-guards, the complete 11-type schema registry (including the Propose/Decide types that ship as schema-only so v2 is additive), the six-step elicitation kernel with ASK batching, and an append-only event log. This is the largest epic by design — the store, kernel, schema registry, and event log are one tightly-coupled substrate (same core files under AD-2/AD-6/AD-8/AD-11/AD-15) that every later epic reuses without re-touching; splitting it further would only create file churn across the same modules.
**FRs covered:** FR-1, FR-2, FR-4 (scope/attention leg), FR-6, FR-9, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18, FR-19, FR-20, FR-21, FR-22, FR-23, FR-24 (Frame side), FR-30, FR-31, FR-32, FR-33, FR-36, FR-42, FR-43, FR-44, FR-47
**NFRs:** NFR1, NFR2, NFR3, NFR6

### Epic 2: Field Mapping
Building on an accepted Inquiry Frame, a researcher runs Map: Scout searches the multi-provider literature corpus (OpenAlex, Semantic Scholar, arXiv, GitHub) and reports back only what exists, Cartographer drafts at least two structurally different ways to cluster the field, the researcher picks or edits one, and sets per-cluster depth budgets before Deepen opens. This is the first point the run's per-cluster derived state can diverge from the run-level nominal state, and the first point the corpus-only retrieval boundary (Scout) is load-bearing.
**FRs covered:** FR-3, FR-25, FR-26, FR-34, FR-45
**NFRs:** NFR5

### Epic 3: Cluster Deepening
A researcher deepens one cluster at a time: Historian writes each Cluster Dossier's mandatory Evolution section (and nothing else), representative papers are marked `human_read`, the Skeptic attacks framings and clusterings from a fresh context, and parallel per-cluster workers claim sections without colliding. This is where the sectional repair pipeline gets its first real exercise, since dossiers are the first artifacts to go stale mid-run as Map's Field Map is revised.
**FRs covered:** FR-27, FR-28, FR-35

### Epic 4: Synthesis & Gap Register — the MVP Terminal Deliverable
A researcher completes Synthesize (the solved/open table, each "open" claim backed by evidence of openness) and Locate, reaching an accepted Gap Register — MVP's actual deliverable, the point v1 is considered a success per SPEC.md's CAP-1 and CAP-5. The gap-meaningfulness leg of the constitutive triad is exercised for the first time here, and generation-window enforcement is proven for real: an attempt to generate direction-shaped content before this Gap Register is accepted is mechanically refused and quarantined, not merely discouraged. Most of the underlying mechanism was already built in Epic 1; this epic is deliberately thin on new FRs because it is the assembly and proof point, not new substrate.
**FRs covered:** FR-4 (gap-meaningfulness leg, extends Epic 1), FR-46

### Epic 5: Loop-backs, Waivers & Off-Ramps
A researcher's investigation rarely goes in a straight line: this epic delivers the defined backward transitions (Deepen→Frame, Synthesize→Map, Locate→Deepen, Locate→Map) with mandatory cause annotations, the explicit-waiver path for skipping a state, gate-loosening proposals that only take effect on researcher approval, and the two other terminal outcomes — a fast, well-documented Dissolution Memo when an intuition doesn't survive scrutiny, and a Dormant run under sweep-based monitoring with defined revival conditions. The post-decision staleness reopen (FR-8, v2-relevant) reuses this epic's sweep mechanism and ships as non-preclusion schema/behavior now.
**FRs covered:** FR-1 (loop-back consequences), FR-5, FR-7, FR-8

### Epic 6: Run Observability & Trust Substrate
Everything logged since Epic 1 becomes actually useful here: deterministic per-run metrics (question economics, token ledger, override profile) computed at every gate, a mechanical charter-violation audit that catches a role acting outside its contract without re-reading transcripts, and trace privacy proven — local-first by default, with any opt-in sharing verified content-stripped. This is the epic that makes SPEC.md's CAP-4 and CAP-7 success criteria checkable facts against the event log rather than promises.
**FRs covered:** FR-29, FR-37, FR-39
**NFRs:** NFR4

**Explicitly out of epic scope (deferred past MVP, per Architecture Spine `deferred_frs`):** FR-38 (cross-run analytics store), FR-40 (Design Audit Report loop), FR-41 (anti-Goodhart pairing) — all three require accumulated data from multiple completed v1 runs that MVP itself cannot produce. The run-1 schema commitments that make them possible later (AD-14) are already covered by Epic 1's FR-14/FR-47 stories.

### Epic 7: Driver & Harness Shell
Epics 1–6 built a deterministic core with 337 passing tests but no epic ever covered the harness that actually drives it — no `skills/kagami-discovery/SKILL.md`, no `agents/`, no producer for the `llm_call` events Epic 6's metrics and charter audit depend on. This epic closes that structural gap rather than opening new product surface: the Interviewer skill and the five role agent definitions (Scout, Cartographer, Historian, Skeptic, worker) specified since Epic 1's AD-4 are actually built and drive a real investigation through the existing core, and the two driver-side guarantees that only surfaced once the harness was scoped for implementation — a refusal-retry ceiling that stops runaway retries instead of the core looping silently, and mandatory `llm_call` reporting so Epic 6's token ledger and charter audit see real data instead of zero — ship as new architecture (AD-26, AD-27) and two new FRs. The epic ends with a golden toy-run dogfooding pass whose pass/fail verdict, not story completion, is the actual readiness gate for using KagamiOS on real research.
**FRs covered:** FR-48, FR-49 (operationalizes FR-17..29, FR-33/34, FR-37 through an actual harness for the first time — those FRs were already structurally covered by Epics 1/2/3/6)
**NFRs:** NFR7
**Explicitly out of Epic 7 scope (deferred, per Architecture Spine AD-4's v1-driver amendment):** `kagami session open/close` and single-use engagement tokens — role attribution is self-declared and trusted for v1-driver instead. Revisit trigger: a role writing off-charter content that a token check would have caught, surfaced during Story 7.5's toy run.

## Epic 1: Plugin Foundation, Chokepoint Substrate & First Framed Investigation

A researcher can install KagamiOS as a Claude Code plugin and take one real investigation through the entire Frame state, with every mechanical guarantee the rest of the system depends on already enforced and provable from the event log.

### Story 1.1: Plugin Scaffold & Chokepoint Bootstrap

As a researcher,
I want KagamiOS to install as a Claude Code plugin with a single `kagami` entrypoint that every write must pass through,
So that no AI write can ever bypass the system's guarantees, and my run data stays mine.

**Acceptance Criteria:**

**Given** the plugin is installed in a Claude Code project
**When** I invoke any `kagami` subcommand via `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami <cmd>`
**Then** it resolves correctly regardless of the invoking working directory (AD-23)

**Given** the plugin is installed
**When** any tool call (`Write`, `Edit`, or `Bash`) references the output root
**Then** the PreToolUse hook denies it unless it matches the single `kagami` invocation allow-pattern — never an enumerated blocklist (AD-2)

**Given** the plugin is uninstalled
**When** I check my run data afterward
**Then** it is untouched — the plugin directory contained only code, schemas, skills, agents, and hooks, never researcher-owned state (AD-13, SPEC CAP-8)

**Given** no run exists yet
**When** I run `kagami run open` for a new run
**Then** a `runs/<run-id>/` directory is created under the configurable output root with `.lock`/`.lease`, an empty `manifest.yaml`, and `events.jsonl` (AD-13, AD-15)

**Given** an old run written under a newer schema registry than the currently installed one
**When** the chokepoint attempts to mutate it
**Then** the mutation is refused; the run remains readable read-only (AD-23)

### Story 1.2: Schema Registry for the Full Artifact Catalog

As a researcher,
I want every artifact type — including the v2 Propose/Decide types — to have one versioned, machine-readable schema from day one,
So that v2 is additive later and never a breaking migration against my v1 runs.

**Acceptance Criteria:**

**Given** the schema registry
**When** I inspect it
**Then** all 11 artifact types are present with kebab-case slugs matching the consistency convention: `intuition-note`, `researcher-profile`, `inquiry-frame`, `confidence-checklist`, `field-map`, `cluster-dossier`, `landscape-synthesis`, `gap-register`, `candidate-direction`, `direction-decision`, `dissolution-memo` (FR-14)

**Given** any schema field in the registry
**When** I inspect it
**Then** it declares `type`, `profile` (minimal/full), and `author` class, and — where relevant — `unknown_class_hint` and `leverage` (FR-30)

**Given** the constitutive-triad fields (scope/attention, gap-meaningfulness, direction-selection) and the two E6 unprimed-question fields
**When** I inspect their schema entries
**Then** each carries `audit_exempt: permanent` (FR-47)

**Given** the Candidate Direction and Direction Decision schemas
**When** I inspect them
**Then** the comparison-table axes (FR-42), red-team-notes field (FR-43), and Decide-gate exit-criteria fields (FR-44) are fully defined, even though no v1 flow creates instances of these types

**Given** the 5 infrastructure stores (Question Ledger, Corpus Cache, Entity Registry, Run Manifest, Run Event Log)
**When** I inspect the registry
**Then** each has its own schema and is queryable by the same ID mechanism as researcher-facing artifacts (FR-14)

**Given** an artifact submitted for validation against the wrong type's schema
**When** validation runs
**Then** it is rejected — an artifact of one type can never be accepted against another type's schema (FR-14)

**Given** the state enum and generation-window table
**When** I inspect them
**Then** all six working states plus Decide are present, even though MVP's flow only reaches Locate (AD-14)

### Story 1.3: Artifact Store — Versioning, Provenance & the Human Edit Surface

As a researcher,
I want every artifact to be an immutable-versioned, human-editable Markdown file where my edits always win over queued AI writes,
So that no AI write can ever silently overwrite something I changed, and no prior state of my work is ever lost.

**Acceptance Criteria:**

**Given** a new artifact is created
**When** I inspect its directory
**Then** it contains `v1.md` (immutable), `current.md` (the only human edit surface), and `meta.yaml` (FR-9, AD-6)

**Given** I hand-edit `current.md`
**When** `kagami scan` runs
**Then** it diffs against the latest version's recorded hash, mints `v(N+1).md` with the touched spans marked `human-confirmed`, and advances the current pointer (AD-6, FR-12)

**Given** an AI-originated write targets a field marked `author: human`
**When** the chokepoint validates the write
**Then** it is refused at the storage layer and logged as a rejected-write event — never silently dropped or silently allowed (FR-31)

**Given** a human-confirmed span and a queued AI write that overlaps it
**When** the chokepoint processes the write inside the same locked operation
**Then** the human edit is processed first and the AI write is refused and re-emitted as a proposed-diff artifact, never applied (AD-16, FR-12)

**Given** an artifact missing any required metadata field (`id`, `type`, `version`, `status`, `depends_on`, `elicited_from`, `decided_by`, `summary`, `created`/`updated`)
**When** validation runs
**Then** it fails and the artifact cannot reach `accepted` status (FR-9)

**Given** a version has been superseded by a newer one
**When** I query the artifact's history
**Then** the superseded version is still retrievable, never deleted (FR-10)

**Given** two parallel workers write to the same artifact
**When** they target different registered section IDs
**Then** both writes succeed; **when** they target the same section ID, the second write is rejected as claimed (FR-11, AD-10, AD-19)

**Given** two parallel writers request new IDs simultaneously
**When** both requests are processed under the run lock
**Then** they never receive the same new ID, and `depends_on`/`elicited_from` pin the specific version referenced at consumption time (FR-32, AD-15)

**Given** a pinned dependency is re-accepted at a newer version
**When** the chokepoint processes that acceptance
**Then** every dependent artifact is marked stale immediately via a pure, cheap graph traversal — no LLM call involved (FR-13)

### Story 1.4: Elicitation Kernel — The Six-Step Loop and Ask-Before-Show

As a researcher,
I want the system to ask me only the questions a schema/artifact diff couldn't resolve itself, batched and ranked,
So that I'm never interrupted with something computable, unearned, or more than five questions deep.

**Acceptance Criteria:**

**Given** an unknown the system encounters while building an artifact
**When** it is triaged
**Then** it is classified Computable, Human-only (only if also blocking), or Deferrable, and every Deferrable default is recorded in the Question Ledger even though no question was asked (FR-17)

**Given** the FRONTIER step selects the next work item
**When** I inspect the event log
**Then** it logs which of the four priority classes it came from — blocking-next-gate, stale repairs on the active path, checklist holes, or deferred work (FR-18)

**Given** a batch of candidate questions
**When** ASK runs
**Then** it never exceeds 5 questions, and every question has a non-empty target and leverage class except the two unprimed E6 questions (FR-18, FR-22)

**Given** a question could be posed as confirm-a-default, menu, or free text
**When** it is generated
**Then** the cheapest form able to express it is used — free text only when the cheaper forms were considered and rejected (FR-23)

**Given** I directly edit an AI-authored draft span
**When** the edit is saved
**Then** the corresponding unknown is resolved, the span's provenance flips to human-confirmed, and no redundant confirm-the-default question follows (FR-19)

**Given** a blocking unknown goes unanswered
**When** the frontier proceeds past it
**Then** the recorded default is applied, the resulting artifact is flagged `provisional`, and the provisional count is surfaced rather than the run halting silently (FR-20)

**Given** parallel workers each emit candidate unknowns concurrently
**When** those unknowns reach the researcher
**Then** exactly one scheduler (ASK) has batched and sequenced them — no two questions from different workers arrive in the same turn without passing through it (FR-21)

**Given** I answer a question
**When** CONSUME runs
**Then** the answer is written to the ledger, `elicited_from` is pinned on the consuming artifact, and dependents are marked stale (FR-18)

**Given** the Frame state begins
**When** the system would show me any AI-generated framing output
**Then** my own unprimed answer to the Frame E6 question is already recorded in the ledger with an earlier timestamp than that output's display (FR-24)

### Story 1.5: Context Loading Contract & Consumption Map

As a researcher,
I want the system's context reads to be predictable and bounded,
So that every state only sees what it's supposed to, and I can trust that cost stays proportionate to what's actually needed.

**Acceptance Criteria:**

**Given** an artifact has been accepted
**When** its summary is generated
**Then** it is 5–10 lines, regenerated only at acceptance time, and stored as part of that version (FR-33)

**Given** a working state consumes another artifact
**When** it reads by default
**Then** it reads the summary; a full-text pull is always a distinct, explicitly logged action (FR-33, FR-15)

**Given** each working state's defined consumption map
**When** a state attempts to read an artifact type outside that map
**Then** the read is not supported by any brief the system can render for that state (FR-15)

**Given** a high rate of full-text pulls immediately following a summary read for the same artifact
**When** metrics are computed later
**Then** this pattern is a detectable signal, distinguishable in the log from a summary-only read (FR-33)

### Story 1.6: Run Event Log

As a researcher,
I want a complete, tamper-evident record of everything that happened during my run,
So that I can later verify — not just trust — that the system behaved correctly.

**Acceptance Criteria:**

**Given** any chokepoint entrypoint mutates state
**When** the operation completes
**Then** exactly one event is appended to `events.jsonl` as part of the same locked operation — one JSON object per line, single `O_APPEND` write (FR-36, AD-11, AD-15)

**Given** the ten event families (`llm_call`, `retrieval`, `artifact_event`, `question_event`, `human_edit`, `frontier_decision`, `gate_event`, `budget_event`, `state_transition`, `terminal_event`)
**When** I inspect the log for a completed run
**Then** every event produced by this epic's operations appears tagged with the correct family (FR-36)

**Given** a completed run's event log is deleted
**When** I compare that run's future behavior against an intact-log run
**Then** behavior is identical — no runtime code path reads the log back during a run (FR-36, AD-11)

**Given** the run targets the minimal-run profile
**When** the run is validated end-to-end
**Then** every full-profile field is legitimately empty and validation still passes (FR-16)

### Story 1.7: First Framed Investigation

As a researcher,
I want to take a real intuition through Frame, from any entry point, to an accepted Inquiry Frame,
So that I can trust this substrate actually works for a real investigation, not just as isolated mechanisms.

**Acceptance Criteria:**

**Given** I start a run via any of the five entry modes (intuition-first, paper-first, field-first, problem-first, tool-first)
**When** the run begins
**Then** a non-empty Intuition Note and Inquiry Frame exist before Map begins (FR-6)

**Given** the Frame state runs
**When** I complete it
**Then** I have answered the unprimed E6 question and the menu-form scope question, and the Inquiry Frame reaches `accepted` via draft→reviewed→accepted (FR-10, FR-24)

**Given** I attempt to skip the Frame state
**When** I do so without recording a one-line waiver
**Then** the run is flagged as a detectable data-integrity violation (FR-2)

**Given** scope/attention allocation is a constitutive-triad decision
**When** any AI role attempts to write that field
**Then** the write is refused at the storage layer, with no trusted-mode override at any level (FR-4, FR-31)

**Given** I reach an accepted Inquiry Frame
**When** I inspect the event log
**Then** every state transition taken so far is logged as a `state_transition` event (FR-1)

## Epic 2: Field Mapping

Building on an accepted Inquiry Frame, a researcher runs Map to a human-accepted Field Map with depth budgets set for Deepen.

### Story 2.1: Scout Searches the Corpus, Provider-Agnostically

As a researcher,
I want literature search to draw from multiple interchangeable providers with no provider hard-coded anywhere,
So that swapping my default provider later costs me a config change, not a code change — and I get paper cards I can reuse across runs.

**Acceptance Criteria:**

**Given** the `LiteratureProvider` port
**When** I inspect any call site that searches literature
**Then** no call site names a specific provider — the default comes from `config.yaml` (AD-7)

**Given** OpenAlex and Semantic Scholar are configured as peer adapters, and arXiv and GitHub as complementary-source adapters
**When** I swap the configured default provider
**Then** the swap requires no code change and passes the same adapter contract test (SPEC CAP-6, AD-7)

**Given** provider credentials
**When** the adapter authenticates
**Then** credentials come from environment variables only, never from `config.yaml` (AD-7)

**Given** the Scout role runs a search
**When** it queries the corpus
**Then** its scope includes preprint servers and code repositories, not just indexed publication venues (FR-25)

**Given** the Scout role is the only role invoking a search tool
**When** any other role's LLM call is inspected in the event log
**Then** no non-Scout call shows a raw-corpus retrieval — all raw-corpus retrievals are attributed to Scout (FR-25, FR-34)

**Given** a paper has already been searched in a prior run
**When** Scout encounters it again
**Then** its paper card is computed once and reused, with a `schema_version` recorded, rather than recomputed (SPEC CAP-6, AD-18)

**Given** a working state other than Map/Scout attempts to read the raw corpus directly
**When** that read is attempted
**Then** it is refused — a state may only read the layer immediately below it, and there is no embedding index over the artifact graph (FR-34)

### Story 2.2: Cartographer Drafts Two Structurally Different Clusterings

As a researcher,
I want to see at least two genuinely different ways to cut the field, and to be the one who picks or edits the clustering,
So that no single AI framing of the field quietly becomes my framing before I've even seen an alternative.

**Acceptance Criteria:**

**Given** a Field Map clustering pass runs
**When** Cartographer drafts it
**Then** at least two structurally different partitionings of the field are produced (FR-26)

**Given** a Field Map draft with only one proposed clustering
**When** it is validated
**Then** it fails validation (FR-26)

**Given** the two candidate clusterings
**When** they are presented to me
**Then** I pick one or edit either, and cluster names are always human-editable (FR-26)

**Given** I have edited a cluster name
**When** a later repair pass runs
**Then** my edited name is never silently reverted (FR-26, FR-12)

**Given** the accepted Field Map
**When** I inspect it
**Then** it records each cluster's recency profile (how fast it moves, how stale its published record runs) at minimal-profile depth (PRD §7.1)

### Story 2.3: Per-Cluster Derived State and Depth Budgets

As a researcher,
I want each cluster's progress tracked independently, and to set my own depth budgets before Deepen begins,
So that different parts of my investigation can move at different speeds without the system forcing false lockstep — and so I stay in control of scope.

**Acceptance Criteria:**

**Given** an accepted Field Map
**When** the kernel computes each cluster's derived state
**Then** it is computed independently as the earliest working state whose exit criteria that cluster hasn't yet met, and the run's nominal state is the modal cluster state (FR-3)

**Given** two clusters in the same run
**When** I inspect their states
**Then** they can be shown as being in different states simultaneously (FR-3)

**Given** any generation-window or gate-placement check
**When** it evaluates a cluster
**Then** it reads that cluster's derived state, never the run-level nominal state alone (FR-3, AD-20)

**Given** Map exit
**When** I set depth budgets
**Then** I specify how many clusters to deepen, how many papers per cluster, and a soft time horizon — all human-owned and revisable at any point (FR-45)

**Given** a depth budget is exhausted during Deepen
**When** the exhaustion is detected
**Then** the system asks a specific extend-or-proceed question rather than silently stopping or silently continuing past it (FR-45)

## Epic 3: Cluster Deepening

A researcher deepens one cluster at a time to a set of human-verified Cluster Dossiers.

### Story 3.1: Historian Writes the Evolution Section & Human-Read Marking

As a researcher,
I want each Cluster Dossier's Evolution history written by a role confined to exactly that section, and to mark representative papers as I actually read them,
So that the dossier is trustworthy history, not frontier speculation dressed as history — and my own reading is the thing that closes out a cluster, not the AI's draft.

**Acceptance Criteria:**

**Given** a Cluster Dossier is being drafted
**When** Historian writes it
**Then** it writes only the Evolution section (founding problem, phase shifts, abandoned branches) (FR-28)

**Given** Historian-authored content
**When** it appears anywhere outside the Evolution section of a dossier
**Then** this is rejected as a generation-window violation, logged as such (FR-28)

**Given** Historian attempts frontier-facing speculation within the Evolution section
**When** this is detected
**Then** it is logged as a generation-window violation attributed to the Historian role (FR-28)

**Given** a Cluster Dossier's representative papers
**When** I read one
**Then** I mark it `human_read` with a one-line reaction — this is the Deepen exit criterion for that dossier (FR-28, PRD §7.1)

**Given** a Cluster Dossier is missing a `human_read` flag on a representative paper
**When** Deepen-exit validation runs for that cluster
**Then** the cluster cannot be marked as having exited Deepen

### Story 3.2: Skeptic Attacks From a Fresh Context

As a researcher,
I want the Skeptic to critique my framings, clusterings, and gaps without ever proposing an alternative or seeing the authoring rationale,
So that its criticism is a genuine outside check, not the same drafting voice agreeing with itself.

**Acceptance Criteria:**

**Given** any framing, clustering, gap, or candidate artifact
**When** Skeptic is invoked against it
**Then** Skeptic may only critique — it never proposes an alternative (FR-27)

**Given** Skeptic is invoked
**When** its context window is assembled
**Then** it excludes the target artifact's authoring conversation — always a fresh context (FR-27)

**Given** Skeptic-authored output
**When** it is checked against constitutive-triad fields (FR-4) or the Candidate Direction type
**Then** no Skeptic output ever appears there as an accepted value (FR-27)

**Given** two consecutive Skeptic invocations against different artifacts in the same run
**When** I inspect their context windows
**Then** neither carries over drafting rationale from the other's target (FR-27)

### Story 3.3: Parallel Cluster Deepening with Sectional Repair

As a researcher,
I want to deepen multiple clusters in parallel without workers colliding, and stale dossiers repaired cheaply and only where they actually broke,
So that a Map-stage revision doesn't force an expensive full-rewrite of work I've already reviewed.

**Acceptance Criteria:**

**Given** depth budgets set at Map exit
**When** Deepen begins
**Then** one worker deepens per cluster, and each worker claims only its own cluster's sections (FR-3, AD-10)

**Given** two workers deepening different clusters
**When** they write concurrently
**Then** neither ever writes to a section claimed by the other live worker (AD-10)

**Given** a worker's session crashes mid-claim
**When** the run is reopened
**Then** its expired claims are reaped and released (AD-10, AD-15)

**Given** a Field Map revision stales a dependent Cluster Dossier
**When** repair runs
**Then** it executes a tiered check — Tier 0 deterministic dependency check first (no model call), Tier 1 cheap-model plausibility check only if Tier 0 doesn't resolve it, Tier 2 regenerates only the specific failing section IDs (FR-35)

**Given** a repair resolves entirely at Tier 0
**When** I inspect the event log
**Then** no model call was invoked for that repair (FR-35)

**Given** a dossier section a human has touched
**When** repair proposes a fix that would affect it
**Then** it produces a proposed diff for review rather than overwriting the human-touched span (FR-35, FR-12, AD-16)

## Epic 4: Synthesis & Gap Register — the MVP Terminal Deliverable

A researcher completes Synthesize and Locate, reaching an accepted Gap Register — the actual v1 success point.

### Story 4.1: Landscape Synthesis at Minimal-Profile Depth

As a researcher,
I want a cross-cluster solved/open table where every "open" claim carries evidence of its absence,
So that I don't mistake "nobody happened to cite this" for an actual gap in the field.

**Acceptance Criteria:**

**Given** accepted Cluster Dossiers
**When** Synthesize drafts the Landscape Synthesis
**Then** it produces a solved/open table at minimal-profile depth — the full competing-approaches matrix is out of MVP scope (PRD §7.1)

**Given** a claim marked "open" in the table
**When** I inspect it
**Then** it carries evidence of its absence, not just an absence of a citation (PRD Glossary — Landscape Synthesis)

**Given** the Landscape Synthesis reaches accepted
**When** I inspect its summary
**Then** it was regenerated at acceptance per the context loading contract (FR-33)

### Story 4.2: Gap Register and the Gap-Meaningfulness Write-Guard

As a researcher,
I want every gap to explain why it exists, and to be the only one who can mark a gap as meaningful to me,
So that the system can't quietly decide, on my behalf, which gaps actually matter.

**Acceptance Criteria:**

**Given** a candidate gap identified during Locate
**When** the Gap Register drafts it
**Then** it includes a mandatory explanation of why the gap exists, not just its absence from the record (PRD Glossary — Gap Register)

**Given** the `meaningful_to_me` field on a Gap Register entry
**When** any AI role attempts to write it
**Then** the write is refused at the storage layer with no trusted-mode override — this is the gap-meaningfulness leg of the constitutive triad (FR-4, FR-31)

**Given** a micro-probe was run as evidence for one Gap Register field
**When** its result is recorded
**Then** it is admitted as evidence and produces no artifacts of its own beyond that one field (PRD Glossary — Micro-probe)

**Given** the Gap Register reaches accepted
**When** I check its exit criteria
**Then** every minimal-profile section — including `why_does_this_gap_exist` and the human `meaningful_to_me` mark — is accepted (FR-11, FR-16)

### Story 4.3: Reaching the MVP Terminal — Generation-Window Enforcement Proven

As a researcher,
I want it to be mechanically impossible for the system to draft a candidate direction before my Gap Register is accepted,
So that the terminal deliverable I actually receive is landscape evidence, never a premature pitch.

**Acceptance Criteria:**

**Given** the run-level Gap Register has not yet been accepted
**When** any attempt is made to create a Candidate Direction artifact
**Then** the chokepoint refuses it (FR-46)

**Given** a generation-window violation is refused
**When** I inspect the run
**Then** the refused content is quarantined to `premature_ideas/`, never discarded and never leaked into a legitimate artifact (FR-46, AD-9)

**Given** the Gap Register is accepted
**When** I compare its acceptance timestamp against any `premature_ideas/` entries in the run
**Then** no Candidate Direction artifact anywhere in the run has a `created` timestamp earlier than this acceptance (FR-46)

**Given** the Gap Register reaches accepted
**When** I check the run's terminal state
**Then** the run is recognized as having reached MVP's terminal deliverable — Decided remains unreachable by construction since Propose/Decide don't exist yet, but the run may still continue to Dormant or another off-ramp per Epic 5 (PRD §7.1, SPEC CAP-1/CAP-5)

## Epic 5: Loop-backs, Waivers & Off-Ramps

A researcher's investigation rarely goes in a straight line — this epic delivers the non-linear paths through a run.

### Story 5.1: Defined Loop-Backs with Mandatory Cause Annotations

As a researcher,
I want to loop back to an earlier state when new evidence contradicts my framing, with a one-line cause recorded,
So that the system never silently presses forward past something that should have changed my mind.

**Acceptance Criteria:**

**Given** I'm in Deepen, Synthesize, or Locate
**When** I trigger one of the defined backward transitions (Deepen→Frame, Synthesize→Map, Locate→Deepen, Locate→Map)
**Then** the transition is accepted and logged as a `state_transition` event (FR-1)

**Given** I attempt a backward transition
**When** I don't supply a cause annotation
**Then** the transition is refused until I provide one (FR-1)

**Given** a backward transition with its cause annotation
**When** I inspect the event log
**Then** the cause is stored directly on the `state_transition` event, not merely implied by adjacent events (FR-1)

**Given** a backward transition not in the defined set (an arbitrary jump)
**When** I attempt it
**Then** it is refused (FR-1)

**Given** any state
**When** I transition directly to Dissolved or Dormant
**Then** there is no requirement to have passed through all six states first (FR-1, FR-7)

### Story 5.2: Gate-Loosening by Researcher Approval

As a researcher,
I want the system to be able to propose relaxing a review gate to a notification based on my own editing history, but never actually loosen it without my explicit approval,
So that trust is earned incrementally and never assumed on my behalf.

**Acceptance Criteria:**

**Given** a non-constitutive review gate
**When** the system has aggregated evidence from my own edit history
**Then** it may propose collapsing that gate into a notification (FR-5)

**Given** such a proposal
**When** it's presented to me
**Then** it cites the specific aggregated statistic that motivated it (FR-5)

**Given** the proposal
**When** I have not yet approved it
**Then** the gate remains at its current strictness (FR-5)

**Given** I approve a gate-loosening proposal
**When** the approval is recorded
**Then** it appears as a discrete approval event in the log — no gate ever loosens without one (FR-5)

**Given** the constitutive-triad fields
**When** a gate-loosening proposal targets them
**Then** it is rejected outright — no trusted-mode override exists for the triad regardless of approval (FR-4)

### Story 5.3: Dissolution — A Fast, Documented Off-Ramp

As a researcher,
I want dissolving a bad intuition to be a fast, first-class, well-documented outcome the system doesn't try to talk me out of,
So that a dead end costs me days, not months.

**Acceptance Criteria:**

**Given** my intuition doesn't survive scrutiny at any state
**When** I choose to dissolve the run
**Then** the system produces a complete Dissolution Memo — what the intuition was, what dissolved it, what I learned, revival conditions, and any salvaged fragments spun off as new Intuition Notes (FR-7)

**Given** a run reaches Dissolved
**When** I inspect its standing
**Then** it has the same standing as reaching Decided or an accepted Gap Register — never a lesser "abandoned" status (FR-7)

**Given** the Dissolution Memo
**When** I inspect its `elicited_from`/`depends_on` fields
**Then** they trace back to the specific evidence that dissolved the intuition (FR-9)

### Story 5.4: Dormancy and the Monitoring Sweep

As a researcher,
I want to park a run with explicit revival conditions and have it checked at the start of my next session, not by a background process I can't see,
So that parking a run never means losing track of it.

**Acceptance Criteria:**

**Given** a run I want to park
**When** I mark it Dormant
**Then** I record explicit revival conditions and it continues to receive monitoring updates (FR-7)

**Given** `kagami monitor` executes
**When** it runs
**Then** it executes as a sweep at run open / skill activation — never a background daemon (FR-7, AD-24)

**Given** a staling alert fires for a Dormant run
**When** the next session opens
**Then** the run is reopened at the affected state at that session, never asynchronously (FR-7, AD-24)

**Given** the post-decision staleness mechanism (FR-8, v2/non-preclusion)
**When** I inspect the sweep's design
**Then** it is generic enough to be reused unchanged once Decided becomes reachable in v2, with no rework required at that point (FR-8, AD-24)

**Given** a genuinely new intuition unrelated to a Dormant run
**When** I start it
**Then** it always starts a new run — it may cite prior artifacts but never reuses the old run (FR-7)

## Epic 6: Run Observability & Trust Substrate

Everything logged since Epic 1 becomes actually useful here: a researcher (or future design owner) can verify, not just trust, what happened in a run.

### Story 6.1: Deterministic Per-Run Derived Metrics

As a researcher,
I want question economics, a token ledger, and a decision block computed deterministically at every gate,
So that the same event log always yields the same numbers — no LLM judgment involved in measuring my own run.

**Acceptance Criteria:**

**Given** a completed gate or terminal
**When** derived metrics are computed
**Then** question economics, a token ledger (including summary-sufficiency), an override profile, and a decision block are all produced by deterministic computation, never LLM judgment (FR-37)

**Given** the same event log
**When** metric computation is re-run
**Then** it always produces identical numbers (FR-37)

**Given** the provisional count shown at a gate
**When** I compare it to the derived metric
**Then** they match exactly (FR-37, FR-20)

**Given** the decision block's fields (candidate origins, unprimed-vs-final diff, provisional count, falsifiable claims as trace objects)
**When** I inspect them at MVP's Gap Register terminal
**Then** the fields applicable to MVP (unprimed-vs-final diff at Frame, provisional count) are populated; Decide-only fields remain empty since that state doesn't exist yet (FR-37, PRD §8)

### Story 6.2: Mechanical Charter-Violation Audit

As a researcher,
I want to check, mechanically and after the fact, whether any role ever acted outside its own contract,
So that charter enforcement is a checkable fact against the log, not something I have to trust by reputation.

**Acceptance Criteria:**

**Given** any LLM call in the run
**When** I inspect its event log entry
**Then** it carries a non-null role tag (FR-29)

**Given** the event log for a completed run
**When** I run a charter-violation audit against it
**Then** it detects, without re-reading transcripts: Scout producing interpretation, Skeptic proposing an alternative, Historian speculating outside Evolution, or any non-Scout call touching the raw corpus (FR-29, FR-25, FR-27, FR-28)

**Given** no charter violations occurred
**When** the audit runs
**Then** it returns zero matches (FR-29)

**Given** a charter violation did occur
**When** the audit runs
**Then** it surfaces the specific responsible event(s), not just a pass/fail flag (FR-29)

### Story 6.3: Trace Privacy — Local-First, Opt-In, Content-Stripped

As a researcher,
I want my run data to stay on my machine by default, and any future sharing to be opt-in and stripped of content,
So that I never have to trade privacy for the system's own self-improvement.

**Acceptance Criteria:**

**Given** the default configuration
**When** I complete a run
**Then** no event data leaves my local store — sharing is off by default (FR-39, NFR4)

**Given** I explicitly opt in to sharing
**When** a shared payload is generated
**Then** it contains only event shapes, counts, and classes — never verbatim question text, artifact content, or paper titles/authors (FR-39)

**Given** any design-analytics feature
**When** I use it as a single researcher
**Then** it functions fully without requiring me to share anything (NFR4)

**Given** the privacy flag in `config.yaml`
**When** I inspect it
**Then** it defaults to off and can only be changed by my own explicit edit (FR-39, AD-12)

## Epic 7: Driver & Harness Shell

Epics 1–6 built a deterministic core with no epic covering the harness that drives it. This epic builds the Interviewer skill, the role agent definitions, and the two driver-side guarantees (refusal-retry ceiling, `llm_call` reporting) that surfaced only once the harness was scoped for implementation — and ends with a golden toy-run dogfooding pass whose verdict gates real use.

### Story 7.1: Walking Skeleton — the Interviewer Drives One Real Traversal

As a researcher,
I want the harness itself — `skills/kagami-discovery/SKILL.md` plus agent definitions — to actually exist and drive a run through Frame,
So that the deterministic core built in Epics 1–6 is something I can actually use, not just something that passes its own test suite.

**Acceptance Criteria:**

**Given** the plugin is installed
**When** I invoke the Interviewer skill
**Then** it resolves `CLAUDE_PLUGIN_ROOT` and opens a run via `kagami run open` without any direct `Write`/`Edit`/`Bash` touching the output root (AD-1, AD-23)

**Given** a live Claude Code session with the plugin's PreToolUse hook active
**When** the skill's own conversational flow is driven end-to-end, including any point where it might be tempted to write output-root content directly
**Then** the hook denies any such attempt — verified in a real session, not only against recorded payloads, since AD-25's suite covers `kagami/` and `hooks/` only, never the skill itself (AD-2, AD-27)

**Given** the hook script itself fails to start (bad `CLAUDE_PLUGIN_ROOT`, `uv` cold-start error)
**When** a `Write`/`Edit`/`Bash` call targets the output root during that failure
**Then** the failure mode is observed and documented — it must not silently fail open (AD-2, AD-27)

**Given** the walking skeleton drives a run
**When** it completes a full Frame traversal (Intuition Note through accepted Inquiry Frame)
**Then** every mechanical guarantee Story 1.7 already proved against a scripted driver is exercised for the first time through the real harness (AD-25 boundary, AD-27)

**Given** this story's Definition of Done
**When** it is reviewed
**Then** it includes a recorded Claude Code session transcript demonstrating the full traversal, attached to the PR — the AD-27 verification path, since no CI suite substitutes for it here

### Story 7.2: `llm_call` Reporting and Launch-Time Model Resolution

As a researcher,
I want every model call my run makes to be reported and priced, and the model actually used for each role to come from my own config,
So that my token ledger reflects reality and I'm not silently locked into whatever model was hard-coded at build time.

**Acceptance Criteria:**

**Given** `schemas/dispatch.yaml`
**When** I inspect it
**Then** it maps every operation class to a tier — deterministic / deterministic-ML / cheap-model / frontier-model (AD-12)

**Given** `config.yaml`'s tier→model map
**When** the skill launches a role's subagent
**Then** the model is resolved at launch time from `dispatch.yaml` + `config.yaml` — no call site names a concrete model (AD-12)

**Given** the harness makes a model call
**When** the call returns
**Then** the harness calls `kagami report llm-call` immediately afterward with `role`, `operation_class`, `model_tier`, token counts, cache-hit, and a harness-minted `--call-id` (FR-49, AD-26)

**Given** a `--call-id` that already appears among the run's recent `llm_call` events
**When** it is reported again
**Then** the chokepoint refuses the duplicate — the ledger is never double-inflated (AD-26)

**Given** a model call the harness never reports
**When** I inspect the token ledger
**Then** that call is invisible to it — a logged AD-11 honest-gap, not a silent correction (FR-49, AD-11)

**Given** a completed gate
**When** I inspect the decision block
**Then** it includes a warning field when the cumulative token ledger crosses my configured soft limit, and never blocks progress regardless of the limit (FR-37, AD-26)

### Story 7.3: Role Agent Definitions with Read-Set-Compliant Context

As a researcher,
I want each role — Scout, Cartographer, Historian, Skeptic, worker — to actually exist as a Claude Code subagent restricted to its own charter and its own read set,
So that the role contracts Epics 2/3/6 already proved auditable are also the roles actually running my investigation.

**Acceptance Criteria:**

**Given** `agents/`
**When** I inspect it
**Then** Scout, Cartographer, Historian, Skeptic, and worker each exist as a subagent definition with role-restricted tools — only Scout's definition includes search tools (FR-25, AD-4)

**Given** a role's subagent is invoked
**When** its context is assembled
**Then** it is built from the read-set table already governing FR-15/FR-33/FR-34, not an ad hoc prompt (AD-4)

**Given** `kagami session open/close` and engagement tokens are deferred (AD-4's v1-driver amendment)
**When** a role writes content
**Then** it supplies a self-declared `--role` argument that must be one of the schema-registry-enumerated roles, refused otherwise — the same trust boundary as FR-49's telemetry role, no separate join key between the two (AD-4, AD-26)

**Given** the Skeptic role specifically
**When** it is invoked
**Then** its context excludes the target artifact's authoring conversation, matching FR-27's fresh-context requirement — now exercised through the real subagent rather than Story 3.2's test fixture

**Given** this story's Definition of Done
**When** it is reviewed
**Then** it includes a checklist review against each role's charter (AD-27) confirming no role's agent definition grants it a tool or context read outside its FR-25..29 contract

### Story 7.4: Safety Discipline — Refusal Ceiling and Provider Backoff

As a researcher,
I want the system to stop and tell me when it's stuck, rather than silently burning tokens retrying the same refused call, and I want a rate-limited provider to back off instead of ending my run,
So that a bug in the harness costs me a conversation, not a bill.

**Acceptance Criteria:**

**Given** the chokepoint's refusal counter
**When** the same `(entrypoint, target)` is refused identically past the configured ceiling
**Then** the next identical attempt receives `requires_researcher` instead of an ordinary refusal (FR-48, AD-26)

**Given** the refusal counter
**When** I inspect its implementation
**Then** it is derived from the tail of `events.jsonl` — no new store — and resets on any intervening non-refusal event for that same `(entrypoint, target)` tuple (AD-26)

**Given** a `requires_researcher` response
**When** it reaches the Interviewer
**Then** it is surfaced directly in-conversation — it never enters the Question Ledger or `kagami ask`'s queue, and carries no question-class key (AD-26, AD-8, AD-14)

**Given** a literature-provider adapter hits its documented rate limit (OpenAlex, Semantic Scholar, arXiv, or GitHub)
**When** the next request would exceed it
**Then** the adapter backs off and retries rather than surfacing a raw provider error to the researcher (NFR7, AD-7)

**Given** a sustained rate-limit condition
**When** backoff is exhausted
**Then** the failure is surfaced as a specific, named error — never a silent hang or an unbounded retry loop (NFR7)

### Story 7.5: The Golden Toy Run — Dogfooding as an Acceptance Test

As a researcher,
I want one fixed, repeatable toy investigation run end-to-end through the actual harness before I trust this system on real research,
So that I validate the mechanics — not the output quality — on a topic I already understand well enough to judge instantly.

**Acceptance Criteria:**

**Given** a fixed toy topic, small corpus scope, and pinned cheap-tier config (the golden toy-run protocol, AD-27)
**When** the run is driven start to finish through Frame→Map→Deepen→Synthesize→Locate
**Then** it reaches an accepted Gap Register through the real harness built in Stories 7.1–7.4, not a scripted driver

**Given** the completed toy run's event log
**When** it is inspected against the evaluation rubric fixed at this story's design time
**Then** it records: the refusal→correction pattern, never refusal→identical-retry (Story 7.4, AD-26); Question Ledger `consumed_by` coverage; the override profile from Story 5.2's gate-loosening mechanism; `premature_ideas/` volume (AD-9); and a check for known clusters the Scout/Cartographer pairing missed — the embedding-index revisit trigger recorded in the Architecture Spine's Deferred section

**Given** the same toy run
**When** `kagami metrics` is run at each gate it passed
**Then** the token ledger and decision block (Story 6.1, Story 7.2) accurately account for every reported `llm_call`, with no reported call missing and no duplicate-inflated total

**Given** this story's Definition of Done
**When** it is reviewed
**Then** it includes the recorded session transcript, the completed rubric, and an explicit pass/fail verdict on whether the harness is ready for a real (non-toy) investigation — this verdict, not story completion, is Epic 7's actual exit criterion
