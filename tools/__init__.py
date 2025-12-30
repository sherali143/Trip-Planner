"""
Trip Planner Tools (Unified MCP Integration)

This package provides all trip planning tools through a unified MCP server:

FLIGHT TOOLS:
- search_round_trip_flights: Search for round-trip flights
- search_comprehensive_flights: Comprehensive flight search

HOTEL TOOLS:
- search_hotels_comprehensive: Comprehensive hotel search with reviews
- search_accommodations_with_location: Location-based accommodation search
- search_hotel_destination: Get destination ID (step 1 for detailed search)
- search_hotels_by_dest_id: Search hotels by destination ID (step 2)
- get_hotel_reviews: Get hotel review scores
- get_attractions_near_hotel: Get nearby attractions

WEB SEARCH TOOLS:
- search_internet: General web search using Serper API
- search_attractions: Search for tourist attractions
- search_restaurants: Search for restaurants

CALCULATOR TOOL:
- calculate: Perform mathematical calculations

All tools communicate with the unified MCP server (trip_planner_mcp_server.py)
via JSON-RPC over stdio for standardized API integration.
"""

from tools.mcp_tools import (
    # Flight tools
    search_round_trip_flights,
    search_comprehensive_flights,
    # Hotel tools
    search_hotels_comprehensive,
    search_accommodations_with_location,
    search_hotel_destination,
    search_hotels_by_dest_id,
    get_hotel_reviews,
    get_attractions_near_hotel,
    # Web search tools
    search_internet,
    search_attractions,
    search_restaurants,
    # Calculator tool
    calculate
)

__all__ = [
    # Flight tools
    'search_round_trip_flights',
    'search_comprehensive_flights',
    # Hotel tools
    'search_hotels_comprehensive',
    'search_accommodations_with_location',
    'search_hotel_destination',
    'search_hotels_by_dest_id',
    'get_hotel_reviews',
    'get_attractions_near_hotel',
    # Web search tools
    'search_internet',
    'search_attractions',
    'search_restaurants',
    # Calculator tool
    'calculate'
]
