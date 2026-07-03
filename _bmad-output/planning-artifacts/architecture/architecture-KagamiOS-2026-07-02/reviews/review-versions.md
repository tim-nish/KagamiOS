# Reviewer Gate — Version & Reality Check

- **Target:** `ARCHITECTURE-SPINE.md` (Stack table + every technology named in ADs/seed)
- **Lens:** every committed decision web-researched or reality-checked, not asserted from training data
- **Date:** 2026-07-02
- **Method:** WebSearch/WebFetch against live sources today, plus inspection of `/workspaces/KagamiOS/_bmad/scripts/`

## Verdict

The Stack table is substantially accurate and clearly was researched (the OpenAlex Feb-2026 pricing change is cited correctly, pydantic 2.13.x and the 3.14.x note are current). Two findings: the **Semantic Scholar rate-limit numbers are outdated/wrong** per the current official page, and the **PyYAML choice needs an explicit round-trip caveat** recorded (PyYAML cannot preserve comments; acceptable only if `meta.yaml` is declared machine-owned/comment-free and the core never rewrites `config.yaml`). Everything load-bearing about the Claude Code plugin platform (AD-2 hook denial, AD-12 per-agent model) is confirmed against current Anthropic docs.

## Per-technology findings

### 1. Python ≥ 3.12 floor, "3.14.x current" — VERIFIED

- Current stable is **Python 3.14.6** (released 2026-06-10); 3.14 is in active bugfix maintenance. The Stack table's "3.14.x current" is correct as of today.
- A ≥ 3.12 floor is sensible: 3.12 is in security support (EOL Oct 2028); 3.10 hits EOL 2026-10-31 so nothing older should be floored. Floor is also compatible with the BMAD scripts' own requirement (3.11+ for `tomllib`, per docstrings in `_bmad/scripts/resolve_config.py`).
- Sources: https://devguide.python.org/versions/ , https://www.python.org/downloads/ , https://endoflife.date/python

### 2. pydantic 2.13.x — VERIFIED

- Latest is **pydantic 2.13.4** (released May 2026, docs at v2.13.4); v2.13 added initial Python 3.14 support, so it pairs correctly with the Python row.
- Sources: https://pypi.org/project/pydantic/ , https://docs.pydantic.dev/latest/ , https://github.com/pydantic/pydantic/releases

### 3. PyYAML 6.x — VERIFIED as current, but FLAGGED: needs a round-trip caveat

- Latest PyYAML is **6.0.3** (Sep 2025) — "6.x" is accurate and PyYAML remains the de facto standard loader (≈1B downloads/month). Release cadence is slow but the package is maintained.
- **Flag:** PyYAML **cannot round-trip comments, key order guarantees, or formatting** — a load-save cycle destroys 100% of comments. `ruamel.yaml` is the round-trip-safe alternative (rt mode preserves comments, flow style, key order) and is actively maintained.
- Does it matter here? Mostly no, by the spine's own design — but only if that design constraint is made explicit:
  - `vN.md` files are immutable once written (AD-6), so frontmatter of existing versions is never re-emitted. Fine.
  - `meta.yaml` is chokepoint-owned and rewritten constantly (current pointer, claims, hashes). PyYAML is fine **iff** `meta.yaml` is declared machine-only: any human comment added to it will be silently destroyed on the next chokepoint write. Under AD-3 a human edit to `meta.yaml` is an out-of-band edit anyway, so the cleanest fix is a one-line note that `meta.yaml` is machine-owned and comment-free.
  - `config.yaml` is researcher-owned (AD-12). The core must treat it as **read-only**; if any future `kagami config set`-style entrypoint rewrites it with PyYAML, researcher comments vanish. Either record "core never writes config.yaml" or plan ruamel.yaml for that one writer.
- **Correction requested:** add the caveat to the Stack row or AD-6/AD-12: "PyYAML (dump path) used only for machine-owned files; researcher-edited YAML is read-only to the core (PyYAML does not preserve comments)."
- Sources: https://pypi.org/project/PyYAML/ , https://pypi.org/project/ruamel.yaml/ , https://yaml.dev/doc/ruamel.yaml/overview/

### 4. Claude Code plugin platform — VERIFIED (all three load-bearing claims)

- **Plugins ship skills + agents + hooks:** confirmed. Plugin components include skills, agents, hooks (plus commands, MCP servers, etc.); plugin hooks live in `hooks/hooks.json` and merge with user/project hooks when the plugin is enabled. The seed's tree (`.claude-plugin/plugin.json` + `skills/` + `agents/` + `hooks/` at plugin root) matches the documented layout.
- **PreToolUse can DENY a Write/Edit (AD-2):** confirmed against current docs. Two mechanisms: exit code 2 blocks the call, or JSON `hookSpecificOutput.permissionDecision: "deny"` with `permissionDecisionReason` (also `allow`/`ask`/`defer`, and `updatedInput` to rewrite tool input). Matchers like `Write|Edit` are the documented pattern. AD-2's enforcement mechanism is real.
- **Per-agent model field (AD-12):** confirmed. Subagent frontmatter supports `model` and `tools` (full list: `description, prompt, tools, disallowedTools, model, permissionMode, mcpServers, hooks, maxTurns, skills, initialPrompt, memory, effort, background, isolation, color`). AD-4's role-restricted tools are equally supported.
- **One platform caveat worth recording (non-blocking):** plugin-shipped subagents **ignore the `hooks`, `mcpServers`, and `permissionMode` frontmatter fields** for security. The spine's hooks are plugin-level (hooks/hooks.json), not per-agent, so AD-2 is unaffected — but no future AD may assume per-agent hooks inside the plugin.
- **AD-12 wiring note (non-blocking):** the spine puts model tiers in `config.yaml` while the platform's `model` field lives in static agent frontmatter. Resolving tier→model at dispatch (model override at spawn) is supported, but the story implementing AD-12 must bridge that explicitly rather than expect frontmatter to read config.
- Sources: https://code.claude.com/docs/en/plugins-reference , https://code.claude.com/docs/en/hooks , https://code.claude.com/docs/en/sub-agents

