"""
The web page renders, asks who is travelling, and refuses an incoherent request.

Why this file exists
--------------------
The form used to collect eight facts and none of them was the number of
travellers. The command-line agent asks it as its second question; the page never
did, so the preferences extractor supplied a figure from context — and that
figure multiplies airfare and meals inside the feasibility check. A budget was
being called possible or impossible partly on a number nobody had entered.

Nothing caught it because nothing tested the page at all. These tests drive the
real Streamlit script through Streamlit's own harness, so a page that raises on
render, loses a field, or runs the planner on an empty form fails here.

No model and no network: every test below stops before the planner is invoked.
The one thing not covered is a full planning run, which needs model requests —
that is exercised by hand and reported in the dissertation rather than pretended
at here.
"""

import datetime
import re

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest

APP = "trip_planner/frontend/app.py"


def _fresh():
    page = AppTest.from_file(APP, default_timeout=120)
    page.run()
    return page


def _labels(widgets):
    return [w.label for w in widgets]


# ---------------------------------------------------------------------------
# It renders
# ---------------------------------------------------------------------------

def test_the_page_renders_without_raising():
    """
    The first thing a supervisor sees. A Streamlit script that raises shows a
    traceback where the form should be, and nothing else on the page works.
    """
    page = _fresh()
    assert not page.exception, [e.value for e in page.exception]


# ---------------------------------------------------------------------------
# It asks who is going — the bug this file was written for
# ---------------------------------------------------------------------------

def test_the_form_asks_how_many_adults_and_children():
    """
    The traveller count multiplies airfare and meals in the feasibility check, so
    it has to be entered rather than inferred.
    """
    page = _fresh()
    numbers = _labels(page.number_input)
    assert "Adults" in numbers, numbers
    assert "Children" in numbers, numbers


def test_adults_starts_at_one_and_cannot_be_zero():
    """
    One traveller is the honest default — it is the smallest real trip, and it
    matches what the extractor falls back to, so the two cannot disagree.
    """
    page = _fresh()
    adults = next(w for w in page.number_input if w.label == "Adults")
    assert adults.value == 1
    assert adults.min == 1


def test_children_starts_at_zero():
    page = _fresh()
    children = next(w for w in page.number_input if w.label == "Children")
    assert children.value == 0
    assert children.min == 0


def test_the_form_still_asks_everything_the_extractor_needs():
    """
    Losing a field here does not break the page — it quietly hands the extractor
    less to work with, which is how the traveller count went missing.
    """
    page = _fresh()
    texts = _labels(page.text_input)
    for wanted in ["Destination", "Travelling from", "Interests"]:
        assert wanted in texts, texts
    assert _labels(page.date_input) == ["Departure", "Return"]
    assert any("budget" in label.lower() for label in _labels(page.number_input))


# ---------------------------------------------------------------------------
# It refuses a request it cannot plan
# ---------------------------------------------------------------------------

def test_an_empty_form_is_refused_and_names_what_is_missing():
    """
    Pressing the button on a blank form must not start a planning run: it costs
    model requests and API quota to discover there was no destination.
    """
    page = _fresh()
    page.button[0].click().run()

    assert not page.exception, [e.value for e in page.exception]
    assert page.error, "a blank form was accepted"
    complaint = page.error[0].value
    for field in ["destination", "origin", "interests"]:
        assert field in complaint, complaint


def test_a_return_date_before_departure_is_refused():
    """
    A negative night count reaches the cost model as a trip of no length, which
    it treats as one night — so the run would succeed and quietly plan the wrong
    trip.
    """
    page = _fresh()
    page.text_input[0].set_value("Istanbul, Turkey")
    page.text_input[1].set_value("Lahore, Pakistan")
    page.text_input[3].set_value("museums")
    page.date_input[0].set_value(datetime.date(2026, 12, 10))
    page.date_input[1].set_value(datetime.date(2026, 12, 3))
    page.button[0].click().run()

    assert not page.exception, [e.value for e in page.exception]
    assert page.error, "a return before departure was accepted"
    assert "return date" in page.error[0].value.lower()


