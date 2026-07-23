"""
Test Hotel APIs - Check if Booking.com Hotel APIs are working
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
print("🧪 TESTING BOOKING.COM HOTEL APIs")
print("="*70)

# Test 1: Search Destination
print("\n📍 TEST 1: Search Hotel Destination (Doha)")
url = f"https://{BOOKING_HOST}/api/v1/hotels/searchDestination"
params = {"query": "Doha"}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:1000]}")
    
    if data.get("status") and data.get("data"):
        dest_id = data["data"][0].get("dest_id")
        dest_name = data["data"][0].get("name")
        print(f"\n✅ Found destination!")
        print(f"   Name: {dest_name}")
        print(f"   Dest ID: {dest_id}")
        
        # Test 2: Search Hotels with dest_id
        print("\n" + "="*70)
        print("🏨 TEST 2: Search Hotels in Doha")
        url = f"https://{BOOKING_HOST}/api/v1/hotels/searchHotels"
        params = {
            "dest_id": dest_id,
            "search_type": "CITY",
            "arrival_date": "2025-12-15",
            "departure_date": "2025-12-25",
            "adults": "1",
            "room_qty": "1",
            "page_number": "1",
            "currency_code": "USD"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=60)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if data.get("status"):
            hotels = data.get("data", {}).get("hotels", [])
            print(f"\n✅ Found {len(hotels)} hotels!")
            
            for idx, hotel in enumerate(hotels[:5], 1):
                print(f"\n   Hotel {idx}: {hotel.get('property', {}).get('name', 'N/A')}")
                print(f"   ID: {hotel.get('property', {}).get('id')}")
                price_info = hotel.get('property', {}).get('priceBreakdown', {})
                price = price_info.get('grossPrice', {}).get('value', 'N/A')
                print(f"   Price: ${price}")
                print(f"   Review Score: {hotel.get('property', {}).get('reviewScore', 'N/A')}/10")
        else:
            print(f"❌ Hotel search failed: {data.get('message', 'Unknown error')}")
            print(f"Full response: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"❌ Destination search failed")
        print(f"   Status: {data.get('status')}")
        print(f"   Message: {data.get('message', 'Unknown')}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Try different query format
print("\n" + "="*70)
print("📍 TEST 3: Search Hotel Destination (just 'Doha' without Qatar)")
url = f"https://{BOOKING_HOST}/api/v1/hotels/searchDestination"
params = {"query": "Doha"}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    
    if data.get("status"):
        print(f"✅ Success with 'Doha'")
        if data.get("data"):
            print(f"   Found {len(data['data'])} results")
            for item in data["data"][:3]:
                print(f"   - {item.get('name')} (dest_id: {item.get('dest_id')})")
    else:
        print(f"❌ Failed: {data.get('message', 'Unknown')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Try with different endpoint timing
print("\n" + "="*70)
print("📍 TEST 4: Retry after short delay")
import time
time.sleep(2)

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Status field: {data.get('status')}")
    print(f"Message: {data.get('message', 'N/A')}")
    
    if data.get("data"):
        print(f"Data items: {len(data.get('data', []))}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)

