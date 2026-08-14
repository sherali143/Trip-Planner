"""
Run ONE architecture on a single request, narrating each step.

For demonstrating a single approach in isolation — what it does, in what order,
what it costs, and whether the itinerary it produced refers to anything real.

    python demos/demo_approach.py A     # single LLM, no tools
    python demos/demo_approach.py B     # six agents, naive
    python demos/demo_approach.py C     # six agents, tuned
    python demos/demo_approach.py D     # three agents + direct API

    python demos/demo_approach.py D "Plan 5 nights in Bangkok from Karachi..."

One parametrised script rather than four near-identical ones: the arms differ
in which function is called, not in how a run should be presented, and four
copies of the presentation logic would drift apart.

Set TRIP_PLANNER_API_MODE=replay to use recorded API responses — the output is
real captured data, it simply costs no quota and cannot fail on a network
hiccup mid-demonstration.
"""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import json
import time

if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(override=True)

import src  # applies logging defaults so the API key is never printed
from src.core.http_cache import cache_summary, get_mode

from comparison.arm_a_single_llm import run_single_llm
from comparison.arm_b_six_agent_naive import run_six_agent_naive
from comparison.arm_c_six_agent_tuned import run_six_agent_tuned
from comparison.arm_d_three_agent_direct import run_three_agent_direct
from comparison.metrics import extract_ground_truth, score_groundedness

DEFAULT_REQUEST = (
    "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing "
    "2026-08-15, budget 800 USD. Interests: history, food, shopping."
)

# Each entry: runner, one-line identity, how it works, what it costs you.
APPROACHES = {
    "A": {
        "name": "Single LLM",
        "runner": run_single_llm,
        "what": "One model call. No agents, no tools, no protocol.",
        "how": [
            "The whole request goes to the model in a single prompt.",
            "The model answers from what it already knows.",
            "Nothing is retrieved, so nothing can be checked.",
        ],
        "watch": "Every price it prints is invented. Compare them against arm D's.",
    },
    "B": {
        "name": "Six agents — naive",
        "runner": run_six_agent_naive,
        "what": "The architecture as first built: specialists reason their way to data.",
        "how": [
            "An extractor turns the request into typed JSON.",
            "Flight, hotel and activity specialists each run a reasoning loop:",
            "  decide which tool to use -> call it -> read the result -> repeat.",
            "A coordinator assembles the itinerary from what they found.",
        ],
        "watch": "Tool schemas are re-sent on every loop iteration. The hotel "
                 "specialist alone carries eight of them.",
    },
    "C": {
        "name": "Six agents — tuned",
        "runner": run_six_agent_tuned,
        "what": "The same six agents, configured as the proposal actually specified.",
        "how": [
            "Identical structure to arm B, with four changes:",
            "  one narrow tool per specialist instead of up to eight,",
            "  reasoning capped at 3 iterations instead of 8-15,",
            "  tool results distilled to the few options that matter,",
            "  the three specialists run concurrently rather than in turn.",
        ],
        "watch": "Same agents, same APIs, same data — only the prompt economics "
                 "differ. Compare its cost against arm B.",
    },
    "D": {
        "name": "Three agents + direct API",
        "runner": run_three_agent_direct,
        "what": "The LLM is used only where judgement is needed.",
        "how": [
            "An extractor turns the request into typed JSON.",
            "Plain Python calls the four APIs — no model involved.",
            "A coordinator assembles the itinerary from that data.",
        ],
        "watch": "Retrieval is deterministic. What it loses: it cannot widen the "
                 "dates and search again when results disappoint.",
    },
}

RULE = "=" * 74


def banner(text):
    print(f"\n{RULE}\n  {text}\n{RULE}")


