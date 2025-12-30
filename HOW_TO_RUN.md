# 🚀 HOW TO RUN THE TRIP PLANNER

## ⚡ Super Quick Start (For Poetry Users)

```powershell
# Navigate to the trip_planner folder
cd trip_planner

# Install dependencies
poetry install

# Create .env file with your API keys
notepad .env

# Run the trip planner
poetry run python main.py
```

That's it! 🎉

---

## Quick Start (5 Steps)

### Step 1: Install Dependencies with Poetry

Since your project uses `pyproject.toml`, you're using Poetry. Open PowerShell in the `trip_planner` folder and run:

```powershell
# Install Poetry if you don't have it
pip install poetry

# Install all dependencies from pyproject.toml
poetry install
```

This will install all dependencies listed in your `pyproject.toml` file including:
- crewai (with tools)
- mcp
- langchain and langchain-openai
- python-dotenv
- requests
- pydantic
- pyyaml

### Step 2: Set Up Your API Keys

Create a file named `.env` in the `trip_planner` folder:

```powershell
# Create .env file
Copy-Item .env.example .env

# Or create manually
notepad .env
```

Add your API keys to `.env`:

```env
OPENAI_API_KEY=your_openai_key_here
RAPIDAPI_KEY=your_rapidapi_key_here
SERPER_API_KEY=your_serper_key_here
```

**Where to get API keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **RapidAPI**: https://rapidapi.com/ (Subscribe to Kiwi.com and Booking.com APIs)
- **Serper**: https://serper.dev/ (Free tier available)

### Step 3: Test MCP Servers (Optional but Recommended)

```powershell
# With Poetry
poetry run python test_mcp_servers.py
```

You should see:
```
✅ Environment: PASSED
✅ Flight MCP: PASSED
✅ Hotel MCP: PASSED
✅ Car Rental MCP: PASSED
```

### Step 4: Run the Trip Planner

```powershell
# With Poetry
poetry run python main.py
```

### Step 5: Enter Your Trip Details

When prompted, enter your trip request:

```
Your trip request: I want to visit Paris for 5 days with a $3000 budget. 
I love art, food, and romantic walks.
```

The agent will ask you follow-up questions. Answer them naturally!

## Example Session

```
╔══════════════════════════════════════════════════════════════════════╗
║              🌍 AI TRIP PLANNER WITH A2A & MCP 🌍                   ║
╚══════════════════════════════════════════════════════════════════════╝

📝 Please describe your ideal trip:

Your trip request: I want to visit Tokyo for 7 days with a $4000 budget

💬 INTERACTIVE CONVERSATION WITH TRAVEL ASSISTANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Agent: That sounds exciting! Tokyo is an amazing destination. 
Let me ask a few questions to plan the perfect trip for you.

First, where are you traveling from? And do you have specific 
dates in mind, or are you flexible?

👤 You: I'm traveling from New York. I'm flexible on dates but 
prefer sometime in April.

🤖 Agent: Perfect! April is cherry blossom season in Tokyo - beautiful 
timing! What interests you most? Japanese culture, food, shopping, 
technology, temples, nightlife, or something else?

👤 You: I love Japanese culture, authentic food, temples, and I'd 
really like to see Mt. Fuji if possible.

🤖 Agent: Wonderful choices! What's your travel style - are you looking 
for luxury accommodations, budget-friendly, or moderate comfort?

👤 You: Moderate is perfect - comfortable but not too expensive.

🤖 Agent: Great! Any dietary restrictions or special requirements I 
should know about?

👤 You: None, I'm open to trying everything!

🤖 Agent: Perfect! I have everything I need. CONVERSATION_COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ Processing your trip plan...

[Agent execution begins...]

✅ All agents initialized
✅ A2A Protocol active
🔍 Flight Agent: Searching 10-15 flight options...
🔍 Hotel Agent: Searching 10-15 hotel options...
🔍 Attraction Agent: Researching activities...
✍️ Coordinator: Creating detailed itinerary...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 YOUR COMPLETE TRAVEL ITINERARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Your detailed 3000+ word itinerary appears here...]

✨ Happy Travels! ✨
```

