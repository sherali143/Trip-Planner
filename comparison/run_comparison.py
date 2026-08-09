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
from src.core.http_cache import cache_summary, get_mode


def run_scenario(scenario: dict, runner_fn, label: str) -> dict:
    """Run a single scenario with a given runner function."""
    print(f"\n{'='*70}")
    print(f"  [{label}] {scenario['id']}: {scenario['name']}")
    print(f"{'='*70}")

    try:
        result = runner_fn(scenario["input"], scenario["id"])
        result["scenario_id"] = scenario["id"]
        result["scenario_name"] = scenario["name"]
        result["runner"] = label
        status = "OK" if result.get("success") else "FAIL"
        print(f"  Result: {status} | Latency: {result.get('latency', 0):.1f}s "
              f"| LLM calls: {result.get('llm_calls', 0)} "
              f"| tokens: {result.get('total_tokens', 0)} "
              f"| ${result.get('cost_usd', 0):.4f}")
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

    # Optional scenario filter: `python -m comparison.run_comparison SC-01 SC-04`.
    # Lets a run be repeated over only the scenarios whose API responses are
    # already recorded, so the comparison can be re-run at zero API cost while
    # the monthly quota is being conserved for uncached scenarios.
    wanted = {a.upper() for a in sys.argv[1:] if a.upper().startswith("SC-")}
    scenarios = [s for s in SCENARIOS if s["id"] in wanted] if wanted else list(SCENARIOS)
    if wanted and not scenarios:
        print(f"No scenarios matched {sorted(wanted)}. Known ids: {[s['id'] for s in SCENARIOS]}")
        return None

    print("\n" + "="*70)
    print("  TRIP PLANNER ARCHITECTURE COMPARISON")
    print(f"  {len(scenarios)} scenario(s) x 2 architectures  |  API mode: {get_mode()}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    overall_start = time.time()

    for scenario in scenarios:
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
        n = max(len(successes), 1)
        all_n = max(len(results), 1)
        return {
            "total": len(results),
            "success": len(successes),
            "fail": len(results) - len(successes),
            "success_rate_pct": round(len(successes) / all_n * 100, 1),
            # Averaged over successes only, so a run that fails fast cannot look
            # "fast". The all-scenario figures below are the unbiased view.
            "avg_latency": sum(r.get("latency", 0) for r in successes) / n,
            "avg_llm_calls": sum(r.get("llm_calls", 0) for r in successes) / n,
            "avg_total_tokens": sum(r.get("total_tokens", 0) for r in successes) / n,
            "avg_cost_usd": round(sum(r.get("cost_usd", 0) for r in successes) / n, 6),
            "total_latency": sum(r.get("latency", 0) for r in successes),
            "total_llm_calls": sum(r.get("llm_calls", 0) for r in successes),
            "total_tokens": sum(r.get("total_tokens", 0) for r in successes),
            "total_cost_usd": round(sum(r.get("cost_usd", 0) for r in results), 6),
            "avg_latency_all_scenarios": sum(r.get("latency", 0) for r in results) / all_n,
            "avg_llm_calls_all_scenarios": sum(r.get("llm_calls", 0) for r in results) / all_n,
            "llm_failures": sum(r.get("llm", {}).get("llm_failures", 0) for r in results),
        }

    b_agg = aggregate(baseline_results)
    o_agg = aggregate(optimized_results)

    comparison = {
        "timestamp": datetime.now().isoformat(),
        "total_scenarios": len(scenarios),
        "scenario_ids": [s["id"] for s in scenarios],
        "total_time_s": round(total_time, 1),
        # Provenance: which model produced these numbers and whether the API
        # layer was live or replayed. Required for the results to be reproducible.
        "provenance": {
            "model": os.getenv("GEMINI_MODEL", "unknown"),
            "api_mode": get_mode(),
            "api_cache": cache_summary(),
        },
        "baseline": b_agg,
        "optimized": o_agg,
        "improvement": {
            "latency_pct": round((1 - o_agg["avg_latency"] / max(b_agg["avg_latency"], 0.001)) * 100, 1),
            "llm_calls_pct": round((1 - o_agg["avg_llm_calls"] / max(b_agg["avg_llm_calls"], 0.001)) * 100, 1),
            "tokens_pct": round((1 - o_agg["avg_total_tokens"] / max(b_agg["avg_total_tokens"], 0.001)) * 100, 1),
            "cost_pct": round((1 - o_agg["avg_cost_usd"] / max(b_agg["avg_cost_usd"], 1e-9)) * 100, 1),
            "success_rate_diff": round(o_agg["success_rate_pct"] - b_agg["success_rate_pct"], 1),
        },
        "baseline_details": baseline_results,
        "optimized_details": optimized_results
    }

    # Save results
    out_path = "comparison/results/comparison_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
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
    print(f"  {'Avg LLM calls (measured)':<30} {b_agg['avg_llm_calls']:<20.1f} {o_agg['avg_llm_calls']:<20.1f}")
    print(f"  {'Avg tokens':<30} {b_agg['avg_total_tokens']:<20.0f} {o_agg['avg_total_tokens']:<20.0f}")
    print(f"  {'Avg cost (USD)':<30} {b_agg['avg_cost_usd']:<20.5f} {o_agg['avg_cost_usd']:<20.5f}")
    print(f"  {'Total LLM calls':<30} {b_agg['total_llm_calls']:<20} {o_agg['total_llm_calls']:<20}")
    print(f"  {'Total latency (s)':<30} {b_agg['total_latency']:<20.1f} {o_agg['total_latency']:<20.1f}")
    print(f"{'='*70}")
    print(f"  IMPROVEMENT (optimized vs baseline):")
    print(f"    Latency:   {comparison['improvement']['latency_pct']}% faster")
    print(f"    LLM calls: {comparison['improvement']['llm_calls_pct']}% fewer")
    print(f"    Tokens:    {comparison['improvement']['tokens_pct']}% fewer")
    print(f"    Cost:      {comparison['improvement']['cost_pct']}% cheaper")
    print(f"    Success:   {comparison['improvement']['success_rate_diff']}% difference")
    print(f"{'='*70}")
    print(f"  API mode: {comparison['provenance']['api_mode']} | "
          f"live calls: {comparison['provenance']['api_cache']['live_calls']} | "
          f"cache hits: {comparison['provenance']['api_cache']['cache_hits']}")
    print(f"{'='*70}")

    return comparison


if __name__ == "__main__":
    main()
