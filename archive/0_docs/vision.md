# KagamiOS — Vision

## One sentence

KagamiOS is an operating system for the research process: it holds the evolving state of a research project in explicit, versioned artifacts, lets AI do the reasoning that is tractable to automate, and routes every decision that constitutes research *taste* to the human — with a permanent trace of why each decision was made.

## Why "Kagami"

Kagami (鏡) means *mirror*. The system does not think for the researcher; it reflects the researcher's reasoning back as an inspectable object. A mirror lets you see what you cannot see directly: the assumption you never wrote down, the hypothesis you quietly abandoned without deciding to, the gap between what you believe and what your evidence supports. That externalization — not automation — is the core product.

## Three reframes of the original goal

The founding document (`questions.md`) states the goal as making the reasoning process "reproducible." Taken literally, this goal is wrong, and the design should not chase it.

### Reframe 1: Traceable, not reproducible

Insight is not reproducible. Two researchers given the same literature will not derive the same intuition, and the same researcher cannot re-run their own "aha" deterministically. What *can* be engineered is:

- **Traceability** — every belief in the project links back to the evidence and decisions that produced it.
- **Resumability** — a project paused for three months (or handed to a collaborator, or picked up by an AI agent) can be resumed from its artifacts alone, without archaeology through chat logs and memory.
- **Auditability** — when a result surprises you, you can find which assumption broke.

This is the honest analogue of BMAD's achievement. BMAD did not make software design reproducible; it made the *state* of a project explicit enough that any agent (human or AI) can pick up the next unit of work with full context. KagamiOS should promise the same, no more.

### Reframe 2: A portfolio of bets, not a pipeline

The original workflow models one idea flowing to one paper. Real researchers — and every serious research organization — run a *portfolio*: many intuitions captured, few surveyed, fewer piloted, very few pushed to publication. The most valuable decisions in research are **selection and kill decisions**, and the proposed pipeline has no place for either. A Research OS that cannot represent "I am dropping this idea, here is why, here is what would revive it" is missing the highest-leverage artifact in research.

KagamiOS therefore has two layers: a **portfolio layer** (ideas as bets with explicit triage, kill, and revive transitions) and a **project layer** (the state machine for a single active bet). See `state_machine.md`.

### Reframe 3: The paper is a living artifact, not a terminal state

The proposal places "Paper Draft" at the end of the pipeline. Experienced researchers do the opposite: Whitesides' classic advice is to write the paper outline *first* and treat it as the research plan; DARPA's Heilmeier Catechism forces the final claims to be articulated before any work begins. Writing is where reasoning gaps become visible — deferring it to the end defers the discovery of those gaps to the moment they are most expensive.

In KagamiOS the paper skeleton is created early (at hypothesis time), and each stage of work updates it. "Writing the paper" as a phase disappears; what remains at the end is polishing an artifact that has been true to the project all along.

## What KagamiOS is not

- **Not a literature survey tool.** Survey is one continuous background process among many, not the product. (This is stated in `questions.md`; the design must enforce it — the strongest gravitational pull during implementation will be toward becoming exactly this.)
- **Not an autonomous scientist.** End-to-end "AI Scientist" systems (idea → experiments → paper without human gates) produce work that is fluent and mostly worthless, because the steps that require taste — problem selection, interpretation of ambiguous results, deciding what to claim — are precisely the ones automation does worst. KagamiOS automates *around* those steps, never through them.
- **Not a project-management overlay.** If KagamiOS degenerates into Jira-for-research — status fields updated to satisfy the tool rather than to think — it has failed. Every artifact must earn its keep (see `principles.md`, "Process must pay rent").
- **Not a proposal generator.** Generating plausible research plans is easy for LLMs and nearly valueless. The value is in the *discipline of transformation*: forcing a vague intuition through stages where it can die cheaply.

## Who it is for, first

The first user is a single researcher (the author) running the Signature-methods-for-deep-learning investigation. That project is the dogfooding case: every design decision in these documents should be testable by asking "would this have helped, or would it have been overhead, in the Signature survey?" Multi-researcher labs are explicitly out of scope for v1 (see `open_questions.md`).

## Success criteria

KagamiOS is working if, after using it on one real project:

1. **Faster kills.** Bad directions die in days (at triage or pilot), not months. Time-to-kill is the single best proxy metric for research process quality.
2. **No lost reasoning.** Any past decision ("why did we not compare against method X?") is answerable from artifacts in under a minute.
3. **Cold-start resumption.** The project can be resumed after a long pause, by the researcher or an AI agent, from artifacts alone.
4. **Claims match evidence.** At writing time, every claim in the paper skeleton links to supporting artifacts, and unsupported claims are visible as such.
5. **The researcher still wants to use it** on the second project. Voluntary adoption is the test that the process is paying rent.
