"""
Test script to verify MCP server integration
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import os
import sys
import json
from tools.mcp_tools import (
    search_comprehensive_flights,
    search_hotels_comprehensive,
    search_accommodations_with_location,
    search_internet,
    search_attractions,
    search_restaurants,
    calculate,
    mcp_client
)

async def test_mcp_server():
    """Test the unified MCP server"""
    print("🚀 Testing Unified MCP Server Integration")
    print("=" * 50)
    
    # Test Flight Search
    print("\n1️⃣ Testing Flight Search...")
    try:
        flight_result = await mcp_client.call_tool(
            "search_cheap_flights",
            {
                "origin": "new_york",
                "destination": "paris",
                "departure_date": "2024-12-15",
                "return_date": "2024-12-22",
                "budget": 1000.0,
                "adults": 1
            }
        )
        
        if flight_result["success"]:
            print("✅ Flight Search - SUCCESS")
            print(f"   Response length: {len(str(flight_result['data']))}")
        else:
            print("❌ Flight Search - FAILED")
            print(f"   Error: {flight_result['error']}")
            
    except Exception as e:
        print("❌ Flight Search - EXCEPTION")
        print(f"   Exception: {e}")
    
    # Test Hotel Search
    print("\n2️⃣ Testing Hotel Search...")
    try:
        hotel_result = await mcp_client.call_tool(
            "search_hotels_comprehensive",
            {
                "destination": "Paris",
                "checkin_date": "2024-12-15",
                "checkout_date": "2024-12-18",
                "budget_per_night": 150.0,
                "adults": 1,
                "rooms": 1
            }
        )
        
        if hotel_result["success"]:
            print("✅ Hotel Search - SUCCESS")
            print(f"   Response length: {len(str(hotel_result['data']))}")
        else:
            print("❌ Hotel Search - FAILED")
            print(f"   Error: {hotel_result['error']}")
            
    except Exception as e:
        print("❌ Hotel Search - EXCEPTION")
        print(f"   Exception: {e}")
    
    # Test Web Search
    print("\n3️⃣ Testing Web Search...")
    try:
        search_result = await mcp_client.call_tool(
            "search_internet",
            {"query": "best restaurants in Paris"}
        )
        
        if search_result["success"]:
            print("✅ Web Search - SUCCESS")
            print(f"   Response length: {len(str(search_result['data']))}")
        else:
            print("❌ Web Search - FAILED")
            print(f"   Error: {search_result['error']}")
            
    except Exception as e:
        print("❌ Web Search - EXCEPTION")
        print(f"   Exception: {e}")
    
    # Test Calculator
    print("\n4️⃣ Testing Calculator...")
    try:
        calc_result = await mcp_client.call_tool(
            "calculate",
            {"operation": "3000 * 0.40"}
        )
        
        if calc_result["success"]:
            print("✅ Calculator - SUCCESS")
            print(f"   Result: {calc_result['data']}")
        else:
            print("❌ Calculator - FAILED")
            print(f"   Error: {calc_result['error']}")
            
    except Exception as e:
        print("❌ Calculator - EXCEPTION")
        print(f"   Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 MCP Server Integration Test Complete")
    
    print("\n" + "=" * 50)
    print("🎯 MCP Server Integration Test Complete")


def test_sync_tools():
    """Test the sync tool wrappers that agents will use"""
    print("\n3️⃣ Testing Sync Tool Wrappers...")
    
    # Test flight search tool
    print("\n   Testing search_comprehensive_flights...")
    try:
        flight_params = {
            "origin": "new_york",
            "destination": "paris",
            "departure_date": "2024-12-15",
            "return_date": "2024-12-22",
            "budget": 1000.0,
            "adults": 1
        }
        
        flight_response = search_comprehensive_flights.invoke(json.dumps(flight_params))
        
        # Check if response contains actual flight data
        if "Flight Search Results" in flight_response and "Raw Results:" in flight_response:
            print("   ✅ Flight search tool - SUCCESS")
            print(f"      Response preview: {flight_response[:300]}...")
        elif "error" in flight_response.lower():
            print("   ❌ Flight search tool - FAILED")
            print(f"      Response: {flight_response[:200]}...")
        else:
            print("   ⚠️ Flight search tool - UNEXPECTED RESPONSE")
            print(f"      Response: {flight_response[:200]}...")
            
    except Exception as e:
        print("   ❌ Flight search tool - EXCEPTION")
        print(f"      Exception: {e}")
    
    # Test hotel search tool
    print("\n   Testing search_hotels_comprehensive...")
    try:
        hotel_params = {
            "destination": "Paris",
            "checkin_date": "2024-12-15",
            "checkout_date": "2024-12-18",
            "budget_per_night": 150.0,
            "adults": 1,
            "rooms": 1
        }
        
        hotel_response = search_hotels_comprehensive.invoke(json.dumps(hotel_params))
        
        # Check if response contains hotel search data
        if "Hotel Search Results" in hotel_response:
            print("   ✅ Hotel search tool - SUCCESS")
            print(f"      Response preview: {hotel_response[:300]}...")
        elif "error" in hotel_response.lower() or "validation error" in hotel_response.lower():
            print("   ❌ Hotel search tool - FAILED") 
            print(f"      Response: {hotel_response[:400]}...")
        else:
            print("   ⚠️ Hotel search tool - UNEXPECTED RESPONSE")
            print(f"      Response: {hotel_response[:300]}...")
            
    except Exception as e:
        print("   ❌ Hotel search tool - EXCEPTION")
        print(f"      Exception: {e}")
    
    # Test accommodations with location tool
    print("\n   Testing search_accommodations_with_location...")
    try:
        location_params = {
            "destination": "Paris",
            "checkin_date": "2024-12-15",
            "checkout_date": "2024-12-18", 
            "budget_per_night": 150.0,
            "latitude": 48.8566,
            "longitude": 2.3522
        }
        
        location_response = search_accommodations_with_location.invoke(json.dumps(location_params))
        
        if "Accommodation Search with Location" in location_response:
            print("   ✅ Accommodations with location tool - SUCCESS")
            print(f"      Response preview: {location_response[:300]}...")
        elif "error" in location_response.lower():
            print("   ❌ Accommodations with location tool - FAILED")
            print(f"      Response: {location_response[:200]}...")
        else:
            print("   ⚠️ Accommodations with location tool - UNEXPECTED RESPONSE")
            print(f"      Response: {location_response[:200]}...")
            
    except Exception as e:
        print("   ❌ Accommodations with location tool - EXCEPTION")
        print(f"      Exception: {e}")
    
    print("\n🎯 Sync Tool Wrapper Test Complete")


def check_mcp_server_exists():
    """Check if MCP server file exists"""
    print("\n🔍 Checking MCP Server Files...")
    
    unified_server = "mcp_servers/trip_planner_mcp_server.py"
    
    if os.path.exists(unified_server):
        print(f"✅ {unified_server} - EXISTS")
    else:
        print(f"❌ {unified_server} - NOT FOUND")


def main():
    """Run all tests"""
    print("🧪 MCP INTEGRATION TESTING")
    print("=" * 60)
    
    # Check files exist
    check_mcp_server_exists()
    
    # Test async MCP client directly
    try:
        asyncio.run(test_mcp_server())
    except Exception as e:
        print(f"❌ Async test failed: {e}")
    
    # Test sync tool wrappers
    test_sync_tools()
    
    print("\n" + "=" * 60)
    print("✨ All tests completed!")


if __name__ == "__main__":
    main()
