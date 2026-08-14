# Tests

```bash
python -m pytest -q        # 137 tests, from the project root
```

No API keys required and no network access — every test here is pure logic.

## What is covered

| File | Tests | Covers |
|---|---|---|
| `test_budget_allocation.py` | 40 | Scenario-aware budget splits; parsing whatever the user types |
| `test_trip_cost.py` | 36 | Cost estimation, feasibility verdicts, edge cases |
| `test_calculator.py` | 26 | The safe AST calculator, including rejection of malicious input |
| `test_itinerary_validator.py` | 20 | Day-count validation on generated itineraries |
| `test_budget_validation.py` | 16 | Budget parsing and breakdown |

## What is deliberately not here

**Anything that calls a live API.** The flight and hotel free tiers are 30 and
50 requests *per month*; a test suite that spent them would make the evaluation
impossible to run. The API layer is exercised through recorded responses in
`.api_cache/` instead.

**Assertion-free scripts.** A set of probe scripts used to live under
`testing/manual/`. Between them they contributed six "passing" tests and zero
assertions — every check was a `print`, and every failure path caught its own
exception and printed a red cross, so they reported success no matter what
happened. They were removed rather than repaired: a test that cannot fail is
worse than no test, because it reports confidence it has not earned.

## Convention

Every test asserts. If you find yourself writing a `print` to check something,
that belongs in a script, not in here.
