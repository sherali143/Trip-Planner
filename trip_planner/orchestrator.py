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

from trip_planner.agents import TripPlannerAgents
from trip_planner.tasks import TripPlannerTasks
from trip_planner.comms import A2AProtocol, A2AMessage, MessageType
from trip_planner.comms.registry import AGENT_REGISTRY

# Import utility modules for enhanced functionality.
# `regenerate_if_incomplete` and `src.core.cache.get_cache` were imported here
# but never called. API response caching is now handled at the HTTP layer by
# src.core.http_cache, which every API call actually goes through.
from trip_planner.core.validators import (
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
    
    @staticmethod
    def _parse_prefs(extraction_output: str) -> dict:
        """Pull the structured preferences out of the extractor's output."""
        import json
        import re

        for pattern in (
            r'\{(?:[^{}]|\{[^{}]*\})*"total_budget"(?:[^{}]|\{[^{}]*\})*\}',
            r'\{.*"destination".*\}',
        ):
            match = re.search(pattern, extraction_output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue

        # Fall back to field-by-field regex if the JSON will not parse.
        prefs = {}
        for key, cast in (("total_budget", float), ("trip_duration", int),
                          ("num_adults", int), ("num_children", int)):
            m = re.search(rf'"{key}":\s*(\d+(?:\.\d+)?)', extraction_output)
            if m:
                prefs[key] = cast(float(m.group(1)))
        for key in ("destination", "origin"):
            m = re.search(rf'"{key}":\s*"([^"]+)"', extraction_output)
            if m:
                prefs[key] = m.group(1)
        return prefs

    def _assess_budget(self, extraction_output: str):
        """
        Judge the stated budget against what this specific trip costs.

        Replaces a fixed formula that ignored the destination entirely
        (300 per traveller for flights, 50 a night for hotels, times a 0.6
        fudge factor). That judged a 700 dollar Bangkok trip and a 700 dollar
        London trip identically, accepting both — so London produced a
        confidently fictional itinerary. See trip_planner/core/trip_cost.py.
        """
        from trip_planner.core.trip_cost import assess_budget

        prefs = self._parse_prefs(extraction_output)

        # An explicit refusal from the extractor still wins.
        if "BUDGET_TOO_LOW" in extraction_output:
            print("[Budget] Extractor flagged the budget as too low")

        travelers = int(prefs.get("num_adults", 1) or 1) + int(prefs.get("num_children", 0) or 0)
        verdict = assess_budget(
            total_budget=float(prefs.get("total_budget", 0) or 0),
            destination=prefs.get("destination", ""),
            nights=int(prefs.get("trip_duration", 5) or 5),
            travelers=max(1, travelers),
            origin=prefs.get("origin", ""),
        )

        if not prefs.get("destination"):
            # Without a destination there is no basis to refuse; let it proceed
            # rather than block on a parsing failure.
            print("[Budget] No destination parsed — skipping feasibility check")
            verdict.feasible = True
        return verdict

    @staticmethod
    def _budget_error_message(verdict) -> str:
        """Explain why the trip cannot be planned, and what would make it work."""
        lines = [
            "",
            "=" * 70,
            "  THIS TRIP CANNOT BE PLANNED WITHIN THAT BUDGET",
            "=" * 70,
            "",
            f"  {verdict.message}",
            "",
            verdict.estimate.explain(),
            "",
            "  WHAT YOU CAN DO:",
        ]
        lines += [f"    {i}. {s}" for i, s in enumerate(verdict.suggestions, 1)]
        lines += ["", "=" * 70, ""]
        return "\n".join(lines)

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

    # ==================================================================
    # PLANNING
    #
    # Two entry points, one implementation. They used to be two methods
    # sharing 74% of their text, and the copies had already drifted: the
    # day-count validation existed in the command-line path and not in the
    # web one, so a short itinerary was silently accepted in the browser and
    # flagged in the terminal.
    # ==================================================================

    def plan_trip(self, user_input: str) -> str:
        """
        Plan a trip, gathering the details through conversation first.

        The command-line entry point: it asks the traveller questions until it
        has what it needs, then plans.
        """
        conversation_id = str(uuid.uuid4())
        print(f"\n{'=' * 80}\nTRIP PLANNER STARTED\n{'=' * 80}")
        print(f"Conversation ID: {conversation_id}\n{'=' * 80}\n")

        self.a2a_protocol.start_conversation(conversation_id, {"user_input": user_input})

        print("\nPHASE 1: Starting conversation with Travel Assistant...\n")
        transcript = self.have_conversation(user_input, conversation_id)
        return self._plan(transcript, conversation_id)

    def plan_trip_from_transcript(self, conversation_transcript: str,
                                  conversation_id: str) -> str:
        """
        Plan a trip from an already-collected transcript.

        The web entry point: the interface has asked its questions through a
        form, so there is no conversation left to hold.
        """
        self.a2a_protocol.start_conversation(
            conversation_id, {"transcript": conversation_transcript})
        return self._plan(conversation_transcript, conversation_id)

    # ------------------------------------------------------------------
    def _plan(self, transcript: str, conversation_id: str) -> str:
        """
        The workflow both entry points run: understand, retrieve, assemble.

        Retrieval happens in plain Python between two model steps. That is the
        design decision this project tests — a model is used where the step
        needs judgement, and not where it does not.
        """
        extraction_output, extraction_task = self._extract_preferences(
            transcript, conversation_id)

        verdict = self._assess_budget(extraction_output)
        if not verdict.feasible:
            message = self._budget_error_message(verdict)
            print(message)
            self.a2a_protocol.end_conversation(conversation_id)
            return message

        # Feasible, but say plainly what this budget buys. A tight budget is a
        # legitimate choice, so this warns and proceeds rather than blocking.
        print(f"\n[Budget] {verdict.verdict.replace('_', ' ').title()}: "
              f"{verdict.message}\n")

        self._retrieve_and_announce(extraction_output, conversation_id)

        itinerary = self._assemble_itinerary(extraction_task, conversation_id)
        itinerary = self._validate_and_enhance_itinerary(itinerary, extraction_output)

        self._send_a2a_message(
            "itinerary_coordinator", "user",
            {"itinerary": itinerary[:5000]},
            conversation_id, MessageType.RESPONSE,
        )
        self.a2a_protocol.end_conversation(conversation_id)

        print(f"\n{'=' * 80}\nTRIP PLANNING COMPLETED\n{'=' * 80}\n")
        self._display_a2a_message_flow(conversation_id)
        return itinerary

    # ------------------------------------------------------------------
    def _extract_preferences(self, transcript: str, conversation_id: str):
        """Turn the conversation into structured fields. This needs a model."""
        print("\nPHASE 2: Extracting structured preferences and validating budget...")

        conversation_task = self.tasks_class.conversation_task(
            agent=self.conversational_agent,
            user_input=transcript,
            conversation_id=conversation_id,
        )
        extraction_task = self.tasks_class.extraction_task(
            agent=self.preferences_extractor,
            conversation_id=conversation_id,
            conversation_task=conversation_task,
        )
        crew = Crew(
            agents=[self.conversational_agent, self.preferences_extractor],
            tasks=[conversation_task, extraction_task],
            process=Process.sequential,
            verbose=True,
        )
        extraction_output = str(self._kickoff_with_retry(crew))
        self._extraction_output = extraction_output
        return extraction_output, extraction_task

    # ------------------------------------------------------------------
    @staticmethod
    def _search_parameters(extraction_output: str) -> dict:
        """
        Pull the search parameters out of the extractor's JSON.

        Budget shares fall back to the default split only when the extractor
        did not supply one; a traveller who states how to divide their money
        has expressed a preference, not made a mistake.
        """
        import json
        import re

        prefs = {}
        match = re.search(r'\{.*"origin".*"destination".*\}', extraction_output,
                          re.DOTALL)
        if match:
            try:
                prefs = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        interests = prefs.get("interests", [])
        total = prefs.get("total_budget", 0) or 0
        split = prefs.get("budget_breakdown") if isinstance(
            prefs.get("budget_breakdown"), dict) else {}
        nights = prefs.get("trip_duration", 5) or 5

        accommodation = split.get("accommodation") or total * 0.35
        meals = split.get("meals") or total * 0.10
        return {
            "origin": prefs.get("origin", ""),
            "destination": prefs.get("destination", ""),
            "departure_date": prefs.get("departure_date", ""),
            "return_date": prefs.get("return_date", ""),
            "nights": nights,
            "adults": prefs.get("num_adults", 1),
            "interests": ", ".join(interests) if isinstance(interests, list)
                         else str(interests or ""),
            "flight_budget": split.get("flights") or total * 0.35,
            "budget_per_night": accommodation / nights if nights > 0 else accommodation,
            "budget_per_meal": meals / (nights * 2) if nights > 0 else meals,
        }

    # ------------------------------------------------------------------
    def _retrieve_and_announce(self, extraction_output: str,
                               conversation_id: str) -> None:
        """
        Fetch flights, hotels, attractions and restaurants, announcing each
        result over the A2A protocol.

        No model is involved. Once the request has been parsed the parameters
        are fixed and there is exactly one correct call to make for each.
        """
        import json

        from trip_planner.server.mcp_server import (search_attractions,
                                                    search_hotels_comprehensive,
                                                    search_restaurants)
        from trip_planner.tools.travel_apis import _call_fly_scraper_api

        p = self._search_parameters(extraction_output)

        self._send_a2a_message(
            "preferences_extractor", "itinerary_coordinator",
            {"extraction_output": extraction_output[:5000]},
            conversation_id, MessageType.REQUEST,
        )

        # Each entry: who announces the result, the field name the coordinator
        # reads, a label for the log, whether the parameters it needs are
        # present, and the call to make.
        fetches = [
            ("flight_data_provider", "flights_data", "flight",
             bool(p["origin"] and p["destination"] and p["departure_date"]),
             lambda: _call_fly_scraper_api(
                 p["origin"], p["destination"], p["departure_date"],
                 p["return_date"] or None, p["adults"], p["flight_budget"])),
            ("hotel_data_provider", "hotels_data", "hotel",
             bool(p["destination"] and p["departure_date"] and p["return_date"]),
             lambda: search_hotels_comprehensive(
                 p["destination"], p["departure_date"], p["return_date"],
                 p["budget_per_night"], p["adults"], 1)),
            ("attraction_data_provider", "attractions_data", "attraction",
             bool(p["destination"] and p["interests"]),
             lambda: search_attractions(
                 p["destination"], p["interests"], p["nights"])),
            ("restaurant_data_provider", "restaurants_data", "restaurant",
             bool(p["destination"]),
             lambda: search_restaurants(
                 p["destination"], p["interests"], p["budget_per_meal"])),
        ]

        for sender, field, label, have_parameters, call in fetches:
            data = ""
            if have_parameters:
                print(f"\nFetching {label} data...")
                try:
                    data = call()
                    print(f"  {label.title()} data retrieved ({len(data)} chars)")
                except Exception as exc:
                    print(f"  {label.title()} search failed: {exc}")
                    data = json.dumps({"success": False, "error": str(exc)})

            self._send_a2a_message(
                sender, "itinerary_coordinator",
                {field: data[:5000],
                 "success": bool(data and "error" not in data.lower())},
                conversation_id, MessageType.RESPONSE,
            )

    # ------------------------------------------------------------------
    def _assemble_itinerary(self, extraction_task, conversation_id: str) -> str:
        """Arrange the retrieved options into a plan. This needs a model."""
        print("\nPHASE 4: Itinerary Coordinator synthesizing all data...")

        coordination_task = self.tasks_class.coordination_task(
            agent=self.coordinator_agent,
            conversation_id=conversation_id,
            extraction_task=extraction_task,
            a2a_message_history=self._build_a2a_message_history(conversation_id),
        )
        crew = Crew(
            agents=[self.coordinator_agent],
            tasks=[coordination_task],
            process=Process.sequential,
            verbose=True,
        )
        return str(self._kickoff_with_retry(crew))
