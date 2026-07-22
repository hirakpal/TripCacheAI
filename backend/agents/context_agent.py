from langchain.agents import create_agent

def get_context_agent(model):
    return create_agent(
        model=model,
        tools=[],
        name="trip_context_expert",
        system_prompt=(
            "You collect missing trip details from the user: city, dates, budget, purpose, and guest count. "
            "Do not recommend hotels yourself. Just ask the user for missing info."
            "STRICT RULE: Do not attempt to use any tools to transfer the user, route the conversation, or hand back control to the supervisor. You are strictly a text-generator. Simply provide your hotel recommendations and stop."
        ),
    )
