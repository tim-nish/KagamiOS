from dataclasses import dataclass
from pathlib import Path

import yaml

SCHEMAS_ROOT = Path(__file__).resolve().parent.parent / "schemas"

ARTIFACT_TYPES = (
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
)

STORE_TYPES = (
    "question-ledger",
    "corpus-cache",
    "entity-registry",
    "run-manifest",
    "run-event-log",
)

STATES = ("frame", "map", "deepen", "synthesize", "locate", "propose")
DECIDE_GATE = "decide"
VALID_GENERATION_WINDOWS = frozenset(STATES) | {"entry", "any", DECIDE_GATE}

# AD-4: the named roles plus the `worker` drafting role, plus the
# Interviewer (the orchestrating skill itself, per AD-4 "the main thread
# is the Interviewer") — the full set a `--role` argument may declare,
# whether on a content write or an FR-49/AD-26 `llm_call` report.
ROLES = ("scout", "cartographer", "historian", "skeptic", "worker", "interviewer")


class RegistryError(Exception):
    pass


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str
    profile: str
    author: str
    unknown_class_hint: str | None = None
    leverage: tuple = ()
    in_summary: bool = False
    audit_exempt: str | None = None
    comparison_axis: bool = False

    @classmethod
    def from_dict(cls, name: str, raw: dict) -> "FieldSpec":
        try:
            field_type = raw["type"]
            profile = raw["profile"]
            author = raw["author"]
        except KeyError as exc:
            raise RegistryError(f"field '{name}' is missing required key {exc}") from None
        return cls(
            name=name,
            type=field_type,
            profile=profile,
            author=author,
            unknown_class_hint=raw.get("unknown_class_hint"),
            leverage=tuple(raw.get("leverage", ())),
            in_summary=bool(raw.get("in_summary", False)),
            audit_exempt=raw.get("audit_exempt"),
            comparison_axis=bool(raw.get("comparison_axis", False)),
        )


@dataclass(frozen=True)
class TypeSchema:
    type_slug: str
    schema_version: int
    fields: dict
    generation_window: str | None = None

    def field(self, name: str) -> FieldSpec:
        try:
            return self.fields[name]
        except KeyError:
            raise RegistryError(f"'{self.type_slug}' has no field '{name}'") from None


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _load_common_metadata_fields(root: Path) -> dict:
    raw = _load_yaml(root / "common_metadata.yaml")
    return {name: FieldSpec.from_dict(name, spec) for name, spec in raw["fields"].items()}


def _build_type_schema(raw: dict, extra_fields: dict) -> TypeSchema:
    fields = dict(extra_fields)
    for name, raw_field in (raw.get("fields") or {}).items():
        fields[name] = FieldSpec.from_dict(name, raw_field)
    return TypeSchema(
        type_slug=raw["type"],
        schema_version=raw["schema_version"],
        fields=fields,
        generation_window=raw.get("generation_window"),
    )


