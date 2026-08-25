"""
The trimmed tool wrappers approach C uses.

Same underlying functions as the tool server, but each returns the best few
results as short lines instead of a full reply. That trimming is most of the
difference between approach B and approach C.
"""

import json
import re

from crewai.tools import tool

from trip_planner.server.mcp_server import (
    search_attractions as _mcp_attractions,
    search_hotels_comprehensive as _mcp_hotels,
    search_restaurants as _mcp_restaurants,
)
from trip_planner.tools.travel_apis import _call_fly_scraper_api

TOP_N = 3


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


@tool("Search flights")
def distilled_search_flights(
    origin: str, destination: str, departure_date: str,
    return_date: str = "", adults: int = 1, budget: float = 0.0
) -> str:
    """Find flights. Give city names and YYYY-MM-DD dates. Returns the cheapest options."""
    try:
        raw = _call_fly_scraper_api(
            origin, destination, departure_date, return_date or None, adults, budget or None
        )
        data = json.loads(raw)
    except Exception as exc:
        return f"FLIGHT SEARCH FAILED: {exc}"

    if not data.get("success"):
        return f"FLIGHT SEARCH FAILED: {data.get('error', 'unknown error')}"

    flights = data.get("flights") or []
    if not flights:
        return "No flights found for those dates."

    lines = [f"{len(flights)} options (showing {min(TOP_N, len(flights))}):"]
    for f in flights[:TOP_N]:
        out = f.get("outbound") or {}
        back = f.get("inbound") or {}
        lines.append(
            f"- {f.get('price_formatted') or f.get('total_price')} | {f.get('airline', '?')} | "
            f"out {out.get('departure', '?')} {out.get('from', '')}->{out.get('to', '')} "
            f"({out.get('stops', 0)} stops)"
            + (f" | back {back.get('departure', '?')}" if back else "")
        )
    return "\n".join(lines)


@tool("Search hotels")
def distilled_search_hotels(
    destination: str, checkin_date: str, checkout_date: str,
    budget_per_night: float = 100.0, adults: int = 1
) -> str:
    """Find hotels in a city for the given YYYY-MM-DD dates. Returns the best-rated options."""
    try:
        raw = _mcp_hotels(destination, checkin_date, checkout_date, budget_per_night, adults, 1)
    except Exception as exc:
        return f"HOTEL SEARCH FAILED: {exc}"

    if "ERROR" in raw[:200].upper() and "Found" not in raw[:200]:
        return f"HOTEL SEARCH FAILED: {_clip(raw, 200)}"

    # The MCP hotel tool returns a long human-formatted report with a review
    # breakdown per hotel; keep only name, nightly price and score.
    names = re.findall(r"Hotel #\d+:\s*(.+)", raw)
    prices = re.findall(r"\((?:\$|USD\s*)([\d.]+)/night\)", raw)
    ratings = re.findall(r"Rating:\s*([\d.]+)/10", raw)

    if not names:
        return "No hotels found."

    lines = [f"{len(names)} hotels (showing {min(TOP_N, len(names))}):"]
    for i in range(min(TOP_N, len(names))):
        price = f"${float(prices[i]):.0f}/night" if i < len(prices) else "price n/a"
        rating = f"{ratings[i]}/10" if i < len(ratings) else "unrated"
        lines.append(f"- {_clip(names[i], 60)} | {price} | {rating}")
    return "\n".join(lines)


def _distil_search_results(raw: str, limit: int) -> str:
    """Compress Serper output (Title/Link/Snippet blocks) to one line per result."""
    titles = re.findall(r"Title:\s*(.+)", raw)
    snippets = re.findall(r"Snippet:\s*(.+)", raw)
    if not titles:
        return _clip(raw, 400)
    out = []
    for i in range(min(limit, len(titles))):
        snippet = _clip(snippets[i], 110) if i < len(snippets) else ""
        out.append(f"- {_clip(titles[i], 80)}: {snippet}")
    return "\n".join(out)


@tool("Search attractions")
def distilled_search_attractions(destination: str, interests: str, duration_days: int = 3) -> str:
    """Find things to do in a city, matched to the traveller's interests."""
    try:
        return _distil_search_results(_mcp_attractions(destination, interests, duration_days), 5)
    except Exception as exc:
        return f"ATTRACTION SEARCH FAILED: {exc}"


@tool("Search restaurants")
def distilled_search_restaurants(destination: str, cuisine_types: str, budget_per_meal: float = 25.0) -> str:
    """Find places to eat in a city within a per-meal budget."""
    try:
        return _distil_search_results(_mcp_restaurants(destination, cuisine_types, budget_per_meal), 4)
    except Exception as exc:
        return f"RESTAURANT SEARCH FAILED: {exc}"
