import json
import os

import requests
from langchain.tools import tool


def _do_search(query: str) -> str:
    """
    Internal function to perform web search using Serper API.
    """
    top_result_to_return = 4
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': os.environ.get('SERPER_API_KEY', ''),
        'content-type': 'application/json'
    }
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        # check if there is an organic key
        if 'organic' not in response.json():
            return "Sorry, I couldn't find anything about that, there could be an error with your serper api key."
        else:
            results = response.json()['organic']
            string = []
            for result in results[:top_result_to_return]:
                try:
                    string.append('\n'.join([
                        f"Title: {result['title']}", f"Link: {result['link']}",
                        f"Snippet: {result['snippet']}", "\n-----------------"
                    ]))
                except KeyError:
                    next

            return '\n'.join(string)
    except Exception as e:
        return f"Sorry, I couldn't find anything about that. Error: {str(e)}"


@tool("Search the internet")
def search_internet(query: str) -> str:
    """Useful to search the internet about a given topic and return relevant results"""
    return _do_search(query)


@tool("Search for flights via MCP")
def search_flights(origin: str, destination: str, departure_date: str, 
                  return_date: str, budget: float) -> str:
    """
    Search for flights using web search (MCP-style interface).
    
    Args:
        origin: Origin city/airport
        destination: Destination city
        departure_date: Departure date
        return_date: Return date
        budget: Maximum budget
        
    Returns:
        Flight search results from the web
    """
    query = f"flights from {origin} to {destination} on {departure_date} returning {return_date} under ${budget}"
    return _do_search(query)


@tool("Search for hotels via MCP")
def search_hotels(destination: str, checkin_date: str, checkout_date: str, 
                 budget_per_night: float) -> str:
    """
    Search for hotels using web search (MCP-style interface).
    
    Args:
        destination: Destination city
        checkin_date: Check-in date
        checkout_date: Check-out date
        budget_per_night: Maximum budget per night
        
    Returns:
        Hotel search results from the web
    """
    query = f"hotels in {destination} from {checkin_date} to {checkout_date} under ${budget_per_night} per night"
    return _do_search(query)


@tool("Search for attractions via MCP")
def search_attractions(destination: str, interests: str, duration_days: int) -> str:
    """
    Search for attractions and activities using web search (MCP-style interface).
    
    Args:
        destination: Destination city
        interests: User interests (comma-separated)
        duration_days: Trip duration in days
        
    Returns:
        Attraction search results from the web
    """
    query = f"best attractions and things to do in {destination} for {interests} {duration_days} days itinerary"
    return _do_search(query)


@tool("Search for restaurants via MCP")
def search_restaurants(destination: str, cuisine_types: str, budget_per_meal: float) -> str:
    """
    Search for restaurants using web search (MCP-style interface).
    
    Args:
        destination: Destination city
        cuisine_types: Types of cuisine
        budget_per_meal: Maximum budget per meal
        
    Returns:
        Restaurant search results from the web
    """
    query = f"best {cuisine_types} restaurants in {destination} under ${budget_per_meal} per person"
    return _do_search(query)


# Legacy class for backward compatibility
class SearchTools:
    """
    Legacy SearchTools class for backward compatibility.
    Use the standalone tool functions instead.
    """
    search_internet = search_internet
    search_flights = search_flights
    search_hotels = search_hotels
    search_attractions = search_attractions
    search_restaurants = search_restaurants