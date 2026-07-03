# Input Reconciliation — ARCHITECTURE-SPINE.md vs PRD + docs-spec

Pass: input-reconciliation (finalize). Date: 2026-07-02.
Spine: `ARCHITECTURE-SPINE.md` (this directory).
Inputs: `_bmad-output/planning-artifacts/prds/prd-KagamiOS-2026-07-02/prd.md` + `addendum.md`; `docs-spec/` (03, 04, 05, 07, 08 checked in full for the sections cited below).

Not flagged (working as intended): Propose/Decide flow deferral (AD-14 + Deferred), cross-run analytics/Design Audit deferral (FR-38/40/41), O2/O5/O6/O7/O8 deferrals, provider failover deferral, schema-field-list transcription deferral, hook-detail deferral, artifact-tier graph-only Standing Refusal, and both negotiated Platform-NFR conditions — the spine explicitly carries "illegal state mutation remains mechanically impossible and every deviation is auditable" (AD-11) and "deterministic core must remain standalone-capable" (AD-5). The PRD's Platform NFR landed essentially intact.

---

## 1. Contradictions (spine vs docs-spec)

**C1 — Corpus-tier embeddings: spine defers what the spec specifies as the retrieval policy.**
Spine Deferred #1 treats a "local embedding index over paper cards" as an optional optimization ("revisit when… demonstrably misses relevant clusters"). But `docs-spec/07_runtime.md` §6 defines the corpus tier as *hybrid* — "metadata + citation graph + **embeddings over paper cards**" — and §5's dispatch table plus `05_elicitation.md` §7 specify Map's candidate partitions as "**embeddings + graph communities**" (deterministic/classical-ML tier). Without embeddings, the Cartographer's two-cut requirement (FR-26) rests on citation-graph communities and provider-side relevance alone — a different mechanism than the spec's. This is a spec deviation dressed as a deferral; if intentional, it should be recorded as a deviation from 07 §5/§6 with the FR-26 consequence acknowledged, not as a plain deferral.

**C2 — AD-12 frames dispatch as per-role model assignment; the spec dispatches per operation class.**
`07_runtime.md` §5: the dispatch table maps *operation → tier* across four tiers (deterministic / deterministic-ML / cheap model / frontier), and one role spans tiers (Scout does cheap-tier paper-card extraction and deterministic dedup). Spine AD-12 flattens this to "per-role model assignment (cheap tier vs. frontier tier)". Per-role defaults can coexist with per-operation dispatch, but as written AD-12 replaces the spec's keying, and Non-Goal #8 / addendum A2 ("static, human-maintained mapping of operation → tier… auditable against actual usage") has no home in the spine. See also D6.

**C3 — "ledger.md, append-only" vs the spec's ledger-entry update semantics.**
`05_elicitation.md` §5: ledger entries are versioned objects whose `consumed_by` is "stamped as artifacts pin it" and whose `superseded_by` is set on later revision — in-place amendment of existing entries. A strictly append-only single `ledger.md` (spine seed + AD-8/conventions) cannot do this without an amendment-entry convention the spine doesn't define. Minor, but SM-4 (question rent) and the staleness engine both read `consumed_by`, so the resolution is load-bearing.

---

## 2. Dropped with divergence risk (in scope or cannot-be-retrofitted; neither encoded nor deferred)

**D1 — Repair pipeline tiers (FR-35; `07_runtime.md` §4).** Tier 0 deterministic dependency check → Tier 1 cheap-model plausibility → Tier 2 regenerate only failing sections, triggered only by the frontier, proposed-diff-only on human-touched spans. Absent from every AD and from Deferred. Repair spans kernel (frontier trigger), store (section status), and LLM dispatch — exactly the cross-unit shape that diverges per implementer. MVP exercises it constantly (loop-backs and revised answers stale artifacts).

**D2 — Summary regeneration timing (FR-33; `07_runtime.md` §3).** "Regenerated only on acceptance and stored as part of the version — summary and content cannot drift." The spine's deterministic chokepoint cannot generate a summary itself (it's a cheap-model call), so the acceptance entrypoint's contract — accept requires a harness-supplied summary bound to that version — must be encoded somewhere. It isn't. Also unencoded: full-pull-after-summary-read logged distinctly (feeds summary-sufficiency).

**D3 — "Human edits always win over queued AI writes" (`07_runtime.md` §2).** AD-10 resolves AI-vs-AI contention (claims), AD-3 detects human edits after the fact, but the precedence rule when `kagami scan` finds a human edit to a section with a live AI claim or queued write is nowhere. Each worker/entrypoint author will pick their own answer.