def test_the_same_day_is_refused_too():
    """Zero nights is not a trip this planner can build."""
    page = _fresh()
    page.text_input[0].set_value("Istanbul, Turkey")
    page.text_input[1].set_value("Lahore, Pakistan")
    page.text_input[3].set_value("museums")
    page.date_input[0].set_value(datetime.date(2026, 12, 10))
    page.date_input[1].set_value(datetime.date(2026, 12, 10))
    page.button[0].click().run()

    assert page.error, "a zero-night trip was accepted"


# ---------------------------------------------------------------------------
# The progress hook the page relies on
# ---------------------------------------------------------------------------

def test_the_orchestrator_reports_steps_to_a_registered_hook():
    """
    The page shows real progress by being told, not by scraping stdout. If the
    hook stops firing the page silently goes back to looking frozen.
    """
    from trip_planner.orchestrator import _detail, _step, set_progress_hook

    seen = []
    set_progress_hook(lambda kind, *parts: seen.append((kind,) + parts))
    try:
        _step("STEP 2 of 4", "PREFERENCES EXTRACTOR", "reading the request")
        _detail("route", "LHE to IST")
    finally:
        set_progress_hook(None)

    assert ("step", "STEP 2 of 4", "PREFERENCES EXTRACTOR",
            "reading the request") in seen
    assert ("detail", "route", "LHE to IST") in seen


def test_unregistering_the_hook_stops_the_reports():
    """Otherwise a stale callback from a finished run is called by the next one."""
    from trip_planner.orchestrator import _step, set_progress_hook

    seen = []
    set_progress_hook(lambda *args: seen.append(args))
    set_progress_hook(None)
    _step("STEP 1 of 4", "CONVERSATIONAL AGENT", "asking")
    assert seen == []


def test_a_hook_that_raises_does_not_break_the_run():
    """Reporting progress must never be the reason a plan fails."""
    from trip_planner.orchestrator import _step, set_progress_hook

    def explode(*_args):
        raise RuntimeError("the interface fell over")

    set_progress_hook(explode)
    try:
        _step("STEP 3 of 4", "PLAIN PYTHON", "fetching")   # must not raise
    finally:
        set_progress_hook(None)


# ---------------------------------------------------------------------------
# The badges shown above the itinerary
# ---------------------------------------------------------------------------
#
# These are read out of what the run reported, so a check that stopped running
# stops being claimed. The day count is the one that matters most: a model asked
# for four days sometimes returns one and stops, and a plan covering a quarter of
# the trip must not be presented as finished.
#
# The strings below are the real lines the orchestrator prints, not invented ones.

COMPLETE = "   ✅ Itinerary validation passed: 4/4 days found"
SHORT = ("   ⚠️ Itinerary validation: 1/4 days found\n"
         "      Missing days: {2, 3, 4}")
MEASURED = ("  FLIGHTS: this figure is measured, not estimated — cheapest of "
            "183 fares the flight API really returned for this route.")
UNLISTED = "[Budget] 'Kyoto, Japan' is not in the price table — checking"


def _tones(console, refused=False):
    from trip_planner.frontend.plan_layout import plan_checks
    return dict(plan_checks(console, refused))


def test_a_complete_itinerary_is_marked_complete():
    checks = _tones(COMPLETE)
    assert checks.get("4 of 4 days present") == "good", checks


def test_a_short_itinerary_says_how_short_and_is_not_marked_good():
    """
    The count, not just a warning. "1 of 4 days present" tells the reader the plan
    covers the first day of a four-day trip; a bare "incomplete" does not.
    """
    checks = _tones(SHORT)
    assert checks.get("1 of 4 days present") == "warn", checks


