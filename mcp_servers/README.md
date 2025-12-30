# MCP Server

This directory contains the unified Model Context Protocol (MCP) server for the trip planner application.

## Unified MCP Server (`trip_planner_mcp_server.py`)

All travel-related tools are now consolidated into a single MCP server that provides:

### Flight Search Tools
- **`search_flights_kiwi`**: Search flights using Kiwi.com API with flexible options
- **`search_cheap_flights`**: Unified search combining multiple APIs for best results

### Hotel & Accommodation Tools
- **`search_hotels_comprehensive`**: Search for hotels with budget filtering
- **`search_accommodations_with_location`**: Location-based accommodation search using GPS coordinates
- **`search_car_rentals`**: Search for rental cars using Booking.com API

### Web Search Tools
- **`search_internet`**: General web search using Serper API
- **`search_attractions`**: Search for tourist attractions and activities
- **`search_restaurants`**: Search for restaurants with cuisine and budget filters

### Calculator Tool
- **`calculate`**: Perform mathematical calculations for budget planning

## Running the MCP Server

### Direct Execution (Testing)
```bash
python mcp_servers/trip_planner_mcp_server.py
```

### With MCP Client (Production)
The server communicates via JSON-RPC over stdio. The `tools/mcp_tools.py` module provides a client that handles all communication automatically.

## Configuration

### Environment Variables
Set your API keys:
```bash
# Windows PowerShell
$env:RAPIDAPI_KEY="your_rapidapi_key_here"
$env:SERPER_API_KEY="your_serper_api_key_here"

# Linux/Mac
export RAPIDAPI_KEY="your_rapidapi_key_here"
export SERPER_API_KEY="your_serper_api_key_here"
```

Or create a `.env` file:
```
RAPIDAPI_KEY=your_rapidapi_key_here
SERPER_API_KEY=your_serper_api_key_here
```

## API Documentation

### Flight APIs (via RapidAPI)
- **Kiwi.com** - For cheap flight searches with flexible options

### Hotel APIs (via RapidAPI)
- **Booking.com** - For car rentals and hotel searches

### Web Search API
- **Serper** - For Google search results (attractions, restaurants, general web)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   CrewAI Agents                      │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                 tools/mcp_tools.py                   │
│              (Langchain Tool Wrappers)               │
│                                                      │
│  - search_round_trip_flights()                       │
│  - search_comprehensive_flights()                    │
│  - search_hotels_comprehensive()                     │
│  - search_accommodations_with_location()             │
│  - search_car_rentals()                             │
│  - search_internet()                                 │
│  - search_attractions()                              │
│  - search_restaurants()                              │
│  - calculate()                                       │
└────────────────────────┬────────────────────────────┘
                         │ JSON-RPC over stdio
                         ▼
┌─────────────────────────────────────────────────────┐
│        mcp_servers/trip_planner_mcp_server.py       │
│                 (Unified MCP Server)                 │
│                                                      │
│  API Integrations:                                   │
│  - Kiwi.com (flights)                               │
│  - Booking.com (hotels, car rentals)                │
│  - Serper (web search)                              │
│  - Calculator (math operations)                      │
└─────────────────────────────────────────────────────┘
```

## Dependencies

```bash
pip install mcp requests python-dotenv
```

Or add to `pyproject.toml`:
```toml
[tool.poetry.dependencies]
mcp = "^1.0.0"
requests = "^2.32.0"
python-dotenv = "^1.0.0"
```
