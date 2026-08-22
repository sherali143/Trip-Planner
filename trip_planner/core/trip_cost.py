"""
What a trip actually costs — estimation, suggestion, and a hard floor.

Why this exists
---------------
Budget validation was a fixed formula that ignored where you were going:

    min_flight_cost = 300 * num_travelers      # Dubai or Tokyo, same number
    min_hotel_cost  = 50 * trip_duration       # Bangkok or London, same number
    min_daily_cost  = 30 * trip_duration * num_travelers
    if total_budget < min_total * 0.6: reject  # 0.6 with no justification

So a $700 Karachi-Bangkok trip and a $700 Lahore-New York trip were judged
against the same threshold, when one is comfortable and the other is impossible.
It could also only ever say "no" — it never told the user what the trip *would*
cost, which is the thing they actually need to know.

What this replaces it with
--------------------------
Costs are built from the trip's own facts: how far (flight, per person), how
many nights (hotel, shared), how many people (meals and activities, per person
per day), and at what standard. Every destination sits in a price tier, so
Bangkok and London are not costed alike.

Three tiers are produced:

  minimum      the cheapest way this trip could be done at all — hostel beds,
               cheapest fare, street food. Below this the trip is not bookable
               and the system refuses rather than producing a fictional plan.
  comfortable  a normal mid-range trip. This is what gets suggested.
  luxury       four-star and up.

The floor is a genuine floor. Above it the user may spend whatever they like,
and a tight-but-possible budget is accepted with a warning rather than blocked —
the system's job is to be honest about what is achievable, not to impose taste.

Calibration
-----------
Anchors below are deliberately conservative for the minimum tier (they must be
achievable, not typical) and mid-range for the comfortable tier. Reference
points: published daily spends of roughly $121 budget / $325 mid-range / $925
luxury for US travel, scaled to regional price levels; and fares measured by
this project from Pakistan — Lahore-Istanbul returned $937 for a mid-range
economy return (see .api_cache), Lahore-Dubai sits far lower.

Sources:
  Motley Fool, Average Cost of a Vacation 2025 — https://www.fool.com/money/research/average-cost-of-a-vacation/
  Pacaso, Average Vacation Cost 2026 — https://www.pacaso.com/blog/average-vacation-cost
  NerdWallet Travel Price Index — https://www.nerdwallet.com/travel/learn/travel-price-tracker
"""

from dataclasses import dataclass, field
from typing import Dict, List

# --- destination price tiers ------------------------------------------------
# Which tier a city sits in drives hotel, food and activity costs. Unknown
# destinations fall to "moderate", the least opinionated option.
_CHEAP = {
    "bangkok", "phuket", "chiang mai", "kuala lumpur", "penang", "hanoi",
    "ho chi minh", "bali", "denpasar", "jakarta", "colombo", "kathmandu",
    "cairo", "istanbul", "antalya", "delhi", "mumbai", "goa", "dhaka",
}
_EXPENSIVE = {
    "london", "paris", "new york", "tokyo", "osaka", "zurich", "geneva",
    "singapore", "sydney", "melbourne", "toronto", "vancouver", "san francisco",
    "los angeles", "boston", "washington", "amsterdam", "copenhagen", "oslo",
    "stockholm", "dublin", "reykjavik", "male", "maldives",
}

# --- flight cost per person, return, economy --------------------------------
# minimum = cheapest realistically bookable; typical = what to actually plan for.
_FLIGHT_COST = {
    "short":  {"minimum": 180, "typical": 320},
    "medium": {"minimum": 350, "typical": 700},
    "long":   {"minimum": 600, "typical": 1050},
}

_SHORT_HAUL = {
    "dubai", "abu dhabi", "sharjah", "doha", "muscat", "kuwait", "bahrain",
    "delhi", "mumbai", "kabul", "tehran", "riyadh", "jeddah", "dammam", "goa",
}
_LONG_HAUL = {
    "london", "paris", "new york", "toronto", "sydney", "melbourne", "tokyo",
    "osaka", "seoul", "los angeles", "chicago", "manchester", "birmingham",
    "frankfurt", "berlin", "amsterdam", "madrid", "barcelona", "rome", "milan",
    "vancouver", "washington", "boston", "san francisco", "dublin",
}

