# MCP Integration Setup Guide

This guide explains how to set up and use the Model Context Protocol (MCP) servers for the trip planner.

## What is MCP?

Model Context Protocol (MCP) is a standardized way for AI agents to access external tools and services. Instead of hardcoding API calls in your agent tools, MCP servers provide a clean interface that agents can discover and use dynamically.

## Architecture

```
CrewAI Agents
    ↓
MCP Servers (Stdio)
    ↓
RapidAPI Gateway
    ↓
Travel APIs (Kiwi.com, Booking.com, etc.)
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Using pip
pip install mcp requests

# Using poetry
poetry add mcp requests
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
OPENAI_API_KEY=your_openai_key
RAPIDAPI_KEY=your_rapidapi_key
SERPER_API_KEY=your_serper_key
```

### 3. Get RapidAPI Key

1. Go to [RapidAPI](https://rapidapi.com/)
2. Sign up for a free account
3. Subscribe to these APIs:
   - [Kiwi.com Cheap Flights](https://rapidapi.com/apiheya/api/kiwi-com-cheap-flights)
   - [Booking.com](https://rapidapi.com/booking-com15/api/booking-com15)
   - [Fly Scraper](https://rapidapi.com/apiheya/api/fly-scraper) (optional)
4. Copy your RapidAPI key from the dashboard

### 4. Test MCP Servers

Run each MCP server independently to test:

```bash
# Test flight search MCP server
python mcp_servers/flight_mcp_server.py

# Test hotel search MCP server  
python mcp_servers/hotel_mcp_server.py
```

## How It Works

### Agent Configuration

Agents are configured to use MCP servers via the `mcps` parameter:

```python
from crewai import Agent
from crewai.mcp import MCPServerStdio

agent = Agent(
    role="Flight Search Specialist",
    goal="Find optimal flights",
    backstory="Expert in finding flight deals",
    mcps=[
        MCPServerStdio(
            command="python",
            args=["mcp_servers/flight_mcp_server.py"],
            env={"RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY")},
            cache_tools_list=True
        )
    ],
    tools=[...other tools...]
)
```

### Tool Discovery

When the agent starts:
1. CrewAI launches the MCP server as a subprocess
2. The server advertises available tools via MCP protocol
3. Agent automatically discovers and can use these tools
4. Tools are called through standard MCP protocol
5. Results are returned to the agent

### Available Tools

#### Flight MCP Server
- `search_flights_kiwi`: Search Kiwi.com for cheap flights
- `search_cheap_flights`: Unified search across multiple APIs

#### Hotel MCP Server
- `search_car_rentals`: Search for rental cars on Booking.com
- `search_hotels_comprehensive`: Search for hotels with budget filtering
- `search_accommodations_with_location`: Location-based hotel search

## Usage in Agents

### Flight Search Agent

```python
flight_agent = Agent(
    role="Flight Search Specialist",
    goal="Find optimal flight options using MCP flight search tools",
    mcps=[
        MCPServerStdio(
            command="python",
            args=["mcp_servers/flight_mcp_server.py"],
            env={"RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY")},
            cache_tools_list=True
        )
    ]
)
```

The agent can now call:
```python
# Example tool call (done automatically by the agent)
search_cheap_flights(
    origin="NYC",
    destination="LON",
    departure_date="2025-06-16",
    return_date="2025-06-30",
    budget=1000,
    adults=1
)
```

### Hotel Search Agent

```python
hotel_agent = Agent(
    role="Hotel & Accommodation Specialist",
    goal="Find perfect accommodations using MCP hotel search tools",
    mcps=[
        MCPServerStdio(
            command="python",
            args=["mcp_servers/hotel_mcp_server.py"],
            env={"RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY")},
            cache_tools_list=True
        )
    ]
)
```

## API Limitations & Notes

### Kiwi.com API
- Best for finding cheap flights
- Supports flexible date searches
- Returns multiple options with quality scores
- Free tier has rate limits

### Booking.com API
- Car rental search is fully implemented
- Hotel search endpoint needs additional configuration
- Check RapidAPI documentation for latest endpoints

### Fly-Scraper API
- Requires two-step process:
  1. First search to get session/itinerary IDs
  2. Use IDs to get detailed flight info
- Currently configured but needs session management

## Troubleshooting

### MCP Server Won't Start
- Check Python path is correct
- Verify `mcp` library is installed
- Check for syntax errors in MCP server files

### API Returns Errors
- Verify RAPIDAPI_KEY is set correctly
- Check API subscription status on RapidAPI
- Review rate limits for your plan

### Agent Can't Find Tools
- Ensure MCP server path is correct (relative to project root)
- Check server starts successfully when run manually
- Enable verbose mode: `verbose=True` in Agent

### Connection Timeout
- Default timeout is 30 seconds
- Increase with: `cache_tools_list=True` to reduce reconnections
- Check network connectivity to RapidAPI

## Development

### Adding New Tools

1. Add function to MCP server:
```python
def search_new_api(...):
    # Implementation
    return results
```

2. Register in `list_tools()`:
```python
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_new_api",
            description="...",
            inputSchema={...}
        )
    ]
```

3. Add handler in `call_tool()`:
```python
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    if name == "search_new_api":
        result = search_new_api(**arguments)
        return [TextContent(type="text", text=result)]
```

### Testing Individual Tools

```python
# Test outside of MCP context
from mcp_servers.flight_mcp_server import search_cheap_flights

result = search_cheap_flights(
    origin="NYC",
    destination="LAX",
    departure_date="2025-12-20",
    adults=2
)
print(result)
```

## Benefits of MCP Approach

1. **Separation of Concerns**: API logic separate from agent logic
2. **Reusability**: Same MCP server can be used by multiple agents
3. **Dynamic Discovery**: Agents automatically find available tools
4. **Standardized Protocol**: Tools follow MCP standard
5. **Easy Testing**: Test MCP servers independently
6. **Scalability**: Add new APIs without changing agent code

## References

- [CrewAI MCP Documentation](https://docs.crewai.com/en/mcp/overview)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [RapidAPI Documentation](https://docs.rapidapi.com/)

## Next Steps

1. Configure your `.env` file with API keys
2. Test MCP servers independently
3. Run the trip planner with MCP-enabled agents
4. Monitor agent tool usage in verbose mode
5. Add additional APIs as needed
