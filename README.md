# AI Trip Planner

MSc dissertation project — Birmingham City University, CMP7200.

Turns a plain-English travel request into a day-by-day itinerary built from real
flights, hotels and venues, using a custom **MCP server** and a typed
**Agent-to-Agent (A2A) protocol** — and measures what four competing
architectures actually cost.

---

## Getting started

Double-click **`run.bat`**.

It creates the virtual environment, installs the pinned dependencies, sets up
`.env`, and then gives you a menu. Nothing else needs installing.

```
1. Plan a trip in the browser      needs API keys
2. Plan a trip in this window      needs API keys
3. Run the test suite              free
4. Run the evaluation experiments  free
5. Rebuild the figures             free
6. Rebuild the dissertation        free
```

Options 3–6 need **no API keys and no internet**: the recorded API responses in
`.api_cache/` are committed, so the whole evaluation replays from disk.

### API keys (only for options 1 and 2)

Paste these into `.env`:

| Key | Used for | Where to get one |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini, the language model | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `RAPIDAPI_KEY` | Flights and hotels | [rapidapi.com](https://rapidapi.com) |
| `SERPER_API_KEY` | Attractions and restaurants | [serper.dev](https://serper.dev) |

---

## The research question

The proposal specified a 6-agent architecture. Instrumenting it showed most of
its model requests went on deterministic data retrieval rather than reasoning, so
a 3-agent design was built that keeps both protocols but fetches data in plain
Python. The multi-agent arm was **tuned first**, so the comparison is against a
fair baseline rather than a straw man.

| Arm | Architecture | File |
|---|---|---|
| **A** | Single model — no agents, no tools | `comparison/arm_a_single_llm.py` |
| **B** | 6 agents, naive (as first built) | `comparison/arm_b_six_agent_naive.py` |
| **C** | 6 agents, tuned — the proposal as designed | `comparison/arm_c_six_agent_tuned.py` |
| **D** | 3 agents + direct API calls — **what ships** | `comparison/arm_d_three_agent_direct.py` |

`run_cli.py` and `run_web.py` both run **arm D**. Arms A, B and C exist for the
evaluation and are kept runnable because the dissertation rests on them.

### Measured results (SC-01, all four arms)

| Arm | Requests | Tokens | Cost | Time | Prices that are real |
|---|---|---|---|---|---|
| A single model | 1 | 11,392 | $0.028 | 93s | **0%** |
| B 6-agent naive | 19 | 63,926 | $0.053 | 86s | 13% |
| C 6-agent tuned | 9 | 10,808 | $0.015 | 66s | 59% |
| D 3-agent direct | 2 | 7,813 | $0.011 | 18s | 57% |

Every request is counted through LiteLLM callbacks — none of these is an
estimate. **This is one scenario of twenty, run once**, which is stated wherever
the numbers appear. Three findings:

- **Tuning matters more than agent count.** Tuning cut the multi-agent arm's
  tokens ~83%; most of the naive penalty was implementation, not architecture.
- **Cheap can mean worthless.** The tool-less arm quoted 57 prices and matched
  **none** to a real fare — the hallucination failure the literature describes,
  measured rather than asserted.
- **Adopting a protocol is not conforming to one.** An audit of this project's
  own protocol layer passes 3 of 9 checks. See below.

### Quota-free experiments

Two parts of the evaluation need no network, no model and no keys, so they cover
all 20 scenarios where the four-arm comparison cannot:

```bash
python -m comparison.exp_protocol      # A2A + MCP conformance
python -m comparison.exp_budget_gate   # budget feasibility gate, 20 scenarios
```

Both found real defects, and both are reported in the dissertation rather than
quietly fixed: message priority is declared and never honoured, inbound
permissions are never enforced, four tool schemas disagree with their
implementations, and the budget gate's cheapest-fare anchor sits ~52% below the
cheapest fare the flight API actually returned.

---

## ⚠️ API quota — read before running anything live

The flight and hotel free tiers are **monthly and very small**:

| API | Limit | Used for |
|---|---|---|
| fly-scraper | **30 / month** | Flights |
| booking-com15 | **50 / month** | Hotels |
| Serper | large | Attractions, restaurants |
| Gemini | free tier, rate-limited | The language model |

One careless run can spend a whole month's allowance, and you cannot buy it back.
Two protections:

```bash
export TRIP_PLANNER_API_MODE=replay      # never touches the network
export TRIP_PLANNER_MAX_LIVE_CALLS=10    # hard stop after N live calls
```

### Record / replay

Every HTTP call goes through `src/core/http_cache.py`. Recorded responses live in
`.api_cache/` and **are committed**, so anyone can reproduce the published
results **with no API keys at all**.

Only 2xx responses are cached, so a quota 429 is never baked in. Request headers
are excluded from both the cache key and the stored file, so no key material is
written to disk. Because recordings are permanent, the evaluation can be built up
**in batches across months**.

---

## Project structure

```
trip_planner/
│
├── run.bat                  START HERE — sets everything up, then a menu
├── run_cli.py               plan a trip in the terminal
├── run_web.py               plan a trip in the browser
│
├── src/                     THE APPLICATION
│   ├── orchestrator.py        the production workflow
│   ├── agents.py, tasks.py    the three agents that need a model
│   ├── comms/                 A2A protocol: 8 agent cards, 6 message types
│   ├── server/                MCP server: 12 schema-validated tools
│   ├── tools/                 tool wrappers plus the direct HTTP clients
│   ├── core/                  caching, measurement, budget, cost, safe maths
│   └── ui/                    Streamlit interface
│
├── comparison/              THE EVALUATION
│   ├── arm_a…arm_d            the four architectures
│   ├── scenarios.py           20 scenarios + declared ground truth
│   ├── metrics.py             groundedness scoring
│   ├── measured.py            the single accessor for measured results
│   ├── exp_protocol.py        A2A + MCP conformance audit    (free)
│   ├── exp_budget_gate.py     budget gate over 20 scenarios  (free)
│   ├── run_comparison.py      the four-arm runner
│   └── results/               measured results, as JSON
│
├── report/                  THE DISSERTATION
│   ├── CMP7200_Dissertation.docx   generated — never edit by hand
│   └── build/                 one module per chapter, plus the proof that
│                              no number in it is typed by hand
│
├── scripts/                 FIGURE GENERATION
│   ├── figlib.py              layout engine: measures text, fails on collisions
│   ├── make_diagrams.py       8 architecture and concept diagrams
│   └── make_charts.py         6 charts, straight from measured data
│
├── demos/                   viva demonstrations
├── testing/                 the test suite
├── figures/                 generated figures, 300 dpi
├── proposal/                the proposal and the assignment brief
└── .api_cache/              recorded API responses (committed)
```

---

## Every command

| Command | What it does | Costs |
|---|---|---|
| `run.bat` | Setup, then everything below via a menu | — |
| `python run_cli.py` | Plan a trip in the terminal | API keys |
| `python run_web.py` | Plan a trip in the browser | API keys |
| `python -m pytest` | The test suite | free |
| `python -m comparison.exp_protocol` | Protocol conformance audit | free |
| `python -m comparison.exp_budget_gate` | Budget gate, 20 scenarios | free |
| `python -m comparison.run_comparison SC-01` | The four-arm comparison | model quota |
| `python demos/demo_all_arms.py --no-pause` | Viva demo: all four, side by side | model quota |
| `python demos/demo_one_arm.py D` | One architecture, narrated | model quota |
| `python scripts/make_diagrams.py` | 8 diagrams at 300 dpi, validated | free |
| `python scripts/make_charts.py` | 6 charts from measured data | free |
| `python -m report.build.build_report --figures` | Rebuild the dissertation | free |
| `python -m report.build.verify_no_hardcoded_numbers` | Prove no number is typed by hand | free |

---

## Architecture

**MCP server** (`src/server/mcp_server.py`) — 12 schema-validated tools over
JSON-RPC/stdio. Runs as a subprocess, so it bootstraps `sys.path` before
importing `src.*`; without that every tool call fails as "Connection lost".

**A2A protocol** (`src/comms/`) — 8 agent cards, 6 message types (REQUEST,
RESPONSE, QUERY, INFO, ERROR, ACK), permission validation. Identical in every
arm, which is the point: the protocol layer is independent of how data is
fetched. In the shipped path it records the exchange rather than dispatching it.

| Component | Technology |
|---|---|
| Agents | CrewAI |
| Model | Google Gemini 2.5 Flash via LiteLLM |
| Flights | fly-scraper (RapidAPI) |
| Hotels | Booking.com (RapidAPI) |
| Web search | Serper.dev |
| Interface | Streamlit + CLI |

---

## Gotchas worth knowing

- **fly-scraper is a two-phase API.** The search endpoint only *starts* the
  search and returns a `sessionId`; results come from
  `/v2/flights/search-incomplete`. Treating the first response as final returns
  zero flights, every time.
- **Its date parameters are camelCase** (`departureDate`, `returnDate`). The
  snake_case forms are silently ignored — HTTP 200, wrong dates, no error.
- **Endpoint paths are plural** (`/flights/...`); the RapidAPI console lists them
  as `flight/...`, which 404s.
- **CrewAI `@tool` makes `Tool` objects, not functions.** Call `.run(...)`, not
  `f(...)`. Runtime code imports the plain functions from `src/server/mcp_server.py`.
- **Never hand-count model requests.** Use `src/core/llm_metrics.py`; its
  callbacks fire off-thread, so sessions drain before reporting.

---

## Status

**Working:** all four arms, all APIs, MCP server, A2A protocol, test suite,
Streamlit UI, the generated dissertation, and every figure.

**Waiting on quota:** repeat runs of SC-01 for a confidence interval (needs only
the Gemini free tier, no travel-API quota), then the remaining 19 scenarios.
Recordings accumulate, so coverage grows without re-running what already exists —
re-run `python -m report.build.build_report --figures` afterwards and every
number, figure and table updates itself.
