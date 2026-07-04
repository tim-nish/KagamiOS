from pathlib import Path

import yaml


def load_config(project_root: Path) -> dict:
    """Researcher-owned settings (AD-12): default provider, output root,
    sharing flag. Never credentials — those come from environment variables
    only (AD-7), since this file lives in the user's project and may be
    committed."""
    config_path = project_root / "config.yaml"
    if not config_path.is_file():
        return {}
    return yaml.safe_load(config_path.read_text()) or {}
