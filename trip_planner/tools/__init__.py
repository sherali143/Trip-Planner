"""
Everything that talks to the outside world.

`agent_tools` is what an agent holds; it reaches outward through either
`mcp_client` (over JSON-RPC) or `travel_apis` (straight over HTTPS).
"""

from trip_planner.tools.agent_tools import (calculate,
                                            get_attractions_near_hotel,
                                            get_hotel_reviews,
                                            search_accommodations_with_location,
                                            search_attractions,
                                            search_comprehensive_flights,
                                            search_hotel_destination,
                                            search_hotels_by_dest_id,
                                            search_hotels_comprehensive,
                                            search_internet, search_restaurants,
                                            search_round_trip_flights)

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
