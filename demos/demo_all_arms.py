"""
Run all four architectures on the same request, side by side.

This is the viva demonstration. It shows the progression from no tools at all,
through naive and then tuned multi-agent, to direct execution — and finishes
with one table comparing what each one cost and whether its itinerary refers to
anything real.

    python demos/demo_all_arms.py              # pauses between arms
    python demos/demo_all_arms.py --no-pause   # runs straight through

Set TRIP_PLANNER_API_MODE=replay first to serve travel data from the recorded
responses. The output is real captured data; it simply spends no monthly quota
and cannot fail on a network hiccup mid-demonstration. Model requests still run
for real, so they still cost Gemini free-tier quota.

Everything here is inside main(). An earlier version ran at module level, which
meant that importing this file — as any tooling, test collector or IDE might —
silently started a four-arm run and spent API quota.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(override=True)

import src  # applies logging defaults so the Gemini key is never printed
from comparison.arm_a_single_llm import run_single_llm
from comparison.arm_b_six_agent_naive import run_six_agent_naive
from comparison.arm_c_six_agent_tuned import run_six_agent_tuned
from comparison.arm_d_three_agent_direct import run_three_agent_direct
from comparison.metrics import score_groundedness
from src.core.http_cache import cache_summary, get_mode

SAMPLE_INPUT = (
    "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing "
    "2026-08-15, budget 800 USD. Interests: history, food, shopping."
)

ARMS = [
    ("A", "SINGLE LLM (no agents, no tools)", run_single_llm),
    ("B", "6 AGENTS - naive", run_six_agent_naive),
    ("C", "6 AGENTS - tuned", run_six_agent_tuned),
    ("D", "3 AGENTS + direct API", run_three_agent_direct),
]

RULE = "=" * 78


def _run_arm(code: str, name: str, runner, should_pause: bool) -> dict:
    print(f"\n{RULE}\n  RUN {code}: {name}\n{RULE}")
    if should_pause:
        input("\n  Press Enter to start...")

    started = time.time()
    try:
        result = runner(SAMPLE_INPUT, "demo")
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        return {"success": False, "error": str(exc), "latency": time.time() - started}

    # The arms catch their own exceptions and return success=False rather than
    # raising, so without this an unavailable provider prints "Completed ...
    # 0 LLM calls" and reads as a successful run of a very cheap arm.
    if not result.get("success"):
        error = str(result.get("error", "no error recorded"))
        print(f"\n  DID NOT COMPLETE - {error[:200]}")
        if "ip address restriction" in error.lower():
            print("  The API key is restricted to specific IP addresses; this "
                  "machine is not on the list.")
        elif "spending cap" in error.lower() or "billing" in error.lower():
            print("  The model provider has stopped accepting requests for this "
                  "billing period.")
        return result

    print(f"\n  Completed in {result.get('latency', 0):.1f}s | "
          f"{result.get('llm_calls', 0)} LLM calls | "
          f"{result.get('total_tokens', 0):,} tokens")
    return result


def _print_table(results: dict) -> None:
    print(f"\n{RULE}\n  FINAL COMPARISON\n{RULE}")
    head = (f"  {'Arm':<34}{'LLM':>5}{'Tokens':>10}{'Cost $':>10}"
            f"{'Secs':>8}{'Real $':>8}")
    print(head)
    print("  " + "-" * (len(head) - 2))
    for code, name, _ in ARMS:
        row = results.get(code) or {}
        label = f"{code} - {name}"
        if not row.get("success"):
            # A row of zeros would read as a real measurement of a cheap arm.
            print(f"  {label:<34}{'did not complete':>41}")
            continue
        grounded = (row.get("groundedness") or {}).get("prices_grounded_pct")
        print(f"  {label:<34}"
              f"{row.get('llm_calls', 0):>5}"
              f"{row.get('total_tokens', 0):>10,}"
              f"{row.get('cost_usd', 0):>10.5f}"
              f"{row.get('latency', 0):>8.1f}"
              f"{(f'{grounded:.0f}%' if grounded is not None else 'n/a'):>8}")

    print("\n  'Real $' = share of prices quoted in the itinerary that match a fare")
    print("  or nightly rate the APIs actually returned.")


def _print_findings(results: dict) -> None:
    """Report what THIS run measured, never a remembered result."""
    control = (results.get("A") or {}).get("groundedness") or {}
    if control.get("prices_quoted"):
        print(f"\n  Arm A quoted {control['prices_quoted']} prices and matched "
              f"{control['prices_grounded']} of them "
              f"({control['prices_grounded_pct']:.0f}%).")
        print("  It calls no API, so it has nothing real to cite.")

    direct, tuned = results.get("D") or {}, results.get("C") or {}
    if direct.get("llm_calls") and tuned.get("llm_calls"):
        print("\n  HEADLINE - D vs C (direct execution vs TUNED multi-agent):")
        print(f"    LLM calls {(1 - direct['llm_calls'] / tuned['llm_calls']) * 100:.0f}% "
              f"fewer   ({tuned['llm_calls']} -> {direct['llm_calls']})")
        if tuned.get("latency"):
            print(f"    Latency   {(1 - direct['latency'] / tuned['latency']) * 100:.0f}% "
                  f"faster  ({tuned['latency']:.0f}s -> {direct['latency']:.0f}s)")

    print(f"\n{RULE}\n  KEY POINTS FOR THE VIVA\n{RULE}")
    print("  1. The A2A protocol and MCP layer are IDENTICAL across all arms.")
    print("     Only the data-fetching layer changes, so the protocol design is")
    print("     independent of how data is retrieved - that is the contribution,")
    print("     not the agent count.")
    print("  2. Tuning the multi-agent arm (C vs B) removes most of its cost. The")
    print("     naive penalty was implementation, not architecture - so the")
    print("     comparison is against a fair baseline, not a straw man.")
    print("  3. Cost alone is not the deciding metric. Arm A is cheap because it")
    print("     calls nothing and invents its data.")
    print(f"\n  Live API calls spent by this run: {cache_summary()['live_calls']}")
    print(RULE)


def main() -> int:
    should_pause = "--no-pause" not in sys.argv

    print(RULE)
    print("  DISSERTATION DEMO: ARCHITECTURE COMPARISON")
    print("  Same input | Four architectures | Side-by-side measured metrics")
    print(RULE)
    print(f"\n  INPUT: {SAMPLE_INPUT}")
    print(f"  API mode: {get_mode()}")
    if get_mode() != "replay":
        print("  WARNING: not in replay mode - this run may spend monthly API quota.")
        print("           Re-run with TRIP_PLANNER_API_MODE=replay to use recordings.")

    results = {code: _run_arm(code, name, runner, should_pause)
               for code, name, runner in ARMS}

    # Score every arm against what arm D actually retrieved.
    truth = (results.get("D") or {}).get("ground_truth") or {}
    if truth.get("hotels") or truth.get("airlines"):
        for code, row in results.items():
            row["groundedness"] = score_groundedness(row.get("result", ""), truth)

    _print_table(results)
    _print_findings(results)
    return 0 if all(r.get("success") for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
