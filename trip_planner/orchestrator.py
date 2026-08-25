"""
The workflow, and the only place it is written down.

Reads the request with a model, fetches flights, hotels and venues in plain
Python, then writes the itinerary with a model. Both entry points -- the
command line and the web page -- run through this file.
"""

import logging
import os
import uuid
import time

from crewai import Crew, Process
from textwrap import dedent
from dotenv import load_dotenv

from trip_planner.agents import TripPlannerAgents
from trip_planner.tasks import TripPlannerTasks
from trip_planner.comms import A2AProtocol, A2AMessage, MessageType
from trip_planner.core.budget import LEGACY_ALLOCATION
from trip_planner.comms.registry import AGENT_REGISTRY
from trip_planner.core.gemini_compat import model_string

# Import utility modules for enhanced functionality.
# `regenerate_if_incomplete` and `core.cache.get_cache` were imported here
# but never called. API response caching is now handled at the HTTP layer by
# trip_planner.core.http_cache, which every API call actually goes through.
from trip_planner.core.validators import (
    validate_day_count,
    extract_trip_duration_from_extraction,
    add_completion_notice
)

# Load environment variables from .env file
load_dotenv(override=True)

# Gemini's key is normalised across both of its names by trip_planner/__init__.py,
# which runs on import of the package. The line that used to be here assigned
# GOOGLE_API_KEY to itself — or to "" when only GEMINI_API_KEY was set, which is
# the case it was presumably meant to handle.
os.environ.setdefault("SERPER_API_KEY", os.getenv("SERPER_API_KEY", ""))

logger = logging.getLogger(__name__)

_PROGRESS_HOOK = None


def set_progress_hook(hook) -> None:
    """
    Register something to be told about each step, as well as the console.

    The web interface used to show a spinner reading "Planning your amazing
    trip..." for the whole run, which is several minutes, and an `st.info` saying
    "Creating travel plan with AI agents..." that was printed once before
    anything started. Neither reflected what was happening, so a page that
    appeared frozen and a page that was working looked identical.

    A hook rather than the UI scraping stdout: the steps are already named at the
    point they begin, so the interface can report the same thing the terminal
    does instead of guessing from captured text.

    Pass None to unregister. Errors raised by a hook are swallowed — reporting
    progress must never be the reason a plan fails.
    """
    global _PROGRESS_HOOK
    _PROGRESS_HOOK = hook


def _announce(kind: str, *parts: str) -> None:
    """Tell the registered hook, if any, and never let it break the run."""
    if _PROGRESS_HOOK is None:
        return
    try:
        _PROGRESS_HOOK(kind, *parts)
    except Exception:                          # noqa: BLE001 - progress only
        logger.debug("progress hook raised", exc_info=True)


def _step(number: str, actor: str, doing: str) -> None:
    """
    Announce a step as: who is working, and on what.

    A live run used to print about five hundred lines, most of it the agents'
    own prompts and the same A2A message logged three times — twice by the
    protocol at INFO and once again in readable form. The parts a reader
    actually needs were somewhere in the middle of that.
    """
    rule = "=" * 74
    print("\n" + rule)
    print(f"  {number}  {actor}")
    print(f"      {doing}")
    print(rule)
    _announce("step", number, actor, doing)


def _detail(label: str, value: str) -> None:
    """One indented fact under the current step."""
    print(f"      {label:<22} {value}")
    _announce("detail", label, value)


def _framework_verbose() -> bool:
    """Whether to let the agent framework print its own prompts and reasoning."""
    return os.getenv("TRIP_PLANNER_VERBOSE", "").strip() in ("1", "true", "yes")


# What a tool says when it failed. These come back as ordinary strings with a
# 200-shaped payload — the search layer catches its own errors and returns an
# explanation — so nothing downstream raises, and without this list the
# explanation was reported as a byte count.
_FAILURE_MARKERS = (
    "❌",                       # the cross the hotel search prefixes
    "ERROR:",
    "Sorry, I couldn't find anything",
    "No recorded response",
    '"success": false',
    '"success":false',
)


