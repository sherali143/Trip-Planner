# # To know more about the Task class, visit: https://docs.crewai.com/concepts/tasks
# from crewai import Task
# from textwrap import dedent
# from typing import Dict, Any


# class TripPlannerTasks:
#     """
#     Trip Planner Tasks with A2A Protocol Integration
    
#     These tasks orchestrate the workflow of the trip planning system,
#     enabling agent-to-agent communication through structured data exchange.
#     """
    
#     def __tip_section(self):
#         return "If you do your BEST WORK, I'll give you a $10,000 commission!"
    
#     def conversation_task(self, agent, user_input: str, conversation_id: str):
#         """
#         Task for the Conversational Agent to engage with the user
#         and gather travel requirements
#         """
#         return Task(
#             description=dedent(f"""
#                 Engage the user in a natural, friendly conversation to understand their 
#                 travel needs. The user has provided the following initial input:
                
#                 User Input: {user_input}
#                 Conversation ID: {conversation_id}
                
#                 Your goal is to gather complete information about:
#                 1. **Destination**: Where do they want to go? (be specific about cities)
#                 2. **Origin**: Where are they traveling from?
#                 3. **Dates**: When do they want to travel? Are dates flexible?
#                 4. **Budget**: What is their total budget? How do they prefer to allocate it?
#                 5. **Interests**: What activities and experiences interest them?
#                    (museums, outdoor activities, food, nightlife, shopping, relaxation, etc.)
#                 6. **Travel Style**: Do they prefer luxury, budget-friendly, or moderate experiences?
#                 7. **Special Requirements**: Any dietary restrictions, accessibility needs, or 
#                    other special considerations?
                
#                 Ask follow-up questions as needed. Be warm, engaging, and helpful. Once you 
#                 have gathered comprehensive information, clearly indicate that the conversation 
#                 is complete and ready for data extraction.
                
#                 {self.__tip_section()}
#             """),
#             expected_output=dedent("""
#                 A complete conversation transcript including:
#                 - All user responses and clarifications
#                 - Confirmation of collected information
#                 - Clear indication that information gathering is complete
#                 - Summary of key travel requirements
#             """),
#             agent=agent
#         )
    
#     def extraction_task(self, agent, conversation_id: str):
#         """
#         Task for the Preferences Extractor to structure conversation data
#         for downstream agents (A2A communication)
#         """
#         return Task(
#             description=dedent(f"""
#                 Analyze the conversation transcript from the Conversational Agent and extract
#                 all travel preferences into a structured format.
                
#                 Conversation ID: {conversation_id}
                
#                 Extract and structure the following information:
                
#                 **Required Fields:**
#                 - origin: Origin city/airport
#                 - destination: Destination city
#                 - departure_date: When they're leaving (YYYY-MM-DD format)
#                 - return_date: When they're returning (YYYY-MM-DD format)
#                 - trip_duration: Number of days
#                 - total_budget: Total budget amount
                
#                 **Budget Breakdown:**
#                 Provide reasonable allocations (simple percentages):
#                 - flights_budget: ~40% of total (adjustable based on distance)
#                 - accommodation_budget: ~30% of total (adjust for travel style)
#                 - activities_budget: ~20% of total
#                 - meals_budget: ~10% of total
                
#                 **Preferences:**
#                 - interests: List of activities/experiences they mentioned
#                 - travel_style: luxury, moderate, or budget
#                 - activity_level: high, moderate, or low
#                 - special_requirements: Any dietary/accessibility needs
#                 - flexibility: Whether dates/plans are flexible
                
#                 **Validation:**
#                 - missing_info: List any critical missing information
#                 - confidence_level: high, medium, or low based on completeness
                
#                 NOTE: Just extract and structure the information - no complex calculations needed.
                
#                 {self.__tip_section()}
#             """),
#             expected_output=dedent("""
#                 A structured JSON object with all extracted travel preferences:
#                 {{
#                     "origin": "city_name",
#                     "destination": "city_name",
#                     "departure_date": "YYYY-MM-DD",
#                     "return_date": "YYYY-MM-DD",
#                     "trip_duration": X,
#                     "total_budget": XXXX,
#                     "budget_breakdown": {{
#                         "flights": XXXX,
#                         "accommodation": XXXX,
#                         "activities": XXXX,
#                         "meals": XXXX
#                     }},
#                     "interests": ["interest1", "interest2", ...],
#                     "travel_style": "style",
#                     "activity_level": "level",
#                     "special_requirements": [...],
#                     "flexibility": "flexible/fixed",
#                     "missing_info": [...],
#                     "confidence_level": "high/medium/low"
#                 }}
#             """),
#             agent=agent,
#             context=[]  # Will receive context from conversation_task
#         )
    
#     def flight_search_task(self, agent, conversation_id: str):
#         """
#         Task for Flight Search Agent to find ALL available flights using MCP servers
#         and send comprehensive results via A2A protocol
#         """
#         return Task(
#             description=dedent(f"""
#                 You have received structured travel preferences via A2A protocol.
#                 Use the MCP flight search tools to find ALL available flight options.
                
#                 Conversation ID: {conversation_id}
                
#                 **Your Mission:**
#                 RETRIEVE FLIGHT OPTIONS WITHIN THE ALLOCATED FLIGHT BUDGET!
                
#                 **BUDGET CONSTRAINT:** You will receive a flight budget allocation.
#                 ONLY present flights that are at or below this budget limit.
#                 If no flights fit the budget, clearly state this and show the cheapest available option.
                
#                 1. **Use the search_round_trip_flights tool:**
#                    - Use the search round trip flights tool with source and destination
#                    - Source format: "Country:US" or "City:new_york"
#                    - Destination format: "Country:FR" or "City:paris_fr"
#                    - The tool will return comprehensive flight data from Kiwi.com API
#                    - Also use search_internet for additional flight deals if needed
                
#                 2. **Gather COMPREHENSIVE data for EACH flight option:**
#                    For every flight found, include:
#                    - Airline name and flight number
#                    - Aircraft type
#                    - Exact departure time and airport (with terminal if available)
#                    - Exact arrival time and airport (with terminal if available)
#                    - Total flight duration
#                    - Number of stops (nonstop, 1 stop, 2+ stops)
#                    - Layover details if applicable
#                    - Price breakdown (base fare, taxes, fees)
#                    - Total price
#                    - Baggage allowance (checked, carry-on)
#                    - Seat selection info
#                    - In-flight amenities (meals, WiFi, entertainment)
#                    - Cancellation policy
#                    - Booking link or reference (VERY IMPORTANT)
                
