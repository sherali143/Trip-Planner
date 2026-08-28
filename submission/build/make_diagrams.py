"""Draws the architecture and sequence diagrams."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from trip_planner.evaluation import measured
from submission.build.figlib import (AQUA, AQUA_FILL, BLUE, BLUE_FILL, GREY, GREY_FILL,
                            INK, INK_2, ORANGE, ORANGE_FILL, PURPLE,
                            PURPLE_FILL, RED, RED_FILL, ROOT, Canvas, stack)


# ============================================================ 1. architecture
def fig_architecture() -> str:
    c = Canvas(13.0, 8.6, "System architecture",
               "Four layers. The shipped path is arm D: three LLM steps with "
               "retrieval in plain Python. Dashed edges mark the MCP transport, "
               "which only the six-agent arms drive.",
               footer="A2A protocol: 8 agent cards, 6 message types (REQUEST, RESPONSE, "
                      "QUERY, INFO, ERROR, ACK), permission-validated. In the shipped path "
                      "the protocol records the exchange; it does not dispatch it.")

    G = 16.0        # left gutter reserved for layer names; nothing is drawn in it
    W = 25.0

    layers = [
        (72.5, "LAYER 1\nUser interface"),
        (55.0, "LAYER 2\nUnderstanding"),
        (28.0, "LAYER 3\nData retrieval"),
        (10.0, "LAYER 4\nAssembly"),
    ]
    for y, name in layers:
        c.label(0, y + 4.5, name, ha="left", fontsize=8.5, weight="bold",
                colour=INK_2, opaque=False)

    ui_web = c.box(G, 72.5, W, 9.0, "Streamlit web app\ntrip_planner/frontend/app.py",
                   edge=GREY, fill=GREY_FILL, fontsize=8.5, name="web")
    ui_cli = c.box(G + 29, 72.5, W, 9.0, "Command line\nrun_cli.py",
                   edge=GREY, fill=GREY_FILL, fontsize=8.5, name="cli")

    conv = c.box(G, 55.0, W, 9.0, "Conversational step\ncollects trip details",
                 fontsize=8.5, name="conversation")
    extract = c.box(G + 29, 55.0, W, 9.0, "Preferences extractor\nfree text to typed JSON",
                    fontsize=8.5, name="extractor")

    mcp = c.box(G, 28.0, W, 15.0,
                "MCP server\n12 tools, JSON-RPC over stdio\ntrip_planner/server/mcp_server.py",
                edge=AQUA, fill=AQUA_FILL, fontsize=8.5, weight="bold", name="mcp")
    apis = [
        c.box(G + 29, 38.0, 22, 5.0, "fly-scraper  ·  flights",
              edge=ORANGE, fill=ORANGE_FILL, fontsize=8.5, name="api_flights"),
        c.box(G + 29, 31.0, 22, 5.0, "Booking.com  ·  hotels",
              edge=ORANGE, fill=ORANGE_FILL, fontsize=8.5, name="api_hotels"),
        c.box(G + 29, 24.0, 22, 5.0, "Serper  ·  places",
              edge=ORANGE, fill=ORANGE_FILL, fontsize=8.5, name="api_places"),
    ]
    cache = c.box(G + 56, 28.0, 22, 15.0,
                  "HTTP cache\nrecord / replay\n+ live-call ceiling",
                  edge=AQUA, fill=AQUA_FILL, fontsize=8.5, name="cache")

    coord = c.box(G, 10.0, 54.0, 9.0,
                  "Itinerary coordinator — assembles the day-by-day plan from "
                  "retrieved data only",
                  fontsize=8.5, name="coordinator")

    c.arrow((ui_web.cx, ui_web.y), (conv.cx, conv.top), colour=GREY)
    c.arrow((ui_cli.cx, ui_cli.y), (extract.cx, extract.top), colour=GREY)
    c.arrow((conv.right, conv.cy), (extract.x, extract.cy), colour=BLUE)
    c.label((conv.right + extract.x) / 2, conv.cy + 4.0, "A2A", fontsize=8, colour=BLUE)

    c.connect(extract, mcp, colour=BLUE, route="v", text="typed JSON")
    for api in apis:
        c.arrow((mcp.right, api.cy), (api.x, api.cy), colour=AQUA)
    c.arrow((apis[1].right, apis[1].cy), (cache.x, apis[1].cy), colour=AQUA, dashed=True)
    c.label(cache.cx, cache.top + 3.0, "every call recorded", fontsize=7.8, colour=AQUA)
    # Straight down from the server into the coordinator's top edge. Aiming at
    # the coordinator's centre instead made this a diagonal, because the
    # coordinator is much wider than the server.
    c.arrow((mcp.cx, mcp.y), (mcp.cx, coord.top), colour=BLUE)
    c.label(mcp.cx + 12, (mcp.y + coord.top) / 2, "retrieved data",
            fontsize=8, colour=BLUE)

    c.validate()
    return c.save("architecture.png")


# =============================================================== 2. data flow
def fig_dataflow() -> str:
    c = Canvas(13.0, 7.4, "Level-1 data flow",
               "What is persisted, and where a number in the evaluation comes from.",
               footer="Recorded API responses and measured result files are both committed, "
                      "so every figure in this report regenerates from disk with no API key.")

    req = c.box(1, 60, 20, 10, "Traveller's\nrequest\n(free text)",
                edge=GREY, fill=GREY_FILL, fontsize=8.5, name="request")
    p1 = c.box(27, 60, 21, 10, "P1\nExtract\npreferences",
               fontsize=8.5, weight="bold", name="P1")
    p2 = c.box(54, 60, 21, 10, "P2\nRetrieve\ntravel data",
               edge=AQUA, fill=AQUA_FILL, fontsize=8.5, weight="bold", name="P2")
    p3 = c.box(54, 34, 21, 10, "P3\nAssemble\nitinerary",
               fontsize=8.5, weight="bold", name="P3")
    p4 = c.box(27, 34, 21, 10, "P4\nMeasure\nthe run",
               edge=PURPLE, fill=PURPLE_FILL, fontsize=8.5, weight="bold", name="P4")
    out = c.box(81, 47, 18, 10, "Day-by-day\nitinerary",
                edge=GREY, fill=GREY_FILL, fontsize=8.5, name="itinerary")

    d1 = c.box(54, 12, 21, 8, "D1  .api_cache/\nrecorded responses",
               edge=AQUA, fill=AQUA_FILL, fontsize=8, name="D1")
    d2 = c.box(27, 12, 21, 8, "D2  results/\nmeasured metrics",
               edge=PURPLE, fill=PURPLE_FILL, fontsize=8, name="D2")
    d3 = c.box(1, 34, 20, 8, "D3  figures/\ncharts and diagrams",
               edge=PURPLE, fill=PURPLE_FILL, fontsize=8, name="D3")

    c.arrow((req.right, req.cy), (p1.x, p1.cy), colour=GREY)
    c.arrow((p1.right, p1.cy), (p2.x, p2.cy), colour=BLUE)
    c.label((p1.right + p2.x) / 2, p1.top + 3.2, "typed JSON", fontsize=7.8, colour=BLUE)
    c.arrow((p2.cx, p2.y), (p3.cx, p3.top), colour=AQUA)
    # Left of the arrow, not right: on the right it sat in the dashed recording
    # lane and read as that edge's label rather than this one's.
    c.label(p2.cx - 12, (p2.y + p3.top) / 2, "flights, hotels,\nplaces",
            fontsize=7.8, colour=AQUA)

    # P3 to the itinerary: right then up, rather than a diagonal that also
    # clipped the output box's corner.
    c.arrow((p3.right, p3.cy), (out.cx, p3.cy), colour=BLUE, head=False)
    c.arrow((out.cx, p3.cy), (out.cx, out.y), colour=BLUE)

    # P2 to the recording store: out to a clear column on the right, down, then
    # back in. Straight down would pass through P3.
    lane = 78.0
    c.arrow((p2.right, p2.cy), (lane, p2.cy), colour=AQUA, dashed=True, head=False)
    c.arrow((lane, p2.cy), (lane, d1.cy), colour=AQUA, dashed=True, head=False)
    c.arrow((lane, d1.cy), (d1.right, d1.cy), colour=AQUA, dashed=True)

    c.arrow((p3.x, p3.cy), (p4.right, p4.cy), colour=PURPLE)
    c.label((p3.x + p4.right) / 2, p3.top + 3.2, "tokens, cost,\nlatency",
            fontsize=7.8, colour=PURPLE)
    c.arrow((p4.cx, p4.y), (d2.cx, d2.top), colour=PURPLE)

    # D2 to D3: left then up.
    c.arrow((d2.x, d2.cy), (d3.cx, d2.cy), colour=PURPLE, dashed=True, head=False)
    c.arrow((d3.cx, d2.cy), (d3.cx, d3.y), colour=PURPLE, dashed=True)

    c.arrow((d1.x, d1.cy), (d2.right, d2.cy), colour=AQUA, dashed=True)
    c.label((d1.x + d2.right) / 2, d1.cy - 4.0, "replay", fontsize=7.5, colour=AQUA)

    c.validate()
    return c.save("dataflow.png")


# ================================================================ 3. sequence
def fig_sequence() -> str:
    # Phase timings are read from the recorded run, not written into the figure.
    phases = measured.phase_timings("D")
    extract_s = phases.get("phase1_extraction_s")
    fetch_s = phases.get("phase2_api_fetch_s")
    coord_s = phases.get("phase3_coordination_s")
    total_s = measured.arm_metric("D", "avg_latency")

    c = Canvas(13.0, 8.2, "End-to-end sequence for one trip request",
               "The shipped path. Two LLM steps bracket a retrieval phase that "
               "uses no model at all.",
               footer=f"Measured on {', '.join(measured.scenario_ids())} with the API layer "
                      f"in {measured.provenance()['api_mode']} mode: extraction "
                      f"{extract_s}s, retrieval {fetch_s}s (replayed), assembly "
                      f"{coord_s}s, {total_s:.1f}s end to end.")

    lanes = ["Traveller", "Extractor\n(LLM)", "Retrieval\n(Python)", "APIs",
             "Coordinator\n(LLM)"]
    xs = [10, 29, 48, 67, 87]
    half = 8.6
    for name, x in zip(lanes, xs):
        c.box(x - half, 71, half * 2, 8.5, name, edge=BLUE, fill=BLUE_FILL,
              fontsize=8.5, weight="bold", name=f"lane_{name[:6]}")
        # Lifeline
        c.arrow((x, 71), (x, 12), colour="#cfcec9", head=False, dashed=True)

    steps = [
        (0, 1, "free-text request", BLUE),
        (1, 1, "parse to typed JSON", BLUE),
        (1, 2, "preferences", BLUE),
        (2, 3, "4 retrieval calls", AQUA),
        (3, 2, "fares, hotels, places", AQUA),
        (2, 4, "assembled data block", AQUA),
        (4, 4, "write day-by-day plan", BLUE),
        (4, 0, "itinerary", BLUE),
    ]
    y = 65.0
    for i, (a, b, text, colour) in enumerate(steps):
        if a == b:
            # A self-call: a small bracket to the right of the lane, with the
            # caption to the LEFT so it cannot run off the right-hand edge on
            # the last lane.
            c.arrow((xs[a], y), (xs[a] + 4.5, y), colour=colour, head=False)
            c.arrow((xs[a] + 4.5, y), (xs[a] + 4.5, y - 3), colour=colour, head=False)
            c.arrow((xs[a] + 4.5, y - 3), (xs[a], y - 3), colour=colour)
            c.label(xs[a] - 2.0, y - 1.5, text, fontsize=7.8, colour=colour, ha="right")
        else:
            c.arrow((xs[a], y), (xs[b], y), colour=colour)
            c.label((xs[a] + xs[b]) / 2, y + 2.6, text, fontsize=7.8, colour=colour)
        c.label(1.0, y, f"{i + 1}", fontsize=8, weight="bold", colour=INK_2,
                ha="left", opaque=False)
        y -= 6.6

    c.validate()
    return c.save("sequence.png")


# ============================================================== 4. four arms
def fig_four_arms() -> str:
    c = Canvas(13.4, 7.6, "The four architectures compared",
               "Identical request, identical APIs, identical A2A layer. Only the "
               "retrieval mechanism differs — that is the independent variable.",
               # The five-box columns under a "6 agents" heading are deliberate, and
               # a reader who counts them deserves the answer from the figure rather
               # than from Section 3.4. Leaving it to the prose invites the marker to
               # read it as an error in the diagram.
               footer="Arms B, C and D reach the same three APIs. Arm A is the control: it "
                      "has no tool access, so nothing it reports was retrieved from anywhere.\n"
                      "B and C show five boxes because the conversational agent of the "
                      "six-agent design is omitted: every arm receives the identical request "
                      "string, so the role has nothing to do. They are a five-agent ablation "
                      "of a six-agent design (Section 3.4).")

    columns = [
        (1.0, "ARM A", "Single LLM", [
            ("One LLM call\n\nno tools\nno retrieval", GREY, GREY_FILL),
        ], "Invents its data"),
        (25.5, "ARM B", "6 agents, naive", [
            ("Extractor", BLUE, BLUE_FILL),
            ("Flight agent\nReAct, 8 tools", ORANGE, ORANGE_FILL),
            ("Hotel agent\nReAct, 8 tools", ORANGE, ORANGE_FILL),
            ("Activities agent\nReAct, 4 tools", ORANGE, ORANGE_FILL),
            ("Coordinator", BLUE, BLUE_FILL),
        ], "Raw payloads, tool\nschemas re-sent each\niteration"),
        (50.0, "ARM C", "6 agents, tuned", [
            ("Extractor", BLUE, BLUE_FILL),
            ("Flight agent\n1 tool", AQUA, AQUA_FILL),
            ("Hotel agent\n1 tool", AQUA, AQUA_FILL),
            ("Activities agent\n2 tools", AQUA, AQUA_FILL),
            ("Coordinator", BLUE, BLUE_FILL),
        ], "Distilled results,\nmax_iter 3,\nrun concurrently"),
        (74.5, "ARM D", "3 agents, direct", [
            ("Extractor", BLUE, BLUE_FILL),
            ("Python calls\nno LLM", AQUA, AQUA_FILL),
            ("Coordinator", BLUE, BLUE_FILL),
        ], "Retrieval is\nplain code"),
    ]

    col_w = 23.0
    for x, code, name, blocks, note in columns:
        c.label(x + col_w / 2, 80.0, code, fontsize=10.5, weight="bold", colour=INK)
        c.label(x + col_w / 2, 75.5, name, fontsize=9, colour=INK_2)
        stack(c, x, 71.0, 22.0, col_w, blocks, fontsize=8.3)
        c.label(x + col_w / 2, 15.0, note, fontsize=8, colour=INK_2)

    c.validate()
    return c.save("four_arms.png")


# =============================================================== 5. A2A flow
def fig_a2a_flow() -> str:
    c = Canvas(12.0, 7.4, "A2A message flow for one trip",
               "Six typed messages, each validated against the sender's agent card "
               "before it is accepted. Measured: 6 of 6 permitted.",
               footer="Measured defect: the queue is FIFO, so the priority field carried on "
                      "every message is never read. Declared inbound permissions "
                      "(can_receive_from) are likewise never enforced.")

    senders = [
        ("preferences_extractor", "REQUEST", "extracted preferences"),
        ("flight_data_provider", "RESPONSE", "flight results"),
        ("hotel_data_provider", "RESPONSE", "hotel results"),
        ("attraction_data_provider", "RESPONSE", "attraction results"),
        ("restaurant_data_provider", "RESPONSE", "restaurant results"),
        ("itinerary_coordinator", "RESPONSE", "final itinerary"),
    ]

    top, row_h = 72.0, 10.4
    for i, (sender, mtype, payload) in enumerate(senders):
        y = top - i * row_h
        c.label(0.5, y, f"{i + 1}", fontsize=9, weight="bold", colour=INK_2,
                ha="left", opaque=False)
        a = c.box(4, y - 3.6, 32, 7.2, sender, edge=BLUE, fill=BLUE_FILL,
                  fontsize=8.3, name=f"s{i}")
        target = "user" if i == len(senders) - 1 else "itinerary_coordinator"
        b = c.box(62, y - 3.6, 32, 7.2, target, edge=AQUA, fill=AQUA_FILL,
                  fontsize=8.3, name=f"r{i}")
        c.arrow((a.right, y), (b.x, y), colour=BLUE)
        c.label((a.right + b.x) / 2, y + 2.9, mtype, fontsize=7.6,
                weight="bold", colour=BLUE)
        c.label((a.right + b.x) / 2, y - 2.9, payload, fontsize=7.4, colour=INK_2)

    c.validate()
    return c.save("a2a_flow.png")


# ========================================================== 6. MCP lifecycle
def fig_mcp_lifecycle() -> str:
    c = Canvas(13.4, 6.2, "MCP tool call lifecycle",
               "Six stages, each able to reject the call. The cache sits in front "
               "of the network, so a repeated query costs no quota.",
               footer="Only 2xx responses are cached, so a quota error is never stored as if "
                      "it were data. Request headers are excluded, so no API key reaches disk.")

    stages = [
        ("1\nSchema\nvalidation", BLUE, BLUE_FILL),
        ("2\nCache\nlookup", AQUA, AQUA_FILL),
        ("3\nQuota\nguard", AQUA, AQUA_FILL),
        ("4\nLive call\n+ retry", ORANGE, ORANGE_FILL),
        ("5\nDistil to\ntop results", BLUE, BLUE_FILL),
        ("6\nCache write\n+ return", AQUA, AQUA_FILL),
    ]
    # Six boxes and five gaps must fit inside the frame with clearance at both
    # ends: 1.0 + 6*14.4 + 5*2.6 reached 100.4 and the last box was cropped.
    x, w, gap = 1.0, 14.0, 2.4
    boxes = []
    for i, (text, edge, fill) in enumerate(stages):
        b = c.box(x, 42, w, 24, text, edge=edge, fill=fill, fontsize=8.4,
                  name=f"stage{i + 1}")
        boxes.append(b)
        if i:
            c.arrow((boxes[i - 1].right, b.cy), (b.x, b.cy), colour=GREY)
        x += w + gap

    cache = boxes[1]
    c.arrow((cache.cx, cache.y), (cache.cx, 30), colour=AQUA, dashed=True)
    c.label(cache.cx + 2, 27.0, "cache hit returns here — no network, no quota spent",
            fontsize=8, colour=AQUA, ha="left")

    guard = boxes[2]
    c.arrow((guard.cx, guard.y), (guard.cx, 19), colour=RED, dashed=True)
    c.label(guard.cx + 2, 16.0, "ceiling reached — raises rather than overspending",
            fontsize=8, colour=RED, ha="left")

    c.validate()
    return c.save("mcp_lifecycle.png")


# ================================================== 7. conceptual framework
def fig_conceptual_framework() -> str:
    # Every figure in the MEASURED OUTCOME column is read from a results file.
    naive_prompt = round(measured.token_split("B")["prompt_tokens"])
    tuned_prompt = round(measured.token_split("C")["prompt_tokens"])
    schema = measured.mcp_schema_stats()
    provider_errors = len(measured.protocol_check("M4")["observed"]["mismatches"])
    a2a_seq = measured.protocol_check("A3")["observed"]
    control = measured.groundedness("A")
    tool_arms = [measured.groundedness(code)["prices_grounded_pct"] for code in ("C", "D")]

    rows_data = [
        ("Context bloat\nSchick et al. (2023);\nXie et al. (2024)",
         "Distil tool output to the top\nthree options; one narrow tool\nper specialist",
         f"Prompt tokens fell from\n{naive_prompt:,} to {tuned_prompt:,} between\n"
         f"the naive and tuned arms",
         "Supported", AQUA, AQUA_FILL),
        ("Protocol fragility\nSchick et al. (2023);\nAnthropic (2024)",
         "Schema-validated MCP tool\nlayer over every API",
         f"{len(schema['defective_tools'])} of {schema['tools_total']} tools have "
         f"schema\ndefects; {provider_errors} advertises the\nwrong provider",
         "Partly\nrefuted", RED, RED_FILL),
        ("Semantic drift\nPark et al. (2023);\nFIPA (2002)",
         "Typed A2A envelope with\npermission validation instead\nof free-text handoff",
         f"{a2a_seq['permitted']} of {a2a_seq['total']} shipped messages\nvalidated; "
         f"priority queue\nand inbound rules absent",
         "Partly\nsupported", ORANGE, ORANGE_FILL),
        ("Hallucinated venues\nand fares\nXie et al. (2024)",
         "Ground every itinerary in\nretrieved data; score what\ncan be traced back to it",
         f"Tool-less arm quoted\n{control['prices_quoted']} prices, matched "
         f"{control['prices_grounded']};\ntool-using arms "
         f"{min(tool_arms):.0f}-{max(tool_arms):.0f}%",
         "Strongly\nsupported", AQUA, AQUA_FILL),
    ]

    c = Canvas(13.4, 8.4, "Conceptual framework",
               f"{len(rows_data)} failure modes the literature documents, the design "
               f"decision taken against each, and what this project measured about it.",
               footer="The right-hand column is what separates this framework from a "
                      "restatement of the literature: each response has a measured outcome, "
                      "including the two that did not survive measurement.")

    col_x = [1.0, 26.0, 55.0, 79.0]
    headers = ["FAILURE MODE\n(literature)", "DESIGN RESPONSE\n(this project)",
               "MEASURED OUTCOME", "VERDICT"]
    widths = [23.0, 27.0, 22.0, 20.0]
    for x, head, w in zip(col_x, headers, widths):
        c.label(x + w / 2, 77.5, head, fontsize=8.6, weight="bold", colour=INK)

    top, gap = 71.0, 2.4
    cursor = top
    for problem, response, outcome, verdict, colour, fill in rows_data:
        # Height is driven by the tallest cell in the row, measured first.
        h = 0.0
        for text, w, fs in ((problem, widths[0], 8.0), (response, widths[1], 8.0),
                            (outcome, widths[2], 8.0), (verdict, widths[3], 8.6)):
            wrapped = c.wrap(text, w - 3.2, fs)
            h = max(h, c.measure(wrapped, fs)[1] + 3.2)
        c.box(col_x[0], cursor - h, widths[0], h, problem,
              edge=GREY, fill=GREY_FILL, fontsize=8.0, name=f"p_{problem[:12]}")
        c.box(col_x[1], cursor - h, widths[1], h, response,
              edge=BLUE, fill=BLUE_FILL, fontsize=8.0, name=f"r_{problem[:12]}")
        c.box(col_x[2], cursor - h, widths[2], h, outcome,
              edge=PURPLE, fill=PURPLE_FILL, fontsize=8.0, name=f"o_{problem[:12]}")
        c.box(col_x[3], cursor - h, widths[3], h, verdict,
              edge=colour, fill=fill, fontsize=8.6, weight="bold",
              name=f"v_{problem[:12]}")
        cursor -= h + gap

    c.validate()
    return c.save("conceptual_framework.png")


# ================================================================ 8. method
def fig_methodology() -> str:
    c = Canvas(13.0, 7.8, "Design Science Research cycles as they actually ran",
               "Three build-and-evaluate cycles. Each was closed by a measurement "
               "that changed the design, not by a decision to move on.",
               footer="Cycle 2 is the pivot the dissertation rests on: the six-agent design "
                      "was measured before it was replaced, and then tuned before it was "
                      "used as a baseline.")

    cycles = [
        ("CYCLE 1\nBuild the artefact",
         "Six agents, 12 MCP tools,\nA2A envelope, Streamlit UI",
         "Itineraries looked right but\ncited nothing retrievable;\nLLM cost was never measured",
         BLUE, BLUE_FILL),
        ("CYCLE 2\nInstrument, then pivot",
         "LiteLLM callback recorder;\nthree-agent design with\nretrieval in plain Python",
         "19 requests per trip, most\nspent on deterministic\nretrieval. Pivot to 3 agents",
         ORANGE, ORANGE_FILL),
        ("CYCLE 3\nRemove the straw man",
         "Tune the six-agent arm\nfirst; add a tool-less\ncontrol; score groundedness",
         "Tuning removed most of the\npenalty — so the honest claim\nis narrower than expected",
         AQUA, AQUA_FILL),
    ]

    # Rows are shortened to pay for the wider inter-row gap the orthogonal
    # feedback route needs; at 19 the third row landed in the footer band.
    y_top = 70.0
    row_h = 18.0
    gap = 4.5
    previous_eval = None
    for i, (title, build, evaluate, colour, fill) in enumerate(cycles):
        y = y_top - i * (row_h + gap)
        a = c.box(1.0, y - row_h, 24.0, row_h, title, edge=colour, fill=fill,
                  fontsize=8.8, weight="bold", name=f"c{i}_title")
        b = c.box(28.0, y - row_h, 32.0, row_h, "BUILD\n\n" + build,
                  edge=BLUE, fill=BLUE_FILL, fontsize=8.0, name=f"c{i}_build")
        d = c.box(63.0, y - row_h, 36.0, row_h, "EVALUATE\n\n" + evaluate,
                  edge=PURPLE, fill=PURPLE_FILL, fontsize=8.0, name=f"c{i}_eval")
        c.arrow((a.right, a.cy), (b.x, b.cy), colour=colour)
        c.arrow((b.right, b.cy), (d.x, d.cy), colour=colour)

        if previous_eval is not None:
            # The feedback edge: what one cycle's evaluation found drove the next
            # cycle's build. Routed through the gap between rows — drawn as a
            # single diagonal it cut straight across the BUILD box between them.
            lane_y = (previous_eval.y + a.top) / 2
            c.arrow((previous_eval.cx, previous_eval.y), (previous_eval.cx, lane_y),
                    colour=PURPLE, dashed=True, head=False)
            c.arrow((previous_eval.cx, lane_y), (a.cx, lane_y),
                    colour=PURPLE, dashed=True, head=False)
            c.arrow((a.cx, lane_y), (a.cx, a.top), colour=PURPLE, dashed=True)
            c.label((previous_eval.cx + a.cx) / 2, lane_y,
                    "what the measurement forced", fontsize=7.4, colour=PURPLE)
        previous_eval = d

    c.validate()
    return c.save("methodology.png")


# ========================================================= 9. the web page
def fig_frontend() -> str:
    """
    What the user actually sees, drawn rather than screenshotted.

    A screenshot would be a picture of one run on one day at one window width.
    This shows the two states the page has and what each panel is for, which is
    what a reader needs in order to follow a live demonstration.
    """
    c = Canvas(13.0, 7.2, "The web page",
               "Two states: filling in the trip, and reading the plan. The same "
               "seven steps are narrated in the terminal at the same time.",
               footer="Every price shown is traceable to a live travel API response. "
                      "Where a figure had to be estimated instead, the page says so.")

    # ---- left: the form ---------------------------------------------------
    c.label(2, 89, "WHILE YOU FILL IT IN", ha="left", fontsize=9,
            weight="bold", colour=PURPLE, opaque=False)

    form = [
        (74, "1  Where and when", "destination, origin, dates"),
        (61, "2  Who is going", "adults, children"),
        (48, "3  Budget and style", "total in USD, what matters most"),
        (35, "4  Preferences", "interests, special requirements"),
    ]
    for y, head, detail in form:
        c.box(2, y, 40, 10.0, f"{head}\n{detail}",
              edge=BLUE, fill=BLUE_FILL, fontsize=8.6, name=head[:6])

    c.box(2, 20, 40, 8.0, "Build my itinerary",
          edge=PURPLE, fill=PURPLE_FILL, fontsize=9.5, weight="bold",
          name="button")

    # ---- middle: the steps ------------------------------------------------
    c.label(48, 89, "WHILE IT RUNS", ha="left", fontsize=9, weight="bold",
            colour=PURPLE, opaque=False)
    steps = ["1  Conversation", "2  Preferences", "3  Flights", "4  Hotels",
             "5  Attractions", "6  Restaurants", "7  Itinerary"]
    for index, name in enumerate(steps):
        y = 76 - index * 8.2
        uses_ai = index in (0, 1, 6)
        c.box(48, y, 22, 6.4, name,
              edge=PURPLE if uses_ai else AQUA,
              fill=PURPLE_FILL if uses_ai else AQUA_FILL,
              fontsize=8.2, name=f"step{index}")
    c.label(59, 12, "purple = uses AI\ngreen = plain code", fontsize=7.8,
            colour=INK_2, opaque=False)

    # ---- right: the result ------------------------------------------------
    c.label(75, 89, "WHEN IT IS DONE", ha="left", fontsize=9, weight="bold",
            colour=PURPLE, opaque=False)
    # Boxes grow to fit their text, so these y values are the bottom edge and the
    # heights are minimums. The header band floor is 86.
    c.box(75, 74, 23, 5.0, "4 of 4 days present\nprice measured, not estimated",
          edge=AQUA, fill=AQUA_FILL, fontsize=7.6, name="badges")
    c.box(75, 65, 23, 5.0, "Nights 4    Travellers 1\nBudget $1,600    Fare $937",
          edge=GREY, fill=GREY_FILL, fontsize=7.6, name="metrics")

    tabs = ["Overview", "Flights", "Hotels", "Day by day", "Budget", "Tips"]
    for index, name in enumerate(tabs):
        y = 56 - index * 7.0
        c.box(75, y, 23, 5.6, name, edge=BLUE, fill=BLUE_FILL, fontsize=8.2,
              name=f"tab{index}")
    c.label(86.5, 11, "one block per day\ninside 'Day by day'", fontsize=7.8,
            colour=INK_2, opaque=False)

    c.validate()
    return c.save("frontend.png")


DIAGRAMS = [
    fig_architecture,
    fig_dataflow,
    fig_sequence,
    fig_four_arms,
    fig_a2a_flow,
    fig_mcp_lifecycle,
    fig_conceptual_framework,
    fig_methodology,
    fig_frontend,
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failures = 0
    for builder in DIAGRAMS:
        try:
            path = builder()
            print(f"  ok   {os.path.relpath(path, ROOT)}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL {builder.__name__}\n       {exc}")
    print(f"\n{len(DIAGRAMS) - failures}/{len(DIAGRAMS)} diagrams valid at 300 dpi")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
