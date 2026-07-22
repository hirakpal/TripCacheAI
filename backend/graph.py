import sqlite3
import streamlit as st
from typing import Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, trim_messages
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq

from backend.agents.hotel_agent import get_hotel_agent
from backend.agents.context_agent import get_context_agent
from backend.agents.itinerary_agent import get_itinerary_agent

# ==========================================
# 1. ADVANCED SUMMARIZATION & TRIMMING REDUCER
# ==========================================
def token_trimming_reducer(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """
    Combines messages, strips heavy metadata, and summarizes long threads 
    to maximize token savings and prevent Groq rate limits.
    """
    combined = add_messages(left, right)
    
    # Strip unnecessary heavy metadata to save hidden context overhead
    for msg in combined:
        if hasattr(msg, "response_metadata"):
            msg.response_metadata = {}
            
    # If the thread gets long (e.g., more than 12 messages), summarize the older context
    if len(combined) > 12:
        # Keep the system prompt / first message, summarize the middle, and keep the last 4 messages raw
        older_messages = combined[1:-4]
        recent_messages = combined[-4:]
        
        # Build a quick text block to summarize
        conversation_text = "\n".join([f"{m.type}: {m.content}" for m in older_messages if m.content])
        
        # Lightweight prompt to create a running summary
        summary_prompt = (
            "Summarize the key facts, preferences, dates, budgets, and decisions made in this travel planning conversation "
            "into a single concise paragraph. Keep all critical constraints:\n\n" + conversation_text
        )
        
        try:
            # We initialize a quick lightweight call or use the main model to generate the summary
            summary_model = ChatGroq(
                model="llama-3.1-8b-instant", 
                temperature=0, 
                api_key=st.secrets["GROQ_API_KEY"]
            )
            summary_response = summary_model.invoke([HumanMessage(content=summary_prompt)])
            
            # Create a compressed history block: [First Message/System] + [Summary Message] + [Recent Turns]
            compressed_history = [
                combined[0],
                SystemMessage(content=f"[Running Conversation Summary]: {summary_response.content}")
            ] + recent_messages
            
            combined = compressed_history
        except Exception:
            pass # Fallback to standard trimming if summary API call fails
            
    # Final strict token budget cap using trim_messages
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
    model="llama-3.3-70b-versatile", # The highly available, fast Meta model
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
        "Do not just answer in chat when an expert is needed; actively route the task to the correct agent."
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
