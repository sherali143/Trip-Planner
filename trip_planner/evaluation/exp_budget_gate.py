"""
Checks the budget feasibility rules against all twenty scenarios.

Compares what the system decides with a hand-labelled answer for each
scenario, and reports the agreement as Cohen's kappa. Needs no network and no
model.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from trip_planner.evaluation.scenarios import SCENARIOS
from trip_planner.core.trip_cost import (assess_budget, estimate_trip_cost,
                                is_known_destination)

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results", "budget_gate.json")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".api_cache")


# --------------------------------------------------------------- T1
def decision_table() -> List[Dict[str, Any]]:
    """The gate's verdict on every scenario, against the designed intent."""
    rows = []
    for entry in SCENARIOS:
        p = entry["params"]
        # The gate is destination-based; for a multi-city trip the priced
        # destination is the first leg, which is also where the flight lands.
        destination = p["legs"][0][0]
        travellers = p["adults"] + p["children"]
        verdict = assess_budget(
            total_budget=p["budget"], destination=destination,
            nights=p["nights"], travelers=travellers, origin=p["origin"],
        )
        expected_infeasible = bool(p.get("expect_infeasible"))
        rows.append({
            "scenario": entry["id"],
            "destination": destination,
            "multi_city": len(p["legs"]) > 1,
            "budget": p["budget"],
            "nights": p["nights"],
            "travellers": travellers,
            "estimate_minimum": verdict.estimate.minimum,
            "estimate_comfortable": verdict.estimate.comfortable,
            "budget_vs_minimum": round(p["budget"] / verdict.estimate.minimum, 2),
            "verdict": verdict.verdict,
            "gate_refused": not verdict.feasible,
            "designed_infeasible": expected_infeasible,
            "agrees": (not verdict.feasible) == expected_infeasible,
            "destination_priced_from_data": is_known_destination(destination),
            "haul": verdict.estimate.haul,
            "price_tier": verdict.estimate.price_tier,
        })
    return rows


