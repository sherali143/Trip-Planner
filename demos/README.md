# Demonstration scripts

For showing the system working. Each narrates what is happening as it happens,
so an architecture can be explained while it runs rather than described
afterwards.

## Run one approach at a time

```bash
python demos/run_approach_a_single_llm.py
python demos/run_approach_b_six_agent_naive.py
python demos/run_approach_c_six_agent_tuned.py
python demos/run_approach_d_three_agent_direct.py
```

Each prints, in order: what the approach is, how it works, what to watch for,
the measured cost, how much of the itinerary traces back to retrieved data, and
the itinerary itself.

Pass your own request as an argument:

```bash
python demos/run_approach_d_three_agent_direct.py "Plan 5 nights in Bangkok from Karachi, budget 1200 USD"
```

## Run all four together

```bash
python demos/demo_comparison.py             # pauses between approaches
python demos/demo_comparison.py --no-pause  # runs straight through
```

Runs A, B, C then D — the optimised design last — and finishes with a metrics
table comparing all four.

## Suggested order for a presentation

| Step | Command | The point being made |
|---|---|---|
| 1 | `run_approach_a_single_llm.py` | The obvious approach. Fast, cheap, and every price invented. This is the problem. |
| 2 | `run_approach_b_six_agent_naive.py` | The proposed multi-agent design as first built. Real data, but the specialists spend most of their calls deciding which tool to use. |
| 3 | `run_approach_c_six_agent_tuned.py` | The same six agents, tuned. Most of the cost disappears without changing the architecture. |
| 4 | `run_approach_d_three_agent_direct.py` | Retrieval moved out of the model entirely. The design that ships. |
| 5 | `demo_comparison.py` | All four side by side. |

That order tells the story the evaluation actually found: the naive multi-agent
penalty is largely an implementation artefact, and what remains after tuning is
a smaller, more honest difference.

## Before demonstrating — use replay mode

```bash
set TRIP_PLANNER_API_MODE=replay        # Windows
export TRIP_PLANNER_API_MODE=replay     # bash
```

The recordings in `.api_cache/` are **real API data captured earlier**, so the
output is genuine. Replaying costs no quota and cannot fail on a network problem
in front of an audience. The flight and hotel APIs allow only 30 and 50 requests
*per month*, so a live demonstration that goes wrong can take the evaluation
down with it.

If you do go live, cap it:

```bash
set TRIP_PLANNER_MAX_LIVE_CALLS=5
```

## Files

| File | Purpose |
|---|---|
| `run_approach_a_single_llm.py` | Approach A alone |
| `run_approach_b_six_agent_naive.py` | Approach B alone |
| `run_approach_c_six_agent_tuned.py` | Approach C alone |
| `run_approach_d_three_agent_direct.py` | Approach D alone |
| `demo_comparison.py` | All four, in order |
| `demo_approach.py` | Shared presentation logic used by the four scripts above |

The four `run_approach_*` scripts are thin: they fix which approach runs and
nothing else. The presentation lives in `demo_approach.py` so all four are shown
identically — four copies would drift, and one would end up printing something
the others do not.

`demo_approach.py` can also be called directly with an approach letter, which is
convenient when scripting:

```bash
python demos/demo_approach.py C
```

## If a run does not complete

The scripts say so and name the cause. The approaches catch their own exceptions
and return a failure result rather than raising, so without that an unavailable
provider would appear only as a silent "0 LLM requests" — which reads as a
successful run of a very cheap approach.

## On the numbers these scripts print

Every figure is measured through provider callbacks at runtime. Earlier versions
printed estimates — including a literal `llm_calls += 8  # simulated` — which
contradicted the measured results in `comparison/results/`.
