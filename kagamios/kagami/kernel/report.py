import json
from pathlib import Path

from kagami.events import append_event
from kagami.registry import ROLES
from kagami.store.locking import acquire_run_lock


class ReportError(Exception):
    pass


def _reported_call_ids(run_dir: Path) -> set[str]:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return set()
    ids: set[str] = set()
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event.get("family") == "llm_call" and event.get("call_id"):
            ids.add(event["call_id"])
    return ids


def report_llm_call(
    run_dir: Path,
    role: str,
    operation_class: str,
    model_tier: str,
    tokens_in: int,
    tokens_out: int,
    cache_hit: bool,
    call_id: str,
) -> dict:
    """FR-49/AD-26(b): the harness reports every model call it makes through
    this validated entrypoint immediately after the call — the core never
    invokes models itself and never infers `role`/`operation_class`/
    `model_tier`/token counts/`cache_hit`. A call made but never reported
    through here is invisible to the token ledger (FR-37) and the charter
    audit (FR-29): an accepted, logged AD-11 honest-gap, never silently
    corrected or inferred after the fact.

    `call_id` is a harness-minted idempotency key (a UUID per model call).
    A report whose `call_id` already appears among this run's `llm_call`
    events is refused — a retried report can never double-inflate the
    ledger (AD-26).
    """
    if not call_id or not call_id.strip():
        raise ReportError("call_id must be non-empty (AD-26: idempotency guard)")
    if not role or not role.strip():
        raise ReportError("an 'llm_call' report must carry a non-null role tag (FR-29)")
    if role not in ROLES:
        raise ReportError(
            f"'{role}' is not a recognized role; must be one of {ROLES} "
            "(AD-4/AD-26: self-declared role must be schema-registry-enumerated)"
        )

    with acquire_run_lock(run_dir / ".lock"):
        if call_id in _reported_call_ids(run_dir):
            raise ReportError(
                f"an llm_call with call_id '{call_id}' was already reported for this run "
                "(AD-26: duplicate report refused, ledger not double-inflated)"
            )
        event = append_event(
            run_dir,
            "llm_call",
            {
                "role": role,
                "operation_class": operation_class,
                "model_tier": model_tier,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cache_hit": bool(cache_hit),
                "call_id": call_id,
            },
        )
    return {"ok": True, "event": event}
