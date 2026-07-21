import sqlite3
import streamlit as st
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
#from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

from langgraph.graph import MessagesState

# 1. Define the explicit state schema
class TripState(MessagesState):
    plan_status: str  # Tracks: "gathering", "pending_approval", "approved"
    remaining_steps: int # Required by LangGraph to prevent infinite loops

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

# # --- NEW IMPORTS FOR MOCK LLM ---
# from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
# from langchain_core.messages import AIMessage

# # 1. Create a custom wrapper to safely handle LangGraph's tool binding
# class SafeMockLLM(FakeMessagesListChatModel):
#     def bind_tools(self, *args, **kwargs):
#         """
#         Intercepts LangGraph's attempt to bind the 'route' tool to the LLM.
#         Returns the LLM itself to prevent NotImplemented errors.
#         """
#         return self

# # 2. Define the exact, strict sequence of events for a single user turn
# mock_sequence = [
#     # Turn 1: Supervisor decides to route to the planner
#     AIMessage(
#         content="", 
#         tool_calls=[{"name": "route", "args": {"next": "itinerary_expert"}, "id": "mock_call_1"}]
#     ),
#     # Turn 2: The planner generates the day-by-day plan
#     AIMessage(
#         content=(
#             "Here is your mock itinerary:\n\n"
#             "Day 1: Historical Tour\n"
#             "Morning: Visit the Red Fort\n\n"
#             "Day 2: Local Cuisine\n"
#             "Morning: Paranthe Wali Gali"
#         )
#     ),
#     # Turn 3: The supervisor synthesizes the final response for the user
#     AIMessage(
#         content="I have generated a 2-day mock itinerary for you! Let me know if you want to revise it."
#     )
# ]

# # 3. Initialize the mock model
# # (Comment out your ChatOpenAI model and use this instead)
# model = SafeMockLLM(responses=mock_sequence)

from langchain_ollama import ChatOllama

# Initialize the model exactly as before
model = ChatOllama(model="llama3.1", temperature=0)

# Initialize the shared LLM using Streamlit secrets
# model = ChatOpenAI(
#     model="gpt-4o", 
#     temperature=0, 
#     api_key=st.secrets["OPENAI_API_KEY"]
# )

# Instantiate the separate agents
hotel_agent = get_hotel_agent(model)
trip_context_agent = get_context_agent(model)
itinerary_agent = get_itinerary_agent(model)  # NEW INSTANCE

# Set up the supervisor workflow
workflow = create_supervisor(
    agents=[trip_context_agent, hotel_agent, itinerary_agent],
    model=model,
    prompt=(
        "You are the supervisor of TripCacheAI, a travel planning team. "
        "1. If the user's request is missing basic info, route to 'trip_context_expert'. "
        "2. If the user asks for accommodation, route to 'hotel_expert'. "
        "3. If the user asks for a schedule, things to do, OR wants to modify/revise an existing plan, ALWAYS route to 'itinerary_expert'. " # <-- THE FIX
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
