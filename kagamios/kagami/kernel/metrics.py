import json
from pathlib import Path

import yaml

from kagami.registry import load_registry
from kagami.store.artifact import count_provisional, read_current


def _read_events(run_dir: Path) -> list:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def compute_override_rate(run_dir: Path, type_slug: str) -> dict:
    """FR-5's evidence base: of this run's own artifacts of `type_slug` that
    reached `accepted`, what fraction ever needed a human edit first — the
    aggregated, per-researcher statistic a gate-loosening proposal for that
    type must cite (AD-11's sanctioned read exception; never raw events at
    the point of decision, only this derived aggregate).
    """
    path = run_dir / "events.jsonl"
    accepted_ids: set[str] = set()
    overridden_ids: set[str] = set()

    if path.is_file():
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event.get("artifact_type") != type_slug:
                continue
            if event.get("family") == "artifact_event" and event.get("kind") == "accepted":
                accepted_ids.add(event["artifact_id"])
            elif event.get("family") == "human_edit":
                overridden_ids.add(event["artifact_id"])

    overridden_count = len(accepted_ids & overridden_ids)
    accepted_count = len(accepted_ids)
    override_rate = (overridden_count / accepted_count) if accepted_count else 0.0

    return {
        "type": type_slug,
        "accepted_count": accepted_count,
        "overridden_count": overridden_count,
        "override_rate": override_rate,
    }


def count_full_pull_after_summary(run_dir: Path) -> int:
    """FR-33: the summary-sufficiency signal.

    Counts artifacts where a full-text pull immediately followed a summary
    read of that same artifact — a detectable sign the summary was too thin.
    Computed after the fact from the event log (AD-11's sanctioned `kagami
    metrics` read exception), never consulted at runtime.
    """
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return 0

    last_read_kind: dict[str, str] = {}
    count = 0
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event.get("family") != "retrieval":
            continue
        artifact_id = event.get("artifact_id")
        kind = event.get("kind")
        if kind == "summary_read":
            last_read_kind[artifact_id] = "summary_read"
        elif kind == "full_text_pull":
            if last_read_kind.get(artifact_id) == "summary_read":
                count += 1
            last_read_kind[artifact_id] = "full_text_pull"

    return count


def compute_question_economics(run_dir: Path) -> list:
    """FR-37: per question — leverage class, consumption, revision, and
    staleness-cascade size — all read directly off the Question Ledger and
    event log, never inferred by a model. `staleness_cascade_size` joins a
    question's `id` against `staled` artifact_events whose `dependency_id`
    is that question (the same join `revise_answer` produces)."""
    ledger_dir = run_dir / "ledger"
    if not ledger_dir.exists():
        return []

    staled_by_dependency: dict = {}
    for event in _read_events(run_dir):
        if event.get("family") == "artifact_event" and event.get("kind") == "staled":
            dep_id = event.get("dependency_id")
            staled_by_dependency[dep_id] = staled_by_dependency.get(dep_id, 0) + 1

    entries = []
    for path in sorted(ledger_dir.glob("*.yaml")):
        entry = yaml.safe_load(path.read_text())
        entries.append(
            {
                "id": entry["id"],
                "target": entry.get("target", ""),
                "leverage_class": entry.get("leverage_class", ""),
                "form": entry.get("form"),
                "consumed_by_count": len(entry.get("consumed_by") or []),
                "revision_count": max(entry.get("version", 1) - 1, 0),
                "default_applied": bool(entry.get("default_applied")),
                "staleness_cascade_size": staled_by_dependency.get(entry["id"], 0),
            }
        )
    return entries


def compute_token_ledger(run_dir: Path) -> dict:
    """FR-37: spend by role x operation class, repair-vs-regen ratio, and
    summary sufficiency — all deterministic aggregation over the event log.
    `llm_call` events (role, operation_class, tokens, cache-hit) are emitted
    by the harness layer outside this core; spend is correctly all-zero
    until that integration exists, never estimated."""
    events = _read_events(run_dir)

    spend_by_role_and_operation_class: dict = {}
    for event in events:
        if event.get("family") != "llm_call":
            continue
        key = f"{event.get('role')}::{event.get('operation_class')}"
        bucket = spend_by_role_and_operation_class.setdefault(
            key, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cache_hits": 0}
        )
        bucket["calls"] += 1
        bucket["tokens_in"] += event.get("tokens_in", 0) or 0
        bucket["tokens_out"] += event.get("tokens_out", 0) or 0
        bucket["cache_hits"] += 1 if event.get("cache_hit") else 0

    repaired_at_tier0 = sum(
        1 for e in events if e.get("family") == "artifact_event" and e.get("kind") == "repair_resolved_at_tier0"
    )
    regenerated_at_tier2 = sum(
        1
        for e in events
        if e.get("family") == "artifact_event" and e.get("kind") == "repair_tier2_applied" and e.get("applied")
    )

    return {
        "spend_by_role_and_operation_class": spend_by_role_and_operation_class,
        "repair_vs_regen": {
            "repaired_at_tier0": repaired_at_tier0,
            "regenerated_at_tier2": regenerated_at_tier2,
        },
        "full_pull_after_summary_count": count_full_pull_after_summary(run_dir),
    }


