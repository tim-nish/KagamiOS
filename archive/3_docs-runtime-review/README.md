# KagamiOS v2 — Implementation & Runtime Design Review (Audit of `docs-discovery/`)

This directory answers `4_questions.md`. It is the runtime-facing sequel to `docs-discovery-review/`: the conceptual design in `docs-discovery/` is the untouched baseline, and this review asks only whether it is **specified precisely enough to build**, how it should behave at runtime, and how it should generate evidence about its own effectiveness. Nothing here proposes changing the state machine, the artifact model, or the elicitation kernel.

**Assumed incorporated** (per `4_questions.md`): the previous audit's M1 (context-loading contract), M3 (cluster ≠ group disambiguation), and S1 (candidate generation widened beyond the Gap Register — promoted to must by the user). One reconciliation note: the user's assumed list omits the previous M2 (staleness ≠ regeneration: lazy, diff-first, sectional repair), but question 2 explicitly names lazy regeneration, diff-based updates, and section-level regeneration as topics — so this review treats **M2 as incorporated as well** and specifies its runtime realization rather than re-arguing it.

Recommendation IDs continue the previous register (which ended at M3 / S8 / O4 / D6), so the two reviews read as one series.

## Reading order

| Doc | Question audited |
|---|---|
| `1_runtime_contracts.md` | Are the runtime I/O contracts precise enough to implement? What is specified, what is ambiguous? |
| `2_context_runtime.md` | Runtime context management beyond the loading contract — essential vs. useful vs. premature |
| `3_observability.md` | The trace architecture: how 100 runs generate evidence about the design |
| `4_design_analytics.md` | How KagamiOS evaluates and improves itself without corrupting itself |

## Verdicts at a glance

1. **Runtime contracts:** the conceptual layer is genuinely well specified (status lifecycle, dependency direction, question card and ledger schemas, consumption map) — but three contracts the design *presupposes* are never written down: machine-readable artifact schemas (the kernel's TRIAGE step literally diffs a draft against "its schema"), an identity/versioning/addressing model (staleness propagation is meaningless without knowing *which version* an artifact consumed), and enforcement of per-field human-only authorship (P3's triad is currently a convention, not a mechanism). All three are must-changes; all three are implementation-only — each mechanizes something the baseline already asserts.
2. **Context runtime:** five mechanisms are essential (the repair pipeline, the deterministic-before-LLM dispatch split, the summary lifecycle, the corpus cache, a two-tier retrieval policy); parallel shard execution and static model tiering are useful; RAG over the artifact graph, learned routing, and speculative generation are premature or wrong at this scale.
3. **Observability:** several baseline mechanisms already *require* telemetry the design never specifies collecting — the E2 rent audit, DQ2's rent proxies, DQ4's extend-or-proceed log, E6's led-or-followed diff. A structured run event log with unified IDs and per-call cost accounting is therefore a must: analytics can be added later, but telemetry that was never collected cannot be reconstructed. Traces are exhaust, never load-bearing state.
4. **Design analytics:** the system should be **self-measuring, never self-modifying** — analytics produce a periodic, human-read Design Audit Report whose proposals pass the same human gates as everything else. One new hazard this review names: tuning *content* defaults from aggregate researcher behavior is E6's homogenization failure at the population level. The safe rule: improve the process's **form** (when to ask, what to load, what to skip) from aggregate data; never its **content** (what to suggest) from other researchers' choices.

## Consolidated recommendation register (continues `docs-discovery-review/`)