def _summarise(label: str, data: str) -> str:
    """
    One line saying what a search actually came back with.

    "Flight data retrieved (3431 chars)" is a length, not a result. A reader
    watching this wants to know whether anything usable arrived and roughly what
    it costs — and the raw payloads are 3 kB of JSON, so printing them is not the
    alternative.

    A FAILURE IS NOT A LENGTH EITHER. The search layer catches its own errors and
    returns an explanation as an ordinary string, so a failed hotel search came
    back as 371 readable characters beginning "ERROR: Failed to find
    destination" — and this reported it as "returned 371 chars". A demonstration
    would have shown a step that looked like it worked, and an itinerary built
    from nothing. Failures are now named.

    Deliberately forgiving: a shape this does not recognise falls back to the
    size, because a narration helper must never be the reason a run fails.
    """
    import json as _json
    import re as _re

    if not data:
        return "nothing returned"

    if any(marker in data for marker in _FAILURE_MARKERS):
        if "No recorded response" in data:
            return ("NO DATA - this exact request is not in the recorded cache "
                    "(replay mode)")
        # The first line that reads like the reason, rather than the whole page.
        for line in data.splitlines():
            cleaned = line.strip().strip("❌").strip()
            if cleaned and ("error" in cleaned.lower()
                            or cleaned.lower().startswith("sorry")):
                return f"NO DATA - {cleaned[:110]}"
        return "NO DATA - the search reported a failure"

    try:
        if label == "flight":
            payload = _json.loads(data)
            flights = payload.get("flights") or []
            if not flights:
                return f"no flights found ({len(data):,} chars)"
            prices = [f.get("total_price") for f in flights
                      if isinstance(f.get("total_price"), (int, float))]
            cheapest = f", cheapest ${min(prices):,.0f}" if prices else ""
            return f"{len(flights)} options{cheapest}"

        if label == "hotel":
            found = _re.search(r"Found (\d+) hotels", data)
            rates = [float(m) for m in _re.findall(r"\(\$([\d.]+)/night\)", data)]
            cheapest = f", cheapest ${min(rates):,.0f}/night" if rates else ""
            if found:
                return f"{found.group(1)} hotels{cheapest}"
            return f"returned {len(data):,} chars{cheapest}"

        # The web searches come back as titled blocks.
        results = data.count("Title:")
        if results:
            return f"{results} results"
    except Exception:                      # noqa: BLE001 - narration only
        pass
    return f"returned {len(data):,} chars"


