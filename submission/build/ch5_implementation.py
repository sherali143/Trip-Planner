"""Chapter 5: implementation."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("5 Implementation")
    report.h1("Implementation")

    report.p("""
        This chapter is organised around what went wrong, because that is where
        the engineering was. Six failures are described in detail. Four were
        silent: the system reported success, produced plausible output, and was
        wrong. Silent failures are the interesting category, because the work is
        not in fixing them but in noticing that anything needs fixing.
    """)

    # ------------------------------------------------------------------ 5.1
    report.h2("5.1  Build order and environment")

    stats = measured.code_stats()
    git = measured.git_stats()
    report.p(f"""
        The system is {val(stats['total_lines'], '{:,}')} lines of Python across
        {val(stats['total_files'])} files, developed over {val(git['commits'])}
        commits, and Appendix E breaks it down by area. It was built in the order the
        layers depend on each other: the tool server first, because nothing can be
        retrieved without it; then the message layer, the agents and the interfaces;
        and last, later than it should have been, the measurement infrastructure.
        That ordering is the root of the first failure below, and Section 7.6 argues
        it should have been reversed.
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
        The symptom was a message from the client wrapper: every invocation returned
        "Connection lost". The cause was mundane. The tool server runs as a subprocess
        launched by path, so the project root is not on the module search path when the
        interpreter starts it, and the first import from the project's own package
        raises. The server died during startup, the client saw a closed pipe, and
        reported a transport error. The fix is three lines inserting the project root
        into the search path before any first-party import.
    """)

    report.p("""
        The fix is trivial and the lesson is not. The failure was invisible from
        outside because of how the agents behaved when a tool returned an error: they
        proceeded, and wrote the itinerary from model knowledge instead. This is
        precisely what the literature reports [@xie2024], reproduced accidentally
        inside a system built to prevent it, and undetectable by inspecting the output.
        A plausible itinerary is not evidence that retrieval worked, which is why
        groundedness scoring exists at all — it is the only check that would have
        caught this, and it was written because this happened.
    """)

    # ------------------------------------------------------------------ 5.3
    report.h2("5.3  Two bugs in one endpoint, both returning HTTP 200")

    evidence = measured.flight_api_evidence()

    report.p(f"""
        Flight search failed in two independent ways, and both returned a success
        status. The recorded response cache preserves all of it, so the sequence
        can be verified rather than asserted.
    """)

    report.h3("5.3.1  Date parameters that are ignored rather than rejected")

    report.p(f"""
        The endpoint documents its origin and destination as camelCase and its
        dates likewise. The first implementation sent snake_case date parameters.
        The API accepted the request, returned HTTP 200, ignored the dates it did
        not recognise, and searched a default window instead. Nothing anywhere
        reported an error; the itineraries simply carried dates the traveller had
        not asked for.
    """)

    report.p(f"""
        The cache holds {val(evidence['broken_recordings'])} recordings made with
        the snake_case parameters. Both are small —
        {' and '.join(val(b) for b in evidence['broken_bytes'])} bytes — and both
        contain {val(evidence['broken_max_itineraries'])} itineraries. The
        recording made after the parameters were corrected is
        {val(evidence['fixed_bytes'], '{:,}')} bytes and contains
        {val(evidence['fixed_itineraries'])}. This is a class of API defect worth
        naming: a parameter that is rejected costs minutes, and a parameter that
        is silently discarded can cost weeks, because every observable signal says
        the call succeeded.
    """)

    report.h3("5.3.2  A search endpoint that does not return results")

    report.p(f"""
        Correcting the parameters was not sufficient. The endpoint is
        asynchronous: the search request starts a search and returns a session
        identifier with a status of "{evidence['fixed_status']}", and results must
        be collected from a second endpoint using that identifier. The first
        implementation treated the initial response as final, so flight search
        returned nothing on every single call.
    """)

    report.p(f"""
        The evidence is again in the cache. The corrected search response carries
        {val(evidence['fixed_itineraries'])} itineraries and a status of
        "{evidence['fixed_status']}"; the poll that follows it returns
        {val(evidence['poll_bytes'], '{:,}')} bytes containing
        {val(evidence['poll_itineraries'])} itineraries with a status of
        "{evidence['poll_status']}". Reading only the first response therefore
        discarded most of the available fares even once the parameters were right.
        A third defect compounded the diagnosis: the provider's console lists these
        paths in the singular while only the plural form resolves, so an
        exploratory call made from the documentation returns 404 and suggests the
        endpoint does not exist.
    """)

    report.p("""
        What made this expensive was a coincidence. For a long period the credential
        had exhausted its monthly allowance, so the call was rejected before reaching
        the parsing code and the empty result looked like a quota problem rather than a
        parsing one. Two independent faults with the same observable symptom is the
        worst case for diagnosis. The cache now stores only successful responses for
        exactly this reason: a quota rejection must never be replayed as though it were
        data.
    """)

    # ------------------------------------------------------------------ 5.4
    report.h2("5.4  The headline metric was not being measured")

    report.p("""
        The comparison's central claim is about model requests, and for a period
        that number was fabricated by the harness. The code incremented a counter
        by a constant after each phase; one line carried the comment that the
        figure was simulated. It counted tasks, not requests. Since the whole point
        of the criticism levelled at the multi-agent arm is that its reasoning
        loops issue many requests per task, the measurement was blind to the effect
        it existed to detect.
    """)

    report.p(f"""
        The replacement registers callbacks with the model client, which every
        completion passes through, and records model, prompt tokens, completion
        tokens, cost and latency per request. The difference was not marginal. The
        naive six-agent arm, credited with a request per task, actually issues
        {val(measured.arm_metric('B', 'avg_llm_calls'))} for a single trip. Two
        earlier claims in this project's own documentation — a request count and a
        cost per itinerary — were wrong by roughly a factor of four once real
        counting began.
    """)

    report.p("""
        Instrumenting correctly then exposed a second-order problem. The client
        dispatches its callbacks off the calling thread, so reading the counters
        immediately after a run undercounts: an early check observed three completions
        and only two callbacks. The session now drains before reporting, blocking until
        no new event has arrived for a quiet period. This matters most for the tuned arm,
        whose three specialists run concurrently, and draining before releasing a session
        also stops a late callback being attributed to the next scenario.
    """)

    report.p(f"""
        A detail from the recorded data confirms the concurrency works as designed.
        The tuned arm's summed model time is
        {val(measured.token_split('C')['llm_time_s'], '{:.1f}')} seconds while
        its wall-clock time is
        {val(measured.arm_metric('C', 'avg_latency'), '{:.1f}')} seconds. Summed
        request time exceeding elapsed time is only possible if requests overlapped,
        which is direct evidence of the thread pool doing its job — a claim the
        proposal made and could not previously support.
    """)

    # ------------------------------------------------------------------ 5.5
    report.h2("5.5  Quota as a first-class engineering constraint")

    cache = measured.api_cache_stats()
    report.p(f"""
        The flight and hotel APIs allow thirty and fifty requests a month. A single
        careless run can consume a month's allowance in under a minute, and it
        cannot be bought back. This is not a nuisance to be handled with care; care
        is exactly what fails at two in the morning. It had to become a property of
        the code.
    """)

    report.p(f"""
        Three mechanisms were built. Every outbound request passes through one cache
        with three modes — replay never touches the network, record calls live only on
        a miss, live refreshes deliberately. A ceiling on live calls raises rather than
        proceeding. And the runner checkpoints after every run. The cache holds
        {val(cache['entries'])} recorded responses, and the published comparison
        replays from them with no credentials at all.
    """)

    report.p("""
        One design decision in the retrieval layer came directly from quota
        arithmetic. Hotel search originally enriched each result with a review
        breakdown and a nearby-venues lookup, at two additional requests per hotel.
        For a ten-hotel result that is twenty requests against a fifty-request
        monthly allowance, and none of the enrichment reached the itinerary,
        because the assembly step never used those fields. Enrichment is now off by
        default behind an environment variable. This is the clearest case in the
        project of a feature whose cost was invisible until the cost was counted.
    """)

    report.p("""
        A related decision protects the credential rather than the quota. The model is
        called over a URL carrying the key as a query parameter, and the HTTP client
        logs every request line at information level, which the agent framework
        enables. A normal run therefore printed a live API key into any terminal,
        screenshot or log it touched. Raising the level of the third-party loggers
        responsible fixes it without altering the project's own logging.
    """)

    # ------------------------------------------------------------------ 5.6
    report.h2("5.6  Two smaller defects that changed how things are checked")

    report.p("""
        The first was a sign error with an impossible output. The direct-execution arm
        reports per-phase timings, and the extraction phase subtracted the run's start
        time from a value that was already an elapsed duration, writing a large
        negative number into the results file. A negative duration cannot occur, and
        nothing in the harness objected. Values that cannot occur should be asserted
        rather than trusted.
    """)

    report.p("""
        The second was in the figure generator and produced a wrong chart that looked
        right. Three panels each built a tick formatter inside a loop, and each
        closure captured the loop variable rather than its value at definition, so
        every panel rendered with whichever formatter the loop finished on — the
        currency one. The request-count axis was labelled in dollars. Nothing failed;
        the chart was simply false. Figures are code, and code that produces a
        document can be wrong like any other.
    """)

    report.p("""
        Both lessons were acted on together. Figure layout is now mechanical rather
        than estimated: text is measured with the renderer at its actual size, boxes
        grow to fit their measured contents, a header band is reserved so a title
        cannot collide with content, connectors route orthogonally, labels carry
        opaque backgrounds so no line strikes through them, and a validation pass
        raises on any overlap, any content outside the frame, and any text larger than
        the box around it. That validator caught a box positioned outside the canvas
        on its first run — something the previous character-count estimate would have
        exported without complaint.
    """)

    # ------------------------------------------------------------------ 5.7
    report.h2("5.7  Testing, and an honest account of what it covers")

    tests = measured.test_count()
    report.p(f"""
        The suite contains {val(tests['collected'])} tests and they pass. What they
        cover is narrower than that number suggests, which bears on how much weight
        it can carry as evidence.
    """)

    report.p("""
        Appendix H tabulates coverage by area. The pattern is that the budget
        allocation, cost estimation and validation modules are tested thoroughly
        because they are pure functions needing no network and no model, while the
        message layer, the tool server, the record-and-replay cache and the metric
        collector have no unit tests at all. The four arms have none either, because
        each run costs model quota. Coverage followed what was cheap to test rather
        than what a defect would cost, and Section 6.4 reports where the defects
        turned out to be.
    """)

    report.p("""
        One case is worth setting out in full, because it shows how a passing suite
        can conceal exactly the defect it appears to cover. The calculator tool is
        the only place in this system where text produced by a model is evaluated
        as code. A block of tests verified that a syntax-tree evaluator rejects
        malicious input — and that evaluator was defined inside the test file. The
        tool the agents could actually call filtered the input against a permitted
        character set and then called the interpreter's own expression evaluator.
    """)

    report.p("""
        The character filter blocks name lookups, so code injection was never
        reachable — genuinely the hard part. What it cannot block is resource
        exhaustion: 9**9**9 is eight characters, passes any character allowlist, and
        occupies the interpreter indefinitely while allocating memory until the
        process dies. The two implementations had also drifted, the test copy having
        omitted unary plus, so a test asserted a rejection that production did not
        make.
    """)

    report.p("""
        This one was fixed rather than recorded, because the remedy is confined and
        verifiable. The evaluator now lives in one module, the tool delegates to it,
        exponentiation is bounded before evaluation rather than after, and the tests
        import the shipped code — one of them asserting that the server's tool is
        that code and not a copy, so the two cannot drift again. The measurements in
        Chapter 6 predate the change and are unaffected: the fix alters which
        expressions are refused, not the value returned for any well-formed one.
    """)
