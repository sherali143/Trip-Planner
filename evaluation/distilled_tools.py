"""
Distilled MCP tools for the optimised 6-agent arm.

Why
---
Measured on SC-01, the naive 6-agent arm spent 94,959 tokens, of which
**79,097 (83%) were prompt tokens**. Raw tool output is only ~2,250 tokens in
total, so the cost is not the payload itself — it is that every ReAct iteration
re-sends the accumulated transcript plus the full JSON schema and docstring of
every tool bound to that agent. The naive hotel agent carries eight tools, so
eight tool schemas are re-serialised on every one of its iterations.

This module attacks that directly:
  * one narrow tool per specialist instead of four to eight,
  * short docstrings (the docstring IS the prompt payload),
  * results distilled to the top few options as compact lines rather than the
    full API response.

This is the distillation stage the proposal describes as part of the MCP
lifecycle (S3.5) and the "returns the top three choices, not the 12 kB API
response" behaviour promised for the specialist agents (S3.4) — neither of
which existed in the implementation.

The DATA is unchanged from the naive arm: these wrappers call the same server
functions, hitting the same APIs through the same recording layer, so the
comparison isolates prompt economics rather than data quality.

One difference worth stating, because "unchanged data path" would otherwise
overstate it: the naive arm reaches those functions through the MCP client over
JSON-RPC, which spawns the server as a subprocess, while these wrappers import and
call them in-process. The responses are identical — same functions, same cache —
but the transport is not. That adds a small, real amount to the naive arm's
wall-clock time, on the order of a second or two per tool call against a total
dominated by twenty-odd sequential model requests at roughly fifteen seconds each.

It does not touch the token comparison, which is what the B-versus-C finding
rests on: transport cannot change how many tokens a prompt contains. It is a minor
confound in the latency comparison between those two arms, and the headline
latency claim in Chapter 6 is C against D, both of which call in-process.
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
