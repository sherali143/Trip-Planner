# Manual API probe scripts

These are **not** part of the automated test suite. They are ad-hoc scripts
that print results for a human to read: none of them define `test_` functions,
several call live endpoints at import time, and `test_apis_direct.py` calls
`exit(1)` at module level — which aborted the whole pytest session with an
INTERNALERROR, so `pytest testing/` collected *zero* tests while they sat in
the test directory.

They were moved here rather than deleted because they are still useful for
poking at an API by hand.

## ⚠️ Running these costs API quota

The RapidAPI free tiers are **monthly**:

| API | Limit |
|---|---|
| fly-scraper (flights) | 30 requests/month |
| booking-com15 (hotels) | 50 requests/month |

Several of these scripts fire multiple live requests. Before running one, set a
cap so a stray script cannot drain the month:

```bash
export TRIP_PLANNER_MAX_LIVE_CALLS=3
python testing/manual/test_hotel_apis.py
```

Better still, prefer replayed data where the query is already recorded:

```bash
export TRIP_PLANNER_API_MODE=replay
```

## Known-broken scripts

Left as-is; fix if you need them, but note what is wrong:

| Script | Problem |
|---|---|
| `test_api_tools.py` | Calls CrewAI `@tool` objects directly — they are `Tool` instances, not functions. Use `.run(...)`. |
| `test_hotel_workflow.py` | Same `'Tool' object is not callable` problem. |
| `test_flight_agent.py` | Builds a CrewAI `Agent` without `llm=`, so CrewAI defaults to OpenAI and demands `OPENAI_API_KEY`. This project uses Gemini. |
| `test_mcp_integration.py` | Uses the old LangChain `.invoke(json_string)` calling convention, and checks for a server path (`mcp_servers/trip_planner_mcp_server.py`) that no longer exists. |
| `test_mcp_servers.py` | Same style — prints outcomes for a human rather than asserting them. |

`test_mcp_integration.py` and `test_mcp_servers.py` lived in `testing/` until
they were moved here. Between them they contributed six "passing" tests and
**zero assertions** — every check was a `print`, and every failure path was a
caught exception followed by a printed ❌, so the suite reported success no
matter what happened. `test_mcp_integration.py` also defines an `async def`
test, which pytest 9 fails outright rather than skipping.

## The real test suite

Lives in `testing/` and runs clean:

```bash
python -m pytest testing/ -q
```
