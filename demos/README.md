# Demonstration scripts

For showing the system working. Each narrates what is happening as it happens,
so an architecture can be explained while it runs rather than described
afterwards.

| Script | Shows |
|---|---|
| `demo_approach.py A\|B\|C\|D` | **One** architecture in isolation — how it works, what it costs, whether its output is real |
| `demo_comparison.py` | **All four** on the same request, ending in a metrics table |

## Showing each approach separately

```bash
python demos/demo_approach.py A     # single LLM, no tools
python demos/demo_approach.py B     # six agents, naive
python demos/demo_approach.py C     # six agents, tuned
python demos/demo_approach.py D     # three agents + direct API
```

Each run prints, in order: what the approach is, how it works, what to watch
for, the measured cost, how much of the itinerary traces back to retrieved
data, and the itinerary itself.

Pass your own request as a second argument:

```bash
python demos/demo_approach.py D "Plan 5 nights in Bangkok from Karachi, budget 1200 USD"
```

## Showing all four together

```bash
python demos/demo_comparison.py             # pauses between arms
python demos/demo_comparison.py --no-pause  # runs straight through
```

## Before demonstrating — use replay mode

```bash
set TRIP_PLANNER_API_MODE=replay        # Windows
export TRIP_PLANNER_API_MODE=replay     # bash
```

The recorded responses in `.api_cache/` are **real API data captured earlier**,
so the output is genuine. Replaying it costs no quota and cannot fail on a
network problem in front of an audience. The flight and hotel APIs allow only
30 and 50 requests *per month*, so a live demonstration that goes wrong can
take the evaluation down with it.

If you do go live, cap it:

```bash
set TRIP_PLANNER_MAX_LIVE_CALLS=5
```

## A suggested order for presenting

1. **`demo_approach.py A`** — the obvious approach. Fast, cheap, and every price
   in its itinerary is invented. This is the problem the project addresses.
2. **`demo_approach.py B`** — the proposed multi-agent design as first built. Real
   data, but the specialists spend most of their calls deciding which tool to use.
3. **`demo_approach.py C`** — the same six agents, tuned. Most of the cost
   disappears without changing the architecture.
4. **`demo_approach.py D`** — retrieval moved out of the model entirely.
5. **`demo_comparison.py`** — all four side by side.

That order tells the story the evaluation actually found: the naive multi-agent
penalty is largely an implementation artefact, and what remains after tuning is
a smaller, more honest difference.

## Why one script rather than four

The arms differ in which function is called, not in how a run should be
presented. Four copies of the presentation logic would drift apart, and one of
them would end up printing something the others do not.

## On the numbers these scripts print

Every figure is measured through provider callbacks at runtime. Earlier versions
printed estimates — including a literal `llm_calls += 8  # simulated` — which
contradicted the measured results in `comparison/results/`.
