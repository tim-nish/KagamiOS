# KagamiOS v2 — The Elicitation Kernel

This is the core of the redesign. `2_questions.md` identifies BMAD's deepest strength as *information elicitation design*: asking the right questions at the right time so agents can act with rising accuracy and autonomy. This document specifies that mechanism for research discovery — how questions are generated, filtered, asked, recorded, and audited.

BMAD's version is template-embedded: its document templates contain elicitation prompts written at authoring time, so the Analyst agent interrogates the user instead of hallucinating requirements. KagamiOS generalizes this: questions are **derived at runtime** from the gap between the artifact under construction and its schema, filtered through a rent test, and asked **against evidence the system has already computed**. The template asks what its author anticipated; the kernel asks what this project actually lacks.

---

## 1. The unit of work: the unknown

At any moment the system is trying to produce or update some artifact (chosen by the scheduler — see `state_machine.md` §1). The artifact's schema and the current evidence define a set of **unknowns**: unfilled fields, unresolved branches, unvalidated assumptions. Every unknown is triaged into exactly one of three classes:

| Class | Meaning | Resolution |
|---|---|---|
| **Computable** | Resolvable by search, reading, synthesis, or inference over existing artifacts | The system resolves it. Never ask the researcher something the literature can answer. |
| **Human-only** | Encodes the researcher's interest, taste, constraints, priorities, or judgment — not in any training data or corpus | Candidate question, *if blocking* |
| **Deferrable** | Doesn't block the next artifact at acceptable quality; a default suffices for now | AI default applied and recorded; may surface later when it becomes blocking |

Only **human-only ∧ blocking** unknowns become questions. This triage is the single most important filter in the system: it is what makes KagamiOS interrogate the researcher less than a form and more usefully than a chat.

The test for "human-only" is concrete: *would two equally competent researchers with the same corpus answer differently?* If yes (interest, taste, constraints), it's human-only. If no (who cites whom, when a subfield emerged, which benchmark a paper used), it's computable, and asking it insults the researcher's time.

## 2. The kernel loop

```
loop:
  1. FRONTIER   Determine the next artifact to build or repair
                (from the state map + staleness flags + Confidence Checklist holes).
  2. ATTEMPT    Draft it from accepted artifacts + computation (search, clustering,
                synthesis). Enumerate remaining unknowns.
  3. TRIAGE     Classify each unknown: computable → resolve now;
                deferrable → apply default, record it; human-only+blocking → queue.
  4. ASK        If the queue is nonempty: batch into a question set (≤5, ranked by
                leverage), each as a question card with target, default, reversibility.
                Otherwise: present the draft for review — review comments are answers too.
  5. CONSUME    Write answers to the ledger; stamp the artifact's `elicited_from`;
                mark stale anything that cited a changed answer.
  6. repeat until the Decide gate closes (or the intuition dissolves).
```

Two properties worth naming:

- **Review is elicitation.** When the researcher edits a draft Field Map ("merge these two clusters", "this 'cluster' is just one group's output"), each edit resolves an unknown the system didn't know it had. Gate reviews are the highest-bandwidth elicitation channel; explicit questions are for unknowns a draft cannot surface.
- **The loop never blocks silently.** If a blocking human-only unknown goes unanswered, the system proceeds with its stated default and flags the artifact `provisional`. Progress with visible assumptions beats stalling.

## 3. Question rent: targets and leverage classes

Per E2, a question is well-formed only if it declares a **target** (the artifact field its answer fills) and a **leverage class**. The six classes come directly from `2_questions.md`, and they map onto the machine like this:

| Leverage class | The answer changes… | Primary target artifact | Typical state |
|---|---|---|---|
| L1 Search scope | which research areas are searched | Inquiry Frame (boundaries, exclusions) | Frame |
| L2 Clustering | how the field is partitioned into groups | Field Map (cluster set, granularity) | Map |
| L3 Representativeness | which papers count as defining | Cluster Dossier (representative set) | Deepen |
| L4 Community priority | which groups/researchers get attention | Field Map priorities; depth budgets | Map / Deepen |
| L5 Gap meaningfulness | which gaps are considered meaningful | Gap Register (`meaningful_to_me`) | Locate |
| L6 Candidate survival | which directions survive comparison | Candidate Directions; Direction Decision | Propose / Decide |

