"""The reference list and the appendices, including the risk register."""

from __future__ import annotations

from trip_planner.evaluation import measured
from submission.build.common import Report, val
from submission.build.references import REFERENCES


def references(report: Report) -> None:
    from submission.build.common import CITATIONS

    report.start_excluded("references")
    report.unnumbered_h1("References")

    entries = sorted(
        (REFERENCES[k]["entry"], REFERENCES[k]["locator"]) for k in CITATIONS.keys()
    )
    for entry, locator in entries:
        line = (f"{entry} Available at: {locator}" if locator.startswith("http")
                else f"{entry} {locator}")
        paragraph = report.doc.add_paragraph(line)
        paragraph.paragraph_format.line_spacing = 1.5
        paragraph.paragraph_format.space_after = 0
        paragraph.paragraph_format.first_line_indent = None
        # Hanging indent, which is the BCU Harvard convention for a reference list.
        from docx.shared import Inches
        paragraph.paragraph_format.left_indent = Inches(0.5)
        paragraph.paragraph_format.first_line_indent = Inches(-0.5)
        # Excluded from the limit, but still counted, so the build's own totals
        # account for every word it writes.
        report._count(line)


def _appendix(report: Report, letter: str, title: str) -> None:
    report.appendix_index.append(letter)
    # Number this appendix's tables and figures by its letter, and start both
    # counters again, so Appendix C's first table is Table C.1.
    report.section_label = letter
    report._table_n = 0
    report._figure_n = 0
    report.unnumbered_h1(f"Appendix {letter} — {title}")


