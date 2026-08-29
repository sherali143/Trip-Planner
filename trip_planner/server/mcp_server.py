"""
The tool server.

Twelve tools for flights, hotels, venues and arithmetic, each with a declared
input schema, served over JSON-RPC on standard input and output. Runs as its
own process.
"""
import os
import sys
import json
import asyncio
from typing import Any, Optional

# This module is launched as a STANDALONE subprocess by MCPClient
# (`python trip_planner/server/mcp_server.py`), so the project root is not on sys.path
# and any `src.*` import would raise ModuleNotFoundError. The failure is quiet
# from the caller's side: every tool call just comes back as "Connection lost".
# Must run before the first src.* import below.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from trip_planner.core.http_cache import cached_get, cached_post
from trip_planner.core.safe_math import calculate as _safe_calculate
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
BOOKING_HOST = "booking-com15.p.rapidapi.com"

# How many hotels get the extra review-breakdown + nearby-attraction lookups.
# Each one costs 2 additional Booking.com calls against a 50-call MONTHLY free
# tier; see the comment at the enrichment block in search_hotels_comprehensive.
_HOTEL_ENRICHMENT_TOP_N = int(os.getenv("HOTEL_ENRICHMENT_TOP_N", "0"))


# ============================================
# HOTEL/ACCOMMODATION FUNCTIONS
# ============================================

def _booking_get(path: str, params: dict, failure: str) -> dict:
    """
    One request to Booking.com, wrapped in the success/error envelope.

    Every endpoint below sends the same host and credential, waits the same
    thirty seconds, and reports failure the same way, so that lives here once
    instead of in each of them.

    `path` completes the URL rather than replacing it: the response cache keys
    on the exact URL and parameters, so both are passed through untouched and
    every existing recording still matches.
    """
    try:
        response = cached_get(
            f"https://{BOOKING_HOST}/api/v1/{path}",
            headers={"x-rapidapi-host": BOOKING_HOST,
                     "x-rapidapi-key": RAPIDAPI_KEY},
            params=params, timeout=30)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e), "message": failure}


def search_hotel_destination(query: str) -> dict:
    """
    Search for a destination to get its dest_id for hotel searches.
    This is STEP 1 of hotel search - required before searching hotels.

    Args:
        query: Destination city name (e.g., "Paris", "London", "Doha")

    Returns:
        Destination search results with dest_id
    """
    return _booking_get("hotels/searchDestination", {"query": query},
                        "Failed to search destination")


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

    return _booking_get("hotels/searchHotels", params, "Failed to search hotels")


def get_hotel_reviews(hotel_id: str) -> dict:
    """
    Get hotel review scores using hotel_id from hotel search.
    This is STEP 3 (optional) - get detailed reviews for a hotel.
    
    Args:
        hotel_id: Hotel ID from searchHotels API
    
    Returns:
        Hotel review scores and ratings
    """
    return _booking_get("hotels/getHotelReviewScores",
                        {"hotel_id": hotel_id, "languagecode": "en-us"},
                        "Failed to get hotel reviews")


def get_attractions_near_hotel(hotel_id: str) -> dict:
    """
    Get popular attractions near a hotel using hotel_id.
    This is STEP 3 (optional) - get nearby attractions for a hotel.
    
    Args:
        hotel_id: Hotel ID from searchHotels API
    
    Returns:
        Nearby attractions and points of interest
    """
    return _booking_get("hotels/getPopularAttractionNearBy",
                        {"hotel_id": hotel_id, "languagecode": "en-us"},
                        "Failed to get attractions near hotel")


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

    # Unwrapped deliberately: this endpoint has always returned the payload
    # itself rather than the envelope the hotel calls use, and its caller reads
    # it that way. Left as it is rather than quietly changing a tool's contract.
    result = _booking_get("cars/searchCarRentals", params,
                          "Failed to search car rentals")
    if result["success"]:
        return result["data"]
    return {"error": result["error"], "message": result["message"]}


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
        
        # STEP 3: Optional per-hotel enrichment (review breakdown + nearby POIs).
        #
        # Each enriched hotel costs 2 extra Booking.com calls, so enriching the
        # top 3 made one hotel search cost 8 calls (1 destination + 1 search +
        # 6 enrichment). The free tier allows 50 calls PER MONTH, so a single
        # 20-scenario evaluation would need 160 and is impossible.
        #
        # Disabled by default: the review breakdown and nearby-attraction lists
        # are not used by any itinerary, and the headline rating and review
        # count already come free with the search response. Set
        # HOTEL_ENRICHMENT_TOP_N to re-enable for interactive demos.
        if idx <= _HOTEL_ENRICHMENT_TOP_N and hotel_id:
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
        response = cached_post(url, headers=headers, data=payload, timeout=30)
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
    Perform mathematical calculations.

    Args:
        operation: Mathematical expression to evaluate (e.g., "200*7" or "5000/2*10")

    Returns:
        Result of the calculation, or a readable error.

    Delegates to trip_planner/core/safe_math.py, which walks the expression's syntax tree
    instead of calling eval. The previous implementation filtered the input
    against a permitted character set and evaluated it directly; that blocks name
    lookups but not `9**9**9`, which is eight characters long and exhausts the
    process. See the module docstring for the full reasoning.
    """
    return _safe_calculate(operation)


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
            name="search_flights",
            description="Search for flights using fly-scraper API. Use this for all flight searches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin city name (e.g., 'London', 'New York', 'Dubai')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination city name (e.g., 'Paris', 'Tokyo', 'Sydney')"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date in YYYY-MM-DD format (optional for one-way)"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult passengers"
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
    if name == "search_flights":
        from trip_planner.tools.travel_apis import _call_booking_flights_api
        result = _call_booking_flights_api(
            origin_city=arguments.get("origin"),
            destination_city=arguments.get("destination"),
            departure_date=arguments.get("departure_date"),
            return_date=arguments.get("return_date"),
            adults=arguments.get("adults", 1)
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
