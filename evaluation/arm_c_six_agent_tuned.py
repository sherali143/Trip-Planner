"""
Approach C: the same six agents, configured properly.

One or two tools each, short prompts, results trimmed before being passed on,
and a hard cap on steps. Exists so the comparison separates tuning from
architecture.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from textwrap import dedent

from crewai import Agent, Crew, Process, Task

from evaluation.distilled_tools import (
    distilled_search_attractions,
    distilled_search_flights,
    distilled_search_hotels,
    distilled_search_restaurants,
)
from trip_planner.core.llm_metrics import recorder
from trip_planner.core.resilience import kickoff_with_retry
from trip_planner.core.budget import LEGACY_ALLOCATION as _DEFAULT_SPLIT
from trip_planner.core.gemini_compat import model_string

MAX_ITER = 3


class OptimizedAgents:
    """Same six roles as the proposal; narrow tools and short prompts."""

    def __init__(self):
        self.llm = model_string()

    def _agent(self, role: str, goal: str, backstory: str, tools: list) -> Agent:
        return Agent(
            role=role, goal=goal, backstory=backstory,
            verbose=False, allow_delegation=False, llm=self.llm,
            tools=tools, max_iter=MAX_ITER, max_rpm=5,
        )

    def preferences_extractor_agent(self) -> Agent:
        return self._agent(
            "Travel Preferences Extractor",
            "Turn a travel request into structured JSON",
            "You extract travel details into JSON. Budget split: flights "
            f"{_DEFAULT_SPLIT['flights']:.0%}, hotels {_DEFAULT_SPLIT['accommodation']:.0%}, "
            f"activities {_DEFAULT_SPLIT['activities']:.0%}, meals {_DEFAULT_SPLIT['meals']:.0%}.",
            [],
        )

    def flight_search_agent(self) -> Agent:
        return self._agent(
            "Flight Search Specialist",
            "Find the best flights within budget",
            "Call the flight tool once with the given cities and dates, then report the options. Never invent flights.",
            [distilled_search_flights],
        )

    def hotel_agent(self) -> Agent:
        return self._agent(
            "Hotel Search Specialist",
            "Find the best hotels within budget",
            "Call the hotel tool once with the given city and dates, then report the options. Never invent hotels.",
            [distilled_search_hotels],
        )

    def attraction_agent(self) -> Agent:
        return self._agent(
            "Activities Specialist",
            "Find attractions and places to eat",
            "Call each tool once, then report what you found. Never invent places.",
            [distilled_search_attractions, distilled_search_restaurants],
        )

    def itinerary_coordinator_agent(self) -> Agent:
        return self._agent(
            "Itinerary Coordinator",
            "Write a complete day-by-day itinerary from the data provided",
            "You assemble a day-by-day plan from data the specialists gathered. Use only that data; do not search.",
            [],
        )


def _run_single(agent: Agent, description: str, expected: str) -> str:
    """Run one agent/task as its own crew so specialists can run concurrently."""
    task = Task(description=dedent(description), expected_output=expected, agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    return str(kickoff_with_retry(crew))


def run_six_agent_tuned(user_input: str, scenario_id: str = "optimized6") -> dict:
    """Run the optimised 6-agent arm. Returns the same metrics dict shape as the other arms."""
    start = time.time()
    errors: list = []
    agents = OptimizedAgents()

    with recorder.session(f"6agent-opt/{scenario_id}") as llm:
        result = _run(user_input, agents, start, errors)

    result["llm"] = llm.summary()
    result["llm_calls"] = result["llm"]["llm_calls"]
    result["total_tokens"] = result["llm"]["total_tokens"]
    result["cost_usd"] = result["llm"]["cost_usd"]
    return result


def _run(user_input: str, agents: OptimizedAgents, start: float, errors: list) -> dict:
    # PHASE 1 — extraction
    try:
        t0 = time.time()
        extraction = _run_single(
            agents.preferences_extractor_agent(),
            f"""
                Extract travel preferences from this request as JSON:
                {user_input}

                Fields: origin, destination, departure_date, return_date, trip_duration,
                total_budget, num_adults, num_children, interests, travel_style,
                budget_breakdown. Compute return_date from duration if needed.
            """,
            '{"origin":"","destination":"","departure_date":"","return_date":"","trip_duration":0,'
            '"total_budget":0,"num_adults":1,"num_children":0,"interests":[],"travel_style":"",'
            '"budget_breakdown":{"flights":0,"accommodation":0,"activities":0,"meals":0}}',
        )
        t_extract = time.time() - t0
    except Exception as exc:
        return {"arch": "arm_c_six_agent_tuned", "success": False,
                "error": str(exc), "latency": time.time() - start}

    # PHASE 2 — three specialists CONCURRENTLY (proposal S3.7)
    t0 = time.time()
    jobs = [
        (agents.flight_search_agent(),
         f"Find flights using this trip data:\n{extraction}\nCall the flight tool once.",
         "The flight options found"),
        (agents.hotel_agent(),
         f"Find hotels using this trip data:\n{extraction}\nCall the hotel tool once.",
         "The hotel options found"),
        (agents.attraction_agent(),
         f"Find attractions and restaurants using this trip data:\n{extraction}\nCall each tool once.",
         "Attractions and restaurants found"),
    ]
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_run_single, a, d, e) for a, d, e in jobs]
            outputs = []
            for fut in futures:
                try:
                    outputs.append(fut.result())
                except Exception as exc:
                    errors.append(str(exc))
                    outputs.append(f"(search failed: {exc})")
        flights, hotels, activities = outputs
    except Exception as exc:
        return {"arch": "arm_c_six_agent_tuned", "success": False,
                "extraction": extraction[:300], "error": str(exc),
                "latency": time.time() - start}
    t_search = time.time() - t0

    # PHASE 3 — coordination
    try:
        t0 = time.time()
        itinerary = _run_single(
            agents.itinerary_coordinator_agent(),
            f"""
                Write a complete day-by-day itinerary using ONLY the data below.

                TRIP: {extraction}
                FLIGHTS: {flights}
                HOTELS: {hotels}
                ACTIVITIES AND FOOD: {activities}

                Include every day individually, a recommended flight and hotel,
                a budget breakdown and travel tips.
            """,
            "A complete day-by-day itinerary with budget and tips",
        )
        t_coord = time.time() - t0
    except Exception as exc:
        return {"arch": "arm_c_six_agent_tuned", "success": False,
                "extraction": extraction[:300], "error": str(exc),
                "latency": time.time() - start}

    return {
        "arch": "arm_c_six_agent_tuned",
        "success": True,
        "result": itinerary,
        "extraction": extraction[:500],
        "latency": time.time() - start,
        "phase1_extraction_s": round(t_extract, 1),
        "phase2_search_parallel_s": round(t_search, 1),
        "phase3_coordination_s": round(t_coord, 1),
        "errors": errors,
    }
