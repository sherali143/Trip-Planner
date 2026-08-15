"""
MCP-Based API Integration Tools for Trip Planning

This module provides MCP server integration through a unified server:
- Flight searches (Kiwi.com, Fly-Scraper)
- Hotel searches (Booking.com)
- Web search (Serper API)
- Calculator (Math operations)

All tools communicate with the unified trip_planner_mcp_server.py via JSON-RPC over stdio.
"""

import json
import asyncio
import sys
import os
from typing import Optional
from crewai.tools import tool
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Path to unified MCP server
MCP_SERVERS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server")
UNIFIED_SERVER_PATH = os.path.join(MCP_SERVERS_PATH, "mcp_server.py")


class MCPClient:
    """Client for communicating with MCP servers via stdio"""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on an MCP server"""
        try:
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                sys.executable, self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024  # 1MB limit for large responses
            )
            
            # MCP initialization request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "trip-planner-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Send initialization
            init_message = json.dumps(init_request) + "\n"
            process.stdin.write(init_message.encode())  # type: ignore
            await process.stdin.drain()  # type: ignore
            
            # Read initialization response with larger buffer
            init_response = await asyncio.wait_for(
                process.stdout.readline(),  # type: ignore
                timeout=60
            )
            if init_response:
                init_data = json.loads(init_response.decode().strip())
                logger.info(f"MCP Server initialized: {init_data}")
            
            # Send tool call request
            tool_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            tool_message = json.dumps(tool_request) + "\n"
            process.stdin.write(tool_message.encode())  # type: ignore
            await process.stdin.drain()  # type: ignore
            
            # Read tool response - use read() with timeout for large responses
            try:
                # Read all available output
                tool_response = await asyncio.wait_for(
                    process.stdout.readline(),  # type: ignore
                    timeout=60
                )
            except asyncio.TimeoutError:
                logger.error("MCP server response timeout")
                return {"success": False, "error": "Response timeout"}
            
            # Close the process
            process.stdin.close()  # type: ignore
            await process.wait()
            
            if tool_response:
                response_data = json.loads(tool_response.decode().strip())
                if "result" in response_data and "content" in response_data["result"]:
                    # Extract the actual content from MCP response
                    content = response_data["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        return {"success": True, "data": content[0]["text"]}
                    else:
                        return {"success": True, "data": str(content)}
                else:
                    return {"success": False, "error": "Invalid MCP response format", "raw": response_data}
            else:
                return {"success": False, "error": "No response from MCP server"}
                
        except Exception as e:
            logger.error(f"MCP client error: {e}")
            return {"success": False, "error": str(e)}


# Initialize unified MCP client
mcp_client = MCPClient(UNIFIED_SERVER_PATH)


def run_async_tool(coro):
    """Helper to run async MCP calls from sync tools"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, we need to run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except Exception:
        # Fallback: create new event loop
        return asyncio.run(coro)





# ============================================
# DIRECT API CALLS (Bypass MCP for large responses)
# ============================================

import time

from src.core.http_cache import cached_get

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# fly-scraper search is asynchronous; see _call_fly_scraper_api for the flow.
_FLY_SCRAPER_BASE = "https://fly-scraper.p.rapidapi.com"
_FLY_SCRAPER_MAX_POLLS = 3
_FLY_SCRAPER_POLL_DELAY_S = 2.0
BOOKING_HOST = "booking-com15.p.rapidapi.com"


