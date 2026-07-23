## Objective
- Remove dead API code; switch to a zero-cost, reliable free-tier architecture by replacing LLM-driven search agents with direct Python API calls

## Important Details
- Repository: `https://github.com/sherali143/Trip-Planner.git`, branch `sherali-dev`
- Dead APIs removed: Kiwi.com, Booking.com Flights (both broken/unreachable)
- Live APIs: Fly-scraper (flights), Booking.com (hotels), Serper (web search)
- Fly-scraper endpoint: `/flights/search-roundtrip` with `originSkyId`, `destinationSkyId`, `outbound_date`, `return_date`
- Flight search code path: `_call_fly_scraper_api()` in `src/tools/mcp_tools.py`
- **LLM provider:** Groq (via LiteLLM model string `groq/llama-3.3-70b-versatile`, 12K TPM) — higher limit accommodates long itinerary output from coordinator
- CrewAI's `ChatGoogleGenerativeAI` object cannot be converted to LiteLLM string; pass plain LiteLLM model string instead
- `.env`: uses `GROQ_API_KEY` and `GEMINI_MODEL=groq/llama-3.1-8b-instant`
- `load_dotenv(override=True)` in `run_cli.py` and `orchestrator.py` prevents stale env vars

## Architecture
- **Phase 1:** Conversational agent gathers trip preferences (1 Crew with 1 agent)
- **Phase 2:** Preferences extractor parses conversation into structured JSON (1 Crew with 1 agent)
- **Phase 3:** Direct Python API calls fetch real data — no LLM calls, no CrewAI agents (zero rate limit impact)
- **Phase 4:** Coordinator agent assembles itinerary from real data (1 Crew with 1 agent)
- **Total: ~3 LLM calls per trip** (vs ~13 before)

## Work State
### Completed (this session)
- Rewrote `orchestrator.py::plan_trip()` — replaces CrewAI search agents with direct calls to `_call_fly_scraper_api()`, `search_hotels_comprehensive()`, `search_attractions()`, `search_restaurants()`; feeds results as strings to coordinator
- Rewrote `orchestrator.py::plan_trip_from_transcript()` — same pattern for Streamlit UI
- Removed `_run_search_crew_parallel()` from orchestrator (dead code)
- Removed `self.flight_agent`, `self.hotel_agent`, `self.attraction_agent` from orchestrator `__init__`
- Cleaned imports: removed `ThreadPoolExecutor`, `as_completed`, `Tuple`, `Any` from orchestrator
- Cleaned `src/comms/registry.py` — removed `FLIGHT_SEARCH_AGENT_CARD`, `HOTEL_AGENT_CARD`, `ATTRACTION_AGENT_CARD` and their `AgentCapability` enum values; updated `can_send_to`/`can_receive_from` references; trimmed `AGENT_REGISTRY` to only 3 agents
- All 36 source files compile cleanly (verified via AST parse + module import)

### Previously Completed
- Removed `_call_kiwi_api_direct()` from `src/tools/mcp_tools.py`
- Removed `search_flights_kiwi()`, `search_cheap_flights()`, `search_flight_destination()`, `search_booking_flights()`, `search_flights_comprehensive_booking()` from `src/server/mcp_server.py`
- Removed `FLY_SCRAPER_HOST`, `KIWI_HOST` constants from `mcp_server.py`
- Added new unified `search_flights` MCP tool pointing to fly-scraper API
- Rewrote `src/agents.py` — removed flight_search_agent, hotel_agent, attraction_agent
- Rewrote `src/tasks.py` — removed flight_search_task, hotel_search_task, attraction_search_task methods; updated `coordination_task()` to accept raw data strings
- Updated all test files (`test_flight_tools.py`, `test_mcp_servers.py`, `test_mcp_integration.py`, `test_direct_flight.py`) to remove dead API references

## Relevant Files
- `src/orchestrator.py`: Main orchestration — `plan_trip()` and `plan_trip_from_transcript()` now call APIs directly after extraction, feed results to single-agent coordinator Crew
- `src/agents.py`: Only 3 agents remain (conversational, extractor, coordinator)
- `src/tasks.py`: Only 3 tasks remain (conversation, extraction, coordination)
- `src/comms/registry.py`: Only 3 agent cards remain (conversational, extractor, coordinator)
- `src/tools/mcp_tools.py`: `_call_fly_scraper_api()` (flight), `_search_hotels_comprehensive()`, `_search_attractions()`, `_search_restaurants()` — underlying HTTP functions
- `src/server/mcp_server.py`: `search_hotels_comprehensive()`, `search_attractions()`, `search_restaurants()`, `_do_serper_search()` — API implementations
- `.env`: `GROQ_API_KEY`, `GEMINI_MODEL=groq/llama-3.1-8b-instant`, `SERPER_API_KEY`, `RAPIDAPI_KEY`
