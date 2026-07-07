import pytest

from kagami.registry import (
    ARTIFACT_TYPES,
    STORE_TYPES,
    RegistryError,
    load_registry,
)


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_all_eleven_artifact_types_present_with_kebab_case_slugs(registry):
    expected = {
        "intuition-note",
        "researcher-profile",
        "inquiry-frame",
        "confidence-checklist",
        "field-map",
        "cluster-dossier",
        "landscape-synthesis",
        "gap-register",
        "candidate-direction",
        "direction-decision",
        "dissolution-memo",
    }
    assert set(registry.artifact_types()) == expected
    assert set(ARTIFACT_TYPES) == expected
    for slug in registry.artifact_types():
        assert slug == slug.lower()
        assert " " not in slug and "_" not in slug


def test_every_field_on_every_type_declares_type_profile_and_author(registry):
    all_schemas = [registry.get_artifact_schema(t) for t in registry.artifact_types()]
    all_schemas += [registry.get_store_schema(s) for s in registry.store_types()]

    checked = 0
    for schema in all_schemas:
        for field_spec in schema.fields.values():
            assert field_spec.type
            assert field_spec.profile in ("minimal", "full")
            assert field_spec.author in ("ai", "human", "ai-drafted-human-confirmed")
            checked += 1
    assert checked > 0


def test_fields_with_unknown_class_hint_or_leverage_declare_them_correctly(registry):
    inquiry_frame = registry.get_artifact_schema("inquiry-frame")
    unprimed = inquiry_frame.field("unprimed_hunch")
    assert unprimed.unknown_class_hint == "human-only"

    field_map = registry.get_artifact_schema("field-map")
    scope = field_map.field("scope")
    assert scope.unknown_class_hint == "human-only"
    assert scope.leverage == ("L2", "L4")


def test_constitutive_triad_and_e6_fields_are_permanently_audit_exempt(registry):
    exempt = set(registry.audit_exempt_fields())
    expected = {
        # scope/attention allocation leg
        ("inquiry-frame", "in_scope_readings"),
        ("inquiry-frame", "exclusions"),
        ("field-map", "scope"),
        # gap-meaningfulness leg
        ("gap-register", "meaningful_to_me"),
        # direction-selection leg (v2 non-preclusion)
        ("candidate-direction", "disposition"),
        # the two E6 unprimed questions
        ("inquiry-frame", "unprimed_hunch"),
        ("direction-decision", "unprimed_lean"),
    }
    assert expected <= exempt

    for type_slug, field_name in expected:
        field_spec = registry.get_artifact_schema(type_slug).field(field_name)
        assert field_spec.author == "human"


def test_candidate_direction_comparison_table_axes_are_fully_defined(registry):
    axes = registry.comparison_axis_fields("candidate-direction")
    assert axes == ("red_team_notes", "requirements", "supporting_evidence", "why_now")

    candidate = registry.get_artifact_schema("candidate-direction")
    assert candidate.field("red_team_notes")  # FR-43: red-team notes field


def test_decide_gate_exit_criteria_fields_are_fully_defined_across_the_schema_graph(registry):
    decision = registry.get_artifact_schema("direction-decision")
    assert decision.field("confidence_checklist_audit")  # checklist trace-complete
    assert decision.field("signed_by")
    assert decision.field("signed_at")

    candidate = registry.get_artifact_schema("candidate-direction")
    assert candidate.field("disposition")  # dispositions recorded

    dossier = registry.get_artifact_schema("cluster-dossier")
    assert dossier.field("representative_papers")  # human-read completeness lives here


def test_five_infrastructure_stores_present_and_queryable_by_id(registry):
    assert set(registry.store_types()) == set(STORE_TYPES)
    assert len(registry.store_types()) == 5
    for slug in registry.store_types():
        schema = registry.get_store_schema(slug)
        assert "id" in schema.fields


def test_artifact_type_never_validates_against_another_types_schema(registry):
    gap_register_fields = {"statement": "a gap", "meaningful_to_me": "meaningful"}
    registry.validate("gap-register", gap_register_fields)

    with pytest.raises(RegistryError):
        registry.validate("candidate-direction", gap_register_fields)


def test_state_enum_and_generation_window_table_ship_complete(registry):
    assert registry.states() == ("frame", "map", "deepen", "synthesize", "locate", "propose")
    assert registry.decide_gate() == "decide"

    assert registry.generation_window("field-map") == "map"
    assert registry.generation_window("gap-register") == "locate"
    # v2 types: windows are present in the table even though MVP's flow
    # never reaches them (AD-14 non-preclusion).
    assert registry.generation_window("candidate-direction") == "propose"
    assert registry.generation_window("direction-decision") == "decide"


