"""
WHAT THIS FILE DOES
===================
Finds what a trip's parts REALLY cost, so the budget check can stop guessing.

The problem it solves
---------------------
The feasibility check estimates from a table of about forty cities. Anything
unlisted falls to the middle row — medium distance, moderate prices — and that is
optimistic for anywhere expensive or far: "Kyoto" was costed at $614 for five
nights where the truth is nearer $987. The table also carries a measured error
where it can be checked at all: for Lahore-Istanbul it says a medium-haul flight
starts at $350, and the cheapest fare the API actually returned was $734.

So the estimate is only as good as constants somebody typed.

Where the real numbers come from
--------------------------------
Two places, cheapest first:

  1. THE RECORDED CACHE. Every API response this project has ever received is
     saved under .api_cache/ and committed. Reading a fare out of it costs
     nothing, needs no key, and is a price a real API really quoted. For any
     route already recorded, this is strictly better than the table.

  2. A LIVE CALL, and only when explicitly asked for. This costs quota from an
     allowance of thirty flight searches a month, so it is never the default:
     spending a month's quota to discover a budget was impossible would be a poor
     trade, and the point of the free check is that a refusal costs nothing.

What this deliberately does NOT do
----------------------------------
It does not replace the table. `assess_budget` still estimates exactly as before
unless a caller passes a probe, because the twenty-scenario budget-gate
evaluation and its Cohen's kappa of 0.643 are published against the table, and
changing the default would mean those figures no longer describe the code. The
live product path passes a probe; the experiment does not.

Every figure this returns carries where it came from, so a verdict can say
"measured" or "estimated" rather than presenting both as the same kind of answer.

FLIGHTS ONLY
------------
There was a hotel equivalent here and it is gone. It read for keys the recorded
Booking.com replies do not contain, so it returned None for every destination
ever asked about — a function that quietly always fails is worse than no function,
because the calling code reads as though the capability exists.

Reinstating it is real work rather than a regex fix: the replies carry `grossPrice`
for the whole stay, so a per-night figure needs the stay length from the request
that produced each recording. Worth doing, and honest to leave undone in the
meantime, because the flight constant is the one shown to be wrong — 52% below a
real fare — and the hotel constant has not been contradicted by anything measured.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT, ".api_cache")


@dataclass
class RealPrice:
    """One price that an API actually quoted, and where it came from."""

    amount: float
    source: str            # "recorded" | "live"
    detail: str            # human-readable provenance
    samples: int = 1

    def describe(self) -> str:
        return f"${self.amount:,.0f} ({self.detail})"


def _airport_codes(text: str) -> List[str]:
    """Three- and four-letter codes appearing in a string, upper-cased."""
    return re.findall(r"\b[A-Z]{3,4}\b", (text or "").upper())


def _as_code(place: str) -> str:
    """
    Turn whatever the caller has into the code the recordings were made with.

    The app passes city names — the traveller typed "Istanbul", not "IST" — while
    the recordings are keyed by the code the request carried. Without this the
    probe finds nothing, because a city name holds no airport code.

    LOOKS UP THE TABLE ONLY, and never calls _resolve_sky_id. That function is the
    right one for making a request, because it falls back to asking Booking.com
    when a city is not in its table — and that fallback is a live call. Using it
    here made a supposedly free lookup spend a hotel request: resolving "Toronto"
    to check a fare cost one of fifty monthly searches, and it did so from the
    function whose entire purpose is to read prices without spending anything.

    An unresolvable name returns "" and the caller falls back to the price table,
    which is the correct outcome: no data, so say so rather than buy some.
    """
    text = (place or "").strip()
    if not text:
        return ""
    upper = text.upper()
    # Already a code.
    if 3 <= len(text) <= 4 and text.isalpha() and text.isupper():
        return upper
    try:
        from trip_planner.tools.travel_apis import CITY_TO_SKYID
    except Exception:                      # noqa: BLE001
        return ""
    lowered = text.lower()
    if lowered in CITY_TO_SKYID:
        return CITY_TO_SKYID[lowered].upper()
    for city, code in CITY_TO_SKYID.items():
        if city in lowered or lowered in city:
            return code.upper()
    return ""


def _fares_in(body: str) -> List[float]:
    """
    Every fare in a recorded flight response, read from the formatted field.

    The provider reports prices twice: as an integer in milli-units
    ("amount": "1074000") and as text ("formatted": "$1,074"). The formatted field
    is the one to read — a regex over the numeric one picks up milli-values, unit
    codes and identifiers, and a first draft of this returned nothing at all
    because it filtered 1,074,000 out as implausible.

    This mirrors the extraction the budget-gate experiment already uses, so the
    two cannot disagree about what the recordings say.
    """
    if "itineraries" not in body:
        return []
    try:
        payload = json.loads(body).get("data") or {}
    except json.JSONDecodeError:
        return []

    fares: List[float] = []
    for itinerary in payload.get("itineraries") or []:
        raw = ((itinerary.get("price") or {}).get("formatted") or "").replace(",", "")
        match = re.search(r"([\d.]+)", raw)
        if match:
            try:
                fares.append(float(match.group(1)))
            except ValueError:
                continue
    return fares


def recorded_flight_price(origin: str, destination: str) -> Optional[RealPrice]:
    """
    The cheapest recorded fare for this route, PER PERSON, or None if unrecorded.

    Per person matters. The provider quotes a total for however many passengers
    the search asked about, and the cost model multiplies its flight figure by the
    number of travellers. Returning the total made that a double count: the
    recorded London search was for two adults at $2,520, which the model then
    doubled to $5,040 and used to refuse a $3,000 trip that the real fare left
    $480 of room in. So each recording is divided by the passenger count it was
    made with.

    Linking a fare to a route takes two steps, because the provider searches in
    two phases. The first call carries the airport codes and the passenger count
    and returns a sessionId with no fares; the fares arrive in a second call keyed
    only by that session. So the session is what carries both facts forward.

    Two shortcuts were tried first and both were wrong. Matching only the request
    parameters found no fares at all, because the recording that holds them is
    keyed by session. Matching airport codes anywhere in the body then matched
    everything, because a 2.3 MB reply listing connections mentions dozens of
    airports — ISB-DOH was reported as $734, which is the Lahore-Istanbul fare.

    A route with no recording returns None. Using another route's fare would be
    worse than admitting there is no data, which is the whole point of this module.
    """
    if not os.path.isdir(CACHE_DIR):
        return None

    wanted = {code for code in (_as_code(origin), _as_code(destination))
              if code and code.isalpha() and 3 <= len(code) <= 4}
    if len(wanted) < 2:
        return None

    entries = []
    for name in sorted(os.listdir(CACHE_DIR)):
        if not name.startswith("fly-scraper") or not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(CACHE_DIR, name), encoding="utf-8") as fh:
                entries.append(json.load(fh))
        except (OSError, json.JSONDecodeError):
            continue

    def route_of(entry) -> set:
        params = entry.get("params") or {}
        codes = set()
        for key in ("originSkyId", "destinationSkyId", "fromEntityId", "toEntityId"):
            codes.update(_airport_codes(str(params.get(key, ""))))
        return codes

    def adults_of(entry) -> int:
        try:
            return max(1, int((entry.get("params") or {}).get("adults", 1) or 1))
        except (TypeError, ValueError):
            return 1

    # Sessions opened for this route, and how many passengers each was for, taken
    # from the replies to its own requests.
    session_adults = {}
    for entry in entries:
        if wanted.issubset(route_of(entry)):
            for session in re.findall(r'"sessionId"\s*:\s*"([^"]{10,})"',
                                      entry.get("body") or ""):
                session_adults[session] = adults_of(entry)

    per_person: List[float] = []
    for entry in entries:
        params = entry.get("params") or {}
        session = str(params.get("sessionId", ""))
        if wanted.issubset(route_of(entry)):
            heads = adults_of(entry)
        elif session and session in session_adults:
            heads = session_adults[session]
        else:
            continue
        per_person.extend(fare / heads for fare in _fares_in(entry.get("body") or ""))

    if not per_person:
        return None
    heads_seen = sorted(set(session_adults.values())) or [1]
    return RealPrice(
        amount=min(per_person), source="recorded", samples=len(per_person),
        detail=f"cheapest of {len(per_person)} fares the flight API really "
               f"returned for this route, per person, from the recorded responses"
               f" (searched for {'/'.join(str(h) for h in heads_seen)} passenger(s))")


def live_flight_price(origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None,
                      adults: int = 1) -> Optional[RealPrice]:
    """
    Ask the flight API what this route really costs, right now.

    This SPENDS QUOTA — one search from an allowance of thirty a month — which is
    why nothing calls it unless the destination has no price data at all. For a
    city the table knows, guessing is not the problem and a purchase is not the
    answer.

    The call goes through the recording layer, so the reply is saved. The next
    check for the same route is free and reads it back. In other words asking once
    calibrates the model for that route permanently, which is the whole reason this
    is worth the request.

    Returns None rather than a fallback on any failure — no dates, no key, the
    quota guard tripping, an empty result. The caller then knows it has no real
    price and can say so, which is better than a number nobody can account for.
    """
    if not departure_date:
        logger.info("no departure date, so no live price check")
        return None
    try:
        from trip_planner.tools.travel_apis import _call_fly_scraper_api
        raw = _call_fly_scraper_api(origin, destination, departure_date,
                                    return_date, adults, None)
    except Exception as exc:              # noqa: BLE001 - quota guard, network, key
        logger.warning("live price check failed: %s", exc)
        return None

    fares = _fares_in(raw or "")
    if not fares:
        logger.info("live price check returned no fares for %s-%s",
                    origin, destination)
        return None
    return RealPrice(
        amount=min(fares), source="live", samples=len(fares),
        detail=f"cheapest of {len(fares)} fares the flight API returned when "
               f"asked just now for this route on {departure_date}")


@dataclass
class PriceProbe:
    """
    Real prices for a route: from the recordings first, and only then by asking.

    Reading a recording costs nothing, so that is always tried. `allow_live` opens
    the second door, and it is off by default because a live search spends one of
    thirty monthly flight requests — including on a check that ends in a refusal.

    The intended use is narrow: turn it on when the destination is not in the
    price table, because that is the case where the alternative is a mid-tier
    default nobody can account for. For a city the table knows, the estimate is
    already grounded and a purchase buys nothing.
    """

    allow_live: bool = False
    departure_date: str = ""
    return_date: str = ""
    adults: int = 1

    def flight(self, origin: str, destination: str) -> Optional[RealPrice]:
        recorded = recorded_flight_price(origin, destination)
        if recorded is not None:
            return recorded
        if not self.allow_live:
            return None
        return live_flight_price(origin, destination, self.departure_date,
                                 self.return_date or None, self.adults)