#                 3. **Organize results by categories:**
#                    - Cheapest options (lowest 5 prices)
#                    - Fastest options (shortest duration)
#                    - Best value options (good price + convenience)
#                    - Premium options (more comfort, better airlines)
#                    - Budget options (basic, no frills)
                
#                 4. **For EACH flight, analyze:**
#                    - Pros (what's good about this option)
#                    - Cons (what are the downsides)
#                    - Best for: (what type of traveler)
#                    - Recommendation score (1-10)
                
#                 5. **Do NOT pre-select or filter out options yet**
#                    - Return 10-15 flight options minimum
#                    - Include options at different price points
#                    - Include options with different durations
#                    - The Itinerary Coordinator will help user choose
                
#                 6. **Calculate costs:**
#                    - Total cost for each flight option
#                    - Compare against user's flight budget
#                    - Show how much budget remains for other activities
                
#                 **Important:** You are gathering data, not making the final choice.
#                 Present ALL viable options with complete information so the user
#                 can make an informed decision with the coordinator's help.
                
#                 {self.__tip_section()}
#             """),
#             expected_output=dedent("""
#                 COMPREHENSIVE flight search results with ALL options:
#                 {{
#                     "search_summary": {{
#                         "origin": "string",
#                         "destination": "string",
#                         "departure_date": "string",
#                         "return_date": "string",
#                         "passengers": number,
#                         "total_options_found": number,
#                         "link_of_flight": url,
#                         "sources_searched": ["Kiwi.com", "Fly-Scraper", "Web Search"]
#                     }},
#                     "all_flights": [
#                         {{
#                             "option_id": "FLIGHT-001",
#                             "airline": "string",
#                             "flight_number": "string",
#                             "aircraft": "string",
#                             "outbound": {{
#                                 "departure_airport": "string",
#                                 "departure_terminal": "string",
#                                 "departure_time": "string",
#                                 "arrival_airport": "string",
#                                 "arrival_terminal": "string",
#                                 "arrival_time": "string",
#                                 "duration": "string",
#                                 "stops": number,
#                                 "layover_details": ["string"]
#                             }},
#                             "return": {{...same structure}},
#                             "pricing": {{
#                                 "base_fare": number,
#                                 "taxes_fees": number,
#                                 "total_price": number,
#                                 "currency": "USD",
#                                 "price_per_person": number
#                             }},
#                             "baggage": {{
#                                 "checked": "string",
#                                 "carry_on": "string",
#                                 "additional_fees": number
#                             }},
#                             "amenities": {{
#                                 "meals": "string",
#                                 "wifi": "string",
#                                 "entertainment": "string",
#                                 "seat_selection": "string"
#                             }},
#                             "policies": {{
#                                 "cancellation": "string",
#                                 "changes": "string"
#                             }},
#                             "booking_info": {{
#                                 "link": "string",
#                                 "reference": "string"
#                             }},
#                             "analysis": {{
#                                 "pros": ["string", "string"],
#                                 "cons": ["string", "string"],
#                                 "best_for": "string",
#                                 "recommendation_score": number,
#                                 "value_rating": "excellent/good/fair/poor"
#                             }}
#                         }}
#                     ],
#                     "categorized_options": {{
#                         "cheapest_5": ["FLIGHT-001", "FLIGHT-003", ...],
#                         "fastest_5": ["FLIGHT-002", "FLIGHT-005", ...],
#                         "best_value_5": ["FLIGHT-004", "FLIGHT-001", ...],
#                         "premium_options": ["FLIGHT-006", ...],
#                         "nonstop_only": ["FLIGHT-002", ...]
#                     }},
#                     "budget_analysis": {{
#                         "user_flight_budget": number,
#                         "cheapest_option": number,
#                         "most_expensive": number,
#                         "average_price": number,
#                         "options_within_budget": number,
#                         "recommendation": "string"
#                     }}
#                 }}
                
#                 Return AT LEAST 10-15 complete flight options with full details!
#             """),
#             agent=agent,
#             context=[]  # Will receive context from extraction_task
#         )
    
#     def hotel_search_task(self, agent, conversation_id: str):
#         """
#         Task for Hotel Agent to find ALL available accommodations using MCP servers
#         and send comprehensive results via A2A protocol
#         """
#         return Task(
#             description=dedent(f"""
#                 You have received structured travel preferences via A2A protocol.
#                 Use the MCP hotel search tools to find ALL available accommodation options.
                
#                 Conversation ID: {conversation_id}
                
#                 **Your Mission:**
#                 RETRIEVE HOTEL OPTIONS WITHIN THE ALLOCATED ACCOMMODATION BUDGET!
                
#                 **BUDGET CONSTRAINT:** You will receive an accommodation budget allocation.
#                 Calculate: max_per_night = accommodation_budget ÷ number_of_nights
#                 ONLY present hotels at or below this nightly rate.
#                 If no hotels fit the budget, clearly state this and show cheapest options.
                
#                 1. **Use the Booking.com API tools in sequence (MANDATORY):**
                   
#                    STEP 1: Use 'Search hotel destination' tool
#                       - Input: destination city name
#                       - Output: Extract dest_id from response data array
                   
#                    STEP 2: Use 'Search hotels by destination' tool
#                       - Input: dest_id, arrival_date, departure_date, adults, room_qty
#                       - Output: List of hotels with hotel_id, prices, basic info
#                       - Get at least 10-15 hotel options
                   
#                    STEP 3: For EACH of the top 10 hotels from results:
#                       - Use 'Get hotel reviews' tool with hotel_id
#                       - Extract: review_score, total_reviews, score_breakdown
#                       - This is CRITICAL for ranking hotels
                   
#                    STEP 4: For your TOP 3 recommended hotels (highest review scores):
#                       - Use 'Get attractions near hotel' tool with hotel_id
#                       - This shows what's nearby to help user decide
                   
#                    STEP 5: Use 'Search the internet' for additional context
#                       - Search "[hotel name] reviews"
#                       - Search "best hotels in [destination]"
                
