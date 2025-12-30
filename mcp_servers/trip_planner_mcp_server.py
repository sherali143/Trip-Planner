"""
Unified MCP Server for Trip Planning
Integrates all APIs as MCP tools:
- Flights (Kiwi.com, Fly-Scraper)
- Hotels/Accommodations (Booking.com)
- Car Rentals (Booking.com)
- Web Search (Serper API)
- Calculator (Math operations)
"""
import os
import json
import asyncio
from typing import Any, Optional
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
FLY_SCRAPER_HOST = "fly-scraper.p.rapidapi.com"
KIWI_HOST = "kiwi-com-cheap-flights.p.rapidapi.com"
BOOKING_HOST = "booking-com15.p.rapidapi.com"


# ============================================
# FLIGHT SEARCH FUNCTIONS
# ============================================

def search_flights_kiwi(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    currency: str = "USD",
    cabin_class: str = "ECONOMY",
    limit: int = 20
) -> dict:
    """
    Search for flights using Kiwi.com API
    
    Args:
        origin: Origin city/airport code (IATA code like ISB, DOH, LHR)
        destination: Destination city/airport code (IATA code)
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Return date for round trips (YYYY-MM-DD)
        adults: Number of adult passengers (used for price calculation)
        currency: Currency code (default: USD)
        cabin_class: Cabin class (ECONOMY, BUSINESS, FIRST)
        limit: Maximum number of results
    
    Returns:
        Flight search results from Kiwi.com
    """
    # Use round-trip or one-way based on return_date
    if return_date:
        url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"
        params = {
            "source": origin,
            "destination": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": 1,  # API only works with 1 adult
            "adultsHoldBags": "[0]",
            "adultsHandBags": "[1]",
            "currency": currency.upper(),
            "cabinClass": cabin_class
        }
    else:
        url = "https://kiwi-com-cheap-flights.p.rapidapi.com/one-way"
        params = {
            "source": origin,
            "destination": destination,
            "date": departure_date,
            "adults": 1,  # API only works with 1 adult
            "adultsHoldBags": "[0]",
            "adultsHandBags": "[1]",
            "currency": currency.upper()
        }
    
    headers = {
        "x-rapidapi-host": KIWI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()
        # Store actual adults count for price calculation
        result["_requested_adults"] = adults
        return result
    except Exception as e:
        return {"error": str(e), "message": "Failed to search flights with Kiwi.com"}


def search_cheap_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    budget: Optional[float] = None,
    adults: int = 1
) -> str:
    """
    Unified flight search for best results
    
    Args:
        origin: Origin city/airport (IATA code like ISB, LHR, JFK)
        destination: Destination city/airport (IATA code)
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Return date (optional, YYYY-MM-DD)
        budget: Maximum budget in USD (total for all passengers)
        adults: Number of passengers
    
    Returns:
        Formatted flight search results with prices adjusted for number of passengers
    """
    num_adults = adults if adults else 1
    
    # Search with Kiwi.com (uses 1 adult internally)
    kiwi_results = search_flights_kiwi(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=num_adults
    )
    
    # Format results for agent consumption
    formatted_output = f"""
✈️ Flight Search Results
=========================
📍 Origin: {origin}
📍 Destination: {destination}
📅 Departure: {departure_date}
📅 Return: {return_date or 'One-way'}
👥 Passengers: {num_adults}
💰 Budget: ${budget} USD (total)
"""
    
    # Check for errors
    if "error" in kiwi_results:
        formatted_output += f"\n❌ API Error: {kiwi_results.get('error', 'Unknown error')}\n"
        return formatted_output
    
    # Parse itineraries from Kiwi response
    itineraries = kiwi_results.get("itineraries", [])
    
    if not itineraries:
        formatted_output += "\n❌ No flights found for this route/date.\n"
        formatted_output += "Try different dates or check the airport codes.\n"
        return formatted_output
    
    formatted_output += f"\n✅ Found {len(itineraries)} flight options!\n"
    formatted_output += "=" * 50 + "\n"
    
    for idx, itin in enumerate(itineraries[:10], 1):
        price_info = itin.get("price", {})
        price_per_person = price_info.get("amount", 0)
        currency = price_info.get("currency", "USD")
        
        # Ensure price is a number
        try:
            price_per_person = float(price_per_person) if price_per_person else 0
        except (ValueError, TypeError):
            price_per_person = 0
        
        # Calculate total price for all passengers
        total_price = price_per_person * num_adults
        
        # Check budget
        within_budget = "✅" if (budget is None or total_price <= budget) else "❌ Over budget"
        
        formatted_output += f"""
--- Flight Option {idx} ---
💰 Price per person: {price_per_person} {currency}
💰 Total ({num_adults} passengers): {total_price} {currency} {within_budget}
"""
        
        # Get flight details from outbound/inbound (Kiwi API structure)
        outbound = itin.get("outbound", {})
        inbound = itin.get("inbound", {})
        
        for direction, leg in [("Outbound", outbound), ("Return", inbound)]:
            if leg:
                formatted_output += f"\n  📍 {direction} Flight:\n"
                
                # Structure: sectorSegments -> segment -> source/destination/carrier
                sector_segments = leg.get("sectorSegments", [])
                
                for sector_seg in sector_segments:
                    seg = sector_seg.get("segment", {})
                    
                    source = seg.get("source", {})
                    dest = seg.get("destination", {})
                    carrier = seg.get("carrier", {})
                    
                    dep_station = source.get("station", {}).get("code", "N/A")
                    arr_station = dest.get("station", {}).get("code", "N/A")
                    dep_time = source.get("localTime", "N/A")
                    arr_time = dest.get("localTime", "N/A")
                    airline = carrier.get("name", "Unknown Airline")
                    flight_code = f"{carrier.get('code', '')}{seg.get('code', '')}"
                    
                    formatted_output += f"     {dep_station} → {arr_station}\n"
                    formatted_output += f"     ✈️ {airline} ({flight_code})\n"
                    formatted_output += f"     🕐 {dep_time[:16] if dep_time != 'N/A' else 'N/A'} - {arr_time[:16] if arr_time != 'N/A' else 'N/A'}\n"
        
        formatted_output += "\n" + "-" * 40 + "\n"
    
    # Summary
    if budget:
        def get_price(i):
            try:
                return float(i.get("price", {}).get("amount", 0)) * num_adults
            except:
                return float('inf')
        affordable = [i for i in itineraries if get_price(i) <= budget]
        formatted_output += f"\n📊 SUMMARY: {len(affordable)} flights within ${budget} budget for {num_adults} passengers\n"
    
    return formatted_output


