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

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest

APP = "trip_planner/ui/app.py"


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
    from trip_planner.ui.app import plan_checks
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
    from trip_planner.ui.app import plan_checks

    assert plan_checks("") == []
