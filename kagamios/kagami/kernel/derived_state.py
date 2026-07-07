import statistics
from pathlib import Path

import yaml

from kagami.events import append_event
from kagami.kernel.dossier import validate_deepen_exit
from kagami.registry import load_registry
from kagami.store.atomic import atomic_write
from kagami.store.locking import acquire_run_lock
from kagami.store.markdown_doc import parse_document

MAP_STATE = "map"
DEEPEN_STATE = "deepen"
PAST_DEEPEN_STATE = "synthesize"


class DepthBudgetError(Exception):
    pass


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "manifest.yaml"


def _read_manifest(run_dir: Path) -> dict:
    return yaml.safe_load(_manifest_path(run_dir).read_text())


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    atomic_write(_manifest_path(run_dir), yaml.safe_dump(manifest, sort_keys=False))


def _list_field_map_ids(run_dir: Path) -> list[str]:
    field_map_root = run_dir / "artifacts" / "field-map"
    if not field_map_root.exists():
        return []
    return sorted(p.name for p in field_map_root.iterdir() if p.is_dir())


def _artifact_status(run_dir: Path, type_slug: str, art_id: str) -> str:
    meta_path = run_dir / "artifacts" / type_slug / art_id / "meta.yaml"
    return yaml.safe_load(meta_path.read_text())["status"]


def _has_accepted_dossier_for_cluster(run_dir: Path, field_map_id: str) -> bool:
    dossier_root = run_dir / "artifacts" / "cluster-dossier"
    if not dossier_root.exists():
        return False
    pin_prefix = f"{field_map_id}@v"
    for meta_path in dossier_root.glob("*/meta.yaml"):
        meta = yaml.safe_load(meta_path.read_text())
        if meta.get("status") != "accepted":
            continue
        current_path = meta_path.parent / "current.md"
        frontmatter, _ = parse_document(current_path.read_text())
        if any(pin.startswith(pin_prefix) for pin in frontmatter.get("depends_on") or []):
            # FR-28/FR-59: acceptance alone isn't the Deepen exit criterion —
            # every representative paper must also carry a human-attributed
            # rating/confidence confirmation.
            if validate_deepen_exit(run_dir, meta["id"])["ok"]:
                return True
    return False


def compute_cluster_state(run_dir: Path, field_map_id: str) -> str:
    """FR-3/AD-20: a cluster's derived state is the earliest working state
    whose exit criteria that cluster hasn't yet met — a pure function over
    store state, never itself a stored fact."""
    status = _artifact_status(run_dir, "field-map", field_map_id)
    if status not in ("reviewed", "accepted"):
        return MAP_STATE  # Map's exit criterion: the card is human-edited or confirmed

    if not _has_accepted_dossier_for_cluster(run_dir, field_map_id):
        return DEEPEN_STATE  # Deepen's exit criterion: dossier reviewed + representative confirmed

    return PAST_DEEPEN_STATE  # cluster has cleared its own per-cluster work


def compute_run_nominal_state(run_dir: Path, registry=None) -> dict:
    """FR-3: the run's nominal state is the modal cluster state — computed,
    never read from a single stored field, and cached into the manifest
    for observability only (AD-20: the cache is never itself the guard's
    read path).
    """
    registry = registry or load_registry()
    field_map_ids = _list_field_map_ids(run_dir)

    per_cluster = {fm_id: compute_cluster_state(run_dir, fm_id) for fm_id in field_map_ids}

    if per_cluster:
        nominal = statistics.mode(per_cluster[fm_id] for fm_id in field_map_ids)
    else:
        manifest = _read_manifest(run_dir)
        nominal = (manifest.get("state_cache") or {}).get("current_state") or registry.states()[0]

    with acquire_run_lock(run_dir / ".lock"):
        manifest = _read_manifest(run_dir)
        manifest["derived_state_per_cluster"] = per_cluster
        _write_manifest(run_dir, manifest)

    return {"ok": True, "nominal_state": nominal, "per_cluster": per_cluster}


def set_depth_budgets(
    run_dir: Path, clusters_to_deepen: list[str], papers_per_cluster: int, time_horizon: str
) -> dict:
    """FR-45: human-owned, revisable at any point — set at Map exit, but
    calling this again later simply supersedes the prior budgets."""
    with acquire_run_lock(run_dir / ".lock"):
        manifest = _read_manifest(run_dir)
        manifest["depth_budgets"] = {
            "clusters_to_deepen": clusters_to_deepen,
            "papers_per_cluster": papers_per_cluster,
            "time_horizon": time_horizon,
        }
        _write_manifest(run_dir, manifest)
        append_event(
            run_dir,
            "budget_event",
            {"kind": "depth_budgets_set", "depth_budgets": manifest["depth_budgets"]},
        )

    return {"ok": True, "depth_budgets": manifest["depth_budgets"]}


def get_depth_budgets(run_dir: Path) -> dict | None:
    return _read_manifest(run_dir).get("depth_budgets")


def assert_depth_budgets_set(run_dir: Path) -> None:
    """FR-45: every run has recorded depth budgets before Deepen begins."""
    if get_depth_budgets(run_dir) is None:
        raise DepthBudgetError("depth budgets must be set before Deepen begins (FR-45)")


def _pending_exhaustion_question(run_dir: Path, cluster_id: str) -> str | None:
    ledger_dir = run_dir / "ledger"
    if not ledger_dir.exists():
        return None
    target = f"depth-budget.{cluster_id}"
    for path in ledger_dir.glob("*.yaml"):
        entry = yaml.safe_load(path.read_text())
        if entry.get("target") == target and entry.get("answered_at") is None:
            return entry["id"]
    return None


def detect_budget_exhaustion(run_dir: Path, cluster_id: str, papers_read_count: int) -> dict:
    """FR-45: exhaustion asks — never a silent stop, never a silent
    continuation. Exactly one extend-or-proceed question per exhaustion;
    an already-pending question for this cluster is never duplicated."""
    from kagami.store import ledger

    budgets = get_depth_budgets(run_dir)
    if budgets is None:
        raise DepthBudgetError("cannot check exhaustion before depth budgets are set (FR-45)")

    if papers_read_count < budgets["papers_per_cluster"]:
        return {"ok": True, "exhausted": False}

    existing = _pending_exhaustion_question(run_dir, cluster_id)
    if existing is not None:
        return {"ok": True, "exhausted": True, "question_id": existing, "newly_asked": False}

    result = ledger.emit_batch(
        run_dir,
        [
            {
                "target": f"depth-budget.{cluster_id}",
                "leverage_class": "L6",
                "form": "confirm",
                "default": "extend",
            }
        ],
    )
    append_event(
        run_dir,
        "budget_event",
        {"kind": "exhausted", "cluster_id": cluster_id, "question_id": result["ids"][0]},
    )
    return {"ok": True, "exhausted": True, "question_id": result["ids"][0], "newly_asked": True}
