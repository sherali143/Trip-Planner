"""
Tool layer exposed to CrewAI agents.

These are CrewAI `@tool` objects, NOT plain functions — call them with
`.run(...)`. Runtime code that needs the underlying behaviour imports the plain
functions from `src.server.mcp_server` instead.

Most of these route through the MCP server over JSON-RPC; the flight tools call
the upstream API directly because their responses are too large to round-trip
comfortably over stdio.
"""

from src.tools.mcp_tools import (
    search_round_trip_flights,
    search_comprehensive_flights,
    search_hotels_comprehensive,
    search_accommodations_with_location,
    search_hotel_destination,
    search_hotels_by_dest_id,
    get_hotel_reviews,
    get_attractions_near_hotel,
    search_internet,
    search_attractions,
    search_restaurants,
    calculate,
)

__all__ = [
    "search_round_trip_flights",
    "search_comprehensive_flights",
    "search_hotels_comprehensive",
    "search_accommodations_with_location",
    "search_hotel_destination",
    "search_hotels_by_dest_id",
    "get_hotel_reviews",
    "get_attractions_near_hotel",
    "search_internet",
    "search_attractions",
    "search_restaurants",
    "calculate",
]
