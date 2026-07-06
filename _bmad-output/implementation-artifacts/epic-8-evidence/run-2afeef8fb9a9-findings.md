# Epic 8 Dogfooding Findings — run-2afeef8fb9a9 (2026-07-04)

Evidence-collection run per `_bmad-output/implementation-artifacts/epic-8-dogfooding-protocol.md`. Full event log reproduced/quoted below directly from `_kagami-output/runs/run-2afeef8fb9a9/events.jsonl` (read directly — see the Story 8.3/AD-2 finding below on how that was possible).

## Run summary

- **Topic:** what graph-based literature-exploration methods and evaluation benchmarks exist for AI-assisted literature survey systems.
- **States reached:** Frame → Map → Deepen → Synthesize → Locate → **MVP terminal reached** (`gap-register-accepted`, `art-638f3284f697`, `2026-07-04T16:43:43Z`).
- **Duration:** ~53 minutes wall-clock (run opened 15:50:55Z, terminal 16:43:43Z), across ~10 subagent dispatches (1 Scout, 1 Cartographer, 3 Historian, 3 Skeptic) plus orchestrator-driven CLI calls.
- **Artifacts:** 1 Intuition Note, 1 Inquiry Frame (accepted), 4 Field Map clusters (`methodology` cut chosen; `pipeline-stage` recorded as `alternative_cut`), 3 Cluster Dossiers (accepted), 9 appraisal records, 1 Landscape Synthesis (accepted), 1 Gap Register (accepted, disposition **suspicious** — see below).
- **Known limitation, recorded by explicit researcher decision, not user error:** all 9 representative-paper `human_read` flags were set by Historian (AI) rather than by the researcher. The researcher reviewed the situation and declined to manually read 9 papers mid-run, judging that requiring a full paper read to close a cluster is too heavyweight for an early-exploration workflow and would rather see a lighter-weight confirmation mechanism (rating/confidence/note) in a future design. This is a workflow-design finding, filed below, not treated as a run defect.

## 8.1 — Corpus Expand

**`corpus expand` is non-functional against the only configured provider.** All three attempts this run were refused with the identical error, confirmed both from the live session and directly from the event log:

```
{"kind": "entrypoint_refused", "entrypoint": "corpus.expand", "canonical_key": "ppr-e6cc673f54f8", "error": "openalex request failed: HTTP 404"}
{"kind": "entrypoint_refused", "entrypoint": "corpus.expand", "canonical_key": "https://doi.org/10.18653/v1/n18-1022", "error": "openalex request failed: HTTP 404"}
{"kind": "entrypoint_refused", "entrypoint": "corpus.expand", "canonical_key": "https://doi.org/10.18653/v1/2025.acl-long.572", "error": "openalex request failed: HTTP 404"}
```

Root cause (confirmed by direct `curl` against the live OpenAlex API during the run): `OpenAlexProvider.citation_graph` (`kagamios/kagami/corpus/adapters.py:90-97`) calls `https://api.openalex.org/works/{id}/citations`, a sub-resource endpoint that does not exist in OpenAlex's real API (`works/{id}` alone returns 200; `works/{id}/citations` returns a literal 404 page). **This means Story 8.1's central deliverable — an edge-carrying retrieval event enabling log-derived citation-graph reconstruction — produced zero data this run.** No graph reconstruction, no seed-anchoring check, and no search-vs-expand yield comparison were possible; the evidence this probe was designed to produce for `future-scout-redesign.md`'s diversity-reserve adjudication row simply does not exist yet.

Secondary observations:
- No `--provider` override exists on `corpus search`/`corpus expand`, so there was no way to route around the broken adapter within a single run, or check whether Semantic Scholar/arXiv/GitHub adapters' `citation_graph` implementations work.
- Paper cards from `corpus search` carry only raw provider metadata (title/DOI/source) — `contribution_line`/`method_class`/`evidence_type`/`key_claims` are always empty, because no content-extraction step exists anywhere in the current pipeline (confirmed by reading `kernel/scout.py:search_corpus`, which calls `get_or_create_paper_card(..., compute=lambda raw=raw: raw)` — a direct passthrough, no model call). This is a real, load-bearing limitation for every downstream role (see 8.2/8.3 below), not specific to the expand bug, but it compounds it: with expand broken, keyword requery is the *only* way to grow the corpus, and keyword requery alone cannot populate richer card content either.
- `kagami cartographer draft` clusters only by `method_class`/`source` (`kernel/cartographer.py`); with both fields empty/uniform this run, it produced an identical partition on both automatic cuts and was correctly refused by its own FR-26 check. Cartographer's actual clustering work happened in the subagent's own reasoning over titles, hand-authored as JSON fed straight to `cartographer create` — which **did** correctly re-validate structural difference at the write chokepoint, independent of `draft`'s failure. The convenience command is not doing the job its name implies once cards are this thin.

