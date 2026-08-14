# Report

The dissertation report belongs here.

## Material available to draw on

| Source | What it gives you |
|---|---|
| `../PROJECT_GUIDE.docx` | Problem, scope, solution, approaches, issues, results, structure |
| `../comparison/results/comparison_results.json` | Every measured number |
| `../figures/*.png` | Seven figures, ready to insert |
| `../comparison/README.md` | Why each architecture exists; which metric to lead with |
| `../proposal/README.md` | Where the implementation diverged from the proposal |
| Git history | What changed and why, for the reflection chapter |

## Regenerating the material

```bash
python scripts/generate_guide.py    # PROJECT_GUIDE.docx
python scripts/make_charts.py       # results charts
python scripts/make_diagrams.py     # architecture diagrams
```

Run these after any evaluation run — the charts and the guide read the results
file directly, so they update themselves.

## Two things to state explicitly

**Scenario coverage.** Check `status` and `scenario_ids` in the results file
before quoting any figure. A partial run is not a finished evaluation.

**Run-to-run variance.** The naive multi-agent arm varied between 19 and 23 LLM
calls on identical input. Reported figures are single-run measurements, and
saying so is stronger than having a marker notice it.
