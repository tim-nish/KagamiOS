# Reviewer Gate — Version & Reality Check (Epic 7 delta: AD-26, AD-27, AD-4/AD-11 amendments)

- **Target:** `ARCHITECTURE-SPINE.md` — new AD-26/AD-27 sections, the AD-4 "v1-driver amendment" and AD-11 "role attribution is harness-self-reported" additions, plus a staleness re-check of the existing `## Stack` table.
- **Lens:** every committed decision web-researched or reality-checked, not asserted from training data.
- **Date:** 2026-07-03
- **Method:** WebSearch against live sources today; full-file read of `ARCHITECTURE-SPINE.md`; cross-read of `prd.md` (§4.6, §4.7, §4.8, §5), `addendum.md` (A4), `epics.md`, and `change-signal-epic7-2026-07-03.md`; inspection of `/opt/claude-commands/implement-issue.md` (the convention AD-27 says it extends).

## Verdict

**Pass, with minor fixes requested.** No fabricated or unverifiable Claude Code capability was found in AD-26/AD-27 — the "real Claude Code session transcript … attached to the PR" claim rests on genuine, confirmed platform behavior (native `/export`, per-session JSONL transcripts under `~/.claude/projects/`, `isSidechain` tagging for subagent turns), not an invented feature. The FR/AD cross-citations in AD-26 and AD-27 are substantively accurate against what those FRs/ADs actually say elsewhere in the file. The existing `## Stack` table (dated "verified current 2026-07-02/03") holds up against fresh searches today (2026-07-03); nothing has gone stale in the one-day gap, and it already reflects corrections from an earlier version-review pass (Semantic Scholar, PyYAML, OpenAlex, GitHub rows all match current live data). Two small citation-precision issues and one fragile informal reference are worth fixing before this is fully clean.

## 1. Technology/mechanism claims in AD-26/AD-27 that needed verification — checked against live sources

| Claim | Location | Verified against | Result |
| --- | --- | --- | --- |
| A real Claude Code session transcript can be produced and attached to a PR as evidence | AD-27(a) | Claude Code docs + community tooling: native `/export <file>` writes the full conversation to disk; sessions persist as append-only `.jsonl` under `~/.claude/projects/<project>/`; subagent-spawned turns are tagged `isSidechain: true`, separable from the main thread | **Real capability, not fabricated.** Nothing here requires an unverified or invented mechanism. |
| PreToolUse hooks can deny a tool call (`exit-2` / `permissionDecision: "deny"`) — load-bearing for AD-2/AD-26's "ceiling must live in the core" reasoning | Stack row; referenced by AD-26's AD-1 justification | Current Claude Code hooks docs | **Confirmed.** Exit code 2 blocks the call (stderr fed back as error); JSON `hookSpecificOutput.permissionDecision: "deny"` on exit 0 is the second, independent mechanism. Both exist as documented. |
| Subagent `model` frontmatter is static; resolved at launch time (underpins AD-12, referenced by AD-26 indirectly via dispatch table) | Stack row | Claude Code sub-agents docs | **Confirmed.** Resolution order is env var (`CLAUDE_CODE_SUBAGENT_MODEL`) → per-invocation parameter → frontmatter → `inherit`. A skill can set the model at launch time via the invocation parameter/env var, which is exactly what AD-12's "resolves the model at launch time from config + dispatch table" requires. |
| Plugin-shipped subagents ignore `hooks`/`mcpServers` frontmatter | Stack row | Claude Code plugins-reference docs | **Confirmed.** Documented, intentional security restriction; plugin-level hooks (`hooks/hooks.json`) are unaffected, consistent with the spine's use of plugin-level (not per-agent) hooks. |

No claim in AD-26 or AD-27 asserts a Claude Code capability that isn't real. The one candidate for over-claiming — "a real Claude Code session transcript … attached to the PR" — is appropriately hedged as a Definition-of-Done *process* (produce a transcript, attach it), not a claim about a specific built-in "attach to PR" feature Claude Code doesn't have. That framing is accurate.

## 2. AD/FR cross-citation check

