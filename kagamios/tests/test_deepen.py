from kagami.kernel.deepen import claim_cluster_sections
from kagami.store.artifact import create_artifact


def _base_fields(**overrides):
    fields = {
        "depends_on": [],
        "elicited_from": [],
        "decided_by": "ai-drafted/human-reviewed",
        "summary": "",
    }
    fields.update(overrides)
    return fields


def _dossier_with_sections(run_dir, sections):
    return create_artifact(run_dir, "cluster-dossier", _base_fields(), sections=sections)


def _section_ids(run_dir, art_id):
    import yaml

    meta = yaml.safe_load((run_dir / "artifacts" / "cluster-dossier" / art_id / "meta.yaml").read_text())
    return {sm["title"]: sm["id"] for sm in meta["sections"]}


def test_worker_claims_all_of_its_own_clusters_sections(tmp_path):
    dossier = _dossier_with_sections(tmp_path, {"evolution": "x", "frontier": "y"})
    section_ids = list(_section_ids(tmp_path, dossier["id"]).values())

    result = claim_cluster_sections(tmp_path, dossier["id"], section_ids, "worker-1")
    assert result["ok"] is True
    assert set(result["claimed"]) == set(section_ids)
    assert result["refused"] == []


def test_second_worker_is_refused_a_section_already_claimed_by_a_live_worker(tmp_path):
    dossier = _dossier_with_sections(tmp_path, {"evolution": "x"})
    section_ids = list(_section_ids(tmp_path, dossier["id"]).values())

    claim_cluster_sections(tmp_path, dossier["id"], section_ids, "worker-1")
    result = claim_cluster_sections(tmp_path, dossier["id"], section_ids, "worker-2")

    assert result["ok"] is False
    assert result["refused"] == section_ids
    assert result["claimed"] == []


def test_two_workers_on_different_clusters_never_collide(tmp_path):
    dossier_a = _dossier_with_sections(tmp_path, {"evolution": "a"})
    dossier_b = _dossier_with_sections(tmp_path, {"evolution": "b"})
    sections_a = list(_section_ids(tmp_path, dossier_a["id"]).values())
    sections_b = list(_section_ids(tmp_path, dossier_b["id"]).values())

    result_a = claim_cluster_sections(tmp_path, dossier_a["id"], sections_a, "worker-1")
    result_b = claim_cluster_sections(tmp_path, dossier_b["id"], sections_b, "worker-2")

    assert result_a["ok"] is True
    assert result_b["ok"] is True
