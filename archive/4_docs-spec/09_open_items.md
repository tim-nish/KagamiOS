# 09 — Open Items and Deferred Features

*(Not normative.)* The open design questions that survive consolidation, updated for what the reviews resolved, plus the deferred optional features with their adoption triggers. Original argumentation: `docs-discovery/open_questions.md` and the two review directories.

## Open questions, updated

### OQ1. Smallest version worth dogfooding *(was DQ1 — now sharpened, still the next action)*
The Signature investigation, run by hand: Inquiry Frame with its menu question, Field Map with the L2/L4 cluster question, one Cluster Dossier with a mandatory Evolution section, Gap Register with both `why_does_this_gap_exist` and `meaningful_to_me`; Question Ledger as an appended log. The minimal-run profile (`04` §5) is now the specced version of this. Test: if the questions feel like the system reading your mind, build tooling; if they feel like a form, no tooling will save the design.

### OQ2. Honest rent measurement *(was DQ2 — mechanism resolved, validation open)*
The event log (M6) makes both proxies computable — differs-from-default rate and revision-cascade size. Open: whether these proxies actually track counterfactual rent ("would the run have differed?"). Dogfooding data decides.

### OQ3. The menu is also an anchor *(was DQ3 — partially mitigated, fundamentally open)*
The clustering is an AI judgment that frames everything downstream. Standing mitigations now in spec: the Cartographer must offer two structurally different cuts (`06_roles.md`); cluster naming is human; the Skeptic attacks partitions; the pre-map structure guess can be recorded E6-style. Open: whether these suffice — the honest answer is that ontology-anchoring cannot be fully engineered away, only made visible.

### OQ4. Stopping, beyond budgets *(was DQ4 — dataset now specced, rule open)*
The convergence test is advisory, never auto-enforced. Every extend-or-proceed answer and its downstream effect on the candidate set is logged (`08` §2); that log is the dataset a principled value-of-information stopping rule would need. Open: the rule itself. A system that says "stop reading" too early produces confident wrong decisions — criterion 2 outranks criterion 1.

### OQ5. Researcher Profile: cold start, drift, stereotype creep *(was DQ6 — rule adopted, dynamics open)*
Annotate-never-filter is now spec (`04`). Open: should profile entries age or require reconfirmation? Does a project *changing* the researcher's taste get captured? Revisit after the profile survives two runs.

### OQ6. Whose confidence? *(was DQ10 — deferred deliberately)*
v2 is single-researcher. The advisor/lab is a *consumer* of the handoff bundle — the portfolio brief is the case one brings to the meeting — not a second gate. Revisit if dogfooding shows advisor conversations reshaping decisions in ways the artifacts never captured.

### OQ7. Evaluation at n≈1 *(was DQ9 — mechanism adopted, patience required)*
Pre-registered falsifiable claims in the Decision memo are now spec (`04`), and late outcome joins are provided for (`08` §4). The robustness test still takes months per run and the strongest quality signals stay n-small. Accepted: quality metrics are vetoes, not targets (`08` §6).

*(Resolved and absorbed, no longer open: DQ5 — 3–5 candidates, fixed qualitative table, no aggregate score → P5; DQ7 — bundle = graph + rendered portfolio brief, resumption test → `04`; DQ8 — new intuition = new run, staling alert reopens the old run → `03` §7.)*

## Deferred optional features (adoption triggers)

| ID | Feature | Adopt when |
|---|---|---|
| O1 | Role-labeled voice; visibly adversarial Skeptic register | first UI pass — cheap, do it then |
| O2/O5 | Prompt-cache prefix ordering | first implementation — guidance already in `07` §8 |
| O6 | Machine-side token budgets and live meters | the cost ledger shows a state chronically overrunning |
| O3 | The Area→Community→Group→Line→Papers hierarchy rendered as a *view* over Field Map + dossiers + entity registry | the presentation surface (advisor brief) wants it — a view may be tree-shaped because a view is allowed to lie a little; the data model is not |
| O4 | Named `research_lines` subsection in dossier Evolution | dogfooding shows Evolution sections repeatedly narrating the same thread |
| O7 | Live stall surfacing ("blocked on q-014 for 6 days") | multi-week runs exist |
| O8 | Controlled question-form experiments (confirm vs. menu variants per class) | real multi-run scale — a third-year idea, not a first-year one |

## Deliberately rejected (do not reopen without new evidence)

Anthropomorphic personas; a portfolio *endpoint*; a first-class knowledge hierarchy; a database as ground truth; RAG over the artifact graph; mechanical Decide-gate closure; analytics-driven self-modification; content defaults tuned from aggregate researcher behavior; lifecycle features beyond the bounded micro-probe. Rationale: `docs-spec/README.md` §"Standing refusals" and the review directories.
