# Figures

Generated, not hand-drawn. Regenerate after any evaluation run:

```bash
python figures/make_charts.py     # results charts — read from the results JSON
python figures/make_diagrams.py   # architecture and flow diagrams
```

## Results charts — `make_charts.py`

These read `comparison/results/comparison_results.json` directly. **No number in
them is typed in**, so a figure cannot drift from the data it claims to show. If
the results file says the run was partial, the caption says so too.

| File | Shows |
|---|---|
| `fig_efficiency.png` | LLM requests, tokens, cost and time for all four arms |
| `fig_groundedness.png` | Share of quoted prices matching a real fare or rate |
| `fig_tuning_effect.png` | What tuning alone bought (arm B → arm C) |

## Diagrams — `make_diagrams.py`

| File | Shows |
|---|---|
| `fig_architecture.png` | Four layers, MCP server, A2A protocol, three APIs, cache |
| `fig_four_arms.png` | The four architectures side by side |
| `fig_a2a_flow.png` | The six A2A messages exchanged per trip |
| `fig_mcp_lifecycle.png` | The six stages of an MCP tool call |

## Design decisions

Worth knowing before editing, because each of these was a bug first:

- **One hue per panel, never a value ramp.** Colouring bars darker-where-bigger
  double-encodes bar length as hue and spends the only free channel on
  information the length already carries. Identity comes from the axis label, so
  the charts also survive greyscale printing.
- **Small multiples, never a second y-axis.** LLM requests (1–19) and tokens
  (7k–64k) share no scale; putting them on one plot would invent a relationship.
- **Direction is stated on every panel** ("lower is better" / "higher is
  better"), because cost and groundedness point opposite ways in the same report.
- **Values are labelled directly** — no one should have to measure a bar against
  a gridline.
- **Diagram layout is explicit, never auto-placed.** Layer names live in a
  reserved left gutter that no connector may enter, and connector labels sit to
  one side of their arrow. Both rules exist because the first drafts routed
  arrows through "LAYER 2" and struck lines through their own captions.

## Verify before use

`matplotlib` will happily render text on top of text. After regenerating, open
each PNG and check for collisions — every layout problem in these figures was
found by looking at the output, not by reading the code.
