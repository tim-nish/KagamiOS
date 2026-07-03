import json

import pytest

from kagami.corpus.provider import LiteratureProvider
from kagami.kernel.scout import CorpusAccessError, search_corpus
from kagami.store.run import open_run


class _StubProvider(LiteratureProvider):
    name = "stub"

    def __init__(self, results):
        self._results = results

    def search(self, query, limit=20):
        return self._results

    def paper_metadata(self, canonical_key):
        raise NotImplementedError

    def citation_graph(self, canonical_key):
        raise NotImplementedError


def _open(tmp_path, run_id="run-scout"):
    open_run(run_id=run_id, output_root=tmp_path / "_out")
    return tmp_path / "_out" / "runs" / run_id, tmp_path / "_out"


def _events(run_dir):
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_scout_role_search_succeeds_and_logs_a_retrieval_event(tmp_path):
    run_dir, output_root = _open(tmp_path)
    provider = _StubProvider([{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}])

    result = search_corpus(run_dir, output_root, provider, "signature methods", role="scout")
    assert result["ok"] is True
    assert len(result["papers"]) == 1
    assert result["papers"][0]["bibliographic_identity"] == "10.1/a"

    retrievals = [e for e in _events(run_dir) if e["family"] == "retrieval" and e["kind"] == "corpus_search"]
    assert len(retrievals) == 1
    assert retrievals[0]["role"] == "scout"
    assert retrievals[0]["provider"] == "stub"


def test_non_scout_role_is_refused_and_logs_nothing(tmp_path):
    run_dir, output_root = _open(tmp_path)
    provider = _StubProvider([{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}])

    with pytest.raises(CorpusAccessError):
        search_corpus(run_dir, output_root, provider, "signature methods", role="cartographer")

    events = _events(run_dir)
    assert not any(e["family"] == "retrieval" for e in events)


def test_second_search_reuses_the_cached_paper_card_across_runs(tmp_path):
    run_dir_1, output_root = _open(tmp_path, run_id="run-1")
    provider = _StubProvider([{"canonical_key": "10.1/a", "title": "Paper A", "source": "stub"}])
    search_corpus(run_dir_1, output_root, provider, "q", role="scout")

    open_run(run_id="run-2", output_root=output_root)
    run_dir_2 = output_root / "runs" / "run-2"
    result = search_corpus(run_dir_2, output_root, provider, "q", role="scout")

    assert result["papers"][0]["reused"] is True
