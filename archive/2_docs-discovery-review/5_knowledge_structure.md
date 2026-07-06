# Review 5 — Knowledge Structure: Artifact Graph vs. Explicit Hierarchy

**Question:** The current design is artifact-centered. Would explicitly modeling a hierarchical knowledge structure — Research Area → Community → Research Group → Research Line → Representative Papers — improve KagamiOS, or is the artifact graph the better abstraction?

**Verdict in one paragraph.** Do not make the five-level hierarchy first-class (**D6**): research fields are not trees, a fixed schema pre-decides granularity the baseline deliberately assigns to the human (L2), and an AI-authored ontology as the system's data model is the anchoring hazard the baseline's own DQ3 warns about — promoted from a question-design problem to a database-design problem. But the proposal points at two real deficiencies. First, the baseline genuinely conflates two of the hierarchy's levels — topical *cluster* and social *research group* — in the Cluster Dossier's definition; that is an internal inconsistency and a **must-fix (M3)**. Second, the legitimate benefits the hierarchy would buy (stable references, cross-run reuse, queryability) are available without ontological commitment via a flat **entity registry (S7)**. If the hierarchy is wanted for human consumption, generate it as a *view* (**O3**).

---

## 1. The hierarchy is mostly already present — implicitly, and better

Mapping the proposed levels onto the baseline:

| Proposed level | Baseline location |
|---|---|
| Research Area | Inquiry Frame (in-scope readings, boundaries) |
| Community | Field Map (communities and recurring groups per cluster) |
| Research Group | Field Map "key groups/people"; Dossier "People & venues" |
| Research Line | Dossier Evolution section; Field Map "lineages" |
| Representative Papers | Dossier representative set (`human_read`, L3-confirmed) |

So the question is not whether this information exists — it does — but whether it should be *reified as a tree with fixed levels*. The baseline stores it inside decision-oriented artifacts instead, and that choice is defensible on four grounds.

## 2. Why the explicit hierarchy should be declined *(Do not change — D6)*

