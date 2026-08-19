"""
WHAT THIS FILE DOES
===================
Shared presentation for every approach demo. It knows how to narrate one
architecture running — and, crucially, how to narrate one that has ALREADY run,
from the recorded measurements, without touching any API.

Why the playback mode exists
----------------------------
The free tiers this project runs on are exhaustible: thirty flight requests a
month, fifty hotel requests, and a rate-limited model. A demonstration that
needs a working API is a demonstration that cannot be given on the day the quota
runs out — which is exactly the day it will be needed.

So there are two modes:

    PLAYBACK (default)  Reads the recorded run from evaluation/results/ and
                        narrates it step by step: the same measured timings, the
                        same measured cost, the same itinerary text that run
                        actually produced. No network, no model, no keys, no
                        quota. It always works.

    LIVE (--live)       Executes the architecture for real. Identical code path
                        to the evaluation harness; needs a working model key.

Both modes narrate the same steps in the same order, because both describe the
same architecture. The only difference is whether the numbers are being produced
now or were produced earlier and recorded.

Playback is labelled as playback everywhere it appears. Presenting a recorded
run as a live one would be dishonest, and a supervisor asking "is this running
now?" deserves a straight answer from the screen rather than from the presenter.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RULE = "=" * 78
THIN = "-" * 78


@dataclass
class Approach:
    """Everything that distinguishes one architecture from another."""

    code: str                     # "A".."D" — also the key in the results file
    name: str                     # short title
    headline: str                 # one sentence: what this approach IS
    steps: List[str]              # how it works, in order
    watch_for: str                # what the supervisor should notice
    runner: Optional[Callable] = None   # live execution; None means playback only
    reads_apis: bool = True


def _wrap(text: str, width: int = 74, indent: str = "    ") -> str:
    import textwrap
    return "\n".join(textwrap.fill(line, width, initial_indent=indent,
                                   subsequent_indent=indent) or indent
                     for line in text.split("\n"))


def _banner(title: str, subtitle: str = "") -> None:
    print(f"\n{RULE}\n  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(RULE)


def _section(title: str) -> None:
    print(f"\n  {title}\n  {THIN[:len(title)]}")


# --------------------------------------------------------------------- data
def _recorded(code: str) -> dict:
    """The recorded measurement for this approach, or a clear failure."""
    from evaluation import measured
    return measured.detail(code)


def _scenario_request() -> str:
    from evaluation.scenarios import scenario
    from evaluation import measured
    return scenario(measured.scenario_ids()[0])["input"]


# ----------------------------------------------------------------- rendering
def _describe(approach: Approach) -> None:
    _section("WHAT THIS APPROACH IS")
    print(_wrap(approach.headline))

    _section("HOW IT WORKS")
    for i, step in enumerate(approach.steps, 1):
        # Wrapped with a hanging indent so a long step stays inside the terminal
        # and its continuation lines line up under the text, not the number.
        import textwrap
        print(textwrap.fill(step, 74, initial_indent=f"    {i}. ",
                            subsequent_indent="       "))

    _section("WHAT TO WATCH FOR")
    print(_wrap(approach.watch_for))


def _show_measurements(record: dict, approach: Approach) -> None:
    llm = record.get("llm") or {}
    _section("WHAT IT COST")
    print(f"    Model requests      {record.get('llm_calls', 0)}")
    print(f"    Prompt tokens       {llm.get('prompt_tokens', 0):,}"
          f"   (re-sent context and tool schemas)")
    print(f"    Completion tokens   {llm.get('completion_tokens', 0):,}"
          f"   (the itinerary text itself)")
    print(f"    Total tokens        {record.get('total_tokens', 0):,}")
    print(f"    Cost                ${record.get('cost_usd', 0):.4f}")
    print(f"    Wall-clock time     {record.get('latency', 0):.1f}s")

    phases = {k: v for k, v in record.items() if k.startswith("phase")}
    if phases:
        print("\n    Time by phase:")
        for key, value in phases.items():
            label = key.replace("phase", "").replace("_s", "").replace("_", " ").strip()
            label = label[1:].strip() if label[:1].isdigit() else label
            print(f"      {label:<28}{value}s")

    ground = record.get("groundedness") or {}
    if ground.get("scored"):
        _section("WAS ANY OF IT REAL?")
        print(f"    Prices quoted in the plan       {ground['prices_quoted']}")
        print(f"    Prices matching a real fare     {ground['prices_grounded']}"
              f"   ({ground['prices_grounded_pct']:.0f}%)")
        print(f"    Hotels named that were retrieved {ground['hotels_grounded']}"
              f" of {ground['hotels_available']}")
        print(f"    Airlines named that were retrieved {ground['airlines_grounded']}"
              f" of {ground['airlines_available']}")
        if ground["prices_grounded"] == 0 and ground["prices_quoted"] > 0:
            print("\n    Every price above was invented. This approach called no API,")
            print("    so it had nothing real to quote.")


def _show_output(record: dict, lines: int = 28) -> None:
    itinerary = (record.get("result") or "").strip()
    if not itinerary:
        print("\n    (no itinerary was produced)")
        return
    _section(f"THE ITINERARY IT PRODUCED  (first {lines} lines)")
    for line in itinerary.splitlines()[:lines]:
        print(f"    {line}")
    remaining = len(itinerary.splitlines()) - lines
    if remaining > 0:
        print(f"\n    ... {remaining} more lines ({len(itinerary):,} characters in total)")


# --------------------------------------------------------------------- modes
def _playback(approach: Approach, pause: bool) -> int:
    from evaluation import measured

    record = _recorded(approach.code)
    provenance = measured.provenance()
    coverage = measured.coverage()

    _banner(f"APPROACH {approach.code}  -  {approach.name}",
            "PLAYBACK of a recorded run. No API calls, no model requests, "
            "no quota spent.")

    print(f"\n  This replays the measurement recorded for scenario "
          f"{record.get('scenario_id')}")
    print(f"  ({record.get('scenario_name')}) on {measured.results()['timestamp'][:10]},")
    print(f"  produced by {provenance.get('model')} with the API layer in "
          f"{provenance.get('api_mode')} mode.")
    print(f"\n  Every number and every line of the itinerary below is what that run")
    print(f"  actually produced. Nothing here is being generated now.")

    _section("THE REQUEST")
    print(_wrap(_scenario_request()))

    _describe(approach)
    if pause:
        input("\n  Press Enter to see what it produced...")

    _show_output(record)
    if pause:
        input("\n  Press Enter to see what it cost...")

    _show_measurements(record, approach)

    print(f"\n{RULE}")
    print(f"  Playback complete. 0 API calls, 0 model requests, 0 quota spent.")
    print(f"  Run with --live to execute this approach for real (needs a model key).")
    print(f"  Coverage note: {coverage['scenarios_measured']} of "
          f"{coverage['scenarios_designed']} designed scenarios is recorded.")
    print(RULE)
    return 0


def _live(approach: Approach, pause: bool) -> int:
    if approach.runner is None:
        print("  This approach has no live runner; playback only.")
        return 1

    from dotenv import load_dotenv
    load_dotenv(override=True)

    import trip_planner  # noqa: F401  side effect: installs logging
    #   defaults, so the model key in the Gemini URL is never printed
    from evaluation.metrics import score_groundedness
    from trip_planner.core.http_cache import cache_summary, get_mode

    request = _scenario_request()

    _banner(f"APPROACH {approach.code}  -  {approach.name}",
            "LIVE run. This executes the architecture and spends quota.")
    print(f"\n  API mode: {get_mode()}")
    if get_mode() != "replay":
        print("  WARNING: not in replay mode - this may spend monthly travel-API quota.")
        print("           Set TRIP_PLANNER_API_MODE=replay to use recorded responses.")

    _section("THE REQUEST")
    print(_wrap(request))
    _describe(approach)

    if pause:
        input("\n  Press Enter to run it...")

    print("\n  Running...\n")
    started = time.time()
    try:
        record = approach.runner(request, "demo")
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        print("\n  If the model quota is exhausted, run without --live to play back")
        print("  the recorded measurement instead. It needs nothing but this folder.")
        return 1

    if not record.get("success"):
        print(f"  DID NOT COMPLETE: {str(record.get('error'))[:300]}")
        print("\n  Run without --live to play back the recorded measurement instead.")
        return 1

    # Score against what the deterministic arm retrieved, exactly as the
    # evaluation harness does, so the number means the same thing.
    truth = _recorded("D").get("ground_truth") or {}
    if truth.get("hotels") or truth.get("airlines"):
        record["groundedness"] = score_groundedness(record.get("result", ""), truth)

    _show_output(record)
    _show_measurements(record, approach)

    print(f"\n{RULE}")
    print(f"  Live run complete in {time.time() - started:.1f}s. "
          f"Live API calls spent: {cache_summary()['live_calls']}")
    print(RULE)
    return 0


def present(approach: Approach, argv: Optional[List[str]] = None) -> int:
    """
    Entry point every approach demo calls.

    Defaults to playback because that is the mode that always works. `--live`
    opts in to spending quota.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    pause = "--no-pause" not in argv
    if "--live" in argv:
        return _live(approach, pause)
    return _playback(approach, pause)
