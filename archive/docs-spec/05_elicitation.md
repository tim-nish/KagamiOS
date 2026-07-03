# 05 — The Elicitation Kernel

The core of the system: how questions are generated, filtered, asked, recorded, and audited. Questions are **derived at runtime** from the diff between the artifact under construction and its machine-readable schema (`07_runtime.md` §1), filtered through a rent test, and asked **against evidence the system has already computed**. A template asks what its author anticipated; the kernel asks what this run actually lacks.

## 1. The unit of work: the unknown

At any moment the system is producing or repairing some artifact. The artifact's schema and current evidence define a set of **unknowns**: unfilled fields, unresolved branches, unvalidated assumptions. Enumeration is deterministic (a schema diff — E8); each unknown is then triaged into exactly one class, seeded by the schema's `unknown_class_hint`:

| Class | Meaning | Resolution |
|---|---|---|
| **Computable** | resolvable by search, reading, synthesis, or inference over existing artifacts | the system resolves it — never ask the researcher what the literature can answer |
| **Human-only** | encodes interest, taste, constraints, priorities, or judgment | candidate question, *if blocking* |
| **Deferrable** | a default suffices for now | AI default applied and recorded; surfaces later only if it becomes blocking |

Only **human-only ∧ blocking** unknowns become questions. The test for human-only is concrete: *would two equally competent researchers with the same corpus answer differently?* Yes → human-only. No → computable, and asking it insults the researcher's time.

## 2. The kernel loop

```
loop:
  1. FRONTIER   Select the next artifact to build or repair, by fixed priority:
                (a) items blocking the next human gate
                (b) stale repairs on the path to that gate
                (c) Confidence Checklist holes
                (d) deferred/opportunistic work.
                Every frontier decision is logged with its reason class (S10).
  2. ATTEMPT    Draft or repair it from accepted artifacts + computation
                (per the dispatch table, 07_runtime.md §5). Enumerate unknowns.
  3. TRIAGE     computable → resolve now; deferrable → apply default, record it;
                human-only+blocking → queue.
  4. ASK        Queue nonempty: batch into a question set (≤5, ranked by leverage),
                each a question card. Otherwise: present the draft for review —
                review comments are answers too.
  5. CONSUME    Write answers to the ledger; pin the artifact's elicited_from;
                mark stale anything that cited a changed answer.
  6. repeat until the Decide gate closes (or the intuition dissolves).
```

Two properties:

- **Review is elicitation.** When the researcher edits a draft ("merge these two clusters"), each edit resolves an unknown the system didn't know it had — and flips the edited span's provenance to human-confirmed (`07_runtime.md` §1). Gate reviews are the highest-bandwidth elicitation channel; explicit questions are for unknowns a draft cannot surface.
- **The loop never blocks silently.** An unanswered blocking unknown gets its stated default and the artifact is flagged `provisional`. Progress with visible assumptions beats stalling. The count of provisional inputs at Decide is surfaced at the gate — it is the cheapest proxy for decision fragility.

The ASK step is the system's single-threaded surface: parallel workers (`07_runtime.md` §7) emit candidate unknowns into the queue, but one scheduler owns batching and sequencing (E4).

## 3. Question rent: targets and leverage classes

Per E2, a question is well-formed only if it declares a **target** (artifact field) and a **leverage class**:

| Class | The answer changes… | Primary target | Typical state |
|---|---|---|---|
| L1 Search scope | which areas are searched | Inquiry Frame (boundaries, exclusions) | Frame |
| L2 Clustering | how the field is partitioned | Field Map (cluster set, granularity) | Map |
| L3 Representativeness | which papers count as defining | Cluster Dossier (representative set) | Deepen |
| L4 Community priority | which clusters/groups get attention | Field Map priorities; depth budgets | Map / Deepen |
| L5 Gap meaningfulness | which gaps count | Gap Register (`meaningful_to_me`) | Locate |
| L6 Candidate survival | which directions survive | Candidate Directions; Direction Decision | Propose / Decide |

