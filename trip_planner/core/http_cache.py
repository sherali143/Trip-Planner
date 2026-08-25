"""
Records every API reply to disk, and replays it afterwards.

This is what lets the whole evaluation run with no API keys. It also enforces
a hard ceiling on live calls, so one careless run cannot spend a month's
allowance. Request headers are never written, so no key reaches disk.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

MODE_RECORD = "record"
MODE_REPLAY = "replay"
MODE_LIVE = "live"
_VALID_MODES = (MODE_RECORD, MODE_REPLAY, MODE_LIVE)

# Anchored to the project root, not to the working directory.
#
# This was ".api_cache", a relative path, so the directory it meant depended on
# where python was started. Running a demo from inside trip_planner/demos/ created
# trip_planner/demos/.api_cache and used it — a replay that found nothing and looked broken,
# or a recording that spent real quota into a directory nothing else reads. The
# empty trip_planner/demos/.api_cache left behind is what led to this being found.
#
# real_prices.py already resolved the same directory from __file__; now both
# agree, and they must, because one reads the recordings the other writes.
DEFAULT_CACHE_DIR = str(
    Path(__file__).resolve().parent.parent.parent / ".api_cache")


class CacheMiss(RuntimeError):
    """Raised when running in replay mode and no recording exists for a request."""


class QuotaGuardTripped(RuntimeError):
    """Raised when a run has spent its allowed number of live API calls."""


def get_live_call_budget() -> Optional[int]:
    """
    Hard ceiling on live API calls for this process, or None for unlimited.

    The paid-for-by-the-month free tiers are tiny (fly-scraper 30/month,
    booking-com15 50/month) and a single accidental full run can consume a
    whole month's allowance in minutes — with no way to buy it back. Set
    TRIP_PLANNER_MAX_LIVE_CALLS to fail loudly instead.
    """
    raw = os.getenv("TRIP_PLANNER_MAX_LIVE_CALLS", "").strip()
    if not raw:
        return None
    try:
        return max(0, int(raw))
    except ValueError:
        logger.warning("Ignoring non-numeric TRIP_PLANNER_MAX_LIVE_CALLS=%r", raw)
        return None


def get_mode() -> str:
    """Current record/replay mode, read fresh so tests can flip it at runtime."""
    mode = os.getenv("TRIP_PLANNER_API_MODE", MODE_RECORD).strip().lower()
    if mode not in _VALID_MODES:
        logger.warning("Unknown TRIP_PLANNER_API_MODE=%r, falling back to %r", mode, MODE_RECORD)
        return MODE_RECORD
    return mode


def _cache_dir() -> Path:
    path = Path(os.getenv("TRIP_PLANNER_CACHE_DIR", DEFAULT_CACHE_DIR))
    path.mkdir(parents=True, exist_ok=True)
    return path


class CachedResponse:
    """
    Minimal stand-in for requests.Response covering the surface this codebase
    uses: .status_code, .text, .json(), .raise_for_status().
    """

    def __init__(self, status_code: int, text: str, url: str = "", from_cache: bool = True):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.from_cache = from_cache

    def json(self) -> Any:
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            raise requests.HTTPError(
                f"{self.status_code} Error (replayed from cache) for url: {self.url}",
                response=None,
            )

    def __repr__(self) -> str:
        return f"<CachedResponse [{self.status_code}] cached={self.from_cache}>"


class _Stats:
    """Per-process counters, reported alongside evaluation results."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.live_calls = 0
        self.live_errors = 0
        self.stored = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "live_calls": self.live_calls,
            "live_errors": self.live_errors,
            "responses_stored": self.stored,
        }


STATS = _Stats()


