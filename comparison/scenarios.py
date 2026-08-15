"""
The twenty evaluation scenarios.

Chosen to span the axes that change an itinerary's difficulty rather than to be
a uniform sample: trip length (3 to 14 nights), distance (short-haul Dubai to
long-haul Tokyo), party size (solo to a family of four), destination price tier,
multi-city routes, and budgets from comfortable down to deliberately impossible.

The impossible ones (SC-05, SC-19) matter: an architecture that confidently
plans a trip nobody could afford is failing, and only these scenarios expose it.

Every architecture receives the identical `input` string, so nothing in the
comparison depends on how a request was phrased.

`params` — declared ground truth
--------------------------------
Each scenario also records the facts a human reads out of the request. Nothing
in any arm reads this field: the arms see only `input`. It exists so that two
things can be measured without an LLM in the loop:

  * the budget feasibility gate can be evaluated on all twenty scenarios with
    exact parameters rather than regex guesses (comparison/exp_budget_gate.py),
  * an arm's extraction step can be scored against what the request actually
    said, instead of against another model's opinion of it.

`legs` is a list because three scenarios are multi-city; `nights` is the total
across legs, which is what a budget has to cover.
"""

SCENARIOS = [
    {
        "id": "SC-01",
        "name": "Short city break - Lahore to Istanbul",
        "input": "I want to plan a trip from Lahore to Istanbul for 4 nights, departing 2026-08-15. Budget is $800 for one person. I like history, food, and shopping.",
        "params": {
            "origin": "Lahore", "legs": [("Istanbul", 4)], "nights": 4,
            "departure_date": "2026-08-15", "budget": 800,
            "adults": 1, "children": 0,
            "interests": ["history", "food", "shopping"],
        },
    },
    {
        "id": "SC-02",
        "name": "Long-haul family trip - Lahore to Tokyo",
        "input": "Plan a trip from Lahore to Tokyo for 8 nights starting 2026-09-01. Budget is $3000 for two adults. We love technology, anime, and Japanese food.",
        "params": {
            "origin": "Lahore", "legs": [("Tokyo", 8)], "nights": 8,
            "departure_date": "2026-09-01", "budget": 3000,
            "adults": 2, "children": 0,
            "interests": ["technology", "anime", "Japanese food"],
        },
    },
    {
        "id": "SC-03",
        "name": "Beach and city combo - Bangkok + Phuket",
        "input": "I want to go from Karachi to Bangkok for 5 nights then Phuket for 5 nights, starting 2026-10-10. Budget is $2500 for one person. I like beaches, nightlife, and street food.",
        "params": {
            "origin": "Karachi", "legs": [("Bangkok", 5), ("Phuket", 5)], "nights": 10,
            "departure_date": "2026-10-10", "budget": 2500,
            "adults": 1, "children": 0,
            "interests": ["beaches", "nightlife", "street food"],
        },
    },
    {
        "id": "SC-04",
        "name": "Tight budget - Karachi to Bangkok",
        "input": "Plan a trip from Karachi to Bangkok for 5 nights, departing 2026-11-01. Budget is $700 for one person. I like temples, food, and markets.",
        "params": {
            "origin": "Karachi", "legs": [("Bangkok", 5)], "nights": 5,
            "departure_date": "2026-11-01", "budget": 700,
            "adults": 1, "children": 0,
            "interests": ["temples", "food", "markets"],
        },
    },
    {
        "id": "SC-05",
        "name": "Impossible budget - Lahore to New York",
        "input": "I need a trip from Lahore to New York for 7 nights starting 2026-12-20. Budget is $300 for one person. I like museums and landmarks.",
        "params": {
            "origin": "Lahore", "legs": [("New York", 7)], "nights": 7,
            "departure_date": "2026-12-20", "budget": 300,
            "adults": 1, "children": 0,
            "interests": ["museums", "landmarks"],
            "expect_infeasible": True,
        },
    },
    {
        "id": "SC-06",
        "name": "European cultural tour - Islamabad to London + Paris",
        "input": "Plan from Islamabad to London for 5 nights then Paris for 4 nights, starting 2026-07-05. Budget is $3500 for two adults. We love museums, art, and fine dining.",
        "params": {
            "origin": "Islamabad", "legs": [("London", 5), ("Paris", 4)], "nights": 9,
            "departure_date": "2026-07-05", "budget": 3500,
            "adults": 2, "children": 0,
            "interests": ["museums", "art", "fine dining"],
        },
    },
    {
        "id": "SC-07",
        "name": "Middle East luxury - Dubai",
        "input": "Trip from Lahore to Dubai for 5 nights starting 2026-08-01. Budget is $4000 for two adults. We want luxury shopping, fine dining, and desert safari.",
        "params": {
            "origin": "Lahore", "legs": [("Dubai", 5)], "nights": 5,
            "departure_date": "2026-08-01", "budget": 4000,
            "adults": 2, "children": 0,
            "interests": ["luxury shopping", "fine dining", "desert safari"],
        },
    },
    {
        "id": "SC-08",
        "name": "Southeast Asia backpacker - Kuala Lumpur",
        "input": "Trip from Karachi to Kuala Lumpur for 7 nights starting 2026-09-15. Budget is $900 for one person. I like street food, nature, and budget activities.",
        "params": {
            "origin": "Karachi", "legs": [("Kuala Lumpur", 7)], "nights": 7,
            "departure_date": "2026-09-15", "budget": 900,
            "adults": 1, "children": 0,
            "interests": ["street food", "nature", "budget activities"],
        },
    },
    {
        "id": "SC-09",
        "name": "South Asia religious - Lahore to Saudi Arabia",
        "input": "Plan from Lahore to Jeddah for 5 nights starting 2026-10-01. Budget is $1500 for one person. I want religious sites and modest accommodations.",
        "params": {
            "origin": "Lahore", "legs": [("Jeddah", 5)], "nights": 5,
            "departure_date": "2026-10-01", "budget": 1500,
            "adults": 1, "children": 0,
            "interests": ["religious sites", "modest accommodations"],
        },
    },
    {
        "id": "SC-10",
        "name": "Central Asia adventure - Islamabad to Istanbul",
        "input": "Trip from Islamabad to Istanbul for 6 nights starting 2026-08-20. Budget is $1200 for one person. I like history, photography, and local experiences.",
        "params": {
            "origin": "Islamabad", "legs": [("Istanbul", 6)], "nights": 6,
            "departure_date": "2026-08-20", "budget": 1200,
            "adults": 1, "children": 0,
            "interests": ["history", "photography", "local experiences"],
        },
    },
    {
        "id": "SC-11",
        "name": "East Asia cultural - Lahore to Bangkok",
        "input": "Plan a trip from Lahore to Bangkok for 6 nights starting 2026-11-10. Budget is $1500 for one person. I like temples, Thai food, and night markets.",
        "params": {
            "origin": "Lahore", "legs": [("Bangkok", 6)], "nights": 6,
            "departure_date": "2026-11-10", "budget": 1500,
            "adults": 1, "children": 0,
            "interests": ["temples", "Thai food", "night markets"],
        },
    },
    {
        "id": "SC-12",
        "name": "Family beach vacation - Dubai",
        "input": "Trip from Islamabad to Dubai for 7 nights starting 2026-12-15. Budget is $3500 for a family of 4 (2 adults, 2 children). We want beaches, theme parks, and family activities.",
        "params": {
            "origin": "Islamabad", "legs": [("Dubai", 7)], "nights": 7,
            "departure_date": "2026-12-15", "budget": 3500,
            "adults": 2, "children": 2,
            "interests": ["beaches", "theme parks", "family activities"],
        },
    },
    {
        "id": "SC-13",
        "name": "Honeymoon - Maldives",
        "input": "Plan from Lahore to Male for 5 nights starting 2027-01-10. Budget is $5000 for two adults. We want overwater villas, spa, and romantic dinners.",
        "params": {
            "origin": "Lahore", "legs": [("Male", 5)], "nights": 5,
            "departure_date": "2027-01-10", "budget": 5000,
            "adults": 2, "children": 0,
            "interests": ["overwater villas", "spa", "romantic dinners"],
        },
    },
    {
        "id": "SC-14",
        "name": "Budget group trip - Istanbul",
        "input": "Trip from Karachi to Istanbul for 6 nights starting 2026-09-20. Budget is $2000 for three adults. We like history, nightlife, and group activities.",
        "params": {
            "origin": "Karachi", "legs": [("Istanbul", 6)], "nights": 6,
            "departure_date": "2026-09-20", "budget": 2000,
            "adults": 3, "children": 0,
            "interests": ["history", "nightlife", "group activities"],
        },
    },
    {
        "id": "SC-15",
        "name": "Last minute - Lahore to Dubai",
        "input": "Need a trip from Lahore to Dubai departing 2026-08-05 for 3 nights. Budget is $1000 for one person. I want shopping and good food.",
        "params": {
            "origin": "Lahore", "legs": [("Dubai", 3)], "nights": 3,
            "departure_date": "2026-08-05", "budget": 1000,
            "adults": 1, "children": 0,
            "interests": ["shopping", "good food"],
        },
    },
    {
        "id": "SC-16",
        "name": "Long stay - Islamabad to Kuala Lumpur",
        "input": "Plan from Islamabad to Kuala Lumpur for 14 nights starting 2026-10-01. Budget is $2000 for one person. I want to experience local life, nature, and food.",
        "params": {
            "origin": "Islamabad", "legs": [("Kuala Lumpur", 14)], "nights": 14,
            "departure_date": "2026-10-01", "budget": 2000,
            "adults": 1, "children": 0,
            "interests": ["local life", "nature", "food"],
        },
    },
    {
        "id": "SC-17",
        "name": "Business trip - Lahore to London",
        "input": "Trip from Lahore to London for 4 nights starting 2026-09-05. Budget is $2500 for one person. I need a central hotel, good transport links, and fine dining options.",
        "params": {
            "origin": "Lahore", "legs": [("London", 4)], "nights": 4,
            "departure_date": "2026-09-05", "budget": 2500,
            "adults": 1, "children": 0,
            "interests": ["central hotel", "transport links", "fine dining"],
        },
    },
    {
        "id": "SC-18",
        "name": "Winter getaway - Islamabad to Thailand",
        "input": "Trip from Islamabad to Phuket for 7 nights starting 2026-12-25. Budget is $2000 for two adults. We want warm weather, beaches, and Thai massage.",
        "params": {
            "origin": "Islamabad", "legs": [("Phuket", 7)], "nights": 7,
            "departure_date": "2026-12-25", "budget": 2000,
            "adults": 2, "children": 0,
            "interests": ["warm weather", "beaches", "Thai massage"],
        },
    },
    {
        "id": "SC-19",
        "name": "Extreme budget - Karachi to Istanbul",
        "input": "Plan from Karachi to Istanbul for 5 nights starting 2026-11-15. Budget is $500 for one person. I just want to explore the city on foot.",
        "params": {
            "origin": "Karachi", "legs": [("Istanbul", 5)], "nights": 5,
            "departure_date": "2026-11-15", "budget": 500,
            "adults": 1, "children": 0,
            "interests": ["walking", "city exploration"],
            "expect_infeasible": True,
        },
    },
    {
        "id": "SC-20",
        "name": "Premium trip - Lahore to Tokyo",
        "input": "Trip from Lahore to Tokyo for 10 nights starting 2027-03-15. Budget is $8000 for two adults. We want luxury hotels, fine dining, and unique cultural experiences.",
        "params": {
            "origin": "Lahore", "legs": [("Tokyo", 10)], "nights": 10,
            "departure_date": "2027-03-15", "budget": 8000,
            "adults": 2, "children": 0,
            "interests": ["luxury hotels", "fine dining", "cultural experiences"],
        },
    },
]


def scenario(scenario_id: str) -> dict:
    """One scenario by id, or KeyError naming the ids that do exist."""
    for entry in SCENARIOS:
        if entry["id"] == scenario_id:
            return entry
    raise KeyError(f"{scenario_id!r} is not a scenario; known ids: "
                   f"{[s['id'] for s in SCENARIOS]}")
