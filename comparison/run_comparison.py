"""
Comparison Runner: runs both baseline (6-agent) and optimized (3-agent + direct API)
on all test scenarios, collects metrics, and saves results.
"""

import os, sys, json, time, traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Fix Windows console encoding for CrewAI emoji output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
os.environ["CREWAI_TRACING_ENABLED"] = "false"

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

from comparison.scenarios import SCENARIOS
from comparison.architecture_6agent import plan_trip_baseline
from comparison.architecture_3agent import plan_trip_optimized


def run_scenario(scenario: dict, runner_fn, label: str) -> dict:
    """Run a single scenario with a given runner function."""
    print(f"\n{'='*70}")
    print(f"  [{label}] {scenario['id']}: {scenario['name']}")
    print(f"{'='*70}")

    try:
        result = runner_fn(scenario["input"])
        result["scenario_id"] = scenario["id"]
        result["scenario_name"] = scenario["name"]
        result["runner"] = label
        status = "OK" if result.get("success") else "FAIL"
        print(f"  Result: {status} | Latency: {result.get('latency', 0):.1f}s | LLM: {result.get('llm_calls', 0)}")
        return result
    except Exception as e:
        print(f"  CRASHED: {e}")
        traceback.print_exc()
        return {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "runner": label,
            "success": False,
            "error": str(e),
            "latency": 0,
            "llm_calls": 0,
            "arch": label
        }


def main():
    os.makedirs("comparison/results", exist_ok=True)

    baseline_results = []
    optimized_results = []

    print("\n" + "="*70)
    print("  TRIP PLANNER ARCHITECTURE COMPARISON")
    print(f"  {len(SCENARIOS)} scenarios x 2 architectures")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    overall_start = time.time()

    for scenario in SCENARIOS:
        # Run baseline (6-agent)
        b_result = run_scenario(scenario, plan_trip_baseline, "BASELINE (6 agents)")
        baseline_results.append(b_result)

        # Run optimized (3-agent + direct API)
        o_result = run_scenario(scenario, plan_trip_optimized, "OPTIMIZED (3 agents)")
        optimized_results.append(o_result)

    total_time = time.time() - overall_start

    # Aggregate metrics
    def aggregate(results):
        successes = [r for r in results if r.get("success")]
        return {
            "total": len(results),
            "success": len(successes),
            "fail": len(results) - len(successes),
            "avg_latency": sum(r.get("latency", 0) for r in successes) / max(len(successes), 1),
            "avg_llm_calls": sum(r.get("llm_calls", 0) for r in successes) / max(len(successes), 1),
            "total_latency": sum(r.get("latency", 0) for r in successes),
            "total_llm_calls": sum(r.get("llm_calls", 0) for r in successes),
        }

    b_agg = aggregate(baseline_results)
    o_agg = aggregate(optimized_results)

    comparison = {
        "timestamp": datetime.now().isoformat(),
        "total_scenarios": len(SCENARIOS),
        "total_time_s": round(total_time, 1),
        "baseline": b_agg,
        "optimized": o_agg,
        "improvement": {
            "latency_pct": round((1 - o_agg["avg_latency"] / max(b_agg["avg_latency"], 0.001)) * 100, 1),
            "llm_calls_pct": round((1 - o_agg["avg_llm_calls"] / max(b_agg["avg_llm_calls"], 0.001)) * 100, 1),
            "success_rate_diff": round(o_agg["success"] / max(o_agg["total"], 1) * 100 -
                                       b_agg["success"] / max(b_agg["total"], 1) * 100, 1)
        },
        "baseline_details": baseline_results,
        "optimized_details": optimized_results
    }

    # Save results
    out_path = "comparison/results/comparison_results.json"
    with open(out_path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"  COMPARISON COMPLETE")
    print(f"  Results saved to: {out_path}")
    print(f"  Total time: {total_time:.0f}s")
    print(f"{'='*70}")
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Metric':<30} {'Baseline (6 agents)':<20} {'Optimized (3 agents)':<20}")
    print(f"  {'─'*30} {'─'*20} {'─'*20}")
    print(f"  {'Success rate':<30} {b_agg['success']}/{b_agg['total']:<16} {o_agg['success']}/{o_agg['total']:<16}")
    print(f"  {'Avg latency (s)':<30} {b_agg['avg_latency']:<20.1f} {o_agg['avg_latency']:<20.1f}")
    print(f"  {'Avg LLM calls':<30} {b_agg['avg_llm_calls']:<20.1f} {o_agg['avg_llm_calls']:<20.1f}")
    print(f"  {'Total LLM calls':<30} {b_agg['total_llm_calls']:<20} {o_agg['total_llm_calls']:<20}")
    print(f"  {'Total latency (s)':<30} {b_agg['total_latency']:<20.1f} {o_agg['total_latency']:<20.1f}")
    print(f"{'='*70}")
    print(f"  IMPROVEMENT (optimized vs baseline):")
    print(f"    Latency:   {comparison['improvement']['latency_pct']}% faster")
    print(f"    LLM calls: {comparison['improvement']['llm_calls_pct']}% fewer")
    print(f"    Success:   {comparison['improvement']['success_rate_diff']}% difference")
    print(f"{'='*70}")

    return comparison


if __name__ == "__main__":
    main()
