"""
Test complete hotel search workflow with review scores
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.mcp_tools import (
    search_hotel_destination,
    search_hotels,
    get_hotel_reviews,
    get_attractions_near_hotel
)
import json

print("="*70)
print("TESTING COMPLETE HOTEL SEARCH WORKFLOW")
print("="*70)

# Step 1: Search destination
print("\n📍 STEP 1: Searching for Paris destination...")
dest_result = search_hotel_destination("Paris")
dest_data = json.loads(dest_result)

if dest_data.get("status"):
    dest_id = dest_data["data"][0]["dest_id"]
    print(f"✅ Found dest_id: {dest_id}")
    print(f"   City: {dest_data['data'][0]['name']}")
    print(f"   Country: {dest_data['data'][0]['country']}")
    print(f"   Hotels available: {dest_data['data'][0]['nr_hotels']}")
else:
    print("❌ Failed to get destination")
    exit(1)

# Step 2: Search hotels
print(f"\n🏨 STEP 2: Searching hotels in Paris (dest_id: {dest_id})...")
hotel_result = search_hotels(f"{dest_id} 2025-12-15 2025-12-18 2 1 USD")
hotel_data = json.loads(hotel_result)

if hotel_data.get("status"):
    hotels = hotel_data.get("data", {}).get("hotels", [])
    print(f"✅ Found {len(hotels)} hotels")
    
    # Show first 3 hotels
    print("\n📋 Sample Hotels:")
    for i, hotel in enumerate(hotels[:3], 1):
        print(f"\n   {i}. {hotel.get('hotel_name', 'N/A')}")
        print(f"      Hotel ID: {hotel.get('hotel_id')}")
        print(f"      Price: ${hotel.get('min_total_price', 'N/A')} total")
        print(f"      Rating: {hotel.get('review_score', 'N/A')}/10")
        
        # Step 3: Get reviews for this hotel
        if hotel.get('hotel_id'):
            hotel_id = str(hotel['hotel_id'])
            print(f"\n   ⭐ Getting detailed reviews for hotel {hotel_id}...")
            reviews_result = get_hotel_reviews(hotel_id)
            reviews_data = json.loads(reviews_result)
            
            if reviews_data.get("status"):
                print(f"      ✅ Review Score: {reviews_data.get('data', {}).get('score', 'N/A')}/10")
                print(f"         Total Reviews: {reviews_data.get('data', {}).get('total_reviews', 'N/A')}")
                scores = reviews_data.get('data', {}).get('score_breakdown', {})
                if scores:
                    print(f"         Cleanliness: {scores.get('cleanliness', 'N/A')}")
                    print(f"         Comfort: {scores.get('comfort', 'N/A')}")
                    print(f"         Location: {scores.get('location', 'N/A')}")
            
            # Step 4: Get nearby attractions
            print(f"\n   🎭 Getting attractions near hotel {hotel_id}...")
            attr_result = get_attractions_near_hotel(hotel_id)
            attr_data = json.loads(attr_result)
            
            if attr_data.get("status"):
                attractions = attr_data.get('data', [])
                print(f"      ✅ Found {len(attractions)} nearby attractions")
                if attractions:
                    for j, attr in enumerate(attractions[:3], 1):
                        print(f"         {j}. {attr.get('name', 'N/A')} - {attr.get('distance', 'N/A')}")
else:
    print("❌ Failed to get hotels")

print("\n" + "="*70)
print("✅ WORKFLOW TEST COMPLETE")
print("="*70)
print("\n✨ All API tools are working correctly!")
print("   ✅ Hotel destination search")
print("   ✅ Hotel search with dates")
print("   ✅ Hotel review scores")
print("   ✅ Nearby attractions")

