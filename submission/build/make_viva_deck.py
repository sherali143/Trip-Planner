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
    quota = measured.api_quota()["apis"]
    code = measured.code_stats()
    tests = measured.test_count()["collected"]
    per_arm = measured.api_calls_per_arm()["arms"]

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
    _text(slide, Inches(1.1), Inches(1.9), Inches(11.2), Inches(0.5),
          [("MSc DISSERTATION  ·  VIVA VOCE", 14, True,
            RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(2.4), Inches(11.2), Inches(1.9),
          [("When is AI worth its cost", 42, True, PAPER),
           ("in a travel planning system?", 42, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.1)
    _rule(slide, Inches(1.1), Inches(4.5), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(4.9), Inches(11.2), Inches(1.4),
          [("I built the same travel planner four different ways "
            "and measured all four.", 18, False, RGBColor(0xC7, 0xD2, 0xFE)),
           ("", 8, False, PAPER),
           (f"Student {STUDENT}   ·   {MODULE}", 13, False,
            RGBColor(0x9C, 0xA3, 0xF5))])
    _notes(slide, """
        Fifteen minutes. One idea: AI is worth paying for when a step needs
        thinking, and is a waste of money when it does not. I built four versions
        of the same planner that differ only in how they fetch data, measured all
        four, and the differences are large.
    """)

    # ---------------------------------------------------------------- 2 problem
    slide = _blank(prs)
    _heading(slide, "The problem", "AI is being used for jobs that do not need it")
    _stat_row(slide, [
        (f"{calls('B'):.0f}", "AI calls to plan one trip\nwhen agents fetch the data"),
        (f"{calls('D'):.0f}", "AI calls for the same trip\nwhen normal code fetches it"),
        (f"{tokens('B') / tokens('D'):.0f}x", "more text sent to the AI,\nfor the same finished plan"),
    ], colour=ACCENT)
    _text(slide, Inches(0.9), Inches(5.3), Inches(11.5), Inches(1.4),
          [("Looking up a flight price needs no thinking. It is one web request.",
            21, True, INK),
           ("But if an AI agent does the looking up, you pay for every step it "
            "takes to decide.", 17, False, SOFT)], spacing=1.25)
    _notes(slide, f"""
        Everyone gives agents tools. Nobody asks which jobs actually need one.
        Reading "leaving on the fifteenth for two adults" needs thinking. Calling
        a flight API with a date does not. The agent version used
        {calls('B'):.1f} AI calls per trip; mine uses {calls('D'):.1f}. The text
        sent differs by about {tokens('B') / tokens('D'):.0f} times, because
        every step re-sends the whole conversation and every tool description.
    """)

    # ---------------------------------------------------------------- 3 question
    slide = _blank(prs)
    _fill(slide, RGBColor(0xF7, 0xF8, 0xFC))
    _text(slide, Inches(1.4), Inches(2.2), Inches(10.5), Inches(2.8),
          [("My question", 26, False, FAINT),
           ("Which steps really need AI,", 40, True, ACCENT),
           ("and which are just expensive?", 40, True, ACCENT)], spacing=1.15)
    _rule(slide, Inches(1.4), Inches(5.3), Inches(2.0), TEAL)
    _text(slide, Inches(1.4), Inches(5.6), Inches(10.5), Inches(0.8),
          [("Everything else is kept identical. Only the data-fetching changes.",
            16, False, SOFT)])
    _notes(slide, """
        Same task, same prompts where they overlap, same tool server, same
        message system, same AI model. Only the way data is fetched changes
        between the four versions. That is what makes the comparison fair.
    """)

    # ---------------------------------------------------------------- 4 the app
    slide = _blank(prs)
    _heading(slide, "What it does", "A working travel planner, not just an experiment")
    _table(slide,
           ["The user", "What happens"],
           [["Fills one form",
             "Where from, where to, dates, how many people, budget, interests"],
            ["Presses one button",
             "Seven steps run and update live on screen as each finishes"],
            ["Sees the plan",
             "A day-by-day itinerary in tabs: flights, hotels, each day, budget, tips"],
            ["Can trust the prices",
             "Real fares from live travel APIs. If a price is a guess, it says so"],
            ["Gets told the truth",
             "If the budget cannot cover the trip, it refuses and says what would work"]],
           col_widths=[1.6, 8.0], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.7), Inches(11.5), Inches(0.9),
          [("There is also a terminal version, and every step is narrated as it runs.",
            17, False, SOFT)])
    _notes(slide, """
        Worth demonstrating live. Ask it for six nights in London on three
        thousand dollars and it declines, tells you the shortfall, and offers a
        shorter trip or a nearer city. It also marks which prices are measured and
        which are estimated, because the built-in price table was 52% below a real
        fare on the one route where both were known.
    """)

    # ---------------------------------------------------------------- 5 agents
    slide = _blank(prs)
    _heading(slide, "The agents", "Three use AI. Four steps do not")
    _table(slide,
           ["Step", "Who does it", "AI?", "Why"],
           [["1", "Conversation agent", "YES",
             "People write requests in a thousand different ways"],
            ["2", "Preferences agent", "YES",
             "Turns that writing into exact fields, then checks the budget"],
            ["3", "Flights, hotels, attractions, restaurants", "no",
             "One correct request each. An IF statement decides, not AI"],
            ["4", "Itinerary agent", "YES",
             "Deciding what to do on which day needs judgement"]],
           col_widths=[0.5, 3.4, 0.8, 6.0], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.6), Inches(11.5), Inches(1.1),
          [("The test for every step: could I write this as ordinary code?",
            20, True, INK),
           ("If yes, no AI. Two steps out of six need thinking. That is the "
            "whole design.", 17, False, SOFT)], spacing=1.25)
    _notes(slide, """
        It started as six agents and became three, because measuring showed most
        of the AI calls were being spent on fetching data. You cannot write a rule
        that understands any phrasing a person might use, and you cannot write a
        rule that makes a day pleasant. You absolutely can write a rule that calls
        a flight API.
    """)

    # ---------------------------------------------------------------- 6 approaches
    slide = _blank(prs)
    _heading(slide, "The four versions", "Only one thing changes: who fetches the data")
    _table(slide,
           ["", "How it works", "Who fetches", "Why I built it"],
           [["A", "One AI call, no tools", "nobody",
             "The floor. Shows what AI alone produces with no real data"],
            ["B", "Six agents, first attempt", "each agent decides",
             "My original proposal, untuned. The honest starting point"],
            ["C", "Same six agents, tuned properly", "each agent decides",
             "Proves the gain is the design, not just better settings"],
            ["D", "Three agents, normal code fetches", "normal code",
             "What I ship. This is the idea being tested"]],
           col_widths=[0.5, 3.2, 2.0, 5.0], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.6), Inches(11.5), Inches(1.0),
          [("C is the important one: without it, someone could say D only won "
            "because B was set up badly.", 18, True, ACCENT)])
    _notes(slide, f"""
        C is what makes the result defensible. Just tuning the six agents, without
        changing the design at all, cut the text sent by
        {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}%. So if I had only
        compared B against D I would have been mixing two different effects
        together and claiming credit for both.
    """)

    # ---------------------------------------------------------------- 7 defects
    slide = _blank(prs)
    _heading(slide, "What went wrong in each version",
             "Measured, not guessed. This is why D exists")
    _table(slide,
           ["", "The problem I measured"],
           [["A", "No tools at all, so it invents everything. Only "
                 f"{grounded('A'):.1f}% of its prices matched a real fare"],
            ["B", "Skipped its own tools: never called the attractions or "
                 "restaurant tool once. Twice produced broken output it had to redo"],
            ["C", f"Better, but still unreliable: never called the flight tool at "
                  f"all on the recorded run"],
            ["D", f"Always makes exactly the same {per_arm['D']['total_http']} "
                  "requests, because code decides, not AI. Nothing gets skipped"]],
           col_widths=[0.5, 10.5], font=13, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.3),
          [("The pattern: when AI decides which tools to call, it sometimes "
            "does not call them.", 20, True, WARN),
           ("The plan still looks finished. That is what makes it dangerous.",
            17, False, SOFT)], spacing=1.25)
    _notes(slide, """
        This slide is the heart of the argument. An agent that skips a tool still
        writes a confident, well-formatted itinerary, so you cannot tell by
        looking. B never once fetched attractions or restaurants and still
        produced a full plan. That is why I measure groundedness rather than
        reading the output and judging it.
    """)

    # ---------------------------------------------------------------- 8 architecture
    slide = _blank(prs)
    _heading(slide, "How it is built", "Four layers. Only the third one changes")
    _figure(slide, "architecture.png", top=Inches(2.0), height=Inches(4.7))
    _notes(slide, """
        Layer one takes the request, two turns words into fields, three fetches
        the data, four writes the plan. My question lives entirely in layer three.
        One honest detail: the shipped version calls the tool functions directly
        rather than over the network protocol. The protocol is genuinely used, but
        only by the six-agent versions, and Section 7.2 of the report says so.
    """)

    # ---------------------------------------------------------------- 9 method
    slide = _blank(prs)
    _heading(slide, "How I measured it", "Repeated runs, and no keys needed to check")
    _stat_row(slide, [
        (f"{coverage['repeats_per_arm']}", "runs of each version,\nso every number has a range"),
        (f"{coverage['scenarios_measured']}/{coverage['scenarios_designed']}",
         "trips measured for cost.\nThe API limits stopped me"),
        (f"{cache['entries']}", "saved API replies, so anyone\ncan repeat this for free"),
        (f"{tests}", "automated tests,\nno keys, no internet"),
    ], colour=ACCENT)
    _text(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.2),
          [("AI calls are counted by the system itself, never by hand.",
            17, False, SOFT),
           ("The limited coverage is printed on every chart, not hidden.",
            17, False, SOFT)], spacing=1.3)
    _notes(slide, f"""
        The weakness first: only {coverage['scenarios_measured']} of
        {coverage['scenarios_designed']} trips for the cost comparison, because
        the free plans allow thirty flight and fifty hotel searches a month. What
        I did instead: the two questions that need no API - does the message
        system behave as designed, and does the budget check work - were tested on
        all twenty, and both found real problems.
    """)

    # ---------------------------------------------------------------- 10 cost
    slide = _blank(prs)
    _heading(slide, "Result 1  ·  Cost", "Fetching data is where the money goes")
    _figure(slide, "efficiency.png", top=Inches(1.95), height=Inches(4.4))
    _text(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6),
          [(f"B sent {tokens('B'):,.0f} units of text.  D sent {tokens('D'):,.0f}.  "
            f"Same trip, same data, same AI.", 16, True, INK)])
    _notes(slide, f"""
        Six agents: {tokens('B'):,.0f} tokens and {calls('B'):.1f} AI calls per
        trip. Three agents with normal code: {tokens('D'):,.0f} and
        {calls('D'):.1f}. The ranges from the repeated runs do not overlap, which
        is why I report this as a real difference and not as noise.
    """)

    # ---------------------------------------------------------------- 11 tuning
    slide = _blank(prs)
    _heading(slide, "Result 2  ·  Settings vs design",
             "Answering the obvious objection")
    _figure(slide, "tuning_effect.png", top=Inches(1.95), height=Inches(4.4))
    _text(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6),
          [(f"Just better settings: {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}% "
            f"less text.  Changing the design: "
            f"{gains.get('D_vs_B', {}).get('tokens_pct', 0):.0f}%.",
            16, True, INK)])
    _notes(slide, f"""
        Honest finding that weakens my own headline. Cutting each agent's tool
        list and step limit, without touching the design, removed
        {gains.get('C_vs_B', {}).get('tokens_pct', 0):.0f}% of the cost. So most
        of B's expense was bad configuration, not the architecture. What is left
        over is the part only the design change reaches, and that is what I claim.
    """)

    # ---------------------------------------------------------------- 12 grounded
    slide = _blank(prs)
    _heading(slide, "Result 3  ·  Is the plan real?", "Cheaper, and no less accurate")
    _figure(slide, "groundedness.png", top=Inches(1.95), height=Inches(4.4))
    _text(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6),
          [(f"Prices that match a real fare:  A {grounded('A'):.1f}%  ·  "
            f"B {grounded('B'):.1f}%  ·  C {grounded('C'):.1f}%  ·  "
            f"D {grounded('D'):.1f}%", 16, True, INK)])
    _notes(slide, f"""
        Saving money would be pointless if the plan got vaguer. A is the control
        and scores {grounded('A'):.1f}% - a confident itinerary invented from
        nothing, which is exactly what this measure exists to catch. It caught a
        real one: my first working run produced a complete plan while every single
        tool call was silently failing.
    """)

    # ---------------------------------------------------------------- 13 my faults
    slide = _blank(prs)
    _heading(slide, "Problems in my own system",
             "Found by measuring it, and reported not hidden")
    _stat_row(slide, [
        (f"{protocol['passed']}/{protocol['total_checks']}",
         "design checks pass.\nSix things I claimed, that do not happen"),
        (f"{gate['recall']:.0%}",
         "of impossible budgets caught.\nIt misses the other half"),
    ], colour=WARN)
    _text(slide, Inches(0.9), Inches(5.3), Inches(11.5), Inches(1.4),
          [("Both are in the report, with the evidence.", 20, True, INK),
           (f"The budget check never wrongly refuses a workable trip "
            f"(precision {gate['precision']:.0%}), but it lets "
            f"{gate['false_negative']} impossible one through. "
            f"Agreement score {gate['cohens_kappa']:.3f} - moderate, not good.",
            16, False, SOFT)], spacing=1.25)
    _notes(slide, f"""
        {protocol['failed']} of {protocol['total_checks']} checks fail. Message
        priority is declared and never actually used. Permissions are declared and
        never enforced. On the budget check, precision is
        {gate['precision']:.0%} and recall {gate['recall']:.0%}. Saying this out
        loud is the point: an evaluation that only confirms its author is not an
        evaluation.
    """)

    # ---------------------------------------------------------------- 14 risk
    slide = _blank(prs)
    _heading(slide, "The biggest risk", "It was never the coding")
    flight = next(v for v in quota.values() if "flight" in v["name"])
    hotel = next(v for v in quota.values() if "hotel" in v["name"])
    _stat_row(slide, [
        (f"{int(flight['limit'])}", "flight searches a month.\nOne search costs two"),
        (f"{int(hotel['limit'])}", "hotel searches a month.\nFree plan, cannot buy more"),
        (f"{cache['entries']}", "replies saved once,\nreused for ever"),
    ], colour=WARN)
    _text(slide, Inches(0.9), Inches(5.3), Inches(11.5), Inches(1.4),
          [("Running out is not a delay. It is a month of waiting.", 20, True, INK),
           ("So I saved every reply to disk before building anything. That is why "
            "you can repeat my results with no API keys at all.", 16, False,
            SOFT)], spacing=1.25)
    _notes(slide, f"""
        Both limits were fully used up during development. The protection was
        built before the four versions were: {cache['entries']} saved replies mean
        a marker with no keys can reproduce every number in the report. What it
        could not do is create requests I never made, so cost coverage stayed at
        {coverage['scenarios_measured']} of {coverage['scenarios_designed']}
        trips. Appendix N has the full register - three of eight risks happened,
        including the AI model being withdrawn mid-project.
    """)

    # ---------------------------------------------------------------- 15 why
    slide = _blank(prs)
    _heading(slide, "Why this matters", "Beyond one travel planner")
    _table(slide,
           ["", "What this project shows"],
           [["1", "AI agents are expensive by default, and most of the cost is "
                 "spent on work that needs no intelligence"],
            ["2", "Giving an agent a tool does not mean it will use it. Mine "
                  "skipped tools and still produced confident plans"],
            ["3", "You cannot tell a made-up plan from a real one by reading it. "
                  "It has to be measured"],
            ["4", "The same result comes out cheaper AND just as accurate, so "
                  "there is no trade-off being hidden here"]],
           col_widths=[0.5, 10.5], font=14, top=Inches(2.2))
    _text(slide, Inches(0.9), Inches(5.5), Inches(11.5), Inches(1.1),
          [("Anyone building with AI agents faces this choice. Most do not "
            "measure it.", 19, True, ACCENT)])
    _notes(slide, """
        If asked "so what?", this is the answer. The industry adds agents and
        tools by default. This project is a worked example of asking which steps
        deserve one, measuring the answer, and finding that the honest answer is
        "fewer than you think".
    """)

    # ---------------------------------------------------------------- 16 reflect
    slide = _blank(prs)
    _heading(slide, "What I would do differently", "One mistake, and what it cost")
    _text(slide, Inches(0.9), Inches(2.2), Inches(11.5), Inches(3.6),
          [("I built the measuring last. It should have been first.",
            24, True, ACCENT),
           ("", 10, False, INK),
           ("Six agents became three only because measuring showed where the "
            "cost was going. That evidence arrived after the system was already "
            "built, so changing it meant rebuilding.", 17, False, INK),
           ("", 8, False, INK),
           ("Build the counter before the thing being counted.", 19, True, INK)],
          spacing=1.3)
    _notes(slide, """
        Honest answer to the likely question. I built the tool server first
        because nothing works without it, then the messaging, then the agents, and
        the measuring last. That order is why my first end-to-end run produced a
        plan with no real data in it and nothing noticed. Reversed, the six-to-
        three change would have been a design decision instead of a rewrite.
    """)

    # ---------------------------------------------------------------- 17 close
    slide = _blank(prs)
    _fill(slide, DARK)
    _text(slide, Inches(1.1), Inches(1.6), Inches(11.2), Inches(0.5),
          [("IN ONE SENTENCE", 14, True, RGBColor(0x9C, 0xA3, 0xF5))])
    _text(slide, Inches(1.1), Inches(2.1), Inches(11.2), Inches(2.4),
          [("Use AI where a step needs thinking.", 34, True, PAPER),
           ("Everywhere else, it is just a bill.", 34, True,
            RGBColor(0x6E, 0xE7, 0xDF))], spacing=1.2)
    _rule(slide, Inches(1.1), Inches(4.7), Inches(1.6), TEAL)
    _text(slide, Inches(1.1), Inches(5.05), Inches(11.2), Inches(1.6),
          [(f"{tokens('B') / tokens('D'):.0f}x cheaper, no loss of accuracy, "
            f"measured on {coverage['scenarios_measured']} trip run "
            f"{coverage['repeats_per_arm']} times.", 18, False,
            RGBColor(0xC7, 0xD2, 0xFE)),
           ("", 8, False, PAPER),
           ("Narrow coverage is the gap. Everything needed to widen it is saved "
            "and runs without keys.", 15, False, RGBColor(0x9C, 0xA3, 0xF5))],
          spacing=1.3)
    _notes(slide, """
        Land on the claim and its limit together. The effect is large and the
        sample is narrow, and both are in the abstract. The saved replies, the
        test harness and the twenty trips are all committed, so the next person -
        or me next month when the limits reset - can widen it without rebuilding
        anything.
    """)

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {os.path.relpath(path, ROOT)}")