def _search_flight_destination_booking(query: str) -> dict:
    """
    Search for airport/city ID using Booking.com Flights API.
    """
    url = f"https://{BOOKING_HOST}/api/v1/flights/searchDestination"
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    params = {"query": query}
    
    try:
        response = cached_get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") and data.get("data"):
            # Find airport ID (prefer airport over city)
            for item in data["data"]:
                if "AIRPORT" in item.get("id", ""):
                    return {
                        "success": True,
                        "airport_id": item["id"],
                        "name": item.get("name"),
                        "code": item.get("code"),
                        "city": item.get("cityName")
                    }
            # If no airport, use first result
            first = data["data"][0]
            return {
                "success": True,
                "airport_id": first["id"],
                "name": first.get("name"),
                "code": first.get("code"),
                "city": first.get("cityName")
            }
        return {"success": False, "error": "No results found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


CITY_TO_SKYID = {
    "islamabad": "ISB", "karachi": "KHI", "lahore": "LHE",
    "london": "LOND", "manchester": "MAN", "birmingham": "BHX",
    "new york": "NYCA", "los angeles": "LAXA", "chicago": "CHIA",
    "san francisco": "SFOA", "miami": "MIAA", "boston": "BOSA",
    "washington": "WASA", "seattle": "SEAA", "dallas": "DFWA",
    "paris": "PARI", "nice": "NCE", "lyon": "LYS",
    "dubai": "DXB", "abu dhabi": "AUH", "doha": "DOH",
    "tokyo": "TYOA", "osaka": "OSAA", "kyoto": "UKY",
    "bangkok": "BKK", "phuket": "HKT", "singapore": "SIN",
    "kuala lumpur": "KUL", "bali": "DPS", "jakarta": "CGK",
    "istanbul": "IST", "ankara": "ESB", "antalya": "AYT",
    "barcelona": "BCN", "madrid": "MAD", "rome": "ROMA",
    "milan": "MILA", "venice": "VCE", "florence": "FLR",
    "amsterdam": "AMS", "brussels": "BRU", "vienna": "VIE",
    "zurich": "ZRH", "geneva": "GVA", "munich": "MUC",
    "frankfurt": "FRA", "berlin": "BER", "hamburg": "HAM",
    "sydney": "SYD", "melbourne": "MEL", "auckland": "AKL",
    "hong kong": "HKG", "seoul": "SEL", "beijing": "BJS",
    "shanghai": "SHA", "mumbai": "BOM", "delhi": "DEL",
    "cairo": "CAI", "casablanca": "CMN", "cape town": "CPT",
    "rio de janeiro": "RIO", "sao paulo": "SAO", "buenos aires": "BUE",
    "stockholm": "ARN", "oslo": "OSL", "copenhagen": "CPH",
    "helsinki": "HEL", "reykjavik": "KEF", "dublin": "DUB",
}


def _resolve_sky_id(location: str) -> str:
    """Resolve a city name to a SkyID code for the fly-scraper API."""
    loc = location.strip().lower()
    if not loc:
        return location
    # If already a short uppercase code like "ISB" or "LOND", pass through
    if len(loc) <= 4 and loc.isalpha() and location.isupper():
        return location
    # Check direct match
    if loc in CITY_TO_SKYID:
        return CITY_TO_SKYID[loc]
    # Check partial match (e.g. "new york city" → "NYCA")
    for key, code in CITY_TO_SKYID.items():
        if key in loc or loc in key:
            return code
    # Fallback: try Booking.com API resolution
    try:
        result = _search_flight_destination_booking(location)
        if result.get("success") and result.get("code"):
            return result["code"]
    except Exception:
        pass
    # Last resort: use the input as-is (API will error, but we tried)
    return location


def _parse_price(price: dict) -> float:
    """
    Convert a fly-scraper price object to whole USD.

    The API reports price.raw as a STRING in thousandths
    (price.unit == "PRICE_UNIT_MILLI"), so "1074000" means $1,074. Reading raw
    directly — as the previous parser did — inflated every fare by 1000x.
    """
    raw = price.get("raw", 0)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if price.get("unit") == "PRICE_UNIT_MILLI":
        value /= 1000.0
    return round(value, 2)


def _leg_airline(leg: dict) -> str:
    """Marketing carrier name for a leg."""
    marketing = ((leg.get("carriers") or {}).get("marketing") or [{}])
    return (marketing[0] or {}).get("name", "") if marketing else ""


def _parse_leg(leg: dict) -> dict:
    """
    Flatten one leg of a fly-scraper itinerary.

    Segment fields differ from the shape the old parser expected: airports live
    under leg.origin/destination as `iata` (not segment.origin.code), times are
    `departure`/`arrival` on the leg, and the carrier name is on
    carriers.marketing[0]. Reading the old paths yielded empty strings for every
    airline, airport and time.
    """
    if not leg:
        return {}
    origin = leg.get("origin") or {}
    destination = leg.get("destination") or {}
    return {
        "airline": _leg_airline(leg),
        "from": origin.get("iata", ""),
        "from_name": origin.get("name", ""),
        "to": destination.get("iata", ""),
        "to_name": destination.get("name", ""),
        "departure": leg.get("departure", ""),
        "arrival": leg.get("arrival", ""),
        "duration_mins": leg.get("durationInMinutes", 0),
        "stops": leg.get("stopCount", 0),
    }


def _call_fly_scraper_api(
    origin_code: str,
    dest_code: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    budget: Optional[float] = None
) -> str:
    """Search flights via fly-scraper API with automatic city-to-SkyID resolution"""
    origin_sky = _resolve_sky_id(origin_code)
    dest_sky = _resolve_sky_id(dest_code)
    
    if origin_sky != origin_code or dest_sky != dest_code:
        print(f"  Resolved {origin_code} → {origin_sky}, {dest_code} → {dest_sky}")
    
    fly_headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "fly-scraper.p.rapidapi.com"
    }
    # Date parameters are camelCase, matching originSkyId/destinationSkyId.
    # The snake_case forms ("outbound_date", "departure_date") are silently
    # IGNORED rather than rejected: the API accepts the request, returns 200,
    # and searches a default date roughly a week out. That is why every result
    # previously carried the wrong outbound date while looking successful.
    params = {
        "originSkyId": origin_sky,
        "destinationSkyId": dest_sky,
        "departureDate": departure_date,
        "adults": adults,
        "currency": "USD",
        "cabinClass": "economy",
        "sortBy": "best"
    }
    if return_date:
        params["returnDate"] = return_date

    # fly-scraper is a two-phase (Skyscanner-style) API: the search endpoint only
    # STARTS the search and returns a sessionId with context.status == "incomplete"
    # and an empty itineraries list. Results must then be collected from the
    # search-incomplete endpoint using that sessionId.
    #
    # The previous implementation read the first response as final, so it returned
    # zero flights on every single search. That failure was masked for months
    # because the exhausted free-tier key returned 429 before this code was reached.
    #
    # Note the v2 path and the plural "/flights/" segment: the RapidAPI console
    # lists these as "flight/..." but only the plural form resolves.
    r = cached_get(
        f"{_FLY_SCRAPER_BASE}/v2/flights/search-roundtrip",
        params=params, headers=fly_headers, timeout=60
    )
    r.raise_for_status()
    data = r.json()

    if not data.get("status"):
        return json.dumps({"success": False, "error": data.get("message", "API error")})

    payload = data.get("data") or {}
    context = payload.get("context") or {}
    itineraries = payload.get("itineraries") or []

    session_id = context.get("sessionId")
    attempts = 0
    while (
        not itineraries
        and context.get("status") == "incomplete"
        and session_id
        and attempts < _FLY_SCRAPER_MAX_POLLS
    ):
        attempts += 1
        if attempts > 1:
            time.sleep(_FLY_SCRAPER_POLL_DELAY_S)
        poll = cached_get(
            f"{_FLY_SCRAPER_BASE}/v2/flights/search-incomplete",
            params={"sessionId": session_id}, headers=fly_headers, timeout=90
        )
        poll.raise_for_status()
        poll_payload = (poll.json() or {}).get("data") or {}
        context = poll_payload.get("context") or {}
        itineraries = poll_payload.get("itineraries") or []
        print(f"  Flight search poll {attempts}: status={context.get('status')}, "
              f"results={len(itineraries)}")

    if not itineraries:
        return json.dumps({"success": True, "flights": []})

    formatted = []
    for i, it in enumerate(itineraries[:5], 1):
        price = it.get("price") or {}
        price_usd = _parse_price(price)
        legs = it.get("legs") or []
        outbound = legs[0] if legs else {}

        flight = {
            "option": i,
            "total_price": price_usd,
            "price_formatted": price.get("formatted", ""),
            "currency": "USD",
            "passengers": adults,
            "within_budget": budget is None or price_usd <= budget,
            "outbound": _parse_leg(outbound),
            "airline": _leg_airline(outbound),
            "duration_mins": outbound.get("durationInMinutes", 0),
            "stops": outbound.get("stopCount", 0),
        }
        if len(legs) > 1:
            flight["inbound"] = _parse_leg(legs[1])
            flight["return_airline"] = _leg_airline(legs[1])
        formatted.append(flight)
    
    result = {
        "success": True,
        "flights": formatted,
        "total_found": len(itineraries)
    }
    return json.dumps(result)


