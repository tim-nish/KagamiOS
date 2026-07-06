# Scout as a Research Exploration System: Conceptual Architecture

*Answers to the questions in `6_questions.md` (2026-07-04). Continues the discussion in [exploration-strategy.md](exploration-strategy.md); conceptual design only, no implementation.*

The previous document argued that Scout's problem is active search on a partially observed graph, not keyword retrieval. This one takes that seriously: what does Scout look like *as a system* if the graph-exploration model is the foundation rather than an aspiration?

---

## 1. Scout architecture around graph exploration

### The one principle everything else follows from

**Separate inference from decision.** Beliefs about the literature ("paper P exists, makes claim C, cites Q, sits in cluster K") are frame-independent facts. Valuations ("P is worth a deep read *for this investigation*") are frame-dependent utilities applied to those beliefs at decision time. Keep them in different components with different lifetimes, and three hard problems become easy:

- **Frame revision becomes cheap.** When the Inquiry Frame changes, you re-run the utility function over the existing belief — you don't re-explore. The map survives; only the coloring changes.
- **Caching becomes principled.** Facts cache forever (this is what the content-derived paper cards already do, AD-18); valuations cache never. The current design got this boundary right by instinct; the architecture makes it a load-bearing wall.
- **Audit becomes possible.** "Why did Scout go there?" decomposes into "what did it believe?" (checkable against sensor events) and "how did it value that?" (checkable against the frame). Conflating them makes every decision an unexplainable blob.

### The components

Six components, in a loop. Scout stops being a function ("query in, papers out") and becomes a process that runs for the life of an investigation.

**1. The Landscape Model** — the belief store, detailed in §3. The known subgraph plus calibrated beliefs about the unknown remainder. Every other component reads it; only sensor returns and checkpoint outcomes write to it. It is the single shared substrate — components communicate *through the belief*, not through each other, which keeps their contracts thin.

