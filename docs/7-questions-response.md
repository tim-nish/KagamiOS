# Response to `7_questions.md`

*Written 2026-07-05. Grounded in the Epic 8 dogfooding evidence
(`_bmad-output/implementation-artifacts/epic-8-evidence/run-2afeef8fb9a9-findings.md`),
the design notebooks (`docs/exploration-strategy.md`,
`docs/scout-conceptual-architecture.md`, `docs/future-scout-redesign.md`), and the
current implementation. Companion to `docs/dogfooding-review.md`.*

---

## Q1 — Is there an existing benchmark for graph-based literature exploration? Should we create one?

**Short answer: partial benchmarks exist for neighboring problems, none for what Scout
actually does. Don't build a public benchmark; build a cheap internal evaluation harness
on top of published systematic reviews.**

What exists (as of my knowledge, early 2026):

- **Systematic-review screening / technology-assisted review**: the CLEF eHealth TAR
  tasks (2017–2019) and the SYNERGY dataset (~26 systematic reviews with full
  include/exclude labels, maintained by the ASReview group). These measure recall of a
  known "included studies" set under screening effort — the closest thing to ground
  truth for literature search that exists.
- **Agentic literature search**: PaSa's AutoScholarQuery/RealScholarQuery, LitSearch
  (2024), and ScholarQABench (OpenScholar, 2024) evaluate LLM agents on scholarly
  retrieval and question answering. Notably, your own dogfooding run's corpus surfaced
  PaSa — the run's topic *was* this question, and its accepted Gap Register is worth
  consulting alongside this answer.
- **Citation recommendation / link prediction** benchmarks exist but measure a different
  task (predict edges, not explore under budget).

None of these measures Scout's actual objective: **coverage and gap-validity of a field
map, per token, on a partially observed graph, under an evolving frame**. The academic
"active search on graphs" literature (Garnett et al.) has evaluation setups but no
standardized public benchmark.

**Should you create one?** Not a public one, and not now. A public benchmark is a
research contribution in its own right (ground truth for "good field map" is genuinely
contested), and Goodhart risk is real: optimizing Scout against a benchmark of *known*
review corpora rewards exactly the vocabulary-following behavior the redesign is trying
to escape. What you should build instead is an **internal harness with two tiers**:

1. **The fixed-corpus golden run** (already exists per AD-27) for harness mechanics and
   regressions — keep it.
2. **Systematic-review replay**: take a published systematic review, give Scout its
   research question as the frame, and measure what fraction of the review's included
   studies Scout rediscovers per token spent. SYNERGY gives you ~26 of these ready-made,
   for free. This is exactly how the snowballing literature (Wohlin) validates itself,
   it exercises the citation-graph sensor directly, and it produces the
   recall-per-token curves the adjudication table needs.

Trade-off to accept: review-replay measures *recall of a known set*, which under-rewards
the diversity probes and gap-finding (the things a review by definition already covered).
Treat it as a floor metric, not the objective — and score gap-validity separately via
the Skeptic's "how hard did you try to kill this gap" standard, which is not
benchmarkable and shouldn't be forced to be.

---

## Q2 — Should the Interviewer move to multiple-choice + optional free text?

**Yes, and the design docs already argue for it without naming it.** The
scout-conceptual-architecture's agenda mechanism specifies decision-ready briefs where
each item carries a recommendation, the evidence, and *what changes under each possible
answer* — that is a multiple-choice question in all but name. "Five crisp forced-choice
decisions at one sitting cost less attention than two vague pings" is the same
principle.

Why it's right beyond cost:

- **Better training data.** Checkpoint outcomes are supposed to feed Appraiser
  calibration (preference learning). A choice among concrete options is a clean label; a
  free-text paragraph is an interpretation problem. Structured answers make the
  "needs less steering every session" goal actually implementable.
