from kagami.store.markdown_doc import Section, parse_document, render_document


def test_render_then_parse_round_trips_frontmatter_and_sections():
    frontmatter = {"id": "art-1", "type": "gap-register", "version": 1}
    sections = [
        Section("sec-a", "statement", "There is a gap here."),
        Section("sec-b", "evidence_of_absence", "Nobody has searched for X."),
    ]

    text = render_document(frontmatter, sections)
    parsed_fm, parsed_sections = parse_document(text)

    assert parsed_fm == frontmatter
    assert [s.id for s in parsed_sections] == ["sec-a", "sec-b"]
    assert [s.title for s in parsed_sections] == ["statement", "evidence_of_absence"]
    assert parsed_sections[0].body == "There is a gap here."
    assert parsed_sections[1].body == "Nobody has searched for X."


def test_parse_document_rejects_missing_frontmatter():
    import pytest

    with pytest.raises(ValueError):
        parse_document("no frontmatter here")


def test_multiline_section_bodies_round_trip():
    frontmatter = {"id": "art-2"}
    sections = [Section("sec-a", "evolution", "line one\nline two\n\nline four")]

    text = render_document(frontmatter, sections)
    _, parsed_sections = parse_document(text)

    assert parsed_sections[0].body == "line one\nline two\n\nline four"
