"""
Direct test of flight API - no CrewAI, just raw API calls
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
print(f"API Key loaded: {'Yes' if RAPIDAPI_KEY else 'No'}")

# Test 1: Simple one-way flight
print("\n" + "="*70)
print("TEST 1: One-way flight ISB -> DOH")
print("="*70)

url = "https://kiwi-com-cheap-flights.p.rapidapi.com/one-way"
params = {
    "source": "ISB",
    "destination": "DOH",
    "date": "2025-12-15",
    "adults": 1,
    "adultsHoldBags": "[0]",
    "adultsHandBags": "[1]",
    "currency": "USD"
}

headers = {
    "x-rapidapi-host": "kiwi-com-cheap-flights.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if "error" in data:
            print(f"❌ API Error: {data.get('error')}")
        else:
            itineraries = data.get("itineraries", [])
            print(f"✅ Found {len(itineraries)} flights!")
            
            if itineraries:
                for i, itin in enumerate(itineraries[:3], 1):
                    price = itin.get("price", {})
                    print(f"\n  Flight {i}:")
                    print(f"    Price: {price.get('amount')} {price.get('currency', 'USD')}")
                    
                    # Get outbound details
                    outbound = itin.get("outbound", {})
                    if outbound:
                        sectors = outbound.get("sectorSegments", [])
                        for seg in sectors:
                            segment = seg.get("segment", {})
                            carrier = segment.get("carrier", {})
                            source = segment.get("source", {})
                            dest = segment.get("destination", {})
                            
                            print(f"    Airline: {carrier.get('name', 'Unknown')}")
                            print(f"    Route: {source.get('station', {}).get('code', 'N/A')} -> {dest.get('station', {}).get('code', 'N/A')}")
    else:
        print(f"Error: {response.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")


# Test 2: Round-trip flight
print("\n" + "="*70)
print("TEST 2: Round-trip flight ISB -> DOH")
print("="*70)

url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"
params = {
    "source": "ISB",
    "destination": "DOH",
    "departureDate": "2025-12-15",
    "returnDate": "2025-12-20",
    "adults": 1,
    "adultsHoldBags": "[0]",
    "adultsHandBags": "[1]",
    "currency": "USD",
    "cabinClass": "ECONOMY"
}

print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if "error" in data:
            print(f"❌ API Error: {data.get('error')}")
        else:
            itineraries = data.get("itineraries", [])
            print(f"✅ Found {len(itineraries)} flights!")
            
            if itineraries:
                for i, itin in enumerate(itineraries[:3], 1):
                    price = itin.get("price", {})
                    print(f"\n  Flight {i}:")
                    print(f"    Price: {price.get('amount')} {price.get('currency', 'USD')}")
    else:
        print(f"Error: {response.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "="*70)
print("DIRECT API TESTS COMPLETE")
print("="*70)
