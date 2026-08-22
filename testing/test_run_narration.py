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


# ---------------------------------------------------------------------------
# The narration reaches the console as well as the page
# ---------------------------------------------------------------------------
#
# The web interface captures the run's output so it can be shown on the page.
# Pointed at a plain StringIO that is ALL it did: every step, the route, the
# budget and each search result went into the page, and the terminal running
# `streamlit run` stayed silent for the whole plan — which is where a
# demonstration is usually watched from.

class TestTheConsoleStillSeesTheRun:
    def test_what_is_captured_is_also_forwarded(self):
        import io
        from contextlib import redirect_stdout

        from trip_planner.core.log_setup import TeeStream

        console = io.StringIO()
        tee = TeeStream(console)
        with redirect_stdout(tee):
            print("STEP 2 of 4  PREFERENCES EXTRACTOR")
            print("      flight   5 options, cheapest $937")

        assert "PREFERENCES EXTRACTOR" in console.getvalue()
        assert "cheapest $937" in console.getvalue()
        assert tee.getvalue() == console.getvalue(), (
            "the page and the console disagree about what happened")

    def test_a_console_that_cannot_encode_does_not_stop_the_run(self):
        """
        A Windows console on a legacy code page raises UnicodeEncodeError on the
        arrows and symbols in the A2A summary. Losing a line of narration is not
        a reason to lose a plan — and that exact failure has already cost one run
        in this project, when a arrow was printed from inside the flight call.
        """
        from contextlib import redirect_stdout

        from trip_planner.core.log_setup import TeeStream

        class CannotEncode:
            def write(self, text):
                raise UnicodeEncodeError("cp1252", text, 0, 1, "not encodable")

            def flush(self):
                pass

        tee = TeeStream(CannotEncode())
        with redirect_stdout(tee):
            print("A2A: preferences_extractor -> itinerary_coordinator")

        assert "preferences_extractor" in tee.getvalue(), (
            "the page lost the line as well")

    def test_the_page_reads_the_run_through_this_and_not_a_bare_buffer(self):
        """
        Read from the source. If the interface goes back to a plain StringIO the
        console falls silent again, and nothing else would notice.
        """
        import pathlib

        source = (pathlib.Path(__file__).parent.parent / "trip_planner" / "ui"
                  / "app.py").read_text(encoding="utf-8")
        assert "TeeStream(sys.stdout)" in source
        assert "redirect_stdout(io.StringIO())" not in source