### 5a. OpenAlex API — VERIFIED

- The Stack row "free tier + usage-based pricing (Feb 2026 change)" is exactly right, and AD-7's use of it as "live proof" is legitimate: OpenAlex announced usage-based pricing in Feb 2026 — **API keys required for all requests (from Feb 13, 2026; free to obtain)**, **$1/day free usage**, then pay-per-use (singleton lookups free; list requests $0.0001; search $0.001/call; semantic search $0.01). The dataset itself stays free.
- Minor addition for the AD-7 adapter story: "API key required for all requests" means the OpenAlex adapter needs key configuration from day one — worth a word in the Stack row.
- Sources: https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/ , https://developers.openalex.org/api-reference/authentication , https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing

### 5b. Semantic Scholar API — WRONG (outdated numbers)

- Stack row says: "free; **keyless 5k req/5min**, higher with free key."
- Current official page says: keyless requests are "**rate-limited to 1000 requests per second shared among all unauthenticated users**" (i.e., a shared global pool, further throttled under heavy use), and "**the introductory rate limit for an API key is 1 RPS on all endpoints**" (dedicated; higher rates by review). The 5k/5min figure appears only in older/third-party material.
- "Higher with free key" is also misleading: the key gives a *dedicated* 1 RPS, not a nominally higher number than the shared pool.
- **Correction requested:** Stack row → "free; keyless = shared global pool (throttled under load); free API key = dedicated 1 RPS introductory, higher by request."
- Sources: https://www.semanticscholar.org/product/api , https://api.semanticscholar.org/api-docs/ , https://github.com/allenai/s2-folks/blob/main/API_RELEASE_NOTES.md

### 5c/6. arXiv API — VERIFIED with caveat

- Still free and open; documented limit is **1 request per 3 seconds, single connection**. Caveat for the adapter story: since ~Feb 25, 2026 users report HTTP 429s even at compliant rates, so the arXiv adapter needs backoff/retry from day one (already covered by the deferred "provider failover/retry policy" item — fine).
- Sources: https://info.arxiv.org/help/api/tou.html , https://info.arxiv.org/help/api/index.html , https://groups.google.com/a/arxiv.org/g/api/c/ycq8giRdZsQ

### 6. GitHub API — VERIFIED with precision note

- Free/public tier exists, but the **search endpoints have their own tight limits** (~30 req/min authenticated for search; code search stricter still; unauthenticated core is only 60 req/hr). "Free/public tiers" is true but the Scout adapter effectively requires a token. Suggest the Stack row say "free with token; search endpoints ~30 req/min".
- Sources: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api , https://docs.github.com/en/rest/rate-limit/rate-limit

### 7. uv shared with BMAD — VERIFIED against the project

- `/workspaces/KagamiOS/_bmad/scripts/` contains `memlog.py`, `resolve_config.py`, `resolve_customization.py` — all Python; `memlog.py` carries PEP 723 inline script metadata (`# /// script`), and the docstrings state "BMad is standardizing on `uv run` to invoke scripts". The spine's "Invocation: always `uv run kagami <cmd>`" and "toolchain shared with BMAD" claims are grounded in the actual repo. The Stack row pins no uv version ("current"), so there is nothing further to falsify.

## Corrections summary (what the spine should change)

1. **Stack table, Semantic Scholar row (WRONG):** replace "keyless 5k req/5min, higher with free key" with the current official limits (shared global pool keyless; dedicated 1 RPS introductory with free key).
2. **Stack table PyYAML row / AD-6 (CAVEAT):** note that PyYAML does not round-trip comments; declare `meta.yaml` machine-owned/comment-free and `config.yaml` read-only to the core (or plan ruamel.yaml for any future config writer).
3. **Stack table, OpenAlex row (minor):** note API key now required for all requests (free key, $1/day allowance).
4. **Stack table, GitHub row (minor):** note token effectively required; search endpoints ~30 req/min.
5. **Platform note near AD-4/AD-12 (informational):** plugin-shipped subagents ignore `hooks`/`mcpServers`/`permissionMode` frontmatter; `model` and `tools` are supported. AD-12's config-driven tiers need explicit dispatch-time model resolution.

No AD is invalidated. AD-2 and AD-12's platform assumptions are confirmed against current Anthropic docs.