# --- per-night hotel, and per-person-per-day food and activities ------------
_NIGHTLY = {
    "cheap":     {"minimum": 12, "comfortable": 55,  "luxury": 200},
    "moderate":  {"minimum": 30, "comfortable": 105, "luxury": 340},
    "expensive": {"minimum": 45, "comfortable": 160, "luxury": 450},
}
_MEALS_PER_DAY = {
    "cheap":     {"minimum": 7,  "comfortable": 25, "luxury": 85},
    "moderate":  {"minimum": 12, "comfortable": 40, "luxury": 120},
    "expensive": {"minimum": 18, "comfortable": 55, "luxury": 150},
}
_ACTIVITIES_PER_DAY = {
    "cheap":     {"minimum": 4, "comfortable": 20, "luxury": 65},
    "moderate":  {"minimum": 7, "comfortable": 30, "luxury": 95},
    "expensive": {"minimum": 9, "comfortable": 40, "luxury": 120},
}

# Verdicts, ordered from unworkable to generous.
IMPOSSIBLE = "impossible"
VERY_TIGHT = "very_tight"
WORKABLE = "workable"
COMFORTABLE = "comfortable"
GENEROUS = "generous"


@dataclass
class CostEstimate:
    """What a specific trip costs at three standards, and how it was derived."""

    minimum: float
    comfortable: float
    luxury: float
    breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    haul: str = "medium"
    price_tier: str = "moderate"
    nights: int = 0
    travelers: int = 1
    destination: str = ""
    # False when the destination matched nothing in the price table and the
    # estimate therefore rests on the middle row of every band rather than on
    # data for this place. The figure is still returned — planning should not
    # stop because a city is unlisted — but a caller quoting it as "what this
    # trip costs" is overstating what it knows, and a traveller told a budget is
    # workable deserves to know the estimate behind that was a default.
    priced_from_data: bool = True

    def explain(self, currency: str = "$") -> str:
        d = self.destination or "your destination"
        lines = [
            f"WHAT THIS TRIP COSTS — {d}, {self.nights} nights, "
            f"{self.travelers} traveller(s)",
            "=" * 66,
            f"  {d.title()} is a {self.price_tier}-priced destination on a "
            f"{self.haul}-haul flight."
            + ("" if self.priced_from_data else
               "  <-- NOT IN THE PRICE TABLE: these are mid-tier defaults"),
            "",
            f"  {'':<16}{'Minimum':>12}{'Comfortable':>14}{'Luxury':>12}",
            "  " + "-" * 54,
        ]
        for cat in ("flights", "accommodation", "meals", "activities"):
            row = self.breakdown.get(cat, {})
            lines.append(
                f"  {cat.title():<16}"
                f"{currency + format(row.get('minimum', 0), ',.0f'):>12}"
                f"{currency + format(row.get('comfortable', 0), ',.0f'):>14}"
                f"{currency + format(row.get('luxury', 0), ',.0f'):>12}"
            )
        lines += [
            "  " + "-" * 54,
            f"  {'TOTAL':<16}{currency + format(self.minimum, ',.0f'):>12}"
            f"{currency + format(self.comfortable, ',.0f'):>14}"
            f"{currency + format(self.luxury, ',.0f'):>12}",
            "",
            f"  Minimum     = cheapest this trip can be done at all "
            f"(hostel, cheapest fare, street food).",
            f"                Below {currency}{self.minimum:,.0f} it is not bookable.",
            f"  Comfortable = a normal mid-range trip. This is the recommendation.",
            "=" * 66,
        ]
        return "\n".join(lines)


