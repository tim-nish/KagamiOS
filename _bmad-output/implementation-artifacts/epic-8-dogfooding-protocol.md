# Epic 8 Dogfooding Protocol (2026-07-04)

## Purpose

This is an evidence-collection run, not a feature evaluation. Epic 8 shipped four
minimal, independently shippable probes (`corpus expand`, appraisal records, Scout
charter discipline, rediscovery-rate) instead of the larger Scout graph-exploration
redesign (`docs/future-scout-redesign.md`). The decision record
(`_bmad-output/planning-artifacts/change-signal-scout-probes-2026-07-04.md`) is explicit
that each probe is instrumentation whose data — not this session's opinions — decides
which, if any, redesign component gets built.

**This session produces evidence and files it against `future-scout-redesign.md`'s
adjudication table. It does not redesign Scout, propose new architecture, or write new
implementation, unless evidence collected during the run clearly forces it** — and even
then, the correct output is a written observation for a future change-signal, not code
written in this session.

## Preconditions (status as of this writing)

- [x] Local `main` fast-forwarded to `origin/main` — Stories 8.1–8.4 all present.
- [x] Full test suite green (433/433).
- [x] AD-2 glob-evasion fix committed (`10276f6`).
- [x] Epic 8 planning record (PRD/spine/epics deltas, change-signal doc, two design
      notebooks, root `config.yaml`) committed (`131d152`).
- [ ] **`_kagami-output/` cleared or renamed aside by the researcher** (blocked for the
      assistant by AD-2's own guard — this is the guard working correctly, not a bug).
      Do not start the run until this is confirmed, or the ~200-paper cross-run corpus
      cache from the prior investigation will pre-seed `reused: true` on any overlapping
      topic and distort the rediscovery-rate reading from iteration 1.
- [ ] Confirm `config.yaml`'s `literature_provider: openalex` is reachable (network /
      API key available in this environment) before relying on live search.

## Topic selection

Pick a real question you actually want answered — this is a real investigation, not a
toy run (the fixed-corpus golden toy run already covers harness mechanics per AD-27; see
`golden-toy-run-protocol.md`). One constraint: prefer a topic domain clearly distinct
from whatever the prior dogfooding run (the one that triggered this change signal)
searched, so the leftover corpus cache — if not cleared — can't confound rediscovery-rate
by pre-marking papers `reused` before Scout does anything in this run.

## Mechanics reminder (what changed since the last real run)

- `corpus search` now defaults `--limit` to 8 (was an unbounded pull to the provider's
  own default of 20). Scout's charter (`agents/scout.md`) now states an iteration
  discipline: search small → skim → decide (requery / expand / report) → cap new papers
  per iteration → name 2–4 anchors when handing off to Map. **This is prompt discipline,
  not a mechanical guarantee** — nothing refuses a large `--limit` or an unnamed anchor.
- `corpus expand --canonical-key <key>` is a second sanctioned Scout entrypoint: pulls
  the citation neighborhood of a known paper and appends one `retrieval` event of kind
  `corpus_expand` carrying an explicit edge list (`from`/`to`/`direction`).
- `appraisal record --paper-id --judgment --frame-version --reason` records a
  frame-stamped judgment separate from the paper card. Cards never carry frame-dependent
  fields (enforced at the write chokepoint — `FORBIDDEN_CARD_FIELDS` in
  `kagami/corpus/cache.py`).
- `metrics rediscovery-rate --run-id <id> [--window N]` (default window in
  `DEFAULT_REDISCOVERY_WINDOW`) reports the fraction of the last N paper lookups
  (search + expand combined) that were already-seen. Warn-only; never blocks.
- `metrics charter-audit --run-id <id>` is a **mechanical, code-checkable** backstop
  (FR-29) for a different, narrower set of violations (Scout producing interpretation
  instead of retrieval, non-Scout roles touching the corpus, Skeptic/Historian
  off-charter writes). It does **not** check the iteration-discipline prose (search size,
  skimming, anchor naming) — that's transcript-only, per AD-27.

## Evidence to capture, per story

### Story 8.1 — Corpus Expand (citation-graph sensor)

- Every `corpus_search` and `corpus_expand` call and its raw response (titles, sources,
  edge lists) — capture in the transcript as it happens; this is the only place the full
  edge lists are visible to a human reviewer, since no `kagami` CLI verb dumps
  `events.jsonl` (by design — AD-11 restricts raw-log reads to `kagami metrics`).
- At run end, ask the researcher to copy `<run-dir>/events.jsonl` out of the output root
  to an evidence folder (outside `_kagami-output/`, e.g.
  `_bmad-output/implementation-artifacts/epic-8-evidence/<run-id>-events.jsonl`) — the
  assistant cannot do this copy itself (AD-2). From that copy, reconstruct the observed
  citation graph from `corpus_expand` events' edge lists and check:
  - Does anchor-expansion find relevant papers `search` alone wouldn't have, and at what
    token cost relative to a search iteration? (yield comparison)
  - Any single-articulation-point clusters — whole communities reachable only from one
    seed's citation basin? (the specific evidence that would fund the diversity-reserve
    component)

