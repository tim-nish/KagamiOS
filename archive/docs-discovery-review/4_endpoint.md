# Review 4 — The Discovery Endpoint

**Question:** The current design ends with a Direction Decision. Would Discovery producing a curated **portfolio of competing research opportunities** (selected direction, promising alternatives, rejected directions with reasons, future opportunities) be a stronger endpoint — or is the Direction Decision already the correct abstraction?

**Verdict in one paragraph.** Split the proposal into its two readings. As a change of *terminal semantics* — "the product of Discovery is a portfolio" — it should be **rejected**: it would dissolve the design's sharpest and most defensible idea, that the product is a decision plus the understanding required to make it, and it would reopen the survey-tool failure mode that `vision.md` was built to close. As a description of the *shape of the terminal artifact*, it is **correct and largely already true**: the baseline's Direction Decision already contains parked candidates with revival conditions and a written comparison; the review recommends completing this into an explicit portfolio structure (S6). The right slogan: **portfolio as format, decision as event.**

---

## 1. What the baseline already contains

Checking the four proposed portfolio components against `artifacts.md` and `state_machine.md`:

| Proposed component | Baseline status |
|---|---|
| Selected direction | Direction Decision, core field |
| Promising alternatives | **Present**: "parked candidates with revival conditions" (Direction Decision), fed by P5's plural-competing requirement and monitored post-Decided (`state_machine.md` §6) |
| Rejected directions with reasons | **Partially present**: "why this over the others" is a comparison authored from the winner's side; there is no per-candidate rejection record |
| Future opportunities | **Present in the Dissolution Memo only** ("salvaged fragments — spawned Intuition Notes"); absent from the Decision |

So the gap between baseline and proposal is two missing fields, not a missing abstraction. That observation drives both halves of the verdict.

## 2. Why portfolio-as-*endpoint* should be rejected *(Do not change — D5)*

1. **It removes the stopping point.** `vision.md`'s central contrast: "a survey has no natural stopping point; discovery does — the point where more reading no longer changes the choice." A decision has a convergence test (does the candidate set still change?); a *curated portfolio* has a coverage test (is anything promising missing?), and coverage is unbounded. Every convergence mechanism in the design — the Confidence Checklist as convergence test, depth budgets, the "further reading no longer changes the candidate set" signal (`state_machine.md` §5) — is anchored to the choice. Re-anchor the endpoint to a portfolio and those mechanisms lose their reference point.
2. **It removes the forcing function for understanding.** E7 says confidence is the product and understanding cannot be delegated. Commitment is what forces internalization: writing "why this over the others" is the act that reveals whether the researcher actually understands the landscape or has merely accepted artifacts. A portfolio deliverable is precisely a way to *defer* that act — it is possible to curate an excellent portfolio of opportunities one doesn't understand deeply enough to choose among. Success criterion 3 (the researcher can answer the checklist from their own head) is tested by choosing, not by curating.
3. **It weakens the terminal condition's honesty.** The design's terminal event is subjective by declaration — the researcher *confidently selects* — and `bmad_transfer.md` §4.1 insists no mechanical criterion may close the Decide gate. "A portfolio was produced" is exactly such a mechanical criterion, and an easier one to satisfy dishonestly than "the researcher signed a comparison."
4. **The failure mode is empirical, not hypothetical.** `vision.md` names the survey-tool pull "the strongest gravitational pull during implementation." An endpoint defined as a document-set points the implementation straight down that gradient.

One further note: for the multi-direction case the baseline already permits plural selection ("chosen direction(s)" in `artifacts.md`) — a researcher who genuinely wants to leave with two live directions can. The portfolio proposal is not needed for that either.

## 3. Why portfolio-as-*format* should be adopted — S6 (Should consider)

The proposal is right about the underlying asset: a completed run has produced expensive, evidence-backed knowledge about directions *not* chosen, and in the baseline that knowledge is scattered (candidate cards, red-team notes, parked list, ledger). Three real consumers want it in one place:

- **The advisor conversation (DQ10).** The case one brings to an advisor is portfolio-shaped: "here are the four serious options, here is why I lean B." The baseline already leans toward a "presentation surface"; the portfolio *is* that surface.
- **The future self.** When post-Decided monitoring fires a revival condition (`state_machine.md` §6), the researcher returns months later; per-candidate rejection reasons are what make the return cheap.
- **Anti-sunk-cost hygiene.** A decision recorded as one winner invites over-commitment; a decision recorded as a ranked portfolio with revival conditions makes switching later a planned move rather than an admission of failure.

**Recommended change (S6), all within the existing artifact set — no new state, gate, or elicitation:**

1. **Structure the Direction Decision explicitly as a portfolio** with four sections: *selected* (with the written comparison, as now); *parked* (with revival conditions, as now); *rejected* (new — see 2); *spawned* (new — see 3).
2. **Add `rejection_reason` to the Candidate Direction schema**, filled at the Decide gate for each non-selected, non-parked candidate — one or two lines, mostly harvestable from the red-team notes and the comparison table (DQ5), so the marginal cost at Decide is minutes. Distinguishing *parked* (viable, conditions attached) from *rejected* (reasoned out) also sharpens what "parked" means, which the baseline leaves implicit.
3. **Port the Dissolution Memo's "salvaged fragments" field to the Decision**: gaps marked `real-but-not-mine`, and any `premature_ideas` quarantine content worth keeping, become spawned Intuition Notes listed in the portfolio. This closes a small asymmetry in the baseline — dissolved runs preserve their by-products, decided runs currently drop theirs.

**Affects:** `artifacts.md` (Direction Decision, Candidate Direction), DQ7 (the two-page brief generated from the handoff bundle becomes the portfolio rendered for a reader), DQ10 (the presentation surface gets its format). **Unaffected, by design:** the Decide gate, the constitutive selection decision, the Confidence Checklist audit, the convergence machinery, terminal-state semantics.

## 4. Answer to the question as asked

The Direction Decision **is** the correct abstraction — the reviewer's strongest finding in its favor is that every convergence and understanding-forcing mechanism in the design is anchored to it, so replacing it is not a local edit but a load-bearing demolition. The portfolio idea is nevertheless more than cosmetic: it names real value the baseline creates and then under-records. Adopt it as the structure of the terminal artifact (S6), decline it as the terminal semantics (D5).
