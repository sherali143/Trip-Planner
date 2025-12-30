"""
Test script for MCP servers
Run this to verify your MCP servers are working correctly
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_flight_mcp():
    """Test the flight MCP server"""
    print("\n" + "="*60)
    print("Testing Flight MCP Server")
    print("="*60)
    
    from mcp_servers.trip_planner_mcp_server import search_cheap_flights
    
    try:
        result = search_cheap_flights(
            origin="NYC",
            destination="LON",
            departure_date="2025-06-16",
            return_date="2025-06-30",
            budget=1000,
            adults=1
        )
        print("\n✅ Flight MCP Server is working!")
        print("\nSample Result (truncated):")
        print(result[:500] + "...\n")
        return True
    except Exception as e:
        print(f"\n❌ Error testing Flight MCP Server: {e}")
        return False


def test_hotel_mcp():
    """Test the hotel MCP server"""
    print("\n" + "="*60)
    print("Testing Hotel MCP Server")
    print("="*60)
    
    from mcp_servers.trip_planner_mcp_server import search_hotels_comprehensive
    
    try:
        result = search_hotels_comprehensive(
            destination="London",
            checkin_date="2025-06-16",
            checkout_date="2025-06-20",
            budget_per_night=150,
            adults=1,
            rooms=1
        )
        print("\n✅ Hotel MCP Server is working!")
        print("\nSample Result (truncated):")
        print(result[:500] + "...\n")
        return True
    except Exception as e:
        print(f"\n❌ Error testing Hotel MCP Server: {e}")
        return False


def test_car_rental_mcp():
    """Test the car rental MCP functionality"""
    print("\n" + "="*60)
    print("Testing Car Rental MCP")
    print("="*60)
    
    from mcp_servers.trip_planner_mcp_server import search_car_rentals
    
    try:
        # JFK Airport coordinates
        result = search_car_rentals(
            pick_up_latitude=40.6397,
            pick_up_longitude=-73.7791,
            drop_off_latitude=40.6397,
            drop_off_longitude=-73.7791,
            pick_up_date="2025-06-16",
            drop_off_date="2025-06-20",
            pick_up_time="10:00",
            drop_off_time="10:00",
            driver_age=30,
            currency_code="USD",
            location="US"
        )
        print("\n✅ Car Rental MCP is working!")
        print("\nSample Result:")
        print(str(result)[:500] + "...\n")
        return True
    except Exception as e:
        print(f"\n❌ Error testing Car Rental MCP: {e}")
        return False


def test_web_search_mcp():
    """Test the web search MCP functionality"""
    print("\n" + "="*60)
    print("Testing Web Search MCP")
    print("="*60)
    
    from mcp_servers.trip_planner_mcp_server import search_internet
    
    try:
        result = search_internet(query="best restaurants in London")
        print("\n✅ Web Search MCP is working!")
        print("\nSample Result (truncated):")
        print(result[:500] + "...\n")
        return True
    except Exception as e:
        print(f"\n❌ Error testing Web Search MCP: {e}")
        return False


def test_calculator_mcp():
    """Test the calculator MCP functionality"""
    print("\n" + "="*60)
    print("Testing Calculator MCP")
    print("="*60)
    
    from mcp_servers.trip_planner_mcp_server import calculate
    
    try:
        result = calculate(operation="3000 * 0.40")
        print("\n✅ Calculator MCP is working!")
        print(f"\nResult: 3000 * 0.40 = {result}\n")
        return True
    except Exception as e:
        print(f"\n❌ Error testing Calculator MCP: {e}")
        return False


def check_environment():
    """Check if required environment variables are set"""
    print("\n" + "="*60)
    print("Checking Environment Configuration")
    print("="*60)
    
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key for agents",
        "RAPIDAPI_KEY": "RapidAPI key for MCP servers",
        "SERPER_API_KEY": "Serper API key for web search"
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Show first 10 chars only for security
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {masked} ({description})")
        else:
            print(f"❌ {var}: NOT SET ({description})")
            all_set = False
    
    print()
    return all_set


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MCP SERVERS TEST SUITE")
    print("="*60)
    
    # Check environment first
    env_ok = check_environment()
    
    if not env_ok:
        print("\n⚠️  Warning: Some environment variables are not set.")
        print("Please configure your .env file before running tests.")
        print("\nContinuing with tests anyway...\n")
    
    # Run tests
    results = {
        "Environment": env_ok,
        "Flight MCP": test_flight_mcp(),
        "Hotel MCP": test_hotel_mcp(),
        "Car Rental MCP": test_car_rental_mcp(),
        "Web Search MCP": test_web_search_mcp(),
        "Calculator MCP": test_calculator_mcp()
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 All tests passed! Your MCP servers are ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("- Missing or invalid API keys in .env file")
        print("- Network connectivity issues")
        print("- API rate limits exceeded")
        print("- Missing dependencies (run: pip install mcp requests)")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
