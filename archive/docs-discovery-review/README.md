# KagamiOS v2 — Design Review (Audit of `docs-discovery/`)

This directory answers `3_questions.md`. It is an **audit, not a redesign**: the v2 Discovery OS in `docs-discovery/` is treated as the baseline, every judgment is made against that design's own stated goals (`vision.md` success criteria, principles P1–P11 / E1–E7), and nothing in `docs-discovery/` is modified. Where the review concludes the baseline is right, it says so explicitly.

Every recommendation carries one of four classifications:

- **Must change** — an internal inconsistency or a gap that would make the design fail its own stated goals at implementation time.
- **Should consider** — a real weakness with a concrete, baseline-compatible remedy; adopt unless dogfooding says otherwise.
- **Optional** — an improvement that is safe to defer.
- **Do not change** — the baseline is correct on this point; proposals to alter it (including those raised in `3_questions.md`) should be declined.

## Reading order

| Doc | Question audited |
|---|---|
| `1_practice_alignment.md` | Does v2 match how strong computational/ML researchers actually move from intuition to direction? |
| `2_agent_personas.md` | Stable BMAD-style personas vs. the baseline's role-behaviors |
| `3_token_efficiency.md` | Preserving discovery quality while minimizing token consumption |
| `4_endpoint.md` | Direction Decision vs. a curated portfolio of research opportunities |
| `5_knowledge_structure.md` | Artifact graph vs. an explicit Area → Community → Group → Line → Papers hierarchy |

## Verdicts at a glance

1. **Practice alignment:** the six-state funnel is a faithful model of *deliberate field entry* — the mode strong researchers use when the stakes justify it. Three real divergences: candidate generation is gaps-only (recombination-driven directions, common in ML, have no AI-side path); the corpus model is publication-centric (the ML frontier lives partly in preprints, code, and workshops); and hard/impossible gap verdicts sometimes need a one-hour probe, not more reading. None is fatal; the first is the most serious.
2. **Personas:** keep the baseline's "modes of critique, not simulated colleagues." Anthropomorphic personas are not a quality lever in this design — they are an anchoring vector (likability → deference, against E6). What *does* matter for quality is stable per-role behavioral contracts, which the baseline gestures at but never specifies.
3. **Token efficiency:** the elicitation kernel solves the *attention* economy brilliantly and says almost nothing about the *token* economy — a real gap for a design whose BMAD inheritance was prized partly for token frugality. Two must-fixes: a context-loading contract (who reads what, summary vs. full), and staleness-repair discipline (E5's "changing your mind is cheap" is currently only true for the researcher, not for the system).
4. **Endpoint:** the Direction Decision is the correct terminal abstraction — do not replace it with a portfolio *endpoint*, which would reopen the survey-tool failure mode `vision.md` exists to fight. But the portfolio is the correct *shape of the terminal artifact*, and the baseline already contains ~80% of it in scattered form; make it explicit.
5. **Knowledge structure:** do not make the five-level hierarchy first-class — real fields are not trees, and a fixed AI-authored ontology is exactly the anchoring hazard the baseline's own DQ3 identifies. The legitimate need underneath the proposal is met by (a) fixing a genuine cluster-vs-group conflation in `artifacts.md`, and (b) a flat entity registry beneath the artifact graph.

## Consolidated recommendation register

| ID | Class | Recommendation | Affects (baseline) | From |
|---|---|---|---|---|
| M1 | **Must change** | Context-loading contract: per-state read-sets, mandatory `summary` block in artifact metadata, summary-by-default consumption | `artifacts.md` §1 §4, `state_machine.md` §3, `bmad_transfer.md` §3 | Q3 |
| M2 | **Must change** | Staleness ≠ regeneration: lazy, diff-first repair of stale artifacts | `principles.md` P7/E5, `elicitation.md` §5, `artifacts.md` §1 | Q3 |
| M3 | **Must change** | Resolve the cluster ≠ research-group conflation in the Cluster Dossier definition | `artifacts.md` §2 §3, `state_machine.md` §3 | Q5 |
| S1 | Should consider | Widen Propose's generation basis: recombination/why-now candidates grounded in Landscape Synthesis, not Gap Register only (generation-window *timing* unchanged) | `artifacts.md` Candidate Direction, `state_machine.md` Propose, E6 | Q1 |
| S2 | Should consider | Frontier corpus sources (preprints, code, workshops) + per-cluster recency profile | Field Map fields, Scout role, monitoring config | Q1 |
| S3 | Should consider | Micro-probe as a Gap Register evidence type (bounded, ≤ hours), or a `probe_before_commit` flag on the Decision | Gap Register, Direction Decision, `vision.md` "what it is not" | Q1 |
| S4 | Should consider | Role charters: per-role permitted/forbidden outputs, evidence obligations, generation-window bindings, context policy | `bmad_transfer.md` §3.5 (new section) | Q2 |
| S5 | Should consider | Corpus cache: per-paper cards computed once and cited by ID; computational-before-generative rule (embeddings/citation-graph clustering, LLM for naming only) | `artifacts.md` (new infrastructure layer), Cartographer role | Q3 |
| S6 | Should consider | Portfolio-structured Direction Decision: explicit selected / parked / rejected-with-reasons / spawned-intuitions sections; `rejection_reason` field on Candidate Direction | `artifacts.md` Direction Decision + Candidate Direction, DQ7, DQ10 | Q4 |
| S7 | Should consider | Flat entity registry (paper / person / group / venue IDs) beneath the artifact graph, cross-run reusable | `artifacts.md`, Researcher Profile reuse, monitoring | Q5 |
| S8 | Should consider | Minimal-run profile: designate mandatory vs. optional fields per artifact so a run can complete in days | `artifacts.md`, `README.md`, DQ1 | Q1 |
| O1 | Optional | Role-labeled voice (e.g., Skeptic output visibly adversarial) — legibility without personas | UI/presentation only | Q2 |
| O2 | Optional | Prompt-cache-aware prefix ordering; machine-side token budgets mirroring depth budgets | implementation guidance, `state_machine.md` §5 | Q3 |
| O3 | Optional | The five-level hierarchy as a generated *view* over Field Map + Dossiers (for the DQ10 presentation surface) | presentation layer only | Q5 |
| O4 | Optional | Named `research_lines` subsection inside the Dossier Evolution section | Cluster Dossier schema | Q5 |
| D1 | **Do not change** | The six-state funnel, loop-backs, and derived (not enforced) states | `state_machine.md` §1–2 | Q1 |
| D2 | **Do not change** | Exclusion of experiments/implementation/writing from scope (subject only to S3's narrow evidence exception) | `vision.md` | Q1 |
| D3 | **Do not change** | "Modes of critique, not simulated colleagues" — no anthropomorphic personas | `bmad_transfer.md` §3.5 | Q2 |
| D4 | **Do not change** | Dossier-as-shard; computable/human-only/deferrable triage | `artifacts.md`, `elicitation.md` §1 | Q3 |
| D5 | **Do not change** | Direction Decision as terminal event; the convergence machinery (Confidence Checklist, depth budgets, Decide gate) | `vision.md`, `state_machine.md` §5 | Q4 |
| D6 | **Do not change** | Artifact graph as memory; human-owned cluster granularity; no first-class knowledge hierarchy | `artifacts.md`, `state_machine.md` §1, DQ3 | Q5 |
