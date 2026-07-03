# KagamiOS v2 — Design Principles

Two parts: an audit of the v1 principles (P1–P11) under the discovery scope, and the new elicitation principles (E1–E7) that the scope change makes central.

---

## 1. Inheritance audit of the v1 principles

| v1 | Verdict | Disposition under the discovery scope |
|---|---|---|
| **P1** Artifacts are the state; conversation is exhaust | **Kept, extended** | Unchanged — with one addition: *answers to elicitation questions are artifacts too* (ledger entries), so even the conversation's load-bearing residue is captured. See E5. |
| **P2** Backward transitions are first-class | **Kept, fewer loops** | Discovery loops less violently than experimentation, but the most important discovery event is still backward: reading the field reframes the intuition. Frame is the most-revised artifact in the system, and that is the system working. |
| **P3** Three decisions belong to the human | **Adapted** | The lifecycle triad (problem selection / kill / claims) becomes the discovery triad: **(1) scope & attention allocation** — which clusters are in, where reading time goes; **(2) gap meaningfulness** — which gaps are real and worth taking; **(3) direction selection** — the terminal choice. Same rule: these have human-only fields the AI cannot write. |
| **P4** AI's highest-leverage role is adversarial | **Kept, plus generation windows** | The Skeptic survives intact (it attacks framings, clusterings, and gaps). New structural enforcement: the AI may not generate direction-shaped content at all before the Gap Register is accepted (E6). |
| **P5** Multiple working hypotheses | **Adapted to candidates** | No hypotheses yet — but the same anti-advocacy logic applies one level up: the Propose state must produce *plural, competing* Candidate Directions, and the Decide gate requires a written comparison, never a single anointed option. |
| **P6** Cheapest test first | **Adapted to questions and reading** | No experiments to stage-gate. The escalation ladder is attention: cheap breadth (Map) before expensive depth (Deepen), and — the elicitation version — the cheapest *question form* first: confirm-a-default before menu before free text (E3). Depth budgets (`state_machine.md` §5) are the stage gates. |
| **P7** Staleness propagates | **Kept, lighter** | Discovery runs in weeks, so literature drift matters less *during* a run — but two staleness sources remain load-bearing: (a) a revised elicitation answer marks every artifact that cited it stale; (b) after a Direction Decision, monitoring can mark the *decision itself* stale ("a paper filling your gap appeared"). |
| **P8** Write the paper backwards | **Retired, logic reborn** | There is no paper. The surviving logic: the terminal artifact is drafted first. The **Confidence Checklist** (what the researcher must know to choose) is created at Frame, and its holes are the to-do list. See `vision.md`. |
| **P9** Process must pay rent | **Kept, extended to questions** | Now applies to the system's outputs *and its inputs*: every artifact must earn its keep, and every question asked of the researcher must earn its answer (E2). Cognitive load is the currency discovery is most likely to overspend. |
| **P10** Negative results are products | **Kept as dissolution** | The discovery-scale kill is the **Dissolution Memo**: "this intuition is already a mature field / was tried and abandoned in the 2000s / dissolves under scrutiny." Reaching it in days is a successful run. |
| **P11** Enter anywhere | **Kept, discovery entry modes** | Intuition-first is one mode. Others: paper-first ("this paper excites me"), field-first ("I want to enter area X"), problem-first ("this metric is stuck"), tool-first ("I have this dataset/skill — where is it valuable?"). All backfill a minimal Intuition Note and enter at Frame. |

---

## 2. New principles: elicitation (E1–E7)

These did not exist in v1 because v1 treated interaction as one mechanism among many. `2_questions.md` corrects this: interaction is part of the reasoning architecture. The E-principles govern it.

### E1. Interaction is architecture: a question is a state-transition request

**Rationale.** The system advances by producing artifacts; artifacts have required fields; some fields cannot be computed — they encode the researcher's interest, taste, constraints, or judgment. A question to the researcher is therefore not conversation: it is the system requesting the missing input for a specific transition, exactly as a build system reports a missing dependency.

**Consequence.** The elicitation loop *is* the scheduler (`elicitation.md` §2). "What should happen next?" is always answered by "what is the highest-leverage unresolved unknown, and who — machine or human — can resolve it?" There is no chat surface separate from the workflow; every exchange is loop traffic.

### E2. Every question pays rent

