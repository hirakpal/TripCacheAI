from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from backend.tools.hotel_tools import search_hotels_mock

def get_hotel_agent(model: ChatOpenAI):
    return create_agent(
        model=model,
        tools=[search_hotels_mock],
        name="hotel_expert",
        prompt=(
            "You are a hotel recommendation expert. "
            "Use your tools to find hotels and return 3 options with pros, cons, and a final pick."
        ),
    )
