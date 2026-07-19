"""
CLI Entry Point for AI Trip Planner
Usage: python run_cli.py
"""

import os
from dotenv import load_dotenv
from textwrap import dedent

load_dotenv()


def validate_api_keys():
    """Validate that all required API keys are present at startup."""
    required_keys = {
        "OPENAI_API_KEY": "OpenAI (powers all agents)",
        "SERPER_API_KEY": "Serper (web search for attractions & restaurants)",
        "RAPIDAPI_KEY": "RapidAPI (flights via Kiwi.com + hotels via Booking.com)",
    }

    missing = []
    for key, description in required_keys.items():
        if not os.getenv(key):
            missing.append(f"  - {key} ({description})")

    if missing:
        print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                      ❌ MISSING API KEYS                                ║
╚══════════════════════════════════════════════════════════════════════════╝
""")
        print("The following required API keys are missing:\n")
        print("\n".join(missing))
        print(f"""
To fix this:
  1. Copy .env.example to .env:  cp .env.example .env
  2. Fill in your API keys in .env
  3. Run the planner again

Need API keys?
  - OpenAI:   https://platform.openai.com/api-keys
  - Serper:   https://serper.dev/
  - RapidAPI: https://rapidapi.com/ (subscribe to Kiwi.com + Booking.com APIs)
""")
        return False
    return True


def main():
    """Main entry point for the trip planner"""

    if not validate_api_keys():
        return

    from src.orchestrator import TripPlannerCrew

    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║              🌍 AI TRIP PLANNER WITH A2A & MCP 🌍                   ║
    ║                                                                      ║
    ║  Features:                                                          ║
    ║  ✅ Agent-to-Agent (A2A) Communication Protocol                     ║
    ║  ✅ Model Context Protocol (MCP) Tool Integration                   ║
    ║  ✅ Multi-Agent Collaborative Planning                              ║
    ║  ✅ Intelligent Budget Optimization                                 ║
    ║  ✅ Comprehensive Itinerary Generation                              ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """)

    print("\n📝 Please describe your ideal trip:")
    print("   (e.g., 'I want to visit Paris for 5 days with a $3000 budget.')\n")

    user_input = input("Your trip request: ").strip()

    if not user_input:
        user_input = dedent("""
            I want to plan a trip to Tokyo, Japan. I'm traveling from New York 
            and would like to go in March 2024 for about 7 days. My budget is around 
            $4000. I'm interested in experiencing Japanese culture, trying authentic 
            food, visiting temples, and maybe seeing Mt. Fuji. I prefer moderate 
            accommodation, nothing too fancy but comfortable. I like a good balance 
            of activities - not too rushed but I want to see the highlights.
        """).strip()
        print(f"\n💡 Using example trip request:\n{user_input}\n")

    trip_planner = TripPlannerCrew()
    itinerary = trip_planner.plan_trip(user_input)

    print("\n" + "="*80)
    print("📋 YOUR COMPLETE TRAVEL ITINERARY")
    print("="*80 + "\n")
    print(itinerary)
    print("\n" + "="*80)
    print("✨ Happy Travels! ✨")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
