Your previous analysis was extremely helpful. I'd like to take the discussion one level deeper and think about Scout as a research exploration system rather than a literature search tool.

Based on your graph exploration model, I'd like your thoughts on the following questions.

1. Scout architecture

If Scout were redesigned around graph exploration rather than keyword retrieval, what would an ideal architecture look like?

Rather than focusing on implementation details, please describe the conceptual architecture, the major components, and how they interact throughout an investigation.

2. Semi-autonomous exploration

One of KagamiOS's goals is to keep the researcher involved without requiring constant Human-in-the-Loop intervention.

Too many checkpoints reduce the value of the system, but fully autonomous exploration risks following the wrong direction.

How should Scout make exploration decisions while remaining only semi-autonomous?

What decisions should always remain human, and which decisions can be delegated safely to the system?

Are there principled decision criteria that minimize unnecessary interruptions?

3. Internal belief state

In your previous answer, you suggested that Scout's state should be a belief rather than simply a collection of papers.

What should this internal belief state actually contain?

How should it evolve during exploration?

How should it influence future exploration decisions, branch allocation, stopping decisions, and frame revisions?

4. Additional considerations

Are there other important exploration principles that we have not discussed?

For example, are there concepts from information retrieval, graph theory, cognitive science, reinforcement learning, decision theory, or scientific discovery that should influence Scout's design?

If you were designing Scout today from scratch, knowing everything discussed so far, what additional principles would you consider essential?

As before, please focus on conceptual design and theory rather than implementation.