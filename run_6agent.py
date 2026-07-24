"""
6-Agent Execution Runner — Shows each agent's call and output live.

Usage: python run_6agent.py
   Or: python run_6agent.py "Plan my own trip..."
"""

import sys, time, json, re, os, logging, warnings
warnings.filterwarnings("ignore", category=UserWarning, module="opentelemetry")
warnings.filterwarnings("ignore", category=UserWarning, module="crewai")
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"
sys.stdout.reconfigure(encoding="utf-8")
from textwrap import dedent
from dotenv import load_dotenv
load_dotenv(override=True)

from crewai import Agent, Task, Crew, Process

logging.getLogger("opentelemetry").setLevel(logging.ERROR)

from src.tools import (
    search_round_trip_flights, search_comprehensive_flights,
    search_hotels_comprehensive, search_accommodations_with_location,
    search_hotel_destination, search_hotels_by_dest_id,
    get_hotel_reviews, get_attractions_near_hotel,
    search_internet, search_attractions, search_restaurants,
    calculate
)

SAMPLE_INPUT = sys.argv[1] if len(sys.argv) > 1 else "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
llm_calls = 0
total_start = time.time()


def sprint(text):
    print(text)


def section(title):
    sprint(f"\n{'='*70}")
    sprint(f"  {title}")
    sprint(f"{'='*70}")


def step(label):
    sprint(f"\n  ▶ {label}")


def show(name, content):
    sprint(f"\n  ┌─ {name} {'─'*50}")
    for line in str(content).split("\n"):
        sprint(f"  │ {line}")
    sprint(f"  └{'─'*60}")


# ============================================================
# AGENT DEFINITIONS
# ============================================================

extractor = Agent(
    role="Travel Preferences Extractor",
    goal="Extract structured JSON from user input",
    backstory="Extract travel preferences from user input into JSON format with origin, destination, dates, budget, interests.",
    verbose=False, allow_delegation=False, llm=model, tools=[], max_iter=3, max_rpm=5
)

flight_agent = Agent(
    role="Flight Search Specialist",
    goal="Find flights within budget using search tools",
    backstory="Search for flights using the comprehensive flight search tool. Return top 5 real options with airline, price, times.",
    verbose=False, allow_delegation=False, llm=model,
    tools=[search_comprehensive_flights, search_round_trip_flights, search_internet, calculate],
    max_iter=8, max_rpm=5
)

hotel_agent = Agent(
    role="Hotel Search Specialist",
    goal="Find hotels within budget using search tools",
    backstory="Search for hotels using Booking.com tools. Return top 5 with price/night, rating, amenities.",
    verbose=False, allow_delegation=False, llm=model,
    tools=[search_hotels_comprehensive, search_accommodations_with_location,
           search_hotel_destination, search_hotels_by_dest_id,
           get_hotel_reviews, get_attractions_near_hotel, search_internet, calculate],
    max_iter=10, max_rpm=5
)

attraction_agent = Agent(
    role="Activities Specialist",
    goal="Find attractions and restaurants within budget",
    backstory="Find activities and dining for each day. Use search_attractions, search_restaurants tools.",
    verbose=False, allow_delegation=False, llm=model,
    tools=[search_attractions, search_restaurants, search_internet, calculate],
    max_iter=10, max_rpm=5
)

coordinator = Agent(
    role="Itinerary Coordinator",
    goal="Create day-by-day itinerary from all agent data",
    backstory="Synthesize data from flight, hotel, and attraction agents into a complete day-by-day itinerary.",
    verbose=False, allow_delegation=True, llm=model,
    tools=[calculate, search_internet, search_attractions, search_restaurants],
    max_iter=15, max_rpm=5
)


# ============================================================
# EXECUTION
# ============================================================

section("6-AGENT EXECUTION RUNNER")
sprint(f"\n  Input: {SAMPLE_INPUT}")
sprint(f"  Running 5 agents one-by-one, showing live outputs...\n")


# ---- AGENT 1: EXTRACTOR ----
section("AGENT 1/5: PREFERENCES EXTRACTOR")
step("Extracting preferences from user input...")