- **It forces the system to do its homework.** To offer options, the system must have
  computed the live alternatives and their consequences. A free-text prompt lets the
  system push undigested ambiguity onto the user.

The trade-offs to design around, not reasons to hesitate:

- **The option list is itself a framing.** A wrong option set constrains the user into
  the system's blind spot — the one place free text is irreplaceable. Mitigation:
  options must be generated from the *actual fork* the system faces (the competing
  branches, the real candidate framings), never invented to fill a template; and the
  free-text escape hatch must always be present and first-class, not buried.
- **One state is exempt: Frame.** The Inquiry Frame is the utility function; eliciting
  it through options can only recover preferences the system already knows how to
  represent. Frame creation and frame revision should stay free-text-first (with the
  system proposing candidate phrasings the user can edit, which is different from
  choosing among them).

**Recommendation:** multiple-choice-with-optional-free-text as the Interviewer default
everywhere downstream of the frame; free-text-first in Frame. Each question should carry
its "what changes under each answer" line — if the system can't write that line, the
question fails the EVOI test and shouldn't be asked at all.

---

## Q3 — Can a literature map be reused for future exploration, or regenerated each time?

**Reuse the terrain; regenerate the coloring.** The architecture's foundational split
(frame-independent facts vs frame-dependent valuations) answers this question directly:

- **Always reuse:** paper cards, citation edges, retrieval history — Layer 1 facts.
  These cache forever by design (AD-18), and the cross-run corpus cache already does
  this today: a paper costs its extraction once *ever*. Regenerating these is pure
  waste.
- **Never reuse blindly:** appraisals, cluster *choices*, the Gap Register — anything
  frame-stamped. A new investigation has a new (or evolved) frame, and stale valuations
  are precisely what the appraisal-record probe exists to keep out of the cache.
- **Reuse with care: the map artifact itself.** A previous run's Field Map is a
  *hypothesis*, and the single largest epistemic risk named in the design docs is
  premature crystallization — the first plausible clustering becoming *the* map, with
  every later judgment scored against it. Feeding the old map in as fixed truth
  maximizes that risk.

**Recommendation:** on a returning topic, load the cached facts silently (already
happens), and hand the previous map to Cartographer as **one candidate cut among the
required plural cuts** — FR-26 already forces structurally different alternatives, which
is exactly the right immune response. The old map competes; it doesn't preside. The
Skeptic should get to attack it like any other cut, with one extra question available:
"what has changed in the field since this map was drawn?"

One practical caveat from the dogfooding run: cross-run cache reuse currently collides
with the rediscovery-rate metric (the protocol had to clear the cache purely for metric
hygiene). See Q8 — the metric should count within-run rediscovery only, so reuse and
saturation-signal stop fighting.

---

## Q4 — Do commercial services provide literature exploration graphs? Cost?

**Yes, several — but they solve a different, smaller problem, and they're cheap.**
Approximate pricing as of my knowledge (early 2026; verify current prices):

| Service | What it does | Approx. cost |
|---|---|---|
| Connected Papers | Similarity graph around one seed paper | Free tier (~5 graphs/mo); paid ~$5–10/mo |
| ResearchRabbit | Citation/author networks, collections, alerts | Free |
| Litmaps | Seed-based citation maps, monitoring | Free tier; ~$10–15/mo pro |
| Inciteful | Citation-network graphs, path between papers | Free |
| Open Knowledge Maps | Topic-level visual maps | Free (nonprofit) |
| scite.ai | Citation-context (supporting/contrasting) | ~$20/mo |
| Elicit | LLM-assisted screening/extraction | Free tier; ~$10–12/mo + credits |
| Semantic Scholar API / OpenAlex | Raw graph data | Free |
| Scopus / Web of Science | Curated citation databases | Institutional (thousands/yr) |

Two conclusions follow:

