"""
Approach A: one model call, no tools.

The control. Shows what fluency alone produces when nothing is retrieved.
"""

import time

from litellm import completion

from trip_planner.core.llm_metrics import recorder
from trip_planner.core.resilience import is_rate_limit_error
from trip_planner.core.gemini_compat import model_string

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
    model = model_string()

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
