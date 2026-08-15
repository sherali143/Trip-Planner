"""
WHAT THIS FOLDER DOES
=====================
Everything to do with calling an external service.

    mcp_client.py   speaks to the MCP server over JSON-RPC, as a subprocess
    travel_apis.py  calls the travel APIs over HTTPS, directly
    agent_tools.py  the 12 tools an agent can hold and decide to call

This module re-exports the twelve agent tools, because that is what an agent is
given. They are CrewAI `Tool` OBJECTS, not plain functions — call `.run(...)`,
never `f(...)`. Code that only wants the behaviour imports the plain functions
from trip_planner/server/mcp_server.py or trip_planner/tools/travel_apis.py.
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
