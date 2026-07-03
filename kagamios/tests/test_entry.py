import pytest

from kagami.kernel.entry import ENTRY_MODES, EntryError, start_run_from_entry
from kagami.kernel.state_machine import get_state_cache
from kagami.store.artifact import read_current
from kagami.store.run import open_run


def _open(tmp_path, run_id="run-entry"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id


@pytest.mark.parametrize("entry_mode", ENTRY_MODES)
def test_every_entry_mode_backfills_a_non_empty_intuition_note_and_roots_at_frame(tmp_path, entry_mode):
    run_dir = _open(tmp_path, run_id=f"run-{entry_mode}")
    result = start_run_from_entry(run_dir, entry_mode, "a paper mentioned signature methods")
    assert result["ok"] is True

    frontmatter, sections = read_current(run_dir, "intuition-note", result["intuition_note_id"])
    assert frontmatter["entry_mode"] == entry_mode
    raw_capture = next(s for s in sections if s.title == "raw_capture")
    assert raw_capture.body

    assert get_state_cache(run_dir)["current_state"] == "frame"


def test_unrecognized_entry_mode_is_refused(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(EntryError):
        start_run_from_entry(run_dir, "not-a-real-mode", "some capture")


def test_empty_raw_capture_is_refused(tmp_path):
    run_dir = _open(tmp_path)
    with pytest.raises(EntryError):
        start_run_from_entry(run_dir, "intuition-first", "   ")
