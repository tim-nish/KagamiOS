from pathlib import Path

import yaml

from kagami.registry import load_registry
from kagami.store.markdown_doc import parse_document


def validate_minimal_profile(run_dir: Path, registry=None) -> dict:
    """FR-16: a run can be validated end-to-end on minimal-profile fields alone.

    Every accepted artifact must have every `profile: minimal` field on its
    type populated; `profile: full` fields may be legitimately empty and are
    never checked.
    """
    registry = registry or load_registry()
    artifacts_root = run_dir / "artifacts"
    violations = []

    if artifacts_root.exists():
        for meta_path in sorted(artifacts_root.glob("*/*/meta.yaml")):
            meta = yaml.safe_load(meta_path.read_text())
            if meta.get("status") != "accepted":
                continue

            type_slug = meta["type"]
            schema = registry.get_artifact_schema(type_slug)
            frontmatter, sections = parse_document((meta_path.parent / "current.md").read_text())
            section_bodies = {s.title: s.body for s in sections}

            for field_name, field_spec in schema.fields.items():
                if field_spec.profile != "minimal":
                    continue
                value = frontmatter.get(field_name, section_bodies.get(field_name))
                # Matches artifact.missing_required_metadata_fields's convention: an
                # empty list is a legitimate "no dependencies"/"nothing pinned" state,
                # not a missing value — only None/"" count as unset.
                if value in (None, ""):
                    violations.append(
                        {"artifact_id": meta["id"], "type": type_slug, "field": field_name}
                    )

    return {"ok": len(violations) == 0, "violations": violations}