class SchemaRegistry:
    def __init__(
        self,
        artifact_schemas: dict,
        store_schemas: dict,
        state_machine: dict,
        consumption_map: dict | None = None,
        paper_card_readable_states: tuple = (),
    ):
        self._artifact_schemas = artifact_schemas
        self._store_schemas = store_schemas
        self._state_machine = state_machine
        self._consumption_map = consumption_map or {}
        self._paper_card_readable_states = tuple(paper_card_readable_states)

    def artifact_types(self) -> tuple:
        return tuple(sorted(self._artifact_schemas))

    def store_types(self) -> tuple:
        return tuple(sorted(self._store_schemas))

    def states(self) -> tuple:
        return tuple(self._state_machine["states"])

    def decide_gate(self) -> str:
        return self._state_machine["decide_gate"]

    def backward_transitions(self) -> tuple:
        return tuple(
            (t["from"], t["to"]) for t in self._state_machine.get("backward_transitions", [])
        )

    def get_artifact_schema(self, type_slug: str) -> TypeSchema:
        try:
            return self._artifact_schemas[type_slug]
        except KeyError:
            raise RegistryError(f"unknown artifact type '{type_slug}'") from None

    def get_store_schema(self, type_slug: str) -> TypeSchema:
        try:
            return self._store_schemas[type_slug]
        except KeyError:
            raise RegistryError(f"unknown infrastructure store '{type_slug}'") from None

    def generation_window(self, type_slug: str) -> str:
        return self.get_artifact_schema(type_slug).generation_window

    def audit_exempt_fields(self) -> tuple:
        result = [
            (type_slug, field_name)
            for type_slug, schema in self._artifact_schemas.items()
            for field_name, spec in schema.fields.items()
            if spec.audit_exempt == "permanent"
        ]
        return tuple(sorted(result))

    def comparison_axis_fields(self, type_slug: str) -> tuple:
        schema = self.get_artifact_schema(type_slug)
        return tuple(
            sorted(name for name, spec in schema.fields.items() if spec.comparison_axis)
        )

    def consumption_map(self, state: str) -> tuple:
        """FR-15: the artifact types a given state's brief may read, of any kind."""
        try:
            return tuple(self._consumption_map[state])
        except KeyError:
            raise RegistryError(f"no consumption map defined for state '{state}'") from None

    def can_read(self, state: str, type_slug: str) -> bool:
        return type_slug in self.consumption_map(state)

    def paper_card_readable_states(self) -> tuple:
        """FR-55: which states may read a paper card's content — audited
        *separately* from `consumption_map`'s `states:` map because a
        paper card lives in the AD-18 corpus-cache store, not the
        versioned artifact store `consumption_map`/`can_read` gate
        (`load_registry`'s own validation only recognizes artifact
        types). Story 10.2's audit: Deepen (Historian) needs it; Synthesize
        and Locate do not — `agents/worker.md`'s existing charter already
        scopes those two states to read exactly one layer up (accepted
        Cluster Dossiers / the Landscape Synthesis), never past the layer
        immediately below the state being drafted for. Extending this
        list is a data change, not a code change, if that audit's answer
        changes.
        """
        return self._paper_card_readable_states

    def can_read_paper_card(self, state: str) -> bool:
        return state in self.paper_card_readable_states()

    def validate(self, type_slug: str, artifact_fields: dict) -> None:
        schema = self.get_artifact_schema(type_slug)
        unknown = set(artifact_fields) - set(schema.fields)
        if unknown:
            raise RegistryError(
                f"field(s) {sorted(unknown)} are not defined on the '{type_slug}' schema "
                "(validated against the wrong type?)"
            )


def load_registry(schemas_root: Path | None = None) -> SchemaRegistry:
    root = schemas_root if schemas_root is not None else SCHEMAS_ROOT
    common_fields = _load_common_metadata_fields(root)

    artifact_schemas = {}
    for path in sorted((root / "artifacts").glob("*.yaml")):
        schema = _build_type_schema(_load_yaml(path), extra_fields=common_fields)
        artifact_schemas[schema.type_slug] = schema

    store_schemas = {}
    for path in sorted((root / "stores").glob("*.yaml")):
        schema = _build_type_schema(_load_yaml(path), extra_fields={})
        store_schemas[schema.type_slug] = schema

    state_machine = _load_yaml(root / "state_machine.yaml")

    missing_artifacts = set(ARTIFACT_TYPES) - set(artifact_schemas)
    if missing_artifacts:
        raise RegistryError(f"schema registry missing artifact types: {sorted(missing_artifacts)}")

    missing_stores = set(STORE_TYPES) - set(store_schemas)
    if missing_stores:
        raise RegistryError(f"schema registry missing infrastructure stores: {sorted(missing_stores)}")

    for type_slug, schema in artifact_schemas.items():
        if schema.generation_window not in VALID_GENERATION_WINDOWS:
            raise RegistryError(
                f"'{type_slug}' has invalid generation_window '{schema.generation_window}'"
            )

    consumption_map_raw = _load_yaml(root / "consumption_map.yaml")
    consumption_map = consumption_map_raw.get("states") or {}
    valid_consumers = set(state_machine["states"]) | {state_machine["decide_gate"]}
    unknown_consumers = set(consumption_map) - valid_consumers
    if unknown_consumers:
        raise RegistryError(f"consumption map has unknown consumer(s): {sorted(unknown_consumers)}")
    for consumer, readable_types in consumption_map.items():
        unknown_types = set(readable_types) - set(artifact_schemas)
        if unknown_types:
            raise RegistryError(
                f"consumption map for '{consumer}' references unknown artifact type(s): "
                f"{sorted(unknown_types)}"
            )

    # FR-55: a second, separately-audited allowlist — a paper card is a
    # corpus-cache entry, not an artifact type, so it cannot live in
    # `consumption_map`'s `states:` map above without that map's own
    # unknown-artifact-type validation rejecting it.
    paper_card_readable_states = tuple(consumption_map_raw.get("paper_card_readable_states") or [])
    unknown_paper_card_consumers = set(paper_card_readable_states) - valid_consumers
    if unknown_paper_card_consumers:
        raise RegistryError(
            f"paper_card_readable_states has unknown consumer(s): {sorted(unknown_paper_card_consumers)}"
        )

    return SchemaRegistry(
        artifact_schemas, store_schemas, state_machine, consumption_map, paper_card_readable_states
    )
