"""
Decides whether a provider's refusal is worth retrying.

A spending cap and a per-minute limit look identical in the response, and
retrying the first one is expensive.
"""

import logging
import re
import time

logger = logging.getLogger(__name__)

# Transient: the provider is asking us to slow down. Waiting helps.
RATE_LIMIT_MARKERS = (
    "rate_limit", "ratelimit", "rate limit", "429", "resource_exhausted", "quota",
)

# Permanent for this billing period: a spending cap or an exhausted monthly
# allowance stays exhausted until the period rolls over. Waiting does not help.
PERMANENT_QUOTA_MARKERS = (
    "spending cap",
    "billing account",
    "exceeded the monthly quota",
    "monthly quota for requests",
    "upgrade your plan",
    "insufficient_quota",
)


def is_permanent_quota_error(error: BaseException) -> bool:
    """True if the provider will keep refusing until the billing period rolls over."""
    text = str(error).lower()
    return any(marker in text for marker in PERMANENT_QUOTA_MARKERS)


def is_rate_limit_error(error: BaseException) -> bool:
    """
    True if this looks like transient throttling worth retrying.

    Permanent quota refusals are excluded deliberately: they match the same
    markers, so without this check they would be retried pointlessly.
    """
    if is_permanent_quota_error(error):
        return False
    text = str(error).lower()
    return any(marker in text for marker in RATE_LIMIT_MARKERS)


def kickoff_with_retry(crew, max_retries: int = 4, base_delay: float = 12.0):
    """
    Run crew.kickoff(), retrying only on transient rate limits.

    Every comparison arm calls this, so throttling is handled identically
    across them. Previously the harness called crew.kickoff() bare, and a run
    that happened to hit the per-minute ceiling was recorded as that
    architecture failing rather than as an infrastructure problem.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return crew.kickoff()
        except Exception as exc:
            last_error = exc

            if is_permanent_quota_error(exc):
                logger.error("Provider quota exhausted for this billing period: %s", exc)
                print("\n  ! The LLM provider has refused the request for the rest of "
                      "the billing period\n    (spending cap or monthly allowance). "
                      "Retrying will not help — stopping.\n")
                raise

            if not is_rate_limit_error(exc) or attempt == max_retries - 1:
                raise

            # Providers often name the wait in the message ("retry after 12s");
            # prefer that over our own backoff when present.
            hinted = re.search(r"(\d+(?:\.\d+)?)\s*s", str(exc))
            delay = max(
                float(hinted.group(1)) if hinted else base_delay * (2 ** attempt),
                5.0,
            )
            logger.warning("Rate limited, waiting %.0fs before retry %d/%d",
                           delay, attempt + 1, max_retries)
            print(f"  Rate limit hit. Waiting {delay:.0f}s before retry "
                  f"({attempt + 1}/{max_retries})...")
            time.sleep(delay)

    raise last_error  # pragma: no cover - the loop always returns or raises