| ID | Class | Recommendation | Affects (baseline) | From |
|---|---|---|---|---|
| M4 | **Must change** | Machine-readable schema registry: per-field type, minimal-profile requiredness, author class with human-only write-guards and human-edit preservation, unknown-class hint, summary membership | `artifacts.md` §1–2, `elicitation.md` §1, P3/E7 enforcement | Q1 |
| M5 | **Must change** | Identity, versioning, and addressing model: stable `id` + monotonic `version`, references pinned as `id@version`, stable section IDs, current-pointer semantics | `artifacts.md` §1, P7/E5 mechanics, M2's sectional repair | Q1 |
| M6 | **Must change** | Structured run event log with unified IDs and per-LLM-call cost accounting — the observability spine | new infrastructure beside the Question Ledger; makes `vision.md` criterion 5, DQ2, DQ4, E6's diff measurable | Q3 |
| S9 | Should consider | Run manifest + workspace layout + the derived-state function specified | `state_machine.md` §1, new run-level file | Q1 |
| S10 | Should consider | Frontier/scheduler priority order specified, and every frontier decision logged with its reason | `elicitation.md` §2, M6 | Q1/Q2 |
| S11 | Should consider | Repair pipeline runtime spec: repair queue, tiered diff-check, sectional regen, summary refresh | realization of M2; `principles.md` P7/E5 | Q2 |
| S12 | Should consider | Two-tier retrieval policy: graph navigation over artifacts (no embedding search), hybrid search over the corpus cache only | M1's contract, S5 corpus cache | Q2 |
| S13 | Should consider | Deterministic-vs-LLM dispatch table + static model tiering per operation class | S5's computational-before-generative rule, role charters (S4) | Q2 |
| S14 | Should consider | Parallel shard execution: dossier drafting per cluster, candidate red-teams, Map search fan-out | `state_machine.md` §3, M1 read-sets | Q2 |
| S15 | Should consider | Design Audit Report: periodic analytics jobs → human-read report → gated design changes; form-not-content rule; every efficiency metric paired with a quality guard | new process doc; feeds S8 minimal-run profile, DQ1–DQ5 | Q4 |
| S16 | Should consider | Trace privacy: local-first storage, researcher owns traces, cross-run aggregation opt-in and content-stripped | M6, `3_observability.md` §5 | Q3 |
| O5 | Optional | Prompt-cache-aware prefix ordering (stable → volatile) | implementation guidance (carried from O2) | Q2 |
| O6 | Optional | Machine-side token budgets and live meters per state | `state_machine.md` §5 (carried from O2) | Q2 |
| O7 | Optional | Stall detection: surface what the run is blocked on and for how long | M6 events, UI | Q3 |
| O8 | Optional | Question-form experiments (form-ladder variants) — only meaningful at multi-run scale | `elicitation.md` §4, S15 | Q4 |
| D7 | **Do not change** | Markdown files + frontmatter as the artifact substrate; no database as ground truth (analytics stores are derived and rebuildable) | `artifacts.md` §1, P1 | Q1 |
| D8 | **Do not change** | Trace-is-exhaust: artifacts remain the only load-bearing state; telemetry is write-only during a run (one narrow, human-approved exception: gate-loosening trust stats) | P1, M6 | Q3 |
| D9 | **Do not change** | No mechanical auto-closure or analytics-driven auto-tuning of gates, triad decisions, or defaults; self-measuring, never self-modifying | `bmad_transfer.md` §4.1–4.2, E6 | Q4 |
| D10 | **Do not change** | The kernel loop, six-state machine, and artifact catalog as the runtime's shape — this review specifies them; it does not amend them | whole baseline | all |

## The three Must Change items, summarized as `4_questions.md` requires

| | M4 schema registry | M5 identity & versioning | M6 run event log |
|---|---|---|---|
| **Why necessary** | The kernel's TRIAGE step derives unknowns "from the gap between the artifact under construction and its schema" — unimplementable without machine-readable schemas; P3's human-only fields are unenforceable without per-field author class | "Superseded artifacts are never deleted" and staleness propagation both presuppose versions and pinned references that are nowhere defined; M2's sectional repair presupposes section identity | The rent audit (E2, success criterion 5), DQ2's proxies, DQ4's extend-or-proceed log, and E6's led-or-followed diff all *require* data no mechanism collects; telemetry cannot be retrofitted onto past runs |
| **Affects** | `artifacts.md` §1–2, `elicitation.md` §1 | `artifacts.md` §1, `principles.md` P7/E5 | new infrastructure entry in `artifacts.md` beside the Question Ledger; `vision.md` criterion 5 |
| **Implementation impact** | Moderate: one YAML schema per artifact type + write-guard checks in the artifact store | Moderate: reference resolution + current-pointers + section anchors in the artifact store; touches every consumer | Low-moderate: append-only JSONL emitter wrapped around LLM calls, retrievals, ledger events, human edits |
| **Conceptual or implementation-only?** | **Implementation-only** — mechanizes what `elicitation.md` §1 and P3 already assert | **Implementation-only** — mechanizes what P7/E5 and `artifacts.md` §1 already assume | **Implementation-only** — collects what the baseline's own audits already promise to measure |
