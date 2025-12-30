"""
Token Reduction Experiment Runner

Compares token usage between:
1. Original agents (with accumulation bug fixed)
2. Optimized agents (condensed backstories, lower max_iter, GPT-4o-mini)

Usage:
    poetry run python experiment_comparison.py
"""

import os
import time
import json
from crewai import Crew, Process

# Configuration
NUM_RUNS = 15  # Full test with 15 runs
OUTPUT_FILE = "experiment_comparison_results.json"

# Test queries (subset for comparison)
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


def run_single_experiment(agents_module, tasks_module, test_case, conversation_id):
    """Run a single experiment and return metrics."""
    agents = agents_module()
    tasks = tasks_module()
    
    # Instantiate agents
    conversational_agent = agents.conversational_agent()
    preferences_agent = agents.preferences_extractor_agent()
    flight_agent = agents.flight_search_agent()
    hotel_agent = agents.hotel_agent()
    attraction_agent = agents.attraction_agent()
    coordinator_agent = agents.itinerary_coordinator_agent()
    
    # Create tasks
    conversation_task = tasks.conversation_task(
        conversational_agent, 
        user_input=test_case['query'],
        conversation_id=conversation_id
    )
    extraction_task = tasks.extraction_task(
        preferences_agent, 
        conversation_id=conversation_id,
        conversation_task=conversation_task
    )
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
    coordination_task = tasks.coordination_task(
        coordinator_agent, 
        conversation_id=conversation_id,
        extraction_task=extraction_task,
        flight_task=flight_task,
        hotel_task=hotel_task,
        attraction_task=attraction_task
    )
    
    crew = Crew(
        agents=[conversational_agent, preferences_agent, flight_agent, 
                hotel_agent, attraction_agent, coordinator_agent],
        tasks=[conversation_task, extraction_task, flight_task, 
               hotel_task, attraction_task, coordination_task],
        verbose=False
    )
    
    start_time = time.time()
    
    try:
        result = crew.kickoff()
        
        # Extract token usage
        tokens = 0
        token_details = {}
        
        if hasattr(result, 'token_usage') and result.token_usage:
            token_usage = result.token_usage
            if isinstance(token_usage, dict):
                tokens = token_usage.get('total_tokens', 0)
                token_details = token_usage
            elif hasattr(token_usage, 'total_tokens'):
                tokens = token_usage.total_tokens
                token_details = {
                    'total_tokens': getattr(token_usage, 'total_tokens', 0),
                    'prompt_tokens': getattr(token_usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(token_usage, 'completion_tokens', 0),
                    'successful_requests': getattr(token_usage, 'successful_requests', 0)
                }
        
        # Check feasibility
        output_str = str(result.raw if hasattr(result, 'raw') else result)
        output_lower = output_str.lower()
        is_feasible = "flight" in output_lower and "hotel" in output_lower
        
        # Protocol errors
        protocol_errors = (
            output_lower.count("error executing") + 
            output_lower.count("invalid parameter") + 
            output_lower.count("api error")
        )
        
        return {
            "success": True,
            "tokens": tokens,
            "token_details": token_details,
            "feasible": is_feasible,
            "protocol_errors": protocol_errors,
            "latency": time.time() - start_time
        }
        
    except Exception as e:
        return {
            "success": False,
            "tokens": 0,
            "feasible": False,
            "protocol_errors": 1,
            "latency": time.time() - start_time,
            "error": str(e)
        }


def run_comparison_experiment():
    """Compare original vs optimized agents."""
    
    # Import modules
    from agents import TripPlannerAgents
    from agents_optimized import TripPlannerAgentsOptimized
    from tasks import TripPlannerTasks
    
    results = {
        "experiment_info": {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "num_runs": NUM_RUNS,
            "configurations": ["original_fixed", "optimized"]
        },
        "original_fixed": {
            "description": "Original agents with accumulation bug fixed",
            "runs": [],
            "metrics": {}
        },
        "optimized": {
            "description": "Optimized agents (shorter backstories, lower max_iter, GPT-4o-mini)",
            "runs": [],
            "metrics": {}
        }
    }
    
    print("=" * 60)
    print("🔬 TOKEN REDUCTION EXPERIMENT")
    print("=" * 60)
    
    # Run original (fixed) configuration
    print("\n📊 PHASE 1: Original Agents (Bug Fixed)")
    print("-" * 40)
    
    for i in range(NUM_RUNS):
        test_case = TEST_QUERIES[i % len(TEST_QUERIES)]
        conversation_id = f"original_{test_case['id']}_{i}"
        
        print(f"  Run {i+1}/{NUM_RUNS}: {test_case['id']}...", end=" ", flush=True)
        
        run_result = run_single_experiment(
            TripPlannerAgents, TripPlannerTasks, 
            test_case, conversation_id
        )
        run_result["query_id"] = test_case['id']
        results["original_fixed"]["runs"].append(run_result)
        
        print(f"✅ {run_result['tokens']:,} tokens")
    
    # Run optimized configuration
    print("\n📊 PHASE 2: Optimized Agents")
    print("-" * 40)
    
    for i in range(NUM_RUNS):
        test_case = TEST_QUERIES[i % len(TEST_QUERIES)]
        conversation_id = f"optimized_{test_case['id']}_{i}"
        
        print(f"  Run {i+1}/{NUM_RUNS}: {test_case['id']}...", end=" ", flush=True)
        
        run_result = run_single_experiment(
            TripPlannerAgentsOptimized, TripPlannerTasks,
            test_case, conversation_id
        )
        run_result["query_id"] = test_case['id']
        results["optimized"]["runs"].append(run_result)
        
        print(f"✅ {run_result['tokens']:,} tokens")
    
    # Calculate metrics for each configuration
    for config in ["original_fixed", "optimized"]:
        runs = results[config]["runs"]
        successful = [r for r in runs if r.get("success", False)]
        
        if runs:
            total_tokens = sum(r["tokens"] for r in runs)
            avg_tokens = total_tokens / len(runs)
            feasibility = sum(1 for r in runs if r.get("feasible", False)) / len(runs) * 100
            avg_latency = sum(r["latency"] for r in runs) / len(runs)
            
            results[config]["metrics"] = {
                "total_runs": len(runs),
                "successful_runs": len(successful),
                "total_tokens": total_tokens,
                "avg_tokens": avg_tokens,
                "feasibility_score": feasibility,
                "avg_latency": avg_latency,
                "total_errors": sum(r.get("protocol_errors", 0) for r in runs)
            }
    
    # Calculate improvement
    orig_avg = results["original_fixed"]["metrics"].get("avg_tokens", 0)
    opt_avg = results["optimized"]["metrics"].get("avg_tokens", 0)
    
    if orig_avg > 0:
        reduction_pct = ((orig_avg - opt_avg) / orig_avg) * 100
        results["comparison"] = {
            "original_avg_tokens": orig_avg,
            "optimized_avg_tokens": opt_avg,
            "token_reduction_pct": reduction_pct,
            "tokens_saved_per_query": orig_avg - opt_avg
        }
    
    # Save results
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n{'Configuration':<25} {'Avg Tokens':>15} {'Feasibility':>12}")
    print("-" * 52)
    print(f"{'Original (Fixed)':<25} {orig_avg:>15,.0f} {results['original_fixed']['metrics'].get('feasibility_score', 0):>11.0f}%")
    print(f"{'Optimized':<25} {opt_avg:>15,.0f} {results['optimized']['metrics'].get('feasibility_score', 0):>11.0f}%")
    print("-" * 52)
    
    if orig_avg > 0:
        print(f"\n🎯 Token Reduction: {reduction_pct:.1f}%")
        print(f"💰 Tokens Saved Per Query: {orig_avg - opt_avg:,.0f}")
    
    print(f"\n📄 Results saved to: {OUTPUT_FILE}")
    
    return results


if __name__ == "__main__":
    run_comparison_experiment()
