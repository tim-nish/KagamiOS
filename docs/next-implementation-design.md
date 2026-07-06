# Next Implementation Cycle — BMAD Planning Brief

*Written 2026-07-05. Synthesizes `docs/dogfooding-review.md` and
`docs/7-questions-response.md` into a concrete plan for how the next implementation
cycle should enter BMAD: which changes need change signals, what the PRD/spine deltas
are, the proposed epic/story cut, and how the work interleaves with dogfooding runs 2–3.
This document is the input to the change-signal step; it is not itself a change signal,
a PRD delta, or an epic.*

---

## 1. Governing constraints (carry these into every downstream artifact)

These are the standing decisions from `change-signal-scout-probes-2026-07-04.md` and
`docs/future-scout-redesign.md`'s resumption protocol. Every change signal, FR, and
story in this cycle must respect them:

1. **The adjudication process is the product of this cycle.** Run 1 tested the
   instruments, not the redesign; the 2–3-run counter still reads zero. Nothing in this
   cycle funds or dissolves an adjudication-table row. The cycle's job is to make runs
   2–3 clean enough that the table can finally be read.
2. **Scope discipline is unchanged:** no belief store, no frontier, no allocator/UCB, no
   diversity reserve, no governor. Any story growing toward those is out of scope. The
   one apparent exception — abstract-level card extraction — is not an exception: it is
   needed under *every* adjudication outcome (see §4).
3. **Amend, never renumber.** New FRs take FR-54 onward; new ADs take AD-29 onward.
   Epics 1–8 are implemented and traceable — preserve verbatim; append Epics 9+.
   Extend the existing PRD with subsections; do not create a new PRD.
4. **FR-25 stays untouched:** Scout remains the sole corpus-touching role; anything new
   lives behind the existing chokepoints.
5. **The event log stays the single source of truth**; anything derived must be
   replayable from it.

## 2. The cycle at a glance

| Track | Vehicle | Epic | Blocking run 2? |
|---|---|---|---|
| 0. Instrument repairs | Defect stories under existing FRs — **no change signal** | Epic 9 | **Yes** |
| A. Paper content & read discipline | Change Signal A | Epic 10 | **Yes** |
| B. Human-signal integrity | Change Signal B | Epic 11 | Only story 11.1 |
| C. Run fork (dev-loop economics) | Change Signal C (small) | Epic 12 | No |
| — Dogfooding runs 2–3 | Amended protocol (§8) | — | — |

Recommended order: **Epic 9 → Epic 10 → Story 11.1 → Run 2 → rest of Epic 11 (+ Epic 12
opportunistically) → Run 3 → adjudication session.**

---

## 3. Track 0 / Epic 9 — Instrument Repairs (no change signal)

These are cases where code disagrees with its own already-approved spec or a live
external API. They change no requirement and no architectural rule, so they enter BMAD
as defect stories under the existing FRs (FR-50 family and FR-29), not as a change
signal. All are precise, small, and fully evidenced in the run-1 findings.

**Story 9.1 — `corpus expand` works against real providers.**
Fix `OpenAlexProvider.citation_graph` (`kagamios/kagami/corpus/adapters.py:90-97`):
incoming citations via `/works?filter=cites:{id}`, outgoing references from the
`referenced_works` array on `works/{id}`. Audit the other three adapters'
`citation_graph` implementations against their live APIs. Add recorded-fixture contract
tests per adapter so provider drift is caught in CI, not mid-run.
*Acceptance:* a live (or fixture-replayed) `kagami corpus expand` mints neighbor cards
and appends one `corpus_expand` retrieval event with a non-empty edge list.

**Story 9.2 — `charter-audit` tells the truth.**
(a) Sync `SCOUT_ALLOWED_OPERATION_CLASSES` (`kernel/charter_audit.py`) with Scout's
charter — `paper_card_extraction` is charter-mandated and must be allowlisted; add a
test that pins the allowlist to the operation classes named in `agents/scout.md` so the
two files cannot drift apart again. (b) Split refused-and-blocked attempts out of
`violation_count` into a separate `refusals_held` count — a guard doing its job must not
read as a breach.
*Acceptance:* replaying run 1's event log reports `violation_count == 0`,
`refusals_held == 1`.

