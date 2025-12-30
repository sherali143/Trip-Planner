# Quick Start Guide - Enhanced Detailed Itinerary System

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies
```bash
pip install mcp requests python-dotenv crewai langchain langchain-openai pydantic pyyaml
```

### Step 2: Set Up API Keys

Create a `.env` file:
```bash
# Required APIs
OPENAI_API_KEY=your_openai_key_here
RAPIDAPI_KEY=your_rapidapi_key_here
SERPER_API_KEY=your_serper_key_here
```

**Get Your Keys:**
1. **OpenAI**: https://platform.openai.com/api-keys
2. **RapidAPI**: https://rapidapi.com/ → Subscribe to:
   - Kiwi.com Cheap Flights
   - Booking.com API
3. **Serper**: https://serper.dev/ (free tier available)

### Step 3: Test MCP Servers
```bash
python test_mcp_servers.py
```

Expected output:
```
✅ Environment: PASSED
✅ Flight MCP: PASSED
✅ Hotel MCP: PASSED
✅ Car Rental MCP: PASSED
```

### Step 4: Run Trip Planner
```bash
python main.py
```

### Step 5: Enter Your Trip Request

Example input:
```
I want to visit Paris for 5 days in June with a $3000 budget. 
I love art museums, French cuisine, romantic walks, and seeing iconic landmarks. 
I prefer moderate accommodations and enjoy both tourist spots and local experiences.
```

## 📋 What You'll Get

### Before Enhancement:
```
Simple itinerary (300-500 words):
- Day 1: Visit Eiffel Tower, lunch nearby, evening walk
- Day 2: Louvre Museum, dinner at restaurant
- Day 3: ...
```

