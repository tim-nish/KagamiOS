# KagamiOS — Design Principles

These are the first principles the design must hold, each with its rationale and its consequence for the system. Several directly contradict assumptions in the founding pipeline; those contradictions are called out.

---

## P1. Artifacts are the state; conversation is exhaust

**Rationale.** This is BMAD's deepest insight and the one that transfers fully. LLM context is ephemeral and human memory is worse. If the state of a project lives in chat history or in the researcher's head, the project cannot be resumed, audited, or handed off. If it lives in versioned documents with explicit dependencies, any agent can pick up the next unit of work.

**Consequence.** Every state transition in the system is defined by artifacts produced, not by activities performed. "We discussed the gap analysis" is not a state change; a Gap Register with reviewed status is.

## P2. Backward transitions are first-class, not failures

**Rationale.** The founding pipeline is a waterfall: ten stages, all arrows pointing down. In software this is merely risky; in research it is *definitionally wrong*, because the purpose of an experiment is to test a hypothesis that may be false. A negative result that sends you back to Hypotheses — or all the way back to Research Questions — is the system working, not the system failing. A workflow whose diagram cannot represent its most common transition will be abandoned the first time reality diverges from it.

**Consequence.** The state machine (`state_machine.md`) makes loop-back transitions explicit, named, and cheap. Rework is budgeted, not treated as exception handling. Every backward transition produces a Decision Record explaining what was learned.

## P3. Three decisions belong to the human, permanently

**Rationale.** Not all human-in-the-loop gates are equal. Most gates are review gates (the human checks AI output — these can loosen with trust). Three are *constitutive* gates: delegating them means the human is no longer doing research.

1. **Problem selection.** What is worth working on is taste — Hamming's question. An AI can score novelty and feasibility; it cannot know what you find important, and importance is not in the training data.
2. **Kill / pivot / continue.** Resource allocation under uncertainty against your own goals.
3. **Claims.** What the paper asserts, and with what strength. The researcher's name is on it; the epistemic commitment must be theirs.

**Consequence.** These three gates are structurally un-automatable in KagamiOS: the artifacts they produce (Triage Memo verdict, Kill Memo, claim strength in the Claim Graph) have a human-authored field the AI cannot write. Everything else — search, summarization, consistency checking, gap enumeration, experiment bookkeeping, first drafts of any artifact — is fair game for automation, with review.

## P4. AI's highest-leverage role is adversarial, not generative

**Rationale.** The failure mode of AI-assisted research is not bad generation; it is *automation bias* — the researcher rubber-stamping fluent AI output. An AI that proposes research gaps produces plausible-sounding gaps everyone else's AI also finds. An AI that attacks your hypothesis ("what would falsify this?", "why does this gap exist — is it hard, uninteresting, or already filled?", "which baseline would a reviewer demand?") makes your reasoning stronger without replacing it. Generation homogenizes; critique sharpens.

**Consequence.** For every generative AI role in the workflow there is a paired critic role, and the critic runs on human-authored artifacts too, not only AI-drafted ones. The Gap Register schema hard-codes the adversarial question (see `artifacts.md`). Review gates present the critic's objections alongside the draft.

## P5. Hold multiple working hypotheses; uncertainty is a field, not a bug

**Rationale.** This is old, hard-won methodology: Chamberlin (1890) argued that a researcher with one hypothesis becomes its advocate; the cure is to hold several in parallel. Platt's *strong inference* (1964) turns this into a workflow — design experiments that discriminate between hypotheses rather than confirm one. The founding pipeline's singular "Hypotheses → Experiment Design" flow invites premature convergence, and `questions.md` itself asks the right question: "How should uncertainty be represented instead of forcing early conclusions?"

**Consequence.** The Hypothesis stage produces a *set* of Hypothesis Cards, each with competing alternatives and falsification criteria. Every artifact carries a confidence/status field (`speculation | supported | contested | refuted | superseded`). Experiment Designs must state which hypotheses they discriminate between. The system never forces a single answer where the honest state is "three candidates, unresolved."

## P6. Cheapest test first — escalate commitment through gates

