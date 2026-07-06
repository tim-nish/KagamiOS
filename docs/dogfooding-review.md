# Dogfooding Review — Epic 8 Evidence Run

*Review of `_bmad-output/implementation-artifacts/epic-8-evidence/run-2afeef8fb9a9-findings.md`
(2026-07-04) against the protocol in
`_bmad-output/implementation-artifacts/epic-8-dogfooding-protocol.md`. Written 2026-07-05.*

## Overall assessment

The run did its job, but the job turned out to be different from the one planned. It was
designed to collect evidence for the six rows of `docs/future-scout-redesign.md`'s
adjudication table; instead it mostly **tested whether the four probes work as
instruments, and found that two do not (cleanly) yet**. None of the six adjudication rows
fired — but three of the six "did not fire" outcomes are instrument failures (`corpus
expand` broken, rediscovery-rate contaminated, no frame revision occurred), not evidence
that the redesign components are unneeded. The findings document itself draws this
distinction correctly, and it is the single most important thing to preserve going into
run 2: **do not credit any adjudication row as "dissolved" on the basis of this run.**

The run also surfaced two findings the probes were not designed to look for — the AD-2
`Read` gap and the empty-paper-card problem — which are arguably more consequential than
anything the probes were pointed at. That is dogfooding working as intended.

The evidence-collection discipline held well: the session recorded a contaminated metric
honestly instead of presenting it at face value, quantified the contamination from the
raw log, refused to write fixes mid-run per protocol, and filed everything against the
adjudication table. The protocol document earned its keep.

## Findings, assessed

Ordered by importance. Classification key: **bug** = code disagrees with its own spec or
an external API; **design** = the system as specified is missing something or specifies
the wrong thing; **protocol** = the dogfooding procedure itself needs amending.

### 1. `corpus expand` is non-functional (OpenAlex 404) — **implementation bug, critical**

`OpenAlexProvider.citation_graph` (`kagamios/kagami/corpus/adapters.py:90-97`) calls
`works/{id}/citations`, a sub-resource that does not exist in OpenAlex's API. All three
expand attempts failed identically; Story 8.1's entire deliverable (edge-carrying
retrieval events) produced zero data.

**Why it matters this much:** it doesn't just block one probe. It blocks the
diversity-reserve adjudication row (needs a reconstructed citation graph), it reduced
Scout's charter decision menu from three options to two (requery/report, no expand), and
it is one of the two live hypotheses for why the rediscovery-rate metric never rose
(breadth-first requery may structurally avoid saturation in a way anchor-expansion would
not). Three of the run's inconclusive results trace partly to this one bug.

**Next step:** fix before run 2, and this is a small, well-understood fix. OpenAlex
exposes citation edges two ways: incoming citations via the filter endpoint
(`/works?filter=cites:{work_id}`) and outgoing references via the `referenced_works`
array already present on the `works/{id}` object the adapter can fetch with a single
call. Verify against the live API (the run already confirmed `works/{id}` returns 200).
While in there, check the Semantic Scholar / arXiv / GitHub adapters' `citation_graph`
implementations too — the run couldn't, because of finding 9. Add a live-API smoke test
or a recorded-fixture test so a provider-side contract drift is caught before the next
run rather than during it.

### 2. Paper cards carry no extracted content — **design issue, critical (highest leverage)**

`kernel/scout.py:search_corpus` passes provider metadata straight through to the card
(`compute=lambda raw=raw: raw`); `contribution_line` / `method_class` / `evidence_type`
/ `key_claims` are always empty. No content-extraction step exists anywhere in the
pipeline.

**Why this is the most important finding of the run:** it cascades into nearly
everything downstream, and the run demonstrated each cascade concretely:

- `cartographer draft` clusters on `method_class`/`source`; with those empty/uniform it
  produced identical partitions and was (correctly) refused by its own FR-26 check. The
  convenience command cannot do its job on thin cards.
- Historian's dossiers this run rested **entirely on subagent background knowledge** of
  famous tools, not on anything the system fed it. That produced credible prose here
  only because the papers were well-known; it will silently fail on obscure papers, and
  nothing in the artifact reveals which regime you're in. This is a correctness risk to
  KagamiOS's core output, not a polish item.
- Appraisals are, in effect, judgments of titles.

**Next step:** this deserves its own probe-sized story (with a change signal, since it
adds a pipeline stage), not a drive-by fix. The minimal version is cheap: OpenAlex
already returns abstracts (`abstract_inverted_index`) in search responses at zero extra
retrieval cost, so an abstract→card extraction step is one model call per new paper,
cached forever per AD-18. It is also exactly "sensor 3, shallow read" from the redesign's
sensor suite — so building it is evidence-aligned, not redesign-by-the-back-door. Fixing
this before run 2 also makes run 2's evidence better across the board (Cartographer,
Historian, and appraisals all become tests of the system rather than of subagent
memory).