def compute_override_profile(run_dir: Path, registry=None) -> dict:
    """FR-37: human-edit volume per artifact type, reusing FR-5's per-type
    override-rate aggregate (`compute_override_rate`) across every type
    that actually has artifacts in this run."""
    artifacts_root = run_dir / "artifacts"
    if not artifacts_root.exists():
        return {}
    types_present = sorted(p.name for p in artifacts_root.iterdir() if p.is_dir())
    return {type_slug: compute_override_rate(run_dir, type_slug) for type_slug in types_present}


def compute_unprimed_vs_final_diff_at_frame(run_dir: Path) -> dict | None:
    """FR-37/FR-24: the MVP-reachable analogue of the decision block's
    unprimed-vs-final diff — Propose's unprimed lean doesn't exist yet, but
    Frame's unprimed hunch does. A pure string comparison against the
    accepted Inquiry Frame's restated intuition, never an LLM judgment call
    on whether they "really" differ."""
    inquiry_frame_root = run_dir / "artifacts" / "inquiry-frame"
    if not inquiry_frame_root.exists():
        return None

    for meta_path in sorted(inquiry_frame_root.glob("*/meta.yaml")):
        meta = yaml.safe_load(meta_path.read_text())
        if meta.get("status") != "accepted":
            continue
        _frontmatter, sections = read_current(run_dir, "inquiry-frame", meta["id"])
        bodies = {s.title: s.body for s in sections}
        unprimed_hunch = bodies.get("unprimed_hunch", "")
        final_restated = bodies.get("intuition_restated", "")
        return {
            "inquiry_frame_id": meta["id"],
            "unprimed_hunch": unprimed_hunch,
            "final_restated": final_restated,
            "differs": unprimed_hunch.strip() != final_restated.strip(),
        }

    return None


def compute_budget_warning(token_ledger: dict, config: dict | None = None) -> dict | None:
    """AD-26(c): a gate-time soft-limit warning, never a block. Reads a
    researcher-set soft limit from `config.yaml` (`token_budget_soft_limit`);
    this is reporting at an existing checkpoint (FR-37), not the live
    budget enforcement NFR5/addendum A4/O6 defer — it never withholds
    progress, only surfaces the number. Returns None when unconfigured or
    still under the limit, so the decision block stays clean by default.
    """
    soft_limit = (config or {}).get("token_budget_soft_limit")
    if not soft_limit:
        return None

    total_tokens = sum(
        bucket["tokens_in"] + bucket["tokens_out"]
        for bucket in token_ledger.get("spend_by_role_and_operation_class", {}).values()
    )
    if total_tokens < soft_limit:
        return None

    return {
        "total_tokens": total_tokens,
        "soft_limit": soft_limit,
        "message": (
            f"Cumulative token spend ({total_tokens}) has crossed the configured "
            f"soft limit ({soft_limit}). This is a warning only — the run is not "
            "blocked (AD-26)."
        ),
    }


def compute_decision_block(run_dir: Path) -> dict:
    """FR-37/PRD §8: at MVP's Gap Register terminal, only the fields
    reachable without Propose/Decide are populated — candidate origins and
    falsifiable claims are Decide-only and stay empty since that state
    doesn't exist yet."""
    return {
        "candidate_origins": [],
        "unprimed_vs_final_diff": compute_unprimed_vs_final_diff_at_frame(run_dir),
        "provisional_count": count_provisional(run_dir),
        "falsifiable_claims": [],
    }


def compute_derived_metrics(run_dir: Path, registry=None, config: dict | None = None) -> dict:
    """FR-37: question economics, a token ledger, an override profile, a
    decision block, and (AD-26c) a gate-time budget warning — all
    deterministic computation over the run's own artifact store and event
    log. Re-running this over the same log always produces identical
    numbers; nothing here is an LLM judgment call."""
    registry = registry or load_registry()
    token_ledger = compute_token_ledger(run_dir)
    return {
        "ok": True,
        "question_economics": compute_question_economics(run_dir),
        "token_ledger": token_ledger,
        "override_profile": compute_override_profile(run_dir, registry),
        "decision_block": compute_decision_block(run_dir),
        "budget_warning": compute_budget_warning(token_ledger, config),
    }
