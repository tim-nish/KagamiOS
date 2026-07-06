# Future Scout Redesign — Design Notebook

> **Status: NOT for implementation.** This is a design notebook, not a plan. It
> preserves the graph-exploration architecture for Scout that was worked out on
> 2026-07-04, so a future session can resume the design after dogfooding evidence has
> accumulated. The deliberate decision (recorded in
> `_bmad-output/planning-artifacts/change-signal-scout-probes-2026-07-04.md`) was to
> ship four minimal probes instead of this redesign, run 2–3 real investigations, and
> let the evidence decide which — if any — of these components get built.
>
> If you are a future session reading this: **check the adjudication section first.**
> Some components in here should probably never be built. That's a success condition,
> not a failure.

## Context as of 2026-07-04

- Epics 1–7 implemented; deterministic core + driver + minimal shell complete; first
  live dogfooding run done. That run exposed Scout's exploration weaknesses (bulk
  keyword retrieval: vocabulary anchoring, no stopping signal, no way to grow from
  good finds), which triggered this design work.
- Full conceptual groundwork lives in two companion documents — read them before this
  one, this notebook does not repeat their arguments:
  - `docs/exploration-strategy.md` — why literature exploration is active search on a
    partially observed graph, not keyword retrieval; why MCTS is the wrong family;
    the frameworks that fit (active search on graphs, budgeted bandits, information
    foraging, submodular coverage); the two-scenario (token-constrained vs
    quality-only) analysis.
  - `docs/scout-conceptual-architecture.md` — the six-component architecture, the
    semi-autonomy model, the five-layer belief state, and six additional design
    principles. This notebook is the index and resumption protocol for that design.
- Four probes were specced (Epic 8) as instrumented down payments: a `corpus expand`
  graph sensor whose retrieval events carry explicit edge lists; frame-stamped
  appraisal records separate from paper cards; an iterative/anchor charter discipline;
  and a rediscovery-rate metric.

## The architecture in one screen (details in the companion doc)

**Foundation principle:** separate inference from decision. Frame-independent facts
(graph, cards) and frame-dependent valuations have different lifetimes; frame revision
re-scores, never re-explores. The probes already honor this in data (cards vs
appraisals); the full design honors it in components.

Six components in an anytime loop, communicating through a shared belief:

| Component | Role | Builds on (from the probes) |
|---|---|---|
| Landscape Model | Belief store: known subgraph + calibrated beliefs about the unexplored | Derived state over retrieval events (edges already in the log) |
| Sensor Suite | query / expand / shallow-read / deep-read, each with declared cost + bias | `corpus search` + `corpus expand` are sensors 1 and 2 |
| Appraiser | The frame's value function; volatile, frame-version-stamped scores | Appraisal records are its output format, hand-produced today |
| Frontier | Explicit ranked list of candidate next actions — Scout's inspectable to-do list | New; a pure reader of Landscape Model + Appraiser |
| Allocator | UCB over the frontier, marginal-value patch-leaving, ring-fenced diversity reserve; sole budget spender | New; replaces charter-prose iteration discipline with policy |
| Governor | Event-driven checkpoint policy (EVOI test: interrupt iff the answer would change the allocation), tripwires, batched agenda | New; cadence evidence comes from probe transcripts |

Belief state in five layers: (1) observed graph with per-node processing depth;
(2) relevance *posteriors* (distributions — UCB needs the spread); (3) beliefs about
the unobserved: bias-corrected density, Good–Turing saturation, and the terra
incognita registry of priced known-unknowns; (4) meta-beliefs: sensor bias estimates,
branch gain-rates, Appraiser calibration against human verdicts; (5) tripwires — the
frame's assumptions as live falsifiable predictions.

Key commitments worth re-affirming at resumption time:
- The event log (Chronicle) stays the single source of truth; the belief is *derived*
  and replayable. No belief database that can drift from the log.
- Checkpoint outcomes are training data (preference learning for the Appraiser), not
  just gates. The system should need less steering every session.
- The belief must be renderable — the map artifact is the medium of supervision.
- Human approves *policies with envelopes* (standing orders), never individual
  actions. Reversibility is manufactured by the architecture (chronicle + cheap
  re-scoring), and every decision made reversible is one the human needn't gate.
