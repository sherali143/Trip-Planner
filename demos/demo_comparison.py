"""
Dissertation Demo: Side-by-Side Comparison of all four architectures.

Runs the same request through every arm and prints one metrics table. This is
the viva demo: it shows the progression from no tools at all, through naive and
then tuned multi-agent, to direct execution.

Usage:
    # free — replays recorded API responses, spends no monthly quota
    TRIP_PLANNER_API_MODE=replay python demo_comparison.py

    # skip the "press Enter" pauses
    python demo_comparison.py --no-pause

Set TRIP_PLANNER_MAX_LIVE_CALLS to cap live API usage if not replaying; the
flight and hotel free tiers are 30 and 50 calls PER MONTH.
"""

import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(override=True)

# This script lives in a subdirectory, so the project root is not on
# sys.path when it is run directly. Add it before importing src/comparison.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import src  # applies logging defaults so the Gemini key is not printed
from src.core.http_cache import cache_summary, get_mode

SAMPLE_INPUT = (
    "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing "
    "2026-08-15, budget 800 USD. Interests: history, food, shopping."
)

PAUSE = "--no-pause" not in sys.argv


def pause(message: str) -> None:
    if PAUSE:
        input(f"\n  {message}")


print("=" * 78)
print("  DISSERTATION DEMO: ARCHITECTURE COMPARISON")
print("  Same input · Four architectures · Side-by-side measured metrics")
print("=" * 78)
print(f"\n  INPUT: {SAMPLE_INPUT}")
print(f"  API mode: {get_mode()}")
if get_mode() != "replay":
    print("  WARNING: not in replay mode — this run may spend monthly API quota.")
    print("           Re-run with TRIP_PLANNER_API_MODE=replay to use recordings.")

# Imported lazily-ish but together, so an import error surfaces before any run.
from comparison.architecture_single_llm import plan_trip_single_llm
from comparison.architecture_6agent import plan_trip_baseline
from comparison.architecture_6agent_optimized import plan_trip_optimized_6agent
from comparison.architecture_3agent import plan_trip_optimized
from comparison.metrics import score_groundedness

ARMS = [
    ("A", "SINGLE LLM (no agents, no tools)", plan_trip_single_llm),
    ("B", "6 AGENTS — naive", plan_trip_baseline),
    ("C", "6 AGENTS — tuned", plan_trip_optimized_6agent),
    ("D", "3 AGENTS + direct API", plan_trip_optimized),
]

results = {}
for code, name, runner in ARMS:
    print("\n" + "=" * 78)
    print(f"  RUN {code}: {name}")
    print("=" * 78)
    pause("Press Enter to start...")

    started = time.time()
    try:
        results[code] = runner(SAMPLE_INPUT, "demo")
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        results[code] = {"success": False, "error": str(exc), "latency": time.time() - started}
        continue

    r = results[code]
    print(f"\n  Completed in {r.get('latency', 0):.1f}s | "
          f"{r.get('llm_calls', 0)} LLM calls | {r.get('total_tokens', 0):,} tokens")

# Score every arm against what arm D actually retrieved.
truth = (results.get("D") or {}).get("ground_truth") or {}
if truth.get("hotels") or truth.get("airlines"):
    for code in results:
        results[code]["groundedness"] = score_groundedness(results[code].get("result", ""), truth)

print("\n" + "=" * 78)
print("  FINAL COMPARISON")
print("=" * 78)
head = f"  {'Arm':<34}{'LLM':>5}{'Tokens':>10}{'Cost $':>10}{'Secs':>8}{'Real $':>8}"
print(head)
print("  " + "-" * (len(head) - 2))
for code, name, _ in ARMS:
    r = results.get(code) or {}
    grounded = (r.get("groundedness") or {}).get("prices_grounded_pct")
    print(f"  {code + ' — ' + name:<34}"
          f"{r.get('llm_calls', 0):>5}"
          f"{r.get('total_tokens', 0):>10,}"
          f"{r.get('cost_usd', 0):>10.5f}"
          f"{r.get('latency', 0):>8.1f}"
          f"{(f'{grounded:.0f}%' if grounded is not None else 'n/a'):>8}")

print("\n  'Real $' = share of prices quoted in the itinerary that match a fare or")
print("  nightly rate the APIs actually returned. The tool-less arm scores 0%:")
print("  every figure it printed was invented.")

d, c = results.get("D") or {}, results.get("C") or {}
if d.get("llm_calls") and c.get("llm_calls"):
    print("\n  HEADLINE — D vs C (direct execution vs TUNED multi-agent):")
    print(f"    LLM calls {(1 - d['llm_calls']/c['llm_calls'])*100:.0f}% fewer   "
          f"({c['llm_calls']} -> {d['llm_calls']})")
    if c.get("latency"):
        print(f"    Latency   {(1 - d['latency']/c['latency'])*100:.0f}% faster  "
              f"({c['latency']:.0f}s -> {d['latency']:.0f}s)")

print("\n" + "=" * 78)
print("  KEY POINTS FOR THE VIVA")
print("=" * 78)
print("  1. The A2A protocol and MCP layer are IDENTICAL across all arms.")
print("     Only the data-fetching layer changes. The protocol design is")
print("     therefore independent of how data is retrieved — that is the")
print("     contribution, not the agent count.")
print("  2. Tuning the multi-agent arm (C vs B) removes most of its cost. The")
print("     naive penalty was implementation, not architecture — so the")
print("     comparison is against a fair baseline, not a straw man.")
print("  3. Cost alone is not the deciding metric. Arm A is cheap because it")
print("     calls nothing and invents its data.")
print(f"\n  API calls spent by this run: {cache_summary()['live_calls']}")
print("=" * 78)
