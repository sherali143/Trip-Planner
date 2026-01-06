"""
Itinerary Validator

Programmatic validation to replace prompt-based enforcement of day counts.
Validates that generated itineraries contain the expected number of day sections.
"""

import re
from typing import Tuple, Optional, Callable, List
import logging

logger = logging.getLogger(__name__)


def validate_day_count(itinerary: str, expected_days: int) -> Tuple[bool, int, List[int]]:
    """
    Validate that itinerary contains the expected number of day sections.
    
    Matches various day header formats:
    - "Day 1:", "DAY 2:", "day 3:"
    - "## Day 1", "### Day 2"
    - "**Day 1**", "**Day 1:**"
    - "🌅 Day 1" (with emoji prefix)
    
    Args:
        itinerary: The generated itinerary text
        expected_days: Number of days expected based on trip duration
    
    Returns:
        Tuple of (is_valid, actual_count, found_days)
        - is_valid: True if actual_count >= expected_days
        - actual_count: Number of unique day sections found
        - found_days: List of day numbers found (for debugging)
    """
    # Match patterns like "Day 1:", "DAY 2:", "## Day 3", "**Day 4**", "🌅 Day 1"
    day_patterns = [
        r'(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?(?:[🌅🌄🌃🌆🌇✈️🏨]\s*)?(?:day|DAY|Day)\s*(\d+)\s*[:\*#\-–—]',
        r'(?:^|\n)\s*\*{2}Day\s*(\d+)\*{2}',
        r'(?:^|\n)\s*━+\s*(?:🌅\s*)?DAY\s*(\d+)',
    ]
    
    found_days = set()
    
    for pattern in day_patterns:
        matches = re.findall(pattern, itinerary, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            try:
                day_num = int(match)
                if 1 <= day_num <= 365:  # Reasonable day number
                    found_days.add(day_num)
            except ValueError:
                continue
    
    found_days_sorted = sorted(found_days)
    actual_count = len(found_days)
    
    # Check if we have enough days
    is_valid = actual_count >= expected_days
    
    logger.debug(f"[Validator] Expected {expected_days} days, found {actual_count}: {found_days_sorted}")
    
    return is_valid, actual_count, found_days_sorted


def get_missing_days(itinerary: str, expected_days: int) -> List[int]:
    """
    Get list of missing day numbers.
    
    Args:
        itinerary: The generated itinerary text
        expected_days: Number of days expected
    
    Returns:
        List of day numbers that are missing
    """
    _, _, found_days = validate_day_count(itinerary, expected_days)
    expected = set(range(1, expected_days + 1))
    missing = expected - set(found_days)
    return sorted(missing)


def regenerate_if_incomplete(
    itinerary: str, 
    expected_days: int, 
    regenerate_fn: Callable[[], str],
    max_attempts: int = 2
) -> Tuple[str, bool, int]:
    """
    Regenerate itinerary if day count doesn't match.
    
    This replaces the prompt-based "CRITICAL: WRITE ALL DAYS" approach
    with programmatic validation and retry.
    
    Args:
        itinerary: Initial generated itinerary
        expected_days: Number of days expected
        regenerate_fn: Function to call for regeneration
        max_attempts: Maximum regeneration attempts (default 2)
    
    Returns:
        Tuple of (final_itinerary, was_regenerated, attempts_made)
    """
    is_valid, count, found_days = validate_day_count(itinerary, expected_days)
    
    if is_valid:
        return itinerary, False, 0
    
    # Need to regenerate
    for attempt in range(1, max_attempts + 1):
        missing = get_missing_days(itinerary, expected_days)
        
        print(f"⚠️ [Validation] Day count mismatch: expected {expected_days}, got {count}.")
        print(f"   Missing days: {missing}")
        print(f"   Regenerating (attempt {attempt}/{max_attempts})...")
        
        logger.warning(
            f"[Validator] Regenerating itinerary: expected {expected_days} days, "
            f"got {count}. Missing: {missing}"
        )
        
        try:
            itinerary = regenerate_fn()
            is_valid, count, found_days = validate_day_count(itinerary, expected_days)
            
            if is_valid:
                print(f"✅ [Validation] Regeneration successful: {count} days found")
                return itinerary, True, attempt
                
        except Exception as e:
            logger.error(f"[Validator] Regeneration failed: {e}")
            print(f"❌ [Validation] Regeneration failed: {e}")
    
    # Return best attempt even if incomplete
    print(f"⚠️ [Validation] Could not generate complete itinerary after {max_attempts} attempts")
    return itinerary, True, max_attempts


def extract_trip_duration_from_extraction(extraction_output: str) -> Optional[int]:
    """
    Extract trip duration from the preferences extraction output.
    
    Args:
        extraction_output: JSON string from extraction task
    
    Returns:
        Trip duration in days, or None if not found
    """
    import json
    
    # Try to parse as JSON
    try:
        # Look for JSON object in the output
        json_match = re.search(r'\{[^{}]*"trip_duration"[^{}]*\}', extraction_output, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return int(data.get('trip_duration', 0)) or None
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    # Fallback to regex
    duration_match = re.search(r'"trip_duration"\s*:\s*(\d+)', extraction_output)
    if duration_match:
        return int(duration_match.group(1))
    
    # Try alternative patterns
    alt_patterns = [
        r'trip_duration:\s*(\d+)',
        r'(\d+)\s*(?:day|night)s?\s*trip',
        r'for\s*(\d+)\s*(?:day|night)s?',
    ]
    
    for pattern in alt_patterns:
        match = re.search(pattern, extraction_output, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


def add_completion_notice(itinerary: str, found_days: int, expected_days: int) -> str:
    """
    Add a notice to the itinerary if it's incomplete.
    
    Args:
        itinerary: The generated itinerary
        found_days: Number of days actually found
        expected_days: Number of days expected
    
    Returns:
        Itinerary with notice appended if incomplete
    """
    if found_days >= expected_days:
        return itinerary
    
    notice = f"""

---

⚠️ **Note**: This itinerary contains {found_days} out of {expected_days} requested days.
For the remaining days, please consider:
- Continuing with similar activities from earlier days
- Adding free exploration time
- Visiting any attractions that were mentioned but not scheduled

To get a complete itinerary, please try regenerating with more specific preferences.
"""
    
    return itinerary + notice
