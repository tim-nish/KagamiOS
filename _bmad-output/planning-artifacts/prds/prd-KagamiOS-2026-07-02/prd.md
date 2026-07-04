---
title: KagamiOS
status: final
created: 2026-07-02
updated: 2026-07-03
---

# PRD: KagamiOS
*Working title — confirm.*

## 0. Document Purpose

This PRD translates the normative, already-finalized design in `docs-spec/` into product-requirement form for downstream BMAD planning (architecture, epics). It is a translation, not a redesign: every Feature, FR, and Non-Goal below traces to a specific `docs-spec/` document, and where this PRD had to make a PM-framing call the spec itself doesn't dictate (wording, grouping, journey invention), the call is tagged `[ASSUMPTION]` inline and indexed in §10. One product-level requirement originates here rather than in `docs-spec/` (which is platform-silent): KagamiOS ships as a **Claude Code plugin in the BMAD ecosystem** — see §5's Platform constraint (researcher decision, 2026-07-02). A second product-level addition originates from implementation-readiness review rather than `docs-spec/`: §4.8's driver-side FRs (FR-48, FR-49), added 2026-07-03 after Epics 1–6 shipped the deterministic core with no epic ever covering the harness that drives it — see §4.8's description for the gap this closes. Deep mechanism detail (schema field lists, dispatch-table tiers, cache guidance, rejected-alternative rationale) that would pad this document without changing what's built lives in `addendum.md`; `docs-spec/` itself remains the authoritative machine-readable source and is not duplicated here. FRs are numbered globally (FR-1 through FR-N) and grouped by mechanism so downstream architecture work can address one subsystem at a time.

## 1. Vision

KagamiOS transforms a vague research intuition into a small set of concrete, evidence-backed candidate research directions — doing the tractable landscape work automatically and asking the researcher only the questions whose answers change the outcome, terminating the moment the researcher confidently selects a direction. It produces a decision plus the understanding required to make it: the field maps, dossiers, and gap registers it generates along the way are the *trace* of that understanding, not the deliverable.

The name is the design intent — questions are put to the researcher against computed evidence, one high-leverage question at a time, so the researcher's own interest becomes visible to them. The system never tells the researcher what to want; it reflects.

What makes this different from a literature-review tool is what it refuses to do: it will not draft a survey for coverage's sake, it will not ask anything computable or anything without evidence already shown, and — critically — it treats reaching "this intuition doesn't survive scrutiny" as fast as possible as a genuine product win, not a failure mode to be engineered away. A survey's deliverable can be handed to someone else; KagamiOS's cannot, because the thing it produces — a defensible decision — depends on the researcher having actually read the papers that define their direction. The system verifies the *trace* of that reading (the Confidence Checklist, `human_read` marks on the papers behind a surviving candidate — §4.7), never the understanding itself; understanding is the one thing here that cannot be delegated, only evidenced.