**D4 — Generation windows keyed to per-cluster derived state (FR-3; `03_state_machine.md` §5, `05_elicitation.md` §6).** AD-9 refuses artifact creation "before its generation-window state" without saying *whose* state. The spec is explicit: windows and gate placement key off per-cluster derived state (a dossier for cluster 1 while cluster 2 is still mapping is legal), except the Gap Register window which is run-level. A run-level implementation of AD-9 blocks legal Deepen parallelism (AD-10's whole point); a naive per-cluster one weakens the direction-content ban.

**D5 — Run manifest contents (`04_artifacts.md` §3).** Spec: run id, rooting Intuition Note, **derived state per cluster**, budget counters, **monitoring config**. Spine seed annotates `manifest.yaml` as "derived state, budgets" — monitoring config and the rooting note are dropped, and "per cluster" is unstated. The schema-field-list deferral covers artifact types via 04 §1/§2 + 07 §1; the manifest lives in 04 §3 and is not clearly inside that deferral.

**D6 — Dispatch-table maintenance and operation-class tagging (`07_runtime.md` §5; `08_observability.md` §2).** Every `llm_call` event must carry purpose tag, operation class, model tier, tokens, cache-hit — the spine's event convention mandates only the `role` tag. And the static human-maintained operation→tier table needs a home (config? schemas/?) and an owner; the spine is silent. Without operation-class logging, the token ledger and tiering decisions (layer 2) can't be computed later.

**D7 — Dormant monitoring in MVP (FR-7).** PRD §7.1 makes Dormant reachable in MVP, with "continues to receive monitoring updates and can be reopened automatically… when a staling alert fires." Only *post-decision* monitoring (FR-8) is deferred. A Claude Code plugin has no daemon — how Dormant monitoring runs (on-next-invocation sweep? explicit `kagami monitor`? deferred outright?) is a platform-shaped question the spine neither answers nor defers.

**D8 — FR-47 and the run-1 observability schema commitments.** FR-47 is missing from the spine's `binds` line entirely (binds: FR-1..41, 45, 46, 42/43/44 non-preclusion). The Design Audit loop deferral doesn't carry FR-47's permanent exemption (triad fields + E6 unprimed questions never statistically demotable). Worse, `08_observability.md` §4 names two schema commitments "made from run 1 because they cannot be retrofitted": the stable question-class key (leverage × state × form, in every ledger entry) and late-arriving outcome joins by run id. The spine's own non-preclusion posture (AD-14) has no observability analog; deferring cross-run analytics without pinning these two makes v1 ledgers unusable by the v2+ audit loop.

**D9 — FR-5 gate loosening.** Researcher-approved collapse of a review gate to a notification, grounded in derived per-researcher aggregates only (never raw events — the one sanctioned G1 exception, `08_observability.md` §1). Not deferred with the analytics loop (it reads layer-2 aggregates, which `kagami metrics` produces in v1) and not encoded. Also sits awkwardly against AD-11's absolute "Nothing in the core or skill reads events.jsonl during a run" — the spec's exception should be either carried or explicitly deferred.

---

## 3. Dropped but harmless (single-unit, transcribable, or moot in MVP)

- **FR-1/FR-2 — loop-back cause annotations and skip waivers.** Validation inside one transition entrypoint; transcribable from 03 §2.
- **FR-6 — five entry modes and backfill.** Skill-flow concern; the "non-empty Intuition Note + Inquiry Frame before Map" invariant could ride the window table but is low-risk either way.
- **FR-23 — question-form ladder (confirm → menu → rank → free text).** Interviewer judgment, mechanically unenforceable; the ledger's `form` field (audit trail) is what matters. Mild tension with AD-1's "no rule may exist only in a SKILL.md" — worth one line in the skill anyway.
- **FR-20 — provisional status flow.** `provisional` is one value in the status enum (schema data); the count-at-Decide surface is v2.
- **FR-39 — content-stripping rules for shared aggregation.** No sharing surface exists in MVP (flag default off per AD-12; layer-3 store deferred), so nothing can leak; but the stripping rules should be named inside the cross-run-analytics Deferred entry so they ride the deferral explicitly rather than vanish.
- **Micro-probe evidence type (Gap Register; Non-Goal #7 boundary).** Pure schema data; covered by the field-list deferral.
- **FR-26 — two-cut validation and human cluster naming.** A schema-registry validation rule (draft with one clustering fails validation); repair protection of human-edited names rides D3/D1's human-span rule.
- **`premature_ideas` visibility gating (`05_elicitation.md` §6).** "Visible only after Propose opens" — Propose is v2; quarantine itself is encoded (AD-9).
- **FR-18 — fixed four-class frontier priority order.** Single-unit (kernel); reason-class logging is already in the event families.

---

## 4. Scope creep (invented beyond both inputs)

- **AD-3's definitional rule + `kagami scan`.** "Out-of-band = definitionally human" and content-hash detection appear in neither input. A reasonable mechanization of FR-12/FR-19 — but the definitional rule has an unexamined edge: non-human out-of-band changes (git checkout/merge, formatters, sync tools) acquire human provenance and silently resolve unknowns. Worth one sentence acknowledging the trade.
- **AD-4's store rule: artifact content must cite a generating role session.** Presented as "what 'the Interviewer never generates content' means mechanically" — neither the PRD nor `docs-spec/06_roles.md` requires session citation on writes. Plausible enforcement invention, but it is new store surface (session identity as a first-class store concept) with no source requirement behind it.
- **memlog.py contract + `uv run` invocation conventions.** Imported from the BMAD ecosystem, not from either input. Consistent with the Platform NFR's "following its layout conventions," so benign — noting only for completeness.

---

## Verdict

The spine is faithful on the load-bearing negotiated items (chokepoint, standalone core, both accepted platform trade-offs, v2 non-preclusion, E6 ordering). Its gaps concentrate in `07_runtime.md`'s mid-level contracts — repair tiers, summary timing, human-write precedence, per-cluster window keying, dispatch/operation-class accounting — which are precisely the cross-unit contracts the spine exists to pin. C1 (embeddings) is the one place it quietly overrides the spec rather than implementing it. D8 (FR-47 + run-1 schema commitments) is the one place its own non-preclusion discipline has a blind spot.
