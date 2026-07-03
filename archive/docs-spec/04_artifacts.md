# 04 — Artifacts and Infrastructure

Artifacts are the state (P1): Markdown files with frontmatter, human-editable, git-versionable. **No database is ground truth**; every other store (§3) is derived or append-only infrastructure. Schemas stay skeletal and grow only under demonstrated need (P9); the machine-readable form of every schema lives in the schema registry (`07_runtime.md` §1).

## 1. Common metadata

```yaml
id: <stable slug>                          # never changes across versions
type: <artifact type>
version: 3                                 # monotonic; versions are immutable
status: draft | reviewed | accepted | stale | superseded | provisional
depends_on: [field-map@v3]                 # pinned at consumption time (M5)
elicited_from: [q-014@v1]                  # pinned ledger answers this artifact consumed
decided_by: human | ai-drafted/human-reviewed
summary: |                                 # 5–10 lines; the default representation everywhere (M1);
  ...                                      # regenerated only on acceptance, part of the version
created / updated: <dates>
```

- **Lifecycle:** `draft` (AI-written) → `reviewed` → `accepted` (human gate). Drafts are never `current`; the `current` pointer per id resolves to the latest accepted version. `provisional` marks artifacts built on an applied default the researcher never confirmed. Superseded versions are never deleted — the trail is the reasoning trace.
- **Staleness** propagates along `depends_on` and `elicited_from`: pinned version < current accepted version ⇒ stale on that edge. Marking is eager; repair is lazy, diff-first, sectional (P7, `07_runtime.md` §4).
- **Sections** have stable IDs (`field-map#cluster-3`, `dossier-ncde#evolution`). Status may live per section; an artifact is accepted iff all its minimal-profile sections are accepted. Sections are the unit of repair, partial retrieval, parallel ownership, and trace addressing.
- **Field provenance:** every field carries an author class from its schema (`ai | human | ai-drafted-human-confirmed`). Human edits to AI spans flip the span to human-confirmed; repair may not silently overwrite human-touched spans (`07_runtime.md` §1).

## 2. The catalog

### Intuition Note *(entry)*
The raw starting point; capture under a minute; no mandatory structure. All five entry modes (P11) backfill one. **Prevents:** losing the origin; an unrooted graph.

### Researcher Profile *(cross-project, grows forever)*
Taste, skills, constraints, risk appetite, time horizon — built **incrementally from ledger answers**, never from a form. Frame's constraint answers, Deepen's reading reactions, and Locate's meaningfulness marks deposit here. **Rule: annotate, never filter** — the profile writes fit *notes* on candidates but never removes one. **Consumed by:** Propose, Decide, future runs. **Prevents:** re-asking taste every project; candidates objectively good and subjectively wrong.

### Inquiry Frame *(Frame)*
What the intuition means, bounded. **Fields:** intuition restated; in-scope readings and explicit exclusions; the E6 unprimed hunch (human-authored, timestamped); motivation; hard constraints. **Prevents:** surveying an unbounded field; optimizing a reading the researcher never meant.

### Confidence Checklist *(Frame → Decide)*
The decision written backwards (P8): what the researcher must credibly know before choosing. Entries link to filling traces; unfilled entries are the to-do list; re-scored at every gate; audited at Decide. **Prevents:** premature confidence; endless reading past the point where it changes anything.

### Field Map *(Map)*
The *structure* of the field. **Clusters are topical partitions** — the unit of sharding, dossiers, and scope decisions. **Research groups are social entities** referenced within clusters via the entity registry (§3); a group may span clusters and a cluster typically contains several groups (M3). **Fields per cluster:** name (human-editable — naming is framing); definition; boundary notes; key groups/people (entity refs); recency profile (how fast this cluster moves; how stale its published record runs — S2); `scope: deep | background | out` (human, constitutive); reading priority (human). Plus: inter-cluster relations; venues. Corpus sources include preprints, code repositories, and workshops, not only publications (S2). **Prevents:** depth-first rabbit-holing before the field's shape is known; the in/out taste decision staying implicit.

### Cluster Dossier *(Deepen; one per in-scope topical cluster)*
The deep card for one cluster's research programme, and the system's **shard**: one dossier plus the Field Map fits an agent's working context. **Sections:**
- **Evolution** *(mandatory)* — founding problem, phase shifts, abandoned branches *and why abandoned*, with groups as actors in the narrative. The main defense against proposing directions the field already tried and quietly dropped. (A *global* historical narrative remains deliberately absent.)
- **Representative papers** — the defining set (human-confirmed, L3), each with contribution line, claimed-vs-demonstrated note, `human_read: yes/no` + one-line human reaction (E7). Non-representative papers get one-line summaries only.
- **People & venues** — leading researchers and active groups (entity refs), where the work appears.
- **Frontier** — what the cluster is trying to do right now, weighted by the recency profile.
**Prevents:** representativeness decided silently by a ranking function; the researcher "knowing" a cluster only through summaries.