extract_task = Task(
    description=dedent(f"""
        Extract travel preferences from this user input into JSON format:
        User: {SAMPLE_INPUT}
        Return JSON with: origin, destination, departure_date, return_date,
        trip_duration, total_budget, num_adults(1), num_children(0),
        interests[], travel_style, budget_breakdown.
    """),
    expected_output='{"origin":"","destination":"","departure_date":"","return_date":"","trip_duration":0,"total_budget":0,"num_adults":1,"num_children":0,"interests":[],"travel_style":"","budget_breakdown":{"flights":0,"accommodation":0,"activities":0,"meals":0}}',
    agent=extractor
)
extract_crew = Crew(agents=[extractor], tasks=[extract_task], process=Process.sequential, verbose=False)
extraction_result = str(extract_crew.kickoff())
llm_calls += 1
show("EXTRACTOR OUTPUT", extraction_result)


# ---- AGENT 2: FLIGHT ----
section("AGENT 2/5: FLIGHT SEARCH SPECIALIST")
step("Calling MCP tools: search_round_trip_flights() / search_comprehensive_flights()")

flight_t = Task(
    description=dedent("""
        Search for REAL flights using the comprehensive flight search tools.
        Use extraction context for origin, destination, departure/return dates.
        Return top 5 real flight options with airline, price, times, duration.
        DO NOT make up data — use the search tools provided.
    """),
    expected_output="Top 5 real flight options with complete pricing and schedule",
    agent=flight_agent,
    context=[extract_task]
)
flight_crew = Crew(agents=[flight_agent], tasks=[flight_t], process=Process.sequential, verbose=False)
flight_result = str(flight_crew.kickoff())
llm_calls += 1
show("FLIGHT AGENT OUTPUT", flight_result)


# ---- AGENT 3: HOTEL ----
section("AGENT 3/5: HOTEL SEARCH SPECIALIST")
step("Calling MCP tools: search_hotel_destination() / search_hotels_by_dest_id() / search_hotels_comprehensive()")

hotel_t = Task(
    description=dedent("""
        Search for REAL hotels using the hotel search tools.
        Use extraction context for destination, dates, budget.
        Return top 5 real hotel options with price, rating, amenities.
        DO NOT make up data — use the search tools provided.
    """),
    expected_output="Top 5 real hotel options with pricing and reviews",
    agent=hotel_agent,
    context=[extract_task]
)
hotel_crew = Crew(agents=[hotel_agent], tasks=[hotel_t], process=Process.sequential, verbose=False)
hotel_result = str(hotel_crew.kickoff())
llm_calls += 1
show("HOTEL AGENT OUTPUT", hotel_result)


# ---- AGENT 4: ATTRACTION ----
section("AGENT 4/5: ACTIVITIES SPECIALIST")
step("Calling MCP tools: search_attractions() / search_restaurants()")

attraction_t = Task(
    description=dedent("""
        Find REAL attractions and restaurants using the search tools.
        Use extraction context for destination, interests, trip duration.
        Provide daily suggestions. DO NOT make up data.
    """),
    expected_output="Daily attraction and restaurant recommendations",
    agent=attraction_agent,
    context=[extract_task]
)
attraction_crew = Crew(agents=[attraction_agent], tasks=[attraction_t], process=Process.sequential, verbose=False)
attraction_result = str(attraction_crew.kickoff())
llm_calls += 1
show("ATTRACTION AGENT OUTPUT", attraction_result)


# ---- AGENT 5: COORDINATOR ----
section("AGENT 5/5: ITINERARY COORDINATOR")
step("Receiving A2A context from all 4 previous agents...")
step("Assembling final itinerary...")

coord_t = Task(
    description=dedent("""
        Synthesize all data from flight, hotel, and attraction search tasks
        into a complete day-by-day itinerary.
        WRITE ALL DAYS INDIVIDUALLY — no shortcuts.
        Include: flight analysis, hotel analysis, daily schedule for EVERY day,
        budget breakdown, travel tips.
    """),
    expected_output="Complete itinerary with all days, budget, and tips",
    agent=coordinator,
    context=[extract_task, flight_t, hotel_t, attraction_t]
)
coord_crew = Crew(
    agents=[coordinator], tasks=[coord_t],
    process=Process.sequential, verbose=False
)
result = str(coord_crew.kickoff())
llm_calls += 1
show("COORDINATOR OUTPUT — FINAL ITINERARY", result)


# ---- SUMMARY ----
total_time = time.time() - total_start
section("SUMMARY")
sprint(f"  Total time:  {total_time:.1f}s")
sprint(f"  LLM calls:   {llm_calls}")
sprint(f"  Agents:      5 executed sequentially")
sprint(f"  MCP calls:   varies (flight + hotel + attraction tools)")
sprint(f"  A2A chain:   extractor → flight → hotel → attraction → coordinator")
