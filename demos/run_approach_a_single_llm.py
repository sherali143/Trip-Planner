"""
Approach A — Single LLM

One model call. No agents, no tools, no protocol.

This is the control: the obvious way to answer the question, and the one that
shows why the rest of the system exists. It produces a fluent itinerary quickly
and cheaply, and none of the prices in it were retrieved from anywhere.

Run:
    python demos/run_approach_a_single_llm.py

    # with your own request
    python demos/run_approach_a_single_llm.py "Plan 5 nights in Bangkok from Karachi, budget 1200 USD"

Set TRIP_PLANNER_API_MODE=replay to use recorded API responses — real captured
data, no quota spent, and it cannot fail on a network hiccup mid-demonstration.

The presentation logic lives in demo_approach.py so all four approaches are
shown identically; this file only fixes which one runs.
"""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from demo_approach import main

if __name__ == "__main__":
    raise SystemExit(main("A"))
