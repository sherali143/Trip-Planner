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


def _cost_derived_shares(
    destination: str, trip_duration: int, num_travelers: int, travel_style: str,
    total_budget: float,
) -> Optional[Tuple[Dict[str, float], str]]:
    """
    Derive the split from what the trip's parts actually cost.

    Preferred over the adjustment rules below, because it is arithmetic rather
    than estimation: if a realistic Tokyo trip costs $1,050 in airfare and $480
    in hotels, the flight share follows from those numbers instead of from a
    hand-chosen "+10% for long haul". The rules were measurably off where the
    two disagreed — on a 3-night Tokyo trip they put flights at 45.5% when the
    real cost structure puts them at 55%.

    Returns None when the destination is unknown, so the caller falls back to
    the rule-based path rather than trusting a default-priced guess.
    """
    from trip_planner.core.trip_cost import classify_price_tier, estimate_trip_cost, is_known_destination

    dest = (destination or "").strip()
    # Only claim a cost-derived split for destinations there is actually price
    # data for. An unknown city silently receives mid-tier defaults, and
    # presenting those as "what this trip costs" would be false confidence.
    if not dest or not is_known_destination(dest):
        return None

    estimate = estimate_trip_cost(dest, trip_duration, num_travelers)
    if estimate.comfortable <= 0:
        return None

    # Pick the standard the BUDGET can actually buy, not the one the user named.
    # Deriving shares from the bare-bones tier and applying them to a much
    # larger budget over-allocates badly: a 14-night Bangkok trip costs about
    # $350 in airfare, so the minimum-tier ratio puts flights at 51% — which on
    # a $3,000 budget would reserve $1,530 for a $350 flight.
    level, blend, label = _tier_for_budget(estimate, total_budget, travel_style)
    intent = parse_style(travel_style)

    def share_at(cat: str) -> float:
        low, high = blend
        # Each category sits at its own point between the two tiers: the budget
        # sets the base, and the traveller's words move the categories those
        # words were about. A luxury STAY moves the room; a luxury TRIP moves
        # the room, the food and the doing; neither shortens the flight.
        at = min(1.0, max(0.0, level + intent.level * intent.weight(cat)))
        return (estimate.breakdown[cat][low] * (1 - at)
                + estimate.breakdown[cat][high] * at)

    costs = {c: share_at(c) for c in CATEGORIES}
    total = sum(costs.values())
    if total <= 0:
        return None

    shares = _cap_at_what_it_can_cost(
        {c: costs[c] / total for c in CATEGORIES}, estimate, total_budget)

    reason = (
        f"Based on what a {label} trip to {dest} actually costs: "
        f"{estimate.haul}-haul flights for {num_travelers} traveller(s), "
        f"{trip_duration} night(s) at {classify_price_tier(dest)}-tier prices."
    )
    # Say what was understood from the traveller's own words. Without this the
    # explanation described the trip's cost structure and never acknowledged the
    # request, so someone who typed "I want a luxury stay" had no way to tell
    # whether it had been read.
    if intent.level:
        reason += f" Adjusted for what you asked for: {intent.label}."
    return shares, reason


