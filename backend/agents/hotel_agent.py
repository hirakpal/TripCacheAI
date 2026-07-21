from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from backend.tools.hotel_tools import search_hotels

def get_hotel_agent(model: ChatOpenAI):
    return create_agent(
        model=model,
        tools=[search_hotels],
        prompt=(
            "You are a specialized hotel booking assistant. "
            "You MUST use the 'search_hotels' tool to find accommodations before answering the user. "
            "Never invent or hallucinate hotel names. Only recommend what the tool returns."
        )
    )
