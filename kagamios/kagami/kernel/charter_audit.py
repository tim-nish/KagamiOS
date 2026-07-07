import json
from pathlib import Path

SCOUT_ROLE = "scout"
SKEPTIC_ROLE = "skeptic"
HISTORIAN_ROLE = "historian"

# FR-25: Scout is confined to retrieval — reporting what exists, never
# interpreting or synthesizing it. Any 'llm_call' under the Scout role
# whose operation falls outside this allowlist is Scout producing
# interpretation, not retrieval. Kept in lockstep with every
# `--operation-class` Scout's own charter (`agents/scout.md`) directs it to
# report — see test_charter_audit.py's pinning test — never a lookup this
# file invents independently of the charter it's meant to check against.
SCOUT_ALLOWED_OPERATION_CLASSES = frozenset({"paper_card_extraction"})

# FR-25/FR-50: both of Scout's sanctioned raw-corpus retrieval kinds — a
# non-Scout role touching either is a charter violation, not just the
# original bulk-search sensor.
RAW_CORPUS_RETRIEVAL_KINDS = frozenset({"corpus_search", "corpus_expand"})


def _read_events(run_dir: Path) -> list:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def audit_charter_violations(run_dir: Path) -> dict:
    """FR-29: a role's charter violation is a checkable fact against the
    run's own event log, never a matter of re-reading transcripts.

    Detects, purely by inspecting event shape (no model call, no judgment):
    - Scout producing interpretation instead of retrieval (FR-25) — a
      landed `llm_call` no chokepoint blocks; a genuine violation.
    - Any non-Scout call touching the raw corpus (FR-25) — already refused
      before it can be logged by `kernel.scout.search_corpus` or
      `kernel.scout.corpus_expand` (FR-50); this check is a defense-in-depth
      backstop, so a hit here means that primary guarantee failed — also a
      genuine violation, not a guard doing its job.

    Separately, surfaces (but never counts as a violation) attempts the
    chokepoint already refused-and-blocked before they could land:
    - Skeptic proposing an alternative rather than only critiquing (FR-27) —
      refused and logged as a `generation_window_violation` by
      `kernel.skeptic.skeptic_write`.
    - Historian speaking outside the Evolution section, including frontier
      speculation within it (FR-28) — refused and logged the same way by
      `kernel.historian.historian_write`.
    These are `refusals_held`: the write never landed, so folding them into
    `violation_count` would make a working guard read as a breach that
    never happened (docs/dogfooding-review.md finding 5).

    Returns the specific responsible event(s) per category, never just a
    pass/fail flag; `violation_count == 0` and `refusals_held == 0` when a
    run is both charter-clean and had nothing to refuse.
    """
    events = _read_events(run_dir)

    non_scout_touched_raw_corpus = [
        event
        for event in events
        if event.get("family") == "retrieval"
        and event.get("kind") in RAW_CORPUS_RETRIEVAL_KINDS
        and event.get("role") != SCOUT_ROLE
    ]

    scout_produced_interpretation = [
        event
        for event in events
        if event.get("family") == "llm_call"
        and event.get("role") == SCOUT_ROLE
        and event.get("operation_class") not in SCOUT_ALLOWED_OPERATION_CLASSES
    ]

    skeptic_proposed_an_alternative = [
        event
        for event in events
        if event.get("family") == "gate_event"
        and event.get("kind") == "generation_window_violation"
        and event.get("role") == SKEPTIC_ROLE
    ]

    historian_spoke_outside_evolution = [
        event
        for event in events
        if event.get("family") == "gate_event"
        and event.get("kind") == "generation_window_violation"
        and event.get("role") == HISTORIAN_ROLE
    ]

    violations = {
        "scout_produced_interpretation": scout_produced_interpretation,
        "non_scout_touched_raw_corpus": non_scout_touched_raw_corpus,
    }
    refusals = {
        "skeptic_proposed_an_alternative": skeptic_proposed_an_alternative,
        "historian_spoke_outside_evolution": historian_spoke_outside_evolution,
    }
    violation_count = sum(len(v) for v in violations.values())
    refusals_held = sum(len(v) for v in refusals.values())

    return {
        "ok": True,
        "violation_count": violation_count,
        "violations": violations,
        "refusals_held": refusals_held,
        "refusals": refusals,
    }