def _cap_at_what_it_can_cost(
    shares: Dict[str, float], estimate, total_budget: float,
) -> Dict[str, float]:
    """
    Stop a category being handed more money than it could possibly absorb.

    Shares are proportions of a fixed budget, so whenever one category is pushed
    down the others rise to fill the gap — and the gap lands wherever the
    arithmetic puts it rather than where it is useful. A fourteen-night Bangkok
    trip needs about $350 of airfare; on a $6,000 budget with a strong "spend as
    little as possible" request, flights were being handed 41% of it, which is
    $2,442 reserved for a $350 flight. The searches then look for a flight ten
    times dearer than the trip needs.

    So each category is capped at what its most expensive version actually costs,
    and the surplus is offered to the categories still below their own ceiling.
    Anything nobody can absorb stays put: a budget genuinely larger than the
    luxury trip is a real situation, and inventing somewhere to put the remainder
    would be worse than leaving it in proportion.
    """
    if total_budget <= 0 or not estimate.breakdown:
        return shares

    # The ceiling is the luxury tier with headroom, not the luxury tier exactly:
    # these are estimates, and a cap that bites at the estimate would fight the
    # cost model on every generous budget.
    ceilings = {
        c: (estimate.breakdown.get(c, {}).get("luxury", 0.0) * 1.3) / total_budget
        for c in CATEGORIES
    }

    capped = dict(shares)
    for _ in range(len(CATEGORIES)):
        surplus = 0.0
        for category in CATEGORIES:
            ceiling = ceilings.get(category, 0.0)
            if ceiling > 0 and capped[category] > ceiling:
                surplus += capped[category] - ceiling
                capped[category] = ceiling
        if surplus <= 1e-9:
            break
        room = {c: max(0.0, ceilings.get(c, 0.0) - capped[c]) for c in CATEGORIES}
        available = sum(room.values())
        if available <= 1e-9:
            break                      # nothing can take it; leave the split as is
        for category in CATEGORIES:
            capped[category] += surplus * (room[category] / available)

    return _normalise(capped)


@dataclass
class StyleIntent:
    """
    What the traveller's own words asked for, as a direction and a scope.

    `level` runs from -1 (compromise on everything) through 0 (no preference
    stated) to +1 (luxury throughout). `scope` says which categories the request
    was actually about, because "luxury stay" and "luxury trip" are different
    requests and used to be treated as the same one.
    """

    level: float
    scope: Dict[str, float]
    label: str
    whole_trip: bool = True

    def weight(self, category: str) -> float:
        """
        How far this category should move, between 0 and 1.

        Flights are asymmetric, and deliberately so. Asking to upgrade cannot buy
        a shorter flight, so an upward request leaves the airfare where the
        distance put it. But asking to spend as little as possible plainly does
        include the flight — and treating it as fixed in that direction had the
        opposite effect to the one requested: money pushed out of the room piled
        onto the airfare instead, so a "spend as little as possible" trip reserved
        a business-class fare it had not asked for.
        """
        return self.scope.get(category, 0.0)


# Every category, for a request that was about the whole trip. Flights sit at zero
# even here: distance decides the airfare, and no phrasing shortens a flight. What
# a luxury request buys is a better room, better food and more to do.
_SCOPE_WHOLE_TRIP = {"flights": 0.0, "accommodation": 1.0, "meals": 0.7,
                     "activities": 0.7}
# A request about where you sleep, and nothing else.
_SCOPE_STAY_ONLY = {"flights": 0.0, "accommodation": 1.0, "meals": 0.15,
                    "activities": 0.15}
# A request about eating and doing, with no claim about the room.
_SCOPE_EXPERIENCE = {"flights": 0.0, "accommodation": 0.15, "meals": 1.0,
                     "activities": 1.0}
# Economising on the whole trip. The reduction is carried by the flight and the
# room, and meals and activities carry none of it — so the money freed lands on
# food and doing things.
#
# This is what "I can fully compromise" actually asks for. The split divides a
# FIXED total, so a downward request cannot lower the total: all it can do is move
# money between categories. Pushing every category down at once therefore changes
# almost nothing, which is what the first version of this did. Pushing the room
# and the flight down moves real money to the part of the trip the traveller was
# willing to keep.
_SCOPE_ECONOMISE = {"flights": 0.8, "accommodation": 1.0, "meals": 0.0,
                    "activities": 0.0}

