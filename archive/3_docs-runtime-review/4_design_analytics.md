# Runtime Review 4 — Design Analytics: How KagamiOS Improves Itself

**Question:** Using the runtime traces, how should KagamiOS evaluate itself — identifying unnecessary artifacts, low-value questions, expensive steps, simplification opportunities, better ordering, better retrieval, better token efficiency, better decision quality — so that the system becomes better through accumulated runs?

**Verdict in one paragraph.** The right architecture is a **self-measuring system, never a self-modifying one (D9)**. The traces of review 3 feed periodic, deterministic analytics jobs whose output is a human-read **Design Audit Report (S15)**; the report's proposals are design changes like any other, adopted through review, not applied by the runtime. This is not conservatism for its own sake — it follows from two of the baseline's own findings. First, `bmad_transfer.md` §4.2: throughput-like metrics must never become objectives, and every efficiency metric in this domain is a Goodhart trap for the one thing that matters and is nearly unmeasurable (decision quality). Second, E6 scaled up: a system that tunes its *content* defaults from aggregate researcher behavior homogenizes its researchers — anchoring at the population level. The safe self-improvement loop tunes the process's **form** (what to ask, when, what to load, what to skip) and leaves its **content** (what to suggest) alone.

---

## 1. S15 (Should consider) — the Design Audit Report loop

The mechanism, end to end:

1. **Trigger:** every N runs (or quarterly), deterministic jobs run over the layer-3 corpus (review 3 §4). No LLM required for any core job below; an LLM may *narrate* the report.
2. **Output:** a Design Audit Report — itself an artifact with the standard frontmatter, because the design should eat its own discipline: claims cite trace evidence the way dossiers cite papers.
3. **Consumption:** a human (the design owner) reads it and turns accepted findings into changes to `docs-discovery/` — schema edits (M4 registry), triage-hint changes, read-set adjustments (M1), question-class reclassifications. The runtime never applies a finding directly.
4. **Closure:** each adopted change records which report finding motivated it, so the next report can check whether the change had the predicted effect. This makes the design process itself traceable — the same property the founding `questions.md` wanted for research reasoning, applied reflexively.

**Affects:** a new small process document (or a section in `open_questions.md`'s successor); consumes M6/layer-3. **Why not "must":** the trace (M6) is the unrecoverable part; the report can start as a human running queries. It should still be adopted — an unanalyzed trace corpus is storage, not evidence.

## 2. The analytics jobs, mapped to the question's list

Each row: the signal, the evidence source, and — the column that keeps this honest — the confound to check before acting.

| Target | Signal (layer-2/3 data) | Acts on | Confound / guard |
|---|---|---|---|
| **Unnecessary artifacts** | Artifact types with persistently low downstream reads (retrieval events) *and* low citation from Decisions/handoffs | Demote fields or whole artifacts to `profile: full` — i.e., evidence-driven refinement of S8's minimal-run profile | Humans read artifacts out-of-band (a dossier read on paper leaves no retrieval event); check `human_read`-adjacent evidence before demoting anything E7-related |
| **Low-value questions** | Question classes with high default-acceptance **and** near-zero downstream divergence (the tier-0/1 diff of the counterfactual: would the artifact differ?) across many runs | Reclassify the class's `unknown_class_hint` (M4) from human-only to deferrable — asked never, defaulted silently. The inverse migration also happens: deferrable defaults that researchers keep *revising later* were questions in disguise; promote them | High default-acceptance alone is ambiguous — it also means *the defaults are good*, which is E3 working. Only the conjunction with zero divergence justifies demotion. **Exempt permanently:** the E6 unprimed questions and the P3 triad — their value is constitutive, not statistical, and no acceptance rate demotes them |
| **Expensive steps** | Token ledger by state × operation class; repair-vs-regen ratios; DQ4's extension log joined against candidate-set changes | Dispatch-table (S13) and read-set (M1) adjustments; budget defaults. The DQ4 join is the jewel: after enough runs it answers *"do Deepen extensions ever change the candidate set?"* with data — the baseline explicitly wished for exactly this dataset |
| **Simplification opportunities** | Optional-field fill rates vs. terminal outcomes; states that are pure pass-throughs in some run types (e.g., paper-first entries may consistently trivialize Frame) | Minimal-run profile per entry mode | n=100 with heterogeneous fields and researchers is weak evidence; propose, dogfood, don't assume |
| **Question ordering** | Revision cascades by ask-state: a question class that, when asked early, is frequently revised after Deepen was asked too early; loop-backs preceded by late-surfacing L1/L2 answers were asked too late | Adjust which state each class's cards surface in (`elicitation.md` §3's "typical state" column becomes data-maintained) | Ordering effects are confounded with intuition quality; require the pattern across many runs, not many questions in one run |
| **Retrieval strategy** | Retrieved-but-uncited rate per requester/purpose; summary-then-full-pull rate | Tighten read-sets (M1); thicken or thin summary blocks (`in_summary` flags in M4) | An uncited retrieval isn't always waste — Skeptic reads are *supposed* to mostly find nothing; judge per purpose class |
| **Token efficiency** | Cache hit rates (O5), tier mix (S13), repair pipeline stage yields (S11) | Prefix ordering, tiering table | Paired quality guard mandatory — see §4 |
| **Decision quality** | The only honest sources: DQ9 pre-registered claim falsifications (late-joined, review 3 §4); post-Decided staleness alerts (the landscape was wrong); dissolution speed for dissolved runs; voluntary reuse (criterion 7); provisional-count at Decide as a leading proxy | Everything above is *subordinate* to this row | See §4 — this row is why nothing else may become an objective |

