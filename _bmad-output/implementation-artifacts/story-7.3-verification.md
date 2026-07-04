# Story 7.3 Verification — Role Agent Definitions with Read-Set-Compliant Context

Per AD-27, `agents/*.md` are prompt artifacts, not pytest-verified. This is the checklist review AD-27 requires: each agent definition checked against its FR-25..29 charter for any tool or content grant that exceeds it.

## Charter checklist

| Role | FR | Tool grants match charter? | Content restriction stated? | Enforcement lives in core, not just prose? |
|---|---|---|---|---|
| Scout | FR-25 | Yes — only Scout has `WebFetch`/`WebSearch`; every other role has `Bash, Read` only | Told explicitly not to interpret/synthesize | Yes — `search_corpus` refuses `role != "scout"` (`kagami/kernel/scout.py`), independent of what the prompt says |
| Cartographer | FR-26 | `Bash, Read` — no write beyond `cartographer create` | Told never to pick a winner; told cluster names are always human-editable | Partial — the store refuses a single-clustering draft, but "never pick a winner" is currently prose discipline, not a mechanical check (no code prevents Cartographer from writing "I recommend cut A" into a section body) |
| Historian | FR-28 | `Bash, Read` — writes only through `historian write` | Told Evolution-only, told frontier speculation is forbidden even there | Yes — `historian_write` refuses any section but `evolution`, and `detect_frontier_speculation` refuses common speculative phrasing mechanically |
| Skeptic | FR-27 | `Bash, Read` — writes only through `skeptic critique`/`skeptic write` | Told never to propose, told fresh-context is structural (Agent-tool isolation), told not to ask for the authoring conversation | Yes — `skeptic_write` refuses every field but `candidate-direction.red_team_notes`; `build_skeptic_context` mechanically omits `elicited_from`. Fresh-context itself relies on Claude Code's own subagent isolation (no shared conversation state by construction) — recorded as the mechanism, not asserted as guaranteed by this repo's code |
| worker | FR-46, FR-4 | `Bash, Read` — writes only through `synthesize write`/`locate write` | Told no direction-shaped content pre-Gap-Register, told no override on `author: human` fields | Yes — `synthesize_write` refuses any field but `solved_open_table`; `locate_write` refuses via the generic FR-31 write-guard for human-only fields; FR-46's window enforcement is store-level (AD-9), not this file |

## Findings

1. **Cartographer's "never pick a winner" is currently prose-only.** Every other role's forbidden action has a corresponding mechanical refusal somewhere in `kagami/kernel/`. Cartographer's does not — nothing stops it from writing recommendation language into a cluster's description field. This is a real gap, not fabricated as closed: recorded here rather than silently accepted, and a candidate for a follow-up story if it proves to matter in practice (Story 7.5's toy run is a natural place to check whether it actually does).
2. **`worker`'s dossier non-Evolution write path doesn't exist yet.** `agents/worker.md` documents this explicitly rather than inventing a plausible-looking command that would fail at runtime — AD-4 names this as worker's domain, but Epic 3's stories built Historian/Skeptic/parallel-claims, not a generic dossier-content entrypoint. Flagged in the agent file itself so a future session doesn't waste a turn discovering it the hard way.
3. **Skeptic's fresh-context guarantee is a platform property, not a KagamiOS one.** `agents/skeptic.md` is explicit about this: launching Skeptic via the Agent/Task tool as a subagent is what actually prevents it from inheriting the authoring conversation, not any code in this repository. If a future harness change ever let a subagent share parent context by default, this charter's enforcement would silently weaken — worth a comment at the point such a platform change would be adopted, not actionable today.
4. **All five files reference `kagami dispatch resolve --operation-class <X>` for launch-time model resolution**, and every operation class named matches an entry in `schemas/dispatch.yaml` (Story 7.2) — checked by grep, not just written and hoped correct: `paper_card_extraction`, `cluster_naming`, `dossier_drafting`, `skeptic_critique`, `synthesis_drafting`, `gap_register_drafting` all resolve.

## Code change alongside the agent files

While writing these, found that `kagami report llm-call`'s `--role` argument (built in Story 7.2) only checked for non-empty, not membership in an enumerated role set — which Story 7.3's own AC requires ("must be one of the schema-registry-enumerated roles, refused otherwise"). Added `ROLES` to `kagami/registry.py` and tightened `report_llm_call` to validate against it, with two new tests (`test_an_unrecognized_role_is_refused_not_accepted_as_free_text`, `test_every_ad4_role_plus_interviewer_is_accepted`). This is a small scope extension of 7.2's own AC, discovered and closed here rather than left half-built.

## Test suite

`355 passed` (2 new: the role-enum tightening above; the 5 agent `.md` files themselves are not exercised by pytest per AD-27).
