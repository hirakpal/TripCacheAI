import streamlit as st
import uuid
import re
from backend.graph import app as trip_agent

# --- 1. Set Layout & Custom CSS ---
st.set_page_config(page_title="TripCacheAI", layout="wide", page_icon="✈️")

st.markdown("""
<style>
    /* Shrink markdown headers and text to fit dual columns better */
    [data-testid="stMarkdownContainer"] h1 { font-size: 1.4rem !important; padding-bottom: 0.5rem; }
    [data-testid="stMarkdownContainer"] h2 { font-size: 1.2rem !important; padding-bottom: 0.5rem; }
    [data-testid="stMarkdownContainer"] h3 { font-size: 1.0rem !important; padding-bottom: 0.5rem; }
    [data-testid="stMarkdownContainer"] p, 
    [data-testid="stMarkdownContainer"] li { font-size: 0.9rem !important; line-height: 1.5; }
    
    /* Give sidebar metrics a sleek look */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. Callbacks & Helper Functions ---
def reset_trip():
    """Wipes the frontend chat, resets token stats, and generates a new thread ID."""
    # 1. Generate a brand new LangGraph Thread ID (Clears Backend Memory)
    st.session_state.thread_id = str(uuid.uuid4())
    # 2. Empty the UI chat bubbles (Clears Frontend Memory)
    st.session_state.messages = []
    st.session_state.actual_spent = 0
    st.session_state.baseline_spent = 0

def record_token_usage(result_messages):
    """Calculates token savings by estimating the full context weight vs actual."""
    if not result_messages:
        return
        
    last_msg = result_messages[-1]
    if hasattr(last_msg, "response_metadata"):
        # Get just the input (prompt) tokens billed by Groq
        turn_spent = last_msg.response_metadata.get("token_usage", {}).get("prompt_tokens", 0)
        
        # Estimate baseline: UI chat history + roughly 1000 tokens for system prompts/tools
        ui_chat_chars = sum(len(str(m["content"])) for m in st.session_state.messages)
        turn_baseline = (ui_chat_chars // 4) + 1000 
        
        st.session_state.actual_spent += turn_spent
        
        # Only record savings if the baseline exceeds what Groq actually charged
        if turn_baseline > turn_spent:
            st.session_state.baseline_spent += turn_baseline
        else:
            st.session_state.baseline_spent += turn_spent

# --- 3. Initialize Session State ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "actual_spent" not in st.session_state:
    st.session_state.actual_spent = 0
if "baseline_spent" not in st.session_state:
    st.session_state.baseline_spent = 0

# --- 4. Sidebar Controls & Token Analytics ---
with st.sidebar:
    st.subheader("🛠️ Session Controls")
    st.button("🔄 Start New Trip", on_click=reset_trip, use_container_width=True)
    
    st.markdown("---")
    st.subheader("⚡ Token Optimization")
    
    spent = st.session_state.actual_spent
    baseline = st.session_state.baseline_spent
    saved = max(0, baseline - spent)
    
    perc_saved = (saved / baseline * 100) if baseline > 0 else 0.0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Spent", value=f"{spent:,}")
    with col2:
        st.metric(label="Saved", value=f"{saved:,}", delta=f"{perc_saved:.1f}%")
        
    st.caption("Context Trimming Efficiency")
    st.progress(min(1.0, perc_saved / 100))

# --- 5. Main Dual-Pane Layout Structure ---
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
        # Use st.write_stream to consume LangGraph's streaming output live
        def generate_response_stream():
            inputs = {"messages": [("user", user_input)]}
            
            # Stream events from the graph (stream mode "updates" or "messages")
            for event in trip_agent.stream(inputs, config=config, stream_mode="updates"):
                # You can even show agent node transitions dynamically if desired!
                for node_name, node_output in event.items():
                    if node_name != "__end__" and "messages" in node_output:
                        latest_msg = node_output["messages"][-1]
                        # If the message is text from an assistant or tool output, yield it
                        if hasattr(latest_msg, "content") and latest_msg.content:
                            # Yield chunks of text for real-time rendering
                            yield latest_msg.content

        # Streamlit handles the real-time typing effect natively
        final_message_content = st.write_stream(generate_response_stream())
        
    # Save cleanly to session history after streaming completes
    st.session_state.messages.append({
        "role": "assistant", 
        "content": final_message_content
    })
    st.rerun()

    # --- HITL Buttons (Rendered in Chat Column) ---
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    current_state = trip_agent.get_state(config)
    current_status = current_state.values.get("plan_status", "gathering") if current_state.values else "gathering"

    if current_status == "pending_approval":
        st.markdown("---")
        st.write("**What do you think of this suggestion?**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Approve Plan", use_container_width=True):
                approval_msg = "I approve this plan. Let's lock it in."
                
                trip_agent.update_state(config, {"plan_status": "approved"})
                st.session_state.messages.append({"role": "user", "content": approval_msg})
                
                with st.spinner("Finalizing..."):
                    inputs = {"messages": [("user", approval_msg)]}
                    result = trip_agent.invoke(inputs, config=config)
                    
                    record_token_usage(result.get("messages", []))
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["messages"][-1].content
                    })
                st.rerun()
                
        with col2:
            if st.button("🔄 Revise Plan", use_container_width=True):
                trip_agent.update_state(config, {"plan_status": "gathering"})
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "No problem! What would you like to change about this itinerary? (e.g., 'Swap day 2 for a beach day', or 'Find a cheaper hotel')"
                })
                st.rerun()


# ==========================================
# RIGHT PANE: Dedicated Itinerary Display
# ==========================================
with itinerary_col:
    st.subheader("📅 Your Itinerary")
    
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    current_state = trip_agent.get_state(config)
    
    if current_state and current_state.values:
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
                
                # --- UPDATED: Bulletproof Tab Parsing Logic ---
                # 1. More robust regex that handles markdown bold (**Day 1**) or headers (### Day 1)
                split_regex = r'(?im)^(?=\s*(?:#{1,6}\s*)?(?:\*\*\s*)?Day\s*\d+)'
                chunks = re.split(split_regex, latest_plan)
                chunks = [c.strip() for c in chunks if c.strip()]
                
                intro_text = ""
                day_chunks = []
                
                # 2. Categorize chunks
                for chunk in chunks:
                    if re.search(r'(?i)^\s*(?:#{1,6}\s*)?(?:\*\*\s*)?Day\s*\d+', chunk):
                        day_chunks.append(chunk)
                    else:
                        intro_text += chunk + "\n\n"
                        
                # 3. FIX for the LLM hallucination (Forgot to write "Day 1")
                # If we have "Day 2" but the intro text contains schedule details, wrap intro as Day 1.
                if len(day_chunks) > 0:
                    if intro_text and re.search(r'(?i)(morning|afternoon|evening)', intro_text):
                        day_chunks.insert(0, f"**Day 1**\n\n{intro_text}")
                        intro_text = "" # Clear intro so it doesn't double-render
                        
                    # Render any remaining intro text (like "Here is your trip to Delhi!")
                    if intro_text.strip():
                        st.markdown(intro_text)
                        
                    # 4. Extract tab names safely
                    tab_names = []
                    for d in day_chunks:
                        match = re.search(r'(?i)Day\s*\d+', d)
                        tab_names.append(match.group(0).title() if match else "Day")
                        
                    # 5. Build Streamlit Tabs
                    if len(tab_names) > 0:
                        tabs = st.tabs(tab_names)
                        for i, tab in enumerate(tabs):
                            with tab:
                                st.markdown(day_chunks[i])
                else:
                    # Fallback if no days are detected at all
                    st.markdown(latest_plan)
        else:
            st.info("Your day-wise plan will appear here once generated.")
    else:
        st.info("Your day-wise plan will appear here once generated.")
