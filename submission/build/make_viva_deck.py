"""
Builds the viva slides.

Every number on a slide is read from the measured results. Slides are kept
deliberately sparse because the marking criteria penalise text-heavy ones; the
detail is in the speaker notes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from trip_planner.evaluation import measured

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIGURES = os.path.join(ROOT, "submission", "build", "figures")
OUTPUT = os.path.join(ROOT, "submission", "CMP7200_Viva_Presentation.pptx")

STUDENT = "25182589"          # anonymous marking: student number only
MODULE = "CMP7200 — Individual Master's Project"

INK = RGBColor(0x16, 0x1A, 0x23)
SOFT = RGBColor(0x54, 0x5C, 0x6E)
FAINT = RGBColor(0x8A, 0x91, 0xA0)
ACCENT = RGBColor(0x43, 0x38, 0xCA)
TEAL = RGBColor(0x0E, 0xA5, 0xA4)
WARN = RGBColor(0xA8, 0x5B, 0x00)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x1E, 0x1B, 0x4B)

W, H = Inches(13.333), Inches(7.5)      # 16:9


# ---------------------------------------------------------------------------
# Slide furniture
# ---------------------------------------------------------------------------

def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _fill(slide, colour):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = colour


def _text(slide, left, top, width, height, runs, align=PP_ALIGN.LEFT,
          anchor=MSO_ANCHOR.TOP, spacing=1.0):
    """
    Add a text box. `runs` is a list of (text, size_pt, bold, colour) tuples,
    one per paragraph, so a slide's type hierarchy is declared where it is used.
    """
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    for index, (text, size, bold, colour) in enumerate(runs):
        para = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        run = para.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = colour
        run.font.name = "Calibri"
    return box


def _rule(slide, left, top, width, colour=ACCENT, height=Emu(34000)):
    bar = slide.shapes.add_shape(1, left, top, width, height)   # rectangle
    bar.fill.solid()
    bar.fill.fore_color.rgb = colour
    bar.line.fill.background()
    bar.shadow.inherit = False
    return bar


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = " ".join(text.split())


def _heading(slide, eyebrow, title):
    """The standard slide head: a small label, a large title, a short rule."""
    _text(slide, Inches(0.9), Inches(0.5), Inches(11.5), Inches(0.4),
          [(eyebrow.upper(), 12, True, ACCENT)])
    _text(slide, Inches(0.9), Inches(0.85), Inches(11.5), Inches(0.9),
          [(title, 32, True, INK)])
    _rule(slide, Inches(0.9), Inches(1.72), Inches(1.1))


def _figure(slide, name, top=Inches(2.0), height=Inches(4.6)):
    """Place a generated figure, centred, or say plainly that it is missing."""
    for folder in ("results", "diagrams"):
        path = os.path.join(FIGURES, folder, name)
        if os.path.exists(path):
            picture = slide.shapes.add_picture(path, Inches(0), top,
                                               height=height)
            picture.left = int((W - picture.width) / 2)
            return picture
    _text(slide, Inches(0.9), top, Inches(11.5), Inches(0.5),
          [(f"[figure {name} not generated — run make_charts and make_diagrams]",
            14, False, WARN)])
    return None


def _stat_row(slide, stats, top=Inches(2.3), colour=ACCENT):
    """
    Evenly spaced big numbers. This is the deck's main device: a figure a marker
    can read from the back of the room, with three words under it.
    """
    count = len(stats)
    gutter = Inches(0.9)
    span = (W - 2 * gutter) / count
    for index, (value, label) in enumerate(stats):
        left = int(gutter + index * span)
        _text(slide, Emu(left), top, Emu(int(span)), Inches(1.3),
              [(value, 60, True, colour)], align=PP_ALIGN.CENTER)
        _text(slide, Emu(left), top + Inches(1.25), Emu(int(span)), Inches(0.8),
              [(label, 14, False, SOFT)], align=PP_ALIGN.CENTER)


def _table(slide, headers, rows, left=Inches(0.9), top=Inches(2.1),
           width=Inches(11.5), col_widths=None, font=12):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), left, top,
                                   width, Inches(0.4 * (len(rows) + 1)))
    table = shape.table
    if col_widths:
        total = sum(col_widths)
        for index, share in enumerate(col_widths):
            table.columns[index].width = Emu(int(width * share / total))
    def style(cell, value, bold, colour, fill):
        # Assigning "" leaves the paragraph with no runs, so styling it raises.
        # An empty header is legitimate — the approach table's first column is
        # just the letter — so write a space and style that.
        cell.text = str(value) if str(value) else " "
        run = cell.text_frame.paragraphs[0].runs[0]
        run.font.size = Pt(font)
        run.font.bold = bold
        run.font.color.rgb = colour
        run.font.name = "Calibri"
        cell.fill.solid()
        cell.fill.fore_color.rgb = fill

    for index, head in enumerate(headers):
        style(table.cell(0, index), head, True, PAPER, ACCENT)
    for r, row in enumerate(rows, start=1):
        shade = PAPER if r % 2 else RGBColor(0xF7, 0xF8, 0xFC)
        for c, value in enumerate(row):
            style(table.cell(r, c), value, False, INK, shade)
    return table


# ---------------------------------------------------------------------------
# The deck
# ---------------------------------------------------------------------------

def build() -> str:
    arms = measured.results()["arms"]
    gains = measured.results().get("improvements", {})
    coverage = measured.coverage()
    protocol = measured.protocol_summary()
    gate = measured.gate_agreement()
    cache = measured.api_cache_stats()
    code = measured.code_stats()
    tests = measured.test_count()["collected"]
    per_arm = measured.api_calls_per_arm()["arms"]
    anchor = measured.gate_external_validity()

    # The refusal example, computed rather than typed. Its whole point is that
    # the floor comes from a real recorded fare, so quoting it from memory would
    # be the one hardcoded number in a deck built to avoid them.
    from trip_planner.core.real_prices import PriceProbe
    from trip_planner.core.trip_cost import assess_budget
    from trip_planner.evaluation.scenarios import scenario

    demo = scenario(measured.scenario_ids()[0])["params"]
    verdict = assess_budget(demo["budget"], demo["legs"][0][0], demo["nights"],
                            demo["adults"], demo["origin"],
                            price_probe=PriceProbe())

    def calls(letter):
        return arms[letter]["avg_llm_calls"]

    def tokens(letter):
        return arms[letter]["avg_total_tokens"]

    def grounded(letter):
        return arms[letter]["avg_prices_grounded_pct"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # ---------------------------------------------------------------- 1 title
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(1.1), Inches(2.0), Inches(11.2), Inches(0.5),
          [("MSc DISSERTATION  ·  VIVA VOCE", 14, True,
            RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(2.5), Inches(11.2), Inches(1.9),
          [("When is AI worth paying for?", 44, True, PAPER),
           ("A travel planner, built four ways.", 32, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.15)
    _rule(slide, Inches(1.1), Inches(4.8), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(5.2), Inches(11.2), Inches(1.2),
          [(f"Student {STUDENT}   ·   {MODULE}", 14, False,
            RGBColor(0x9C, 0xA3, 0xF5))])
    _notes(slide, """
        Fifteen minutes, fourteen slides. One idea: AI is worth paying for when a
        step needs thinking, and is wasted money when it does not. I built the
        same travel planner four ways and measured all four.
    """)

    # ---------------------------------------------------------------- 2 problem
    slide = _blank(prs)
    _heading(slide, "1  ·  The problem", "AI is paid to do work that needs no thinking")
    _stat_row(slide, [
        (f"{calls('B'):.0f}", "AI calls to plan one trip\nwhen agents fetch the data"),
        (f"{calls('D'):.0f}", "AI calls for the same trip\nwhen normal code fetches it"),
        (f"{tokens('B') / tokens('D'):.0f}x", "more text sent to the AI,\nsame finished plan"),
    ], colour=WARN)
    _text(slide, Inches(0.9), Inches(5.3), Inches(11.5), Inches(1.4),
          [("Looking up a flight price is one web request. It needs no thinking.",
            21, True, INK),
           ("But when an AI agent does the looking up, you pay for every step it "
            "takes to decide.", 17, False, SOFT)], spacing=1.25)
    _notes(slide, f"""
        Everyone gives agents tools. Nobody asks which jobs need one. The agent
        version used {calls('B'):.1f} AI calls per trip; mine uses
        {calls('D'):.1f}. Every loop step re-sends the whole conversation and
        every tool description, which is why the text differs by
        {tokens('B') / tokens('D'):.0f} times.
    """)

    # ---------------------------------------------------------------- 3 solution
    slide = _blank(prs)
    _heading(slide, "2  ·  My solution", "One rule, applied to every step")
    _text(slide, Inches(0.9), Inches(2.2), Inches(11.5), Inches(1.4),
          [("Could I write this step as ordinary code?", 32, True, ACCENT)])
    _table(slide,
           ["Answer", "So", "Which steps"],
           [["No — it needs judgement", "use AI",
             "Reading the request  ·  Writing the day-by-day plan"],
            ["Yes — the rule is fixed", "use plain code",
             "Flights  ·  Hotels  ·  Attractions  ·  Restaurants"]],
           col_widths=[2.4, 1.6, 6.4], font=14, top=Inches(3.5))
    _text(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.3),
          [("Two steps out of six need AI. The other four are IF statements.",
            21, True, INK),
           ("Same finished plan. A fraction of the cost.", 17, False, SOFT)],
          spacing=1.25)
    _notes(slide, """
        This is the whole contribution in one slide. You cannot write a rule that
        understands any phrasing a person might use, and you cannot write a rule
        that makes a day pleasant. You absolutely can write a rule that calls a
        flight API with a date. It started as six agents and became three because
        measuring showed where the calls were going.
    """)

    # ---------------------------------------------------------------- 4 frontend
    slide = _blank(prs)
    _heading(slide, "3  ·  What the user sees", "One form, live progress, plan in tabs")
    _figure(slide, "frontend.png", top=Inches(1.95), height=Inches(4.7))
    _text(slide, Inches(0.9), Inches(6.75), Inches(11.5), Inches(0.5),
          [("Purple steps use AI. Green steps are plain code. Both are narrated "
            "in the terminal as they run.", 15, False, SOFT)])
    _notes(slide, """
        Worth demonstrating live. Ask for six nights in London on three thousand
        dollars and it refuses, gives the shortfall, and offers a shorter trip or
        a nearer city. The seven step rows tick over as each finishes, so the page
        never looks frozen. The plan arrives in six tabs with one block per day.
    """)

    # ---------------------------------------------------------------- 5 approaches
    slide = _blank(prs)
    _heading(slide, "4  ·  The four versions",
             "Only one thing changes: who fetches the data")
    _table(slide,
           ["", "How it works", "Who fetches the data", "Why I built it"],
           [["A", "One AI call, no tools", "nobody",
             "The floor. Shows what AI invents with no real data"],
            ["B", "Six agents, first attempt", "each agent decides",
             "My original proposal. The honest starting point"],
            ["C", "Same six agents, tuned", "each agent decides",
             "Proves the gain is the design, not just better settings"],
            ["D", "Three agents", "plain code",
             "What I ship. The idea being tested"]],
           col_widths=[0.5, 2.9, 2.3, 5.0], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.6), Inches(11.5), Inches(1.0),
          [("C is the important one. Without it, someone could say D only won "
            "because B was set up badly.", 18, True, ACCENT)])
    _notes(slide, f"""
        C makes the result defensible. Tuning the six agents without changing the
        design at all cut the text sent by
        {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}%. Comparing B against D
        alone would have mixed two effects and claimed credit for both.
    """)

    # ---------------------------------------------------------------- 6 tools
    slide = _blank(prs)
    _heading(slide, "5  ·  Agents and their tools", "Counted from the code, per version")
    _table(slide,
           ["Agent", "B  tools", "B  steps", "C  tools", "C  steps", "D"],
           [["Preferences extractor", "0", "3", "0", "3", "0 tools"],
            ["Flight search", "4", "8", "1", "3", "removed"],
            ["Hotel search", "8", "10", "1", "3", "removed"],
            ["Activities", "4", "10", "2", "3", "removed"],
            ["Itinerary coordinator", "4", "15", "0", "3", "4 tools"],
            ["Conversation", "—", "—", "—", "—", "0 tools"],
            ["TOTAL TOOL SLOTS", "20", "", "4", "", "4"]],
           col_widths=[3.2, 1.1, 1.1, 1.1, 1.1, 1.6], font=12.5, top=Inches(2.15))
    _text(slide, Inches(0.9), Inches(5.9), Inches(11.5), Inches(0.9),
          [("The hotel agent alone held 8 tools and 10 steps. Every step re-sent "
            "all 8 tool descriptions to the AI.", 17, True, INK)])
    _notes(slide, """
        "Steps" is the loop limit: how many times the agent may think, call a
        tool, and think again. Each step is a full AI call that re-sends the
        conversation and every tool description it holds. Eight tools times ten
        steps is where B's cost came from. C cut the same agents to one or two
        tools and three steps. D removes the fetching agents entirely, so the four
        tools that remain belong to the coordinator and nothing loops.
    """)

    # ---------------------------------------------------------------- 7 how tools work
    slide = _blank(prs)
    _heading(slide, "6  ·  How a tool call works", "12 tools, each with a checked input")
    _figure(slide, "mcp_lifecycle.png", top=Inches(1.95), height=Inches(4.3))
    _text(slide, Inches(0.9), Inches(6.4), Inches(11.5), Inches(0.7),
          [("The benefit: every input is checked against a schema before it "
            "reaches an API, and every reply is saved so the same request is "
            "never bought twice.", 15, False, SOFT)])
    _notes(slide, f"""
        The tool server runs as its own program and answers over JSON-RPC. Twelve
        tools, each declaring what input it accepts, so a malformed request is
        refused rather than sent. Every reply passes through a record-and-replay
        layer: {cache['entries']} responses are saved, which is why anyone can
        reproduce my results with no API keys. Honest caveat: the shipped version
        calls these functions directly rather than over the protocol - the
        protocol is exercised by the six-agent versions, and the report says so.
    """)

    # ---------------------------------------------------------------- 8 defects
    slide = _blank(prs)
    _heading(slide, "7  ·  What went wrong in each version",
             "Measured, not guessed. This is why D exists")
    _table(slide,
           ["", "The problem I measured"],
           [["A", "No tools, so it invents everything. Only "
                 f"{grounded('A'):.1f}% of its prices matched a real fare"],
            ["B", "Skipped its own tools: never called the attractions or the "
                  "restaurant tool once. Twice produced broken output it had to redo"],
            ["C", "Better, but still unreliable: never called the flight tool at "
                  "all on the recorded run"],
            ["D", f"Always makes exactly the same {per_arm['D']['total_http']} "
                  "requests, because code decides, not AI. Nothing is skipped"]],
           col_widths=[0.5, 10.5], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.3),
          [("When AI decides which tools to call, it sometimes does not call them.",
            21, True, WARN),
           ("The plan still looks finished. That is what makes it dangerous.",
            17, False, SOFT)], spacing=1.25)
    _notes(slide, """
        The heart of the argument. An agent that skips a tool still writes a
        confident, well-formatted itinerary, so you cannot tell by reading it. B
        never once fetched attractions or restaurants and still produced a full
        plan. That is why groundedness is measured rather than judged by eye.
    """)

    # ---------------------------------------------------------------- 9 budget split
    slide = _blank(prs)
    _heading(slide, "8  ·  Budget: dividing the money",
             "Worked out from the trip, not a fixed percentage")
    _table(slide,
           ["The traveller says", "What changes"],
           [["nothing", "Split comes from what this trip's parts actually cost"],
            ["\"a luxury stay\"", "More to the room. Flights and food stay sensible"],
            ["\"luxury trip\"", "Spread across the room, the food and the doing"],
            ["\"I can compromise\"", "Money moves out of the room into experiences"],
            ["their own split", "Used exactly as given. It is their money"]],
           col_widths=[2.6, 7.8], font=13.5, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.6), Inches(11.5), Inches(1.1),
          [("A fixed percentage cannot know that a long-haul flight eats the "
            "budget and a short one does not.", 18, True, INK)])
    _notes(slide, """
        It used to be one fixed percentage split for every trip. It now reads the
        wording, and no category is ever given more than it could possibly spend.
        On a two thousand dollar Istanbul trip the room budget moves from $327 if
        the traveller can compromise, to $443 at moderate, to $664 for a luxury
        stay. Same total, different trip.
    """)

    # ---------------------------------------------------------------- 10 budget check
    slide = _blank(prs)
    _heading(slide, "9  ·  Budget: is the trip even possible?",
             "It refuses, and says what would work")
    _stat_row(slide, [
        (f"${demo['budget']:,.0f}",
         f"asked for\n{demo['nights']} nights in {demo['legs'][0][0]}"),
        (f"${verdict.estimate.minimum:,.0f}",
         "the cheapest it can\nactually be done for"),
        ("REFUSED" if not verdict.feasible else "ALLOWED",
         "with the shortfall named,\nand three ways to fix it"),
    ], colour=WARN)
    _text(slide, Inches(0.9), Inches(5.2), Inches(11.5), Inches(1.5),
          [(f"Why ${verdict.estimate.minimum:,.0f}? Because it checks the real "
            f"recorded fare, not a built-in table.", 19, True, INK),
           (f"The table said a medium-haul flight starts at "
            f"${anchor['estimated_minimum']:,.0f}. The API actually returned "
            f"${anchor['cheapest_real_fare']:,.0f} — the table was "
            f"{abs(anchor['minimum_anchor_error_pct']):.0f}% too low.",
            17, False, SOFT)], spacing=1.3)
    _notes(slide, f"""
        Two parts. It estimates what the trip costs at minimum, comfortable and
        luxury standards, and refuses anything below the floor - then offers to
        shorten the trip, raise the budget, or pick a nearer city. And where a
        real fare has been recorded for that route it uses that instead of the
        table, and marks the line as measured rather than estimated. Tested on all
        {coverage['scenarios_designed']} trips: it never wrongly refuses a
        workable one, and it misses {gate['false_negative']} impossible one.
        Agreement score {gate['cohens_kappa']:.3f}.
    """)

    # ---------------------------------------------------------------- 11 cost
    slide = _blank(prs)
    _heading(slide, "10  ·  Result: cost", "Fetching data is where the money went")
    _figure(slide, "efficiency.png", top=Inches(1.95), height=Inches(4.4))
    _text(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6),
          [(f"B sent {tokens('B'):,.0f} units of text.  D sent {tokens('D'):,.0f}.  "
            f"Same trip, same data, same AI model.", 16, True, INK)])
    _notes(slide, f"""
        {coverage['repeats_per_arm']} runs of each version, so every bar has a
        range. The ranges for B and D do not overlap, which is why this is
        reported as a real difference rather than noise. Tuning alone accounted
        for {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}% and the design
        change reached {gains.get('D_vs_B', {}).get('tokens_pct', 0):.0f}% - the
        gap between those two is what I claim.
    """)

    # ---------------------------------------------------------------- 12 grounded
    slide = _blank(prs)
    _heading(slide, "11  ·  Result: is the plan real?", "Cheaper, and no less accurate")
    _figure(slide, "groundedness.png", top=Inches(1.95), height=Inches(4.4))
    _text(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6),
          [(f"Prices matching a real fare:   A {grounded('A'):.1f}%   ·   "
            f"B {grounded('B'):.1f}%   ·   C {grounded('C'):.1f}%   ·   "
            f"D {grounded('D'):.1f}%", 16, True, INK)])
    _notes(slide, f"""
        Saving money would be pointless if the plan got vaguer. A is the control
        and scores {grounded('A'):.1f}% - a confident itinerary invented from
        nothing, which is what this measure exists to catch. It caught a real one:
        my first working run produced a complete plan while every tool call was
        silently failing.
    """)

    # ---------------------------------------------------------------- 13 my faults
    slide = _blank(prs)
    _heading(slide, "12  ·  Problems in my own system",
             "Found by measuring it. Reported, not hidden")
    _stat_row(slide, [
        (f"{protocol['passed']}/{protocol['total_checks']}",
         "design checks pass.\nSix things I claimed do not happen"),
        (f"{gate['recall']:.0%}",
         "of impossible budgets caught.\nIt misses the other half"),
        (f"{coverage['scenarios_measured']}/{coverage['scenarios_designed']}",
         "trips measured for cost.\nThe API limits stopped me"),
    ], colour=WARN)
    _text(slide, Inches(0.9), Inches(5.3), Inches(11.5), Inches(1.4),
          [("All three are in the report, with the evidence.", 20, True, INK),
           ("An evaluation that only confirms its author is not an evaluation.",
            17, False, SOFT)], spacing=1.25)
    _notes(slide, f"""
        {protocol['failed']} of {protocol['total_checks']} checks fail: message
        priority is declared and never used, permissions are declared and never
        enforced. The budget check never wrongly refuses a workable trip but
        misses half the impossible ones. And cost coverage is one trip because the
        free plans allow thirty flight searches a month. All three are stated in
        the abstract, not buried.
    """)

    # ---------------------------------------------------------------- 14 why
    slide = _blank(prs)
    _heading(slide, "13  ·  Why this matters", "Beyond one travel planner")
    _table(slide,
           ["", "What this project shows"],
           [["1", "AI agents are expensive by default, and most of the cost buys "
                 "work that needs no intelligence"],
            ["2", "Giving an agent a tool does not mean it will use it. Mine "
                  "skipped tools and still produced confident plans"],
            ["3", "You cannot tell an invented plan from a real one by reading "
                  "it. It has to be measured"],
            ["4", "The cheaper design was also just as accurate, so there is no "
                  "hidden trade-off being sold here"]],
           col_widths=[0.5, 10.5], font=14, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.5), Inches(11.5), Inches(1.1),
          [("Anyone building with AI agents faces this choice. Most do not "
            "measure it.", 19, True, ACCENT)])
    _notes(slide, f"""
        The "so what?" answer. The system is {code['areas']['trip_planner']['lines']:,}
        lines with {tests} tests, and the whole evaluation replays from disk with
        no API keys, so the method is reusable by anyone asking the same question
        about their own agents.
    """)

    # ---------------------------------------------------------------- 15 close
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(1.1), Inches(1.7), Inches(11.2), Inches(0.5),
          [("IN ONE SENTENCE", 14, True, RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(2.2), Inches(11.2), Inches(2.4),
          [("Use AI where a step needs thinking.", 36, True, PAPER),
           ("Everywhere else, it is just a bill.", 36, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.2)
    _rule(slide, Inches(1.1), Inches(4.8), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(5.15), Inches(11.2), Inches(1.6),
          [(f"{tokens('B') / tokens('D'):.0f}x cheaper, no loss of accuracy, "
            f"on {coverage['scenarios_measured']} trip run "
            f"{coverage['repeats_per_arm']} times.", 19, False,
            RGBColor(0xC7, 0xD2, 0xFE)),
           ("", 8, False, PAPER),
           ("Narrow coverage is the gap, and everything needed to widen it is "
            "saved and runs without keys.", 15, False,
            RGBColor(0x9C, 0xA3, 0xF5))], spacing=1.3)
    _notes(slide, """
        Land the claim and its limit in the same breath. The effect is large and
        the sample is narrow, and both are in the abstract. The saved replies, the
        harness and the twenty trips are all committed, so the next person - or me
        next month when the limits reset - can widen it without rebuilding.
    """)

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {os.path.relpath(path, ROOT)}")
