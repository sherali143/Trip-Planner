# Submission

Everything a marker reads. Each document is generated except the two PDFs.

| File | What it is | Rebuilt by |
|---|---|---|
| `CMP7200_Dissertation.docx` | The dissertation. **The main deliverable.** | `python -m submission.build.build_dissertation` |
| `CMP7200_Viva_Presentation.pptx` | The viva slides. Detail is in the speaker notes. | `python -m submission.build.make_viva_deck` |
| `PROJECT_OVERVIEW.docx` | Plain-English guide to the whole project. Read this first. | `python -m submission.build.make_handover` |
| `AI_Trip_Planner_Proposal.pdf` | The original proposal, as submitted. | — |
| `CMP7200_Assignment_Brief.pdf` | The assignment brief. | — |

## Do not edit the generated three by hand

The next build overwrites them. Every number in all three is read from
`trip_planner/evaluation/results/` through `trip_planner/evaluation/measured.py`, so they cannot disagree
with each other or with the measured data. Edit the generators in `submission/build/`
instead.

## Before submitting

- Open the dissertation in Word and update the contents field once
  (right-click the table of contents, Update Field). Word writes page numbers,
  and the generator cannot.
- Attach the cover sheet. Marking is anonymous, so the document carries the
  student number and no name.
- The brief asks for font size 11 and 1.5 line spacing; the generator sets both.
