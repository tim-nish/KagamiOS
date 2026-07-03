# Runtime Review 1 — I/O Contracts

**Question:** Are the runtime contracts precise enough for implementation? Per artifact: inputs, outputs, minimal schema, update rules, identity, dependency rules, versioning, summary blocks, retrieval boundaries. What is already sufficient; what is still ambiguous?

**Verdict in one paragraph.** The baseline is unusually precise *at the conceptual layer* — better than most design documents that reach implementation. What it consistently does is *assert* runtime properties without defining the machinery that provides them: the kernel diffs drafts against schemas that exist only as prose; staleness pins nothing to versions; human-only fields have no enforcement; "the project is in Deepen" is called a derived fact but the derivation is never given. None of these gaps requires conceptual change — each must-change below mechanizes something the baseline already claims. That is the finding in one sentence: **the design is complete; the contracts are not.**

---

## 1. What is already sufficiently specified *(Do not change)*

Audited field by field against the checklist in `4_questions.md`:

| Contract element | Where | Status |
|---|---|---|
| Artifact inventory & purpose | `artifacts.md` §2 | Sufficient — each artifact has inputs, producing state, prevented failure |
| Status lifecycle | `artifacts.md` §1 (`draft → reviewed → accepted`, plus `stale / superseded / provisional`) | Sufficient as a state set; transition *authority* is clear (acceptance is human) |
| Dependency direction | `depends_on`, `elicited_from` | Sufficient in direction; **insufficient in binding** (see §3) |
| Question card & ledger schemas | `elicitation.md` §4–5 | Sufficient — the most implementation-ready schemas in the baseline |
| Consumption map | `artifacts.md` §4 (+ M1's read-set column, assumed) | Sufficient |
| Retrieval boundaries | M1 (assumed incorporated) | Sufficient given M1 |
| Summary blocks | M1 (assumed) | Sufficient given M1; the *lifecycle* of summaries lands in review 2 (S11) |
| **Substrate: Markdown + frontmatter** | `artifacts.md` §1 | **Do not change (D7).** Files are inspectable, diffable, git-versionable, and directly human-editable — and review-is-elicitation (`elicitation.md` §2) *requires* direct human editing of the ground truth. Any proposal to move ground truth into a database should be declined; databases in this system are derived views (analytics store, entity registry index), rebuildable from the files. |

## 2. M4 (Must change) — the machine-readable schema registry

**Why necessary.** `elicitation.md` §1: unknowns are "unfilled fields, unresolved branches, unvalidated assumptions" defined by "the artifact's schema and the current evidence"; §2's ATTEMPT step "enumerate[s] remaining unknowns." This is the engine of the entire system, and it is a *diff between a draft and a schema* — which means the schema must be a machine-readable object, not four prose bullet points in `artifacts.md`. Separately, P3 declares fields "the AI cannot write" and E7 requires "human-authored fields … visually and structurally distinct"; without per-field metadata there is nothing for a runtime to enforce, and the constitutive triad is protected by good intentions.

**The contract.** One schema file per artifact type (YAML, versioned like everything else), each field declaring:

```yaml
field: scope                       # per cluster, in field-map
type: enum [deep, background, out]
profile: minimal                   # minimal | full  → S8's minimal-run profile becomes machine-checkable
author: human                      # ai | human | ai-drafted-human-confirmed  → P3/E7 enforcement
unknown_class_hint: human-only     # computable | human-only | deferrable  → seeds TRIAGE (kernel may override with reasons)
leverage: [L2, L4]                 # links the field to the question-rent taxonomy of elicitation.md §3
in_summary: true                   # M1: whether this field surfaces in the artifact's summary block
```

Two runtime guards come with it, both enforcing existing principles rather than adding new ones:

1. **Write-guard:** the artifact store rejects AI writes to `author: human` fields. The triad becomes a mechanism.
2. **Human-edit preservation:** when a human edits an AI-drafted span (review-is-elicitation), the span's effective author class flips to `human-confirmed`; subsequent repair (M2) may not overwrite it silently — repair *proposes a diff* on human-touched spans and applies freely elsewhere. Without this rule, lazy regeneration quietly destroys the highest-bandwidth elicitation channel the design has.

**Affects:** `artifacts.md` §1–2 (schemas move from prose to registry; prose remains as rationale), `elicitation.md` §1 (TRIAGE consumes `unknown_class_hint`). **Implementation impact:** moderate — a schema loader plus store-level checks; every artifact writer goes through it. **Conceptual or implementation-only:** implementation-only. Every element above is asserted somewhere in the baseline; M4 gives the assertions a load-bearing form.

## 3. M5 (Must change) — identity, versioning, and addressing

**Why necessary.** The baseline names versions ("field-map-v3", "depth-budget-v1"), promises "superseded artifacts are never deleted — the trail is the reasoning trace," and builds its central mechanism (staleness, P7/E5) on artifacts knowing what they consumed. But it never defines: whether `id` is stable across versions; whether `depends_on: field-map` binds to *whichever version is current* (floating) or *the version actually read* (pinned); or what a "section" is, though M2's sectional repair and per-cluster acceptance both need one. Floating references make staleness undecidable — you cannot know an artifact is stale unless you know which version it consumed.

**The contract.**

- **Stable `id` per artifact; monotonic `version`; immutable versions.** A new revision is a new version of the same `id`; `superseded` is a relation between versions, not artifacts.
- **References pin at consumption time:** `depends_on: [field-map@v3]`, `elicited_from: [q-014@v1]`. Staleness is then a pure computation: *pinned version < current accepted version* ⇒ stale along that edge. This is P7/E5 made decidable.
- **A `current` pointer per id** (latest *accepted* version — drafts are never `current`), so casual readers and the handoff bundle resolve names cheaply.
- **Stable section IDs** within artifacts (frontmatter-registered anchors: `field-map#cluster-3`, `dossier-nCDE#evolution`), giving M2's sectional repair, per-cluster status, M1's partial retrieval, and M6's trace events a common address space. Section IDs survive regeneration; content within them changes.
- **One ID space across subsystems:** artifacts, ledger questions, corpus-cache paper cards, entity-registry entries (if S7 adopted), and trace events all reference the same identifiers. This single decision is what later makes observability (review 3) cheap.

**Affects:** `artifacts.md` §1 (frontmatter gains `version`; references gain pins), `principles.md` P7/E5 (mechanics footnote). **Implementation impact:** moderate — reference resolution and current-pointer maintenance in the artifact store; every consumer resolves through it. **Conceptual or implementation-only:** implementation-only — the baseline already behaves as if this exists; M5 writes it down.

## 4. S9 (Should consider) — the run manifest and the derived-state function

Nothing defines what a *run* is on disk. Needed, one small file per run: run id; the rooting Intuition Note; budget counters; monitoring config; and — the substantive part — the **derived-state function** made explicit. `state_machine.md` §1 says "the project is in Deepen" is "a derived fact" over frontier artifacts, and that different clusters can be in different states, but gives no derivation. A simple specification suffices: *a cluster's state is the earliest state whose exit criteria (state table, §3) it has not met; the run's nominal state is the modal cluster state; gates and generation windows key off per-cluster state, not run state.* Whatever the exact rule, it must be written: generation windows (E6) are enforced *against* this function, so an unspecified function means an unenforceable window. **Affects:** `state_machine.md` §1 §3, new run-level file. Should-consider rather than must only because any reasonable fixed rule works — but one must be fixed.

## 5. Smaller ambiguities, resolved in passing

- **Acceptance granularity.** Exit criteria imply per-section acceptance (per cluster card, per dossier). With M5's section IDs, let `status` live at both levels: sections accept individually; the artifact's status is derived (accepted iff all `profile: minimal` sections accepted). *Folded into M4/M5; no separate ID.*
- **Concurrent writes.** Single researcher; the only real conflict is parallel AI drafting (S14) touching one artifact. Rule: parallel writers own disjoint section IDs (one dossier per worker; one cluster card per worker); human edits always win over queued AI writes. *One paragraph in the M5 contract; not a mechanism.*
- **The handoff bundle format** (DQ7) is a runtime I/O contract too, but the baseline's own lean (bundle = artifact graph + generated two-page brief, tested by the resumption test) is adequate; with S6 the brief is the rendered portfolio. **Do not change** beyond what S6 already recommends.
- **The Question Ledger** needs only what M5 gives everything else (versioned answers, pinned citations — `superseded_by` already anticipates this). Its schema is otherwise the baseline's most buildable. **Do not change.**
