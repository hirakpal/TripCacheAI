import sqlite3
import streamlit as st
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
#from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState

# 1. Define the explicit state schema
class TripState(TypedDict):
    plan_status: str  # Tracks: "gathering", "pending_approval", "approved"

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

# Initialize the shared LLM using Streamlit secrets
model = ChatOpenAI(
    model="gpt-4o", 
    temperature=0, 
    api_key=st.secrets["OPENAI_API_KEY"]
)

# Instantiate the separate agents
hotel_agent = get_hotel_agent(model)
trip_context_agent = get_context_agent(model)
itinerary_agent = get_itinerary_agent(model)  # NEW INSTANCE

# Set up the supervisor workflow
workflow = create_supervisor(
    agents=[trip_context_agent, hotel_agent, itinerary_agent], # ADDED ITINERARY AGENT
    model=model,
    prompt=(
        "You are the supervisor of TripCacheAI, a travel planning team. "
        "1. If the user's request is missing basic info (city, budget, trip purpose), route to 'trip_context_expert'. "
        "2. If the user is asking for accommodation or where to stay, route to 'hotel_expert'. "
        "3. If the user asks for a schedule, day-by-day plan, or things to do, route to 'itinerary_expert'. "
        "Always synthesize the final answer concisely and in a friendly tone."
    ),
    state_schema=TripState,
    output_mode="last_message",
)
# Initialize the SQLite checkpointer. 
# This automatically creates a 'trip_memory.sqlite' file in your project root.
# Create a persistent connection and pass it to the saver ---
# check_same_thread=False allows Streamlit's multiple threads to share this connection
conn = sqlite3.connect("trip_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
# Compile with memory
#memory = InMemorySaver()
app = workflow.compile(checkpointer=memory)