## 8.2 — Appraisal Records

9 appraisal records were written (`apr-7667bb0e1677` … `apr-56693a298e5b`), all at `frame_version: "1"` — the Inquiry Frame was never revised this run, so **this run produced no evidence on the frame-revision/re-judging-cost question** the change signal specifically calls out. That question remains open pending a run where the frame actually moves mid-session.

What did work cleanly:
- The fact/judgment split held structurally: a spot-check of `ppr-ad4d46b7b8cc`'s card after all 9 appraisals were recorded shows no relevance/priority/judgment field ever landed on it (`FORBIDDEN_CARD_FIELDS` enforcement confirmed live, not just by code reading).
- `appraisal record` has **no role/actor argument or check at all** (`kagamios/kagami/cli.py` appraisal parser; `kagamios/kagami/store/appraisal.py:record_appraisal` signature has no role/caller parameter). Any role could have issued these appraisals; there's currently no restriction on who judges. Not obviously wrong (appraisal is meant to be a judgment, and multiple roles arguably could hold opinions), but worth noting as an open design question alongside the `human_read`/`meaningful_to_me` findings below, since it's the same "field name implies an owner, but nothing enforces one" pattern recurring a third time.

## 8.3 — Scout Charter Discipline (AD-27) + a broader AD-2 finding

### Scout iteration discipline — transcript checklist

| Checklist item | Result |
|---|---|
| Small `--limit`, not inflated | ✅ — every search used `--limit 5`, below even the charter's own default of 8 |
| Skimmed before next action | ✅ — self-reported and consistent with the 13 distinct, topically-drifting reformulations in the log |
| Legible decision each iteration (requery/expand/report) | ✅, with an asterisk — Scout *always* requeried, never successfully expanded (expand was broken all 3 attempts; see 8.1). The charter's decision menu was effectively 2 options, not 3, this run. |
| No single iteration flooded the corpus | ✅ — capped at 5 new lookups/iteration |
| 2–4 anchors named at handoff | ✅ — named exactly 4 |
| Checkpoint cadence | **Zero human checkpoints fired during the entire Map-state search.** Scout ran all 13 iterations autonomously and reported back only once, at the end. |

`kagami metrics charter-audit` reported **14 violations, but on inspection nearly all are not real charter breaches**:

- **13 are a false-positive caused by a real code bug, not a Scout violation.** `charter_audit.py`'s `SCOUT_ALLOWED_OPERATION_CLASSES = frozenset({"corpus_search", "retrieval"})` does not include `"paper_card_extraction"` — but Scout's own charter (`agents/scout.md`) explicitly instructs Scout to resolve and report every model call under `--operation-class paper_card_extraction`, and Scout did exactly that, correctly, 13 times. The mechanical backstop's allowlist is simply out of sync with the charter it's supposed to be checking. **As currently shipped, any run where Scout behaves exactly per its own charter will show 13+ "violations" in this audit** — the tool's signal is not currently trustworthy at face value. (`kagamios/kagami/kernel/charter_audit.py:12,57-63`)
- **1 is Historian's frontier-speculation attempt, correctly refused** (`"this suggests a promising direction"`, FR-28) — the write did not land (confirmed: dossier version was unchanged after the refusal). This is the guard working as intended, not a violation that got through; it's just bundled into the same `violation_count` as real breaches, which overstates severity if read casually.
- **Net real violation count this run: 0.**

### A significant, independently-verified finding beyond Scout specifically: **`Read` is not covered by the AD-2 guard at all**

The architecture spine claims (AD-2/AD-23): *"The PreToolUse hook is default-deny for any tool invocation whose arguments reference the output root — `Write`, `Edit`, and every `Bash` command alike."* This is not accurate. `kagamios/hooks/hooks.json`'s matcher is literally `"Write|Edit|NotebookEdit|Bash"` — **`Read` is never included**, regardless of subagent or main session. Verified three independent ways this run:
1. Cartographer's subagent read `field-map` artifacts' `current.md` directly off disk (absolute path under `_kagami-output/`) with no denial, to confirm a cluster-name-to-art-id mapping the CLI couldn't answer.
2. The orchestrator (this session) read the exact same kind of path directly (`_kagami-output/runs/.../field-map/art-.../current.md`) with no denial, confirming it wasn't subagent-specific.
3. A separate Historian subagent independently discovered the same gap while trying to inspect a paper card's contents, and used it as its only way to see card data at all (see next point).