Checked every AD-26/AD-27 citation (AD-1, AD-15, AD-22, AD-25, AD-11, FR-48, FR-49, FR-37) against the actual text of that AD/FR elsewhere in the file, plus the underlying PRD FRs.

- **AD-26 ↔ FR-48:** accurate. PRD FR-48: "tracks consecutive identical refusals against the same target; past a fixed ceiling, the next identical attempt returns a distinct escalation status." AD-26(a) matches exactly, adding the `(entrypoint, target)` grouping and the concrete status name `requires_researcher` — both are architecture-level refinements consistent with, not contradicting, FR-48's text.
- **AD-26 ↔ FR-49:** accurate. PRD FR-49 requires role/operation_class/model_tier/token counts/cache-hit reported "through a validated entrypoint immediately after the call," core "never invokes models itself and never infers these fields." AD-26(b) reproduces this precisely and correctly frames it as "AD-22's `needs_llm` protocol run in reverse."
- **AD-26 ↔ FR-37:** accurate. PRD FR-37's consequence: "the token ledger is compared against a researcher-set soft limit in `config.yaml`; exceeding it adds a warning to the decision block, never a block on proceeding." AD-26(c) restates this near-verbatim and correctly cross-links the NFR5/addendum-A4/O6 non-reopening language, which matches `addendum.md`'s own "2026-07-03 addition" note on A4 nearly word for word ("not the O6 trigger firing," "sequenced, not in tension").
- **AD-26 ↔ AD-1:** accurate. AD-1's rule ("All mechanical guarantees … are implemented in the Python core, never in prompts … no rule may exist only in a SKILL.md") directly supports AD-26's "the ceiling must live in the core, not skill prose per AD-1" reasoning.
- **AD-26 ↔ AD-15:** accurate. AD-15 covers "every mutating entrypoint" acquiring the run lock; tracking a refusal counter is itself a state mutation, so locking it under AD-15 is consistent, if implicit (AD-15's text doesn't explicitly address refusal-counter writes, but nothing in it excludes them).
- **AD-26 ↔ AD-22:** accurate. AD-22's two-pattern protocol (schema-validated input argument, or `needs_llm` work item fulfilled through a validating entrypoint) is correctly characterized as running "in reverse" for `llm_call` reporting.
- **AD-27 ↔ AD-25 — imprecise.** AD-27's rule states "AD-25 verifies `kagami/` only," and AD-11's honest-gap entry repeats this as "AD-25 covers only `kagami/`." But AD-25 itself, three sections earlier in the same file, states its **Binds** line as `kagami/` test suite; **hooks**; AD-5's standalone claim, and its Rule explicitly says "Hooks are tested against recorded PreToolUse payloads." So AD-25 covers `kagami/` **and** `hooks/`, not `kagami/` only. The functional point AD-27 is making (that `skills/` and `agents/` specifically fall outside AD-25's suite) is correct and the hooks/skills-agents split is a sensible one (hooks are deterministic and replayable against recorded payloads; skills/agents involve live model behavior and can't be). But the literal sentence "AD-25 covers only `kagami/`" is contradicted by AD-25's own binds line. **Recommend:** reword to "AD-25 verifies `kagami/` and `hooks/`; `skills/` and `agents/` fall outside that suite" in both AD-11 and AD-27.
- **AD-11 ↔ AD-4 (self-citation) — minor ambiguity.** AD-11's honest-gap entry reads: "…AD-4's session/engagement-token machinery is deferred (AD-26)." The parenthetical `(AD-26)` sits immediately after "is deferred," inviting a reader to think AD-26 is the source/authority for the deferral decision. In fact the deferral itself is recorded only in AD-4's own "v1-driver amendment" paragraph; AD-26 is merely the mechanism (the reporting entrypoint) used for the interim self-reported-role workaround. **Recommend:** either drop the parenthetical or change it to "(interim reporting via AD-26)" to remove the ambiguity.
- **AD-26's "NFR5" reference — fragile, not wrong.** AD-26's Prevents clause cites "the NFR5/addendum-A4 deferral." The PRD's §5 "Cross-Cutting NFRs" is an unnumbered bullet list; "Cost discipline via retrieval boundaries, not budgets" is the 5th bullet, so "NFR5" is correct *by position today*. But the PRD does not itself label these bullets NFR1..NFR5 anywhere, so this is an informally-invented numbering that would silently point at the wrong bullet if the PRD's list is ever reordered or a bullet inserted/removed. Content-wise it's currently accurate (confirmed by reading §5 in full); flagging only as a fragile-reference risk, not a present error.
- **All other AD-26/AD-27 binds** (agents/skills paths, Epic 7 story acceptance criteria, FR-37/48/49) check out against `epics.md` and `change-signal-epic7-2026-07-03.md`, which record the same decisions (retry ceiling, `llm_call` reporting entrypoint, FR-37 budget checkpoint, AD-25-covers-core-only framing, transcript+checklist+golden-toy-run DoD) essentially verbatim — the spine is a faithful architecture-level rendering of the change signal.

One further observation (not a citation error, informational only): the Dependency-direction Mermaid diagram still labels `BRIEFS[kagami/briefs — read-set bundles, engagement tokens]` without a footnote that engagement tokens are deferred per AD-4's v1-driver amendment. That's defensible as "target shape, not current-epic shape," but a reader skimming only the diagram could miss that tokens aren't live yet in Epic 7.

## 3. Stack section re-check for 2026-07-03 staleness

The Stack table is dated "verified current 2026-07-02/03." Re-ran fresh searches today; nothing has moved in the one-day window, and the table already carries fixes visible in the repo's own earlier `review-versions.md` (Semantic Scholar rate limits, PyYAML round-trip caveat, OpenAlex key requirement, GitHub token/rate-limit note — all previously flagged there and now present in the current Stack table).

- **Python:** current stable is 3.14.6 (released 2026-06-10); table says "≥3.12 (3.14.x current)" — still accurate.
- **pydantic:** latest stable is 2.13.4 (April/May 2026); a 2.14.0a1 pre-release exists but nothing stable supersedes 2.13.x yet — table's "2.13.x" still accurate.
- **PyYAML:** latest is 6.0.3 (Sep 2025); table's "6.x — cannot round-trip comments" still accurate, and the caveat from the prior review is now baked into the table's own wording.
- **OpenAlex:** Feb 24, 2026 usage-based pricing announcement and Feb 13, 2026 mandatory-API-key requirement both independently confirmed; table matches.
- **Semantic Scholar:** keyless shared-pool + ~1 RPS dedicated free-key tier confirmed against `s2-folks/API_RELEASE_NOTES.md` (last officially updated Nov 2024, no report of a subsequent change); table matches.
- **arXiv:** the "429 tightening reported since Feb 2026" note is corroborated by an active arXiv API mailing-list thread describing a Feb 25–26, 2026 spike in 429s with arXiv confirming increased capacity and an outstanding fix — table's hedged wording ("reported since," not "resolved") remains accurate as of today.
- **GitHub search API:** ~30 req/min for authenticated search confirmed current.
- **uv:** table deliberately pins no version ("current"); nothing to falsify.

No stale entries found in the Stack table as of 2026-07-03.

## Corrections requested (summary)

1. **AD-11 and AD-27:** reword "AD-25 covers/verifies only `kagami/`" to "AD-25 covers `kagami/` and `hooks/`" (AD-25's own Binds line and Rule text include hooks; the current wording is contradicted by AD-25 itself).
2. **AD-11:** clarify the `(AD-26)` parenthetical after "AD-4's session/engagement-token machinery is deferred" — it currently reads as citing AD-26 for the deferral decision, when the deferral is recorded in AD-4 and AD-26 only supplies the interim reporting mechanism.
3. **Optional/low-severity:** anchor "NFR5" to something more durable than positional order in the PRD's unnumbered §5 bullet list (e.g., quote the bullet's opening words alongside the number), so a future PRD edit can't silently break the reference.
4. **Optional/informational:** a one-line footnote on the Dependency-direction diagram noting engagement tokens are deferred for Epic 7 would remove the only place in the file where the v1-driver amendment isn't visible.

No AD is invalidated by this pass. AD-26 and AD-27 are grounded in real, verified Claude Code platform behavior, and their FR/AD citations are substantively correct.
