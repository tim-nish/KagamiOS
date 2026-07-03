# Adversarial Review — Architecture Spine, KagamiOS v1

Reviewer lens: construct two units one level down that each obey every AD to the letter yet build incompatibly. Every pair found is a hole to close with a new or tightened AD.

Target: `ARCHITECTURE-SPINE.md` (2026-07-02 draft). Contracts consulted: `docs-spec/04_artifacts.md`, `docs-spec/05_elicitation.md` §5–6, `docs-spec/07_runtime.md`.

Verdict: **9 holes**, ranked most-dangerous first. Holes 1–3 are correctness-destroying (lost writes, forged provenance, destroyed human edits); 4–7 are shared-data-shape clashes that force a rewrite of one unit when they meet; 8–9 are ADs whose Rule is unenforceable as written.

---

## Hole 1 — Concurrent chokepoint invocations are unserialized: AD-10's claim check is itself a race

**Units:** *artifact store + versioning* vs. *role subagents + parallel Deepen workers*.

**The two compliant constructions.** The chokepoint is a CLI: every `uv run kagami …` is a **separate OS process**. Nothing in any AD says two invocations may not run concurrently — AD-10 *encourages* it ("parallel writers", FR-3 one worker per cluster), and AD-4 has the Interviewer skill launching subagents that each call the CLI.

- The store unit implements AD-6/AD-10 exactly as written: read `meta.yaml`, check the section-claims table, verify the target section is unclaimed, compute next version = max(N)+1, write `vN.md`, rewrite `meta.yaml` with the new pointer/claim, append the event. Every step per the Rule. No lock — no AD asks for one.
- The subagent unit launches two Deepen workers. Both invoke `kagami claim`/`kagami write` within the same millisecond window.

**The incompatibility.** Classic read-modify-write race, four distinct corruptions, all while both units obey every AD:

1. **Claims:** both processes read `meta.yaml`, both see `sec-frontier` unclaimed, both record a claim, both write. AD-10's "the chokepoint rejects a write to a section claimed by another live worker" is satisfied *by each process's local view* — and violated in effect. The very mechanism that "prevents two workers writing the same section" is the thing that races.
2. **Version integers:** both compute next = v4. AD-6 says the chokepoint never rewrites an existing `vN.md` — so the second writer either clobbers `v4.md` before the first's rename lands, or errors nondeterministically. "Versions are monotonic integers owned by the chokepoint" names an owner (the chokepoint) that is *plural at runtime*.
3. **`meta.yaml`:** two whole-file rewrites; last writer silently discards the other's claim/pin/hash updates. A lost claim then invites a third writer into a "free" section.
4. **`events.jsonl` / `queue/` / `manifest.yaml`:** concurrent appends from separate processes can interleave partial lines unless every writer uses `O_APPEND` with single-`write()` lines — a discipline no AD states. A torn line breaks AD-11's promise that `kagami metrics` is deterministic over the log.

Also cross-process ID minting: "IDs assigned only by the chokepoint" (Consistency table) gives two concurrent processes no shared counter for `sec-`, `q-`, `evt-`.

**Close with (new AD-15 — Chokepoint serialization).** Every mutating `kagami` entrypoint acquires an exclusive advisory lock on `runs/<run-id>/.lock` (`flock`, bounded wait, `{"ok": false, "error": "busy"}` on timeout) for the entrepoint's full read-validate-write-append span. Claims and version numbers are decided only under the lock; `meta.yaml` updates are write-temp-then-atomic-rename; `events.jsonl`/`ledger` appends are single `write()` calls under `O_APPEND`. Parallelism (AD-10) is parallel *LLM work*; store mutation is serial by construction. Cross-run stores get their own lock (see Hole 5).

---

## Hole 2 — AD-2's deny-list plus AD-3's "out-of-band is definitionally human" compose into a provenance forgery channel

**Units:** *hooks + plugin packaging* vs. *`kagami scan` (store/provenance)*.

**The two compliant constructions.**

- The hooks unit implements AD-2 verbatim: PreToolUse denies the agent's `Write`, `Edit`, and `Bash`-**redirect** access to the output root. That is the full stated obligation. It ships matchers for `>`, `>>`, `tee`.
- The scan unit implements AD-3 verbatim: "File changes not made through the chokepoint are human edits" — a definition, not a heuristic. Scan flips touched spans to `human-confirmed` and **resolves the corresponding unknowns**.

