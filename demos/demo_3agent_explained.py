"""
Educational Demo: 3-Agent + Direct API Architecture with MCP + A2A Explanations
Shows how this architecture differs from 6-agent — replaces search agents with
direct Python API calls while keeping the same MCP servers underneath.

Usage: python demo_3agent_explained.py
"""

import sys, time, json, re, os, logging, warnings
warnings.filterwarnings("ignore", category=UserWarning, module="opentelemetry")
warnings.filterwarnings("ignore", category=UserWarning, module="crewai")
sys.stdout.reconfigure(encoding="utf-8")
from textwrap import dedent
from dotenv import load_dotenv
load_dotenv(override=True)

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"

from crewai import Agent, Task, Crew, Process

logging.getLogger("opentelemetry").setLevel(logging.ERROR)
# This script lives in a subdirectory, so the project root is not on
# sys.path when it is run directly. Add it before importing src/comparison.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from src.agents import TripPlannerAgents
from src.tools.mcp_tools import _call_fly_scraper_api
from src.server.mcp_server import search_hotels_comprehensive, search_attractions, search_restaurants

from src.core.llm_metrics import recorder

SAMPLE_INPUT = "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

# LLM usage is measured by LiteLLM callbacks, not counted by hand: the
# previous "llm_calls += 8  # simulated" style printed numbers that
# contradicted the measured results in comparison/results/.
_llm_session = recorder.start("demo_3agent_explained.py")
total_start = time.time()
model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")


def sprint(text):
    print(text)


def section(title):
    sprint(f"\n{'='*70}")
    sprint(f"  {title}")
    sprint(f"{'='*70}")


def subsection(title):
    sprint(f"\n{'-'*70}")
    sprint(f"  {title}")
    sprint(f"{'-'*70}")


section("3-AGENT + DIRECT API ARCHITECTURE — EXPLAINED STEP-BY-STEP")
sprint(f"\n  Input: {SAMPLE_INPUT}")
sprint(f"\n  Same MCP servers, same APIs — but NO intermediate search agents.")
sprint(f"  The 3 search agents are REPLACED by direct Python function calls.")
sprint(f"  This removes 3 LLM calls and ~80% of the latency.")

sprint(f"\n  Architecture Comparison:")
sprint(f"  6-Agent:  Extractor → Flight Agent → Hotel Agent → Attr. Agent → Coordinator")
sprint(f"  3-Agent:  Extractor → Direct APIs (flights, hotels, attractions, restaurants) → Coordinator")
sprint(f"            ↓                      ↓                              ↓")
sprint(f"   LLM calls:    1               0 (pure functions)              1")
sprint(f"            Total: 2 LLM calls (vs 5 in 6-agent)")


# ============================================================
# PHASE 1: EXTRACTION
# ============================================================

section("PHASE 1: PREFERENCES EXTRACTOR")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Travel Preferences Extractor")
sprint("  Tools:      NONE — same as 6-agent version")
sprint("  LLM call:   1 — parses user request into structured JSON")
sprint("")
sprint("  The extractor works IDENTICALLY in both architectures.")
sprint("  No MCP calls, no A2A context (first agent).")

subsection("EXECUTING...")

agents_class = TripPlannerAgents()
t0 = time.time()
extractor_agent = agents_class.preferences_extractor_agent()
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
t1 = time.time()

subsection("EXTRACTION OUTPUT")
sprint(f"\n{extraction_result}\n")
sprint(f"  Latency: {t1-t0:.1f}s | LLM calls: 1")

# Parse extraction
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

# ============================================================
# MCP + A2A EXPLANATION FOR 3-AGENT
# ============================================================

section("KEY DIFFERENCE: DIRECT API CALLS vs AGENT-BASED SEARCH")

