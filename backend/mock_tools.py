from langchain_core.tools import tool

@tool
def search_hotels(location: str, budget: str, check_in_date: str, check_out_date: str) -> dict:
    """
    Searches for hotels based on location, budget, and dates.
    ALL parameters (location, budget, check_in_date, check_out_date) are mandatory.
    Dates must be provided in YYYY-MM-DD format.
    """
    
    # 1. The Mock Database
    mock_database = {
        "bengaluru": [
            {"name": "The Taj West End", "price_per_night": 15000, "currency": "INR", "rating": 4.8, "amenities": ["Pool", "Spa"]},
            {"name": "ITC Gardenia", "price_per_night": 12000, "currency": "INR", "rating": 4.7, "amenities": ["Eco-friendly", "Gym"]},
            {"name": "Holiday Inn Express", "price_per_night": 4000, "currency": "INR", "rating": 4.1, "amenities": ["Free WiFi", "Budget"]}
        ]
    }

    city_key = location.lower().strip()
    
    # 2. Fetch results (Mocking availability for the provided dates)
    results = mock_database.get(city_key, [
        {"name": f"The Grand {location} Plaza", "price_per_night": 8000, "currency": "INR", "rating": 4.2, "amenities": ["Pool", "WiFi"]}
    ])

    # 3. Return the payload, reflecting the requested dates back to the agent
    return {
        "search_parameters": {
            "location": location,
            "check_in": check_in_date,
            "check_out": check_out_date,
            "budget": budget
        },
        "available_hotels": results
    }

@tool
def search_attractions(city: str, interests: str = "top tourist attractions") -> str:
    """Search for real activities, landmarks, and attractions in a city using Google Places (Mock Version)."""
    
    # Mock data customized based on the input parameters
    mock_places = [
        {
            "name": f"The Great {city} Museum", 
            "address": f"123 Museum Way, {city}", 
            "rating": 4.8
        },
        {
            "name": f"{city} Central Park", 
            "address": f"456 Green Ave, {city}", 
            "rating": 4.7
        },
        {
            "name": f"Historic Downtown {city}", 
            "address": f"789 Main St, {city}", 
            "rating": 4.5
        },
        {
            "name": f"The {interests.title()} Experience", 
            "address": f"101 Tourist Blvd, {city}", 
            "rating": 4.3
        },
        {
            "name": f"{city} Observation Deck",
            "address": f"999 Sky High Tower, {city}",
            "rating": 4.9
        }
    ]
    
    lines = []
    for p in mock_places:
        name = p.get("name", "Unknown")
        addr = p.get("address", "N/A")
        rating = p.get("rating", "N/A")
        lines.append(f"{name} | {addr} | rating: {rating}")
        
    return "\n".join(lines) if lines else f"No attractions found in {city}."
