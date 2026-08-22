"""
Agent definitions for the production pipeline.

Three agents, each of which exists because the step genuinely needs judgement:
understanding a free-text request, and assembling a coherent day-by-day plan
from retrieved data. Everything between those two — the actual data retrieval —
is deterministic and is done in plain Python rather than by an agent.

The six-agent variants used for the evaluation live in `comparison/`.
"""

from crewai import Agent
from textwrap import dedent

from trip_planner.core.budget import LEGACY_ALLOCATION as _DEFAULT_SPLIT
from trip_planner.core.gemini_compat import model_string

# Tools needed by the coordinator agent
from trip_planner.tools import (
    search_internet,
    search_attractions,
    search_restaurants,
    calculate
)

class TripPlannerAgents:
    """
    Trip Planner Agents with A2A Communication and MCP Tool Integration
    Only uses LLM for conversation + itinerary assembly.
    Flight/hotel/attraction data is fetched via direct API calls.
    """

    def __init__(self):
        model = model_string()

        self.llm_conversation = model
        self.llm_standard = model
        self.llm_coordinator = model

    def conversational_agent(self) -> Agent:
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
            max_iter=8,
            max_rpm=3
        )

    def preferences_extractor_agent(self) -> Agent:
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

                Budget allocation: if the user stated how to split their budget,
                use their split. Otherwise default to flights {DEFAULT_SPLIT}.
                The parts must sum to the total.
                Calculate return_date from departure + duration if not explicit.
                Defaults: 1 adult, 0 children if not specified.
            """).replace("{DEFAULT_SPLIT}", (
                f"{_DEFAULT_SPLIT['flights']:.0%}, hotels "
                f"{_DEFAULT_SPLIT['accommodation']:.0%}, activities "
                f"{_DEFAULT_SPLIT['activities']:.0%}, meals "
                f"{_DEFAULT_SPLIT['meals']:.0%}"
            )),
            verbose=True,
            allow_delegation=False,
            llm=self.llm_standard,
            tools=[],
            max_iter=3,
            max_rpm=3
        )

    def itinerary_coordinator_agent(self) -> Agent:
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
            max_iter=10,
            max_rpm=3
        )
