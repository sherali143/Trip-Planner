"""
Baseline: 6-Agent Architecture (per proposal)
- Conversational + Extractor + Flight Search + Hotel + Attraction + Coordinator
- Sequential CrewAI execution with context chaining between all agents
- Takes scenario input directly (no interactive conversation)
"""

import os, uuid, time, json, re
from textwrap import dedent
from crewai import Agent, Task, Crew, Process

from src.tools import (
    search_round_trip_flights, search_comprehensive_flights,
    search_hotels_comprehensive, search_accommodations_with_location,
    search_hotel_destination, search_hotels_by_dest_id,
    get_hotel_reviews, get_attractions_near_hotel,
    search_internet, search_attractions, search_restaurants,
    calculate
)


class BaselineAgents:
    def __init__(self):
        model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
        self.llm = model

    def preferences_extractor_agent(self):
        return Agent(
            role="Travel Preferences Extractor",
            goal="Extract structured JSON from conversation transcript",
            backstory=dedent("""
                Extract travel preferences from user input into JSON format.
                Fields: origin, destination, departure_date, return_date, trip_duration,
                total_budget, num_adults, num_children, interests, travel_style.
                Allocate budget: flights 35%, hotels 35%, activities 20%, meals 10%.
            """),
            verbose=True, allow_delegation=False, llm=self.llm, tools=[], max_iter=3, max_rpm=5
        )

    def flight_search_agent(self):
        return Agent(
            role="Flight Search Specialist",
            goal="Find flights within budget using search tools",
            backstory=dedent("""
                Search for flights using the comprehensive flight search tool.
                Use origin, destination, dates from preferences. Return top 5 options.
                Use tools to find REAL flight data, not made-up information.
            """),
            verbose=False, allow_delegation=False, llm=self.llm,
            tools=[search_comprehensive_flights, search_round_trip_flights, search_internet, calculate],
            max_iter=8, max_rpm=5
        )

    def hotel_agent(self):
        return Agent(
            role="Hotel Search Specialist",
            goal="Find hotels within budget using search tools",
            backstory=dedent("""
                Search for hotels using Booking.com tools.
                Use destination, dates, budget from extraction.
                Return top 5 with price/night, rating, amenities.
                Use hotel search tools to find REAL data.
            """),
            verbose=False, allow_delegation=False, llm=self.llm,
            tools=[search_hotels_comprehensive, search_accommodations_with_location,
                   search_hotel_destination, search_hotels_by_dest_id,
                   get_hotel_reviews, get_attractions_near_hotel, search_internet, calculate],
            max_iter=10, max_rpm=5
        )

    def attraction_agent(self):
        return Agent(
            role="Activities Specialist",
            goal="Find attractions and restaurants within budget",
            backstory=dedent("""
                Find activities and dining for each day of the trip.
                For each day include: morning activity, lunch, afternoon activity, dinner.
                Use search_attractions, search_restaurants tools to find REAL data.
            """),
            verbose=False, allow_delegation=False, llm=self.llm,
            tools=[search_attractions, search_restaurants, search_internet, calculate],
            max_iter=10, max_rpm=5
        )

    def itinerary_coordinator_agent(self):
        return Agent(
            role="Itinerary Coordinator",
            goal="Create day-by-day itinerary from all agent data",
            backstory=dedent("""
                Synthesize data from flight, hotel, and attraction agents into a
                complete day-by-day itinerary. Include ALL days individually.
                Include flight analysis, hotel analysis, daily schedule,
                budget breakdown, and travel tips. No shortcuts on day count.
            """),
            verbose=False, allow_delegation=True, llm=self.llm,
            tools=[calculate, search_internet, search_attractions, search_restaurants],
            max_iter=15, max_rpm=5
        )


