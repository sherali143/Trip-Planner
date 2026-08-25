"""Chapter 4: design."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("4 Design")
    report.h1("Design")

    # ------------------------------------------------------------------ 4.1
    report.h2("4.1  Architecture")

    report.p("""
        The system is layered by the kind of work each layer does rather than by
        the technology it uses. Layer one accepts a request. Layer two turns free
        text into a typed structure. Layer three retrieves data. Layer four
        assembles a plan. The division matters because the research question is
        about layer three: it is the only layer whose implementation differs
        between the four evaluated arms, and holding the other three constant is
        what makes the comparison mean anything.
    """)

    report.figure(
        "diagrams/architecture.png",
        "System architecture. The shipped configuration performs retrieval in "
        "ordinary Python; the JSON-RPC transport is exercised by the six-agent arms.")

    report.p("""
        The tool server is not the only route to an external API. The shipped path
        imports the tool
        functions and calls them in process, and the flight tool reaches its upstream
        endpoint without passing through the server at all. The JSON-RPC transport is
        genuinely exercised, but only by the naive six-agent arm, whose agents hold
        wrappers that spawn the server as a subprocess. Section 7.2 assesses what that
        means for the objective the server was built to satisfy.
    """)

    report.figure(
        "diagrams/sequence.png",
        "End-to-end sequence for one request in the shipped configuration, with "
        "measured phase timings.")

    report.p("""
        The sequence makes the design argument visible. Two model steps bracket a
        retrieval phase that uses no model. Both model steps have genuine work: turning
        "for two adults, leaving on the fifteenth" into structured fields, and
        arranging retrieved options into a plan whose pacing and proximity make sense.
        Between them there is nothing to decide — the parameters are fixed, and four
        calls fetch flights, hotels, attractions and restaurants.
    """)

    report.figure(
        "diagrams/dataflow.png",
        "Level-1 data flow, showing the three persisted stores that make the "
        "reported results reproducible.")

    # ------------------------------------------------------------------ 4.2
    report.h2("4.2  Module decomposition")

    stats = measured.code_stats()
    report.p(f"""
        The implementation is {val(stats['total_lines'], '{:,}')} lines of Python
        across {val(stats['total_files'])} files; Appendix E maps every module to its
        responsibility. Two boundaries in that map were placed deliberately, and both
        had been violated earlier in development. Measurement is separated from the
        code being measured, because an early version incremented a counter inside
        the arm it was measuring and produced a figure that counted tasks rather than
        requests. Evaluation code is kept out of the shipped path, because the
        distillation helpers written for the tuned arm are meaningful only as an
        experimental treatment and would have become production behaviour had they
        been placed in the tool layer.
    """)

    report.p("""
        Three further separations carry weight. The message layer is identical across
        all four arms, so it must not depend on any of them — that independence is what
        lets the comparison isolate retrieval. The tool server runs as a subprocess and
        cannot import from its caller's context, which caused the failure in Section
        5.2. And every outbound call passes through one caching chokepoint, because a
        quota guarantee any call site can bypass is not a guarantee.
    """)

    # ------------------------------------------------------------------ 4.3
    report.h2("4.3  Interface contracts")

    report.h3("4.3.1  The tool interface")

    report.p("""
        Each tool declares a name, a description and a JSON input schema, and is
        invoked over JSON-RPC with an arguments object. The contract's value is
        that a malformed call fails at the boundary with a schema error rather
        than reaching a third-party API as a well-formed request with wrong
        content. Its weakness is that the schema is a declaration and nothing in
        the protocol requires it to match the function behind it
        [@anthropic2024; @hou2025], which is the gap Section 6.4 measured.
    """)

    report.figure(
        "diagrams/mcp_lifecycle.png",
        "The six-stage tool call lifecycle. Two stages can return early: a cache "
        "hit avoids the network entirely, and the quota guard refuses rather than "
        "overspending.")

    report.p("""
        The cache position is the consequential design choice. Placing it in front
        of the network rather than inside each tool means every tool inherits both
        replay and quota protection without knowing either exists, and adding a
        tool cannot accidentally bypass them. The cost is that the cache key is
        computed from method, URL, parameters and body, so a semantically
        equivalent call with reordered parameters misses — acceptable here because
        the deterministic arm issues canonical parameters, and the reason that arm
        runs first.
    """)

    report.h3("4.3.2  The inter-agent interface")

    report.p("""
        Every inter-agent message carries a sender, a receiver, one of six types,
        a conversation identifier, a timestamp, a priority and a typed payload.
        Before delivery, the sender's agent card is consulted to confirm the
        recipient is permitted. The types follow the speech-act tradition
        [@fipa2002]: a request expects action, a response carries a result, an
        error reports a failure, and an acknowledgement confirms receipt.
    """)

    report.figure(
        "diagrams/a2a_flow.png",
        "The six messages exchanged for one trip, with the measured conformance "
        "result and the two declared behaviours that are not implemented.")

    report.p(f"""
        The contract holds in the direction that is exercised and not in the
        directions that are not. Permission validation works: an undeclared edge
        and an empty payload are both refused, and all
        {val(measured.protocol_check('A3')['observed']['permitted'])} messages the
        shipped path emits are permitted. Two declared behaviours are absent. The
        priority field is written on every message and never read, because the
        queue is first-in-first-out. Each agent card declares which senders it
        accepts, and that declaration is never consulted, because validation
        examines only the sender's outbound list. Both are reported in Section 6.4
        and neither was known before the conformance audit was written.
    """)

    # ------------------------------------------------------------------ 4.4
    report.h2("4.4  Key design decisions")

    report.h3("4.4.1  Where a language model is used, and where it is not")

    report.p("""
        The governing decision is a test applied to each step: does this step
        require a judgement that cannot be expressed as code? Interpreting a
        free-text request does, because the mapping from phrasing to fields is
        open-ended. Composing a day-by-day plan does, because there is no single
        correct ordering and the trade-offs between proximity, pacing and budget
        are matters of taste. Fetching a fare for a known route on a known date
        does not. The three-agent design follows directly from applying that test
        consistently, and the comparison in Chapter 6 is a test of whether the
        test was right.
    """)

    report.figure(
        "diagrams/four_arms.png",
        "The four evaluated configurations. Only the retrieval mechanism differs; "
        "the request, the APIs and the message layer are held constant.")

    report.h3("4.4.2  Budget allocation derived from cost, not from a fixed split")

    report.p("""
        The system must decide how much of a stated budget goes to flights,
        accommodation, food and activities. The original implementation used one
        fixed percentage split for every trip, which is wrong in a way that
        compounds: airfare is incurred per person and scales with distance, while
        accommodation is incurred per night and is shared between travellers. A
        split that suits a solo short-haul trip therefore misallocates badly for a
        family travelling far. The replacement derives the split from what the
        components of that specific trip cost, and honours an explicit split when
        the traveller gives one, because a user who says how to divide their money
        has expressed a preference and not made an error.
    """)

    report.h3("4.4.3  A feasibility floor rather than a rejection rule")

    report.p("""
        A budget below what a trip can possibly cost should be refused, because
        planning it produces a fiction. The first implementation refused on a
        fixed formula that ignored the destination entirely, judging a seven
        hundred dollar trip to Bangkok and a seven hundred dollar trip to London
        by the same threshold and accepting both. The replacement estimates the
        cost of the specific trip at three standards — minimum, comfortable and
        luxury — from destination price tier, flight distance band, nights, party
        size and room sharing, then refuses only below the minimum. Above it, a
        tight budget produces a warning and proceeds, because tightness is a
        legitimate choice and only impossibility is not. Section 6.5 reports how
        well this works, including the case it gets wrong and why.
    """)

    report.h3("4.4.4  Validation of output structure in code, not in the prompt")

    report.p("""
        A five-night trip needs five days in its itinerary. The original approach
        instructed the model in capital letters to write every day, which fails
        intermittently and silently. The current approach counts the day headings
        in the generated text, compares against the extracted duration, and
        appends an explicit notice when days are missing. A check that can fail
        loudly is worth more than an instruction that can be ignored quietly, and
        this is the smallest example of the chapter's general principle.
    """)

    # ------------------------------------------------------------------ 4.5
    report.h2("4.5  Technology choices, with their costs")

    report.table(
        ["Decision", "Selected (rejected)", "What it bought", "What it cost"],
        [
            ["Agent framework", "CrewAI (AutoGen, MetaGPT, LangGraph)",
             "Roles map onto travel sub-tasks; tool binding is a few lines",
             "Its reasoning loop is not directly controllable, so request counts vary "
             "between runs and must be measured, never assumed"],
            ["Tool protocol", "MCP over JSON-RPC (vendor function-calling, bespoke "
             "REST)",
             "Vendor-neutral, declared schemas, one server for every tool",
             "A subprocess boundary, a serialisation limit on large payloads, and no "
             "guarantee a schema matches its implementation"],
            ["Inter-agent messaging", "Typed envelope with agent cards (free text, "
             "framework threads)",
             "Permission validation and a full audit trail per conversation",
             "In the shipped path it records rather than dispatches, so part of the "
             "library is unexercised"],
            ["Model",
             f"{measured.model_name()} (the proposal's GPT-4o split, Claude)",
             "A free tier that made repeated evaluation affordable, and callbacks "
             "exposing per-request usage",
             "Output tokens dominate its cost, so cost tracks verbosity; results are "
             "specific to this model; and a per-minute rate limit forced the harness "
             "to pace itself"],
            ["Flights", "fly-scraper (Kiwi.com as proposed, Amadeus)",
             "A free tier still available when Kiwi withdrew theirs",
             "Thirty requests a month, an asynchronous two-phase search, and "
             "parameters ignored rather than rejected"],
            ["Hotels", "Booking.com (Hotels.com, Expedia)",
             "One provider covering search, review scores and nearby venues",
             "Fifty requests a month; enrichment costs two extra requests per hotel, "
             "so it is disabled by default"],
            ["Venue search", "Serper.dev (Bing, Brave, scraping)",
             "A quota generous enough never to constrain the evaluation",
             "Results are web snippets, so venue data is less structured than flight "
             "or hotel data"],
            ["Interface", "Streamlit and a command-line client (Gradio, Flask, React)",
             "Fastest route to a demonstrable artefact",
             "Its rerun model does not suit a streaming conversation, so the web "
             "interface asks a fixed question sequence"],
        ],
        "Technology decisions. The final column is the one that matters for "
        "Chapter 7: every choice constrained something later.",
        widths=[1.05, 1.5, 1.6, 2.35],
        font_pt=8.5,
    )

    report.p("""
        The model choice altered the project's economics rather than merely its
        provider. The proposal specified a two-model split — expensive for dialogue
        and synthesis, cheap for extraction and search — with a target under one
        dollar per itinerary. A free tier removed the reason for that complexity, and
        with a single model the arms differ only in architecture, which makes the
        comparison cleaner than the proposal's design would have been.
    """)

    report.p("""
        One consequence of the framework choice governs the difference between the
        naive and tuned arms, so it is worth naming here and quantifying in Section
        6.3. Every tool bound to an agent contributes its name, description and JSON
        schema to that agent's prompt, and the prompt is re-sent on every iteration of
        its reasoning loop. In the naive configuration the hotel agent holds eight
        tools, so eight schemas are re-serialised on each of up to ten iterations. The
        framework makes tool binding trivial, which is exactly why the cost of binding
        many tools stays invisible until it is measured.
    """)
