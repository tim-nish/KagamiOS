import argparse
import json
import sys

from kagami.paths import resolve_output_root
from kagami.schema_version import SchemaVersionError
from kagami.store import ledger
from kagami.store.artifact import ArtifactError, count_provisional, scan
from kagami.store.ledger import LedgerError
from kagami.store.run import open_run


def _run_dir(run_id: str):
    return resolve_output_root() / "runs" / run_id


def _cmd_run_open(args: argparse.Namespace) -> dict:
    try:
        return open_run(run_id=args.run_id)
    except SchemaVersionError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_scan(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    try:
        return scan(run_dir, args.type, args.art_id)
    except (ArtifactError, FileNotFoundError) as exc:
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


def _cmd_metrics_provisional_count(args: argparse.Namespace) -> dict:
    run_dir = _run_dir(args.run_id)
    return {"ok": True, "provisional_count": count_provisional(run_dir)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kagami")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_subparsers = run_parser.add_subparsers(dest="run_command", required=True)

    open_parser = run_subparsers.add_parser("open")
    open_parser.add_argument("--run-id", dest="run_id", default=None)
    open_parser.set_defaults(func=_cmd_run_open)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("--run-id", dest="run_id", required=True)
    scan_parser.add_argument("--type", dest="type", required=True)
    scan_parser.add_argument("--art-id", dest="art_id", required=True)
    scan_parser.set_defaults(func=_cmd_scan)

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
