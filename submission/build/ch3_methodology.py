"""Chapter 3: methodology."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val


def build(report: Report) -> None:
    report.start_body("3 Methodology")
    report.h1("Methodology")

    # ------------------------------------------------------------------ 3.1
    report.h2("3.1  Research approach")

    report.p("""
        The contribution of this project is a working system and what measuring it
        revealed, which places it in design science: knowledge is produced by
        building an artefact and evaluating it against the problem it was built for
        [@hevner2004]. The six-activity process model — problem identification,
        objective definition, design and development, demonstration, evaluation,
        communication — supplies the structure, and its authors are explicit that
        the process is iterative, with evaluation feeding back into design
        [@peffers2007]. That iteration is the part that mattered here, because two
        of the three cycles ended by contradicting the design that entered them.
    """)

    report.p("""
        Two alternatives were rejected. A comparative user study of commercial
        assistants would have produced findings about products rather than
        architecture, and needed ethical approval the question did not warrant. A
        formal treatment would have avoided the quota problem and produced no evidence
        that any of it works against a live endpoint, which is where every interesting
        failure in Chapter 5 occurred.
    """)

    report.figure(
        "diagrams/methodology.png",
        "The three design-science cycles as they actually ran. Each was closed by "
        "a measurement that changed the design rather than by a decision to move on.")

    report.p("""
        Cycle one built the artefact the proposal specified and ended when the system
        was found producing confident itineraries that cited nothing retrievable,
        because a path defect meant every tool call was failing silently. Cycle two
        added instrumentation, and the resulting count motivated the three-agent
        design. Cycle three removed the obvious objection to that comparison by tuning
        the six-agent arm first, and produced the result that weakened the project's
        own thesis.
    """)

    # ------------------------------------------------------------------ 3.2
    report.h2("3.2  Why four architectures rather than two")

    report.p("""
        The comparison could have been run as three agents against six, and that design
        is unsound in two directions at once. Against the six-agent implementation as
        first written, any advantage the three-agent design showed is open to the
        objection that the baseline was badly configured. Without a tool-less control,
        nothing establishes that the tool layer contributes at all, and the cheapest
        architecture appears to win while its output is unverifiable.
    """)

    report.p("""
        Four arms follow. A is the control with no tools at all, establishing what
        the tool layer buys and what a plan looks like when nothing in it was
        retrieved. B is the six-agent design as first implemented — its cost is what
        motivated the pivot, so removing it would hide the reasoning. C is the same
        six roles tuned: one narrow tool each, distilled results, concurrent
        execution, shorter prompts. D is the three-agent design with retrieval in
        ordinary Python, which is the claim under test. Appendix L tabulates the role
        each plays.
    """)

    report.p("""
        Arm C is the methodological centre of the evaluation and it was expensive to
        include: building it meant implementing three commitments the proposal had made
        and the first implementation had not, then handing the improved version the
        strongest possible position before comparing against it. It also produced the
        result in Section 6.3, that most of the difference the project set out to
        demonstrate was implementation quality rather than architecture. Arm C is what
        makes that finding available; its absence is what would have made the headline
        claim indefensible under questioning.
    """)

    report.p("""
        One control is imperfect. The six-agent arms instantiate five agents: the conversational agent is omitted so
        every arm receives one identical request string, since a multi-turn dialogue
        cannot be held identical across four architectures. The comparison is therefore
        between three agents and a five-agent ablation of the six-agent design. The
        omitted role is the same in both multi-agent arms and absent from the other two,
        so it does not bias the contrast — but the arms are named for the design they
        represent, and the difference should be visible.
    """)

    # ------------------------------------------------------------------ 3.3
    report.h2("3.3  Scenario design")

    coverage = measured.coverage()
    report.p(f"""
        {val(coverage['scenarios_designed'])} scenarios were written before any
        measurement, to span the axes that change an itinerary's difficulty rather
        than to sample uniformly: trip length from three to fourteen nights,
        distance from short-haul Dubai to long-haul Tokyo, party size from solo to
        a family of four, destination price tier, multi-city routes, and budgets
        from generous down to deliberately impossible. Every arm receives the
        identical request string, so nothing in the comparison depends on
        phrasing.
    """)

    report.p("""
        Two scenarios were written to be unaffordable, deliberately: an architecture
        that confidently plans a trip nobody could afford is failing in the way the
        literature describes [@xie2024], and only an impossible case exposes it. Those
        two made the budget-gate result in Section 6.5 possible, and they also caught a
        defect in the gate itself. Each scenario further records the facts a reader
        extracts from its request — origin, legs, nights, date, budget, party — as
        declared ground truth. No arm reads that field; it exists so the gate can be
        evaluated with exact parameters rather than parsed guesses.
    """)

    # ------------------------------------------------------------------ 3.4
    report.h2("3.4  Metrics, and what each one cannot tell you")

    report.p("""
        Seven metrics are collected, and each is recorded together with what it
        cannot establish; Appendix H tabulates all seven with their provenance and
        their limits. Four concern cost — model requests, prompt and completion
        tokens, dollar cost and wall-clock latency — and all four are obtained by
        instrument rather than by inference, which is what makes them comparable
        across arms. Two concern quality: the proportion of quoted prices matching a
        retrieved fare, and the proportion of named hotels and airlines appearing in
        the retrieved results. The seventh is protocol conformance, a count of
        executable checks passed.
    """)

    report.p("""
        The groundedness measure is asymmetric, and reporting its two halves as
        equals would overstate the result. Matching a name is weak
        evidence: on the recorded scenario the arm with no tool access named a real
        airline for the route, having called nothing. Matching a price is strong,
        because landing within 2% of a fare quoted minutes earlier is not something
        prior knowledge delivers. The tolerance exists because an itinerary
        legitimately rounds and sums nightly rates into totals, and it is narrow enough
        that invention does not pass it. Price grounding carries the claim.
    """)

    # ------------------------------------------------------------------ 3.5
    report.h2("3.5  Controls, fairness and reproducibility")

    report.p(f"""
        Four properties are enforced by the harness rather than by care. Every arm
        receives the byte-identical request, and every arm is measured by the same
        instrument, so a hand-counted figure can never be compared against a measured
        one. The arm with deterministic retrieval runs first in each scenario, which
        populates the response cache with canonical parameters so the agent arms replay
        rather than issuing slightly different live queries. Results are checkpointed
        after each scenario, so an interrupted run keeps what it has already paid for.
        Section 5.5 describes the mechanisms.
    """)

    report.p("""
        The weakness of replay is worth naming here, because it qualifies one of the
        four headline metrics. Replayed retrieval takes milliseconds, so latency
        figures understate a live run and the direct arm's retrieval phase reads as
        effectively zero. Comparisons between arms remain valid, since all four
        replay the same responses; they are not estimates of production latency.
    """)

    # ------------------------------------------------------------------ 3.6
    report.h2("3.6  Data strategy and its limits")

    report.p(f"""
        The evaluation data is machine-generated — recorded API responses and
        measured metrics — with no human-subject data of any kind. The binding
        constraint is quota: the flight API allows thirty requests a month and the
        hotel API fifty, on free tiers that cannot be topped up, and a single flight
        search costs two because the endpoint is asynchronous and must be polled. One
        scenario therefore consumes roughly four of eighty monthly requests, and
        recording all {val(coverage['scenarios_designed'])} designed scenarios spans
        more than one monthly cycle. {val(coverage['scenarios_measured'])} is
        recorded, which is the real sample size for the cost comparison and is quoted
        as such wherever those numbers appear.
    """)

    report.p("""
        This shaped what could be claimed. The response was not to present one
        scenario as twenty, but to ask which questions can be answered without quota
        and answer those completely: protocol conformance needs no network, and the
        feasibility gate needs neither network nor model. Both are evaluated across
        the full scenario set, and both produced negative findings that the
        quota-limited comparison could not have produced. Quota was also this
        project's largest risk: Appendix N holds the register, the controls built
        before the arms were, and which risks occurred regardless.
    """)

    # ------------------------------------------------------------------ 3.7
    report.h2("3.7  Ethics and professional considerations")

    report.p("""
        No human participants were involved, no personal data was collected and no
        ethical approval was required; this was confirmed with the supervisor at the
        first check-in. All API use is read-only and within published free-tier terms,
        and no endpoint was scraped. The response cache holds third-party commercial
        data — hotel names, review scores, fares — locally and solely to reproduce the
        reported results; it contains no personal data, and request headers carrying
        credentials are excluded from what is written to disk.
    """)

    report.p("""
        One obligation runs beyond compliance and shaped a measurement. The BCS code
        requires members not to misrepresent what their work can do [@bcs2022], and a
        system that prints prices invites the reading that those prices are bookable.
        That is why groundedness is measured rather than assumed. Section 7.5 returns
        to the professional and legal position with the measured result in hand.
    """)
