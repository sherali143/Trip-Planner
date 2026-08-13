"""
Real LLM call instrumentation.

Why this exists
---------------
The comparison harness previously derived its headline metric from hardcoded
constants (`llm_calls += 4`, and in run_6agent.py literally
`llm_calls += 8  # simulated`). That counts *tasks*, not LLM requests: a CrewAI
ReAct agent with max_iter=8 can issue eight requests for a single task, which is
precisely the cost the 6-agent architecture is being criticised for. Reporting
an assumed number as a measurement would not survive scrutiny.

CrewAI routes every completion through LiteLLM, so registering LiteLLM
success/failure callbacks captures every real request — including the ones made
inside ReAct loops and internal retries — together with token counts, cost and
wall-clock latency.

Usage
-----
    from src.core.llm_metrics import recorder

    with recorder.session("6agent/SC-01") as sess:
        crew.kickoff()
    print(sess.summary())        # real call count, tokens, cost, latency
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMBudgetExceeded(RuntimeError):
    """Raised when a run has spent its allowed number of LLM requests."""


class _GlobalLLMBudget:
    """
    Process-wide ceiling on LLM requests, with pacing.

    A full four-arm run over 20 scenarios issues roughly 620 Gemini requests
    (measured: 31 per scenario). Free tiers cap both requests-per-minute and
    requests-per-day, so an unguarded run can exhaust the day's allowance part
    way through and leave the evaluation half finished — having spent the quota
    without producing a complete result.

    TRIP_PLANNER_MAX_LLM_CALLS   hard ceiling; raises rather than overspending
    TRIP_PLANNER_LLM_DELAY_S     seconds to wait between requests (RPM relief)
    """

    def __init__(self) -> None:
        self.calls = 0
        self._last_call_at = 0.0
        self._lock = threading.Lock()

    @property
    def limit(self) -> Optional[int]:
        raw = os.getenv("TRIP_PLANNER_MAX_LLM_CALLS", "").strip()
        if not raw:
            return None
        try:
            return max(0, int(raw))
        except ValueError:
            return None

    @property
    def delay(self) -> float:
        try:
            return max(0.0, float(os.getenv("TRIP_PLANNER_LLM_DELAY_S", "0")))
        except ValueError:
            return 0.0

    def remaining(self) -> Optional[int]:
        limit = self.limit
        return None if limit is None else max(0, limit - self.calls)

    def record(self) -> None:
        """Count one observed request. Called by the recorder's callback."""
        with self._lock:
            self.calls += 1

    def would_exceed(self, expected: int) -> bool:
        """
        True if starting a unit of work costing `expected` requests would go
        past the ceiling.

        Checked at scenario boundaries rather than per request: a scenario that
        stops half way still spends its API quota but produces no usable row,
        so the useful place to stop is between whole scenarios.
        """
        limit = self.limit
        return limit is not None and (self.calls + expected) > limit

    def pace(self) -> None:
        """Wait out TRIP_PLANNER_LLM_DELAY_S since the last paced step."""
        delay = self.delay
        if delay <= 0:
            return
        with self._lock:
            if self._last_call_at:
                wait = delay - (time.time() - self._last_call_at)
                if wait > 0:
                    time.sleep(wait)
            self._last_call_at = time.time()


BUDGET = _GlobalLLMBudget()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class LLMSession:
    """Accumulates every LLM request observed while the session is active."""

    def __init__(self, label: str):
        self.label = label
        self.calls: List[Dict[str, Any]] = []
        self.failures: List[Dict[str, Any]] = []
        self.started_at = time.time()
        self.ended_at: Optional[float] = None
        self._lock = threading.Lock()

    def record_success(self, model: str, prompt_tokens: int, completion_tokens: int,
                       cost_usd: float, latency_s: float) -> None:
        with self._lock:
            self.calls.append({
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost_usd": cost_usd,
                "latency_s": round(latency_s, 3),
            })

    def record_failure(self, model: str, error: str, latency_s: float) -> None:
        with self._lock:
            self.failures.append({
                "model": model,
                "error": error[:300],
                "latency_s": round(latency_s, 3),
            })

    def event_count(self) -> int:
        with self._lock:
            return len(self.calls) + len(self.failures)

    def flush(self, quiet_period: float = 1.0, min_wait: float = 0.4, timeout: float = 20.0) -> None:
        """
        Wait for in-flight LiteLLM callbacks to land.

        LiteLLM dispatches success/failure callbacks off the calling thread, so
        reading counters straight after crew.kickoff() undercounts (measured:
        3 completions, only 2 callbacks arrived immediately). Block until no new
        event has arrived for `quiet_period` seconds, capped by `timeout`.
        """
        deadline = time.time() + timeout
        floor = time.time() + min_wait
        last_count = -1
        last_change = time.time()
        while time.time() < deadline:
            count = self.event_count()
            now = time.time()
            if count != last_count:
                last_count = count
                last_change = now
            elif now >= floor and (now - last_change) >= quiet_period:
                return
            time.sleep(0.05)
        logger.debug("llm_metrics flush timed out for session %r", self.label)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            calls = list(self.calls)
            failures = list(self.failures)
        end = self.ended_at if self.ended_at is not None else time.time()
        return {
            "label": self.label,
            "llm_calls": len(calls),
            "llm_failures": len(failures),
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "completion_tokens": sum(c["completion_tokens"] for c in calls),
            "total_tokens": sum(c["total_tokens"] for c in calls),
            "cost_usd": round(sum(c["cost_usd"] for c in calls), 6),
            "llm_time_s": round(sum(c["latency_s"] for c in calls), 2),
            "wall_time_s": round(end - self.started_at, 2),
            "models_used": sorted({c["model"] for c in calls if c["model"]}),
            "failure_details": failures,
        }


