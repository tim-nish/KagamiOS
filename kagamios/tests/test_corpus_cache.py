import json

import pytest

from kagami.corpus.cache import CorpusCacheError, get_or_create_paper_card, mint_paper_id, read_paper_card
from kagami.corpus.extraction import CONTENT_SOURCE_ABSTRACT, CONTENT_SOURCE_NONE
from kagami.store.read import ConsumptionError
from kagami.store.run import open_run


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


def test_no_abstract_yields_empty_content_fields_and_a_none_content_source(tmp_path):
    """FR-54: providers without abstract data (arXiv, GitHub, as of this
    writing) must never fabricate or approximate content — an exposed
    provider bias instead."""
    card, _ = get_or_create_paper_card(tmp_path, "10.1/abc", lambda: {"title": "A", "source": "arxiv"})
    assert card["contribution_line"] == ""
    assert card["method_class"] == ""
    assert card["evidence_type"] == ""
    assert card["key_claims"] == []
    assert card["content_source"] == CONTENT_SOURCE_NONE


def test_an_abstract_triggers_extraction_and_populates_content_fields(tmp_path):
    """FR-54: on a cache miss, a provider result carrying a title and
    abstract runs the mint-time extractor and lands its output on the
    card, fixture-tested here with a recorded (fake) abstract."""
    seen = []

    def fake_extract(title, abstract):
        seen.append((title, abstract))
        return {
            "contribution_line": "line",
            "method_class": "empirical",
            "evidence_type": "quantitative",
            "key_claims": ["claim"],
        }

    card, reused = get_or_create_paper_card(
        tmp_path,
        "10.1/abc",
        lambda: {"title": "A", "abstract": "some recorded abstract text", "source": "openalex"},
        extract=fake_extract,
    )

    assert reused is False
    assert seen == [("A", "some recorded abstract text")]
    assert card["contribution_line"] == "line"
    assert card["method_class"] == "empirical"
    assert card["evidence_type"] == "quantitative"
    assert card["key_claims"] == ["claim"]
    assert card["content_source"] == CONTENT_SOURCE_ABSTRACT


def test_extraction_runs_once_ever_never_re_triggered_on_a_cache_hit(tmp_path):
    """FR-54/AD-18: extraction runs once, ever, at mint time — a second
    request for the same canonical_key must return the cached card
    unchanged, without calling `extract` again."""
    calls = {"n": 0}

    def fake_extract(title, abstract):
        calls["n"] += 1
        return {"contribution_line": "x", "method_class": "empirical", "evidence_type": "qualitative", "key_claims": []}

    compute = lambda: {"title": "A", "abstract": "recorded abstract"}

    card1, reused1 = get_or_create_paper_card(tmp_path, "10.1/abc", compute, extract=fake_extract)
    assert reused1 is False
    assert calls["n"] == 1

    card2, reused2 = get_or_create_paper_card(tmp_path, "10.1/abc", compute, extract=fake_extract)
    assert reused2 is True
    assert calls["n"] == 1
    assert card2 == card1


@pytest.mark.parametrize("field", ["relevance", "priority", "judgment", "meaningful_to_me"])
def test_forbidden_card_fields_are_still_refused_alongside_an_abstract(tmp_path, field):
    """FR-52/AD-28: extraction adds content fields, never a judgment field
    — the FORBIDDEN_CARD_FIELDS chokepoint invariant is unchanged by this
    extension, even when the raw input also carries an abstract."""
    with pytest.raises(CorpusCacheError):
        get_or_create_paper_card(
            tmp_path, "10.1/abc", lambda: {"title": "A", "abstract": "some abstract", field: "x"}
        )


def _open(tmp_path, run_id="run-read-card"):
    output_root = tmp_path / "_out"
    open_run(run_id=run_id, output_root=output_root)
    return output_root / "runs" / run_id, output_root


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_read_paper_card_succeeds_from_an_allowed_state_and_logs_a_retrieval_event(tmp_path):
    """FR-55: Deepen (Historian) has a legitimate, logged way to read a
    paper card's content — the same pattern `read_artifact`'s
    `summary_read`/`full_text_pull` already established."""
    run_dir, output_root = _open(tmp_path)
    minted, _ = get_or_create_paper_card(output_root, "10.1/abc", lambda: {"title": "A", "source": "openalex"})

    result = read_paper_card(run_dir, output_root, "deepen", minted["id"])

    assert result["ok"] is True
    assert result["card"]["id"] == minted["id"]

    retrievals = [e for e in _events(run_dir) if e["family"] == "retrieval" and e["kind"] == "paper_card_read"]
    assert len(retrievals) == 1
    assert retrievals[0]["state"] == "deepen"
    assert retrievals[0]["paper_id"] == minted["id"]


def test_read_paper_card_is_refused_from_a_state_without_a_defined_brief(tmp_path):
    """FR-55/Story 10.2's audit: Synthesize and Locate do not read
    paper-card content directly — extending consumption_map.yaml is a
    data change, not a code change, if that audit's answer changes."""
    run_dir, output_root = _open(tmp_path)
    minted, _ = get_or_create_paper_card(output_root, "10.1/abc", lambda: {"title": "A"})

    with pytest.raises(ConsumptionError):
        read_paper_card(run_dir, output_root, "synthesize", minted["id"])

    assert not any(e["family"] == "retrieval" for e in _events(run_dir))


def test_read_paper_card_refuses_an_unknown_paper_id(tmp_path):
    run_dir, output_root = _open(tmp_path)
    with pytest.raises(CorpusCacheError):
        read_paper_card(run_dir, output_root, "deepen", "ppr-does-not-exist")