**Story 9.3 — Provider override + CLI friction polish.**
`--provider` override on `corpus search`/`corpus expand` (resilience to single-provider
outages; run 1 had no route around the broken adapter). Normalize case on state/section
string arguments at the CLI boundary; make the two FR-15 error variants consistent;
auto-mint (or clearly instruct) `--call-id` so the AD-26 first-attempt stumble stops
recurring across roles.

---

## 4. Change Signal A → Epic 10 — Paper Content & Read Discipline

**Trigger to record:** run 1 demonstrated that (i) paper cards carry no extracted
content — `kernel/scout.py:search_corpus` is a raw metadata passthrough — so Historian's
dossiers rested entirely on subagent background knowledge, Cartographer's `draft`
degenerated to identical partitions, and appraisals judged titles; (ii) no state's
consumption map includes `paper_card`, so Deepen has no sanctioned way to read the
content it exists to write about (three independent FR-15 refusals); (iii) the AD-2
guard's matcher omits `Read`, so every role routed around (ii) by reading the output
root directly — the spine's default-deny claim is false as shipped.

These three are one coherent change: give roles a legitimate way to see paper content,
then close the illegitimate way. **Internal sequencing is mandatory: read path before
guard closure** — closing the `Read` gap first would deadlock Deepen.

**Proposed FR deltas (PRD subsection: "Paper content & read discipline"):**

- **FR-54 — Abstract-derived card extraction (the shallow-read rung).** At card-mint
  time, populate the card's content fields (`contribution_line`, `method_class`,
  `evidence_type`, `key_claims`) from provider-supplied title+abstract via one model
  call, reported under the existing `paper_card_extraction` operation class. OpenAlex
  already returns abstracts (`abstract_inverted_index`) in search responses — zero
  extra retrieval. Cards remain frame-independent facts cached forever (AD-18
  unchanged in kind, extended from metadata to abstract-derived content); the
  `FORBIDDEN_CARD_FIELDS` chokepoint invariant (AD-28) is untouched. Providers without
  abstracts yield cards with content fields empty and a `content_source` marker — a
  real sensor bias, exposed rather than papered over.
- **FR-55 — Sanctioned paper-card read path.** Add `paper_card` to the consumption-map
  read-sets that need it (Deepen at minimum; audit Synthesize and Locate at
  story-design time), and/or a `kagami corpus show <paper-id>` verb — either way routed
  through the existing FR-15 read chokepoint with a defined brief. No role reads card
  files off disk.
- **FR-56 — Close the `Read` gap.** Add `Read` to the AD-2 hook matcher
  (`kagamios/hooks/hooks.json`), restoring the spine's "any tool invocation" claim.
  Testable at the hook boundary: a `Read` targeting the output root is denied; the same
  content is reachable via the FR-55 path.

**Spine deltas:** re-affirm AD-2/AD-23 (text corrected to match the now-true
implementation — amend, never renumber). One genuinely new AD:

- **AD-29 — The sensor cost ladder.** Processing depth is a budgeted ladder: metadata
  (free at retrieval) → abstract-derived card (one model call, once ever, at mint) →
  deep read (**not built in this cycle**; when built, section-limited and explicitly
  gated). No pipeline step may pay a rung's cost without the previous rung's evidence.
  Recording the ladder now is what keeps FR-54 a rung rather than a slippery slope — and
  gives the deferred deep-read sensor a numbered home so building it later is an
  amendment, not a redesign.

**Proposed story cut:**

- **10.1 — Extraction at the mint chokepoint (FR-54).** Touches
  `get_or_create_paper_card`'s compute path; fixture-tested with recorded abstracts;
  re-run the Cartographer `draft` path over extracted cards to confirm `method_class`
  clustering becomes non-degenerate (this is the FR-26 convenience command earning its
  name back).
