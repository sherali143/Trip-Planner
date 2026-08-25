"""Demonstrates approach B: six agents, as first built."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trip_planner.demos._presenter import Approach, present
from trip_planner.evaluation.arm_b_six_agent_naive import run_six_agent_naive

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