#                 2. **Gather COMPREHENSIVE data for EACH hotel option:**
#                    For every hotel found, include:
#                    **SAVE THIS INFORMATION VERY IMPORTANT**
#                    - Hotel name and brand
#                    - Full address and neighborhood description
#                    - Star rating (1-5 stars)
#                    - Guest review score (out of 10)
#                    - Number of reviews
#                    - Distance to city center / main attractions
#                    - Room types available (standard, deluxe, suite)
#                    - Price per night for each room type
#                    - Total cost for entire stay
#                    - Check-in/check-out times
#                    - Amenities list:
#                      * Free WiFi, breakfast, parking
#                      * Pool, gym, spa
#                      * Restaurant, bar, room service
#                      * Air conditioning, elevator
#                      * Laundry, concierge, etc.
#                    - Cancellation policy
#                    - Photos available (yes/no)
#                    - Booking platforms where available
#                    - Recent reviews highlights
#                    - Safety features
                
#                 3. **RANK hotels by review scores (MOST IMPORTANT):**
#                    - Sort all hotels by review score (highest first)
#                    - Your TOP 3 recommendations must be highest rated
#                    - Also categorize by:
#                      * Best overall (high rating + good price)
#                      * Best value (good rating, lower price)
#                      * Best location (high rating + near attractions)
#                      * Budget options (under $100/night with decent ratings)
#                      * Mid-range options ($100-200/night)
#                      * Luxury options ($200+/night with excellent ratings)
                
#                 4. **For EACH hotel, analyze:**
#                    - Pros (what's great about this property)
#                    - Cons (what are the downsides)
#                    - Best for: (couples, families, solo travelers, etc.)
#                    - Location score (1-10 for convenience)
#                    - Value score (1-10 for price vs quality)
#                    - Overall recommendation score (1-10)
                
#                 5. **Include neighborhood information:**
#                    For each hotel's area, describe:
#                    - Neighborhood character (quiet, lively, touristy, local)
#                    - Safety level
#                    - Nearby restaurants and shops
#                    - Public transport access
#                    - Walking distance to major sights
#                    - Parking availability
                
#                 6. **Do NOT pre-select or filter out options yet**
#                    - Return 10-15 hotel options minimum
#                    - Include options at different price points
#                    - Include options in different neighborhoods
#                    - The Itinerary Coordinator will help user choose
                
#                 7. **Calculate costs:**
#                    - Nightly rate × number of nights
#                    - Total accommodation cost for trip
#                    - Resort fees, taxes (if applicable)
#                    - Compare against user's accommodation budget
                
#                 8. **Additional options (if relevant):**
#                    - Vacation rentals (Airbnb-style)
#                    - Boutique hotels
#                    - Hostels (if budget-conscious)
#                    - Bed & Breakfasts
                
#                 **Important:** You are gathering data, not making the final choice.
#                 Present ALL viable options with complete information so the user
#                 can make an informed decision with the coordinator's help.
                
#                 {self.__tip_section()}
#             """),
#             expected_output=dedent("""
#                 COMPREHENSIVE hotel search results RANKED BY REVIEW SCORES:
                
#                 ===========================================================
#                 🏆 TOP 3 RECOMMENDED HOTELS (Ranked by Review Score)
#                 ===========================================================
                
#                 #1. [Hotel Name] - Review Score: X.X/10 (XXX reviews)
#                     - Price: $XX/night ($XXX total)
#                     - Location: [Neighborhood]
#                     - Nearby Attractions: [From API - list top 5]
#                     - Amenities: [List key amenities]
#                     - Why recommended: [Based on high reviews and user preferences]
                
#                 #2. [Hotel Name] - Review Score: X.X/10 (XXX reviews)
#                     [Same details]
                
#                 #3. [Hotel Name] - Review Score: X.X/10 (XXX reviews)
#                     [Same details]
                                   
#                 (also add information about the hotel you get from the tool about why this hotel is recommended)
                
#                 ===========================================================
#                 📋 ALL HOTEL OPTIONS (Sorted by Review Score)
#                 ===========================================================
                
#                 Present 10-15 hotels with REAL data from API:
#                 {{
#                     "search_summary": {{
#                         "destination": "string",
#                         "checkin_date": "string",
#                         "checkout_date": "string",
#                         "nights": number,
#                         "guests": number,
#                         "total_options_found": number,
#                         "sources_searched": ["Booking.com", "Web Search"]
#                     }},
#                     "all_hotels": [
#                         {{
#                             "option_id": "HOTEL-001",
#                             "name": "string",
#                             "brand": "string",
#                             "star_rating": number,
#                             "guest_rating": {{
#                                 "score": number,
#                                 "out_of": 10,
#                                 "review_count": number,
#                                 "rating_description": "Excellent/Very Good/Good/Fair"
#                             }},
#                             "location": {{
#                                 "full_address": "string",
#                                 "neighborhood": "string",
#                                 "neighborhood_description": "detailed description",
#                                 "distance_to_center": "string",
#                                 "distance_to_attractions": {{
#                                     "attraction_name": "distance"
#                                 }},
#                                 "public_transport": "string",
#                                 "safety_level": "high/medium/low",
#                                 "location_score": number
#                             }},
#                             "rooms": [
#                                 {{
#                                     "type": "Standard Double Room",
#                                     "price_per_night": number,
#                                     "total_cost": number,
#                                     "sleeps": number,
#                                     "bed_type": "string",
#                                     "size_sqm": number
#                                 }}
#                             ],
#                             "pricing": {{
#                                 "lowest_rate_per_night": number,
#                                 "total_for_stay": number,
#                                 "taxes_fees": number,
#                                 "resort_fee": number,
#                                 "total_with_fees": number,
#                                 "cancellation_fee": "string"
#                             }},
#                             "amenities": {{
#                                 "free": ["WiFi", "breakfast", "..."],
#                                 "paid": ["parking $XX", "spa", "..."],
#                                 "room_features": ["AC", "TV", "minibar", "..."],
#                                 "hotel_facilities": ["pool", "gym", "restaurant", "..."]
#                             }},
#                             "policies": {{
#                                 "checkin_time": "string",
#                                 "checkout_time": "string",
#                                 "cancellation": "string",
#                                 "pet_policy": "string",
#                                 "children_policy": "string"
#                             }},
#                             "reviews": {{
#                                 "recent_positive": ["string", "string"],
#                                 "recent_negative": ["string", "string"],
#                                 "most_praised": "string",
#                                 "most_criticized": "string"
#                             }},
#                             "booking_info": {{
#                                 "platforms": ["Booking.com", "Expedia", "..."],
#                                 "links": {{"platform": "url"}},
#                                 "deals_available": "string"
#                             }},
#                             "analysis": {{
#                                 "pros": ["string", "string", "string"],
#                                 "cons": ["string", "string"],
#                                 "best_for": "couples/families/solo/business",
#                                 "value_score": number,
#                                 "location_score": number,
#                                 "overall_score": number,
#                                 "recommendation": "string"
#                             }}
#                         }}
#                     ],
#                     "categorized_options": {{
#                         "budget_picks": ["HOTEL-001", "HOTEL-003", ...],
#                         "mid_range_picks": ["HOTEL-002", ...],
#                         "luxury_picks": ["HOTEL-006", ...],
#                         "best_location": ["HOTEL-004", ...],
#                         "best_value": ["HOTEL-001", ...],
#                         "highest_rated": ["HOTEL-005", ...],
#                         "family_friendly": ["HOTEL-007", ...],
#                         "romantic": ["HOTEL-008", ...]
#                     }},
#                     "neighborhood_guide": {{
#                         "neighborhood_name": {{
#                             "description": "string",
#                             "pros": ["string"],
#                             "cons": ["string"],
#                             "hotels_in_area": ["HOTEL-001", ...]
#                         }}
#                     }},
#                     "budget_analysis": {{
#                         "user_accommodation_budget": number,
#                         "cheapest_option": number,
#                         "most_expensive": number,
#                         "average_price": number,
#                         "options_within_budget": number,
#                         "recommendation": "string"
#                     }}
#                 }}
                