**2. The Sensor Suite** — the four action types from the previous document (query, node expansion, shallow read, deep read), each wrapped as a sensor with a declared cost profile and a declared *bias model* (arXiv over-represents some fields; citation expansion over-represents hubs; keyword search over-represents the frame's own vocabulary). Sensors are deliberately dumb: they observe and report, they never decide. The bias declarations matter because the Landscape Model must correct for them when estimating what the unsampled field looks like — a region that looks empty through a biased sensor may just be invisible to it.

**3. The Appraiser** — the utility side of the inference/decision split. Holds the current frame's value function; scores nodes, regions, and candidate actions for expected information gain per token *given this frame*. Its outputs are explicitly volatile — stamped with the frame version that produced them, and mass-invalidated when the frame moves.

**4. The Frontier** — an explicit, first-class data structure: the set of candidate next actions (expand node X, probe region R, deepen paper P, re-query with vocabulary V), each carrying the Appraiser's score and its uncertainty. This is the "open list" of best-first search, and making it explicit rather than implicit is what makes the whole system inspectable: *the frontier is Scout's to-do list, and rendering it answers "what would Scout do next and why" at any moment.*

**5. The Allocator** — the policy from the previous document, now as a named component: UCB selection over the frontier, marginal-value-theorem patch-leaving within branches, the protected diversity reserve as a separate ring-fenced sub-budget the UCB arithmetic cannot raid. The Allocator is the only component that spends budget, which gives cost accounting a single chokepoint — the same design move FR-25 makes for corpus access.

**6. The Governor** — the checkpoint policy from §2, watching belief deltas and tripwires, deciding when a human needs to enter the loop, and maintaining the agenda of non-urgent questions between checkpoints.

Underneath all six sits the **Chronicle** — the event log, which KagamiOS already has. Every sensor return, every allocation, every appraisal batch, every checkpoint lands there with its inputs. Two consequences worth naming: the Chronicle makes exploration *replayable* (re-run the decision sequence under a revised frame to see where the paths diverge — a powerful tool for understanding what a frame change actually means), and it is the data source for the rediscovery-rate statistics that power stopping.

### The loop

```
        ┌──────────────────────────────────────────────┐
        │                                              ▼
   Sensors ──observe──▶ Landscape Model ──beliefs──▶ Appraiser
                              ▲                        │ scores
                              │                        ▼
   Human ◀──checkpoints── Governor ◀──watches──   Frontier
        │                                              │
        └──frame/blessings──▶ Appraiser          Allocator ──spends──▶ Sensors
```

Sense → update belief → appraise → rank frontier → allocate → sense again; the Governor watches the belief stream and pulls the human in on triggers. Note what is *absent*: there is no "search phase" followed by a "done" state. Exploration is an anytime process that the Governor pauses at checkpoints and the human eventually stops. The Map state consumes a *snapshot* of the Landscape Model (rendered as paper cards plus a terra-incognita report), not a final output — which preserves the existing retrieval boundary: other roles still only ever see processed artifacts; the live belief and the sensors stay inside Scout's charter.

---

## 2. Semi-autonomous exploration

### The framing shift: approve policies, not actions

The reason checkpoint design feels like a lose-lose (too many = nagging, too few = drift) is usually that the system is asking the human to approve *actions*. Actions are the wrong granularity. The model that works — because it's how a PI supervises a grad student — is **standing orders**: the human blesses *policies with envelopes* ("explore these three directions, roughly this budget split, deepen anything matching this description without asking"), and the system executes freely inside the envelope. Interruptions then only happen at envelope *boundaries*, which are rare by construction. The grad student doesn't ask permission to read a paper; they come back when a direction dies, a budget runs out, or something weird turns up.

### The decision criterion: expected value of asking

For everything inside an envelope, there is a single principled interrupt test — the expected value of information applied to the *human's answer*:

> Interrupt iff P(the answer changes the next allocation) × (impact of that change) > (cost of the interruption).

Each factor does real work. If every plausible answer leads to the same next action, asking is pure cost — don't ask, log the decision, move on. If the answer matters but the stakes are one shallow read, don't ask. If the answer matters and the stakes are a branch's whole budget, ask. This one inequality replaces every ad-hoc "should we check in here?" debate, and it explains *why* the four triggers from the previous document are the right ones — comparable-UCB budget forks, diversity-probe strikes, global saturation, and tripwire violations are exactly the events where the inequality flips.

### Three mechanisms that reduce interruptions without adding drift risk

**Tripwires — the frame as falsifiable predictions.** At frame time, the human's assumptions are written down as checkable expectations: "community X will have addressed Y," "this area is mostly post-2020," "these two literatures don't talk to each other." Exploration then *tests* the frame continuously as a side effect. A tripped wire is a high-quality interrupt — it means the world disagrees with the human's model, which is precisely the news a researcher wants immediately. Tripwires convert vague "keep me informed" anxiety into a finite contract, and they are the main defense against the fully-autonomous failure mode (following a wrong direction confidently) *without* adding a single scheduled check-in.

**The agenda — batching the non-urgent.** Most questions worth asking are not worth asking *now*. The Governor accumulates them and presents a decision-ready brief at natural boundaries: each item with a recommendation, the evidence, and — critically — *what changes under each possible answer*, so the human decides in seconds rather than re-deriving context. Interrupt quality is the metric to optimize, not interrupt count: five crisp forced-choice decisions at one sitting cost less attention than two vague "how's this looking?" pings.

**Asynchronous audit with cheap reversal.** Because the Chronicle records every allocation with its inputs, and because the belief/valuation split makes re-scoring cheap, the human can review *after the fact* and issue corrections — "you overweighted that cluster; here's why" — which the Appraiser absorbs as a value-model update (see §3). Most system decisions are thereby *provisionally* autonomous rather than finally autonomous: wrong ones waste some budget but are recoverable, which is what makes delegating them safe. This is the deep reason the reversible/preference-laden taxonomy from the previous document works: reversibility isn't a property decisions have on their own — **the architecture manufactures reversibility**, and every decision it makes reversible is a decision the human no longer needs to gate.

### The resulting division

Always human: the frame and its revisions; the standing orders (branch blessings, budget envelopes, the definition of "interesting"); responses to tripwires and probe strikes; the final stop. Always system: everything inside a blessed envelope — next-node selection, query reformulation, shallow/deep escalation, patch-leaving, intra-envelope reallocation — every one of it logged, every one of it re-scorable. The boundary is not a list of decision types; it is the envelope edge, and the human draws the envelopes.

---

## 3. The internal belief state

### What it contains — five layers

**Layer 1: The observed graph.** Papers as nodes with per-node *processing depth* (known-to-exist → carded → deep-read); typed edges (citation, authorship, venue, semantic similarity); cluster assignments with membership confidence. This is the map's terrain — pure fact, frame-independent, cacheable forever.

**Layer 2: Valuations.** Per-node and per-region relevance *posteriors* — distributions, not point scores, because the spread is what UCB allocation consumes; a paper that is "0.5 relevant, certainly" and one that is "0.5 relevant, could be 0.1 or 0.9" demand opposite treatment (ignore the first, probe the second). Stamped with frame version; bulk-invalidated on frame change.

**Layer 3: Beliefs about the unobserved.** The layer that makes it a belief state rather than a database, and the part the current Scout entirely lacks. Estimated density of relevant work per region of topic space, corrected for sensor bias; per-region saturation statistics from rediscovery rates (Good–Turing: the rate of *new* discoveries per sample estimates the unseen mass); and a **terra incognita registry** — explicitly represented unexplored regions, each with why it's suspected to exist (a semantic direction no branch has entered, a community citing into our clusters that we've never sampled, a tripwire prediction not yet tested) and a rough probe cost. The registry is what lets Scout say the most epistemically important sentence in its repertoire: *"here is what I know I haven't looked at"* — turning unknown-unknowns into known-unknowns is arguably Scout's real product.

