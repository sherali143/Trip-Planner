"""Chapter 6: evaluation and results."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import BuildError, Report, val

# The two arms this chapter's headline comparison is between.
_TUNED, _DIRECT = "C", "D"


def _require_separation(metric: str, claim: str) -> None:
    """
        Fail the build if this chapter claims two intervals are separated and they
        are not. A qualitative claim is as capable of going stale as a number, and
        the perturbation check cannot catch it: it verifies that values move when
        the data moves, not that a sentence about those values is still true. So the
        claim is checked against the data it describes. Deliberately not
        self-rewording. If the tuned and direct arms stop separating on cost, the
        chapter's argument has changed and needs a person to rewrite it, not a
        builder to quietly swap "do not overlap" for "overlap".
    """
    if measured.intervals_overlap(_TUNED, _DIRECT, metric):
        a = measured.spread(_TUNED, metric)
        b = measured.spread(_DIRECT, metric)
        raise BuildError(
            f"{claim} says the {metric} intervals do not overlap, but they now do: "
            f"arm {_TUNED} [{a['ci95_low']:.4f}, {a['ci95_high']:.4f}] against arm "
            f"{_DIRECT} [{b['ci95_low']:.4f}, {b['ci95_high']:.4f}]. The finding has "
            f"changed — rewrite the argument in ch6_evaluation.py rather than "
            f"loosening this check.")


def _require_overlap(metric: str, claim: str) -> None:
    """The mirror of _require_separation, for a claim that two intervals DO overlap."""
    if not measured.intervals_overlap(_TUNED, _DIRECT, metric):
        a = measured.spread(_TUNED, metric)
        b = measured.spread(_DIRECT, metric)
        raise BuildError(
            f"{claim} says the {metric} intervals overlap, but they no longer do: "
            f"arm {_TUNED} [{a['ci95_low']:.4f}, {a['ci95_high']:.4f}] against arm "
            f"{_DIRECT} [{b['ci95_low']:.4f}, {b['ci95_high']:.4f}]. That would be a "
            f"stronger result than this dissertation claims, and it must be argued "
            f"deliberately rather than appearing by accident.")


def build(report: Report) -> None:
    report.start_body("6 Evaluation")
    report.h1("Evaluation")

    coverage = measured.coverage()

    # ------------------------------------------------------------------ 6.1
    report.h2("6.1  Experimental design and what it can support")

    report.p("""
        Five experiments answer five questions. E1 compares what each architecture
        costs per trip and how grounded its output is. E2 and E3 re-read E1's
        records to ask where the token spend goes and how much of the multi-agent
        penalty is implementation rather than architecture. E4 audits whether the
        protocol layer behaves as the design claims. E5 asks whether the budget gate
        refuses budgets that cannot buy the trip, and whether its cost model is
        externally valid. Appendix K tabulates each with its coverage and what it
        costs to run. Only E1 spends model quota; E4 and E5 touch no network at all,
        which is why they cover the full scenario set and E1 does not.
    """)

    report.p(f"""
        E1's sample is uneven in a way that must be stated before its numbers are
        read. Every architecture was run {val(coverage['repeats_per_arm'])} times,
        so every figure carries a standard deviation and a 95% interval. Those
        repeats sit on {val(coverage['scenarios_measured'])} of
        {val(coverage['scenarios_designed'])} designed scenarios, because repeats
        replay recorded responses free while each new scenario costs about four of
        the eighty API requests a month allows. Differences between architectures on
        this trip can therefore be judged against their own noise; generalisation to
        other trips cannot, and this remains a single-case study in the sense used
        in empirical software engineering [@runeson2009; @wohlin2012].
    """)

    report.p(f"""
        Intervals are Student-t rather than normal, because at
        {val(coverage['repeats_per_arm'])} observations the normal approximation is
        too narrow, and an interval quoted too tightly is worse than none. Rather
        than a significance test, which would claim more precision than five
        observations hold, differences are judged by whether two arms' intervals
        overlap — a conservative reading, reported in both directions below.
    """)

    # ------------------------------------------------------------------ 6.2
    report.h2("6.2  E1: what each architecture costs")

    report.figure("results/efficiency.png",
                  "Model requests, tokens, cost and wall-clock time per trip for "
                  "all four architectures.")

    def _pm(code: str, metric: str, fmt: str) -> str:
        """Mean plus or minus one standard deviation, both measured."""
        block = measured.spread(code, metric)
        return f"{val(block['mean'], fmt)} ± {val(block['sd'], fmt)}"

    rows = []
    for code in ("A", "B", "C", "D"):
        arm = measured.arm(code)
        rows.append([
            f"{code}  {arm['name']}",
            _pm(code, "llm_calls", "{:.1f}"),
            _pm(code, "total_tokens", "{:,.0f}"),
            _pm(code, "cost_usd", "{:.4f}"),
            _pm(code, "latency", "{:.0f}"),
            _pm(code, "prices_grounded_pct", "{:.0f}"),
        ])
    report.table(
        ["Architecture", "Requests", "Tokens", "Cost (USD)", "Seconds",
         "Prices grounded (%)"],
        rows,
        f"E1 results on {', '.join(coverage['scenario_ids'])}, mean ± one standard "
        f"deviation over {coverage['repeats_per_arm']} runs of each architecture. "
        f"Requests are counted by provider callback. Retrieval is replayed, so "
        f"latency excludes network time.",
        widths=[1.55, 0.95, 1.15, 0.95, 0.8, 1.1],
        font_pt=9,
    )

    report.p(f"""
        Two standard deviations are zero, and that is a result rather than rounding.
        The tool-less arm issues exactly {val(measured.spread('A',
        'llm_calls')['mean'], '{:.0f}')} request and the direct arm exactly
        {val(measured.spread('D', 'llm_calls')['mean'], '{:.0f}')} on every run,
        because neither contains a loop deciding how many requests to make. The
        agent arms cannot offer that — the naive arm varies by
        {val(measured.spread('B', 'llm_calls')['cv_pct'], '{:.1f}')}% and the tuned
        arm by {val(measured.spread('C', 'llm_calls')['cv_pct'], '{:.1f}')}%. For
        anyone budgeting, predictability is a property in its own right.
    """)

    d_vs_c = measured.improvement("D_vs_C")
    d_vs_b = measured.improvement("D_vs_B")
    report.p(f"""
        Against the tuned six-agent arm, the three-agent design used
        {val(d_vs_c['llm_calls_pct'], '{:.1f}')}% fewer model requests,
        {val(d_vs_c['latency_pct'], '{:.1f}')}% less wall-clock time,
        {val(d_vs_c['cost_pct'], '{:.1f}')}% less money and
        {val(d_vs_c['tokens_pct'], '{:.1f}')}% fewer tokens. Against the naive arm
        every gap is larger — {val(d_vs_b['tokens_pct'], '{:.1f}')}% fewer tokens —
        and Section 6.3 explains why that is the wrong comparison to lead with.
    """)

    cost_c, cost_d = measured.spread("C", "cost_usd"), measured.spread("D", "cost_usd")
    lat_c, lat_d = measured.spread("C", "latency"), measured.spread("D", "latency")
    gnd_c, gnd_d = (measured.spread("C", "prices_grounded_pct"),
                    measured.spread("D", "prices_grounded_pct"))
    # The words "do not overlap" used to be typed here while only the bounds came
    # from the data. If a re-measurement made the cost intervals overlap, the
    # chapter would have printed overlapping numbers underneath a sentence saying
    # they do not. The relationship is now read from the data, and a flip stops the
    # build: it does not need rewording, it needs the argument rewritten, and that
    # is a decision for a person.
    _require_separation("cost_usd", "Section 6.4's cost claim")
    _require_separation("latency", "Section 6.4's latency claim")
    _require_overlap("prices_grounded_pct", "Section 6.4's groundedness claim")

    report.p(f"""
        With repeats, those percentages can be tested against their own noise
        instead of being asserted, and the answer separates cleanly into two kinds.
        Cost intervals do not overlap: the tuned arm sits in
        [{val(cost_c['ci95_low'], '${:.4f}')}, {val(cost_c['ci95_high'],
        '${:.4f}')}] and the direct arm in [{val(cost_d['ci95_low'], '${:.4f}')},
        {val(cost_d['ci95_high'], '${:.4f}')}]. Latency intervals do not overlap
        either — [{val(lat_c['ci95_low'], '{:.1f}')}, {val(lat_c['ci95_high'],
        '{:.1f}')}] seconds against [{val(lat_d['ci95_low'], '{:.1f}')},
        {val(lat_d['ci95_high'], '{:.1f}')}]. Both differences are therefore larger
        than run-to-run variation.
    """)

    report.p(f"""
        Groundedness behaves the other way, and this is the result the chapter turns
        on. The tuned arm's interval is [{val(gnd_c['ci95_low'], '{:.1f}')},
        {val(gnd_c['ci95_high'], '{:.1f}')}]% and the direct arm's is
        [{val(gnd_d['ci95_low'], '{:.1f}')}, {val(gnd_d['ci95_high'], '{:.1f}')}]%.
        They overlap substantially. The tuned arm's mean is higher —
        {val(gnd_c['mean'], '{:.1f}')}% against {val(gnd_d['mean'], '{:.1f}')}% —
        and with five observations apiece that difference cannot be distinguished
        from noise. The honest reading is not that the two are equal but that this
        evidence cannot separate them, and the direction of the means is worth
        recording in case more data resolves it against the direct arm.
    """)

    report.p("""
        So the supported claim is narrow and specific: removing the model from
        deterministic retrieval buys a decisive saving in cost, latency and request
        count, makes request cost exactly predictable, and costs no groundedness
        this evidence can detect. It does not show better-grounded plans, and the
        means lean slightly the other way.
    """)

    report.p(f"""
        One result runs against the expected direction. The tool-less arm is not the
        cheapest: it cost {val(measured.arm_metric('A', 'avg_cost_usd'), '${:.4f}')}
        against the direct arm's {val(measured.arm_metric('D', 'avg_cost_usd'),
        '${:.4f}')} despite issuing one request rather than two, and it was the
        slowest arm at {val(measured.arm_metric('A', 'avg_latency'), '{:.0f}')}
        seconds. The next section explains why.
    """)

    # ------------------------------------------------------------------ 6.3
    report.h2("6.3  E2 and E3: where the tokens go, and what tuning removed")

    report.figure("results/token_decomposition.png",
                  "Prompt and completion tokens per architecture. Prompt tokens are "
                  "re-sent context and tool schemas; completion tokens are the "
                  "generated itinerary.")

    # Means across repeats, matching the table above and the token chart.
    a_llm = measured.token_split("A")
    b_llm = measured.token_split("B")
    c_llm = measured.token_split("C")
    d_llm = measured.token_split("D")

    report.p(f"""
        The decomposition explains the anomalies. The tool-less arm spent
        {val(a_llm['prompt_tokens'], '{:,.0f}')} prompt tokens against
        {val(a_llm['completion_tokens'], '{:,.0f}')} completion: with no data to
        work from it invented detail to fill the requested structure. Output is
        billed at several times the rate of input, so an arm that reads nothing and
        writes a great deal is expensive, and its latency follows for the same
        reason.
    """)

    report.p(f"""
        The naive six-agent arm has the opposite profile:
        {val(b_llm['prompt_tokens'], '{:,.0f}')} prompt tokens against
        {val(b_llm['completion_tokens'], '{:,.0f}')} completion, so
        {val(b_llm['prompt_tokens'] / (b_llm['prompt_tokens'] +
        b_llm['completion_tokens']) * 100, '{:.0f}')}% of its spend is re-sent
        context. Raw tool output for the whole scenario is a small fraction of that,
        so the payload is not the problem — re-sending the accumulated transcript
        plus every bound tool's schema on every reasoning iteration is. This is the
        context-bloat mechanism from Section 2.1, measured [@schick2023; @liu2024].
    """)

    report.figure("results/tuning_effect.png",
                  "The tuning ablation. Same six roles, same data path, same model; "
                  "only prompt economics changed.")

    c_vs_b = measured.improvement("C_vs_B")
    report.p(f"""
        E3 is the result that most constrains what this dissertation can claim. The
        six-agent arm was tuned in five ways: one narrow tool per specialist instead
        of up to eight, an iteration ceiling of three instead of fifteen, distilled
        tool results, shorter role descriptions, and the three specialists run
        concurrently. With the same architecture and the same retrieved data, that
        reduced its tokens by {val(c_vs_b['tokens_pct'], '{:.1f}')}%, its cost by
        {val(c_vs_b['cost_pct'], '{:.1f}')}% and its request count by
        {val(c_vs_b['llm_calls_pct'], '{:.1f}')}%. Prompt tokens fell from
        {val(b_llm['prompt_tokens'], '{:,.0f}')} to {val(c_llm['prompt_tokens'],
        '{:,.0f}')}.
    """)

    report.p(f"""
        Most of the penalty attributed to the multi-agent design was therefore
        implementation quality, not architecture. Run against the naive arm alone
        the comparison would have reported a {val(d_vs_b['tokens_pct'], '{:.1f}')}%
        token advantage, and the conclusion would have been unattributable: a reader
        could not tell how much came from removing agents and how much from
        configuring them competently. The defensible claim is narrower. Against a
        competently configured multi-agent baseline, removing the model from
        deterministic retrieval saves request count and latency decisively and cost
        only modestly, at no measured loss of groundedness. That claim survives the
        obvious objection; the wider one does not.
    """)

    # ------------------------------------------------------------------ 6.4
    report.h2("6.4  E4: does the protocol layer do what the design says?")

    report.figure("results/protocol_conformance.png",
                  "Nine conformance checks over the message layer and the tool "
                  "schemas. Six fail.")

    summary = measured.protocol_summary()
    schema = measured.mcp_schema_stats()
    a2 = measured.protocol_check("A2")
    a1 = measured.protocol_check("A1")
    a5 = measured.protocol_check("A5")
    m4 = measured.protocol_check("M4")

    report.p(f"""
        {val(summary['passed'])} of {val(summary['total_checks'])} checks pass. The
        proposal committed to a schema pass rate of 100% and an inter-agent error
        rate below 1%; the second is met on the path that ships and the first is not
        met at all. The six failures are findings about this artefact, not
        incidental defects.
    """)

    report.p(f"""
        Three failures are in the message layer. Priority is declared on every
        message and never honoured, because the queue is first-in-first-out:
        enqueued {a2['observed']['enqueued']}, delivered
        {a2['observed']['delivered']}. Declared inbound permissions have no effect,
        since validation consults only the sender's outbound list, leaving
        {val(len(a1['observed']['unmirrored_inbound_declarations']))} of
        {val(a1['observed']['declared_outbound_edges'])} declared edges asymmetric.
        And a message polled by the wrong recipient is destroyed, because the
        receive path removes it from the queue before checking the address.
    """)

    report.p(f"""
        Three are in the tool layer. {val(len(schema['defective_tools']))} of
        {val(schema['tools_total'])} tools accept parameters their schema omits —
        {val(schema['undeclared_parameter_count'])} in total — so an agent cannot
        set them and they silently take defaults, which is precisely the class of
        mismatch the schema layer was adopted to prevent. One tool treats a
        parameter as mandatory that its schema does not list as required. And one
        advertises the flight scraper in its description while its dispatcher calls
        the hotel provider's flight endpoint, so an agent choosing it on that
        description gets a different backend. Appendix B gives every check and its
        observation.
    """)

    report.p("""
        Two general readings follow. Adopting a protocol is not conforming to it:
        the specification governs how a schema is declared and transported and
        leaves its correspondence with the code behind it to the implementer
        [@anthropic2024; @hou2025], and nothing warned. And the message-layer
        defects sit in code the shipped path never executes, which is how they
        survived a passing suite. All six were found in an afternoon by an
        experiment needing no network, no model and no credentials, after weeks in
        which none was noticed.
    """)

    # ------------------------------------------------------------------ 6.5
    report.h2("6.5  E5: the budget gate, and a calibration failure behind it")

    report.figure("results/budget_gate.png",
                  "The gate's decision on all twenty scenarios, and the flight-cost "
                  "anchor that explains the one it gets wrong.")

    agreement = measured.gate_agreement()
    anchor = measured.gate_external_validity()
    misses = measured.gate_misses()
    monotonic = measured.budget_gate()["monotonicity"]

    report.p(f"""
        Two of the twenty scenarios were written to be unaffordable. The gate
        refused {val(agreement['true_positive'])} of them and accepted
        {val(agreement['true_negative'])} of the eighteen affordable ones, with
        {val(agreement['false_positive'])} false refusals and
        {val(agreement['false_negative'])} miss. Raw agreement of
        {val(agreement['accuracy_pct'], '{:.1f}')}% is a misleading figure, because
        with eighteen of twenty cases affordable a gate that refused nothing would
        score {val(agreement['chance_agreement'] * 100, '{:.0f}')}%. Cohen's kappa
        corrects for chance agreement [@cohen1960] and gives
        {val(agreement['cohens_kappa'], '{:.3f}')} — substantial rather than good on
        the conventional interpretation [@landis1977].
    """)

    if not misses:
        raise RuntimeError(
            "the budget gate results record no disagreement with designed intent; "
            "Section 6.5 is written around one and must be revised if the gate "
            "starts agreeing everywhere")
    miss = misses[0]
    report.p(f"""
        The missed case is {miss['scenario']}: {val(miss['budget'], '${:,.0f}')} for
        {val(miss['nights'])} nights in {miss['destination']} for one traveller. The
        gate estimated a minimum of {val(miss['estimate_minimum'], '${:,.0f}')},
        judged the budget {val(miss['budget_vs_minimum'], '{:.2f}')} times that
        floor, returned a verdict of "{miss['verdict'].replace('_', ' ')}" and
        proceeded.
    """)

    report.p(f"""
        The cause is measurable rather than a matter of opinion, and it is the most
        useful result in this chapter. The gate's cost model rests on anchor values
        for the cheapest realistically bookable fare in each distance band. For the
        one route where real fares are recorded — {anchor['route']}, with
        {val(anchor['fares_recorded'])} fares in the response cache — the model's
        anchor is {val(anchor['estimated_minimum'], '${:,.0f}')} while the cheapest
        fare the API actually returned was {val(anchor['cheapest_real_fare'],
        '${:,.0f}')} and the median was {val(anchor['median_real_fare'],
        '${:,.0f}')}. The anchor is {val(abs(anchor['minimum_anchor_error_pct']),
        '{:.0f}')}% below the cheapest real fare.
    """)

    report.p(f"""
        That mis-calibration accounts for the missed decision arithmetically: with
        the flight floor at less than half the real airfare, the estimated minimum
        comes out at {val(miss['estimate_minimum'], '${:,.0f}')} when the airfare
        alone would consume the entire {val(miss['budget'], '${:,.0f}')}. The gate
        reasons correctly from a wrong number. It is also internally consistent — a
        monotonicity check over {val(monotonic['checks_run'])} cases found
        {val(len(monotonic['violations']))} violations — so the structure is right
        and the constants are wrong, which is far more tractable than the reverse.
    """)

    report.p("""
        The obvious response is to raise the anchor, and it has deliberately not
        been done. One route cannot calibrate three distance bands. Correcting the
        medium-haul constant against the only route with recorded fares would be
        tuning a model on its single validation point: the short-haul and long-haul
        constants would stay as unvalidated as before, while the whole model
        appeared checked.
    """)

    # ------------------------------------------------------------------ 6.6
    report.h2("6.6  A worked example")

    truth = measured.detail("D")["ground_truth"]
    control = measured.groundedness("A")
    direct = measured.groundedness("D")

    gate_row = measured.budget_gate()["decision_table"][0]
    report.p(f"""
        Following one scenario through shows how the measures interact. The request
        is a four-night trip from Lahore to Istanbul for one traveller on eight
        hundred dollars, with an interest in history, food and shopping. Extraction
        produces structured fields. The gate estimates a minimum of
        {val(gate_row['estimate_minimum'], '${:,.0f}')} and a comfortable figure of
        {val(gate_row['estimate_comfortable'], '${:,.0f}')}, returns a verdict of
        workable, warns and proceeds. Retrieval returns {val(len(truth['hotels']))}
        hotels, {val(len(truth['airlines']))} airlines and
        {val(len(truth['prices']))} distinct prices, and that set becomes the ground
        truth for every arm. Six typed messages are exchanged and all six pass
        permission validation.
    """)

    report.p(f"""
        The four arms then diverge on the same request. The direct arm quoted
        {val(direct['prices_quoted'])} prices, of which
        {val(direct['prices_grounded'])} match a retrieved fare or nightly rate. The
        tool-less arm quoted {val(control['prices_quoted'])} — more than twice as
        many — and matched {val(control['prices_grounded'])}. It named a real
        airline for the route despite calling no API, which is why entity matching
        is reported as weak evidence.
    """)

    report.figure("results/groundedness.png",
                  "Groundedness by architecture. The left panel carries the claim; "
                  "the right panel shows why entity matching cannot.")

    report.p(f"""
        This is the project's clearest result and its least surprising: the cheapest
        way to produce an itinerary is to invent one, and the tool layer is the
        difference between a plausible plan and a usable one.
    """)

    # ------------------------------------------------------------------ 6.7
    report.h2("6.7  Threats to validity")

    report.p(f"""
        One threat stopped being hypothetical, and handling it produced the repeats
        this chapter relies on. The model the first round of measurements used was
        withdrawn from new API keys, and its replacement refuses any request whose
        message list ends with a model turn — precisely how the agent framework's
        reasoning loop prompts. The three-agent arm was unaffected, having no such
        loop; the six-agent arms could not run at all. A compatibility layer now
        adjusts only requests that would otherwise be rejected, passes the rest
        through untouched, and counts what it changed. These figures are therefore
        not comparable with the earlier round, and an architecture evaluated against
        someone else's hosted model inherits that model's lifetime — a stronger
        argument for the recorded response cache than the one originally made.
    """)

    report.p(f"""
        Appendix L tabulates every threat with its remedy, classified after Wohlin
        et al. (2012). The three that most limit this chapter are breadth, the
        overlap, and the author. Breadth: the repeats give depth on one scenario and
        nothing about other trips. The overlap: the tuned and direct arms cannot be
        separated on groundedness, so "no measurable penalty" is the claim, not
        "equal". And the author designed, built, measured and interpreted all of it.
        The design offers a partial answer to the last rather than a defence — the
        conformance audit compares declarations against implementations, and the
        gate evaluation compares decisions against intent recorded before any
        measurement. Neither outcome was chosen and both went against the design. A
        study that produced {val(measured.protocol_summary()['failed'])} failures
        against its own author is harder to dismiss than one that confirmed
        everything.
    """)
