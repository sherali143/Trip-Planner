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
import subprocess
import sys
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Path to unified MCP server
MCP_SERVERS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server")
UNIFIED_SERVER_PATH = os.path.join(MCP_SERVERS_PATH, "mcp.py")


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
# PYDANTIC INPUT SCHEMAS FOR STRUCTURED TOOLS
# ============================================

class FlightSearchInput(BaseModel):
    """Input schema for flight search"""
    source: str = Field(description="Origin city name (e.g., 'Islamabad', 'London', 'New York')")
    destination: str = Field(description="Destination city name (e.g., 'Doha', 'Dubai', 'Paris')")
    departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(default=None, description="Return date in YYYY-MM-DD format (optional for one-way)")
    adults: int = Field(description="Number of adult passengers")
    cabin_class: str = Field(default="ECONOMY", description="Cabin class: ECONOMY, BUSINESS, or FIRST")


class ComprehensiveFlightInput(BaseModel):
    """Input schema for comprehensive flight search"""
    origin: str = Field(description="Origin city name (e.g., 'Islamabad', 'London')")
    destination: str = Field(description="Destination city name (e.g., 'Doha', 'Dubai')")
    departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(default=None, description="Return date in YYYY-MM-DD format")
    budget: Optional[float] = Field(default=None, description="Maximum budget in USD (total for all passengers)")
    adults: int = Field(description="Number of adult passengers")


class HotelSearchInput(BaseModel):
    """Input schema for hotel search"""
    destination: str = Field(description="Destination city name")
    checkin_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    checkout_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    budget_per_night: float = Field(description="Maximum budget per night in USD")
    adults: int = Field(description="Number of guests")
    rooms: int = Field(description="Number of rooms needed")
    star_rating: Optional[int] = Field(default=None, description="Desired star rating 1-5 (optional)")


class AccommodationSearchInput(BaseModel):
    """Input schema for accommodation search with location"""
    destination: str = Field(description="Destination city name")
    checkin_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    checkout_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    budget_per_night: float = Field(description="Maximum budget per night in USD")
    latitude: Optional[float] = Field(default=None, description="GPS latitude (optional)")
    longitude: Optional[float] = Field(default=None, description="GPS longitude (optional)")


class AttractionSearchInput(BaseModel):
    """Input schema for attraction search"""
    destination: str = Field(description="Destination city name")
    interests: str = Field(description="Comma-separated interests like 'museums, food, nightlife'")
    duration_days: int = Field(description="Number of days for the trip")


class RestaurantSearchInput(BaseModel):
    """Input schema for restaurant search"""
    destination: str = Field(description="Destination city name")
    cuisine_types: str = Field(description="Types of cuisine like 'French, Italian, local'")
    budget_per_meal: float = Field(description="Maximum budget per meal in USD")


class HotelsByDestIdInput(BaseModel):
    """Input schema for hotels by destination ID search"""
    dest_id: str = Field(description="Destination ID from search_hotel_destination")
    search_type: str = Field(default="CITY", description="Search type: CITY or REGION")
    arrival_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    departure_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    adults: int = Field(description="Number of guests")
    room_qty: int = Field(description="Number of rooms")
    currency_code: str = Field(default="USD", description="Currency code like USD, EUR")


# ============================================
# DIRECT API CALLS (Bypass MCP for large responses)
# ============================================