**Layer 4: Meta-beliefs.** Per-sensor reliability and bias estimates, updated by cross-validation between sensors (when semantic search finds a cluster that citation expansion never reached, that measures citation expansion's blindness). Per-branch gain-rate histories — the marginal value theorem's inputs. And the Appraiser's own *calibration record* against human checkpoint verdicts: when the human keeps demoting papers the Appraiser scored highly, that residual is itself evidence — see evolution, below.

**Layer 5: The tripwires.** The frame's assumptions as live, falsifiable predictions with their current status (untested / supported / tension / tripped). This layer is the hinge between exploration and frame revision.

### How it evolves

Every sensor return updates Layers 1 and 3 (new facts; revised density and saturation estimates — including from *duplicates*, which carry no new facts but real information: rediscovery is saturation evidence). The Appraiser refreshes Layer 2 lazily, on frame changes and on demand. But the highest-value evidence stream is the cheapest one to overlook: **checkpoint outcomes**. When a human blesses, kills, or redirects, the correct update is not just to the decided branch — it is to the *value model* (Layer 4 calibration). A human demotion of a highly-scored cluster teaches the Appraiser what the frame's words actually mean to this researcher, and that generalizes to every future appraisal. This is preference learning, and it is the difference between a system the human steers forever and one that needs less steering every session. A checkpoint answer that only affects the question asked was mostly wasted.

**On frame revision**, the layers decouple exactly as designed: Layer 1 untouched, Layer 2 invalidated and recomputed, Layer 3's densities re-colored (the *relevant* density changes even though the underlying field didn't), Layer 5 rewritten with fresh tripwires. Re-framing costs an appraisal pass, not an exploration pass — this cheapness is the architecture's single biggest payoff, because it removes the strongest hidden pressure in research tooling: the sunk-cost pressure to keep a stale frame *because re-exploring is expensive*.

### How it drives decisions

Each downstream decision reads a specific slice: **allocation** reads Layer 2 posteriors plus Layer 4 gain rates (UCB needs both the mean and the spread); **stopping** reads Layer 3 saturation plus the state of the terra-incognita registry — the honest stopping claim is "blessed regions saturated, *and* the remaining unexplored regions are enumerated, priced, and declined," which is a fundamentally stronger statement than "the budget ran out"; **frame-revision proposals** read Layer 5 — accumulated tripwire tension is quantified pressure on the frame, surfaced with evidence rather than as a vibe; **checkpoint triggers** read belief *deltas* — the Governor watches for large jumps (a probe strike is precisely a large sudden update to Layer 3), which is what makes interrupts event-driven at the mechanism level rather than by convention.

One requirement binds all of this: **the belief must be renderable.** A map artifact a human can actually read — clusters, branch trajectories, saturation shading, terra incognita marked as such, tripwire status. Not as reporting garnish: the rendered belief is the *medium of the checkpoint conversation*. The human corrects the map ("this cluster is one thing, not two"; "this desert is worth a probe"), and map-corrections are exactly the value-model updates Layer 4 wants. An unrenderable belief state can't be supervised, and an unsupervisable Scout can't be semi-autonomous — belief transparency is not a feature; it is what makes §2 possible at all.

---

## 4. Additional principles

Six principles not yet on the table that belong in a from-scratch design, ordered roughly by how much they'd change the system.

