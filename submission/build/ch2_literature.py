"""Chapter 2: literature review."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("2 Literature review")
    report.h1("Literature Review")

    report.p("""
        Five bodies of work bear on the design of this system: how a single model
        uses tools, how multiple models are orchestrated, how tool and inter-agent
        interfaces are specified, how travel planning has been evaluated as a
        task, and how groundedness is measured. Each is examined for what it
        establishes and where it stops, because the gaps are what the design has
        to answer. The chapter closes by drawing them into the framework that
        governed the build.
    """)

    # ------------------------------------------------------------------ 2.1
    report.h2("2.1  Tool use by a single model, and where it stops scaling")

    report.p("""
        The founding result is that a model can learn when to call an external
        function. Toolformer showed this could be self-supervised: the model
        annotates its own training text with API calls and keeps the ones that
        reduce perplexity [@schick2023]. ReAct made the control flow explicit,
        interleaving a reasoning trace with actions so that observations feed back
        into the next decision [@yao2023], and Reflexion added a self-critique
        step that lets an agent revise after a failure [@shinn2023]. Together
        these establish the mechanism this project depends on: a model can be
        given a tool and will use it.
    """)

    report.p("""
        The limit is structural rather than a matter of model quality. Each ReAct
        iteration appends its observation to the transcript and re-sends the whole
        thing, so context grows monotonically with the number of tool calls. The
        economic consequence is rarely stated in these papers, whose evaluations report
        task success rather than request counts: a loop that iterates eight times costs
        eight requests, each larger than the last. The behavioural consequence is that
        models attend unevenly across a long context, recovering material in the middle
        least reliably [@liu2024], so an instruction issued at the start of a planning
        task competes with API output accumulated since, and loses.
    """)

    report.p("""
        Reflexion is instructive about what these papers do not settle. Its
        self-critique improves outcomes where success is ambiguous enough for the
        model to reason about. Retrieving a flight price is not such a task: there is
        one correct call, and a critique step adds a request without adding
        information. This literature establishes that a model can decide to call a
        tool; it does not establish that it should be the thing deciding when the
        decision is already determined. That distinction is the hypothesis this
        project set out to measure.
    """)

    # ------------------------------------------------------------------ 2.2
    report.h2("2.2  Multi-agent orchestration: four positions on the same trade-off")

    report.p("""
        Multi-agent frameworks divide a task among specialised components, and
        differ mainly in how tightly they constrain what those components say to
        each other. AutoGen sits at the permissive end, with agents conversing in
        natural language [@wu2023]; the flexibility is real, and so is the cost,
        because an unconstrained channel can carry a malformed or misinterpreted
        message as easily as a correct one. MetaGPT takes the opposite position,
        assigning each role a standard operating procedure and passing structured
        documents between stages [@hong2024], which reduces ambiguity at the price
        of a workflow that must be specified in advance. GPTSwarm reframes the
        question entirely, treating the agent topology as a graph to be optimised
        rather than designed [@zhuge2024] — elegant, and dependent on a reward
        signal that a travel plan does not obviously supply. CrewAI occupies the
        pragmatic middle with roles, goals and tools [@crewai2024].
    """)

    report.p("""
        Read together, these four are positions on one trade-off: expressiveness against
        verifiability. The surveys of the area map the design space thoroughly
        [@wang2024; @xi2023] but are organised by capability rather than cost,
        documenting what architectures can do and not what they spend. That framing has
        been challenged directly: an analysis of 200 traces across seven frameworks
        attributes most failures to specification and inter-agent misalignment rather
        than to model capability [@cemri2025], which reverses the usual inference.
        Adding agents adds coordination surface, and coordination surface is where these
        systems break — the strongest available argument for the position this project
        tests, that a component should be added only where judgement is required.
    """)

    report.p("""
        CrewAI was selected on practical rather than theoretical grounds, and Section
        4.5 records what that cost. The relevant point here is that none of these four
        frameworks publishes the measurement a designer needs: what one agent, on one
        task, adds to the request count.
    """)

    # ------------------------------------------------------------------ 2.3
    report.h2("2.3  Interface specification: schemas below, message types above")

    report.p("""
        Two layers need specifying in a system like this, and the literature
        treats them very differently. Below the agents, the Model Context Protocol
        standardises how a tool is described and invoked, giving each tool a
        JSON-RPC entry point and a declared input schema [@anthropic2024]. The
        appeal is straightforward: a malformed call is rejected at the boundary
        rather than reaching an API as a silent error. MCP is young, however. An
        early analysis of its landscape notes that the specification governs the
        transport and the schema declaration, but leaves the correspondence between
        a declared schema and the code behind it to the implementer [@hou2025].
        That is not a small gap, and Section 6.4 reports what auditing it found in
        this project's own server.
    """)

    report.p("""
        Above the agents there is no equivalent standard. The nearest is much
        older. The FIPA Communicative Act Library defines a typed vocabulary of
        speech acts for agent messaging — request, inform, agree, refuse — so that
        the intent of a message is not left to interpretation [@fipa2002]. Modern
        LLM frameworks largely abandoned this for free text, and the observed
        consequence is what motivated the reintroduction of typing here. In a study of twenty-five generative
        agents, information transmitted between agents as natural language
        degraded across successive hops as each recipient paraphrased what it had
        received [@park2023].
    """)

    report.p("""
        This project adopts both layers — schema validation below, typed envelopes
        above — which is not novel in either half. What it allows is a test of whether
        the combination behaves as its advocates claim, and that requires treating
        conformance as something to measure rather than something the presence of a
        protocol guarantees. Section 6.4 reports that distinction mattering.
    """)

    # ------------------------------------------------------------------ 2.4
    report.h2("2.4  Travel planning as an evaluated task")

    report.p("""
        Itinerary generation has a long pre-LLM history, generally as constrained
        optimisation over a fixed catalogue of points of interest [@lim2019]. Those
        systems were sound about constraints and closed about data: nothing they
        produced could be booked. The current literature inverts both properties.
    """)

    report.p("""
        TravelPlanner is the reference point. It supplies 1,225 tasks with
        explicit budget and commonsense constraints and a sandboxed environment,
        and reports that the best single-agent GPT-4 configuration achieves a
        0.6% final pass rate [@xie2024]. Its value is that it separates
        plausibility from correctness. Its limit, for a project like this one, is
        that its environment is a frozen snapshot. An agent that scores well on it
        has not shown it can cope with a live API that returns a session identifier
        instead of results, or ignores a parameter it does not recognise. Both
        happened here, and Chapter 5 documents them.
    """)

    report.p("""
        Two follow-ups accept the benchmark's diagnosis and disagree about the
        remedy. One compiles the constraints into a satisfiability problem and
        uses a formal solver, reporting large gains and arguing that constraint
        satisfaction is not what a language model should be doing [@hao2024]. The
        other keeps the model in the loop but surrounds it with external critics
        that verify and re-prompt, an arrangement its authors call LLM-Modulo
        [@gundawar2024]. Both concede the same ground: the model is unreliable at
        the deterministic parts of the task and should be relieved of them. Both,
        however, apply that reasoning to constraint checking rather than to
        retrieval, which is the earlier and more expensive step. Extending the
        argument to retrieval, and measuring the result on live APIs, is where
        this project sits.
    """)

    # ------------------------------------------------------------------ 2.5
    report.h2("2.5  Measuring whether output is grounded")

    report.p("""
        If the failure is invention, the evaluation has to detect invention, and
        surveys of hallucination in generated text make clear that fluency
        measures will not [@ji2023]. Two approaches are relevant. FActScore
        decomposes generated text into atomic factual claims and verifies each
        against a knowledge source, reporting precision over claims rather than a
        single verdict per document [@min2023]. RAGAS applies a related idea to
        retrieval-augmented generation, scoring faithfulness by asking whether
        each statement is supported by the retrieved context [@es2024].
    """)

    report.p("""
        Both use a language model as the judge, which is reasonable for open-domain
        prose and unnecessary here. Travel data has a property general text does not:
        the ground truth is numeric and was retrieved minutes earlier. Whether a
        quoted fare matches a fare the API returned is a comparison rather than an
        inference, and it avoids importing a second model's errors into the
        measurement. The metric used here follows the FActScore principle — score the
        atomic claims, not the document — while substituting exact matching against
        recorded responses for model-based adjudication. Its weakness, set out in
        Section 3.4, is that it measures whether named entities were retrieved and not
        whether they were well chosen.
    """)

    # ------------------------------------------------------------------ 2.6
    report.h2("2.6  Conceptual framework and the gap addressed")

    report.p("""
        The five streams converge on four failure modes, each with a documented
        cause and each admitting a design response. Context bloat follows from the
        ReAct loop's monotonic transcript growth [@schick2023] and from uneven
        attention over long inputs [@liu2024]; the response is to distil tool
        output and narrow each component's tool set. Protocol fragility follows
        from unvalidated tool invocation [@anthropic2024; @hou2025]; the response
        is a declared schema per tool. Semantic drift follows from free-text
        handoff between agents [@park2023]; the response is a typed envelope with
        validated permissions, in the FIPA tradition [@fipa2002]. Hallucinated
        venues and fares follow from generating what should be retrieved
        [@xie2024]; the response is to ground every claim in a recorded API
        response and to score what can be traced back to one.
    """)

    protocol = measured.protocol_summary()
    report.figure(
        "diagrams/conceptual_framework.png",
        "The conceptual framework. Each documented failure mode, the design "
        "decision taken against it, and the measured outcome. Two of the four "
        "responses did not survive measurement.")

    report.p(f"""
        The fourth column is what distinguishes this framework from a restatement
        of its sources. Each response was tested, and two did not hold. The schema
        layer meant to prevent malformed invocation contains
        {val(len(measured.mcp_schema_stats()['defective_tools']))} tools whose
        declared schemas disagree with their implementations, and the typed
        message layer honours its permission rules while ignoring the priority
        ordering it advertises: {val(protocol['passed'])} of
        {val(protocol['total_checks'])} conformance checks pass. Adopting a
        protocol is not the same as conforming to it, and the literature reviewed
        above offers no method for telling the difference. Section 6.4 supplies
        one.
    """)

    report.p("""
        The gap this dissertation addresses can now be stated precisely. The tool
        literature establishes that models can retrieve; the multi-agent
        literature establishes that tasks can be decomposed; the travel literature
        establishes that ungrounded planning fails; and the most recent failure
        analysis suggests coordination is where multi-agent systems break
        [@cemri2025]. None of them measures what a language model costs at a step
        where no judgement is required, on live consumer APIs, against a
        multi-agent baseline that has been tuned first so the comparison is fair.
        That measurement is the contribution, and its narrowness is deliberate:
        Chapter 6 reports that tuning the baseline removed most of the difference
        the project expected to find.
    """)
