import os
from pathlib import Path

OUTPUT_ROOT_ENV_VAR = "KAGAMI_OUTPUT_ROOT"
DEFAULT_OUTPUT_ROOT_DIRNAME = "_kagami-output"


def resolve_output_root(cwd: Path | None = None) -> Path:
    cwd = cwd if cwd is not None else Path.cwd()
    override = os.environ.get(OUTPUT_ROOT_ENV_VAR)
    if override:
        override_path = Path(override)
        return override_path if override_path.is_absolute() else cwd / override_path
    return cwd / DEFAULT_OUTPUT_ROOT_DIRNAME
