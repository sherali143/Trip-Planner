"""
WHAT THIS FILE DOES
===================
Demonstrates APPROACH A: one language model, on its own, with no tools, no
agents and no protocols.

This is the control in the experiment. It exists to answer a question the other
three approaches cannot: what does the tool layer actually buy? Approach A is
the cheapest and the fastest to write, and every price it prints is invented,
because it never calls anything.

    python demos/approach_a_single_llm.py              # playback, always works
    python demos/approach_a_single_llm.py --live       # run it for real
    python demos/approach_a_single_llm.py --no-pause   # no "press Enter" stops

Playback replays the recorded measurement with no API calls and no model
requests, so it works when every quota is exhausted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos._presenter import Approach, present
from evaluation.arm_a_single_llm import run_single_llm

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
