from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.store.atomic import atomic_write
from kagami.store.ids import mint_id
from kagami.store.locking import acquire_run_lock
from kagami.timeutil import utc_now_iso


class AppraisalError(Exception):
    pass


def _appraisals_dir(run_dir: Path) -> Path:
    return run_dir / "appraisals"


def _entry_path(run_dir: Path, appraisal_id: str) -> Path:
    return _appraisals_dir(run_dir) / f"{appraisal_id}.yaml"


def record_appraisal(
    run_dir: Path, paper_id: str, judgment: str, frame_version: str, reason: str
) -> dict:
    """FR-52/AD-28: a frame-dependent judgment about a paper, recorded
    structurally separate from that paper's frame-independent card (AD-18,
    `kagami/corpus/cache.py`). Every appraisal is stamped with the Inquiry
    Frame version that produced it — on frame revision, a prior appraisal is
    never implicitly carried forward as still valid for the new version;
    re-appraising is a distinct, separately recorded act (see
    `current_appraisal_for_paper`), and the paper card the appraisal
    references is never touched by this write.

    Run-scoped: appraisals live under `runs/<run-id>/appraisals/`, not the
    cross-run corpus cache (AD-13) — a judgment about a paper belongs to the
    run and frame that produced it, never to the paper itself.
    """
    if not paper_id or not judgment or not frame_version:
        raise AppraisalError(
            "paper_id, judgment, and frame_version are all required to record an appraisal (FR-52)"
        )

    appraisal_id = mint_id("apr-")
    entry = {
        "id": appraisal_id,
        "paper_id": paper_id,
        "judgment": judgment,
        "frame_version": frame_version,
        "reason": reason or "",
        "recorded_at": utc_now_iso(),
    }

    with acquire_run_lock(run_dir / ".lock"):
        _appraisals_dir(run_dir).mkdir(parents=True, exist_ok=True)
        atomic_write(_entry_path(run_dir, appraisal_id), yaml.safe_dump(entry, sort_keys=False))
        append_event(
            run_dir,
            "artifact_event",
            {
                "kind": "appraisal_recorded",
                "appraisal_id": appraisal_id,
                "paper_id": paper_id,
                "frame_version": frame_version,
            },
        )

    return {"ok": True, "id": appraisal_id}


def list_appraisals_for_paper(run_dir: Path, paper_id: str) -> list[dict]:
    """Every appraisal ever recorded for `paper_id` in this run, oldest
    first — including ones stamped with an earlier `frame_version`, since
    re-appraisal on frame revision is additive (a new entry), never an edit
    of the prior one (FR-52)."""
    appraisals_dir = _appraisals_dir(run_dir)
    if not appraisals_dir.exists():
        return []
    entries = [yaml.safe_load(path.read_text()) for path in sorted(appraisals_dir.glob("*.yaml"))]
    return [entry for entry in entries if entry.get("paper_id") == paper_id]


def current_appraisal_for_paper(run_dir: Path, paper_id: str, frame_version: str) -> dict | None:
    """FR-52: the appraisal (if any) recorded specifically against
    `frame_version` — an appraisal stamped with an older frame_version is
    never treated as still valid for a newer one; the caller gets `None`
    until this paper is re-appraised against the current frame."""
    matches = [
        entry
        for entry in list_appraisals_for_paper(run_dir, paper_id)
        if entry.get("frame_version") == frame_version
    ]
    return matches[-1] if matches else None
