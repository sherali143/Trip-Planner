"""
3-Agent Execution Runner — Shows each phase's calls and outputs live.

Usage: python run_3agent.py
   Or: python run_3agent.py "Plan my own trip..."
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
from src.tools.mcp_tools import _call_fly_scraper_api
from src.server.mcp_server import search_hotels_comprehensive, search_attractions, search_restaurants

SAMPLE_INPUT = sys.argv[1] if len(sys.argv) > 1 else "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
llm_calls = 0
total_start = time.time()


def _make_extractor():
    return Agent(
        role="Travel Preferences Extractor",
        goal="Extract structured JSON from user input",
        backstory="Extract travel preferences from user input into JSON format with origin, destination, dates, budget, interests.",
        verbose=False, allow_delegation=False, llm=model, tools=[], max_iter=3, max_rpm=5
    )


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
    sprint(f"  │ (truncated to 20 lines)")
    lines = str(content).split("\n")
    for line in lines[:20]:
        sprint(f"  │ {line}")
    if len(lines) > 20:
        sprint(f"  │ ... ({len(lines)-20} more lines)")
    sprint(f"  └{'─'*60}")




extractor_agent = _make_extractor()

section("3-AGENT EXECUTION RUNNER")
sprint(f"\n  Input: {SAMPLE_INPUT}")
sprint(f"  3 phases: Extractor → Direct APIs → Coordinator")


# ============================================================
# PHASE 1: EXTRACTION
# ============================================================
section("PHASE 1/3: PREFERENCES EXTRACTOR")
step("1 LLM call — parsing user request into JSON...")

extract_task = Task(
    description=dedent(f"""
        Extract travel preferences from this user request into JSON format:
        User: {SAMPLE_INPUT}
        Return JSON with: origin, destination, departure_date, return_date,
        trip_duration, total_budget, num_adults(1), num_children(0),
        interests[], travel_style, budget_breakdown.
        If trip_duration given but no return_date, calculate return_date.
    """),
    expected_output='{"origin":"","destination":"","departure_date":"","return_date":"","trip_duration":0,"total_budget":0,"num_adults":1,"num_children":0,"interests":[],"travel_style":"","budget_breakdown":{"flights":0,"accommodation":0,"activities":0,"meals":0}}',
    agent=extractor_agent
)
extract_crew = Crew(
    agents=[extractor_agent],
    tasks=[extract_task],
    process=Process.sequential, verbose=False
)
extraction_result = str(extract_crew.kickoff())
llm_calls += 1
show("EXTRACTOR OUTPUT", extraction_result)

# Parse
try:
    json_match = re.search(r'\{.*"origin".*"destination".*\}', extraction_result, re.DOTALL)
    prefs = json.loads(json_match.group(0)) if json_match else {}
except Exception:
    prefs = {}

origin = prefs.get("origin", "")
destination = prefs.get("destination", "")
departure_date = prefs.get("departure_date", "")
return_date = prefs.get("return_date", "")
trip_duration = prefs.get("trip_duration", 5)
num_adults = prefs.get("num_adults", 1)
total_budget = prefs.get("total_budget", 0) or 0
interests_raw = prefs.get("interests", [])
interests = ", ".join(interests_raw) if isinstance(interests_raw, list) else str(interests_raw or "")
bd = prefs.get("budget_breakdown", {})
flight_budget = bd.get("flights", total_budget * 0.35) or total_budget * 0.35
accommodation_budget = bd.get("accommodation", total_budget * 0.35) or total_budget * 0.35
meals_budget = bd.get("meals", total_budget * 0.10) or total_budget * 0.10
budget_per_night = accommodation_budget / trip_duration if trip_duration > 0 else accommodation_budget
budget_per_meal = meals_budget / (trip_duration * 2) if trip_duration > 0 else meals_budget

step(f"Parsed: {destination} | {departure_date}→{return_date} | ${total_budget}")


# ============================================================
# PHASE 2: DIRECT API CALLS
# ============================================================
section("PHASE 2/3: DIRECT API CALLS (0 LLM calls)")
step("Calling _call_fly_scraper_api() → MCP Server: fly-scraper")

flights_data = ""
if origin and destination and departure_date:
    try:
        flights_data = _call_fly_scraper_api(origin, destination, departure_date, return_date, num_adults, flight_budget)
        show("FLIGHT API RESPONSE", flights_data)
    except Exception as e:
        flights_data = json.dumps({"success": False, "error": str(e)})
        sprint(f"\n  ⚠ Flight API error: {e}")
else:
    sprint("  ⏭ Skipped (missing data)")

step("Calling search_hotels_comprehensive() → MCP Server: Booking.com")
hotels_data = ""
if destination and departure_date and return_date:
    try:
        hotels_data = search_hotels_comprehensive(destination, departure_date, return_date, budget_per_night, num_adults, 1)
        show("HOTEL API RESPONSE", hotels_data)
    except Exception as e:
        hotels_data = json.dumps({"error": "Hotel search failed", "success": False})
        sprint(f"\n  ⚠ Hotel API error: {e}")
else:
    sprint("  ⏭ Skipped (missing data)")

step("Calling search_attractions() → MCP Server: Serper (Google Search)")
attractions_data = ""
if destination and interests:
    try:
        attractions_data = search_attractions(destination, interests, trip_duration)
        show("ATTRACTIONS API RESPONSE", attractions_data)
    except Exception as e:
        attractions_data = json.dumps({"error": "Attraction search failed", "success": False})
        sprint(f"\n  ⚠ Attractions API error: {e}")
else:
    sprint("  ⏭ Skipped (missing data)")

step("Calling search_restaurants() → MCP Server: Serper (Google Search)")
restaurants_data = ""
if destination:
    try:
        restaurants_data = search_restaurants(destination, interests, budget_per_meal)
        show("RESTAURANTS API RESPONSE", restaurants_data)
    except Exception as e:
        restaurants_data = json.dumps({"error": "Restaurant search failed", "success": False})
        sprint(f"\n  ⚠ Restaurants API error: {e}")
else:
    sprint("  ⏭ Skipped (missing data)")


# ============================================================
# PHASE 3: COORDINATOR
# ============================================================
section("PHASE 3/3: ITINERARY COORDINATOR")
step("Feeding all data as A2A context...")
step("Assembling final itinerary (1 LLM call)...")

data_block = f"""
PREFERENCES:
{json.dumps(prefs, indent=2)}

