"""
Trip Planner Research Experiment - 8 Iterations for Paper Validation

Runs 8 diverse, complex travel scenarios to generate performance metrics for the research paper.
Tracks:
- Token Usage (Prompt vs Completion)
- Latency
- Feasibility (Success Rate)
- Protocol Errors
"""

import os
import time
import json
import sys
from datetime import datetime
from crewai import Crew, Process

# 8 Complex Test Scenarios for Research Paper
TEST_QUERIES = [
    {
        "id": "PAPER_001",
        "query": "7-day trip to Tokyo and Kyoto for 2 adults. Budget $3500. Interested in anime, temples, and sushi. Departure June 15, 2025. Need a ryokan stay for at least one night.",
        "expected_days": 7
    },
    {
        "id": "PAPER_002",
        "query": "Business trip to London from New York for 5 days. Budget $5000. Need business class flight, hotel near Canary Wharf, and reliable Wi-Fi. Dates: May 12-17, 2025.",
        "expected_days": 5
    },
    {
        "id": "PAPER_003",
        "query": "10-day family vacation to Italy (Rome, Florence, Venice) for 2 adults, 2 kids. Budget $8000. Start July 1. Need kid-friendly tours and hotels with pools.",
        "expected_days": 10
    },
    {
        "id": "PAPER_004",
        "query": "Solo backpacking trip to Thailand for 14 days. Budget $1500 USD. Start Nov 1, 2025. Focus on street food, beaches, and hostels. Visiting Bangkok and Phuket.",
        "expected_days": 14
    },
    {
        "id": "PAPER_005",
        "query": "Honeymoon in Paris for 6 days. Budget $6000. Romantic dining, Eiffel Tower view hotel, and Seine cruise. Depart Sept 10, 2025.",
        "expected_days": 6
    },
    {
        "id": "PAPER_006",
        "query": "Weekend shopping trip to Dubai from Riyadh. 3 days. High budget ($10k). Luxury malls, Burj Khalifa, high-end dining. Start Dec 5, 2025.",
        "expected_days": 3
    },
    {
        "id": "PAPER_007",
        "query": "Cultural trip to Cairo, Egypt for 5 days. Budget $2000. Pyramids, museums, Nile cruise. Just me. Start Oct 12, 2025.",
        "expected_days": 5
    },
    {
        "id": "PAPER_008",
        "query": "Adventure trip to Costa Rica (San Jose & Arenal) for 8 days. Budget $3000. Zip-lining, hiking, wildlife. 2 adults. Start March 3, 2025.",
        "expected_days": 8
    }
]


def evaluate_response(response: str, expected_days: int) -> dict:
    """Evaluate quality and feasibility."""
    import re
    response_lower = response.lower()
    
    has_flights = 'flight' in response_lower
    has_hotels = 'hotel' in response_lower
    has_daily_plan = expected_days > 0 # Simplified check
    
    # Count days
    # Supports "Day 1", "**Day 1**", "### Day 1", etc.
    day_count = len(re.findall(r'(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?(?:Day|DAY|day)\s*\d+', response))
    
    # Logic: Feasible if it has flights, hotels, and at least 50% of expected days detailed
    feasible = has_flights and has_hotels and (day_count >= expected_days * 0.5)
    
    return {
        "actual_days": day_count,
        "feasible": feasible,
        "completeness_score": min(day_count / expected_days, 1.0) * 100
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

def run_experiment():
    print(f"🚀 STARTING 8-ITERATION RESEARCH EXPERIMENT")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {"runs": [], "summary": {}}
    
    try:
        from agents import TripPlannerAgents
        from tasks import TripPlannerTasks
    except ImportError as e:
        print(f"Import Error: {e}")
        return

    total_tokens = 0
    total_latency = 0
    successful_runs = 0

    for i, case in enumerate(TEST_QUERIES):
        print(f"\n[{i+1}/8] Running Scenario: {case['id']} ({case['expected_days']} days)")
        start_time = time.time()
        
        try:
            # Init
            agents = TripPlannerAgents()
            tasks = TripPlannerTasks()
            cid = f"PAPER_EXP_{case['id']}_{int(time.time())}"
            
            # Agents
            conv_agent = agents.conversational_agent()
            pref_agent = agents.preferences_extractor_agent()
            flight_agent = agents.flight_search_agent()
            hotel_agent = agents.hotel_agent()
            attr_agent = agents.attraction_agent()
            coord_agent = agents.itinerary_coordinator_agent()
            
            # Tasks
            t_conv = tasks.conversation_task(conv_agent, case['query'], cid)
            t_extract = tasks.extraction_task(pref_agent, cid, t_conv)
            t_flight = tasks.flight_search_task(flight_agent, cid, t_extract)
            t_hotel = tasks.hotel_search_task(hotel_agent, cid, t_extract)
            t_attr = tasks.attraction_search_task(attr_agent, cid, t_extract)
            t_coord = tasks.coordination_task(coord_agent, cid, t_extract, t_flight, t_hotel, t_attr)
            
            crew = Crew(
                agents=[conv_agent, pref_agent, flight_agent, hotel_agent, attr_agent, coord_agent],
                tasks=[t_conv, t_extract, t_flight, t_hotel, t_attr, t_coord],
                verbose=True
            )
            
            result = crew.kickoff()
            latency = time.time() - start_time
            
            # Metrics
            tokens = extract_tokens(result)
            output_text = str(result.raw if hasattr(result, 'raw') else result)
            eval_metrics = evaluate_response(output_text, case['expected_days'])
            
            run_data = {
                "id": case['id'],
                "latency": round(latency, 2),
                "tokens": tokens,
                "feasible": eval_metrics['feasible'],
                "days_found": eval_metrics['actual_days']
            }
            results["runs"].append(run_data)
            
            total_tokens += tokens['total']
            total_latency += latency
            if eval_metrics['feasible']:
                successful_runs += 1
                
            print(f"✅ DONE. Tokens: {tokens['total']:,} | Latency: {latency:.1f}s | Feasible: {eval_metrics['feasible']}")

            # Save incrementally
            with open("experiment_results_paper.json", "w") as f:
                json.dump(results, f, indent=2)

        except Exception as e:
            print(f"❌ FAILED: {e}")
            results["runs"].append({"id": case['id'], "error": str(e), "feasible": False})

    # Summary
    avg_tokens = total_tokens / 8
    avg_latency = total_latency / 8
    feasibility_rate = (successful_runs / 8) * 100
    
    results["summary"] = {
        "avg_tokens": round(avg_tokens, 0),
        "avg_latency": round(avg_latency, 2),
        "feasibility_rate": f"{feasibility_rate}%",
        "total_runs": 8
    }
    
    with open("experiment_results_paper.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n📊 EXPERIMENT COMPLETE")
    print(f"Avg Tokens: {avg_tokens:,.0f}")
    print(f"Feasibility: {feasibility_rate}%")
    print(f"Results saved to experiment_results_paper.json")

if __name__ == "__main__":
    run_experiment()
