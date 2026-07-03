# KagamiOS v2 — Vision

## One sentence

KagamiOS is an operating system for research discovery: it transforms a vague research intuition into a small set of concrete, evidence-backed candidate directions by doing the tractable landscape work automatically and asking the researcher only the questions whose answers change the outcome — and it terminates the moment the researcher confidently selects a direction.

## The endpoint, redefined

The product of KagamiOS is **a decision, plus the understanding required to make it**. The artifacts — field maps, dossiers, gap registers — are the *trace* of that understanding, not the deliverable. This is the sharpest difference from a survey tool, and it drives every design choice:

- A survey tool's output is a document; its success is coverage. KagamiOS's output is a Direction Decision; its success is that the decision holds up. Landscape work that cannot change which candidate directions survive is skipped by construction (Principle E2).
- A survey has no natural stopping point; discovery does — the point where more reading no longer changes the choice. KagamiOS makes stopping a managed decision (depth budgets, `state_machine.md` §5) rather than an accident of exhaustion.
- A survey can be delegated; understanding cannot. The researcher must actually read the papers that define their eventual direction, and the system verifies the *trace* of that reading even though it cannot verify the understanding itself (Principle E7).

## Why "Kagami" still fits

Kagami (鏡) means *mirror*. In v1 the mirror reflected the project's reasoning back as inspectable artifacts. In v2 the mirror is sharper and more personal: **the questions are the mirror**. A researcher with a vague intuition does not yet know what they are interested in — theory or application, mechanism or performance, this community or that one. A well-chosen question ("the field splits into these five clusters; which are you actually drawn to?") shows the researcher the shape of their own interest. The system does not tell the researcher what to want; it makes the researcher's wanting visible to themselves, one high-leverage question at a time.

## What KagamiOS is not

- **Not an AI Scientist and not an idea generator.** Sharpened from v1: the AI does not merely avoid replacing taste — it is *structurally forbidden* from proposing research directions before the landscape and gap artifacts are accepted (generation windows, `elicitation.md` §6). A direction proposed on day one is fluent, generic, and anchoring; a direction generated from an accepted Gap Register, after the researcher's own hunches have been recorded, is evidence.
- **Not a literature survey tool** — see above. This remains the strongest gravitational pull during implementation, and it is now even closer, because discovery's day-to-day activity *looks* like surveying. The defense is that every artifact and every question must trace forward to candidate survival.
- **Not an intake form.** The naive way to "elicit information" is a big upfront questionnaire. That maximizes cognitive load exactly when the researcher knows the least. KagamiOS asks nothing it can compute, nothing before it is needed, and nothing without showing the evidence that makes the question concrete (E3, E4).
- **Not a lifecycle manager.** Experiment design, implementation, execution, and writing are outside the system boundary. The Direction Decision is a handoff artifact; what consumes it (a v1-style lifecycle machine, a human process, nothing) is explicitly not KagamiOS's concern.

## The decision, written backwards

v1's Principle P8 ("write the paper backwards from day one") is retired with the paper — but its logic survives in a new form. At Frame time, the system drafts the **Confidence Checklist**: the concrete things the researcher will need to know before they can credibly choose a direction. It is essentially the question list from `2_questions.md`'s example, instantiated for this project:

- Which communities exist around this topic, and how did each evolve?
- Who are the leading researchers, and which papers define each thread?
- What competes with this approach, and on what terms?
- What is solved, what is open, and *why* is each open thing still open?
- Which direction fits my taste, skills, and constraints — and why now?

The checklist exists from the first day, and its unfilled entries are the project's to-do list. Every state fills some entries; the Decide gate checks the trace behind each. This is the discovery analogue of the paper skeleton: the terminal artifact created first, integrating everything, whose holes drive the work.

## First user and dogfooding case

Unchanged from v1: a single researcher running the Signature-methods-for-deep-learning investigation. The worked example in `elicitation.md` §7 runs that exact case through the design. Every mechanism should be tested by asking: *would this question / artifact / gate have moved the Signature investigation toward a confident choice, or would it have been overhead?*

## Success criteria

KagamiOS v2 is working if, after one real discovery run:

1. **Time-to-confident-decision is weeks, not months.** From captured intuition to a Direction Decision the researcher stands behind.
2. **The decision is robust.** The chosen direction survives first contact with deep, post-decision literature work — no discovering that the gap was filled two years ago (a "type-4 gap" in v1's terms). This is the one objectively testable criterion: the deep survey that follows the decision should confirm, not overturn, the landscape the decision was based on.
3. **The researcher can answer the checklist.** They can name the communities, the defining papers, the competing approaches, and the reason each surviving gap exists — from their own head, not by looking it up.
4. **Cheap dissolution.** An intuition that turns out to be already-solved or vacuous dissolves in days, with a Dissolution Memo, and the researcher regards this as a *win* (v1 P10, inherited).
5. **Every question paid rent.** The question ledger audit (`elicitation.md` §5) shows no questions whose answers were never consumed by an artifact.
6. **The handoff works.** A downstream process (human or agent) can pick up the Direction Decision and its evidence trail without re-interviewing the researcher.
7. **Voluntary reuse** on the next vague intuition — still the test that the process pays rent.