sprint("")
sprint("  6-Agent Flow (before):                             3-Agent Flow (now):")
sprint("  ┌──────────────────┐                               ┌──────────────────┐")
sprint("  │  EXTRACTOR       │                               │  EXTRACTOR       │")
sprint("  └────────┬─────────┘                               └────────┬─────────┘")
sprint("           │ A2A context                                      │ JSON output")
sprint("           ▼                                                   ▼")
sprint("  ┌──────────────────┐                               ┌──────────────────┐")
sprint("  │  FLIGHT AGENT    │  LLM decides → MCP tool       │  Python function  │")
sprint("  │  (CrewAI + LLM)  │  → fly-scraper API            │  _call_fly_       │")
sprint("  │  1 LLM call      │                               │  scraper_api()    │")
sprint("  └──────────────────┘                               │  0 LLM calls      │")
sprint("                                                      └──────────────────┘")
sprint("")
sprint("  Instead of: 'Agent thinks → decides to call tool →")
sprint("              calls MCP server → LLM reads result →")
sprint("              formats response'")
sprint("")
sprint("  We do:     'Python function → calls MCP server →")
sprint("              returns raw data directly'")
sprint("")
sprint("  Same MCP server. Same API calls. But ZERO LLM overhead.")
sprint("  The data goes DIRECTLY to the coordinator.")

# ============================================================
# PHASE 2: DIRECT API CALLS
# ============================================================

section("PHASE 2: DIRECT API CALLS (REPLACES 3 SEARCH AGENTS)")

subsection("CALLING FLIGHT API")
sprint("  Function:  _call_fly_scraper_api()")
sprint("  MCP Server: fly-scraper (same as 6-agent's Flight Agent would use)")
sprint("  Args:      origin={origin}, destination={destination}")
sprint(f"             dates={departure_date} → {return_date}")
sprint("  LLM calls: 0 (pure Python)")
sprint("  Status:    calling...")
flights_data = ""
if origin and destination and departure_date:
    try:
        flights_data = _call_fly_scraper_api(origin, destination, departure_date, return_date, num_adults, flight_budget)
        sprint("  Result:    ✓ retrieved")
    except Exception as e:
        flights_data = json.dumps({"success": False, "error": str(e)})
        sprint(f"  Result:    ⚠ {e}")
else:
    sprint("  Result:    ⏭ skipped (missing origin/destination/date)")

subsection("CALLING HOTEL API")
sprint("  Function:  search_hotels_comprehensive()")
sprint("  MCP Server: Booking.com (same as 6-agent's Hotel Agent would use)")
sprint("  Args:      destination={destination}")
sprint("             dates={departure_date} → {return_date}")
sprint(f"             max_price={budget_per_night:.0f}/night")
sprint("  LLM calls: 0 (pure Python)")
sprint("  Status:    calling...")
hotels_data = ""
if destination and departure_date and return_date:
    try:
        hotels_data = search_hotels_comprehensive(destination, departure_date, return_date, budget_per_night, num_adults, 1)
        sprint("  Result:    ✓ retrieved")
    except Exception as e:
        hotels_data = json.dumps({"error": "Hotel search failed", "success": False})
        sprint(f"  Result:    ⚠ {e}")
else:
    sprint("  Result:    ⏭ skipped")

subsection("CALLING ATTRACTIONS API")
sprint("  Function:  search_attractions()")
sprint("  MCP Server: Serper (Google Search)")
sprint("  Args:      destination={destination}, interests={interests}")
sprint("  LLM calls: 0 (pure Python)")
sprint("  Status:    calling...")
attractions_data = ""
if destination and interests:
    try:
        attractions_data = search_attractions(destination, interests, trip_duration)
        sprint("  Result:    ✓ retrieved")
    except Exception as e:
        attractions_data = json.dumps({"error": "Attraction search failed", "success": False})
        sprint(f"  Result:    ⚠ {e}")
else:
    sprint("  Result:    ⏭ skipped")

subsection("CALLING RESTAURANTS API")
sprint("  Function:  search_restaurants()")
sprint("  MCP Server: Serper (Google Search)")
sprint("  Args:      destination={destination}, interests={interests}")
sprint(f"             max_price={budget_per_meal:.0f}/meal")
sprint("  LLM calls: 0 (pure Python)")
sprint("  Status:    calling...")
restaurants_data = ""
if destination:
    try:
        restaurants_data = search_restaurants(destination, interests, budget_per_meal)
        sprint("  Result:    ✓ retrieved")
    except Exception as e:
        restaurants_data = json.dumps({"error": "Restaurant search failed", "success": False})
        sprint(f"  Result:    ⚠ {e}")
else:
    sprint("  Result:    ⏭ skipped")

t2 = time.time()

subsection("RAW API DATA (truncated)")
sprint(f"\n  Flights:      {str(flights_data)[:200]}...")
sprint(f"  Hotels:       {str(hotels_data)[:200]}...")
sprint(f"  Attractions:  {str(attractions_data)[:200]}...")
sprint(f"  Restaurants:  {str(restaurants_data)[:200]}...")
sprint(f"\n  Phase 2 latency: {t2-t1:.1f}s | LLM calls: 0")

