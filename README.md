# AI Trip Planner

MSc dissertation project — Birmingham City University, CMP7200.

Turns a plain-English travel request into a day-by-day itinerary built from real
flights, hotels and venues, using a custom **MCP server** and a typed
**Agent-to-Agent (A2A) protocol** — and measures what four competing
architectures actually cost.

---

## Start here

Read **`submission/PROJECT_OVERVIEW.docx`** first — six pages of plain English covering the
problem, the four approaches, what was found, the known issues, and how to
demonstrate the work. It is written for someone who has never seen this
repository.

Then double-click **`run.bat`**.

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
 10. Rebuild the project overview
 11. Rebuild the viva presentation

PLAN A REAL TRIP    needs API keys
 12. In the browser
 13. In this window
```

**Options 1 to 11 need no API keys and no internet.** The demos replay real
recorded runs, so they work even when every quota is exhausted.

### Without `run.bat`

`run.bat` is Windows only, and it does nothing you cannot do in three commands.
Verified from a clean clone:

```bash
python -m venv .venv                          # needs Python 3.10 or newer
.venv/Scripts/python -m pip install -r requirements.txt    # ~400 MB, 2-5 min
cp .env.example .env                          # only needed for a live trip
```

Then any of these, with `.venv/Scripts/python` as `python`:

```bash
python -m pytest -q                                     # the test suite
python trip_planner/demos/compare_all_approaches.py     # all four approaches
python -m trip_planner.evaluation.exp_protocol          # conformance audit
python -m trip_planner.evaluation.exp_budget_gate       # the feasibility gate
python -m submission.build.build_dissertation --split-appendices   # the report
python run_web.py                                       # the web page
```

On macOS or Linux the interpreter is `.venv/bin/python` instead.

**Keep the folder path short.** The install writes deeply nested files inside
`.venv`, and Windows caps paths at 260 characters. From a long path the install
fails with a confusing "No such file or directory" on a file you have never heard
of. `run.bat` warns above 90 characters; if you are installing by hand, put the
project somewhere like `C:	rip_planner`.

### API keys (only for options 12 and 13)

Paste into `.env`:

| Key | Used for | Where to get one |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini, the language model | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `RAPIDAPI_KEY` | Flights and hotels | [rapidapi.com](https://rapidapi.com) |
| `SERPER_API_KEY` | Attractions and restaurants | [serper.dev](https://serper.dev) |

---

## The layout

Two folders: the code, and what gets handed in.

```
trip_planner/          all the code
  orchestrator.py        the workflow: read the request, fetch, assemble
  agents.py  tasks.py    the three agents that use a model, and their instructions
  core/                  budgets, costs, caching, measuring, safe arithmetic
  frontend/              the web page
  comms/                 the message protocol between components
  server/                the tool server (12 tools over JSON-RPC)
  tools/                 anything that calls an external service
  evaluation/            the four approaches, the scenarios, the measured results
  demos/                 one runnable demonstration per approach
  tests/                 the test suite

submission/            everything handed in
  CMP7200_Dissertation.docx        the main deliverable
  CMP7200_Viva_Presentation.pptx   the slides
  PROJECT_OVERVIEW.docx            plain-English guide — read this first
  AI_Trip_Planner_Proposal.pdf     the original proposal
  CMP7200_Assignment_Brief.pdf     the brief
  build/                           the scripts that generate the three above

