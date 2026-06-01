"""
Test the new Booking.com Flight API integration in mcp_tools.py
"""

import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.mcp_tools import _call_booking_flights_api
import json

print("="*70)
print("🧪 TESTING BOOKING.COM FLIGHT API INTEGRATION")
print("="*70)

# Test parameters
origin = "Islamabad"
destination = "Doha"
departure_date = "2025-12-15"
return_date = "2025-12-25"
adults = 1
budget = 1050

print(f"\n📋 TEST PARAMETERS:")
print(f"   Origin: {origin}")
print(f"   Destination: {destination}")
print(f"   Departure: {departure_date}")
print(f"   Return: {return_date}")
print(f"   Adults: {adults}")
print(f"   Budget: ${budget}")

print("\n🔍 Searching flights...")
result = _call_booking_flights_api(
    origin_city=origin,
    destination_city=destination,
    departure_date=departure_date,
    return_date=return_date,
    adults=adults,
    budget=budget
)

# Parse and display results
data = json.loads(result)

if data.get("success"):
    print(f"\n✅ Search successful!")
    print(f"   Flights found: {data.get('flights_found', 0)}")
    print(f"   Within budget: {data.get('within_budget', 0)}")
    
    print(f"\n📊 FLIGHT OPTIONS:")
    for flight in data.get("flights", [])[:5]:
        print(f"\n   Option {flight['option']}:")
        print(f"   💰 ${flight['total_price']} total (${flight['price_per_person']}/person)")
        print(f"   ✅ Within budget: {flight['within_budget']}")
        
        # Outbound
        if flight.get("outbound"):
            print(f"\n   📤 OUTBOUND ({flight.get('outbound_date', 'N/A')}):")
            for leg in flight["outbound"]:
                print(f"      {leg['from']} → {leg['to']}")
                print(f"      ✈️  {leg['airline']} {leg['flight_code']}")
                print(f"      🕐 {leg['departure']} - {leg['arrival']}")
        
        # Return
        if flight.get("return"):
            print(f"\n   📥 RETURN ({flight.get('return_date', 'N/A')}):")
            for leg in flight["return"]:
                print(f"      {leg['from']} → {leg['to']}")
                print(f"      ✈️  {leg['airline']} {leg['flight_code']}")
                print(f"      🕐 {leg['departure']} - {leg['arrival']}")
else:
    print(f"\n❌ Search failed: {data.get('error', 'Unknown error')}")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
