"""
Trip Planner with A2A Protocol and MCP Integration

This is the main orchestration file that brings together:
- Agent-to-Agent (A2A) communication protocol
- Model Context Protocol (MCP) tool integration
- Multi-agent workflow for trip planning
"""

import os
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from crewai import Crew, Process
from textwrap import dedent
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple

from agents import TripPlannerAgents
from tasks import TripPlannerTasks
from a2a_protocol import A2AProtocol, A2AMessage, MessageType
from agent_cards import AGENT_REGISTRY

# Import utility modules for enhanced functionality
from utils.itinerary_validator import (
    validate_day_count, 
    regenerate_if_incomplete,
    extract_trip_duration_from_extraction,
    add_completion_notice
)
from utils.cache_manager import get_cache

# Load environment variables from .env file
load_dotenv()

# Set up API keys
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
#os.environ["OPENAI_ORGANIZATION"] = os.getenv("OPENAI_ORGANIZATION_ID", "")
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY", "")


class TripPlannerCrew:
    """
    Main Trip Planner Crew orchestrating A2A communication and MCP tool usage
    
    Workflow:
    1. Conversational Agent gathers user requirements
    2. Preferences Extractor structures the data (A2A message)
    3. Search Agents (Flight, Hotel, Attraction) work in parallel with MCP tools
    4. Itinerary Coordinator synthesizes everything into final plan
    """
    
    def __init__(self, parallel_mode: bool = True):
        self.agents_class = TripPlannerAgents()
        self.tasks_class = TripPlannerTasks()
        self.a2a_protocol = A2AProtocol()
        self.parallel_mode = parallel_mode  # Enable parallel API searches
        self._extraction_output = None  # Store for validation
        
        # Initialize agents
        self.conversational_agent = self.agents_class.conversational_agent()
        self.preferences_extractor = self.agents_class.preferences_extractor_agent()
        self.flight_agent = self.agents_class.flight_search_agent()
        self.hotel_agent = self.agents_class.hotel_agent()
        self.attraction_agent = self.agents_class.attraction_agent()
        self.coordinator_agent = self.agents_class.itinerary_coordinator_agent()
        
        print("✅ All agents initialized")
        print(f"✅ A2A Protocol active with {len(AGENT_REGISTRY)} registered agent cards")
        print(f"✅ Parallel mode: {'ENABLED' if parallel_mode else 'DISABLED'}")
    
    def _is_budget_too_low(self, extraction_output: str, conversation_transcript: str) -> bool:
        """
        Check if the budget is too low for the trip.
        
        Uses simple heuristics:
        - International trips need at least $500 per person
        - Flights alone typically cost $300-$1500
        - Hotels typically cost $50-$200/night minimum
        """
        import re
        import json
        
        # Try to parse budget from extraction output
        try:
            # First, try to parse as JSON directly
            try:
                # Look for JSON block in the output - match complete JSON object
                json_match = re.search(r'\{(?:[^{}]|\{[^{}]*\})*"total_budget"(?:[^{}]|\{[^{}]*\})*\}', extraction_output, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    total_budget = float(data.get('total_budget', 0))
                    print(f"[DEBUG] Parsed budget from JSON: ${total_budget}")
                else:
                    # Fallback: regex search
                    budget_match = re.search(r'"total_budget":\s*(\d+(?:\.\d+)?)', extraction_output)
                    if budget_match:
                        total_budget = float(budget_match.group(1))
                        print(f"[DEBUG] Parsed budget from regex: ${total_budget}")
                    else:
                        print("[DEBUG] Could not find budget in extraction output")
                        return False  # Can't determine budget, proceed
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON decode error: {e}")
                # Fallback: regex search
                budget_match = re.search(r'"total_budget":\s*(\d+(?:\.\d+)?)', extraction_output)
                if budget_match:
                    total_budget = float(budget_match.group(1))
                    print(f"[DEBUG] Parsed budget from regex fallback: ${total_budget}")
                else:
                    print("[DEBUG] Could not find budget in extraction output (fallback)")
                    return False  # Can't determine budget, proceed
            
            # Look for trip duration
            duration_match = re.search(r'"trip_duration":\s*(\d+)', extraction_output)
            if duration_match:
                trip_duration = int(duration_match.group(1))
            else:
                trip_duration = 5  # Default assumption
            
            # Look for number of travelers
            travelers_match = re.search(r'"total_travelers":\s*(\d+)', extraction_output)
            if travelers_match:
                num_travelers = int(travelers_match.group(1))
            else:
                num_travelers = 1
            
            # Check for explicit budget warning from agent
            if "BUDGET_TOO_LOW" in extraction_output:
                return True
            
            # Calculate minimum realistic budget
            # Minimum: $300 flights + $50/night hotels + $30/day activities per person
            min_flight_cost = 300 * num_travelers
            min_hotel_cost = 50 * trip_duration
            min_daily_cost = 30 * trip_duration * num_travelers
            min_total = min_flight_cost + min_hotel_cost + min_daily_cost
            
            # If budget is less than 60% of minimum, it's too low
            if total_budget < (min_total * 0.6):
                return True
            
            # Specific check: if budget < $200 for any international trip, reject
            if total_budget < 200:
                return True
                
            return False
            
        except Exception as e:
            print(f"Budget validation error: {e}")
            return False  # On error, proceed with trip planning
    
    def _get_budget_error_message(self, extraction_output: str, conversation_transcript: str) -> str:
        """
        Generate a helpful error message when budget is too low.
        """
        import re
        import json
        
        # Extract details - try JSON first, then regex fallback
        try:
            json_match = re.search(r'\{[^}]*"total_budget"[^}]*\}', extraction_output, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                total_budget = float(data.get('total_budget', 0))
                trip_duration = int(data.get('trip_duration', 5))
                num_travelers = int(data.get('total_travelers', 1))
                destination = data.get('destination', 'your destination')
                origin = data.get('origin', 'your origin')
            else:
                raise ValueError("No JSON found")
        except (json.JSONDecodeError, ValueError):
            # Fallback to regex
            budget_match = re.search(r'"total_budget":\s*(\d+(?:\.\d+)?)', extraction_output)
            total_budget = float(budget_match.group(1)) if budget_match else 0
            
            duration_match = re.search(r'"trip_duration":\s*(\d+)', extraction_output)
            trip_duration = int(duration_match.group(1)) if duration_match else 5
            
            travelers_match = re.search(r'"total_travelers":\s*(\d+)', extraction_output)
            num_travelers = int(travelers_match.group(1)) if travelers_match else 1
            
            destination_match = re.search(r'"destination":\s*"([^"]+)"', extraction_output)
            destination = destination_match.group(1) if destination_match else "your destination"
            
            origin_match = re.search(r'"origin":\s*"([^"]+)"', extraction_output)
            origin = origin_match.group(1) if origin_match else "your origin"
        
        # Calculate recommended minimum
        min_flight = 400 * num_travelers
        min_hotel = 60 * trip_duration
        min_daily = 40 * trip_duration * num_travelers
        recommended_min = min_flight + min_hotel + min_daily
        
        message = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        ❌ BUDGET TOO LOW - CANNOT PROCEED                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

I'm sorry, but your budget of ${total_budget:.0f} is too low for a trip from {origin} to {destination}.

📊 YOUR REQUEST:
   • Origin: {origin}
   • Destination: {destination}
   • Duration: {trip_duration} days
   • Travelers: {num_travelers} person(s)
   • Your Budget: ${total_budget:.0f}

💰 REALISTIC COST BREAKDOWN:
   • Flights: ${min_flight:.0f} minimum (${min_flight/num_travelers:.0f}/person round-trip)
   • Hotels: ${min_hotel:.0f} minimum (${min_hotel/trip_duration:.0f}/night for {trip_duration} nights)
   • Daily expenses: ${min_daily:.0f} (food, transport, activities)
   
   📌 MINIMUM RECOMMENDED BUDGET: ${recommended_min:.0f}

🔧 YOUR OPTIONS:
   1. Increase your budget to at least ${recommended_min:.0f}
   2. Reduce trip duration to {max(1, int(total_budget / 150))} days
   3. Choose a closer/cheaper destination
   4. Reduce number of travelers

Please restart with a more realistic budget. International travel from Pakistan 
typically costs at least $800-$1500 per person for a week-long trip.

╔══════════════════════════════════════════════════════════════════════════════╗
║              Run 'python main.py' again with a revised budget                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        return message
    
    def _run_search_crew_parallel(
        self, 
        extraction_task, 
        conversation_id: str,
        timeout: int = 180
    ) -> Tuple[Any, Any, Any]:
        """
        Run flight, hotel, and attraction searches in parallel using ThreadPoolExecutor.
        
        This provides ~2-3x speedup compared to sequential execution when all APIs respond.
        Individual failures don't block other searches.
        
        Args:
            extraction_task: Completed extraction task with user preferences
            conversation_id: A2A conversation ID
            timeout: Maximum time to wait for each search (seconds)
            
        Returns:
            Tuple of (flight_result, hotel_result, attraction_result)
        """
        print("\n🔄 Running searches in PARALLEL mode...")
        start_time = time.time()
        
        # Create search tasks
        flight_task = self.tasks_class.flight_search_task(
            agent=self.flight_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        hotel_task = self.tasks_class.hotel_search_task(
            agent=self.hotel_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        attraction_task = self.tasks_class.attraction_search_task(
            agent=self.attraction_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        # Define executor functions for each search
        def run_flight_search():
            print("   ✈️  Starting flight search...")
            crew = Crew(agents=[self.flight_agent], tasks=[flight_task], process=Process.sequential, verbose=True)
            result = crew.kickoff()
            print("   ✈️  Flight search completed")
            return flight_task, result
        
        def run_hotel_search():
            print("   🏨 Starting hotel search...")
            crew = Crew(agents=[self.hotel_agent], tasks=[hotel_task], process=Process.sequential, verbose=True)
            result = crew.kickoff()
            print("   🏨 Hotel search completed")
            return hotel_task, result
        
        def run_attraction_search():
            print("   🎭 Starting attraction search...")
            crew = Crew(agents=[self.attraction_agent], tasks=[attraction_task], process=Process.sequential, verbose=True)
            result = crew.kickoff()
            print("   🎭 Attraction search completed")
            return attraction_task, result
        
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(run_flight_search): "flight",
                executor.submit(run_hotel_search): "hotel",
                executor.submit(run_attraction_search): "attraction"
            }
            
            for future in as_completed(futures, timeout=timeout):
                task_type = futures[future]
                try:
                    task, result = future.result(timeout=timeout)
                    results[task_type] = (task, result)
                except Exception as e:
                    print(f"   ⚠️ {task_type} search failed: {e}")
                    # Store the task even if result failed
                    if task_type == "flight":
                        results[task_type] = (flight_task, None)
                    elif task_type == "hotel":
                        results[task_type] = (hotel_task, None)
                    else:
                        results[task_type] = (attraction_task, None)
        
        elapsed = time.time() - start_time
        print(f"\n✅ Parallel searches completed in {elapsed:.1f}s")
        
        # Return tasks in consistent order
        return (
            results.get("flight", (flight_task, None))[0],
            results.get("hotel", (hotel_task, None))[0],
            results.get("attraction", (attraction_task, None))[0]
        )
    
    def _validate_and_enhance_itinerary(
        self, 
        itinerary: str, 
        extraction_output: str
    ) -> str:
        """
        Validate the itinerary day count and add completion notice if incomplete.
        
        This replaces the prompt-based "CRITICAL: WRITE ALL DAYS" approach with
        programmatic validation.
        
        Args:
            itinerary: Generated itinerary text
            extraction_output: Extraction task output (for trip duration)
            
        Returns:
            Validated (and possibly enhanced) itinerary
        """
        # Extract expected trip duration
        expected_days = extract_trip_duration_from_extraction(extraction_output)
        
        if expected_days is None:
            print("   ⚠️ Could not determine trip duration for validation")
            return itinerary
        
        # Validate day count
        is_valid, actual_count, found_days = validate_day_count(itinerary, expected_days)
        
        if is_valid:
            print(f"   ✅ Itinerary validation passed: {actual_count}/{expected_days} days found")
            return itinerary
        else:
            print(f"   ⚠️ Itinerary validation: {actual_count}/{expected_days} days found")
            print(f"      Missing days: {set(range(1, expected_days + 1)) - set(found_days)}")
            
            # Add completion notice for user
            return add_completion_notice(itinerary, actual_count, expected_days)
    
    def have_conversation(self, initial_input: str, conversation_id: str) -> str:
        """
        Have an interactive conversation with the conversational agent
        
        Args:
            initial_input: User's initial trip request
            conversation_id: Unique conversation ID
            
        Returns:
            Complete conversation transcript
        """
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        conversation_history = []
        
        # System prompt for the conversational agent
        system_prompt = dedent("""
            You are a friendly, knowledgeable travel assistant who loves helping people 
            plan their dream trips. You engage in warm, natural conversations.
            
            IMPORTANT: Ask questions ONE AT A TIME, not all at once. Be conversational and natural.
            
            You need to gather this information IN ORDER:
            1. **Destination**: Where do they want to go? (if not already mentioned) 
            2. *People* Ask for how many people are traveling with you
            3. **Origin**: Where are they traveling from?
            4. **Dates**: When do they want to travel (start and end dates)? Are dates flexible?
            5. **Budget**: What is their total budget for the entire trip?
            6. **Interests**: What activities and experiences interest them? (museums, food, adventure, relaxation, etc.)
            7. **Travel Style**: Do they prefer luxury, budget-friendly, or moderate accommodations and experiences?
            8. **Special Requirements**: Any dietary restrictions, accessibility needs, or other special considerations?
            
            After the user answers each question one by one **VERY IMPORTANT** ASK THESE QUESTIONS ONE BY ONE dont jumble up questions, 
            ask the NEXT question. Keep it conversational.
            
            Once you have ALL the information needed, say "CONVERSATION_COMPLETE" at the end of your message.
        """)
        
        conversation_history.append(SystemMessage(content=system_prompt))
        conversation_history.append(HumanMessage(content=initial_input))
        
        print("\n" + "="*80)
        print("💬 INTERACTIVE CONVERSATION WITH TRAVEL ASSISTANT")
        print("="*80)
        print("(Type your responses below. The agent will let you know when enough info is gathered.)")
        print("="*80 + "\n")
        
        full_transcript = f"User: {initial_input}\n\n"
        
        while True:
            # Get AI response
            response = llm.invoke(conversation_history)
            agent_message = response.content
            
            print(f"\n🤖 Agent: {agent_message}\n")
            full_transcript += f"Agent: {agent_message}\n\n"
            
            conversation_history.append(AIMessage(content=agent_message))
            
            # Check if conversation is complete
            if "CONVERSATION_COMPLETE" in agent_message:
                print("\n✅ Travel assistant has gathered all necessary information!\n")
                break
            
            # Get user response
            user_response = input("You: ").strip()
            
            if not user_response:
                user_response = "Please continue with the information you have."
            
            full_transcript += f"User: {user_response}\n\n"
            conversation_history.append(HumanMessage(content=user_response))
            
            # Safety check - max 10 conversation turns
            if len(conversation_history) > 22:  # 1 system + 10 turns * 2 messages + 1
                print("\n⚠️  Maximum conversation length reached. Proceeding with available information.\n")
                break
        
        return full_transcript
    
    def plan_trip(self, user_input: str) -> str:
        """
        Main method to plan a trip based on user input
        
        Args:
            user_input: Initial user message about their trip
            
        Returns:
            Complete travel itinerary
        """
        # Generate unique conversation ID for A2A tracking
        conversation_id = str(uuid.uuid4())
        
        print(f"\n{'='*80}")
        print(f"🌍 TRIP PLANNER STARTED")
        print(f"{'='*80}")
        print(f"Conversation ID: {conversation_id}")
        print(f"{'='*80}\n")
        
        # Start A2A conversation
        self.a2a_protocol.start_conversation(conversation_id, {"user_input": user_input})
        
        # ============================================
        # PHASE 1: Interactive Conversation
        # ============================================
        
        print("\n🤖 PHASE 1: Starting conversation with Travel Assistant...\n")
        conversation_transcript = self.have_conversation(user_input, conversation_id)
        
        # ============================================
        # PHASE 2: Extract Preferences & Validate Budget
        # ============================================
        
        print("\n🔍 PHASE 2: Extracting structured preferences and validating budget...")
        
        # Create conversation task
        conversation_task = self.tasks_class.conversation_task(
            agent=self.conversational_agent,
            user_input=conversation_transcript,
            conversation_id=conversation_id
        )
        
        # Create extraction task
        extraction_task = self.tasks_class.extraction_task(
            agent=self.preferences_extractor,
            conversation_id=conversation_id,
            conversation_task=conversation_task
        )
        
        # Run extraction FIRST to validate budget
        print("\n💰 Validating budget before proceeding...")
        
        extraction_crew = Crew(
            agents=[self.conversational_agent, self.preferences_extractor],
            tasks=[conversation_task, extraction_task],
            process=Process.sequential,
            verbose=True
        )
        
        extraction_result = extraction_crew.kickoff()
        extraction_output = str(extraction_result)
        self._extraction_output = extraction_output  # Store for validation
        
        # Check for budget issues
        if self._is_budget_too_low(extraction_output, conversation_transcript):
            print("\n" + "="*80)
            print("❌ BUDGET TOO LOW - CANNOT PROCEED")
            print("="*80)
            
            budget_error_message = self._get_budget_error_message(extraction_output, conversation_transcript)
            
            print(budget_error_message)
            print("="*80 + "\n")
            
            # End conversation
            self.a2a_protocol.end_conversation(conversation_id)
            
            return budget_error_message
        
        print("\n✅ Budget validated! Proceeding with trip planning...\n")
        
        # ============================================
        # PHASE 3: Parallel Search with MCP Tools
        # ============================================
        
        print("\n✈️  PHASE 3: Flight Search Agent using MCP-style search tools...")
        flight_task = self.tasks_class.flight_search_task(
            agent=self.flight_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        print("\n🏨 PHASE 4: Hotel Agent using MCP-style search tools...")
        hotel_task = self.tasks_class.hotel_search_task(
            agent=self.hotel_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        print("\n🎭 PHASE 5: Attraction Agent using MCP-style search tools...")
        attraction_task = self.tasks_class.attraction_search_task(
            agent=self.attraction_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        # ============================================
        # PHASE 4: Coordination & Itinerary Creation
        # ============================================
        
        print("\n📋 PHASE 6: Itinerary Coordinator synthesizing all data...")
        coordination_task = self.tasks_class.coordination_task(
            agent=self.coordinator_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task,
            flight_task=flight_task,
            hotel_task=hotel_task,
            attraction_task=attraction_task
        )
        
        # ============================================
        # Create and Execute Main Crew
        # ============================================
        
        print("\n🚀 Assembling crew and executing workflow...\n")
        
        crew = Crew(
            agents=[
                self.flight_agent,
                self.hotel_agent,
                self.attraction_agent,
                self.coordinator_agent
            ],
            tasks=[
                flight_task,
                hotel_task,
                attraction_task,
                coordination_task
            ],
            process=Process.sequential,
            verbose=True
        )
        
        # Execute the crew
        result = crew.kickoff()
        
        # Validate itinerary day count
        result_str = str(result)
        if self._extraction_output:
            result_str = self._validate_and_enhance_itinerary(result_str, self._extraction_output)
        
        # End A2A conversation
        self.a2a_protocol.end_conversation(conversation_id)
        
        print(f"\n{'='*80}")
        print("✅ TRIP PLANNING COMPLETED")
        print(f"{'='*80}\n")
        
        # Display A2A protocol statistics
        conversation_history = self.a2a_protocol.get_conversation_history(conversation_id)
        print(f"📊 A2A Protocol Statistics:")
        print(f"   - Total messages exchanged: {len(conversation_history)}")
        print(f"   - Conversation ID: {conversation_id}")
        print(f"{'='*80}\n")
        
        return result_str
    
    def plan_trip_from_transcript(self, conversation_transcript: str, conversation_id: str) -> str:
        """
        Plan a trip from an existing conversation transcript (for Streamlit UI)
        
        Args:
            conversation_transcript: Complete conversation text
            conversation_id: Unique conversation ID
            
        Returns:
            Complete travel itinerary
        """
        # Start A2A conversation
        self.a2a_protocol.start_conversation(conversation_id, {"transcript": conversation_transcript})
        
        # Create a simple task wrapper with the conversation transcript
        conversation_task = self.tasks_class.conversation_task(
            agent=self.conversational_agent,
            user_input=conversation_transcript,
            conversation_id=conversation_id
        )
        
        # Extraction task
        extraction_task = self.tasks_class.extraction_task(
            agent=self.preferences_extractor,
            conversation_id=conversation_id,
            conversation_task=conversation_task
        )
        
        # Run extraction FIRST to validate budget
        extraction_crew = Crew(
            agents=[self.conversational_agent, self.preferences_extractor],
            tasks=[conversation_task, extraction_task],
            process=Process.sequential,
            verbose=True
        )
        
        extraction_result = extraction_crew.kickoff()
        extraction_output = str(extraction_result)
        self._extraction_output = extraction_output  # Store for validation
        
        # Debug: Print extraction output to see what we're parsing
        print("\n[DEBUG - Second check] Extraction output (first 500 chars):")
        print(extraction_output[:500])
        print("...\n")
        
        # Check for budget issues
        if self._is_budget_too_low(extraction_output, conversation_transcript):
            self.a2a_protocol.end_conversation(conversation_id)
            return self._get_budget_error_message(extraction_output, conversation_transcript)
        
        # Search tasks
        flight_task = self.tasks_class.flight_search_task(
            agent=self.flight_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        hotel_task = self.tasks_class.hotel_search_task(
            agent=self.hotel_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        attraction_task = self.tasks_class.attraction_search_task(
            agent=self.attraction_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task
        )
        
        # Coordination task
        coordination_task = self.tasks_class.coordination_task(
            agent=self.coordinator_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task,
            flight_task=flight_task,
            hotel_task=hotel_task,
            attraction_task=attraction_task
        )
        
        # Create and execute crew (without extraction tasks, already done)
        crew = Crew(
            agents=[
                self.flight_agent,
                self.hotel_agent,
                self.attraction_agent,
                self.coordinator_agent
            ],
            tasks=[
                flight_task,
                hotel_task,
                attraction_task,
                coordination_task
            ],
            process=Process.sequential,
            verbose=True
        )
        
        # Execute the crew
        result = crew.kickoff()
        
        # End A2A conversation
        self.a2a_protocol.end_conversation(conversation_id)
        
        return str(result)


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
    
    # Validate API keys before starting
    if not validate_api_keys():
        return
    
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
    
    # Get user input
    print("\n📝 Please describe your ideal trip:")
    print("   (e.g., 'I want to visit Paris for 5 days with a $3000 budget.')\n")
    
    user_input = input("Your trip request: ").strip()
    
    if not user_input:
        # Use example if no input provided
        user_input = dedent("""
            I want to plan a trip to Tokyo, Japan. I'm traveling from New York 
            and would like to go in March 2024 for about 7 days. My budget is around 
            $4000. I'm interested in experiencing Japanese culture, trying authentic 
            food, visiting temples, and maybe seeing Mt. Fuji. I prefer moderate 
            accommodation, nothing too fancy but comfortable. I like a good balance 
            of activities - not too rushed but I want to see the highlights.
        """).strip()
        print(f"\n💡 Using example trip request:\n{user_input}\n")
    
    # Initialize and run trip planner
    trip_planner = TripPlannerCrew()
    itinerary = trip_planner.plan_trip(user_input)
    
    # Display final itinerary
    print("\n" + "="*80)
    print("📋 YOUR COMPLETE TRAVEL ITINERARY")
    print("="*80 + "\n")
    print(itinerary)
    print("\n" + "="*80)
    print("✨ Happy Travels! ✨")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

