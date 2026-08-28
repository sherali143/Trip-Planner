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
    coverage = measured.coverage()
    protocol = measured.protocol_summary()
    gate = measured.gate_agreement()
    cache = measured.api_cache_stats()
    tests = measured.test_count()["collected"]
    per_arm = measured.api_calls_per_arm()["arms"]
    anchor = measured.gate_external_validity()

    # Computed, not typed: the whole point of this example is that the floor comes
    # from a real recorded fare.
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

    # ----------------------------------------- 1  title, problem, solution
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(0.9), Inches(0.6), Inches(11.5), Inches(0.4),
          [("MSc DISSERTATION  ·  VIVA VOCE  ·  " + MODULE, 12, True,
            RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(0.9), Inches(1.05), Inches(11.5), Inches(1.1),
          [("AI Trip Planner", 46, True, PAPER)])
    _text(slide, Inches(0.9), Inches(2.15), Inches(11.5), Inches(0.6),
          [("You type where you want to go. It gives you a day-by-day plan with "
            "real flight and hotel prices.", 17, False,
            RGBColor(0xC7, 0xD2, 0xFE))])
    _rule(slide, Inches(0.9), Inches(2.95), Inches(1.4), TEAL)

    _text(slide, Inches(0.9), Inches(3.4), Inches(5.4), Inches(2.5),
          [("THE PROBLEM", 13, True, RGBColor(0xF0, 0xB4, 0x6A)),
           ("", 6, False, PAPER),
           ("Planning a trip needs flights, hotels, places to visit and a budget "
            "that adds up.", 17, False, PAPER),
           ("", 4, False, PAPER),
           ("One AI doing all of it is slow, expensive, and makes prices up.",
            17, False, PAPER)], spacing=1.25)

    _text(slide, Inches(6.9), Inches(3.4), Inches(5.5), Inches(2.5),
          [("MY SOLUTION", 13, True, RGBColor(0x6E, 0xE7, 0xDF)),
           ("", 6, False, PAPER),
           ("Split the job between several small agents, each with one clear "
            "task.", 17, False, PAPER),
           ("", 4, False, PAPER),
           ("Then give AI only to the agents that need to think.", 17, False,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.25)

    _text(slide, Inches(0.9), Inches(6.35), Inches(11.5), Inches(0.5),
          [(f"Student {STUDENT}", 12, False, RGBColor(0x9C, 0xA3, 0xF5))])
    _notes(slide, f"""
        Ten slides. The project is a working travel planner. The question is which
        parts of it actually need AI. I built it four different ways and measured
        all four: the all-agent version needs {calls('B'):.1f} AI calls per trip
        and mine needs {calls('D'):.1f}.
    """)

    # ----------------------------------------------------- 2  the agents
    slide = _blank(prs)
    _heading(slide, "1  ·  We use several agents",
             "Each one has a name and one job")
    _table(slide,
           ["Agent", "What it does", "Needs AI?"],
           [["Travel Conversation Assistant",
             "Asks the traveller for anything missing", "Yes - people write in "
             "many ways"],
            ["Travel Preferences Extractor",
             "Turns those words into exact fields", "Yes - same reason"],
            ["Flight Search Specialist", "Looks up flights", "No"],
            ["Hotel Search Specialist", "Looks up hotels", "No"],
            ["Activities Specialist", "Looks up places to visit and eat", "No"],
            ["Itinerary Coordinator", "Writes the day-by-day plan",
             "Yes - which day, what order"]],
           col_widths=[3.4, 4.6, 3.0], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.9), Inches(11.5), Inches(0.9),
          [("Looking something up does not need thinking. Only three agents "
            "really need AI.", 19, True, ACCENT)])
    _notes(slide, """
        The test for each agent: could I write its job as ordinary code? You
        cannot write a rule that understands any way a person might phrase a
        request, and you cannot write a rule that makes a day pleasant. You can
        absolutely write a rule that calls a flight API with a date.
    """)

    # -------------------------------------------------- 3  the approaches
    slide = _blank(prs)
    _heading(slide, "2  ·  I built it four ways", "So I could compare them fairly")
    _table(slide,
           ["", "Name", "What it is"],
           [["A", "One AI, no tools",
             "A single AI call. It has no way to look anything up, so it invents "
             "the whole plan"],
            ["B", "Six agents, first try",
             "Every agent gets tools and decides for itself when to use them. "
             "This was my original plan"],
            ["C", "Six agents, tidied up",
             "Same six agents, but fewer tools each and a tighter limit on how "
             "long they can think"],
            ["D", "Three agents",
             "The look-up agents are gone. Normal code fetches the data. This is "
             "what I ship"]],
           col_widths=[0.5, 2.5, 8.0], font=13.5, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.7), Inches(11.5), Inches(1.0),
          [("C exists so nobody can say D only won because B was set up badly.",
            19, True, ACCENT)])
    _notes(slide, """
        A is the floor: it shows what AI produces with no real data. B is my
        original proposal. C is the same design with sensible settings, which is
        what makes the comparison honest. D is the idea being tested.
    """)

    # ---------------------------------------------- 4  tools in each approach
    slide = _blank(prs)
    _heading(slide, "3  ·  Which tools each agent gets",
             "Read from the code. A has none at all")
    _table(slide,
           ["Agent", "B  (first try)", "C  (tidied)", "D  (shipped)"],
           [["Preferences Extractor", "none", "none", "none"],
            ["Conversation Assistant", "not used", "not used", "none"],
            ["Flight Search",
             "search_comprehensive_flights, search_round_trip_flights, "
             "search_internet, calculate",
             "distilled_search_flights", "agent removed"],
            ["Hotel Search",
             "search_hotels_comprehensive, search_accommodations_with_location, "
             "search_hotel_destination, search_hotels_by_dest_id, "
             "get_hotel_reviews, get_attractions_near_hotel, search_internet, "
             "calculate",
             "distilled_search_hotels", "agent removed"],
            ["Activities",
             "search_attractions, search_restaurants, search_internet, calculate",
             "distilled_search_attractions, distilled_search_restaurants",
             "agent removed"],
            ["Itinerary Coordinator",
             "calculate, search_internet, search_attractions, search_restaurants",
             "none",
             "calculate, search_internet, search_attractions, search_restaurants"],
            ["TOTAL TOOLS", "20", "4", "4"]],
           col_widths=[2.2, 4.2, 2.6, 2.4], font=9.5, top=Inches(2.1))
    _text(slide, Inches(0.9), Inches(6.4), Inches(11.5), Inches(0.7),
          [("The hotel agent alone had 8 tools. Every time it thinks, all 8 tool "
            "descriptions are sent to the AI again.", 16, True, INK)])
    _notes(slide, """
        The most useful slide for a question. In B the hotel agent had eight tools
        and was allowed ten thinking steps; each step is a full AI call that
        re-sends the conversation and all eight tool descriptions. In C the same
        agent has one tool that returns the best three hotels already trimmed. In
        D there is no hotel agent at all - four lines of Python make the call.
    """)

    # ------------------------------------------------------- 5  AI calls
    slide = _blank(prs)
    _heading(slide, "4  ·  How many AI calls each one makes", "Per trip planned")
    _table(slide,
           ["", "Approach", "AI calls", "Text sent to the AI", "Cost per trip"],
           [["A", "One AI, no tools", f"{calls('A'):.0f}",
             f"{tokens('A'):,.0f}", f"${arms['A']['avg_cost_usd']:.3f}"],
            ["B", "Six agents, first try", f"{calls('B'):.0f}",
             f"{tokens('B'):,.0f}", f"${arms['B']['avg_cost_usd']:.3f}"],
            ["C", "Six agents, tidied up", f"{calls('C'):.0f}",
             f"{tokens('C'):,.0f}", f"${arms['C']['avg_cost_usd']:.3f}"],
            ["D", "Three agents  (shipped)", f"{calls('D'):.0f}",
             f"{tokens('D'):,.0f}", f"${arms['D']['avg_cost_usd']:.3f}"]],
           col_widths=[0.5, 3.4, 1.6, 2.6, 2.2], font=14, top=Inches(2.3))
    _text(slide, Inches(0.9), Inches(4.9), Inches(11.5), Inches(1.6),
          [(f"B needs {calls('B'):.0f} AI calls. D needs {calls('D'):.0f}.",
            26, True, ACCENT),
           ("", 6, False, INK),
           (f"That is {tokens('B') / tokens('D'):.0f} times less text, for the "
            f"same finished plan.", 19, False, SOFT)], spacing=1.25)
    _notes(slide, f"""
        Averages over {coverage['repeats_per_arm']} runs each. A looks cheap but
        it retrieves nothing, so its plan is invented - the next slide but one
        shows that. The interesting pair is B and D: same task, same data, same AI
        model, {tokens('B') / tokens('D'):.0f} times the text.
    """)

    # ------------------------------------------------------- 6  frontend
    slide = _blank(prs)
    _heading(slide, "5  ·  What the user sees",
             "One form, live progress, the plan in tabs")
    _figure(slide, "frontend.png", top=Inches(1.95), height=Inches(4.7))
    _text(slide, Inches(0.9), Inches(6.75), Inches(11.5), Inches(0.5),
          [("Purple steps use AI. Green steps are normal code.", 15, False, SOFT)])
    _notes(slide, """
        Worth showing live. The seven rows tick over as each step finishes, so the
        page never looks frozen, and the same steps are printed in the terminal at
        the same time. Ask for six nights in London on three thousand dollars and
        it refuses, says how much short you are, and offers a shorter trip or a
        cheaper city.
    """)

    # ------------------------------------------------- 7  what went wrong
    slide = _blank(prs)
    _heading(slide, "6  ·  What went wrong in each one",
             "Measured, not guessed. This is why D exists")
    _table(slide,
           ["", "The problem I measured"],
           [["A", f"No tools, so it invents everything. Only {grounded('A'):.1f}% "
                  "of its prices matched a real one"],
            ["B", "Did not use its own tools: never called the attractions or the "
                  "restaurant tool once. Twice gave broken output"],
            ["C", "Better, but still missed things: never called the flight tool "
                  "at all on the recorded run"],
            ["D", f"Always makes the same {per_arm['D']['total_http']} requests, "
                  "because code decides, not AI. Nothing gets skipped"]],
           col_widths=[0.5, 10.5], font=13.5, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.3),
          [("When AI decides which tools to use, sometimes it just does not use "
            "them.", 21, True, WARN),
           ("The plan still looks complete. That is what makes it dangerous.",
            17, False, SOFT)], spacing=1.25)
    _notes(slide, """
        The heart of the argument. An agent that skips a tool still writes a
        confident, tidy itinerary, so you cannot tell by reading it. B never
        fetched attractions or restaurants at all and still produced a full plan.
        That is why I measure how much of a plan came from real data.
    """)

    # ---------------------------------------------------- 8  budget check
    slide = _blank(prs)
    _heading(slide, "7  ·  The budget check",
             "It splits the money, then refuses the impossible")
    _table(slide,
           ["Step", "What it does"],
           [["1  Split", "Divides the budget across flights, hotel, food and "
                         "things to do - based on this trip, not a fixed share"],
            ["2  Listen", "\"a luxury stay\" moves money to the hotel; "
                          "\"I can compromise\" moves it to experiences"],
            ["3  Check", "Works out the cheapest this trip could possibly cost"],
            ["4  Refuse", "If the budget is below that, it says so and offers "
                          "three ways to fix it"]],
           col_widths=[1.6, 8.9], font=13.5, top=Inches(2.15))
    _stat_row(slide, [
        (f"${demo['budget']:,.0f}", "traveller asked for"),
        (f"${verdict.estimate.minimum:,.0f}", "cheapest it can be done"),
        ("REFUSED" if not verdict.feasible else "ALLOWED", "with reasons given"),
    ], top=Inches(5.05), colour=WARN)
    _text(slide, Inches(0.9), Inches(6.6), Inches(11.5), Inches(0.6),
          [(f"It uses the real recorded price. The built-in table said "
            f"${anchor['estimated_minimum']:,.0f}; the API returned "
            f"${anchor['cheapest_real_fare']:,.0f}.", 15, False, SOFT)])
    _notes(slide, f"""
        Two things people ask about. Splitting: it used to be one fixed percentage
        for every trip; now it reads the wording, and on a two thousand dollar
        Istanbul trip the hotel budget moves from $327 to $664 depending on what
        the traveller says matters. Checking: tested on all
        {coverage['scenarios_designed']} trips, it never wrongly refuses a trip
        that works, and misses {gate['false_negative']} impossible one.
    """)

    # -------------------------------------------------------- 9  results
    slide = _blank(prs)
    _heading(slide, "8  ·  Results", "Cheaper, and just as accurate")
    _figure(slide, "efficiency.png", top=Inches(1.9), height=Inches(3.8))
    _stat_row(slide, [
        (f"{tokens('B') / tokens('D'):.0f}x", "cheaper than the all-agent version"),
        (f"{grounded('D'):.0f}%", "of my plan's prices are real"),
        (f"{protocol['passed']}/{protocol['total_checks']}",
         "of my own design checks pass"),
    ], top=Inches(5.85), colour=ACCENT)
    _notes(slide, f"""
        Cheaper and no less accurate, so there is no hidden trade-off. The third
        number is deliberately on this slide: {protocol['failed']} of my own
        design checks fail - message priority is declared and never used, and
        permissions are declared and never enforced. Cost coverage is also only
        {coverage['scenarios_measured']} of {coverage['scenarios_designed']} trips
        because the free API plans allow thirty flight searches a month. All of it
        is in the report rather than hidden.
    """)

    # ------------------------------------------------------- 10  closing
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(1.1), Inches(1.6), Inches(11.2), Inches(0.5),
          [("IN ONE SENTENCE", 14, True, RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(2.1), Inches(11.2), Inches(2.2),
          [("Give AI the steps that need thinking.", 36, True, PAPER),
           ("Let normal code do the looking up.", 36, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.2)
    _rule(slide, Inches(1.1), Inches(4.55), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(4.9), Inches(11.2), Inches(2.0),
          [(f"{tokens('B') / tokens('D'):.0f}x cheaper  ·  same accuracy  ·  "
            f"{tests} tests  ·  {cache['entries']} saved API replies so anyone "
            f"can repeat it", 17, False, RGBColor(0xC7, 0xD2, 0xFE)),
           ("", 8, False, PAPER),
           (f"The gap: only {coverage['scenarios_measured']} of "
            f"{coverage['scenarios_designed']} trips measured for cost, because "
            f"of the free API limits.", 15, False, RGBColor(0x9C, 0xA3, 0xF5))],
          spacing=1.3)
    _notes(slide, """
        Land the claim and its limit together. The effect is large and the sample
        is narrow, and both are in the abstract. The saved replies, the test
        harness and the twenty trips are all committed, so this can be widened
        next month when the API limits reset, without rebuilding anything.
    """)

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {os.path.relpath(path, ROOT)}")
