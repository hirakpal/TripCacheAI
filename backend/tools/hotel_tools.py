from typing import Literal
from langchain_core.tools import tool

@tool
def search_hotels_mock(
    city: str,
    budget: Literal["low", "mid", "high"] = "mid",
    purpose: Literal["business", "family", "couple", "solo"] = "business",
) -> str:
    """Search hotels. (Currently mocked for rapid prototyping)."""
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
