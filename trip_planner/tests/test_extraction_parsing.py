"""
The extractor's output must stay readable to everything downstream.

This exists because of a silent, intermittent bug. CrewAI stores a parsed dict on
its result object when it manages to parse the model's answer, and str() on that
object then returns a PYTHON REPR — {'total_budget': 800.0}, single quotes —
rather than JSON. Every regex in the orchestrator looks for "total_budget" with
double quotes, so when the framework succeeded at parsing, the orchestrator
failed at reading, and:

  * _parse_prefs returned an empty dict,
  * _assess_budget therefore saw no destination and skipped the budget
    feasibility check entirely — the supervisor's requested feature, silently off,
  * _search_parameters fell back to empty origin and destination.

On the run that exposed it, the extractor had flagged BUDGET_TOO_LOW and asked for
a $1,000 minimum against a stated $800 budget, and the trip was planned anyway.

The bug only appeared when parsing SUCCEEDED, which is why it survived so long.
None of these tests calls a model.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from trip_planner.orchestrator import TripPlannerCrew

PREFS = {
    "origin": "Lahore",
    "destination": "Istanbul",
    "departure_date": "2026-08-15",
    "return_date": "2026-08-19",
    "trip_duration": 4,
    "total_budget": 800.0,
    "num_adults": 1,
    "num_children": 0,
    "budget_breakdown": {"flights": 280.0, "accommodation": 280.0,
                         "activities": 160.0, "meals": 80.0},
    "interests": ["history", "food", "shopping"],
    "travel_style": "moderate",
}


class FakeCrewOutput:
    """Stands in for a CrewAI result, which carries both a dict and raw text."""

    def __init__(self, json_dict=None, raw=None):
        self.json_dict = json_dict
        self.raw = raw

    def __str__(self):
        # Faithful to the framework: the dict wins, and it stringifies as a
        # Python repr. This is the behaviour that caused the bug.
        if self.json_dict:
            return str(self.json_dict)
        return self.raw or ""


def test_a_parsed_dict_result_becomes_valid_json_not_a_python_repr():
    text = TripPlannerCrew._as_json_text(FakeCrewOutput(json_dict=PREFS))
    assert "'total_budget'" not in text, (
        "the result is a Python repr; every downstream regex expects JSON")
    assert '"total_budget"' in text
    json.loads(text)  # must be parseable, not merely double-quoted


def test_raw_text_is_used_when_the_framework_could_not_parse():
    raw = '{"destination": "Istanbul", "total_budget": 800}'
    assert TripPlannerCrew._as_json_text(FakeCrewOutput(raw=raw)) == raw


def test_a_dict_result_is_preferred_over_raw_text():
    """The dict is the framework's own parse, so it is the more reliable source."""
    out = FakeCrewOutput(json_dict=PREFS, raw="some prose that is not json")
    assert json.loads(TripPlannerCrew._as_json_text(out))["destination"] == "Istanbul"


def test_an_empty_result_does_not_crash():
    assert TripPlannerCrew._as_json_text(FakeCrewOutput()) == ""


@pytest.mark.parametrize("field,expected", [
    ("destination", "Istanbul"),
    ("origin", "Lahore"),
    ("total_budget", 800.0),
    ("trip_duration", 4),
])
def test_prefs_survive_the_round_trip_a_parsed_result_used_to_break(field, expected):
    """
    The whole chain: framework result -> text -> _parse_prefs.

    This is the assertion that would have failed before the fix, for every field.
    """
    text = TripPlannerCrew._as_json_text(FakeCrewOutput(json_dict=PREFS))
    prefs = TripPlannerCrew._parse_prefs(text)
    assert prefs, "_parse_prefs found nothing at all"
    assert prefs.get(field) == expected


def test_the_budget_check_receives_a_destination_so_it_cannot_skip_itself():
    """
    _assess_budget skips its feasibility check when no destination is parsed.

    That is a reasonable fallback and a dangerous one: it turned the budget gate
    off without saying so. This asserts the input it needs actually arrives.
    """
    text = TripPlannerCrew._as_json_text(FakeCrewOutput(json_dict=PREFS))
    assert TripPlannerCrew._parse_prefs(text).get("destination")


def test_search_parameters_survive_a_parsed_result():
    """Retrieval needs origin, destination and dates, or it skips every fetch."""
    text = TripPlannerCrew._as_json_text(FakeCrewOutput(json_dict=PREFS))
    params = TripPlannerCrew._search_parameters(text)
    assert params["origin"] == "Lahore"
    assert params["destination"] == "Istanbul"
    assert params["departure_date"] == "2026-08-15"
    # The extractor's own split must be honoured, not replaced by the default.
    assert round(params["flight_budget"]) == 280


def test_an_approved_allocation_overrides_the_extracted_split():
    """The command line's interactive budget choice has to reach the searches."""
    text = TripPlannerCrew._as_json_text(FakeCrewOutput(json_dict=PREFS))
    params = TripPlannerCrew._search_parameters(
        text, allocation={"flights": 200.0, "accommodation": 400.0,
                          "activities": 100.0, "meals": 100.0})
    assert round(params["flight_budget"]) == 200, (
        "an allocation the traveller approved was ignored")
