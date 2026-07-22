from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
#from backend.tools.hotel_tools import search_hotels
from backend.mock_tools import search_hotels

def get_hotel_agent(model):
    return create_agent(
        model=model,
        tools=[search_hotels],
        name="hotel_expert",
        system_prompt=(
            "You are a specialized hotel booking assistant. "
            "Your goal is to recommend accommodations using the 'search_hotels' tool. "
            "CRITICAL: The 'search_hotels' tool requires 4 mandatory inputs: location, budget, check-in date, and check-out date. "
            "If the user has not provided ALL 4 of these details in the conversation, you MUST ask the user for the missing information before calling the tool. "
            "Never invent or hallucinate hotel names or availability. Only recommend what the tool returns."
            "STRICT ROUTING RULE: You are strictly a text-generator once your tools are finished. LangGraph will automatically handle routing when you finish speaking. "
            "NEVER attempt to transfer control back to the supervisor. NEVER output fake tool calls or tags like <function=transfer_back_to_supervisor>. Just provide your final text response and stop."
            
        )
    )

# def get_hotel_agent(model: ChatOpenAI):
#     return create_agent(
#         model=model,
#         tools=[search_hotels],
#         prompt=(
#             "You are a specialized hotel booking assistant. "
#             "Your goal is to recommend accommodations using the 'search_hotels' tool. "
#             "CRITICAL: The 'search_hotels' tool requires 4 mandatory inputs: location, budget, check-in date, and check-out date. "
#             "If the user has not provided ALL 4 of these details in the conversation, you MUST ask the user for the missing information before calling the tool. "
#             "Never invent or hallucinate hotel names or availability. Only recommend what the tool returns."
#         )
#     )
