import argparse
import json
import sys
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
from kagami.kernel.dossier import DossierError, mark_representative_paper_read, validate_deepen_exit
from kagami.kernel.entry import EntryError, start_run_from_entry
from kagami.kernel.frame import complete_frame
from kagami.kernel.gate_trust import GateTrustError, approve_gate_loosening, propose_gate_loosening
from kagami.kernel.historian import HistorianError, historian_write
from kagami.kernel.locate import (
    LocateError,
    check_mvp_terminal,
    locate_write,
    mark_gap_meaningful,
    record_micro_probe_evidence,
    validate_locate_exit,
)
from kagami.kernel.metrics import count_full_pull_after_summary
from kagami.kernel.profile import validate_minimal_profile
from kagami.kernel.repair import apply_tier2_repair, repair_artifact
from kagami.kernel.scout import CorpusAccessError, search_corpus
from kagami.kernel.skeptic import SkepticError, build_skeptic_context, record_skeptic_critique, skeptic_write
from kagami.kernel.state_machine import StateMachineError, enter_state
from kagami.kernel.synthesize import SynthesizeError, synthesize_write, validate_landscape_synthesis
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
        provider = resolve_provider(config)
        return search_corpus(run_dir, output_root, provider, args.query, args.role)
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


def _cmd_dossier_mark_read(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return mark_representative_paper_read(run_dir, args.art_id, args.paper_id, args.reaction)
    except DossierError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_dossier_validate_deepen_exit(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return validate_deepen_exit(run_dir, args.art_id)


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
    corpus_search_parser.set_defaults(func=_cmd_corpus_search)

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
