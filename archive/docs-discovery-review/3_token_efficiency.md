# Review 3 — Token-Cost Efficiency

**Question:** BMAD achieves high quality at low token cost. How can KagamiOS preserve or improve discovery quality while minimizing token consumption — considering sharding, artifact summaries, cacheable intermediate artifacts, retrieval boundaries, citation-backed compressed representations, and avoiding unnecessary LLM calls?

**Verdict in one paragraph.** The baseline optimizes the scarce resource it names — researcher attention — with real rigor (E2–E4, the triage, the rent audit), and is almost silent on the resource this question names: tokens. That silence matters because discovery is intrinsically the most token-hungry phase of research (mapping a field means processing hundreds of documents), and because BMAD's frugality — which the founding `2_questions.md` explicitly admired — comes from a context discipline the baseline has not yet written down. The skeleton is already right: dossiers are shards, the triage avoids the worst waste, artifacts are the handoff medium. What's missing is the **loading contract** (who reads what, at what resolution) and a **repair discipline** for the staleness cascade, both of which are must-fixes because without them a literal implementation quietly fails the design's own inheritance claims. Three further additions are strong should-considers.

---

## 1. Where the token cost actually is

Ranked by expected spend in a real run:

1. **Corpus processing** (Map/Deepen): reading and re-reading hundreds of abstracts and dozens of papers. Dominant cost by an order of magnitude.
2. **Staleness cascades**: E5 invites the researcher to revise answers cheaply; every revision can stale the Field Map and everything downstream. If stale means regenerate, one changed L2 answer costs a re-run of half the pipeline.
3. **Context reloading**: each kernel iteration re-reading the artifact graph.
4. Question generation, drafting, red-teaming: comparatively cheap; not worth optimizing.

The recommendations below address these in order.

## 2. M1 (Must change) — the context-loading contract

**Gap.** `artifacts.md` §4 says who consumes which artifact but not *at what resolution* or *what else they carry*. BMAD's efficiency comes precisely from the rule the baseline never states: the dev agent loads one story, not the PRD. The baseline even sizes the dossier as "one dossier plus the Field Map fits an agent's working context" — the shard exists, but no rule prevents the Synthesize step from loading five full dossiers, or the kernel loop from re-reading the whole graph every iteration. Absent the rule, the default implementation loads everything, and the design silently loses the inheritance it was built on.

**Fix.** Three additions, all to existing documents:

1. **A mandatory `summary` block** (5–10 lines, maintained on every accepted revision) in the common artifact metadata (`artifacts.md` §1). The summary is the *default* representation of an artifact everywhere; full text is pulled on explicit demand.
2. **A read-set column** in the consumption map (`artifacts.md` §4) and the state table (`state_machine.md` §3): e.g. Deepen reads *Field Map (full) + one dossier (full) + other dossiers (summary)*; Synthesize reads *dossiers (structured sections, not raw papers)*; Propose reads *Gap Register (full) + Synthesis (full) + dossiers (summary) + Profile (full)*.
3. **A retrieval-boundary rule:** each state reads the artifacts of the previous layer and never reaches past them to the raw corpus — corpus access goes through the Scout, and paper content enters later states only as citations into the corpus cache (S5). This makes the dossier a true boundary, which is what "shard" means.

**Affects:** `artifacts.md` §1 §4, `state_machine.md` §3, `bmad_transfer.md` §3.3. Quality note: this is not a quality/cost trade — bounded contexts *improve* output (less distraction, less cross-cluster leakage in dossiers), which is the other half of why BMAD shards.

## 3. M2 (Must change) — staleness is not regeneration

**Gap — an internal inconsistency.** E5's promise ("changing your mind is cheap and safe — dependents will be flagged") is what makes fast, low-anxiety answering rational, and the whole elicitation kernel leans on it. But the baseline defines staleness propagation (P7, `elicited_from`) without defining *repair*. If flagged-stale means regenerate-on-next-touch, the promise is true for the researcher and false for the system: every revised answer triggers a cascade of LLM re-drafts. An implementer will notice, and the likely workaround — propagating staleness less eagerly — breaks P7 instead. The design needs the third option stated.

