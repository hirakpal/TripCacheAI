import os
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver

# Ensure you have OPENAI_API_KEY set in your environment
model = ChatOpenAI(model="gpt-4o", temperature=0)

# ---------------------------------------------------------
# Tools
# ---------------------------------------------------------
@tool
def search_hotels_mock(
    city: str,
    budget: Literal["low", "mid", "high"] = "mid",
    purpose: Literal["business", "family", "couple", "solo"] = "business",
) -> str:
    """Search hotels. (Currently mocked for rapid prototyping)."""
    # Later: Replace this with your Google Places or Booking API logic
    catalog = [
        {"name": "TechHub Inn", "city": "Bengaluru", "budget": "mid", "purpose": "business", "rating": 4.6},
        {"name": "Oasis Resort", "city": "Bengaluru", "budget": "high", "purpose": "couple", "rating": 4.9},
        {"name": "City Square Stay", "city": "Bengaluru", "budget": "mid", "purpose": "family", "rating": 4.2},
    ]
    
    matches = [h for h in catalog if h["city"].lower() == city.lower() and h["budget"] == budget]
    if not matches:
        return f"No {budget} budget hotels found in {city}."
        
    return "\n".join(
        f"{h['name']} | Rating: {h['rating']} | Best for: {h['purpose']}" 
        for h in matches
    )

# ---------------------------------------------------------
# Agents
# ---------------------------------------------------------
hotel_agent = create_react_agent(
    model=model,
    tools=[search_hotels_mock],
    name="hotel_expert",
    prompt=(
        "You are a hotel recommendation expert. "
        "Use your tools to find hotels and return 3 options with pros, cons, and a final pick."
    ),
)

trip_context_agent = create_react_agent(
    model=model,
    tools=[],
    name="trip_context_expert",
    prompt=(
        "You collect missing trip details from the user: city, dates, budget, purpose, and guest count. "
        "Do not recommend hotels yourself. Just ask the user for missing info."
    ),
)

# ---------------------------------------------------------
# Supervisor & Graph Compilation
# ---------------------------------------------------------
memory = InMemorySaver()

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

# Compile the workflow with memory enabled for multi-turn conversations
app = workflow.compile(checkpointer=memory)
