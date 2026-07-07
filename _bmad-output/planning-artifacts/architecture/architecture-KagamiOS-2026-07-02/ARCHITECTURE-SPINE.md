---
name: 'KagamiOS v1'
type: architecture-spine
purpose: build-substrate
altitude: feature
paradigm: 'ports-and-adapters (hexagonal) deterministic core, hosted as a Claude Code plugin — "gatekeeper kernel": the LLM harness drives, the core refuses'
scope: 'KagamiOS v1 MVP — states Frame→Map→Deepen→Synthesize→Locate; terminal deliverable is an accepted Gap Register; Propose/Decide deferred to v2 but must not be precluded'
status: final
created: '2026-07-02'
updated: '2026-07-06'
binds: ['FR-1..FR-7', 'FR-9..FR-37', 'FR-39', 'FR-45', 'FR-46', 'FR-48', 'FR-49', 'FR-50', 'FR-51', 'FR-52', 'FR-53', 'FR-54', 'FR-55', 'FR-56']
binds_non_preclusion: ['FR-8', 'FR-42', 'FR-43', 'FR-44', 'FR-47']
deferred_frs: ['FR-38', 'FR-40', 'FR-41']
sources: ['_bmad-output/planning-artifacts/prds/prd-KagamiOS-2026-07-02/prd.md', '_bmad-output/planning-artifacts/change-signal-scout-probes-2026-07-04.md', '_bmad-output/planning-artifacts/change-signal-paper-content-2026-07-06.md', 'archive/docs-spec/ (archived — historical/audit material only, superseded by this Architecture Spine and its companion SPEC/PRD)']
companions: ['docs/future-scout-redesign.md (design notebook only — NOT an implementation source; see its own status header)']
---

# Architecture Spine — KagamiOS v1

## Design Paradigm

**Hexagonal (ports-and-adapters) deterministic core, hosted as a Claude Code plugin.** The core (`kagami/`) is a pure-Python library exposing ports; every volatile dependency is an adapter behind a port: literature providers, the LLM harness itself (see AD-22), the elicitation surface, the filesystem store. Control flow is inverted relative to a classic app — the LLM harness (Claude Code skill + subagents) drives, and the core's job is to **refuse illegal outcomes and record everything**, not to orchestrate. Nickname used throughout: *gatekeeper kernel*.

Layer map:

- `kagami/store/` — artifact store, versioning, write-guards, staleness, section identity, entity-registry identity (the gate)
- `kagami/kernel/` — derived state, frontier, triage, question batching, generation windows, repair tiers (pure functions over store state)
- `kagami/events/` — event log append + derived metrics
- `kagami/corpus/` — paper cards, provider port + adapters (OpenAlex, Semantic Scholar, arXiv, GitHub); main writer of the entity registry
- `kagami/briefs/` — read-set-compliant context bundle rendering per (role, state, target)
- `skills/`, `agents/`, `hooks/` — the harness-facing shell; never contains state or rules

## Invariants & Rules

### AD-1 — Runtime shape: Claude Code plugin with a deterministic gatekeeper core `[ADOPTED]`

- **Binds:** all
- **Prevents:** enforcement-by-prompt-convention; a standalone app that abandons the BMAD ecosystem
- **Rule:** KagamiOS ships as a Claude Code plugin, co-installable with BMAD. All mechanical guarantees (write-guards, generation windows, ASK batching, versioning, event logging, staleness, derived state) are implemented in the Python core, never in prompts. Claude Code is the driver, never the kernel: no rule may exist only in a SKILL.md. **v1-driver amendment (2026-07-03):** this rule governs *guarantees* — outcomes the core can enforce by refusing an illegal state. AD-26(b)'s reporting *obligation* (the harness must call `kagami report llm-call` after each model invocation) is not such a guarantee — the core cannot compel an external call to happen, only make an unreported one visibly uncredited (AD-11's honest-gap register). This is the same accepted category as "frontier obedience" and "main-thread token accounting incomplete," not a new exception to this AD.

### AD-2 — The chokepoint: `kagami` entrypoints are the only sanctioned mutation path, enforced by default-deny `[ADOPTED]`

- **Binds:** all state (artifacts, ledger, event log, corpus, registry, profile, manifest)
- **Prevents:** two mutation paths with different validation; unvalidated state reaching the store; hook evasion via unenumerated Bash write vectors (`cp`, `sed -i`, `python -c`, heredocs, …)
- **Rule:** Every AI-originated state change goes through a `kagami` CLI entrypoint. The PreToolUse hook is **default-deny for any tool invocation whose arguments reference the output root** — `Write`, `Edit`, `NotebookEdit`, `Bash`, **and `Read`** alike — with a single allow-pattern: the `kagami` invocation form (AD-23). Never an enumerated blocklist of write patterns. Each entrypoint validates against the schema registry, enforces window/guard/claim rules, appends its event, and echoes one-line JSON — the memlog.py contract, generalized. **Text correction (2026-07-06, FR-56):** `hooks/hooks.json`'s matcher shipped as `Write|Edit|NotebookEdit|Bash` only — omitting `Read` — so the "any tool invocation" claim above was false from Epic 1 through Epic 9; every role routed around the missing FR-55 read path by reading the output root directly with `Read` instead. FR-56 (`change-signal-paper-content-2026-07-06.md`) closes the gap by adding `Read` to the matcher; this rule's text is corrected here to state the guarantee this AD always intended, now that it is true. Amend, never renumber — this is a text fix to an existing rule, not a new AD.

### AD-3 — Provenance: data plane vs. control plane; out-of-band data-plane changes are candidate human edits