**The incompatibility.** `Bash` has unboundedly many write vectors that are not redirects: `cp`, `mv`, `sed -i`, `python -c 'open(...,"w")'`, `dd`, `git checkout --`, heredoc via `cat <<EOF | python`. An agent (or a single hallucinated tool call — no malice needed) writes into `artifacts/…/v3.md` via `cp`. The hooks unit is compliant — redirects were denied. The scan unit is compliant — and now **stamps the AI's own text `human-confirmed`, auto-resolves open unknowns, and grants it the protected-span status of §1's human-edit-preservation rule**. AD-3's "Prevents: an AI path that fakes human provenance" is defeated by the composition of two Rules each followed to the letter. This also silently satisfies E6/AD-9 obligations ("human" ledger-adjacent edits) that were supposed to be un-fakeable.

**Close with (tighten AD-2 + AD-3).** AD-2: the hook is **default-deny for any tool invocation whose arguments reference the output root**, with a single allow-pattern (`uv run kagami …`); "deny Write/Edit/Bash-redirect" is replaced by allowlist semantics — enumerating write vectors is a losing game. AD-3 adds a corroboration clause: scan classifies an out-of-band change as human only when it did not occur inside an active AI turn (chokepoint records turn-boundary markers from hook events); changes detected mid-turn are quarantined as `suspect` and require explicit human confirmation before any span flips to `human-confirmed` or any unknown auto-resolves.

---

## Hole 3 — A queued AI write racing an unscanned human edit destroys the edit; docs-spec's "human edits always win" is encoded in no AD

**Units:** *elicitation kernel / repair pipeline* vs. *artifact store + `kagami scan`*.

**The two compliant constructions.**

- docs-spec 07 §2: "**human edits always win over queued AI writes**"; §1: repair "must emit a *proposed diff* for human-touched spans — silent overwrites of review edits would destroy the highest-bandwidth elicitation channel the system has." **No AD states either rule.** The repair unit therefore builds: kernel selects a stale artifact, worker regenerates failing sections, calls `kagami write` → chokepoint validates schema, window, claims, appends event, writes `v(N+1)`. Every AD satisfied.
- The scan unit implements AD-3's letter: human edits are detected "by content hash **on next touch**". It builds scan as an entrypoint the *skill* invokes at session start and gates.

**The incompatibility.** The researcher edits the current version's cluster-3 span in her editor. Before any "touch" that runs scan, the queued repair write lands: `v(N+1)` is created from the pre-edit content, `current` advances, and the human's spans — never flipped to `human-confirmed`, because scan wasn't the next touch; the *write* was — are superseded by AI text with clean AI provenance. Staleness (AD-6) doesn't help: the human edit isn't a version, so no pin comparison ever flags it. The spine's silence lets a fully AD-compliant unit violate docs-spec's most explicitly load-bearing rule. (Note the ordering dependency on Hole 2: this is the benign-race twin of the forgery channel.)

**Close with (new AD-16 — Scan-before-write; human edits win).** Every mutating entrypoint that targets an artifact runs the content-hash check on that artifact *first, inside the same locked operation* (AD-15). If uncommitted human edits are detected: the scan result is applied (spans → `human-confirmed`, unknowns resolved) **before** the write is validated, and any AI write overlapping a human-confirmed span is refused — the entrypoint returns the write as a *proposed diff* artifact instead. "Human edits always win over queued AI writes" and "proposed diffs only for human-touched spans" become store refusals, per AD-1's own standard (mechanical, never prompt-convention).

---

## Hole 4 — Two format authorities for the Question Ledger; "append-only ledger.md" contradicts the ledger schema it must implement

**Units:** *elicitation kernel + ASK scheduler* vs. *state machine + staleness engine* (and *event log + metrics* as a third reader).

**The two compliant constructions.**

- The ASK unit reads the Structural Seed — `ledger.md   # question ledger, append-only` — and AD-8 ("`kagami ask answer` writes the ledger entry and timestamps"). It builds a human-readable, append-only Markdown log: one heading per question, prose answer, timestamp. Nothing in any AD gives the ledger a schema; the schema registry (AD-14) covers exactly the **eleven artifact types**, and the ledger is explicitly not one of them (04 §3: infrastructure layer).
- The staleness/state unit reads docs-spec 05 §5: ledger entries are **versioned structured records** (`q-014@v1` — artifacts pin *ledger versions* in `elicited_from`), with `consumed_by` **stamped after creation** as artifacts pin the answer, and `superseded_by` set on later revision. It builds a machine store where entries are *mutated in place* — which is what the spec requires and what "append-only ledger.md" forbids.

