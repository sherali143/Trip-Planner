"""
Debug Kiwi API - Check why dates are wrong
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
KIWI_HOST = "kiwi-com-cheap-flights.p.rapidapi.com"

# Test with specific date
url = f"https://{KIWI_HOST}/round-trip"
params = {
    "source": "ISB",
    "destination": "DOH",
    "departureDate": "2025-12-15",
    "returnDate": "2025-12-25",
    "adults": 1,
    "adultsHoldBags": "[0]",
    "adultsHandBags": "[1]",
    "currency": "USD",
    "cabinClass": "ECONOMY"
}

headers = {
    "x-rapidapi-host": KIWI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}

print("🔍 Testing Kiwi API with specific dates...")
print(f"   Departure: 2025-12-15")
print(f"   Return: 2025-12-25")
print()

response = requests.get(url, headers=headers, params=params, timeout=30)
data = response.json()

print(f"Status: {response.status_code}")
print(f"Number of itineraries: {len(data.get('itineraries', []))}")

# Check the actual dates in the response
print("\n📅 ACTUAL DATES IN RESPONSE:")
for idx, itin in enumerate(data.get("itineraries", [])[:5], 1):
    outbound = itin.get("outbound", {})
    inbound = itin.get("inbound", {})
    
    out_segments = outbound.get("sectorSegments", [])
    in_segments = inbound.get("sectorSegments", [])
    
    if out_segments:
        first_out = out_segments[0].get("segment", {})
        out_time = first_out.get("source", {}).get("localTime", "N/A")
        print(f"\nOption {idx}:")
        print(f"   Outbound: {out_time[:10] if out_time != 'N/A' else 'N/A'}")
    
    if in_segments:
        first_in = in_segments[0].get("segment", {})
        in_time = first_in.get("source", {}).get("localTime", "N/A")
        print(f"   Return: {in_time[:10] if in_time != 'N/A' else 'N/A'}")

# Save full response for analysis
with open("kiwi_response_debug.json", "w") as f:
    json.dump(data, f, indent=2)
print("\n💾 Full response saved to kiwi_response_debug.json")

# Check if there's a different endpoint or parameter
print("\n" + "="*70)
print("🔍 Checking API documentation parameters...")
print("="*70)

# The issue might be that this API returns "cheap flights" not "flights on date"
# Let's check if there's a date filtering parameter
print("""
The Kiwi API appears to return "cheap flight deals" across multiple dates,
not flights specifically on the requested date.

This is common with "cheap flights" APIs - they search for the best prices
over a range of dates rather than exact dates.

OPTIONS TO FIX:
1. Use a different API endpoint that supports exact dates
2. Filter results to only show flights matching our dates
3. Use the Amadeus or Skyscanner API instead
""")
