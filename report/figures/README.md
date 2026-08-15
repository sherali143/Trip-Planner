# Figures

Generated output. Nothing here is edited by hand — regenerate instead:

```bash
python report/build/make_diagrams.py    # diagrams/
python report/build/make_charts.py      # results/
```

Everything is 300 dpi, and every diagram passes geometric validation before it
is written. See `../scripts/README.md` for how that works.

## `diagrams/` — what the system is

These change when the **design** changes.

| File | Shown in |
|---|---|
| `architecture.png` | Design — the four layers, and which paths actually use the tool server |
| `dataflow.png` | Design — what is persisted, and where each reported number comes from |
| `sequence.png` | Design — one request end to end, with measured phase timings |
| `four_arms.png` | Design — the four evaluated architectures side by side |
| `a2a_flow.png` | Design — the six typed messages, and the two behaviours that are not implemented |
| `mcp_lifecycle.png` | Design — the six-stage tool call, and the two stages that return early |
| `conceptual_framework.png` | Literature review — failure mode, design response, measured outcome |
| `methodology.png` | Methodology — the three design-science cycles as they actually ran |

Three of these read measured values (phase timings, token counts, conformance
results), so they are not purely structural — rerun them after a measurement run.

## `results/` — what was measured

These change when the **results** change.

| File | Shows |
|---|---|
| `efficiency.png` | Requests, tokens, cost and time for all four arms |
| `token_decomposition.png` | Prompt vs completion tokens — why the tuned arm is cheaper |
| `tuning_effect.png` | The B-to-C ablation: how much of the penalty was implementation |
| `groundedness.png` | Quoted prices matching a real fare, and why entity matching is weak |
| `protocol_conformance.png` | All nine conformance checks, pass or fail |
| `budget_gate.png` | The gate's decision on 20 scenarios, and the anchor error behind the miss |

Every chart carries its own scope line — how many scenarios, how many repeats,
which model, which API mode — so a single-scenario result can never be mistaken
for a complete evaluation.
