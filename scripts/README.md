# Figure generation

Every diagram and chart in the dissertation is generated from code. Nothing is
drawn by hand, and no value in a figure is typed by hand — the charts read
measured results through `comparison/measured.py`, the same accessor the report
chapters use.

```bash
python scripts/make_diagrams.py    # 8 diagrams -> figures/diagrams/
python scripts/make_charts.py      # 6 charts   -> figures/results/
```

Both exit non-zero if anything is wrong, so a broken figure stops the report
build rather than reaching the document.

| File | What it is |
|---|---|
| `figlib.py` | The layout engine. Everything else builds on it. |
| `make_diagrams.py` | Architecture, data flow, sequence, the four arms, A2A, MCP lifecycle, conceptual framework, methodology |
| `make_charts.py` | Cost, token decomposition, tuning ablation, groundedness, protocol conformance, budget gate |

## Why there is a layout engine

The first generation of these diagrams estimated text width from character
count. On a proportional font that is wrong in both directions, and the results
were labels overflowing their boxes, connectors drawn through text, and titles
colliding with content whenever a canvas was resized. Each defect was found by
looking at the exported image, which is a slow and unreliable way to find a
layout bug.

`figlib.py` makes layout mechanical instead:

- text is **measured** with the real renderer at the real font size, then wrapped
  to a width in data units
- boxes **grow** to fit their measured contents rather than clipping them
- a header band is **reserved**, so a title cannot collide with content
- connectors are **orthogonal**, and a diagonal has to be opted into explicitly
- labels carry an **opaque background**, so no line strikes through them
- `validate()` raises `LayoutError` on any overlap, any content outside the
  frame, any text larger than its box, and any connector that cuts through a box
  it does not belong to

That validator has already caught a box positioned off-canvas and three diagonal
connectors passing through unrelated boxes — two of which had been exported and
not noticed.

Everything is written at **300 dpi**, the floor for print-quality figures in a
submitted document.

## Adding a figure

Add a function to `make_diagrams.py` or `make_charts.py`, then add it to the
`DIAGRAMS` or `CHARTS` list at the bottom. Read values through
`comparison.measured` — never type a number into a figure, because a figure that
disagrees with the table beside it is worse than no figure.