A question fitting no class is computed, defaulted, or dropped. (Exception: the two sanctioned E6 unprimed questions, leverage L6 by way of preserving the researcher's independent signal.) The "typical state" column is a default, maintained against evidence: cross-run analytics may propose re-ordering when a class asked early is systematically revised later (`08_observability.md` §5) — proposals only, adopted by review.

## 4. The question card

```yaml
question:      # one sentence, concrete, grounded in shown evidence
why_asked:     # target field + leverage class ("fills field-map.scope;
               #   changes which clusters get deep-dived — L2/L4")
evidence:      # the computed material the question is asked against
default:       # the AI's proposed answer; silence/skip = accept default
reversibility: # cost of changing later (usually: "cheap — dependents flagged stale")
```

An empty `evidence` field is legal only for the two E6 unprimed questions. The `why_asked` line gives the researcher a legitimate veto: "this doesn't matter for me" is a recorded answer, and the default applies.

**Form ladder (E3), cheapest first:** (1) confirm a default → (2) menu over computed options → (3) rank/allocate → (4) free text (reserved for E6 unprimed answers and genuinely open constraints).

**Batching (E4):** sets of ≤5, at review gates by preference, ranked by leverage. Mid-state blocking asks are allowed but rare — a state that keeps interrupting is mis-scoped. Nothing is asked "while we're at it."

## 5. The Question Ledger

Every asked question and every applied default is a versioned ledger entry:

```yaml
id: q-014
state: Map
question: "Which of these 5 clusters are in scope?"
form: menu                                       # class key: leverage × state × form
leverage: [L2, L4]
target: field-map.scope
evidence_shown: field-map@v2
answer: "1,2,4 in; 3 background; 5 out"          # or: default_applied
answered_at: ...
consumed_by: [field-map@v3, depth-budget@v1]     # stamped as artifacts pin it
superseded_by: q-031                             # if later revised
```

Three jobs: **(1) Staleness for answers (E5)** — revising q-014 stales everything that pinned it; changing your mind is cheap and safe, for the researcher *and* the machine (lazy repair, P7). **(2) Rent audit (E2)** — empty `consumed_by`, or consumption with zero downstream divergence, marks a kernel bug; measured via the event log (`08_observability.md` §3). **(3) The trace** — the question/answer sequence is the record of how a vague intuition became a decision. The `form`/`leverage`/`state` triple is the stable **question-class key** used for cross-run learning; the E6 unprimed questions and the P3 triad are permanently exempt from statistical demotion.

## 6. Anchoring discipline and generation windows (E6)

**Generation windows.** Each artifact type has an earliest state before which the AI may not draft it, enforced against the per-cluster derived state (`03_state_machine.md` §5). The binding one: *no direction-shaped content before the Gap Register is accepted.* Direction-like text appearing early is quarantined into `premature_ideas`, visible only after Propose opens (and harvestable into the Decision's *spawned* section). Early-state AI output is descriptive or interrogative, never creative. The window constrains **timing only**: once open, candidates may be generated from any accepted evidence — gaps or synthesis (S1).

**Ask-before-show.** At Frame: "Before I map anything — what do you suspect the interesting angle is?" At Propose: "Before I show candidates — which direction are you leaning toward?" Both are ledger entries written before AI output is displayed. At Decide, the diff between unprimed lean and final choice is shown — making it visible whether the tool led or followed.

## 7. Worked example: the Signature-methods intuition

Intuition Note: *"Signature methods may become useful building blocks for deep learning."*

**Frame.** Unprimed hunch recorded first (E6). Shallow orientation pass, then:
> *q1 (menu, L1).* "'Building blocks for deep learning' reads four ways: (a) signature transforms as architecture components, (b) signatures as feature maps for time-series representation learning, (c) signature theory as an analysis tool for nets, (d) downstream applications. Which are in scope? **Default: a+b.**"
> *q2 (confirm, L1).* "I'll treat rough-path theory as background, not a survey target — object?"
> *q3 (free text, constraints → Researcher Profile).* "Hard constraints worth respecting — compute scale, math depth, time horizon?"

*Not asked:* "what is a signature?" (computable), "who works on this?" (computable), "what's your research question?" (doesn't exist yet — that's the output).

**Map.** Embedding + citation-graph partition (E8), cluster cards drafted, alternative cut offered, then:
> *q4 (menu + rank, L2/L4).* "The field clusters into: (1) deep signature architectures, (2) neural CDEs, (3) signature kernels, (4) log-signature efficiency, (5) expressiveness theory, (6) applications. Cluster cards attached. Which are in scope; rank the in-scope ones. **Default: 1,2,3 deep; 4,5 background; 6 out.**"
> *q5 (confirm, L4).* "Clusters 1–3 share recurring groups [entity refs]. Prioritize their lineages in dossiers — object?"

**Deepen.** Parallel dossiers; questions sparse — mostly review-as-elicitation, plus:
> *q6 (menu, L3).* "For cluster 2, these 4 as defining papers [cards]. These are the ones *you* read. Swap any? **Default: as listed.**"
> *q7 (confirm, L4/L1).* "Cluster 3 keeps citing into GP-kernel literature. Expand one hop as background, ~a day of reading? **Default: yes, background-depth.**"

**Synthesize.** Computable from accepted dossiers; the researcher reviews:
> *q8 (confirm, L5-setup).* "The matrix says signatures compete with learned encoders on data-efficiency and irregular sampling, and lose on scalability. Your reading reactions weight irregular sampling heavily — confirm? This weights the gap analysis."

**Locate.** Gaps enumerated, each forced through `why_does_this_gap_exist` (one settled by a two-hour micro-probe: the naive baseline does *not* already work):
> *q9 (rank + annotate, L5).* "Seven gaps survived the screen [register attached]. Mark each: meaningful / real-but-not-mine / suspicious."

**Propose → Decide.** Unprimed lean recorded; candidates generated from accepted gaps *and* one synthesis-rooted transplant (signature kernels × the attention-efficiency trend), each with fit notes and red-team lines:
> *q10 (rank, L6).* "Four candidates [cards]. Your unprimed lean matched candidate B. Rank them; the Decision memo requires a written 'why this over the others', and each non-selected candidate gets parked-with-conditions or rejected-with-reason."

Total researcher-facing questions: ten to fifteen across the run, each grounded in shown evidence, each with a default, each feeding a named artifact field.
