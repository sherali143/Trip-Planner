# `evaluation/` — the experiment

The experiment. Four architectures answer the same twenty requests, and this
package measures what each one costs and whether what it produced was real.

## The four arms

| Arm | File | What it is |
|---|---|---|
| **A** | `arm_a_single_llm.py` | One LLM call. No agents, no tools, no A2A. The control. |
| **B** | `arm_b_six_agent_naive.py` | Six agents, naive — the architecture as first built. |
| **C** | `arm_c_six_agent_tuned.py` | Six agents, tuned — the architecture as the proposal specified. |
| **D** | `arm_d_three_agent_direct.py` | Three agents; retrieval moved out of the LLM into plain Python. |

## Why each arm exists

Every arm has to justify its place, or it is padding.

**A — Single LLM.** The obvious approach, and the one a reader will ask about
first: why not just prompt a model? Without it, the claim that the tool layer is
necessary rests on assertion. With it, the answer is measured — arm A quotes
prices that match nothing retrieved, which is the hallucination failure the
literature reports (Xie et al., 2024). It also anchors the cost axis: A is the
cheapest arm, which is precisely why cost alone cannot decide the comparison.

**B — Six agents, naive.** The architecture as first built, and the evidence for
the problem the project set out to solve. Without B, "the multi-agent design was
expensive" is a claim; with it, it is a measurement. B is also what makes the
*value of tuning* measurable at all — the single most interesting finding here
requires something to measure C against.

**C — Six agents, tuned.** The architecture as the proposal actually specified.
Three commitments were never implemented in B — distilled tool output (§3.4),
concurrent specialists (§3.7), distillation inside the MCP lifecycle (§3.5) —
and comparing D against an under-built baseline would invite the obvious
objection that the multi-agent arm lost through misconfiguration rather than
design. C removes that objection, and **D is compared against C as the headline
claim**, not against B.

**D — Three agents, direct API.** The proposed improvement, and what the
production system actually runs. It is the only arm that ships.

Presented in that order the four read as one progression — no tools, naive
multi-agent, tuned multi-agent, direct execution — rather than four rivals.

## Supporting modules

| File | Purpose |
|---|---|
| `scenarios.py` | The twenty requests, spanning length, distance, party size and budget |
| `metrics.py` | Groundedness: does the itinerary cite data that was actually retrieved? |
| `distilled_tools.py` | Compact tool wrappers used by arm C |
| `run_comparison.py` | Runs the arms, aggregates, checkpoints, writes `results/` |
| `measured.py` | The single accessor every figure, chapter and document reads results through |
| `verify_approaches.py` | Prints what every approach is actually made of — agents, tools per agent, loop caps — plus a live round trip to the MCP server and the A2A card registry. Costs nothing: building an agent does not call the model. |
| `check_quota.py` | Reports how much monthly travel-API quota is left. **Costs 1 flight and 1 hotel call** — the balance is only returned in a response header, so there is no free way to ask. Writes `results/api_quota.json`. |

## Running it

```bash
# free — replays recorded API responses, spends no quota
TRIP_PLANNER_API_MODE=replay python -m evaluation.run_comparison

# one or more specific scenarios
TRIP_PLANNER_API_MODE=replay python -m evaluation.run_comparison SC-01 SC-04

# a live batch, bounded in both directions
TRIP_PLANNER_MAX_LLM_CALLS=180 TRIP_PLANNER_MAX_LIVE_CALLS=18 \
TRIP_PLANNER_API_MODE=record python -m evaluation.run_comparison
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


## Experiments that cost nothing to run

Two parts of the evaluation need no network, no model and no credentials, so
they cover all twenty scenarios where the four-arm comparison covers one.

```bash
python -m evaluation.exp_protocol      # A2A + MCP conformance, 9 checks
python -m evaluation.exp_budget_gate   # budget feasibility gate, 20 scenarios
```

Both are designed to be able to fail, and both did. The protocol audit passes 3
of 9 checks; the budget gate reaches Cohen's kappa 0.643 against the intent the
scenarios were written with, and the cause of its one miss is measurable — the
cheapest-fare anchor sits about 52% below the cheapest fare the flight API
actually returned for the one route with recorded fares.

Results are written to `results/` and read by everything else through
`measured.py`, which is the single accessor for measured data. Figures and the
dissertation both go through it, so a chart cannot disagree with the table
beside it.
