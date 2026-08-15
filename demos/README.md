# Demonstrations

Two scripts, for showing the system rather than evaluating it. Both narrate what
is happening as it happens, which `comparison/run_comparison.py` deliberately
does not — that one is a measurement harness and prints a results table.

| Script | What it shows |
|---|---|
| `demo_one_arm.py` | One architecture on one request, step by step |
| `demo_all_arms.py` | All four architectures on the same request, side by side |

```bash
python demos/demo_one_arm.py A          # single model, no tools
python demos/demo_one_arm.py D          # three agents + direct API
python demos/demo_one_arm.py D "Plan 5 nights in Bangkok from Karachi..."

python demos/demo_all_arms.py           # all four, pausing between each
python demos/demo_all_arms.py --no-pause
```

## Run them in replay mode

```bash
export TRIP_PLANNER_API_MODE=replay     # Windows: set TRIP_PLANNER_API_MODE=replay
```

The travel data is then served from the recorded responses in `.api_cache/`. The
output is real captured data — it simply costs no travel-API quota and cannot
fail on a network hiccup part way through a demonstration. Model requests still
cost Gemini free-tier quota, because the model genuinely runs.

## What to point at

`demo_all_arms.py` is the one to show. Its value is the contrast: the tool-less
arm produces a confident, well-formatted itinerary in which **no quoted price
matches anything real**, next to arms that cost more and produce plans whose
prices can be traced back to a retrieved fare. That comparison is the project's
central finding, and it is more convincing watched than described.

`demo_one_arm.py` is for the follow-up question — "what is arm C actually
doing?" — where the step-by-step narration earns its place.

There were once four extra wrapper scripts, one per arm. They differed only in
the letter they passed, so the presentation logic existed in four copies; they
were removed and the letter is now an argument.
