"""
The twelve tools an agent can hold and choose to call.

Each one wraps a server tool and returns a short readable result rather than
the raw reply, because the raw replies run to thousands of characters.
"""

import json
import logging
from typing import Optional

from crewai.tools import tool

from trip_planner.tools.mcp_client import mcp_client, run_async_tool
from trip_planner.tools.travel_apis import _call_booking_flights_api

logger = logging.getLogger(__name__)

# ============================================
# FLIGHT SEARCH TOOLS (Structured) - Using fly-scraper API
# ============================================

def _search_round_trip_flights(
    source: str,
    destination: str,
    departure_date: str,
    adults: int,
    return_date: Optional[str] = None,
    cabin_class: str = "ECONOMY"
) -> str:
    """Internal function for round trip flight search - uses Booking.com API for exact dates"""
    try:
        logger.info(f"Searching flights: {source} -> {destination}, {departure_date} to {return_date}, {adults} adults")
        
        # Use Booking.com API (returns exact dates, multiple airlines)
        result = _call_booking_flights_api(
            origin_city=source,
            destination_city=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            cabin_class=cabin_class
        )
        return result
    except Exception as e:
        logger.error(f"Flight search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Search round trip flights")
def search_round_trip_flights(source: str, destination: str, departure_date: str, adults: int, return_date: Optional[str] = None, cabin_class: str = "ECONOMY") -> str:
    """Search for round-trip flights using Booking.com API.
    Returns flights on EXACT dates with multiple airlines.

    REQUIRED parameters:
    - source: Origin city name (e.g., 'Islamabad', 'London', 'New York')
    - destination: Destination city name (e.g., 'Doha', 'Dubai', 'Paris')
    - departure_date: Date in YYYY-MM-DD format (flights will be on THIS date)
    - adults: Number of passengers

    OPTIONAL parameters:
    - return_date: Return date in YYYY-MM-DD format
    - cabin_class: ECONOMY, BUSINESS, or FIRST (default: ECONOMY)

    NOTE: Use CITY NAMES, not airport codes! The API will find the correct airport.
    """
    return _search_round_trip_flights(source, destination, departure_date, adults, return_date, cabin_class)


@tool("Search comprehensive flights")
def search_comprehensive_flights(origin: str, destination: str, departure_date: str, adults: int, return_date: Optional[str] = None, budget: Optional[float] = None) -> str:
    """Comprehensive flight search with budget filtering.

    REQUIRED parameters:
    - origin: Origin airport IATA code (e.g., 'ISB' for Islamabad, 'LHR' for London)
    - destination: Destination airport IATA code (e.g., 'DOH' for Doha, 'DXB' for Dubai)
    - departure_date: Date in YYYY-MM-DD format
    - adults: Number of passengers

    OPTIONAL parameters:
    - return_date: Return date in YYYY-MM-DD format
    - budget: Maximum budget in USD (total for all passengers)

    IMPORTANT: Use 3-letter IATA airport codes, NOT city names!
    Common codes: ISB=Islamabad, LHE=Lahore, KHI=Karachi, DOH=Doha, DXB=Dubai, LHR=London, JFK=New York, CDG=Paris
    """
    return _search_comprehensive_flights(origin, destination, departure_date, adults, return_date, budget)


def _search_comprehensive_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int,
    return_date: Optional[str] = None,
    budget: Optional[float] = None
) -> str:
    """Internal function for comprehensive flight search - uses Booking.com API"""
    try:
        logger.info(f"Comprehensive flight search: {origin} -> {destination}, budget: ${budget}")
        
        # Use Booking.com API for exact dates and multiple airlines
        result = _call_booking_flights_api(
            origin_city=origin,
            destination_city=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            budget=budget
        )
        
        return result
    except Exception as e:
        logger.error(f"Comprehensive flight search error: {e}")
        return json.dumps({"error": str(e), "success": False})



# ============================================
# HOTEL SEARCH TOOLS (Structured)
# ============================================

def _search_hotels_comprehensive(
    destination: str,
    checkin_date: str,
    checkout_date: str,
    budget_per_night: float,
    adults: int,
    rooms: int,
    star_rating: Optional[int] = None
) -> str:
    """Internal function for comprehensive hotel search"""
    try:
        arguments = {
            "destination": destination,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "budget_per_night": budget_per_night,
            "adults": adults,
            "rooms": rooms
        }
        
        if star_rating is not None:
            arguments["star_rating"] = star_rating
        
        result = run_async_tool(mcp_client.call_tool("search_hotels_comprehensive", arguments))
        
        if result["success"]:
            logger.info(f"Found hotels for {destination}")
            return result["data"]
        else:
            logger.error(f"Hotel search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Hotel search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Search hotels comprehensive")