1. **This is not "too dependent on individual interests" to exist — as a
   visualization.** These services prove the citation-neighborhood-around-seeds product
   is buildable and commoditized at ~$0–20/month. What every one of them lacks is what
   KagamiOS is actually building: a *frame* (whose question is this map answering?),
   iterative exploration with a belief about the unexplored, earned negative claims (a
   Gap Register), and human-in-the-loop appraisal with provenance. They are sensors and
   renderers; KagamiOS is an investigation. Your instinct is half right: the *map
   rendering* is commodity; the *investigation* is where individual interest and
   understanding live, and that's the defensible part.
2. **Treat them as potential sensors, not competitors.** The redesign's open question
   #3 (semantic-similarity edges for the diversity reserve) explicitly suggests checking
   provider-side related-paper endpoints before owning an embedding store — Connected
   Papers-style similarity and Semantic Scholar's recommendations API are exactly that.

---

## Q5 — Should the survey rely on ratings/rankings/simple choices instead of free text?

**Yes — your premise is correct, and the dogfooding run just validated it.** The run's
researcher (you) declined to read 9 representative papers mid-run and flagged the binary
`human_read` gate as too heavyweight for early exploration — preferring a rating,
confidence level, or short note. That is this question, encountered in the wild.

The principle that resolves it cleanly: **the user owns the utility function; the system
owns everything else.** A user who starts a survey *because they don't yet understand
the field* cannot be a source of field knowledge — asking them to read papers or write
detailed opinions mid-survey inverts the product's value proposition. What the user
*can* always provide, cheaply and reliably, is preference signal: "this direction, not
that one"; "this cluster feels like one thing, not two"; "3/5, low confidence." And
preference signal is exactly what the architecture needs from them — checkpoint verdicts
as Appraiser training data work *better* when they're structured (see Q2).

The boundary to hold: ratings and choices degrade gracefully everywhere *except* where
the user's own words are the payload —

- **Frame creation/revision** (the utility function itself);
- **Tripwire authoring** (the frame's assumptions as falsifiable predictions);
- **The "interesting?" verdict on a diversity-probe strike** (an option list can't
  anticipate what makes an unexpected finding matter to this researcher).

These are low-frequency, high-leverage moments — a handful per run. Everything
high-frequency (paper-level confirmation, cluster feedback, branch blessing) should be
structured.

**Recommendation:** adopt structured-first as an explicit design principle for the
Interviewer, and make the first concrete application the Deepen exit gate: replace the
binary `human_read` requirement (FR-28) with an actor-checked rating + confidence +
optional note. This fixes the workflow finding and the "field implies an owner, nothing
enforces one" mechanical gap in one change. It needs a change signal since it touches an
exit criterion.

---

## Q6 — Confirm: no phase ever reads an entire paper?

**Confirmed — and currently the system reads even less than you think, which is the
actual problem.** As shipped, no phase reads *any* paper content at all, including
abstracts: `kernel/scout.py:search_corpus` passes raw provider metadata (title, DOI,
source) straight onto the card with no model call, and the dogfooding run confirmed
every content field (`contribution_line`, `key_claims`, …) is always empty. Historian
wrote this run's dossiers from its own background knowledge of famous papers — which
will silently fail on obscure ones.

So the honest answer to "is full-paper reading avoided?" is: yes, but not by design
discipline — by the absence of any reading at all, and that absence is a defect (see
`docs/dogfooding-review.md`, finding 2).

The design intent, which matches your instinct exactly, is the **cost ladder** from
`exploration-strategy.md`: metadata scan → abstract card (shallow read) → deep read,
where each rung's cost is paid only when the previous rung's evidence justifies it, and
*most of the budget should die at rung 1*. Under that design:

- **Abstract-level extraction becomes the default ceiling.** OpenAlex already returns
  abstracts in search responses (`abstract_inverted_index`) — so rung 2 costs one model
  call per new paper, cached forever, with zero extra retrieval.
- **Deep read exists but is rare, gated, and section-limited.** It is the most expensive
  sensor in the suite, spent only by explicit allocation (or human request) on papers
  that survived the cheaper rungs — and "deep read" should mean *the sections the
  question needs* (methods, results, the related-work paragraph that names the gap), not
  the PDF end to end. A full linear read is almost never the highest-information use of
  those tokens.

**Recommendation:** commit to the ladder explicitly: rung 2 (abstract cards) as the
next implementation step, rung 3 (section-limited deep read) as a declared sensor with a
declared cost that only the Allocator or the human can spend. "Never read a whole paper"
is then not a prohibition to remember but a budget structure that makes it the natural
outcome.

---

## Q7 — Scout processes ~200 papers; is reducing that part of the optimization plan?

**Yes, but the plan reduces something more precise than the count: it reduces
*processing depth times paper count*, and it replaces the arbitrary stopping point with
an evidence-based one.** Three distinctions matter:

1. **Knowing a paper exists is nearly free; processing it is not.** 200 metadata records
   are a trivial cost. The prior run's ~200 was expensive because every discovered paper
   got the same (full) treatment — bulk collection "pays full price for its worst
   guesses." Under the cost ladder (Q6), the *known* node count may even grow (citation
   expansion sees more of the graph), while the *carded* count falls and the *deep-read*
   count falls to a handful. Optimizing the known-count down would actually be wrong —
   awareness of the field's extent is what Layer 3 (beliefs about the unobserved) is
   built from.