**Rationale.** Directly from `2_questions.md`. Researcher attention is the scarcest resource in the system, and question fatigue is the discovery-scope version of process theater: three lazy questions and the researcher stops answering thoughtfully; ten and they stop answering at all.

**Consequence.** A question is well-formed only if it declares (a) a **target**: the artifact field or branch its answer fills, and (b) a **leverage class**: which of the six downstream effects it changes — search scope, clustering, representativeness, community priority, gap meaningfulness, or candidate survival (`elicitation.md` §3). Questions that cannot name both are rejected by construction. The ledger audit (§5) retroactively checks that answers were actually consumed.

### E3. Elicit against evidence, not against a blank page

**Rationale.** "What are you interested in — theory, representation learning, time-series, robustness, efficiency, or applications?" is a hard question in the abstract and an easy one against a map. The system has cheap compute and the researcher has expensive attention, so the system must always spend compute first: search, cluster, draft — *then* ask, presenting the question as a choice over concrete evidence ("the field splits into these five clusters — which are in scope?"). This is also the main cognitive-load reducer: recognition is cheaper than recall, and selection is cheaper than generation.

**Consequence.** Question forms are ranked by load, cheapest preferred: **confirm a default** ("I'm assuming X — object?") → **select from a computed menu** → **rank / allocate** → **free text** (rare, justified). Every question ships with the AI's proposed default, so accepting silently is always a valid, cheap answer. Open-ended questions are permitted only where the researcher's unprimed view is itself the datum (see E6).

### E4. Ask at the last responsible moment

**Rationale.** Upfront intake forms ask everything while the researcher knows the least and remembers the answers worst. An answer elicited just before it is consumed is better-informed (the researcher has seen the intervening evidence), better-motivated (its purpose is visible), and fresher when used.

**Consequence.** No intake stage exists. Questions surface in small batches at review gates, plus rare blocking asks mid-state. Each question card shows *why now* — the artifact waiting on it. Deferrable unknowns are explicitly deferred with the AI's default in place, not asked "while we're at it."

### E5. Answers are revisable artifacts

**Rationale.** Fear of answering wrong is a major source of cognitive load — the researcher stalls on "which clusters are in scope?" because it feels irreversible. It must not be. If answers are versioned ledger entries and every artifact records which answers it consumed (`elicited_from`), then changing an answer simply marks the dependents stale, exactly like any upstream artifact change (P7).

**Consequence.** Each question card states its **reversibility** ("cheap to change later — dependents will be flagged"). The researcher is explicitly encouraged to answer directionally and fast; the system, not the researcher, tracks the consequences. "Skip — use your default" is always a recordable answer.

### E6. Anchoring discipline: the researcher's view is elicited before the AI's is shown

**Rationale.** The deep failure mode of AI-assisted discovery is not bad output but *homogenization*: the AI's fluent framing becomes the researcher's framing, and everyone running the same tool over the same literature converges on the same "obvious" directions (v1's Q3, now central). Once an AI-proposed direction is seen, the researcher's independent signal is contaminated and cannot be recovered.

**Consequence.** Two mechanisms. **Generation windows:** each artifact type has an earliest state before which the AI may not draft it — in particular, no direction-shaped content before the Gap Register is accepted. **Ask-before-show:** at the two contamination-critical points (Frame: "what do you suspect the interesting angle is?"; Propose: "before I show candidates — which direction are you already leaning toward?"), the researcher's unprimed answer is recorded in the ledger *first*. This is the one sanctioned use of open-ended questions (E3 exception), and it preserves both the researcher's originality and an audit trail of whether the tool led or followed.

### E7. Confidence is the product; understanding cannot be delegated

**Rationale.** The terminal condition is subjective — the researcher *confidently* selects. A pile of excellent AI-written dossiers the researcher hasn't internalized fails the mission even if every artifact is accepted. Summaries inform; only reading and choosing build the taste-level familiarity the endpoint requires.

**Consequence.** (a) Representative papers carry a `human_read` flag with a one-line human reaction; the Decide gate requires it for the papers defining each surviving candidate. (b) The Confidence Checklist is checked against *traces* (what was read, what was human-annotated), since understanding itself is unverifiable. (c) AI text is labeled as AI text everywhere; the human-authored fields (P3 triad, reading reactions, unprimed hunches) are visually and structurally distinct. The system optimizes for what ends up in the researcher's head, and treats artifacts as the means.