@dataclass
class BudgetVerdict:
    """Whether a stated budget can actually buy the trip."""

    verdict: str
    feasible: bool
    stated_budget: float
    estimate: CostEstimate
    message: str
    suggestions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """
        Attach the caveat when the estimate rests on defaults, not on data.

        Done here rather than in each of the five verdict branches, so a new
        branch cannot be added that forgets it. An unlisted destination used to
        produce a figure indistinguishable from a priced one: "Kyoto" was costed
        as medium-haul at moderate prices — about $614 for five nights where the
        real figure is nearer Toronto's $987 — and a $700 budget was called
        workable with nothing on screen to suggest the number was a default.

        The estimate is still returned and planning still proceeds. What changes
        is that the traveller is told which of the two kinds of answer they have.
        """
        if self.estimate.priced_from_data:
            return
        dest = self.estimate.destination or "that destination"
        self.message += (
            f"\n\n  NOTE: {dest} is not in the price table, so this estimate uses "
            f"mid-range defaults — a medium-haul flight at moderate prices. It is "
            f"likely to be optimistic for an expensive or distant destination. "
            f"Naming a major city gives a figure based on price data for that place."
        )
        self.suggestions.append(
            f"Treat this figure as indicative: {dest} is not in the price table.")


def classify_haul(destination: str) -> str:
    dest = (destination or "").strip().lower()
    if any(city in dest for city in _SHORT_HAUL):
        return "short"
    if any(city in dest for city in _LONG_HAUL):
        return "long"
    return "medium"


def is_known_destination(destination: str) -> bool:
    """
    True when there is actual price data for this destination.

    Unknown cities are still costed, using mid-tier defaults, so that planning
    can proceed — but callers presenting a figure as "what this trip costs"
    need to know whether it rests on data or on a default.
    """
    dest = (destination or "").strip().lower()
    if not dest:
        return False
    return any(
        city in dest
        for group in (_CHEAP, _EXPENSIVE, _SHORT_HAUL, _LONG_HAUL)
        for city in group
    )


def classify_price_tier(destination: str) -> str:
    dest = (destination or "").strip().lower()
    if any(city in dest for city in _CHEAP):
        return "cheap"
    if any(city in dest for city in _EXPENSIVE):
        return "expensive"
    return "moderate"


