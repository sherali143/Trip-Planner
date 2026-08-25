"""
Demonstrates approach D: three agents with the lookups in plain Python.

This is what the system ships, so this is the one to show first.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos._presenter import Approach, present
from evaluation.arm_d_three_agent_direct import run_three_agent_direct

APPROACH_D = Approach(
    code="D",
    name="Three agents, direct retrieval",
    runner=run_three_agent_direct,
    headline=(
        "Two model steps with a retrieval phase between them that uses no model "
        "at all. A model interprets the request, ordinary Python fetches the "
        "data, and a model assembles the plan. The test applied to every step "
        "was: does this require a judgement that cannot be written as code?"
    ),
    steps=[
        "The extractor turns the request into structured fields. This needs a "
        "model: the mapping from phrasing to fields is open-ended.",
        "Four API calls fetch flights, hotels, attractions and restaurants. This "
        "needs no model: the parameters are already fixed and there is one "
        "correct call to make.",
        "The coordinator arranges the retrieved options into a day-by-day plan. "
        "This needs a model: pacing and proximity are matters of judgement.",
    ],
    watch_for=(
        "Two model requests instead of nine or nineteen, and groundedness as good "
        "as the tuned six-agent approach. The retrieval phase reads as almost "
        "zero seconds because the recorded API responses are replayed from disk; "
        "a live run would be slower there. The saving is in request count and "
        "latency more than in money, and the dissertation says so."
    ),
)

if __name__ == "__main__":
    raise SystemExit(present(APPROACH_D))