- **Binds:** store, provenance (FR-12, FR-19), `kagami scan`
- **Prevents:** AI writes laundered into human provenance; hand/git edits to control state accepted as intent; asking questions an edit already answered
- **Rule:** AD-3 applies only to **data-plane files** — `current.md` (the sole human edit surface, AD-6) and other declared human surfaces. `meta.yaml`, `manifest.yaml`, `events.jsonl`, `queue/`, the ledger record store, and lock/lease files are **control-plane: chokepoint-exclusive** — an out-of-band change to them is corruption, not intent: detected by hash at next entrypoint, refused as input, reported, and rebuilt from data-plane ground truth where derivable (P1). A data-plane change detected by `kagami scan` is a *candidate* human edit: it is attributed human when it occurred outside an active AI turn (turn boundaries recorded by hook events); a change appearing mid-AI-turn is quarantined `suspect` and flips no provenance and resolves no unknowns until the researcher confirms it with one keystroke at the next gate. Known accepted edge: git operations and formatters run by the researcher acquire human attribution — logged, revisitable.

### AD-4 — Roles are subagents with registered sessions; the orchestrating skill *is* the Interviewer

- **Binds:** FR-25..FR-29, FR-33/34 (read sets), FR-27 (Skeptic freshness)
- **Prevents:** role charters as vibes; context leakage between roles; content writes with fabricated role attribution; briefs keyed inconsistently with the spec's read-set table
- **Rule:** Named roles — Scout, Cartographer, Historian, Skeptic — plus a **`worker` drafting role parameterized by (state, target)** (dossier non-Evolution sections, Synthesis, Gap Register drafts) are subagent definitions with role-restricted tools (only Scout gets search tools). Role sessions are **registered with the chokepoint** via hook-driven `kagami session open/close` (a control-plane session table); `kagami brief <role> <state> <target>` renders the read-set-compliant context bundle — the read-set table in `docs-spec/07_runtime.md` §3 is the normative content of the brief renderer — and mints a **single-use engagement token** bound to (role, target). An artifact content submission must present a token whose session is open, role-matching, and unexpired, else refused. The main thread is the Interviewer: it schedules and asks; content it writes without a token is refused. Residual, accepted as detect-and-audit (AD-11): a live role citing its own valid token for off-charter content. **v1-driver amendment (2026-07-03):** `kagami session open/close` and single-use engagement tokens are deferred — Epic 7's walking skeleton does not implement them. Interim: content-write role attribution and `llm_call` telemetry role attribution collapse to **the same single self-declared `--role` argument** — a content submission and its corresponding `kagami report llm-call` (AD-26b) both carry `--role` from the same trust boundary, with no separate join key between them and no cryptographic binding to a session, because there is no session to bind to. `--role` must be one of the schema-registry-enumerated roles or the call is refused (a floor this AD already had); nothing above that floor is verified. This is a real weakening of this AD's original token-gated write path, recorded as a new AD-11 honest-gap entry, not silently accepted. Revisit trigger: a role writing off-charter content that a token check would have caught, surfaced during the Epic 7 toy run (AD-27), promotes session/token implementation from deferred to required.

### AD-5 — Core is a standalone-capable library; harness bindings are adapters `[ADOPTED]`

- **Binds:** `kagami/` package layout, all harness-facing code
- **Prevents:** core logic importing anything Claude-Code-specific; a future CLI/runtime requiring a rewrite
- **Rule:** `kagami/` imports no harness API. The skill, hooks, and agent definitions call the core only through its CLI entrypoints. A future non-plugin runtime is an adapter over the same entrypoints. The standing proof is AD-25's scripted-driver test suite.

### AD-6 — Store layout: explicit immutable version files; `current.md` is the only human edit surface `[ADOPTED]`

- **Binds:** artifact store, FR-9..FR-14, FR-32, FR-33
- **Prevents:** version semantics depending on git state; history reconstruction from diffs; in-place human edits destroying pinned version content; summary/content drift
- **Rule:** Each artifact is a directory: immutable `vN.md` files (the chokepoint never rewrites an existing one; no one edits them), a mutable **`current.md`** — the materialized copy of the current accepted version and the *only* file humans edit — and `meta.yaml` (current pointer, status, pins, claims, section registry, content hashes; control-plane per AD-3). `kagami scan` diffs `current.md` against the latest version's recorded hash, mints `v(N+1).md` with touched spans `human-confirmed`, and advances the pointer — so integer-compare staleness fires on human edits exactly as on AI ones. Versions are monotonic integers owned by the chokepoint under the run lock (AD-15). The 5–10 line `summary` is regenerated **only at acceptance** and stored as part of that version (`kagami accept` requires it as validated input — AD-22); a full-text pull is a distinct logged event from a summary read.

### AD-7 — Literature providers behind one port; default is configuration `[ADOPTED]`

