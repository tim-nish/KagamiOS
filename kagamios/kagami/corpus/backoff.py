import time
import urllib.error
from typing import Callable

from kagami.corpus.provider import ProviderError

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY_SECONDS = 1.0

# 429 is the standard rate-limit status; GitHub also signals exhausted
# quota via 403 (its search API doesn't always use 429) — both are
# retryable, everything else is a real request error, not a rate limit.
RETRYABLE_HTTP_CODES = (429, 403)


class ProviderRateLimitError(ProviderError):
    """NFR7: raised only after backoff is exhausted against a sustained
    rate-limit condition — a specific, named error, never a bare
    exception, a silent hang, or an unbounded retry loop."""


def with_backoff(
    fetch_call: Callable[[], dict],
    provider_name: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    """NFR7: literature-provider adapters back off and retry against a
    documented rate limit rather than surfacing the raw HTTP error as a
    run-ending crash. Bounded — `max_retries` is always finite — and each
    retry backs off exponentially (`base_delay_seconds * 2**attempt`) so a
    sustained limit doesn't hammer the provider. A non-rate-limit HTTP
    error (a real 404, a malformed request) is never retried — only
    `RETRYABLE_HTTP_CODES` triggers backoff at all.
    """
    last_exc: urllib.error.HTTPError | None = None
    for attempt in range(max_retries + 1):
        try:
            return fetch_call()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_CODES:
                raise ProviderError(f"{provider_name} request failed: HTTP {exc.code}") from exc
            last_exc = exc
            if attempt < max_retries:
                sleep_fn(base_delay_seconds * (2**attempt))

    raise ProviderRateLimitError(
        f"{provider_name} rate-limited this request {max_retries + 1} times in a row "
        f"(last: HTTP {last_exc.code if last_exc else '?'}); giving up rather than "
        "retrying unboundedly (NFR7)"
    )