A proposed question that fits no class is, by definition, not worth the researcher's attention — it gets computed, defaulted, or dropped. (The one exception: the two sanctioned unprimed questions of E6, whose leverage class is L6 by way of preserving the researcher's independent signal.)

## 4. The question card

Every question the researcher sees carries the same five parts:

```yaml
question:      # one sentence, concrete, grounded in shown evidence
why_asked:     # one line: target field + leverage class ("fills Field Map
               #   scope; changes which clusters get deep-dived — L2/L4")
evidence:      # the computed material the question is asked against
               #   (the cluster list, the candidate paper set, the draft taxonomy)
default:       # the AI's proposed answer; silence/skip = accept default
reversibility: # what it costs to change this answer later
               #   (usually: "cheap — dependents will be flagged stale")
```

The `why_asked` line keeps the system honest and gives the researcher a legitimate veto: "this doesn't matter for me" is a recorded answer, and the default applies. The `evidence` field enforces E3 — a card with an empty evidence field is only legal for the two E6 unprimed questions.

**Form ladder (E3), cheapest first.** (1) *Confirm a default:* "I'm treating rough-path theory as background, not a cluster of interest — object?" (2) *Menu:* "Which of these five clusters are in scope? Default: 1, 2, 4." (3) *Rank/allocate:* "Order these three clusters by how much reading time they deserve." (4) *Free text:* reserved for E6 unprimed hunches and genuinely open constraints.

**Batching (E4).** Questions surface in sets of at most five, at review gates by preference, ranked by leverage. Mid-state blocking asks are allowed but should be rare — a state that keeps interrupting is mis-scoped. Nothing is asked "while we're at it": a deferrable unknown waits until it blocks.

## 5. The Question Ledger

Every asked question — and every applied default — becomes a ledger entry:

```yaml
id: q-014
state: Map
question: "Which of these 5 clusters are in scope?"
leverage: [L2, L4]
target: field-map.scope
evidence_shown: field-map-draft-v2
answer: "1,2,4 in; 3 background; 5 out"        # or: default_applied
answered_at: ...
consumed_by: [field-map-v3, depth-budget-v1]    # stamped as artifacts cite it
superseded_by: q-031                            # if later revised
```

The ledger does three jobs:

1. **Staleness for answers (E5).** Artifacts cite the answers they consumed via `elicited_from`. Revising q-014 marks `field-map-v3` and everything downstream stale — changing your mind is cheap and safe, which is what makes fast, low-anxiety answering rational.
2. **Rent audit (E2, retroactive).** A question whose `consumed_by` stays empty was a bad question — a kernel bug, reviewable and fixable. Success criterion 5 in `vision.md` is checked here.
3. **Elicitation trace.** The ledger is the record of how a vague intuition became a decision — which is precisely the reasoning process the founding `questions.md` wanted made traceable. In discovery, the question/answer sequence *is* that trace.

## 6. Anchoring discipline and generation windows (E6)

Two rules protect the researcher's independent signal:

**Generation windows.** Each artifact type has an earliest state before which the AI may not draft it. The binding one: *no direction-shaped content — candidate directions, "promising avenues", "future work" framings — before the Gap Register is accepted.* If direction-like text appears in an early synthesis, it is quarantined into a `premature_ideas` holding pen, visible only after Propose opens. Early-state AI output is descriptive (what exists) and interrogative (what do you mean) — never creative.

**Ask-before-show.** At Frame: "Before I map anything — what do you currently suspect the interesting angle is?" At Propose: "Before I show generated candidates — which direction are you already leaning toward, given everything you've read?" Both answers are ledger entries written before AI output is displayed. At Decide, the comparison between the unprimed lean and the final choice is shown — making it visible whether the tool led the researcher or followed them.

