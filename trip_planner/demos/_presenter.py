"""
The shared narration for the approach demos.

Written once here so each demo file only has to describe its own approach.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
    from trip_planner.evaluation import measured
    return measured.detail(code)


def _scenario_request() -> str:
    from trip_planner.evaluation.scenarios import scenario
    from trip_planner.evaluation import measured
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
    # Neutral label: for the agent arms this is largely re-sent context, for the
    # three-agent arm it is largely retrieved data. The timeline below says which.
    print(f"    Prompt tokens       {llm.get('prompt_tokens', 0):,}"
          f"   (everything sent TO the model)")
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

    _show_call_timeline(llm.get("per_call") or [], approach.code)
    _show_groundedness(record)


def _show_call_timeline(per_call: List[dict], code: str) -> None:
    """
    One row per model request, so the cost explains itself.

    The totals say an architecture spent 120,000 tokens. This says why: in a
    reasoning loop the prompt column climbs on every request, because each
    iteration re-sends the whole conversation and every tool schema. Watching
    that column grow is the clearest single piece of evidence in the project,
    and it needs no interpretation from the person presenting it.
    """
    if not per_call:
        return
    print("\n    Every model request, in order:")
    print(f"      {'#':>3}  {'prompt':>9}  {'reply':>8}  {'seconds':>8}   growth")
    first_prompt = per_call[0]["prompt_tokens"] or 1
    for row in per_call:
        growth = row["prompt_tokens"] / first_prompt
        bar = "#" * min(28, max(1, int(growth * 2)))
        print(f"      {row['n']:>3}  {row['prompt_tokens']:>9,}  "
              f"{row['completion_tokens']:>8,}  {row['latency_s']:>8.1f}   {bar}")
    if len(per_call) > 1:
        last = per_call[-1]["prompt_tokens"]
        print(f"\n      The prompt grew from {first_prompt:,} to {last:,} tokens "
              f"({last / first_prompt:.1f}x).")
        print(f"      {_growth_reason(code)}")


def _growth_reason(code: str) -> str:
    """
    Say what the growing prompt actually consists of, which differs by approach.

    This was one sentence for all four and it was wrong for the shipped one. In a
    reasoning loop the prompt grows because the conversation and every tool schema
    are re-sent — waste. In the three-agent design it grows because the retrieved
    flights and hotels are handed to the writer — the entire point. Same shape on
    the screen, opposite meanings, and calling both "re-sent context" would have
    argued against the approach this project recommends.
    """
    if code in ("B", "C"):
        return ("That growth is the conversation and tool schemas being re-sent on "
                "each loop step — it is not new information.")
    if code == "D":
        return ("That growth is the retrieved flights and hotels being handed to "
                "the writer — it IS new information, fetched without a model.")
    return "Each request carries whatever the previous step produced."


def _show_groundedness(record: dict) -> None:
    """How much of what the plan says was actually retrieved."""
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
    from trip_planner.evaluation import measured

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


class _RetryCounter:
    """
    Collapse the framework's parse-retry messages into one measured number.

    The agent framework prints this, once per occurrence, sometimes six times in
    a row:

        Error parsing LLM output, agent will retry: I did it wrong. Tried to both
        perform Action and give a Final Answer at the same time...

    It is not a crash and it is not a misconfiguration. The reasoning loop asks
    the model to answer in a strict format — either call a tool OR give a final
    answer — and the model sometimes does both in one reply. The framework throws
    that reply away and asks again.

    Every retry is a FULL model request: the whole conversation and every tool
    schema, re-sent. So it is a real cost, and it is already inside the request
    and token counts this demo reports. What was missing was a name for it. Six
    identical red lines read as "this project is broken"; "6 model calls were
    spent re-asking because the framework could not parse the reply" reads as
    what it is — a measured weakness of giving an agent many tools and a long
    leash, which is exactly what approach C tightens and approach D removes.

    Suppressed rather than hidden: the count is printed, and it is printed even
    when it is zero for the approaches that do not suffer from it.
    """

    PHRASE = "Error parsing LLM output"

    def __init__(self) -> None:
        self.count = 0
        self._real_stdout = None
        self._real_stderr = None

    def _filter(self, stream):
        counter = self

        class _Filtered:
            def write(self, text):
                if counter.PHRASE in text:
                    counter.count += 1
                    # Print one dot per retry so the screen shows something is
                    # happening during a six-minute run, without six paragraphs.
                    stream.write(".")
                    stream.flush()
                    return len(text)
                return stream.write(text)

            def flush(self):
                return stream.flush()

            def __getattr__(self, name):
                return getattr(stream, name)

        return _Filtered()

    def __enter__(self):
        self._real_stdout, self._real_stderr = sys.stdout, sys.stderr
        sys.stdout = self._filter(self._real_stdout)
        sys.stderr = self._filter(self._real_stderr)
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self._real_stdout, self._real_stderr
        return False

    def report(self) -> None:
        _section("WAS ANYTHING WASTED?")
        if not self.count:
            print("    Parse retries                   0")
            print("\n    Every reply the framework asked for came back in a shape")
            print("    it could read. Nothing was re-asked.")
            return
        print(f"    Parse retries                   {self.count}")
        print(f"\n    {self.count} model call(s) were spent re-asking, because the agent")
        print("    replied in a shape the framework could not parse — it tried to")
        print("    call a tool and give a final answer in the same breath.")
        print("    Each retry re-sends the whole conversation and every tool schema.")
        print("    This is counted in the totals above, and it is a cost of giving")
        print("    one agent many tools and a long reasoning leash.")


def _live(approach: Approach, pause: bool) -> int:
    if approach.runner is None:
        print("  This approach has no live runner; playback only.")
        return 1

    from dotenv import load_dotenv
    load_dotenv(override=True)

    import trip_planner  # noqa: F401  side effect: installs logging
    #   defaults, so the model key in the Gemini URL is never printed
    from trip_planner.evaluation.metrics import score_groundedness
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
    retries = _RetryCounter()
    try:
        with retries:
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
    retries.report()

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
        _protect_travel_quota(argv)
        return _live(approach, pause)
    return _playback(approach, pause)


def _protect_travel_quota(argv: List[str]) -> None:
    """
    Run the MODEL live but replay the travel responses, unless told otherwise.

    `--live` means "execute this architecture for real", and what a demonstration
    needs from that is a real model doing real reasoning. It does not need to buy
    flight data it already has on disk.

    Without this the API layer defaults to `record`, which is cache-first but
    calls the live API on a MISS. A miss is easy to cause by accident: the live
    extractor may format a date or an airport slightly differently from the
    recorded run, and that costs a request from an allowance of thirty a month
    that does not refill before this project is submitted. Losing a month's quota
    to a rehearsal is not a risk worth carrying for a demonstration.

    `--live-apis` opts back in, and says so on screen.
    """
    if "--live-apis" in argv:
        os.environ.pop("TRIP_PLANNER_API_MODE", None)   # let the default apply
        print("  --live-apis: travel APIs will be called for real. This SPENDS")
        print("               monthly flight and hotel quota.\n")
        return
    # An explicit setting in the environment is the operator's decision; honour it.
    if os.environ.get("TRIP_PLANNER_API_MODE"):
        return
    os.environ["TRIP_PLANNER_API_MODE"] = "replay"
    print("  The model runs live. Travel responses replay from disk, so no")
    print("  flight or hotel quota is spent. Add --live-apis to change that.\n")
