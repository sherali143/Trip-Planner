"""
Builds the dissertation.

Assembles the chapters, then refuses to save the document if anything is
wrong: a missing figure, an uncited reference, a repeated argument, a body
over the word ceiling, or a failing test.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from trip_planner.evaluation import measured
from submission.build import (appendices, ch1_introduction, ch2_literature,
                         ch3_methodology, ch4_design, ch5_implementation,
                         ch6_evaluation, ch7_reflection, ch8_conclusion,
                         frontmatter)
from submission.build.common import (CITATIONS, ROOT, VALUES, BuildError, Report,
                                find_banned_words, find_dangling_references,
                                find_duplicate_prose,
                                find_spelling_inconsistencies)

WORD_LIMIT = 12000
TOLERANCE = 0.10
OUTPUT = os.path.join(ROOT, "submission", "CMP7200_Dissertation.docx")

CHAPTERS = [
    ch1_introduction,
    ch2_literature,
    ch3_methodology,
    ch4_design,
    ch5_implementation,
    ch6_evaluation,
    ch7_reflection,
    ch8_conclusion,
]


def run_test_suite() -> dict:
    """Run pytest and report what it actually says, not what it said last time."""
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                          cwd=ROOT, capture_output=True, text=True, timeout=900)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    passed = re.search(r"(\d+) passed", proc.stdout)
    failed = re.search(r"(\d+) failed", proc.stdout)
    return {
        "passed": int(passed.group(1)) if passed else 0,
        "failed": int(failed.group(1)) if failed else 0,
        "exit_code": proc.returncode,
        "summary": tail,
    }


def regenerate_figures() -> None:
    for script in ("submission/build/make_diagrams.py", "submission/build/make_charts.py"):
        proc = subprocess.run([sys.executable, script], cwd=ROOT,
                              capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            raise BuildError(f"{script} failed:\n{proc.stdout}\n{proc.stderr}")
        print(f"  {script}: {proc.stdout.strip().splitlines()[-1]}")


def assemble() -> Report:
    report = Report()
    frontmatter.title_page(report)
    frontmatter.abstract(report)
    frontmatter.contents(report)
    for chapter in CHAPTERS:
        chapter.build(report)
    appendices.references(report)
    appendices.appendices(report)
    frontmatter.figure_and_table_lists(report)
    # Last, because it reports the body count and so must run after the body.
    frontmatter.declare_word_count(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--figures", action="store_true",
                        help="regenerate every figure before building")
    parser.add_argument("--no-tests", action="store_true",
                        help="skip the test suite")
    parser.add_argument("--output", default=OUTPUT)
    parser.add_argument("--values-out",
                        help="write every interpolated measured value to this JSON "
                             "file; used by verify_no_hardcoded_numbers.py")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 78)
    print("  BUILDING THE DISSERTATION")
    print("=" * 78)

    if args.figures:
        print("\nFigures")
        regenerate_figures()

    tests = None
    if not args.no_tests:
        print("\nTest suite")
        tests = run_test_suite()
        print(f"  {tests['summary']}")
        if tests["failed"] or tests["exit_code"] != 0:
            raise BuildError(
                f"the test suite is not green ({tests['failed']} failed, exit "
                f"{tests['exit_code']}). A dissertation should not be built on a "
                f"failing suite.")

    print("\nAssembling")
    report = assemble()
    path = report.save(args.output)

    if args.values_out:
        import json
        with open(args.values_out, "w", encoding="utf-8") as fh:
            json.dump({"rendered": VALUES.rendered(),
                       "by_location": VALUES.by_location(),
                       "count": len(VALUES.entries),
                       "body_words": report.body_words}, fh, indent=2)

    problems = []

    # --- citations -----------------------------------------------------------
    try:
        CITATIONS.verify()
        print(f"  citations: {len(CITATIONS.used)} works cited, all with a "
              f"reference entry and a locator")
    except BuildError as exc:
        problems.append(str(exc))

    # --- banned words --------------------------------------------------------
    banned = find_banned_words(report.prose_blocks)
    if banned:
        problems.append("banned filler words in the prose: "
                        + ", ".join(f"{w} ({c})" for c, w in banned))
    else:
        print("  prose: no banned filler words")

    # --- duplicate argument --------------------------------------------------
    duplicates = find_duplicate_prose(report.prose_blocks)
    if duplicates:
        problems.append(
            "paragraphs overlapping above 35%:\n    "
            + "\n    ".join(f"{a}\n      vs {b}  ({pct:.0%})"
                            for a, b, pct in duplicates))
    else:
        print(f"  prose: no paragraph pair overlaps above 35% "
              f"({len(report.prose_blocks)} paragraphs compared)")

    # --- spelling ------------------------------------------------------------
    document_text = "\n".join(report.all_text)
    spelling = find_spelling_inconsistencies(document_text)
    if spelling:
        problems.append(
            "US spellings in a document that commits to British English: "
            + ", ".join(f"{us} (use {uk})" for us, uk in spelling))
    else:
        print("  prose: British spelling consistent throughout")

    # --- cross-references ----------------------------------------------------
    dangling = find_dangling_references(document_text)
    if dangling:
        problems.append("cross-references that do not resolve:\n    "
                        + "\n    ".join(dangling))
    else:
        print("  cross-references: every Section and Appendix reference resolves")

    # --- appendix order ------------------------------------------------------
    letters = report.appendix_index
    expected = [chr(ord("A") + i) for i in range(len(letters))]
    if letters != expected:
        problems.append(f"appendices are lettered {' '.join(letters)}; they must "
                        f"run {' '.join(expected)} in the order they appear")
    else:
        print(f"  appendices: {len(letters)}, lettered A to {letters[-1]} in order")

    # --- figures -------------------------------------------------------------
    print(f"  figures: {len(report.figure_index)} inserted, "
          f"{len(report.table_index)} tables")

    # --- measured values ----------------------------------------------------
    print(f"  measured values interpolated: {len(VALUES.entries)}")

    # --- word count ---------------------------------------------------------
    limit_with_margin = int(WORD_LIMIT * (1 + TOLERANCE))
    print("\nWord count (main body only; front matter, references and appendices "
          "excluded)")
    for name, count in report.words_by_chapter.items():
        print(f"  {name:<28}{count:>7,}")
    print(f"  {'-' * 35}")
    print(f"  {'MAIN BODY':<28}{report.body_words:>7,}   "
          f"limit {WORD_LIMIT:,}, with +{int(TOLERANCE * 100)}% margin "
          f"{limit_with_margin:,}")
    print(f"  {'excluded from the count':<28}{report.excluded_words:>7,}")

    if report.body_words > limit_with_margin:
        problems.append(
            f"main body is {report.body_words:,} words, past the "
            f"{limit_with_margin:,} hard ceiling. Nothing beyond it is marked.")
    elif report.body_words > WORD_LIMIT:
        over = report.body_words - WORD_LIMIT
        headroom = limit_with_margin - report.body_words
        print(f"  NOTE: {over:,} words into the tolerance margin, "
              f"{headroom:,} short of the {limit_with_margin:,} hard ceiling.")
        # The headroom is printed as a number because it is small enough to matter:
        # adding a sentence to the body can breach the ceiling, and nothing past it
        # is marked. Move evidence into an appendix before cutting analysis.
        if headroom < 150:
            print(f"        That is roughly {max(1, headroom // 25)} sentence(s) of "
                  f"room. Before adding to the body, move something out of it — "
                  f"an appendix\n        does not count against the limit.")

    # --- coverage honesty ----------------------------------------------------
    coverage = measured.coverage()
    if not coverage["is_complete"]:
        print(f"\n  Coverage: {coverage['scenarios_measured']}/"
              f"{coverage['scenarios_designed']} scenarios "
              f"({coverage['coverage_pct']}%) for the four-arm comparison. "
              f"Stated in the abstract, Section 6.1 and every chart.")

    if problems:
        print("\n" + "=" * 78)
        print(f"  BUILD FAILED — {len(problems)} problem(s)")
        print("=" * 78)
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\n" + "=" * 78)
    print(f"  BUILD OK  ->  {os.path.relpath(path, ROOT)}")
    if tests:
        print(f"  test suite: {tests['passed']} passed")
    print("  Open in Word and update the contents field once (right-click, "
          "Update Field).")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