# Words that set the DIRECTION, strongest first so "not luxury" style phrasing
# cannot match the wrong end. Each maps to how far up or down the standard moves.
_DIRECTION_WORDS = (
    (0.9, ("ultra luxury", "5 star", "five star", "five-star", "no expense",
           "money no object", "best possible", "top end", "top-end")),
    (0.65, ("luxury", "luxurious", "premium", "high end", "high-end", "upscale",
            "lavish", "splurge", "treat", "indulgent", "4 star", "four star")),
    # A mild upgrade: the traveller asked for something better than the floor,
    # without asking for luxury.
    (0.25, ("comfortable", "nice", "decent", "good")),
    # Explicitly neutral. "Moderate" is this system's default answer to the style
    # question, so it must mean "no preference stated" and leave the split exactly
    # where the budget and the trip's shape put it. Reading it as a mild upgrade
    # silently biased every default trip toward a better room.
    (0.0, ("moderate", "standard", "average", "mid range", "mid-range", "normal",
           "no preference", "either", "any")),
    (-0.9, ("shoestring", "as cheap as possible", "cheapest possible",
            "fully compromise", "compromise fully", "bare minimum",
            "rock bottom", "hostel")),
    (-0.65, ("budget", "backpacker", "cheap", "economy", "frugal", "thrifty",
             "compromise", "save money", "spend less", "low cost", "low-cost")),
)

# Words that narrow the SCOPE to part of the trip.
_STAY_WORDS = ("stay", "hotel", "room", "accommodation", "resort", "lodging",
               "sleep", "suite")
_EXPERIENCE_WORDS = ("food", "eat", "eating", "dining", "restaurant", "meal",
                     "experience", "activities", "activity", "tours", "doing",
                     "attractions")
_WHOLE_TRIP_WORDS = ("trip", "everything", "throughout", "whole", "all of it",
                     "overall", "holiday", "vacation", "travel")


def parse_style(travel_style: str) -> StyleIntent:
    """
    Read the traveller's own phrasing into a direction and a scope.

    This replaced two separate implementations that had drifted apart: the
    cost-derived path recognised one list of words and the fallback path another,
    each with its own hardcoded adjustments, so "five star" worked on a listed
    destination and did nothing on an unlisted one. Both now come through here.

    It reads the words rather than matching an enum, because that is what a
    traveller types. "I want a luxury stay" is a request about the room. "Luxury
    trip" is a request about all of it. "I can fully compromise" is a request to
    spend as little as possible. Those used to be the same input.

    An empty or unrecognised description returns level 0, which leaves the split
    exactly where the budget and the trip's shape put it — the honest answer when
    nothing was asked for.
    """
    text = (travel_style or "").strip().lower()
    if not text:
        return StyleIntent(0.0, _SCOPE_WHOLE_TRIP, "no style stated")

    level = 0.0
    matched = ""
    for strength, words in _DIRECTION_WORDS:
        hit = next((w for w in words if w in text), None)
        if hit:
            level, matched = strength, hit
            break

    if not matched:
        return StyleIntent(0.0, _SCOPE_WHOLE_TRIP, "no clear preference")
    if level == 0.0:
        return StyleIntent(0.0, _SCOPE_WHOLE_TRIP, f"{matched} — no preference stated")

    # Scope: what was the request actually about? A phrase naming the whole trip
    # wins over one naming the room, because "luxury trip including the hotel"
    # mentions both and means the trip.
    if any(w in text for w in _WHOLE_TRIP_WORDS):
        scope = _SCOPE_WHOLE_TRIP if level > 0 else _SCOPE_ECONOMISE
        where, whole = "the whole trip", True
    elif any(w in text for w in _STAY_WORDS):
        scope, where, whole = _SCOPE_STAY_ONLY, "the stay", False
    elif any(w in text for w in _EXPERIENCE_WORDS):
        scope, where, whole = _SCOPE_EXPERIENCE, "food and activities", False
    else:
        scope = _SCOPE_WHOLE_TRIP if level > 0 else _SCOPE_ECONOMISE
        where, whole = "the whole trip", True

    direction = "upgrade" if level > 0 else "economise"
    return StyleIntent(level, scope, f"{matched} — {direction} {where}", whole)


# How much the stated travel style moves each category.
#
# Style is about the standard of the trip, not the distance flown. Someone asking
# for a luxury stay wants a better room and better meals; they still have to cover
# the same miles, and the airfare does not become optional because they said
# "luxury". Applying one bias to all four categories equally — which is what this
# did — moved everything together and so barely changed the RATIOS between them:
# on a $2,000 Istanbul trip, "budget" and "luxury" differed by 1.3 percentage
# points on accommodation, which is not a difference anyone would notice.
#
# Weighting the categories separately is what makes the style request visible.
# Accommodation carries it fully, because that is what "luxury stay" means. Meals
# and activities carry most of it. Flights carry none: the bracket the budget can
# afford already decides those.
_STYLE_WEIGHT: Dict[str, float] = {
    "flights": 0.0,
    "accommodation": 1.0,
    "meals": 0.7,
    "activities": 0.7,
}


