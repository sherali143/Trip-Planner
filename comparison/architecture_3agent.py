"""
Optimized runner: wraps current orchestrator's direct API + coordinator pattern.
Skips interactive conversation — feeds scenario input directly to extraction + coordinator.
"""

import os, sys, time, uuid, json, re
from textwrap import dedent
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

load_dotenv(override=True)

from src.tools.mcp_tools import _call_fly_scraper_api
from src.server.mcp_server import search_hotels_comprehensive, search_attractions, search_restaurants
from src.agents import TripPlannerAgents
from src.core.llm_metrics import recorder
from src.core.resilience import kickoff_with_retry


def _make_coordinator():
    """Create coordinator agent WITHOUT tools (just assembles provided data)."""
    model = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
    return Agent(
        role="Itinerary Coordinator",
        goal="Create day-by-day itinerary from the provided data only",
        backstory="You synthesize flight, hotel, attraction, and restaurant data into a complete itinerary. Do NOT search for additional information.",
        verbose=False,
        allow_delegation=False,
        llm=model,
        tools=[],
        max_iter=3,
        max_rpm=5
    )


def plan_trip_optimized(user_input: str, scenario_id: str = "optimized") -> dict:
    """
    Run optimized 3-agent + direct API architecture.
    Phase 1: Extraction (LLM)
    Phase 2: Direct API calls (flights, hotels, attractions, restaurants) — no LLM
    Phase 3: Coordinator (LLM)

    Call counts are measured by the LiteLLM recorder, not asserted, so this arm
    is counted on exactly the same basis as the 6-agent arm.
    """
    start = time.time()
    errors = []

    agents_class = TripPlannerAgents()
    coordinator = _make_coordinator()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with recorder.session(f"3agent/{scenario_id}") as llm:
        result = _run_optimized(user_input, agents_class, coordinator, start, errors)

    result["llm"] = llm.summary()
    result["llm_calls"] = result["llm"]["llm_calls"]
    result["total_tokens"] = result["llm"]["total_tokens"]
    result["cost_usd"] = result["llm"]["cost_usd"]
    return result


def _run_optimized(user_input, agents_class, coordinator, start, errors) -> dict:
    try:
        # PHASE 1: Extraction (single task, no conversation loop)
        extract_task = Task(
            description=dedent(f"""
                Extract travel preferences from this user request into JSON format:
                User: {user_input}

                Return JSON with these fields:
                - origin, destination, departure_date, return_date, trip_duration
                - total_budget (number, default 0 if not mentioned), num_adults(default 1), num_children(default 0)
                - interests[], travel_style
                - budget_breakdown (flights 35%, hotels 35%, activities 20%, meals 10%)

                If trip_duration given but no return_date, calculate it.
            """),
            expected_output='{"origin":"","destination":"","departure_date":"","return_date":"","trip_duration":0,"total_budget":0,"num_adults":1,"num_children":0,"interests":[],"travel_style":"","budget_breakdown":{"flights":0,"accommodation":0,"activities":0,"meals":0}}',
            agent=agents_class.preferences_extractor_agent()
        )

        extract_crew = Crew(
            agents=[agents_class.preferences_extractor_agent()],
            tasks=[extract_task],
            process=Process.sequential, verbose=False
        )
        extraction_result = str(kickoff_with_retry(extract_crew))
        t1 = time.time()

    except Exception as e:
        return {"arch": "architecture_3agent", "success": False, "error": str(e),
                "latency": time.time() - start}

    # Parse extraction JSON
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
    total_budget = prefs.get("total_budget", 0)
    if not total_budget:
        total_budget = 0
    interests_raw = prefs.get("interests", [])
    interests = ", ".join(interests_raw) if isinstance(interests_raw, list) else str(interests_raw or "")

    bd = prefs.get("budget_breakdown", {})
    if isinstance(bd, dict):
        flight_budget = bd.get("flights", total_budget * 0.35) or total_budget * 0.35
        accommodation_budget = bd.get("accommodation", total_budget * 0.35) or total_budget * 0.35
        meals_budget = bd.get("meals", total_budget * 0.10) or total_budget * 0.10
    else:
        flight_budget = total_budget * 0.35
        accommodation_budget = total_budget * 0.35
        meals_budget = total_budget * 0.10

    budget_per_night = accommodation_budget / trip_duration if trip_duration > 0 else accommodation_budget
    budget_per_meal = meals_budget / (trip_duration * 2) if trip_duration > 0 else meals_budget

    # PHASE 2: Direct API calls
    flights_data = ""
    if origin and destination and departure_date:
        try:
            flights_data = _call_fly_scraper_api(origin, destination, departure_date, return_date, num_adults, flight_budget)
        except Exception as e:
            errors.append(f"flights:{e}")
            flights_data = json.dumps({"success": False, "error": str(e)})

    hotels_data = ""
    if destination and departure_date and return_date:
        try:
            hotels_data = search_hotels_comprehensive(destination, departure_date, return_date, budget_per_night, num_adults, 1)
        except Exception as e:
            errors.append(f"hotels:{e}")
            hotels_data = json.dumps({"error": "Hotel search failed", "success": False})

    attractions_data = ""
    if destination and interests:
        try:
            attractions_data = search_attractions(destination, interests, trip_duration)
        except Exception as e:
            errors.append(f"attractions:{e}")
            attractions_data = json.dumps({"error": "Attraction search failed", "success": False})

    restaurants_data = ""
    if destination:
        try:
            restaurants_data = search_restaurants(destination, interests, budget_per_meal)
        except Exception as e:
            errors.append(f"restaurants:{e}")
            restaurants_data = json.dumps({"error": "Restaurant search failed", "success": False})

    t2 = time.time()

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

    # PHASE 3: Coordinator (no tools — just assembles)
    try:
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
        result = str(kickoff_with_retry(coord_crew))
    except Exception as e:
        return {"arch": "architecture_3agent", "success": False,
                "extraction": extraction_result[:300], "error": str(e),
                "latency": time.time() - start}

    end = time.time()
    return {
        "arch": "architecture_3agent",
        "success": True,
        "result": result,
        "extraction": extraction_result[:500],
        "latency": end - start,
        # t1/t2 are absolute timestamps; phase1_s previously subtracted `start`
        # from an already-elapsed duration and reported a large negative number.
        "phase1_extraction_s": round(t1 - start, 1),
        "phase2_api_fetch_s": round(t2 - t1, 1),
        "phase3_coordination_s": round(end - t2, 1),
        "errors": errors
    }
