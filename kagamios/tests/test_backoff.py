import urllib.error

import pytest

from kagami.corpus.adapters import ArxivProvider
from kagami.corpus.backoff import ProviderRateLimitError, with_backoff
from kagami.corpus.provider import ProviderError


def _http_error(code):
    return urllib.error.HTTPError(url="http://x", code=code, msg="rate limited", hdrs=None, fp=None)


def test_a_successful_call_needs_no_retry_and_no_sleep():
    sleeps = []
    result = with_backoff(lambda: {"ok": True}, "test-provider", sleep_fn=sleeps.append)
    assert result == {"ok": True}
    assert sleeps == []


def test_a_429_is_retried_and_succeeds_on_a_later_attempt():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _http_error(429)
        return {"ok": True}

    sleeps = []
    result = with_backoff(flaky, "test-provider", max_retries=3, sleep_fn=sleeps.append)
    assert result == {"ok": True}
    assert attempts["n"] == 3
    # Two retries happened, so two backoff sleeps, exponential.
    assert sleeps == [1.0, 2.0]


def test_a_github_style_403_rate_limit_is_also_retried():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise _http_error(403)
        return {"ok": True}

    result = with_backoff(flaky, "github", max_retries=2, sleep_fn=lambda s: None)
    assert result == {"ok": True}


def test_a_non_rate_limit_http_error_is_never_retried():
    attempts = {"n": 0}

    def always_404():
        attempts["n"] += 1
        raise _http_error(404)

    with pytest.raises(ProviderError):
        with_backoff(always_404, "test-provider", max_retries=3, sleep_fn=lambda s: None)
    assert attempts["n"] == 1  # no retry attempted


def test_exhausted_retries_raise_a_specific_named_error_not_a_bare_exception():
    def always_429():
        raise _http_error(429)

    sleeps = []
    with pytest.raises(ProviderRateLimitError) as exc_info:
        with_backoff(always_429, "test-provider", max_retries=2, sleep_fn=sleeps.append)

    # Bounded: exactly max_retries+1 attempts were made, then it gave up —
    # never an unbounded loop.
    assert len(sleeps) == 2
    assert "test-provider" in str(exc_info.value)
    assert "rate-limited" in str(exc_info.value)


def test_retries_are_always_bounded_never_unbounded():
    attempts = {"n": 0}

    def always_429():
        attempts["n"] += 1
        raise _http_error(429)

    with pytest.raises(ProviderRateLimitError):
        with_backoff(always_429, "test-provider", max_retries=5, sleep_fn=lambda s: None)
    assert attempts["n"] == 6  # max_retries + 1, never more


def test_an_adapter_retries_a_transient_429_through_the_real_search_path():
    attempts = {"n": 0}

    def flaky_fetch(url):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise _http_error(429)
        return {"entries": [{"arxiv_id": "2101.00001", "title": "Paper C"}]}

    provider = ArxivProvider(fetch=flaky_fetch, sleep_fn=lambda s: None)
    results = provider.search("signature methods")
    assert results[0]["canonical_key"] == "2101.00001"
    assert attempts["n"] == 2


def test_an_adapter_surfaces_a_named_error_when_backoff_is_exhausted():
    def always_429(url):
        raise _http_error(429)

    provider = ArxivProvider(fetch=always_429, max_retries=1, sleep_fn=lambda s: None)
    with pytest.raises(ProviderRateLimitError):
        provider.search("signature methods")