# ============================================================
# PHASE 3: COORDINATOR
# ============================================================

section("PHASE 3: ITINERARY COORDINATOR")

subsection("HOW A2A WORKS HERE")
sprint("  In the 6-agent architecture, A2A means:")
sprint("    Extractor → Flight Agent → Hotel Agent → Attr. Agent → Coordinator")
sprint("    (each agent's output is context for the next)")
sprint("")
sprint("  In the 3-agent architecture, A2A means:")
sprint("    Extractor → Python APIs → Coordinator")
sprint("    (extraction JSON + raw API data are fed as context)")
sprint("")
sprint("  The coordinator receives ALL data as a single text block:")
sprint("  • Extracted preferences (JSON)")
sprint("  • Flight data (raw API response)")
sprint("  • Hotel data (raw API response)")
sprint("  • Attractions data (raw API response)")
sprint("  • Restaurant data (raw API response)")
sprint("")
sprint("  No tools, no delegation — just pure assembly.")

subsection("EXECUTING COORDINATOR...")

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
        - Day-by-day schedule for each day of the trip
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
    agents=[coordinator],
    tasks=[coord_task],
    process=Process.sequential, verbose=False
)
result = str(coord_crew.kickoff())
t3 = time.time()

subsection("FINAL ITINERARY OUTPUT")
sprint(f"\n{result}\n")

# ============================================================
# SUMMARY
# ============================================================

total_time = time.time() - total_start

section("ARCHITECTURE RECAP — MCP & A2A FLOW DIAGRAM")

sprint("")
sprint("  ┌──────────────────┐")
sprint("  │  USER INPUT      │")
sprint("  └────────┬─────────┘")
sprint("           │")
sprint("           ▼")
sprint("  ┌──────────────────┐     1 LLM call")
sprint("  │  EXTRACTOR       │─────────────────────────┐")
sprint("  │  (Agent)         │  Extracts JSON           │")
sprint("  └──────────────────┘                          │")
sprint("           │ JSON output                         │")
sprint("           ▼                                     │")
sprint("  ┌─────────────────────────────────────┐        │")
sprint("  │  DIRECT API CALLS (Python)          │        │")
sprint("  │  _call_fly_scraper_api(AUH, ...)    │        │")
sprint("  │    → MCP Server: fly-scraper        │        │")
sprint("  │  search_hotels_comprehensive(...)   │        │")
sprint("  │    → MCP Server: Booking.com        │        │")
sprint("  │  search_attractions(...)            │        │")
sprint("  │    → MCP Server: Serper             │        │")
sprint("  │  search_restaurants(...)            │        │")
sprint("  │    → MCP Server: Serper             │        │")
sprint("  │  0 LLM calls — pure functions       │        │")
sprint("  └─────────────────────────────────────┘        │")
sprint("           │ raw data                              │")
sprint("           ▼                                       │")
sprint("  ┌──────────────────┐                             │")
sprint("  │  COORDINATOR     │◄────────────────────────────┘")
sprint("  │  (Agent)         │  1 LLM call")
sprint("  └────────┬─────────┘")
sprint("           │")
sprint("           ▼")
sprint("  ┌──────────────────┐")
sprint("  │  FINAL           │")
sprint("  │  ITINERARY       │")
sprint("  └──────────────────┘")
sprint("")

section("METRICS")
sprint(f"  Total latency:      {total_time:.1f} seconds")
_m = recorder.stop().summary()
sprint(f"  LLM calls:   {_m['llm_calls']}  (measured, not estimated)")
sprint(f"  Tokens:      {_m['total_tokens']:,} (prompt {_m['prompt_tokens']:,} + output {_m['completion_tokens']:,})")
sprint(f"  Cost:        ${_m['cost_usd']:.5f}")
sprint(f"  API calls:          4 (flights, hotels, attractions, restaurants)")
sprint(f"  A2A transfers:      1 (extractor → coordinator)")
sprint(f"  Architecture:       3-Agent + Direct API (Python calls)")
sprint(f"")
sprint(f"  VS 6-Agent:")
sprint(f"  LLM calls:          2 vs 5 (60% reduction)")
sprint(f"  Latency:            ~33s vs ~170s (80% reduction)")
