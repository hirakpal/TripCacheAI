import streamlit as st
import uuid
from backend.graph import app as trip_agent

st.set_page_config(page_title="TripCacheAI", layout="centered")

# 1. Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Define the reset callback function ---
def reset_trip():
    """Wipes the frontend chat and generates a new LangGraph thread ID."""
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    

st.title("TripCacheAI ✈️")
st.caption("Multi-Agent Travel Planner (Human-in-the-Loop)")

# 2. Sidebar controls
with st.sidebar:
    st.subheader("Session Controls")
    st.button("Start New Trip", on_click=reset_trip)

# 3. Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Determine if we should show HITL Action Buttons
show_buttons = False
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
    # Retrieve the source we saved earlier
    last_source = st.session_state.messages[-1].get("source", "")
    
    # Only show buttons if the plan-generating agents just spoke
    if last_source in ["hotel_expert", "itinerary_expert"]:
        show_buttons = True

# 5. Handle standard text input
if user_input := st.chat_input("Where to? Or what would you like to change?"):
    # Display and save user message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Prepare configuration for LangGraph memory
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    # Invoke the multi-agent graph
    with st.chat_message("assistant"):
        with st.spinner("TripCacheAI is thinking..."):
            inputs = {"messages": [("user", user_input)]}
            result = trip_agent.invoke(inputs, config=config)
            
            # Extract the raw AIMessage object
            final_ai_message = result["messages"][-1]
            final_message_content = final_ai_message.content
            # Check if a specialist acted during this turn
            plan_generated = False
            for m in reversed(result["messages"]):
                if m.type == "human": 
                    break

                agent_name = getattr(m, "name", "")
                if agent_name == "itinerary_expert":
                    plan_generated = True
                    break
            # --- NEW: Explicitly commit the state transition to the database ---
            if plan_generated:
                trip_agent.update_state(config, {"plan_status": "pending_approval"})
            else:
                trip_agent.update_state(config, {"plan_status": "gathering"})

            st.markdown(final_message_content)
            
    # Save the assistant's response to UI state and force a rerun to update buttons
    st.session_state.messages.append({
        "role": "assistant", 
        "content": final_message_content,
        
    })
    st.rerun()

# 6. Render the HITL Action Buttons
# Fetch the current state directly from the SQLite database
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
            
            # --- NEW: Explicitly transition the state to approved ---
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