### After Enhancement:
```
COMPREHENSIVE DETAILED ITINERARY (3000-5000 words):

═══════════════════════════════════════════════════════════════
📋 EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════════
Paris, France - 5 Days of Art, Culture & Romance
June 15-19, 2025
Total Budget: $3,000 (Within budget by $127!)
...

═══════════════════════════════════════════════════════════════
✈️ FLIGHT DETAILS
═══════════════════════════════════════════════════════════════
OUTBOUND FLIGHT:
- Airline: Air France AF123
- Aircraft: Boeing 777-300ER
- Departure: JFK Terminal 1, Gate B23, 7:30 PM
- Arrival: CDG Terminal 2E, 8:45 AM +1
- Duration: 7h 15m (crossing 6 time zones)
- Seat Recommendations: 
  • Window: 18A, 19A (good wing views)
  • Aisle: 15C, 16C (quick exit)
  • Avoid: Rows 30-35 (near lavatories)
- In-flight: Complimentary meals, entertainment, WiFi ($20)
- Baggage: 1 checked (50lbs), 1 carry-on
- Price: $687 including taxes
...

═══════════════════════════════════════════════════════════════
🏨 ACCOMMODATION DETAILS
═══════════════════════════════════════════════════════════════
HOTEL: Hôtel Louvre Marsollier Opera
- Address: 13 Rue Marsollier, 2nd Arr., 75002 Paris
- Neighborhood: Opera/Louvre - Perfect location!
  Walking distance to Louvre (8 min), Opera (5 min)
- Check-in: June 15, 3:00 PM
- Check-out: June 19, 11:00 AM
- Room Type: Superior Double Room (recommended)
- Amenities:
  ✓ Free WiFi
  ✓ Air conditioning
  ✓ Daily housekeeping
  ✓ 24-hour front desk
  ✓ Elevator
  ✓ Safe in room
- Rate: $142/night × 4 nights = $568
- Hotel Tips:
  • Ask for upper floor room (quieter, better views)
  • Breakfast not included but café next door is better
  • Concierge speaks English and gives great recommendations
...

═══════════════════════════════════════════════════════════════
📅 DETAILED DAY-BY-DAY ITINERARY
═══════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌅 DAY 1: June 15 - Arrival & Latin Quarter Exploration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**MORNING (8:45 AM - 12:00 PM)**

🕐 8:45 AM - Arrival at Charles de Gaulle Airport (CDG)
- Terminal: 2E
- Immigration: EU citizens 15 min, others 30-45 min
- Baggage claim: Carousel 7 or 8
- Welcome to Paris! Currency: Euros (€1 = $1.09)

🕐 9:45 AM - Airport to Hotel Transfer
- Best option: RER B train to Châtelet, then Metro Line 7
- Cost: €11.40 per person
- Duration: 50 minutes
- Tickets: Buy at machine or counter (credit cards accepted)
- Route: 
  1. Follow "Paris by train" signs
  2. RER B towards "Robinson/Saint-Rémy"
  3. Exit at "Châtelet-Les Halles"
  4. Transfer to Metro Line 7 (pink line)
  5. Exit at "Pyramides"
  6. Walk 3 minutes to hotel
- Alternative: Taxi €55-70 (45 min) if tired
- What to have: Euros for tips, phone charged for maps

🕐 11:00 AM - Hotel Check-in & Refresh
- Drop bags even if room not ready
- Ask concierge for:
  • Metro map and carnet (10-ride ticket book, €16.90)
  • Restaurant recommendations
  • Museum pass info
- Freshen up: 30 minutes
- Change clothes to comfortable walking shoes

🕐 11:45 AM - Neighborhood Orientation Walk
- Walk around Opera district
- See: Palais Garnier (Opera House) exterior
- Distance: 0.5 km, 10 minutes
- Free activity!
- Photo op: Opera House facade

**AFTERNOON (12:00 PM - 6:00 PM)**

🕐 12:15 PM - Lunch at Café de la Paix
- Location: 5 Place de l'Opéra, 75009 (right at Opera)
- Cuisine: Classic French brasserie
- Ambiance: Historic café (opened 1862), beautiful interior
- Must-try dishes:
  1. French Onion Soup (€15) - Their specialty!
  2. Croque Monsieur (€18) - Classic grilled ham & cheese
  3. Salade Niçoise (€22) - Fresh and perfect for lunch
- Average cost: €25-35 per person including drink
- Reservation: Not needed for lunch
- Tip: 15% service included, leave €2-3 extra
- Why here: Historic location, people-watching, authentic
- Alternative if full: Bouillon Chartier (cheaper, 5 min walk)

🕐 2:00 PM - Walk to Latin Quarter
- Start: From Opera
- Route: Walk south via Rue de Rivoli (scenic)
- Distance: 2.2 km, 25 minutes
- Or Metro: Line 7 to Saint-Michel (5 min, €2.15)
- What to see en route: Seine River, Notre-Dame exterior

🕐 2:30 PM - LATIN QUARTER EXPLORATION
- Activity: Explore this historic, charming neighborhood
- Duration: 2.5 hours
- Cost: Free (just walking and exploring!)

**SPECIFIC HIGHLIGHTS:**

📍 Shakespeare and Company Bookstore
- Address: 37 Rue de la Bûcherie
- Why visit: Iconic English bookstore since 1951
- Duration: 30 minutes
- Don't miss: Upstairs reading room, resident cats
- Tip: Sign the guestbook!
- Photo spot: Outside with Notre-Dame behind

📍 Panthéon
- Address: Place du Panthéon
- Why visit: Stunning neoclassical monument, tomb of famous French
- Entry: €11.50 (or skip if budget-conscious)
- Duration: 45 minutes inside
- Highlights: 
  1. Foucault's Pendulum
  2. Tombs of Voltaire, Rousseau, Victor Hugo
  3. Dome view (if open)
- Best view: From outside, up the steps
- Photo spot: Steps looking down Rue Soufflot

📍 Jardin du Luxembourg
- Address: Rue de Vaugirard
- Why visit: Most beautiful park in Paris
- Duration: 45 minutes
- Free!
- What to do:
  • Relax by Medici Fountain
  • Watch toy boats in pond
  • See Luxembourg Palace exterior
  • Find the Statue of Liberty replica
- Insider tip: Get gelato from cart (€3-4)
- Photo spots: Fountain, Palace, tree-lined paths

🕐 5:00 PM - Coffee Break at Café de Flore
- Location: 172 Boulevard Saint-Germain
- Why here: Historic café, Hemingway wrote here
- Order: Café crème (€7) and croissant (€3.50)
- Duration: 30 minutes
- People-watching heaven!

**EVENING (6:00 PM - 11:00 PM)**

🕐 6:30 PM - Return to Hotel
- Walk or Metro back
- Freshen up: 1 hour
- Evening outfit: Smart casual (no shorts)

🕐 7:30 PM - Dinner at Le Comptoir du Relais
- Location: 9 Carrefour de l'Odéon, 6th arr.
- Cuisine: Modern French bistro
- Ambiance: Cozy, authentic, locals love it
- Reservation: ESSENTIAL - book now! +33 1 44 27 07 97
- Must-try dishes:
  1. Duck Terrine (€14) - House specialty
  2. Coq au Vin (€28) - Best in Paris
  3. Chocolate Fondant (€12) - To die for
- Wine pairing: Côtes du Rhône (€32 bottle)
- Average: €50-65 per person with wine
- Why recommended: Authentic French, reasonable prices, 
  Chef Yves Camdeborde is famous
- Dress code: Smart casual
- Tip: Service included, but leave €5-10
- Alternative: L'Avant Comptoir (same owner, no reservations,
  tapas-style, €30-40 pp)

🕐 9:30 PM - Evening Stroll along Seine
- Activity: Romantic walk by the river
- Route: From restaurant to Pont Neuf
- Duration: 45 minutes
- Free!
- What you'll see:
  • Notre-Dame illuminated
  • Seine River boats
  • Street performers
  • Lit bridges
- Photo spots: Pont Neuf, Pont des Arts
- Safety: Very safe, well-lit, many people
- Tip: Stop for wine at riverside kiosk (€5)

🕐 10:30 PM - Return to Hotel
- Walk or Metro (Line 7 from Pont Neuf)
- Stop: Pyramides
- Duration: 15 minutes
- Cost: €2.15 or use carnet ticket

🕐 11:00 PM - Rest Up!
- Tomorrow is museum day (you'll walk 10km!)

**DAY 1 COST SUMMARY:**
- Airport transfer: €11.40
- Metro carnet (10 tickets): €16.90
- Lunch: €32
- Panthéon: €11.50 (optional)
- Coffee: €10.50
- Dinner: €58
- Evening wine: €5
**TOTAL: €145.30**

**DAY 1 TIPS:**
✓ Arrive with some euros already
✓ Download Google Maps offline for Paris
✓ Buy carnet (10 metro tickets) - saves money
✓ Keep passport on you always
✓ Watch for pickpockets in tourist areas
✓ Pharmacies have green cross signs
✓ Emergency: 112 (works in all Europe)
✓ Your hotel is at a PERFECT location!

**TOMORROW PREVIEW:**
Day 2: Louvre Museum (arrive at opening!), Tuileries Gardens,
Sainte-Chapelle, Seine dinner cruise

[CONTINUE THIS LEVEL OF DETAIL FOR DAYS 2, 3, 4, 5...]

═══════════════════════════════════════════════════════════════
💰 COMPREHENSIVE BUDGET BREAKDOWN
═══════════════════════════════════════════════════════════════
...

═══════════════════════════════════════════════════════════════
💡 COMPREHENSIVE TRAVEL TIPS & ADVICE
═══════════════════════════════════════════════════════════════
...
```

