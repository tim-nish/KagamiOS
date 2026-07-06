# KagamiOS — Open Questions

Unresolved design questions, ranked roughly by how much they could change the design. Each states the question, the tension behind it, and a current lean where one exists. These should be settled by dogfooding (see Q1), not by more design writing.

---

## Q1. What is the smallest version worth dogfooding?

The whole design is unvalidated theory until it runs against a real project, and the Signature-methods investigation is sitting right there as the test case. But which subset to try first? Full artifact catalog + state machine risks process theater (P9); too little tests nothing.

**Lean:** start with only the pieces that have no existing tool: Triage Memo (Heilmeier screen) on 3–5 captured intuitions, Hypothesis Cards with `falsified_by`, Gap Register with `why_does_this_gap_exist`, and RDRs at decisions. Plain Markdown in a repo, no tooling. If those four artifacts pay rent by hand, build tooling; if they don't pay rent by hand, tooling won't save them.

## Q2. How is the process kept from being theater?

The design's own biggest risk (P9). Sub-questions: Which artifacts will be rubber-stamped in practice? Should the system *detect* rubber-stamping (e.g., accepted-without-edits within seconds)? Is a "waiver" mechanism a safety valve or a hole that drains all discipline?

**Lean:** measure during dogfooding — track per-artifact time-spent vs. later-referenced. An artifact that is never re-read after acceptance is a candidate for deletion. No mechanism can substitute for the willingness to delete parts of the design.

## Q3. Does formalization homogenize research taste?

A sharper version of the automation-bias worry (P4): if many researchers run the same gap-enumeration and hypothesis-drafting prompts over the same literature, they converge on the same "obvious" gaps — the system could make its users *more* average precisely where research rewards being unusual. The adversarial framing mitigates but does not obviously eliminate this: a shared critic also homogenizes what survives critique.

**Open:** is there a design that provably pushes toward the tails? (Candidate: AI enumerates and *attacks*; only human-authored additions to the Gap Register may be marked `taken_by_us`. The founding pipeline's implicit answer — AI proposes, human selects — is probably not enough.)

## Q4. How should belief revision be represented?

P5 says uncertainty is a field, but what type? Numeric probabilities invite false precision and are famously miscalibrated even for experts; the current qualitative enum (`speculation | supported | contested | refuted`) may be too coarse to notice drift. Also open: is the confidence *history* (the trace of changes with reasons) actually the valuable object, rather than the current value?

**Lean:** qualitative enum + mandatory one-line reason per change; revisit only if dogfooding shows the enum losing information that mattered.

## Q5. Project-level states vs. artifact-graph purity

`state_machine.md` §3 chose a hybrid, but the balance is unresolved: how strongly should the state view *prescribe*? If the scheduler says "you are in Design" while the researcher is legitimately doing three states at once, does the view help or nag? Where exactly is the line between "narrative spine" and "false linearity re-imported through the UI"?

**Lean:** the state view is advisory only — it recommends next actions from the artifact frontier and never blocks work. But this needs testing against the drowning-in-openness failure mode it exists to fix; advice that can be ignored freely may not fix it.

## Q6. Scope: is KagamiOS ML-research-specific?

The design quietly assumes experiments are code: cheap probes, fast iteration, re-runs on demand. Wet-lab, clinical, and field research have irreversible experiments, months-long cycles, and regulatory preregistration — there the stage-gate weight should *increase*, and Probe may not exist. Theory/mathematics research barely has an Execute state at all.

**Lean:** design v1 unapologetically for ML/computational research; keep the artifact layer domain-neutral so state-machine variants per domain remain possible. Declare this rather than pretending generality.

## Q7. Single researcher vs. lab

V1 targets one researcher (`vision.md`). But most research is collaborative, and the artifact model creaks under collaboration: who is "the human" at a constitutive gate (P3)? Do advisor and student both sign? Are RDRs shared truth or per-person? Does the portfolio belong to a person or a lab? The academic reality — the advisor *is* the human-in-the-loop for most students, and lab meetings are the real review gates — suggests the multi-party version is the more faithful model, not an extension.

**Open;** deliberately deferred, but the artifact schemas should avoid baking in single-authorship (e.g., `decided_by` already names a person, which generalizes).

## Q8. Confidentiality and priority

Unpublished ideas are competitively sensitive. Every AI-drafted artifact means sending the project's crown jewels — the intuition, the gap, the hypothesis — to a model API. Related: does an AI-drafted trail affect priority disputes or authorship norms? And some researchers will simply refuse.

**Open:** at minimum, the design must not *require* cloud AI for the artifact layer to function (plain Markdown must remain valid); local-model and no-AI degradation paths matter more here than usual.

## Q9. How would we know KagamiOS works?

`vision.md` lists success criteria, but most are self-reported and n=1. Time-to-kill is measurable but confounded (maybe the ideas were just bad). Cold-start resumption is testable (pause a project, have an agent resume it from artifacts alone — a genuinely nice benchmark). Is there any honest comparison, given no researcher runs the same project twice, with and without the OS?

**Lean:** accept n=1 anecdote for v1; define the resumption test precisely, since it is the one objective, repeatable measurement the design admits.

## Q10. Does the Historical Narrative earn its way back in?

Demoted to optional (`state_machine.md` §1.2) on cost grounds. Counterargument worth respecting: for a *method-first* intuition like Signatures — exactly the founding use case — understanding why the field evolved as it did may be the single best defense against type-4 gaps ("already filled, you missed it") and against re-proposing ideas the field already tried and abandoned in an earlier fashion cycle.

**Test during dogfooding:** write it for the Signature project; record whether any downstream artifact ever cites it.

## Q11. Build vs. integrate

Zotero holds references; OSF holds preregistrations; ELNs hold lab notebooks; arXiv/Semantic Scholar feeds exist; git holds versions. What is KagamiOS's actual footprint — a schema-plus-conventions layer over git and existing tools, or a system with its own storage and UI? The staleness graph (P7) is the one component nothing else provides; almost everything else risks reinventing a tool someone already maintains.

**Lean:** KagamiOS = artifact schemas + dependency/staleness semantics + agent roles, hosted in a plain git repo; integrate outward for references and feeds. Decide only after Q1's hand-run dogfooding shows where the friction actually is.

## Q12. Deadline-driven reality

ML research runs on conference deadlines: the last month before a deadline is triage warfare, and no one updates artifact frontmatter at 3 a.m. Does the system have a "sprint mode" — a sanctioned degraded state with post-hoc artifact reconciliation — or does it accept going dark and being re-synced after submission?

**Lean:** post-hoc reconciliation as an explicit, supported operation (the system asks what happened and backfills RDRs), because pretending the dark period won't happen violates P9.
