# 02 — Design Principles

Two families: the structural principles P1–P11 and the elicitation principles E1–E8. Interaction is part of the reasoning architecture, not a chat surface; the E-principles govern it. Every mechanism in this spec should be traceable to a principle here, and every principle should be enforced by at least one mechanism.

---

## Structural principles

### P1. Artifacts are the state; everything else is exhaust
Artifacts (Markdown files with frontmatter, `04_artifacts.md`) are the system's only load-bearing state. Conversation is exhaust — except that answers to elicitation questions are captured as ledger entries, which are artifacts (E5). Runtime traces are exhaust too: the event log (`08_observability.md`) is write-only during a run, and a run with a deleted trace behaves identically.

### P2. Backward transitions are first-class
Discovery's most important event is often backward: reading the field reframes the intuition. The Inquiry Frame is the most-revised artifact in the system, and that is the system working. Loop-backs carry a one-line annotation of cause (`03_state_machine.md` §2).

### P3. Three decisions belong to the human — the constitutive triad
**(1) Scope & attention allocation** — which readings of the intuition are in play; which clusters are in or out; where reading time goes. **(2) Gap meaningfulness** — which gaps are real *and mine*. **(3) Direction selection** — the terminal choice. These live in fields declared `author: human` in the schema registry, and the artifact store rejects AI writes to them (`07_runtime.md` §1). Enforcement is mechanical, not conventional.

### P4. The AI's highest-leverage generative role is adversarial
The Skeptic attacks framings, clusterings, gap claims, and candidates (`06_roles.md`). Constructive AI output before the generation window opens is descriptive (what exists) or interrogative (what do you mean) — never creative (E6).

### P5. Plural, competing candidates — never a single anointed option
Propose must produce competing Candidate Directions (3–5 as a default), compared on a fixed qualitative table (same axes for all: gap/evidence strength, why-now, requirements vs. profile, strongest objection) with **no aggregate score**. The human writes "why this over the others" from the table, not from a computed ranking.

### P6. Cheapest first
Breadth before depth (Map before Deepen); the cheapest question form before more expensive ones (E3's form ladder); the cheapest resolution mechanism before more expensive ones (E8's resolution ladder). Depth budgets are the stage gates.

### P7. Staleness propagates; repair is lazy
Every artifact pins the versions it consumed (`depends_on: [id@version]`, `elicited_from: [q-id@version]` — `07_runtime.md` §2). A revised input marks dependents stale immediately (cheap graph traversal, no model calls). **Marking is eager; repair is lazy, diff-first, and sectional**: stale artifacts are repaired only when the scheduler needs them, repair first checks whether the change actually alters the artifact, and regenerates only affected sections (`07_runtime.md` §4). Post-terminal, monitoring can stale the Direction Decision itself.

### P8. The decision is drafted backwards
The Confidence Checklist — everything the researcher must credibly know before choosing — is created at Frame, filled by every state, and audited against traces at Decide. It doubles as the convergence test: when its remaining holes can only be filled by *choosing*, the system says so (`03_state_machine.md` §6).

### P9. Process must pay rent
Every artifact must earn its keep, and every question must earn its answer (E2). Cognitive load is the currency discovery most easily overspends; token spend is the second (E8, `07_runtime.md`). The minimal-run profile (`04_artifacts.md` §5) is P9 applied to schemas; the Design Audit Report (`08_observability.md` §5) is P9 applied to the design itself, with receipts.

### P10. Dissolution is a product
The discovery-scale kill is the Dissolution Memo: "already a mature field / tried and abandoned / dissolves under scrutiny." Reaching it in days is a *successful* run.

### P11. Enter anywhere
Five entry modes — intuition-first, paper-first, field-first, problem-first, tool-first — all backfill a minimal Intuition Note and enter at Frame.

---

## Elicitation principles

### E1. A question is a state-transition request
Artifacts have required fields; some fields cannot be computed because they encode the researcher's interest, taste, constraints, or judgment. A question is the system requesting missing input for a specific transition — a build system reporting a missing dependency. The elicitation loop *is* the scheduler (`05_elicitation.md` §2); there is no chat surface separate from the workflow.

### E2. Every question pays rent
A question is well-formed only if it declares a **target** (the artifact field its answer fills) and a **leverage class** (which of six downstream effects it changes — `05_elicitation.md` §3). Questions that cannot name both are computed, defaulted, or dropped. The ledger audit retroactively checks that answers were consumed, using event-log evidence (`08_observability.md`).

### E3. Elicit against evidence, not a blank page
The system spends compute first — search, cluster, draft — then asks, presenting questions as choices over shown evidence. Question forms ranked by load, cheapest preferred: confirm-a-default → menu → rank/allocate → free text (rare, justified). Every question ships with the AI's proposed default; silence is a valid answer. Open-ended questions are permitted only where the researcher's unprimed view is itself the datum (E6).

### E4. Ask at the last responsible moment
No intake stage. Questions surface in small batches (≤5) at review gates, plus rare blocking asks mid-state. Each card shows *why now*. Deferrable unknowns get the AI's default and wait until they block.

### E5. Answers are revisable artifacts
Answers are versioned ledger entries; artifacts cite them via `elicited_from`; revising an answer stales dependents exactly like any upstream change (P7). Question cards state their reversibility. Fast, directional answering is rational because the system — not the researcher — tracks consequences, and because repair is cheap (P7's lazy discipline is what keeps this promise for the machine as well as the human).

### E6. Anchoring discipline: the researcher's signal is protected
The deep failure mode of AI-assisted discovery is homogenization — the AI's fluent framing becomes everyone's framing. Two mechanisms: **Generation windows** — each artifact type has an earliest state before which the AI may not draft it; in particular, no direction-shaped content before the Gap Register is accepted, with premature output quarantined into a `premature_ideas` pen. **Ask-before-show** — at Frame ("what do you suspect the interesting angle is?") and at Propose ("which direction are you already leaning toward?"), the researcher's unprimed answer is recorded before any AI output is displayed; the Decide gate shows the diff between unprimed lean and final choice. The window constrains *timing*, not provenance: once open, candidates may be generated from any accepted evidence (gaps *or* synthesis — `04_artifacts.md`). At population scale, E6 extends to analytics: aggregate data may tune the process's form, never its content (`08_observability.md` §6).

### E7. Confidence is the product; understanding cannot be delegated
The terminal condition is subjective — the researcher *confidently* selects. Representative papers carry `human_read` flags with a one-line human reaction, required at Decide for the papers defining each surviving candidate. The Confidence Checklist is audited against traces. AI text is labeled as AI text everywhere; human-authored fields are structurally distinct (enforced by field provenance, `07_runtime.md` §1).

### E8. The resolution ladder: deterministic before generative before human
Every unknown and every operation is resolved by the cheapest sufficient mechanism, escalating: **deterministic computation** (schema diffs, citation statistics, embedding clustering, staleness propagation) → **cheap model** (extraction, diff-checks, summaries) → **frontier model** (naming, synthesis, red-teaming) → **researcher question** (human-only unknowns only). E3's "compute first, then ask" and the triage of `05_elicitation.md` §1 are the top rung; the dispatch table of `07_runtime.md` §5 is the bottom rungs. Never generate what is calculable; never ask what is generatable.