import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
KIWI_HOST = "kiwi-com-cheap-flights.p.rapidapi.com"
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
        response = requests.get(url, headers=headers, params=params, timeout=30)
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
    Direct call to Booking.com Flights API - returns flights on EXACT dates.
    This is more reliable than Kiwi API which returns flights across multiple dates.
    """
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    # Step 1: Get origin airport ID
    origin_result = _search_flight_destination_booking(origin_city)
    if not origin_result.get("success"):
        return json.dumps({
            "success": False,
            "error": f"Could not find airport for '{origin_city}': {origin_result.get('error')}"
        })
    
    from_id = origin_result["airport_id"]
    origin_name = origin_result.get("name", origin_city)
    
    # Step 2: Get destination airport ID
    dest_result = _search_flight_destination_booking(destination_city)
    if not dest_result.get("success"):
        return json.dumps({
            "success": False,
            "error": f"Could not find airport for '{destination_city}': {dest_result.get('error')}"
        })
    
    to_id = dest_result["airport_id"]
    dest_name = dest_result.get("name", destination_city)
    
    # Step 3: Search flights
    url = f"https://{BOOKING_HOST}/api/v1/flights/searchFlights"
    
    params = {
        "fromId": from_id,
        "toId": to_id,
        "departDate": departure_date,
        "pageNo": 1,
        "adults": adults,
        "children": "",
        "sort": "BEST",
        "cabinClass": cabin_class,
        "currency_code": "USD"
    }
    
    if return_date:
        params["returnDate"] = return_date
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("status"):
            return json.dumps({
                "success": False,
                "error": data.get("message", "API error")
            })
        
        flight_offers = data.get("data", {}).get("flightOffers", [])
        
        if not flight_offers:
            return json.dumps({
                "success": True,
                "message": f"No flights found from {origin_city} to {destination_city} on {departure_date}",
                "flights": []
            })
        
        # Format flight results
        formatted_flights = []
        formatted_flights = []
        for idx, offer in enumerate(flight_offers[:5], 1):
            # Price
            price_info = offer.get("priceBreakdown", {})
            total_price = float(price_info.get("total", {}).get("units", 0))
            currency = price_info.get("total", {}).get("currencyCode", "USD")
            price_per_person = total_price / adults if adults > 0 else total_price
            
            # Budget check
            within_budget = budget is None or total_price <= budget
            
            flight = {
                "option": idx,
                "price_per_person": round(price_per_person, 2),
                "total_price": round(total_price, 2),
                "currency": currency,
                "passengers": adults,
                "within_budget": within_budget
            }
            
            # Flight segments
            segments = offer.get("segments", [])
            
            # Outbound flight
            if segments:
                outbound_segment = segments[0]
                outbound_legs = []
                
                for leg in outbound_segment.get("legs", []):
                    carriers = leg.get("carriersData", [])
                    airline = carriers[0].get("name", "Unknown") if carriers else "Unknown"
                    carrier_code = leg.get("flightInfo", {}).get("carrierInfo", {}).get("operatingCarrier", "")
                    flight_num = leg.get("flightInfo", {}).get("flightNumber", "")
                    
                    outbound_legs.append({
                        "airline": airline,
                        "flight_code": f"{carrier_code}{flight_num}",
                        "from": leg.get("departureAirport", {}).get("code", "N/A"),
                        "to": leg.get("arrivalAirport", {}).get("code", "N/A"),
                        "departure": leg.get("departureTime", "N/A"),
                        "arrival": leg.get("arrivalTime", "N/A"),
                        "duration_mins": leg.get("durationInMinutes", 0)
                    })
                
                flight["outbound"] = outbound_legs
                flight["outbound_date"] = departure_date
            
            # Return flight (if round-trip)
            if len(segments) > 1 and return_date:
                return_segment = segments[1]
                return_legs = []
                
                for leg in return_segment.get("legs", []):
                    carriers = leg.get("carriersData", [])
                    airline = carriers[0].get("name", "Unknown") if carriers else "Unknown"
                    carrier_code = leg.get("flightInfo", {}).get("carrierInfo", {}).get("operatingCarrier", "")
                    flight_num = leg.get("flightInfo", {}).get("flightNumber", "")
                    
                    return_legs.append({
                        "airline": airline,
                        "flight_code": f"{carrier_code}{flight_num}",
                        "from": leg.get("departureAirport", {}).get("code", "N/A"),
                        "to": leg.get("arrivalAirport", {}).get("code", "N/A"),
                        "departure": leg.get("departureTime", "N/A"),
                        "arrival": leg.get("arrivalTime", "N/A"),
                        "duration_mins": leg.get("durationInMinutes", 0)
                    })
                
                flight["return"] = return_legs
                flight["return_date"] = return_date
            
            formatted_flights.append(flight)
        
        # Filter by budget if specified
        if budget:
            within_budget_flights = [f for f in formatted_flights if f["within_budget"]]
        else:
            within_budget_flights = formatted_flights
        
        result = {
            "success": True,
            "search": {
                "origin": origin_name,
                "origin_code": from_id.replace(".AIRPORT", ""),
                "destination": dest_name,
                "destination_code": to_id.replace(".AIRPORT", ""),
                "departure_date": departure_date,
                "return_date": return_date,
                "passengers": adults,
                "budget": budget
            },
            "flights_found": len(flight_offers),
            "within_budget": len(within_budget_flights) if budget else len(formatted_flights),
            "flights": formatted_flights
        }
        
        return json.dumps(result, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({"error": "API timeout", "success": False})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e), "success": False})
    except Exception as e:
        return json.dumps({"error": str(e), "success": False})


def _call_kiwi_api_direct(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "ECONOMY"
) -> str:
    """
    Direct call to Kiwi.com API - bypasses MCP for reliability with large responses
    """
    headers = {
        "x-rapidapi-host": KIWI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    # Determine one-way or round-trip
    if return_date:
        url = f"https://{KIWI_HOST}/round-trip"
        params = {
            "source": origin,
            "destination": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": 1,  # API works best with 1, we multiply price
            "adultsHoldBags": "[0]",
            "adultsHandBags": "[1]",
            "currency": "USD",
            "cabinClass": cabin_class
        }
    else:
        url = f"https://{KIWI_HOST}/one-way"
        params = {
            "source": origin,
            "destination": destination,
            "date": departure_date,
            "adults": 1,
            "adultsHoldBags": "[0]",
            "adultsHandBags": "[1]",
            "currency": "USD"
        }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "error" in data:
            return json.dumps({"error": data.get("error"), "success": False})
        
        # Parse and format results
        itineraries = data.get("itineraries", [])
        
        if not itineraries:
            return json.dumps({
                "success": True,
                "message": "No flights found for this route/date",
                "flights": []
            })
        
        # Format flight results
        formatted_flights = []
        formatted_flights = []
        for i, itin in enumerate(itineraries[:5], 1):
            price_info = itin.get("price", {})
            price_per_person = float(price_info.get("amount", 0))
            total_price = price_per_person * adults
            
            flight = {
                "option": i,
                "price_per_person": price_per_person,
                "total_price": total_price,
                "currency": "USD",
                "passengers": adults
            }
            
            # Get outbound flight details
            outbound = itin.get("outbound", {})
            if outbound:
                sectors = outbound.get("sectorSegments", [])
                outbound_legs = []
                for seg in sectors:
                    segment = seg.get("segment", {})
                    carrier = segment.get("carrier", {})
                    source = segment.get("source", {})
                    dest = segment.get("destination", {})
                    
                    outbound_legs.append({
                        "airline": carrier.get("name", "Unknown"),
                        "flight_code": f"{carrier.get('code', '')}{segment.get('code', '')}",
                        "from": source.get("station", {}).get("code", "N/A"),
                        "to": dest.get("station", {}).get("code", "N/A"),
                        "departure": source.get("localTime", "N/A")[:16] if source.get("localTime") else "N/A",
                        "arrival": dest.get("localTime", "N/A")[:16] if dest.get("localTime") else "N/A"
                    })
                flight["outbound"] = outbound_legs
            
            # Get return flight details if round-trip
            inbound = itin.get("inbound", {})
            if inbound:
                sectors = inbound.get("sectorSegments", [])
                return_legs = []
                for seg in sectors:
                    segment = seg.get("segment", {})
                    carrier = segment.get("carrier", {})
                    source = segment.get("source", {})
                    dest = segment.get("destination", {})
                    
                    return_legs.append({
                        "airline": carrier.get("name", "Unknown"),
                        "flight_code": f"{carrier.get('code', '')}{segment.get('code', '')}",
                        "from": source.get("station", {}).get("code", "N/A"),
                        "to": dest.get("station", {}).get("code", "N/A"),
                        "departure": source.get("localTime", "N/A")[:16] if source.get("localTime") else "N/A",
                        "arrival": dest.get("localTime", "N/A")[:16] if dest.get("localTime") else "N/A"
                    })
                flight["return"] = return_legs
            
            formatted_flights.append(flight)
        
        # Create summary
        result = {
            "success": True,
            "search": {
                "origin": origin,
                "destination": destination,
                "departure": departure_date,
                "return": return_date,
                "passengers": adults
            },
            "flights_found": len(itineraries),
            "showing": len(formatted_flights),
            "flights": formatted_flights
        }
        
        return json.dumps(result, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({"error": "API timeout", "success": False})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e), "success": False})
    except Exception as e:
        return json.dumps({"error": str(e), "success": False})


# ============================================
# FLIGHT SEARCH TOOLS (Structured) - Using Booking.com API
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


search_round_trip_flights = StructuredTool.from_function(
    func=_search_round_trip_flights,
    name="Search round trip flights",
    description="""Search for round-trip flights using Booking.com API.
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
    """,
    args_schema=FlightSearchInput
)


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


search_comprehensive_flights = StructuredTool.from_function(
    func=_search_comprehensive_flights,
    name="Search comprehensive flights",
    description="""Comprehensive flight search with budget filtering.
    
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
    """,
    args_schema=ComprehensiveFlightInput
)


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


search_hotels_comprehensive = StructuredTool.from_function(
    func=_search_hotels_comprehensive,
    name="Search hotels comprehensive",
    description="""Comprehensive hotel search with reviews and budget filtering.
    
    REQUIRED parameters:
    - destination: City name (e.g., 'Paris', 'Doha', 'London')
    - checkin_date: Check-in date in YYYY-MM-DD format
    - checkout_date: Check-out date in YYYY-MM-DD format
    - budget_per_night: Maximum budget per night in USD
    - adults: Number of guests
    - rooms: Number of rooms needed
    
    OPTIONAL parameters:
    - star_rating: Desired star rating 1-5
    """,
    args_schema=HotelSearchInput
)


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


search_accommodations_with_location = StructuredTool.from_function(
    func=_search_accommodations_with_location,
    name="Search accommodations with location",
    description="""Search for accommodations with optional GPS coordinates.
    
    REQUIRED parameters:
    - destination: City name
    - checkin_date: Check-in date in YYYY-MM-DD format
    - checkout_date: Check-out date in YYYY-MM-DD format
    - budget_per_night: Maximum budget per night in USD
    
    OPTIONAL parameters:
    - latitude: GPS latitude for location-based search
    - longitude: GPS longitude for location-based search
    """,
    args_schema=AccommodationSearchInput
)


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


search_attractions = StructuredTool.from_function(
    func=_search_attractions,
    name="Search for attractions",
    description="""Search for attractions and things to do at a destination.
    
    REQUIRED parameters:
    - destination: City name (e.g., 'Doha', 'Paris')
    - interests: Comma-separated interests (e.g., 'museums, food, nightlife, beaches')
    - duration_days: Number of days for the trip
    """,
    args_schema=AttractionSearchInput
)


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


search_restaurants = StructuredTool.from_function(
    func=_search_restaurants,
    name="Search for restaurants",
    description="""Search for restaurants at a destination.
    
    REQUIRED parameters:
    - destination: City name (e.g., 'Doha', 'Paris')
    - cuisine_types: Types of cuisine (e.g., 'Arabic, Middle Eastern, Seafood')
    - budget_per_meal: Maximum budget per meal in USD
    """,
    args_schema=RestaurantSearchInput
)


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


search_hotels_by_dest_id = StructuredTool.from_function(
    func=_search_hotels_by_dest_id,
    name="Search hotels by destination ID",
    description="""Search hotels using dest_id from search_hotel_destination (STEP 2).
    
    REQUIRED parameters:
    - dest_id: Destination ID from search_hotel_destination result
    - arrival_date: Check-in date in YYYY-MM-DD format
    - departure_date: Check-out date in YYYY-MM-DD format
    - adults: Number of guests
    - room_qty: Number of rooms
    
    OPTIONAL parameters:
    - search_type: CITY or REGION (default: CITY)
    - currency_code: USD, EUR, etc. (default: USD)
    """,
    args_schema=HotelsByDestIdInput
)


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
