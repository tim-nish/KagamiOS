# 01 — Vision and Scope

## The endpoint

The product of KagamiOS is **a decision, plus the understanding required to make it**. Artifacts — field maps, dossiers, gap registers — are the *trace* of that understanding, not the deliverable. The terminal event is the researcher confidently saying *"this is the direction I want to pursue"*; the terminal artifact is the **Direction Decision**, structured as a portfolio (selected direction, parked alternatives with revival conditions, rejected candidates with reasons, spawned future intuitions — `04_artifacts.md`). The portfolio is the format; the decision is the event. Everything after the decision — experiment design, implementation, writing — is outside the system boundary.

Three consequences drive the whole design:

- A survey tool's output is a document and its success is coverage. KagamiOS's output is a decision and its success is that the decision holds up. Landscape work that cannot change which candidate directions survive is skipped by construction (E2).
- A survey has no natural stopping point; discovery does — the point where more reading no longer changes the choice. Stopping is a managed decision (depth budgets and the convergence test, `03_state_machine.md` §6), not an accident of exhaustion.
- A survey can be delegated; understanding cannot. The researcher must read the papers that define their eventual direction, and the system verifies the *trace* of that reading (E7) even though it cannot verify the understanding itself.

## The mirror

Kagami (鏡) means *mirror*: the questions are the mirror. A researcher with a vague intuition does not yet know what they are interested in. A well-chosen question, asked against computed evidence ("the field splits into these five clusters — which are you drawn to?"), shows the researcher the shape of their own interest. The system never tells the researcher what to want; it makes the wanting visible, one high-leverage question at a time.

## What KagamiOS is not

- **Not an AI Scientist or idea generator.** The AI is structurally forbidden from proposing direction-shaped content before the landscape and gap artifacts are accepted (generation windows, E6), and the researcher's unprimed views are recorded before AI output is shown (ask-before-show). A direction generated from an accepted Gap Register and Landscape Synthesis, after the researcher's own hunches are on record, is evidence; a direction proposed on day one is anchoring.
- **Not a literature survey tool.** The strongest gravitational pull during implementation, because discovery's daily activity *looks* like surveying. The defense: every artifact and every question must trace forward to candidate survival.
- **Not an intake form.** The system asks nothing it can compute, nothing before it is needed, and nothing without showing the evidence that makes the question concrete (E3, E4).
- **Not a lifecycle manager.** The Direction Decision is a handoff. One bounded concession exists: a researcher-executed **micro-probe** (hours, not days) is admissible as *evidence* for a single Gap Register feasibility claim (`04_artifacts.md`), because the literature systematically underreports "we tried it and it was fine." Micro-probes produce evidence entries, never artifacts of their own, and never open an execution stage.

## The decision, written backwards

At Frame time the system drafts the **Confidence Checklist**: the concrete things this researcher must credibly know before choosing — which communities exist and how each evolved; who leads them and which papers define each thread; what competes with the approach and on what terms; what is solved, what is open, and *why* each open thing is still open; which direction fits the researcher's taste, skills, and constraints, and why now. The checklist exists from day one; its unfilled entries are the project's to-do list; every state fills entries; the Decide gate audits the trace behind each (P8).

## First user and dogfooding case

A single researcher running the *Signature-methods-for-deep-learning* investigation (worked example, `05_elicitation.md` §7). Every mechanism is tested by one question: *would this have moved the Signature investigation toward a confident choice, or would it have been overhead?*

## Success criteria

KagamiOS is working if, after one real discovery run:

1. **Time-to-confident-decision is weeks, not months** — and days for a minimal-profile run (`04_artifacts.md` §5).
2. **The decision is robust.** The post-decision deep literature work confirms, not overturns, the landscape the decision was based on. Falsifiable claims are pre-registered in the Decision memo so this is testable (`08_observability.md` §3).
3. **The researcher can answer the checklist from their own head** — communities, defining papers, competitors, why each surviving gap exists.
4. **Cheap dissolution.** An already-solved or vacuous intuition dissolves in days with a Dissolution Memo, and this counts as a win (P10).
5. **Every question paid rent.** The ledger audit shows no questions whose answers were never consumed — now measurable via the run event log (`08_observability.md`).
6. **The handoff works.** A downstream process can pick up the Decision bundle without re-interviewing the researcher (resumption test: an agent with only the bundle can answer the Confidence Checklist).
7. **Voluntary reuse** on the next vague intuition.
