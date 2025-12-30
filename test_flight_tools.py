"""
Test the updated flight tools directly
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.mcp_tools import _call_kiwi_api_direct, _search_round_trip_flights

print("="*70)
print("🧪 TESTING DIRECT FLIGHT API CALL")
print("="*70)

# Test 1: Direct API call
print("\n📍 Test 1: Direct Kiwi API call")
result = _call_kiwi_api_direct(
    origin="ISB",
    destination="DOH",
    departure_date="2025-12-15",
    return_date="2025-12-20",
    adults=2
)
print(result[:2000] if len(result) > 2000 else result)

# Test 2: Through the tool wrapper
print("\n" + "="*70)
print("📍 Test 2: Through _search_round_trip_flights wrapper")
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