def estimate_trip_cost(
    destination: str,
    nights: int = 5,
    travelers: int = 1,
    origin: str = "",
) -> CostEstimate:
    """
    Estimate what this trip costs at minimum, comfortable and luxury standards.

    Scaling rules follow how the costs are actually incurred: airfare is per
    person, accommodation is per night and shared, food and activities are per
    person per day.
    """
    nights = max(1, int(nights or 1))
    travelers = max(1, int(travelers or 1))
    haul = classify_haul(destination)
    tier = classify_price_tier(destination)

    flights = _FLIGHT_COST[haul]
    # Rooms sleep two; three travellers need two rooms.
    rooms = max(1, (travelers + 1) // 2)
    days = nights + 1  # you eat on the day you arrive and the day you leave

    breakdown = {
        "flights": {
            "minimum": flights["minimum"] * travelers,
            "comfortable": flights["typical"] * travelers,
            "luxury": flights["typical"] * 2.6 * travelers,
        },
        "accommodation": {
            level: _NIGHTLY[tier][level] * nights * rooms
            for level in ("minimum", "comfortable", "luxury")
        },
        "meals": {
            level: _MEALS_PER_DAY[tier][level] * days * travelers
            for level in ("minimum", "comfortable", "luxury")
        },
        "activities": {
            level: _ACTIVITIES_PER_DAY[tier][level] * days * travelers
            for level in ("minimum", "comfortable", "luxury")
        },
    }

    totals = {
        level: sum(cat[level] for cat in breakdown.values())
        for level in ("minimum", "comfortable", "luxury")
    }

    return CostEstimate(
        minimum=round(totals["minimum"]),
        comfortable=round(totals["comfortable"]),
        luxury=round(totals["luxury"]),
        breakdown={k: {kk: round(vv) for kk, vv in v.items()} for k, v in breakdown.items()},
        haul=haul,
        price_tier=tier,
        nights=nights,
        travelers=travelers,
        destination=destination,
        priced_from_data=is_known_destination(destination),
    )


def assess_budget(
    total_budget: float,
    destination: str,
    nights: int = 5,
    travelers: int = 1,
    origin: str = "",
) -> BudgetVerdict:
    """
    Judge a stated budget against what the trip actually costs.

    Only a budget below the true minimum is refused. Everything above it is
    accepted — tight budgets get a warning and concrete options, not a block,
    because "tight" is a legitimate choice and only "impossible" is not.
    """
    estimate = estimate_trip_cost(destination, nights, travelers, origin)
    budget = float(total_budget or 0)
    dest = destination or "your destination"

    if budget < estimate.minimum:
        shortfall = estimate.minimum - budget
        nights_affordable = _max_affordable_nights(budget, destination, travelers)
        suggestions = [
            f"Raise the budget to at least ${estimate.minimum:,.0f} "
            f"(${estimate.comfortable:,.0f} is comfortable).",
        ]
        if nights_affordable >= 1:
            suggestions.append(
                f"Keep ${budget:,.0f} and shorten the trip to about "
                f"{nights_affordable} night(s)."
            )
        else:
            suggestions.append(
                "Even one night is out of reach at this budget, mostly because "
                f"the flight alone is about "
                f"${estimate.breakdown['flights']['minimum']:,.0f} for "
                f"{travelers} traveller(s)."
            )
        if travelers > 1:
            per_head = budget / travelers
            suggestions.append(
                f"That is ${per_head:,.0f} per person. Travelling with fewer "
                f"people, or splitting a higher total, would help."
            )
        suggestions.append("Choose a nearer or cheaper destination.")

        return BudgetVerdict(
            verdict=IMPOSSIBLE,
            feasible=False,
            stated_budget=budget,
            estimate=estimate,
            message=(
                f"${budget:,.0f} cannot cover {nights} nights in {dest} for "
                f"{travelers} traveller(s). The cheapest this trip can be done "
                f"is about ${estimate.minimum:,.0f} — short ${shortfall:,.0f}."
            ),
            suggestions=suggestions,
        )

    if budget < estimate.minimum * 1.25:
        return BudgetVerdict(
            verdict=VERY_TIGHT, feasible=True, stated_budget=budget, estimate=estimate,
            message=(
                f"${budget:,.0f} is workable but very tight for {dest}. Expect "
                f"hostels or budget hotels, street food, and mostly free "
                f"attractions. A comfortable trip would be around "
                f"${estimate.comfortable:,.0f}."
            ),
            suggestions=["Proceeding — the plan will favour the cheapest real options."],
        )

    if budget < estimate.comfortable:
        return BudgetVerdict(
            verdict=WORKABLE, feasible=True, stated_budget=budget, estimate=estimate,
            message=(
                f"${budget:,.0f} works for {dest}. It sits between the minimum "
                f"(${estimate.minimum:,.0f}) and a comfortable trip "
                f"(${estimate.comfortable:,.0f}), so expect good value rather "
                f"than luxury."
            ),
        )

    if budget < estimate.luxury:
        return BudgetVerdict(
            verdict=COMFORTABLE, feasible=True, stated_budget=budget, estimate=estimate,
            message=(
                f"${budget:,.0f} is comfortable for {dest} — mid-range hotels, "
                f"restaurant meals and paid attractions are all affordable."
            ),
        )

    return BudgetVerdict(
        verdict=GENEROUS, feasible=True, stated_budget=budget, estimate=estimate,
        message=(
            f"${budget:,.0f} is generous for {dest}. Four-star and above is "
            f"within reach (luxury level is about ${estimate.luxury:,.0f})."
        ),
    )


def _max_affordable_nights(budget: float, destination: str, travelers: int) -> int:
    """Longest trip this budget could actually cover, at minimum standard."""
    for nights in range(14, 0, -1):
        if estimate_trip_cost(destination, nights, travelers).minimum <= budget:
            return nights
    return 0


def suggest_budget(destination: str, nights: int = 5, travelers: int = 1,
                   origin: str = "") -> str:
    """A short answer to 'what budget do I need for this trip?'"""
    e = estimate_trip_cost(destination, nights, travelers, origin)
    return (
        f"For {nights} nights in {destination} with {travelers} traveller(s):\n"
        f"  Minimum (bare-bones):  ${e.minimum:,.0f}   <- below this, not bookable\n"
        f"  Comfortable:           ${e.comfortable:,.0f}   <- recommended\n"
        f"  Luxury:                ${e.luxury:,.0f}"
    )
