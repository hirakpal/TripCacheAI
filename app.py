import streamlit as st
import uuid
import re
from backend.graph import get_compiled_graph
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
    st.session_state.daily_limit_exceeded = False
    st.session_state.rate_limit_details = {"used": 0, "limit": 100000, "requested": 0}

def parse_rate_limit_error(error_msg: str):
    """Extracts actual used, limit, and requested token counts from 429 error messages."""
    limit = re.search(r'Limit\s+(\d+)', error_msg)
    used = re.search(r'Used\s+(\d+)', error_msg)
    requested = re.search(r'Requested\s+(\d+)', error_msg)
    
    return {
        "limit": int(limit.group(1)) if limit else 100000,
        "used": int(used.group(1)) if used else 0,
        "requested": int(requested.group(1)) if requested else 0,
    }

def record_token_usage(result_messages, was_error: bool = False):
    """Calculates token metrics using real response metadata; ignores failed turns."""
    if was_error or not result_messages:
        return  # Don't skew stats on crashed turns

    last_msg = result_messages[-1]
    turn_spent = 0
    
    if hasattr(last_msg, "response_metadata") and last_msg.response_metadata:
        usage = last_msg.response_metadata.get("token_usage", {})
        turn_spent = usage.get("prompt_tokens", 0) or usage.get("total_tokens", 0)
    
    if turn_spent == 0:
        msg_content = getattr(last_msg, "content", "")
        turn_spent = len(str(msg_content)) // 4

    # Calculate actual turn baseline from uncompressed chat length
    ui_chat_chars = sum(len(str(m["content"])) for m in st.session_state.messages)
    turn_baseline = max(turn_spent, (ui_chat_chars // 4) + 500)
    
    st.session_state.actual_spent += turn_spent
    st.session_state.baseline_spent += turn_baseline

def render_hotel_card(content: str, card_index: int = 0):
    """Parses hotel recommendations and renders them as sleek inline UI cards with unique keys."""
    if "Hotel Name:" in content or "The Lalit" in content or "The Imperial" in content:
        st.markdown("### 🏨 Hotel Recommendation")
        with st.container(border=True):
            st.markdown(content)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Book This Hotel", key=f"book_hotel_{card_index}_{hash(content)}"):
                    st.success("Hotel selected and locked into your trip plan!")
            with col2:
                if st.button("🔄 Show Alternatives", key=f"alt_hotel_{card_index}_{hash(content)}"):
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
if "daily_limit_exceeded" not in st.session_state:
    st.session_state.daily_limit_exceeded = False
if "rate_limit_details" not in st.session_state:
    st.session_state.rate_limit_details = {"used": 0, "limit": 100000, "requested": 0}

# --- 4. Sidebar Controls & Token Analytics ---
with st.sidebar:
    st.subheader("🛠️ Session Controls")
    st.button("🔄 Start New Trip", on_click=reset_trip, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🤖 LLM Selection")
    
    available_models = [
        # Groq Models
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        
        # OpenAI Models
        "gpt-4o",
        "gpt-4o-mini",
        
        # Google Gemini Models
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        
        # Anthropic Claude Models
        "claude-3-5-sonnet-20241022",
    ]
    
    selected_model = st.selectbox(
        "Active Model:",
        options=available_models,
        index=0,
        key="selected_model"
    )
    
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

    # Dynamic Alert Box for Token Quota / Rate Limit Breaches
    if st.session_state.get("daily_limit_exceeded", False):
        err_data = st.session_state.get("rate_limit_details", {"used": 0, "limit": 100000, "requested": 0})
        
        st.error("⚠️ **Daily Token Cap Reached!**")
        st.caption(
            f"Used **{err_data['used']:,} / {err_data['limit']:,}** daily tokens. "
            f"Your last request ({err_data['requested']:,} tokens) breached the cap. "
            "Please select a different model above to continue."
        )

    st.markdown("---")
    
    @st.fragment
    def render_audit_logs_fragment():
        with st.expander("🛠️ System Audit Logs", expanded=False):
            col_ref, col_dl = st.columns(2)
            with col_ref:
                if st.button("Refresh Logs", key="refresh_audit_logs_btn"):
                    st.rerun(scope="fragment")
            with col_dl:
                all_logs = get_recent_logs(100)
                log_text = "\n".join(all_logs)
                st.download_button(
                    label="📥 Download",
                    data=log_text,
                    file_name="tripcache_audit_logs.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_audit_logs_btn"
                )
                
            recent_logs = get_recent_logs(15)
            for log_idx, log in enumerate(reversed(recent_logs)):
                st.code(log, language="text")

    render_audit_logs_fragment()

# --- Instantiates the Graph with the Selected Model ---
trip_agent = get_compiled_graph(st.session_state.selected_model)

# --- 5. Main Dual-Pane Layout Structure ---
chat_col, itinerary_col = st.columns([2, 1], gap="large")

# ==========================================
# LEFT PANE: Chat Interface & Input
# ==========================================
with chat_col:
    st.title("TripCacheAI ✈️")
    st.caption("Multi-Agent Travel Planner (Human-in-the-Loop + Streaming)")

    # Render existing chat history
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_hotel_card(msg["content"], card_index=idx)
            else:
                st.markdown(msg["content"])

    # --- Contextual AI Suggestion Chips ---
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
                        # Pass the exact suggestion text directly—no custom logic needed!
                        st.session_state.messages.append({"role": "user", "content": suggestion})

                        with st.chat_message("assistant"):
                            status_placeholder = st.status("TripCacheAI is thinking...", expanded=True)
                            inputs = {"messages": [("user", suggestion)]}
                            was_error = False

                            try:
                                result = trip_agent.invoke(inputs, config=config)
                                final_content = result["messages"][-1].content
                                st.session_state.daily_limit_exceeded = False
                                status_placeholder.update(label="Response ready!", state="complete", expanded=False)
                            except Exception as e:
                                was_error = True
                                error_str = str(e)
                                if "429" in error_str or "rate_limit" in error_str or "tokens" in error_str:
                                    st.session_state.daily_limit_exceeded = True
                                    st.session_state.rate_limit_details = parse_rate_limit_error(error_str)
                                final_content = "API Rate Limited or Quota Exceeded. Please switch models in the sidebar."
                                status_placeholder.update(label="Rate Limit / Quota Exceeded", state="error", expanded=True)
                                st.warning("Quota reached on selected model. Please switch to another model in the sidebar.")

                            render_hotel_card(final_content, card_index=999)
                            if not was_error:
                                record_token_usage(result.get("messages", []) if 'result' in locals() else [])

                        st.session_state.messages.append({"role": "assistant", "content": final_content})
                        st.rerun()

    # Handle standard text input
    if user_input := st.chat_input("Where to? Or what would you like to change?"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        with st.chat_message("assistant"):
            status_placeholder = st.status("TripCacheAI is thinking...", expanded=True)
            
            inputs = {"messages": [("user", user_input)]}
            final_message_content = ""
            was_error = False
            
            try:
                log_event("info", "ROUTER", f"Processing user input with {st.session_state.selected_model}: {user_input}")
                for event in trip_agent.stream(inputs, config=config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_name != "__end__":
                            status_placeholder.update(label=f"Active Agent: **{node_name}** processing...", state="running")
                            log_event("info", "GRAPH_NODE", "Node executed successfully", f"Node: {node_name}")
                            
                            if "messages" in node_output and node_output["messages"]:
                                latest_msg = node_output["messages"][-1]
                                content = getattr(latest_msg, "content", "")
                                if content and "Successfully transferred" not in content:
                                    final_message_content = content

                status_placeholder.update(label="Response ready!", state="complete", expanded=False)
                log_event("info", "SUCCESS", "Turn completed successfully.")
                st.session_state.daily_limit_exceeded = False
                
            except Exception as e:
                was_error = True
                error_msg = str(e)
                log_event("error", "CRASH", "Graph execution failed or rate limited", error_msg)
                
                if "429" in error_msg or "rate_limit" in error_msg or "tokens" in error_msg:
                    st.session_state.daily_limit_exceeded = True
                    st.session_state.rate_limit_details = parse_rate_limit_error(error_msg)
                
                status_placeholder.update(label="API Quota / Rate Limit Breached", state="error", expanded=True)
                st.warning(f"System Notice: Daily token limit or rate limit reached on model `{st.session_state.selected_model}`. Please switch models in the sidebar.")
                final_message_content = "Daily token cap or rate limit reached. Please switch models in the left sidebar to continue."

            if not final_message_content or "Successfully transferred" in final_message_content:
                final_state = trip_agent.get_state(config)
                if final_state and final_state.values:
                    msgs = final_state.values.get("messages", [])
                    if msgs:
                        final_message_content = msgs[-1].content

            render_hotel_card(final_message_content, card_index=888)
            
            current_state = trip_agent.get_state(config)
            if current_state and current_state.values:
                all_msgs = current_state.values.get("messages", [])
                record_token_usage(all_msgs, was_error=was_error)
                
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
            if st.button("✅ Approve Plan", key="approve_plan_btn", use_container_width=True):
                approval_msg = "I approve this plan. Let's lock it in."
                trip_agent.update_state(config, {"plan_status": "approved"})
                st.session_state.messages.append({"role": "user", "content": approval_msg})
                
                with st.spinner("Finalizing..."):
                    inputs = {"messages": [("user", approval_msg)]}
                    try:
                        result = trip_agent.invoke(inputs, config=config)
                        record_token_usage(result.get("messages", []))
                        res_content = result["messages"][-1].content
                        st.session_state.daily_limit_exceeded = False
                    except Exception as e:
                        err_str = str(e)
                        if "429" in err_str or "rate_limit" in err_str or "tokens" in err_str:
                            st.session_state.daily_limit_exceeded = True
                            st.session_state.rate_limit_details = parse_rate_limit_error(err_str)
                        res_content = "Rate limit or quota reached. Switch models in the sidebar."
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": res_content
                    })
                st.rerun()
                
        with col2:
            if st.button("🔄 Revise Plan", key="revise_plan_btn", use_container_width=True):
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
