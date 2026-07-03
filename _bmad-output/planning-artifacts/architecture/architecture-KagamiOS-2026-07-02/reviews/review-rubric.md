# Rubric Review — ARCHITECTURE-SPINE.md (KagamiOS v1)

Reviewer: rubric walker (architecture-spine reviewer gate)
Date: 2026-07-02
Target: `_bmad-output/planning-artifacts/architecture/architecture-KagamiOS-2026-07-02/ARCHITECTURE-SPINE.md`
Judged against: good-spine checklist (items 1–6), PRD §4.1–4.7, `docs-spec/03,04,05,07,08`

## Verdict

**Revise before build.** The domain core of this spine is genuinely strong: the gatekeeper-kernel paradigm, the AD-2 chokepoint, the AD-6 store rules, and the AD-14 non-preclusion obligation encode the spec's hardest invariants as store refusals rather than prompt convention, and the three user-made decisions (runtime shape, provider abstraction, store layout) are all present and enforceable at the headline level. The stack table's claims verify as current for 2026-07-02 (pydantic 2.13.x, OpenAlex Feb-2026 pricing change, Python 3.14.x, S2 keyless limits — all confirmed). But the spine fails the gate as-is on one critical flaw — the AD-2/AD-3 interaction inverts the provenance model whenever the PreToolUse hook's coverage is imperfect, and the spine then defers hook coverage as a "single-unit concern" — and on a band of high findings clustered exactly where domain-focused drafts go silent: the human-edit/immutability mechanism, concurrent-session and crash behavior, installation and schema migration, the protocol for core operations that need model output, and monitoring for the v1-reachable Dormant terminal. None of these require rethinking the paradigm; all are additive ADs or rule rewordings. Fix the critical and the highs, downgrade the two "impossible" overclaims to honest detect-and-audit entries (the spine already has the pattern in AD-11), and this spine is buildable.

---

## Critical

### C1 — Hook evasion converts AI writes into human provenance (AD-2 × AD-3, plus the Deferred hook item)
- **Checklist:** 2 (Rule does not prevent its stated divergence), 3 (Deferred item hides cross-unit risk)
- **Location:** AD-2 Rule ("A PreToolUse hook denies the agent's direct `Write`/`Edit`/`Bash`-redirect access"), AD-3 Rule ("File changes not made through the chokepoint … are human edits"), Deferred: "Hook implementation details (matcher patterns, deny-message text) — single-unit concern."
- **Problem:** AD-3 makes out-of-band change *definitionally* human, and `kagami scan` then flips spans to `human-confirmed` and resolves unknowns. That definition is only sound if AD-2's deny surface is total. It is not: a matcher-based PreToolUse hook over "Write/Edit/Bash-redirect" cannot enumerate every Bash mutation path (`python -c`, `tee`, `sed -i`, `mv`, `cp`, heredocs, `git apply`, …). Any AI write that slips past the hook is laundered into human provenance — which defeats FR-4/FR-31 (constitutive-triad write-guards, "no role override"), FR-12 (authorship classes), and FR-19 (edits resolve unknowns). AD-3's own "Prevents" line — "an AI path that fakes human provenance" — is exactly what the gap creates. Deferring the deny surface as a single-unit detail hides the one place where the whole provenance model is load-bearing.
- **Fix:** (a) Lift the deny surface into the spine: default-deny *all* writes under the output root for *all* tools, allowlisting only the `kagami` entrypoints — never an enumerated blocklist of write patterns. (b) Break the definitional equivalence in AD-3: out-of-band changes detected by `kagami scan` are *candidate* human edits; attribution requires either occurrence outside an active AI turn (session-scoped attribution via hook-recorded turn boundaries) or explicit one-keystroke human confirmation at next gate. Unattributable changes are quarantined as violations, not human-confirmed. (c) Keep only matcher syntax and message text in Deferred.

---

## High

