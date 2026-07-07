import argparse
import json
import sys
import uuid
from pathlib import Path

from kagami.config import load_config
from kagami.corpus.adapters import resolve_provider
from kagami.corpus.provider import ProviderError
from kagami.kernel.cartographer import (
    CartographerError,
    create_field_map_clusters,
    draft_clusterings,
    validate_field_map_draft,
)
from kagami.kernel.charter_audit import audit_charter_violations
from kagami.kernel.privacy import PrivacyError, generate_shared_payload
from kagami.kernel.derived_state import (
    DepthBudgetError,
    compute_run_nominal_state,
    detect_budget_exhaustion,
    get_depth_budgets,
    set_depth_budgets,
)
from kagami.kernel.deepen import claim_cluster_sections
from kagami.kernel.dissolution import (
    DissolutionError,
    check_dissolution_terminal,
    draft_dissolution_memo,
    record_revival_conditions,
    record_what_was_learned,
    spin_off_salvaged_fragment,
    validate_dissolution_exit,
)
from kagami.kernel.dossier import (
    DossierError,
    create_cluster_dossier,
    mark_representative_paper_read,
    validate_deepen_exit,
)
from kagami.kernel.entry import EntryError, start_run_from_entry
from kagami.kernel.frame import complete_frame
from kagami.kernel.gate_trust import GateTrustError, approve_gate_loosening, propose_gate_loosening
from kagami.kernel.historian import HistorianError, historian_write
from kagami.kernel.locate import (
    LocateError,
    check_mvp_terminal,
    create_gap_register,
    locate_write,
    mark_gap_meaningful,
    record_micro_probe_evidence,
    validate_locate_exit,
)
from kagami.kernel.dispatch import DispatchError, resolve_model
from kagami.kernel.metrics import (
    DEFAULT_REDISCOVERY_WINDOW,
    compute_derived_metrics,
    compute_rediscovery_rate,
    count_full_pull_after_summary,
)
from kagami.kernel.monitor import MonitorError, mark_dormant, monitor_sweep
from kagami.kernel.refusal import DEFAULT_REFUSAL_CEILING, record_refusal_and_check_ceiling
from kagami.kernel.report import ReportError, report_llm_call
from kagami.kernel.profile import validate_minimal_profile
from kagami.kernel.repair import apply_tier2_repair, repair_artifact
from kagami.kernel.scout import CorpusAccessError, DEFAULT_SEARCH_LIMIT, corpus_expand, search_corpus
from kagami.store.appraisal import AppraisalError, record_appraisal
from kagami.kernel.skeptic import SkepticError, build_skeptic_context, record_skeptic_critique, skeptic_write
from kagami.kernel.state_machine import StateMachineError, enter_state
from kagami.kernel.synthesize import (
    SynthesizeError,
    create_landscape_synthesis,
    synthesize_write,
    validate_landscape_synthesis,
)
from kagami.paths import resolve_output_root
from kagami.registry import RegistryError
from kagami.schema_version import SchemaVersionError
from kagami.store import ledger
from kagami.store.artifact import ArtifactError, accept_artifact, count_provisional, review_artifact, scan
from kagami.store.ledger import LedgerError
from kagami.store.read import ConsumptionError, read_artifact
from kagami.store.run import open_run


def _run_dir(run_id: str):
    return resolve_output_root() / "runs" / run_id


_SUBCOMMAND_DEST_NAMES = (
    "run_command", "state_command", "monitor_command", "budgets_command",
    "entry_command", "frame_command", "deepen_command", "repair_command",
    "skeptic_command", "historian_command", "dossier_command",
    "dissolution_command", "synthesize_command", "locate_command",
    "cartographer_command", "corpus_command", "ask_command",
    "metrics_command", "gate_command", "report_command", "dispatch_command",
    "appraisal_command",
)


def _entrypoint_key(args: argparse.Namespace) -> str:
    """AD-26(a): the `entrypoint` half of the `(entrypoint, target)` tuple
    the refusal ceiling keys on — the full dotted subcommand path, e.g.
    `historian.write`, so two different subcommands never share a
    ceiling."""
    parts = [args.command]
    for dest in _SUBCOMMAND_DEST_NAMES:
        value = getattr(args, dest, None)
        if value:
            parts.append(value)
    return ".".join(parts)


# docs/dogfooding-review.md finding 10: `--state` (state:enter, read) and
# `--section` (historian:write, skeptic:write) are compared against a
# lowercase canonical vocabulary several kernel layers down
# (state_machine.yaml's states, historian.EVOLUTION_SECTION,
# skeptic.RED_TEAM_FIELD) — normalized once here, at the one shared
# parsing point every entrypoint passes through, so the same input form
# is never accepted by one subcommand and refused by another.
_CASE_NORMALIZED_ARG_DESTS = ("state", "section")


def _normalize_case_insensitive_args(args: argparse.Namespace) -> None:
    for dest in _CASE_NORMALIZED_ARG_DESTS:
        value = getattr(args, dest, None)
        if isinstance(value, str):
            setattr(args, dest, value.strip().lower())


def _target_key(args: argparse.Namespace) -> str:
    """AD-26(a): the `target` half — every argument except `func` and the
    subcommand-selector dests themselves (already folded into the
    entrypoint key), so two calls only share a target when every other
    argument is identical too. A call with different content (e.g. a
    different `--body`) is a different target, not a retry — the ceiling
    exists for identical retries, not iterative attempts."""
    excluded = {"func", "command"} | set(_SUBCOMMAND_DEST_NAMES)
    payload = {k: v for k, v in sorted(vars(args).items()) if k not in excluded}
    return json.dumps(payload, sort_keys=True, default=str)