class LLMRecorder:
    """
    Registers LiteLLM callbacks once and routes observations into whichever
    session is currently active. Nested sessions are not supported; the most
    recently opened session receives the events.
    """

    def __init__(self) -> None:
        self._active: Optional[LLMSession] = None
        self._previous_stack: List[Optional[LLMSession]] = []
        self._installed = False
        self._lock = threading.Lock()

    # -- callback plumbing -------------------------------------------------

    def _install(self) -> None:
        if self._installed:
            return
        try:
            import litellm
        except ImportError:  # pragma: no cover - litellm is a hard dependency
            logger.warning("litellm unavailable; LLM metrics will report zeros")
            return

        # Tolerant signatures: LiteLLM has varied the callback arity across
        # versions, so accept anything and pull what we need positionally.
        def _on_success(*args, **kwargs):
            try:
                self._handle_success(*args)
            except Exception as exc:  # never let telemetry break a run
                logger.debug("llm_metrics success callback error: %s", exc)

        def _on_failure(*args, **kwargs):
            try:
                self._handle_failure(*args)
            except Exception as exc:
                logger.debug("llm_metrics failure callback error: %s", exc)

        if _on_success not in litellm.success_callback:
            litellm.success_callback.append(_on_success)
        if _on_failure not in litellm.failure_callback:
            litellm.failure_callback.append(_on_failure)
        self._installed = True
        logger.debug("llm_metrics callbacks installed")

    def _handle_success(self, request_kwargs=None, response=None, start_time=None, end_time=None):
        # Counted even outside a session, so the process-wide budget reflects
        # every request made against the provider's daily allowance.
        BUDGET.record()

        session = self._active
        if session is None:
            return

        request_kwargs = request_kwargs or {}
        model = request_kwargs.get("model") or getattr(response, "model", "") or ""

        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        prompt_tokens = completion_tokens = 0
        if usage is not None:
            get = usage.get if isinstance(usage, dict) else lambda k, d=0: getattr(usage, k, d)
            prompt_tokens = _safe_int(get("prompt_tokens", 0))
            completion_tokens = _safe_int(get("completion_tokens", 0))

        cost = 0.0
        # LiteLLM puts a computed cost in the logging payload when it can.
        raw_cost = request_kwargs.get("response_cost")
        if raw_cost is None:
            std = request_kwargs.get("standard_logging_object") or {}
            raw_cost = std.get("response_cost") if isinstance(std, dict) else None
        if raw_cost is not None:
            try:
                cost = float(raw_cost)
            except (TypeError, ValueError):
                cost = 0.0
        else:
            try:
                import litellm
                cost = float(litellm.completion_cost(completion_response=response) or 0.0)
            except Exception:
                cost = 0.0

        session.record_success(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_s=self._elapsed(start_time, end_time),
        )

    def _handle_failure(self, request_kwargs=None, response=None, start_time=None, end_time=None):
        session = self._active
        if session is None:
            return
        request_kwargs = request_kwargs or {}
        error = request_kwargs.get("exception") or response
        session.record_failure(
            model=request_kwargs.get("model", ""),
            error=str(error),
            latency_s=self._elapsed(start_time, end_time),
        )

    @staticmethod
    def _elapsed(start_time, end_time) -> float:
        try:
            if start_time is None or end_time is None:
                return 0.0
            if hasattr(end_time, "timestamp") and hasattr(start_time, "timestamp"):
                return max(0.0, end_time.timestamp() - start_time.timestamp())
            return max(0.0, float(end_time) - float(start_time))
        except Exception:
            return 0.0

    # -- public API --------------------------------------------------------

    def start(self, label: str) -> LLMSession:
        """
        Begin recording without a `with` block — for top-level demo scripts.

        Pair with stop(). Prefer session() anywhere a context manager fits.
        """
        self._install()
        with self._lock:
            current = LLMSession(label)
            self._previous_stack.append(self._active)
            self._active = current
        return current

    def stop(self) -> Optional[LLMSession]:
        """End the session opened by start(), drained and ready to summarise."""
        with self._lock:
            current = self._active
            self._active = self._previous_stack.pop() if self._previous_stack else None
        if current is not None:
            current.ended_at = time.time()
            current.flush()
        return current

    @contextmanager
    def session(self, label: str):
        """Capture every LLM request issued inside this block."""
        self._install()
        with self._lock:
            previous = self._active
            current = LLMSession(label)
            self._active = current
        try:
            yield current
        finally:
            current.ended_at = time.time()
            # Drain before releasing the session, otherwise a late callback from
            # this block would be attributed to the next scenario's session.
            current.flush()
            with self._lock:
                self._active = previous


recorder = LLMRecorder()