- **10.2 — Read path + consumption-map audit (FR-55).** Includes regenerating role
  briefs so Historian's context instructions point at the sanctioned path.
- **10.3 — Guard closure + spine reconciliation (FR-56, AD-29, AD-2/23 text).** Last in
  the epic, by construction.

**What this deliberately does not include:** deep read (rung 3), embeddings, any content
store outside the card. Q6's "sections only, never whole papers" is honored by AD-29's
gating, not by building the sensor now.

---

## 5. Change Signal B → Epic 11 — Human-Signal Integrity

**Trigger to record:** run 1 found the "field implies an owner, nothing enforces one"
pattern three times (`human_read` set by an AI role on all 9 papers; `appraisal record`
has no actor argument; `meaningful_to_me` previously); the researcher directly judged
the binary read-gate too heavyweight for early exploration; and the rediscovery-rate
metric was silenced once by cross-run cache reuse (protocol had to clear the cache) and
poisoned once by orchestrator re-queries — both because the metric cannot see *who
asked and why*. `7_questions.md` Q2/Q5/Q8 converge on the same direction: structured,
attributed, lightweight human signal.

**Proposed FR deltas (PRD subsection: "Actor attribution & confirmation weight"):**

- **FR-57 — Retrieval attribution + within-run metric scoping.** Retrieval events carry
  the requesting role (and an `administrative` flag for non-exploration lookups);
  rediscovery-rate (FR-52 amended) counts only this run's organic Scout lookups.
  Consequences: cross-run cache reuse stops confounding the saturation signal (the
  cache never needs clearing again), and an orchestrator convenience re-query can no
  longer poison the window. Deterministic, replayable from the log.
- **FR-58 — Actor attribution on judgments.** Human-asserted fields and judgment
  records carry who asserted them, enforced at the write chokepoint: `human_read` (or
  its successor) is settable only by the human actor; `appraisal record` gains a
  `--role` argument recorded in the entry. Same enforcement pattern as AD-28's
  forbidden-fields check — one chokepoint, mechanically testable.