def test_no_day_badge_is_shown_when_no_day_check_ran():
    """Absent is correct here. A green tick nothing verified is the worst option."""
    assert not any("days present" in text for text in _tones("").keys())


def test_a_measured_fare_is_distinguished_from_an_estimated_one():
    """
    The price table is 52% below a real fare on the one route where both are
    known, so which of the two produced a verdict is worth a reader's attention.
    """
    assert _tones(MEASURED).get("flight price measured, not estimated") == "good"


def test_an_unlisted_destination_is_flagged():
    assert _tones(UNLISTED).get("destination not in the price table") == "warn"


def test_a_refusal_is_flagged_as_a_refusal():
    checks = _tones(COMPLETE, refused=True)
    assert checks.get("budget below the floor for this trip") == "bad", checks


def test_a_run_that_reported_nothing_claims_nothing():
    """No console output means no checks ran, so there is nothing to show."""
    from trip_planner.frontend.plan_layout import plan_checks

    assert plan_checks("") == []


# ---------------------------------------------------------------------------
# Showing the plan in sections rather than as one long page
# ---------------------------------------------------------------------------
#
# A finished itinerary is around 24,000 characters across eight sections with a
# block per day. It was being poured into a 55%-wide column as a single markdown
# string: 380 lines of vertical scroll, with no way to reach the third day except
# by dragging past the first two.
#
# BOTH fixtures below are REAL plans, saved verbatim from runs against the
# recorded Istanbul data, and they are here because they DISAGREE. One uses `#`
# eight times, once per section. The other uses `#` once for the document title
# and `##` eight times for the sections. The first version of this parser split
# on `#` regardless, so the second plan came out as one unrecognised blob under a
# single tab called "More" — found by running the page a second time, not by
# reading the code. Testing against text I invented would only have proved the
# parser handles text written to be handled.

import pathlib

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures").glob("*.md"))
PLANS = {path.name: path.read_text(encoding="utf-8") for path in FIXTURES}
FIXTURE = PLANS["itinerary_istanbul.md"]          # the one section-per-`#`


def test_both_recorded_formats_are_present():
    """The point of two fixtures is that they differ. One of each, at least."""
    from trip_planner.frontend.plan_layout import section_level

    assert len(PLANS) >= 2, list(PLANS)
    assert {section_level(text) for text in PLANS.values()} == {1, 2}


@pytest.mark.parametrize("name", sorted(PLANS))
def test_the_section_level_is_the_one_that_repeats(name):
    """
    A heading level used once is a title; used many times it is a divider. That
    is the only rule that tells the two real formats apart.
    """
    from trip_planner.frontend.plan_layout import section_level, split_sections

    found = split_sections(PLANS[name])
    assert len(found) >= 8, (
        f"{name} split into {len(found)} sections at level "
        f"{section_level(PLANS[name])}")


@pytest.mark.parametrize("name", sorted(PLANS))
def test_every_section_reaches_a_tab_and_nothing_is_dropped(name):
    """
    A tab that hid part of the plan would be worse than a long page, so the
    grouping must be lossless.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs, split_sections

    grouped = [pair for _, sections in group_into_tabs(PLANS[name])
               for pair in sections]
    assert len(grouped) == len(split_sections(PLANS[name]))


@pytest.mark.parametrize("name", sorted(PLANS))
def test_the_tabs_come_out_in_reading_order(name):
    """Both formats must present the same six tabs in the same order."""
    from trip_planner.frontend.plan_layout import group_into_tabs

    assert [tab for tab, _ in group_into_tabs(PLANS[name])] == [
        "Overview", "Flights", "Hotels", "Day by day", "Budget", "Tips"]


@pytest.mark.parametrize("name", sorted(PLANS))
def test_the_two_budget_sections_share_one_tab(name):
    """
    Each plan carries both a validation section and a full breakdown. Two tabs
    both called Budget would be a puzzle, not a navigation aid.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs

    budget = dict(group_into_tabs(PLANS[name]))["Budget"]
    assert len(budget) == 2, [t for t, _ in budget]


