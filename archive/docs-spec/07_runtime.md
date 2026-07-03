# 07 — Runtime Contracts and Context Management

The implementation contracts: everything the conceptual layers (01–06) assert but a runtime must actually provide. Governing rule inherited from P1: artifacts (Markdown + frontmatter) are the only ground truth; every store and index below is derived and rebuildable.

## 1. The schema registry (M4)

One machine-readable schema per artifact type (YAML, versioned like artifacts). Per field:

```yaml
field: scope                        # per cluster, in field-map
type: enum [deep, background, out]
profile: minimal                    # minimal | full   → the minimal-run profile (04 §5)
author: human                       # ai | human | ai-drafted-human-confirmed  → P3/E7
unknown_class_hint: human-only      # computable | human-only | deferrable → seeds TRIAGE
leverage: [L2, L4]                  # links the field to question rent (05 §3)
in_summary: true                    # whether this field surfaces in the summary block
```

The registry is what makes the kernel's TRIAGE step a deterministic schema diff (E8), the minimal-run profile machine-checkable, and the constitutive triad enforceable. Two store-level guards:

1. **Write-guard.** The artifact store rejects AI writes to `author: human` fields. No exceptions, no role overrides.
2. **Human-edit preservation.** A human edit to an AI-drafted span flips the span's effective author class to `human-confirmed`. Repair (§4) may regenerate untouched AI spans freely but must emit a *proposed diff* for human-touched spans — silent overwrites of review edits would destroy the highest-bandwidth elicitation channel the system has.

## 2. Identity, versioning, and addressing (M5)

- **Stable `id` per artifact; monotonic `version`; versions are immutable.** `superseded` is a relation between versions of one id.
- **References pin at consumption time:** `depends_on: [field-map@v3]`, `elicited_from: [q-014@v1]`. Staleness is thereby decidable: *pinned < current-accepted* ⇒ stale on that edge.
- **`current` pointer per id** = latest *accepted* version; drafts are never current.
- **Stable section IDs** (`field-map#cluster-3`) registered in frontmatter: the unit of per-section status, repair, partial retrieval, parallel ownership, and trace addressing. Section IDs survive regeneration.
- **One ID space** across artifacts, ledger questions, paper cards, entities, and trace events. This single decision is what makes observability joins trivial.
- **Concurrency:** parallel AI writers own disjoint section IDs; human edits always win over queued AI writes.

## 3. The context loading contract (M1)

**Summary blocks.** Every artifact carries a 5–10-line `summary` (fields chosen by `in_summary`), regenerated only on acceptance and stored as part of the version — summary and content cannot drift. The summary is the default representation of any artifact anywhere; full text is pulled on explicit demand, and every full-pull-after-summary-read is logged (it is the signal that a summary is too thin).

**Read-sets per state.** Normative defaults; the scheduler itself runs on manifests, statuses, and summaries only.

| Consumer | Full | Summary | Never |
|---|---|---|---|
| Frame | Intuition Note, Researcher Profile | — | corpus (except Scout orientation pass) |
| Map (Cartographer) | Inquiry Frame | Confidence Checklist | downstream artifacts |
| Deepen (per-cluster worker) | Field Map, own dossier | sibling dossiers, Inquiry Frame | other clusters' paper full texts |
| Synthesize | accepted dossiers, Field Map | — | raw corpus |
| Locate | Landscape Synthesis | dossiers, Field Map | raw corpus |
| Propose | Gap Register, Synthesis, Researcher Profile | dossiers, Confidence Checklist | raw corpus |
| Decide | Candidate cards, Checklist, Profile, relevant ledger entries | everything else | — |
| Skeptic (any engagement) | artifact under attack + its cited evidence | — | the drafting rationale |

**Retrieval-boundary rule.** Each state reads the artifacts of the previous layer and never reaches past them to the raw corpus. Corpus access goes through the Scout; paper content enters later states only as paper cards by ID. Exceptions: representative-paper work and the researcher's own `human_read` reading.

## 4. The repair pipeline (M2 / S11)

