# KagamiOS — Clarification and Next Design Request

First, thank you for the previous design review.

The documents you produced were extremely valuable, especially the discussions around:

* Traceability vs. reproducibility
* Artifact-centered state management
* Human-in-the-loop decision making
* Staleness propagation
* Process must pay rent
* BMAD's transferable mechanisms vs. non-transferable epistemology

After reviewing the documents, I realized that my original `questions.md` unintentionally suggested a much broader scope than I actually intend.

---

# Clarification

KagamiOS is **not** intended to manage the complete research lifecycle.

It is **not** an AI Scientist.

It is **not** a research execution system.

It does **not** perform:

* experiment design
* implementation
* experiment execution
* paper writing
* publication workflow

Those activities belong to downstream tools or future workflows.

---

# What KagamiOS actually is

KagamiOS is a **Research Discovery Operating System**.

Its purpose is to transform a vague research intuition into one or more concrete, evidence-backed research directions.

The endpoint is **not** a paper.

The endpoint is that the researcher confidently says:

> "This is the research direction I want to pursue."

Everything after that is outside the scope of KagamiOS.

---

# What I want to inherit from BMAD

One thing I may not have explained clearly enough:

What impressed me about BMAD was not only its state transitions, artifact handoffs, low token cost, or sharding.

The most impressive part was its **information elicitation design**.

BMAD does not ask the user to manually specify everything upfront.

Instead, it asks the right questions at the right time, extracts the missing information needed for the next artifact, and gradually reaches a state where AI agents can act with much higher accuracy and autonomy.

In other words, BMAD reduces the user's cognitive load while still obtaining the information necessary to produce precise artifacts.

This is the kind of mechanism I want KagamiOS to inherit.

For KagamiOS, interaction should not be treated merely as a chat interface.

Interaction is part of the reasoning architecture.

The system should ask the researcher only the questions that are necessary to reduce ambiguity enough for the next discovery artifact to be produced.

Every question should pay rent.

A question is justified only if the answer changes one of the following:

* which research areas are searched
* how the field is clustered
* which papers are considered representative
* which communities or researchers are prioritized
* which gaps are considered meaningful
* which candidate directions survive

The goal is not to burden the researcher with process.

The goal is to let the researcher start from a vague intuition, answer a small number of high-leverage questions, and allow the system to construct increasingly precise discovery artifacts.

---

# Typical workflow

A typical workflow looks more like:

Idea

↓

Clarify the intuition through targeted elicitation

↓

Identify related research areas

↓

Cluster the field into research groups

↓

Understand the history of each group

↓

Identify major researchers and communities

↓

Read representative papers

↓

Compare competing approaches

↓

Understand current research trends

↓

Identify research gaps

↓

Generate candidate research directions

↓

Human selects a direction for further research

End.

There is intentionally **no** Experiment, Implementation, or Paper stage.

---

# Example

Suppose I begin with:

> "Signature methods may become useful building blocks for deep learning."

KagamiOS should help me answer questions such as:

* What exactly am I interested in: theory, representation learning, time-series modeling, Transformers, robustness, efficiency, or applications?
* What research communities exist around Signature methods?
* How did each community evolve?
* Who are the leading researchers?
* Which papers define each direction?
* Which approaches compete with Signature?
* Which problems have already been solved?
* Which problems remain open?
* Which directions appear most promising?
* Which direction best matches my taste, skill set, and constraints?

After understanding the landscape, I choose one direction.

Only then would another workflow begin.

---

# New Design Request

Given this clarified scope, please redesign KagamiOS as a **Research Discovery Operating System**.

Please focus on:

1. The appropriate state machine for research discovery.
2. The minimal set of artifacts needed before a concrete research direction is selected.
3. Human decision points during discovery.
4. The interaction model: how KagamiOS should ask questions to elicit missing information with minimal cognitive load.
5. How each question should connect to artifact creation or state transitions.
6. Which BMAD concepts still transfer well.
7. Which new concepts are unique to research discovery.
8. Whether "research groups", "historical evolution", "research landscape", and "candidate directions" should become first-class artifacts.
9. How AI should collaborate with the researcher without prematurely proposing research ideas.
10. Whether Discovery itself should be modeled as a state machine, an artifact graph, an elicitation loop, or another abstraction.

Please ignore experiment execution, coding, implementation planning, and paper writing entirely.
