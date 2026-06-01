import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import os
import time
import json
import random
from crewai import Crew, Process
from agents import TripPlannerAgents
from tasks import TripPlannerTasks

# --- CONFIGURATION ---
NUM_RUNS = 5  # Number of test runs for the paper
OUTPUT_FILE = "experiment_results.json"

# TripTailor "Hard" Dataset Sub-samples (Complex queries)
TEST_QUERIES = [
    {
        "id": "HARD_001",
        "query": "I need a 7-day trip to Tokyo and Kyoto starting Dec 15th. Budget is tight ($2500 total for 2 people). Need flights, cheap hotels near transit, and 3 specific cultural activities per day. Must include a tea ceremony."
    },
    {
        "id": "HARD_002",
        "query": "Plan a 5-day business trip to London from New York, departing next Monday. Need a hotel with a meeting room in Canary Wharf, business class flights, and dinner reservations for 4 people at a Michelin star restaurant under $300/person."
    },
    {
        "id": "HARD_003",
        "query": "Family vacation to Paris for 4 (2 adults, 2 kids) in July. Budget $6000. Want Disney Paris for 1 day, Louvre, and Versailles. Need family suite hotel."
    }
]

def run_experiment():
    results = {
        "metrics": {
            "total_runs": 0,
            "successful_runs": 0,
            "total_tokens": 0,
            "protocol_errors": 0,
            "feasibility_score": 0.0
        },
        "details": []
    }

    print(f"🔬 STARTING EXPERIMENT: Running {NUM_RUNS} iterations...")
    
    for i in range(NUM_RUNS):
        # Pick a random query or cycle through
        test_case = TEST_QUERIES[i % len(TEST_QUERIES)]
        print(f"\n🧪 RUN {i+1}/{NUM_RUNS}: {test_case['id']}")
        
        # Generate a unique conversation ID for this run
        conversation_id = f"benchmark_{test_case['id']}_{i}"
        
        # ===== FIX: Create FRESH agents for each run to prevent context accumulation =====
        agents = TripPlannerAgents()
        tasks = TripPlannerTasks()
        
        conversational_agent = agents.conversational_agent()
        preferences_agent = agents.preferences_extractor_agent()
        flight_agent = agents.flight_search_agent()
        hotel_agent = agents.hotel_agent()
        attraction_agent = agents.attraction_agent()
        coordinator_agent = agents.itinerary_coordinator_agent()
        
        # 1. Setup Tasks based on the test query
        # Create the conversation task first (this handles user input)
        conversation_task = tasks.conversation_task(
            conversational_agent, 
            user_input=test_case['query'],
            conversation_id=conversation_id
        )
        
        # Extraction task depends on conversation task
        extraction_task = tasks.extraction_task(
            preferences_agent, 
            conversation_id=conversation_id,
            conversation_task=conversation_task
        )
        
        # Search tasks depend on extraction task
        flight_task = tasks.flight_search_task(
            flight_agent, 
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        hotel_task = tasks.hotel_search_task(
            hotel_agent, 
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        attraction_task = tasks.attraction_search_task(
            attraction_agent, 
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        # Coordination task receives all search results
        coordination_task = tasks.coordination_task(
            coordinator_agent, 
            conversation_id=conversation_id,
            extraction_task=extraction_task,
            flight_task=flight_task,
            hotel_task=hotel_task,
            attraction_task=attraction_task
        )

        crew = Crew(
            agents=[conversational_agent, preferences_agent, flight_agent, hotel_agent, attraction_agent, coordinator_agent],
            tasks=[conversation_task, extraction_task, flight_task, hotel_task, attraction_task, coordination_task],
            verbose=False  # Keep it clean for logs
        )

        start_time = time.time()
        
        # Track Tokens and Errors
        try:
            # Run the crew and get result
            result = crew.kickoff()
            
            # METRIC 1: Token Usage - Use CrewAI's built-in token_usage attribute
            tokens = 0
            token_usage_data = {}
            
            # CrewAI stores token usage in the result object
            if hasattr(result, 'token_usage'):
                token_usage = result.token_usage
                if token_usage:
                    # token_usage is a dict with 'total_tokens', 'prompt_tokens', 'completion_tokens'
                    if isinstance(token_usage, dict):
                        tokens = token_usage.get('total_tokens', 0)
                        token_usage_data = token_usage
                    elif hasattr(token_usage, 'total_tokens'):
                        tokens = token_usage.total_tokens
                        token_usage_data = {
                            'total_tokens': getattr(token_usage, 'total_tokens', 0),
                            'prompt_tokens': getattr(token_usage, 'prompt_tokens', 0),
                            'completion_tokens': getattr(token_usage, 'completion_tokens', 0),
                            'successful_requests': getattr(token_usage, 'successful_requests', 0)
                        }
            
            # METRIC 2: Feasibility Check (Heuristic)
            # Check if output contains flight numbers and hotel names
            output_str = str(result.raw if hasattr(result, 'raw') else result)
            output_lower = output_str.lower()
            is_feasible = "flight" in output_lower and "hotel" in output_lower and "total cost" in output_lower
            
            # METRIC 3: Protocol Errors
            # Check if the result mentions "Error" or "Missing" which implies the MCP tool failed
            protocol_errors = output_lower.count("error executing") + output_lower.count("invalid parameter") + output_lower.count("api error")

            run_data = {
                "id": test_case['id'],
                "tokens": tokens,
                "token_usage_details": token_usage_data,
                "feasible": is_feasible,
                "protocol_errors": protocol_errors,
                "latency": time.time() - start_time
            }
            
            results["details"].append(run_data)
            
            # Aggregation
            results["metrics"]["total_runs"] += 1
            if is_feasible: results["metrics"]["successful_runs"] += 1
            results["metrics"]["total_tokens"] += tokens
            results["metrics"]["protocol_errors"] += protocol_errors

            print(f"   ✅ Result: Tokens={tokens}, Errors={protocol_errors}, Feasible={is_feasible}")
            if token_usage_data:
                print(f"   📊 Token Details: {token_usage_data}")

        except Exception as e:
            print(f"   ❌ RUN FAILED: {str(e)}")
            results["metrics"]["total_runs"] += 1
            results["details"].append({
                "id": test_case['id'],
                "tokens": 0,
                "feasible": False,
                "protocol_errors": 1,
                "latency": time.time() - start_time,
                "error": str(e)
            })

    # Final Calculations
    total = results["metrics"]["total_runs"]
    if total > 0:
        results["metrics"]["feasibility_score"] = (results["metrics"]["successful_runs"] / total) * 100
        results["metrics"]["avg_tokens"] = results["metrics"]["total_tokens"] / total
        results["metrics"]["avg_errors"] = results["metrics"]["protocol_errors"] / total

    # Save to file for the Agent to read
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to {OUTPUT_FILE}")
    print(f"📊 FINAL METRICS:")
    print(f"   - Feasibility Score: {results['metrics']['feasibility_score']:.1f}%")
    print(f"   - Average Tokens: {results['metrics']['avg_tokens']:.0f}")
    print(f"   - Average Errors: {results['metrics']['avg_errors']:.2f}")

if __name__ == "__main__":
    run_experiment()
