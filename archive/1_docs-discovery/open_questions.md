# KagamiOS v2 — Open Questions

Unresolved design questions for the discovery scope, ranked roughly by how much they could change the design. v1's open questions that remain relevant are folded in rather than repeated; several v1 questions (deadline mode, execute-stage domains) fall away with the scope.

---

## DQ1. What is the smallest version worth dogfooding?

Same discipline as v1's Q1, new answer needed. The Signature investigation is the test case, and the kernel can be run *by hand*: a human (or a plain LLM session following the docs) plays the Interviewer, producing question cards and artifacts as Markdown.

**Lean:** hand-run exactly four pieces — the Inquiry Frame with its menu question, the Field Map with the L2/L4 cluster question, one Cluster Dossier with a mandatory Evolution section, and the Gap Register with both `why_does_this_gap_exist` and `meaningful_to_me`. Keep the Question Ledger as a simple appended log. If the questions feel like the system reading your mind, build tooling; if they feel like a form, no tooling will save the design.

## DQ2. How is question rent measured honestly?

`consumed_by` non-empty is necessary but weak: an answer can be consumed by an artifact and still have changed nothing (the AI's default was identical, or the downstream artifact would have been the same either way). Counterfactual rent — "would the run have differed?" — is what E2 actually promises and is hard to observe.

**Lean:** track two proxies during dogfooding: (a) answer-differs-from-default rate (if the researcher nearly always accepts defaults, the questions weren't questions), and (b) staleness cascades triggered by answer revisions (answers that, when changed, invalidate a lot were high-leverage). Neither is sufficient; both are cheap.

## DQ3. The menu is also an anchor

E3/E6 protect against AI-proposed *directions*, but evidence-grounded elicitation has a subtler anchoring problem: the **clustering itself is an AI judgment** that frames everything downstream. If the AI partitions the field into five clusters, the researcher chooses among *those five* — the ontology was never theirs. This is the discovery version of v1's Q3 (homogenization), one level up.

**Open.** Candidate mitigations, untested: offer two structurally different clusterings and ask which cuts the field the way the researcher sees it; make cluster *naming* a human act (naming is framing); have the Skeptic attack the clustering ("what does this partition hide?"); record the researcher's pre-map guess at the field's structure (an E6-style unprimed ask) and diff it against the AI's map.

## DQ4. The stopping problem, beyond budgets

Depth budgets are a crude fix for non-termination. The real quantity is value-of-information: does the next paper have any chance of changing the candidate set or the choice? The convergence test (`state_machine.md` §5) asserts this can be detected — but detecting it *reliably* is a research problem itself, and a system that says "stop reading" too early produces confident wrong decisions (failing success criterion 2 to satisfy criterion 1).

**Lean:** budgets + the convergence test as an advisory signal, never auto-enforced; log every "extend or proceed?" answer and, post-hoc, whether extensions ever changed the candidate set. That log is the dataset the better stopping rule would need anyway.

## DQ5. Candidate comparison: how structured?

How many candidates should Propose produce (two? five?), and should fit-to-profile be scored? A numeric fit score against the Researcher Profile invites false precision and quietly automates the constitutive selection gate; pure prose comparison may hide inconsistent reasoning across candidates.

**Lean:** 3–5 candidates; a fixed *qualitative* comparison table (same axes for all candidates: gap strength, why-now, requirements vs. profile, strongest objection) with no aggregate score. The human writes the "why this over the others" paragraph from the table, not from a ranking the system computed.

## DQ6. The Researcher Profile: cold start, drift, and creep

The profile is most valuable when mature and empty on day one — exactly backwards for a first run. Taste also drifts (this project may *change* what the researcher likes), and an accreting profile risks becoming a stereotype the system over-fits to ("you bounced off two theory papers in 2026, so I stopped showing you theory").

**Open:** how strongly should Propose weight the profile vs. merely annotate with it? Should profile entries age or require reconfirmation? **Lean:** annotate, never filter — the profile writes fit *notes* on candidates but never removes one.

## DQ7. What exactly does the handoff need?

The Direction Decision's handoff bundle claims a downstream process can proceed "without re-interviewing the researcher." Against what consumer is that tested? A v1-style lifecycle machine would want the bundle to seed its Frame/Survey states (the Decision looks a lot like a very strong Triage Memo + partial Question Hierarchy); a human advisor wants two pages; a downstream agent wants the whole graph.

**Lean:** define the bundle as the artifact graph plus a generated two-page brief, and run v1's resumption test on it: can an agent with only the bundle answer the Confidence Checklist questions? That doubles as the objective evaluation for DQ9.

## DQ8. Is discovery ever finished?

The design says KagamiOS terminates at Decided, with post-terminal monitoring that can stale the Decision. But monitoring shades back into discovery: a staling alert may warrant re-running Locate, which reopens Propose… Is "Decided" a terminal state or a low-energy state the project rests in? And when the researcher's downstream work spawns a *new* vague intuition, is that a new run or a loop?

**Lean:** new intuition = new run (new Intuition Note, shared Researcher Profile, citable prior artifacts); staling alert = reopen the old run at the affected state. Keeps runs bounded without pretending the world stops.

## DQ9. Evaluation: decision robustness is testable — barely

Success criterion 2 (the post-decision deep survey confirms rather than overturns the landscape) is the design's one objective test, but it takes months to resolve and is n=1. The checklist self-test (criterion 3) is quick but self-reported. Time-to-decision is confounded by intuition quality.

**Lean:** accept n=1 for v2, but pre-register the robustness test at Decide time: write down, in the Decision memo, the specific claims about the landscape that downstream work could falsify ("no published method does X under constraint Y"). Falsification of a pre-registered claim is a clean, honest failure signal — and its absence after real downstream work is the strongest available success signal.

## DQ10. Whose confidence?

The terminal condition is the researcher's confidence — but for a PhD student, the real gate is the advisor's confidence, and for a lab, the direction decision may be collective. v1's Q7 (single researcher vs. lab) lands differently here: discovery artifacts are exactly what one brings *to* an advisor meeting, which suggests the near-term answer is not multi-user gates but a **presentation surface** — the handoff bundle formatted as the case one makes to whoever must also be convinced.

**Lean:** v2 stays single-researcher; treat "convince the advisor" as a consumer of the handoff bundle (DQ7), not a second gate. Revisit if dogfooding shows the advisor conversation reshaping decisions in ways the artifacts never captured.
