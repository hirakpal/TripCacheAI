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
            "MANDATORY FORMATTING INSTRUCTIONS: "
            "1. Present the itinerary in a clean, professional layout using bold headers for each day (e.g., '### Day 1: Arrival & Historical Exploration'). "
            "2. Create a structured, day-by-day schedule grouping activities logically by location. "
            "2. For each day, use clear bullet points categorized explicitly into **Morning**, **Afternoon**, and **Evening**. "
            "3. Include estimated travel methods or tips (e.g., transport recommendations) inline with each activity. "
            "4. Add a dedicated section at the bottom for **Recommended Local Restaurants & Food Spots**. "
            "CRITICAL: Whenever you revise, swap, or update an itinerary, you MUST output the ENTIRE multi-day plan from Day 1 to the final day. Never output just a single modified day. "
            "STRICT ROUTING RULE: You are strictly a text-generator once your tools are finished. Never output fake tool tags."
            "NEVER attempt to transfer control back to the supervisor. NEVER output fake tool calls or tags like <function=transfer_back_to_supervisor>. Just provide your final text response and stop."
            
        ),
        
    )
# def get_itinerary_agent(model: ChatOpenAI):
#     return create_agent(
#         model=model,
#         tools=[search_attractions],
#         name="itinerary_expert",
#         system_prompt=(
#             "You are an expert travel itinerary planner. "
#             "Use your tools to find local attractions based on the user's interests. "
#             "Create a structured, day-by-day schedule grouping activities logically by location. "
#             "Always include suggestions for Morning, Afternoon, and Evening."
#             "CRITICAL: Whenever you revise, swap, or update an itinerary, you MUST output the ENTIRE multi-day plan from Day 1 to the final day. Never output just a single modified day." 
#         ),
#     )
