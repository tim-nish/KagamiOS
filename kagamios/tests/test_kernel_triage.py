import pytest

from kagami.kernel.triage import (
    COMPUTABLE,
    DEFERRABLE,
    HUMAN_ONLY,
    TriageError,
    triage_unknown,
)


def test_computable_hint_always_resolves_computable():
    assert triage_unknown("computable", blocking=True) == COMPUTABLE
    assert triage_unknown("computable", blocking=False) == COMPUTABLE


def test_human_only_and_blocking_becomes_a_candidate_question():
    assert triage_unknown("human-only", blocking=True) == HUMAN_ONLY


def test_human_only_but_not_blocking_is_deferred_not_asked():
    assert triage_unknown("human-only", blocking=False) == DEFERRABLE


def test_deferrable_hint_is_always_deferred():
    assert triage_unknown("deferrable", blocking=True) == DEFERRABLE
    assert triage_unknown("deferrable", blocking=False) == DEFERRABLE


def test_unrecognized_hint_raises():
    with pytest.raises(TriageError):
        triage_unknown("mystery", blocking=True)
