"""
All four approaches side by side, with the table and what to say about it.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from demos._presenter import RULE, _scenario_request
from demos.approach_a_single_llm import APPROACH_A
from demos.approach_b_six_agent_naive import APPROACH_B
from demos.approach_c_six_agent_tuned import APPROACH_C
from demos.approach_d_three_agent_direct import APPROACH_D

APPROACHES = [APPROACH_A, APPROACH_B, APPROACH_C, APPROACH_D]


def _gather_playback() -> dict:
    from evaluation import measured
    return {a.code: measured.detail(a.code) for a in APPROACHES}


def _gather_live(pause: bool) -> dict:
    from dotenv import load_dotenv
    load_dotenv(override=True)

    import trip_planner  # noqa: F401  side effect: installs logging
    #   defaults, so the model key in the Gemini URL is never printed
    from evaluation import measured
    from evaluation.metrics import score_groundedness

    request = _scenario_request()
    results = {}
    for approach in APPROACHES:
        print(f"\n{RULE}\n  RUNNING {approach.code}: {approach.name}\n{RULE}")
        if pause:
            input("\n  Press Enter to start...")
        started = time.time()
        try:
            results[approach.code] = approach.runner(request, "demo")
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            results[approach.code] = {"success": False, "error": str(exc),
                                      "latency": time.time() - started}
            continue
        row = results[approach.code]
        if not row.get("success"):
            print(f"  DID NOT COMPLETE: {str(row.get('error'))[:200]}")
            continue
        print(f"  Done in {row.get('latency', 0):.1f}s | "
              f"{row.get('llm_calls', 0)} model requests | "
              f"{row.get('total_tokens', 0):,} tokens")

    # Score every approach against what the deterministic one retrieved.
    truth = (results.get("D") or {}).get("ground_truth") or {}
    if not truth.get("hotels"):
        truth = measured.detail("D").get("ground_truth") or {}
    if truth.get("hotels") or truth.get("airlines"):
        for row in results.values():
            if row.get("success"):
                row["groundedness"] = score_groundedness(row.get("result", ""), truth)
    return results


def _table(results: dict) -> None:
    print(f"\n{RULE}\n  ALL FOUR APPROACHES, SAME REQUEST\n{RULE}\n")
    head = (f"  {'Approach':<36}{'Reqs':>6}{'Tokens':>10}{'Cost $':>10}"
            f"{'Secs':>7}{'Real $':>8}")
    print(head)
    print("  " + "-" * (len(head) - 2))
    for approach in APPROACHES:
        row = results.get(approach.code) or {}
        label = f"{approach.code}  {approach.name}"
        if not row.get("success"):
            print(f"  {label:<36}{'did not complete':>41}")
            continue
        ground = (row.get("groundedness") or {}).get("prices_grounded_pct")
        print(f"  {label:<36}"
              f"{row.get('llm_calls', 0):>6}"
              f"{row.get('total_tokens', 0):>10,}"
              f"{row.get('cost_usd', 0):>10.5f}"
              f"{row.get('latency', 0):>7.1f}"
              f"{(f'{ground:.0f}%' if ground is not None else 'n/a'):>8}")
    print("\n  'Real $' = share of the prices in the plan that match a fare or")
    print("  nightly rate the APIs actually returned.")
    # The dissertation quotes MEANS over every repeat; this table shows the single
    # run being replayed. Both are honest and they differ slightly, so say which
    # is which. A supervisor holding the report beside this screen should not have
    # to wonder whether one of them is wrong.
    print("\n  These are the figures from the ONE recorded run being replayed.")
    print("  The dissertation quotes means over all repeats, so its table reads")
    print("  a little differently — same data, averaged rather than single-run.")


def _findings(results: dict) -> None:
    print(f"\n{RULE}\n  WHAT TO SAY ABOUT THIS TABLE\n{RULE}")

    control = (results.get("A") or {}).get("groundedness") or {}
    if control.get("prices_quoted"):
        print(f"\n  1. Cheapest is not best. Approach A quoted "
              f"{control['prices_quoted']} prices and")
        print(f"     matched {control['prices_grounded']} of them to anything real. "
              f"It calls no API,")
        print(f"     so it has nothing to cite. Cost means nothing without this column.")

    naive, tuned = results.get("B") or {}, results.get("C") or {}
    if naive.get("total_tokens") and tuned.get("total_tokens"):
        drop = (1 - tuned["total_tokens"] / naive["total_tokens"]) * 100
        print(f"\n  2. Tuning matters more than agent count. B and C are the SAME six")
        print(f"     agents with the same data. Tuning alone cut tokens by {drop:.0f}%.")
        print(f"     So the fair comparison for D is against C, not against B.")

    direct = results.get("D") or {}
    if direct.get("llm_calls") and tuned.get("llm_calls"):
        calls = (1 - direct["llm_calls"] / tuned["llm_calls"]) * 100
        print(f"\n  3. Against that fair baseline, D uses {calls:.0f}% fewer model "
              f"requests")
        print(f"     with the same groundedness — but the cost saving is modest. The")
        print(f"     honest claim is about request count and latency, not money.")

    print(f"\n  4. The protocols are IDENTICAL in all four. Only retrieval differs,")
    print(f"     which is what makes this a controlled comparison.")
    print(f"\n{RULE}")


def main() -> int:
    argv = sys.argv[1:]
    pause = "--no-pause" not in argv
    live = "--live" in argv

    from evaluation import measured
    coverage = measured.coverage()

    print(RULE)
    print("  ALL FOUR APPROACHES COMPARED")
    print(f"  {'LIVE run - spends quota' if live else 'PLAYBACK of recorded runs - no API calls, no quota'}")
    print(RULE)
    print(f"\n  Request: {_scenario_request()}")

    if not live:
        print(f"\n  These are the measurements recorded on "
              f"{measured.results()['timestamp'][:10]} for scenario")
        print(f"  {coverage['scenario_ids'][0]}, produced by {coverage['model']}. "
              f"Nothing is being generated now.")

    results = _gather_live(pause) if live else _gather_playback()

    _table(results)
    _findings(results)

    print(f"\n  Coverage: {coverage['scenarios_measured']} of "
          f"{coverage['scenarios_designed']} designed scenarios recorded, "
          f"{coverage['repeats_per_arm']} run each.")
    print(f"  See any one approach in detail:  "
          f"python demos/approach_d_three_agent_direct.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
