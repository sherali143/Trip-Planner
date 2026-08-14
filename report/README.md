# Report

The dissertation report belongs here.

## Files here

| File | What it is |
|---|---|
| `Dissertation_TEMPLATE.docx` | **Start here.** A formatted Word shell: 7 chapters, 36 sections, all 7 figures already placed, 11 pt / 1.5 spacing as the brief requires. Write directly into it. |
| `REPORT_OUTLINE.md` | The same structure in plain text, with the word budget and evidence map |

## Using the template

Open `Dissertation_TEMPLATE.docx` and save it under your own filename. Each
section carries a grey italic **GUIDANCE** box saying what belongs there and
which artefact supports it, followed by a `[placeholder]` to type into. Delete
the guidance boxes as you go — 42 of them, and none should survive to
submission.

Regenerate the template with `python scripts/generate_report_template.py`. Doing
so overwrites `Dissertation_TEMPLATE.docx`, so work in a renamed copy.

`REPORT_OUTLINE.md` is a planning aid: chapter structure, what each section has
to contain to satisfy the published marking criteria, which evidence in this
repository supports it, and a word budget that sums to 12,000. It contains no
prose for the submission — every `[WRITE]` marker is yours. The assignment brief
is explicit that assessed writing must be your own and not an AI tool's.

## Material available to draw on

| Source | What it gives you |
|---|---|
| `../PROJECT_GUIDE.docx` | Problem, scope, solution, approaches, issues, results, structure |
| `../comparison/results/comparison_results.json` | Every measured number |
| `../figures/diagrams/` | Four design diagrams — architecture, MCP, A2A, the four arms |
| `../figures/results/` | Three measured charts — cost, tuning effect, groundedness |
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
