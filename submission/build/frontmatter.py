"""Title page, abstract, contents, and the lists of figures and tables."""

from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from evaluation import measured
from submission.build.common import (ACCENT, AWARD, FACULTY, MODULE_CODE,
                                MODULE_TITLE, MUTED, STUDENT_NUMBER,
                                SUBMISSION_DATE, TITLE, UNIVERSITY, Report, val)


def _centred(report: Report, text: str, *, size: float = 11, bold: bool = False,
             colour=None, space_after: float = 6) -> None:
    paragraph = report.doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = 1.2
    run = paragraph.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if colour is not None:
        run.font.color.rgb = colour
    report._count(text)


def title_page(report: Report) -> None:
    report.start_excluded("title page")
    _centred(report, UNIVERSITY, size=13, bold=True, space_after=2)
    _centred(report, FACULTY, size=10.5, colour=MUTED, space_after=28)

    _centred(report, TITLE, size=17, bold=True, colour=ACCENT, space_after=26)

    _centred(report, f"{MODULE_CODE}  {MODULE_TITLE}", size=11.5, space_after=2)
    _centred(report, "Assessment 2: Project Dissertation", size=11.5, space_after=26)

    # Student number only. The brief: "This assessment will be marked
    # anonymously and should show your student number only."
    _centred(report, f"Student Number: {STUDENT_NUMBER}", size=12.5, bold=True,
             space_after=26)

    _centred(report,
             f"Submitted in partial fulfilment of the requirements for the degree of "
             f"{AWARD}", size=10.5, colour=MUTED, space_after=6)
    _centred(report, SUBMISSION_DATE, size=10.5, colour=MUTED, space_after=30)

    coverage = measured.coverage()
    _centred(report,
             f"All quantitative results in this dissertation were produced by "
             f"{coverage['model']} across "
             f"{val(coverage['scenarios_measured'])} of "
             f"{val(coverage['scenarios_designed'])} designed evaluation scenarios, "
             f"with the API layer in {coverage['api_mode']} mode. Every figure and "
             f"table is generated from the committed result files; no value in this "
             f"document is typed by hand.",
             size=9, colour=MUTED)


