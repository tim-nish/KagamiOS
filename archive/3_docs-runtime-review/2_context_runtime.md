# Runtime Review 2 — Context Management at Runtime

**Question:** Beyond the Context Loading Contract (M1, assumed incorporated), what runtime mechanisms should KagamiOS define — retrieval boundaries, read sets, summaries, caches, lazy/diff/sectional regeneration, retrieval policies, LLM vs. deterministic computation, parallelism? Distinguish essential mechanisms, useful optimizations, and premature optimizations.

**Verdict in one paragraph.** With M1 and M2 assumed, the remaining work is not inventing mechanisms but *finishing* them: M2 names lazy/diff-first/sectional repair but not the pipeline that executes it; M1 names read-sets but not the summary lifecycle or the retrieval policy beneath them; S5 names computational-before-generative but not the dispatch table that decides. Five mechanisms are essential — the system underperforms or overspends without them from run one. Everything else is either a useful optimization (adopt when dogfooding shows the cost) or premature at this scale (a dozen artifacts, hundreds of papers, one researcher). The classification table is in §5.

---

## 1. S11 (Should consider) — the repair pipeline, specified

M2 (assumed) states the three properties: lazy, diff-first, sectional. The runtime realization:

1. **Marking is eager, repair is lazy.** A changed answer or artifact version propagates `stale` flags along pinned edges (M5) immediately — this is cheap graph traversal, no LLM. Nothing is regenerated at mark time.
2. **The frontier is the trigger.** Repair happens only when the kernel's FRONTIER step selects a stale artifact as needed (`elicitation.md` §2). Stale artifacts not on any path to the current gate are never repaired — they may die stale, correctly.
3. **Tiered diff-check before regeneration.** Tier 0, deterministic: does the changed input actually feed any section of this artifact (schema-level dependency, from M4's field metadata)? Often answerable without any model call. Tier 1, cheap model: given the old input, new input, and the section summary — "does this change plausibly alter this section?" Tier 2: regenerate only the sections that fail tier 0/1, within M1's read-set.
4. **Human-touched spans are never silently regenerated** (M4's preservation rule): repair emits a proposed diff for those spans instead.
5. **Summary refresh rides acceptance.** Summaries (M1) are regenerated when a version is *accepted*, never on intermediate edits — the summary is part of the accepted version (M5), so summary and content can never drift apart, and drafts don't burn summary calls.

**Affects:** realization of M2 (`principles.md` P7/E5), `elicitation.md` §2 (FRONTIER consumes the repair queue). **Classification: essential** — this is where E5's "changing your mind is cheap" becomes true for the system and not just the researcher.

## 2. S13 (Should consider) — the dispatch table: deterministic before LLM, and which LLM

S5's rule (never generate what is calculable) needs an operational form: a static table mapping kernel operations to execution classes. Illustrative, not exhaustive:

| Operation | Class |
|---|---|
| Unknown enumeration (schema diff, M4), staleness propagation, budget accounting, exit-criteria checks, derived-state function (S9) | **Deterministic — no model.** Note that TRIAGE's *enumeration* is deterministic; only classification of genuinely ambiguous unknowns needs a model, and M4's `unknown_class_hint` pre-answers most of those |
| Dedup, citation statistics, co-author structure, candidate cluster partitions, representative-set candidates (centrality), venue/recency profiles | **Deterministic / classical ML** (embeddings, graph algorithms) |
| Paper-card extraction (S5), tier-1 diff-checks (§1), summary refresh | **Cheap model tier** |
| Cluster naming and boundary notes, dossier drafting, synthesis matrix, red-teaming, question phrasing | **Frontier model tier** |
| Skeptic passes, Decide-gate audit support | **Frontier tier, fresh context** (role charters, S4) |

The table is *static and human-maintained* — learned or dynamic routing is premature (§5). **Classification: essential** in its deterministic/LLM split (getting this wrong is the single largest avoidable cost — LLM-clustering 500 papers versus embeddings-plus-naming is an order-of-magnitude difference); **useful** in its cheap/frontier tiering (safe to start everything on one model and tier down with cost data from M6).

## 3. S12 (Should consider) — the two-tier retrieval policy

M1 fixes *who* reads *what*; this fixes *how content is found*:

- **Artifact tier: graph navigation only.** A run has ~a dozen artifacts, explicitly linked (`depends_on`, `elicited_from`, consumption map). Every legitimate access pattern is "follow an edge" or "resolve an id" (M5). **No embedding search over artifacts** — a vector index here adds infrastructure, nondeterminism, and retrieval noise to a structure that is already a better index of itself. This is worth stating as a rule precisely because RAG is the reflexive implementation of "system with documents," and here it would be wrong.
- **Corpus tier: hybrid search, behind the Scout.** Papers (hundreds to thousands) are searched by metadata + citation graph + embeddings over paper cards (S5). M1's boundary rule stands: only the Scout touches the raw corpus; later states receive paper *cards by ID*, and full text is pulled only for representative-paper work and `human_read` reading.
- **Retrieval accounting:** every retrieval event carries *requester, purpose, and target id* (M6), and whether the retrieved item was subsequently cited by the produced artifact — this is what makes "which retrievals were unnecessary" (review 3) measurable rather than aspirational.

**Classification: essential** (the policy); the accounting rides on M6.

## 4. S14 (Should consider) — parallelism, exactly where the shards are

The baseline's shard design (dossier + Field Map fits one context) already defines the parallelism boundaries; the runtime should use them:

- **Deepen is embarrassingly parallel:** one worker per in-scope cluster, disjoint section ownership (review 1 §5), independent read-sets per M1. This is the longest state in wall-clock terms and the human's reading happens concurrently — parallel drafting means the researcher is never waiting on the machine here.
- **Map fan-out:** search queries and cluster-card drafting parallelize; the partition proposal itself is one deterministic job (§2).
- **Propose:** red-team each candidate in parallel, fresh contexts (which is also what the Skeptic's independence wants — S4).
- **What must stay serial:** the elicitation kernel's ASK step. Question batches are ranked, ≤5, at gates (`elicitation.md` §4); parallel workers emit *candidate* unknowns into the queue, but one scheduler owns batching and sequencing. Parallelizing the researcher-facing surface would recreate the interruption storm E4 exists to prevent.

**Classification: useful** — correctness never depends on it; adopt when Deepen latency annoys.

## 5. The classification the question asks for

| Mechanism | Essential / Useful / Premature | Register |
|---|---|---|
| Repair pipeline (lazy mark/trigger split, tiered diff-check, sectional regen, summary-on-accept) | **Essential** | S11 |
| Deterministic-vs-LLM dispatch split | **Essential** | S13 |
| Summary lifecycle bound to accepted versions | **Essential** | S11 (5) |
| Corpus cache / paper cards, compute-once, cite-by-ID | **Essential** (S5, carried) | S5 |
| Two-tier retrieval policy; no RAG over artifacts | **Essential** | S12 |
| Static model tiering (cheap tier for extraction/diff-checks) | Useful | S13 |
| Parallel shard execution (Deepen, red-teams, Map fan-out) | Useful | S14 |
| Prompt-cache prefix ordering (stable → volatile: charters + schemas, accepted artifacts, working draft) | Useful | O5 |
| Machine token budgets + live meters per state | Useful | O6 |
| Batched embedding computation | Useful (trivial) | — |
| Vector index / RAG over the artifact graph | **Premature — and wrong at this scale** (see §3) | D-level rejection |
| Learned / dynamic model routing | Premature — needs M6 cost data that doesn't exist yet | — |
| Speculative pre-generation of next-state artifacts | Premature — and it collides with generation windows (E6): pre-drafting direction-adjacent content before its window opens is exactly the quarantine case; the token savings are negative | — |
| Cross-run shared knowledge base beyond paper cards / entity registry | Premature (DQ8's per-run lean stands) | — |
| Distributed execution / autoscaling infrastructure | Premature — one researcher, one run, one machine | — |

## 6. What is already right *(Do not change)*

- **The shard boundary** (dossier + Field Map per context) — S14 exploits it; nothing changes it.
- **The kernel loop as the sole scheduler** — parallel workers feed it; nothing bypasses it. The one refinement worth adopting is S10 (review 1/3): fix the FRONTIER priority order (gate-blocking items → stale repairs on the gate path → checklist holes → deferred) and *log each frontier decision with its reason* — not to constrain the design but because an unlogged scheduler is the one component whose behavior can't be audited afterward, and review 3 needs it.
- **E4's batching discipline** as the runtime's concurrency limit on the human surface (§4). The researcher is the one single-threaded component; the design already knows this.
