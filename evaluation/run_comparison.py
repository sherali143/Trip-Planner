"""
Runs the four approaches, repeats them, and writes the measured numbers.

Output goes to evaluation/results/, which is what every document reads.
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

from evaluation.scenarios import SCENARIOS
from evaluation.arm_b_six_agent_naive import run_six_agent_naive
from evaluation.arm_d_three_agent_direct import run_three_agent_direct
from evaluation.arm_c_six_agent_tuned import run_six_agent_tuned
from evaluation.arm_a_single_llm import run_single_llm
from evaluation.metrics import score_groundedness
from trip_planner.core.http_cache import cache_summary, get_mode
from trip_planner.core.llm_metrics import BUDGET

# Ordered least-to-most engineered so the results table reads as a progression:
# no tools at all -> naive multi-agent -> tuned multi-agent -> direct execution.
ARMS = [
    ("A", "SINGLE LLM", run_single_llm),
    ("B", "6 AGENTS (naive)", run_six_agent_naive),
    ("C", "6 AGENTS (optimised)", run_six_agent_tuned),
    ("D", "3 AGENTS (direct API)", run_three_agent_direct),
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


RESULTS_PATH = "evaluation/results/comparison_results.json"


def _load_previous():
    """Previously completed scenarios, so a stopped run can be resumed."""
    if not os.path.exists(RESULTS_PATH):
        return {}
    try:
        with open(RESULTS_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    by_arm = data.get("details_by_arm") or {}
    return {code: {r.get("scenario_id"): r for r in rows if r.get("scenario_id")}
            for code, rows in by_arm.items()}


def _dispersion(values: list) -> dict:
    """
    Mean, standard deviation and a 95% confidence interval for one metric.

    Reported because a single observation cannot support a claim about a
    difference. With repeats the question "is this gap real or is it noise?"
    becomes answerable, which is the whole reason repeats exist.

    The interval uses Student's t, not 1.96 sigma: at five runs the normal
    approximation is meaningfully too narrow, and quoting an interval that is
    too tight is worse than quoting none.
    """
    n = len(values)
    if n == 0:
        return {"n": 0}
    mean = sum(values) / n
    if n == 1:
        return {"n": 1, "mean": mean, "sd": None, "ci95_low": None,
                "ci95_high": None, "cv_pct": None}
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    sd = variance ** 0.5
    # Two-tailed t at 95% for small samples; falls back to 1.96 beyond the table.
    T = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447,
         8: 2.365, 9: 2.306, 10: 2.262}
    t = T.get(n - 1, 1.96)
    margin = t * sd / (n ** 0.5)
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
        # Coefficient of variation: how noisy this metric is relative to its own
        # size, which is what decides whether a small gap between arms is real.
        "cv_pct": round(sd / mean * 100, 1) if mean else None,
    }


def _save(payload):
    os.makedirs("evaluation/results", exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)


def main():
    os.makedirs("evaluation/results", exist_ok=True)

    results_by_arm = {code: [] for code, _, _ in ARMS}

    # Optional scenario filter: `python -m evaluation.run_comparison SC-01 SC-04`.
    # Lets a run be repeated over only the scenarios whose API responses are
    # already recorded, so the comparison can be re-run at zero API cost while
    # the monthly quota is being conserved for uncached scenarios.
    # `--repeats N` runs every scenario N times so the spread can be measured.
    # One observation per arm establishes an ordering and nothing about whether a
    # small difference is real, which is the limitation this flag removes.
    repeats = 1
    for arg in sys.argv[1:]:
        if arg.startswith("--repeats"):
            repeats = max(1, int(arg.split("=", 1)[1] if "=" in arg
                                 else sys.argv[sys.argv.index(arg) + 1]))

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

    # Resume: reuse scenarios already completed in a previous run rather than
    # paying for them again. A full four-arm run over 20 scenarios costs about
    # 620 LLM requests, so a run that stops part way — daily quota, network, a
    # crash — must not throw away what it already bought.
    previous = _load_previous()
    reused = 0

    # Roughly what one scenario costs across all arms, used to decide whether
    # there is enough budget left to start another one.
    per_scenario_llm = int(os.getenv("TRIP_PLANNER_LLM_PER_SCENARIO", "35"))
    stopped_early = None

    for scenario in scenarios:
        sid = scenario["id"]

        done_everywhere = all(sid in previous.get(code, {}) for code, _, _ in ARMS)
        if done_everywhere and "--force" not in sys.argv:
            for code, _, _ in ARMS:
                results_by_arm[code].append(previous[code][sid])
            reused += 1
            print(f"  [skip] {sid} already recorded — pass --force to redo it")
            continue

        if BUDGET.would_exceed(per_scenario_llm):
            stopped_early = (
                f"Stopped before {sid}: starting it would pass the "
                f"TRIP_PLANNER_MAX_LLM_CALLS ceiling "
                f"({BUDGET.calls} requests used). Completed scenarios are saved "
                f"— re-run the same command later to continue from here."
            )
            print(f"\n  ! {stopped_early}\n")
            break

        for attempt in range(repeats):
            if repeats > 1:
                print(f"\n  --- {sid}: repeat {attempt + 1} of {repeats} ---")

            for code, name, runner in execution_order:
                row = run_scenario(scenario, runner, f"{code} — {name}")
                # Which repeat this row belongs to, so the aggregate can compute a
                # spread rather than assuming one observation per scenario.
                row["repeat"] = attempt
                results_by_arm[code].append(row)
            BUDGET.pace()

            # Groundedness: score every arm's itinerary against the data arm D
            # actually retrieved for this repeat. Arms with no tool access have
            # nothing real to cite, which is exactly what this exposes.
            truth = (results_by_arm["D"][-1] or {}).get("ground_truth") or {}
            if truth.get("hotels") or truth.get("airlines"):
                for code, _, _ in ARMS:
                    result = results_by_arm[code][-1]
                    result["groundedness"] = score_groundedness(
                        result.get("result", ""), truth)
            else:
                print("  ! no ground truth retrieved for this repeat — "
                      "groundedness skipped")

            # Save after every repeat — and after scoring, so the checkpoint is
            # complete — rather than once at the end. An interrupted run then
            # keeps everything it has already paid for.
            _save({
                "status": "in_progress",
                "completed_scenarios": [r.get("scenario_id")
                                        for r in results_by_arm["D"]],
                "details_by_arm": results_by_arm,
            })

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
            # Spread across repeats. Without these an arm's mean is a point with
            # no error bar, and a small gap between two arms cannot be told from
            # run-to-run noise.
            "spread": {
                "llm_calls": _dispersion([r.get("llm_calls", 0) for r in successes]),
                "total_tokens": _dispersion([r.get("total_tokens", 0) for r in successes]),
                "cost_usd": _dispersion([r.get("cost_usd", 0) for r in successes]),
                "latency": _dispersion([r.get("latency", 0) for r in successes]),
                "prices_grounded_pct": _dispersion([
                    (r.get("groundedness") or {}).get("prices_grounded_pct", 0)
                    for r in successes]),
            },
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

    # Record how complete this result set is, so a partial run is never
    # mistaken for a finished evaluation when the numbers are written up.
    comparison["status"] = "partial" if stopped_early else "complete"
    comparison["scenarios_reused_from_previous_run"] = reused
    comparison["llm_requests_this_run"] = BUDGET.calls
    if stopped_early:
        comparison["stopped_early"] = stopped_early

    out_path = RESULTS_PATH
    _save(comparison)

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
    cache_info = comparison["provenance"]["api_cache"]
    budget = cache_info.get("live_call_budget")
    print(f"  API mode: {comparison['provenance']['api_mode']} | "
          f"live calls: {cache_info['live_calls']}"
          f"{'/' + str(budget) if budget is not None else ' (NO BUDGET GUARD SET)'} | "
          f"cache hits: {cache_info['cache_hits']}")
    print(f"{'='*70}")

    return comparison


if __name__ == "__main__":
    main()