- **Binds:** `kagami/corpus/`, Scout; FR-50, FR-51
- **Prevents:** single-provider coupling; provider choice baked into call sites (OpenAlex's Feb-2026 pricing change is the live proof); a citation-graph contract that only ever grows one direction
- **Rule:** One `LiteratureProvider` port (search, paper metadata, citation graph). OpenAlex and Semantic Scholar are peer adapters; arXiv and GitHub are complementary-source adapters. No call site names a provider; the default comes from `config.yaml`. Provider credentials come from **environment variables only, never `config.yaml`** (which lives in the user's project and may be committed). **Scout-probes amendment (2026-07-04, FR-51):** `citation_graph(canonical_key)` returns `{"canonical_key", "cited_by": [...], "references": [...]}` — both directions, always present as keys even when empty. Each adapter fills what its underlying API actually offers; arXiv and GitHub legitimately return empty lists for one or both directions today — an exposed provider bias, not a bug to mask. This is an amendment to the port's return shape, not a new port method; `kagami/kernel/scout.py`'s new `corpus_expand` operation (FR-50) is its first caller — that operation itself needs no new AD, since it is `search_corpus`'s role-gate (AD-2) and event-logging (AD-11) pattern applied to a second Scout action, not a new mechanism.

### AD-8 — Single ASK scheduler, batch ≤ 5, enforced at the ledger

- **Binds:** FR-18, FR-21..FR-23, Question Ledger
- **Prevents:** parallel workers each interrogating the researcher; oversized batches
- **Rule:** `kagami ask` is the only entrypoint that creates researcher-facing questions. Worker-emitted unknowns land in `queue/`, never directly in front of the researcher. `kagami ask emit` refuses a batch over 5 and requires target + leverage class per question (E6 unprimed pair excepted); `kagami ask answer` writes the ledger entry (AD-17) and timestamps; `kagami ask revise` is the E5 revision path.

### AD-9 — Generation windows enforced by store refusal, keyed to per-cluster derived state

- **Binds:** FR-24, FR-46; v2 non-preclusion of FR-42/43/44
- **Prevents:** direction-shaped content before an accepted Gap Register; AI framing *drafted* before the unprimed answer is recorded; run-level window checks blocking legal Deepen parallelism
- **Rule:** The chokepoint refuses to create an artifact type before its generation-window state per the registry's window table (which includes Propose/Decide types from day one). **Windows key off the per-cluster derived state (AD-20's pure function), except the Candidate-Direction window, which keys off run-level Gap Register acceptance** — a dossier for cluster 1 while cluster 2 is still mapping is legal. Refused direction-shaped content is quarantined to `premature_ideas/`, never discarded. The Frame draft artifact cannot be written until the Frame unprimed ledger entry exists — *artifact creation* ordering is impossible to violate; *conversational display* before the ledger entry is detect-and-audit (AD-11's honest-gap list).

### AD-10 — Parallel writers claim sections; claims are lease-bound

- **Binds:** FR-11, Deepen parallelism (FR-3, one worker per cluster)
- **Prevents:** two workers writing the same section; merge ambiguity; crashed workers wedging sections forever
- **Rule:** A write names the section IDs (AD-19) it targets; `meta.yaml` records active claims; the chokepoint — under the run lock (AD-15) — rejects a write to a section claimed by another live worker. A claim carries the session lease id (AD-15) and expires with it; expired claims are reaped at run open. Sequential execution is a valid degraded mode — parallelism is an optimization, never a correctness requirement.

### AD-11 — Event log: append-only JSONL, written only by the core; the honest-gap register

- **Binds:** FR-29, FR-36..FR-37, FR-5
- **Prevents:** runtime behavior reading telemetry; unlogged mutations; overclaimed guarantees
- **Rule:** Every chokepoint entrypoint appends its event (one JSON object per line, single `O_APPEND` write, `family` per the spec's ten families) as part of the same locked operation. An `llm_call` event carries `role`, `operation_class`, `model_tier`, token counts, and cache-hit — without operation-class tagging the layer-2 token ledger is uncomputable later. The core exposes no read API over `events.jsonl`; the invariant "a run with its trace deleted behaves identically" is a standing test (AD-25) — meaning no run **behavior** (state transitions, gate outcomes, content generation) may branch on log-derived data. `kagami metrics` (FR-37) is the one place permitted to read the raw log, and it does so routinely at every gate to compute question economics, the token ledger, and the decision block — this is reporting, not behavior, so it runs unconditionally and is not the exception. **The one sanctioned exception is a behavior-altering read**: FR-5 gate-loosening, which consumes only `kagami metrics`' derived aggregates (never raw events) and only takes effect on researcher approval. AD-26(c)'s gate-time budget warning is `kagami metrics` reporting, not a second exception. **Honest-gap register (accepted, detect-and-audit, logged not hidden):** main-thread token/prompt accounting incomplete; frontier obedience; conversational display before ledger entry (AD-9); off-charter content under a valid engagement token (AD-4); harness-side reads of the log file by subagents; **role attribution is harness-self-reported and trusted, not mechanically token-gated, for v1-driver** — AD-4's own v1-driver amendment defers the session/engagement-token machinery; AD-26(b) supplies the interim self-declared `--role` mechanism; **driver-side (`skills/`, `agents/`) behavior is verified by transcript and checklist, not by the CLI-boundary test suite** — AD-25 covers `kagami/` and `hooks/` only (AD-27).

### AD-12 — Dispatch is per *operation class*; models, tiers, and researcher-owned settings live in config

- **Binds:** agent definitions, dispatch decisions, `config.yaml`, `schemas/dispatch.yaml`
- **Prevents:** hard-coded model names rotting; per-role flattening of the spec's operation→tier table; researcher-owned choices requiring code changes
- **Rule:** The **static, human-maintained dispatch table** (`schemas/dispatch.yaml`, versioned with the registry) maps operation classes to tiers: deterministic / deterministic-ML / cheap-model / frontier-model, per `docs-spec/07_runtime.md` §5. `config.yaml` maps tiers to concrete models. Subagent `model` frontmatter is static, so the skill resolves the model **at launch time** from config + dispatch table. Default literature provider, output roots, and the privacy/sharing flag (default **off**, FR-39) are also `config.yaml`. Code refers to operation classes, tiers, and ports — never to concrete model or provider names.

### AD-13 — User data lives in the user's project, never in the plugin install

- **Binds:** all stores
- **Prevents:** researcher-owned data trapped in a plugin directory; plugin upgrades touching user state
- **Rule:** Runs (`runs/<run-id>/`), corpus cache, entity registry, and researcher profile live under the configurable output root in the user's project. The plugin directory contains only code, schemas, skills, agents, hooks. Deleting the plugin loses no user data; deleting the output root loses no plugin.

### AD-14 — Non-preclusion is a schema-registry obligation — including the infrastructure stores and observability commitments

- **Binds:** schema registry, state-machine enum, window table, ledger schema, event schema; FR-47 non-preclusion
- **Prevents:** v1 shortcuts that make Propose/Decide — or the v2+ Design Audit loop — a breaking change
- **Rule:** The state enum, artifact schema registry, and generation-window table ship complete (all six states + Decide, all eleven artifact types) from v1; the registry also governs the **infrastructure stores** (ledger entry, run manifest, event families). Three things are locked from run 1 because they cannot be retrofitted: (a) the stable **question-class key** (leverage × state × form) in every ledger entry; (b) **run-id outcome-join** fields for late-arriving quality data; (c) the **`audit_exempt: permanent`** flag on constitutive-triad fields and the two E6 unprimed question classes (FR-47). MVP omits the *flows* for Propose/Decide, not their types.

### AD-15 — Chokepoint serialization, single-writer lease, and crash consistency

- **Binds:** every mutating entrypoint; all locks; FR-32 (ID minting)
- **Prevents:** claim-check races; duplicate version integers; lost `meta.yaml` updates; torn JSONL lines; two sessions corrupting one run; wedged state after a crash
- **Rule:** Every mutating entrypoint acquires an exclusive advisory lock (`flock`, bounded wait, `{"ok": false, "error": "busy"}` on timeout) on `runs/<run-id>/.lock` for its full read-validate-write-append span; version integers, IDs, and claims are decided only under it. **One writer session per run:** `kagami run open` takes a lease file (holder id + heartbeat); a second session gets read-only access or must explicitly break a stale lease. Fixed write order per operation — version file → meta → event — all via temp-file + fsync + atomic rename; JSONL appends are single `write()` calls under `O_APPEND`. `kagami run open` runs a consistency repair that detects and completes or rolls back torn operations and reaps expired claims. Cross-run stores carry their own locks (AD-18). Store mutation is serial by construction; parallelism (AD-10) is parallel *LLM work*.

### AD-16 — Scan-before-write: human edits always win over queued AI writes

- **Binds:** every artifact-mutating entrypoint; FR-12, FR-19; `docs-spec/07_runtime.md` §2
- **Prevents:** a queued AI regeneration silently superseding an unscanned human edit — the highest-bandwidth elicitation channel destroyed by a race
- **Rule:** Inside the same locked operation (AD-15), every entrypoint targeting an artifact runs the `current.md` hash check *first*. Detected human edits are processed first (spans → `human-confirmed`, unknowns resolved, `v(N+1)` minted per AD-6); then the AI write is re-validated, and if it overlaps any human-confirmed span it is **refused and re-emitted as a proposed-diff artifact** — never applied. "Human edits always win" is a store refusal, not a scheduler courtesy.

### AD-17 — The Question Ledger is a schema-governed record store; `ledger.md` is a render

- **Binds:** FR-18, FR-22, AD-8; `docs-spec/05_elicitation.md` §5
- **Prevents:** a prose ledger the staleness engine can't compute over; append-only colliding with `consumed_by`/`superseded_by` stamping; researcher hand-edits gutting the trace
- **Rule:** Ledger entries are structured records (`ledger/q-NNN.yaml`) validated against the registry's ledger schema, field-for-field per 05 §5 including the question-class key (AD-14). Entry *versions* are immutable (`q-NNN@v2` on revision via `kagami ask revise`); `consumed_by` stamps live in a mutable per-entry meta section, mirroring `meta.yaml`. `elicited_from` pins `q-id@version`, so answer revisions propagate staleness through the standard integer compare. `ledger.md` is a derived, regenerable human view — control-plane, not an edit surface.

### AD-18 — Cross-run store contracts

- **Binds:** `corpus/`, `registry/`, `profile/`; FR-14, FR-32
- **Prevents:** pin-consuming code meeting a versionless profile; entity/paper ID collisions across runs; unmigratable cache shapes
- **Rule:** (a) `profile/researcher-profile/` is a normal AD-6 artifact directory (versions, `current.md`, `meta.yaml`); everything pinning the profile pins a version. (b) `corpus/` and `registry/` are **derived and unversioned** with **content-derived IDs** — `ppr-` from a canonical bibliographic key (DOI/arXiv-ID hash), `ent-` from a canonical entity key — so concurrent minting converges instead of colliding; every card/record carries `schema_version`. (c) Each cross-run store has its own lock (AD-15 mechanics). Identity semantics live in `kagami/store/`; `kagami/corpus/` is the registry's main writer.

### AD-19 — Section identity: opaque, minted once, registered, never content-derived

- **Binds:** FR-11, AD-10 claims, repair, briefs, trace addressing
- **Prevents:** heading-slug IDs orphaning claims, per-section status, and pinned deps on every rename
- **Rule:** Section IDs are opaque (`sec-` + chokepoint-minted suffix), created once at section creation, registered in `meta.yaml` (`sections: [{id, title}]`), and never derived from content or headings. A write must reference existing IDs or explicitly create/retire IDs — retirement is a logged event and releases claims; a version that silently drops a registered live section is refused. Titles are mutable labels; identity is the ID, and it survives regeneration.

### AD-20 — Derived state is the kernel's pure function; the manifest is a cache plus the non-derivable facts

- **Binds:** FR-3, AD-9 guards, `manifest.yaml`
- **Prevents:** two authorities for the input to window/gate refusals; guard decisions read from a stale or hand-damaged file
- **Rule:** Per-cluster derived state is *definitionally* `kagami/kernel/`'s pure function over store + ledger. `manifest.yaml`'s state fields are a cache, recomputed by every mutating entrypoint and **never read for a guard decision** — guards call the function. The manifest's authoritative contents are only what is not derivable: run id, rooting Intuition Note reference, depth budgets, and monitoring config (per `docs-spec/04_artifacts.md` §3).

### AD-21 — Repair pipeline: tiered, frontier-triggered, sectional

- **Binds:** FR-13, FR-35; `docs-spec/07_runtime.md` §4
- **Prevents:** whole-artifact regeneration on every staleness mark; repair invented differently per unit; silent overwrites of human spans
- **Rule:** Repair runs only when the frontier needs the stale artifact (never eagerly): Tier 0 — deterministic dependency check (no model call); Tier 1 — cheap-model plausibility check per failing edge (via AD-22's protocol); Tier 2 — regenerate only the failing section IDs. Human-touched spans get proposed diffs only (AD-16). Tier assignment is dispatch-table data (AD-12).

### AD-22 — Core operations needing model output use one protocol: validated input or `needs_llm` work item

- **Binds:** `kagami accept` (summaries), repair Tier 1, paper-card extraction; the "LLM harness as adapter" port
- **Prevents:** three units inventing three different core↔model seams
- **Rule:** Chokepoint entrypoints never invoke models. An operation requiring model output either (a) demands it as a schema-validated input argument (`kagami accept` refuses without a conforming summary for that version), or (b) returns a typed `needs_llm` work item in its JSON echo — operation class, brief reference, expected schema — which the harness fulfills and submits through a validating entrypoint. No third pattern.

### AD-23 — Installation and schema migration

- **Binds:** every invocation; plugin upgrades; old runs
- **Prevents:** each entrypoint guessing how `kagami` resolves from an arbitrary cwd; an upgraded registry silently mutating old-schema runs
- **Rule:** The plugin ships a `pyproject.toml`; every invocation is `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami <cmd>` (hooks and the skill own resolving the plugin root); uv materializes dependencies on first run. Every write stamps `schema_registry_version` into `meta.yaml`/`manifest.yaml`; the chokepoint **refuses to mutate** a run written under a *newer* registry, and reads older-schema runs read-only via the versioned registry (FR-30). `kagami migrate` — human-invoked, logged, minting new versions, never editing `vN.md` in place — is the only path that rewrites old runs. **Text confirmation (2026-07-06, FR-55/FR-56):** this invocation form is the sole allow-pattern AD-2's guard checks a `Bash` call against; it was never itself in question — the AD-2 gap FR-56 closed was the guard's tool matcher omitting `Read` entirely, not any weakening of this invocation convention. Reads of paper-card content go through this same invocation form via FR-55's sanctioned entrypoint, exactly like every other read.

### AD-24 — Monitoring is a sweep, not a daemon

- **Binds:** FR-7 (Dormant, v1-reachable); FR-8 non-preclusion
- **Prevents:** one unit assuming a background process a plugin cannot have, another assuming none
- **Rule:** `kagami monitor` executes the manifest's monitoring config as a sweep at run open / skill activation. Dormant reopening therefore happens **at next session, never asynchronously** — an explicit narrowing of FR-7's "automatically," recorded here and in the memlog (PRD wording amendment recommended, pending researcher approval). v2 post-decision monitoring (FR-8) reuses the same sweep mechanism.

### AD-25 — Testing: the core is verified at the CLI boundary, harness-free

- **Binds:** `kagami/` test suite; hooks; AD-5's standalone claim
- **Prevents:** per-story invention of test strategy; AD-5 degrading into an aspiration
- **Rule:** The core is tested at the entrypoint boundary against the one-line-JSON contract with a scripted driver replacing the harness — this suite is the standing proof of AD-5. A golden minimal-run fixture exercises windows, guards, staleness, E6 ordering, scan-before-write, and lease/crash recovery. The events-deletion invariance test (AD-11) is part of it. Hooks are tested against recorded PreToolUse payloads. Anything finer is story-level.

### AD-26 — Driver operational discipline: refusal-retry ceiling, mandatory `llm_call` reporting, gate-time budget warning `[ADOPTED]`

- **Binds:** FR-48, FR-49, FR-37's soft-limit consequence; the harness/skill layer; `kagami` CLI
- **Prevents:** unbounded retry-storm token burn (the core cannot loop — only the harness driving it can, so the ceiling must live in the core, not skill prose per AD-1, whose own amendment note points here); model calls invisible to the token ledger and charter audit; double-reported calls silently inflating the ledger; two implementers inventing incompatible reporting entrypoints or refusal-counter storage; a live-budget-enforcement feature quietly reopening the PRD §5 "cost discipline via retrieval boundaries, not budgets" NFR / addendum-A4 deferral it was never meant to touch
- **Rule:** (a) **Refusal-retry ceiling.** The refusal counter is not a new store: it is a **pure function over the tail of `events.jsonl`**, matching AD-20's derived-state philosophy — every chokepoint refusal appends its own event (extending FR-31's existing rejected-write-event pattern to all refusals, not only write-guard ones), and the ceiling scans backward from the run's most recent event for a consecutive run of refusal events sharing the same `(entrypoint, target)` tuple (`target` = the entrypoint's primary identifying argument — artifact id, section id, or command target). The run breaks — counter resets to zero — on any intervening non-refusal event for that same tuple. The attempt at the configured ceiling returns a distinct `requires_researcher` status instead of an ordinary refusal (FR-48) — a stop-and-surface outcome, never a silent Nth refusal or an N+1th retry. `requires_researcher` is a **synchronous CLI response**, not a Question Ledger entry — it does not enter `kagami ask`'s queue (AD-8) and carries no question-class key (AD-14); it is surfaced directly to the Interviewer in-conversation, the same channel an ordinary refusal already uses. (b) **Reporting entrypoint.** The harness calls `kagami report llm-call` (the one previously unnamed CLI verb in this spine — every sibling, including deferred `kagami session open/close`, is named) immediately after every model invocation, supplying `role`, `operation_class`, `model_tier`, token counts, cache-hit, and a harness-minted **`--call-id`** (UUID) before the `llm_call` event is appended — AD-22's `needs_llm` protocol run in reverse: the harness fulfills the work *and* reports it, both through validating entrypoints, never a bare append and never a core-side inference. The chokepoint refuses a report whose `call_id` already appears among the run's recent `llm_call` events — the idempotency guard against double-reporting inflating the ledger. A call made but never reported is invisible to the ledger and audit — logged as an AD-11 honest-gap, not silently corrected. (c) **Gate-time warning.** `kagami metrics`'s decision block (FR-37) compares the run's cumulative token ledger against a `config.yaml` soft limit and adds a warning field to the block — never a block on proceeding. This is the **routine reporting read** `kagami metrics` already performs at every gate (AD-11's distinction, amended below) — not the single behavior-altering exception FR-5 names — and it does not itself trigger the live budget enforcement the PRD §5 NFR and addendum A4/O6 defer; it exists to accumulate the chronic-overrun evidence O6 names as its own adoption trigger.

### AD-27 — Testing convention for prompt artifacts: `skills/` and `agents/` are verified by transcript, not pytest `[ADOPTED]`

- **Binds:** `skills/kagami-discovery/SKILL.md`, `agents/` (Scout, Cartographer, Historian, Skeptic, worker definitions); Epic 7 story acceptance criteria
- **Prevents:** unfalsifiable Definition-of-Done on harness-side stories; AD-25's CLI-boundary proof being mistaken for covering the driver too
- **Rule:** AD-25 verifies `kagami/` and `hooks/` only — the entrypoint boundary and the hook payloads, harness-free. `skills/` and `agents/` are prompts, not code, and cannot be exercised by that suite. A driver story's Definition of Done instead requires: (a) a **recorded-transcript check** — a real Claude Code session transcript demonstrating the story's acceptance criteria end-to-end, attached to the PR, extending the `implement-issue` review convention already in use; (b) a **checklist review** against the role/skill's charter — does the artifact violate any AD, does any FR consequence fail on inspection; (c) for the walking-skeleton and toy-run stories specifically, a **golden toy-run protocol** — a fixed, repeatable toy investigation (topic, corpus scope, config pinned) whose event log is inspected against the evaluation rubric fixed at Epic 7 story-design time. None of these substitute for AD-25's suite on the core; they are the driver's parallel, weaker-but-honest verification path — itself an AD-11 honest-gap entry, not a claim of parity with the core's guarantees.

### AD-28 — Fact/judgment separation: paper cards are frame-independent, appraisals are frame-stamped `[ADOPTED]`

- **Binds:** FR-52; AD-18 (paper card identity); non-preclusion for any future belief-store/Appraiser component
- **Prevents:** a frame-dependent opinion (is this paper relevant *to this run's current framing*) laundered into a frame-independent, cross-run-cached fact (AD-18's content-derived paper card); a frame revision requiring re-exploration instead of merely re-scoring
- **Rule:** A paper card (AD-18) may never carry a relevance, priority, or judgment field — the schema registry (FR-30) enforces this as a hard invariant at the write chokepoint (AD-2), the same class of mechanical refusal as FR-31's write-guard, not a drafting convention. A separate, run-scoped **appraisal record** (`{paper_id, judgment, frame_version, reason}`) is the only sanctioned place a frame-dependent valuation lives; it is written only through a validated `kagami` entrypoint and stamped with the Inquiry Frame version that produced it (AD-6's version semantics, reused). When the frame is revised, appraisals are re-issued against the new frame version — the paper cards they reference are untouched, exactly as AD-13/AD-18 already promise for any cross-run-cached fact. This is the one genuinely new architectural rule in the 2026-07-04 Scout-probes change (`change-signal-scout-probes-2026-07-04.md`): it exists to keep the fact/valuation boundary honest now, so that a future belief-store split (`docs/future-scout-redesign.md` — design notes only, not a build target) would be additive rather than a retrofit. Nothing about a frontier, allocator, or governor is implied or required by this rule; it governs data shape only.

