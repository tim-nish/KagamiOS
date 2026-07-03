import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path

from kagami.timeutil import utc_now_iso


@contextmanager
def acquire_run_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def write_lease(lease_path: Path, holder_id: str | None = None) -> dict:
    holder_id = holder_id or str(uuid.uuid4())
    now = utc_now_iso()
    lease = {"holder": holder_id, "opened_at": now, "heartbeat": now}
    lease_path.write_text(json.dumps(lease) + "\n")
    return lease