#                 ⚠️ CRITICAL REQUIREMENTS - YOUR OUTPUT MUST INCLUDE:
#                 - [ ] dest_id obtained from "Search hotel destination" tool
#                 - [ ] At least 10-15 hotels from "Search hotels by destination" tool
#                 - [ ] Review scores for each hotel from "Get hotel reviews" tool
#                 - [ ] Nearby attractions for top 3 hotels from "Get attractions near hotel" tool
#                 - [ ] Complete details for each hotel (name, price, rating, amenities, address)
                
#                 IF YOU RETURN "No data available" or "Missing hotel information", YOU HAVE FAILED.
#                 USE THE TOOLS. THEY WORK. GET THE DATA.
                
#                 Return AT LEAST 10-15 complete hotel options with full details!
#             """),
#             agent=agent,
#             context=[]  # Will receive context from extraction_task
#         )
    
#     def attraction_search_task(self, agent, conversation_id: str):
#         """
#         Task for Attraction Agent to discover activities using MCP-style search tools
#         and send categorized results via A2A protocol
#         """
#         return Task(
#             description=dedent(f"""
#                 You have received structured travel preferences via A2A protocol.
#                 Use the MCP-style attraction and restaurant search tools to discover amazing experiences.
                
#                 Conversation ID: {conversation_id}
                
#                 **Your Mission:**
#                 Provide DETAILED, COMPREHENSIVE activity and restaurant recommendations WITHIN BUDGET!
                
#                 **BUDGET CONSTRAINT:** You will receive activity and meal budget allocations.
#                 Calculate: daily_budget = (activities_budget + meals_budget) ÷ trip_duration
#                 Suggest a balanced mix of activities and meals that fit within this daily limit.
#                 Include free/low-cost options to balance expensive ones.
                
#                 1. Use the search_attractions tool with user interests
#                 2. Use the search_restaurants tool to find dining options
#                 3. Search the internet extensively for:
#                    - Current events happening during their travel dates
#                    - Special exhibitions or temporary attractions
#                    - Local festivals or celebrations
#                    - Hidden gems and off-the-beaten-path experiences
#                    - Recently opened restaurants or hot spots
                
#                 4. For EACH attraction, research and provide:
#                    - Full description (what it is, why it's special)
#                    - Exact address and how to get there
#                    - Opening hours and best time to visit
#                    - Entry cost and booking requirements
#                    - Duration needed (realistic time estimate)
#                    - Top highlights (what to see/do there)
#                    - Insider tips (what locals know)
#                    - Photo opportunities
#                    - Nearby cafes or facilities
                
#                 5. For EACH restaurant, provide:
#                    - Full description of cuisine and ambiance
#                    - Signature dishes (3-5 must-try items)
#                    - Price range per person
#                    - Reservation requirements
#                    - Dress code if any
#                    - Why it's recommended
#                    - Alternative options nearby
                
#                 6. Organize by day considering:
#                    - Geographic clustering (minimize backtracking)
#                    - Logical flow (museums before lunch, evening activities, etc.)
#                    - User's activity level (don't overbook)
#                    - Mix of indoor/outdoor activities
#                    - Balance of touristy and local experiences
#                    - Weather considerations
#                    - Opening hours of attractions
                
#                 7. Include for each day:
#                    - Morning activity (9 AM - 12 PM)
#                    - Lunch recommendation with details
#                    - Afternoon activity (2 PM - 6 PM)
#                    - Dinner recommendation with details
#                    - Evening activity or entertainment
#                    - Coffee/snack spots for breaks
#                    - Total estimated cost for the day
#                    - Walking distance/transport needs
                
#                 Be THOROUGH and DETAILED. Provide at least 2-3 options for each meal.
#                 Include backup activities in case of weather or closures.
                
