"""
A stated travel style has to change the split, and change the right part of it.

The style was already a parameter and already fed into the tier blend, but one
bias was applied to all four categories equally. Moving everything together
barely moved the RATIOS: on a $2,000 Istanbul trip, "budget" and "luxury"
differed by 1.3 percentage points on accommodation. A traveller who asked for a
luxury stay could not have told they had been heard.

The fix weights the categories separately, because a style request means
different things to different lines. "Luxury" is a statement about the room and
the restaurants; the airfare is whatever the distance costs, and does not become
optional because someone asked for a nicer hotel.

These tests pin the direction and the size of the effect, and pin the thing that
must NOT move: the flight budget, which the distance decides.

No model, no network, no keys.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from trip_planner.core.budget import CATEGORIES, build_allocation

TRIP = dict(total_budget=2000, trip_duration=4, num_travelers=1,
            origin="Lahore", destination="Istanbul")


def allocation_for(style):
    return build_allocation(travel_style=style, **TRIP)


def test_luxury_spends_more_on_the_stay_than_moderate():
    luxury = allocation_for("luxury").amounts["accommodation"]
    moderate = allocation_for("moderate").amounts["accommodation"]
    assert luxury > moderate, (
        "asking for a luxury stay did not increase the accommodation budget")


def test_budget_style_spends_less_on_the_stay_than_moderate():
    budget = allocation_for("budget").amounts["accommodation"]
    moderate = allocation_for("moderate").amounts["accommodation"]
    assert budget < moderate


def test_the_effect_is_large_enough_to_notice():
    """
    The point of the change. A 1.3-point difference is not an answer to
    "I want a luxury stay", so the test asserts a size, not just a direction.
    """
    luxury = allocation_for("luxury").percent("accommodation")
    budget = allocation_for("budget").percent("accommodation")
    assert luxury - budget >= 10.0, (
        f"luxury gives accommodation {luxury}% and budget {budget}% — "
        f"a {luxury - budget:.1f} point spread is too small to be a response")


def test_luxury_roughly_doubles_the_room_budget_against_a_shoestring_one():
    luxury = allocation_for("luxury").amounts["accommodation"]
    budget = allocation_for("budget").amounts["accommodation"]
    assert luxury > budget * 1.8


def test_a_better_room_is_paid_for_out_of_the_rest_of_the_budget():
    """
    The trade-off is real and has to be, because the total is fixed.

    Flights carry a style weight of zero — taste cannot shorten a flight — but the
    shares are normalised to the budget the traveller actually has. So asking for
    a luxury stay on the same $2,000 moves money INTO the room and out of
    everything else, including the airfare. That is the honest arithmetic of a
    fixed budget, not a defect: wanting a better room on the same money means
    flying cheaper.

    What protects it from going too far is the existing bookability warning,
    covered by the next test.
    """
    luxury = allocation_for("luxury").amounts
    budget = allocation_for("budget").amounts
    assert luxury["accommodation"] > budget["accommodation"]
    assert luxury["flights"] < budget["flights"], (
        "the room grew but nothing paid for it")


def test_a_split_that_cannot_buy_the_flight_is_flagged():
    """
    The guard on the trade-off above.

    A luxury request on a budget that barely covers the airfare would otherwise
    reserve a room it cannot afford to reach. The warning is calibrated on
    observed fares from Pakistan and fires below the haul floor.
    """
    tight = build_allocation(total_budget=600, trip_duration=10, num_travelers=1,
                             travel_style="luxury", origin="Lahore",
                             destination="London")
    assert any("Flights" in w for w in tight.warnings), (
        f"a luxury 10-night London trip on $600 drew no flight warning: "
        f"{tight.warnings}")


def test_a_comfortable_budget_draws_no_flight_warning():
    """The warning must not fire on every economical trip, or it means nothing."""
    fine = allocation_for("luxury")
    assert not any("Flights" in w for w in fine.warnings), fine.warnings


@pytest.mark.parametrize("style", ["luxury", "premium", "high-end", "five star"])
def test_the_wordings_a_traveller_actually_uses_are_recognised(style):
    """A traveller types "premium", not the enum value the code expects."""
    assert (allocation_for(style).amounts["accommodation"]
            > allocation_for("moderate").amounts["accommodation"])


@pytest.mark.parametrize("style", ["budget", "backpacker", "cheap", "shoestring"])
def test_the_frugal_wordings_are_recognised_too(style):
    assert (allocation_for(style).amounts["accommodation"]
            < allocation_for("moderate").amounts["accommodation"])


@pytest.mark.parametrize("style", ["luxury", "moderate", "budget", "", "nonsense"])
def test_the_split_still_adds_up(style):
    allocation = allocation_for(style)
    assert sum(allocation.shares.values()) == pytest.approx(1.0)
    assert sum(allocation.amounts.values()) == pytest.approx(TRIP["total_budget"],
                                                             rel=0.01)


@pytest.mark.parametrize("style", ["luxury", "budget"])
def test_no_category_is_starved_or_takes_everything(style):
    """A style request must not push a category to zero or to the whole budget."""
    for category, share in allocation_for(style).shares.items():
        assert 0.02 < share < 0.85, f"{category} took {share:.0%} on {style}"


def test_an_unrecognised_style_behaves_as_moderate():
    assert (allocation_for("nonsense").amounts["accommodation"]
            == pytest.approx(allocation_for("moderate").amounts["accommodation"]))


def test_style_still_loses_to_an_explicit_user_split():
    """
    The traveller's own numbers outrank any inference from their words.

    Someone who says "luxury" and then types 40/30/20/10 has stated a preference
    twice, and the second one is specific.
    """
    explicit = build_allocation(travel_style="luxury",
                                user_input="40/30/20/10", **TRIP)
    assert explicit.source == "user"
    assert explicit.percent("flights") == pytest.approx(40.0, abs=0.5)
    assert explicit.percent("accommodation") == pytest.approx(30.0, abs=0.5)
