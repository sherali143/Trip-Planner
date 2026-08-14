# Application code

The production system: takes a plain-English travel request and returns a
day-by-day itinerary built from live flight, hotel and attraction data.

## Layout

| Path | Responsibility |
|---|---|
| `orchestrator.py` | The workflow. Conversation → extraction → retrieval → assembly. |
| `agents.py` | The three agents that need an LLM, and why each one does. |
| `tasks.py` | Task definitions and prompts for those agents. |
| `comms/` | A2A protocol — typed messages, agent cards, permission validation. |
| `server/mcp_server.py` | MCP server: 12 schema-validated tools over JSON-RPC/stdio. |
| `tools/mcp_tools.py` | CrewAI tool wrappers plus the direct HTTP calls. |
| `core/` | Infrastructure — see below. |
| `ui/app.py` | Streamlit interface. |

## `core/` — the infrastructure

| Module | What it solves |
|---|---|
| `http_cache.py` | Record/replay for every HTTP call, plus a hard live-call ceiling. Makes the evaluation reproducible without API keys and stops one run draining a monthly allowance. |
| `llm_metrics.py` | Counts real LLM requests, tokens and cost from LiteLLM callbacks. Never hand-count — ReAct loops issue far more requests than there are tasks. |
| `resilience.py` | Decides whether a provider refusal is worth retrying. A spending cap and a per-minute limit look identical; treating them alike is expensive either way. |
| `budget.py` | Derives a budget split from what the trip's parts actually cost, and honours whatever split the user gives instead. |
| `trip_cost.py` | Estimates what a trip costs at minimum, comfortable and luxury standards, and refuses budgets below the true floor. |
| `validators.py` | Checks the generated itinerary actually contains every day it should. |
| `log_setup.py` | Keeps the Gemini API key out of the console — it travels as a URL parameter, which httpx logs at INFO. |

## Three things that will bite you

**CrewAI `@tool` produces `Tool` objects, not functions.** Call `.run(...)`, not
`f(...)`. Runtime code imports the plain functions from `server/mcp_server.py`
instead; the wrappers in `tools/` exist for agents to hold.

**The MCP server runs as a subprocess.** It bootstraps `sys.path` before
importing anything under `src.`, because the project root is not on the path
when Python launches it directly. Without that, every tool call fails as
"Connection lost" — and it fails *silently*, so the agents simply produce
itineraries from model knowledge instead of API data.

**fly-scraper is a two-phase API.** The search endpoint only starts a search and
returns a `sessionId`; results come from `/v2/flights/search-incomplete`. Its
date parameters are camelCase (`departureDate`), and the snake_case forms are
accepted with HTTP 200 and then ignored — wrong dates, no error.

## The design argument this code exists to make

The A2A protocol and MCP server are identical across all four evaluated
architectures. Only the retrieval layer differs. That is the point: the protocol
design is independent of whether an LLM or plain Python does the fetching, and
the measurements show the LLM adds cost there without adding judgement.
