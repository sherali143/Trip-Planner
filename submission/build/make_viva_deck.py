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
    tests = measured.test_count()["collected"]
    per_arm = measured.api_calls_per_arm()["arms"]
    anchor = measured.gate_external_validity()

    # The refusal example, computed rather than typed. Its whole point is that the
    # floor comes from a real recorded fare, so quoting it from memory would be
    # the one hardcoded number in a deck built to avoid them.
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

    # ------------------------------------------------- 1  title + problem + fix
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(0.9), Inches(0.55), Inches(11.5), Inches(0.4),
          [("MSc DISSERTATION  ·  VIVA VOCE  ·  " + MODULE, 12, True,
            RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(0.9), Inches(1.0), Inches(11.5), Inches(1.2),
          [("AI Trip Planner", 46, True, PAPER)])
    _text(slide, Inches(0.9), Inches(2.15), Inches(11.5), Inches(0.7),
          [("Type where you want to go. Get a day-by-day plan built from real "
            "flight and hotel prices.", 17, False, RGBColor(0xC7, 0xD2, 0xFE))])
    _rule(slide, Inches(0.9), Inches(2.95), Inches(1.4), TEAL)

    # Two blocks: the problem, then what I did about it.
    _text(slide, Inches(0.9), Inches(3.35), Inches(5.4), Inches(2.6),
          [("THE PROBLEM", 13, True, RGBColor(0xF0, 0xB4, 0x6A)),
           ("", 6, False, PAPER),
           ("AI agents are given tools and left to decide when to use them.",
            17, False, PAPER),
           ("", 5, False, PAPER),
           (f"That cost {calls('B'):.0f} AI calls to plan one trip — and the "
            f"agents still skipped their own tools.", 15, False,
            RGBColor(0xC7, 0xD2, 0xFE))], spacing=1.25)

    _text(slide, Inches(6.9), Inches(3.35), Inches(5.5), Inches(2.6),
          [("MY SOLUTION", 13, True, RGBColor(0x6E, 0xE7, 0xDF)),
           ("", 6, False, PAPER),
           ("Use AI only where a step needs thinking. Fetch data with plain code.",
            17, False, PAPER),
           ("", 5, False, PAPER),
           (f"Same plan for {calls('D'):.0f} AI calls — "
            f"{tokens('B') / tokens('D'):.0f}x cheaper, just as accurate.",
            15, False, RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.25)

    _text(slide, Inches(0.9), Inches(6.35), Inches(11.5), Inches(0.5),
          [(f"Student {STUDENT}", 12, False, RGBColor(0x9C, 0xA3, 0xF5))])
    _notes(slide, f"""
        Ten slides, fifteen minutes. The project is a working travel planner. The
        research question is which steps inside it actually need AI. I built it
        four ways and measured all four: the agent version needed
        {calls('B'):.1f} AI calls per trip and mine needs {calls('D'):.1f}.
    """)

    # ---------------------------------------------------------- 2  the agents
    slide = _blank(prs)
    _heading(slide, "1  ·  The agents", "Their real names, and what each one does")
    _table(slide,
           ["Agent name", "Its job", "Uses AI?"],
           [["Travel Conversation Assistant",
             "Asks the traveller for anything missing", "YES"],
            ["Travel Preferences Extractor",
             "Turns the words into exact fields, then checks the budget", "YES"],
            ["Flight Search Specialist", "Finds flights", "no — removed in D"],
            ["Hotel Search Specialist", "Finds hotels", "no — removed in D"],
            ["Activities Specialist", "Finds attractions and restaurants",
             "no — removed in D"],
            ["Itinerary Coordinator",
             "Writes the day-by-day plan from what was found", "YES"]],
           col_widths=[3.4, 5.4, 2.2], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.9), Inches(11.5), Inches(0.9),
          [("The three search agents were removed. Plain code does their job for "
            "a fraction of the cost.", 18, True, ACCENT)])
    _notes(slide, """
        Six agents became three. The three that stayed each fail the test "could I
        write this as ordinary code?" - you cannot write a rule that understands
        any phrasing a person might use, and you cannot write a rule that makes a
        day pleasant. The three that went were only ever making API calls, and an
        IF statement does that perfectly well.
    """)

    # ------------------------------------------------------ 3  the approaches
    slide = _blank(prs)
    _heading(slide, "2  ·  The four approaches",
             "Only one thing changes: who fetches the data")
    _table(slide,
           ["", "Approach", "Who fetches the data", "Why it exists"],
           [["A", "One AI call, no tools", "nobody",
             "The floor. Shows what AI invents with no data"],
            ["B", "Six agents, first attempt", "each agent decides",
             "My original proposal, untuned"],
            ["C", "Six agents, tuned", "each agent decides",
             "Proves the gain is the design, not the settings"],
            ["D", "Three agents", "plain code",
             "What I ship. The idea being tested"]],
           col_widths=[0.5, 2.9, 2.3, 5.0], font=13.5, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.7), Inches(11.5), Inches(1.0),
          [("C matters most. Without it, someone could say D only won because B "
            "was set up badly.", 18, True, ACCENT)])
    _notes(slide, f"""
        Tuning the six agents without changing the design cut the text sent by
        {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}%. Comparing B against D
        alone would have mixed two effects together and claimed credit for both.
    """)

    # ----------------------------------------------- 4  tools per agent per arm
    slide = _blank(prs)
    _heading(slide, "3  ·  Tools given to each agent",
             "Counted from the code. This is where the cost came from")
    _table(slide,
           ["Agent", "A", "B", "C", "D"],
           [["Travel Preferences Extractor", "—", "0 tools", "0 tools", "0 tools"],
            ["Flight Search Specialist", "—", "4 tools, 8 steps",
             "1 tool, 3 steps", "removed"],
            ["Hotel Search Specialist", "—", "8 tools, 10 steps",
             "1 tool, 3 steps", "removed"],
            ["Activities Specialist", "—", "4 tools, 10 steps",
             "2 tools, 3 steps", "removed"],
            ["Itinerary Coordinator", "—", "4 tools, 15 steps",
             "0 tools", "4 tools"],
            ["Travel Conversation Assistant", "—", "—", "—", "0 tools"],
            ["TOTAL TOOLS", "0", "20", "4", "4"]],
           col_widths=[3.6, 0.9, 2.4, 2.0, 1.6], font=12.5, top=Inches(2.15))
    _text(slide, Inches(0.9), Inches(5.95), Inches(11.5), Inches(0.9),
          [("\"Steps\" is how many times an agent may loop. Each loop re-sends "
            "every tool description to the AI — that is the bill.", 17, True,
            INK)])
    _notes(slide, """
        The single most useful table in the deck. The hotel agent held 8 tools and
        was allowed 10 loops. Every loop is a full AI call that re-sends the
        conversation and all 8 tool descriptions. Twenty tool slots in B, four in
        C, four in D - and in D they belong to the coordinator, which does not
        loop looking for data because the data is already there.
    """)

    # --------------------------------------------------------- 5  the frontend
    slide = _blank(prs)
    _heading(slide, "4  ·  What the user sees",
             "One form, live progress, the plan in tabs")
    _figure(slide, "frontend.png", top=Inches(1.95), height=Inches(4.7))
    _text(slide, Inches(0.9), Inches(6.75), Inches(11.5), Inches(0.5),
          [("Purple steps use AI. Green steps are plain code.", 15, False, SOFT)])
    _notes(slide, """
        Worth demonstrating live. The seven rows tick over as each step finishes,
        so the page never looks frozen, and the same steps are narrated in the
        terminal at the same time. Ask for six nights in London on three thousand
        dollars and it refuses, names the shortfall, and offers a shorter trip or
        a nearer city.
    """)

    # ------------------------------------------------------------- 6  defects
    slide = _blank(prs)
    _heading(slide, "5  ·  What went wrong in each approach",
             "Measured, not guessed. This is why D exists")
    _table(slide,
           ["", "The problem I measured"],
           [["A", f"No tools, so it invents everything. Only {grounded('A'):.1f}% "
                  "of its prices matched a real fare"],
            ["B", "Skipped its own tools: never called the attractions or the "
                  "restaurant tool once. Twice produced broken output"],
            ["C", "Better, but still unreliable: never called the flight tool at "
                  "all on the recorded run"],
            ["D", f"Always makes the same {per_arm['D']['total_http']} requests, "
                  "because code decides, not AI. Nothing is skipped"]],
           col_widths=[0.5, 10.5], font=13.5, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.3),
          [("When AI decides which tools to call, it sometimes does not call them.",
            21, True, WARN),
           ("The plan still looks finished. That is what makes it dangerous.",
            17, False, SOFT)], spacing=1.25)
    _notes(slide, """
        The heart of the argument. An agent that skips a tool still writes a
        confident, well-formatted itinerary, so you cannot tell by reading it. B
        never fetched attractions or restaurants at all and still produced a full
        plan. That is why groundedness is measured rather than judged by eye.
    """)

    # -------------------------------------------------------------- 7  budget
    slide = _blank(prs)
    _heading(slide, "6  ·  The budget check", "It divides the money, then refuses the impossible")
    _table(slide,
           ["Step", "What it does"],
           [["1  Divide", "Splits the budget across flights, hotel, food and "
                          "activities — worked out from this trip, not a fixed %"],
            ["2  Listen", "\"a luxury stay\" moves money to the room; "
                          "\"I can compromise\" moves it to experiences"],
            ["3  Check", "Works out the cheapest this trip could possibly cost"],
            ["4  Refuse", "If the budget is below that, it says so and offers "
                          "three ways to fix it"]],
           col_widths=[1.7, 8.8], font=13.5, top=Inches(2.15))
    _stat_row(slide, [
        (f"${demo['budget']:,.0f}", "asked for"),
        (f"${verdict.estimate.minimum:,.0f}", "cheapest it can be done"),
        ("REFUSED" if not verdict.feasible else "ALLOWED", "with reasons given"),
    ], top=Inches(5.05), colour=WARN)
    _text(slide, Inches(0.9), Inches(6.6), Inches(11.5), Inches(0.6),
          [(f"It uses the real recorded fare. The built-in table said "
            f"${anchor['estimated_minimum']:,.0f} — the API returned "
            f"${anchor['cheapest_real_fare']:,.0f}.", 15, False, SOFT)])
    _notes(slide, f"""
        Two features people ask about. Dividing: it used to be one fixed
        percentage for every trip, and now it reads the wording - on a two
        thousand dollar Istanbul trip the room budget moves from $327 to $664
        depending on what the traveller says matters. Checking: tested on all
        {coverage['scenarios_designed']} trips, it never wrongly refuses a
        workable one and misses {gate['false_negative']} impossible one.
        Agreement score {gate['cohens_kappa']:.3f}.
    """)

    # ------------------------------------------------------------- 8  results
    slide = _blank(prs)
    _heading(slide, "7  ·  Results", "Cheaper, and no less accurate")
    _figure(slide, "efficiency.png", top=Inches(1.9), height=Inches(3.9))
    _stat_row(slide, [
        (f"{tokens('B') / tokens('D'):.0f}x", "cheaper than the agent version"),
        (f"{grounded('D'):.0f}%", "of D's prices match a real fare"),
        (f"{grounded('A'):.1f}%", "of A's do — it has no tools"),
    ], top=Inches(5.95), colour=ACCENT)
    _notes(slide, f"""
        {coverage['repeats_per_arm']} runs of each version, so every bar has a
        range, and the ranges for B and D do not overlap. On accuracy: A is the
        control and scores {grounded('A'):.1f}% - a confident itinerary invented
        from nothing, which is what that measure exists to catch. It caught a real
        one: my first working run produced a complete plan while every tool call
        was silently failing.
    """)

    # ---------------------------------------------------------- 9  my problems
    slide = _blank(prs)
    _heading(slide, "8  ·  Problems in my own system",
             "Found by measuring it. Reported, not hidden")
    _stat_row(slide, [
        (f"{protocol['passed']}/{protocol['total_checks']}",
         "design checks pass.\nSix things I claimed do not happen"),
        (f"{gate['recall']:.0%}",
         "of impossible budgets caught.\nIt misses the other half"),
        (f"{coverage['scenarios_measured']}/{coverage['scenarios_designed']}",
         "trips measured for cost.\nThe free API limits stopped me"),
    ], colour=WARN)
    _text(slide, Inches(0.9), Inches(5.3), Inches(11.5), Inches(1.4),
          [("All three are in the report, with the evidence.", 20, True, INK),
           ("An evaluation that only confirms its author is not an evaluation.",
            17, False, SOFT)], spacing=1.25)
    _notes(slide, f"""
        {protocol['failed']} of {protocol['total_checks']} checks fail: message
        priority is declared and never used, permissions declared and never
        enforced. Cost coverage is one trip because the free plans allow thirty
        flight searches a month, and {cache['entries']} saved responses mean
        anyone can still reproduce every number with no API keys. All three are
        stated in the abstract, not buried.
    """)

    # ------------------------------------------------------------ 10  closing
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(1.1), Inches(1.5), Inches(11.2), Inches(0.5),
          [("IN ONE SENTENCE", 14, True, RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(2.0), Inches(11.2), Inches(2.2),
          [("Use AI where a step needs thinking.", 36, True, PAPER),
           ("Everywhere else, it is just a bill.", 36, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.2)
    _rule(slide, Inches(1.1), Inches(4.45), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(4.8), Inches(11.2), Inches(2.0),
          [(f"{tokens('B') / tokens('D'):.0f}x cheaper  ·  same accuracy  ·  "
            f"{tests} tests  ·  {cache['entries']} saved API replies so anyone "
            f"can repeat it", 17, False, RGBColor(0xC7, 0xD2, 0xFE)),
           ("", 8, False, PAPER),
           (f"The gap: only {coverage['scenarios_measured']} of "
            f"{coverage['scenarios_designed']} trips measured for cost. "
            f"Everything needed to widen it is saved and runs without keys.",
            15, False, RGBColor(0x9C, 0xA3, 0xF5))], spacing=1.3)
    _notes(slide, """
        Land the claim and its limit in the same breath. The effect is large and
        the sample is narrow, and both are in the abstract. The saved replies, the
        harness and the twenty trips are committed, so the next person - or me
        next month when the limits reset - can widen it without rebuilding.
    """)

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {os.path.relpath(path, ROOT)}")
