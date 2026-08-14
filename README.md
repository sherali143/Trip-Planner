# AI Trip Planner — Multi-Agent Travel Planning System

MSc dissertation project (Birmingham City University, CMP7200).

Turns a plain-English travel request into a day-by-day itinerary with real
flights, hotels, attractions and restaurants — built on a custom **MCP server**
and a typed **Agent-to-Agent (A2A) protocol**, and evaluated as **four competing
architectures**.

---

## The research question

The proposal specified a 6-agent architecture. Instrumenting it showed most of
its LLM calls went on deterministic data retrieval rather than reasoning. So a
3-agent design was built that keeps the same protocols but fetches data in plain
Python — and the multi-agent arm was *tuned* first, so the comparison is against
a fair baseline rather than a straw man.

| Arm | Architecture | File |
|---|---|---|
| **A** | Single LLM — no agents, no tools | `comparison/arm_a_single_llm.py` |
| **B** | 6 agents, naive (as first built) | `comparison/arm_b_six_agent_naive.py` |
| **C** | 6 agents, tuned — the proposal as designed | `comparison/arm_c_six_agent_tuned.py` |
| **D** | 3 agents + direct API calls | `comparison/arm_d_three_agent_direct.py` |

### Which approach the system actually runs

The four architectures above exist **for the evaluation**. The production
system — `run_cli.py` and `run_web.py` — runs **arm D**: three agents with
direct API retrieval. Arms A, B and C are built and kept runnable because they
are the comparison the dissertation rests on, not because anything ships them.

| Command | Approach used |
|---|---|
| `python run_cli.py` | **D** — 3 agents + direct API |
| `python run_web.py` | **D** — 3 agents + direct API |
| `python demos/demo_comparison.py` | all four, side by side |
| `python demos/demo_approach.py B` | **B** alone, narrated |
| `python demos/demo_approach.py D` | **D** alone, narrated |
| `python -m comparison.run_comparison` | all four, across the scenarios |

### Measured results (SC-01, all four arms)

| Arm | LLM calls | Tokens | Cost | Time | Prices that are real |
|---|---|---|---|---|---|
| A single LLM | 1 | 11,392 | $0.028 | 93s | **0%** |
| B 6-agent naive | 19 | 63,926 | $0.053 | 86s | 13% |
| C 6-agent tuned | 9 | 10,808 | $0.015 | 66s | 59% |
| D 3-agent direct | 2 | 7,813 | $0.011 | 18s | 57% |

Every LLM request is counted via LiteLLM callbacks — none of these numbers is an
estimate. Two findings:

- **Tuning matters more than agent count.** Tuning cut the multi-agent arm's
  tokens ~83%; most of the naive penalty was implementation, not architecture.
  Against the *tuned* arm, D still wins clearly on call count and latency, but
  only modestly on cost.
- **Cheap can mean worthless.** The tool-less arm quoted 57 prices and matched
  **none** to a real fare. That is the hallucination failure the literature
  describes (Xie et al., 2024) — measured, not asserted.

---

## Quick start

```bash
# 1. install
setup.bat                      # Windows
# or: python -m venv .venv && pip install -r requirements.txt

# 2. configure
cp .env.example .env           # then paste your keys in

# 3. run the comparison — FREE, replays recorded API responses
TRIP_PLANNER_API_MODE=replay python -m comparison.run_comparison SC-01
```

### Other entry points

| Command | What it does |
|---|---|
| `python run_cli.py` | Interactive terminal planner |
| `python run_web.py` | Streamlit web UI (localhost:8501) |
| `python demos/demo_comparison.py --no-pause` | Viva demo: all four arms side by side |
| `python demos/demo_approach.py A\|B\|C\|D` | One approach in isolation, narrated |
| `python -m comparison.run_comparison` | Full evaluation, all 20 scenarios |
| `python docs/generate_docx.py` | Rebuild the project document from results |
| `python -m pytest` | Test suite (148 tests) |
| `python figures/make_charts.py` | Regenerate results charts |
| `python figures/make_diagrams.py` | Regenerate architecture diagrams |

---

## ⚠️ API quota — read this before running anything live

The flight and hotel free tiers are **monthly and very small**:

| API | Limit | Used for |
|---|---|---|
| fly-scraper | **30 / month** | Flights |
| booking-com15 | **50 / month** | Hotels |
| Serper | large | Attractions, restaurants |
| Gemini | free tier | The LLM |

One careless run can spend a whole month's allowance, and you cannot buy it
back. Two protections:

