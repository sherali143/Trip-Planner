"""
Test the updated flight tools directly
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.mcp_tools import _search_round_trip_flights

print("="*70)
print("🧪 TESTING ROUND TRIP FLIGHT TOOL")
print("="*70)

# Test: Through the tool wrapper
print("\n" + "="*70)
print("📍 Testing _search_round_trip_flights wrapper")
print("="*70)
result2 = _search_round_trip_flights(
    source="ISB",
    destination="DOH",
    departure_date="2025-12-15",
    adults=2,
    return_date="2025-12-20",
    cabin_class="ECONOMY"
)
print(result2[:2000] if len(result2) > 2000 else result2)

print("\n" + "="*70)
print("✅ TESTS COMPLETE")
print("="*70)