#                 {self.__tip_section()}
#             """),
#             expected_output=dedent("""
#                 COMPREHENSIVE attraction and restaurant guide organized by day:
#                 {{
#                     "daily_itinerary": [
#                         {{
#                             "day": number,
#                             "date": "string",
#                             "theme": "string (e.g., 'Historic Sites & Culture')",
#                             "morning_activity": {{
#                                 "name": "string",
#                                 "description": "detailed 2-3 sentence description",
#                                 "address": "full address",
#                                 "how_to_get_there": "specific transport instructions",
#                                 "duration": "X hours",
#                                 "estimated_cost": "$XX",
#                                 "opening_hours": "string",
#                                 "best_time": "string",
#                                 "highlights": ["top things to see", "..."],
#                                 "insider_tips": ["tip 1", "tip 2", "..."],
#                                 "what_to_bring": ["items needed"],
#                                 "photo_spots": ["location 1", "location 2"]
#                             }},
#                             "lunch": {{
#                                 "restaurant_name": "string",
#                                 "cuisine": "string",
#                                 "address": "string",
#                                 "description": "detailed description of ambiance and food",
#                                 "signature_dishes": ["dish 1 ($XX)", "dish 2 ($XX)", "dish 3 ($XX)"],
#                                 "price_range": "$XX-XX per person",
#                                 "reservation": "yes/no and how",
#                                 "why_recommended": "string",
#                                 "alternatives": ["option 1", "option 2"]
#                             }},
#                             "afternoon_activity": {{...same detail as morning}},
#                             "dinner": {{...same detail as lunch}},
#                             "evening_activity": {{...same detail as morning}},
#                             "day_summary": {{
#                                 "total_cost": "$XXX",
#                                 "total_walking": "X km/miles",
#                                 "energy_level": "high/medium/low",
#                                 "tips": ["specific tips for this day"]
#                             }},
#                             "backup_options": ["alternative activities if needed"]
#                         }}
#                     ],
#                     "additional_restaurants": [
#                         {{detailed info for 10+ more restaurants}}
#                     ],
#                     "free_activities": [
#                         {{list of free things to do}}
#                     ],
#                     "hidden_gems": [
#                         {{off-beaten-path recommendations}}
#                     ],
#                     "total_estimated_cost": number,
#                     "within_budget": boolean,
#                     "general_tips": ["extensive list of area-specific tips"]
#                 }}
                
#                 Provide EXTENSIVE detail - imagine you're writing a guidebook chapter!
#             """),
#             agent=agent,
#             context=[]  # Will receive context from extraction_task
#         )
    
#     def coordination_task(self, agent, conversation_id: str):
#         """
#         Task for Itinerary Coordinator to create detailed day-by-day itinerary
#         """
#         return Task(
#             description=dedent(f"""
#                 Create a comprehensive travel itinerary using ONLY the real data provided by other agents.
                
#                 Conversation ID: {conversation_id}
                
#                 YOU WILL RECEIVE:
#                 - User preferences (dates, budget, interests, trip duration)
#                 - Flight options from Flight Agent (real API data)
#                 - Hotel options from Hotel Agent (real API data)  
#                 - Attractions and restaurants from Attraction Agent (real search data)
                
#                 YOUR TASK - Create a detailed itinerary with these sections:
                
#                 **Your Mission:**
#                 You are receiving COMPLETE OPTIONS from all search agents:
#                 - Flight Agent: 10-15 flight options with full details
#                 - Hotel Agent: 10-15 hotel options with full details
#                 - Attraction Agent: Daily activity suggestions
                
#                 Your job is to:
#                 1. **Present ALL options to the user in an organized way and as detail as possible**
#                 2. **Help them understand the tradeoffs between options**
#                 3. **Make intelligent recommendations based on their preferences**
#                 4. **Create the final detailed itinerary with their chosen options**
#                 5. **VERIFY ALL BUDGET ALLOCATIONS - Use calculator to ensure total stays within budget**
                
#                 **CRITICAL BUDGET VERIFICATION:**
#                 Each agent has already filtered by their budget allocation, but YOU must:
#                 - Calculate the TOTAL cost of recommended options
#                 - Verify: flights + hotel + activities + meals ≤ total_budget
#                 - If over budget, adjust recommendations or suggest savings
#                 - Show clear budget breakdown and remaining/excess amounts
                
#                 **STEP 1: PRESENT FLIGHT OPTIONS**
                
#                 Organize and present ALL flight options received:
                
#                 ═══════════════════════════════════════════════════════════════
#                 ✈️ FLIGHT OPTIONS ANALYSIS
#                 ═══════════════════════════════════════════════════════════════
                
#                 **YOUR TOP 3 RECOMMENDED FLIGHTS:**
#                 (Based on user's preferences, explain WHY these 3)
                
#                 🥇 BEST OVERALL: [Airline + Price]
#                 ├─ Why recommended: [Detailed reasoning]
#                 ├─ Outbound: [Full details]
#                 ├─ Return: [Full details]
#                 ├─ Total: $XXX
#                 └─ Perfect if you: [User type]
                
#                 🥈 BEST VALUE: [Airline + Price]
#                 [Same detail level]
                
#                 🥉 CHEAPEST: [Airline + Price]
#                 [Same detail level]
                
#                 **OTHER OPTIONS TO CONSIDER:**
#                 (Present remaining 7-12 options in organized table)
                
#                 | Option | Airline | Price | Duration | Stops | Best For |
#                 |--------|---------|-------|----------|-------|----------|
#                 | 4      | ...     | $XXX  | Xh XXm   | 0     | ...      |
                
#                 **FLIGHT DECISION GUIDE:**
#                 - If you prioritize: [Price] → Choose Option X
#                 - If you prioritize: [Speed] → Choose Option Y
#                 - If you prioritize: [Comfort] → Choose Option Z
                
#                 ═══════════════════════════════════════════════════════════════
#                 🏨 HOTEL OPTIONS ANALYSIS
#                 ═══════════════════════════════════════════════════════════════
                
#                 **YOUR TOP 3 RECOMMENDED HOTELS:**
#                 (Based on user's preferences, explain WHY these 3)
                
#                 🥇 BEST OVERALL: [Hotel Name + Price]
#                 ├─ Why recommended: [Detailed reasoning]
#                 ├─ Location: [Full details + map description]
#                 ├─ Room: [Type and amenities]
#                 ├─ Price: $XXX/night ($XXX total)
#                 ├─ Rating: X.X/10 (XXX reviews)
#                 └─ Perfect if you: [User type]
                
#                 🥈 BEST VALUE: [Hotel Name + Price]
#                 [Same detail level]
                
#                 🥉 BEST LOCATION: [Hotel Name + Price]
#                 [Same detail level]
                
#                 **OTHER OPTIONS TO CONSIDER:**
#                 (Present remaining 7-12 options in organized table)
                
#                 | Option | Hotel | Neighborhood | Price/Night | Total | Rating | Distance |
#                 |--------|-------|--------------|-------------|-------|--------|----------|
#                 | 4      | ...   | ...          | $XXX        | $XXX  | 8.5/10 | ...      |
                
