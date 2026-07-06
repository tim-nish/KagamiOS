# KagamiOS v2 — Artifact Catalog

The minimal set of artifacts needed before a research direction is selected (request #2), with explicit verdicts on the four candidate first-class concepts (request #8). Artifacts are ground truth (P1); schemas stay skeletal and grow only under demonstrated need (P9). Nine artifacts plus the Question Ledger.

## 1. Common metadata

Every artifact is a Markdown file with frontmatter, inheriting v1's scheme plus one new field:

```yaml
id: <slug>
type: <artifact type>
status: draft | reviewed | accepted | stale | superseded | provisional
depends_on: [<artifact ids>]
elicited_from: [<ledger question ids>]     # NEW — the answers this artifact consumed
decided_by: human | ai-drafted/human-reviewed
created / updated: <dates>
```

**Lifecycle** as in v1: `draft` (AI-written) → `reviewed` → `accepted` (human gate). Staleness propagates along `depends_on` **and** `elicited_from`: revising an answer in the Question Ledger stales every artifact that cited it (E5). `provisional` marks artifacts built on an applied default the researcher never confirmed. Superseded artifacts are never deleted — the trail is the reasoning trace.

## 2. The catalog

### Intuition Note *(entry)*
Unchanged from v1: the raw starting point, capture under a minute, no mandatory structure. All five entry modes (P11: intuition-, paper-, field-, problem-, tool-first) backfill one of these.
- **Prevents:** losing the origin; an unrooted dependency graph.

### Researcher Profile *(cross-project, grows forever)*
The researcher's taste, skills, constraints, risk appetite, and time horizon — built **incrementally from ledger answers**, never from a form. Frame's constraint questions, Deepen's reading reactions, and Locate's meaningfulness marks all deposit here.
- **Fields (all optional, accreting):** interests/anti-interests; skills and tools; constraints (compute, math depth, collaboration, timeline); taste signals (papers loved/bounced-off, with reactions).
- **Consumed by:** Propose (fit-to-profile notes on every candidate); Decide.
- **Prevents:** re-asking the same taste questions every project; candidates that are objectively good and subjectively wrong. No BMAD analogue exists — BMAD models requirements, not the user.

### Inquiry Frame *(Frame)*
What the intuition means, bounded. Replaces v1's Question Hierarchy — at discovery time there is no research question yet; there are *readings of an intuition* and boundaries.
- **Fields:** the intuition restated; in-scope readings (from the Frame menu question) and explicit exclusions; the E6 unprimed hunch (human-authored, timestamped); motivation ("why this pulls at me"); hard constraints.
- **Prevents:** surveying an unbounded field; the system optimizing for a reading of the intuition the researcher never meant.

### Confidence Checklist *(created at Frame, lives until Decide)*
The decision written backwards (P8's heir): what the researcher must credibly know before choosing — communities, evolutions, defining papers read, competitors, why-each-gap-exists, fit and why-now. Entries link to the traces that fill them; unfilled entries are the to-do list; the Decide gate audits it.
- **Prevents:** premature confidence; and the opposite — endless reading past the point where it changes anything (`state_machine.md` §5).

### Field Map *(Map)* — **verdict on "research landscape," part 1: first-class, split in two**
The *structure* of the field: clusters with one-line definitions and boundaries, relations between clusters, communities and recurring groups per cluster, key researchers and lineages, venues. This is the evidence base for the highest-leverage questions in the system (L2/L4) — the clustering the researcher confirms here shapes everything downstream.
- **Fields per cluster:** name (human-editable — naming is framing); definition; boundary notes ("X is here, not in cluster 3 because…"); key groups/people; `scope: deep | background | out` (human, constitutive); reading priority (human).
- **Prevents:** depth-first rabbit-holing before the shape of the field is known; deferring the in/out taste decision until it is implicit and invisible.

### Cluster Dossier *(Deepen, one per in-scope cluster)* — **verdict on "research groups": first-class. Verdict on "historical evolution": first-class, as a mandatory dossier section**
The self-contained deep card for one research group/school. Also the system's **shard** (BMAD sense): sized so one dossier plus the Field Map fits an agent's working context.
- **Sections:**
  - **Evolution** — how this cluster got here: founding problem, phase shifts, abandoned branches *and why abandoned*. v1 demoted the (global) Historical Narrative to optional; the discovery scope **reverses that per cluster** — evolution is the main defense against proposing directions the field already tried and quietly dropped, and against "gaps" that are really graveyards. A global narrative remains unnecessary; per-cluster evolution is mandatory.
  - **Representative papers** — the defining set (human-confirmed, L3), each with contribution line, claimed-vs-demonstrated note, and `human_read: yes/no` + one-line human reaction (E7).
  - **People & venues** — leading researchers, active groups, where the work appears.
  - **Frontier** — what this cluster is trying to do *right now*; recent movement.
- **Prevents:** representativeness decided silently by an AI ranking function; the researcher "knowing" a cluster only through summaries.

### Landscape Synthesis *(Synthesize)* — **verdict on "research landscape," part 2**
The *dynamics* across clusters, computable from accepted dossiers: the competing-approaches matrix (what competes with what, on which axes, who wins where — with the researcher's confirmed weightings); trend directions; the solved/open table where every "open" entry carries evidence of openness (what was searched), not mere absence.
- **Prevents:** gap-hunting straight from raw dossiers; "open problems" that are just un-searched problems.

### Gap Register *(Locate)* — inherited from v1, one field added
Per gap: statement; evidence of absence; the mandatory adversarial screen **`why_does_this_gap_exist`**: `hard | uninteresting | impossible | recently_filled | genuinely_open`, with argument (kept verbatim — it is v1's best mechanism and it lives at the heart of the new scope); who is closest to filling it; **new:** `meaningful_to_me: meaningful | real-but-not-mine | suspicious` (human-only — constitutive gate 2).
- **Prevents:** LLM gap-slop; pursuing gaps that are real but not *yours*.

### Candidate Direction *(Propose)* — **verdict: first-class, plural, competing**
The bridge artifact between landscape and choice. Generated only after the generation window opens (E6) and only from accepted gaps.
- **Fields:** the direction, question-shaped, one line; supporting gaps (register links); defining papers (must be `human_read`); competing sibling candidates (P5-adapted); what pursuing it requires (skills/data/compute — checked against Researcher Profile); fit notes; why-now argument; red-team notes ("the strongest reason this direction is a mistake"); `origin: ai-generated | human-added` (the E6 audit trail).
- **Prevents:** single-option advocacy; direction choices made against imagined rather than stated requirements.

### Direction Decision *(Decide — terminal)*
The product. Human-signed.
- **Fields:** chosen direction(s); **why this over the others** — the written comparison (human-authored); diff against the unprimed lean (E6 audit — did the tool lead or follow?); parked candidates with revival conditions; Confidence Checklist audit (each entry → trace link); the **handoff bundle** manifest (frame, map, relevant dossiers, synthesis, register, candidate cards, ledger) — sufficient for any downstream process to proceed without re-interviewing the researcher.
- Post-terminal: monitoring can mark this artifact stale (`state_machine.md` §6).

### Dissolution Memo *(any state — terminal)*
The discovery-scale Kill Memo (P10): what the intuition was, what dissolved it (evidence links — "mature field," "tried and abandoned 2004–2011, see cluster 2 evolution," "vacuous under scrutiny"), what was learned, revival conditions, salvaged fragments (spawned Intuition Notes). Reaching this in days is a successful run.

### Question Ledger *(infrastructure, whole run)*
Every question, answer, and applied default — schema in `elicitation.md` §5. Technically kernel infrastructure rather than a document the researcher reads, but listed here because it is the staleness source for `elicited_from` and the run's reasoning trace.

*(Not carried over: v1's Research Decision Record. Discovery's decisions are few and localized; the Direction Decision, Dissolution Memo, ledger, and loop-back annotations cover them. Reinstate only if dogfooding shows untraced decisions — P9 cuts both ways.)*

## 3. Request #8, answered in one place

| Concept | First-class? | As |
|---|---|---|
| Research groups | **Yes** | Cluster Dossier (one per group/school), clusters enumerated in the Field Map |
| Historical evolution | **Yes — per cluster** | mandatory Evolution section of each dossier; *global* narrative stays retired (reversal of v1's blanket demotion, scoped) |
| Research landscape | **Yes — split** | Field Map (structure) + Landscape Synthesis (dynamics); merging them hides that one is a human-taste surface (L2/L4) and the other is mostly computable |
| Candidate directions | **Yes** | Candidate Direction cards — plural, competing, gap-rooted, profile-checked |

## 4. Consumption map

| Artifact | Produced in | Consumed by |
|---|---|---|
| Intuition Note | entry | Frame |
| Researcher Profile | continuously | Propose, Decide; future projects |
| Inquiry Frame | Frame | Map; every question's scope check |
| Confidence Checklist | Frame | every gate; Decide audit |
| Field Map | Map | Deepen (budgets), Synthesize; monitoring config |
| Cluster Dossiers | Deepen | Synthesize; Propose (defining papers); handoff |
| Landscape Synthesis | Synthesize | Locate |
| Gap Register | Locate | Propose |
| Candidate Directions | Propose | Decide |
| Direction Decision | Decide | downstream (outside KagamiOS); monitoring |
| Dissolution Memo | any | future selves; portfolio |
| Question Ledger | whole run | staleness engine; rent audit; the trace |
