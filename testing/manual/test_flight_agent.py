"""
Test script to isolate and debug the flight search functionality.
Uses a simple agent to test the MCP flight tools directly.
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from textwrap import dedent

# Load environment variables
load_dotenv()

# Import the flight tools
from src.tools.mcp_tools import (
    search_comprehensive_flights,
    search_round_trip_flights,
    search_internet
)

# Set up API keys
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

print("="*70)
print("🧪 FLIGHT SEARCH AGENT TEST")
print("="*70)

# Create a simple test agent
llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

flight_test_agent = Agent(
    role="Flight Search Tester",
    goal="Test the flight search tools with specific parameters",
    backstory=dedent("""
        You are a testing agent. Your job is to call the flight search tool
        with the EXACT parameters given and report the results.
        
        IMPORTANT: Use IATA airport codes:
        - ISB = Islamabad
        - DOH = Doha
        - LHR = London
        - DXB = Dubai
        
        When searching, use these EXACT parameters:
        - source/origin: Use 3-letter IATA code (e.g., "ISB")
        - destination: Use 3-letter IATA code (e.g., "DOH")
        - departure_date: YYYY-MM-DD format
        - return_date: YYYY-MM-DD format
        - adults: Number of passengers (integer)
        
        If one tool fails, try the other flight search tool.
        Report exactly what the API returns - success or error.
    """),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[
        search_comprehensive_flights,
        search_round_trip_flights,
        search_internet
    ],
    max_iter=5
)

# Create a simple test task
test_task = Task(
    description=dedent("""
        Search for flights with these EXACT parameters:
        
        - Origin: ISB (Islamabad)
        - Destination: DOH (Doha)
        - Departure Date: 2025-12-15
        - Return Date: 2025-12-20
        - Adults: 1
        - Cabin Class: ECONOMY
        
        Steps:
        1. First try "Search comprehensive flights" tool with:
           - origin: "ISB"
           - destination: "DOH"
           - departure_date: "2025-12-15"
           - return_date: "2025-12-20"
           - adults: 1
           
        2. If that fails, try "Search round trip flights" tool with:
           - source: "ISB"
           - destination: "DOH"
           - departure_date: "2025-12-15"
           - return_date: "2025-12-20"
           - adults: 1
           - cabin_class: "ECONOMY"
        
        3. Report the EXACT output from the tool - whether success or error.
        
        DO NOT make up any flight data. Only report what the API returns.
    """),
    expected_output=dedent("""
        A report containing:
        1. Which tool was used
        2. The exact parameters passed
        3. The exact response from the API (success or error)
        4. If successful, list the flight options found
    """),
    agent=flight_test_agent
)

# Create and run the crew
crew = Crew(
    agents=[flight_test_agent],
    tasks=[test_task],
    process=Process.sequential,
    verbose=True
)

print("\n🚀 Starting flight search test...\n")
result = crew.kickoff()

print("\n" + "="*70)
print("📋 TEST RESULT")
print("="*70)
print(result)
print("="*70)

