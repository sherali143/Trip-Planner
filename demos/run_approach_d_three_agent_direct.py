"""
Approach D — Three agents, direct API

The final design, and the one the production system runs.

The model is used only where judgement is required: understanding the request
and assembling the plan. Retrieval in between is plain Python. What it gives up
is adaptivity — it cannot widen the dates and search again when results
disappoint.

Run:
    python demos/run_approach_d_three_agent_direct.py

    # with your own request
    python demos/run_approach_d_three_agent_direct.py "Plan 5 nights in Bangkok from Karachi, budget 1200 USD"

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
    raise SystemExit(main("D"))