def abstract(report: Report) -> None:
    report.start_excluded("abstract")
    report.unnumbered_h1("Abstract")

    coverage = measured.coverage()
    d_vs_c = measured.improvement("D_vs_C")
    c_vs_b = measured.improvement("C_vs_B")
    control = measured.groundedness("A")
    tuned = measured.groundedness("C")
    direct = measured.groundedness("D")
    protocol = measured.protocol_summary()
    gate = measured.gate_agreement()
    anchor = measured.gate_external_validity()

    report.p(f"""
        Travel planning is a natural test of whether a language model can be
        trusted with a task that has verifiable answers. A plan names flights,
        hotels, prices and dates, and each of those either corresponds to
        something bookable or does not. Current single-model assistants perform
        badly on exactly this: the strongest single-agent baseline on the
        TravelPlanner benchmark completes 0.6% of tasks, failing largely through
        invented venues and fabricated prices [@xie2024]. This dissertation asks
        a narrower question than "can agents plan travel", namely: given a
        schema-validated tool layer and a typed inter-agent protocol, what does
        delegating data retrieval to a language model actually cost, and what
        does it buy?
    """)

    report.p(f"""
        A working system was built and then evaluated against itself in four
        configurations: a single model with no tools, a six-agent design in the
        naive configuration first implemented, the same six-agent design after
        its prompt economics were tuned, and a three-agent design that keeps both
        protocols but performs retrieval in ordinary Python. All four share one
        Model Context Protocol server exposing twelve tools over three live
        travel APIs, and one typed agent-to-agent message layer. Every language
        model request is counted by provider callback rather than estimated, and
        every HTTP response is recorded so results replay without an API key.
    """)

    report.p(f"""
        Three findings matter, and the second is not the expected one. First,
        retrieval delegated to a model costs measurably more without being
        measurably better. Against the tuned six-agent arm the three-agent design
        used {val(d_vs_c['llm_calls_pct'], '{:.1f}')}% fewer model requests,
        {val(d_vs_c['latency_pct'], '{:.1f}')}% less wall-clock time and
        {val(d_vs_c['cost_pct'], '{:.1f}')}% less money, with cost and latency
        intervals that do not overlap across
        {val(coverage['repeats_per_arm'])} runs of each. Its groundedness interval
        does overlap the tuned arm's, so the saving comes at no quality penalty
        this evidence can detect — though the tuned arm's mean is the higher of
        the two, and that is recorded rather than rounded away. Second, most of the
        multi-agent penalty was implementation rather than architecture: tuning
        alone cut the six-agent arm's token use by
        {val(c_vs_b['tokens_pct'], '{:.1f}')}%, which narrows the defensible claim
        considerably. Third, tool access is what separates a plausible itinerary
        from a usable one — the tool-less arm quoted
        {val(control['prices_quoted'])} prices and matched
        {val(control['prices_grounded'])} of them to anything real.
    """)

    report.p(f"""
        The evaluation also turned on the system that produced it. A conformance
        audit of the project's own protocol layer passed
        {val(protocol['passed'])} of {val(protocol['total_checks'])} checks:
        message priority is declared on every message and never honoured, and
        {val(len(measured.mcp_schema_stats()['defective_tools']))} of
        {val(measured.mcp_schema_stats()['tools_total'])} tool schemas disagree with
        their implementations. The
        budget feasibility gate, evaluated across all twenty designed scenarios,
        reached a Cohen's kappa of {val(gate['cohens_kappa'], '{:.3f}')} against
        the intent the scenarios were written with, and the reason is traceable:
        its cheapest-fare anchor sits
        {val(abs(anchor['minimum_anchor_error_pct']), '{:.0f}')}% below the
        cheapest fare the flight API actually returned for the one route where
        real fares are recorded. These are defects in the artefact, found by
        measuring it, and they are the most useful evidence the project produced.
    """)

    report.p(f"""
        The principal limitation is stated plainly and early, and it is breadth
        rather than depth. Monthly free-tier quotas on the flight and hotel APIs
        mean the four-arm comparison rests on
        {val(coverage['scenarios_measured'])} recorded scenario of
        {val(coverage['scenarios_designed'])} designed. Repeats replay recorded
        responses and so cost no quota, which is why every figure has an interval;
        additional scenarios cannot be bought the same way. Differences on this
        scenario are therefore measurable, and generalisation to other trips is
        not established.
        The protocol and budget-gate experiments are quota-free and therefore
        cover the full scenario set. The contribution is a reproducible harness
        and a measured, appropriately narrow finding, not a benchmark result.
    """)


def contents(report: Report) -> None:
    """
    Insert a table-of-contents field for Word to populate.

    python-docx cannot compute page numbers, so the field is written as raw
    WordprocessingML and Word fills it in on first open. This is flagged in the
    build output because it needs one manual action.
    """
    report.start_excluded("contents")
    report.unnumbered_h1("Contents")

    paragraph = report.doc.add_paragraph()
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-3" \h \z \u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = ("Right-click here and choose 'Update Field' to build the "
                        "table of contents.")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, separate, placeholder, end):
        run._r.append(element)


def figure_and_table_lists(report: Report) -> None:
    """
    Lists of figures and tables, generated from what was actually inserted.

    Written after the body is built, so the lists cannot disagree with the
    document. Called last by build_report.py and moved into position by Word's
    own field update is not possible, so these appear at the end of the front
    matter section instead — a compromise noted in the build output.
    """
    report.start_excluded("lists of figures and tables")
    report.unnumbered_h1("Figures")
    for tag, caption in report.figure_index:
        paragraph = report.doc.add_paragraph(f"{tag}   {caption}")
        paragraph.paragraph_format.line_spacing = 1.15
        paragraph.paragraph_format.space_after = Pt(3)

    report.unnumbered_h1("Tables", page_break=False)
    for tag, caption in report.table_index:
        paragraph = report.doc.add_paragraph(f"{tag}   {caption}")
        paragraph.paragraph_format.line_spacing = 1.15
        paragraph.paragraph_format.space_after = Pt(3)