### 3. `Read` is not covered by the AD-2 guard — **implementation bug against the spine, high**

The spine (AD-2/AD-23) claims the PreToolUse hook is default-deny for *any* tool
touching the output root; `hooks.json`'s matcher is `"Write|Edit|NotebookEdit|Bash"` —
`Read` is absent. Exercised, unprompted, by two subagents and the orchestrator; the
findings document itself was produced by reading `events.jsonl` through this gap (a
protocol deviation worth noting: the protocol prescribed a researcher-performed copy).

**Assessment:** the spine's claim is simply false as shipped, and an architectural
integrity claim that is false is high-severity regardless of whether the current effect
was benign. But note *why* it was exercised: every actor that used the gap was routing
around a **missing sanctioned read path** (finding 4). Closing the gap first would have
deadlocked Historian entirely.

**Next step — sequencing matters:**
1. Add the sanctioned read path (finding 4) so roles have a legitimate way to see what
   they need.
2. Then add `Read` to the hook matcher.
3. Then correct or re-affirm the spine text (amend, never renumber, per the resumption
   protocol).
Doing step 2 before step 1 converts a discipline gap into a hard blocker.

### 4. No sanctioned read path for paper-card content in Deepen — **design issue, high**

`consumption_map.yaml`'s `deepen` read-set omits `paper_card` (no state includes it),
and no CLI verb fetches card content. All three Historian subagents hit this wall
independently, three times, with the same FR-15 refusal.

**Assessment:** this is a genuine hole in the FR-15 consumption maps — Deepen's whole
purpose is to write dossiers *about papers*, and the state cannot legitimately read
paper data. It compounds with finding 2 (even via the guard gap, there was little content
to read).

**Next step:** add `paper_card` to the `deepen` read-set (and audit other states —
Synthesize and Locate plausibly need it too), or add a `kagami corpus show <paper-id>`
verb routed through the read chokepoint. Ship together with findings 2 and 3 as one
coherent "roles can actually see paper content, and only through the chokepoint"
change.

### 5. `charter-audit` reports false violations — **implementation bug, high**

`charter_audit.py`'s `SCOUT_ALLOWED_OPERATION_CLASSES` omits
`paper_card_extraction`, which Scout's own charter instructs it to use. Result: 13 of 14
reported violations were Scout behaving exactly per charter; the 14th was a guard
*correctly refusing* a Historian write, bundled into the same count as if it had landed.
Net real violations: 0.

**Why it matters:** FR-29's mechanical backstop is the thing that's supposed to be
trustworthy when transcript review isn't. As shipped, **every charter-compliant run
reports 13+ violations**, so the tool's signal is unusable at face value — worse than no
tool, because a casual reader would conclude Scout is off-charter.

**Next step:** two small fixes. (a) Sync the allowlist with the charter, and add a test
asserting every operation class named in `agents/scout.md` is allowlisted — the bug was
the two files drifting, so the test should pin them together. (b) Separate
refused-and-blocked attempts from landed violations in the output (`refusals_held` vs
`violation_count`), so a working guard stops inflating the breach count.

### 6. Rediscovery-rate tail contamination — **protocol issue (with a small design tweak), medium**

The orchestrator re-ran 5 cached queries mid-run to extract JSON for Cartographer,
appending 25 guaranteed cache hits to the retrieval log. Default-window readings
(`--window 20`, `--window 5`) read 1.0 — measuring only the contamination. The genuine
organic rate, isolated by hand, was ~1.5% (1/65) with no plateau.