#                 **HOTEL DECISION GUIDE:**
#                 - If you prioritize: [Location] → Choose Hotel X
#                 - If you prioritize: [Budget] → Choose Hotel Y
#                 - If you prioritize: [Luxury] → Choose Hotel Z
                
#                 ═══════════════════════════════════════════════════════════════
#                 💡 MY EXPERT RECOMMENDATIONS
#                 ═══════════════════════════════════════════════════════════════
                
#                 Based on your preferences for [describe their preferences], here's 
#                 what I recommend and why:
                
#                 **RECOMMENDED FLIGHT:** Option X - [Airline]
#                 - Reasoning: [2-3 paragraphs explaining why this is perfect for them]
#                 - Cost: $XXX (leaves $XXX from flight budget)
                
#                 **RECOMMENDED HOTEL:** Option Y - [Hotel Name]
#                 - Reasoning: [2-3 paragraphs explaining why this is perfect for them]
#                 - Cost: $XXX/night × X nights = $XXX (leaves $XXX from hotel budget)
                
#                 **TOTAL SO FAR:** $XXX
#                 **REMAINING BUDGET:** $XXX for activities and meals
                
#                 **ALTERNATIVE COMBINATIONS TO CONSIDER:**
#                 1. Flight X + Hotel Y = $XXX (Most balanced)
#                 2. Flight Z + Hotel A = $XXX (Budget-friendly, saves $XXX)
#                 3. Flight B + Hotel C = $XXX (Premium experience)
                
#                 ═══════════════════════════════════════════════════════════════
                
#                 **STEP 2: CREATE DETAILED ITINERARY**
                
#                 Now create an EXCEPTIONALLY DETAILED, comprehensive travel itinerary
#                 using YOUR RECOMMENDED flight and hotel (or explicitly state if using
#                 alternatives). This should be the most detailed itinerary possible - 
#                 every hour planned, every detail covered.
                
#                 **DETAILED ITINERARY STRUCTURE:**
                
#                 ═══════════════════════════════════════════════════════════════
#                 📋 EXECUTIVE SUMMARY
#                 ═══════════════════════════════════════════════════════════════
#                 - Destination overview with key highlights
#                 - Trip duration and dates
#                 - Total cost breakdown with detailed line items
#                 - Budget status (within/over budget with explanations)
#                 - Weather expectations and what to pack
#                 - Cultural highlights and what makes this trip special
                
#                 ═══════════════════════════════════════════════════════════════
#                 ✈️ FLIGHT DETAILS
#                 ═══════════════════════════════════════════════════════════════
#                 **OUTBOUND FLIGHT:**
#                 - Airline, flight number, aircraft type
#                 - Departure: Airport, terminal, gate area, exact time
#                 - Arrival: Airport, terminal, exact time
#                 - Flight duration, time zone changes
#                 - Seat recommendations (window/aisle, quiet zones)
#                 - In-flight amenities (meals, entertainment, WiFi)
#                 - Baggage allowance details
#                 - Estimated price with breakdown
                
#                 **RETURN FLIGHT:** [same detail level]
                
#                 **Booking Tips:**
#                 - Best websites to book
#                 - Optimal booking time
#                 - Travel insurance recommendations
                
#                 ═══════════════════════════════════════════════════════════════
#                 🏨 ACCOMMODATION DETAILS
#                 ═══════════════════════════════════════════════════════════════
#                 **HOTEL: [Name]**
#                 - Full address with neighborhood description
#                 - Check-in/check-out times and procedures
#                 - Room type recommendations with reasons
#                 - Amenities list (pool, gym, spa, breakfast, WiFi, etc.)
#                 - Distance to major attractions with transport options
#                 - Nearby conveniences (grocery, pharmacy, ATM)
#                 - Hotel tips (best rooms, hidden gems, what to avoid)
#                 - Nightly rate and total cost
#                 - Booking website recommendations
#                 - Cancellation policy notes
                
#                 ═══════════════════════════════════════════════════════════════
#                 📅 DETAILED DAY-BY-DAY ITINERARY
#                 ═══════════════════════════════════════════════════════════════
                
#                 For EACH DAY, provide EXTENSIVE detail:
#                 if user has a trip of 7 days then you have provide schedule of each day individually and in very detailed way
#                 in the first day the user will be landing from the airport and then to the hotel so in the first day include that as well


                
#                 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                 🌅 DAY [number]: [Date] - [Theme/Focus of the day]
#                 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                
#                 **MORNING **
                
#                 🕐 - Wake Up & Hotel Breakfast
#                 - Where: Hotel restaurant / room service
#                 - What to order: Specific menu recommendations
#                 - Cost: $XX per person
#                 - Time needed: 45 minutes
#                 - Tip: [Insider tip about breakfast]
                
#                 🕐  - Prepare for the Day
#                 - What to bring: [Detailed packing list for the day]
#                 - Weather check: [Expected conditions]
#                 - Dress code: [What to wear and why]
                
#                 🕐 - Travel to [First Attraction]
#                 - Departure point: Hotel main entrance
#                 - Transport: [Specific method - taxi/metro/walk/bus]
#                 - Route: [Exact directions or metro lines]
#                 - Duration: XX minutes
#                 - Cost: $XX
#                 - Pro tip: [Local transport insight]
                
#                 🕐  - [MAIN MORNING ATTRACTION]
#                 - Activity: [Detailed description of what you'll do]
#                 - Location: [Full address and area description]
#                 - Why visit: [What makes this special/must-see]
#                 - Duration: 2-3 hours
#                 - Entry cost: $XX per person
#                 - Booking: [Online/at door/skip-the-line options]
#                 - What to see: [Top 5 highlights within attraction]
#                   1. [Specific sight with description]
#                   2. [Specific sight with description]
#                   3. [Specific sight with description]
#                   4. [Specific sight with description]
#                   5. [Specific sight with description]
#                 - Best time: Morning to avoid crowds
#                 - Photo spots: [3-4 specific Instagram-worthy locations]
#                 - Insider tips: 
#                   • [Specific tip about visiting]
#                   • [What to skip/avoid]
#                   • [Hidden gems within]
#                 - Accessibility: [Wheelchair access, elevators, etc.]
#                 - Facilities: [Restrooms, gift shop, cafe locations]
                
#                 **AFTERNOON (12:00 PM - 6:00 PM)**
                
