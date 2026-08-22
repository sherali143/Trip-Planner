"""
The budget check can use real fares instead of a constant, and says which it used.

The price table carries a measured error where it can be checked at all: it says a
medium-haul flight starts at $350, and the cheapest fare the API actually returned
for Lahore-Istanbul was $734. That is not a small difference — on a $800 four-night
trip the table says "workable" and the real fare says impossible.

So `assess_budget` now takes an optional probe that reads fares out of the recorded
API responses. It costs nothing, needs no key, and returns a price a real API
really quoted. Where there is no recording it returns None and the table stands.

The default is unchanged and must stay unchanged: the twenty-scenario budget-gate
evaluation and its Cohen's kappa of 0.643 are published against the table, so
switching the probe on by default would mean those figures no longer describe the
code. The live path passes a probe; the experiment does not. Two tests below hold
that line.

No model, no network, no keys — the recordings are on disk.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from trip_planner.core.real_prices import PriceProbe, recorded_flight_price
from trip_planner.core.trip_cost import assess_budget, estimate_trip_cost

# The one route this project has real recorded fares for.
RECORDED_ROUTE = ("Lahore", "Istanbul")
# The cheapest fare in those recordings. Also reported as cheapest_real_fare by
# the budget-gate experiment, so the two extractions must agree.
RECORDED_CHEAPEST = 734.0


class TestReadingRealFares:
    def test_the_recorded_route_yields_a_real_fare(self):
        price = recorded_flight_price(*RECORDED_ROUTE)
        assert price is not None
        assert price.amount == pytest.approx(RECORDED_CHEAPEST, abs=1.0)
        assert price.source == "recorded"

    def test_it_agrees_with_the_experiment_about_the_same_recordings(self):
        """
        Two extractions of the same files must not disagree.

        The budget-gate experiment reports this figure as cheapest_real_fare, and
        it is quoted in the dissertation. A second reader of the same cache giving
        a different answer would make one of them wrong.
        """
        from evaluation import measured

        try:
            published = measured.gate_external_validity()["cheapest_real_fare"]
        except Exception:                          # noqa: BLE001
            pytest.skip("no external-validity block recorded")
        price = recorded_flight_price(*RECORDED_ROUTE)
        assert price is not None
        assert price.amount == pytest.approx(published, abs=1.0)

    def test_a_city_name_is_resolved_to_the_code_the_recording_used(self):
        """
        The app passes "Istanbul", the recording is keyed "IST".

        Without resolution the probe never fired on the live path, because a city
        name holds no airport code and the route could not be identified.
        """
        by_name = recorded_flight_price("Lahore", "Istanbul")
        by_code = recorded_flight_price("LHE", "IST")
        assert by_name is not None and by_code is not None
        assert by_name.amount == by_code.amount

    @pytest.mark.parametrize("origin,destination", [
        ("Lahore", "Toronto"), ("Islamabad", "Doha"), ("Dubai", "London"),
    ])
    def test_an_unrecorded_route_returns_nothing_rather_than_a_guess(self, origin,
                                                                    destination):
        """
        Using another route's fare would be worse than admitting there is no data.

        This is not hypothetical. A draft matched airport codes anywhere in the
        response body, and a 2.3 MB reply listing connections mentions dozens of
        airports — so Islamabad-Doha was reported as $734, which is the
        Lahore-Istanbul fare.
        """
        assert recorded_flight_price(origin, destination) is None


class TestTheEstimateUsesIt:
    def test_a_real_fare_replaces_the_constant(self):
        table = estimate_trip_cost("Istanbul", 4, 1, "Lahore")
        real = estimate_trip_cost("Istanbul", 4, 1, "Lahore", price_probe=PriceProbe())
        assert table.breakdown["flights"]["minimum"] == 350, "the table changed"
        assert real.breakdown["flights"]["minimum"] == pytest.approx(
            RECORDED_CHEAPEST, abs=1.0)
        assert real.minimum > table.minimum

    def test_the_estimate_records_which_lines_are_measured(self):
        real = estimate_trip_cost("Istanbul", 4, 1, "Lahore", price_probe=PriceProbe())
        assert "flights" in real.measured_lines
        assert "recorded" in real.measured_lines["flights"]

    def test_lines_with_no_recording_are_not_claimed_as_measured(self):
        real = estimate_trip_cost("Istanbul", 4, 1, "Lahore", price_probe=PriceProbe())
        assert "accommodation" not in real.measured_lines

    def test_an_unrecorded_route_falls_back_to_the_table_silently_identically(self):
        with_probe = estimate_trip_cost("Toronto", 5, 1, "Lahore",
                                        price_probe=PriceProbe())
        without = estimate_trip_cost("Toronto", 5, 1, "Lahore")
        assert with_probe.minimum == without.minimum
        assert not with_probe.measured_lines


class TestTheVerdictChangesAndSaysWhy:
    def test_the_real_fare_can_flip_a_verdict(self):
        """
        The whole point. $800 for four nights in Istanbul is "workable" against
        the table and impossible against the fare the API actually quoted.
        """
        table = assess_budget(800, "Istanbul", 4, 1, "Lahore")
        real = assess_budget(800, "Istanbul", 4, 1, "Lahore",
                             price_probe=PriceProbe())
        assert table.feasible is True
        assert real.feasible is False

    def test_the_verdict_says_the_figure_was_measured(self):
        real = assess_budget(800, "Istanbul", 4, 1, "Lahore",
                             price_probe=PriceProbe())
        assert "measured, not estimated" in real.message
        assert "FLIGHTS" in real.message

    def test_a_refusal_still_explains_what_would_work(self):
        real = assess_budget(800, "Istanbul", 4, 1, "Lahore",
                             price_probe=PriceProbe())
        assert real.suggestions
        assert any("Raise the budget" in s for s in real.suggestions)


class TestTheDefaultIsUntouched:
    """
    The line that must not move.

    Cohen's kappa 0.643 over twenty scenarios is published against the table. If
    the probe ever becomes the default, every verdict in that evaluation is
    recomputed and the figure in the dissertation stops describing the code.
    """

    @pytest.mark.parametrize("budget,destination,nights,expected", [
        (800, "Istanbul", 4, True),
        (300, "New York", 7, False),
        (2500, "Toronto", 5, True),
        (200, "Toronto", 7, False),
    ])
    def test_no_probe_means_exactly_the_previous_behaviour(self, budget, destination,
                                                           nights, expected):
        assert assess_budget(budget, destination, nights, 1,
                             "Lahore").feasible is expected

    def test_the_experiment_does_not_pass_a_probe(self):
        """Read from the source, so this cannot drift out of date."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source = open(os.path.join(root, "evaluation", "exp_budget_gate.py"),
                      encoding="utf-8").read()
        assert "price_probe" not in source, (
            "the budget-gate experiment now passes a price probe; its published "
            "Cohen's kappa no longer describes the code that produced it")


