import json
from pathlib import Path

# FR-39: only these categorical, code-defined (never free-text) fields may
# travel in a shared payload. Every event's `family`/`kind` pair is always a
# fixed vocabulary string the code itself emits, never derived from a
# researcher's own words — same for `role`, `leverage_class`, and
# `artifact_type`, all schema/registry enums. Everything else on an event
# (question targets and answers, revival conditions, corpus queries, paper
# ids, red-team objections, free-line causes/waivers) stays local.
SHAREABLE_CLASS_FIELDS = ("role", "leverage_class", "artifact_type")


class PrivacyError(Exception):
    pass


def sharing_enabled(config: dict) -> bool:
    """AD-12/FR-39: the sharing flag defaults to off and only this
    researcher's own explicit `config.yaml` edit can turn it on — nothing
    in this core ever writes `config.yaml`."""
    return bool((config or {}).get("sharing_enabled", False))


def _read_events(run_dir: Path) -> list:
    path = run_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def _counts_by(values: list) -> dict:
    counts: dict = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def generate_shared_payload(run_dir: Path, config: dict) -> dict:
    """FR-39: with sharing disabled (the default), refuses outright rather
    than producing anything — no event data leaves the local store. With
    sharing enabled, the payload carries only event shapes (family::kind),
    counts, and the fixed-vocabulary classes in `SHAREABLE_CLASS_FIELDS` —
    never verbatim question text, artifact content, or paper identities.
    """
    if not sharing_enabled(config):
        raise PrivacyError(
            "sharing is disabled by default (FR-39/AD-12); enable 'sharing_enabled: true' "
            "in config.yaml yourself before a shared payload can be generated"
        )

    events = _read_events(run_dir)

    payload = {
        "ok": True,
        "event_count": len(events),
        "event_class_counts": _counts_by(
            [f"{event.get('family')}::{event.get('kind')}" for event in events]
        ),
    }
    for field_name in SHAREABLE_CLASS_FIELDS:
        payload[f"{field_name}_counts"] = _counts_by(
            [event[field_name] for event in events if event.get(field_name)]
        )

    return payload