def _make_key(method: str, url: str, params: Optional[dict], body: Optional[Any]) -> str:
    """
    Build a stable cache key. Headers are deliberately excluded: they carry API
    keys, and they never change the response for these endpoints.
    """
    if isinstance(body, (bytes, bytearray)):
        body_repr = body.decode("utf-8", errors="replace")
    elif body is None:
        body_repr = ""
    elif isinstance(body, str):
        body_repr = body
    else:
        body_repr = json.dumps(body, sort_keys=True, default=str)

    payload = json.dumps(
        {
            "method": method.upper(),
            "url": url,
            "params": params or {},
            "body": body_repr,
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    # Prefix with the host so the cache directory stays human-auditable.
    host = url.split("//")[-1].split("/")[0].replace(":", "_")
    return f"{host}__{digest}"


def _read(key: str) -> Optional[CachedResponse]:
    cache_file = _cache_dir() / f"{key}.json"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as fh:
            entry = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupt cache entry %s: %s", key, exc)
        return None
    return CachedResponse(
        status_code=entry.get("status_code", 200),
        text=entry.get("body", ""),
        url=entry.get("url", ""),
        from_cache=True,
    )


def _write(key: str, method: str, url: str, params: Optional[dict], response: Any) -> None:
    """Persist a successful response. Headers are never stored."""
    entry = {
        "recorded_at": time.time(),
        "recorded_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "method": method.upper(),
        "url": url,
        "params": params or {},
        "status_code": response.status_code,
        "body": response.text,
    }
    cache_file = _cache_dir() / f"{key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as fh:
            json.dump(entry, fh, indent=2)
        STATS.stored += 1
    except OSError as exc:
        logger.warning("Could not write cache entry %s: %s", key, exc)


def _request(
    method: str,
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    data: Optional[Any] = None,
    json_body: Optional[Any] = None,
    timeout: int = 30,
):
    mode = get_mode()
    body = data if data is not None else json_body
    key = _make_key(method, url, params, body)

    # Cache-first for every mode except an explicit live refresh.
    if mode != MODE_LIVE:
        cached = _read(key)
        if cached is not None:
            STATS.hits += 1
            logger.debug("[http_cache] HIT %s", key)
            return cached
        STATS.misses += 1
        if mode == MODE_REPLAY:
            raise CacheMiss(
                f"No recorded response for {method.upper()} {url} "
                f"(params={params}). Run once with TRIP_PLANNER_API_MODE=record "
                f"to populate the cache."
            )

    budget = get_live_call_budget()
    if budget is not None and STATS.live_calls >= budget:
        raise QuotaGuardTripped(
            f"Live API call budget exhausted ({budget} calls used this run). "
            f"Refusing to call {url}. Raise TRIP_PLANNER_MAX_LIVE_CALLS to allow "
            f"more, or run with TRIP_PLANNER_API_MODE=replay to use only "
            f"recorded responses."
        )

    logger.debug("[http_cache] LIVE %s", url)
    STATS.live_calls += 1
    response = requests.request(
        method.upper(),
        url,
        headers=headers,
        params=params,
        data=data,
        json=json_body,
        timeout=timeout,
    )

    # Only cache successes: never bake in a quota-exhaustion 429 or a flaky 5xx.
    if 200 <= response.status_code < 300:
        _write(key, method, url, params, response)
    else:
        STATS.live_errors += 1
        logger.warning("[http_cache] not caching %s response from %s", response.status_code, url)

    return response


def cached_get(url: str, headers: Optional[dict] = None, params: Optional[dict] = None, timeout: int = 30):
    """Drop-in replacement for requests.get with record/replay caching."""
    return _request("GET", url, headers=headers, params=params, timeout=timeout)


def cached_post(
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    data: Optional[Any] = None,
    json: Optional[Any] = None,
    timeout: int = 30,
):
    """Drop-in replacement for requests.post with record/replay caching."""
    return _request("POST", url, headers=headers, params=params, data=data, json_body=json, timeout=timeout)


def cache_summary() -> Dict[str, Any]:
    """Snapshot for inclusion in evaluation result files."""
    entries = list(_cache_dir().glob("*.json"))
    budget = get_live_call_budget()
    return {
        "mode": get_mode(),
        "cache_dir": str(_cache_dir()),
        "recorded_entries": len(entries),
        "live_call_budget": budget,
        "live_calls_remaining": (None if budget is None else max(0, budget - STATS.live_calls)),
        **STATS.as_dict(),
    }
