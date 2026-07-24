import streamlit as st
from typing import Annotated, Optional
from langchain_core.messages import BaseMessage, trim_messages
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

# ==========================================
# 1. OPTIMIZED TOKEN TRIMMING REDUCER
# ==========================================
def token_trimming_reducer(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """
    Combines messages, strips heavy metadata, and trims older turns deterministically
    without triggering secondary LLM calls.
    """
    combined = add_messages(left, right)
    
    # Strip unnecessary heavy metadata to save context overhead
    for msg in combined:
        if hasattr(msg, "response_metadata"):
            msg.response_metadata = {}
            
    # Deterministic trimming: keeps system prompt + initial inputs and trims middle turns
    return trim_messages(
        combined,
        max_tokens=2500, 
        strategy="last",
        token_counter=lambda msgs: sum(len(str(m.content)) // 4 for m in msgs),
        include_system=True,
        start_on="human",
        allow_partial=False
    )

# ==========================================
# 2. OPTIMIZED STATE SCHEMA
# ==========================================
class TripState(MessagesState):
    messages: Annotated[list[BaseMessage], token_trimming_reducer]
    plan_status: Optional[str] = "gathering"
    remaining_steps: Optional[int] = None

# ==========================================
# 3. INITIALIZE GROQ LLM WITH RETRIES
# ==========================================
model = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0, 
    max_retries=5,
    api_key=st.secrets["GROQ_API_KEY"]
)

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
        "You are the central supervisor of TripCacheAI, a multi-agent travel planning team. "
        "Analyze the entire conversation history carefully to check what details the user has provided.\n\n"
        "STRICT ROUTING RULES:\n"
        "1. If the user has provided basic details (destination, dates/duration, or budget), route to 'itinerary_expert' to generate or refine the plan.\n"
        "2. If the user explicitly asks about hotels or accommodation, route to 'hotel_expert'.\n"
        "3. ONLY route to 'trip_context_expert' if the user's initial input lacks basic travel information and no details have been collected yet.\n"
        "CRITICAL: Route to the appropriate agent once and yield control back to the user."
    ),
    state_schema=TripState,
    output_mode="last_message",
)

# ==========================================
# 6. MEMORY CHECKPOINTER & COMPILATION
# ==========================================
# Initialize connection and saver directly
conn = sqlite3.connect("trip_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)