def search_hotels_comprehensive(destination: str, checkin_date: str, checkout_date: str, budget_per_night: float, adults: int, rooms: int, star_rating: Optional[int] = None) -> str:
    """Comprehensive hotel search with reviews and budget filtering.

    REQUIRED parameters:
    - destination: City name (e.g., 'Paris', 'Doha', 'London')
    - checkin_date: Check-in date in YYYY-MM-DD format
    - checkout_date: Check-out date in YYYY-MM-DD format
    - budget_per_night: Maximum budget per night in USD
    - adults: Number of guests
    - rooms: Number of rooms needed

    OPTIONAL parameters:
    - star_rating: Desired star rating 1-5
    """
    return _search_hotels_comprehensive(destination, checkin_date, checkout_date, budget_per_night, adults, rooms, star_rating)


def _search_accommodations_with_location(
    destination: str,
    checkin_date: str,
    
    checkout_date: str,
    budget_per_night: float,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """Internal function for accommodation search with location"""
    try:
        arguments = {
            "destination": destination,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "budget_per_night": budget_per_night,
            "latitude": latitude,
            "longitude": longitude
        }
        
        result = run_async_tool(mcp_client.call_tool("search_accommodations_with_location", arguments))
        
        if result["success"]:
            logger.info(f"Found accommodations for {destination}")
            return result["data"]
        else:
            logger.error(f"Accommodation search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Accommodation search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Search accommodations with location")
def search_accommodations_with_location(destination: str, checkin_date: str, checkout_date: str, budget_per_night: float, latitude: Optional[float] = None, longitude: Optional[float] = None) -> str:
    """Search for accommodations with optional GPS coordinates.

    REQUIRED parameters:
    - destination: City name
    - checkin_date: Check-in date in YYYY-MM-DD format
    - checkout_date: Check-out date in YYYY-MM-DD format
    - budget_per_night: Maximum budget per night in USD

    OPTIONAL parameters:
    - latitude: GPS latitude for location-based search
    - longitude: GPS longitude for location-based search
    """
    return _search_accommodations_with_location(destination, checkin_date, checkout_date, budget_per_night, latitude, longitude)


# ============================================
# WEB SEARCH TOOLS (Simple string input)
# ============================================

@tool("Search the internet")
def search_internet(query: str) -> str:
    """
    Search the internet about a given topic using Serper API.
    
    Args:
        query: Search query string (e.g., "best restaurants in Paris")
        
    Returns:
        Search results from the web
    """
    try:
        arguments = {"query": query}
        
        result = run_async_tool(mcp_client.call_tool("search_internet", arguments))
        
        if result["success"]:
            logger.info(f"Web search completed for: {query}")
            # Truncate to save tokens (limit to 3000 chars)
            data = result["data"]
            if len(data) > 3000:
                data = data[:3000] + "... (truncated)"
            return data
        else:
            logger.error(f"Web search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return json.dumps({"error": str(e), "success": False})


def _search_attractions(
    destination: str,
    interests: str,
    duration_days: int
) -> str:
    """Internal function for attraction search"""
    try:
        arguments = {
            "destination": destination,
            "interests": interests,
            "duration_days": duration_days
        }
        
        result = run_async_tool(mcp_client.call_tool("search_attractions", arguments))
        
        if result["success"]:
            logger.info(f"Found attractions for {destination}")
            return result["data"]
        else:
            logger.error(f"Attraction search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Attraction search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Search for attractions")
def search_attractions(destination: str, interests: str, duration_days: int) -> str:
    """Search for attractions and things to do at a destination.

    REQUIRED parameters:
    - destination: City name (e.g., 'Doha', 'Paris')
    - interests: Comma-separated interests (e.g., 'museums, food, nightlife, beaches')
    - duration_days: Number of days for the trip
    """
    return _search_attractions(destination, interests, duration_days)


def _search_restaurants(
    destination: str,
    cuisine_types: str,
    budget_per_meal: float
) -> str:
    """Internal function for restaurant search"""
    try:
        arguments = {
            "destination": destination,
            "cuisine_types": cuisine_types,
            "budget_per_meal": budget_per_meal
        }
        
        result = run_async_tool(mcp_client.call_tool("search_restaurants", arguments))
        
        if result["success"]:
            logger.info(f"Found restaurants for {destination}")
            return result["data"]
        else:
            logger.error(f"Restaurant search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Restaurant search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Search for restaurants")
def search_restaurants(destination: str, cuisine_types: str, budget_per_meal: float) -> str:
    """Search for restaurants at a destination.

    REQUIRED parameters:
    - destination: City name (e.g., 'Doha', 'Paris')
    - cuisine_types: Types of cuisine (e.g., 'Arabic, Middle Eastern, Seafood')
    - budget_per_meal: Maximum budget per meal in USD
    """
    return _search_restaurants(destination, cuisine_types, budget_per_meal)


# ============================================
# CALCULATOR TOOL (Simple string input)
# ============================================

@tool("Make a calculation")
def calculate(operation: str) -> str:
    """
    Perform mathematical calculations.
    Useful for budget calculations, currency conversions, etc.
    
    Args:
        operation: Mathematical expression to evaluate (e.g., "200*7" or "5000/2*10")
        
    Returns:
        Result of the calculation
    """
    try:
        arguments = {"operation": operation}
        
        result = run_async_tool(mcp_client.call_tool("calculate", arguments))
        
        if result["success"]:
            logger.info(f"Calculation completed: {operation} = {result['data']}")
            return result["data"]
        else:
            logger.error(f"Calculation failed: {result['error']}")
            return f"Error: {result['error']}"
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        return f"Error: {str(e)}"


# ============================================
# ADDITIONAL HOTEL TOOLS (Simple string input)
# ============================================

@tool("Search hotel destination ID")
def search_hotel_destination(query: str) -> str:
    """
    Search for a destination to get its dest_id for hotel searches.
    This is STEP 1 - use this FIRST before searching hotels by dest_id.
    
    Args:
        query: Destination city name (e.g., "Paris", "London", "Doha")
        
    Returns:
        Destination data with dest_id needed for detailed hotel search
    """
    try:
        arguments = {"query": query}
        
        result = run_async_tool(mcp_client.call_tool("search_hotel_destination", arguments))
        
        if result["success"]:
            logger.info(f"Found destination ID for: {query}")
            return result["data"]
        else:
            logger.error(f"Destination search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Destination search error: {e}")
        return json.dumps({"error": str(e), "success": False})


def _search_hotels_by_dest_id(
    dest_id: str,
    arrival_date: str,
    departure_date: str,
    adults: int,
    room_qty: int,
    search_type: str = "CITY",
    currency_code: str = "USD"
) -> str:
    """Internal function for hotels by destination ID search"""
    try:
        arguments = {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": arrival_date,
            "departure_date": departure_date,
            "adults": adults,
            "room_qty": room_qty,
            "currency_code": currency_code
        }
        
        result = run_async_tool(mcp_client.call_tool("search_hotels_by_destination", arguments))
        
        if result["success"]:
            logger.info(f"Found hotels for dest_id: {dest_id}")
            return result["data"]
        else:
            logger.error(f"Hotel search failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Hotel search error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Search hotels by destination ID")
def search_hotels_by_dest_id(dest_id: str, arrival_date: str, departure_date: str, adults: int, room_qty: int, search_type: str = "CITY", currency_code: str = "USD") -> str:
    """Search hotels using dest_id from search_hotel_destination (STEP 2).

    REQUIRED parameters:
    - dest_id: Destination ID from search_hotel_destination result
    - arrival_date: Check-in date in YYYY-MM-DD format
    - departure_date: Check-out date in YYYY-MM-DD format
    - adults: Number of guests
    - room_qty: Number of rooms

    OPTIONAL parameters:
    - search_type: CITY or REGION (default: CITY)
    - currency_code: USD, EUR, etc. (default: USD)
    """
    return _search_hotels_by_dest_id(dest_id, arrival_date, departure_date, adults, room_qty, search_type, currency_code)


@tool("Get hotel reviews by ID")
def get_hotel_reviews(hotel_id: str) -> str:
    """
    Get hotel review scores using hotel_id from hotel search results.
    
    Args:
        hotel_id: Hotel ID from searchHotels API results (will be converted to string)
        
    Returns:
        Hotel review scores and ratings breakdown
    """
    try:
        # Ensure hotel_id is a string (agent might pass int)
        hotel_id = str(hotel_id)
        arguments = {"hotel_id": hotel_id}
        
        result = run_async_tool(mcp_client.call_tool("get_hotel_reviews", arguments))
        
        if result["success"]:
            logger.info(f"Got reviews for hotel_id: {hotel_id}")
            return result["data"]
        else:
            logger.error(f"Get reviews failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Get reviews error: {e}")
        return json.dumps({"error": str(e), "success": False})


@tool("Get attractions near hotel")
def get_attractions_near_hotel(hotel_id: str) -> str:
    """
    Get popular attractions near a hotel using hotel_id.
    
    Args:
        hotel_id: Hotel ID from searchHotels API results (will be converted to string)
        
    Returns:
        Nearby attractions and points of interest
    """
    try:
        # Ensure hotel_id is a string (agent might pass int)
        hotel_id = str(hotel_id)
        arguments = {"hotel_id": hotel_id}
        
        result = run_async_tool(mcp_client.call_tool("get_attractions_near_hotel", arguments))
        
        if result["success"]:
            logger.info(f"Got attractions for hotel_id: {hotel_id}")
            return result["data"]
        else:
            logger.error(f"Get attractions failed: {result['error']}")
            return json.dumps({"error": result["error"], "success": False})
    except Exception as e:
        logger.error(f"Get attractions error: {e}")
        return json.dumps({"error": str(e), "success": False})


# Export all tools for agent use
__all__ = [
    # Flight tools
    "search_round_trip_flights",
    "search_comprehensive_flights",
    # Hotel tools
    "search_hotels_comprehensive",
    "search_accommodations_with_location",
    "search_hotel_destination",
    "search_hotels_by_dest_id",
    "get_hotel_reviews",
    "get_attractions_near_hotel",
    # Web search tools
    "search_internet",
    "search_attractions",
    "search_restaurants",
    # Calculator tool
    "calculate"
]
