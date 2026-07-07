import pytest

from kagami.kernel.cartographer import (
    CartographerError,
    compute_recency_profile,
    create_field_map_clusters,
    cuts_are_structurally_different,
    draft_clusterings,
    validate_field_map_draft,
)
from kagami.store.artifact import RejectedWriteError, attempt_ai_write, read_current, scan


def _papers():
    return [
        {"id": "ppr-1", "method_class": "empirical", "source": "openalex"},
        {"id": "ppr-2", "method_class": "empirical", "source": "arxiv"},
        {"id": "ppr-3", "method_class": "theoretical", "source": "arxiv"},
    ]


def test_draft_clusterings_produces_at_least_two_structurally_different_cuts():
    result = draft_clusterings(_papers())
    assert len(result["cuts"]) >= 2
    validate_field_map_draft(result["cuts"])  # does not raise


def test_cuts_are_structurally_different_detects_a_genuine_difference():
    result = draft_clusterings(_papers())
    assert cuts_are_structurally_different(result["cuts"][0], result["cuts"][1])


def test_single_clustering_draft_fails_validation():
    result = draft_clusterings(_papers())
    with pytest.raises(CartographerError):
        validate_field_map_draft([result["cuts"][0]])


def test_two_cuts_that_partition_identically_fail_validation():
    # Same grouping under different labels is not a genuine structural
    # alternative — this is the "only one distinguishable clustering" case
    # showing up as two cuts rather than literally one.
    identical_papers = [
        {"id": "ppr-1", "method_class": "x", "source": "x"},
        {"id": "ppr-2", "method_class": "y", "source": "y"},
    ]
    result = draft_clusterings(identical_papers)
    with pytest.raises(CartographerError):
        validate_field_map_draft(result["cuts"])


def test_draft_over_extraction_backed_cards_produces_non_degenerate_method_class_clustering(tmp_path):
    """FR-54/FR-26: run 1's cards carried no `method_class` at all, so every
    card fell into the same 'unclassified' bucket and the draft degenerated
    to identical partitions. Re-run over cards minted through the FR-54
    extraction path (same chokepoint `search_corpus`/`corpus_expand` use)
    and confirm `method_class` clustering earns its two-cut name back."""
    from kagami.corpus.cache import get_or_create_paper_card

    empirical_abstract = (
        "We conduct extensive experiments on three benchmark datasets. "
        "Results show a significant accuracy improvement over strong baselines."
    )
    theoretical_abstract = (
        "We prove a tight upper bound on the sample complexity of this class of algorithms. "
        "Our theorem holds under mild assumptions."
    )

    card_a, _ = get_or_create_paper_card(
        tmp_path, "10.1/a", lambda: {"title": "Paper A", "abstract": empirical_abstract, "source": "openalex"}
    )
    card_b, _ = get_or_create_paper_card(
        tmp_path, "10.1/b", lambda: {"title": "Paper B", "abstract": theoretical_abstract, "source": "openalex"}
    )

    assert card_a["method_class"] != card_b["method_class"]

    result = draft_clusterings([card_a, card_b])
    validate_field_map_draft(result["cuts"])  # does not raise: genuinely non-degenerate


def test_compute_recency_profile_is_non_empty_and_deterministic():
    papers = [{"source": "openalex"}, {"source": "arxiv"}]
    profile = compute_recency_profile(papers)
    assert profile
    assert compute_recency_profile(papers) == profile


def test_create_field_map_clusters_instantiates_the_chosen_cut_only(tmp_path):
    papers = _papers()
    result = draft_clusterings(papers)
    papers_by_id = {p["id"]: p for p in papers}
    chosen = result["cuts"][0]

    outcome = create_field_map_clusters(tmp_path, chosen, result["cuts"], papers_by_id)
    assert outcome["ok"] is True
    assert len(outcome["field_map_ids"]) == len(chosen["clusters"])

    for art_id in outcome["field_map_ids"]:
        frontmatter, sections = read_current(tmp_path, "field-map", art_id)
        assert frontmatter["recency_profile"]
        assert frontmatter["alternative_cut"]
        cluster_name_section = next(s for s in sections if s.title == "cluster_name")
        assert cluster_name_section.body  # human-editable name, AI-seeded


def test_create_field_map_clusters_refuses_an_invalid_single_cut(tmp_path):
    papers = _papers()
    result = draft_clusterings(papers)
    papers_by_id = {p["id"]: p for p in papers}

    with pytest.raises(CartographerError):
        create_field_map_clusters(tmp_path, result["cuts"][0], [result["cuts"][0]], papers_by_id)


def test_cluster_name_is_a_constitutive_human_field_ai_write_is_refused(tmp_path):
    papers = _papers()
    result = draft_clusterings(papers)
    papers_by_id = {p["id"]: p for p in papers}
    outcome = create_field_map_clusters(tmp_path, result["cuts"][0], result["cuts"], papers_by_id)
    art_id = outcome["field_map_ids"][0]

    with pytest.raises(RejectedWriteError):
        attempt_ai_write(tmp_path, "field-map", art_id, "cluster_name", "AI renamed this")


def test_edited_cluster_name_is_never_silently_reverted_by_repair(tmp_path):
    papers = _papers()
    result = draft_clusterings(papers)
    papers_by_id = {p["id"]: p for p in papers}
    outcome = create_field_map_clusters(tmp_path, result["cuts"][0], result["cuts"], papers_by_id)
    art_id = outcome["field_map_ids"][0]

    art_dir = tmp_path / "artifacts" / "field-map" / art_id
    current_text = (art_dir / "current.md").read_text()
    original_name = next(
        s for s in read_current(tmp_path, "field-map", art_id)[1] if s.title == "cluster_name"
    ).body
    (art_dir / "current.md").write_text(current_text.replace(original_name, "researcher's chosen name"))
    scan(tmp_path, "field-map", art_id)  # AD-6: mints v2, flips cluster_name to human-confirmed

    # A later "repair" attempt (an AI write) targeting cluster_name is
    # refused outright — it's a constitutive human field, never AI-writable
    # regardless of touch state — so the human's edit is never at risk.
    with pytest.raises(RejectedWriteError):
        attempt_ai_write(tmp_path, "field-map", art_id, "cluster_name", "AI reverts this")

    _, sections = read_current(tmp_path, "field-map", art_id)
    cluster_name = next(s for s in sections if s.title == "cluster_name")
    assert cluster_name.body == "researcher's chosen name"
