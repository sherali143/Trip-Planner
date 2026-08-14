# Demonstration scripts

Walkthroughs for the viva. Each prints what is happening at every step, so the
architecture can be explained while it runs rather than described afterwards.

| Script | Shows |
|---|---|
| `demo_comparison.py` | All four architectures on one request, side by side, ending in a metrics table |
| `demo_6agent_explained.py` | Arm B in detail — each agent, each ReAct loop, each MCP call |
| `demo_3agent_explained.py` | Arm D in detail — and where the LLM was removed from the path |

## Running them

```bash
# free: replays recorded API responses, spends no quota
TRIP_PLANNER_API_MODE=replay python demos/demo_comparison.py --no-pause

# same, with pauses so you can talk between phases
TRIP_PLANNER_API_MODE=replay python demos/demo_comparison.py
```

`--no-pause` skips the "press Enter" prompts. Every script still needs LLM
access; only the travel APIs are replayed from cache.

## Before demonstrating live

Set a ceiling. The travel API free tiers are monthly, and a demo that overruns
them leaves nothing for the evaluation:

```bash
export TRIP_PLANNER_MAX_LIVE_CALLS=5
```

Better still, demonstrate in `replay` mode. The recorded responses in
`.api_cache/` are real API data captured earlier, so the output is genuine —
it simply costs nothing and cannot fail on a network hiccup mid-presentation.

## Note on the numbers they print

Every figure these scripts report is measured through the LiteLLM recorder at
runtime, not hardcoded. Earlier versions printed estimates — including a literal
`llm_calls += 8  # simulated` — which contradicted the measured results in
`comparison/results/`.
