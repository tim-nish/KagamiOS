import pytest

from kagami.corpus.cache import CorpusCacheError, get_or_create_paper_card, mint_paper_id


def test_mint_paper_id_is_deterministic_and_content_derived():
    assert mint_paper_id("10.1/abc") == mint_paper_id("10.1/abc")
    assert mint_paper_id("10.1/abc") != mint_paper_id("10.1/xyz")
    assert mint_paper_id("10.1/abc").startswith("ppr-")


def test_mint_paper_id_refuses_empty_canonical_key():
    with pytest.raises(CorpusCacheError):
        mint_paper_id("")


def test_get_or_create_computes_once_and_reuses_thereafter(tmp_path):
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"title": "Paper A", "source": "openalex"}

    card1, reused1 = get_or_create_paper_card(tmp_path, "10.1/abc", compute)
    assert reused1 is False
    assert calls["n"] == 1
    assert card1["schema_version"] == 1
    assert card1["bibliographic_identity"] == "10.1/abc"
    assert card1["title"] == "Paper A"

    card2, reused2 = get_or_create_paper_card(tmp_path, "10.1/abc", compute)
    assert reused2 is True
    assert calls["n"] == 1  # compute() was not called again
    assert card2["id"] == card1["id"]


def test_different_papers_get_different_cache_entries(tmp_path):
    card_a, _ = get_or_create_paper_card(tmp_path, "10.1/a", lambda: {"title": "A"})
    card_b, _ = get_or_create_paper_card(tmp_path, "10.1/b", lambda: {"title": "B"})
    assert card_a["id"] != card_b["id"]


def test_cache_survives_across_separate_calls_reading_the_same_output_root(tmp_path):
    get_or_create_paper_card(tmp_path, "10.1/abc", lambda: {"title": "Paper A"})
    assert (tmp_path / "corpus" / f"{mint_paper_id('10.1/abc')}.yaml").is_file()

    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"title": "should not run"}

    card, reused = get_or_create_paper_card(tmp_path, "10.1/abc", compute)
    assert reused is True
    assert calls["n"] == 0
    assert card["title"] == "Paper A"


@pytest.mark.parametrize("field", ["relevance", "priority", "judgment", "meaningful_to_me"])
def test_get_or_create_refuses_a_frame_dependent_field_on_the_raw_input(tmp_path, field):
    """FR-52/AD-28: a paper card is a frame-independent fact — a
    frame-dependent valuation may never land on it, even if a caller's
    compute() result happens to carry one."""
    with pytest.raises(CorpusCacheError):
        get_or_create_paper_card(tmp_path, "10.1/abc", lambda: {"title": "A", field: "x"})

    assert not (tmp_path / "corpus" / f"{mint_paper_id('10.1/abc')}.yaml").is_file()


def test_get_or_create_with_no_frame_dependent_fields_still_succeeds(tmp_path):
    card, reused = get_or_create_paper_card(tmp_path, "10.1/xyz", lambda: {"title": "Clean"})
    assert reused is False
    assert card["title"] == "Clean"
