import streamlit as st
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent

# Initialize the shared LLM
model = ChatOpenAI(
    model="gpt-4o", 
    temperature=0, 
    api_key=st.secrets["OPENAI_API_KEY"]
)

# Instantiate the separate agents
hotel_agent = get_hotel_agent(model)
trip_context_agent = get_context_agent(model)

# Set up the supervisor workflow
workflow = create_supervisor(
    agents=[trip_context_agent, hotel_agent],
    model=model,
    prompt=(
        "You are the supervisor of TripCacheAI, a travel planning team. "
        "If the user's request is missing city, budget, or trip purpose, route to 'trip_context_expert'. "
        "If the user has provided enough details to search, route to 'hotel_expert'. "
        "Always produce a friendly, concise final response."
    ),
    output_mode="last_message",
)

# Compile with memory
memory = InMemorySaver()
app = workflow.compile(checkpointer=memory)