def _cmd_run_open(args: argparse.Namespace) -> dict:
    try:
        return open_run(run_id=args.run_id)
    except SchemaVersionError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_run_validate_profile(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return validate_minimal_profile(run_dir)


def _cmd_scan(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return scan(run_dir, args.type, args.art_id)
    except (ArtifactError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_accept(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return accept_artifact(run_dir, args.type, args.art_id, args.summary)
    except (ArtifactError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_review(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return review_artifact(run_dir, args.type, args.art_id)
    except (ArtifactError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_state_enter(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return enter_state(run_dir, args.state, waiver=args.waiver, cause=args.cause)
    except StateMachineError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_entry_start(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return start_run_from_entry(run_dir, args.entry_mode, args.raw_capture)
    except EntryError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_frame_complete(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    fields = json.loads(args.fields_json)
    sections = json.loads(args.sections_json)
    try:
        return complete_frame(
            run_dir, args.unprimed_answer, args.scope_answer, fields, sections, args.summary
        )
    except (LedgerError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_read(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return read_artifact(run_dir, args.state, args.type, args.art_id, args.resolution)
    except (ConsumptionError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_ask_emit(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        questions = json.loads(args.questions_json)
        return ledger.emit_batch(run_dir, questions)
    except (LedgerError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_ask_answer(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return ledger.answer_question(run_dir, args.id, args.answer)
    except LedgerError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_ask_revise(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return ledger.revise_answer(run_dir, args.id, args.answer)
    except LedgerError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_corpus_search(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    output_root = resolve_output_root()
    config = load_config(Path.cwd())
    try:
        provider = resolve_provider(config, provider_override=args.provider)
        return search_corpus(run_dir, output_root, provider, args.query, args.role, limit=args.limit)
    except (ProviderError, CorpusAccessError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_appraisal_record(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return record_appraisal(run_dir, args.paper_id, args.judgment, args.frame_version, args.reason)
    except AppraisalError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_corpus_expand(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    output_root = resolve_output_root()
    config = load_config(Path.cwd())
    try:
        provider = resolve_provider(config, provider_override=args.provider)
        return corpus_expand(run_dir, output_root, provider, args.canonical_key, args.role)
    except (ProviderError, CorpusAccessError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_cartographer_draft(args: argparse.Namespace) -> dict:
    papers = json.loads(args.papers_json)
    try:
        result = draft_clusterings(papers)
        validate_field_map_draft(result["cuts"])
        return {"ok": True, **result}
    except CartographerError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_cartographer_create(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    papers = json.loads(args.papers_json)
    papers_by_id = {p["id"]: p for p in papers}
    cuts = json.loads(args.cuts_json)
    chosen_cut = next((c for c in cuts if c["basis"] == args.chosen_basis), None)
    if chosen_cut is None:
        return {"ok": False, "error": f"no cut with basis '{args.chosen_basis}' among the provided cuts"}
    try:
        return create_field_map_clusters(run_dir, chosen_cut, cuts, papers_by_id)
    except (CartographerError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_deepen_claim(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    section_ids = json.loads(args.sections_json)
    return claim_cluster_sections(run_dir, args.art_id, section_ids, args.holder)


def _cmd_repair_check(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return repair_artifact(run_dir, args.type, args.art_id)


def _cmd_repair_apply(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    section_fixes = json.loads(args.fixes_json)
    return apply_tier2_repair(run_dir, args.type, args.art_id, section_fixes)


def _cmd_skeptic_context(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return build_skeptic_context(run_dir, args.type, args.art_id)


def _cmd_skeptic_critique(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    evidence_cited = json.loads(args.evidence_json)
    return record_skeptic_critique(run_dir, args.type, args.art_id, args.objection, evidence_cited)


def _cmd_skeptic_write(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return skeptic_write(run_dir, args.type, args.art_id, args.section, args.body)
    except (SkepticError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_historian_write(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return historian_write(run_dir, args.art_id, args.section, args.body)
    except (HistorianError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dossier_create(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    representative_paper_ids = json.loads(args.representative_papers_json)
    try:
        return create_cluster_dossier(run_dir, args.field_map_id, representative_paper_ids)
    except DossierError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dossier_mark_read(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return mark_representative_paper_read(run_dir, args.art_id, args.paper_id, args.reaction)
    except DossierError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dossier_validate_deepen_exit(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return validate_deepen_exit(run_dir, args.art_id)


def _cmd_synthesize_create(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return create_landscape_synthesis(run_dir)


def _cmd_synthesize_write(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    rows = json.loads(args.rows_json)
    dossier_ids = json.loads(args.dossier_ids_json)
    try:
        return synthesize_write(run_dir, args.art_id, args.field, rows, dossier_ids)
    except (SynthesizeError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_synthesize_validate(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return validate_landscape_synthesis(run_dir, args.art_id)


def _cmd_locate_create(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return create_gap_register(run_dir, args.statement, args.evidence_of_absence)


def _cmd_locate_write(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return locate_write(run_dir, args.art_id, args.field, args.content)
    except (LocateError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_locate_mark_meaningful(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return mark_gap_meaningful(run_dir, args.art_id, args.disposition)
    except (LocateError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_locate_record_micro_probe(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return record_micro_probe_evidence(run_dir, args.art_id, args.evidence)
    except (LocateError, ArtifactError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_locate_validate_exit(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return validate_locate_exit(run_dir, args.art_id)


def _cmd_locate_check_terminal(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return check_mvp_terminal(run_dir)


def _cmd_state_derive(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return compute_run_nominal_state(run_dir)


def _cmd_budgets_set(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    clusters_to_deepen = json.loads(args.clusters_json)
    return set_depth_budgets(run_dir, clusters_to_deepen, args.papers_per_cluster, args.time_horizon)


def _cmd_budgets_get(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return {"ok": True, "depth_budgets": get_depth_budgets(run_dir)}


def _cmd_budgets_check_exhaustion(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return detect_budget_exhaustion(run_dir, args.cluster_id, args.papers_read_count)
    except DepthBudgetError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dissolution_draft(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    dissolving_evidence = json.loads(args.dissolving_evidence_json)
    dissolving_ledger_refs = json.loads(args.dissolving_ledger_refs_json) if args.dissolving_ledger_refs_json else []
    try:
        return draft_dissolution_memo(
            run_dir, args.intuition_summary, dissolving_evidence, dissolving_ledger_refs
        )
    except DissolutionError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dissolution_record_learned(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return record_what_was_learned(run_dir, args.art_id, args.content)


def _cmd_dissolution_record_revival_conditions(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return record_revival_conditions(run_dir, args.art_id, args.content)


def _cmd_dissolution_spin_off_fragment(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return spin_off_salvaged_fragment(run_dir, args.art_id, args.raw_capture, args.entry_mode)
    except DissolutionError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dissolution_validate_exit(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return validate_dissolution_exit(run_dir, args.art_id)


def _cmd_dissolution_check_terminal(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return check_dissolution_terminal(run_dir)


def _cmd_monitor_mark_dormant(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return mark_dormant(run_dir, args.revival_conditions)
    except (MonitorError, StateMachineError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_monitor_sweep(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return monitor_sweep(run_dir)
    except MonitorError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_gate_propose(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return propose_gate_loosening(run_dir, args.type)
    except (GateTrustError, RegistryError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_gate_approve(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return approve_gate_loosening(run_dir, args.type)
    except (GateTrustError, RegistryError) as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_metrics_provisional_count(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return {"ok": True, "provisional_count": count_provisional(run_dir)}


def _cmd_metrics_summary_sufficiency(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return {"ok": True, "full_pull_after_summary_count": count_full_pull_after_summary(run_dir)}


def _cmd_metrics_derived(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    config = load_config(Path.cwd())
    return compute_derived_metrics(run_dir, config=config)


def _cmd_metrics_rediscovery_rate(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return {"ok": True, **compute_rediscovery_rate(run_dir, window=args.window)}


def _cmd_metrics_charter_audit(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return audit_charter_violations(run_dir)


def _cmd_metrics_shared_payload(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    config = load_config(Path.cwd())
    try:
        return generate_shared_payload(run_dir, config)
    except PrivacyError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_report_llm_call(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    # AD-26/docs/dogfooding-review.md finding 10: the guard's purpose is
    # idempotency, not ceremony — a harness that forgets `--call-id` gets a
    # freshly minted one rather than a first-attempt refusal. A harness
    # that *wants* the idempotency guarantee still passes its own
    # `--call-id` explicitly, so a real retry is still caught by
    # `report_llm_call`'s duplicate check below.
    call_id = args.call_id or str(uuid.uuid4())
    try:
        return report_llm_call(
            run_dir,
            args.role,
            args.operation_class,
            args.model_tier,
            args.tokens_in,
            args.tokens_out,
            args.cache_hit == "true",
            call_id,
        )
    except ReportError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dispatch_resolve(args: argparse.Namespace) -> dict:
    config = load_config(Path.cwd())
    try:
        return resolve_model(args.operation_class, config)
    except DispatchError as exc:
        return {"ok": False, "error": str(exc)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kagami")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_subparsers = run_parser.add_subparsers(dest="run_command", required=True)

    open_parser = run_subparsers.add_parser("open")
    open_parser.add_argument("--run-id", dest="run_id", default=None)
    open_parser.set_defaults(func=_cmd_run_open)

    validate_profile_parser = run_subparsers.add_parser("validate-profile")
    validate_profile_parser.add_argument("--run-id", dest="run_id", required=True)
    validate_profile_parser.set_defaults(func=_cmd_run_validate_profile)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--run-id", dest="run_id", required=True)
    scan_parser.add_argument("--type", dest="type", required=True)
    scan_parser.add_argument("--art-id", dest="art_id", required=True)
    scan_parser.set_defaults(func=_cmd_scan)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--run-id", dest="run_id", required=True)
    review_parser.add_argument("--type", dest="type", required=True)
    review_parser.add_argument("--art-id", dest="art_id", required=True)
    review_parser.set_defaults(func=_cmd_review)

    accept_parser = subparsers.add_parser("accept")
    accept_parser.add_argument("--run-id", dest="run_id", required=True)
    accept_parser.add_argument("--type", dest="type", required=True)
    accept_parser.add_argument("--art-id", dest="art_id", required=True)
    accept_parser.add_argument("--summary", dest="summary", required=True)
    accept_parser.set_defaults(func=_cmd_accept)

    state_parser = subparsers.add_parser("state")
    state_subparsers = state_parser.add_subparsers(dest="state_command", required=True)

    state_enter_parser = state_subparsers.add_parser("enter")
    state_enter_parser.add_argument("--run-id", dest="run_id", required=True)
    state_enter_parser.add_argument("--state", dest="state", required=True)
    state_enter_parser.add_argument("--waiver", dest="waiver", default=None)
    state_enter_parser.add_argument("--cause", dest="cause", default=None)
    state_enter_parser.set_defaults(func=_cmd_state_enter)

    state_derive_parser = state_subparsers.add_parser("derive")
    state_derive_parser.add_argument("--run-id", dest="run_id", required=True)
    state_derive_parser.set_defaults(func=_cmd_state_derive)

    monitor_parser = subparsers.add_parser("monitor")
    monitor_subparsers = monitor_parser.add_subparsers(dest="monitor_command", required=True)

    monitor_mark_dormant_parser = monitor_subparsers.add_parser("mark-dormant")
    monitor_mark_dormant_parser.add_argument("--run-id", dest="run_id", required=True)
    monitor_mark_dormant_parser.add_argument(
        "--revival-conditions", dest="revival_conditions", required=True
    )
    monitor_mark_dormant_parser.set_defaults(func=_cmd_monitor_mark_dormant)

    monitor_sweep_parser = monitor_subparsers.add_parser("sweep")
    monitor_sweep_parser.add_argument("--run-id", dest="run_id", required=True)
    monitor_sweep_parser.set_defaults(func=_cmd_monitor_sweep)

    budgets_parser = subparsers.add_parser("budgets")
    budgets_subparsers = budgets_parser.add_subparsers(dest="budgets_command", required=True)

    budgets_set_parser = budgets_subparsers.add_parser("set")
    budgets_set_parser.add_argument("--run-id", dest="run_id", required=True)
    budgets_set_parser.add_argument("--clusters", dest="clusters_json", required=True)
    budgets_set_parser.add_argument(
        "--papers-per-cluster", dest="papers_per_cluster", type=int, required=True
    )
    budgets_set_parser.add_argument("--time-horizon", dest="time_horizon", required=True)
    budgets_set_parser.set_defaults(func=_cmd_budgets_set)

    budgets_get_parser = budgets_subparsers.add_parser("get")
    budgets_get_parser.add_argument("--run-id", dest="run_id", required=True)
    budgets_get_parser.set_defaults(func=_cmd_budgets_get)

    budgets_check_parser = budgets_subparsers.add_parser("check-exhaustion")
    budgets_check_parser.add_argument("--run-id", dest="run_id", required=True)
    budgets_check_parser.add_argument("--cluster-id", dest="cluster_id", required=True)
    budgets_check_parser.add_argument(
        "--papers-read-count", dest="papers_read_count", type=int, required=True
    )
    budgets_check_parser.set_defaults(func=_cmd_budgets_check_exhaustion)

    entry_parser = subparsers.add_parser("entry")
    entry_subparsers = entry_parser.add_subparsers(dest="entry_command", required=True)

    entry_start_parser = entry_subparsers.add_parser("start")
    entry_start_parser.add_argument("--run-id", dest="run_id", required=True)
    entry_start_parser.add_argument("--entry-mode", dest="entry_mode", required=True)
    entry_start_parser.add_argument("--raw-capture", dest="raw_capture", required=True)
    entry_start_parser.set_defaults(func=_cmd_entry_start)

    frame_parser = subparsers.add_parser("frame")
    frame_subparsers = frame_parser.add_subparsers(dest="frame_command", required=True)

    frame_complete_parser = frame_subparsers.add_parser("complete")
    frame_complete_parser.add_argument("--run-id", dest="run_id", required=True)
    frame_complete_parser.add_argument("--unprimed-answer", dest="unprimed_answer", required=True)
    frame_complete_parser.add_argument("--scope-answer", dest="scope_answer", required=True)
    frame_complete_parser.add_argument("--fields", dest="fields_json", required=True)
    frame_complete_parser.add_argument("--sections", dest="sections_json", required=True)
    frame_complete_parser.add_argument("--summary", dest="summary", required=True)
    frame_complete_parser.set_defaults(func=_cmd_frame_complete)

    deepen_parser = subparsers.add_parser("deepen")
    deepen_subparsers = deepen_parser.add_subparsers(dest="deepen_command", required=True)

    deepen_claim_parser = deepen_subparsers.add_parser("claim")
    deepen_claim_parser.add_argument("--run-id", dest="run_id", required=True)
    deepen_claim_parser.add_argument("--art-id", dest="art_id", required=True)
    deepen_claim_parser.add_argument("--sections", dest="sections_json", required=True)
    deepen_claim_parser.add_argument("--holder", dest="holder", required=True)
    deepen_claim_parser.set_defaults(func=_cmd_deepen_claim)

    repair_parser = subparsers.add_parser("repair")
    repair_subparsers = repair_parser.add_subparsers(dest="repair_command", required=True)

    repair_check_parser = repair_subparsers.add_parser("check")
    repair_check_parser.add_argument("--run-id", dest="run_id", required=True)
    repair_check_parser.add_argument("--type", dest="type", required=True)
    repair_check_parser.add_argument("--art-id", dest="art_id", required=True)
    repair_check_parser.set_defaults(func=_cmd_repair_check)

    repair_apply_parser = repair_subparsers.add_parser("apply")
    repair_apply_parser.add_argument("--run-id", dest="run_id", required=True)
    repair_apply_parser.add_argument("--type", dest="type", required=True)
    repair_apply_parser.add_argument("--art-id", dest="art_id", required=True)
    repair_apply_parser.add_argument("--fixes", dest="fixes_json", required=True)
    repair_apply_parser.set_defaults(func=_cmd_repair_apply)

    skeptic_parser = subparsers.add_parser("skeptic")
    skeptic_subparsers = skeptic_parser.add_subparsers(dest="skeptic_command", required=True)

    skeptic_context_parser = skeptic_subparsers.add_parser("context")
    skeptic_context_parser.add_argument("--run-id", dest="run_id", required=True)
    skeptic_context_parser.add_argument("--type", dest="type", required=True)
    skeptic_context_parser.add_argument("--art-id", dest="art_id", required=True)
    skeptic_context_parser.set_defaults(func=_cmd_skeptic_context)

    skeptic_critique_parser = skeptic_subparsers.add_parser("critique")
    skeptic_critique_parser.add_argument("--run-id", dest="run_id", required=True)
    skeptic_critique_parser.add_argument("--type", dest="type", required=True)
    skeptic_critique_parser.add_argument("--art-id", dest="art_id", required=True)
    skeptic_critique_parser.add_argument("--objection", dest="objection", required=True)
    skeptic_critique_parser.add_argument("--evidence", dest="evidence_json", required=True)
    skeptic_critique_parser.set_defaults(func=_cmd_skeptic_critique)

    skeptic_write_parser = skeptic_subparsers.add_parser("write")
    skeptic_write_parser.add_argument("--run-id", dest="run_id", required=True)
    skeptic_write_parser.add_argument("--type", dest="type", required=True)
    skeptic_write_parser.add_argument("--art-id", dest="art_id", required=True)
    skeptic_write_parser.add_argument("--section", dest="section", required=True)
    skeptic_write_parser.add_argument("--body", dest="body", required=True)
    skeptic_write_parser.set_defaults(func=_cmd_skeptic_write)

    historian_parser = subparsers.add_parser("historian")
    historian_subparsers = historian_parser.add_subparsers(dest="historian_command", required=True)

    historian_write_parser = historian_subparsers.add_parser("write")
    historian_write_parser.add_argument("--run-id", dest="run_id", required=True)
    historian_write_parser.add_argument("--art-id", dest="art_id", required=True)
    historian_write_parser.add_argument("--section", dest="section", required=True)
    historian_write_parser.add_argument("--body", dest="body", required=True)
    historian_write_parser.set_defaults(func=_cmd_historian_write)

    dossier_parser = subparsers.add_parser("dossier")
    dossier_subparsers = dossier_parser.add_subparsers(dest="dossier_command", required=True)

    dossier_create_parser = dossier_subparsers.add_parser("create")
    dossier_create_parser.add_argument("--run-id", dest="run_id", required=True)
    dossier_create_parser.add_argument("--field-map-id", dest="field_map_id", required=True)
    dossier_create_parser.add_argument(
        "--representative-papers", dest="representative_papers_json", required=True
    )
    dossier_create_parser.set_defaults(func=_cmd_dossier_create)

    dossier_mark_read_parser = dossier_subparsers.add_parser("mark-read")
    dossier_mark_read_parser.add_argument("--run-id", dest="run_id", required=True)
    dossier_mark_read_parser.add_argument("--art-id", dest="art_id", required=True)
    dossier_mark_read_parser.add_argument("--paper-id", dest="paper_id", required=True)
    dossier_mark_read_parser.add_argument("--reaction", dest="reaction", required=True)
    dossier_mark_read_parser.set_defaults(func=_cmd_dossier_mark_read)

    dossier_validate_parser = dossier_subparsers.add_parser("validate-deepen-exit")
    dossier_validate_parser.add_argument("--run-id", dest="run_id", required=True)
    dossier_validate_parser.add_argument("--art-id", dest="art_id", required=True)
    dossier_validate_parser.set_defaults(func=_cmd_dossier_validate_deepen_exit)

    dissolution_parser = subparsers.add_parser("dissolution")
    dissolution_subparsers = dissolution_parser.add_subparsers(dest="dissolution_command", required=True)

    dissolution_draft_parser = dissolution_subparsers.add_parser("draft")
    dissolution_draft_parser.add_argument("--run-id", dest="run_id", required=True)
    dissolution_draft_parser.add_argument("--intuition-summary", dest="intuition_summary", required=True)
    dissolution_draft_parser.add_argument(
        "--dissolving-evidence", dest="dissolving_evidence_json", required=True
    )
    dissolution_draft_parser.add_argument(
        "--dissolving-ledger-refs", dest="dissolving_ledger_refs_json", default=None
    )
    dissolution_draft_parser.set_defaults(func=_cmd_dissolution_draft)

    dissolution_record_learned_parser = dissolution_subparsers.add_parser("record-learned")
    dissolution_record_learned_parser.add_argument("--run-id", dest="run_id", required=True)
    dissolution_record_learned_parser.add_argument("--art-id", dest="art_id", required=True)
    dissolution_record_learned_parser.add_argument("--content", dest="content", required=True)
    dissolution_record_learned_parser.set_defaults(func=_cmd_dissolution_record_learned)

    dissolution_record_revival_parser = dissolution_subparsers.add_parser("record-revival-conditions")
    dissolution_record_revival_parser.add_argument("--run-id", dest="run_id", required=True)
    dissolution_record_revival_parser.add_argument("--art-id", dest="art_id", required=True)
    dissolution_record_revival_parser.add_argument("--content", dest="content", required=True)
    dissolution_record_revival_parser.set_defaults(func=_cmd_dissolution_record_revival_conditions)

    dissolution_spin_off_parser = dissolution_subparsers.add_parser("spin-off-fragment")
    dissolution_spin_off_parser.add_argument("--run-id", dest="run_id", required=True)
    dissolution_spin_off_parser.add_argument("--art-id", dest="art_id", required=True)
    dissolution_spin_off_parser.add_argument("--raw-capture", dest="raw_capture", required=True)
    dissolution_spin_off_parser.add_argument(
        "--entry-mode", dest="entry_mode", default="intuition-first"
    )
    dissolution_spin_off_parser.set_defaults(func=_cmd_dissolution_spin_off_fragment)

    dissolution_validate_exit_parser = dissolution_subparsers.add_parser("validate-exit")
    dissolution_validate_exit_parser.add_argument("--run-id", dest="run_id", required=True)
    dissolution_validate_exit_parser.add_argument("--art-id", dest="art_id", required=True)
    dissolution_validate_exit_parser.set_defaults(func=_cmd_dissolution_validate_exit)

    dissolution_check_terminal_parser = dissolution_subparsers.add_parser("check-terminal")
    dissolution_check_terminal_parser.add_argument("--run-id", dest="run_id", required=True)
    dissolution_check_terminal_parser.set_defaults(func=_cmd_dissolution_check_terminal)

    synthesize_parser = subparsers.add_parser("synthesize")
    synthesize_subparsers = synthesize_parser.add_subparsers(dest="synthesize_command", required=True)

    synthesize_create_parser = synthesize_subparsers.add_parser("create")
    synthesize_create_parser.add_argument("--run-id", dest="run_id", required=True)
    synthesize_create_parser.set_defaults(func=_cmd_synthesize_create)

    synthesize_write_parser = synthesize_subparsers.add_parser("write")
    synthesize_write_parser.add_argument("--run-id", dest="run_id", required=True)
    synthesize_write_parser.add_argument("--art-id", dest="art_id", required=True)
    synthesize_write_parser.add_argument("--field", dest="field", required=True)
    synthesize_write_parser.add_argument("--rows", dest="rows_json", required=True)
    synthesize_write_parser.add_argument("--dossier-ids", dest="dossier_ids_json", required=True)
    synthesize_write_parser.set_defaults(func=_cmd_synthesize_write)

    synthesize_validate_parser = synthesize_subparsers.add_parser("validate")
    synthesize_validate_parser.add_argument("--run-id", dest="run_id", required=True)
    synthesize_validate_parser.add_argument("--art-id", dest="art_id", required=True)
    synthesize_validate_parser.set_defaults(func=_cmd_synthesize_validate)

    locate_parser = subparsers.add_parser("locate")
    locate_subparsers = locate_parser.add_subparsers(dest="locate_command", required=True)

    locate_create_parser = locate_subparsers.add_parser("create")
    locate_create_parser.add_argument("--run-id", dest="run_id", required=True)
    locate_create_parser.add_argument("--statement", dest="statement", required=True)
    locate_create_parser.add_argument(
        "--evidence-of-absence", dest="evidence_of_absence", required=True
    )
    locate_create_parser.set_defaults(func=_cmd_locate_create)

    locate_write_parser = locate_subparsers.add_parser("write")
    locate_write_parser.add_argument("--run-id", dest="run_id", required=True)
    locate_write_parser.add_argument("--art-id", dest="art_id", required=True)
    locate_write_parser.add_argument("--field", dest="field", required=True)
    locate_write_parser.add_argument("--content", dest="content", required=True)
    locate_write_parser.set_defaults(func=_cmd_locate_write)

    locate_mark_meaningful_parser = locate_subparsers.add_parser("mark-meaningful")
    locate_mark_meaningful_parser.add_argument("--run-id", dest="run_id", required=True)
    locate_mark_meaningful_parser.add_argument("--art-id", dest="art_id", required=True)
    locate_mark_meaningful_parser.add_argument("--disposition", dest="disposition", required=True)
    locate_mark_meaningful_parser.set_defaults(func=_cmd_locate_mark_meaningful)

    locate_record_micro_probe_parser = locate_subparsers.add_parser("record-micro-probe")
    locate_record_micro_probe_parser.add_argument("--run-id", dest="run_id", required=True)
    locate_record_micro_probe_parser.add_argument("--art-id", dest="art_id", required=True)
    locate_record_micro_probe_parser.add_argument("--evidence", dest="evidence", required=True)
    locate_record_micro_probe_parser.set_defaults(func=_cmd_locate_record_micro_probe)

    locate_validate_exit_parser = locate_subparsers.add_parser("validate-locate-exit")
    locate_validate_exit_parser.add_argument("--run-id", dest="run_id", required=True)
    locate_validate_exit_parser.add_argument("--art-id", dest="art_id", required=True)
    locate_validate_exit_parser.set_defaults(func=_cmd_locate_validate_exit)

    locate_check_terminal_parser = locate_subparsers.add_parser("check-terminal")
    locate_check_terminal_parser.add_argument("--run-id", dest="run_id", required=True)
    locate_check_terminal_parser.set_defaults(func=_cmd_locate_check_terminal)

    cartographer_parser = subparsers.add_parser("cartographer")
    cartographer_subparsers = cartographer_parser.add_subparsers(
        dest="cartographer_command", required=True
    )

    cartographer_draft_parser = cartographer_subparsers.add_parser("draft")
    cartographer_draft_parser.add_argument("--papers", dest="papers_json", required=True)
    cartographer_draft_parser.set_defaults(func=_cmd_cartographer_draft)

    cartographer_create_parser = cartographer_subparsers.add_parser("create")
    cartographer_create_parser.add_argument("--run-id", dest="run_id", required=True)
    cartographer_create_parser.add_argument("--papers", dest="papers_json", required=True)
    cartographer_create_parser.add_argument("--cuts", dest="cuts_json", required=True)
    cartographer_create_parser.add_argument("--chosen-basis", dest="chosen_basis", required=True)
    cartographer_create_parser.set_defaults(func=_cmd_cartographer_create)

    corpus_parser = subparsers.add_parser("corpus")
    corpus_subparsers = corpus_parser.add_subparsers(dest="corpus_command", required=True)

    corpus_search_parser = corpus_subparsers.add_parser("search")
    corpus_search_parser.add_argument("--run-id", dest="run_id", required=True)
    corpus_search_parser.add_argument("--role", dest="role", required=True)
    corpus_search_parser.add_argument("--query", dest="query", required=True)
    corpus_search_parser.add_argument(
        "--limit", dest="limit", type=int, default=DEFAULT_SEARCH_LIMIT
    )
    corpus_search_parser.add_argument("--provider", dest="provider", default=None)
    corpus_search_parser.set_defaults(func=_cmd_corpus_search)

    corpus_expand_parser = corpus_subparsers.add_parser("expand")
    corpus_expand_parser.add_argument("--run-id", dest="run_id", required=True)
    corpus_expand_parser.add_argument("--role", dest="role", required=True)
    corpus_expand_parser.add_argument("--canonical-key", dest="canonical_key", required=True)
    corpus_expand_parser.add_argument("--provider", dest="provider", default=None)
    corpus_expand_parser.set_defaults(func=_cmd_corpus_expand)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--run-id", dest="run_id", required=True)
    read_parser.add_argument("--state", dest="state", required=True)
    read_parser.add_argument("--type", dest="type", required=True)
    read_parser.add_argument("--art-id", dest="art_id", required=True)
    read_parser.add_argument(
        "--resolution", dest="resolution", required=True, choices=("summary", "full")
    )
    read_parser.set_defaults(func=_cmd_read)

    ask_parser = subparsers.add_parser("ask")
    ask_subparsers = ask_parser.add_subparsers(dest="ask_command", required=True)

    emit_parser = ask_subparsers.add_parser("emit")
    emit_parser.add_argument("--run-id", dest="run_id", required=True)
    emit_parser.add_argument("--questions", dest="questions_json", required=True)
    emit_parser.set_defaults(func=_cmd_ask_emit)

    answer_parser = ask_subparsers.add_parser("answer")
    answer_parser.add_argument("--run-id", dest="run_id", required=True)
    answer_parser.add_argument("--id", dest="id", required=True)
    answer_parser.add_argument("--answer", dest="answer", required=True)
    answer_parser.set_defaults(func=_cmd_ask_answer)

    revise_parser = ask_subparsers.add_parser("revise")
    revise_parser.add_argument("--run-id", dest="run_id", required=True)
    revise_parser.add_argument("--id", dest="id", required=True)
    revise_parser.add_argument("--answer", dest="answer", required=True)
    revise_parser.set_defaults(func=_cmd_ask_revise)

    metrics_parser = subparsers.add_parser("metrics")
    metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_command", required=True)

    provisional_count_parser = metrics_subparsers.add_parser("provisional-count")
    provisional_count_parser.add_argument("--run-id", dest="run_id", required=True)
    provisional_count_parser.set_defaults(func=_cmd_metrics_provisional_count)

    summary_sufficiency_parser = metrics_subparsers.add_parser("summary-sufficiency")
    summary_sufficiency_parser.add_argument("--run-id", dest="run_id", required=True)
    summary_sufficiency_parser.set_defaults(func=_cmd_metrics_summary_sufficiency)

    derived_parser = metrics_subparsers.add_parser("derived")
    derived_parser.add_argument("--run-id", dest="run_id", required=True)
    derived_parser.set_defaults(func=_cmd_metrics_derived)

    rediscovery_rate_parser = metrics_subparsers.add_parser("rediscovery-rate")
    rediscovery_rate_parser.add_argument("--run-id", dest="run_id", required=True)
    rediscovery_rate_parser.add_argument(
        "--window", dest="window", type=int, default=DEFAULT_REDISCOVERY_WINDOW
    )
    rediscovery_rate_parser.set_defaults(func=_cmd_metrics_rediscovery_rate)

    charter_audit_parser = metrics_subparsers.add_parser("charter-audit")
    charter_audit_parser.add_argument("--run-id", dest="run_id", required=True)
    charter_audit_parser.set_defaults(func=_cmd_metrics_charter_audit)

    shared_payload_parser = metrics_subparsers.add_parser("shared-payload")
    shared_payload_parser.add_argument("--run-id", dest="run_id", required=True)
    shared_payload_parser.set_defaults(func=_cmd_metrics_shared_payload)

    gate_parser = subparsers.add_parser("gate")
    gate_subparsers = gate_parser.add_subparsers(dest="gate_command", required=True)

    gate_propose_parser = gate_subparsers.add_parser("propose")
    gate_propose_parser.add_argument("--run-id", dest="run_id", required=True)
    gate_propose_parser.add_argument("--type", dest="type", required=True)
    gate_propose_parser.set_defaults(func=_cmd_gate_propose)

    gate_approve_parser = gate_subparsers.add_parser("approve")
    gate_approve_parser.add_argument("--run-id", dest="run_id", required=True)
    gate_approve_parser.add_argument("--type", dest="type", required=True)
    gate_approve_parser.set_defaults(func=_cmd_gate_approve)

    report_parser = subparsers.add_parser("report")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)

    report_llm_call_parser = report_subparsers.add_parser("llm-call")
    report_llm_call_parser.add_argument("--run-id", dest="run_id", required=True)
    report_llm_call_parser.add_argument("--role", dest="role", required=True)
    report_llm_call_parser.add_argument(
        "--operation-class", dest="operation_class", required=True
    )
    report_llm_call_parser.add_argument("--model-tier", dest="model_tier", required=True)
    report_llm_call_parser.add_argument(
        "--tokens-in", dest="tokens_in", type=int, required=True
    )
    report_llm_call_parser.add_argument(
        "--tokens-out", dest="tokens_out", type=int, required=True
    )
    report_llm_call_parser.add_argument(
        "--cache-hit", dest="cache_hit", choices=("true", "false"), required=True
    )
    report_llm_call_parser.add_argument(
        "--call-id", dest="call_id", default=None,
        help="idempotency key (AD-26); auto-minted via uuid4 when omitted",
    )
    report_llm_call_parser.set_defaults(func=_cmd_report_llm_call)

    dispatch_parser = subparsers.add_parser("dispatch")
    dispatch_subparsers = dispatch_parser.add_subparsers(dest="dispatch_command", required=True)

    dispatch_resolve_parser = dispatch_subparsers.add_parser("resolve")
    dispatch_resolve_parser.add_argument(
        "--operation-class", dest="operation_class", required=True
    )
    dispatch_resolve_parser.set_defaults(func=_cmd_dispatch_resolve)

    appraisal_parser = subparsers.add_parser("appraisal")
    appraisal_subparsers = appraisal_parser.add_subparsers(dest="appraisal_command", required=True)

    appraisal_record_parser = appraisal_subparsers.add_parser("record")
    appraisal_record_parser.add_argument("--run-id", dest="run_id", required=True)
    appraisal_record_parser.add_argument("--paper-id", dest="paper_id", required=True)
    appraisal_record_parser.add_argument("--judgment", dest="judgment", required=True)
    appraisal_record_parser.add_argument("--frame-version", dest="frame_version", required=True)
    appraisal_record_parser.add_argument("--reason", dest="reason", required=True)
    appraisal_record_parser.set_defaults(func=_cmd_appraisal_record)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _normalize_case_insensitive_args(args)
    try:
        result = args.func(args)
    except json.JSONDecodeError as exc:
        # Several _cmd_* functions parse a --X-json argument before their
        # own try/except begins (e.g. _cmd_frame_complete); malformed JSON
        # from the harness must be a clean refusal the ceiling below can
        # act on, never an unhandled crash — a crash is a worse safety
        # failure than a silent hang (Story 7.4's own scope).
        result = {"ok": False, "error": f"malformed JSON argument: {exc}"}

    run_id = getattr(args, "run_id", None)
    # AD-26(a) tracks true refusals, never a "violations" check's normal,
    # expected not-yet-satisfied result. Several commands share the
    # {"ok": len(violations) == 0, "violations": [...]} contract (e.g.
    # validate_deepen_exit, validate_locate_exit, validate_landscape_
    # synthesis, validate_minimal_profile) — a `False` there means "this
    # artifact isn't done yet," not "this call failed." Discovered live
    # while driving the Story 7.5 toy run: without this check, an ordinary
    # validate-fix-validate-fix loop while completing a Gap Register would
    # have wrongly escalated to requires_researcher after 3 legitimate
    # checks. Detected structurally (the "violations" key), not by a
    # command-name allowlist, so it covers this contract wherever it's
    # used, including future callers.
    is_informational_check = "violations" in result
    if not result.get("ok") and run_id and not is_informational_check:
        # FR-48/AD-26(a): every refusal against a run is logged and checked
        # against the consecutive-identical-refusal ceiling — a
        # core-enforced backstop against a retry-storm burning tokens,
        # never something a skill/harness rule alone could guarantee
        # (AD-1's amendment note).
        config = load_config(Path.cwd())
        ceiling = config.get("refusal_ceiling", DEFAULT_REFUSAL_CEILING)
        run_dir = _run_dir(run_id)
        if run_dir.is_dir():
            escalation = record_refusal_and_check_ceiling(
                run_dir, _entrypoint_key(args), _target_key(args), result.get("error"), ceiling
            )
            if escalation["escalate"]:
                result = {
                    "ok": False,
                    "status": "requires_researcher",
                    "error": result.get("error"),
                    "consecutive_refusals": escalation["count"],
                }

    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
