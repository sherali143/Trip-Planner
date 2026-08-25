"""
Reports how much monthly API allowance is left.

COSTS ONE CALL PER API. The allowance is only reported in the headers of a
real response, and the recording layer strips headers, so there is no free way
to ask. Run it once before a demonstration, never in a loop.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
import json

import requests
from dotenv import load_dotenv

# Where the reading is saved. PROJECT_OVERVIEW.docx reads this file rather than
# quoting a number typed by hand, so the document can say when the reading was
# taken and stay honest as the balance falls.
QUOTA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "results", "api_quota.json")

# The header names RapidAPI uses. The limit header carries the window length as
# a separate header, which is why both are read rather than assumed monthly.
REMAINING = "x-ratelimit-requests-remaining"
LIMIT = "x-ratelimit-requests-limit"
RESET = "x-ratelimit-requests-reset"

# One cheap, well-formed request per API. Each is the smallest query that still
# returns 2xx, because a 4xx may not carry quota headers at all.
PROBES = [
    {
        "name": "fly-scraper (flights)",
        "host": "fly-scraper.p.rapidapi.com",
        "url": "https://fly-scraper.p.rapidapi.com/flights/search-one-way",
        "params": {"fromEntityId": "LHE", "toEntityId": "IST",
                   "departDate": "2026-12-01", "adults": "1"},
        "documented_limit": 30,
    },
    {
        "name": "booking-com15 (hotels)",
        "host": "booking-com15.p.rapidapi.com",
        "url": "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination",
        "params": {"query": "Istanbul"},
        "documented_limit": 50,
    },
]


def _probe(probe: dict, key: str) -> dict:
    headers = {"x-rapidapi-key": key, "x-rapidapi-host": probe["host"]}
    try:
        response = requests.get(probe["url"], headers=headers,
                                params=probe["params"], timeout=30)
    except requests.RequestException as exc:
        return {"error": f"could not reach the API: {exc}"}

    out = {
        "status": response.status_code,
        "remaining": response.headers.get(REMAINING),
        "limit": response.headers.get(LIMIT),
        "reset_seconds": response.headers.get(RESET),
    }
    if response.status_code == 429:
        out["error"] = "quota exhausted (HTTP 429)"
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv(override=True)
    key = os.getenv("RAPIDAPI_KEY", "")

    print("=" * 74)
    print("  TRAVEL API QUOTA")
    print("=" * 74)
    print("\n  This makes ONE live call per API. That costs 1 flight call and")
    print("  1 hotel call from the monthly allowance — the quota is only")
    print("  reported in the response to a real request.\n")

    if not key or key.startswith("your_"):
        print("  RAPIDAPI_KEY is not set in .env, so nothing can be checked.")
        return 1

    readings = {}
    for probe in PROBES:
        result = _probe(probe, key)
        readings[probe["host"]] = {"name": probe["name"], **result}
        print(f"  {probe['name']}")
        if result.get("error"):
            print(f"    {result['error']}")
        if result.get("remaining") is not None:
            limit = result.get("limit") or probe["documented_limit"]
            print(f"    remaining this month : {result['remaining']} of {limit}")
            if result.get("reset_seconds"):
                try:
                    days = int(result["reset_seconds"]) / 86400
                    print(f"    resets in            : {days:.1f} days")
                except (TypeError, ValueError):
                    pass
        elif not result.get("error"):
            # Some plans omit the headers entirely. Say so rather than print
            # nothing, or the reader assumes the check silently failed.
            print(f"    HTTP {result['status']}, but this plan returned no quota "
                  f"headers.")
            print(f"    Check the dashboard at rapidapi.com instead.")
        print()

    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with open(QUOTA_PATH, "w", encoding="utf-8") as fh:
        json.dump({"checked_at": stamp, "apis": readings}, fh, indent=2)
    print(f"  Reading saved to {os.path.relpath(QUOTA_PATH, os.path.dirname(os.path.dirname(QUOTA_PATH)))}")
    print(f"  Taken at {stamp}. Re-run this to refresh it (costs 2 calls).\n")

    print("  Serper (attractions and restaurants): large free allowance, and it")
    print("  is not the constraint. Dashboard: serper.dev")
    print("  Gemini (the language model): free tier, rate-limited per minute")
    print("  rather than per month. Dashboard: aistudio.google.com\n")
    print("  What one trip costs, measured:")
    print("    approach D  1 flight call + 2 hotel calls + 2 Serper calls")
    print("    approaches B and C vary — their agents decide how often to call")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