#                 🕐  - Lunch at [Restaurant Name]
#                 - Cuisine: [Type of cuisine]
#                 - Location: [Full address, distance from morning spot]
#                 - How to get there: [Walk/transport with time]
#                 - Ambiance: [Description of atmosphere]
#                 - Must-try dishes:
#                   1. [Dish name] - [Description and price]
#                   2. [Dish name] - [Description and price]
#                   3. [Dish name] - [Description and price]
#                 - Average cost per person: $XX-XX
#                 - Reservation: [Needed? How to book?]
#                 - Dietary options: [Vegetarian/vegan/gluten-free availability]
#                 - Local tip: [Something only locals know]
                
#                 🕐 - [AFTERNOON ACTIVITY]
#                 - Activity: [Detailed description]
#                 - Location: [Full address]
#                 - Duration: 2 hours
#                 - Cost: $XX
#                 - What you'll do: [Step-by-step of the experience]
#                 - What's included: [Detailed inclusions]
#                 - What to bring: [Specific items needed]
#                 - Best practices: [How to make the most of it]
#                 - Alternative options: [If this doesn't interest you]
                
#                 🕐  - Coffee/Snack Break
#                 - Café: [Specific café name]
#                 - Specialties: [What they're known for]
#                 - Cost: $XX
#                 - Why here: [What makes it special]
#                 - Time to relax: 30-45 minutes
                
#                 **EVENING (6:00 PM - 11:00 PM)**
                
#                 🕐  - Return to Hotel & Refresh
#                 - Travel time: [Duration and method]
#                 - Freshen up time: 1 hour
#                 - Evening outfit: [Dress code for dinner/evening]
                
#                 🕐  - Dinner at [Restaurant Name]
#                 - Cuisine: [Detailed description]
#                 - Location: [Full address with neighborhood vibe]
#                 - Reservation: [Time and how to book]
#                 - Price range: $XX-XX per person
#                 - Signature dishes: [3-4 must-orders with descriptions]
#                 - Wine/drink pairings: [Recommendations]
#                 - Duration: 1.5-2 hours
#                 - Dress code: [Specific requirements]
#                 - Why this restaurant: [What makes it special]
                
#                 🕐  - [EVENING ACTIVITY/ATTRACTION]
#                 - Activity: [Night activity, show, walk, etc.]
#                 - Location: [Where]
#                 - Duration: 1-2 hours
#                 - Cost: $XX
#                 - What to expect: [Detailed description]
#                 - Safety: [Evening safety tips for the area]
#                 - Alternative: [If you prefer to rest]
                
#                 🕐 11:00 PM - Return to Hotel
#                 - Transport: [Method and why]
#                 - Cost: $XX
#                 - Safety tip: [Evening travel advice]

#                 the above below is an example so you would have to adjust it according to information given to you 
#                 sometimes user may want to hang out late out at night so keep it mind as well
                
#                 **DAY  SUMMARY:**
#                 - Total walking distance: ~X km/miles
#                 - Estimated daily cost: $XXX (breakdown: transport $XX, food $XX, attractions $XX)
#                 - Energy level: [High/Medium/Low activity day]
#                 - Must-bring items: [List]
#                 - Weather prep: [What to expect and prepare for]
#                 - Local etiquette: [Important cultural notes for the day]
                
#                 ⚠️⚠️⚠️ CRITICAL: REPEAT THIS LEVEL OF DETAIL FOR EVERY SINGLE DAY ⚠️⚠️⚠️
                
#                 If the trip is 7 days, you MUST create Day 1, Day 2, Day 3, Day 4, Day 5, Day 6, Day 7
#                 If the trip is 5 days, you MUST create Day 1, Day 2, Day 3, Day 4, Day 5
#                 If the trip is 3 days, you MUST create Day 1, Day 2, Day 3
                
#                 DO NOT STOP AT DAY 1. DO NOT USE "[REPEAT FOR OTHER DAYS]" - ACTUALLY WRITE EACH DAY OUT.
#                 SHOWING ONLY ONE DAY IS COMPLETELY UNACCEPTABLE AND USELESS TO THE USER.
                
#                 You MUST plan EVERY SINGLE DAY with full morning, lunch, afternoon, dinner, evening details.
                
#                 ═══════════════════════════════════════════════════════════════
#                 💰 COMPREHENSIVE BUDGET BREAKDOWN
#                 ═══════════════════════════════════════════════════════════════
                
#                 **FLIGHTS:**
#                 - Outbound flight: $XXX
#                 - Return flight: $XXX
#                 - Baggage fees: $XX
#                 - Seat selection: $XX
#                 - Travel insurance: $XX
#                 **SUBTOTAL: $XXXX**
                
#                 **ACCOMMODATION:**
#                 - Hotel (X nights @ $XX/night): $XXX
#                 - Resort fees/taxes: $XX
#                 - Tips for housekeeping: $XX
#                 **SUBTOTAL: $XXXX**
                
#                 **DAILY ACTIVITIES & ATTRACTIONS:**
#                 Day 1: $XXX (itemized list)
#                 Day 2: $XXX (itemized list)
#                 [etc. for each day]
#                 **SUBTOTAL: $XXXX**
                
#                 **MEALS:**
#                 - Breakfasts (X days @ $XX): $XXX
#                 - Lunches (X days @ $XX): $XXX
#                 - Dinners (X days @ $XX): $XXX
#                 - Snacks/coffee: $XXX
#                 **SUBTOTAL: $XXXX**
                
#                 **TRANSPORTATION:**
#                 - Airport transfers: $XXX
#                 - Daily transport passes: $XXX
#                 - Taxis/rideshares: $XXX
#                 **SUBTOTAL: $XXX**
                
#                 **MISCELLANEOUS:**
#                 - Shopping budget: $XXX
#                 - Emergency fund: $XXX
#                 - Tips/gratuities: $XXX
#                 - Phone/data: $XX
#                 **SUBTOTAL: $XXX**
                
#                 ═══════════════════════════════════════════════════════════════
#                 **GRAND TOTAL: $XXXX**
#                 **Original Budget: $XXXX**
#                 **Status: [Within budget by $XX / Over budget by $XX]**
#                 ═══════════════════════════════════════════════════════════════
                
#                 ═══════════════════════════════════════════════════════════════
#                 💡 COMPREHENSIVE TRAVEL TIPS & ADVICE
#                 ═══════════════════════════════════════════════════════════════
                