**The incompatibility.** Three-way: (a) shape — prose Markdown vs. parseable versioned records; the staleness engine cannot compute `pinned q-014@v1 < current` over unstructured prose, so AD-6's "staleness computed without LLM calls" silently fails for the `elicited_from` edge class. (b) mutation model — `consumed_by` stamping and `superseded_by` are in-place updates to existing entries; "append-only" is either violated or the spec fields go unimplemented. (c) authority — the researcher can edit `ledger.md` in her editor, and per AD-3 that is *definitionally a human edit* to be honored, gutting append-only entirely.

**Close with (new AD-17 — The ledger is a schema-governed record store; ledger.md is a render).** Ledger entries live as structured records (e.g., `ledger/q-NNN.yaml`, or fenced YAML blocks with a registry-validated schema) matching 05 §5 field-for-field; entry *versions* are immutable and revision appends `q-NNN@v2` (resolving the append-only/mutation clash the same way AD-6 does for artifacts — `consumed_by` stamps live in a mutable per-entry meta section, mirroring `meta.yaml`). `ledger.md` is a derived, regenerable human view — a **control-plane file** in Hole 7's sense, not a human-edit surface; researchers revise answers through `kagami ask revise`, which is the E5 path anyway.

---

## Hole 5 — Cross-run stores (`corpus/`, `registry/`, `profile/`) have no versioning, locking, or ownership AD — and `researcher-profile` has two plausible owners

**Units:** *corpus tier + provider adapters* vs. *artifact store + versioning*.

**The two compliant constructions.**

- AD-6's Rule binds "artifact store, FR-9..14" and describes `runs/<run-id>/artifacts/<type>/<art-id>/`. The corpus unit reads AD-13 + docs-spec 04 §3 ("derived, cross-run, warm-startable") and builds `corpus/` and `registry/` as **mutable caches updated in place** — no `vN.md`, no `meta.yaml`, no claims. Fully compliant: no AD extends versioning past run artifacts.
- The store unit notices `researcher-profile` is one of the **eleven artifact-type slugs in the spine's own Consistency table**, hence registry-governed (AD-14), hence — it reasonably concludes — an AD-6 artifact with immutable versions and a `current` pointer. But the Structural Seed puts the profile at `profile/` (cross-run), *outside* `runs/<run-id>/artifacts/`. The unit must choose: AD-6 directory shape at a path AD-6 never mentions, or plain file. Either choice is compliant. docs-spec says Propose/Decide **consume the profile via pins** (`depends_on`) and it is "built incrementally from ledger answers" — pins require versions; incremental growth from two concurrent runs requires arbitration.
- Concurrency: two runs (two Claude Code sessions — nothing forbids it; "one researcher, one run, one machine" is a *deferral note* in 07 §8, not an AD) both append to `profile/`, both mint `ent-` and `ppr-` IDs in `registry/` and `corpus/` with no shared counter and no lock. AD-10's claims live in per-run `meta.yaml` and cannot mediate.

**The incompatibility.** One unit ships pin-consuming code (`researcher-profile@v7`) against a store the other unit built pointerless and versionless; entity/paper IDs collide or fork across runs; a plugin upgrade that changes card shape has no version to migrate. Two compliant units, incompatible data shapes at three shared paths.

**Close with (new AD-18 — Cross-run store contracts).** (a) `profile/` holds exactly one AD-6-shaped artifact (`profile/researcher-profile/vN.md + meta.yaml`); everything pinning it pins a version. (b) `corpus/` and `registry/` are declared **derived and unversioned**, with content-derived IDs — `ppr-` from a canonical bibliographic key (DOI/arXiv-ID hash), `ent-` from a canonical entity key — so concurrent minting converges instead of colliding; a `schema_version` field per card/record covers upgrades. (c) A per-store lock (AD-15 mechanics) guards read-modify-write on all three; alternatively an explicit AD that concurrent runs on one output root are refused at `kagami run start`.

---

## Hole 6 — "Stable section IDs" with no minting or survival semantics: heading-derived vs. registered IDs

