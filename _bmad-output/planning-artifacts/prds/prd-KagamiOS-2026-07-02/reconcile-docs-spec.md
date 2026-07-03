# Input Reconciliation — docs-spec/ vs. prd.md + addendum.md

Input reconciled: `docs-spec/` (10 files: README.md, 01_vision.md–09_open_items.md) against `prd.md` + `addendum.md`.

## 1. Real omissions (concrete decided mechanisms missing entirely)

1. **Depth budgets mechanism** — `docs-spec/03_state_machine.md` §6: budgets are set at Map exit (human-owned, revisable: clusters to deepen, papers-per-cluster, soft time horizon); exhaustion raises a specific rent-paying "extend cluster N by N papers, or proceed?" question (L6). No FR covered the *existence* of this mechanism — only its "never auto-enforced" negative framing appeared (Non-Goal #9, OQ-D).
2. **`human_read` flag + one-line human reaction** — `docs-spec/02_principles.md` E7 and `docs-spec/03_state_machine.md` state table (Deepen exit criterion; Decide requires it for papers defining each surviving candidate). Missing everywhere — gate-blocking mechanism, not schema detail.
3. **P5 — plural competing candidates, fixed comparison table, no aggregate score** — `docs-spec/02_principles.md` P5. Only appeared inside the non-normative UJ-1 narrative; no FR stated the requirement.
4. **Candidate red-teaming** — `docs-spec/03_state_machine.md` Propose row and `docs-spec/04_artifacts.md` (Candidate Direction's `red-team notes`, harvested into `rejection_reason`). Not stated as a requirement anywhere.
5. **S1 candidate-generation vocabulary (transplants, why-now/capability-overhang candidates)** — Candidate Direction glossary entry only said "cites gap or synthesis evidence," dropping the broader generation vocabulary.
6. **Operational test for human-only classification** — `docs-spec/05_elicitation.md` §1: "would two equally competent researchers with the same corpus answer differently?" Missing from FR-17.
7. **Generation-window enforcement as a testable requirement** — mentioned only in glossary/addendum prose, never as a numbered FR with consequences.
8. **Scout's corpus scope (S2)** — preprints, code repositories, workshop venues, not just publications. FR-25 only said "raw literature corpus."
9. **Field Map's recency profile field** — how fast a cluster moves / how stale its published record runs. Absent.
10. **Dissolution Memo's salvaged fragments (spawned Intuition Notes)** — glossary entry dropped this field.
11. **Handoff bundle's two-page rendered portfolio brief** — only the functional resumption test (SM-5) was captured, not the concrete deliverable form.
12. **Permanent exemption from statistical demotion** — the two E6 unprimed questions and the P3 constitutive triad are permanently exempt from the Design Audit Report's statistical demotion (`05_elicitation.md` §5, `08_observability.md` §5). Absent from FR-40/FR-41.
13. **MVP §7.1 didn't explicitly enumerate Landscape Synthesis / minimal-profile Candidate Direction / minimal-profile Direction Decision as in-scope**, though `docs-spec/04_artifacts.md` §5's minimal-run profile explicitly includes "Candidate cards (direction, evidence, red-team line); Decision (selected + why-over-others)" as minimal-profile, not full-profile accretion.

## 2. Flattened qualitative substance

1. **E7 — "Confidence is the product; understanding cannot be delegated."** Tied to omission #2; the philosophical claim (system verifies the *trace* of reading, never the understanding itself) was absent.
2. **E6 — "homogenization" as the deep failure mode.** Reduced to the word "deference" inside a Non-Goal rationale; the vivid "AI's fluent framing becomes everyone's framing" articulation was dropped.
3. **P5's ethos of refusing a single anointed answer.** Beyond the missing FR, the philosophy (a computed ranking would be the system choosing for the researcher, against "the mirror") only surfaced in non-normative UJ prose.
4. **The vision's litmus test for every mechanism** — "would this have moved the Signature investigation toward a confident choice, or would it have been overhead?" — reduced in addendum.md A5 to a question-count sanity check only, losing its role as the design test for whether any mechanism belongs in the system.
5. **"A survey can be delegated; understanding cannot"** — the specific delegable/non-delegable contrast from `01_vision.md` "Three consequences" was missing from §1 Vision.

## 3. Non-Goals (§6) / MVP Out-of-Scope (§7.2) vs. docs-spec

**Zero gaps.** §6's 10 Non-Goals full 1:1 match `docs-spec/README.md` Standing Refusals (7 items, D1–D10). §7.2 correctly carries all eight deferred features (O1–O8) with correct adoption triggers, none omitted, none added.

## 4. Factual drift

1. **"All five terminals reachable"** (§7.1) — should be **three** terminals (Decided, Dissolved, Dormant) per `docs-spec/README.md` and `03_state_machine.md` §2. Numeric error.
2. **FR-14 "Ten-artifact catalog"** lists eleven distinct types. This ambiguity originates in docs-spec itself (README says "Ten artifacts," `04_artifacts.md` §2 has 11 `###`-level entries) — the PRD inherited it uncorrected and stated the count as if settled.

## Disposition

All applicable items fixed directly in `prd.md`/`addendum.md` during the same finalize pass (see `.memlog.md` for the specific change log). None required a scope change beyond what `docs-spec/` already decided.
