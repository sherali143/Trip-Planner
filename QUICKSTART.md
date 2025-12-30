# 🚀 QUICK START GUIDE

## Get Your Trip Planner Running in 5 Minutes!

### Step 1: Install Dependencies ⚙️
```powershell
cd c:\Users\SHEHROZALI\Desktop\trip_planner\trip_planner
pip install crewai[tools] langchain langchain-openai python-dotenv requests pydantic pyyaml
```

### Step 2: Set Up Environment Variables 🔑
Create a `.env` file in the `trip_planner` directory:
```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=sk-your-openai-key-here
SERPER_API_KEY=your-serper-key-here
```

### Step 3: Run the Trip Planner 🌍
```powershell
python main.py
```

### Step 4: Enter Your Trip Request ✈️
When prompted, enter something like:
```
I want to visit Paris for 5 days with a $3000 budget. 
I'm interested in art, museums, French cuisine, and the Eiffel Tower.
```

## 🎯 What Happens Next?

The system will:
1. **Ask clarifying questions** (conversational agent)
2. **Extract structured data** (preferences extractor via A2A)
3. **Search using MCP-style tools** (SearchTools with web search)
   - Flights via web search
   - Hotels via web search  
   - Attractions via web search
   - Restaurants via web search
4. **Create your itinerary** (coordinator synthesizes everything)
5. **Display complete plan** with budget breakdown!

## 📊 You'll See:

```
════════════════════════════════════════════════════════════════════════
🌍 TRIP PLANNER STARTED
════════════════════════════════════════════════════════════════════════
Conversation ID: abc-123-def
User Input: I want to visit Paris...
════════════════════════════════════════════════════════════════════════

🤖 PHASE 1: Conversational Agent engaging with user...
🔍 PHASE 2: Extracting structured preferences...
✈️  PHASE 3: Flight Search Agent using MCP-style search tools...
🏨 PHASE 4: Hotel Agent using MCP-style search tools...
🎭 PHASE 5: Attraction Agent using MCP-style search tools...
📋 PHASE 6: Itinerary Coordinator synthesizing all data...

════════════════════════════════════════════════════════════════════════
✅ TRIP PLANNING COMPLETED
════════════════════════════════════════════════════════════════════════
```

## 🔍 Troubleshooting

### Issue: Import errors
```powershell
pip install --upgrade crewai langchain langchain-openai
```

### Issue: Missing API keys
Make sure `.env` file exists and has valid keys:
```powershell
cat .env
```

### Issue: Want to use real MCP servers
The system currently uses SearchTools with web search (Serper API) which provides real data.
To integrate dedicated MCP servers, edit `agents.py` and use CrewAI's native MCP syntax:
```python
agent = Agent(
    role="Flight Search",
    mcps=["https://your-mcp-server.com/flights"]
)

## 💡 Pro Tips

1. **Test with mock data first** - Already configured!
2. **Check config.yaml** to customize agent behavior
3. **View A2A messages** - Set `verbose: true` in config
4. **Add more agents** - Follow the pattern in `agents.py`

## 📚 Next Steps

- Read `README.md` for detailed documentation
- Check `IMPLEMENTATION_SUMMARY.md` for architecture details
- Explore `agent_cards.py` to understand A2A protocol
- Modify `config.yaml` to tune agent behavior

## 🎉 That's It!

You now have a fully functional AI trip planner with:
- ✅ A2A Protocol (agent cards, messages, executor)
- ✅ MCP-style interface (SearchTools with web search)
- ✅ Multi-agent workflow (6 specialized agents)
- ✅ Real-time search (flights, hotels, attractions, restaurants)
- ✅ Budget optimization
- ✅ Complete itinerary generation

**Enjoy planning amazing trips!** 🌍✈️🏨
