# Tests

```bash
python -m pytest -q        # 393 tests, from the project root
```

No API keys required and no network access — every test here is pure logic.

## What is covered

| File | Tests | Covers |
|---|---|---|
| `test_calculator.py` | 46 | The safe AST calculator, including rejection of malicious input |
| `test_budget_allocation.py` | 44 | Scenario-aware budget splits; parsing whatever the user types |
| `test_trip_cost.py` | 35 | Cost estimation, feasibility verdicts, edge cases |
| `test_itinerary_validator.py` | 20 | Day-count validation on generated itineraries |
| `test_style_shifts_allocation.py` | 33 | That a stated travel style visibly moves the split. One bias applied to all four categories left "budget" and "luxury" 1.3 points apart on accommodation. |
| `test_real_price_validation.py` | 34 | That the budget check can use a fare the API really quoted instead of a constant, says which it used, and that the DEFAULT stays the table — the published Cohen's kappa depends on it. |
| `test_unpriced_destination.py` | 36 | That an estimate built on mid-tier defaults says so. An unlisted destination used to produce a figure indistinguishable from a priced one. |
| `test_a2a_protocol.py` | 19 | Message serialisation, dispatch and permission refusal. Covers the slice of the protocol library the shipped path records but never dispatches. |
| `test_documentation_accuracy.py` | 22 | That the READMEs still tell the truth about the code, and that no function, duplicated body or assigned-but-unread attribute survives unused. The dead-code scans were run by hand until they became tests. |
| `test_run_narration.py` | 16 | That the line each step prints says what happened. A failed hotel search returns an explanation as an ordinary string, and was being reported as "returned 371 chars" — a step that looked like it worked. |
| `test_web_interface.py` | 61 | That the page renders, asks how many people are travelling, and refuses a form it cannot plan. Nothing tested the page at all, which is how it came to collect eight facts without ever asking the traveller count — a number the feasibility check multiplies by. |
| `test_budget_validation.py` | 16 | Budget parsing and breakdown |
| `test_extraction_parsing.py` | 11 | That the extractor's output stays readable to everything downstream. Written after a silent bug turned the budget feasibility check off entirely. |

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

## Why documentation is tested

`test_documentation_accuracy.py` fails when the prose and the project disagree:
a README naming a deleted file, a documented command with no target, a tool
count that no longer matches the server, or a results table that has drifted
from the measured data. Those are the first things a reader hits, and each one
costs more trust than it saves. The project document already generates its
numbers from the results file; this is what protects the hand-written ones.
