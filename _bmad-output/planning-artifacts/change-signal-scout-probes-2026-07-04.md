# Change Signal: Scout Exploration Probes (2026-07-04)

## Trigger
The first live dogfooding run (post-Epic 7 golden toy run) exposed weaknesses in Scout's
exploration strategy: one-shot bulk keyword retrieval anchors the corpus on the query's
vocabulary, gives no stopping signal, and offers no way to grow from good papers once
found. A conceptual analysis was produced (`docs/exploration-strategy.md`,
`docs/scout-conceptual-architecture.md`) and a product decision was made: do NOT
redesign Scout now. Instead, land four minimal probes before the next real dogfooding
run. Each probe is small, independently shippable, and doubles as instrumentation whose
evidence will decide whether the larger redesign (recorded in
`docs/future-scout-redesign.md`) is ever built.

**Scope discipline for this change:** no belief store, no frontier data structure, no
allocation policy (UCB), no diversity budget, no checkpoint governor. Any story that
grows toward those is out of scope — they are deliberately deferred pending dogfooding
evidence. Do not redesign Scout.

## Verified state (code inspection, 2026-07-04)
1. `kagami/kernel/scout.py` exposes only `search_corpus` (provider `search` → paper
   cards → one `retrieval` event with `kind: corpus_search`). Scout has exactly one
   sensor: bulk keyword search.
2. The AD-7 port already declares `paper_metadata(canonical_key)` and
   `citation_graph(canonical_key)`, and all four adapters implement them — but no
   kernel code path calls them. The graph sensor exists at the port and is unreachable.
3. `citation_graph` returns `{"canonical_key", "cited_by": [ids]}` — forward citations
   only, bare ids without titles. Backward references are not in the port contract.
   ArXiv/GitHub adapters have no real citation source (empty/degenerate results).
4. `get_or_create_paper_card` (AD-18) already returns a `reused` flag and search
   results already carry it, but nothing aggregates it — rediscovery information is
   generated and then dropped.
5. `search(query, limit=20)` takes a limit; the CLI/charter never lowers it. Scout's
   charter (`agents/scout.md`) contains no iteration or anchor discipline.
6. Paper cards are the only per-paper artifact; there is nowhere to record a
   frame-relative relevance judgment except inside the card itself, which would couple
   a frame-independent fact (AD-18 content-derived, cached forever) to a
   frame-dependent opinion.

## Decisions already made (record these; do not relitigate)
- **PRD:** extend the existing PRD with a small subsection under the Scout/corpus FRs
  ("Scout exploration probes"). Do NOT create a new PRD. New FRs take the next free
  numbers (FR-50 onward); all are mechanically testable at the CLI boundary except the
  charter change, which falls under the existing prompt-artifact testing convention.
- **New FRs:**
  a. **Corpus expand (graph sensor).** A new Scout-only entrypoint
     `kagami corpus expand --run-id <id> --role scout --canonical-key <key>` in
     `kagami/kernel/scout.py`, gated by the same role check and chokepoint as
     `search_corpus` (FR-25 unchanged: Scout remains the sole corpus-touching role;
     this adds a second sanctioned action behind the same gate). Behavior: call
     `provider.citation_graph`, then `provider.paper_metadata` per neighbor id, mint
     cards via the existing `get_or_create_paper_card` path, and append one
     `retrieval` event with `kind: corpus_expand`, the origin paper id, and an
     explicit edge list (`{"from": <paper_id>, "to": <paper_id>,
     "direction": "cited_by" | "references"}`).
     **The edge list in the event payload is the load-bearing decision:** the observed
     citation graph must be fully derivable from the event log (same derived-state
     pattern as `kagami/kernel/derived_state.py`). No graph store, no new artifact
     type. This is what makes the probe a down payment on the future design instead of
     throwaway code.
  b. **Port contract extension.** `citation_graph` returns
     `{"canonical_key", "cited_by": [...], "references": [...]}`; adapters fill what
     their API offers and return empty lists otherwise (arXiv/GitHub legitimately
     empty — that asymmetry is a real provider bias and is fine to expose). At most a
     new testable consequence under the existing corpus FRs; AD-7 is amended, not
     replaced.
  c. **Appraisal records (fact/judgment split).** A new run-scoped artifact:
     appraisal entries of `{paper_id, judgment, frame_version, reason}` written via a
     validated `kagami` entrypoint, plus a hard schema invariant enforced at the write
     chokepoint: **paper cards never contain frame-dependent fields** (no relevance,
     no priority, no judgment). Cards stay frame-independent facts cached forever;
     judgments live in the run, stamped with the frame version that produced them.
     On frame revision, appraisals are re-issued; cards are untouched.
  d. **Rediscovery-rate metric (saturation signal).** A derived-state computation over
     `retrieval` events: fraction of already-seen papers (the existing `reused` flag)
     over the last N retrievals, surfaced wherever run metrics already surface.
     Warn-only reporting, zero behavior change — same posture as the FR-37 token-budget
     checkpoint: deterministic gate-time evidence, not a live control loop.
- **Charter change (no new FR machinery beyond the prompt-artifact convention):**
  `agents/scout.md` gains an iteration discipline — search with a small limit
  (default 5–8, not 20); work in explicit iterations of query → skim cards → decide
  (requery with revised vocabulary / expand an anchor / report back); cap new papers
  per iteration; and name 2–4 anchor papers when reporting to Map. Verified per the
  existing prompt-artifact testing convention (recorded-transcript check + checklist),
  since agent definitions cannot be pytest-verified.
- **Architecture Spine:** amend, never renumber. Expected deltas: AD-7 return-shape
  amendment (decision b); one new AD recording the **fact/judgment separation
  invariant** (decision c) — this is the only genuinely new architectural rule in the
  change, and it exists to keep the door open for the deferred redesign without
  building any of it.
- **Epics:** APPEND Epic 8 to `epics.md`. Epics 1–7 are implemented and traceable —
  preserve verbatim. Update the Requirements Inventory and FR Coverage Map for the new
  FRs only.
- Proposed Epic 8 story cut (refine at story-design time):
  8.1 `corpus expand` kernel op + CLI + port contract extension + edge-carrying
      retrieval event (decisions a, b). Mirrors the existing `corpus search` path in
      shape, tests, and role gating.
  8.2 Appraisal artifact + card frame-independence invariant at the write chokepoint
      (decision c).
  8.3 Scout charter iteration/anchor discipline + transcript verification
      (charter change).
  8.4 Rediscovery-rate derived metric in the existing metrics surface (decision d).
  Ordering: 8.1 and 8.2 before the next real investigation; 8.3 with them (cheap);
  8.4 whenever convenient (read-only).

## Evidence the next dogfooding runs must produce (why these probes, and what they decide)
Each probe instruments a specific open question; the answers adjudicate the deferred
redesign in `docs/future-scout-redesign.md`:
- Does anchor expansion beat re-querying for relevant-papers-per-token? (8.1 events
  make the two sensors' yields directly comparable from the log.)
- Does the corpus show seed anchoring — clusters reachable only from one seed's
  citation basin? (8.1's derivable graph makes this checkable after the fact; persistent
  anchoring is the evidence that would fund the diversity-reserve component.)
- Does the rediscovery rate actually plateau when a region is exhausted, and would it
  have made a good stopping signal? (8.4; funds the saturation/stopping machinery.)
- How often does the frame move mid-run, and what did re-judging cost? (8.2's
  frame-stamped appraisals; funds the full belief-store split.)
- What checkpoint cadence does iterative search naturally want? (8.3 transcripts; funds
  the governor design.)
