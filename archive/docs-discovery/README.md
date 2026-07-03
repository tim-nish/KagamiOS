# KagamiOS v2 — Research Discovery Operating System

This directory is a complete redesign of KagamiOS in response to the scope clarification in `2_questions.md`. The v1 documents in `docs/` (the Research *Lifecycle* OS) are preserved untouched so the two designs can be compared side by side.

## Relationship to the v1 design

v1 modeled the entire lifecycle: portfolio of bets, then Frame → Survey → Position → Hypothesize → Probe → Design → Execute → Interpret → Communicate → Review. The v2 scope corresponds roughly to v1's **Frame → Survey → Position slice plus the very front edge of Hypothesize**, expanded to full resolution — and everything after it is deleted, not deferred. The terminal event is no longer a paper; it is the researcher saying *"this is the direction I want to pursue."*

Two consequences of the truncation ripple through everything:

1. **The convergence assumption largely returns.** v1's central finding was that BMAD's epistemology (uncertainty decreases monotonically) does not transfer to research, because experiments can legitimately increase uncertainty. But *discovery* — like BMAD's planning phase — really is a process of converting ambiguity into a spec. The spec is the research direction. Discovery : research lifecycle :: BMAD planning : BMAD execution. This makes BMAD a much better donor for v2 than it was for v1 (see `bmad_transfer.md`).
2. **Elicitation moves from a supporting mechanism to the kernel.** In v1, templates-with-embedded-elicitation was one of five transferable BMAD mechanisms. In v2 it is the engine: the system advances by identifying what it does not know, resolving what it can by computation, and asking the researcher only the questions whose answers change the outcome (see `elicitation.md`).

## Reading order

| Doc | Contents |
|---|---|
| `vision.md` | What a Discovery OS is, its endpoint, what it is not, success criteria |
| `principles.md` | Which v1 principles survive (kept / adapted / retired) + the new elicitation principles E1–E7 |
| `elicitation.md` | **The kernel.** The elicitation loop, question rent, leverage classes, question ledger, researcher profile, worked Signature-methods example |
| `state_machine.md` | The discovery state machine, human gates, loop-backs, terminal states, and the answer to "state machine vs. artifact graph vs. elicitation loop" |
| `artifacts.md` | The minimal artifact catalog, with explicit verdicts on which concepts become first-class |
| `bmad_transfer.md` | Re-audit of the BMAD analogy under the discovery scope |
| `open_questions.md` | Unresolved design questions (DQ1–DQ10) |

## Answers at a glance

The ten requests in `2_questions.md`, and where each is answered:

| # | Request | Short answer | Where |
|---|---|---|---|
| 1 | State machine for discovery | Six working states — Frame, Map, Deepen, Synthesize, Locate, Propose — plus a Decide gate and three terminal states (Decided, Dissolved, Dormant) | `state_machine.md` §2 |
| 2 | Minimal artifact set | Nine artifacts, from Intuition Note to Direction Decision; each justified by a failure it prevents | `artifacts.md` |
| 3 | Human decision points | Three constitutive gates: **scope & attention allocation**, **gap meaningfulness**, **direction selection** — plus review gates and mandatory human reading | `state_machine.md` §3 |
| 4 | Interaction model | An elicitation loop: triage unknowns into computable / human-only / deferrable; ask only blocking human-only unknowns, against evidence, with defaults | `elicitation.md` |
| 5 | Question ↔ artifact connection | Every question must declare a target artifact field and one of six leverage classes; answers are ledger entries that artifacts cite via `elicited_from` | `elicitation.md` §3–4 |
| 6 | BMAD concepts that transfer | Artifact handoffs, gates, elicitation (generalized), sharding (cluster dossiers), roles — and, newly, the convergence epistemology | `bmad_transfer.md` |
| 7 | Concepts unique to discovery | Researcher Profile, evidence-grounded elicitation, generation windows, question rent auditing, confidence-as-product, dissolution-as-success | `principles.md` E1–E7, `bmad_transfer.md` §5 |
| 8 | First-class artifacts? | Research groups → **yes** (Cluster Dossier). Historical evolution → **yes, per cluster** (dossier section, promoted from v1's demotion). Landscape → **yes, split in two** (Field Map + Landscape Synthesis). Candidate directions → **yes** (Candidate Direction cards) | `artifacts.md` §3 |
| 9 | AI without premature ideas | Generation windows (AI may not draft direction-shaped content before Gaps are accepted) + anchoring discipline (researcher's own view is elicited before AI output is shown) | `principles.md` E6, `elicitation.md` §6 |
| 10 | Which abstraction? | A hybrid with a new emphasis: the artifact graph is the **memory**, the elicitation loop is the **engine**, the state machine is the **map**. None of the three alone suffices | `state_machine.md` §1 |