def _kappa(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Cohen's kappa between the gate's refusals and the designed intent.

    Reported instead of accuracy because the classes are heavily unbalanced
    (2 infeasible of 20): a gate that refused nothing at all would still score
    90% accuracy, so accuracy cannot distinguish a working gate from a dead one.
    """
    tp = sum(1 for r in rows if r["gate_refused"] and r["designed_infeasible"])
    tn = sum(1 for r in rows if not r["gate_refused"] and not r["designed_infeasible"])
    fp = sum(1 for r in rows if r["gate_refused"] and not r["designed_infeasible"])
    fn = sum(1 for r in rows if not r["gate_refused"] and r["designed_infeasible"])
    n = tp + tn + fp + fn
    observed = (tp + tn) / n
    p_yes = ((tp + fp) / n) * ((tp + fn) / n)
    p_no = ((tn + fn) / n) * ((tn + fp) / n)
    expected = p_yes + p_no
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return {
        "true_positive": tp, "true_negative": tn,
        "false_positive": fp, "false_negative": fn,
        "n": n,
        "observed_agreement": round(observed, 3),
        "chance_agreement": round(expected, 3),
        "cohens_kappa": round(kappa, 3),
        "accuracy_pct": round(observed * 100, 1),
        "precision": round(tp / (tp + fp), 3) if (tp + fp) else None,
        "recall": round(tp / (tp + fn), 3) if (tp + fn) else None,
    }


# --------------------------------------------------------------- T2
def _recorded_fares(origin: str, destination: str) -> List[float]:
    """
    Per-person fares the API really returned FOR THIS ROUTE, cheapest first.

    This function used to read every fly-scraper recording and pool the fares out
    of all of them, then external_validity() labelled the result with SC-01's
    route. That was right only while the cache held one route. It holds three, and
    the day the London recordings were committed the median jumped from $1,053 to
    $1,285 and the reported anchor error with it — a published figure moving
    because unrelated data had been added.

    It now calls the same route-matching reader the product uses, so the two
    cannot disagree about what the recordings say.
    """
    from trip_planner.core.real_prices import recorded_flight_fares

    return sorted(set(recorded_flight_fares(origin, destination)))


def external_validity() -> Dict[str, Any]:
    """Compare the gate's flight anchor against fares actually quoted by the API."""
    sc01 = next(s for s in SCENARIOS if s["id"] == "SC-01")["params"]
    fares = _recorded_fares(sc01["origin"], sc01["legs"][0][0])
    estimate = estimate_trip_cost(sc01["legs"][0][0], sc01["nights"], sc01["adults"])
    est_min = estimate.breakdown["flights"]["minimum"]
    est_typical = estimate.breakdown["flights"]["comfortable"]

    if not fares:
        return {"comparable": False,
                "reason": "no recorded flight response with itineraries in .api_cache"}

    cheapest, median = fares[0], fares[len(fares) // 2]
    return {
        "comparable": True,
        "route": f"{sc01['origin']} to {sc01['legs'][0][0]}",
        "fares_recorded": len(fares),
        "cheapest_real_fare": cheapest,
        "median_real_fare": median,
        "estimated_minimum": est_min,
        "estimated_typical": est_typical,
        # The interesting quantity: does the "cheapest bookable" anchor sit at
        # or below the cheapest fare that was really on offer? If it sits above,
        # the gate refuses trips that are in fact bookable; if far below, it
        # accepts trips it should refuse.
        "minimum_anchor_error_pct": round((est_min - cheapest) / cheapest * 100, 1),
        "typical_anchor_error_pct": round((est_typical - median) / median * 100, 1),
        "anchor_below_cheapest_real_fare": est_min <= cheapest,
    }


# --------------------------------------------------------------- T3
def monotonicity() -> Dict[str, Any]:
    """Properties any correct cost model must have, regardless of calibration."""
    violations: List[str] = []
    destinations = ["Istanbul", "London", "Bangkok", "Dubai", "Tokyo", "Nowhereville"]

    for dest in destinations:
        # Cost must not fall as nights rise.
        previous = None
        for nights in range(1, 15):
            current = estimate_trip_cost(dest, nights, 1).minimum
            if previous is not None and current < previous:
                violations.append(f"{dest}: minimum fell from {previous} to {current} "
                                  f"between {nights - 1} and {nights} nights")
            previous = current
        # Cost must not fall as travellers rise.
        previous = None
        for travellers in range(1, 7):
            current = estimate_trip_cost(dest, 5, travellers).minimum
            if previous is not None and current < previous:
                violations.append(f"{dest}: minimum fell from {previous} to {current} "
                                  f"between {travellers - 1} and {travellers} travellers")
            previous = current
        # A budget accepted for n nights must still be accepted for fewer.
        for nights in range(2, 15):
            budget = estimate_trip_cost(dest, nights, 1).minimum
            if not assess_budget(budget, dest, nights - 1, 1).feasible:
                violations.append(f"{dest}: budget {budget:.0f} accepted at {nights} "
                                  f"nights but refused at {nights - 1}")
    return {
        "destinations_tested": destinations,
        "checks_run": len(destinations) * (14 + 6 + 13),
        "violations": violations,
        "passed": not violations,
    }


def run() -> Dict[str, Any]:
    rows = decision_table()
    payload = {
        "experiment": "budget_gate",
        "cost": {"llm_requests": 0, "live_api_calls": 0, "usd": 0.0},
        "scenarios_evaluated": len(rows),
        "decision_table": rows,
        "agreement": _kappa(rows),
        "external_validity": external_validity(),
        "monotonicity": monotonicity(),
        "coverage": {
            "destinations_priced_from_data": sum(
                1 for r in rows if r["destination_priced_from_data"]),
            "destinations_on_default_tier": sum(
                1 for r in rows if not r["destination_priced_from_data"]),
            "multi_city_scenarios_costed_on_first_leg_only": sum(
                1 for r in rows if r["multi_city"]),
        },
    }
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return payload


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = run()

    print("\n" + "=" * 96)
    print("  BUDGET FEASIBILITY GATE — all 20 scenarios, no LLM, no API calls")
    print("=" * 96)
    head = (f"  {'ID':<7}{'destination':<14}{'budget':>7}{'nts':>4}{'pax':>4}"
            f"{'minimum':>9}{'comfort':>9}{'b/min':>7}  {'verdict':<12}"
            f"{'refused':>8}{'agrees':>7}  {'priced':<7}")
    print(head)
    print("  " + "-" * (len(head) - 2))
    for r in p["decision_table"]:
        print(f"  {r['scenario']:<7}{r['destination'][:13]:<14}{r['budget']:>7.0f}"
              f"{r['nights']:>4}{r['travellers']:>4}{r['estimate_minimum']:>9,.0f}"
              f"{r['estimate_comfortable']:>9,.0f}{r['budget_vs_minimum']:>7.2f}  "
              f"{r['verdict']:<12}{str(r['gate_refused']):>8}"
              f"{('yes' if r['agrees'] else 'NO'):>7}  "
              f"{('data' if r['destination_priced_from_data'] else 'DEFAULT'):<7}")

    a = p["agreement"]
    print("\n  Agreement with designed intent")
    print(f"    refused correctly {a['true_positive']}   accepted correctly {a['true_negative']}   "
          f"refused wrongly {a['false_positive']}   missed {a['false_negative']}")
    print(f"    accuracy {a['accuracy_pct']}%   Cohen's kappa {a['cohens_kappa']}   "
          f"(chance agreement {a['chance_agreement']})")

    e = p["external_validity"]
    print("\n  External validity of the flight anchor")
    if e.get("comparable"):
        print(f"    {e['route']}: {e['fares_recorded']} real fares recorded, "
              f"cheapest ${e['cheapest_real_fare']:,.0f}, median ${e['median_real_fare']:,.0f}")
        print(f"    model's 'cheapest bookable' anchor ${e['estimated_minimum']:,.0f} "
              f"({e['minimum_anchor_error_pct']:+.1f}% vs cheapest real fare)")
        print(f"    model's 'typical' anchor ${e['estimated_typical']:,.0f} "
              f"({e['typical_anchor_error_pct']:+.1f}% vs median real fare)")
        print(f"    anchor at or below cheapest real fare: "
              f"{e['anchor_below_cheapest_real_fare']}")
    else:
        print(f"    not comparable: {e['reason']}")

    m = p["monotonicity"]
    print(f"\n  Monotonicity: {m['checks_run']} checks, "
          f"{len(m['violations'])} violations")
    for v in m["violations"][:5]:
        print(f"    VIOLATION {v}")

    c = p["coverage"]
    print(f"\n  Coverage: {c['destinations_priced_from_data']}/20 scenarios have a "
          f"destination in the price table; {c['destinations_on_default_tier']} fall back "
          f"to mid-tier defaults")
    print(f"            {c['multi_city_scenarios_costed_on_first_leg_only']} multi-city "
          f"scenarios are costed on their first leg only")
    print(f"\n  Written to {RESULTS_PATH}")
    print("=" * 96)


if __name__ == "__main__":
    main()