FLIGHTS:
{flights_data[:3000] if isinstance(flights_data, str) else str(flights_data)[:3000]}

HOTELS:
{hotels_data[:3000] if isinstance(hotels_data, str) else str(hotels_data)[:3000]}

ATTRACTIONS:
{attractions_data[:3000] if isinstance(attractions_data, str) else str(attractions_data)[:3000]}

RESTAURANTS:
{restaurants_data[:3000] if isinstance(restaurants_data, str) else str(restaurants_data)[:3000]}
"""

coordinator = Agent(
    role="Itinerary Coordinator",
    goal="Create day-by-day itinerary from the provided data only",
    backstory="You synthesize flight, hotel, attraction, and restaurant data into a complete itinerary. Do NOT search for additional information.",
    verbose=False, allow_delegation=False, llm=model, tools=[], max_iter=3, max_rpm=5
)

coord_task = Task(
    description=dedent(f"""
        Create a complete day-by-day itinerary using ONLY the data below.
        Do NOT search for any additional information.
        {data_block}
        Requirements:
        - Day-by-day schedule for each day
        - Flight recommendations from flights data
        - Hotel recommendations from hotels data
        - Activities from attractions data
        - Restaurants from restaurants data
        - Budget breakdown
        - Travel tips
    """),
    expected_output="Complete day-by-day itinerary with all sections",
    agent=coordinator
)
coord_crew = Crew(
    agents=[coordinator], tasks=[coord_task],
    process=Process.sequential, verbose=False
)
result = str(coord_crew.kickoff())
llm_calls += 1
show("COORDINATOR OUTPUT — FINAL ITINERARY", result)


# ============================================================
# SUMMARY
# ============================================================
total_time = time.time() - total_start
section("SUMMARY")
sprint(f"  Total time:  {total_time:.1f}s")
sprint(f"  LLM calls:   {llm_calls}")
sprint(f"  API calls:   4 (flights, hotels, attractions, restaurants)")
sprint(f"  A2A chain:   extractor → coordinator (data fed as context block)")