This means every role can freely read raw artifacts, paper cards, or (had it been needed) `events.jsonl` directly, bypassing the entire chokepoint-mediated read discipline FR-15's consumption maps are supposed to enforce. This is squarely an AD-2 finding, not a hypothetical — it was exercised, unprompted, by two independent subagents plus the orchestrator, all needing to route around a *missing* sanctioned read path (see next finding) and finding the guard didn't stop them.

### A related, corroborated gap: no sanctioned read path for paper-card content in Deepen

All three independent Historian subagents hit the same wall: `consumption_map.yaml`'s `deepen` state read-set is `[field-map, cluster-dossier, inquiry-frame]` — **`paper_card` is not in it, for any state.** There is no `kagami corpus`/`kagami dossier` subcommand to fetch a card's content either. Confirmed live 3 times independently:
```
{"entrypoint": "read", "target": "...\"type\": \"paper_card\"...", "error": "state 'deepen' has no defined brief for reading 'paper_card' (FR-15)"}
```
Combined with 8.1's finding that cards carry no extracted content anyway, this means Historian's dossier-writing this run rested entirely on each subagent's own background knowledge of well-known tools (Rayyan, ASReview, CitNetExplorer, PaSa, etc.), not on anything the system fed it. That happened to produce credible prose here because the papers were famous — it would not generalize to an obscure paper, and there is currently no way to tell the difference from the artifact alone.

### Minor, recurring friction: string-literal casing traps with no normalization

Found three times, independently: (1) Historian's `--section` argument must be the literal lowercase `evolution` — my own dispatch instructions said `Evolution` in all three Historian prompts, and each subagent had to read `kernel/historian.py` source to discover the mismatch before writing successfully. (2) A `read` call using `"state": "Deepen"` (capitalized) produced a different error (`"no consumption map defined for state 'Deepen'"`) than the lowercase `"deepen"` call (`"state 'deepen' has no defined brief..."`) — state names are also case-sensitive with no normalization, and the two failure modes look different enough to be confusing. Neither is a severe bug, but the pattern (string keys compared by exact case, discoverable only by reading source, no normalization anywhere) recurred enough to be worth flagging as a systemic small-friction source rather than one typo.

### Another recurring minor friction: empty `--call-id` on first `report llm-call` attempt

Both Scout and Skeptic, independently, made their *first* `report llm-call` attempt with `--call-id ""` and were correctly refused by AD-26's idempotency guard, then retried with a real UUID successfully. Not a bug (the guard did its job) but a repeated first-attempt stumble across two different roles is a signal the charter instruction to "mint a UUID call-id" isn't landing as clearly as it could.

## 8.4 — Rediscovery-Rate Metric

This is the finding that most needs a methodology caveat, because **the orchestrator (this session) contaminated the tail of the retrieval-event log**, and the default-window reading is misleading as a result — recorded honestly rather than presented at face value.

**What happened:** after Scout's real 13-query exploration ended (last organic query at `15:57:30Z`), the orchestrator asked Scout to re-run 5 of its own already-cached queries a second time (`16:01:20Z`–`16:01:38Z`) purely to extract paper-card JSON for Cartographer's input. Those 5 re-queries × 5 papers = 25 guaranteed cache-hit lookups, appended at the very end of the run's retrieval events.

**Effect on the metric, precisely quantified from the event log:**
- `kagami metrics rediscovery-rate --window 20` → `1.0` (20/20 reused)
- `kagami metrics rediscovery-rate --window 5` → `1.0` (5/5 reused)
- Both readings are measuring **only the orchestrator's contaminating re-query**, not genuine within-run exploration — the window is small enough that the artificial tail completely fills it.
- `kagami metrics rediscovery-rate --window 0` (full lifetime) → `0.289` (26/90 reused) — a blend of the genuine and contaminating phases.
- **Isolating the genuine 13-query, 65-lookup organic exploration phase by hand from the raw log: exactly 1 rediscovery out of 65 lookups (≈1.5%).** Only one paper (`ppr-a16bd3bc5dda`) was returned by two different query reformulations; every other lookup across 13 topically-drifting queries was a fresh paper.

