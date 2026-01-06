# Trip Planner Setup Guide

Complete setup instructions for the AI Trip Planner with A2A Protocol and MCP Integration.

## Prerequisites

- Python 3.10+
- OpenAI API key
- RapidAPI key (for flight and hotel APIs)
- Serper API key (for web search)

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd trip_planner
pip install poetry
poetry install
```

Or using pip:
```bash
pip install crewai[tools] langchain langchain-openai python-dotenv requests pydantic pyyaml mcp
```

### 2. Configure Environment

Create a `.env` file:
```env
# Required
OPENAI_API_KEY=your_openai_api_key
SERPER_API_KEY=your_serper_api_key
RAPIDAPI_KEY=your_rapidapi_key

# Optional
OPENAI_ORGANIZATION_ID=your_org_id
```

### 3. Get API Keys

| API | Purpose | Sign Up |
|-----|---------|---------|
| OpenAI | LLM for agents | [platform.openai.com](https://platform.openai.com) |
| RapidAPI | Flight & hotel search | [rapidapi.com](https://rapidapi.com) |
| Serper | Web search | [serper.dev](https://serper.dev) |

**RapidAPI subscriptions needed:**
- [Kiwi.com Cheap Flights](https://rapidapi.com/apiheya/api/kiwi-com-cheap-flights)
- [Booking.com](https://rapidapi.com/booking-com15/api/booking-com15)

### 4. Verify Setup

```bash
python test_mcp_servers.py
```

### 5. Run Trip Planner

**Command Line:**
```bash
python main.py
```

**Web UI (Streamlit):**
```bash
streamlit run app.py
```

**With Parallel Mode (faster):**
```python
from main import TripPlannerCrew
crew = TripPlannerCrew(parallel_mode=True)
```

## Example Usage

When prompted, enter your trip request:
```
I want to visit Tokyo for 7 days with a $4000 budget. I'm interested in 
Japanese culture, temples, authentic food, and seeing Mt. Fuji.
```

## Project Structure

```
trip_planner/
├── main.py              # Main orchestrator
├── agents.py            # Agent definitions
├── tasks.py             # Task definitions
├── a2a_protocol.py      # Agent-to-agent communication
├── tools/               # Tool implementations
│   ├── mcp_tools.py     # MCP tool wrappers
│   └── calculatortool.py # Safe calculator
├── utils/               # Utility modules
│   ├── api_resilience.py # Retry/fallback logic
│   ├── cache_manager.py  # Query caching
│   └── itinerary_validator.py # Day-count validation
├── mcp_servers/         # MCP server implementations
└── tests/               # Test suite
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API key errors | Check `.env` file exists and keys are valid |
| Rate limit errors | Wait 1-2 minutes, or reduce `max_rpm` in agents |
| Package not found | Run `poetry install` or `pip install -r requirements.txt` |

## Advanced Configuration

See `config.yaml` for:
- Agent model settings (GPT-4, temperature)
- Budget allocation defaults
- MCP server endpoints

## Documentation

- [README.md](../README.md) - Full system documentation
- [MCP_SETUP.md](../MCP_SETUP.md) - Detailed MCP configuration
