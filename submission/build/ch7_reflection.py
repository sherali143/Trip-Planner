"""Chapter 7: reflection."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("7 Critical reflection")
    report.h1("Critical Reflection")

    coverage = measured.coverage()
    summary = measured.protocol_summary()
    schema = measured.mcp_schema_stats()

    # ------------------------------------------------------------------ 7.1
    report.h2("7.1  Achievement against each objective")

    report.table(
        ["Objective", "Status", "Honest assessment, with the evidence"],
        [
            ["1. Tool server with schema-validated tools", "Met with defects",
             f"Twelve tools advertised and dispatchable, but only "
             f"{val(schema['clean'])} of {val(schema['inspectable'])} inspectable schemas match "
             f"their implementation (Section 6.4). The server works; the validation "
             f"guarantee it was built for is weaker than claimed"],
            ["2. Typed protocol with priority queuing", "Partly met",
             "Eight agent cards, six message types and permission validation all "
             "work, and every shipped message is permitted. Priority queuing was "
             "specified and is not implemented — the queue is FIFO (Section 6.4)"],
            ["3. Agent layer with measured model usage", "Met",
             "Provider callbacks capture every request, including those inside "
             "reasoning loops. The strongest part of the work: it replaced a "
             "hardcoded count that had been reported as a measurement"],
            ["4. Record/replay with a live-call ceiling", "Met",
             f"{val(measured.api_cache_stats()['entries'])} committed responses; the "
             f"comparison replays with no credentials. Load-bearing — without it "
             f"there would be no reproducible result at all"],
            ["5. Working demonstration", "Met",
             "Command-line and web interfaces both drive the shipped configuration. "
             "The web interface uses a fixed question sequence rather than the "
             "conversational agent (Section 7.3)"],
            ["6. Four-architecture comparison", "Met, with intervals",
             f"All four arms runnable and reproducible, measured "
             f"{val(coverage['repeats_per_arm'])} times each on "
             f"{val(coverage['scenarios_measured'])} of "
             f"{val(coverage['scenarios_designed'])} scenarios, so every figure has "
             f"a standard deviation and a 95% interval. Breadth is the remaining gap"],
            ["7. Evaluation across twenty scenarios", "Met for two of three "
             "experiments",
             "Sections 6.4 and 6.5 cover all twenty; Section 6.2 does not. No "
             "rearrangement of the work would have changed that, because the "
             "constraint is a monthly quota"],
        ],
        "Objectives against evidence. Three of seven are qualified.",
        widths=[1.55, 1.05, 3.6],
        font_pt=8.5,
    )

    report.p("""
        Objective 1 is the one whose single-word status misleads. It was met as an
        artefact and undermined as a guarantee: a server exists, exposes tools, and
        validates nothing about the correspondence between what it advertises and
        what it runs.
    """)

    # ------------------------------------------------------------------ 7.2
    report.h2("7.2  Where the protocols ended up in the shipped path")

    report.p("""
        The two protocols this project is named for are less load-bearing in the
        shipped configuration than the proposal implied. The message layer records the exchange and never dispatches it: the
        orchestrator sends messages and reads the conversation history but never
        dequeues, so the delivery machinery, the executor class and the
        message-processing loop are all unreachable in production. The tool server is
        driven over JSON-RPC only by the naive six-agent arm; the shipped path imports
        the same functions and calls them in process.
    """)

    report.p("""
        This follows from the pivot rather than from carelessness. Once agents
        stopped performing retrieval there was nothing left for them to send each
        other about it, so the message layer's role narrowed to an audit trail. That
        is genuinely useful, since it is what makes the exchange inspectable, but it
        is not what was promised. The pivot that produced the project's main result
        also hollowed out two of its stated deliverables.
    """)

    # ------------------------------------------------------------------ 7.3
    report.h2("7.3  Deviations from the proposal")

    report.p(f"""
        Eight commitments changed between the proposal and delivery, and Appendix I
        tabulates each with its reason and its evidence. Three were forced from
        outside. The proposed flight provider withdrew free access mid-project,
        which also collapsed two planned flight tools into one. The model changed to
        a free tier, which made repeated evaluation affordable and removed model
        choice as a confound between arms. Two followed from measurement: six agents became three
        because instrumentation showed most requests were spent on deterministic
        retrieval, and scenario coverage fell to
        {val(coverage['scenarios_measured'])} for the cost comparison because the
        monthly quota permits no more. One was a framework constraint: the web interface
        asks a fixed question sequence because its rerun model does not suit a streaming
        dialogue.
    """)

    report.p("""
        The remaining two are failures of delivery rather than changes of plan, and
        should be read as such. Priority queuing was promised and not built. The
        proposal's bookability target — re-query success — was replaced by groundedness,
        a weaker measure, because the stronger one needed quota the project did not
        have. Presenting either as a considered design revision would be dishonest; what
        can fairly be claimed is that both were found by measurement rather than left
        for a marker to notice.
    """)

    # ------------------------------------------------------------------ 7.4
    report.h2("7.4  Limitations")

    report.p(f"""
        The cost comparison covers {val(coverage['scenarios_measured'])} scenario,
        measured {val(coverage['repeats_per_arm'])} times per architecture. Depth is
        therefore adequate and breadth is not: differences on this trip are supported
        by intervals, and nothing establishes that they hold for a longer stay, a
        cheaper destination or a larger party. Latency excludes network time because
        retrieval is replayed. All results are specific to one model whose input and output
        prices differ by a large factor, which is what makes the tool-less arm
        expensive; a flatter price ratio would compress the differences in Section 6.2.
        Groundedness measures whether named entities were retrieved, not whether they
        were well chosen, so nothing here shows the plans are good — only that they are
        real. The gate's cost model is validated against one route, the scenarios are
        author-written, and there is no user study.
    """)

    report.p(f"""
        The test suite's coverage is narrower than its size implies: thorough on the
        pure-Python modules, absent on the protocol layer, the record-and-replay cache
        and the metric collector. Six protocol defects were found by a purpose-written
        experiment and none by the suite that passed throughout. The same audit found
        one further defect, a test block exercising a copy of the calculator rather
        than the shipped one, and that has been closed (Section 5.7). The rest are
        recorded rather than repaired, for the reason given above.
    """)

    # ------------------------------------------------------------------ 7.5
    report.h2("7.5  Professional, legal and ethical reflection")

    report.p(f"""
        The professional obligation comes first: the BCS code requires members not to
        misrepresent what their work can do [@bcs2022]. A system that prints prices
        invites the reading that those prices are bookable, and Section 6.6 shows how
        badly that reading can fail — an arm with no tool access produced
        {val(measured.groundedness('A')['prices_quoted'])} confident prices, none
        corresponding to anything. The design response is that groundedness is measured
        rather than assumed. The delivery gap is that although the repository's
        documentation states plainly that the system is a planning aid, the web
        interface itself carries no such notice, and the proposal committed to one.
        That is an unmet commitment, and it is listed in Section 8.3.
    """)

    report.p("""
        A deployed version would sit in a materially different legal position. Giving
        consumers travel information through automated processing falls within the
        transparency expectations of the AI Act, which requires that users know they
        are interacting with an AI system and that its limitations are disclosed
        [@euaiact2024]. Data protection guidance becomes relevant the moment real
        requests are stored, because a travel itinerary reveals location, dates,
        household composition and financial capacity — a rich profile from a short
        conversation [@ico2023]. This project avoids all of it by processing no personal
        data, which makes its ethical footprint small rather than the problem easy.
    """)

    report.p("""
        A last point of professional honesty concerns the cached data. Holding
        third-party fares locally is defensible for academic reproduction and would
        not be defensible as the basis of a service, because a cached fare presented
        to a user as current is a misrepresentation however it was obtained.
    """)

    # ------------------------------------------------------------------ 7.6
    report.h2("7.6  Personal reflection")

    report.p("""
        The clearest mistake was ordering. Measurement was built in the second cycle,
        after the system worked, and until then every claim about cost was a guess — one
        of which reached the project's own documentation as a result. Had the request
        counter existed on day one, the pivot this dissertation is built on would have
        been visible in week two rather than week six, and quota would have been left
        for the scenario coverage the evaluation now lacks.
        Instrumentation is not a reporting concern to add when writing up; it is what
        tells you what to build next.
    """)

    report.p(f"""
        The second mistake was treating a passing test suite as evidence about the
        system. {val(measured.test_count()['collected'])} tests pass, and they pass on
        the parts that were easy to test: pure functions with no network and no model.
        The parts carrying the research claim had no tests, and the defects were exactly
        where the tests were not. Writing the conformance audit took an afternoon and
        found six. Coverage should have been chosen by what a defect would cost, not by
        what was convenient to write.
    """)

    report.p("""
        The judgement I would defend is including arm C. Tuning the baseline before
        comparing against it cost several days and substantially weakened the result:
        the honest claim shrank from a large advantage over multi-agent retrieval to
        a decisive advantage in request count and latency with a modest one in cost.
        The temptation to compare against the naive arm and report the larger number
        was real. The narrower claim is the one that survives the first question a
        viva would ask, and a result that cannot survive that question is not worth
        having.
    """)
