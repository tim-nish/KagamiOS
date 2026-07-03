# KagamiOS v2 — BMAD Transfer, Re-audited

v1's `bmad_comparison.md` concluded: BMAD's *mechanisms* transfer to research; its *epistemology* (uncertainty decreases monotonically) does not. The discovery scope forces a significant revision of that verdict — mostly in BMAD's favor.

## 1. The headline reversal: discovery is a planning phase

BMAD has two phases: **planning** (Analyst → PM → Architect produce successive documents, each reducing ambiguity, ending in a spec) and **execution** (sharded stories implemented and verified). v1 tried to map BMAD onto the whole research lifecycle and correctly found the execution-phase analogy broken: in research the spec is the output, experiments can increase uncertainty, and "done" doesn't exist.

But KagamiOS v2 covers only discovery — and **discovery is a planning phase**. It is exactly the process of converting ambiguity (a vague intuition) into a spec (a chosen, evidence-backed direction). The proportion holds precisely:

> **Discovery : research lifecycle :: BMAD planning : BMAD execution.**

Consequences:

- **The convergence assumption approximately returns.** Frame → Map → Deepen → Synthesize → Locate → Propose is genuinely a funnel: each accepted artifact narrows ambiguity. v1's anti-convergence machinery is still needed, but as an exception path, not the spine — the loop-backs (reading reframes the intuition) are real and first-class (P2), yet the *nominal* flow converges the way BMAD's planning flow does.
- **v1's "what must NOT transfer" list shrinks.** Of its five items, the completable-design objection (§4.2) and up-front decomposition objection (§4.3) largely dissolve — see §3 below. The done-as-verification objection survives in modified form (§4).

## 2. Mapping table, revised

| BMAD | v2 analogue | Fidelity |
|---|---|---|
| Analyst brief (elicits "what do you actually want?") | Frame → Inquiry Frame | **excellent** — the closest analogy in either design generation |
| Analyst's embedded elicitation prompts | The elicitation kernel | **the core inheritance**, generalized — see §3 |
| PM's PRD (what & why, not how) | Field Map + Landscape Synthesis | good — both are the "state of the world + what matters" document |
| Market / competitor research | Deepen + Synthesize | **better than in v1** — competitor analysis was a weak analogy for lifecycle survey but is a strong one for discovery: enumerate the players, their histories, their positions, who wins where |
| Architect's architecture doc (the spec) | Direction Decision | good — the artifact that authorizes downstream work |
| Epics → sharded stories | Field Map → Cluster Dossiers | **good — a reversal.** See §3 |
| Dev agent / QA agent | — | **no analogue, correctly** — that's the downstream KagamiOS no longer models |
| Human approval gates | Review gates + the constitutive triad | as v1, with the triad re-derived for discovery |
| Brownfield "document the existing system first" | Map + Deepen before Locate | **excellent** — a field is a brownfield codebase; you map what exists before proposing changes. The generation window (E6) is exactly the brownfield discipline: no proposals before the documentation is accepted |

## 3. What transfers — including two v1 rejections that now transfer

