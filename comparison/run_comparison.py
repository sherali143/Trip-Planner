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
from comparison.architecture_6agent_optimized import plan_trip_optimized_6agent
from comparison.architecture_single_llm import plan_trip_single_llm
from comparison.metrics import score_groundedness
from src.core.http_cache import cache_summary, get_mode

# Ordered least-to-most engineered so the results table reads as a progression:
# no tools at all -> naive multi-agent -> tuned multi-agent -> direct execution.
ARMS = [
    ("A", "SINGLE LLM", plan_trip_single_llm),
    ("B", "6 AGENTS (naive)", plan_trip_baseline),
    ("C", "6 AGENTS (optimised)", plan_trip_optimized_6agent),
    ("D", "3 AGENTS (direct API)", plan_trip_optimized),
]


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

    results_by_arm = {code: [] for code, _, _ in ARMS}

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
    print(f"  {len(scenarios)} scenario(s) x {len(ARMS)} architectures  |  API mode: {get_mode()}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    overall_start = time.time()

    # Execute arm D first for each scenario, then report in ARMS order.
    #
    # D fetches every data type once, deterministically, with canonical
    # parameters. Running it first populates the HTTP cache, so the agent arms
    # that follow mostly replay rather than spending live quota on the same
    # queries. Reversed (agents first), each arm's ReAct loop can issue slightly
    # different parameters and burn several months' allowance in one run.
    execution_order = sorted(ARMS, key=lambda a: a[0] != "D")

    for scenario in scenarios:
        for code, name, runner in execution_order:
            results_by_arm[code].append(run_scenario(scenario, runner, f"{code} — {name}"))

        # Groundedness: score every arm's itinerary against the data arm D
        # actually retrieved for this scenario. Arms with no tool access have
        # nothing real to cite, which is exactly what this exposes.
        truth = (results_by_arm["D"][-1] or {}).get("ground_truth") or {}
        if truth.get("hotels") or truth.get("airlines"):
            for code, _, _ in ARMS:
                result = results_by_arm[code][-1]
                result["groundedness"] = score_groundedness(result.get("result", ""), truth)
        else:
            print("  ! no ground truth retrieved for this scenario — groundedness skipped")

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
            # Bookability pillar: cheapness means nothing if the itinerary
            # refers to venues and fares that were never retrieved.
            "grounded_itineraries": sum(
                1 for r in results if (r.get("groundedness") or {}).get("uses_real_data")
            ),
            "avg_hotels_grounded": round(sum(
                (r.get("groundedness") or {}).get("hotels_grounded", 0) for r in successes
            ) / n, 2),
            "avg_airlines_grounded": round(sum(
                (r.get("groundedness") or {}).get("airlines_grounded", 0) for r in successes
            ) / n, 2),
            "avg_prices_grounded_pct": round(sum(
                (r.get("groundedness") or {}).get("prices_grounded_pct", 0) for r in successes
            ) / n, 1),
        }

    agg_by_arm = {code: aggregate(results_by_arm[code]) for code, _, _ in ARMS}
    arm_names = {code: name for code, name, _ in ARMS}

    def gain(reference: str, candidate: str) -> dict:
        """Percentage improvement of `candidate` over `reference`."""
        ref, cand = agg_by_arm[reference], agg_by_arm[candidate]
        pct = lambda a, b, floor=0.001: round((1 - b / max(a, floor)) * 100, 1)
        return {
            "vs": reference,
            "latency_pct": pct(ref["avg_latency"], cand["avg_latency"]),
            "llm_calls_pct": pct(ref["avg_llm_calls"], cand["avg_llm_calls"]),
            "tokens_pct": pct(ref["avg_total_tokens"], cand["avg_total_tokens"]),
            "cost_pct": pct(ref["avg_cost_usd"], cand["avg_cost_usd"], 1e-9),
            "success_rate_diff": round(cand["success_rate_pct"] - ref["success_rate_pct"], 1),
        }

    # Kept for backwards compatibility with anything reading the two-arm shape.
    b_agg, o_agg = agg_by_arm["B"], agg_by_arm["D"]

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
        "arms": {code: {"name": arm_names[code], **agg_by_arm[code]} for code, _, _ in ARMS},
        "improvements": {
            # The headline claim: direct execution vs the TUNED multi-agent arm.
            # Quoting D against naive B alone invites "your baseline was badly
            # configured"; D vs C answers that objection directly.
            "D_vs_C": gain("C", "D"),
            "D_vs_B": gain("B", "D"),
            "C_vs_B": gain("B", "C"),
        },
        "baseline": b_agg,
        "optimized": o_agg,
        "improvement": gain("B", "D"),
        "details_by_arm": results_by_arm,
        "baseline_details": results_by_arm["B"],
        "optimized_details": results_by_arm["D"],
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
    header = (f"  {'Arm':<26}{'OK':>6}{'LLM':>6}{'Tokens':>9}{'Cost $':>9}"
              f"{'Secs':>7}{'Real':>7}{'$ ok':>7}")
    print(header)
    print("  " + "─" * (len(header) - 2))
    for code, name, _ in ARMS:
        a = agg_by_arm[code]
        print(f"  {code + ' — ' + name:<26}{a['success']}/{a['total']:<4}"
              f"{a['avg_llm_calls']:>6.1f}{a['avg_total_tokens']:>9.0f}"
              f"{a['avg_cost_usd']:>9.5f}{a['avg_latency']:>7.1f}"
              f"{str(a['grounded_itineraries']) + '/' + str(a['total']):>7}"
              f"{a['avg_prices_grounded_pct']:>6.0f}%")
    print("  Real = itineraries citing data actually retrieved from the APIs")
    print("  $ ok = quoted prices matching a real fare or nightly rate")
    print(f"{'='*70}")
    for key, caption in [
        ("D_vs_C", "D (3-agent) vs C (6-agent TUNED)  <- headline claim"),
        ("D_vs_B", "D (3-agent) vs B (6-agent naive)"),
        ("C_vs_B", "C (tuned) vs B (naive)            <- value of tuning"),
    ]:
        g = comparison["improvements"][key]
        print(f"  {caption}")
        print(f"    LLM calls {g['llm_calls_pct']:>6}% fewer | tokens {g['tokens_pct']:>6}% fewer | "
              f"cost {g['cost_pct']:>6}% cheaper | latency {g['latency_pct']:>6}% faster")
    print(f"{'='*70}")
    print(f"  API mode: {comparison['provenance']['api_mode']} | "
          f"live calls: {comparison['provenance']['api_cache']['live_calls']} | "
          f"cache hits: {comparison['provenance']['api_cache']['cache_hits']}")
    print(f"{'='*70}")

    return comparison


if __name__ == "__main__":
    main()