**Assessment:** the protocol lesson is already correctly recorded (capture card data
from the original call's output; never re-query for convenience). But the incident also
exposes a design fragility: the metric cannot distinguish *why* a lookup happened. Any
future administrative re-query — by anyone — silently poisons the window, and there is
no post-hoc exclusion mechanism.

**Next step:** amend the protocol (done, in effect, by the findings doc). Additionally,
consider attributing retrieval events with the requesting role/purpose and having the
metric count only Scout-attributed organic lookups. That is a small event-schema
addition, consistent with the log-as-source-of-truth commitment, and it makes the metric
robust instead of etiquette-dependent. Fold into the same change signal as finding 7's
actor-attribution pattern if pursued.

### 7. "Field implies an owner, nothing enforces one" — recurring pattern — **design issue, medium**

Three independent occurrences: `human_read` set by an AI role on all 9 papers with no
complaint; `appraisal record` has no actor/role argument or check; (and the previously
noted `meaningful_to_me`). Plus the researcher's direct judgment: a binary
"I have read this paper" gate before Deepen can close is **too heavyweight for an
early-exploration workflow** — they want a lighter confirmation (rating / confidence /
note).

**Assessment:** two distinct findings sharing one root. The mechanical half (no actor
attribution anywhere) is a schema gap that recurs because there is no actor concept in
the store layer at all. The workflow half is a validated UX finding about Deepen's exit
criterion — and it converges with the researcher's broader position in `7_questions.md`
(Q5): heavy human input mid-survey undermines the product's value.

**Next step:** treat as one design change: add actor attribution to human-asserted
fields and judgments (who set `human_read`, who issued an appraisal), and replace the
binary `human_read` exit gate with a lightweight human confirmation
(rating/confidence/optional note) that *is* actor-checked. Needs a change signal since
it touches FR-28's exit criterion. See `docs/7-questions-response.md` Q5 for the fuller
argument.

### 8. Zero human checkpoints during Scout's search — **evidence gap, medium (for adjudication)**

Scout ran all 13 iterations fully autonomously; the Governor and Frontier/Allocator
adjudication rows therefore had literally nothing to evaluate. Not a defect — the
current system has no checkpoint mechanism inside Map at all — but it means those two
rows can never fire from a run shaped like this one.

**Next step:** protocol amendment for run 2: the researcher should deliberately inject
at least one mid-search redirection (and, ideally, steer the run so a frame revision
occurs, which also unblocks the belief-store-split row / Story 8.2's open question).
These rows measure *friction under human steering*; a run with no steering can't
measure them.

### 9. No `--provider` override on corpus commands — **design gap, low-medium**

There was no way to route around the broken OpenAlex adapter or to test other providers'
`citation_graph` implementations within the run. A `--provider` flag (or per-command
config override) is cheap and makes future runs resilient to single-provider outages.
Worth doing alongside finding 1.

### 10. String-casing traps and first-attempt `--call-id ""` stumbles — **implementation polish, low**

Case-sensitive string keys (`evolution` vs `Evolution`, `deepen` vs `Deepen`) with
divergent error messages, discoverable only by reading source; two roles independently
first-attempted an empty call-id before the AD-26 guard corrected them.

**Next step:** normalize case at the CLI boundary (lowercase state/section arguments
before dispatch), make the two FR-15 error messages consistent, and tighten the charter
wording on minting call-ids (or auto-mint when absent, since the guard's purpose is
idempotency, not ceremony). Small, but three independent subagents paying a
read-the-source tax each is a real token cost multiplied across every future run.

## Priority summary

| # | Finding | Class | Importance | When |
|---|---|---|---|---|
| 1 | `corpus expand` OpenAlex 404 | bug | critical | before run 2 |
| 2 | Cards carry no extracted content | design | critical | before run 2 (own story + change signal) |
| 3 | `Read` not covered by AD-2 guard | bug (vs spine) | high | before run 2, **after** #4 |
| 4 | No sanctioned paper-card read path in Deepen | design | high | before run 2, with #3 |
| 5 | `charter-audit` false positives | bug | high | before run 2 |
| 6 | Rediscovery-rate tail contamination | protocol (+small design) | medium | protocol now; schema tweak optional |
| 7 | Actor attribution + `human_read` gate weight | design | medium | change signal; can follow run 2 |
| 8 | Zero checkpoints → two rows unfireable | evidence gap | medium | protocol amendment for run 2 |
| 9 | No `--provider` override | design gap | low-med | with #1 |
| 10 | Casing traps, empty call-id | polish | low | opportunistic |

## Recommended sequence

1. **Fix the instruments** (findings 1, 5, 9, 10): small, precise, well-evidenced bugs.
   No change signal needed — these make the shipped probes do what their stories already
   claimed.
2. **One coherent read-path/content change** (findings 2, 3, 4): change signal, then a
   probe-sized story adding abstract-level card extraction, a sanctioned card read path,
   and `Read` in the hook matcher — in that order. This is the highest-leverage work
   item on the list and stays inside the "evidence decides the redesign" discipline: the
   shallow-read sensor was going to be needed under every adjudication outcome.
3. **Run 2** with the amended protocol: cache cleared, no orchestrator re-queries,
   expand working, at least one deliberate human redirection, and a topic/steering plan
   that makes a frame revision plausible. Only then do the adjudication rows get their
   first real reading.
4. **Actor attribution + Deepen exit-gate redesign** (finding 7): write the change
   signal now while the evidence is fresh; implement after run 2 unless run 2 is blocked
   on it (it isn't).

Per the redesign notebook's own resumption protocol, no adjudication row should be
funded or dissolved before 2–3 clean runs — and run 1, for adjudication purposes, was
not clean. The counter effectively still reads zero.