**Units:** *artifact store (write path)* vs. *repair pipeline + brief rendering + AD-10 claims* (all consumers of `sec-` IDs).

**The two compliant constructions.**

- The store unit must put section IDs somewhere; the spine says only "`sec-` … assigned only by the chokepoint." It derives them from heading slugs at write time (`sec-<artifact>-<slug(heading)>`) — deterministic, chokepoint-assigned, compliant.
- The consumer units build on docs-spec 07 §2: "Stable section IDs … **survive regeneration**" — the unit of per-section status, repair, claims, and trace addressing. Tier-0 diff checks, `meta.yaml` claims (AD-10), section-status acceptance ("accepted iff all minimal-profile sections accepted", 04 §1), and brief partial-retrieval all key on `sec-` IDs persisting across versions.

**The incompatibility.** The Cartographer regenerates the Field Map and renames cluster 3 ("naming is framing" — the field is *designed* to be human-renamed, 04 §2). Slug-derived ID changes → the old ID's per-section status, human-confirmed flags, active claims, and pinned section-level dependencies all dangle; the new ID is unclaimed and status-less. A live worker's AD-10 claim on `sec-…-cluster-3` no longer matches anything, so a second writer sails through the claim check. Both units followed every AD; the spine never said what "assigned by the chokepoint" must guarantee across versions — docs-spec did, and the spine's silence let one unit drop it.

**Close with (tighten AD-6 or new AD-19 — Section identity).** Section IDs are opaque, minted once by the chokepoint at section creation, registered in frontmatter (`sections: [{id: sec-a7f3, title: "…"}]`), and **never derived from content or headings**. A write must reference existing IDs or explicitly create/retire IDs (retirement is a logged event and releases claims); a version that silently drops a registered live section is refused. Titles are mutable labels; identity is the ID.

---

## Hole 7 — `meta.yaml` is mutable control data, but AD-3 makes any out-of-band edit to it "definitionally human"

**Units:** *artifact store* vs. *`kagami scan`*. (Distinct from Hole 2: this one needs no rogue AI — an ordinary researcher `git checkout`/hand-edit suffices.)

**The two compliant constructions.**

- The store unit treats `meta.yaml` (current pointer, status, pins, claims, hashes) — and `manifest.yaml`, `queue/`, `events.jsonl` — as chokepoint-owned control state: the integrity substrate for AD-6 staleness, AD-9 windows, AD-10 claims, AD-11 audit.
- The scan unit implements AD-3's Rule, which binds "the store" and defines *all* non-chokepoint file changes as human edits. `meta.yaml` is a file. A researcher (or her `git checkout`, or a merge) changes `current: 3 → 4`, deletes a claim, or edits a hash. Scan, to the letter, must treat this as a human edit to honor — or at minimum has no AD telling it to do anything else.

**The incompatibility.** If the scan unit honors it: the human can (accidentally — a git operation is enough) accept drafts, un-stale artifacts, free claimed sections, and desynchronize hashes, and the store unit's every guard now runs on forged inputs while both units are compliant. If the scan unit instead ignores/reverts it, it violates AD-3's letter and the two units disagree about who owns the file. The spine also never answers the prompt's direct question — *who may write `meta.yaml`* — beyond implication; nor whether events.jsonl or queue/ files enjoy AD-3's human-by-definition status.

**Close with (tighten AD-3 — Data plane vs. control plane).** AD-3 applies only to **artifact content files** (`vN.md`) and other declared human-edit surfaces. `meta.yaml`, `manifest.yaml`, `events.jsonl`, `queue/`, and the ledger record store (AD-17) are **control-plane files**: chokepoint-exclusive; out-of-band changes to them are *corruption, not intent* — detected by hash at next entrypoint, refused as inputs, reported, and repaired by deterministic rebuild from data-plane ground truth where possible (P1: artifacts are the only ground truth; control state is derived and rebuildable — the spec already grants this).

---

## Hole 8 — Two authorities for derived run state: `manifest.yaml` fields vs. kernel pure functions

**Units:** *state machine + manifest* vs. *elicitation kernel / generation-window enforcement (AD-9)*.

**The two compliant constructions.**

