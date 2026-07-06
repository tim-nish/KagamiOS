# Navigating a Research Landscape: A Conceptual Model for Scout Exploration

*Answers to the questions in `5_questions.md` (2026-07-04). This is a conceptual discussion, not an implementation plan.*

The question: should Scout collect hundreds of papers up front (its current behavior — `kagami corpus search` returns a batch, each result becomes a paper card), or should exploration grow like a tree — a few seed papers, thin branches, extend only what proves promising, prune as evidence accumulates?

---

## 1. Is "thin branches first" a good strategy?

**Yes — it is close to how expert human researchers demonstrably work, and the empirical literature on literature search supports it.** But it has two characteristic failure modes that the design must compensate for, and the pure form of it is not quite the right shape.

What supports it:

- **Berrypicking (Bates, 1989).** Real search behavior is not one query returning one result set; it is an evolving sequence of small retrievals where each find reshapes the query. The information need itself changes as evidence accumulates — which is exactly KagamiOS's situation, since the Inquiry Frame sharpens during a run.
- **Snowballing in systematic reviews (Wohlin, 2014 and successors).** Backward/forward citation chaining from a small seed set recovers the large majority of a systematic review's final corpus, usually more efficiently than database keyword search. A few good seeds plus graph expansion beats broad querying for *recall per unit effort*.
- **Cost structure.** Reading (or card-extracting) a paper is expensive; discovering that it exists is cheap. Any strategy that commits processing budget before relevance evidence exists — which is what bulk up-front collection does — pays full price for its worst guesses. Incremental expansion lets relevance evidence arrive before the expensive commitment.

The two failure modes to design against:

1. **Seed anchoring.** The tree can only grow from where it was planted. If the seeds sit in one research community, the exploration inherits that community's terminology, citation habits, and blind spots. Scientific literature is notoriously fragmented — the same idea lives under different names in different fields (this is precisely the phenomenon Swanson's "undiscovered public knowledge" work exploited: literatures A and C that never cite each other but are logically connected through B). A pure snowball never crosses a citation desert. **For a system whose purpose is finding gaps, this is the most dangerous bias, because the gaps worth finding often live exactly in those deserts.**
2. **Rich-get-richer distortion.** Citation graphs are scale-free; expansion by citations preferentially rediscovers hubs. Hubs are useful landmarks but low-information after the first visit — the promising *thin* branch is often a low-citation recent paper the graph gradient points away from.

So the verdict: thin-branches-first is the right skeleton, but it must be a **guided graph exploration with forced diversity probes**, not a pure greedy tree. The current batch behavior isn't wrong so much as it is *one primitive* — a broad, cheap sensor sweep — that the tree strategy still needs, just demoted from "the whole strategy" to "one action type among several."

---

## 2. Is MCTS the right analogy?

**Mostly no, though it gets two things right.**

What MCTS gets right, and worth keeping:

- **Optimism under uncertainty (UCB).** Allocate the next expansion to the branch whose *upper confidence bound* on value is highest, not its mean estimate. Branches barely explored get an uncertainty bonus. This is the correct exploration/exploitation arithmetic regardless of algorithm.
- **Anytime behavior.** Stop whenever the budget runs out and the current best answer is meaningful. Literature exploration needs exactly this property.

Where the analogy breaks:

| MCTS assumes | Literature exploration has |
|---|---|
| A **tree** — states reached by one path | A **graph** with massive convergence: the same paper is reached via citations, authors, venues, and semantic similarity. Treating it as a tree double-counts and misattributes credit. |
| Cheap **rollouts** to a terminal state | No terminal state and no cheap simulation. You cannot "play out" a research branch to see how it ends; every evaluation costs real retrieval and reading. |
| A crisp **reward** at the end | Delayed, subjective, non-stationary value: "was this branch worth it" depends on a human's evolving frame and on what *other* branches found (a paper's value drops if another branch already covered its idea — rewards are not independent across branches). |
| Moves change the state | Reading a paper doesn't change the literature; it changes your *knowledge* of it. This is a belief-state (information-gathering) problem, not a game. |

That last row is the deep one: this is not adversarial planning, it is **sequential experimental design** — choosing which expensive observation to make next to maximally reduce uncertainty about an unknown landscape. Different family, different theory.

