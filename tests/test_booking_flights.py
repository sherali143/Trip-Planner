"""
Test Booking.com Flights API
- searchDestination: Get airport/city IDs
- searchFlights: Search for actual flights
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
BOOKING_HOST = "booking-com15.p.rapidapi.com"

headers = {
    "x-rapidapi-host": BOOKING_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}

print("="*70)
print("🧪 TESTING BOOKING.COM FLIGHTS API")
print("="*70)

# Step 1: Search for Islamabad airport
print("\n📍 STEP 1: Search for Islamabad airport ID...")
url = f"https://{BOOKING_HOST}/api/v1/flights/searchDestination"
params = {"query": "islamabad"}

response = requests.get(url, headers=headers, params=params, timeout=30)
print(f"Status: {response.status_code}")

isb_data = response.json()
print(f"Response: {json.dumps(isb_data, indent=2)[:1000]}")

# Extract the airport ID
isb_id = None
if isb_data.get("status") and isb_data.get("data"):
    for item in isb_data["data"]:
        if "AIRPORT" in item.get("id", ""):
            isb_id = item["id"]
            print(f"\n✅ Found Islamabad Airport ID: {isb_id}")
            print(f"   Name: {item.get('name')}")
            break

# Step 2: Search for Doha airport
print("\n📍 STEP 2: Search for Doha airport ID...")
params = {"query": "doha"}

response = requests.get(url, headers=headers, params=params, timeout=30)
print(f"Status: {response.status_code}")

doha_data = response.json()
print(f"Response: {json.dumps(doha_data, indent=2)[:1000]}")

# Extract the airport ID
doha_id = None
if doha_data.get("status") and doha_data.get("data"):
    for item in doha_data["data"]:
        if "AIRPORT" in item.get("id", ""):
            doha_id = item["id"]
            print(f"\n✅ Found Doha Airport ID: {doha_id}")
            print(f"   Name: {item.get('name')}")
            break

# Step 3: Search for flights
if isb_id and doha_id:
    print("\n" + "="*70)
    print("✈️  STEP 3: Search for flights ISB -> DOH")
    print("="*70)
    
    url = f"https://{BOOKING_HOST}/api/v1/flights/searchFlights"
    params = {
        "fromId": isb_id,
        "toId": doha_id,
        "departDate": "2025-12-15",  # Specific date!
        "returnDate": "2025-12-25",  # Return date
        "pageNo": 1,
        "adults": 1,
        "children": "",
        "sort": "BEST",
        "cabinClass": "ECONOMY",
        "currency_code": "USD"
    }
    
    print(f"\nSearch parameters:")
    print(f"   From: {isb_id}")
    print(f"   To: {doha_id}")
    print(f"   Departure: 2025-12-15")
    print(f"   Return: 2025-12-25")
    print(f"   Adults: 1")
    
    response = requests.get(url, headers=headers, params=params, timeout=60)
    print(f"\nStatus: {response.status_code}")
    
    flight_data = response.json()
    
    # Save full response
    with open("booking_flights_response.json", "w") as f:
        json.dump(flight_data, f, indent=2)
    print("💾 Full response saved to booking_flights_response.json")
    
    # Parse the response
    if flight_data.get("status"):
        flights = flight_data.get("data", {}).get("flightOffers", [])
        print(f"\n✅ Found {len(flights)} flight offers!")
        
        for idx, flight in enumerate(flights[:5], 1):
            print(f"\n--- Flight Option {idx} ---")
            
            # Price
            price_info = flight.get("priceBreakdown", {})
            total_price = price_info.get("total", {}).get("units", 0)
            currency = price_info.get("total", {}).get("currencyCode", "USD")
            print(f"💰 Price: {total_price} {currency}")
            
            # Segments
            segments = flight.get("segments", [])
            for seg_idx, segment in enumerate(segments):
                direction = "OUTBOUND" if seg_idx == 0 else "RETURN"
                print(f"\n  📍 {direction}:")
                
                legs = segment.get("legs", [])
                for leg in legs:
                    dep_airport = leg.get("departureAirport", {}).get("code", "N/A")
                    arr_airport = leg.get("arrivalAirport", {}).get("code", "N/A")
                    dep_time = leg.get("departureTime", "N/A")
                    arr_time = leg.get("arrivalTime", "N/A")
                    carrier = leg.get("carriersData", [{}])[0].get("name", "Unknown")
                    flight_num = leg.get("flightInfo", {}).get("flightNumber", "N/A")
                    
                    print(f"     {dep_airport} → {arr_airport}")
                    print(f"     ✈️  {carrier} {flight_num}")
                    print(f"     🕐 {dep_time} - {arr_time}")
    else:
        print(f"❌ API Error: {flight_data.get('message', 'Unknown error')}")
        print(f"Full response: {json.dumps(flight_data, indent=2)[:500]}")
else:
    print("\n❌ Could not find airport IDs")