- FR-25 survives intact: all sensors live behind Scout's chokepoint; other roles still
  see only processed artifacts. The architecture lives *inside* Scout's boundary.

Additional principles recorded in the companion doc (§4): Bayesian surprise per token
as the universal currency; gaps as *earned* negative claims (confidence = hostile
search survived); red-teaming the belief itself, not just artifacts; MDL/compression
as map-quality criterion; the citation time axis (recency under-signaling, sleeping
beauties, cluster velocity); holding multiple competing maps to resist premature
crystallization.

## Adjudication: what dogfooding evidence funds what

This is the contract with the probes. Build a component only when its failure mode has
been observed, not because this notebook exists.

| Observed in dogfooding runs | Component it funds | How to check (from probe data) |
|---|---|---|
| Corpus clusters reachable only from one seed's citation basin; whole communities missing that a semantic jump later finds | Diversity reserve in the Allocator | Reconstruct the graph from `corpus_expand` events; look for single-articulation-point clusters and post-hoc discovered deserts |
| "When do we stop?" repeatedly decided by fatigue or budget, not evidence; or stopped too early and a later search found a missed region | Saturation machinery (Layer 3) + Governor stop-trigger | Did the rediscovery-rate metric plateau where stopping happened / should have happened? |
| Frame revised mid-run and re-judging felt expensive or was skipped, letting a stale frame persist | Full belief-store split + Appraiser | Count frame versions per run; compare appraisal re-issue cost vs re-exploration cost from the log |
| Branch choices contested — human kept overriding which direction got effort | Frontier + UCB Allocator | Probe-3 transcripts: how often did the human redirect vs bless? |
| Checkpoints felt too chatty or too silent; interrupts asked things whose answer changed nothing | Governor (EVOI policy, tripwires, agenda) | Transcript review: for each checkpoint, would any plausible answer have changed the next action? |
| Expansion kept rediscovering hubs; recent/low-citation work systematically missing | Time-axis appraisal treatment; sensor-bias meta-beliefs (Layer 4) | Age/citation-count distribution of cards vs what deep reads found valuable |
| None of the above after 2–3 real runs | **Nothing. Close this notebook.** | The probes were sufficient; the redesign is dissolved, cheaply. |

## Open questions left unresolved (on purpose)

1. **Where does the Appraiser's value function live?** Charter prose scored by the
   model in-context vs an explicit scored rubric artifact. Affects auditability and
   FR-29 charter-audit interaction. No evidence yet.
2. **Envelope representation.** Standing orders need a concrete form (per-branch token
   budgets? paper-count caps? scope predicates?) and a place in the gate/trust
   machinery. Should reuse the FR-37 budget-checkpoint pattern if built.
3. **Semantic-similarity edges.** The diversity reserve needs jumps that citation
   edges can't provide, which implies embeddings — the first genuinely new
   infrastructure (everything else derives from the log). Defer hardest; check first
   whether provider-side related-paper endpoints (the AD-7 port could grow one method)
   are enough before owning an embedding store.
4. **Multiple competing maps.** FR-26 already forces plural clusterings at
   Cartographer; extending pluralism back into exploration (probing where rival maps
   disagree) needs a cheap representation of "a map hypothesis" first. No design yet.
5. **Governor vs Interviewer boundary.** The Interviewer (AD-4 skill) already owns
   the human conversation; a Governor must not become a second mouth. Likely shape:
   Governor emits typed escalation events, Interviewer voices them. Decide only after
   probe-3 transcripts show what escalations actually look like.

## Resumption protocol for a future session

1. Read the two companion docs, then this notebook's adjudication table.
2. Pull the evidence: reconstruct graphs from `corpus_expand` events, plot
   rediscovery-rate trajectories, count frame versions and appraisal re-issues, review
   checkpoint transcripts against the EVOI test.
3. Fund only the components whose row in the table fired. Write a change signal in the
   established format (`_bmad-output/planning-artifacts/change-signal-*.md`) scoped to
   exactly those components — amend the spine, never renumber, and keep FR-25's
   chokepoint untouched.
4. Whatever gets built: belief as derived state over the log, valuations
   frame-stamped, and renderable at every step. Those three are the non-negotiables;
   everything else in this notebook is hypothesis.