# ============================================
# BOOKING.COM FLIGHTS API (MORE RELIABLE)
# ============================================

def search_flight_destination(query: str) -> dict:
    """
    Search for airport/city ID for flight searches.
    This is STEP 1 of Booking.com flight search.
    
    Args:
        query: City or airport name (e.g., "Islamabad", "Doha", "London")
    
    Returns:
        Airport/city ID for use in searchFlights API
    """
    url = f"https://{BOOKING_HOST}/api/v1/flights/searchDestination"
    
    params = {"query": query}
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") and data.get("data"):
            # Find airport ID
            for item in data["data"]:
                if "AIRPORT" in item.get("id", ""):
                    return {
                        "success": True,
                        "airport_id": item["id"],
                        "name": item.get("name"),
                        "code": item.get("code"),
                        "city": item.get("cityName"),
                        "country": item.get("countryName")
                    }
            # If no airport found, return first result
            first = data["data"][0]
            return {
                "success": True,
                "airport_id": first["id"],
                "name": first.get("name"),
                "code": first.get("code"),
                "city": first.get("cityName"),
                "country": first.get("countryName")
            }
        return {"success": False, "error": "No results found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_booking_flights(
    from_id: str,
    to_id: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    children: str = "",
    cabin_class: str = "ECONOMY",
    currency: str = "USD",
    sort: str = "BEST"
) -> dict:
    """
    Search for flights using Booking.com Flights API.
    Returns flights on EXACT dates specified.
    
    Args:
        from_id: Origin airport ID (e.g., "ISB.AIRPORT") from searchDestination
        to_id: Destination airport ID (e.g., "DOH.AIRPORT") from searchDestination
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Return date (YYYY-MM-DD) for round trip, None for one-way
        adults: Number of adult passengers
        children: Comma-separated children ages (e.g., "5,10")
        cabin_class: ECONOMY, BUSINESS, or FIRST
        currency: Currency code (USD, EUR, etc.)
        sort: BEST, CHEAPEST, FASTEST
    
    Returns:
        Flight search results with multiple airlines
    """
    url = f"https://{BOOKING_HOST}/api/v1/flights/searchFlights"
    
    params = {
        "fromId": from_id,
        "toId": to_id,
        "departDate": departure_date,
        "pageNo": 1,
        "adults": adults,
        "children": children,
        "sort": sort,
        "cabinClass": cabin_class,
        "currency_code": currency
    }
    
    if return_date:
        params["returnDate"] = return_date
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status"):
            return {"success": True, "data": data.get("data", {})}
        return {"success": False, "error": data.get("message", "Unknown error")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_flights_comprehensive_booking(
    origin_city: str,
    destination_city: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    budget: Optional[float] = None,
    cabin_class: str = "ECONOMY"
) -> str:
    """
    Comprehensive flight search using Booking.com API.
    Handles the full flow: search destinations -> search flights -> format results.
    
    Args:
        origin_city: Origin city name (e.g., "Islamabad")
        destination_city: Destination city name (e.g., "Doha")
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Return date (YYYY-MM-DD) for round trip
        adults: Number of passengers
        budget: Maximum budget in USD (total for all passengers)
        cabin_class: ECONOMY, BUSINESS, FIRST
    
    Returns:
        Formatted flight search results
    """
    # Step 1: Get origin airport ID
    origin_result = search_flight_destination(origin_city)
    if not origin_result.get("success"):
        return f"❌ Could not find airport for '{origin_city}': {origin_result.get('error')}"
    
    from_id = origin_result["airport_id"]
    origin_name = origin_result.get("name", origin_city)
    
    # Step 2: Get destination airport ID
    dest_result = search_flight_destination(destination_city)
    if not dest_result.get("success"):
        return f"❌ Could not find airport for '{destination_city}': {dest_result.get('error')}"
    
    to_id = dest_result["airport_id"]
    dest_name = dest_result.get("name", destination_city)
    
    # Step 3: Search flights
    flight_result = search_booking_flights(
        from_id=from_id,
        to_id=to_id,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        cabin_class=cabin_class
    )
    
    if not flight_result.get("success"):
        return f"❌ Flight search failed: {flight_result.get('error')}"
    
    # Step 4: Format results
    flights_data = flight_result.get("data", {})
    flight_offers = flights_data.get("flightOffers", [])
    
    if not flight_offers:
        return f"❌ No flights found from {origin_city} to {destination_city} on {departure_date}"
    
    # Build formatted output
    output = f"""
✈️ FLIGHT SEARCH RESULTS (Booking.com)
{'='*60}
📍 From: {origin_name} ({from_id.replace('.AIRPORT', '')})
📍 To: {dest_name} ({to_id.replace('.AIRPORT', '')})
📅 Departure: {departure_date}
📅 Return: {return_date or 'One-way'}
👥 Passengers: {adults}
💰 Budget: ${budget} USD (total)
{'='*60}

✅ Found {len(flight_offers)} flight options!
"""
    
    for idx, offer in enumerate(flight_offers[:15], 1):
        # Price
        price_info = offer.get("priceBreakdown", {})
        total_price = float(price_info.get("total", {}).get("units", 0))
        currency = price_info.get("total", {}).get("currencyCode", "USD")
        
        # Budget check
        within_budget = "✅" if (budget is None or total_price <= budget) else "❌ Over budget"
        
        output += f"""
{'─'*60}
✈️ OPTION {idx}
{'─'*60}
💰 Total Price: ${total_price} {currency} {within_budget}
💰 Per Person: ${total_price / adults:.2f} {currency}
"""
        
        # Flight segments
        segments = offer.get("segments", [])
        for seg_idx, segment in enumerate(segments):
            direction = "📤 OUTBOUND" if seg_idx == 0 else "📥 RETURN"
            
            # Get departure date from first leg
            legs = segment.get("legs", [])
            if legs:
                first_leg = legs[0]
                dep_time = first_leg.get("departureTime", "")[:10]
                output += f"\n{direction} ({dep_time}):\n"
            
            for leg in legs:
                dep_airport = leg.get("departureAirport", {}).get("code", "N/A")
                arr_airport = leg.get("arrivalAirport", {}).get("code", "N/A")
                dep_time = leg.get("departureTime", "N/A")
                arr_time = leg.get("arrivalTime", "N/A")
                
                # Airline info
                carriers = leg.get("carriersData", [])
                airline = carriers[0].get("name", "Unknown") if carriers else "Unknown"
                flight_num = leg.get("flightInfo", {}).get("flightNumber", "N/A")
                carrier_code = leg.get("flightInfo", {}).get("carrierInfo", {}).get("operatingCarrier", "")
                
                # Duration
                duration_mins = leg.get("durationInMinutes", 0)
                hours = duration_mins // 60
                mins = duration_mins % 60
                
                output += f"""   {dep_airport} → {arr_airport}
   ✈️  {airline} {carrier_code}{flight_num}
   🕐 {dep_time} - {arr_time}
   ⏱️  Duration: {hours}h {mins}m
"""
    
    # Summary
    if budget:
        affordable = [o for o in flight_offers if float(o.get("priceBreakdown", {}).get("total", {}).get("units", 0)) <= budget]
        output += f"""
{'='*60}
📊 SUMMARY
{'='*60}
💰 Budget: ${budget}
✅ Flights within budget: {len(affordable)} of {len(flight_offers)}
"""
        if affordable:
            cheapest = min(affordable, key=lambda x: float(x.get("priceBreakdown", {}).get("total", {}).get("units", 0)))
            cheapest_price = float(cheapest.get("priceBreakdown", {}).get("total", {}).get("units", 0))
            output += f"🏆 Cheapest within budget: ${cheapest_price}\n"
    else:
        cheapest = min(flight_offers, key=lambda x: float(x.get("priceBreakdown", {}).get("total", {}).get("units", 0)))
        cheapest_price = float(cheapest.get("priceBreakdown", {}).get("total", {}).get("units", 0))
        output += f"""
{'='*60}
📊 SUMMARY
{'='*60}
🏆 Cheapest option: ${cheapest_price}
✈️  Total options: {len(flight_offers)}
"""
    
    return output


# ============================================
# HOTEL/ACCOMMODATION FUNCTIONS
# ============================================

def search_hotel_destination(query: str) -> dict:
    """
    Search for a destination to get its dest_id for hotel searches.
    This is STEP 1 of hotel search - required before searching hotels.
    
    Args:
        query: Destination city name (e.g., "Paris", "London", "Doha")
    
    Returns:
        Destination search results with dest_id
    """
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
    
    params = {"query": query}
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to search destination"}


def search_hotels_by_destination(
    dest_id: str,
    search_type: str,
    arrival_date: str,
    departure_date: str,
    adults: Optional[int] = None,  # Must be provided - no default
    children_age: str = "",
    room_qty: Optional[int] = None,  # Must be provided - no default
    page_number: int = 1,
    currency_code: str = "USD"
) -> dict:
    """
    Search for hotels using dest_id from search_hotel_destination.
    This is STEP 2 of hotel search.
    
    Args:
        dest_id: Destination ID from searchDestination API
        search_type: Type of search (CITY, REGION, etc.)
        arrival_date: Check-in date (YYYY-MM-DD)
        departure_date: Check-out date (YYYY-MM-DD)
        adults: Number of adults
        children_age: Children ages comma-separated (e.g., "0,17")
        room_qty: Number of rooms
        page_number: Page number for pagination
        currency_code: Currency code (USD, EUR, etc.)
    
    Returns:
        Hotel search results with hotel_id for each hotel
    """
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    
    params = {
        "dest_id": dest_id,
        "search_type": search_type,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "adults": adults,
        "room_qty": room_qty,
        "page_number": page_number,
        "units": "metric",
        "temperature_unit": "c",
        "languagecode": "en-us",
        "currency_code": currency_code
    }
    
    if children_age:
        params["children_age"] = children_age
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to search hotels"}


def get_hotel_reviews(hotel_id: str) -> dict:
    """
    Get hotel review scores using hotel_id from hotel search.
    This is STEP 3 (optional) - get detailed reviews for a hotel.
    
    Args:
        hotel_id: Hotel ID from searchHotels API
    
    Returns:
        Hotel review scores and ratings
    """
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviewScores"
    
    params = {
        "hotel_id": hotel_id,
        "languagecode": "en-us"
    }
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to get hotel reviews"}


def get_attractions_near_hotel(hotel_id: str) -> dict:
    """
    Get popular attractions near a hotel using hotel_id.
    This is STEP 3 (optional) - get nearby attractions for a hotel.
    
    Args:
        hotel_id: Hotel ID from searchHotels API
    
    Returns:
        Nearby attractions and points of interest
    """
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getPopularAttractionNearBy"
    
    params = {
        "hotel_id": hotel_id,
        "languagecode": "en-us"
    }
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to get attractions near hotel"}


def search_car_rentals(
    pick_up_latitude: float,
    pick_up_longitude: float,
    drop_off_latitude: float,
    drop_off_longitude: float,
    pick_up_date: str,
    drop_off_date: str,
    pick_up_time: str = "10:00",
    drop_off_time: str = "10:00",
    driver_age: int = 30,
    currency_code: str = "USD",
    location: str = "US"
) -> dict:
    """
    Search for car rentals using Booking.com API
    """
    url = "https://booking-com15.p.rapidapi.com/api/v1/cars/searchCarRentals"
    
    params = {
        "pick_up_latitude": pick_up_latitude,
        "pick_up_longitude": pick_up_longitude,
        "drop_off_latitude": drop_off_latitude,
        "drop_off_longitude": drop_off_longitude,
        "pick_up_date": pick_up_date,
        "drop_off_date": drop_off_date,
        "pick_up_time": pick_up_time,
        "drop_off_time": drop_off_time,
        "driver_age": driver_age,
        "currency_code": currency_code,
        "location": location
    }
    
    headers = {
        "x-rapidapi-host": BOOKING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "message": "Failed to search car rentals"}


def search_hotels_comprehensive(
    destination: str,
    checkin_date: str,
    checkout_date: str,
    budget_per_night: float,
    adults: Optional[int] = None,  # Must be provided - no default
    rooms: Optional[int] = None,  # Must be provided - no default
    star_rating: Optional[int] = None,
    currency_code: str = "USD"
) -> str:
    """
    Comprehensive hotel search that:
    1. Searches for destination to get dest_id
    2. Searches hotels using dest_id
    3. Gets reviews and nearby attractions for top hotels
    
    Args:
        destination: Destination city name
        checkin_date: Check-in date (YYYY-MM-DD)
        checkout_date: Check-out date (YYYY-MM-DD)
        budget_per_night: Maximum budget per night
        adults: Number of adults
        rooms: Number of rooms
        star_rating: Desired star rating (1-5)
        currency_code: Currency code (USD, EUR, etc.)
    
    Returns:
        Formatted hotel search results with reviews
    """
    results = {
        "search_params": {
            "destination": destination,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "budget_per_night": budget_per_night,
            "adults": adults,
            "rooms": rooms,
            "star_rating": star_rating
        },
        "destination_search": None,
        "hotels": [],
        "errors": []
    }
    
    # STEP 1: Search for destination to get dest_id
    dest_result = search_hotel_destination(destination)
    results["destination_search"] = dest_result
    
    if not dest_result.get("success"):
        return f"""
Hotel Search Results
====================
❌ ERROR: Failed to find destination "{destination}"
Error: {dest_result.get('error', 'Unknown error')}

Please try with a different city name or check your API key.
"""
    
    # Extract dest_id from destination search
    dest_data = dest_result.get("data", {})
    if isinstance(dest_data, dict) and "data" in dest_data:
        destinations = dest_data.get("data", [])
    elif isinstance(dest_data, list):
        destinations = dest_data
    else:
        destinations = []
    
    if not destinations:
        return f"""
Hotel Search Results
====================
❌ No destinations found for "{destination}"

Try searching with a more specific city name.
Raw response: {json.dumps(dest_result, indent=2)}
"""
    
    # Get the first matching destination
    first_dest = destinations[0] if destinations else {}
    dest_id = first_dest.get("dest_id") or first_dest.get("id")
    # API returns lowercase but API expects uppercase - convert it
    search_type_raw = first_dest.get("search_type", "city") or first_dest.get("dest_type", "city")
    search_type = search_type_raw.upper() if search_type_raw else "CITY"
    dest_name = first_dest.get("name", destination) or first_dest.get("city_name", destination) or first_dest.get("label", destination)
    
    if not dest_id:
        return f"""
Hotel Search Results
====================
❌ Could not extract destination ID for "{destination}"

Raw destination data: {json.dumps(first_dest, indent=2)}
"""
    
    # STEP 2: Search hotels using dest_id
    hotels_result = search_hotels_by_destination(
        dest_id=str(dest_id),
        search_type=search_type,
        arrival_date=checkin_date,
        departure_date=checkout_date,
        adults=adults,
        room_qty=rooms,
        currency_code=currency_code
    )
    
    if not hotels_result.get("success"):
        results["errors"].append(f"Hotel search failed: {hotels_result.get('error')}")
        return f"""
Hotel Search Results
====================
Destination: {dest_name} (ID: {dest_id})
Check-in: {checkin_date}
Check-out: {checkout_date}

❌ ERROR: Failed to search hotels
Error: {hotels_result.get('error', 'Unknown error')}

Raw response: {json.dumps(hotels_result, indent=2)}
"""
    
    # Parse hotel results
    hotels_data = hotels_result.get("data", {})
    if isinstance(hotels_data, dict):
        hotels_list = hotels_data.get("data", {}).get("hotels", []) or hotels_data.get("hotels", []) or hotels_data.get("data", [])
    else:
        hotels_list = []
    
    # Format output
    formatted_output = f"""
🏨 Hotel Search Results
========================
📍 Destination: {dest_name} (ID: {dest_id})
📅 Check-in: {checkin_date}
📅 Check-out: {checkout_date}
💰 Budget: ${budget_per_night}/night
👥 Adults: {adults}
🛏️ Rooms: {rooms}
⭐ Star Rating: {star_rating or 'Any'}

"""
    
    if not hotels_list:
        formatted_output += """
❌ No hotels found matching your criteria.

This could be because:
- No availability for these dates
- Budget is too restrictive
- Try different dates or increase budget

"""
        formatted_output += f"\nRaw API Response:\n{json.dumps(hotels_data, indent=2)[:2000]}"
        return formatted_output
    
    formatted_output += f"✅ Found {len(hotels_list)} hotels\n\n"
    formatted_output += "=" * 50 + "\n"
    
    # Process top hotels (limit to 10 for performance)
    import re  # Import here for regex parsing
    for idx, hotel in enumerate(hotels_list[:10], 1):
        # The API nests hotel data in 'property' object
        prop = hotel.get("property", {})
        
        hotel_id = hotel.get("hotel_id") or prop.get("id") or hotel.get("id")
        hotel_name = prop.get("name") or hotel.get("hotel_name") or hotel.get("name", "Unknown Hotel")
        
        # Get price info from property.priceBreakdown
        price_info = prop.get("priceBreakdown", {}) or hotel.get("composite_price_breakdown", {}) or hotel.get("price_breakdown", {})
        gross_price_obj = price_info.get("grossPrice", {})
        if isinstance(gross_price_obj, dict):
            gross_price = gross_price_obj.get("value", "N/A")
            currency = gross_price_obj.get("currency", currency_code)
        else:
            gross_price = price_info.get("gross_amount_per_night", {}).get("value") or \
                          price_info.get("gross_price") or \
                          hotel.get("min_total_price") or \
                          hotel.get("price", "N/A")
            currency = price_info.get("gross_amount_per_night", {}).get("currency") or \
                       price_info.get("currency") or currency_code
        
        # Get review info from property
        review_score = prop.get("reviewScore") or hotel.get("review_score") or hotel.get("rating", "N/A")
        review_count = prop.get("reviewCount") or hotel.get("review_nr") or hotel.get("review_count", "N/A")
        review_word = prop.get("reviewScoreWord", "") or hotel.get("review_score_word", "")
        
        # Get location info - extract from accessibilityLabel if available
        accessibility_label = hotel.get("accessibilityLabel", "")
        address = prop.get("address", "") or hotel.get("address", "") or hotel.get("address_trans", "")
        
        # Try to extract district from accessibilityLabel (e.g., "12th arr.")
        district = ""
        if accessibility_label:
            import re
            district_match = re.search(r'(\d+(?:st|nd|rd|th)\s+arr\.?)', accessibility_label, re.IGNORECASE)
            if district_match:
                district = district_match.group(1)
        
        distance = prop.get("distance_to_cc", "") or hotel.get("distance_to_cc", "") or hotel.get("distance", "")
        # Extract distance from accessibility label if not available
        if not distance and accessibility_label:
            dist_match = re.search(r'([\d.]+\s*km from downtown)', accessibility_label, re.IGNORECASE)
            if dist_match:
                distance = dist_match.group(1)
        
        # Get hotel class/stars
        hotel_class = prop.get("propertyClass") or prop.get("accuratePropertyClass") or hotel.get("class") or hotel.get("hotel_class") or hotel.get("star_rating", "")
        
        # Calculate price per night (API returns total price for 5 nights)
        price_per_night = "N/A"
        if gross_price and gross_price != "N/A":
            try:
                total_price = float(str(gross_price).replace(",", ""))
                # Calculate nights between dates
                from datetime import datetime
                checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
                checkout = datetime.strptime(checkout_date, "%Y-%m-%d")
                nights = (checkout - checkin).days
                if nights > 0:
                    price_per_night = round(total_price / nights, 2)
                else:
                    price_per_night = total_price
            except:
                price_per_night = gross_price
        
        formatted_output += f"""
🏨 Hotel #{idx}: {hotel_name}
{'⭐' * int(float(hotel_class)) if hotel_class and str(hotel_class).replace('.','').isdigit() and float(hotel_class) > 0 else ''}
─────────────────────────────────
💰 Total Price: {gross_price if gross_price != 'N/A' else 'N/A'} {currency} (${price_per_night}/night)
📊 Rating: {review_score}/10 {review_word} ({review_count} reviews)
📍 Location: {district} {address}
📏 Distance to center: {distance}
🆔 Hotel ID: {hotel_id}
"""
        
        # STEP 3: Get reviews for top 3 hotels only (to avoid too many API calls)
        if idx <= 3 and hotel_id:
            # Get review scores
            reviews = get_hotel_reviews(str(hotel_id))
            if reviews.get("success"):
                review_data = reviews.get("data", {})
                if isinstance(review_data, dict):
                    data_content = review_data.get("data", [])
                    # data_content is typically a list with one item containing score_breakdown
                    if isinstance(data_content, list) and len(data_content) > 0:
                        first_item = data_content[0]
                        score_breakdown = first_item.get("score_breakdown", [])
                        if score_breakdown:
                            formatted_output += "\n   📝 Review Breakdown:\n"
                            # score_breakdown is a list with items containing 'question' lists
                            for breakdown in score_breakdown[:1]:  # Usually one item
                                questions = breakdown.get("question", [])
                                for q in questions[:6]:  # Limit to 6 categories
                                    cat_name = q.get("localized_question", "")
                                    cat_score = q.get("score", "N/A")
                                    if cat_name and cat_score:
                                        formatted_output += f"      • {cat_name}: {cat_score}/10\n"
                        # Also show score percentages if available
                        score_percentage = first_item.get("score_percentage", [])
                        if score_percentage:
                            formatted_output += "   📈 Score Distribution:\n"
                            for sp in score_percentage[:3]:  # Show top 3
                                word = sp.get("score_word", "")
                                pct = sp.get("percent", 0)
                                if word:
                                    formatted_output += f"      • {word}: {pct}%\n"
            
            # Get nearby attractions
            attractions = get_attractions_near_hotel(str(hotel_id))
            if attractions.get("success"):
                attr_data = attractions.get("data", {})
                if isinstance(attr_data, dict):
                    inner_data = attr_data.get("data", {})
                    # The API returns { data: { popular_landmarks: [], closest_landmarks: [] } }
                    if isinstance(inner_data, dict):
                        popular = inner_data.get("popular_landmarks", [])
                        closest = inner_data.get("closest_landmarks", [])
                        attr_list = popular + closest
                    else:
                        attr_list = inner_data if isinstance(inner_data, list) else []
                    
                    if attr_list and isinstance(attr_list, list) and len(attr_list) > 0:
                        formatted_output += "\n   🎯 Nearby Attractions:\n"
                        for attr in attr_list[:5]:
                            attr_name = attr.get("name", "") or attr.get("attraction_name", "") or attr.get("tag_name", "")
                            attr_dist = attr.get("distance", "") or attr.get("distance_from_hotel", "")
                            if attr_name:
                                formatted_output += f"      • {attr_name} ({attr_dist})\n"
        
        formatted_output += "\n" + "=" * 50 + "\n"
        
        # Filter by budget (use price_per_night, not total)
        try:
            if price_per_night and price_per_night != "N/A":
                price_val = float(str(price_per_night).replace(",", ""))
                if price_val <= budget_per_night:
                    results["hotels"].append({
                        "hotel_id": hotel_id,
                        "name": hotel_name,
                        "price_per_night": price_val,
                        "total_price": gross_price,
                        "currency": currency,
                        "review_score": review_score,
                        "review_count": review_count,
                        "location": f"{district} {address}".strip(),
                        "within_budget": True
                    })
        except (ValueError, TypeError):
            pass
    
    # Summary
    budget_hotels = [h for h in results["hotels"] if h.get("within_budget")]
    formatted_output += f"""

📊 SUMMARY
──────────
Total hotels found: {len(hotels_list)}
Hotels within ${budget_per_night}/night budget: {len(budget_hotels)}

💡 TIP: Use the hotel_id to get more details, book, or compare options.
"""
    
    return formatted_output


def search_accommodations_with_location(
    destination: str,
    checkin_date: str,
    checkout_date: str,
    budget_per_night: float,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    adults: Optional[int] = None,  # Must be provided - no default
    rooms: Optional[int] = None,  # Must be provided - no default
    currency_code: str = "USD"
) -> str:
    """
    Search for accommodations - wrapper that calls search_hotels_comprehensive
    """
    # Just call the comprehensive search since it handles everything
    return search_hotels_comprehensive(
        destination=destination,
        checkin_date=checkin_date,
        checkout_date=checkout_date,
        budget_per_night=budget_per_night,
        adults=adults,
        rooms=rooms,
        currency_code=currency_code
    )


# ============================================
# WEB SEARCH FUNCTIONS (Serper API)
# ============================================

def _do_serper_search(query: str) -> str:
    """
    Internal function to perform web search using Serper API.
    """
    top_result_to_return = 4
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'content-type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        if 'organic' not in response.json():
            return "Sorry, I couldn't find anything about that. There could be an error with your Serper API key."
        else:
            results = response.json()['organic']
            string = []
            for result in results[:top_result_to_return]:
                try:
                    string.append('\n'.join([
                        f"Title: {result['title']}", 
                        f"Link: {result['link']}",
                        f"Snippet: {result['snippet']}", 
                        "\n-----------------"
                    ]))
                except KeyError:
                    continue
            return '\n'.join(string)
    except Exception as e:
        return f"Sorry, I couldn't find anything about that. Error: {str(e)}"


def search_internet(query: str) -> str:
    """
    Search the internet about a given topic and return relevant results
    
    Args:
        query: Search query string
    
    Returns:
        Search results from the web
    """
    return _do_serper_search(query)


def search_attractions(destination: str, interests: str, duration_days: int) -> str:
    """
    Search for attractions and activities using web search
    
    Args:
        destination: Destination city
        interests: User interests (comma-separated)
        duration_days: Trip duration in days
    
    Returns:
        Attraction search results from the web
    """
    query = f"best attractions and things to do in {destination} for {interests} {duration_days} days itinerary"
    return _do_serper_search(query)


def search_restaurants(destination: str, cuisine_types: str, budget_per_meal: float) -> str:
    """
    Search for restaurants using web search
    
    Args:
        destination: Destination city
        cuisine_types: Types of cuisine
        budget_per_meal: Maximum budget per meal
    
    Returns:
        Restaurant search results from the web
    """
    query = f"best {cuisine_types} restaurants in {destination} under ${budget_per_meal} per person"
    return _do_serper_search(query)


# ============================================
# CALCULATOR FUNCTION
# ============================================

def calculate(operation: str) -> str:
    """
    Perform mathematical calculations
    
    Args:
        operation: Mathematical expression to evaluate (e.g., "200*7" or "5000/2*10")
    
    Returns:
        Result of the calculation
    """
    try:
        # Basic safety check - only allow math operations
        allowed_chars = set('0123456789+-*/().% ')
        if not all(c in allowed_chars for c in operation):
            return "Error: Only mathematical expressions are allowed"
        
        result = eval(operation)
        return str(result)
    except SyntaxError:
        return "Error: Invalid syntax in mathematical expression"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================
# MCP SERVER SETUP
# ============================================

app = Server("trip-planner-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available trip planning tools"""
    return [
        # Flight Tools
        Tool(
            name="search_flights_kiwi",
            description="Search for flights using Kiwi.com API. Best for finding cheap flights and flexible options.",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin city/airport (e.g., 'Country:US', 'City:london_gb')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination city/airport (e.g., 'City:paris_fr')"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date in YYYY-MM-DD format (optional)"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult passengers - MUST be provided from user conversation"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (USD, EUR, GBP, etc.)"
                    },
                    "cabin_class": {
                        "type": "string",
                        "description": "Cabin class (ECONOMY, BUSINESS, FIRST)"
                    }
                },
                "required": ["origin", "destination", "departure_date", "adults"]
            }
        ),
        Tool(
            name="search_cheap_flights",
            description="Unified flight search combining multiple APIs for comprehensive results. Use this for general flight searches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin city or airport code"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination city or airport code"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date in YYYY-MM-DD format (optional)"
                    },
                    "budget": {
                        "type": "number",
                        "description": "Maximum budget in USD (optional)"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult passengers - MUST be provided from user conversation"
                    }
                },
                "required": ["origin", "destination", "departure_date", "adults"]
            }
        ),
        # Hotel Tools
        Tool(
            name="search_hotels_comprehensive",
            description="Comprehensive hotel search with budget filtering. Use this for finding accommodations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination city or location name"
                    },
                    "checkin_date": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format"
                    },
                    "checkout_date": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format"
                    },
                    "budget_per_night": {
                        "type": "number",
                        "description": "Maximum budget per night in USD"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adults - MUST be provided from user conversation"
                    },
                    "rooms": {
                        "type": "integer",
                        "description": "Number of rooms needed - MUST be provided from user conversation"
                    },
                    "star_rating": {
                        "type": "integer",
                        "description": "Desired star rating (1-5, optional)"
                    }
                },
                "required": ["destination", "checkin_date", "checkout_date", "budget_per_night", "adults", "rooms"]
            }
        ),
        Tool(
            name="search_accommodations_with_location",
            description="Search for accommodations with optional GPS coordinates for location-based results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination city name"
                    },
                    "checkin_date": {
                        "type": "string",
                        "description": "Check-in date (YYYY-MM-DD)"
                    },
                    "checkout_date": {
                        "type": "string",
                        "description": "Check-out date (YYYY-MM-DD)"
                    },
                    "budget_per_night": {
                        "type": "number",
                        "description": "Maximum budget per night"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Optional latitude for location search"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Optional longitude for location search"
                    }
                },
                "required": ["destination", "checkin_date", "checkout_date", "budget_per_night"]
            }
        ),
        Tool(
            name="search_car_rentals",
            description="Search for car rentals using Booking.com API. Useful for travelers needing transportation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pick_up_latitude": {
                        "type": "number",
                        "description": "Pickup location latitude"
                    },
                    "pick_up_longitude": {
                        "type": "number",
                        "description": "Pickup location longitude"
                    },
                    "drop_off_latitude": {
                        "type": "number",
                        "description": "Drop-off location latitude"
                    },
                    "drop_off_longitude": {
                        "type": "number",
                        "description": "Drop-off location longitude"
                    },
                    "pick_up_date": {
                        "type": "string",
                        "description": "Pickup date (YYYY-MM-DD)"
                    },
                    "drop_off_date": {
                        "type": "string",
                        "description": "Drop-off date (YYYY-MM-DD)"
                    },
                    "pick_up_time": {
                        "type": "string",
                        "description": "Pickup time (HH:MM)",
                        "default": "10:00"
                    },
                    "drop_off_time": {
                        "type": "string",
                        "description": "Drop-off time (HH:MM)",
                        "default": "10:00"
                    },
                    "driver_age": {
                        "type": "integer",
                        "description": "Driver's age",
                        "default": 30
                    },
                    "currency_code": {
                        "type": "string",
                        "description": "Currency code (USD, EUR, etc.)",
                        "default": "USD"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location code (US, GB, etc.)",
                        "default": "US"
                    }
                },
                "required": [
                    "pick_up_latitude", "pick_up_longitude",
                    "drop_off_latitude", "drop_off_longitude",
                    "pick_up_date", "drop_off_date"
                ]
            }
        ),
        # Web Search Tools
        Tool(
            name="search_internet",
            description="Search the internet about any topic using Serper API. Returns relevant web results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_attractions",
            description="Search for attractions and things to do at a destination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination city"
                    },
                    "interests": {
                        "type": "string",
                        "description": "User interests (comma-separated, e.g., 'museums, food, nightlife')"
                    },
                    "duration_days": {
                        "type": "integer",
                        "description": "Trip duration in days"
                    }
                },
                "required": ["destination", "interests", "duration_days"]
            }
        ),
        Tool(
            name="search_restaurants",
            description="Search for restaurants at a destination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination city"
                    },
                    "cuisine_types": {
                        "type": "string",
                        "description": "Types of cuisine (e.g., 'Italian, French')"
                    },
                    "budget_per_meal": {
                        "type": "number",
                        "description": "Maximum budget per meal"
                    }
                },
                "required": ["destination", "cuisine_types", "budget_per_meal"]
            }
        ),
        # Calculator Tool
        Tool(
            name="calculate",
            description="Perform mathematical calculations. Useful for budget calculations, currency conversions, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '200*7' or '5000/2*10')"
                    }
                },
                "required": ["operation"]
            }
        ),
        # Additional Hotel Tools
        Tool(
            name="search_hotel_destination",
            description="Search for a destination to get its dest_id. Use this FIRST before searching hotels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Destination city name (e.g., 'Paris', 'London', 'Doha')"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_hotels_by_destination",
            description="Search hotels using dest_id from search_hotel_destination. Use AFTER getting dest_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dest_id": {
                        "type": "string",
                        "description": "Destination ID from searchDestination API"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search (CITY, REGION, etc.)"
                    },
                    "arrival_date": {
                        "type": "string",
                        "description": "Check-in date (YYYY-MM-DD)"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Check-out date (YYYY-MM-DD)"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adults - MUST be provided from user conversation"
                    },
                    "room_qty": {
                        "type": "integer",
                        "description": "Number of rooms - MUST be provided from user conversation"
                    },
                    "currency_code": {
                        "type": "string",
                        "description": "Currency code (USD, EUR, etc.)"
                    }
                },
                "required": ["dest_id", "arrival_date", "departure_date", "adults", "room_qty"]
            }
        ),
        Tool(
            name="get_hotel_reviews",
            description="Get hotel review scores using hotel_id from hotel search results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hotel_id": {
                        "type": "string",
                        "description": "Hotel ID from searchHotels API"
                    }
                },
                "required": ["hotel_id"]
            }
        ),
        Tool(
            name="get_attractions_near_hotel",
            description="Get popular attractions near a hotel using hotel_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hotel_id": {
                        "type": "string",
                        "description": "Hotel ID from searchHotels API"
                    }
                },
                "required": ["hotel_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute trip planning tools"""
    
    # Flight Tools
    if name == "search_flights_kiwi":
        result = search_flights_kiwi(
            origin=arguments.get("origin"),
            destination=arguments.get("destination"),
            departure_date=arguments.get("departure_date"),
            return_date=arguments.get("return_date"),
            adults=arguments.get("adults"),  # Required - must be provided
            currency=arguments.get("currency", "USD"),
            cabin_class=arguments.get("cabin_class", "ECONOMY")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "search_cheap_flights":
        result = search_cheap_flights(
            origin=arguments.get("origin"),
            destination=arguments.get("destination"),
            departure_date=arguments.get("departure_date"),
            return_date=arguments.get("return_date"),
            budget=arguments.get("budget"),
            adults=arguments.get("adults")  # Required - must be provided
        )
        return [TextContent(type="text", text=result)]
    
    # Hotel Tools
    elif name == "search_hotels_comprehensive":
        result = search_hotels_comprehensive(
            destination=arguments.get("destination"),
            checkin_date=arguments.get("checkin_date"),
            checkout_date=arguments.get("checkout_date"),
            budget_per_night=arguments.get("budget_per_night"),
            adults=arguments.get("adults"),  # Required - must be provided
            rooms=arguments.get("rooms"),  # Required - must be provided
            star_rating=arguments.get("star_rating")
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "search_accommodations_with_location":
        result = search_accommodations_with_location(
            destination=arguments.get("destination"),
            checkin_date=arguments.get("checkin_date"),
            checkout_date=arguments.get("checkout_date"),
            budget_per_night=arguments.get("budget_per_night"),
            latitude=arguments.get("latitude"),
            longitude=arguments.get("longitude")
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "search_car_rentals":
        result = search_car_rentals(
            pick_up_latitude=arguments.get("pick_up_latitude"),
            pick_up_longitude=arguments.get("pick_up_longitude"),
            drop_off_latitude=arguments.get("drop_off_latitude"),
            drop_off_longitude=arguments.get("drop_off_longitude"),
            pick_up_date=arguments.get("pick_up_date"),
            drop_off_date=arguments.get("drop_off_date"),
            pick_up_time=arguments.get("pick_up_time", "10:00"),
            drop_off_time=arguments.get("drop_off_time", "10:00"),
            driver_age=arguments.get("driver_age", 30),
            currency_code=arguments.get("currency_code", "USD"),
            location=arguments.get("location", "US")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    # Web Search Tools
    elif name == "search_internet":
        result = search_internet(query=arguments.get("query"))
        return [TextContent(type="text", text=result)]
    
    elif name == "search_attractions":
        result = search_attractions(
            destination=arguments.get("destination"),
            interests=arguments.get("interests"),
            duration_days=arguments.get("duration_days")
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "search_restaurants":
        result = search_restaurants(
            destination=arguments.get("destination"),
            cuisine_types=arguments.get("cuisine_types"),
            budget_per_meal=arguments.get("budget_per_meal")
        )
        return [TextContent(type="text", text=result)]
    
    # Calculator Tool
    elif name == "calculate":
        result = calculate(operation=arguments.get("operation"))
        return [TextContent(type="text", text=result)]
    
    # Additional Hotel Tools
    elif name == "search_hotel_destination":
        result = search_hotel_destination(query=arguments.get("query"))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "search_hotels_by_destination":
        result = search_hotels_by_destination(
            dest_id=arguments.get("dest_id"),
            search_type=arguments.get("search_type", "CITY"),
            arrival_date=arguments.get("arrival_date"),
            departure_date=arguments.get("departure_date"),
            adults=arguments.get("adults"),  # Required - must be provided
            room_qty=arguments.get("room_qty"),  # Required - must be provided
            currency_code=arguments.get("currency_code", "USD")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_hotel_reviews":
        result = get_hotel_reviews(hotel_id=arguments.get("hotel_id"))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_attractions_near_hotel":
        result = get_attractions_near_hotel(hotel_id=arguments.get("hotel_id"))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