1. **Fields are not trees.** Signature kernels sit between the signature community and the GP-kernel community (the baseline's own worked example, q7, is a cross-link: "cluster 3 keeps citing back into GP kernels"). Groups publish across communities; papers found multiple lines; neural CDEs belong simultaneously to a signature lineage and to the neural-ODE lineage that has nothing to do with signatures. A tree forces every such object into exactly one parent; the misfits are not edge cases — in ML they are usually where the interesting directions live (review 1, S1: transplant candidates exist *between* clusters). A graph with typed relations represents this; a hierarchy amputates it.
2. **Fixed levels are a Procrustean bed.** Some discoveries have no meaningful "community" stratum (a young topic is one community); some have no group structure worth modeling (method-defined clusters with diffuse authorship). The baseline instead lets the Field Map's granularity be a *human L2 decision per run* — one of its constitutive taste surfaces (`state_machine.md` §4). A five-level schema pre-answers the very question the design routes to the researcher.
3. **The ontology anchor.** DQ3 already identifies the design's subtlest anchoring problem: "the clustering itself is an AI judgment… the ontology was never theirs." A first-class hierarchy makes this strictly worse: the AI's ontology stops being a reviewable draft artifact and becomes the schema everything else is stored in — contestable in principle, but in practice as hard to revise as any database migration. The baseline's mitigation candidates (two competing clusterings, human naming, Skeptic attacks on the partition) all depend on the partition remaining a cheap, human-editable artifact.
4. **Knowledge-base pull is survey-tool pull.** A hierarchy is coverage-oriented — empty slots ask to be filled ("we haven't characterized the communities of cluster 4 yet"). The artifact graph is decision-oriented — everything must trace to candidate survival (E2). `vision.md` calls the survey pull the strongest implementation gravity; a knowledge hierarchy as the core data model is that pull given a schema.

## 3. M3 (Must change) — the baseline conflates cluster and group

The user's proposed hierarchy separates *Community* from *Research Group*, and checking the baseline against that distinction exposes a real internal inconsistency:

- `artifacts.md` §2 defines the Cluster Dossier as "*(Deepen, one per in-scope cluster)*" but describes it as "the self-contained deep card for **one research group/school**."
- `artifacts.md` §3 answers request #8 with "Research groups → **Yes** — Cluster Dossier (**one per group/school**), clusters enumerated in the Field Map."
- Meanwhile the Field Map defines clusters *topically* (the worked example's clusters — "deep signature architectures," "signature kernels," "log-signature methods & efficiency" — are topics, each containing several groups), and lists "key groups/people" as fields *within* a cluster.

So a dossier is simultaneously one-per-cluster and one-per-group, and a cluster is simultaneously a topic and a school. For the worked example it happens not to matter much ("clusters 1–3 share a small set of recurring groups"); in a larger field it determines the shard count, the budget structure, and what the Evolution section is the evolution *of* (a research programme's intellectual history vs. a lab's output history — different documents).

**Fix (small, textual):** define the **cluster** as the topical unit — the shard, the dossier unit, the L2 surface — and the **group** as a social entity *referenced within* clusters (many-to-many: groups span clusters, clusters contain groups). Rewrite the dossier's one-line description and the §3 verdict row accordingly: research groups are first-class **as entities catalogued in the Field Map and dossiers** (and, with S7, in the entity registry), not as the dossier's unit of decomposition. The Evolution section is the evolution of the cluster's research programme, with groups as actors in it. **Affects:** `artifacts.md` §2 (Cluster Dossier) and §3, `state_machine.md` §3 Deepen row. No mechanism changes.

## 4. S7 (Should consider) — a flat entity registry instead of a hierarchy

The benefits the hierarchy proposal is actually reaching for — stable identity, queryability, reuse — do not require levels. They require *entities*:

- **The gap.** In the baseline, people, groups, venues, and (absent S5) papers exist only as prose inside artifacts. Nothing makes "T. Lyons" in the Field Map, a dossier's People section, and the monitoring config the same object; nothing lets the next run over adjacent territory reuse this run's map of who is where.
- **The fix.** A flat registry of typed entities — `paper`, `person`, `group`, `venue` — with stable IDs and typed *relations* (person→group membership, paper→cluster assignment *many-to-many*, group→venue habits), living beneath the artifact graph as infrastructure, exactly like the Question Ledger. Artifacts mention entities by ID; the registry is cross-run and shared with the corpus cache of S5 (paper cards are its `paper` entities). The monitoring config (`state_machine.md` §6) becomes a query over it rather than a copied list.
- **Why this is not the hierarchy through the back door:** the registry has no levels and asserts no containment. "Research Line," the hierarchy's most interpretive level, is deliberately *excluded* — lines are narrative claims about the literature, and they stay where the baseline puts them, inside human-reviewed Evolution sections. The registry stores what is computable and objective (identity, authorship, citation); the artifacts store what is interpretive and reviewable. That boundary is the same computable/human-only line the elicitation kernel already draws (`elicitation.md` §1), applied to storage.

**Affects:** `artifacts.md` (new infrastructure entry), Researcher Profile (cross-project reuse gets a substrate), monitoring config. **O4 (Optional):** if dogfooding shows Evolution sections repeatedly narrating the same thread, allow a named `research_lines` subsection inside the dossier — named by the human (naming is framing), never a registry entity.

## 5. O3 (Optional) — the hierarchy as a view

Everything needed to *render* Area → Community → Group → Line → Papers exists in the Field Map, dossiers, and (with S7) the registry. For the consumers who think hierarchically — the advisor reading the DQ10 presentation surface, the researcher wanting an orientation poster of the field — generate the hierarchy as a projection, recomputed on demand, owned by no one. A view can be tree-shaped because a view is allowed to lie a little; a data model is not.

## 6. Answer to the question as asked

The artifact graph **is** the better abstraction, and the baseline's reasoning for it (`state_machine.md` §1: graph as memory, loop as engine, states as map) survives this challenge intact — **Do not change (D6)**. The hierarchy proposal earns its keep differently: it exposes one genuine defect (the cluster/group conflation — **M3**, the only must-change this question produces) and motivates one genuine addition (the entity registry — **S7**) that delivers the proposal's practical benefits without its ontological costs.
