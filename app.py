import streamlit as st
import uuid
from backend.graph import app as trip_agent

st.set_page_config(page_title="TripCacheAI", layout="centered")

# 1. Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("TripCacheAI ✈️")
st.caption("Multi-Agent Travel Planner (Human-in-the-Loop)")

# 2. Sidebar controls
with st.sidebar:
    st.subheader("Session Controls")
    if st.button("Start New Trip"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# 3. Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Determine if we should show HITL Action Buttons
show_buttons = False
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
    last_message_text = st.session_state.messages[-1]["content"]
    
    # Heuristic: If the message ends with a question mark, the context agent is likely still gathering info.
    # We only show buttons if it appears to be a finalized proposal (no trailing question mark).
    if not last_message_text.strip().endswith("?"):
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
            
            final_message = result["messages"][-1].content
            st.markdown(final_message)
            
    # Save the assistant's response to UI state and force a rerun to update buttons
    st.session_state.messages.append({"role": "assistant", "content": final_message})
    st.rerun()

# 6. Render the HITL Action Buttons
if show_buttons:
    st.markdown("---")
    st.write("**What do you think of this suggestion?**")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Approve Plan"):
            approval_msg = "I approve this plan. Let's lock it in."
            
            # Save the simulated user approval to UI state
            st.session_state.messages.append({"role": "user", "content": approval_msg})
            
            # Update the backend LangGraph memory so the supervisor knows it was approved
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            with st.spinner("Finalizing..."):
                inputs = {"messages": [("user", approval_msg)]}
                result = trip_agent.invoke(inputs, config=config)
                st.session_state.messages.append({"role": "assistant", "content": result["messages"][-1].content})
            
            # Refresh the UI to clear the buttons and show the finalization message
            st.rerun()
            
    with col2:
        if st.button("🔄 Revise Plan"):
            # Inform the user to use the standard input for revisions
            st.info("Please type the changes you'd like to make in the chat box below!")
