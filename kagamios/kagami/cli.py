import argparse
import json
import sys

from kagami.paths import resolve_output_root
from kagami.schema_version import SchemaVersionError
from kagami.store.artifact import ArtifactError, scan
from kagami.store.run import open_run


def _cmd_run_open(args: argparse.Namespace) -> dict:
    try:
        return open_run(run_id=args.run_id)
    except SchemaVersionError as exc:
        return {"ok": False, "error": str(exc)}


def _cmd_scan(args: argparse.Namespace) -> dict:
    run_dir = resolve_output_root() / "runs" / args.run_id
    try:
        return scan(run_dir, args.type, args.art_id)
    except (ArtifactError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