class TestTheStyleShortfallFlag:
    def test_asking_for_luxury_on_a_middling_budget_is_flagged(self):
        verdict = assess_budget(1200, "Istanbul", 4, 1, "Lahore",
                                travel_style="I want a luxury trip")
        note = verdict.style_shortfall()
        assert note is not None
        assert "luxury" in note.lower()
        assert "$" in note, "the note has to name the figure that would reach it"

    def test_a_budget_that_reaches_luxury_is_not_flagged(self):
        verdict = assess_budget(8000, "Istanbul", 4, 1, "Lahore",
                                travel_style="luxury")
        assert verdict.style_shortfall() is None

    def test_no_flag_when_luxury_was_never_asked_for(self):
        verdict = assess_budget(1200, "Istanbul", 4, 1, "Lahore",
                                travel_style="moderate")
        assert verdict.style_shortfall() is None

    def test_no_flag_on_a_refusal(self):
        """A refusal already explains itself; adding a style note would be noise."""
        verdict = assess_budget(100, "New York", 7, 1, "Lahore",
                                travel_style="luxury")
        assert not verdict.feasible
        assert verdict.style_shortfall() is None


class TestAskingForAPriceCostsQuotaAndIsRationed:
    """
    A live search spends one of thirty monthly flight requests, so when it may
    happen is a decision, not a default.

    None of these tests makes a network call. They check the gate rather than the
    call: what would be attempted, and what would not.
    """

    def test_a_probe_will_not_ask_unless_told_to(self, monkeypatch):
        called = []
        import trip_planner.core.real_prices as rp
        monkeypatch.setattr(rp, "live_flight_price",
                            lambda *a, **k: called.append(a) or None)
        rp.PriceProbe(allow_live=False, departure_date="2026-12-01").flight(
            "Lahore", "Kyoto")
        assert not called, "a probe asked for a live price without being allowed to"

    def test_a_recorded_route_is_never_bought_again(self, monkeypatch):
        """
        The recording is free and is a real price. Buying the same route again
        would spend quota to learn nothing.
        """
        called = []
        import trip_planner.core.real_prices as rp
        monkeypatch.setattr(rp, "live_flight_price",
                            lambda *a, **k: called.append(a) or None)
        price = rp.PriceProbe(allow_live=True,
                              departure_date="2026-08-15").flight(*RECORDED_ROUTE)
        assert price is not None and price.source == "recorded"
        assert not called, "a route already on disk was bought again"

    def test_no_date_means_no_request(self):
        """
        A fare is for a date. Asking without one would spend a request to receive
        a price for a trip nobody is taking.
        """
        from trip_planner.core.real_prices import live_flight_price
        assert live_flight_price("Lahore", "Kyoto", "") is None

    def test_a_failed_request_returns_nothing_rather_than_a_number(self,
                                                                  monkeypatch):
        """
        No key, no network, a tripped quota guard, an empty result: all of them
        have to produce None. Returning a plausible figure from a failed lookup is
        how a system starts reporting numbers nobody can account for.
        """
        import trip_planner.core.real_prices as rp

        def explode(*_a, **_k):
            raise RuntimeError("quota guard tripped")

        monkeypatch.setattr("trip_planner.tools.travel_apis._call_fly_scraper_api",
                            explode)
        assert rp.live_flight_price("Lahore", "Kyoto", "2026-12-01") is None

    def test_only_an_unlisted_destination_is_allowed_to_ask(self):
        """
        Read from the orchestrator's source, so the rule cannot quietly widen.

        For a city the table knows, the estimate is already grounded and a purchase
        buys nothing. The request is worth making exactly where the alternative is
        a mid-tier default.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source = open(os.path.join(root, "trip_planner", "orchestrator.py"),
                      encoding="utf-8").read()
        assert "allow_live=unlisted" in source, (
            "the orchestrator no longer gates live price checks on the "
            "destination being unlisted")
        assert "is_known_destination" in source
