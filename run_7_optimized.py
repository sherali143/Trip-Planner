"""
Run 7 additional optimized experiments to complete paper validation data.
Uses TripPlannerAgentsOptimized with GPT-4o-mini for non-critical agents.
"""

import os
import time
import json
from datetime import datetime
from crewai import Crew, Process

# 7 Test Scenarios (diverse mix)
TEST_QUERIES = [
    {
        "id": "OPT_RUN_01",
        "query": "5-day trip to Barcelona from London for 2 adults. Budget $3000. Beach, Gaudi architecture, tapas. Departure April 10, 2025.",
        "expected_days": 5
    },
    {
        "id": "OPT_RUN_02", 
        "query": "3-day weekend getaway to Amsterdam for a couple. Budget $1500. Museums, canals, local food. May 2-5, 2025.",
        "expected_days": 3
    },
    {
        "id": "OPT_RUN_03",
        "query": "7-day family trip to Orlando (4 people, 2 kids). Budget $5000. Disney, Universal, beach day. June 20-27, 2025.",
        "expected_days": 7
    },
    {
        "id": "OPT_RUN_04",
        "query": "4-day solo business trip to Singapore. Budget $4000. Conference, Marina Bay, hawker food. Sept 15-19, 2025.",
        "expected_days": 4
    },
    {
        "id": "OPT_RUN_05",
        "query": "6-day honeymoon in Maldives for 2. Budget $8000. Overwater villa, snorkeling, romantic dinner. Nov 1-7, 2025.",
        "expected_days": 6
    },
    {
        "id": "OPT_RUN_06",
        "query": "5-day cultural trip to Istanbul for 2 adults. Budget $2500. Hagia Sophia, Blue Mosque, bazaars, Turkish food. Oct 5-10, 2025.",
        "expected_days": 5
    },
    {
        "id": "OPT_RUN_07",
        "query": "4-day ski trip to Swiss Alps (Zermatt) for 3 adults. Budget $6000. Skiing, spa, fondue. Jan 15-19, 2026.",
        "expected_days": 4
    }
]


def evaluate_response(response: str, expected_days: int) -> dict:
    """Evaluate quality and feasibility."""
    import re
    response_lower = response.lower()
    
    has_flights = 'flight' in response_lower
    has_hotels = 'hotel' in response_lower
    
    # Count days mentioned
    day_count = len(re.findall(r'(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?(?:Day|DAY|day)\s*\d+', response))
    
    feasible = has_flights and has_hotels and (day_count >= expected_days * 0.5)
    
    return {
        "actual_days": day_count,
        "feasible": feasible,
        "completeness_score": min(day_count / expected_days, 1.0) * 100 if expected_days > 0 else 0
    }


def extract_tokens(result):
    """Extract token usage safely."""
    try:
        if hasattr(result, 'token_usage'):
            return {
                "total": result.token_usage.total_tokens,
                "prompt": result.token_usage.prompt_tokens,
                "completion": result.token_usage.completion_tokens,
                "requests": getattr(result.token_usage, 'successful_requests', 0)
            }
        return {"total": 0, "prompt": 0, "completion": 0, "requests": 0}
    except:
        return {"total": 0, "prompt": 0, "completion": 0, "requests": 0}


