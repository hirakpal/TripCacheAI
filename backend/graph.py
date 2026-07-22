import sqlite3
import streamlit as st
from typing import Annotated
from langchain_core.messages import BaseMessage, trim_messages
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

# ==========================================
# 1. THE TOKEN MANAGEMENT REDUCER
# ==========================================
def token_trimming_reducer(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Intercepts new messages and trims history to prevent API rate limits."""
    # Add new messages to the history using the standard method
    combined = add_messages(left, right)
    
    # Trim the conversation down to a safe limit for the 8B model (~1500 tokens)
    return trim_messages(
        combined,
        max_tokens=1500, 
        strategy="last",
        token_counter=lambda msgs: sum(len(str(m.content)) // 4 for m in msgs),
        include_system=True,
        start_on="human",
        allow_partial=False
    )

# ==========================================
# 2. THE OPTIMIZED STATE SCHEMA
# ==========================================
class TripState(MessagesState):
    # Override the default 'messages' behavior from MessagesState
    # to use our custom trimmer instead of the default add_messages
    messages: Annotated[list[BaseMessage], token_trimming_reducer]
    plan_status: str  
    remaining_steps: int 

# ==========================================
# 3. INITIALIZE GROQ LLM
# ==========================================
model = ChatGroq(
    model="llama-3.1-8b-instant", # The highly available, fast Meta model
    temperature=0, 
    max_retries=10, # Auto-recovers from any rogue 429 rate limit errors
    api_key=st.secrets["GROQ_API_KEY"]
)
# Initialize the shared LLM using Streamlit secrets
# model = ChatOpenAI(
#     model="gpt-4o", 
#     temperature=0, 
#     api_key=st.secrets["OPENAI_API_KEY"]
# )
# ==========================================
# 4. INSTANTIATE AGENTS
# ==========================================
hotel_agent = get_hotel_agent(model)
trip_context_agent = get_context_agent(model)
itinerary_agent = get_itinerary_agent(model) 

# ==========================================
# 5. SUPERVISOR WORKFLOW
# ==========================================
workflow = create_supervisor(
    agents=[trip_context_agent, hotel_agent, itinerary_agent],
    model=model,
    prompt=(
        "You are the supervisor of TripCacheAI, a travel planning team. "
        "1. If the user's request is missing basic info, route to 'trip_context_expert'. "
        "2. If the user asks for accommodation, route to 'hotel_expert'. "
        "3. If the user asks for a schedule, things to do, OR wants to modify/revise an existing plan, ALWAYS route to 'itinerary_expert'. "
        "Always synthesize the final answer concisely and in a friendly tone."
    ),
    state_schema=TripState,
    output_mode="last_message",
)

# ==========================================
# 6. MEMORY CHECKPOINTER & COMPILATION
# ==========================================
# check_same_thread=False allows Streamlit's multiple threads to share this connection
conn = sqlite3.connect("trip_memory.sqlite", check_same_thread=False)
# Compile with memory
#memory = InMemorySaver()
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)
