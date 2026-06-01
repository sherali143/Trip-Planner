"""
Trip Planner Tasks - CrewAI Task Definitions

Defines the workflow tasks for the multi-agent trip planning system.
Each task is assigned to a specific agent and includes context chaining
for A2A communication between agents.

Reference: https://docs.crewai.com/concepts/tasks
"""

from crewai import Task
from textwrap import dedent
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


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
                
                Your goal is to gather complete information about:
                1. **Destination**: Where do they want to go? (be specific about cities)
                2. **Origin**: Where are they traveling from?
                3. **Dates**: When do they want to travel? Are dates flexible?
                4. **Budget**: What is their total budget? How do they prefer to allocate it?
                5. **Interests**: What activities and experiences interest them?
                   (museums, outdoor activities, food, nightlife, shopping, relaxation, etc.)
                6. **Travel Style**: Do they prefer luxury, budget-friendly, or moderate experiences?
                7. **Special Requirements**: Any dietary restrictions, accessibility needs, or 
                   other special considerations?
                
                Ask follow-up questions as needed. Be warm, engaging, and helpful. Once you 
                have gathered comprehensive information, clearly indicate that the conversation 
                is complete and ready for data extraction.
                
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
                Calculate the exact budget allocations (simple math):
                - flights_budget: total_budget * 0.35 (35% of total)
                - accommodation_budget: total_budget * 0.35 (35% of total)
                - activities_budget: total_budget * 0.20 (20% of total)
                - meals_budget: total_budget * 0.10 (10% of total)
                
                DO NOT use any tools for this calculation - just compute it directly.
                Example: If total_budget = 150000, then flights = 150000 * 0.35 = 52500
                
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
    
    def flight_search_task(self, agent, conversation_id: str, extraction_task):
        """
        Task for Flight Search Agent to find flights
        
        NOW INCLUDES: Proper context from extraction task
        """
        return Task(
            description=dedent(f"""
                You have received structured travel preferences via the extraction task context.
                
                ⚠️⚠️⚠️ CRITICAL: USE EXACT DATES FROM EXTRACTION ⚠️⚠️⚠️
                
                ACCESS THE PREFERENCES LIKE THIS:
                - preferences = context from extraction_task
                - origin = preferences['origin']
                - destination = preferences['destination']
                - departure_date = preferences['departure_date']  ← USE THIS EXACT DATE
                - return_date = preferences['return_date']  ← USE THIS EXACT DATE
                - flight_budget = preferences['budget_breakdown']['flights']
                - adults = preferences['total_travelers']  ← USE THIS EXACT NUMBER
                
                Conversation ID: {conversation_id}
                
                **Your Mission:**
                Use the "Search comprehensive flights" tool to find real flights within budget.
                
                **MANDATORY STEPS:**
                1. READ the extraction task output CAREFULLY
                2. USE THE EXACT departure_date and return_date - DO NOT CHANGE THEM
                3. Convert city names to IATA codes:
                   - Islamabad → ISB
                   - Doha → DOH
                   - Dubai → DXB
                   - London → LHR
                   - Paris → CDG
                   - New York → JFK
                4. Call "Search comprehensive flights" with:
                   - origin: IATA code (e.g., "ISB")
                   - destination: IATA code (e.g., "DOH")
                   - departure_date: EXACT date from extraction (YYYY-MM-DD)
                   - return_date: EXACT date from extraction (YYYY-MM-DD)
                   - adults: number from extraction
                   - budget: flight budget from extraction
                5. Present flight options with complete details
                6. If API fails, use search_internet as backup
                
                **EXAMPLE:**
                If extraction says departure_date="2025-12-15", return_date="2025-12-25"
                You MUST search for flights on 2025-12-15 returning 2025-12-25
                NOT 2026, NOT different dates!
                
                **FOR EACH FLIGHT INCLUDE:**
                - Airline, flight number
                - Departure/arrival times and airports
                - Total duration and stops
                - Price per person and total price
                - Whether it's within budget
                
                **BUDGET COMPLIANCE:**
                - flight_budget from extraction task = HARD LIMIT
                - Only show flights ≤ this amount
                - If no flights fit, clearly state and show cheapest option
                
                CRITICAL: Return REAL data from tools. No fake information.
                CRITICAL: USE THE EXACT DATES FROM EXTRACTION - DO NOT MODIFY THEM!
                
                {self.__tip_section()}
            """),
            expected_output=dedent("""
                Comprehensive flight search results with 5 real options:
                
                {{
                    "search_summary": {{
                        "origin": "string",
                        "destination": "string",
                        "departure_date": "string",
                        "return_date": "string",
                        "flight_budget_limit": number,
                        "total_options_found": number
                    }},
                    "all_flights": [
                        {{
                            "option_id": "FLIGHT-001",
                            "airline": "string",
                            "flight_number": "string",
                            "outbound": {{ detailed flight info }},
                            "return": {{ detailed flight info }},
                            "pricing": {{ complete breakdown }},
                            "booking_link": "url",
                            "analysis": {{
                                "pros": [],
                                "cons": [],
                                "recommendation_score": number
                            }}
                        }}
                    ],
                    "categorized_options": {{
                        "cheapest_5": [],
                        "fastest_5": [],
                        "best_value_5": []
                    }}
                }}
                
                Return TOP 5 complete flight options with REAL API data!
            """),
            agent=agent,
            context=[extraction_task]  # ✅ RECEIVES STRUCTURED PREFERENCES
        )
    
    def hotel_search_task(self, agent, conversation_id: str, extraction_task):
        """
        Task for Hotel Agent to find hotels
        
        NOW INCLUDES: Proper context and mandatory validation
        """
        return Task(
            description=dedent(f"""
                You have received structured travel preferences via the extraction task context.
                
                ACCESS THE PREFERENCES LIKE THIS:
                - preferences = context from extraction_task
                - destination = preferences['destination']
                - checkin = preferences['departure_date']
                - checkout = preferences['return_date']
                - nights = preferences['trip_duration']
                - hotel_budget = preferences['budget_breakdown']['accommodation']
                
                Conversation ID: {conversation_id}
                
                **Your Mission:**
                Use Booking.com API tools to find real hotels within budget.
                
                **MANDATORY PROCESS - YOU CANNOT SKIP STEPS:**
                
                STEP 1: ✅ Use "Search hotel destination" tool
                   - Input: destination city name
                   - Extract: dest_id from response
                   - If this fails, STOP and report error
                
                STEP 2: ✅ Use "Search hotels by destination" tool
                   - Input: dest_id, arrival_date, departure_date, adults=2, room_qty=1
                   - Get TOP 5 hotels with prices
                   - If this fails, STOP and report error
                
                STEP 3: ✅ Calculate budget limit
                   - Use calculator: hotel_budget ÷ nights = max_per_night
                   - Filter: keep only hotels where price ≤ max_per_night
                
                STEP 4: ✅ Use "Get hotel reviews" tool
                   - For EACH hotel (top 5), get reviews
                   - Extract: review_score, number_of_reviews
                   - Sort by review_score (highest first)
                
                STEP 5: ✅ Pick TOP 3 hotels (highest rated within budget)
                
                STEP 6: ✅ Use "Get attractions near hotel" tool
                   - For your TOP 3, get nearby attractions
                   - This helps user make decision
                
                **FOR EACH HOTEL INCLUDE:**
                - Name, star rating, address
                - Review score (X.X/10) and number of reviews
                - Price per night and total cost
                - Complete amenities list
                - Nearby attractions (from API)
                - Neighborhood description
                - Pros/cons analysis
                - Booking links
                
                **OUTPUT VALIDATION:**
                ⚠️ Your output MUST include:
                - [ ] dest_id obtained from Step 1
                - [ ] At least 5 hotels from Step 2
                - [ ] Review scores for each from Step 4
                - [ ] Attractions for top 3 from Step 6
                - [ ] Complete details for each hotel
                
                IF ANY STEP FAILS, explicitly state which step and why.
                "No data available" is UNACCEPTABLE - use the tools!
                
                {self.__tip_section()}
            """),
            expected_output=dedent("""
                COMPREHENSIVE hotel search results RANKED BY REVIEW SCORES:
                
                ═══════════════════════════════════════════════════════════
                🏆 TOP 3 RECOMMENDED HOTELS
                ═══════════════════════════════════════════════════════════
                
                #1. [Hotel Name] - Review Score: X.X/10 (XXX reviews)
                    - Price: $XX/night ($XXX total)
                    - Location: [Neighborhood + description]
                    - Nearby Attractions: [From API - list top 5]
                    - Why recommended: [Based on reviews + user preferences]
                    - Booking link: [URL]
                
                #2. [Hotel Name] - [Same complete details]
                #3. [Hotel Name] - [Same complete details]
                
                ═══════════════════════════════════════════════════════════
                📋 ALL HOTEL OPTIONS (5 hotels sorted by review score)
                ═══════════════════════════════════════════════════════════
                
                Provide JSON structure with complete hotel data as specified.
                
                Return TOP 5 complete hotel options with REAL API data!
                
                ═══════════════════════════════════════════════════════════
                ⚠️ VALIDATION REQUIREMENTS - YOUR OUTPUT MUST INCLUDE:
                ═══════════════════════════════════════════════════════════
                ✅ At least 5 hotels with complete information
                ✅ Review scores from Booking.com API for each hotel
                ✅ Nearby attractions for top 3 recommended hotels
                ✅ Complete pricing information (per night + total)
                ✅ NO "missing data" or "not available" responses
                
                ❌ If any of these are missing, the task has FAILED and you must try again.
            """),
            agent=agent,
            context=[extraction_task]  # ✅ RECEIVES STRUCTURED PREFERENCES
        )
    
    def attraction_search_task(self, agent, conversation_id: str, extraction_task):
        """
        Task for Attraction Agent to find activities
        
        NOW INCLUDES: Proper context from extraction and budget tracking
        """
        return Task(
            description=dedent(f"""
                You have received structured travel preferences via the extraction task context.
                
                ACCESS THE PREFERENCES LIKE THIS:
                - preferences = context from extraction_task
                - destination = preferences['destination']
                - interests = preferences['interests']
                - trip_duration = preferences['trip_duration']
                - activities_budget = preferences['budget_breakdown']['activities']
                - meals_budget = preferences['budget_breakdown']['meals']
                
                Conversation ID: {conversation_id}
                
                **Your Mission:**
                Find comprehensive activity and restaurant options within budget.
                
                **PROCESS:**
                1. Calculate daily budget: (activities_budget + meals_budget) ÷ trip_duration
                2. Use search_attractions tool with destination and interests
                3. Use search_restaurants tool for dining options
                4. Use search_internet extensively for:
                   - Current events during travel dates
                   - Hidden gems and local favorites
                   - Recently opened spots
                   - Festival or seasonal events
                
                **FOR EACH DAY, PROVIDE:**
                - Morning activity (9 AM - 12 PM) with complete details
                - Lunch recommendation with 3 menu items and prices
                - Afternoon activity (2 PM - 6 PM) with complete details
                - Dinner recommendation with 3 menu items and prices
                - Evening activity or rest option
                - Coffee/snack spots
                - Daily cost total (must be ≤ daily_budget)
                - Transport details between locations
                
                **FOR EACH ATTRACTION:**
                - Full description (what it is, why special)
                - Exact address and transport from hotel
                - Opening hours and best visiting time
                - Entry cost and booking needs
                - Duration needed (realistic)
                - Top 5 highlights to see
                - Insider tips
                
                **FOR EACH RESTAURANT:**
                - Full description of cuisine and ambiance
                - 3-5 signature dishes with prices
                - Price range per person
                - Reservation requirements
                - Why recommended
                - Alternative nearby options
                
                **BUDGET TRACKING:**
                - Track spending for each day
                - Mix free/low-cost with paid activities
                - Ensure daily total ≤ daily_budget
                - Provide budget-friendly alternatives
                
                {self.__tip_section()}
            """),
            expected_output=dedent("""
                COMPREHENSIVE attraction and restaurant guide for EACH day:
                
                {{
                    "daily_budget": number,
                    "daily_itinerary": [
                        {{
                            "day": 1,
                            "date": "string",
                            "theme": "string",
                            "morning_activity": {{
                                "name": "string",
                                "description": "detailed 2-3 sentences",
                                "address": "full address",
                                "transport": "how to get there",
                                "duration": "X hours",
                                "cost": "$XX",
                                "opening_hours": "string",
                                "highlights": ["top 5 things to see"],
                                "insider_tips": ["tip 1", "tip 2"]
                            }},
                            "lunch": {{
                                "restaurant_name": "string",
                                "cuisine": "string",
                                "signature_dishes": ["dish 1 ($XX)", "dish 2", "dish 3"],
                                "price_range": "$XX-XX",
                                "why_recommended": "string"
                            }},
                            "afternoon_activity": {{ same detail }},
                            "dinner": {{ same detail }},
                            "evening_activity": {{ same detail }},
                            "day_summary": {{
                                "total_cost": "$XXX",
                                "within_budget": true/false
                            }}
                        }}
                    ]
                }}
                
                Provide EXTENSIVE detail for EACH DAY of the trip!
            """),
            agent=agent,
            context=[extraction_task]  # ✅ RECEIVES STRUCTURED PREFERENCES
        )
    
    def coordination_task(self, agent, conversation_id: str, extraction_task, flight_task, hotel_task, attraction_task):
        """
        Task for Itinerary Coordinator to create detailed itinerary
        
        NOW INCLUDES: All context from previous tasks + detailed instructions
        """
        return Task(
            description=dedent(f"""
                You are the Itinerary Coordinator. You will receive COMPLETE DATA from:
                1. Extraction Task: User preferences and budget breakdown
                2. Flight Task: Top 5 flight options with complete details
                3. Hotel Task: Top 5 hotel options with reviews and locations
                4. Attraction Task: Daily activity and restaurant suggestions
                
                Conversation ID: {conversation_id}
                
                ═══════════════════════════════════════════════════════════
                ⚠️⚠️⚠️ CRITICAL: WRITE ALL DAYS INDIVIDUALLY ⚠️⚠️⚠️
                ═══════════════════════════════════════════════════════════
                
                BEFORE writing: Check extraction task for trip_duration (e.g., 15 days)
                REQUIREMENT: Create EXACTLY that many "DAY X:" sections with full details
                FORBIDDEN: "[Continue with Days X-Y]" or "Similar to Day 1" = COMPLETE FAILURE
                
                ═══════════════════════════════════════════════════════════
                
                **YOUR PROCESS:**
                
                STEP 1: PRESENT ALL OPTIONS
                
                ═══════════════════════════════════════════════════════════
                ✈️ FLIGHT OPTIONS ANALYSIS
                ═══════════════════════════════════════════════════════════
                
                Present ALL flights received from Flight Agent:
                
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
                🏨 HOTEL OPTIONS ANALYSIS
                ═══════════════════════════════════════════════════════════
                
                Present ALL hotels received from Hotel Agent:
                
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
                
                - [ ] All flights from Flight Agent presented
                - [ ] All hotels from Hotel Agent presented
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
            context=[extraction_task, flight_task, hotel_task, attraction_task]  # ✅ ALL CONTEXT
        )
