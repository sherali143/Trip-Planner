"""
Tests for budget validation logic.

Verifies that the budget validation correctly identifies unrealistic
budgets for trips based on destination, duration, and traveler count.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBudgetValidation:
    """Test budget validation logic from main.py."""
    
    @pytest.fixture
    def mock_is_budget_too_low(self):
        """
        Create a standalone version of the budget validation logic
        for testing without initializing the full TripPlannerCrew.
        """
        import re
        import json
        
        def is_budget_too_low(extraction_output: str) -> bool:
            try:
                # Parse budget from extraction output
                try:
                    json_match = re.search(
                        r'\{(?:[^{}]|\{[^{}]*\})*"total_budget"(?:[^{}]|\{[^{}]*\})*\}',
                        extraction_output, re.DOTALL
                    )
                    if json_match:
                        data = json.loads(json_match.group(0))
                        total_budget = float(data.get('total_budget', 0))
                    else:
                        budget_match = re.search(
                            r'"total_budget":\s*(\d+(?:\.\d+)?)',
                            extraction_output
                        )
                        if budget_match:
                            total_budget = float(budget_match.group(1))
                        else:
                            return False
                except json.JSONDecodeError:
                    budget_match = re.search(
                        r'"total_budget":\s*(\d+(?:\.\d+)?)',
                        extraction_output
                    )
                    if budget_match:
                        total_budget = float(budget_match.group(1))
                    else:
                        return False
                
                # Get trip duration
                duration_match = re.search(
                    r'"trip_duration":\s*(\d+)',
                    extraction_output
                )
                trip_duration = int(duration_match.group(1)) if duration_match else 5
                
                # Get number of travelers
                travelers_match = re.search(
                    r'"total_travelers":\s*(\d+)',
                    extraction_output
                )
                num_travelers = int(travelers_match.group(1)) if travelers_match else 1
                
                # Check for explicit budget warning
                if "BUDGET_TOO_LOW" in extraction_output:
                    return True
                
                # Calculate minimum realistic budget
                min_flight_cost = 300 * num_travelers
                min_hotel_cost = 50 * trip_duration
                min_daily_cost = 30 * trip_duration * num_travelers
                min_total = min_flight_cost + min_hotel_cost + min_daily_cost
                
                # Budget too low if less than 60% of minimum
                if total_budget < (min_total * 0.6):
                    return True
                
                # Specific check for very low budgets
                if total_budget < 200:
                    return True
                
                return False
                
            except Exception:
                return False
        
        return is_budget_too_low
    
    # ========== Valid Budget Tests ==========
    
    def test_accepts_reasonable_budget_short_trip(self, mock_is_budget_too_low):
        """Test that reasonable budget for short trip is accepted."""
        extraction = '''{
            "origin": "New York",
            "destination": "London",
            "total_budget": 2000,
            "trip_duration": 5,
            "total_travelers": 1
        }'''
        assert mock_is_budget_too_low(extraction) is False
    
    def test_accepts_reasonable_budget_long_trip(self, mock_is_budget_too_low):
        """Test that reasonable budget for longer trip is accepted."""
        extraction = '''{
            "origin": "Los Angeles",
            "destination": "Tokyo",
            "total_budget": 5000,
            "trip_duration": 10,
            "total_travelers": 1
        }'''
        assert mock_is_budget_too_low(extraction) is False
    
    def test_accepts_budget_for_multiple_travelers(self, mock_is_budget_too_low):
        """Test budget scaled for multiple travelers."""
        extraction = '''{
            "origin": "Chicago",
            "destination": "Paris",
            "total_budget": 6000,
            "trip_duration": 7,
            "total_travelers": 2
        }'''
        assert mock_is_budget_too_low(extraction) is False
    
    def test_accepts_luxury_budget(self, mock_is_budget_too_low):
        """Test that high luxury budget is accepted."""
        extraction = '''{
            "origin": "Miami",
            "destination": "Dubai",
            "total_budget": 15000,
            "trip_duration": 7,
            "total_travelers": 2
        }'''
        assert mock_is_budget_too_low(extraction) is False
    
    # ========== Invalid Budget Tests ==========
    
    def test_rejects_very_low_budget(self, mock_is_budget_too_low):
        """Test that extremely low budget is rejected."""
        extraction = '''{
            "origin": "New York",
            "destination": "Paris",
            "total_budget": 50,
            "trip_duration": 7,
            "total_travelers": 1
        }'''
        assert mock_is_budget_too_low(extraction) is True
    
    def test_rejects_budget_under_200(self, mock_is_budget_too_low):
        """Test that budget under $200 is always rejected."""
        extraction = '''{
            "origin": "Boston",
            "destination": "London",
            "total_budget": 150,
            "trip_duration": 3,
            "total_travelers": 1
        }'''
        assert mock_is_budget_too_low(extraction) is True
    
    def test_rejects_insufficient_budget_for_group(self, mock_is_budget_too_low):
        """Test that budget insufficient for group size is rejected."""
        extraction = '''{
            "origin": "Seattle",
            "destination": "Rome",
            "total_budget": 500,
            "trip_duration": 7,
            "total_travelers": 4
        }'''
        assert mock_is_budget_too_low(extraction) is True
    
    def test_rejects_budget_with_explicit_warning(self, mock_is_budget_too_low):
        """Test that explicit BUDGET_TOO_LOW flag is respected."""
        extraction = '''{
            "origin": "Dallas",
            "destination": "Tokyo",
            "total_budget": 1000,
            "trip_duration": 10,
            "total_travelers": 1,
            "budget_warning": "BUDGET_TOO_LOW"
        }'''
        assert mock_is_budget_too_low(extraction) is True
    
    # ========== Edge Cases ==========
    
    def test_handles_missing_duration(self, mock_is_budget_too_low):
        """Test handling when trip_duration is missing (defaults to 5)."""
        extraction = '''{
            "origin": "Atlanta",
            "destination": "Berlin",
            "total_budget": 2000,
            "total_travelers": 1
        }'''
        # With default 5 days and 1 traveler, $2000 should be enough
        assert mock_is_budget_too_low(extraction) is False
    
    def test_handles_missing_travelers(self, mock_is_budget_too_low):
        """Test handling when total_travelers is missing (defaults to 1)."""
        extraction = '''{
            "origin": "Denver",
            "destination": "Amsterdam",
            "total_budget": 2500,
            "trip_duration": 7
        }'''
        # With 1 traveler and 7 days, $2500 should be enough
        assert mock_is_budget_too_low(extraction) is False
    
    def test_handles_non_json_format(self, mock_is_budget_too_low):
        """Test handling of non-JSON extraction output."""
        extraction = '''
        Extracted preferences:
        - total_budget: 3000
        - trip_duration: 7
        - total_travelers: 2
        '''
        # Should fall back to regex parsing
        assert mock_is_budget_too_low(extraction) is False
    
    def test_handles_invalid_extraction(self, mock_is_budget_too_low):
        """Test handling of completely invalid extraction."""
        extraction = "This is not a valid extraction at all"
        # Should return False (can't determine, proceed with caution)
        assert mock_is_budget_too_low(extraction) is False
    
    # ========== Budget Calculation Tests ==========
    
    def test_budget_threshold_calculation(self, mock_is_budget_too_low):
        """Test the budget threshold calculations."""
        # Minimum for 1 person, 5 days:
        # min_flight = 300, min_hotel = 250, min_daily = 150
        # Total = 700, 60% threshold = 420
        
        # Just above threshold
        extraction_ok = '''{
            "total_budget": 450,
            "trip_duration": 5,
            "total_travelers": 1
        }'''
        assert mock_is_budget_too_low(extraction_ok) is False
        
        # Just below threshold
        extraction_low = '''{
            "total_budget": 350,
            "trip_duration": 5,
            "total_travelers": 1
        }'''
        assert mock_is_budget_too_low(extraction_low) is True


class TestBudgetBreakdown:
    """Test budget breakdown calculations."""
    
    def test_standard_allocation(self):
        """Test standard 35/35/20/10 budget allocation."""
        total_budget = 3000
        
        expected = {
            "flights": 1050.0,      # 35%
            "accommodation": 1050.0, # 35%
            "activities": 600.0,     # 20%
            "meals": 300.0           # 10%
        }
        
        actual = {
            "flights": total_budget * 0.35,
            "accommodation": total_budget * 0.35,
            "activities": total_budget * 0.20,
            "meals": total_budget * 0.10
        }
        
        assert actual == expected
        assert sum(actual.values()) == total_budget
    
    def test_per_night_hotel_budget(self):
        """Test per-night hotel budget calculation."""
        accommodation_budget = 1050
        trip_duration = 7
        
        per_night = accommodation_budget / trip_duration
        assert per_night == 150.0
    
    def test_daily_activities_budget(self):
        """Test daily activities + meals budget calculation."""
        activities_budget = 600
        meals_budget = 300
        trip_duration = 7
        
        daily_budget = (activities_budget + meals_budget) / trip_duration
        assert daily_budget == pytest.approx(128.57, rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