def appendices(report: Report) -> None:
    report.start_excluded("appendices")

    # Hoisted: several appendices quote coverage, and one of them now appears
    # before the point where it used to be defined.
    coverage = measured.coverage()

    # ---------------------------------------------------------------- A
    _appendix(report, "A", "Reproducing every number in this dissertation")

    report.p("""
        No credentials are required. The recorded API responses are committed, so
        the whole evaluation replays from disk. Run the commands in this order; each
        writes the data file the next one reads, and the document is rebuilt last.
    """)
    report.code(
        "run.bat                                 # sets up everything, then a menu\n"
        "\n"
        "python -m pytest -q                     # the test suite\n"
        "python -m trip_planner.evaluation.exp_protocol       # protocol conformance      (free)\n"
        "python -m trip_planner.evaluation.exp_budget_gate    # budget gate, 20 scenarios (free)\n"
        "\n"
        "python trip_planner/demos/compare_all_approaches.py  # all four, from the recordings\n"
        "\n"
        "python submission/build/make_diagrams.py    # 8 diagrams, 300 dpi, validated\n"
        "python submission/build/make_charts.py      # 6 charts from measured data\n"
        "python -m submission.build.build_dissertation     # this document\n"
        "python -m submission.build.verify_no_hardcoded_numbers   # perturbation check\n"
        "\n"
        "# Re-measuring the four arms needs a model that can run all of them.\n"
        "# See Section 6.7: the model these results came from has been withdrawn.\n"
        "set TRIP_PLANNER_API_MODE=replay\n"
        "set TRIP_PLANNER_MAX_LIVE_CALLS=0\n"
        "python -m trip_planner.evaluation.run_comparison SC-01 --force --repeats 5\n"
    )

    report.p("""
        The report build refuses to complete if a figure is missing, if a citation
        has no reference entry, if a reference is never cited, or if any diagram
        fails geometric validation. It also re-runs the test suite and reports the
        real pass count rather than a remembered one.
    """)

    # ---------------------------------------------------------------- B
    _appendix(report, "B", "Full protocol conformance results")

    checks = measured.protocol()["a2a_checks"] + measured.protocol()["mcp_checks"]
    report.table(
        ["ID", "Claim tested", "Result", "Observation"],
        [[c["id"], c["claim"], "PASS" if c["passed"] else "FAIL", c["detail"]]
         for c in checks],
        "Every conformance check, its claim, its result and the observation behind it.",
        widths=[0.35, 1.9, 0.55, 3.5],
        font_pt=8,
    )

    schema = measured.mcp_schema_stats()
    tools = measured.protocol_check("M2")["observed"]["tools"]
    report.table(
        ["Tool", "Dispatches to", "Parameters missing from schema", "Required mismatch"],
        [[t["tool"], t["dispatches_to"],
          ", ".join(t["undeclared_params"]) or "none",
          ", ".join(t["required_mismatch"]) or "none"]
         for t in tools],
        f"Per-tool schema audit. {val(schema['clean'])} of {val(schema['inspectable'])} "
        f"inspectable tools are clean; "
        f"{val(schema['undeclared_parameter_count'])} implementation parameters are "
        f"undeclared in total.",
        widths=[1.55, 1.75, 1.7, 1.3],
        font_pt=8,
    )

    # ---------------------------------------------------------------- C
    _appendix(report, "C", "Full budget gate decision table")

    rows = measured.budget_gate()["decision_table"]
    report.table(
        ["Scenario", "Destination", "Budget", "Nights", "Travellers", "Minimum",
         "Comfortable", "Budget/min", "Verdict", "Agrees"],
        [[r["scenario"], r["destination"], val(r["budget"], "${:,.0f}"),
          val(r["nights"]), val(r["travellers"]),
          val(r["estimate_minimum"], "${:,.0f}"),
          val(r["estimate_comfortable"], "${:,.0f}"),
          val(r["budget_vs_minimum"], "{:.2f}"),
          r["verdict"].replace("_", " "),
          "yes" if r["agrees"] else "NO"]
         for r in rows],
        "The feasibility gate's decision on all twenty designed scenarios.",
        widths=[0.6, 0.95, 0.5, 0.45, 0.55, 0.55, 0.7, 0.55, 0.8, 0.45],
        font_pt=7.5,
    )

    agreement = measured.gate_agreement()
    report.table(
        ["Quantity", "Value"],
        [["Scenarios evaluated", val(agreement["n"])],
         ["Correctly refused (true positive)", val(agreement["true_positive"])],
         ["Correctly accepted (true negative)", val(agreement["true_negative"])],
         ["Wrongly refused (false positive)", val(agreement["false_positive"])],
         ["Wrongly accepted (false negative)", val(agreement["false_negative"])],
         ["Observed agreement", val(agreement["observed_agreement"], "{:.3f}")],
         ["Chance agreement", val(agreement["chance_agreement"], "{:.3f}")],
         ["Cohen's kappa", val(agreement["cohens_kappa"], "{:.3f}")],
         ["Precision", val(agreement["precision"], "{:.3f}")],
         ["Recall", val(agreement["recall"], "{:.3f}")]],
        "Agreement statistics for the feasibility gate.",
        widths=[3.0, 1.2],
    )

    # ---------------------------------------------------------------- D
    _appendix(report, "D", "Per-arm measured detail")

    detail_rows = []
    for code in ("A", "B", "C", "D"):
        arm = measured.arm(code)
        llm = measured.token_split(code)
        ground = measured.groundedness(code)
        detail_rows.append([
            f"{code} {arm['name']}",
            val(arm["avg_llm_calls"]),
            val(llm["prompt_tokens"], "{:,.0f}"),
            val(llm["completion_tokens"], "{:,.0f}"),
            val(arm["avg_cost_usd"], "${:.4f}"),
            val(llm["llm_time_s"], "{:.1f}"),
            val(arm["avg_latency"], "{:.1f}"),
            val(ground["prices_quoted"]),
            val(ground["prices_grounded"]),
            val(ground["prices_grounded_pct"], "{:.1f}%"),
        ])
    report.table(
        ["Arm", "Requests", "Prompt tok", "Completion tok", "Cost",
         "Model s", "Wall s", "Prices quoted", "Grounded", "Grounded %"],
        detail_rows,
        "Full measured detail per arm. Note that the tuned arm's summed model time "
        "exceeds its wall-clock time, which is direct evidence of concurrent "
        "execution.",
        widths=[1.15, 0.6, 0.65, 0.75, 0.55, 0.5, 0.5, 0.65, 0.6, 0.6],
        font_pt=8,
    )

    truth = measured.detail("D")["ground_truth"]
    report.p(f"""
        The ground truth for the recorded scenario, extracted from what the APIs
        actually returned and used to score every arm: {val(len(truth['hotels']))}
        hotels, {val(len(truth['airlines']))} airlines and
        {val(len(truth['prices']))} distinct prices ranging from
        {val(min(truth['prices']), '${:,.2f}')} to
        {val(max(truth['prices']), '${:,.2f}')}.
    """)

    # ---------------------------------------------------------------- E
    _appendix(report, "E", "Code map and test summary")

    stats = measured.code_stats()
    report.table(
        ["Area", "Files", "Lines", "Purpose"],
        [[area, val(row["files"]), val(row["lines"], "{:,}"), row["description"]]
         for area, row in stats["areas"].items()]
        + [["Total", val(stats["total_files"]), val(stats["total_lines"], "{:,}"), ""]],
        "Code map by area.",
        widths=[1.3, 0.7, 0.8, 3.4],
    )

    report.p("""
        Module decomposition, referenced from Section 4.2. The right-hand column is
        the reason each boundary exists rather than a description of what the module
        contains.
    """)
    report.table(
        ["Module", "Responsibility", "Why it is separate"],
        [
            ["trip_planner/orchestrator.py",
             "The workflow: conversation, extraction, retrieval, assembly",
             "The only component that knows the order of operations. Both entry "
             "points run one method; they were two sharing 74% of their text"],
            ["trip_planner/agents.py, trip_planner/tasks.py",
             "The three agents that need a model, and their prompts",
             "Prompts change far more often than control flow"],
            ["trip_planner/comms/", "Typed messages, agent cards, permission validation",
             "Identical across all four arms, so it must not depend on any of them"],
            ["trip_planner/server/mcp_server.py",
             "The tool server: twelve tools over JSON-RPC and stdio",
             "Runs as a subprocess, so it cannot import from the caller's context"],
            ["trip_planner/tools/", "MCP client, direct HTTP clients, agent tool "
             "wrappers — one file each",
             "They were one 986-line module; split so the dependency is visible"],
            ["trip_planner/core/http_cache.py",
             "Record and replay, plus the live-call ceiling",
             "Every API call must pass one chokepoint or the guarantee is void"],
            ["trip_planner/core/llm_metrics.py", "Request, token and cost accounting",
             "Measurement must not live inside the thing being measured"],
            ["trip_planner/core/trip_cost.py, budget.py",
             "What a trip costs, and how a budget is split",
             "Testable in isolation, with no model and no network"],
            ["trip_planner/core/validators.py, resilience.py, log_setup.py",
             "Output validation, retry classification, credential-safe logging",
             "Cross-cutting concerns that no single caller owns"],
            ["trip_planner/evaluation/", "The four arms, the scenarios, the metrics, the runner",
             "Evaluation code must not be reachable from the shipped path"],
            ["submission/build/make_*.py", "Figure generation with mechanical layout "
             "validation",
             "A document generator is code, and can be wrong like any other"],
            ["submission/build/", "One module per chapter, plus shared helpers",
             "Every number is interpolated from measured data, never typed"],
        ],
        "Module decomposition and the reason for each boundary.",
        widths=[1.75, 2.35, 2.1],
        font_pt=8.5,
    )

    tests = measured.test_count()
    report.p(f"""
        The suite collects {val(tests['collected'])} tests. Section 5.7 sets out what
        they cover and, more importantly, what they do not: the message layer, the
        tool server, the record-and-replay cache and the metric collector have no
        unit tests, and are covered instead by the conformance experiment in
        Appendix B.
    """)

    cache = measured.api_cache_stats()
    report.table(
        ["Host", "Recorded responses"],
        [[host, val(n)] for host, n in sorted(cache["by_host"].items())]
        + [["Total", val(cache["entries"])]],
        f"Recorded API responses by host, "
        f"{val(cache['total_kb'], '{:,.0f}')} kB committed in total. These are what "
        f"make the results reproducible without credentials.",
        widths=[2.6, 1.4],
    )

    # ---------------------------------------------------------------- F
    _appendix(report, "F", "Forensic evidence from the recorded flight responses")

    evidence = measured.flight_api_evidence()
    report.p("""
        The response cache doubles as a record of the flight-search defects described
        in Section 5.3. The three kinds of recording can be compared directly.
    """)
    report.table(
        ["Recording", "Bytes", "Itineraries returned", "What it demonstrates"],
        [
            ["Search with snake_case date parameters",
             " / ".join(val(b) for b in evidence["broken_bytes"]),
             val(evidence["broken_max_itineraries"]),
             "The API accepted the request, returned HTTP 200, and ignored the dates"],
            ["Search with camelCase date parameters",
             val(evidence["fixed_bytes"], "{:,}"),
             val(evidence["fixed_itineraries"]),
             f"Correct dates, but status is still "
             f"'{evidence['fixed_status']}' — the search has only started"],
            ["Poll of the incomplete search",
             val(evidence["poll_bytes"], "{:,}"),
             val(evidence["poll_itineraries"]),
             f"Status '{evidence['poll_status']}'. Reading only the first response "
             f"discards most available fares"],
        ],
        "Recorded evidence for the two silent flight-search defects. Both fixes were "
        "necessary; neither was signalled by an error.",
        widths=[1.9, 0.8, 0.85, 2.75],
        font_pt=8.5,
    )

    # ---------------------------------------------------------------- G
    _appendix(report, "G", "Metrics, their provenance and their limits")

    report.p("""
        Referenced from Section 3.4. The right-hand column governs how strongly
        Chapter 6 states its conclusions, and is the reason price grounding carries
        the quality claim while entity grounding is reported only as support.
    """)
    report.table(
        ["Metric", "How it is obtained", "What it cannot establish"],
        [
            ["Model requests per trip",
             "Counted by provider callback on every completion, including those "
             "issued inside reasoning loops and internal retries",
             "Nothing about whether a request was useful — only that it happened"],
            ["Prompt and completion tokens",
             "Read from the provider's usage field per request",
             "Cost equivalence: on this model output tokens are billed several times "
             "input, so a token total conceals which kind it is made of"],
            ["Cost in US dollars",
             "Computed by the client library from its own price table",
             "Portability. A different provider or tier changes every figure"],
            ["Wall-clock latency",
             "Measured per arm and per phase",
             "The network component, since retrieval is replayed from disk and a "
             "live run would be slower"],
            ["Prices grounded",
             "Proportion of prices quoted in the itinerary matching a recorded fare "
             "or nightly rate within 2%",
             "Whether the option chosen was a good one, or whether the plan is "
             "internally consistent"],
            ["Entities grounded",
             "Hotel and airline names in the itinerary appearing in the retrieved "
             "results",
             "Much at all on its own — the obvious airline for a route is guessable, "
             "so this is supporting evidence only"],
            ["Protocol conformance",
             "Nine executable checks over the message layer and the tool schemas",
             "Whether a conforming protocol produces better plans"],
        ],
        "The seven metrics, their provenance, and the limit of each.",
        widths=[1.35, 2.45, 2.4],
        font_pt=8.5,
    )

    # ---------------------------------------------------------------- H
    _appendix(report, "H", "Test coverage by area")

    report.p("""
        Referenced from Section 5.7. The modules with most tests are the ones least
        central to the research claim, which is a consequence of their being the
        cheapest to test rather than a judgement about where defects were likely.
    """)
    report.table(
        ["Area", "Covered by the suite", "Assessment"],
        [
            ["Budget allocation and splitting", "Yes, extensively",
             "Pure functions with no network or model, so cheap to test thoroughly"],
            ["Trip cost estimation and the feasibility floor", "Yes",
             "Tested against the module's own thresholds, which is why Section 6.5 "
             "evaluates it against real fares instead"],
            ["Itinerary day-count validation", "Yes", "Straightforward and adequate"],
            ["Documentation accuracy", "Yes",
             "Tests that documented files exist and documented counts match the "
             "code — unusual, and it has caught real drift"],
            ["Safe arithmetic evaluation", "Yes, since the audit",
             "Previously the tests exercised a copy inside the test file while the "
             "tool used a character allowlist and a bare eval. One module now, and a "
             "test asserts the server's tool IS that module (Section 5.7)"],
            ["The message layer", "No",
             "Covered instead by the conformance experiment, which found three "
             "defects"],
            ["The tool server and its schemas", "No",
             "Covered instead by the conformance experiment, which found four "
             "defective schemas"],
            ["Record and replay, and metric collection", "No",
             "Exercised on every evaluation run but never asserted"],
            ["The four arms", "No",
             "Each run costs model quota, so no automated test drives them"],
        ],
        "Test coverage by area.",
        widths=[1.7, 1.75, 2.55],
        font_pt=8.5,
    )

    # ---------------------------------------------------------------- J
    _appendix(report, "I", "Every deviation from the proposal")

    report.p("""
        Referenced from Section 7.3, which groups these by cause and argues the two
        that are delivery failures rather than design changes.
    """)
    report.table(
        ["Proposed", "Delivered", "Why it changed, and where the evidence sits"],
        [
            ["Six agents in production", "Three; six retained for evaluation",
             "Instrumentation showed most requests were spent on deterministic "
             "retrieval. The six-agent design was measured before it was replaced and "
             "tuned before being used as a baseline (Sections 6.2, 6.3)"],
            ["Kiwi.com for flights", "fly-scraper via RapidAPI",
             "Kiwi withdrew free API access during the project; this was the only "
             "remaining free option with return-fare search (Section 5.3)"],
            ["GPT-4o and GPT-4o-mini split",
             f"{measured.model_name()} throughout",
             "A free tier made repeated evaluation affordable, and one model removes "
             "model choice as a confound between arms (Appendix N)"],
            ["Thirteen tools", "Twelve",
             "Two proposed flight tools collapsed into one when the provider changed "
             "(Section 6.4)"],
            ["Priority queuing, four levels", "Three levels, no ordering",
             "Not implemented. Found by the conformance audit rather than by "
             "recollection, and reported rather than dropped (Section 6.4, check A2)"],
            ["Search agents call the APIs via the MCP server",
             "Only the naive six-agent arm does; the shipped path calls the same "
             "functions in process",
             "The proposal's Figure 1 put the MCP server on the retrieval path of "
             "three parallel search agents. Removing retrieval from the agents left "
             "no agent to route through it, so the shipped path imports the server's "
             "tool functions instead. The JSON-RPC transport is still exercised by "
             "the naive arm and by the conformance audit, which tests all twelve "
             "declared schemas against their implementations (Sections 4.2, 7.2)"],
            ["Three search agents running in parallel",
             "Parallel in the tuned arm; sequential in the naive arm; absent from "
             "the shipped path",
             "Concurrency was one of the three proposal commitments missing from the "
             "naive implementation, which is why that arm was tuned before being used "
             "as a baseline rather than compared against as first built (Section 6.3)"],
            ["Bookability at least 80%",
             f"{val(measured.groundedness('D')['prices_grounded_pct'], '{:.0f}')}% of quoted "
             f"prices grounded",
             "The proposal defined bookability as re-query success, which needs quota "
             "this project did not have. Groundedness is a weaker but measurable "
             "substitute, and the substitution reduces ambition (Section 6.6)"],
            ["Twenty scenarios everywhere",
             f"Twenty for two experiments, "
             f"{val(measured.coverage()['scenarios_measured'])} for the cost comparison",
             "Monthly free-tier quota. Recordings accumulate, so coverage grows without "
             "re-running what exists (Section 6.1)"],
            ["Conversational agent in the web interface",
             "Fixed question sequence there",
             "The interface framework re-runs its whole script on each interaction, "
             "which does not suit a streaming dialogue. The conversational agent remains "
             "in the command-line path (Section 4.5)"],
        ],
        "Every deviation from the proposal, with its reason and its evidence.",
        widths=[1.35, 1.35, 3.5],
        font_pt=8.5,
    )

    # ---------------------------------------------------------------- L
    _appendix(report, "J", "The four arms and why each is in the design")

    report.p("""
        Referenced from Section 3.2, which argues why four arms are needed rather
        than two.
    """)
    report.table(
        ["Arm", "Configuration", "Why it is in the design"],
        [
            ["A", "One model request, no tools, no agents, no protocols",
             "Control. Establishes what the tool layer buys, and what a plan looks "
             "like when nothing in it was retrieved."],
            ["B", "Six roles, naive configuration as first implemented",
             "The starting point. Its cost is what motivated the pivot, so removing "
             "it would hide the reasoning."],
            ["C", "Six roles, tuned: one narrow tool each, distilled results, "
                  "concurrent execution, shorter prompts",
             "The fair baseline. Answers the objection that the multi-agent arm lost "
             "through misconfiguration."],
            ["D", "Three roles; retrieval in ordinary Python",
             "The proposed design. The claim under test."],
        ],
        "The four arms and the role each plays in the argument.",
        widths=[0.5, 2.6, 3.2],
    )

    # ---------------------------------------------------------------- M
    _appendix(report, "K", "Experimental design")

    report.p("""
        Referenced from Section 6.1, which argues what each experiment can and
        cannot support.
    """)
    report.table(
        ["#", "Experiment and question", "Coverage", "Cost to run"],
        [
            ["E1", "Four-arm comparison: what does each architecture cost per trip, "
                   "and is its output grounded?",
             f"{val(coverage['scenarios_measured'])} of "
             f"{val(coverage['scenarios_designed'])} scenarios, "
             f"{val(coverage['repeats_per_arm'])} run each",
             "Model quota; responses replayed"],
            ["E2", "Token decomposition: where does each architecture's spend go?",
             "E1's records", "None"],
            ["E3", "Tuning ablation: how much of the multi-agent penalty is "
                   "implementation rather than architecture?",
             "E1's records", "None"],
            ["E4", "Conformance audit: does the protocol layer behave as the design "
                   "claims?",
             "9 executable checks", "None — no network, no model"],
            ["E5", "Feasibility gate: does it refuse budgets that cannot buy the "
                   "trip, and is its cost model externally valid?",
             f"All {val(coverage['scenarios_designed'])} scenarios",
             "None — no network, no model"],
        ],
        "Experimental design. Three of five cost nothing to run, which is why they "
        "cover the full scenario set while E1 does not.",
        widths=[0.35, 3.0, 1.35, 1.6],
        font_pt=9,
    )

    # ---------------------------------------------------------------- K
    _appendix(report, "L", "Threats to validity, with remedies")

    report.p("""
        Referenced from Section 6.7, which gives each threat and its effect. This
        appendix adds what would resolve it, ordered as in the body.
    """)
    report.table(
        ["Threat", "Type", "Effect on the claims", "What would resolve it"],
        [
            ["One scenario, run once", "Internal",
             "No variance estimate; small differences between arms cannot be separated "
             "from noise, though order-of-magnitude ones can",
             "Repeat runs for a confidence interval, then the remaining scenarios for "
             "generality. The first needs no API quota"],
            ["Naive arm observed varying 19-23 requests in development notes",
             "Internal",
             "Quantifies the noise informally and confirms it is smaller than the gap "
             "it would need to close",
             "Recording repeats rather than relying on a note made at the time"],
            ["Retrieval is replayed from disk", "Internal",
             "Latency understates a live run; the direct arm's retrieval phase reads as "
             "near zero",
             "A live timing pass once quota permits, reported separately"],
            ["Results come from one model", "External",
             "Cost tracks this model's input-to-output price ratio; a flatter ratio "
             "would compress the differences",
             "Re-running the harness against a second provider; the client layer is "
             "already provider-agnostic"],
            ["Scenarios are author-written", "External",
             "Phrasing may be easier to parse than genuine user text",
             "Requests collected from real users, which needs ethical approval"],
            ["The cost model covers about sixty cities", "External",
             "Destinations outside it fall back to mid-tier defaults; all twenty "
             "scenarios happen to be inside it",
             "Deriving price tiers from live data rather than a fixed table"],
            ["Groundedness is recall of retrieved entities", "Construct",
             "Measures whether a plan was built from real data, not whether the "
             "options chosen were good",
             "Preference judgements from participants ranking itineraries"],
            ["Entity matching is guessable", "Construct",
             "Cannot carry a claim on its own",
             "Already mitigated by reporting the two signals separately and letting "
             "price matching carry the claim"],
            ["The author designed, built, measured and interpreted everything",
             "Construct",
             "Experimenter bias, partly offset by executable checks whose outcome was "
             "not chosen",
             "Independent replication from the committed response cache, which needs "
             "no credentials"],
        ],
        "Threats to validity, their effect and their remedies.",
        widths=[1.5, 0.6, 2.1, 2.1],
        font_pt=8,
    )

    # ---------------------------------------------------------------- I
    # ---------------------------------------------------------------- N
    _appendix(report, "M", "Risk analysis and the risk register")

    quota = measured.api_quota()["apis"]
    cache = measured.api_cache_stats()
    # The quota reading stores its counters as strings, because that is how
    # RapidAPI sends the headers they came from. val() formats numbers.
    def _counts(entry):
        return {k: int(v) for k, v in entry.items()
                if k in ("remaining", "limit") and str(v).strip().isdigit()}

    flights = _counts(next(v for v in quota.values() if "flight" in v["name"]))
    hotels = _counts(next(v for v in quota.values() if "hotel" in v["name"]))
    calls_d = measured.api_calls_per_arm()["arms"]["D"]

    report.p("""
        Signposted from Section 3.6. Risks are recorded here with what was done about
        them and what then happened, because a register listing only intentions is
        untestable. Likelihood and impact are the values assigned at the start of the
        project; the final column is the outcome, and three of these risks occurred.
    """)

    report.p(f"""
        The binding risk was never technical difficulty. It was the monthly request
        allowance on the travel APIs: {val(flights['limit'])} flight searches and
        {val(hotels['limit'])} hotel searches, on free tiers that cannot be topped up
        and reset only at the end of a billing cycle. One flight search costs two
        requests, because the provider's endpoint is asynchronous and has to be
        polled for the fares. A single evaluated scenario therefore consumes about
        {val(calls_d['total_http'] + 1)} requests through the shipped arm, and far
        more through the agent-driven arms, where a reasoning loop decides how many
        calls to make and made {val(measured.api_calls_per_arm()['arms']['B']['model_calls'])}
        model requests on the run recorded here.
    """)

    report.p(f"""
        The consequence is that quota exhaustion is not a delay but a hard stop of up
        to a month, arriving without warning in the middle of a measurement. Two
        controls were built before the arms were: every HTTP call passes through a
        record-and-replay layer, so a response is bought once and reused for ever, and
        a hard ceiling on live calls per process fails the run loudly rather than
        spending an allowance it cannot recover. {val(cache['entries'])} responses are
        committed, which is why the whole evaluation replays from disk with no
        credentials, and why the figures in this dissertation can be reproduced by a
        marker who has no API keys at all.
    """)

    report.p(f"""
        The controls worked and the risk still bit. At the last reading the flight
        allowance stood at {val(flights['remaining'])} of {val(flights['limit'])} and
        the hotel allowance at {val(hotels['remaining'])} of {val(hotels['limit'])},
        and recording all {val(coverage['scenarios_designed'])} designed scenarios
        needs more than one monthly cycle. Coverage of the cost comparison is
        therefore {val(coverage['scenarios_measured'])} scenario, stated as such in
        the abstract, in Section 6.1 and on every chart rather than smoothed over.
        That is the honest residual: the mitigation protected reproducibility, not
        breadth, and no amount of caching creates requests that were never made.
    """)

    report.table(
        ["Risk", "Likelihood", "Impact", "Mitigation built", "What actually happened"],
        [
            ["Travel API monthly allowance exhausted mid-measurement",
             "High", "High",
             "Record-and-replay of every HTTP call; hard per-process ceiling on live "
             "calls; quota read from response headers and committed to a file",
             "OCCURRED. Both allowances were fully spent during development. The cache "
             f"({val(cache['entries'])} responses) kept every result reproducible, but "
             f"coverage of the cost comparison is {val(coverage['scenarios_measured'])} "
             f"of {val(coverage['scenarios_designed'])} scenarios"],

            ["A single accidental run drains a month's allowance",
             "Medium", "High",
             "TRIP_PLANNER_MAX_LIVE_CALLS refuses the call rather than spending it; "
             "replay is the default mode for every demonstration",
             "Prevented, then nearly caused anyway by a free price lookup that "
             "resolved a city name through a live endpoint. One hotel request was "
             "spent before a test was added to forbid it (Section 5.6)"],

            ["Model provider withdraws or changes the model mid-project",
             "Medium", "High",
             "One module holds the model string and the request-shape compatibility "
             "layer, so a change is edited in a single place",
             "OCCURRED. The model named in the proposal was withdrawn. The arms were "
             "restored by editing one constant; the affected requests are counted and "
             "reported rather than silently repaired"],

            ["Tool calls fail silently and the model answers from memory",
             "Medium", "High",
             "Groundedness measured as recall of retrieved entities, so a plan built "
             "without data scores low even when it reads well",
             "OCCURRED on the first end-to-end run: every tool call was failing and "
             "the itinerary looked complete. This is why the metric exists "
             "(Section 5.2)"],

            ["Reported numbers drift away from the measured data",
             "Medium", "High",
             "Every figure interpolated from the results files at build time, and a "
             "perturbation test that corrupts the data and fails if any printed "
             "number does not move",
             "Controlled. The proof runs on every build and is reported in "
             "Appendix N"],

            ["Credentials committed to version control or printed in logs",
             "Medium", "High",
             "Keys confined to an ignored .env; request headers excluded from the "
             "response cache; third-party loggers raised above INFO because the model "
             "key travels in the URL",
             "Controlled. No credential appears in any tracked file or committed "
             "response"],

            ["Scope too large for one part-time project",
             "High", "Medium",
             "Four architectures reduced to the minimum that still isolates the "
             "variable; questions answerable without quota answered in full",
             "Managed. Protocol conformance and the feasibility gate were evaluated "
             f"across all {val(coverage['scenarios_designed'])} scenarios because "
             "neither needs the network, and both produced negative findings"],

            ["Single point of failure: one laptop, one author",
             "Medium", "Medium",
             "Everything in version control; the evaluation reproducible from the "
             "committed cache with no credentials",
             "Controlled, with a residual: the repository is the only copy until it "
             "is pushed to a remote"],
        ],
        "Risk register: the assessment made at the start, the control built for it, "
        "and the outcome. Three of the eight risks occurred.",
        widths=[1.35, 0.62, 0.55, 1.9, 1.9],
        font_pt=7.5,
    )

    _appendix(report, "N", "Provenance of the reported results")

    provenance = measured.provenance()
    coverage = measured.coverage()
    report.table(
        ["Field", "Value"],
        [
            ["Model", provenance.get("model", "unknown")],
            ["API layer mode", provenance.get("api_mode", "unknown")],
            ["Result set status", coverage["status"]],
            ["Scenarios measured", f"{val(coverage['scenarios_measured'])} of "
                                   f"{val(coverage['scenarios_designed'])} "
                                   f"({val(coverage['coverage_pct'], '{:.1f}')}%)"],
            ["Scenario identifiers", ", ".join(coverage["scenario_ids"])],
            ["Repeat runs per arm", val(coverage["repeats_per_arm"])],
            ["Recorded API responses", val(cache["entries"])],
            ["Live API calls during the recorded run",
             val(provenance.get("api_cache", {}).get("live_calls", 0))],
            ["Commits", val(measured.git_stats()["commits"])],
            ["First commit", str(measured.git_stats()["first_commit"])],
            ["Last commit", str(measured.git_stats()["last_commit"])],
        ],
        "Provenance of every quantitative result in this dissertation.",
        widths=[2.0, 2.6],
    )

    report.p("""
        The comparison was run with the API layer in replay mode and zero live calls,
        which is why the reported figures can be reproduced exactly rather than
        approximately. A live run would return different fares and therefore
        different groundedness scores; the recorded responses fix the ground truth so
        that the architectures are compared against identical data.
    """)
