# Submission

Everything a marker reads. Each document is generated except the two PDFs.

| File | What it is | Words | Rebuilt by |
|---|---|---|---|
| `CMP7200_Dissertation.docx` | The dissertation. **The main deliverable.** | 14,316 | `python -m submission.build.build_dissertation --split-appendices` |
| `CMP7200_Appendices.docx` | Appendices A to O. Submitted alongside the dissertation. | 4,426 | the same command |
| `CMP7200_Viva_Presentation.pptx` | The viva slides. Detail is in the speaker notes. | 794 | `python -m submission.build.make_viva_deck` |
| `PROJECT_OVERVIEW.docx` | Plain-English guide to the whole project. Read this first. | — | `python -m submission.build.make_handover` |
| `AI_Trip_Planner_Proposal.pdf` | The original proposal, as submitted. | — | — |
| `CMP7200_Assignment_Brief.pdf` | The assignment brief. | — | — |

## Two files or one

`--split-appendices` writes the appendices as their own document, which takes the
dissertation itself from 18,645 words to 14,316. Without the flag the build
produces a single document containing everything — same text, nothing added or
removed either way. Cross-references resolve across the pair, so "Appendix F" in
Chapter 5 finds its target in both arrangements.

The word count that is assessed is the main body, 12,384 words, and it is stated
on the title page in both arrangements. Appendices and references are excluded
from it.

## Do not edit the generated four by hand

The next build overwrites them. Every number in all three is read from
`trip_planner/evaluation/results/` through `trip_planner/evaluation/measured.py`, so they cannot disagree
with each other or with the measured data. Edit the generators in `submission/build/`
instead.

## Before submitting

- Open the dissertation in Word and update the contents field once
  (right-click the table of contents, Update Field). Word writes page numbers,
  and the generator cannot.
- Close both documents in Word before rebuilding. Word holds a write lock and
  the build fails with a permission error rather than a useful message.
- Submit `CMP7200_Appendices.docx` with the dissertation. It carries the student
  number and a line naming the document it belongs to, so the pair cannot be
  separated by accident.
- Attach the cover sheet. Marking is anonymous, so the document carries the
  student number and no name.
- The brief asks for font size 11 and 1.5 line spacing; the generator sets both.
