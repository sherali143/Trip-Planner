"""
Approach C — Six agents, tuned

The same six agents, configured as the proposal actually specified.

One narrow tool per specialist instead of up to eight, reasoning capped at three
iterations, tool results distilled to the options that matter, and the three
specialists running concurrently. Same agents, same APIs, same data — only the
prompt economics differ. Compare its cost against approach B.

Run:
    python demos/run_approach_c_six_agent_tuned.py

    # with your own request
    python demos/run_approach_c_six_agent_tuned.py "Plan 5 nights in Bangkok from Karachi, budget 1200 USD"

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
    raise SystemExit(main("C"))
