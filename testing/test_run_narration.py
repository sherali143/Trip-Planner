"""
What the run says it did has to match what it did.

The console and the web page both show one line per search, produced by
`_summarise`. A search that failed still returns a string: the search layer
catches its own errors and hands back an explanation rather than raising, so
nothing downstream can tell the difference by shape alone.

That is how a failed hotel search came to be reported as "returned 371 chars".
The 371 characters read "ERROR: Failed to find destination" — a demonstration
would have shown a step that looked like it had worked, followed by an itinerary
built from nothing.

These tests hold two lines: a failure is named as a failure, and a real result is
still summarised by what is in it rather than by how long it is.

No model, no network, no keys.
"""

import pytest

from trip_planner.orchestrator import _summarise


# The real payloads, copied from a replay run rather than invented.
HOTEL_FAILURE = """
Hotel Search Results
====================
❌ ERROR: Failed to find destination "Istanbul, Turkey"
Error: No recorded response for GET https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination (params={'query': 'Istanbul, Turkey'}). Run once with TRIP_PLANNER_API_MODE=record to populate the cache.

Please try with a different city name or check your API key.
"""

VENUE_FAILURE = ("Sorry, I couldn't find anything about that. Error: No recorded "
                 "response for POST https://google.serper.dev/search "
                 "(params=None).")

TOOL_FAILURE = '{"success": false, "error": "connection reset"}'


class TestAFailureIsNamed:
    """A byte count is not a result, and it is not an error message either."""

    def test_a_failed_hotel_search_is_not_reported_as_a_length(self):
        summary = _summarise("hotel", HOTEL_FAILURE)
        assert "chars" not in summary, summary
        assert "NO DATA" in summary

    def test_a_failed_venue_search_is_not_reported_as_a_length(self):
        summary = _summarise("attraction", VENUE_FAILURE)
        assert "chars" not in summary, summary
        assert "NO DATA" in summary

    def test_a_tool_error_payload_is_recognised(self):
        assert "NO DATA" in _summarise("hotel", TOOL_FAILURE)

    def test_a_cache_miss_says_it_is_a_cache_miss(self):
        """
        The commonest failure during a demonstration, and the most misleading if
        unexplained — nothing is broken, that exact request was simply never
        recorded.
        """
        summary = _summarise("hotel", HOTEL_FAILURE)
        assert "recorded cache" in summary

    def test_nothing_returned_says_so(self):
        assert _summarise("flight", "") == "nothing returned"

    def test_a_failure_summary_stays_one_line(self):
        """It is printed as one indented line under a step."""
        for payload in (HOTEL_FAILURE, VENUE_FAILURE, TOOL_FAILURE):
            summary = _summarise("hotel", payload)
            assert "\n" not in summary, summary
            assert len(summary) <= 160, len(summary)


class TestARealResultIsStillSummarisedByContent:
    """The failure check must not swallow the successful cases."""

    def test_flights_are_counted_and_priced(self):
        payload = ('{"flights": [{"total_price": 937.0}, {"total_price": 1204.0},'
                   ' {"total_price": 1580.0}]}')
        summary = _summarise("flight", payload)
        assert "3 options" in summary
        assert "$937" in summary

    def test_hotels_are_counted_and_priced(self):
        payload = "Found 20 hotels\n1. Aloft Karakoy ($92.40/night)\n2. X ($150.00/night)"
        summary = _summarise("hotel", payload)
        assert "20 hotels" in summary
        assert "$92/night" in summary

    def test_venue_results_are_counted(self):
        payload = "Title: Hagia Sophia\nTitle: Topkapi Palace\nTitle: Basilica Cistern"
        assert _summarise("attraction", payload) == "3 results"

    def test_an_empty_flight_list_is_not_called_a_success(self):
        assert "no flights found" in _summarise("flight", '{"flights": []}')

    @pytest.mark.parametrize("payload", [
        "some text with no recognisable shape at all",
        '{"unexpected": "json"}',
    ])
    def test_an_unrecognised_shape_falls_back_to_the_size(self, payload):
        """
        Deliberate. A narration helper must never be the reason a run fails, so
        anything it cannot read is reported as what it can measure.
        """
        assert "chars" in _summarise("hotel", payload)

    def test_the_word_error_inside_a_real_result_is_not_a_false_alarm(self):
        """
        "ERROR:" is the marker, not the word "error". A hotel called the Terror
        Museum, or a review mentioning an error, must not blank the result.
        """
        payload = ("Found 3 hotels\n1. Hotel near the Error Museum ($88.00/night)\n"
                   "2. B ($99.00/night)\n3. C ($120.00/night)")
        summary = _summarise("hotel", payload)
        assert "3 hotels" in summary, summary
        assert "NO DATA" not in summary
