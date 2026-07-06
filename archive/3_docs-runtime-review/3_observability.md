# Runtime Review 3 — Observability and Traceability

**Question:** After 100 Discovery runs, how should the system have collected runtime traces so the design itself can be improved? Propose an observability architecture that generates evidence about the design's own effectiveness, not just a record of reasoning.

**Verdict in one paragraph.** The baseline already *promises* measurements it has no mechanism to make: success criterion 5 audits question rent via the ledger; DQ2 proposes rent proxies (answer-differs-from-default rate, revision cascades); DQ4 says to "log every extend-or-proceed answer and, post-hoc, whether extensions ever changed the candidate set"; E6 requires diffing the unprimed lean against the final choice. Each of these presupposes telemetry the design never specifies collecting. That is why the run event log is a **must (M6)** and the analytics on top of it are not: analytics can be written next year over data collected this year, but data not collected during run 1 is gone. The architecture below is three layers — events, per-run derivations, cross-run corpus — with one governing principle inherited from P1: **traces are exhaust, never load-bearing.**

---

## 1. The governing principle *(Do not change — D8)*

P1 says artifacts are the state and conversation is exhaust. The trace extends the same rule: **artifacts remain the only load-bearing state; the event log is write-only during a run.** No runtime behavior may depend on reading telemetry — a run with a deleted trace must behave identically. This keeps runs auditable (the trace explains behavior rather than causing it), keeps the trace deletable (which §5's privacy stance needs), and blocks a whole class of feedback pathologies before they exist.

One narrow, sanctioned exception, because the baseline itself asks for it: `state_machine.md` §4 makes review gates "loosenable with trust." Trust must be grounded in something — the honest ground is aggregated per-researcher statistics (override rates, revision rates). So: gate-loosening may read *derived per-researcher aggregates* (layer 2), never raw events, and only as a proposal the researcher approves ("your Field Map edits have been near-zero for three runs — collapse this gate to notification?"). The exception is human-gated, which keeps it inside the design's philosophy.

## 2. M6 (Must change) — Layer 1: the run event log

**Why necessary** — stated above; concretely, four baseline mechanisms (`vision.md` criterion 5, DQ2, DQ4, E6's led-or-followed diff) are unmeasurable without it, and `4_questions.md`'s entire question 4 is downstream of it. **Affects:** new infrastructure entry in `artifacts.md` beside the Question Ledger. **Implementation impact:** low-moderate — an append-only JSONL stream per run, emitted by thin wrappers around the LLM client, the retrieval layer, the artifact store, and the question surface. **Conceptual or implementation-only:** implementation-only; it collects what the design already promises to measure.

**The event vocabulary** (every event: timestamp, run id, and M5-space ids — one ID space is what makes joins trivial later):

| Event family | Payload | Downstream evidence (question 3's list) |
|---|---|---|
| `llm_call` | role, purpose tag, operation class (S13), target `id@version#section`, model tier, tokens in/out, cache hit/miss | where token costs accumulate; tiering decisions |
| `retrieval` | requester, purpose, target id, tier (artifact/corpus), **later joined: cited-by-output?** | which retrievals were unnecessary |
| `artifact_event` | draft / review / accept / stale-mark / repair (with diff-check tier & outcome) / supersede | rarely-referenced artifacts; repair-vs-regen ratios |
| `question_event` | asked / answered / default-applied / skipped / revised; card fields; **answer-differs-from-default?** | which questions were useful; DQ2's proxies, both of them |
| `human_edit` | target section, span author-class flip (M4), size of edit | where researchers override AI suggestions — measured as *edits against AI drafts*, which field-level provenance makes precise |
| `frontier_decision` | chosen artifact, reason class (gate-blocking / stale-repair / checklist-hole / deferred) (S10) | where Discovery stalls; scheduler auditability |
| `gate_event` | gate, outcome, questions batched, checklist fill state | stall attribution; checklist trajectory |
| `budget_event` | budget, counter, extend-or-proceed answer | DQ4's log, verbatim |
| `state_transition` | per-cluster derived state change (S9), incl. loop-backs with annotation | loop-back frequency by cause |
| `terminal_event` | Decided / Dissolved / Dormant; for Decided: chosen candidate id, origin (ai/human-added; gap/synthesis-rooted), unprimed-lean match | which candidates get selected; E6's led-or-followed, now a field |

**Stall detection (O7, Optional):** stalls are *absences*, so they are computed, not emitted — wall-clock gaps joined against what was pending (`gate_event` / `question_event` open items). Surfacing them ("this run has been blocked on q-014 for 6 days") is a UI nicety; *recording* enough to compute them is already covered above.

## 3. Layer 2 — per-run derived metrics *(part of M6's contract, computed not collected)*

Deterministic jobs over the event log, run at gates and at terminal, written next to the run:

- **Question economics:** per question — differs-from-default, `consumed_by` count, revision count, staleness cascade size when revised (DQ2's two proxies), leverage class, state. Success criterion 5's rent audit becomes a query.
- **Token ledger:** spend by state × role × operation class × artifact; repair-vs-full-regen ratio; summary sufficiency (rate of full-text pulls following summary reads — high rate means summaries are too thin, feeding M1 tuning).
- **Override profile:** human-edit volume per artifact type and role (a heavily edited Cartographer output and an untouched Historian output *mean something* — layer 3 finds out what).
- **Trajectory:** time-in-state (wall-clock vs. active), loop-back counts by cause, checklist fill curve, stall episodes with attribution.
- **Decision block:** candidate origins, lean-vs-choice diff, provisional-count at Decide (how much of the decision rests on unconfirmed defaults — arguably the single best cheap proxy for decision fragility), DQ9's pre-registered falsifiable claims carried as first-class trace objects so later falsification events can join back.

## 4. Layer 3 — the cross-run corpus (the "100 runs" view)

Run summaries (layer 2 outputs + run metadata: entry mode, field, terminal state, duration) accumulate in a small local analytics store — derived and rebuildable from run traces (D7's rule applies here too: no new ground truth). Two schema decisions matter now, because retrofitting them is what's expensive:

1. **A stable question-class taxonomy.** Cross-run learning about questions requires identifying "the same question" across runs. Leverage class × state × form (from the card schema) is a serviceable class key and already exists in the ledger schema — record it per question from run 1.
2. **Outcome joins arrive late.** The strongest quality signals — DQ9 falsifications, post-Decided staleness alerts, voluntary reuse (criterion 7), dormant revivals — occur months after the run. The corpus must support late-arriving outcome events joined to old runs by run id. Trivial if planned, painful if not.

What layer 3 is *for* is review 4's subject; what it must *be* is: local, derived, and joinable.

## 5. S16 (Should consider) — trace privacy

A discovery trace is a researcher's unpublished research direction, their taste profile, their unprimed hunches, and the gaps they consider theirs — competitively sensitive IP of exactly the kind researchers guard before publication. Consequences, all cheap if adopted early: traces are **local-first** and owned by the researcher; the trace is deletable without breaking the run (guaranteed by D8's write-only rule); cross-run aggregation (layer 3) is per-researcher by default; any *shared* aggregation (multi-user lab deployments, future) is opt-in and **content-stripped** — event shapes, counts, and classes travel; question text, artifact content, and paper identities do not. This also pre-answers the population-level anchoring hazard raised in review 4 §3: content that never leaves the researcher's machine cannot homogenize anyone else's defaults. **Affects:** M6's storage contract; one paragraph of policy.

## 6. What not to build *(Do not change / rejected)*

- **No telemetry inside artifacts.** Artifacts stay clean reasoning documents (P1); all instrumentation lives in the event stream, joined by ID. The one apparent exception — `human_read` flags, `elicited_from` — is not telemetry: those are reasoning-bearing fields the design already owns.
- **No dashboards-first.** The consumer of this architecture is the design process (review 4), not a live ops screen. O7's stall surface is the only runtime-facing view worth having early.
- **No third-party analytics dependency as ground truth.** Everything above is files: JSONL events, computed summaries. Tooling on top is free to vary; the data contract is not.