@pytest.mark.parametrize("name", sorted(PLANS))
def test_a_four_day_trip_yields_exactly_four_days(name):
    """
    Every day ends with its own "DAY 1 SUMMARY:" line, which a looser match read
    as another heading — nine entries for a four-day trip, four of them stubs.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs, split_days

    body = dict(group_into_tabs(PLANS[name]))["Day by day"][0][1]
    labels = [label.split(" ")[1] for label, _ in split_days(body)]
    assert labels == ["1", "2", "3", "4"], labels


@pytest.mark.parametrize("name", sorted(PLANS))
def test_each_day_keeps_its_own_summary(name):
    """The summary belongs to the day above it, not to an entry of its own."""
    from trip_planner.frontend.plan_layout import group_into_tabs, split_days

    body = dict(group_into_tabs(PLANS[name]))["Day by day"][0][1]
    for label, text in split_days(body):
        assert "SUMMARY" in text.upper(), f"{name}: {label} lost its summary"


@pytest.mark.parametrize("name", sorted(PLANS))
def test_no_empty_day_entry_is_produced(name):
    """
    A section can open with a bare rule. An expander labelled "Before day 1" with
    nothing in it is a thing to click for no reason.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs, split_days

    body = dict(group_into_tabs(PLANS[name]))["Day by day"][0][1]
    for label, text in split_days(body):
        assert text.strip(), f"{name}: {label} is empty"


@pytest.mark.parametrize("name", sorted(PLANS))
def test_the_day_label_is_short_enough_to_read(name):
    """
    Streamlit puts this in an expander header. The coordinator writes headings
    like "DAY 4: Tuesday, August 18, 2026 - Wednesday, August 19, 2026 - Modern
    Art, Galata & Departure", which wraps to three lines.
    """
    from trip_planner.frontend.plan_layout import (MAX_DAY_LABEL, group_into_tabs,
                                             split_days)

    body = dict(group_into_tabs(PLANS[name]))["Day by day"][0][1]
    for label, _ in split_days(body):
        assert len(label) <= MAX_DAY_LABEL, f"{len(label)} chars: {label}"


def test_the_preamble_is_kept_and_shown_first():
    """
    The `##` plan opens with its title, the dates and the headline budget before
    any section heading. That is the first thing a reader wants, so it belongs in
    Overview rather than in a tab called "More" — or dropped.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs

    overview = dict(group_into_tabs(
        PLANS["itinerary_istanbul_h2.md"]))["Overview"]
    assert overview[0][0] is None, [t for t, _ in overview]
    assert "Travel Dates" in overview[0][1]


def test_a_specific_heading_beats_a_generic_word_inside_it():
    """
    "FLIGHT OPTIONS ANALYSIS & RECOMMENDATIONS" contains "recommendation", which
    is an Overview word. It is a flight section, and the matching order is what
    makes that true.
    """
    from trip_planner.frontend.plan_layout import tab_for

    assert tab_for("FLIGHT OPTIONS ANALYSIS & RECOMMENDATIONS") == "Flights"
    assert tab_for("HOTEL OPTIONS ANALYSIS & RECOMMENDATIONS") == "Hotels"
    assert tab_for("EXPERT RECOMMENDATIONS & COMBINATIONS") == "Overview"
    assert tab_for("DAILY BUDGET BREAKDOWN") == "Budget"
    assert tab_for("DETAILED DAY-BY-DAY ITINERARY") == "Day by day"


def test_a_budget_table_row_is_not_mistaken_for_a_day():
    """A table row naming a day is not a day heading."""
    from trip_planner.frontend.plan_layout import split_days

    rows = "\n".join([
        "### Day 1: Arrival",
        "Something happened.",
        "| **Day 2 Expenses** | lunch | $30 |",
        "| **Day 3 Expenses** | dinner | $40 |",
    ])
    days = split_days(rows)
    assert len(days) == 1, [label for label, _ in days]
    assert "Day 2 Expenses" in days[0][1]


def test_a_plan_with_no_headings_is_kept_whole():
    """
    The fallback matters more than the tabs. A model that ignores the requested
    headings must not produce a blank page.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs, split_sections

    plain = "Just a paragraph about a trip, with no headings at all."
    assert split_sections(plain) == [(None, plain)]
    assert group_into_tabs(plain), "a headingless plan produced no tabs"


