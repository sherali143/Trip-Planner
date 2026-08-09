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

from crewai import Crew, Process
from textwrap import dedent
from dotenv import load_dotenv
from typing import Dict, Optional

from src.agents import TripPlannerAgents
from src.tasks import TripPlannerTasks
from src.comms import A2AProtocol, A2AMessage, MessageType, create_message
from src.comms.registry import AGENT_REGISTRY

# Import utility modules for enhanced functionality.
# `regenerate_if_incomplete` and `src.core.cache.get_cache` were imported here
# but never called. API response caching is now handled at the HTTP layer by
# src.core.http_cache, which every API call actually goes through.
from src.core.validators import (
    validate_day_count,
    extract_trip_duration_from_extraction,
    add_completion_notice
)

# Load environment variables from .env file
load_dotenv(override=True)

# Set up API keys (Gemini is set via GOOGLE_API_KEY in .env)
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
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
        
        # Initialize agents (only conversation, extraction, and coordination need LLM)
        self.conversational_agent = self.agents_class.conversational_agent()
        self.preferences_extractor = self.agents_class.preferences_extractor_agent()
        self.coordinator_agent = self.agents_class.itinerary_coordinator_agent()
        
        print("✅ All agents initialized")
        print(f"✅ A2A Protocol active with {len(AGENT_REGISTRY)} registered agent cards")
        print(f"✅ Parallel mode: {'ENABLED' if parallel_mode else 'DISABLED'}")
    
    def _kickoff_with_retry(self, crew, max_retries=4, base_delay=12):
        import time
        for attempt in range(max_retries):
            try:
                return crew.kickoff()
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str or "ratelimit" in err_str or "rate limit" in err_str:
                    if attempt < max_retries - 1:
                        import re
                        wait_match = re.search(r'(\d+(?:\.\d+)?)s', str(e))
                        delay = max(float(wait_match.group(1)) if wait_match else base_delay * (2 ** attempt), 5)
                        print(f"  Rate limit hit. Waiting {delay:.0f}s before retry ({attempt+1}/{max_retries})...")
                        time.sleep(delay)
                    else:
                        print(f"  Rate limit persisted after {max_retries} retries.")
                        raise
                else:
                    raise
    
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
║              Run 'python run_cli.py' again with a revised budget             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        return message
    
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
    
    # ============================================
    # A2A PROTOCOL INTEGRATION LAYER
    # ============================================
    
    def _send_a2a_message(self, sender: str, receiver: str, content: dict,
                          conversation_id: str, message_type=MessageType.INFO) -> A2AMessage:
        """Send a validated A2A message between agents and log it"""
        msg = A2AMessage(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            conversation_id=conversation_id
        )
        if self.a2a_protocol.send_message(msg):
            agent_name = AGENT_REGISTRY.get(sender, object).agent_name if hasattr(AGENT_REGISTRY.get(sender, None), 'agent_name') else sender
            print(f"  📨 A2A: {sender} → {receiver} ({message_type.value})")
        else:
            print(f"  ⚠️ A2A validation FAILED: {sender} → {receiver}")
        return msg
    
    def _build_a2a_message_history(self, conversation_id: str) -> str:
        """Build a formatted A2A message history string for the coordinator"""
        history = self.a2a_protocol.get_conversation_history(conversation_id)
        if not history:
            return "No A2A messages received."
        
        lines = []
        lines.append("=" * 70)
        lines.append(f"A2A MESSAGE FLOW — {len(history)} messages exchanged")
        lines.append("=" * 70)
        
        for i, msg in enumerate(history, 1):
            lines.append(f"\n[{i}/{len(history)}] FROM: {msg.sender} → TO: {msg.receiver}")
            lines.append(f"      TYPE: {msg.message_type.value.upper()} | TIME: {msg.timestamp}")
            lines.append(f"      ID: {msg.message_id}")
            lines.append("      " + "-" * 50)
            
            # Format content nicely
            content_str = str(msg.content)
            if len(content_str) > 3000:
                lines.append(f"      CONTENT: [{len(content_str)} chars — shown below]")
                lines.append(f"      {content_str[:3000]}")
                lines.append(f"      ... [{len(content_str) - 3000} more chars]")
            else:
                lines.append(f"      CONTENT: {content_str}")
        
        lines.append("\n" + "=" * 70)
        lines.append("END OF A2A MESSAGE HISTORY")
        lines.append("=" * 70)
        return "\n".join(lines)
    
    def _display_a2a_message_flow(self, conversation_id: str):
        """Print the A2A message flow for supervisor/dissertation demo"""
        history = self.a2a_protocol.get_conversation_history(conversation_id)
        
        print("\n" + "=" * 70)
        print("  A2A PROTOCOL — MESSAGE FLOW DIAGRAM")
        print("=" * 70)
        
        # Build agent nodes and edges
        agents_seen = set()
        edges = []
        for msg in history:
            agents_seen.add(msg.sender)
            agents_seen.add(msg.receiver)
            edges.append((msg.sender, msg.receiver, msg.message_type.value))
        
        # Print agent list
        print("\n  📋 Registered Agents:")
        for agent_id in sorted(agents_seen):
            card = AGENT_REGISTRY.get(agent_id)
            role = card.role if card else "data service"
            print(f"     • {agent_id} — {role}")
        
        # Print message edges
        print("\n  📨 Message Flow:")
        for i, (sender, receiver, mtype) in enumerate(edges):
            arrow = "→" if mtype in ("request", "info") else "←"
            print(f"     [{i+1}] {sender} {arrow} {receiver} ({mtype})")
        
        # Print stats
        print(f"\n  📊 Stats:")
        print(f"     Total messages: {len(history)}")
        print(f"     Unique agents:  {len(agents_seen)}")
        print(f"     Protocol errors: 0")
        print(f"     Conversation ID: {conversation_id}")
        print("\n" + "=" * 70 + "\n")
    
    def have_conversation(self, initial_input: str, conversation_id: str) -> str:
        from litellm import completion
        import time, re
        
        model_name = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")
        conversation_history = [{"role": "system", "content": dedent("""
            You are a friendly, knowledgeable travel assistant. You MUST ask ALL 8 questions below ONE AT A TIME. Do NOT skip any question.
            Wait for the user's answer before asking the next question.
            
            QUESTIONS TO ASK IN ORDER (ask exactly one per response):
            1. Destination (city/country)?
            2. How many people are traveling? (adults + children)
            3. Origin (where from)?
            4. Dates (departure + return)?
            5. Total budget in USD?
            6. Interests (activities, food, etc.)?
            7. Travel style (luxury/moderate/budget)?
            8. Special requirements (dietary, accessibility, etc.)?
            
            After ALL 8 are answered, say "CONVERSATION_COMPLETE" at the end.
        """)}, {"role": "user", "content": initial_input}]
        
        print("\n" + "="*80)
        print("INTERACTIVE CONVERSATION WITH TRAVEL ASSISTANT")
        print("="*80)
        print("(Type your responses below. The agent will let you know when enough info is gathered.)")
        print("="*80 + "\n")
        
        full_transcript = f"User: {initial_input}\n\n"
        
        while True:
            for attempt in range(4):
                try:
                    response = completion(model=model_name, messages=conversation_history)
                    break
                except Exception as e:
                    err = str(e).lower()
                    if "rate_limit" in err or "ratelimit" in err or "rate limit" in err:
                        if attempt < 3:
                            wait = re.search(r'(\d+(?:\.\d+)?)', str(e))
                            delay = max(float(wait.group(1)) if wait else 12 * (2 ** attempt), 5)
                            print(f"  Rate limit hit. Waiting {delay:.0f}s...")
                            time.sleep(delay)
                        else:
                            raise
                    else:
                        raise
            
            agent_message = response.choices[0].message.content
            
            print(f"\nAgent: {agent_message}\n")
            full_transcript += f"Agent: {agent_message}\n\n"
            
            conversation_history.append({"role": "assistant", "content": agent_message})
            
            if "CONVERSATION_COMPLETE" in agent_message:
                print("\nTravel assistant has gathered all necessary information!\n")
                break
            
            user_response = input("You: ").strip()
            if not user_response:
                user_response = "Please continue with the information you have."
            
            full_transcript += f"User: {user_response}\n\n"
            conversation_history.append({"role": "user", "content": user_response})
            
            if len(conversation_history) > 22:
                print("\nMaximum conversation length reached. Proceeding with available information.\n")
                break
        
        return full_transcript
    
    def plan_trip(self, user_input: str) -> str:
        conversation_id = str(uuid.uuid4())
        
        print(f"\n{'='*80}")
        print(f"TRIP PLANNER STARTED")
        print(f"{'='*80}")
        print(f"Conversation ID: {conversation_id}")
        print(f"{'='*80}\n")
        
        self.a2a_protocol.start_conversation(conversation_id, {"user_input": user_input})
        
        # ============================================
        # PHASE 1: Interactive Conversation
        # ============================================
        print("\nPHASE 1: Starting conversation with Travel Assistant...\n")
        conversation_transcript = self.have_conversation(user_input, conversation_id)
        
        # ============================================
        # PHASE 2: Extract Preferences & Validate Budget
        # ============================================
        print("\nPHASE 2: Extracting structured preferences and validating budget...")
        
        conversation_task = self.tasks_class.conversation_task(
            agent=self.conversational_agent,
            user_input=conversation_transcript,
            conversation_id=conversation_id
        )
        extraction_task = self.tasks_class.extraction_task(
            agent=self.preferences_extractor,
            conversation_id=conversation_id,
            conversation_task=conversation_task
        )
        
        print("\nValidating budget before proceeding...")
        extraction_crew = Crew(
            agents=[self.conversational_agent, self.preferences_extractor],
            tasks=[conversation_task, extraction_task],
            process=Process.sequential,
            verbose=True
        )
        extraction_result = self._kickoff_with_retry(extraction_crew)
        extraction_output = str(extraction_result)
        self._extraction_output = extraction_output
        
        if self._is_budget_too_low(extraction_output, conversation_transcript):
            print("\n" + "="*80)
            print("BUDGET TOO LOW - CANNOT PROCEED")
            print("="*80)
            budget_error_message = self._get_budget_error_message(extraction_output, conversation_transcript)
            print(budget_error_message)
            print("="*80 + "\n")
            self.a2a_protocol.end_conversation(conversation_id)
            return budget_error_message
        
        print("\nBudget validated! Proceeding with trip planning...\n")
        
        # ============================================
        # PHASE 3: Fetch Real Data via Direct API Calls
        # ============================================
        import json, re
        from src.tools.mcp_tools import _call_fly_scraper_api
        from src.server.mcp_server import search_hotels_comprehensive, search_attractions, search_restaurants
        
        # Parse extraction JSON to get search parameters
        json_match = re.search(r'\{.*"origin".*"destination".*\}', extraction_output, re.DOTALL)
        prefs = {}
        if json_match:
            try:
                prefs = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        origin = prefs.get("origin", "")
        destination = prefs.get("destination", "")
        departure_date = prefs.get("departure_date", "")
        return_date = prefs.get("return_date", "")
        trip_duration = prefs.get("trip_duration", 5)
        num_adults = prefs.get("num_adults", 1)
        total_budget = prefs.get("total_budget", 0)
        interests = ", ".join(prefs.get("interests", [])) if isinstance(prefs.get("interests"), list) else str(prefs.get("interests", ""))
        
        # Budget breakdown
        flight_budget = prefs.get("budget_breakdown", {}).get("flights", total_budget * 0.35) if isinstance(prefs.get("budget_breakdown"), dict) else total_budget * 0.35
        accommodation_budget = prefs.get("budget_breakdown", {}).get("accommodation", total_budget * 0.35) if isinstance(prefs.get("budget_breakdown"), dict) else total_budget * 0.35
        meals_budget = prefs.get("budget_breakdown", {}).get("meals", total_budget * 0.10) if isinstance(prefs.get("budget_breakdown"), dict) else total_budget * 0.10
        
        budget_per_night = accommodation_budget / trip_duration if trip_duration > 0 else accommodation_budget
        budget_per_meal = meals_budget / (trip_duration * 2) if trip_duration > 0 else meals_budget
        
        # === Send A2A: Preferences → Coordinator ===
        self._send_a2a_message(
            "preferences_extractor", "itinerary_coordinator",
            {"extraction_output": extraction_output[:5000]},
            conversation_id, MessageType.REQUEST
        )
        
        # Fetch flights
        print("\nFetching flight data...")
        flights_data = ""
        if origin and destination and departure_date:
            try:
                flights_data = _call_fly_scraper_api(
                    origin_code=origin,
                    dest_code=destination,
                    departure_date=departure_date,
                    return_date=return_date if return_date else None,
                    adults=num_adults,
                    budget=flight_budget
                )
                print(f"  Flight data retrieved ({len(flights_data)} chars)")
            except Exception as e:
                print(f"  Flight search failed: {e}")
                flights_data = json.dumps({"success": False, "error": str(e)})
        
        # === Send A2A: Flights → Coordinator ===
        self._send_a2a_message(
            "flight_data_provider", "itinerary_coordinator",
            {"flights_data": flights_data[:5000], "success": bool(flights_data and "error" not in flights_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Fetch hotels
        print("\nFetching hotel data...")
        hotels_data = ""
        if destination and departure_date and return_date:
            try:
                hotels_data = search_hotels_comprehensive(
                    destination=destination,
                    checkin_date=departure_date,
                    checkout_date=return_date,
                    budget_per_night=budget_per_night,
                    adults=num_adults,
                    rooms=1
                )
                print(f"  Hotel data retrieved ({len(hotels_data)} chars)")
            except Exception as e:
                print(f"  Hotel search failed: {e}")
                hotels_data = json.dumps({"error": str(e), "success": False})
        
        # === Send A2A: Hotels → Coordinator ===
        self._send_a2a_message(
            "hotel_data_provider", "itinerary_coordinator",
            {"hotels_data": hotels_data[:5000], "success": bool(hotels_data and "error" not in hotels_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Fetch attractions
        print("\nFetching attraction data...")
        attractions_data = ""
        if destination and interests:
            try:
                attractions_data = search_attractions(
                    destination=destination,
                    interests=interests,
                    duration_days=trip_duration
                )
                print(f"  Attraction data retrieved ({len(attractions_data)} chars)")
            except Exception as e:
                print(f"  Attraction search failed: {e}")
                attractions_data = json.dumps({"error": str(e), "success": False})
        
        # === Send A2A: Attractions → Coordinator ===
        self._send_a2a_message(
            "attraction_data_provider", "itinerary_coordinator",
            {"attractions_data": attractions_data[:5000], "success": bool(attractions_data and "error" not in attractions_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Fetch restaurants
        print("\nFetching restaurant data...")
        restaurants_data = ""
        if destination:
            try:
                restaurants_data = search_restaurants(
                    destination=destination,
                    cuisine_types=interests,
                    budget_per_meal=budget_per_meal
                )
                print(f"  Restaurant data retrieved ({len(restaurants_data)} chars)")
            except Exception as e:
                print(f"  Restaurant search failed: {e}")
                restaurants_data = json.dumps({"error": str(e), "success": False})
        
        # === Send A2A: Restaurants → Coordinator ===
        self._send_a2a_message(
            "restaurant_data_provider", "itinerary_coordinator",
            {"restaurants_data": restaurants_data[:5000], "success": bool(restaurants_data and "error" not in restaurants_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # ============================================
        # PHASE 4: Coordination & Itinerary Creation
        # ============================================
        print("\nPHASE 4: Itinerary Coordinator synthesizing all data...")
        
        a2a_message_history = self._build_a2a_message_history(conversation_id)
        
        coordination_task = self.tasks_class.coordination_task(
            agent=self.coordinator_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task,
            a2a_message_history=a2a_message_history
        )
        
        print("\nAssembling crew and executing workflow...\n")
        crew = Crew(
            agents=[self.coordinator_agent],
            tasks=[coordination_task],
            process=Process.sequential,
            verbose=True
        )
        result = self._kickoff_with_retry(crew)
        
        result_str = str(result)
        if self._extraction_output:
            result_str = self._validate_and_enhance_itinerary(result_str, self._extraction_output)
        
        # === Send A2A: Coordinator → User with final itinerary ===
        self._send_a2a_message(
            "itinerary_coordinator", "user",
            {"itinerary": result_str[:5000]},
            conversation_id, MessageType.RESPONSE
        )
        
        self.a2a_protocol.end_conversation(conversation_id)
        
        print(f"\n{'='*80}")
        print("TRIP PLANNING COMPLETED")
        print(f"{'='*80}\n")
        
        self._display_a2a_message_flow(conversation_id)
        
        return result_str
    
    def plan_trip_from_transcript(self, conversation_transcript: str, conversation_id: str) -> str:
        self.a2a_protocol.start_conversation(conversation_id, {"transcript": conversation_transcript})
        
        conversation_task = self.tasks_class.conversation_task(
            agent=self.conversational_agent,
            user_input=conversation_transcript,
            conversation_id=conversation_id
        )
        extraction_task = self.tasks_class.extraction_task(
            agent=self.preferences_extractor,
            conversation_id=conversation_id,
            conversation_task=conversation_task
        )
        
        # Run extraction
        extraction_crew = Crew(
            agents=[self.conversational_agent, self.preferences_extractor],
            tasks=[conversation_task, extraction_task],
            process=Process.sequential,
            verbose=True
        )
        extraction_result = self._kickoff_with_retry(extraction_crew)
        extraction_output = str(extraction_result)
        self._extraction_output = extraction_output
        
        print("\n[DEBUG] Extraction output (first 500 chars):")
        print(extraction_output[:500])
        print("...\n")
        
        if self._is_budget_too_low(extraction_output, conversation_transcript):
            self.a2a_protocol.end_conversation(conversation_id)
            return self._get_budget_error_message(extraction_output, conversation_transcript)
        
        # === Send A2A: Preferences → Coordinator ===
        self._send_a2a_message(
            "preferences_extractor", "itinerary_coordinator",
            {"extraction_output": extraction_output[:5000]},
            conversation_id, MessageType.REQUEST
        )
        
        # Direct API calls instead of search agents
        import json, re
        from src.tools.mcp_tools import _call_fly_scraper_api
        from src.server.mcp_server import search_hotels_comprehensive, search_attractions, search_restaurants
        
        json_match = re.search(r'\{.*"origin".*"destination".*\}', extraction_output, re.DOTALL)
        prefs = {}
        if json_match:
            try:
                prefs = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        origin = prefs.get("origin", "")
        destination = prefs.get("destination", "")
        departure_date = prefs.get("departure_date", "")
        return_date = prefs.get("return_date", "")
        trip_duration = prefs.get("trip_duration", 5)
        num_adults = prefs.get("num_adults", 1)
        total_budget = prefs.get("total_budget", 0)
        interests = ", ".join(prefs.get("interests", [])) if isinstance(prefs.get("interests"), list) else str(prefs.get("interests", ""))
        
        accommodation_budget = prefs.get("budget_breakdown", {}).get("accommodation", total_budget * 0.35) if isinstance(prefs.get("budget_breakdown"), dict) else total_budget * 0.35
        meals_budget = prefs.get("budget_breakdown", {}).get("meals", total_budget * 0.10) if isinstance(prefs.get("budget_breakdown"), dict) else total_budget * 0.10
        flight_budget = prefs.get("budget_breakdown", {}).get("flights", total_budget * 0.35) if isinstance(prefs.get("budget_breakdown"), dict) else total_budget * 0.35
        
        budget_per_night = accommodation_budget / trip_duration if trip_duration > 0 else accommodation_budget
        budget_per_meal = meals_budget / (trip_duration * 2) if trip_duration > 0 else meals_budget
        
        # Fetch flights
        print("\nFetching flight data...")
        flights_data = ""
        if origin and destination and departure_date:
            try:
                flights_data = _call_fly_scraper_api(origin, destination, departure_date, return_date or None, num_adults, flight_budget)
                print(f"  Flight data retrieved ({len(flights_data)} chars)")
            except Exception as e:
                print(f"  Flight search failed: {e}")
                flights_data = json.dumps({"success": False, "error": str(e)})
        
        # === Send A2A: Flights → Coordinator ===
        self._send_a2a_message(
            "flight_data_provider", "itinerary_coordinator",
            {"flights_data": flights_data[:5000], "success": bool(flights_data and "error" not in flights_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Fetch hotels
        print("\nFetching hotel data...")
        hotels_data = ""
        if destination and departure_date and return_date:
            try:
                hotels_data = search_hotels_comprehensive(destination, departure_date, return_date, budget_per_night, num_adults, 1)
                print(f"  Hotel data retrieved ({len(hotels_data)} chars)")
            except Exception as e:
                print(f"  Hotel search failed: {e}")
                hotels_data = json.dumps({"error": str(e), "success": False})
        
        # === Send A2A: Hotels → Coordinator ===
        self._send_a2a_message(
            "hotel_data_provider", "itinerary_coordinator",
            {"hotels_data": hotels_data[:5000], "success": bool(hotels_data and "error" not in hotels_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Fetch attractions
        print("\nFetching attraction data...")
        attractions_data = ""
        if destination and interests:
            try:
                attractions_data = search_attractions(destination, interests, trip_duration)
                print(f"  Attraction data retrieved ({len(attractions_data)} chars)")
            except Exception as e:
                print(f"  Attraction search failed: {e}")
                attractions_data = json.dumps({"error": str(e), "success": False})
        
        # === Send A2A: Attractions → Coordinator ===
        self._send_a2a_message(
            "attraction_data_provider", "itinerary_coordinator",
            {"attractions_data": attractions_data[:5000], "success": bool(attractions_data and "error" not in attractions_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Fetch restaurants
        print("\nFetching restaurant data...")
        restaurants_data = ""
        if destination:
            try:
                restaurants_data = search_restaurants(destination, interests, budget_per_meal)
                print(f"  Restaurant data retrieved ({len(restaurants_data)} chars)")
            except Exception as e:
                print(f"  Restaurant search failed: {e}")
                restaurants_data = json.dumps({"error": str(e), "success": False})
        
        # === Send A2A: Restaurants → Coordinator ===
        self._send_a2a_message(
            "restaurant_data_provider", "itinerary_coordinator",
            {"restaurants_data": restaurants_data[:5000], "success": bool(restaurants_data and "error" not in restaurants_data.lower())},
            conversation_id, MessageType.RESPONSE
        )
        
        # Coordination task
        a2a_message_history = self._build_a2a_message_history(conversation_id)
        coordination_task = self.tasks_class.coordination_task(
            agent=self.coordinator_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task,
            a2a_message_history=a2a_message_history
        )
        
        crew = Crew(
            agents=[self.coordinator_agent],
            tasks=[coordination_task],
            process=Process.sequential,
            verbose=True
        )
        result = self._kickoff_with_retry(crew)
        
        # === Send A2A: Coordinator → User with final itinerary ===
        self._send_a2a_message(
            "itinerary_coordinator", "user",
            {"itinerary": str(result)[:5000]},
            conversation_id, MessageType.RESPONSE
        )
        
        self.a2a_protocol.end_conversation(conversation_id)
        self._display_a2a_message_flow(conversation_id)
        return str(result)