def test_backward_transitions_are_registered(registry):
    transitions = registry.backward_transitions()
    assert ("deepen", "frame") in transitions
    assert ("synthesize", "map") in transitions
    assert ("locate", "deepen") in transitions
    assert ("locate", "map") in transitions
    assert ("propose", "locate") in transitions
    assert ("decided", "propose") in transitions


def test_consumption_map_defines_all_states_including_decide(registry):
    for state in (*registry.states(), registry.decide_gate()):
        readable = registry.consumption_map(state)
        assert readable, f"state '{state}' has no readable types defined"


def test_can_read_reflects_the_consumption_map(registry):
    assert registry.can_read("frame", "intuition-note") is True
    assert registry.can_read("frame", "gap-register") is False
    assert registry.can_read("locate", "landscape-synthesis") is True


def test_consumption_map_rejects_unknown_consumer(tmp_path):
    schemas_root = _minimal_schemas_root(tmp_path)
    (schemas_root / "consumption_map.yaml").write_text(
        "schema_version: 1\nstates:\n  not-a-real-state: [intuition-note]\n"
    )
    with pytest.raises(RegistryError, match="unknown consumer"):
        load_registry(schemas_root)


def test_consumption_map_rejects_unknown_artifact_type(tmp_path):
    schemas_root = _minimal_schemas_root(tmp_path)
    (schemas_root / "consumption_map.yaml").write_text(
        "schema_version: 1\nstates:\n  frame: [not-a-real-type]\n"
    )
    with pytest.raises(RegistryError, match="unknown artifact type"):
        load_registry(schemas_root)


def test_can_read_paper_card_reflects_story_10_2s_audit(registry):
    """FR-55: Deepen (Historian) needs paper-card content; Synthesize and
    Locate were audited and do not — see `consumption_map.yaml`'s
    `paper_card_readable_states` comment for the reasoning."""
    assert registry.can_read_paper_card("deepen") is True
    assert registry.can_read_paper_card("synthesize") is False
    assert registry.can_read_paper_card("locate") is False
    assert registry.can_read_paper_card("frame") is False


def test_paper_card_readable_states_rejects_unknown_consumer(tmp_path):
    schemas_root = _minimal_schemas_root(tmp_path)
    (schemas_root / "consumption_map.yaml").write_text(
        "schema_version: 1\nstates:\n  frame: [intuition-note]\n"
        "paper_card_readable_states: [not-a-real-state]\n"
    )
    with pytest.raises(RegistryError, match="paper_card_readable_states has unknown consumer"):
        load_registry(schemas_root)


def _minimal_schemas_root(tmp_path):
    import shutil

    from kagami.registry import SCHEMAS_ROOT

    schemas_root = tmp_path / "schemas"
    shutil.copytree(SCHEMAS_ROOT, schemas_root)
    return schemas_root


def test_load_registry_raises_when_an_artifact_type_is_missing(tmp_path):
    schemas_root = tmp_path / "schemas"
    (schemas_root / "artifacts").mkdir(parents=True)
    (schemas_root / "stores").mkdir(parents=True)
    (schemas_root / "common_metadata.yaml").write_text("schema_version: 1\nfields: {}\n")
    (schemas_root / "state_machine.yaml").write_text(
        "schema_version: 1\nstates: [frame]\ndecide_gate: decide\n"
    )

    with pytest.raises(RegistryError, match="missing artifact types"):
        load_registry(schemas_root)


def test_field_missing_required_key_raises_registry_error(tmp_path):
    schemas_root = tmp_path / "schemas"
    (schemas_root / "artifacts").mkdir(parents=True)
    (schemas_root / "stores").mkdir(parents=True)
    (schemas_root / "common_metadata.yaml").write_text("schema_version: 1\nfields: {}\n")
    (schemas_root / "state_machine.yaml").write_text(
        "schema_version: 1\nstates: [frame]\ndecide_gate: decide\n"
    )
    (schemas_root / "artifacts" / "intuition-note.yaml").write_text(
        "type: intuition-note\nschema_version: 1\ngeneration_window: entry\n"
        "fields:\n  raw_capture:\n    type: text\n"  # missing profile/author
    )

    with pytest.raises(RegistryError, match="missing required key"):
        load_registry(schemas_root)
