"""
Streamlit UI for AI Trip Planner
"""

import streamlit as st
from dotenv import load_dotenv
from src.orchestrator import TripPlannerCrew
import uuid

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Trip Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #E3F2FD;
        margin-left: 20%;
    }
    .agent-message {
        background-color: #F5F5F5;
        margin-right: 20%;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        border-radius: 0.5rem;
        padding: 0.75rem;
    }
    .info-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4CAF50;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'conversation_complete' not in st.session_state:
    st.session_state.conversation_complete = False
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None
if 'crew' not in st.session_state:
    st.session_state.crew = None
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}

# Questions to ask one by one
QUESTIONS = [
    ("destination", "🌍 Where would you like to go?", "e.g., Paris, France or Tokyo, Japan"),
    ("origin", "🏠 Where are you traveling from?", "e.g., New York, USA"),
    ("start_date", "📅 When do you want to start your trip?", "e.g., December 15, 2025"),
    ("end_date", "📅 When do you want to return?", "e.g., December 22, 2025"),
    ("budget", "💰 What is your total budget for this trip?", "e.g., $3000"),
    ("interests", "🎯 What interests you most?", "e.g., museums, food, nightlife, nature, adventure"),
    ("travel_style", "✨ What's your travel style?", "Options: luxury, moderate, budget-friendly"),
    ("special_requirements", "🔔 Any special requirements?", "e.g., dietary restrictions, accessibility needs (or type 'none')")
]

# Header
st.markdown('<h1 class="main-header">✈️ AI Trip Planner with A2A Protocol</h1>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📋 Trip Planning Progress")
    
    if st.session_state.conversation_complete:
        st.success("✅ Information gathering complete!")
        if st.session_state.itinerary:
            st.success("✅ Itinerary generated!")
    else:
        progress = st.session_state.current_question_index / len(QUESTIONS)
        st.progress(progress)
        st.write(f"Question {st.session_state.current_question_index + 1} of {len(QUESTIONS)}")
    
    st.markdown("---")
    st.header("🔑 Required Information")
    for key, question, _ in QUESTIONS:
        if key in st.session_state.user_answers:
            st.write(f"✅ {question.split('?')[0].replace('🌍 ', '').replace('🏠 ', '').replace('📅 ', '').replace('💰 ', '').replace('🎯 ', '').replace('✨ ', '').replace('🔔 ', '')}")
        else:
            st.write(f"⏳ {question.split('?')[0].replace('🌍 ', '').replace('🏠 ', '').replace('📅 ', '').replace('💰 ', '').replace('🎯 ', '').replace('✨ ', '').replace('🔔 ', '')}")
    
    if st.button("🔄 Start Over"):
        st.session_state.conversation_history = []
        st.session_state.conversation_complete = False
        st.session_state.itinerary = None
        st.session_state.crew = None
        st.session_state.conversation_id = None
        st.session_state.current_question_index = 0
        st.session_state.user_answers = {}
        st.rerun()

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("💬 Trip Planning Conversation")
    
    # Display conversation history
    for msg in st.session_state.conversation_history:
        if msg['role'] == 'user':
            st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message agent-message"><strong>🤖 Travel Assistant:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
    
    # Question interface
    if not st.session_state.conversation_complete:
        if st.session_state.current_question_index < len(QUESTIONS):
            key, question, placeholder = QUESTIONS[st.session_state.current_question_index]
            
            st.markdown(f'<div class="info-box"><strong>{question}</strong></div>', unsafe_allow_html=True)
            
            with st.form(key=f"question_form_{key}", clear_on_submit=True):
                user_input = st.text_input("Your answer:", placeholder=placeholder, key=f"input_{key}")
                submit_button = st.form_submit_button("Submit Answer")
                
                if submit_button and user_input:
                    # Store answer
                    st.session_state.user_answers[key] = user_input
                    
                    # Add to conversation history
                    st.session_state.conversation_history.append({
                        'role': 'agent',
                        'content': question
                    })
                    st.session_state.conversation_history.append({
                        'role': 'user',
                        'content': user_input
                    })
                    
                    # Move to next question
                    st.session_state.current_question_index += 1
                    
                    # Check if all questions answered
                    if st.session_state.current_question_index >= len(QUESTIONS):
                        st.session_state.conversation_complete = True
                    
                    st.rerun()
    
    # Generate itinerary button
    if st.session_state.conversation_complete and not st.session_state.itinerary:
        st.markdown("---")
        st.success("✅ All information collected! Ready to generate your personalized itinerary.")
        
        if st.button("🚀 Generate My Trip Itinerary", type="primary"):
            with st.spinner("🔄 Planning your amazing trip... This may take a few minutes..."):
                try:
                    # Create conversation ID
                    if not st.session_state.conversation_id:
                        st.session_state.conversation_id = str(uuid.uuid4())
                    
                    # Format the conversation into a transcript
                    conversation_transcript = "CONVERSATION TRANSCRIPT:\n\n"
                    for msg in st.session_state.conversation_history:
                        if msg['role'] == 'agent':
                            conversation_transcript += f"Agent: {msg['content']}\n"
                        else:
                            conversation_transcript += f"User: {msg['content']}\n"
                    
                    # Initialize crew if not already done
                    if not st.session_state.crew:
                        st.session_state.crew = TripPlannerCrew()
                    
                    # Generate itinerary using the main workflow (skip the conversation part)
                    # We'll directly create the tasks with the conversation data
                    st.info("📋 Creating travel plan with AI agents...")
                    
                    # This will run the full crew workflow
                    result = st.session_state.crew.plan_trip_from_transcript(
                        conversation_transcript,
                        st.session_state.conversation_id
                    )
                    
                    st.session_state.itinerary = result
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error generating itinerary: {str(e)}")
                    st.error("Please try again or contact support if the issue persists.")

with col2:
    st.header("📄 Your Travel Itinerary")
    
    if st.session_state.itinerary:
        # Display the generated itinerary
        st.markdown(st.session_state.itinerary)
        
        # Download button
        st.download_button(
            label="📥 Download Itinerary",
            data=st.session_state.itinerary,
            file_name="my_trip_itinerary.txt",
            mime="text/plain"
        )
    else:
        st.info("💡 Your detailed travel itinerary will appear here once all questions are answered and the trip is planned.")
        st.markdown("""
        **What you'll get:**
        - ✈️ Flight options with recommendations
        - 🏨 Hotel options with reviews and ratings
        - 📅 Day-by-day detailed itinerary
        - 🎯 Activities and restaurant recommendations
        - 💰 Complete budget breakdown
        - 💡 Travel tips and local insights
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Powered by CrewAI with A2A Protocol & MCP Integration</p>
</div>
""", unsafe_allow_html=True)