2. **The discipline is already working.** The Epic 8 run's Scout, under the new charter
   (limit 5–8, capped iterations), made 65 organic lookups — roughly a third of the
   prior run's volume — and still reached the MVP terminal with accepted artifacts.
3. **The right control variable is budget, not paper count.** A paper-count target
   reintroduces the arbitrariness the redesign removes. The intended mechanism is: token
   budgets per state, successive-halving allocation across branches, marginal-value
   patch-leaving within branches, and rediscovery-rate saturation as the stop signal.
   Corpus size then comes out as a *result* — small for a narrow frame, larger for a
   sprawling one — rather than going in as a target.

**Recommendation:** don't set "get under N papers" as a goal. Set per-state token
budgets (the FR-37 budget-checkpoint pattern already exists to hang them on), ship the
cost ladder, and let run 2's metrics show where the spend actually goes. If after that
the corpus is still bloated, the evidence will say which rung is leaking.

---

## Q8 — Distinguish already-explored papers from new ones; reuse and expand previous maps?

**Half of this already exists; the other half is the right long-term direction but
should wait for the adjudication — and there's a cheap middle step.**

**What exists today:** the corpus cache is cross-run and marks papers `reused: true` —
the system already knows, mechanically, which papers any previous run touched (this is
exactly why the dogfooding protocol required clearing the cache: old papers would
pre-register as "seen"). Paper-level explored/new distinction is therefore not an
architecture change; at most it's a rendering change (badge reused papers in artifacts).

**What's missing, in increasing order of cost:**

1. **User-level vs system-level "explored."** The cache knows the *system* saw a paper;
   nothing records whether *you* engaged with it. This is the same actor-attribution gap
   the dogfooding run found three times (`human_read`, appraisals). Fix it once,
   uniformly.
2. **Metric hygiene for reuse.** Rediscovery-rate currently can't distinguish
   "rediscovered within this run" (saturation evidence) from "reused from a prior run"
   (cache economics). Scope the metric to within-run lookups so cross-run reuse stops
   contaminating it — then the cache never needs clearing again, and reuse becomes
   free instead of a confound. Small change, high value.