Every mechanism in this system is held to one test, and every Feature and FR below should trace back to it: would this have moved a real investigation toward a confident choice, or would it have been overhead? (`addendum.md` A5 restates this as the design test, not merely a UX volume check.) The corollary is why the anchoring-discipline mechanisms in §4.3 and §4.4 exist at all: the deep failure mode of AI-assisted discovery is homogenization — the AI's fluent framing quietly becoming everyone's framing — and generation windows, ask-before-show, and the Skeptic's attack-only mandate are the concrete defenses against it, not process for its own sake. `[ASSUMPTION: this section condenses docs-spec/01_vision.md "The mirror," "Three consequences," and "What KagamiOS is not," plus 02_principles.md E6's homogenization framing, into PM-facing prose; no new claims added beyond the source.]`

## 2. Target User

### 2.1 Jobs To Be Done

- As a researcher sitting on a vague intuition, I need to know within weeks — not months — whether it's worth pursuing, and if so, which of several concrete directions to commit to.
- As a researcher, I need the landscape work (what exists, what's been tried, where the real gaps are) done for me where it's mechanical, so my own reading time goes to the parts that actually require my judgment.
- As a researcher, I need to be asked only questions I couldn't have answered by looking something up — and I need to know, later, that every question I was asked actually mattered to the outcome.
- As a researcher, I need a decision I can defend to myself and to an advisor: a record of *why* I chose this direction over the others, with the counterfactual evidence attached, not just a conclusion.
- As a researcher, I need dissolving a bad intuition to be cheap. An idea that doesn't survive scrutiny should cost me days, not the months it costs today.

### 2.2 Non-Users (v1)

- **Labs or multi-researcher teams using KagamiOS as a shared gate.** v1 is single-researcher; an advisor or lab is a *consumer* of the finished handoff bundle (the case brought to a meeting), never a second approval gate inside the system. (`docs-spec/09_open_items.md` OQ6 — deliberately deferred, not a permanent exclusion.)
- **Researchers wanting an idea-generation or "AI Scientist" tool.** KagamiOS is structurally forbidden from proposing direction-shaped content before the landscape evidence is in place; it will not generate research ideas from nothing.
- **Researchers wanting execution support.** Experiment design, implementation, running experiments, and writing are all outside the system boundary. The sole concession is a researcher-executed, hours-bounded micro-probe usable as evidence for one Gap Register claim.

### 2.3 Key User Journeys

*KagamiOS has a single user role (the researcher) interacting with a system of internal AI role-contracts, not multiple human personas — per product-shape guidance this section stays light: two journeys, prose beats, no FR-mapping table.* `[ASSUMPTION: personas below are invented illustrations, not sourced from docs-spec, which deliberately names no example researcher other than the anonymous "Signature investigation" dogfooding case.]`

- **UJ-1. Asha decides where to point her second PhD year.**
  - **Persona + context:** Asha, a second-year PhD student, has a hunch that her advisor's lab hasn't fully chased down. She's never run KagamiOS before.
  - **Entry state:** Opens a new run from a half-formed idea — no paper, no notes beyond a sentence in her lab notebook.
  - **Path:** She types the sentence as her Intuition Note. KagamiOS backfills a minimal Inquiry Frame and asks one menu question about scope (realizes FR-1, FR-17). It then computes a Field Map on its own and offers her two structurally different ways to cluster the field, asking her to pick or edit one (realizes FR-26). Over the next several days it deepens one cluster at a time, surfacing a handful of batched, ranked questions at each review gate — never more than five at once, always with a default she can accept (realizes FR-18, FR-20).
  - **Climax:** At Propose, KagamiOS shows her three to five candidate directions on one qualitative comparison table, each citing specific gaps or synthesis evidence, with no aggregate score telling her which to pick (realizes FR-42). She reads the Confidence Checklist and finds she can answer every entry from memory — the communities, the defining papers, why each surviving gap exists (checked against the Decide gate's own exit criteria, FR-44).
  - **Resolution:** She signs a Direction Decision. It records which candidates she selected, parked, and rejected, and why. Total elapsed time: under three weeks.
  - **Edge case:** Midway through Deepen, new evidence in one cluster contradicts her original framing. KagamiOS loops back to Frame with a one-line cause note rather than silently pressing forward (realizes FR-2).

- **UJ-2. Marcus's intuition doesn't survive contact with the literature.**
  - **Persona + context:** Marcus has an idea he's excited about but hasn't stress-tested.
  - **Entry state:** Enters via a paper he just read (paper-first entry mode), which backfills his Intuition Note.
  - **Path:** By the end of Map, the Field Map already shows his intuition sitting inside a cluster with a well-known negative result three years old. The Skeptic role flags this directly rather than letting him discover it later (realizes FR-27).
  - **Climax:** Marcus recognizes the idea doesn't hold up. He does not push through to Propose.
  - **Resolution:** KagamiOS writes a Dissolution Memo — what the intuition was, what dissolved it, what he learned, and the conditions under which it could be revived — instead of a Direction Decision (realizes FR-6). Elapsed time: four days.
  - **Why this journey matters:** a fast, well-documented dissolution is a designed success state for KagamiOS, not a failure path the product should try to avoid producing.

## 3. Glossary

*Downstream workflows and readers use these terms exactly; no synonyms appear elsewhere in this PRD.*

**Terminal artifacts and decision objects**
- **Direction Decision** — The terminal, human-signed artifact: a portfolio of candidates marked selected / parked / rejected / spawned, plus a Confidence Checklist audit, probe flags, and pre-registered falsifiable claims. Its handoff bundle is the artifact graph plus a generated two-page portfolio brief — the rendered form a downstream reader (advisor, future self) actually opens. Ends a run in the Decided state.
- **Dissolution Memo** — The terminal artifact when an intuition doesn't survive scrutiny: what the intuition was, what dissolved it, what was learned, revival conditions, and any salvaged fragments spun off as new Intuition Notes for a future run. Ends a run in the Dissolved state; reaching it quickly is a success, not a failure.

**Working artifacts (produced in sequence, each depends on the last)**
- **Intuition Note** — The raw starting-point capture, under a minute, no mandatory structure. Every entry mode backfills one.
- **Researcher Profile** — Cross-project, ever-growing record of the researcher's taste, skills, constraints, risk appetite, and time horizon, built incrementally from their answers. Annotated, never filtered.
- **Inquiry Frame** — Defines what the intuition means and its boundary: in-scope readings, exclusions, the researcher's unprimed hunch, constraints. The most-revised artifact in the system.
- **Confidence Checklist** — Everything the researcher must credibly know before choosing a direction, created at Frame and filled in by every subsequent state; doubles as the test for whether the run has converged.
- **Field Map** — The structure of the field: topical clusters, how they relate, venues, and each cluster's recency profile (how fast it moves; how stale its published record runs). Research groups are entities referenced inside it, not clusters themselves.
- **Cluster Dossier** — The deep card for one in-scope topical cluster: its research programme, a mandatory Evolution history, representative papers (each carrying a `human_read` flag and one-line reaction once read — see FR-44), people, venues, and current frontier. One per cluster.
- **Landscape Synthesis** — The cross-cluster picture: a competing-approaches matrix, trend directions, and a solved/open table (every "open" claim must carry evidence of openness, not just absence of a citation).
- **Gap Register** — Per-gap statement of what's missing, evidence of its absence, a mandatory explanation of *why the gap exists*, and a human mark of whether it's meaningful to this researcher. Admits micro-probe evidence.
- **Candidate Direction** — One of several competing direction cards, generated only after the Gap Register is accepted; cites specific gap or synthesis evidence, or names a cross-cluster transplant or a why-now/capability-overhang rationale; carries red-team notes and a selected/parked/rejected disposition once the researcher decides.

**Infrastructure stores (not researcher-facing artifacts, but part of the same ID space)**
- **Question Ledger** — Append-only log of every question asked, its answer, any default applied instead, and later revisions. The run's reasoning trace.
- **Entity Registry** — Typed entities (paper, person, group, venue) with stable IDs and typed relations between them. No hierarchy.
- **Corpus Cache** — Paper cards computed once per paper and reused across the run and future runs.
- **Run Manifest** — Per-run bookkeeping: run ID, the rooting Intuition Note, each cluster's current derived state, budget counters, monitoring configuration.
- **Run Event Log** — Append-only record of everything that happened during a run (every LLM call, retrieval, edit, question, gate, transition). Exhaust: nothing at runtime may depend on reading it back.

**States, gates, and terminals**
- **The six working states** — Frame, Map, Deepen, Synthesize, Locate, Propose. Nominal order; loop-backs between them are normal, not errors.
- **Decide gate** — Where Candidate Directions become a signed Direction Decision. Human-only.
- **Decided / Dissolved / Dormant** — The three terminal outcomes of a run: a signed decision, a documented dissolution, or a parked run under monitoring with defined revival conditions.
- **Derived state** — A cluster's actual state is computed as the earliest working state whose exit criteria it hasn't yet met; different clusters in the same run can be in different states at once.

**AI roles (behavioral contracts, not personas)**
- **Interviewer** — Runs the question-scheduling loop; never advocates for an answer.
- **Scout** — The only role that touches the raw literature corpus; reports what exists, never interprets.
- **Cartographer** — Drafts the Field Map's clustering; must always offer at least two structurally different ways to cut the field.
- **Historian** — Writes each dossier's Evolution section; never speculates about the frontier.
- **Skeptic** — Attacks framings, clusterings, gaps, and candidates; never proposes an alternative; works from a fresh context each time.

**Mechanism terms**
- **Question rent** — The requirement that every question declare what it's for and earn its keep; audited retroactively against whether the answer was actually used.
- **Micro-probe** — A researcher-run, hours-bounded feasibility check usable as evidence for exactly one Gap Register field. Produces no artifacts of its own and never opens a full execution stage.
- **Minimal-run profile** — The subset of every artifact's fields required for a fast (days-scale) run, as opposed to the full field set.
- **Generation window** — The earliest state at which the system is permitted to draft a given artifact type; enforces that no direction-shaped content appears before the Gap Register is accepted.
- **Staleness** — The condition where an artifact's pinned dependency is out of date relative to its source's current accepted version; marked immediately, repaired lazily.

## 4. Features

`[ASSUMPTION: the seven subsections below (4.1-4.7) group FRs by mechanism, mapping directly onto docs-spec/03-08's own document boundaries; the spec does not itself mandate this exact grouping, but it was chosen for downstream architecture traceability over an alternative grouping by researcher-visible workflow stage.]`

### 4.1 State Machine and Workflow Control
**Description:** KagamiOS runs each investigation through six working states (Frame, Map, Deepen, Synthesize, Locate, Propose) in nominal order, with backward transitions and per-cluster state divergence both treated as normal operation rather than exceptions. A fixed set of three human-only decisions (the constitutive triad) can never be automated away regardless of how much the researcher trusts the system. Realizes UJ-1, UJ-2.

#### FR-1: Six-state nominal progression with defined loop-backs
The system moves a run through Frame → Map → Deepen → Synthesize → Locate → Propose → the Decide gate, and supports the specific defined backward transitions (e.g., Deepen→Frame, Synthesize→Map, Locate→Deepen, Locate→Map, Propose→Locate, and post-decision Decided→Propose on staling).

**Consequences (testable):**
- Every state transition, forward or backward, is logged as a `state_transition` event.
- Every backward transition carries a mandatory one-line cause annotation before it is accepted.
- Any state can transition directly to Dissolved or Dormant; there is no requirement to pass through all six states to reach either terminal.

#### FR-2: Skipping a state requires an explicit waiver
A researcher may skip a working state, but only by recording a one-line waiver at the time of the skip.

**Consequences (testable):**
- A run with a skipped state and no waiver on record is a data-integrity violation the system can detect and flag.

#### FR-3: Per-cluster derived state
The system computes each cluster's actual state independently as the earliest working state whose exit criteria that cluster hasn't met, and computes the run's nominal state as the modal cluster state.

**Consequences (testable):**
- Two clusters in the same run can be shown as being in different states simultaneously.
- Generation-window and gate-placement logic (§4.3) reads the per-cluster derived state, never the run-level nominal state alone.

#### FR-4: Constitutive triad is mechanically human-only
Three decisions — scope and attention allocation, gap meaningfulness, and direction selection — can only be made by the researcher, enforced by field-level write-guards (§4.5), not by convention.

**Consequences (testable):**
- No AI-authored value ever appears in a field tagged as belonging to the constitutive triad; an attempted AI write to such a field is rejected at the storage layer, not just discouraged by prompt.
- This restriction has no "trusted mode" override — unlike other review gates (FR-5), it cannot be loosened at any trust level.

#### FR-5: Review gates may be loosened to a notification, only with explicit researcher approval
For non-constitutive gates, the system may propose collapsing a review gate into a notification, grounded in that researcher's own aggregated edit history, but only takes effect after the researcher approves it.

**Consequences (testable):**
- No gate loosens without a recorded researcher approval event.
- The proposal to loosen a gate cites the specific aggregated statistic that motivated it.

#### FR-6: Entering mid-machine backfills minimum viable context
A researcher can start a run from any of five entry points (intuition-first, paper-first, field-first, problem-first, tool-first); the system backfills a minimal Intuition Note and Inquiry Frame so every run is rooted in the artifact graph the same way regardless of entry mode.

**Consequences (testable):**
- A run started from any of the five entry modes has a non-empty Intuition Note and Inquiry Frame before the Map state begins.

#### FR-7: Dissolution and Dormancy are first-class terminal outcomes
A run can end at Dissolved (the intuition doesn't survive scrutiny, documented in a Dissolution Memo) or Dormant (parked with explicit revival conditions and continued monitoring) with the same standing as ending at Decided.

**Consequences (testable):**
- Reaching Dissolved produces a complete Dissolution Memo, not merely a run marked "abandoned."
- A Dormant run continues to receive monitoring updates and is reopened at the affected state at the next session following a staling alert (monitoring runs as a sweep on session start, not a background daemon — see architecture spine AD-24).

#### FR-8: Post-decision staleness reopens the affected state, not a new run
Once a run reaches Decided, monitoring continues; if new evidence stales the Direction Decision, the system alerts the researcher and reopens the *existing* run at the affected state rather than starting fresh.

**Consequences (testable):**
- A staling alert references the specific artifact(s) that went stale and reopens the run at the state that produced them.
- A genuinely new intuition never reuses an old run — it always starts a new one, though it may cite prior artifacts.

### 4.2 Artifact System
**Description:** Every KagamiOS artifact is a human-editable, version-controllable Markdown file with frontmatter — never a database row — carrying a common metadata schema, a strict draft-to-accepted lifecycle, and section-level provenance so the system always knows which spans a human touched. Realizes the trace that both UJ-1 and UJ-2 depend on for a defensible decision or a documented dissolution.

#### FR-9: Common metadata on every artifact
Every artifact carries `id`, `type`, a monotonic immutable `version`, `status`, `depends_on`, `elicited_from`, `decided_by`, a 5–10 line `summary`, and `created`/`updated` timestamps.

**Consequences (testable):**
- An artifact missing any required metadata field fails validation and cannot reach `accepted` status.
- `version` numbers never decrease and are never reused, even after edits are reverted.

#### FR-10: Draft-to-accepted lifecycle with a human gate
An artifact moves `draft` (AI-written) → `reviewed` → `accepted` (human gate); the `current` pointer always resolves to the latest *accepted* version, never a draft.

**Consequences (testable):**
- No AI-authored draft is ever treated as `current` by any downstream consumer.
- Superseded versions are retained, never deleted, so any prior state is reconstructable.

#### FR-11: Section-level acceptance and addressing
Every artifact section has a stable ID; the artifact as a whole is `accepted` only once every minimal-profile section is accepted; sections are the unit for repair, retrieval, parallel-worker ownership, and citation.

**Consequences (testable):**
- A citation (`elicited_from`, `depends_on`) can pin to a specific section ID, not just the whole artifact.
- Two parallel workers writing to the same artifact never write to the same section simultaneously.

#### FR-12: Field-level authorship and edit preservation
Every field carries an author class (`ai`, `human`, or `ai-drafted-human-confirmed`); a human edit to an AI-authored span flips that span's author class permanently, and automated repair may not silently overwrite a human-touched span.

**Consequences (testable):**
- Repair proposes a diff for review on any human-touched span rather than overwriting it outright.
- Querying an artifact's provenance returns, per field, which class authored the current value.

#### FR-13: Staleness marks eagerly, repairs lazily
When a pinned dependency's source is re-accepted at a newer version, every artifact pinning the old version is marked stale immediately; regeneration happens only when the scheduler's frontier next needs that artifact.

**Consequences (testable):**
- Marking a dependent stale is a pure, cheap graph traversal with no LLM call involved.
- A stale artifact that the frontier never revisits is never regenerated — the system does not eagerly "catch up" work nobody asked for.

#### FR-14: Full artifact catalog plus five infrastructure stores
The system implements the full catalog: nine working artifacts (Intuition Note, Researcher Profile, Inquiry Frame, Confidence Checklist, Field Map, Cluster Dossier, Landscape Synthesis, Gap Register, Candidate Direction) plus two terminal artifacts (Direction Decision, Dissolution Memo — §3), and five infrastructure stores (Question Ledger, Corpus Cache, Entity Registry, Run Manifest, Run Event Log) sharing the same ID space. `[NOTE FOR PM: docs-spec/README.md refers to "ten artifacts" while 04_artifacts.md §2 enumerates eleven — this PRD counts explicitly (9 working + 2 terminal = 11) rather than repeat the source's own ambiguous headline number.]`

**Consequences (testable):**
- Each artifact type validates against its own schema in the registry (§4.5); an artifact of one type can never be accepted against another type's schema.
- Infrastructure stores are queryable by the same ID mechanism as researcher-facing artifacts.
- The Direction Decision's handoff bundle always includes both the artifact graph and a generated two-page portfolio brief (see Glossary).

#### FR-15: Per-state consumption map
For each working state, the system defines which artifacts it reads, and at what resolution (full text vs. summary only).

**Consequences (testable):**
- A state never reads an artifact type outside its defined consumption map.
- A "summary only" consumption is logged distinctly from a "full text" pull (feeds FR-33's summary-sufficiency signal).

#### FR-16: Minimal-run profile
Every schema field is marked `profile: minimal` or `profile: full`; a minimal-profile run requires only the defined minimal subset across all artifacts, targeting a days-scale run rather than a weeks-scale one.

**Consequences (testable):**
- A run can be validated and accepted end-to-end using only minimal-profile fields, with every full-profile field legitimately empty.
- MVP (§7) implements exactly this profile — see §7.1.

### 4.3 Elicitation Kernel and Question Scheduling
**Description:** The kernel is the scheduler for the entire system: there is no separate chat surface. It derives candidate questions from the gap between an artifact-in-progress and its schema, triages them into computable / human-only / deferrable, and only ever surfaces the human-only-and-blocking ones, in small ranked batches, always against evidence the researcher can see. Realizes UJ-1's question-batching beats.

#### FR-17: Three-way unknown triage
Every unknown the system encounters while building an artifact is classified as Computable (the system resolves it itself), Human-only (a candidate question, but only if it's also blocking), or Deferrable (an AI default is applied and recorded). The operational test for Human-only is: would two equally competent researchers, given the same corpus, answer this differently?

**Consequences (testable):**
- No unknown reaches the researcher as a question unless it is both human-only and blocking.
- Every deferred unknown's applied default is recorded in the Question Ledger even though no question was asked.
- A triage decision can be checked against the two-researcher test as a documented rationale, not left as an unexplained classification.

#### FR-18: Six-step kernel loop with a fixed frontier priority
The loop runs FRONTIER (select next work by fixed priority: blocking-next-gate, then stale repairs on the active path, then checklist holes, then deferred work) → ATTEMPT → TRIAGE → ASK (batch of at most 5, ranked by leverage) → CONSUME (write the answer to the ledger, pin `elicited_from`, mark dependents stale) → repeat, until the Decide gate closes or the intuition dissolves.

**Consequences (testable):**
- Every FRONTIER selection logs which of the four priority classes it came from.
- No ASK batch ever exceeds 5 questions.
- Every CONSUME event pins the answering ledger entry into the consuming artifact's `elicited_from`.

#### FR-19: Editing a draft is itself an elicitation event
When a researcher edits an AI-authored draft directly, that edit resolves the corresponding unknown and flips the edited span's provenance to human-confirmed (see FR-12) — the system does not also separately ask the question the edit already answered.

**Consequences (testable):**
- An edited span never generates a redundant confirm-the-default question afterward.

#### FR-20: No silent blocking; provisional flag on unanswered blockers
If a blocking unknown goes unanswered, the system applies its recorded default, flags the resulting artifact `provisional`, and surfaces the total provisional count at the Decide gate rather than halting silently.

**Consequences (testable):**
- A run can reach the Decide gate with provisional artifacts; the gate displays the provisional count explicitly rather than hiding it.
- No state transition silently stalls waiting on an unanswered question with no visible flag.

#### FR-21: Single-threaded ASK step
Even though parallel workers (Deepen's per-cluster workers, Map's search fan-out) may each emit candidate unknowns concurrently, exactly one scheduler owns batching and sequencing of what actually reaches the researcher.

**Consequences (testable):**
- Two questions from different parallel workers never reach the researcher in the same turn without having passed through the single ASK scheduler's batching and ranking.

#### FR-22: Well-formed questions only
A question may reach the researcher only if it declares a target (the specific artifact field it resolves) and a leverage class; the only exception is the two unprimed E6 questions (FR-24), which are allowed empty evidence.

**Consequences (testable):**
- Every Question Ledger entry other than the two unprimed questions has a non-empty target and leverage class.
- A candidate unknown missing a target or leverage class is computed, defaulted, or dropped — never asked as-is.

#### FR-23: Cheapest question form first
Questions are posed in ascending cost order: confirm-a-default, then menu, then rank/allocate, with free text reserved for cases the cheaper forms can't express.

**Consequences (testable):**
- No question uses free-text form unless a confirm/menu/rank form was considered and rejected as insufficient for that specific unknown.

#### FR-24: Ask-before-show for the two unprimed questions
At Frame and at Propose, the researcher's own unprimed answer is recorded in the ledger *before* any AI-generated output for that state is displayed to them.

**Consequences (testable):**
- The ledger timestamp for each of these two questions' answers is always earlier than the timestamp of the corresponding AI output being shown.
- The diff between the researcher's unprimed answer and the eventual AI framing is visible at the Decide gate.

### 4.4 AI Role Contracts
**Description:** Five roles define what different parts of the system are permitted and forbidden to do — behavioral contracts enforced by write permissions and generation windows, not character or persona. Realizes UJ-2's Skeptic-flags-a-dead-end beat.

#### FR-25: Scout is the sole corpus-touching role
Only the Scout role queries the raw literature corpus — preprints and code repositories and workshop venues, not published papers alone — every other role works from paper cards, dossiers, or other already-processed artifacts.

**Consequences (testable):**
- No non-Scout LLM call in the event log shows a raw-corpus retrieval; all raw-corpus retrievals are attributed to Scout.
- Scout's search scope includes preprint servers and code repositories, not just indexed publication venues; a Field Map built without checking these is incomplete by this FR's own standard.

#### FR-26: Cartographer must offer at least two structurally different cuts
Every Field Map clustering pass produces at least two genuinely different ways of partitioning the field, and the researcher (not the system) decides which to use or how to edit it; cluster names are always human-editable.

**Consequences (testable):**
- A Field Map draft with only one proposed clustering fails validation.
- A human-edited cluster name is never silently reverted by a later repair pass.

#### FR-27: Skeptic attacks only, with a fresh context
The Skeptic role may only critique existing framings, clusterings, gaps, or candidates — it never proposes an alternative — and it always runs from a fresh context, never the drafting rationale of the artifact it's attacking.

**Consequences (testable):**
- No Skeptic-authored output ever appears as an accepted value in a constitutive-triad field (would violate FR-4) or as a Candidate Direction.
- Every Skeptic invocation's context window excludes the target artifact's authoring conversation.

#### FR-28: Historian is confined to the Evolution section
The Historian role writes only the Cluster Dossier's Evolution section (founding problem, phase shifts, abandoned branches) and is forbidden from any frontier-facing speculation.

**Consequences (testable):**
- No Historian-authored content appears outside the Evolution section of any dossier.
- Frontier-speculative content attributed to the Historian role is a generation-window violation, logged as such.

#### FR-29: Every LLM call is tagged with its acting role and auditable against that role's charter
Each LLM call in the run event log records which role it was made under, so a charter violation (e.g., Scout producing interpretation, Skeptic proposing an alternative) is a checkable fact against the log, not a matter of judgment.

**Consequences (testable):**
- Every `llm_call` event has a non-null role tag.
- A charter-violation audit can be run mechanically against the event log without re-reading transcripts.

### 4.5 Runtime Contracts: Identity, Versioning, Write-Guards, and Retrieval
**Description:** The substrate that makes the rest of the system trustworthy: a machine-readable schema per artifact type, hard write-guards protecting human-owned fields, a single stable ID space, and retrieval rules that keep each state's context bounded and predictable.

#### FR-30: Schema registry with per-field metadata drives validation
Each artifact type has one versioned, machine-readable schema; each field in it declares `type`, `profile` (minimal/full), `author` class, and (where relevant) `unknown_class_hint` and `leverage`.

**Consequences (testable):**
- An artifact cannot be marked `accepted` if it fails validation against its type's current schema.
- Schema changes are themselves versioned, so an old artifact's validating schema version is always recoverable.

#### FR-31: Write-guard rejects AI writes to human-only fields, with no role override
The artifact store mechanically refuses any AI-originated write to a field marked `author: human`, regardless of which role is attempting the write.

**Consequences (testable):**
- An attempted AI write to a human-only field is rejected at the storage layer and logged as a rejected-write event, not silently dropped or silently allowed.

#### FR-32: Stable identity and versioning across the whole system
Every artifact, ledger entry, paper card, entity, and trace event shares one ID space with stable `id`s and monotonic immutable `version`s; `depends_on` and `elicited_from` pin the specific version referenced at the time of consumption.

**Consequences (testable):**
- Staleness (FR-13) is decidable purely by comparing a pinned version number to the current accepted version — no content diff required to detect it.
- Two parallel writers never receive the same new ID.

#### FR-33: Context loading contract — summaries by default, full text only on demand
Every artifact carries a 5–10 line summary regenerated only on acceptance; consuming states read the summary by default per the per-state consumption map (FR-15), and a full-text pull is always an explicit, logged action.

**Consequences (testable):**
- A full-text pull event is distinguishable in the log from a summary-only read.
- A high rate of full-text pulls immediately following a summary read for the same artifact is a detectable signal (feeds §8's summary-sufficiency metric).

#### FR-34: Retrieval boundary — each state reads only the layer below it
A working state may read artifacts from the immediately preceding layer only; it never reaches past that layer to the raw corpus directly (raw-corpus access is Scout-only, per FR-25), and there is no embedding index over the artifact graph itself.

**Consequences (testable):**
- No non-Scout retrieval event targets the raw corpus.
- The artifact-graph retrieval layer supports graph traversal queries only; a vector-similarity query against artifacts is not a supported operation in v1.

#### FR-35: Sectional repair pipeline
Repair on a stale artifact runs a tiered check — a cheap deterministic dependency check first, then a cheap-model plausibility check, and only then regenerates the specific sections that actually fail — rather than regenerating the whole artifact.

**Consequences (testable):**
- A repair that only needed the Tier 0 deterministic check never invokes a model call.
- Regeneration output is scoped to the failing section IDs, never the whole artifact, when only some sections fail.

### 4.6 Observability and Self-Measurement
**Description:** KagamiOS logs enough about its own runs to be improved by a human design owner later, without ever letting that telemetry change its own runtime behavior. Self-measuring, never self-modifying.

#### FR-36: Run event log is write-only during a run
The event log records every `llm_call`, `retrieval`, `artifact_event`, `question_event`, `human_edit`, `frontier_decision`, `gate_event`, `budget_event`, `state_transition`, and `terminal_event`, and no runtime behavior may read it back during that same run — a run with its trace deleted afterward behaves identically to one with the trace intact.

**Consequences (testable):**
- Deleting a completed run's event log has zero effect on any other run's behavior.
- The one sanctioned exception (gate-loosening proposals, FR-5) reads only derived aggregates, never raw events, and only with researcher approval.

#### FR-37: Deterministic per-run derived metrics
At each gate and at the terminal, the system computes question economics, a token ledger (including summary-sufficiency), an override profile, and a decision block (candidate origins, unprimed-vs-final diff, provisional count at Decide, falsifiable claims as trace objects) — all as deterministic computation, not LLM judgment.

**Consequences (testable):**
- Re-running the metric computation over the same event log always produces the same numbers.
- The provisional count shown at Decide (FR-20) matches the derived metric exactly.
- At each gate, the token ledger is compared against a researcher-set soft limit in `config.yaml`; exceeding it adds a warning to the decision block, never a block on proceeding — this is deterministic reporting at an existing checkpoint, not the live budget enforcement §5 defers (added 2026-07-03, §4.8).

#### FR-38: Cross-run corpus is derived and rebuildable, never ground truth
Run summaries accumulate into a local analytics store used for cross-run analysis; this store can be deleted and rebuilt from the per-run event logs at any time without data loss.

**Consequences (testable):**
- Deleting the cross-run analytics store and rebuilding it from retained event logs reproduces the same store.

#### FR-39: Trace privacy — local-first, opt-in sharing, content-stripped aggregation
Traces are local-first and researcher-owned by default; any lab- or advisor-level aggregation is strictly opt-in, and when shared, only event shapes/counts/classes travel — question text, artifact content, and paper identities never leave the researcher's own store.

**Consequences (testable):**
- With opt-in sharing disabled (the default), no event data leaves the researcher's local store.
- With opt-in sharing enabled, an inspection of the shared payload contains no verbatim question text, artifact content, or paper titles/authors.

#### FR-40: Design Audit Report loop is human-gated
Periodically (every N runs, or quarterly), deterministic jobs over the cross-run corpus produce a Design Audit Report citing specific trace evidence; a human design owner reads it and decides whether to make a spec change — the system never applies a finding automatically.

**Consequences (testable):**
- No schema, gate, prompt, or question-class classification changes as a direct, automatic consequence of a Design Audit Report; every such change traces to a human-approved decision that cites the report.

#### FR-41: Anti-Goodhart pairing on efficiency findings
Every efficiency-oriented finding in a Design Audit Report ships paired with its quality guard in the same report; if the guard moved the wrong way, the finding is reported as a regression, not a saving.

**Consequences (testable):**
- No Design Audit Report contains an efficiency finding without an adjacent quality-guard reading for the same period.
- Quality-guard metrics (e.g., falsification rate, post-decision staleness rate) never appear framed as something to be maximized — see §8's framing note.

### 4.7 Propose, Decide, and Self-Improvement Guardrails
**Description:** The mechanics of how candidates get compared and how a run actually closes at Decide — plus the specific guardrails that stop the Design Audit Report loop (§4.6) from ever eroding the researcher's own judgment. These requirements are what stop "3–5 candidates" from quietly becoming a ranked list, and what stop "self-measuring" from quietly becoming "self-adjusting the parts that were never supposed to move." Realizes UJ-1's Propose/Decide beats.

#### FR-42: Candidate comparison uses a fixed qualitative table with no aggregate score
Propose presents 3–5 Candidate Directions on one fixed qualitative table — the same axes for every candidate (gap/evidence strength, why-now, requirements vs. researcher profile, strongest objection) — and computes no aggregate score across those axes.

**Consequences (testable):**
- No numeric or ranked "top candidate" is ever computed or displayed; the table's axes are identical across all candidates shown.
- The researcher writes, in their own words, why the selected candidate wins over the others — this text is stored on the Direction Decision, not inferred from the table.

#### FR-43: Candidates are red-teamed in parallel before Decide
Each Candidate Direction is attacked by the Skeptic role in a fresh, isolated context (per FR-27) before Decide; the resulting red-team notes are attached to the candidate and, for rejected candidates, harvested into the Direction Decision's `rejection_reason`.

**Consequences (testable):**
- Every candidate reaching the comparison table (FR-42) has non-empty red-team notes attached.
- Every candidate marked `rejected` on the Direction Decision has a `rejection_reason` traceable to its red-team notes.

#### FR-44: Decide gate exit criteria, including the human-read requirement
The Decide gate does not close until: the Confidence Checklist is trace-complete, the comparison table (FR-42) is written, every candidate has a recorded disposition (selected/parked/rejected/spawned), the representative papers behind each surviving candidate carry a `human_read` flag with a one-line human reaction, and the decision is signed by the researcher.

**Consequences (testable):**
- A Direction Decision cannot reach `accepted` status while any surviving candidate's representative papers are missing a `human_read` flag.
- The full exit-criteria checklist (checklist trace-complete / comparison written / dispositions recorded / human-read complete / signed) is checkable mechanically against artifact state, not left to reviewer judgment.

#### FR-45: Depth budgets are set at Map exit and their exhaustion asks, never silently stops or silently continues
At Map exit, the researcher sets depth budgets per cluster (how many clusters to deepen, how many papers per cluster, a soft time horizon); these are human-owned and revisable at any point. When a budget is exhausted, the system asks a specific extend-or-proceed question rather than silently stopping or silently continuing past it.

**Consequences (testable):**
- Every run has recorded depth budgets before Deepen begins.
- Every budget-exhaustion event produces exactly one extend-or-proceed question in the ledger — never a silent continuation and never a silent halt.

#### FR-46: Generation-window enforcement is binding, not advisory
No direction-shaped content (see FR-22's leverage-class framing and the Candidate Direction artifact) may be generated anywhere in the system until the run-level Gap Register is accepted. Content generated in violation of this is quarantined to a `premature_ideas` bucket rather than being discarded or allowed to leak into a legitimate artifact.

**Consequences (testable):**
- No Candidate Direction artifact has a `created` timestamp earlier than its run's Gap Register acceptance timestamp.
- Any generation-window violation produces a `premature_ideas` entry rather than a silently dropped or silently accepted artifact.

#### FR-47: Constitutive-triad fields and the two unprimed E6 questions are permanently exempt from Design Audit statistical demotion
The Design Audit Report loop (FR-40, FR-41) may recommend process-form changes based on aggregate statistics, but the constitutive-triad fields (FR-4) and the two unprimed ask-before-show questions (FR-24) can never be demoted, reclassified, or streamlined by that loop regardless of what the statistics show.

**Consequences (testable):**
- No Design Audit Report recommendation, however adopted, ever changes the human-only status of a constitutive-triad field or removes either unprimed question from the run.
- This exemption is checkable directly against the audit-adoption log (FR-40): an adopted change touching either category is a process violation, not a valid outcome.

### 4.8 Driver & Harness Shell
**Description:** `[ASSUMPTION: this section originates from implementation-readiness review, not docs-spec/, added 2026-07-03 — see §0.]` Sections 4.1–4.6 specify a deterministic core that refuses illegal outcomes; something outside it has to actually drive a run — open it, dispatch roles, call models, and report back. Most of that driver behavior is already specified as product requirement (FR-17..24's elicitation loop, FR-25..29's role charters, FR-33/34's read-set boundaries); this section covers the two driver-side behaviors that surfaced as gaps only once the harness itself was scoped for implementation, and that need mechanical enforcement rather than prompt convention to be trustworthy at all.

#### FR-48: Refusal-retry ceiling with mandatory escalation
The system tracks consecutive identical refusals against the same target; past a fixed ceiling, the next identical attempt returns a distinct escalation status instead of an ordinary refusal, forcing a stop-and-surface-to-the-researcher outcome rather than an unbounded retry loop.

**Consequences (testable):**
- N consecutive identical refusals against the same target always produce the escalation response on attempt N+1 — never a silent Nth ordinary refusal, and never an N+2th retry.
- The escalation is enforced mechanically, not by harness/prompt logic — a scripted driver issuing the same call sequence produces the same escalation.

#### FR-49: Every model invocation is reported through a validated entrypoint
Whatever drives the system reports every model call it makes — role, operation class, model tier, token counts, cache-hit status — through a validated entrypoint immediately after the call; the deterministic core never invokes models itself and never infers these fields.

**Consequences (testable):**
- Every `llm_call` event in the run event log (FR-36) was written by this entrypoint, not fabricated or inferred after the fact.
- A model call made but never reported is invisible to the token ledger (FR-37) and the charter audit (FR-29) — an accepted, logged gap (self-reporting is detect-and-audit, not prevent), never silently corrected or hidden.

## 5. Cross-Cutting NFRs

- **Platform: Claude Code plugin, BMAD-ecosystem native** (researcher decision, 2026-07-02). KagamiOS installs and runs as a Claude Code plugin, co-installable with BMAD and following its layout conventions (skills + deterministic scripts + hooks). The mechanical guarantees in §4 (write-guards, generation windows, ASK batching, event logging) are implemented as deterministic code *inside* the plugin — a script chokepoint that is the only sanctioned mutation path, with hooks blocking direct AI writes to the artifact store — never as prompt convention. Two accepted v1 trade-offs of this platform: main-thread token/prompt accounting is incomplete, and scheduler obedience is detect-and-audit rather than prevent; both are acceptable only because illegal state mutation remains mechanically impossible and every deviation is auditable. The deterministic core must remain standalone-capable as a library, so a future non-plugin runtime is an adapter, not a rewrite.
- **Auditability by construction.** Every mechanically enforceable rule in §4 (write-guards, generation windows, role charters, gate approvals) must be checkable against the run event log after the fact, not just assertable as an intended behavior. This is why FR-29, FR-31, and FR-36 exist as explicit requirements rather than being left as implementation detail.
- **Determinism before generation, always.** Wherever a value can be computed deterministically (staleness, provisional counts, derived metrics, per-run summaries), it must be computed deterministically — never inferred by a model call. This governs FR-13, FR-32, FR-37.
- **Privacy is local-first by default, not opt-out.** Sharing is opt-in and content-stripped, never the reverse (FR-39). No design-analytics feature may require sharing to function for a single researcher.
- **Cost discipline via retrieval boundaries, not budgets.** v1 controls token/compute cost primarily through the context loading contract and retrieval boundary (FR-33, FR-34), not through live budget enforcement — machine-side budgets and meters are explicitly deferred (see `addendum.md` A4, trigger O6). FR-37's gate-time soft-limit warning (§4.8) is deterministic reporting at an existing checkpoint, not live enforcement, and does not itself trigger O6 — it is intended to produce the usage evidence O6's adoption trigger is waiting for.
- **No silent data loss.** Superseded artifact versions are retained (FR-10); human-touched spans are never silently overwritten (FR-12); rejected writes are logged, not dropped (FR-31).
- **Provider resilience.** Literature-provider adapters (FR-25) implement backoff/retry against each provider's documented rate limits so transient throttling surfaces as a retry, never as a run-ending error (added 2026-07-03, §4.8's driver scope).

## 6. Non-Goals (Explicit)

KagamiOS v1 explicitly will not:

1. **Use anthropomorphic AI personas.** Roles are behavioral contracts with no name or character — character increases researcher deference, which the anchoring-discipline principle (E6) exists specifically to prevent.
2. **Treat the candidate portfolio as the terminal event.** The terminal event is the researcher's confident selection; the portfolio structure is the *format* of the resulting artifact, not the thing that ends the run.
3. **Build a first-class knowledge hierarchy.** Fields are not trees. The entity registry plus the artifact graph cover the need; a tree-shaped view may be rendered over them later (deferred, see `addendum.md`) but is never the underlying data model.
4. **Use a database as ground truth.** Artifacts are Markdown files with frontmatter; every other store is derived and rebuildable from them.
5. **Build a RAG or vector index over the artifact graph.** Retrieval over artifacts is graph navigation only; embedding search exists solely inside the corpus tier, behind the Scout role.
6. **Mechanically auto-close the Decide gate, or let analytics modify the system automatically.** The system is self-measuring, never self-modifying (FR-40) — no auto-reclassification of questions, auto-loosened gates beyond FR-5's researcher-approved path, auto-edited schemas, or auto-tuned prompts.
7. **Support any lifecycle stage beyond the bounded micro-probe.** Experiment design, implementation, execution, and writing are all out of the system boundary; the micro-probe (hours-bounded, evidence for exactly one Gap Register field) is the sole, deliberately narrow exception.
8. **Build a learned or adaptive routing layer.** The deterministic/cheap-model/frontier-model dispatch table (`addendum.md` A2) is static and human-maintained until multi-run cost data justifies revisiting this.
9. **Auto-enforce stopping.** Depth budgets and the Confidence Checklist convergence test are advisory signals the researcher can act on; the system never halts a run automatically on their basis.
10. **Serve labs or multi-researcher teams as a shared gate in v1.** See §2.2 Non-Users. An advisor consumes the finished bundle; they never gate a run from inside it.

*(Full rationale and originating review documents for each item: `addendum.md` A7.)*

## 7. MVP Scope

### 7.1 In Scope

**Decision (2026-07-02, researcher):** MVP covers the states Frame → Map → Deepen → Synthesize → Locate, ending at an accepted Gap Register. Propose and the Decide gate are v2. Within that boundary, MVP targets the **minimal-run profile** (FR-16):

- Intuition Note capture, all five entry modes (FR-6).
- Inquiry Frame including its menu-form scope question, and the Frame-state unprimed question (FR-24, Frame side only).
- Field Map including its two-cut clustering requirement, recency profile, and one cluster-selection question (FR-26).
- One Cluster Dossier per in-scope cluster, including the mandatory Evolution section and `human_read` flags on representative papers (FR-28; the Deepen exit criterion — the *Decide-side* human-read audit in FR-44 is v2).
- Landscape Synthesis at minimal-profile depth (the solved/open table with evidence-of-openness, not the full competing-approaches matrix).
- Gap Register including both the `why_does_this_gap_exist` screen and the human `meaningful_to_me` mark. **An accepted Gap Register is MVP's terminal deliverable.**
- Question Ledger as an append-only log (FR-18, FR-22).
- The five working states above with their loop-backs (§4.1), the elicitation kernel (§4.3), the constitutive-triad write-guards for the two triad decisions that occur in-scope — scope/attention and gap meaningfulness (FR-4, FR-31) — depth budgets (FR-45), generation-window enforcement (FR-46, which in MVP means *no* direction-shaped content is ever legitimate, since Propose doesn't exist yet), and the run event log (FR-36).
- Terminals reachable in MVP: **Dissolved and Dormant.** Decided is unreachable by construction — it requires the Decide gate. A v1 run that completes its Gap Register simply rests there (or goes Dormant) until v2 adds Propose/Decide.

### 7.2 Out of Scope for MVP

- **Propose state and Decide gate, and everything that exists only for them** (researcher decision, 2026-07-02): Candidate Direction and Direction Decision artifacts, the fixed comparison table (FR-42), candidate red-teaming (FR-43), Decide exit criteria (FR-44), the Propose-side unprimed question (FR-24), post-decision monitoring/staling reopens (FR-8), and the direction-selection leg of the constitutive triad (FR-4). These remain product requirements — v2 implements them; nothing in v1's architecture may preclude them.
- **Landscape Synthesis full-profile fields.** Minimal-profile only for MVP; full-profile depth is a post-MVP accretion per FR-16.
- **Cross-run corpus and Design Audit Report loop (§4.6, FR-38, FR-40, FR-41).** Requires accumulated runs to be meaningful; not buildable-and-testable until multiple minimal-profile runs exist. *[NOTE FOR PM: this means MVP cannot validate its own self-improvement loop — plan a second phase specifically to accumulate the N runs this needs.]*
- **Role-labeled voice / visibly adversarial Skeptic register (O1).** Adopt at first UI pass — deferred, not because it's hard, but because it's presentation polish over a mechanism that must work headless first.
- **Prompt-cache prefix ordering discipline (O2/O5).** Adopt at first implementation pass, not required to validate the minimal-run profile itself.
- **Machine-side token budgets and live meters (O6).** Deferred until the cost ledger (once it exists) shows a state chronically overrunning.
- **Hierarchy view, named research-lines subsection, live stall surfacing, controlled question-form experiments (O3, O4, O7, O8).** All deferred with their own adoption triggers — see `addendum.md`.
- **Multi-researcher / advisor-as-gate support.** See Non-Goal #10.
- **Learned/adaptive dispatch routing, vector index over artifacts, speculative pre-generation, distributed execution.** See Non-Goal #8 and `addendum.md` A4 — considered and explicitly rejected for now, not merely deprioritized.

## 8. Success Metrics

*Framing note, load-bearing: the spec is explicit that quality/robustness signals are guardrails that **veto** efficiency changes, never targets to optimize upward on their own. The Primary/Secondary/Counter-metric split below preserves that distinction; do not restructure it into a single scorecard where quality metrics compete with speed metrics for "best number."*

*MVP measurability note: with Propose/Decide deferred to v2 (§7.1), the decision-anchored metrics — SM-1, SM-2, SM-5, SM-C1, SM-C2 — cannot be measured until v2. MVP's live metrics are SM-3 (dissolution speed), SM-4 (question rent), SM-6 (voluntary reuse), SM-C3 (charter violations), plus a v1 interim analogue of SM-1: time from Intuition Note to an accepted Gap Register.*

**Primary**
- **SM-1**: Time-to-confident-decision — wall-clock time from Intuition Note to a signed Direction Decision. Target: weeks, not months, for a full-profile run; days for a minimal-profile run. Validates FR-16, the state machine (§4.1) as a whole.
- **SM-2**: Checklist self-recall — at Decide, the researcher can answer every Confidence Checklist entry from memory (communities, defining papers, competing approaches, why each surviving gap exists) without re-reading source artifacts. Validates FR-15 (consumption map), the Confidence Checklist mechanism.
- **SM-3**: Dissolution speed — wall-clock time from Intuition Note to a signed Dissolution Memo, for intuitions that don't survive scrutiny. Target: days. Validates FR-7.

**Secondary**
- **SM-4**: Question rent — proportion of Question Ledger entries whose answer is actually consumed by a downstream artifact (`consumed_by` populated), vs. asked-and-unused. Validates FR-18, FR-22.
- **SM-5**: Handoff completeness (resumption test) — a downstream reader given only the Direction Decision bundle can answer the Confidence Checklist without re-interviewing the researcher. Validates the Direction Decision artifact and FR-33's summary contract.
- **SM-6**: Voluntary reuse — the researcher starts a second run on a new intuition without being prompted. A behavioral signal that the first run was worth the researcher's time, not just spec-compliant.

**Counter-metrics (guardrails — never optimize upward in isolation)**
- **SM-C1**: Decision robustness — post-decision literature work confirms rather than overturns the landscape a Direction Decision was based on, measured against the pre-registered falsifiable claims in that decision. Counterbalances SM-1: a faster decision that turns out wrong is a regression, not a win. Validates FR-37's decision block.
- **SM-C2**: Provisional-count at Decide — the number of provisional (unanswered-blocker-defaulted) artifacts a run reaches Decide with. Counterbalances SM-1 and SM-4: fewer questions asked is only good if it isn't achieved by silently defaulting through blockers. Validates FR-20.
- **SM-C3**: Charter-violation rate — instances where a role's output violates its own contract (§4.4), caught via the auditable event log (FR-29). Counterbalances any pressure to speed up generation by loosening role boundaries.

## 9. Open Questions

1. **OQ-A — RESOLVED (researcher decision, 2026-07-02): skip the hand-run validation; proceed directly to implementation.** The spec's recommended felt-test (`docs-spec/09_open_items.md` OQ1 — "does this feel like the system reading your mind, or a form?") will instead be answered by dogfooding the built MVP itself. Residual risk accepted: if the elicitation UX fails the felt-test, the fix lands as a design change against working software rather than against paper. See `addendum.md` A6.
2. **OQ-B (spec OQ2) — Does the event log actually measure counterfactual question rent?** The mechanism (differs-from-default rate, revision-cascade size) is buildable now; whether it tracks the thing it's meant to track is an open empirical question the spec defers to dogfooding data.
3. **OQ-C (spec OQ3) — Is the Field Map clustering anchor sufficiently mitigated?** Two-cut requirement, human naming, and Skeptic attack are all in scope (FR-26, FR-27) as mitigations; the spec is explicit that whether they're *sufficient* is fundamentally open, not something this PRD can resolve by building more mechanism.
4. **OQ-D (spec OQ4) — What should the eventual principled stopping rule be?** Depth budgets and the convergence test remain advisory only in v1 (Non-Goal #9); the event log this PRD requires (FR-36) is explicitly the dataset a future stopping rule would need, but the rule itself is not in scope.
5. **OQ-E (spec OQ5) — Should Researcher Profile entries age or require reconfirmation?** Annotate-never-filter is in scope (part of the Researcher Profile artifact, §3); aging/reconfirmation dynamics are explicitly deferred until the profile has survived at least two runs.
6. **OQ-F (spec OQ7) — How is quality evaluated at n≈1?** Pre-registered falsifiable claims (SM-C1) and late outcome joins are in scope; the underlying robustness test takes months per run to resolve, and the strongest quality signals will stay n-small for a long time. Accepted per spec: this is why quality metrics are vetoes, not targets (§8 framing note).

## 10. Assumptions Index

- §1 — Vision section is condensed PM-facing prose from `docs-spec/01_vision.md` ("The mirror," "Three consequences," "What KagamiOS is not") plus `02_principles.md` E6's homogenization framing; no new claims beyond the source.
- §2.3 — UJ-1 and UJ-2 personas (Asha, Marcus) and their specific narrative beats are invented illustrations; the spec itself names no example researcher beyond the anonymous Signature-methods dogfooding case (`addendum.md` A5).
- §4 (intro) — FR grouping into seven subsections (state machine, artifacts, elicitation, roles, runtime, observability, Propose/Decide-and-guardrails) is a PM-authoring choice for downstream traceability; the spec does not itself mandate this exact grouping, though it maps directly onto `docs-spec/`'s own document boundaries (03–08) plus a consolidated cluster for mechanisms that were originally scattered across `02_principles.md` and `03_state_machine.md`.
- §7.1 — ~~MVP scope assumption~~ **superseded by researcher decision (2026-07-02):** MVP runs through Gap Register only; Propose/Decide are v2. The hand-run validation question (OQ-A) was resolved by decision, not assumption — skip it and build.
- Stakes tier (Internal tool, ~5-8pg target) and working mode (Fast path) for this PRD run were defaulted without explicit user confirmation after a calibration question went unanswered; see `.memlog.md`. Implicitly ratified by the researcher's approval of this PRD as the implementation baseline (2026-07-02).
