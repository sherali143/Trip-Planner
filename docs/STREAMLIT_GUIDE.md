# Running the Streamlit UI

## Installation

1. Install streamlit:
```bash
poetry add streamlit
# or
pip install streamlit
```

## Running the App

### Option 1: Using Streamlit (Recommended)
```bash
streamlit run app.py
```

This will:
- Open a browser window automatically at http://localhost:8501
- Show the interactive UI where you can:
  - Answer questions one by one
  - See your progress
  - View the generated itinerary
  - Download your itinerary as a text file

### Option 2: Using Terminal (Original)
```bash
python main.py
```

This will run the original terminal-based interactive conversation.

## Features of the Streamlit UI

✨ **Interactive Question Flow**
- Questions are asked one at a time
- Clear progress tracking
- Easy-to-use form interface

📊 **Visual Progress**
- Progress bar showing completion
- Checklist of answered questions
- Conversation history display

📄 **Itinerary Display**
- Beautiful formatted output
- Download as text file
- Easy to read and share

🔄 **Start Over**
- Reset button to start a new trip plan
- Clean slate for planning multiple trips

## UI Layout

The interface has two columns:

**Left Column**: Conversation Area
- Shows the conversation history
- Displays current question
- Input field for your answer

**Right Column**: Itinerary Display
- Shows the generated itinerary once complete
- Provides download button
- Displays helpful tips while planning

**Sidebar**: Progress Tracker
- Shows which questions have been answered
- Progress bar
- Start over button

## Tips

1. **Be specific** with your answers (e.g., "Paris, France" instead of just "Paris")
2. **Include dates** in proper format (e.g., "December 15, 2025")
3. **Budget** should be a number with currency (e.g., "$3000")
4. **Interests** can be multiple items separated by commas
5. The planning process takes a few minutes - be patient!

## Troubleshooting

If the app doesn't start:
```bash
# Make sure streamlit is installed
pip list | grep streamlit

# If not installed
pip install streamlit

# Then run again
streamlit run app.py
```

If you get API errors:
- Check that your `.env` file has all required API keys
- Ensure OPENAI_API_KEY, SERPER_API_KEY, and RAPIDAPI_KEY are set
