# Archive — Frozen Legacy Design Material

**Status: historical.** Everything under this directory is frozen design and audit history. None of it is current implementation guidance, and none of it should be treated as a source of truth for building KagamiOS.

## Current source of truth

Implementation guidance for KagamiOS comes from the BMAD planning artifacts under `_bmad-output/`:

- **`_bmad-output/specs/spec-kagamios/SPEC.md`** — the primary specification (the canonical, preservation-validated contract).
- **`_bmad-output/planning-artifacts/prds/prd-KagamiOS-2026-07-02/prd.md`** — the finalized PRD (companion to SPEC.md).
- **`_bmad-output/planning-artifacts/architecture/architecture-KagamiOS-2026-07-02/ARCHITECTURE-SPINE.md`** — the Architecture Spine (companion to SPEC.md).
- **`_bmad-output/planning-artifacts/epics.md`** — the epic and story breakdown derived from the above.

If something in this archive appears to conflict with those documents, the `_bmad-output/` documents win. This archive is not kept in sync with them going forward.

## What's in here

Each subdirectory is preserved exactly as it was when superseded — nothing has been rewritten, corrected, or redesigned on the way in. Internal cross-references between these documents (e.g. `docs-spec/` citing `docs-discovery-review/`) still resolve correctly, since all five directories were moved here together as siblings.

| Directory | What it is |
|---|---|
| `docs/` | The original v1 "Research Lifecycle OS" design. Superseded in full by the v2 scope pivot; kept only for side-by-side comparison. |
| `docs-discovery/` | The v2 "Research Discovery OS" redesign that followed the v1→v2 scope clarification. |
| `docs-discovery-review/` | First audit pass over `docs-discovery/` (practice alignment, agent personas, token efficiency, endpoint semantics, knowledge structure). An audit, not a redesign — the baseline it reviews was left unmodified. |
| `docs-runtime-review/` | Second audit pass, runtime-facing sequel to the first (runtime contracts, context/runtime behavior, observability, design analytics). Also audit-only. |
| `docs-spec/` | The consolidated, once-normative specification that synthesized `docs-discovery/` as amended by both audits. This was the design's last stop *before* it was translated into the BMAD-native SPEC/PRD/Architecture artifacts now living in `_bmad-output/` — it has since been superseded by that translation and is retained here as the audit trail those artifacts were distilled from. |

## When to open these documents

Normally: never. Day-to-day implementation work should never need to consult this archive — everything a builder needs lives in `_bmad-output/`.

The one legitimate reason to open something here is to recover **historical design rationale** that the current artifacts intentionally don't repeat — e.g. why an alternative was rejected, what an earlier audit flagged and how it was resolved, or how the current spec's wording traces back to an earlier design decision. Treat anything found here as color and context only, never as a requirement or instruction to implement against.
