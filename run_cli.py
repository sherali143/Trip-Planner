"""
AI Trip Planner — Clean CLI
Usage: python run_cli.py
"""

import os, sys, json, re, time
sys.stdout.reconfigure(encoding="utf-8")

# Suppress noisy logs
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["LITELLM_LOG"] = "ERROR"
import logging
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("src").setLevel(logging.ERROR)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("crewai").setLevel(logging.ERROR)
import litellm
litellm.suppress_debug_info = True
litellm.set_verbose(False)

from dotenv import load_dotenv
from textwrap import dedent
from crewai import Agent, Task, Crew, Process

load_dotenv(override=True)

# Ensure GEMINI_API_KEY is always set (LiteLLM needs it for gemini/ models)
if os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

SEP = "━" * 60


def validate_api_keys():
    required = {
        "GOOGLE_API_KEY": "Google Gemini (AI agents)",
        "SERPER_API_KEY": "Serper (web search)",
        "RAPIDAPI_KEY": "RapidAPI (flights + hotels)",
    }
    missing = [f"  - {k} ({v})" for k, v in required.items() if not os.getenv(k)]
    if missing:
        print("\n❌ MISSING API KEYS:\n" + "\n".join(missing))
        print("\nAdd them to .env file and try again.\n")
        return False
    return True