**Bayesian surprise as the universal currency.** The previous documents said "information gain per token" without committing to what *information* means. Commit: value observations by how much they *move the belief* (KL divergence between prior and posterior — Itti & Baldi's "Bayesian surprise," the same quantity behind curiosity-driven RL). The consequences are counterintuitive and correct: the twentieth confirming paper in a mapped cluster is nearly worthless however individually excellent; a mediocre workshop paper that *contradicts* the cluster's assumed consensus is precious; a probe that finds genuine emptiness where density was expected is a *positive-value* result. Surprise-valuation automatically produces diminishing returns within patches (deriving the marginal value theorem instead of bolting it on) and automatically prizes anomalies — which, per Kuhn, is where fields actually turn.

**Gaps are claims, and absence of evidence must be earned.** A gap register entry is a *negative existence claim* — "no one has done X" — and the belief state must distinguish three states that current tooling collapses: *searched-and-absent* (with the search effort quantified), *unsearched* (terra incognita), and *searched-through-a-biased-sensor* (absence not yet meaningful). A gap's confidence should be, roughly, the amount of hostile search it has survived — searched for under multiple communities' vocabularies, through multiple sensors, and not found. This gives the Skeptic role a precise question to ask of any gap: *how hard did you try to kill this?* — and gives Scout a standard for when a gap is ready to leave the register.

**Adversarial testing of the belief, not just the artifacts.** KagamiOS's Skeptic attacks framings, clusterings, and gaps — outputs. The belief state itself accumulates biases upstream of every output: seed anchoring in Layer 1's shape, frame-vocabulary contamination in Layer 2, sensor blind spots hiding in Layer 3's "empty" regions. A belief-level red team asks structural questions — *which Layer-1 regions exist only because of where we started? which Layer-3 emptiness has actually been tested against an unbiased sensor? which cluster boundary is an artifact of one provider's coverage?* — and its findings are probe requests, not prose. Attacking the belief catches distortions before they propagate into every artifact built on top; attacking artifacts catches them one artifact at a time, after the damage.

**Compression as the measure of understanding.** What makes a field map *good*? The MDL answer: a good map is a short description of the literature that still predicts it — name the clusters and a stranger can guess where papers fall and roughly what they say. This yields a non-arbitrary criterion for cluster granularity (split while splitting keeps buying description-length; stop when it stops), a definition of a landmark paper (one that materially shortens its cluster's description), and a signal shared with surprise-valuation: a paper the current map compresses badly is either mis-clustered or genuinely novel, and both readings demand attention. This principle is really Cartographer's, but Scout's exploration should *feed* it — sampling to reduce description length is a coverage objective with teeth.

**The graph has a time axis — respect it.** Scientometrics facts with design consequences: citation signal lags years, so recent work is systematically under-signaled exactly where a gap-hunting system most needs signal — recency demands its own appraisal treatment (semantic and author-trajectory evidence substituting for the citations that don't exist yet). "Sleeping beauties" (work ignored for a decade, then foundational) are the highest-value single finds available to a system like this, and they are *invisible to citation-following by definition* — one more independent argument for the semantic-jump diversity reserve. And a cluster's *velocity* (growing, mature, abandoned) changes a gap's meaning entirely: a hole in an accelerating field is an opportunity; the same hole in an abandoned field is usually a tombstone — someone found out why not, and the reason didn't get published. Layer 1 should carry temporal structure as a first-class feature, not as metadata.

**Hold multiple maps for as long as possible.** The single largest epistemic risk in the whole pipeline is premature crystallization: the first plausible clustering becomes *the* map, every subsequent appraisal is scored against it, and confirmation compounds silently. The belief state should maintain *competing* structural hypotheses — plural clusterings, plural frame-interpretations — for as long as evidence leaves them live, allocating occasional probes specifically at observations that *discriminate* between them (the experimental-design view: the most informative probe is the one the rival maps disagree about most). KagamiOS's FR-26 already demands Cartographer produce structurally different clusterings; this principle extends that pluralism backwards into exploration itself, where it changes which papers get sampled — and it is the cheap, single-run form of what the previous document's parallel seed-disjoint explorations buy expensively.

### If designing Scout from scratch: the essentials

1. **Inference/decision separation** — frame-independent facts, frame-dependent valuations, different lifetimes. The foundation everything above stands on.
2. **Surprise per token as the objective** — one currency for allocation, patch-leaving, and stopping alike.
3. **Explicit ignorance** — terra incognita and sensor bias represented as first-class belief, so "we didn't look there" is always a statement the system can make, priced.
4. **Manufactured reversibility** — chronicle + re-scorable beliefs make most decisions cheap to undo, and every reversible decision is one the human needn't gate; this, not clever checkpoint placement, is what makes semi-autonomy safe.
5. **Checkpoints as training data** — every human verdict updates the value model, not just the decided question; the system needs less steering each session or the human-in-the-loop design has failed.
6. **A renderable belief** — the map artifact is the medium of supervision; whatever cannot be rendered cannot be corrected, and whatever cannot be corrected should not be trusted.
