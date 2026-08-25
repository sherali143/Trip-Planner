# The dissertation

`CMP7200_Dissertation.docx` is generated. Do not edit it by hand — the next build
overwrites it. Edit the chapter modules in `build/` instead.

```bash
python -m report.build.build_report --figures      # regenerate figures, then build
python -m report.build.build_report                # build (still runs the test suite)
python -m report.build.build_report --no-tests     # build only, faster
python -m report.build.verify_no_hardcoded_numbers # prove no number is typed by hand
python -m report.build.make_viva_deck               # the viva slides
```

## Why it is generated

Every quantitative claim in the document is read from a measured results file
through `evaluation/measured.py`, the single accessor for measured data. Nothing
is typed. That is not a style preference: an earlier version of this project's
documentation hardcoded its headline figures — "5 LLM calls", "~230 seconds",
"85% faster" — and all three turned out to be wrong once the LLM calls were
actually instrumented.

## Layout

| Path | What it is |
|---|---|
| `build/common.py` | Document plumbing: styling, numbering, citations, word counting, `val()` |
| `build/references.py` | The bibliography as data, in BCU Harvard |
| `build/frontmatter.py` | Title page, abstract, contents, figure and table lists |
| `build/ch1_introduction.py` … `ch8_conclusion.py` | One module per chapter |
| `build/appendices.py` | Reference list and the appendices, including the risk register |
| `build/build_report.py` | Assembles the document and enforces every check below |
| `build/verify_no_hardcoded_numbers.py` | The perturbation proof |
| `build/make_viva_deck.py` | The viva slides, built from the same measured data |
| `build/make_charts.py`, `build/make_diagrams.py`, `build/figlib.py` | The figures |
| `build/make_handover.py` | `submission/PROJECT_OVERVIEW.docx`, the plain-English guide |

## What the build refuses to produce

The build fails rather than emitting a document with any of these:

- a figure a chapter references but which does not exist on disk
- a citation key with no entry in `references.py`
- a reference defined but never cited, or one with no DOI, arXiv id or URL
- a banned filler word in the prose (`delve`, `leverage`, `robust`, `seamless`,
  `moreover`, and the rest of the list in `common.py`)
- two paragraphs sharing more than 35% of their eight-word sequences, which is
  how a repeated argument gets caught
- a main body past the 13,200-word hard ceiling (12,000 + the brief's 10%)
- a failing test suite

It also reports the real pass count from `pytest` rather than a remembered one,
and prints the word count per chapter against the limit on every run.

## The perturbation proof

`verify_no_hardcoded_numbers.py` corrupts every number in every results file,
rebuilds, and checks that every distinctive value from the original document has
disappeared and every new one has appeared. It then restores the real data and
confirms the rebuilt document matches the original exactly.

Values that do not change under corruption are not accepted silently: each one
must be attributable to a source the perturbation cannot reach — the test count,
the repository's own line counts, the git history, or the size of a recorded API
response — and the check computes those from their live sources to confirm it.

## Before submitting

Things only you can do:

- [ ] Read the whole document and rewrite passages in your own voice. It is a
      complete, fully-referenced draft, not a submission. You must be able to
      defend every claim in it.
- [ ] Attach the BCU cover sheet
- [ ] Open the document in Word once and update the contents field
      (right-click the placeholder → Update Field). `python-docx` cannot compute
      page numbers, so the field is inserted for Word to fill.
- [ ] Check the student number on the title page is yours
- [ ] Submit via Moodle

Already enforced by the build, so no need to check by hand: font size 11, 1.5
line spacing, page numbers, student number only with no name anywhere, BCU
Harvard referencing, word count within the limit, every figure captioned and
referenced, and every number matching the results files.
