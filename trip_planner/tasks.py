"""
What each agent is told to do.

One task definition per agent, holding the instructions and the shape of the
answer expected back.
"""

from crewai import Task
from textwrap import dedent
from typing import List, Optional
from pydantic import BaseModel

from trip_planner.core.budget import LEGACY_ALLOCATION as _DEFAULT_SPLIT


# ============================================================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUTS
# ============================================================================

class BudgetBreakdown(BaseModel):
    flights: float
    accommodation: float
    activities: float
    meals: float

class TravelPreferences(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: str
    trip_duration: int
    total_budget: float
    num_adults: int = 1  # Default to 1 adult if not specified
    num_children: int = 0  # Default to 0 children if not specified
    total_travelers: int = 1  # Total number of travelers
    budget_breakdown: BudgetBreakdown
    interests: List[str]
    travel_style: str
    activity_level: str
    special_requirements: List[str] = []
    flexibility: str
    confidence_level: str = "medium"
    # Budget warning fields
    budget_warning: str = "OK"  # "OK" or "BUDGET_TOO_LOW"
    budget_issue: Optional[str] = None  # Explanation if budget is too low
    minimum_recommended_budget: Optional[float] = None  # Suggested minimum if too low


class TripPlannerTasks:
    """
    Trip Planner Tasks with A2A Protocol Integration
    
    These tasks orchestrate the workflow of the trip planning system,
    enabling agent-to-agent communication through structured data exchange.
    """
    
    def __tip_section(self):
        return "If you do your BEST WORK, I'll give you a $10,000 commission!"
    
    def conversation_task(self, agent, user_input: str, conversation_id: str):
        """
        Task for the Conversational Agent to engage with the user
        and gather travel requirements
        """
        return Task(
            description=dedent(f"""
                Engage the user in a natural, friendly conversation to understand their 
                travel needs. The user has provided the following initial input:
                
                User Input: {user_input}
                Conversation ID: {conversation_id}
                
                You MUST ask ALL 8 questions below ONE AT A TIME. Do NOT skip any.
                Wait for the user's answer before asking the next question.
                
                1. Destination?
                2. How many people are traveling?
                3. Origin (where from)?
                4. Dates (departure + return)?
                5. Total budget in USD?
                6. Interests?
                7. Travel style (luxury/moderate/budget)?
                8. Special requirements?
                
                {self.__tip_section()}
            """),
            expected_output=dedent("""
                A complete conversation transcript including:
                - All user responses and clarifications
                - Confirmation of collected information
                - Clear indication that information gathering is complete
                - Summary of key travel requirements
            """),
            agent=agent
        )
    
    def extraction_task(self, agent, conversation_id: str, conversation_task):
        """
        Task for the Preferences Extractor to structure conversation data
        for downstream agents (A2A communication)
        
        NOW INCLUDES: Pydantic model for structured output + Budget Validation
        """
        return Task(
            description=dedent(f"""
                READ THE COMPLETE CONVERSATION TRANSCRIPT from the previous task context
                and extract all travel preferences into a structured format.
                
                Conversation ID: {conversation_id}
                
                ⚠️ IMPORTANT: The conversation transcript is in your CONTEXT from the previous task.
                READ IT CAREFULLY and extract ALL the information the user provided.
                
                Extract and structure the following information from the conversation:
                
                **EXTRACTION EXAMPLES:**
                
                If user says: "I want to go to USA from Islamabad for 10 days starting December 15"
                - origin: "Islamabad"
                - destination: "USA"
                - departure_date: "2025-12-15"
                - trip_duration: 10
                - return_date: "2025-12-25" (Dec 15 + 10 days)
                
                If user says: "budget of 150000 dollars" or "$150000"
                - total_budget: 150000
                
                If user says: "luxury trip" or "I prefer luxury"
                - travel_style: "luxury"
                
                If user says: "museums, food, adventure, relaxation" or "all"
                - interests: ["museums", "food", "adventure", "relaxation", "shopping", "nightlife", "culture"]
                
                If user says: "one person" or "just me" or nothing about travelers
                - num_adults: 1
                - num_children: 0
                - total_travelers: 1
                
                **Required Fields:**
                - origin: Origin city/airport (e.g., "Islamabad", "Pakistan")
                - destination: Destination city/country (e.g., "USA", "New York")
                - departure_date: When they're leaving (YYYY-MM-DD format, e.g., "2025-12-15")
                - return_date: When they're returning (YYYY-MM-DD format)
                  ⚠️ If only trip_duration is given, CALCULATE return_date = departure_date + trip_duration
                - trip_duration: Number of days (e.g., 10)
                - total_budget: Total budget amount in USD (e.g., 150000)
                - num_adults: Number of adult travelers (DEFAULT TO 1 if not specified)
                - num_children: Number of children (DEFAULT TO 0 if not specified)
                
                **Budget Breakdown:**
                If the user stated how they want their budget split, USE THEIR
                NUMBERS — this is their preference, not yours to override.
                Examples of the user stating a split:
                  "most of it on the hotel"        -> weight accommodation higher
                  "I want 50% on flights"          -> flights = total * 0.50
                  "$600 for flights, rest flexible" -> flights_budget = 600

                Only if the user said NOTHING about splitting the budget, use:
                - flights_budget: total_budget * {_DEFAULT_SPLIT['flights']}
                - accommodation_budget: total_budget * {_DEFAULT_SPLIT['accommodation']}
                - activities_budget: total_budget * {_DEFAULT_SPLIT['activities']}
                - meals_budget: total_budget * {_DEFAULT_SPLIT['meals']}

                The four values must add up to total_budget.
                DO NOT use any tools for this calculation - just compute it directly.
                Example: If total_budget = 150000 and no split was stated,
                flights = 150000 * {_DEFAULT_SPLIT['flights']} = {150000 * _DEFAULT_SPLIT['flights']:.0f}
                
                **⚠️⚠️⚠️ BUDGET VALIDATION - VERY IMPORTANT ⚠️⚠️⚠️**
                
                After calculating budget breakdown, CHECK if budget is realistic:
                
                1. **Flight Budget Check:**
                   - International flights typically cost $400-$1500 per person
                   - If flight_budget < $300 per person, flag as "BUDGET_TOO_LOW"
                   
                2. **Hotel Budget Check:**
                   - Calculate: hotel_per_night = accommodation_budget ÷ trip_duration
                   - If hotel_per_night < $30, flag as "BUDGET_TOO_LOW"
                   
                3. **Daily Budget Check:**
                   - Calculate: daily_budget = (activities + meals) ÷ trip_duration
                   - If daily_budget < $30 per person, flag as "BUDGET_TOO_LOW"
                
                **If budget is too low, include:**
                - budget_warning: "BUDGET_TOO_LOW"
                - budget_issue: Explain which component is underfunded
                - minimum_recommended_budget: Calculate what would be realistic
                
                **Preferences:**
                - interests: List of activities/experiences they mentioned
                - travel_style: luxury, moderate, or budget
                - activity_level: high, moderate, or low
                - special_requirements: Any dietary/accessibility needs
                - flexibility: Whether dates/plans are flexible
                
                **IMPORTANT RULES:**
                1. If trip_duration is given but return_date is not, CALCULATE IT:
                   return_date = departure_date + trip_duration days
                   Example: departure_date=2025-12-15, trip_duration=10 → return_date=2025-12-25
                   
                2. If num_adults is not specified, DEFAULT TO 1
                
                3. If travel_style mentions "budget" or "budget friendly", set travel_style="budget"
                
                4. NEVER return status="INCOMPLETE" - always provide your best estimate
                
                5. ALWAYS validate if budget is realistic for the destination and trip duration
                
                **Validation:**
                - confidence_level: high, medium, or low based on completeness
                
                {self.__tip_section()}
            """),
            expected_output=dedent("""
                A structured JSON object with all extracted travel preferences:
                {{
                    "origin": "city_name",
                    "destination": "city_name",
                    "departure_date": "YYYY-MM-DD",
                    "return_date": "YYYY-MM-DD",
                    "trip_duration": X,
                    "total_budget": XXXX,
                    "num_adults": X,
                    "num_children": X,
                    "total_travelers": X,
                    "budget_breakdown": {{
                        "flights": XXXX,
                        "accommodation": XXXX,
                        "activities": XXXX,
                        "meals": XXXX
                    }},
                    "budget_warning": "OK" or "BUDGET_TOO_LOW",
                    "budget_issue": "Explanation if budget is too low",
                    "minimum_recommended_budget": XXXX (if budget too low),
                    "interests": ["interest1", "interest2"],
                    "travel_style": "style",
                    "activity_level": "level",
                    "special_requirements": [],
                    "flexibility": "flexible/fixed",
                    "confidence_level": "high/medium/low"
                }}
                
                ⚠️ If budget is too low, CLEARLY STATE the warning and recommended minimum!
                
                ALWAYS provide complete data - calculate return_date if needed!
            """),
            agent=agent,
            context=[conversation_task],  # ✅ NOW PROPERLY RECEIVES CONVERSATION DATA
            output_json=TravelPreferences  # ✅ STRUCTURED OUTPUT WITH VALIDATION
        )
    
    def coordination_task(self, agent, conversation_id: str, extraction_task,
                          a2a_message_history: str = ""):
        """
        Task for Itinerary Coordinator to create detailed itinerary
        
        Data is received via A2A messages from multiple data provider agents.
        """
        return Task(
            description=dedent(f"""
                You are the Itinerary Coordinator. You receive data via the A2A protocol
                from multiple specialized agents in the system. Below is the complete
                A2A message history containing all information you need.
                
                Conversation ID: {conversation_id}
                
                ═══════════════════════════════════════════════════════════
                📨 A2A MESSAGE HISTORY (formatted for your context)
                ═══════════════════════════════════════════════════════════
                
                {a2a_message_history}
                
                ═══════════════════════════════════════════════════════════
                END OF A2A MESSAGES — use the data above to build the itinerary
                ═══════════════════════════════════════════════════════════
                
                ═══════════════════════════════════════════════════════════
                ⚠️⚠️⚠️ CRITICAL: WRITE ALL DAYS INDIVIDUALLY ⚠️⚠️⚠️
                ═══════════════════════════════════════════════════════════
                
                BEFORE writing: Check the extraction task context for trip_duration
                REQUIREMENT: Create EXACTLY that many "DAY X:" sections with full details
                FORBIDDEN: "[Continue with Days X-Y]" or "Similar to Day 1" = COMPLETE FAILURE
                
                ═══════════════════════════════════════════════════════════
                
                **YOUR PROCESS:**
                
                STEP 1: PRESENT ALL OPTIONS FROM THE A2A MESSAGES
                
                ═══════════════════════════════════════════════════════════
                ✈️ FLIGHT OPTIONS ANALYSIS (from flight_data_provider A2A message)
                ═══════════════════════════════════════════════════════════
                
                Present ALL flights received from the Flight Data Provider:
                
                **YOUR TOP 3 RECOMMENDED FLIGHTS:**
                (Explain WHY based on user preferences)
                
                🥇 BEST OVERALL: [Airline + Price]
                ├─ Why recommended: [2-3 sentences explaining fit]
                ├─ Outbound: [Complete details]
                ├─ Return: [Complete details]
                ├─ Total: $XXX
                ├─ Budget impact: Leaves $XXX for other expenses
                └─ Perfect if you: [User type]
                
                🥈 BEST VALUE: [Same detail]
                🥉 CHEAPEST: [Same detail]
                
                **OTHER OPTIONS:** (Table with remaining flights)
                
                ═══════════════════════════════════════════════════════════
                🏨 HOTEL OPTIONS ANALYSIS (from hotel_data_provider A2A message)
                ═══════════════════════════════════════════════════════════
                
                Present ALL hotels received from the Hotel Data Provider:
                
                **YOUR TOP 3 RECOMMENDED HOTELS:**
                (Explain WHY based on user preferences and review scores)
                
                🥇 BEST OVERALL: [Hotel + Price]
                ├─ Why recommended: [2-3 sentences]
                ├─ Location: [Neighborhood description]
                ├─ Rating: X.X/10 (XXX reviews)
                ├─ Price: $XXX/night ($XXX total)
                ├─ Nearby: [Top attractions from API]
                └─ Perfect if you: [User type]
                
                🥈 BEST VALUE: [Same detail]
                🥉 BEST LOCATION: [Same detail]
                
                **OTHER OPTIONS:** (Table with remaining hotels)
                
                ═══════════════════════════════════════════════════════════
                💡 MY EXPERT RECOMMENDATIONS
                ═══════════════════════════════════════════════════════════
                
                Based on user preferences, recommend:
                - **BEST FLIGHT:** Option X - Why this is perfect [2 paragraphs]
                - **BEST HOTEL:** Option Y - Why this is perfect [2 paragraphs]
                - **TOTAL SO FAR:** $XXX
                - **REMAINING BUDGET:** $XXX for activities/meals
                
                **ALTERNATIVE COMBINATIONS:**
                1. Flight A + Hotel B = $XXX (Most balanced)
                2. Flight C + Hotel D = $XXX (Budget-friendly)
                3. Flight E + Hotel F = $XXX (Premium)
                
                ═══════════════════════════════════════════════════════════
                
                STEP 2: CREATE DETAILED DAILY ITINERARY
                
                Now create EXCEPTIONALLY DETAILED itinerary using:
                - Your recommended flight and hotel
                - Activities from Attraction Agent
                
                ⚠️⚠️⚠️ CRITICAL REQUIREMENT ⚠️⚠️⚠️
                
                You MUST create a detailed plan for EVERY SINGLE DAY.
                - If trip is 7 days: Create Day 1, Day 2, Day 3, Day 4, Day 5, Day 6, Day 7
                - If trip is 5 days: Create Day 1, Day 2, Day 3, Day 4, Day 5
                - If trip is 3 days: Create Day 1, Day 2, Day 3
                
                DO NOT write "Day 1" only and stop.
                DO NOT use "[Repeat for other days]" 
                ACTUALLY WRITE OUT EACH DAY INDIVIDUALLY.
                
                ⚠️⚠️⚠️ ARRIVAL AND DEPARTURE DAYS ⚠️⚠️⚠️
                
                **DAY 1 (ARRIVAL DAY) MUST START WITH:**
                - Flight departure time and airport from origin city
                - Flight arrival time at destination airport
                - Immigration and baggage claim (estimate 1 hour)
                - Transport from airport to hotel (taxi/metro)
                - Hotel check-in time
                - Rest/freshen up at hotel
                - THEN afternoon/evening activities
                
                **LAST DAY (DEPARTURE DAY) MUST END WITH:**
                - Morning activities (if flight is afternoon/evening)
                - Hotel checkout time
                - Transport from hotel to airport (allow 3 hours before flight)
                - Flight departure time from destination
                - Flight arrival time at origin
                - END OF TRIP
                
                **FOR EACH DAY INCLUDE:**
                
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                🌅 DAY X: [Date] - [Theme]
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                
                Note: Day 1 includes flight arrival and hotel check-in
                
                **MORNING (7:00 AM - 12:00 PM)**
                🕐 7:00 AM - Wake Up & Breakfast
                - Where: Hotel restaurant
                - What to order: [Specific items]
                - Cost: $XX
                
                🕐 9:00 AM - Travel to [Attraction]
                - Transport: [Taxi/Metro/Walk + exact route]
                - Duration: XX min
                - Cost: $XX
                
                🕐 9:30 AM - [MAIN ATTRACTION]
                - Full description: [What it is, why visit]
                - Location: [Address]
                - Duration: 2-3 hours
                - Cost: $XX
                - Top 5 highlights:
                  1. [Specific thing to see]
                  2. [Specific thing to see]
                  3. [Specific thing to see]
                  4. [Specific thing to see]
                  5. [Specific thing to see]
                - Insider tips: [3-4 specific tips]
                
                **AFTERNOON (12:00 PM - 6:00 PM)**
                🕐 12:30 PM - Lunch at [Restaurant]
                - Cuisine: [Type]
                - Location: [Address + how to get there]
                - Must-try dishes:
                  1. [Dish] ($XX)
                  2. [Dish] ($XX)
                  3. [Dish] ($XX)
                - Cost: $XX per person
                
                🕐 2:00 PM - [AFTERNOON ACTIVITY]
                - [Complete details like morning]
                
                **EVENING (6:00 PM - 11:00 PM)**
                🕐 6:00 PM - Return to Hotel
                🕐 7:30 PM - Dinner at [Restaurant]
                - [Complete details]
                🕐 9:00 PM - [Evening Activity]
                - [Complete details]
                
                **DAY X SUMMARY:**
                - Total cost: $XXX
                - Walking: X km
                - Energy: High/Medium/Low
                - Tips: [Specific to this day]
                
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                
                ⚠️⚠️⚠️ MANDATORY REQUIREMENT ⚠️⚠️⚠️
                
                WRITE EVERY SINGLE DAY INDIVIDUALLY. NO SHORTCUTS.
                
                ❌ FORBIDDEN: "[Continue with Days X-Y]" or "Similar to Day 1"
                ✅ REQUIRED: trip_duration from extraction = number of "DAY X:" sections
                
                Format for each day:
                ━━━ DAY X: [Date] - [Theme] ━━━
                **MORNING** (7 AM-12 PM): Breakfast + activity with times/costs
                **AFTERNOON** (12 PM-6 PM): Lunch + activity with times/costs  
                **EVENING** (6 PM-11 PM): Dinner + activity with times/costs
                **DAY X SUMMARY:** Total cost, tips
                
                If trip is 15 days → Create Days 1-15 individually
                If trip is 7 days → Create Days 1-7 individually
                
                Before submitting: COUNT your "DAY X:" sections = trip_duration?
                If NO = FAILED. Must write all days.
                
                STEP 3: BUDGET WARNING CHECK
                
                ═══════════════════════════════════════════════════════════
                ⚠️ BUDGET VALIDATION
                ═══════════════════════════════════════════════════════════
                
                CHECK the extraction task output for budget_warning field:
                
                **If budget_warning = "BUDGET_TOO_LOW":**
                
                ⚠️⚠️⚠️ IMPORTANT BUDGET WARNING ⚠️⚠️⚠️
                
                The user's budget of $XXX appears to be TOO LOW for this trip.
                
                **Issue:** [Explain what's underfunded - flights, hotels, or daily expenses]
                
                **Minimum Recommended Budget:** $XXXX
                
                **Options:**
                1. Increase budget to at least $XXXX
                2. Reduce trip duration from X days to Y days
                3. Choose a more budget-friendly destination
                4. Travel during off-peak season
                
                **What we found within your budget:**
                - Cheapest flight: $XXX (but may have long layovers)
                - Cheapest hotel: $XX/night (basic accommodation)
                - Daily activities: $XX (limited to free/low-cost options)
                
                **Proceed with caution** - the itinerary below uses the cheapest options available,
                but you may need to increase your budget for a comfortable trip.
                
                ═══════════════════════════════════════════════════════════
                
                STEP 4: BUDGET BREAKDOWN
                
                ═══════════════════════════════════════════════════════════
                💰 COMPREHENSIVE BUDGET BREAKDOWN
                ═══════════════════════════════════════════════════════════
                
                **FLIGHTS:** $XXX (detailed breakdown)
                **ACCOMMODATION:** $XXX (detailed breakdown)
                **DAILY EXPENSES:**
                - Day 1: $XXX (itemized)
                - Day 2: $XXX (itemized)
                - Day 3: $XXX (itemized)
                - [MUST LIST EVERY DAY - no shortcuts]
                **TRANSPORTATION:** $XXX
                **MISCELLANEOUS:** $XXX
                
                **GRAND TOTAL:** $XXXX
                **ORIGINAL BUDGET:** $XXXX
                **STATUS:** Within budget by $XXX / Over by $XXX
                
                STEP 5: TRAVEL TIPS
                
                Provide comprehensive pre-trip advice, packing lists, local knowledge,
                safety tips, money-saving strategies, and alternative activities.
                
                {self.__tip_section()}
            """),
            expected_output=dedent("""
                An EXTREMELY DETAILED travel itinerary containing:
                
                1. ✅ Executive Summary (destination overview, weather, culture)
                2. ✅ Complete Flight Analysis (all options + recommendations)
                3. ✅ Complete Hotel Analysis (all options + recommendations)
                4. ✅ Expert Recommendations (why these choices are perfect)
                5. ✅ ⚠️ BUDGET WARNING (if budget is too low) - explain the issue and recommendations
                6. ✅ DETAILED DAY-BY-DAY ITINERARY FOR EVERY SINGLE DAY
                   - Hour-by-hour schedule
                   - Complete activity descriptions
                   - Restaurant recommendations with menu items
                   - Transport details
                   - Costs for everything
                   - Insider tips
                7. ✅ Complete Budget Breakdown (itemized for each day)
                8. ✅ Comprehensive Travel Tips
                
                LENGTH: 4000+ words minimum
                QUALITY: Traveler needs NO additional research
                
                ⚠️⚠️⚠️ MANDATORY VALIDATION CHECKLIST ⚠️⚠️⚠️
                
                Before submitting, verify you have included:
                
                - [ ] All flights from A2A flight_data_provider message
                - [ ] All hotels from A2A hotel_data_provider message
                - [ ] Attractions from A2A attraction_data_provider message
                - [ ] Restaurants from A2A restaurant_data_provider message
                - [ ] Budget warning if budget is too low
                - [ ] DAY 1 complete schedule (arrival day)
                - [ ] DAY 2 complete schedule
                - [ ] DAY 3 complete schedule
                - [ ] DAY 4 complete schedule (if trip is 4+ days)
                - [ ] DAY 5 complete schedule (if trip is 5+ days)
                - [ ] DAY 6 complete schedule (if trip is 6+ days)
                - [ ] DAY 7 complete schedule (if trip is 7+ days)
                - [ ] [Continue for each day of the trip]
                - [ ] LAST DAY includes departure/return flight
                - [ ] Budget totals are accurate
                - [ ] NO placeholders or shortcuts
                
                ═══════════════════════════════════════════════════════════
                ⚠️ CRITICAL - READ THIS:
                ═══════════════════════════════════════════════════════════
                
                If the user asked for a 20-day itinerary, you MUST provide:
                DAY 1, DAY 2, DAY 3, DAY 4, DAY 5, DAY 6, DAY 7, DAY 8, DAY 9, DAY 10,
                DAY 11, DAY 12, DAY 13, DAY 14, DAY 15, DAY 16, DAY 17, DAY 18, DAY 19, DAY 20
                
                ALL WITH FULL DETAILS. No shortcuts. No "repeat for other days."
                
                If you stop at Day 2 when user asked for 5 days, THE TASK HAS FAILED.
                
                The trip_duration field tells you EXACTLY how many days to plan.
                PLAN EVERY SINGLE ONE OF THEM.
                
                ❌ UNACCEPTABLE: "Day 1: [details], Days 2-5: Similar activities"
                ✅ ACCEPTABLE: "Day 1: [full details], Day 2: [full details], Day 3: [full details]..."
            """),
            agent=agent,
            context=[extraction_task]
        )
