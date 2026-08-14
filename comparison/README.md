# Evaluation harness

The experiment. Four architectures answer the same twenty requests, and this
package measures what each one costs and whether what it produced was real.

## The four arms

| Arm | File | What it is |
|---|---|---|
| **A** | `architecture_single_llm.py` | One LLM call. No agents, no tools, no A2A. The control. |
| **B** | `architecture_6agent.py` | Six agents, naive — the architecture as first built. |
| **C** | `architecture_6agent_optimized.py` | Six agents, tuned — the architecture as the proposal specified. |
| **D** | `architecture_3agent.py` | Three agents; retrieval moved out of the LLM into plain Python. |

Arm C exists so the comparison is not against a straw man. Three commitments in
the proposal were never implemented in arm B — distilled tool output (§3.4),
concurrent search agents (§3.7), distillation inside the MCP lifecycle (§3.5) —
and beating an under-built baseline would prove nothing. Arm C implements them,
and D is compared against C as the headline claim.

## Supporting modules

| File | Purpose |
|---|---|
| `scenarios.py` | The twenty requests, spanning length, distance, party size and budget |
| `metrics.py` | Groundedness: does the itinerary cite data that was actually retrieved? |
| `distilled_tools.py` | Compact tool wrappers used by arm C |
| `run_comparison.py` | Runs the arms, aggregates, checkpoints, writes `results/` |

## Running it

```bash
# free — replays recorded API responses, spends no quota
TRIP_PLANNER_API_MODE=replay python -m comparison.run_comparison

# one or more specific scenarios
TRIP_PLANNER_API_MODE=replay python -m comparison.run_comparison SC-01 SC-04

# a live batch, bounded in both directions
TRIP_PLANNER_MAX_LLM_CALLS=180 TRIP_PLANNER_MAX_LIVE_CALLS=18 \
TRIP_PLANNER_API_MODE=record python -m comparison.run_comparison
```

Runs are **resumable**. Results are checkpointed after every scenario, and a
re-run reuses what is already recorded rather than paying for it again — a full
four-arm pass costs roughly 620 LLM requests, so a run interrupted at scenario
15 must not discard the fifteen it already bought. Pass `--force` to redo a
scenario deliberately.

## Reading the results

`results/comparison_results.json` carries the numbers plus the provenance needed
to trust them: which model produced them, whether the API layer was live or
replayed, how many scenarios were reused, and a `status` of `complete` or
`partial`. **Check `status` before quoting anything** — a partial run is not a
finished evaluation.

## What the metrics mean, and which to lead with

Cost and latency alone would rank arm A first: it is cheap precisely because it
calls nothing and invents its data. `metrics.py` is the counterweight.

Lead with **`prices_grounded_pct`** — the share of prices in the itinerary that
match a fare or nightly rate the APIs actually returned. Guessing a price within
2% of a real one is not something prior knowledge delivers.

Treat the **name** counts as supporting colour only. A model with no tool access
can still name a real airline by guessing the obvious one for the route: on
SC-01 the tool-less arm "matched" Turkish Airlines for Istanbul having called no
API at all.

## Fairness rules the harness enforces

- Every arm runs the same scenario string; nothing depends on phrasing.
- Every arm shares one retry policy, so throttling is never recorded as one
  architecture failing.
- LLM usage is counted from LiteLLM callbacks, never estimated.
- Arm D runs first per scenario so its canonical queries populate the cache and
  the agent arms replay rather than spending fresh quota.
- Budget allocation is deliberately held at the legacy fixed split here. The
  user-facing scenario-aware allocation would change `budget_per_night`, which
  changes the hotel query, which would invalidate every recorded response.
