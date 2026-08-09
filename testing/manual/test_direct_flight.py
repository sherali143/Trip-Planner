"""
Direct test of flight API via fly-scraper
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
print(f"API Key loaded: {'Yes' if RAPIDAPI_KEY else 'No'}")

# Test: One-way flight ISB -> DOH using fly-scraper
print("\n" + "="*70)
print("TEST: One-way flight ISB -> DOH via fly-scraper")
print("="*70)

from src.tools.mcp_tools import _call_booking_flights_api

result = _call_booking_flights_api(
    origin_city="Islamabad",
    destination_city="Doha",
    departure_date="2025-12-15",
    return_date="2025-12-20",
    adults=2
)
print(result[:2000] if len(result) > 2000 else result)

print("\n" + "="*70)
print("DIRECT API TEST COMPLETE")
print("="*70)
