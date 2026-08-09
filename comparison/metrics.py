"""
Groundedness scoring — the proposal's "bookability" pillar (S3.10).

Why
---
Cost and latency alone cannot decide between these architectures. The
single-LLM arm is cheap precisely BECAUSE it never calls an API: it invents
airlines, hotels and prices. That is the failure the literature centres on —
the best single-LLM agent scores 0.6% final-pass on TravelPlanner largely
through hallucinated venues and fabricated prices (Xie et al., 2024). An
evaluation that reports "arm A costs $0.018" without reporting that arm A's
itinerary refers to nothing real would be actively misleading.

What is measured
----------------
For each scenario the data actually retrieved from the live APIs is the ground
truth. An itinerary is scored on how much of what it names can be traced back
to that data:

  hotels_grounded    hotels named in the itinerary that appear in the API results
  airlines_grounded  airlines named that appear in the flight results
  prices_grounded    quoted prices that match a real quoted fare or nightly rate

This is deliberately a *recall of real entities*, not a hallucination detector:
it answers "is this itinerary built from retrieved data?" A tool-less arm
scores near zero, which is the point.

Prices are matched with a tolerance because an itinerary legitimately rounds
($947 -> "about $950") and legitimately sums nightly rates into totals.

Interpreting the two signals (important — they are not equally strong)
----------------------------------------------------------------------
Name matching is WEAK evidence on its own. A model with no tool access can
still name a real airline by guessing the obvious one for the route: measured
on SC-01, the tool-less arm "matched" Turkish Airlines for Istanbul purely by
prior knowledge, having called no API at all.

Price matching is the robust signal. Guessing a fare that lands within 2% of a
real quoted price is not something prior knowledge delivers. On the same
scenario the tool-less arm quoted 57 prices and matched 0 of them, while the
tool-using arms matched 57-59%.

So report prices_grounded_pct as the bookability headline and treat the name
counts as supporting colour, not proof.
"""

import json
import re
from typing import Dict, List

PRICE_TOLERANCE = 0.02  # 2% — absorbs rounding, not invention

# Words that appear inside hotel names but are far too generic to count as a
# match on their own; without this "Hotel" alone would score as grounded.
_GENERIC = {
    "hotel", "hotels", "the", "istanbul", "airport", "city", "old", "town",
    "inn", "suites", "resort", "palace", "house", "centre", "center", "grand",
    "park", "plaza", "royal", "garden", "boutique", "apartment", "apartments",
}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(text).lower())


def _distinctive(name: str) -> List[str]:
    """Tokens from a name that are specific enough to identify it."""
    return [t for t in _norm(name).split() if len(t) > 3 and t not in _GENERIC]


def extract_ground_truth(flights_raw: str, hotels_raw: str) -> Dict:
    """Pull the real entity names and prices out of the retrieved API payloads."""
    hotels = re.findall(r"Hotel #\d+:\s*(.+)", hotels_raw or "")
    nightly = [float(p) for p in re.findall(r"\((?:\$|USD\s*)([\d.]+)/night\)", hotels_raw or "")]

    airlines: List[str] = []
    fares: List[float] = []
    try:
        data = json.loads(flights_raw) if flights_raw else {}
        for f in data.get("flights") or []:
            if f.get("airline"):
                airlines.append(f["airline"])
            if f.get("total_price"):
                fares.append(float(f["total_price"]))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return {
        "hotels": [h.strip() for h in hotels],
        "airlines": sorted(set(airlines)),
        "prices": sorted(set(nightly + fares)),
    }


def _name_in_text(name: str, text_norm: str) -> bool:
    tokens = _distinctive(name)
    if not tokens:
        return False
    # Two distinctive tokens is a confident match; one is enough only when the
    # name has just one distinctive token to give (e.g. "Theodora").
    hits = sum(1 for t in tokens if t in text_norm)
    return hits >= (2 if len(tokens) > 1 else 1)


def score_groundedness(itinerary: str, truth: Dict) -> Dict:
    """Score one itinerary against the scenario's retrieved data."""
    if not itinerary:
        return {"scored": False, "reason": "empty itinerary"}

    text_norm = _norm(itinerary)

    hotels_hit = [h for h in truth.get("hotels", []) if _name_in_text(h, text_norm)]
    airlines_hit = [a for a in truth.get("airlines", []) if _name_in_text(a, text_norm)]

    quoted = [float(p.replace(",", "")) for p in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)", itinerary)]
    real_prices = truth.get("prices", [])
    prices_hit = [
        q for q in quoted
        if any(abs(q - r) <= max(r * PRICE_TOLERANCE, 1.0) for r in real_prices)
    ]

    n_hotels = len(truth.get("hotels", [])) or 1
    n_airlines = len(truth.get("airlines", [])) or 1

    return {
        "scored": True,
        "hotels_grounded": len(hotels_hit),
        "hotels_available": len(truth.get("hotels", [])),
        "hotels_grounded_pct": round(len(hotels_hit) / n_hotels * 100, 1),
        "airlines_grounded": len(airlines_hit),
        "airlines_available": len(truth.get("airlines", [])),
        "airlines_grounded_pct": round(len(airlines_hit) / n_airlines * 100, 1),
        "prices_quoted": len(quoted),
        "prices_grounded": len(prices_hit),
        "prices_grounded_pct": round(len(prices_hit) / len(quoted) * 100, 1) if quoted else 0.0,
        # The headline: did this itinerary cite ANY real retrieved entity?
        "uses_real_data": bool(hotels_hit or airlines_hit),
        "matched_hotels": hotels_hit[:5],
        "matched_airlines": airlines_hit[:5],
    }
