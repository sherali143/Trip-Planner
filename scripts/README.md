# Generators

Everything here produces a deliverable from the project's own data. Nothing is
written by hand, so no figure or document can drift from what the code measured.

| Script | Produces |
|---|---|
| `generate_guide.py` | `PROJECT_GUIDE.docx` in the project root |
| `make_charts.py` | The three results charts in `figures/` |
| `make_diagrams.py` | The four architecture diagrams in `figures/` |

```bash
python scripts/generate_guide.py
python scripts/make_charts.py
python scripts/make_diagrams.py
```

Run all three after any evaluation run.

`generate_guide.py` and `make_charts.py` read
`comparison/results/comparison_results.json`. If it is missing they say so
rather than inventing plausible numbers — an earlier version of the document
hardcoded "5 LLM calls", which instrumentation later showed to be 19 to 23.

`DEVELOPMENT_NOTES.md` holds working notes: current state, API gotchas and
quota rules.
