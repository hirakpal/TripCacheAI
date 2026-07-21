import streamlit as st
import uuid
from backend.graph import app as trip_agent
import re

# --- 1. Set Layout ---
# Use "wide" to support the dual-pane layout
st.set_page_config(page_title="TripCacheAI", layout="wide")

# --- Inject Custom CSS for better text sizing ---
st.markdown("""
<style>
    /* Shrink markdown headers and text to fit the columns better */
    [data-testid="stMarkdownContainer"] h1 { font-size: 1.4rem !important; padding-bottom: 0.5rem; }
    [data-testid="stMarkdownContainer"] h2 { font-size: 1.2rem !important; padding-bottom: 0.5rem; }
    [data-testid="stMarkdownContainer"] h3 { font-size: 1.0rem !important; padding-bottom: 0.5rem; }
    [data-testid="stMarkdownContainer"] p, 
    [data-testid="stMarkdownContainer"] li { font-size: 0.9rem !important; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# --- 2. Callbacks ---
def reset_trip():
    """Wipes the frontend chat and generates a new LangGraph thread ID."""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

# --- 3. Initialize Session State ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. Sidebar Controls ---
with st.sidebar:
    st.subheader("Session Controls")
    st.button("Start New Trip", on_click=reset_trip)

# --- 5. Main Layout Structure ---
# Chat takes up ~65% of the screen, Itinerary takes ~35%
chat_col, itinerary_col = st.columns([2, 1], gap="large")

# ==========================================
# LEFT PANE: Chat Interface & Input
# ==========================================
with chat_col:
    st.title("TripCacheAI ✈️")
    st.caption("Multi-Agent Travel Planner (Human-in-the-Loop)")

    # Render existing chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle standard text input
    if user_input := st.chat_input("Where to? Or what would you like to change?"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        with st.chat_message("assistant"):
            with st.spinner("TripCacheAI is thinking..."):
                inputs = {"messages": [("user", user_input)]}
                result = trip_agent.invoke(inputs, config=config)
                
                final_message_content = result["messages"][-1].content
                
                # Check if the planner generated a day-wise plan during this turn
                plan_generated = False
                for m in reversed(result["messages"]):
                    if m.type == "human": 
                        break
                    
                    agent_name = getattr(m, "name", "")
                    
                    # Strict check for the planner agent
                    if agent_name == "itinerary_expert":
                        plan_generated = True
                        break
                
                # Explicitly commit the state transition to the database
                if plan_generated:
                    trip_agent.update_state(config, {"plan_status": "pending_approval"})
                else:
                    trip_agent.update_state(config, {"plan_status": "gathering"})
                
                st.markdown(final_message_content)
                
        # Save the assistant's response cleanly
        st.session_state.messages.append({
            "role": "assistant", 
            "content": final_message_content
        })
        st.rerun()

    # --- HITL Buttons (Rendered in Chat Column) ---
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    current_state = trip_agent.get_state(config)
    current_status = current_state.values.get("plan_status", "gathering")

    if current_status == "pending_approval":
        st.markdown("---")
        st.write("**What do you think of this suggestion?**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Approve Plan"):
                approval_msg = "I approve this plan. Let's lock it in."
                
                # Explicitly transition the state to approved
                trip_agent.update_state(config, {"plan_status": "approved"})
                
                st.session_state.messages.append({"role": "user", "content": approval_msg})
                with st.spinner("Finalizing..."):
                    inputs = {"messages": [("user", approval_msg)]}
                    result = trip_agent.invoke(inputs, config=config)
                    st.session_state.messages.append({"role": "assistant", "content": result["messages"][-1].content})
                st.rerun()
                
        with col2:
            if st.button("🔄 Revise Plan"):
                st.info("Please type the changes you'd like to make in the chat box below!")


# ==========================================
# RIGHT PANE: Dedicated Itinerary Display
# ==========================================
with itinerary_col:
    st.subheader("📅 Your Itinerary")
    
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    current_state = trip_agent.get_state(config)
    
    if current_state.values:
        messages = current_state.values.get("messages", [])
        
        # Search backwards to find the actual day-by-day plan
        latest_plan = None
        for m in reversed(messages):
            if getattr(m, "name", "") == "itinerary_expert":
                if m.content and "Transferring back" not in m.content:
                    latest_plan = m.content
                    break
        
        if latest_plan:
            with st.container(height=650, border=True):
                # --- NEW: Dynamic Tab Parsing Logic ---
                
                # Split the text right before any line that starts with "Day X"
                # (Handles markdown like "## Day 1:", "**Day 2**", etc.)
                chunks = re.split(r'(?im)^(?=#{0,4}\s*\*?Day\s*\d+)', latest_plan)
                chunks = [c.strip() for c in chunks if c.strip()]
                
                intro_text = ""
                day_chunks = []
                
                # Categorize the chunks into "Intro" vs "Actual Days"
                for chunk in chunks:
                    if re.search(r'(?i)^#{0,4}\s*\*?Day\s*\d+', chunk):
                        day_chunks.append(chunk)
                    else:
                        intro_text += chunk + "\n\n"
                        
                # If we found multiple days, render the tabs!
                if len(day_chunks) > 1:
                    if intro_text:
                        st.markdown(intro_text) # Render any intro text above the tabs
                        
                    # Extract clean tab names (e.g., "Day 1", "Day 2")
                    tab_names = []
                    for d in day_chunks:
                        match = re.search(r'(?i)Day\s*\d+', d)
                        tab_names.append(match.group(0).title() if match else "Day")
                        
                    # Generate the tabs dynamically
                    tabs = st.tabs(tab_names)
                    
                    # Fill each tab with its respective content
                    for i, tab in enumerate(tabs):
                        with tab:
                            st.markdown(day_chunks[i])
                else:
                    # Fallback: Just render normally if it's 1 day or parsing failed
                    st.markdown(latest_plan)
        else:
            st.info("Your day-wise plan will appear here once generated.")
    else:
        st.info("Your day-wise plan will appear here once generated.")
