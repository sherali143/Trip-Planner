"""Chapter 1: introduction."""

from __future__ import annotations

from evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("1 Introduction")
    report.h1("Introduction")

    # ------------------------------------------------------------------ 1.1
    report.h2("1.1  Background")

    report.p("""
        International tourism receipts returned to roughly 1.5 trillion US
        dollars in 2023, and arrivals recovered to close to their pre-pandemic
        level [@unwto2024]. The industry grew back. The planning experience did
        not change with it. Assembling a week away still means reconciling a
        flight search, a hotel search, an attractions list and a budget across
        several tabs, then redoing most of it when one price moves. The task is
        tedious rather than difficult, which is precisely the profile of work
        that automation should suit.
    """)

    report.p("""
        Large language models look like the obvious instrument, and for the
        conversational part of the task they are: interpreting "a week in Bangkok for
        two thousand dollars, we like markets and temples" is what they do well. The
        difficulty appears at the next step. A travel plan is not writing to be judged
        on fluency; it is a set of claims about the world. A named flight either exists
        at that price on that date or it does not. That makes travel planning a useful
        test case, because unlike summarisation the output can be checked against an
        authority.
    """)

    report.p("""
        Checked that way, current systems do poorly. On TravelPlanner, a
        benchmark of 1,225 travel-planning tasks with hard commonsense and budget
        constraints, the strongest single-agent configuration of GPT-4 completed
        0.6% of tasks end to end [@xie2024]. The failures were not stylistic.
        Plans referred to venues that do not exist, quoted prices that were never
        offered, and violated the budget they had been given. The same survey
        literature that documents hallucination in text generation generally
        [@ji2023] describes a sharper version of the problem here: a fluent
        itinerary that cannot be booked is worse than no itinerary, because it
        looks finished.
    """)

    # ------------------------------------------------------------------ 1.2
    report.h2("1.2  The specific problem")

    report.p("""
        Two structural responses to this are well established. Tool use lets a
        model fetch facts instead of recalling them [@schick2023], and
        multi-agent decomposition gives each part of a task to a component with a
        narrow remit [@wu2023]. Both are widely adopted. What is much less
        settled is how they interact, and at what price. Delegating a data
        lookup to an agent means the lookup now happens inside a reasoning loop:
        the model decides which tool to call, with what arguments, and whether to
        call it again. Every one of those decisions is a model request, and every
        request re-sends the accumulated context.
    """)

    report.p("""
        That cost is rarely reported. Framework documentation counts agents and
        tasks; papers report task success. Neither answers whether the reasoning loop
        earns its cost at the point where it is applied. Retrieving a flight price is
        not a judgement call: once the request is parsed the parameters are fixed,
        the endpoint is deterministic, and there is exactly one correct call to make.
        A recent analysis of multi-agent failures argues from taxonomy rather than
        cost that a large share arise from specification and coordination rather than
        from model capability [@cemri2025]. This project treats the matter as an
        empirical question about one system, which needs a system worth measuring, an
        instrument that counts what is spent, and a quality measure that stops
        cheapness being mistaken for merit.
    """)

    # ------------------------------------------------------------------ 1.3
    report.h2("1.3  Aim")

    report.p("""
        The aim of this project is to design, build and evaluate a multi-agent
        travel planning system that produces day-by-day itineraries grounded in
        live flight, hotel and venue data through a schema-validated Model
        Context Protocol tool layer and a typed agent-to-agent message protocol,
        and to measure what delegating data retrieval to a language model costs
        and what it contributes.
    """)

    # ------------------------------------------------------------------ 1.4
    report.h2("1.4  Objectives")

    report.p("""
        The objectives below are stated as they were finally met. Five differ from
        the proposal, and Section 7.3 tabulates every difference with its reason and
        its evidence rather than leaving a reader to compare the two documents.
    """)

    report.numbered_list([
        "Build a Model Context Protocol server exposing the project's travel tools "
        "over JSON-RPC with a declared input schema for each, and audit those "
        "schemas against their implementations.",

        "Design and implement a typed agent-to-agent protocol with agent cards, six "
        "message types, permission validation and conversation tracking, and test "
        "its conformance rather than assert it.",

        "Implement the agent layer and instrument every model request so that call "
        "counts, token counts and cost are measured rather than estimated.",

        "Build a record-and-replay layer over every outbound HTTP request, with a "
        "hard ceiling on live calls, so the evaluation reproduces without API keys "
        "and cannot exhaust a monthly quota by accident.",

        "Deliver a working demonstration through both a command-line and a web "
        "interface.",

        "Evaluate four architectures on identical inputs — a tool-less single model, "
        "a naive six-agent design, the same design after tuning, and a three-agent "
        "design with direct retrieval — measuring requests, tokens, cost, latency "
        "and the groundedness of the resulting itinerary.",

        "Evaluate the components that can be measured without API quota across the "
        "full designed scenario set: protocol conformance and the budget "
        "feasibility gate.",
    ])

    # ------------------------------------------------------------------ 1.5
    report.h2("1.5  Scope")

    coverage = measured.coverage()
    report.table(
        ["In scope", "Out of scope", "Why excluded"],
        [
            ["English free-text requests", "Multilingual input",
             "A translation failure mode that does not bear on the question"],
            ["Three live APIs behind one tool server",
             "Global distribution systems",
             "Commercial agreements are unobtainable for a student project"],
            ["Read-only search and planning", "Booking and payment",
             "Payment data would require ethical approval and PCI scope"],
            ["Scripted scenarios", "A study with human participants",
             "No ethical approval sought, so no human-subject data collected"],
            ["Cost, latency and groundedness", "Whether a traveller would enjoy it",
             "Preference satisfaction needs participants; groundedness does not"],
            [f"{val(coverage['scenarios_designed'])} designed scenarios",
             "A four-arm pass over all twenty",
             "Free-tier API quota, quantified in Section 6.1"],
        ],
        "Project scope, and the reason for each exclusion.",
        widths=[1.8, 1.8, 2.7],
    )

    report.p("""
        One exclusion limits what can be claimed and is stated
        twice. The system is a planning aid. It books nothing, and it is not
        evaluated on whether a traveller would choose its plans — only on whether
        what it names was actually retrieved. Groundedness is necessary for a usable
        plan, not sufficient.
    """)

    # ------------------------------------------------------------------ 1.6
    report.h2("1.6  Contributions")

    report.p(f"""
        Three things are offered. The first is a reproducible measurement harness:
        every model request is counted through provider callbacks, every HTTP response
        is recorded and committed, and the whole comparison replays from disk with no
        credentials, so the numbers here can be checked rather than trusted. The second
        is a comparison that includes its own fair baseline — the multi-agent arm was
        tuned before being used as a comparator, which weakened the headline result and
        is reported anyway. The third is a conformance audit of the project's own
        protocol layer, which found
        {val(measured.protocol_summary()['failed'])} defects in work this
        dissertation would otherwise have described as complete.
    """)

    # ------------------------------------------------------------------ 1.7
    report.h2("1.7  Structure of this dissertation")

    report.p("""
        Chapter 2 reviews five streams of literature and closes with a conceptual
        framework linking each documented failure mode to a design decision taken
        against it. Chapters 3 and 4 give the research approach, the evaluation design
        and the architecture, in each case with the alternatives that were rejected.
        Chapter 5 covers implementation, concentrating on the failures that shaped the
        system. Chapter 6 reports the experiments and their threats to validity,
        Chapter 7 assesses each objective against evidence, and Chapter 8 orders future
        work by how much each item would strengthen the claims made here.
    """)