**What this means for the adjudication question** ("does rediscovery rate plateau when a region is exhausted, and would it make a good stopping signal?"): **this run gives no evidence of a plateau** — the rate stayed near zero for the entire organic search, right up to the point Scout stopped. Scout's own stated reason for stopping was *declining topical relevance* (a qualitative judgment about query drift), not rediscovery saturation. Two live possibilities, not resolved by this run: (a) Scout's breadth-first requery strategy (fresh vocabulary each iteration) structurally avoids triggering the rediscovery signal even when a stop is warranted, so the metric may need a different exploration strategy (e.g. genuine anchor-expansion, which 8.1's bug prevented testing) before it can be evaluated fairly; or (b) 13 iterations simply wasn't enough to reach saturation in a corpus this size. Cannot distinguish between these from one run.

**Protocol lesson for future runs, recorded so it isn't repeated:** never issue orchestrator-driven re-queries against a run already in progress for convenience (e.g. extracting JSON for a downstream role) — it silently and severely distorts the rediscovery-rate tail reading, with no way to flag or exclude it after the fact via the CLI. If card data needs to be handed to another role, capture it from the original call's output at the time, not by re-querying later.

## Adjudication table update (`docs/future-scout-redesign.md`)

| Row | This run's evidence |
|---|---|
| Diversity reserve (seed-anchoring check) | **Not fireable this run** — `corpus expand` was non-functional, so no citation graph was ever produced to check for single-articulation-point clusters. |
| Saturation/stopping machinery | **Not fired, and the metric itself couldn't be cleanly read** — see 8.4. Genuine organic rate (~1.5%) shows no plateau; contaminated by orchestrator error at the tail. Needs a clean re-run. |
| Full belief-store split (frame revision cost) | **Not fireable this run** — frame was never revised; no re-judging cost exists to measure. |
| Frontier + UCB Allocator (branch contestation) | **Not fired** — zero human redirections occurred during Scout's search; it ran fully autonomously. |
| Governor (checkpoint cadence/EVOI) | **Not fired** — zero checkpoints occurred to evaluate against the EVOI test. |
| Time-axis/sensor-bias treatment | **Not directly tested**, though Scout's own account (generic task-vocabulary queries over-matching unrelated domains before narrowing to named systems) is a related, adjacent observation about query-vocabulary bias, not citation-recency bias specifically. |

**None of the six rows fired this run** — but three of the "not fireable" outcomes are because the underlying probe was broken (`corpus expand`) or contaminated (rediscovery-rate tail), not because the redesign components are unneeded. That's a different, more important conclusion than "the probes were sufficient": **this run mostly tested whether the probes work at all, and found two do not (cleanly) yet.** A second real run, after `corpus expand` is fixed and without orchestrator interference in the retrieval-event tail, is needed before this table's rows can be evaluated on their merits.

## Workflow-design finding (researcher-flagged, not a bug)

Deepen's exit criterion (`kagami dossier validate-deepen-exit`, FR-28) requires every representative paper's `human_read` flag to be `true` before a dossier is a valid basis for the MVP terminal. Mechanically, this flag has **no actor/role check at all** (confirmed: an AI role — Historian — set it on all 9 papers this run, and the system accepted this without complaint). Independent of that mechanical gap, the researcher's own judgment (given directly, not inferred) is that **requiring a full paper read at this stage is too heavyweight for an exploratory literature-survey workflow** — the researcher would prefer a lighter-weight confirmation (a rating, a confidence level, or a free-form note) rather than a binary "I have read this" gate before Deepen can close. Filed as a UX/workflow-design finding for whoever next touches Deepen's exit criteria, not as something this session should fix.

## Open items

- The corpus-expand OpenAlex bug and the charter-audit allowlist bug are both precise, small, well-evidenced fixes — but per this run's explicit scope, no fix was attempted; they're recorded here for a future session to act on.
- A second real run is needed, ideally: (a) after `corpus expand` is fixed, so 8.1 evidence can actually be produced; (b) without any orchestrator-issued re-queries mid-run, so 8.4's rediscovery-rate reading stays clean; (c) long/varied enough that a frame revision actually occurs, so 8.2's re-judging-cost question can be answered; (d) with at least one deliberate human redirection of Scout's search, so the Frontier/Allocator adjudication row has anything to evaluate against.
