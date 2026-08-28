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
    cache = measured.api_cache_stats()
    tests = measured.test_count()["collected"]
    per_arm = measured.api_calls_per_arm()["arms"]
    anchor = measured.gate_external_validity()

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

    def secs(letter):
        return arms[letter]["avg_latency"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # =============================================== 1  title, problem, solution
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
           ("A trip needs flights, hotels, places to visit and a budget that "
            "adds up.", 17, False, PAPER),
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
    _notes(slide, """
        Nine slides. A working travel planner, and one question inside it: which
        parts of it really need AI? I built it four ways and measured all four.
    """)

    # ============================================================= 2  the agents
    slide = _blank(prs)
    _heading(slide, "1  ·  The agents", "Each one has a name and one job")
    _table(slide,
           ["Agent", "What it does"],
           [["Travel Conversation Assistant",
             "Asks the traveller for anything missing"],
            ["Travel Preferences Extractor",
             "Turns those words into exact fields"],
            ["Flight Search Specialist", "Looks up flights"],
            ["Hotel Search Specialist", "Looks up hotels"],
            ["Activities Specialist",
             "Looks up places to visit and places to eat"],
            ["Itinerary Coordinator", "Writes the final day-by-day plan"]],
           col_widths=[4.0, 6.8], font=15, top=Inches(2.3))
    _text(slide, Inches(0.9), Inches(6.1), Inches(11.5), Inches(0.8),
          [("Six agents. The next four slides show which of them each approach "
            "uses, and what tools each one is given.", 17, False, SOFT)])
    _notes(slide, """
        Six agents. Two of them read what the traveller wrote, three look things
        up, and one writes the plan. Keep this slide up while naming them - the
        next four slides all refer back to these names.
    """)

    # ============================================================ 3  approach A
    slide = _blank(prs)
    _heading(slide, "2  ·  Approach A", "One AI on its own. No agents, no tools")
    _table(slide,
           ["Agent", "How many tools", "Which tools"],
           [["none — just one AI call", "0", "none"]],
           col_widths=[4.4, 2.6, 3.8], font=15, top=Inches(2.3))
    _text(slide, Inches(0.9), Inches(3.4), Inches(11.5), Inches(0.7),
          [("The AI writes the whole plan from what it already knows. It cannot "
            "look anything up.", 18, False, INK)])
    _stat_row(slide, [
        (f"{calls('A'):.0f}", "AI call"),
        (f"{grounded('A'):.1f}%", "of its prices were real"),
        (f"{secs('A'):.0f}s", "to finish"),
    ], top=Inches(4.3), colour=WARN)
    _text(slide, Inches(0.9), Inches(6.2), Inches(11.5), Inches(0.8),
          [("So it makes the prices up. This is the baseline everything else has "
            "to beat.", 20, True, WARN)])
    _notes(slide, f"""
        Say it plainly: Approach A shows what happens when AI plans a trip with no
        access to real travel data. It produced a confident, well-written
        itinerary and {grounded('A'):.1f}% of the prices in it matched anything
        real. Every other approach has to beat this.
    """)

    # ============================================================ 4  approach B
    slide = _blank(prs)
    _heading(slide, "3  ·  Approach B",
             "Six agents. Each one picks its own tools")
    _table(slide,
           ["Agent", "Tools", "Which tools"],
           [["Travel Preferences Extractor", "0", "none"],
            ["Flight Search Specialist", "4",
             "search_comprehensive_flights,  search_round_trip_flights,  "
             "search_internet,  calculate"],
            ["Hotel Search Specialist", "8",
             "search_hotels_comprehensive,  search_accommodations_with_location,  "
             "search_hotel_destination,  search_hotels_by_dest_id,  "
             "get_hotel_reviews,  get_attractions_near_hotel,  search_internet,  "
             "calculate"],
            ["Activities Specialist", "4",
             "search_attractions,  search_restaurants,  search_internet,  "
             "calculate"],
            ["Itinerary Coordinator", "4",
             "calculate,  search_internet,  search_attractions,  "
             "search_restaurants"],
            ["Total", "20", ""]],
           col_widths=[3.2, 0.9, 6.9], font=11, top=Inches(2.15))
    _text(slide, Inches(0.9), Inches(5.5), Inches(11.5), Inches(1.4),
          [(f"It used {calls('B'):.0f} AI calls and took {secs('B'):.0f} seconds "
            f"to plan one trip.", 20, True, INK),
           ("Too much freedom: the agents keep thinking and searching — and they "
            "still never called two of their own tools.", 17, True, WARN)],
          spacing=1.25)
    _notes(slide, f"""
        This was my original proposal. The hotel agent has eight tools and is
        allowed ten thinking steps, and every step is a separate AI call that
        re-sends the conversation and all eight tool descriptions. It took
        {calls('B'):.1f} AI calls and {secs('B'):.0f} seconds, gave broken output
        twice, and never once called the attractions or the restaurant tool -
        while still producing a plan that looked complete.
    """)

    # ============================================================ 5  approach C
    slide = _blank(prs)
    _heading(slide, "4  ·  Approach C",
             "The same six agents, but set up properly")
    _table(slide,
           ["Agent", "Tools", "Which tools"],
           [["Travel Preferences Extractor", "0", "none"],
            ["Flight Search Specialist", "1", "distilled_search_flights"],
            ["Hotel Search Specialist", "1", "distilled_search_hotels"],
            ["Activities Specialist", "2",
             "distilled_search_attractions,  distilled_search_restaurants"],
            ["Itinerary Coordinator", "0", "none"],
            ["Total", "4", ""]],
           col_widths=[3.2, 0.9, 6.9], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.0), Inches(11.5), Inches(1.9),
          [("Three changes: fewer tools each, only 3 thinking steps instead of "
            "15, and the AI is shown the best 3 results instead of 12,000 "
            "characters.", 17, False, INK),
           ("", 5, False, INK),
           (f"Result: {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}% less "
            f"text sent, and {calls('C'):.0f} AI calls instead of "
            f"{calls('B'):.0f}.", 20, True, ACCENT),
           ("Worth saying out loud: most of B's cost was bad setup, not the "
            "design.", 17, True, WARN)], spacing=1.2)
    _notes(slide, f"""
        Approach C is Approach B done properly, and it exists so nobody can say D
        only won because B was set up badly. Instead of handing the AI twelve
        thousand characters of hotel data, it gets three lines - Theodora Pension
        $33 10/10, and so on. Settings alone removed
        {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}% of the tokens. Being
        honest about that is what makes the next slide believable.
    """)

    # ============================================================ 6  approach D
    slide = _blank(prs)
    _heading(slide, "5  ·  Approach D",
             "Three agents. Plain Python does the searching")
    _table(slide,
           ["Agent", "Tools", "Which tools"],
           [["Travel Conversation Assistant", "0", "none"],
            ["Travel Preferences Extractor", "0", "none"],
            ["Itinerary Coordinator", "0",
             "none — the data is handed to it already"],
            ["Total", "0", ""]],
           col_widths=[3.2, 0.9, 6.9], font=13.5, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(4.25), Inches(11.5), Inches(0.5),
          [("The three search agents are gone. Plain Python fetches the flights, "
            "hotels, attractions and restaurants.", 18, True, INK)])
    _text(slide, Inches(0.9), Inches(4.8), Inches(11.5), Inches(0.5),
          [("(In the web app the coordinator keeps 4 helper tools — calculate, "
            "search_internet, search_attractions, search_restaurants. The "
            "measured run removes them.)", 12, False, SOFT)])
    _stat_row(slide, [
        (f"{calls('D'):.0f}", "AI calls"),
        (f"{secs('D'):.0f}s", "to finish"),
        (f"{per_arm['D']['total_http']}", "searches, every single time"),
    ], top=Inches(5.35), colour=ACCENT)
    _text(slide, Inches(0.9), Inches(7.0), Inches(11.5), Inches(0.4),
          [("Once we know the place and the dates, there is nothing left for AI "
            "to decide.", 16, False, SOFT)])
    _notes(slide, f"""
        This is the one that ships. AI understands the request, Python fetches the
        data, AI writes the plan. No agent holds a search tool in the measured
        run, so it makes exactly {per_arm['D']['total_http']} searches every time
        in the same order - an IF statement decides rather than a model, so
        nothing can be skipped, which is exactly what B and C both did. If asked
        about the four helper tools in the web app: they are on the coordinator
        for the interactive path, and the measured arm strips them so the
        comparison is clean.
    """)

    # ========================================================== 7  the comparison
    slide = _blank(prs)
    _heading(slide, "6  ·  All four side by side",
             f"Each one run {coverage['repeats_per_arm']} times")
    _table(slide,
           ["", "A  one AI", "B  6 agents", "C  6 tuned", "D  3 agents"],
           [["Tools given to agents", "0", "20", "4", "0"],
            ["AI calls", f"{calls('A'):.0f}", f"{calls('B'):.0f}",
             f"{calls('C'):.0f}", f"{calls('D'):.0f}"],
            ["Text sent to the AI", f"{tokens('A'):,.0f}", f"{tokens('B'):,.0f}",
             f"{tokens('C'):,.0f}", f"{tokens('D'):,.0f}"],
            ["Cost per trip", f"${arms['A']['avg_cost_usd']:.4f}",
             f"${arms['B']['avg_cost_usd']:.4f}",
             f"${arms['C']['avg_cost_usd']:.4f}",
             f"${arms['D']['avg_cost_usd']:.4f}"],
            ["Time", f"{secs('A'):.0f}s", f"{secs('B'):.0f}s",
             f"{secs('C'):.0f}s", f"{secs('D'):.0f}s"],
            ["Prices that were real", f"{grounded('A'):.1f}%",
             f"{grounded('B'):.0f}%", f"{grounded('C'):.0f}%",
             f"{grounded('D'):.0f}%"]],
           col_widths=[3.0, 2.0, 2.0, 2.0, 2.2], font=14, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.7), Inches(11.5), Inches(1.2),
          [("Being honest: D is not more accurate than C — their ranges overlap.",
            17, False, SOFT),
           (f"What D is: {tokens('C') / tokens('D'):.1f}x cheaper than C and "
            f"{tokens('B') / tokens('D'):.0f}x cheaper than B, with no drop in "
            f"accuracy.", 19, True, ACCENT)], spacing=1.3)
    _notes(slide, f"""
        Read the last row carefully. C is {grounded('C'):.0f}% and D is
        {grounded('D'):.0f}%, and their ranges overlap, so I cannot claim D is
        better grounded and I do not. What does not overlap is the token count.
        The claim is cheaper and faster with no measurable penalty - a smaller
        claim than the numbers first suggest, and the only one the data supports.
    """)

    # ======================================================== 8  what user sees
    slide = _blank(prs)
    _heading(slide, "7  ·  What the user sees",
             "And the check that stops an impossible trip")
    _figure(slide, "frontend.png", top=Inches(1.9), height=Inches(3.4))
    _stat_row(slide, [
        (f"${demo['budget']:,.0f}", "traveller asked for"),
        (f"${verdict.estimate.minimum:,.0f}", "cheapest it can be done"),
        ("REFUSED" if not verdict.feasible else "ALLOWED",
         "with three ways to fix it"),
    ], top=Inches(5.45), colour=WARN)
    _notes(slide, f"""
        Two things worth demonstrating. The seven step rows tick over live as each
        finishes, so the page never looks frozen. And the budget check: it works
        out the cheapest this trip could possibly cost, using the real recorded
        fare rather than a built-in table - the table said
        ${anchor['estimated_minimum']:,.0f} and the API returned
        ${anchor['cheapest_real_fare']:,.0f} - then refuses and offers a shorter
        trip, a bigger budget, or a nearer city.
    """)

    # ============================================================= 9  conclusion
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(1.1), Inches(1.4), Inches(11.2), Inches(0.5),
          [("IN ONE SENTENCE", 14, True, RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(1.9), Inches(11.2), Inches(2.0),
          [("AI decides what the user wants and how to show it.", 30, True,
            PAPER),
           ("Python decides what data to fetch.", 30, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.2)
    _rule(slide, Inches(1.1), Inches(4.1), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(4.45), Inches(11.2), Inches(2.4),
          [("WHAT I FOUND", 12, True, RGBColor(0x9C, 0xA3, 0xF5)),
           ("", 5, False, PAPER),
           ("1.  Without tools, AI makes travel prices up. Tools are essential.",
            17, False, RGBColor(0xC7, 0xD2, 0xFE)),
           (f"2.  Setup matters hugely — settings alone saved "
            f"{gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}% of the cost.",
            17, False, RGBColor(0xC7, 0xD2, 0xFE)),
           ("3.  Taking AI out of the searching is cheaper and faster, and just "
            "as accurate.", 17, False, RGBColor(0x6E, 0xE7, 0xDF)),
           ("", 5, False, PAPER),
           (f"Honest gap: only {coverage['scenarios_measured']} of "
            f"{coverage['scenarios_designed']} trips measured for cost, because "
            f"of the free API limits.", 14, False,
            RGBColor(0x9C, 0xA3, 0xF5))], spacing=1.25)
    _notes(slide, f"""
        Three findings from three comparisons: A against the rest shows tools are
        essential, B against C shows setup matters, C against D shows that
        removing AI from the searching costs nothing in quality. {tests} tests
        and {cache['entries']} saved API replies mean anyone can check all of it
        without an API key.
    """)

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {os.path.relpath(path, ROOT)}")
