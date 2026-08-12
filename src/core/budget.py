"""
Scenario-aware budget allocation.

Why this exists
---------------
The system previously hardcoded one split for every trip — flights 35%,
accommodation 35%, activities 20%, meals 10% — written into seven places. That
is wrong for most trips, and it was an unstated assumption with no source
behind it.

It is wrong because the two largest categories scale on *different* axes:

  * flight cost is roughly **per person** and set by **distance**. It does not
    care how many nights you stay.
  * accommodation cost is **per night** and largely **shared** between
    travellers in a room. It does not care how far you flew.

So a 3-night trip to a nearby city and a 14-night long-haul family trip cannot
sensibly use the same percentages. On a short long-haul trip the flight
dominates; on a long regional trip accommodation does.

Evidence base
-------------
Published breakdowns cluster in these ranges rather than on single values:

  accommodation  30-40%   flights  20-30%   food  15-25%   activities  10-20%

NerdWallet's Travel Price Index weights flights at 36% and lodging at 30% of
travel spending. A widely used planning heuristic splits 50% essentials
(flights + accommodation), 30% experiences (food + activities), 20% buffer.
Daily spend separates sharply by style — roughly $121/day budget, $325/day
mid-range, $925/day luxury — with accommodation the largest single category for
luxury travellers.

Sources:
  NerdWallet Travel Price Index — https://www.nerdwallet.com/travel/learn/travel-price-tracker
  Motley Fool, Average Cost of a Vacation 2025 — https://www.fool.com/money/research/average-cost-of-a-vacation/
  YouGov, Vacation budget breakdown — https://yougov.com/articles/49764-vacation-budget-breakdown-what-will-consumers-spend-more-or-less-money-on
  Pacaso, Average Vacation Cost 2026 — https://www.pacaso.com/blog/average-vacation-cost

The user always has the final word. This module SUGGESTS and EXPLAINS; it never
overrides an explicit choice. It does warn when a choice looks unlikely to work,
because silently accepting an impossible split produces an itinerary that cannot
be booked.

Note on the evaluation arms
---------------------------
comparison/ deliberately keeps the legacy fixed split (see LEGACY_ALLOCATION).
Changing the split changes budget_per_night, which changes the hotel query, which
would invalidate every recorded API response and force live calls against a
30/50-per-month quota. The architecture comparison is about where the LLM sits,
not about budget policy, so holding allocation constant keeps the arms comparable.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

CATEGORIES = ("flights", "accommodation", "activities", "meals")

# What each category pays for, in plain language. Shown to the user before they
# are asked to change anything — a person cannot sensibly choose a split for
# categories they have to guess the meaning of.
CATEGORY_HELP: Dict[str, str] = {
    "flights": "Return airfare for everyone travelling. Set by distance, and it is "
               "per person — two travellers means roughly double.",
    "accommodation": "Hotel for the whole stay. Charged per night, and normally "
                     "shared, so a couple in one room pays about the same as one person.",
    "activities": "Entry tickets, tours, museums, day trips, local transport.",
    "meals": "Food and drink for the trip — roughly two paid meals per person per day.",
}

# The split the system used before this module existed. comparison/ still uses
# it so previously recorded results stay valid; see the module docstring.
LEGACY_ALLOCATION: Dict[str, float] = {
    "flights": 0.35, "accommodation": 0.35, "activities": 0.20, "meals": 0.10,
}

# Starting point before scenario adjustment, placed mid-range in the published
# figures above.
BASE_ALLOCATION: Dict[str, float] = {
    "flights": 0.32, "accommodation": 0.33, "activities": 0.17, "meals": 0.18,
}

# Rough haul classification. Flight share depends mainly on distance, and the
# scenarios in this project all originate in Pakistan, so regions are grouped
# relative to that. Unknown destinations fall back to "medium", which is
# deliberately the least opinionated option.
_SHORT_HAUL = {
    "dubai", "abu dhabi", "sharjah", "doha", "muscat", "kuwait", "bahrain",
    "delhi", "mumbai", "kabul", "tehran", "riyadh", "jeddah", "dammam",
}
_LONG_HAUL = {
    "london", "paris", "new york", "toronto", "sydney", "melbourne", "tokyo",
    "los angeles", "chicago", "manchester", "birmingham", "frankfurt", "berlin",
    "amsterdam", "madrid", "barcelona", "rome", "milan", "seoul", "osaka",
    "vancouver", "washington", "boston", "san francisco",
}


@dataclass
class Allocation:
    """A budget split, the money it implies, and why it was chosen."""

    shares: Dict[str, float]                     # fractions, sum to 1.0
    amounts: Dict[str, float]                    # absolute currency amounts
    total_budget: float
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    source: str = "suggested"                    # "suggested" | "user" | "legacy"

    def percent(self, category: str) -> float:
        return round(self.shares.get(category, 0.0) * 100, 1)

    def as_dict(self) -> Dict[str, float]:
        """The budget_breakdown shape the rest of the pipeline already expects."""
        return dict(self.amounts)

    def explain(self, currency: str = "$") -> str:
        """A complete, readable explanation — what, how much, and why."""
        lines = [
            "BUDGET ALLOCATION",
            "=" * 62,
            f"Total budget: {currency}{self.total_budget:,.0f}",
            "",
        ]
        for cat in CATEGORIES:
            lines.append(f"  {cat.title():<14} {self.percent(cat):>5.1f}%   "
                         f"{currency}{self.amounts.get(cat, 0):>10,.0f}")
            lines.append(f"  {'':<14} {CATEGORY_HELP[cat]}")
            lines.append("")

        if self.reasons:
            lines.append("Why this split for your trip:")
            lines.extend(f"  - {r}" for r in self.reasons)
            lines.append("")

        if self.warnings:
            lines.append("Please check:")
            lines.extend(f"  ! {w}" for w in self.warnings)
            lines.append("")

        lines.append("This is a suggestion. You can change any of it.")
        lines.append("=" * 62)
        return "\n".join(lines)


def _haul(origin: str, destination: str) -> str:
    dest = (destination or "").strip().lower()
    for city in _SHORT_HAUL:
        if city in dest:
            return "short"
    for city in _LONG_HAUL:
        if city in dest:
            return "long"
    return "medium"


def _normalise(shares: Dict[str, float]) -> Dict[str, float]:
    """Scale shares to sum to exactly 1.0, dropping negatives."""
    clean = {c: max(0.0, float(shares.get(c, 0.0))) for c in CATEGORIES}
    total = sum(clean.values())
    if total <= 0:
        return dict(BASE_ALLOCATION)
    return {c: v / total for c, v in clean.items()}


def suggest_allocation(
    total_budget: float,
    trip_duration: int = 5,
    num_travelers: int = 1,
    travel_style: str = "moderate",
    origin: str = "",
    destination: str = "",
) -> Allocation:
    """
    Suggest a split for THIS trip, with the reasoning recorded.

    Adjustments are applied to BASE_ALLOCATION and then renormalised, so the
    result always sums to 100% regardless of how many rules fire.
    """
    shares = dict(BASE_ALLOCATION)
    reasons: List[str] = []

    # --- distance: sets the flight share -------------------------------------
    haul = _haul(origin, destination)
    if haul == "long":
        shares["flights"] += 0.10
        reasons.append("Long-haul destination, so airfare takes a larger share.")
    elif haul == "short":
        shares["flights"] -= 0.08
        reasons.append("Short-haul destination, so airfare is a smaller share.")

    # --- duration: nights dilute the one-off flight cost ---------------------
    if trip_duration >= 10:
        shares["flights"] -= 0.08
        shares["accommodation"] += 0.05
        shares["meals"] += 0.03
        reasons.append(f"{trip_duration} nights — the one-off flight cost is spread "
                       "thin, while nightly and daily costs dominate.")
    elif trip_duration <= 3:
        shares["flights"] += 0.08
        shares["accommodation"] -= 0.05
        shares["meals"] -= 0.03
        reasons.append(f"Only {trip_duration} nights — the flight is most of the cost.")

    # --- party size: flights scale per head, rooms are shared ----------------
    if num_travelers >= 2:
        shares["flights"] += 0.05
        shares["accommodation"] -= 0.03
        shares["meals"] += 0.02
        reasons.append(f"{num_travelers} travellers — airfare and meals multiply per "
                       "person, but a room is shared.")

    # --- style ---------------------------------------------------------------
    style = (travel_style or "moderate").strip().lower()
    if style in ("luxury", "premium", "high-end"):
        shares["accommodation"] += 0.07
        shares["meals"] += 0.03
        shares["activities"] -= 0.02
        reasons.append("Luxury style — accommodation is the largest category for "
                       "luxury travellers.")
    elif style in ("budget", "backpacker", "cheap", "economy"):
        shares["accommodation"] -= 0.06
        shares["activities"] += 0.03
        shares["meals"] += 0.03
        reasons.append("Budget style — cheaper stays leave more for food and doing things.")

    shares = _normalise(shares)
    allocation = Allocation(
        shares=shares,
        amounts={c: round(total_budget * s, 2) for c, s in shares.items()},
        total_budget=float(total_budget),
        reasons=reasons or ["Balanced split based on published travel-spending averages."],
        source="suggested",
    )
    allocation.warnings = check_realism(allocation, trip_duration, num_travelers, haul)
    return allocation


def check_realism(
    allocation: Allocation,
    trip_duration: int,
    num_travelers: int,
    haul: str = "medium",
) -> List[str]:
    """
    Flag splits that are unlikely to produce a bookable trip.

    This is the difference between asking a user for a number and actually
    handling the answer: a split can sum to 100% and still be unusable, and
    saying so up front is more useful than returning an itinerary that cannot
    be booked.
    """
    warnings: List[str] = []
    amounts = allocation.amounts
    nights = max(1, trip_duration)
    heads = max(1, num_travelers)

    # Floors are "clearly not bookable", not "looks tight" — the aim is to catch
    # impossible allocations without warning on every economical trip. Calibrated
    # against observed return fares from Pakistan: LHE-DXB around 250,
    # LHE-IST around 900 (measured, see .api_cache), long-haul higher again.
    per_person_flight = amounts.get("flights", 0) / heads
    floor = {"short": 180, "medium": 350, "long": 600}.get(haul, 350)
    if per_person_flight < floor:
        warnings.append(
            f"Flights: {per_person_flight:,.0f} per person may be too low — "
            f"{haul}-haul return fares usually start around {floor:,.0f}."
        )

    per_night = amounts.get("accommodation", 0) / nights
    if per_night < 25:
        warnings.append(
            f"Accommodation: {per_night:,.0f} per night is below most hostel rates."
        )

    per_meal = amounts.get("meals", 0) / (nights * heads * 2)
    if per_meal < 4:
        warnings.append(
            f"Meals: about {per_meal:,.0f} per meal per person — very tight."
        )

    if amounts.get("activities", 0) / nights < 5:
        warnings.append("Activities: under 5 per day leaves little for entry tickets or transport.")

    return warnings


def parse_user_allocation(
    raw: str,
    total_budget: float,
    fallback: Optional[Dict[str, float]] = None,
) -> Tuple[Optional[Dict[str, float]], List[str]]:
    """
    Read a split the user typed, in whichever form they typed it.

    Accepts, case-insensitively:
        "40/30/20/10"                      four numbers, in category order
        "flights 40, hotel 30"             named, partial — the rest keeps its
                                           existing proportions
        "flights 500, hotels 400"          absolute amounts
        ""                                 no opinion -> (None, [])

    Returns (shares or None, messages). Never raises on bad input: a user
    mistyping a number should get an explanation, not a stack trace.
    """
    messages: List[str] = []
    text = (raw or "").strip().lower()
    if not text or text in ("d", "default", "y", "yes", "ok", "keep", "-"):
        return None, messages

    base = dict(fallback or BASE_ALLOCATION)
    aliases = {
        "flights": "flights", "flight": "flights", "air": "flights", "airfare": "flights",
        "accommodation": "accommodation", "hotel": "accommodation", "hotels": "accommodation",
        "stay": "accommodation", "lodging": "accommodation", "room": "accommodation",
        "activities": "activities", "activity": "activities", "tours": "activities",
        "sightseeing": "activities", "attractions": "activities",
        "meals": "meals", "meal": "meals", "food": "meals", "eating": "meals",
        "dining": "meals",
    }

    import re

    # Form 1: four bare numbers separated by / , or whitespace.
    bare = re.findall(r"\d+(?:\.\d+)?", text)
    if not any(word in text for word in aliases) and len(bare) == 4:
        values = [float(v) for v in bare]
        messages.append(f"Read as flights/accommodation/activities/meals = "
                        f"{'/'.join(str(int(v)) for v in values)}")
        divisor = _unit_divisor(values, text, total_budget, messages)
        shares = {c: v / divisor for c, v in zip(CATEGORIES, values)}
        return _finalise_user_shares(shares, total_budget, messages), messages

    # Form 2: named pairs, possibly partial.
    pairs = re.findall(r"([a-z]+)\s*[:=]?\s*\$?\s*(\d+(?:\.\d+)?)\s*%?", text)
    named: Dict[str, float] = {}
    for word, value in pairs:
        category = aliases.get(word)
        if category:
            named[category] = float(value)

    if not named:
        messages.append(
            "Could not read that. Try '40/30/20/10' (percentages in the order "
            "flights/accommodation/activities/meals), or name them like "
            "'hotel 45, flights 25'."
        )
        return None, messages

    # Absolute amounts or percentages? See _unit_divisor for the rule.
    divisor = _unit_divisor(list(named.values()), text, total_budget, messages)
    if divisor != 100.0:
        shares = {c: named.get(c, 0.0) / divisor for c in CATEGORIES}
        missing = [c for c in CATEGORIES if c not in named]
        if missing:
            stated = sum(shares[c] for c in named)
            remaining = max(0.0, 1.0 - stated)
            base_missing = sum(base[c] for c in missing) or 1.0
            for c in missing:
                shares[c] = remaining * (base[c] / base_missing)
            messages.append(f"Kept the suggested proportions for: {', '.join(missing)}.")
        return _finalise_user_shares(shares, total_budget, messages), messages

    # Percentages, possibly partial: give the rest what is left over, keeping
    # their relative proportions.
    missing = [c for c in CATEGORIES if c not in named]
    shares = {c: named[c] / 100.0 for c in named}
    if missing:
        stated = sum(shares.values())
        remaining = max(0.0, 1.0 - stated)
        base_missing = sum(base[c] for c in missing) or 1.0
        for c in missing:
            shares[c] = remaining * (base[c] / base_missing)
        messages.append(f"You set {', '.join(named)}; the remaining "
                        f"{remaining * 100:.0f}% was divided across "
                        f"{', '.join(missing)}.")

    return _finalise_user_shares(shares, total_budget, messages), messages


def _unit_divisor(values: List[float], text: str, total_budget: float,
                  messages: List[str]) -> float:
    """
    Decide whether the user typed percentages or money, and return the divisor
    that converts their numbers into fractions (100 for percent, the total
    budget for money).

    A naive "sum > 100 means money" rule misreads the common case of
    percentages that overshoot — "flights 50, hotel 50, food 50, tours 50"
    sums to 200 but is plainly four percentages the user needs rescaling, not
    $200 spread over a $1,000 trip. The signals that actually distinguish them:

      * an explicit currency symbol
      * any single value above 100, since nobody writes "150%"
      * a total in the neighbourhood of the trip budget
    """
    if not values:
        return 100.0

    total = sum(values)
    absolute = (
        "$" in text
        or any(v > 100 for v in values)
        or (total_budget > 0 and 0.5 * total_budget <= total <= 1.5 * total_budget)
    )

    if absolute and total_budget > 0:
        messages.append("Read as amounts of money, not percentages.")
        return float(total_budget)

    messages.append("Read as percentages.")
    return 100.0


def _finalise_user_shares(shares: Dict[str, float], total_budget: float,
                          messages: List[str]) -> Dict[str, float]:
    raw_total = sum(max(0.0, v) for v in shares.values())
    if raw_total <= 0:
        messages.append("Everything came to zero, so the suggested split was kept.")
        return dict(BASE_ALLOCATION)
    if abs(raw_total - 1.0) > 0.011:
        messages.append(f"Your numbers added up to {raw_total * 100:.0f}%, "
                        f"so they were scaled to 100%.")
    return _normalise(shares)


def build_allocation(
    total_budget: float,
    trip_duration: int = 5,
    num_travelers: int = 1,
    travel_style: str = "moderate",
    origin: str = "",
    destination: str = "",
    user_input: str = "",
) -> Allocation:
    """
    Suggest a split, then apply the user's preference if they expressed one.

    This is the entry point for CLI and web flows.
    """
    suggestion = suggest_allocation(
        total_budget, trip_duration, num_travelers, travel_style, origin, destination
    )

    user_shares, messages = parse_user_allocation(
        user_input, total_budget, fallback=suggestion.shares
    )
    if user_shares is None:
        suggestion.reasons.extend(messages)
        return suggestion

    chosen = Allocation(
        shares=user_shares,
        amounts={c: round(total_budget * s, 2) for c, s in user_shares.items()},
        total_budget=float(total_budget),
        reasons=["You chose this split."] + messages,
        source="user",
    )
    # Still check it — the user's choice is honoured, but they are told if it
    # looks unbookable rather than finding out from an empty itinerary.
    chosen.warnings = check_realism(
        chosen, trip_duration, num_travelers, _haul(origin, destination)
    )
    return chosen
