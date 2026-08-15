"""
WHAT THIS FILE DOES
===================
Demonstrates APPROACH C: the same six agents as approach B, tuned.

This is the most important approach to be able to show, because it is what makes
the whole comparison fair. Without it, approach D could be accused of beating a
badly configured baseline rather than a well configured one — and the honest
answer, which this demo makes visible, is that tuning alone removes most of the
multi-agent penalty.

Nothing about the architecture changes here. Same six roles, same data, same
model. Only the prompt economics differ.

    python demos/approach_c_six_agent_tuned.py              # playback, always works
    python demos/approach_c_six_agent_tuned.py --live       # run it for real
    python demos/approach_c_six_agent_tuned.py --no-pause   # no "press Enter" stops

Playback replays the recorded measurement with no API calls and no model
requests, so it works when every quota is exhausted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demos._presenter import Approach, present
from evaluation.arm_c_six_agent_tuned import run_six_agent_tuned

APPROACH_C = Approach(
    code="C",
    name="Six agents, tuned",
    runner=run_six_agent_tuned,
    headline=(
        "The proposal's six-agent design, configured properly. Each specialist "
        "gets one narrow tool instead of up to eight, tool results are distilled "
        "to the top few options, role descriptions are short, the reasoning loop "
        "is capped at three iterations, and the three specialists run at the same "
        "time rather than one after another."
    ),
    steps=[
        "The extractor turns the request into structured fields.",
        "Flight, hotel and activities specialists run CONCURRENTLY.",
        "Each calls one narrow tool once and reports the distilled result.",
        "The coordinator assembles the plan from what they found, with no tools "
        "of its own.",
    ],
    watch_for=(
        "Compare the token count against approach B. The architecture is "
        "identical and the data is identical, so the whole difference is prompt "
        "economics. Also note that the summed model time exceeds the wall-clock "
        "time — that is only possible if the three specialists really did run "
        "concurrently, which is the proposal's parallelism commitment being met."
    ),
)

if __name__ == "__main__":
    raise SystemExit(present(APPROACH_C))