3. **Map-level reuse** — your actual request. "Expand a previous map from a new
   perspective" is, in the redesign's vocabulary, *a new frame applied to cached Layer 1
   facts* — re-score, don't re-explore. This is literally the architecture's
   headline payoff ("re-framing costs an appraisal pass, not an exploration pass"), so
   the long-term answer is: yes, and the belief-store-split adjudication row is the
   thing that decides when it gets built. The blocker today is that the event log and
   derived state are per-run; facts would need a cross-run identity (the corpus cache
   already has one; maps and edges don't yet).

**Recommendation:** do (1) and (2) with the actor-attribution change signal — cheap, no
architectural impact. For (3), your own instinct ("if this significantly changes the
architecture, we can postpone") is correct: postpone the full mechanism until 2–3 runs
have adjudicated the belief-store split. In the meantime, use the cheap bridge from Q3:
seed a returning-topic run with the prior map as one candidate cut plus the prior
anchors as Scout context — input, not constraint. That captures most of the reuse value
at zero architectural cost, and the runs it produces generate exactly the evidence the
adjudication needs.

---

## Q9 — Checkpoint/resume for dogfooding, to avoid rerunning the whole pipeline?

**Mostly yes, it would be straightforward — because the architecture already made the
expensive commitments — but distinguish three things you might mean, which have very
different costs:**

1. **Resuming an interrupted run: already exists.** Each run persists everything
   (`events.jsonl` as append-only source of truth, versioned artifacts, a state cache
   with `current_state`), and the discovery skill supports "resume run \<id\>." Nothing
   to build.
2. **Not re-paying external retrieval: already exists.** The cross-run corpus cache
   means a rerun over the same topic hits cache for every previously seen paper. Scout's
   provider calls — the slowest external dependency — are largely amortized on the
   second pass. (Model-call tokens for the roles are the remaining cost.)
3. **What you're asking for — fork a run at the stage before a modified component:
   doesn't exist, and is a modest feature, not an architecture change.** The reason it's
   cheap is that the architecture already holds the two commitments that make replay
   safe: the event log is the single source of truth (derived state is replayable from
   it), and state entry is defined by consumption maps (each state declares exactly
   which artifacts it reads). A `kagami run fork --from-state <state>` would: create a
   *new* run directory (never rewrite the parent's log — append-only is sacred), copy
   the parent's artifacts and event prefix up to that state boundary, record the parent
   run id for provenance, and set `current_state`. Re-entering the state then works
   through the normal machinery.

The two real design wrinkles, both manageable:

- **Human decisions in the copied prefix.** Gate approvals and appraisals made before
  the fork point were given against artifacts the modified component may now produce
  differently. Carrying them forward is usually what a dev iteration wants; the fork
  should mark them `inherited` so a reviewer can tell replayed consent from fresh
  consent.
- **Metrics across forks.** Rediscovery-rate and friends must not blend parent and
  child events; the provenance field plus within-run metric scoping (Q8, item 2) covers
  this.

**Recommendation:** file it as a small story ("run fork at state boundaries") — genuinely
straightforward, high dogfooding leverage, and fully aligned with the replayability
commitment the redesign notebook lists as non-negotiable. Until it lands, the cheap
workaround for component-level iteration is: keep the corpus cache warm (retrieval is
then near-free), use the fixed-corpus golden run (AD-27) for harness mechanics, and for
a single downstream component, hand-seed a scratch run with the prior run's artifacts
copied in as inputs. That covers most dev loops today at a fraction of a full-pipeline
token spend.

---

## Cross-cutting recommendation

Six of these nine questions (2, 3, 5, 6, 7, 8) converge on decisions the redesign
notebook already made and the adjudication process is already testing: structured
human input at low frequency, fact/valuation split with facts cached forever, cost
ladder over uniform processing, budgets over paper counts. The direction for KagamiOS is
therefore less "decide these nine things" than "protect the adjudication process that
decides them": fix the broken instruments, run 2–3 clean investigations, and let the
table fire or stay silent. The only items that shouldn't wait for that are the
instrument fixes and the two cheap, evidence-backed changes this run already justified —
abstract-level cards (Q6) and the lightweight Deepen confirmation gate (Q5).
