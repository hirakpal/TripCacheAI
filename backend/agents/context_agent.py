from langchain.agents import create_agent

def get_context_agent(model):
    return create_agent(
        model=model,
        tools=[],
        name="trip_context_expert",
        system_prompt=(
            "You collect missing trip details from the user: city, dates, budget, purpose, and guest count. "
            "Do not recommend hotels yourself. Just ask the user for missing info."
        ),
    )