1. **Artifact-driven context handoff (P1).** Fully, as in v1. Unchanged.
2. **Elicitation design — the requested inheritance, generalized.** What BMAD actually does: templates contain elicitation prompts written at template-authoring time, so agents interrogate the user rather than hallucinate; its "advanced elicitation" menu offers reflective options after drafts. KagamiOS keeps the *purpose* and upgrades the *mechanism* in four ways: questions are **derived at runtime** from the diff between the draft artifact and its schema (not fixed in templates); every question passes a **rent test** with a declared target and leverage class (E2); questions are asked **against computed evidence** with defaults, menus over blanks (E3 — BMAD asks against a blank page); and answers are **first-class, revisable, staleness-participating artifacts** in a ledger (E5 — BMAD's answers vanish into the resulting document). This is the difference between a questionnaire and a kernel.
3. **Sharding — now with up-front decomposition.** v1 rejected BMAD's epic→story decomposition because research work items spawn from results and cannot be enumerated in advance. In discovery they largely **can**: once the Field Map is accepted, the shards — Cluster Dossiers — are enumerable, self-contained, and independently workable, exactly like a story backlog. The Scrum-Master-shards-the-PRD move transfers almost verbatim: the Map state shards the field.
4. **Human gates between artifacts.** As v1, with the discovery triad (scope & attention / gap meaningfulness / selection) replacing the lifecycle triad.
5. **Role-specialized agents.** Revised cast: **Interviewer** (runs the kernel — BMAD's Analyst, promoted to the central role), **Scout** (search/monitoring), **Cartographer** (clustering — no BMAD counterpart), **Historian** (dossier evolution sections), **Skeptic** (attacks framings, clusterings, gaps — kept from v1, P4). No Dev, no QA. v1's caution stands: these are modes of critique, not simulated colleagues.

## 4. What still must not transfer

1. **"Done" as verification.** BMAD's stories close when acceptance criteria pass — verification against a spec. Discovery's terminal condition is a human's *confidence*, which is subjective and unverifiable. The system can verify only the trace (papers read, checklist entries linked — E7). No mechanical criterion may auto-close the Decide gate.
2. **Throughput as objective.** Worse in discovery than in the lifecycle: optimizing artifact throughput yields fast shallow maps and confident wrong decisions. The safe metrics are time-to-*dissolution* for bad intuitions and decision robustness (`vision.md` criteria 1–2, 4) — never artifacts per week.
3. **The proposing agent.** BMAD *wants* its agents to propose (architectures, story breakdowns) as early as possible; the human corrects. Imported into discovery this is the homogenization/anchoring failure (E6): an AI proposing directions on day one contaminates the researcher's independent signal irrecoverably. Hence generation windows and ask-before-show — a discipline BMAD not only lacks but actively inverts.
4. **World-driven staleness.** Still absent from BMAD, still needed here (lighter during a run, load-bearing after Decided — the decision itself can be staled by a new paper). Software requirements change by decision; literature changes by itself.
5. **Ceremony tolerance.** As v1 §4.5, sharpened: BMAD's reader-agents don't feel friction; KagamiOS's human feels every question. P9/E2 have no BMAD counterpart because BMAD doesn't need them.

## 5. Genuinely new concepts, unique to discovery (request #7)

Mechanisms with no counterpart in BMAD *or* in KagamiOS v1:

| Concept | What it is | Why discovery specifically needs it |
|---|---|---|
| **Question rent + leverage classes** | every question declares the artifact field and downstream effect its answer changes; audited retroactively via the ledger | discovery's scarce resource is researcher attention; the lifecycle's was compute/time |
| **Evidence-grounded elicitation** | compute first, then ask as selection over shown evidence with a default | vague intuitions can't answer abstract questions; they can react to maps |
| **Question Ledger + `elicited_from` staleness** | answers as versioned artifacts; changing your mind is cheap and traceable | the elicitation trace *is* the discovery reasoning trace |
| **Researcher Profile** | incremental cross-project model of taste, skills, constraints | the terminal decision is a *fit* judgment, and fit has two sides |
| **Generation windows + ask-before-show** | AI may not draft direction-shaped content before Gaps accept; unprimed views recorded first | anti-anchoring, anti-homogenization — the integrity of the researcher's signal |
| **Confidence Checklist** | the decision's knowledge-requirements drafted at Frame; holes drive work; audited at Decide | replaces both BMAD's acceptance criteria and v1's paper skeleton for a subjective terminal condition |
| **Dissolution as terminal success** | intuitions that dissolve under mapping die in days with a memo | the cheapest good outcome discovery can produce |
| **Convergence test / depth budgets** | explicit "more reading no longer changes the candidate set" signal | discovery's characteristic failure is non-termination, which neither BMAD (bounded backlog) nor the lifecycle (bounded experiments) shares |