def main():
    print(SEP)
    print("  AI TRIP PLANNER — 3-Agent + Direct API Architecture")
    print(SEP)

    if not validate_api_keys():
        return

    # Get user input
    print("\n📝 Describe your ideal trip:")
    print("   (e.g., 'Plan a trip to Paris for 7 days with $3000 budget')\n")
    user_input = input("You: ").strip()
    if not user_input:
        user_input = "Plan a trip to Paris for 5 days with $3000 budget. Interests: food, culture."
        print(f"  (using default: {user_input})\n")

    model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
    total_llm_calls = 0
    global_start = time.time()

    # ============================================================
    # PHASE 1: Interactive Conversation (clean Q&A loop)
    # ============================================================
    print(f"\n{SEP}")
    print("  ▶ PHASE 1: COLLECTING TRIP INFORMATION")
    print(f"{SEP}")

    from litellm import completion

    conversation = [
        {"role": "system", "content": dedent("""
            You are a travel assistant. Ask the user ONE question at a time.
            Questions in order: destination, travelers, origin city, dates (departure+return),
            total budget USD, interests, travel style, special requirements.

            After ALL 8 questions are answered, say CONVERSATION_COMPLETE.
        """)},
        {"role": "user", "content": user_input}
    ]

    transcript = f"User: {user_input}\n\n"
    round_num = 0

    while True:
        round_num += 1
        resp = completion(model=model, messages=conversation, temperature=0.3)
        total_llm_calls += 1
        msg = resp.choices[0].message.content

        if "CONVERSATION_COMPLETE" in msg:
            clean = msg.replace("CONVERSATION_COMPLETE", "").strip()
            if clean:
                print(f"\n  Agent: {clean}\n")
                transcript += f"Agent: {clean}\n\n"
            break

        print(f"\n  Agent: {msg}")
        transcript += f"Agent: {msg}\n\n"
        conversation.append({"role": "assistant", "content": msg})

        answer = input("\n  You: ").strip()
        if not answer:
            answer = "I don't have more details. Proceed with what you have."
        transcript += f"User: {answer}\n\n"
        conversation.append({"role": "user", "content": answer})

        if round_num > 10:
            break

    print(f"\n  ✅ All information collected\n")

    # ============================================================
    # PHASE 2: Extract Preferences
    # ============================================================
    print(f"{SEP}")
    print("  ▶ PHASE 2: EXTRACTING PREFERENCES")
    print(f"{SEP}")

    from src.agents import TripPlannerAgents
    agents = TripPlannerAgents()

    extract_task = Task(
        description=dedent(f"""
            Extract travel preferences from this conversation into JSON:
            {transcript}

            Return JSON: origin, destination, departure_date, return_date,
            trip_duration, total_budget, num_adults, num_children,
            interests[], travel_style, budget_breakdown.
        """),
        expected_output="JSON object",
        agent=agents.preferences_extractor_agent()
    )

    extract_crew = Crew(
        agents=[agents.preferences_extractor_agent()],
        tasks=[extract_task],
        process=Process.sequential,
        verbose=False
    )

    extraction_result = str(extract_crew.kickoff())
    total_llm_calls += 1

    prefs = {}
    try:
        jm = re.search(r'\{.*"origin".*"destination".*\}', extraction_result, re.DOTALL)
        if jm:
            prefs = json.loads(jm.group(0))
    except Exception:
        pass

    print(f"\n  Origin:      {prefs.get('origin', '?')}")
    print(f"  Destination: {prefs.get('destination', '?')}")
    print(f"  Dates:       {prefs.get('departure_date', '?')} → {prefs.get('return_date', '?')}")
    print(f"  Budget:      ${prefs.get('total_budget', 0)}")
    print(f"  Interests:   {', '.join(prefs.get('interests', []))}")
    print(f"  Style:       {prefs.get('travel_style', 'not specified')}")
    print(f"  ✅ Extraction complete\n")

    # ============================================================
    # PHASE 3: Direct API Calls
    # ============================================================
    print(f"{SEP}")
    print("  ▶ PHASE 3: FETCHING REAL-TIME DATA")
    print(f"{SEP}")

    origin = prefs.get("origin", "")
    destination = prefs.get("destination", "")
    dep_date = prefs.get("departure_date", "")
    ret_date = prefs.get("return_date", "")
    duration = prefs.get("trip_duration", 5)
    adults = prefs.get("num_adults", 1)
    budget = prefs.get("total_budget", 0)
    interests = ", ".join(prefs.get("interests", [])) if isinstance(prefs.get("interests"), list) else str(prefs.get("interests", ""))

    bd = prefs.get("budget_breakdown", {})
    if isinstance(bd, dict):
        fb = bd.get("flights", budget * 0.35) or budget * 0.35
        ab = bd.get("accommodation", budget * 0.35) or budget * 0.35
        mb = bd.get("meals", budget * 0.10) or budget * 0.10
    else:
        fb = budget * 0.35
        ab = budget * 0.35
        mb = budget * 0.10

    bpn = ab / duration if duration > 0 else ab
    bpm = mb / (duration * 2) if duration > 0 else mb

    api_errors = []
    flights_data = hotels_data = attractions_data = restaurants_data = ""

    from src.tools.mcp_tools import _call_fly_scraper_api
    from src.server.mcp_server import search_hotels_comprehensive, search_attractions, search_restaurants

    if origin and destination and dep_date:
        try:
            flights_data = _call_fly_scraper_api(origin, destination, dep_date, ret_date, adults, fb)
            print("  ✓ Flights: data retrieved")
        except Exception as e:
            api_errors.append(f"Flights: {e}")
            print(f"  ⚠ Flights: {e}")

    if destination and dep_date and ret_date:
        try:
            hotels_data = search_hotels_comprehensive(destination, dep_date, ret_date, bpn, adults, 1)
            print("  ✓ Hotels: data retrieved")
        except Exception as e:
            api_errors.append(f"Hotels: {e}")
            print(f"  ⚠ Hotels: {e}")

    if destination and interests:
        try:
            attractions_data = search_attractions(destination, interests, duration)
            print("  ✓ Attractions: data retrieved")
        except Exception as e:
            api_errors.append(f"Attractions: {e}")
            print(f"  ⚠ Attractions: {e}")

    if destination:
        try:
            restaurants_data = search_restaurants(destination, interests, bpm)
            print("  ✓ Restaurants: data retrieved")
        except Exception as e:
            api_errors.append(f"Restaurants: {e}")
            print(f"  ⚠ Restaurants: {e}")

    if api_errors:
        print(f"\n  ⚠ {len(api_errors)} API error(s) — coordinator will work with available data")
    else:
        print(f"  ✅ All data retrieved successfully")

    # ============================================================
    # PHASE 4: Coordinator assembles itinerary
    # ============================================================
    print(f"\n{SEP}")
    print("  ▶ PHASE 4: ASSEMBLING ITINERARY")
    print(f"{SEP}")

    data_block = f"""
PREFERENCES:
{json.dumps(prefs, indent=2)}

FLIGHTS:
{str(flights_data)[:3000]}

HOTELS:
{str(hotels_data)[:3000]}

ATTRACTIONS:
{str(attractions_data)[:3000]}

RESTAURANTS:
{str(restaurants_data)[:3000]}
"""

    coord_agent = Agent(
        role="Itinerary Coordinator",
        goal="Create day-by-day itinerary from provided data only",
        backstory="Synthesize flight, hotel, and attraction data into a complete day-by-day itinerary.",
        verbose=False,
        allow_delegation=False,
        llm=model,
        tools=[],
        max_iter=2,
        max_rpm=5
    )

    coord_task = Task(
        description=dedent(f"""
            Create a complete day-by-day itinerary using ONLY the data below.
            Do NOT search for additional information.

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
        expected_output="Complete day-by-day itinerary",
        agent=coord_agent
    )

    coord_crew = Crew(
        agents=[coord_agent],
        tasks=[coord_task],
        process=Process.sequential,
        verbose=False
    )

    print("  Itinerary Coordinator working...")
    result = str(coord_crew.kickoff())
    total_llm_calls += 1
    total_time = time.time() - global_start

    # ============================================================
    # OUTPUT
    # ============================================================
    print(f"\n{SEP}")
    print("  📋 YOUR COMPLETE TRAVEL ITINERARY")
    print(f"{SEP}\n")
    print(result)

    print(f"\n{SEP}")
    print("  SUMMARY")
    print(f"{SEP}")
    print(f"  LLM calls:     {total_llm_calls}")
    print(f"  Total time:    {total_time:.1f}s")
    print(f"  API errors:    {len(api_errors)}")
    print(f"  Architecture:  3-Agent + Direct API")
    for e in api_errors:
        print(f"    ⚠ {e}")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