## 7. Worked example: the Signature-methods intuition

Starting point (Intuition Note): *"Signature methods may become useful building blocks for deep learning."* What the kernel actually asks, per state — and, equally important, what it does *not* ask.

**Frame.** The system first records the E6 unprimed hunch ("what do you suspect the angle is?"). It then does a shallow orientation pass (computable) and asks against it:

> *q1 (menu, L1).* "'Building blocks for deep learning' reads at least four ways: (a) signature transforms as architecture components / layers, (b) signatures as feature maps for time-series representation learning, (c) signature theory as an analysis tool for existing nets, (d) downstream applications (finance, health). Which are in scope? **Default: a+b.**"
> *q2 (confirm, L1).* "I'll treat rough-path theory as background you'll absorb as needed, not a survey target — object?"
> *q3 (free text, constraints → Researcher Profile).* "Any hard constraints worth respecting — compute scale, math depth you'll tolerate, time horizon?"

Not asked: "what is a signature?" (computable), "who works on this?" (computable), "what's your research question?" (doesn't exist yet — that's the *output*).

**Map.** The system searches, clusters, and drafts a Field Map — then asks:

> *q4 (menu + rank, L2/L4).* "The field clusters into: (1) deep signature architectures (sig-layers, deep signature transforms), (2) neural CDEs / continuous-time models, (3) signature kernels, (4) log-signature methods & efficiency, (5) theory of expressiveness/universality, (6) application-driven work. Evidence: cluster cards attached, ~15 papers each. Which are in scope, and rank the in-scope ones by reading priority. **Default: 1,2,3 deep; 4,5 background; 6 out.**"
> *q5 (confirm, L4).* "Clusters 1–3 share a small set of recurring groups [named]. I'll prioritize their lineages when building dossiers — object?"

**Deepen.** Dossiers are drafted per in-scope cluster (history, representative papers, people, frontier). Questions here are sparse — mostly review-as-elicitation, plus:

> *q6 (menu, L3).* "For cluster 2 (neural CDEs) I propose these 4 as the defining papers [cards with one-line contributions]. These are the ones *you* read, not just me. Swap any? **Default: as listed.**"
> *q7 (confirm, L4/L1).* "The history of cluster 3 keeps citing back into Gaussian-process kernel literature. Expand scope one hop into GP kernels as background, at ~a day of reading? **Default: yes, background-depth only.**"

**Synthesize.** Cross-cluster comparison and trends are computable from accepted dossiers; the researcher reviews rather than answers. One typical card:

> *q8 (confirm, L5-setup).* "The comparison matrix says signatures compete with learned encoders mainly on data-efficiency and irregular sampling, and lose on scalability. Your reading reactions suggest you weight irregular-sampling robustness heavily — confirm? This will weight the gap analysis."

**Locate.** The AI enumerates candidate gaps, each forced through `why_does_this_gap_exist` (inherited from v1). The researcher's question is the constitutive one:

> *q9 (rank + annotate, L5).* "Seven gaps survived the adversarial screen [register attached, each with its existence-explanation]. Mark each: meaningful to you / real but not mine / suspicious. This is a human-only field."

**Propose → Decide.** The E6 unprimed lean is recorded; only then are Candidate Direction cards generated *from accepted gaps only*, each with fit-to-profile notes. Final cards:

> *q10 (rank, L6).* "Four candidates [cards: direction, supporting gaps, defining papers you've read, what pursuing it needs, why-now]. Your unprimed lean matched candidate B. Rank them; the Decision memo will require a written 'why this over the others'."

Total researcher-facing questions across the whole run: on the order of ten to fifteen, each grounded in shown evidence, each with a default, each feeding a named artifact field. That is the BMAD inheritance, delivered: minimal cognitive load, rising system autonomy, and a complete trace from vague intuition to confident choice.