def run_optimized_experiments():
    print(f"🚀 STARTING 7 OPTIMIZED EXPERIMENT RUNS")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {"runs": [], "summary": {}, "timestamp": datetime.now().isoformat()}
    
    try:
        from agents_optimized import TripPlannerAgentsOptimized
        from tasks import TripPlannerTasks
    except ImportError as e:
        print(f"Import Error: {e}")
        return

    total_tokens = 0
    total_latency = 0
    successful_runs = 0
    feasible_count = 0

    for i, case in enumerate(TEST_QUERIES):
        print(f"\n[{i+1}/7] Running: {case['id']} ({case['expected_days']} days)")
        print(f"Query: {case['query'][:60]}...")
        start_time = time.time()
        
        try:
            # Initialize optimized agents
            agents = TripPlannerAgentsOptimized(use_mini_models=True)
            tasks = TripPlannerTasks()
            cid = f"OPT_EXP_{case['id']}_{int(time.time())}"
            
            # Create agents
            conv_agent = agents.conversational_agent()
            pref_agent = agents.preferences_extractor_agent()
            flight_agent = agents.flight_search_agent()
            hotel_agent = agents.hotel_agent()
            attr_agent = agents.attraction_agent()
            coord_agent = agents.itinerary_coordinator_agent()
            
            # Create tasks
            t_conv = tasks.conversation_task(conv_agent, case['query'], cid)
            t_extract = tasks.extraction_task(pref_agent, cid, t_conv)
            t_flight = tasks.flight_search_task(flight_agent, cid, t_extract)
            t_hotel = tasks.hotel_search_task(hotel_agent, cid, t_extract)
            t_attr = tasks.attraction_search_task(attr_agent, cid, t_extract)
            t_coord = tasks.coordination_task(coord_agent, cid, t_extract, t_flight, t_hotel, t_attr)
            
            crew = Crew(
                agents=[conv_agent, pref_agent, flight_agent, hotel_agent, attr_agent, coord_agent],
                tasks=[t_conv, t_extract, t_flight, t_hotel, t_attr, t_coord],
                verbose=False  # Reduced verbosity for cleaner output
            )
            
            result = crew.kickoff()
            latency = time.time() - start_time
            
            # Extract metrics
            tokens = extract_tokens(result)
            output_text = str(result.raw if hasattr(result, 'raw') else result)
            eval_metrics = evaluate_response(output_text, case['expected_days'])
            
            run_data = {
                "id": case['id'],
                "query": case['query'],
                "latency": round(latency, 2),
                "tokens": tokens,
                "feasible": eval_metrics['feasible'],
                "days_found": eval_metrics['actual_days'],
                "expected_days": case['expected_days'],
                "success": True,
                "output_preview": output_text[:500] + "..." if len(output_text) > 500 else output_text
            }
            results["runs"].append(run_data)
            
            total_tokens += tokens['total']
            total_latency += latency
            successful_runs += 1
            if eval_metrics['feasible']:
                feasible_count += 1
                
            print(f"✅ DONE | Tokens: {tokens['total']:,} | Latency: {latency:.1f}s | Feasible: {eval_metrics['feasible']}")

            # Save incrementally
            with open("optimized_7runs_results.json", "w") as f:
                json.dump(results, f, indent=2)

        except Exception as e:
            latency = time.time() - start_time
            print(f"❌ FAILED: {e}")
            results["runs"].append({
                "id": case['id'],
                "error": str(e),
                "feasible": False,
                "success": False,
                "latency": round(latency, 2)
            })
            
            # Save even on failure
            with open("optimized_7runs_results.json", "w") as f:
                json.dump(results, f, indent=2)

    # Calculate summary
    if successful_runs > 0:
        avg_tokens = total_tokens / successful_runs
        avg_latency = total_latency / successful_runs
        feasibility_rate = (feasible_count / successful_runs) * 100
    else:
        avg_tokens = 0
        avg_latency = 0
        feasibility_rate = 0
    
    results["summary"] = {
        "total_runs": 7,
        "successful_runs": successful_runs,
        "feasible_runs": feasible_count,
        "avg_tokens": round(avg_tokens, 0),
        "avg_latency": round(avg_latency, 2),
        "feasibility_rate": f"{feasibility_rate:.1f}%",
        "total_tokens": total_tokens
    }
    
    # Final save
    with open("optimized_7runs_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n" + "=" * 60)
    print("📊 EXPERIMENT COMPLETE")
    print(f"Successful Runs: {successful_runs}/7")
    print(f"Feasible Runs: {feasible_count}/{successful_runs}")
    print(f"Avg Tokens: {avg_tokens:,.0f}")
    print(f"Avg Latency: {avg_latency:.1f}s")
    print(f"Feasibility: {feasibility_rate:.1f}%")
    print(f"Results saved to: optimized_7runs_results.json")


if __name__ == "__main__":
    run_optimized_experiments()
