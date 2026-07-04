# Golden Toy-Run Protocol (AD-27)

Fixed and repeatable, per Story 7.5. A future run of this protocol should reproduce the same clusters, the same dossier count, and the same terminal outcome (an accepted Gap Register), even though exact prose will differ run to run since drafting isn't itself deterministic.

## Topic

**In-context learning (ICL) in large language models.** Chosen because it's a field I (the executing model) can judge the plausibility of a field map, a dossier's Evolution section, and a stated gap against, without needing external verification — the entire point of a toy run is judging mechanics, not outsourcing judgment of content quality.

## Corpus scope — fixed, not live-searched

Six real, well-known papers, hand-entered as fixture data rather than fetched via a live Scout corpus search:

| id | title | method_class | source |
|---|---|---|---|
| ppr-gpt3 | Brown et al. 2020, "Language Models are Few-Shot Learners" | prompting | arxiv |
| ppr-cot | Wei et al. 2022, "Chain-of-Thought Prompting Elicits Reasoning" | prompting | arxiv |
| ppr-bayes | Xie et al. 2022, "An Explanation of In-context Learning as Implicit Bayesian Inference" | theory | arxiv |
| ppr-algo | Akyürek et al. 2022, "What Learning Algorithm is In-Context Learning?" | theory | arxiv |
| ppr-demo | Min et al. 2022, "Rethinking the Role of Demonstrations" | empirical-analysis | arxiv |
| ppr-induction | Olsson et al. 2022, "In-context Learning and Induction Heads" | mechanistic-interpretability | anthropic-blog |

**Why fixed instead of live:** a golden protocol's entire value is repeatability. A live Scout search against OpenAlex/arXiv could return different papers on different days (index changes, rate limits, an API key that isn't configured in every environment this protocol runs in), which would silently break "fixed, repeatable." A fixed corpus is also honest about what this run tests — the harness's *mechanics* (state machine, write-guards, role charters, elicitation, event log, refusal ceiling), not Scout's actual search quality, which is a live-network concern out of this story's scope.

**Deliberately excluded, known to me:** Hendel et al. 2023, "In-Context Learning Creates Task Vectors" — a real, well-known ICL sub-area (task-vector / activation-patching approaches) I know exists but did not include in the six-paper corpus above. This is a deliberately planted gap, not an accidental omission — see the rubric evaluation's cluster-miss check for why.

## Config — pinned

- `refusal_ceiling: 3` (default, unchanged)
- `token_budget_soft_limit: 5000` (low enough that this toy run is expected to cross it, to prove the warning fires and doesn't block)
- Model tier: not actually invoking a live subagent model call for this run — see the verification doc for exactly what "reported `llm_call`" means in this execution.

## Depth budget

2 of the 4 clusters Cartographer's `method_class` cut produces (`prompting`, `theory`) are put in scope; `empirical-analysis` and `mechanistic-interpretability` are left out of this toy run's budget — a real, bounded depth-budget decision, not every cluster getting deepened.

## Sequence

Frame (intuition → accepted Inquiry Frame) → Map (Cartographer drafts two cuts, `method_class` chosen, depth budgets set) → Deepen (2 clusters: Historian writes Evolution, representative papers marked read, Skeptic critiques, dossier accepted) → Synthesize (solved/open table from the 2 accepted dossiers) → Locate (Gap Register drafted, `why_does_this_gap_exist` set, accepted) → MVP terminal check.

Full command-by-command execution log and rubric evaluation: `story-7.5-verification.md` in this same directory.
