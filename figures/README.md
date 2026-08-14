# Figures

Generated, never hand-drawn. Split by what makes them change.

```bash
python scripts/make_diagrams.py   # diagrams/  — change when the design changes
python scripts/make_charts.py     # results/   — change after every evaluation run
```

## `diagrams/` — how the system is built

Redraw these only when the architecture itself changes.

| File | Shows | Used in |
|---|---|---|
| `architecture.png` | Four layers, MCP server, A2A protocol, three APIs, cache | Guide §3 |
| `mcp_lifecycle.png` | The six stages of an MCP tool call | Guide §3 |
| `a2a_flow.png` | The six A2A messages exchanged per trip | Guide §3 |
| `four_arms.png` | The four architectures side by side | Guide §4 |

## `results/` — what was measured

These read `comparison/results/comparison_results.json` directly. **No number in
them is typed in**, so a chart cannot disagree with the data it claims to show,
and a partial run is labelled as one in the caption.

| File | Shows | Used in |
|---|---|---|
| `efficiency.png` | LLM calls, tokens, cost and time for all four arms | Guide §6 |
| `tuning_effect.png` | What tuning alone bought (arm B → arm C) | Guide §6.1 |
| `groundedness.png` | Share of quoted prices matching a real fare or rate | Guide §6.2 |

Regenerate `results/` after every evaluation run. `PROJECT_GUIDE.docx` embeds
all seven, so run `scripts/generate_guide.py` afterwards.

## Design decisions

Each of these was a bug before it was a rule:

- **One hue per panel, never a value ramp.** Colouring bars darker-where-bigger
  double-encodes bar length as hue and spends the only free channel on
  information the length already carries. Identity comes from the axis label, so
  the charts survive greyscale printing.
- **Small multiples, never a second y-axis.** LLM calls (1–19) and tokens
  (7k–64k) share no scale; one plot would invent a relationship between them.
- **Direction stated on every panel** — "lower is better" for cost sits beside
  "higher is better" for groundedness in the same document.
- **Values labelled directly.** Nobody should measure a bar against a gridline.
- **Diagram layout is explicit, never auto-placed.** Layer names occupy a
  reserved gutter no connector may enter, and connector labels sit to one side
  of their arrow. Both rules exist because the first drafts routed arrows
  through the word "LAYER 2" and struck lines through their own captions.

## After regenerating, look at them

matplotlib will happily draw text on top of text. Every layout fault in these
figures was found by opening the output, not by reading the code.