**Fix.** Add a repair discipline to P7/E5 (one paragraph each in `principles.md`, `elicitation.md` §5, `artifacts.md` §1):

- **Lazy:** stale artifacts are repaired only when next needed (frontier selection already provides the trigger), never eagerly.
- **Diff-first:** repair begins with a cheap check — *does the changed answer actually alter this artifact?* A revised q-014 ("cluster 3 background → in scope") changes the Field Map's scope field and the budgets, but most dossier content survives verbatim. The check is a small classification call, not a re-draft.
- **Sectional:** artifacts repair at section granularity (the dossier's Evolution section rarely depends on any elicited answer; its representative set might).

This also protects the researcher-facing property: if revising an answer visibly causes minutes of expensive churn, the researcher learns not to revise — quietly destroying E5's behavioral goal. Cost discipline and psychology point the same way.

## 4. S5 (Should consider) — the corpus cache and computational-before-generative

**Gap.** Papers are the unit the system touches most and the only heavily-reused object with no cached representation: `artifacts.md` gives representative papers a contribution line *inside* dossiers, but nothing stops the system from re-summarizing the same paper in the Map pass, the dossier draft, the synthesis matrix, and a candidate card.

**Fix, two parts:**

1. **Paper cards.** A per-paper structured card (bibliographic identity, one-line contribution, method class, evidence type, key claims with section citations) computed **once** on first contact, stored beneath the artifact graph, and thereafter *cited by ID*. Every artifact that mentions a paper carries the ID, not a fresh summary. This is the "citation-backed compressed representation" of the question, and it doubles as the substrate for the entity registry (S7, review 5) and post-Decided monitoring. Cross-run reuse is free: the next intuition touching the same field starts with a warm cache.
2. **Computational-before-generative.** E3 already says *compute first, then ask* — extend the same principle one level down: *compute cheaply first, generate expensively second.* Clustering 500 papers by LLM judgment is enormous; embeddings + citation-graph community detection + co-author structure produce candidate partitions nearly free, with the LLM reserved for what it is uniquely good at — naming clusters, writing boundary notes, flagging where the graph structure and the semantic structure disagree. Same pattern elsewhere: dedup, venue/recency statistics, and representative-set candidates (citation centrality) are classical computations; only their interpretation is generative.

**Affects:** `artifacts.md` (a new infrastructure entry beside the Question Ledger), Cartographer/Scout charters (S4), `bmad_transfer.md` §3. Note the symmetry this creates: the elicitation kernel's triage (never *ask* what is computable) gets a compute-side twin (never *generate* what is calculable). It could even be recorded as a principle E8, though the review does not insist on that.

## 5. O2 (Optional) — cache-aware mechanics and machine-side budgets

- **Prompt-cache-aware prefixes.** Accepted artifacts are immutable until staled — ideal cache material. Order contexts as *stable → volatile*: role charter + schemas, then accepted artifacts, then the working draft. Pure implementation guidance; worth one line in the docs so it isn't lost.
- **Machine-side budgets.** Depth budgets (`state_machine.md` §5) bound *human* reading; a parallel per-state token/paper-count budget would bound machine reading, with overruns surfaced exactly like budget-exhaustion questions ("Map has processed 800 abstracts; the cluster structure stopped changing 300 ago — proceed?"). This doubles as a convergence signal for DQ4. Optional because depth budgets already bound the dominant costs indirectly.

## 6. What is already right *(Do not change — D4)*

- **Dossier-as-shard** (`artifacts.md`, `bmad_transfer.md` §3.3) — the correct decomposition; M1 completes it rather than changing it.
- **The computable/human-only/deferrable triage** (`elicitation.md` §1) — besides protecting attention, it is already the design's biggest token saver: every question *not* asked is a round-trip and a context reload avoided; every deferrable default applied silently is a whole interaction elided.
- **Artifacts as the handoff medium (P1)** — conversation-as-exhaust is the cheap architecture as well as the traceable one.
- **The Question Ledger** — an append-only log of one-line entries; negligible cost, high value. No change.