#                 **BEFORE YOU GO:**
#                 - Book flights by: [Date]
#                 - Book hotels by: [Date]
#                 - Travel insurance: [Recommendations]
#                 - Visa requirements: [Details]
#                 - Vaccinations: [If any needed]
#                 - Currency exchange: [Best methods and rates]
#                 - Credit card prep: [Notify banks, fees, best cards]
                
#                 **PACKING ESSENTIALS:**
#                 - Clothing: [Specific items for weather/activities]
#                 - Electronics: [Adapters, chargers, voltage]
#                 - Documents: [Checklist of what to bring]
#                 - Medications: [Travel health kit]
#                 - Apps to download: [Useful apps with descriptions]
                
#                 **LOCAL KNOWLEDGE:**
#                 - Language basics: [Key phrases]
#                 - Cultural do's and don'ts: [Important etiquette]
#                 - Safety tips: [Area-specific advice]
#                 - Scams to avoid: [Common tourist traps]
#                 - Tipping customs: [When and how much]
#                 - Emergency contacts: [Police, ambulance, embassy]
                
#                 **TRANSPORTATION:**
#                 - Airport to hotel: [All options with pros/cons]
#                 - Getting around: [Metro/bus/taxi/walking guide]
#                 - Transport passes: [Which to buy and where]
#                 - Car rental: [If needed, where and how]
                
#                 **FOOD & DINING:**
#                 - Must-try local dishes: [List with descriptions]
#                 - Food safety tips: [What to watch for]
#                 - Dietary restrictions: [How to communicate]
#                 - Where locals eat: [Neighborhood recommendations]
#                 - Markets/food halls: [Best ones to visit]
                
#                 **MONEY SAVING TIPS:**
#                 - [10-15 specific ways to save money]
#                 - Free activities: [Detailed list]
#                 - Happy hours: [Where and when]
#                 - Discount cards: [City passes worth it?]
                
#                 **ALTERNATIVE ACTIVITIES:**
#                 (If you have extra time or want to swap something)
#                 - [10-15 backup activities with full details]
                
#                 ═══════════════════════════════════════════════════════════════
                
#                 This itinerary should be SO DETAILED that the traveler can print it 
#                 and follow it hour-by-hour without any additional research needed!
                
#                 {self.__tip_section()}
#             """),
#             expected_output=dedent("""
#                 An EXTREMELY DETAILED, comprehensive travel itinerary with:
                
#                 ✅ Executive summary with complete destination overview
#                 ✅ Detailed flight information with all booking details from Flight Agent
#                 ✅ Complete hotel information with insider tips from Hotel Agent (MUST INCLUDE HOTEL DATA)
#                 ✅ ⚠️ MANDATORY: Hour-by-hour itinerary for EVERY SINGLE DAY OF THE TRIP ⚠️
#                    - If 7-day trip: Must have DAY 1, DAY 2, DAY 3, DAY 4, DAY 5, DAY 6, DAY 7 all fully detailed
#                                    each day should contain a detailed schedule
#                    - If 5-day trip: Must have DAY 1, DAY 2, DAY 3, DAY 4, DAY 5 all fully detailed
#                    - If 3-day trip: Must have DAY 1, DAY 2, DAY 3 all fully detailed
#                    - Each day must include:
#                      * Exact times for every activity
#                      * Detailed descriptions of each attraction
#                      * Specific restaurant recommendations with menu items
#                      * Transport details between locations
#                      * Costs for everything
#                      * Insider tips and local knowledge
#                      * Photo opportunities
#                      * What to bring/wear for each part of day
#                 ✅ Itemized budget breakdown for everything
#                 ✅ Comprehensive pre-trip preparation guide
#                 ✅ Extensive local knowledge and tips
#                 ✅ Emergency information and contacts
#                 ✅ Alternative activities and backup plans
                
#                 ⚠️ VALIDATION CHECKLIST - YOUR OUTPUT MUST HAVE:
#                 - [ ] ALL flight options from Flight Agent (not "missing data")
#                 - [ ] ALL hotel options from Hotel Agent (not "missing data" or "not available")
#                 - [ ] COMPLETE itinerary for EVERY day (not just Day 1)
#                 - [ ] Each day has morning, lunch, afternoon, dinner, evening fully detailed
#                 - [ ] Budget breakdown with actual numbers from agents
                
#                 IF ANY OF THESE ARE MISSING, THE OUTPUT IS INCOMPLETE AND UNACCEPTABLE.
                
#                 FORMAT: Use emojis, clear sections, and beautiful formatting.
#                 LENGTH: This should be a LONG, detailed document (3000+ words minimum).
#                 GOAL: The traveler should need NO additional research - everything is here!
#             """),
#             agent=agent,
#             context=[]  # Will receive context from flight, hotel, and attraction tasks
#         )
    
# To know more about the Task class, visit: https://docs.crewai.com/concepts/tasks
from crewai import Task
from textwrap import dedent
from typing import Dict, Any
from pydantic import BaseModel, Field
from typing import List, Optional


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
                Comprehensive flight search results with 10-15 real options:
                
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
                
                Return AT LEAST 10 complete flight options with REAL API data!
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
                   - Get AT LEAST 15 hotels with prices
                   - If this fails, STOP and report error
                
                STEP 3: ✅ Calculate budget limit
                   - Use calculator: hotel_budget ÷ nights = max_per_night
                   - Filter: keep only hotels where price ≤ max_per_night
                
                STEP 4: ✅ Use "Get hotel reviews" tool
                   - For EACH hotel (at least top 15), get reviews
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
                - [ ] At least 15 hotels from Step 2
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
                📋 ALL HOTEL OPTIONS (15+ hotels sorted by review score)
                ═══════════════════════════════════════════════════════════
                
                Provide JSON structure with complete hotel data as specified.
                
                Return AT LEAST 15 complete hotel options with REAL API data!
                
                ═══════════════════════════════════════════════════════════
                ⚠️ VALIDATION REQUIREMENTS - YOUR OUTPUT MUST INCLUDE:
                ═══════════════════════════════════════════════════════════
                ✅ At least 10-15 hotels with complete information
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
                2. Flight Task: 10-15 flight options with complete details
                3. Hotel Task: 10-15 hotel options with reviews and locations
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
                
                **OTHER OPTIONS:** (Table with remaining 7-12 flights)
                
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