def plan_trip_baseline(user_input: str) -> dict:
    """Run the 6-agent baseline. Returns metrics dict."""
    start = time.time()
    llm_calls = 0
    errors = []

    agents = BaselineAgents()
    cid = str(uuid.uuid4())

    try:
        # PHASE 1: Extraction
        t1 = time.time()
        extract_task = Task(
            description=dedent(f"""
                Extract travel preferences from this user input into JSON format:
                User: {user_input}
                
                Return JSON with: origin, destination, departure_date, return_date,
                trip_duration, total_budget, num_adults(1), num_children(0),
                interests[], travel_style, budget_breakdown.
                
                If trip_duration given but no return_date, calculate: return = departure + duration.
                Default: 1 adult, 0 children.
            """),
            expected_output="""{"origin":"","destination":"","departure_date":"","return_date":"","trip_duration":0,"total_budget":0,"num_adults":1,"num_children":0,"interests":[],"travel_style":"","budget_breakdown":{"flights":0,"accommodation":0,"activities":0,"meals":0}}""",
            agent=agents.preferences_extractor_agent()
        )

        extract_crew = Crew(
            agents=[agents.preferences_extractor_agent()],
            tasks=[extract_task],
            process=Process.sequential, verbose=True
        )
        extraction_result = str(extract_crew.kickoff())
        llm_calls += 1
        t2 = time.time()
    except Exception as e:
        return {"arch": "baseline_6agent", "success": False, "error": str(e),
                "latency": time.time() - start, "llm_calls": 0}

    try:
        # PHASE 2: Flight + Hotel + Attraction + Coordinator (sequential)
        flight_t = Task(
            description=dedent("""
                Search for REAL flights using the comprehensive flight search tools.
                Use extraction context for origin, destination, departure/return dates.
                Return top 5 real flight options with airline, price, times, duration.
                DO NOT make up data - use the search tools provided.
            """),
            expected_output="Top 5 real flight options with complete pricing and schedule",
            agent=agents.flight_search_agent(),
            context=[extract_task]
        )

        hotel_t = Task(
            description=dedent("""
                Search for REAL hotels using the hotel search tools.
                Use extraction context for destination, dates, budget.
                Return top 5 real hotel options with price, rating, amenities.
                DO NOT make up data - use the search tools provided.
            """),
            expected_output="Top 5 real hotel options with pricing and reviews",
            agent=agents.hotel_agent(),
            context=[extract_task]
        )

        attraction_t = Task(
            description=dedent("""
                Find REAL attractions and restaurants using the search tools.
                Use extraction context for destination, interests, trip duration.
                Provide daily suggestions. DO NOT make up data.
            """),
            expected_output="Daily attraction and restaurant recommendations",
            agent=agents.attraction_agent(),
            context=[extract_task]
        )

        coord_t = Task(
            description=dedent(f"""
                Synthesize all data from flight, hotel, and attraction search tasks
                into a complete day-by-day itinerary.
                WRITE ALL DAYS INDIVIDUALLY - no shortcuts.
                Include: flight analysis, hotel analysis, daily schedule for EVERY day,
                budget breakdown, travel tips.
            """),
            expected_output="Complete itinerary with all days, budget, and tips",
            agent=agents.itinerary_coordinator_agent(),
            context=[extract_task, flight_t, hotel_t, attraction_t]
        )

        main_crew = Crew(
            agents=[agents.flight_search_agent(), agents.hotel_agent(),
                    agents.attraction_agent(), agents.itinerary_coordinator_agent()],
            tasks=[flight_t, hotel_t, attraction_t, coord_t],
            process=Process.sequential, verbose=True
        )
        result = main_crew.kickoff()
        llm_calls += 4
    except Exception as e:
        errors.append(str(e))
        return {"arch": "baseline_6agent", "success": False,
                "extraction": extraction_result[:300], "error": str(e),
                "latency": time.time() - start, "llm_calls": llm_calls}

    total = time.time() - start
    return {
        "arch": "baseline_6agent",
        "success": True,
        "result": str(result),
        "extraction": extraction_result[:500],
        "latency": total,
        "llm_calls": llm_calls,
        "phase1_s": round(t2 - t1, 1),
        "phase2_s": round(total - (t2 - t1), 1),
        "errors": errors
    }
