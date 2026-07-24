import sqlite3
from typing import Annotated, Optional, Dict, Any
import streamlit as st

from langchain_core.messages import BaseMessage, trim_messages
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph_supervisor import create_supervisor

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent
from backend.schemas import AgentResponse, NextAction, AgentStatus

# ==========================================
# 0. DYNAMIC LLM FACTORY
# ==========================================
def get_llm(model_name: str = "llama-3.3-70b-versatile"):
    """
    Instantiates the selected model dynamically based on provider.
    Supports Groq, OpenAI, Google Gemini, Anthropic Claude, or OpenRouter fallback.
    """
    # 1. Groq Models
    if model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]:
        return ChatGroq(
            model=model_name,
            temperature=0,
            max_retries=5,
            api_key=st.secrets["GROQ_API_KEY"]
        )
    
    # 2. ChatGPT / OpenAI Models
    elif model_name in ["gpt-4o", "gpt-4o-mini"]:
        return ChatOpenAI(
            model=model_name,
            temperature=0,
            max_retries=5,
            api_key=st.secrets["OPENAI_API_KEY"]
        )
        
    # 3. Google Gemini Models
    elif "gemini" in model_name:
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            max_retries=5,
            google_api_key=st.secrets["GOOGLE_API_KEY"]
        )
        
    # 4. Anthropic Claude Models
    elif "claude" in model_name:
        return ChatAnthropic(
            model=model_name,
            temperature=0,
            max_retries=5,
            anthropic_api_key=st.secrets["ANTHROPIC_API_KEY"]
        )

    # 5. Fallback via OpenRouter
    else:
        return ChatOpenAI(
            model=model_name,
            temperature=0,
            max_retries=5,
            openai_api_key=st.secrets["OPENROUTER_API_KEY"],
            openai_api_base="https://openrouter.ai/api/v1"
        )

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
    traveler_profile: Optional[Dict[str, Any]] = {}
    suggestion_chips: Optional[list[str]] = []
    next_action: Optional[str] = NextAction.WAIT_FOR_USER.value
    next_agent: Optional[str] = None
    remaining_steps: Optional[int] = None

# ==========================================
# 3. MEMORY CHECKPOINTER & COMPILATION
# ==========================================
conn = sqlite3.connect("trip_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

# ==========================================
# 4. DYNAMIC GRAPH BUILDER FACTORY
# ==========================================
def get_compiled_graph(model_name: str = "llama-3.3-70b-versatile"):
    """
    Builds and compiles the supervisor workflow using the user's selected active model.
    """
    model = get_llm(model_name)

    hotel_agent = get_hotel_agent(model)
    traveler_profile_expert = get_context_agent(model)
    itinerary_agent = get_itinerary_agent(model)

    # CRITICAL: Attach explicit .name attributes to callable function closures
    hotel_agent.name = "hotel_expert"
    traveler_profile_expert.name = "traveler_profile_expert"
    itinerary_agent.name = "itinerary_expert"

    workflow = create_supervisor(
        agents=[traveler_profile_expert, hotel_agent, itinerary_agent],
        model=model,
        prompt=(
            "You are the central supervisor of TripCacheAI, a multi-agent travel planning team.\n\n"
            "ROUTER DIRECTIVES:\n"
            "1. Check the conversation history for basic trip constraints (destination, dates/duration, budget, travelers, arrival hub).\n"
            "2. IF any mandatory profile details are missing, route to 'traveler_profile_expert'.\n"
            "3. IF duration/dates, budget, and destination are already present in the message history, route to 'itinerary_expert'.\n"
            "4. IF the user asks about hotels, accommodation, or places to stay, route to 'hotel_expert'.\n"
            "5. Do NOT re-route to 'traveler_profile_expert' if the traveler profile is complete."
        ),
        state_schema=TripState,
        output_mode="last_message",
    )

    return workflow.compile(checkpointer=memory)

# Default fallback instance for direct module imports
app = get_compiled_graph("llama-3.3-70b-versatile")
