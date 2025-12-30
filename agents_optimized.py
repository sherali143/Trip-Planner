"""
Optimized Trip Planner Agents for Token Reduction Experiment

OPTIMIZATIONS APPLIED:
1. Condensed backstories (~30% shorter)
2. Lower max_iter values (3-5 vs 8-15)
3. GPT-4o-mini for non-critical agents
4. verbose=False by default
"""

from crewai import Agent
from textwrap import dedent
from langchain_openai import ChatOpenAI
from typing import List, Optional
import os

# All tools from the unified MCP tools module
from tools.mcp_tools import (
    search_comprehensive_flights,
    search_round_trip_flights,
    search_hotels_comprehensive,
    search_accommodations_with_location,
    search_hotel_destination,
    search_hotels_by_dest_id,
    get_hotel_reviews,
    get_attractions_near_hotel,
    search_internet,
    search_attractions,
    search_restaurants,
    calculate
)


class TripPlannerAgentsOptimized:
    """
    Optimized Trip Planner Agents with reduced token consumption.
    
    Changes vs original:
    - ~30% shorter backstories
    - max_iter reduced from 8-15 to 3-5
    - GPT-4o-mini for search agents
    - verbose=False for all agents
    """
    
    def __init__(self, use_mini_models: bool = True):
        """
        Args:
            use_mini_models: If True, use GPT-4o-mini for search agents (cheaper)
        """
        # GPT-4 for conversation (emotional intelligence)
        self.llm_conversation = ChatOpenAI(
            model="gpt-4",  # type: ignore
            temperature=0.7  # type: ignore
        )
        
        # Standard model for structured tasks
        self.llm_standard = ChatOpenAI(
            model="gpt-4o-mini" if use_mini_models else "gpt-4o",  # type: ignore
            temperature=0.3  # type: ignore
        )
        
        # Coordinator uses full GPT-4o for quality
        self.llm_coordinator = ChatOpenAI(
            model="gpt-4o",  # type: ignore
            temperature=0.3  # type: ignore
        )
    
    def conversational_agent(self) -> Agent:
        """Conversational Agent - OPTIMIZED"""
        return Agent(
            role="Travel Assistant",
            goal="Collect travel requirements through friendly conversation",
            backstory=dedent("""
                You are a friendly travel assistant. Collect these REQUIRED details:
                1. Origin city
                2. Destination  
                3. Departure date (YYYY-MM-DD)
                4. Return date
                5. Number of travelers
                6. Total budget (USD)
                7. Interests/activities
                
                After collecting all info, summarize and confirm with user.
                Never assume dates or traveler count - always ask.
            """),
            verbose=False,
            allow_delegation=False,
            llm=self.llm_conversation,
            tools=[],
            max_iter=5  # Reduced from 15
        )
    
    def preferences_extractor_agent(self) -> Agent:
        """Preferences Extractor - OPTIMIZED"""
        return Agent(
            role="Preferences Extractor",
            goal="Extract structured JSON from conversation",
            backstory=dedent("""
                Extract travel preferences from conversation into JSON:
                {
                    "origin": "city",
                    "destination": "city", 
                    "departure_date": "YYYY-MM-DD",
                    "return_date": "YYYY-MM-DD",
                    "num_adults": N,
                    "num_children": N,
                    "total_budget": N,
                    "interests": ["list"],
                    "travel_style": "budget/moderate/luxury"
                }
                
                Budget allocation: flights 35%, hotels 35%, activities 20%, meals 10%.
            """),
            verbose=False,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[],
            max_iter=3  # Reduced from 5
        )
    
    def flight_search_agent(self) -> Agent:
        """Flight Search Agent - OPTIMIZED"""
        return Agent(
            role="Flight Specialist",
            goal="Find flights within budget using city names",
            backstory=dedent("""
                Search for flights using Booking.com API.
                
                IMPORTANT:
                - Use CITY NAMES (not airport codes)
                - Use exact dates from extraction (YYYY-MM-DD)
                - Default: 1 adult, ECONOMY class
                
                Return top 5 options with price, airline, times.
                If API fails, use search_internet as backup.
            """),
            verbose=False,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[
                search_comprehensive_flights,
                search_round_trip_flights,
                search_internet,
                calculate
            ],
            max_iter=4  # Reduced from 8
        )
    
    def hotel_agent(self) -> Agent:
        """Hotel Search Agent - OPTIMIZED"""
        return Agent(
            role="Hotel Specialist",
            goal="Find hotels within budget",
            backstory=dedent("""
                Search for hotels using Booking.com API.
                
                PROCESS:
                1. Search destination for dest_id
                2. Search hotels with dates, adults, rooms
                3. Get reviews for top 3 hotels
                
                Return top 5 options with price/night, rating, amenities.
                Calculate: budget_per_night = accommodation_budget / nights.
            """),
            verbose=False,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[
                search_hotels_comprehensive,
                search_hotel_destination,
                search_hotels_by_dest_id,
                get_hotel_reviews,
                search_internet,
                calculate
            ],
            max_iter=5  # Reduced from 12
        )
    
    def attraction_agent(self) -> Agent:
        """Attractions Agent - OPTIMIZED"""
        return Agent(
            role="Activities Specialist",
            goal="Find attractions and restaurants within budget",
            backstory=dedent("""
                Find activities and dining for each day of the trip.
                
                For each day include:
                - Morning activity (name, cost, hours)
                - Lunch restaurant (name, cuisine, price range)
                - Afternoon activity
                - Dinner restaurant
                
                Track daily spending vs daily_budget.
                Mix free and paid activities.
            """),
            verbose=False,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[
                search_attractions,
                search_restaurants,
                search_internet,
                calculate
            ],
            max_iter=4  # Reduced from 10
        )
    
    def itinerary_coordinator_agent(self) -> Agent:
        """Itinerary Coordinator - OPTIMIZED"""
        return Agent(
            role="Itinerary Coordinator",
            goal="Create detailed day-by-day itinerary from all agent data",
            backstory=dedent("""
                Synthesize data from all agents into a complete itinerary.
                
                OUTPUT STRUCTURE:
                1. TOP 3 FLIGHTS (price, times, airline)
                2. TOP 3 HOTELS (price/night, rating, location)
                3. DAILY ITINERARY for each day:
                   - Morning: Activity + Lunch
                   - Afternoon: Activity + Dinner
                   - Daily cost total
                4. BUDGET SUMMARY (total vs allocated)
                
                Use ONLY real data from other agents.
                Calculate totals with calculator tool.
            """),
            verbose=False,
            allow_delegation=False,
            llm=self.llm_coordinator,
            tools=[calculate, search_internet],
            max_iter=5  # Reduced from 15
        )
