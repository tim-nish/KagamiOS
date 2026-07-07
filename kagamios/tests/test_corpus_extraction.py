from kagami.corpus.extraction import extract_card_content


def test_extract_card_content_classifies_an_empirical_abstract():
    abstract = (
        "We conduct extensive experiments on three benchmark datasets. "
        "Results show a significant accuracy improvement over strong baselines."
    )
    result = extract_card_content("An Empirical Study", abstract)
    assert result["method_class"] == "empirical"
    assert result["evidence_type"] == "quantitative"
    assert result["contribution_line"] == "We conduct extensive experiments on three benchmark datasets."
    assert result["key_claims"]


def test_extract_card_content_classifies_a_theoretical_abstract():
    abstract = (
        "We prove a tight upper bound on the sample complexity of this class of algorithms. "
        "Our theorem holds under mild assumptions."
    )
    result = extract_card_content("A Theoretical Analysis", abstract)
    assert result["method_class"] == "theoretical"


def test_extract_card_content_falls_back_to_unspecified_without_marker_keywords():
    result = extract_card_content("T", "A short note about a topic with no clear signal words.")
    assert result["method_class"] == "unspecified"
    assert result["evidence_type"] == "qualitative"


def test_extract_card_content_is_deterministic():
    abstract = "We propose a new framework and argue for its generality."
    assert extract_card_content("T", abstract) == extract_card_content("T", abstract)


def test_extract_card_content_key_claims_falls_back_to_first_sentence_with_no_claim_markers():
    result = extract_card_content("T", "Nothing notable happens here. A second sentence follows.")
    assert result["key_claims"] == ["Nothing notable happens here."]


def test_extract_card_content_on_empty_abstract_returns_empty_fields():
    result = extract_card_content("T", "")
    assert result == {
        "contribution_line": "",
        "method_class": "unspecified",
        "evidence_type": "qualitative",
        "key_claims": [],
    }
