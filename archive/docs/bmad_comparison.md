# KagamiOS — BMAD Comparison

KagamiOS is pitched as "a research analogue of BMAD." This document takes that analogy seriously enough to find where it breaks. Summary: BMAD's *mechanisms* (artifact handoffs, gates, templates, sharding, role separation) transfer well; BMAD's *epistemology* (uncertainty decreases monotonically as you move through phases) does not transfer at all, and importing it silently is the main way KagamiOS could fail.

## 1. What BMAD actually is

BMAD (Breakthrough Method for Agile AI-Driven Development) structures AI-assisted software delivery in two phases:

1. **Planning** — role-specialized agents produce documents in sequence: Analyst (project brief) → PM (PRD) → Architect (architecture doc), each consuming the previous artifact, each with a human approval gate. Templates embed elicitation prompts so the agent interrogates the human rather than hallucinating requirements.
2. **Execution** — a Scrum Master agent *shards* the big documents into hyper-detailed, self-contained story files sized to an LLM context window; a Dev agent implements each story; a QA agent reviews against acceptance criteria.

The load-bearing insight: **the artifacts, not the conversation, carry the project's state**, so any agent can pick up a unit of work with complete context. Everything else is choreography.

## 2. Mapping table

| BMAD | KagamiOS analogue | Fidelity of the analogy |
|---|---|---|
| Project brief (Analyst) | Intuition Note + Triage Memo | good |
| PRD (PM) | Question Hierarchy | good — both define *what and why*, not *how* |
| Architecture doc (Architect) | Experiment Design | partial — see §4.2 |
| Market/competitor research | Survey Corpus + Landscape Map | partial — competitors don't publish their source; researchers do. Survey is deeper and *continuous* |
| Epics → sharded stories | Experiment Design → runs/probes | **weak** — see §4.3 |
| Dev agent implements story | Execute state | good, for ML research where experiments are code |
| QA vs. acceptance criteria | Interpret vs. ex-ante criteria | partial — see §4.1 |
| Human approval gates | Review gates + three constitutive gates | KagamiOS distinguishes two kinds (P3); BMAD doesn't need to |
| Done / shipped | — | **no analogue** — see §4.1 |
| Brownfield vs. greenfield | entering a mature vs. nascent field | surprisingly good — a mature field, like a legacy codebase, demands "document what exists" before proposing changes |

## 3. What transfers

1. **Artifact-driven context handoff.** Transfers fully; it is the whole reason to build KagamiOS (P1). Both systems exist to defeat the same enemy: state trapped in ephemeral context (chat history, human memory).
2. **Human approval gates between phases.** Transfers with an upgrade: BMAD's gates are all review gates; KagamiOS additionally marks three as constitutive and permanently human (P3).
3. **Templates with embedded elicitation.** Transfers beautifully. A Hypothesis Card template that *demands* `falsified_by`, a Gap Register that *demands* `why_does_this_gap_exist` — the template interrogating the researcher is the cheapest possible rigor mechanism.
4. **Sharding for context windows.** Transfers as mechanism: a full project (corpus + designs + logs) exceeds any context window, so units of AI work must be self-contained (one hypothesis card + its design + relevant runs). But the decomposition is not plannable up front — see §4.3.
5. **Role-specialized agents.** Transfers: Scout (search/monitor), Historian (synthesis), **Skeptic** (the adversarial critic — no clean BMAD counterpart, and by P4 the most important one), Methodologist (design red-team), Scribe (skeleton maintenance), Bookkeeper (run logs). The caution: BMAD's personas map to real job titles on real teams; research roles are hats one person swaps, so roles should be *modes of critique*, not simulated colleagues.

## 4. What must NOT transfer

### 4.1 The convergence assumption

The deep one. In BMAD, uncertainty decreases monotonically: brief → PRD → architecture → stories → code, each artifact more determined than the last, ending in "done" — binary acceptance criteria pass and the ticket closes. This is correct for software because *the spec is an input*: someone decides what to build, and the process verifies conformance.

In research, the spec is the *output* — the hypothesis is precisely the thing under test — and a well-designed experiment can legitimately *increase* uncertainty (destroy the plan, reopen the question). Consequences already built into the design:

- Backward transitions are first-class (P2), where BMAD treats rework as exception.
- "Done" has no analogue: claims are defeasible forever; a "published" project can be reopened by a failed replication. Terminal states are portfolio states (KILLED, GRADUATED), not epistemic ones.
- Acceptance criteria become *ex-ante discrimination criteria*: written before the run like BMAD's criteria are written before the code, but their job is to prevent self-deception at Interpret, not to define completion. "Criteria failed" is a normal, informative outcome, not a QA rejection.
- Rework must be *budgeted*: BMAD's DAG becomes a cyclic graph, and staleness propagation (P7) exists to make the cycles safe.

### 4.2 The completable-design assumption

BMAD's Architect can produce a full architecture before a line of code because software design is (approximately) deducible from requirements. A full experimental program is *not* deducible from a hypothesis: experiment N+1 depends on the result of experiment N. Hence the Probe state and the rule that Experiment Designs are written per-campaign, not per-project. An agent that drafts the "complete implementation plan" of the founding pipeline would be generating fiction past the first experiment.

### 4.3 Up-front decomposition (epics → stories)

The Scrum Master can shard a PRD into an ordered story backlog because the work is enumerable in advance. Research work items *spawn from results*: today's anomaly is next week's ablation. KagamiOS keeps the shard *format* (self-contained work units) but generates them just-in-time from the artifact frontier, never as an up-front backlog.

### 4.4 Throughput as the objective

BMAD optimizes for velocity of correct implementation. Optimizing a research process for artifact throughput yields salami science and confirmatory experiments — the metric is trivially gameable by lowering ambition. The only safe efficiency metric is *time-to-kill* for bad directions (`vision.md`, success criterion 1); for good directions the process optimizes traceability and rigor, not speed.

### 4.5 Ceremony tolerance

BMAD's verbose artifacts are cheap because agents write and read most of them. KagamiOS has a human at every gate who feels every mandatory field; P9 (process must pay rent) has no BMAD counterpart because BMAD doesn't need it. Artifact schemas here must stay an order of magnitude lighter.

## 5. Where research demands mechanisms BMAD lacks

1. **Staleness propagation (P7).** Software requirements change by decision; the literature changes *by itself*. Nothing in BMAD watches the world and marks artifacts suspect. This is KagamiOS's most novel component.
2. **The Skeptic (P4).** BMAD's QA checks conformance to a spec; research needs an adversary that attacks the spec itself — gaps, hypotheses, designs, interpretations.
3. **A portfolio layer (P10).** BMAD manages one project someone already decided to build. Research's scarcest resource is allocated *across* bets; kill/park/revive decisions need first-class representation.
4. **Uncertainty as data (P5).** BMAD artifacts assert; KagamiOS artifacts carry confidence, competing alternatives, and belief-revision history.
5. **A living terminal artifact (P8).** No BMAD document plays the role of the Paper Skeleton — an output that exists from the start and integrates everything, whose holes are the to-do list.
