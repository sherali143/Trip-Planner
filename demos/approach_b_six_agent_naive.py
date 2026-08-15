"""
WHAT THIS FILE DOES
===================
Demonstrates APPROACH B: six agents in the naive configuration, which is the
architecture the proposal specified and the way it was first implemented.

Each specialist agent is given a set of tools and left to work out for itself
how to use them, inside a reasoning loop that may iterate many times. It
retrieves real data and it is expensive, and this demo exists to show exactly
where that expense comes from.

    python demos/approach_b_six_agent_naive.py              # playback, always works
    python demos/approach_b_six_agent_naive.py --live       # run it for real
    python demos/approach_b_six_agent_naive.py --no-pause   # no "press Enter" stops

Playback replays the recorded measurement with no API calls and no model
requests, so it works when every quota is exhausted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos._presenter import Approach, present
from evaluation.arm_b_six_agent_naive import run_six_agent_naive

APPROACH_B = Approach(
    code="B",
    name="Six agents, naive configuration",
    runner=run_six_agent_naive,
    headline=(
        "Six specialised agents: an extractor, three search specialists for "
        "flights, hotels and activities, and a coordinator that assembles their "
        "findings. Each specialist holds several tools and decides for itself "
        "which to call, how many times, and when to stop."
    ),
    steps=[
        "The extractor turns the free-text request into structured fields.",
        "The flight agent is handed eight tools and reasons about which to call.",
        "The hotel agent does the same, also with eight tools.",
        "The activities agent searches for attractions and restaurants.",
        "The coordinator assembles everything into a day-by-day plan.",
    ],
    watch_for=(
        "The request count, and where the tokens go. Every tool bound to an agent "
        "puts its full JSON schema into that agent's prompt, and the prompt is "
        "re-sent on every iteration of its reasoning loop. Roughly three quarters "
        "of this approach's token spend is re-sent context rather than new "
        "information. Approach C fixes exactly this without changing the "
        "architecture."
    ),
)

if __name__ == "__main__":
    raise SystemExit(present(APPROACH_B))
