"""
Tests for scenario-aware budget allocation.

Focus is on the two things that make this a system rather than a prompt:
allocations always sum to 100% no matter which adjustment rules fire, and user
input is parsed forgivingly but never silently misread.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.core.budget import (
    BASE_ALLOCATION,
    CATEGORIES,
    LEGACY_ALLOCATION,
    build_allocation,
    check_realism,
    parse_user_allocation,
    suggest_allocation,
)


def _sums_to_one(allocation):
    return abs(sum(allocation.shares.values()) - 1.0) < 1e-6


class TestSuggestion:
    def test_shares_always_sum_to_100_percent(self):
        # Every combination of rules must still normalise.
        for duration in (1, 3, 5, 10, 21):
            for travelers in (1, 2, 5):
                for style in ("budget", "moderate", "luxury"):
                    for dest in ("Dubai", "Istanbul", "Tokyo", "Nowhereville"):
                        a = suggest_allocation(2000, duration, travelers, style,
                                               "Lahore", dest)
                        assert _sums_to_one(a), (duration, travelers, style, dest)

    def test_amounts_match_total_budget(self):
        a = suggest_allocation(3000, 7, 2, "moderate", "Lahore", "Istanbul")
        assert abs(sum(a.amounts.values()) - 3000) < 1.0

    def test_long_haul_gets_bigger_flight_share_than_short_haul(self):
        long_haul = suggest_allocation(3000, 5, 1, "moderate", "Lahore", "Tokyo")
        short_haul = suggest_allocation(3000, 5, 1, "moderate", "Lahore", "Dubai")
        assert long_haul.shares["flights"] > short_haul.shares["flights"]

    def test_longer_trip_reduces_flight_share(self):
        # The flight is a one-off cost; more nights dilute it.
        short = suggest_allocation(3000, 3, 1, "moderate", "Lahore", "Istanbul")
        long = suggest_allocation(3000, 14, 1, "moderate", "Lahore", "Istanbul")
        assert long.shares["flights"] < short.shares["flights"]
        assert long.shares["accommodation"] > short.shares["accommodation"]

    def test_luxury_raises_accommodation_share(self):
        lux = suggest_allocation(5000, 5, 2, "luxury", "Lahore", "Dubai")
        budget = suggest_allocation(5000, 5, 2, "budget", "Lahore", "Dubai")
        assert lux.shares["accommodation"] > budget.shares["accommodation"]

    def test_more_travellers_raises_flight_share(self):
        # Airfare multiplies per person; a room is shared.
        solo = suggest_allocation(4000, 5, 1, "moderate", "Lahore", "Istanbul")
        pair = suggest_allocation(4000, 5, 3, "moderate", "Lahore", "Istanbul")
        assert pair.shares["flights"] > solo.shares["flights"]

    def test_reasons_are_always_given(self):
        a = suggest_allocation(1000, 5, 1, "moderate", "Lahore", "Istanbul")
        assert a.reasons, "a suggestion with no explanation is not usable"

    def test_explain_mentions_every_category(self):
        text = suggest_allocation(2000, 5, 1, "moderate", "Lahore", "Istanbul").explain()
        for category in CATEGORIES:
            assert category.title() in text


class TestUserInput:
    def test_blank_means_no_opinion(self):
        shares, _ = parse_user_allocation("", 1000)
        assert shares is None

    @pytest.mark.parametrize("word", ["default", "d", "yes", "ok", "keep"])
    def test_accept_words_mean_no_opinion(self, word):
        shares, _ = parse_user_allocation(word, 1000)
        assert shares is None

    def test_four_bare_numbers(self):
        shares, _ = parse_user_allocation("40/30/20/10", 1000)
        assert shares["flights"] == pytest.approx(0.40)
        assert shares["meals"] == pytest.approx(0.10)

    def test_named_categories_with_aliases(self):
        shares, _ = parse_user_allocation("hotel 50, flights 30, food 10, tours 10", 1000)
        assert shares["accommodation"] == pytest.approx(0.50)
        assert shares["meals"] == pytest.approx(0.10)
        assert shares["activities"] == pytest.approx(0.10)

    def test_partial_input_fills_the_rest(self):
        # User cares only about hotels; the remainder keeps suggested proportions.
        shares, messages = parse_user_allocation("hotel 60", 1000)
        assert shares["accommodation"] == pytest.approx(0.60)
        assert abs(sum(shares.values()) - 1.0) < 1e-6
        assert any("remaining" in m for m in messages)

    def test_absolute_amounts(self):
        shares, messages = parse_user_allocation(
            "flights 500, hotel 300, food 100, activities 100", 1000)
        assert shares["flights"] == pytest.approx(0.50)
        assert any("absolute" in m for m in messages)

    def test_percentages_not_summing_to_100_are_scaled_and_reported(self):
        shares, messages = parse_user_allocation("flights 50, hotel 50, food 50, tours 50", 1000)
        assert abs(sum(shares.values()) - 1.0) < 1e-6
        assert any("scaled" in m for m in messages)

    def test_unreadable_input_explains_itself(self):
        shares, messages = parse_user_allocation("i want it cheap please", 1000)
        assert shares is None
        assert messages and "Could not read" in messages[0]

    def test_negative_values_do_not_produce_negative_shares(self):
        shares, _ = parse_user_allocation("flights -50, hotel 80", 1000)
        assert shares is None or all(v >= 0 for v in shares.values())

    def test_all_zero_falls_back_rather_than_dividing_by_zero(self):
        shares, messages = parse_user_allocation("flights 0, hotel 0, food 0, tours 0", 1000)
        assert shares == BASE_ALLOCATION
        assert any("zero" in m for m in messages)


class TestRealismChecks:
    def test_warns_when_flight_budget_cannot_buy_a_long_haul_seat(self):
        a = build_allocation(600, 7, 2, "moderate", "Lahore", "Tokyo",
                             user_input="flights 10, hotel 60, food 20, tours 10")
        assert any("Flights" in w for w in a.warnings)

    def test_warns_on_impossible_nightly_rate(self):
        a = build_allocation(500, 10, 1, "moderate", "Lahore", "Istanbul",
                             user_input="flights 90, hotel 4, food 3, tours 3")
        assert any("Accommodation" in w for w in a.warnings)

    def test_sensible_allocation_produces_no_warnings(self):
        a = suggest_allocation(4000, 5, 1, "moderate", "Lahore", "Istanbul")
        assert a.warnings == []

    def test_user_choice_is_honoured_even_when_warned(self):
        # Warnings inform; they must never silently override the user.
        a = build_allocation(600, 7, 2, "moderate", "Lahore", "Tokyo",
                             user_input="flights 10, hotel 60, food 20, tours 10")
        assert a.source == "user"
        assert a.shares["flights"] == pytest.approx(0.10)
        assert a.warnings


class TestIntegration:
    def test_build_allocation_without_user_input_returns_suggestion(self):
        a = build_allocation(2000, 5, 1, "moderate", "Lahore", "Istanbul")
        assert a.source == "suggested"

    def test_as_dict_matches_pipeline_shape(self):
        # The rest of the pipeline reads budget_breakdown with these keys.
        a = suggest_allocation(2000, 5, 1, "moderate", "Lahore", "Istanbul")
        breakdown = a.as_dict()
        assert set(breakdown) == set(CATEGORIES)
        assert all(isinstance(v, float) for v in breakdown.values())

    def test_legacy_split_is_unchanged(self):
        # comparison/ depends on this staying exactly as it was, so previously
        # recorded API responses remain valid and the arms stay comparable.
        assert LEGACY_ALLOCATION == {
            "flights": 0.35, "accommodation": 0.35, "activities": 0.20, "meals": 0.10,
        }

    def test_zero_budget_does_not_crash(self):
        a = suggest_allocation(0, 5, 1, "moderate", "Lahore", "Istanbul")
        assert _sums_to_one(a)
        assert all(v == 0 for v in a.amounts.values())