def test_an_unrecognised_heading_still_gets_somewhere():
    """Anything the rules do not know lands under More rather than vanishing."""
    from trip_planner.frontend.plan_layout import group_into_tabs, tab_for

    assert tab_for("WEATHER AND WHAT IT MEANS") == "More"
    tabs = dict(group_into_tabs("# WEATHER\nRain.\n# CLIMATE\nHot.\n"))
    assert "More" in tabs


# ---------------------------------------------------------------------------
# The seven named steps
# ---------------------------------------------------------------------------
#
# The orchestrator reports four phases and, inside the third, one line per
# search. Four rows hid the interesting part — three of the four searches happen
# inside one phase — so the rows are those reports spread out. This checks the
# spreading, because a progress display that drifts from the run is worse than
# none: it says work is finished that has not started.

def test_there_are_seven_named_steps():
    from trip_planner.frontend.plan_layout import STEPS

    assert [name for name, _ in STEPS] == [
        "Conversation", "Preferences", "Flights", "Hotels", "Attractions",
        "Restaurants", "Itinerary"]
    assert all(what.strip() for _, what in STEPS), "a step has no description"


def test_nothing_is_claimed_before_the_run_starts():
    from trip_planner.frontend.plan_layout import IDLE, progress_states, STEPS

    assert progress_states([]) == [IDLE] * len(STEPS)


def test_the_form_counts_as_the_conversation_having_happened():
    """
    The orchestrator never announces phase 1 on the web path — the transcript
    arrives already written. Without this the first row would sit unstarted for
    the whole run, which reads as a step that failed.
    """
    from trip_planner.frontend.plan_layout import DONE, progress_states

    assert progress_states([], conversation_done=True)[0] == DONE


def test_a_phase_marks_everything_before_it_finished():
    """
    The orchestrator only reports a phase once the previous one has returned, so
    reaching phase 3 is evidence that phases 1 and 2 completed.
    """
    from trip_planner.frontend.plan_layout import DONE, NOW, progress_states

    states = progress_states([("phase", 2), ("phase", 3)],
                             conversation_done=True)
    assert states[0] == DONE          # conversation
    assert states[1] == DONE          # preferences
    assert states[2] == NOW           # flights, in progress


def test_each_search_completes_its_own_row_and_starts_the_next():
    from trip_planner.frontend.plan_layout import DONE, NOW, progress_states

    states = progress_states(
        [("phase", 2), ("phase", 3), ("search", "flight"), ("search", "hotel")],
        conversation_done=True)
    assert states[2] == DONE          # flights found
    assert states[3] == DONE          # hotels found
    assert states[4] == NOW           # attractions, in progress


def test_a_finished_run_shows_every_row_done():
    """The full sequence a real run reports, in the order it reports it."""
    from trip_planner.frontend.plan_layout import DONE, STEPS, progress_states

    events = [("phase", 2), ("phase", 3), ("search", "flight"),
              ("search", "hotel"), ("search", "attraction"),
              ("search", "restaurant"), ("phase", 4)]
    states = progress_states(events, conversation_done=True)
    assert states[:6] == [DONE] * 6
    assert len(states) == len(STEPS)


