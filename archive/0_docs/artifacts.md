# KagamiOS — Artifact Catalog

Artifacts are the ground truth of a project (Principle P1); states are a view over them (`state_machine.md` §3). This catalog defines each artifact's purpose, producer, consumers, and a minimal schema sketch. Schemas are deliberately skeletal (Principle P9): fields are added only when dogfooding demonstrates the need.

## Common metadata

Every artifact is a Markdown file with frontmatter:

```yaml
id: <slug>
type: <artifact type>
status: draft | reviewed | accepted | stale | superseded
confidence: speculation | supported | contested | refuted   # where applicable
depends_on: [<artifact ids>]
decided_by: human | ai-drafted/human-reviewed               # provenance of the judgment
created / updated: <dates>
```

**Lifecycle.** `draft` (usually AI-written) → `reviewed` (human read it, commented) → `accepted` (human signed off; this is a gate). When any artifact in `depends_on` changes after acceptance, status flips to `stale` — flagged for human re-review, never auto-regenerated or auto-cleared (P7). `superseded` points to the replacement, and is never deleted: the trail of abandoned versions *is* the reasoning trace (`vision.md`, Reframe 1).

---

## Portfolio-layer artifacts

### Intuition Note
The raw starting point; capture must cost under a minute or intuitions will not be captured.
- **Body:** the intuition in the researcher's own words; where it came from; free-form.
- **Anti-requirement:** no mandatory structure. Structure at capture time kills capture.

### Triage Memo
A minutes-scale screen before an idea earns real time. The questions are the **Heilmeier Catechism**, compressed: What are you trying to do? How is it done today and what are the limits? What's new in your approach and why might it succeed? Who cares? What does a first test cost?
- **AI drafts** answers from the Intuition Note plus a shallow literature pass; **human writes** the verdict.
- **Fields:** `verdict: pursue | park | drop` (human-only, P3), `revival_conditions` (if parked).

### Kill Memo
The death certificate — a first-class product, not cleanup (P10).
- **Fields:** what was believed; what killed it (evidence link); what was learned; `revival_conditions`; salvageable pieces (spawned Intuition Notes).

---

## Project-layer artifacts

### Question Hierarchy *(Frame)*
The root research question, subquestions, and the assumptions under each — replacing the founding pipeline's vague Idea/Questions/Targets triple.
- **Per question:** the question; why an answer would matter; what shape an answer would take; known assumptions.
- **Validation:** the AI critic attacks each question — already answered? unanswerable? uninteresting if answered?

### Survey Corpus *(Survey, continuous)*
Papers with structured annotations: relevance to which RQ, one-line contribution, claimed vs. demonstrated results, extracted limitations. Plus a monitoring config (queries, venues, authors to watch). Alerts from monitoring are what mark downstream artifacts stale.

### Landscape Map *(Survey)*
The synthesized view: taxonomy of approaches, active groups, benchmark/dataset inventory, trend directions. This — not the corpus — is what Position consumes.

### Historical Narrative *(Survey, optional)*
How the field got here; produced on demand only. Demoted from a pipeline stage per `state_machine.md` §1.2.

### Gap Register *(Position)*
Candidate gaps, each forced through the adversarial screen (P4). Per gap:
- statement of the gap; evidence of absence (what was searched, not just "I didn't find it");
- **`why_does_this_gap_exist`** — mandatory: `hard | uninteresting | impossible | recently_filled | genuinely_open`, with argument. A gap register entry without this field is invalid by construction;
- who is closest to filling it; `taken_by_us: yes/no` (human, P3).

### Hypothesis Card *(Hypothesize)* — plural, competing (P5)
- **Fields:** claim (one line, **human-authored**, P3); mechanism (why it would be true); competing alternatives (links to sibling cards); `falsified_by` — the concrete observation that would kill it; cheapest discriminating test; `confidence` (updated across the project — the card's confidence history is the belief-revision trace).

### Paper Skeleton *(created at Hypothesize, lives forever — P8)*
Section outline with the intended claim of each section; grows from bullet points to prose across the whole project. Holes in the skeleton are the project's to-do list.

### Pilot Report *(Probe)*
Deliberately scrappy: what was tried (timeboxed), what happened, cost estimate for the real thing, `verdict: kill | pivot | proceed` (human, P3). A "kill" verdict here is a cheap success.

### Experiment Design *(Design)* — preregistration-style
- **Fields:** hypotheses discriminated (must reference ≥1 card, ideally ≥2 — P5); baselines and why these; metrics; ablations; **success/failure criteria written ex ante**; implementation plan (data, compute, code layout); risks; reviewer red-team notes ("what will Reviewer 2 demand?").
- The ex-ante criteria are the anti-self-deception mechanism: they are signed off before results exist and diffed against at Interpret.

### Run Log *(Execute)*
The lab notebook: per-run record (config, code version, data version, result pointer, anomalies), and **deviations from the Experiment Design, each logged with a reason**. Mostly AI/tooling-maintained; the human logs judgment calls.

### Interpretation Memo *(Interpret)*
What the results mean — the artifact where self-deception is fought.
- **Fields:** results vs. ex-ante criteria (a diff, not a narrative); the preferred explanation; **alternative explanations including boring ones** (bug, data leakage, seed variance, baseline mistuning) with how each was addressed; updated confidence per Hypothesis Card; verdict — which loop-back transition, if any.

### Claim Graph *(Interpret → Communicate)*
Claims linked to evidence (runs, papers, memos), each with human-assigned strength (P3). At Communicate, every assertion in the draft must trace to a claim-graph edge; unsupported assertions render as visible holes. This is the mechanism behind success criterion 4 in `vision.md`.

### Research Decision Record *(any state)*
The ADR analogue: context, options considered, decision, rationale, what would reverse it. Written at every gate and every loop-back transition. RDRs are the primary answer to "why did we not do X?" — the highest-value query against a resumed project.

---

## Consumption map

| Artifact | Produced in | Consumed by |
|---|---|---|
| Intuition Note | capture | Triage |
| Triage Memo | Triage | portfolio decisions; Frame |
| Question Hierarchy | Frame | Survey, Position |
| Survey Corpus / Landscape Map | Survey | Position; staleness alerts everywhere |
| Gap Register | Position | Hypothesize |
| Hypothesis Cards | Hypothesize | Probe, Design, Interpret |
| Paper Skeleton | Hypothesize→ | every later state; Communicate |
| Pilot Report | Probe | Design; portfolio (kill) |
| Experiment Design | Design | Execute, Interpret |
| Run Log | Execute | Interpret |
| Interpretation Memo | Interpret | Communicate; loop-backs |
| Claim Graph | Interpret | Communicate, Review |
| RDRs / Kill Memos | anywhere | future selves, collaborators, agents |
