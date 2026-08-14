"""
Approach B — Six agents, naive

The architecture as it was first built, following the proposal's agent
decomposition.

Specialists reason their way to data: decide which tool to use, call it, read
the result, repeat. Each carries up to eight tool schemas that are re-sent on
every iteration, and raw API payloads enter the context. This is the arm whose
cost motivated the rest of the project.

Run:
    python demos/run_approach_b_six_agent_naive.py

    # with your own request
    python demos/run_approach_b_six_agent_naive.py "Plan 5 nights in Bangkok from Karachi, budget 1200 USD"

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
    raise SystemExit(main("B"))
