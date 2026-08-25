# `trip_planner/` — the system itself

Takes a plain-English travel request and returns a day-by-day itinerary built
from real flight, hotel and venue data.

This is the application. The four architectures it was compared against live in
`../trip_planner/evaluation/`, and nothing in this folder imports from there.

## The shape of a request

```
  request  →  extractor  →  retrieval  →  coordinator  →  itinerary
                (model)     (plain Python)   (model)
```

Two model steps with a retrieval phase between them that uses no model at all.
The test applied to every step was: **does this need a judgement that cannot be
written as code?** Interpreting "leaving on the fifteenth for two adults" does.
Arranging retrieved options into a sensible day-by-day plan does. Fetching a
fare for a known route on a known date does not.

## Layout

| Path | What it does |
|---|---|
| `orchestrator.py` | The workflow. Both entry points — command line and web — run through one `_plan` method. |
| `agents.py` | The three agents that need a model, and why each one does. |
| `tasks.py` | Their task definitions and prompts. |
| `comms/` | The A2A protocol: typed messages, agent cards, permission validation. |
| `server/` | The MCP server: 12 schema-validated tools over JSON-RPC and stdio. |
| `tools/` | Everything that calls an external service — see below. |
| `core/` | Infrastructure — see below. |
| `frontend/app.py` | The Streamlit web interface: one grouped form, live per-step progress, and the finished plan split into tabs. |
| `frontend/plan_layout.py` | Reads a finished plan's own section and day structure, so the page can show it in parts. No Streamlit import — it lived in `app.py`, where importing it ran the whole page. |

### `tools/` — three files, three jobs

| File | What it does |
|---|---|
| `mcp_client.py` | Speaks to the MCP server over JSON-RPC, launching it as a subprocess |
| `travel_apis.py` | Calls fly-scraper and Booking.com over HTTPS, directly |
| `agent_tools.py` | The 12 tools an agent can hold and decide to call |

These were one 986-line file mixing all three. Splitting them makes the
dependency obvious: an agent holds `agent_tools`, which reaches the outside world
through either `mcp_client` or `travel_apis`.

### `comms/` — the A2A protocol

| File | What it does |
|---|---|
| `protocol.py` | The typed message envelope and its six message types. A message carries its sender, recipient, intent and payload, so an exchange can be checked rather than assumed. |
| `registry.py` | The eight agent cards. Each declares what its agent can send and receive, which is what makes an undeclared message a detectable error instead of a silent one. |

The conformance audit (`python -m trip_planner.evaluation.exp_protocol`) tests this layer
against its own declarations and currently fails 3 of its 5 A2A checks — priority
is declared but never honoured, and inbound permissions are never enforced. Those
are reported in the dissertation rather than quietly fixed.

### `core/` — the infrastructure

| Module | What it solves |
|---|---|
| `http_cache.py` | Record/replay for every HTTP call, plus a hard live-call ceiling. Makes the evaluation reproducible without API keys and stops one run draining a monthly allowance. |
| `llm_metrics.py` | Counts real model requests, tokens and cost from provider callbacks. Never hand-count — a reasoning loop issues far more requests than there are tasks. |
| `safe_math.py` | Arithmetic for the calculator tool, without `eval`. The character-filter version it replaced blocked name lookups but not `9**9**9`. |
| `resilience.py` | Decides whether a provider refusal is worth retrying. A spending cap and a per-minute limit look identical; treating them alike is expensive either way. |
| `budget.py` | Derives a budget split from what the trip's parts actually cost, and honours whatever split the traveller gives instead. |
| `trip_cost.py` | Estimates what a trip costs at minimum, comfortable and luxury standards, and refuses budgets below the true floor. |
| `validators.py` | Checks the generated itinerary contains every day it should. |
| `log_setup.py` | Keeps the model API key out of the console — it travels as a URL parameter, which the HTTP client logs at INFO. |
| `real_prices.py` | Finds what a trip's parts REALLY cost, by reading fares out of the recorded API responses. Costs nothing and needs no key. The budget check uses it where a route was recorded and the price table only where it was not — and says which. |
| `gemini_compat.py` | Makes the agent arms runnable on current Gemini models, which reject a request whose last message is a model turn — exactly what a reasoning loop produces. Adds a short user turn to only those requests and counts how many it changed. Also holds the single default model string, so no module can fall back to the withdrawn one. |

## Four things that will bite you

**The MCP server runs as a subprocess.** It bootstraps `sys.path` before
importing anything under `trip_planner.`, because the project root is not on the
path when Python launches it by filename. Without that, every tool call fails as
"Connection lost" — and it fails *silently*, so the agents produce itineraries
from model knowledge instead of API data.

**CrewAI `@tool` produces `Tool` objects, not functions.** Call `.run(...)`, not
`f(...)`. Runtime code that just wants the behaviour imports the plain functions
from `server/mcp_server.py` or `tools/travel_apis.py`.

**fly-scraper is a two-phase API.** The search endpoint only starts a search and
returns a `sessionId`; results come from `/v2/flights/search-incomplete`. Its
date parameters are camelCase (`departureDate`), and the snake_case forms are
accepted with HTTP 200 and then ignored — wrong dates, no error.

**Never hand-count model requests.** Use `core/llm_metrics.py`. Its callbacks
fire off-thread, so a session drains before reporting.

## The design argument this code exists to make

The A2A protocol and the MCP server are identical across all four evaluated
architectures. Only the retrieval layer differs. That is the point: the protocol
design is independent of whether a model or plain Python does the fetching, and
the measurements show the model adds cost there without adding judgement.

Two honest qualifications, both argued in the dissertation rather than buried
here. In the shipped path the A2A layer records the exchange rather than
dispatching it — the orchestrator sends messages and reads the history, and never
dequeues. And the shipped path imports the tool functions in process rather than
driving them over JSON-RPC; the transport is exercised by the six-agent
architectures.
