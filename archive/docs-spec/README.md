# KagamiOS — Research Discovery OS: Consolidated Specification

**Status: normative.** This directory is the single source specification for KagamiOS implementation and for downstream BMAD-style planning. It consolidates and supersedes, for implementation purposes, the design in `docs-discovery/` as amended by the two audits in `docs-discovery-review/` and `docs-runtime-review/`. The source directories are preserved unchanged as the design record — rationale, alternatives considered, and review argumentation live there and are not repeated here.

## What KagamiOS is, in one sentence

KagamiOS transforms a vague research intuition into a small set of concrete, evidence-backed candidate research directions by doing the tractable landscape work automatically and asking the researcher only the questions whose answers change the outcome — terminating the moment the researcher confidently selects a direction.

## Document map

| Doc | Contents | Normative core |
|---|---|---|
| `01_vision.md` | Scope, endpoint, what the system is not, success criteria | The Direction Decision (portfolio-structured) as terminal artifact |
| `02_principles.md` | Design principles P1–P11 and E1–E8 | Every mechanism in this spec traces to a principle |
| `03_state_machine.md` | States, gates, loop-backs, terminals, budgets, stopping, derived-state function | Six working states + Decide gate + three terminals |
| `04_artifacts.md` | Artifact catalog, common metadata, infrastructure layer, consumption map, minimal-run profile | Ten artifacts + five infrastructure stores |
| `05_elicitation.md` | The kernel: unknown triage, the loop, question rent, cards, ledger, anchoring discipline | The scheduler of the whole system |
| `06_roles.md` | Role charters: Interviewer, Scout, Cartographer, Historian, Skeptic | Contracts, not personas |
| `07_runtime.md` | Schema registry, identity/versioning, context loading contract, repair pipeline, dispatch table, retrieval policy, parallelism | The implementation contracts |
| `08_observability.md` | Run event log, derived metrics, cross-run corpus, privacy, design analytics, governance | Self-measuring, never self-modifying |
| `09_open_items.md` | Remaining open questions and deferred optional features | Not normative |

Reading order for a new implementer: 01 → 03 → 05 → 04 → 07, then the rest. Reading order for BMAD planning: this README → 01 → 09 (what is still open) → the register below (what is already decided).

## Incorporation policy and provenance

The two audits produced a single recommendation register (M1–M6, S1–S16, O1–O8, D1–D10). Disposition in this spec:

- **Incorporated as normative** — all Must items and all Should-consider items. The user's directive in `4_questions.md` promoted S1 to must; both audits classified S2–S16 as "adopt unless dogfooding says otherwise," and this spec adopts them.
- **Deferred** — Optional items O1–O8, listed in `09_open_items.md` with their triggers.
- **Affirmed** — Do-not-change items D1–D10 are simply true of this spec; they are noted below only where an implementer might otherwise "improve" them away.

| Rec | Incorporated where |
|---|---|
| M1 Context loading contract (summaries, read-sets, retrieval boundary) | `07_runtime.md` §3; `04_artifacts.md` §1 §4 |
| M2 Staleness ≠ regeneration (lazy, diff-first, sectional repair) | `02_principles.md` P7; `07_runtime.md` §4 |
| M3 Cluster ≠ research group | `04_artifacts.md` (Field Map, Cluster Dossier); `03_state_machine.md` state table |
| M4 Machine-readable schema registry, write-guards, edit preservation | `07_runtime.md` §1 |
| M5 Identity, versioning, section addressing, pinned references | `07_runtime.md` §2; `04_artifacts.md` §1 |
| M6 Run event log + cost accounting | `08_observability.md` §2; `04_artifacts.md` §3 |
| S1 Candidates from gaps **and** synthesis evidence | `04_artifacts.md` (Candidate Direction); `03_state_machine.md` (Propose) |
| S2 Frontier corpus sources + recency profiles | `04_artifacts.md` (Field Map); `06_roles.md` (Scout) |
| S3 Micro-probe evidence + `probe_before_commit` | `04_artifacts.md` (Gap Register, Direction Decision) |
| S4 Role charters | `06_roles.md` |
| S5 Corpus cache / paper cards; compute-before-generate | `04_artifacts.md` §3; `02_principles.md` E8; `07_runtime.md` §5 |
| S6 Portfolio-structured Direction Decision; `rejection_reason` | `04_artifacts.md` (Direction Decision, Candidate Direction) |
| S7 Entity registry | `04_artifacts.md` §3 |
| S8 Minimal-run profile | `04_artifacts.md` §5; `07_runtime.md` §1 |
| S9 Run manifest + derived-state function | `03_state_machine.md` §5; `04_artifacts.md` §3 |
| S10 Scheduler priority order + frontier logging | `05_elicitation.md` §2; `08_observability.md` §2 |
| S11 Repair pipeline | `07_runtime.md` §4 |
| S12 Two-tier retrieval policy | `07_runtime.md` §6 |
| S13 Deterministic-vs-LLM dispatch table + model tiering | `07_runtime.md` §5 |
| S14 Parallel shard execution | `07_runtime.md` §7 |
| S15 Design Audit Report loop; form-not-content rule; anti-Goodhart pairing | `08_observability.md` §5–6 |
| S16 Trace privacy | `08_observability.md` §4 |
| O1–O8 | Deferred — `09_open_items.md` |
| D1–D10 | Affirmed throughout; see §"Standing refusals" below |

## Standing refusals

Decisions that were challenged during review and deliberately retained. An implementer proposing any of the following should read the corresponding review first:

1. **No anthropomorphic agent personas.** Roles are contracts (`06_roles.md`); character increases deference, and deference is the failure mode E6 exists to prevent. (`docs-discovery-review/2_agent_personas.md`)
2. **No portfolio *endpoint*.** The terminal event is the researcher's confident selection; the portfolio is the *format* of the terminal artifact, not the terminal semantics. (`docs-discovery-review/4_endpoint.md`)
3. **No first-class knowledge hierarchy.** Fields are not trees; the entity registry plus the artifact graph covers the need. A hierarchy may be rendered as a view. (`docs-discovery-review/5_knowledge_structure.md`)
4. **No database as ground truth.** Artifacts are Markdown files with frontmatter; all stores beyond them are derived and rebuildable. (`docs-runtime-review/1_runtime_contracts.md`)
5. **No RAG / vector index over the artifact graph.** Graph navigation only; embedding search exists solely in the corpus tier. (`docs-runtime-review/2_context_runtime.md`)
6. **No mechanical closure of the Decide gate, and no analytics-driven self-modification.** The system is self-measuring, never self-modifying. (`docs-runtime-review/4_design_analytics.md`)
7. **No lifecycle features.** Experiment design, implementation, execution, and writing are out of scope; the sole concession is the bounded micro-probe evidence type (`04_artifacts.md`, Gap Register).
