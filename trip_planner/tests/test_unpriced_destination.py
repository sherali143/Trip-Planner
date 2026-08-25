"""
An estimate built on defaults must say so.

The cost model matches a destination against about forty listed cities. Anything
it does not recognise falls to the middle row of every band — medium-haul flight,
moderate prices — and the figure it produced was indistinguishable from one backed
by price data for that place.

That is optimistic for anywhere expensive or distant. "Kyoto" was costed at about
$614 for five nights where the real figure is nearer Toronto's $987, so a $700
budget was reported workable with nothing on screen to suggest the estimate was a
default.

The estimate is still produced — planning should not stop because a city is
unlisted — but the verdict now carries the caveat. These tests pin both halves of
that: the warning appears when it should, and NOTHING ELSE CHANGES, because the
budget gate's twenty recorded scenarios all use listed destinations and their
verdicts must stay exactly as measured.

No model, no network, no keys.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from trip_planner.core.trip_cost import (assess_budget, estimate_trip_cost,
                                         is_known_destination)

# In the price table, and in different bands, so a change to one row cannot make
# these tests pass by accident.
LISTED = ["Toronto", "Istanbul", "Dubai", "New York", "Bangkok", "London"]
# Real places the table has never heard of.
UNLISTED = ["Kyoto", "Nairobi", "Ulaanbaatar", "Canada", "Lagos", "Tbilisi"]


@pytest.mark.parametrize("city", LISTED)
def test_a_listed_destination_is_priced_from_data(city):
    assert is_known_destination(city)
    assert estimate_trip_cost(city, 5, 1).priced_from_data


@pytest.mark.parametrize("city", UNLISTED)
def test_an_unlisted_destination_is_flagged_as_not_priced_from_data(city):
    assert not is_known_destination(city)
    assert not estimate_trip_cost(city, 5, 1).priced_from_data


@pytest.mark.parametrize("city", UNLISTED)
def test_an_unlisted_destination_still_gets_an_estimate(city):
    """Planning must not stop because a city is unlisted."""
    estimate = estimate_trip_cost(city, 5, 1)
    assert estimate.minimum > 0
    assert estimate.comfortable > estimate.minimum


@pytest.mark.parametrize("city", UNLISTED)
def test_the_verdict_says_the_figure_rests_on_defaults(city):
    verdict = assess_budget(total_budget=2000, destination=city, nights=5,
                            travelers=1, origin="Lahore")
    assert "not in the price table" in verdict.message, (
        "an estimate built on defaults reads exactly like one built on data")
    assert any("indicative" in s for s in verdict.suggestions)


@pytest.mark.parametrize("city", LISTED)
def test_a_listed_destination_gets_no_such_warning(city):
    """The caveat must not appear where the estimate is actually backed by data."""
    verdict = assess_budget(total_budget=2000, destination=city, nights=5,
                            travelers=1, origin="Lahore")
    assert "not in the price table" not in verdict.message


def test_the_warning_appears_on_a_refusal_too():
    """
    A refusal is where the caveat matters most.

    Being told a trip is impossible on the strength of a default is worse than
    being told it is affordable on one, because it stops the traveller entirely.
    """
    verdict = assess_budget(total_budget=100, destination="Ulaanbaatar", nights=7,
                            travelers=2, origin="Lahore")
    assert not verdict.feasible
    assert "not in the price table" in verdict.message


# Budget, destination, and whether that trip is possible. Each budget is chosen
# to sit clearly on one side of that destination's floor, so the test asserts the
# decision rather than the precise threshold.
@pytest.mark.parametrize("budget,city,expected_feasible", [
    (2500, "Toronto", True),      # floor about $1,200 for 7 nights
    (1200, "Istanbul", True),     # cheap tier, medium haul
    (300, "New York", False),     # floor $1,131 — the designed-impossible case
    (200, "Toronto", False),
])
def test_no_listed_verdict_changed(budget, city, expected_feasible):
    """
    The decisions the budget gate recorded must be untouched.

    Twenty scenarios and a Cohen's kappa of 0.643 are published against this
    model. Adding a caveat to unlisted destinations must not move a single
    verdict for a listed one, or the recorded evaluation stops describing the code.
    """
    verdict = assess_budget(total_budget=budget, destination=city, nights=7,
                            travelers=1, origin="Lahore")
    assert verdict.feasible is expected_feasible


def test_every_gate_scenario_is_still_priced_from_data():
    """
    The recorded evaluation reports "0 fall back to mid-tier defaults".

    If a scenario's destination ever stopped being listed, its verdict would
    silently start resting on defaults while the results file still claimed
    otherwise. This is what notices.
    """
    from trip_planner.evaluation.scenarios import SCENARIOS

    unlisted = []
    for scenario in SCENARIOS:
        destination = (scenario.get("destination")
                       or scenario.get("input", ""))
        if not is_known_destination(destination):
            unlisted.append(f"{scenario['id']}: {destination[:40]}")
    assert not unlisted, (
        "these evaluation scenarios would now be costed from defaults: "
        + ", ".join(unlisted))