## What You'll Get

Your output will include:

1. **✈️ Flight Options Analysis** (10-15 options)
   - Top 3 recommended flights with detailed reasoning
   - Full comparison table
   - Decision guide

2. **🏨 Hotel Options Analysis** (10-15 options)
   - Top 3 recommended hotels with detailed reasoning
   - Full comparison table
   - Neighborhood descriptions

3. **💡 Expert Recommendations**
   - Recommended flight + why
   - Recommended hotel + why
   - Budget breakdown
   - Alternative combinations

4. **📅 Extremely Detailed Itinerary**
   - Hour-by-hour schedule for every day
   - Specific restaurant recommendations with menu items
   - Transport details between locations
   - Insider tips and local knowledge
   - Photo opportunities
   - What to wear/bring
   - Complete cost breakdowns
   - 3000-5000+ words

## Troubleshooting

### Issue: "Module not found" error

**Solution:**
```powershell
# Reinstall dependencies with Poetry
poetry install

# Or update all packages
poetry update
```

### Issue: "API key not found" error

**Solution:** Make sure your `.env` file is in the same folder as `main.py` and contains valid API keys.

### Issue: MCP servers not working

**Solution:**
```powershell
# Check your RAPIDAPI_KEY is correct
poetry run python test_mcp_servers.py

# Make sure you subscribed to the APIs on RapidAPI
```

### Issue: Takes too long / times out

**Solution:** 
- This is normal! The system makes many API calls and uses GPT-4
- First run can take 5-10 minutes
- Be patient, it's gathering 30+ options and creating a detailed plan

### Issue: Output is too short

**Solution:** 
- Make sure you're using GPT-4 (not GPT-3.5)
- Check your OpenAI API key has access to GPT-4
- The system is designed for detailed output - if it's short, there may be an error

## Tips for Best Results

1. **Be specific in your initial request**: Include destination, duration, budget, interests

2. **Answer questions naturally**: The conversational agent works best with natural language

3. **Provide your budget clearly**: This helps find options within your range

4. **Mention your interests**: Culture, food, adventure, relaxation, etc.

5. **Be patient**: The system queries multiple APIs and creates a comprehensive plan

## File Structure

```
trip_planner/
├── main.py                    ← RUN THIS FILE
├── agents.py                  (Agent definitions)
├── tasks.py                   (Task definitions)
├── tools/
│   ├── searchtool.py         (Search tools)
│   └── calculatortool.py     (Calculator)
├── mcp_servers/
│   ├── flight_mcp_server.py  (Flight API integration)
│   └── hotel_mcp_server.py   (Hotel API integration)
├── .env                       ← CREATE THIS (your API keys)
├── .env.example              (Example template)
└── test_mcp_servers.py       (Test script)
```

## Environment Variables Explained

```env
# Required for AI agents (GPT-4)
OPENAI_API_KEY=sk-...

# Required for flight/hotel search via MCP
RAPIDAPI_KEY=...

# Required for web search (attractions, restaurants)
SERPER_API_KEY=...
```

## Advanced: Run with Specific Example

If you want to skip the conversation and use a pre-defined trip:

Edit `main.py` around line 284 and change the example, or just press Enter when prompted to use the default example.

## Need Help?

- Check `README.md` for full documentation
- Check `MCP_SETUP.md` for MCP server details
- Check `IMPROVED_WORKFLOW.md` for how the system works
- Run `python test_mcp_servers.py` to diagnose issues

## Summary

**To run with Poetry:**
```powershell
# 1. Install Poetry (if needed)
pip install poetry

# 2. Install all dependencies from pyproject.toml
poetry install

# 3. Create .env with your API keys
notepad .env

# 4. Test (optional)
poetry run python test_mcp_servers.py

# 5. Run!
poetry run python main.py
```

**Or activate Poetry shell first:**
```powershell
# Enter Poetry environment
poetry shell

# Then run without "poetry run" prefix
python test_mcp_servers.py
python main.py
```

Enjoy your detailed trip planning! 🌍✈️🏨
