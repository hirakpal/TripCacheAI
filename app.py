import streamlit as st
import uuid
from backend.graph import app as trip_agent

st.set_page_config(page_title="TripCacheAI", layout="centered")

# Initialize session state for memory and thread ID
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("TripCacheAI ✈️")
st.caption("Multi-Agent Travel Planner Prototype")

# Sidebar controls
with st.sidebar:
    st.subheader("Session Controls")
    if st.button("Start New Trip"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.success("New session started!")

# Display chat history
# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 1. Explicitly assign the input to a variable first
user_input = st.chat_input("Where are you planning to go?")

# 2. Check if the user actually submitted something
if user_input:
    # Add user message to UI state
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Prepare configuration for LangGraph (this ties the turn to the specific thread_id)
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    with st.chat_message("assistant"):
        with st.spinner("TripCacheAI is thinking..."):
            # We only need to pass the newest message; LangGraph's checkpointer handles history
            inputs = {"messages": [("user", user_input)]}
            
            # Invoke the graph
            result = trip_agent.invoke(inputs, config=config)
            
            # Extract the final assistant message
            final_message = result["messages"][-1].content
            st.markdown(final_message)
            
            # Save assistant message to UI state
            st.session_state.messages.append({"role": "assistant", "content": final_message})