"""
Run optimized system: 2 test runs first, then 75 iterations if tests pass.
"""

import os
import time
import json
from datetime import datetime
from crewai import Crew

# Diverse test queries for 75 runs (cycling through these)
QUERY_POOL = [
    "5-day trip to Barcelona from London for 2 adults. Budget $3000. Beach, Gaudi architecture, tapas. Departure April 10, 2025.",
    "3-day weekend getaway to Amsterdam for a couple. Budget $1500. Museums, canals, local food. May 2-5, 2025.",
    "7-day family trip to Orlando (4 people, 2 kids). Budget $5000. Disney, Universal, beach day. June 20-27, 2025.",
    "4-day solo business trip to Singapore. Budget $4000. Conference, Marina Bay, hawker food. Sept 15-19, 2025.",
    "6-day honeymoon in Maldives for 2. Budget $8000. Overwater villa, snorkeling, romantic dinner. Nov 1-7, 2025.",
    "5-day cultural trip to Istanbul for 2 adults. Budget $2500. Hagia Sophia, Blue Mosque, bazaars, Turkish food. Oct 5-10, 2025.",
    "4-day ski trip to Swiss Alps (Zermatt) for 3 adults. Budget $6000. Skiing, spa, fondue. Jan 15-19, 2026.",
    "7-day Japan trip for 2 (Tokyo + Kyoto). Budget $4500. Cherry blossoms, temples, sushi. April 1-8, 2025.",
    "5-day London trip for 4 adults. Budget $3500. Business meetings, theater, pubs. March 10-15, 2025.",
    "10-day Italy adventure (Rome, Florence, Venice) for 2. Budget $6000. Art, history, wine. Sept 1-11, 2025.",
]


def run_single_iteration(run_id: int, query: str):
    """Run a single optimized iteration."""
    from agents_optimized import TripPlannerAgentsOptimized
    from tasks import TripPlannerTasks
    import re
    
    start_time = time.time()
    
    try:
        agents = TripPlannerAgentsOptimized(use_mini_models=True)
        tasks = TripPlannerTasks()
        cid = f"RUN_{run_id}_{int(time.time())}"
        
        conv_agent = agents.conversational_agent()
        pref_agent = agents.preferences_extractor_agent()
        flight_agent = agents.flight_search_agent()
        hotel_agent = agents.hotel_agent()
        attr_agent = agents.attraction_agent()
        coord_agent = agents.itinerary_coordinator_agent()
        
        t_conv = tasks.conversation_task(conv_agent, query, cid)
        t_extract = tasks.extraction_task(pref_agent, cid, t_conv)
        t_flight = tasks.flight_search_task(flight_agent, cid, t_extract)
        t_hotel = tasks.hotel_search_task(hotel_agent, cid, t_extract)
        t_attr = tasks.attraction_search_task(attr_agent, cid, t_extract)
        t_coord = tasks.coordination_task(coord_agent, cid, t_extract, t_flight, t_hotel, t_attr)
        
        crew = Crew(
            agents=[conv_agent, pref_agent, flight_agent, hotel_agent, attr_agent, coord_agent],
            tasks=[t_conv, t_extract, t_flight, t_hotel, t_attr, t_coord],
            verbose=False
        )
        
        result = crew.kickoff()
        latency = time.time() - start_time
        
        output_text = str(result.raw if hasattr(result, 'raw') else result)
        
        # Extract token usage
        tokens = 0
        if hasattr(result, 'token_usage'):
            tokens = getattr(result.token_usage, 'total_tokens', 0)
        
        # Check feasibility (has flights, hotels, day mentions)
        has_flights = 'flight' in output_text.lower()
        has_hotels = 'hotel' in output_text.lower()
        day_count = len(re.findall(r'(?:Day|DAY)\s*\d+', output_text))
        feasible = has_flights and has_hotels and day_count >= 1
        
        return {
            "run_id": run_id,
            "success": True,
            "feasible": feasible,
            "tokens": tokens,
            "latency": round(latency, 1),
            "output_length": len(output_text),
            "days_found": day_count
        }
        
    except Exception as e:
        latency = time.time() - start_time
        return {
            "run_id": run_id,
            "success": False,
            "error": str(e),
            "latency": round(latency, 1)
        }


def run_experiment(num_runs: int, output_file: str):
    """Run the experiment with specified number of iterations."""
    print(f"🚀 STARTING {num_runs}-ITERATION EXPERIMENT")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {
        "runs": [],
        "summary": {},
        "timestamp": datetime.now().isoformat(),
        "total_runs": num_runs
    }
    
    successful = 0
    feasible = 0
    total_tokens = 0
    total_latency = 0
    
    for i in range(num_runs):
        query = QUERY_POOL[i % len(QUERY_POOL)]
        print(f"\n[{i+1}/{num_runs}] Running iteration...")
        
        run_result = run_single_iteration(i + 1, query)
        results["runs"].append(run_result)
        
        if run_result.get("success"):
            successful += 1
            total_latency += run_result.get("latency", 0)
            total_tokens += run_result.get("tokens", 0)
            if run_result.get("feasible"):
                feasible += 1
            print(f"✅ Run {i+1}: Tokens={run_result.get('tokens', 0):,} | Latency={run_result.get('latency', 0):.1f}s | Feasible={run_result.get('feasible')}")
        else:
            print(f"❌ Run {i+1}: FAILED - {run_result.get('error', 'Unknown')[:50]}")
        
        # Save incrementally
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2)
    
    # Calculate summary
    results["summary"] = {
        "total_runs": num_runs,
        "successful": successful,
        "feasible": feasible,
        "success_rate": f"{(successful/num_runs)*100:.1f}%",
        "feasibility_rate": f"{(feasible/successful)*100:.1f}%" if successful > 0 else "0%",
        "avg_tokens": round(total_tokens / successful) if successful > 0 else 0,
        "avg_latency": round(total_latency / successful, 1) if successful > 0 else 0,
        "total_tokens": total_tokens
    }
    
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("📊 EXPERIMENT COMPLETE")
    print(f"Success: {successful}/{num_runs} ({results['summary']['success_rate']})")
    print(f"Feasible: {feasible}/{successful} ({results['summary']['feasibility_rate']})")
    print(f"Avg Tokens: {results['summary']['avg_tokens']:,}")
    print(f"Avg Latency: {results['summary']['avg_latency']}s")
    print(f"Results: {output_file}")
    
    return results


def main():
    print("=" * 60)
    print("PHASE 1: Running 2 test iterations...")
    print("=" * 60)
    
    test_results = run_experiment(2, "test_2runs.json")
    
    if test_results["summary"]["successful"] >= 2:
        print("\n✅ Tests PASSED! Proceeding with 75 iterations...\n")
        time.sleep(2)
        
        print("=" * 60)
        print("PHASE 2: Running 75 iterations...")
        print("=" * 60)
        
        run_experiment(75, "experiment_75runs.json")
    else:
        print("\n❌ Tests FAILED! Not proceeding with 75 iterations.")
        print(f"Only {test_results['summary']['successful']}/2 tests passed.")


if __name__ == "__main__":
    main()
