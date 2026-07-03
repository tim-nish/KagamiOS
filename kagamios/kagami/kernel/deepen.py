from pathlib import Path

from kagami.store.artifact import claim_section


def claim_cluster_sections(run_dir: Path, dossier_art_id: str, section_ids: list[str], holder: str) -> dict:
    """FR-3/AD-10: one worker deepens per cluster. Since each cluster has
    its own Cluster Dossier artifact, cross-cluster collisions are
    impossible by construction (claims live in that artifact's own
    meta.yaml) — this claims a worker's own cluster's sections under its
    session lease holder, section by section, so a partial claim is
    visible rather than silently all-or-nothing.
    """
    claimed = []
    refused = []
    for section_id in section_ids:
        if claim_section(run_dir, "cluster-dossier", dossier_art_id, section_id, holder):
            claimed.append(section_id)
        else:
            refused.append(section_id)

    return {"ok": len(refused) == 0, "claimed": claimed, "refused": refused}
