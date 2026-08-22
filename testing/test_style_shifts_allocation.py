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

from trip_planner.core.budget import build_allocation

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


# ------------------------------------------------------------------ phrasing
# What a traveller actually types, rather than the three words a dropdown offers.
class TestPhrasingIsUnderstood:
    """
    The style is read from the traveller's own words.

    Two implementations of this used to exist — one on the cost-derived path and
    one on the fallback — with different word lists, so "five star" was understood
    for a listed destination and ignored for an unlisted one. Both now come
    through parse_style.
    """

    def test_a_luxury_stay_is_a_request_about_the_room(self):
        from trip_planner.core.budget import parse_style
        intent = parse_style("I want a luxury stay")
        assert intent.level > 0
        assert intent.weight("accommodation") == 1.0
        assert intent.weight("flights") == 0.0, "taste cannot shorten a flight"

    def test_a_luxury_trip_is_a_request_about_all_of_it(self):
        from trip_planner.core.budget import parse_style
        intent = parse_style("luxury full trip")
        assert intent.weight("accommodation") == 1.0
        assert intent.weight("meals") > 0.5, "a luxury trip includes the food"

    def test_a_luxury_stay_buys_a_better_room_than_a_luxury_trip(self):
        """
        The same budget, spread differently.

        "Luxury stay" concentrates on the room. "Luxury trip" spends some of that
        on food and activities instead, so the room ends up smaller.
        """
        stay = allocation_for("I want a luxury stay")
        trip = allocation_for("luxury full trip")
        assert stay.amounts["accommodation"] > trip.amounts["accommodation"]
        assert trip.amounts["meals"] > stay.amounts["meals"]

    def test_compromising_moves_money_to_food_and_doing_things(self):
        """
        The split divides a fixed total, so "spend less" cannot lower it.

        What it can do is move money out of the room and the airfare and into the
        part of the trip the traveller was willing to keep. Pushing every category
        down at once — which an earlier version did — changed almost nothing.
        """
        lean = allocation_for("I can fully compromise")
        neutral = allocation_for("moderate")
        assert lean.amounts["accommodation"] < neutral.amounts["accommodation"]
        assert lean.amounts["meals"] > neutral.amounts["meals"]
        assert lean.amounts["activities"] > neutral.amounts["activities"]

    def test_moderate_is_neutral(self):
        """
        "Moderate" is this system's default answer to the style question.

        Reading it as a mild upgrade — which one draft did — silently biased every
        default trip toward a better room.
        """
        from trip_planner.core.budget import parse_style
        assert parse_style("moderate").level == 0.0
        assert parse_style("standard").level == 0.0
        stated = allocation_for("moderate").amounts
        unstated = allocation_for("").amounts
        assert stated == unstated

    def test_strength_is_graded_not_binary(self):
        from trip_planner.core.budget import parse_style
        assert (parse_style("money no object").level
                > parse_style("luxury").level
                > parse_style("comfortable").level
                > parse_style("moderate").level
                > parse_style("budget").level
                > parse_style("shoestring").level)

    def test_the_reason_names_what_was_understood(self):
        """A traveller should be able to see their words were read correctly."""
        allocation = allocation_for("I want a luxury stay")
        assert any("stay" in r for r in allocation.reasons), allocation.reasons

    def test_an_unlisted_destination_understands_the_same_words(self):
        """
        The regression the single parser exists to prevent.

        The fallback path used to hold its own shorter word list, so this worked
        for Istanbul and did nothing for Kyoto.
        """
        lux = build_allocation(total_budget=2000, trip_duration=4, num_travelers=1,
                               travel_style="five star hotel", origin="Lahore",
                               destination="Kyoto")
        lean = build_allocation(total_budget=2000, trip_duration=4, num_travelers=1,
                                travel_style="shoestring", origin="Lahore",
                                destination="Kyoto")
        assert lux.amounts["accommodation"] > lean.amounts["accommodation"]


def test_no_category_is_handed_more_than_it_could_cost():
    """
    A fourteen-night Bangkok trip needs about $350 of airfare.

    Shares are proportions, so money pushed out of one category lands wherever the
    arithmetic puts it. On $6,000 with a strong economise request, flights were
    handed 41% — $2,442 reserved for a $350 flight, which then makes the search
    look for a fare ten times dearer than the trip needs.
    """
    generous = build_allocation(total_budget=6000, trip_duration=14, num_travelers=1,
                                travel_style="budget", origin="Lahore",
                                destination="Bangkok")
    assert generous.percent("flights") < 35.0, (
        f"flights took {generous.percent('flights')}% "
        f"(${generous.amounts['flights']:,.0f}) of a $6,000 budget")