def main():
    args = [a for a in _sys.argv[1:]]
    code = (args[0].upper() if args else "").strip()
    if code not in APPROACHES:
        print(__doc__)
        print("Choose one of: " + ", ".join(f"{k} ({v['name']})"
                                            for k, v in APPROACHES.items()))
        return 1

    request = args[1] if len(args) > 1 else DEFAULT_REQUEST
    spec = APPROACHES[code]

    banner(f"ARM {code}  —  {spec['name']}")
    print(f"\n  {spec['what']}\n")
    print("  How it works:")
    for line in spec["how"]:
        print(f"    {line}")
    print(f"\n  Watch for:\n    {spec['watch']}")

    print(f"\n  Request:\n    {request}")
    print(f"\n  API mode: {get_mode()}", end="")
    if get_mode() != "replay":
        print("   <- NOT replay: this run may spend monthly API quota")
    else:
        print("   (recorded responses; no quota spent)")

    banner("RUNNING")
    started = time.time()
    try:
        result = spec["runner"](request, "demo")
    except Exception as exc:
        print(f"\n  FAILED: {type(exc).__name__}: {exc}")
        return 1

    # The arm runners catch their own exceptions and return success=False rather
    # than raising, so without this an unavailable provider would show up only
    # as a silent "0 LLM requests" — confusing in front of an audience.
    if not result.get("success"):
        banner("RUN DID NOT COMPLETE")
        error = str(result.get("error", "no error recorded"))
        print(f"\n  {error[:400]}")
        if "spending cap" in error.lower() or "billing" in error.lower():
            print("\n  The LLM provider has stopped accepting requests for this "
                  "billing period.\n  Raise the cap, then re-run.")
        elif "ip address restriction" in error.lower():
            print("\n  The API key is restricted to specific IP addresses and this "
                  "machine is not\n  on the list. Remove the restriction, then re-run.")
        elif "cachemiss" in error.lower() or "no recorded response" in error.lower():
            print("\n  Replay mode has no recording for this request. Either use the "
                  "default\n  request, or record it once with "
                  "TRIP_PLANNER_API_MODE=record.")
        print(f"\n  Live API calls spent: {cache_summary()['live_calls']}")
        return 1

    banner("WHAT IT COST")
    print(f"\n  {'LLM requests':<22}{result.get('llm_calls', 0):>12,}")
    print(f"  {'Tokens':<22}{result.get('total_tokens', 0):>12,}")
    print(f"  {'Cost (USD)':<22}{result.get('cost_usd', 0):>12.5f}")
    print(f"  {'Wall time (s)':<22}{result.get('latency', time.time() - started):>12.1f}")
    print("\n  Measured through provider callbacks at runtime — not estimated.")

    # Groundedness needs the retrieved data as its reference. Arm D produces it;
    # for the others, fetch it separately so the check still has something to
    # compare against.
    truth = result.get("ground_truth")
    if not truth:
        try:
            reference = run_three_agent_direct(request, "demo-reference")
            truth = reference.get("ground_truth")
        except Exception:
            truth = None

    if truth and (truth.get("hotels") or truth.get("airlines")):
        score = score_groundedness(result.get("result", ""), truth)
        banner("IS ANY OF IT REAL?")
        print(f"\n  Prices quoted in the itinerary   {score['prices_quoted']:>6}")
        print(f"  ...matching a real fare or rate  {score['prices_grounded']:>6}"
              f"   ({score['prices_grounded_pct']:.0f}%)")
        if score["matched_hotels"]:
            print(f"\n  Real hotels named: {', '.join(score['matched_hotels'][:3])}")
        if score["matched_airlines"]:
            print(f"  Real airlines named: {', '.join(score['matched_airlines'][:3])}")
        if score["prices_grounded_pct"] == 0:
            print("\n  Not one price matches anything retrieved — every figure "
                  "in this itinerary was invented.")

    itinerary = result.get("result", "")
    banner("ITINERARY (first 900 characters)")
    print()
    print(itinerary[:900] if itinerary else "(empty)")
    if len(itinerary) > 900:
        print(f"\n  ... {len(itinerary) - 900:,} more characters")

    print(f"\n{RULE}")
    print(f"  Live API calls spent by this run: {cache_summary()['live_calls']}")
    print(f"  Compare all four:  python demos/demo_comparison.py")
    print(RULE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
