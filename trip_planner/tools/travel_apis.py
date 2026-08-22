"""
WHAT THIS FILE DOES
===================
Calls the travel APIs over HTTPS, directly.

These are the functions that actually fetch data: flights from fly-scraper,
airport identifiers and a fallback flight search from Booking.com. They do not
go through the MCP server, because a flight response is large enough that
round-tripping it through a subprocess pipe is wasteful, and because the shipped
path has no agent that needs to choose between them.

Every request goes through trip_planner/core/http_cache.py, so it is recorded on
the way out and replayed on the way back in. That is what lets the whole
evaluation re-run with no API keys.

Three things about fly-scraper that are not obvious
---------------------------------------------------
1. It is a TWO-PHASE API. The search endpoint only STARTS a search and returns a
   sessionId with status "incomplete"; the results come from a second endpoint.
   Reading the first response as final returns zero flights, every time.

2. Its date parameters are camelCase (departureDate, returnDate). The snake_case
   forms are accepted, return HTTP 200, and are then ignored — so the search runs
   against a default date window and nothing reports an error.

3. The paths are plural (/flights/...). The provider's own console lists them in
   the singular, which 404s.

All three are preserved in the recorded responses in .api_cache/, which is why
the dissertation can show the evidence rather than describe it.
"""

import json
import logging
import os
import time
from typing import Optional

from trip_planner.core.http_cache import cached_get

logger = logging.getLogger(__name__)

from trip_planner.core.http_cache import cached_get

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
        # ASCII deliberately. This printed "->" as an arrow character, which
        # raises UnicodeEncodeError on a Windows console still using cp1252 — and
        # it raised from inside the flight call, so the whole search failed on a
        # progress message. It surfaced as "live price check failed: 'charmap'
        # codec can't encode character", which reads like an API problem.
        print(f"  Resolved {origin_code} -> {origin_sky}, {dest_code} -> {dest_sky}")
    
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
