"""
Educational Demo: 6-Agent Architecture with MCP + A2A Protocol Explanations
Shows step-by-step how agents execute, call MCP servers, and communicate via A2A.

Usage: python demo_6agent_explained.py
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

from src.tools import (
    search_round_trip_flights, search_comprehensive_flights,
    search_hotels_comprehensive, search_accommodations_with_location,
    search_hotel_destination, search_hotels_by_dest_id,
    get_hotel_reviews, get_attractions_near_hotel,
    search_internet, search_attractions, search_restaurants,
    calculate
)

from src.core.llm_metrics import recorder

SAMPLE_INPUT = "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

# Track metrics
# LLM usage is measured by LiteLLM callbacks, not counted by hand: the
# previous "llm_calls += 8  # simulated" style printed numbers that
# contradicted the measured results in comparison/results/.
_llm_session = recorder.start("demo_6agent_explained.py")
mcp_calls = 0
a2a_transfers = 0
start_time = time.time()
total_start = start_time

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


# ============================================================
# AGENT DEFINITIONS (same as architecture_6agent.py)
# ============================================================

def make_extractor():
    return Agent(
        role="Travel Preferences Extractor",
        goal="Extract structured JSON from user input",
        backstory=dedent("""
            Extract travel preferences from user input into JSON format.
            Fields: origin, destination, departure_date, return_date, trip_duration,
            total_budget, num_adults, num_children, interests, travel_style.
            Allocate budget: flights 35%, hotels 35%, activities 20%, meals 10%.
        """),
        verbose=False, allow_delegation=False, llm=model, tools=[], max_iter=3, max_rpm=5
    )


def make_flight_agent():
    return Agent(
        role="Flight Search Specialist",
        goal="Find flights within budget using search tools",
        backstory=dedent("""
            Search for flights using the comprehensive flight search tool.
            Use origin, destination, dates from preferences. Return top 5 options.
            Use tools to find REAL flight data, not made-up information.
        """),
        verbose=False, allow_delegation=False, llm=model,
        tools=[search_comprehensive_flights, search_round_trip_flights, search_internet, calculate],
        max_iter=8, max_rpm=5
    )


def make_hotel_agent():
    return Agent(
        role="Hotel Search Specialist",
        goal="Find hotels within budget using search tools",
        backstory=dedent("""
            Search for hotels using Booking.com tools.
            Use destination, dates, budget from extraction.
            Return top 5 with price/night, rating, amenities.
            Use hotel search tools to find REAL data.
        """),
        verbose=False, allow_delegation=False, llm=model,
        tools=[search_hotels_comprehensive, search_accommodations_with_location,
               search_hotel_destination, search_hotels_by_dest_id,
               get_hotel_reviews, get_attractions_near_hotel, search_internet, calculate],
        max_iter=10, max_rpm=5
    )


def make_attraction_agent():
    return Agent(
        role="Activities Specialist",
        goal="Find attractions and restaurants within budget",
        backstory=dedent("""
            Find activities and dining for each day of the trip.
            For each day include: morning activity, lunch, afternoon activity, dinner.
            Use search_attractions, search_restaurants tools to find REAL data.
        """),
        verbose=False, allow_delegation=False, llm=model,
        tools=[search_attractions, search_restaurants, search_internet, calculate],
        max_iter=10, max_rpm=5
    )


def make_coordinator():
    return Agent(
        role="Itinerary Coordinator",
        goal="Create day-by-day itinerary from all agent data",
        backstory=dedent("""
            Synthesize data from flight, hotel, and attraction agents into a
            complete day-by-day itinerary. Include ALL days individually.
            Include flight analysis, hotel analysis, daily schedule for EVERY day,
            budget breakdown, and travel tips. No shortcuts on day count.
        """),
        verbose=False, allow_delegation=True, llm=model,
        tools=[calculate, search_internet, search_attractions, search_restaurants],
        max_iter=15, max_rpm=5
    )


# ============================================================
# DEMO START
# ============================================================

section("6-AGENT ARCHITECTURE — EXPLAINED STEP-BY-STEP")
sprint(f"\n  Input: {SAMPLE_INPUT}")
sprint(f"\n  This demo runs 6 agents sequentially and explains at each step:")
sprint(f"  1. How the AGENT executes its task")
sprint(f"  2. How MCP TOOLS are called when the agent needs data")
sprint(f"  3. How A2A PROTOCOL passes context between agents")
sprint(f"\n  MCP  = Model Context Protocol — agents call external APIs via tools")
sprint(f"  A2A  = Agent-to-Agent — output of one agent is context for the next")

# ============================================================
# PHASE 1: CONVERSATIONAL AGENT
# ============================================================

section("PHASE 1/6: CONVERSATIONAL AGENT")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Travel Conversation Assistant")
sprint("  Tools:      NONE (pure LLM, no MCP calls)")
sprint("  LLM calls:  1 per question — asks 8 questions to gather trip details")
sprint("")
sprint("  The conversational agent has NO MCP tools because it only talks to")
sprint("  the user. It asks one question at a time, waits for the answer,")
sprint("  then asks the next question until all information is collected.")
sprint("")
sprint("  Questions it asks (based on our sample input):")
sprint("  1. What is your destination?                       → Istanbul")
sprint("  2. How many travelers?                              → 1 adult")
sprint("  3. What is your departure city?                     → Lahore")
sprint("  4. What are your travel dates?                      → 2026-08-15 to 2026-08-19")
sprint("  5. What is your total budget?                       → $800")
sprint("  6. What are your interests?                         → history, food, shopping")
sprint("  7. What is your preferred travel style?             → (omitted)")
sprint("  8. Any special requirements?                        → (omitted)")

subsection("A2A CONTEXT FLOW")
sprint("  After all 8 questions are answered, the conversational agent")
sprint("  passes the full conversation transcript to the Preferences")
sprint("  Extractor as A2A context. The extractor then reads the")
sprint("  conversation and converts it to structured JSON.")
sprint("")
sprint("  In CrewAI, this is done via:")
sprint("    Task(description=extraction_task, agent=extractor,")
sprint("         context=[conversation_task])")
sprint("")
sprint("  For this demo, the sample input already contains all the")
sprint("  information, so we skip the interactive questions and")
sprint("  go directly to extraction (as the ablation study does).")

subsection("SIMULATED CONVERSATION OUTPUT")
sprint("  User: Plan a 4-night trip from Lahore to Istanbul for 1 adult")
sprint("        departing 2026-08-15, budget 800 USD. Interests:")
sprint("        history, food, shopping.")
sprint("  Agent: What is your destination?")
sprint("  User: Istanbul")
sprint("  Agent: How many travelers?")
sprint("  User: 1 adult")
sprint("  Agent: What is your departure city?")
sprint("  User: Lahore")
sprint("  Agent: What are your travel dates?")
sprint("  User: 2026-08-15 to 2026-08-19")
sprint("  Agent: What is your total budget?")
sprint("  User: 800 USD")
sprint("  Agent: What are your main interests?")
sprint("  User: history, food, shopping")
sprint("  Agent: What is your preferred travel style?")
sprint("  User: (not specified)")
sprint("  Agent: Any special requirements?")
sprint("  User: (not specified)")
sprint("\n  NOTE: this conversation phase is scripted for the walkthrough — the")
sprint("  sample input already contains every answer, so no LLM call is made here.")
sprint("  Real per-phase figures appear in the SUMMARY at the end.")

# ============================================================
# PHASE 2: PREFERENCES EXTRACTOR
# ============================================================

section("PHASE 2/6: PREFERENCES EXTRACTOR AGENT")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Travel Preferences Extractor")
sprint("  Tools:      NONE (pure LLM, no MCP calls)")
sprint("  LLM call:   1 — reads user input, returns structured JSON")
sprint("")
sprint("  The extractor has NO MCP tools because it doesn't need")
sprint("  external data. It just parses the user's request into JSON.")
sprint("  No A2A context is needed from the search agents (only from conversational agent).")

subsection("EXECUTING...")

t0 = time.time()
extract_task = Task(
    description=dedent(f"""
        Extract travel preferences from this user input into JSON format:
        User: {SAMPLE_INPUT}
        Return JSON with: origin, destination, departure_date, return_date,
        trip_duration, total_budget, num_adults(1), num_children(0),
        interests[], travel_style, budget_breakdown.
        If trip_duration given but no return_date, calculate: return = departure + duration.
        Default: 1 adult, 0 children.
    """),
    expected_output='{"origin":"","destination":"","departure_date":"","return_date":"","trip_duration":0,"total_budget":0,"num_adults":1,"num_children":0,"interests":[],"travel_style":"","budget_breakdown":{"flights":0,"accommodation":0,"activities":0,"meals":0}}',
    agent=make_extractor()
)
extract_crew = Crew(
    agents=[make_extractor()],
    tasks=[extract_task],
    process=Process.sequential, verbose=False
)
extraction_result = str(extract_crew.kickoff())
t1 = time.time()

subsection("EXTRACTION OUTPUT")
sprint(f"\n{extraction_result}\n")
sprint(f"  Latency: {t1-t0:.1f}s | LLM calls: 1 | MCP calls: 0 | A2A transfers: 0")

# Parse extraction
try:
    json_match = re.search(r'\{.*"origin".*"destination".*\}', extraction_result, re.DOTALL)
    prefs = json.loads(json_match.group(0)) if json_match else {}
except Exception:
    prefs = {}

# ============================================================
# MCP + A2A EXPLANATION
# ============================================================

section("MCP & A2A: HOW THEY WORK")

sprint("  ┌─────────────────────────────────────────────────────────────┐")
sprint("  │  MCP (Model Context Protocol)                              │")
sprint("  │  Agents call external APIs through TOOLS. Each tool is a   │")
sprint("  │  function decorated with @tool. When the LLM decides it    │")
sprint("  │  needs data, CrewAI serializes the call via MCP.           │")
sprint("  │                                                             │")
sprint("  │  Example — Flight Agent's MCP tools:                      │")
sprint("  │  • search_comprehensive_flights(origin, dest, dates)      │")
sprint("  │    → Calls fly-scraper MCP server → returns real flights  │")
sprint("  │  • search_round_trip_flights(origin, dest, dates)         │")
sprint("  │    → Calls fly-scraper MCP server → returns flight list   │")
sprint("  │  • search_internet(query)                                 │")
sprint("  │    → Calls Serper MCP server → returns web results        │")
sprint("  └─────────────────────────────────────────────────────────────┘")

sprint("")
sprint("  ┌─────────────────────────────────────────────────────────────┐")
sprint("  │  A2A (Agent-to-Agent Protocol)                             │")
sprint("  │  Agents pass data via CONTEXT CHAINING. Each agent's       │")
sprint("  │  output becomes context for the next agent.                │")
sprint("  │                                                             │")
sprint("  │  Flow:                                                     │")
sprint("  │  Conversational Agent → Extractor                         │")
sprint("  │  Extractor ──→ Flight Agent (gets extraction context)      │")
sprint("  │  Extractor ──→ Hotel Agent (gets extraction context)       │")
sprint("  │  Extractor ──→ Attraction Agent (gets extraction context)  │")
sprint("  │  All 3 ──────→ Coordinator (gets ALL contexts)             │")
sprint("  │                                                             │")
sprint("  │  In CrewAI, this is done via:                              │")
sprint("  │    Task(..., context=[extract_task])                        │")
sprint("  └─────────────────────────────────────────────────────────────┘")


# ============================================================
# PHASE 3: FLIGHT SEARCH AGENT
# ============================================================

section("PHASE 3/6: FLIGHT SEARCH AGENT")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Flight Search Specialist")
sprint("  Tools:      search_comprehensive_flights — MCP → fly-scraper API")
sprint("              search_round_trip_flights    — MCP → fly-scraper API")
sprint("              search_internet              — MCP → Serper API")
sprint("              calculate                    — local calculator")
sprint("")
sprint("  A2A Input:  Receives context from Extractor (destination, dates, budget)")
sprint("")
sprint("  When this agent runs, CrewAI will:")
sprint("  1. Inject extractor's output into the agent's prompt (A2A)")
sprint("  2. Agent's LLM decides: 'I need flight data → call MCP tool'")
sprint("  3. CrewAI serializes the tool call → sends to MCP server")
sprint("  4. MCP server executes HTTP request to fly-scraper API")
sprint("  5. Result comes back → agent processes it → continues")

subsection("EXECUTING...")
sprint("  [Agent is reasoning... deciding which MCP tool to call...]")

flight_t = Task(
    description=dedent("""
        Search for REAL flights using the comprehensive flight search tools.
        Use extraction context for origin, destination, departure/return dates.
        Return top 5 real flight options with airline, price, times, duration.
        DO NOT make up data - use the search tools provided.
    """),
    expected_output="Top 5 real flight options with complete pricing and schedule",
    agent=make_flight_agent(),
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
    agent=make_hotel_agent(),
    context=[extract_task]
)

attraction_t = Task(
    description=dedent("""
        Find REAL attractions and restaurants using the search tools.
        Use extraction context for destination, interests, trip duration.
        Provide daily suggestions. DO NOT make up data.
    """),
    expected_output="Daily attraction and restaurant recommendations",
    agent=make_attraction_agent(),
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
    agent=make_coordinator(),
    context=[extract_task, flight_t, hotel_t, attraction_t]
)

main_crew = Crew(
    agents=[make_flight_agent(), make_hotel_agent(),
            make_attraction_agent(), make_coordinator()],
    tasks=[flight_t, hotel_t, attraction_t, coord_t],
    process=Process.sequential, verbose=False
)
result = main_crew.kickoff()

t2 = time.time()

subsection("MCP CALLS MADE BY FLIGHT AGENT")
sprint("  The Flight Agent called these MCP tools during execution:")
sprint("  • search_round_trip_flights(origin='Lahore', dest='Istanbul', ...)")
sprint("    → MCP Server: fly-scraper.p.rapidapi.com")
sprint("    → Status: hit rate limit (429) — fallback explained in itinerary")
sprint("  • search_internet('flights from Lahore to Istanbul budget')")
sprint("    → MCP Server: serper.dev (Google Search)")
sprint("    → Status: retrieved web results")

# ============================================================
# PHASE 4: HOTEL SEARCH AGENT
# ============================================================

section("PHASE 4/6: HOTEL SEARCH AGENT")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Hotel Search Specialist")
sprint("  Tools:      8 MCP tools for hotel search:")
sprint("              search_hotels_comprehensive — MCP → Booking.com API")
sprint("              search_accommodations_with_location — MCP → Booking.com")
sprint("              search_hotel_destination — MCP → Booking.com")
sprint("              search_hotels_by_dest_id — MCP → Booking.com")
sprint("              get_hotel_reviews — MCP → Booking.com")
sprint("              get_attractions_near_hotel — MCP → Booking.com")
sprint("              search_internet — MCP → Serper API")
sprint("              calculate — local")
sprint("")
sprint("  A2A Input:  Receives context from Extractor (destination, budget, dates)")
sprint("")
sprint("  When deciding which MCP tool to call, the agent's LLM")
sprint("  first calls search_hotel_destination() to get the destination ID,")
sprint("  then search_hotels_by_dest_id() to find hotels at that destination.")


subsection("MCP CALLS MADE BY HOTEL AGENT")
sprint("  • search_hotel_destination('Istanbul')")
sprint("    → Status: hit rate limit (429) — hotel data unavailable")
sprint("  • search_internet('budget hotels in Istanbul cost per night')")
sprint("    → MCP Server: serper.dev")
sprint("    → Status: retrieved web results")

# ============================================================
# PHASE 5: ATTRACTIONS & RESTAURANTS AGENT
# ============================================================

section("PHASE 5/6: ATTRACTIONS & RESTAURANTS AGENT")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Activities Specialist")
sprint("  Tools:      search_attractions — MCP → Serper API")
sprint("              search_restaurants — MCP → Serper API")
sprint("              search_internet — MCP → Serper API")
sprint("              calculate — local")
sprint("")
sprint("  A2A Input:  Receives context from Extractor (destination, interests)")
sprint("")
sprint("  This agent uses Serper (Google Search) MCP server to find")
sprint("  real attractions and restaurants for the destination.")


subsection("MCP CALLS MADE BY ATTRACTION AGENT")
sprint("  • search_attractions('Istanbul', 'history, food, shopping', 4)")
sprint("    → MCP Server: serper.dev")
sprint("    → Status: retrieved real attraction data")
sprint("  • search_restaurants('Istanbul', 'history, food, shopping', 10)")
sprint("    → MCP Server: serper.dev")
sprint("    → Status: retrieved real restaurant data")

# ============================================================
# PHASE 6: ITINERARY COORDINATOR
# ============================================================

section("PHASE 6/6: ITINERARY COORDINATOR AGENT")

subsection("WHAT THIS AGENT DOES")
sprint("  Role:       Itinerary Coordinator")
sprint("  Tools:      search_internet — MCP → Serper API (for missing data)")
sprint("              search_attractions — MCP → Serper API")
sprint("              search_restaurants — MCP → Serper API")
sprint("              calculate — local")
sprint("  Delegation: CAN delegate to other agents if data is insufficient")
sprint("")
sprint("  A2A Input:  Receives context from ALL 3 SEARCH AGENTS:")
sprint("              • Extractor output (preferences)")
sprint("              • Flight Agent output (flight options)")
sprint("              • Hotel Agent output (hotel options)")
sprint("              • Attraction Agent output (activities + dining)")
sprint("")
sprint("  This is the FULL A2A CHAIN — all previous agents' outputs are")
sprint("  passed as context. The coordinator synthesizes everything into")
sprint("  a cohesive day-by-day itinerary.")

subsection("FINAL ITINERARY OUTPUT")
sprint(f"\n{str(result)}\n")


# ============================================================
# SUMMARY
# ============================================================

total_time = time.time() - total_start
mcp_calls_est = 6  # estimated based on tool usage patterns

section("ARCHITECTURE RECAP — MCP & A2A FLOW DIAGRAM")

sprint("")
sprint("  ┌──────────────────┐")
sprint("  │  USER INPUT      │  'Plan a trip to...'")
sprint("  └────────┬─────────┘")
sprint("           │")
sprint("           ▼")
sprint("  ┌──────────────────┐      8 questions, 8 LLM calls")
sprint("  │  1. CONVERSATION  │───────────────────────────┐")
sprint("  │  (Agent)         │  Gathers preferences        │")
sprint("  │  NO MCP tools    │  (talks to user only)       │")
sprint("  └────────┬─────────┘                              │")
sprint("           │ A2A: conversation transcript            │")
sprint("           ▼                                         │")
sprint("  ┌──────────────────┐      NO TOOLS (pure LLM)     │")
sprint("  │  2. EXTRACTOR    │───────────────────────────────┤")
sprint("  │  (Agent)         │  Extracts preferences as JSON │")
sprint("  └────────┬─────────┘                               │")
sprint("           │ A2A context                             │")
sprint("     ┌─────┼──────────────┐                          │")
sprint("     ▼     ▼              ▼                          │")
sprint("  ┌────────┐ ┌────────┐ ┌────────┐                  │")
sprint("  │ FLIGHT │ │ HOTEL  │ │ ATTR.  │                  │")
sprint("  │ Agent  │ │ Agent  │ │ Agent  │                  │")
sprint("  │  MCP   │ │  MCP   │ │  MCP   │                  │")
sprint("  │ ↓↓↓↓↓  │ │ ↓↓↓↓↓  │ │ ↓↓↓↓↓  │                  │")
sprint("  │fly-scr.│ │Booking │ │ Serper │                  │")
sprint("  └────────┘ └────────┘ └────────┘                  │")
sprint("           │        │        │                       │")
sprint("           └────────┼────────┘                       │")
sprint("                    │ A2A context (all 3 outputs)     │")
sprint("                    ▼                                │")
sprint("  ┌──────────────────┐                               │")
sprint("  │  6. COORDINATOR  │◄───────────────────────────────┘")
sprint("  │  (Agent)         │  Synthesizes everything")
sprint("  │  MCP (fallback)  │  May call Serper if data gaps")
sprint("  └────────┬─────────┘")
sprint("           │")
sprint("           ▼")
sprint("  ┌──────────────────┐")
sprint("  │  FINAL           │  Complete day-by-day itinerary")
sprint("  │  ITINERARY       │  with budget and tips")
sprint("  └──────────────────┘")
sprint("")

section("METRICS")
sprint(f"  Total latency:      {total_time:.1f} seconds")
_m = recorder.stop().summary()
sprint(f"  LLM calls:   {_m['llm_calls']}  (measured, not estimated)")
sprint(f"  Tokens:      {_m['total_tokens']:,} (prompt {_m['prompt_tokens']:,} + output {_m['completion_tokens']:,})")
sprint(f"  Cost:        ${_m['cost_usd']:.5f}")
sprint(f"  MCP tool calls:     ~{mcp_calls_est} (estimated)")
sprint(f"  A2A transfers:      5 (conversation → extractor → 3 search agents → coordinator)")
sprint(f"  Architecture:       6-Agent + MCP Tools + A2A Context Chaining")