**Rationale.** The pipeline goes Hypotheses → Experiment Design → Implementation Plan, i.e., straight from idea to full commitment. Real research interposes cheap probes: a back-of-envelope calculation, a 30-minute script on toy data, an email to someone who tried it. Stage-gate R&D processes (Cooper) and drug-discovery pipelines exist precisely because cost per stage escalates by orders of magnitude — the gate's job is to spend a little to avoid spending a lot. ML research has cheap iterations, so gates should be *light* — but a pilot stage is still the highest-ROI addition to the founding pipeline.

**Consequence.** A **Probe** state sits between Hypothesize and full Experiment Design. Its artifact (Pilot Report) is deliberately scrappy — hours of work, not days — and its gate is a kill/continue decision. Also consequence: early stages (Triage) are minutes of work; only surviving ideas earn expensive stages (full survey).

## P7. Staleness propagates — build-system semantics over the artifact graph

**Rationale.** Artifacts depend on each other: an Experiment Design depends on a Hypothesis Card, which depends on a Gap Register entry, which depends on the Survey. When an upstream artifact changes — a new paper fills your gap, a pilot refutes an assumption — downstream artifacts are silently invalid. Humans are terrible at tracking this; build systems are perfect at it. This is the mechanism that makes P2's loops *safe*: you can revise anything upstream because the system tells you exactly what downstream is now suspect.

**Consequence.** Every artifact declares `depends_on`. A change to an accepted artifact marks its dependents `stale`. Stale artifacts are not deleted or auto-regenerated; they are flagged for human re-review (the change might not matter — that judgment is cheap for a human and unreliable for a machine). This one mechanism may be KagamiOS's most distinctive feature; no existing research tool has it.

## P8. Write the paper backwards from day one

**Rationale.** See `vision.md`, Reframe 3. Whitesides' outline method and the Heilmeier Catechism both exploit the same fact: articulating the end-state claim exposes reasoning gaps earlier than any other exercise. Additionally, the paper skeleton is the natural *integration point* — the artifact where survey, gaps, hypotheses, and results must cohere, so inconsistencies between them surface as visible holes.

**Consequence.** The Paper Skeleton artifact is created at the Hypothesize stage at the latest. Later stages *update* it. The Triage Memo is literally the Heilmeier questions. There is no "Paper Draft" state; there is a Communicate state whose work is polishing and submission.

## P9. Process must pay rent

**Rationale.** The gravest risk to KagamiOS is not a wrong state machine; it is *process theater* — a beautiful formalism the researcher abandons in week two because updating artifacts costs more than the confusion they prevent. Researchers have rejected heavyweight process for a century, usually correctly. BMAD gets away with ceremony because its users are AI agents that do not feel friction; KagamiOS's human is in the loop constantly and will feel every field.

**Consequence.** (a) Every artifact must be justified by a failure it prevents, and the AI drafts everything it can — the human's job is deciding and reviewing, rarely typing. (b) The system degrades gracefully: a project tracked only as an Intuition Note plus a running notebook is valid; states can be skipped with an explicit (one-line) waiver. (c) Artifact schemas start minimal and grow only under demonstrated need. (d) If dogfooding shows an artifact is always rubber-stamped, delete it.

## P10. Negative results and kills are products, not waste

**Rationale.** The most systematically lost knowledge in research is *why abandoned directions were abandoned*. Labs re-explore dead ends because the death certificate was never written. Publication bias makes this worse externally; nothing forces it internally.

**Consequence.** Kill Memos and refuted Hypothesis Cards are permanent, searchable, first-class artifacts. The portfolio layer keeps killed bets visible with their revival conditions ("revisit if inference costs drop 10×"). A killed project with a good Kill Memo is a *successful* run of KagamiOS.

## P11. Enter anywhere

**Rationale.** The founding pipeline assumes research begins with a vague intuition about a technique. That is one entry mode among several: problem-first ("this metric is stuck"), anomaly-first ("this result makes no sense"), resource-first ("we just got this dataset/compute"), literature-first ("this new paper enables X"), collaboration-first ("co-author brings a half-built project"). Forcing every start through Idea → Research Questions misdescribes most research and will be worked around, breaking the artifact trail at its origin.

**Consequence.** Any state can be an entry point. Entering mid-machine creates the upstream artifacts *retroactively and minimally* (a one-paragraph Intuition Note reconstructing why this is interesting) so the dependency graph is rooted, without pretending the process was followed forward.
