import streamlit as st
import uuid
import re
from backend.graph import app as trip_agent
from backend.audit_logger import log_event, get_recent_logs

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
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.actual_spent = 0
    st.session_state.baseline_spent = 0

def record_token_usage(result_messages):
    """Reliably extracts prompt tokens from response metadata and calculates savings."""
    if not result_messages:
        return
        
    last_msg = result_messages[-1]
    turn_spent = 0
    
    if hasattr(last_msg, "response_metadata") and last_msg.response_metadata:
        usage = last_msg.response_metadata.get("token_usage", {})
        turn_spent = usage.get("prompt_tokens", 0) or usage.get("total_tokens", 0)
    
    if turn_spent == 0:
        msg_content = getattr(last_msg, "content", "")
        turn_spent = max(500, len(str(msg_content)) // 4)

    ui_chat_chars = sum(len(str(m["content"])) for m in st.session_state.messages)
    turn_baseline = (ui_chat_chars // 4) + 1200 
    
    st.session_state.actual_spent += turn_spent
    
    if turn_baseline > turn_spent:
        st.session_state.baseline_spent += turn_baseline
    else:
        st.session_state.baseline_spent += turn_spent

def render_hotel_card(content: str):
    """Parses hotel recommendations and renders them as sleek inline UI cards."""
    if "Hotel Name:" in content or "The Lalit" in content or "The Imperial" in content:
        st.markdown("### 🏨 Hotel Recommendation")
        with st.container(border=True):
            st.markdown(content)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Book This Hotel", key=f"book_{hash(content)}"):
                    st.success("Hotel selected and locked into your trip plan!")
            with col2:
                if st.button("🔄 Show Alternatives", key=f"alt_{hash(content)}"):
                    st.session_state.messages.append({"role": "user", "content": "Can you show me more alternative hotels?"})
                    st.rerun()
    else:
        st.markdown(content)

def get_ai_suggestions(current_status, last_assistant_message, latest_agent_name):
    """Dynamically generates contextual AI suggestion chips based on active agent and message content."""
    msg_lower = last_assistant_message.lower()
    suggestions = []

    if current_status == "gathering":
        if "dates" in msg_lower or "when" in msg_lower:
            suggestions = ["This weekend (3 days)", "Next month, 5 days", "Custom dates"]
        elif "budget" in msg_lower:
            suggestions = ["25,000 INR (Budget)", "50,000 INR (Comfort)", "Luxury tier"]
        elif "purpose" in msg_lower or "interests" in msg_lower:
            suggestions = ["Sightseeing & Shopping", "Foodie tour & Culture", "Relaxation & History"]
        elif "guests" in msg_lower or "traveling" in msg_lower:
            suggestions = ["Solo traveler", "2 Guests (Couple)", "Family of 4"]
        else:
            suggestions = ["Plan a 3-day itinerary", "Find hotels first", "Recommend local food"]

    elif "hotel" in msg_lower or latest_agent_name == "hotel_agent":
        suggestions = ["Book this hotel", "Show cheaper alternatives", "Look for hotels near Connaught Place"]

    elif current_status == "pending_approval":
        suggestions = ["Approve plan", "Add more historical sites", "Swap a day for shopping"]

    else:
        suggestions = ["Show me hotels", "Suggest local restaurants", "What about transport options?"]

    return suggestions[:3]

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

with st.sidebar:
    st.markdown("---")
    
    # Wrap the audit logs in a fragment so refreshing logs NEVER resets your main chat or trip session
    @st.fragment
    def render_audit_logs_fragment():
        with st.expander("🛠️ System Audit Logs", expanded=False):
            col_ref, col_dl = st.columns(2)
            with col_ref:
                if st.button("Refresh Logs"):
                    # Fragment-scoped rerun only updates this block, leaving the chat intact
                    st.rerun(scope="fragment")
            with col_dl:
                all_logs = get_recent_logs(100)
                log_text = "\n".join(all_logs)
                st.download_button(
                    label="📥 Download",
                    data=log_text,
                    file_name="tripcache_audit_logs.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
            recent_logs = get_recent_logs(15)
            for log in reversed(recent_logs):
                st.code(log, language="text")

    render_audit_logs_fragment()

# --- 5. Main Dual-Pane Layout Structure ---
chat_col, itinerary_col = st.columns([2, 1], gap="large")

# ==========================================
# LEFT PANE: Chat Interface & Input
# ==========================================
with chat_col:
    st.title("TripCacheAI ✈️")
    st.caption("Multi-Agent Travel Planner (Human-in-the-Loop + Streaming)")

    # Render existing chat history with card support
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_hotel_card(msg["content"])
            else:
                st.markdown(msg["content"])

    # --- Contextual AI Suggestion Chips (Only show after conversation starts) ---
    if st.session_state.messages:
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        current_state = trip_agent.get_state(config)
        current_status = current_state.values.get("plan_status", "gathering") if current_state.values else "gathering"
        
        messages = current_state.values.get("messages", []) if current_state.values else []
        latest_agent_name = getattr(messages[-1], "name", "") if messages else ""
        
        last_msg_text = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
        suggestions = get_ai_suggestions(current_status, last_msg_text, latest_agent_name)

        if suggestions:
            st.markdown("<small style='color: gray;'>💡 **Suggested Actions:**</small>", unsafe_allow_html=True)
            cols = st.columns(len(suggestions))
            for idx, suggestion in enumerate(suggestions):
                with cols[idx]:
                    if st.button(suggestion, key=f"sug_{idx}_{hash(suggestion)}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": suggestion})
                        
                        with st.chat_message("assistant"):
                            status_placeholder = st.status("TripCacheAI is thinking...", expanded=True)
                            inputs = {"messages": [("user", suggestion)]}
                            
                            try:
                                result = trip_agent.invoke(inputs, config=config)
                                final_content = result["messages"][-1].content
                                status_placeholder.update(label="Response ready!", state="complete", expanded=False)
                            except Exception as e:
                                final_content = f"API Rate Limited or Timeout Error: {str(e)}"
                                status_placeholder.update(label="Rate Limit / Timeout Notice", state="error", expanded=True)
                                st.warning("The LLM provider is currently rate-limiting requests. Please wait a few seconds and try again.")
                                
                            render_hotel_card(final_content)
                            record_token_usage(result.get("messages", []) if 'result' in locals() else [])
                            
                        st.session_state.messages.append({"role": "assistant", "content": final_content})
                        st.rerun()

    # Handle standard text input with streaming and rate-limit guard
    if user_input := st.chat_input("Where to? Or what would you like to change?"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        with st.chat_message("assistant"):
            status_placeholder = st.status("TripCacheAI is thinking...", expanded=True)
            
            inputs = {"messages": [("user", user_input)]}
            final_message_content = ""
            
            try:
                log_event("info", "ROUTER", f"Processing user input: {user_input}")
                for event in trip_agent.stream(inputs, config=config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_name != "__end__":
                            status_placeholder.update(label=f"Active Agent: **{node_name}** processing...", state="running")
                            log_event("info", "GRAPH_NODE", f"Node executed successfully", f"Node: {node_name}")
                            
                            if "messages" in node_output and node_output["messages"]:
                                latest_msg = node_output["messages"][-1]
                                content = getattr(latest_msg, "content", "")
                                if content and "Successfully transferred" not in content:
                                    final_message_content = content

                status_placeholder.update(label="Response ready!", state="complete", expanded=False)
                log_event("info", "SUCCESS", "Turn completed successfully.")
                
            except Exception as e:
                error_msg = str(e)
                log_event("error", "CRASH", "Graph execution failed or rate limited", error_msg)
                status_placeholder.update(label="API Rate Limit / Timeout - Check Audit Log", state="error", expanded=True)
                st.warning(f"System Notice: LLM provider rate limit reached. Please wait a few seconds. (Details: {error_msg})")
                final_message_content = "I encountered a rate limit or timeout processing your request. Please check your audit logs and try again."

            if not final_message_content or "Successfully transferred" in final_message_content:
                final_state = trip_agent.get_state(config)
                if final_state and final_state.values:
                    msgs = final_state.values.get("messages", [])
                    if msgs:
                        final_message_content = msgs[-1].content

            render_hotel_card(final_message_content)
            
            current_state = trip_agent.get_state(config)
            if current_state and current_state.values:
                all_msgs = current_state.values.get("messages", [])
                record_token_usage(all_msgs)
                
                plan_generated = any(getattr(m, "name", "") == "itinerary_expert" for m in all_msgs[-3:])
                if plan_generated:
                    trip_agent.update_state(config, {"plan_status": "pending_approval"})
                else:
                    trip_agent.update_state(config, {"plan_status": "gathering"})

        st.session_state.messages.append({
            "role": "assistant", 
            "content": final_message_content
        })
        st.rerun()

    # --- HITL Buttons ---
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
                    "content": "No problem! What would you like to change about this itinerary?"
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
        
        latest_plan = None
        for m in reversed(messages):
            if getattr(m, "name", "") == "itinerary_expert":
                if m.content and "Transferring back" not in m.content:
                    latest_plan = m.content
                    break
        
        if latest_plan:
            with st.container(height=650, border=True):
                split_regex = r'(?im)^(?=\s*(?:#{1,6}\s*)?(?:\*\*\s*)?Day\s*\d+)'
                chunks = re.split(split_regex, latest_plan)
                chunks = [c.strip() for c in chunks if c.strip()]
                
                intro_text = ""
                day_chunks = []
                
                for chunk in chunks:
                    if re.search(r'(?i)^\s*(?:#{1,6}\s*)?(?:\*\*\s*)?Day\s*\d+', chunk):
                        day_chunks.append(chunk)
                    else:
                        intro_text += chunk + "\n\n"
                        
                if len(day_chunks) > 0:
                    if intro_text and re.search(r'(?i)(morning|afternoon|evening)', intro_text):
                        day_chunks.insert(0, f"**Day 1**\n\n{intro_text}")
                        intro_text = ""
                        
                    if intro_text.strip():
                        st.markdown(intro_text)
                        
                    tab_names = []
                    for d in day_chunks:
                        match = re.search(r'(?i)Day\s*\d+', d)
                        tab_names.append(match.group(0).title() if match else "Day")
                        
                    if len(tab_names) > 0:
                        tabs = st.tabs(tab_names)
                        for i, tab in enumerate(tabs):
                            with tab:
                                st.markdown(day_chunks[i])
                else:
                    st.markdown(latest_plan)
        else:
            st.info("Your day-wise plan will appear here once generated.")
    else:
        st.info("Your day-wise plan will appear here once generated.")
