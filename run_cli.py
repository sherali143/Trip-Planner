"""Plans a trip in the terminal. Run: python run_cli.py"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Keep the console readable. The AI libraries log at INFO by default, and one of
# them prints the request URL — which carries the API key as a parameter.
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["LITELLM_LOG"] = "ERROR"

import logging

for noisy in ("LiteLLM", "litellm", "httpx", "trip_planner", "opentelemetry",
              "crewai"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

import litellm

litellm.suppress_debug_info = True

from dotenv import load_dotenv

load_dotenv(override=True)

# Google's key is valid under either name and .env carries either one. Importing
# the package copies it to both; doing it here too would be a second copy of a
# rule that already lives in trip_planner/core/gemini_compat.py.
import trip_planner  # noqa: F401,E402  side effect: keys, logging, model shim

SEP = "━" * 60

DEFAULT_REQUEST = ("Plan a trip to Paris for 5 days with $3000 budget. "
                   "Interests: food, culture.")


def validate_api_keys() -> bool:
    """Name every missing key at once, rather than failing on the first."""
    # Each entry: the names that would satisfy it, and what it is for. Gemini
    # accepts either of its two names, so requiring one specifically would reject
    # a .env that is perfectly usable.
    required = [
        (("GOOGLE_API_KEY", "GEMINI_API_KEY"), "Google Gemini (the AI agents)"),
        (("SERPER_API_KEY",), "Serper (attractions and restaurants)"),
        (("RAPIDAPI_KEY",), "RapidAPI (flights and hotels)"),
    ]

    def present(name: str) -> bool:
        value = os.getenv(name, "")
        return bool(value) and not value.startswith("your_")

    missing = [f"  - {' or '.join(names)}: {what}"
               for names, what in required
               if not any(present(name) for name in names)]
    if missing:
        print("\nMISSING API KEYS:\n" + "\n".join(missing))
        print("\nAdd them to .env and try again.")
        print("Nothing here needs keys: run.bat options 1 to 10.\n")
        return False
    return True


def _confirm_allocation(extraction_output: str):
    """
    Show the suggested budget split, explain it, and accept any change.

    Passed to the orchestrator as a callback. Asking "what percentage for
    flights?" cold is not a fair question — most people have no basis for
    answering it. So the split is proposed from the trip's own shape (distance,
    nights, party size, style), explained, and then whatever the traveller says
    is used. See trip_planner/core/budget.py for the evidence behind the default.

    Returns absolute amounts, or None to keep what the extractor produced.
    """
    from trip_planner.core.budget import build_allocation
    from trip_planner.orchestrator import TripPlannerCrew

    prefs = TripPlannerCrew._parse_prefs(extraction_output)
    try:
        total = float(prefs.get("total_budget", 0) or 0)
    except (TypeError, ValueError):
        total = 0.0
    if total <= 0:
        # No budget to divide. Say so: silently skipping the one interactive step
        # this file exists for looks identical to the step being broken, and the
        # difference matters when someone is demonstrating the feature.
        print("\n  (No total budget was extracted, so there is nothing to split.")
        print("   Continuing with the search defaults.)\n")
        return None

    travelers = max(1, int(prefs.get("num_adults", 1) or 1)
                    + int(prefs.get("num_children", 0) or 0))
    kwargs = dict(
        total_budget=total,
        trip_duration=int(prefs.get("trip_duration", 5) or 5),
        num_travelers=travelers,
        travel_style=prefs.get("travel_style", "") or "",
        origin=prefs.get("origin", "") or "",
        destination=prefs.get("destination", "") or "",
    )
    allocation = build_allocation(**kwargs)

    print(f"\n{SEP}\n  BUDGET ALLOCATION\n{SEP}\n")
    print(allocation.explain())
    print("\n  Press Enter to accept, or type a different split.")
    print("  Examples:  40/30/20/10   (flights/accommodation/activities/meals)")
    print("             hotel 50, flights 25")
    print("             flights 600, hotel 400")
    try:
        answer = input("\n  Your choice: ").strip()
    except (EOFError, KeyboardInterrupt):
        # Piped input or a non-interactive shell. Keep the suggestion rather
        # than crashing, so the CLI still works when scripted.
        answer = ""

    if not answer:
        print("\n  Using the suggested split.\n")
        return allocation.as_dict()

    revised = build_allocation(user_input=answer, **kwargs)
    if revised.source != "user":
        # The input could not be read; build_allocation says why.
        print("\n  Keeping the suggested split.")
        for note in revised.reasons:
            print(f"    {note}")
        print()
        return revised.as_dict()

    print()
    print(revised.explain())
    if revised.warnings:
        print("\n  Your split is being used as entered. The notes above are")
        print("  warnings, not corrections.\n")
    return revised.as_dict()


def main() -> int:
    print(SEP)
    print("  AI TRIP PLANNER  -  three agents, direct retrieval")
    print(SEP)

    if not validate_api_keys():
        return 1

    print("\nDescribe your trip:")
    print("   (for example: 'Plan a trip to Paris for 7 days with $3000')")
    # Budgets are read as US dollars everywhere in this project, so say so rather
    # than leave a traveller to guess from a currency symbol in an example.
    print("   Budgets are read as US DOLLARS. Please convert before entering.\n")
    try:
        request = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        request = ""
    if not request:
        request = DEFAULT_REQUEST
        print(f"  (using the default: {request})\n")

    # Everything below this line lives in one place, shared with the web app.
    from trip_planner.orchestrator import TripPlannerCrew

    crew = TripPlannerCrew()
    itinerary = crew.plan_trip(request, confirm_allocation=_confirm_allocation)

    print(f"\n{SEP}\n  YOUR ITINERARY\n{SEP}\n")
    print(itinerary)
    print(f"\n{SEP}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
