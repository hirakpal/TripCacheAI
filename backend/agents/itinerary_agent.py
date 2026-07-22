from langchain.agents import create_agent
#from backend.tools.itinerary_tools import search_attractions
from backend.mock_tools import search_attractions

def get_itinerary_agent(model):
    return create_agent(
        model=model,
        tools=[search_attractions],
        name="itinerary_expert",
        system_prompt=(
            "You are an expert travel itinerary planner. "
            "Use your tools to find local attractions based on the user's interests. "
            "Create a structured, day-by-day schedule grouping activities logically by location. "
            "Always include suggestions for Morning, Afternoon, and Evening."
            "CRITICAL: Whenever you revise, swap, or update an itinerary, you MUST output the ENTIRE multi-day plan from Day 1 to the final day. Never output just a single modified day." 
        ),
    )
def get_itinerary_agent(model,ChatOpenAI):
    return create_agent(
        model=model,
        tools=[search_attractions],
        name="itinerary_expert",
        system_prompt=(
            "You are an expert travel itinerary planner. "
            "Use your tools to find local attractions based on the user's interests. "
            "Create a structured, day-by-day schedule grouping activities logically by location. "
            "Always include suggestions for Morning, Afternoon, and Evening."
            "CRITICAL: Whenever you revise, swap, or update an itinerary, you MUST output the ENTIRE multi-day plan from Day 1 to the final day. Never output just a single modified day." 
        ),
    )
