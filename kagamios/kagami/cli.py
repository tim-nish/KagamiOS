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
from kagami.kernel.entry import EntryError, start_run_from_entry
from kagami.kernel.frame import complete_frame
from kagami.kernel.metrics import count_full_pull_after_summary
from kagami.kernel.profile import validate_minimal_profile
from kagami.kernel.scout import CorpusAccessError, search_corpus
from kagami.kernel.state_machine import StateMachineError, enter_state
from kagami.paths import resolve_output_root
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
