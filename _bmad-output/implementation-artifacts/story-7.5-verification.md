# Story 7.5 Verification — The Golden Toy Run

Protocol: `golden-toy-run-protocol.md` (same directory). Executed for real against a scratch `KAGAMI_OUTPUT_ROOT`, driving the actual `kagami` CLI through every state Frame→Map→Deepen→Synthesize→Locate to an accepted Gap Register, using the exact entrypoints Stories 7.1–7.4 built or wired. Run id `run-toy-icl`.

## What "driven through the harness" means in this execution — stated precisely

I drove the CLI sequence myself, playing each role and reporting `llm_call` events under the correct role tag, rather than spawning `agents/*.md` as literal, separate Claude Code subagent sessions via the Agent tool. This is a real limitation of this execution, not a claim of full parity with a live multi-subagent Claude Code session — the same category of honest gap Story 7.1 already recorded (this session doesn't have the `kagamios` plugin installed via Claude Code's own mechanism, so a true multi-subagent session wasn't available to drive this from). What this execution *does* prove: every entrypoint the harness stories (7.1–7.4) built is individually correct and composes correctly end-to-end against real content, under real role attribution, producing a real event log — which is the load-bearing part AD-27's rubric evaluation below actually needs.

## Sequence executed

Frame (intuition capture → ask-before-show unprimed question → accepted Inquiry Frame) → Map (Cartographer drafted 2 structurally different cuts, `method_class` chosen, 4 Field Maps created, depth budget set to 2 of 4 clusters) → Deepen (2 clusters: Historian wrote Evolution, 2 representative papers each marked `human_read` with real reactions, Skeptic critiqued each dossier from its restricted context, both dossiers accepted, both passed `validate-deepen-exit` clean) → Synthesize (solved/open table drafted from both accepted dossiers, accepted) → Locate (Gap Register drafted and accepted, `meaningful_to_me` marked by the researcher) → MVP terminal reached.

8 `llm_call` events reported across `interviewer`, `cartographer`, `historian` (×2), `skeptic` (×2), `worker` (×2) — every role except `scout` (no live corpus search in this protocol — see protocol doc) reported at least one call.

## Rubric evaluation

**Refusal → correction pattern (never refusal → identical retry).** Three genuine refusals occurred, all real, none anticipated in advance:
1. `accept` on the Landscape Synthesis: summary was 4 lines, needed 5–10 (FR-33). Corrected with a longer, different summary on the next call — a different target, not a retry.
2. `locate write --field why_does_this_gap_exist`: refused with "no section named...". Traced to a real bug in my own `create_gap_register` (see Findings #1 below), fixed, then succeeded against a freshly-created artifact.
3. `dossier validate-deepen-exit` initially showed up as a "refusal" in the ceiling's own log — this was itself a bug in the ceiling logic (Finding #2), not a real refusal; fixed before this doc was finalized.

No identical retry ever occurred. The ceiling was never actually crossed in this run (nothing repeated 3 times identically) — a `requires_researcher` escalation was exercised separately in Story 7.4's own unit/CLI tests, not needed here since every real refusal in this run was followed by a genuinely different, corrected call.

**Question Ledger `consumed_by` coverage.** Both ledger entries from Frame (the unprimed question and the scope question) show `consumed_by_count: 1` in `kagami metrics derived`'s `question_economics` — 2/2, full coverage.

**Override profile.** `gap-register` shows `override_rate: 0.5` (1 of 2 accepted gap-registers has a `human_edit`) — this is `meaningful_to_me` being a genuine human-only write, correctly counted, though arguably `compute_override_rate`'s framing ("overridden") is a slight semantic mismatch for a human-only field completion versus an actual override of AI-drafted content; a pre-existing Story 6.1 framing question, not something this story changes. All other types show `override_rate: 0.0` — no human edits were needed to correct any AI draft in this toy run, which is itself a plausible, unremarkable finding for a run this short.

**`premature_ideas/` volume.** Zero — the directory doesn't exist. No generation-window violation was attempted or triggered (this toy run's protocol never reached Propose, so this is expected, not a strong signal either way).

**Known-cluster-miss check.** Deliberately planted per the protocol: Hendel et al. 2023's task-vector account of ICL was knowingly excluded from the six-paper corpus. The resulting Gap Register never mentions it, and nothing in the run's event log or artifacts shows any mechanism catching the omission — because this toy run's Cartographer only ever clusters the fixed six-paper input, never searches for what it doesn't have. **This confirms the check does what it's supposed to do (surface a real, known gap the run's own artifacts don't catch), but the finding itself is manufactured, not discovered** — this run used a fixed corpus specifically so it wouldn't do live Scout search (protocol doc's own reasoning), so it cannot exercise whether a *live* Scout/Cartographer pairing would find task-vector work on a real search. That test still needs a live-corpus run to mean anything as an actual signal about Scout's search quality — recorded here as still open, not answered by this toy run.

## Findings beyond the rubric — two real bugs, both discovered only by actually driving the run

**Finding #1 (significant, not fixed — pre-existing, Epic 4 scope): `kagami accept` does not enforce type-specific exit criteria, and `check_mvp_terminal` doesn't either.**

By accident (a stale shell variable reused after a failed write — a genuine mistake I made, not a planted scenario), I called `review` + `accept` on a Gap Register that was missing `why_does_this_gap_exist` and `meaningful_to_me` entirely. The system accepted it anyway: `accept_artifact` only checks the *generic* common-metadata fields (id/type/version/status/depends_on/elicited_from/decided_by/summary/created/updated), never the type-specific minimal-profile completeness `validate_locate_exit` separately checks. Worse: `check_mvp_terminal` (and by extension the `mvp_terminal_reached` event it logs, confirmed present in this run's actual event log for the broken artifact) treats *any* accepted Gap Register as reaching the terminal — so the run was marked MVP-complete on an artifact `validate-locate-exit` itself reports as having two missing required fields when checked directly:

```
$ kagami locate validate-locate-exit --run-id run-toy-icl --art-id art-3a9012a7da3b
{"ok": false, "violations": ["... missing minimal-profile field 'why_does_this_gap_exist'", "... missing minimal-profile field 'meaningful_to_me'"]}
```

This is not an Epic 7 regression — `validate_deepen_exit`, `validate_locate_exit`, and `validate_landscape_synthesis` have existed as separately-callable, not automatically-invoked, checks since Epics 3/4. It is exactly the kind of gap a real dogfooding run is supposed to surface and a unit test, testing each function in isolation, would never catch. **Recommendation, not implemented here:** either `kagami accept` should call the matching type-specific validator before allowing `accepted` status for types that have one, or the Interviewer skill must be given a hard rule to always call the matching `validate-*-exit` before ever calling `accept` on a terminal-adjacent type — a real design decision belonging to whoever owns Epic 4's contract, not something to quietly patch under Epic 7.

**Finding #2 (fixed in this PR): the refusal-ceiling middleware (Story 7.4) conflated a "violations" check's normal not-yet-satisfied result with a real refusal.**

`validate_deepen_exit`, `validate_locate_exit`, `validate_landscape_synthesis`, and `validate_minimal_profile` all share the contract `{"ok": len(violations) == 0, "violations": [...]}` — `ok: false` there means "not done yet," not "this call failed." The refusal-ceiling middleware built in Story 7.4 didn't know the difference, and would have escalated an entirely ordinary "check → fix one thing → check again" loop to `requires_researcher` after 3 legitimate re-checks of the same still-incomplete artifact. Fixed in `kagami/cli.py::main()` by detecting the `"violations"` key structurally (not a command-name allowlist, so it covers this contract wherever it's used) and exempting those results from ceiling tracking. New test: `test_a_repeated_violations_check_never_escalates_even_past_the_ceiling`.

## Test suite

`381 passed` (1 new, for Finding #2's fix — Findings #1 and its underlying artifacts are dogfooding evidence, not something this story's test suite asserts against, since fixing it is out of scope here).

## Verdict

**Conditional pass.** Every mechanism Epic 7 itself built or wired — the Interviewer skill's CLI sequence, launch-time dispatch resolution, `llm_call` reporting and its idempotency guard, role charters and their tool restrictions, the refusal ceiling (once Finding #2 was fixed), and provider-backoff infrastructure (not exercised live in this fixed-corpus run, but unit-tested in Story 7.4) — worked correctly, composed correctly, and produced a real, inspectable event log across a genuine end-to-end run to an accepted Gap Register.

**Not a clean pass:** Finding #1 is a real correctness gap, serious enough that an unsupervised real investigation could silently reach a false "done" — a Gap Register missing its own required content, with the run reporting itself terminal. This is not Epic 7's bug to own, but it is a precondition for trusting Epic 7's own golden-run verdict as sufficient license for unsupervised real use. **Recommendation: resolve Finding #1 (or add the Interviewer-skill hard rule as a stopgap) before dogfooding a real, non-toy investigation** — the mechanics this story was built to validate are sound; the one gap found sits one layer below them, in Epic 4's accept contract, and this toy run is exactly what caught it.
