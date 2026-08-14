# AI Trip Planner — working notes

MSc dissertation project (BCU, CMP7200). A multi-agent travel planner built on a
custom MCP server and a typed Agent-to-Agent (A2A) protocol, evaluated as four
competing architectures.

## The research question

The proposal specified a 6-agent architecture. Measurement showed most of its
LLM calls were spent on deterministic data retrieval rather than reasoning, so a
3-agent design was built that keeps the same protocols but fetches data in plain
Python. The dissertation compares them — with the 6-agent arm tuned first, so
the comparison is not against a straw man.

## The four arms

| Arm | File | What it is |
|---|---|---|
| A | `comparison/arm_a_single_llm.py` | One LLM call, no agents, no tools |
| B | `comparison/arm_b_six_agent_naive.py` | 6 agents, naive config (as first built) |
| C | `comparison/arm_c_six_agent_tuned.py` | 6 agents, tuned — the proposal as designed |
| D | `comparison/arm_d_three_agent_direct.py` | 3 agents + direct API calls |

Run them: `python -m comparison.run_comparison` (add `SC-01 SC-04` to filter).
Results land in `comparison/results/comparison_results.json`.

## Measured so far (SC-01, all four arms)

| Arm | LLM calls | Tokens | Cost | Secs | Prices that are real |
|---|---|---|---|---|---|
| A single LLM | 1 | 11,392 | $0.028 | 92.6 | **0%** |
| B 6-agent naive | 19 | 63,926 | $0.053 | 85.5 | 13% |
| C 6-agent tuned | 9 | 10,808 | $0.015 | 66.1 | 59% |
| D 3-agent direct | 2 | 7,813 | $0.011 | 17.9 | 57% |

Two findings worth keeping straight:

- Tuning the multi-agent arm cut its tokens ~83%. Most of the naive penalty was
  implementation, not architecture. Against the *tuned* arm, D still wins clearly
  on call count and latency, but only modestly on cost.
- The tool-less arm quoted 57 prices and matched **none** of them to a real fare.
  Cheapness there is worthless — it is the hallucination failure the literature
  describes (Xie et al., 2024).

## ⚠️ API quota — read before running anything

Free tiers are **monthly** and small:

| API | Limit |
|---|---|
| fly-scraper (flights) | **30 / month** |
| booking-com15 (hotels) | **50 / month** |
| Serper | large |
| Gemini | free tier, rate-limited per minute |

Always set a cap:

```bash
export TRIP_PLANNER_MAX_LIVE_CALLS=10   # hard stop; raises QuotaGuardTripped
```

### Record / replay

Every HTTP call goes through `src/core/http_cache.py`.

| Mode | Behaviour |
|---|---|
| `record` (default) | Use cache; call live only on a miss, then store it |
| `replay` | Cache only — **never** touches the network |
| `live` | Always call live, refresh the cache |

```bash
export TRIP_PLANNER_API_MODE=replay     # re-run the whole evaluation for free
```

Recorded responses live in `.api_cache/` and are committed, so results reproduce
**with no API keys at all**. Only 2xx responses are cached, so a quota 429 is
never baked in. Request headers are excluded, so no key material is written.

Because recordings are permanent, the evaluation can be built up in batches
across months — record some scenarios now, the rest after the quota resets, then
replay all 20 for free.

## Configuration

`.env`:

| Key | Purpose |
|---|---|
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Gemini (the LLM) |
| `GEMINI_MODEL` | LiteLLM model string, e.g. `gemini/gemini-2.5-flash` |
| `RAPIDAPI_KEY` | Both flights and hotels |
| `SERPER_API_KEY` | Attractions, restaurants, web search |

Model is **Gemini 2.5 Flash** via LiteLLM. (Earlier notes said Groq — that is no
longer true and there is no `GROQ_API_KEY`.)

## Architecture notes

- **MCP server** — `src/server/mcp_server.py`, 12 tools over JSON-RPC/stdio. It
  runs as a *subprocess*, so it bootstraps `sys.path` before importing `src.*`;
  without that every tool call fails as "Connection lost".
- **A2A protocol** — `src/comms/`, 8 agent cards, 6 message types, permission
  validation. **Identical in every arm** — that is the point: the protocol layer
  is independent of how data is fetched.
- **Tool layer** — `src/tools/mcp_tools.py`. Note the CrewAI `@tool` decorator
  makes these `Tool` objects, not functions: call `.run(...)`, not `f(...)`.
  Runtime code imports the plain functions from `src/server/mcp_server.py`.
- **Metrics** — `src/core/llm_metrics.py` hooks LiteLLM callbacks to count real
  requests, tokens and cost. Callbacks fire off-thread, so sessions drain before
  reporting. Never hand-count LLM calls.
- **Groundedness** — `comparison/metrics.py`. Lead with `prices_grounded_pct`;
  name matching is weak evidence (a tool-less model can guess "Turkish Airlines"
  for Istanbul).

## Gotchas that cost real time

- fly-scraper is a **two-phase** API: the search endpoint only starts the search
  and returns a `sessionId`; results come from `/v2/flights/search-incomplete`.
  Reading the first response as final returns zero flights, always.
- Its date parameters are **camelCase** (`departureDate`, `returnDate`). The
  snake_case forms are silently ignored — HTTP 200, wrong dates, no error.
- Endpoint paths are **plural** (`/flights/...`); the console lists them as
  `flight/...`, which 404s.
- Hotel enrichment (review breakdown, nearby POIs) costs 2 extra calls per hotel
  and reaches no itinerary. Off by default via `HOTEL_ENRICHMENT_TOP_N`.

## Tests

```bash
python -m pytest -q          # 149 passed
```

Every test carries real assertions. Ad-hoc probe scripts that asserted nothing
and called live endpoints were removed rather than kept beside them.

## Still to do

1. Record the remaining 19 scenarios (batch across quota resets)
2. Regenerate `docs/Dissertation_Project_Explanation.docx` — run `python scripts/generate_guide.py`
3. Consider running each scenario 3x — arm B varied 19-23 calls between runs