def test_an_unknown_report_changes_nothing():
    """
    A phase number or search label this does not recognise must be ignored, not
    crash the page and not silently mark the wrong row.
    """
    from trip_planner.frontend.plan_layout import progress_states

    baseline = progress_states([("phase", 2)], conversation_done=True)
    noisy = progress_states(
        [("phase", 2), ("phase", 99), ("search", "helicopter")],
        conversation_done=True)
    assert noisy == baseline


def test_the_search_labels_match_what_the_orchestrator_emits():
    """
    These keys are the labels the retrieval step passes to _detail. If one is
    renamed there, its row would silently never light up.
    """
    import inspect

    from trip_planner import orchestrator
    from trip_planner.frontend.plan_layout import SEARCH_ROW

    source = inspect.getsource(orchestrator._retrieve_and_announce
                               if hasattr(orchestrator, "_retrieve_and_announce")
                               else orchestrator.TripPlannerCrew._retrieve_and_announce)
    for label in SEARCH_ROW:
        assert f'"{label}"' in source, (
            f"the page expects a search labelled {label!r}, which the "
            f"orchestrator no longer emits")


# ---------------------------------------------------------------------------
# Sections rendered as cards rather than one column of text
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(PLANS))
def test_a_flight_section_breaks_into_parts(name):
    """
    A flight section is three recommended options plus a table of the rest, each
    under its own sub-heading. As one markdown string the boundaries are buried.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs, split_blocks

    body = dict(group_into_tabs(PLANS[name]))["Flights"][0][1]
    blocks = split_blocks(body)
    assert len(blocks) >= 2, [h for h, _ in blocks]


@pytest.mark.parametrize("name", sorted(PLANS))
def test_splitting_a_section_keeps_all_of_its_text(name):
    """
    Cards are a presentation change. Losing a line to one would be a content
    change, and the reader has no way to know.
    """
    from trip_planner.frontend.plan_layout import group_into_tabs, split_blocks

    for _, sections in group_into_tabs(PLANS[name]):
        for _, body in sections:
            joined = " ".join(text for _, text in split_blocks(body))
            for word in re.findall(r"\$[\d,]+", body):
                assert word in joined, f"{name}: lost {word}"


def test_block_headings_lose_their_markdown_decoration():
    """
    The coordinator writes "### **YOUR TOP 3 RECOMMENDED FLIGHTS:**". The stars
    are decoration for a markdown reader, not part of the name of anything, and
    this heading is rendered as a card title rather than as markdown.
    """
    from trip_planner.frontend.plan_layout import split_blocks

    body = "\n".join(["### **TOP 3 FLIGHTS:**", "One.",
                      "### **THE REST:**", "Two."])
    headings = [h for h, _ in split_blocks(body)]
    assert headings == ["TOP 3 FLIGHTS", "THE REST"], headings


def test_a_section_with_nothing_to_split_comes_back_whole():
    """One card holding an entire section is a border for no reason."""
    from trip_planner.frontend.plan_layout import split_blocks

    blocks = split_blocks("Just a paragraph, no sub-headings at all.")
    assert len(blocks) == 1
    assert blocks[0][0] is None


# ---------------------------------------------------------------------------
# The results page itself
# ---------------------------------------------------------------------------
#
# Driven by putting a finished plan into session state, so these cost no model
# requests and no API quota — the expensive part of a run is producing the plan,
# and one real plan is already saved as the fixture above.

def _finished_page():
    page = AppTest.from_file(APP, default_timeout=120)
    page.session_state["itinerary"] = FIXTURE
    page.session_state["console"] = (
        "   Itinerary validation passed: 4/4 days found\n"
        "  FLIGHTS: this figure is measured, not estimated - cheapest of 183 fares.\n")
    page.session_state["conversation_id"] = "abcd1234-0000-0000"
    page.session_state["facts"] = [("route", "LHE to IST"),
                                   ("flight", "10 options, cheapest $734")]
    page.session_state["answers"] = {
        "destination": "Istanbul, Turkey", "origin": "Lahore, Pakistan",
        "start_date": "2026-08-15", "end_date": "2026-08-19",
        "adults": 1, "children": 0, "budget": 3000.0,
        "travel_style": "a luxury stay", "interests": "museums",
        "special_requirements": "none", "nights": 4}
    page.run()
    return page


def test_the_results_page_renders_without_raising():
    page = _finished_page()
    assert not page.exception, [e.value for e in page.exception]


def test_the_plan_is_shown_as_tabs_not_as_one_long_page():
    """
    The whole point of the change. One markdown string meant 380 lines of scroll
    with no way to reach the third day except by dragging past the first two.
    """
    page = _finished_page()
    assert len(page.tabs) == 6, len(page.tabs)


def test_the_summary_strip_reports_only_what_the_run_established():
    """
    The fare is there because the route was recorded and a real price was read
    out of it. On an unrecorded route the column is absent, not estimated.
    """
    page = _finished_page()
    metrics = {m.label: m.value for m in page.metric}
    assert metrics["Nights"] == "4"
    assert metrics["Travellers"] == "1"
    assert metrics["Budget"] == "$3,000"
    assert metrics["Cheapest fare found"] == "$734"


def test_no_fare_is_shown_when_the_run_found_none():
    """An absent measurement must leave an absent column, not a zero."""
    page = AppTest.from_file(APP, default_timeout=120)
    page.session_state["itinerary"] = FIXTURE
    page.session_state["console"] = ""
    page.session_state["facts"] = []
    page.session_state["answers"] = {"destination": "Kyoto", "nights": 3,
                                     "adults": 2, "children": 0, "budget": 4000.0}
    page.run()
    assert not page.exception, [e.value for e in page.exception]
    assert "Cheapest fare found" not in {m.label for m in page.metric}


def test_a_refusal_is_not_presented_as_an_itinerary():
    """
    When the budget check refuses a trip, what comes back is the refusal and its
    reasoning. Showing that under the heading "Itinerary" would misdescribe it.
    """
    page = AppTest.from_file(APP, default_timeout=120)
    page.session_state["itinerary"] = (
        "======\n  THIS TRIP CANNOT BE PLANNED WITHIN THAT BUDGET\n"
        "  $3,000 cannot cover 6 nights in London.\n")
    page.session_state["console"] = ""
    page.session_state["facts"] = []
    page.session_state["answers"] = {"destination": "London", "nights": 6,
                                     "adults": 2, "children": 0, "budget": 3000.0}
    page.run()
    assert not page.exception, [e.value for e in page.exception]
    assert not page.tabs, "a refusal was split into itinerary tabs"
    badges = " ".join(str(m.value) for m in page.markdown)
    assert "budget below the floor" in badges


def test_a_failed_run_says_so_and_shows_no_tabs():
    page = AppTest.from_file(APP, default_timeout=120)
    page.session_state["failure"] = "RuntimeError: the model refused"
    page.session_state["console"] = "some output before it died"
    page.run()
    assert not page.exception, [e.value for e in page.exception]
    assert page.error, "a failed run reported nothing"
    assert "RuntimeError" in page.error[0].value


def test_the_layout_helpers_stay_out_of_the_streamlit_script():
    """
    They used to live in app.py, and importing them ran the whole page.

    A Streamlit script executes top to bottom on import, so
    `from trip_planner.frontend.app import split_days` drew the sidebar and the form
    outside any script-run context and left Streamlit's global state holding an
    open form. Every page test after that point in the same process died on
    "st.button() can't be used in an st.form()" — six of them, and the page
    itself was fine. The functions were pure; the module was not.

    So: the layout module must not import streamlit, and importing it must not
    leave a page behind.
    """
    import trip_planner.frontend.plan_layout as layout

    source = pathlib.Path(layout.__file__).read_text(encoding="utf-8")
    assert "import streamlit" not in source, (
        "plan_layout imports streamlit; importing it will run a page again")
    assert not hasattr(layout, "st")
