# 08 — Observability and Design Analytics

The system generates evidence about its own effectiveness, not just a record of reasoning. Three layers — events, per-run derivations, cross-run corpus — under three governance rules. The rules come first because everything else is downstream of them.

## 1. Governance rules

**G1 — Traces are exhaust (P1 extended).** Artifacts are the only load-bearing state; the event log is **write-only during a run**. No runtime behavior may depend on reading telemetry: a run with a deleted trace behaves identically. This keeps traces explanatory rather than causal, deletable (→ §4 privacy), and blocks feedback pathologies by construction. *One sanctioned, human-gated exception:* review gates are loosenable with trust (`03_state_machine.md` §4); the loosening proposal may read *derived per-researcher aggregates* (layer 2) — never raw events — and takes effect only on the researcher's approval. The constitutive triad never loosens.

**G2 — Self-measuring, never self-modifying.** Analytics produce reports; humans change the design. No threshold auto-reclassifies a question, auto-loosens a gate, auto-edits a schema, or auto-tunes a prompt. (BMAD's lesson inverted: throughput-like metrics must never become objectives.)

**G3 — Form, not content (E6 at population scale).** Aggregate data may tune the process's **form**: when a question class is asked, how cards are batched, what contexts load, which fields are minimal-profile, what is computed deterministically. Aggregate data may never tune **content**: which clusters to include, which gaps matter, which candidates to favor, or the default answer to any taste question. Content defaults come from *this* run's evidence and *this* researcher's profile only. Without this rule, the improvement loop homogenizes its researchers — anchoring implemented as evidence-driven refinement. §4's content-stripped aggregation enforces G3 physically.

## 2. Layer 1 — the run event log (M6)

Append-only JSONL per run, emitted by thin wrappers around the LLM client, retrieval layer, artifact store, and question surface. Every event carries timestamp, run id, and M5-space ids (one ID space makes every join below trivial).

| Event family | Payload | Evidence it enables |
|---|---|---|
| `llm_call` | role, purpose tag, operation class (`07` §5), target `id@version#section`, model tier, tokens in/out, cache hit | where token costs accumulate; tiering decisions |
| `retrieval` | requester, purpose, target, tier; later joined: cited-by-output? | unnecessary retrievals, per purpose class |
| `artifact_event` | draft / review / accept / stale-mark / repair (diff-check tier + outcome) / supersede | rarely-referenced artifacts; repair-vs-regen ratios |
| `question_event` | asked / answered / default-applied / skipped / revised; card fields; differs-from-default? | question usefulness; the rent audit's raw data |
| `human_edit` | target section, provenance flip, edit size | where researchers override AI output — precise, via field provenance |
| `frontier_decision` | chosen artifact, reason class (S10) | scheduler auditability; stall attribution |
| `gate_event` | gate, outcome, batched questions, checklist fill state | checklist trajectory; stall attribution |
| `budget_event` | budget, counter, extend-or-proceed answer | the stopping-rule dataset (`03` §6) |
| `state_transition` | per-cluster state change, loop-backs with cause | loop-back frequency by cause |
| `terminal_event` | Decided/Dissolved/Dormant; candidate origin (ai/human; gap/synthesis-rooted); unprimed-lean match | selection patterns; E6's led-or-followed, as a field |

Stalls are absences, computed not emitted: wall-clock gaps joined against pending items. Surfacing them live ("blocked on q-014 for 6 days") is optional (O7).

## 3. Layer 2 — per-run derived metrics

Deterministic jobs at gates and at terminal, written beside the run:

- **Question economics:** per question — differs-from-default; `consumed_by` count; revision count; staleness-cascade size when revised; leverage class; state. Success criterion 5's rent audit becomes a query.
- **Token ledger:** spend by state × role × operation class × artifact; repair-vs-regen ratio; **summary sufficiency** (full-pull-after-summary-read rate — high means summaries too thin).
- **Override profile:** human-edit volume per artifact type and role.
- **Trajectory:** time-in-state (wall-clock vs. active); loop-backs by cause; checklist fill curve; stall episodes with attribution.
- **Decision block:** candidate origins; lean-vs-choice diff; **provisional-count at Decide** (how much of the decision rests on unconfirmed defaults — the best cheap proxy for decision fragility); the pre-registered falsifiable claims (`04_artifacts.md`, Direction Decision) carried as trace objects so later falsification events join back.

## 4. Layer 3 — the cross-run corpus, and privacy (S16)

Run summaries (layer-2 outputs + metadata: entry mode, field, terminal state, duration) accumulate in a small local analytics store — derived, rebuildable, never ground truth. Two schema commitments made from run 1 because they cannot be retrofitted: a **stable question-class key** (leverage × state × form, already in the ledger schema) so "the same question" is identifiable across runs; and **late-arriving outcome joins** — DQ9 falsifications, post-Decided staleness alerts, dormant revivals, voluntary reuse — attached to old runs by run id, months later.

**Privacy.** A discovery trace is unpublished research direction, taste, and unprimed hunches — competitively sensitive IP. Therefore: traces are **local-first and researcher-owned**; deletable without breaking anything (G1 guarantees it); layer-3 aggregation is per-researcher by default; any shared aggregation (lab deployments) is **opt-in and content-stripped** — event shapes, counts, and classes travel; question text, artifact content, and paper identities do not. Content-stripping is also what makes G3 physically enforceable.

## 5. The Design Audit Report loop (S15)

Every N runs (or quarterly): deterministic jobs over layer 3 → a **Design Audit Report** — itself an artifact with standard frontmatter, claims citing trace evidence the way dossiers cite papers → read by the design owner → accepted findings become reviewed changes to this spec (schema edits, triage-hint moves, read-set adjustments, profile changes) → each adopted change records its motivating finding, so the next report checks whether it had the predicted effect. The design process eats its own traceability discipline.

The core jobs, each with the confound that keeps it honest:

| Target | Signal | Acts on | Guard / confound |
|---|---|---|---|
| Unnecessary artifacts | low downstream reads ∧ low citation from Decisions, across runs | demote fields/artifacts to `full` profile | humans read on paper — check E7-adjacent evidence before demoting |
| Low-value questions | high default-acceptance **∧** zero downstream divergence | reclassify `unknown_class_hint` human-only → deferrable; the inverse migration too (defaults researchers keep revising later were questions in disguise) | acceptance alone also means *good defaults* (E3 working); only the conjunction demotes. **Permanently exempt:** E6 unprimed questions, the P3 triad |
| Expensive steps | token ledger; DQ4 join — *did Deepen extensions ever change the candidate set?* | dispatch table, read-sets, budget defaults | value, not just cost |
| Simplification | optional-field fill rates vs. outcomes; pass-through states per entry mode | minimal-run profile per entry mode | n≈100 heterogeneous runs is weak; propose, dogfood |
| Question ordering | classes asked early but systematically revised post-Deepen; loop-backs preceded by late L1/L2 answers | the "typical state" column (`05` §3) | confounded with intuition quality; require cross-run pattern |
| Retrieval strategy | retrieved-but-uncited per purpose; summary sufficiency | read-sets; `in_summary` flags | Skeptic reads are supposed to find nothing |
| Token efficiency | cache hits, tier mix, repair-stage yields | prefix ordering, tiering | §6's pairing rule, always |
| **Decision quality** | pre-registered claim falsifications; post-Decided staleness; dissolution speed; voluntary reuse; provisional-count as leading proxy | nothing directly — this row **vetoes** the others | see §6 |

## 6. Anti-Goodhart pairing

Every efficiency finding ships with its quality guard, and both appear in the report: fewer questions is good *only if* override and late-revision rates don't rise; cheaper Deepen is good *only if* provisional-counts and post-decision staleness don't rise; faster time-to-Decided is good *only if* falsifications don't rise. A finding whose guard moved the wrong way is reported as a **regression, not a saving**. The quality metrics themselves are never optimization targets — they are few, slow, and n-small; their statistical job is to *veto* efficiency changes, which is the one job n≈100-with-lag can actually perform.

## 7. What accumulates across runs — the sanctioned list

| Accumulates | Status |
|---|---|
| Researcher Profile (per researcher; annotate-never-filter) | sanctioned — baseline |
| Corpus cache (paper cards); entity registry | sanctioned — factual, researcher-local |
| Question-class statistics; retrieval yields; cost ledgers | sanctioned — form (G3), feeds §5 |
| Design Audit Reports + adopted changes | sanctioned — the loop itself, human-gated |
| Content defaults tuned from other researchers' choices | **rejected** (G3) |
| Auto-modified prompts, gates, schemas | **rejected** (G2) |
| Controlled question-form experiments (O8) | deferred — meaningful only at real scale |