### Landscape Synthesis *(Synthesize)*
The *dynamics* across clusters, computable from accepted dossiers: competing-approaches matrix (who competes with whom, on which axes, who wins where — with the researcher's confirmed weightings); trend directions; the solved/open table where every "open" entry carries evidence of openness (what was searched), never mere absence. **Prevents:** gap-hunting from raw dossiers; "open problems" that are just un-searched problems.

### Gap Register *(Locate)*
Per gap: statement; evidence of absence; the mandatory adversarial screen **`why_does_this_gap_exist`**: `hard | uninteresting | impossible | recently_filled | genuinely_open`, with argument; who is closest to filling it; `meaningful_to_me: meaningful | real-but-not-mine | suspicious` (human-only — constitutive). **Evidence types** include literature evidence and the bounded **micro-probe** (S3): a researcher-executed feasibility poke, hard-bounded to hours, recorded as evidence for exactly one field, producing no artifacts of its own. **Prevents:** LLM gap-slop; pursuing gaps that are real but not yours; `hard`/`impossible` verdicts resting on reading alone when an hour of poking would settle them.

### Candidate Direction *(Propose; plural, competing)*
The bridge between landscape and choice. Generated only after the generation window opens (E6 — timing constraint only). **Fields:** the direction, question-shaped, one line; **supporting evidence** — Gap Register links *and/or* Landscape Synthesis links (cross-cluster transplants, capability-overhang/why-now candidates — S1), every candidate citing its evidence; defining papers (must be `human_read`); competing sibling candidates (P5); requirements (skills/data/compute, checked against the Researcher Profile); fit notes (annotations, never filters); why-now argument; red-team notes ("the strongest reason this is a mistake"); `origin: ai-generated | human-added`; **`disposition`** *(filled at Decide)*: `selected | parked (revival conditions) | rejected (rejection_reason)` (S6). **Prevents:** single-option advocacy; gap-only tunnel vision; choices made against imagined requirements.

### Direction Decision *(Decide — terminal)*
The product. Human-signed. **Structured as a portfolio** (S6):
1. **Selected** direction(s), with the human-authored **"why this over the others"** comparison and the diff against the unprimed lean (E6 audit — did the tool lead or follow?).
2. **Parked** candidates with revival conditions (fed to monitoring).
3. **Rejected** candidates with `rejection_reason` (harvested largely from red-team notes and the comparison table).
4. **Spawned** future opportunities: gaps marked `real-but-not-mine` and worthwhile `premature_ideas` quarantine content, emitted as new Intuition Notes.
Plus: the Confidence Checklist audit (each entry → trace link); **`probe_before_commit`** flags marking load-bearing feasibility claims that rest on reading alone (S3); **pre-registered falsifiable claims** about the landscape ("no published method does X under constraint Y") for the robustness test (`08_observability.md` §3); the **handoff bundle** manifest — the artifact graph plus a generated two-page brief (the rendered portfolio), sufficient for any downstream process to proceed without re-interviewing the researcher. Post-terminal, monitoring can mark this artifact stale.

### Dissolution Memo *(any state — terminal)*
The discovery-scale kill memo (P10): what the intuition was; what dissolved it (evidence links); what was learned; revival conditions; salvaged fragments (spawned Intuition Notes). Reaching this in days is a successful run.

## 3. Infrastructure layer *(not researcher-facing documents; same ID space as artifacts — M5)*

| Store | Contents | Nature |
|---|---|---|
| **Question Ledger** | every question, answer, applied default, and revision (`05_elicitation.md` §5) | append-only; staleness source for `elicited_from`; the run's reasoning trace |
| **Corpus cache** (S5) | one **paper card** per paper, computed once on first contact: bibliographic identity, one-line contribution, method class, evidence type, key claims with section citations. Artifacts cite paper IDs; no paper is ever re-summarized | derived, cross-run, warm-startable |
| **Entity registry** (S7) | typed entities — `paper`, `person`, `group`, `venue` — with stable IDs and typed *relations* (person→group, paper→cluster many-to-many, group→venue). **No levels, no containment tree**; interpretive structure (research lines, evolution) stays in human-reviewed artifacts | derived, cross-run |
| **Run manifest** (S9) | run id, rooting Intuition Note, derived state per cluster, budget counters, monitoring config | per-run, small |
| **Run event log** (M6) | append-only JSONL trace of every LLM call, retrieval, artifact event, question event, human edit, frontier decision, gate, budget, and transition (`08_observability.md` §2) | write-only during a run (P1); local-first; deletable without affecting behavior |

## 4. Consumption map

Resolution column implements the context loading contract (M1); full read-set detail in `07_runtime.md` §3.

| Artifact | Produced in | Consumed by (default resolution) |
|---|---|---|
| Intuition Note | entry | Frame (full) |
| Researcher Profile | continuously | Propose, Decide (full); future runs |
| Inquiry Frame | Frame | Map (full); every question's scope check (summary) |
| Confidence Checklist | Frame | every gate (full); Decide audit (full) |
| Field Map | Map | Deepen (full), Synthesize (full); monitoring (queries) |
| Cluster Dossiers | Deepen | Synthesize (full, accepted only); Propose (summary); Decide handoff (summary) |
| Landscape Synthesis | Synthesize | Locate (full); Propose (full) |
| Gap Register | Locate | Propose (full) |
| Candidate Directions | Propose | Decide (full) |
| Direction Decision | Decide | downstream (bundle); monitoring |
| Dissolution Memo | any | future selves; portfolio of intuitions |
| Question Ledger | whole run | staleness engine; rent audit; the trace |

## 5. The minimal-run profile (S8)

Every schema field is marked `profile: minimal | full` in the schema registry. A **minimal run** — targeting days, not weeks — requires only: Intuition Note; Inquiry Frame (readings, exclusions, unprimed hunch); Field Map (clusters with scope marks; no recency profiles, no venue detail); one Dossier per deep cluster (Evolution + representative papers only); Gap Register (screen + meaningfulness); Candidate cards (direction, evidence, red-team line); Decision (selected + why-over-others). Everything else — synthesis matrix detail, people/venue sections, fit notes, recency profiles — is `full`-profile accretion. Field-level fill rates versus outcomes are tracked across runs to move fields between profiles, through the audit loop (`08_observability.md` §5), never automatically.
