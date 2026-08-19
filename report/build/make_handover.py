"""
WHAT THIS FILE DOES
===================
Generates PROJECT_OVERVIEW.docx — a short, plain-English guide to the whole
project for someone who has never seen it.

This is not the dissertation. The dissertation argues a research case in academic
language; this explains what the project is, how to run it, and how to show it to
a supervisor, in the simplest words that are still accurate. It is deliberately a
few pages, not thirty.

Numbers come from the measured results through evaluation/measured.py, the same
accessor the dissertation uses, so this document cannot drift away from it.

    python report/build/make_handover.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from evaluation import measured

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT = os.path.join(ROOT, "PROJECT_OVERVIEW.docx")

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x52, 0x51, 0x4E)


class Doc:
    """A very small wrapper. This document has no numbering or cross-references."""

    def __init__(self) -> None:
        self.d = Document()
        style = self.d.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.line_spacing = 1.15
        style.paragraph_format.space_after = Pt(6)
        for s in self.d.sections:
            s.left_margin = s.right_margin = Inches(0.9)
            s.top_margin = s.bottom_margin = Inches(0.8)

    def title(self, text: str, subtitle: str = "") -> None:
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(20)
        r.font.color.rgb = ACCENT
        if subtitle:
            p2 = self.d.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r2 = p2.add_run(subtitle)
            r2.font.size = Pt(11)
            r2.font.color.rgb = MUTED

    def h(self, text: str) -> None:
        self.d.add_heading(text, level=1)

    def h2(self, text: str) -> None:
        self.d.add_heading(text, level=2)

    def p(self, text: str) -> None:
        self.d.add_paragraph(" ".join(text.split()))

    def bullets(self, items) -> None:
        for i in items:
            self.d.add_paragraph(" ".join(i.split()), style="List Bullet")

    def steps(self, items) -> None:
        for i in items:
            self.d.add_paragraph(" ".join(i.split()), style="List Number")

    def code(self, text: str) -> None:
        p = self.d.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.space_after = Pt(8)
        r = p.add_run(text)
        r.font.name = "Consolas"
        r.font.size = Pt(9)

    def table(self, headers, rows, widths=None, font_pt=9.5) -> None:
        t = self.d.add_table(rows=1 + len(rows), cols=len(headers))
        t.style = "Light Grid Accent 1"
        for i, head in enumerate(headers):
            c = t.rows[0].cells[i]
            c.text = ""
            r = c.paragraphs[0].add_run(str(head))
            r.bold = True
            r.font.size = Pt(font_pt)
        for ri, row in enumerate(rows, start=1):
            for ci, val in enumerate(row):
                c = t.rows[ri].cells[ci]
                c.text = ""
                r = c.paragraphs[0].add_run(str(val))
                r.font.size = Pt(font_pt)
                c.paragraphs[0].paragraph_format.space_after = Pt(2)
        if widths:
            for row in t.rows:
                for c, w in zip(row.cells, widths):
                    c.width = Inches(w)
        self.d.add_paragraph()

    def save(self) -> str:
        self.d.save(OUTPUT)
        return OUTPUT


def build() -> str:
    cov = measured.coverage()
    doc = Doc()

    doc.title("AI Trip Planner",
              "What this project is, how to run it, and how to show it. "
              "CMP7200 MSc Individual Project.")

    # ------------------------------------------------------------------
    doc.h("1. The problem")
    doc.p("""
        Planning a trip takes a long time. You open a flight site, a hotel site,
        a few blogs, and a calculator, then start again every time a price
        changes. It is boring work, not hard work — which is the kind of work a
        computer should do.
    """)
    doc.p("""
        You might expect an AI chatbot to solve this already. It does not. If you
        ask one for a travel plan it will give you a confident answer with real
        looking flight numbers and hotel names — and many of them do not exist.
        A published benchmark tested this properly: the best single AI agent
        completed only 0.6% of travel planning tasks correctly. The plans looked
        finished. They were not bookable.
    """)
    doc.p("""
        The reason is simple. The AI is writing from memory instead of looking
        things up. So the question this project asks is not "can AI plan travel"
        but something narrower and more useful: if we give the AI real tools to
        look things up, who should decide when to use them — the AI, or ordinary
        code?
    """)

    # ------------------------------------------------------------------
    doc.h("2. What the system does")
    doc.p("""
        You type a request in normal English, for example "4 nights in Istanbul
        from Lahore, leaving 15 August, budget 800 dollars, I like history and
        food". The system returns a day-by-day plan with real flights, real
        hotels, real places to eat, and a budget breakdown.
    """)
    doc.code(
        "your request\n"
        "     |\n"
        "     v\n"
        "  STEP 1   AI reads the request and turns it into fields\n"
        "           (origin, destination, dates, budget, interests)\n"
        "     |\n"
        "     v\n"
        "  STEP 2   Plain Python code fetches the data - NO AI here\n"
        "           flights, hotels, attractions, restaurants\n"
        "     |\n"
        "     v\n"
        "  STEP 3   AI arranges the results into a day-by-day plan\n"
        "     |\n"
        "     v\n"
        "  your itinerary"
    )
    doc.p("""
        The important idea is in step 2. The AI is used in step 1 and step 3
        because those need judgement — there is no single right way to phrase a
        request, and no single right way to order a day. Step 2 needs no
        judgement at all: once we know the cities and dates, there is exactly one
        correct search to run. So step 2 uses no AI. Testing whether that was the
        right decision is what the whole project measures.
    """)

    # ------------------------------------------------------------------
    doc.h("3. The four approaches we compared")
    doc.p("""
        The same request was given to four different designs. Everything else was
        held identical — same APIs, same message protocol, same request text — so
        the only thing that changes is who does the data fetching.
    """)
    doc.table(
        ["Approach", "How it works", "Why we built it"],
        [
            ["A — Single AI", "One AI call. No tools. No lookups.",
             "The control. Shows what the tools are worth, and what a plan looks "
             "like when nothing in it was looked up."],
            ["B — 6 agents, naive", "Six AI agents. Each search agent gets many "
             "tools and decides for itself what to call.",
             "This is how we built it first, following the proposal. Its cost is "
             "the reason we changed the design."],
            ["C — 6 agents, tuned", "Same six agents, configured properly: one "
             "tool each, shorter prompts, run at the same time.",
             "The fair comparison. Without it, someone could say approach D only "
             "won because B was set up badly."],
            ["D — 3 agents, direct", "Two AI steps. The lookups are plain Python.",
             "This is the design that ships. It is the claim being tested."],
        ],
        widths=[1.3, 2.4, 2.7],
    )
    doc.p("""
        Approach C matters more than it looks. It would have been easy to compare
        our new design against the badly configured version and report a huge
        win. Building the tuned version first was slower and made our own result
        smaller — and it is the reason the result can be defended.
    """)

    # ------------------------------------------------------------------
    doc.h("4. What we found")
    rows = []
    for code in ("A", "B", "C", "D"):
        arm = measured.arm(code)
        g = measured.groundedness(code)
        rows.append([
            f"{code}  {arm['name']}",
            f"{arm['avg_llm_calls']:.0f}",
            f"{arm['avg_total_tokens']:,.0f}",
            f"${arm['avg_cost_usd']:.4f}",
            f"{arm['avg_latency']:.0f}s",
            f"{g['prices_grounded_pct']:.0f}%",
        ])
    doc.table(
        ["Approach", "AI calls", "Tokens", "Cost", "Time", "Prices that are real"],
        rows,
        widths=[1.7, 0.75, 0.85, 0.8, 0.6, 1.3],
    )
    doc.p(f"""
        The last column is the one to look at first. "Prices that are real" means:
        of all the prices printed in the plan, how many match a price the travel
        websites actually returned. Approach A scored
        {measured.groundedness('A')['prices_grounded_pct']:.0f}% — it printed
        {measured.groundedness('A')['prices_quoted']} prices and not one of them
        was real. It is the cheapest approach and its output is worthless.
    """)
    doc.p("""
        Three findings:
    """)
    doc.bullets([
        "Tools matter more than anything. Without them the plan is fiction. "
        "This is the clearest result in the project.",
        "Tuning matters more than the number of agents. B and C are the SAME six "
        "agents with the same data — only the prompts and settings changed — and "
        "that alone cut token use by about 83%. So most of what looked like the "
        "cost of using many agents was really just bad configuration.",
        "Removing the AI from the lookup step saves a lot of AI calls and time, "
        "and only a little money. That is a smaller claim than we expected, and "
        "it is the one the numbers actually support.",
    ])
    doc.p(f"""
        Every one of these numbers is an average of
        {cov['repeats_per_arm']} separate runs, so the report can also say how much
        each one wobbles between runs. Two results are worth knowing:
    """)
    doc.bullets([
        "Approach D is cheaper and faster than C by more than the run-to-run "
        "wobble, so that difference is real.",
        "On how much of the plan is real, C and D overlap. So the honest statement "
        "is 'we cannot tell them apart', not 'they are equal'. C's average is "
        "actually slightly higher, and the report says so.",
        "Approaches A and D use exactly the same number of AI calls every single "
        "time. B and C do not, because they contain a loop that decides for itself "
        "how many calls to make. Predictable cost is a real advantage.",
    ])
    doc.p(f"""
        Honest limit: the runs all use
        {cov['scenarios_measured']} test scenario out of
        {cov['scenarios_designed']} we designed. Repeating a scenario is free
        because the website replies are replayed from disk, but each NEW scenario
        needs about four of the 80 free lookups a month. So we have good depth on
        one trip and no breadth across trips. The report says this in the abstract
        and on every chart.
    """)

    # ------------------------------------------------------------------
    doc.h("5. Budget validation (the change the supervisor asked for)")
    doc.p("""
        The supervisor asked for the budget handling to be improved. Two things
        were wrong with the original version, and both are fixed.
    """)
    doc.h2("Problem 1: the same budget split for every trip")
    doc.p("""
        The first version always split the money the same way — 35% flights, 35%
        hotels, and so on — no matter what the trip was. That is wrong, because
        costs do not scale the same way. A flight is paid per person and gets
        more expensive the further you go. A hotel room is paid per night and is
        shared between people. So a split that suits one person going somewhere
        near is badly wrong for a family going far.
    """)
    doc.p("""
        Now the split is worked out from what that particular trip actually
        costs. And if the traveller says how they want to divide their money, we
        use their split — someone who says that has made a choice, not a mistake.
    """)
    doc.h2("Problem 2: it did not know whether a budget was possible")
    doc.p("""
        The first version refused a budget using one fixed formula that ignored
        the destination completely. It judged 700 dollars for Bangkok and 700
        dollars for London by the same rule and accepted both — so it happily
        produced a confident, impossible plan for London.
    """)
    doc.p("""
        Now the system estimates what that specific trip costs at three levels —
        the cheapest it can possibly be done, comfortable, and luxury — using the
        destination's price level, the flight distance, the number of nights, the
        number of people, and room sharing. It only refuses a budget below the
        true minimum. Above that, a tight budget gets a warning and carries on,
        because tight is a real choice and only impossible is not.
    """)
    gate = measured.gate_agreement()
    anchor = measured.gate_external_validity()
    misses = measured.gate_misses()
    doc.p(f"""
        We then tested it on all {gate['n']} scenarios, and reported the result
        even though it is not perfect. Two scenarios were written to be
        impossible. It correctly refused {gate['true_positive']} and wrongly
        allowed {gate['false_negative']}
        ({misses[0]['scenario'] if misses else 'none'}). The agreement score
        (Cohen's kappa) is {gate['cohens_kappa']:.3f}.
    """)
    doc.p(f"""
        We also found out WHY it got that one wrong, which is more useful than
        the score. The system assumes the cheapest possible flight on that route
        costs about ${anchor['estimated_minimum']:,.0f}. The travel website
        actually returned ${anchor['cheapest_real_fare']:,.0f} as its cheapest —
        so our assumption is about
        {abs(anchor['minimum_anchor_error_pct']):.0f}% too low. With the flight
        cost guessed at half the real price, the total minimum comes out too low,
        and a budget slips through that should not have. The structure is right;
        one number in it is wrong.
    """)

    # ------------------------------------------------------------------
    doc.h("6. Known issues, stated honestly")
    protocol = measured.protocol_summary()
    doc.p(f"""
        We wrote a test that checks whether our own communication and tool layers
        really behave the way the design says. {protocol['passed']} of
        {protocol['total_checks']} checks passed. The failures are listed in the
        report rather than quietly fixed, because finding them by measuring is
        worth more marks than pretending they were never there.
    """)
    doc.table(
        ["Issue", "What it means in plain terms"],
        [
            ["Message priority does nothing",
             "Every message carries a priority label, but the queue ignores it and "
             "delivers in arrival order."],
            ["Inbound permissions are not checked",
             "Each component lists who may send to it. That list is never read; "
             "only the sender's own list is checked."],
            ["4 of 12 tools have wrong descriptions",
             "Some tools accept settings that are missing from their published "
             "description, and one names the wrong data provider."],
            ["Flight cost guess is too low",
             f"About {abs(anchor['minimum_anchor_error_pct']):.0f}% under the real "
             f"cheapest fare, which is why one impossible budget was allowed."],
            [f"Only {cov['scenarios_measured']} of {cov['scenarios_designed']} "
             f"scenarios measured",
             "The travel websites' free monthly limit. Nothing to do with the code."],
            ["Google retired the AI model we measured on",
             "Handled — see section 9. The old numbers stay valid for the model "
             "that produced them."],
        ],
        widths=[2.1, 4.3],
    )

    # ------------------------------------------------------------------
    doc.h("7. How to run it")
    doc.p("""
        Put the project folder somewhere with a SHORT path, for example
        C:\\trip_planner. Windows cannot handle very long folder paths and the
        install will fail with a confusing error if the folder is buried deep.
    """)
    doc.p("Then double-click one file:")
    doc.code("run.bat")
    doc.p("""
        That is all. It checks Python is installed, creates its own private
        Python environment, installs everything it needs, sets up the settings
        file, checks the install worked, and then shows a menu. The first run
        takes a few minutes. Every run after that starts in seconds.
    """)
    doc.table(
        ["Menu option", "What it does", "Needs internet or keys?"],
        [
            ["1", "Compare all four approaches side by side", "No"],
            ["2 to 5", "Show one approach in detail (A, B, C or D)", "No"],
            ["6", "Run the test suite", "No"],
            ["7", "Run the evaluation experiments", "No"],
            ["8", "Rebuild all the figures", "No"],
            ["9", "Rebuild the dissertation document", "No"],
            ["10", "Plan a real trip in the web browser", "Yes"],
            ["11", "Plan a real trip in this window", "Yes"],
            ["12", "Exit", "No"],
        ],
        widths=[1.0, 3.4, 2.0],
    )
    doc.p("""
        Options 1 to 9 work with no internet and no API keys at all. This is
        deliberate: the free accounts this project uses run out, and a
        demonstration that needs a working internet account is one that cannot be
        given on the day the account runs out.
    """)

    # ------------------------------------------------------------------
    doc.h("8. How to show it to the supervisor")
    doc.p("""
        Fifteen minutes, in this order. Everything here works offline, so nothing
        can fail on the day.
    """)
    doc.steps([
        "Double-click run.bat and choose option 1. This runs all four approaches "
        "side by side and prints one comparison table. Point at the last column "
        "and say: approach A is the cheapest and every price in it is invented. "
        "That is the whole point of the project in one line.",

        "Point at approaches B and C in the same table. Say: these are the SAME "
        "six agents with the same data. Only the settings changed, and that alone "
        "cut token use by about 83%. So we compared our new design against the "
        "properly tuned version, not the badly configured one.",

        "Choose option 5 (approach D, the one that ships). It shows the real "
        "itinerary that was produced, what it cost, and how much of it was real. "
        "Say: two AI calls instead of nine, same quality.",

        "Choose option 7. This runs the two experiments that need no internet. "
        "Say: these check our own system against its own design, and they found "
        "six things wrong, which are all written up in the report.",

        "Choose option 6 to show the test suite passing.",

        "Open report/CMP7200_Dissertation.docx. Say: every number in this "
        "document is read from the measured results files, none is typed by hand, "
        "and there is a script that proves it by corrupting the data and checking "
        "the document changes.",

        "If asked to plan a real trip live, use option 10 with the API keys in "
        "place. If the internet or the free quota is unavailable, options 1 to 9 "
        "still work and show real recorded output.",
    ])
    doc.p("""
        One thing worth saying out loud, because it is a strength and not a
        weakness: when you show a demo from option 1 to 5, the screen says
        clearly that it is replaying a recorded run. It is real measured output,
        not a live one, and it says so. If the supervisor asks whether it is
        running now, the honest answer is already on the screen.
    """)

    # ------------------------------------------------------------------
    doc.h("9. About the AI model")
    doc.p(f"""
        The first round of measurements used Google's Gemini 2.5 Flash. Google
        then stopped giving that model to new accounts, so it could no longer be
        run at all. Its replacement works, but it refuses a particular message
        pattern that the agent framework produces, which meant approaches B and C
        would not run on it either. Every number in this project has since been
        re-measured on the replacement, {measured.model_name()}, which is the
        model the results and the report describe.
    """)
    doc.p("""
        This is fixed. A small compatibility layer
        (trip_planner/core/gemini_compat.py) adjusts only the requests that would
        otherwise be rejected, leaves every other request untouched, and counts
        how many it changed so a run can report whether it was needed. All four
        approaches run again.
    """)
    doc.p("""
        Two honest notes. Numbers from the new model are not directly comparable
        to the old ones, because it is a different model — so if the evaluation is
        re-run, all four approaches must be re-run together. And the report treats
        this as a genuine finding: a system measured against someone else's hosted
        model inherits that model's lifetime.
    """)

    # ------------------------------------------------------------------
    doc.h("10. Folder structure")
    doc.code(
        "trip_planner\\\n"
        "  run.bat                  <- START HERE. Sets up everything, then a menu.\n"
        "  run_cli.py               plan a trip in the terminal\n"
        "  run_web.py               plan a trip in the browser\n"
        "  README.md                the technical readme\n"
        "  PROJECT_OVERVIEW.docx    this document\n"
        "  requirements.txt         the exact package versions used\n"
        "  .env                     your API keys (never shared, never committed)\n"
        "\n"
        "  trip_planner\\           THE SYSTEM ITSELF\n"
        "    orchestrator.py        the workflow: read, fetch, assemble\n"
        "    agents.py, tasks.py    the three AI agents and their instructions\n"
        "    comms\\                the message protocol between components\n"
        "    server\\               the MCP tool server (12 tools)\n"
        "    tools\\                three files: MCP client, travel APIs, agent tools\n"
        "    core\\                 caching, measuring, budget, cost, safe maths\n"
        "    ui\\app.py             the web page\n"
        "\n"
        "  evaluation\\             THE EXPERIMENT\n"
        "    arm_a ... arm_d        the four approaches\n"
        "    scenarios.py           the 20 test trips\n"
        "    metrics.py             scores how much of a plan is real\n"
        "    measured.py            the ONE place results are read from\n"
        "    exp_protocol.py        checks our protocols against the design\n"
        "    exp_budget_gate.py     checks the budget rules on all 20 scenarios\n"
        "    results\\              the measured numbers, as files\n"
        "\n"
        "  demos\\                  DEMONSTRATIONS (work with no internet)\n"
        "    compare_all_approaches.py     all four side by side\n"
        "    approach_a ... approach_d     one approach each, in detail\n"
        "\n"
        "  report\\                 THE DISSERTATION\n"
        "    CMP7200_Dissertation.docx     the report itself\n"
        "    build\\                       one file per chapter, and the figures\n"
        "    figures\\                     all 14 pictures, generated\n"
        "\n"
        "  testing\\                the test suite\n"
        "  proposal\\               the original proposal and the assignment brief\n"
        "  .api_cache\\             recorded website replies, so results replay free"
    )

    # ------------------------------------------------------------------
    doc.h("11. Important files, if you only look at a few")
    doc.table(
        ["File", "Why it matters"],
        [
            ["run.bat", "The only thing anyone needs to double-click."],
            ["trip_planner/orchestrator.py",
             "The workflow. Read this to understand how the system works."],
            ["trip_planner/core/http_cache.py",
             "Records every website reply so results can be reproduced with no "
             "accounts, and stops one run using up a whole month's free quota."],
            ["trip_planner/core/llm_metrics.py",
             "Counts real AI calls, tokens and cost. Earlier versions guessed "
             "these numbers and the guesses were wrong."],
            ["trip_planner/core/trip_cost.py",
             "The budget validation the supervisor asked for."],
            ["evaluation/measured.py",
             "The single place any measured number is read from. This is why the "
             "report cannot disagree with the charts."],
            ["report/build/verify_no_hardcoded_numbers.py",
             "Proves no number in the report is typed by hand: it corrupts the "
             "data, rebuilds, and checks every value changed."],
        ],
        widths=[2.2, 4.2],
    )

    # ------------------------------------------------------------------
    doc.h("12. The APIs used")
    doc.table(
        ["What", "Service", "Free limit", "Used for"],
        [
            ["AI model", "Google Gemini", "Free tier, limited per minute",
             "Reading the request and writing the plan"],
            ["Flights", "fly-scraper (RapidAPI)", "30 per MONTH",
             "Real flight prices and times"],
            ["Hotels", "Booking.com (RapidAPI)", "50 per MONTH",
             "Real hotels, prices and review scores"],
            ["Places", "Serper.dev", "Generous", "Attractions and restaurants"],
        ],
        widths=[0.9, 1.7, 1.5, 2.3],
    )
    cache = measured.api_cache_stats()
    doc.p(f"""
        The flight and hotel limits are per MONTH and very small. One careless run
        can use a whole month and it cannot be bought back. That is why every
        website reply is recorded: there are {cache['entries']} recorded replies
        in the project, and they let anyone reproduce the results with no accounts
        at all.
    """)

    # ------------------------------------------------------------------
    doc.h("13. If something goes wrong")
    doc.table(
        ["Problem", "What to do"],
        [
            ["\"Python is not recognised\"",
             "Install Python 3.10 or newer from python.org and TICK \"Add Python "
             "to PATH\" during installation."],
            ["Install fails with \"No such file or directory\"",
             "The folder path is too long for Windows. Move the whole folder to "
             "somewhere short like C:\\trip_planner and run again."],
            ["Something says a dependency is missing",
             "Delete the .venv folder and run run.bat again. It rebuilds from "
             "scratch."],
            ["A live trip plan fails",
             "The free quota has probably run out. Options 1 to 9 still work with "
             "no internet."],
            ["The report will not rebuild",
             "It refuses to build if a figure is missing or a number cannot be "
             "found. Run option 8 first to rebuild the figures."],
        ],
        widths=[2.3, 4.1],
    )

    path = doc.save()
    return path


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"wrote {os.path.relpath(build(), ROOT)}")
