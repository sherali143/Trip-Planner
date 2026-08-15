# AI Trip Planner

MSc dissertation project — Birmingham City University, CMP7200.

Turns a plain-English travel request into a day-by-day itinerary built from real
flights, hotels and venues, using a custom **MCP server** and a typed
**Agent-to-Agent (A2A) protocol** — and measures what four competing
architectures actually cost.

---

## Start here

Double-click **`run.bat`**.

It checks Python, creates the virtual environment, installs the pinned
dependencies, sets up `.env`, and then shows a menu. Nothing else to install.

```
DEMONSTRATIONS      free - no keys, no internet, no quota
  1. Compare all four approaches      <- show this first
  2. Approach A - single LLM, no tools
  3. Approach B - six agents, naive
  4. Approach C - six agents, tuned
  5. Approach D - three agents, direct  (what ships)

THE PROJECT         free
  6. Run the test suite
  7. Run the evaluation experiments
  8. Rebuild the figures
  9. Rebuild the dissertation

PLAN A REAL TRIP    needs API keys
 10. In the browser
 11. In this window
```

**Options 1 to 9 need no API keys and no internet.** The demos replay real
recorded runs, so they work even when every quota is exhausted.

### API keys (only for options 10 and 11)

Paste into `.env`:

| Key | Used for | Where to get one |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini, the language model | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `RAPIDAPI_KEY` | Flights and hotels | [rapidapi.com](https://rapidapi.com) |
| `SERPER_API_KEY` | Attractions and restaurants | [serper.dev](https://serper.dev) |

---

## The five folders

| Folder | What is in it |
|---|---|
| **`trip_planner/`** | The system itself. All the application code. |
| **`evaluation/`** | The four approaches, the scenarios, the metrics and the measured results the dissertation is built from. |
| **`demos/`** | One runnable demonstration per approach, plus a side-by-side comparison. Works with no keys. |
| **`report/`** | The dissertation, the code that generates it, and every figure. |
| **`proposal/`** | The original proposal and the assignment brief. |
| **`testing/`** | The test suite. |

Every source file opens with a comment saying what that file does and why.

---

## The research question

The proposal specified a 6-agent architecture. Instrumenting it showed most of
its model requests went on deterministic data retrieval rather than reasoning, so
a 3-agent design was built that keeps both protocols but fetches data in plain
Python. The multi-agent arm was **tuned first**, so the comparison is against a
fair baseline rather than a straw man.

| Approach | Architecture | Code |
|---|---|---|
| **A** | Single model — no agents, no tools | `evaluation/arm_a_single_llm.py` |
| **B** | 6 agents, naive (as first built) | `evaluation/arm_b_six_agent_naive.py` |
| **C** | 6 agents, tuned — the proposal as designed | `evaluation/arm_c_six_agent_tuned.py` |
| **D** | 3 agents + direct API calls — **what ships** | `evaluation/arm_d_three_agent_direct.py` |

`run_cli.py` and `run_web.py` both run **approach D**. A, B and C exist for the
evaluation and are kept runnable because the dissertation rests on them.

### Measured results (SC-01, all four)

| Approach | Requests | Tokens | Cost | Time | Prices that are real |
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
- **Cheap can mean worthless.** The tool-less approach quoted 57 prices and
  matched **none** to a real fare.
- **Adopting a protocol is not conforming to one.** An audit of this project's
  own protocol layer passes 3 of 9 checks.

### Experiments that need no quota

```bash
python -m evaluation.exp_protocol      # A2A + MCP conformance, 9 checks
python -m evaluation.exp_budget_gate   # budget gate across all 20 scenarios
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

```bash
export TRIP_PLANNER_API_MODE=replay      # never touches the network
export TRIP_PLANNER_MAX_LIVE_CALLS=10    # hard stop after N live calls
```

Every HTTP call goes through `trip_planner/core/http_cache.py`. Recorded
responses live in `.api_cache/` and **are committed**, so the published results
reproduce **with no API keys at all**. Only 2xx responses are cached, so a quota
429 is never baked in, and request headers are excluded from both the cache key
and the stored file, so no key material reaches disk.

---

## Every command

| Command | What it does | Costs |
|---|---|---|
| `run.bat` | Setup, then everything below via a menu | — |
| `python demos/compare_all_approaches.py` | All four side by side | free |
| `python demos/approach_d_three_agent_direct.py` | One approach in detail (also `_a_`, `_b_`, `_c_`) | free |
| `python -m pytest` | The test suite | free |
| `python -m evaluation.exp_protocol` | Protocol conformance audit | free |
| `python -m evaluation.exp_budget_gate` | Budget gate, 20 scenarios | free |
| `python report/build/make_diagrams.py` | 8 diagrams at 300 dpi, validated | free |
| `python report/build/make_charts.py` | 6 charts from measured data | free |
| `python -m report.build.build_report --figures` | Rebuild the dissertation | free |
| `python -m report.build.verify_no_hardcoded_numbers` | Prove no number is typed by hand | free |
| `python -m evaluation.run_comparison SC-01` | The four-approach comparison | model quota |
| `python run_cli.py` | Plan a trip in the terminal | API keys |
| `python run_web.py` | Plan a trip in the browser | API keys |

Add `--live` to any demo to execute it for real instead of replaying.

---

## Architecture

**MCP server** (`trip_planner/server/mcp_server.py`) — 12 schema-validated tools
over JSON-RPC/stdio. Runs as a subprocess, so it bootstraps `sys.path` before
importing `trip_planner.*`; without that every tool call fails as "Connection
lost".

**A2A protocol** (`trip_planner/comms/`) — 8 agent cards, 6 message types
(REQUEST, RESPONSE, QUERY, INFO, ERROR, ACK), permission validation. Identical in
every approach, which is the point: the protocol layer is independent of how data
is fetched. In the shipped path it records the exchange rather than dispatching
it.

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
  `f(...)`. Runtime code imports the plain functions from the MCP server module.
- **Never hand-count model requests.** Use `trip_planner/core/llm_metrics.py`;
  its callbacks fire off-thread, so sessions drain before reporting.

---

## Status

**Working:** all four approaches, all APIs, MCP server, A2A protocol, test suite,
Streamlit UI, the generated dissertation, and every figure.

**Waiting on quota:** repeat runs of SC-01 for a confidence interval (needs only
the Gemini free tier, no travel-API quota), then the remaining 19 scenarios.
Recordings accumulate, so coverage grows without re-running what already exists —
rebuild the report afterwards and every number, figure and table updates itself.