run.bat                one click: sets up everything, then a menu
run_cli.py             plan a trip in the terminal
run_web.py             plan a trip in the browser
requirements.txt       pinned dependencies
.env.example           key template (.env itself is never committed)
.api_cache/            recorded API replies, so every result replays for free
```

Finished documents sit at `submission/`, the scripts that build them one level
down in `build/`, so what is being submitted is obvious without reading anything.

Every source file opens with one or two plain sentences saying what it is for.

---

## The research question

The proposal specified a 6-agent architecture. Instrumenting it showed most of
its model requests went on deterministic data retrieval rather than reasoning, so
a 3-agent design was built that keeps both protocols but fetches data in plain
Python. The multi-agent arm was **tuned first**, so the comparison is against a
fair baseline rather than a straw man.

| Approach | Architecture | Code |
|---|---|---|
| **A** | Single model — no agents, no tools | `trip_planner/evaluation/arm_a_single_llm.py` |
| **B** | 6 agents, naive (as first built) | `trip_planner/evaluation/arm_b_six_agent_naive.py` |
| **C** | 6 agents, tuned — the proposal as designed | `trip_planner/evaluation/arm_c_six_agent_tuned.py` |
| **D** | 3 agents + direct API calls — **what ships** | `trip_planner/evaluation/arm_d_three_agent_direct.py` |

`run_cli.py` and `run_web.py` both run **approach D**. A, B and C exist for the
evaluation and are kept runnable because the dissertation rests on them.

### Measured results (SC-01, 5 runs of each)

| Approach | AI calls | Tokens | Cost | Time | Prices that are real |
|---|---|---|---|---|---|
| A single model | 1 | 4,644 | $0.0170 | 27s | 2% |
| B 6-agent naive | 21 | 120,703 | $0.1859 | 372s | 23% |
| C 6-agent tuned | 10 | 13,521 | $0.0313 | 37s | 56% |
| D 3-agent direct | 2 | 7,840 | $0.0179 | 23s | 47% |

Every request is counted through LiteLLM callbacks — none of these is an
estimate. Each architecture was run **5 times**, so the
report carries a standard deviation and a 95% interval for every figure. The
runs cover **1 of 20**
designed scenarios: repeats replay recorded API responses and cost nothing,
while extra scenarios need travel-API quota.

Four findings:

- **Tools matter most.** The tool-less approach quoted
  29 prices and matched
  0 to a real fare.
- **Tuning matters more than agent count.** B and C are the *same* six agents
  with the same data; tuning alone cut tokens by
  89%.
- **Removing the model from retrieval is decisively cheaper and faster.** Cost
  and latency intervals for C and D do not overlap.
- **It is not measurably better grounded.** C and D groundedness intervals do
  overlap, and C's mean is the higher of the two. Reported as-is.

### Experiments that need no quota

```bash
python -m trip_planner.evaluation.exp_protocol      # A2A + MCP conformance, 9 checks
python -m trip_planner.evaluation.exp_budget_gate   # budget gate across all 20 scenarios
```

Both found real defects, and both are reported in the dissertation rather than
quietly fixed: message priority is declared and never honoured, inbound
permissions are never enforced, three tool schemas disagree with their
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
| `python trip_planner/demos/compare_all_approaches.py` | All four side by side | free |
| `python trip_planner/demos/approach_d_three_agent_direct.py` | One approach in detail (also `_a_`, `_b_`, `_c_`) | free |
| `python -m pytest` | The test suite | free |
| `python trip_planner/demos/show_agent_messages.py` | Watch the A2A protocol pass real messages, and refuse an undeclared one | free |
| `python -m trip_planner.evaluation.verify_approaches` | Prove every approach, the MCP server and the A2A layer are wired up | free |
| `python -m trip_planner.evaluation.exp_protocol` | Protocol conformance audit | free |
| `python -m trip_planner.evaluation.exp_budget_gate` | Budget gate, 20 scenarios | free |
| `python submission/build/make_diagrams.py` | 8 diagrams at 300 dpi, validated | free |
| `python submission/build/make_charts.py` | 6 charts from measured data | free |
| `python -m submission.build.build_dissertation --figures --split-appendices` | Rebuild the dissertation and its appendices document | free |
| `python submission/build/make_handover.py` | Rebuild `submission/PROJECT_OVERVIEW.docx` | free |
| `python -m submission.build.make_viva_deck` | Rebuild `submission/CMP7200_Viva_Presentation.pptx` | free |
| `python -m submission.build.verify_no_hardcoded_numbers` | Prove no number is typed by hand | free |
| `python -m trip_planner.evaluation.run_comparison SC-01` | The four-approach comparison | model quota |
| `python run_cli.py` | Plan a trip in the terminal | API keys |
| `python run_web.py` | Plan a trip in the browser | API keys |

Add `--live` to any demo to run the **model** for real. Travel responses still
replay from disk, so no flight or hotel quota is spent — the screen says so.
Add `--live-apis` as well to call the travel APIs for real, which **does** spend
the monthly allowance.

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
| Model | Google Gemini 3.6 Flash via LiteLLM (2.5 Flash produced the first round and was withdrawn mid-project) |
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