def _call_booking_flights_api(
    origin_city: str,
    destination_city: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    budget: Optional[float] = None,
    cabin_class: str = "ECONOMY"
) -> str:
    """
    Search flights via fly-scraper API.
    Uses local city-to-SkyID map first, falls back to Booking.com API.
    """
    # Try local resolution first
    origin_code = _resolve_sky_id(origin_city)
    if origin_code == origin_city:
        origin_result = _search_flight_destination_booking(origin_city)
        if not origin_result.get("success"):
            return json.dumps({"success": False, "error": f"Could not find airport for '{origin_city}'"})
        origin_code = origin_result.get("code", "")

    dest_code = _resolve_sky_id(destination_city)
    if dest_code == destination_city:
        dest_result = _search_flight_destination_booking(destination_city)
        if not dest_result.get("success"):
            return json.dumps({"success": False, "error": f"Could not find airport for '{destination_city}'"})
        dest_code = dest_result.get("code", "")

    try:
        return _call_fly_scraper_api(origin_code, dest_code, departure_date, return_date, adults, budget)
    except Exception as e:
        # Must report the failure honestly. This previously returned
        # {"success": True, "flights": []}, which made a quota 429 look like a
        # successful search with no results: the 6-agent arm's LLM would then
        # invent flights while the 3-agent arm (calling _call_fly_scraper_api
        # directly) recorded a real error — making the two arms' success rates
        # non-comparable.
        logger.error(f"Flight search failed for {origin_code}->{dest_code}: {e}")
        return json.dumps({"success": False, "flights": [], "error": str(e)})


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
