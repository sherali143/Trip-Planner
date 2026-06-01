"""
Test the exact API calls from your curl commands
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = "d2578842a2msha6c9e88223eefdcp159694jsn7129dba33a80"

print("="*70)
print("TESTING EXACT CURL COMMANDS")
print("="*70)

# Test 1: Get attractions near hotel
print("\n🎭 TEST 1: Get attractions near hotel ID 5955189")
url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getPopularAttractionNearBy"
headers = {
    'x-rapidapi-host': 'booking-com15.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}
params = {
    'hotel_id': '5955189',
    'languagecode': 'en-us'
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:500]}...")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Get hotel review metadata
print("\n⭐ TEST 2: Get hotel review metadata for hotel ID 1377073")
url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviewsFilterMetadata"
params = {
    'hotel_id': '1377073',
    'languagecode': 'en-us'
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:500]}...")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Search destination (Paris)
print("\n📍 TEST 3: Search destination - Paris")
url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
params = {'query': 'Paris'}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    
    if data.get("status"):
        print(f"✅ Success!")
        print(f"   Destination: {data['data'][0]['name']}")
        print(f"   Dest ID: {data['data'][0]['dest_id']}")
        print(f"   Hotels: {data['data'][0]['nr_hotels']}")
        
        # Now search hotels with this dest_id
        dest_id = data['data'][0]['dest_id']
        print(f"\n🏨 TEST 4: Searching hotels in Paris (dest_id: {dest_id})")
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
        params = {
            'dest_id': dest_id,
            'search_type': 'CITY',
            'arrival_date': '2025-12-15',
            'departure_date': '2025-12-18',
            'adults': '2',
            'room_qty': '1',
            'page_number': '1',
            'units': 'metric',
            'temperature_unit': 'c',
            'languagecode': 'en-us',
            'currency_code': 'USD'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if data.get("status"):
            hotels = data.get("data", {}).get("hotels", [])
            print(f"✅ Found {len(hotels)} hotels")
            if hotels:
                hotel = hotels[0]
                print(f"\n   First Hotel: {hotel.get('hotel_name', 'N/A')}")
                print(f"   Hotel ID: {hotel.get('hotel_id')}")
                print(f"   Price: ${hotel.get('min_total_price', 'N/A')}")
                print(f"   Review Score: {hotel.get('review_score', 'N/A')}/10")
        else:
            print(f"❌ Failed: {data.get('message', 'Unknown error')}")
    else:
        print(f"❌ Failed: {data.get('message', 'Unknown error')}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*70)
print("TESTS COMPLETE")
print("="*70)
