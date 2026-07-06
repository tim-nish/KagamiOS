# Review 1 — Alignment with Real Research Practice

**Question:** Does KagamiOS v2 match how strong computational/ML researchers actually move from vague intuition to a concrete research direction? Where does it diverge, and are the divergences acceptable design choices or serious flaws?

**Verdict in one paragraph.** The v2 design is a faithful — in places unusually faithful — model of *deliberate field entry*: the mode a strong researcher adopts when entering an unfamiliar area with enough at stake to justify systematic landscape work (a PhD topic, a lab's new bet, a career pivot). Several of its mechanisms encode things experienced researchers do that tools never capture. Its divergences from practice fall into two groups: deliberate scope choices that are defensible (no experiments, no social layer, single-shot runs) and one structural divergence that is a genuine flaw at "should change" severity — the gaps-only basis for AI-generated candidates.

---

## 1. Where the design matches practice well

These points are audited as **Do not change**; they are the design's load-bearing alignment with how strong researchers actually work.

1. **Reading reframes the intuition (P2, Deepen → Frame loop-back).** The single most common real event in early discovery is discovering that your question was the wrong question. The baseline makes this a first-class transition and calls Frame "the most-revised artifact in the system, and that is the system working" — that phrase could have been written by a research advisor. Correct.
2. **`human_read` + reaction (E7).** No strong researcher chooses a direction from summaries; taste forms only through contact with primary sources. Most AI research tools get this exactly wrong (they optimize for sparing the human the reading). The baseline treats reading as unautomatable and verifies the trace. This is one of the design's best calls.
3. **Evolution sections and graveyard-awareness (Cluster Dossier).** The question a senior researcher asks about any "gap" is *"why hasn't this been done?"* — and the answer usually lives in abandoned branches of the field's history. Making per-cluster evolution mandatory, and `why_does_this_gap_exist` a forced field, encodes senior-researcher instinct directly. Correct, including the choice to keep the *global* narrative retired.
4. **Dissolution as success (P10).** Strong researchers kill bad ideas fast and cheaply, and regard a fast kill as productive. Most tools structurally can't represent this. Correct.
5. **Ask-against-evidence (E3).** This is how good advisors operate: they don't ask "what are you interested in?"; they show you the landscape and watch what you react to. The kernel mechanizes recognition-over-recall in the same way. Correct.
6. **The Confidence Checklist.** "What would I need to know to defend this choice at group meeting?" is the real internal test researchers apply. Drafting it at Frame and auditing it at Decide is a faithful formalization.
7. **Entry modes (P11).** Real discovery starts paper-first and tool-first at least as often as intuition-first. Covered.

## 2. Divergence A — candidate generation is gaps-only *(the serious one)*

**The practice.** In ML specifically, strong research directions frequently do not originate as *literature gaps* at all. The dominant real-world generators are:

- **Recombination / transplant:** "technique X from field A, applied to problem structure B" (attention → vision; diffusion → molecules; signatures → sequence models, which is the dogfooding case itself).
- **Capability overhang / why-now:** a new tool, dataset, hardware regime, or model scale makes an old, well-known-hard thing suddenly tractable. The "gap" was always visible; what changed is feasibility.
- **Anomaly-chasing:** a result in the literature that shouldn't be true, or a baseline that wins when it shouldn't.

None of these has evidence-of-absence in a Gap Register; a transplant direction may correspond to *no* gap in any surveyed cluster, because it lives between clusters.

**The baseline.** `state_machine.md` §3 (Propose row) and `artifacts.md` (Candidate Direction) restrict AI generation to "candidates from accepted gaps only." The researcher may add candidates by hand (`origin: human-added`), so the path exists — but the system's generative machinery, its comparison scaffolding, and its evidence-tracing all privilege gap-rooted directions. The `why_now` field on Candidate Direction acknowledges the capability-overhang pattern but has no upstream artifact feeding it.

**The diagnosis.** Two distinct restrictions are fused in E6, and only one of them is doing anti-anchoring work:

- The **timing** restriction (no direction-shaped content before the Gap Register is accepted, unprimed lean recorded first) is the actual anchoring defense. **Do not change.**
- The **provenance** restriction (generated candidates must be rooted in register entries) is an extra constraint that contributes nothing to anchoring — by the time the window opens, the researcher's independent signal is already protected — while cutting off the candidate classes above.

**Recommendation S1 (Should consider).** After the generation window opens, allow Propose to generate candidates grounded in the *Landscape Synthesis* as well as the Gap Register: cross-cluster transplants (justified by the comparison matrix), capability-overhang candidates (justified by trend entries), each still required to cite its evidence and still passing the red-team. Affected: `artifacts.md` Candidate Direction (`supporting gaps` becomes `supporting evidence: gaps and/or synthesis links`), `state_machine.md` Propose row, `principles.md` E6 consequence wording. The generation window, ask-before-show, and the ban on pre-Locate direction content are all unchanged.

## 3. Divergence B — a publication-centric corpus

**The practice.** In fast-moving ML areas the peer-reviewed record lags the frontier by six to eighteen months. Working researchers triangulate arXiv, code releases, workshop papers, and community chatter; the *shape* of a field (clusters, communities) is stable in the published record, but the *frontier* sections of a dossier and the "solved/open" table are exactly where publication lag produces confident wrong answers — the failure mode success criterion 2 ("no discovering the gap was filled two years ago") exists to prevent, and the one place the baseline is currently weakest against it.

**Recommendation S2 (Should consider).** Extend the Scout's evidence sources to preprints, code repositories, and workshop venues, and add a per-cluster *recency profile* to the Field Map (how fast this cluster moves; how stale its published record runs). The monitoring config in `state_machine.md` §6 already implies this capability; the change is to use it *during* the run, not only after Decided. Affected: Field Map fields, Scout role, Dossier Frontier section. No architectural change.

**Explicitly not recommended:** modeling the *social* channel (advisor conversations, peer feedback) inside the system. The baseline's DQ10 lean — treat the advisor as a consumer of the handoff bundle, not a second gate — is right for v2. **Do not change.**

## 4. Divergence C — no micro-probes

**The practice.** Strong computational researchers interleave reading with one-hour pokes: run the released code, check whether the naive baseline already works, check whether the dataset exists at usable scale. For gap verdicts of `hard` or `impossible`, a probe is often *cheaper and more reliable than any amount of reading* — the literature systematically underreports "we tried it and it was fine."

**The baseline** excludes all experimentation by scope (`vision.md`, `2_questions.md`), which is the right boundary for its purpose: the failure it guards against is discovery sliding into execution. But a total ban means some `why_does_this_gap_exist` fields will hold verdicts that a strong researcher would never accept on textual evidence alone — and the Decision inherits that softness.

**Recommendation S3 (Should consider).** The minimal-change remedy, in order of preference: (a) admit a **micro-probe** as a Gap Register evidence type — human-executed, hard-bounded (hours, not days), recorded as evidence for exactly one `why_does_this_gap_exist` field, never producing artifacts of its own; or, if even that feels like scope creep, (b) a `probe_before_commit` flag on the Direction Decision marking which load-bearing feasibility claims rest on reading alone, so the downstream process knows what to verify first. Option (b) changes nothing about the boundary and is nearly free. Affected: Gap Register schema, Direction Decision, one sentence in `vision.md` "not a lifecycle manager."

## 5. Divergence D — weight and formality vs. satisficing

**The practice.** Strong researchers often satisfice: a few days of reading, one advisor conversation, commit, course-correct during execution. Nine artifact types, a question ledger, budgets, and gates is more ceremony than most real discovery episodes carry.

**The audit finding:** this is *mostly* defended already — P9/E2 make ceremony a named enemy, DQ1's lean is a four-artifact hand-run, and dissolution-in-days is a success criterion. The residual risk is that the artifact schemas, as written, don't distinguish load-bearing fields from nice-to-have ones, so a literal implementation makes every run pay full freight.

**Recommendation S8 (Should consider).** Mark, per artifact, the minimal mandatory field set versus optional accretions — a "minimal-run profile" under which a run can reach Decided or Dissolved in days. This is DQ1's lean promoted from a dogfooding note to a schema property. Affected: `artifacts.md` (a column or annotation per artifact), `README.md`.

## 6. Divergences that are acceptable as-is *(Do not change)*

- **D1 — The funnel itself.** Real discovery zigzags, but the baseline already handles this: states are derived milestones, not enforced phases ("different clusters may be in different states simultaneously"), and loop-backs are first-class. The convergence spine matches the honest structure of the task: discovery, unlike research execution, really does reduce ambiguity monotonically *in the limit* even when locally it doesn't.
- **D2 — Lifecycle exclusion.** The scope cut at Decided is the design's foundational choice and it is correct; S3 above is an evidence-type concession, not a boundary move.
- **Single-researcher, single-run model.** Real discovery runs in the background over months; Dormant plus DQ8's "new intuition = new run" lean covers this adequately for v2.
