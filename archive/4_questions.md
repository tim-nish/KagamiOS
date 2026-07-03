# KagamiOS v2 — Implementation and Runtime Design Review

The Discovery OS design has now completed several review iterations.

The current `docs-discovery/` design should be treated as the baseline.

The previous audit identified only three **Must Change** items:

1. Relax the restriction that Candidate Directions must originate only from the Gap Register.
2. Introduce an explicit Context Loading Contract for token efficiency.
3. Resolve the ambiguity of what a Cluster Dossier represents.

Assume these changes will be incorporated.

This review is **not** about redesigning KagamiOS.

Instead, I would like you to review the implementation-facing aspects that have not yet been fully specified.

---

# 1. Runtime I/O Specification

Please evaluate whether the current design specifies the runtime contracts precisely enough for implementation.

For every major artifact, what should be defined?

For example:

* required input
* required output
* minimal schema
* update rules
* identity (IDs)
* dependency rules
* versioning
* summary blocks
* retrieval boundaries

Which parts are already sufficiently specified?

Which parts are still ambiguous?

---

# 2. Runtime Context Management

One of BMAD's major strengths is maintaining high quality while keeping token usage low.

Beyond the Context Loading Contract already identified in the previous audit, what additional runtime mechanisms should KagamiOS define?

Consider topics such as:

* retrieval boundaries
* state-specific read sets
* artifact summaries
* cacheable intermediate representations
* lazy regeneration
* diff-based updates
* section-level regeneration
* retrieval policies
* LLM vs deterministic computation
* opportunities for parallel execution

Please distinguish between:

* essential runtime mechanisms
* useful optimizations
* premature optimizations

---

# 3. Observability and Traceability

Suppose KagamiOS has been used for 100 Discovery runs.

How should the system collect runtime traces so that the design itself can be continuously improved?

Rather than only preserving reasoning, I want KagamiOS to generate evidence about its own effectiveness.

For example:

* which questions were actually useful
* which questions almost never changed downstream artifacts
* which artifacts were rarely referenced later
* where token costs accumulated
* which retrievals were unnecessary
* where researchers overrode AI suggestions
* where researchers frequently changed previous answers
* where Discovery commonly stalled
* which candidate directions were usually selected
* which interaction patterns produced better decisions

Please propose an observability architecture for KagamiOS.

---

# 4. Design Analytics

Using those runtime traces, how should KagamiOS evaluate itself?

For example:

* identifying unnecessary artifacts
* identifying low-value questions
* detecting expensive workflow steps
* identifying opportunities to simplify the process
* improving question ordering
* improving retrieval strategies
* improving token efficiency
* improving decision quality

The goal is for KagamiOS itself to become increasingly better through accumulated Discovery runs.

---

# Important constraints

* Treat the current Discovery OS as the baseline.
* Do not redesign the overall architecture.
* Do not replace the existing state machine or artifact model.
* Focus only on implementation contracts, runtime behavior, observability, and continuous improvement.

If you recommend changes, classify each recommendation as:

* Must change
* Should consider
* Optional
* Do not change

Also specify exactly which existing document or mechanism would be affected.
