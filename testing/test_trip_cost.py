"""
Tests for trip cost estimation and budget feasibility.

The behaviour that matters: costs must respond to the destination (the old
hardcoded rule did not), the floor must be a real floor, and everything above
the floor must be allowed through — a tight budget is a legitimate choice, only
an impossible one is not.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.core.trip_cost import (
    COMFORTABLE,
    GENEROUS,
    IMPOSSIBLE,
    VERY_TIGHT,
    WORKABLE,
    assess_budget,
    classify_haul,
    classify_price_tier,
    estimate_trip_cost,
    suggest_budget,
)


class TestCostStructure:
    def test_tiers_are_ordered(self):
        e = estimate_trip_cost("Dubai", 5, 2)
        assert e.minimum < e.comfortable < e.luxury

    def test_breakdown_sums_to_each_total(self):
        e = estimate_trip_cost("Istanbul", 7, 2)
        for level, total in (("minimum", e.minimum), ("comfortable", e.comfortable),
                             ("luxury", e.luxury)):
            parts = sum(cat[level] for cat in e.breakdown.values())
            assert abs(parts - total) <= 2, level

    def test_flights_scale_per_person(self):
        solo = estimate_trip_cost("Dubai", 5, 1)
        trio = estimate_trip_cost("Dubai", 5, 3)
        assert trio.breakdown["flights"]["minimum"] == pytest.approx(
            solo.breakdown["flights"]["minimum"] * 3)

    def test_accommodation_is_shared_not_per_person(self):
        # Two people share a room, so cost must NOT double.
        solo = estimate_trip_cost("Dubai", 5, 1)
        pair = estimate_trip_cost("Dubai", 5, 2)
        assert pair.breakdown["accommodation"]["minimum"] == \
            solo.breakdown["accommodation"]["minimum"]

    def test_three_travellers_need_two_rooms(self):
        pair = estimate_trip_cost("Dubai", 5, 2)
        trio = estimate_trip_cost("Dubai", 5, 3)
        assert trio.breakdown["accommodation"]["minimum"] == \
            pair.breakdown["accommodation"]["minimum"] * 2

    def test_accommodation_scales_with_nights(self):
        short = estimate_trip_cost("Dubai", 2, 1)
        long = estimate_trip_cost("Dubai", 10, 1)
        assert long.breakdown["accommodation"]["minimum"] > \
            short.breakdown["accommodation"]["minimum"] * 4

    def test_flights_do_not_scale_with_nights(self):
        short = estimate_trip_cost("Dubai", 2, 1)
        long = estimate_trip_cost("Dubai", 20, 1)
        assert short.breakdown["flights"]["minimum"] == long.breakdown["flights"]["minimum"]


class TestDestinationSensitivity:
    """The whole point: the old rule used one number for every destination."""

    def test_expensive_city_costs_more_than_cheap_city(self):
        bangkok = estimate_trip_cost("Bangkok", 5, 1)
        london = estimate_trip_cost("London", 5, 1)
        assert london.minimum > bangkok.minimum * 1.5

    def test_same_budget_can_be_workable_and_impossible(self):
        # 700 dollars: fine for Bangkok, not possible for London.
        assert assess_budget(700, "Bangkok", 5, 1).feasible
        assert not assess_budget(700, "London", 5, 1).feasible

    @pytest.mark.parametrize("city,haul", [
        ("Dubai", "short"), ("Tokyo", "long"), ("London", "long"),
        ("Istanbul", "medium"), ("Nowhereville", "medium"),
    ])
    def test_haul_classification(self, city, haul):
        assert classify_haul(city) == haul

    @pytest.mark.parametrize("city,tier", [
        ("Bangkok", "cheap"), ("London", "expensive"), ("Dubai", "moderate"),
        ("Nowhereville", "moderate"),
    ])
    def test_price_tier_classification(self, city, tier):
        assert classify_price_tier(city) == tier

    def test_unknown_destination_uses_middle_defaults(self):
        # An unrecognised city must not crash or be treated as free.
        e = estimate_trip_cost("Xanadu", 5, 1)
        assert e.minimum > 0
        assert e.price_tier == "moderate"


class TestVerdicts:
    def test_below_minimum_is_refused(self):
        v = assess_budget(300, "Dubai", 5, 3)
        assert v.verdict == IMPOSSIBLE
        assert not v.feasible
        assert v.suggestions, "a refusal must say what would make it work"

    def test_just_above_minimum_is_allowed_with_a_warning(self):
        e = estimate_trip_cost("Dubai", 5, 3)
        v = assess_budget(e.minimum + 10, "Dubai", 5, 3)
        assert v.feasible
        assert v.verdict == VERY_TIGHT

    def test_verdicts_climb_with_budget(self):
        seen = [assess_budget(b, "Dubai", 5, 3).verdict
                for b in (300, 1250, 2000, 5000, 12000)]
        assert seen == [IMPOSSIBLE, VERY_TIGHT, WORKABLE, COMFORTABLE, GENEROUS]

    def test_refusal_message_names_the_shortfall(self):
        v = assess_budget(300, "Dubai", 5, 3)
        assert "300" in v.message and "short" in v.message.lower()

    def test_refusal_offers_a_shorter_trip_when_one_would_fit(self):
        v = assess_budget(700, "Bangkok", 14, 1)
        if not v.feasible:
            assert any("shorten" in s.lower() for s in v.suggestions)

    def test_refusal_explains_when_even_one_night_is_impossible(self):
        # Flight alone exceeds the budget — shortening cannot help.
        v = assess_budget(200, "Tokyo", 7, 4)
        assert not v.feasible
        assert any("one night" in s.lower() for s in v.suggestions)

    def test_per_person_hint_only_for_groups(self):
        group = assess_budget(300, "Dubai", 5, 3)
        assert any("per person" in s for s in group.suggestions)


class TestEdgeCases:
    def test_zero_budget_is_refused_not_crashed(self):
        v = assess_budget(0, "Dubai", 5, 1)
        assert not v.feasible

    def test_zero_nights_is_treated_as_one(self):
        e = estimate_trip_cost("Dubai", 0, 1)
        assert e.nights == 1
        assert e.minimum > 0

    def test_zero_travellers_is_treated_as_one(self):
        e = estimate_trip_cost("Dubai", 5, 0)
        assert e.travelers == 1

    def test_empty_destination_does_not_crash(self):
        e = estimate_trip_cost("", 5, 1)
        assert e.minimum > 0

    def test_negative_values_do_not_produce_negative_costs(self):
        e = estimate_trip_cost("Dubai", -5, -2)
        assert e.minimum > 0
        assert e.nights >= 1 and e.travelers >= 1

    def test_very_long_trip_is_dominated_by_nightly_costs(self):
        e = estimate_trip_cost("Bangkok", 60, 1)
        assert e.breakdown["accommodation"]["minimum"] > e.breakdown["flights"]["minimum"]

    def test_large_group_is_handled(self):
        e = estimate_trip_cost("Dubai", 5, 10)
        assert e.breakdown["accommodation"]["minimum"] == \
            estimate_trip_cost("Dubai", 5, 2).breakdown["accommodation"]["minimum"] * 5


class TestExplanations:
    def test_explain_covers_every_category_and_tier(self):
        text = estimate_trip_cost("Dubai", 5, 3).explain()
        for word in ("Flights", "Accommodation", "Meals", "Activities",
                     "Minimum", "Comfortable", "Luxury", "TOTAL"):
            assert word in text

    def test_explain_states_the_floor_in_words(self):
        text = estimate_trip_cost("Dubai", 5, 3).explain()
        assert "not bookable" in text

    def test_suggest_budget_gives_three_numbers(self):
        text = suggest_budget("Dubai", 5, 3)
        assert "Minimum" in text and "Comfortable" in text and "Luxury" in text