1. **Mark eagerly, repair lazily.** Version/answer changes propagate `stale` flags along pinned edges immediately — pure graph traversal, no model calls. Nothing regenerates at mark time.
2. **The frontier is the trigger.** Repair runs only when the kernel selects a stale artifact as needed. Stale artifacts off the path to the current gate are never repaired; they may die stale, correctly.
3. **Tiered diff-check before regeneration.** *Tier 0 (deterministic):* does the changed input feed any section of this artifact, per schema-level dependencies? Often decisive alone. *Tier 1 (cheap model):* given old input, new input, and the section summary — does this change plausibly alter this section? *Tier 2:* regenerate only failing sections, within the read-set.
4. **Human-touched spans:** proposed diffs only (§1).
5. **Summary refresh rides acceptance** (§3).

This pipeline is what makes E5's promise — "changing your mind is cheap" — true for the machine and not only for the researcher.

## 5. The dispatch table (S13, E8)

Static, human-maintained; every LLM call carries its operation class in the event log. Illustrative:

| Operation | Class |
|---|---|
| Unknown enumeration (schema diff), staleness propagation, budget accounting, exit-criteria checks, derived-state function | **Deterministic — no model** |
| Dedup; citation statistics; co-author structure; candidate partitions (embeddings + graph communities); representative-set candidates (centrality); recency profiles | **Deterministic / classical ML** |
| Paper-card extraction; tier-1 diff-checks; summary refresh | **Cheap model tier** |
| Cluster naming and boundary notes; dossier drafting; synthesis matrix; red-teaming; question phrasing | **Frontier model tier** |
| Skeptic passes; Decide-gate audit support | **Frontier tier, fresh context** |

Getting the deterministic/LLM split wrong is the largest avoidable cost in the system (LLM-clustering 500 papers vs. embeddings-plus-naming is an order of magnitude). Tiering may start as "one model for everything" and tighten with cost data from the event log. **Learned or dynamic routing is out of scope** until multi-run cost data exists.

## 6. The retrieval policy (S12)

- **Artifact tier: graph navigation only.** ~A dozen artifacts, explicitly linked; every legitimate access is "follow an edge" or "resolve an id." **No embedding index over artifacts** — RAG here would add infrastructure, nondeterminism, and retrieval noise to a structure that is already a better index of itself. This rule exists because RAG is the reflexive implementation of "system with documents," and here it is wrong.
- **Corpus tier: hybrid search, behind the Scout.** Metadata + citation graph + embeddings over paper cards. Bounded by the retrieval-boundary rule (§3).
- **Accounting:** every retrieval logs requester, purpose, and target; whether the retrieved item was cited by the produced output is joined later (`08_observability.md`). Judged per purpose class — Skeptic reads are *supposed* to mostly find nothing.

## 7. Parallel execution (S14)

Correctness never depends on parallelism; the shard boundaries define where it is safe:

- **Deepen:** one worker per in-scope cluster, disjoint section ownership, per-cluster read-sets. The longest state in wall-clock terms; parallel drafting means the researcher's concurrent reading, not the machine, is the critical path.
- **Map:** search fan-out and cluster-card drafting parallelize; the partition computation is one deterministic job.
- **Propose:** red-team each candidate in parallel, fresh contexts.
- **Serial by design:** the ASK surface. One scheduler owns question batching and sequencing (`05_elicitation.md` §2); parallel workers enqueue candidate unknowns only. The researcher is the one single-threaded component.

## 8. Cache and cost mechanics *(guidance, not contract)*

- **Prefix ordering (O5):** contexts ordered stable → volatile: role charter + schemas, then accepted artifacts (immutable until staled — ideal cache material), then the working draft.
- **Machine budgets (O6, deferred):** per-state token/paper-count budgets mirroring depth budgets, surfacing overruns as questions ("Map has processed 800 abstracts; the cluster structure stopped changing 300 ago — proceed?"). Adopt when the cost ledger shows the need.
- **Out of scope as premature:** vector index over artifacts (§6), learned routing (§5), speculative pre-generation of next-state artifacts (collides with generation windows; negative expected savings), cross-run shared knowledge bases beyond paper cards and the entity registry, distributed execution — one researcher, one run, one machine.