### Better-fitting frameworks

Ordered from closest formal match to closest behavioral match:

1. **Active search on graphs (Garnett et al., 2012+).** This is *literally* the formal problem: sequentially select nodes of a partially observed graph to label (read), maximizing the number of "targets" (relevant papers) found under a fixed query budget. One-step Bayesian-optimal policies and their lookahead corrections are well studied. If one framework deserves the title "theory of what Scout is doing," it's this one.
2. **Budgeted multi-armed bandits / best-arm identification.** Treat each research branch (a thread, a community, a query direction) as an arm; pulling = expanding it by a few papers; reward = information gained. The *pure exploration / fixed-budget* variants match scenario 1 below almost exactly, and they come with a beautifully simple algorithm (see §6).
3. **Bayesian optimization / active learning.** Model "insight density" as an unknown smooth-ish function over topic space (embedding space); each paper read is a costly sample; an acquisition function (expected information gain, UCB) picks the next sample. Correct mental model for *where to probe*, weaker on graph structure.
4. **Information foraging theory (Pirolli & Card).** The best *behavioral* model. The landscape is patches (clusters, venues, author groups); following "information scent" between patches; and — crucially — the **marginal value theorem** from optimal foraging: leave a patch when its instantaneous rate of information gain drops below the average rate available across the landscape. This gives Scout a principled, locally computable stopping rule per cluster, which MCTS never provides.
5. **Submodular coverage maximization.** For the *mapping* objective specifically (Cartographer's needs): value of a paper set = coverage + diversity, which is submodular, and greedy selection under a budget carries the classic (1 − 1/e) guarantee. Formalizes "identify a few representative papers" — representativeness is a coverage property, not a quality property.

**Synthesis:** the literature landscape is a *partially observed graph*; exploring it is *active search* guided by *bandit-style allocation* across branches, with *foraging-theoretic* patch-leaving rules, optimizing a *submodular coverage* objective early and a *best-arm* objective late. MCTS was a reasonable first pointer at this cluster of ideas, but the load-bearing concepts come from the information-gathering family, not the game-tree family.

---

## 3. Modeling the literature landscape as a search space

Not a tree. The productive model has three parts:

**The terrain — a multi-layer graph.** Nodes are papers; several edge types with different semantics: citations (directed, temporal — the only edges that encode intellectual lineage), co-authorship (encodes communities and labs), venue co-occurrence, and semantic similarity from embeddings (the only edge type that *crosses terminology barriers*, which is why it's the anti-anchoring instrument). Structural facts that matter: scale-free degree distribution (hubs exist and dominate naive expansion), strong community structure, and systematic *synonymy gaps* between communities — the deserts where literature-based discovery happens.

**The sensors — actions with different cost/information profiles.** The agent never sees the graph; it sees what its actions return:

| Action | Cost | What it reveals |
|---|---|---|
| Keyword/semantic query | Low | A biased sample of nodes matching current vocabulary |
| Expand a node (citations in/out) | Low–medium | Local graph structure, lineage |
| Shallow read (title/abstract → card) | Medium | Node features, rough relevance |
| Deep read (full text) | High | Actual claims, methods, real gaps |

The current Scout implements essentially only row 1 + 3 in bulk. The tree intuition adds rows 2 and 4 and — more importantly — a *policy* over all four.

**The state — a belief, not a position.** The state is (the known subgraph, per-node processing depth, a belief about the unexplored remainder — e.g. estimated density of relevant work per region of topic space, updated as samples come in). Framed this way the whole problem is a budget-constrained POMDP whose actions gather information rather than change the world — which is exactly the class the frameworks in §2 approximate tractably.

One estimate deserves special mention because it powers the stopping rule: **the rediscovery rate.** When expansions keep returning papers you already have, that is capture-recapture evidence (Good–Turing style) that the relevant population in this region is nearly exhausted. It is cheap to track and it converts "have we seen enough?" from vibes into an estimator.

---

## 4. Balancing exploration and exploitation

First, name the thing the question hides: there are **two different objectives** wearing one trenchcoat.

- **Mapping** (Cartographer's input): learn the *shape* of the field. Coverage-driven, diversity-seeking, submodular — exploration-flavored by nature.
- **Prospecting** (Gap Register's input): find the *most promising* gaps/threads. Value-driven, depth-seeking, best-arm-flavored — exploitation by nature.

Most exploration/exploitation confusion dissolves once these are separated, because they dominate different *phases*: early in a run, mapping value dwarfs prospecting value (you can't judge a gap against a field you can't see); later the sign flips. So the balance is not a fixed knob but a schedule, and the principled controls are:

1. **UCB allocation across branches.** Each branch carries (estimated marginal information gain per token, uncertainty). Expand the branch with the best upper bound. Young branches get expanded on optimism; branches that keep disappointing decay naturally. No explicit "prune" operator needed — pruning is just an allocation that never comes.
2. **Marginal value theorem within a branch.** Leave a patch when its local rate of new information drops below the landscape average. This handles the "when to stop digging here" decision that UCB doesn't.
3. **A protected diversity reserve.** A fixed slice of budget (order 10–15%) spent on *out-of-basin* probes — semantic-similarity jumps rather than citation hops, deliberately far from existing branches in topic space. This line item exists to pay for escaping seed anchoring, and it must be protected precisely because UCB will never spend there voluntarily: unexplored regions have no evidence, and most probes will fail. That's the price of insurance against the desert problem. A probe that hits triggers a checkpoint (§5), because finding an unknown adjacent literature is frame-changing news.
4. **Non-stationarity handling.** Branch values are scored against the current Inquiry Frame. When the frame is revised, cached *relevance* judgments are stale even though paper *cards* (factual extractions) are not — which incidentally validates the existing card/interpretation separation (AD-18): facts cache across frame changes; value estimates must not.

---

## 5. Where the human decides, where the system decides

The clean dividing principle: **the human owns the utility function; the system owns the optimization.** Anything that defines *what counts as valuable* is human territory; anything that is arithmetic over an agreed value definition is system territory.

**Human decisions** (all preference-laden, low-frequency, high-leverage):
- The Inquiry Frame and its revisions — this *is* the utility function. (KagamiOS already gates this; the exploration model just gives the gate more work to do.)
- Branch-level direction at checkpoints: bless, kill, or redirect a research thread. Killing a branch encodes taste and outside knowledge the system doesn't have.
- What "interesting" means when a diversity probe surfaces something unexpected — expand the frame or note-and-ignore.
- Final stopping: accepting "the map is good enough" is a judgment about the human's own purposes.

**System decisions** (mechanical, high-frequency, low-stakes-per-decision):
- Which paper to expand next *within* a blessed branch; query reformulation; dedup; shallow-vs-deep read choices; patch-leaving via marginal value; UCB budget allocation across blessed branches.

**When to interrupt** — the important design choice. Checkpoints should be **event-driven, not periodic**. Fixed-interval check-ins produce the worst of both worlds: interruptions when nothing needs deciding, silence when something does. The principled trigger is *expected value of information from asking*: interrupt when the human's answer would plausibly change the system's next allocation. Concretely, that fires on:

1. Two branches competing for significant budget with comparable UCB scores (a genuine fork — the human's taste is the tiebreaker).
2. A diversity probe striking an unknown cluster (potential frame revision).
3. Global marginal gain dropping below threshold (candidate stop — "the field looks mapped; here's the rediscovery-rate evidence").
4. Accumulated evidence contradicting a frame assumption (Skeptic-adjacent: the frame said X matters, the literature keeps saying it doesn't).

Between triggers, the system decides deterministically and logs why — which fits the existing event-log discipline: every allocation decision is an event with its inputs, so the human can audit the tree's growth after the fact instead of supervising it in real time.

---

## 6. The two scenarios

### Scenario 1 — token efficiency is a binding constraint

The problem becomes **fixed-budget pure exploration** (budgeted active search / best-arm identification), and that reframing does real work, because fixed-budget bandits have a canonical, almost embarrassingly simple algorithm — **successive halving**:

> Give every candidate branch a small equal budget. Score them. Kill the bottom half. Double the per-branch budget for survivors. Repeat.

This is the "thin branches" intuition made rigorous — it provably approximates optimal budget allocation without needing good value estimates up front, because early rounds are cheap enough that being wrong about a branch costs little. Everything else follows from cost discipline:

- **Strict cost laddering:** metadata scan → abstract card → deep read, with each rung gating the next. Never pay a rung's cost without the previous rung's evidence. (Most of the budget should die at rung 1.)
- **Caching as strategy, not plumbing:** content-derived paper cards (already built) mean a paper costs its extraction once *ever*, across branches and runs. Under token constraints the cache is the exploration subsidy.
- **Shrink the diversity reserve but never to zero.** ~10% floor. Under budget pressure the temptation is to cut insurance first; the desert-blindness risk is exactly as real at low budget — you just accept detecting deserts without fully mapping them.
- **Accepted losses:** shallower coverage of disconnected communities, hub-biased maps, and gaps ranked with wider error bars. The honest posture is to *report* the unexplored regions as unexplored (the map has labeled terra incognita), not to pretend the mapped part is the field.

### Scenario 2 — token cost ignored, only quality matters

The tempting conclusion — "then just collect everything" — is wrong, and seeing why clarifies the whole design. Remove token cost and the binding constraints become **attention quality, synthesis capacity, and human time**. A 5,000-paper pile doesn't produce a better field map than a well-chosen 300 if the synthesis step drowns; bulk collection just moves the selection problem downstream to where it's harder. What actually changes:

- **Parallel independent explorations.** Run several seed-disjoint explorations of the same frame and compare resulting maps. Divergence between maps is the single best detector of seed anchoring — unaffordable under scenario 1, the first thing to buy under scenario 2. (Redundancy flips from waste to signal: a cluster found by three independent paths is confirmed; a cluster only one path sees is fragile.)
- **Adversarial search.** Dedicated Skeptic-flavored exploration: for every candidate gap, *actively hunt for the paper that already fills it*, using each community's own vocabulary. A gap that survives a well-funded hostile search is a real gap; under scenario 1 you mostly can't afford this and gaps stay "apparent."
- **Systematic desert-crossing.** Deliberate terminology translation between communities — take each cluster's core concepts, generate each adjacent field's likely synonyms, search there. This is Swanson-style literature-based discovery run as a routine subroutine rather than a lucky probe.
- **Saturation-based stopping.** Stop on capture-recapture evidence (rediscovery rate ≈ 1 within every blessed region *and* the diversity probes have gone dry), not on budget exhaustion. Quality mode changes the stopping *criterion*, not just the stopping *time*.
- **What doesn't change:** the tree/graph structure, the human checkpoints, the two-objective schedule, event-driven interrupts. Money buys breadth, redundancy, and adversarial rigor — it does not buy a different conceptual model.

The deepest point of the comparison: **the two scenarios differ in budget *allocation*, not in strategy *shape*.** That is the hallmark of a sound conceptual model — it should degrade gracefully under constraint rather than flip to a different algorithm. "Collect hundreds up front" fails this test (it has no sensible constrained version: it just collects fewer, with the same blindness). Thin-branches-with-diversity-probes passes it.

---

## Summary

- Thin-branches-first is right, upgraded from tree to **guided graph exploration**, with the current batch search demoted to one cheap sensor among four.
- MCTS is the wrong family (game trees, cheap rollouts, crisp rewards); the right family is **information gathering**: active search on graphs, budgeted bandits, Bayesian experimental design, information foraging.
- The landscape is a **partially observed multi-layer graph**; the state is a **belief**, and the rediscovery rate is the cheap estimator that powers principled stopping.
- Exploration/exploitation is really **mapping vs prospecting** on a schedule: UCB across branches, marginal-value-theorem within branches, plus a *protected* diversity reserve that UCB would never fund on its own.
- The human owns the **utility function** (frame, branch blessing, "interesting", final stop) at event-driven checkpoints; the system owns the **optimization** and logs every allocation for after-the-fact audit.
- Token constraints select **successive halving** and cost-laddering; unlimited budget buys **parallel seeds, adversarial gap-testing, and desert-crossing** — but the strategy's shape is invariant across both, which is the strongest evidence it's the right shape.
