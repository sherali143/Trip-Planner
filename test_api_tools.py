"""
Quick test script to verify API tools are working
"""
import os
from dotenv import load_dotenv
from tools.mcp_tools import search_hotel_destination, search_round_trip_flights

# Load environment
load_dotenv()

print("="*60)
print("Testing API Tools")
print("="*60)

# Check API key
api_key = os.getenv("RAPIDAPI_KEY", "")
print(f"\nRAPIDAPI_KEY loaded: {'Yes' if api_key else 'No'}")
print(f"Key length: {len(api_key)}")
print(f"Key starts with: {api_key[:10] if len(api_key) > 10 else 'N/A'}...")

# Test hotel destination search
print("\n" + "="*60)
print("TEST 1: Search Hotel Destination (Paris)")
print("="*60)
result = search_hotel_destination("Paris")
print(result[:500] + "..." if len(result) > 500 else result)

# Test flight search
print("\n" + "="*60)
print("TEST 2: Search Flights (US to France)")
print("="*60)
result2 = search_round_trip_flights.invoke({
    "source": "Country:US",
    "destination": "Country:FR",
    "adults": 1,
    "cabin_class": "ECONOMY",
    "limit": 5
})
print(result2[:500] + "..." if len(result2) > 500 else result2)

print("\n" + "="*60)
print("Tests Complete")
print("="*60)
