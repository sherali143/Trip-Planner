"""
Scores how much of an itinerary came from real data.

Counts the hotels, airlines and prices in a plan that can be traced back to
something the APIs actually returned. A plan invented from model knowledge
reads fluently and scores near zero.
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
