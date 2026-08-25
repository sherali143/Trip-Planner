"""Chapter 8: conclusion."""

from __future__ import annotations

from evaluation import measured
from report.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("8 Conclusion")
    report.h1("Conclusion")

    coverage = measured.coverage()
    d_vs_c = measured.improvement("D_vs_C")
    c_vs_b = measured.improvement("C_vs_B")
    control = measured.groundedness("A")
    summary = measured.protocol_summary()
    anchor = measured.gate_external_validity()

    # ------------------------------------------------------------------ 8.1
    report.h2("8.1  What was found")

    report.p(f"""
        This project asked what it costs to delegate data retrieval to a language model
        in a system that already has a schema-validated tool layer and a typed
        inter-agent protocol. On the one scenario for which all four architectures are
        recorded, removing the model from retrieval reduced requests by
        {val(d_vs_c['llm_calls_pct'], '{:.1f}')}% and wall-clock time by
        {val(d_vs_c['latency_pct'], '{:.1f}')}% against a tuned six-agent baseline,
        while cost fell only {val(d_vs_c['cost_pct'], '{:.1f}')}% and groundedness was
        unchanged. The answer is therefore yes, with a qualification that matters: the
        saving is in requests and latency, not primarily in money.
    """)

    report.p(f"""
        The more useful finding narrowed the claim. Tuning the six-agent arm, without
        changing its architecture, data or model, removed
        {val(c_vs_b['tokens_pct'], '{:.1f}')}% of its token spend. Most of what would
        have been reported as the cost of multi-agent architecture was the cost of
        binding eight tools to an agent and letting it iterate fifteen times. Any
        comparison of this kind that does not tune its baseline first is measuring
        implementation quality and calling it architecture.
    """)

    report.p(f"""
        Tool access, by contrast, was decisive. The arm with no tools quoted
        {val(control['prices_quoted'])} prices and matched
        {val(control['prices_grounded'])} to anything retrieved, reproducing under
        measurement the failure the benchmark literature reports [@xie2024]. The gap
        between a plausible itinerary and a usable one is entirely the retrieval layer;
        what is negotiable is whether a language model should operate it.
    """)

    report.p(f"""
        Measuring the artefact against its own design then found
        {val(summary['total_checks'] - summary['passed'])} defects in it: declared
        message priorities never honoured, inbound permissions never enforced, a
        receive path that destroys misaddressed messages,
        {val(len(measured.mcp_schema_stats()['defective_tools']))} tool schemas that
        disagree with their implementations, and a cost model whose flight anchor sits
        {val(abs(anchor['minimum_anchor_error_pct']), '{:.0f}')}% below the cheapest
        fare its own API returned — which is why the gate accepts one budget it should
        refuse. None was found by a passing test suite.
    """)

    # ------------------------------------------------------------------ 8.2
    report.h2("8.2  Contribution")

    report.p("""
        The contribution is threefold and deliberately modest. First, a working
        protocol-mediated travel planner whose every reported number regenerates
        from committed data, so the results can be checked rather than believed.
        Second, a comparison that includes its own fair baseline and reports the
        weaker conclusion that followed. Third, a demonstration that conformance to
        a tool protocol is a property to be tested rather than an outcome of adopting
        one, together with an executable method for testing it that costs nothing to
        run.
    """)

    # ------------------------------------------------------------------ 8.3
    report.h2("8.3  Future work, ordered by how much each would strengthen the claims")

    report.numbered_list([
        "Repeat runs, on a model that can execute every arm. Five per arm would "
        "give a mean, a standard deviation and a confidence interval. This was "
        "attempted and could not be completed: the model the results were measured "
        "on has been withdrawn, and its replacement refuses the prompt shape the "
        "agent framework's reasoning loop produces (Section 6.7). It now needs "
        "either a framework version that reshapes those requests or a provider "
        "still serving a compatible model — and all four arms must then be re-run "
        "together, because a mean pooled across two models means nothing.",

        f"Record the remaining "
        f"{val(coverage['scenarios_designed'] - coverage['scenarios_measured'])} "
        f"scenarios. Roughly four requests each against eighty a month means two "
        f"monthly cycles, or a paid tier at trivial cost. Recordings accumulate, so "
        f"this extends coverage without re-running what exists, turning a "
        f"single-case measurement into a comparison across trip lengths and party "
        f"sizes.",

        "Recalibrate the cost model against real fares on several routes per "
        "distance band. Correcting the one measured anchor alone would be fitting a "
        "model to its only validation point. Once recalibrated, the gate should be "
        "re-evaluated on the same twenty scenarios to see whether the missed case is "
        "caught and whether any correct refusal is lost.",

        "Repair the six conformance defects and re-run the audit. Generating each "
        "tool's schema from its implementation signature, rather than declaring it "
        "separately, would make that class of defect unrepresentable rather than "
        "merely fixed.",

        "Add the interface notice the proposal committed to: that the system is a "
        "planning aid, that prices were retrieved at a point in time, and that "
        "nothing shown is bookable.",

        "Build and measure a hybrid arm. A model adds cost where retrieval is "
        "deterministic, but retrieval is not always deterministic — when a first "
        "search returns nothing, choosing between wider dates, a relaxed budget and "
        "a nearby airport is a judgement. An arm that invokes an agent only on that "
        "path would test whether the boundary drawn in Section 4.4 is in the right "
        "place. It is the most interesting item here and deliberately not the first, "
        "because it extends the work rather than strengthening what is claimed.",

        "Validate against human judgement. Groundedness establishes that a plan is "
        "real, not that it is good. Travellers ranking itineraries from the four "
        "arms would test whether the measured quality equivalence holds for the "
        "people the plans are for. It needs ethical approval and is the largest item "
        "here.",
    ])

    # ------------------------------------------------------------------ 8.4
    report.h2("8.4  Closing")

    report.p(f"""
        The result this project set out to demonstrate turned out to be smaller than
        expected, and the results it did not set out to find turned out to be the
        useful ones. A fair baseline removed most of the advantage the pivot was
        supposed to show. An afternoon's worth of conformance checking found
        {val(summary['total_checks'] - summary['passed'])} defects in a system whose
        {val(measured.test_count()['collected'])} passing tests had said nothing about
        any of them. Both outcomes came from the same decision, which was to measure
        the artefact rather than describe it, and to report what the measurement said.
    """)