```bash
# never touches the network — reproduces everything from recordings
export TRIP_PLANNER_API_MODE=replay

# hard stop after N live calls
export TRIP_PLANNER_MAX_LIVE_CALLS=10
```

### Record / replay

Every HTTP call goes through `src/core/http_cache.py`. Recorded responses live
in `.api_cache/` and **are committed**, so anyone can reproduce the published
results **with no API keys at all**.

Only 2xx responses are cached, so a quota 429 is never baked in. Request headers
are excluded from both the cache key and the stored file, so no key material is
written to disk.

Because recordings are permanent, the evaluation can be built up **in batches
across months** — record some scenarios now, the rest after the quota resets,
then replay all 20 for free.

---

## Project structure

```
trip_planner/
│
├── src/                     APPLICATION CODE
│   ├── agents.py              the three agents that need an LLM
│   ├── tasks.py               their task definitions and prompts
│   ├── orchestrator.py        the production workflow
│   ├── comms/                 A2A protocol — envelope, registry, queue
│   ├── server/                MCP server — 12 schema-validated tools
│   ├── tools/                 tool wrappers exposed to agents
│   ├── core/                  caching, measurement, retry, budget, cost
│   └── ui/                    Streamlit interface
│
├── comparison/              THE EVALUATION
│   ├── architecture_*.py      the four approaches (A, B, C, D)
│   ├── scenarios.py           20 evaluation scenarios
│   ├── metrics.py             groundedness scoring
│   ├── run_comparison.py      the runner
│   └── results/               measured results (committed)
│
├── docs/                    PROPOSAL AND REPORTS
│   ├── AI_Trip_Planner_Proposal.pdf
│   ├── CMP7200_Assignment_Brief.pdf
│   ├── AI_Trip_Planner_Project_Document.docx
│   ├── generate_docx.py       regenerates the document from results
│   └── DEVELOPMENT_NOTES.md
│
├── demos/                   demo_approach.py (one arm) + demo_comparison.py (all four)
├── figures/                 7 generated charts and diagrams
├── testing/                 148 automated tests
├── deploy/                  Dockerfile and compose
├── .api_cache/              recorded API responses (committed)
│
├── setup.bat                one-command setup
├── run_cli.py               plan a trip in the terminal
├── run_web.py               plan a trip in the browser
└── requirements.txt         pinned dependencies
```

---

## Architecture

**MCP server** (`src/server/mcp_server.py`) — 12 schema-validated tools over
JSON-RPC/stdio. Runs as a subprocess, so it bootstraps `sys.path` before
importing `src.*`; without that every tool call fails as "Connection lost".

**A2A protocol** (`src/comms/`) — 8 agent cards, 6 message types (REQUEST,
RESPONSE, QUERY, INFO, ERROR, ACK), permission validation, priority queue.
**Identical in every arm** — that is the point: the protocol layer is
independent of how data is fetched.

**Tech stack**

| Component | Technology |
|---|---|
| Agents | CrewAI |
| LLM | Google Gemini 2.5 Flash via LiteLLM |
| Flights | fly-scraper (RapidAPI) |
| Hotels | Booking.com (RapidAPI) |
| Web search | Serper.dev |
| UI | Streamlit + CLI |

---

## Gotchas worth knowing

- **fly-scraper is a two-phase API.** The search endpoint only *starts* the
  search and returns a `sessionId`; results come from
  `/v2/flights/search-incomplete`. Treating the first response as final returns
  zero flights, every time.
- **Its date parameters are camelCase** (`departureDate`, `returnDate`). The
  snake_case forms are silently ignored — HTTP 200, wrong dates, no error.
- **Endpoint paths are plural** (`/flights/...`); the RapidAPI console lists
  them as `flight/...`, which 404s.
- **CrewAI `@tool` makes `Tool` objects, not functions.** Call `.run(...)`, not
  `f(...)`. Runtime code imports the plain functions from `src/server/mcp_server.py`.
- **Never hand-count LLM calls.** Use `src/core/llm_metrics.py`; its callbacks
  fire off-thread, so sessions drain before reporting.

---

## Status

Working: all four arms, all APIs, MCP server, A2A protocol, test suite,
auto-generated dissertation document, Streamlit UI.

Remaining: record the other 19 scenarios (batched across quota resets), then
re-run `docs/generate_docx.py`.

See `docs/DEVELOPMENT_NOTES.md` for detailed working notes, and `docs/AI_Trip_Planner_Project_Document.docx` for the full project document.