- **FR-59 — Lightweight Deepen confirmation gate (amends FR-28's exit criterion).**
  Replace the binary `human_read` requirement with an actor-checked human confirmation
  per representative paper: rating + confidence + optional note. The gate checks that a
  *human-attributed* confirmation exists, not that a paper was read.

**Charter/skill change (prompt-artifact convention, no FR machinery):** the Interviewer
adopts structured-first questioning — multiple-choice with a mandatory free-text escape
hatch, each question carrying its "what changes under each answer" line; free-text-first
remains the rule in Frame (the utility function is elicited, not chosen). Verified per
the existing recorded-transcript convention, like Story 8.3.

**Spine delta:** one new AD — **AD-30 — Signals carry their author.** Any field or
record whose meaning depends on *who* produced it (human confirmations, judgments,
retrieval purposes) must carry and enforce actor attribution at the write chokepoint.
This names the pattern once so the fourth occurrence becomes a spine violation instead
of a rediscovery.

**Proposed story cut:**

- **11.1 — Retrieval attribution + metric scoping (FR-57).** *Pull this forward, before
  run 2*: it repairs a run-1 instrument failure, and changing the metric's semantics
  mid-adjudication is safe precisely because run 1 produced no clean reading to compare
  against.
- **11.2 — Actor attribution at the write chokepoint (FR-58, AD-30).**
- **11.3 — Lightweight confirmation gate + Interviewer structured-first (FR-59 +
  charter change).** After run 2 is fine; run 2 can use the existing gate.

---

## 6. Change Signal C → Epic 12 — Run Fork (optional, dev-loop economics)

**Trigger:** dogfooding reruns pay full-pipeline token cost to test one modified
component (`7_questions.md` Q9). The architecture already made the commitments that make
this cheap (append-only log as source of truth; consumption maps define state inputs).

- **FR-60 — `kagami run fork --run-id <parent> --from-state <state>`.** Creates a *new*
  run directory (the parent's log is never rewritten): copies the parent's artifacts and
  event prefix up to the state boundary, records `parent_run_id` provenance, marks
  copied human decisions `inherited`, sets `current_state`. Metrics never blend parent
  and child events (FR-57's scoping covers this).

Single-story epic. No spine delta — it is an application of existing commitments.
Schedule opportunistically; nothing else depends on it, but every dev loop after it
lands gets cheaper, so earlier is better if capacity allows.

---

## 7. What this cycle explicitly defers (unchanged from the standing decision)

Belief store / Landscape Model, Frontier, Allocator/UCB, diversity reserve, Governor,
deep-read sensor (AD-29 rung 3), embeddings/semantic-similarity edges, cross-run
map-level reuse (the `7_questions.md` Q8 mechanism beyond what the corpus cache already
does), and any external benchmark work beyond the note in §8. Each of these waits on its
adjudication-table row. A story that needs one of them is mis-scoped.

---

## 8. The evidence contract: dogfooding runs 2–3

The protocol (`epic-8-dogfooding-protocol.md`) is amended, not rewritten. Deltas for
run 2, each traceable to a run-1 finding:

1. **No orchestrator-issued corpus lookups mid-run, ever.** Card data for downstream
   roles is captured from the original call's output. (FR-57 additionally makes the
   metric robust to a violation, but the protocol rule stands.)
2. **Evidence extraction respects AD-2.** The researcher copies `events.jsonl` out of
   the output root; the assistant does not read it in place. Run 1's shortcut worked
   only because of the FR-56 gap, which Epic 10 closes.
3. **At least one deliberate human redirection of Scout's search**, and a topic/steering
   plan that makes a mid-run frame revision plausible — otherwise the Governor,
   Frontier/Allocator, and belief-store-split rows remain structurally unfireable, as
   they were in run 1.
4. **Cache handling:** once 11.1 (FR-57) lands, do *not* clear the cross-run cache —
   reuse becomes free and the metric ignores it. If run 2 somehow precedes 11.1, clear
   the cache as before and record the caveat.
5. **Expand must actually run:** Scout should exercise `corpus expand` on its named
   anchors so the diversity-reserve row finally has a citation graph to be checked
   against, and the search-vs-expand yield comparison has data on both sides.
6. Rediscovery-rate readings at 2–3 mid-run points plus run end, quoted verbatim, as
   before.

**Benchmark note (from Q1, deliberately small):** when convenient — not gating anything
— trial one systematic-review replay (SYNERGY dataset: frame = the review's question;
measure recovery of its included-studies set per token). If it proves cheap and
informative, it enters the *next* cycle as a proper FR; for now it is an experiment, not
a commitment.

**After run 3:** hold the adjudication session per `future-scout-redesign.md`'s
resumption protocol — pull graphs from `corpus_expand` events, rediscovery trajectories,
frame-revision/appraisal-reissue counts, and checkpoint transcripts; fund only the rows
that fired; write the next change signal scoped to exactly those components. If no row
fires across clean runs, close the notebook — that is a success condition.

---

## 9. Execution notes for the BMAD flow

- Author Change Signals A–C in the established format
  (`_bmad-output/planning-artifacts/change-signal-*.md`), each with its own
  verified-state section re-checked against code at writing time (this brief's file
  references are as of 2026-07-05).
- PRD: extend `prds/prd-KagamiOS-2026-07-02` with the two subsections named above;
  spine: amend `ARCHITECTURE-SPINE.md` with AD-29/AD-30 and the AD-2/23 text
  correction; epics: append Epics 9–12 to `epics.md` and update the Requirements
  Inventory / FR Coverage Map for FR-54–FR-60 only.
- Story authoring and implementation proceed per the existing conventions
  (`bmad-create-story` → `bmad-dev-story`); Epic 9's defect stories cite the run-1
  findings document as their evidence base in lieu of a change signal.
- Every mechanical FR here is testable at a chokepoint or CLI boundary; the two
  prompt-artifact changes (Interviewer structured-first; protocol deltas) use the
  recorded-transcript convention. Nothing in this cycle requires a new testing
  convention.