## 3. The population-level anchoring hazard — the form/content rule

A hazard no baseline document names, because it only exists once analytics exist. E6 protects one researcher from one AI's fluent framing. Now consider the aggregate loop: 100 researchers' choices tune the system's defaults → cluster in/out defaults drift toward the majority's taste → menu defaults suggest what people like them chose → the tool leads everyone toward the population mode. That is homogenization — v1's Q3, the baseline's named deep failure — *implemented via the improvement loop*, with each step looking like evidence-driven refinement.

**The rule (part of S15, and worth a line in `principles.md` if adopted):** aggregate data may tune **form** — when a question is asked, how it's batched, what context is loaded, which fields are mandatory, what gets computed deterministically. Aggregate data may never tune **content** — which clusters to include, which gaps matter, which candidates to favor, what any *default answer to a taste question* should be. Content defaults come from *this* run's evidence and *this* researcher's profile only. (S16's content-stripped aggregation enforces this physically: content that never enters the corpus can't tune anything.)

The Researcher Profile is the sanctioned personalization channel and already has its own guard — DQ6's "annotate, never filter" lean, which this review endorses unchanged.

## 4. Anti-Goodhart governance *(Do not change the priority order — D9)*

`bmad_transfer.md` §4.2 already rules that throughput must not be an objective; the analytics loop needs that rule operationalized, because a loop optimizing measurable proxies will sacrifice the unmeasurable target by default:

- **Every efficiency finding ships paired with its quality guard**, and both go in the report: fewer questions is good *only if* override and late-revision rates don't rise; cheaper Deepen is good *only if* provisional-counts at Decide and post-decision staleness don't rise; faster time-to-Decided is good *only if* DQ9 falsifications don't rise. A finding whose guard moved the wrong way is reported as a regression, not a saving.
- **The quality metrics are never optimization targets themselves** — they are few, slow, and n-small (DQ9 falsification takes months; reuse is one bit per researcher per project). They serve as *vetoes* on efficiency changes, which is the one statistical job n=100-with-lag can actually perform.
- **No mechanical adoption.** No threshold auto-reclassifies a question, auto-loosens a gate, or auto-edits a schema. The runtime's only sanctioned analytics consumer remains the human-approved gate-loosening proposal of review 3 §1.

## 5. What self-improvement is sanctioned to accumulate *(summary)*

| Accumulates across runs | Status |
|---|---|
| Researcher Profile (per researcher) | Already in baseline — **do not change** (with DQ6's annotate-never-filter lean) |
| Corpus cache / paper cards; entity registry (S5/S7) | Sanctioned — factual, content-bearing but researcher-local |
| Question-class statistics; read-set/retrieval yields; cost ledgers | Sanctioned — form, feeds S15 |
| Design Audit Reports and their adopted changes | Sanctioned — the improvement loop itself, human-gated |
| Tuned content defaults from other researchers' choices | **Rejected** (§3) |
| Auto-modified prompts, gates, schemas | **Rejected** (D9) |
| **O8 (Optional):** controlled question-form experiments (e.g., confirm-vs-menu variants of the same class, compared on differs-from-default and revision rates) | Legitimate but only meaningful at real scale; a natural third-year idea, not a first-year one |

The end state `4_questions.md` asks for — "KagamiOS itself becomes increasingly better through accumulated Discovery runs" — is achieved, but with the same shape the design gives the researcher's own work: evidence is gathered mechanically, synthesized into reviewable artifacts, and *decided on by a human whose judgment the system is built to inform, not replace*. The Discovery OS improves the way it helps researchers decide: by making the evidence impossible to ignore and the decision impossible to delegate.
