"""Chapter 5: implementation."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("5 Implementation")
    report.h1("Implementation")

    report.p("""
        This chapter is organised around what went wrong, because that is where the
        engineering was. Six failures are described in detail. Four were silent: the
        system reported success, produced plausible output, and was wrong. Silent
        failures are the interesting category, because the work is not in fixing
        them but in noticing that anything needs fixing.
    """)

    # ------------------------------------------------------------------ 5.1
    report.h2("5.1  Build order and environment")

    stats = measured.code_stats()
    git = measured.git_stats()
    report.p(f"""
        The system is {val(stats['total_lines'], '{:,}')} lines of Python across
        {val(stats['total_files'])} files, developed over {val(git['commits'])}
        commits, and Appendix E breaks it down by area. It was built in dependency
        order: the tool server first, because nothing can be retrieved without it;
        then the message layer, the agents and the interfaces; and last, later than
        it should have been, the measurement infrastructure. That ordering is the
        root of the first failure below, and Section 7.6 argues it should have been
        reversed.
    """)

    # ------------------------------------------------------------------ 5.2
    report.h2("5.2  The tool server failed silently, and the system hid it")

    report.p("""
        The first working end-to-end run produced a complete, confident,
        well-formatted itinerary with named hotels and specific fares. None of it
        was real. Every tool call was failing, and the system reported nothing
        wrong.
    """)

    report.p("""
        Every invocation returned "Connection lost", and the cause was mundane. The
        tool server runs as a subprocess launched by path, so the project root is
        absent from the module search path and the first first-party import raises.
        The server died during startup, the client saw a closed pipe and reported a
        transport error. The fix is three lines putting the project root on the
        search path.
    """)

    report.p("""
        The fix is trivial and the lesson is not. The failure was invisible from
        outside because of how the agents behaved on a tool error: they proceeded,
        writing the itinerary from model knowledge instead. That is what the
        literature reports [@xie2024], reproduced accidentally inside a system built
        to prevent it and undetectable from the output. A plausible itinerary is not
        evidence that retrieval worked, which is why groundedness scoring exists —
        it is the only check that would have caught this, and it was written because
        this happened.
    """)

    # ------------------------------------------------------------------ 5.3
    report.h2("5.3  Two bugs in one endpoint, both returning HTTP 200")

    evidence = measured.flight_api_evidence()

    report.p(f"""
        Flight search failed in two independent ways, and both returned a success
        status. The recorded response cache preserves all of it, so the sequence can
        be verified rather than asserted.
    """)

    report.h3("5.3.1  Date parameters that are ignored rather than rejected")

    report.p(f"""
        The endpoint documents its origin, destination and dates as camelCase. The
        first implementation sent snake_case dates. The API accepted the request,
        returned HTTP 200, ignored the dates it did not recognise and searched a
        default window. Nothing reported an error; the itineraries simply carried
        dates nobody asked for.
    """)

    report.p(f"""
        Appendix F tabulates the recordings on either side of the fix: the
        {val(evidence['broken_recordings'])} made with snake_case parameters return
        {val(evidence['broken_max_itineraries'])} itineraries, the corrected one
        {val(evidence['fixed_itineraries'])}. This is a class of API defect worth
        naming. A parameter that is rejected costs minutes; a parameter that is
        silently discarded can cost weeks, because every observable signal says the
        call succeeded.
    """)

    report.h3("5.3.2  A search endpoint that does not return results")

    report.p(f"""
        Correcting the parameters was not sufficient. The endpoint is asynchronous:
        the search request starts a search and returns a session identifier with a
        status of "{evidence['fixed_status']}", and results must be collected from a
        second endpoint using that identifier. The first implementation treated the
        initial response as final, so flight search returned nothing on every single
        call.
    """)

    report.p(f"""
        Appendix F compares the two responses: the search returns
        {val(evidence['fixed_itineraries'])} itineraries, the poll that follows it
        {val(evidence['poll_itineraries'])}. Reading only the first therefore
        discarded most of the available fares even once the parameters were right. A
        third defect compounded the diagnosis. The provider's console lists these
        paths in the singular while only the plural form resolves, so an exploratory
        call made from the documentation returns 404 and suggests the endpoint does
        not exist.
    """)

    report.p("""
        A coincidence made this expensive. The credential had exhausted its monthly
        allowance, so calls were rejected before reaching the parsing code and the
        empty result looked like a quota problem rather than a parsing one. Two
        independent faults with one observable symptom is the worst case for
        diagnosis. The cache now stores only successful responses for that reason: a
        quota rejection must never replay as data.
    """)

    # ------------------------------------------------------------------ 5.4
    report.h2("5.4  The headline metric was not being measured")

    report.p("""
        The comparison's central claim is about model requests, and for a period the
        harness fabricated that number. The code incremented a counter by a constant
        after each phase, one line commenting that the figure was simulated. It
        counted tasks, not requests. Since the criticism of the multi-agent arm is
        precisely that its reasoning loops issue many requests per task, the
        measurement was blind to the effect it existed to detect.
    """)

    report.p(f"""
        The replacement registers callbacks with the model client, which every
        completion passes through, recording model, prompt and completion tokens,
        cost and latency per request. The difference was not marginal: the naive
        six-agent arm, credited with a request per task, actually issues
        {val(measured.arm_metric('B', 'avg_llm_calls'))} for one trip. Two claims in
        this project's own documentation — a request count and a cost per itinerary
        — were wrong by roughly a factor of four once real counting began.
    """)

    report.p("""
        Instrumenting correctly exposed a second-order problem. The client
        dispatches callbacks off the calling thread, so reading the counters
        immediately after a run undercounts: an early check saw three completions
        and two callbacks. The session now drains before reporting, blocking until
        no event has arrived for a quiet period. That matters most for the tuned
        arm, whose specialists run concurrently, and it stops a late callback being
        attributed to the next scenario.
    """)

    report.p(f"""
        The recorded data confirms the concurrency works as designed. The tuned
        arm's summed model time is {val(measured.token_split('C')['llm_time_s'],
        '{:.1f}')} seconds against a wall-clock {val(measured.arm_metric('C',
        'avg_latency'), '{:.1f}')}. Summed request time exceeding elapsed time is
        only possible if requests overlapped — direct evidence of the thread pool
        doing its job, a claim the proposal made and could not previously support.
    """)

    # ------------------------------------------------------------------ 5.5
    report.h2("5.5  Quota as a first-class engineering constraint")

    cache = measured.api_cache_stats()
    report.p(f"""
        The flight and hotel APIs allow thirty and fifty requests a month, and one
        careless run can spend a month's allowance in under a minute with no way to
        buy it back. Care is exactly what fails at two in the morning, so the
        constraint had to become a property of the code.
    """)

    report.p(f"""
        Three mechanisms were built. Every outbound request passes through one cache
        with three modes: replay never touches the network, record calls live only
        on a miss, live refreshes deliberately. A ceiling on live calls raises
        rather than proceeding, and the runner checkpoints after every run. The
        cache holds {val(cache['entries'])} responses, and the published comparison
        replays from them with no credentials.
    """)

    report.p("""
        One retrieval decision came directly from quota arithmetic. Hotel search
        originally enriched each result with a review breakdown and a nearby-venues
        lookup, at two extra requests per hotel — twenty for a ten-hotel result
        against a fifty-request allowance — and none of it reached the itinerary,
        because the assembly step never read those fields. Enrichment is now off by
        default behind an environment variable: the clearest case here of a feature
        whose cost was invisible until counted.
    """)

    report.p("""
        A related decision protects the credential rather than the quota. The model
        is called over a URL carrying the key as a query parameter, and the HTTP
        client logs every request line at information level, which the agent
        framework enables. A normal run therefore printed a live API key into any
        terminal, screenshot or log it touched. Raising the level of the third-party
        loggers fixes it without altering the project's own logging.
    """)

    # ------------------------------------------------------------------ 5.6
    report.h2("5.6  Two smaller defects that changed how things are checked")

    report.p("""
        Two defects neither the suite nor a reader would have caught, set out in
        full in Appendix O. A sign error wrote a negative duration into the results
        file, and nothing objected to a value that cannot occur. A closure in the
        figure generator captured a loop variable rather than its value, so a chart
        labelled a request count in dollars: nothing failed, the chart was simply
        false.
    """)

    report.p("""
        Both lessons were acted on together, and both are about checking rather
        than coding. Values that cannot occur are now asserted rather than trusted.
        Figure layout is measured rather than estimated — text sized by the
        renderer itself, boxes grown to fit it, and a validation pass that raises
        on any overlap or oversized text. That validator caught a box outside the
        canvas on its first run, which the previous character-count estimate would
        have exported without complaint. Figures are code, and code that produces a
        document can be wrong like any other.
    """)

    # ------------------------------------------------------------------ 5.7
    report.h2("5.7  Testing, and an honest account of what it covers")

    tests = measured.test_count()
    report.p(f"""
        The suite contains {val(tests['collected'])} passing tests. What they cover
        is narrower than that number suggests, which bears on the weight it can
        carry as evidence.
    """)

    report.p("""
        Appendix H tabulates coverage by area. The budget allocation, cost
        estimation and validation modules are tested thoroughly, because they are
        pure functions needing no network and no model. The message layer, the tool
        server, the record-and-replay cache and the metric collector have no unit
        tests at all, and the four arms have none either, because each run costs
        model quota. Coverage followed what was cheap to test rather than what a
        defect would cost, and Section 6.4 reports where the defects turned out to
        be.
    """)

    report.p("""
        One case shows how a passing suite can conceal the very defect it appears to
        cover. The calculator tool is the only place here where text produced by a
        model is evaluated as code. A block of tests verified that a syntax-tree
        evaluator rejects malicious input — and that evaluator was defined inside
        the test file, not in the tool the agents could call. Appendix O sets out
        what was reachable, and the fix. It was fixed rather than recorded, because
        the remedy is confined and verifiable, and the measurements in Chapter 6
        predate it and are unaffected.
    """)