- The layer map defines the kernel as "derived state, frontier, triage … **pure functions over store state**." The kernel unit therefore computes the per-cluster state and window openness from artifacts + ledger on demand, and AD-9's refusals consult that function.
- The Structural Seed defines `manifest.yaml` as containing "run manifest **incl. derived state**, budgets," and the Capability Map assigns "§4.1 State machine … `kernel/` derived-state + `manifest.yaml`." The state-machine unit therefore *persists* state in the manifest and mutates it on transitions via the chokepoint; its gate/waiver/loop-back logic and its window checks read the manifest.

**The incompatibility.** Two sources of truth for the single input to AD-9's refusal — the spine's flagship "violation is impossible" guarantee. They diverge in ordinary operation: a human edit resolved via scan flips the pure function's answer (Gap Register now accepted ⇒ Propose window open) while the manifest still says Locate — or vice versa after a manifest write races (Hole 1). One unit's `kagami write candidate-direction` is refused, the other unit's identical call is accepted, depending only on which authority that entrypoint's author picked. Both authors were compliant.

**Close with (tighten AD-9/AD-6 or new AD-20 — Manifest is a cache).** Derived state is *definitionally* the kernel's pure function over store + ledger. `manifest.yaml`'s state fields are a cache, recomputed and rewritten by every mutating entrypoint (cheap: pure graph traversal, per 07 §4), and **never read for a guard decision** — guards call the function. Budgets and monitoring config, which are not derivable, are the manifest's only authoritative content.

---

## Hole 9 — Unenforceable Rules as written (AD-4; AD-11 clause)

**AD-4 — "the store refuses artifact content that does not cite a generating role session."** The chokepoint is a local Python process; it cannot verify that a `session-id` string corresponds to a real subagent launch — it has no trusted channel to the harness's launch records. Any caller (including the main thread, which AD-4 says "never generates content") passes `--role scout --session <anything>` and the refusal is satisfied. As written this is enforcement-by-honor-system, i.e., exactly the "rule that exists only in a SKILL.md" that AD-1 forbids, laundered through a CLI flag. **Close:** subagent-launch hooks (SessionStart/SubagentStop or equivalent) register live role sessions *with the chokepoint* (`kagami session open/close`, writing a control-plane session table); a write's cited session must be open, role-matching, and unexpired, else refused. Then "the Interviewer never generates content" is mechanical, not vibes. (Residual: a role can still cite its own session for off-charter content — accept and log as detect-and-audit, the same downgrade class AD-11 already declares.)

**AD-11 — "Nothing in the core or skill reads `events.jsonl` during a run."** The core half is enforceable (code review + no read API). The skill/agent half is not: subagents have `Read`, and no hook is specified to deny reads of the log. Either add the log to the hook's deny scope (read *and* write) or restate the clause as a code-review invariant for the core plus an audit check for the harness — currently it reads as a guarantee the architecture cannot give.

---

## Summary table

| # | Hole | Units in conflict | Fix |
|---|------|-------------------|-----|
| 1 | Unserialized concurrent CLI invocations; claim check races | store ↔ parallel workers | AD-15: run lock + atomic write discipline |
| 2 | Bash non-redirect writes + "out-of-band = human" ⇒ provenance forgery | hooks ↔ scan | tighten AD-2 (default-deny) + AD-3 (turn-aware corroboration) |
| 3 | Queued AI write beats unscanned human edit; "human wins" in no AD | repair ↔ store/scan | AD-16: scan-before-write; overlap ⇒ proposed diff |
| 4 | ledger.md prose/append-only vs. versioned mutable ledger records | ASK scheduler ↔ staleness engine | AD-17: schema-governed ledger store; .md is a render |
| 5 | corpus/registry/profile unversioned, unlocked; profile dual-owned | corpus tier ↔ store | AD-18: profile is AD-6 artifact; caches get content-derived IDs + lock |
| 6 | Section-ID minting/stability unspecified; slug IDs orphan claims/status | store ↔ repair/briefs/claims | AD-19: opaque registered IDs, explicit create/retire |
| 7 | meta.yaml mutable + AD-3 makes hand edits to it "human" | store ↔ scan | tighten AD-3: data-plane vs. control-plane files |
| 8 | manifest.yaml derived-state vs. kernel pure function — two window authorities | state machine ↔ kernel/AD-9 | AD-20: manifest state is a never-read-for-guards cache |
| 9 | AD-4 role-session citation & AD-11 no-read clause unenforceable as written | AD-4 store refusal / AD-11 | session registration via hooks; log-read denial or reclassify |
