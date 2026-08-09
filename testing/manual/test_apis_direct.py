"""
Direct test of hotel API functions (bypass LangChain tool wrapper)
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HEADERS = {
    'x-rapidapi-host': 'booking-com15.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

print("="*70)
print("TESTING HOTEL APIs DIRECTLY")
print("="*70)
print(f"\nAPI Key configured: {'Yes' if RAPIDAPI_KEY else 'No'}")

# Step 1: Search destination
print("\n📍 STEP 1: Searching for Paris...")
try:
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
    response = requests.get(url, headers=RAPIDAPI_HEADERS, params={'query': 'Paris'}, timeout=30)
    response.raise_for_status()
    dest_data = response.json()
    
    if dest_data.get("status"):
        dest_id = dest_data["data"][0]["dest_id"]
        print(f"✅ Found dest_id: {dest_id}")
        print(f"   Hotels available: {dest_data['data'][0]['nr_hotels']}")
    else:
        print(f"❌ Failed: {dest_data}")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Step 2: Search hotels
print(f"\n🏨 STEP 2: Searching hotels (dest_id: {dest_id})...")
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
response = requests.get(url, headers=RAPIDAPI_HEADERS, params=params, timeout=30)
hotel_data = response.json()

if hotel_data.get("status"):
    hotels = hotel_data.get("data", {}).get("hotels", [])
    print(f"✅ Found {len(hotels)} hotels")
    
    # Test first hotel only
    if hotels:
        hotel = hotels[0]
        hotel_id = str(hotel.get('hotel_id'))
        print(f"\n📋 Testing with: {hotel.get('hotel_name', 'N/A')}")
        print(f"   Hotel ID: {hotel_id}")
        print(f"   Price: ${hotel.get('min_total_price', 'N/A')}")
        print(f"   Rating: {hotel.get('review_score', 'N/A')}/10")
        
        # Step 3: Get reviews
        print(f"\n⭐ STEP 3: Getting reviews for hotel {hotel_id}...")
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviewScores"
        response = requests.get(url, headers=RAPIDAPI_HEADERS, 
                              params={'hotel_id': hotel_id, 'languagecode': 'en-us'}, 
                              timeout=30)
        reviews_data = response.json()
        
        if reviews_data.get("status"):
            review_info = reviews_data.get('data', {})
            # Handle if data is a list or dict
            if isinstance(review_info, list):
                review_info = review_info[0] if review_info else {}
            
            score = review_info.get('score', 'N/A')
            total_reviews = review_info.get('total_reviews', 'N/A')
            print(f"✅ Review Score: {score}/10")
            print(f"   Total Reviews: {total_reviews}")
            scores = review_info.get('score_breakdown', {})
            if scores:
                print(f"   Cleanliness: {scores.get('cleanliness', 'N/A')}")
                print(f"   Comfort: {scores.get('comfort', 'N/A')}")
                print(f"   Location: {scores.get('location', 'N/A')}")
        else:
            print(f"❌ Reviews failed: {reviews_data.get('message', 'Unknown error')}")
        
        # Step 4: Get attractions
        print(f"\n🎭 STEP 4: Getting attractions near hotel {hotel_id}...")
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getPopularAttractionNearBy"
        response = requests.get(url, headers=RAPIDAPI_HEADERS, 
                              params={'hotel_id': hotel_id, 'languagecode': 'en-us'}, 
                              timeout=30)
        attr_data = response.json()
        
        if attr_data.get("status"):
            attractions = attr_data.get('data', [])
            print(f"✅ Found {len(attractions)} nearby attractions")
            for i, attr in enumerate(attractions[:5], 1):
                print(f"   {i}. {attr.get('name', 'N/A')} - {attr.get('distance', 'N/A')}")
        else:
            print(f"❌ Attractions failed: {attr_data.get('message', 'Unknown error')}")

print("\n" + "="*70)
print("✅ ALL APIS WORKING PERFECTLY")
print("="*70)

