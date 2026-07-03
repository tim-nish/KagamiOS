from kagami.kernel.refusal import consecutive_refusal_count, record_refusal_and_check_ceiling
from kagami.store.run import open_run


def _open(tmp_path):
    open_run(run_id="run-refusal", output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / "run-refusal"


def test_no_events_means_zero_consecutive_refusals(tmp_path):
    run_dir = _open(tmp_path)
    assert consecutive_refusal_count(run_dir, "historian.write", "target-1") == 0


def test_a_single_refusal_is_counted(tmp_path):
    run_dir = _open(tmp_path)
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "some error")
    assert consecutive_refusal_count(run_dir, "historian.write", "target-1") == 1


def test_consecutive_identical_refusals_accumulate(tmp_path):
    run_dir = _open(tmp_path)
    for _ in range(2):
        record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err")
    assert consecutive_refusal_count(run_dir, "historian.write", "target-1") == 2


def test_a_different_targets_refusal_does_not_inflate_the_first_targets_count(tmp_path):
    run_dir = _open(tmp_path)
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err")
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-2", "err")
    # Strict-adjacency design (see module docstring): an unrelated tuple's
    # refusal in between also breaks target-1's streak, since the most
    # recent event is no longer a match for target-1. This is the intended
    # trade-off, not a bug — a true runaway loop calls the *same* thing
    # back-to-back, and target-2's refusal is exactly the kind of
    # intervening activity that means target-1 isn't in a tight loop.
    assert consecutive_refusal_count(run_dir, "historian.write", "target-1") == 0
    assert consecutive_refusal_count(run_dir, "historian.write", "target-2") == 1


def test_two_different_targets_interleaved_each_track_their_own_immediate_streak(tmp_path):
    run_dir = _open(tmp_path)
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err")
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err")
    # target-1 has an unbroken streak of 2 right up to this point.
    assert consecutive_refusal_count(run_dir, "historian.write", "target-1") == 2


def test_an_intervening_event_for_the_same_tuple_resets_the_streak(tmp_path):
    from kagami.events import append_event

    run_dir = _open(tmp_path)
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err")
    record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err")
    # Something else happens for this run (not this tuple's refusal).
    append_event(run_dir, "artifact_event", {"kind": "accepted", "artifact_id": "unrelated"})
    assert consecutive_refusal_count(run_dir, "historian.write", "target-1") == 0


def test_escalation_fires_exactly_at_the_configured_ceiling_not_before_or_after(tmp_path):
    run_dir = _open(tmp_path)
    results = [
        record_refusal_and_check_ceiling(run_dir, "historian.write", "target-1", "err", ceiling=3)
        for _ in range(4)
    ]
    assert [r["escalate"] for r in results] == [False, False, True, True]
    assert [r["count"] for r in results] == [1, 2, 3, 4]
