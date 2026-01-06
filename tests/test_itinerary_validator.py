"""
Tests for the itinerary validator module.

Verifies that day-count validation correctly identifies complete and
incomplete itineraries.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.itinerary_validator import (
    validate_day_count,
    get_missing_days,
    regenerate_if_incomplete,
    extract_trip_duration_from_extraction,
    add_completion_notice
)


class TestValidateDayCount:
    """Test the validate_day_count function."""
    
    def test_validates_correct_day_count_simple(self):
        """Test validation with simple day headers."""
        itinerary = """
        ## Day 1: Arrival
        Morning activities...
        
        ## Day 2: Exploration
        Visit attractions...
        
        ## Day 3: Departure
        Final activities...
        """
        is_valid, count, found_days = validate_day_count(itinerary, 3)
        assert is_valid is True
        assert count == 3
        assert found_days == [1, 2, 3]
    
    def test_validates_correct_day_count_with_emojis(self):
        """Test validation with emoji-prefixed day headers."""
        itinerary = """
        🌅 Day 1: Arrival in Paris
        Morning: Check in to hotel
        
        🌅 Day 2: Exploring the City
        Morning: Eiffel Tower
        
        🌅 Day 3: Museums
        Morning: Louvre
        
        🌅 Day 4: Day Trip
        Morning: Versailles
        
        🌅 Day 5: Departure
        Morning: Pack and leave
        """
        is_valid, count, found_days = validate_day_count(itinerary, 5)
        assert is_valid is True
        assert count == 5
        assert found_days == [1, 2, 3, 4, 5]
    
    def test_validates_uppercase_day_headers(self):
        """Test validation with uppercase DAY headers."""
        itinerary = """
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        🌅 DAY 1: ARRIVAL
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        **MORNING**
        Check in to hotel
        
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        🌅 DAY 2: EXPLORATION
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        **MORNING**
        Visit attractions
        """
        is_valid, count, found_days = validate_day_count(itinerary, 2)
        assert is_valid is True
        assert count == 2
    
    def test_detects_missing_days(self):
        """Test detection of incomplete itinerary."""
        itinerary = """
        ## Day 1: Arrival
        Morning activities...
        """
        is_valid, count, found_days = validate_day_count(itinerary, 5)
        assert is_valid is False
        assert count == 1
        assert found_days == [1]
    
    def test_detects_gaps_in_days(self):
        """Test detection of non-sequential days."""
        itinerary = """
        ## Day 1: Arrival
        Morning activities...
        
        ## Day 3: Skip
        Skipped day 2
        
        ## Day 5: Another skip
        Missing days 2 and 4
        """
        is_valid, count, found_days = validate_day_count(itinerary, 5)
        assert is_valid is False
        assert count == 3
        assert found_days == [1, 3, 5]
    
    def test_handles_bold_day_headers(self):
        """Test validation with bold markdown headers."""
        itinerary = """
        **Day 1:** Arrival
        Morning activities...
        
        **Day 2:** Exploration
        Visit attractions...
        """
        is_valid, count, found_days = validate_day_count(itinerary, 2)
        assert is_valid is True
        assert count == 2
    
    def test_handles_empty_itinerary(self):
        """Test validation with empty or no day headers."""
        itinerary = "This is just some text without any day headers."
        is_valid, count, found_days = validate_day_count(itinerary, 5)
        assert is_valid is False
        assert count == 0
        assert found_days == []
    
    def test_exceeds_expected_days(self):
        """Test when itinerary has more days than expected."""
        itinerary = """
        Day 1: First
        Day 2: Second
        Day 3: Third
        Day 4: Fourth
        Day 5: Fifth
        """
        is_valid, count, found_days = validate_day_count(itinerary, 3)
        assert is_valid is True  # 5 >= 3
        assert count == 5


class TestGetMissingDays:
    """Test the get_missing_days function."""
    
    def test_identifies_missing_days(self):
        """Test identification of specific missing days."""
        itinerary = """
        Day 1: First
        Day 3: Third
        Day 5: Fifth
        """
        missing = get_missing_days(itinerary, 5)
        assert missing == [2, 4]
    
    def test_no_missing_days(self):
        """Test when all days are present."""
        itinerary = """
        Day 1: First
        Day 2: Second
        Day 3: Third
        """
        missing = get_missing_days(itinerary, 3)
        assert missing == []
    
    def test_all_days_missing(self):
        """Test when no days are present."""
        itinerary = "No day headers here"
        missing = get_missing_days(itinerary, 3)
        assert missing == [1, 2, 3]


class TestExtractTripDuration:
    """Test the extract_trip_duration_from_extraction function."""
    
    def test_extracts_from_json(self):
        """Test extraction from JSON format."""
        extraction = '{"origin": "NYC", "destination": "Paris", "trip_duration": 7}'
        duration = extract_trip_duration_from_extraction(extraction)
        assert duration == 7
    
    def test_extracts_from_regex(self):
        """Test extraction using regex fallback."""
        extraction = 'The trip_duration: 5 days and other info'
        duration = extract_trip_duration_from_extraction(extraction)
        assert duration == 5
    
    def test_handles_missing_duration(self):
        """Test handling of missing duration."""
        extraction = '{"origin": "NYC", "destination": "Paris"}'
        duration = extract_trip_duration_from_extraction(extraction)
        assert duration is None
    
    def test_handles_invalid_json(self):
        """Test handling of invalid JSON."""
        extraction = 'This is not valid JSON but contains trip_duration: 10'
        duration = extract_trip_duration_from_extraction(extraction)
        assert duration == 10


class TestAddCompletionNotice:
    """Test the add_completion_notice function."""
    
    def test_adds_notice_when_incomplete(self):
        """Test that notice is added for incomplete itinerary."""
        itinerary = "Day 1: Arrival\nSome content here."
        result = add_completion_notice(itinerary, 1, 5)
        assert "Note" in result
        assert "1 out of 5" in result
    
    def test_no_notice_when_complete(self):
        """Test that no notice is added for complete itinerary."""
        itinerary = "Day 1: Arrival\nSome content here."
        result = add_completion_notice(itinerary, 5, 5)
        assert result == itinerary
        assert "Note" not in result


class TestRegenerateIfIncomplete:
    """Test the regenerate_if_incomplete function."""
    
    def test_returns_valid_immediately(self):
        """Test that valid itinerary is returned without regeneration."""
        itinerary = """
        Day 1: First
        Day 2: Second
        Day 3: Third
        """
        
        # This shouldn't be called
        def regenerate_fn():
            raise Exception("Should not be called")
        
        result, was_regenerated, attempts = regenerate_if_incomplete(
            itinerary, 3, regenerate_fn
        )
        
        assert was_regenerated is False
        assert attempts == 0
        assert "Day 1" in result
    
    def test_regenerates_incomplete(self):
        """Test that incomplete itinerary triggers regeneration."""
        incomplete = "Day 1: Only one day"
        complete = """
        Day 1: First
        Day 2: Second
        Day 3: Third
        """
        
        call_count = [0]
        
        def regenerate_fn():
            call_count[0] += 1
            return complete
        
        result, was_regenerated, attempts = regenerate_if_incomplete(
            incomplete, 3, regenerate_fn
        )
        
        assert was_regenerated is True
        assert attempts == 1
        assert call_count[0] == 1
        assert "Day 3" in result
    
    def test_respects_max_attempts(self):
        """Test that max attempts limit is respected."""
        incomplete = "Day 1: Only one day"
        
        call_count = [0]
        
        def regenerate_fn():
            call_count[0] += 1
            return "Still incomplete: Day 1 only"
        
        result, was_regenerated, attempts = regenerate_if_incomplete(
            incomplete, 5, regenerate_fn, max_attempts=3
        )
        
        assert was_regenerated is True
        assert attempts == 3
        assert call_count[0] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
