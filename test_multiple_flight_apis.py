"""
Test Multiple Flight APIs to find best working one
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

print("="*70)
print("🔍 TESTING MULTIPLE FLIGHT APIs")
print("="*70)

# Test parameters
origin = "ISB"
destination = "DOH"
departure_date = "2025-12-15"
return_date = "2025-12-25"

# ============================================
# API 1: Skyscanner API
# ============================================
print("\n📍 API 1: SKYSCANNER")
print("-"*50)

try:
    # First get location IDs
    url = "https://skyscanner80.p.rapidapi.com/api/v1/flights/auto-complete"
    headers = {
        "x-rapidapi-host": "skyscanner80.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    params = {"query": "Islamabad"}
    
    response = requests.get(url, headers=headers, params=params, timeout=15)
    print(f"   Auto-complete status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Found: {json.dumps(data, indent=2)[:300]}...")
        
        # Try flight search
        url = "https://skyscanner80.p.rapidapi.com/api/v1/flights/search-roundtrip"
        params = {
            "fromId": "ISB",  # or use entity from auto-complete
            "toId": "DOH",
            "departDate": departure_date,
            "returnDate": return_date,
            "adults": 1,
            "currency": "USD",
            "market": "US",
            "locale": "en-US"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"   Flight search status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Skyscanner works!")
            print(f"   Response preview: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Exception: {e}")

# ============================================
# API 2: Amadeus (if available)
# ============================================
print("\n📍 API 2: TRIPADVISOR FLIGHTS")
print("-"*50)

try:
    url = "https://tripadvisor16.p.rapidapi.com/api/v1/flights/searchFlights"
    headers = {
        "x-rapidapi-host": "tripadvisor16.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    params = {
        "sourceAirportCode": origin,
        "destinationAirportCode": destination,
        "date": departure_date,
        "itineraryType": "ROUND_TRIP",
        "sortOrder": "PRICE",
        "numAdults": 1,
        "numSeniors": 0,
        "classOfService": "ECONOMY",
        "returnDate": return_date,
        "pageNumber": 1,
        "currencyCode": "USD"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        flights = data.get("data", {}).get("flights", [])
        print(f"   ✅ TripAdvisor works! Found {len(flights)} flights")
        
        if flights:
            for idx, flight in enumerate(flights[:3], 1):
                segments = flight.get("segments", [])
                price = flight.get("purchaseLinks", [{}])[0].get("totalPrice", "N/A")
                print(f"\n   Flight {idx}: ${price}")
                for seg in segments[:2]:
                    legs = seg.get("legs", [])
                    for leg in legs[:1]:
                        dep = leg.get("departureDateTime", "")
                        arr = leg.get("arrivalDateTime", "")
                        carrier = leg.get("marketingCarrier", {}).get("displayName", "Unknown")
                        print(f"      {carrier}: {dep[:10]} {dep[11:16]} → {arr[11:16]}")
    else:
        print(f"   ❌ Error: {response.text[:300]}")
        
except Exception as e:
    print(f"   ❌ Exception: {e}")

# ============================================
# API 3: Priceline
# ============================================
print("\n📍 API 3: PRICELINE")
print("-"*50)

try:
    url = "https://priceline-com-provider.p.rapidapi.com/v2/flight/roundTrip"
    headers = {
        "x-rapidapi-host": "priceline-com-provider.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    params = {
        "departure_date": departure_date,
        "adults": 1,
        "sid": "iSiX639",
        "origin_airport_code": origin,
        "destination_airport_code": destination,
        "return_date": return_date
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Priceline works!")
        print(f"   Response: {json.dumps(data, indent=2)[:500]}...")
    else:
        print(f"   ❌ Error: {response.text[:300]}")
        
except Exception as e:
    print(f"   ❌ Exception: {e}")

# ============================================
# API 4: Google Flights (via SerpApi style)
# ============================================
print("\n📍 API 4: GOOGLE FLIGHTS")
print("-"*50)

try:
    url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"
    headers = {
        "x-rapidapi-host": "google-flights2.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    params = {
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "return_date": return_date,
        "currency": "USD",
        "adults": 1,
        "travel_class": 1
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Google Flights works!")
        print(f"   Response: {json.dumps(data, indent=2)[:500]}...")
    else:
        print(f"   ❌ Error: {response.text[:300]}")
        
except Exception as e:
    print(f"   ❌ Exception: {e}")

# ============================================
# API 5: Flights Sky Scanner (different endpoint)
# ============================================
print("\n📍 API 5: SKY-SCANNER3")
print("-"*50)

try:
    url = "https://sky-scanner3.p.rapidapi.com/flights/search-roundtrip"
    headers = {
        "x-rapidapi-host": "sky-scanner3.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    params = {
        "fromEntityId": "ISB",
        "toEntityId": "DOH",
        "departDate": departure_date,
        "returnDate": return_date,
        "currency": "USD"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Sky-Scanner3 works!")
        itineraries = data.get("data", {}).get("itineraries", [])
        print(f"   Found {len(itineraries)} itineraries")
        
        for idx, itin in enumerate(itineraries[:3], 1):
            price = itin.get("price", {}).get("formatted", "N/A")
            legs = itin.get("legs", [])
            print(f"\n   Option {idx}: {price}")
            for leg in legs[:2]:
                origin_name = leg.get("origin", {}).get("name", "")
                dest_name = leg.get("destination", {}).get("name", "")
                departure = leg.get("departure", "")[:16]
                carriers = leg.get("carriers", {}).get("marketing", [])
                carrier_name = carriers[0].get("name", "Unknown") if carriers else "Unknown"
                print(f"      {carrier_name}: {origin_name} → {dest_name} at {departure}")
    else:
        print(f"   ❌ Error: {response.text[:300]}")
        
except Exception as e:
    print(f"   ❌ Exception: {e}")


print("\n" + "="*70)
print("📊 SUMMARY")
print("="*70)
print("""
Check which APIs returned status 200 and actual flight data.
The best API will be one that:
1. Returns flights for the EXACT dates requested
2. Shows multiple airlines (not just PIA)
3. Has correct pricing
""")