### H1 — Human edits vs `vN.md` immutability: the mechanism is undecided and the two readings are incompatible
- **Checklist:** 1 (divergence point the spine is silent on), 2 (AD-6's Rule undermined)
- **Location:** AD-3 Rule ("`kagami scan` detects them by content hash on next touch"), AD-6 Rule ("`vN.md` files (immutable once written)"), Structural Seed (`artifacts/<type>/<art-id>/` = `vN.md` + `meta.yaml`).
- **Problem:** If the researcher's editor is the sanctioned human path (AD-3), what file do they edit? If they edit the current `vN.md` in place: immutability is broken, the original v-N content is unrecoverable (defeating AD-6's "Prevents: history reconstruction from diffs" and FR-10's "superseded versions retained"), and integer-compare staleness never fires because no new version was minted — dependents pinned `@vN` silently point at changed content. The store unit and the scan unit, built independently, will resolve this differently.
- **Fix:** Decide the edit surface in AD-6: e.g., each artifact directory carries a mutable `current.md` (materialized copy of the current accepted version) as the *only* human-editable file; `vN.md` files are never edited by anyone. `kagami scan` diffs `current.md` against the latest `vN.md` hash (hashes recorded in `meta.yaml`), mints `v(N+1).md` with the touched spans marked human-confirmed, and advances the pointer — which makes staleness fire correctly through the existing integer compare.

### H2 — Concurrent sessions, crash recovery, and claim liveness are unaddressed
- **Checklist:** 6 (operational envelope), 2 (AD-10's "live worker" is unenforceable as written)
- **Location:** AD-10 Rule ("a section claimed by another *live* worker"), AD-2/AD-11 (multi-file mutation: `vN.md` + `meta.yaml` + `events.jsonl` per operation), Structural Seed.
- **Problem:** (a) Nothing defines how the store knows a worker is live; after a subagent or session crash, claims in `meta.yaml` wedge their sections forever or get honored inconsistently. (b) Each chokepoint operation touches at least three files with no stated atomicity or ordering; a mid-operation crash leaves an artifact version without its event, or a pointer without its file — and no recovery pass is defined. (c) Two Claude Code sessions opened on the same run (the rubric's explicit case) both append `events.jsonl` and rewrite `meta.yaml` with no locking discipline. Every one of these is a place where independently built units will choose incompatibly.
- **Fix:** Add an AD: single-writer-per-run via a lease file in `runs/<run-id>/` (holder id + heartbeat timestamp; second session opens read-only or must break a stale lease explicitly); claims carry the lease id and expire with it; chokepoint operations follow a fixed write order (version file → meta → event) with a `kagami scan`-style consistency repair on run open that detects and completes/rolls back torn operations. Note explicitly that JSONL append is the crash-tolerant format choice for the event log.

### H3 — Installation/distribution and schema upgrade/migration are silent dimensions
- **Checklist:** 6 (a whole dimension left silent is a finding)
- **Location:** Structural Seed (plugin tree shows `.claude-plugin/plugin.json` only); AD-13 (separates data from plugin but says nothing about upgrading either); no AD, Deferred, or open question covers either dimension.
- **Problem:** (a) *Install:* the core is a Python package with dependencies (pydantic, PyYAML) living inside a plugin directory, invoked as `uv run kagami` from the *user's project* cwd. How the package and its deps materialize on install, and how `uv run` resolves `kagami` from an arbitrary cwd (plugin-local `pyproject.toml`? `uv run --project <plugin-dir>`? `uv tool install`?) is undecided — and it shapes every entrypoint's invocation contract (a Consistency Convention row already hard-codes `uv run kagami`). (b) *Upgrade:* AD-13 guarantees plugin upgrades don't touch user data, but not what happens when an upgraded plugin's schema registry meets existing runs. FR-30 makes old schemas recoverable for reads; nothing decides write behavior against older-schema runs, or who migrates.
- **Fix:** Two short ADs. Install: name the mechanism (e.g., plugin ships a `pyproject.toml`; every invocation is `uv run --project ${CLAUDE_PLUGIN_ROOT} kagami …`; the skill/hooks own resolving the plugin root) and update the Invocation convention to match. Migration: stamp `schema_registry_version` in `meta.yaml`/`manifest.yaml` at write time; the chokepoint refuses to mutate a run written under a newer registry; a `kagami migrate` entrypoint (human-invoked, logged) is the only path that rewrites old runs — mechanical migrations only, minting new versions, never editing `vN.md` in place.

### H4 — No protocol for core operations that require model output
- **Checklist:** 1 (two units will invent incompatible patterns), 5 (spec capabilities FR-33, FR-35 lack an architectural home for their LLM step)
- **Location:** Design Paradigm ("every volatile dependency is an adapter behind a port: … the LLM harness itself") — the port is named and then never given an AD; Capability Map §4.5 row.
- **Problem:** Several spec-mandated operations are half-deterministic, half-model: summary regeneration on acceptance (FR-33 / 07 §3 — summary is part of the version), Tier-1 repair plausibility checks (FR-35 / 07 §4), paper-card extraction (04 §3). The core is deterministic and, in the plugin runtime, cannot call a model mid-CLI-invocation — the harness must supply the model output. But no AD fixes the shape: does `accept` refuse without a supplied summary, or emit a needs-LLM work item? Does repair return Tier-1 prompts for the harness to run? The accept unit, the repair unit, and the corpus unit will each invent a different answer.
- **Fix:** Add an AD naming the single pattern: chokepoint entrypoints never invoke models; any operation needing model output either (a) requires the output as a validated input argument (e.g., `kagami accept` demands a schema-checked summary) or (b) returns a typed `needs_llm` work item in its JSON echo, which the harness fulfills and submits through a validating entrypoint. One pattern, used by accept, repair Tier-1, and paper-card extraction alike.

### H5 — Monitoring has no architectural home, but Dormant is a v1-reachable terminal
- **Checklist:** 5 (PRD capability walk — FR-7 hole), 6 (environmental envelope: nothing in a plugin runs unattended)
- **Location:** Capability Map §4.1 row (FR-1..8); the word "monitoring" appears nowhere in the spine; PRD §7.1 ("Terminals reachable in MVP: Dissolved and Dormant"), FR-7 ("A Dormant run continues to receive monitoring updates and can be reopened automatically").
- **Problem:** Post-*decision* monitoring (FR-8) is legitimately deferred, but Dormant is in MVP scope and FR-7 gives it live monitoring semantics. A Claude Code plugin has no daemon; *when* monitoring runs is an architecture-level decision, not a story detail — left silent, one unit will assume a background process that cannot exist and another will assume none.
- **Fix:** Decide it: e.g., "monitoring is a sweep, not a daemon — `kagami monitor` executes the manifest's monitoring config on skill activation / run open; Dormant reopening therefore happens at next session, never asynchronously," and record the FR-7 "automatically" narrowing explicitly (or push a PRD amendment). Add a row to the Capability Map.

---

## Medium

### M1 — AD-4's "cite a generating role session" is provenance-by-declaration, presented as mechanical enforcement
- **Checklist:** 2
- **Location:** AD-4 Rule ("the store refuses artifact content that does not cite a generating role session, which is what 'the Interviewer never generates content' means mechanically").
- **Problem:** The chokepoint can verify a session id is *cited*, not that the content *came from* that session — the main thread can generate content and cite any logged subagent launch. This is detect-and-audit, not prevention, but the Rule claims prevention.
- **Fix:** Either restate honestly (move it into AD-11's accepted detect-and-audit list, auditable via role-tagged launch events per FR-29), or strengthen: `kagami brief` mints a single-use engagement token bound to the role and target; content submission must present it.

### M2 — AD-9's "violation is impossible" overclaims for ask-before-show
- **Checklist:** 2
- **Location:** AD-9 Rule ("E6 ordering is proven by timestamps and violation is impossible, not merely logged").
- **Problem:** The store gates artifact *writes*. FR-24's obligation is about *display*: the AI must not show its framing before the unprimed answer is recorded — and the Interviewer can render framing text conversationally without touching the store. Write-ordering is genuinely impossible to violate; show-ordering is only auditable.
- **Fix:** Scope the impossibility claim to artifact creation; add display-ordering to AD-11's honest gap list ("conversational display before ledger entry is detect-and-audit, acceptable because the drafted artifact remains impossible").

### M3 — Question Ledger format contradicts the spec's ledger contract
- **Checklist:** 1, 5 (contradicts `docs-spec/05_elicitation.md` §5)
- **Location:** Structural Seed: "`ledger.md` — question ledger, append-only."
- **Problem:** Spec 05 §5 defines ledger entries as versioned objects (`q-014@v1`) with `consumed_by` *stamped later* as artifacts pin them, and `superseded_by` on revision. A single append-only Markdown file cannot support post-hoc stamping or per-entry versioning; staleness-on-answer-revision (E5) pins `q-id@version`. Two units (ask/answer vs consume/staleness) will diverge on entry mutability.
- **Fix:** Make the ledger a directory of per-question entry files (or a YAML/JSONL stream with per-entry versions) under AD-6-style rules; define "append-only" as entries never deleted, `consumed_by` stamped by minting a new entry version through the chokepoint. Human-readable rendering can be a derived `ledger.md`.

### M4 — Corpus-tier embeddings deferral silently contradicts 07_runtime §6 and undercuts FR-26's mechanism
- **Checklist:** 5
- **Location:** Deferred: "Local embedding index over paper cards — revisit when…"
- **Problem:** `docs-spec/07_runtime.md` §6 specifies the corpus tier as "metadata + citation graph + **embeddings** over paper cards," and §5's dispatch table computes candidate partitions via "embeddings + graph communities" — the mechanism behind the Cartographer's two structurally different cuts (FR-26). Deferring embeddings is a defensible MVP narrowing (provider-side semantic search now exists — OpenAlex sells it at $0.01/query as of Feb 2026), but the spine neither acknowledges the deviation nor names the substitute partition mechanism.
- **Fix:** In the Deferred entry, state the deviation from 07 §6 explicitly and fix the interim mechanism: candidate partitions from citation-graph communities plus provider-side relevance/semantic search; FR-26's two cuts must be derivable from that pair. Record it as an accepted-deviation, mirroring AD-11's style.

### M5 — "Human edits always win over queued AI writes" (07 §2) is not encoded anywhere
- **Checklist:** 5, 1
- **Location:** AD-10 (claims), AD-3 (scan "on next touch" — touch by whom, when?).
- **Problem:** The spec's concurrency rule gives human edits priority over queued AI writes. The spine's claim mechanism arbitrates AI-vs-AI only; nothing orders an undetected human edit against an incoming chokepoint write — a worker holding a valid claim can overwrite a human edit made since its brief was rendered.
- **Fix:** One sentence in AD-10 or AD-3: the chokepoint runs the scan hash-check on the target artifact *before* applying any AI write; a mismatch processes the human edit first (per H1's mechanism) and rejects the AI write as stale.

### M6 — FR-47 is absent from binds, the Capability Map, and the non-preclusion obligation
- **Checklist:** 5 (FR-cluster walk — §4.7 hole)
- **Location:** Frontmatter `binds` (stops at FR-46), Capability Map §4.7 row (lists only FR-45, FR-46), AD-14.
- **Problem:** FR-47 (constitutive-triad fields and E6 unprimed questions permanently exempt from Design Audit demotion) governs the deferred audit loop, but its *exemption marking* is a schema-registry concern with the same retrofit risk AD-14 exists to prevent: if the registry format ships without a permanent-exemption flag, v2's audit loop needs a breaking schema change.
- **Fix:** Add an exemption flag (e.g., `audit_exempt: permanent`) to the registry format under AD-14's day-one obligation; add FR-47 to `binds` (non-preclusion) and to the §4.7 map row.

### M7 — Testing strategy is a silent dimension
- **Checklist:** 6
- **Location:** Absent everywhere — no AD, convention, Deferred entry, or open question.
- **Problem:** The spine's central payoff — a deterministic core testable without the harness (AD-5) — is never cashed out as a testing decision. How the core is verified (against what contract), and how hook and subagent behavior are exercised, will otherwise be invented per-story.
- **Fix:** One short AD or convention row: the core is tested at the CLI entrypoint boundary against the one-line-JSON contract with a scripted driver replacing the harness (this is also the standing proof of AD-5); a golden minimal-run fixture exercises windows, guards, staleness, and E6 ordering; hooks are tested against recorded PreToolUse payloads. Anything finer is story-level.

### M8 — Worker-role taxonomy and brief keying don't cover the spec's read-set table
- **Checklist:** 1, 5
- **Location:** AD-4 (four named subagents; `kagami brief <role> <target>`), Consistency Conventions (`role` tag required on `llm_call`).
- **Problem:** `docs-spec/07_runtime.md` §3 keys read-sets by *consumer state* (Frame, Deepen worker, Synthesize, Locate…), not by the four named roles. Who drafts dossier non-Evolution sections, the Synthesis, and the Gap Register — and what `role` tag those calls carry (FR-29 requires non-null) — is unspecified. The briefs unit and the agents unit can key bundles incompatibly.
- **Fix:** In AD-4, name the drafting worker roles (e.g., a `worker` subagent parameterized by state/cluster) and key briefs by (role, state, target); state that the read-set table in 07 §3 is the normative content of the brief renderer.

---

## Low

### L1 — `binds` frontmatter is internally inconsistent with Deferred
- **Checklist:** 5
- **Location:** Frontmatter: `binds: [FR-1..FR-41, FR-45, FR-46, 'FR-42/43/44 non-preclusion only']`.
- **Problem:** The range FR-1..41 includes FR-38/40/41 (deferred, listed under Deferred) and FR-8 (deferred per PRD §7.2 except non-preclusion); FR-47 is missing entirely (see M6).
- **Fix:** Rewrite as bound / non-preclusion-only / deferred lists that match the Deferred section: e.g., binds FR-1..7, 9..37, 39, 45, 46; non-preclusion FR-8, 42, 43, 44, 47; deferred FR-38, 40, 41.

### L2 — Provider credentials undecided; the default provider is no longer usable keyless
- **Checklist:** 4 (verification nuance), 6
- **Location:** Stack table ("OpenAlex API — free tier + usage-based pricing"), AD-12 (`config.yaml` contents).
- **Problem:** Verified 2026-07-02: OpenAlex's Feb-2026 change made API keys mandatory for *all* requests ($1/day free usage per key). The spine's "free tier" wording is roughly right, but Scout cannot call the default provider without a key, and where keys live (env var vs `config.yaml` — the latter sits in the user's project and may be committed) is undecided.
- **Fix:** Convention row: provider credentials come from environment variables only, never `config.yaml`; note the OpenAlex mandatory-key fact in the Stack table.

### L3 — Entity registry has no owning module in the layer map
- **Checklist:** 1
- **Location:** Design Paradigm layer map (store/kernel/events/corpus/briefs); Structural Seed `registry/`; ID convention `ent-`.
- **Problem:** The registry appears in the tree and the ID space but no `kagami/` package owns it; FR-32/FR-14 give it artifact-grade identity semantics.
- **Fix:** Assign it explicitly (natural home: `kagami/store/` for identity/versioning with `kagami/corpus/` as its main writer) in the layer map.

### L4 — Capability Map §4.1 row omits `events/`
- **Checklist:** 5 (cosmetic map hole)
- **Location:** Capability Map, §4.1 row ("`kernel/` derived-state + `manifest.yaml`").
- **Problem:** FR-1 requires `state_transition` events and FR-5's loosening proposals read derived aggregates (`kagami metrics`) — both live in `events/`, absent from the row.
- **Fix:** Add `events/` to the row's "Lives in" column.

---

## Checklist disposition

| Item | Result |
| --- | --- |
| 1. Fixes all real divergence points | **Fail** — H1, H2, H4, M3, M5, M8, L3 |
| 2. Every Rule enforceable, prevents its divergence | **Fail** — C1, M1, M2 (plus H2's "live worker") |
| 3. Deferred items cannot cause divergence | **Fail** — hook deny surface (C1); others sound |
| 4. Named tech verified-current | **Pass** — all claims confirmed for 2026-07-02 (pydantic 2.13.4, OpenAlex Feb-2026 change, Python 3.14.x, S2 limits); one nuance (L2: OpenAlex keys now mandatory) |
| 5. Covers PRD FR clusters; no docs-spec/07 contradictions | **Partial** — H5, M3, M4, M5, M6, L1, L4 |
| 6. Every owned dimension decided/deferred/open | **Fail** — installation, migration, crash recovery, concurrent sessions, testing, monitoring all silent (H2, H3, H5, M7) |
