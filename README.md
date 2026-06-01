# AI Trip Planner — Multi-Agent System with A2A Protocol & MCP

A production-grade AI trip planning system using multi-agent collaboration, real travel APIs, and industry-standard protocols.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER INPUT                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CONVERSATIONAL AGENT (GPT-4o)                   │
│              Gathers travel details via chat                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ A2A Protocol
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            PREFERENCES EXTRACTOR (GPT-4o)                    │
│            Structures conversation → JSON                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ A2A Protocol
              ┌───────────┼───────────┐
              ▼           ▼           ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  FLIGHT AGENT    │ │  HOTEL AGENT     │ │ ATTRACTION AGENT │
│  Kiwi + Booking  │ │  Booking.com     │ │  Serper (Google) │
│  via MCP Server  │ │  via MCP Server  │ │  via MCP Server  │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                     │
         └────────────┬───────┴─────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│            ITINERARY COORDINATOR (GPT-4o)                    │
│            Synthesizes → Day-by-day travel plan              │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | [CrewAI](https://docs.crewai.com/) |
| LLM | OpenAI GPT-4o |
| Agent Communication | Custom A2A Protocol |
| Tool Protocol | [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) |
| Flight API | RapidAPI → Kiwi.com + Booking.com Flights |
| Hotel API | RapidAPI → Booking.com Hotels |
| Web Search | Serper API (Google Search) |
| UI | Streamlit |
| Package Manager | Poetry |

## Quick Start

### Prerequisites

- Python 3.10–3.13
- API Keys (see below)

### Installation

```bash
git clone https://github.com/HamzahAhmad2000/trip-planner.git
cd trip-planner
pip install poetry
poetry install
```

### Configure API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys:

| Key | Provider | Get it from |
|-----|----------|-------------|
| `OPENAI_API_KEY` | OpenAI | https://platform.openai.com/api-keys |
| `SERPER_API_KEY` | Serper | https://serper.dev/ |
| `RAPIDAPI_KEY` | RapidAPI | https://rapidapi.com/ |

For RapidAPI, subscribe to:
- [Kiwi.com Cheap Flights](https://rapidapi.com/apiheya/api/kiwi-com-cheap-flights) (free tier)
- [Booking.com](https://rapidapi.com/booking-com15/api/booking-com15) (free tier)

### Run

```bash
# CLI mode (interactive conversation)
poetry run python main.py

# Web UI mode (Streamlit)
poetry run streamlit run app.py
```

## Project Structure

```
trip_planner/
├── main.py                    # Main orchestrator (TripPlannerCrew)
├── agents.py                  # 6 CrewAI agent definitions
├── tasks.py                   # Task definitions with Pydantic models
├── a2a_protocol.py            # A2A message protocol implementation
├── agent_cards.py             # Agent metadata & capability cards
├── config.yaml                # Configuration (models, budgets, protocol)
├── app.py                     # Streamlit web UI
├── run_ui.bat                 # Windows shortcut for Streamlit
│
├── mcp_servers/               # MCP Server (tool provider)
│   └── trip_planner_mcp_server.py   # Unified server (13 tools)
│
├── tools/                     # CrewAI tool wrappers
│   ├── __init__.py            # Tool exports
│   ├── mcp_tools.py           # MCP client + direct API tools
│   ├── searchtool.py          # Web search tools
│   └── calculatortool.py      # Budget calculator
│
├── utils/                     # Utilities
│   ├── itinerary_validator.py # Day-count validation
│   ├── cache_manager.py       # API response caching
│   └── api_resilience.py      # Retry/fallback logic
│
├── tests/                     # Test suite
├── experiments/               # Research experiment runners & results
├── papers/                    # Academic paper (LaTeX)
├── docs/                      # Additional documentation
│
├── pyproject.toml             # Poetry dependencies
├── poetry.lock                # Locked dependencies
├── .env.example               # Environment template
└── .gitignore                 # Git ignore rules
```

## How It Works

### Workflow (6 Phases)

1. **Conversation** — Agent asks user questions one-by-one (destination, dates, budget, interests)
2. **Extraction** — Structures conversation into JSON with budget validation
3. **Flight Search** — Calls Booking.com/Kiwi.com APIs for real flight data
4. **Hotel Search** — Calls Booking.com API for hotels, reviews, nearby attractions
5. **Attraction Search** — Uses Serper (Google) for activities & restaurants
6. **Coordination** — Combines all data into a detailed day-by-day itinerary

### MCP Server

The unified MCP server (`mcp_servers/trip_planner_mcp_server.py`) exposes 13 tools:

| Tool | API | Purpose |
|------|-----|---------|
| `search_flights_kiwi` | Kiwi.com | Cheap flight search |
| `search_cheap_flights` | Kiwi.com | Unified flight search |
| `search_hotels_comprehensive` | Booking.com | Full hotel search + reviews |
| `search_hotel_destination` | Booking.com | Get destination ID |
| `search_hotels_by_destination` | Booking.com | Search by dest_id |
| `get_hotel_reviews` | Booking.com | Hotel review scores |
| `get_attractions_near_hotel` | Booking.com | Nearby POIs |
| `search_accommodations_with_location` | Booking.com | GPS-based search |
| `search_car_rentals` | Booking.com | Car rental search |
| `search_internet` | Serper | General web search |
| `search_attractions` | Serper | Tourist attractions |
| `search_restaurants` | Serper | Restaurant search |
| `calculate` | Local | Math operations |

### A2A Protocol

Agents communicate via structured messages:

```json
{
  "sender": "preferences_extractor",
  "receiver": "flight_agent",
  "message_type": "request",
  "content": {"origin": "Islamabad", "destination": "Tokyo", ...},
  "conversation_id": "uuid",
  "priority": "high"
}
```

## Testing

```bash
# Run unit tests
poetry run pytest tests/

# Test MCP server independently
poetry run python mcp_servers/trip_planner_mcp_server.py
```

## Configuration

Edit `config.yaml` to customize:
- Agent models and temperatures
- Budget allocation percentages
- A2A protocol timeouts
- Search result limits

## References

- [CrewAI Documentation](https://docs.crewai.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP + CrewAI Integration](https://docs.crewai.com/en/mcp/overview)
