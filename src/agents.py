
from crewai import Agent
from textwrap import dedent
from langchain_openai import ChatOpenAI
from typing import List, Optional
import os

# All tools now come from the unified MCP tools module
from src.tools import (
    # Flight tools
    search_comprehensive_flights,
    search_round_trip_flights,
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


class TripPlannerAgents:
    """
    Trip Planner Agents with A2A Communication and MCP Tool Integration
    
    Enhanced with better LLM configuration and explicit instructions
    """
    
    def __init__(self):
        # Configurable model via env var (defaults to gpt-4o for backward compatibility)
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        self.llm_conversation = ChatOpenAI(
            model=model,  # type: ignore
            temperature=0.7  # type: ignore
        )
        
        self.llm_standard = ChatOpenAI(
            model=model,  # type: ignore
            temperature=0.3  # type: ignore
        )
        
        self.llm_coordinator = ChatOpenAI(
            model=model,  # type: ignore
            temperature=0.3  # type: ignore
        )
    
    def conversational_agent(self) -> Agent:
        """
        Conversational LLM Agent that engages users in natural dialogue
        """
        return Agent(
            role="Travel Conversation Assistant",
            goal="Collect complete travel information through friendly conversation",
            backstory=dedent("""
                Friendly travel assistant. Collect these REQUIRED details through conversation:
                1. Origin city
                2. Destination
                3. Departure date (YYYY-MM-DD format)
                4. Return date (or trip duration)
                5. Number of travelers (adults, children)
                6. Total budget (USD)
                7. Interests/activities
                8. Accommodation preference
                
                Conversation flow: Ask questions one at a time. After collecting all info,
                summarize and confirm with user before signaling completion.
                
                Rules: Never assume dates or traveler count - always ask explicitly.
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.llm_conversation,
            tools=[],
            max_iter=15
        )
    
    def preferences_extractor_agent(self) -> Agent:
        """
        Preferences Extractor Agent - structures conversation data
        """
        return Agent(
            role="Travel Preferences Extractor",
            goal="Extract structured JSON from conversation transcript",
            backstory=dedent("""
                Extract travel preferences from conversation into JSON format:
                {
                    "origin": "city", "destination": "city",
                    "departure_date": "YYYY-MM-DD", "return_date": "YYYY-MM-DD",
                    "trip_duration": N, "num_adults": N, "num_children": N,
                    "total_budget": N, "interests": [], "travel_style": "budget/moderate/luxury"
                }
                
                Budget allocation: flights 35%, hotels 35%, activities 20%, meals 10%.
                Calculate return_date from departure + duration if not explicit.
                Defaults: 1 adult, 0 children if not specified.
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[],
            max_iter=5
        )
    
    def flight_search_agent(self) -> Agent:
        """
        Flight Search Agent - Uses Booking.com Flight API for real flight searches
        """
        return Agent(
            role="Flight Search Specialist",
            goal="Find flights within budget using city names",
            backstory=dedent("""
                Search for flights using Booking.com API.
                
                Process:
                1. Get origin, destination, dates from extraction task
                2. Call search_comprehensive_flights with CITY NAMES (not airport codes)
                3. Return top 5 options with price, airline, times, duration
                
                Defaults: 1 adult, ECONOMY class.
                If API fails, use search_internet as backup.
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[
                search_comprehensive_flights,
                search_round_trip_flights,
                search_internet,
                calculate
            ],
            max_iter=8
        )
    
    def hotel_agent(self) -> Agent:
        """
        Hotel Search Agent - Uses MCP Hotel Server for comprehensive hotel searches
        """
        return Agent(
            role="Hotel Search Specialist",
            goal="Find hotels within budget",
            backstory=dedent("""
                Search for hotels using Booking.com API.
                
                Process:
                1. Get destination, dates, travelers from extraction task
                2. Calculate budget_per_night = accommodation_budget / trip_duration
                3. Call search_hotels_comprehensive
                4. Return top 5 options with price/night, rating, amenities
                
                Defaults: 1 adult, 1 room.
                If MCP fails, use search_internet as backup.
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[
                search_hotels_comprehensive,
                search_accommodations_with_location,
                search_hotel_destination,
                search_hotels_by_dest_id,
                get_hotel_reviews,
                get_attractions_near_hotel,
                search_internet,
                calculate
            ],
            max_iter=12
        )
    
    def attraction_agent(self) -> Agent:
        """
        Attractions & Activities Agent
        """
        return Agent(
            role="Activities Specialist",
            goal="Find attractions and restaurants within budget",
            backstory=dedent("""
                Find activities and dining for each day of the trip.
                
                For each day include:
                - Morning activity (name, cost, hours)
                - Lunch restaurant (cuisine, price range)
                - Afternoon activity
                - Dinner restaurant
                
                Track daily spending vs daily_budget = (activities + meals) / trip_days.
                Mix free and paid activities. Use search_attractions and search_restaurants.
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[
                search_attractions,
                search_restaurants,
                search_internet,
                calculate
            ],
            max_iter=10
        )
    
    def itinerary_coordinator_agent(self) -> Agent:
        """
        Itinerary Coordinator - Creates final detailed itinerary
        """
        return Agent(
            role="Itinerary Coordinator",
            goal="Create day-by-day itinerary from all agent data",
            backstory=dedent("""
                Synthesize data from flight, hotel, and attraction agents into a complete itinerary.
                
                OUTPUT STRUCTURE (ALL SECTIONS REQUIRED):
                1. TOP 3 FLIGHTS with prices, times, airline
                2. TOP 3 HOTELS with price/night, rating, location
                3. DAILY ITINERARY - Create "DAY X:" section for EVERY day:
                   - Morning: Activity + Breakfast/Lunch
                   - Afternoon: Activity + Dinner
                   - Daily cost subtotal
                4. BUDGET SUMMARY (itemized total vs allocated)
                5. TRAVEL TIPS (packing, local knowledge)
                
                CRITICAL RULES:
                - NEVER return just a summary - always provide FULL DETAILS
                - Your output must be 500+ words minimum
                - Each "DAY X:" section must have specific activities, times, and costs
                - If trip is 5 days, you must have: DAY 1, DAY 2, DAY 3, DAY 4, DAY 5
                - Use calculator to verify budget math
            """),
            verbose=True,
            allow_delegation=True,
            llm=self.llm_coordinator,
            tools=[
                calculate,
                search_internet,
                search_attractions,
                search_restaurants
            ],
            max_iter=15,
            max_rpm=10
        )