### AD-29 — The sensor cost ladder `[ADOPTED]`

- **Binds:** FR-54; non-preclusion for the deferred deep-read sensor
- **Prevents:** a shallow-read probe becoming a slippery slope into full-text ingestion without a named, gated next rung; a future deep-read feature being built as an unplanned redesign instead of a numbered amendment
- **Rule:** Processing depth over a paper is a budgeted ladder, each rung strictly more expensive than the last and never paid without the previous rung's evidence: **metadata** (free at retrieval, `search_corpus`/`corpus_expand`'s existing behavior) → **abstract-derived card** (one model call, once ever, at mint time, FR-54) → **deep read** (**not built in this cycle**; when built, section-limited per `7_questions.md`/`8_questions.md`'s "sections only, never whole papers" framing, and explicitly gated behind evidence that the abstract-derived rung is insufficient). This is the second genuinely new architectural rule since AD-28 (the fact/judgment split); it exists to keep FR-54 a rung rather than an open-ended content-ingestion feature, and gives the deferred deep-read sensor a numbered home in this spine so building it later is an amendment, not a redesign.

### Dependency direction

```mermaid
graph TD
    SKILL[skills/ — Interviewer orchestration] --> CLI[kagami CLI entrypoints]
    AGENTS[agents/ — Scout, Cartographer, Historian, Skeptic, worker] --> CLI
    HOOKS[hooks/ — default-deny guard, session + turn markers] --> CLI
    CLI --> KERNEL[kagami/kernel — frontier, triage, windows, derived state, repair tiers]
    CLI --> STORE[kagami/store — versions, guards, claims, sections, identity]
    CLI --> EVENTS[kagami/events — log, metrics]
    CLI --> BRIEFS[kagami/briefs — read-set bundles, engagement tokens]
    KERNEL --> STORE
    BRIEFS --> STORE
    CORPUS[kagami/corpus — provider port, registry writer] --> PROV[adapters: OpenAlex / S2 / arXiv / GitHub]
    CLI --> CORPUS
    CORPUS --> STORE
```

Arrows mean "may depend on." The core packages never import upward (AD-5); `store` imports nothing else in the diagram.

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| IDs | One ID space, prefix-typed: `run-`, `art-`, `sec-`, `q-`, `ppr-`, `ent-`, `evt-`. Minted only by the chokepoint under its lock (AD-15); `ppr-`/`ent-` are content-derived (AD-18). |
| Artifact type slugs | kebab-case, exactly matching schema registry filenames: `intuition-note`, `inquiry-frame`, `field-map`, `cluster-dossier`, `landscape-synthesis`, `gap-register`, `confidence-checklist`, `researcher-profile`, `candidate-direction`, `direction-decision`, `dissolution-memo` |
| Dates | ISO-8601 UTC everywhere (frontmatter, ledger, events) |
| Script I/O | Every `kagami` entrypoint echoes one-line JSON `{"ok": bool, ...}` on stdout; errors are `{"ok": false, "error": "..."}`; model-needing operations may return `needs_llm` items (AD-22) |
| Event log | JSONL, one event per line, `family` ∈ the spec's ten families; `llm_call` events carry `role`, `operation_class`, `model_tier`, tokens, cache-hit (AD-11) |
| Invocation | Always `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami <cmd>` (AD-23); no bare `python` |
| Human edit surface | `current.md` only (AD-6); `vN.md` and all control-plane files are never hand-edited |
| Credentials | Environment variables only; never `config.yaml` (AD-7) |
| YAML files | `meta.yaml`, `manifest.yaml`, ledger records are machine-owned and comment-free (PyYAML round-trip constraint); the core never rewrites `config.yaml` |
| Vocabulary | PRD Glossary terms verbatim in code identifiers, schema names, and docs — no synonyms |

## Stack

*Seed — verified current 2026-07-02/03; the code owns this once it exists.*

| Name | Version / status |
| --- | --- |
| Python | ≥ 3.12 (3.14.x current) |
| uv | current (toolchain shared with BMAD); plugin ships `pyproject.toml`, invoked via `--project` (AD-23) |
| pydantic | 2.13.x (schema registry validation) |
| PyYAML | 6.x — cannot round-trip comments; acceptable per the machine-owned-YAML convention above |
| Claude Code plugin platform | plugins ship skills + agents + hooks (verified); PreToolUse can deny (exit-2 / `permissionDecision: "deny"`); subagent `model` frontmatter static → launch-time resolution per AD-12; plugin-shipped subagents ignore `hooks`/`mcpServers` frontmatter (plugin-level hooks unaffected) |
| OpenAlex API | usage-based pricing since Feb 2026; **API key now mandatory for all requests** (free key, ~$1/day allowance) — adapter needs key config (env var) from day one |
| Semantic Scholar API | free; keyless = shared global pool (throttled under load), free key = dedicated ~1 RPS introductory tier |
| arXiv API | free; ~1 req/3s etiquette, 429 tightening reported since Feb 2026 — backoff required in adapter |
| GitHub search API | token effectively required; ~30 req/min search limit |

## Structural Seed

Plugin tree:

```text
kagamios/                          # plugin root (code only — AD-13)
  .claude-plugin/plugin.json
  pyproject.toml                   # AD-23: uv project for the core
  skills/kagami-discovery/SKILL.md # the Interviewer (AD-4)
  agents/                          # scout.md, cartographer.md, historian.md, skeptic.md, worker.md
  hooks/                           # default-deny guard, session/turn markers (AD-2, AD-3, AD-4)
  kagami/                          # deterministic core (AD-5): store/ kernel/ events/ corpus/ briefs/
  schemas/                         # versioned YAML registry: 11 artifact types, infrastructure stores,
                                   #   window table, dispatch.yaml (AD-12, AD-14)
```

User project tree (under the configurable output root):

```text
_kagami-output/
  config.yaml                      # provider default, tier→model map, output roots, privacy flag (AD-12)
  runs/<run-id>/
    .lock / .lease                 # AD-15
    manifest.yaml                  # run id, rooting note ref, budgets, monitoring config + state cache (AD-20)
    artifacts/<type>/<art-id>/     # vN.md (immutable) + current.md (edit surface) + meta.yaml (AD-6)
    ledger/                        # q-NNN.yaml record store (AD-17); ledger.md = derived render
    appraisals/                    # frame-stamped judgment records, run-scoped (AD-28, FR-52)
    events.jsonl                   # event log (AD-11)
    queue/                         # worker-emitted unknowns awaiting the ASK scheduler (AD-8)
    premature_ideas/               # generation-window quarantine (AD-9)
  corpus/                          # paper cards, cross-run, content-derived ppr- IDs (AD-18)
  registry/                        # entity registry, cross-run, content-derived ent- IDs (AD-18)
  profile/researcher-profile/      # AD-6-shaped artifact directory (AD-18)
```

## Capability → Architecture Map

| Capability (PRD) | Lives in | Governed by |
| --- | --- | --- |
| §4.1 State machine, loop-backs, waivers, terminals (FR-1..7) | `kernel/` derived-state + `manifest.yaml` + `events/` | AD-2, AD-14, AD-20 |
| §4.1 Dormant monitoring (FR-7) | `kagami monitor` sweep | AD-24 |
| §4.2 Artifact system (FR-9..16) | `store/` | AD-2, AD-3, AD-6, AD-10, AD-15, AD-16, AD-19 |
| §4.2 Repair (FR-13, FR-35) | `kernel/` repair tiers | AD-21, AD-22, AD-16 |
| §4.3 Elicitation kernel (FR-17..24) | `kernel/` + `kagami ask` + `ledger/` + skill | AD-4, AD-8, AD-9, AD-17 |
| §4.4 Role contracts (FR-25..29) | `agents/` + `briefs/` + hooks + session table | AD-4, AD-12 |
| §4.5 Runtime contracts (FR-30..35) | `schemas/` + `store/` + `briefs/` | AD-2, AD-5, AD-6, AD-22, AD-23 |
| §4.6 Observability (FR-36, FR-37, FR-39; 38/40/41 deferred) | `events/` | AD-11, AD-13, AD-14 |
| §4.7 guardrails in-scope for v1 (FR-45 budgets, FR-46 windows) | `kernel/` + `manifest.yaml` | AD-9, AD-20 |
| Corpus / Scout search (FR-25) | `corpus/` + provider adapters | AD-7, AD-18 |
| v2 non-preclusion (FR-8, FR-42/43/44, FR-47) | `schemas/` window table + state enum + exemption flags | AD-14, AD-24 |
| §4.8 Driver & harness shell (FR-48 retry ceiling, FR-49 reporting) | `skills/kagami-discovery/` + `agents/` + new reporting entrypoint | AD-26, AD-27, AD-4 (deferral), AD-11 (honest-gap) |
| §4.9 Scout exploration probes (FR-50 corpus expand, FR-51 port contract, FR-52 appraisals, FR-53 rediscovery metric) | `kagami/kernel/scout.py` (`corpus_expand`) + `kagami/corpus/` (port + adapters) + new appraisal store + `kagami/kernel/metrics.py` | AD-2, AD-7 (amended), AD-11 (event-derivable graph), AD-28 (new), AD-20 (derived-metric pattern) |
| §4.10 Paper content & read discipline (FR-54 extraction, FR-55 read path, FR-56 guard closure) | `kagami/corpus/cache.py` (`get_or_create_paper_card`'s compute path, `read_paper_card`) + `kagami/registry.py` (`paper_card_readable_states`) + `hooks/hooks.json` matcher | AD-2 (text-corrected), AD-7, AD-18, AD-22 (`needs_llm`/validated-input protocol), AD-29 (new) |

## Deferred

- **Scout graph-exploration architecture (belief store, frontier, allocator, governor)** — recorded as design notes only in `docs/future-scout-redesign.md`, explicitly not an implementation source. The 2026-07-04 Scout-probes change (FR-50..FR-53, AD-28) ships four minimal, independently shippable instrumentation probes instead, each designed to produce the dogfooding evidence that notebook's adjudication table needs. Revisit trigger: per-component, evaluated against 2–3 real investigation runs' probe data — not before, and not by this notebook's existence alone.
- **Deep-read sensor (AD-29 rung 3)** — section-limited full-text ingestion beyond the abstract-derived card (FR-54). Not built this cycle; deferred pending evidence from dogfooding runs 2–3 on whether the abstract-derived rung is sufficient. Revisit trigger: the sanctioned read path (FR-55) proving insufficient for Historian/Synthesize/Locate's actual needs, observed during runs 2–3, per `change-signal-paper-content-2026-07-06.md`.
- **Local embedding index over paper cards** — **recorded deviation from `docs-spec/07_runtime.md` §5–§6** (which specifies corpus-tier hybrid retrieval including embeddings, and embeddings + graph communities as Map's partition mechanism), accepted by explicit researcher decision. Interim mechanism, fixed here so units don't diverge: candidate partitions derive from **citation-graph communities plus provider-side relevance/semantic search**, and FR-26's two structurally different cuts must be derivable from that pair. Revisit trigger: Scout/Cartographer demonstrably miss relevant clusters during dogfooding. (Artifact tier stays graph-only permanently — Standing Refusal, not a deferral.)
- **Propose/Decide flows** (FR-42/43/44, the Propose-side unprimed question, post-decision monitoring FR-8) — v2; types, windows, and exemption flags already ship per AD-14; FR-8 reuses AD-24's sweep.
- **Cross-run analytics store + Design Audit Report loop** (FR-38, FR-40, FR-41) — needs accumulated runs; PRD §7.2. The run-1 schema commitments that make this loop possible later are *not* deferred (AD-14). FR-39's content-stripping rules (event shapes/counts/classes travel; question text, artifact content, paper identities never) ride this deferral explicitly and bind any future sharing surface.
- **CLI / non-plugin runtime adapter** — enabled by AD-5, built only if the plugin-model downgrades (AD-11) prove unacceptable.
- **Prompt-cache prefix ordering, machine token budgets, stall surfacing, question-form experiments** (O2/O5, O6, O7, O8) — adoption triggers per PRD §7.2.
- **Provider failover/retry/backoff policy details** — a story-level decision inside the AD-7 port; rate-limit facts recorded in Stack.
- **Exact schema field lists per artifact type** — transcription from `docs-spec/04_artifacts.md` + `07_runtime.md` §1 at story time; the registry format, window table, ledger schema, and exemption flags are fixed here (AD-14), their contents are data.
- **Hook matcher syntax and deny-message text** — single-unit detail; the deny *semantics* (default-deny + allowlist) are AD-2, not deferrable.
- **`kagami migrate` mechanics** — the refusal rule and version stamping are AD-23; the migration implementation waits until a schema change exists to migrate.
