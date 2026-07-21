import streamlit as st
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from your_module import app  # import your compiled LangGraph workflow

st.set_page_config(page_title="TravelWeaver Prototype", layout="wide")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "thread-001"
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("TravelWeaver – Multi-Agent Travel Planner (Prototype)")

with st.sidebar:
    st.subheader("Session controls")
    new_thread = st.button("New trip session")
    if new_thread:
        st.session_state.thread_id = f"thread-{st.session_state.thread_id.split('-')[-1]}-new"
        st.session_state.messages = []
        st.success("Started a new trip session.")

st.write("Chat with the front desk agent. The supervisor will call hotel and planner/validator agents as needed.")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    else:
        st.chat_message("assistant").markdown(msg["content"])

user_input = st.chat_input("Describe your trip (destination, days, budget)...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    config = {
        "configurable": {
            "thread_id": st.session_state.thread_id,
        }
    }

    result = app.invoke({"messages": st.session_state.messages}, config=config)
    st.session_state.messages = result["messages"]

    st.chat_message("assistant").markdown(result["messages"][-1]["content"])
