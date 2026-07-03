import os
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
