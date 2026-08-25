"""Demonstrates approach A: one model call, no tools."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trip_planner.demos._presenter import Approach, present
from trip_planner.evaluation.arm_a_single_llm import run_single_llm

APPROACH_A = Approach(
    code="A",
    name="Single LLM (no agents, no tools)",
    reads_apis=False,
    runner=run_single_llm,
    headline=(
        "One prompt, one model request, one answer. The model is asked for a "
        "complete itinerary and writes it from what it already knows. There is "
        "no retrieval step, so there is nothing to check the answer against."
    ),
    steps=[
        "The traveller's request is put into a single prompt.",
        "The model is asked for flights, hotels, a day-by-day plan and a budget.",
        "The model answers from prior knowledge. No API is contacted.",
        "The answer is returned as the finished itinerary.",
    ],
    watch_for=(
        "The output looks complete and confident, and it is the least trustworthy "
        "of the four. Compare its quoted prices against approach D's: this one "
        "matched none of them to a real fare. That is the failure the literature "
        "describes, reproduced here under measurement rather than asserted."
    ),
)

if __name__ == "__main__":
    raise SystemExit(present(APPROACH_A))