## 🎯 Key Features

✅ **Hour-by-hour schedule** - Know exactly what to do every moment
✅ **Specific restaurants** - Not just "eat lunch", but WHERE with WHAT to order
✅ **Transport details** - Exact metro lines, walking times, costs
✅ **Insider tips** - What locals know, what to avoid
✅ **Photo spots** - Best Instagram locations
✅ **Alternatives** - Backup options for everything
✅ **Budget tracking** - Cost of every activity
✅ **What to wear** - Dress codes for each activity
✅ **What to bring** - Daily packing lists
✅ **Local knowledge** - Cultural tips, etiquette

## 🔧 Troubleshooting

### Issue: Itinerary still too short

**Solution:** Check your OpenAI model:
```python
# In agents.py, ensure you're using GPT-4
self.llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)
```

### Issue: MCP servers failing

**Solution:** Verify API keys:
```bash
python test_mcp_servers.py
```

### Issue: Rate limits hit

**Solution:** Add delays between requests or upgrade API plans

## 📞 Support

- Check `MCP_SETUP.md` for detailed MCP configuration
- Check `DETAILED_ITINERARY_UPDATE.md` for technical details
- Review `README.md` for full documentation

## 🎉 Enjoy Your Detailed Itineraries!

Your trip planner now creates professional-grade, extremely detailed itineraries that travelers will love!