class TripPlannerCrew:
    """
    The shipped workflow: two model steps with plain-Python retrieval between them.

      1. Conversational agent gathers the request        (uses the model)
      2. Preferences extractor structures it, and the budget is checked
                                                         (uses the model)
      3. Flights, hotels, attractions and restaurants are fetched in order,
         each call decided by an if statement            (no model, no agent)
      4. Itinerary coordinator assembles the day-by-day plan
                                                         (uses the model)

    Every exchange is recorded over the A2A protocol.

    This docstring described three search agents working in parallel with MCP
    tools. That was the six-agent design, and it has not been what this class does
    since the pivot: retrieval is a sequential loop over four calls, and appendix
    E records the parallel search agents as removed. A comment describing a
    previous version of the code is worse than none, because it is read as current.
    """

    def __init__(self):
        self.agents_class = TripPlannerAgents()
        self.tasks_class = TripPlannerTasks()
        self.a2a_protocol = A2AProtocol()
        self._extraction_output = None  # Store for validation

        # Initialize agents (only conversation, extraction, and coordination need LLM)
        self.conversational_agent = self.agents_class.conversational_agent()
        self.preferences_extractor = self.agents_class.preferences_extractor_agent()
        self.coordinator_agent = self.agents_class.itinerary_coordinator_agent()
        
        print(f"  Ready: 3 agents that use the model, "
              f"{len(AGENT_REGISTRY)} A2A agent cards registered.")
        print(f"  Retrieval runs in plain Python between the model steps."
              + ("" if _framework_verbose() else
                 "  (TRIP_PLANNER_VERBOSE=1 for the framework's own trace)"))
    
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
        from trip_planner.core.real_prices import PriceProbe
        from trip_planner.core.trip_cost import assess_budget, is_known_destination

        prefs = self._parse_prefs(extraction_output)

        # An explicit refusal from the extractor still wins.
        if "BUDGET_TOO_LOW" in extraction_output:
            print("[Budget] Extractor flagged the budget as too low")

        travelers = int(prefs.get("num_adults", 1) or 1) + int(prefs.get("num_children", 0) or 0)
        # A real fare beats a constant. The probe reads the recorded responses
        # first, which costs nothing and needs no key.
        #
        # When the destination is not in the price table it is allowed to ASK, and
        # that spends one of thirty monthly flight searches. That trade is worth
        # making precisely there and nowhere else: for an unlisted city the
        # alternative is the middle row of every band — Kyoto costed as medium-haul
        # at moderate prices, about $614 for five nights where the truth is nearer
        # $987 — and a number nobody can account for is worse than a request. For a
        # city the table knows, the estimate is already grounded and buying a fare
        # would tell us nothing new.
        #
        # The reply is recorded, so asking once calibrates that route permanently
        # and every later check for it is free.
        #
        # Deliberately NOT passed by trip_planner/evaluation/exp_budget_gate.py: that
        # experiment's twenty scenarios and its Cohen's kappa are published against
        # the table, and a different input would mean those figures no longer
        # describe the code.
        destination = prefs.get("destination", "")
        unlisted = bool(destination) and not is_known_destination(destination)
        if unlisted:
            print(f"[Budget] '{destination}' is not in the price table — checking "
                  f"the real fare rather than assuming a mid-range default. "
                  f"This uses one flight search.")
        verdict = assess_budget(
            total_budget=float(prefs.get("total_budget", 0) or 0),
            destination=destination,
            nights=int(prefs.get("trip_duration", 5) or 5),
            travelers=max(1, travelers),
            origin=prefs.get("origin", ""),
            price_probe=PriceProbe(
                allow_live=unlisted,
                departure_date=str(prefs.get("departure_date", "") or ""),
                return_date=str(prefs.get("return_date", "") or ""),
                adults=max(1, travelers)),
            travel_style=str(prefs.get("travel_style", "") or ""),
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
            _announce("days", "unknown", "", "")
            return itinerary

        # Validate day count
        is_valid, actual_count, found_days = validate_day_count(itinerary, expected_days)

        # Reported to the hook as well, so the web interface can show the same
        # result as a badge rather than leaving the reader to notice a warning
        # paragraph appended to the bottom of a long itinerary.
        _announce("days", "complete" if is_valid else "short",
                  str(actual_count), str(expected_days))

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
        
        # Counted, not asserted. This line used to read "Protocol errors: 0" as a
        # literal, which was a claim the code had no way to make — nothing counts
        # protocol errors, and the conformance audit reports 3 of 5 A2A checks
        # failing. A printed zero that cannot go up is worse than no line at all.
        errors = sum(1 for m in history if m.message_type == MessageType.ERROR)
        print(f"\n  📊 Stats:")
        print(f"     Total messages:  {len(history)}")
        print(f"     Unique agents:   {len(agents_seen)}")
        print(f"     Error messages:  {errors}")
        print("=" * 70 + "\n")
    
    def have_conversation(self, initial_input: str, conversation_id: str) -> str:
        from litellm import completion
        import time, re
        
        model_name = model_string()
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
        
        # The step banner immediately above already names this agent and says it
        # is collecting details, so this only needs to explain the one thing the
        # banner cannot: that the reader is expected to type.
        print("      Type your answers below; it will say when it has enough.\n")

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

    def plan_trip(self, user_input: str, confirm_allocation=None) -> str:
        """
        Plan a trip, gathering the details through conversation first.

        The command-line entry point: it asks the traveller questions until it
        has what it needs, then plans.
        """
        conversation_id = str(uuid.uuid4())
        # One line, not a banner. There used to be three stacked rule-and-title
        # blocks before the first question — this one, the conversation's own, and
        # the step banner — each restating that a trip planner had started.
        print(f"\n  Conversation {conversation_id[:8]} started.")

        self.a2a_protocol.start_conversation(conversation_id, {"user_input": user_input})

        _step("STEP 1 of 4", "CONVERSATIONAL AGENT  (uses the model)",
              "Asking the traveller for the details the plan needs")
        transcript = self.have_conversation(user_input, conversation_id)
        return self._plan(transcript, conversation_id, confirm_allocation)

    def plan_trip_from_transcript(self, conversation_transcript: str,
                                  conversation_id: str,
                                  confirm_allocation=None) -> str:
        """
        Plan a trip from an already-collected transcript.

        The web entry point: the interface has asked its questions through a
        form, so there is no conversation left to hold.
        """
        self.a2a_protocol.start_conversation(
            conversation_id, {"transcript": conversation_transcript})
        return self._plan(conversation_transcript, conversation_id,
                          confirm_allocation)

    # ------------------------------------------------------------------
    def _plan(self, transcript: str, conversation_id: str,
              confirm_allocation=None) -> str:
        """
        The workflow both entry points run: understand, retrieve, assemble.

        Retrieval happens in plain Python between two model steps. That is the
        design decision this project tests — a model is used where the step
        needs judgement, and not where it does not.

        `confirm_allocation` is an optional callback taking the extracted
        preferences and returning a budget split to use instead of the extracted
        one, or None to keep it. It exists because the command line can ask the
        traveller to approve the split and the web form cannot, and the
        alternative was a second copy of this whole workflow in run_cli.py —
        which is what used to be there, and which had already drifted: the
        command line skipped the A2A layer and the itinerary validation entirely.
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
        _announce("budget", verdict.verdict, verdict.message)

        # A budget can be workable and still not reach what was asked for. Saying
        # so here lets the traveller choose between spending more and expecting
        # less, rather than finding the difference in the finished itinerary.
        shortfall = verdict.style_shortfall()
        if shortfall:
            print(f"[Budget] {shortfall}\n")

        allocation = None
        if confirm_allocation is not None:
            allocation = confirm_allocation(extraction_output)

        self._retrieve_and_announce(extraction_output, conversation_id,
                                    allocation=allocation)

        itinerary = self._assemble_itinerary(extraction_task, conversation_id)
        itinerary = self._validate_and_enhance_itinerary(itinerary, extraction_output)

        self._send_a2a_message(
            "itinerary_coordinator", "user",
            {"itinerary": itinerary[:5000]},
            conversation_id, MessageType.RESPONSE,
        )
        self.a2a_protocol.end_conversation(conversation_id)

        # No "COMPLETED" banner here: the A2A summary that follows opens with its
        # own rule and title, so the two ran together as one wall of equals signs.
        self._display_a2a_message_flow(conversation_id)
        return itinerary

    # ------------------------------------------------------------------
    def _extract_preferences(self, transcript: str, conversation_id: str):
        """Turn the conversation into structured fields. This needs a model."""
        _step("STEP 2 of 4", "PREFERENCES EXTRACTOR  (uses the model)",
              "Turning the conversation into structured fields, then checking the budget")

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
            # Off deliberately. Verbose prints each agent's whole task prompt —
            # several hundred lines per run — and the step banners above already
            # say which agent is working and what it was given. Set
            # TRIP_PLANNER_VERBOSE=1 for the framework's own trace when debugging.
            verbose=_framework_verbose(),
        )
        extraction_output = self._as_json_text(self._kickoff_with_retry(crew))
        self._extraction_output = extraction_output
        return extraction_output, extraction_task

    @staticmethod
    def _as_json_text(crew_result) -> str:
        """
        Get the crew's answer as JSON TEXT, not as a Python repr.

        str() on a CrewAI result is not safe here. When the framework manages to
        parse the model's answer it stores a dict and str() then returns a Python
        repr — {'total_budget': 800.0} — with single quotes. Every downstream
        regex looks for "total_budget" with double quotes, so all of them missed,
        and the failure was silent and intermittent: it only appeared when the
        framework SUCCEEDED at parsing, which is the opposite of what anyone
        debugging would expect.

        What that cost: _parse_prefs returned an empty dict, so _assess_budget saw
        no destination and skipped the feasibility check altogether. On the run
        that exposed this the extractor had itself flagged BUDGET_TOO_LOW and
        recommended a minimum of $1,000 against a stated $800 — and the trip was
        planned anyway, because the warning was in a dict nobody could read.
        """
        import json

        payload = getattr(crew_result, "json_dict", None)
        if isinstance(payload, dict) and payload:
            return json.dumps(payload)
        raw = getattr(crew_result, "raw", None)
        if isinstance(raw, str) and raw.strip():
            return raw
        return str(crew_result)

    # ------------------------------------------------------------------
    @staticmethod
    def _search_parameters(extraction_output: str, allocation: dict = None) -> dict:
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
        # An allocation the traveller approved outranks one the extractor guessed.
        # This is how the command line's interactive budget split reaches the
        # searches without a second copy of the workflow existing to carry it.
        if isinstance(allocation, dict) and allocation:
            split = {k: total * v if v <= 1 else v for k, v in allocation.items()}
        nights = prefs.get("trip_duration", 5) or 5

        accommodation = split.get("accommodation") or total * LEGACY_ALLOCATION["accommodation"]
        meals = split.get("meals") or total * LEGACY_ALLOCATION["meals"]
        return {
            "origin": prefs.get("origin", ""),
            "destination": prefs.get("destination", ""),
            "departure_date": prefs.get("departure_date", ""),
            "return_date": prefs.get("return_date", ""),
            "nights": nights,
            "adults": prefs.get("num_adults", 1),
            "interests": ", ".join(interests) if isinstance(interests, list)
                         else str(interests or ""),
            "flight_budget": split.get("flights") or total * LEGACY_ALLOCATION["flights"],
            "budget_per_night": accommodation / nights if nights > 0 else accommodation,
            "budget_per_meal": meals / (nights * 2) if nights > 0 else meals,
        }

    # ------------------------------------------------------------------
    def _retrieve_and_announce(self, extraction_output: str,
                               conversation_id: str,
                               allocation: dict = None) -> None:
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

        p = self._search_parameters(extraction_output, allocation)

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

        _step("STEP 3 of 4", "PLAIN PYTHON  (no model, no agent)",
              "Fetching the data. Four calls, each decided by an if statement.")
        _detail("route", f"{p['origin'] or '?'} to {p['destination'] or '?'}")
        _detail("dates", f"{p['departure_date'] or '?'} to "
                         f"{p['return_date'] or '?'}  "
                         f"({p['nights']} nights, {p['adults']} traveller(s))")
        _detail("budget passed in", f"flights ${p['flight_budget']:,.0f} | "
                                    f"hotel ${p['budget_per_night']:,.0f}/night | "
                                    f"meals ${p['budget_per_meal']:,.0f}/meal")
        print()

        for sender, field, label, have_parameters, call in fetches:
            data = ""
            # Through _detail rather than print, so the web interface is told what
            # each search returned and can show the same four lines the terminal
            # does. It used to show a spinner for the whole of this.
            if not have_parameters:
                _detail(label, "SKIPPED - the request did not contain what this "
                               "search needs")
            else:
                try:
                    data = call()
                    _detail(label, _summarise(label, data))
                except Exception as exc:
                    # The type as well as the message: several exceptions on this
                    # path stringify to nothing, and "search failed:" with an
                    # empty reason is not something anyone can act on.
                    _detail(label, f"FAILED - {type(exc).__name__}: "
                                   f"{exc or 'no message given'}")
                    data = json.dumps({"success": False, "error": str(exc)})

            self._send_a2a_message(
                sender, "itinerary_coordinator",
                {field: data[:5000],
                 "success": bool(data and "error" not in data.lower())},
                conversation_id, MessageType.RESPONSE,
            )
            print(f"      {'':<12} -> handed to itinerary_coordinator over A2A "
                  f"({len(data):,} chars)")

    # ------------------------------------------------------------------
    def _assemble_itinerary(self, extraction_task, conversation_id: str) -> str:
        """Arrange the retrieved options into a plan. This needs a model."""
        _step("STEP 4 of 4", "ITINERARY COORDINATOR  (uses the model)",
              "Writing the day-by-day plan from the retrieved data only")

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
            # Off deliberately. Verbose prints each agent's whole task prompt —
            # several hundred lines per run — and the step banners above already
            # say which agent is working and what it was given. Set
            # TRIP_PLANNER_VERBOSE=1 for the framework's own trace when debugging.
            verbose=_framework_verbose(),
        )
        return str(self._kickoff_with_retry(crew))
