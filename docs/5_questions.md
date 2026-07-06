Now I'd like to discuss the exploration strategy itself.

My original intuition was different from the current Scout behavior.

Rather than collecting hundreds of papers up front, I imagined exploration more like growing a tree.

The process would be something like:

1. Identify a few representative or influential papers.
2. Build several thin research branches from them.
3. Gradually extend only promising branches.
4. Ask the researcher for guidance (or make deterministic decisions) at suitable checkpoints.
5. Expand or prune the search space as evidence accumulates.

I mentioned Monte Carlo Tree Search (MCTS) simply because I know it as a tree-search algorithm, but I'm not attached to it.

I'd like you to think about this as a research problem.

Please discuss:

- Is this "thin branches first" strategy actually a good way to explore scientific literature?
- Is MCTS an appropriate analogy, or is there a better theoretical framework?
- Are there exploration strategies from information retrieval, active learning, Bayesian optimization, search theory, reinforcement learning, graph exploration, or another field that fit this problem better?
- How would you model the literature landscape as a search space?
- How should exploration and exploitation be balanced?
- Where should the human make decisions, and where should the system decide automatically?

Please also compare two scenarios:

1. Token efficiency is an important constraint.
2. Token cost is ignored and only research quality matters.

I'm not asking for implementation ideas yet.
I'm asking for the best conceptual model for navigating a research landscape.