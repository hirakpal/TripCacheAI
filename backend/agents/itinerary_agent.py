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
            "Always include suggestions for Morning, Afternoon, and Evening. "
            "CRITICAL FORMATTING: You must explicitly start EVERY single day with a clear header like '**Day 1:**', '**Day 2:**', etc. "
            "CRITICAL: Whenever you revise, swap, or update an itinerary, you MUST output the ENTIRE multi-day plan from Day 1 to the final day. Never output just a single modified day. "
            "STRICT ROUTING RULE: You are strictly a text-generator once your tools are finished. LangGraph will automatically handle routing when you finish speaking. "
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