def _tier_for_budget(estimate, total_budget: float, travel_style: str):
    """
    Locate the budget between the costed standards and blend the two either side.

    Returns (position, (low_tier, high_tier), label) where position is 0..1
    between the two named tiers, so the resulting shares move smoothly with the
    budget instead of jumping between three fixed ratios.

    The position returned is the one the BUDGET justifies, with no style bias in
    it. The stated style is applied per category by the caller, weighted by
    _STYLE_WEIGHT, because a style request means different things to a hotel line
    and to an airfare line.
    """
    budget = float(total_budget or 0)
    style = (travel_style or "moderate").strip().lower()

    # With no budget stated, fall back to the named style.
    if budget <= 0:
        if style in ("luxury", "premium", "high-end"):
            return 1.0, ("comfortable", "luxury"), "luxury"
        if style in ("budget", "backpacker", "cheap", "economy"):
            return 0.0, ("minimum", "comfortable"), "bare-bones"
        return 1.0, ("minimum", "comfortable"), "comfortable"

    # The budget sets the bracket; the stated style still shifts position inside
    # it. Two people with the same money who describe themselves as "luxury" and
    # "budget" genuinely do want different splits — the first toward nicer
    # rooms, the second toward cheaper stays and more doing.
    bias = 0.0   # style is applied per category by the caller, not here

    def clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    if budget <= estimate.minimum:
        return clamp(bias), ("minimum", "comfortable"), "bare-bones"
    if budget <= estimate.comfortable:
        span = max(1.0, estimate.comfortable - estimate.minimum)
        position = clamp((budget - estimate.minimum) / span + bias)
        return position, ("minimum", "comfortable"), (
            "modest" if position < 0.5 else "comfortable")
    if budget <= estimate.luxury:
        span = max(1.0, estimate.luxury - estimate.comfortable)
        position = clamp((budget - estimate.comfortable) / span + bias)
        return position, ("comfortable", "luxury"), (
            "comfortable" if position < 0.5 else "high-end")
    return 1.0, ("comfortable", "luxury"), "luxury"


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

    Prefers a split derived from the trip's real cost structure. Falls back to
    the adjustment rules below only when the destination is unknown, since
    those rules cannot be checked against anything.
    """
    derived = _cost_derived_shares(
        destination, trip_duration, num_travelers, travel_style, total_budget)
    if derived is not None:
        shares, reason = derived
        allocation = Allocation(
            shares=shares,
            amounts={c: round(total_budget * s, 2) for c, s in shares.items()},
            total_budget=float(total_budget),
            reasons=[reason],
            source="suggested",
        )
        allocation.warnings = check_realism(
            allocation, trip_duration, num_travelers, _haul(origin, destination)
        )
        return allocation

    shares = dict(BASE_ALLOCATION)
    reasons: List[str] = [
        f"'{destination}' is not a destination with known price data, so this "
        f"uses published average travel-spending shares adjusted for your trip."
    ] if destination else []

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
    # Through the same parser the cost-derived path uses. This block used to hold
    # its own adjustments and its own shorter list of words, so "five star" was
    # understood for a listed destination and ignored for an unlisted one.
    intent = parse_style(travel_style)
    if intent.level:
        moved = []
        for category in ("accommodation", "meals", "activities"):
            shift = 0.09 * intent.level * intent.weight(category)
            if shift:
                shares[category] += shift
                moved.append(category)
        if moved:
            direction = "more" if intent.level > 0 else "less"
            reasons.append(
                f"You asked for '{travel_style.strip()}' ({intent.label}), so "
                f"{direction} of the budget goes to "
                f"{', '.join(m.replace('accommodation', 'the stay') for m in moved)}.")

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