### Story 8.2 — Appraisal Records (fact/judgment split)

- Every `appraisal record` call: paper id, judgment, frame_version, reason — log in the
  transcript as issued.
- Track frame revisions during the run (each time the Inquiry Frame's version bumps).
  For each revision: how many prior appraisals became stale, were they re-issued, and
  what did re-judging cost (tokens, turns) versus what re-exploring would have cost?
  This is the direct evidence FR-52/AD-28 exists to produce for the belief-store-split
  adjudication row.
- Spot-check: confirm no paper card ever picked up a `relevance`/`priority`/`judgment`
  field (should be structurally impossible per the write chokepoint, but worth an
  observation either way — a violation here would itself be a finding).

### Story 8.3 — Scout Charter Discipline (AD-27 verification)

This story's Definition of Done is transcript + checklist, not pytest — treat this run's
own transcript as the AD-27 artifact.

- **Recorded-transcript check**: after the run, review Scout's actual tool calls against
  the charter checklist:
  - [ ] Search calls used a small `--limit` (default 8), not an inflated one, absent a
        stated reason.
  - [ ] Scout visibly skimmed results (titles/sources/authors) before its next action,
        not chained calls blindly.
  - [ ] Each iteration was a legible decision: requery / expand / report — not a repeat
        of the same query.
  - [ ] No single iteration flooded the corpus beyond what got skimmed before the next
        decision.
  - [ ] Anchors (2–4 papers) were named when Scout reported back to Map.
- **Checkpoint cadence observation**: note every point a human was asked to weigh in
  during Scout's search — was each one earned (would a plausible different answer have
  changed the next action)? This is the raw material the future Governor's EVOI test
  would need; captured here as an observation, not implemented.
- **Mechanical backstop**: run `kagami metrics charter-audit --run-id <id>` and confirm
  `violation_count == 0` (or record what fired).

### Story 8.4 — Rediscovery-Rate Metric

- Run `kagami metrics rediscovery-rate --run-id <id>` at 2–3 points during Scout's work
  (not only at the end) and again at run end. Record `sample_size` and `rediscovery_rate`
  each time.
- Does the rate rise and plateau as a region gets exhausted? Compare the plateau point
  (if any) against when Scout actually stopped searching that region, or against when a
  human intervened to redirect — would the metric have made a good, earlier stopping
  signal than what actually happened?
- Note whether the pre-run corpus cache state (cleared vs. not) makes the very first
  reading meaningful or artificially inflated — record this as a caveat on the reading,
  not a reason to discard it.

## Recording mechanism

- **Session transcript**: this Claude Code session transcript *is* the AD-27 artifact for
  Story 8.3. Keep the run in one continuous session where practical; if it must span
  sessions, note the break point explicitly in the evidence log so continuity isn't
  silently assumed.
- **Event logs**: researcher copies `<run-dir>/events.jsonl` (and, if useful,
  `manifest.yaml`) out of `_kagami-output/` into
  `_bmad-output/implementation-artifacts/epic-8-evidence/` after the run. The assistant
  can then read that copy freely (it's outside the guarded output root) for graph
  reconstruction and analysis.
- **Metrics**: every `kagami metrics rediscovery-rate` / `charter-audit` / `derived` call
  and its JSON output gets pasted into the evidence log verbatim (they're cheap,
  deterministic, and re-runnable — no reason to summarize instead of quoting).
- **Observations**: use the template below, filled in live during the run rather than
  reconstructed afterward from memory.

## Post-run: evidence log template

Create `_bmad-output/implementation-artifacts/epic-8-evidence/<run-id>-findings.md` with:

```markdown
# Epic 8 Dogfooding Findings — <run-id> (<date>)

## Run summary
Topic, states reached, terminal outcome, rough duration.

## 8.1 Corpus Expand
- Search vs. expand yield comparison:
- Seed-anchoring observed (y/n, detail):

## 8.2 Appraisal Records
- Frame revisions: <count>, re-judging cost each time:
- Card frame-independence violations: <none observed | detail>

## 8.3 Scout Charter Discipline
- Checklist result (see protocol):
- Checkpoint cadence observations:
- `charter-audit` result:

## 8.4 Rediscovery-Rate
- Readings over the run (timestamp/point → sample_size, rediscovery_rate):
- Plateau vs. actual/ideal stopping point:

## Adjudication table update
For each row in `docs/future-scout-redesign.md`'s adjudication table: did this run's
evidence fire it, partially fire it, or not fire it? One line per row.

## Open items
Anything that doesn't fit the above, including any case where the evidence seemed to
call for new implementation — record the observation here; do not act on it in this
session.
```

Repeat for a second and third real run before treating any adjudication-table row as
decided (`future-scout-redesign.md`'s own resumption protocol calls for 2–3 runs before
funding or dissolving any component).
