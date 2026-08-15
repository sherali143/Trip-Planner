"""
Arm A: single-LLM baseline — no agents, no tools, no protocols.

Why this arm exists
-------------------
Proposal Objectives 6 and 7 promise ablations "with respect to the single-LLM
baseline" and a target of ">=25% improvement over a single-LLM model". No such
baseline existed in the codebase, so neither objective could be evidenced.

It also anchors the other direction of the comparison. Arms B/C/D all differ in
*how* they retrieve data; this arm retrieves nothing. It is the control that
shows what the MCP tool layer buys in the first place — which is the point the
literature makes about hallucinated venues and fabricated prices (Xie et al.,
2024). Expect it to be the cheapest and fastest arm by a wide margin and the
least trustworthy, and report it as such: cost is only meaningful next to
whether the itinerary refers to anything real.

One LiteLLM completion, one prompt, no tool access.
"""

import os
import time

from litellm import completion

from trip_planner.core.llm_metrics import recorder
from trip_planner.core.resilience import is_rate_limit_error

PROMPT = """You are a travel planner. Create a complete day-by-day travel itinerary for this request:

{request}

Include:
- Recommended flights with airline and price
- Recommended hotels with nightly price and rating
- A separate section for EVERY day of the trip, with morning and afternoon activities and meals
- A budget breakdown
- Travel tips

Give specific names, times and prices."""


def run_single_llm(user_input: str, scenario_id: str = "single") -> dict:
    """Run the single-LLM baseline. Returns the same metrics dict shape as the other arms."""
    start = time.time()
    model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")

    with recorder.session(f"single-llm/{scenario_id}") as llm:
        result = _run(user_input, model, start)

    result["llm"] = llm.summary()
    result["llm_calls"] = result["llm"]["llm_calls"]
    result["total_tokens"] = result["llm"]["total_tokens"]
    result["cost_usd"] = result["llm"]["cost_usd"]
    return result


def _run(user_input: str, model: str, start: float) -> dict:
    messages = [{"role": "user", "content": PROMPT.format(request=user_input)}]

    last_error = None
    for attempt in range(4):
        try:
            response = completion(model=model, messages=messages)
            return {
                "arch": "arm_a_single_llm",
                "success": True,
                "result": response.choices[0].message.content or "",
                # No extraction step exists in this arm; the model is handed the
                # raw request. Recorded explicitly so the field is not mistaken
                # for a missing measurement.
                "extraction": "(no extraction step — single prompt)",
                "latency": time.time() - start,
                "errors": [],
            }
        except Exception as exc:
            last_error = exc
            if not is_rate_limit_error(exc) or attempt == 3:
                break
            time.sleep(12 * (2 ** attempt))

    return {
        "arch": "arm_a_single_llm",
        "success": False,
        "error": str(last_error),
        "latency": time.time() - start,
    }
